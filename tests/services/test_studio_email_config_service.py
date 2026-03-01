"""DEV-443: Tests for StudioEmailConfigService.

TDD RED phase: Tests written FIRST.
Tests CRUD, plan gating, encryption, SSRF protection, SMTP validation.
"""

import ipaddress
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from app.models.studio_email_config import StudioEmailConfig
from app.models.user import User
from app.services.studio_email_config_service import StudioEmailConfigService

TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest.fixture
def service():
    with patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": TEST_FERNET_KEY}):
        return StudioEmailConfigService()


@pytest.fixture
def pro_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.billing_plan_slug = "pro"
    return user


@pytest.fixture
def base_user():
    user = MagicMock(spec=User)
    user.id = 2
    user.billing_plan_slug = "base"
    return user


@pytest.fixture
def premium_user():
    user = MagicMock(spec=User)
    user.id = 3
    user.billing_plan_slug = "premium"
    return user


@pytest.fixture
def config_data():
    return {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "user@example.com",
        "smtp_password": "secret_password_123",
        "use_tls": True,
        "from_email": "info@studio.it",
        "from_name": "Studio Rossi",
        "reply_to_email": "reply@studio.it",
    }


class TestEncryptDecrypt:
    """Tests for password encryption/decryption."""

    def test_encrypt_decrypt_round_trip(self, service) -> None:
        """Encrypting and decrypting should return the original password."""
        original = "my_secret_password_123!"
        encrypted = service._encrypt_password(original)
        assert encrypted != original
        decrypted = service._decrypt_password(encrypted)
        assert decrypted == original

    def test_encrypted_password_is_different_each_time(self, service) -> None:
        """Fernet produces different ciphertexts for the same plaintext."""
        password = "test_password"
        enc1 = service._encrypt_password(password)
        enc2 = service._encrypt_password(password)
        assert enc1 != enc2  # Fernet uses random IV


class TestPlanEligibility:
    """Tests for plan-based gating."""

    def test_base_plan_rejected(self, service, base_user) -> None:
        """Base plan users should NOT be eligible for custom email."""
        assert service._check_plan_eligibility(base_user) is False

    def test_pro_plan_allowed(self, service, pro_user) -> None:
        """Pro plan users should be eligible for custom email."""
        assert service._check_plan_eligibility(pro_user) is True

    def test_premium_plan_allowed(self, service, premium_user) -> None:
        """Premium plan users should be eligible for custom email."""
        assert service._check_plan_eligibility(premium_user) is True


class TestSSRFProtection:
    """Tests for SSRF protection on SMTP host."""

    def test_private_ip_10_rejected(self, service) -> None:
        """10.x.x.x private IP range should be blocked."""
        assert service._is_safe_host("10.0.0.1") is False

    def test_private_ip_172_rejected(self, service) -> None:
        """172.16-31.x.x private IP range should be blocked."""
        assert service._is_safe_host("172.16.0.1") is False

    def test_private_ip_192_rejected(self, service) -> None:
        """192.168.x.x private IP range should be blocked."""
        assert service._is_safe_host("192.168.1.1") is False

    def test_localhost_rejected(self, service) -> None:
        """127.0.0.1 should be blocked."""
        assert service._is_safe_host("127.0.0.1") is False

    def test_public_host_allowed(self, service) -> None:
        """Public hostname like smtp.gmail.com should be allowed."""
        assert service._is_safe_host("smtp.gmail.com") is True

    def test_invalid_port_rejected(self, service) -> None:
        """Only ports 25, 465, 587 should be allowed."""
        assert service._is_valid_port(8080) is False
        assert service._is_valid_port(22) is False

    def test_valid_ports_accepted(self, service) -> None:
        """Ports 25, 465, 587 should be accepted."""
        assert service._is_valid_port(25) is True
        assert service._is_valid_port(465) is True
        assert service._is_valid_port(587) is True


class TestCreateOrUpdateConfig:
    """Tests for create_or_update_config."""

    @pytest.mark.asyncio
    async def test_create_config_pro_user(self, service, pro_user, config_data) -> None:
        """Pro user should be able to create config."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing config
        mock_db.execute.return_value = mock_result

        with patch("app.services.studio_email_config_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.create_or_update_config(pro_user, config_data)

        assert result is not None
        assert result.user_id == 1
        assert result.smtp_host == "smtp.example.com"
        assert result.from_email == "info@studio.it"
        # Password should be encrypted, not plain
        assert result.smtp_password_encrypted != "secret_password_123"

    @pytest.mark.asyncio
    async def test_create_config_base_plan_rejected(self, service, base_user, config_data) -> None:
        """Base plan user should be rejected with ValueError."""
        with pytest.raises(ValueError, match="[Pp]iano"):
            await service.create_or_update_config(base_user, config_data)

    @pytest.mark.asyncio
    async def test_update_existing_config(self, service, pro_user, config_data) -> None:
        """Updating existing config should update fields in place."""
        existing = StudioEmailConfig(
            id=1,
            user_id=1,
            smtp_host="old.smtp.com",
            smtp_username="old@example.com",
            smtp_password_encrypted="old_encrypted",
            from_email="old@studio.it",
            from_name="Old Studio",
        )

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        with patch("app.services.studio_email_config_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.create_or_update_config(pro_user, config_data)

        assert result.smtp_host == "smtp.example.com"
        assert result.from_email == "info@studio.it"

    @pytest.mark.asyncio
    async def test_ssrf_blocked_private_ip(self, service, pro_user) -> None:
        """SSRF: private IP should be rejected."""
        data = {
            "smtp_host": "10.0.0.1",
            "smtp_port": 587,
            "smtp_username": "user@example.com",
            "smtp_password": "pass",
            "from_email": "info@studio.it",
            "from_name": "Studio",
        }
        with pytest.raises(ValueError, match="[Hh]ost"):
            await service.create_or_update_config(pro_user, data)

    @pytest.mark.asyncio
    async def test_invalid_port_rejected(self, service, pro_user) -> None:
        """Invalid port should be rejected."""
        data = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 8080,
            "smtp_username": "user@example.com",
            "smtp_password": "pass",
            "from_email": "info@studio.it",
            "from_name": "Studio",
        }
        with pytest.raises(ValueError, match="[Pp]ort"):
            await service.create_or_update_config(pro_user, data)


class TestGetConfig:
    """Tests for get_config (password redacted)."""

    @pytest.mark.asyncio
    async def test_get_config_password_redacted(self, service, pro_user) -> None:
        """get_config should return config with password redacted."""
        encrypted_pw = service._encrypt_password("real_password")
        existing = StudioEmailConfig(
            id=1,
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password_encrypted=encrypted_pw,
            from_email="info@studio.it",
            from_name="Studio Rossi",
            is_verified=True,
        )

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        with patch("app.services.studio_email_config_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.get_config(pro_user)

        assert result is not None
        assert result["has_password"] is True
        assert "smtp_password" not in result
        assert "smtp_password_encrypted" not in result
        assert result["smtp_host"] == "smtp.example.com"
        assert result["is_verified"] is True

    @pytest.mark.asyncio
    async def test_get_config_not_found(self, service, pro_user) -> None:
        """get_config should return None when no config exists."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.services.studio_email_config_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.get_config(pro_user)

        assert result is None


class TestDeleteConfig:
    """Tests for delete_config."""

    @pytest.mark.asyncio
    async def test_delete_config_success(self, service, pro_user) -> None:
        """delete_config should remove existing config."""
        existing = StudioEmailConfig(
            id=1,
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password_encrypted="enc",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        with patch("app.services.studio_email_config_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.delete_config(pro_user)

        assert result is True
        mock_db.delete.assert_called_once_with(existing)

    @pytest.mark.asyncio
    async def test_delete_config_not_found(self, service, pro_user) -> None:
        """delete_config should return False when no config exists."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.services.studio_email_config_service.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            result = await service.delete_config(pro_user)

        assert result is False


class TestValidateSmtpConnection:
    """Tests for validate_smtp_connection."""

    @pytest.mark.asyncio
    async def test_smtp_validation_success(self, service) -> None:
        """Successful SMTP handshake should return True."""
        with patch("app.services.studio_email_config_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = await service.validate_smtp_connection(
                host="smtp.example.com",
                port=587,
                username="user@example.com",
                password="password",
                use_tls=True,
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_smtp_validation_failure(self, service) -> None:
        """Failed SMTP handshake should return False."""
        with patch("app.services.studio_email_config_service.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = MagicMock(side_effect=Exception("Connection refused"))
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = await service.validate_smtp_connection(
                host="smtp.bad.com",
                port=587,
                username="user@example.com",
                password="password",
                use_tls=True,
            )
        assert result is False
