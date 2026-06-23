package service

import (
	"context"
	"math/big"
	"time"

	"cortex/internal/modules/finance/domain"
	"gorm.io/gorm"
)

func (s *FinanceService) rebuildHolding(ctx context.Context, tx *gorm.DB, ownerID, assetID, actorID string) error {
	var assetTxs []domain.AssetTransaction
	if err := tx.WithContext(ctx).
		Where("owner_id = ? AND asset_id = ? AND deleted_at IS NULL", ownerID, assetID).
		Order("occurred_at ASC, created_at ASC, id ASC").
		Find(&assetTxs).Error; err != nil {
		return err
	}
	var quantityLabel string
	var totalCost, realizedGain int64
	for _, row := range assetTxs {
		switch row.TransactionType {
		case domain.AssetTransactionBuy, domain.AssetTransactionTransferIn:
			totalCost += row.NetAmountMinor
		case domain.AssetTransactionSell, domain.AssetTransactionTransferOut:
			realizedGain += row.NetAmountMinor - row.GrossAmountMinor
			if totalCost > row.NetAmountMinor {
				totalCost -= row.NetAmountMinor
			} else {
				totalCost = 0
			}
		case domain.AssetTransactionDividend:
			realizedGain += row.NetAmountMinor
		}
		quantityLabel = row.Quantity
	}
	priceMinor, pricedAt, err := s.latestAssetPrice(ctx, tx, ownerID, assetID)
	if err != nil {
		return err
	}
	currentValue := totalCost
	if priceMinor > 0 {
		if qRat, err := parsePositiveQuantity(quantityLabel); err == nil {
			pRat := new(big.Rat).SetInt64(priceMinor)
			valRat := new(big.Rat).Mul(qRat, pRat)
			currentValue = new(big.Int).Div(valRat.Num(), valRat.Denom()).Int64()
		} else {
			currentValue = priceMinor
		}
	}
	now := s.now()
	holding := domain.AssetHolding{
		ID:                  domain.NewID("ahl"),
		OwnerID:             ownerID,
		AssetID:             assetID,
		Quantity:            defaultString(quantityLabel, "0"),
		AverageCostMinor:    totalCost,
		TotalCostMinor:      totalCost,
		RealizedGainMinor:   realizedGain,
		CurrentPriceMinor:   priceMinor,
		CurrentValueMinor:   currentValue,
		UnrealizedGainMinor: currentValue - totalCost,
		LastPricedAt:        pricedAt,
		AuditFields:         domain.NewAudit(actorID, now),
	}
	var existing domain.AssetHolding
	err = tx.WithContext(ctx).Where("owner_id = ? AND asset_id = ?", ownerID, assetID).First(&existing).Error
	if err == nil {
		holding.ID = existing.ID
		holding.CreatedAt = existing.CreatedAt
		holding.CreatedBy = existing.CreatedBy
		holding.UpdatedAt = now
		holding.UpdatedBy = domain.NormalizeActor(actorID)
		return tx.Save(&holding).Error
	}
	if err != nil && err != gorm.ErrRecordNotFound {
		return err
	}
	return tx.Create(&holding).Error
}

func (s *FinanceService) latestAssetPrice(ctx context.Context, tx *gorm.DB, ownerID, assetID string) (int64, *time.Time, error) {
	var price domain.AssetPrice
	err := tx.WithContext(ctx).Where("owner_id = ? AND asset_id = ?", ownerID, assetID).Order("priced_at DESC, created_at DESC").First(&price).Error
	if err == gorm.ErrRecordNotFound {
		return 0, nil, nil
	}
	if err != nil {
		return 0, nil, err
	}
	selected := price.PriceMinor
	if price.SellPriceMinor > 0 {
		selected = price.SellPriceMinor
	}
	return selected, &price.PricedAt, nil
}
