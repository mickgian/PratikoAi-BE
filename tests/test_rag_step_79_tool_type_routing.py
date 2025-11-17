"""
Test suite for RAG STEP 79 - Tool type routing decision.

This module tests the tool type detection and routing logic that determines
which type of tool is being called and routes execution accordingly.

Based on Mermaid diagram: ToolType (Tool type?)
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message


class TestToolTypeRouting:
    """Test tool type routing decision functionality with structured logging."""

    @pytest.fixture
    def lang_graph_agent(self):
        """Create LangGraphAgent instance for testing."""
        return LangGraphAgent()

    def test_detect_knowledge_tool_type(self, lang_graph_agent):
        """Test detection of Knowledge tool type."""
        tool_name = "KnowledgeSearchTool"

        result = lang_graph_agent._detect_tool_type(tool_name)

        assert result == "Knowledge"

    def test_detect_ccnl_tool_type(self, lang_graph_agent):
        """Test detection of CCNL tool type."""
        tool_name = "CCNLTool"

        result = lang_graph_agent._detect_tool_type(tool_name)

        assert result == "CCNL"

    def test_detect_document_tool_type(self, lang_graph_agent):
        """Test detection of Document tool type."""
        tool_name = "DocumentIngestTool"

        result = lang_graph_agent._detect_tool_type(tool_name)

        assert result == "Document"

    def test_detect_faq_tool_type(self, lang_graph_agent):
        """Test detection of FAQ tool type."""
        tool_name = "FAQTool"

        result = lang_graph_agent._detect_tool_type(tool_name)

        assert result == "FAQ"

    def test_detect_unknown_tool_type(self, lang_graph_agent):
        """Test detection of unknown tool type."""
        tool_name = "UnknownTool"

        result = lang_graph_agent._detect_tool_type(tool_name)

        assert result == "Unknown"

    @pytest.mark.asyncio
    async def test_tool_type_routing_with_structured_logging(self, lang_graph_agent):
        """Test tool type routing with proper structured logging."""
        with patch("app.core.langgraph.graph.rag_step_log") as mock_log:
            # Test Knowledge tool routing
            tool_name = "KnowledgeSearchTool"
            tool_type = lang_graph_agent._detect_tool_type(tool_name)

            # Log the routing decision
            lang_graph_agent._log_tool_type_decision(tool_name, tool_type)

            # Verify structured logging occurred
            mock_log.assert_called()

            # Check the log call arguments
            call_args = mock_log.call_args
            assert call_args[0][0] == 79  # step
            assert call_args[0][1] == "RAG.routing.tool.type"  # step_id
            assert call_args[0][2] == "ToolType"  # node_label

            # Check kwargs
            call_kwargs = call_args[1]
            assert call_kwargs["tool_name"] == "KnowledgeSearchTool"
            assert call_kwargs["tool_type"] == "Knowledge"
            assert call_kwargs["decision"] == "route_to_knowledge"

    @pytest.mark.asyncio
    async def test_tool_type_routing_with_timer(self, lang_graph_agent):
        """Test tool type routing with performance timing."""
        with patch("app.core.langgraph.graph.rag_step_timer") as mock_timer:
            # Setup timer context manager mock
            timer_context = MagicMock()
            mock_timer.return_value.__enter__ = MagicMock(return_value=timer_context)
            mock_timer.return_value.__exit__ = MagicMock(return_value=None)

            # Test CCNL tool routing
            tool_name = "CCNLTool"

            # Execute with timer
            with lang_graph_agent._tool_type_timer(tool_name):
                lang_graph_agent._detect_tool_type(tool_name)

            # Verify timer was called
            mock_timer.assert_called_once()
            timer_call = mock_timer.call_args

            # Check positional args
            assert timer_call[0][0] == 79  # step
            assert timer_call[0][1] == "RAG.routing.tool.type"  # step_id
            assert timer_call[0][2] == "ToolType"  # node_label

            # Check kwargs
            assert timer_call[1]["tool_name"] == "CCNLTool"

    @pytest.mark.asyncio
    async def test_tool_routing_in_tool_call_flow(self, lang_graph_agent):
        """Test tool type routing integrated in _tool_call flow."""
        with patch("app.core.langgraph.graph.rag_step_log") as mock_log:
            # Mock tool and tool result
            mock_tool = AsyncMock()
            mock_tool.ainvoke.return_value = "Tool execution result"

            # Setup tools_by_name
            lang_graph_agent.tools_by_name = {"DocumentIngestTool": mock_tool}

            # Create state with tool call
            from langchain_core.messages import AIMessage, ToolMessage

            from app.schemas.graph import GraphState

            state = GraphState(
                session_id="test_session_123",
                messages=[
                    AIMessage(
                        content="Processing document",
                        tool_calls=[
                            {"id": "call_123", "name": "DocumentIngestTool", "args": {"file": "document.pdf"}}
                        ],
                    )
                ],
            )

            # Execute tool call
            await lang_graph_agent._tool_call(state)

            # Verify tool was executed
            mock_tool.ainvoke.assert_called_once_with({"file": "document.pdf"})

            # Verify tool type was logged
            log_calls = [call for call in mock_log.call_args_list if len(call[0]) >= 3 and call[0][0] == 79]
            assert len(log_calls) > 0

            # Check the routing decision
            routing_call = log_calls[0]
            assert routing_call[1]["tool_type"] == "Document"
            assert routing_call[1]["decision"] == "route_to_document"

    def test_tool_type_mappings(self, lang_graph_agent):
        """Test all expected tool type mappings."""
        mappings = {
            "KnowledgeSearchTool": "Knowledge",
            "knowledge_search": "Knowledge",
            "CCNLTool": "CCNL",
            "ccnl_query": "CCNL",
            "DocumentIngestTool": "Document",
            "document_ingest": "Document",
            "FAQTool": "FAQ",
            "faq_query": "FAQ",
            "calculator": "Unknown",
            "web_search": "Unknown",
        }

        for tool_name, expected_type in mappings.items():
            result = lang_graph_agent._detect_tool_type(tool_name)
            assert result == expected_type, f"Tool {tool_name} should map to {expected_type}, got {result}"

    def test_routing_decision_generation(self, lang_graph_agent):
        """Test generation of routing decisions based on tool type."""
        decisions = {
            "Knowledge": "route_to_knowledge",
            "CCNL": "route_to_ccnl",
            "Document": "route_to_document",
            "FAQ": "route_to_faq",
            "Unknown": "route_to_unknown",
        }

        for tool_type, expected_decision in decisions.items():
            result = lang_graph_agent._get_routing_decision(tool_type)
            assert result == expected_decision, f"Type {tool_type} should route to {expected_decision}"


class TestToolTypeErrorHandling:
    """Test error handling in tool type routing."""

    @pytest.fixture
    def lang_graph_agent(self):
        """Create LangGraphAgent instance for testing."""
        return LangGraphAgent()

    def test_none_tool_name_handling(self, lang_graph_agent):
        """Test handling of None tool name."""
        result = lang_graph_agent._detect_tool_type(None)
        assert result == "Unknown"

    def test_empty_tool_name_handling(self, lang_graph_agent):
        """Test handling of empty tool name."""
        result = lang_graph_agent._detect_tool_type("")
        assert result == "Unknown"

    @pytest.mark.asyncio
    async def test_tool_type_detection_with_error_logging(self, lang_graph_agent):
        """Test tool type detection error logging."""
        with patch("app.core.langgraph.graph.rag_step_log") as mock_log:
            # Test with invalid tool name
            tool_name = None
            tool_type = lang_graph_agent._detect_tool_type(tool_name)

            # Log the error case
            lang_graph_agent._log_tool_type_decision(tool_name, tool_type, error="Invalid tool name")

            # Verify error was logged
            mock_log.assert_called()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs.get("error") == "Invalid tool name"
            assert call_kwargs["tool_type"] == "Unknown"


# Integration test scenarios
@pytest.mark.asyncio
async def test_full_tool_routing_flow():
    """Test complete tool routing flow with all tool types."""
    agent = LangGraphAgent()

    test_cases = [
        ("KnowledgeSearchTool", "Knowledge", "route_to_knowledge"),
        ("CCNLTool", "CCNL", "route_to_ccnl"),
        ("DocumentIngestTool", "Document", "route_to_document"),
        ("FAQTool", "FAQ", "route_to_faq"),
    ]

    for tool_name, expected_type, expected_decision in test_cases:
        with patch("app.core.langgraph.graph.rag_step_log") as mock_log:
            # Detect tool type
            tool_type = agent._detect_tool_type(tool_name)
            assert tool_type == expected_type

            # Get routing decision
            decision = agent._get_routing_decision(tool_type)
            assert decision == expected_decision

            # Log the decision
            agent._log_tool_type_decision(tool_name, tool_type)

            # Verify logging
            mock_log.assert_called()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["tool_name"] == tool_name
            assert call_kwargs["tool_type"] == expected_type
            assert call_kwargs["decision"] == expected_decision
