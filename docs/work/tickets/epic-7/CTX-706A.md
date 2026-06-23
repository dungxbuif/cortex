---
artifact_type: ticket
id: CTX-706A
status: ready
owner: shared
priority: High
lane: high-risk
trace:
  backlog_item: BL-009
  requirement: REQ-006
  phase: docs/work/phases/PHASE-7-orchestrator-completion.md
  detail_design: docs/work/tickets/epic-7/DETAIL_DESIGN.md
  test_verification: src/ai_service/tests/test_orchestrator_policy.py
  validation_matrix: docs/work/VALIDATION_MATRIX.md
  docs_review: docs/work/tickets/epic-7/CTX-706A.md#docs-review
  release_notes: docs/releases/CHANGELOG.md
---

# Ticket: CTX-706A Policy/Audit gRPC Bridge and Policy/Audit Enforcement

## Context

The Python orchestrator needs to check policies and persist audit events during tool execution. In Epic 5, Go modules for `system/audit` and `system/policy` were implemented, but they are currently internal Go modules without gRPC exposure. The Python orchestrator cannot access them natively. 

We need to implement a gRPC bridge for both `PolicyService` and `AuditService`, compile the stubs, wrap them on the Go side as a gRPC server, and build the corresponding Python `GrpcPolicyEnforcer` and `GrpcAuditSink` (or gRPC clients) to wire into the Python `ToolAdapterExecutor` (or tool execution engine).

This is a critical prerequisite for Finance writes/operations, as write-capable tools must not execute in production without policy check results and audit persistence.

## Scope

- Define the gRPC interfaces for `PolicyService` and `AuditService` in `src/proto/cortex.proto`.
  - `PolicyService` should expose policy check capability evaluation (allow/deny/require_confirmation).
  - `AuditService` should expose log/persist audit events.
- Run protobuf codegen for both Go and Python runtimes.
- Implement Go gRPC server wrappers for `system/policy` and `system/audit`.
- Implement Python `PolicyGrpcClient` (GrpcPolicyEnforcer) and `AuditGrpcClient` (GrpcAuditSink) to talk to the Go server.
- Wire the Python clients into the tool execution/executor engine (e.g. `ToolAdapterExecutor`).
- Implement integration/unit tests verifying the full flow:
  - Policy decisions: Allow (executes tool), Deny (blocks tool and returns denial observation), Require Confirmation (suspends loop, creates pending confirmation).
  - Audit logging: emits audit logs after tool execution.

## Out of Scope

- Implementing the React UI console or Telegram transport changes.
- Implementing Finance writes/operations themselves (handled in future Finance connector tickets).

## Acceptance Criteria

- [ ] Protobuf definitions compile successfully for both Go and Python.
- [ ] Go backend starts the gRPC server exposing `PolicyService` and `AuditService`.
- [ ] Python orchestrator calls `PolicyGrpcClient` to evaluate tool permissions.
- [ ] Python orchestrator emits audit events to `AuditGrpcClient` post-execution.
- [ ] Tool execution loop correctly routes to `Deny` (returns denial message) and `Require Confirmation` (halts loop and persists confirmation).
- [ ] Integration tests verify the end-to-end policy check, confirmation suspension, denial logic, and audit database persistence.

## Small Task Exemption

- Small task exemption: no

## Test Expectations

- Integration tests checking Python gRPC client requests to Go gRPC services (`PolicyService`, `AuditService`).
- Integration/unit tests verifying policy checks (allow, deny, confirm) and audit logs stored in the PostgreSQL database.

## Docs Review

- Requirements: no master requirement changes.
- Architecture: aligns with the Go↔Python gRPC architecture model.
- API: no public HTTP API changes; new internal gRPC endpoints defined in proto.
- ERD/Data: no schema changes.
- ADR: none required.
- Release notes: update `docs/releases/CHANGELOG.md`.
