"""DEV-449: Tests for SMTP encryption key rotation script.

TDD RED phase: Tests written FIRST.
Tests re-encryption, atomic transactions, invalid key handling, empty table.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.models.studio_email_config import StudioEmailConfig
from app.scripts.rotate_smtp_encryption_key import rotate_encryption_key


@pytest.fixture
def old_key():
    return Fernet.generate_key().decode()


@pytest.fixture
def new_key():
    return Fernet.generate_key().decode()


def _make_config(config_id: int, user_id: int, old_key: str, password: str) -> StudioEmailConfig:
    """Create a StudioEmailConfig with a password encrypted using the old key."""
    f = Fernet(old_key.encode())
    return StudioEmailConfig(
        id=config_id,
        user_id=user_id,
        smtp_host="smtp.example.com",
        smtp_username="user@example.com",
        smtp_password_encrypted=f.encrypt(password.encode()).decode(),
        from_email="info@studio.it",
        from_name="Studio",
    )


class TestRotateEncryptionKey:
    """Tests for rotate_encryption_key function."""

    @pytest.mark.asyncio
    async def test_re_encrypt_all_records(self, old_key, new_key) -> None:
        """Should re-encrypt all stored passwords with new key."""
        config1 = _make_config(1, 1, old_key, "password_one")
        config2 = _make_config(2, 2, old_key, "password_two")

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [config1, config2]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("app.scripts.rotate_smtp_encryption_key.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            count = await rotate_encryption_key(old_key, new_key)

        assert count == 2

        # Verify the passwords can be decrypted with the new key
        new_fernet = Fernet(new_key.encode())
        assert new_fernet.decrypt(config1.smtp_password_encrypted.encode()).decode() == "password_one"
        assert new_fernet.decrypt(config2.smtp_password_encrypted.encode()).decode() == "password_two"

    @pytest.mark.asyncio
    async def test_atomic_transaction_commits(self, old_key, new_key) -> None:
        """Should commit all changes in a single transaction."""
        config = _make_config(1, 1, old_key, "my_password")

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [config]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("app.scripts.rotate_smtp_encryption_key.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            await rotate_encryption_key(old_key, new_key)

        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_old_key_raises(self, new_key) -> None:
        """Invalid old key should raise an error during decryption."""
        # Create config encrypted with a different key
        real_key = Fernet.generate_key().decode()
        config = _make_config(1, 1, real_key, "my_password")

        wrong_old_key = Fernet.generate_key().decode()

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [config]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("app.scripts.rotate_smtp_encryption_key.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            with pytest.raises(InvalidToken):
                await rotate_encryption_key(wrong_old_key, new_key)

        # Should NOT commit on failure
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_table_no_op(self, old_key, new_key) -> None:
        """Empty table should be a no-op, returning 0."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("app.scripts.rotate_smtp_encryption_key.database_service") as mock_db_svc:
            mock_db_svc.get_db.return_value = mock_db
            count = await rotate_encryption_key(old_key, new_key)

        assert count == 0
        mock_db.commit.assert_awaited_once()
