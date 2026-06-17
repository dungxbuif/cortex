package service

import (
	"context"
	"strings"

	appErrors "cortex/internal/core/errors"
	"cortex/internal/modules/finance/domain"
	"gorm.io/gorm"
)

func (s *FinanceService) CreateAsset(ctx context.Context, cmd domain.CreateAssetCommand) (*domain.Asset, error) {
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	symbol := strings.ToUpper(strings.TrimSpace(cmd.Symbol))
	name := strings.TrimSpace(cmd.Name)
	if symbol == "" || name == "" {
		return nil, appErrors.NewValidationError("asset symbol and name are required")
	}
	if !validAssetType(cmd.AssetType) {
		return nil, appErrors.NewValidationError("invalid asset type")
	}
	currency := domain.NormalizeCurrency(cmd.Currency)
	var count int64
	if err := s.db.WithContext(ctx).Model(&domain.Asset{}).
		Where("owner_id = ? AND asset_type = ? AND symbol = ? AND currency = ?", ownerID, cmd.AssetType, symbol, currency).
		Count(&count).Error; err != nil {
		return nil, err
	}
	if count > 0 {
		return nil, appErrors.NewValidationError("asset key must be unique")
	}
	now := s.now()
	asset := &domain.Asset{
		ID:          domain.NewID("ast"),
		OwnerID:     ownerID,
		AssetType:   cmd.AssetType,
		Symbol:      symbol,
		Name:        name,
		Currency:    currency,
		Unit:        defaultString(cmd.Unit, "unit"),
		PriceSource: defaultString(cmd.PriceSource, "manual"),
		IsActive:    true,
		AuditFields: domain.NewAudit(actorID, now),
	}
	if err := s.db.WithContext(ctx).Create(asset).Error; err != nil {
		return nil, err
	}
	return asset, nil
}

func (s *FinanceService) RecordAssetTransaction(ctx context.Context, cmd domain.RecordAssetTransactionCommand) (*domain.AssetTransaction, error) {
	if _, err := parsePositiveQuantity(cmd.Quantity); err != nil {
		return nil, err
	}
	if cmd.NetAmountMinor < 0 || cmd.GrossAmountMinor < 0 || cmd.FeeMinor < 0 || cmd.TaxMinor < 0 {
		return nil, appErrors.NewValidationError("asset money fields cannot be negative")
	}
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	var row domain.AssetTransaction
	err := s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var asset domain.Asset
		if err := s.firstOwnedTx(ctx, tx, ownerID, cmd.AssetID, &asset); err != nil {
			return err
		}
		if !asset.IsActive {
			return appErrors.NewValidationError("inactive asset cannot receive new transactions")
		}
		currency := domain.NormalizeCurrency(cmd.Currency)
		if currency != asset.Currency {
			return appErrors.NewValidationError("asset transaction currency must match asset currency")
		}
		var linkedCashID *string
		if requiresAssetCashMovement(cmd.Type) && cmd.WalletID == nil {
			return appErrors.NewValidationError("cash-affecting asset transaction requires wallet")
		}
		if cmd.WalletID != nil && requiresAssetCashMovement(cmd.Type) {
			wallet, err := s.lockWallet(ctx, tx, ownerID, *cmd.WalletID)
			if err != nil {
				return err
			}
			if wallet.Status != domain.WalletStatusActive {
				return appErrors.NewValidationError("archived wallet cannot fund asset transaction")
			}
			if wallet.Currency != currency {
				return appErrors.NewValidationError("asset transaction currency must match wallet currency")
			}
			txType, dir := domain.TransactionTypeInvestmentBuy, domain.DirectionDebit
			if cmd.Type == domain.AssetTransactionSell || cmd.Type == domain.AssetTransactionDividend {
				txType, dir = domain.TransactionTypeInvestmentSell, domain.DirectionCredit
				wallet.CurrentBalanceMinor += cmd.NetAmountMinor
			} else {
				wallet.CurrentBalanceMinor -= cmd.NetAmountMinor
			}
			if err := tx.Save(wallet).Error; err != nil {
				return err
			}
			cash := s.newTransaction(ownerID, actorID, *cmd.WalletID, nil, txType, dir, cmd.NetAmountMinor, currency, cmd.OccurredAt, cmd.Note)
			cash.ExcludeFromReport = true
			if err := tx.Create(&cash).Error; err != nil {
				return err
			}
			linkedCashID = &cash.ID
		}
		now := s.now()
		row = domain.AssetTransaction{
			ID:                      domain.NewID("atx"),
			OwnerID:                 ownerID,
			AssetID:                 cmd.AssetID,
			WalletID:                cmd.WalletID,
			LinkedCashTransactionID: linkedCashID,
			TransactionType:         cmd.Type,
			Quantity:                cmd.Quantity,
			UnitPriceMinor:          cmd.UnitPriceMinor,
			GrossAmountMinor:        cmd.GrossAmountMinor,
			FeeMinor:                cmd.FeeMinor,
			TaxMinor:                cmd.TaxMinor,
			NetAmountMinor:          cmd.NetAmountMinor,
			Currency:                currency,
			OccurredAt:              defaultTime(cmd.OccurredAt, now),
			Note:                    cmd.Note,
			AuditFields:             domain.NewAudit(actorID, now),
		}
		if err := tx.Create(&row).Error; err != nil {
			return err
		}
		return s.rebuildHolding(ctx, tx, ownerID, cmd.AssetID, actorID)
	})
	return &row, err
}

func (s *FinanceService) UpdateAssetPrice(ctx context.Context, cmd domain.UpdateAssetPriceCommand) (*domain.AssetPrice, error) {
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	if cmd.PriceMinor <= 0 && cmd.BuyPriceMinor <= 0 && cmd.SellPriceMinor <= 0 {
		return nil, appErrors.NewValidationError("at least one price field must be positive")
	}
	if !validPriceType(cmd.PriceType) {
		return nil, appErrors.NewValidationError("invalid price type")
	}
	var asset domain.Asset
	if err := s.firstOwned(ctx, ownerID, cmd.AssetID, &asset); err != nil {
		return nil, err
	}
	currency := domain.NormalizeCurrency(cmd.Currency)
	if currency != asset.Currency {
		return nil, appErrors.NewValidationError("asset price currency must match asset currency")
	}
	now := s.now()
	price := &domain.AssetPrice{
		ID:             domain.NewID("apr"),
		OwnerID:        ownerID,
		AssetID:        cmd.AssetID,
		PriceMinor:     cmd.PriceMinor,
		BuyPriceMinor:  cmd.BuyPriceMinor,
		SellPriceMinor: cmd.SellPriceMinor,
		Currency:       currency,
		PriceType:      cmd.PriceType,
		Source:         defaultString(cmd.Source, "manual"),
		PricedAt:       defaultTime(cmd.PricedAt, now),
		AuditFields:    domain.NewAudit(actorID, now),
	}
	if err := s.db.WithContext(ctx).Create(price).Error; err != nil {
		return nil, err
	}
	if err := s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		return s.rebuildHolding(ctx, tx, ownerID, cmd.AssetID, actorID)
	}); err != nil {
		return nil, err
	}
	return price, nil
}
