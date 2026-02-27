"""DEV-412: Tests for Email Tracking API endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.tracking import router


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
