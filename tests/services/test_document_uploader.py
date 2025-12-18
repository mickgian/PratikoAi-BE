"""Tests for DocumentUploader service.

TDD tests for Shannon entropy calculation fix (DEV-007).
"""

import pytest

from app.services.document_uploader import DocumentUploader


class TestCalculateEntropy:
    """Tests for the _calculate_entropy method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.uploader = DocumentUploader()

    def test_calculate_entropy_empty_data(self):
        """Empty data should have entropy = 0."""
        entropy = self.uploader._calculate_entropy(b"")
        assert entropy == 0.0

    def test_calculate_entropy_single_value(self):
        """Single repeated value should have entropy = 0."""
        # All zeros - no randomness
        data = b"\x00" * 100
        entropy = self.uploader._calculate_entropy(data)
        assert entropy == 0.0

    def test_calculate_entropy_two_values_equal(self):
        """Two equally distributed values should have entropy = 1.0."""
        # Half 0x00, half 0xFF - maximum entropy for 2 symbols
        data = b"\x00" * 50 + b"\xff" * 50
        entropy = self.uploader._calculate_entropy(data)
        assert 0.99 < entropy < 1.01  # Should be exactly 1.0

    def test_calculate_entropy_uniform_distribution(self):
        """Uniform byte distribution should have max entropy ~8.0 bits."""
        # All 256 byte values once - maximum entropy for bytes
        data = bytes(range(256))
        entropy = self.uploader._calculate_entropy(data)
        assert 7.99 < entropy < 8.01  # Should be exactly 8.0

    def test_calculate_entropy_returns_float(self):
        """Entropy should always return a float."""
        data = b"test data"
        entropy = self.uploader._calculate_entropy(data)
        assert isinstance(entropy, float)

    def test_calculate_entropy_non_negative(self):
        """Entropy should never be negative."""
        # Various test inputs
        test_data = [
            b"",
            b"\x00",
            b"hello world",
            bytes(range(256)),
            b"\x00\xff" * 100,
        ]
        for data in test_data:
            entropy = self.uploader._calculate_entropy(data)
            assert entropy >= 0.0, f"Entropy should be non-negative for {data!r}"
