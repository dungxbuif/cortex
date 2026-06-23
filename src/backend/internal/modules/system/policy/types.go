package policy

import "context"

const (
	ModuleFinance     = "finance"
	ModuleSecondBrain = "second_brain"
	ModuleHomelab     = "homelab"
)

const (
	CapabilityRead                = "read"
	CapabilityRAGQuery            = "rag_query"
	CapabilityCapture             = "capture"
	CapabilityWriteAppDB          = "write_app_db"
	CapabilityWriteExternalSource = "write_external_source"
	CapabilitySyncFromExternal    = "sync_from_external"
	CapabilityIndexExternalSource = "index_external_source"
	CapabilityExecuteRuntime      = "execute_runtime_action"
	CapabilityManagePolicy        = "manage_policy"
)

const (
	DecisionAllow                = "allow"
	DecisionDeny                 = "deny"
	DecisionRequireConfirmation  = "require_confirmation"
	DecisionRequireClarification = "require_clarification"
	DecisionManualActionRequired = "manual_action_required"
)

type AuditSink interface {
	AppendEvent(ctx context.Context, command AuditEventCommand) (AuditEvent, error)
}

type AuditEvent struct {
	ID string
}

type AuditEventCommand struct {
	EventType      string
	Module         string
	ActorType      string
	ActorID        string
	ConversationID string
	RequestID      string
	ToolName       string
	Capability     string
	SourceRef      map[string]any
	TargetRef      map[string]any
	Status         string
	Metadata       map[string]any
}

type EvaluateCommand struct {
	Module         string
	Capability     string
	ActorType      string
	ActorID        string
	ConversationID string
	RequestID      string
	ToolName       string
	HighImpact     bool
	Ambiguous      bool
	LowConfidence  bool
	MoneyMovement  bool
	AuditRead      bool
	SourceRef      map[string]any
	TargetRef      map[string]any
	Metadata       map[string]any
}

type DecisionResult struct {
	Decision     string
	Reason       string
	AuditEventID string
}
