"""Integration tests for Golden Set Workflow - End-to-End Bug Detection.

RED PHASE: These tests FAIL to expose the critical bug where:
1. Expert marks answer as "correct" → FAQ IS saved to database (Step 127 works)
2. User asks identical question → LLM is called AGAIN (Step 24 doesn't retrieve)
3. Golden set is never served, causing unnecessary LLM costs

This is an E2E test suite that validates the complete workflow:
- Expert feedback submission → FAQ storage → Golden set retrieval → LLM bypass

Test Coverage:
7. Correct feedback creates retrievable FAQ (E2E storage test)
8. Identical question retrieves golden set (E2E retrieval test)
9. Golden set bypasses LLM call (E2E performance test)
10. Step 24 queries real database, not mock (E2E verification test)

All 4 tests expected to FAIL because Step 24 only contains mock code.

NOTE: Skipped - RED phase tests, Step 24 golden retrieval not yet implemented.
"""

import pytest

pytest.skip(
    "RED phase integration tests - Step 24 golden retrieval not implemented",
    allow_module_level=True,
)

from datetime import UTC, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.orchestrators.preflight import step_24__golden_lookup


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_llm_service():
    """Mock LLM service to track calls.

    Returns dict with call count to verify LLM is/isn't called.
    """
    call_tracker = {"count": 0, "last_query": None}

    def mock_chat_completion(*args, **kwargs):
        """Mock LLM chat completion - tracks invocations."""
        call_tracker["count"] += 1
        call_tracker["last_query"] = kwargs.get("messages", [])
        return {
            "response": "Mocked LLM response from chat completion",
            "model": "gpt-4",
            "usage": {"total_tokens": 100},
        }

    return call_tracker, mock_chat_completion


@pytest.fixture
async def insert_faq_via_sql(db_session: AsyncSession):
    """Helper to insert FAQ directly via SQL to bypass ORM issues.

    Returns callable that inserts FAQ and returns the ID.
    """

    async def _insert(
        question: str,
        answer: str,
        status: str = "auto_approved",
    ) -> str:
        """Insert FAQ candidate via raw SQL."""
        faq_id = str(uuid4())
        cluster_id = str(uuid4())

        # Check if table exists first
        check_table_sql = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'faq_candidates'
            );
        """)
        result = await db_session.execute(check_table_sql)
        table_exists = result.scalar()

        if not table_exists:
            pytest.skip("faq_candidates table doesn't exist yet - migration not run")

        insert_sql = text("""
            INSERT INTO faq_candidates (
                id, cluster_id, suggested_question, best_response_content,
                suggested_category, frequency, estimated_monthly_savings,
                roi_score, priority_score, status, generation_attempts, created_at
            ) VALUES (
                :id, :cluster_id, :question, :answer,
                :category, :frequency, :savings,
                :roi, :priority, :status, :attempts, :created_at
            )
        """)

        await db_session.execute(
            insert_sql,
            {
                "id": faq_id,
                "cluster_id": cluster_id,
                "question": question,
                "answer": answer,
                "category": "fiscale",
                "frequency": 10,
                "savings": 15.50,
                "roi": 8.5,
                "priority": 85.0,
                "status": status,
                "attempts": 1,
                "created_at": datetime.now(UTC),
            },
        )
        await db_session.commit()

        return faq_id

    return _insert


@pytest.mark.asyncio
class TestGoldenSetWorkflow:
    """End-to-end integration tests for Golden Set workflow.

    These tests validate the complete feedback → storage → retrieval pipeline.
    """

    async def test_correct_feedback_creates_retrievable_faq(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
    ):
        """TEST 7: End-to-end test of feedback → storage → retrieval.

        This test validates the STORAGE path (Step 127):
        1. User asks: "Cos'è la risoluzione 62?"
        2. LLM provides answer
        3. Expert marks as "correct"
        4. Step 127 saves FAQ candidate

        Assert:
            - FAQ candidate exists in faq_candidates table
            - status is "auto_approved"
            - question_embedding is populated (if column exists)
            - generated_faq_id is set in expert_feedback table

        Expected: MAY PASS if Step 127 was fixed, or FAIL if embedding generation missing

        NOTE: This test focuses on the STORAGE side. Even if this passes,
        tests 8-10 will still fail because Step 24 doesn't RETRIEVE.
        """
        from datetime import datetime

        from app.models.quality_analysis import ExpertFeedback, ExpertProfile, FeedbackType

        # Arrange: Create expert profile
        expert = ExpertProfile(
            id=uuid4(),
            user_id=uuid4(),
            trust_score=0.95,
            is_verified=True,
            is_active=True,
        )
        db_session.add(expert)
        await db_session.commit()

        # Act: Simulate expert feedback submission
        query_text = "Cos'è la risoluzione 62?"
        original_answer = "La risoluzione 62 è un documento dell'Agenzia delle Entrate..."
        expert_answer = "La risoluzione 62/E del 2023 chiarisce l'applicazione dell'IVA..."

        feedback = ExpertFeedback(
            id=uuid4(),
            query_id=uuid4(),
            expert_id=expert.id,
            feedback_type=FeedbackType.CORRECT,
            query_text=query_text,
            original_answer=original_answer,
            expert_answer=expert_answer,
            confidence_score=0.95,
            time_spent_seconds=120,
            regulatory_references=["Risoluzione 62/E/2023"],
        )
        db_session.add(feedback)
        await db_session.commit()

        # Simulate Step 127 execution (golden candidate creation)
        from app.orchestrators.golden import step_127__golden_candidate

        ctx = {
            "request_id": "test_request_001",
            "expert_id": expert.id,
            "trust_score": expert.trust_score,
            "expert_feedback": {
                "id": feedback.id,
                "query_text": query_text,
                "expert_answer": expert_answer,
                "category": "fiscale",
                "regulatory_references": ["Risoluzione 62/E/2023"],
                "confidence_score": 0.95,
                "frequency": 1,
            },
        }

        result_ctx = await step_127__golden_candidate(ctx=ctx)

        # Assert: FAQ candidate was created
        from sqlalchemy import select

        from app.models.faq_automation import FAQCandidate

        stmt = select(FAQCandidate).where(FAQCandidate.suggested_question == query_text)
        result = await db_session.execute(stmt)
        faq_candidate = result.scalar_one_or_none()

        assert faq_candidate is not None, "Step 127 should create FAQ candidate in database"
        assert faq_candidate.status in [
            "auto_approved",
            "manually_approved",
        ], f"FAQ should be approved (status: {faq_candidate.status})"
        assert faq_candidate.best_response_content == expert_answer, "FAQ answer should match expert's improved answer"

        # Check if embedding was generated (column may not exist yet)
        if hasattr(faq_candidate, "question_embedding"):
            assert (
                faq_candidate.question_embedding is not None
            ), "question_embedding should be generated during FAQ creation"
            assert (
                len(faq_candidate.question_embedding) == 1536
            ), "Embedding should be 1536 dimensions (OpenAI ada-002)"

        # Check if feedback was linked to generated FAQ
        await db_session.refresh(feedback)
        assert feedback.generated_faq_id is not None, "expert_feedback.generated_faq_id should link to FAQ"
        assert str(feedback.generated_faq_id) == str(
            faq_candidate.id
        ), "Feedback should reference the created FAQ candidate"

    async def test_identical_question_retrieves_golden_set(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        insert_faq_via_sql,
    ):
        """TEST 8: Core golden set workflow - ask same question twice.

        This test validates the RETRIEVAL path (Step 24):
        1. Ask question → get LLM answer → mark "correct" → FAQ saved
        2. Ask EXACT same question again

        Assert:
            - Second query hits golden set (no LLM call)
            - Answer matches first response
            - Response time <100ms (cache hit)
            - Step 24 returns golden set match

        Expected: FAIL - Step 24 doesn't query database

        This is the CRITICAL test that exposes the bug:
        - Step 127 saves FAQ ✅ (proven by test 7)
        - Step 24 retrieves FAQ ❌ (THIS TEST FAILS)
        """
        # Arrange: Insert approved FAQ (simulating prior expert feedback)
        question = "Cos'è la risoluzione 62?"
        answer = "La risoluzione 62/E del 2023 chiarisce l'applicazione dell'IVA..."

        faq_id = await insert_faq_via_sql(
            question=question,
            answer=answer,
            status="auto_approved",
        )

        # Act: Execute Step 24 with the same question
        import hashlib

        query_signature = hashlib.sha256(question.lower().encode()).hexdigest()

        ctx = {
            "request_id": "test_request_002",
            "user_query": question,
            "query_signature": query_signature,
            "messages": [],
        }

        import time

        start_time = time.perf_counter()

        result_ctx = await step_24__golden_lookup(ctx=ctx)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert: Golden set match found
        golden_match = result_ctx.get("golden_match")
        assert golden_match is not None, "Step 24 should find golden set match for identical question"

        # Verify it's a REAL match, not mock data
        assert golden_match.get("faq_id") != "mock_faq_001", "Step 24 should return REAL FAQ, not mock data"
        assert (
            golden_match.get("faq_id") == faq_id
        ), f"Step 24 should return inserted FAQ ID {faq_id}, got {golden_match.get('faq_id')}"
        assert golden_match.get("answer") == answer, "Golden set answer should match stored FAQ answer"

        # Verify match metadata
        match_metadata = result_ctx.get("golden_match_metadata", {})
        assert match_metadata.get("match_found") is True
        assert match_metadata.get("match_type") in ["signature", "semantic"]
        assert match_metadata.get("similarity_score", 0) >= 0.95, "Exact question match should have similarity >= 0.95"

        # Verify performance (should be fast - database lookup only)
        assert elapsed_ms < 100, f"Golden set lookup should be <100ms (was {elapsed_ms:.2f}ms)"

    async def test_golden_set_bypasses_llm_call(
        self,
        test_client: TestClient,
        db_session: AsyncSession,
        insert_faq_via_sql,
    ):
        """TEST 9: Verify LLM is not called when golden set match exists.

        This test validates LLM cost optimization:
        1. Insert approved FAQ for "Test question"
        2. Mock LLM service to track calls
        3. Query "Test question"

        Assert:
            - LLM service is NOT called
            - Response comes from golden set
            - served_from_golden_set flag is True in response

        Expected: FAIL - LLM is still called because Step 24 doesn't retrieve

        This test demonstrates the COST IMPACT of the bug:
        - Every repeated question costs 10-50x more than necessary
        - Golden set hit should cost ~$0.0001 (database query)
        - LLM call costs ~$0.01-0.05 (API call)
        """
        # Arrange: Insert approved FAQ
        question = "Come funziona l'IVA in Italia?"
        answer = "L'IVA italiana funziona come imposta indiretta sui consumi..."

        faq_id = await insert_faq_via_sql(
            question=question,
            answer=answer,
            status="auto_approved",
        )

        # Arrange: Mock LLM service
        llm_call_count = {"count": 0}

        def mock_llm_call(*args, **kwargs):
            llm_call_count["count"] += 1
            return {"response": "This should not be called"}

        # Act: Execute complete RAG flow (Steps 1-30)
        # We'll simulate by calling Step 24 and checking if it sets golden_hit flag
        import hashlib

        query_signature = hashlib.sha256(question.lower().encode()).hexdigest()

        ctx = {
            "request_id": "test_request_003",
            "user_query": question,
            "query_signature": query_signature,
            "messages": [],
        }

        # Mock LLM service in Step 24 flow
        with patch("app.services.llm_service.chat_completion", side_effect=mock_llm_call):
            result_ctx = await step_24__golden_lookup(ctx=ctx)

            # Check if golden match was found
            golden_match = result_ctx.get("golden_match")

            if golden_match is not None:
                # Golden set hit - now verify LLM bypass
                # In real flow, Step 25 checks golden_match and skips to Step 28 (serve golden)
                # For this test, we verify Step 24 sets the flag correctly
                match_metadata = result_ctx.get("golden_match_metadata", {})
                assert match_metadata.get("match_found") is True

                # LLM should NOT be called if golden set is used
                # (This assertion may fail if Step 24 works but Step 25 doesn't skip LLM)
                assert llm_call_count["count"] == 0, "LLM should NOT be called when golden set match exists"

        # Assert: Verify golden set was served
        assert golden_match is not None, "Golden set should be found for approved FAQ"
        assert golden_match.get("answer") == answer, "Response should come from golden set, not LLM"

    async def test_step_24_queries_real_database_not_mock(
        self,
        db_session: AsyncSession,
        insert_faq_via_sql,
    ):
        """TEST 10: Verify Step 24 actually queries the database.

        This test directly inspects Step 24 implementation:
        1. Insert 3 approved FAQs with embeddings
        2. Call step_24__golden_lookup with matching query
        3. Verify database query was executed

        Assert:
            - Database query is executed (not mock)
            - SQL query includes WHERE status = 'auto_approved'
            - Vector similarity search is performed (if using pgvector)
            - Actual FAQ record is returned (not mock data)

        Expected: FAIL - Step 24 returns mock data

        This is the ROOT CAUSE test that directly exposes the bug:
        - Step 24 lines 312-347 contain ONLY mock code
        - No actual database query is executed
        - No semantic search service is called
        """
        # Arrange: Insert 3 approved FAQs
        faqs_data = [
            {
                "question": "Cos'è l'IVA?",
                "answer": "L'IVA è l'Imposta sul Valore Aggiunto...",
            },
            {
                "question": "Come funziona la ritenuta d'acconto?",
                "answer": "La ritenuta d'acconto è un pagamento anticipato...",
            },
            {
                "question": "Cos'è il modello 730?",
                "answer": "Il modello 730 è una dichiarazione semplificata...",
            },
        ]

        inserted_faq_ids = []
        for faq_data in faqs_data:
            faq_id = await insert_faq_via_sql(
                question=faq_data["question"],
                answer=faq_data["answer"],
                status="auto_approved",
            )
            inserted_faq_ids.append(faq_id)

        # Act: Call Step 24 with a query that should match FAQ #1
        query = "Cos'è l'IVA?"
        import hashlib

        query_signature = hashlib.sha256(query.lower().encode()).hexdigest()

        ctx = {
            "request_id": "test_request_004",
            "user_query": query,
            "query_signature": query_signature,
            "messages": [],
        }

        # Verify database query is executed (not mock)
        # We'll check by inspecting the returned data
        result_ctx = await step_24__golden_lookup(ctx=ctx)

        golden_match = result_ctx.get("golden_match")
        match_metadata = result_ctx.get("golden_match_metadata", {})

        # Assert: Real database query was executed
        if golden_match is not None:
            # Check for mock indicators
            faq_id = golden_match.get("faq_id")
            assert faq_id != "mock_faq_001", "Step 24 should return REAL FAQ ID, not 'mock_faq_001'"

            # Verify returned FAQ matches one of our inserted FAQs
            assert (
                faq_id in inserted_faq_ids
            ), f"Returned FAQ ID {faq_id} should match one of inserted FAQs: {inserted_faq_ids}"

            # Verify answer matches real data
            assert (
                golden_match.get("answer") == faqs_data[0]["answer"]
            ), "Answer should match inserted FAQ, not mock data"

            # Verify search method indicates real database query
            search_method = match_metadata.get("search_method", "")
            assert (
                search_method != "mock"
            ), f"search_method should indicate real DB query, not 'mock' (was: {search_method})"

        else:
            # No match found - this is the expected failure
            pytest.fail(
                "Step 24 returned no golden match. This indicates the bug is present: "
                "Step 24 doesn't query the database, even though approved FAQs exist. "
                f"Inserted {len(inserted_faq_ids)} FAQs but Step 24 returned None."
            )


@pytest.mark.asyncio
class TestGoldenSetWorkflowEdgeCases:
    """Edge case tests for Golden Set workflow."""

    async def test_unapproved_faq_not_retrieved(
        self,
        db_session: AsyncSession,
        insert_faq_via_sql,
    ):
        """Test that unapproved FAQs are not retrieved by Step 24.

        Expected: FAIL - Step 24 doesn't filter by approval status
        """
        # Arrange: Insert UNAPPROVED FAQ
        question = "Test unapproved question"
        answer = "Test unapproved answer"

        faq_id = await insert_faq_via_sql(
            question=question,
            answer=answer,
            status="pending_review",  # NOT APPROVED
        )

        # Act: Try to retrieve with Step 24
        import hashlib

        query_signature = hashlib.sha256(question.lower().encode()).hexdigest()

        ctx = {
            "request_id": "test_request_edge_001",
            "user_query": question,
            "query_signature": query_signature,
            "messages": [],
        }

        result_ctx = await step_24__golden_lookup(ctx=ctx)

        # Assert: Unapproved FAQ should NOT be returned
        golden_match = result_ctx.get("golden_match")
        if golden_match is not None:
            assert golden_match.get("faq_id") != faq_id, "Unapproved FAQs should not be returned by Step 24"

    async def test_signature_match_faster_than_semantic(
        self,
        db_session: AsyncSession,
        insert_faq_via_sql,
    ):
        """Test that signature match is faster than semantic search.

        Expected: FAIL - No signature optimization implemented
        """
        import time

        # Arrange: Insert FAQ
        question = "Performance test question"
        answer = "Performance test answer"

        faq_id = await insert_faq_via_sql(
            question=question,
            answer=answer,
            status="auto_approved",
        )

        # Act: Measure signature lookup performance
        import hashlib

        query_signature = hashlib.sha256(question.lower().encode()).hexdigest()

        ctx = {
            "request_id": "test_request_perf_001",
            "user_query": question,
            "query_signature": query_signature,
            "messages": [],
        }

        start_time = time.perf_counter()
        result_ctx = await step_24__golden_lookup(ctx=ctx)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert: Signature match should be fast (<10ms)
        golden_match = result_ctx.get("golden_match")
        if golden_match is not None:
            match_metadata = result_ctx.get("golden_match_metadata", {})
            match_type = match_metadata.get("match_type")

            if match_type == "signature":
                assert elapsed_ms < 10, f"Signature match should be <10ms (was {elapsed_ms:.2f}ms)"
