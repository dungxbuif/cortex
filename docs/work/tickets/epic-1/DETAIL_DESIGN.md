---
artifact_type: detail_design
id: DESIGN-EPIC-1-FINANCE-SERVICES
status: ready
owner: ai
approval: pending
human_fields:
  - approval
  - constraints
  - scope_decisions
ai_fields:
  - problem
  - context_loaded
  - brownfield_scope
  - proposed_approach
  - design_tradeoffs
  - architecture_overview
  - execution_flow
  - api_data_model
  - security
  - test_plan
  - reconciliation_plan
shared_fields:
  - status
  - trace
  - small_task_exemption
trace:
  backlog_item: BL-003
  requirement:
    - REQ-003
    - REQ-004
    - REQ-005
  phase: ../../phases/PHASE-1-finance.md
  ticket_or_bug:
    - CTX-101
    - CTX-102
    - CTX-103
    - CTX-104
    - CTX-105
    - CTX-106
    - CTX-107
    - CTX-108
    - CTX-109
  test_verification: TBD
  validation_matrix: ../../VALIDATION_MATRIX.md
  docs_review: TBD
  adrs: []
  master_docs_touched:
    - ../../../requirements/REQUIREMENTS.md
    - ../../../architecture/API.md
    - ../../../architecture/ERD.md
    - ../../../architecture/ARCHITECTURE.md
---

# DETAIL DESIGN: Epic 1 Finance Services

## Status

- ID: DESIGN-EPIC-1-FINANCE-SERVICES
- Status: ready
- Ticket/Bug: CTX-101 through CTX-109
- Approval: pending
- Author: AI
- Updated: 2026-06-17

## Trace Links

- Backlog item: [BL-003](../../BACKLOG.md)
- Phase: [PHASE-1-finance.md](../../phases/PHASE-1-finance.md)
- Tickets: [CTX-101](CTX-101.md), [CTX-102](CTX-102.md), [CTX-103](CTX-103.md), [CTX-104](CTX-104.md), [CTX-105](CTX-105.md), [CTX-106](CTX-106.md), [CTX-107](CTX-107.md), [CTX-108](CTX-108.md), [CTX-109](CTX-109.md)
- Requirements: `REQ-003`, `REQ-004`, `REQ-005`
- Validation matrix: [VALIDATION_MATRIX.md](../../VALIDATION_MATRIX.md)

---

## 1. Context & Scope

### Problem Statement

Epic 1 needs deterministic Finance domain services before the orchestrator can safely expose finance tools to chat. The services must own finance business rules, persistence coordination, validation, and report calculations while staying free of LLM prompts, OpenAI schemas, chat history, and presentation logic.

Why now: `CTX-101` is active and wallet behavior is the base dependency for categories, transactions, transfers, assets, reports, and net worth.

Success outcome: a clear implementation contract for Finance services that downstream code work can follow without redefining module boundaries or data rules per ticket.

### Context Loaded

- `docs/CONTEXT.md`
- `docs/work/BACKLOG.md`
- `docs/work/phases/PHASE-1-finance.md`
- `docs/work/tickets/epic-1/CTX-101.md` through `CTX-109.md`
- `docs/raw_spec/modules/finance.md`
- `docs/requirements/REQUIREMENTS.md`
- `docs/architecture/API.md`
- `docs/architecture/ERD.md`
- `docs/architecture/ARCHITECTURE.md`
- Existing backend scaffold under `src/backend/internal/`

### Brownfield Scope

- Touched modules/files planned:
  - `src/backend/internal/modules/finance/domain`
  - `src/backend/internal/modules/finance/service`
  - `src/backend/internal/modules/finance/repository`
  - `src/backend/internal/modules/finance/delivery`
  - `src/backend/migrations`
- Direct dependencies inspected:
  - `src/backend/internal/infrastructure/db/postgres.go`
  - `src/backend/internal/core/errors/errors.go`
  - `src/backend/internal/core/validator/validator.go`
  - `src/backend/internal/config/config.go`
- Contracts affected:
  - Finance Domain API contracts in `docs/architecture/API.md`
  - Finance ERD in `docs/architecture/ERD.md`
  - Finance requirements `REQ-003`, `REQ-004`, `REQ-005`
- Known unknowns:
  - Exact migration tool has not been selected.
  - Auth/user ownership is not yet implemented; services should reserve `owner_id` or `user_id` where needed but avoid inventing auth flows.
  - Audit/permission services are in later epics; Epic 1 should expose service seams for them without implementing policy logic.
- Scope expansion reason: service design spans all Epic 1 tickets because wallet/category/transaction/reporting behavior is tightly coupled by balance and net-worth invariants.

### Small Task Exemption

- Small task exemption: no
- Reason: Finance service work touches data model, domain APIs, persistence, and user-visible financial calculations.
- Impact checked: API=yes, DB=yes, Security=yes, Runtime=no, Standards=no

---

## 2. Design Considerations & Trade-offs

| Consideration / Alternative | Pros | Cons | Decision |
| --- | --- | --- | --- |
| Service layer per aggregate (`WalletService`, `CategoryService`, etc.) | Clear ticket ownership and focused tests | Cross-service operations need coordination | Chosen |
| One large `FinanceService` | Simple first file structure | Becomes a rule dumping ground and blocks parallel work | Rejected |
| Direct GORM calls from delivery/tool adapter | Fast initially | Business rules leak outside Finance module | Rejected |
| Repository interfaces inside finance module | Enables service tests with fakes and isolates GORM | Slightly more boilerplate | Chosen |
| Store wallet balance as mutable field | Fast reads and simple reporting | Requires atomic updates and transaction safety | Chosen with invariant tests |
| Compute wallet balance only from transactions | Stronger source-of-truth purity | More expensive and awkward for initial balance/adjustment flows | Rejected for MVP |

---

## 3. Architecture Overview

### Finance Service Boundary

```text
+-----------------------------+
| Orchestrator / Tool Adapter |
| (future integration layer)   |
+--------------+--------------+
               |
               v
+-----------------------------+
| Finance Delivery API        |
| command/query DTO mapping   |
+--------------+--------------+
               |
               v
+-----------------------------+
| Finance Services            |
| business rules + use cases  |
| Wallet / Category / Tx      |
| Asset / Report / NetWorth   |
+--------------+--------------+
               |
               v
+-----------------------------+
| Finance Repositories        |
| persistence queries only    |
+--------------+--------------+
               |
               v
+-----------------------------+
| PostgreSQL                  |
| canonical finance store     |
+-----------------------------+

Shared dependencies:
  Finance Delivery + Services -> core/validator, core/errors
  Finance Services            -> future audit/policy integration seam

Boundary rule:
  LLM prompts, OpenAI schemas, chat history, and response synthesis stay
  outside Finance. Finance owns deterministic money/domain behavior only.
```

### Component Responsibilities

| Component | Role |
| --- | --- |
| Finance domain models | Define wallet, category, transaction, asset, report, and net-worth entities and invariants. |
| Finance services | Implement use cases and business rules. They are the only layer allowed to coordinate finance repositories. |
| Finance repositories | Persist and query finance entities through PostgreSQL/GORM. No business decisions. |
| Finance delivery/tool adapter | Converts orchestrator/internal calls into service commands. No balance math or validation beyond transport parsing. |
| Core validator | Validates request DTO shape before service rules run. |
| Core errors | Returns structured `ValidationError`, `NotFound`, `Conflict`, and future `NeedsConfirmation` errors. |
| PostgreSQL | Canonical Finance source of truth. |

### Target Package Shape

```text
src/backend/internal/modules/finance/
  domain/
    wallet.go
    category.go
    transaction.go
    asset.go
    report.go
  service/
    wallet_service.go
    category_service.go
    transaction_service.go
    asset_service.go
    report_service.go
    net_worth_service.go
    debt_service.go
  repository/
    interfaces.go
    gorm_wallet_repository.go
    gorm_category_repository.go
    gorm_transaction_repository.go
    gorm_asset_repository.go
  delivery/
    finance_api.go
```

---

## 4. Execution Flow

### Wallet Create/Update/Archive

1. Delivery receives `CreateWalletCommand`, `UpdateWalletCommand`, or `ArchiveWalletCommand`.
2. Core validator checks required fields and enum values.
3. `WalletService` enforces finance rules:
   - wallet name must be unique among active wallets for the owner
   - wallet type must be one of `basic`, `goal`, `credit`, `linked`
   - currency defaults to `VND`
   - archived wallet cannot be used for new transactions
4. Repository persists changes.
5. Service returns structured wallet DTO.

### Income/Expense Transaction

1. Delivery receives `CreateTransactionCommand`.
2. Validator checks amount, currency, wallet id, category id, type, occurred time.
3. `TransactionService` loads wallet/category and rejects archived or missing records.
4. Service updates wallet balance:
   - income increases wallet balance
   - expense decreases wallet balance
5. Service saves transaction and wallet update in one DB transaction.
6. Service returns transaction DTO plus updated wallet balance.

### Transfer Transaction

1. Delivery receives `CreateTransferCommand`.
2. `TransactionService` validates source and destination wallets.
3. Service rejects same-wallet transfer and archived wallets.
4. Service creates exactly two transaction rows with one shared `transfer_group_id`:
   - source wallet row with `type = transfer_out`
   - destination wallet row with `type = transfer_in`
5. Service debits source and credits destination atomically.
6. Net worth must not change because transfer only moves value between wallets.

### Asset Transaction

1. `AssetService` validates asset and funding wallet.
2. Buy/sell/transfer/dividend/split operations create asset transaction records.
3. Buy/sell/dividend operations create or link a cash transaction when the operation affects a wallet.
4. `AssetService` updates current holding quantity, remaining cost basis, and realized gain/loss.
5. Current asset value is calculated from the latest accepted market price, not from purchase price.
6. Net-worth calculation uses holdings plus latest price history.

### Reporting And Net Worth

1. `ReportService` queries transactions by date range, wallet, category, and exclusion flag.
2. `ReportService` excludes investment cash movements from living-expense and ordinary-income totals unless the query explicitly asks for investment activity.
3. `NetWorthService` combines wallet balances, current asset values, and active debt/loan positions.
3. Services return structured results suitable for Markdown rendering later.

### Debt And Loan Tracking

1. `DebtService` receives `CreateDebtOrLoanCommand`.
2. Direction determines business meaning:
   - `i_owe`: liability; subtract remaining balance from net worth.
   - `owed_to_me`: receivable asset; add remaining balance to net worth.
3. `DebtService` records counterparty, principal amount, remaining amount, due date, note, and status.
4. `RecordDebtPayment` validates the debt exists and active remaining balance is sufficient.
5. Payment against `i_owe` links to a cash transaction that decreases wallet balance.
6. Collection against `owed_to_me` links to a cash transaction that increases wallet balance.
7. Settlement updates remaining balance and status atomically with linked cash movement.

---

## 5. API & Data Model Design

### Finance Domain API Surface

These are internal Go APIs, not public REST endpoints.

```go
type WalletService interface {
    CreateWallet(ctx context.Context, cmd CreateWalletCommand) (*WalletDTO, error)
    UpdateWallet(ctx context.Context, cmd UpdateWalletCommand) (*WalletDTO, error)
    GetWallet(ctx context.Context, id string) (*WalletDTO, error)
    ListWallets(ctx context.Context, query ListWalletsQuery) ([]WalletDTO, error)
    ArchiveWallet(ctx context.Context, id string) error
}

type TransactionService interface {
    CreateIncomeExpense(ctx context.Context, cmd CreateTransactionCommand) (*TransactionDTO, error)
    CreateTransfer(ctx context.Context, cmd CreateTransferCommand) (*TransferDTO, error)
}

type AssetService interface {
    CreateAsset(ctx context.Context, cmd CreateAssetCommand) (*AssetDTO, error)
    RecordAssetTransaction(ctx context.Context, cmd RecordAssetTransactionCommand) (*AssetTransactionDTO, error)
    UpdateAssetPrice(ctx context.Context, cmd UpdateAssetPriceCommand) (*AssetPriceDTO, error)
    GetAssetHolding(ctx context.Context, query AssetHoldingQuery) (*AssetHoldingDTO, error)
    ListAssetHoldings(ctx context.Context, query ListAssetHoldingsQuery) ([]AssetHoldingDTO, error)
}

type ReportService interface {
    GetFinancialReport(ctx context.Context, query ReportQuery) (*FinancialReportDTO, error)
    GetNetWorth(ctx context.Context, query NetWorthQuery) (*NetWorthDTO, error)
}

type DebtService interface {
    CreateDebtOrLoan(ctx context.Context, cmd CreateDebtOrLoanCommand) (*DebtLoanDTO, error)
    UpdateDebtOrLoan(ctx context.Context, cmd UpdateDebtOrLoanCommand) (*DebtLoanDTO, error)
    RecordDebtPayment(ctx context.Context, cmd RecordDebtPaymentCommand) (*DebtPaymentDTO, error)
    GetDebtStatus(ctx context.Context, query DebtStatusQuery) (*DebtStatusDTO, error)
    ListDebts(ctx context.Context, query ListDebtsQuery) ([]DebtLoanDTO, error)
}
```

### Data Model Changes

### Finance ERD

```text
+------------------+            +------------------+
| wallets          |            | categories       |
|------------------|            |------------------|
| id PK            |<----+      | id PK            |
| owner_id         |     |      | owner_id         |
| name             |     |      | parent_id FK ----+---+
| type             |     |      | name             |   |
| currency         |     |      | type             |   |
| initial_bal_minor|     |      | aliases          |   |
| current_bal_minor|     |      | status           |   |
| include_in_total |     |      +------------------+   |
| status           |     |                             |
| archived_at      |     |                             |
| created/updated  |     |                             |
+--------+---------+     |                             |
         |               |                             |
         | 1             | many                        |
         v               |                             |
+------------------+     |                             |
| transactions     |     |                             |
|------------------|     |                             |
| id PK            |     |                             |
| owner_id         |     |                             |
| wallet_id FK ----+-----+                             |
| category_id FK --+-----------------------------------+
| type             |
| direction        |
| amount_minor     |
| currency         |
| occurred_at      |
| note             |
| exclude_report   |
| transfer_group_id|
| deleted_at       |
| created/updated  |
+------------------+

+------------------+            +----------------------+
| assets           |            | asset_transactions   |
|------------------|            |----------------------|
| id PK            |<----+      | id PK                |
| owner_id         |     |      | owner_id             |
| asset_type       |     +------| asset_id FK          |
| symbol           |            | wallet_id FK --------+----> wallets.id
| name             |            | transaction_type     |
| currency         |            | quantity             |
| unit             |            | unit_price_minor     |
| price_source     |            | gross_amount_minor   |
| is_active        |            | fee_minor            |
+--------+---------+            | tax_minor            |
         |                      | net_amount_minor     |
         |                      | linked_cash_tx_id --> transactions.id
         |                      | occurred_at          |
         |                      | deleted_at           |
         |                      | created/updated      |
         |                      +----------------------+
         |
         | 1
         |
         |      +----------------------+       +----------------------+
         +----->| asset_holdings       |       | asset_prices         |
         |      |----------------------|       |----------------------|
         |      | id PK                |       | id PK                |
         |      | owner_id             |       | owner_id             |
         |      | asset_id FK          |<------| asset_id FK          |
|      | quantity             |       | price_minor          |
|      | avg_cost_minor       |       | buy_price_minor      |
|      | total_cost_minor     |       | sell_price_minor     |
|      | realized_gain_minor  |       | currency             |
|      | current_price_minor  |       | price_type           |
|      | current_value_minor  |       | source               |
         |      | unreal_gain_minor    |       | priced_at            |
|      | last_priced_at       |       | created/updated      |
|      | created/updated      |       +----------------------+
         |      +----------------------+
         |
         |      +----------------------+
         +----->| portfolio_valuation  |
                | computed, not source |
                |----------------------|
                | cash_value           |
                | asset_value          |
                | liability_value      |
                | receivable_value     |
                | net_worth            |
                | realized_gain_period |
                | unrealized_gain      |
                +----------------------+

+------------------+            +----------------------+
| debt_loans       |            | debt_payments        |
|------------------|            |----------------------|
| id PK            |<----+      | id PK                |
| owner_id         |     |      | owner_id             |
| direction        |     +------| debt_loan_id FK      |
| counterparty     |            | wallet_id FK --------+----> wallets.id
| principal_minor  |            | cash_transaction_id -+----> transactions.id
| remaining_minor  |            | amount_minor         |
| currency         |            | paid_at              |
| due_date         |            | note                 |
| status           |            +----------------------+
| note             |
| created/updated  |
+------------------+

Key invariants:
  - wallet.current_balance_minor is mutated only by Finance services.
  - income increases wallet balance; expense decreases wallet balance.
  - transfer debits one wallet and credits another atomically.
  - transfer must not change net worth.
  - asset buy/sell may move cash, but investment value belongs to net worth,
    not living expense reporting.
  - asset_transactions keep historical execution price and fees/taxes.
  - asset_prices keep market price history and are never overwritten.
  - asset_holdings are derived/current position state maintained by services.
  - net worth uses latest acceptable market price, not original buy price.
  - i_owe debt remaining balance is liability and subtracts from net worth.
  - owed_to_me loan remaining balance is receivable and adds to net worth.
  - debt payments/collections must link cash movement to keep wallet balances honest.
  - reports use business-effective dates such as occurred_at, paid_at, priced_at,
    and as_of; audit timestamps such as created_at only answer when the row was
    recorded in the system.
```

Auditable field standard:

- Every source-of-truth finance table must include `created_at`, `created_by`, `updated_at`, and `updated_by`.
- Tables that support soft delete must also include `deleted_at` and `deleted_by`.
- Archive/status retirement actor is captured through `updated_by` in Epic 1.
- Append-only historical tables still include `created_at`, `created_by`, `updated_at`, and `updated_by` so correction flows remain traceable.
- Projection tables include audit fields for the projection row itself, but their business source of truth remains the event/transaction tables that rebuild them.
- Audit fields answer "who last touched this row"; finance audit events still answer "what changed before/after and why".
- Soft delete is limited to tables where user correction is expected: `transactions`, `asset_transactions`, and `debt_payments`.
- Soft-deleted rows must be excluded from reports, net-worth calculations, holding rebuilds, and debt remaining-balance calculations.

Initial entities:

- `wallets`
  - `id`, `owner_id`, `name`, `type`, `currency`, `initial_balance_minor`, `current_balance_minor`, `include_in_total`, `status`, `created_at`, `created_by`, `updated_at`, `updated_by`, `archived_at`
- `categories`
  - `id`, `owner_id`, `parent_id`, `name`, `type`, `aliases`, `status`, `created_at`, `created_by`, `updated_at`, `updated_by`
- `transactions`
  - `id`, `owner_id`, `wallet_id`, `category_id`, `type`, `direction`, `amount_minor`, `currency`, `occurred_at`, `note`, `with_person`, `location`, `event_id`, `exclude_from_report`, `transfer_group_id`, `created_at`, `created_by`, `updated_at`, `updated_by`, `deleted_at`, `deleted_by`
- `assets`
  - `id`, `owner_id`, `asset_type`, `symbol`, `name`, `currency`, `unit`, `price_source`, `is_active`, `created_at`, `created_by`, `updated_at`, `updated_by`
- `asset_transactions`
  - `id`, `owner_id`, `asset_id`, `wallet_id`, `transaction_type`, `quantity`, `unit_price_minor`, `gross_amount_minor`, `fee_minor`, `tax_minor`, `net_amount_minor`, `currency`, `occurred_at`, `note`, `linked_cash_transaction_id`, `created_at`, `created_by`, `updated_at`, `updated_by`, `deleted_at`, `deleted_by`
- `asset_holdings`
  - `id`, `owner_id`, `asset_id`, `quantity`, `average_cost_minor`, `total_cost_minor`, `realized_gain_minor`, `current_price_minor`, `current_value_minor`, `unrealized_gain_minor`, `last_priced_at`, `created_at`, `created_by`, `updated_at`, `updated_by`
- `asset_prices`
  - `id`, `owner_id`, `asset_id`, `price_minor`, `buy_price_minor`, `sell_price_minor`, `currency`, `price_type`, `source`, `priced_at`, `created_at`, `created_by`, `updated_at`, `updated_by`
- `debt_loans`
  - `id`, `owner_id`, `direction`, `counterparty`, `principal_amount_minor`, `remaining_amount_minor`, `currency`, `due_date`, `status`, `note`, `created_at`, `created_by`, `updated_at`, `updated_by`, `archived_at`
- `debt_payments`
  - `id`, `owner_id`, `debt_loan_id`, `wallet_id`, `cash_transaction_id`, `amount_minor`, `paid_at`, `note`, `created_at`, `created_by`, `updated_at`, `updated_by`, `deleted_at`, `deleted_by`

Schema migration needed: yes.

### Asset Valuation Rules

- Purchase price is historical execution data and lives on `asset_transactions.unit_price_minor`.
- Current market price is time-series data and lives on `asset_prices`.
- Do not overwrite old prices when a new market price arrives.
- Default cost basis method is `weighted_average_cost`.
- Future tax-specific reporting may add FIFO, but FIFO is out of scope for Epic 1.
- Price selection must be deterministic:
  - Gold: latest `sell_price`, then latest generic `price`, then latest manual fallback.
  - Stock/fund/crypto: latest `close`, then latest `last`, then latest manual fallback.
  - Saving deposit: principal plus accrued interest when available; otherwise latest manual value.
  - Cash equivalent: latest market/manual exchange value when denominated in non-base currency.
- For assets without market feeds, user-entered manual price is allowed.
- `asset_holdings` is current derived state for fast reads; source of truth remains `asset_transactions` plus latest accepted `asset_prices`.
- Holding rebuild rule:
  - Any create/update/delete/backdated edit to an `asset_transaction` must trigger recalculation for that `asset_id`.
  - Recalculation replays asset transactions in `occurred_at`, `created_at`, `id` order.
  - Recalculation must produce the same `quantity`, `average_cost`, `total_cost`, and `realized_gain` as incremental updates.
  - A future repair command should be able to rebuild holdings for one asset or all assets.
- Net worth formula:

```text
net_worth = included_cash_wallets + current_asset_values - debts
current_asset_value = holding.quantity * latest_usable_asset_price
unrealized_gain = current_asset_value - holding.total_cost
```

### Debt, Loan, And Saving Deposit Boundaries

- `debt_loans.direction = i_owe` means the owner owes someone else. Remaining balance is a liability.
- `debt_loans.direction = owed_to_me` means someone else owes the owner. Remaining balance is a receivable asset.
- `debt_payments` record settlement events and must link to cash transactions when cash moves.
- Net worth includes:
  - subtract active `i_owe` remaining balances
  - add active `owed_to_me` remaining balances
  - subtract credit wallet balances when wallet type is `credit`
- `saving_deposit` is modeled as an asset when it has term, interest, or valuation behavior.
- Liquid bank accounts remain wallets, not assets.
- A savings deposit that is funded from a wallet should create/link cash movement similarly to investment buys.

### Reporting Exclusion Rules For Investments

- `investment_buy` / `transfer_to_asset` cash movement decreases wallet balance but is excluded from living-expense totals.
- `investment_sell` cash movement increases wallet balance but is excluded from ordinary income totals.
- Dividends are investment income and should be reported separately from salary/ordinary income.
- Fees and taxes may appear in investment performance reporting, but not as living expenses unless the user explicitly asks for total costs.
- `GetFinancialReport` default view focuses on ordinary cashflow: income, expense, transfers, and excluded/other amount.
- Investment activity belongs in portfolio or net-worth reports unless explicitly included in the report query.

### Query And Report Optimization

Reporting must be designed around predictable PostgreSQL query shapes, not ad hoc scans.

- Transaction reports filter by `owner_id`, `occurred_at` range, `deleted_at IS NULL`, and `exclude_from_report`.
- `created_at` must not drive financial period reports because users may record a transaction today for a past or future business date.
- `created_at` is used for operational/audit views such as "what did I enter today?" and import troubleshooting.
- Cashflow reports aggregate from `transactions` by `type`, `wallet_id`, `category_id`, and date bucket derived from `occurred_at`.
- Asset reports aggregate from `asset_holdings` for current portfolio reads and replay `asset_transactions` only for rebuild/audit/debug flows.
- Asset valuation queries select the latest usable `asset_prices` by `(owner_id, asset_id, priced_at DESC)` with deterministic price-type fallback.
- Debt reports filter `debt_loans` by `owner_id`, `direction`, `status`, and `due_date`; settlement history comes from `debt_payments.paid_at`.
- Net-worth reads should not scan raw transaction history. They combine `wallets.current_balance_minor`, `asset_holdings.current_value_minor`, latest asset price freshness, and active debt/loan remaining balances.
- For Epic 1, use direct indexed aggregate SQL. Add monthly/daily materialized reporting tables only when query volume or report latency proves the need.
- `FinancialReportDTO` must include:
  - `period_start`, `period_end`, `group_by`
  - `income_total_minor`, `expense_total_minor`, `net_cashflow_minor`
  - `transfer_in_total_minor`, `transfer_out_total_minor`
  - `excluded_total_minor`
  - `investment_cash_movement_total_minor`
  - `by_category`, `by_wallet`, and `by_period` breakdowns
  - warnings for ignored soft-deleted records, excluded records, and stale/unknown valuation data

Required initial indexes:

- `transactions(owner_id, occurred_at DESC)` with `deleted_at IS NULL`
- `transactions(owner_id, wallet_id, occurred_at DESC)` with `deleted_at IS NULL`
- `transactions(owner_id, category_id, occurred_at DESC)` with `deleted_at IS NULL`
- `transactions(owner_id, type, occurred_at DESC)` with `deleted_at IS NULL`
- `transactions(owner_id, exclude_from_report, occurred_at DESC)` with `deleted_at IS NULL`
- `transactions(owner_id, transfer_group_id)` where `transfer_group_id IS NOT NULL`
- `asset_transactions(owner_id, asset_id, occurred_at, created_at, id)`
- `asset_holdings(owner_id, asset_id)` unique
- `asset_prices(owner_id, asset_id, priced_at DESC)`
- `debt_loans(owner_id, direction, status, due_date)`
- `debt_payments(owner_id, debt_loan_id, paid_at DESC)`

Required constraints:

- `wallets`: active wallet names must be unique per owner.
- `categories`: category names must be unique per owner, type, and parent.
- `assets`: asset key must be unique per owner, asset type, symbol, and currency.
- `asset_holdings`: exactly one holding row per owner and asset.
- `transactions.amount_minor > 0`.
- `asset_transactions.quantity > 0` except split/adjustment operations where explicit domain rules allow zero cash movement.
- `debt_loans.principal_amount_minor > 0`.
- `debt_loans.remaining_amount_minor >= 0`.
- `debt_payments.amount_minor > 0`.
- Foreign keys must use the same `owner_id` scope to prevent cross-owner linkage.

Soft-delete and correction behavior:

- Soft-deleting `transactions` excludes the row from reports and wallet balance repair calculations.
- Soft-deleting an `asset_transaction` triggers holding recalculation for the affected asset.
- Soft-deleting a `debt_payment` triggers debt remaining-balance recalculation.
- A `debt_payment` with linked `cash_transaction_id` must not be deleted directly. Use a correction/reversal command so cash and debt remain consistent.
- A transaction linked to asset or debt movement must not be deleted directly unless the owning correction command handles linked row reversal/recalculation atomically.

### Deferred From Epic 1

The raw Finance spec includes additional domains that are not covered by `CTX-101` through `CTX-108` and should become later tickets:

- Budgets and budget alerts.
- Saving goals beyond basic goal-wallet support.
- Recurring transactions, bills, subscriptions, and reminders.
- Smart suggestions from historical notes, merchants, amounts, and aliases.
- Receipt OCR/document extraction; Finance only receives structured extracted payloads later.
- Provider sync, market data automation, and external bank/broker integrations.

### Money Representation

Use integer minor units for stored money values. For `VND`, minor units can be whole VND. Do not use floating point for balances, amounts, prices, or net-worth totals.

DB type guidance:

- Money fields use `BIGINT` and the `_minor` suffix.
- Quantity fields use `NUMERIC(30, 12)` to support gold, stock, fund, and crypto fractional positions.
- Currency fields use `CHAR(3)` ISO code and default to `VND` where user input omits currency.
- Application DTOs may expose decimal strings for user-facing values, but persistence remains integer minor units plus explicit currency.

---

## 6. Security & Authorization

- Authentication changes: none in Epic 1.
- Authorization/permissions: future policy service will gate finance writes. Epic 1 services should accept owner/user identifiers in commands so ownership checks can be added without reshaping all APIs.
- Data privacy/PII impact: finance data is sensitive. Logs and errors must not print full transaction notes, people, locations, or raw financial payloads.
- Input validation:
  - amount must be positive for transaction commands
  - wallet/category/asset ids must exist
  - enum values must be constrained
  - archived wallets/categories/assets cannot be used for new writes
- Audit: finance tables must persist `created_at`, `created_by`, `updated_at`, and `updated_by` in Epic 1. Tables that support soft delete also persist `deleted_at` and `deleted_by`. Service commands must carry actor/source metadata so repositories can populate those fields.

---

## 7. Implementation & Verification Plan

### Impacted Areas

- Code/modules: Finance module under `src/backend/internal/modules/finance/`
- Product behavior: wallet/category/transaction/asset/report finance behavior
- API/contracts: internal Finance Domain API contracts
- Data/schema: finance tables and migrations
- Security/auth: sensitive data handling and future ownership seams
- Deployment/runtime: no direct runtime change expected
- Docs: API, ERD, architecture, validation matrix, context, tickets

### Ticket Order

1. `CTX-101`: Wallet API CRUD
2. `CTX-102`: Category API CRUD
3. `CTX-103`: Income/Expense Transaction API
4. `CTX-104`: Transfer Transaction API
5. `CTX-105`: Asset Master API
6. `CTX-106`: Asset Transaction API
7. `CTX-107`: Reporting API
8. `CTX-108`: Net Worth API
9. `CTX-109`: Debt & Loan Tracking API

### Test Plan

- Unit:
  - wallet validation and archive behavior
  - category hierarchy and alias behavior
  - transaction amount/type/date validation
  - transfer net-worth invariant
  - asset transaction cash movement rules
  - weighted-average cost basis updates
  - asset price history selection for current valuation
  - unrealized and realized gain/loss calculations
  - report and net-worth calculations
  - debt/loan direction, remaining balance, settlement, and net-worth impact
  - audit fields populated on create/update paths and on soft-delete paths where supported
- Integration:
  - GORM repository persistence for each entity
  - transaction atomicity for transfers and asset cash movements
  - indexed report queries use `occurred_at` for business periods and `created_at` only for audit/entry-time views
  - migration smoke test against PostgreSQL
- E2E: not required for Epic 1 services because orchestrator/chat delivery is out of scope.
- UAT: required later when orchestrator exposes finance tools to chat; not required for service-only implementation.
- Manual/platform: database migration run and rollback notes when migration tooling is chosen.
- Docs review: required after each ticket implementation.

### Suggested Commands

```bash
cd src/backend
go test ./...
go test ./internal/modules/finance/... -run Wallet
go test ./internal/modules/finance/... -run Transaction
go test ./internal/modules/finance/... -run Asset
go test ./internal/modules/finance/... -run Report
```

### Validation Matrix Impact

- Update required: yes
- Rows:
  - `CTX-101` wallet CRUD and archive behavior
  - `CTX-102` category CRUD, parent/child, alias behavior
  - `CTX-103` income/expense transaction persistence and balance changes
  - `CTX-104` transfer atomicity and net-worth invariant
  - `CTX-105` asset master CRUD, units, price source, active state
  - `CTX-106` asset transaction, holdings, cost basis, price history, and cash movement rules
  - `CTX-107` report aggregation
  - `CTX-108` net-worth calculation using latest market valuation
  - `CTX-109` debt/loan tracking and linked cash movement

### Verification Results

- Command: `cd src/backend && go test ./internal/modules/finance/...`
- Result: pass
- Notes: focused unit tests cover shared owner default, audit helper behavior, money validation, signed report amounts, period grouping, and wallet type validation.
- Command: `cd src/backend && go test ./...`
- Result: pass
- Notes: compile/vet pass across backend packages.
- Command: `cd src/backend && GOCACHE=/private/tmp/cortex-go-cache DATABASE_URL=postgres://dev:password@localhost:5432/cortex?sslmode=disable go test ./...`
- Result: pass
- Notes: local PostgreSQL integration tests execute the real migration in an isolated schema and cover the end-to-end finance service flow plus critical validation cases.

---

## 8. Reconciliation Plan

- Requirements docs: update after implementation if behavior differs from `REQ-003`, `REQ-004`, or `REQ-005`
- Architecture docs: update with actual Finance package shape and service boundaries
- API docs: update with final Finance Domain API signatures
- ERD docs: update with final tables, fields, indexes, and relationships
- SDD docs: no change unless high-level service architecture changes
- ADR: create only if money representation, migration tooling, or transaction modeling introduces a durable tradeoff
- Context: update after each completed ticket

### Docs Review Checklist

- Code changed but docs unchanged reason: not applicable after implementation; docs must be checked per ticket
- Requirements updated or not needed reason: TBD per ticket
- Architecture updated or not needed reason: TBD per ticket
- API updated or not needed reason: TBD per ticket
- ERD/data updated or not needed reason: TBD per ticket
- SDD updated or not needed reason: TBD per ticket
- ADR created or not needed reason: TBD per ticket
