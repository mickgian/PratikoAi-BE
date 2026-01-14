"""Unit tests for TieredIngestionService (ADR-023).

Tests tiered document ingestion with mocked database operations.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.document_classifier import (
    ClassificationResult,
    DocumentClassifier,
    DocumentTier,
    ParsingStrategy,
)
from app.services.italian_law_parser import ItalianLawParser, LawArticle, ParsedLaw
from app.services.tiered_ingestion_service import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    IngestionResult,
    TieredIngestionService,
)

# Sample law text for testing
SAMPLE_LAW_TEXT = """Art. 1 - Test Article

1. Test content for article 1.

Art. 2 - Another Article

1. Test content for article 2.
"""


class TestTieredIngestionServiceInit:
    """Tests for service initialization."""

    def test_init_with_defaults(self) -> None:
        """Service initializes with default classifier and parser."""
        mock_db = MagicMock()
        service = TieredIngestionService(db_session=mock_db)

        assert service._db == mock_db
        assert isinstance(service._classifier, DocumentClassifier)
        assert isinstance(service._law_parser, ItalianLawParser)

    def test_init_with_custom_components(self) -> None:
        """Service accepts custom classifier and parser."""
        mock_db = MagicMock()
        mock_classifier = MagicMock(spec=DocumentClassifier)
        mock_parser = MagicMock(spec=ItalianLawParser)

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=mock_classifier,
            law_parser=mock_parser,
        )

        assert service._classifier == mock_classifier
        assert service._law_parser == mock_parser


class TestTieredIngestionServiceChunking:
    """Tests for text chunking functionality."""

    @pytest.fixture
    def service(self) -> TieredIngestionService:
        mock_db = MagicMock()
        return TieredIngestionService(db_session=mock_db)

    def test_chunk_empty_text(self, service: TieredIngestionService) -> None:
        """Empty text returns empty list."""
        chunks = service._chunk_text("")
        assert chunks == []

    def test_chunk_short_text(self, service: TieredIngestionService) -> None:
        """Short text returns single chunk."""
        text = "Short text."
        chunks = service._chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_long_text(self, service: TieredIngestionService) -> None:
        """Long text is split into multiple chunks."""
        text = "Word " * 500  # ~2500 chars
        chunks = service._chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) > 1

    def test_chunk_respects_sentence_boundaries(self, service: TieredIngestionService) -> None:
        """Chunking tries to break at sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = service._chunk_text(text, chunk_size=40, overlap=5)
        # Check that chunks don't split mid-sentence when possible
        for chunk in chunks:
            # Chunks should typically end at sentence boundaries
            assert chunk.endswith(".") or chunk == chunks[-1]

    def test_chunk_respects_paragraph_boundaries(self, service: TieredIngestionService) -> None:
        """Chunking prefers paragraph boundaries."""
        text = "Para 1.\n\nPara 2.\n\nPara 3.\n\nPara 4."
        chunks = service._chunk_text(text, chunk_size=25, overlap=5)
        assert len(chunks) > 1


class TestTieredIngestionServiceDateParsing:
    """Tests for date parsing functionality."""

    @pytest.fixture
    def service(self) -> TieredIngestionService:
        mock_db = MagicMock()
        return TieredIngestionService(db_session=mock_db)

    def test_parse_date_string(self, service: TieredIngestionService) -> None:
        """Parses date string in YYYY-MM-DD format."""
        result = service._parse_date("2025-12-30")
        assert result == date(2025, 12, 30)

    def test_parse_date_object(self, service: TieredIngestionService) -> None:
        """Returns date object as-is."""
        d = date(2025, 12, 30)
        result = service._parse_date(d)
        assert result == d

    def test_parse_date_none(self, service: TieredIngestionService) -> None:
        """Returns None for None input."""
        result = service._parse_date(None)
        assert result is None

    def test_parse_date_invalid(self, service: TieredIngestionService) -> None:
        """Returns None for invalid date string."""
        result = service._parse_date("invalid")
        assert result is None


class TestTieredIngestionServiceTier1:
    """Tests for Tier 1 (CRITICAL) article-level ingestion."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock async database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def mock_classifier(self) -> MagicMock:
        """Create mock classifier returning Tier 1."""
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
    def mock_parser(self) -> MagicMock:
        """Create mock law parser."""
        parser = MagicMock(spec=ItalianLawParser)
        parser.parse.return_value = ParsedLaw(
            title="Test Law",
            law_number="199/2025",
            publication_date="30 dicembre 2025",
            articles=[
                LawArticle(
                    article_number="Art. 1",
                    article_number_int=1,
                    title="Test Article",
                    full_text="Article content",
                    commi=[],
                    cross_references=[],
                    topics=["bonus"],
                    titolo="Titolo I",
                    capo="Capo I",
                ),
            ],
            allegati=[{"id": "A", "title": "Test"}],
            metadata={},
        )
        return parser

    @pytest.mark.asyncio
    async def test_tier1_creates_parent_document(
        self,
        mock_db: AsyncMock,
        mock_classifier: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Tier 1 ingestion creates a parent document."""
        # Track added items
        added_items = []
        mock_db.add = lambda item: added_items.append(item)

        # Simulate ID assignment on flush
        async def assign_ids():
            for i, item in enumerate(added_items):
                if item.id is None:
                    item.id = i + 1

        mock_db.flush = AsyncMock(side_effect=assign_ids)

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=mock_classifier,
            law_parser=mock_parser,
        )

        result = await service.ingest(
            title="LEGGE 30 dicembre 2025, n. 199",
            content=SAMPLE_LAW_TEXT,
            source="gazzetta_ufficiale",
        )

        # Should create parent + 1 article + 1 allegato
        assert result.items_created == 3
        assert result.tier == DocumentTier.CRITICAL
        assert result.parsing_strategy == ParsingStrategy.ARTICLE_LEVEL
        assert result.articles_parsed == 1

    @pytest.mark.asyncio
    async def test_tier1_combines_topics(
        self,
        mock_db: AsyncMock,
        mock_classifier: MagicMock,
        mock_parser: MagicMock,
    ) -> None:
        """Tier 1 combines document and article topics."""
        added_items = []
        mock_db.add = lambda item: added_items.append(item)

        async def assign_ids():
            for i, item in enumerate(added_items):
                if item.id is None:
                    item.id = i + 1

        mock_db.flush = AsyncMock(side_effect=assign_ids)

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=mock_classifier,
            law_parser=mock_parser,
        )

        result = await service.ingest(
            title="Test Law",
            content=SAMPLE_LAW_TEXT,
            source="test",
        )

        # Topics should include both document-level (irpef) and article-level (bonus)
        assert "irpef" in result.topics_detected
        assert "bonus" in result.topics_detected


class TestTieredIngestionServiceTier2:
    """Tests for Tier 2 (IMPORTANT) standard chunking."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def mock_classifier(self) -> MagicMock:
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

    @pytest.mark.asyncio
    async def test_tier2_creates_chunks(
        self,
        mock_db: AsyncMock,
        mock_classifier: MagicMock,
    ) -> None:
        """Tier 2 ingestion creates multiple chunks."""
        added_items = []
        mock_db.add = lambda item: added_items.append(item)

        async def assign_ids():
            for i, item in enumerate(added_items):
                if item.id is None:
                    item.id = i + 1

        mock_db.flush = AsyncMock(side_effect=assign_ids)

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=mock_classifier,
        )

        # Create text that will result in multiple chunks
        long_text = "Test content. " * 200  # ~2800 chars

        result = await service.ingest(
            title="Circolare n. 19/E",
            content=long_text,
            source="agenzia_entrate",
        )

        assert result.tier == DocumentTier.IMPORTANT
        assert result.parsing_strategy == ParsingStrategy.STANDARD_CHUNKING
        assert result.items_created >= 1
        assert result.articles_parsed == 0

    @pytest.mark.asyncio
    async def test_tier2_preserves_topics(
        self,
        mock_db: AsyncMock,
        mock_classifier: MagicMock,
    ) -> None:
        """Tier 2 ingestion preserves detected topics."""
        added_items = []
        mock_db.add = lambda item: added_items.append(item)

        async def assign_ids():
            for i, item in enumerate(added_items):
                if item.id is None:
                    item.id = i + 1

        mock_db.flush = AsyncMock(side_effect=assign_ids)

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=mock_classifier,
        )

        result = await service.ingest(
            title="Circolare n. 19/E",
            content="IVA content",
            source="agenzia_entrate",
        )

        assert "iva" in result.topics_detected


class TestTieredIngestionServiceTier3:
    """Tests for Tier 3 (REFERENCE) light indexing."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def mock_classifier(self) -> MagicMock:
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

    @pytest.mark.asyncio
    async def test_tier3_creates_single_item(
        self,
        mock_db: AsyncMock,
        mock_classifier: MagicMock,
    ) -> None:
        """Tier 3 ingestion creates a single item."""
        added_items = []
        mock_db.add = lambda item: added_items.append(item)

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=mock_classifier,
        )

        result = await service.ingest(
            title="News Item",
            content="Some news content",
            source="news",
        )

        assert result.tier == DocumentTier.REFERENCE
        assert result.parsing_strategy == ParsingStrategy.LIGHT_INDEXING
        assert result.items_created == 1

    @pytest.mark.asyncio
    async def test_tier3_truncates_content(
        self,
        mock_db: AsyncMock,
        mock_classifier: MagicMock,
    ) -> None:
        """Tier 3 ingestion truncates long content."""
        added_items = []
        mock_db.add = lambda item: added_items.append(item)

        service = TieredIngestionService(
            db_session=mock_db,
            classifier=mock_classifier,
        )

        # Create very long content
        long_content = "X" * 10000

        await service.ingest(
            title="News Item",
            content=long_content,
            source="news",
        )

        # Check the added item has truncated content
        assert len(added_items) == 1
        assert len(added_items[0].content) <= 5000


class TestIngestionResultDataclass:
    """Tests for IngestionResult dataclass."""

    def test_ingestion_result_attributes(self) -> None:
        """IngestionResult has all required attributes."""
        result = IngestionResult(
            document_id=123,
            tier=1,
            items_created=10,
            articles_parsed=5,
            topics_detected=["irpef", "iva"],
            parsing_strategy="article_level",
        )

        assert result.document_id == 123
        assert result.tier == 1
        assert result.items_created == 10
        assert result.articles_parsed == 5
        assert result.topics_detected == ["irpef", "iva"]
        assert result.parsing_strategy == "article_level"

    def test_ingestion_result_none_document_id(self) -> None:
        """IngestionResult can have None document_id."""
        result = IngestionResult(
            document_id=None,
            tier=3,
            items_created=1,
            articles_parsed=0,
            topics_detected=[],
            parsing_strategy="light_indexing",
        )

        assert result.document_id is None
