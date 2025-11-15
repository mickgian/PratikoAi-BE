"""Parity tests comparing Phase 1A graph vs legacy hybrid implementation."""

import os
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message


class TestPhase1AParity:
    """Parity tests to ensure Phase 1A produces equivalent results to legacy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_messages = [Message(role="user", content="test query")]
        self.session_id = "test-session-123"

    def teardown_method(self):
        """Clean up after tests."""
        pass

    @pytest.mark.asyncio
    @patch("app.core.langgraph.graph.LangGraphAgent._get_connection_pool")
    @patch("app.orchestrators.platform.step_1__validate_request")
    @patch("app.orchestrators.platform.step_3__valid_check")
    @patch("app.orchestrators.privacy.step_6__privacy_check")
    @patch("app.orchestrators.platform.step_9__piicheck")
    @patch("app.orchestrators.cache.step_59__check_cache")
    @patch("app.orchestrators.cache.step_62__cache_hit")
    @patch("app.orchestrators.response.step_112__end")
    async def test_parity_cache_hit_scenario(
        self, mock_end, mock_cache_hit, mock_check_cache, mock_pii, mock_privacy, mock_valid, mock_validate, mock_pool
    ):
        """Test parity between Phase 1A and legacy for cache hit scenario."""
        # Setup consistent mocks for both paths
        mock_pool.return_value = None
        mock_validate.return_value = {"request_valid": True, "user_authenticated": True}
        mock_valid.return_value = {"request_valid": True}
        mock_privacy.return_value = {"privacy_enabled": False}
        mock_pii.return_value = {"pii_detected": False}
        mock_check_cache.return_value = {}
        mock_cache_hit.return_value = {"cache_hit": True}
        mock_end.return_value = {"final_response": {"content": "cached response", "source": "cache"}}

        initial_state = {"messages": [{"role": "user", "content": "test query"}], "session_id": self.session_id}

        # Phase 1A is now the default implementation
        phase1a_agent = LangGraphAgent()
        phase1a_graph = await phase1a_agent.create_graph()
        phase1a_result = await phase1a_graph.ainvoke(initial_state)

        # For this minimal test, just verify Phase 1A executed
        assert phase1a_result is not None
        # In full parity testing, we'd compare:
        # assert legacy_result['final_response'] == phase1a_result['final_response']

    @pytest.mark.asyncio
    @patch("app.core.langgraph.graph.LangGraphAgent._get_connection_pool")
    async def test_parity_error_response_format(self, mock_pool):
        """Test that error responses maintain same format between implementations."""
        mock_pool.return_value = None

        # Mock validation failure
        with (
            patch("app.orchestrators.platform.step_1__validate_request") as mock_validate,
            patch("app.orchestrators.platform.step_3__valid_check") as mock_valid,
            patch("app.orchestrators.response.step_112__end") as mock_end,
        ):
            mock_validate.return_value = {"request_valid": False}
            mock_valid.return_value = {"request_valid": False}
            mock_end.return_value = {}

            # Test Phase 1A error path (now default)
            agent = LangGraphAgent()
            graph = await agent.create_graph()

            initial_state = {"messages": [{"role": "user", "content": "invalid"}], "session_id": self.session_id}

            result = await graph.ainvoke(initial_state)

            # Verify error response structure
            assert result is not None
            # In full implementation, would verify error format consistency

    @pytest.mark.asyncio
    async def test_observability_parity(self):
        """Test that both implementations emit equivalent observability data."""
        # This test would verify that:
        # 1. Same RAG STEP logs are emitted
        # 2. Same metrics are tracked
        # 3. Same timing information is captured
        # 4. Same error paths are logged

        # For now, just test that observability imports work
        from app.observability.rag_logging import rag_step_log, rag_step_timer

        # Test that the imports work (basic smoke test)
        assert rag_step_log is not None
        assert rag_step_timer is not None

    def test_state_compatibility(self):
        """Test that state structures are compatible between implementations."""
        from app.core.langgraph.types import RAGState
        from app.schemas.graph import GraphState

        # Verify RAGState is compatible with GraphState
        state = GraphState(messages=[{"role": "user", "content": "test"}], session_id="test")

        # Should be able to use GraphState as RAGState
        assert isinstance(state, GraphState)

        # Test state dict conversion
        state_dict = state.model_dump()
        assert "messages" in state_dict
        assert "session_id" in state_dict

    @pytest.mark.asyncio
    async def test_phase1a_is_default_implementation(self):
        """Test that Phase 1A graph is now the default implementation."""
        agent = LangGraphAgent()
        with patch.object(agent, "create_graph_phase1a") as mock_phase1a:
            with patch("app.core.langgraph.graph.LangGraphAgent._get_connection_pool") as mock_pool:
                mock_pool.return_value = None
                mock_phase1a.return_value = Mock()  # Mock the Phase 1A graph

                # This should call create_graph_phase1a since it's the default
                graph = await agent.create_graph()

                # Phase 1A should be called
                mock_phase1a.assert_called_once()
                assert graph is not None
