"""Test rag_step_log and rag_step_timer helpers."""

import time
from unittest.mock import patch

import pytest

from app.core.langgraph.types import rag_step_log, rag_step_timer


class TestLoggingHelpers:
    """Test logging helper functions."""

    def test_rag_step_log_basic(self):
        """Test basic rag_step_log functionality."""
        with patch('app.core.langgraph.types.logger') as mock_logger:
            rag_step_log(1, "enter")

            # Verify logger.info was called
            mock_logger.info.assert_called_once()
            args, kwargs = mock_logger.info.call_args

            # Check message format
            assert "RAG_STEP_1: enter" in args[0]

            # Check extra data
            assert "extra" in kwargs
            extra_data = kwargs["extra"]
            assert extra_data["step"] == 1
            assert extra_data["msg"] == "enter"

    def test_rag_step_log_with_attributes(self):
        """Test rag_step_log with additional attributes."""
        with patch('app.core.langgraph.types.logger') as mock_logger:
            rag_step_log(3, "exit", keys=["a", "b"], status="success")

            mock_logger.info.assert_called_once()
            args, kwargs = mock_logger.info.call_args

            assert "RAG_STEP_3: exit" in args[0]

            extra_data = kwargs["extra"]
            assert extra_data["step"] == 3
            assert extra_data["msg"] == "exit"
            assert extra_data["keys"] == ["a", "b"]
            assert extra_data["status"] == "success"

    def test_rag_step_timer_basic(self):
        """Test basic rag_step_timer functionality."""
        with patch('app.core.langgraph.types.logger') as mock_logger:
            with rag_step_timer(5):
                time.sleep(0.01)  # Small delay to ensure measurable duration

            # Verify timer log was called
            mock_logger.info.assert_called_once()
            args, kwargs = mock_logger.info.call_args

            # Check timer message format
            assert "RAG_STEP_5_TIMER:" in args[0]
            assert "s" in args[0]  # Duration should be logged with 's'

            # Check extra data
            extra_data = kwargs["extra"]
            assert extra_data["step"] == 5
            assert "duration_seconds" in extra_data
            assert isinstance(extra_data["duration_seconds"], float)
            assert extra_data["duration_seconds"] > 0

    def test_rag_step_timer_with_exception(self):
        """Test rag_step_timer logs duration even when exception occurs."""
        with patch('app.core.langgraph.types.logger') as mock_logger:
            with pytest.raises(ValueError):
                with rag_step_timer(10):
                    raise ValueError("Test exception")

            # Timer should still log despite exception
            mock_logger.info.assert_called_once()
            args, kwargs = mock_logger.info.call_args
            assert "RAG_STEP_10_TIMER:" in args[0]

    def test_rag_step_timer_duration_precision(self):
        """Test that timer duration has correct precision."""
        with patch('app.core.langgraph.types.logger') as mock_logger:
            with rag_step_timer(7):
                pass

            args, kwargs = mock_logger.info.call_args

            # Duration should be formatted to 3 decimal places
            duration_str = args[0]
            # Extract the duration part (e.g., "0.001s")
            import re
            match = re.search(r'(\d+\.\d{3})s', duration_str)
            assert match is not None, f"Duration format not found in: {duration_str}"