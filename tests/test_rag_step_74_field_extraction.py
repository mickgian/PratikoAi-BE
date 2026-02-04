"""Tests for DEV-254: Fix field extraction bugs in step_74__track_usage.

These tests verify that step 74 correctly handles the actual state structure
produced by step 64 (model_used, provider dict, llm_response dict).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.base import LLMResponse
from app.orchestrators.metrics import step_74__track_usage


class TestStep74ModelExtraction:
    """Tests for Bug 1: model field name mismatch."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_model_extracted_from_model_used(self, mock_tracker, mock_logger, mock_rag_log):
        """step_064 stores model as state['model_used'], step_074 must read it."""
        llm_response = LLMResponse(
            content="Test", model="gpt-4", provider="openai", tokens_used=100, cost_estimate=0.002
        )
        mock_tracker.track_llm_usage = AsyncMock(return_value=MagicMock())

        ctx = {
            "user_id": "user_1",
            "session_id": "sess_1",
            "provider": "openai",
            "model_used": "gpt-4",  # step_064 stores as model_used, NOT model
            "llm_response": llm_response,
            "response_time_ms": 500,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is True
        assert result["model"] == "gpt-4"
        mock_tracker.track_llm_usage.assert_called_once()
        assert mock_tracker.track_llm_usage.call_args[1]["model"] == "gpt-4"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_model_fallback_to_llm_dict(self, mock_tracker, mock_logger, mock_rag_log):
        """If model_used not at top-level, fall back to state['llm']['model_used']."""
        llm_response = LLMResponse(
            content="Test", model="gpt-4", provider="openai", tokens_used=100, cost_estimate=0.002
        )
        mock_tracker.track_llm_usage = AsyncMock(return_value=MagicMock())

        ctx = {
            "user_id": "user_1",
            "session_id": "sess_1",
            "provider": "openai",
            # model_used NOT at top level
            "llm": {"model_used": "gpt-4", "success": True},
            "llm_response": llm_response,
            "response_time_ms": 500,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is True
        assert result["model"] == "gpt-4"


class TestStep74ProviderExtraction:
    """Tests for Bug 2: provider type mismatch."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_provider_dict_unwrapped_to_string(self, mock_tracker, mock_logger, mock_rag_log):
        """step_064 stores provider as dict, step_074 must unwrap to string."""
        llm_response = LLMResponse(
            content="Test", model="gpt-4", provider="openai", tokens_used=100, cost_estimate=0.002
        )
        mock_tracker.track_llm_usage = AsyncMock(return_value=MagicMock())

        ctx = {
            "user_id": "user_1",
            "session_id": "sess_1",
            "provider": {"strategy": "cost_optimized", "selected": "openai", "estimate": 0.002},
            "model": "gpt-4",
            "llm_response": llm_response,
            "response_time_ms": 500,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is True
        assert result["provider"] == "openai"
        mock_tracker.track_llm_usage.assert_called_once()
        assert mock_tracker.track_llm_usage.call_args[1]["provider"] == "openai"

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_provider_dict_without_selected_key(self, mock_tracker, mock_logger, mock_rag_log):
        """Provider dict missing 'selected' key should log warning and skip tracking."""
        llm_response = LLMResponse(
            content="Test", model="gpt-4", provider="openai", tokens_used=100, cost_estimate=0.002
        )

        ctx = {
            "user_id": "user_1",
            "session_id": "sess_1",
            "provider": {"strategy": "cost_optimized"},  # missing "selected"
            "model": "gpt-4",
            "llm_response": llm_response,
            "response_time_ms": 500,
        }

        result = await step_74__track_usage(ctx=ctx)

        # provider is None after unwrap -> validation fails
        assert result["usage_tracked"] is False
        assert result["error"] is not None
        mock_tracker.track_llm_usage.assert_not_called()


class TestStep74LLMResponseExtraction:
    """Tests for Bug 3: llm_response type mismatch."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_llm_response_dict_handled(self, mock_tracker, mock_logger, mock_rag_log):
        """llm_response stored as dict must be converted to LLMResponse-compatible object."""
        mock_tracker.track_llm_usage = AsyncMock(return_value=MagicMock())

        ctx = {
            "user_id": "user_1",
            "session_id": "sess_1",
            "provider": "openai",
            "model": "gpt-4",
            "llm_response": {"content": "Test response"},  # dict, not LLMResponse
            "llm": {
                "model_used": "gpt-4",
                "tokens_used": {"input": 80, "output": 20},
                "cost_estimate": 0.002,
            },
            "response_time_ms": 500,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is True
        assert result["total_tokens"] == 100
        assert result["cost"] == 0.002

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_llm_response_dict_no_token_data_defaults_to_zero(self, mock_tracker, mock_logger, mock_rag_log):
        """Dict llm_response without token data in llm dict should default to 0 tokens."""
        mock_tracker.track_llm_usage = AsyncMock(return_value=MagicMock())

        ctx = {
            "user_id": "user_1",
            "session_id": "sess_1",
            "provider": "openai",
            "model": "gpt-4",
            "llm_response": {"content": "Test response"},  # dict
            # no llm dict with tokens
            "response_time_ms": 500,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is True
        assert result["total_tokens"] == 0
        assert result["cost"] == 0.0

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_llm_response_none_fails_validation(self, mock_tracker, mock_logger, mock_rag_log):
        """llm_response not in state at all should fail validation."""
        ctx = {
            "user_id": "user_1",
            "session_id": "sess_1",
            "provider": "openai",
            "model": "gpt-4",
            # no llm_response
            "response_time_ms": 500,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is False
        assert result["error"] == "Missing required usage tracking data"
        mock_tracker.track_llm_usage.assert_not_called()


class TestStep74MissingModel:
    """Tests for missing model edge case."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_missing_model_logs_error(self, mock_tracker, mock_logger, mock_rag_log):
        """No model anywhere in state should log error and not track."""
        llm_response = LLMResponse(
            content="Test", model="gpt-4", provider="openai", tokens_used=100, cost_estimate=0.002
        )

        ctx = {
            "user_id": "user_1",
            "session_id": "sess_1",
            "provider": "openai",
            # no model, no model_used, no llm.model_used
            "llm_response": llm_response,
            "response_time_ms": 500,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is False
        assert result["error"] == "Missing required usage tracking data"
        mock_logger.error.assert_called_once()


class TestStep74CombinedRealWorldState:
    """Integration-style tests simulating the actual state shape from step_064."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.metrics.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.usage_tracker.usage_tracker")
    async def test_real_world_state_from_step_064(self, mock_tracker, mock_logger, mock_rag_log):
        """Simulate the exact state shape produced by node_step_64."""
        mock_tracker.track_llm_usage = AsyncMock(return_value=MagicMock())

        # This is what state actually looks like after step_064 runs
        ctx = {
            "user_id": "user_1",
            "session_id": "sess_1",
            "provider": {"strategy": "cost_optimized", "selected": "openai", "estimate": 0.003},
            "model_used": "gpt-4",
            "llm_response": {"content": "La risposta legale..."},
            "llm": {
                "model_used": "gpt-4",
                "success": True,
                "response": {"content": "La risposta legale..."},
                "tokens_used": {"input": 120, "output": 30},
                "cost_estimate": 0.003,
            },
            "response_time_ms": 2500,
            "cache_hit": False,
            "pii_detected": False,
        }

        result = await step_74__track_usage(ctx=ctx)

        assert result["usage_tracked"] is True
        assert result["model"] == "gpt-4"
        assert result["provider"] == "openai"
        assert result["total_tokens"] == 150
        assert result["cost"] == 0.003
