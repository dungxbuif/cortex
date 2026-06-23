---
artifact_type: changelog
id: CHANGELOG
status: active
owner: shared
human_fields: [release_approval]
ai_fields: [change_entries, linked_releases]
shared_fields: [status]
---

# Changelog

## Field Ownership

- Human owns release approval.
- AI maintains change entries and links to release notes.

All notable changes should be recorded here.

## [Unreleased]

### Added
- Implemented Epic 7 CTX-705 Second Brain and Homelab module connectors: added `SecondBrainConnector` and `HomelabConnector`, normalized service outputs into `ToolObservation` with citations, aligned registry target names for status/search/capture/link validation, preserved capture tags, protected capture-inbox and Homelab read-only boundaries, rejected unallowlisted Homelab local paths, and added focused connector tests.
- Implemented Epic 7 CTX-704 Telegram transport adapter: added Telegram update normalization into `ConversationInput`, explicit chat/user allowlist enforcement, typing actions, Markdown-lite to Telegram-safe HTML rendering for short messages, plaintext chunking for long responses, plain-text fallback, environment settings, optional `python-telegram-bot` wiring, and focused tests.
- Completed Epic 7 CTX-701A design gate: prompt contract, orchestrator decision flow, Telegram-first surface decision, confirmation rules, citation behavior, and eval examples are reviewed in `DETAIL_DESIGN.md` before later LLM/ReAct runtime work.
- Implemented Epic 7 CTX-700 and CTX-701 foundations: added shared Python orchestration contracts, connector registry startup validation, PostgreSQL-backed conversation and pending-confirmation state, migration `000004_orchestrator_conversations.sql`, and focused tests for registry validation, context trimming, inactivity reset, confirmation hashing, TTL expiration, and Telegram actor binding.
- Implemented Phase 9 React/Tailwind Client Console: added `src/client` Vite app with a single chat conversation, future module tabs, right-side tool/citation/audit panels, OpenAI SSE client plumbing, FastAPI `/ui` hosting for built assets, internal single-user JWT bootstrap via `/api/auth/dev-token`, backend bearer-token validation mapped to user `11111111-1111-1111-1111-111111111111`, and SSE support for `/v1/chat/completions`.
- Implemented Epic 5 Audit & Permissions: added Go `system/audit` with `audit_events` migration, append/get/list APIs, required-field/status validation, recursive secret-key rejection, plus Go `system/policy` with static v1 capability decisions, hard source-of-truth denials, Finance confirmation decisions, webhook actor support for `second_brain.index_external_source`, and audit-backed decision events.
- Implemented Epic 8 Async Ingestion & Delete Sync Hardening: Second Brain webhook now returns `202 Accepted` after persisting a PostgreSQL-backed ingestion job, worker processing handles object fetch/chunk/embed/vector writes, and S3 delete events remove matching documents/chunks from active RAG results.
- Implemented CTX-204 Second Brain Obsidian MinIO webhook sync on `feat/obsidian-sync`: migrated the authenticated webhook route directly into Python FastAPI, added a standard-library AWS Signature V4 network client for real S3/MinIO connection, retained the filesystem-based simulation for local tests, and verified E2E against a real secure S3 bucket.
- Added Epic 4 AI service restructuring plan and CTX-403 baseline repair: the renamed Python service now imports and tests through `ai_service.*`, FastAPI dev tests can inject deterministic fake embeddings, and the Python test suite passes against local PostgreSQL/pgvector without requiring Google credentials outside the opt-in smoke test.
- Added CTX-404 AI provider boundary: introduced an `Embedder` port, moved Google provider code under `src/ai_service/providers/`, added `GoogleEmbedder`, added `AI_SERVICE_*` env fallback support, and updated Second Brain/Homelab services to use injected embedders instead of importing `GoogleAIClient` directly.
- Added CTX-405 domain persistence split: moved Second Brain and Homelab models/repositories into domain-owned modules, reduced `core/repository.py` to shared SQL/psql helpers, and added repository contract tests covering SQLite and local PostgreSQL/pgvector adapters.
- Added CTX-406 domain service cleanup: Second Brain and Homelab chunking now produce raw chunks before service-level embedding, Homelab redaction/link validation/chunking helpers are split into focused modules, and pure helper tests verify behavior without DB/network.
- Added CTX-407 Python gRPC server: generated Python protobuf stubs, added Second Brain and Homelab gRPC handlers, implemented the Python composition root, mapped common errors to gRPC status codes, and verified in-process gRPC calls against real application services.
- Added CTX-408 Go gateway proxy: generated Go protobuf stubs, added an internal AI service gRPC client, registered Echo proxy routes for Second Brain and Homelab, added `AI_SERVICE_ADDRESS`, and verified JSON routes against a fake gRPC server.
- Added CTX-409 local runtime harness: scripts now start Python AI gRPC plus the Go Gateway together, check `/api/ai/health`, and document local defaults for `AI_SERVICE_ADDRESS`, ports, and the dev PostgreSQL URL.
- Completed Epic 4 final E2E: local curl checks through the Go Gateway now verify Python gRPC health, Second Brain capture create/list/status, Homelab link validation, Homelab sync, and Homelab search over a real PostgreSQL/pgvector-backed runtime.
- Added CTX-411 Python gateway orchestrator path: `/v1/chat/completions` now runs in the Python AI service, routes capture and Homelab/Second Brain search intents through existing module services, keeps one shared PostgreSQL database with module-separated tables, and exposes the same deterministic router through Python gRPC `OrchestratorService.ChatCompletions`.
- Planned Epic 7 Full LLM/ReAct Orchestrator Completion after current epics and remaining tasks: added phase and CTX-701 through CTX-706 for prompt/runtime, tool registry, tool adapter execution, module connectors, sync/completion gaps, and eval/E2E proof.
- Added CTX-701A as a pre-implementation design ticket for human-reviewed prompt contracts, orchestrator decision flow, tool-selection policy, and eval examples before coding the LLM/ReAct runtime.
- Planned Epic 8 Async Ingestion & Delete Sync Hardening: added phase and CTX-801/CTX-802 to move Second Brain webhook ingestion off the API request thread, return `202 Accepted`, process jobs in a worker, and remove stale documents/chunks when S3 delete events arrive.
- Implemented Epic 3 Homelab Readonly QA module: added Git documentation recursive sync pipeline with checksum change-detection, regex-based secret/credential and public IP redaction, pgvector-based RAG search with relative path and commit SHA citations, and a relative Markdown link and hash fragment validator using GFM slugification. Exposed FastAPI endpoints for sync, search, and validation. Improved test suite portability via temporary directory-based testing.
- Added initial Python Second Brain service under `src/secondbrain`, moved Second Brain notes and local testdata out of the Go backend tree, installed/enabled pgvector in local PostgreSQL `cortex`, added environment-based configuration and SQL migrations, and implemented deterministic capture, sync status, Markdown parsing/chunking, policy-safe retrieval, FastAPI adapter tests, local PostgreSQL pgvector integration tests, Google API smoke-test hooks, and 18-case real Vault ground-truth retrieval coverage.
- Recorded architecture boundary that Python owns Orchestrator/LLM tool runtime and AI/RAG-heavy processing, Go owns API-heavy deterministic components, and Go↔Python communication should use internal gRPC with FastAPI only as a Python dev/debug adapter.
- Added Cortex app MVP planning artifacts from `docs/raw_spec/`: `PHASE-APP-1`, six draft JIRA-style `CORTEX-N` app tickets, backlog/roadmap links, and validation matrix rows. App tickets are grouped by epic: Epic 1 Base Platform, Epic 2 Finance App, Epic 3 Second Brain App, and Epic 4 Homelab App.
- Added Epic 1 Finance services detail design under `docs/work/tickets/epic-1/`, linked CTX-101 through CTX-108 to the shared design, and added planned validation rows for the Finance service tickets.
- Revised Epic 1 asset design to match the raw finance spec: added holdings, price history, valuation rules, cost-basis behavior, and asset-specific acceptance criteria.
- Reconciled master design docs for Finance asset valuation: architecture, API contracts, ERD, product spec, and requirements now describe holdings, price history, current market valuation, and weighted-average cost basis.
- Optimized Finance DB/design rules for asset valuation: deterministic price priority, rebuildable holdings, investment reporting exclusions, saving deposit classification, and v1 liability boundaries.
- Added Finance debt/loan tracking design for both directions: money I owe and money owed to me, including linked cash movement and net-worth impact.
- Added Finance query/reporting design rules: reports use business-effective dates such as `occurred_at`, tables include created/updated actor fields, and only correction-oriented tables use soft delete fields.
- Hardened Epic 1 Finance implementation design with concrete DB type rules, paired transfer rows, soft-delete recalculation behavior, report DTO shape, indexes, and initial constraints.
- Implemented initial Epic 1 Finance backend module with wallet, category, transaction, transfer, asset, report, net-worth, and debt/loan service logic, hard-coded single-user owner handling, schema migration, and focused unit tests.
- Split Finance service implementation into focused files and moved tests into dedicated `domain/tests` and `service/tests` packages; added local PostgreSQL integration tests that execute the real migration.

## [1.1.1] - 2026-06-07

### Changed
- **Debugging Standards Enhancements**: Upgraded `docs/standards/DEBUGGING.md` to include 5 major proactive bug-fixing practices for AI agents. The detailed rationale for these changes is as follows:
  - **Assess Impact (Blast Radius Analysis)**:
    - *Problem:* Fixing a local bug in a shared library or core utility can cause a chain reaction, breaking multiple other features.
    - *Solution:* Added a mandatory `Assess Impact` phase before implementing fixes, requiring agents to find references and verify that the proposed change will not break dependent features.
  - **Horizontal Fix & Proactive Search**:
    - *Problem:* Fixing a single instance of a bug (e.g., a missing null check) often leaves similar undiscovered vulnerabilities elsewhere in the codebase.
    - *Solution:* Added a `Proactive Search` phase. After fixing the local bug, agents must scan the entire codebase for the same problematic pattern and address it proactively.
  - **Telemetry First for Opaque Bugs**:
    - *Problem:* The previous standard mandated blocking a bug if it could not be reproduced locally, which could stall progress on environment-specific production issues.
    - *Solution:* If a bug lacks local reproduction steps but occurs in higher environments, the agent must create a PR/Ticket to add Telemetry/Logs/Tracing to gather data before marking it as blocked.
  - **Strict Red-Green Testing**:
    - *Problem:* Writing regression proofs after the fix or without explicit validation can lead to tests that always pass, providing a false sense of security.
    - *Solution:* Enforced strict Red-Green testing. The regression test MUST be written and fail (Red) with recorded output *before* any fix code is written, ensuring the test is actually catching the bug.
  - **Anti-Patterns Documentation (Post-mortem)**:
    - *Problem:* Valuable knowledge gained from complex architectural bugs is often lost after the fix is merged.
    - *Solution:* Required documenting root causes and gotchas as *Anti-Patterns* during the Reconcile phase so future agents avoid repeating the same mistakes.

## [1.1.0] - 2026-06-05

### Added
- **Feedback Intake Flow**: Added `PHASE 0: FEEDBACK INTAKE & TRIAGE` to the Agent Lifecycle.
- **Feedback Funnel**: Created `docs/work/FEEDBACK_LOG.md` to serve as the raw intake funnel for all user feedback before entering the backlog.
- **Feedback Template**: Created `docs/templates/FEEDBACK.md` for deep-dive analysis of complex user feedback.
- **SDD Template**: Added `docs/templates/SDD.md` (Software Design Document) to track high-level system architecture and required its synchronization upon detail design changes in `DOCS.md`.

### Changed
- **Triage Types**: Allowed triage types for user feedback in `WORKFLOW.md` now explicitly include `Enhancement`.
- **Detail Design Revamp**: Revamped `docs/templates/DETAIL_DESIGN.md` structure. It now integrates visual components (Architecture Overview, Execution Flow, API & Data Model Design, Security) while retaining strict Harness lifecycle metadata and reconciliation rules.
- **Agent Rules**: Updated `AGENTS.md` (Rule 9: Completion Rules) to strictly enforce writing framework and user-facing changes to `CHANGELOG.md`.
- **Docs Guide**: Updated `docs/README.md` to include the new templates and feedback intake funnel.

## [1.0.0] - 2026-06-05

### Added
- Initial SDLC agent framework scaffold.
