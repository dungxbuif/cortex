package system

import (
	"context"

	"cortex/internal/infrastructure/grpc/pb"
	"cortex/internal/modules/system/audit"
	"cortex/internal/modules/system/policy"
)

type PolicyEvaluator interface {
	Evaluate(context.Context, policy.EvaluateCommand) (policy.DecisionResult, error)
}

type AuditAppender interface {
	AppendEvent(context.Context, audit.AppendEventCommand) (audit.Event, error)
}

type AuditPolicyAdapter struct {
	Audit AuditAppender
}

func (a AuditPolicyAdapter) AppendEvent(ctx context.Context, command policy.AuditEventCommand) (policy.AuditEvent, error) {
	event, err := a.Audit.AppendEvent(ctx, audit.AppendEventCommand{
		EventType:      command.EventType,
		Module:         command.Module,
		ActorType:      command.ActorType,
		ActorID:        command.ActorID,
		ConversationID: command.ConversationID,
		RequestID:      command.RequestID,
		ToolName:       command.ToolName,
		Capability:     command.Capability,
		SourceRef:      toAuditJSONMap(command.SourceRef),
		TargetRef:      toAuditJSONMap(command.TargetRef),
		Status:         command.Status,
		Metadata:       toAuditJSONMap(command.Metadata),
	})
	if err != nil {
		return policy.AuditEvent{}, err
	}
	return policy.AuditEvent{ID: event.ID}, nil
}

type PolicyServicer struct {
	pb.UnimplementedPolicyServiceServer
	Service PolicyEvaluator
}

func (s PolicyServicer) HealthCheck(context.Context, *pb.HealthCheckRequest) (*pb.HealthCheckResponse, error) {
	return &pb.HealthCheckResponse{Status: "ok"}, nil
}

func (s PolicyServicer) EvaluatePolicy(ctx context.Context, req *pb.EvaluatePolicyRequest) (*pb.EvaluatePolicyResponse, error) {
	result, err := s.Service.Evaluate(ctx, policy.EvaluateCommand{
		Module:         req.GetModule(),
		Capability:     req.GetCapability(),
		ActorType:      req.GetActorType(),
		ActorID:        req.GetActorId(),
		ConversationID: req.GetConversationId(),
		RequestID:      req.GetRequestId(),
		ToolName:       req.GetToolName(),
		HighImpact:     req.GetHighImpact(),
		Ambiguous:      req.GetAmbiguous(),
		LowConfidence:  req.GetLowConfidence(),
		MoneyMovement:  req.GetMoneyMovement(),
		AuditRead:      req.GetAuditRead(),
		SourceRef:      entriesToMap(req.GetSourceRef()),
		TargetRef:      entriesToMap(req.GetTargetRef()),
		Metadata:       entriesToMap(req.GetMetadata()),
	})
	if err != nil {
		return nil, err
	}
	return &pb.EvaluatePolicyResponse{
		Decision:     result.Decision,
		Reason:       result.Reason,
		AuditEventId: result.AuditEventID,
	}, nil
}

type AuditServicer struct {
	pb.UnimplementedAuditServiceServer
	Service AuditAppender
}

func (s AuditServicer) HealthCheck(context.Context, *pb.HealthCheckRequest) (*pb.HealthCheckResponse, error) {
	return &pb.HealthCheckResponse{Status: "ok"}, nil
}

func (s AuditServicer) AppendAuditEvent(ctx context.Context, req *pb.AppendAuditEventRequest) (*pb.AppendAuditEventResponse, error) {
	event, err := s.Service.AppendEvent(ctx, audit.AppendEventCommand{
		EventType:      req.GetEventType(),
		Module:         req.GetModule(),
		ActorType:      req.GetActorType(),
		ActorID:        req.GetActorId(),
		ConversationID: req.GetConversationId(),
		RequestID:      req.GetRequestId(),
		ToolName:       req.GetToolName(),
		Capability:     req.GetCapability(),
		SourceRef:      toAuditJSONMap(entriesToMap(req.GetSourceRef())),
		TargetRef:      toAuditJSONMap(entriesToMap(req.GetTargetRef())),
		Status:         req.GetStatus(),
		Metadata:       toAuditJSONMap(entriesToMap(req.GetMetadata())),
	})
	if err != nil {
		return nil, err
	}
	return &pb.AppendAuditEventResponse{AuditEventId: event.ID}, nil
}

func entriesToMap(entries []*pb.StringMapEntry) map[string]any {
	out := map[string]any{}
	for _, entry := range entries {
		out[entry.GetKey()] = entry.GetValue()
	}
	return out
}

func toAuditJSONMap(values map[string]any) audit.JSONMap {
	out := audit.JSONMap{}
	for key, value := range values {
		out[key] = value
	}
	return out
}
