"""End-to-End Integration Tests for Expert Feedback System.

These tests verify the COMPLETE workflow from API request → database → file system,
catching integration bugs that unit tests miss (e.g., API contract mismatches,
database constraint violations, file system errors).

Test Strategy Document: docs/testing/E2E_EXPERT_FEEDBACK_TESTING_STRATEGY.md
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.database import get_db
from app.models.quality_analysis import (
    ExpertCredentialType,
    ExpertFeedback,
    ExpertGeneratedTask,
    ExpertProfile,
    FeedbackType,
    ItalianFeedbackCategory,
)
from app.models.user import User, UserRole

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def test_super_user(db_session: AsyncSession) -> User:
    """Create test user with SUPER_USER role."""
    user = User(
        email="super_user@e2e-test.com",
        hashed_password="<hashed-test-password>",
        is_active=True,
        is_verified=True,
        role=UserRole.SUPER_USER.value,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_regular_user(db_session: AsyncSession) -> User:
    """Create test user with regular USER role."""
    user = User(
        email="regular_user@e2e-test.com",
        hashed_password="<hashed-test-password>",
        is_active=True,
        is_verified=True,
        role=UserRole.REGULAR_USER.value,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_expert_profile(db_session: AsyncSession, test_super_user: User) -> ExpertProfile:
    """Create test expert profile with high trust score."""
    profile = ExpertProfile(
        user_id=test_super_user.id,
        credentials=["Dottore Commercialista"],
        credential_types=[ExpertCredentialType.DOTTORE_COMMERCIALISTA],
        experience_years=15,
        specializations=["diritto_tributario", "fiscale"],
        feedback_count=100,
        feedback_accuracy_rate=0.95,
        average_response_time_seconds=200,
        trust_score=0.92,
        professional_registration_number="AA123456",
        organization="Studio Test E2E",
        location_city="Milano",
        is_verified=True,
        is_active=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest.fixture
def sample_feedback_payload():
    """Sample feedback submission payload (valid JSON)."""
    return {
        "query_id": str(uuid4()),
        "feedback_type": "incomplete",
        "category": "calcolo_sbagliato",
        "query_text": "Come si calcola l'IVA per il regime forfettario?",
        "original_answer": "Nel regime forfettario non si applica l'IVA.",
        "expert_answer": "Nel regime forfettario non si applica l'IVA in fattura, "
        "ma sono previsti adempimenti specifici per cessioni intra-UE.",
        "improvement_suggestions": [
            "Aggiungere casi specifici per cessioni UE",
            "Citare normativa aggiornata 2024",
        ],
        "regulatory_references": ["Art. 1, comma 54-89, L. 190/2014"],
        "confidence_score": 0.9,
        "time_spent_seconds": 180,
        "complexity_rating": 3,
        "additional_details": "La risposta non tratta i casi di cessione beni intra-UE "
        "che richiedono adempimenti IVA specifici anche per forfettari.",
    }


@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Create temporary project root with QUERY_ISSUES_ROADMAP.md structure."""
    # Create QUERY_ISSUES_ROADMAP.md with proper structure
    roadmap = tmp_path / "QUERY_ISSUES_ROADMAP.md"
    roadmap.write_text(
        """# PratikoAi - Query Issues Roadmap

## Development Process Issues (QUERY-01 to QUERY-07)

### QUERY-01: Test Process Issue
**Priority:** LOW | **Effort:** TBD
**Status:** 🟢 COMPLETE

[Reserved for development process issues]

---

## Expert Feedback Issues (Auto-generated from QUERY-08 onwards)

"""
    )

    return tmp_path


# ============================================================================
# E2E-01: Happy Path - Correct Feedback
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_01_correct_feedback_golden_set_workflow(
    db_session: AsyncSession,
    test_super_user: User,
    test_expert_profile: ExpertProfile,
    sample_feedback_payload: dict,
):
    """E2E-01: Verify complete workflow for CORRECT feedback.

    Test Steps:
    1. Authenticate as SUPER_USER
    2. Submit "correct" feedback via POST /api/v1/expert-feedback/submit
    3. Verify HTTP 201 response with correct JSON structure
    4. Verify feedback record exists in database with all fields
    5. Verify task_creation_attempted=True (Golden Set workflow triggered)
    6. Verify expert metrics updated

    Expected Outcomes:
    - HTTP 201 Created
    - Feedback stored with feedback_type='correct'
    - task_creation_attempted=True (Golden Set workflow)
    - generated_task_id is null (no task for correct feedback)
    - Expert's feedback_count incremented
    """
    # Modify payload for "correct" feedback
    payload = sample_feedback_payload.copy()
    payload["feedback_type"] = "correct"
    payload["category"] = None  # Optional for correct feedback
    payload.pop("additional_details")  # Not needed for correct
    payload.pop("expert_answer")  # Not needed for correct

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Override authentication
        app.dependency_overrides[get_current_user] = lambda: test_super_user

        try:
            # Step 2: Submit feedback
            response = await client.post("/api/v1/expert-feedback/submit", json=payload)

            # Step 3: Verify HTTP response
            assert response.status_code == 201
            data = response.json()
            assert data["feedback_type"] == "correct"
            assert data["expert_trust_score"] == 0.92
            assert data["task_creation_attempted"] is True  # Golden Set workflow
            assert data["generated_task_id"] is None

            feedback_id = UUID(data["feedback_id"])

            # Step 4: Verify database record
            result = await db_session.execute(select(ExpertFeedback).where(ExpertFeedback.id == feedback_id))
            feedback_record = result.scalar_one()

            assert feedback_record.feedback_type == FeedbackType.CORRECT
            assert feedback_record.query_text == payload["query_text"]
            assert feedback_record.original_answer == payload["original_answer"]
            assert feedback_record.confidence_score == 0.9
            assert feedback_record.time_spent_seconds == 180
            assert feedback_record.task_creation_attempted is True
            assert feedback_record.generated_task_id is None

            # Step 5: Verify timestamps auto-populated
            assert feedback_record.feedback_timestamp is not None
            assert feedback_record.created_at is not None
            assert feedback_record.updated_at is not None

            # Step 6: Verify expert metrics updated
            await db_session.refresh(test_expert_profile)
            assert test_expert_profile.feedback_count == 101  # Was 100

        finally:
            app.dependency_overrides.clear()


# ============================================================================
# E2E-02: Happy Path - Incomplete with Task Generation
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_02_incomplete_feedback_task_generation(
    db_session: AsyncSession,
    test_super_user: User,
    test_expert_profile: ExpertProfile,
    sample_feedback_payload: dict,
    temp_project_root: Path,
):
    """E2E-02: Verify complete workflow for INCOMPLETE feedback with task generation.

    Test Steps:
    1. Submit "incomplete" feedback with additional_details
    2. Verify HTTP 201 response
    3. Wait for background task to complete
    4. Verify feedback record in database
    5. Verify task file created/updated (QUERY_ISSUES_ROADMAP.md)
    6. Verify task content includes query, answer, expert details
    7. Verify generated_task_id populated
    8. Verify record in expert_generated_tasks table

    Expected Outcomes:
    - HTTP 201 Created
    - Feedback stored with feedback_type='incomplete'
    - task_creation_attempted=True
    - Task file updated with new task
    - generated_task_id populated (e.g., "QUERY-08")
    - task_creation_success=True
    """
    from app.services.task_generator_service import TaskGeneratorService

    # Patch TaskGeneratorService to use temp directory
    with patch.object(
        TaskGeneratorService,
        "__init__",
        lambda self, db: setattr(self, "db", db) or setattr(self, "project_root", temp_project_root),
    ):
        payload = sample_feedback_payload.copy()
        payload["feedback_type"] = "incomplete"

        async with AsyncClient(app=app, base_url="http://test") as client:
            app.dependency_overrides[get_current_user] = lambda: test_super_user

            try:
                # Step 1: Submit feedback
                response = await client.post("/api/v1/expert-feedback/submit", json=payload)

                # Step 2: Verify HTTP response
                assert response.status_code == 201
                data = response.json()
                assert data["task_creation_attempted"] is True

                feedback_id = UUID(data["feedback_id"])

                # Step 3: Wait for background task to complete
                await asyncio.sleep(3)

                # Step 4: Refresh feedback record
                result = await db_session.execute(select(ExpertFeedback).where(ExpertFeedback.id == feedback_id))
                feedback_record = result.scalar_one()

                # Step 5: Verify task ID populated
                assert feedback_record.generated_task_id is not None
                assert feedback_record.generated_task_id.startswith("QUERY-")
                assert feedback_record.task_creation_success is True

                task_id = feedback_record.generated_task_id

                # Step 6: Verify file updated
                roadmap_file = temp_project_root / "QUERY_ISSUES_ROADMAP.md"
                assert roadmap_file.exists()

                content = roadmap_file.read_text()
                assert task_id in content
                assert payload["query_text"] in content
                assert payload["original_answer"] in content
                assert payload["additional_details"] in content
                assert f"Trust Score: {test_expert_profile.trust_score:.2f}" in content

                # Step 7: Verify task record in database
                result = await db_session.execute(
                    select(ExpertGeneratedTask).where(ExpertGeneratedTask.task_id == task_id)
                )
                task_record = result.scalar_one()

                assert task_record.feedback_id == feedback_id
                assert task_record.expert_id == test_expert_profile.id
                assert task_record.question == payload["query_text"]
                assert task_record.answer == payload["original_answer"]
                assert task_record.additional_details == payload["additional_details"]
                assert task_record.file_path == "QUERY_ISSUES_ROADMAP.md"

            finally:
                app.dependency_overrides.clear()


# ============================================================================
# E2E-04: Authentication & Authorization RBAC
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_04_authentication_authorization_rbac(
    db_session: AsyncSession,
    test_regular_user: User,
    test_super_user: User,
    test_expert_profile: ExpertProfile,
    sample_feedback_payload: dict,
):
    """E2E-04: Verify role-based access control for feedback submission.

    Test Steps:
    1. Unauthenticated request → 401 Unauthorized
    2. Regular USER role → 403 Forbidden
    3. SUPER_USER without expert profile → 403 Forbidden
    4. SUPER_USER with inactive expert → 403 Forbidden
    5. SUPER_USER with active expert → 201 Success

    Expected Outcomes:
    - 401 for unauthenticated
    - 403 for regular users
    - 403 for users without expert profile
    - 403 for inactive experts
    - 201 for SUPER_USER with active expert
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        try:
            # Test 1: Unauthenticated request
            response = await client.post("/api/v1/expert-feedback/submit", json=sample_feedback_payload)
            assert response.status_code == 401

            # Test 2: Regular user (not SUPER_USER)
            app.dependency_overrides[get_current_user] = lambda: test_regular_user

            response = await client.post("/api/v1/expert-feedback/submit", json=sample_feedback_payload)
            assert response.status_code == 403
            assert "Only super users can provide feedback" in response.json()["detail"]

            # Test 3: SUPER_USER without expert profile
            super_user_no_profile = User(
                email="super_no_profile@e2e-test.com",
                hashed_password="hashed",
                role=UserRole.SUPER_USER.value,
                is_active=True,
                is_verified=True,
            )
            db_session.add(super_user_no_profile)
            await db_session.commit()

            app.dependency_overrides[get_current_user] = lambda: super_user_no_profile

            response = await client.post("/api/v1/expert-feedback/submit", json=sample_feedback_payload)
            assert response.status_code == 403
            assert "not an expert" in response.json()["detail"]

            # Test 4: SUPER_USER with inactive expert
            test_expert_profile.is_active = False
            await db_session.commit()

            app.dependency_overrides[get_current_user] = lambda: test_super_user

            response = await client.post("/api/v1/expert-feedback/submit", json=sample_feedback_payload)
            assert response.status_code == 403
            assert "not active or verified" in response.json()["detail"]

            # Test 5: Success - SUPER_USER with active expert
            test_expert_profile.is_active = True
            await db_session.commit()

            response = await client.post("/api/v1/expert-feedback/submit", json=sample_feedback_payload)
            assert response.status_code == 201

        finally:
            app.dependency_overrides.clear()


# ============================================================================
# E2E-05: Validation Errors
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_05_validation_errors(
    db_session: AsyncSession,
    test_super_user: User,
    test_expert_profile: ExpertProfile,
    sample_feedback_payload: dict,
):
    """E2E-05: Verify Pydantic validation catches invalid data.

    Test Steps:
    1. Missing required field (query_text) → 422
    2. Invalid feedback_type → 422
    3. Invalid confidence_score → 422
    4. Invalid time_spent_seconds → 422
    5. Placeholder query_text → 422

    Expected Outcomes:
    - 422 Validation Error for all invalid cases
    - Error messages describe validation failure
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        app.dependency_overrides[get_current_user] = lambda: test_super_user

        try:
            # Test 1: Missing required field
            invalid_payload = sample_feedback_payload.copy()
            del invalid_payload["query_text"]

            response = await client.post("/api/v1/expert-feedback/submit", json=invalid_payload)
            assert response.status_code == 422

            # Test 2: Invalid feedback_type
            invalid_payload = sample_feedback_payload.copy()
            invalid_payload["feedback_type"] = "invalid_type"

            response = await client.post("/api/v1/expert-feedback/submit", json=invalid_payload)
            assert response.status_code == 422

            # Test 3: Invalid confidence_score (>1.0)
            invalid_payload = sample_feedback_payload.copy()
            invalid_payload["confidence_score"] = 1.5

            response = await client.post("/api/v1/expert-feedback/submit", json=invalid_payload)
            assert response.status_code == 422

            # Test 4: Invalid time_spent_seconds (negative)
            invalid_payload = sample_feedback_payload.copy()
            invalid_payload["time_spent_seconds"] = -10

            response = await client.post("/api/v1/expert-feedback/submit", json=invalid_payload)
            assert response.status_code == 422

            # Test 5: Placeholder query_text (catches API contract bug!)
            invalid_payload = sample_feedback_payload.copy()
            invalid_payload["query_text"] = "[Domanda precedente dell'utente]"

            response = await client.post("/api/v1/expert-feedback/submit", json=invalid_payload)
            assert response.status_code == 422
            error_detail = str(response.json()["detail"])
            assert "placeholder" in error_detail.lower()

        finally:
            app.dependency_overrides.clear()


# ============================================================================
# E2E-07: Field Mappings & Type Compatibility
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_07_field_mappings_type_compatibility(
    db_session: AsyncSession,
    test_super_user: User,
    test_expert_profile: ExpertProfile,
    sample_feedback_payload: dict,
):
    """E2E-07: Verify field mappings and type compatibility (API contract test).

    Test Steps:
    1. Submit feedback with all fields populated
    2. Verify UUID fields stored as UUID type
    3. Verify enum values map correctly
    4. Verify ARRAY fields stored correctly
    5. Verify timestamps auto-populate

    Expected Outcomes:
    - Italian categories map to correct enum
    - UUID strings convert to UUID type
    - ARRAY fields stored as PostgreSQL arrays
    - Timestamps auto-populate
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        app.dependency_overrides[get_current_user] = lambda: test_super_user

        try:
            # Submit feedback with all fields
            response = await client.post("/api/v1/expert-feedback/submit", json=sample_feedback_payload)

            assert response.status_code == 201
            feedback_id = UUID(response.json()["feedback_id"])

            # Retrieve from database and verify field types
            result = await db_session.execute(select(ExpertFeedback).where(ExpertFeedback.id == feedback_id))
            feedback_record = result.scalar_one()

            # Verify UUID types
            assert isinstance(feedback_record.id, UUID)
            assert isinstance(feedback_record.query_id, UUID)
            assert isinstance(feedback_record.expert_id, UUID)

            # Verify enum mapping
            assert feedback_record.category == ItalianFeedbackCategory.CALCOLO_SBAGLIATO

            # Verify ARRAY fields
            assert isinstance(feedback_record.improvement_suggestions, list)
            assert len(feedback_record.improvement_suggestions) == 2
            assert "Aggiungere casi specifici per cessioni UE" in feedback_record.improvement_suggestions

            assert isinstance(feedback_record.regulatory_references, list)
            assert "Art. 1, comma 54-89, L. 190/2014" in feedback_record.regulatory_references

            # Verify timestamps auto-populated
            assert feedback_record.feedback_timestamp is not None
            assert feedback_record.created_at is not None
            assert feedback_record.updated_at is not None

        finally:
            app.dependency_overrides.clear()
