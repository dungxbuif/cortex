---
artifact_type: erd_doc
id: ERD-MASTER
status: draft
owner: shared
human_fields: [data_ownership_rules]
ai_fields: [entities, relationships, data_dictionaries]
shared_fields: [status]
---

# Entity Relationship Diagram

## Field Ownership

- Human owns data ownership rules (which system owns what).
- AI maintains entities, relationships, and data dictionaries.

## Data Ownership Rules

According to the Source of Truth matrix (`docs/raw_spec/spec.md`):
- **Finance Module**: Owns all its canonical data within Cortex PostgreSQL (Wallets, Categories, Transactions, Assets).
- **Second Brain Module**: Owns only its *capture buffer* in PostgreSQL. The canonical Vault data is owned by local Obsidian files and is mirrored/indexed by Cortex.
- **Homelab Module**: Completely read-only, sourcing from GitHub repos.

## Finance Entities

The Finance database separates cashflow from investment valuation:

- `transactions` represent income, expense, transfer, and cash movement records.
- `asset_transactions` represent historical investment events and execution prices.
- `asset_holdings` represent current derived positions and cost basis.
- `asset_prices` preserve market/manual price history.
- Net worth is computed from included wallet balances plus current asset values minus liabilities.
- Debt/loan tracking distinguishes money I owe from money owed to me.
- Finance tables carry auditable fields so each row records actor and timestamp metadata.
- Financial period reports use business-effective timestamps such as `occurred_at`, `paid_at`, `priced_at`, and `as_of`; `created_at` is only the system record creation timestamp.

```mermaid
erDiagram
    WALLET ||--o{ TRANSACTION : "has"
    CATEGORY ||--o{ TRANSACTION : "categorizes"
    ASSET ||--o{ ASSET_TRANSACTION : "tracked via"
    WALLET ||--o{ ASSET_TRANSACTION : "funds / receives from"
    TRANSACTION ||--o{ ASSET_TRANSACTION : "linked cash movement"
    ASSET ||--o{ ASSET_HOLDING : "current position"
    ASSET ||--o{ ASSET_PRICE : "price history"
    DEBT_LOAN ||--o{ DEBT_PAYMENT : "settled by"
    WALLET ||--o{ DEBT_PAYMENT : "cash movement"
    TRANSACTION ||--o{ DEBT_PAYMENT : "linked cash transaction"

    WALLET {
        string id PK
        string owner_id
        string name
        string type "basic, goal, credit, linked"
        string currency
        int initial_balance_minor
        int current_balance_minor
        boolean include_in_total
        string status "active, archived"
        datetime created_at
        string created_by
        datetime updated_at
        string updated_by
        datetime archived_at
    }

    CATEGORY {
        string id PK
        string owner_id
        string name
        string parent_id FK
        string type "income, expense"
        json aliases
        string status
        datetime created_at
        string created_by
        datetime updated_at
        string updated_by
    }

    TRANSACTION {
        string id PK
        string owner_id
        string wallet_id FK
        string category_id FK
        string type "income, expense, transfer_in, transfer_out"
        string direction "debit, credit"
        int amount_minor
        string currency
        datetime occurred_at
        string note
        string with_person
        string location
        string event_id
        boolean exclude_from_report
        string transfer_group_id
        datetime created_at
        string created_by
        datetime updated_at
        string updated_by
        datetime deleted_at
        string deleted_by
    }

    ASSET {
        string id PK
        string owner_id
        string asset_type "gold, stock, fund, crypto, saving_deposit, cash_equivalent, other"
        string symbol
        string name
        string currency
        string unit
        string price_source "manual, provider_api, n8n_webhook"
        boolean is_active
        datetime created_at
        string created_by
        datetime updated_at
        string updated_by
    }

    ASSET_TRANSACTION {
        string id PK
        string owner_id
        string asset_id FK
        string wallet_id FK
        string linked_cash_transaction_id FK
        string transaction_type "buy, sell, transfer_in, transfer_out, dividend, stock_dividend, split, price_adjustment"
        numeric quantity
        int unit_price_minor
        int gross_amount_minor
        int fee_minor
        int tax_minor
        int net_amount_minor
        string currency
        datetime occurred_at
        datetime created_at
        string created_by
        datetime updated_at
        string updated_by
        datetime deleted_at
        string deleted_by
    }

    ASSET_HOLDING {
        string id PK
        string owner_id
        string asset_id FK
        numeric quantity
        int average_cost_minor
        int total_cost_minor
        int realized_gain_minor
        int current_price_minor
        int current_value_minor
        int unrealized_gain_minor
        datetime last_priced_at
        datetime created_at
        string created_by
        datetime updated_at
        string updated_by
    }

    ASSET_PRICE {
        string id PK
        string owner_id
        string asset_id FK
        int price_minor
        int buy_price_minor
        int sell_price_minor
        string currency
        string price_type "buy, sell, close, manual, estimated"
        string source
        datetime priced_at
        datetime created_at
        string created_by
        datetime updated_at
        string updated_by
    }

    DEBT_LOAN {
        string id PK
        string owner_id
        string direction "i_owe, owed_to_me"
        string counterparty
        int principal_amount_minor
        int remaining_amount_minor
        string currency
        datetime due_date
        string status "active, partially_settled, settled, forgiven, archived"
        string note
        datetime created_at
        string created_by
        datetime updated_at
        string updated_by
        datetime archived_at
    }

    DEBT_PAYMENT {
        string id PK
        string owner_id
        string debt_loan_id FK
        string wallet_id FK
        string cash_transaction_id FK
        int amount_minor
        datetime paid_at
        string note
        datetime created_at
        string created_by
        datetime updated_at
        string updated_by
        datetime deleted_at
        string deleted_by
    }
```

### Finance Valuation Rules

- Historical purchase/sale price lives on `ASSET_TRANSACTION.unit_price_minor`.
- Current market value comes from the latest usable `ASSET_PRICE`.
- Price history is append-only for valuation purposes; do not overwrite prior market prices.
- Default cost basis is weighted average.
- Deterministic price priority:
  - Gold: latest `sell_price`, latest generic `price`, latest manual fallback.
  - Stocks/funds/crypto: latest close, latest last, latest manual fallback.
  - Saving deposit: principal plus accrued interest when available; otherwise latest manual value.
- Investment buys may reduce wallet cash but must not count as living expenses.
- `ASSET_HOLDING` is a rebuildable projection from `ASSET_TRANSACTION` plus latest usable `ASSET_PRICE`.
- `DEBT_LOAN.direction = i_owe` is a liability and subtracts from net worth.
- `DEBT_LOAN.direction = owed_to_me` is a receivable and adds to net worth.
- Debt payments/collections link to cash transactions so wallet balances and debt balances stay aligned.

### Finance Query Rules

- Use `TRANSACTION.occurred_at` for financial period reports, not `TRANSACTION.created_at`.
- Use `created_at`/`created_by` and `updated_at`/`updated_by` for operational audit views.
- Net-worth reads combine `WALLET.current_balance_minor`, `ASSET_HOLDING.current_value_minor`, latest usable `ASSET_PRICE`, and active `DEBT_LOAN.remaining_amount_minor`; they must not scan raw transaction history for normal reads.
- Money fields use `BIGINT` minor units and the `_minor` suffix. Quantity fields use `NUMERIC(30, 12)`.
- Transfers are stored as two `TRANSACTION` rows with the same `transfer_group_id`: one `transfer_out` row and one `transfer_in` row.
- Soft delete is limited to `TRANSACTION`, `ASSET_TRANSACTION`, and `DEBT_PAYMENT`; soft-deleted rows are excluded from reports, valuation rebuilds, and debt settlement calculations.
- Linked asset/debt cash movement rows require correction or reversal commands so related records stay consistent.
- Initial report indexes:
  - `transactions(owner_id, occurred_at DESC)` where `deleted_at IS NULL`
  - `transactions(owner_id, wallet_id, occurred_at DESC)` where `deleted_at IS NULL`
  - `transactions(owner_id, category_id, occurred_at DESC)` where `deleted_at IS NULL`
  - `transactions(owner_id, type, occurred_at DESC)` where `deleted_at IS NULL`
  - `transactions(owner_id, exclude_from_report, occurred_at DESC)` where `deleted_at IS NULL`
  - `transactions(owner_id, transfer_group_id)` where `transfer_group_id IS NOT NULL`
  - `asset_transactions(owner_id, asset_id, occurred_at, created_at, id)`
  - `asset_holdings(owner_id, asset_id)` unique
  - `asset_prices(owner_id, asset_id, priced_at DESC)`
  - `debt_loans(owner_id, direction, status, due_date)`
  - `debt_payments(owner_id, debt_loan_id, paid_at DESC)`
- Initial constraints:
  - active wallet names are unique per owner
  - category names are unique per owner, type, and parent
  - assets are unique per owner, asset type, symbol, and currency
  - `asset_holdings(owner_id, asset_id)` is unique
  - `_minor` amount fields are positive and `remaining_amount_minor` is non-negative
  - linked finance rows must stay inside the same `owner_id`

## System / Event Entities

```mermaid
erDiagram
    AUDIT_EVENT {
        string id PK
        string module
        string action "create_transaction, deny_permission, sync"
        string details
        datetime created_at
    }
```
