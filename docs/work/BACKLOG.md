---
artifact_type: backlog
id: BACKLOG
status: active
owner: shared
human_fields:
  - priority_override
  - rank
  - blocker_decisions
ai_fields:
  - risk_flags
  - lane_recommendation
  - next_artifact
  - notes
shared_fields:
  - queue_items
  - status
updated: TBD
---

# Backlog

## Field Ownership

- Human owns priority overrides, rank changes, and blocker decisions.
- AI may recommend lane, risk flags, next artifact, and notes.
- Shared fields include queue rows and item status.

Use this file as the runtime work queue.

The backlog decides what should be worked on next. It does not replace tickets, bugs, requirements, phases, detail designs, or verification artifacts.

## Queue Rules

- Backlog order MAY change at runtime based on priority, severity, dependency, or new information.
- Bugs MAY preempt feature tickets when severity or user impact is higher.
- New requirements MAY enter the backlog before they become requirements docs, phases, or tickets.
- Maintenance and framework work MAY appear in the same queue as product work.
- The active queue focus MUST be reflected in `docs/CONTEXT.md`.
- Do not process all tickets before bugs by default; process the highest-priority queue item that is ready and appropriately scoped.

## Intake Rules

- Keep each item short and actionable.
- Link to source context, requirement, phase, ticket, bug, or decision when available.
- Classify each item by lane: `tiny`, `normal`, `high-risk`, or `blocked`.
- Promote non-tiny backlog items into a requirement slice, phase, ticket, or bug before execution.
- Do not execute directly from backlog unless the item is clearly tiny and records a small-task exemption.
- High-risk items require detail design approval before implementation.
- Blocked items must record the missing decision, dependency, or input.

## Lane Guide

| Lane | Use When | Required Next Artifact |
| --- | --- | --- |
| tiny | Low-risk docs/copy/naming/narrow edits with no contract or runtime impact | Backlog row may be enough with small-task exemption |
| normal | Bounded story-sized work, bug fix, or maintenance task | Ticket or bug |
| high-risk | Auth, authorization, data, security, public contract, external provider, migration, major dependency, or multi-domain impact | Ticket/bug plus detail design and approval |
| blocked | Work cannot proceed because input, decision, dependency, or environment is missing | Blocker note and owner |

## Risk Flags

Mark risk flags in the `Risk Flags` column when relevant:

- Auth
- Authorization
- Data model
- Migration/data loss
- Audit/security/privacy
- External system/provider
- Public contract/API
- Existing behavior
- Weak proof
- Multi-domain
- Deployment/runtime
- Standards change

## Items

| Rank | ID | Type | Lane | Title | Priority | Status | Links | Risk Flags | Next Artifact | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | BL-001 | framework | normal | Finalize first project-specific standards | Medium | open | `docs/standards/` | Standards change | TBD | Add human-maintained rules in `docs/standards/`. |
