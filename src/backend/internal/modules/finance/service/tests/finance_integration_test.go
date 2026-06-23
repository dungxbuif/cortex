package tests

import (
	"context"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"cortex/internal/modules/finance/domain"
	"cortex/internal/modules/finance/service"
	"github.com/joho/godotenv"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func integrationDB(t *testing.T) *gorm.DB {
	t.Helper()
	_ = godotenv.Load("../../../../../.env") // ignore error if not exists
	dsn := os.Getenv("FINANCE_TEST_DATABASE_URL")
	if dsn == "" {
		dsn = os.Getenv("DATABASE_URL")
	}
	if dsn == "" {
		t.Skip("set FINANCE_TEST_DATABASE_URL or DATABASE_URL for integration tests")
	}

	schema := "finance_test_" + strings.ToLower(strings.ReplaceAll(domain.NewID("schema"), "-", "_"))
	admin, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		t.Fatalf("open admin db: %v", err)
	}
	if err := admin.Exec("CREATE SCHEMA " + schema).Error; err != nil {
		t.Fatalf("create schema: %v", err)
	}
	t.Cleanup(func() {
		_ = admin.Exec("DROP SCHEMA " + schema + " CASCADE").Error
		if sqlDB, err := admin.DB(); err == nil {
			_ = sqlDB.Close()
		}
	})

	schemaDSN := dsnWithSearchPath(t, dsn, schema)
	db, err := gorm.Open(postgres.Open(schemaDSN), &gorm.Config{})
	if err != nil {
		t.Fatalf("open schema db: %v", err)
	}
	if sqlDB, err := db.DB(); err == nil {
		sqlDB.SetMaxOpenConns(1)
		t.Cleanup(func() { _ = sqlDB.Close() })
	}

	migrationSQL, err := os.ReadFile(findMigrationPath(t))
	if err != nil {
		t.Fatalf("read migration: %v", err)
	}
	if err := db.Exec(string(migrationSQL)).Error; err != nil {
		t.Fatalf("run migration: %v", err)
	}
	return db
}

func findMigrationPath(t *testing.T) string {
	t.Helper()
	wd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	for i := 0; i < 8; i++ {
		candidate := filepath.Join(wd, "migrations", "000001_init.up.sql")
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
		wd = filepath.Dir(wd)
	}
	t.Fatal("migration file not found")
	return ""
}

func dsnWithSearchPath(t *testing.T, raw, schema string) string {
	t.Helper()
	u, err := url.Parse(raw)
	if err != nil {
		t.Fatalf("parse dsn: %v", err)
	}
	q := u.Query()
	q.Set("search_path", schema)
	u.RawQuery = q.Encode()
	return u.String()
}

func TestFinanceEpic1EndToEndServiceFlow(t *testing.T) {
	db := integrationDB(t)
	svc := service.NewFinanceService(db)
	ctx := context.Background()
	occurred := time.Date(2026, 6, 17, 9, 0, 0, 0, time.UTC)

	cash, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{Name: "Cash", Type: domain.WalletTypeBasic, InitialBalanceMinor: 1_000_000, IncludeInTotal: true})
	if err != nil {
		t.Fatalf("create cash wallet: %v", err)
	}
	bank, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{Name: "Bank", Type: domain.WalletTypeBasic, InitialBalanceMinor: 2_000_000, IncludeInTotal: true})
	if err != nil {
		t.Fatalf("create bank wallet: %v", err)
	}
	incomeCat, err := svc.CreateCategory(ctx, domain.CreateCategoryCommand{Name: "Salary", Type: domain.CategoryTypeIncome})
	if err != nil {
		t.Fatalf("create income category: %v", err)
	}
	expenseCat, err := svc.CreateCategory(ctx, domain.CreateCategoryCommand{Name: "Food", Type: domain.CategoryTypeExpense})
	if err != nil {
		t.Fatalf("create expense category: %v", err)
	}

	if _, err := svc.CreateIncomeExpense(ctx, domain.CreateTransactionCommand{WalletID: cash.ID, CategoryID: &incomeCat.ID, Type: domain.TransactionTypeIncome, AmountMinor: 500_000, OccurredAt: occurred}); err != nil {
		t.Fatalf("create income: %v", err)
	}
	if _, err := svc.CreateIncomeExpense(ctx, domain.CreateTransactionCommand{WalletID: cash.ID, CategoryID: &expenseCat.ID, Type: domain.TransactionTypeExpense, AmountMinor: 100_000, OccurredAt: occurred}); err != nil {
		t.Fatalf("create expense: %v", err)
	}
	transferRows, err := svc.CreateTransfer(ctx, domain.CreateTransferCommand{FromWalletID: cash.ID, ToWalletID: bank.ID, AmountMinor: 200_000, OccurredAt: occurred})
	if err != nil {
		t.Fatalf("create transfer: %v", err)
	}
	if len(transferRows) != 2 || transferRows[0].TransferGroupID == nil || transferRows[1].TransferGroupID == nil || *transferRows[0].TransferGroupID != *transferRows[1].TransferGroupID {
		t.Fatalf("transfer rows not paired by transfer_group_id: %#v", transferRows)
	}

	asset, err := svc.CreateAsset(ctx, domain.CreateAssetCommand{AssetType: domain.AssetTypeGold, Symbol: "SJC", Name: "SJC Gold", Currency: "VND", Unit: "tael", PriceSource: "manual"})
	if err != nil {
		t.Fatalf("create asset: %v", err)
	}
	if _, err := svc.RecordAssetTransaction(ctx, domain.RecordAssetTransactionCommand{
		AssetID: asset.ID, WalletID: &bank.ID, Type: domain.AssetTransactionBuy, Quantity: "1.000000000000",
		UnitPriceMinor: 100_000, GrossAmountMinor: 100_000, NetAmountMinor: 100_000, Currency: "VND", OccurredAt: occurred,
	}); err != nil {
		t.Fatalf("record asset buy: %v", err)
	}
	if _, err := svc.UpdateAssetPrice(ctx, domain.UpdateAssetPriceCommand{AssetID: asset.ID, SellPriceMinor: 120_000, Currency: "VND", PriceType: domain.PriceTypeSell, Source: "manual", PricedAt: occurred}); err != nil {
		t.Fatalf("update asset price: %v", err)
	}

	debt, err := svc.CreateDebtOrLoan(ctx, domain.CreateDebtOrLoanCommand{Direction: domain.DebtDirectionIOwe, Counterparty: "Friend", PrincipalAmountMinor: 300_000, Currency: "VND"})
	if err != nil {
		t.Fatalf("create debt: %v", err)
	}
	if _, err := svc.RecordDebtPayment(ctx, domain.RecordDebtPaymentCommand{DebtLoanID: debt.ID, WalletID: cash.ID, AmountMinor: 50_000, PaidAt: occurred}); err != nil {
		t.Fatalf("record debt payment: %v", err)
	}

	report, err := svc.GetFinancialReport(ctx, domain.ReportQuery{PeriodStart: occurred.Add(-time.Hour), PeriodEnd: occurred.Add(24 * time.Hour), GroupBy: "day"})
	if err != nil {
		t.Fatalf("get report: %v", err)
	}
	if report.IncomeTotalMinor != 500_000 || report.ExpenseTotalMinor != 100_000 {
		t.Fatalf("ordinary report totals = income %d expense %d", report.IncomeTotalMinor, report.ExpenseTotalMinor)
	}
	if report.ExcludedTotalMinor != 100_000 {
		t.Fatalf("excluded investment total = %d, want 100000", report.ExcludedTotalMinor)
	}

	netWorth, err := svc.GetNetWorth(ctx, domain.NetWorthQuery{AsOf: occurred})
	if err != nil {
		t.Fatalf("get net worth: %v", err)
	}
	if netWorth.AssetValueMinor == 0 {
		t.Fatalf("expected asset value in net worth: %#v", netWorth)
	}
	if netWorth.LiabilityMinor < 250_000 {
		t.Fatalf("expected remaining debt liability in net worth: %#v", netWorth)
	}
}

func TestFinanceEpic1CriticalValidation(t *testing.T) {
	db := integrationDB(t)
	svc := service.NewFinanceService(db)
	ctx := context.Background()

	wallet, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{Name: "Cash", Type: domain.WalletTypeBasic, InitialBalanceMinor: 100_000, IncludeInTotal: true})
	if err != nil {
		t.Fatalf("create wallet: %v", err)
	}
	if _, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{Name: " Cash ", Type: domain.WalletTypeBasic}); err == nil {
		t.Fatal("expected duplicate wallet validation error")
	}
	if err := svc.ArchiveWallet(ctx, "", "", wallet.ID); err != nil {
		t.Fatalf("archive wallet: %v", err)
	}
	if _, err := svc.CreateIncomeExpense(ctx, domain.CreateTransactionCommand{WalletID: wallet.ID, Type: domain.TransactionTypeIncome, AmountMinor: 1}); err == nil {
		t.Fatal("expected archived wallet transaction validation error")
	}

	active, err := svc.CreateWallet(ctx, domain.CreateWalletCommand{Name: "Active", Type: domain.WalletTypeBasic, InitialBalanceMinor: 100_000, IncludeInTotal: true})
	if err != nil {
		t.Fatalf("create active wallet: %v", err)
	}
	debt, err := svc.CreateDebtOrLoan(ctx, domain.CreateDebtOrLoanCommand{Direction: domain.DebtDirectionOwedToMe, Counterparty: "Friend", PrincipalAmountMinor: 10_000})
	if err != nil {
		t.Fatalf("create debt: %v", err)
	}
	if _, err := svc.RecordDebtPayment(ctx, domain.RecordDebtPaymentCommand{DebtLoanID: debt.ID, WalletID: active.ID, AmountMinor: 20_000}); err == nil {
		t.Fatal("expected overpayment validation error")
	}
	if _, err := svc.GetFinancialReport(ctx, domain.ReportQuery{PeriodStart: time.Now(), PeriodEnd: time.Now().Add(-time.Hour)}); err == nil {
		t.Fatal("expected invalid report period validation error")
	}
}
