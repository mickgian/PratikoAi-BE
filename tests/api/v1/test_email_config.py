"""DEV-444: Tests for Studio Email Config API endpoints.

TDD RED phase: Tests written FIRST.
Tests create, get, delete, test email endpoints with auth and plan gating.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import User


@pytest.fixture
def mock_pro_user():
    """Mock authenticated Pro plan user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.billing_plan_slug = "pro"
    user.role = "regular_user"
    return user


@pytest.fixture
def mock_base_user():
    """Mock authenticated Base plan user."""
    user = MagicMock(spec=User)
    user.id = 2
    user.email = "base@example.com"
    user.billing_plan_slug = "base"
    user.role = "regular_user"
    return user


@pytest.fixture
def config_response():
    """Sample config response dict (password redacted)."""
    return {
        "id": 1,
        "user_id": 1,
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "user@example.com",
        "has_password": True,
        "use_tls": True,
        "from_email": "info@studio.it",
        "from_name": "Studio Rossi",
        "reply_to_email": "reply@studio.it",
        "is_verified": True,
        "is_active": True,
        "created_at": None,
        "updated_at": None,
    }


class TestCreateEmailConfig:
    """Tests for POST /email-config."""

    @pytest.mark.asyncio
    async def test_create_config_201(self, mock_pro_user) -> None:
        """Pro user should successfully create config (201)."""
        from app.api.v1.email_config import create_or_update_email_config
        from app.schemas.email_config import EmailConfigCreateRequest

        request = EmailConfigCreateRequest(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="secret",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )

        mock_config = MagicMock()
        mock_config.id = 1
        mock_config.user_id = 1
        mock_config.smtp_host = "smtp.example.com"
        mock_config.smtp_port = 587
        mock_config.smtp_username = "user@example.com"
        mock_config.from_email = "info@studio.it"
        mock_config.from_name = "Studio Rossi"
        mock_config.reply_to_email = None
        mock_config.use_tls = True
        mock_config.is_verified = False
        mock_config.is_active = True

        with patch("app.api.v1.email_config.studio_email_config_service") as mock_svc:
            mock_svc.create_or_update_config = AsyncMock(return_value=mock_config)
            result = await create_or_update_email_config(request=request, user=mock_pro_user)

        assert result.smtp_host == "smtp.example.com"
        assert result.has_password is True

    @pytest.mark.asyncio
    async def test_create_config_base_plan_403(self, mock_base_user) -> None:
        """Base plan user should get 403."""
        from app.api.v1.email_config import create_or_update_email_config
        from app.schemas.email_config import EmailConfigCreateRequest

        request = EmailConfigCreateRequest(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="secret",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )

        with patch("app.api.v1.email_config.studio_email_config_service") as mock_svc:
            mock_svc.create_or_update_config = AsyncMock(side_effect=ValueError("Piano non permette"))
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await create_or_update_email_config(request=request, user=mock_base_user)
            assert exc_info.value.status_code == 403


class TestGetEmailConfig:
    """Tests for GET /email-config."""

    @pytest.mark.asyncio
    async def test_get_config_200(self, mock_pro_user, config_response) -> None:
        """Should return config with password redacted."""
        from app.api.v1.email_config import get_email_config

        with patch("app.api.v1.email_config.studio_email_config_service") as mock_svc:
            mock_svc.get_config = AsyncMock(return_value=config_response)
            result = await get_email_config(user=mock_pro_user)

        assert result.smtp_host == "smtp.example.com"
        assert result.has_password is True
        assert result.is_verified is True

    @pytest.mark.asyncio
    async def test_get_config_not_found_404(self, mock_pro_user) -> None:
        """Should return 404 when no config exists."""
        from app.api.v1.email_config import get_email_config

        with patch("app.api.v1.email_config.studio_email_config_service") as mock_svc:
            mock_svc.get_config = AsyncMock(return_value=None)
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await get_email_config(user=mock_pro_user)
            assert exc_info.value.status_code == 404


class TestDeleteEmailConfig:
    """Tests for DELETE /email-config."""

    @pytest.mark.asyncio
    async def test_delete_config_204(self, mock_pro_user) -> None:
        """Should delete config and return success message."""
        from app.api.v1.email_config import delete_email_config

        with patch("app.api.v1.email_config.studio_email_config_service") as mock_svc:
            mock_svc.delete_config = AsyncMock(return_value=True)
            result = await delete_email_config(user=mock_pro_user)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_config_not_found(self, mock_pro_user) -> None:
        """Should return 404 when no config to delete."""
        from app.api.v1.email_config import delete_email_config

        with patch("app.api.v1.email_config.studio_email_config_service") as mock_svc:
            mock_svc.delete_config = AsyncMock(return_value=False)
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await delete_email_config(user=mock_pro_user)
            assert exc_info.value.status_code == 404


class TestTestEmailConfig:
    """Tests for POST /email-config/test."""

    @pytest.mark.asyncio
    async def test_test_email_success(self, mock_pro_user) -> None:
        """Successful SMTP test should return success."""
        from app.api.v1.email_config import test_email_config

        with patch("app.api.v1.email_config.studio_email_config_service") as mock_svc:
            mock_svc.verify_config = AsyncMock(return_value=True)
            result = await test_email_config(user=mock_pro_user)

        assert result["success"] is True
        assert result["verified"] is True

    @pytest.mark.asyncio
    async def test_test_email_failure(self, mock_pro_user) -> None:
        """Failed SMTP test should return 422."""
        from app.api.v1.email_config import test_email_config

        with patch("app.api.v1.email_config.studio_email_config_service") as mock_svc:
            mock_svc.verify_config = AsyncMock(return_value=False)
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await test_email_config(user=mock_pro_user)
            assert exc_info.value.status_code == 422
