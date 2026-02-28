"""Tests for DEV-367: API Error Response Standardization."""

import pytest
from fastapi import HTTPException
from starlette.testclient import TestClient

from app.core.exceptions import (
    AppError,
    ConflictError,
    ErrorResponse,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    TenantIsolationError,
    ValidationError,
    app_error_handler,
    generic_exception_handler,
    http_exception_handler,
)

# ---------------------------------------------------------------------------
# AppError base class
# ---------------------------------------------------------------------------


class TestAppError:
    """Tests for the base AppError class."""

    def test_default_values(self):
        err = AppError(detail="test")
        assert err.detail == "test"
        assert err.error_code == "INTERNAL_ERROR"
        assert err.status_code == 500

    def test_custom_values(self):
        err = AppError(detail="custom", error_code="CUSTOM", status_code=418)
        assert err.detail == "custom"
        assert err.error_code == "CUSTOM"
        assert err.status_code == 418

    def test_is_exception(self):
        err = AppError(detail="err")
        assert isinstance(err, Exception)

    def test_str_representation(self):
        err = AppError(detail="message text")
        assert str(err) == "message text"


# ---------------------------------------------------------------------------
# Subclass errors
# ---------------------------------------------------------------------------


class TestNotFoundError:
    def test_defaults(self):
        err = NotFoundError()
        assert err.error_code == "NOT_FOUND"
        assert err.status_code == 404
        assert "non trovata" in err.detail

    def test_custom_detail(self):
        err = NotFoundError(detail="Cliente non trovato.")
        assert err.detail == "Cliente non trovato."


class TestValidationError:
    def test_defaults(self):
        err = ValidationError()
        assert err.error_code == "VALIDATION_ERROR"
        assert err.status_code == 400

    def test_custom_detail(self):
        err = ValidationError(detail="Campo obbligatorio mancante.")
        assert err.detail == "Campo obbligatorio mancante."


class TestConflictError:
    def test_defaults(self):
        err = ConflictError()
        assert err.error_code == "CONFLICT"
        assert err.status_code == 409

    def test_custom_detail(self):
        err = ConflictError(detail="Codice fiscale duplicato.")
        assert err.detail == "Codice fiscale duplicato."


class TestForbiddenError:
    def test_defaults(self):
        err = ForbiddenError()
        assert err.error_code == "FORBIDDEN"
        assert err.status_code == 403


class TestTenantIsolationError:
    def test_defaults(self):
        err = TenantIsolationError()
        assert err.error_code == "TENANT_ISOLATION"
        assert err.status_code == 403

    def test_is_app_error(self):
        err = TenantIsolationError()
        assert isinstance(err, AppError)


class TestRateLimitError:
    def test_defaults(self):
        err = RateLimitError()
        assert err.error_code == "RATE_LIMITED"
        assert err.status_code == 429


# ---------------------------------------------------------------------------
# ErrorResponse helper
# ---------------------------------------------------------------------------


class TestErrorResponse:
    def test_to_dict(self):
        resp = ErrorResponse(detail="msg", error_code="CODE", status_code=400)
        d = resp.to_dict()
        assert d == {"detail": "msg", "error_code": "CODE", "status_code": 400}


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_app_error_handler():
    """app_error_handler returns standard JSON body."""
    from starlette.datastructures import Headers
    from starlette.requests import Request

    scope = {"type": "http", "method": "GET", "path": "/test", "headers": []}
    request = Request(scope)
    exc = NotFoundError(detail="Non trovato")
    response = await app_error_handler(request, exc)
    assert response.status_code == 404
    import json

    body = json.loads(response.body)
    assert body["detail"] == "Non trovato"
    assert body["error_code"] == "NOT_FOUND"
    assert body["status_code"] == 404


@pytest.mark.asyncio
async def test_http_exception_handler():
    """http_exception_handler wraps HTTPException in standard format."""
    from starlette.requests import Request

    scope = {"type": "http", "method": "GET", "path": "/test", "headers": []}
    request = Request(scope)
    exc = HTTPException(status_code=422, detail="Unprocessable")
    response = await http_exception_handler(request, exc)
    assert response.status_code == 422
    import json

    body = json.loads(response.body)
    assert body["error_code"] == "HTTP_ERROR"
    assert body["status_code"] == 422


@pytest.mark.asyncio
async def test_generic_exception_handler():
    """generic_exception_handler catches unhandled errors."""
    from starlette.requests import Request

    scope = {"type": "http", "method": "GET", "path": "/test", "headers": []}
    request = Request(scope)
    exc = RuntimeError("unexpected")
    response = await generic_exception_handler(request, exc)
    assert response.status_code == 500
    import json

    body = json.loads(response.body)
    assert body["error_code"] == "INTERNAL_ERROR"
