"""Standardized error responses per API_CONVENTIONS.md."""

from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    """Create a standardized API error response."""
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": details or {}}},
    )


# Common error factories
def not_found(resource: str = "Resource") -> HTTPException:
    return api_error(404, "NOT_FOUND", f"{resource} not found")


def forbidden(message: str = "Access denied") -> HTTPException:
    return api_error(403, "INSUFFICIENT_PERMISSIONS", message)


def bad_request(code: str, message: str, details: dict | None = None) -> HTTPException:
    return api_error(400, code, message, details)


def validation_error(message: str = "Validation failed", details: dict | None = None) -> HTTPException:
    return api_error(422, "VALIDATION_ERROR", message, details)


def conflict(message: str = "Conflict") -> HTTPException:
    return api_error(409, "CONFLICT", message)