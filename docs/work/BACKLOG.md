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
| 1 | BL-001 | framework | blocked | Finalize first project-specific standards | Medium | blocked | `docs/standards/` | Standards change | Human-maintained standards content | Blocked on human-authored project-specific standards; agents may propose changes but must not silently define human-maintained rules. |
| 2 | BL-002 | feature | normal | Epic 0: Setup Base | High | done | `docs/work/phases/PHASE-0-setup-base.md` | Deployment/runtime | `docs/work/tickets/CTX-001.md` | Reconciled as verified: Go module, DB/migrations, core errors, validator/logger, and tests are in place. |
| 3 | BL-003 | feature | high-risk | Epic 1: Finance APIs | High | verified | `docs/work/phases/PHASE-1-finance.md` | Data model, Multi-domain | `docs/work/tickets/epic-1/CTX-101.md` | Core Finance domain APIs for wallet, category, tx, assets |
| 4 | BL-004 | feature | normal | Epic 2: Second Brain | Medium | done | `docs/work/phases/PHASE-2-second-brain.md` | External system/provider | `docs/work/tickets/epic-2/CTX-201.md` | Capture buffer and Vault RAG |
| 5 | BL-005 | feature | normal | Epic 3: Homelab | Low | done | `docs/work/phases/PHASE-3-homelab.md` | External system/provider | `docs/work/tickets/epic-3/DETAIL_DESIGN.md` | Read-only query over homelab docs |
| 6 | BL-008 | feature | high-risk | Epic 4 Restructuring & gRPC | High | done | `docs/work/phases/PHASE-4-restructuring.md` | Standards change | `docs/work/tickets/epic-4/CTX-411.md` | CTX-403 through CTX-411 verified; Python gateway `/v1/chat/completions` now routes into existing module services over the shared DB. |
| 7 | BL-010 | feature | high-risk | Second Brain Obsidian MinIO webhook sync | High | done | `docs/work/tickets/epic-2/CTX-204.md` | External system/provider, Public contract/API, Deployment/runtime, Audit/security/privacy | `docs/work/tickets/epic-2/DETAIL_DESIGN_MINIO_WEBHOOK.md` | Implemented local S3/MinIO simulation, authenticated webhook route, gRPC sync RPC, and checksum-aware indexing for `second-brain/` Markdown objects. |
| 8 | BL-006 | feature | high-risk | Epic 5: Audit & Permissions | High | done | `docs/work/phases/PHASE-5-audit-policy.md` | Audit/security/privacy | `docs/work/tickets/CTX-501.md` | CTX-501 and CTX-502 verified; added audit event persistence and static v1 capability guard with audit-backed decisions. |
| 9 | BL-007 | feature | high-risk | Epic 6: Orchestrator | High | blocked | `docs/work/phases/PHASE-6-orchestrator.md` | Public contract/API | `docs/work/tickets/CTX-601.md` | Excluded from autonomous work; superseded by human-supervised Epic 7 prompt/orchestrator/LLM tickets. |
| 10 | BL-009 | feature | high-risk | Epic 7: Full LLM/ReAct Orchestrator Completion | High | ready | `docs/work/phases/PHASE-7-orchestrator-completion.md` | Public contract/API, External system/provider, Multi-domain, Audit/security/privacy | `docs/work/tickets/epic-7/CTX-702.md` | CTX-701A design gate is done; CTX-700 shared orchestration contracts and CTX-701 conversation/confirmation state are verified; next slice is Telegram bot transport adapter before LLM/runtime wiring. |
| 11 | BL-011 | feature | high-risk | Epic 8: Async Ingestion & Delete Sync Hardening | High | done | `docs/work/phases/PHASE-8-ingestion-hardening.md` | External system/provider, Deployment/runtime, Data model, Existing behavior | `docs/work/tickets/epic-8/CTX-801.md` | CTX-801 and CTX-802 verified; webhook now returns `202 Accepted` after job persistence, worker processes upsert/delete jobs, and delete sync removes stale RAG chunks. |
| 12 | BL-012 | feature | high-risk | Phase 9: React/Tailwind Client Console | High | done | `docs/work/phases/PHASE-9-client-console.md` | Auth, Public contract/API, Deployment/runtime, Existing behavior | `docs/work/tickets/client-console/CTX-901.md` | CTX-901 verified; FastAPI serves React/Tailwind `/ui`, app routes require internal single-user JWT, and `/v1/chat/completions` supports OpenAI-compatible SSE streaming. |
