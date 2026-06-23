package audit

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"time"

	"gorm.io/gorm"
)

var (
	ErrInvalidEvent = errors.New("invalid audit event")
	ErrSecretRef    = errors.New("audit event contains secret-looking key")
)

type Service struct {
	db  *gorm.DB
	now func() time.Time
}

func NewService(db *gorm.DB) *Service {
	return &Service{db: db, now: func() time.Time { return time.Now().UTC() }}
}

func (s *Service) AppendEvent(ctx context.Context, command AppendEventCommand) (Event, error) {
	if err := validateAppendCommand(command); err != nil {
		return Event{}, err
	}
	event := Event{
		ID:             newEventID(),
		EventType:      normalizeRequired(command.EventType),
		Module:         normalizeRequired(command.Module),
		ActorType:      normalizeRequired(command.ActorType),
		ActorID:        normalizeRequired(command.ActorID),
		ConversationID: strings.TrimSpace(command.ConversationID),
		RequestID:      strings.TrimSpace(command.RequestID),
		ToolName:       strings.TrimSpace(command.ToolName),
		Capability:     strings.TrimSpace(command.Capability),
		SourceRef:      nonNilJSONMap(command.SourceRef),
		TargetRef:      nonNilJSONMap(command.TargetRef),
		Status:         normalizeRequired(command.Status),
		Metadata:       nonNilJSONMap(command.Metadata),
		CreatedAt:      s.now(),
	}
	if err := s.db.WithContext(ctx).Create(&event).Error; err != nil {
		return Event{}, err
	}
	return event, nil
}

func newEventID() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return fmt.Sprintf("audit_%d", time.Now().UTC().UnixNano())
	}
	return "audit_" + hex.EncodeToString(b[:])
}

func (s *Service) GetEvent(ctx context.Context, id string) (Event, error) {
	var event Event
	if err := s.db.WithContext(ctx).Where("id = ?", id).First(&event).Error; err != nil {
		return Event{}, err
	}
	return event, nil
}

func (s *Service) ListEvents(ctx context.Context, query ListEventsQuery) ([]Event, error) {
	db := s.db.WithContext(ctx).Model(&Event{}).Order("created_at DESC")
	if query.Module != "" {
		db = db.Where("module = ?", query.Module)
	}
	if query.EventType != "" {
		db = db.Where("event_type = ?", query.EventType)
	}
	if query.RequestID != "" {
		db = db.Where("request_id = ?", query.RequestID)
	}
	limit := query.Limit
	if limit <= 0 || limit > 500 {
		limit = 100
	}
	var events []Event
	if err := db.Limit(limit).Find(&events).Error; err != nil {
		return nil, err
	}
	return events, nil
}

func (s *Service) ListEventsByRequest(ctx context.Context, requestID string) ([]Event, error) {
	return s.ListEvents(ctx, ListEventsQuery{RequestID: requestID})
}

func (s *Service) ListModuleTimeline(ctx context.Context, module string, query ListEventsQuery) ([]Event, error) {
	query.Module = module
	return s.ListEvents(ctx, query)
}

func validateAppendCommand(command AppendEventCommand) error {
	missing := []string{}
	if normalizeRequired(command.EventType) == "" {
		missing = append(missing, "event_type")
	}
	if normalizeRequired(command.Module) == "" {
		missing = append(missing, "module")
	}
	if normalizeRequired(command.ActorType) == "" {
		missing = append(missing, "actor_type")
	}
	if normalizeRequired(command.ActorID) == "" {
		missing = append(missing, "actor_id")
	}
	if normalizeRequired(command.Status) == "" {
		missing = append(missing, "status")
	}
	if len(missing) > 0 {
		return fmt.Errorf("%w: missing %s", ErrInvalidEvent, strings.Join(missing, ", "))
	}
	switch normalizeRequired(command.Status) {
	case StatusSuccess, StatusFailed, StatusDenied, StatusSkipped:
	default:
		return fmt.Errorf("%w: unsupported status %q", ErrInvalidEvent, command.Status)
	}
	for label, ref := range map[string]JSONMap{
		"metadata":   command.Metadata,
		"source_ref": command.SourceRef,
		"target_ref": command.TargetRef,
	} {
		if key := findSecretKey(ref); key != "" {
			return fmt.Errorf("%w: %s.%s", ErrSecretRef, label, key)
		}
	}
	return nil
}

func nonNilJSONMap(value JSONMap) JSONMap {
	if value == nil {
		return JSONMap{}
	}
	return value
}

func findSecretKey(value any) string {
	switch typed := value.(type) {
	case JSONMap:
		for key, item := range typed {
			if isSecretKey(key) {
				return key
			}
			if nested := findSecretKey(item); nested != "" {
				return key + "." + nested
			}
		}
	case map[string]any:
		for key, item := range typed {
			if isSecretKey(key) {
				return key
			}
			if nested := findSecretKey(item); nested != "" {
				return key + "." + nested
			}
		}
	case []any:
		for _, item := range typed {
			if nested := findSecretKey(item); nested != "" {
				return nested
			}
		}
	}
	return ""
}

func isSecretKey(key string) bool {
	normalized := strings.ToLower(strings.ReplaceAll(strings.ReplaceAll(key, "-", "_"), " ", "_"))
	secretFragments := []string{"password", "token", "secret", "api_key", "apikey", "authorization", "credential"}
	for _, fragment := range secretFragments {
		if strings.Contains(normalized, fragment) {
			return true
		}
	}
	return false
}
