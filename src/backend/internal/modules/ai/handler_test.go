package ai

import (
	"bytes"
	"context"
	"encoding/json"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"

	grpcclient "cortex/internal/infrastructure/grpc"
	"cortex/internal/infrastructure/grpc/pb"

	"github.com/labstack/echo/v4"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
	"google.golang.org/grpc/test/bufconn"
)

const bufSize = 1024 * 1024

type fakeAIServer struct {
	pb.UnimplementedSecondBrainServiceServer
	pb.UnimplementedHomelabServiceServer

	lastOwnerID  string
	lastRepoPath string
}

func (s *fakeAIServer) HealthCheck(context.Context, *pb.HealthCheckRequest) (*pb.HealthCheckResponse, error) {
	return &pb.HealthCheckResponse{Status: "ok"}, nil
}

func (s *fakeAIServer) CreateCapture(_ context.Context, req *pb.CreateCaptureRequest) (*pb.CreateCaptureResponse, error) {
	if req.GetRawText() == "" {
		return nil, status.Error(codes.InvalidArgument, "raw_text is required")
	}
	s.lastOwnerID = req.GetOwnerId()
	return &pb.CreateCaptureResponse{Capture: &pb.CaptureRecord{
		Id:                 "cap-1",
		Status:             "captured",
		RawText:            req.GetRawText(),
		NormalizedMarkdown: "normalized",
		CreatedAt:          "2026-06-18T00:00:00Z",
	}}, nil
}

func (s *fakeAIServer) ListCaptures(_ context.Context, req *pb.ListCapturesRequest) (*pb.ListCapturesResponse, error) {
	s.lastOwnerID = req.GetOwnerId()
	return &pb.ListCapturesResponse{Captures: []*pb.CaptureRecord{{Id: "cap-1", Status: "captured"}}}, nil
}

func (s *fakeAIServer) GetSyncStatus(_ context.Context, req *pb.GetSyncStatusRequest) (*pb.GetSyncStatusResponse, error) {
	s.lastOwnerID = req.GetOwnerId()
	return &pb.GetSyncStatusResponse{TotalDocuments: 2, IndexedDocuments: 1, TotalChunks: 3}, nil
}

func (s *fakeAIServer) SearchSecondBrain(_ context.Context, req *pb.SearchRequest) (*pb.SearchResponse, error) {
	s.lastOwnerID = req.GetOwnerId()
	return searchResponse("vault/note.md"), nil
}

func (s *fakeAIServer) SyncHomelab(_ context.Context, req *pb.SyncHomelabRequest) (*pb.SyncHomelabResponse, error) {
	s.lastOwnerID = req.GetOwnerId()
	s.lastRepoPath = req.GetRepoPath()
	return &pb.SyncHomelabResponse{Status: "success", ProcessedFiles: 1}, nil
}

func (s *fakeAIServer) SearchHomelab(_ context.Context, req *pb.SearchRequest) (*pb.SearchResponse, error) {
	s.lastOwnerID = req.GetOwnerId()
	return searchResponse("README.md"), nil
}

func (s *fakeAIServer) ValidateLinks(_ context.Context, req *pb.ValidateLinksRequest) (*pb.ValidateLinksResponse, error) {
	s.lastRepoPath = req.GetRepoPath()
	return &pb.ValidateLinksResponse{
		Status:      "completed",
		BrokenLinks: []*pb.BrokenLink{{SourceFile: "README.md", LineNumber: 2, RawLink: "./missing.md", Reason: "missing_file"}},
	}, nil
}

func TestGatewayRoutesProxyToGRPCAndInjectDefaultOwner(t *testing.T) {
	e, server := newTestGateway(t)

	statusCode, body := requestJSON(t, e, http.MethodPost, "/api/secondbrain/captures", map[string]any{
		"raw_text": "capture me",
	})
	if statusCode != http.StatusCreated {
		t.Fatalf("expected 201, got %d body=%s", statusCode, body)
	}
	if server.lastOwnerID != defaultOwnerID {
		t.Fatalf("expected default owner %q, got %q", defaultOwnerID, server.lastOwnerID)
	}

	statusCode, body = requestJSON(t, e, http.MethodPost, "/api/secondbrain/search", map[string]any{
		"query":    "rag",
		"owner_id": "custom-owner",
		"top_k":    3,
	})
	if statusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d body=%s", statusCode, body)
	}
	if server.lastOwnerID != "custom-owner" {
		t.Fatalf("expected explicit owner to pass through, got %q", server.lastOwnerID)
	}

	statusCode, body = requestJSON(t, e, http.MethodPost, "/api/homelab/sync", map[string]any{
		"repo_path": "/tmp/homelab",
	})
	if statusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d body=%s", statusCode, body)
	}
	if server.lastOwnerID != defaultOwnerID || server.lastRepoPath != "/tmp/homelab" {
		t.Fatalf("unexpected homelab request owner=%q repo=%q", server.lastOwnerID, server.lastRepoPath)
	}

	statusCode, body = requestJSON(t, e, http.MethodPost, "/api/homelab/validate-links", map[string]any{
		"repo_path": "/tmp/homelab",
	})
	if statusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d body=%s", statusCode, body)
	}
	var payload map[string]any
	if err := json.Unmarshal(body, &payload); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if payload["status"] != "completed" {
		t.Fatalf("unexpected validate status: %v", payload["status"])
	}
}

func TestGatewayMapsGRPCInvalidArgumentToHTTP400(t *testing.T) {
	e, _ := newTestGateway(t)

	statusCode, body := requestJSON(t, e, http.MethodPost, "/api/secondbrain/captures", map[string]any{})
	if statusCode != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d body=%s", statusCode, body)
	}
}

func newTestGateway(t *testing.T) (*echo.Echo, *fakeAIServer) {
	t.Helper()

	listener := bufconn.Listen(bufSize)
	grpcServer := grpc.NewServer()
	fake := &fakeAIServer{}
	pb.RegisterSecondBrainServiceServer(grpcServer, fake)
	pb.RegisterHomelabServiceServer(grpcServer, fake)

	go func() {
		if err := grpcServer.Serve(listener); err != nil {
			t.Errorf("serve fake grpc: %v", err)
		}
	}()
	t.Cleanup(grpcServer.Stop)
	t.Cleanup(func() { _ = listener.Close() })

	conn, err := grpc.DialContext(
		context.Background(),
		"bufnet",
		grpc.WithContextDialer(func(context.Context, string) (net.Conn, error) {
			return listener.Dial()
		}),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		t.Fatalf("dial bufconn: %v", err)
	}
	t.Cleanup(func() { _ = conn.Close() })

	e := echo.New()
	RegisterRoutes(e, grpcclient.NewAIServiceClientFromConn(conn))
	return e, fake
}

func requestJSON(t *testing.T, e *echo.Echo, method string, path string, payload map[string]any) (int, []byte) {
	t.Helper()
	body, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal request: %v", err)
	}
	req := httptest.NewRequest(method, path, bytes.NewReader(body))
	req.Header.Set(echo.HeaderContentType, echo.MIMEApplicationJSON)
	rec := httptest.NewRecorder()
	e.ServeHTTP(rec, req)
	return rec.Code, rec.Body.Bytes()
}

func searchResponse(path string) *pb.SearchResponse {
	return &pb.SearchResponse{Results: []*pb.SearchResult{{
		Score: 0.9,
		Document: &pb.DocumentMetadata{
			Id:          "doc-1",
			OwnerId:     defaultOwnerID,
			FilePath:    path,
			IndexStatus: "indexed",
		},
		Chunk: &pb.ChunkMetadata{
			Id:           "chunk-1",
			DocumentId:   "doc-1",
			OwnerId:      defaultOwnerID,
			FilePath:     path,
			ChunkIndex:   0,
			Content:      "content",
			TokenCount:   1,
			HeadingChain: []string{"H1"},
		},
	}}}
}
