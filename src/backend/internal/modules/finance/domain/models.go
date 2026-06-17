package domain

import (
	"crypto/rand"
	"encoding/hex"
	"time"

	appErrors "cortex/internal/core/errors"
)

const (
	DefaultOwnerID = "owner-single-user"
	SystemActorID  = "system"

	DefaultCurrency = "VND"
)

type WalletType string
type WalletStatus string
type CategoryType string
type TransactionType string
type TransactionDirection string
type AssetType string
type AssetTransactionType string
type AssetPriceType string
type DebtDirection string
type DebtStatus string

const (
	WalletTypeBasic  WalletType = "basic"
	WalletTypeGoal   WalletType = "goal"
	WalletTypeCredit WalletType = "credit"
	WalletTypeLinked WalletType = "linked"

	WalletStatusActive   WalletStatus = "active"
	WalletStatusArchived WalletStatus = "archived"

	CategoryTypeIncome  CategoryType = "income"
	CategoryTypeExpense CategoryType = "expense"

	TransactionTypeIncome         TransactionType = "income"
	TransactionTypeExpense        TransactionType = "expense"
	TransactionTypeTransferIn     TransactionType = "transfer_in"
	TransactionTypeTransferOut    TransactionType = "transfer_out"
	TransactionTypeInvestmentBuy  TransactionType = "investment_buy"
	TransactionTypeInvestmentSell TransactionType = "investment_sell"
	TransactionTypeDebtPayment    TransactionType = "debt_payment"
	TransactionTypeDebtCollection TransactionType = "debt_collection"

	DirectionDebit  TransactionDirection = "debit"
	DirectionCredit TransactionDirection = "credit"

	AssetTypeGold           AssetType = "gold"
	AssetTypeStock          AssetType = "stock"
	AssetTypeFund           AssetType = "fund"
	AssetTypeCrypto         AssetType = "crypto"
	AssetTypeSavingDeposit  AssetType = "saving_deposit"
	AssetTypeCashEquivalent AssetType = "cash_equivalent"
	AssetTypeOther          AssetType = "other"

	AssetTransactionBuy         AssetTransactionType = "buy"
	AssetTransactionSell        AssetTransactionType = "sell"
	AssetTransactionTransferIn  AssetTransactionType = "transfer_in"
	AssetTransactionTransferOut AssetTransactionType = "transfer_out"
	AssetTransactionDividend    AssetTransactionType = "dividend"
	AssetTransactionSplit       AssetTransactionType = "split"
	AssetTransactionAdjustment  AssetTransactionType = "price_adjustment"

	PriceTypeBuy       AssetPriceType = "buy"
	PriceTypeSell      AssetPriceType = "sell"
	PriceTypeClose     AssetPriceType = "close"
	PriceTypeLast      AssetPriceType = "last"
	PriceTypeManual    AssetPriceType = "manual"
	PriceTypeEstimated AssetPriceType = "estimated"

	DebtDirectionIOwe     DebtDirection = "i_owe"
	DebtDirectionOwedToMe DebtDirection = "owed_to_me"

	DebtStatusActive           DebtStatus = "active"
	DebtStatusPartiallySettled DebtStatus = "partially_settled"
	DebtStatusSettled          DebtStatus = "settled"
	DebtStatusForgiven         DebtStatus = "forgiven"
	DebtStatusArchived         DebtStatus = "archived"
)

type AuditFields struct {
	CreatedAt time.Time `gorm:"not null"`
	CreatedBy string    `gorm:"size:64;not null"`
	UpdatedAt time.Time `gorm:"not null"`
	UpdatedBy string    `gorm:"size:64;not null"`
}

type SoftDeleteFields struct {
	DeletedAt *time.Time `gorm:"index"`
	DeletedBy *string    `gorm:"size:64"`
}

type Wallet struct {
	ID                  string       `gorm:"primaryKey;size:64"`
	OwnerID             string       `gorm:"size:64;not null;index"`
	Name                string       `gorm:"size:160;not null"`
	Type                WalletType   `gorm:"size:32;not null"`
	Currency            string       `gorm:"size:3;not null"`
	InitialBalanceMinor int64        `gorm:"not null"`
	CurrentBalanceMinor int64        `gorm:"not null"`
	IncludeInTotal      bool         `gorm:"not null"`
	Status              WalletStatus `gorm:"size:32;not null;index"`
	ArchivedAt          *time.Time
	AuditFields
}

type Category struct {
	ID       string       `gorm:"primaryKey;size:64"`
	OwnerID  string       `gorm:"size:64;not null;index"`
	ParentID *string      `gorm:"size:64;index"`
	Name     string       `gorm:"size:160;not null"`
	Type     CategoryType `gorm:"size:32;not null"`
	Aliases  string       `gorm:"type:text;not null;default:''"`
	Status   string       `gorm:"size:32;not null;default:'active'"`
	AuditFields
}

type Transaction struct {
	ID                string               `gorm:"primaryKey;size:64"`
	OwnerID           string               `gorm:"size:64;not null;index"`
	WalletID          string               `gorm:"size:64;not null;index"`
	CategoryID        *string              `gorm:"size:64;index"`
	Type              TransactionType      `gorm:"size:40;not null;index"`
	Direction         TransactionDirection `gorm:"size:16;not null"`
	AmountMinor       int64                `gorm:"not null"`
	Currency          string               `gorm:"size:3;not null"`
	OccurredAt        time.Time            `gorm:"not null;index"`
	Note              string               `gorm:"type:text;not null;default:''"`
	WithPerson        string               `gorm:"size:160;not null;default:''"`
	Location          string               `gorm:"size:240;not null;default:''"`
	EventID           string               `gorm:"size:120;not null;default:''"`
	ExcludeFromReport bool                 `gorm:"not null"`
	TransferGroupID   *string              `gorm:"size:64;index"`
	AuditFields
	SoftDeleteFields
}

type Asset struct {
	ID          string    `gorm:"primaryKey;size:64"`
	OwnerID     string    `gorm:"size:64;not null;index"`
	AssetType   AssetType `gorm:"size:40;not null"`
	Symbol      string    `gorm:"size:64;not null"`
	Name        string    `gorm:"size:160;not null"`
	Currency    string    `gorm:"size:3;not null"`
	Unit        string    `gorm:"size:32;not null"`
	PriceSource string    `gorm:"size:40;not null"`
	IsActive    bool      `gorm:"not null"`
	AuditFields
}

type AssetTransaction struct {
	ID                      string               `gorm:"primaryKey;size:64"`
	OwnerID                 string               `gorm:"size:64;not null;index"`
	AssetID                 string               `gorm:"size:64;not null;index"`
	WalletID                *string              `gorm:"size:64;index"`
	LinkedCashTransactionID *string              `gorm:"size:64;index"`
	TransactionType         AssetTransactionType `gorm:"size:40;not null"`
	Quantity                string               `gorm:"type:numeric(30,12);not null"`
	UnitPriceMinor          int64                `gorm:"not null"`
	GrossAmountMinor        int64                `gorm:"not null"`
	FeeMinor                int64                `gorm:"not null"`
	TaxMinor                int64                `gorm:"not null"`
	NetAmountMinor          int64                `gorm:"not null"`
	Currency                string               `gorm:"size:3;not null"`
	OccurredAt              time.Time            `gorm:"not null;index"`
	Note                    string               `gorm:"type:text;not null;default:''"`
	AuditFields
	SoftDeleteFields
}

type AssetHolding struct {
	ID                  string `gorm:"primaryKey;size:64"`
	OwnerID             string `gorm:"size:64;not null;index"`
	AssetID             string `gorm:"size:64;not null;uniqueIndex:idx_asset_holding_owner_asset"`
	Quantity            string `gorm:"type:numeric(30,12);not null"`
	AverageCostMinor    int64  `gorm:"not null"`
	TotalCostMinor      int64  `gorm:"not null"`
	RealizedGainMinor   int64  `gorm:"not null"`
	CurrentPriceMinor   int64  `gorm:"not null"`
	CurrentValueMinor   int64  `gorm:"not null"`
	UnrealizedGainMinor int64  `gorm:"not null"`
	LastPricedAt        *time.Time
	AuditFields
}

type AssetPrice struct {
	ID             string         `gorm:"primaryKey;size:64"`
	OwnerID        string         `gorm:"size:64;not null;index"`
	AssetID        string         `gorm:"size:64;not null;index"`
	PriceMinor     int64          `gorm:"not null"`
	BuyPriceMinor  int64          `gorm:"not null"`
	SellPriceMinor int64          `gorm:"not null"`
	Currency       string         `gorm:"size:3;not null"`
	PriceType      AssetPriceType `gorm:"size:32;not null;index"`
	Source         string         `gorm:"size:80;not null"`
	PricedAt       time.Time      `gorm:"not null;index"`
	AuditFields
}

type DebtLoan struct {
	ID                   string        `gorm:"primaryKey;size:64"`
	OwnerID              string        `gorm:"size:64;not null;index"`
	Direction            DebtDirection `gorm:"size:32;not null;index"`
	Counterparty         string        `gorm:"size:160;not null"`
	PrincipalAmountMinor int64         `gorm:"not null"`
	RemainingAmountMinor int64         `gorm:"not null"`
	Currency             string        `gorm:"size:3;not null"`
	DueDate              *time.Time    `gorm:"index"`
	Status               DebtStatus    `gorm:"size:32;not null;index"`
	Note                 string        `gorm:"type:text;not null;default:''"`
	ArchivedAt           *time.Time
	AuditFields
}

type DebtPayment struct {
	ID                string    `gorm:"primaryKey;size:64"`
	OwnerID           string    `gorm:"size:64;not null;index"`
	DebtLoanID        string    `gorm:"size:64;not null;index"`
	WalletID          string    `gorm:"size:64;not null;index"`
	CashTransactionID *string   `gorm:"size:64;index"`
	AmountMinor       int64     `gorm:"not null"`
	PaidAt            time.Time `gorm:"not null;index"`
	Note              string    `gorm:"type:text;not null;default:''"`
	AuditFields
	SoftDeleteFields
}

func NewID(prefix string) string {
	var b [8]byte
	if _, err := rand.Read(b[:]); err != nil {
		return prefix + "_" + time.Now().UTC().Format("20060102150405.000000000")
	}
	return prefix + "_" + hex.EncodeToString(b[:])
}

func NewAudit(actor string, now time.Time) AuditFields {
	if actor == "" {
		actor = SystemActorID
	}
	return AuditFields{CreatedAt: now, CreatedBy: actor, UpdatedAt: now, UpdatedBy: actor}
}

func Touch(a *AuditFields, actor string, now time.Time) {
	if actor == "" {
		actor = SystemActorID
	}
	a.UpdatedAt = now
	a.UpdatedBy = actor
}

func NormalizeOwner(ownerID string) string {
	if ownerID == "" {
		return DefaultOwnerID
	}
	return ownerID
}

func NormalizeActor(actorID string) string {
	if actorID == "" {
		return SystemActorID
	}
	return actorID
}

func NormalizeCurrency(currency string) string {
	if currency == "" {
		return DefaultCurrency
	}
	return currency
}

func RequirePositiveMinor(name string, value int64) error {
	if value <= 0 {
		return appErrors.NewValidationError(name + " must be positive")
	}
	return nil
}
