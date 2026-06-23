package tests

import (
	"context"
	"testing"
	"time"

	"cortex/internal/modules/finance/domain"
	"cortex/internal/modules/finance/service"
)

func TestDebtSettlementEdgeCases(t *testing.T) {
	db := integrationDB(t)
	svc := service.NewFinanceService(db)
	ctx := context.Background()

	// 1. Direction IOwe (Liability)
	_, err := svc.CreateDebtOrLoan(ctx, domain.CreateDebtOrLoanCommand{
		Direction:            domain.DebtDirectionIOwe,
		Counterparty:         "Bank",
		PrincipalAmountMinor: 5_000_000,
		Currency:             "VND",
	})
	if err != nil {
		t.Fatalf("create debt: %v", err)
	}

	// NetWorth query should see liability
	netWorth, err := svc.GetNetWorth(ctx, domain.NetWorthQuery{AsOf: time.Now()})
	if err != nil {
		t.Fatalf("get net worth: %v", err)
	}
	if netWorth.LiabilityMinor < 5_000_000 {
		t.Errorf("expected liability to be at least 5000000, got %d", netWorth.LiabilityMinor)
	}

	// 2. Direction OwedToMe (Receivable / Asset)
	owedToMe, err := svc.CreateDebtOrLoan(ctx, domain.CreateDebtOrLoanCommand{
		Direction:            domain.DebtDirectionOwedToMe,
		Counterparty:         "Alice",
		PrincipalAmountMinor: 2_000_000,
		Currency:             "VND",
	})
	if err != nil {
		t.Fatalf("create loan: %v", err)
	}

	// NetWorth query should see receivable
	netWorth, err = svc.GetNetWorth(ctx, domain.NetWorthQuery{AsOf: time.Now()})
	if err != nil {
		t.Fatalf("get net worth: %v", err)
	}
	if netWorth.ReceivableMinor < 2_000_000 {
		t.Errorf("expected receivable to be at least 2000000, got %d", netWorth.ReceivableMinor)
	}

	// 3. Debt Settlement limits using GORM checks
	wallet, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{
		Name:                "Debt Payment Wallet",
		Type:                domain.WalletTypeBasic,
		InitialBalanceMinor: 10_000_000,
		IncludeInTotal:      true,
	})
	if err != nil {
		t.Fatalf("create wallet: %v", err)
	}

	_, err = svc.RecordDebtPayment(ctx, domain.RecordDebtPaymentCommand{
		DebtLoanID:  owedToMe.ID,
		WalletID:    wallet.ID,
		AmountMinor: 1_500_000, // Partial payment
		PaidAt:      time.Now(),
	})
	if err != nil {
		t.Fatalf("record debt payment: %v", err)
	}

	// Verify remaining amount directly via GORM
	var updatedLoan domain.DebtLoan
	db.First(&updatedLoan, "id = ?", owedToMe.ID)

	if updatedLoan.RemainingAmountMinor != 500_000 {
		t.Errorf("expected remaining amount 500000, got %d", updatedLoan.RemainingAmountMinor)
	}

	// Attempt to overpay the remaining amount
	_, err = svc.RecordDebtPayment(ctx, domain.RecordDebtPaymentCommand{
		DebtLoanID:  owedToMe.ID,
		WalletID:    wallet.ID,
		AmountMinor: 600_000, // Overpayment
		PaidAt:      time.Now(),
	})
	if err == nil {
		t.Error("expected error when overpaying debt, got nil")
	}
}
