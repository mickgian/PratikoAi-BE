"""DEV-415: Tests for Unsubscribe API endpoints."""

from unittest.mock import AsyncMock, patch

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
