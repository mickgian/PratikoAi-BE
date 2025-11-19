"""Tests for HashGate duplicate content detection."""

import pytest

from app.core.hash_gate import HashGate


class TestHashGate:
    """Test HashGate duplicate detection functionality."""

    def test_hash_gate_initialization(self):
        """Test HashGate initialization."""
        gate = HashGate("test-stream-123")
        assert gate.stream_id == "test-stream-123"
        assert len(gate.seen_hashes) == 0
        assert gate.delta_count == 0

    def test_check_delta_with_new_content(self):
        """Test checking a new delta passes through."""
        gate = HashGate("test-stream")
        gate.check_delta("Hello, world!", seq=1)
        assert gate.delta_count == 1
        assert len(gate.seen_hashes) == 1

    def test_check_delta_with_empty_string(self):
        """Test empty delta is skipped."""
        gate = HashGate("test-stream")
        gate.check_delta("", seq=1)
        assert gate.delta_count == 0
        assert len(gate.seen_hashes) == 0

    def test_check_delta_with_none(self):
        """Test None delta is skipped."""
        gate = HashGate("test-stream")
        gate.check_delta(None, seq=1)
        assert gate.delta_count == 0
        assert len(gate.seen_hashes) == 0

    def test_check_delta_duplicate_raises_error(self):
        """Test duplicate delta raises RuntimeError."""
        gate = HashGate("test-stream")
        delta = "This is a test delta"

        # First check should pass
        gate.check_delta(delta, seq=1)
        assert gate.delta_count == 1

        # Second check with same content should raise
        with pytest.raises(RuntimeError, match="Duplicate hash .* detected"):
            gate.check_delta(delta, seq=2)

    def test_check_delta_different_content(self):
        """Test different deltas don't trigger duplicate detection."""
        gate = HashGate("test-stream")

        gate.check_delta("First delta", seq=1)
        gate.check_delta("Second delta", seq=2)
        gate.check_delta("Third delta", seq=3)

        assert gate.delta_count == 3
        assert len(gate.seen_hashes) == 3

    def test_check_delta_similar_but_different(self):
        """Test similar but different content doesn't trigger duplicate."""
        gate = HashGate("test-stream")

        gate.check_delta("Hello, world!", seq=1)
        gate.check_delta("Hello, world?", seq=2)  # Different punctuation
        gate.check_delta("Hello, World!", seq=3)  # Different capitalization

        assert gate.delta_count == 3
        assert len(gate.seen_hashes) == 3

    def test_check_delta_with_long_content(self):
        """Test long delta content is handled correctly."""
        gate = HashGate("test-stream")
        long_content = "A" * 1000

        gate.check_delta(long_content, seq=1)
        assert gate.delta_count == 1

        # Duplicate should still be detected
        with pytest.raises(RuntimeError):
            gate.check_delta(long_content, seq=2)

    def test_check_delta_unicode_content(self):
        """Test Unicode content is handled correctly."""
        gate = HashGate("test-stream")

        gate.check_delta("Ciao, mondo! 🇮🇹", seq=1)
        gate.check_delta("Über schön €100", seq=2)
        gate.check_delta("日本語テキスト", seq=3)

        assert gate.delta_count == 3
        assert len(gate.seen_hashes) == 3

    def test_multiple_streams_independent(self):
        """Test different stream IDs maintain independent state."""
        gate1 = HashGate("stream-1")
        gate2 = HashGate("stream-2")

        delta = "Same content in both streams"

        # Should pass for both streams independently
        gate1.check_delta(delta, seq=1)
        gate2.check_delta(delta, seq=1)

        assert gate1.delta_count == 1
        assert gate2.delta_count == 1

    def test_hash_truncation(self):
        """Test that hashes are truncated to 12 characters."""
        gate = HashGate("test-stream")
        gate.check_delta("Test content", seq=1)

        # All hashes should be 12 characters or less
        for hash_val in gate.seen_hashes:
            assert len(hash_val) <= 12

    def test_check_delta_sequential_numbers(self):
        """Test delta counting is sequential."""
        gate = HashGate("test-stream")

        for i in range(10):
            gate.check_delta(f"Delta {i}", seq=i)

        assert gate.delta_count == 10
        assert len(gate.seen_hashes) == 10

    def test_check_delta_whitespace_variants(self):
        """Test whitespace differences create different hashes."""
        gate = HashGate("test-stream")

        gate.check_delta("Hello world", seq=1)
        gate.check_delta("Hello  world", seq=2)  # Double space
        gate.check_delta("Hello\nworld", seq=3)  # Newline

        assert gate.delta_count == 3
        assert len(gate.seen_hashes) == 3
