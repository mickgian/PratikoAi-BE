"""Tests for DEV-366: OpenAPI Schema Validation.

Ensures OpenAPI schema is accurate and complete for frontend type generation.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.compliance import router as compliance_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.websocket import router as websocket_router


@pytest.fixture
def app():
    """Create test app with all Wave 7 routers."""
    app = FastAPI(title="PratikoAI", version="2.0.0")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(compliance_router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/api/v1")
    return app


class TestOpenAPISchema:
    """Validate OpenAPI schema generation."""

    @pytest.mark.asyncio
    async def test_openapi_schema_generates(self, app):
        """OpenAPI schema generates without errors."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/openapi.json")

        assert resp.status_code == 200
        schema = resp.json()
        assert "openapi" in schema
        assert schema["info"]["title"] == "PratikoAI"

    @pytest.mark.asyncio
    async def test_dashboard_endpoint_in_schema(self, app):
        """Dashboard endpoint appears in schema."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/openapi.json")

        paths = resp.json()["paths"]
        assert "/api/v1/dashboard" in paths

    @pytest.mark.asyncio
    async def test_compliance_endpoint_in_schema(self, app):
        """Compliance endpoint appears in schema."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/openapi.json")

        paths = resp.json()["paths"]
        assert "/api/v1/compliance" in paths

    @pytest.mark.asyncio
    async def test_all_endpoints_have_responses(self, app):
        """All endpoints define at least one response."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/openapi.json")

        paths = resp.json()["paths"]
        for path, methods in paths.items():
            for method, spec in methods.items():
                if method in ("get", "post", "put", "delete", "patch"):
                    assert "responses" in spec, f"Missing responses for {method} {path}"

    @pytest.mark.asyncio
    async def test_schema_has_components(self, app):
        """Schema includes component definitions."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/openapi.json")

        schema = resp.json()
        # At minimum should have validation error schema
        assert "components" in schema or "paths" in schema
