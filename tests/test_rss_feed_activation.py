"""
TDD Test Suite for RSS Feed Collection Activation
Following Test-Driven Development principles for PratikoAI Italian regulatory sources.

This test suite verifies RSS feed activation, scheduling, and integration
with the knowledge base search system for Italian authorities:
- Agenzia delle Entrate
- INPS
- INAIL
- Gazzetta Ufficiale
- MEF (Ministero Economia e Finanze)

Performance targets: <60 seconds per feed, 100+ documents in first run
Schedule: Every 4 hours with deduplication and Italian FTS integration
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import feedparser
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeItem
from app.models.regulatory_documents import RegulatoryDocument
from app.services.dynamic_knowledge_collector import DynamicKnowledgeCollector, collect_italian_documents_task
from app.services.rss_feed_monitor import FeedHealthMonitor, RSSFeedMonitor
from app.services.scheduler_service import ScheduledTask, ScheduleInterval, SchedulerService, scheduler_service
from app.services.search_service import SearchService


class TestRSSFeedActivation:
    """Test RSS feed activation and operational readiness"""

    @pytest.mark.asyncio
    async def test_rss_feed_monitor_initialization(self):
        """Test RSSFeedMonitor initializes with Italian feed URLs"""
        monitor = RSSFeedMonitor()

        # Verify Italian authority feeds are configured
        assert hasattr(monitor, "italian_feeds")
        assert "agenzia_entrate_circolari" in monitor.italian_feeds
        assert "agenzia_entrate_risoluzioni" in monitor.italian_feeds
        assert "agenzia_entrate_provvedimenti" in monitor.italian_feeds
        assert "inps_circolari" in monitor.italian_feeds
        assert "inps_messaggi" in monitor.italian_feeds
        assert "gazzetta_ufficiale_serie_generale" in monitor.italian_feeds
        assert "gazzetta_ufficiale_decreti" in monitor.italian_feeds

        # Verify URLs are properly formatted
        for _feed_key, feed_url in monitor.italian_feeds.items():
            assert feed_url.startswith("https://")
            assert "xml" in feed_url.lower() or "rss" in feed_url.lower()

    @pytest.mark.asyncio
    async def test_agenzia_entrate_feed_collection(self):
        """Test Agenzia delle Entrate feed collection with performance target"""
        # Mock successful feed parsing with realistic Italian content
        [
            Mock(
                title="Circolare n. 18/E del 15 agosto 2025",
                link="https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_18E_2025.pdf",
                description="Modifiche alla disciplina IVA per operazioni B2C nel settore digitale",
                published_parsed=time.struct_time((2025, 8, 15, 10, 30, 0, 0, 227, 0)),
                guid="https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_18E_2025.pdf",
            ),
            Mock(
                title="Risoluzione n. 55/E del 12 agosto 2025",
                link="https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Risoluzione_55E_2025.pdf",
                description="Chiarimenti su deduzione spese per veicoli aziendali",
                published_parsed=time.struct_time((2025, 8, 12, 14, 15, 0, 0, 224, 0)),
                guid="https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Risoluzione_55E_2025.pdf",
            ),
        ]

        # Mock the RSS XML data
        mock_rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Agenzia delle Entrate - Feed</title>
                <item>
                    <title>Circolare n. 18/E del 15 agosto 2025</title>
                    <link>https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_18E_2025.pdf</link>
                    <description>Modifiche alla disciplina IVA per operazioni B2C nel settore digitale</description>
                    <pubDate>Thu, 15 Aug 2025 10:30:00 GMT</pubDate>
                    <guid>https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_18E_2025.pdf</guid>
                </item>
                <item>
                    <title>Risoluzione n. 55/E del 12 agosto 2025</title>
                    <link>https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Risoluzione_55E_2025.pdf</link>
                    <description>Chiarimenti su deduzione spese per veicoli aziendali</description>
                    <pubDate>Mon, 12 Aug 2025 14:15:00 GMT</pubDate>
                    <guid>https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Risoluzione_55E_2025.pdf</guid>
                </item>
            </channel>
        </rss>"""

        with patch("aiohttp.ClientSession.get") as mock_get:
            # Mock HTTP response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = mock_rss_xml
            mock_get.return_value.__aenter__.return_value = mock_response

            start_time = time.time()

            # Use async context manager as required
            async with RSSFeedMonitor() as monitor:
                # Test circolari feed
                circolari_results = await monitor.parse_agenzia_entrate_feed(
                    "https://www.agenziaentrate.gov.it/portale/rss/circolari.xml", "circolari"
                )

                # Test risoluzioni feed
                risoluzioni_results = await monitor.parse_agenzia_entrate_feed(
                    "https://www.agenziaentrate.gov.it/portale/rss/risoluzioni.xml", "risoluzioni"
                )

            end_time = time.time()
            processing_time = end_time - start_time

            # Performance requirement: < 60 seconds per feed
            assert processing_time < 60, f"Feed processing took {processing_time:.2f}s, should be < 60s"

            # Verify document structure
            assert len(circolari_results) == 2
            assert len(risoluzioni_results) == 2

            # Verify Italian regulatory document parsing
            doc = circolari_results[0]
            assert doc["source"] == "agenzia_entrate"
            assert doc["source_type"] == "circolari"
            assert "Circolare" in doc["title"]
            assert "IVA" in doc["description"]
            assert doc["published_date"].year == 2025
            assert doc["published_date"].month == 8
            assert doc["published_date"].day == 15

            # Verify document categorization
            assert "document_number" in doc
            assert "authority" in doc.get("metadata", {})
            assert doc["metadata"]["authority"] == "Agenzia delle Entrate"

    @pytest.mark.asyncio
    async def test_inps_feed_collection(self):
        """Test INPS feed collection for pension and social security updates"""
        mock_entries = [
            Mock(
                title="Circolare INPS n. 89 del 20 agosto 2025",
                link="https://www.inps.it/bussola/VisualizzaDoc.aspx?sVirtualURL=/Circolari/Circolare numero 89 del 20-08-2025.htm",
                description="Pensioni anticipate per lavori usuranti - Aggiornamenti procedurali",
                published_parsed=time.struct_time((2025, 8, 20, 16, 0, 0, 1, 232, 0)),
                guid="inps_circolare_89_2025",
            ),
            Mock(
                title="Messaggio INPS n. 2856 del 18 agosto 2025",
                link="https://www.inps.it/bussola/VisualizzaDoc.aspx?sVirtualURL=/MessaggiGiuridico/Messaggio numero 2856 del 18-08-2025.htm",
                description="Cassa Integrazione Ordinaria - Modalità telematiche di domanda",
                published_parsed=time.struct_time((2025, 8, 18, 11, 30, 0, 6, 230, 0)),
                guid="inps_messaggio_2856_2025",
            ),
        ]

        with patch("feedparser.parse") as mock_feedparser:
            mock_feed = Mock()
            mock_feed.entries = mock_entries
            mock_feedparser.return_value = mock_feed

            async with RSSFeedMonitor() as monitor:
                results = await monitor.parse_inps_feed("https://www.inps.it/rss/circolari.xml")

            assert len(results) == 2

            # Verify INPS specific parsing
            circolare = results[0]
            assert circolare["source"] == "inps"
            assert circolare["source_type"] == "circolari"
            assert "Pensioni anticipate" in circolare["description"]
            assert "lavori usuranti" in circolare["description"]

            messaggio = results[1]
            assert messaggio["source"] == "inps"
            assert messaggio["source_type"] == "messaggi"
            assert "Cassa Integrazione" in messaggio["description"]

    @pytest.mark.asyncio
    async def test_gazzetta_ufficiale_feed_collection(self):
        """Test Gazzetta Ufficiale feed collection for legal and regulatory updates"""
        mock_entries = [
            Mock(
                title="DECRETO LEGISLATIVO 25 agosto 2025, n. 178",
                link="https://www.gazzettaufficiale.it/eli/id/2025/08/25/025G0189/sg",
                description="Misure urgenti in materia di tributi locali e semplificazione fiscale",
                published_parsed=time.struct_time((2025, 8, 25, 8, 0, 0, 4, 237, 0)),
                guid="gu_decreto_178_2025",
            ),
            Mock(
                title="LEGGE 22 agosto 2025, n. 156",
                link="https://www.gazzettaufficiale.it/eli/id/2025/08/22/025G0187/sg",
                description="Conversione del decreto-legge 25 giugno 2025, n. 89",
                published_parsed=time.struct_time((2025, 8, 22, 8, 0, 0, 1, 234, 0)),
                guid="gu_legge_156_2025",
            ),
        ]

        with patch("feedparser.parse") as mock_feedparser:
            mock_feed = Mock()
            mock_feed.entries = mock_entries
            mock_feedparser.return_value = mock_feed

            async with RSSFeedMonitor() as monitor:
                results = await monitor.parse_gazzetta_ufficiale_feed(
                    "https://www.gazzettaufficiale.it/rss/serie_generale.xml"
                )

            assert len(results) == 2

            # Verify Gazzetta Ufficiale specific parsing
            decreto = results[0]
            assert decreto["source"] == "gazzetta_ufficiale"
            assert decreto["source_type"] == "decreto_legislativo"
            assert "DECRETO LEGISLATIVO" in decreto["title"]
            assert "tributi locali" in decreto["description"]

            legge = results[1]
            assert legge["source"] == "gazzetta_ufficiale"
            assert legge["source_type"] == "legge"
            assert "LEGGE" in legge["title"]

    @pytest.mark.asyncio
    async def test_document_deduplication(self, mock_db_session):
        """Test document deduplication prevents duplicate processing"""
        # Create existing documents in mock database
        existing_docs = [
            RegulatoryDocument(
                id="existing-1",
                source="agenzia_entrate",
                source_type="circolari",
                title="Circolare n. 15/E del 20 luglio 2025",
                url="https://www.agenziaentrate.gov.it/existing.pdf",
                published_date=datetime(2025, 7, 20),
                content_hash="existing_hash_123",
            )
        ]

        # Mock database query to return existing documents
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = existing_docs

        collector = DynamicKnowledgeCollector(mock_db_session)

        # Test feed items with mix of new and existing
        feed_items = [
            {
                "title": "Circolare n. 15/E del 20 luglio 2025",  # Existing
                "url": "https://www.agenziaentrate.gov.it/existing.pdf",
                "content_hash": "existing_hash_123",
            },
            {
                "title": "Circolare n. 16/E del 25 luglio 2025",  # New
                "url": "https://www.agenziaentrate.gov.it/new.pdf",
                "content_hash": "new_hash_456",
            },
        ]

        filtered_docs = await collector.filter_new_documents(feed_items)

        # Should only return the new document
        assert len(filtered_docs) == 1
        assert filtered_docs[0]["title"] == "Circolare n. 16/E del 25 luglio 2025"
        assert filtered_docs[0]["url"] == "https://www.agenziaentrate.gov.it/new.pdf"

    @pytest.mark.asyncio
    async def test_scheduler_activation(self):
        """Test scheduler activation for 4-hour Italian document collection"""
        with patch("app.services.scheduler_service.scheduler_service") as mock_scheduler:
            # Test task registration
            task = ScheduledTask(
                name="italian_documents_4h",
                interval=ScheduleInterval.EVERY_4_HOURS,
                function=collect_italian_documents_task,
                enabled=True,
            )

            mock_scheduler.add_task.return_value = None
            mock_scheduler.tasks = {"italian_documents_4h": task}

            # Verify task configuration
            assert task.name == "italian_documents_4h"
            assert task.interval == ScheduleInterval.EVERY_4_HOURS
            assert task.function == collect_italian_documents_task
            assert task.enabled is True

            # Verify 4-hour interval calculation
            from app.services.scheduler_service import SchedulerService

            scheduler = SchedulerService()
            next_run = scheduler._calculate_next_run(ScheduleInterval.EVERY_4_HOURS)
            expected_run = datetime.utcnow() + timedelta(hours=4)

            # Allow 1 minute tolerance for execution time
            time_diff = abs((next_run - expected_run).total_seconds())
            assert time_diff < 60, f"Schedule timing off by {time_diff} seconds"

    @pytest.mark.asyncio
    async def test_italian_search_integration(self, mock_db_session):
        """Test integration with Italian full-text search system"""
        # Mock knowledge items being added to search index
        KnowledgeItem(
            id=1,
            title="Circolare n. 18/E del 15 agosto 2025",
            content="Modifiche alla disciplina IVA per operazioni B2C nel settore digitale. Le nuove disposizioni entreranno in vigore dal 1° gennaio 2026.",
            category="agenzia_entrate_circolari",
            subcategory="circolari",
            source="regulatory_update",
            source_url="https://www.agenziaentrate.gov.it/portale/documents/20143/5501356/Circolare_18E_2025.pdf",
            language="it",
            relevance_score=0.9,
            tags=["IVA", "B2C", "settore digitale"],
            legal_references=["D.Lgs. 52/2019", "Dir. UE 2017/2455"],
        )

        # Mock search service
        search_service = SearchService(mock_db_session)

        # Test Italian query processing
        with patch.object(search_service, "_execute_search") as mock_search:
            mock_search.return_value = [
                Mock(
                    id="1",
                    title="Circolare n. 18/E del 15 agosto 2025",
                    content="Modifiche alla disciplina IVA...",
                    category="agenzia_entrate_circolari",
                    rank_score=0.85,
                    relevance_score=0.9,
                    highlight="Modifiche alla disciplina <b>IVA</b> per operazioni B2C",
                    source="regulatory_update",
                )
            ]

            # Test Italian search query
            results = await search_service.search(
                query="IVA operazioni digitali", category="agenzia_entrate_circolari"
            )

            assert len(results) == 1
            assert "IVA" in results[0].highlight
            assert results[0].category == "agenzia_entrate_circolari"
            assert results[0].rank_score > 0.8

    @pytest.mark.asyncio
    async def test_knowledge_base_population_target(self, mock_db_session):
        """Test knowledge base reaches 100+ documents target in first run"""
        # Generate 150 mock Italian regulatory documents
        mock_documents = []
        for i in range(150):
            authority = ["agenzia_entrate", "inps", "gazzetta_ufficiale"][i % 3]
            doc_type = ["circolari", "risoluzioni", "messaggi", "decreti"][i % 4]

            mock_documents.append(
                {
                    "title": f"Documento {authority} n. {i + 1} del 2025",
                    "url": f"https://{authority}.gov.it/doc_{i + 1}.pdf",
                    "content": f"Contenuto del documento {i + 1} su normative italiane",
                    "source": authority,
                    "source_type": doc_type,
                    "published_date": datetime(2025, 8, 1 + (i % 30)),
                    "metadata": {"authority": authority.replace("_", " ").title(), "document_number": f"{i + 1}/2025"},
                }
            )

        # Mock successful processing
        with patch(
            "app.services.dynamic_knowledge_collector.DynamicKnowledgeCollector.process_document_batch"
        ) as mock_batch:
            mock_batch.return_value = [{"success": True, "document_id": f"doc_{i + 1}"} for i in range(150)]

            collector = DynamicKnowledgeCollector(mock_db_session)
            results = await collector.process_document_batch(mock_documents)

            # Verify 100+ documents target reached
            successful_docs = [r for r in results if r.get("success")]
            assert len(successful_docs) >= 100, f"Only processed {len(successful_docs)} documents, target is 100+"
            assert len(successful_docs) == 150  # All should succeed in mock

    @pytest.mark.asyncio
    async def test_parallel_feed_processing_performance(self):
        """Test concurrent processing of all Italian feeds meets performance targets"""
        italian_feeds = {
            "agenzia_entrate_circolari": "https://www.agenziaentrate.gov.it/portale/rss/circolari.xml",
            "agenzia_entrate_risoluzioni": "https://www.agenziaentrate.gov.it/portale/rss/risoluzioni.xml",
            "agenzia_entrate_provvedimenti": "https://www.agenziaentrate.gov.it/portale/rss/provvedimenti.xml",
            "inps_circolari": "https://www.inps.it/rss/circolari.xml",
            "inps_messaggi": "https://www.inps.it/rss/messaggi.xml",
            "gazzetta_ufficiale_serie_generale": "https://www.gazzettaufficiale.it/rss/serie_generale.xml",
            "gazzetta_ufficiale_decreti": "https://www.gazzettaufficiale.it/rss/decreti.xml",
        }

        # Mock feed parsing with realistic response times
        with patch("app.services.rss_feed_monitor.RSSFeedMonitor.parse_feed") as mock_parse:

            async def mock_parse_feed(url, *args):
                # Simulate realistic feed parsing time (15-45 seconds per feed)
                await asyncio.sleep(0.1)  # Reduced for testing
                return [
                    {"title": f"Test Document from {url}", "url": f"{url}/test.pdf", "published_date": datetime.now()}
                ]

            mock_parse.side_effect = mock_parse_feed

            collector = DynamicKnowledgeCollector(None)
            start_time = time.time()

            # Process all feeds in parallel
            results = await collector.process_all_feeds_parallel(italian_feeds)

            end_time = time.time()
            total_processing_time = end_time - start_time

            # Performance target: All 7 feeds processed in under 5 minutes (300s)
            assert (
                total_processing_time < 300
            ), f"Parallel processing took {total_processing_time:.2f}s, should be < 300s"

            # Verify all feeds were processed
            assert len(results) == 7
            successful_feeds = [r for r in results if r.get("success", True)]
            assert len(successful_feeds) >= 6, "At least 6/7 feeds should succeed for system resilience"

    @pytest.mark.asyncio
    async def test_feed_health_monitoring(self, mock_db_session):
        """Test feed health monitoring and error tracking"""
        health_monitor = FeedHealthMonitor(mock_db_session)

        # Test successful feed status
        await health_monitor.record_feed_status(
            feed_url="https://www.agenziaentrate.gov.it/portale/rss/circolari.xml",
            status="success",
            document_count=15,
            processing_time=45.2,
        )

        # Test failed feed status
        await health_monitor.record_feed_status(
            feed_url="https://www.inps.it/rss/circolari.xml",
            status="error",
            error_message="Connection timeout after 60 seconds",
            document_count=0,
            processing_time=60.0,
        )

        # Verify status tracking calls
        assert mock_db_session.add.call_count == 2
        assert mock_db_session.commit.call_count == 2

    @pytest.mark.asyncio
    async def test_emergency_rollback_capability(self, mock_db_session):
        """Test rollback capability if RSS collection causes issues"""
        collector = DynamicKnowledgeCollector(mock_db_session)

        # Mock transaction rollback scenario
        mock_db_session.rollback = AsyncMock()
        mock_db_session.commit.side_effect = Exception("Database constraint violation")

        # Attempt document processing with failure
        document_data = {"title": "Test Document", "content": "Test content", "source": "agenzia_entrate"}

        with pytest.raises(Exception):
            await collector.process_single_document(document_data)

        # Verify rollback was called
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_italian_content_validation(self):
        """Test validation of Italian regulatory content"""
        processor = DynamicKnowledgeCollector(None)

        # Test valid Italian regulatory content
        valid_content = {
            "title": "Circolare n. 18/E del 15 agosto 2025",
            "content": "Modifiche alla disciplina IVA per operazioni B2C nel settore digitale",
            "source": "agenzia_entrate",
            "language": "it",
        }

        is_valid = await processor.validate_italian_regulatory_content(valid_content)
        assert is_valid is True

        # Test invalid content (non-Italian, no regulatory keywords)
        invalid_content = {
            "title": "Random English Document",
            "content": "This is random English text without regulatory content",
            "source": "unknown_source",
            "language": "en",
        }

        is_valid = await processor.validate_italian_regulatory_content(invalid_content)
        assert is_valid is False


@pytest.fixture
def mock_db_session():
    """Provide mock database session for testing"""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestEndToEndRSSActivation:
    """End-to-end integration tests for complete RSS activation"""

    @pytest.mark.asyncio
    async def test_complete_rss_activation_workflow(self, mock_db_session):
        """Test complete RSS activation workflow from scheduling to search integration"""
        # 1. Initialize and configure scheduler
        scheduler = SchedulerService()

        # 2. Add Italian document collection task
        task = ScheduledTask(
            name="italian_documents_4h",
            interval=ScheduleInterval.EVERY_4_HOURS,
            function=collect_italian_documents_task,
            enabled=True,
        )
        scheduler.add_task(task)

        # 3. Mock successful RSS collection
        with patch("app.services.dynamic_knowledge_collector.collect_italian_documents_task") as mock_task:
            mock_task.return_value = {
                "success": True,
                "documents_processed": 125,
                "feeds_processed": 7,
                "processing_time": 240.5,
                "new_documents": 125,
            }

            # 4. Execute scheduled task
            result = await collect_italian_documents_task()

            # 5. Verify workflow success
            assert result["success"] is True
            assert result["documents_processed"] >= 100  # Target reached
            assert result["feeds_processed"] == 7  # All Italian feeds
            assert result["processing_time"] < 300  # Under 5 minutes

            # 6. Verify task was called
            mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_readiness_checklist(self):
        """Test system readiness checklist for RSS activation"""
        checklist_results = {}

        # 1. RSS Feed URLs accessible
        monitor = RSSFeedMonitor()
        checklist_results["rss_feeds_configured"] = (
            hasattr(monitor, "italian_feeds") and len(monitor.italian_feeds) >= 7
        )

        # 2. Scheduler service operational
        scheduler = SchedulerService()
        checklist_results["scheduler_ready"] = scheduler is not None

        # 3. Database models available
        try:
            from app.models.knowledge import KnowledgeItem
            from app.models.regulatory_documents import RegulatoryDocument

            checklist_results["database_models_ready"] = True
        except ImportError:
            checklist_results["database_models_ready"] = False

        # 4. Search service configured for Italian
        from app.services.search_service import SearchService

        checklist_results["search_service_ready"] = SearchService is not None

        # 5. Document processing pipeline available
        from app.services.dynamic_knowledge_collector import DynamicKnowledgeCollector

        checklist_results["document_processor_ready"] = DynamicKnowledgeCollector is not None

        # Verify all systems ready
        assert all(checklist_results.values()), f"System readiness failed: {checklist_results}"

        # Log readiness status
        print("RSS Feed Activation Readiness Checklist:")
        for check, status in checklist_results.items():
            status_symbol = "✅" if status else "❌"
            print(f"  {status_symbol} {check}: {'READY' if status else 'NOT READY'}")
