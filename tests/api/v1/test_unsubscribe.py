"""DEV-415: Tests for Unsubscribe API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.unsubscribe import router


@pytest.fixture
def unsub_client():
    """TestClient with mocked DB dependency."""
    app = FastAPI()
    app.include_router(router)

    mock_db = AsyncMock()

    async def override_get_db():
        yield mock_db

    import app.models.database as db_module

    app.dependency_overrides[db_module.get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestUnsubscribeRouter:
    def test_router_has_prefix(self):
        assert router.prefix == "/unsubscribe"

    def test_router_has_get_route(self):
        paths = [r.path for r in router.routes]
        assert "/unsubscribe/{client_id}" in paths

    def test_router_tags(self):
        assert "unsubscribe" in router.tags

    def test_router_has_post_route(self):
        methods = []
        for r in router.routes:
            if hasattr(r, "methods"):
                methods.extend(r.methods)
        assert "GET" in methods
        assert "POST" in methods

    def test_unsubscribe_client_function_exists(self):
        from app.api.v1.unsubscribe import unsubscribe_client

        assert callable(unsubscribe_client)

    def test_unsubscribe_client_post_function_exists(self):
        from app.api.v1.unsubscribe import unsubscribe_client_post

        assert callable(unsubscribe_client_post)

    def test_both_endpoints_same_path(self):
        get_paths = [r.path for r in router.routes if hasattr(r, "methods") and "GET" in r.methods]
        post_paths = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/unsubscribe/{client_id}" in get_paths
        assert "/unsubscribe/{client_id}" in post_paths


class TestUnsubscribeClientGet:
    """Tests for GET /unsubscribe/{client_id}."""

    @patch("app.api.v1.unsubscribe.unsubscribe_service")
    def test_unsubscribe_success(self, mock_service, unsub_client):
        mock_service.unsubscribe = AsyncMock(return_value=True)
        resp = unsub_client.get(
            "/unsubscribe/42",
            params={"token": "valid-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Disiscrizione completata con successo."
        mock_service.unsubscribe.assert_awaited_once()

    @patch("app.api.v1.unsubscribe.unsubscribe_service")
    def test_unsubscribe_not_found(self, mock_service, unsub_client):
        mock_service.unsubscribe = AsyncMock(return_value=False)
        resp = unsub_client.get(
            "/unsubscribe/999",
            params={"token": "some-token"},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "non trovato" in data["detail"].lower()

    @patch("app.api.v1.unsubscribe.unsubscribe_service")
    def test_unsubscribe_missing_token_returns_422(self, mock_service, unsub_client):
        resp = unsub_client.get("/unsubscribe/42")
        assert resp.status_code == 422


class TestUnsubscribeClientPost:
    """Tests for POST /unsubscribe/{client_id} (one-click)."""

    @patch("app.api.v1.unsubscribe.unsubscribe_service")
    def test_post_unsubscribe_success(self, mock_service, unsub_client):
        mock_service.unsubscribe = AsyncMock(return_value=True)
        resp = unsub_client.post(
            "/unsubscribe/10",
            params={"token": "one-click-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Disiscrizione completata con successo."

    @patch("app.api.v1.unsubscribe.unsubscribe_service")
    def test_post_unsubscribe_not_found(self, mock_service, unsub_client):
        mock_service.unsubscribe = AsyncMock(return_value=False)
        resp = unsub_client.post(
            "/unsubscribe/999",
            params={"token": "one-click-token"},
        )
        assert resp.status_code == 404

    @patch("app.api.v1.unsubscribe.unsubscribe_service")
    def test_post_missing_token_returns_422(self, mock_service, unsub_client):
        resp = unsub_client.post("/unsubscribe/10")
        assert resp.status_code == 422
