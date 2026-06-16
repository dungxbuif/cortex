---
artifact_type: validation_matrix
id: VALIDATION_MATRIX
status: active
owner: shared
human_fields:
  - proof_override
  - acceptance_signoff
ai_fields:
  - proof_recommendation
  - evidence_links
  - status_updates
shared_fields:
  - matrix_rows
  - validation_status
updated: TBD
---

# Validation Matrix

## Field Ownership

- Human owns proof overrides and acceptance sign-off.
- AI recommends proof types, links evidence, and updates status from verification.

This file maps accepted behavior and work items to proof.

Policy lives in `docs/standards/VALIDATION.md`. This matrix is runtime project state and should change as work is planned, implemented, changed, or retired.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built or verified |
| implemented | Implemented and evidence exists |
| changed | Contract or expected proof changed after earlier implementation |
| retired | No longer part of the accepted project contract |

## Matrix

| Requirement | Phase | Ticket/Bug | Contract/Behavior | Unit | Integration | E2E | UAT | Platform/Manual | Docs Review | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | Add rows when requirements, tickets, or bugs are created | no | no | no | no | no | no | planned | none |
| Epic 1 Base permission/audit | PHASE-APP-1 | CORTEX-1 | Capability policy gates module operations and append-only audit APIs record sensitive operations safely | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 1 Base RAG/indexing | PHASE-APP-1 | CORTEX-2 | Shared RAG/indexing APIs parse, redact, chunk, retrieve, cite sources, and exclude disallowed sources | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 1 Base runtime | PHASE-APP-1 | CORTEX-6 | OpenAI-compatible chat runtime validates tool calls and delegates through pre-planned API boundaries | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 2 Finance App | PHASE-APP-1 | CORTEX-5 | Finance transaction APIs validate natural language writes, confirm ambiguity/high impact, and audit persistence | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 3 Second Brain App | PHASE-APP-1 | CORTEX-3 | Capture APIs store temporary notes without direct Vault writes or RAG access to capture buffer | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 4 Homelab App | PHASE-APP-1 | CORTEX-4 | Homelab sync/index/RAG APIs are read-only, redacted, cited by repo path and commit, and deny edits/actions | yes | yes | no | yes | yes | yes | planned | Ticket acceptance criteria |

## Rules

- Add or update a row when a requirement, ticket, bug, public contract, or accepted behavior is created or changed.
- Mark proof columns `yes`, `no`, or `not_required`.
- Link evidence to `docs/templates/TEST_VERIFICATION.md`, ticket verification sections, UAT, docs review, release notes, or command output summaries.
- Do not set `implemented` until required proof has evidence.
- If a proof type is `not_required`, record the reason in the linked ticket, bug, or verification artifact.
