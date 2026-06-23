package policy

import (
	"context"

	"cortex/internal/modules/system/audit"
)

type AuditServiceAdapter struct {
	Service *audit.Service
}

func (a AuditServiceAdapter) AppendEvent(ctx context.Context, command AuditEventCommand) (AuditEvent, error) {
	event, err := a.Service.AppendEvent(ctx, audit.AppendEventCommand{
		EventType:      command.EventType,
		Module:         command.Module,
		ActorType:      command.ActorType,
		ActorID:        command.ActorID,
		ConversationID: command.ConversationID,
		RequestID:      command.RequestID,
		ToolName:       command.ToolName,
		Capability:     command.Capability,
		SourceRef:      audit.JSONMap(command.SourceRef),
		TargetRef:      audit.JSONMap(command.TargetRef),
		Status:         command.Status,
		Metadata:       audit.JSONMap(command.Metadata),
	})
	if err != nil {
		return AuditEvent{}, err
	}
	return AuditEvent{ID: event.ID}, nil
}
