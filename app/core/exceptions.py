"""DEV-367: Standardized API error responses.

Provides consistent error format across all endpoints for frontend handling.
All errors return: {"detail": str, "error_code": str, "status_code": int}.
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.logging import logger


class AppError(Exception):
    """Base application error with structured response."""

    def __init__(
        self,
        detail: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
    ) -> None:
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(detail)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, detail: str = "Risorsa non trovata.") -> None:
        super().__init__(detail=detail, error_code="NOT_FOUND", status_code=404)


class ValidationError(AppError):
    """Validation failure."""

    def __init__(self, detail: str = "Dati non validi.") -> None:
        super().__init__(detail=detail, error_code="VALIDATION_ERROR", status_code=400)


class ConflictError(AppError):
    """Conflict — duplicate resource."""

    def __init__(self, detail: str = "Conflitto: la risorsa esiste già.") -> None:
        super().__init__(detail=detail, error_code="CONFLICT", status_code=409)


class ForbiddenError(AppError):
    """Authorization failure."""

    def __init__(self, detail: str = "Accesso negato.") -> None:
        super().__init__(detail=detail, error_code="FORBIDDEN", status_code=403)


class TenantIsolationError(AppError):
    """Cross-tenant access attempt."""

    def __init__(self, detail: str = "Accesso negato: studio non autorizzato.") -> None:
        super().__init__(detail=detail, error_code="TENANT_ISOLATION", status_code=403)


class RateLimitError(AppError):
    """Rate limit exceeded."""

    def __init__(self, detail: str = "Limite richieste superato.") -> None:
        super().__init__(detail=detail, error_code="RATE_LIMITED", status_code=429)


# ---------------------------------------------------------------------------
# Error response schema (for OpenAPI docs)
# ---------------------------------------------------------------------------


class ErrorResponse:
    """Standard error response body."""

    def __init__(self, detail: str, error_code: str, status_code: int) -> None:
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            "detail": self.detail,
            "error_code": self.error_code,
            "status_code": self.status_code,
        }


# ---------------------------------------------------------------------------
# Exception handlers (register on FastAPI app)
# ---------------------------------------------------------------------------


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Handle AppError and subclasses with standard JSON body."""
    logger.warning(
        "app_error",
        error_code=exc.error_code,
        status_code=exc.status_code,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
        },
    )


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Wrap FastAPI HTTPException into standard format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc.detail),
            "error_code": "HTTP_ERROR",
            "status_code": exc.status_code,
        },
    )


async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled errors."""
    logger.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Errore interno del server.",
            "error_code": "INTERNAL_ERROR",
            "status_code": 500,
        },
    )
