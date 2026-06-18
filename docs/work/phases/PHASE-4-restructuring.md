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
---

# PHASE-4-restructuring: AI Service Restructuring & gRPC Integration

## Goal
Restructure the Python AI codebase into clean modular sub-packages under `ai_service` and implement gRPC communication between the Go Backend Gateway and the Python AI Service.

## Scope
- Renaming the Python codebase directory from `src/secondbrain` to `src/ai_service`.
- Isolating layers into separate modules (`core`, `secondbrain`, `homelab`, `orchestrator`, `grpc`).
- Creating `src/proto/cortex.proto` containing the service schemas.
- Generating Python and Go stub classes from protobuf files.
- Implementing the Python gRPC server mapping service calls.
- Implementing the Go gRPC client and proxying HTTP traffic via Echo handlers.
- Upgrading Go and Python test suites.

## Out of Scope
- Implementing the full Chat Orchestrator LLM loop (since it is part of the next Phase/Epic).
- Implementing audit logging database tables and capability guards (which are part of Phase 4/Epic 4 security checks).

## Priority
High

## Success Criteria
- Echo backend runs HTTP REST handlers that proxy commands to the Python gRPC server.
- All RAG search and link checker tests pass under the new restructured codebase.
- Protobuf contracts are clean, version-independent, and generated code compiles successfully.

## Verification Plan

- Python AI service unit/integration suite.
- Go backend full suite, including Finance regression tests and AI gateway tests.
- Opt-in real Google model smoke with local credentials.
- Local curl E2E through Go Gateway to Python gRPC.

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

Final evidence:

- `go test ./...` passes.
- `PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v` passes, 24 tests OK.
- Opt-in Google smoke passes, 2 tests OK.
- Curl E2E through `scripts/run-ai-gateway-dev.sh` passes for health, capture create/list/status, Homelab link validation, sync, and search.
