"""E2E tests for expert feedback submission API endpoint.

These tests validate the complete feedback submission flow from API request
through database persistence to background task execution.

BUGS THIS WOULD HAVE CAUGHT:
- Bug #2: Frontend validation schema mismatch (Pydantic validators)
- Bug #3: Foreign key to non-existent table (database constraints)
- Bug #5: Database session management (background tasks using closed sessions)
- Bug #6: String to enum conversion (API receives strings, must convert to enums)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
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
    ExpertProfile,
    FeedbackType,
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
    """Create test super user in database."""
    user = User(
        email=f"submission_test_{id(real_db)}@test.com",
        hashed_password="hashed",
        role=UserRole.SUPER_USER.value,
    )
    real_db.add(user)
    await real_db.commit()
    await real_db.refresh(user)
    return user


@pytest.fixture
async def test_regular_user(real_db):
    """Create test regular user (not super user) in database."""
    user = User(
        email=f"regular_test_{id(real_db)}@test.com",
        hashed_password="hashed",
        role=UserRole.REGULAR_USER.value,
    )
    real_db.add(user)
    await real_db.commit()
    await real_db.refresh(user)
    return user


@pytest.fixture
async def test_expert(real_db, test_super_user):
    """Create test expert profile in database."""
    expert = ExpertProfile(
        user_id=test_super_user.id,
        credential_types=[
            ExpertCredentialType.DOTTORE_COMMERCIALISTA,
            ExpertCredentialType.REVISORE_LEGALE,
        ],
        trust_score=0.85,
        is_verified=True,
        is_active=True,
    )
    real_db.add(expert)
    await real_db.commit()
    await real_db.refresh(expert)
    return expert


class TestFeedbackSubmissionValidation:
    """Test API validation for feedback submission (Bug #2: Frontend schema mismatch)."""

    def test_submit_feedback_invalid_feedback_type(self, test_super_user, test_expert):
        """Test API rejects invalid feedback_type values (Bug #2, #6)."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "INVALID_TYPE",  # Invalid value
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    def test_submit_feedback_invalid_category(self, test_super_user, test_expert):
        """Test API rejects invalid category values (Bug #2)."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "incomplete",
                        "category": "invalid_category",  # Invalid value
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    def test_submit_feedback_confidence_score_out_of_range(self, test_super_user):
        """Test API rejects confidence_score outside [0.0, 1.0] range."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "correct",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 1.5,  # Out of range
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    def test_submit_feedback_negative_time_spent(self, test_super_user):
        """Test API rejects negative time_spent_seconds."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "correct",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": -10,  # Negative value
                    },
                )

                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    def test_submit_feedback_complexity_rating_out_of_range(self, test_super_user):
        """Test API rejects complexity_rating outside [1, 5] range."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "correct",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                        "complexity_rating": 10,  # Out of range (1-5)
                    },
                )

                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    def test_submit_feedback_query_text_placeholder_rejected(self, test_super_user):
        """Test API rejects placeholder query_text (Bug #2: Frontend must extract actual query).

        Bug discovered during manual testing: Frontend was sending placeholder text
        instead of extracting actual user query from chat history.
        """

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with TestClient(app) as client:
                # Test Italian placeholder
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "correct",
                        "query_text": "[Domanda precedente dell'utente]",  # Placeholder
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
                assert "placeholder" in response.json()["detail"][0]["msg"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_submit_feedback_empty_query_text_rejected(self, test_super_user):
        """Test API rejects empty query_text."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "correct",
                        "query_text": "",  # Empty
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()


class TestFeedbackSubmissionAuthorization:
    """Test authorization requirements for feedback submission."""

    def test_submit_feedback_requires_super_user_role(self, test_regular_user, test_expert):
        """Test feedback submission fails for non-super users (RBAC check)."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_regular_user
        app.dependency_overrides[get_db] = mock_get_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(uuid4()),
                        "feedback_type": "correct",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == status.HTTP_403_FORBIDDEN
                assert "super user" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_requires_expert_profile(self, real_db, test_super_user):
        """Test feedback submission fails if user has no expert profile (Bug #3: FK constraint)."""

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
                        "feedback_type": "correct",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == status.HTTP_403_FORBIDDEN
                assert "not an expert" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_requires_active_expert(self, real_db, test_super_user, test_expert):
        """Test feedback submission fails if expert is not active."""
        test_expert.is_active = False
        await real_db.commit()

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
                        "feedback_type": "correct",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == status.HTTP_403_FORBIDDEN
                assert "not active" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


class TestFeedbackSubmissionE2E:
    """End-to-end tests for feedback submission (Bug #5: Session management)."""

    @pytest.mark.asyncio
    async def test_submit_correct_feedback_complete_flow(self, real_db, test_super_user, test_expert):
        """Test complete flow: submit CORRECT feedback → database persistence → Golden Set workflow.

        This test validates:
        - API accepts valid CORRECT feedback
        - Feedback is persisted to database
        - Enum values are correctly stored
        - Background task is triggered (doesn't crash with closed session)
        """

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            query_id = uuid4()

            # Mock Golden Set workflow to avoid dependency
            with patch("app.api.v1.expert_feedback._trigger_golden_set_workflow") as mock_workflow:
                mock_workflow.return_value = AsyncMock()

                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/expert-feedback/submit",
                        json={
                            "query_id": str(query_id),
                            "feedback_type": "correct",  # String (Bug #6: must convert to enum)
                            "query_text": "Come si calcola l'IVA?",
                            "original_answer": "Si applica il 22%",
                            "confidence_score": 0.95,
                            "time_spent_seconds": 120,
                        },
                    )

                    assert response.status_code == status.HTTP_201_CREATED
                    data = response.json()
                    assert "feedback_id" in data
                    assert data["feedback_type"] == "correct"
                    assert data["expert_trust_score"] == test_expert.trust_score
                    assert data["task_creation_attempted"] is True  # Golden Set workflow

                    # Verify feedback was persisted to database
                    feedback_id = data["feedback_id"]
                    feedback = await real_db.get(ExpertFeedback, feedback_id)

                    assert feedback is not None
                    assert feedback.feedback_type == FeedbackType.CORRECT  # Enum, not string
                    assert feedback.query_id == query_id
                    assert feedback.expert_id == test_expert.id
                    assert feedback.query_text == "Come si calcola l'IVA?"
                    assert feedback.confidence_score == 0.95
                    assert feedback.time_spent_seconds == 120

                    # Verify background task was triggered
                    mock_workflow.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_incomplete_feedback_with_task_generation(self, real_db, test_super_user, test_expert):
        """Test INCOMPLETE feedback with task generation (Bug #5: Background task session).

        This test validates:
        - INCOMPLETE feedback triggers task generation
        - Background task uses its own database session (not closed request session)
        - Task generation doesn't block feedback submission response
        """

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            query_id = uuid4()

            # Mock TaskGeneratorService to avoid file I/O
            with patch("app.api.v1.expert_feedback.TaskGeneratorService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.generate_task_from_feedback = AsyncMock(return_value="QUERY-08")
                mock_service_class.return_value = mock_service

                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/expert-feedback/submit",
                        json={
                            "query_id": str(query_id),
                            "feedback_type": "incomplete",
                            "category": "calcolo_sbagliato",
                            "query_text": "Come si calcola l'IVA per i forfettari?",
                            "original_answer": "I forfettari non pagano IVA",
                            "confidence_score": 0.8,
                            "time_spent_seconds": 180,
                            "additional_details": "Manca spiegazione dei casi specifici UE",
                        },
                    )

                    assert response.status_code == status.HTTP_201_CREATED
                    data = response.json()
                    assert data["feedback_type"] == "incomplete"
                    assert data["task_creation_attempted"] is True

                    # Verify feedback was persisted
                    feedback_id = data["feedback_id"]
                    feedback = await real_db.get(ExpertFeedback, feedback_id)

                    assert feedback is not None
                    assert feedback.feedback_type == FeedbackType.INCOMPLETE
                    assert feedback.additional_details == "Manca spiegazione dei casi specifici UE"

                    # Wait briefly for background task to execute
                    await asyncio.sleep(0.1)

                    # Verify background task was called (Bug #5: must use own session)
                    # The task should not crash even though request session is closed
                    mock_service.generate_task_from_feedback.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_incorrect_feedback_with_all_fields(self, real_db, test_super_user, test_expert):
        """Test INCORRECT feedback with all optional fields populated."""

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            query_id = uuid4()

            with patch("app.api.v1.expert_feedback.TaskGeneratorService"):
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/expert-feedback/submit",
                        json={
                            "query_id": str(query_id),
                            "feedback_type": "incorrect",
                            "category": "interpretazione_errata",
                            "query_text": "Quale aliquota IVA per gli e-book?",
                            "original_answer": "Si applica l'aliquota del 22%",
                            "expert_answer": "Per gli e-book si applica l'aliquota ridotta del 4%",
                            "improvement_suggestions": [
                                "Aggiornare knowledge base con aliquote ridotte",
                                "Citare D.L. 83/2012",
                            ],
                            "regulatory_references": ["D.L. 83/2012", "Art. 74, comma 1-bis DPR 633/1972"],
                            "confidence_score": 0.98,
                            "time_spent_seconds": 240,
                            "complexity_rating": 4,
                            "additional_details": "La risposta è completamente errata. Gli e-book hanno aliquota 4%.",
                        },
                    )

                    assert response.status_code == status.HTTP_201_CREATED
                    data = response.json()

                    # Verify all fields were stored correctly
                    feedback_id = data["feedback_id"]
                    feedback = await real_db.get(ExpertFeedback, feedback_id)

                    assert feedback.feedback_type == FeedbackType.INCORRECT
                    assert feedback.expert_answer == "Per gli e-book si applica l'aliquota ridotta del 4%"
                    assert len(feedback.improvement_suggestions) == 2
                    assert len(feedback.regulatory_references) == 2
                    assert feedback.complexity_rating == 4
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_without_optional_fields(self, real_db, test_super_user, test_expert):
        """Test feedback submission with only required fields (minimal case)."""

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            query_id = uuid4()

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        # Required fields only
                        "query_id": str(query_id),
                        "feedback_type": "correct",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                        # No optional fields
                    },
                )

                assert response.status_code == status.HTTP_201_CREATED
                data = response.json()

                # Verify feedback was created with defaults for optional fields
                feedback_id = data["feedback_id"]
                feedback = await real_db.get(ExpertFeedback, feedback_id)

                assert feedback.category is None
                assert feedback.expert_answer is None
                assert feedback.improvement_suggestions == []
                assert feedback.regulatory_references == []
                assert feedback.complexity_rating is None
                assert feedback.additional_details is None
        finally:
            app.dependency_overrides.clear()


class TestFeedbackSubmissionEnumConversion:
    """Test string-to-enum conversion in API layer (Bug #6)."""

    @pytest.mark.asyncio
    async def test_all_feedback_types_string_to_enum(self, real_db, test_super_user, test_expert):
        """Test all feedback_type string values are correctly converted to enums."""

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with patch("app.api.v1.expert_feedback._trigger_golden_set_workflow"):
                with patch("app.api.v1.expert_feedback.TaskGeneratorService"):
                    with TestClient(app) as client:
                        feedback_types = ["correct", "incomplete", "incorrect"]

                        for feedback_type_str in feedback_types:
                            response = client.post(
                                "/api/v1/expert-feedback/submit",
                                json={
                                    "query_id": str(uuid4()),
                                    "feedback_type": feedback_type_str,  # String
                                    "query_text": f"Test {feedback_type_str}",
                                    "original_answer": "Test answer",
                                    "confidence_score": 0.9,
                                    "time_spent_seconds": 100,
                                },
                            )

                            assert response.status_code == status.HTTP_201_CREATED
                            data = response.json()

                            # Verify enum was stored correctly
                            feedback_id = data["feedback_id"]
                            feedback = await real_db.get(ExpertFeedback, feedback_id)

                            assert feedback.feedback_type.value == feedback_type_str
                            assert isinstance(feedback.feedback_type, FeedbackType)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_all_categories_string_to_enum(self, real_db, test_super_user, test_expert):
        """Test all category string values are correctly converted to enums."""

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_super_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                categories = [
                    "normativa_obsoleta",
                    "interpretazione_errata",
                    "caso_mancante",
                    "calcolo_sbagliato",
                    "troppo_generico",
                ]

                for category_str in categories:
                    response = client.post(
                        "/api/v1/expert-feedback/submit",
                        json={
                            "query_id": str(uuid4()),
                            "feedback_type": "incomplete",
                            "category": category_str,  # String
                            "query_text": f"Test {category_str}",
                            "original_answer": "Test answer",
                            "confidence_score": 0.8,
                            "time_spent_seconds": 120,
                        },
                    )

                    assert response.status_code == status.HTTP_201_CREATED
                    data = response.json()

                    # Verify enum was stored correctly
                    feedback_id = data["feedback_id"]
                    feedback = await real_db.get(ExpertFeedback, feedback_id)

                    assert feedback.category.value == category_str
        finally:
            app.dependency_overrides.clear()
