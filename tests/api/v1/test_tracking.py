"""DEV-412: Tests for Email Tracking API endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Guard the import — tracking module triggers DB engine creation at import time
# when app.models.database is not already mocked in sys.modules.
try:
    from app.api.v1.tracking import router

    _TRACKING_IMPORTABLE = True
except Exception:
    _TRACKING_IMPORTABLE = False
    router = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(not _TRACKING_IMPORTABLE, reason="Cannot import tracking module (requires DB)")


def _get_get_db_callable():
    """Get the get_db callable that the tracking module imported.

    When app.models.database is mocked (by conftest sys.modules injection),
    get_db is a MagicMock attribute. We must use the *same* object that the
    router captured at import time so that dependency_overrides can match it.
    """
    import app.api.v1.tracking as tracking_mod

    return tracking_mod.get_db


@pytest.fixture
def tracking_client():
    """TestClient with mocked DB dependency.

    Uses app.dependency_overrides on the *same* get_db callable the router
    captured, so the override works regardless of whether app.models.database
    is real or mocked.
    """
    get_db = _get_get_db_callable()

    mock_db = AsyncMock()

    async def override_get_db():
        yield mock_db

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestTrackingRouter:
    def test_router_has_prefix(self):
        assert router.prefix == "/t"

    def test_router_has_routes(self):
        paths = [r.path for r in router.routes]
        assert "/t/{tracking_type}/{token}" in paths
        assert "/t/stats/{communication_id}" in paths

    def test_router_tags(self):
        assert "tracking" in router.tags

    def test_track_redirect_route_is_get(self):
        for route in router.routes:
            if hasattr(route, "path") and route.path == "/t/{tracking_type}/{token}":
                assert "GET" in route.methods

    def test_stats_route_is_get(self):
        for route in router.routes:
            if hasattr(route, "path") and route.path == "/t/stats/{communication_id}":
                assert "GET" in route.methods

    def test_route_count(self):
        paths = [r.path for r in router.routes]
        assert len(paths) == 2

    def test_track_redirect_function_exists(self):
        from app.api.v1.tracking import track_redirect

        assert callable(track_redirect)

    def test_get_tracking_stats_function_exists(self):
        from app.api.v1.tracking import get_tracking_stats

        assert callable(get_tracking_stats)


class TestTrackRedirect:
    """Tests for GET /t/{tracking_type}/{token}."""

    @patch("app.api.v1.tracking.email_tracking_service")
    def test_track_redirect_success(self, mock_service, tracking_client):
        mock_service.record_event = AsyncMock(return_value=None)
        cid = str(uuid.uuid4())
        resp = tracking_client.get(
            "/t/click/test-token-123",
            params={"dest": "https://example.com", "cid": cid},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert resp.headers["location"] == "https://example.com"
        mock_service.record_event.assert_awaited_once()

    @patch("app.api.v1.tracking.email_tracking_service")
    def test_track_redirect_open_type(self, mock_service, tracking_client):
        mock_service.record_event = AsyncMock(return_value=None)
        cid = str(uuid.uuid4())
        resp = tracking_client.get(
            "/t/open/token-abc",
            params={"dest": "https://example.com/page", "cid": cid},
            follow_redirects=False,
        )
        assert resp.status_code == 302

    @patch("app.api.v1.tracking.email_tracking_service")
    def test_track_redirect_missing_dest_returns_422(self, mock_service, tracking_client):
        cid = str(uuid.uuid4())
        resp = tracking_client.get(
            "/t/click/some-token",
            params={"cid": cid},
        )
        assert resp.status_code == 422

    @patch("app.api.v1.tracking.email_tracking_service")
    def test_track_redirect_missing_cid_returns_422(self, mock_service, tracking_client):
        resp = tracking_client.get(
            "/t/click/some-token",
            params={"dest": "https://example.com"},
        )
        assert resp.status_code == 422


class TestGetTrackingStats:
    """Tests for GET /t/stats/{communication_id}."""

    @patch("app.api.v1.tracking.email_tracking_service")
    def test_stats_success(self, mock_service, tracking_client):
        cid = str(uuid.uuid4())
        mock_service.get_communication_stats = AsyncMock(return_value={"opens": 5, "clicks": 3})
        resp = tracking_client.get(f"/t/stats/{cid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["opens"] == 5
        assert data["clicks"] == 3

    @patch("app.api.v1.tracking.email_tracking_service")
    def test_stats_invalid_uuid_returns_422(self, mock_service, tracking_client):
        resp = tracking_client.get("/t/stats/not-a-uuid")
        assert resp.status_code == 422
