---
artifact_type: ticket
id: CTX-701A
status: done
owner: shared
priority: High
lane: normal
trace:
  backlog_item: BL-009
  requirement: REQ-006
  phase: docs/work/phases/PHASE-7-orchestrator-completion.md
  detail_design: docs/work/tickets/epic-7/DETAIL_DESIGN.md
  test_verification: docs review and approval of prompts/flows
  validation_matrix: docs/work/VALIDATION_MATRIX.md
  docs_review: docs/work/tickets/epic-7/CTX-701A.md#docs-review
  release_notes: docs/releases/CHANGELOG.md
---

# Ticket: CTX-701A Prompt Contract And Orchestrator Decision Flow

## Context

The project needs a reviewable design for how the AI runtime behaves before implementing a full LLM/ReAct loop. The user is still building AI orchestration knowledge, so this ticket should produce a clear artifact that can be discussed and confirmed before code changes.

This ticket is completed. The finalized prompt contract, ReAct state flow (including the drop of OpenWebUI and `/v1/chat/completions` API in favor of Telegram bot, use of PostgreSQL for state, and async Python execution) have been successfully documented and approved in `DETAIL_DESIGN.md`.

## Scope

- Define the Cortex prompt contract as human-readable design content before implementation.
- Specify system/developer/module prompt responsibilities.
- Define the orchestrator decision flow as explicit states.
- Define tool-selection rules, argument completeness rules, clarification rules, confirmation rules, denial rules, and fallback rules.
- Define the first safe tool-call scope for v1: Second Brain capture/search/status, Homelab read-only search/link/status, and Finance read/report/net-worth.
- Define response presentation rules, including RAG citation behavior.
- Define eval/replay examples that prove the intended behavior before runtime code is implemented.

## Out of Scope

- Implementing provider calls.
- Implementing tool registry code.
- Implementing adapter execution code.
- Enabling unrestricted Finance writes.
- Changing domain service business logic.

## Acceptance Criteria

- [x] Prompt contract explains system/developer/module/response responsibilities (documented in `DETAIL_DESIGN.md`).
- [x] Orchestrator states and transitions are documented clearly enough to implement (documented in `DETAIL_DESIGN.md`).
- [x] Tool-selection policy states which tools are eligible for v1 (documented in `DETAIL_DESIGN.md`).
- [x] Clarification, confirmation, denial, fallback, and citation rules are documented with examples (documented in `DETAIL_DESIGN.md`).
- [x] Eval examples cover no-tool answer, Second Brain capture, Second Brain RAG with citation, Homelab read-only RAG, Homelab write denial, Finance read/report, ambiguous Finance write confirmation, provider failure fallback, and missing argument clarification (documented in `DETAIL_DESIGN.md`).
- [x] Human Q&A items are recorded and resolved (documented in `DETAIL_DESIGN.md`).

## Small Task Exemption

- Small task exemption: no

## Test Expectations

- Docs review only for this design ticket. All prompt and flow decisions are finalized and recorded in the detail design.
