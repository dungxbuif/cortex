---
artifact_type: ticket
id: CTX-701A
status: ready
owner: shared
priority: High
lane: high-risk
trace:
  backlog_item: BL-009
  requirement: REQ-006
  phase: docs/work/phases/PHASE-7-orchestrator-completion.md
  detail_design: docs/work/tickets/epic-7/DETAIL_DESIGN.md
  validation_matrix: docs/work/VALIDATION_MATRIX.md
  docs_review: docs/work/tickets/epic-7/CTX-701A.md#docs-review
  release_notes: docs/releases/CHANGELOG.md
---

# Ticket: CTX-701A Prompt Contract And Orchestrator Decision Flow

## Context

The project needs a reviewable design for how the AI runtime behaves before implementing a full LLM/ReAct loop. The user is still building AI orchestration knowledge, so this ticket should produce a clear artifact that can be discussed and confirmed before code changes.

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

## Recommended Design Direction

Use an explicit Python orchestrator state machine rather than a free-form agent framework for v1:

```text
receive_request
  -> build_context
  -> classify_intent
  -> select_candidate_tools
  -> decide_next_action
  -> validate_tool_arguments
  -> check_policy
  -> execute_tool
  -> observe_result
  -> synthesize_response
```

Required terminal or branch states:

- `clarify`: required arguments are missing or user intent is ambiguous.
- `confirm`: the action is allowed only after user confirmation.
- `deny`: the requested action violates source-of-truth or capability policy.
- `fallback`: provider/tool/runtime failure prevents normal completion.
- `synthesize`: tool results or no-tool reasoning are ready for final answer.

## Prompt Contract Draft

The design artifact should separate prompt responsibilities:

| Prompt Area | Responsibility |
| --- | --- |
| System rules | Non-negotiable Cortex boundaries: no Homelab writes, no direct Vault writes, Finance writes need validation/confirmation, RAG needs citations. |
| Developer rules | Orchestration procedure, tool-call rules, clarification/confirmation/deny behavior, fallback behavior. |
| Module rules | Finance, Second Brain, and Homelab capability/source-of-truth constraints. |
| Response rules | Markdown output, tables when useful, citations for RAG, concise denial/confirmation prompts. |

Prompts must not be embedded inside Finance, Second Brain, or Homelab domain services.

## Acceptance Criteria

- [ ] Prompt contract explains system/developer/module/response responsibilities.
- [ ] Orchestrator states and transitions are documented clearly enough to implement.
- [ ] Tool-selection policy states which tools are eligible for v1.
- [ ] Clarification, confirmation, denial, fallback, and citation rules are documented with examples.
- [ ] Eval examples cover no-tool answer, Second Brain capture, Second Brain RAG with citation, Homelab read-only RAG, Homelab write denial, Finance read/report, ambiguous Finance write confirmation, provider failure fallback, and missing argument clarification.
- [ ] Human Q&A items are recorded before CTX-701 implementation begins.

## Small Task Exemption

- Small task exemption: no

## Test Expectations

- Docs review only for this design ticket.
- Runtime tests are implemented in follow-up tickets after this design is approved.

## Open Q&A For Human Review

- Should Finance write tools be excluded from go-live v1, or included only behind confirmation?
- Should prompts live as Markdown/YAML files loaded by Python, or as Python constants generated from docs?
- Should the first provider integration target Gemini tool calling directly, or keep a provider-neutral internal tool-call representation with provider-specific adapters?
- What exact citation style should Second Brain use for Obsidian navigation in Open WebUI?
