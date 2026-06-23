package system

import (
	"context"
	"net"
	"testing"

	"cortex/internal/infrastructure/grpc/pb"
	"cortex/internal/modules/system/audit"
	"cortex/internal/modules/system/policy"
	"google.golang.org/grpc"
	"google.golang.org/grpc/test/bufconn"
)

const bufSize = 1024 * 1024

type fakeAudit struct {
	events []audit.AppendEventCommand
}

func (f *fakeAudit) AppendEvent(ctx context.Context, command audit.AppendEventCommand) (audit.Event, error) {
	f.events = append(f.events, command)
	return audit.Event{ID: "audit-id"}, nil
}

func TestPolicyAndAuditGrpcServices(t *testing.T) {
	ctx := context.Background()
	auditSvc := &fakeAudit{}
	policySvc := policy.NewService(AuditPolicyAdapter{Audit: auditSvc})

	lis := bufconn.Listen(bufSize)
	server := grpc.NewServer()
	pb.RegisterPolicyServiceServer(server, PolicyServicer{Service: policySvc})
	pb.RegisterAuditServiceServer(server, AuditServicer{Service: auditSvc})
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

	policyClient := pb.NewPolicyServiceClient(conn)
	policyResp, err := policyClient.EvaluatePolicy(ctx, &pb.EvaluatePolicyRequest{
		Module:     policy.ModuleFinance,
		Capability: policy.CapabilityWriteAppDB,
		ActorType:  "user",
		ActorId:    "actor-1",
		RequestId:  "request-1",
		ToolName:   "finance_create_transaction",
		HighImpact: true,
		SourceRef:  []*pb.StringMapEntry{{Key: "channel", Value: "telegram"}},
		TargetRef:  []*pb.StringMapEntry{{Key: "wallet_id", Value: "wallet-1"}},
		Metadata:   []*pb.StringMapEntry{{Key: "test", Value: "true"}},
	})
	if err != nil {
		t.Fatalf("evaluate policy: %v", err)
	}
	if policyResp.GetDecision() != policy.DecisionRequireConfirmation {
		t.Fatalf("expected require_confirmation, got %q", policyResp.GetDecision())
	}
	if policyResp.GetAuditEventId() != "audit-id" {
		t.Fatalf("expected audit id, got %q", policyResp.GetAuditEventId())
	}
	if len(auditSvc.events) != 1 {
		t.Fatalf("expected policy audit event, got %d", len(auditSvc.events))
	}

	auditClient := pb.NewAuditServiceClient(conn)
	auditResp, err := auditClient.AppendAuditEvent(ctx, &pb.AppendAuditEventRequest{
		EventType: "ToolExecuted",
		Module:    policy.ModuleSecondBrain,
		ActorType: "user",
		ActorId:   "actor-1",
		Status:    audit.StatusSuccess,
		ToolName:  "secondbrain_capture_note",
	})
	if err != nil {
		t.Fatalf("append audit: %v", err)
	}
	if auditResp.GetAuditEventId() != "audit-id" {
		t.Fatalf("expected audit id, got %q", auditResp.GetAuditEventId())
	}
}
