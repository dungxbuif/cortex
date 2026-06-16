---
artifact_type: roadmap
id: ROADMAP
status: active
owner: human
human_fields:
  - milestones
  - priority
  - phase_order
ai_fields:
  - phase_links
  - status_summaries
shared_fields:
  - milestone_status
updated: TBD
---

# Roadmap

## Field Ownership

- Human owns milestones, priority, and phase order.
- AI maintains phase links and status summaries.

Use this file to group work into milestones or major phases.

## Roadmap Rules

- A roadmap item becomes executable only after it has a phase file in `docs/work/phases/`.
- Each phase should contain one or more tickets or bugs.
- Completed phases should link to release notes or changelog entries when relevant.

## Milestones

| Milestone | Goal | Status | Phase Files |
| --- | --- | --- | --- |
| M0 | Establish SDLC agent framework | active | TBD |
| M1 | Phase 2: Develop Harness CLI (Hard Enforcement) | ready | [PHASE-2.md](phases/PHASE-2.md) |
