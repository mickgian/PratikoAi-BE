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
