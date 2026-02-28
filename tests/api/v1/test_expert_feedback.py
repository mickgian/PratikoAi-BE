"""Comprehensive tests for expert_feedback API router.

Covers all endpoints, branches, error paths, background tasks, and edge cases.
All external dependencies (DB, Redis, LLM, auth) are mocked.
Target: >= 90% code coverage of app/api/v1/expert_feedback.py

Tests cover:
- Router configuration: prefix, tags, routes, HTTP methods
- POST /submit: role validation, expert validation, verified/active checks,
  happy paths (correct/incorrect/incomplete), background task triggers,
  internal server errors
- GET /history: pagination, feedback_type filter, non-expert, invalid filter,
  pagination edge cases, internal server errors
- GET /{feedback_id}: found, not found, unauthorized, no expert profile,
  internal server errors
- GET /experts/me/profile: found, not found, internal server errors
- _trigger_golden_set_workflow: all branches (success, no candidate,
  not approved, no faq_id, import error, general exception)
- Schema validation edge cases
"""

import sys
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Pre-populate sys.modules to prevent real DB connection attempts at import.
# This MUST happen before any app module import.
# ---------------------------------------------------------------------------
if "app.services.database" not in sys.modules:
    _mock_db_module = MagicMock()
    _mock_db_module.database_service = MagicMock(is_connected=True)
    sys.modules["app.services.database"] = _mock_db_module

if "app.core.embed" not in sys.modules:
    _mock_embed = MagicMock()
    _mock_embed.generate_embedding = AsyncMock(return_value=None)
    _mock_embed.generate_embeddings_batch = AsyncMock(return_value=[])
    sys.modules["app.core.embed"] = _mock_embed

# Now safe to import application modules
from datetime import datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.auth import get_current_user
from app.api.v1.expert_feedback import _trigger_golden_set_workflow, router
from app.models.database import get_db
from app.models.user import UserRole

# ---------------------------------------------------------------------------
# Constants and helpers
# ---------------------------------------------------------------------------

MOCK_USER_ID = 42
MOCK_EXPERT_ID = uuid4()
MOCK_FEEDBACK_ID = uuid4()
MOCK_QUERY_ID = uuid4()


def _make_mock_user(role: str = UserRole.SUPER_USER.value, user_id: int = MOCK_USER_ID):
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id
    user.role = role
    user.email = "expert@test.com"
    return user


def _make_mock_expert(
    expert_id: UUID = MOCK_EXPERT_ID,
    user_id: int = MOCK_USER_ID,
    is_active: bool = True,
    is_verified: bool = True,
    trust_score: float = 0.85,
):
    """Create a mock ExpertProfile object."""
    expert = MagicMock()
    expert.id = expert_id
    expert.user_id = user_id
    expert.is_active = is_active
    expert.is_verified = is_verified
    expert.trust_score = trust_score
    expert.credentials = ["Dottore Commercialista"]
    expert.credential_types = ["dottore_commercialista"]
    expert.experience_years = 10
    expert.specializations = ["diritto_tributario"]
    expert.feedback_count = 50
    expert.feedback_accuracy_rate = 0.92
    expert.average_response_time_seconds = 200
    expert.professional_registration_number = "AA123"
    expert.organization = "Studio Test"
    expert.location_city = "Milano"
    expert.verification_date = datetime(2024, 1, 15)
    return expert


def _make_mock_feedback(
    feedback_id: UUID = MOCK_FEEDBACK_ID,
    expert_id: UUID = MOCK_EXPERT_ID,
    query_id: UUID = MOCK_QUERY_ID,
    feedback_type: str = "correct",
):
    """Create a mock ExpertFeedback object."""
    fb = MagicMock()
    fb.id = feedback_id
    fb.query_id = query_id
    fb.expert_id = expert_id
    fb.feedback_type = feedback_type
    fb.category = None
    fb.query_text = "Come si calcola l'IVA?"
    fb.original_answer = "L'IVA si calcola applicando..."
    fb.expert_answer = None
    fb.improvement_suggestions = []
    fb.regulatory_references = []
    fb.confidence_score = 0.9
    fb.time_spent_seconds = 120
    fb.complexity_rating = 3
    fb.additional_details = None
    fb.feedback_timestamp = datetime(2025, 1, 15, 10, 0)
    fb.generated_task_id = None
    fb.generated_faq_id = None
    fb.task_creation_attempted = False
    fb.task_creation_success = None
    fb.task_creation_error = None
    fb.action_taken = None
    fb.improvement_applied = False
    return fb


def _make_submission_json(
    feedback_type="correct",
    query_text="Come si calcola l'IVA?",
    original_answer="L'IVA si applica al 22%",
    confidence_score=0.9,
    time_spent_seconds=120,
    **extra,
):
    """Build a valid submission JSON payload."""
    payload = {
        "query_id": str(uuid4()),
        "feedback_type": feedback_type,
        "query_text": query_text,
        "original_answer": original_answer,
        "confidence_score": confidence_score,
        "time_spent_seconds": time_spent_seconds,
    }
    payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create a FastAPI app with the expert-feedback router."""
    _app = FastAPI()
    _app.include_router(router)
    return _app


@pytest.fixture
def mock_db():
    """Create a mock async DB session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a SUPER_USER mock."""
    return _make_mock_user()


@pytest.fixture
def mock_expert():
    """Create an active, verified expert profile mock."""
    return _make_mock_expert()


@pytest.fixture
def client(app, mock_db, mock_user):
    """Create an async test client tuple with overridden dependencies."""

    async def override_get_db():
        yield mock_db

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return app, mock_db, mock_user


# ---------------------------------------------------------------------------
# Router configuration
# ---------------------------------------------------------------------------


class TestRouterConfiguration:
    """Tests for router setup."""

    def test_router_prefix(self):
        assert router.prefix == "/expert-feedback"

    def test_router_tags(self):
        assert "Expert Feedback" in router.tags

    def test_submit_route_exists(self):
        paths = [route.path for route in router.routes]
        assert any("/submit" in p for p in paths)

    def test_history_route_exists(self):
        paths = [route.path for route in router.routes]
        assert any("/history" in p for p in paths)

    def test_detail_route_exists(self):
        paths = [route.path for route in router.routes]
        assert any("{feedback_id}" in p for p in paths)

    def test_profile_route_exists(self):
        paths = [route.path for route in router.routes]
        assert any("/experts/me/profile" in p for p in paths)

    def test_route_methods(self):
        route_methods = {}
        for route in router.routes:
            if hasattr(route, "methods"):
                route_methods[route.path] = route.methods

        # Router paths may include the prefix
        submit_key = next((p for p in route_methods if "/submit" in p), None)
        history_key = next((p for p in route_methods if "/history" in p), None)
        detail_key = next((p for p in route_methods if "{feedback_id}" in p), None)
        profile_key = next((p for p in route_methods if "/experts/me/profile" in p), None)

        assert submit_key is not None and "POST" in route_methods[submit_key]
        assert history_key is not None and "GET" in route_methods[history_key]
        assert detail_key is not None and "GET" in route_methods[detail_key]
        assert profile_key is not None and "GET" in route_methods[profile_key]


# ---------------------------------------------------------------------------
# POST /submit
# ---------------------------------------------------------------------------


class TestSubmitFeedback:
    """Tests for POST /expert-feedback/submit."""

    @pytest.mark.asyncio
    async def test_submit_regular_user_forbidden(self, client):
        """Regular users cannot submit feedback (403)."""
        app, mock_db, mock_user = client
        mock_user.role = UserRole.REGULAR_USER.value

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/expert-feedback/submit", json=_make_submission_json())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_submit_expert_role_forbidden(self, client):
        """EXPERT role (not SUPER_USER) cannot submit feedback (403)."""
        app, mock_db, mock_user = client
        mock_user.role = UserRole.EXPERT.value

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/expert-feedback/submit", json=_make_submission_json())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_submit_no_expert_profile_forbidden(self, client):
        """User with no expert profile gets 403."""
        app, mock_db, _ = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/expert-feedback/submit", json=_make_submission_json())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_submit_inactive_expert_forbidden(self, client):
        """Inactive expert gets 403."""
        app, mock_db, _ = client
        expert = _make_mock_expert(is_active=False, is_verified=True)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/expert-feedback/submit", json=_make_submission_json())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_submit_unverified_expert_forbidden(self, client):
        """Unverified expert gets 403."""
        app, mock_db, _ = client
        expert = _make_mock_expert(is_active=True, is_verified=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/expert-feedback/submit", json=_make_submission_json())
        assert resp.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.ExpertFeedback")
    async def test_submit_success_correct_feedback(self, mock_feedback_cls, client):
        """Successful 'correct' feedback returns 201 and triggers golden set."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        mock_fb = _make_mock_feedback(feedback_type="correct")
        mock_fb.task_creation_attempted = True
        mock_feedback_cls.return_value = mock_fb

        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/expert-feedback/submit", json=_make_submission_json("correct"))
        assert resp.status_code == 201
        data = resp.json()
        assert data["feedback_type"] == "correct"
        assert data["message"] == "Feedback submitted successfully"

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.ExpertFeedback")
    async def test_submit_success_incorrect_with_details(self, mock_feedback_cls, client):
        """Incorrect feedback with additional_details triggers task generation."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        mock_fb = _make_mock_feedback(feedback_type="incorrect")
        mock_fb.additional_details = "This is wrong because..."
        mock_fb.task_creation_attempted = True
        mock_feedback_cls.return_value = mock_fb

        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("app.api.v1.expert_feedback.asyncio.create_task"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post(
                    "/expert-feedback/submit",
                    json=_make_submission_json(
                        "incorrect",
                        additional_details="This is wrong because...",
                    ),
                )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.ExpertFeedback")
    async def test_submit_success_incomplete_with_details(self, mock_feedback_cls, client):
        """Incomplete feedback with additional_details triggers task generation."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        mock_fb = _make_mock_feedback(feedback_type="incomplete")
        mock_fb.additional_details = "Missing case X"
        mock_fb.task_creation_attempted = True
        mock_feedback_cls.return_value = mock_fb

        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("app.api.v1.expert_feedback.asyncio.create_task"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post(
                    "/expert-feedback/submit",
                    json=_make_submission_json(
                        "incomplete",
                        additional_details="Missing case X",
                    ),
                )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.ExpertFeedback")
    async def test_submit_incomplete_without_details_no_task(self, mock_feedback_cls, client):
        """Incomplete feedback WITHOUT additional_details does NOT trigger task."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        mock_fb = _make_mock_feedback(feedback_type="incomplete")
        mock_fb.additional_details = None
        mock_fb.task_creation_attempted = False
        mock_feedback_cls.return_value = mock_fb

        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json("incomplete"),
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_submit_admin_role_allowed(self, client):
        """Admin users can submit feedback."""
        app, mock_db, mock_user = client
        mock_user.role = UserRole.ADMIN.value
        expert = _make_mock_expert()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("app.api.v1.expert_feedback.ExpertFeedback") as mock_fb_cls:
            mock_fb = _make_mock_feedback()
            mock_fb_cls.return_value = mock_fb

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post("/expert-feedback/submit", json=_make_submission_json())
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_submit_invalid_feedback_type(self, client):
        """Invalid feedback_type in body returns 422."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(feedback_type="invalid_type"),
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.ExpertFeedback")
    async def test_submit_internal_error(self, mock_feedback_cls, client):
        """Internal error during submit returns 500."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        # Make ExpertFeedback constructor raise
        mock_feedback_cls.side_effect = RuntimeError("Internal error")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/expert-feedback/submit", json=_make_submission_json())
        assert resp.status_code == 500

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.ExpertFeedback")
    async def test_submit_with_category(self, mock_feedback_cls, client):
        """Submit with valid Italian category."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        mock_fb = _make_mock_feedback()
        mock_feedback_cls.return_value = mock_fb

        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(category="calcolo_sbagliato"),
            )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# GET /history
# ---------------------------------------------------------------------------


class TestGetFeedbackHistory:
    """Tests for GET /expert-feedback/history."""

    @pytest.mark.asyncio
    async def test_history_non_expert_forbidden(self, client):
        """Non-expert user gets 403."""
        app, mock_db, _ = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/history")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_history_success(self, client):
        """Expert user gets feedback history."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = expert

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        feedback_result = MagicMock()
        feedback_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[expert_result, count_result, feedback_result])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_history_with_items(self, client):
        """History returns actual feedback records."""
        app, mock_db, _ = client
        expert = _make_mock_expert()
        fb = _make_mock_feedback()

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = expert

        count_result = MagicMock()
        count_result.scalar.return_value = 1

        feedback_result = MagicMock()
        feedback_result.scalars.return_value.all.return_value = [fb]

        mock_db.execute = AsyncMock(side_effect=[expert_result, count_result, feedback_result])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_history_with_valid_feedback_type_filter(self, client):
        """Filter by valid feedback_type returns filtered results."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = expert

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        feedback_result = MagicMock()
        feedback_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[expert_result, count_result, feedback_result])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/history?feedback_type=correct")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_history_invalid_feedback_type_filter(self, client):
        """Invalid feedback_type filter returns 422."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/history?feedback_type=invalid_value")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_history_pagination_limit_capped(self, client):
        """Limit >100 is capped to 100."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = expert

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        feedback_result = MagicMock()
        feedback_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[expert_result, count_result, feedback_result])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/history?limit=500")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 100

    @pytest.mark.asyncio
    async def test_history_pagination_limit_below_one(self, client):
        """Limit <1 is reset to 20."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = expert

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        feedback_result = MagicMock()
        feedback_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[expert_result, count_result, feedback_result])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/history?limit=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 20

    @pytest.mark.asyncio
    async def test_history_negative_offset(self, client):
        """Negative offset is reset to 0."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = expert

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        feedback_result = MagicMock()
        feedback_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[expert_result, count_result, feedback_result])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/history?offset=-5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_history_internal_error(self, client):
        """Internal error returns 500."""
        app, mock_db, _ = client
        expert = _make_mock_expert()

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = expert

        mock_db.execute = AsyncMock(side_effect=[expert_result, RuntimeError("DB crash")])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/history")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /{feedback_id}
# ---------------------------------------------------------------------------


class TestGetFeedbackDetail:
    """Tests for GET /expert-feedback/{feedback_id}."""

    @pytest.mark.asyncio
    async def test_detail_not_found(self, client):
        """Non-existent feedback returns 404."""
        app, mock_db, _ = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/expert-feedback/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_detail_unauthorized(self, client):
        """User who is not the feedback owner gets 403."""
        app, mock_db, _ = client
        feedback = _make_mock_feedback()

        other_expert = _make_mock_expert(expert_id=uuid4())

        feedback_result = MagicMock()
        feedback_result.scalar_one_or_none.return_value = feedback

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = other_expert

        mock_db.execute = AsyncMock(side_effect=[feedback_result, expert_result])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/expert-feedback/{feedback.id}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_detail_no_expert_profile(self, client):
        """User without expert profile gets 403."""
        app, mock_db, _ = client
        feedback = _make_mock_feedback()

        feedback_result = MagicMock()
        feedback_result.scalar_one_or_none.return_value = feedback

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[feedback_result, expert_result])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/expert-feedback/{feedback.id}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_detail_success(self, client):
        """Owner can view their own feedback detail."""
        app, mock_db, _ = client
        feedback = _make_mock_feedback()
        expert = _make_mock_expert(expert_id=feedback.expert_id)

        feedback_result = MagicMock()
        feedback_result.scalar_one_or_none.return_value = feedback

        expert_result = MagicMock()
        expert_result.scalar_one_or_none.return_value = expert

        mock_db.execute = AsyncMock(side_effect=[feedback_result, expert_result])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/expert-feedback/{feedback.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(feedback.id)
        assert data["feedback_type"] == "correct"
        assert data["improvement_applied"] is False

    @pytest.mark.asyncio
    async def test_detail_internal_error(self, client):
        """Internal error returns 500."""
        app, mock_db, _ = client

        mock_db.execute = AsyncMock(side_effect=RuntimeError("DB crash"))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/expert-feedback/{uuid4()}")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /experts/me/profile
# ---------------------------------------------------------------------------


class TestGetExpertProfile:
    """Tests for GET /expert-feedback/experts/me/profile."""

    @pytest.mark.asyncio
    async def test_profile_not_found(self, client):
        """User without expert profile gets 404."""
        app, mock_db, _ = client

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/experts/me/profile")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_profile_success(self, client):
        """Expert gets their profile successfully."""
        app, mock_db, mock_user = client
        expert = _make_mock_expert(user_id=mock_user.id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expert
        mock_db.execute.return_value = mock_result

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/experts/me/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == mock_user.id
        assert data["trust_score"] == expert.trust_score
        assert data["is_verified"] is True
        assert data["credentials"] == ["Dottore Commercialista"]

    @pytest.mark.asyncio
    async def test_profile_internal_error(self, client):
        """Internal error returns 500."""
        app, mock_db, _ = client

        mock_db.execute = AsyncMock(side_effect=RuntimeError("DB crash"))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/experts/me/profile")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# _trigger_golden_set_workflow tests
# ---------------------------------------------------------------------------


class TestTriggerGoldenSetWorkflow:
    """Tests for the background Golden Set workflow function."""

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_success(self, mock_session_local):
        """Full success: feedback -> candidate -> approved -> published."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": {"priority_score": 0.9}})
        mock_s128 = AsyncMock(return_value={"approval_decision": {"status": "auto_approved"}})
        mock_s129 = AsyncMock(return_value={"published_faq": {"id": "faq-123"}, "version": "1.0"})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                    step_128__golden_approval=mock_s128,
                    step_129__publish_golden=mock_s129,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.generated_faq_id == "faq-123"
        assert mock_feedback.task_creation_success is True

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_feedback_not_found(self, mock_session_local):
        """If feedback not found, returns early."""
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await _trigger_golden_set_workflow(uuid4(), uuid4())

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_user_not_found(self, mock_session_local):
        """If user not found, returns early."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, None])

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        await _trigger_golden_set_workflow(feedback_id, expert_id)

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_no_candidate(self, mock_session_local):
        """S127 produces no candidate -> sets task_creation_success=False."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": None})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.task_creation_success is False

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_not_approved(self, mock_session_local):
        """S128 returns 'pending_review' -> sets task_creation_success=False."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": {"priority_score": 0.5}})
        mock_s128 = AsyncMock(return_value={"approval_decision": {"status": "pending_review"}})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                    step_128__golden_approval=mock_s128,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.task_creation_success is False

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_import_error(self, mock_session_local):
        """ImportError of golden orchestrator is handled gracefully."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch.dict("sys.modules", {"app.orchestrators.golden": None}):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.task_creation_success is False
        assert "Import error" in str(mock_feedback.task_creation_error)

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_general_exception(self, mock_session_local):
        """General exception is handled gracefully."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_golden = MagicMock()
        mock_golden.step_127__golden_candidate = AsyncMock(side_effect=RuntimeError("Workflow crash"))

        with patch.dict("sys.modules", {"app.orchestrators.golden": mock_golden}):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.task_creation_success is False
        assert "Workflow crash" in str(mock_feedback.task_creation_error)


# ---------------------------------------------------------------------------
# Schema validation edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Additional edge case and schema validation tests."""

    @pytest.mark.asyncio
    async def test_submit_missing_required_fields(self, client):
        """Missing required fields returns 422."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/expert-feedback/submit", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_confidence_out_of_range(self, client):
        """Confidence score outside 0.0-1.0 returns 422."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(confidence_score=1.5),
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_negative_confidence(self, client):
        """Negative confidence score returns 422."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(confidence_score=-0.1),
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_negative_time_spent(self, client):
        """Negative time_spent_seconds returns 422."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(time_spent_seconds=-1),
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_zero_time_spent(self, client):
        """Zero time_spent_seconds returns 422 (must be >0)."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(time_spent_seconds=0),
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_placeholder_query_text_rejected(self, client):
        """Placeholder query_text values are rejected with 422."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(query_text="[Domanda precedente dell'utente]"),
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_invalid_category(self, client):
        """Invalid category returns 422."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(category="not_a_valid_category"),
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_detail_invalid_uuid_format(self, client):
        """Invalid UUID in path returns 422."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/expert-feedback/not-a-valid-uuid")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_complexity_out_of_range(self, client):
        """Complexity rating outside 1-5 returns 422."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(complexity_rating=6),
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_complexity_zero(self, client):
        """Complexity rating of 0 returns 422 (must be >= 1)."""
        app, _, _ = client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/expert-feedback/submit",
                json=_make_submission_json(complexity_rating=0),
            )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Additional coverage tests for remaining uncovered branches
# ---------------------------------------------------------------------------


class TestGoldenWorkflowAdditionalBranches:
    """Tests for uncovered branches in _trigger_golden_set_workflow."""

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_approval_decision_as_string(self, mock_session_local):
        """approval_decision as string (not dict) is handled correctly (lines 132-133)."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user_obj = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user_obj])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": {"priority_score": 0.9}})
        # approval_decision is a string "auto_approved" instead of a dict
        mock_s128 = AsyncMock(return_value={"approval_decision": "auto_approved"})
        mock_s129 = AsyncMock(return_value={"published_faq": {"id": "faq-str-approved"}, "version": "2.0"})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                    step_128__golden_approval=mock_s128,
                    step_129__publish_golden=mock_s129,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.generated_faq_id == "faq-str-approved"
        assert mock_feedback.task_creation_success is True

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_approval_decision_as_string_not_approved(self, mock_session_local):
        """approval_decision as string 'pending_review' is not approved (lines 132-133 + 137-141)."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user_obj = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user_obj])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": {"priority_score": 0.5}})
        # approval_decision is a string but not an approved status
        mock_s128 = AsyncMock(return_value={"approval_decision": "rejected"})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                    step_128__golden_approval=mock_s128,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.task_creation_success is False

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_approval_decision_unexpected_type(self, mock_session_local):
        """approval_decision as unexpected type (e.g. int) sets approval_status=None (lines 134-135)."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user_obj = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user_obj])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": {"priority_score": 0.7}})
        # approval_decision is an integer - neither dict nor string
        mock_s128 = AsyncMock(return_value={"approval_decision": 42})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                    step_128__golden_approval=mock_s128,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        # None is not in ["auto_approved", "manual_approved"], so not approved
        assert mock_feedback.task_creation_success is False

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_approval_decision_list_type(self, mock_session_local):
        """approval_decision as list type falls to else branch (lines 134-135)."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user_obj = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user_obj])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": {"priority_score": 0.6}})
        # approval_decision is a list - neither dict nor string
        mock_s128 = AsyncMock(return_value={"approval_decision": ["auto_approved"]})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                    step_128__golden_approval=mock_s128,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.task_creation_success is False

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_no_faq_id_in_published(self, mock_session_local):
        """S129 publishes but returned FAQ has no 'id' -> task_creation_success=False (lines 166-168)."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user_obj = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user_obj])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": {"priority_score": 0.9}})
        mock_s128 = AsyncMock(return_value={"approval_decision": {"status": "manual_approved"}})
        # published_faq is a dict but has no 'id' key
        mock_s129 = AsyncMock(return_value={"published_faq": {"status": "created"}})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                    step_128__golden_approval=mock_s128,
                    step_129__publish_golden=mock_s129,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.task_creation_success is False

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_published_faq_not_dict(self, mock_session_local):
        """S129 returns published_faq as non-dict -> faq_id is None (lines 151, 166-168)."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user_obj = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user_obj])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": {"priority_score": 0.9}})
        mock_s128 = AsyncMock(return_value={"approval_decision": {"status": "auto_approved"}})
        # published_faq is a string, not a dict
        mock_s129 = AsyncMock(return_value={"published_faq": "some-string-value"})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                    step_128__golden_approval=mock_s128,
                    step_129__publish_golden=mock_s129,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.task_creation_success is False

    @pytest.mark.asyncio
    @patch("app.api.v1.expert_feedback.AsyncSessionLocal")
    async def test_golden_workflow_manual_approved_string(self, mock_session_local):
        """approval_decision as string 'manual_approved' is accepted (lines 132-133)."""
        feedback_id = uuid4()
        expert_id = uuid4()

        mock_db = AsyncMock()
        mock_feedback = _make_mock_feedback(feedback_id=feedback_id)
        mock_expert = _make_mock_expert(expert_id=expert_id)
        mock_user_obj = _make_mock_user()

        mock_db.get = AsyncMock(side_effect=[mock_feedback, mock_expert, mock_user_obj])
        mock_db.commit = AsyncMock()

        mock_session_local.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_s127 = AsyncMock(return_value={"faq_candidate": {"priority_score": 0.8}})
        # approval_decision as string "manual_approved"
        mock_s128 = AsyncMock(return_value={"approval_decision": "manual_approved"})
        mock_s129 = AsyncMock(return_value={"published_faq": {"id": "faq-manual"}, "version": "3.0"})

        with patch.dict(
            "sys.modules",
            {
                "app.orchestrators.golden": MagicMock(
                    step_127__golden_candidate=mock_s127,
                    step_128__golden_approval=mock_s128,
                    step_129__publish_golden=mock_s129,
                ),
            },
        ):
            await _trigger_golden_set_workflow(feedback_id, expert_id)

        assert mock_feedback.generated_faq_id == "faq-manual"
        assert mock_feedback.task_creation_success is True
