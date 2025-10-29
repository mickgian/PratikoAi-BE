#!/usr/bin/env python3
"""
Tests for RAG STEP 12 — LangGraphAgent._classify_user_query Extract user message

This step extracts the latest user message from a conversation for classification.
Connects from Step 11 (ConvertMessages) and feeds into classification workflow.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.chat import Message


class TestRAGStep12ExtractQuery:
    """Test suite for RAG STEP 12 - Extract user message"""

    @pytest.fixture
    def mock_conversation_messages(self):
        """Mock conversation with multiple message types."""
        return [
            Message(role="system", content="You are a helpful assistant"),
            Message(role="user", content="What are my tax obligations?"),
            Message(role="assistant", content="Tax obligations depend on your status..."),
            Message(role="user", content="Can you be more specific for freelancers?")
        ]

    @pytest.fixture
    def mock_single_user_message(self):
        """Mock conversation with single user message."""
        return [
            Message(role="user", content="Calculate my income tax for 2024")
        ]

    @pytest.fixture
    def mock_no_user_messages(self):
        """Mock conversation with no user messages."""
        return [
            Message(role="system", content="System message"),
            Message(role="assistant", content="Assistant response")
        ]

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_successful_extraction(self, mock_logger, mock_rag_log, mock_conversation_messages):
        """Test Step 12: Successful extraction of latest user message"""
        from app.orchestrators.classify import step_12__extract_query

        # Context with converted messages from Step 11
        ctx = {
            'converted_messages': mock_conversation_messages,
            'message_count': len(mock_conversation_messages),
            'request_id': 'req_123'
        }

        # Call the orchestrator function
        result = await step_12__extract_query(ctx=ctx)

        # Verify result structure
        assert isinstance(result, dict)
        assert result['extraction_successful'] is True
        assert result['user_message_found'] is True
        assert result['extracted_query'] == "Can you be more specific for freelancers?"
        assert result['user_message_count'] == 2
        assert result['next_step'] == 'ClassifyDomain'
        assert 'latest_user_message' in result

        # Verify logging
        mock_logger.info.assert_called()
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any('User query extraction completed' in call for call in log_calls)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        assert len(completed_logs) > 0
        log_call = completed_logs[0]
        assert log_call[1]['step'] == 12
        assert log_call[1]['extraction_successful'] is True
        assert log_call[1]['user_message_found'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_single_user_message(self, mock_logger, mock_rag_log, mock_single_user_message):
        """Test Step 12: Extract from conversation with single user message"""
        from app.orchestrators.classify import step_12__extract_query

        ctx = {
            'converted_messages': mock_single_user_message,
            'message_count': 1,
            'request_id': 'req_456'
        }

        result = await step_12__extract_query(ctx=ctx)

        # Should extract the only user message
        assert result['extraction_successful'] is True
        assert result['user_message_found'] is True
        assert result['extracted_query'] == "Calculate my income tax for 2024"
        assert result['user_message_count'] == 1
        assert result['latest_user_message'].role == 'user'

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_no_user_messages(self, mock_logger, mock_rag_log, mock_no_user_messages):
        """Test Step 12: Handle conversation with no user messages"""
        from app.orchestrators.classify import step_12__extract_query

        ctx = {
            'converted_messages': mock_no_user_messages,
            'message_count': 2,
            'request_id': 'req_nouser'
        }

        result = await step_12__extract_query(ctx=ctx)

        # Should handle gracefully but indicate no user message found
        assert result['extraction_successful'] is True
        assert result['user_message_found'] is False
        assert result['extracted_query'] is None
        assert result['user_message_count'] == 0
        assert result['next_step'] == 'DefaultPrompt'  # Skip classification

        # Verify warning logged
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_empty_messages(self, mock_logger, mock_rag_log):
        """Test Step 12: Handle empty message list"""
        from app.orchestrators.classify import step_12__extract_query

        ctx = {
            'converted_messages': [],
            'message_count': 0,
            'request_id': 'req_empty'
        }

        result = await step_12__extract_query(ctx=ctx)

        # Should handle empty list gracefully
        assert result['extraction_successful'] is True
        assert result['user_message_found'] is False
        assert result['extracted_query'] is None
        assert result['user_message_count'] == 0
        assert result['next_step'] == 'DefaultPrompt'

        # Verify warning logged
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_message_content_analysis(self, mock_logger, mock_rag_log):
        """Test Step 12: Analyze different types of user message content"""
        from app.orchestrators.classify import step_12__extract_query

        # Messages with various content types
        complex_messages = [
            Message(role="user", content="Short query"),
            Message(role="assistant", content="Response"),
            Message(role="user", content="This is a very long user query that contains multiple sentences. It asks about complex tax regulations for small businesses. The user wants detailed information about deductions, filing requirements, and compliance rules.")
        ]

        ctx = {
            'converted_messages': complex_messages,
            'request_id': 'req_analysis'
        }

        result = await step_12__extract_query(ctx=ctx)

        # Should extract the latest (longest) user message
        assert result['extraction_successful'] is True
        assert result['user_message_found'] is True
        assert len(result['extracted_query']) > 100  # Long message
        assert 'tax regulations' in result['extracted_query']
        assert result['query_length'] > 100
        assert result['query_complexity'] == 'complex'  # Based on length

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_message_extraction_order(self, mock_logger, mock_rag_log):
        """Test Step 12: Verify latest message extraction (reverse chronological)"""
        from app.orchestrators.classify import step_12__extract_query

        # Messages in chronological order
        time_ordered_messages = [
            Message(role="user", content="First user message"),
            Message(role="user", content="Second user message"),
            Message(role="assistant", content="Assistant response"),
            Message(role="user", content="Latest user message")  # This should be extracted
        ]

        ctx = {
            'converted_messages': time_ordered_messages,
            'request_id': 'req_order'
        }

        result = await step_12__extract_query(ctx=ctx)

        # Should extract the last user message in the list
        assert result['extraction_successful'] is True
        assert result['extracted_query'] == "Latest user message"
        assert result['message_position'] == 3  # 0-indexed position
        assert result['user_message_count'] == 3

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_query_preprocessing(self, mock_logger, mock_rag_log):
        """Test Step 12: Query text preprocessing and normalization"""
        from app.orchestrators.classify import step_12__extract_query

        # Message with extra whitespace and formatting
        messy_messages = [
            Message(role="user", content="  \n\t What are my tax obligations?  \n  ")
        ]

        ctx = {
            'converted_messages': messy_messages,
            'request_id': 'req_preprocess'
        }

        result = await step_12__extract_query(ctx=ctx)

        # Should clean up the extracted query
        assert result['extraction_successful'] is True
        assert result['extracted_query'] == "What are my tax obligations?"  # Trimmed
        assert result['original_query'] == "  \n\t What are my tax obligations?  \n  "
        assert result['preprocessing_applied'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_ready_for_classification(self, mock_logger, mock_rag_log, mock_conversation_messages):
        """Test Step 12: Output ready for classification steps"""
        from app.orchestrators.classify import step_12__extract_query

        ctx = {
            'converted_messages': mock_conversation_messages,
            'request_id': 'req_ready'
        }

        result = await step_12__extract_query(ctx=ctx)

        # Verify output is ready for classification
        assert result['ready_for_classification'] is True
        assert 'extracted_query' in result
        assert 'latest_user_message' in result
        assert result['next_step'] == 'ClassifyDomain'

        # These fields needed for classification steps
        assert result['extracted_query'] is not None
        assert len(result['extracted_query']) > 0
        assert isinstance(result['latest_user_message'], Message)

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_comprehensive_logging(self, mock_logger, mock_rag_log, mock_conversation_messages):
        """Test Step 12: Comprehensive logging format"""
        from app.orchestrators.classify import step_12__extract_query

        ctx = {
            'converted_messages': mock_conversation_messages,
            'request_id': 'req_comprehensive'
        }

        await step_12__extract_query(ctx=ctx)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]

        assert len(completed_logs) > 0
        log_call = completed_logs[0]

        # Check required fields
        required_fields = [
            'step', 'step_id', 'node_label',
            'extraction_successful', 'user_message_found', 'user_message_count',
            'processing_stage', 'next_step'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]['step'] == 12
        assert log_call[1]['step_id'] == 'RAG.classify.langgraphagent.classify.user.query.extract.user.message'
        assert log_call[1]['node_label'] == 'ExtractQuery'

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_performance_tracking(self, mock_logger, mock_rag_log, mock_conversation_messages):
        """Test Step 12: Performance tracking with timer"""
        from app.orchestrators.classify import step_12__extract_query

        with patch('app.orchestrators.classify.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            ctx = {
                'converted_messages': mock_conversation_messages,
                'request_id': 'req_perf'
            }

            await step_12__extract_query(ctx=ctx)

            # Verify timer was used
            mock_timer.assert_called_with(
                12,
                'RAG.classify.langgraphagent.classify.user.query.extract.user.message',
                'ExtractQuery',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_parity_preservation(self, mock_logger, mock_rag_log, mock_conversation_messages):
        """Test Step 12: Parity test - behavior identical to LangGraphAgent._classify_user_query extraction"""
        from app.orchestrators.classify import step_12__extract_query

        ctx = {
            'converted_messages': mock_conversation_messages,
            'request_id': 'req_parity'
        }

        # Call orchestrator
        result = await step_12__extract_query(ctx=ctx)

        # Verify behavior matches expected LangGraphAgent._classify_user_query extraction
        assert result['extraction_successful'] is True
        assert result['user_message_found'] is True

        # Should extract the latest user message (same as original implementation)
        expected_query = "Can you be more specific for freelancers?"
        assert result['extracted_query'] == expected_query

        # Verify message analysis is preserved
        assert result['user_message_count'] == 2  # Total user messages
        assert isinstance(result['latest_user_message'], Message)
        assert result['latest_user_message'].content == expected_query

    @pytest.mark.asyncio
    @patch('app.orchestrators.classify.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_12_error_handling(self, mock_logger, mock_rag_log):
        """Test Step 12: Error handling with invalid input"""
        from app.orchestrators.classify import step_12__extract_query

        # Test with None context
        result = await step_12__extract_query(ctx=None)

        # Should handle gracefully
        assert result['extraction_successful'] is False
        assert 'error' in result
        assert 'Missing context' in result['error']

        # Verify error logging
        mock_logger.error.assert_called_once()