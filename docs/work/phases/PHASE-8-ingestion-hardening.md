---
artifact_type: phase
id: PHASE-8-ingestion-hardening
status: ready
owner: human
human_fields:
  - goal
  - scope
  - out_of_scope
  - priority
  - success_criteria
ai_fields:
  - risks
  - dependencies
  - verification_plan
  - completion_summary
shared_fields:
  - status
  - trace
  - tickets_and_bugs
trace:
  backlog_items:
    - BL-011
  roadmap: ROADMAP
  requirements:
    - docs/raw_spec/system/source-of-truth-sync.md
    - docs/raw_spec/system/rag-indexing.md
  tickets:
    - ../tickets/epic-8/CTX-802.md
    - ../tickets/epic-8/CTX-803.md
    - ../tickets/epic-8/CTX-709.md
---

# PHASE-8: Async Ingestion & Delete Sync Hardening

## Goal

Harden Second Brain external ingestion after the current synchronous MinIO webhook path by moving heavy work off the API thread and keeping the RAG index consistent when source documents are deleted.

## Scope

- Introduce an asynchronous ingestion job path for Obsidian/MinIO webhook events.
- Return `202 Accepted` from webhook handling after authentication, event validation, and durable job enqueue/persistence.
- Process S3 object create/update events in a worker that downloads objects, chunks Markdown, calls embedding providers, and writes PostgreSQL/pgvector records.
- Process S3 object delete events by removing or tombstoning the matching `secondbrain_documents` row and deleting related `secondbrain_document_chunks`.
- Track ingestion job status, retries, failure reasons, source revision/hash, and idempotency keys.
- Preserve existing checksum-aware indexing behavior and source-of-truth rules.
- Add a unified S3-compatible webhook that can trigger full-domain resync for Second Brain and Homelab while S3-compatible is still under development.

## Out of Scope

- Direct writes to the local Obsidian Vault.
- Replacing n8n as the webhook/event source.
- Broad production deployment automation beyond the queue/worker runtime contract.
- Reworking unrelated Homelab or Finance ingestion paths.
- Implementing the S3-compatible daemon itself.

## Priority

High after Epic 5 and Epic 7 go-live-critical work.

## Success Criteria

- Webhook requests do not perform S3 download, chunking, embedding, or vector writes inline.
- Webhook route validates the event and returns `202 Accepted` after enqueueing or persisting a durable job.
- Worker retries rate-limited provider calls without blocking API request threads.
- Delete events remove stale Second Brain documents and chunks from RAG results.
- S3-compatible events trigger full root resync and remove stale derived RAG rows for Second Brain and Homelab.
- Job status and deletion behavior are covered by integration tests.
- Validation matrix, architecture/source-of-truth docs, and changelog are reconciled.

## Risks

- Queue persistence and retry semantics can duplicate work if idempotency is weak.
- Delete sync can remove valid chunks if source keys are mapped incorrectly.
- Provider rate limits can still backlog workers without visibility and retry controls.
- Async processing changes webhook response semantics and requires updated tests/UAT.

## Dependencies

- CTX-204 current synchronous webhook sync remains the baseline behavior.
- Epic 5 Audit & Permissions should authorize `second_brain.index_external_source` for webhook clients such as n8n and audit enqueue/worker decisions.
- Epic 7 should consume stale-index and citation metadata consistently.

## Verification Plan

- Unit tests for event classification, idempotency keys, and delete-key mapping.
- Integration tests for webhook enqueue returning `202 Accepted`.
- Worker tests with fake S3/object store and fake embedder covering create/update/delete.
- PostgreSQL/pgvector integration proof that deleted documents/chunks no longer appear in RAG search.
- Failure tests for provider rate limits/retries and dead-letter or failed job status.

## Completion Summary

- CTX-801 and CTX-802 are verified.
- CTX-803 is verified: `POST /api/webhooks/s3` authenticates with `X-Cortex-S3-Token`, validates S3-compatible event domains and optional paths against configured roots, triggers full root resync for `second_brain` or `homelab`, and deletes stale derived RAG rows when files disappear.
- Webhook handling now authenticates and persists a Second Brain ingestion job before returning `202 Accepted`; object download, chunking, embedding, and vector writes happen through the worker execution path.
- Added PostgreSQL-backed ingestion job table and SQLite/PostgreSQL repository support using explicit job metadata columns.
- Delete events such as `s3:ObjectRemoved:*` remove matching `secondbrain_documents` and `secondbrain_document_chunks` records from the active RAG index.
- Verification passed with focused S3-compatible job/delete tests, focused S3-compatible webhook tests, API runtime test, full Python AI suite, full Go backend suite, script syntax check, and `git diff --check`.
- Remaining Epic 8 slice: CTX-709 eval replay and E2E chat proof.
