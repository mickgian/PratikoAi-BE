"""Pytest configuration for unit tests.

Mocks database initialization to allow unit tests to run without a database.
The sys.modules pre-population MUST happen at module level (not inside a fixture)
so it takes effect before pytest collects test modules and triggers imports.
"""

import sys
from unittest.mock import AsyncMock, MagicMock

# Pre-populate sys.modules BEFORE any test module is collected.
if "app.models.database" not in sys.modules:
    _mock_models_db = MagicMock()
    _mock_models_db.AsyncSessionLocal = MagicMock()
    _mock_models_db.async_engine = MagicMock()
    _mock_models_db.sync_engine = MagicMock()
    _mock_models_db.get_sync_session = MagicMock()
    _mock_models_db.get_async_database_url = MagicMock(return_value="postgresql+asyncpg://test:test@localhost/test")
    sys.modules["app.models.database"] = _mock_models_db

if "app.services.database" not in sys.modules:
    _mock_db = MagicMock()
    _mock_db.is_connected = True
    _mock_module = MagicMock()
    _mock_module.database_service = _mock_db
    sys.modules["app.services.database"] = _mock_module

# Mock app.core.embed to prevent OpenAI client instantiation and
# tiktoken encoding download at import time.
if "app.core.embed" not in sys.modules:
    _mock_embed = MagicMock()
    _mock_embed.generate_embedding = AsyncMock(return_value=None)
    _mock_embed.generate_embeddings_batch = AsyncMock(return_value=[])
    _mock_embed.embedding_to_pgvector = MagicMock(return_value=None)
    _mock_embed.truncate_to_token_limit = MagicMock(side_effect=lambda text, **kw: text)
    _mock_embed.validate_embedding = MagicMock(return_value=True)
    _mock_embed.cosine_similarity = MagicMock(return_value=0.9)
    _mock_embed.embed_text_for_storage = AsyncMock(return_value=None)
    _mock_embed.pgvector_to_embedding = MagicMock(return_value=None)
    _mock_embed.EMBED_DIM = 1536
    _mock_embed.EMBED_MODEL = "text-embedding-3-small"
    sys.modules["app.core.embed"] = _mock_embed
