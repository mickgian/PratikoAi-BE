"""DEV-412: Tests for Email Tracking API endpoints."""

import uuid

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
