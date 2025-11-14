"""
Tests for RAG Step 102: ProcessMsg (LangGraphAgent.__process_messages Convert to dict).

This step converts LangChain BaseMessage objects to dictionary format for final response
processing, filtering to keep only assistant and user messages with content.
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage, SystemMessage


class TestRAGStep102ProcessMsg:
    """Unit tests for Step 102: ProcessMsg."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_converts_messages_to_dict_format(self, mock_rag_log):
        """Test Step 102: Converts LangChain messages to dictionary format."""
        from app.orchestrators.response import step_102__process_msg

        # Mock LangChain messages
        messages = [
            HumanMessage(content="User question about Italian tax law"),
            AIMessage(content="Assistant response with tax information"),
            HumanMessage(content="Follow-up question"),
            AIMessage(content="Follow-up response")
        ]

        ctx = {
            'messages': messages,
            'response_source': 'final_response',
            'conversation_metadata': {
                'turn_count': 2,
                'total_tokens': 150
            },
            'request_id': 'test-102-convert'
        }

        result = await step_102__process_msg(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result['next_step'] == 'log_completion'
        assert 'processed_messages' in result
        assert len(result['processed_messages']) == 4

        # Verify message format conversion
        for msg in result['processed_messages']:
            assert 'role' in msg
            assert 'content' in msg
            assert msg['role'] in ['user', 'assistant']
            assert isinstance(msg['content'], str)
            assert len(msg['content']) > 0

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_filters_out_system_and_tool_messages(self, mock_rag_log):
        """Test Step 102: Filters out system and tool messages, keeps only user/assistant."""
        from app.orchestrators.response import step_102__process_msg

        messages = [
            SystemMessage(content="You are a helpful AI assistant"),
            HumanMessage(content="User question"),
            AIMessage(content="AI response", tool_calls=[{"id": "call_1", "name": "search", "args": {}}]),
            ToolMessage(content="Tool result", tool_call_id="call_1"),
            AIMessage(content="Final AI response"),
            HumanMessage(content="Another user question")
        ]

        ctx = {
            'messages': messages,
            'response_source': 'tool_results',
            'request_id': 'test-102-filter'
        }

        result = await step_102__process_msg(messages=[], ctx=ctx)

        # Should only have user and assistant messages with content
        processed = result['processed_messages']
        assert len(processed) == 4  # 2 HumanMessage + 2 AIMessage with content

        roles = [msg['role'] for msg in processed]
        assert 'system' not in roles
        assert 'tool' not in roles
        assert all(role in ['user', 'assistant'] for role in roles)

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_handles_empty_content_messages(self, mock_rag_log):
        """Test Step 102: Filters out messages with empty content."""
        from app.orchestrators.response import step_102__process_msg

        messages = [
            HumanMessage(content="Valid user message"),
            AIMessage(content=""),  # Empty content
            HumanMessage(content="   "),  # Whitespace only
            AIMessage(content="Valid AI response")
        ]

        ctx = {
            'messages': messages,
            'request_id': 'test-102-empty'
        }

        result = await step_102__process_msg(messages=[], ctx=ctx)

        processed = result['processed_messages']
        # Should only have messages with non-empty content
        assert len(processed) == 2
        assert all(msg['content'] and msg['content'].strip() for msg in processed)

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_preserves_message_content_and_order(self, mock_rag_log):
        """Test Step 102: Preserves exact message content and conversation order."""
        from app.orchestrators.response import step_102__process_msg

        expected_messages = [
            ("user", "Che cos'è l'IVA in Italia?"),
            ("assistant", "L'IVA (Imposta sul Valore Aggiunto) è una tassa sui consumi applicata in Italia..."),
            ("user", "Quali sono le aliquote IVA?"),
            ("assistant", "Le aliquote IVA in Italia sono: 4%, 10%, 22% ordinaria...")
        ]

        messages = [
            HumanMessage(content=expected_messages[0][1]),
            AIMessage(content=expected_messages[1][1]),
            HumanMessage(content=expected_messages[2][1]),
            AIMessage(content=expected_messages[3][1])
        ]

        ctx = {
            'messages': messages,
            'request_id': 'test-102-preserve'
        }

        result = await step_102__process_msg(messages=[], ctx=ctx)

        processed = result['processed_messages']
        assert len(processed) == 4

        for i, (expected_role, expected_content) in enumerate(expected_messages):
            assert processed[i]['role'] == expected_role
            assert processed[i]['content'] == expected_content

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_handles_complex_message_types(self, mock_rag_log):
        """Test Step 102: Handles complex message types and tool calls."""
        from app.orchestrators.response import step_102__process_msg

        messages = [
            HumanMessage(content="Search for tax information"),
            AIMessage(
                content="I'll search for tax information for you.",
                tool_calls=[{"id": "call_1", "name": "knowledge_search", "args": {"query": "tax"}}]
            ),
            ToolMessage(content="Found tax documents...", tool_call_id="call_1"),
            AIMessage(content="Based on the search results, here's what I found about Italian taxes...")
        ]

        ctx = {
            'messages': messages,
            'request_id': 'test-102-complex'
        }

        result = await step_102__process_msg(messages=[], ctx=ctx)

        processed = result['processed_messages']
        # Should have user message + 2 assistant messages (tool call filtered out)
        assert len(processed) == 3

        user_msgs = [msg for msg in processed if msg['role'] == 'user']
        assistant_msgs = [msg for msg in processed if msg['role'] == 'assistant']
        assert len(user_msgs) == 1
        assert len(assistant_msgs) == 2

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_preserves_all_context_data(self, mock_rag_log):
        """Test Step 102: Preserves all context data for downstream processing."""
        from app.orchestrators.response import step_102__process_msg

        original_ctx = {
            'messages': [
                HumanMessage(content="Test message"),
                AIMessage(content="Test response")
            ],
            'user_data': {'id': 'user_123'},
            'session_data': {'id': 'session_456'},
            'response_metadata': {
                'provider': 'openai',
                'model': 'gpt-4',
                'tokens_used': 85
            },
            'processing_history': ['tool_execution', 'final_response'],
            'request_id': 'test-102-context'
        }

        result = await step_102__process_msg(messages=[], ctx=original_ctx.copy())

        # Verify all original context is preserved
        assert result['user_data'] == original_ctx['user_data']
        assert result['session_data'] == original_ctx['session_data']
        assert result['response_metadata'] == original_ctx['response_metadata']
        assert result['processing_history'] == original_ctx['processing_history']

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_adds_processing_metadata(self, mock_rag_log):
        """Test Step 102: Adds message processing metadata."""
        from app.orchestrators.response import step_102__process_msg

        messages = [
            HumanMessage(content="User question"),
            AIMessage(content="AI response")
        ]

        ctx = {
            'messages': messages,
            'request_id': 'test-102-metadata'
        }

        result = await step_102__process_msg(messages=[], ctx=ctx)

        assert result['processing_stage'] == 'message_processing'
        assert result['next_step'] == 'log_completion'
        assert 'message_processing_timestamp' in result
        assert result['original_message_count'] == 2
        assert result['processed_message_count'] == 2

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_handles_empty_messages_list(self, mock_rag_log):
        """Test Step 102: Handles empty messages list gracefully."""
        from app.orchestrators.response import step_102__process_msg

        ctx = {
            'messages': [],
            'response_source': 'empty_conversation',
            'request_id': 'test-102-empty'
        }

        result = await step_102__process_msg(messages=[], ctx=ctx)

        assert result['processed_messages'] == []
        assert result['original_message_count'] == 0
        assert result['processed_message_count'] == 0
        assert result['next_step'] == 'log_completion'

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_logs_processing_details(self, mock_rag_log):
        """Test Step 102: Logs message processing details for observability."""
        from app.orchestrators.response import step_102__process_msg

        messages = [
            SystemMessage(content="System prompt"),
            HumanMessage(content="User query"),
            AIMessage(content="AI response"),
            ToolMessage(content="Tool result", tool_call_id="call_1")
        ]

        ctx = {
            'messages': messages,
            'request_id': 'test-102-logging'
        }

        await step_102__process_msg(messages=[], ctx=ctx)

        # Verify structured logging
        assert mock_rag_log.call_count >= 2

        # Find the completion log call
        completion_call = None
        for call in mock_rag_log.call_args_list:
            if call[1].get('processing_stage') == 'completed':
                completion_call = call[1]
                break

        assert completion_call is not None
        assert completion_call['step'] == 102
        assert 'original_message_count' in completion_call or 'processing_stage' in completion_call


class TestRAGStep102Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_102_parity_message_conversion_behavior(self):
        """Test Step 102 parity: Message conversion behavior unchanged."""
        from app.orchestrators.response import step_102__process_msg

        test_cases = [
            # Case 1: Mixed message types
            {
                'messages': [
                    SystemMessage(content="System message"),
                    HumanMessage(content="User message 1"),
                    AIMessage(content="AI response 1"),
                    ToolMessage(content="Tool result", tool_call_id="call_1"),
                    HumanMessage(content="User message 2"),
                    AIMessage(content="AI response 2")
                ],
                'expected_count': 4  # Only user and assistant messages
            },
            # Case 2: Only valid messages
            {
                'messages': [
                    HumanMessage(content="Question"),
                    AIMessage(content="Answer")
                ],
                'expected_count': 2
            },
            # Case 3: Empty content filtering
            {
                'messages': [
                    HumanMessage(content="Valid message"),
                    AIMessage(content=""),  # Empty content
                    HumanMessage(content="Another valid message")
                ],
                'expected_count': 2
            }
        ]

        for i, test_case in enumerate(test_cases):
            ctx = {
                'messages': test_case['messages'],
                'request_id': f"parity-{i}"
            }

            with patch('app.orchestrators.response.rag_step_log'):
                result = await step_102__process_msg(messages=[], ctx=ctx)

            assert len(result['processed_messages']) == test_case['expected_count']
            assert result['next_step'] == 'log_completion'
            assert result['processing_stage'] == 'message_processing'


class TestRAGStep102Integration:
    """Integration tests for Step 102 with neighbors."""

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_final_response_to_102_integration(self, mock_final_log):
        """Test FinalResponse → Step 102 integration."""

        # Simulate incoming from FinalResponse (Step 101)
        final_response_ctx = {
            'messages': [
                HumanMessage(content="User query about Italian labor law"),
                AIMessage(content="Response about CCNL agreements and worker rights")
            ],
            'response_source': 'final_response',
            'processing_stage': 'final_response',
            'conversation_metadata': {
                'domain_classification': 'labor',
                'confidence': 0.92
            },
            'request_id': 'integration-final-102'
        }

        from app.orchestrators.response import step_102__process_msg

        result = await step_102__process_msg(messages=[], ctx=final_response_ctx)

        assert result['response_source'] == 'final_response'
        assert result['next_step'] == 'log_completion'
        assert len(result['processed_messages']) == 2
        assert 'conversation_metadata' in result

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_return_cached_to_102_integration(self, mock_cached_log):
        """Test ReturnCached → Step 102 integration."""

        # Simulate incoming from ReturnCached (Step 66)
        cached_ctx = {
            'messages': [
                HumanMessage(content="Cached query"),
                AIMessage(content="Cached response from Redis")
            ],
            'response_source': 'cached',
            'cached_metadata': {
                'cache_hit': True,
                'cache_key': 'query_sig_abc123',
                'cached_at': '2025-01-15T10:00:00Z'
            },
            'request_id': 'integration-cached-102'
        }

        from app.orchestrators.response import step_102__process_msg

        result = await step_102__process_msg(messages=[], ctx=cached_ctx)

        assert result['response_source'] == 'cached'
        assert result['next_step'] == 'log_completion'
        assert 'cached_metadata' in result
        assert len(result['processed_messages']) == 2

    @pytest.mark.asyncio
    @patch('app.orchestrators.response.rag_step_log')
    async def test_step_102_prepares_for_log_complete(self, mock_rag_log):
        """Test Step 102 prepares data for LogComplete (Step 103)."""
        from app.orchestrators.response import step_102__process_msg

        ctx = {
            'messages': [
                HumanMessage(content="Final user message"),
                AIMessage(content="Final assistant response")
            ],
            'processing_metrics': {
                'total_tokens': 150,
                'processing_time_ms': 1250
            },
            'completion_ready': True,
            'request_id': 'test-102-prep'
        }

        result = await step_102__process_msg(messages=[], ctx=ctx)

        # Verify data prepared for LogComplete step
        assert result['next_step'] == 'log_completion'
        assert result['processing_stage'] == 'message_processing'
        assert 'processing_metrics' in result
        assert 'completion_ready' in result
        assert len(result['processed_messages']) == 2
        assert result['processed_message_count'] == 2