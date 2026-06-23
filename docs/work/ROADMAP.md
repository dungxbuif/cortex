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
| M2 | Cortex app MVP ticket plan from raw spec | ready | [PHASE-APP-1.md](phases/PHASE-APP-1.md) |
| M3 | Cortex implementation epics and remaining orchestration completion work | ready | [PHASE-0](phases/PHASE-0-setup-base.md), [PHASE-1](phases/PHASE-1-finance.md), [PHASE-2](phases/PHASE-2-second-brain.md), [PHASE-3](phases/PHASE-3-homelab.md), [PHASE-4](phases/PHASE-4-restructuring.md), [PHASE-5](phases/PHASE-5-audit-policy.md), [PHASE-6](phases/PHASE-6-orchestrator.md), [PHASE-7](phases/PHASE-7-orchestrator-completion.md) |
| M4 | Post-MVP ingestion hardening and RAG consistency | ready | [PHASE-8](phases/PHASE-8-ingestion-hardening.md) |
