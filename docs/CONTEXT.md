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

- Status: Initial SDLC agent framework scaffold.
- Active backlog: `docs/work/BACKLOG.md`
- Current queue focus: None.
- Active phase: None.
- Active ticket: None.
- Active bug: None.

## Current Focus

Establish the markdown framework that keeps human and AI agents aligned across planning, implementation, verification, release, and maintenance.

## Recently Touched Areas

- `AGENTS.md`
- `docs/`
- `docs/templates/`
- `docs/standards/`

## Recent Decisions

- Keep `AGENTS.md` at the repository root for agent discovery.
- Keep shared state in `docs/CONTEXT.md`.
- Use markdown-only enforcement for v1.
- Use `docs/work/phases/` for multi-ticket work.
- Use pay-as-you-go documentation for brownfield projects.

## Next Steps

- Review `docs/work/BACKLOG.md` before selecting the next work item.
- Create the first roadmap or phase when implementation work begins.
- Fill product and architecture master docs as the project becomes concrete.
- Add project-specific human standards under `docs/standards/`.

## Open Questions

- No project-specific technology stack has been selected yet.
- No product requirements have been finalized yet.
