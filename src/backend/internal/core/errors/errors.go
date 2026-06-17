package errors

import "fmt"

const (
	CodeValidationError   = "VALIDATION_ERROR"
	CodeNotFound          = "NOT_FOUND"
	CodeNeedsConfirmation = "NEEDS_CONFIRMATION"

	MsgValidationError = "Invalid input data"
	MsgNotFound        = "Resource %s not found"
)

type AppError struct {
	Code    string
	Message string
	Details interface{}
}

func (e *AppError) Error() string {
	return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

func NewValidationError(details interface{}) *AppError {
	return &AppError{
		Code:    CodeValidationError,
		Message: MsgValidationError,
		Details: details,
	}
}

func NewNotFoundError(resource string) *AppError {
	return &AppError{
		Code:    CodeNotFound,
		Message: fmt.Sprintf(MsgNotFound, resource),
	}
}

func NewNeedsConfirmationError(prompt string) *AppError {
	return &AppError{
		Code:    CodeNeedsConfirmation,
		Message: prompt,
	}
}
