"""DEV-415: Tests for Unsubscribe API endpoints."""

import pytest

from app.api.v1.unsubscribe import router


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
