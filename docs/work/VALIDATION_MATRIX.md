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
| REQ-003 | PHASE-1 | CTX-101 | Wallet CRUD, balance query, active/archived state, and archive guard for future transaction writes | yes | yes | no | not_required | no | yes | in_progress | Code added in `src/backend/internal/modules/finance/`; `go test ./...` pass. Pending DB integration and full AC tests. |
| REQ-005 | PHASE-1 | CTX-102 | Category CRUD with parent/child hierarchy and alias support | yes | yes | no | not_required | no | yes | in_progress | Code added in `src/backend/internal/modules/finance/`; `go test ./...` pass. Pending DB integration and full AC tests. |
| REQ-003 | PHASE-1 | CTX-103 | Income/expense transaction API validates wallet/category/amount and updates wallet balance | yes | yes | no | not_required | no | yes | in_progress | Code added in `src/backend/internal/modules/finance/`; `go test ./...` pass. Pending DB integration and full AC tests. |
| REQ-003 | PHASE-1 | CTX-104 | Transfer transaction API creates paired transfer_out/transfer_in rows with one transfer_group_id, moves funds atomically, and does not change net worth | yes | yes | no | not_required | no | yes | in_progress | Code added in `src/backend/internal/modules/finance/`; `go test ./...` pass. Pending DB integration and full AC tests. |
| REQ-004 | PHASE-1 | CTX-105 | Asset master API manages investment definitions, asset units, price sources, and active state | yes | yes | no | not_required | no | yes | in_progress | Code added in `src/backend/internal/modules/finance/`; `go test ./...` pass. Pending DB integration and full AC tests. |
| REQ-004 | PHASE-1 | CTX-106 | Asset transaction API records buy/sell/dividend behavior, cash movement, holdings, rebuildable cost basis, and price history | yes | yes | no | not_required | no | yes | in_progress | Code added in `src/backend/internal/modules/finance/`; `go test ./...` pass. Pending DB integration and full AC tests. |
| REQ-005 | PHASE-1 | CTX-107 | Reporting API aggregates ordinary income/expenses separately from investment cash movements by occurred_at business period using indexed query shapes | yes | yes | no | not_required | no | yes | in_progress | Code added in `src/backend/internal/modules/finance/`; `go test ./...` pass. Pending DB integration and full AC tests. |
| NFR-006 | PHASE-1 | CTX-101..CTX-109 | Finance tables include created/updated actor and timestamp fields; soft-delete fields are limited to correction flows and soft-deleted records are excluded from reports/rebuilds/debt settlement | yes | yes | no | not_required | no | yes | in_progress | Code and migration added; `go test ./...` pass. Pending live migration smoke test. |
| REQ-004 | PHASE-1 | CTX-108 | Net worth API calculates cash plus current market-valued assets minus v1 liabilities with deterministic price selection and gain output | yes | yes | no | not_required | no | yes | in_progress | Code added in `src/backend/internal/modules/finance/`; `go test ./...` pass. Pending DB integration and full AC tests. |
| REQ-010 | PHASE-1 | CTX-109 | Debt and loan tracking supports i_owe and owed_to_me, linked cash movement, remaining balance, status, and net-worth impact | yes | yes | no | not_required | no | yes | in_progress | Code added in `src/backend/internal/modules/finance/`; `go test ./...` pass. Pending DB integration and full AC tests. |
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
