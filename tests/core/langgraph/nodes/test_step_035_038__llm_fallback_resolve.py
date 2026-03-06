"""Tests for Step 35-38 Consolidated: LLM Fallback Resolution.

Validates that the merged node correctly handles LLM fallback,
comparison, and resolution in a single LangGraph node.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.langgraph.nodes.step_035_038__llm_fallback_resolve import node_step_35_38


class TestConsolidatedLLMFallbackResolve:
    """Tests for merged LLMFallback + LLMBetter + UseLLM + UseRuleBased node."""

    @pytest.mark.asyncio
    async def test_llm_better_uses_llm_classification(self):
        """When LLM is better, adopts LLM classification."""
        state = {
            "user_query": "test",
            "messages": [],
            "classification": {"domain": "generico", "confidence": 0.3},
        }

        with (
            patch(
                "app.orchestrators.classify.step_35__llm_fallback",
                new_callable=AsyncMock,
                return_value={
                    "llm_domain": "fiscale",
                    "llm_confidence": 0.9,
                    "fallback_used": True,
                },
            ),
            patch(
                "app.orchestrators.llm.step_36__llmbetter",
                new_callable=AsyncMock,
                return_value={"llm_is_better": True, "reasoning": "higher confidence"},
            ),
            patch(
                "app.orchestrators.llm.step_37__use_llm",
                new_callable=AsyncMock,
                return_value={"domain": "fiscale", "action": "info", "confidence": 0.9},
            ),
        ):
            result = await node_step_35_38(state)

        cls = result["classification"]
        assert cls["method_used"] == "llm"
        assert cls["domain"] == "fiscale"
        assert cls["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_rule_based_when_llm_not_better(self):
        """When LLM is not better, keeps rule-based classification."""
        state = {
            "user_query": "test",
            "messages": [],
            "classification": {"domain": "fiscale", "confidence": 0.7},
        }

        with (
            patch(
                "app.orchestrators.classify.step_35__llm_fallback",
                new_callable=AsyncMock,
                return_value={"llm_domain": "generico", "llm_confidence": 0.4},
            ),
            patch(
                "app.orchestrators.llm.step_36__llmbetter",
                new_callable=AsyncMock,
                return_value={"llm_is_better": False},
            ),
            patch(
                "app.orchestrators.platform.step_38__use_rule_based",
                new_callable=AsyncMock,
                return_value={"domain": "fiscale", "action": "info", "confidence": 0.7},
            ),
        ):
            result = await node_step_35_38(state)

        cls = result["classification"]
        assert cls["method_used"] == "rule_based"
        assert cls["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_error_in_llm_fallback_uses_rule_based(self):
        """LLM fallback error gracefully falls back to rule-based."""
        state = {
            "user_query": "test",
            "messages": [],
            "classification": {"domain": "fiscale", "confidence": 0.5},
        }

        with (
            patch(
                "app.orchestrators.classify.step_35__llm_fallback",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LLM error"),
            ),
            patch(
                "app.orchestrators.platform.step_38__use_rule_based",
                new_callable=AsyncMock,
                return_value={"domain": "fiscale", "action": "info", "confidence": 0.5},
            ),
        ):
            result = await node_step_35_38(state)

        cls = result["classification"]
        assert cls["method_used"] == "rule_based"

    @pytest.mark.asyncio
    async def test_preserves_llm_comparison_data(self):
        """Stores LLM comparison reasoning in classification."""
        state = {
            "user_query": "test",
            "messages": [],
            "classification": {},
        }

        with (
            patch(
                "app.orchestrators.classify.step_35__llm_fallback",
                new_callable=AsyncMock,
                return_value={"llm_domain": "fiscale", "llm_confidence": 0.8},
            ),
            patch(
                "app.orchestrators.llm.step_36__llmbetter",
                new_callable=AsyncMock,
                return_value={"llm_is_better": True, "reasoning": "LLM more precise"},
            ),
            patch(
                "app.orchestrators.llm.step_37__use_llm",
                new_callable=AsyncMock,
                return_value={"domain": "fiscale", "confidence": 0.8},
            ),
        ):
            result = await node_step_35_38(state)

        cls = result["classification"]
        assert cls["llm_is_better"] is True
        assert cls["comparison_reasoning"] == "LLM more precise"
