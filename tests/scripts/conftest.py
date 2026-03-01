"""Conftest for scripts tests — mocks DB to avoid connection at import time."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

if not os.environ.get("POSTGRES_URL"):
    os.environ["POSTGRES_URL"] = "postgresql://test:test@localhost:5432/pratikoai_test"

if "app.services.database" not in sys.modules:
    _mock_db = MagicMock()
    _mock_db.is_connected = True
    _mock_module = MagicMock()
    _mock_module.database_service = _mock_db
    sys.modules["app.services.database"] = _mock_module

if "app.core.embed" not in sys.modules:
    _mock_embed = MagicMock()
    _mock_embed.generate_embedding = AsyncMock(return_value=None)
    sys.modules["app.core.embed"] = _mock_embed
