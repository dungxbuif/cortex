package tests

import (
	"context"
	"testing"
	"time"

	"cortex/internal/modules/finance/domain"
	"cortex/internal/modules/finance/service"
)

func TestWalletCategoryEdgeCases(t *testing.T) {
	db := integrationDB(t)
	svc := service.NewFinanceService(db)
	ctx := context.Background()

	// 1. Soft-deleted/Archived Wallet cannot be used
	wallet, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{
		Name:                "Temp Wallet",
		Type:                domain.WalletTypeBasic,
		InitialBalanceMinor: 10_000,
		IncludeInTotal:      true,
	})
	if err != nil {
		t.Fatalf("create wallet: %v", err)
	}

	err = svc.ArchiveWallet(ctx, wallet.OwnerID, "test-actor", wallet.ID)
	if err != nil {
		t.Fatalf("archive wallet: %v", err)
	}

	category, err := svc.CreateCategory(ctx, domain.CreateCategoryCommand{
		Name: "Test Expense",
		Type: domain.CategoryTypeExpense,
	})
	if err != nil {
		t.Fatalf("create category: %v", err)
	}

	_, err = svc.CreateIncomeExpense(ctx, domain.CreateTransactionCommand{
		WalletID:    wallet.ID,
		CategoryID:  &category.ID,
		Type:        domain.TransactionTypeExpense,
		AmountMinor: 5_000,
		OccurredAt:  time.Now(),
	})
	if err == nil {
		t.Error("expected error when transacting on an archived wallet, got nil")
	}

	// 2. Category names must be unique per type
	_, err = svc.CreateCategory(ctx, domain.CreateCategoryCommand{
		Name: "Test Expense", // Same name
		Type: domain.CategoryTypeExpense,
	})
	if err == nil {
		t.Error("expected error when creating duplicate category name for the same type")
	}

	// But it CAN be created under a different type
	_, err = svc.CreateCategory(ctx, domain.CreateCategoryCommand{
		Name: "Test Expense", // Same name, different type
		Type: domain.CategoryTypeIncome,
	})
	if err != nil {
		t.Errorf("unexpected error when creating category with same name but different type: %v", err)
	}
}
