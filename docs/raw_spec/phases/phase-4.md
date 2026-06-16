---
type: Strategy
title: "Phase 4: Local LLMs & Fine-Tuning"
description: "Tự chủ hoàn toàn với Model Serving cục bộ và Fine-Tuning."
timestamp: 2026-06-16T00:00:00Z
---

# Phase 4: Local LLMs & Fine-Tuning (Tự chủ hoàn toàn)

Thoát ly khỏi Google AI Studio đối với các task nhạy cảm.

**Kiến thức AI Apply:** Model Serving (vLLM, Ollama), Prompt Optimization cho model nhỏ, PEFT/LoRA (Fine-tuning).

**Thực thi:**
* Deploy các model như Llama-3 (8B) hoặc Qwen ngay trên Homelab.
* Fine-tuning: Thu thập lịch sử chat và dữ liệu quản lý tài chính từ Phase 1. Dùng nó để fine-tune một model nhỏ chuyên trách việc parse giao dịch tài chính cá nhân của riêng bạn (ví dụ: model tự hiểu "Cf" là "Cà phê, danh mục ăn uống").
