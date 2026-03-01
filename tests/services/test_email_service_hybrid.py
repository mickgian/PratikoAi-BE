"""DEV-445: Tests for EmailService hybrid sending (fallback chain).

TDD RED phase: Tests written FIRST.
Tests custom SMTP config → fallback to default → error logging.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from app.models.studio_email_config import StudioEmailConfig

TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest.fixture
def custom_config():
    """Verified custom SMTP config."""
    f = Fernet(TEST_FERNET_KEY.encode())
    return StudioEmailConfig(
        id=1,
        user_id=1,
        smtp_host="smtp.studio.it",
        smtp_port=587,
        smtp_username="info@studio.it",
        smtp_password_encrypted=f.encrypt(b"custom_password").decode(),
        use_tls=True,
        from_email="info@studio.it",
        from_name="Studio Rossi",
        reply_to_email="reply@studio.it",
        is_verified=True,
        is_active=True,
    )


@pytest.fixture
def unverified_config():
    """Unverified custom SMTP config."""
    f = Fernet(TEST_FERNET_KEY.encode())
    return StudioEmailConfig(
        id=2,
        user_id=2,
        smtp_host="smtp.studio.it",
        smtp_port=587,
        smtp_username="info@studio.it",
        smtp_password_encrypted=f.encrypt(b"custom_password").decode(),
        use_tls=True,
        from_email="info@studio.it",
        from_name="Studio Rossi",
        is_verified=False,
        is_active=True,
    )


class TestHybridSending:
    """Tests for the hybrid email sending fallback chain."""

    @pytest.mark.asyncio
    async def test_send_with_custom_config(self, custom_config) -> None:
        """When user has verified custom config, use it."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.email_service import EmailService

            service = EmailService()

            with (
                patch.object(service, "_send_via_smtp", new_callable=AsyncMock, return_value=True) as mock_send,
                patch("app.services.email_service.studio_email_config_service") as mock_config_svc,
            ):
                mock_config_svc.get_raw_config = AsyncMock(return_value=custom_config)
                mock_config_svc._decrypt_password = MagicMock(return_value="custom_password")

                result = await service.send_hybrid_email(
                    user_id=1,
                    recipient_email="client@example.com",
                    subject="Test Subject",
                    html_content="<p>Test</p>",
                )

            assert result is True
            # Should have been called with the custom SMTP config
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args
            assert call_kwargs[1]["smtp_host"] == "smtp.studio.it"
            assert call_kwargs[1]["from_email"] == "info@studio.it"
            assert call_kwargs[1]["from_name"] == "Studio Rossi"

    @pytest.mark.asyncio
    async def test_fallback_to_default_on_custom_failure(self, custom_config) -> None:
        """When custom SMTP fails, fall back to default PratikoAI SMTP."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.email_service import EmailService

            service = EmailService()

            with (
                patch.object(
                    service,
                    "_send_via_smtp",
                    new_callable=AsyncMock,
                    side_effect=[False, True],  # Custom fails, default succeeds
                ) as mock_send,
                patch("app.services.email_service.studio_email_config_service") as mock_config_svc,
            ):
                mock_config_svc.get_raw_config = AsyncMock(return_value=custom_config)
                mock_config_svc._decrypt_password = MagicMock(return_value="custom_password")

                result = await service.send_hybrid_email(
                    user_id=1,
                    recipient_email="client@example.com",
                    subject="Test Subject",
                    html_content="<p>Test</p>",
                )

            assert result is True
            assert mock_send.call_count == 2  # Custom + default

    @pytest.mark.asyncio
    async def test_default_smtp_when_no_custom_config(self) -> None:
        """When no custom config exists, use default PratikoAI SMTP."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.email_service import EmailService

            service = EmailService()

            with (
                patch.object(service, "_send_via_smtp", new_callable=AsyncMock, return_value=True) as mock_send,
                patch("app.services.email_service.studio_email_config_service") as mock_config_svc,
            ):
                mock_config_svc.get_raw_config = AsyncMock(return_value=None)

                result = await service.send_hybrid_email(
                    user_id=1,
                    recipient_email="client@example.com",
                    subject="Test Subject",
                    html_content="<p>Test</p>",
                )

            assert result is True
            mock_send.assert_called_once()
            # Should use default PratikoAI SMTP
            call_kwargs = mock_send.call_args
            assert call_kwargs[1]["smtp_host"] == service.smtp_server

    @pytest.mark.asyncio
    async def test_reply_to_header_set(self, custom_config) -> None:
        """Custom config should set Reply-To header."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.email_service import EmailService

            service = EmailService()

            with (
                patch.object(service, "_send_via_smtp", new_callable=AsyncMock, return_value=True) as mock_send,
                patch("app.services.email_service.studio_email_config_service") as mock_config_svc,
            ):
                mock_config_svc.get_raw_config = AsyncMock(return_value=custom_config)
                mock_config_svc._decrypt_password = MagicMock(return_value="custom_password")

                await service.send_hybrid_email(
                    user_id=1,
                    recipient_email="client@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                )

            call_kwargs = mock_send.call_args
            assert call_kwargs[1]["reply_to"] == "reply@studio.it"

    @pytest.mark.asyncio
    async def test_from_header_with_studio_name(self, custom_config) -> None:
        """Custom config should set From header with studio name."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.email_service import EmailService

            service = EmailService()

            with (
                patch.object(service, "_send_via_smtp", new_callable=AsyncMock, return_value=True) as mock_send,
                patch("app.services.email_service.studio_email_config_service") as mock_config_svc,
            ):
                mock_config_svc.get_raw_config = AsyncMock(return_value=custom_config)
                mock_config_svc._decrypt_password = MagicMock(return_value="custom_password")

                await service.send_hybrid_email(
                    user_id=1,
                    recipient_email="client@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                )

            call_kwargs = mock_send.call_args
            assert call_kwargs[1]["from_name"] == "Studio Rossi"
            assert call_kwargs[1]["from_email"] == "info@studio.it"

    @pytest.mark.asyncio
    async def test_unverified_config_skipped(self) -> None:
        """Unverified config should be skipped (get_raw_config filters it)."""
        with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
            from app.services.email_service import EmailService

            service = EmailService()

            with (
                patch.object(service, "_send_via_smtp", new_callable=AsyncMock, return_value=True) as mock_send,
                patch("app.services.email_service.studio_email_config_service") as mock_config_svc,
            ):
                # get_raw_config returns None for unverified configs
                mock_config_svc.get_raw_config = AsyncMock(return_value=None)

                result = await service.send_hybrid_email(
                    user_id=2,
                    recipient_email="client@example.com",
                    subject="Test",
                    html_content="<p>Test</p>",
                )

            assert result is True
            mock_send.assert_called_once()
            # Should use default
            call_kwargs = mock_send.call_args
            assert call_kwargs[1]["smtp_host"] == service.smtp_server
