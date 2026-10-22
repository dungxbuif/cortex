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

- Status: Epic 5 Audit & Permissions, Epic 8 CTX-801 through CTX-803, Phase 9 React/Tailwind Client Console, and Epic 7 CTX-700 through CTX-708 are implemented and verified; eval/E2E proof remains human-supervised.
- Active backlog: `docs/work/BACKLOG.md`
- Current queue focus: Epic 8 work has advanced through `CTX-803`; next slice is `CTX-709` eval replay and E2E chat proof.
- Active phase: None.
- Active ticket: None.
- Active bug: None.

## Current Focus

Epic 4 is complete with Python-owned chat gateway routing into existing Second Brain and Homelab services. Epic 5 Audit & Permissions is verified. Epic 8 CTX-801 through CTX-803 are verified, including S3-compatible async ingestion, delete sync, and full-resync webhook triggers for Second Brain/Homelab. Phase 9 Client Console is verified with React/Tailwind, single-user JWT, and SSE. Epic 7 CTX-700 through CTX-708 are verified, including Telegram transport, module connectors, Finance read bridge, tool execution, policy/audit bridge, presentation, health, and graceful degradation. Remaining eval/E2E proof remains queued for human-supervised implementation.

## Recently Touched Areas

- `docs/work/BACKLOG.md`
- `docs/work/phases/PHASE-5-audit-policy.md`
- `docs/work/phases/PHASE-6-orchestrator.md`
- `docs/work/tickets/CTX-501.md`
- `docs/work/tickets/CTX-502.md`
- `docs/work/tickets/CTX-601.md`
- `docs/work/tickets/CTX-602.md`
- `docs/work/tickets/CTX-603.md`
- `docs/work/tickets/CTX-604.md`
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
- `docs/work/tickets/epic-4/DETAIL_DESIGN.md`
- `docs/work/tickets/epic-4/implementation_plan.md`
- `docs/work/tickets/epic-4/CTX-403.md`
- `src/ai_service/__init__.py`
- `src/ai_service/api.py`
- `src/ai_service/tests/test_api_runtime.py`
- `src/ai_service/tests/test_google_ai_smoke.py`
- `src/ai_service/tests/test_homelab.py`
- `src/ai_service/tests/test_postgres_real_vault_integration.py`
- `src/ai_service/tests/test_secondbrain_service.py`
- `docs/work/tickets/epic-4/CTX-404.md`
- `docs/work/tickets/epic-4/CTX-405.md`
- `src/ai_service/core/config.py`
- `src/ai_service/core/google_ai.py`
- `src/ai_service/core/ports.py`
- `src/ai_service/providers/`
- `docs/work/tickets/epic-4/CTX-406.md`
- `src/ai_service/secondbrain/models.py`
- `src/ai_service/secondbrain/repository.py`
- `src/ai_service/homelab/models.py`
- `src/ai_service/homelab/repository.py`
- `docs/work/tickets/epic-4/CTX-407.md`
- `docs/work/tickets/epic-4/CTX-408.md`
- `docs/work/tickets/epic-4/CTX-409.md`
- `docs/work/tickets/epic-4/CTX-410.md`
- `docs/work/phases/PHASE-7-orchestrator-completion.md`
- `docs/work/tickets/epic-7/DETAIL_DESIGN.md`
- `docs/work/tickets/epic-7/CTX-701A.md`
- `docs/work/tickets/epic-7/CTX-700.md`
- `docs/work/tickets/epic-7/CTX-701.md`
- `docs/work/tickets/epic-7/CTX-702.md`
- `docs/work/tickets/epic-7/CTX-703.md`
- `docs/work/tickets/epic-7/CTX-704.md`
- `docs/work/tickets/epic-7/CTX-705.md`
- `docs/work/tickets/epic-7/CTX-706.md`
- `docs/work/tickets/epic-7/CTX-707.md`
- `docs/work/tickets/epic-7/CTX-708.md`
- `docs/work/tickets/epic-7/CTX-709.md`
- `docs/work/tickets/epic-7/CTX-710.md`
- `docs/work/phases/PHASE-8-ingestion-hardening.md`
- `docs/work/tickets/epic-8/DETAIL_DESIGN.md`
- `docs/work/tickets/epic-8/CTX-801.md`
- `docs/work/tickets/epic-8/CTX-802.md`
- `src/backend/migrations/000002_audit_events.up.sql`
- `src/backend/migrations/000002_audit_events.down.sql`
- `src/backend/internal/modules/system/audit/`
- `src/backend/internal/modules/system/policy/`
- `src/ai_service/migrations/000003_secondbrain_ingestion_jobs.sql`
- `src/ai_service/homelab/redaction.py`
- `src/ai_service/homelab/link_validator.py`
- `src/ai_service/homelab/markdown.py`
- `src/ai_service/tests/test_domain_helpers.py`
- `src/ai_service/grpc/`
- `src/ai_service/grpc_server.py`
- `src/ai_service/tests/test_grpc_runtime.py`
- `src/backend/internal/infrastructure/grpc/`
- `src/backend/internal/modules/ai/`
- `src/backend/internal/config/config.go`
- `src/backend/cmd/server/main.go`
- `src/proto/cortex.proto`
- `scripts/run-ai-gateway-dev.sh`
- `scripts/check-ai-gateway.sh`
- `README.md`
- `docs/work/tickets/epic-2/CTX-204.md`
- `docs/work/tickets/epic-2/DETAIL_DESIGN_MINIO_WEBHOOK.md`
- `docs/raw_spec/system/external-automation.md`
- `src/ai_service/secondbrain/object_store.py`
- `src/ai_service/secondbrain/service.py`
- `src/ai_service/grpc/`
- `src/backend/internal/modules/ai/`
- `src/proto/cortex.proto`
- `scripts/simulate-secondbrain-s3-action.sh`
- `docs/work/phases/PHASE-9-client-console.md`
- `docs/work/tickets/client-console/DETAIL_DESIGN.md`
- `docs/work/tickets/client-console/CTX-901.md`
- `docs/decisions/ADR-005-internal-single-user-jwt.md`
- `src/client/`
- `src/ai_service/api.py`
- `src/ai_service/tests/test_api_runtime.py`
- `src/ai_service/orchestrator/contracts.py`
- `src/ai_service/orchestrator/conversation.py`
- `src/ai_service/orchestrator/telegram.py`
- `src/ai_service/migrations/000004_orchestrator_conversations.sql`
- `src/ai_service/tests/test_orchestrator_contracts.py`
- `src/ai_service/tests/test_orchestrator_conversation.py`
- `src/ai_service/tests/test_orchestrator_telegram.py`

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
- Second Brain has moved out of `src/backend/internal/modules/secondbrain` into standalone Python AI service path `src/ai_service`.
- Second Brain implementation starts with deterministic, testable core behavior before external LLM calls: capture lifecycle, Markdown/frontmatter parsing, heading-aware chunking, sync counts, policy-safe search, wiki/staging priority ranking, query expansion, and optional FastAPI adapter.
- Second Brain DB naming is standardized around `secondbrain_captures`, `secondbrain_documents`, and `secondbrain_document_chunks`; Python service uses the shared PostgreSQL instance/database with prefixed table ownership.
- Second Brain local PostgreSQL integration test uses `dev/password` against database `cortex`, indexes 91 real local Vault markdown files, and passes 18/18 ground-truth retrieval checks.
- `pgvector` is installed in the local Docker `postgres` container and enabled in database `cortex` as extension `vector` version `0.8.2`; `secondbrain_document_chunks.embedding` is verified as DB type `vector`.
- Python AI service reads DB/model settings from environment variables and has versioned SQL migrations under `src/ai_service/migrations/`; migration `000001_secondbrain_pgvector` is applied in local DB `cortex` and sets embeddings to `VECTOR(768)`.
- Google model smoke tests are implemented and opt-in with `SECOND_BRAIN_RUN_GOOGLE_SMOKE=true`; local attempt successfully connects and validates API/model/key for Gemini generation and embedding models.
- **Real Google AI Embeddings** are fully integrated: The original deterministic hashes have been replaced by real `gemini-embedding-2` calls using Python's standard `urllib.request` library with exponential backoff handling to bypass rate limits. All 91 ground truth local documents were successfully embedded and verified natively with Google API.
- **Checksum Sync Optimization**: RAG Sync operations now bypass unmodified documents using checksum-matching against existing metadata in the database, protecting API limits and reducing sync time drastically.
- Architecture decision update: Python owns Orchestrator/LLM tool runtime and AI/RAG-heavy processing; Go is preferred for API-heavy deterministic services; Go↔Python communication uses internal gRPC. FastAPI is retained only as a Python dev/debug adapter.
- Epic 4 is approved for incremental implementation by ticket breakdown: CTX-403 baseline/import repair, CTX-404 ports/providers, CTX-405 repository split, CTX-406 domain cleanup, CTX-407 Python gRPC, CTX-408 Go gateway, CTX-409 runtime harness, CTX-410 E2E/docs reconciliation.
- CTX-403 is verified: `ai_service.*` import root passes, all Python tests import the renamed package, non-smoke tests use deterministic fake embeddings, and the Python suite passes against local PostgreSQL/pgvector without requiring Google credentials outside the opt-in smoke test.
- CTX-404 is verified: `Embedder` port exists, Google provider code lives under `src/ai_service/providers/`, Second Brain and Homelab services no longer import `GoogleAIClient` directly, full Python suite passes, and opt-in Google smoke passes with `.env.local`.
- CTX-405 is verified: Second Brain and Homelab models/repositories are domain-owned, `core/repository.py` only contains shared SQL/psql helpers, repository contract tests pass against SQLite and local PostgreSQL/pgvector, and the full Python suite plus opt-in Google smoke pass.
- CTX-406 is verified: Second Brain and Homelab chunking produces raw chunks before embedding, Homelab redaction/link validation/chunking helpers are split into focused modules, pure helper tests pass, full Python suite passes, and opt-in Google smoke passes.
- CTX-407 is verified: Python protobuf stubs, gRPC handlers, and `grpc_server.py` expose Second Brain/Homelab service calls through generated clients; in-process gRPC tests pass, full Python suite passes, and opt-in Google smoke passes.
- CTX-408 is verified: Go protobuf stubs, AI service gRPC client, Echo proxy routes, and `AI_SERVICE_ADDRESS` config compile and test. `go test ./...`, Python AI suite, and opt-in Google smoke all pass.
- CTX-409 is verified: local harness starts Python AI gRPC and Go Gateway together, `/api/ai/health` passes through Go->Python gRPC, backend/Python tests pass, and opt-in Google smoke passes.
- CTX-410 is verified: final local curl E2E through Go Gateway covers Python gRPC health, Second Brain capture create/list/status, Homelab link validation, Homelab sync, and Homelab search. Epic 4 phase is marked done.
- CTX-411 is verified: Python gateway `/v1/chat/completions` routes chat capture and Homelab search intents into existing module services, uses the same PostgreSQL database with module-separated tables, and exposes the same deterministic router through Python gRPC `OrchestratorService.ChatCompletions`.
- BL-009 / Epic 7 is active and ready for incremental human-supervised implementation: CTX-701A prompt-contract design is done, CTX-700 through CTX-708 are verified, and CTX-709 eval/E2E proof remains.
- BL-011 / Epic 8 is planned and ready for review after go-live-critical Epic 5/Epic 7 work: CTX-801 covers async ingestion queue/worker semantics for Second Brain object webhooks, and CTX-802 covers S3 delete synchronization to remove stale documents/chunks from RAG.
- BL-006 / Epic 5 is verified: Go `system/audit` persists append-only `audit_events`, Go `system/policy` evaluates static v1 capability decisions, source-of-truth denials, Finance confirmation, webhook actor authorization, and audit-backed decisions.
- BL-011 / Epic 8 is verified: Second Brain webhook persists ingestion jobs and returns `202 Accepted`; worker processing handles upsert/delete events; delete sync removes stale `secondbrain_documents` and `secondbrain_document_chunks` from active RAG results.
- BL-012 / Phase 9 is verified: FastAPI serves a React/Tailwind client at `/ui`, app API routes validate an internal non-expiring JWT for the hard-coded single user `11111111-1111-1111-1111-111111111111`, `/v1/chat/completions` supports OpenAI-compatible SSE when `stream: true`, and the client uses one chat conversation with tabs reserved for future module UIs.
- **Python Direct Public Gateway**: Retired the thin Go gRPC HTTP proxy routes completely. Python's FastAPI app now directly serves as the Public API Gateway & Service for all REST endpoints (`/api/secondbrain/*`, `/api/homelab/*`) and `/v1/chat/completions`.
- Current sprint branch is `feat/obsidian-sync`.
- CTX-204 is done: Second Brain Obsidian S3-compatible webhook sync uses an authenticated webhook route directly in Python FastAPI, standard-library AWS Signature V4 network adapter for real S3 bucket connection, and local filesystem-backed S3 simulation for offline tests. S3-compatible storage remains a mirror/snapshot of canonical Obsidian `second-brain/`, not a writable canonical source.
- CTX-700 is verified: shared Python orchestration contracts now define transport-neutral conversation input, tool execution context, tool observations, module health, tool definitions, async `ModuleConnector`, `ConnectorRegistry`, and startup validation between tool registry targets and connector-supported targets.
- CTX-701 is verified: Python AI service migration `000004_orchestrator_conversations.sql` adds `conversations`, `conversation_messages`, and `pending_confirmations`; `ConversationManager` persists context windows, resets stale conversations after inactivity, hashes tool args, enforces pending-confirmation TTL, and binds confirmations to channel/user actors.
- CTX-704 is verified: Telegram transport adapter normalizes text updates into `ConversationInput`, enforces explicit chat/user allowlist authorization, sends typing actions, renders Markdown-lite into Telegram-safe HTML for short messages, sends long responses as plaintext chunks, retries plain text fallback, loads env settings, and exposes optional `python-telegram-bot` wiring.
- CTX-705 is verified: `SecondBrainConnector` and `HomelabConnector` map ReAct tool calls into existing Python services, return normalized `ToolObservation` data and citations, preserve capture tags, preserve capture-inbox/no-Vault-write and Homelab redaction boundaries, reject unallowlisted Homelab local paths, and pass focused/full Python AI test suites.
- CTX-706A is verified: `PolicyService` and `AuditService` are defined in protobuf, Go and Python stubs are regenerated, Go backend starts internal system gRPC services via `SYSTEM_GRPC_ADDRESS`, and Python `GrpcPolicyEnforcer`/`GrpcAuditSink` clients map decisions and audit events.
- CTX-706 is verified: `ToolAdapterExecutor` validates schemas, evaluates policy decisions, handles deny/confirmation branches, dispatches connectors, maps connector failures, and emits audit events.
- CTX-707 is verified: Finance read-only gRPC bridge and Python connector expose wallets, categories, reports, and net worth through established Go Finance services without direct Python Finance table access.
- CTX-708 is verified: presentation helpers render citations and Finance summaries, Telegram sanitizes allowed HTML tags, connector health snapshots are available, stale-index warnings are generated, and unavailable gRPC services map to controlled fallback text.
- CTX-803 is verified: S3-compatible events call `POST /api/webhooks/s3` with `X-Cortex-S3-Token`; while S3-compatible event payloads are still stabilizing, accepted events trigger full root resync for `second_brain` or `homelab` and remove stale derived RAG rows for missing Markdown files.

## Next Steps

- Next implementation step is CTX-709 eval replay and E2E chat proof.
- Remaining human-supervised items include evals and go-live readiness.

## Open Questions

- None.
