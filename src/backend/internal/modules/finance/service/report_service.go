package service

import (
	"context"

	appErrors "cortex/internal/core/errors"
	"cortex/internal/modules/finance/domain"
)

func (s *FinanceService) GetFinancialReport(ctx context.Context, query domain.ReportQuery) (*domain.FinancialReportDTO, error) {
	if !query.PeriodStart.IsZero() && !query.PeriodEnd.IsZero() && !query.PeriodStart.Before(query.PeriodEnd) {
		return nil, appErrors.NewValidationError("period_start must be before period_end")
	}
	ownerID := domain.NormalizeOwner(query.OwnerID)
	groupBy := defaultString(query.GroupBy, "none")
	dto := &domain.FinancialReportDTO{
		PeriodStart: query.PeriodStart,
		PeriodEnd:   query.PeriodEnd,
		GroupBy:     groupBy,
		ByCategory:  map[string]int64{},
		ByWallet:    map[string]int64{},
		ByPeriod:    map[string]int64{},
	}
	dbq := s.db.WithContext(ctx).Where("owner_id = ? AND deleted_at IS NULL", ownerID)
	dateColumn := "occurred_at"
	if query.UseCreatedAtAuditDate {
		dateColumn = "created_at"
	}
	if !query.PeriodStart.IsZero() {
		dbq = dbq.Where(dateColumn+" >= ?", query.PeriodStart)
	}
	if !query.PeriodEnd.IsZero() {
		dbq = dbq.Where(dateColumn+" < ?", query.PeriodEnd)
	}
	if query.WalletID != nil {
		dbq = dbq.Where("wallet_id = ?", *query.WalletID)
	}
	if query.CategoryID != nil {
		dbq = dbq.Where("category_id = ?", *query.CategoryID)
	}
	var rows []domain.Transaction
	if err := dbq.Find(&rows).Error; err != nil {
		return nil, err
	}
	for _, row := range rows {
		if row.ExcludeFromReport {
			dto.ExcludedTotalMinor += row.AmountMinor
			if !query.IncludeInvestment {
				continue
			}
		}
		switch row.Type {
		case domain.TransactionTypeIncome:
			dto.IncomeTotalMinor += row.AmountMinor
		case domain.TransactionTypeExpense:
			dto.ExpenseTotalMinor += row.AmountMinor
		case domain.TransactionTypeTransferIn:
			dto.TransferInTotalMinor += row.AmountMinor
		case domain.TransactionTypeTransferOut:
			dto.TransferOutTotalMinor += row.AmountMinor
		case domain.TransactionTypeInvestmentBuy, domain.TransactionTypeInvestmentSell:
			dto.InvestmentCashMovementTotalMinor += row.AmountMinor
		}
		dto.ByWallet[row.WalletID] += signedAmount(row)
		if row.CategoryID != nil {
			dto.ByCategory[*row.CategoryID] += signedAmount(row)
		}
		periodSource := row.OccurredAt
		if query.UseCreatedAtAuditDate {
			periodSource = row.CreatedAt
		}
		dto.ByPeriod[periodKey(periodSource, groupBy)] += signedAmount(row)
	}
	dto.NetCashflowMinor = dto.IncomeTotalMinor - dto.ExpenseTotalMinor
	return dto, nil
}

func (s *FinanceService) GetNetWorth(ctx context.Context, query domain.NetWorthQuery) (*domain.NetWorthDTO, error) {
	ownerID := domain.NormalizeOwner(query.OwnerID)
	dto := &domain.NetWorthDTO{AsOf: defaultTime(query.AsOf, s.now())}
	var wallets []domain.Wallet
	if err := s.db.WithContext(ctx).Where("owner_id = ? AND status = ? AND include_in_total = ?", ownerID, domain.WalletStatusActive, true).Find(&wallets).Error; err != nil {
		return nil, err
	}
	for _, wallet := range wallets {
		if wallet.Type == domain.WalletTypeCredit {
			dto.LiabilityMinor += abs64(wallet.CurrentBalanceMinor)
			continue
		}
		dto.CashTotalMinor += wallet.CurrentBalanceMinor
	}
	var holdings []domain.AssetHolding
	if err := s.db.WithContext(ctx).Where("owner_id = ?", ownerID).Find(&holdings).Error; err != nil {
		return nil, err
	}
	for _, holding := range holdings {
		dto.AssetValueMinor += holding.CurrentValueMinor
		dto.RealizedGainMinor += holding.RealizedGainMinor
		dto.UnrealizedGainMinor += holding.UnrealizedGainMinor
	}
	var debts []domain.DebtLoan
	if err := s.db.WithContext(ctx).Where("owner_id = ? AND status IN ?", ownerID, []domain.DebtStatus{domain.DebtStatusActive, domain.DebtStatusPartiallySettled}).Find(&debts).Error; err != nil {
		return nil, err
	}
	for _, debt := range debts {
		if debt.Direction == domain.DebtDirectionIOwe {
			dto.LiabilityMinor += debt.RemainingAmountMinor
		} else {
			dto.ReceivableMinor += debt.RemainingAmountMinor
		}
	}
	dto.NetWorthMinor = dto.CashTotalMinor + dto.AssetValueMinor + dto.ReceivableMinor - dto.LiabilityMinor
	return dto, nil
}
