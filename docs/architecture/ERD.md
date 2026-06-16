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

```mermaid
erDiagram
    WALLET ||--o{ TRANSACTION : "has"
    CATEGORY ||--o{ TRANSACTION : "categorizes"
    ASSET ||--o{ ASSET_TRANSACTION : "tracked via"
    WALLET ||--o{ ASSET_TRANSACTION : "funds / receives from"
    
    WALLET {
        string id PK
        string name
        string type "basic, goal, credit"
        string currency
        numeric balance
    }
    
    CATEGORY {
        string id PK
        string name
        string parent_id FK
    }
    
    TRANSACTION {
        string id PK
        string wallet_id FK
        string category_id FK
        string type "income, expense, transfer"
        numeric amount
        string currency
        datetime occurred_at
        string note
    }
    
    ASSET {
        string id PK
        string type "gold, stock, crypto"
        string symbol
        string name
    }
    
    ASSET_TRANSACTION {
        string id PK
        string asset_id FK
        string wallet_id FK
        string transaction_type "buy, sell, dividend"
        numeric quantity
        numeric unit_price
        numeric net_amount
    }
```

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
