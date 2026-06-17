package service

import (
	"context"
	"fmt"
	"math/big"
	"strings"
	"time"

	appErrors "cortex/internal/core/errors"
	"cortex/internal/modules/finance/domain"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

func (s *FinanceService) newTransaction(ownerID, actorID, walletID string, categoryID *string, txType domain.TransactionType, direction domain.TransactionDirection, amount int64, currency string, occurredAt time.Time, note string) domain.Transaction {
	now := s.now()
	return domain.Transaction{
		ID:          domain.NewID("txn"),
		OwnerID:     ownerID,
		WalletID:    walletID,
		CategoryID:  categoryID,
		Type:        txType,
		Direction:   direction,
		AmountMinor: amount,
		Currency:    domain.NormalizeCurrency(currency),
		OccurredAt:  defaultTime(occurredAt, now),
		Note:        note,
		AuditFields: domain.NewAudit(actorID, now),
	}
}

func (s *FinanceService) lockWallet(ctx context.Context, tx *gorm.DB, ownerID, walletID string) (*domain.Wallet, error) {
	var wallet domain.Wallet
	if err := tx.WithContext(ctx).Clauses(clause.Locking{Strength: "UPDATE"}).Where("owner_id = ? AND id = ?", ownerID, walletID).First(&wallet).Error; err != nil {
		return nil, mapGormNotFound(err, "wallet")
	}
	return &wallet, nil
}

func (s *FinanceService) getCategory(ctx context.Context, tx *gorm.DB, ownerID, categoryID string) (*domain.Category, error) {
	var category domain.Category
	if err := tx.WithContext(ctx).Where("owner_id = ? AND id = ?", ownerID, categoryID).First(&category).Error; err != nil {
		return nil, mapGormNotFound(err, "category")
	}
	return &category, nil
}

func (s *FinanceService) firstOwned(ctx context.Context, ownerID, id string, dest interface{}) error {
	return mapGormNotFound(s.db.WithContext(ctx).Where("owner_id = ? AND id = ?", ownerID, id).First(dest).Error, "resource")
}

func (s *FinanceService) firstOwnedTx(ctx context.Context, tx *gorm.DB, ownerID, id string, dest interface{}) error {
	return mapGormNotFound(tx.WithContext(ctx).Where("owner_id = ? AND id = ?", ownerID, id).First(dest).Error, "resource")
}

func mapGormNotFound(err error, resource string) error {
	if err == nil {
		return nil
	}
	if err == gorm.ErrRecordNotFound {
		return appErrors.NewNotFoundError(resource)
	}
	return err
}

func validWalletType(value domain.WalletType) bool {
	switch value {
	case domain.WalletTypeBasic, domain.WalletTypeGoal, domain.WalletTypeCredit, domain.WalletTypeLinked:
		return true
	default:
		return false
	}
}

func validAssetType(value domain.AssetType) bool {
	switch value {
	case domain.AssetTypeGold, domain.AssetTypeStock, domain.AssetTypeFund, domain.AssetTypeCrypto, domain.AssetTypeSavingDeposit, domain.AssetTypeCashEquivalent, domain.AssetTypeOther:
		return true
	default:
		return false
	}
}

func validPriceType(value domain.AssetPriceType) bool {
	switch value {
	case domain.PriceTypeBuy, domain.PriceTypeSell, domain.PriceTypeClose, domain.PriceTypeLast, domain.PriceTypeManual, domain.PriceTypeEstimated:
		return true
	default:
		return false
	}
}

func validDebtStatus(value domain.DebtStatus) bool {
	switch value {
	case domain.DebtStatusActive, domain.DebtStatusPartiallySettled, domain.DebtStatusSettled, domain.DebtStatusForgiven, domain.DebtStatusArchived:
		return true
	default:
		return false
	}
}

func requiresAssetCashMovement(value domain.AssetTransactionType) bool {
	switch value {
	case domain.AssetTransactionBuy, domain.AssetTransactionSell, domain.AssetTransactionDividend:
		return true
	default:
		return false
	}
}

func parsePositiveQuantity(value string) (*big.Rat, error) {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return nil, appErrors.NewValidationError("quantity is required")
	}
	q, ok := new(big.Rat).SetString(trimmed)
	if !ok {
		return nil, appErrors.NewValidationError("quantity must be numeric")
	}
	if q.Sign() <= 0 {
		return nil, appErrors.NewValidationError("quantity must be positive")
	}
	return q, nil
}

func defaultString(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return strings.TrimSpace(value)
}

func defaultTime(value time.Time, fallback time.Time) time.Time {
	if value.IsZero() {
		return fallback
	}
	return value
}

func signedAmount(row domain.Transaction) int64 {
	if row.Direction == domain.DirectionDebit {
		return -row.AmountMinor
	}
	return row.AmountMinor
}

func periodKey(t time.Time, groupBy string) string {
	switch groupBy {
	case "day":
		return t.Format("2006-01-02")
	case "month":
		return t.Format("2006-01")
	default:
		return "all"
	}
}

func abs64(v int64) int64 {
	if v < 0 {
		return -v
	}
	return v
}

func FormatOwnerScopedID(ownerID, id string) string {
	return fmt.Sprintf("%s/%s", domain.NormalizeOwner(ownerID), id)
}
