package audit

import (
	"context"
	"database/sql/driver"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

const (
	StatusSuccess = "success"
	StatusFailed  = "failed"
	StatusDenied  = "denied"
	StatusSkipped = "skipped"
)

type JSONMap map[string]any

func (m JSONMap) Value() (driver.Value, error) {
	if m == nil {
		return []byte("{}"), nil
	}
	return json.Marshal(map[string]any(m))
}

func (m *JSONMap) Scan(value any) error {
	if value == nil {
		*m = JSONMap{}
		return nil
	}
	var raw []byte
	switch typed := value.(type) {
	case []byte:
		raw = typed
	case string:
		raw = []byte(typed)
	default:
		return fmt.Errorf("unsupported JSONMap scan type %T", value)
	}
	var decoded map[string]any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return err
	}
	*m = JSONMap(decoded)
	return nil
}

type Event struct {
	ID             string    `gorm:"column:id;primaryKey"`
	EventType      string    `gorm:"column:event_type"`
	Module         string    `gorm:"column:module"`
	ActorType      string    `gorm:"column:actor_type"`
	ActorID        string    `gorm:"column:actor_id"`
	ConversationID string    `gorm:"column:conversation_id"`
	RequestID      string    `gorm:"column:request_id"`
	ToolName       string    `gorm:"column:tool_name"`
	Capability     string    `gorm:"column:capability"`
	SourceRef      JSONMap   `gorm:"column:source_ref;type:jsonb"`
	TargetRef      JSONMap   `gorm:"column:target_ref;type:jsonb"`
	Status         string    `gorm:"column:status"`
	Metadata       JSONMap   `gorm:"column:metadata;type:jsonb"`
	CreatedAt      time.Time `gorm:"column:created_at"`
}

func (Event) TableName() string {
	return "audit_events"
}

type AppendEventCommand struct {
	EventType      string
	Module         string
	ActorType      string
	ActorID        string
	ConversationID string
	RequestID      string
	ToolName       string
	Capability     string
	SourceRef      JSONMap
	TargetRef      JSONMap
	Status         string
	Metadata       JSONMap
}

type ListEventsQuery struct {
	Module    string
	EventType string
	RequestID string
	Limit     int
}

type EventSink interface {
	AppendEvent(ctx context.Context, command AppendEventCommand) (Event, error)
}

func normalizeRequired(value string) string {
	return strings.TrimSpace(value)
}
