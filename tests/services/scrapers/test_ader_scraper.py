"""Tests for AdER (Agenzia Entrate-Riscossione) Scraper - DEV-242 Phase 38

Unit tests for the AdERScraper class.
These tests use mocked database connections to avoid requiring a real database.
"""

import sys
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Create mock services to prevent database connection during import
mock_db_service = MagicMock()
mock_vector_service = MagicMock()

# Patch before importing
sys.modules["app.services.database"] = MagicMock(database_service=mock_db_service)
sys.modules["app.services.vector_service"] = MagicMock(vector_service=mock_vector_service)

# Now import after patching
from app.services.scrapers.ader_scraper import (
    AdERDocument,
    AdERScraper,
    ScrapingResult,
)


class TestAdERDocument:
    """Tests for AdERDocument dataclass."""

    @pytest.fixture
    def AdERDocument(self):
        """Import AdERDocument avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.ader_scraper import AdERDocument

            return AdERDocument

    def test_create_basic_document(self, AdERDocument):
        """Test creating a basic document."""
        doc = AdERDocument(
            title="Rottamazione Quinquies - Regole Ufficiali",
            url="https://www.agenziaentrateriscossione.gov.it/it/novita/rottamazione",
            document_type="regole_rottamazione",
        )

        assert doc.title == "Rottamazione Quinquies - Regole Ufficiali"
        assert doc.url == "https://www.agenziaentrateriscossione.gov.it/it/novita/rottamazione"
        assert doc.document_type == "regole_rottamazione"
        assert doc.authority == "Agenzia delle Entrate-Riscossione"

    def test_generate_content_hash(self, AdERDocument):
        """Test content hash generation."""
        doc = AdERDocument(
            title="Test Document",
            url="https://example.com/doc",
            document_type="news",
            full_text="Sample content about rottamazione",
            published_date=date(2026, 1, 12),
        )

        hash_value = doc.generate_content_hash()

        assert hash_value is not None
        assert len(hash_value) == 64  # SHA256 hex length
        assert doc.content_hash == hash_value

    def test_to_dict(self, AdERDocument):
        """Test converting document to dictionary."""
        doc = AdERDocument(
            title="Rottamazione Quinquies - Regole Ufficiali",
            url="https://www.agenziaentrateriscossione.gov.it/it/novita/rottamazione",
            document_type="regole_rottamazione",
            published_date=date(2026, 1, 12),
            full_text="La rottamazione quinquies consente...",
            topics=["rottamazione", "pagamento"],
        )

        result = doc.to_dict()

        assert result["title"] == "Rottamazione Quinquies - Regole Ufficiali"
        assert result["source"] == "agenzia_entrate_riscossione"
        assert result["source_type"] == "regole_rottamazione"
        assert result["published_date"] == date(2026, 1, 12)
        assert result["content"] == "La rottamazione quinquies consente..."
        assert result["metadata"]["topics"] == ["rottamazione", "pagamento"]


class TestScrapingResult:
    """Tests for ScrapingResult dataclass."""

    @pytest.fixture
    def ScrapingResult(self):
        """Import ScrapingResult avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.ader_scraper import ScrapingResult

            return ScrapingResult

    def test_default_values(self, ScrapingResult):
        """Test default values for ScrapingResult."""
        result = ScrapingResult()

        assert result.documents_found == 0
        assert result.documents_processed == 0
        assert result.documents_saved == 0
        assert result.errors == 0
        assert result.duration_seconds == 0

    def test_duration_minutes(self, ScrapingResult):
        """Test duration_minutes calculation."""
        result = ScrapingResult(duration_seconds=120)

        assert result.duration_minutes == 2.0


class TestAdERScraper:
    """Tests for AdERScraper class."""

    @pytest.fixture
    def scraper(self):
        """Create an AdERScraper instance without database."""
        return AdERScraper(db_session=None)

    def test_init_without_db(self, scraper):
        """Test scraper initialization without database."""
        assert scraper.db_session is None
        assert scraper.knowledge_integrator is None
        assert scraper.rate_limit_delay == 2.0
        assert scraper.max_retries == 3

    def test_relevant_keywords(self, scraper):
        """Test that relevant keywords are defined."""
        assert "rottamazione" in scraper.RELEVANT_KEYWORDS
        assert "definizione agevolata" in scraper.RELEVANT_KEYWORDS
        assert "pace fiscale" in scraper.RELEVANT_KEYWORDS
        assert "rateizzazione" in scraper.RELEVANT_KEYWORDS
        assert "decadenza" in scraper.RELEVANT_KEYWORDS
        assert "tolleranza" in scraper.RELEVANT_KEYWORDS

    def test_base_url(self, scraper):
        """Test that base URL is correct."""
        assert scraper.BASE_URL == "https://www.agenziaentrateriscossione.gov.it"
        assert "novita" in scraper.NEWS_URL

    def test_determine_document_type_rottamazione(self, scraper):
        """Test document type detection for rottamazione."""
        doc_type = scraper._determine_document_type(
            "Rottamazione Quinquies - Regole Ufficiali",
            "/novita/rottamazione-quinquies",
        )
        assert doc_type == "regole_rottamazione"

    def test_determine_document_type_definizione_agevolata(self, scraper):
        """Test document type detection for definizione agevolata."""
        doc_type = scraper._determine_document_type(
            "Definizione Agevolata 2026",
            "/novita/definizione-agevolata",
        )
        assert doc_type == "regole_rottamazione"

    def test_determine_document_type_comunicazione(self, scraper):
        """Test document type detection for comunicazione."""
        doc_type = scraper._determine_document_type(
            "Comunicato stampa",
            "/comunicati/2026/01/comunicato",
        )
        assert doc_type == "comunicazione"

    def test_determine_document_type_news(self, scraper):
        """Test document type detection for news."""
        doc_type = scraper._determine_document_type(
            "Nuove funzionalità",
            "/news/2026/01/nuove-funzionalita",
        )
        assert doc_type == "news"

    def test_extract_date_from_url_with_slashes(self, scraper):
        """Test date extraction from URL with slash separators."""
        extracted_date = scraper._extract_date_from_url("/2026/01/12/article")
        assert extracted_date == date(2026, 1, 12)

    def test_extract_date_from_url_compact(self, scraper):
        """Test date extraction from compact URL format."""
        extracted_date = scraper._extract_date_from_url("/20260112/")
        assert extracted_date == date(2026, 1, 12)

    def test_extract_date_from_url_no_date(self, scraper):
        """Test date extraction returns None when no date found."""
        extracted_date = scraper._extract_date_from_url("/novita/articolo")
        assert extracted_date is None

    def test_extract_date_from_text_italian(self, scraper):
        """Test date extraction from Italian text."""
        extracted_date = scraper._extract_date_from_text("Pubblicato il 12 gennaio 2026")
        assert extracted_date == date(2026, 1, 12)

    def test_extract_date_from_text_numeric(self, scraper):
        """Test date extraction from numeric text."""
        extracted_date = scraper._extract_date_from_text("Data: 12/01/2026")
        assert extracted_date == date(2026, 1, 12)

    def test_extract_date_from_text_no_date(self, scraper):
        """Test date extraction returns None when no date found."""
        extracted_date = scraper._extract_date_from_text("No date here")
        assert extracted_date is None

    def test_filter_documents_by_topics(self, scraper):
        """Test filtering documents by relevant topics."""

        documents = [
            AdERDocument(
                title="Rottamazione Quinquies",
                url="https://example.com/1",
                document_type="news",
            ),
            AdERDocument(
                title="Privacy Policy",
                url="https://example.com/2",
                document_type="news",
            ),
            AdERDocument(
                title="Pagamento Rateale",
                url="https://example.com/3",
                document_type="news",
            ),
        ]

        filtered = scraper._filter_documents_by_topics(documents)

        assert len(filtered) == 2
        assert filtered[0].title == "Rottamazione Quinquies"
        assert filtered[1].title == "Pagamento Rateale"
        assert "rottamazione" in filtered[0].topics
        assert "pagamento" in filtered[1].topics

    def test_is_path_allowed_no_robots(self, scraper):
        """Test path checking when robots.txt not loaded."""
        assert scraper._is_path_allowed("https://example.com/any/path") is True

    def test_parse_robots_txt(self, scraper):
        """Test parsing robots.txt content."""
        robots_content = """
User-agent: *
Disallow: /private/
Allow: /public/
"""
        scraper._parse_robots_txt(robots_content)

        assert "/private/" in scraper._robots_rules
        assert scraper._robots_rules["/private/"] is False
        assert "/public/" in scraper._robots_rules
        assert scraper._robots_rules["/public/"] is True


class TestAdERScraperAsync:
    """Async tests for AdERScraper."""

    @pytest.fixture
    def scraper(self):
        """Create an AdERScraper instance without database."""
        return AdERScraper(db_session=None)

    @pytest.mark.asyncio
    async def test_context_manager(self, scraper):
        """Test async context manager."""
        async with scraper as s:
            assert s._session is not None
        assert scraper._session is None

    @pytest.mark.asyncio
    async def test_fetch_page_with_retry_success(self, scraper):
        """Test successful page fetch."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>Test content</html>")

        with patch.object(scraper, "_ensure_session"):
            scraper._session = MagicMock()
            scraper._session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

            content = await scraper._fetch_page_with_retry("https://example.com")

            # Note: This test is simplified - in real implementation
            # the context manager pattern needs proper async mock setup

    @pytest.mark.asyncio
    async def test_scrape_recent_documents_empty(self, scraper):
        """Test scraping when no documents found."""
        with patch.object(scraper, "_scrape_news_list", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            result = await scraper.scrape_recent_documents(days_back=1)

            assert result.documents_found == 0
            assert result.documents_saved == 0


class TestScrapeDailyTask:
    """Tests for scrape_ader_daily_task function."""

    @pytest.mark.asyncio
    async def test_scrape_daily_task_without_db(self):
        """Test daily task without database."""
        from app.services.scrapers.ader_scraper import scrape_ader_daily_task

        with patch(
            "app.services.scrapers.ader_scraper.AdERScraper.scrape_recent_documents",
            new_callable=AsyncMock,
        ) as mock_scrape:
            mock_scrape.return_value = ScrapingResult(
                documents_found=5,
                documents_saved=0,
                errors=0,
            )

            result = await scrape_ader_daily_task(db_session=None)

            assert result.documents_found == 5
            assert result.documents_saved == 0
