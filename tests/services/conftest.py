"""
Pytest configuration for services tests.

Mocks database initialization to allow unit tests to run without database.
"""

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session", autouse=True)
def mock_database_service():
    """Mock database_service before app.services is imported."""
    # Create a mock database service
    mock_db = MagicMock()
    mock_db.is_connected = True

    # Pre-populate sys.modules to prevent actual import
    if "app.services.database" not in sys.modules:
        mock_module = MagicMock()
        mock_module.database_service = mock_db
        sys.modules["app.services.database"] = mock_module
