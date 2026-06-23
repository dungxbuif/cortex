---
artifact_type: detail_design
id: CTX-901-DESIGN
status: approved
owner: shared
human_fields:
  - approval
ai_fields:
  - design
  - test_plan
shared_fields:
  - scope
  - trace_links
---

# CTX-901 Detail Design: FastAPI-Served Cortex Client Console

## Problem

Cortex has working Python gateway routes for health, Second Brain, Homelab, chat, and async ingestion, but there is no React/Tailwind client UI phase or browser surface for manual operation and Q&A. The user asked to implement client code immediately, approved the mockup, and then clarified that the current scope must use one chat conversation, future module tabs, hard-coded single-user JWT handling, and OpenAI-compatible SSE streaming.

## Context Loaded

- `docs/CONTEXT.md`
- `docs/work/BACKLOG.md`
- `docs/standards/README.md`
- `docs/standards/QUALITY_BAR.md`
- `docs/standards/VALIDATION.md`
- `docs/raw_spec/spec.md`
- `src/ai_service/api.py`
- `src/ai_service/tests/test_api_runtime.py`
- `docs/architecture/API.md`
- `docs/work/VALIDATION_MATRIX.md`
- `docs/releases/CHANGELOG.md`

## Brownfield Scope

Touched code stays inside the active Python gateway plus a new `src/client` React app. FastAPI serves the Vite build output under `/ui` so the browser client and API remain same-origin.

## Proposed Approach

- Add `src/client` with React, Vite, Tailwind, and focused component tests.
- Add `/ui` to `create_app`, returning `src/client/dist/index.html` with a fallback to the legacy static file while developing.
- Add `/ui/assets/{asset_path:path}` to serve Vite build assets safely from `src/client/dist/assets`.
- Build a chat-first workspace:
  - one single conversation,
  - tabs for future dedicated module UIs,
  - center chat transcript and composer,
  - right-side citations/tool-call/audit panels.
- Add `/api/auth/dev-token` to issue an internal non-expiring JWT for the hard-coded user.
- Require `Authorization: Bearer <token>` for application API routes.
- Ignore client-supplied `owner_id` for app routes and use UUID `11111111-1111-1111-1111-111111111111`.
- Support OpenAI-compatible SSE chunks from `/v1/chat/completions` when `stream: true`.
- Keep prompt/LLM ReAct design out of scope. The chat API may be visible as a future integration, but this ticket does not implement prompt behavior.

## Alternatives Considered

- Plain static app: rejected after user clarified the client must be React/Tailwind.
- Open WebUI customization only: rejected because the current repository still needs a testable first-party client surface for existing module APIs.
- Server-rendered templates: rejected because static assets are sufficient and avoid introducing template dependencies.

## Impact

- Code: `src/ai_service/api.py`, `src/client/*`, `src/ai_service/tests/test_api_runtime.py`.
- API: adds browser UI routes `/ui` and `/ui/assets/{asset_path:path}`, `/api/auth/dev-token`, app-route JWT validation, and SSE streaming support for `/v1/chat/completions`.
- Data: no schema change.
- Security: internal single-user JWT is enforced by backend; webhook token remains required for ingestion enqueue.
- Runtime: adds Node client dependencies and a Vite/Tailwind build step.
- Docs: API, backlog, validation matrix, changelog, context, phase, and ticket.

## Test Plan

- Client unit tests: `rtk npm run test`
- Client production build: `rtk npm run build`
- Focused API test: `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_api_runtime.FastAPIRuntimeTest -v`
- Full Python suite: `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v`
- Full Go suite: `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...`
- Script syntax: `rtk bash -n scripts/simulate-secondbrain-s3-action.sh`
- Diff hygiene: `rtk git diff --check`
- Visual/browser proof: Playwright desktop and mobile screenshots from FastAPI `/ui`.

## Approval

Approved by direct user instruction to implement the client after mockup review and follow-up clarification.

## Trace Links

- Phase: `docs/work/phases/PHASE-9-client-console.md`
- Ticket: `docs/work/tickets/client-console/CTX-901.md`
- Validation: `docs/work/VALIDATION_MATRIX.md`
- API docs: `docs/architecture/API.md`
- ADR: `docs/decisions/ADR-005-internal-single-user-jwt.md`
- Release notes: `docs/releases/CHANGELOG.md`
