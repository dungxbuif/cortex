# Implementation Plan: Epic 4 AI Service Restructuring & gRPC Gateway

## Scope Decision

Epic 4 được chia thành nhiều ticket nhỏ để implementation dễ test và rollback được theo từng lát cắt. Epic này được xem là **infrastructure-completion epic** cho Cortex runtime: hoàn thiện package boundary, provider boundary, gRPC boundary, config, local runtime, test harness, và module migration rules để các epic sau không phải sửa nền liên tục.

Quyết định scope:

- Có thể sửa module cũ nếu cần để chúng tuân thủ boundary mới, chạy được qua hạ tầng mới, hoặc test được qua contract mới.
- Không thêm business feature mới vào Finance/Second Brain/Homelab nếu feature đó không trực tiếp phục vụ hạ tầng Epic 4.
- Finance REST routes: chỉ đưa vào Epic 4 nếu cần chứng minh Go gateway/module-registration hạ tầng. Nếu làm, chỉ expose minimal read/write smoke route hoặc health/registration route, không mở rộng full product API.
- FastAPI: giữ lại làm dev/debug adapter, không phải public contract chính.
- Env prefix: thêm `AI_SERVICE_*` là prefix mới, fallback `SECOND_BRAIN_*` để backward compatible.
- Orchestrator: chỉ giữ gRPC health/stub nếu cần contract compile; full chat loop thuộc Epic 5.

## Infrastructure Completion Recommendations

Kiến nghị cho Epic 4:

1. Treat Epic 4 as the stable runtime foundation before building Orchestrator.
2. Allow old module edits, but every edit must map to one of these reasons: package boundary, dependency injection, contract generation, config unification, testability, local runtime, or gateway registration.
3. Do not let Finance become the center of this epic. Finance may be touched only to validate Go module registration patterns.
4. Put provider clients under `providers/`, not `core/`.
5. Put contracts under `src/proto/` and generated code under explicit generated folders.
6. Add one local run path that a human can execute without guessing: DB -> Python AI service -> Go gateway -> curl.
7. Add fake adapters for every external boundary: fake embedder, fake repo, fake gRPC server/client.
8. Record every cross-runtime contract in docs before implementation starts.
9. Keep generated files reproducible with documented commands.
10. End the epic only when a full vertical path is proven, not when individual packages compile.

## Dependency Map

```text
CTX-403 baseline/import repair
  -> CTX-404 ports/providers split
  -> CTX-405 domain models/repositories split
  -> CTX-406 domain service cleanup
  -> CTX-407 Python gRPC server
  -> CTX-408 Go gRPC gateway
  -> CTX-409 runtime harness, generated-code workflow, and local dev commands
  -> CTX-410 E2E verification and docs reconciliation
```

## Integration Spine

Mọi ticket trong Epic 4 phải nối vào cùng một đường xương sống runtime, không được tạo file hoặc abstraction rời rạc mà chưa có caller/callee rõ ràng.

```text
Go Echo route
  -> Go AIServiceClient
  -> generated gRPC client
  -> Python grpc_server.py
  -> grpc/handlers.py
  -> SecondBrainService / HomelabService
  -> Repository port + Embedder port
  -> Postgres repository + Google/local/fake embedder
  -> PostgreSQL + pgvector / provider API
```

Quy tắc liền mạch:

- Mỗi ticket phải giữ hoặc khôi phục được một vertical smoke path nhỏ.
- Mỗi abstraction mới phải có ít nhất một production caller và một test fake/mock caller.
- Mỗi file mới phải nằm trong một dependency direction đã định, không tạo import vòng.
- Mỗi ticket phải cập nhật contract nếu contract thay đổi: proto, port protocol, repository method, HTTP route, hoặc config.
- Không được merge một ticket chỉ vì unit test của file mới pass nếu nó chưa nối vào use case hiện có.

## Cross-Ticket Contract Ledger

Các contract này là dây nối giữa các ticket. Khi một ticket thay đổi contract, ticket đó phải cập nhật ledger này và các ticket sau phải dùng đúng contract mới.

| Contract | Owner Ticket | Consumers | Stability Rule |
| --- | --- | --- | --- |
| Python package import root `ai_service.*` | CTX-403 | All Python tickets | Must stay green before any refactor |
| `Embedder` protocol | CTX-404 | CTX-406, CTX-407 tests | Additive changes only unless all consumers updated same ticket |
| `SecondBrainRepository` protocol | CTX-405 | CTX-406, CTX-407 | Methods must match service use cases, not table internals |
| `HomelabRepository` protocol | CTX-405 | CTX-406, CTX-407 | Methods must match service use cases, not table internals |
| `src/proto/cortex.proto` | CTX-407 | CTX-408, CTX-409 | Proto changes require regenerated Python and Go stubs together |
| `AI_SERVICE_ADDRESS` config | CTX-408 | Go gateway, E2E | Default must work for local dev |
| HTTP route shape | CTX-408 | CTX-409, future Open WebUI integration | Must be documented in API docs during reconciliation |
| Local runtime commands | CTX-409 | CTX-410, future contributors | Must start DB/Python/Go consistently |
| Generated-code commands | CTX-409 | CTX-407, CTX-408 maintenance | Must regenerate Python and Go stubs without manual edits |

## Continuity Gates

Each ticket must pass its own tests plus the continuity gate from previous tickets:

| After Ticket | Required continuity check |
| --- | --- |
| CTX-403 | Python import root and existing tests discover correctly |
| CTX-404 | Services can run with fake embedder and no network |
| CTX-405 | Services can run against split repositories with the same test expectations as before |
| CTX-406 | Index/search use cases run through service layer using fake repo/embedder and Postgres repo |
| CTX-407 | Python gRPC handler calls real services, not placeholder logic |
| CTX-408 | Go HTTP handler reaches fake or real gRPC service and maps response/error correctly |
| CTX-409 | Local runtime commands and generated-code workflow are reproducible |
| CTX-410 | Full local path works with real DB/pgvector and documented commands |

If a continuity gate fails, stop the next ticket and fix the broken connection first. Do not continue by adding more layers on top of a red baseline.

## Ticket Breakdown

### CTX-403: Baseline Repair and Trace Alignment

Goal: đưa repo về trạng thái import/test baseline sạch sau rename `src/secondbrain` -> `src/ai_service`.

Scope:

- Fix `src/ai_service/__init__.py` import path.
- Update all tests from `secondbrain.*` to `ai_service.*`.
- Fix `CTX-403.md` detail design links from `epic-3` to `epic-4`.
- Decide whether `src/ai_service/tests/testdata/mock_vault/` is committed fixture or ignored external data.

Acceptance:

- `PYTHONPATH=src src/ai_service/.venv/bin/python -c "from ai_service.secondbrain.service import SecondBrainService; from ai_service.homelab.service import HomelabService; print('OK')"` passes.
- `PYTHONPATH=src src/ai_service/.venv/bin/python -m unittest discover -s src/ai_service/tests -v` no longer fails on import path errors.
- Ticket trace links point to Epic 4 design.
- Continuity gate: current Python package root is stable for all later tickets.

Out of scope:

- No provider abstraction.
- No repository split.
- No gRPC implementation.

### CTX-404: AI Ports and Provider Adapters

Goal: tách provider AI khỏi domain/application services.

Scope:

- Add `ai_service/core/ports.py` with `Embedder` protocol.
- Move provider code from `core/google_ai.py` to `providers/google_ai.py`.
- Add `providers/embedding.py` with `GoogleEmbedder`.
- Add test fake embedder utilities for deterministic unit tests.
- Rename settings class to `AIServiceSettings`.
- Add `AI_SERVICE_*` env variables with fallback to `SECOND_BRAIN_*`.

Acceptance:

- No `secondbrain/` or `homelab/` file imports `GoogleAIClient`.
- Unit tests can instantiate services with fake embedder without network access.
- Google smoke tests still pass when opt-in env is enabled.
- Continuity gate: existing service methods still work through the same public service API.

Out of scope:

- Repository split.
- gRPC server.

### CTX-405: Domain Models and Repository Split

Goal: remove `core/repository.py` god class by splitting persistence per domain.

Scope:

- Move Second Brain dataclasses into `secondbrain/models.py`.
- Move Homelab dataclasses into `homelab/models.py`.
- Keep shared status/enums/time helpers in `core/models.py`.
- Add `SecondBrainRepository` and `HomelabRepository` protocols in `core/ports.py`.
- Create `secondbrain/repository.py` for Second Brain query methods.
- Create `homelab/repository.py` for Homelab query methods.
- Keep only shared SQL helpers/base psql runner in `core/repository.py`.

Acceptance:

- Existing Second Brain tests pass against Postgres.
- Existing Homelab tests pass against Postgres.
- `core/repository.py` has no domain-specific method names like `homelab`, `capture`, `vault`, `sync_status`.
- Repository contract tests prove fake/in-memory and Postgres adapters expose the same behavior for service needs.
- Continuity gate: CTX-404 fake embedder service tests run unchanged except import paths.

Out of scope:

- Transport changes.
- Go gateway.

### CTX-406: Domain Service Cleanup

Goal: make Second Brain and Homelab services small, testable, and dependency-injected.

Scope:

- `secondbrain/markdown.py` returns `RawChunk` without embedding.
- `secondbrain/service.py` accepts repository + embedder via constructor.
- Extract Homelab redaction into `homelab/redaction.py`.
- Extract Homelab markdown link validation into `homelab/link_validator.py`.
- `homelab/service.py` accepts repository + embedder via constructor.
- Remove default construction of real Google client inside domain services.

Acceptance:

- Pure unit tests cover markdown chunking, redaction, checksum, signature verification, and link validation with no DB/network.
- Application service tests use fake repo and fake embedder.
- Real Postgres integration tests still pass.
- Search/index code embeds in batch where practical.
- Continuity gate: the same service use cases are callable by both FastAPI dev adapter and upcoming gRPC handlers.

Out of scope:

- gRPC.
- Go.

### CTX-407: Python gRPC Server

Goal: expose AI service functions through internal gRPC.

Scope:

- Generate Python protobuf stubs under `ai_service/grpc/`.
- Implement `grpc/handlers.py` for Second Brain and Homelab services.
- Implement `grpc_server.py` as composition root.
- Add gRPC error mapping for invalid input, not found, provider failure, and internal failure.
- Add request/response serialization tests.

Acceptance:

- In-process Python gRPC tests call `CreateCapture`, `ListCaptures`, `SearchSecondBrain`, `SyncHomelab`, `SearchHomelab`, and `ValidateLinks`.
- Startup smoke verifies settings -> provider -> repos -> services -> server wiring.
- gRPC handlers contain no SQL and no provider-specific API calls.
- Continuity gate: gRPC calls reach real application services and do not duplicate business logic.

Out of scope:

- Go HTTP proxy.
- Full Orchestrator chat loop.

### CTX-408: Go gRPC Gateway

Goal: Go backend can proxy AI service REST routes to Python gRPC.

Scope:

- Generate Go protobuf stubs under `src/backend/internal/infrastructure/grpc/pb/`.
- Add `internal/infrastructure/grpc/client.go`.
- Add config `AI_SERVICE_ADDRESS` with default `localhost:50051`.
- Register AI service HTTP routes in Echo gateway.
- Use fake gRPC server in Go tests.

Acceptance:

- `go test ./...` passes in `src/backend`.
- Go client maps gRPC failures to stable HTTP errors.
- HTTP routes for Second Brain and Homelab proxy to fake gRPC server in tests.
- Continuity gate: route names, proto messages, and Python handler methods are aligned by tests.

Out of scope:

- Finance REST routes.
- Permission/audit guard implementation.

### CTX-409: Runtime Harness and Generated-Code Workflow

Goal: make the local infrastructure reproducible so future tickets do not depend on hidden shell knowledge.

Scope:

- Document or add commands for generating Python and Go protobuf stubs.
- Add local run commands for Python gRPC service and Go gateway.
- Add a minimal health/smoke path for each runtime.
- Add config defaults for local dev: DB, AI service address, owner id, migration path.
- Add dependency notes for `grpcio`, `grpcio-tools`, Go protobuf plugins, and pgvector.
- Optional: add lightweight scripts/task targets if the repo already uses a task runner; otherwise document exact commands.
- If Finance module registration is required to validate Go gateway structure, add only minimal route registration smoke, not full Finance feature routing.

Acceptance:

- A new agent can run documented commands from a clean checkout plus local DB.
- Proto generation command is documented and produces the expected Python/Go files.
- Runtime smoke commands prove DB, Python gRPC service, and Go gateway can start independently.
- No generated file is edited manually after generation.

Out of scope:

- Full deployment automation.
- Production process supervisor.
- Full Finance REST API.

### CTX-410: Real E2E, Validation Matrix, and Docs Reconciliation

Goal: prove the integrated runtime works with real DB/pgvector and reconcile docs.

Scope:

- Run Python unit/integration tests.
- Run Google smoke tests when credentials are available.
- Run Go tests.
- Run manual or automated E2E: Go HTTP -> Python gRPC -> PostgreSQL/pgvector.
- Update `docs/work/VALIDATION_MATRIX.md`.
- Update `docs/CONTEXT.md`, backlog, changelog, architecture/API docs, and ADR links.

Acceptance:

- Exact command evidence recorded for Python, Go, DB, gRPC, and E2E checks.
- UAT result recorded for gateway routes.
- Master docs match actual runtime boundaries.
- Epic status can move to `verified` only after evidence is complete.
- Continuity gate: at least one full path command proves Go HTTP -> Python gRPC -> service -> DB/provider boundary.

Out of scope:

- New product features.
- Orchestrator reasoning loop.

## Recommended Implementation Order

1. Finish CTX-403 first. Do not proceed while import baseline is red.
2. Implement CTX-404 and CTX-406 before CTX-405 only if repository split is too risky; otherwise CTX-405 before service cleanup is cleaner.
3. Keep every ticket green before moving to the next.
4. Do not start Go gateway until Python gRPC server has in-process tests passing.
5. Do not start final E2E until runtime/generation commands are documented and reproducible.
6. Do not mark Epic 4 done until CTX-410 records real command evidence.

## Old Module Modification Policy

Old modules may be modified during Epic 4 under these rules:

| Allowed change | Example | Required proof |
| --- | --- | --- |
| Boundary cleanup | Remove provider import from domain service | Unit test with fake adapter |
| Dependency injection | Constructor accepts repo/embedder/client interface | Existing service tests still pass |
| Repository contract alignment | Split shared repo into domain repos | Postgres integration tests |
| Go gateway registration pattern | Add minimal module route registration | `go test ./...` and HTTP smoke |
| Config unification | Add `AI_SERVICE_*` fallback logic | Config unit test |
| Generated contract alignment | Update proto and regenerated stubs | Python + Go compile/tests |

Not allowed in this epic without a new ticket/design:

- New Finance business workflows.
- New Orchestrator reasoning behavior.
- New permission/audit policy database model.
- New external provider integrations beyond the existing Google AI path.
- Vault write behavior or Homelab repo write behavior.

## Per-Ticket Handoff Template

At the end of every ticket, update the next ticket with this short handoff:

```text
Contract changed:
- <proto/port/repo/config/route changed or "none">

Current working path:
- <smallest command proving the ticket is connected to the spine>

Next ticket must use:
- <exact class/function/proto/config name>

Known constraints:
- <what must not be broken>
```

This handoff prevents the next task from reinterpreting the architecture and drifting away from the integrated flow.

## Test Strategy by Layer

| Layer | Test Type | Example proof |
| --- | --- | --- |
| Pure domain functions | Unit | markdown chunking, redaction, link validation |
| Application services | Unit with fake ports | fake repo + fake embedder |
| Repository adapters | Integration | Postgres/pgvector schema + CRUD/search |
| Provider adapters | Opt-in smoke | Google embedding/generation with `.env.local` sourced but not printed |
| gRPC handlers | Integration | in-process Python gRPC server/client |
| Go gateway | Integration | Go HTTP handlers + fake gRPC server |
| Full path | E2E/manual | curl Go route -> Python gRPC -> DB |

## Design Guardrails

- Domain modules must not import provider clients.
- Domain modules must not read env directly.
- Transport handlers must not contain SQL or provider calls.
- Repositories must not parse markdown or call embedder.
- Provider adapters must not know Second Brain/Homelab business terms beyond generic text embedding/generation inputs.
- Generated protobuf files must be committed or regenerated reproducibly by a documented command.
