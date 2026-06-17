---
type: Strategy
title: "Phase 2: RAG & Semantic Search"
description: "Làm chủ dữ liệu phi cấu trúc, nâng cấp Second-Brain thành hệ thống hỏi đáp với tài liệu."
timestamp: 2026-06-16T00:00:00Z
---

# Phase 2: RAG & Semantic Search (Làm chủ dữ liệu phi cấu trúc)

Nhằm nâng cấp Second-Brain từ chỗ chỉ lưu file Markdown thô sang một hệ thống "hỏi đáp với tài liệu".

**Kiến thức AI Apply:** Embeddings, Chunking strategies (cắt nhỏ text), Vector Database, Retrieval-Augmented Generation (RAG).

**Thực thi:**
* Dùng PostgreSQL + pgvector làm vector store mặc định để giữ vận hành local đơn giản.
* Viết Python AI service để định kỳ đọc file Markdown từ Vault mirror/snapshot, chuyển thành vector và lưu vào DB.
* Khi bạn hỏi "Tháng trước tôi set up con router thế nào?", Python Orchestrator sẽ gọi RAG service tìm kiếm các đoạn text liên quan, nhét vào prompt, và Gemini sẽ tổng hợp câu trả lời.
