---
type: Specification
title: "System Spec: Orchestrator & Tool Runtime"
description: "Đặc tả Cortex Runtime chịu trách nhiệm điều phối chat, LLM, tool calls, permission policy, module APIs và response synthesis."
timestamp: 2026-06-16T00:00:00Z
---

# System Spec: Orchestrator & Tool Runtime

## 1. Mục tiêu

Orchestrator là tầng điều phối giữa Chat UI, LLM provider, Tool Registry, Permission Policy, RAG service và các module APIs.

Orchestrator không chứa business logic của Finance, Second Brain hoặc Homelab. Nó chỉ hiểu intent, chọn tool hợp lệ, gọi API đúng quyền, xử lý kết quả và tổng hợp phản hồi.

Implementation owner: Orchestrator is implemented in Python. It may call Go API-heavy/domain services and Python AI services through internal gRPC contracts. This keeps LLM/provider/tooling close to Python's AI ecosystem while preserving Go for deterministic API-heavy components.

## 2. Responsibilities

- Nhận request OpenAI-compatible từ Open WebUI.
- Chuẩn hóa session, user id, conversation id và request metadata.
- Nạp policy theo user/module/tool.
- Chọn tool definitions hợp lệ cho request.
- Gọi LLM provider để reasoning/tool selection.
- Validate tool call arguments trước khi thực thi.
- Check capability/permission trước khi gọi tool adapter.
- Gọi domain API hoặc system service.
- Ghi audit/event cho tool call, permission deny, RAG query, sync/index.
- Gửi kết quả tool về LLM để tổng hợp answer.
- Trả Markdown response cho Open WebUI.

## 3. Non-Responsibilities

- Không quyết định business rule của Finance.
- Không ghi trực tiếp Obsidian Vault.
- Không edit Homelab repo.
- Không chạy runtime infra action.
- Không bỏ qua permission policy.
- Không tự lưu dữ liệu canonical khi module không cho phép.

## 4. Runtime Flow

```text
Open WebUI request
  -> API Proxy
  -> Session loader
  -> Policy context loader
  -> Context planner
  -> Tool definition builder
  -> LLM call
  -> Tool call parser
  -> Permission check
  -> Tool adapter
  -> Module/System API
  -> Audit/event
  -> LLM synthesis
  -> Markdown response
```

## 5. Tool Registry Contract

Mỗi tool definition phải khai báo:

```json
{
  "name": "finance_create_transaction",
  "module": "finance",
  "target_api": "CreateTransaction",
  "required_capabilities": ["write_app_db"],
  "confirmation": "required_when_ambiguous_or_high_impact",
  "input_schema": {},
  "output_schema": {},
  "idempotency": "client_request_id",
  "audit_event": "FinanceTransactionCreated"
}
```

Required fields:

- `name`: tool name exposed to LLM.
- `module`: owning module or system service.
- `target_api`: domain/system API to call.
- `required_capabilities`: capability list enforced before call.
- `input_schema`: structured validation schema.
- `output_schema`: expected structured output.
- `confirmation`: none, required, conditional.
- `audit_event`: event emitted after success/failure.

## 6. Tool Call Rules

- Tool arguments must be schema-validated.
- Missing required data returns `needs_clarification`, not a guessed write.
- Low confidence category/entity/date mapping must ask user.
- Write operations must include idempotency key.
- Tool results returned to LLM must be structured and safe to render.
- Sensitive fields must be redacted before entering LLM context.

## 7. Context Planning

Orchestrator decides context sources by intent:

- Finance report: call Finance query APIs; RAG optional.
- Finance write: no RAG unless needed for category/policy help.
- Second Brain question: use RAG/indexed Vault documents.
- Second Brain capture: create Capture Inbox record, no RAG ingestion.
- Homelab question: use Homelab indexed repo RAG.
- Homelab edit/action request: refuse action boundary, provide guidance/source paths only.

## 8. Error Handling

Standard response states:

- `success`
- `needs_clarification`
- `needs_confirmation`
- `permission_denied`
- `validation_error`
- `not_found`
- `conflict`
- `external_sync_pending`
- `system_error`

Every error should include:

- `code`
- `message`
- `retryable`
- `safe_user_message`
- `audit_event_id`

## 9. Module Boundary

Orchestrator may call:

- Finance domain APIs.
- Second Brain domain APIs.
- Homelab domain APIs.
- RAG/Indexing service APIs.
- Sync service APIs.
- Audit/Event APIs.
- Permission Policy APIs.

Orchestrator must not bypass these APIs to write DB/files directly.
