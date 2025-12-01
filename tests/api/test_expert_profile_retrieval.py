"""Tests for expert profile retrieval API endpoint.

These tests validate that expert profile data is correctly serialized to JSON,
especially enum fields that must be converted from Python enums to string values.

BUGS THIS WOULD HAVE CAUGHT:
- Bug #8: Enum deserialization (reading credential_types array from database and serializing to JSON)
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.database import AsyncSessionLocal
from app.models.quality_analysis import ExpertCredentialType, ExpertProfile
from app.models.user import User, UserRole


@pytest.fixture
async def real_db():
    """Real database session for integration tests."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture
async def test_user(real_db):
    """Create test super user in database."""
    user = User(
        email=f"profile_test_{id(real_db)}@test.com",
        hashed_password="hashed",
        role=UserRole.SUPER_USER.value,
        name="Test Expert",
    )
    real_db.add(user)
    await real_db.commit()
    await real_db.refresh(user)
    return user


@pytest.fixture
async def test_expert(real_db, test_user):
    """Create test expert profile with multiple credential types."""
    expert = ExpertProfile(
        user_id=test_user.id,
        credentials=["Dottore Commercialista", "Revisore Legale"],
        credential_types=[
            ExpertCredentialType.DOTTORE_COMMERCIALISTA,
            ExpertCredentialType.REVISORE_LEGALE,
        ],
        experience_years=15,
        specializations=["diritto_tributario", "contabilità"],
        feedback_count=50,
        feedback_accuracy_rate=0.95,
        average_response_time_seconds=180,
        trust_score=0.88,
        professional_registration_number="AA123456",
        organization="Studio Test",
        location_city="Milano",
        is_verified=True,
        is_active=True,
    )
    real_db.add(expert)
    await real_db.commit()
    await real_db.refresh(expert)
    return expert


class TestExpertProfileRetrieval:
    """Test GET /api/v1/expert-feedback/experts/me/profile endpoint."""

    @pytest.mark.asyncio
    async def test_get_expert_profile_success(self, real_db, test_user, test_expert):
        """Test successful expert profile retrieval with enum deserialization (Bug #8)."""

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/experts/me/profile")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                # Verify basic fields
                assert data["id"] == str(test_expert.id)
                assert data["user_id"] == test_user.id
                assert data["role"] == UserRole.SUPER_USER.value

                # Verify enum deserialization (Bug #8)
                # credential_types should be list of strings (enum values), not enum objects
                assert isinstance(data["credential_types"], list)
                assert len(data["credential_types"]) == 2
                assert "dottore_commercialista" in data["credential_types"]
                assert "revisore_legale" in data["credential_types"]

                # Verify string credentials
                assert "Dottore Commercialista" in data["credentials"]
                assert "Revisore Legale" in data["credentials"]

                # Verify other fields
                assert data["experience_years"] == 15
                assert "diritto_tributario" in data["specializations"]
                assert data["feedback_count"] == 50
                assert data["trust_score"] == 0.88
                assert data["is_verified"] is True
                assert data["is_active"] is True
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_expert_profile_enum_array_values(self, real_db, test_user):
        """Test credential_types array enum serialization (Bug #8).

        This test specifically validates that ARRAY enums are correctly
        deserialized from database and serialized to JSON response.
        """
        # Create expert with all credential types
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[
                ExpertCredentialType.DOTTORE_COMMERCIALISTA,
                ExpertCredentialType.REVISORE_LEGALE,
                ExpertCredentialType.CONSULENTE_FISCALE,
                ExpertCredentialType.CONSULENTE_LAVORO,
                ExpertCredentialType.CAF_OPERATOR,
                ExpertCredentialType.ADMIN,
            ],
            is_verified=True,
            is_active=True,
        )
        real_db.add(expert)
        await real_db.commit()
        await real_db.refresh(expert)

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/experts/me/profile")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                # Verify all credential types are serialized as strings
                credential_types = data["credential_types"]
                assert len(credential_types) == 6
                assert "dottore_commercialista" in credential_types
                assert "revisore_legale" in credential_types
                assert "consulente_fiscale" in credential_types
                assert "consulente_lavoro" in credential_types
                assert "caf_operator" in credential_types
                assert "admin" in credential_types

                # Verify no enum objects leaked into JSON
                for cred_type in credential_types:
                    assert isinstance(cred_type, str)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_expert_profile_empty_credential_types(self, real_db, test_user):
        """Test profile with empty credential_types array."""
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[],  # Empty array
            is_verified=True,
            is_active=True,
        )
        real_db.add(expert)
        await real_db.commit()
        await real_db.refresh(expert)

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/experts/me/profile")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                assert data["credential_types"] == []
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_expert_profile_not_found(self, real_db, test_user):
        """Test profile retrieval when user has no expert profile."""

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/experts/me/profile")

                assert response.status_code == status.HTTP_404_NOT_FOUND
                assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_expert_profile_nullable_fields(self, real_db, test_user):
        """Test profile with nullable fields set to None."""
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[ExpertCredentialType.CONSULENTE_FISCALE],
            # All optional fields as None
            professional_registration_number=None,
            organization=None,
            location_city=None,
            verification_date=None,
            is_verified=True,
            is_active=True,
        )
        real_db.add(expert)
        await real_db.commit()
        await real_db.refresh(expert)

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/experts/me/profile")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                # Verify nullable fields are properly serialized as null
                assert data["professional_registration_number"] is None
                assert data["organization"] is None
                assert data["location_city"] is None
                assert data["verification_date"] is None
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_expert_profile_includes_user_role(self, real_db, test_expert):
        """Test that profile response includes user role (for frontend RBAC)."""
        # Test with different user roles
        test_cases = [
            (UserRole.REGULAR_USER, "regular_user"),
            (UserRole.SUPER_USER, "super_user"),
            (UserRole.ADMIN, "admin"),
        ]

        for role_enum, role_str in test_cases:
            user = User(
                email=f"role_test_{role_str}@test.com",
                hashed_password="hashed",
                role=role_enum.value,
            )
            real_db.add(user)
            await real_db.commit()
            await real_db.refresh(user)

            expert = ExpertProfile(
                user_id=user.id,
                credential_types=[ExpertCredentialType.ADMIN],
                is_verified=True,
                is_active=True,
            )
            real_db.add(expert)
            await real_db.commit()
            await real_db.refresh(expert)

            async def get_real_db():
                yield real_db

            app.dependency_overrides[get_current_user] = lambda u=user: u
            app.dependency_overrides[get_db] = get_real_db

            try:
                with TestClient(app) as client:
                    response = client.get("/api/v1/expert-feedback/experts/me/profile")

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()

                    # Verify role is included in response
                    assert data["role"] == role_str
            finally:
                app.dependency_overrides.clear()


class TestExpertProfileMetrics:
    """Test expert profile metrics are correctly returned."""

    @pytest.mark.asyncio
    async def test_get_expert_profile_metrics_ranges(self, real_db, test_user):
        """Test profile metrics are within valid ranges."""
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[ExpertCredentialType.DOTTORE_COMMERCIALISTA],
            feedback_count=100,
            feedback_accuracy_rate=0.95,  # 0.0-1.0 range
            trust_score=0.85,  # 0.0-1.0 range
            average_response_time_seconds=180,
            is_verified=True,
            is_active=True,
        )
        real_db.add(expert)
        await real_db.commit()
        await real_db.refresh(expert)

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/experts/me/profile")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                # Verify metrics are numbers in valid ranges
                assert isinstance(data["feedback_count"], int)
                assert data["feedback_count"] == 100

                assert isinstance(data["feedback_accuracy_rate"], float)
                assert 0.0 <= data["feedback_accuracy_rate"] <= 1.0

                assert isinstance(data["trust_score"], float)
                assert 0.0 <= data["trust_score"] <= 1.0

                assert isinstance(data["average_response_time_seconds"], int)
                assert data["average_response_time_seconds"] > 0
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_expert_profile_default_metrics(self, real_db, test_user):
        """Test profile with default metric values (new expert)."""
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[ExpertCredentialType.CONSULENTE_FISCALE],
            # Default metrics (new expert with no feedback yet)
            feedback_count=0,
            feedback_accuracy_rate=0.0,
            trust_score=0.5,  # Default trust score
            average_response_time_seconds=0,
            is_verified=True,
            is_active=True,
        )
        real_db.add(expert)
        await real_db.commit()
        await real_db.refresh(expert)

        async def get_real_db():
            yield real_db

        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[get_db] = get_real_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/expert-feedback/experts/me/profile")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                # Verify default metric values
                assert data["feedback_count"] == 0
                assert data["feedback_accuracy_rate"] == 0.0
                assert data["trust_score"] == 0.5
                assert data["average_response_time_seconds"] == 0
        finally:
            app.dependency_overrides.clear()
