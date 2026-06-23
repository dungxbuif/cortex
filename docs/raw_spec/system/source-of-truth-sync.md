---
type: Specification
title: "System Spec: Source of Truth & Sync Policy"
description: "Đặc tả canonical source, derived source, capture buffer, mirror, sync lifecycle và conflict policy cho các module Cortex."
timestamp: 2026-06-16T00:00:00Z
---

# System Spec: Source of Truth & Sync Policy

## 1. Mục tiêu

Mỗi module phải khai báo dữ liệu nào là canonical, dữ liệu nào chỉ là derived/index/cache, và Cortex được phép ghi vào đâu. Đây là nền tảng để tránh nhầm DB tạm, RAG index hoặc mirror thành nguồn chính.

## 2. Source Types

```text
canonical_source
capture_buffer
mirror_snapshot
metadata_index
search_index
rag_index
audit_log
external_provider
```

Ý nghĩa:

- `canonical_source`: nơi dữ liệu chính thức sống.
- `capture_buffer`: nơi lưu tạm input/draft trước khi vào canonical.
- `mirror_snapshot`: bản copy từ external source để app đọc/index.
- `metadata_index`: metadata parse từ source.
- `search_index`: full-text index.
- `rag_index`: embeddings/chunks dùng cho RAG.
- `audit_log`: event history.
- `external_provider`: API/service ngoài app.

## 3. Module Declarations

### 3.1. Finance

```yaml
module: finance
canonical_source: cortex_postgresql
capture_buffer: optional_transaction_drafts
mirror_snapshot: none
metadata_index: optional_reporting_cache
rag_index: optional_finance_insights
write_policy:
  chat_write: allowed_via_finance_domain_api
  external_write: denied_by_default
  confirmation: required_for_ambiguous_or_high_impact
sync_policy:
  import_csv: allowed
  provider_sync: future_scope
```

### 3.2. Second Brain

```yaml
module: second_brain
canonical_source: local_obsidian_vault_second_brain_folder
capture_buffer: cortex_capture_inbox_db
mirror_snapshot: future_cli_or_plugin_or_git_or_upload_snapshot
metadata_index: cortex_db
rag_index: indexed_vault_documents_only
write_policy:
  chat_capture: allowed_to_capture_db
  direct_vault_write: denied_current_scope
  external_write: denied_current_scope
sync_policy:
  vault_to_app: minio_mirror_webhook_or_future_mechanism
  app_to_vault: manual_export_by_user
```

### 3.3. Homelab

```yaml
module: homelab
canonical_source: github_repo_dungxbuif_homelab
capture_buffer: none
mirror_snapshot: app_git_mirror
metadata_index: cortex_db
rag_index: redacted_indexed_repo_documents
write_policy:
  chat_write: denied
  repo_write: denied
  runtime_action: denied
sync_policy:
  github_webhook: verify_then_enqueue
  git_pull: allowed_by_sync_worker
  index_after_redaction: required
```

## 4. Generic Lifecycle

```text
Raw input or external change
  -> capture buffer or sync trigger
  -> normalization/parser
  -> validation/security scan
  -> canonical write or mirror update
  -> metadata/search/RAG index
  -> audit events
```

Not every module uses every stage.

## 5. Conflict Policy

When derived data conflicts with canonical source:

- Canonical source wins.
- Derived index is stale and must be reindexed.
- RAG answer must prefer canonical-backed chunks.
- If two canonical-looking sources conflict, report conflict instead of guessing.

Examples:

- Second Brain: Vault file wins over Capture Inbox record.
- Homelab: latest indexed Git commit wins over stale mirror metadata.
- Finance: transaction table wins over cached report.

## 6. Deletion Policy

- Canonical deletion should be represented as tombstone or soft-delete when possible.
- Index deletion follows canonical deletion after sync.
- Audit events are not deleted through normal APIs.
- Capture buffer records may be discarded, but discard is audited.

## 7. Sync Safety Rules

- Webhooks enqueue work; they do not run heavy sync inline.
- Sync job records source revision, content hash and indexed revision.
- Indexing must be idempotent by source revision + path + content hash.
- External docs/config must pass redaction before embedding.
- Sync failures must not corrupt last good index.

## 8. Current Cortex Implementation Notes

- Second Brain MinIO/S3 webhook handling persists a `secondbrain_ingestion_jobs` row and returns `202 Accepted`; object fetch, chunking, embedding, and vector writes are handled by the worker execution path.
- Second Brain object delete events are represented as ingestion jobs with `event_type = delete`; worker processing removes matching documents and chunks from active RAG tables.
- Active Second Brain RAG content remains in PostgreSQL + pgvector tables (`secondbrain_documents`, `secondbrain_document_chunks`); ingestion jobs store only event metadata and processing status.
