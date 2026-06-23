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

Cortex is a personal AI system acting as a unified gateway for an individual's data domains. It is structured around a **Python Gateway / Orchestrator / AI runtime** plus **Go API-heavy deterministic services**. Python owns the OpenAI-compatible chat gateway, LLM orchestration, tool routing, context planning, RAG coordination, provider integration, response synthesis, and AI evaluations. Go is preferred for deterministic domain/API components such as Finance and compatibility proxy surfaces when useful. Go and Python communicate through internal gRPC contracts where they are separate processes.

## System Boundaries

- **Cortex Client / Open WebUI-compatible Clients**: The first-party React/Tailwind client is served at `/ui`; Open WebUI compatibility remains through `/v1/chat/completions`.
- **Python Gateway, Orchestrator & LLM Runtime**: Exposes `/v1/chat/completions`, maps chat intents to strict domain API tool calls, manages context, calls LLM providers, and synthesizes responses.
- **Go Domain/API Services**: Pure business logic and API-heavy components such as Finance, exposed to Python through gRPC where needed.
- **Python AI Services**: Specialized AI/RAG/vector/document-understanding tasks for Second Brain and Homelab, available through direct Python calls inside the service boundary and internal gRPC where a process boundary is useful.
- **N8n (External Automation)**: Handles crons, external integrations, and pushes data back to Cortex via webhooks.

## Modules

| Module | Responsibility | Key Data |
| --- | --- | --- |
| **Finance (Go)** | Manage personal finance, wallets, transactions, investment holdings, market price history, reports, and net worth. | PostgreSQL (Canonical) |
| **Second Brain (Python)** | Knowledge management, capture inbox, and Obsidian RAG pipeline with strict evaluations. | Obsidian Vault (Canonical) / PostgreSQL (Buffer & Vector Index) |
| **Homelab (Python AI Service)** | Homelab docs sync, redaction, RAG search, and link validation. Python gateway/orchestrator calls the service directly inside the AI runtime; internal gRPC remains available as a service contract. | GitHub Repo (Canonical) / PostgreSQL (Vector Index) |
| **Orchestrator (Python)** | Intent parsing, tool calling, context planning, provider calls, and response synthesis. | Ephemeral Context |
| **System Services (Go)** | Permission and audit control for future tool/runtime calls. | PostgreSQL |

## Data Flow

```text
User Message -> Cortex Client or Open WebUI -> Python /v1/chat/completions Gateway
  -> Python Orchestrator (Intent + Permission Check)
  -> Tool Adapter
  -> Domain/API Service (gRPC to Go service OR Python AI service)
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

- **Chat Flow**: Request/response or OpenAI-compatible SSE streaming via Python `/v1/chat/completions`.
- **Client Flow**: FastAPI serves the React/Tailwind client at `/ui`; the client bootstraps an internal non-expiring JWT from `/api/auth/dev-token`, uses one hard-coded user UUID, and keeps one single chat conversation with tabs reserved for module-specific UIs.
- **Sync/Index Flow**: Asynchronous jobs pulling from canonical sources or mirrors -> Redaction -> Chunking -> Vector Index.
- **AI Compatibility Proxy Flow**: Go Echo routes under `/api/secondbrain/*` and `/api/homelab/*` remain thin internal/dev adapters. They map JSON to generated protobuf messages, call the Python AI service over internal gRPC, and return JSON without adding domain logic in Go.
- **Second Brain Obsidian Sync Flow**: n8n or another MinIO event source posts an authenticated object event to the Python Gateway. The gateway validates `X-Cortex-N8n-Token`, persists an ingestion job, and returns `202 Accepted`. A worker path processes the job: create/update events fetch Markdown from the configured MinIO/S3 mirror, chunk, embed, and write PostgreSQL + pgvector records; delete events remove matching documents/chunks from active RAG search. MinIO remains a mirror/snapshot, not the canonical authoring source.

```text
MinIO/S3 event
  -> Python FastAPI webhook
  -> secondbrain_ingestion_jobs
  -> worker process job
  -> SecondBrainService
  -> secondbrain_documents + secondbrain_document_chunks (pgvector)
```

## System Audit And Policy

Epic 5 adds internal Go system services for audit and capability decisions:

- `system/audit` persists append-only `audit_events` records with generated IDs, timestamps, JSONB source/target refs, and recursive secret-key rejection.
- `system/policy` evaluates the static v1 capability matrix for Finance, Second Brain, and Homelab.
- The policy service hard-denies Homelab external writes/runtime actions and Second Brain direct Vault writes, requires confirmation for high-impact Finance writes, and supports webhook/system actor checks such as `second_brain.index_external_source`.

These services are internal primitives for future Orchestrator/tool adapter wiring; no public audit or policy management API is exposed in this slice.

```text
OpenAI-compatible chat request
  -> Python FastAPI /v1/chat/completions
  -> OrchestratorService
  -> SecondBrainService / HomelabService
  -> PostgreSQL + pgvector / local Git or Vault mirror
```

## Dependencies

- **PostgreSQL + pgvector**: Core database for finance data, capture buffers, and vector embeddings.
- **Go**: Deterministic domain/API services and compatibility proxy surfaces.
- **Python / gRPC services**: Ecosystem for advanced RAG, text chunking, embeddings, reranking, and LLM evaluations.
- **Python Gateway/Orchestrator**: OpenAI-compatible chat gateway, LLM/tool runtime, context planning, provider integrations, and response synthesis.
- **FastAPI**: Primary Python chat gateway surface and optional dev/debug adapter for module diagnostics.
- **React/Tailwind Cortex Client**: First-party internal UI served from FastAPI `/ui`.
- **Open WebUI**: Compatible frontend chat client through the OpenAI API surface.
- **LLM Provider**: Gemini / OpenAI for intelligence.
- **N8n**: External webhook worker.
- **MinIO-compatible object storage**: Optional Second Brain mirror/snapshot source for Obsidian sync. Local development uses `SECOND_BRAIN_MINIO_LOCAL_ROOT` as a filesystem-backed S3 bucket simulation.

## Risks And Tradeoffs

- **LLM Non-determinism**: Addressed by enforcing the Module Boundary Principle.
- **Data Privacy**: Mitigated by running everything locally/self-hosted and using redaction pipelines before indexing.

## Linked Decisions

- [ADR-001: Go Modular Monolith](../decisions/ADR-001-go-modular-monolith.md)
- [ADR-002: Module Boundary Principle](../decisions/ADR-002-module-boundary-principle.md)
- [ADR-003: Use Python for Orchestrator and AI-heavy processing, Go for API-heavy components](../decisions/ADR-003-second-brain-python-migration.md)
- [ADR-004: Switch to Real AI Embeddings and Checksum Optimization](../decisions/ADR-004-real-ai-embeddings-and-checksum-optimization.md)
- [ADR-005: Internal Single-User JWT For Cortex Client](../decisions/ADR-005-internal-single-user-jwt.md)
