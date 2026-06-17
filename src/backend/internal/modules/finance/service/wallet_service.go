package service

import (
	"context"
	"strings"

	appErrors "cortex/internal/core/errors"
	"cortex/internal/modules/finance/domain"
)

func (s *FinanceService) CreateWallet(ctx context.Context, cmd domain.CreateWalletCommand) (*domain.Wallet, error) {
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	name := strings.TrimSpace(cmd.Name)
	if name == "" {
		return nil, appErrors.NewValidationError("wallet name is required")
	}
	if cmd.Type == "" {
		cmd.Type = domain.WalletTypeBasic
	}
	if !validWalletType(cmd.Type) {
		return nil, appErrors.NewValidationError("invalid wallet type")
	}
	if cmd.Type != domain.WalletTypeCredit && cmd.InitialBalanceMinor < 0 {
		return nil, appErrors.NewValidationError("initial_balance_minor cannot be negative for cash wallets")
	}
	var count int64
	if err := s.db.WithContext(ctx).Model(&domain.Wallet{}).
		Where("owner_id = ? AND lower(name) = lower(?) AND status = ?", ownerID, name, domain.WalletStatusActive).
		Count(&count).Error; err != nil {
		return nil, err
	}
	if count > 0 {
		return nil, appErrors.NewValidationError("active wallet name must be unique")
	}
	now := s.now()
	wallet := &domain.Wallet{
		ID:                  domain.NewID("wal"),
		OwnerID:             ownerID,
		Name:                name,
		Type:                cmd.Type,
		Currency:            domain.NormalizeCurrency(cmd.Currency),
		InitialBalanceMinor: cmd.InitialBalanceMinor,
		CurrentBalanceMinor: cmd.InitialBalanceMinor,
		IncludeInTotal:      cmd.IncludeInTotal,
		Status:              domain.WalletStatusActive,
		AuditFields:         domain.NewAudit(actorID, now),
	}
	if err := s.db.WithContext(ctx).Create(wallet).Error; err != nil {
		return nil, err
	}
	return wallet, nil
}

func (s *FinanceService) UpdateWallet(ctx context.Context, cmd domain.UpdateWalletCommand) (*domain.Wallet, error) {
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	var wallet domain.Wallet
	if err := s.firstOwned(ctx, ownerID, cmd.ID, &wallet); err != nil {
		return nil, err
	}
	if cmd.Name != nil {
		name := strings.TrimSpace(*cmd.Name)
		if name == "" {
			return nil, appErrors.NewValidationError("wallet name is required")
		}
		var count int64
		if err := s.db.WithContext(ctx).Model(&domain.Wallet{}).
			Where("owner_id = ? AND id <> ? AND lower(name) = lower(?) AND status = ?", ownerID, cmd.ID, name, domain.WalletStatusActive).
			Count(&count).Error; err != nil {
			return nil, err
		}
		if count > 0 {
			return nil, appErrors.NewValidationError("active wallet name must be unique")
		}
		wallet.Name = name
	}
	if cmd.IncludeInTotal != nil {
		wallet.IncludeInTotal = *cmd.IncludeInTotal
	}
	domain.Touch(&wallet.AuditFields, actorID, s.now())
	if err := s.db.WithContext(ctx).Save(&wallet).Error; err != nil {
		return nil, err
	}
	return &wallet, nil
}

func (s *FinanceService) ArchiveWallet(ctx context.Context, ownerID, actorID, id string) error {
	ownerID, actorID = domain.NormalizeOwner(ownerID), domain.NormalizeActor(actorID)
	var wallet domain.Wallet
	if err := s.firstOwned(ctx, ownerID, id, &wallet); err != nil {
		return err
	}
	now := s.now()
	wallet.Status = domain.WalletStatusArchived
	wallet.ArchivedAt = &now
	domain.Touch(&wallet.AuditFields, actorID, now)
	return s.db.WithContext(ctx).Save(&wallet).Error
}

func (s *FinanceService) ListWallets(ctx context.Context, ownerID string) ([]domain.Wallet, error) {
	var wallets []domain.Wallet
	err := s.db.WithContext(ctx).Where("owner_id = ?", domain.NormalizeOwner(ownerID)).Order("name ASC").Find(&wallets).Error
	return wallets, err
}
