---
artifact_type: phase
id: PHASE-4-restructuring
status: done
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
    - BL-008
  roadmap: ROADMAP
  requirements: []
  tickets:
    - ../tickets/epic-4/CTX-403.md
    - ../tickets/epic-4/CTX-404.md
    - ../tickets/epic-4/CTX-405.md
    - ../tickets/epic-4/CTX-406.md
    - ../tickets/epic-4/CTX-407.md
    - ../tickets/epic-4/CTX-408.md
    - ../tickets/epic-4/CTX-409.md
    - ../tickets/epic-4/CTX-410.md
    - ../tickets/epic-4/CTX-411.md
---

# PHASE-4-restructuring: AI Service Restructuring & gRPC Integration

## Goal
Restructure the Python AI codebase into clean modular sub-packages under `ai_service`, implement internal gRPC contracts, and expose the Python-owned OpenAI-compatible gateway/orchestrator path.

## Scope
- Renaming the Python codebase directory from `src/secondbrain` to `src/ai_service`.
- Isolating layers into separate modules (`core`, `secondbrain`, `homelab`, `orchestrator`, `grpc`).
- Creating `src/proto/cortex.proto` containing the service schemas.
- Generating Python and Go stub classes from protobuf files.
- Implementing the Python gRPC server mapping service calls.
- Implementing the Go gRPC client and proxying HTTP traffic via Echo handlers.
- Implementing the Python gateway route `/v1/chat/completions` that routes chat into existing Second Brain and Homelab services.
- Upgrading Go and Python test suites.

## Out of Scope
- Implementing the full Chat Orchestrator LLM/ReAct loop (since it is part of the next Phase/Epic).
- Implementing audit logging database tables and capability guards (which are part of Phase 4/Epic 4 security checks).
- Removing existing Go gateway code.

## Priority
High

## Success Criteria
- Python gateway exposes an OpenAI-compatible chat route that delegates into the existing module services.
- Echo backend REST proxy remains regression-tested but is not the primary orchestrator gateway.
- All RAG search and link checker tests pass under the new restructured codebase.
- Protobuf contracts are clean, version-independent, and generated code compiles successfully.

## Verification Plan

- Python AI service unit/integration suite.
- Go backend full suite, including Finance regression tests and AI gateway tests.
- Opt-in real Google model smoke with local credentials.
- Python gateway and Python gRPC orchestrator runtime tests.

## Completion Summary

Epic 4 is complete and verified.

- CTX-403 repaired the renamed `ai_service.*` Python package baseline.
- CTX-404 isolated AI provider access behind `Embedder` and provider adapters.
- CTX-405 split Second Brain and Homelab repositories/models into domain-owned modules.
- CTX-406 split domain helper logic and moved embedding attachment to service orchestration.
- CTX-407 implemented Python gRPC server and handlers.
- CTX-408 implemented Go protobuf stubs, gRPC client, and Echo proxy routes.
- CTX-409 added local runtime harness scripts.
- CTX-410 verified real local Go Gateway -> Python gRPC E2E for Second Brain and Homelab paths.
- CTX-411 added the Python-owned OpenAI-compatible gateway/orchestrator full flow for chat capture and Homelab search over the existing module services.

Final evidence:

- `go test ./...` passes.
- `PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v` passes, 25 tests OK.
- Opt-in Google smoke passes, 2 tests OK.
- Curl E2E through `scripts/run-ai-gateway-dev.sh` passes for health, capture create/list/status, Homelab link validation, sync, and search.
- Python gateway `/v1/chat/completions` and Python gRPC `OrchestratorService.ChatCompletions` tests pass against the same module services.
