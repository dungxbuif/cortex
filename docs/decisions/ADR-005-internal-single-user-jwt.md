---
artifact_type: adr
id: ADR-005
status: accepted
owner: shared
human_fields:
  - decision_context
ai_fields:
  - consequences
shared_fields:
  - decision
  - trace_links
---

# ADR-005: Internal Single-User JWT For Cortex Client

## Context

The current Cortex deployment is an internal network app for one user. The user explicitly requested no user-management UI, a hard-coded user UUID, and normal JWT-style backend checks using a non-expiring token.

## Decision

The Python FastAPI gateway issues a dev/internal JWT from `GET /api/auth/dev-token` and requires `Authorization: Bearer <token>` for application routes. The JWT uses HS256 with `CORTEX_INTERNAL_JWT_SECRET` or a local default, has no `exp`, and must carry subject `11111111-1111-1111-1111-111111111111`.

Application routes ignore client-supplied `owner_id` and use the verified single-user UUID. The n8n webhook keeps its existing `X-Cortex-N8n-Token` authentication.

## Alternatives Considered

- No auth at all: rejected because the user requested JWT checks to remain in backend logic.
- Full multi-user auth: rejected for current scope because the user explicitly does not need user management.
- Expiring JWT/refresh flow: rejected for current internal scope because the user asked for a non-expiring token.

## Consequences

- The React client can bootstrap itself without login by calling `/api/auth/dev-token`.
- Backend route tests can exercise normal bearer-token behavior.
- This is not an internet-facing security model. Before external exposure, Cortex needs real identity, expiry/rotation, and permission enforcement bound to users or service actors.

## Trace Links

- Phase: `docs/work/phases/PHASE-9-client-console.md`
- Ticket: `docs/work/tickets/client-console/CTX-901.md`
- API docs: `docs/architecture/API.md`
- Validation: `docs/work/VALIDATION_MATRIX.md`
