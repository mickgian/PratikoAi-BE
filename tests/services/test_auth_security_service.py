"""Tests for auth security service (lockout, login attempts, session limits)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.auth_security_service import AuthSecurityService


class TestAccountLockout:
    """Test account lockout after failed attempts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = AuthSecurityService()

    def test_is_account_locked_no_lockout(self):
        """Test account is not locked when no lockout time set."""
        assert self.service.is_account_locked(account_locked_until=None) is False

    def test_is_account_locked_expired(self):
        """Test account lockout has expired."""
        past = datetime.now(UTC) - timedelta(minutes=1)
        assert self.service.is_account_locked(account_locked_until=past) is False

    def test_is_account_locked_active(self):
        """Test account is currently locked."""
        future = datetime.now(UTC) + timedelta(minutes=10)
        assert self.service.is_account_locked(account_locked_until=future) is True

    def test_should_lock_account_below_threshold(self):
        """Test no lock when attempts below threshold."""
        assert self.service.should_lock_account(failed_attempts=4) is False

    def test_should_lock_account_at_threshold(self):
        """Test lock when attempts reach threshold."""
        assert self.service.should_lock_account(failed_attempts=5) is True

    def test_should_lock_account_above_threshold(self):
        """Test lock when attempts exceed threshold."""
        assert self.service.should_lock_account(failed_attempts=10) is True

    def test_get_lockout_duration_first_lock(self):
        """Test first lockout duration is 15 minutes."""
        duration = self.service.get_lockout_duration(failed_attempts=5)
        assert duration == timedelta(minutes=15)

    def test_get_lockout_duration_escalating(self):
        """Test lockout duration escalates with more attempts."""
        duration_5 = self.service.get_lockout_duration(failed_attempts=5)
        duration_10 = self.service.get_lockout_duration(failed_attempts=10)
        assert duration_10 > duration_5

    def test_get_lockout_duration_max_cap(self):
        """Test lockout duration is capped at 24 hours."""
        duration = self.service.get_lockout_duration(failed_attempts=100)
        assert duration <= timedelta(hours=24)


class TestSessionLimits:
    """Test concurrent session limits."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = AuthSecurityService()

    def test_max_sessions_default(self):
        """Test default max sessions is 5."""
        assert self.service.max_sessions == 5

    def test_exceeds_session_limit_false(self):
        """Test under session limit."""
        assert self.service.exceeds_session_limit(current_count=3) is False

    def test_exceeds_session_limit_true(self):
        """Test over session limit."""
        assert self.service.exceeds_session_limit(current_count=5) is True
