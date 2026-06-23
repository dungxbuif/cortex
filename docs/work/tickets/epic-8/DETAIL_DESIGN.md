---
artifact_type: detail_design
id: EPIC-8-DETAIL-DESIGN
status: approved
owner: shared
human_fields:
  - approval
  - scope_tradeoffs
ai_fields:
  - problem_statement
  - context_loaded
  - proposed_approach
  - alternatives
  - impact
  - verification_plan
  - reconciliation_plan
shared_fields:
  - status
  - trace
trace:
  backlog_item: BL-011
  phase: docs/work/phases/PHASE-8-ingestion-hardening.md
  tickets:
    - docs/work/tickets/epic-8/CTX-801.md
    - docs/work/tickets/epic-8/CTX-802.md
  raw_specs:
    - docs/raw_spec/system/source-of-truth-sync.md
    - docs/raw_spec/system/rag-indexing.md
  validation_matrix: docs/work/VALIDATION_MATRIX.md
  release_notes: docs/releases/CHANGELOG.md
---

# Epic 8 Detail Design: Async Ingestion & Delete Sync Hardening

## Approval Status

Approved by human instruction: "Approve triển khai Epic 5 rồi Epic 8."

## Problem Statement

The current Second Brain MinIO webhook path handles indexing synchronously on the API request thread. A webhook request can perform event validation, S3 object retrieval, Markdown chunking, Gemini embedding calls, and PostgreSQL/pgvector writes before responding. Large files or provider rate limits can therefore block webhook requests and cause timeouts.

The current path also handles create/update ingestion but does not yet process delete events. Removed Obsidian mirror files can leave stale `secondbrain_documents` and `secondbrain_document_chunks` records, allowing RAG to cite content that no longer exists in the canonical source.

## Context Loaded

- `docs/CONTEXT.md`
- `docs/work/BACKLOG.md`
- `docs/standards/README.md`
- `docs/standards/QUALITY_BAR.md`
- `docs/standards/VALIDATION.md`
- `docs/raw_spec/spec.md`
- `docs/raw_spec/system/source-of-truth-sync.md`
- `docs/raw_spec/system/rag-indexing.md`
- `docs/work/tickets/epic-2/CTX-204.md`
- `docs/work/phases/PHASE-8-ingestion-hardening.md`

## Proposed Approach

### CTX-801: Async Ingestion Queue

Introduce a durable ingestion job boundary:

```text
Webhook request
  -> authenticate token/client
  -> authorize second_brain.index_external_source
  -> validate event scope
  -> persist/enqueue ingestion job
  -> return 202 Accepted

Worker
  -> claim job
  -> fetch S3/MinIO object
  -> parse/chunk Markdown
  -> embed chunks with retry/backoff
  -> write document/chunk records
  -> mark job succeeded/failed
```

The first implementation uses a PostgreSQL-backed job table with explicit columns for event metadata and status. Indexed document content and embeddings remain in the existing PostgreSQL + pgvector document/chunk tables; JSON is not used as a substitute for the vector index. The interface keeps room for Celery/RQ or another broker later.

### CTX-802: Delete Synchronization

Handle delete events through the same job boundary:

```text
s3:ObjectRemoved:* event
  -> validate accepted prefix and Markdown suffix
  -> persist delete job
  -> worker maps bucket/key to document source path
  -> delete or tombstone document row
  -> delete related secondbrain_document_chunks
  -> audit cleanup result
```

Deletion behavior must follow the source-of-truth policy: the Obsidian Vault/mirror is canonical for knowledge documents, the PostgreSQL RAG index is derived, and derived chunks must not survive canonical deletion.

## Alternatives Considered

### Alternative A: Keep synchronous webhook ingestion

Rejected. It is simple but fragile under large files, slow S3, provider latency, and Gemini rate limits.

### Alternative B: Add Celery/RQ immediately

Viable, but may be deferred if a database-backed queue satisfies the first hardening slice with fewer runtime dependencies. The job interface should not depend on the specific queue engine.

### Alternative C: Mark deleted records stale but keep chunks searchable

Rejected. It preserves forensic data but violates RAG correctness unless every query filters stale records perfectly. If historical retention is needed later, keep it outside active RAG search.

## Impact

| Area | Impact |
| --- | --- |
| API/contract | Webhook success semantics change from synchronous completion to `202 Accepted` job acceptance. |
| Data model | Adds ingestion job/status records and delete/tombstone handling if approved. |
| Runtime | Adds worker process or worker loop for ingestion jobs. |
| Security/audit | Should call Epic 5 capability policy for `second_brain.index_external_source` and audit enqueue/worker/delete events. |
| Existing behavior | CTX-204 sync behavior must remain functionally equivalent once jobs complete. |
| Docs | Source-of-truth, architecture, validation matrix, and changelog need reconciliation. |

## Verification Plan

Expected proof after implementation:

```bash
rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v
rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...
rtk bash -n scripts/simulate-secondbrain-s3-action.sh
rtk git diff --check
```

Required coverage:

- Webhook route returns `202 Accepted` after accepted create/update job persistence.
- Worker processes create/update job with fake object store and fake embedder.
- Retry/failure paths record job status without blocking webhook response.
- Delete event removes or tombstones document rows and removes related chunks.
- RAG search no longer returns deleted content.
- Authorization/audit hooks are covered when Epic 5 policy is available.

## Reconciliation Plan

- Update `docs/work/VALIDATION_MATRIX.md` with implemented evidence.
- Update `docs/architecture/ARCHITECTURE.md` for async ingestion runtime.
- Update source-of-truth docs if deletion/tombstone policy is refined.
- Update `docs/releases/CHANGELOG.md`.
- Update `docs/CONTEXT.md` and `docs/work/BACKLOG.md`.
