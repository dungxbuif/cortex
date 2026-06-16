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

- `CreateTransaction(command)`: Record income, expense, or cash transfers.
- `CreateTransfer(command)`: Move money between wallets.
- `RecordAssetTransaction(command)`: Buy, sell, or receive dividends for investments.
- `GetFinancialReport(query)`: Return aggregated cash flow and expense reporting.
- `GetNetWorth(query)`: Calculate total asset values minus liabilities.
- `CreateCategory(command)` / `CreateWallet(command)`: Master data management.

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
