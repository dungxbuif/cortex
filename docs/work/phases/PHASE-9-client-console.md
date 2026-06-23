---
artifact_type: phase
id: PHASE-9-client-console
status: done
owner: shared
human_fields:
  - approval
  - acceptance
ai_fields:
  - implementation_notes
  - verification
shared_fields:
  - scope
  - trace_links
---

# Phase 9: Client Console

## Scope

Implement a React/Tailwind Cortex client console served by the existing Python FastAPI gateway.

In scope:

- Browser-accessible React/Tailwind chat workspace at `/ui`.
- Same-origin built assets under `/ui/assets/*`.
- One hard-coded internal user with backend JWT validation.
- Single chat conversation with OpenAI-compatible SSE streaming.
- Tabs reserved for future module-specific UIs: Chat, Second Brain, Homelab, Finance, Ingestion, Audit.
- Regression tests proving UI routes/assets, JWT auth, and SSE are available.
- Documentation reconciliation for API, backlog, validation matrix, changelog, and context.

Out of scope:

- LLM prompt/ReAct runtime implementation.
- Multi-user management and auth UI.
- Finance write UX until the confirmed Finance API surface is exposed through the active Python gateway.

## Approval

Approved for immediate implementation by user request and follow-up decisions:

- React/Tailwind client.
- One chat conversation only.
- Tabs for future dedicated UIs.
- Hard-coded single user UUID `11111111-1111-1111-1111-111111111111`.
- Backend JWT check retained with an internal non-expiring token.
- OpenAI SSE-compatible streaming.

## Trace Links

- Backlog: `docs/work/BACKLOG.md`
- Ticket: `docs/work/tickets/client-console/CTX-901.md`
- Detail design: `docs/work/tickets/client-console/DETAIL_DESIGN.md`
- Validation: `docs/work/VALIDATION_MATRIX.md`
- API docs: `docs/architecture/API.md`
- ADR: `docs/decisions/ADR-005-internal-single-user-jwt.md`
- Release notes: `docs/releases/CHANGELOG.md`

## Verification

- `rtk npm run test` in `src/client`: pass, 2 tests.
- `rtk npm run build` in `src/client`: pass.
- `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_api_runtime.FastAPIRuntimeTest -v`: pass.
- `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v`: pass, 33 tests OK, 1 Google smoke skipped.
- `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...` from `src/backend`: pass.
- `rtk bash -n scripts/simulate-secondbrain-s3-action.sh`: pass.
- `rtk git diff --check`: pass.
- Playwright screenshot verification: `/private/tmp/cortex-ui-desktop.png` and `/private/tmp/cortex-ui-mobile.png` captured from FastAPI `/ui`; rendered assets loaded and layout was nonblank/responsive.
- SSE smoke: local `/v1/chat/completions` returned OpenAI-style `data:` chunks and `data: [DONE]`.
