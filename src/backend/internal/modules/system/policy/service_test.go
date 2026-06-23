package policy

import (
	"context"
	"testing"
)

type fakeAuditSink struct {
	events []AuditEventCommand
}

func (f *fakeAuditSink) AppendEvent(_ context.Context, command AuditEventCommand) (AuditEvent, error) {
	f.events = append(f.events, command)
	return AuditEvent{ID: "audit-id"}, nil
}

func TestEvaluateAllowsKnownCapabilityAndAuditsIndexDecision(t *testing.T) {
	sink := &fakeAuditSink{}
	service := NewService(sink)
	result, err := service.Evaluate(context.Background(), EvaluateCommand{
		Module:     ModuleSecondBrain,
		Capability: CapabilityIndexExternalSource,
		ActorType:  "system",
		ActorID:    "n8n_worker",
		RequestID:  "req-1",
		ToolName:   "second_brain.sync_minio_object",
	})
	if err != nil {
		t.Fatalf("evaluate: %v", err)
	}
	if result.Decision != DecisionAllow {
		t.Fatalf("expected allow, got %#v", result)
	}
	if result.AuditEventID != "audit-id" {
		t.Fatalf("expected audit id, got %q", result.AuditEventID)
	}
	if len(sink.events) != 1 || sink.events[0].EventType != "PermissionAllowed" {
		t.Fatalf("expected allowed audit event, got %#v", sink.events)
	}
}

func TestEvaluateDeniesUnknownModuleOrCapability(t *testing.T) {
	service := NewService(&fakeAuditSink{})
	result, err := service.Evaluate(context.Background(), EvaluateCommand{
		Module:     "unknown",
		Capability: CapabilityRead,
	})
	if err != nil {
		t.Fatalf("evaluate unknown module: %v", err)
	}
	if result.Decision != DecisionDeny {
		t.Fatalf("expected deny for unknown module, got %#v", result)
	}

	result, err = service.Evaluate(context.Background(), EvaluateCommand{
		Module:     ModuleFinance,
		Capability: "teleport",
	})
	if err != nil {
		t.Fatalf("evaluate unknown capability: %v", err)
	}
	if result.Decision != DecisionDeny {
		t.Fatalf("expected deny for unknown capability, got %#v", result)
	}
}

func TestEvaluateHardDeniesSourceOfTruthViolations(t *testing.T) {
	service := NewService(&fakeAuditSink{})
	cases := []EvaluateCommand{
		{Module: ModuleHomelab, Capability: CapabilityWriteExternalSource},
		{Module: ModuleHomelab, Capability: CapabilityExecuteRuntime},
		{Module: ModuleSecondBrain, Capability: CapabilityWriteExternalSource},
	}
	for _, command := range cases {
		result, err := service.Evaluate(context.Background(), command)
		if err != nil {
			t.Fatalf("evaluate hard denial: %v", err)
		}
		if result.Decision != DecisionDeny {
			t.Fatalf("expected deny for %#v, got %#v", command, result)
		}
	}
}

func TestEvaluateRequiresConfirmationForHighImpactFinanceWrite(t *testing.T) {
	sink := &fakeAuditSink{}
	service := NewService(sink)
	result, err := service.Evaluate(context.Background(), EvaluateCommand{
		Module:        ModuleFinance,
		Capability:    CapabilityWriteAppDB,
		HighImpact:    true,
		MoneyMovement: true,
		ActorType:     "user",
		ActorID:       "owner",
	})
	if err != nil {
		t.Fatalf("evaluate finance write: %v", err)
	}
	if result.Decision != DecisionRequireConfirmation {
		t.Fatalf("expected require confirmation, got %#v", result)
	}
	if len(sink.events) != 1 || sink.events[0].EventType != "ConfirmationRequested" {
		t.Fatalf("expected confirmation audit event, got %#v", sink.events)
	}
}

func TestConfirmationCannotOverrideHardDenial(t *testing.T) {
	service := NewService(&fakeAuditSink{})
	result, err := service.Evaluate(context.Background(), EvaluateCommand{
		Module:        ModuleHomelab,
		Capability:    CapabilityWriteExternalSource,
		HighImpact:    true,
		MoneyMovement: true,
	})
	if err != nil {
		t.Fatalf("evaluate hard denial: %v", err)
	}
	if result.Decision != DecisionDeny {
		t.Fatalf("expected deny before confirmation, got %#v", result)
	}
}
