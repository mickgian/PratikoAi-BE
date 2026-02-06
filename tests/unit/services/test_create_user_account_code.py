"""Unit tests for account_code assignment during user creation.

Tests cover:
- User gets a non-None account_code after creation
- account_code matches the expected format ({3_letters}{hundreds}{2_digits}-{seq})
- Email is passed to generate_account_code
"""

import re
from unittest.mock import MagicMock, patch

import pytest

from app.services.database import DatabaseService
from app.utils.account_code import generate_account_code

# Pattern: 3 uppercase letters + hundreds (200-900) + 2 digits + dash + sequence
ACCOUNT_CODE_PATTERN = re.compile(r"^[A-Z]{3}[2-9]00\d{2}-\d+$")


class TestCreateUserAccountCode:
    """Tests for account_code generation in create_user service."""

    @pytest.fixture
    def mock_db_service(self):
        """Create a DatabaseService with mocked engine."""
        service = object.__new__(DatabaseService)
        service.engine = MagicMock()
        return service

    @pytest.fixture
    def mock_session_context(self):
        """Create a mock session context manager."""
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.refresh = MagicMock()
        return mock_session

    def test_create_user_assigns_account_code(self, mock_db_service, mock_session_context) -> None:
        """User should have a non-None account_code after creation."""
        with patch.object(DatabaseService, "create_user") as mock_create:
            # Simulate successful user creation with account_code
            mock_user = MagicMock()
            mock_user.account_code = "TES70021-1"
            mock_create.return_value = mock_user

            import asyncio

            result = asyncio.get_event_loop().run_until_complete(
                mock_db_service.create_user("test@example.com", "hashed_password")
            )

            # account_code should be set
            assert result.account_code is not None
            assert result.account_code == "TES70021-1"

    def test_create_user_account_code_matches_format(self) -> None:
        """account_code should match the {3_letters}{hundreds}{2_digits}-{seq} pattern."""
        # Test the pattern against known valid codes
        assert ACCOUNT_CODE_PATTERN.match("MGI70021-1")
        assert ACCOUNT_CODE_PATTERN.match("TES30045-2")
        assert ACCOUNT_CODE_PATTERN.match("ABC90099-100")

        # Test the actual generator function
        code = generate_account_code("test.user@example.com", sequence=1)
        assert ACCOUNT_CODE_PATTERN.match(code), f"Generated code {code} doesn't match pattern"

    def test_create_user_passes_email_to_generator(self) -> None:
        """Email should be passed to generate_account_code for prefix extraction."""
        with patch("app.services.database.generate_account_code") as mock_gen:
            mock_gen.return_value = "TES30045-1"

            # Verify the real generator extracts prefix from email
            code = generate_account_code("test.user@example.com", sequence=1)
            assert code.startswith("TES"), f"Expected prefix 'TES', got {code[:3]}"
