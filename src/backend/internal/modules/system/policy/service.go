package policy

import (
	"context"
	"errors"
	"fmt"
	"strings"
)

var ErrDenied = errors.New("capability denied")

type Service struct {
	audit AuditSink
}

func NewService(audit AuditSink) *Service {
	return &Service{audit: audit}
}

func (s *Service) Evaluate(ctx context.Context, command EvaluateCommand) (DecisionResult, error) {
	module := strings.TrimSpace(command.Module)
	capability := strings.TrimSpace(command.Capability)
	result := evaluateDecision(command, module, capability)

	if shouldAudit(command, result.Decision) && s.audit != nil {
		event, err := s.audit.AppendEvent(ctx, AuditEventCommand{
			EventType:      eventTypeForDecision(result.Decision),
			Module:         module,
			ActorType:      defaultString(command.ActorType, "system"),
			ActorID:        defaultString(command.ActorID, "unknown"),
			ConversationID: command.ConversationID,
			RequestID:      command.RequestID,
			ToolName:       command.ToolName,
			Capability:     capability,
			SourceRef:      command.SourceRef,
			TargetRef:      command.TargetRef,
			Status:         auditStatusForDecision(result.Decision),
			Metadata: mergeMetadata(command.Metadata, map[string]any{
				"decision": result.Decision,
				"reason":   result.Reason,
			}),
		})
		if err != nil {
			return DecisionResult{}, err
		}
		result.AuditEventID = event.ID
	}
	return result, nil
}

func (s *Service) RequireAllowed(ctx context.Context, command EvaluateCommand) error {
	result, err := s.Evaluate(ctx, command)
	if err != nil {
		return err
	}
	if result.Decision != DecisionAllow {
		return fmt.Errorf("%w: %s", ErrDenied, result.Reason)
	}
	return nil
}

func evaluateDecision(command EvaluateCommand, module string, capability string) DecisionResult {
	if module == "" || capability == "" {
		return DecisionResult{Decision: DecisionDeny, Reason: "module and capability are required"}
	}
	if isHardDenied(module, capability) {
		return DecisionResult{Decision: DecisionDeny, Reason: "capability violates source-of-truth policy"}
	}
	if !isKnownModule(module) {
		return DecisionResult{Decision: DecisionDeny, Reason: "unknown module"}
	}
	if !isKnownCapability(capability) {
		return DecisionResult{Decision: DecisionDeny, Reason: "unknown capability"}
	}
	if !isAllowed(module, capability) {
		return DecisionResult{Decision: DecisionDeny, Reason: "capability is not allowed for module"}
	}
	if module == ModuleFinance && capability == CapabilityWriteAppDB &&
		(command.HighImpact || command.Ambiguous || command.LowConfidence || command.MoneyMovement) {
		return DecisionResult{Decision: DecisionRequireConfirmation, Reason: "finance write requires confirmation"}
	}
	return DecisionResult{Decision: DecisionAllow, Reason: "capability allowed"}
}

func isKnownModule(module string) bool {
	switch module {
	case ModuleFinance, ModuleSecondBrain, ModuleHomelab:
		return true
	default:
		return false
	}
}

func isKnownCapability(capability string) bool {
	switch capability {
	case CapabilityRead, CapabilityRAGQuery, CapabilityCapture, CapabilityWriteAppDB,
		CapabilityWriteExternalSource, CapabilitySyncFromExternal, CapabilityIndexExternalSource,
		CapabilityExecuteRuntime, CapabilityManagePolicy:
		return true
	default:
		return false
	}
}

func isHardDenied(module string, capability string) bool {
	if capability == CapabilityExecuteRuntime || capability == CapabilityManagePolicy {
		return true
	}
	return (module == ModuleHomelab && capability == CapabilityWriteExternalSource) ||
		(module == ModuleSecondBrain && capability == CapabilityWriteExternalSource)
}

func isAllowed(module string, capability string) bool {
	matrix := map[string]map[string]bool{
		ModuleFinance: {
			CapabilityRead:       true,
			CapabilityWriteAppDB: true,
		},
		ModuleSecondBrain: {
			CapabilityRead:                true,
			CapabilityRAGQuery:            true,
			CapabilityCapture:             true,
			CapabilityWriteAppDB:          true,
			CapabilityIndexExternalSource: true,
		},
		ModuleHomelab: {
			CapabilityRead:                true,
			CapabilityRAGQuery:            true,
			CapabilityWriteAppDB:          true,
			CapabilitySyncFromExternal:    true,
			CapabilityIndexExternalSource: true,
		},
	}
	return matrix[module][capability]
}

func shouldAudit(command EvaluateCommand, decision string) bool {
	if decision != DecisionAllow {
		return true
	}
	if command.AuditRead && command.Capability == CapabilityRead {
		return true
	}
	switch command.Capability {
	case CapabilityWriteAppDB, CapabilityWriteExternalSource, CapabilitySyncFromExternal,
		CapabilityIndexExternalSource, CapabilityRAGQuery, CapabilityExecuteRuntime, CapabilityManagePolicy:
		return true
	default:
		return false
	}
}

func eventTypeForDecision(decision string) string {
	switch decision {
	case DecisionDeny:
		return "PermissionDenied"
	case DecisionRequireConfirmation:
		return "ConfirmationRequested"
	default:
		return "PermissionAllowed"
	}
}

func auditStatusForDecision(decision string) string {
	switch decision {
	case DecisionDeny:
		return "denied"
	case DecisionRequireConfirmation:
		return "skipped"
	default:
		return "success"
	}
}

func defaultString(value string, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return strings.TrimSpace(value)
}

func mergeMetadata(base map[string]any, overlay map[string]any) map[string]any {
	merged := map[string]any{}
	for key, value := range base {
		merged[key] = value
	}
	for key, value := range overlay {
		merged[key] = value
	}
	return merged
}
