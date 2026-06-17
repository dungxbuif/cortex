---
type: Strategy
title: "Phase 3: Multi-Agent & Tiêu chuẩn hoá giao tiếp (MCP)"
description: "Áp dụng Multi-Agent Systems và Model Context Protocol (MCP) khi số lượng Plugin/Tools tăng."
timestamp: 2026-06-16T00:00:00Z
---

# Phase 3: Multi-Agent & Tiêu chuẩn hoá giao tiếp (MCP)

Khi số lượng "Plugin/Tools" lên tới hàng chục, một Agent sẽ bị quá tải ngữ cảnh.

**Kiến thức AI Apply:** Multi-Agent Systems, Agentic Workflows, Semantic Routing.

**Thực thi:**
* Thay vì 1 Agent, bạn chia ra: Finance Agent, Homelab Agent, Research Agent. Python Orchestrator sẽ đóng vai trò Supervisor Agent, nhận tin nhắn và định tuyến (Routing) đến đúng Agent con xử lý.
* Cross-runtime service calls dùng gRPC cho contract nội bộ. MCP có thể được áp dụng sau cho plugin/tool ecosystem khi cần chuẩn giao tiếp rộng hơn bên ngoài boundary Go/Python nội bộ.
