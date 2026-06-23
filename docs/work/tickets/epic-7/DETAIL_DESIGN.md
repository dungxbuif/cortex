---
artifact_type: detail_design
id: EPIC-7-DETAIL-DESIGN
status: ready
owner: shared
trace:
  phase: docs/work/phases/PHASE-7-orchestrator-completion.md
  backlog_item: BL-009
  tickets:
    - docs/work/tickets/epic-7/CTX-701A.md
    - docs/work/tickets/epic-7/CTX-701.md
    - docs/work/tickets/epic-7/CTX-702.md
    - docs/work/tickets/epic-7/CTX-703.md
    - docs/work/tickets/epic-7/CTX-704.md
    - docs/work/tickets/epic-7/CTX-705.md
    - docs/work/tickets/epic-7/CTX-706.md
---

# Epic 7 Detail Design: Full LLM/ReAct Orchestrator Completion

## Problem

Epic 4 created the Python gateway and deterministic routing layer, but the project is not complete until the gateway can run a real LLM-backed orchestration loop, call tools safely, connect all old modules, and prove behavior through replayable tests/evals.

## Design Goals

- Keep domain modules free of prompts, LLM schemas, chat history, and ReAct state.
- Make Python the owner of `/v1/chat/completions`, tool routing, prompt contracts, and response synthesis.
- Reuse existing Finance, Second Brain, and Homelab services instead of copying business logic into the orchestrator.
- Use one shared PostgreSQL database; keep module isolation by table/repository boundary.
- Gate write-capable tools through permission, confirmation, and audit policy.

## Target Component Model

```text
+----------------+
| Open WebUI     |
| /v1/chat/...   |
+-------+--------+
        |
        v
+--------------------------+
| Python Gateway           |
| request/session adapter   |
+------------+-------------+
             |
             v
+--------------------------+        +----------------------+
| LLM/ReAct Orchestrator   | -----> | Tool Registry        |
| prompt + planning loop   |        | JSON schemas/policy  |
+------------+-------------+        +----------+-----------+
             |                                 |
             v                                 v
+--------------------------+        +----------------------+
| Tool Adapter Executor    | -----> | Permission/Audit     |
| validate/map/execute     |        | confirmation gates   |
+------------+-------------+        +----------+-----------+
             |
             v
+--------------------------+--------------------------+
| Finance Connector | Second Brain Connector | Homelab Connector |
+---------+---------+------------+-----------+---------+---------+
          |                      |                     |
          v                      v                     v
   Finance APIs          SecondBrainService      HomelabService
          |                      |                     |
          +----------------------+---------------------+
                                 |
                                 v
                    PostgreSQL cortex + pgvector
```

## Key Decisions

- **Provider-neutral tool schema first:** Registry owns generic schemas and converts to provider-specific shape at the boundary.
- **Adapters are thin:** Tool adapters validate/authorize/map/execute only. Domain services own behavior.
- **ReAct loop has hard limits:** Max turns, timeout, no-tool fallback, provider-error fallback, and clarification state prevent runaway loops.
- **Citations are mandatory for RAG-backed answers:** Second Brain and Homelab results must carry source path/snippet/score into synthesis.
- **Presentation owns citation layout:** The Orchestrator/Presentation Adapter formats source metadata into Markdown citations for Open WebUI. Second Brain citations should prefer Obsidian-friendly note/path labels when source metadata supports them; Homelab citations should keep repo path and commit SHA.
- **One DB:** Finance canonical tables, `secondbrain_*`, and `homelab_*` remain in one shared database.

## Ticket Breakdown

| Ticket | Purpose |
| --- | --- |
| CTX-701A | Prompt contract and orchestration decision-flow design for human Q&A |
| CTX-701 | LLM/ReAct runtime and prompt contract |
| CTX-702 | Tool registry and JSON schema contracts |
| CTX-703 | Tool adapter execution layer |
| CTX-704 | Module connectors for Finance, Second Brain, Homelab |
| CTX-705 | Sync/completion gaps and graceful degradation |
| CTX-706 | Evals and end-to-end chat tests |

## Verification Strategy

- Unit tests for prompt policy, registry schemas, adapters, error mapping, and formatting.
- Review tests/examples for prompt contract, decision states, tool-selection policy, clarification, confirmation, denial, and citation behavior before implementing runtime code.
- Integration tests against local PostgreSQL `cortex` with pgvector.
- Fake-provider replay tests for deterministic CI coverage.
- Opt-in real-provider smoke/eval using env credentials only.
- E2E tests against `/v1/chat/completions` for read, capture, confirmation, denial, and fallback cases.

## Open Constraints

- Full write-capable Finance chat flows should wait for or integrate with Audit & Permissions.
- Homelab must remain read-only.
- Second Brain chat must not write directly to the Vault.
- Capture inbox remains excluded from RAG unless explicitly approved by module policy.
