"""Conftest for API v1 tests - ensures DB env vars are set before app imports.

Mocks database initialization to allow unit tests to run without database.
The sys.modules pre-population MUST happen at module level (not inside a fixture)
so it takes effect before pytest collects test modules and triggers imports.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

if not os.environ.get("POSTGRES_URL"):
    os.environ["POSTGRES_URL"] = "postgresql://test:test@localhost:5432/pratikoai_test"

# Pre-populate sys.modules BEFORE any test module is collected.
# This prevents app.services.database from creating a DB engine at import time.
if "app.services.database" not in sys.modules:
    _mock_db = MagicMock()
    _mock_db.is_connected = True
    _mock_module = MagicMock()
    _mock_module.database_service = _mock_db
    sys.modules["app.services.database"] = _mock_module

# Mock app.core.embed to prevent tiktoken downloads at import time.
if "app.core.embed" not in sys.modules:
    _mock_embed = MagicMock()
    _mock_embed.generate_embedding = AsyncMock(return_value=None)
    _mock_embed.generate_embeddings_batch = AsyncMock(return_value=[])
    _mock_embed.embedding_to_pgvector = MagicMock(
        side_effect=lambda emb: ("[" + ",".join(str(x) for x in emb) + "]") if emb else None
    )
    _mock_embed.truncate_to_token_limit = MagicMock(side_effect=lambda text, **kw: text)
    _mock_embed.validate_embedding = MagicMock(return_value=True)
    _mock_embed.cosine_similarity = MagicMock(return_value=0.9)
    _mock_embed.embed_text_for_storage = AsyncMock(return_value=None)
    _mock_embed.pgvector_to_embedding = MagicMock(return_value=None)
    _mock_embed.EMBED_DIM = 1536
    _mock_embed.EMBED_MODEL = "text-embedding-3-small"
    sys.modules["app.core.embed"] = _mock_embed
