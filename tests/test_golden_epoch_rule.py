"""Unit tests for Golden fast-path epoch invalidation."""

import pytest
from app.services.golden_fast_path import GoldenFastPathService


class TestGoldenEpochRule:
    """Test suite for Golden epoch checking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = GoldenFastPathService()

    def test_serve_golden_when_kb_epoch_equal(self):
        """Test that Golden is served when kb_epoch == golden_epoch."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.95,
            kb_epoch=100,
            golden_epoch=100
        )

        assert can_serve == True

    def test_serve_golden_when_kb_epoch_older(self):
        """Test that Golden is served when kb_epoch < golden_epoch."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.95,
            kb_epoch=99,
            golden_epoch=100
        )

        assert can_serve == True

    def test_reject_golden_when_kb_epoch_newer(self):
        """Test that Golden is rejected when kb_epoch > golden_epoch."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.95,
            kb_epoch=101,
            golden_epoch=100
        )

        assert can_serve == False

    def test_reject_golden_when_confidence_low(self):
        """Test that Golden is rejected when confidence is too low."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.85,  # Below default threshold of 0.90
            kb_epoch=100,
            golden_epoch=100
        )

        assert can_serve == False

    def test_serve_golden_at_exact_threshold(self):
        """Test that Golden is served at exact confidence threshold."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.90,  # Exactly at threshold
            kb_epoch=100,
            golden_epoch=100
        )

        assert can_serve == True

    def test_custom_confidence_threshold(self):
        """Test that custom confidence threshold works."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.85,
            kb_epoch=100,
            golden_epoch=100,
            confidence_threshold=0.80  # Custom lower threshold
        )

        assert can_serve == True

    def test_reject_golden_both_conditions_fail(self):
        """Test that Golden is rejected when both conditions fail."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.85,  # Too low
            kb_epoch=101,  # KB newer
            golden_epoch=100
        )

        assert can_serve == False

    def test_large_epoch_difference(self):
        """Test with large epoch difference."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.95,
            kb_epoch=200,
            golden_epoch=100  # KB is 100 epochs newer
        )

        assert can_serve == False

    def test_zero_epochs(self):
        """Test with epoch 0 (initial state)."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.95,
            kb_epoch=0,
            golden_epoch=0
        )

        assert can_serve == True

    def test_negative_epoch_difference(self):
        """Test when Golden is from future epoch (shouldn't happen but test anyway)."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.95,
            kb_epoch=50,
            golden_epoch=100  # Golden from future?
        )

        # Should still serve since kb_epoch <= golden_epoch
        assert can_serve == True

    def test_high_confidence_low_epoch(self):
        """Test perfect confidence but stale Golden."""
        can_serve = self.service.can_serve_from_golden(
            confidence=1.0,  # Perfect match
            kb_epoch=200,  # But KB is much newer
            golden_epoch=100
        )

        # Should reject - epoch rule takes precedence
        assert can_serve == False

    def test_borderline_confidence_fresh_golden(self):
        """Test borderline confidence with fresh Golden."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.90,  # Just at threshold
            kb_epoch=100,  # Golden is fresh
            golden_epoch=100
        )

        assert can_serve == True

    def test_confidence_just_below_threshold(self):
        """Test confidence just below threshold."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.8999,  # Just below 0.90
            kb_epoch=100,
            golden_epoch=100
        )

        assert can_serve == False

    def test_kb_epoch_one_higher(self):
        """Test KB epoch exactly one higher than Golden."""
        can_serve = self.service.can_serve_from_golden(
            confidence=0.95,
            kb_epoch=101,
            golden_epoch=100
        )

        # Should reject even with small difference
        assert can_serve == False
