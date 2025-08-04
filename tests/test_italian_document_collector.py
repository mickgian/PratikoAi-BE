"""Tests for Italian document collector service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.services.italian_document_collector import (
    ItalianDocumentCollector,
    collect_italian_documents_task,
    ITALIAN_RSS_FEEDS,
    TAX_KEYWORDS
)
from app.models.italian_data import ItalianOfficialDocument, DocumentCategory


class TestItalianDocumentCollector:
    """Test suite for Italian document collector."""

    @pytest.fixture
    def collector(self):
        """Create a collector instance."""
        return ItalianDocumentCollector()

    @pytest.fixture
    def mock_feed_entry(self):
        """Create a mock RSS feed entry."""
        return {
            'title': 'Circolare n. 1/E del 15 gennaio 2024 - Nuove disposizioni IVA',
            'link': 'https://www.agenziaentrate.gov.it/portale/documents/20143/5000414/Circolare+1E_2024.pdf',
            'summary': 'La presente circolare fornisce chiarimenti sulle nuove disposizioni in materia di IVA.',
            'published': 'Mon, 15 Jan 2024 10:00:00 GMT',
            'pubDate': 'Mon, 15 Jan 2024 10:00:00 GMT'
        }

    @pytest.fixture
    def mock_feedparser_result(self, mock_feed_entry):
        """Create a mock feedparser result."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feed.entries = [mock_feed_entry]
        return mock_feed

    def test_init(self, collector):
        """Test collector initialization."""
        assert collector.session is not None
        assert collector.logger is not None
        assert collector.session.headers['User-Agent'] == 'PratikoAI-DocumentCollector/1.0 (Tax Professional Knowledge System)'

    def test_rss_feeds_configuration(self):
        """Test RSS feeds configuration is complete."""
        assert 'agenzia_entrate' in ITALIAN_RSS_FEEDS
        assert 'mef' in ITALIAN_RSS_FEEDS
        assert 'inps' in ITALIAN_RSS_FEEDS
        assert 'gazzetta_ufficiale' in ITALIAN_RSS_FEEDS
        
        # Check Agenzia Entrate feeds
        ae_feeds = ITALIAN_RSS_FEEDS['agenzia_entrate']['feeds']
        assert 'circolari' in ae_feeds
        assert 'risoluzioni' in ae_feeds
        assert 'provvedimenti' in ae_feeds
        
        # Check URLs are well-formed
        for source_config in ITALIAN_RSS_FEEDS.values():
            for feed_url in source_config['feeds'].values():
                assert feed_url.startswith(('http://', 'https://'))

    def test_tax_keywords_configuration(self):
        """Test tax keywords configuration."""
        assert 'iva' in TAX_KEYWORDS
        assert 'irpef' in TAX_KEYWORDS
        assert 'ires' in TAX_KEYWORDS
        
        # Check keywords are comprehensive
        assert len(TAX_KEYWORDS['iva']) >= 3
        assert 'imposta valore aggiunto' in TAX_KEYWORDS['iva']

    def test_generate_document_id(self, collector):
        """Test document ID generation."""
        authority = "Agenzia delle Entrate"
        title = "Circolare n. 1/E del 15 gennaio 2024"
        link = "https://www.agenziaentrate.gov.it/test.pdf"
        
        doc_id = collector._generate_document_id(authority, title, link)
        
        assert doc_id.startswith("agenzia_delle_entrate_")
        assert len(doc_id) == len("agenzia_delle_entrate_") + 12  # authority + 12 char hash
        
        # Same inputs should generate same ID
        doc_id2 = collector._generate_document_id(authority, title, link)
        assert doc_id == doc_id2

    def test_generate_content_hash(self, collector):
        """Test content hash generation."""
        title = "Test Title"
        summary = "Test Summary"
        link = "https://example.com/test"
        
        hash1 = collector._generate_content_hash(title, summary, link)
        hash2 = collector._generate_content_hash(title, summary, link)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
        
        # Different content should generate different hash
        hash3 = collector._generate_content_hash("Different Title", summary, link)
        assert hash1 != hash3

    def test_parse_date_success(self, collector):
        """Test successful date parsing."""
        # RFC 2822 format (RSS standard)
        date_str = "Mon, 15 Jan 2024 10:00:00 GMT"
        parsed_date = collector._parse_date(date_str)
        
        assert parsed_date is not None
        assert parsed_date.year == 2024
        assert parsed_date.month == 1
        assert parsed_date.day == 15

    def test_parse_date_italian_format(self, collector):
        """Test Italian date format parsing."""
        date_str = "15/01/2024"
        parsed_date = collector._parse_date(date_str)
        
        assert parsed_date is not None
        assert parsed_date.year == 2024
        assert parsed_date.month == 1
        assert parsed_date.day == 15

    def test_parse_date_failure(self, collector):
        """Test date parsing failure."""
        invalid_date = "invalid date string"
        parsed_date = collector._parse_date(invalid_date)
        
        assert parsed_date is None

    def test_classify_document_category_by_feed_type(self, collector):
        """Test document classification by feed type."""
        # Test feed type mapping
        assert collector._classify_document_category("", "", "circolari") == DocumentCategory.CIRCOLARE
        assert collector._classify_document_category("", "", "risoluzioni") == DocumentCategory.RISOLUZIONE
        assert collector._classify_document_category("", "", "provvedimenti") == DocumentCategory.PROVVEDIMENTO
        assert collector._classify_document_category("", "", "messaggi") == DocumentCategory.MESSAGGIO

    def test_classify_document_category_by_content(self, collector):
        """Test document classification by content."""
        # Test content-based classification
        title_circolare = "Circolare n. 1/E - Chiarimenti su IVA"
        assert collector._classify_document_category(title_circolare, "", "altro") == DocumentCategory.CIRCOLARE
        
        title_risoluzione = "Risoluzione n. 5/E - Risposta a quesito"
        assert collector._classify_document_category(title_risoluzione, "", "altro") == DocumentCategory.RISOLUZIONE
        
        title_decreto = "Decreto del Ministro - Nuove disposizioni"
        assert collector._classify_document_category(title_decreto, "", "altro") == DocumentCategory.DECRETO

    def test_extract_tax_types(self, collector):
        """Test tax type extraction."""
        # Test IVA detection
        title_iva = "Circolare IVA - Nuove disposizioni imposta valore aggiunto"
        content_iva = "La presente circolare tratta di fatturazione elettronica"
        tax_types = collector._extract_tax_types(title_iva, content_iva)
        
        assert 'iva' in tax_types
        
        # Test IRPEF detection
        title_irpef = "Disposizioni IRPEF per reddito persone fisiche"
        tax_types = collector._extract_tax_types(title_irpef, "")
        
        assert 'irpef' in tax_types
        
        # Test multiple tax types
        title_multi = "Disposizioni IVA e IRES per società"
        tax_types = collector._extract_tax_types(title_multi, "")
        
        assert 'iva' in tax_types
        assert 'ires' in tax_types

    def test_extract_keywords(self, collector):
        """Test keyword extraction."""
        title = "Circolare imposta dichiarazione versamento"
        content = "Sono previste sanzioni per mancato adempimento"
        
        keywords = collector._extract_keywords(title, content)
        
        assert 'imposta' in keywords
        assert 'dichiarazione' in keywords
        assert 'versamento' in keywords
        assert 'sanzione' in keywords
        assert len(keywords) <= 20  # Limit check

    @patch('feedparser.parse')
    async def test_process_rss_feed_success(self, mock_feedparser, collector, mock_feedparser_result):
        """Test successful RSS feed processing."""
        mock_feedparser.return_value = mock_feedparser_result
        
        with patch.object(collector, '_process_rss_entry', new_callable=AsyncMock) as mock_process_entry:
            mock_process_entry.return_value = Mock(id=1)  # Mock document
            
            result = await collector._process_rss_feed(
                "https://test.xml",
                "Test Authority", 
                "test_feed"
            )
            
            assert result['documents_found'] == 1
            assert result['new_documents'] == 1
            assert len(result['errors']) == 0
            mock_process_entry.assert_called_once()

    @patch('feedparser.parse')
    async def test_process_rss_feed_empty(self, mock_feedparser, collector):
        """Test RSS feed processing with no entries."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feed.entries = []
        mock_feedparser.return_value = mock_feed
        
        result = await collector._process_rss_feed(
            "https://test.xml",
            "Test Authority",
            "test_feed"
        )
        
        assert result['documents_found'] == 0
        assert result['new_documents'] == 0

    @patch('feedparser.parse')
    async def test_process_rss_feed_with_errors(self, mock_feedparser, collector):
        """Test RSS feed processing with parse errors."""
        mock_feed = Mock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Parse error")
        mock_feed.entries = []
        mock_feedparser.return_value = mock_feed
        
        result = await collector._process_rss_feed(
            "https://test.xml",
            "Test Authority",
            "test_feed"
        )
        
        assert len(result['errors']) == 1
        assert "RSS feed parsing error" in result['errors'][0]

    @patch('app.services.database.database_service.get_session')
    async def test_process_rss_entry_new_document(self, mock_get_session, collector, mock_feed_entry):
        """Test processing new RSS entry."""
        # Mock database session
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Mock no existing document found
        mock_session.exec.return_value.first.return_value = None
        
        # Mock document creation
        mock_doc = Mock()
        mock_doc.id = 1
        mock_session.refresh = AsyncMock()
        
        result = await collector._process_rss_entry(
            mock_feed_entry,
            "Agenzia delle Entrate",
            "circolari",
            "https://test-feed.xml"
        )
        
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch('app.services.database.database_service.get_session')
    async def test_process_rss_entry_duplicate_document(self, mock_get_session, collector, mock_feed_entry):
        """Test processing duplicate RSS entry."""
        # Mock database session
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Mock existing document found
        existing_doc = Mock()
        mock_session.exec.return_value.first.return_value = existing_doc
        
        result = await collector._process_rss_entry(
            mock_feed_entry,
            "Agenzia delle Entrate",
            "circolari",
            "https://test-feed.xml"
        )
        
        assert result is None  # Should return None for duplicates
        mock_session.add.assert_not_called()

    def test_process_rss_entry_missing_data(self, collector):
        """Test processing RSS entry with missing required data."""
        # Entry with missing title
        incomplete_entry = {
            'link': 'https://example.com/test',
            'summary': 'Test summary'
        }
        
        # This should handle gracefully and return None
        # Note: Would need to be async test in real implementation

    @patch('app.services.database.database_service.get_session')
    async def test_get_collection_status(self, mock_get_session, collector):
        """Test getting collection status."""
        # Mock database session
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_get_session.return_value = mock_context_manager
        
        # Mock document results
        mock_docs = [
            Mock(processing_status='pending', publication_date=datetime.utcnow()),
            Mock(processing_status='completed', publication_date=datetime.utcnow()),
            Mock(processing_status='failed', publication_date=datetime.utcnow()),
        ]
        mock_session.exec.return_value = iter(mock_docs)
        
        status = await collector.get_collection_status()
        
        assert 'total_documents' in status
        assert 'authorities' in status
        assert 'processing_status' in status

    @patch('app.services.cache_service.cache_service')
    async def test_invalidate_cache_for_updates(self, mock_cache_service, collector):
        """Test cache invalidation."""
        mock_cache_service.delete_pattern = AsyncMock()
        
        await collector.invalidate_cache_for_updates()
        
        # Verify cache patterns were deleted
        assert mock_cache_service.delete_pattern.call_count >= 4
        call_args = [call[0][0] for call in mock_cache_service.delete_pattern.call_args_list]
        assert "italian_knowledge:*" in call_args
        assert "italian_search:*" in call_args

    @patch('app.services.italian_document_collector.italian_document_collector')
    async def test_collect_italian_documents_task(self, mock_collector):
        """Test the scheduled collection task."""
        # Mock collector results
        mock_results = {
            'new_documents': 5,
            'errors': []
        }
        mock_collector.collect_all_documents = AsyncMock(return_value=mock_results)
        mock_collector.invalidate_cache_for_updates = AsyncMock()
        
        await collect_italian_documents_task()
        
        mock_collector.collect_all_documents.assert_called_once()
        mock_collector.invalidate_cache_for_updates.assert_called_once()

    @patch('app.services.italian_document_collector.italian_document_collector')
    async def test_collect_italian_documents_task_no_new_docs(self, mock_collector):
        """Test scheduled task with no new documents."""
        # Mock collector results with no new documents
        mock_results = {
            'new_documents': 0,
            'errors': []
        }
        mock_collector.collect_all_documents = AsyncMock(return_value=mock_results)
        mock_collector.invalidate_cache_for_updates = AsyncMock()
        
        await collect_italian_documents_task()
        
        mock_collector.collect_all_documents.assert_called_once()
        # Should not invalidate cache if no new documents
        mock_collector.invalidate_cache_for_updates.assert_not_called()

    @patch('requests.Session.get')
    async def test_fetch_document_content_success(self, mock_get, collector):
        """Test successful document content fetching."""
        # Mock HTML response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'<html><body><p>Test content</p></body></html>'
        mock_get.return_value = mock_response
        
        content = await collector._fetch_document_content("https://example.com/doc.html")
        
        assert content is not None
        assert "Test content" in content
        assert "<html>" not in content  # HTML tags should be stripped

    @patch('requests.Session.get')
    async def test_fetch_document_content_failure(self, mock_get, collector):
        """Test document content fetching failure."""
        mock_get.side_effect = Exception("Network error")
        
        content = await collector._fetch_document_content("https://example.com/doc.html")
        
        assert content is None

    @patch('requests.Session.get')
    async def test_fetch_document_content_large_document(self, mock_get, collector):
        """Test document content fetching with size limit."""
        # Create large content (over 50KB)
        large_content = "x" * 60000
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = f'<html><body><p>{large_content}</p></body></html>'.encode()
        mock_get.return_value = mock_response
        
        content = await collector._fetch_document_content("https://example.com/large-doc.html")
        
        assert content is not None
        assert len(content) <= 50000 + len("... [content truncated]")
        assert content.endswith("... [content truncated]")


class TestIntegration:
    """Integration tests for document collection."""

    @pytest.mark.slow
    @patch('feedparser.parse')
    @patch('app.services.database.database_service.get_session')
    async def test_full_collection_workflow(self, mock_get_session, mock_feedparser):
        """Test complete document collection workflow."""
        # This would be a more comprehensive integration test
        # Testing the full flow from RSS parsing to database storage
        pass

    @pytest.mark.slow  
    async def test_real_rss_feed_parsing(self):
        """Test parsing actual RSS feeds (if accessible)."""
        # This test would validate against real RSS feeds
        # Should be marked as slow and possibly skipped in CI
        pass