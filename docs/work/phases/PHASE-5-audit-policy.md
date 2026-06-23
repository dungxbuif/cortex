---
artifact_type: phase
id: PHASE-5
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
  backlog_items: []
  roadmap: ROADMAP
  requirements: []
  tickets:
    - ../tickets/CTX-501.md\n    - ../tickets/CTX-502.md
---

# PHASE-5: Audit & Permission Guards

## Goal
Audit & Permission Guards

Implement the official capability policy and immutable audit trail that future tool calls, webhook clients, sync jobs, RAG queries, and write-capable actions must use before production use.

## Scope
Implementation of associated tickets.

- `CTX-501`: append-only audit/event persistence and query APIs.
- `CTX-502`: capability policy service and audit-backed allow/deny/confirmation decisions.
- Explicitly cover webhook clients such as n8n: authenticated clients must be authorized for capabilities such as `second_brain.index_external_source` before enqueueing or running ingestion work.
- Preserve current static-token webhook authentication only as an initial authentication mechanism; authorization and audit are owned by this phase.

## Success Criteria

- Permission decisions for write/sync/index/RAG-sensitive operations are centrally evaluated.
- `second_brain.index_external_source` can be checked for webhook clients before Second Brain indexing.
- Denied and allowed policy decisions are written to immutable audit events.
- Homelab write/runtime actions and direct Second Brain Vault writes are hard-denied.
- Finance high-impact writes require confirmation.

## Completion Summary

- CTX-501 and CTX-502 are verified.
- Added Go `system/audit` service with `audit_events` migration, append/get/list APIs, validation, and recursive secret-key rejection.
- Added Go `system/policy` service with static v1 capability matrix, allow/deny/confirmation decisions, webhook actor support for `second_brain.index_external_source`, and audit emission.
- Verification passed with focused system tests, full Go backend tests, and full Python AI suite.
