"""Tests for QA environment role assignment on registration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr
from starlette.requests import Request as StarletteRequest

from app.api.v1.auth import _get_qa_role, register_user
from app.core.config import Environment
from app.models.user import UserRole

FAKE_STAKEHOLDER = "stakeholder@test.com"
FAKE_STAKEHOLDRESS = "stakeholdress@test.com"


@pytest.fixture(autouse=True)
def _qa_env_vars(monkeypatch):
    """Set fake stakeholder env vars for all tests."""
    monkeypatch.setenv("STAKEHOLDER_EMAIL", FAKE_STAKEHOLDER)
    monkeypatch.setenv("STAKEHOLDRESS_EMAIL", FAKE_STAKEHOLDRESS)


class TestGetQaRole:
    """Tests for _get_qa_role helper."""

    @patch("app.api.v1.auth.settings")
    def test_assigns_admin_to_stakeholder_on_qa(self, mock_settings):
        """Stakeholder gets ADMIN role on QA."""
        mock_settings.ENVIRONMENT = Environment.QA

        result = _get_qa_role(FAKE_STAKEHOLDER)

        assert result == UserRole.ADMIN.value

    @patch("app.api.v1.auth.settings")
    def test_assigns_super_user_to_stakeholdress_on_qa(self, mock_settings):
        """Stakeholdress gets SUPER_USER role on QA."""
        mock_settings.ENVIRONMENT = Environment.QA

        result = _get_qa_role(FAKE_STAKEHOLDRESS)

        assert result == UserRole.SUPER_USER.value

    @patch("app.api.v1.auth.settings")
    def test_returns_none_for_unknown_email_on_qa(self, mock_settings):
        """Unknown emails get no role override on QA."""
        mock_settings.ENVIRONMENT = Environment.QA

        result = _get_qa_role("random@example.com")

        assert result is None

    @patch("app.api.v1.auth.settings")
    def test_returns_none_on_development(self, mock_settings):
        """Known QA emails get no role override outside QA."""
        mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

        result = _get_qa_role(FAKE_STAKEHOLDER)

        assert result is None

    @patch("app.api.v1.auth.settings")
    def test_returns_none_on_production(self, mock_settings):
        """Known QA emails get no role override in production."""
        mock_settings.ENVIRONMENT = Environment.PRODUCTION

        result = _get_qa_role(FAKE_STAKEHOLDER)

        assert result is None


class TestExpertProfileCreationOnRegistration:
    """Tests that an ExpertProfile is auto-created for QA elevated-role users."""

    @staticmethod
    def _make_request() -> StarletteRequest:
        scope = {"type": "http", "method": "POST", "path": "/register", "headers": [], "query_string": b""}
        return StarletteRequest(scope)

    @pytest.mark.asyncio()
    @patch("app.api.v1.auth.email_service")
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_creates_expert_profile_when_qa_role_assigned(self, _mock_limiter, mock_db, mock_email):
        """ExpertProfile is created when registration assigns a QA role."""
        mock_email.send_welcome_email = AsyncMock(return_value=True)
        mock_user = MagicMock(id=1, email=FAKE_STAKEHOLDER)
        mock_db.get_user_by_email = AsyncMock(return_value=None)
        mock_db.create_user = AsyncMock(return_value=mock_user)
        mock_db.create_expert_profile = AsyncMock()
        mock_db.update_user_refresh_token = AsyncMock()

        user_data = MagicMock(email=FAKE_STAKEHOLDER, password=SecretStr("StrongP@ss1"))

        with (
            patch("app.api.v1.auth.sanitize_email", return_value=FAKE_STAKEHOLDER),
            patch("app.api.v1.auth.validate_password_strength"),
            patch("app.api.v1.auth.User") as mock_user_cls,
            patch("app.api.v1.auth.create_access_token") as mock_at,
            patch("app.api.v1.auth.create_refresh_token") as mock_rt,
            patch("app.api.v1.auth._get_qa_role", return_value=UserRole.ADMIN.value),
        ):
            mock_user_cls.hash_password.return_value = "hashed"
            mock_at.return_value = MagicMock(access_token="at", expires_at="2099-01-01")
            mock_rt.return_value = MagicMock(access_token="rt")

            await register_user(self._make_request(), user_data)

        mock_db.create_expert_profile.assert_called_once_with(1)

    @pytest.mark.asyncio()
    @patch("app.api.v1.auth.email_service")
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_skips_expert_profile_for_regular_user(self, _mock_limiter, mock_db, mock_email):
        """ExpertProfile is NOT created for regular (non-QA) registrations."""
        mock_email.send_welcome_email = AsyncMock(return_value=True)
        mock_user = MagicMock(id=2, email="regular@example.com")
        mock_db.get_user_by_email = AsyncMock(return_value=None)
        mock_db.create_user = AsyncMock(return_value=mock_user)
        mock_db.create_expert_profile = AsyncMock()
        mock_db.update_user_refresh_token = AsyncMock()

        user_data = MagicMock(email="regular@example.com", password=SecretStr("StrongP@ss1"))

        with (
            patch("app.api.v1.auth.sanitize_email", return_value="regular@example.com"),
            patch("app.api.v1.auth.validate_password_strength"),
            patch("app.api.v1.auth.User") as mock_user_cls,
            patch("app.api.v1.auth.create_access_token") as mock_at,
            patch("app.api.v1.auth.create_refresh_token") as mock_rt,
            patch("app.api.v1.auth._get_qa_role", return_value=None),
        ):
            mock_user_cls.hash_password.return_value = "hashed"
            mock_at.return_value = MagicMock(access_token="at", expires_at="2099-01-01")
            mock_rt.return_value = MagicMock(access_token="rt")

            await register_user(self._make_request(), user_data)

        mock_db.create_expert_profile.assert_not_called()
