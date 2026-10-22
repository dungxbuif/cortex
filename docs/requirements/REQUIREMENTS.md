---
artifact_type: requirements_index
id: REQUIREMENTS
status: draft
owner: shared
human_fields: [priority, acceptance, requirement_source]
ai_fields: [requirement_rows, status_updates, trace_links]
shared_fields: [functional_requirements, non_functional_requirements]
---

# Requirements

## Field Ownership

- Human owns priority, acceptance, and requirement source.
- AI maintains rows, trace links, and status updates.

## Functional Requirements

| ID | Requirement | Priority | Source | Status |
| --- | --- | --- | --- | --- |
| REQ-001 | Provide an OpenAI-compatible API to accept chat requests from Open WebUI. | High | `spec.md` | draft |
| REQ-002 | Extract intents and parameters via LLM to invoke deterministic Domain APIs (Orchestrator). | High | `spec.md` | draft |
| REQ-003 | **Finance**: Record income, expense, and transfer transactions across various wallets. | High | `finance.md` | draft |
| REQ-004 | **Finance**: Track investment assets, historical asset transactions, current holdings, market price history, weighted-average cost basis, and calculate Net Worth without treating investment buys as living expenses. | High | `finance.md` | draft |
| REQ-005 | **Finance**: Generate financial reports, budget alerts, and categorize transactions using business-effective dates for financial periods. | Medium | `finance.md` | draft |
| REQ-010 | **Finance**: Track debts and loans in both directions: money I owe and money other people owe me, including repayments/collections and net-worth impact. | High | `finance.md` | draft |
| REQ-006 | **Second Brain**: Capture insights and notes into an Inbox Database buffer. | Medium | `spec.md` | draft |
| REQ-007 | **Second Brain**: Perform RAG (Retrieval-Augmented Generation) queries against a local Obsidian Vault. | Medium | `spec.md` | draft |
| REQ-008 | **Homelab**: Perform read-only RAG and QA against the pulled Homelab repository. | Medium | `spec.md` | draft |
| REQ-009 | Sync and index data from external canonical sources and mirrors for RAG, including webhook-triggered indexing of Obsidian `second-brain/` Markdown objects from an S3-compatible mirror. | High | `spec.md` | draft |

## Non-Functional Requirements

| ID | Requirement | Category | Status |
| --- | --- | --- | --- |
| NFR-001 | **Module Boundary**: Domain modules must not contain LLM prompts or ReAct loops. | Architecture | draft |
| NFR-002 | **Source of Truth**: The Homelab module must be strictly read-only from the chat interface. | Security | draft |
| NFR-003 | **Source of Truth**: Second Brain must only write to a database buffer, never directly to the local Vault files via chat. | Security | draft |
| NFR-004 | **Auditing**: All API tool calls, syncs, indexings, writes, and permission denials must be logged. | Compliance | draft |
| NFR-005 | **Citations**: RAG answers must provide citations if relying on indexed documents. | UX / Accuracy | draft |
| NFR-006 | **Finance Auditability**: Finance tables must include auditable actor/timestamp fields, while financial reports use business-effective timestamps such as `occurred_at`, not row `created_at`. | Compliance / Reporting | draft |
