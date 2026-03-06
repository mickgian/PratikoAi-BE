"""Tests for Step 31+32 Consolidated: Classify Domain and Calculate Scores.

Validates that the merged node produces identical output to the
original separate steps 31 and 32.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.langgraph.nodes.step_031_032__classify_and_score import node_step_31_32


class TestConsolidatedClassifyAndScore:
    """Tests for merged ClassifyDomain + CalcScores node."""

    @pytest.mark.asyncio
    async def test_returns_classification_with_scores(self):
        """Combined node produces both classification and score data."""
        state = {
            "user_query": "Come calcolare le tasse?",
            "messages": [{"role": "user", "content": "Come calcolare le tasse?"}],
            "classification": {},
        }

        with (
            patch(
                "app.orchestrators.classify.step_31__classify_domain",
                new_callable=AsyncMock,
                return_value={
                    "domain": "fiscale",
                    "confidence": 0.85,
                    "fallback_used": False,
                    "classification": {
                        "domain": "fiscale",
                        "confidence": 0.85,
                    },
                },
            ),
            patch(
                "app.orchestrators.classify.step_32__calc_scores",
                new_callable=AsyncMock,
                return_value={
                    "domain_scores": {"fiscale": 0.85},
                    "action_scores": {"info": 0.9},
                    "matched_keywords": ["tasse"],
                },
            ),
        ):
            result = await node_step_31_32(state)

        assert "classification" in result
        cls = result["classification"]
        assert cls.get("domain") == "fiscale"
        assert cls.get("confidence") == 0.85
        assert "domain_scores" in cls
        assert "action_scores" in cls
        assert "matched_keywords" in cls

    @pytest.mark.asyncio
    async def test_preserves_existing_state(self):
        """Combined node preserves all other state keys."""
        state = {
            "user_query": "test",
            "messages": [],
            "classification": {},
            "user_id": "u1",
            "session_id": "s1",
        }

        with (
            patch(
                "app.orchestrators.classify.step_31__classify_domain",
                new_callable=AsyncMock,
                return_value={"domain": "test", "confidence": 0.5},
            ),
            patch(
                "app.orchestrators.classify.step_32__calc_scores",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await node_step_31_32(state)

        assert result["user_id"] == "u1"
        assert result["session_id"] == "s1"

    @pytest.mark.asyncio
    async def test_stores_query_composition(self):
        """Query composition from step 31 is stored in state."""
        state = {
            "user_query": "test",
            "messages": [],
            "classification": {},
        }

        with (
            patch(
                "app.orchestrators.classify.step_31__classify_domain",
                new_callable=AsyncMock,
                return_value={
                    "domain": "fiscale",
                    "confidence": 0.8,
                    "query_composition": {"type": "question"},
                },
            ),
            patch(
                "app.orchestrators.classify.step_32__calc_scores",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await node_step_31_32(state)

        assert result["query_composition"] == {"type": "question"}
