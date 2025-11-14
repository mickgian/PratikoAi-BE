#!/usr/bin/env python3
"""
Tests for RAG STEP 15 — Continue without classification

This step bypasses classification and proceeds with default prompting.
Used when classification fails or is not needed for the workflow.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.chat import Message


class TestRAGStep15DefaultPrompt:
    """Test suite for RAG STEP 15 - Continue without classification"""

    @pytest.fixture
    def mock_user_messages(self):
        """Mock user messages for processing."""
        return [
            Message(role="user", content="What are Italian tax regulations?"),
            Message(role="assistant", content="Tax regulations vary by region..."),
            Message(role="user", content="Tell me more about VAT")
        ]

    @pytest.fixture
    def mock_classification_failed_context(self):
        """Mock context when classification has failed."""
        return {
            'classification_attempted': True,
            'classification_successful': False,
            'classification_error': 'Low confidence threshold not met',
            'user_query': 'Tell me more about VAT',
            'request_id': 'req_123'
        }

    @pytest.fixture
    def mock_no_classification_context(self):
        """Mock context when no classification was attempted."""
        return {
            'classification_attempted': False,
            'user_query': 'Simple question about taxes',
            'request_id': 'req_456'
        }

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_successful_default_prompt(self, mock_logger, mock_rag_log, mock_classification_failed_context):
        """Test Step 15: Successful default prompt setup after classification failure"""
        from app.orchestrators.prompting import step_15__default_prompt

        # Context with classification failure
        ctx = mock_classification_failed_context

        # Call the orchestrator function
        result = await step_15__default_prompt(ctx=ctx)

        # Verify result structure
        assert isinstance(result, dict)
        assert result['default_prompt_applied'] is True
        assert result['classification_bypassed'] is True
        assert result['prompt_strategy'] == 'default'
        assert result['next_step'] == 'SelectPrompt'
        assert 'system_prompt' in result
        assert 'prompt_context' in result

        # Verify logging
        mock_logger.info.assert_called()
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any('Default prompt setup completed' in call for call in log_calls)

        # Verify RAG step logging
        completed_logs = [
            call for call in mock_rag_log.call_args_list
            if call[1].get('processing_stage') == 'completed'
        ]
        assert len(completed_logs) > 0
        log_call = completed_logs[0]
        assert log_call[1]['step'] == 15
        assert log_call[1]['default_prompt_applied'] is True
        assert log_call[1]['classification_bypassed'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_no_classification_attempted(self, mock_logger, mock_rag_log, mock_no_classification_context):
        """Test Step 15: Default prompt when no classification was attempted"""
        from app.orchestrators.prompting import step_15__default_prompt

        ctx = mock_no_classification_context

        result = await step_15__default_prompt(ctx=ctx)

        # Should succeed with no classification context
        assert result['default_prompt_applied'] is True
        assert result['classification_bypassed'] is True
        assert result['bypass_reason'] == 'no_classification_attempted'
        assert result['prompt_strategy'] == 'default'

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    @patch('app.core.prompts.SYSTEM_PROMPT', 'You are a helpful assistant.')
    async def test_step_15_system_prompt_selection(self, mock_logger, mock_rag_log):
        """Test Step 15: System prompt selection and setup"""
        from app.orchestrators.prompting import step_15__default_prompt

        ctx = {
            'user_query': 'What is 2+2?',
            'request_id': 'req_prompt'
        }

        result = await step_15__default_prompt(ctx=ctx)

        # Should use default system prompt
        assert result['default_prompt_applied'] is True
        assert result['system_prompt'] is not None
        assert len(result['system_prompt']) > 0
        assert result['prompt_type'] == 'system'
        assert result['prompt_source'] == 'default'

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_prompt_context_building(self, mock_logger, mock_rag_log):
        """Test Step 15: Build prompt context for downstream processing"""
        from app.orchestrators.prompting import step_15__default_prompt

        ctx = {
            'user_query': 'Explain Italian tax law',
            'user_messages': [
                Message(role="user", content="What are my obligations?"),
                Message(role="user", content="Explain Italian tax law")
            ],
            'session_context': {'user_id': 123, 'session_id': 'sess_789'},
            'request_id': 'req_context'
        }

        result = await step_15__default_prompt(ctx=ctx)

        # Should build comprehensive prompt context
        assert result['default_prompt_applied'] is True
        assert 'prompt_context' in result

        prompt_context = result['prompt_context']
        assert 'user_query' in prompt_context
        assert 'message_count' in prompt_context
        assert 'strategy' in prompt_context
        assert prompt_context['strategy'] == 'default_prompting'

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_empty_context(self, mock_logger, mock_rag_log):
        """Test Step 15: Handle empty context gracefully"""
        from app.orchestrators.prompting import step_15__default_prompt

        # Call with no context
        result = await step_15__default_prompt(ctx={})

        # Should still succeed with defaults
        assert result['default_prompt_applied'] is True
        assert result['classification_bypassed'] is True
        assert result['prompt_strategy'] == 'default'
        assert result['next_step'] == 'SelectPrompt'

        # Verify warning logged
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_query_analysis(self, mock_logger, mock_rag_log):
        """Test Step 15: Analyze user query characteristics"""
        from app.orchestrators.prompting import step_15__default_prompt

        # Test with different query types
        test_cases = [
            ("Simple question", "simple"),
            ("This is a more complex question about tax regulations that requires detailed analysis", "medium"),  # 94 chars = medium
            ("What is VAT?", "simple")
        ]

        for query, expected_complexity in test_cases:
            ctx = {
                'user_query': query,
                'request_id': f'req_{expected_complexity}'
            }

            result = await step_15__default_prompt(ctx=ctx)

            assert result['default_prompt_applied'] is True
            assert result['query_analysis']['complexity'] == expected_complexity
            assert result['query_analysis']['length'] == len(query)

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_workflow_routing(self, mock_logger, mock_rag_log):
        """Test Step 15: Proper workflow routing decisions"""
        from app.orchestrators.prompting import step_15__default_prompt

        ctx = {
            'user_query': 'Help with taxes',
            'workflow_mode': 'standard',
            'request_id': 'req_routing'
        }

        result = await step_15__default_prompt(ctx=ctx)

        # Should route to appropriate next step
        assert result['default_prompt_applied'] is True
        assert result['next_step'] == 'SelectPrompt'
        assert result['routing_decision'] == 'default_workflow'
        assert result['ready_for_prompt_selection'] is True

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_ready_for_prompt_selection(self, mock_logger, mock_rag_log, mock_classification_failed_context):
        """Test Step 15: Output ready for prompt selection steps"""
        from app.orchestrators.prompting import step_15__default_prompt

        ctx = mock_classification_failed_context

        result = await step_15__default_prompt(ctx=ctx)

        # Verify output is ready for prompt selection
        assert result['ready_for_prompt_selection'] is True
        assert 'system_prompt' in result
        assert 'prompt_context' in result
        assert result['next_step'] == 'SelectPrompt'

        # These fields needed for prompt selection steps
        assert result['system_prompt'] is not None
        assert result['prompt_context'] is not None
        assert 'strategy' in result['prompt_context']

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_comprehensive_logging(self, mock_logger, mock_rag_log, mock_classification_failed_context):
        """Test Step 15: Comprehensive logging format"""
        from app.orchestrators.prompting import step_15__default_prompt

        ctx = mock_classification_failed_context

        await step_15__default_prompt(ctx=ctx)

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
            'default_prompt_applied', 'classification_bypassed', 'prompt_strategy',
            'processing_stage', 'next_step'
        ]

        for field in required_fields:
            assert field in log_call[1], f"Missing field: {field}"

        assert log_call[1]['step'] == 15
        assert log_call[1]['step_id'] == 'RAG.prompting.continue.without.classification'
        assert log_call[1]['node_label'] == 'DefaultPrompt'

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_performance_tracking(self, mock_logger, mock_rag_log, mock_classification_failed_context):
        """Test Step 15: Performance tracking with timer"""
        from app.orchestrators.prompting import step_15__default_prompt

        with patch('app.orchestrators.prompting.rag_step_timer') as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            ctx = mock_classification_failed_context

            await step_15__default_prompt(ctx=ctx)

            # Verify timer was used
            mock_timer.assert_called_with(
                15,
                'RAG.prompting.continue.without.classification',
                'DefaultPrompt',
                stage='start'
            )

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_parity_preservation(self, mock_logger, mock_rag_log, mock_classification_failed_context):
        """Test Step 15: Parity test - behavior identical to original default prompting"""
        from app.orchestrators.prompting import step_15__default_prompt

        ctx = mock_classification_failed_context

        # Call orchestrator
        result = await step_15__default_prompt(ctx=ctx)

        # Verify behavior matches expected default prompting workflow
        assert result['default_prompt_applied'] is True
        assert result['classification_bypassed'] is True
        assert result['prompt_strategy'] == 'default'

        # Should use appropriate system prompt
        assert result['system_prompt'] is not None
        assert len(result['system_prompt']) > 0

        # Should build proper prompt context
        assert 'prompt_context' in result
        assert result['prompt_context']['strategy'] == 'default_prompting'

    @pytest.mark.asyncio
    @patch('app.orchestrators.prompting.rag_step_log')
    @patch('app.core.logging.logger')
    async def test_step_15_error_handling(self, mock_logger, mock_rag_log):
        """Test Step 15: Error handling with invalid input"""
        from app.orchestrators.prompting import step_15__default_prompt

        # Test with None context
        result = await step_15__default_prompt(ctx=None)

        # Should handle gracefully
        assert result['default_prompt_applied'] is False
        assert 'error' in result
        assert 'Missing context' in result['error']

        # Verify error logging
        mock_logger.error.assert_called_once()