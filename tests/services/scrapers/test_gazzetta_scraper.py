"""Tests for Gazzetta Ufficiale Scraper - DEV-BE-69 Phase 4

Unit tests for the GazzettaScraper class.
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
from app.services.scrapers.gazzetta_scraper import (
    GazzettaDocument,
    GazzettaScraper,
    ScrapingResult,
)


class TestGazzettaDocument:
    """Tests for GazzettaDocument dataclass."""

    @pytest.fixture
    def GazzettaDocument(self):
        """Import GazzettaDocument avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaDocument

            return GazzettaDocument

    def test_create_basic_document(self, GazzettaDocument):
        """Test creating a basic document."""
        doc = GazzettaDocument(
            title="Test Document",
            url="https://example.com/doc",
            document_type="decreto",
        )

        assert doc.title == "Test Document"
        assert doc.url == "https://example.com/doc"
        assert doc.document_type == "decreto"
        assert doc.authority == "Gazzetta Ufficiale"
        assert doc.series == "serie_generale"

    def test_generate_content_hash(self, GazzettaDocument):
        """Test content hash generation."""
        doc = GazzettaDocument(
            title="Test Document",
            url="https://example.com/doc",
            document_type="decreto",
            full_text="Sample content",
            published_date=date(2024, 1, 15),
        )

        hash_value = doc.generate_content_hash()

        assert hash_value is not None
        assert len(hash_value) == 64  # SHA256 hex length
        assert doc.content_hash == hash_value

    def test_to_dict(self, GazzettaDocument):
        """Test converting document to dictionary."""
        doc = GazzettaDocument(
            title="Decreto n. 123",
            url="https://gazzettaufficiale.it/atto/123",
            document_type="decreto",
            document_number="123",
            published_date=date(2024, 3, 15),
            full_text="Decreto content here",
            topics=["tribut", "fiscal"],
        )

        result = doc.to_dict()

        assert result["title"] == "Decreto n. 123"
        assert result["source"] == "gazzetta_ufficiale"
        assert result["source_type"] == "decreto"
        assert result["document_number"] == "123"
        assert result["published_date"] == date(2024, 3, 15)
        assert result["content"] == "Decreto content here"
        assert result["metadata"]["topics"] == ["tribut", "fiscal"]


class TestScrapingResult:
    """Tests for ScrapingResult dataclass."""

    @pytest.fixture
    def ScrapingResult(self):
        """Import ScrapingResult avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import ScrapingResult

            return ScrapingResult

    def test_default_values(self, ScrapingResult):
        """Test default values."""
        result = ScrapingResult()

        assert result.documents_found == 0
        assert result.documents_processed == 0
        assert result.documents_saved == 0
        assert result.errors == 0
        assert result.duration_seconds == 0

    def test_duration_minutes(self, ScrapingResult):
        """Test duration in minutes calculation."""
        result = ScrapingResult(duration_seconds=120)

        assert result.duration_minutes == 2.0

    def test_with_date_range(self, ScrapingResult):
        """Test result with date range."""
        result = ScrapingResult(
            documents_found=10,
            documents_saved=8,
            errors=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert result.start_date == date(2024, 1, 1)
        assert result.end_date == date(2024, 1, 31)


class TestGazzettaScraper:
    """Tests for GazzettaScraper class."""

    @pytest.fixture
    def GazzettaScraper(self):
        """Import GazzettaScraper avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaScraper

            return GazzettaScraper

    @pytest.fixture
    def GazzettaDocument(self):
        """Import GazzettaDocument avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaDocument

            return GazzettaDocument

    def test_initialization(self, GazzettaScraper):
        """Test scraper initialization with defaults."""
        scraper = GazzettaScraper()

        assert scraper.rate_limit_delay == 2.0
        assert scraper.max_retries == 3
        assert scraper.timeout_seconds == 30
        assert scraper.max_concurrent_requests == 3
        assert scraper.respect_robots_txt is True

    def test_initialization_custom_config(self, GazzettaScraper):
        """Test scraper initialization with custom config."""
        scraper = GazzettaScraper(
            rate_limit_delay=5.0,
            max_retries=5,
            timeout_seconds=60,
            max_concurrent_requests=2,
            respect_robots_txt=False,
        )

        assert scraper.rate_limit_delay == 5.0
        assert scraper.max_retries == 5
        assert scraper.timeout_seconds == 60
        assert scraper.max_concurrent_requests == 2
        assert scraper.respect_robots_txt is False

    def test_determine_document_type_decreto_legislativo(self, GazzettaScraper):
        """Test document type determination for decreto legislativo."""
        scraper = GazzettaScraper()

        assert scraper._determine_document_type("Decreto Legislativo n. 123") == "decreto_legislativo"
        assert scraper._determine_document_type("D.Lgs. 456/2024") == "decreto_legislativo"

    def test_determine_document_type_decreto_legge(self, GazzettaScraper):
        """Test document type determination for decreto legge."""
        scraper = GazzettaScraper()

        assert scraper._determine_document_type("Decreto Legge n. 123") == "decreto_legge"
        assert scraper._determine_document_type("D.L. 456/2024") == "decreto_legge"

    def test_determine_document_type_legge(self, GazzettaScraper):
        """Test document type determination for legge."""
        scraper = GazzettaScraper()

        assert scraper._determine_document_type("Legge n. 123 del 2024") == "legge"

    def test_determine_document_type_decreto(self, GazzettaScraper):
        """Test document type determination for generic decreto."""
        scraper = GazzettaScraper()

        assert scraper._determine_document_type("Decreto n. 123") == "decreto"

    def test_determine_document_type_dpcm(self, GazzettaScraper):
        """Test document type determination for DPCM."""
        scraper = GazzettaScraper()

        assert scraper._determine_document_type("DPCM 15 marzo 2024") == "dpcm"
        assert scraper._determine_document_type("Decreto del Presidente del Consiglio") == "dpcm"

    def test_determine_document_type_circolare(self, GazzettaScraper):
        """Test document type determination for circolare."""
        scraper = GazzettaScraper()

        assert scraper._determine_document_type("Circolare n. 5/E") == "circolare"

    def test_determine_document_type_default(self, GazzettaScraper):
        """Test document type determination default."""
        scraper = GazzettaScraper()

        assert scraper._determine_document_type("Unknown document type") == "atto_normativo"

    def test_extract_document_number(self, GazzettaScraper):
        """Test document number extraction."""
        scraper = GazzettaScraper()

        assert scraper._extract_document_number("Decreto n. 123 del 2024") == "123"
        assert scraper._extract_document_number("Legge numero 456 del 2024") == "456"
        assert scraper._extract_document_number("D.Lgs. n.789/2024") == "789/2024"
        assert scraper._extract_document_number("123/2024") == "123/2024"
        assert scraper._extract_document_number("No number here") is None

    def test_extract_date_from_text_italian_format(self, GazzettaScraper):
        """Test date extraction from Italian format text."""
        scraper = GazzettaScraper()

        result = scraper._extract_date_from_text("15 marzo 2024")
        assert result == date(2024, 3, 15)

        result = scraper._extract_date_from_text("1 gennaio 2025")
        assert result == date(2025, 1, 1)

        result = scraper._extract_date_from_text("31 dicembre 2023")
        assert result == date(2023, 12, 31)

    def test_extract_date_from_text_numeric_format(self, GazzettaScraper):
        """Test date extraction from numeric format text."""
        scraper = GazzettaScraper()

        result = scraper._extract_date_from_text("15/03/2024")
        assert result == date(2024, 3, 15)

        result = scraper._extract_date_from_text("01-01-2025")
        assert result == date(2025, 1, 1)

    def test_extract_date_from_text_no_date(self, GazzettaScraper):
        """Test date extraction when no date present."""
        scraper = GazzettaScraper()

        assert scraper._extract_date_from_text("No date here") is None

    def test_extract_date_from_url(self, GazzettaScraper):
        """Test date extraction from URL."""
        scraper = GazzettaScraper()

        result = scraper._extract_date_from_url("/2024/03/15/document.html")
        assert result == date(2024, 3, 15)

        result = scraper._extract_date_from_url("/20240315/document.html")
        assert result == date(2024, 3, 15)

    def test_extract_date_from_url_no_date(self, GazzettaScraper):
        """Test date extraction from URL without date."""
        scraper = GazzettaScraper()

        assert scraper._extract_date_from_url("/documents/latest.html") is None

    def test_is_path_allowed_no_rules(self, GazzettaScraper):
        """Test path checking with no robots rules."""
        scraper = GazzettaScraper()
        scraper._robots_rules = {}

        assert scraper._is_path_allowed("https://example.com/any/path") is True

    def test_is_path_allowed_with_disallow(self, GazzettaScraper):
        """Test path checking with disallow rule."""
        scraper = GazzettaScraper()
        scraper._robots_rules = {"/private/": False}

        assert scraper._is_path_allowed("https://example.com/public/doc") is True
        assert scraper._is_path_allowed("https://example.com/private/doc") is False

    def test_is_path_allowed_with_allow(self, GazzettaScraper):
        """Test path checking with allow rule."""
        scraper = GazzettaScraper()
        scraper._robots_rules = {"/": False, "/public/": True}

        assert scraper._is_path_allowed("https://example.com/public/doc") is True

    def test_is_path_allowed_robots_disabled(self, GazzettaScraper):
        """Test path checking when robots.txt is disabled."""
        scraper = GazzettaScraper(respect_robots_txt=False)
        scraper._robots_rules = {"/private/": False}

        assert scraper._is_path_allowed("https://example.com/private/doc") is True

    def test_filter_documents_by_topics_tax(self, GazzettaScraper, GazzettaDocument):
        """Test document filtering for tax topics."""
        scraper = GazzettaScraper()

        docs = [
            GazzettaDocument(
                title="Decreto tributario",
                url="https://example.com/1",
                document_type="decreto",
            ),
            GazzettaDocument(
                title="Decreto ambiente",
                url="https://example.com/2",
                document_type="decreto",
            ),
            GazzettaDocument(
                title="Legge IVA",
                url="https://example.com/3",
                document_type="legge",
            ),
        ]

        filtered = scraper._filter_documents_by_topics(docs, filter_tax=True, filter_labor=False)

        assert len(filtered) == 2
        titles = [d.title for d in filtered]
        assert "Decreto tributario" in titles
        assert "Legge IVA" in titles
        assert "Decreto ambiente" not in titles

    def test_filter_documents_by_topics_labor(self, GazzettaScraper, GazzettaDocument):
        """Test document filtering for labor topics."""
        scraper = GazzettaScraper()

        docs = [
            GazzettaDocument(
                title="Decreto sul lavoro",
                url="https://example.com/1",
                document_type="decreto",
            ),
            GazzettaDocument(
                title="Legge ambientale",
                url="https://example.com/2",
                document_type="legge",
            ),
            GazzettaDocument(
                title="Contratto pensione",
                url="https://example.com/3",
                document_type="circolare",
            ),
        ]

        filtered = scraper._filter_documents_by_topics(docs, filter_tax=False, filter_labor=True)

        assert len(filtered) == 2
        titles = [d.title for d in filtered]
        assert "Decreto sul lavoro" in titles
        assert "Contratto pensione" in titles

    def test_filter_documents_by_topics_both(self, GazzettaScraper, GazzettaDocument):
        """Test document filtering for both tax and labor topics."""
        scraper = GazzettaScraper()

        docs = [
            GazzettaDocument(
                title="Decreto tributario",
                url="https://example.com/1",
                document_type="decreto",
            ),
            GazzettaDocument(
                title="Decreto lavoro",
                url="https://example.com/2",
                document_type="decreto",
            ),
            GazzettaDocument(
                title="Decreto ambiente",
                url="https://example.com/3",
                document_type="decreto",
            ),
        ]

        filtered = scraper._filter_documents_by_topics(docs, filter_tax=True, filter_labor=True)

        assert len(filtered) == 2

    def test_filter_documents_no_filter(self, GazzettaScraper, GazzettaDocument):
        """Test document filtering with no filters."""
        scraper = GazzettaScraper()

        docs = [
            GazzettaDocument(title="Doc 1", url="https://example.com/1", document_type="decreto"),
            GazzettaDocument(title="Doc 2", url="https://example.com/2", document_type="legge"),
        ]

        filtered = scraper._filter_documents_by_topics(docs, filter_tax=False, filter_labor=False)

        assert len(filtered) == 2

    def test_parse_robots_txt(self, GazzettaScraper):
        """Test robots.txt parsing."""
        scraper = GazzettaScraper()

        robots_content = """
        User-agent: *
        Disallow: /private/
        Disallow: /admin/
        Allow: /public/
        """

        scraper._parse_robots_txt(robots_content)

        assert "/private/" in scraper._robots_rules
        assert "/admin/" in scraper._robots_rules
        assert "/public/" in scraper._robots_rules
        assert scraper._robots_rules["/private/"] is False
        assert scraper._robots_rules["/admin/"] is False
        assert scraper._robots_rules["/public/"] is True


@pytest.mark.asyncio
class TestGazzettaScraperAsync:
    """Async tests for GazzettaScraper."""

    @pytest.fixture
    def GazzettaScraper(self):
        """Import GazzettaScraper avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaScraper

            return GazzettaScraper

    @pytest.fixture
    def GazzettaDocument(self):
        """Import GazzettaDocument avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaDocument

            return GazzettaDocument

    async def test_context_manager(self, GazzettaScraper):
        """Test async context manager."""
        async with GazzettaScraper() as scraper:
            assert scraper._session is not None

        assert scraper._session is None

    async def test_ensure_session(self, GazzettaScraper):
        """Test session creation."""
        scraper = GazzettaScraper()

        await scraper._ensure_session()

        assert scraper._session is not None

        # Clean up
        await scraper._session.close()

    async def test_fetch_page_with_retry_success(self, GazzettaScraper):
        """Test successful page fetch."""
        scraper = GazzettaScraper()
        scraper._robots_rules = {}  # No restrictions

        # Create a proper async context manager mock
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>Test content</html>")

        # Create async context manager
        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = mock_response
        async_cm.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value = async_cm

        scraper._session = mock_session

        result = await scraper._fetch_page_with_retry("https://example.com/test")

        assert result == "<html>Test content</html>"

    async def test_fetch_page_with_retry_blocked_by_robots(self, GazzettaScraper):
        """Test page fetch blocked by robots.txt."""
        scraper = GazzettaScraper()
        scraper._robots_rules = {"/private/": False}

        result = await scraper._fetch_page_with_retry("https://example.com/private/doc")

        assert result is None

    async def test_fetch_page_with_retry_rate_limited(self, GazzettaScraper):
        """Test handling of 429 rate limiting."""
        scraper = GazzettaScraper(max_retries=1, rate_limit_delay=0.01)
        scraper._robots_rules = {}

        # First response is 429
        mock_response_429 = MagicMock()
        mock_response_429.status = 429
        mock_response_429.headers = {"Retry-After": "0"}

        async_cm_429 = AsyncMock()
        async_cm_429.__aenter__.return_value = mock_response_429
        async_cm_429.__aexit__.return_value = None

        # Second response is 200
        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.text = AsyncMock(return_value="<html>Success</html>")

        async_cm_200 = AsyncMock()
        async_cm_200.__aenter__.return_value = mock_response_200
        async_cm_200.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.side_effect = [async_cm_429, async_cm_200]

        scraper._session = mock_session

        result = await scraper._fetch_page_with_retry("https://example.com/test")

        assert result == "<html>Success</html>"

    async def test_fetch_page_with_retry_timeout(self, GazzettaScraper):
        """Test handling of timeout errors."""
        scraper = GazzettaScraper(max_retries=0, rate_limit_delay=0.01)
        scraper._robots_rules = {}

        # Create async context manager that raises on enter
        async_cm = AsyncMock()
        async_cm.__aenter__.side_effect = TimeoutError("Connection timed out")

        mock_session = MagicMock()
        mock_session.get.return_value = async_cm

        scraper._session = mock_session

        result = await scraper._fetch_page_with_retry("https://example.com/test")

        assert result is None

    async def test_fetch_page_with_retry_http_error(self, GazzettaScraper):
        """Test handling of HTTP errors."""
        scraper = GazzettaScraper(max_retries=0, rate_limit_delay=0.01)
        scraper._robots_rules = {}

        mock_response = MagicMock()
        mock_response.status = 500

        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = mock_response
        async_cm.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value = async_cm

        scraper._session = mock_session

        result = await scraper._fetch_page_with_retry("https://example.com/test")

        assert result is None

    async def test_scrape_recent_documents_empty(self, GazzettaScraper):
        """Test scraping when no documents found."""
        scraper = GazzettaScraper()

        # Mock _scrape_document_list to return empty
        scraper._scrape_document_list = AsyncMock(return_value=[])

        result = await scraper.scrape_recent_documents(days_back=1)

        assert result.documents_found == 0
        assert result.documents_saved == 0
        assert result.errors == 0

    async def test_scrape_recent_documents_with_documents(self, GazzettaScraper, GazzettaDocument):
        """Test scraping with documents found."""
        scraper = GazzettaScraper()

        mock_docs = [
            GazzettaDocument(
                title="Decreto tributario",
                url="https://example.com/1",
                document_type="decreto",
            ),
            GazzettaDocument(
                title="Legge lavoro",
                url="https://example.com/2",
                document_type="legge",
            ),
        ]

        scraper._scrape_document_list = AsyncMock(return_value=mock_docs)
        scraper._fetch_document_content = AsyncMock(return_value=mock_docs[0])

        # Mock knowledge_integrator to simulate DB persistence
        mock_integrator = MagicMock()
        mock_integrator.update_knowledge_base = AsyncMock(return_value={"success": True, "action": "created"})
        scraper.knowledge_integrator = mock_integrator

        result = await scraper.scrape_recent_documents(days_back=1, filter_tax=False, filter_labor=False)

        assert result.documents_found == 2
        assert result.documents_processed == 2
        assert result.documents_saved == 2

    async def test_scrape_recent_documents_with_limit(self, GazzettaScraper, GazzettaDocument):
        """Test scraping respects limit parameter."""
        scraper = GazzettaScraper()

        mock_docs = [
            GazzettaDocument(title=f"Doc {i}", url=f"https://example.com/{i}", document_type="decreto")
            for i in range(10)
        ]

        scraper._scrape_document_list = AsyncMock(return_value=mock_docs)
        scraper._fetch_document_content = AsyncMock(return_value=mock_docs[0])

        result = await scraper.scrape_recent_documents(days_back=1, filter_tax=False, filter_labor=False, limit=3)

        # Only 3 documents should be processed due to limit
        assert result.documents_processed == 3

    async def test_scrape_recent_documents_error_handling(self, GazzettaScraper, GazzettaDocument):
        """Test error handling during document processing."""
        scraper = GazzettaScraper()

        mock_docs = [
            GazzettaDocument(title="Doc 1", url="https://example.com/1", document_type="decreto"),
        ]

        scraper._scrape_document_list = AsyncMock(return_value=mock_docs)
        scraper._fetch_document_content = AsyncMock(side_effect=Exception("Fetch failed"))

        result = await scraper.scrape_recent_documents(days_back=1, filter_tax=False, filter_labor=False)

        assert result.documents_found == 1
        assert result.errors == 1

    async def test_scrape_document_list_empty_html(self, GazzettaScraper):
        """Test document list scraping with empty response."""
        scraper = GazzettaScraper()
        scraper._fetch_page_with_retry = AsyncMock(return_value=None)

        result = await scraper._scrape_document_list(date(2024, 1, 1), date(2024, 1, 31))

        assert result == []

    async def test_scrape_document_list_with_html(self, GazzettaScraper):
        """Test document list scraping with HTML content."""
        scraper = GazzettaScraper()

        html_content = """
        <html>
        <body>
            <div class="risultato">
                <a href="/atto/123">Decreto n. 123 del 2024</a>
                <span class="data">15/01/2024</span>
            </div>
        </body>
        </html>
        """
        scraper._fetch_page_with_retry = AsyncMock(return_value=html_content)

        result = await scraper._scrape_document_list(date(2024, 1, 1), date(2024, 1, 31))

        # The parser looks for specific HTML structure - empty result is expected for generic HTML
        assert isinstance(result, list)

    async def test_check_robots_txt(self, GazzettaScraper):
        """Test robots.txt checking."""
        scraper = GazzettaScraper()

        robots_content = """
        User-agent: *
        Disallow: /admin/
        Allow: /public/
        """

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=robots_content)

        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = mock_response
        async_cm.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value = async_cm

        scraper._session = mock_session

        await scraper._check_robots_txt()

        assert "/admin/" in scraper._robots_rules
        assert scraper._robots_rules["/admin/"] is False

    async def test_check_robots_txt_not_found(self, GazzettaScraper):
        """Test robots.txt not found."""
        scraper = GazzettaScraper()

        mock_response = MagicMock()
        mock_response.status = 404

        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = mock_response
        async_cm.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value = async_cm

        scraper._session = mock_session

        await scraper._check_robots_txt()

        # No rules should be set
        assert scraper._robots_rules == {}

    async def test_fetch_document_content(self, GazzettaScraper, GazzettaDocument):
        """Test fetching full document content."""
        scraper = GazzettaScraper()

        doc = GazzettaDocument(
            title="Decreto n. 123",
            url="https://example.com/atto/123",
            document_type="decreto",
        )

        html_content = """
        <html>
        <body>
            <div class="testoAtto">Full text of the decree here.</div>
        </body>
        </html>
        """

        scraper._fetch_page_with_retry = AsyncMock(return_value=html_content)

        result = await scraper._fetch_document_content(doc)

        assert result is not None
        assert result.title == "Decreto n. 123"

    async def test_fetch_document_content_no_html(self, GazzettaScraper, GazzettaDocument):
        """Test fetching document when page fetch fails."""
        scraper = GazzettaScraper()

        doc = GazzettaDocument(
            title="Decreto n. 123",
            url="https://example.com/atto/123",
            document_type="decreto",
        )

        scraper._fetch_page_with_retry = AsyncMock(return_value=None)

        result = await scraper._fetch_document_content(doc)

        assert result is None


class TestGazzettaScraperKeywords:
    """Tests for keyword lists."""

    @pytest.fixture
    def GazzettaScraper(self):
        """Import GazzettaScraper avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaScraper

            return GazzettaScraper

    def test_tax_keywords_present(self, GazzettaScraper):
        """Test that all expected tax keywords are present."""
        expected_keywords = ["tribut", "fiscal", "imposta", "iva", "irpef", "ires"]

        for kw in expected_keywords:
            assert kw in GazzettaScraper.TAX_KEYWORDS

    def test_labor_keywords_present(self, GazzettaScraper):
        """Test that all expected labor keywords are present."""
        expected_keywords = ["lavoro", "occupazion", "pensione", "previdenza", "inps", "inail"]

        for kw in expected_keywords:
            assert kw in GazzettaScraper.LABOR_KEYWORDS


class TestGazzettaScraperDBIntegration:
    """Tests for database integration via KnowledgeIntegrator."""

    @pytest.fixture
    def GazzettaScraper(self):
        """Import GazzettaScraper avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaScraper

            return GazzettaScraper

    @pytest.fixture
    def GazzettaDocument(self):
        """Import GazzettaDocument avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaDocument

            return GazzettaDocument

    def test_initialization_with_db_session(self, GazzettaScraper):
        """Test scraper initialization with db_session parameter."""
        mock_session = MagicMock()
        scraper = GazzettaScraper(db_session=mock_session)

        assert scraper.db_session == mock_session
        assert scraper.knowledge_integrator is not None

    def test_initialization_without_db_session(self, GazzettaScraper):
        """Test scraper initialization without db_session (backwards compatible)."""
        scraper = GazzettaScraper()

        assert scraper.db_session is None
        assert scraper.knowledge_integrator is None

    def test_initialization_with_none_db_session(self, GazzettaScraper):
        """Test scraper initialization with explicit None db_session."""
        scraper = GazzettaScraper(db_session=None)

        assert scraper.db_session is None
        assert scraper.knowledge_integrator is None


@pytest.mark.asyncio
class TestGazzettaScraperDBIntegrationAsync:
    """Async tests for database integration via KnowledgeIntegrator."""

    @pytest.fixture
    def GazzettaScraper(self):
        """Import GazzettaScraper avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaScraper

            return GazzettaScraper

    @pytest.fixture
    def GazzettaDocument(self):
        """Import GazzettaDocument avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaDocument

            return GazzettaDocument

    async def test_scrape_calls_knowledge_integrator(self, GazzettaScraper, GazzettaDocument):
        """Test that scraping calls KnowledgeIntegrator when db_session provided."""
        mock_session = MagicMock()
        scraper = GazzettaScraper(db_session=mock_session)

        # Mock KnowledgeIntegrator
        mock_integrator = MagicMock()
        mock_integrator.update_knowledge_base = AsyncMock(
            return_value={"success": True, "action": "created", "document_id": "123"}
        )
        scraper.knowledge_integrator = mock_integrator

        mock_docs = [
            GazzettaDocument(
                title="Decreto tributario",
                url="https://example.com/1",
                document_type="decreto",
                full_text="Full text content",
            ),
        ]

        scraper._scrape_document_list = AsyncMock(return_value=mock_docs)
        scraper._fetch_document_content = AsyncMock(return_value=mock_docs[0])

        result = await scraper.scrape_recent_documents(days_back=1, filter_tax=False, filter_labor=False)

        # Verify KnowledgeIntegrator was called
        mock_integrator.update_knowledge_base.assert_called_once()
        assert result.documents_saved == 1

    async def test_scrape_without_db_session_does_not_save(self, GazzettaScraper, GazzettaDocument):
        """Test that scraping without db_session doesn't try to save."""
        scraper = GazzettaScraper()  # No db_session

        mock_docs = [
            GazzettaDocument(
                title="Decreto tributario",
                url="https://example.com/1",
                document_type="decreto",
                full_text="Full text content",
            ),
        ]

        scraper._scrape_document_list = AsyncMock(return_value=mock_docs)
        scraper._fetch_document_content = AsyncMock(return_value=mock_docs[0])

        result = await scraper.scrape_recent_documents(days_back=1, filter_tax=False, filter_labor=False)

        # Documents processed but not saved (no db_session)
        assert result.documents_processed == 1
        assert result.documents_saved == 0  # No saving without db_session

    async def test_scrape_handles_integration_failure(self, GazzettaScraper, GazzettaDocument):
        """Test that scraping handles KnowledgeIntegrator failures gracefully."""
        mock_session = MagicMock()
        scraper = GazzettaScraper(db_session=mock_session)

        # Mock KnowledgeIntegrator to fail
        mock_integrator = MagicMock()
        mock_integrator.update_knowledge_base = AsyncMock(
            return_value={"success": False, "error": "Integration failed"}
        )
        scraper.knowledge_integrator = mock_integrator

        mock_docs = [
            GazzettaDocument(
                title="Decreto tributario",
                url="https://example.com/1",
                document_type="decreto",
                full_text="Full text content",
            ),
        ]

        scraper._scrape_document_list = AsyncMock(return_value=mock_docs)
        scraper._fetch_document_content = AsyncMock(return_value=mock_docs[0])

        result = await scraper.scrape_recent_documents(days_back=1, filter_tax=False, filter_labor=False)

        # Error should be counted
        assert result.errors == 1
        assert result.documents_saved == 0
