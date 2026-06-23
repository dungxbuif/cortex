---
artifact_type: phase
id: PHASE-7-orchestrator-completion
status: ready
owner: human
human_fields:
  - goal
  - scope
  - out_of_scope
  - priority
  - success_criteria
ai_fields:
  - risks
  - dependencies
  - verification_plan
  - completion_summary
shared_fields:
  - status
  - trace
  - tickets_and_bugs
trace:
  backlog_items:
    - BL-009
  roadmap: ROADMAP
  requirements:
    - docs/raw_spec/system/orchestrator.md
    - docs/raw_spec/system/permission-policy.md
    - docs/raw_spec/system/source-of-truth-sync.md
  tickets:
    - ../tickets/epic-7/CTX-701A.md
    - ../tickets/epic-7/CTX-701.md
    - ../tickets/epic-7/CTX-702.md
    - ../tickets/epic-7/CTX-703.md
    - ../tickets/epic-7/CTX-704.md
    - ../tickets/epic-7/CTX-705.md
    - ../tickets/epic-7/CTX-706.md
---

# PHASE-7: Full LLM/ReAct Orchestrator Completion

## Goal

Complete the real AI runtime after the base Python gateway exists: LLM/ReAct orchestration, prompts, tool-call adapter, module connectors, sync/completion glue, and production-grade verification.

## Scope

- Full LLM/ReAct chat loop behind Python `/v1/chat/completions`.
- Prompt contracts, tool selection policy, context planning, and fallback/clarification behavior.
- Human-reviewable prompt and orchestration decision-flow design before runtime implementation.
- Tool-call schema registry and adapter execution for Finance, Second Brain, Homelab, and system services.
- Module connector layer that reuses existing APIs/services instead of duplicating business logic.
- Sync/completion gaps needed to make Open WebUI chat flows work end to end.
- RAG citation layout for Second Brain and Homelab answers, including source links suitable for Open WebUI display.
- Evaluation, replay, and E2E test harness for realistic chat scenarios.

## Out of Scope

- Rewriting Finance, Second Brain, or Homelab domain business logic.
- Creating separate databases per module. Cortex continues to use one shared PostgreSQL database with module-separated tables.
- Bypassing audit/permission policy for write-capable tools.
- Direct writes to Obsidian Vault or Homelab repo.

## Priority

High

## Success Criteria

- `/v1/chat/completions` can run real LLM-backed tool routing for supported read/capture/write-safe flows.
- Prompt contracts and orchestration state transitions are documented with examples before code implementation.
- Tool calls are schema-validated before execution.
- Write-capable actions use permission/confirmation gates.
- Finance, Second Brain, and Homelab connectors call existing domain APIs/services.
- RAG answers include citations when based on indexed documents.
- Second Brain citations include Markdown/Obsidian-friendly source links or labels derived from indexed source metadata.
- E2E/eval suite proves happy paths, ambiguous prompts, denied operations, and provider failure fallbacks.

## Risks

- LLM non-determinism can hide regressions without replay/evals.
- Tool adapters can accidentally duplicate domain logic.
- Writes can violate source-of-truth policy if permission/confirmation gates are skipped.
- Context injection can leak private or unapproved capture buffer data.

## Dependencies

- Epic 4 Python gateway and deterministic router are complete.
- Epic 5 Audit & Permissions should gate write-capable tools before production use.
- Existing module services and repositories must remain the source of business behavior.

## Verification Plan

- Unit tests for prompt policy, tool schema validation, adapter argument mapping, and clarification decisions.
- Integration tests for tool execution against real local PostgreSQL/pgvector.
- Provider smoke/eval tests with configured Google model.
- E2E chat tests for Finance, Second Brain, Homelab, denied writes, and fallback responses.
- Docs reconciliation for architecture, API, source-of-truth, and validation matrix.

## Completion Summary

- Pending implementation.
