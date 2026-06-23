package service

import (
	"time"

	"cortex/internal/modules/finance/domain"
	"gorm.io/gorm"
)

type FinanceService struct {
	db  *gorm.DB
	now func() time.Time
}

func NewFinanceService(db *gorm.DB) *FinanceService {
	return &FinanceService{db: db, now: func() time.Time { return time.Now().UTC() }}
}

func (s *FinanceService) AutoMigrate() error {
	return s.db.AutoMigrate(
		&domain.Wallet{},
		&domain.Category{},
		&domain.Transaction{},
		&domain.Asset{},
		&domain.AssetTransaction{},
		&domain.AssetHolding{},
		&domain.AssetPrice{},
		&domain.DebtLoan{},
		&domain.DebtPayment{},
	)
}
