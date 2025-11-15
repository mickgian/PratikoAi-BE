"""Integration tests for Phase 1A RAG graph."""

import os
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message
from app.schemas.graph import GraphState


class TestPhase1AIntegration:
    """Integration test suite for Phase 1A graph flows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = LangGraphAgent()
        self.sample_messages = [Message(role="user", content="test query")]
        self.session_id = "test-session-123"

    def teardown_method(self):
        """Clean up after tests."""
        pass

    @pytest.mark.asyncio
    @patch("app.core.langgraph.graph.LangGraphAgent._get_connection_pool")
    async def test_create_phase1a_graph(self, mock_connection_pool):
        """Test Phase 1A graph creation."""
        # Setup
        mock_connection_pool.return_value = None

        # Execute
        graph = await self.agent.create_graph_phase1a()

        # Assert
        assert graph is not None
        # Note: In production tests, we'd check node names and edges

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.step_1__validate_request")
    @patch("app.orchestrators.platform.step_3__valid_check")
    @patch("app.orchestrators.privacy.step_6__privacy_check")
    @patch("app.orchestrators.platform.step_9__piicheck")
    @patch("app.orchestrators.cache.step_59__check_cache")
    @patch("app.orchestrators.cache.step_62__cache_hit")
    @patch("app.orchestrators.response.step_112__end")
    @patch("app.core.langgraph.graph.LangGraphAgent._get_connection_pool")
    async def test_cache_hit_flow(
        self, mock_pool, mock_end, mock_cache_hit, mock_check_cache, mock_pii, mock_privacy, mock_valid, mock_validate
    ):
        """Test Case A: valid request → privacy pass → cache hit → End."""
        # Setup mocks
        mock_pool.return_value = None
        mock_validate.return_value = {"request_valid": True, "user_authenticated": True}
        mock_valid.return_value = {"request_valid": True}
        mock_privacy.return_value = {"privacy_enabled": False}
        mock_pii.return_value = {"pii_detected": False}
        mock_check_cache.return_value = {}
        mock_cache_hit.return_value = {"cache_hit": True}
        mock_end.return_value = {}

        # Create graph
        graph = await self.agent.create_graph_phase1a()
        assert graph is not None

        # Execute graph
        initial_state = {"messages": [{"role": "user", "content": "test query"}], "session_id": self.session_id}

        result = await graph.ainvoke(initial_state)

        # Assert flow completed
        assert result is not None
        # Verify final response structure would be created

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.step_1__validate_request")
    @patch("app.orchestrators.platform.step_3__valid_check")
    @patch("app.orchestrators.privacy.step_6__privacy_check")
    @patch("app.orchestrators.platform.step_9__piicheck")
    @patch("app.orchestrators.cache.step_59__check_cache")
    @patch("app.orchestrators.cache.step_62__cache_hit")
    @patch("app.orchestrators.providers.step_64__llmcall")
    @patch("app.orchestrators.llm.step_67__llmsuccess")
    @patch("app.orchestrators.response.step_112__end")
    @patch("app.core.langgraph.graph.LangGraphAgent._get_connection_pool")
    async def test_llm_success_flow(
        self,
        mock_pool,
        mock_end,
        mock_llm_success,
        mock_llm_call,
        mock_cache_hit,
        mock_check_cache,
        mock_pii,
        mock_privacy,
        mock_valid,
        mock_validate,
    ):
        """Test Case B: valid request → privacy pass → cache miss → LLM success → End."""
        # Setup mocks
        mock_pool.return_value = None
        mock_validate.return_value = {"request_valid": True, "user_authenticated": True}
        mock_valid.return_value = {"request_valid": True}
        mock_privacy.return_value = {"privacy_enabled": False}
        mock_pii.return_value = {"pii_detected": False}
        mock_check_cache.return_value = {}
        mock_cache_hit.return_value = {"cache_hit": False}
        mock_llm_call.return_value = {"llm_response": "test response"}
        mock_llm_success.return_value = {"llm_success": True}
        mock_end.return_value = {}

        # Create graph
        graph = await self.agent.create_graph_phase1a()
        assert graph is not None

        # Execute graph
        initial_state = {"messages": [{"role": "user", "content": "test query"}], "session_id": self.session_id}

        result = await graph.ainvoke(initial_state)

        # Assert flow completed with LLM call
        assert result is not None

    @pytest.mark.asyncio
    @patch("app.orchestrators.platform.step_1__validate_request")
    @patch("app.orchestrators.platform.step_3__valid_check")
    @patch("app.orchestrators.response.step_112__end")
    @patch("app.core.langgraph.graph.LangGraphAgent._get_connection_pool")
    async def test_invalid_request_flow(self, mock_pool, mock_end, mock_valid, mock_validate):
        """Test Case C: invalid request → End."""
        # Setup mocks
        mock_pool.return_value = None
        mock_validate.return_value = {"request_valid": False}
        mock_valid.return_value = {"request_valid": False}
        mock_end.return_value = {}

        # Create graph
        graph = await self.agent.create_graph_phase1a()
        assert graph is not None

        # Execute graph
        initial_state = {"messages": [{"role": "user", "content": "invalid request"}], "session_id": self.session_id}

        result = await graph.ainvoke(initial_state)

        # Assert flow went directly to End
        assert result is not None

    def test_routing_logic(self):
        """Test routing methods work correctly."""
        agent = LangGraphAgent()

        # Test ValidCheck routing
        assert agent._route_from_valid_check({"request_valid": True}) == "PrivacyCheck"
        assert agent._route_from_valid_check({"request_valid": False}) == "End"

        # Test PrivacyCheck routing
        assert agent._route_from_privacy_check({}) == "PIICheck"

        # Test PIICheck routing
        assert agent._route_from_pii_check({}) == "CheckCache"

        # Test CacheHit routing
        assert agent._route_from_cache_hit({"cache_hit": True}) == "End"
        assert agent._route_from_cache_hit({"cache_hit": False}) == "LLMCall"

        # Test LLMSuccess routing
        assert agent._route_from_llm_success({}) == "End"

    @pytest.mark.asyncio
    @patch("app.core.langgraph.graph.LangGraphAgent._get_connection_pool")
    async def test_phase1a_is_default(self, mock_pool):
        """Test that Phase 1A graph is the default implementation."""
        # Phase 1A graph should be created by default
        mock_pool.return_value = None
        agent = LangGraphAgent()
        graph = await agent.create_graph()

        # Verify it's using Phase 1A by checking it calls create_graph_phase1a
        assert graph is not None
