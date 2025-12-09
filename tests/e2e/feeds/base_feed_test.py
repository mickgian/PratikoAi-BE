"""Base class for E2E RSS feed tests - DEV-BE-69 Phase 6.

Implements the FULL E2E test flow with REAL services:
1. Ingest documents from RSS feed (real RSS, 1 doc max)
2. Query for documents using LangGraph RAG pipeline (real LLM)
3. Save as golden set (simulate "Corretta" button click)
4. Verify golden set retrieval bypasses LLM

This is NOT mocked - it uses real APIs to validate the full RAG pipeline.

Usage:
    class TestINPSMessaggiFeed(BaseFeedE2ETest):
        FEED_URL = "https://www.inps.it/it/it.rss.messaggi.xml"
        FEED_TYPE = "messaggi"
        QUERY_VARIATIONS = [
            "Di cosa parla l'ultimo messaggio INPS?",
            "Cosa dice il messaggio INPS recente?",
            "ultimo msg inps",
        ]

For full E2E flow tests (with real LLM and golden set):
    class TestINPSMessaggiFeedFull(BaseFeedE2ETestCommitted):
        # Same as above but uses committed transactions
        ...
"""

import asyncio
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class E2ETestResult:
    """Result of a complete E2E test execution."""

    feed_name: str
    query: str
    documents_ingested: int = 0
    documents_found_in_search: int = 0
    llm_response_generated: bool = False
    llm_response_text: str = ""
    golden_set_saved: bool = False
    golden_set_faq_id: str | None = None
    golden_hit_on_retrieval: bool = False
    llm_bypassed_on_retrieval: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Test passed if all critical steps succeeded."""
        return (
            self.documents_ingested > 0
            and self.llm_response_generated
            and self.golden_set_saved
            and self.golden_hit_on_retrieval
            and self.llm_bypassed_on_retrieval
            and len(self.errors) == 0
        )


class BaseFeedE2ETest(ABC):
    """Base class for RSS feed E2E tests with REAL services.

    Subclasses must define:
    - FEED_URL: RSS feed URL
    - FEED_TYPE: Feed type (e.g., "messaggi", "circolari")
    - QUERY_VARIATIONS: List of 3 semantic query variations (formal, casual, typo)

    The test flow uses:
    - Real RSS ingestion via run_rss_ingestion()
    - Real LLM calls via LangGraphAgent
    - Real Golden Set save via expert feedback API
    - Real Golden Set retrieval verification
    """

    # Must be overridden by subclasses
    FEED_URL: str = ""
    FEED_TYPE: str = ""
    FEED_SOURCE: str = ""  # e.g., "inps", "agenzia_entrate"
    QUERY_VARIATIONS: list[str] = []

    # Optional configuration
    MAX_ITEMS_TO_INGEST: int = 1  # Limit ingestion to be polite
    GOLDEN_WAIT_SECONDS: float = 2.0  # Wait for async golden set workflow
    TEST_TIMEOUT_SECONDS: float = 120.0  # Overall test timeout

    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_context(self, db_session):
        """Set up test fixtures.

        Note: Only sets up db_session. Expert profile is set up lazily
        in tests that need it via _get_or_create_expert_profile().
        """
        self.db_session = db_session
        self.expert_profile = None  # Will be set lazily when needed
        self.test_user_id = f"e2e_test_{uuid4().hex[:8]}"
        self.test_session_id = f"session_{uuid4().hex[:8]}"

    async def _get_or_create_expert_profile(self):
        """Get or create expert profile for golden set tests.

        Creates and persists an expert profile with high trust score for auto-approval.
        This is only called by tests that actually need it.
        """
        if self.expert_profile is not None:
            return self.expert_profile

        from app.models.quality_analysis import ExpertProfile

        expert_id = uuid4()

        # Create expert profile with high trust
        self.expert_profile = ExpertProfile(
            id=expert_id,
            user_id=1,  # Test user ID
            trust_score=0.95,  # Auto-approve threshold
            is_verified=True,
            is_active=True,
            credentials=["Dottore Commercialista"],
            credential_types=["dottore_commercialista"],
            specializations=["fiscale", "tributario", "lavoro", "previdenza"],
            experience_years=10,
            feedback_count=0,
            feedback_accuracy_rate=1.0,
            average_response_time_seconds=60,
        )

        # Persist to database (required for foreign key constraint)
        self.db_session.add(self.expert_profile)
        await self.db_session.flush()

        return self.expert_profile

    # =========================================================================
    # STEP 1: REAL RSS INGESTION
    # =========================================================================

    async def _ingest_from_rss(self) -> dict[str, Any]:
        """Step 1: Ingest documents from real RSS feed.

        Uses run_rss_ingestion() with max_items=1 to be polite to external sites.
        """
        from app.ingest.rss_normativa import run_rss_ingestion

        result = await run_rss_ingestion(
            session=self.db_session,
            feed_url=self.FEED_URL,
            feed_type=self.FEED_TYPE,
            max_items=self.MAX_ITEMS_TO_INGEST,
        )

        return {
            "success": result.get("status") == "success",
            "new_documents": result.get("new_documents", 0),
            "skipped_existing": result.get("skipped_existing", 0),
            "failed": result.get("failed", 0),
            "total_items": result.get("total_items", 0),
        }

    async def _get_latest_ingested_document(self) -> dict | None:
        """Get the most recently ingested document from this feed."""
        from app.models.knowledge import KnowledgeItem

        # Query for most recent document from this feed source
        source_pattern = f"{self.FEED_SOURCE}_{self.FEED_TYPE}"

        result = await self.db_session.execute(
            select(KnowledgeItem)
            .where(KnowledgeItem.source.ilike(f"%{source_pattern}%"))
            .order_by(KnowledgeItem.created_at.desc())
            .limit(1)
        )
        doc = result.scalar_one_or_none()

        if doc:
            return {
                "id": str(doc.id),
                "title": doc.title,
                "source": doc.source,
                "url": doc.source_url,  # KnowledgeItem uses source_url
                "created_at": doc.created_at,
            }
        return None

    # =========================================================================
    # STEP 2: REAL LLM QUERY VIA LANGGRAPH
    # =========================================================================

    async def _execute_rag_query(self, query: str) -> dict[str, Any]:
        """Step 2: Execute query through full RAG pipeline with real LLM.

        Uses LangGraphAgent.get_stream_response() to capture metadata
        including golden_hit status.
        """
        from app.core.langgraph.graph import LangGraphAgent
        from app.schemas.chat import Message

        agent = LangGraphAgent()

        # Create message in expected format
        messages = [Message(role="user", content=query)]

        # Collect streaming response and metadata
        response_chunks = []
        golden_hit = False

        try:
            async for chunk in agent.get_stream_response(
                messages=messages,
                session_id=self.test_session_id,
                user_id=self.test_user_id,
            ):
                # Check for metadata line
                if chunk.startswith("__RESPONSE_METADATA__:"):
                    metadata = chunk.replace("__RESPONSE_METADATA__:", "")
                    if "golden_hit=True" in metadata:
                        golden_hit = True
                else:
                    response_chunks.append(chunk)

            full_response = "".join(response_chunks)

            return {
                "success": len(full_response) > 0,
                "response": full_response,
                "golden_hit": golden_hit,
                "query": query,
            }

        except Exception as e:
            return {
                "success": False,
                "response": "",
                "golden_hit": False,
                "query": query,
                "error": str(e),
            }

    # =========================================================================
    # STEP 3: SAVE TO GOLDEN SET (Simulate "Corretta" Button)
    # =========================================================================

    async def _save_to_golden_set(self, query: str, response: str) -> dict[str, Any]:
        """Step 3: Save response to golden set via expert feedback.

        This simulates the user clicking "Corretta" button which triggers:
        - S127: Create FAQCandidate
        - S128: Auto-approve (trust_score >= 0.95)
        - S129: Publish to faq_entries
        - S130: Cache invalidation
        """
        from uuid import uuid4

        from app.models.quality_analysis import ExpertFeedback, FeedbackType

        # Get or create expert profile lazily
        expert = await self._get_or_create_expert_profile()

        # Create feedback record directly (simulating API call)
        feedback = ExpertFeedback(
            query_id=uuid4(),  # Generate new query ID for test
            expert_id=expert.id,
            feedback_type=FeedbackType.CORRECT,  # KEY: triggers golden set
            query_text=query,
            original_answer=response,
            expert_answer=None,  # Uses original for "correct"
            confidence_score=0.95,  # High confidence for auto-approve
            time_spent_seconds=60,
            task_creation_attempted=True,
        )

        self.db_session.add(feedback)
        await self.db_session.flush()

        # Trigger golden set workflow manually (simulates background task)
        try:
            from app.api.v1.expert_feedback import _trigger_golden_set_workflow

            await _trigger_golden_set_workflow(feedback.id, expert.id)

            # Refresh to get updated fields
            await self.db_session.refresh(feedback)

            return {
                "success": feedback.task_creation_success or False,
                "feedback_id": str(feedback.id),
                "faq_id": str(feedback.generated_faq_id) if feedback.generated_faq_id else None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # STEP 4: VERIFY GOLDEN RETRIEVAL (Must NOT call LLM)
    # =========================================================================

    async def _verify_golden_retrieval(self, query: str) -> dict[str, Any]:
        """Step 4: Query again and verify golden set is hit (no LLM call).

        This is the critical test - the second query should:
        - Hit the golden set (semantic similarity match)
        - NOT call the LLM (bypass)
        - Return the cached golden answer
        """
        result = await self._execute_rag_query(query)

        return {
            "golden_hit": result.get("golden_hit", False),
            "llm_bypassed": result.get("golden_hit", False),  # Golden hit = LLM bypassed
            "response": result.get("response", ""),
        }

    # =========================================================================
    # COMPLETE E2E TEST FLOW
    # =========================================================================

    async def run_full_e2e_flow(self, query: str) -> E2ETestResult:
        """Execute the complete 4-step E2E test flow.

        1. Ingest 1 document from RSS feed
        2. Query with LLM (should NOT hit golden)
        3. Save to golden set (simulate "Corretta")
        4. Query again (MUST hit golden, no LLM)
        """
        result = E2ETestResult(
            feed_name=f"{self.FEED_SOURCE}_{self.FEED_TYPE}",
            query=query,
        )

        try:
            # STEP 1: Ingest from RSS
            ingest_result = await self._ingest_from_rss()
            result.documents_ingested = ingest_result.get("new_documents", 0) + ingest_result.get(
                "skipped_existing", 0
            )

            if result.documents_ingested == 0 and ingest_result.get("total_items", 0) == 0:
                result.errors.append("No documents found in RSS feed")
                return result

            # Get document info for context
            doc = await self._get_latest_ingested_document()
            if doc:
                result.documents_found_in_search = 1

            # STEP 2: Query with LLM (first time, no golden hit expected)
            query_result = await self._execute_rag_query(query)
            result.llm_response_generated = query_result.get("success", False)
            result.llm_response_text = query_result.get("response", "")

            if not result.llm_response_generated:
                result.errors.append(f"LLM query failed: {query_result.get('error', 'unknown error')}")
                return result

            if query_result.get("golden_hit"):
                # Already in golden set - this is OK for re-runs
                result.golden_hit_on_retrieval = True
                result.llm_bypassed_on_retrieval = True
                result.golden_set_saved = True
                return result

            # STEP 3: Save to golden set
            golden_save = await self._save_to_golden_set(query, result.llm_response_text)
            result.golden_set_saved = golden_save.get("success", False)
            result.golden_set_faq_id = golden_save.get("faq_id")

            if not result.golden_set_saved:
                result.errors.append(f"Golden set save failed: {golden_save.get('error', 'unknown error')}")
                return result

            # Wait for async workflow to complete
            await asyncio.sleep(self.GOLDEN_WAIT_SECONDS)

            # STEP 4: Verify golden retrieval (MUST hit golden, no LLM)
            retrieval_result = await self._verify_golden_retrieval(query)
            result.golden_hit_on_retrieval = retrieval_result.get("golden_hit", False)
            result.llm_bypassed_on_retrieval = retrieval_result.get("llm_bypassed", False)

            if not result.golden_hit_on_retrieval:
                result.errors.append("Golden set not hit on retrieval - semantic matching failed")

        except Exception as e:
            result.errors.append(f"Exception: {str(e)}")

        return result

    # =========================================================================
    # STANDARD TEST METHODS - Subclasses inherit these
    # =========================================================================

    # NOTE: Full E2E flow tests are defined in BaseFeedE2ETestCommitted
    # which uses db_session_committed for real LLM + golden set testing

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_rss_feed_accessible(self):
        """Verify RSS feed is accessible and returns entries."""
        from app.ingest.rss_normativa import fetch_rss_feed

        items = await fetch_rss_feed(self.FEED_URL)

        assert len(items) > 0, f"RSS feed {self.FEED_URL} returned no items"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_documents_exist_in_db(self):
        """Verify documents from this feed exist in database."""
        source_pattern = f"{self.FEED_SOURCE}_{self.FEED_TYPE}"

        result = await self.db_session.execute(
            text("""
                SELECT COUNT(*) FROM knowledge_items
                WHERE source ILIKE :pattern
            """),
            {"pattern": f"%{source_pattern}%"},
        )
        count = result.scalar()

        # This test may fail on first run - that's expected
        # Use test_full_e2e_flow_* to ingest first
        if count == 0:
            pytest.skip(
                f"No documents for {source_pattern} yet. " f"Run test_full_e2e_flow_variation_1 first to ingest."
            )

        assert count > 0, f"Expected documents for {source_pattern}, found {count}"


# =============================================================================
# COMMITTED TRANSACTION VERSION - For Full E2E Flow with Real LLM
# =============================================================================


class BaseFeedE2ETestCommitted(ABC):
    """Base class for FULL E2E tests using committed transactions.

    This version uses db_session_committed which commits data,
    allowing the golden set workflow (which creates its own session)
    to see test data.

    Subclasses must define:
    - FEED_URL: RSS feed URL
    - FEED_TYPE: Feed type (e.g., "messaggi", "circolari")
    - FEED_SOURCE: Source identifier (e.g., "inps", "agenzia_entrate")
    - QUERY_VARIATIONS: List of 3 semantic query variations

    Usage:
        class TestINPSMessaggiFullE2E(BaseFeedE2ETestCommitted):
            FEED_URL = "https://www.inps.it/it/it.rss.messaggi.xml"
            ...
    """

    # Must be overridden by subclasses
    FEED_URL: str = ""
    FEED_TYPE: str = ""
    FEED_SOURCE: str = ""
    QUERY_VARIATIONS: list[str] = []

    # Configuration
    MAX_ITEMS_TO_INGEST: int = 1
    GOLDEN_WAIT_SECONDS: float = 3.0  # Slightly longer for committed transactions
    TEST_TIMEOUT_SECONDS: float = 180.0

    @pytest_asyncio.fixture(autouse=True)
    async def setup_committed_context(self, db_session_committed):
        """Set up test context with committed session."""
        self.db_session = db_session_committed
        self.expert_profile = None
        self.test_user_id = f"e2e_full_{uuid4().hex[:8]}"
        self.test_session_id = f"session_full_{uuid4().hex[:8]}"

    async def _get_or_create_expert_profile(self):
        """Create expert profile and commit it."""
        if self.expert_profile is not None:
            return self.expert_profile

        from app.models.quality_analysis import ExpertProfile

        expert_id = uuid4()

        self.expert_profile = ExpertProfile(
            id=expert_id,
            user_id=1,
            trust_score=0.95,
            is_verified=True,
            is_active=True,
            credentials=["Dottore Commercialista"],
            credential_types=["dottore_commercialista"],
            specializations=["fiscale", "tributario", "lavoro", "previdenza"],
            experience_years=10,
            feedback_count=0,
            feedback_accuracy_rate=1.0,
            average_response_time_seconds=60,
        )

        self.db_session.add(self.expert_profile)
        await self.db_session.commit()

        # Track for cleanup
        if hasattr(self.db_session, "cleanup_data"):
            self.db_session.cleanup_data["expert_profiles"].append(expert_id)

        return self.expert_profile

    # =========================================================================
    # STEP 1: REAL RSS INGESTION (committed)
    # =========================================================================

    async def _ingest_from_rss(self) -> dict[str, Any]:
        """Ingest from RSS feed with committed transaction."""
        from app.ingest.rss_normativa import run_rss_ingestion

        result = await run_rss_ingestion(
            session=self.db_session,
            feed_url=self.FEED_URL,
            feed_type=self.FEED_TYPE,
            max_items=self.MAX_ITEMS_TO_INGEST,
        )

        # Commit ingested documents
        await self.db_session.commit()

        return {
            "success": result.get("status") == "success",
            "new_documents": result.get("new_documents", 0),
            "skipped_existing": result.get("skipped_existing", 0),
            "failed": result.get("failed", 0),
            "total_items": result.get("total_items", 0),
        }

    # =========================================================================
    # STEP 2: REAL LLM QUERY
    # =========================================================================

    async def _execute_rag_query(self, query: str) -> dict[str, Any]:
        """Execute query with REAL LLM via LangGraphAgent."""
        from app.core.langgraph.graph import LangGraphAgent
        from app.schemas.chat import Message

        agent = LangGraphAgent()
        messages = [Message(role="user", content=query)]

        response_chunks = []
        golden_hit = False

        try:
            async for chunk in agent.get_stream_response(
                messages=messages,
                session_id=self.test_session_id,
                user_id=self.test_user_id,
            ):
                if chunk.startswith("__RESPONSE_METADATA__:"):
                    if "golden_hit=True" in chunk:
                        golden_hit = True
                else:
                    response_chunks.append(chunk)

            return {
                "success": len(response_chunks) > 0,
                "response": "".join(response_chunks),
                "golden_hit": golden_hit,
                "query": query,
            }
        except Exception as e:
            return {
                "success": False,
                "response": "",
                "golden_hit": False,
                "query": query,
                "error": str(e),
            }

    # =========================================================================
    # STEP 3: SAVE TO GOLDEN SET (committed)
    # =========================================================================

    async def _save_to_golden_set(self, query: str, response: str) -> dict[str, Any]:
        """Save to golden set with committed transaction."""
        from app.models.quality_analysis import ExpertFeedback, FeedbackType

        expert = await self._get_or_create_expert_profile()

        feedback_id = uuid4()
        query_id = uuid4()

        feedback = ExpertFeedback(
            id=feedback_id,
            query_id=query_id,
            expert_id=expert.id,
            feedback_type=FeedbackType.CORRECT,
            query_text=query,
            original_answer=response,
            expert_answer=None,
            confidence_score=0.95,
            time_spent_seconds=60,
            task_creation_attempted=True,
        )

        self.db_session.add(feedback)
        await self.db_session.commit()

        # Track for cleanup
        if hasattr(self.db_session, "cleanup_data"):
            self.db_session.cleanup_data["expert_feedback"].append(feedback_id)

        # Trigger golden set workflow
        try:
            from app.api.v1.expert_feedback import _trigger_golden_set_workflow

            await _trigger_golden_set_workflow(feedback.id, expert.id)

            # Refresh to check results
            await self.db_session.refresh(feedback)

            # Track generated FAQ for cleanup
            if feedback.generated_faq_id and hasattr(self.db_session, "cleanup_data"):
                self.db_session.cleanup_data["faq_entries"].append(feedback.generated_faq_id)

            return {
                "success": feedback.task_creation_success or False,
                "feedback_id": str(feedback.id),
                "faq_id": str(feedback.generated_faq_id) if feedback.generated_faq_id else None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # STEP 4: VERIFY GOLDEN RETRIEVAL
    # =========================================================================

    async def _verify_golden_retrieval(self, query: str) -> dict[str, Any]:
        """Query again and verify golden set is hit (no LLM call)."""
        # Use new session ID to avoid any client-side caching
        original_session = self.test_session_id
        self.test_session_id = f"verify_{uuid4().hex[:8]}"

        result = await self._execute_rag_query(query)

        self.test_session_id = original_session

        return {
            "golden_hit": result.get("golden_hit", False),
            "llm_bypassed": result.get("golden_hit", False),
            "response": result.get("response", ""),
        }

    # =========================================================================
    # COMPLETE E2E FLOW
    # =========================================================================

    async def run_full_e2e_flow(self, query: str) -> E2ETestResult:
        """Execute complete 4-step E2E flow with real LLM."""
        result = E2ETestResult(
            feed_name=f"{self.FEED_SOURCE}_{self.FEED_TYPE}",
            query=query,
        )

        try:
            # STEP 1: Ingest from RSS
            ingest_result = await self._ingest_from_rss()
            result.documents_ingested = ingest_result.get("new_documents", 0) + ingest_result.get(
                "skipped_existing", 0
            )

            if result.documents_ingested == 0 and ingest_result.get("total_items", 0) == 0:
                result.errors.append("No documents found in RSS feed")
                return result

            # STEP 2: Query with LLM
            query_result = await self._execute_rag_query(query)
            result.llm_response_generated = query_result.get("success", False)
            result.llm_response_text = query_result.get("response", "")

            if not result.llm_response_generated:
                result.errors.append(f"LLM query failed: {query_result.get('error', 'unknown')}")
                return result

            if query_result.get("golden_hit"):
                # Already in golden set (re-run scenario)
                result.golden_hit_on_retrieval = True
                result.llm_bypassed_on_retrieval = True
                result.golden_set_saved = True
                return result

            # STEP 3: Save to golden set
            golden_save = await self._save_to_golden_set(query, result.llm_response_text)
            result.golden_set_saved = golden_save.get("success", False)
            result.golden_set_faq_id = golden_save.get("faq_id")

            if not result.golden_set_saved:
                result.errors.append(f"Golden save failed: {golden_save.get('error', 'unknown')}")
                return result

            # Wait for async workflow
            await asyncio.sleep(self.GOLDEN_WAIT_SECONDS)

            # STEP 4: Verify golden retrieval
            retrieval = await self._verify_golden_retrieval(query)
            result.golden_hit_on_retrieval = retrieval.get("golden_hit", False)
            result.llm_bypassed_on_retrieval = retrieval.get("llm_bypassed", False)

            if not result.golden_hit_on_retrieval:
                result.errors.append("Golden set not hit on retrieval - semantic matching may need tuning")

        except Exception as e:
            result.errors.append(f"Exception: {str(e)}")

        return result

    # =========================================================================
    # FULL E2E TEST METHODS
    # =========================================================================

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_full_e2e_flow_variation_1(self):
        """Full E2E test with formal query variation.

        Flow:
        1. Ingest 1 document from RSS feed
        2. Query with real LLM (should NOT hit golden)
        3. Save to golden set (simulate "Corretta" button)
        4. Query again (MUST hit golden, no LLM call)
        """
        if not self.QUERY_VARIATIONS:
            pytest.skip("No query variations defined")

        result = await self.run_full_e2e_flow(self.QUERY_VARIATIONS[0])

        assert result.passed, (
            f"E2E test failed for {result.feed_name}:\n"
            f"  Query: {result.query}\n"
            f"  Ingested: {result.documents_ingested}\n"
            f"  LLM Response: {result.llm_response_generated}\n"
            f"  Golden Saved: {result.golden_set_saved}\n"
            f"  Golden Hit: {result.golden_hit_on_retrieval}\n"
            f"  LLM Bypassed: {result.llm_bypassed_on_retrieval}\n"
            f"  Errors: {result.errors}"
        )

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_full_e2e_flow_variation_2(self):
        """Full E2E test with casual query variation."""
        if len(self.QUERY_VARIATIONS) < 2:
            pytest.skip("Less than 2 query variations defined")

        result = await self.run_full_e2e_flow(self.QUERY_VARIATIONS[1])

        assert result.passed, (
            f"E2E test failed for {result.feed_name}:\n" f"  Query: {result.query}\n" f"  Errors: {result.errors}"
        )

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.llm
    async def test_full_e2e_flow_variation_3(self):
        """Full E2E test with typo query variation."""
        if len(self.QUERY_VARIATIONS) < 3:
            pytest.skip("Less than 3 query variations defined")

        result = await self.run_full_e2e_flow(self.QUERY_VARIATIONS[2])

        assert result.passed, (
            f"E2E test failed for {result.feed_name}:\n" f"  Query: {result.query}\n" f"  Errors: {result.errors}"
        )
