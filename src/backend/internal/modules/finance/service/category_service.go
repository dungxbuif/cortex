package service

import (
	"context"
	"strings"

	appErrors "cortex/internal/core/errors"
	"cortex/internal/modules/finance/domain"
)

func (s *FinanceService) CreateCategory(ctx context.Context, cmd domain.CreateCategoryCommand) (*domain.Category, error) {
	ownerID, actorID := domain.NormalizeOwner(cmd.OwnerID), domain.NormalizeActor(cmd.ActorID)
	name := strings.TrimSpace(cmd.Name)
	if name == "" {
		return nil, appErrors.NewValidationError("category name is required")
	}
	if cmd.Type != domain.CategoryTypeIncome && cmd.Type != domain.CategoryTypeExpense {
		return nil, appErrors.NewValidationError("invalid category type")
	}
	if cmd.ParentID != nil {
		if _, err := s.getCategory(ctx, s.db, ownerID, *cmd.ParentID); err != nil {
			return nil, err
		}
	}
	var count int64
	q := s.db.WithContext(ctx).Model(&domain.Category{}).
		Where("owner_id = ? AND type = ? AND lower(name) = lower(?)", ownerID, cmd.Type, name)
	if cmd.ParentID == nil {
		q = q.Where("parent_id IS NULL")
	} else {
		q = q.Where("parent_id = ?", *cmd.ParentID)
	}
	if err := q.Count(&count).Error; err != nil {
		return nil, err
	}
	if count > 0 {
		return nil, appErrors.NewValidationError("category name must be unique per parent and type")
	}
	now := s.now()
	category := &domain.Category{
		ID:          domain.NewID("cat"),
		OwnerID:     ownerID,
		ParentID:    cmd.ParentID,
		Name:        name,
		Type:        cmd.Type,
		Aliases:     cmd.Aliases,
		Status:      "active",
		AuditFields: domain.NewAudit(actorID, now),
	}
	if err := s.db.WithContext(ctx).Create(category).Error; err != nil {
		return nil, err
	}
	return category, nil
}
