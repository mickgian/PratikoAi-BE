"""Tests for DEV-254/DEV-257: node_step_74 wrapper correctly extracts fields from RAGState."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestNodeStep74FieldExtraction:
    """Verify node wrapper extracts model/provider from RAGState before calling orchestrator."""

    @pytest.mark.asyncio
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_log")
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_timer")
    @patch("app.core.langgraph.nodes.step_074__track_usage.step_74__track_usage", new_callable=AsyncMock)
    async def test_passes_model_used_as_kwarg(self, mock_orchestrator, mock_timer, mock_log):
        """node_step_74 should extract model_used from state and pass as model kwarg."""
        from app.core.langgraph.nodes.step_074__track_usage import node_step_74

        mock_orchestrator.return_value = {"usage_tracked": True}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        state = {
            "model_used": "gpt-4",
            "provider": "openai",
            "messages": [],
        }

        await node_step_74(state)

        mock_orchestrator.assert_called_once()
        call_kwargs = mock_orchestrator.call_args[1]
        assert call_kwargs["model"] == "gpt-4"

    @pytest.mark.asyncio
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_log")
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_timer")
    @patch("app.core.langgraph.nodes.step_074__track_usage.step_74__track_usage", new_callable=AsyncMock)
    async def test_passes_model_from_llm_dict_fallback(self, mock_orchestrator, mock_timer, mock_log):
        """node_step_74 should fallback to llm.model_used if model_used not at top level."""
        from app.core.langgraph.nodes.step_074__track_usage import node_step_74

        mock_orchestrator.return_value = {"usage_tracked": True}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        state = {
            "llm": {"model_used": "gpt-4"},
            "provider": "openai",
            "messages": [],
        }

        await node_step_74(state)

        call_kwargs = mock_orchestrator.call_args[1]
        assert call_kwargs["model"] == "gpt-4"

    @pytest.mark.asyncio
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_log")
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_timer")
    @patch("app.core.langgraph.nodes.step_074__track_usage.step_74__track_usage", new_callable=AsyncMock)
    async def test_unwraps_provider_dict_to_selected(self, mock_orchestrator, mock_timer, mock_log):
        """node_step_74 should unwrap provider dict to the 'selected' string value."""
        from app.core.langgraph.nodes.step_074__track_usage import node_step_74

        mock_orchestrator.return_value = {"usage_tracked": True}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        state = {
            "model_used": "gpt-4",
            "provider": {"strategy": "cost_optimized", "selected": "openai", "estimate": 0.003},
            "messages": [],
        }

        await node_step_74(state)

        call_kwargs = mock_orchestrator.call_args[1]
        assert call_kwargs["provider"] == "openai"

    @pytest.mark.asyncio
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_log")
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_timer")
    @patch("app.core.langgraph.nodes.step_074__track_usage.step_74__track_usage", new_callable=AsyncMock)
    async def test_passes_string_provider_unchanged(self, mock_orchestrator, mock_timer, mock_log):
        """node_step_74 should pass string provider unchanged."""
        from app.core.langgraph.nodes.step_074__track_usage import node_step_74

        mock_orchestrator.return_value = {"usage_tracked": True}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        state = {
            "model_used": "gpt-4",
            "provider": "anthropic",
            "messages": [],
        }

        await node_step_74(state)

        call_kwargs = mock_orchestrator.call_args[1]
        assert call_kwargs["provider"] == "anthropic"


class TestNodeStep74ProviderTypeFallback:
    """DEV-257: CheapProvider (step_051) stores provider as 'provider_type', not 'selected'."""

    @pytest.mark.asyncio
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_log")
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_timer")
    @patch("app.core.langgraph.nodes.step_074__track_usage.step_74__track_usage", new_callable=AsyncMock)
    async def test_extracts_provider_type_when_selected_missing(self, mock_orchestrator, mock_timer, mock_log):
        """DEV-257: provider dict from CheapProvider has 'provider_type' but no 'selected'."""
        from app.core.langgraph.nodes.step_074__track_usage import node_step_74

        mock_orchestrator.return_value = {"usage_tracked": True}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # This is the actual state shape from CheapProvider (step_051)
        state = {
            "model_used": "gpt-4o",
            "provider": {
                "strategy": "CHEAP",
                "provider_type": "openai",
                "model": "gpt-4o",
                "cost_per_token": 0.00001,
            },
            "messages": [],
        }

        await node_step_74(state)

        call_kwargs = mock_orchestrator.call_args[1]
        assert call_kwargs["provider"] == "openai"

    @pytest.mark.asyncio
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_log")
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_timer")
    @patch("app.core.langgraph.nodes.step_074__track_usage.step_74__track_usage", new_callable=AsyncMock)
    async def test_prefers_selected_over_provider_type(self, mock_orchestrator, mock_timer, mock_log):
        """When both 'selected' and 'provider_type' exist, prefer 'selected'."""
        from app.core.langgraph.nodes.step_074__track_usage import node_step_74

        mock_orchestrator.return_value = {"usage_tracked": True}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        state = {
            "model_used": "gpt-4o",
            "provider": {
                "selected": "anthropic",
                "provider_type": "openai",
            },
            "messages": [],
        }

        await node_step_74(state)

        call_kwargs = mock_orchestrator.call_args[1]
        assert call_kwargs["provider"] == "anthropic"

    @pytest.mark.asyncio
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_log")
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_timer")
    @patch("app.core.langgraph.nodes.step_074__track_usage.step_74__track_usage", new_callable=AsyncMock)
    async def test_falls_back_to_name_when_both_missing(self, mock_orchestrator, mock_timer, mock_log):
        """Falls back to 'name' key when both 'selected' and 'provider_type' are absent."""
        from app.core.langgraph.nodes.step_074__track_usage import node_step_74

        mock_orchestrator.return_value = {"usage_tracked": True}
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        state = {
            "model_used": "gpt-4o",
            "provider": {"name": "openai", "model": "gpt-4o"},
            "messages": [],
        }

        await node_step_74(state)

        call_kwargs = mock_orchestrator.call_args[1]
        assert call_kwargs["provider"] == "openai"
