package tests

import (
	"testing"
)

func TestMigrationSmoke(t *testing.T) {
	// integrationDB creates a fresh schema and applies the 000001_init.up.sql migration.
	// If it succeeds, it means the SQL executes without syntax errors.
	db := integrationDB(t)

	// List of tables expected from Epic 1 ERD
	expectedTables := []string{
		"wallets",
		"categories",
		"transactions",
		"assets",
		"asset_transactions",
		"asset_prices",
		"asset_holdings",
		"debt_loans",
		"debt_payments",
	}

	migrator := db.Migrator()
	for _, table := range expectedTables {
		if !migrator.HasTable(table) {
			t.Errorf("expected table %q to exist after migration, but it was not found", table)
		}
	}
}
