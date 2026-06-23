package domain

import "time"

type CreateWalletCommand struct {
	OwnerID             string
	ActorID             string
	Name                string
	Type                WalletType
	Currency            string
	InitialBalanceMinor int64
	IncludeInTotal      bool
}

type UpdateWalletCommand struct {
	OwnerID        string
	ActorID        string
	ID             string
	Name           *string
	IncludeInTotal *bool
}

type CreateCategoryCommand struct {
	OwnerID  string
	ActorID  string
	ParentID *string
	Name     string
	Type     CategoryType
	Aliases  string
}

type CreateTransactionCommand struct {
	OwnerID           string
	ActorID           string
	WalletID          string
	CategoryID        *string
	Type              TransactionType
	AmountMinor       int64
	Currency          string
	OccurredAt        time.Time
	Note              string
	WithPerson        string
	Location          string
	EventID           string
	ExcludeFromReport bool
}

type CreateTransferCommand struct {
	OwnerID      string
	ActorID      string
	FromWalletID string
	ToWalletID   string
	AmountMinor  int64
	Currency     string
	OccurredAt   time.Time
	Note         string
}

type CreateAssetCommand struct {
	OwnerID     string
	ActorID     string
	AssetType   AssetType
	Symbol      string
	Name        string
	Currency    string
	Unit        string
	PriceSource string
}

type RecordAssetTransactionCommand struct {
	OwnerID          string
	ActorID          string
	AssetID          string
	WalletID         *string
	Type             AssetTransactionType
	Quantity         string
	UnitPriceMinor   int64
	GrossAmountMinor int64
	FeeMinor         int64
	TaxMinor         int64
	NetAmountMinor   int64
	Currency         string
	OccurredAt       time.Time
	Note             string
}

type UpdateAssetPriceCommand struct {
	OwnerID        string
	ActorID        string
	AssetID        string
	PriceMinor     int64
	BuyPriceMinor  int64
	SellPriceMinor int64
	Currency       string
	PriceType      AssetPriceType
	Source         string
	PricedAt       time.Time
}

type CreateDebtOrLoanCommand struct {
	OwnerID              string
	ActorID              string
	Direction            DebtDirection
	Counterparty         string
	PrincipalAmountMinor int64
	Currency             string
	DueDate              *time.Time
	Note                 string
}

type UpdateDebtOrLoanCommand struct {
	OwnerID      string
	ActorID      string
	ID           string
	Counterparty *string
	DueDate      *time.Time
	Status       *DebtStatus
	Note         *string
}

type RecordDebtPaymentCommand struct {
	OwnerID     string
	ActorID     string
	DebtLoanID  string
	WalletID    string
	AmountMinor int64
	PaidAt      time.Time
	Note        string
}

type ReportQuery struct {
	OwnerID               string
	PeriodStart           time.Time
	PeriodEnd             time.Time
	WalletID              *string
	CategoryID            *string
	IncludeInvestment     bool
	GroupBy               string
	UseCreatedAtAuditDate bool
}

type NetWorthQuery struct {
	OwnerID string
	AsOf    time.Time
}

type ListDebtsQuery struct {
	OwnerID   string
	Direction *DebtDirection
	Status    *DebtStatus
	DueBefore *time.Time
}

type DebtStatusQuery struct {
	OwnerID string
	ID      string
}

type FinancialReportDTO struct {
	PeriodStart                      time.Time
	PeriodEnd                        time.Time
	GroupBy                          string
	IncomeTotalMinor                 int64
	ExpenseTotalMinor                int64
	NetCashflowMinor                 int64
	TransferInTotalMinor             int64
	TransferOutTotalMinor            int64
	ExcludedTotalMinor               int64
	InvestmentCashMovementTotalMinor int64
	ByCategory                       map[string]int64
	ByWallet                         map[string]int64
	ByPeriod                         map[string]int64
	Warnings                         []string
}

type NetWorthDTO struct {
	AsOf                time.Time
	CashTotalMinor      int64
	AssetValueMinor     int64
	LiabilityMinor      int64
	ReceivableMinor     int64
	NetWorthMinor       int64
	RealizedGainMinor   int64
	UnrealizedGainMinor int64
	Warnings            []string
}

type DebtStatusDTO struct {
	DebtLoan
	PaidOrCollectedMinor int64
}
