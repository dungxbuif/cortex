---
type: Specification
title: "System Spec: Capability & Permission Policy"
description: "Đặc tả capability model và policy enforcement cho module APIs, tool calls, sync, write và read-only boundaries."
timestamp: 2026-06-16T00:00:00Z
---

# System Spec: Capability & Permission Policy

## 1. Mục tiêu

Permission Policy xác định Cortex được phép đọc, capture, ghi DB, sync, index hoặc thao tác external source ở đâu. Policy được enforce bởi Orchestrator trước mọi tool/API call.

## 2. Capability Vocabulary

```text
read
rag_query
capture
write_app_db
write_external_source
sync_from_external
index_external_source
execute_runtime_action
manage_policy
```

Ý nghĩa:

- `read`: đọc dữ liệu đã được module expose.
- `rag_query`: hỏi đáp trên indexed knowledge.
- `capture`: lưu raw input vào buffer/draft.
- `write_app_db`: ghi vào database của Cortex.
- `write_external_source`: ghi vào source ngoài app như Vault/Git repo/provider.
- `sync_from_external`: pull/sync dữ liệu từ source ngoài vào mirror.
- `index_external_source`: parse/redact/index dữ liệu đã sync.
- `execute_runtime_action`: chạy thao tác có side effect ngoài app.
- `manage_policy`: thay đổi quyền/policy.

## 3. Module Capability Matrix

| Module | read | rag_query | capture | write_app_db | write_external_source | sync_from_external | index_external_source | execute_runtime_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Finance | Yes | Optional | Draft/import | Yes | No by default | Future provider sync | Optional | No |
| Second Brain | Yes | Yes | Yes | Capture/metadata only | No | Future Vault sync | Yes | No |
| Homelab | Yes | Yes | No | Sync/index metadata only | No | Git pull/webhook | Yes | No |

## 4. Policy Decisions

Policy decision output:

```json
{
  "allowed": true,
  "decision": "allow",
  "required_confirmation": false,
  "reason": "finance write_app_db allowed via CreateTransaction",
  "policy_id": "finance.write.transaction.v1"
}
```

Decision types:

- `allow`
- `deny`
- `require_confirmation`
- `require_clarification`
- `require_manual_action`

## 5. Write Policy

Writes are allowed only when all conditions are true:

- Module declares the required capability.
- Target API accepts writes.
- Input passes validation.
- Source-of-truth policy allows the target store.
- Required confirmation is satisfied.
- Audit event can be recorded.

Examples:

- Finance transaction: allowed through Finance API.
- Second Brain chat note: allowed only into Capture Inbox DB.
- Second Brain Vault markdown edit: denied in current scope.
- Homelab markdown/config edit: denied.
- Homelab runtime action: denied.

## 6. Confirmation Policy

Confirmation required when:

- Money movement or balance-impacting write.
- Category/wallet/date/entity mapping confidence is low.
- User intent is ambiguous.
- Operation may create duplicates.
- Import/update touches many records.
- Policy marks tool as high impact.

Confirmation is not a substitute for permission. If capability is denied, confirmation cannot override it.

## 7. Read-Only Boundaries

Hard read-only boundaries:

- Homelab chat cannot edit repo, create patch, commit, push or execute commands.
- Second Brain chat cannot write directly to local Obsidian Vault.
- RAG/indexing services cannot expose raw secrets.

For denied write requests, response should provide:

- Boundary reason.
- Relevant source path or module API if useful.
- Manual next step for user.

## 8. Audit Requirements

Every policy decision for write/sync/index/RAG must produce an audit event:

- `PermissionAllowed`
- `PermissionDenied`
- `ConfirmationRequested`
- `ConfirmationAccepted`
- `ConfirmationRejected`

Audit must include module, tool, capability, actor, request id and policy id.
