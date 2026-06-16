---
type: Specification
title: "Cortex System Specification - V1.0"
status: "DRAFT"
description: "Spec tổng thể cho Cortex Platform, các module cá nhân, orchestrator, permission, source-of-truth, RAG/indexing và audit/event nền."
timestamp: 2026-06-16T00:00:00Z
---

# Cortex System Specification - V1.0

> **Lộ trình:** Xem chi tiết tại [AI Roadmap](phases/index.md)

## 1. Mục tiêu (Objective)

Xây dựng Cortex như một personal AI system hoạt động qua Chat UI, có khả năng hỏi đáp, capture, phân tích và thao tác có kiểm soát trên các module cá nhân.

3 module đầu tiên:

- [Finance Module](modules/finance.md): quản lý tài chính cá nhân, dòng tiền, tài sản, ngân sách, nợ và báo cáo.
- [Second-Brain Module](modules/second-brain.md): quản lý tri thức cá nhân dựa trên Obsidian Vault, capture inbox và RAG từ Markdown.
- [Homelab Module](modules/homelab.md): hỏi đáp read-only trên repo Homelab đã pull/index, không chat-to-edit.

Cortex dùng kiến trúc modular monolith bằng Go, expose OpenAI-compatible API cho Open WebUI, điều phối LLM/tool calls ở tầng runtime, và gọi vào các module thông qua domain APIs ổn định.

## 2. System Spec Index

Root spec này là bản tổng thể. Các spec nền:

- [Orchestrator & Tool Runtime](system/orchestrator.md)
- [Capability & Permission Policy](system/permission-policy.md)
- [Source of Truth & Sync Policy](system/source-of-truth-sync.md)
- [RAG & Indexing Service](system/rag-indexing.md)
- [Audit & Event Model](system/audit-events.md)

Module specs:

- [Finance](modules/finance.md)
- [Second Brain](modules/second-brain.md)
- [Homelab](modules/homelab.md)

## 3. Kiến trúc Hệ thống (System Architecture)

Hệ thống xoay quanh 4 luồng tương tác chính:

1. **User <-> Open WebUI:** Giao diện người dùng duy nhất, hỗ trợ chat, quản lý lịch sử, render Markdown/UI đẹp mắt.
2. **Open WebUI <-> Go Backend:** Open WebUI gọi Go Backend qua chuẩn OpenAI API (`/v1/chat/completions`). Go Backend đóng vai trò API proxy và Cortex Runtime.
3. **Go Backend <-> LLM Provider:** Runtime gọi model thật để reasoning, intent extraction, tool choice và response synthesis.
4. **Go Backend <-> Module APIs / System Services:** Runtime gọi domain APIs, RAG/indexing, sync, audit, permission, database, Git mirror hoặc external integrations.

Luồng chuẩn:

```text
Chat / Open WebUI
  -> OpenAI-compatible API Proxy
  -> Cortex Runtime / Orchestrator
  -> Capability & Permission Policy
  -> Tool Adapter / Module API
  -> Domain Service / System Service
  -> Canonical Store / Mirror / DB / RAG Index
```

### 3.1. Module Boundary Principle

Các module nghiệp vụ như Finance, Second-Brain và Homelab chỉ tập trung expose **domain APIs** ổn định. Module không phụ thuộc vào LLM, prompt, ReAct loop, OpenAI tool-call schema, chat history, hoặc quyết định tool nào cần gọi.

Các layer phía trên chịu trách nhiệm điều phối AI:

- **Cortex Runtime / Orchestrator:** hiểu intent, trích xuất tham số, hỏi lại khi thiếu dữ liệu, điều phối nhiều bước.
- **Tool Adapter / Tool Registry:** map tool-call schema sang domain API tương ứng.
- **Presentation Adapter:** format kết quả domain API thành Markdown/chat response phù hợp với Open WebUI.
- **Permission Policy:** kiểm tra quyền read/capture/write/sync/index trước khi gọi API.
- **Audit/Event Service:** ghi nhận mọi sync, index, tool call, write, deny và RAG query quan trọng.

Nguyên tắc này giúp domain module test được độc lập, dễ thay LLM, dễ thêm UI khác ngoài chat, và tránh để LLM nắm business logic nhạy cảm.

## 4. Source-of-Truth Matrix

Mỗi module phải khai báo source of truth, derived source và write policy. Chi tiết ở [Source of Truth & Sync Policy](system/source-of-truth-sync.md).

| Module | Canonical source | App DB role | RAG/index source | Write policy |
| --- | --- | --- | --- | --- |
| Finance | Cortex PostgreSQL | Canonical finance store | Optional derived reports/insights | Chat có thể ghi qua Finance APIs sau validation/confirmation |
| Second Brain | Local Obsidian Vault `second-brain/` | Capture buffer, metadata, sync state, index | Indexed Vault mirror only | Chat chỉ capture vào DB; không ghi trực tiếp Vault |
| Homelab | GitHub repo `dungxbuif/Homelab` | Mirror state, metadata, index | Pulled/redacted repo mirror | Chat read-only; app chỉ pull Git và update RAG |

## 5. Capability Model

Cortex không suy luận quyền theo tên module. Mỗi module khai báo capability rõ ràng, Orchestrator enforce qua [Capability & Permission Policy](system/permission-policy.md).

| Capability | Finance | Second Brain | Homelab |
| --- | --- | --- | --- |
| `read` | Yes | Yes | Yes |
| `rag_query` | Optional | Yes | Yes |
| `capture` | Draft/import only | Capture Inbox DB | No |
| `write_app_db` | Yes | Capture/metadata only | Sync/index metadata only |
| `write_external_source` | No by default | No direct Vault write | No repo write |
| `sync_from_external` | Bank/provider future | Vault mirror future | Git pull/webhook |
| `execute_runtime_action` | No | No | No |

## 6. Các thành phần Cốt lõi (Core Components - Go Backend)

### 6.1. OpenAI API Proxy & Session Management

- **Chức năng:** Lắng nghe request `/v1/chat/completions` từ Open WebUI.
- **Session/Context:** Open WebUI gửi Messages History; Go Backend tiếp nhận, nạp policy, chọn context nội bộ/RAG khi cần, gắn tool definitions hợp lệ rồi gọi LLM provider.

### 6.2. Cortex Runtime, Orchestrator & Dynamic Tool Registry

- Xem chi tiết: [Orchestrator & Tool Runtime](system/orchestrator.md).
- Registry định nghĩa tool schema, target API, required capabilities, confirmation policy và output contract.
- Mỗi tool chỉ là adapter gọi vào domain/system API, không chứa business logic.
- Orchestrator không được bỏ qua permission policy.
- Nếu thiếu dữ liệu hoặc confidence thấp, Orchestrator hỏi lại user thay vì đoán.

### 6.3. System Services

- **Permission Service:** enforce capability matrix, source-of-truth write policy và confirmation requirement.
- **RAG/Indexing Service:** parse, redact, chunk, embed, search, cite source.
- **Sync Service:** sync từ external canonical sources như Git repo hoặc Vault mirror/snapshot.
- **Audit/Event Service:** ghi event bất biến cho tool call, sync, index, write, permission deny.
- **Presentation Adapter:** render structured result thành Markdown/table phù hợp Open WebUI.

### 6.4. Modules

- **[Finance Module](modules/finance.md):**
  - Domain APIs cho transaction, wallet, category, budget, report, asset, debt, net worth.
  - Canonical data nằm trong Cortex PostgreSQL.
  - Chat có thể ghi qua Finance APIs nếu đủ dữ liệu, pass validation và confirmation khi cần.

- **[Second-Brain Module](modules/second-brain.md):**
  - Domain APIs cho capture inbox, Vault document query, sync state, tracking query, RAG/search.
  - Canonical knowledge nằm trong local Obsidian Vault `second-brain/`.
  - Chat chỉ capture vào DB buffer; không ghi trực tiếp Vault.

- **[Homelab Module](modules/homelab.md):**
  - Domain APIs cho repo sync status, docs search/RAG, link graph, service catalog, validation/security reports.
  - Canonical knowledge nằm trong GitHub repo `dungxbuif/Homelab`.
  - Chat read-only; không edit repo, không tạo patch, không commit/push, không chạy lệnh vận hành.

## 7. Data Flow Tổng Thể

```text
User message
  -> Open WebUI
  -> OpenAI-compatible API Proxy
  -> Cortex Runtime
  -> Intent + capability check
  -> Optional RAG/search context
  -> Tool/domain API call
  -> Audit/event write
  -> LLM response synthesis
  -> Markdown response to Open WebUI
```

Sync/index flow:

```text
Canonical source
  -> Sync adapter
  -> Mirror/snapshot
  -> Parser
  -> Redaction/security scan
  -> Metadata index
  -> Full-text/vector index
  -> RAG answers with citations
```

## 8. External Worker (N8n)

N8n là external automation layer, không phải nơi chứa business logic chính.

- Cron jobs: gọi webhook vào Cortex khi cần sync/check giá/crawl dữ liệu.
- Third-party integrations: OAuth, RSS, provider APIs, job orchestration.
- N8n output phải đi qua Cortex API để permission, validation và audit được áp dụng.

## 9. Technology Stack

- **Interface/Client:** **Open WebUI** (chạy Docker local).
- **Core Backend:** Go modular monolith, OpenAI-compatible API server.
- **AI Model:** Gemini/OpenAI-compatible provider tùy cấu hình.
- **Database:** PostgreSQL + pgvector.
- **Storage/Mirror:** local disk mirror, Git mirror, optional MinIO for attachment/snapshot/backup.
- **External Integration:** N8n self-hosted.

## 10. Non-Negotiable System Rules

- Module APIs không chứa prompt/tool-call/LLM reasoning logic.
- Mọi write phải có source-of-truth policy rõ ràng.
- RAG không được đọc dữ liệu capture tạm nếu module không cho phép.
- RAG answer phải có citation khi dựa vào indexed documents.
- Secret scanning/redaction phải chạy trước khi index external docs/config.
- Homelab là read-only qua chat.
- Second Brain không ghi trực tiếp local Vault trong scope hiện tại.
- Finance được phép ghi DB qua API có validation/confirmation.
- Audit/event log là cross-cutting, không để mỗi module tự định nghĩa rời rạc.
