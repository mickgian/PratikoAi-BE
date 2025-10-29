"""
Pytest configuration and fixtures for the test suite.

This module provides common fixtures and configuration for all tests,
including database mocking and async support.
"""

import os
import pytest
from contextlib import contextmanager
from unittest.mock import Mock, AsyncMock, patch


def pytest_addoption(parser):
    """Add custom command-line options for Phase 9 tests."""
    parser.addoption(
        "--budget-cache",
        action="store",
        default=None,
        type=int,
        help="Cache operation budget in milliseconds (default: 25ms)",
    )
    parser.addoption(
        "--budget-llm",
        action="store",
        default=None,
        type=int,
        help="LLM wrapper budget in milliseconds (default: 400ms)",
    )
    parser.addoption(
        "--budget-tools",
        action="store",
        default=None,
        type=int,
        help="Tools wrapper budget in milliseconds (default: 200ms)",
    )
    parser.addoption(
        "--budget-stream",
        action="store",
        default=None,
        type=int,
        help="Streaming budget in milliseconds (default: 150ms)",
    )
    parser.addoption(
        "--budget-provider",
        action="store",
        default=None,
        type=int,
        help="Provider selection budget in milliseconds (default: 50ms)",
    )
    parser.addoption(
        "--budget-privacy",
        action="store",
        default=None,
        type=int,
        help="Privacy check budget in milliseconds (default: 30ms)",
    )
    parser.addoption(
        "--budget-golden",
        action="store",
        default=None,
        type=int,
        help="Golden lookup budget in milliseconds (default: 40ms)",
    )


@pytest.fixture(scope="session", autouse=True)
def set_budget_env_vars(request):
    """Set budget environment variables from CLI options."""
    budget_mappings = {
        "budget_cache": "RAG_BUDGET_P95_CACHE_MS",
        "budget_llm": "RAG_BUDGET_P95_LLM_MS",
        "budget_tools": "RAG_BUDGET_P95_TOOLS_MS",
        "budget_stream": "RAG_BUDGET_P95_STREAM_MS",
        "budget_provider": "RAG_BUDGET_P95_PROVIDER_MS",
        "budget_privacy": "RAG_BUDGET_P95_PRIVACY_MS",
        "budget_golden": "RAG_BUDGET_P95_GOLDEN_MS",
    }

    for opt_name, env_var in budget_mappings.items():
        value = request.config.getoption(f"--{opt_name.replace('_', '-')}")
        if value is not None:
            os.environ[env_var] = str(value)


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.exec = Mock()
    return session


@contextmanager
def assume_mock_database():
    """Context manager to assume mock database operations work correctly."""
    # In real tests, this would set up test database or mock objects
    # For now, it's a placeholder that allows tests to pass
    yield


# Add the fixture to pytest namespace
pytest.assume_mock_database = assume_mock_database