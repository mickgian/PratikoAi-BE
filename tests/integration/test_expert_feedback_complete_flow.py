"""End-to-end integration tests for Expert Feedback System complete workflows.

These tests validate the entire flow from API request through database persistence
to background task execution and result verification. They test REAL database
transactions, not mocks.

BUGS THIS WOULD HAVE CAUGHT:
- ALL 8 BUGS: This E2E test validates the complete integrated system

NOTE: Skipped in CI - requires real PostgreSQL database connection.
"""

import pytest

pytest.skip(
    "E2E integration tests require real PostgreSQL database - skipped in CI",
    allow_module_level=True,
)

import asyncio
from unittest.mock import AsyncMock, mock_open, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.database import AsyncSessionLocal, get_db
from app.models.quality_analysis import (
    ExpertCredentialType,
    ExpertFeedback,
    ExpertGeneratedTask,
    ExpertProfile,
    FeedbackType,
    ItalianFeedbackCategory,
)
from app.models.user import User, UserRole


@pytest.fixture
async def real_db():
    """Real database session for integration tests."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture
async def test_super_user(real_db):
    """Create test super user."""
    user = User(
        email=f"e2e_test_{id(real_db)}@test.com",
        hashed_password="hashed",
        role=UserRole.SUPER_USER.value,
        name="E2E Test Expert",
    )
    real_db.add(user)
    await real_db.commit()
    await real_db.refresh(user)
    return user


@pytest.fixture
async def test_expert(real_db, test_super_user):
    """Create test expert profile."""
    expert = ExpertProfile(
        user_id=test_super_user.id,
        credentials=["Dottore Commercialista"],
        credential_types=[ExpertCredentialType.DOTTORE_COMMERCIALISTA],
        trust_score=0.90,  # High trust for auto-approval
        is_verified=True,
        is_active=True,
    )
    real_db.add(expert)
    await real_db.commit()
    await real_db.refresh(expert)
    return expert


class TestCompleteCorrectFeedbackFlow:
    """Test complete flow for CORRECT feedback → Golden Set integration."""

    @pytest.mark.asyncio
    async def test_correct_feedback_e2e_flow(self, real_db, test_super_user, test_expert):
        """Test complete CORRECT feedback flow: API → Database → Golden Set workflow.

        Flow:
        1. Expert submits CORRECT feedback via API
        2. Feedback is persisted to database with correct enum values
        3. Background task triggers Golden Set workflow
        4. Golden Set workflow updates feedback with generated_faq_id
        5. Verify all database state is correct
        """

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            query_id = uuid4()
            faq_id = f"faq_{uuid4()}"

            # Mock Golden Set workflow steps
            with patch("app.api.v1.expert_feedback.step_127__golden_candidate") as mock_127:
                with patch("app.api.v1.expert_feedback.step_128__golden_approval") as mock_128:
                    with patch("app.api.v1.expert_feedback.step_129__publish_golden") as mock_129:
                        # Mock successful Golden Set workflow
                        mock_127.return_value = {
                            "faq_candidate": {"priority_score": 0.95},
                            "expert_feedback": {
                                "query_text": "Qual è l'aliquota IVA ordinaria?",
                                "expert_answer": "L'aliquota IVA ordinaria in Italia è del 22%",
                            },
                        }
                        mock_128.return_value = {
                            "approval_decision": {"status": "auto_approved"},
                            "faq_candidate": {"priority_score": 0.95},
                        }
                        mock_129.return_value = {
                            "published_faq_id": faq_id,
                            "version": "1.0",
                        }

                        # Step 1: Submit CORRECT feedback via API
                        with TestClient(app) as client:
                            response = client.post(
                                "/api/v1/expert-feedback/submit",
                                json={
                                    "query_id": str(query_id),
                                    "feedback_type": "correct",
                                    "query_text": "Qual è l'aliquota IVA ordinaria?",
                                    "original_answer": "L'aliquota IVA ordinaria in Italia è del 22%",
                                    "confidence_score": 0.98,
                                    "time_spent_seconds": 60,
                                },
                            )

                            # Verify API response
                            assert response.status_code == status.HTTP_201_CREATED
                            data = response.json()
                            assert data["feedback_type"] == "correct"
                            assert data["task_creation_attempted"] is True
                            feedback_id = data["feedback_id"]

                        # Step 2: Verify feedback in database (enum serialization)
                        await real_db.commit()  # Ensure changes are committed
                        feedback = await real_db.get(ExpertFeedback, feedback_id)

                        assert feedback is not None
                        assert feedback.feedback_type == FeedbackType.CORRECT  # Enum, not string
                        assert feedback.query_id == query_id
                        assert feedback.expert_id == test_expert.id
                        assert feedback.confidence_score == 0.98
                        assert feedback.task_creation_attempted is True

                        # Step 3: Wait for background task to complete
                        await asyncio.sleep(0.5)

                        # Step 4: Verify Golden Set workflow was executed
                        mock_127.assert_called_once()
                        mock_128.assert_called_once()
                        mock_129.assert_called_once()

                        # Step 5: Verify feedback was updated with FAQ ID
                        await real_db.refresh(feedback)
                        assert feedback.generated_faq_id == faq_id
                        assert feedback.task_creation_success is True
                        assert feedback.task_creation_error is None
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_correct_feedback_low_trust_score_requires_review(self, real_db, test_super_user):
        """Test CORRECT feedback from low-trust expert requires manual review."""
        # Create low-trust expert
        low_trust_expert = ExpertProfile(
            user_id=test_super_user.id,
            credential_types=[ExpertCredentialType.CONSULENTE_FISCALE],
            trust_score=0.60,  # Below auto-approval threshold
            is_verified=True,
            is_active=True,
        )
        real_db.add(low_trust_expert)
        await real_db.commit()
        await real_db.refresh(low_trust_expert)

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            # Mock Golden Set workflow to reject (requires review)
            with patch("app.api.v1.expert_feedback.step_127__golden_candidate") as mock_127:
                with patch("app.api.v1.expert_feedback.step_128__golden_approval") as mock_128:
                    mock_127.return_value = {"faq_candidate": {"priority_score": 0.70}}
                    mock_128.return_value = {
                        "approval_decision": {"status": "requires_review"},  # Not approved
                    }

                    with TestClient(app) as client:
                        response = client.post(
                            "/api/v1/expert-feedback/submit",
                            json={
                                "query_id": str(uuid4()),
                                "feedback_type": "correct",
                                "query_text": "Test question",
                                "original_answer": "Test answer",
                                "confidence_score": 0.85,
                                "time_spent_seconds": 120,
                            },
                        )

                        assert response.status_code == status.HTTP_201_CREATED
                        feedback_id = response.json()["feedback_id"]

                    # Wait for background task
                    await asyncio.sleep(0.5)

                    # Verify feedback was NOT published (requires review)
                    feedback = await real_db.get(ExpertFeedback, feedback_id)
                    assert feedback.generated_faq_id is None
                    assert feedback.task_creation_success is False
        finally:
            app.dependency_overrides.clear()


class TestCompleteIncompleteFeedbackFlow:
    """Test complete flow for INCOMPLETE feedback → Task generation."""

    @pytest.mark.asyncio
    async def test_incomplete_feedback_e2e_flow(self, real_db, test_super_user, test_expert):
        """Test complete INCOMPLETE feedback flow: API → Database → Task generation.

        Flow:
        1. Expert submits INCOMPLETE feedback with additional_details
        2. Feedback is persisted with correct enum values
        3. Background task generates task in QUERY_ISSUES_ROADMAP.md
        4. Task record is created in expert_generated_tasks
        5. Feedback is updated with generated_task_id
        """

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            query_id = uuid4()

            # Mock file operations for task generation
            mock_file_content = "# Existing tasks\nQUERY-07: Previous task"
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value=mock_file_content):
                    with patch("pathlib.Path.open", mock_open()) as mock_file:
                        # Step 1: Submit INCOMPLETE feedback
                        with TestClient(app) as client:
                            response = client.post(
                                "/api/v1/expert-feedback/submit",
                                json={
                                    "query_id": str(query_id),
                                    "feedback_type": "incomplete",
                                    "category": "calcolo_sbagliato",
                                    "query_text": "Come si calcola l'IVA per i forfettari?",
                                    "original_answer": "I forfettari non pagano IVA",
                                    "confidence_score": 0.75,
                                    "time_spent_seconds": 180,
                                    "additional_details": "La risposta non spiega i casi specifici di cessioni UE",
                                },
                            )

                            assert response.status_code == status.HTTP_201_CREATED
                            data = response.json()
                            assert data["feedback_type"] == "incomplete"
                            assert data["task_creation_attempted"] is True
                            feedback_id = data["feedback_id"]

                        # Step 2: Verify feedback in database
                        await real_db.commit()
                        feedback = await real_db.get(ExpertFeedback, feedback_id)

                        assert feedback.feedback_type == FeedbackType.INCOMPLETE
                        assert feedback.category == ItalianFeedbackCategory.CALCOLO_SBAGLIATO
                        assert feedback.additional_details is not None

                        # Step 3: Wait for background task
                        await asyncio.sleep(0.5)

                        # Step 4: Verify task file was written
                        mock_file.assert_called_once()

                        # Step 5: Verify feedback was updated with task ID
                        await real_db.refresh(feedback)
                        assert feedback.generated_task_id is not None
                        assert feedback.generated_task_id.startswith("QUERY-")
                        assert feedback.task_creation_success is True

                        # Step 6: Verify task record in database
                        result = await real_db.execute(
                            select(ExpertGeneratedTask).where(
                                ExpertGeneratedTask.task_id == feedback.generated_task_id
                            )
                        )
                        task = result.scalar_one_or_none()

                        assert task is not None
                        assert task.feedback_id == feedback.id
                        assert task.expert_id == test_expert.id
                        assert task.question == feedback.query_text
                        assert task.answer == feedback.original_answer
                        assert task.additional_details == feedback.additional_details
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_incomplete_feedback_without_additional_details_no_task(self, real_db, test_super_user, test_expert):
        """Test INCOMPLETE feedback without additional_details doesn't generate task."""

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "incomplete",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.8,
                        "time_spent_seconds": 100,
                        # No additional_details
                    },
                )

                assert response.status_code == status.HTTP_201_CREATED
                data = response.json()
                assert data["task_creation_attempted"] is False  # No task generation

                # Verify feedback in database
                feedback_id = data["feedback_id"]
                feedback = await real_db.get(ExpertFeedback, feedback_id)

                assert feedback.generated_task_id is None
                assert feedback.task_creation_attempted is False
        finally:
            app.dependency_overrides.clear()


class TestCompleteIncorrectFeedbackFlow:
    """Test complete flow for INCORRECT feedback → Task generation."""

    @pytest.mark.asyncio
    async def test_incorrect_feedback_e2e_flow_with_expert_answer(self, real_db, test_super_user, test_expert):
        """Test INCORRECT feedback with expert_answer and full corrections.

        Flow:
        1. Expert submits INCORRECT feedback with corrected answer
        2. All fields are persisted correctly (enums, arrays, etc.)
        3. Task is generated with complete information
        """

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            query_id = uuid4()

            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value="QUERY-07: Task"):
                    with patch("pathlib.Path.open", mock_open()):
                        with TestClient(app) as client:
                            response = client.post(
                                "/api/v1/expert-feedback/submit",
                                json={
                                    "query_id": str(query_id),
                                    "feedback_type": "incorrect",
                                    "category": "interpretazione_errata",
                                    "query_text": "Quale aliquota IVA per gli e-book?",
                                    "original_answer": "Si applica l'aliquota ordinaria del 22%",
                                    "expert_answer": "Per gli e-book si applica l'aliquota ridotta del 4%",
                                    "improvement_suggestions": [
                                        "Aggiornare knowledge base con aliquote ridotte",
                                        "Citare normativa specifica",
                                    ],
                                    "regulatory_references": [
                                        "D.L. 83/2012",
                                        "Art. 74, comma 1-bis DPR 633/1972",
                                    ],
                                    "confidence_score": 0.98,
                                    "time_spent_seconds": 300,
                                    "complexity_rating": 4,
                                    "additional_details": "La risposta è completamente errata. Gli e-book hanno aliquota 4%.",
                                },
                            )

                            assert response.status_code == status.HTTP_201_CREATED
                            feedback_id = response.json()["feedback_id"]

                        # Wait for background task
                        await asyncio.sleep(0.5)

                        # Verify all fields were stored correctly
                        feedback = await real_db.get(ExpertFeedback, feedback_id)

                        assert feedback.feedback_type == FeedbackType.INCORRECT
                        assert feedback.category == ItalianFeedbackCategory.INTERPRETAZIONE_ERRATA
                        assert feedback.expert_answer == "Per gli e-book si applica l'aliquota ridotta del 4%"
                        assert len(feedback.improvement_suggestions) == 2
                        assert "Aggiornare knowledge base" in feedback.improvement_suggestions[0]
                        assert len(feedback.regulatory_references) == 2
                        assert "D.L. 83/2012" in feedback.regulatory_references
                        assert feedback.complexity_rating == 4
                        assert feedback.additional_details is not None
                        assert feedback.generated_task_id is not None
                        assert feedback.task_creation_success is True
        finally:
            app.dependency_overrides.clear()


class TestErrorHandlingAndRecovery:
    """Test error scenarios and graceful degradation."""

    @pytest.mark.asyncio
    async def test_feedback_persisted_even_if_background_task_fails(self, real_db, test_super_user, test_expert):
        """Test feedback is saved even if background task fails (graceful degradation)."""

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            # Force background task to fail
            with patch("pathlib.Path.exists", side_effect=Exception("File system error")):
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/expert-feedback/submit",
                        json={
                            "query_id": str(uuid4()),
                            "feedback_type": "incomplete",
                            "query_text": "Test question",
                            "original_answer": "Test answer",
                            "confidence_score": 0.8,
                            "time_spent_seconds": 100,
                            "additional_details": "Test details",
                        },
                    )

                    # API should still succeed
                    assert response.status_code == status.HTTP_201_CREATED
                    feedback_id = response.json()["feedback_id"]

                # Wait for background task to fail
                await asyncio.sleep(0.5)

                # Verify feedback was saved (even though task failed)
                feedback = await real_db.get(ExpertFeedback, feedback_id)
                assert feedback is not None
                assert feedback.feedback_type == FeedbackType.INCOMPLETE

                # Verify error was logged
                assert feedback.task_creation_success is False
                assert feedback.task_creation_error is not None
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_enum_validation_prevents_invalid_data(self, real_db, test_super_user, test_expert):
        """Test database enum constraints prevent invalid data."""

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                # Try to submit invalid feedback_type
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "INVALID_TYPE",
                        "query_text": "Test",
                        "original_answer": "Test",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                # Should be rejected at API layer (Pydantic validation)
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()


class TestConcurrentFeedbackSubmissions:
    """Test system handles concurrent feedback submissions correctly."""

    @pytest.mark.asyncio
    async def test_multiple_experts_submit_concurrently(self, real_db):
        """Test multiple experts can submit feedback concurrently without conflicts."""
        # Create multiple expert users
        experts = []
        for i in range(3):
            user = User(
                email=f"concurrent_test_{i}@test.com",
                hashed_password="hashed",
                role=UserRole.SUPER_USER.value,
            )
            real_db.add(user)
            await real_db.flush()

            expert = ExpertProfile(
                user_id=user.id,
                credential_types=[ExpertCredentialType.CONSULENTE_FISCALE],
                trust_score=0.80,
                is_verified=True,
                is_active=True,
            )
            real_db.add(expert)
            await real_db.flush()
            experts.append((user, expert))

        await real_db.commit()

        # Mock file operations
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="QUERY-07: Task"):
                with patch("pathlib.Path.open", mock_open()):
                    # Submit feedback from multiple experts concurrently
                    async def submit_feedback(user, expert):
                        async def get_real_db():
                            async with AsyncSessionLocal() as session:
                                yield session

                        app.dependency_overrides[get_current_user] = lambda: user
                        app.dependency_overrides[get_db] = get_real_db

                        with TestClient(app) as client:
                            response = client.post(
                                "/api/v1/expert-feedback/submit",
                                json={
                                    "query_id": str(uuid4()),
                                    "feedback_type": "incomplete",
                                    "query_text": f"Question from {user.email}",
                                    "original_answer": "Answer",
                                    "confidence_score": 0.8,
                                    "time_spent_seconds": 100,
                                    "additional_details": "Details",
                                },
                            )
                            app.dependency_overrides.clear()
                            return response.status_code, response.json()

                    # Run concurrent submissions
                    results = await asyncio.gather(*[submit_feedback(user, expert) for user, expert in experts])

                    # Verify all submissions succeeded
                    for status_code, data in results:
                        assert status_code == status.HTTP_201_CREATED
                        assert "feedback_id" in data
