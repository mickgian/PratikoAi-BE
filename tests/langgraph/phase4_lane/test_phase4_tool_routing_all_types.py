"""Test tool routing for all tool types in Phase 4 lane."""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.langgraph.nodes.step_075__tool_check import node_step_75
from app.core.langgraph.nodes.step_079__tool_type import node_step_79
from app.core.langgraph.nodes.step_080__kb_tool import node_step_80
from app.core.langgraph.nodes.step_081__ccnl_tool import node_step_81
from app.core.langgraph.nodes.step_082__doc_ingest_tool import node_step_82
from app.core.langgraph.nodes.step_083__faq_tool import node_step_83
from app.core.langgraph.nodes.step_099__tool_results import node_step_99
from app.core.langgraph.types import RAGState


class TestPhase4ToolRoutingAllTypes:
    """Test suite for Phase 4 tool routing across all tool types."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_state = RAGState(
            messages=[{"role": "user", "content": "test message"}], session_id="test-session-123"
        )

    @patch("app.core.langgraph.nodes.step_075__tool_check.step_75__tool_check")
    @patch("app.core.langgraph.nodes.step_075__tool_check.rag_step_log")
    @patch("app.core.langgraph.nodes.step_075__tool_check.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_75_tools_requested(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 75: ToolCheck node when tools are requested."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "tools_requested": True,
            "tool_calls": [{"name": "kb_query", "args": {"query": "test"}}],
            "requires_tools": True,
        }

        # Execute
        result = await node_step_75(self.sample_state)

        # Assert tools state structure
        assert "tools" in result
        assert result["tools"]["requested"] is True
        assert "tool_calls" in result

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(75)

    @patch("app.core.langgraph.nodes.step_075__tool_check.step_75__tool_check")
    @patch("app.core.langgraph.nodes.step_075__tool_check.rag_step_log")
    @patch("app.core.langgraph.nodes.step_075__tool_check.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_75_no_tools_needed(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 75: ToolCheck node when no tools are needed."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {"tools_requested": False, "tool_calls": [], "requires_tools": False}

        # Execute
        result = await node_step_75(self.sample_state)

        # Assert no tools state
        assert "tools" in result
        assert result["tools"]["requested"] is False

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(75)

    @patch("app.core.langgraph.nodes.step_079__tool_type.step_79__tool_type")
    @patch("app.core.langgraph.nodes.step_079__tool_type.rag_step_log")
    @patch("app.core.langgraph.nodes.step_079__tool_type.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_79_kb_tool_type(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 79: ToolType node for KB tool routing."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "tool_type": "kb",
            "routing_decision": "kb_query",
            "tool_args": {"query": "test knowledge base query"},
        }

        # Execute
        result = await node_step_79(self.sample_state)

        # Assert tool type routing
        assert "tools" in result
        assert result["tools"]["type"] == "kb"

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(79)

    @patch("app.core.langgraph.nodes.step_079__tool_type.step_79__tool_type")
    @patch("app.core.langgraph.nodes.step_079__tool_type.rag_step_log")
    @patch("app.core.langgraph.nodes.step_079__tool_type.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_79_ccnl_tool_type(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 79: ToolType node for CCNL tool routing."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "tool_type": "ccnl",
            "routing_decision": "ccnl_query",
            "tool_args": {"query": "CCNL labor contract question"},
        }

        # Execute
        result = await node_step_79(self.sample_state)

        # Assert CCNL tool type routing
        assert "tools" in result
        assert result["tools"]["type"] == "ccnl"

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(79)

    @patch("app.core.langgraph.nodes.step_080__kb_tool.step_80__kbquery_tool")
    @patch("app.core.langgraph.nodes.step_080__kb_tool.rag_step_log")
    @patch("app.core.langgraph.nodes.step_080__kb_tool.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_80_kb_tool_execution(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 80: KBTool node execution."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "kb_results": [
                {"title": "Document 1", "content": "KB content 1"},
                {"title": "Document 2", "content": "KB content 2"},
            ],
            "query_executed": True,
            "results_count": 2,
        }

        # Set up state for KB tool
        state_for_kb = self.sample_state.copy()
        state_for_kb["tools"] = {"type": "kb", "requested": True}

        # Execute
        result = await node_step_80(state_for_kb)

        # Assert KB tool results
        assert "kb_results" in result
        assert result["query_executed"] is True
        assert len(result["kb_results"]) == 2

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(80)

    @patch("app.core.langgraph.nodes.step_081__ccnl_tool.step_81__ccnlquery")
    @patch("app.core.langgraph.nodes.step_081__ccnl_tool.rag_step_log")
    @patch("app.core.langgraph.nodes.step_081__ccnl_tool.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_81_ccnl_tool_execution(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 81: CCNLTool node execution."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "ccnl_results": [{"contract": "CCNL Commerce", "article": "15", "content": "CCNL article content"}],
            "query_executed": True,
            "calculation_performed": True,
        }

        # Set up state for CCNL tool
        state_for_ccnl = self.sample_state.copy()
        state_for_ccnl["tools"] = {"type": "ccnl", "requested": True}

        # Execute
        result = await node_step_81(state_for_ccnl)

        # Assert CCNL tool results
        assert "ccnl_results" in result
        assert result["query_executed"] is True
        assert result["calculation_performed"] is True

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(81)

    @patch("app.core.langgraph.nodes.step_082__doc_ingest_tool.step_82__doc_ingest")
    @patch("app.core.langgraph.nodes.step_082__doc_ingest_tool.rag_step_log")
    @patch("app.core.langgraph.nodes.step_082__doc_ingest_tool.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_82_doc_ingest_tool_execution(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 82: DocIngestTool node execution."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "document_processed": True,
            "extracted_data": {"fields": ["name", "date"], "values": ["Test", "2024-01-01"]},
            "doc_type": "invoice",
            "processing_success": True,
        }

        # Set up state for document ingest tool
        state_for_doc = self.sample_state.copy()
        state_for_doc["tools"] = {"type": "doc", "requested": True}

        # Execute
        result = await node_step_82(state_for_doc)

        # Assert document ingest results
        assert result["document_processed"] is True
        assert "extracted_data" in result
        assert result["processing_success"] is True

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(82)

    @patch("app.core.langgraph.nodes.step_083__faq_tool.step_83__faqquery")
    @patch("app.core.langgraph.nodes.step_083__faq_tool.rag_step_log")
    @patch("app.core.langgraph.nodes.step_083__faq_tool.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_83_faq_tool_execution(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 83: FAQTool node execution."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "faq_results": [{"question": "How to calculate VAT?", "answer": "VAT is calculated at 22%"}],
            "query_executed": True,
            "matched_faqs": 1,
        }

        # Set up state for FAQ tool
        state_for_faq = self.sample_state.copy()
        state_for_faq["tools"] = {"type": "faq", "requested": True}

        # Execute
        result = await node_step_83(state_for_faq)

        # Assert FAQ tool results
        assert "faq_results" in result
        assert result["query_executed"] is True
        assert result["matched_faqs"] == 1

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(83)

    @patch("app.core.langgraph.nodes.step_099__tool_results.step_99__tool_results")
    @patch("app.core.langgraph.nodes.step_099__tool_results.rag_step_log")
    @patch("app.core.langgraph.nodes.step_099__tool_results.rag_step_timer")
    @pytest.mark.asyncio
    async def test_node_step_99_tool_results_consolidation(self, mock_timer, mock_log, mock_orchestrator):
        """Test Step 99: ToolResults node consolidates tool outputs."""
        # Setup
        timer_context = Mock()
        timer_context.__enter__ = Mock(return_value=timer_context)
        timer_context.__exit__ = Mock(return_value=None)
        mock_timer.return_value = timer_context

        mock_orchestrator.return_value = {
            "consolidated_results": {"tool_type": "kb", "results": ["result1", "result2"], "success": True},
            "results_formatted": True,
            "ready_for_response": True,
        }

        # Set up state with tool results
        state_with_results = self.sample_state.copy()
        state_with_results["tools"] = {"type": "kb", "requested": True, "results": ["result1", "result2"]}

        # Execute
        result = await node_step_99(state_with_results)

        # Assert tool results consolidation
        assert "consolidated_results" in result
        assert result["results_formatted"] is True
        assert result["ready_for_response"] is True

        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
        mock_timer.assert_called_once_with(99)

    @pytest.mark.asyncio
    async def test_tool_routing_flow_kb_path(self):
        """Test complete tool routing flow: ToolCheck → ToolType → KBTool → ToolResults."""

        # Step 75: ToolCheck detects tools needed
        with patch("app.core.langgraph.nodes.step_075__tool_check.step_75__tool_check") as mock_75:
            with patch("app.core.langgraph.nodes.step_075__tool_check.rag_step_timer"):
                mock_75.return_value = {"tools_requested": True}

                state_after_75 = await node_step_75(self.sample_state)
                state_after_75["tools"] = {"requested": True}

        # Step 79: ToolType routes to KB
        with patch("app.core.langgraph.nodes.step_079__tool_type.step_79__tool_type") as mock_79:
            with patch("app.core.langgraph.nodes.step_079__tool_type.rag_step_timer"):
                mock_79.return_value = {"tool_type": "kb"}

                state_after_79 = await node_step_79(state_after_75)
                state_after_79["tools"] = {"type": "kb", "requested": True}

        # Step 80: KBTool executes
        with patch("app.core.langgraph.nodes.step_080__kb_tool.step_80__kbquery_tool") as mock_80:
            with patch("app.core.langgraph.nodes.step_080__kb_tool.rag_step_timer"):
                mock_80.return_value = {"kb_results": ["result1"]}

                state_after_80 = await node_step_80(state_after_79)

                # Verify KB tool executed
                assert "kb_results" in state_after_80

        # Step 99: ToolResults consolidates
        with patch("app.core.langgraph.nodes.step_099__tool_results.step_99__tool_results") as mock_99:
            with patch("app.core.langgraph.nodes.step_099__tool_results.rag_step_timer"):
                mock_99.return_value = {"consolidated_results": {"type": "kb"}}

                state_after_99 = await node_step_99(state_after_80)

                # Verify results are consolidated
                assert "consolidated_results" in state_after_99

    @pytest.mark.asyncio
    async def test_tool_routing_flow_ccnl_path(self):
        """Test tool routing flow for CCNL: ToolCheck → ToolType → CCNLTool → ToolResults."""

        # Similar to KB path but routes to CCNL tool
        with patch("app.core.langgraph.nodes.step_075__tool_check.step_75__tool_check") as mock_75:
            with patch("app.core.langgraph.nodes.step_075__tool_check.rag_step_timer"):
                mock_75.return_value = {"tools_requested": True}

                state_after_75 = await node_step_75(self.sample_state)
                state_after_75["tools"] = {"requested": True}

        # Step 79: ToolType routes to CCNL
        with patch("app.core.langgraph.nodes.step_079__tool_type.step_79__tool_type") as mock_79:
            with patch("app.core.langgraph.nodes.step_079__tool_type.rag_step_timer"):
                mock_79.return_value = {"tool_type": "ccnl"}

                state_after_79 = await node_step_79(state_after_75)
                state_after_79["tools"] = {"type": "ccnl", "requested": True}

        # Step 81: CCNLTool executes
        with patch("app.core.langgraph.nodes.step_081__ccnl_tool.step_81__ccnlquery") as mock_81:
            with patch("app.core.langgraph.nodes.step_081__ccnl_tool.rag_step_timer"):
                mock_81.return_value = {"ccnl_results": ["ccnl_result1"]}

                state_after_81 = await node_step_81(state_after_79)

                # Verify CCNL tool executed
                assert "ccnl_results" in state_after_81
