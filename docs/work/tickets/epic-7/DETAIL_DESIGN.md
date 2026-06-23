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
    - docs/work/tickets/epic-7/CTX-706A.md
---

# Epic 7 Detail Design: Full LLM/ReAct Orchestrator Completion

## Problem

Epic 4 created the Python gateway and deterministic routing layer, but the project is not complete until the gateway can run a real LLM-backed orchestration loop, call tools safely, connect all old modules, and prove behavior through replayable tests/evals.

## Design Goals

- Keep domain modules free of prompts, LLM schemas, chat history, and ReAct state.
- Make Python the owner of the orchestrator, tool routing, prompt contracts, and response synthesis.
- Reuse existing Finance, Second Brain, and Homelab services instead of copying business logic into the orchestrator.
- Use one shared PostgreSQL database; keep module isolation by table/repository boundary.
- Gate write-capable tools through permission, confirmation, and audit policy.

### Response Prompt

```text
Respond in concise plain text and structured lists.

Use compact bullet summaries or <pre> aligned text blocks for Finance reports (do not use Markdown tables).
For RAG-backed answers, include citations as a bullet list at the end:
- Sources:
- 1. <code>path/to/file.md @ commit</code>
For clarification, ask one focused question and name the missing fields.
For confirmation, summarize the exact action and ask for explicit approval.
For denial, state the policy boundary and safe alternative.
For fallback, explain what is unavailable and what the user can retry or check.
```

## Target Component Model

```text
+-----------------------+
| Telegram Bot Interface|
+-----------+-----------+
            |
            v
+--------------------------+
| Python Gateway           |
| request/session adapter  |
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
- **One DB:** Finance canonical tables, `secondbrain_*`, and `homelab_*` remain in one shared database.

## Chat Surface Decision

Telegram bot is the single, exclusive user-facing chat surface for Epic 7 and beyond. OpenWebUI and `/v1/chat/completions` compatibility are completely dropped.

Implications:

- The orchestrator core processes structured `ConversationInput`, decoupled from HTTP transports, but currently only wired to Telegram.
- Telegram adapter owns Telegram-specific concerns: webhook or polling setup, Telegram user/chat ID mapping, message normalization, response chunking, conversation history management, robust HTML escaping, and sending "typing..." actions during long LLM calls to preserve UX.
- **Telegram Rendering Policy (HTML Mode)**:
  - Default parse mode: `HTML` (not `MarkdownV2`, due to escaping complexities).
  - Escape all user/model text using standard `html.escape`.
  - Adapter whitelists tags: `<b>` for headings, `<i>` optional, `<code>` for inline IDs/paths, `<pre>` for blocks/tabular reports, `<a href="">` for safe URLs.
  - Long message chunking: max 4096 chars, target size ~3500 chars, splitting by paragraph/line.
  - Plain-text fallback: if HTML send fails due to malformed tags, retry with tags stripped/escaped.
- Authorization starts with an explicit Telegram user/chat allowlist mapped to the current single Cortex owner. Do not rely on obscurity of the bot token as authorization.

## Ticket Breakdown

| Ticket | Purpose |
| --- | --- |
| CTX-701A | Prompt contract and orchestration decision-flow design for human Q&A |
| CTX-701 | LLM/ReAct runtime and prompt contract |
| CTX-702 | Tool Registry And JSON Schema Contracts |
| CTX-703 | LLM/ReAct Runtime Loop async state machine |
| CTX-704 | Telegram bot transport adapter |
| CTX-705 | Module connectors for Second Brain and Homelab |
| CTX-706 | Tool Adapter Executor |
| CTX-706A | Policy/Audit gRPC Bridge & GrpcPolicyEnforcer |
| CTX-707 | Evals and end-to-end chat tests |

## Verification Strategy

- Unit tests for prompt policy, registry schemas, adapters, error mapping, and Telegram HTML escaping/chunking logic.
- Review tests/examples for prompt contract, decision states, tool-selection policy, and citation behavior.
- Integration tests against local PostgreSQL `cortex` with pgvector.
- Fake-provider replay tests for deterministic CI coverage.
- Opt-in real-provider smoke/eval using env credentials only.
- E2E tests against Telegram bot interface for read, capture, confirmation, denial, and fallback cases.

## Open Constraints

- Finance connector and full write-capable Finance chat flows should wait for or integrate with Audit & Permissions.
- Homelab must remain read-only.
- Second Brain chat must not write directly to the Vault.
- Capture inbox remains excluded from RAG unless explicitly approved by module policy.
