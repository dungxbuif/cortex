---
type: Specification
title: "System Spec: Audit & Event Model"
description: "Đặc tả event model chung cho Cortex, dùng cho audit, debug, lineage, sync/index tracking và permission decisions."
timestamp: 2026-06-16T00:00:00Z
---

# System Spec: Audit & Event Model

## 1. Mục tiêu

Audit/Event Model là hạ tầng chung để ghi lại những gì Cortex đã đọc, sync, index, gọi tool, ghi dữ liệu, deny quyền hoặc yêu cầu confirmation.

Event log giúp:

- Debug lỗi hệ thống.
- Truy vết data lineage.
- Xem lịch sử sync/index.
- Kiểm tra permission decisions.
- Review các write quan trọng.
- Phục hồi hoặc so sánh trạng thái.

## 2. Event Contract

```json
{
  "event_id": "evt_...",
  "event_type": "FinanceTransactionCreated",
  "module": "finance",
  "actor_type": "user|system|scheduler|webhook",
  "actor_id": "user_id",
  "conversation_id": "chat_id",
  "request_id": "req_id",
  "tool_name": "finance_create_transaction",
  "capability": "write_app_db",
  "source_ref": {},
  "target_ref": {},
  "status": "success|failed|denied|skipped",
  "metadata": {},
  "created_at": "2026-06-16T00:00:00Z"
}
```

## 3. Event Categories

### 3.1. Runtime Events

- `ChatRequestReceived`
- `ToolCallRequested`
- `ToolCallValidated`
- `ToolCallExecuted`
- `ToolCallFailed`
- `ResponseSynthesized`

### 3.2. Permission Events

- `PermissionAllowed`
- `PermissionDenied`
- `ConfirmationRequested`
- `ConfirmationAccepted`
- `ConfirmationRejected`

### 3.3. Sync & Index Events

- `SyncJobQueued`
- `SyncJobStarted`
- `SyncJobCompleted`
- `SyncJobFailed`
- `DocumentParsed`
- `DocumentIndexed`
- `DocumentSkipped`
- `IndexChunkCreated`
- `IndexChunkSkipped`
- `SecretFindingDetected`
- `RedactionApplied`
- `RagQueryExecuted`

### 3.4. Finance Events

- `FinanceTransactionCreated`
- `FinanceTransactionUpdated`
- `FinanceTransactionDeleted`
- `FinanceWalletCreated`
- `FinanceBudgetCreated`
- `FinanceAssetValuationUpdated`
- `FinanceImportCompleted`

### 3.5. Second Brain Events

- `CaptureCreated`
- `CaptureUpdated`
- `CaptureMarkedCopied`
- `CaptureMarkedExported`
- `CaptureDiscarded`
- `VaultSyncStarted`
- `VaultSyncCompleted`
- `KnowledgeDocumentIndexed`

### 3.6. Homelab Events

- `HomelabWebhookReceived`
- `HomelabRepoSyncQueued`
- `HomelabRepoSynced`
- `HomelabDocumentIndexed`
- `HomelabDocumentSkipped`
- `HomelabSecretFindingDetected`
- `HomelabIndexRedactionApplied`
- `HomelabRagQueryExecuted`

## 4. Audit Rules

- Audit log should be append-only.
- Normal APIs must not hard-delete audit events.
- Secret values must never be written to audit metadata.
- Store references/hashes instead of raw sensitive payloads.
- Failed and denied operations are audited.
- RAG queries are audited with source refs, not full private answer text by default.

## 5. Data Lineage

Events should connect:

```text
sync job
  -> source revision
  -> parsed document
  -> redacted chunk
  -> index record
  -> RAG query
  -> answer citation
```

For Finance writes:

```text
chat request
  -> tool call
  -> permission decision
  -> confirmation if any
  -> domain API write
  -> created/updated entity id
```

For Second Brain capture:

```text
chat request
  -> capture created
  -> user copied/exported manually
  -> future vault sync
  -> indexed document
```

## 6. API Surface

- `AppendEvent(command)`.
- `ListEvents(query)`.
- `GetEvent(event_id)`.
- `ListEventsByRequest(request_id)`.
- `ListEventsBySource(source_ref)`.
- `ListModuleTimeline(module, filters)`.
- `GetAuditSummary(query)`.
