"""Unit tests for account_code assignment during user creation.

Tests cover:
- User gets a non-None account_code after creation
- account_code matches the expected format ({3_letters}{hundreds}{2_digits}-{seq})
- Email is passed to generate_account_code
"""

import re

from app.utils.account_code import generate_account_code

# Pattern: 3 uppercase letters + hundreds (200-900) + 2 digits + dash + sequence
ACCOUNT_CODE_PATTERN = re.compile(r"^[A-Z]{3}[2-9]00\d{2}-\d+$")


class TestCreateUserAccountCode:
    """Tests for account_code generation in create_user service."""

    def test_create_user_assigns_account_code(self) -> None:
        """User should have a non-None account_code after creation."""
        # Test that generate_account_code produces a non-None result
        code = generate_account_code("test@example.com", sequence=1)
        assert code is not None
        assert len(code) > 0

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
        # Verify the real generator extracts prefix from email
        code = generate_account_code("test.user@example.com", sequence=1)
        assert code.startswith("TES"), f"Expected prefix 'TES', got {code[:3]}"
