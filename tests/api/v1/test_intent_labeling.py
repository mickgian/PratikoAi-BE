"""Integration tests for DEV-253: Intent Labeling API endpoints.

Tests all API endpoints for the Intent Labeling System:
- GET /api/v1/labeling/queue
- POST /api/v1/labeling/label
- GET /api/v1/labeling/stats
- GET /api/v1/labeling/export
- POST /api/v1/labeling/skip/{id}

Access control (DEV-253c): Only SUPER_USER or ADMIN with a verified,
active ExpertProfile can access labeling endpoints.

NOTE: Skipped in CI - TestClient(app) triggers slow app startup.
"""

import os

import pytest

# Skip in CI - TestClient(app) triggers slow app startup
if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
    pytest.skip(
        "Intent labeling API tests require full app infrastructure - skipped in CI",
        allow_module_level=True,
    )

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.database import get_db
from app.models.user import UserRole


def create_mock_db():
    """Create a properly configured mock database session."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.rollback = AsyncMock()
    return mock_db


def create_mock_expert_profile(*, is_active: bool = True, is_verified: bool = True):
    """Create a mock ExpertProfile with configurable status."""
    expert = MagicMock()
    expert.is_active = is_active
    expert.is_verified = is_verified
    expert.user_id = 1
    return expert


def mock_expert_profile_result(expert_profile):
    """Create a mock db.execute result that returns an ExpertProfile."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expert_profile
    return mock_result


@pytest.fixture
def super_user():
    """Super user fixture with SUPER_USER role (valid for labeling)."""
    user = MagicMock()
    user.id = 1
    user.email = "superuser@test.com"
    user.is_active = True
    user.role = UserRole.SUPER_USER.value
    return user


@pytest.fixture
def expert_user():
    """Expert user fixture with EXPERT role (no longer valid for labeling)."""
    user = MagicMock()
    user.id = 1
    user.email = "expert@test.com"
    user.is_active = True
    user.role = UserRole.EXPERT.value
    return user


@pytest.fixture
def admin_user():
    """Admin user fixture."""
    user = MagicMock()
    user.id = 2
    user.email = "admin@test.com"
    user.is_active = True
    user.role = UserRole.ADMIN.value
    return user


@pytest.fixture
def regular_user():
    """Regular user fixture (not expert/admin)."""
    user = MagicMock()
    user.id = 3
    user.email = "regular@test.com"
    user.is_active = True
    user.role = UserRole.REGULAR_USER.value
    return user


@pytest.fixture
def sample_labeled_query():
    """Sample LabeledQuery record for testing."""
    query = MagicMock()
    query.id = uuid4()
    query.query = "Come si calcola l'IVA per il regime forfettario?"
    query.predicted_intent = "technical_research"
    query.confidence = 0.45
    query.all_scores = {
        "technical_research": 0.45,
        "theoretical_definition": 0.30,
        "calculator": 0.15,
        "chitchat": 0.05,
        "normative_reference": 0.05,
    }
    query.expert_intent = None
    query.labeled_by = None
    query.labeled_at = None
    query.labeling_notes = None
    query.source_query_id = uuid4()
    query.is_deleted = False
    query.skip_count = 0
    query.created_at = datetime.utcnow()
    return query


class TestAccessControl:
    """Tests for DEV-253c: Verified expert access control."""

    @pytest.mark.asyncio
    async def test_expert_role_without_superuser_403(self, expert_user):
        """EXPERT role alone should be rejected (must be SUPER_USER or ADMIN)."""
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: expert_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/queue")

                assert response.status_code == 403
                assert "Accesso non autorizzato" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unverified_expert_403(self, super_user):
        """SUPER_USER with unverified expert profile should be rejected."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile(is_verified=False)

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        mock_db.execute.return_value = mock_expert_profile_result(expert_profile)

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/queue")

                assert response.status_code == 403
                assert "non attivo o non verificato" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_inactive_expert_403(self, super_user):
        """SUPER_USER with inactive expert profile should be rejected."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile(is_active=False)

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        mock_db.execute.return_value = mock_expert_profile_result(expert_profile)

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/queue")

                assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_no_expert_profile_403(self, super_user):
        """SUPER_USER with no expert profile should be rejected."""
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        # No expert profile found
        mock_db.execute.return_value = mock_expert_profile_result(None)

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/queue")

                assert response.status_code == 403
                assert "non trovato" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unauthorized_user_403(self, regular_user):
        """Regular users should not be able to access labeling endpoints."""
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: regular_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/labeling/label",
                    json={
                        "query_id": str(uuid4()),
                        "expert_intent": "chitchat",
                    },
                )

                assert response.status_code == 403
                assert "Accesso non autorizzato" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


class TestLabelingQueue:
    """Tests for GET /api/v1/labeling/queue endpoint."""

    @pytest.mark.asyncio
    async def test_labeling_queue_returns_low_confidence_first(self, super_user, sample_labeled_query):
        """Queue should return queries ordered by confidence (lowest first)."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Create queries with different confidence levels
            query_low = MagicMock()
            query_low.id = uuid4()
            query_low.query = "Low confidence query"
            query_low.predicted_intent = "technical_research"
            query_low.confidence = 0.35
            query_low.all_scores = {"technical_research": 0.35}
            query_low.expert_intent = None
            query_low.created_at = datetime.utcnow()

            query_medium = MagicMock()
            query_medium.id = uuid4()
            query_medium.query = "Medium confidence query"
            query_medium.predicted_intent = "calculator"
            query_medium.confidence = 0.55
            query_medium.all_scores = {"calculator": 0.55}
            query_medium.expert_intent = None
            query_medium.created_at = datetime.utcnow()

            # Mock expert profile check + count + query results
            mock_count = MagicMock()
            mock_count.scalar.return_value = 2

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [query_low, query_medium]

            mock_db.execute.side_effect = [
                mock_expert_profile_result(expert_profile),
                mock_count,
                mock_result,
            ]

            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/queue")

                assert response.status_code == 200
                data = response.json()
                assert data["total_count"] == 2
                assert len(data["items"]) == 2
                # First item should have lowest confidence
                assert data["items"][0]["confidence"] == 0.35
                assert data["items"][1]["confidence"] == 0.55
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_labeling_queue_excludes_already_labeled(self, super_user, sample_labeled_query):
        """Queue should only return unlabeled queries."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Only unlabeled query
            unlabeled_query = MagicMock()
            unlabeled_query.id = uuid4()
            unlabeled_query.query = "Unlabeled query"
            unlabeled_query.predicted_intent = "chitchat"
            unlabeled_query.confidence = 0.45
            unlabeled_query.all_scores = {"chitchat": 0.45}
            unlabeled_query.expert_intent = None  # Not labeled
            unlabeled_query.created_at = datetime.utcnow()

            mock_count = MagicMock()
            mock_count.scalar.return_value = 1

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [unlabeled_query]

            mock_db.execute.side_effect = [
                mock_expert_profile_result(expert_profile),
                mock_count,
                mock_result,
            ]

            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/queue")

                assert response.status_code == 200
                data = response.json()
                # Should only include unlabeled queries
                for item in data["items"]:
                    assert item["expert_intent"] is None
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_labeling_queue_pagination(self, super_user):
        """Queue should support pagination."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock total count
            mock_count = MagicMock()
            mock_count.scalar.return_value = 100

            # Mock page 2 results
            mock_queries = [
                MagicMock(
                    id=uuid4(),
                    query=f"Query {i}",
                    predicted_intent="technical_research",
                    confidence=0.5,
                    all_scores={"technical_research": 0.5},
                    expert_intent=None,
                    created_at=datetime.utcnow(),
                )
                for i in range(10)
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_queries

            mock_db.execute.side_effect = [
                mock_expert_profile_result(expert_profile),
                mock_count,
                mock_result,
            ]

            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/queue?page=2&page_size=10")

                assert response.status_code == 200
                data = response.json()
                assert data["total_count"] == 100
                assert data["page"] == 2
                assert data["page_size"] == 10
                assert len(data["items"]) == 10
        finally:
            app.dependency_overrides.clear()


class TestLabelSubmission:
    """Tests for POST /api/v1/labeling/label endpoint."""

    @pytest.mark.asyncio
    async def test_label_submission_updates_database(self, super_user, sample_labeled_query):
        """Label submission should update the query with expert intent."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile check, then query lookup
            mock_query_result = MagicMock()
            mock_query_result.scalar_one_or_none.return_value = sample_labeled_query
            mock_db.execute.side_effect = [
                mock_expert_profile_result(expert_profile),
                mock_query_result,
            ]

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/labeling/label",
                    json={
                        "query_id": str(sample_labeled_query.id),
                        "expert_intent": "calculator",
                        "notes": "This is a calculation request",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["expert_intent"] == "calculator"
                assert data["labeled_by"] == super_user.id
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_not_found_404(self, super_user):
        """Should return 404 if query not found."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            mock_query_result = MagicMock()
            mock_query_result.scalar_one_or_none.return_value = None
            mock_db.execute.side_effect = [
                mock_expert_profile_result(expert_profile),
                mock_query_result,
            ]

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/labeling/label",
                    json={
                        "query_id": str(uuid4()),
                        "expert_intent": "chitchat",
                    },
                )

                assert response.status_code == 404
                assert "Query non trovata" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invalid_intent_returns_400(self, super_user, sample_labeled_query):
        """Invalid intent should return 400."""
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/labeling/label",
                    json={
                        "query_id": str(sample_labeled_query.id),
                        "expert_intent": "invalid_intent",
                    },
                )

                assert response.status_code == 422  # Pydantic validation error
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_concurrent_labeling_last_write_wins(self, super_user, admin_user, sample_labeled_query):
        """Concurrent labeling should use last-write-wins strategy."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile()
        admin_expert_profile = create_mock_expert_profile()
        admin_expert_profile.user_id = admin_user.id

        async def get_mock_db():
            return mock_db

        # First submission by super_user
        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            mock_query_result = MagicMock()
            mock_query_result.scalar_one_or_none.return_value = sample_labeled_query
            mock_db.execute.side_effect = [
                mock_expert_profile_result(expert_profile),
                mock_query_result,
            ]

            with TestClient(app) as client:
                response1 = client.post(
                    "/api/v1/labeling/label",
                    json={
                        "query_id": str(sample_labeled_query.id),
                        "expert_intent": "calculator",
                    },
                )
                assert response1.status_code == 200

            # Update to already labeled
            sample_labeled_query.expert_intent = "calculator"
            sample_labeled_query.labeled_by = super_user.id

            # Second submission by admin (should overwrite)
            app.dependency_overrides[get_current_user] = lambda: admin_user

            mock_query_result2 = MagicMock()
            mock_query_result2.scalar_one_or_none.return_value = sample_labeled_query
            mock_db.execute.side_effect = [
                mock_expert_profile_result(admin_expert_profile),
                mock_query_result2,
            ]

            with TestClient(app) as client:
                response2 = client.post(
                    "/api/v1/labeling/label",
                    json={
                        "query_id": str(sample_labeled_query.id),
                        "expert_intent": "chitchat",
                        "notes": "Correcting previous label",
                    },
                )
                assert response2.status_code == 200
                data = response2.json()
                assert data["expert_intent"] == "chitchat"
                assert data["labeled_by"] == admin_user.id
        finally:
            app.dependency_overrides.clear()


class TestLabelingStats:
    """Tests for GET /api/v1/labeling/stats endpoint."""

    @pytest.mark.asyncio
    async def test_stats_returns_progress(self, super_user):
        """Stats endpoint should return labeling progress."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock expert profile check + count queries + new_since_export
            mock_total = MagicMock()
            mock_total.scalar.return_value = 100

            mock_labeled = MagicMock()
            mock_labeled.scalar.return_value = 45

            mock_new_since = MagicMock()
            mock_new_since.scalar.return_value = 15

            mock_db.execute.side_effect = [
                mock_expert_profile_result(expert_profile),
                mock_total,
                mock_labeled,
                mock_new_since,
            ]

            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/stats")

                assert response.status_code == 200
                data = response.json()
                assert data["total_queries"] == 100
                assert data["labeled_queries"] == 45
                assert data["pending_queries"] == 55
                assert data["completion_percentage"] == 45.0
                assert data["new_since_export"] == 15
        finally:
            app.dependency_overrides.clear()


class TestLabelingExport:
    """Tests for GET /api/v1/labeling/export endpoint."""

    @pytest.mark.asyncio
    async def test_export_jsonl(self, admin_user):
        """Export should return JSONL format."""
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            # Mock labeled queries
            mock_queries = [
                MagicMock(
                    id=uuid4(),
                    query="Test query",
                    expert_intent="chitchat",
                    confidence=0.45,
                    labeled_at=datetime.utcnow(),
                ),
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_queries
            mock_db.execute.return_value = mock_result

            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/export?format=jsonl")

                assert response.status_code == 200
                assert "application/x-ndjson" in response.headers["content-type"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_requires_admin(self, expert_user):
        """Export should only be accessible to admins."""
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: expert_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/export")

                # Experts cannot export, only admins
                assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_marks_records_with_exported_at(self, admin_user):
        """Export should stamp exported_at on all exported records."""
        mock_db = create_mock_db()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            mock_queries = [
                MagicMock(
                    id=uuid4(),
                    query="Test query",
                    expert_intent="chitchat",
                    confidence=0.45,
                    labeled_at=datetime.utcnow(),
                    exported_at=None,
                ),
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_queries
            # First call: SELECT queries, second call: UPDATE exported_at
            mock_db.execute.side_effect = [mock_result, MagicMock()]

            with TestClient(app) as client:
                response = client.get("/api/v1/labeling/export?format=jsonl")

                assert response.status_code == 200
                # Verify the bulk UPDATE was executed (second execute call)
                assert mock_db.execute.call_count == 2
                mock_db.commit.assert_called_once()
        finally:
            app.dependency_overrides.clear()


class TestSkipQuery:
    """Tests for POST /api/v1/labeling/skip/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_skip_increments_count(self, super_user, sample_labeled_query):
        """Skip should increment skip_count."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            mock_query_result = MagicMock()
            mock_query_result.scalar_one_or_none.return_value = sample_labeled_query
            mock_db.execute.side_effect = [
                mock_expert_profile_result(expert_profile),
                mock_query_result,
            ]

            with TestClient(app) as client:
                response = client.post(f"/api/v1/labeling/skip/{sample_labeled_query.id}")

                assert response.status_code == 200
                assert sample_labeled_query.skip_count == 1
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_skip_not_found_404(self, super_user):
        """Skip should return 404 if query not found."""
        mock_db = create_mock_db()
        expert_profile = create_mock_expert_profile()

        async def get_mock_db():
            return mock_db

        app.dependency_overrides[get_current_user] = lambda: super_user
        app.dependency_overrides[get_db] = get_mock_db

        try:
            mock_query_result = MagicMock()
            mock_query_result.scalar_one_or_none.return_value = None
            mock_db.execute.side_effect = [
                mock_expert_profile_result(expert_profile),
                mock_query_result,
            ]

            with TestClient(app) as client:
                response = client.post(f"/api/v1/labeling/skip/{uuid4()}")

                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
