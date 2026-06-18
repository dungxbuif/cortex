# Second Brain Module: Academic Notes, AI/RAG Mental Model, and Project Design

> Note: This document is intentionally educational. The owner does not need deep AI
> background before implementation, so the goal is to explain the academic problem,
> practical AI concepts, and how those concepts map into Cortex tickets CTX-201,
> CTX-202, and CTX-203.

## 1. Dat van de: Raw Spec va yeu cau he thong

Cortex is a personal AI system used through chat. The Second Brain module manages a
local Obsidian Vault named `second-brain/`, captures new notes from chat, and answers
questions from indexed Markdown knowledge.

From the raw spec, the important requirements are:

- The local Obsidian Vault is the canonical source of long-term knowledge.
- PostgreSQL is not the canonical knowledge store. It stores capture buffer,
  metadata, sync state, audit data, full-text index, and vector index.
- Chat may capture temporary notes into DB, but must not write directly to the
  local Vault in the current scope.
- RAG must read only approved, synced, indexed Vault documents.
- RAG must not read transient capture inbox data.
- RAG answers must cite source documents when they rely on indexed knowledge.
- Module APIs must not contain prompts, ReAct loops, OpenAI tool schemas, or chat
  history logic. Orchestrator owns AI coordination; the module owns domain APIs.
- Go remains the Cortex orchestrator/API gateway. ADR-003 moves Second Brain AI/RAG
  heavy work to a Python FastAPI service because Python has better tooling for
  Markdown parsing, embeddings, evaluation, and RAG experiments.

The product problem:

```text
User has knowledge in Obsidian Markdown.
User asks Cortex a question in chat.
Cortex must answer using the right notes, not guess, not leak private/capture data,
and show which files support the answer.
```

The engineering problem:

```text
Markdown Vault
  -> parse
  -> normalize metadata
  -> chunk
  -> embed
  -> index
  -> retrieve
  -> filter by policy
  -> build context
  -> answer with citations
  -> evaluate quality
```

## 2. Kien truc tong quan

Second Brain is not "training an AI". It is a controlled retrieval and grounding
pipeline around an existing LLM.

```text
+------------------+       +----------------------+       +-------------------+
| Open WebUI Chat  | ----> | Go Cortex            | ----> | Python Second     |
|                  |       | Orchestrator/Gateway |       | Brain API         |
+------------------+       +----------------------+       +-------------------+
                                      |                           |
                                      v                           v
                           +----------------------+       +-------------------+
                           | Permission / Tool    |       | PostgreSQL        |
                           | Adapter / Audit      |       | pgvector + FTS    |
                           +----------------------+       +-------------------+
                                                                  ^
                                                                  |
                                                        +-------------------+
                                                        | Obsidian Vault    |
                                                        | second-brain/     |
                                                        +-------------------+
```

Ownership:

- Go Orchestrator: chat API, intent routing, permission checks, tool adapter,
  response synthesis.
- Python Second Brain API: capture inbox API, sync status API, Markdown parsing,
  chunking, embeddings, retrieval, RAG policy, evaluation.
- PostgreSQL + pgvector: capture records, document metadata, chunk index, vector
  embeddings, retrieval logs.
- Obsidian Vault: human-owned canonical knowledge.

## 3. Kho khan thuc te

### 3.1. LLM khong tu biet tri thuc ca nhan

LLM only knows what was in training data and what is provided in prompt context. It
does not automatically know your Obsidian Vault. If the system sends the wrong
context, the model may answer confidently but incorrectly.

Practical implication:

- The hardest part is not writing the final prompt.
- The hardest part is retrieving the right notes and rejecting forbidden notes.

### 3.2. Markdown is semi-structured, not clean database rows

Obsidian notes contain frontmatter, headings, wikilinks, tags, backlinks, Dataview
blocks, code blocks, checklists, daily logs, and mixed Vietnamese/English text.

Problems:

- Naive text splitting can cut a concept in half.
- YAML frontmatter may be missing, malformed, or inconsistent.
- Links and headings carry meaning that plain text search misses.
- `wiki/`, `staging/`, `raw/`, `tracking/`, and `archive/` should not rank equally.

### 3.3. Capture inbox is not knowledge yet

A chat capture is only a draft. It may be wrong, duplicated, private, or not yet
reviewed. If RAG reads capture inbox directly, the system can answer from temporary
unapproved notes.

Rule:

```text
capture inbox -> review/copy/export by human -> Vault -> sync/index -> RAG source
```

Never:

```text
capture inbox -> RAG answer
```

### 3.4. AI quality cannot be judged by feeling

AI answers often sound good even when retrieval is bad. For this project, quality
must be measured with golden tests and metrics:

- Did the retriever return the expected file?
- Did `wiki/` rank above `raw/`?
- Did private or `rag:false` files leak?
- Did every grounded answer include citation?
- Did archive files pollute active answers?

## 4. Giai phap thiet ke

### 4.1. Separate capture, sync, retrieval, and generation

The system is divided into clear stages:

```text
CTX-201 Capture Buffer API
  User chat note -> normalized markdown draft -> DB capture inbox

CTX-202 Sync Status API
  Vault snapshot -> document metadata -> checksum/status/index state

CTX-203 Vault RAG Query API
  User question -> retrieve approved chunks -> return cited context
```

Generation is deliberately outside the Second Brain domain module. The module
returns structured search results and citations. The orchestrator decides how to ask
the LLM to produce the final answer.

### 4.2. Use RAG instead of training

RAG means Retrieval-Augmented Generation:

1. Retrieve relevant chunks from a trusted knowledge base.
2. Add those chunks to the model context.
3. Ask the model to answer only from that context.
4. Return citations so the answer is auditable.

Why this design:

- Personal knowledge changes often; retraining is slow, expensive, and unnecessary.
- RAG keeps source-of-truth in Markdown, where the human can edit it.
- RAG allows privacy filters before context reaches the model.
- RAG can be tested with deterministic retrieval datasets.

### 4.3. Prefer hybrid search

Vector search is good at semantic similarity, but weak for exact names, file paths,
tags, and technical identifiers. Full-text search is good at exact words, but weak
for paraphrases.

Use hybrid retrieval:

```text
final_score =
  vector_similarity_score
  + full_text_score
  + metadata_boost
  + lifecycle_boost
  - policy_penalty
```

Example:

- Question: "consistent hashing la gi?"
- Full-text finds notes containing `consistent hashing`.
- Vector search finds semantically similar caching/scaling notes.
- Metadata boost prefers `wiki/` over `raw/`.
- Policy filter removes `private:true`, `rag:false`, archive, and capture inbox.

### 4.4. Make policy a retrieval constraint, not a prompt suggestion

Do not rely on a prompt that says "do not read private notes". Private notes must be
excluded before the LLM sees context.

Policy checks happen before answer generation:

```text
candidate chunks
  -> owner filter
  -> rag_allowed filter
  -> private filter
  -> capture inbox exclusion
  -> archive/default lifecycle filter
  -> context builder
  -> LLM prompt
```

## 5. Kien thuc nen AI can biet va cach apply vao Cortex

### 5.1. Token and context window

A token is a model processing unit, roughly a piece of a word. LLMs can only read a
limited number of tokens per request.

Apply to Cortex:

- Do not put the whole Vault into one prompt.
- Retrieve top relevant chunks only.
- Deduplicate overlapping chunks.
- Keep citation metadata with each chunk.

### 5.2. Embedding

An embedding is a numeric vector representing semantic meaning of text. Similar
meaning should produce vectors close to each other.

Apply to Cortex:

- Store chunk embeddings in PostgreSQL `pgvector`.
- Store one embedding per chunk, not one embedding per whole Vault.
- Recompute embeddings when file checksum changes.

### 5.3. Chunking

Chunking splits documents into retrieval units. Good chunks preserve meaning.

Bad chunking:

```text
Every 1000 characters, cut text blindly.
```

Better chunking:

```text
Keep heading chain + paragraph/list/code block boundaries.
Attach source path, heading, tags, status, and line range.
```

Apply to Cortex:

- Chunk by Markdown structure: H1/H2/H3, lists, code blocks, and frontmatter.
- Keep `heading_chain` for citation and ranking.
- Avoid chunks that mix unrelated topics.

### 5.4. Retrieval

Retrieval chooses which chunks are relevant for a question.

Metrics:

- Precision: how many retrieved chunks are actually relevant.
- Recall: how many expected relevant chunks were found.
- Top-k accuracy: whether expected source appears in top k results.
- MRR: how high the first correct result appears.

Apply to Cortex:

- Gate CTX-203 with top-3 retrieval accuracy >= 85%.
- Prefer `wiki/` when both `wiki/` and `raw/` match the same concept.
- Log query, candidate chunks, final chunks, and ranking reasons for debugging.

### 5.5. Grounding

Grounding means the answer must be supported by provided source context.

Apply to Cortex:

- If retrieval returns no reliable source, answer should say knowledge is missing.
- Do not let the LLM invent facts from memory for personal knowledge questions.
- Require citations for answers that use Vault knowledge.

### 5.6. Citation

Citation links the answer back to source files/headings.

Apply to Cortex:

- Every retrieved chunk carries `vault_path`, `heading_chain`, and optional line
  range.
- Final answer should cite the source path.
- Citation coverage target: 100% for grounded RAG answers.

### 5.7. Evaluation

Evaluation is the test suite for AI behavior.

Apply to Cortex:

- Maintain JSONL eval questions with expected paths.
- Include negative cases: capture inbox should not be found; `rag:false` should not
  be found; private notes should not be found.
- Run golden tests for parser, metadata, chunker, link graph, policy, and retrieval.

Example eval row:

```json
{"question":"Consistent hashing la gi?","expected_paths":["wiki/system-design/consistent-hashing.md"],"must_rank_above":["raw/consistent-hashing-raw.md"]}
```

### 5.8. Reranking

Reranking reorders retrieved candidates using a stronger scoring model or rules.

Apply later, not first:

- Start with hybrid search and deterministic metadata boosts.
- Add reranking only after baseline evals exist.
- Never use reranking to bypass policy filters.

## 6. Project-specific data model mental model

Recommended table naming should stay consistent with the ERD:

- `secondbrain_captures`: temporary capture inbox. Not a RAG source.
- `secondbrain_documents`: metadata for indexed Vault files.
- `secondbrain_document_chunks`: chunk text and embeddings for RAG.

Important fields:

```text
secondbrain_documents
  id
  owner_id
  vault_path
  checksum
  document_type       raw | staging | wiki | tracking | dailylog | archive
  rag_allowed         false if frontmatter says rag:false
  private             true if note is private
  frontmatter
  indexed_at

secondbrain_document_chunks
  id
  document_id
  chunk_index
  content
  heading_chain
  embedding
  token_count
```

Why this model:

- Document metadata changes independently from chunk content.
- Chunks are the retrieval unit, documents are the source/citation unit.
- Capture inbox is physically separate so RAG exclusion can be enforced by schema
  and query design, not only by developer discipline.

## 7. Implementation roadmap for this phase

### Step 1: CTX-201 Capture Buffer API

Goal:

- Accept raw text from chat.
- Normalize into Markdown draft.
- Save to `secondbrain_captures`.
- Support list/detail/copy/export/discard status.

Must not:

- Write directly to Obsidian Vault.
- Put capture records into RAG index.

### Step 2: CTX-202 Sync Status API

Goal:

- Track Vault snapshot/index state.
- Know which files are indexed, stale, failed, deleted, or skipped.
- Store checksum and indexing metadata.

Must not:

- Treat DB as canonical knowledge.
- Silently index private or forbidden files.

### Step 3: CTX-203 Vault RAG Query API

Goal:

- Search approved Vault chunks with hybrid retrieval.
- Return chunks with citations and ranking metadata.
- Exclude capture inbox, private notes, `rag:false`, and archive by default.

Must not:

- Generate final answer inside the domain service.
- Return uncited context for grounded RAG.

## 8. Minimum quality gates

Level 1 system is acceptable only when:

- Markdown parser handles frontmatter, headings, links, code blocks, and tags.
- Chunker preserves semantic structure and citation metadata.
- Indexer detects created, updated, deleted, and moved files.
- RAG query returns expected source paths for golden questions.
- Capture inbox leak count is 0.
- `rag:false` leak count is 0.
- Private note leak count is 0.
- Archive pollution rate is 0 by default.
- Citation coverage is 100% for grounded answers.
- Top-3 retrieval accuracy is >= 85%.
- Wiki priority accuracy is >= 90%.

## 9. What not to do

- Do not put the whole Vault into the prompt.
- Do not let the LLM decide which files it may read.
- Do not let RAG read capture inbox records.
- Do not chunk by fixed character count without Markdown structure.
- Do not judge quality by whether the answer "sounds right".
- Do not optimize prompts before retrieval works.
- Do not add rerankers, agents, or knowledge graphs before baseline evals exist.
- Do not mix orchestrator prompt logic into the Second Brain domain service.

## 10. Practical learning order

For implementation, learn in this order:

1. Source-of-truth and policy: which data may be read or written.
2. Markdown parsing and metadata normalization.
3. Chunking and citation metadata.
4. Embeddings and pgvector basics.
5. Full-text search and hybrid ranking.
6. Retrieval evaluation metrics.
7. Context building and grounding.
8. Prompt contract for final answer.
9. Observability for RAG debugging.
10. Advanced reranking and graph features.

This order matters because a strong model cannot fix a weak retrieval pipeline. In
Cortex, AI quality starts with source control, parsing, chunking, retrieval, and
evaluation before prompt tuning.
