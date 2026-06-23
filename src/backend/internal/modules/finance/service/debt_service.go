package service

import (
	"context"
	"strings"

	appErrors "cortex/internal/core/errors"
	"cortex/internal/modules/finance/domain"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

func (s *FinanceService) CreateDebtOrLoan(ctx context.Context, cmd domain.CreateDebtOrLoanCommand) (*domain.DebtLoan, error) {
	if cmd.Direction != domain.DebtDirectionIOwe && cmd.Direction != domain.DebtDirectionOwedToMe {
		return nil, appErrors.NewValidationError("invalid debt direction")
	}
	if err := domain.RequirePositiveMinor("principal_amount_minor", cmd.PrincipalAmountMinor); err != nil {
		return nil, err
	}
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	now := s.now()
	debt := &domain.DebtLoan{
		ID:                   domain.NewID("debt"),
		OwnerID:              ownerID,
		Direction:            cmd.Direction,
		Counterparty:         strings.TrimSpace(cmd.Counterparty),
		PrincipalAmountMinor: cmd.PrincipalAmountMinor,
		RemainingAmountMinor: cmd.PrincipalAmountMinor,
		Currency:             domain.NormalizeCurrency(cmd.Currency),
		DueDate:              cmd.DueDate,
		Status:               domain.DebtStatusActive,
		Note:                 cmd.Note,
		AuditFields:          domain.NewAudit(actorID, now),
	}
	if debt.Counterparty == "" {
		return nil, appErrors.NewValidationError("counterparty is required")
	}
	if err := s.db.WithContext(ctx).Create(debt).Error; err != nil {
		return nil, err
	}
	return debt, nil
}

func (s *FinanceService) UpdateDebtOrLoan(ctx context.Context, cmd domain.UpdateDebtOrLoanCommand) (*domain.DebtLoan, error) {
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	var debt domain.DebtLoan
	if err := s.firstOwned(ctx, ownerID, cmd.ID, &debt); err != nil {
		return nil, err
	}
	if cmd.Counterparty != nil {
		counterparty := strings.TrimSpace(*cmd.Counterparty)
		if counterparty == "" {
			return nil, appErrors.NewValidationError("counterparty is required")
		}
		debt.Counterparty = counterparty
	}
	if cmd.DueDate != nil {
		debt.DueDate = cmd.DueDate
	}
	if cmd.Status != nil {
		if !validDebtStatus(*cmd.Status) {
			return nil, appErrors.NewValidationError("invalid debt status")
		}
		debt.Status = *cmd.Status
	}
	if cmd.Note != nil {
		debt.Note = *cmd.Note
	}
	domain.Touch(&debt.AuditFields, actorID, s.now())
	if err := s.db.WithContext(ctx).Save(&debt).Error; err != nil {
		return nil, err
	}
	return &debt, nil
}

func (s *FinanceService) RecordDebtPayment(ctx context.Context, cmd domain.RecordDebtPaymentCommand) (*domain.DebtPayment, error) {
	if err := domain.RequirePositiveMinor("amount_minor", cmd.AmountMinor); err != nil {
		return nil, err
	}
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	var payment domain.DebtPayment
	err := s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		var debt domain.DebtLoan
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).Where("owner_id = ? AND id = ?", ownerID, cmd.DebtLoanID).First(&debt).Error; err != nil {
			return mapGormNotFound(err, "debt_loan")
		}
		if debt.Status == domain.DebtStatusSettled || debt.Status == domain.DebtStatusArchived || debt.Status == domain.DebtStatusForgiven {
			return appErrors.NewValidationError("debt is not active for settlement")
		}
		if cmd.AmountMinor > debt.RemainingAmountMinor {
			return appErrors.NewValidationError("payment exceeds remaining amount")
		}
		wallet, err := s.lockWallet(ctx, tx, ownerID, cmd.WalletID)
		if err != nil {
			return err
		}
		if wallet.Status != domain.WalletStatusActive {
			return appErrors.NewValidationError("archived wallet cannot settle debt")
		}
		if wallet.Currency != debt.Currency {
			return appErrors.NewValidationError("debt payment currency must match wallet currency")
		}
		txType, dir := domain.TransactionTypeDebtPayment, domain.DirectionDebit
		if debt.Direction == domain.DebtDirectionOwedToMe {
			txType, dir = domain.TransactionTypeDebtCollection, domain.DirectionCredit
			wallet.CurrentBalanceMinor += cmd.AmountMinor
		} else {
			wallet.CurrentBalanceMinor -= cmd.AmountMinor
		}
		if err := tx.Save(wallet).Error; err != nil {
			return err
		}
		cash := s.newTransaction(ownerID, actorID, cmd.WalletID, nil, txType, dir, cmd.AmountMinor, debt.Currency, cmd.PaidAt, cmd.Note)
		if err := tx.Create(&cash).Error; err != nil {
			return err
		}
		debt.RemainingAmountMinor -= cmd.AmountMinor
		if debt.RemainingAmountMinor == 0 {
			debt.Status = domain.DebtStatusSettled
		} else {
			debt.Status = domain.DebtStatusPartiallySettled
		}
		domain.Touch(&debt.AuditFields, actorID, s.now())
		if err := tx.Save(&debt).Error; err != nil {
			return err
		}
		now := s.now()
		payment = domain.DebtPayment{
			ID:                domain.NewID("dpm"),
			OwnerID:           ownerID,
			DebtLoanID:        debt.ID,
			WalletID:          wallet.ID,
			CashTransactionID: &cash.ID,
			AmountMinor:       cmd.AmountMinor,
			PaidAt:            defaultTime(cmd.PaidAt, now),
			Note:              cmd.Note,
			AuditFields:       domain.NewAudit(actorID, now),
		}
		return tx.Create(&payment).Error
	})
	return &payment, err
}

func (s *FinanceService) GetDebtStatus(ctx context.Context, query domain.DebtStatusQuery) (*domain.DebtStatusDTO, error) {
	ownerID := domain.NormalizeOwner(query.OwnerID)
	var debt domain.DebtLoan
	if err := s.firstOwned(ctx, ownerID, query.ID, &debt); err != nil {
		return nil, err
	}
	return &domain.DebtStatusDTO{DebtLoan: debt, PaidOrCollectedMinor: debt.PrincipalAmountMinor - debt.RemainingAmountMinor}, nil
}

func (s *FinanceService) ListDebts(ctx context.Context, query domain.ListDebtsQuery) ([]domain.DebtLoan, error) {
	dbq := s.db.WithContext(ctx).Where("owner_id = ?", domain.NormalizeOwner(query.OwnerID))
	if query.Direction != nil {
		dbq = dbq.Where("direction = ?", *query.Direction)
	}
	if query.Status != nil {
		dbq = dbq.Where("status = ?", *query.Status)
	}
	if query.DueBefore != nil {
		dbq = dbq.Where("due_date <= ?", *query.DueBefore)
	}
	var debts []domain.DebtLoan
	err := dbq.Order("due_date ASC NULLS LAST, created_at DESC").Find(&debts).Error
	return debts, err
}
