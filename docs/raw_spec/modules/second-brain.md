---
type: Specification
title: "Module Spec: Second Brain & Personal Knowledge"
description: "Đặc tả nghiệp vụ và domain API cho Module Second Brain, quản lý tri thức cá nhân, tracking, capture inbox và RAG từ Obsidian Vault."
timestamp: 2026-06-16T00:00:00Z
---

# Module Spec: Second Brain & Personal Knowledge

> **Framework source:** [Second Brain Framework](second-brain-framework/README.md)

## 1. Mục tiêu (Objective)

Second Brain là hệ thống quản lý tri thức cá nhân dựa trên Markdown. Mục tiêu chính là giữ một thư mục `second-brain/` trong Obsidian Vault làm nơi biên soạn và lưu trữ canonical, đồng thời cho Cortex App sync/index dữ liệu đó để phục vụ search, dashboard, planning và RAG.

Nguyên tắc nền tảng:

- **Obsidian Vault `second-brain/` là canonical source of truth** cho knowledge lâu dài.
- **Markdown + YAML frontmatter** là format chính để đảm bảo portability, editability và tương thích với Obsidian/AI tools khác.
- **Database không phải nơi lưu tri thức chính thức**; database chỉ dùng cho capture buffer, metadata index, sync state, audit và search/RAG index.
- **RAG chỉ đọc dữ liệu đã được sync/index từ folder `second-brain/`**, không đọc capture DB tạm.
- **Cortex App không ghi trực tiếp vào local Obsidian Vault** trong phiên bản này. User export/copy thủ công từ Capture Inbox vào Vault.
- **Human owns knowledge**: `wiki/` là tri thức đã được người dùng biên soạn/chốt.
- **Orchestrator owns process**: LLM/tool-call layer điều phối capture, normalize, suggest, reminder; module chỉ expose domain APIs.

### 1.1. Source-of-Truth Declaration

```yaml
module: second_brain
module_type: knowledge_module
canonical_source: local_obsidian_vault_second_brain_folder
capture_buffer: cortex_capture_inbox_db
derived_sources:
  - app_side_vault_mirror_or_snapshot
  - metadata_index
  - search_index
  - rag_index
write_policy:
  chat_capture: allowed_to_capture_db
  direct_vault_write: denied_current_scope
  app_to_vault: manual_export_by_user
sync_policy:
  vault_to_app: future_cli_or_plugin_or_git_or_upload_snapshot
  rag_reads_capture_db: false
```

## 2. Storage & Source-of-Truth Model

### 2.1. Canonical Markdown Folder

Canonical source:

```text
Obsidian Vault/
  second-brain/
    raw/
    staging/
    wiki/
    tracking/
      hubs/
    dailylogs/
    archive/
    GUIDE/
    CONFIG.md
    INDEX.md
    README.md
```

Vai trò:

- `raw/`: dữ liệu gốc đã chuẩn hóa metadata, giữ nguyên nội dung nguồn.
- `staging/`: bản digest/tóm tắt/chuẩn hóa do AI hoặc workflow tạo ra.
- `wiki/`: tri thức hoàn thiện do human biên soạn.
- `tracking/`: task, project, course, habit, book, research, usecase, hub.
- `dailylogs/`: nhật ký hằng ngày.
- `archive/`: lưu raw/staging đã hoàn tất hoặc không còn active.
- `INDEX.md`: Dataview dashboard, không phải database.
- `CONFIG.md`: taxonomy, status, priority, nudge rules, inbox sources.

### 2.2. Database Roles

Database được dùng cho các vai trò phụ trợ:

- **Capture Inbox DB**: lưu note từ chat trước khi user copy/export vào Obsidian.
- **Metadata Index**: metadata parse từ frontmatter của folder `second-brain/`.
- **Sync State**: checksum, file path, last indexed time, indexing status.
- **Search/RAG Index**: full-text index, embeddings, chunk references.
- **Audit Log**: lịch sử thao tác qua Cortex App/API.

Database không được xem là canonical knowledge store.

### 2.3. MinIO Role

MinIO có thể dùng cho:

- Backup/snapshot của markdown canonical.
- Lưu attachment lớn: ảnh, PDF, audio, snapshot HTML.
- Mirror object store cho app/homelab nếu không đọc trực tiếp được Vault.

MinIO không thay thế Obsidian Vault làm nơi biên soạn chính.

## 3. Capture Inbox Model

Capture Inbox là buffer tạm cho note tạo từ chat trước khi đưa vào `second-brain/`.

Ví dụ user nói:

```text
Note lại: Consistent hashing giúp giảm key remap khi scale cache.
```

Cortex lưu vào DB capture:

```text
status: captured
source: chat
kind: raw_note
raw_text: nội dung user nói
normalized_markdown: markdown theo raw_entry template
suggested_tags: [...]
```

Capture DB lifecycle:

```text
captured -> copied -> exported -> indexed_from_vault
captured -> discarded
```

Quy tắc:

- Capture DB **không được RAG đọc**.
- Capture DB **không được xem là knowledge chính thức**.
- Capture chỉ xuất hiện trong UI nhỏ `Capture Inbox` để user review/copy/export.
- Khi note được user copy/export thủ công vào Obsidian `second-brain/`, indexer sẽ parse markdown và đưa vào metadata/search/RAG index.
- Nếu capture đã export, record giữ `vault_path`, `checksum`, `exported_at` để tránh duplicate.
- Direct write/export từ Cortex App vào local Vault không nằm trong scope hiện tại.

## 4. Capture Inbox UI

Cortex App cần một UI nhỏ để xem lại các note capture từ chat.

### 4.1. List View

Hiển thị:

- Title.
- Source: chat, manual, import.
- Suggested tags.
- Status: captured, copied, exported, discarded.
- Created time.
- Preview.

Actions:

- View detail.
- Copy Markdown.
- Download `.md`.
- Mark as copied.
- Mark as exported manually.
- Discard.

### 4.2. Detail View

Hiển thị:

- Raw text gốc.
- Normalized Markdown theo template `raw_entry.md`.
- Suggested frontmatter.
- Copy button.
- Optional: download file.

Ví dụ normalized markdown:

```markdown
---
type: Raw
title: "Consistent hashing note"
description: "Note nhanh từ chat về consistent hashing."
source: "chat"
raw_type: note
timestamp: 2026-06-16T10:30:00Z
tags: [system-design, caching]
status: raw
priority: normal
---

## Mô tả
> Note nhanh được capture từ Cortex chat.

## Nội dung gốc

Consistent hashing giúp giảm key remap khi scale cache.
```

## 5. Sync & Indexing Pipeline

Sync/indexer là cầu nối giữa Obsidian Vault và Cortex App.

Trong phiên bản hiện tại, Cortex App không có quyền ghi vào local Vault. Cơ chế đưa Vault lên app sẽ được nghiên cứu sau, có thể là CLI tool, Obsidian plugin, Syncthing mirror, Git sync, hoặc upload/sync job riêng.

```text
Local Obsidian second-brain/
  -> future sync mechanism: CLI / plugin / Syncthing / Git / upload
  -> app-side mirror or readable snapshot
  -> parse Markdown + YAML frontmatter
  -> validate framework rules
  -> update metadata DB
  -> update search index
  -> update embeddings/pgvector
  -> emit sync/index events
```

Indexer responsibilities:

- Detect created/updated/deleted/moved files.
- Parse frontmatter and body.
- Extract markdown links/backlinks.
- Extract tags/status/priority/groups/wiki_path.
- Detect duplicate by checksum/capture id if available.
- Update metadata index.
- Update full-text search.
- Update embedding chunks for RAG.
- Mark stale/broken files for review.

RAG source policy:

- Include: indexed `raw/`, `staging/`, `wiki/`, selected `tracking/` if configured.
- Exclude: Capture Inbox DB.
- Exclude: archived/deleted unless query explicitly asks.
- Prefer `wiki/` over `staging/`, and `staging/` over `raw/` when duplicates/lineage exist.

## 6. Knowledge Lifecycle

Canonical lifecycle:

```text
inbox/chat/import
  -> capture DB (optional temporary buffer)
  -> user manually copies/exports markdown
  -> raw/ in local Obsidian Vault
  -> future sync mechanism pushes Vault snapshot to app
  -> staging/
  -> wiki/ human-owned
  -> archive raw/staging when complete
```

Framework lifecycle:

- `raw`: collected source.
- `staged`: AI/human digest available.
- `reading`: human reviewing.
- `wiki`: promoted to curated knowledge.
- `deferred`: intentionally postponed.
- `archived`: no longer active but preserved.

Important:

- `wiki/` should trace back to staging/raw source when possible.
- `staging/` should not be hard-deleted after promotion; archive or mark archived.
- `raw/` should preserve source content.

## 7. Second-Brain Domain APIs

Second-Brain module expose domain APIs. It does not contain prompt logic, tool-call schema, chat history, or LLM reasoning.

### 7.1. Capture APIs

- `CreateCapture(command)`: Lưu note/chat/link vào Capture Inbox DB.
- `ListCaptures(query)`: Liệt kê captures theo status/source/tag/time.
- `GetCapture(capture_id)`: Xem capture detail.
- `RenderCaptureMarkdown(capture_id)`: Render normalized markdown từ capture.
- `MarkCaptureCopied(capture_id)`: Đánh dấu đã copy.
- `MarkCaptureExported(capture_id, vault_path, checksum)`: Đánh dấu user đã đưa capture vào Vault thủ công.
- `DiscardCapture(capture_id, reason)`: Bỏ capture.

### 7.2. Vault Document APIs

- `GetDocument(document_ref)`: Đọc markdown document từ canonical folder hoặc indexed mirror.
- `ListDocuments(query)`: Liệt kê documents từ metadata index.
- `SearchDocuments(query)`: Search theo keyword/tag/status/path.
- `GetDocumentLineage(document_ref)`: Lấy quan hệ raw -> staging -> wiki.
- `GetBacklinks(document_ref)`: Lấy backlinks/internal links.

### 7.3. Sync APIs

- `RunSync(command)`: Chạy sync/index từ app-side mirror/snapshot.
- `GetSyncStatus(query)`: Xem trạng thái sync/index.
- `ReindexDocument(document_ref)`: Reindex một document.
- `ReindexVault(scope)`: Reindex toàn bộ hoặc một subtree.
- `ValidateDocument(document_ref)`: Validate frontmatter/framework rules.

### 7.4. Tracking APIs

- `ListTrackingItems(query)`: Liệt kê task/project/book/course/habit/research/usecase từ indexed Vault.
- `GetTrackingItem(item_ref)`: Xem tracking item từ indexed Vault.
- `GetStaleItems(query)`: Lấy item stale/overdue/deferred.
- `GetPlanSignals(query)`: Lấy dữ liệu để Orchestrator suggest plan.

### 7.5. Daily Log APIs

- `GetDailyLog(date)`: Đọc daily log.
- `GetReviewSummary(query)`: Tổng hợp dữ liệu review ngày/tuần.

### 7.6. RAG/Search APIs

- `SearchKnowledge(query)`: Search/RAG trên indexed Vault documents.
- `GetRelatedDocuments(document_ref)`: Gợi ý related notes.
- `GetKnowledgeGaps(query)`: Phân tích gaps dựa trên taxonomy/wiki paths.

## 8. Business Rules & Invariants

- Obsidian `second-brain/` folder là canonical source of truth.
- Cortex App không ghi trực tiếp vào local Obsidian Vault trong phiên bản này.
- Capture DB là temporary buffer, không phải knowledge store chính thức.
- RAG không đọc Capture Inbox DB.
- Mọi knowledge lâu dài phải có thể xuất hiện dưới dạng Markdown trong Vault.
- `raw/` không được mất nội dung nguồn.
- `wiki/` là human-owned; AI chỉ draft/suggest patch nếu chưa có confirmation.
- `INDEX.md` chỉ là dashboard; state nằm ở files/frontmatter.
- Status và priority dùng plain text canonical values, không dùng biểu tượng.
- Nếu sync phát hiện file lỗi frontmatter, không được tự sửa file trong Vault; chỉ report validation issue.
- Nếu cùng một capture xuất hiện trong Vault theo checksum/capture id, phải mark capture đã exported/indexed để tránh duplicate.
- Direct write, direct export, auto-fix Vault files, và Obsidian plugin/CLI sync nằm trong scope nghiên cứu sau.

## 9. API Command/Query Contracts

### 9.1. CreateCapture Command

Input chính:

- `source`: chat, manual, import.
- `raw_text`.
- `suggested_title`.
- `suggested_description`.
- `suggested_tags`.
- `raw_type`: note, link, article, video, pdf, code, conversation.
- `created_from_thread_id` nếu có.

Output chính:

- `capture_id`.
- `status`: captured.
- `normalized_markdown`.
- `suggested_filename`.
- `warnings`.

### 9.2. MarkCaptureExported Command

Input chính:

- `capture_id`.
- `vault_path`.
- `checksum`.
- `export_method`: copy, download, manual.

Output chính:

- Updated capture status.
- Duplicate/sync warning nếu checksum đã tồn tại.

### 9.3. RunSync Command

Input chính:

- `scope`: full, changed_only, path.
- `path` nếu scope là path.
- `force_reindex`.

Output chính:

- Files scanned.
- Files indexed.
- Files skipped.
- Validation errors.
- Embedding jobs queued.

## 10. Audit, Events & Safety

Audit:

- Capture created/copied/exported/discarded.
- Document indexed/reindexed/validation failed.
- RAG index updated.

Events:

- `CaptureCreated`.
- `CaptureExported`.
- `VaultDocumentIndexed`.
- `VaultDocumentValidationFailed`.
- `EmbeddingQueued`.
- `EmbeddingUpdated`.
- `VaultSyncCompleted`.

Safety:

- App does not write to local Vault directly in the current scope.
- Bulk sync/index jobs require preview/dry-run when they affect metadata or index state.
- Capture discard should be reversible or audited.
- Sync should not overwrite user edits.
- Conflict resolution should prefer canonical Vault file over stale DB index.

## 11. Use Case Backlog

- Capture quick note from chat.
- Review Capture Inbox.
- Copy normalized markdown into Obsidian.
- Mark capture as exported.
- Sync Obsidian folder to app through future CLI/plugin/sync mechanism.
- Search indexed knowledge.
- Ask RAG question over `wiki/` and `staging/`.
- Show stale raw notes.
- Show staged notes waiting for wiki.
- Suggest plan from tracking/dailylogs.
- Detect broken links.
- Detect missing frontmatter.
- Suggest wiki draft from staging.
- Suggest patch for wiki, human confirms before applying.
- Research future sync mechanism: CLI tool, Obsidian plugin, Syncthing mirror, Git sync, or MinIO/upload bridge.
