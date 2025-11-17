"""Test node wrapper delegation pattern."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.langgraph.nodes.step_001__validate_request import node_step_1
from app.core.langgraph.nodes.step_003__valid_check import node_step_3
from app.core.langgraph.nodes.step_006__privacy_check import node_step_6
from app.core.langgraph.types import RAGState


class TestNodeWrapperDelegation:
    """Test that node wrappers properly delegate to orchestrator functions."""

    @pytest.mark.asyncio
    async def test_node_step_1_delegation(self):
        """Test step 1 node wrapper delegates correctly."""
        with (
            patch(
                "app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            mock_orchestrator.return_value = {"request_valid": True}

            initial_state = RAGState({"request_id": "test-123", "messages": [{"role": "user", "content": "Hello"}]})

            result = await node_step_1(initial_state)

            # Verify orchestrator was called with correct parameters
            mock_orchestrator.assert_called_once()
            call_args = mock_orchestrator.call_args
            assert call_args[1]["messages"] == [{"role": "user", "content": "Hello"}]
            assert "ctx" in call_args[1]

            # Verify result is merged back into state
            assert isinstance(result, dict)  # RAGState is a dict subclass
            assert result["request_id"] == "test-123"
            assert result["request_valid"] is True

    def test_node_step_3_delegation(self):
        """Test step 3 node wrapper delegates correctly."""
        with patch("app.core.langgraph.nodes.step_003__valid_check.step_3__valid_check") as mock_orchestrator:
            with patch("app.core.langgraph.types.logger"):
                mock_orchestrator.return_value = {"validation_result": "passed"}

                initial_state = RAGState({"request_id": "test-456", "messages": []})

                result = node_step_3(initial_state)

                # Verify orchestrator was called
                mock_orchestrator.assert_called_once()
                call_args = mock_orchestrator.call_args
                assert call_args[1]["messages"] == []
                assert call_args[1]["ctx"]["request_id"] == "test-456"

                # Verify result
                assert result["validation_result"] == "passed"

    @pytest.mark.asyncio
    async def test_async_node_step_6_delegation(self):
        """Test async step 6 node wrapper delegates correctly."""
        with (
            patch(
                "app.core.langgraph.nodes.step_006__privacy_check.step_6__privacy_check", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            mock_orchestrator.return_value = {"privacy_enabled": False}

            initial_state = RAGState(
                {"request_id": "test-789", "messages": [{"role": "user", "content": "Test message"}]}
            )

            result = await node_step_6(initial_state)

            # Verify orchestrator was called
            mock_orchestrator.assert_called_once()
            call_args = mock_orchestrator.call_args
            assert call_args[1]["messages"] == [{"role": "user", "content": "Test message"}]

            # Verify result
            assert result["privacy_enabled"] is False

    @pytest.mark.asyncio
    async def test_state_immutability(self):
        """Test that original state is not modified by node wrappers."""
        with (
            patch(
                "app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.types.logger"),
        ):
            mock_orchestrator.return_value = {"new_field": "new_value"}

            original_state = RAGState({"request_id": "test-immutable", "existing_field": "existing_value"})

            # Make a copy to compare
            original_copy = original_state.copy()

            result = await node_step_1(original_state)

            # Original state should be unchanged
            assert original_state == original_copy
            assert "new_field" not in original_state

            # Result should have new field
            assert result["new_field"] == "new_value"
            assert result["existing_field"] == "existing_value"

    @pytest.mark.asyncio
    async def test_logging_calls(self):
        """Test that node wrappers make proper logging calls."""
        with (
            patch(
                "app.core.langgraph.nodes.step_001__validate_request.step_1__validate_request", new_callable=AsyncMock
            ) as mock_orchestrator,
            patch("app.core.langgraph.nodes.step_001__validate_request.rag_step_log") as mock_log,
        ):
            with patch("app.core.langgraph.nodes.step_001__validate_request.rag_step_timer") as mock_timer:
                mock_orchestrator.return_value = {}
                mock_timer.return_value.__enter__ = MagicMock()
                mock_timer.return_value.__exit__ = MagicMock()

                state = RAGState({"request_id": "test-logging"})
                await node_step_1(state)

                # Verify logging calls
                assert mock_log.call_count == 2  # enter and exit
                enter_call = mock_log.call_args_list[0]
                exit_call = mock_log.call_args_list[1]

                # Check enter call
                assert enter_call[0][0] == 1  # step number
                assert enter_call[0][1] == "enter"

                # Check exit call
                assert exit_call[0][0] == 1  # step number
                assert exit_call[0][1] == "exit"

                # Verify timer was used
                mock_timer.assert_called_once_with(1)
