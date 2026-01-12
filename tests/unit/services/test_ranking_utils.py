"""Tests for ranking utilities (DEV-242 Phase 11).

Tests for tier-based ranking multipliers and source authority boosts.
"""

import pytest

from app.services.ranking_utils import (
    TIER_MULTIPLIERS,
    get_source_authority_boost,
    get_tier_multiplier,
)


class TestTierMultiplier:
    """Tests for DEV-242 Phase 11: Tier-based ranking."""

    def test_tier_1_gets_highest_multiplier(self):
        """Tier 1 (laws) gets 1.25x boost."""
        assert get_tier_multiplier(1) == 1.25

    def test_tier_2_gets_moderate_multiplier(self):
        """Tier 2 (circulars) gets 1.10x boost."""
        assert get_tier_multiplier(2) == 1.10

    def test_tier_3_gets_penalty(self):
        """Tier 3 (news) gets 0.80x penalty."""
        assert get_tier_multiplier(3) == 0.80

    def test_none_tier_gets_neutral(self):
        """Unclassified docs get 1.0 (neutral)."""
        assert get_tier_multiplier(None) == 1.0

    def test_unknown_tier_gets_neutral(self):
        """Unknown tier values get 1.0 (neutral)."""
        assert get_tier_multiplier(99) == 1.0
        assert get_tier_multiplier(0) == 1.0
        assert get_tier_multiplier(-1) == 1.0

    def test_tier_multipliers_constant_has_expected_values(self):
        """TIER_MULTIPLIERS constant has expected configuration."""
        assert TIER_MULTIPLIERS == {
            1: 1.25,
            2: 1.10,
            3: 0.80,
        }


class TestSourceAuthorityBoost:
    """Tests for source authority boost (existing functionality)."""

    def test_official_sources_get_highest_boost(self):
        """Official sources (ADE, INPS) get 0.15 boost."""
        assert get_source_authority_boost("agenzia_entrate_normativa") == 0.15
        assert get_source_authority_boost("inps_circolari") == 0.15
        assert get_source_authority_boost("gazzetta_ufficiale") == 0.15

    def test_semi_official_sources_get_moderate_boost(self):
        """Semi-official sources get 0.10 boost."""
        assert get_source_authority_boost("confindustria") == 0.10
        assert get_source_authority_boost("ordine_commercialisti") == 0.10

    def test_unknown_sources_get_no_boost(self):
        """Unknown sources get 0.0 boost."""
        assert get_source_authority_boost("unknown_source") == 0.0
        assert get_source_authority_boost("blog_post") == 0.0

    def test_none_source_gets_no_boost(self):
        """None source gets 0.0 boost."""
        assert get_source_authority_boost(None) == 0.0

    def test_empty_source_gets_no_boost(self):
        """Empty string source gets 0.0 boost."""
        assert get_source_authority_boost("") == 0.0
        assert get_source_authority_boost("   ") == 0.0


class TestTierMultiplierRankingImpact:
    """Integration-style tests showing tier impact on ranking."""

    def test_tier_1_law_outranks_tier_3_news_with_equal_base_score(self):
        """Tier 1 law outranks Tier 3 news when base scores are equal."""
        base_score = 0.80

        law_score = base_score * get_tier_multiplier(1)  # 0.80 * 1.25 = 1.0
        news_score = base_score * get_tier_multiplier(3)  # 0.80 * 0.80 = 0.64

        assert law_score > news_score
        assert law_score == pytest.approx(1.0)
        assert news_score == pytest.approx(0.64)

    def test_tier_1_law_outranks_higher_scoring_news(self):
        """Tier 1 law at 0.78 outranks Tier 3 news at 0.85 after multipliers."""
        law_base = 0.78
        news_base = 0.85

        law_score = law_base * get_tier_multiplier(1)  # 0.78 * 1.25 = 0.975
        news_score = news_base * get_tier_multiplier(3)  # 0.85 * 0.80 = 0.68

        assert law_score > news_score
        assert law_score == pytest.approx(0.975)
        assert news_score == pytest.approx(0.68)
