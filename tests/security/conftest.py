"""Conftest for security tests - mock DB and embed modules."""

import sys
from unittest.mock import AsyncMock as _AsyncMock
from unittest.mock import MagicMock as _MagicMock

if "app.services.database" not in sys.modules:
    _mock_db = _MagicMock()
    _mock_db.is_connected = True
    _mock_module = _MagicMock()
    _mock_module.database_service = _mock_db
    sys.modules["app.services.database"] = _mock_module

if "app.core.embed" not in sys.modules:
    _mock_embed = _MagicMock()
    _mock_embed.generate_embedding = _AsyncMock(return_value=None)
    _mock_embed.cosine_similarity = _MagicMock(return_value=0.9)
    _mock_embed.EMBED_DIM = 1536
    sys.modules["app.core.embed"] = _mock_embed
