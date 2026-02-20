"""Pytest configuration for Agentic RAG tests.

Provides fixtures for testing LangGraph nodes in isolation.
Tests mock external dependencies (LLMRouterService, etc.) via patch decorators.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_llm_router_service():
    """Fixture to create a mock LLMRouterService for tests."""
    mock_service = AsyncMock()
    return mock_service


@pytest.fixture
def mock_rag_state():
    """Fixture to create a base RAG state for testing."""
    return {
        "request_id": "test-request-id",
        "session_id": "test-session-id",
        "user_query": "Test query",
        "messages": [{"role": "user", "content": "Test query"}],
    }
