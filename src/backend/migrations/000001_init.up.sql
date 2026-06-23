DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
        CREATE EXTENSION IF NOT EXISTS vector;
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS wallets (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'VND',
    initial_balance_minor BIGINT NOT NULL,
    current_balance_minor BIGINT NOT NULL,
    include_in_total BOOLEAN NOT NULL DEFAULT TRUE,
    status TEXT NOT NULL,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_wallets_owner_active_name
    ON wallets (owner_id, lower(name))
    WHERE status = 'active';

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    parent_id TEXT REFERENCES categories(id),
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    aliases TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_owner_type_parent_name
    ON categories (owner_id, type, COALESCE(parent_id, ''), lower(name));

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    wallet_id TEXT NOT NULL REFERENCES wallets(id),
    category_id TEXT REFERENCES categories(id),
    type TEXT NOT NULL,
    direction TEXT NOT NULL,
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    currency CHAR(3) NOT NULL DEFAULT 'VND',
    occurred_at TIMESTAMPTZ NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    with_person TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    event_id TEXT NOT NULL DEFAULT '',
    exclude_from_report BOOLEAN NOT NULL DEFAULT FALSE,
    transfer_group_id TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL,
    deleted_at TIMESTAMPTZ,
    deleted_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_transactions_owner_occurred_active
    ON transactions (owner_id, occurred_at DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_owner_wallet_occurred_active
    ON transactions (owner_id, wallet_id, occurred_at DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_owner_category_occurred_active
    ON transactions (owner_id, category_id, occurred_at DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_owner_type_occurred_active
    ON transactions (owner_id, type, occurred_at DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_owner_excluded_occurred_active
    ON transactions (owner_id, exclude_from_report, occurred_at DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_owner_transfer_group
    ON transactions (owner_id, transfer_group_id)
    WHERE transfer_group_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'VND',
    unit TEXT NOT NULL,
    price_source TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_owner_key
    ON assets (owner_id, asset_type, symbol, currency);

CREATE TABLE IF NOT EXISTS asset_transactions (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    wallet_id TEXT REFERENCES wallets(id),
    linked_cash_transaction_id TEXT REFERENCES transactions(id),
    transaction_type TEXT NOT NULL,
    quantity NUMERIC(30, 12) NOT NULL,
    unit_price_minor BIGINT NOT NULL,
    gross_amount_minor BIGINT NOT NULL CHECK (gross_amount_minor >= 0),
    fee_minor BIGINT NOT NULL CHECK (fee_minor >= 0),
    tax_minor BIGINT NOT NULL CHECK (tax_minor >= 0),
    net_amount_minor BIGINT NOT NULL CHECK (net_amount_minor >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'VND',
    occurred_at TIMESTAMPTZ NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL,
    deleted_at TIMESTAMPTZ,
    deleted_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_asset_transactions_owner_asset_rebuild
    ON asset_transactions (owner_id, asset_id, occurred_at, created_at, id)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS asset_holdings (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    quantity NUMERIC(30, 12) NOT NULL,
    average_cost_minor BIGINT NOT NULL,
    total_cost_minor BIGINT NOT NULL,
    realized_gain_minor BIGINT NOT NULL,
    current_price_minor BIGINT NOT NULL,
    current_value_minor BIGINT NOT NULL,
    unrealized_gain_minor BIGINT NOT NULL,
    last_priced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL,
    UNIQUE (owner_id, asset_id)
);

CREATE TABLE IF NOT EXISTS asset_prices (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    price_minor BIGINT NOT NULL DEFAULT 0,
    buy_price_minor BIGINT NOT NULL DEFAULT 0,
    sell_price_minor BIGINT NOT NULL DEFAULT 0,
    currency CHAR(3) NOT NULL DEFAULT 'VND',
    price_type TEXT NOT NULL,
    source TEXT NOT NULL,
    priced_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_asset_prices_owner_asset_priced
    ON asset_prices (owner_id, asset_id, priced_at DESC);

CREATE TABLE IF NOT EXISTS debt_loans (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    counterparty TEXT NOT NULL,
    principal_amount_minor BIGINT NOT NULL CHECK (principal_amount_minor > 0),
    remaining_amount_minor BIGINT NOT NULL CHECK (remaining_amount_minor >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'VND',
    due_date TIMESTAMPTZ,
    status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_debt_loans_owner_direction_status_due
    ON debt_loans (owner_id, direction, status, due_date);

CREATE TABLE IF NOT EXISTS debt_payments (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    debt_loan_id TEXT NOT NULL REFERENCES debt_loans(id),
    wallet_id TEXT NOT NULL REFERENCES wallets(id),
    cash_transaction_id TEXT REFERENCES transactions(id),
    amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
    paid_at TIMESTAMPTZ NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL,
    deleted_at TIMESTAMPTZ,
    deleted_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_debt_payments_owner_debt_paid
    ON debt_payments (owner_id, debt_loan_id, paid_at DESC)
    WHERE deleted_at IS NULL;
