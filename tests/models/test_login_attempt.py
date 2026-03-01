"""Tests for LoginAttempt model."""

import pytest

from app.models.login_attempt import LoginAttempt


class TestLoginAttemptModel:
    """Test LoginAttempt model definition."""

    def test_create_login_attempt_success(self):
        """Test creating a successful login attempt record."""
        attempt = LoginAttempt(
            user_id=1,
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
        )
        assert attempt.user_id == 1
        assert attempt.email == "test@example.com"
        assert attempt.ip_address == "192.168.1.1"
        assert attempt.success is True
        assert attempt.failure_reason is None

    def test_create_login_attempt_failure(self):
        """Test creating a failed login attempt record."""
        attempt = LoginAttempt(
            email="test@example.com",
            ip_address="10.0.0.1",
            success=False,
            failure_reason="wrong_password",
        )
        assert attempt.user_id is None
        assert attempt.success is False
        assert attempt.failure_reason == "wrong_password"

    def test_login_attempt_defaults(self):
        """Test default values for login attempt."""
        attempt = LoginAttempt(email="test@example.com")
        assert attempt.user_id is None
        assert attempt.ip_address == ""
        assert attempt.user_agent == ""
        assert attempt.success is False
        assert attempt.failure_reason is None

    def test_login_attempt_table_name(self):
        """Test table name is correct."""
        assert LoginAttempt.__tablename__ == "login_attempt"
