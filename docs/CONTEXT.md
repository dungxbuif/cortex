---
artifact_type: project_context
id: CONTEXT
status: active
owner: shared
human_fields:
  - current_focus
  - open_questions
  - priority_override
ai_fields:
  - recently_touched_areas
  - recent_decisions
  - next_steps
  - queue_summary
shared_fields:
  - current_status
  - active_backlog
  - current_queue_focus
  - active_phase
  - active_ticket
  - active_bug
updated: TBD
---

# Project Context

## Field Ownership

- Human owns project intent, priority overrides, and unresolved product questions.
- AI owns concise state refreshes after work: touched areas, recent decisions, next steps, and queue summary.
- Shared fields can be updated by either human or AI, but AI must not silently override human priority.

## Current Status

- Status: Initial SDLC agent framework scaffold plus Cortex app MVP ticket planning.
- Active backlog: `docs/work/BACKLOG.md`
- Current queue focus: `BL-APP-001` after `BL-001`, pending human priority choice.
- Active phase: docs/work/phases/PHASE-1-finance.md
- Active ticket: docs/work/tickets/epic-1/CTX-101.md
- Active bug: None.

## Current Focus

Review Epic 1 Finance API implementation and add remaining exhaustive per-ticket edge-case tests.

## Recently Touched Areas

- `AGENTS.md`
- `docs/`
- `docs/templates/`
- `docs/standards/`
- `docs/work/phases/PHASE-1-finance.md`
- `docs/work/tickets/epic-1/CTX-101.md`
- `docs/work/tickets/epic-1/DETAIL_DESIGN.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/architecture/API.md`
- `docs/architecture/ERD.md`
- `docs/requirements/SPEC.md`
- `docs/requirements/REQUIREMENTS.md`

## Recent Decisions

- Keep `AGENTS.md` at the repository root for agent discovery.
- Keep shared state in `docs/CONTEXT.md`.
- Use markdown-only enforcement for v1.
- Use `docs/work/phases/` for multi-ticket work.
- Use pay-as-you-go documentation for brownfield projects.
- Preserve existing harness `PHASE-2`; use `PHASE-APP-1` for Cortex app MVP planning from `docs/raw_spec/`.
- Treat app implementation tickets as high-risk unless proven otherwise because they touch API, data, security, runtime, external sources, or multi-domain behavior.
- Use JIRA-style ticket keys for app work: `CORTEX-1`, `CORTEX-2`, etc. (mapped to `CTX-xxx`).
- Group app work by epic: Epic 1 Base Platform, Epic 2 Finance App, Epic 3 Second Brain App, Epic 4 Homelab App.
- Plan API/domain contracts before orchestrator integration.
- Epic 1 Finance tickets are grouped under `docs/work/tickets/epic-1/`.
- Epic 1 Finance services share one detail design because wallet, category, transaction, asset, reporting, and net-worth services depend on shared balance and persistence invariants.
- Epic 1 asset design must model historical transactions, current holdings, market price history, and portfolio valuation separately so net worth uses current value while expense reports ignore investment buys.
- Master architecture, API, ERD, and requirements docs have been reconciled with the Epic 1 Finance asset valuation model.
- Epic 1 optimization rules: holdings are rebuildable projections, price selection is deterministic by asset class, investment cash movements are excluded from ordinary reports by default, saving deposits are assets only when term/interest behavior exists, debt/loan records distinguish `i_owe` liabilities from `owed_to_me` receivables, financial reports use business-effective dates such as `occurred_at`, finance tables carry `created_at/by` plus `updated_at/by`, money is stored as integer minor units, asset quantities use fixed precision decimals, and transfers are paired rows sharing `transfer_group_id`.
- Epic 1 Finance implementation now has split domain/service files, DTOs, GORM-backed service logic, migrations, hard-coded single-user `owner-single-user`, external test packages under `domain/tests` and `service/tests`, and local PostgreSQL integration proof. Tickets remain `in_review` until remaining exhaustive edge-case tests are added.

## Next Steps

- Add remaining per-ticket edge-case tests for CTX-101 through CTX-109, especially asset quantity arithmetic, price priority, report include-investments behavior, and correction/reversal flows.

## Open Questions

- Should Cortex app MVP (`BL-APP-001`) preempt framework standards finalization (`BL-001`)?
- Confirm whether Epic 1 should include any additional base ticket before `CORTEX-1`.
