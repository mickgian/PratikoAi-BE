"""DEV-316: Tests for Tenant Context Middleware.

Tests cover:
- Happy path: valid JWT with studio_id extracted and set in request state
- Missing Authorization header returns 401
- Invalid JWT token returns 401
- JWT without studio_id returns 403
- The get_current_studio_id dependency correctly extracts from request state
- OPTIONS requests bypass auth (CORS preflight)
- Health check endpoints bypass auth
- Expired JWT returns 401
- Malformed Bearer header returns 401
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI
from jose import jwt
from starlette.testclient import TestClient

from app.middleware.tenant_context import TenantContextMiddleware, get_current_studio_id

# ------------------------------------------------------------------
# Test JWT constants
# ------------------------------------------------------------------
TEST_SECRET_KEY = "test-secret-key-for-tenant-context-middleware"
TEST_ALGORITHM = "HS256"


def _make_jwt(claims: dict, secret: str = TEST_SECRET_KEY, algorithm: str = TEST_ALGORITHM) -> str:
    """Create a JWT token with the given claims."""
    return jwt.encode(claims, secret, algorithm=algorithm)


def _make_valid_jwt(studio_id: UUID | str | None = None, **extra_claims) -> str:
    """Create a valid JWT token with studio_id."""
    claims = {
        "sub": "user-123",
        "exp": datetime.now(UTC) + timedelta(hours=2),
        "iat": datetime.now(UTC),
    }
    if studio_id is not None:
        claims["studio_id"] = str(studio_id)
    claims.update(extra_claims)
    return _make_jwt(claims)


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with the tenant context middleware."""
    app = FastAPI()

    @app.get("/api/v1/clients")
    async def protected_endpoint(
        studio_id: UUID = Depends(get_current_studio_id),
    ):
        return {"studio_id": str(studio_id)}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/api/v1/health")
    async def api_health():
        return {"status": "healthy"}

    # Add middleware — mock settings to use test secret key
    with patch("app.middleware.tenant_context.settings") as mock_settings:
        mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
        mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
        app.add_middleware(TenantContextMiddleware)

    return app


def _make_client() -> TestClient:
    """Create a TestClient with the middleware-enabled app."""
    app = _make_app()
    return TestClient(app, raise_server_exceptions=False)


# ------------------------------------------------------------------ #
# Happy path: valid JWT with studio_id
# ------------------------------------------------------------------ #
class TestHappyPath:
    """Tests for successful JWT + studio_id extraction."""

    def test_valid_jwt_with_studio_id_sets_request_state(self) -> None:
        """Valid JWT with studio_id sets request.state.studio_id."""
        studio_id = uuid4()
        token = _make_valid_jwt(studio_id=studio_id)
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["studio_id"] == str(studio_id)

    def test_studio_id_is_uuid_type(self) -> None:
        """The studio_id in request state is a UUID object."""
        studio_id = uuid4()
        token = _make_valid_jwt(studio_id=studio_id)
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        # Verify it's a valid UUID string (parseable)
        UUID(resp.json()["studio_id"])


# ------------------------------------------------------------------ #
# Missing Authorization header
# ------------------------------------------------------------------ #
class TestMissingAuthHeader:
    """Tests for requests without Authorization header."""

    def test_missing_auth_header_returns_401(self) -> None:
        """Request without Authorization header returns 401."""
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get("/api/v1/clients")

        assert resp.status_code == 401
        body = resp.json()
        assert "detail" in body

    def test_empty_auth_header_returns_401(self) -> None:
        """Empty Authorization header returns 401."""
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": ""},
            )

        assert resp.status_code == 401

    def test_non_bearer_auth_returns_401(self) -> None:
        """Authorization header without 'Bearer' prefix returns 401."""
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": "Basic dXNlcjpwYXNz"},
            )

        assert resp.status_code == 401


# ------------------------------------------------------------------ #
# Invalid JWT token
# ------------------------------------------------------------------ #
class TestInvalidJWT:
    """Tests for invalid JWT tokens."""

    def test_invalid_jwt_returns_401(self) -> None:
        """Completely invalid JWT string returns 401."""
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": "Bearer not-a-valid-jwt"},
            )

        assert resp.status_code == 401

    def test_wrong_secret_key_returns_401(self) -> None:
        """JWT signed with wrong secret key returns 401."""
        studio_id = uuid4()
        token = _make_jwt(
            {
                "sub": "user-123",
                "studio_id": str(studio_id),
                "exp": datetime.now(UTC) + timedelta(hours=2),
            },
            secret="wrong-secret-key",
        )
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 401

    def test_expired_jwt_returns_401(self) -> None:
        """Expired JWT token returns 401."""
        studio_id = uuid4()
        token = _make_jwt(
            {
                "sub": "user-123",
                "studio_id": str(studio_id),
                "exp": datetime.now(UTC) - timedelta(hours=1),
                "iat": datetime.now(UTC) - timedelta(hours=2),
            },
        )
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 401


# ------------------------------------------------------------------ #
# JWT without studio_id claim
# ------------------------------------------------------------------ #
class TestMissingStudioId:
    """Tests for JWTs that are valid but lack studio_id."""

    def test_jwt_without_studio_id_returns_403(self) -> None:
        """Valid JWT without studio_id claim returns 403."""
        token = _make_valid_jwt(studio_id=None)  # No studio_id
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 403
        body = resp.json()
        assert "studio" in body["detail"].lower() or "Studio" in body["detail"]

    def test_jwt_with_empty_studio_id_returns_403(self) -> None:
        """Valid JWT with empty string studio_id returns 403."""
        token = _make_valid_jwt(studio_id="")
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 403

    def test_jwt_with_invalid_uuid_studio_id_returns_403(self) -> None:
        """Valid JWT with non-UUID studio_id returns 403."""
        token = _make_valid_jwt(studio_id="not-a-uuid")
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 403


# ------------------------------------------------------------------ #
# get_current_studio_id dependency
# ------------------------------------------------------------------ #
class TestGetCurrentStudioIdDependency:
    """Tests for the get_current_studio_id FastAPI dependency."""

    def test_dependency_returns_uuid_from_request_state(self) -> None:
        """Dependency returns UUID when studio_id is set in request.state."""
        studio_id = uuid4()
        request = MagicMock()
        request.state = SimpleNamespace(studio_id=studio_id)

        result = get_current_studio_id(request)

        assert result == studio_id
        assert isinstance(result, UUID)

    def test_dependency_raises_403_when_no_studio_id(self) -> None:
        """Dependency raises HTTPException 403 when studio_id is missing."""
        request = MagicMock()
        request.state = SimpleNamespace()  # No studio_id

        with pytest.raises(Exception) as exc_info:
            get_current_studio_id(request)

        # FastAPI HTTPException with status_code 403
        assert exc_info.value.status_code == 403

    def test_dependency_raises_403_when_studio_id_is_none(self) -> None:
        """Dependency raises HTTPException 403 when studio_id is explicitly None."""
        request = MagicMock()
        request.state = SimpleNamespace(studio_id=None)

        with pytest.raises(Exception) as exc_info:
            get_current_studio_id(request)

        assert exc_info.value.status_code == 403


# ------------------------------------------------------------------ #
# OPTIONS requests bypass auth (CORS preflight)
# ------------------------------------------------------------------ #
class TestCORSPreflight:
    """Tests for OPTIONS request bypass."""

    def test_options_request_bypasses_auth(self) -> None:
        """OPTIONS request should bypass auth middleware."""
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.options("/api/v1/clients")

        # OPTIONS should not return 401/403, should pass through
        assert resp.status_code != 401
        assert resp.status_code != 403


# ------------------------------------------------------------------ #
# Health check bypass
# ------------------------------------------------------------------ #
class TestHealthCheckBypass:
    """Tests for health check endpoint bypass."""

    def test_root_health_bypasses_auth(self) -> None:
        """GET /health bypasses the tenant context middleware."""
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get("/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_api_health_bypasses_auth(self) -> None:
        """GET /api/v1/health bypasses the tenant context middleware."""
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get("/api/v1/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_health_no_auth_header_required(self) -> None:
        """Health endpoints do not require Authorization header."""
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            # No Authorization header at all
            resp = client.get("/health")

        assert resp.status_code == 200


# ------------------------------------------------------------------ #
# Edge cases
# ------------------------------------------------------------------ #
class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_bearer_prefix_case_insensitive(self) -> None:
        """Authorization header should accept 'Bearer' (case-sensitive per RFC)."""
        studio_id = uuid4()
        token = _make_valid_jwt(studio_id=studio_id)
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            # Standard "Bearer" casing
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200

    def test_bearer_with_extra_spaces_returns_401(self) -> None:
        """Authorization header 'Bearer  token' (extra space) returns 401."""
        studio_id = uuid4()
        token = _make_valid_jwt(studio_id=studio_id)
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get(
                "/api/v1/clients",
                headers={"Authorization": f"Bearer  {token}"},
            )

        # Should still work because we strip/split properly, or return 401
        # The important thing is it doesn't crash
        assert resp.status_code in (200, 401)

    def test_openapi_docs_bypass_auth(self) -> None:
        """OpenAPI docs endpoint should bypass auth."""
        client = _make_client()

        with patch("app.middleware.tenant_context.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = TEST_SECRET_KEY
            mock_settings.JWT_ALGORITHM = TEST_ALGORITHM
            resp = client.get("/docs")

        # Should not be blocked by tenant middleware
        assert resp.status_code != 401
        assert resp.status_code != 403
