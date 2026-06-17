---
artifact_type: architecture_doc
id: ARCH-MASTER
status: draft
owner: shared
human_fields: [approved_boundaries, architectural_constraints, tradeoff_approval]
ai_fields: [overview, modules, diagrams, flows, dependencies, risks]
shared_fields: [status, linked_decisions]
---

# Architecture

## Field Ownership

- Human owns approved boundaries, constraints, and tradeoff approvals.
- AI maintains implementation-grounded overview, modules, diagrams, flows, dependencies, and risks.

## Overview

Cortex is a personal AI system acting as a unified gateway for an individual's data domains. It is structured as a **Go Modular Monolith**, exposing an OpenAI-compatible API to the Open WebUI frontend. It coordinates LLM interactions, tool calls, and RAG at the Orchestrator layer, and routes actions to strictly separated domain modules via Domain APIs.

## System Boundaries

- **Open WebUI (Client)**: The sole chat interface.
- **Orchestrator & LLM**: Maps chat intents to strict domain API tool calls.
- **Domain Modules**: Pure business logic (Finance, Second Brain, Homelab) with no LLM logic inside.
- **N8n (External Automation)**: Handles crons, external integrations, and pushes data back to Cortex via webhooks.

## Modules

| Module | Responsibility | Key Data |
| --- | --- | --- |
| **Finance** | Manage personal finance, wallets, transactions, investment holdings, market price history, reports, and net worth. | PostgreSQL (Canonical) |
| **Second Brain** | Knowledge management, capture inbox, and Obsidian RAG. | Obsidian Vault (Canonical) / PostgreSQL (Buffer) |
| **Homelab** | Homelab service queries, docs, and validation. | GitHub Repo (Canonical) |
| **Orchestrator** | Intent parsing, tool calling, and response synthesis. | Ephemeral Context |
| **System Services** | Permission, Audit, Sync, and RAG indexing. | PostgreSQL / pgvector |

## Data Flow

```text
User Message -> Open WebUI -> Cortex OpenAI Proxy
  -> Orchestrator (Intent + Permission Check)
  -> Tool Adapter
  -> Domain API (e.g. Finance.CreateTransaction)
  -> Audit Event Log
  -> LLM Synthesis -> Markdown Response to User
```

## Finance Service Boundary

Finance is a deterministic domain module. It owns money movement, wallet balances, investment holdings, cost basis, market valuation, and reporting rules. It must not contain prompts, OpenAI tool schemas, chat history, or response synthesis.

```text
+-----------------------------+
| Orchestrator / Tool Adapter |
| chat intent + tool mapping   |
+--------------+--------------+
               |
               v
+-----------------------------+
| Finance Delivery API        |
| command/query DTO mapping   |
+--------------+--------------+
               |
               v
+-----------------------------+
| Finance Services            |
| wallet/category/transaction |
| asset/report/net-worth rules|
+--------------+--------------+
               |
               v
+-----------------------------+
| Finance Repositories        |
| persistence queries only    |
+--------------+--------------+
               |
               v
+-----------------------------+
| PostgreSQL                  |
| canonical finance store     |
+-----------------------------+
```

Finance investment modeling separates historical execution data from current market valuation:

- `asset_transactions` record what happened at the time: buy/sell/dividend/split, quantity, unit price, fees, taxes, and linked cash movement.
- `asset_holdings` hold current derived positions, weighted-average cost, current value, and gain/loss fields.
- `asset_prices` store market price history and are not overwritten.
- Net worth uses current asset values, not original purchase prices.

Finance reporting and auditability follow separate time semantics:

- Business reports use effective dates such as `transactions.occurred_at`, `asset_transactions.occurred_at`, `asset_prices.priced_at`, `debt_payments.paid_at`, and net-worth `as_of`.
- Row audit fields such as `created_at`, `created_by`, `updated_at`, and `updated_by` record when and by whom data was entered or changed.
- A transaction can be created today for a past or future business date; reports must place it in the period of `occurred_at`, not `created_at`.
- Normal report reads use indexed aggregates and projections (`wallets.current_balance`, `asset_holdings`, latest `asset_prices`, active `debt_loans`) instead of replaying raw history.

## Runtime Flow

- **Chat Flow**: Synchronous request/response loop via `/v1/chat/completions`.
- **Sync/Index Flow**: Asynchronous jobs pulling from canonical sources (Git, Vault) -> Redaction -> Chunking -> Vector Index.

## Dependencies

- **PostgreSQL + pgvector**: Core database for finance data, capture buffers, and vector embeddings.
- **Open WebUI**: Frontend chat client.
- **LLM Provider**: Gemini / OpenAI for intelligence.
- **N8n**: External webhook worker.

## Risks And Tradeoffs

- **LLM Non-determinism**: Addressed by enforcing the Module Boundary Principle.
- **Data Privacy**: Mitigated by running everything locally/self-hosted and using redaction pipelines before indexing.

## Linked Decisions

- [ADR-001: Go Modular Monolith](../decisions/ADR-001-go-modular-monolith.md)
- [ADR-002: Module Boundary Principle](../decisions/ADR-002-module-boundary-principle.md)
