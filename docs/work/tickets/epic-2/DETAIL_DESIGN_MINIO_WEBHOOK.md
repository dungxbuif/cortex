---
artifact_type: detail_design
id: DESIGN-CTX-204-MINIO-WEBHOOK
status: done
owner: ai
approval: approved
human_fields:
  - approval
  - constraints
  - scope_decisions
ai_fields:
  - problem
  - context_loaded
  - brownfield_scope
  - proposed_approach
  - design_tradeoffs
  - architecture_overview
  - execution_flow
  - api_data_model
  - security
  - test_plan
  - reconciliation_plan
shared_fields:
  - status
  - trace
  - small_task_exemption
trace:
  backlog_item: BL-010
  requirement: REQ-009
  phase: docs/work/phases/PHASE-2-second-brain.md
  ticket_or_bug: docs/work/tickets/epic-2/CTX-204.md
  test_verification: docs/work/tickets/epic-2/CTX-204.md#verification-results
  validation_matrix: docs/work/VALIDATION_MATRIX.md
  docs_review: docs/work/tickets/epic-2/CTX-204.md#docs-review
  adrs: []
  master_docs_touched:
    - docs/raw_spec/modules/second-brain.md
    - docs/raw_spec/system/source-of-truth-sync.md
    - docs/raw_spec/system/external-automation.md
    - docs/architecture/API.md
    - docs/architecture/ARCHITECTURE.md
---

# DETAIL DESIGN: Second Brain Obsidian MinIO Webhook Sync

## Status

- ID: DESIGN-CTX-204-MINIO-WEBHOOK
- Status: done
- Ticket: CTX-204
- Approval: approved by user instruction to complete implementation and local S3 simulation
- Author: Codex
- Updated: 2026-06-18
- Sprint anchor: branch `feat/obsidian-sync`, commit `79c501e4c67a12a1dfdf9d7af351edf7a549e6cc`

## 1. Context & Scope

### Problem Statement

Obsidian sync writes Second Brain Markdown content into a MinIO-compatible bucket. Cortex needs a webhook-driven ingestion path that indexes only objects under the `second-brain/` prefix so RAG/search reflects the latest Obsidian content without Cortex writing directly to the Vault.

Success outcome:

- An authenticated webhook can trigger indexing for `second-brain/**/*.md`.
- Cortex fetches object content from MinIO using configured credentials and passes Markdown to the existing `SecondBrainService.index_vault_document`.
- Objects outside `second-brain/` and non-Markdown objects are skipped.
- Replayed webhook events are idempotent through existing checksum behavior.

### Context Loaded

- `docs/CONTEXT.md`
- `docs/work/BACKLOG.md`
- `docs/standards/README.md`
- `docs/standards/QUALITY_BAR.md`
- `docs/standards/VALIDATION.md`
- `docs/standards/CODE.md`
- `docs/standards/TESTING.md`
- `docs/standards/DOCS.md`
- `docs/raw_spec/spec.md`
- `docs/raw_spec/modules/second-brain.md`
- `docs/raw_spec/system/source-of-truth-sync.md`
- `docs/raw_spec/system/rag-indexing.md`
- `docs/raw_spec/system/external-automation.md`
- `docs/work/phases/PHASE-2-second-brain.md`
- `docs/work/tickets/epic-2/CTX-201.md`
- `docs/work/tickets/epic-2/CTX-202.md`
- `docs/work/tickets/epic-2/CTX-203.md`
- `docs/work/tickets/epic-2/DETAIL_DESIGN.md`
- `src/ai_service/secondbrain/service.py`
- `src/ai_service/secondbrain/repository.py`
- `src/ai_service/api.py`
- `src/backend/internal/modules/ai/handler.go`
- `src/proto/cortex.proto`

### Brownfield Scope

Touched modules/files expected:

- `src/ai_service/secondbrain/` for MinIO object fetch and sync orchestration.
- `src/ai_service/grpc_server.py` and generated Python proto files if the Go gateway calls Python through gRPC.
- `src/proto/cortex.proto` for a Second Brain sync RPC.
- `src/backend/internal/modules/ai/handler.go` or a new webhook package for the HTTP endpoint.
- `src/backend/internal/config/config.go` for webhook token and MinIO/runtime settings if config is Go-owned.
- Focused tests under `src/ai_service/tests/` and `src/backend/internal/modules/ai/`.

Direct dependencies inspected:

- Existing Second Brain indexing service and repository.
- Existing Go-to-Python gRPC gateway route style.
- External automation webhook security spec.

Contracts affected:

- New webhook HTTP endpoint.
- Optional new gRPC request/response for Second Brain object sync.
- Runtime environment variables for MinIO credentials/bucket and webhook token.

Known unknowns:

- Exact webhook payload shape from n8n/MinIO is not supplied yet.
- Whether the webhook is emitted by n8n or MinIO notification directly is not final.
- Credential names and bucket name will be supplied by the human.
- Full async queue infrastructure does not exist yet.

Scope expansion reason:

- The user requested webhook-driven sync from MinIO; this necessarily crosses API, security, runtime config, external object storage, and RAG indexing.

### Small Task Exemption

- Small task exemption: no
- Reason: This changes external integration, public/internal API contract, credential handling, runtime configuration, and indexing behavior.
- Impact checked: API=yes, DB=no, Security=yes, Runtime=yes, Standards=no

## 2. Design Considerations & Trade-offs

| Consideration / Alternative | Pros | Cons | Decision |
| --- | --- | --- | --- |
| Webhook indexes synchronously in request | Simple to implement and easy to verify locally | Violates sync safety guidance for heavy jobs; embedding can exceed request timeout | Rejected as the long-term shape; acceptable only for a bounded v1 handler if documented as temporary and timeout-safe |
| Webhook records/enqueues job, worker indexes later | Matches source-of-truth sync rules and scales better | Requires job table/queue not currently present | Preferred target; if implementation needs to stay narrow, simulate enqueue through a service boundary and keep HTTP handler thin |
| Go fetches MinIO object and sends Markdown to Python | Keeps HTTP/webhook in Go | Moves object storage credential handling and content transport into Go; duplicates indexing concerns | Rejected unless Python cannot own MinIO client |
| Python fetches MinIO object and indexes | Keeps RAG/indexing and provider-specific object parsing in AI service | Requires Go-to-Python sync RPC and Python runtime config | Chosen |
| Use official MinIO SDK | Better compatibility with MinIO APIs | Adds dependency and requires approval/ADR if major | Rejected for this slice; local filesystem-backed S3 simulation avoids a new dependency while preserving the bucket/key contract |

## 3. Architecture Overview

```text
------------------------+
| n8n or MinIO webhook  |
+-----------+------------+
            |
            v
+------------------------+
| Go Gateway             |
| /api/webhooks/...      |
| - token validation     |
| - prefix validation    |
| - thin request mapping |
+-----------+------------+
            |
            v gRPC
+------------------------+
| Python AI Service      |
| SecondBrainService     |
| - fetch MinIO object   |
| - validate key/prefix  |
| - index markdown       |
+-----------+------------+
            |
            v
+------------------------+
| PostgreSQL + pgvector  |
| secondbrain_documents  |
| secondbrain_chunks     |
+------------------------+
```

### Component Responsibilities

| Component | Role |
| --- | --- |
| Go webhook handler | Authenticates webhook, validates basic payload, maps to gRPC, returns accepted/skipped/error response. |
| Python Second Brain sync adapter | Fetches object content from MinIO-compatible storage, validates prefix/type, calls existing document indexing pipeline. |
| Existing SecondBrainService | Owns Markdown parsing, checksum idempotency, chunking, embedding, and repository writes. |
| Repository | Persists document/chunk metadata; no schema change expected for v1. |

## 4. Execution Flow

1. Webhook caller sends object event to `POST /api/webhooks/n8n/secondbrain/obsidian-sync` or the approved equivalent.
2. Go validates `X-Cortex-N8n-Token` or the approved webhook token header.
3. Go extracts bucket, object key, event id, owner id, and optional content metadata.
4. Go rejects or skips invalid keys that do not start with `second-brain/`.
5. Go calls Python `SecondBrainService.SyncMinIOObject`.
6. Python validates bucket/key against configured allow-list.
7. Python fetches the object content using configured MinIO endpoint and credentials.
8. Python skips non-Markdown objects and indexes Markdown through `index_vault_document`.
9. Existing checksum logic returns zero chunks for unchanged content.
10. Response reports `indexed`, `skipped`, or `failed` with processed/skipped/failed counts.

## 5. API & Data Model Design

### API Changes

Proposed HTTP endpoint:

- Endpoint: `POST /api/webhooks/n8n/secondbrain/obsidian-sync`
- Headers:
  - `X-Cortex-N8n-Token: <token>`
- Request:

```json
{
  "bucket": "human-supplied-bucket",
  "object_key": "second-brain/wiki/example.md",
  "event_id": "optional-source-event-id",
  "owner_id": "owner"
}
```

- Response:

```json
{
  "status": "indexed|skipped|failed",
  "processed_files": 1,
  "skipped_files": 0,
  "failed_files": 0,
  "object_key": "second-brain/wiki/example.md",
  "message": "indexed 4 chunks"
}
```

Proposed gRPC addition:

```proto
rpc SyncSecondBrainObject(SyncSecondBrainObjectRequest) returns (SyncSecondBrainObjectResponse);

message SyncSecondBrainObjectRequest {
  string bucket = 1;
  string object_key = 2;
  string event_id = 3;
  string owner_id = 4;
}

message SyncSecondBrainObjectResponse {
  string status = 1;
  int32 processed_files = 2;
  int32 skipped_files = 3;
  int32 failed_files = 4;
  string object_key = 5;
  string message = 6;
}
```

### Data Model Changes

- Schema migration needed: no for the narrow v1 path.
- Existing tables affected:
  - `secondbrain_documents`
  - `secondbrain_document_chunks`
- Optional future table:
  - `sync_jobs` for durable async processing. Not included unless approval expands scope.

### Runtime Configuration

Implemented environment variables:

- `SECOND_BRAIN_MINIO_BUCKET`
- `SECOND_BRAIN_MINIO_PREFIX=second-brain/`
- `SECOND_BRAIN_MINIO_LOCAL_ROOT`
- `CORTEX_N8N_API_KEY` or a more specific webhook token

## 6. Security & Authorization

- Authentication changes: add webhook token validation for the new route.
- Authorization / permissions: if CTX-501/CTX-502 policy service is available, evaluate `second_brain.index_external_source`; otherwise the handler must keep a documented local guard and leave a TODO trace to wire policy.
- Data privacy: MinIO credentials must be read from environment/config only and never logged, returned, or persisted.
- Input validation:
  - Require non-empty bucket and object key.
  - Object key must be normalized and start with `second-brain/`.
  - Reject path traversal markers such as `..`.
  - Skip non-`.md` objects.
  - Enforce configured bucket allow-list.
- Source-of-truth: MinIO is treated as a mirror/snapshot of Obsidian, not canonical knowledge authoring storage.

## 7. Implementation & Verification Plan

### Impacted Areas

- Code/modules: Go AI/webhook handler, proto/gRPC, Python Second Brain service.
- Product behavior: Second Brain RAG can be refreshed by Obsidian sync events.
- API/contracts: new webhook endpoint and possibly new gRPC RPC.
- Data/schema: no migration expected.
- Security/auth: webhook token and object key validation.
- Deployment/runtime: MinIO config/env vars.
- Docs: requirements, architecture, API, validation matrix, context, changelog.

### Test Plan

- Unit:
  - object key prefix validation accepts only `second-brain/**/*.md`.
  - webhook auth rejects missing/wrong token.
  - sync service skips non-Markdown and out-of-prefix objects.
- Integration:
  - fake MinIO object store returns Markdown; service indexes it and search/status reflect new document.
  - replay with same content returns skipped/no duplicate chunks through checksum behavior.
- E2E:
  - Go route with fake gRPC server verifies request mapping and auth behavior.
  - Optional local runtime E2E after credentials are supplied.
- UAT:
  - Manual curl or n8n workflow sends a real/simulated webhook for one object under `second-brain/`.
  - Verify `/api/secondbrain/status` or search returns indexed content.
- Manual/platform:
  - Record env var names used, with secrets redacted.
- Docs review:
  - Required after implementation.

Expected commands:

```bash
cd src/backend && go test ./internal/modules/ai/...
cd src/backend && go test ./...
PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v
git diff --check
```

### Validation Matrix Impact

- Update required: yes
- Row: CTX-204 implemented.

### Verification Results

- Command: `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v`
- Result: pass, 30 tests OK, 1 Google smoke skipped by opt-in flag.
- Notes: Full Python AI service suite covers local S3 simulation, Second Brain service behavior, gRPC runtime, PostgreSQL integrations, Homelab, and API runtime.

- Command: `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...`
- Result: pass.
- Notes: Full backend suite covers Go webhook auth/proxy behavior and existing Finance/Gateway tests.

- Command: `rtk git diff --check`
- Result: pass.
- Notes: No whitespace errors.

## 8. Reconciliation Plan

- Requirements docs: updated.
- Architecture docs: updated.
- API docs: updated.
- ERD docs: no change; no schema change.
- SDD docs: not needed; high-level runtime boundary is unchanged.
- ADR: not needed; MinIO remains a mirror/snapshot and no major dependency was added.
- Context: updated.

### Docs Review Checklist

- Code changed but docs unchanged reason: docs updated.
- Requirements updated or not needed reason: updated `docs/requirements/REQUIREMENTS.md`.
- Architecture updated or not needed reason: updated `docs/architecture/ARCHITECTURE.md`.
- API updated or not needed reason: updated `docs/architecture/API.md`.
- ERD/data updated or not needed reason: no schema change expected; revisit after implementation.
- SDD updated or not needed reason: not needed; high-level architecture boundary is unchanged.
- ADR created or not needed reason: not needed; follows existing MinIO mirror/source-of-truth policy.

## Completion

Implementation is complete for the local S3/MinIO simulation slice. Real MinIO network credentials can be wired later behind the same bucket/key contract if needed.
