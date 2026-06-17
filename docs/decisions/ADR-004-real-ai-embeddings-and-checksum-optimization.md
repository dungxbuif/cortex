---
artifact_type: adr
id: ADR-004
status: accepted
owner: human
human_fields: [title, status, context, decision, consequences]
ai_fields: [evidence, linked_issues]
shared_fields: []
---

# ADR-004: Switch to Real AI Embeddings and Checksum Optimization

## Context
The Second Brain module originally relied on deterministic hashing for chunk "embeddings" to allow the system to pass unit tests without connecting to an external API. As the RAG capability matures, we need actual vector embeddings with high dimensionality to accurately calculate cosine similarity and return semantically relevant documents. Relying entirely on an external API (Google Gemini `gemini-embedding-2`) introduces issues around API rate limits (e.g. 15 Requests Per Minute on free tiers) and latency when indexing the entire vault repeatedly.

## Decision
1. **Google Gemini Embeddings Integration**: We replace the deterministic local embedding mock with the real Google AI Gemini embedding model using Python's standard `urllib.request`.
2. **Exponential Backoff Retry Strategy**: To handle `HTTP 429 Too Many Requests`, we implemented an exponential backoff loop directly in the HTTP client logic.
3. **Checksum Indexing Bypass**: We compute a checksum of the incoming markdown document and compare it to the existing `checksum` in the database. Unmodified files skip the chunking and embedding phase, immediately returning 0 chunks processed, avoiding expensive embedding extraction over the network.

## Consequences
- **Positive**: We achieve true semantic search with RAG and ground-truth testing.
- **Positive**: Frequent sync calls by clients will not trigger rate-limits or slow down processing for unmodified files.
- **Negative**: The testing environment requires a valid `GOOGLE_API_KEY` to run RAG integration tests.

## Evidence
- Integration tests ran on a real 91-file local vault passed successfully using real Gemini embeddings, taking roughly 8 minutes to initially chunk and embed, but completing instantly upon second run due to checksum optimization.
- The Python standard library `urllib` replaced shell `curl` commands, removing reliance on subprocess execution while maintaining cross-platform compatibility.

## Linked Issues
- Phase: Second Brain AI Evaluation Setup
