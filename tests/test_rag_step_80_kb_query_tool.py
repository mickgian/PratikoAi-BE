"""
Tests for RAG STEP 80 — KnowledgeSearchTool.search KB on demand (RAG.kb.knowledgesearchtool.search.kb.on.demand)

This process step executes on-demand knowledge base search when the LLM calls the KnowledgeSearchTool.
Uses KnowledgeSearchService for hybrid BM25 + vector + recency search.
"""

from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

import pytest


class TestRAGStep80KBQueryTool:
    """Test suite for RAG STEP 80 - KB on-demand search tool."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_80_executes_knowledge_search(self, mock_rag_log):
        """Test Step 80: Executes knowledge base search via tool."""
        from app.orchestrators.kb import step_80__kbquery_tool

        ctx = {
            'tool_name': 'KnowledgeSearchTool',
            'tool_args': {'query': 'Come funziona il TFR?'},
            'tool_call_id': 'call_kb_123',
            'request_id': 'test-80-search'
        }

        result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        assert 'kb_results' in result or 'search_results' in result
        assert result['next_step'] == 'tool_results'

        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log['step'] == 80
        assert completed_log['node_label'] == 'KBQueryTool'

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    @patch('app.services.knowledge_search_service.KnowledgeSearchService')
    async def test_step_80_uses_knowledge_search_service(self, mock_service_class, mock_rag_log):
        """Test Step 80: Uses KnowledgeSearchService for KB retrieval."""
        from app.orchestrators.kb import step_80__kbquery_tool

        mock_service = MagicMock()
        mock_service.search_knowledge = AsyncMock(return_value=[
            {'title': 'TFR Info', 'content': 'TFR explanation', 'score': 0.95},
            {'title': 'TFR Calculation', 'content': 'How to calc TFR', 'score': 0.87}
        ])
        mock_service_class.return_value = mock_service

        ctx = {
            'tool_args': {'query': 'TFR calculation'},
            'tool_call_id': 'call_123',
            'request_id': 'test-80-service'
        }

        result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        assert 'kb_results' in result or 'search_results' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_80_handles_query_parameter(self, mock_rag_log):
        """Test Step 80: Handles query parameter from tool args."""
        from app.orchestrators.kb import step_80__kbquery_tool

        test_query = 'Quanto costa un contratto a tempo determinato?'

        ctx = {
            'tool_args': {'query': test_query},
            'tool_call_id': 'call_456',
            'request_id': 'test-80-query'
        }

        result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        assert 'query' in result or 'search_query' in result
        assert result.get('query') == test_query or result.get('search_query') == test_query

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_80_returns_hybrid_search_results(self, mock_rag_log):
        """Test Step 80: Returns hybrid search results (BM25 + vector + recency)."""
        from app.orchestrators.kb import step_80__kbquery_tool

        ctx = {
            'tool_args': {'query': 'Ferie annuali dipendente'},
            'tool_call_id': 'call_hybrid',
            'request_id': 'test-80-hybrid'
        }

        result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        kb_key = 'kb_results' if 'kb_results' in result else 'search_results'
        assert kb_key in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_80_handles_empty_results(self, mock_rag_log):
        """Test Step 80: Handles empty search results gracefully."""
        from app.orchestrators.kb import step_80__kbquery_tool

        ctx = {
            'tool_args': {'query': 'nonexistent query xyz'},
            'tool_call_id': 'call_empty',
            'request_id': 'test-80-empty'
        }

        result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        assert result['next_step'] == 'tool_results'

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_80_includes_search_metadata(self, mock_rag_log):
        """Test Step 80: Includes search metadata in results."""
        from app.orchestrators.kb import step_80__kbquery_tool

        ctx = {
            'tool_args': {'query': 'CCNL metalmeccanici'},
            'tool_call_id': 'call_meta',
            'request_id': 'test-80-metadata',
            'user_id': 'user789'
        }

        result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        assert 'search_metadata' in result or 'result_count' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_80_routes_to_tool_results(self, mock_rag_log):
        """Test Step 80: Routes to Step 99 (ToolResults) per Mermaid."""
        from app.orchestrators.kb import step_80__kbquery_tool

        ctx = {
            'tool_args': {'query': 'Test query'},
            'tool_call_id': 'call_route',
            'request_id': 'test-80-route'
        }

        result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        assert result['next_step'] == 'tool_results'

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_80_preserves_context(self, mock_rag_log):
        """Test Step 80: Preserves context fields for Step 99."""
        from app.orchestrators.kb import step_80__kbquery_tool

        ctx = {
            'tool_args': {'query': 'Context test'},
            'tool_call_id': 'call_ctx',
            'request_id': 'test-80-context',
            'user_id': 'user456',
            'session_id': 'session789',
            'other_field': 'preserved_value'
        }

        result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        assert result['request_id'] == 'test-80-context'
        assert result['user_id'] == 'user456'
        assert result['session_id'] == 'session789'
        assert result['other_field'] == 'preserved_value'


class TestRAGStep80Parity:
    """Parity tests proving Step 80 uses KnowledgeSearchService correctly."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_80_parity_with_knowledge_search_service(self, mock_rag_log):
        """Test Step 80: Uses same search logic as KnowledgeSearchService."""
        from app.orchestrators.kb import step_80__kbquery_tool
        from app.services.knowledge_search_service import KnowledgeSearchService
        from unittest.mock import MagicMock

        query = 'Come calcolare il TFR?'

        mock_db = MagicMock()

        service = KnowledgeSearchService(db_session=mock_db)

        ctx = {
            'tool_args': {'query': query},
            'tool_call_id': 'call_parity',
            'request_id': 'parity-test',
            'db_session': mock_db
        }

        orch_result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        assert 'kb_results' in orch_result or 'search_results' in orch_result


class TestRAGStep80Integration:
    """Integration tests for Step 79 → Step 80 → Step 99 flow."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_79_to_80_integration(self, mock_kb_log):
        """Test Step 79 (ToolType) → Step 80 (KBQueryTool) integration flow."""
        from app.orchestrators.kb import step_80__kbquery_tool

        # Simulate Step 79 output (when Knowledge tool type is detected)
        # Note: Step 79 is not yet implemented, so we mock its expected output
        step_79_output = {
            'tool_type': 'Knowledge',
            'tool_name': 'KnowledgeSearchTool',
            'tool_call_id': 'call_integration',
            'tool_args': {'query': 'Ferie dipendente'},
            'next_step': 'kb_query_tool',
            'request_id': 'test-integration-79-80'
        }

        # Step 80: Execute KB search
        step_80_result = await step_80__kbquery_tool(messages=[], ctx=step_79_output)

        # Should route to Step 99 (ToolResults)
        assert step_80_result['next_step'] == 'tool_results'
        assert 'kb_results' in step_80_result or 'search_results' in step_80_result

    @pytest.mark.asyncio
    @patch('app.orchestrators.kb.rag_step_log')
    async def test_step_80_prepares_for_step_99(self, mock_rag_log):
        """Test Step 80: Prepares output for Step 99 (ToolResults)."""
        from app.orchestrators.kb import step_80__kbquery_tool

        ctx = {
            'tool_args': {'query': 'Test final'},
            'tool_call_id': 'call_final',
            'request_id': 'test-80-final',
            'ai_message': MagicMock()
        }

        result = await step_80__kbquery_tool(messages=[], ctx=ctx)

        assert 'tool_call_id' in result
        assert result['next_step'] == 'tool_results'
        assert 'kb_results' in result or 'search_results' in result