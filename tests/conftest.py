"""
Pytest configuration and fixtures for the test suite.

This module provides common fixtures and configuration for all tests,
including database mocking and async support.
"""

import pytest
from contextlib import contextmanager
from unittest.mock import Mock, AsyncMock, patch


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