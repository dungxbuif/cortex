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
* Thay vì 1 Agent, bạn chia ra: Finance Agent, Homelab Agent, Research Agent. Go sẽ đóng vai trò Supervisor Agent, nhận tin nhắn và định tuyến (Routing) đến đúng Agent con xử lý.
* Đây là lúc bạn apply MCP (Model Context Protocol). Các domain services (n8n, Python script) sẽ trở thành các MCP Servers, và Go BE là MCP Client. Mọi thứ tuân theo chuẩn giao tiếp quốc tế, cực kỳ dễ cắm rút.
