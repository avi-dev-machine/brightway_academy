"""Application-specific exceptions. Each maps to a stable error code and HTTP status."""

from typing import Any


class AppError(Exception):
    status_code: int = 400
    code: str = "APP_ERROR"
    message: str = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "The requested resource was not found."


class StudentNotFoundError(NotFoundError):
    code = "STUDENT_NOT_FOUND"
    message = "Student was not found."


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "The request conflicts with existing data."


class DuplicateStudentError(ConflictError):
    code = "DUPLICATE_STUDENT"
    message = "A student with this ID No. already exists."


class InvalidStateError(ConflictError):
    code = "INVALID_STATE"
    message = "This action is not allowed in the current state."


class ValidationFailedError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "The request contains invalid data."


class InvalidCSVError(ValidationFailedError):
    code = "INVALID_CSV"
    message = "The CSV file is invalid."


class FileValidationError(ValidationFailedError):
    code = "INVALID_FILE"
    message = "The uploaded file is invalid."


class PaymentVerificationError(AppError):
    status_code = 400
    code = "PAYMENT_VERIFICATION_FAILED"
    message = "Payment could not be verified."


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"
    message = "Authentication is required."


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Too many requests. Please try again later."


class ReceiptGenerationError(AppError):
    status_code = 500
    code = "RECEIPT_GENERATION_FAILED"
    message = "The receipt could not be generated."


class ExternalServiceError(AppError):
    status_code = 502
    code = "EXTERNAL_SERVICE_ERROR"
    message = "An external service failed. Please try again later."


class ServiceNotConfiguredError(AppError):
    status_code = 503
    code = "SERVICE_NOT_CONFIGURED"
    message = "This feature is not configured yet."
