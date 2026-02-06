"""Unit tests for account code generator utility.

Tests cover:
- Format validation ({3_letters}{hundreds}{2_digits}-{sequence})
- Email prefix extraction (first 3 alphabetic chars)
- Uniqueness across multiple generations
- Length constraint (max_length=20)
"""

import re

import pytest

from app.utils.account_code import generate_account_code

# Pattern: 3 uppercase letters + hundreds (200-900) + 2 digits + dash + sequence
# Example: MGI70021-1
ACCOUNT_CODE_PATTERN = re.compile(r"^[A-Z]{3}[2-9]00\d{2}-\d+$")


class TestGenerateAccountCode:
    """Tests for generate_account_code function."""

    def test_generate_account_code_format(self) -> None:
        """Generated code should match {3_letters}{hundreds}{2_digits}-{seq} format."""
        code = generate_account_code(email="michele.giannone@gmail.com", sequence=1)
        assert ACCOUNT_CODE_PATTERN.match(code), f"Code '{code}' does not match expected pattern"

    def test_generate_account_code_email_prefix_extraction(self) -> None:
        """Email prefix should be first 3 alphabetic characters uppercased."""
        code = generate_account_code(email="michele.giannone@gmail.com", sequence=1)
        assert code.startswith("MIC"), f"Code '{code}' should start with 'MIC'"

    def test_generate_account_code_email_with_numbers(self) -> None:
        """Email with numbers should skip non-alphabetic characters."""
        code = generate_account_code(email="user123test@example.com", sequence=1)
        assert code.startswith("USE"), f"Code '{code}' should start with 'USE' (skipping numbers)"

    def test_generate_account_code_short_email_prefix(self) -> None:
        """Email with <3 alphabetic chars should be padded with X."""
        code = generate_account_code(email="ab@example.com", sequence=1)
        assert code.startswith("ABX"), f"Code '{code}' should start with 'ABX' (padded)"

    def test_generate_account_code_uniqueness(self) -> None:
        """Two consecutive calls should produce different codes (random part)."""
        code1 = generate_account_code(email="test@example.com", sequence=1)
        code2 = generate_account_code(email="test@example.com", sequence=2)
        assert code1 != code2

    def test_generate_account_code_length_under_20(self) -> None:
        """Generated code should fit within max_length=20."""
        code = generate_account_code(email="test@example.com", sequence=1)
        assert len(code) <= 20, f"Code '{code}' is {len(code)} chars, exceeds 20"

    def test_generate_account_code_with_large_sequence(self) -> None:
        """Code should still be valid with larger sequence numbers."""
        code = generate_account_code(email="test@example.com", sequence=999)
        assert ACCOUNT_CODE_PATTERN.match(code)
        assert len(code) <= 20

    def test_generate_account_code_default_sequence(self) -> None:
        """Default sequence should be 1."""
        code = generate_account_code(email="test@example.com")
        assert code.endswith("-1")

    def test_generate_account_code_hundreds_in_valid_range(self) -> None:
        """Hundreds component should be in 200-900 range."""
        # Generate multiple codes to verify the random hundreds
        for _ in range(20):
            code = generate_account_code(email="test@example.com", sequence=1)
            # Extract hundreds (chars 3-6, e.g., "TES700" -> "700")
            hundreds = int(code[3:6])
            assert hundreds in [200, 300, 400, 500, 600, 700, 800, 900], f"Hundreds '{hundreds}' not in valid range"
