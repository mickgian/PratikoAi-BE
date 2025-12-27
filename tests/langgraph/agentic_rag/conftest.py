"""Pytest configuration for Agentic RAG tests.

Provides fixtures to avoid database connections during unit tests.
These mocks must be applied before the test module imports any app code.
"""

import sys
from unittest.mock import MagicMock

# Mock database-related modules BEFORE any imports
# This prevents database connection attempts during test collection
_mock_database = MagicMock()
_mock_database.DatabaseService.return_value = MagicMock()
_mock_database.get_db_session.return_value = MagicMock()

# Pre-populate sys.modules with mocked database modules
sys.modules["app.services.database"] = _mock_database
sys.modules["app.models.database"] = MagicMock()
sys.modules["app.core.database"] = MagicMock()
