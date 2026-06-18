---
type: Specification
title: "System Spec: External Automation & N8n Integration"
description: "Specification of roles, integration architecture, webhook security, capability model, and integration plans for n8n in the Cortex system."
timestamp: 2026-06-18T00:00:00Z
---

# System Spec: External Automation & N8n Integration

## 1. Objective

Define the exact role of **n8n** within the Cortex system architecture. This spec ensures n8n acts as an External Automation Layer without violating Cortex's Module Boundary Principle and security policies.

---

## 2. Roles & Boundaries

N8n acts as an **External Worker / Event Orchestrator**, running independently and communicating with Cortex via standard protocols (HTTPS Webhooks / REST APIs).

### 2.1. Permitted Actions (What n8n CAN do):
* **Cron & Scheduling:** Run periodic tasks (e.g., triggering stock/crypto price checks, daily reminders).
* **Data Ingestion & Extraction (ETL):** Gather data from external sources (web scraping, RSS feeds, banking/provider APIs) and push it to Cortex.
* **Notification Routing:** Listen to events from Cortex and route notifications to the user via external channels (Telegram, Discord, Slack, Email).
* **OAuth & OAuth2 flows:** Manage tokens and credentials for third-party services to prevent exposing complex security configurations inside Cortex Backend.

### 2.2. Prohibited Actions (What n8n CANNOT do):
* **Contain Core Business Logic:** N8n workflows must not calculate wallet balances, parse RAG document chunks, or enforce authorization guards.
* **Direct Database Read/Write:** N8n must not connect directly to Cortex's PostgreSQL instance or Obsidian Vault files. All data access must pass through secured API endpoints exposed by Go/Python backend services.

---

## 3. Integration Architecture & Data Flow

Communication between n8n and Cortex follows a **Webhook Push & Pull** model:

```text
Flow 1: Push (n8n -> Cortex)
+------------------+         +----------------------------+         +-----------------------+
|   n8n Workflow   |  HTTPS  | Go Gateway (Port 8080)     |  gRPC   | Python AI / Domain SB |
| (Fetch Ext Data) +-------->+  - Route: /api/webhooks/*  +-------->+  - Embed/Sync         |
|                  |  POST   |  - Auth & Capability Check |         |  - Save DB            |
+------------------+         +----------------------------+         +-----------------------+

Flow 2: Pull/Notify (Cortex -> n8n)
+------------------+         +----------------------------+         +-----------------------+
|  Cortex Domain   | Event   | Webhook Dispatcher (Go)    | HTTPS   |      n8n Webhook      |
|  (State Changed) +-------->+  - Send payload to n8n     +-------->+ (Send Telegram/Email) |
+------------------+         +----------------------------+         +-----------------------+
```

---

## 4. Security & Authentication

To protect Cortex from unauthorized external requests:

1. **Authentication Token:**
   * Cortex defines a dedicated API Key for n8n (`CORTEX_N8N_API_KEY`) stored in Go Backend and n8n environment variables.
   * Every request from n8n to Cortex must include the header:
     ```http
     X-Cortex-N8n-Token: <token_value>
     ```
2. **Webhook Endpoint Routing:**
   * Routes dedicated to n8n are grouped under `/api/webhooks/n8n/*`.
   * These endpoints bypass standard browser CORS checks and should be restricted to local IP addresses or secure gateway tunnels (e.g., Rathole, Cloudflare Tunnels).
3. **Payload Signature (HMAC):**
   * For sensitive write operations (e.g., updates to financial records), n8n must sign payloads using HMAC-SHA256 with a shared secret key, passing the signature in the `X-Cortex-Signature` header.

---

## 5. Capability & Permission Model for n8n

n8n is identified in the Cortex capability guard as a **System Principal** (`principal: "n8n_worker"`).

The capability guard defines permissions for this principal:

| Module | Required Action | Capability | Default Status | Notes |
| --- | --- | --- | --- | --- |
| **Finance** | Update asset prices | `finance:write_prices` | **Allowed** | For automated market price synchronization |
| **Finance** | Create transactions | `finance:write_transactions` | **Denied** (Requires confirmation) | Prevents automated duplicates/uncontrolled writes |
| **Second Brain** | Ingest capture notes | `secondbrain:capture` | **Allowed** | Push temporary snippets from Telegram/RSS to Capture DB |
| **Homelab** | Trigger repo sync | `homelab:sync_trigger` | **Allowed** | Triggered by GitHub Webhook push events |

---

## 6. Step-by-Step Integration Plan

The integration of n8n is divided into four distinct phases:

### Phase 1: Build Webhook Infrastructure on Go Backend
1. **Register Webhook Routes in Go Echo:**
   * Create the package `internal/infrastructure/webhooks/n8n/`.
   * Define JSON webhook handlers for each module:
     * `POST /api/webhooks/n8n/finance/prices`
     * `POST /api/webhooks/n8n/secondbrain/capture`
     * `POST /api/webhooks/n8n/homelab/sync`
2. **Implement Security Middleware:**
   * Verify the `X-Cortex-N8n-Token`.
   * Inject the Principal context (`n8n_worker`) into the request context for downstream permission checks and audit logs.

### Phase 2: Secure Processing & Audit Trails
1. **Link to Domain Services via gRPC:**
   * Webhook handlers map JSON DTOs to generated protobuf messages.
   * Invoke the respective gRPC services (e.g., `SecondBrainService.Capture` or `FinanceService.UpdateAssetPrice`).
2. **Record Audit Events:**
   * Log all successful and blocked webhook attempts in the centralized `audit_events` store.

### Phase 3: Implement Template n8n Workflows
1. **Finance Pricing Sync Workflow:**
   * **Trigger:** Cron node (every day at 17:00).
   * **Action 1:** Fetch latest assets/prices from CoinGecko or Yahoo Finance.
   * **Action 2:** Send HTTP request to `POST /api/webhooks/n8n/finance/prices` with the API key.
2. **Second Brain Capture Workflow:**
   * **Trigger:** Telegram Bot trigger or RSS Reader.
   * **Action:** Format note content as temporary Markdown and post it to `/api/webhooks/n8n/secondbrain/capture`.

### Phase 4: Verification & UAT
1. **Mock Testing:** Send HTTP requests using curl with/without valid headers to ensure middleware filters requests correctly.
2. **E2E Testing:** Trigger the workflow from the n8n UI, monitor Go Backend logs, and verify that changes persist correctly in PostgreSQL.
