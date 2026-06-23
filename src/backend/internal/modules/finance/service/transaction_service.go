package service

import (
	"context"

	appErrors "cortex/internal/core/errors"
	"cortex/internal/modules/finance/domain"
	"gorm.io/gorm"
)

func (s *FinanceService) CreateIncomeExpense(ctx context.Context, cmd domain.CreateTransactionCommand) (*domain.Transaction, error) {
	if cmd.Type != domain.TransactionTypeIncome && cmd.Type != domain.TransactionTypeExpense {
		return nil, appErrors.NewValidationError("transaction type must be income or expense")
	}
	if err := domain.RequirePositiveMinor("amount_minor", cmd.AmountMinor); err != nil {
		return nil, err
	}
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	var out domain.Transaction
	err := s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		wallet, err := s.lockWallet(ctx, tx, ownerID, cmd.WalletID)
		if err != nil {
			return err
		}
		if wallet.Status != domain.WalletStatusActive {
			return appErrors.NewValidationError("archived wallet cannot be used for new transactions")
		}
		currency := domain.NormalizeCurrency(cmd.Currency)
		if currency != wallet.Currency {
			return appErrors.NewValidationError("transaction currency must match wallet currency")
		}
		if cmd.CategoryID != nil {
			category, err := s.getCategory(ctx, tx, ownerID, *cmd.CategoryID)
			if err != nil {
				return err
			}
			if (cmd.Type == domain.TransactionTypeIncome && category.Type != domain.CategoryTypeIncome) ||
				(cmd.Type == domain.TransactionTypeExpense && category.Type != domain.CategoryTypeExpense) {
				return appErrors.NewValidationError("category type must match transaction type")
			}
		}
		direction := domain.DirectionCredit
		if cmd.Type == domain.TransactionTypeExpense {
			direction = domain.DirectionDebit
			wallet.CurrentBalanceMinor -= cmd.AmountMinor
		} else {
			wallet.CurrentBalanceMinor += cmd.AmountMinor
		}
		if err := tx.Save(wallet).Error; err != nil {
			return err
		}
		out = s.newTransaction(ownerID, actorID, cmd.WalletID, cmd.CategoryID, cmd.Type, direction, cmd.AmountMinor, currency, cmd.OccurredAt, cmd.Note)
		out.WithPerson = cmd.WithPerson
		out.Location = cmd.Location
		out.EventID = cmd.EventID
		out.ExcludeFromReport = cmd.ExcludeFromReport
		return tx.Create(&out).Error
	})
	return &out, err
}

func (s *FinanceService) CreateTransfer(ctx context.Context, cmd domain.CreateTransferCommand) ([]domain.Transaction, error) {
	if cmd.FromWalletID == cmd.ToWalletID {
		return nil, appErrors.NewValidationError("source and destination wallets must differ")
	}
	if err := domain.RequirePositiveMinor("amount_minor", cmd.AmountMinor); err != nil {
		return nil, err
	}
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	groupID := domain.NewID("trg")
	var rows []domain.Transaction
	err := s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		from, err := s.lockWallet(ctx, tx, ownerID, cmd.FromWalletID)
		if err != nil {
			return err
		}
		to, err := s.lockWallet(ctx, tx, ownerID, cmd.ToWalletID)
		if err != nil {
			return err
		}
		if from.Status != domain.WalletStatusActive || to.Status != domain.WalletStatusActive {
			return appErrors.NewValidationError("archived wallets cannot be used for transfer")
		}
		currency := domain.NormalizeCurrency(cmd.Currency)
		if from.Currency != to.Currency || currency != from.Currency {
			return appErrors.NewValidationError("transfer currency must match both wallets")
		}
		from.CurrentBalanceMinor -= cmd.AmountMinor
		to.CurrentBalanceMinor += cmd.AmountMinor
		if err := tx.Save(from).Error; err != nil {
			return err
		}
		if err := tx.Save(to).Error; err != nil {
			return err
		}
		out := s.newTransaction(ownerID, actorID, cmd.FromWalletID, nil, domain.TransactionTypeTransferOut, domain.DirectionDebit, cmd.AmountMinor, currency, cmd.OccurredAt, cmd.Note)
		in := s.newTransaction(ownerID, actorID, cmd.ToWalletID, nil, domain.TransactionTypeTransferIn, domain.DirectionCredit, cmd.AmountMinor, currency, cmd.OccurredAt, cmd.Note)
		out.TransferGroupID = &groupID
		in.TransferGroupID = &groupID
		rows = []domain.Transaction{out, in}
		return tx.Create(&rows).Error
	})
	return rows, err
}
