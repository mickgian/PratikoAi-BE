"""Tests for rate limiter configuration."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.limiter import limiter


class TestLimiter:
    """Test rate limiter initialization."""

    def test_limiter_exists(self):
        """Test limiter object is initialized."""
        assert limiter is not None

    def test_limiter_has_key_func(self):
        """Test limiter has key function configured."""
        assert hasattr(limiter, "_key_func")

    def test_limiter_type(self):
        """Test limiter is correct type."""
        from slowapi import Limiter

        assert isinstance(limiter, Limiter)

    @patch("app.core.limiter.settings")
    def test_limiter_uses_settings(self, mock_settings):
        """Test limiter uses settings from config."""
        # This test verifies the import structure is correct
        from app.core import limiter as limiter_module

        assert hasattr(limiter_module, "settings")
