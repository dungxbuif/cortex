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
| REQ-009 | PHASE-2 | CTX-204 | Authenticated webhook-triggered Second Brain sync indexes MinIO mirror objects under `second-brain/` only, skips out-of-prefix or non-Markdown objects, and remains idempotent by checksum | yes | yes | yes | yes | yes | yes | implemented | `rtk env PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v` pass, 30 tests OK, 1 Google smoke skipped; `rtk env GOCACHE=/private/tmp/cortex-go-cache go test ./...` pass; `rtk bash -n scripts/simulate-secondbrain-s3-action.sh` pass. |
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
| REQ-006 | PHASE-7-orchestrator-completion | CTX-701 | LLM/ReAct runtime and prompt contracts drive `/v1/chat/completions` without moving prompts or chat state into domain modules | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-702 | Tool registry defines provider-neutral JSON schemas, capability metadata, confirmation policy, and output contracts | yes | no | no | not_required | no | yes | planned | Ticket acceptance criteria. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-703 | Tool adapter validates, authorizes, maps, executes, and normalizes tool calls through existing services | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-704 | Finance, Second Brain, and Homelab connectors call existing module APIs/services and preserve module source-of-truth rules | yes | yes | no | yes | no | yes | planned | Ticket acceptance criteria. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-705 | Runtime health, sync status, citation formatting, and graceful degradation close remaining chat-system completion gaps | yes | yes | no | yes | yes | yes | planned | Ticket acceptance criteria. |
| REQ-006 | PHASE-7-orchestrator-completion | CTX-706 | Replayable evals and E2E chat tests prove real orchestrator behavior across happy, ambiguous, denied, and fallback flows | yes | yes | yes | yes | yes | yes | planned | Ticket acceptance criteria. |

## Rules

- Add or update a row when a requirement, ticket, bug, public contract, or accepted behavior is created or changed.
- Mark proof columns `yes`, `no`, or `not_required`.
- Link evidence to `docs/templates/TEST_VERIFICATION.md`, ticket verification sections, UAT, docs review, release notes, or command output summaries.
- Do not set `implemented` until required proof has evidence.
- If a proof type is `not_required`, record the reason in the linked ticket, bug, or verification artifact.
