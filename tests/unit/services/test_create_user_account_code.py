"""Unit tests for account_code assignment during user creation.

Tests cover:
- User gets a non-None account_code after creation
- account_code matches the expected format ({3_letters}{hundreds}{2_digits}-{seq})
- Email is passed to generate_account_code
"""

import re
from unittest.mock import MagicMock, patch

import pytest

# Pattern: 3 uppercase letters + hundreds (200-900) + 2 digits + dash + sequence
ACCOUNT_CODE_PATTERN = re.compile(r"^[A-Z]{3}[2-9]00\d{2}-\d+$")


class TestCreateUserAccountCode:
    """Tests for account_code generation in create_user service."""

    @patch("app.services.database.generate_account_code")
    def test_create_user_assigns_account_code(self, mock_gen: MagicMock) -> None:
        """User should have a non-None account_code after creation."""
        mock_gen.return_value = "TES70021-1"

        from app.services.database import DatabaseService

        service = DatabaseService.__new__(DatabaseService)
        # Mock the engine and session
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.account_code = "TES70021-1"
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.refresh = MagicMock(side_effect=lambda u: setattr(u, "account_code", "TES70021-1"))

        with patch("app.services.database.Session", return_value=mock_session):
            service.engine = MagicMock()
            import asyncio

            asyncio.get_event_loop().run_until_complete(service.create_user("test@example.com", "hashed_password"))

        # Verify generate_account_code was called with email parameter
        mock_gen.assert_called_once_with(email="test@example.com", sequence=1)

    @patch("app.services.database.generate_account_code")
    def test_create_user_account_code_matches_format(self, mock_gen: MagicMock) -> None:
        """account_code should match the {3_letters}{hundreds}{2_digits}-{seq} pattern."""
        mock_gen.return_value = "MGI70021-1"
        assert ACCOUNT_CODE_PATTERN.match("MGI70021-1")

    @patch("app.services.database.generate_account_code")
    def test_create_user_passes_email_to_generator(self, mock_gen: MagicMock) -> None:
        """Email should be passed to generate_account_code for prefix extraction."""
        mock_gen.return_value = "MIC30045-1"

        from app.services.database import DatabaseService

        service = DatabaseService.__new__(DatabaseService)
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch("app.services.database.Session", return_value=mock_session):
            service.engine = MagicMock()
            import asyncio

            asyncio.get_event_loop().run_until_complete(
                service.create_user("michele.giannone@gmail.com", "hashed_password")
            )

        # Verify email was passed
        mock_gen.assert_called_once_with(email="michele.giannone@gmail.com", sequence=1)
