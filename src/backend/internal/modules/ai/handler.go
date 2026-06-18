package ai

import (
	"context"
	"net/http"
	"time"

	grpcclient "cortex/internal/infrastructure/grpc"
	"cortex/internal/infrastructure/grpc/pb"

	"github.com/labstack/echo/v4"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

const defaultOwnerID = "owner"

type Handler struct {
	client  *grpcclient.AIServiceClient
	timeout time.Duration
}

func RegisterRoutes(e *echo.Echo, client *grpcclient.AIServiceClient) {
	NewHandler(client).Register(e)
}

func NewHandler(client *grpcclient.AIServiceClient) *Handler {
	return &Handler{client: client, timeout: 15 * time.Second}
}

func (h *Handler) Register(e *echo.Echo) {
	e.GET("/api/ai/health", h.health)

	e.POST("/api/secondbrain/captures", h.createCapture)
	e.GET("/api/secondbrain/captures", h.listCaptures)
	e.GET("/api/secondbrain/status", h.secondBrainStatus)
	e.POST("/api/secondbrain/search", h.searchSecondBrain)

	e.POST("/api/homelab/sync", h.syncHomelab)
	e.POST("/api/homelab/search", h.searchHomelab)
	e.POST("/api/homelab/validate-links", h.validateHomelabLinks)
}

type createCaptureRequest struct {
	RawText string `json:"raw_text"`
	Source  string `json:"source"`
	OwnerID string `json:"owner_id"`
}

type searchRequest struct {
	Query   string `json:"query"`
	OwnerID string `json:"owner_id"`
	TopK    int32  `json:"top_k"`
}

type syncHomelabRequest struct {
	RepoPath  string `json:"repo_path"`
	RepoURL   string `json:"repo_url"`
	Branch    string `json:"branch"`
	CommitSHA string `json:"commit_sha"`
	OwnerID   string `json:"owner_id"`
}

type validateLinksRequest struct {
	RepoPath string `json:"repo_path"`
}

func (h *Handler) health(c echo.Context) error {
	ctx, cancel := h.context(c)
	defer cancel()

	sb, err := h.client.SecondBrain.HealthCheck(ctx, &pb.HealthCheckRequest{})
	if err != nil {
		return writeGRPCError(c, err)
	}
	hl, err := h.client.Homelab.HealthCheck(ctx, &pb.HealthCheckRequest{})
	if err != nil {
		return writeGRPCError(c, err)
	}
	return c.JSON(http.StatusOK, map[string]string{
		"status":       "ok",
		"second_brain": sb.GetStatus(),
		"homelab":      hl.GetStatus(),
	})
}

func (h *Handler) createCapture(c echo.Context) error {
	var req createCaptureRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, errorBody("invalid_json", err.Error()))
	}
	if req.Source == "" {
		req.Source = "gateway"
	}
	ctx, cancel := h.context(c)
	defer cancel()

	resp, err := h.client.SecondBrain.CreateCapture(ctx, &pb.CreateCaptureRequest{
		RawText: req.RawText,
		Source:  req.Source,
		OwnerId: ownerID(req.OwnerID),
	})
	if err != nil {
		return writeGRPCError(c, err)
	}
	return c.JSON(http.StatusCreated, map[string]any{"capture": captureMap(resp.GetCapture())})
}

func (h *Handler) listCaptures(c echo.Context) error {
	ctx, cancel := h.context(c)
	defer cancel()

	resp, err := h.client.SecondBrain.ListCaptures(ctx, &pb.ListCapturesRequest{OwnerId: ownerID(c.QueryParam("owner_id"))})
	if err != nil {
		return writeGRPCError(c, err)
	}
	captures := make([]map[string]any, 0, len(resp.GetCaptures()))
	for _, capture := range resp.GetCaptures() {
		captures = append(captures, captureMap(capture))
	}
	return c.JSON(http.StatusOK, map[string]any{"captures": captures})
}

func (h *Handler) secondBrainStatus(c echo.Context) error {
	ctx, cancel := h.context(c)
	defer cancel()

	resp, err := h.client.SecondBrain.GetSyncStatus(ctx, &pb.GetSyncStatusRequest{OwnerId: ownerID(c.QueryParam("owner_id"))})
	if err != nil {
		return writeGRPCError(c, err)
	}
	return c.JSON(http.StatusOK, map[string]any{
		"total_documents":   resp.GetTotalDocuments(),
		"indexed_documents": resp.GetIndexedDocuments(),
		"total_chunks":      resp.GetTotalChunks(),
	})
}

func (h *Handler) searchSecondBrain(c echo.Context) error {
	var req searchRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, errorBody("invalid_json", err.Error()))
	}
	ctx, cancel := h.context(c)
	defer cancel()

	resp, err := h.client.SecondBrain.SearchSecondBrain(ctx, &pb.SearchRequest{
		Query:   req.Query,
		OwnerId: ownerID(req.OwnerID),
		TopK:    req.TopK,
	})
	if err != nil {
		return writeGRPCError(c, err)
	}
	return c.JSON(http.StatusOK, map[string]any{"results": searchResultMaps(resp.GetResults())})
}

func (h *Handler) syncHomelab(c echo.Context) error {
	var req syncHomelabRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, errorBody("invalid_json", err.Error()))
	}
	ctx, cancel := h.context(c)
	defer cancel()

	resp, err := h.client.Homelab.SyncHomelab(ctx, &pb.SyncHomelabRequest{
		RepoPath:  req.RepoPath,
		RepoUrl:   req.RepoURL,
		Branch:    req.Branch,
		CommitSha: req.CommitSHA,
		OwnerId:   ownerID(req.OwnerID),
	})
	if err != nil {
		return writeGRPCError(c, err)
	}
	return c.JSON(http.StatusOK, map[string]any{
		"status":          resp.GetStatus(),
		"processed_files": resp.GetProcessedFiles(),
		"skipped_files":   resp.GetSkippedFiles(),
		"failed_files":    resp.GetFailedFiles(),
	})
}

func (h *Handler) searchHomelab(c echo.Context) error {
	var req searchRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, errorBody("invalid_json", err.Error()))
	}
	ctx, cancel := h.context(c)
	defer cancel()

	resp, err := h.client.Homelab.SearchHomelab(ctx, &pb.SearchRequest{
		Query:   req.Query,
		OwnerId: ownerID(req.OwnerID),
		TopK:    req.TopK,
	})
	if err != nil {
		return writeGRPCError(c, err)
	}
	return c.JSON(http.StatusOK, map[string]any{"results": searchResultMaps(resp.GetResults())})
}

func (h *Handler) validateHomelabLinks(c echo.Context) error {
	var req validateLinksRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, errorBody("invalid_json", err.Error()))
	}
	ctx, cancel := h.context(c)
	defer cancel()

	resp, err := h.client.Homelab.ValidateLinks(ctx, &pb.ValidateLinksRequest{RepoPath: req.RepoPath})
	if err != nil {
		return writeGRPCError(c, err)
	}
	links := make([]map[string]any, 0, len(resp.GetBrokenLinks()))
	for _, link := range resp.GetBrokenLinks() {
		links = append(links, map[string]any{
			"source_file": link.GetSourceFile(),
			"line_number": link.GetLineNumber(),
			"raw_link":    link.GetRawLink(),
			"reason":      link.GetReason(),
		})
	}
	return c.JSON(http.StatusOK, map[string]any{"status": resp.GetStatus(), "broken_links": links})
}

func (h *Handler) context(c echo.Context) (context.Context, context.CancelFunc) {
	return context.WithTimeout(c.Request().Context(), h.timeout)
}

func ownerID(value string) string {
	if value == "" {
		return defaultOwnerID
	}
	return value
}

func writeGRPCError(c echo.Context, err error) error {
	st, ok := status.FromError(err)
	if !ok {
		return c.JSON(http.StatusBadGateway, errorBody("grpc_error", err.Error()))
	}
	statusCode := http.StatusBadGateway
	switch st.Code() {
	case codes.InvalidArgument:
		statusCode = http.StatusBadRequest
	case codes.NotFound:
		statusCode = http.StatusNotFound
	case codes.Unavailable, codes.DeadlineExceeded:
		statusCode = http.StatusServiceUnavailable
	}
	return c.JSON(statusCode, errorBody(st.Code().String(), st.Message()))
}

func errorBody(code string, message string) map[string]string {
	return map[string]string{"error": code, "message": message}
}

func captureMap(capture *pb.CaptureRecord) map[string]any {
	if capture == nil {
		return map[string]any{}
	}
	return map[string]any{
		"id":                  capture.GetId(),
		"status":              capture.GetStatus(),
		"raw_text":            capture.GetRawText(),
		"normalized_markdown": capture.GetNormalizedMarkdown(),
		"vault_path":          capture.GetVaultPath(),
		"created_at":          capture.GetCreatedAt(),
	}
}

func searchResultMaps(results []*pb.SearchResult) []map[string]any {
	out := make([]map[string]any, 0, len(results))
	for _, result := range results {
		out = append(out, map[string]any{
			"score":    result.GetScore(),
			"chunk":    chunkMap(result.GetChunk()),
			"document": documentMap(result.GetDocument()),
		})
	}
	return out
}

func chunkMap(chunk *pb.ChunkMetadata) map[string]any {
	if chunk == nil {
		return map[string]any{}
	}
	return map[string]any{
		"id":            chunk.GetId(),
		"document_id":   chunk.GetDocumentId(),
		"owner_id":      chunk.GetOwnerId(),
		"file_path":     chunk.GetFilePath(),
		"chunk_index":   chunk.GetChunkIndex(),
		"content":       chunk.GetContent(),
		"heading_chain": chunk.GetHeadingChain(),
		"token_count":   chunk.GetTokenCount(),
	}
}

func documentMap(document *pb.DocumentMetadata) map[string]any {
	if document == nil {
		return map[string]any{}
	}
	return map[string]any{
		"id":           document.GetId(),
		"owner_id":     document.GetOwnerId(),
		"repo_url":     document.GetRepoUrl(),
		"branch":       document.GetBranch(),
		"commit_sha":   document.GetCommitSha(),
		"file_path":    document.GetFilePath(),
		"checksum":     document.GetChecksum(),
		"index_status": document.GetIndexStatus(),
		"indexed_at":   document.GetIndexedAt(),
	}
}
