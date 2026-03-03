"""Tests for inline embedding generation in TieredIngestionService.

Verifies that tiered ingestion generates embeddings at ingestion time
instead of relying solely on the daily backfill task.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.knowledge import KnowledgeItem
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.document_classifier import (
    ClassificationResult,
    DocumentClassifier,
    DocumentTier,
    ParsingStrategy,
)
from app.services.italian_law_parser import ItalianLawParser, LawArticle, ParsedLaw
from app.services.tiered_ingestion_service import TieredIngestionService

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Async DB session that tracks added items and assigns IDs on flush."""
    db = AsyncMock()
    db._added_items: list = []

    def _add(item):
        db._added_items.append(item)

    db.add = _add

    async def _flush():
        for i, item in enumerate(db._added_items):
            if hasattr(item, "id") and item.id is None:
                item.id = i + 1

    db.flush = AsyncMock(side_effect=_flush)
    db.commit = AsyncMock()

    # No duplicate content hash
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.fixture
def tier1_classifier() -> MagicMock:
    classifier = MagicMock(spec=DocumentClassifier)
    classifier.classify.return_value = ClassificationResult(
        tier=DocumentTier.CRITICAL,
        parsing_strategy=ParsingStrategy.ARTICLE_LEVEL,
        confidence=1.0,
        matched_pattern="explicit:test",
        detected_topics=["irpef"],
        is_explicit_match=True,
    )
    return classifier


@pytest.fixture
def tier2_classifier() -> MagicMock:
    classifier = MagicMock(spec=DocumentClassifier)
    classifier.classify.return_value = ClassificationResult(
        tier=DocumentTier.IMPORTANT,
        parsing_strategy=ParsingStrategy.STANDARD_CHUNKING,
        confidence=0.9,
        matched_pattern="Circolare",
        detected_topics=["iva"],
        is_explicit_match=False,
    )
    return classifier


@pytest.fixture
def tier3_classifier() -> MagicMock:
    classifier = MagicMock(spec=DocumentClassifier)
    classifier.classify.return_value = ClassificationResult(
        tier=DocumentTier.REFERENCE,
        parsing_strategy=ParsingStrategy.LIGHT_INDEXING,
        confidence=0.5,
        matched_pattern=None,
        detected_topics=[],
        is_explicit_match=False,
    )
    return classifier


@pytest.fixture
def mock_parser() -> MagicMock:
    """Law parser returning 2 articles and 1 allegato."""
    parser = MagicMock(spec=ItalianLawParser)
    parser.parse.return_value = ParsedLaw(
        title="Test Law",
        law_number="199/2025",
        publication_date="30 dicembre 2025",
        articles=[
            LawArticle(
                article_number="Art. 1",
                article_number_int=1,
                title="Test Article One",
                full_text="Content of article one about taxes.",
                commi=[],
                cross_references=[],
                topics=["bonus"],
                titolo="Titolo I",
                capo="Capo I",
            ),
            LawArticle(
                article_number="Art. 2",
                article_number_int=2,
                title="Test Article Two",
                full_text="Content of article two about pensions.",
                commi=[],
                cross_references=[],
                topics=["pensioni"],
                titolo="Titolo I",
                capo="Capo I",
            ),
        ],
        allegati=[{"id": "A", "title": "Allegato Test"}],
        metadata={},
    )
    return parser


FAKE_EMBEDDING = [0.1] * 1536


# ---------------------------------------------------------------------------
# Tier 1 embedding tests
# ---------------------------------------------------------------------------


class TestTier1InlineEmbeddings:
    """Tier 1 article-level ingestion generates embeddings for items and chunks."""

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embeddings_batch")
    @patch("app.services.tiered_ingestion_service.generate_embedding")
    async def test_tier1_items_get_embeddings(
        self,
        mock_gen_embed: AsyncMock,
        mock_gen_batch: AsyncMock,
        mock_db: AsyncMock,
        tier1_classifier: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Each KnowledgeItem (parent, articles, allegati) gets an embedding."""
        mock_gen_embed.return_value = FAKE_EMBEDDING
        mock_gen_batch.return_value = [FAKE_EMBEDDING, FAKE_EMBEDDING]

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier1_classifier,
            law_parser=mock_parser,
        )

        await service.ingest(
            title="LEGGE test",
            content="Full law content",
            source="gazzetta_ufficiale",
        )

        items = [i for i in mock_db._added_items if isinstance(i, KnowledgeItem)]
        # parent + 2 articles + 1 allegato = 4 items
        assert len(items) == 4
        for item in items:
            assert item.embedding is not None, f"Item '{item.title}' missing embedding"

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embeddings_batch")
    @patch("app.services.tiered_ingestion_service.generate_embedding")
    async def test_tier1_chunks_get_embeddings(
        self,
        mock_gen_embed: AsyncMock,
        mock_gen_batch: AsyncMock,
        mock_db: AsyncMock,
        tier1_classifier: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """KnowledgeChunks created for articles get batch embeddings."""
        mock_gen_embed.return_value = FAKE_EMBEDDING
        mock_gen_batch.return_value = [FAKE_EMBEDDING, FAKE_EMBEDDING]

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier1_classifier,
            law_parser=mock_parser,
        )

        await service.ingest(
            title="LEGGE test",
            content="Full law content",
            source="gazzetta_ufficiale",
        )

        chunks = [i for i in mock_db._added_items if isinstance(i, KnowledgeChunk)]
        assert len(chunks) >= 2  # one chunk per article
        for chunk in chunks:
            assert chunk.embedding is not None, f"Chunk index {chunk.chunk_index} missing embedding"

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embeddings_batch")
    @patch("app.services.tiered_ingestion_service.generate_embedding")
    async def test_tier1_batch_called_with_chunk_texts(
        self,
        mock_gen_embed: AsyncMock,
        mock_gen_batch: AsyncMock,
        mock_db: AsyncMock,
        tier1_classifier: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """generate_embeddings_batch is called with collected chunk texts."""
        mock_gen_embed.return_value = FAKE_EMBEDDING
        mock_gen_batch.return_value = [FAKE_EMBEDDING, FAKE_EMBEDDING]

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier1_classifier,
            law_parser=mock_parser,
        )

        await service.ingest(
            title="LEGGE test",
            content="Full law content",
            source="gazzetta_ufficiale",
        )

        mock_gen_batch.assert_called_once()
        batch_texts = mock_gen_batch.call_args[0][0]
        assert len(batch_texts) == 2  # 2 articles → 2 chunk texts


# ---------------------------------------------------------------------------
# Tier 2 embedding tests
# ---------------------------------------------------------------------------


class TestTier2InlineEmbeddings:
    """Tier 2 standard-chunking ingestion generates embeddings for items."""

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embeddings_batch")
    async def test_tier2_items_get_embeddings(
        self,
        mock_gen_batch: AsyncMock,
        mock_db: AsyncMock,
        tier2_classifier: MagicMock,
    ) -> None:
        """All KnowledgeItem chunks get embeddings via batch call."""
        mock_gen_batch.return_value = [FAKE_EMBEDDING]

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier2_classifier,
        )

        await service.ingest(
            title="Circolare n. 19/E",
            content="Short content for single chunk.",
            source="agenzia_entrate",
        )

        items = [i for i in mock_db._added_items if isinstance(i, KnowledgeItem)]
        assert len(items) >= 1
        for item in items:
            assert item.embedding is not None

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embeddings_batch")
    async def test_tier2_batch_called_with_chunk_contents(
        self,
        mock_gen_batch: AsyncMock,
        mock_db: AsyncMock,
        tier2_classifier: MagicMock,
    ) -> None:
        """generate_embeddings_batch is called with all chunk contents."""
        mock_gen_batch.return_value = [FAKE_EMBEDDING, FAKE_EMBEDDING]

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier2_classifier,
        )

        # Two chunks
        long_text = "Test content. " * 400
        await service.ingest(
            title="Circolare n. 19/E",
            content=long_text,
            source="agenzia_entrate",
        )

        mock_gen_batch.assert_called_once()
        batch_texts = mock_gen_batch.call_args[0][0]
        assert len(batch_texts) >= 2


# ---------------------------------------------------------------------------
# Tier 3 embedding tests
# ---------------------------------------------------------------------------


class TestTier3InlineEmbeddings:
    """Tier 3 light-indexing ingestion generates embedding for the single item."""

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embedding")
    async def test_tier3_item_gets_embedding(
        self,
        mock_gen_embed: AsyncMock,
        mock_db: AsyncMock,
        tier3_classifier: MagicMock,
    ) -> None:
        """Single KnowledgeItem gets an embedding."""
        mock_gen_embed.return_value = FAKE_EMBEDDING

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier3_classifier,
        )

        await service.ingest(
            title="News Item",
            content="Some news content about tax changes.",
            source="news",
        )

        items = [i for i in mock_db._added_items if isinstance(i, KnowledgeItem)]
        assert len(items) == 1
        assert items[0].embedding is not None

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embedding")
    async def test_tier3_calls_generate_embedding_with_content(
        self,
        mock_gen_embed: AsyncMock,
        mock_db: AsyncMock,
        tier3_classifier: MagicMock,
    ) -> None:
        """generate_embedding is called with the item's content."""
        mock_gen_embed.return_value = FAKE_EMBEDDING

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier3_classifier,
        )

        await service.ingest(
            title="News Item",
            content="Some news content about tax changes.",
            source="news",
        )

        mock_gen_embed.assert_called_once()
        # Content is truncated to 5000 chars for tier 3
        assert "tax changes" in mock_gen_embed.call_args[0][0]


# ---------------------------------------------------------------------------
# Graceful degradation tests
# ---------------------------------------------------------------------------


class TestEmbeddingGracefulDegradation:
    """Items are still created when embedding generation fails."""

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embedding")
    async def test_tier3_api_failure_still_creates_item(
        self,
        mock_gen_embed: AsyncMock,
        mock_db: AsyncMock,
        tier3_classifier: MagicMock,
    ) -> None:
        """Item is created with embedding=None when API fails."""
        mock_gen_embed.return_value = None  # API failure

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier3_classifier,
        )

        result = await service.ingest(
            title="News Item",
            content="Content.",
            source="news",
        )

        assert result.items_created == 1
        items = [i for i in mock_db._added_items if isinstance(i, KnowledgeItem)]
        assert len(items) == 1
        assert items[0].embedding is None

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embeddings_batch")
    @patch("app.services.tiered_ingestion_service.generate_embedding")
    async def test_tier1_partial_batch_failure(
        self,
        mock_gen_embed: AsyncMock,
        mock_gen_batch: AsyncMock,
        mock_db: AsyncMock,
        tier1_classifier: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Chunks with failed embeddings get None, others succeed."""
        mock_gen_embed.return_value = FAKE_EMBEDDING
        # First chunk succeeds, second fails
        mock_gen_batch.return_value = [FAKE_EMBEDDING, None]

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier1_classifier,
            law_parser=mock_parser,
        )

        result = await service.ingest(
            title="LEGGE test",
            content="Law content",
            source="gazzetta_ufficiale",
        )

        assert result.items_created >= 3
        chunks = [i for i in mock_db._added_items if isinstance(i, KnowledgeChunk)]
        assert chunks[0].embedding is not None
        assert chunks[1].embedding is None

    @pytest.mark.asyncio
    @patch("app.services.tiered_ingestion_service.generate_embeddings_batch")
    async def test_tier2_api_failure_still_creates_items(
        self,
        mock_gen_batch: AsyncMock,
        mock_db: AsyncMock,
        tier2_classifier: MagicMock,
    ) -> None:
        """Items are created with embedding=None when batch API fails."""
        mock_gen_batch.return_value = [None]

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=tier2_classifier,
        )

        result = await service.ingest(
            title="Circolare n. 19/E",
            content="Short content.",
            source="agenzia_entrate",
        )

        assert result.items_created >= 1
        items = [i for i in mock_db._added_items if isinstance(i, KnowledgeItem)]
        assert items[0].embedding is None
