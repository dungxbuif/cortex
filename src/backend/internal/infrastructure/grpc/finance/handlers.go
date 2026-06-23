package finance

import (
	"context"
	"time"

	"cortex/internal/infrastructure/grpc/pb"
	"cortex/internal/modules/finance/domain"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type FinanceService interface {
	ListWallets(ctx context.Context, ownerID string) ([]domain.Wallet, error)
	ListCategories(ctx context.Context, ownerID string) ([]domain.Category, error)
	GetFinancialReport(ctx context.Context, query domain.ReportQuery) (*domain.FinancialReportDTO, error)
	GetNetWorth(ctx context.Context, query domain.NetWorthQuery) (*domain.NetWorthDTO, error)
}

type FinanceServicer struct {
	pb.UnimplementedFinanceServiceServer
	Service FinanceService
}

func (s FinanceServicer) HealthCheck(ctx context.Context, req *pb.HealthCheckRequest) (*pb.HealthCheckResponse, error) {
	return &pb.HealthCheckResponse{Status: "ok"}, nil
}

func (s FinanceServicer) ListWallets(ctx context.Context, req *pb.ListWalletsRequest) (*pb.ListWalletsResponse, error) {
	if s.Service == nil {
		return nil, status.Error(codes.FailedPrecondition, "finance service is not wired")
	}
	wallets, err := s.Service.ListWallets(ctx, req.GetOwnerId())
	if err != nil {
		return nil, err
	}

	records := make([]*pb.WalletRecord, 0, len(wallets))
	for _, w := range wallets {
		records = append(records, &pb.WalletRecord{
			Id:                  w.ID,
			OwnerId:             w.OwnerID,
			Name:                w.Name,
			Type:                string(w.Type),
			Currency:            w.Currency,
			InitialBalanceMinor: w.InitialBalanceMinor,
			CurrentBalanceMinor: w.CurrentBalanceMinor,
			IncludeInTotal:      w.IncludeInTotal,
			Status:              string(w.Status),
			CreatedAt:           w.CreatedAt.Format(time.RFC3339),
			UpdatedAt:           w.UpdatedAt.Format(time.RFC3339),
		})
	}

	return &pb.ListWalletsResponse{Wallets: records}, nil
}

func (s FinanceServicer) ListCategories(ctx context.Context, req *pb.ListCategoriesRequest) (*pb.ListCategoriesResponse, error) {
	if s.Service == nil {
		return nil, status.Error(codes.FailedPrecondition, "finance service is not wired")
	}
	categories, err := s.Service.ListCategories(ctx, req.GetOwnerId())
	if err != nil {
		return nil, err
	}

	records := make([]*pb.CategoryRecord, 0, len(categories))
	for _, c := range categories {
		records = append(records, &pb.CategoryRecord{
			Id:        c.ID,
			OwnerId:   c.OwnerID,
			ParentId:  c.ParentID,
			Name:      c.Name,
			Type:      string(c.Type),
			Aliases:   c.Aliases,
			Status:    c.Status,
			CreatedAt: c.CreatedAt.Format(time.RFC3339),
			UpdatedAt: c.UpdatedAt.Format(time.RFC3339),
		})
	}

	return &pb.ListCategoriesResponse{Categories: records}, nil
}

func (s FinanceServicer) GetFinancialReport(ctx context.Context, req *pb.GetFinancialReportRequest) (*pb.GetFinancialReportResponse, error) {
	if s.Service == nil {
		return nil, status.Error(codes.FailedPrecondition, "finance service is not wired")
	}
	var start, end time.Time
	var err error

	if req.GetPeriodStart() != "" {
		start, err = time.Parse(time.RFC3339, req.GetPeriodStart())
		if err != nil {
			return nil, err
		}
	}
	if req.GetPeriodEnd() != "" {
		end, err = time.Parse(time.RFC3339, req.GetPeriodEnd())
		if err != nil {
			return nil, err
		}
	}

	query := domain.ReportQuery{
		OwnerID:               req.GetOwnerId(),
		PeriodStart:           start,
		PeriodEnd:             end,
		IncludeInvestment:     req.GetIncludeInvestment(),
		GroupBy:               req.GetGroupBy(),
		UseCreatedAtAuditDate: req.GetUseCreatedAtAuditDate(),
	}

	if req.WalletId != nil {
		w := req.GetWalletId()
		query.WalletID = &w
	}
	if req.CategoryId != nil {
		c := req.GetCategoryId()
		query.CategoryID = &c
	}

	dto, err := s.Service.GetFinancialReport(ctx, query)
	if err != nil {
		return nil, err
	}

	return &pb.GetFinancialReportResponse{
		PeriodStart:                      dto.PeriodStart.Format(time.RFC3339),
		PeriodEnd:                        dto.PeriodEnd.Format(time.RFC3339),
		GroupBy:                          dto.GroupBy,
		IncomeTotalMinor:                 dto.IncomeTotalMinor,
		ExpenseTotalMinor:                dto.ExpenseTotalMinor,
		NetCashflowMinor:                 dto.NetCashflowMinor,
		TransferInTotalMinor:             dto.TransferInTotalMinor,
		TransferOutTotalMinor:            dto.TransferOutTotalMinor,
		ExcludedTotalMinor:               dto.ExcludedTotalMinor,
		InvestmentCashMovementTotalMinor: dto.InvestmentCashMovementTotalMinor,
		ByCategory:                      dto.ByCategory,
		ByWallet:                        dto.ByWallet,
		ByPeriod:                        dto.ByPeriod,
		Warnings:                        dto.Warnings,
	}, nil
}

func (s FinanceServicer) GetNetWorth(ctx context.Context, req *pb.GetNetWorthRequest) (*pb.GetNetWorthResponse, error) {
	if s.Service == nil {
		return nil, status.Error(codes.FailedPrecondition, "finance service is not wired")
	}
	var asOf time.Time
	var err error

	if req.GetAsOf() != "" {
		asOf, err = time.Parse(time.RFC3339, req.GetAsOf())
		if err != nil {
			return nil, err
		}
	}

	query := domain.NetWorthQuery{
		OwnerID: req.GetOwnerId(),
		AsOf:    asOf,
	}

	dto, err := s.Service.GetNetWorth(ctx, query)
	if err != nil {
		return nil, err
	}

	return &pb.GetNetWorthResponse{
		AsOf:                dto.AsOf.Format(time.RFC3339),
		CashTotalMinor:      dto.CashTotalMinor,
		AssetValueMinor:     dto.AssetValueMinor,
		LiabilityMinor:      dto.LiabilityMinor,
		ReceivableMinor:     dto.ReceivableMinor,
		NetWorthMinor:       dto.NetWorthMinor,
		RealizedGainMinor:   dto.RealizedGainMinor,
		UnrealizedGainMinor: dto.UnrealizedGainMinor,
		Warnings:            dto.Warnings,
	}, nil
}
