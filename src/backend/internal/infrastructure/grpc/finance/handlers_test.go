package finance

import (
	"context"
	"net"
	"testing"
	"time"

	"cortex/internal/infrastructure/grpc/pb"
	"cortex/internal/modules/finance/domain"
	"google.golang.org/grpc"
	"google.golang.org/grpc/test/bufconn"
)

const bufSize = 1024 * 1024

type fakeFinance struct {
	wallets    []domain.Wallet
	categories []domain.Category
	report     *domain.FinancialReportDTO
	netWorth   *domain.NetWorthDTO
}

func (f *fakeFinance) ListWallets(ctx context.Context, ownerID string) ([]domain.Wallet, error) {
	return f.wallets, nil
}

func (f *fakeFinance) ListCategories(ctx context.Context, ownerID string) ([]domain.Category, error) {
	return f.categories, nil
}

func (f *fakeFinance) GetFinancialReport(ctx context.Context, query domain.ReportQuery) (*domain.FinancialReportDTO, error) {
	return f.report, nil
}

func (f *fakeFinance) GetNetWorth(ctx context.Context, query domain.NetWorthQuery) (*domain.NetWorthDTO, error) {
	return f.netWorth, nil
}

func TestFinanceGrpcService(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()

	parentID := "cat_parent"
	fSvc := &fakeFinance{
		wallets: []domain.Wallet{
			{
				ID:                  "wal_1",
				OwnerID:             "owner-1",
				Name:                "Cash Wallet",
				Type:                domain.WalletTypeBasic,
				Currency:            "VND",
				InitialBalanceMinor: 10000,
				CurrentBalanceMinor: 15000,
				IncludeInTotal:      true,
				Status:              domain.WalletStatusActive,
				AuditFields: domain.AuditFields{
					CreatedAt: now,
					CreatedBy: "user",
					UpdatedAt: now,
					UpdatedBy: "user",
				},
			},
		},
		categories: []domain.Category{
			{
				ID:       "cat_1",
				OwnerID:  "owner-1",
				ParentID: &parentID,
				Name:     "Food",
				Type:     domain.CategoryTypeExpense,
				Aliases:  "grocery,restaurant",
				Status:   "active",
				AuditFields: domain.AuditFields{
					CreatedAt: now,
					CreatedBy: "user",
					UpdatedAt: now,
					UpdatedBy: "user",
				},
			},
		},
		report: &domain.FinancialReportDTO{
			PeriodStart:       now,
			PeriodEnd:         now.Add(24 * time.Hour),
			GroupBy:           "day",
			IncomeTotalMinor:  5000,
			ExpenseTotalMinor: 2000,
			NetCashflowMinor:  3000,
			ByCategory:        map[string]int64{"cat_1": 2000},
			ByWallet:          map[string]int64{"wal_1": 3000},
			ByPeriod:          map[string]int64{now.Format("2006-01-02"): 3000},
			Warnings:          []string{"test warning"},
		},
		netWorth: &domain.NetWorthDTO{
			AsOf:            now,
			CashTotalMinor:  15000,
			AssetValueMinor: 50000,
			LiabilityMinor:  5000,
			ReceivableMinor: 1000,
			NetWorthMinor:   61000,
			Warnings:        []string{"networth warning"},
		},
	}

	lis := bufconn.Listen(bufSize)
	server := grpc.NewServer()
	pb.RegisterFinanceServiceServer(server, FinanceServicer{Service: fSvc})
	go func() {
		if err := server.Serve(lis); err != nil {
			t.Errorf("serve grpc: %v", err)
		}
	}()
	defer server.Stop()

	conn, err := grpc.NewClient(
		"passthrough:///bufnet",
		grpc.WithContextDialer(func(context.Context, string) (net.Conn, error) {
			return lis.Dial()
		}),
		grpc.WithInsecure(),
	)
	if err != nil {
		t.Fatalf("dial bufnet: %v", err)
	}
	defer conn.Close()

	client := pb.NewFinanceServiceClient(conn)

	// Test ListWallets
	wResp, err := client.ListWallets(ctx, &pb.ListWalletsRequest{OwnerId: "owner-1"})
	if err != nil {
		t.Fatalf("ListWallets failed: %v", err)
	}
	if len(wResp.Wallets) != 1 || wResp.Wallets[0].Id != "wal_1" {
		t.Fatalf("expected wal_1, got %+v", wResp.Wallets)
	}
	if wResp.Wallets[0].CreatedAt != now.Format(time.RFC3339) {
		t.Fatalf("expected format %s, got %s", now.Format(time.RFC3339), wResp.Wallets[0].CreatedAt)
	}

	// Test ListCategories
	cResp, err := client.ListCategories(ctx, &pb.ListCategoriesRequest{OwnerId: "owner-1"})
	if err != nil {
		t.Fatalf("ListCategories failed: %v", err)
	}
	if len(cResp.Categories) != 1 || cResp.Categories[0].Id != "cat_1" || *cResp.Categories[0].ParentId != "cat_parent" {
		t.Fatalf("expected cat_1 with parent cat_parent, got %+v", cResp.Categories)
	}

	// Test GetFinancialReport
	rResp, err := client.GetFinancialReport(ctx, &pb.GetFinancialReportRequest{
		OwnerId:     "owner-1",
		PeriodStart: now.Format(time.RFC3339),
		PeriodEnd:   now.Add(24 * time.Hour).Format(time.RFC3339),
	})
	if err != nil {
		t.Fatalf("GetFinancialReport failed: %v", err)
	}
	if rResp.IncomeTotalMinor != 5000 || rResp.ByCategory["cat_1"] != 2000 {
		t.Fatalf("expected income 5000 and cat_1 2000, got %+v", rResp)
	}

	// Test GetNetWorth
	nwResp, err := client.GetNetWorth(ctx, &pb.GetNetWorthRequest{
		OwnerId: "owner-1",
		AsOf:    now.Format(time.RFC3339),
	})
	if err != nil {
		t.Fatalf("GetNetWorth failed: %v", err)
	}
	if nwResp.NetWorthMinor != 61000 || len(nwResp.Warnings) != 1 {
		t.Fatalf("expected networth 61000, got %+v", nwResp)
	}
}
