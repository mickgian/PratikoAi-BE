"""Test LLM success and cache response path in Phase 4 lane."""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.langgraph.nodes.step_064__llm_call import node_step_64
from app.core.langgraph.nodes.step_067__llm_success import node_step_67
from app.core.langgraph.nodes.step_068__cache_response import node_step_68
from app.core.langgraph.nodes.step_074__track_usage import node_step_74
from app.core.langgraph.types import RAGState


class TestPhase4LLMSuccessAndCache:
    """Test suite for Phase 4 LLM success and cache response path."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_state = RAGState(
            messages=[{"role": "user", "content": "test message"}], session_id="test-session-123"
        )

    @patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall")
    @patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_log")
    @patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_64_llm_call_success(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 64: LLMCall node with successful response."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "llm_request": {"messages": ["test"], "model": "gpt-4"},
            "llm_response": {"content": "LLM response", "cost": 0.01},
            "provider_used": "openai",
        }

        # Execute
        result = await node_step_64(self.sample_state)

        # Assert LLM state structure
        assert "llm" in result
        assert result["llm"]["request"] == {"messages": ["test"], "model": "gpt-4"}
        assert result["llm"]["response"] == {"content": "LLM response", "cost": 0.01}
        assert result["llm"]["success"] is True

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(64)

    @patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall")
    @patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_log")
    @patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_64_llm_call_failure(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 64: LLMCall node with failed response."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "llm_request": {"messages": ["test"], "model": "gpt-4"},
            "llm_response": None,  # Failed call
            "error": "API timeout",
        }

        # Execute
        result = await node_step_64(self.sample_state)

        # Assert LLM state structure for failure
        assert "llm" in result
        assert result["llm"]["request"] == {"messages": ["test"], "model": "gpt-4"}
        assert result["llm"]["response"] is None
        assert result["llm"]["success"] is False

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(64)

    @patch("app.core.langgraph.nodes.step_067__llm_success.step_67__llmsuccess")
    @patch("app.core.langgraph.nodes.step_067__llm_success.rag_step_log")
    @patch("app.core.langgraph.nodes.step_067__llm_success.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_67_llm_success_decision(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 67: LLMSuccess node sets decision for routing."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {}

        # Set up state with successful LLM call
        state_with_llm = self.sample_state.copy()
        state_with_llm["llm"] = {
            "request": {"messages": ["test"]},
            "response": {"content": "success"},
            "success": True,
        }

        # Execute
        result = await node_step_67(state_with_llm)

        # Assert decision is set for routing
        assert result["llm_success_decision"] is True

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(67)

    @patch("app.core.langgraph.nodes.step_067__llm_success.step_67__llmsuccess")
    @patch("app.core.langgraph.nodes.step_067__llm_success.rag_step_log")
    @patch("app.core.langgraph.nodes.step_067__llm_success.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_67_llm_failure_decision(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 67: LLMSuccess node with failure routes to retry."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {}

        # Set up state with failed LLM call
        state_with_llm = self.sample_state.copy()
        state_with_llm["llm"] = {"request": {"messages": ["test"]}, "response": None, "success": False}

        # Execute
        result = await node_step_67(state_with_llm)

        # Assert decision is set for routing to retry
        assert result["llm_success_decision"] is False

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(67)

    @patch("app.core.langgraph.nodes.step_068__cache_response.step_68__cache_response")
    @patch("app.core.langgraph.nodes.step_068__cache_response.rag_step_log")
    @patch("app.core.langgraph.nodes.step_068__cache_response.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_68_cache_response(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 68: CacheResponse node caches successful LLM response."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {"cache_key": "generated-cache-key", "cached": True, "cache_ttl": 3600}

        # Set up state with successful LLM response
        state_with_llm = self.sample_state.copy()
        state_with_llm["llm"] = {
            "request": {"messages": ["test"]},
            "response": {"content": "LLM response"},
            "success": True,
        }

        # Execute
        result = await node_step_68(state_with_llm)

        # Assert response is cached
        assert "cache_key" in result
        assert result["cached"] is True

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(68)

    @patch("app.core.langgraph.nodes.step_074__track_usage.step_74__track_usage")
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_log")
    @patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_74_track_usage(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 74: TrackUsage node tracks LLM usage metrics."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "usage_tracked": True,
            "metrics": {"tokens_used": 150, "cost_eur": 0.01, "response_time_ms": 1200},
        }

        # Set up state with LLM response
        state_with_llm = self.sample_state.copy()
        state_with_llm["llm"] = {"response": {"content": "LLM response"}, "success": True}

        # Execute
        result = await node_step_74(state_with_llm)

        # Assert usage is tracked
        assert result["usage_tracked"] is True
        assert "metrics" in result

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(74)

    @pytest.mark.asyncio
    async def test_llm_success_flow_end_to_end(self):
        """Test complete LLM success flow: LLMCall → LLMSuccess → CacheResponse → TrackUsage."""

        # Step 64: LLMCall sets LLM state
        with patch("app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall") as mock_64:
            with patch("app.core.langgraph.nodes.step_064__llm_call.rag_step_timer"):
                mock_64.return_value = {
                    "llm_request": {"messages": ["test"]},
                    "llm_response": {"content": "success"},
                }

                state_after_64 = await node_step_64(self.sample_state)

                # Verify LLM state is populated
                assert state_after_64["llm"]["success"] is True
                assert state_after_64["llm"]["response"] is not None

        # Step 67: LLMSuccess reads LLM state and sets decision
        with patch("app.core.langgraph.nodes.step_067__llm_success.step_67__llmsuccess") as mock_67:
            with patch("app.core.langgraph.nodes.step_067__llm_success.rag_step_timer"):
                mock_67.return_value = {}

                state_after_67 = await node_step_67(state_after_64)

                # Verify decision is set based on LLM success
                assert state_after_67["llm_success_decision"] is True

        # Step 68: CacheResponse should work with successful LLM
        with patch("app.core.langgraph.nodes.step_068__cache_response.step_68__cache_response") as mock_68:
            with patch("app.core.langgraph.nodes.step_068__cache_response.rag_step_timer"):
                mock_68.return_value = {"cached": True}

                state_after_68 = await node_step_68(state_after_67)

                # Verify response is cached
                assert state_after_68["cached"] is True

        # Step 74: TrackUsage should work with LLM metrics
        with patch("app.core.langgraph.nodes.step_074__track_usage.step_74__track_usage") as mock_74:
            with patch("app.core.langgraph.nodes.step_074__track_usage.rag_step_timer"):
                mock_74.return_value = {"usage_tracked": True}

                state_after_74 = await node_step_74(state_after_68)

                # Verify usage is tracked
                assert state_after_74["usage_tracked"] is True
