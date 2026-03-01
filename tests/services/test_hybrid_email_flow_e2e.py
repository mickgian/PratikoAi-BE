"""DEV-447: End-to-end tests for hybrid email sending flow.

Tests the full hybrid email workflow:
- Configure custom SMTP → verify → send → verify headers
- Fallback chain when custom fails
- Plan downgrade disabling custom config
- Base plan uses default only
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from app.models.studio_email_config import StudioEmailConfig
from app.models.user import User

TEST_FERNET_KEY = Fernet.generate_key().decode()


def _make_user(user_id: int, plan: str = "pro") -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = f"user{user_id}@example.com"
    user.billing_plan_slug = plan
    return user


def _make_config(user_id: int, verified: bool = True) -> StudioEmailConfig:
    f = Fernet(TEST_FERNET_KEY.encode())
    return StudioEmailConfig(
        id=user_id,
        user_id=user_id,
        smtp_host="smtp.studio.it",
        smtp_port=587,
        smtp_username="info@studio.it",
        smtp_password_encrypted=f.encrypt(b"studio_smtp_pass").decode(),
        use_tls=True,
        from_email="info@studio.it",
        from_name="Studio Rossi",
        reply_to_email="reply@studio.it",
        is_verified=verified,
        is_active=True,
    )


class TestCustomSmtpSendFlow:
    """E2E: Configure custom SMTP → verify → send communication → verify headers."""

    @pytest.mark.asyncio
    async def test_custom_smtp_send_flow(self) -> None:
        """Full flow: create config, verify, send email with custom SMTP."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.email_service import EmailService
            from app.services.studio_email_config_service import StudioEmailConfigService

            user = _make_user(1, "pro")
            config_svc = StudioEmailConfigService()
            email_svc = EmailService()

            # Step 1: Create config
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result

            with patch("app.services.studio_email_config_service.database_service") as mock_db_svc:
                mock_db_svc.get_db.return_value = mock_db
                config = await config_svc.create_or_update_config(
                    user,
                    {
                        "smtp_host": "smtp.studio.it",
                        "smtp_port": 587,
                        "smtp_username": "info@studio.it",
                        "smtp_password": "studio_smtp_pass",
                        "from_email": "info@studio.it",
                        "from_name": "Studio Rossi",
                        "reply_to_email": "reply@studio.it",
                    },
                )

            assert config.smtp_host == "smtp.studio.it"
            assert config.from_email == "info@studio.it"

            # Step 2: Send email using hybrid (custom SMTP)
            verified_config = _make_config(1, verified=True)

            with (
                patch.object(email_svc, "_send_via_smtp", new_callable=AsyncMock, return_value=True) as mock_send,
                patch("app.services.email_service.studio_email_config_service") as mock_cfg_svc,
            ):
                mock_cfg_svc.get_raw_config = AsyncMock(return_value=verified_config)
                mock_cfg_svc._decrypt_password = MagicMock(return_value="studio_smtp_pass")

                result = await email_svc.send_hybrid_email(
                    user_id=1,
                    recipient_email="client@example.com",
                    subject="Comunicazione importante",
                    html_content="<p>Contenuto della comunicazione</p>",
                )

            assert result is True
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["smtp_host"] == "smtp.studio.it"
            assert call_kwargs["from_email"] == "info@studio.it"
            assert call_kwargs["from_name"] == "Studio Rossi"
            assert call_kwargs["reply_to"] == "reply@studio.it"


class TestFallbackToDefaultFlow:
    """E2E: Custom SMTP fails → fallback to PratikoAI default."""

    @pytest.mark.asyncio
    async def test_fallback_to_default_flow(self) -> None:
        """When custom SMTP fails, should successfully send via default."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.email_service import EmailService

            email_svc = EmailService()
            verified_config = _make_config(1, verified=True)

            with (
                patch.object(
                    email_svc,
                    "_send_via_smtp",
                    new_callable=AsyncMock,
                    side_effect=[False, True],  # Custom fails, default succeeds
                ) as mock_send,
                patch("app.services.email_service.studio_email_config_service") as mock_cfg_svc,
            ):
                mock_cfg_svc.get_raw_config = AsyncMock(return_value=verified_config)
                mock_cfg_svc._decrypt_password = MagicMock(return_value="studio_smtp_pass")

                result = await email_svc.send_hybrid_email(
                    user_id=1,
                    recipient_email="client@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                )

            assert result is True
            assert mock_send.call_count == 2
            # Second call should be to default SMTP
            second_call = mock_send.call_args_list[1][1]
            assert second_call["smtp_host"] == email_svc.smtp_server


class TestPlanDowngradeDisablesCustom:
    """E2E: Pro → Base downgrade disables custom config."""

    @pytest.mark.asyncio
    async def test_plan_downgrade_disables_custom(self) -> None:
        """After downgrade to Base, creating config should be rejected."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.studio_email_config_service import StudioEmailConfigService

            config_svc = StudioEmailConfigService()

            # User was Pro, now downgraded to Base
            base_user = _make_user(1, "base")

            with pytest.raises(ValueError, match="[Pp]iano"):
                await config_svc.create_or_update_config(
                    base_user,
                    {
                        "smtp_host": "smtp.studio.it",
                        "smtp_port": 587,
                        "smtp_username": "info@studio.it",
                        "smtp_password": "pass",
                        "from_email": "info@studio.it",
                        "from_name": "Studio",
                    },
                )


class TestBasePlanUsesDefaultOnly:
    """E2E: Base plan users always use PratikoAI default SMTP."""

    @pytest.mark.asyncio
    async def test_base_plan_uses_default_only(self) -> None:
        """Base plan user sends via default PratikoAI SMTP."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.email_service import EmailService

            email_svc = EmailService()

            with (
                patch.object(email_svc, "_send_via_smtp", new_callable=AsyncMock, return_value=True) as mock_send,
                patch("app.services.email_service.studio_email_config_service") as mock_cfg_svc,
            ):
                # No custom config for base user
                mock_cfg_svc.get_raw_config = AsyncMock(return_value=None)

                result = await email_svc.send_hybrid_email(
                    user_id=2,
                    recipient_email="client@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                    studio_name="Studio Base",
                )

            assert result is True
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["smtp_host"] == email_svc.smtp_server
            assert call_kwargs["from_name"] == "Studio Base"
