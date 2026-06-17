package tests

import (
	"context"
	"testing"
	"time"

	"cortex/internal/modules/finance/domain"
	"cortex/internal/modules/finance/service"
)

func TestAssetValuationEdgeCases(t *testing.T) {
	db := integrationDB(t)
	svc := service.NewFinanceService(db)
	ctx := context.Background()

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
		Symbol:      "AAPL",
		Name:        "Apple Inc.",
		Currency:    "USD",
		Unit:        "share",
		PriceSource: "manual",
	})
	if err != nil {
		t.Fatalf("create asset: %v", err)
	}

	now := time.Now()
	_, err = svc.RecordAssetTransaction(ctx, domain.RecordAssetTransactionCommand{
		AssetID:          asset.ID,
		WalletID:         &bank.ID,
		Type:             domain.AssetTransactionBuy,
		Quantity:         "10.000000000000",
		UnitPriceMinor:   150_00, // $150
		GrossAmountMinor: 1_500_00,
		FeeMinor:         0,
		TaxMinor:         0,
		NetAmountMinor:   1_500_00, // Costs $1500
		Currency:         "USD",
		OccurredAt:       now.Add(-time.Hour),
	})
	if err != nil {
		t.Fatalf("record asset buy: %v", err)
	}

	// Verify Holding directly via GORM
	var holding domain.AssetHolding
	db.First(&holding, "asset_id = ?", asset.ID)
	if holding.Quantity != "10.000000000000" {
		t.Errorf("expected 10 shares, got %s", holding.Quantity)
	}

	// 2. Update Asset Price twice. The latest price should be used.
	_, err = svc.UpdateAssetPrice(ctx, domain.UpdateAssetPriceCommand{
		AssetID:        asset.ID,
		PriceMinor:     160_00,
		Currency:       "USD",
		PriceType:      domain.PriceTypeClose,
		Source:         "manual",
		PricedAt:       now.Add(-30 * time.Minute),
	})
	if err != nil {
		t.Fatalf("update asset price 1: %v", err)
	}

	_, err = svc.UpdateAssetPrice(ctx, domain.UpdateAssetPriceCommand{
		AssetID:        asset.ID,
		PriceMinor:     170_00,
		Currency:       "USD",
		PriceType:      domain.PriceTypeClose,
		Source:         "manual",
		PricedAt:       now, 
	})
	if err != nil {
		t.Fatalf("update asset price 2: %v", err)
	}

	// Verify NetWorth incorporates the $170 price (10 shares * 170 = $1700)
	netWorth, err := svc.GetNetWorth(ctx, domain.NetWorthQuery{AsOf: time.Now().Add(time.Hour)})
	if err != nil {
		t.Fatalf("get net worth: %v", err)
	}

	expectedAssetValue := int64(1_700_00)
	if netWorth.AssetValueMinor != expectedAssetValue {
		t.Errorf("expected asset value %d in net worth, got %d", expectedAssetValue, netWorth.AssetValueMinor)
	}
}
