package tests

import (
	"strings"
	"testing"
	"time"

	"cortex/internal/modules/finance/domain"
)

func TestNormalizeOwnerDefaultsToSingleUserOwner(t *testing.T) {
	if got := domain.NormalizeOwner(""); got != domain.DefaultOwnerID {
		t.Fatalf("NormalizeOwner(\"\") = %q, want %q", got, domain.DefaultOwnerID)
	}
	if got := domain.NormalizeOwner("custom-owner"); got != "custom-owner" {
		t.Fatalf("NormalizeOwner(custom) = %q", got)
	}
}

func TestAuditHelpersPopulateAndTouchActorFields(t *testing.T) {
	createdAt := time.Date(2026, 6, 17, 10, 0, 0, 0, time.UTC)
	audit := domain.NewAudit("owner", createdAt)
	if audit.CreatedBy != "owner" || audit.UpdatedBy != "owner" {
		t.Fatalf("audit actor fields = %q/%q", audit.CreatedBy, audit.UpdatedBy)
	}

	updatedAt := createdAt.Add(time.Hour)
	domain.Touch(&audit, "editor", updatedAt)
	if audit.CreatedBy != "owner" {
		t.Fatalf("created actor changed to %q", audit.CreatedBy)
	}
	if audit.UpdatedBy != "editor" || !audit.UpdatedAt.Equal(updatedAt) {
		t.Fatalf("updated audit = %q/%s", audit.UpdatedBy, audit.UpdatedAt)
	}
}

func TestRequirePositiveMinor(t *testing.T) {
	if err := domain.RequirePositiveMinor("amount_minor", 1); err != nil {
		t.Fatalf("positive minor amount returned error: %v", err)
	}
	err := domain.RequirePositiveMinor("amount_minor", 0)
	if err == nil || !strings.Contains(err.Error(), "VALIDATION_ERROR") {
		t.Fatalf("zero minor amount error = %v", err)
	}
}
