package tests

import (
	"context"
	"testing"
	"time"

	"cortex/internal/modules/finance/domain"
	"cortex/internal/modules/finance/service"
)

func TestTransactionAndTransferEdgeCases(t *testing.T) {
	db := integrationDB(t)
	svc := service.NewFinanceService(db)
	ctx := context.Background()

	cash, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{
		Name:                "Cash Wallet",
		Type:                domain.WalletTypeBasic,
		InitialBalanceMinor: 20_000,
		IncludeInTotal:      true,
	})
	if err != nil {
		t.Fatalf("create cash wallet: %v", err)
	}

	bank, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{
		Name:                "Bank Wallet",
		Type:                domain.WalletTypeBasic,
		InitialBalanceMinor: 5_000,
		IncludeInTotal:      true,
	})
	if err != nil {
		t.Fatalf("create bank wallet: %v", err)
	}

	// 1. Cross-Wallet Transfer produces exactly 2 rows with the same TransferGroupID
	transferRows, err := svc.CreateTransfer(ctx, domain.CreateTransferCommand{
		FromWalletID: cash.ID,
		ToWalletID:   bank.ID,
		AmountMinor:  5_000,
		OccurredAt:   time.Now(),
		Note:         "Test Transfer",
	})
	if err != nil {
		t.Fatalf("create transfer: %v", err)
	}

	if len(transferRows) != 2 {
		t.Fatalf("expected 2 transfer rows, got %d", len(transferRows))
	}

	groupID := transferRows[0].TransferGroupID
	if groupID == nil || *groupID == "" {
		t.Fatalf("expected transfer_group_id to be populated, got nil")
	}

	if *transferRows[1].TransferGroupID != *groupID {
		t.Fatalf("expected transfer_group_id to match for both rows")
	}

	// Check DB state using GORM to verify atomicity and rows
	var txs []domain.Transaction
	db.Where("transfer_group_id = ?", *groupID).Find(&txs)
	if len(txs) != 2 {
		t.Fatalf("expected 2 transactions in DB for transfer group, got %d", len(txs))
	}

	var transferOut, transferIn domain.Transaction
	for _, tx := range txs {
		if tx.Type == domain.TransactionTypeTransferOut {
			transferOut = tx
		} else if tx.Type == domain.TransactionTypeTransferIn {
			transferIn = tx
		}
	}

	if transferOut.Direction != domain.DirectionDebit || transferOut.AmountMinor != 5_000 || transferOut.WalletID != cash.ID {
		t.Errorf("transfer_out row is incorrect: %+v", transferOut)
	}
	if transferIn.Direction != domain.DirectionCredit || transferIn.AmountMinor != 5_000 || transferIn.WalletID != bank.ID {
		t.Errorf("transfer_in row is incorrect: %+v", transferIn)
	}

	// 2. Verify Wallet Balances via GORM
	var updatedCash, updatedBank domain.Wallet
	db.First(&updatedCash, "id = ?", cash.ID)
	db.First(&updatedBank, "id = ?", bank.ID)

	if updatedCash.CurrentBalanceMinor != 15_000 {
		t.Errorf("expected cash balance 15000, got %d", updatedCash.CurrentBalanceMinor)
	}
	if updatedBank.CurrentBalanceMinor != 10_000 {
		t.Errorf("expected bank balance 10000, got %d", updatedBank.CurrentBalanceMinor)
	}
}
