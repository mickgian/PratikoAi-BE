"""Integration tests for Expert Feedback API endpoints.

Tests all API endpoints for the Expert Feedback System:
- POST /api/v1/expert-feedback/submit
- GET /api/v1/expert-feedback/history
- GET /api/v1/expert-feedback/{feedback_id}
- GET /api/v1/expert-feedback/experts/me/profile
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.database import get_db
from app.models.quality_analysis import (
    ExpertCredentialType,
    ExpertFeedback,
    ExpertProfile,
    FeedbackType,
    ItalianFeedbackCategory,
)
from app.models.user import User, UserRole


def create_mock_db():
    """Create a properly configured mock database session."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.rollback = AsyncMock()
    return mock_db


@pytest.fixture
def test_user():
    """Test user fixture with SUPER_USER role using MagicMock."""
    user = MagicMock()
    user.id = 1
    user.email = "expert@test.com"
    user.is_active = True
    user.is_verified = True
    user.role = UserRole.SUPER_USER.value  # SUPER_USER role for RBAC
    return user


@pytest.fixture
def regular_user():
    """Regular user fixture (not a super user) using MagicMock."""
    user = MagicMock()
    user.id = 2
    user.email = "regular@test.com"
    user.is_active = True
    user.is_verified = True
    user.role = UserRole.REGULAR_USER.value  # Regular user role
    return user


@pytest.fixture
def expert_profile():
    """Expert profile fixture with high trust score using MagicMock."""
    profile = MagicMock()
    profile.id = uuid4()
    profile.user_id = 1  # User model uses integer IDs, not UUIDs
    profile.credentials = ["Dottore Commercialista", "Revisore Legale"]
    profile.credential_types = [ExpertCredentialType.DOTTORE_COMMERCIALISTA, ExpertCredentialType.REVISORE_LEGALE]
    profile.experience_years = 15
    profile.specializations = ["diritto_tributario", "lavoro"]
    profile.feedback_count = 100
    profile.feedback_accuracy_rate = 0.95
    profile.average_response_time_seconds = 200
    profile.trust_score = 0.92  # Above threshold of 0.7
    profile.professional_registration_number = "AA123456"
    profile.organization = "Studio Test"
    profile.location_city = "Milano"
    profile.is_verified = True
    profile.is_active = True
    return profile


@pytest.fixture
def low_trust_expert():
    """Expert profile with low trust score (below threshold) using MagicMock."""
    profile = MagicMock()
    profile.id = uuid4()
    profile.user_id = 2  # User model uses integer IDs, not UUIDs
    profile.credentials = ["Consulente Fiscale"]
    profile.credential_types = [ExpertCredentialType.CONSULENTE_FISCALE]
    profile.experience_years = 2
    profile.specializations = ["fiscale"]
    profile.feedback_count = 5
    profile.feedback_accuracy_rate = 0.5
    profile.average_response_time_seconds = 300
    profile.trust_score = 0.5  # Below threshold of 0.7
    profile.is_verified = True
    profile.is_active = True
    return profile


@pytest.fixture
def sample_feedback(expert_profile):
    """Sample feedback record using MagicMock."""
    feedback = MagicMock()
    feedback.id = uuid4()
    feedback.query_id = uuid4()
    feedback.expert_id = expert_profile.id
    feedback.feedback_type = FeedbackType.INCOMPLETE  # Use actual enum, not MagicMock
    feedback.category = ItalianFeedbackCategory.CALCOLO_SBAGLIATO  # Use actual enum
    feedback.query_text = "Come si calcola l'IVA per il regime forfettario?"
    feedback.original_answer = "Nel regime forfettario non si applica l'IVA."
    feedback.expert_answer = "Nel regime forfettario non si applica l'IVA in fattura, ma..."
    feedback.improvement_suggestions = ["Aggiungere casi specifici", "Citare normativa aggiornata"]
    feedback.regulatory_references = ["Art. 1, comma 54-89, L. 190/2014"]
    feedback.confidence_score = 0.9
    feedback.time_spent_seconds = 180
    feedback.complexity_rating = 3
    feedback.additional_details = "La risposta è incompleta perché non tratta i casi specifici."
    feedback.task_creation_attempted = True
    feedback.generated_task_id = "DEV-BE-123"
    feedback.generated_faq_id = None  # Added for Golden Set integration
    feedback.task_creation_success = True
    feedback.task_creation_error = None
    feedback.action_taken = None
    feedback.improvement_applied = False
    feedback.feedback_timestamp = datetime.now()  # Changed from created_at to match schema
    feedback.created_at = datetime.now()
    feedback.updated_at = datetime.now()
    return feedback


class TestSubmitFeedback:
    """Tests for POST /api/v1/expert-feedback/submit endpoint."""

    @pytest.fixture
    def client(self, test_user):
        """Test client fixture with dependency overrides."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = mock_get_db

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_success_with_task_generation(self, test_user, expert_profile):
        """Test successful feedback submission with automatic task generation."""
        query_id = uuid4()

        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            with (
                patch("app.api.v1.expert_feedback.TaskGeneratorService") as mock_task_service,
                patch("app.api.v1.expert_feedback.ExpertFeedback") as mock_feedback_class,
            ):
                # Mock expert profile query
                mock_expert_result = MagicMock()
                mock_expert_result.scalar_one_or_none.return_value = expert_profile
                mock_db.execute.return_value = mock_expert_result

                # Mock task service
                mock_service_instance = AsyncMock()
                mock_task_service.return_value = mock_service_instance

                # Mock feedback instance - use actual enum value, not MagicMock
                mock_feedback = MagicMock()
                mock_feedback.id = uuid4()
                mock_feedback.feedback_type = FeedbackType.INCOMPLETE
                mock_feedback.task_creation_attempted = True
                mock_feedback.generated_task_id = None
                mock_feedback.generated_faq_id = None
                mock_feedback_class.return_value = mock_feedback

                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/expert-feedback/submit",
                        json={
                            "query_id": str(query_id),
                            "feedback_type": "incomplete",
                            "category": "calcolo_sbagliato",
                            "query_text": "Come si calcola l'IVA?",
                            "original_answer": "Si applica il 22%",
                            "expert_answer": "Si applica il 22% sulla base imponibile...",
                            "improvement_suggestions": ["Aggiungere dettagli"],
                            "regulatory_references": ["D.P.R. 633/1972"],
                            "confidence_score": 0.9,
                            "time_spent_seconds": 180,
                            "complexity_rating": 3,
                            "additional_details": "Manca spiegazione della base imponibile",
                        },
                    )

                    assert response.status_code == 201
                    data = response.json()
                    assert data["feedback_type"] == "incomplete"
                    assert data["expert_trust_score"] == 0.92
                    assert data["task_creation_attempted"] is True
                    assert "message" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_super_user_success(self, test_user, expert_profile):
        """Test successful feedback submission with SUPER_USER role."""
        query_id = uuid4()

        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies - test_user has SUPER_USER role
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            with patch("app.api.v1.expert_feedback.ExpertFeedback") as mock_feedback_class:
                # Mock expert profile query
                mock_expert_result = MagicMock()
                mock_expert_result.scalar_one_or_none.return_value = expert_profile
                mock_db.execute.return_value = mock_expert_result

                # Mock feedback instance - use actual enum value, not MagicMock
                mock_feedback = MagicMock()
                mock_feedback.id = uuid4()
                mock_feedback.feedback_type = FeedbackType.CORRECT
                mock_feedback.task_creation_attempted = True  # Changed to True for Golden Set workflow
                mock_feedback.generated_task_id = None
                mock_feedback.generated_faq_id = None  # Will be populated by background task
                mock_feedback_class.return_value = mock_feedback

                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/expert-feedback/submit",
                        json={
                            "query_id": str(query_id),
                            "feedback_type": "correct",
                            "query_text": "Test question",
                            "original_answer": "Test answer",
                            "confidence_score": 0.9,
                            "time_spent_seconds": 100,
                        },
                    )

                    assert response.status_code == 201
                    data = response.json()
                    assert data["feedback_type"] == "correct"
                    assert data["expert_trust_score"] == 0.92
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_not_super_user(self, regular_user, expert_profile):
        """Test feedback submission fails when user is not a SUPER_USER."""
        query_id = uuid4()

        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies - use regular_user (not SUPER_USER)
        app.dependency_overrides[get_current_user] = lambda: regular_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(query_id),
                        "feedback_type": "incomplete",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.8,
                        "time_spent_seconds": 120,
                    },
                )

                assert response.status_code == 403
                assert "Only super users can provide feedback" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_not_expert(self, test_user):
        """Test feedback submission fails when user is not an expert."""
        query_id = uuid4()

        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile query - return None (not an expert)
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_expert_result

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(query_id),
                        "feedback_type": "correct",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == 403
                assert "not an expert" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_inactive_expert(self, test_user, expert_profile):
        """Test feedback submission fails when expert is inactive."""
        expert_profile.is_active = False
        query_id = uuid4()

        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile query
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = expert_profile
            mock_db.execute.return_value = mock_expert_result

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(query_id),
                        "feedback_type": "correct",
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == 403
                assert "not active or verified" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_validation_error(self, test_user, expert_profile):
        """Test feedback submission fails with invalid data."""
        query_id = uuid4()

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user

        try:
            with TestClient(app) as client:
                # Invalid feedback_type
                response = client.post(
                    "/api/v1/expert-feedback/submit",
                    json={
                        "query_id": str(query_id),
                        "feedback_type": "invalid_type",  # Invalid
                        "query_text": "Test question",
                        "original_answer": "Test answer",
                        "confidence_score": 0.9,
                        "time_spent_seconds": 100,
                    },
                )

                assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_feedback_without_additional_details(self, test_user, expert_profile):
        """Test feedback submission without additional_details (no task generation)."""
        query_id = uuid4()

        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            with patch("app.api.v1.expert_feedback.ExpertFeedback") as mock_feedback_class:
                # Mock expert profile query
                mock_expert_result = MagicMock()
                mock_expert_result.scalar_one_or_none.return_value = expert_profile
                mock_db.execute.return_value = mock_expert_result

                # Mock feedback instance - use actual enum value, not MagicMock
                mock_feedback = MagicMock()
                mock_feedback.id = uuid4()
                mock_feedback.feedback_type = FeedbackType.INCOMPLETE
                mock_feedback.task_creation_attempted = False
                mock_feedback.generated_task_id = None
                mock_feedback.generated_faq_id = None
                mock_feedback_class.return_value = mock_feedback

                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/expert-feedback/submit",
                        json={
                            "query_id": str(query_id),
                            "feedback_type": "incomplete",
                            "query_text": "Test question",
                            "original_answer": "Test answer",
                            "confidence_score": 0.9,
                            "time_spent_seconds": 100,
                            # No additional_details
                        },
                    )

                    assert response.status_code == 201
                    data = response.json()
                    assert data["task_creation_attempted"] is False
        finally:
            app.dependency_overrides.clear()


class TestFeedbackHistory:
    """Tests for GET /api/v1/expert-feedback/history endpoint."""

    @pytest.fixture
    def client(self, test_user):
        """Test client fixture with dependency overrides."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = mock_get_db

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_feedback_history_success(self, test_user, expert_profile, sample_feedback):
        """Test successful feedback history retrieval."""
        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile query
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = expert_profile

            # Mock feedback query
            mock_feedback_result = MagicMock()
            mock_feedback_result.scalars.return_value.all.return_value = [sample_feedback]

            # Mock count query
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 1

            mock_db.execute.side_effect = [mock_expert_result, mock_count_result, mock_feedback_result]

            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/history?limit=20&offset=0")

                assert response.status_code == 200
                data = response.json()
                assert data["total_count"] == 1
                assert data["limit"] == 20
                assert data["offset"] == 0
                assert len(data["items"]) == 1
                assert data["items"][0]["feedback_type"] == "incomplete"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_feedback_history_not_expert(self, test_user):
        """Test feedback history fails when user is not an expert."""
        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile query - return None
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_expert_result

            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/history")

                assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_feedback_history_with_filter(self, test_user, expert_profile):
        """Test feedback history with feedback_type filter."""
        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile query
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = expert_profile

            # Mock feedback query
            mock_feedback_result = MagicMock()
            mock_feedback_result.scalars.return_value.all.return_value = []

            # Mock count query
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0

            mock_db.execute.side_effect = [mock_expert_result, mock_count_result, mock_feedback_result]

            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/history?feedback_type=incomplete")

                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_feedback_history_invalid_filter(self, test_user, expert_profile):
        """Test feedback history with invalid feedback_type filter."""
        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile query
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = expert_profile
            mock_db.execute.return_value = mock_expert_result

            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/history?feedback_type=invalid")

                assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


class TestFeedbackDetail:
    """Tests for GET /api/v1/expert-feedback/{feedback_id} endpoint."""

    @pytest.fixture
    def client(self, test_user):
        """Test client fixture with dependency overrides."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = mock_get_db

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_feedback_detail_success(self, test_user, expert_profile, sample_feedback):
        """Test successful feedback detail retrieval."""
        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock feedback query
            mock_feedback_result = MagicMock()
            mock_feedback_result.scalar_one_or_none.return_value = sample_feedback

            # Mock expert profile query
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = expert_profile

            mock_db.execute.side_effect = [mock_feedback_result, mock_expert_result]

            with TestClient(app) as client:
                response = client.get(f"/api/v1/expert-feedback/{sample_feedback.id}")

                assert response.status_code == 200
                data = response.json()
                assert data["id"] == str(sample_feedback.id)
                assert data["feedback_type"] == "incomplete"
                assert data["generated_task_id"] == "DEV-BE-123"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_feedback_detail_not_found(self, test_user):
        """Test feedback detail retrieval with non-existent feedback."""
        fake_id = uuid4()

        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock feedback query - return None
            mock_feedback_result = MagicMock()
            mock_feedback_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_feedback_result

            with TestClient(app) as client:
                response = client.get(f"/api/v1/expert-feedback/{fake_id}")

                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_feedback_detail_unauthorized(self, test_user, expert_profile, sample_feedback):
        """Test feedback detail retrieval fails for unauthorized expert."""
        # Make feedback belong to different expert
        sample_feedback.expert_id = uuid4()

        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock feedback query
            mock_feedback_result = MagicMock()
            mock_feedback_result.scalar_one_or_none.return_value = sample_feedback

            # Mock expert profile query
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = expert_profile

            mock_db.execute.side_effect = [mock_feedback_result, mock_expert_result]

            with TestClient(app) as client:
                response = client.get(f"/api/v1/expert-feedback/{sample_feedback.id}")

                assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()


class TestExpertProfile:
    """Tests for GET /api/v1/expert-feedback/experts/me/profile endpoint."""

    @pytest.fixture
    def client(self, test_user):
        """Test client fixture with dependency overrides."""

        async def mock_get_db():
            return AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = mock_get_db

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_expert_profile_success(self, test_user, expert_profile):
        """Test successful expert profile retrieval."""
        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile query
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = expert_profile
            mock_db.execute.return_value = mock_expert_result

            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/experts/me/profile")

                assert response.status_code == 200
                data = response.json()
                assert data["id"] == str(expert_profile.id)
                assert data["trust_score"] == 0.92
                assert data["is_verified"] is True
                assert data["is_active"] is True
                assert "Dottore Commercialista" in data["credentials"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_expert_profile_not_found(self, test_user):
        """Test expert profile retrieval when user is not an expert."""
        # Create mock database
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile query - return None
            mock_expert_result = MagicMock()
            mock_expert_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_expert_result

            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/experts/me/profile")

                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
