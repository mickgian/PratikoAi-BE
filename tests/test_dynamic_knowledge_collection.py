"""
Test suite for Dynamic Knowledge Collection System (DKCS).
Following TDD principles - these tests are written before implementation.

This system monitors Italian regulatory sources for updates and automatically
integrates new documents into the knowledge base.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import feedparser
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.regulatory_documents import DocumentSource, FeedStatus, ProcessingStatus, RegulatoryDocument

# These imports will be created during implementation
from app.services.dynamic_knowledge_collector import (
    DocumentProcessor,
    DynamicKnowledgeCollector,
    KnowledgeIntegrator,
    RSSFeedMonitor,
)
from app.services.scheduler_service import SchedulerService


class TestRSSFeedMonitor:
    """Test RSS feed monitoring for Italian regulatory sources"""

    @pytest.mark.asyncio
    async def test_agenzia_entrate_feed_parsing(self):
        """Test parsing of Agenzia delle Entrate RSS feeds"""
        # Mock RSS feed data for Agenzia Entrate

        # Mock feedparser response
        with patch("feedparser.parse") as mock_feedparser:
            mock_feed = Mock()
            mock_feed.entries = [
                Mock(
                    title="Circolare n. 15/E del 25 luglio 2025",
                    link="https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_15E_2025.pdf",
                    description="IVA su servizi digitali - Nuove disposizioni per operatori B2B",
                    published_parsed=(2025, 7, 25, 10, 0, 0, 3, 206, 0),
                    guid="https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_15E_2025.pdf",
                ),
                Mock(
                    title="Circolare n. 14/E del 20 luglio 2025",
                    link="https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_14E_2025.pdf",
                    description="Dichiarazione dei redditi 2025 - Novità e chiarimenti",
                    published_parsed=(2025, 7, 20, 14, 30, 0, 0, 201, 0),
                    guid="https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_14E_2025.pdf",
                ),
            ]
            mock_feedparser.return_value = mock_feed

            # Test RSS feed monitor
            monitor = RSSFeedMonitor()
            results = await monitor.parse_agenzia_entrate_feed(
                "https://www.agenziaentrate.gov.it/portale/rss/circolari.xml", "circolari"
            )

            assert len(results) == 2
            assert results[0]["title"] == "Circolare n. 15/E del 25 luglio 2025"
            assert results[0]["source"] == "agenzia_entrate"
            assert results[0]["source_type"] == "circolari"
            assert (
                results[0]["url"]
                == "https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_15E_2025.pdf"
            )
            assert "IVA su servizi digitali" in results[0]["description"]
            assert results[0]["published_date"].year == 2025
            assert results[0]["published_date"].month == 7
            assert results[0]["published_date"].day == 25

    @pytest.mark.asyncio
    async def test_inps_feed_parsing(self):
        """Test parsing of INPS RSS feeds"""

        with patch("feedparser.parse") as mock_feedparser:
            mock_feed = Mock()
            mock_feed.entries = [
                Mock(
                    title="Circolare INPS n. 82 del 30 luglio 2025",
                    link="https://www.inps.it/bussola/VisualizzaDoc.aspx?sVirtualURL=/Circolari/Circolare numero 82 del 30-07-2025.htm",
                    description="Pensioni di vecchiaia - Nuovi requisiti e modalità di calcolo",
                    published_parsed=(2025, 7, 30, 16, 0, 0, 1, 211, 0),
                    guid="https://www.inps.it/bussola/VisualizzaDoc.aspx?sVirtualURL=/Circolari/Circolare numero 82 del 30-07-2025.htm",
                )
            ]
            mock_feedparser.return_value = mock_feed

            monitor = RSSFeedMonitor()
            results = await monitor.parse_inps_feed("https://www.inps.it/rss/circolari.xml")

            assert len(results) == 1
            assert results[0]["title"] == "Circolare INPS n. 82 del 30 luglio 2025"
            assert results[0]["source"] == "inps"
            assert results[0]["source_type"] == "circolari"
            assert "Pensioni di vecchiaia" in results[0]["description"]

    @pytest.mark.asyncio
    async def test_gazzetta_ufficiale_feed_parsing(self):
        """Test parsing of Gazzetta Ufficiale RSS feeds"""
        with patch("feedparser.parse") as mock_feedparser:
            mock_feed = Mock()
            mock_feed.entries = [
                Mock(
                    title="DECRETO LEGISLATIVO 28 luglio 2025, n. 156",
                    link="https://www.gazzettaufficiale.it/eli/id/2025/07/28/025G0167/sg",
                    description="Disposizioni in materia di tributi locali",
                    published_parsed=(2025, 7, 28, 8, 0, 0, 4, 209, 0),
                    guid="https://www.gazzettaufficiale.it/eli/id/2025/07/28/025G0167/sg",
                )
            ]
            mock_feedparser.return_value = mock_feed

            monitor = RSSFeedMonitor()
            results = await monitor.parse_gazzetta_ufficiale_feed(
                "https://www.gazzettaufficiale.it/rss/serie_generale.xml"
            )

            assert len(results) == 1
            assert results[0]["title"] == "DECRETO LEGISLATIVO 28 luglio 2025, n. 156"
            assert results[0]["source"] == "gazzetta_ufficiale"
            assert results[0]["source_type"] == "decreto_legislativo"
            assert "tributi locali" in results[0]["description"]

    @pytest.mark.asyncio
    async def test_new_document_detection(self, db_session: AsyncSession):
        """Test detection of new documents vs existing ones"""
        # Create existing document in database
        existing_doc = RegulatoryDocument(
            id="test-doc-1",
            source="agenzia_entrate",
            source_type="circolari",
            title="Existing Document",
            url="https://example.com/existing.pdf",
            published_date=datetime(2025, 7, 1),
            content_hash="existing_hash_123",
        )
        db_session.add(existing_doc)
        await db_session.commit()

        collector = DynamicKnowledgeCollector(db_session)

        # Test with mix of new and existing documents
        feed_items = [
            {
                "title": "Existing Document",
                "url": "https://example.com/existing.pdf",
                "description": "Already exists",
                "published_date": datetime(2025, 7, 1),
                "source": "agenzia_entrate",
                "source_type": "circolari",
            },
            {
                "title": "New Document",
                "url": "https://example.com/new.pdf",
                "description": "This is new",
                "published_date": datetime(2025, 7, 25),
                "source": "agenzia_entrate",
                "source_type": "circolari",
            },
        ]

        new_documents = await collector.filter_new_documents(feed_items)

        assert len(new_documents) == 1
        assert new_documents[0]["title"] == "New Document"
        assert new_documents[0]["url"] == "https://example.com/new.pdf"

    @pytest.mark.asyncio
    async def test_content_extraction_pdf(self):
        """Test content extraction from PDF documents"""
        # Mock PDF content
        mock_pdf_content = """
        AGENZIA DELLE ENTRATE

        Circolare n. 15/E del 25 luglio 2025

        OGGETTO: IVA su servizi digitali - Nuove disposizioni per operatori B2B

        Si comunica che a decorrere dal 1° gennaio 2026, i servizi digitali
        prestati da soggetti passivi italiani nei confronti di altri soggetti
        passivi dell'Unione Europea sono soggetti alle seguenti disposizioni:

        1. Applicazione dell'aliquota ordinaria del 22%
        2. Fatturazione elettronica obbligatoria
        3. Comunicazione trimestrale all'Agenzia delle Entrate

        Per ulteriori informazioni si rimanda alla normativa di riferimento.
        """

        with patch("app.services.document_processor.extract_pdf_content") as mock_extract:
            mock_extract.return_value = mock_pdf_content

            processor = DocumentProcessor()
            content = await processor.extract_content_from_pdf("https://example.com/test.pdf")

            assert "IVA su servizi digitali" in content
            assert "22%" in content
            assert "Fatturazione elettronica obbligatoria" in content
            assert len(content) > 100  # Ensure substantial content extracted

    @pytest.mark.asyncio
    async def test_content_extraction_html(self):
        """Test content extraction from HTML documents"""

        with patch("app.services.document_processor.extract_html_content") as mock_extract:
            mock_extract.return_value = "Circolare INPS n. 82 del 30 luglio 2025\nPensioni di vecchiaia - Nuovi requisiti\nCon la presente circolare si comunica che...\nEtà minima: 67 anni\nContributi minimi: 20 anni"

            processor = DocumentProcessor()
            content = await processor.extract_content_from_html("https://example.com/test.html")

            assert "Pensioni di vecchiaia" in content
            assert "67 anni" in content
            assert "20 anni" in content

    @pytest.mark.asyncio
    async def test_knowledge_base_update(self, db_session: AsyncSession):
        """Test updating knowledge base with new regulatory documents"""
        # Mock new document data
        document_data = {
            "title": "Circolare n. 15/E del 25 luglio 2025",
            "url": "https://example.com/circolare_15E_2025.pdf",
            "description": "IVA su servizi digitali - Nuove disposizioni",
            "content": "Contenuto completo della circolare...",
            "published_date": datetime(2025, 7, 25),
            "source": "agenzia_entrate",
            "source_type": "circolari",
            "document_number": "15/E",
            "metadata": {
                "year": 2025,
                "authority": "Agenzia delle Entrate",
                "topics": ["IVA", "servizi digitali", "B2B"],
            },
        }

        integrator = KnowledgeIntegrator(db_session)
        result = await integrator.update_knowledge_base(document_data)

        assert result["success"] is True
        assert "document_id" in result

        # Verify document was stored in regulatory_documents table
        query = select(RegulatoryDocument).where(RegulatoryDocument.url == document_data["url"])
        doc = await db_session.execute(query)
        stored_doc = doc.scalar_one_or_none()

        assert stored_doc is not None
        assert stored_doc.title == document_data["title"]
        assert stored_doc.source == document_data["source"]
        assert stored_doc.document_number == document_data["document_number"]

        # Verify document was also added to knowledge_items for FTS
        from app.models.knowledge import KnowledgeItem

        query = select(KnowledgeItem).where(KnowledgeItem.source_url == document_data["url"])
        knowledge_item = await db_session.execute(query)
        stored_item = knowledge_item.scalar_one_or_none()

        assert stored_item is not None
        assert stored_item.title == document_data["title"]
        assert stored_item.source == "regulatory_update"
        assert stored_item.category == "agenzia_entrate_circolari"

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation when new documents arrive"""
        from app.services.cache import cache_service

        # Mock cache service
        with patch.object(cache_service, "clear_cache") as mock_clear_cache:
            mock_clear_cache.return_value = 5  # 5 cache entries cleared

            # Simulate new document arrival
            integrator = KnowledgeIntegrator(None)  # No DB needed for cache test
            await integrator.invalidate_relevant_caches(topics=["IVA", "servizi digitali"], source="agenzia_entrate")

            # Verify cache invalidation was called with correct patterns

            assert mock_clear_cache.call_count >= 4

            # Check that IVA-related searches were invalidated
            call_args = [call[0][0] for call in mock_clear_cache.call_args_list]
            assert any("iva" in arg.lower() for arg in call_args)

    @pytest.mark.asyncio
    async def test_citation_tracking(self, db_session: AsyncSession):
        """Test proper citation tracking and source attribution"""
        document_data = {
            "title": "Circolare n. 15/E del 25 luglio 2025",
            "url": "https://example.com/circolare_15E_2025.pdf",
            "description": "IVA su servizi digitali",
            "content": "Contenuto della circolare",
            "published_date": datetime(2025, 7, 25),
            "source": "agenzia_entrate",
            "source_type": "circolari",
            "document_number": "15/E",
        }

        integrator = KnowledgeIntegrator(db_session)
        result = await integrator.create_citation_data(document_data)

        expected_citation = {
            "title": "Circolare n. 15/E del 25 luglio 2025",
            "source": "Agenzia delle Entrate",
            "document_type": "Circolare",
            "document_number": "15/E",
            "published_date": "25 luglio 2025",
            "url": "https://example.com/circolare_15E_2025.pdf",
            "short_citation": "Circolare AE n. 15/E/2025",
            "full_citation": "Agenzia delle Entrate, Circolare n. 15/E del 25 luglio 2025",
        }

        assert result["title"] == expected_citation["title"]
        assert result["source"] == expected_citation["source"]
        assert result["short_citation"] == expected_citation["short_citation"]
        assert result["full_citation"] == expected_citation["full_citation"]

    @pytest.mark.asyncio
    async def test_scheduled_job_execution(self):
        """Test scheduled job execution every 4 hours"""
        with patch("app.services.scheduler_service.APScheduler") as mock_scheduler:
            scheduler_service = SchedulerService()

            # Test job registration
            await scheduler_service.register_knowledge_collection_job()

            # Verify job was scheduled with correct interval
            mock_scheduler.add_job.assert_called_once()
            call_args = mock_scheduler.add_job.call_args

            assert call_args[1]["id"] == "dynamic_knowledge_collection"
            assert call_args[1]["trigger"].interval.total_seconds() == 4 * 3600  # 4 hours
            assert call_args[1]["replace_existing"] is True

    @pytest.mark.asyncio
    async def test_parallel_feed_processing(self):
        """Test concurrent processing of multiple RSS feeds"""
        feeds = {
            "agenzia_entrate_circolari": "https://www.agenziaentrate.gov.it/portale/rss/circolari.xml",
            "agenzia_entrate_risoluzioni": "https://www.agenziaentrate.gov.it/portale/rss/risoluzioni.xml",
            "inps_circolari": "https://www.inps.it/rss/circolari.xml",
            "gazzetta_ufficiale": "https://www.gazzettaufficiale.it/rss/serie_generale.xml",
        }

        # Mock successful feed parsing
        with patch("app.services.rss_feed_monitor.RSSFeedMonitor.parse_feed") as mock_parse:
            mock_parse.return_value = [{"title": "Test Document", "url": "https://example.com/test.pdf"}]

            collector = DynamicKnowledgeCollector(None)
            results = await collector.process_all_feeds_parallel(feeds)

            # Verify all feeds were processed
            assert len(results) == 4
            assert all(result["success"] for result in results)
            assert mock_parse.call_count == 4

    @pytest.mark.asyncio
    async def test_error_handling_failed_feeds(self, db_session: AsyncSession):
        """Test error handling for failed feeds or network issues"""
        # Test network timeout
        with patch("feedparser.parse") as mock_feedparser:
            mock_feedparser.side_effect = Exception("Network timeout")

            monitor = RSSFeedMonitor()

            # Should not raise exception, should return empty list
            results = await monitor.parse_feed_with_error_handling("https://invalid-url.com/feed.xml")

            assert results == []

        # Test feed status tracking
        feed_tracker = FeedStatus(
            feed_url="https://test-feed.com/rss.xml", last_checked=datetime.now(), status="error", errors=1
        )

        db_session.add(feed_tracker)
        await db_session.commit()

        # Verify error was recorded
        query = select(FeedStatus).where(FeedStatus.feed_url == "https://test-feed.com/rss.xml")
        result = await db_session.execute(query)
        stored_status = result.scalar_one()

        assert stored_status.status == "error"
        assert stored_status.errors == 1

    @pytest.mark.asyncio
    async def test_document_version_tracking(self, db_session: AsyncSession):
        """Test tracking of document versions and updates"""
        # Create initial document
        original_doc = RegulatoryDocument(
            id="test-doc-version",
            source="agenzia_entrate",
            source_type="circolari",
            title="Circolare n. 10/E del 15 luglio 2025",
            url="https://example.com/circolare_10E_2025.pdf",
            published_date=datetime(2025, 7, 15),
            content="Contenuto originale",
            content_hash=hashlib.sha256(b"Contenuto originale").hexdigest(),
            version=1,
        )
        db_session.add(original_doc)
        await db_session.commit()

        # Simulate updated document with same URL but different content
        updated_data = {
            "title": "Circolare n. 10/E del 15 luglio 2025 (Aggiornata)",
            "url": "https://example.com/circolare_10E_2025.pdf",  # Same URL
            "content": "Contenuto aggiornato con nuove informazioni",
            "published_date": datetime(2025, 7, 15),
            "source": "agenzia_entrate",
            "source_type": "circolari",
        }

        integrator = KnowledgeIntegrator(db_session)
        result = await integrator.handle_document_update(updated_data)

        assert result["action"] == "updated"
        assert result["version"] == 2

        # Verify new version was created
        query = select(RegulatoryDocument).where(
            RegulatoryDocument.url == updated_data["url"], RegulatoryDocument.version == 2
        )
        updated_doc = await db_session.execute(query)
        stored_doc = updated_doc.scalar_one_or_none()

        assert stored_doc is not None
        assert stored_doc.content == updated_data["content"]
        assert "Aggiornata" in stored_doc.title

    @pytest.mark.asyncio
    async def test_performance_with_large_feeds(self):
        """Test system performance with large feed responses (1000+ items)"""
        # Generate large feed with 1000 items
        large_feed_items = []
        for i in range(1000):
            large_feed_items.append(
                {
                    "title": f"Documento {i + 1} del 2025",
                    "url": f"https://example.com/doc_{i + 1}.pdf",
                    "description": f"Descrizione del documento {i + 1}",
                    "published_date": datetime(2025, 7, i % 31 + 1),
                    "source": "agenzia_entrate",
                    "source_type": "circolari",
                }
            )

        import time

        start_time = time.time()

        # Mock database operations to focus on processing logic
        with patch("app.services.knowledge_integrator.KnowledgeIntegrator.update_knowledge_base") as mock_update:
            mock_update.return_value = {"success": True, "document_id": "test-id"}

            collector = DynamicKnowledgeCollector(None)
            results = await collector.process_document_batch(large_feed_items)

            processing_time = time.time() - start_time

            # Should process 1000 documents within 15 minutes (900 seconds)
            assert processing_time < 900, f"Processing took {processing_time} seconds, should be < 900s"
            assert len(results) == 1000
            assert all(result.get("success", False) for result in results)

    @pytest.mark.asyncio
    async def test_feed_history_maintenance(self, db_session: AsyncSession):
        """Test maintaining feed history for 90 days"""
        # Create old feed status records
        old_date = datetime.now() - timedelta(days=95)
        recent_date = datetime.now() - timedelta(days=30)

        old_status = FeedStatus(
            feed_url="https://old-feed.com/rss.xml", last_checked=old_date, last_success=old_date, status="success"
        )

        recent_status = FeedStatus(
            feed_url="https://recent-feed.com/rss.xml",
            last_checked=recent_date,
            last_success=recent_date,
            status="success",
        )

        db_session.add_all([old_status, recent_status])
        await db_session.commit()

        # Run cleanup job
        collector = DynamicKnowledgeCollector(db_session)
        deleted_count = await collector.cleanup_old_feed_history(retention_days=90)

        assert deleted_count == 1

        # Verify only recent record remains
        query = select(FeedStatus)
        result = await db_session.execute(query)
        remaining_records = result.scalars().all()

        assert len(remaining_records) == 1
        assert remaining_records[0].feed_url == "https://recent-feed.com/rss.xml"


@pytest.fixture
async def db_session():
    """Provide a transactional database session for tests"""
    async for session in get_async_session():
        async with session.begin():
            yield session
            # Rollback will happen automatically


class TestDynamicKnowledgeCollectorIntegration:
    """Integration tests for the complete Dynamic Knowledge Collection System"""

    @pytest.mark.asyncio
    async def test_end_to_end_document_collection(self, db_session: AsyncSession):
        """Test complete end-to-end document collection process"""
        # This test verifies the entire pipeline:
        # RSS parsing -> Content extraction -> Knowledge base update -> Cache invalidation

        with (
            patch("feedparser.parse") as mock_feedparser,
            patch("app.services.document_processor.extract_pdf_content") as mock_pdf,
            patch("app.services.cache.cache_service.clear_cache") as mock_cache,
        ):
            # Mock RSS feed response
            mock_feed = Mock()
            mock_feed.entries = [
                Mock(
                    title="Circolare n. 16/E del 1 agosto 2025",
                    link="https://www.agenziaentrate.gov.it/test.pdf",
                    description="Nuove disposizioni IVA per e-commerce",
                    published_parsed=(2025, 8, 1, 9, 0, 0, 1, 213, 0),
                    guid="unique-guid-123",
                )
            ]
            mock_feedparser.return_value = mock_feed

            # Mock PDF content extraction
            mock_pdf.return_value = """
            AGENZIA DELLE ENTRATE
            Circolare n. 16/E del 1 agosto 2025

            OGGETTO: Nuove disposizioni IVA per e-commerce

            1. Premessa
            Con la presente circolare si forniscono chiarimenti...

            2. Ambito di applicazione
            Le nuove disposizioni si applicano a partire dal 1° gennaio 2026...
            """

            # Mock cache clearing
            mock_cache.return_value = 3

            # Execute end-to-end collection
            collector = DynamicKnowledgeCollector(db_session)
            results = await collector.collect_and_process_updates()

            # Verify RSS parsing was called
            mock_feedparser.assert_called()

            # Verify PDF extraction was called
            mock_pdf.assert_called_with("https://www.agenziaentrate.gov.it/test.pdf")

            # Verify cache was invalidated
            mock_cache.assert_called()

            # Verify results
            assert len(results) > 0
            assert results[0]["success"] is True
            assert "new_documents" in results[0]

            # Verify document was stored in database
            query = select(RegulatoryDocument).where(RegulatoryDocument.title.contains("Circolare n. 16/E"))
            result = await db_session.execute(query)
            stored_doc = result.scalar_one_or_none()

            assert stored_doc is not None
            assert "e-commerce" in stored_doc.title.lower()
            assert stored_doc.source == "agenzia_entrate"
            assert stored_doc.processed_at is not None

    @pytest.mark.asyncio
    async def test_system_resilience_with_failures(self, db_session: AsyncSession):
        """Test system resilience when some feeds fail but others succeed"""
        with patch("app.services.rss_feed_monitor.RSSFeedMonitor.parse_feed") as mock_parse:
            # Simulate mixed success/failure scenario
            def side_effect(feed_url, *args):
                if "agenzia_entrate" in feed_url:
                    return [{"title": "Success Document", "url": "https://success.pdf"}]
                elif "inps" in feed_url:
                    raise Exception("INPS feed temporarily unavailable")
                else:
                    return []

            mock_parse.side_effect = side_effect

            collector = DynamicKnowledgeCollector(db_session)
            results = await collector.collect_with_resilience()

            # System should continue working despite some failures
            assert len(results) > 0
            successful_feeds = [r for r in results if r.get("success")]
            failed_feeds = [r for r in results if not r.get("success")]

            assert len(successful_feeds) >= 1  # At least Agenzia Entrate succeeded
            assert len(failed_feeds) >= 1  # INPS should have failed

            # Verify error logging and status tracking
            query = select(FeedStatus).where(FeedStatus.status == "error")
            result = await db_session.execute(query)
            error_statuses = result.scalars().all()

            assert len(error_statuses) >= 1
            assert any("inps" in status.feed_url for status in error_statuses)
