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

- Status: Epic 3 Homelab Readonly RAG & Link Validation completed and verified. Epic 4 Audit & Permissions is ready for planning.
- Active backlog: `docs/work/BACKLOG.md`
- Current queue focus: `BL-006`
- Active phase: docs/work/phases/PHASE-4-audit-policy.md
- Active ticket: docs/work/tickets/CTX-401.md, docs/work/tickets/CTX-402.md
- Active bug: None.

## Current Focus

Complete Epic 3 Homelab Readonly RAG & Link Validation, verifying it successfully runs over the real exam directory. Prepare detail design and implementation plan for Epic 4: Audit & Permissions.

## Recently Touched Areas

- `AGENTS.md`
- `docs/CONTEXT.md`
- `docs/work/VALIDATION_MATRIX.md`
- `docs/work/BACKLOG.md`
- `docs/work/phases/PHASE-3-homelab.md`
- `docs/work/tickets/epic-3/CTX-301.md`
- `docs/work/tickets/epic-3/CTX-302.md`
- `docs/work/tickets/epic-3/DETAIL_DESIGN.md`
- `src/secondbrain/homelab.py`
- `src/secondbrain/repository.py`
- `src/secondbrain/api.py`
- `src/secondbrain/models.py`
- `src/secondbrain/tests/test_homelab.py`
- `src/secondbrain/tests/test_api_runtime.py`

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
- `src/secondbrain/`

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
- Epic 1 Finance implementation has passed all exhaustive edge-case and E2E integration tests natively against PostgreSQL. All tickets verified and committed.
- Second Brain has moved out of `src/backend/internal/modules/secondbrain` into standalone Python service path `src/secondbrain`.
- Second Brain implementation starts with deterministic, testable core behavior before external LLM calls: capture lifecycle, Markdown/frontmatter parsing, heading-aware chunking, sync counts, policy-safe search, wiki/staging priority ranking, query expansion, and optional FastAPI adapter.
- Second Brain DB naming is standardized around `secondbrain_captures`, `secondbrain_documents`, and `secondbrain_document_chunks`; Python service uses the shared PostgreSQL instance/database with prefixed table ownership.
- Second Brain local PostgreSQL integration test uses `dev/password` against database `cortex`, indexes 91 real local Vault markdown files, and passes 18/18 ground-truth retrieval checks.
- `pgvector` is installed in the local Docker `postgres` container and enabled in database `cortex` as extension `vector` version `0.8.2`; `secondbrain_document_chunks.embedding` is verified as DB type `vector`.
- Python Second Brain reads DB/model settings from environment variables and has versioned SQL migrations under `src/secondbrain/migrations/`; migration `000001_secondbrain_pgvector` is applied in local DB `cortex` and sets embeddings to `VECTOR(768)`.
- Google model smoke tests are implemented and opt-in with `SECOND_BRAIN_RUN_GOOGLE_SMOKE=true`; local attempt successfully connects and validates API/model/key for Gemini generation and embedding models.
- **Real Google AI Embeddings** are fully integrated: The original deterministic hashes have been replaced by real `gemini-embedding-2` calls using Python's standard `urllib.request` library with exponential backoff handling to bypass rate limits. All 91 ground truth local documents were successfully embedded and verified natively with Google API.
- **Checksum Sync Optimization**: RAG Sync operations now bypass unmodified documents using checksum-matching against existing metadata in the database, protecting API limits and reducing sync time drastically.
- Architecture decision update: Python owns Orchestrator/LLM tool runtime and AI/RAG-heavy processing; Go is preferred for API-heavy deterministic services; Go↔Python communication uses internal gRPC. FastAPI is retained only as a Python dev/debug adapter.

## Next Steps

- Prepare the DETAIL_DESIGN.md and implementation plan for Epic 4 Audit & Permissions.
- Implement event logging and capability guard policy service in Go/Python.

## Open Questions

- None.
