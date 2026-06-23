package audit

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func TestValidateAppendCommandRejectsMissingRequiredFields(t *testing.T) {
	err := validateAppendCommand(AppendEventCommand{})
	if !errors.Is(err, ErrInvalidEvent) {
		t.Fatalf("expected ErrInvalidEvent, got %v", err)
	}
	for _, field := range []string{"event_type", "module", "actor_type", "actor_id", "status"} {
		if !strings.Contains(err.Error(), field) {
			t.Fatalf("expected missing field %s in error %q", field, err.Error())
		}
	}
}

func TestValidateAppendCommandRejectsUnsupportedStatus(t *testing.T) {
	err := validateAppendCommand(validCommand(func(command *AppendEventCommand) {
		command.Status = "pending"
	}))
	if !errors.Is(err, ErrInvalidEvent) {
		t.Fatalf("expected ErrInvalidEvent, got %v", err)
	}
}

func TestValidateAppendCommandRejectsSecretLookingKeysRecursively(t *testing.T) {
	err := validateAppendCommand(validCommand(func(command *AppendEventCommand) {
		command.Metadata = JSONMap{
			"nested": map[string]any{
				"api_key": "do-not-store",
			},
		}
	}))
	if !errors.Is(err, ErrSecretRef) {
		t.Fatalf("expected ErrSecretRef, got %v", err)
	}
}

func TestServiceAppendGetListWithPostgres(t *testing.T) {
	db := integrationDB(t)
	service := NewService(db)

	first, err := service.AppendEvent(context.Background(), validCommand(func(command *AppendEventCommand) {
		command.RequestID = "req-1"
		command.Module = "second_brain"
		command.EventType = "PermissionAllowed"
	}))
	if err != nil {
		t.Fatalf("append first event: %v", err)
	}
	_, err = service.AppendEvent(context.Background(), validCommand(func(command *AppendEventCommand) {
		command.RequestID = "req-1"
		command.Module = "finance"
		command.EventType = "PermissionDenied"
		command.Status = StatusDenied
	}))
	if err != nil {
		t.Fatalf("append second event: %v", err)
	}

	got, err := service.GetEvent(context.Background(), first.ID)
	if err != nil {
		t.Fatalf("get event: %v", err)
	}
	if got.ID != first.ID || got.Module != "second_brain" {
		t.Fatalf("unexpected event: %#v", got)
	}

	byRequest, err := service.ListEventsByRequest(context.Background(), "req-1")
	if err != nil {
		t.Fatalf("list by request: %v", err)
	}
	if len(byRequest) != 2 {
		t.Fatalf("expected 2 request events, got %d", len(byRequest))
	}

	timeline, err := service.ListModuleTimeline(context.Background(), "second_brain", ListEventsQuery{})
	if err != nil {
		t.Fatalf("list module timeline: %v", err)
	}
	if len(timeline) != 1 || timeline[0].ID != first.ID {
		t.Fatalf("unexpected module timeline: %#v", timeline)
	}
}

func validCommand(mutators ...func(*AppendEventCommand)) AppendEventCommand {
	command := AppendEventCommand{
		EventType:  "PermissionAllowed",
		Module:     "second_brain",
		ActorType:  "system",
		ActorID:    "n8n_worker",
		Capability: "index_external_source",
		Status:     StatusSuccess,
		SourceRef:  JSONMap{"bucket": "obsidian", "key": "second-brain/wiki/a.md"},
		TargetRef:  JSONMap{"table": "secondbrain_documents"},
		Metadata:   JSONMap{"reason": "test"},
	}
	for _, mutator := range mutators {
		mutator(&command)
	}
	return command
}

func integrationDB(t *testing.T) *gorm.DB {
	t.Helper()
	dsn := os.Getenv("SYSTEM_TEST_DATABASE_URL")
	if dsn == "" {
		dsn = os.Getenv("DATABASE_URL")
	}
	if dsn == "" {
		t.Skip("set SYSTEM_TEST_DATABASE_URL or DATABASE_URL for audit integration tests")
	}
	admin, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		t.Fatalf("connect admin database: %v", err)
	}
	schema := "test_audit_" + strings.ReplaceAll(newEventID(), "-", "_")
	if err := admin.Exec("CREATE SCHEMA " + schema).Error; err != nil {
		t.Fatalf("create schema: %v", err)
	}
	t.Cleanup(func() {
		_ = admin.Exec("DROP SCHEMA " + schema + " CASCADE").Error
	})
	schemaDSN := dsn
	if strings.Contains(schemaDSN, "search_path=") {
		t.Fatalf("test dsn must not already set search_path")
	}
	separator := "?"
	if strings.Contains(schemaDSN, "?") {
		separator = "&"
	}
	schemaDSN += separator + "search_path=" + schema
	db, err := gorm.Open(postgres.Open(schemaDSN), &gorm.Config{})
	if err != nil {
		t.Fatalf("connect schema database: %v", err)
	}
	sqlBytes, err := os.ReadFile(migrationPath(t, "000002_audit_events.up.sql"))
	if err != nil {
		t.Fatalf("read audit migration: %v", err)
	}
	if err := db.Exec(string(sqlBytes)).Error; err != nil {
		t.Fatalf("apply audit migration: %v", err)
	}
	return db
}

func migrationPath(t *testing.T, filename string) string {
	t.Helper()
	wd, err := os.Getwd()
	if err != nil {
		t.Fatalf("get wd: %v", err)
	}
	for {
		candidate := filepath.Join(wd, "migrations", filename)
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
		parent := filepath.Dir(wd)
		if parent == wd {
			t.Fatalf("could not find migration %s", filename)
		}
		wd = parent
	}
}
