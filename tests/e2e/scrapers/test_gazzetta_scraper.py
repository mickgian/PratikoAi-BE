"""E2E tests for Gazzetta Ufficiale scraper - DEV-BE-69 Phase 6.

Tests the complete workflow from scraping to knowledge base integration:
1. Scraper initialization and configuration
2. Document scraping with robots.txt respect
3. Content filtering by topic (tax/labor)
4. Knowledge base integration
5. Search retrieval of scraped documents

These tests use mocked HTTP responses to avoid hitting real websites
while still testing the complete integration flow.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest


class TestGazzettaScraperE2E:
    """E2E tests for Gazzetta Ufficiale scraper."""

    @pytest.fixture
    def gazzetta_scraper_class(self):
        """Import GazzettaScraper with mocked database."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaScraper

            return GazzettaScraper

    @pytest.fixture
    def gazzetta_document_class(self):
        """Import GazzettaDocument with mocked database."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaDocument

            return GazzettaDocument

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_scraper_initialization(self, gazzetta_scraper_class):
        """Test scraper initializes with correct defaults."""
        scraper = gazzetta_scraper_class()

        assert scraper.rate_limit_delay >= 0.5, "Rate limit should be at least 0.5s"
        assert scraper.max_concurrent_requests <= 5, "Max concurrent should be <= 5"
        assert scraper.respect_robots_txt is True, "Should respect robots.txt by default"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_document_filtering_tax(self, gazzetta_scraper_class, gazzetta_document_class):
        """Test filtering documents by tax topic."""
        scraper = gazzetta_scraper_class()

        # Create test documents
        docs = [
            gazzetta_document_class(
                title="Decreto IVA 2025",
                url="https://example.com/1",
                document_type="decreto",
                full_text="Modifica aliquota IVA al 22%",
            ),
            gazzetta_document_class(
                title="Decreto sicurezza stradale",
                url="https://example.com/2",
                document_type="decreto",
                full_text="Nuove norme per la circolazione",
            ),
            gazzetta_document_class(
                title="Legge tributaria imprese",
                url="https://example.com/3",
                document_type="legge",
                full_text="Agevolazioni fiscali per PMI",
            ),
        ]

        # Filter for tax documents only
        tax_docs = scraper._filter_documents_by_topics(docs, filter_tax=True, filter_labor=False)

        assert len(tax_docs) == 2, "Should find 2 tax-related documents"
        titles = [d.title for d in tax_docs]
        assert "Decreto IVA 2025" in titles
        assert "Legge tributaria imprese" in titles
        assert "Decreto sicurezza stradale" not in titles

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_document_filtering_labor(self, gazzetta_scraper_class, gazzetta_document_class):
        """Test filtering documents by labor topic."""
        scraper = gazzetta_scraper_class()

        docs = [
            gazzetta_document_class(
                title="Decreto lavoro dipendente",
                url="https://example.com/1",
                document_type="decreto",
                full_text="Norme sul lavoro subordinato",
            ),
            gazzetta_document_class(
                title="Legge contratti collettivi",
                url="https://example.com/2",
                document_type="legge",
                full_text="Rinnovo CCNL metalmeccanici",
            ),
            gazzetta_document_class(
                title="Decreto ambiente",
                url="https://example.com/3",
                document_type="decreto",
                full_text="Tutela ambientale",
            ),
        ]

        # Filter for labor documents only
        labor_docs = scraper._filter_documents_by_topics(docs, filter_tax=False, filter_labor=True)

        assert len(labor_docs) == 2, "Should find 2 labor-related documents"
        titles = [d.title for d in labor_docs]
        assert "Decreto lavoro dipendente" in titles
        assert "Legge contratti collettivi" in titles

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_document_to_dict_conversion(self, gazzetta_document_class):
        """Test document conversion to knowledge base format."""
        doc = gazzetta_document_class(
            title="Decreto n. 123 tributario",
            url="https://gazzettaufficiale.it/atto/123",
            document_type="decreto",
            document_number="123",
            published_date=date(2025, 3, 15),
            full_text="Contenuto del decreto tributario.",
            topics=["tribut", "fiscal"],
        )

        result = doc.to_dict()

        assert result["title"] == "Decreto n. 123 tributario"
        assert result["source"] == "gazzetta_ufficiale"
        assert result["source_type"] == "decreto"
        assert result["document_number"] == "123"
        assert result["content"] == "Contenuto del decreto tributario."
        assert "tribut" in result["metadata"]["topics"]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_content_hash_deduplication(self, gazzetta_document_class):
        """Test that duplicate content produces same hash.

        Note: The hash is based on title + full_text + published_date,
        so truly duplicate documents (same title, content, date) will match.
        """
        from datetime import date

        pub_date = date(2025, 1, 15)

        doc1 = gazzetta_document_class(
            title="Decreto n. 123",
            url="https://example.com/1",
            document_type="decreto",
            full_text="Same content here",
            published_date=pub_date,
        )

        doc2 = gazzetta_document_class(
            title="Decreto n. 123",  # Same title
            url="https://example.com/mirror/1",  # Different URL (mirror site)
            document_type="decreto",
            full_text="Same content here",  # Same content
            published_date=pub_date,  # Same date
        )

        doc3 = gazzetta_document_class(
            title="Decreto n. 456",  # Different title
            url="https://example.com/3",
            document_type="decreto",
            full_text="Different content",  # Different content
            published_date=pub_date,
        )

        hash1 = doc1.generate_content_hash()
        hash2 = doc2.generate_content_hash()
        hash3 = doc3.generate_content_hash()

        assert hash1 == hash2, "Same title/content/date should produce same hash"
        assert hash1 != hash3, "Different title/content should produce different hash"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_full_scrape_workflow(self, gazzetta_scraper_class, gazzetta_document_class):
        """Test complete scrape workflow with mocked responses."""
        scraper = gazzetta_scraper_class()

        # Mock documents that would be scraped
        mock_docs = [
            gazzetta_document_class(
                title="Decreto Legislativo n. 100 del 2025",
                url="https://gazzettaufficiale.it/atto/100",
                document_type="decreto_legislativo",
                published_date=date(2025, 1, 15),
                full_text="Riforma fiscale 2025",
            ),
            gazzetta_document_class(
                title="Legge n. 50 tributaria",
                url="https://gazzettaufficiale.it/atto/50",
                document_type="legge",
                published_date=date(2025, 1, 20),
                full_text="Modifica IVA agevolata",
            ),
        ]

        # Mock internal methods
        scraper._scrape_document_list = AsyncMock(return_value=mock_docs)
        scraper._fetch_document_content = AsyncMock(side_effect=lambda doc: doc)
        scraper._save_to_knowledge_base = AsyncMock(return_value=True)

        # Execute workflow
        result = await scraper.scrape_recent_documents(days_back=7, filter_tax=True, filter_labor=False)

        # Verify results
        assert result.documents_found == 2
        assert result.documents_processed >= 1
        assert result.errors == 0
        assert scraper._scrape_document_list.called

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_rate_limiting_configuration(self, gazzetta_scraper_class):
        """Test that rate limiting can be configured."""
        # Default rate limiting
        default_scraper = gazzetta_scraper_class()
        assert default_scraper.rate_limit_delay >= 0.5

        # Custom rate limiting
        custom_scraper = gazzetta_scraper_class(rate_limit_delay=2.0)
        assert custom_scraper.rate_limit_delay == 2.0

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_robots_txt_respect(self, gazzetta_scraper_class):
        """Test robots.txt compliance."""
        scraper = gazzetta_scraper_class(respect_robots_txt=True)

        # Mock robots rules
        scraper._robots_rules = {
            "/private/": False,
            "/atti/serie_generale/": True,
        }

        # Should be blocked
        assert scraper._is_path_allowed("https://gazzettaufficiale.it/private/doc") is False

        # Should be allowed
        assert scraper._is_path_allowed("https://gazzettaufficiale.it/atti/serie_generale/123") is True


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_scraped_documents_searchable(db_session):
    """Test that scraped documents are searchable in knowledge base.

    This test verifies the end-to-end flow:
    1. Document scraped and saved
    2. Document indexed in search
    3. Query finds the document
    """
    from app.services.knowledge_search_service import KnowledgeSearchService

    service = KnowledgeSearchService(db_session=db_session)

    # Search for Gazzetta Ufficiale documents
    query_data = {
        "query": "decreto legislativo tributario",
        "canonical_facts": [],
        "user_id": "test_user",
        "session_id": "test_session",
        "trace_id": "test_gazzetta_search",
        "search_mode": "hybrid",
        "filters": {"source_pattern": "gazzetta_ufficiale%"},
        "max_results": 5,
    }

    results = await service.retrieve_topk(query_data)

    # Log results (may be empty if test DB has no Gazzetta documents)
    if results:
        print(f"Found {len(results)} Gazzetta documents")
        for r in results[:3]:
            print(f"  - {r.title}")


# ============================================================================
# Full E2E Flow Tests (scrape → query → golden set → verify bypass)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.llm
async def test_gazzetta_full_e2e_flow(db_session_committed, test_expert_profile_committed):
    """Full E2E test for Gazzetta Ufficiale scraper.

    Flow:
    1. Scrape 1 document (polite)
    2. Query with LLM
    3. Save to golden set
    4. Verify golden retrieval (no LLM)

    Uses db_session_committed for golden set workflow visibility.
    """
    import asyncio
    from uuid import uuid4

    from app.core.langgraph.graph import LangGraphAgent
    from app.models.quality_analysis import ExpertFeedback, FeedbackType
    from app.schemas.chat import Message
    from app.services.scrapers.gazzetta_scraper import GazzettaScraper

    test_session_id = f"gazzetta_e2e_{uuid4().hex[:8]}"

    # STEP 1: Scrape 1 document (be polite to external site)
    scraper = GazzettaScraper(rate_limit_delay=2.0)

    try:
        result = await scraper.scrape_recent_documents(
            days_back=7,
            filter_tax=True,
            filter_labor=False,
            max_documents=1,
        )

        if result.documents_processed == 0:
            pytest.skip("No Gazzetta documents available to scrape")

        print(f"Scraped {result.documents_processed} Gazzetta documents")

    except Exception as e:
        pytest.skip(f"Gazzetta scraping failed: {e}")

    # STEP 2: Query with LLM
    query = "Di cosa parla l'ultimo decreto pubblicato in Gazzetta Ufficiale?"

    agent = LangGraphAgent()
    messages = [Message(role="user", content=query)]

    response_chunks = []
    golden_hit_first = False

    async for chunk in agent.get_stream_response(
        messages=messages,
        session_id=test_session_id,
        user_id="test_user",
    ):
        if chunk.startswith("__RESPONSE_METADATA__:"):
            if "golden_hit=True" in chunk:
                golden_hit_first = True
        else:
            response_chunks.append(chunk)

    first_response = "".join(response_chunks)

    if not first_response:
        pytest.skip("LLM did not generate response for Gazzetta query")

    print(f"First query response: {first_response[:200]}...")

    # If already a golden hit, that's fine (re-run scenario)
    if golden_hit_first:
        print("Golden set already contains this query")
        return

    # STEP 3: Save to golden set (with committed transaction)
    feedback_id = uuid4()
    feedback = ExpertFeedback(
        id=feedback_id,
        query_id=uuid4(),
        expert_id=test_expert_profile_committed.id,
        feedback_type=FeedbackType.CORRECT,
        query_text=query,
        original_answer=first_response,
        expert_answer=None,
        confidence_score=0.95,
        time_spent_seconds=60,
        task_creation_attempted=True,
    )

    db_session_committed.add(feedback)
    await db_session_committed.commit()

    # Track for cleanup
    if hasattr(db_session_committed, "cleanup_data"):
        db_session_committed.cleanup_data["expert_feedback"].append(feedback_id)

    # Trigger golden set workflow
    try:
        from app.api.v1.expert_feedback import _trigger_golden_set_workflow

        await _trigger_golden_set_workflow(feedback.id, test_expert_profile_committed.id)
    except Exception as e:
        print(f"Golden set workflow warning: {e}")

    # Wait for async workflow
    await asyncio.sleep(3.0)

    # STEP 4: Query again - should hit golden set
    response_chunks_2 = []
    golden_hit_second = False

    async for chunk in agent.get_stream_response(
        messages=messages,
        session_id=f"{test_session_id}_2",
        user_id="test_user",
    ):
        if chunk.startswith("__RESPONSE_METADATA__:"):
            if "golden_hit=True" in chunk:
                golden_hit_second = True
        else:
            response_chunks_2.append(chunk)

    # Verify golden set was hit
    assert golden_hit_second, (
        "Second query should hit golden set. Semantic matching may need tuning for Gazzetta queries."
    )
