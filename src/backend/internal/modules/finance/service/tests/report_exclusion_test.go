package tests

import (
	"context"
	"testing"
	"time"

	"cortex/internal/modules/finance/domain"
	"cortex/internal/modules/finance/service"
)

func TestReportExclusions(t *testing.T) {
	db := integrationDB(t)
	svc := service.NewFinanceService(db)
	ctx := context.Background()
	now := time.Now()

	// 1. Setup Wallet and Asset
	bank, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{
		Name:                "Investment Bank",
		Type:                domain.WalletTypeBasic,
		InitialBalanceMinor: 1_000_000,
		IncludeInTotal:      true,
		Currency:            "USD",
	})
	if err != nil {
		t.Fatalf("create wallet: %v", err)
	}

	asset, err := svc.CreateAsset(ctx, domain.CreateAssetCommand{
		AssetType:   domain.AssetTypeStock,
		Symbol:      "TSLA",
		Name:        "Tesla Inc.",
		Currency:    "USD",
		Unit:        "share",
		PriceSource: "manual",
	})
	if err != nil {
		t.Fatalf("create asset: %v", err)
	}

	// 2. Buy Asset - creates a Cash Transaction with exclude_from_report = true implicitly
	_, err = svc.RecordAssetTransaction(ctx, domain.RecordAssetTransactionCommand{
		AssetID:          asset.ID,
		WalletID:         &bank.ID,
		Type:             domain.AssetTransactionBuy,
		Quantity:         "5.000000000000",
		UnitPriceMinor:   200_00,
		GrossAmountMinor: 1_000_00,
		FeeMinor:         0,
		TaxMinor:         0,
		NetAmountMinor:   1_000_00, // $1000 spend
		Currency:         "USD",
		OccurredAt:       now,
	})
	if err != nil {
		t.Fatalf("record asset buy: %v", err)
	}

	// 3. Regular Expense
	category, err := svc.CreateCategory(ctx, domain.CreateCategoryCommand{
		Name: "Food",
		Type: domain.CategoryTypeExpense,
	})
	if err != nil {
		t.Fatalf("create category: %v", err)
	}

	_, err = svc.CreateIncomeExpense(ctx, domain.CreateTransactionCommand{
		WalletID:    bank.ID,
		CategoryID:  &category.ID,
		Type:        domain.TransactionTypeExpense,
		AmountMinor: 50_00, // $50
		Currency:    "USD",
		OccurredAt:  now,
	})
	if err != nil {
		t.Fatalf("create expense: %v", err)
	}

	// 4. Get Financial Report
	report, err := svc.GetFinancialReport(ctx, domain.ReportQuery{
		PeriodStart: now.Add(-time.Hour),
		PeriodEnd:   now.Add(time.Hour),
		GroupBy:     "none",
	})
	if err != nil {
		t.Fatalf("get financial report: %v", err)
	}

	// The $1000 spend on the asset should NOT be in ExpenseTotalMinor
	// Only the $50 regular expense should be.
	if report.ExpenseTotalMinor != 50_00 {
		t.Errorf("expected regular expense total 5000, got %d", report.ExpenseTotalMinor)
	}

	// The $1000 should be in ExcludedTotalMinor
	if report.ExcludedTotalMinor != 1_000_00 {
		t.Errorf("expected excluded total 100000, got %d", report.ExcludedTotalMinor)
	}

	// 5. Test Reversals / Soft Delete via GORM direct execution (since soft delete is domain feature)
	// Soft delete the regular expense
	err = db.Exec("UPDATE transactions SET deleted_at = ? WHERE amount_minor = 5000 AND exclude_from_report = false", now).Error
	if err != nil {
		t.Fatalf("soft delete expense: %v", err)
	}

	// Get report again
	report2, err := svc.GetFinancialReport(ctx, domain.ReportQuery{
		PeriodStart: now.Add(-time.Hour),
		PeriodEnd:   now.Add(time.Hour),
		GroupBy:     "none",
	})
	if err != nil {
		t.Fatalf("get financial report 2: %v", err)
	}

	// Expense should now be 0
	if report2.ExpenseTotalMinor != 0 {
		t.Errorf("expected expense total 0 after soft delete, got %d", report2.ExpenseTotalMinor)
	}
}
