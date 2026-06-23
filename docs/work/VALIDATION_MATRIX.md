---
artifact_type: validation_matrix
id: VALIDATION_MATRIX
status: active
owner: shared
human_fields:
  - proof_override
  - acceptance_signoff
ai_fields:
  - proof_recommendation
  - evidence_links
  - status_updates
shared_fields:
  - matrix_rows
  - validation_status
updated: TBD
---

# Validation Matrix

## Field Ownership

- Human owns proof overrides and acceptance sign-off.
- AI recommends proof types, links evidence, and updates status from verification.

This file maps accepted behavior and work items to proof.

Policy lives in `docs/standards/VALIDATION.md`. This matrix is runtime project state and should change as work is planned, implemented, changed, or retired.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built or verified |
| implemented | Implemented and evidence exists |
| changed | Contract or expected proof changed after earlier implementation |
| retired | No longer part of the accepted project contract |

## Matrix

| Requirement | Phase | Ticket/Bug | Contract/Behavior | Unit | Integration | E2E | UAT | Platform/Manual | Docs Review | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | Add rows when requirements, tickets, or bugs are created | no | no | no | no | no | no | planned | none |
| Infrastructure | PHASE-0 | CTX-001 | Backend Go module and clean package structure exist under `src/backend` | yes | yes | no | not_required | no | yes | implemented | `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...` pass with approved localhost PostgreSQL access. |
| Infrastructure | PHASE-0 | CTX-002 | PostgreSQL connection and migration setup exist for backend and AI service pgvector tables | yes | yes | no | not_required | yes | yes | implemented | Backend full Go suite pass; Python AI suite pass with 33 tests OK and 1 Google smoke skipped. |
| Infrastructure | PHASE-0 | CTX-003 | Core error handling includes validation, not-found, and needs-confirmation concepts | yes | yes | no | not_required | no | yes | implemented | `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...` pass with approved localhost PostgreSQL access. |
| Infrastructure | PHASE-0 | CTX-004 | Structured JSON logging is configured for the backend | yes | yes | no | not_required | no | yes | implemented | `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...` pass with approved localhost PostgreSQL access. |
| REQ-003 | PHASE-1 | CTX-101 | Wallet CRUD, balance query, active/archived state, and archive guard for future transaction writes | yes | yes | no | not_required | no | yes | verified | `go test ./...` pass; DB-backed GORM tests pass natively. |
| REQ-005 | PHASE-1 | CTX-102 | Category CRUD with parent/child hierarchy and alias support | yes | yes | no | not_required | no | yes | verified | `go test ./...` pass; DB-backed GORM tests pass natively. |
| REQ-003 | PHASE-1 | CTX-103 | Income/expense transaction API validates wallet/category/amount and updates wallet balance | yes | yes | no | not_required | no | yes | verified | `go test ./...` pass; DB-backed GORM tests pass natively. |
| REQ-003 | PHASE-1 | CTX-104 | Transfer transaction API creates paired transfer_out/transfer_in rows with one transfer_group_id, moves funds atomically, and does not change net worth | yes | yes | no | not_required | no | yes | verified | `go test ./...` pass; DB-backed GORM tests pass natively. |
| REQ-004 | PHASE-1 | CTX-105 | Asset master API manages investment definitions, asset units, price sources, and active state | yes | yes | no | not_required | no | yes | verified | `go test ./...` pass; DB-backed GORM tests pass natively. |
| REQ-004 | PHASE-1 | CTX-106 | Asset transaction API records buy/sell/dividend behavior, cash movement, holdings, rebuildable cost basis, and price history | yes | yes | no | not_required | no | yes | verified | `go test ./...` pass; DB-backed GORM tests pass natively. |
| REQ-005 | PHASE-1 | CTX-107 | Reporting API aggregates ordinary income/expenses separately from investment cash movements by occurred_at business period using indexed query shapes | yes | yes | no | not_required | no | yes | verified | `go test ./...` pass; DB-backed GORM tests pass natively. |
| NFR-006 | PHASE-1 | CTX-101..CTX-109 | Finance tables include created/updated actor and timestamp fields; soft-delete fields are limited to correction flows and soft-deleted records are excluded from reports/rebuilds/debt settlement | yes | yes | no | not_required | no | yes | verified | Migration smoke tested through isolated-schema local PostgreSQL integration tests; `go test ./...` pass. |
| REQ-004 | PHASE-1 | CTX-108 | Net worth API calculates cash plus current market-valued assets minus v1 liabilities with deterministic price selection and gain output | yes | yes | no | not_required | no | yes | verified | `go test ./...` pass; DB-backed GORM tests pass natively. |
| REQ-010 | PHASE-1 | CTX-109 | Debt and loan tracking supports i_owe and owed_to_me, linked cash movement, remaining balance, status, and net-worth impact | yes | yes | no | not_required | no | yes | verified | `go test ./...` pass; DB-backed GORM tests pass natively. |
| Epic 1 Base permission/audit | PHASE-APP-1 | CORTEX-1 | Capability policy gates module operations and append-only audit APIs record sensitive operations safely | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 1 Base RAG/indexing | PHASE-APP-1 | CORTEX-2 | Shared RAG/indexing APIs parse, redact, chunk, retrieve, cite sources, and exclude disallowed sources | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 1 Base runtime | PHASE-APP-1 | CORTEX-6 | OpenAI-compatible chat runtime validates tool calls and delegates through pre-planned API boundaries | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 2 Finance App | PHASE-APP-1 | CORTEX-5 | Finance transaction APIs validate natural language writes, confirm ambiguity/high impact, and audit persistence | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 3 Second Brain App | PHASE-APP-1 | CORTEX-3 | Capture APIs store temporary notes without direct Vault writes or RAG access to capture buffer | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria |
| Epic 4 Homelab App | PHASE-APP-1 | CORTEX-4 | Homelab sync/index/RAG APIs are read-only, redacted, cited by repo path and commit, and deny edits/actions | yes | yes | no | yes | yes | yes | planned | Ticket acceptance criteria |
| REQ-002 | PHASE-2 | CTX-201 | Capture buffer stores chat notes as temporary markdown drafts, supports lifecycle status, and is excluded from RAG search | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/secondbrain/.venv/bin/python -m unittest discover -s src/secondbrain/tests -v` pass, including local PostgreSQL `cortex` pgvector integration. |
| REQ-002 | PHASE-2 | CTX-202 | Sync status reports indexed document and chunk counts from the Second Brain repository | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/secondbrain/.venv/bin/python -m unittest discover -s src/secondbrain/tests -v` pass; real Vault fixture indexed 91 markdown files into PostgreSQL pgvector tables. |
| REQ-002 | PHASE-2 | CTX-203 | Vault RAG query searches indexed chunks with policy filters for capture inbox, `rag:false`, private notes, archive exclusion, wiki/staging priority, query expansion, and out-of-scope rejection | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/secondbrain/.venv/bin/python -m unittest discover -s src/secondbrain/tests -v` pass; 18/18 real ground-truth retrieval cases pass and embedding column is verified as `vector(768)`. |
| REQ-009 | PHASE-2 | CTX-204 | Authenticated webhook-triggered Second Brain sync indexes MinIO mirror objects under `second-brain/` only, skips out-of-prefix or non-Markdown objects, and remains idempotent by checksum | yes | yes | yes | yes | yes | yes | implemented | `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v` pass, 30 tests OK, 1 Google smoke skipped; `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...` pass; verified E2E against real secure S3/MinIO (https://storage.dungxbuif.com) using standard-library AWS Signature V4. |
| REQ-008 | PHASE-3 | CTX-301 | Homelab RAG search queries indexed chunks using pgvector with public IP/secret redaction and source/commit SHA citations | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/secondbrain/.venv/bin/python -m unittest src/secondbrain/tests/test_homelab.py -v` pass, including Postgres pgvector integration. |
| REQ-008 | PHASE-3 | CTX-302 | Markdown relative link and fragment anchor validation tool detects broken references in repository docs | yes | yes | no | not_required | yes | yes | implemented | Verified against the real exam folder with 6 broken links reported. Test suite passes. |
| Infrastructure | PHASE-4-restructuring | CTX-403 | Python AI service baseline imports and tests run under the renamed `ai_service.*` package root without requiring Google credentials for non-smoke tests | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/ai_service/.venv/bin/python -c "from ai_service.secondbrain.service import SecondBrainService; from ai_service.homelab.service import HomelabService; print('OK')"` pass; `PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v` pass, 15 tests OK, 1 Google smoke skipped by opt-in flag. |
| Infrastructure | PHASE-4-restructuring | CTX-404 | AI provider coupling is isolated behind an `Embedder` port and provider adapters; domain services can use fake embedders without Google credentials while Google provider smoke remains valid | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v` pass, 15 tests OK; opt-in Google smoke with `.env.local` and `SECOND_BRAIN_RUN_GOOGLE_SMOKE=true` pass, 2 tests OK. |
| Infrastructure | PHASE-4-restructuring | CTX-405 | Second Brain and Homelab models/repositories are split into domain-owned modules while shared core repository code only contains SQL/psql helpers | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_repository_contracts -v` pass, 2 contract tests OK; `PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v` pass, 17 tests OK; Google smoke pass, 2 tests OK. |
| Infrastructure | PHASE-4-restructuring | CTX-406 | Domain services delegate pure Markdown chunking, redaction, checksum/signature, and link validation helpers; indexing attaches embeddings through injected `Embedder` | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_domain_helpers -v` pass, 4 pure helper tests OK; full Python suite pass, 21 tests OK; Google smoke pass, 2 tests OK. |
| Infrastructure | PHASE-4-restructuring | CTX-407 | Python gRPC server exposes Second Brain and Homelab service calls through generated stubs, maps runtime errors to gRPC status codes, and delegates to application services without SQL/provider logic in handlers | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_grpc_runtime -v` pass, 3 in-process gRPC tests OK; full Python suite pass, 24 tests OK; Google smoke pass, 2 tests OK; handler grep shows no SQL/provider calls. |
| Infrastructure | PHASE-4-restructuring | CTX-408 | Go proxy gateway is retired; Python FastAPI now serves as the direct Public API Gateway & Service for all AI/Second Brain/Homelab REST endpoints | yes | yes | no | not_required | no | yes | retired | Go handlers deleted; Go tests compile and pass without AI proxy; Python FastAPI handles all REST endpoints. |
| Infrastructure | PHASE-4-restructuring | CTX-409 | Local runtime harness starts Python AI gRPC and Python FastAPI Gateway together, and verifies Python-direct health through gateway HTTP | no | yes | yes | not_required | yes | yes | implemented | `scripts/run-ai-gateway-dev.sh` starts python gRPC and FastAPI; `scripts/check-ai-gateway.sh` pass; Python AI suite pass, 25 tests OK. |
| Infrastructure | PHASE-4-restructuring | CTX-410 | Final local E2E verifies Python FastAPI Gateway HTTP routes directly reach Python application services for health, Second Brain captures/status, Homelab link validation, Homelab sync, and Homelab search | no | yes | yes | not_required | yes | yes | implemented | Python FastAPI exposes `/api/secondbrain/*` and `/api/homelab/*` matching expected E2E shapes; FastAPIRuntimeTest passes for all legacy and public routes. |
| Infrastructure | PHASE-4-restructuring | CTX-411 | Python gateway exposes OpenAI-compatible `/v1/chat/completions` and routes chat capture/search intents into existing Second Brain and Homelab services over one shared PostgreSQL database with module-separated tables | yes | yes | no | not_required | no | yes | implemented | `PYTHONPATH=src src/ai_service/.venv/bin/python -m compileall -q src/ai_service && PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v` pass, 25 tests OK; `go test ./...` pass; Google smoke pass, 2 tests OK. |
| NFR-004 | PHASE-5 | CTX-501 | Audit logging persists append-only system events with generated IDs, timestamps, query APIs, status validation, and recursive secret-key rejection | yes | yes | no | not_required | no | yes | implemented | `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./internal/modules/system/...` pass; `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...` pass with localhost PostgreSQL access; Python AI suite pass, 33 tests OK, 1 smoke skipped. |
| NFR-004 | PHASE-5 | CTX-502 | Capability policy evaluates module/capability decisions, hard-denies source-of-truth violations, requires Finance confirmation, supports webhook actor authorization, and emits audit events | yes | yes | no | not_required | no | yes | implemented | `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./internal/modules/system/...` pass; `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...` pass with localhost PostgreSQL access; Python AI suite pass, 33 tests OK, 1 smoke skipped. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-701A | Prompt contract and orchestrator decision-flow design are reviewed before implementing the LLM/ReAct runtime | no | no | no | yes | no | yes | verified | Docs-only review complete: `docs/work/tickets/epic-7/CTX-701A.md` acceptance criteria checked; `docs/work/tickets/epic-7/DETAIL_DESIGN.md` records the approved prompt contract, state flow, Telegram-first surface, confirmation rules, citation behavior, and eval examples. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-700 | Shared Python orchestration contracts define transport-neutral conversation input, tool execution context, tool observations, module connector protocol, static tool registry, and connector startup validation | yes | no | no | not_required | no | yes | verified | `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_orchestrator_contracts -v` pass, 4 tests OK; full AI suite pass, 42 tests OK and 1 Google smoke skipped. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-701 | Conversation and confirmation state persists Telegram/API conversation history and pending confirmations with context trimming, inactivity reset, TTL expiration, argument hashing, and actor binding | yes | yes | no | not_required | no | yes | verified | `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_orchestrator_conversation -v` pass, 5 tests OK; full AI suite pass, 42 tests OK and 1 Google smoke skipped. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-702 | Tool Registry And JSON Schema Contracts | yes | no | no | not_required | no | yes | verified | `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_orchestrator_registry -v` pass, 6 tests OK. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-703 | LLM/ReAct Runtime Loop async state machine with max-turns and validation fallback | yes | no | no | not_required | no | yes | verified | `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_orchestrator_react -v` pass, 9 tests OK. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-704 | Telegram bot transport adapter normalizes text updates, enforces user/chat allowlist, emits typing actions, renders Markdown-lite to safe Telegram HTML for short messages, uses plaintext chunks for long responses, retries plain text fallback, loads env settings, and provides optional `python-telegram-bot` wiring | yes | no | no | not_required | no | yes | verified | `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest src.ai_service.tests.test_orchestrator_telegram -v` pass, 13 tests OK; full AI suite pass, 70 tests OK and 1 Google smoke skipped. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-705 | Runtime health, sync status, citation formatting, and graceful degradation close remaining chat-system completion gaps | yes | yes | no | yes | yes | yes | planned | Ticket acceptance criteria. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-706 | Replayable evals and E2E chat tests prove real orchestrator behavior across happy, ambiguous, denied, and fallback flows | yes | yes | yes | yes | yes | yes | planned | Ticket acceptance criteria. |
| REQ-009 | PHASE-8-ingestion-hardening | CTX-801 | Second Brain object webhook ingestion accepts events quickly, persists/enqueues jobs, returns `202 Accepted`, and performs S3 download/chunk/embed/index work asynchronously in a worker | yes | yes | yes | not_required | yes | yes | implemented | Focused MinIO/job tests pass, API runtime test pass, full Python AI suite pass with 33 tests OK and 1 smoke skipped, `rtk bash -n scripts/simulate-secondbrain-s3-action.sh` pass. |
| REQ-009 | PHASE-8-ingestion-hardening | CTX-802 | Second Brain delete synchronization handles `s3:ObjectRemoved:*` events and removes stale documents/chunks from active RAG results | yes | yes | yes | not_required | yes | yes | implemented | Focused MinIO delete tests pass; deleted document no longer appears in RAG search; full Python AI suite pass with 33 tests OK and 1 smoke skipped. |
| Client UI | PHASE-9-client-console | CTX-901 | FastAPI serves the React/Tailwind Cortex client at `/ui`, application APIs require internal single-user JWT, and `/v1/chat/completions` supports OpenAI-compatible SSE for the single chat conversation | yes | yes | yes | yes | yes | yes | implemented | `rtk npm run test` pass; `rtk npm run build` pass; focused FastAPI runtime test pass; full Python suite pass with 33 tests OK and 1 smoke skipped; Go suite pass; Playwright desktop/mobile screenshots captured; local SSE curl smoke returned `data:` chunks and `[DONE]`. |

## Rules

- Add or update a row when a requirement, ticket, bug, public contract, or accepted behavior is created or changed.
- Mark proof columns `yes`, `no`, or `not_required`.
- Link evidence to `docs/templates/TEST_VERIFICATION.md`, ticket verification sections, UAT, docs review, release notes, or command output summaries.
- Do not set `implemented` until required proof has evidence.
- If a proof type is `not_required`, record the reason in the linked ticket, bug, or verification artifact.
