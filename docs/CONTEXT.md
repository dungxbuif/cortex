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
- Active phase: `docs/work/phases/PHASE-APP-1.md`
- Active ticket: None.
- Active bug: None.

## Current Focus

Establish the markdown framework that keeps human and AI agents aligned across planning, implementation, verification, release, and maintenance.

## Recently Touched Areas

- `AGENTS.md`
- `docs/`
- `docs/templates/`
- `docs/standards/`
- `docs/work/phases/PHASE-APP-1.md`
- `docs/work/tickets/CORTEX-*.md`

## Recent Decisions

- Keep `AGENTS.md` at the repository root for agent discovery.
- Keep shared state in `docs/CONTEXT.md`.
- Use markdown-only enforcement for v1.
- Use `docs/work/phases/` for multi-ticket work.
- Use pay-as-you-go documentation for brownfield projects.
- Preserve existing harness `PHASE-2`; use `PHASE-APP-1` for Cortex app MVP planning from `docs/raw_spec/`.
- Treat app implementation tickets as high-risk unless proven otherwise because they touch API, data, security, runtime, external sources, or multi-domain behavior.
- Use JIRA-style ticket keys for app work: `CORTEX-1`, `CORTEX-2`, etc.
- Group app work by epic: Epic 1 Base Platform, Epic 2 Finance App, Epic 3 Second Brain App, Epic 4 Homelab App.
- Plan API/domain contracts before orchestrator integration; `CORTEX-6` stays inside Epic 1 but depends on the base API tickets.

## Next Steps

- Choose whether `BL-001` or `BL-APP-001` is the next active queue item.
- If app work proceeds, start with Epic 1 Base Platform: `CORTEX-1` detail design before implementation.
- Reconcile raw app spec into master requirements and architecture docs during implementation tickets.
- Add project-specific human standards under `docs/standards/`.

## Open Questions

- Should Cortex app MVP (`BL-APP-001`) preempt framework standards finalization (`BL-001`)?
- Confirm whether Epic 1 should include any additional base ticket before `CORTEX-1`.
