---
artifact_type: api_doc
id: API-MASTER
status: draft
owner: shared
human_fields: [public_contracts, authentication_rules]
ai_fields: [endpoints, schemas, error_codes]
shared_fields: [status]
---

# API Contracts

## Field Ownership

- Human owns public contracts and authentication rules.
- AI maintains endpoints, schemas, and error codes.

## Public Contracts

The primary interface to Cortex is the OpenAI-compatible `/v1/chat/completions` API. All UI interactions happen through this single proxy layer.

## Domain APIs

The domain modules do not expose REST HTTP endpoints individually; they expose Go function signatures (or internal RPCs) that the Orchestrator's Tool Adapter invokes. Below are the core Domain APIs defined for the modules.

### Finance Module

Wallet and category APIs:

- `CreateWallet(command)`: Create a wallet/account with type, currency, initial balance, include-in-total flag, and active status.
- `UpdateWallet(wallet_id, patch)`: Update wallet metadata without corrupting current balance.
- `ArchiveWallet(wallet_id)`: Archive an inactive wallet so future transactions cannot use it.
- `ListWallets(query)`: List active/archived wallets.
- `GetWalletBalance(wallet_id, as_of)`: Return wallet balance at a point in time.
- `CreateCategory(command)`: Create an income/expense category with optional parent and aliases.
- `UpdateCategory(category_id, patch)`: Update category metadata.
- `ListCategories(query)`: List category hierarchy and visibility.
- `ResolveCategory(input)`: Suggest a category from note, merchant, alias, or history.

Transaction APIs:

- `CreateTransaction(command)`: Record income or expense.
- `CreateTransfer(command)`: Move money between wallets without changing net worth by creating paired `transfer_out` and `transfer_in` rows with one `transfer_group_id`.
- `UpdateTransaction(transaction_id, patch)`: Update an existing transaction.
- `SoftDeleteTransaction(transaction_id, reason)`: Soft-delete a transaction.
- `ListTransactions(query)`: List/search transactions by business date (`occurred_at`) or audit entry date (`created_at`) depending on query mode.

Investment asset APIs:

- `CreateAsset(command)`: Create asset master data with asset type, symbol, name, currency, unit, price source, and active state.
- `RecordAssetTransaction(command)`: Record buy, sell, transfer in/out, dividend, stock dividend, split, or manual adjustment.
- `UpdateAssetPrice(command)`: Append a new market/manual price snapshot without overwriting historical prices.
- `GetAssetHolding(query)`: Return current position, cost basis, current price, current value, realized gain, and unrealized gain for one asset.
- `ListAssetHoldings(query)`: Return portfolio holdings by asset class.

Report and valuation APIs:

- `GetFinancialReport(query)`: Return aggregated cash flow and expense reporting by business-effective date with income, expense, net cashflow, transfer totals, excluded totals, investment cash movement, category/wallet/period breakdowns, and warnings.
- `GetNetWorth(query)`: Calculate included cash wallets plus current market-valued assets and receivables minus debts/credit liabilities.

Debt and loan APIs:

- `CreateDebtOrLoan(command)`: Create a liability (`i_owe`) or receivable (`owed_to_me`) with counterparty, principal amount, currency, due date, note, and status.
- `UpdateDebtOrLoan(id, patch)`: Update metadata, due date, note, or status.
- `RecordDebtPayment(command)`: Record payment/collection and link it to wallet cash movement.
- `GetDebtStatus(query)`: Return principal, paid/collected amount, remaining amount, due date, and status.
- `ListDebts(query)`: List active, settled, forgiven, archived, payable, and receivable records.

### Second Brain Module

- `CaptureNote(command)`: Save an idea/note to the temporary capture buffer database.
- `QueryVault(query)`: Search indexed Obsidian vault items via RAG.
- `GetSyncStatus(query)`: Check the last time the Vault mirror was updated.

### Homelab Module

- `SearchDocs(query)`: RAG query over the Homelab documentation.
- `GetServiceCatalog()`: List deployed Homelab services.

## Error Handling

APIs should return structured errors (via Go `error` interfaces) mapped to the following concepts:
- `NeedsConfirmation`: The request lacks confidence and the Orchestrator must ask the user (e.g. fuzzy category matching).
- `ValidationError`: Missing required fields (e.g. amount <= 0).
- `Conflict`: Resource already exists.
- `NotFound`: Entity missing.
