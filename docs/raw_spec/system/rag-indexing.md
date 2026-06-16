---
type: Specification
title: "System Spec: RAG & Indexing Service"
description: "Đặc tả service chung cho sync, parse, redaction, chunking, embedding, retrieval, citations và RAG source policy."
timestamp: 2026-06-16T00:00:00Z
---

# System Spec: RAG & Indexing Service

## 1. Mục tiêu

RAG & Indexing Service là hạ tầng chung. Module không tự implement RAG riêng; module chỉ khai báo source, include/exclude policy, parser hints, redaction rules, ranking priority và citation format.

## 2. Responsibilities

- Nhận sync/index jobs từ module hoặc system scheduler.
- Đọc mirror/snapshot/canonical source được phép.
- Parse Markdown, YAML frontmatter, IaC metadata, CSV hoặc structured records khi cần.
- Redact secrets/sensitive fields trước khi chunk/embed.
- Tạo metadata index, full-text index và vector index.
- Trả retrieval results kèm citations.
- Theo dõi stale/deleted/moved documents.
- Ghi audit events cho query/index/redaction.

## 3. Non-Responsibilities

- Không ghi canonical source.
- Không sửa markdown/config.
- Không quyết định business rule của module.
- Không expose raw secrets.
- Không đọc capture buffer nếu module policy cấm.

## 4. Module Index Policies

### 4.1. Finance

- RAG optional.
- Primary source là structured DB queries, không phải document RAG.
- Có thể index derived finance insights/report notes trong tương lai.
- Không embed raw sensitive financial payload nếu không cần.

### 4.2. Second Brain

- Include indexed Vault mirror/snapshot.
- Exclude Capture Inbox DB.
- Prefer `wiki/` over `staging/`, `staging/` over `raw/`.
- Archived/deleted content chỉ dùng khi query explicitly asks.
- Citation should include Vault path and indexed timestamp/source revision if available.

### 4.3. Homelab

- Include active repo docs/IaC metadata.
- Exclude `deprecated/**` by default.
- Exclude credentials, keys, kubeconfigs, tfstate, raw diagnostics.
- Secret scan/redaction required before embedding.
- Citation must include repo path and commit SHA.

## 5. Index Record Contract

```json
{
  "source_id": "homelab:github:dungxbuif/Homelab",
  "module": "homelab",
  "source_type": "git_repo",
  "source_revision": "commit_sha",
  "path": "docs/MAIN.md",
  "content_hash": "sha256",
  "chunk_id": "docs/MAIN.md#section-3:chunk-2",
  "title": "Network Architecture",
  "headings": ["MAIN", "Network Architecture"],
  "tags": [],
  "redaction_status": "clean|redacted|skipped",
  "indexed_at": "2026-06-16T00:00:00Z"
}
```

## 6. Retrieval Contract

Retrieval result must include:

- `answer_context`.
- `module`.
- `source_path`.
- `source_revision`.
- `chunk_id`.
- `score`.
- `redaction_status`.
- `citation_label`.
- `confidence`.

LLM-facing context must be safe:

- No raw secrets.
- No skipped chunks.
- No stale chunks unless explicitly marked.

## 7. Redaction Rules

Mandatory redaction before embedding:

- Passwords.
- Tokens.
- Private keys.
- Kubeconfigs.
- `.env` values.
- Terraform state secrets.
- Provider credentials.
- Private connection strings.

If redaction cannot safely preserve meaning, skip indexing the chunk and emit `IndexChunkSkipped`.

## 8. Citation Rules

- RAG answers must cite source when based on indexed documents.
- Homelab citation: `path @ commit_sha`.
- Second Brain citation: `vault_path @ indexed_at/source_revision`.
- If sources conflict, answer should say conflict exists and list sources.
- If confidence is low, answer should be explicit.

## 9. API Surface

- `SubmitIndexJob(command)`.
- `GetIndexJobStatus(query)`.
- `SearchIndex(query)`.
- `GetDocumentChunks(query)`.
- `GetSourceCitation(query)`.
- `GetRedactionReport(query)`.
- `ReindexSource(command)`.
- `DeleteStaleChunks(command)`.
