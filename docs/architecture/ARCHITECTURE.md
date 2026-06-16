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
| **Finance** | Manage personal finance, budgets, assets, and net worth. | PostgreSQL (Canonical) |
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
