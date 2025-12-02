# E2E Integration Testing Strategy: Expert Feedback System

**Document Version:** 1.0
**Created:** 2025-11-25
**Author:** PratikoAI Test Generation Subagent (@Clelia)
**Status:** READY FOR IMPLEMENTATION
**Related Task:** DEV-BE-72 Expert Feedback Database Schema

---

## Executive Summary

This document defines the **End-to-End (E2E) Integration Testing Strategy** for the Expert Feedback System. Unlike existing unit tests (17 API tests, 18 service tests), E2E tests verify the **COMPLETE workflow** from API request → database → file system → background tasks, catching integration bugs like API contract mismatches that occurred during development.

**Current Gap:** The Italian field name vs English API mismatch (and missing required fields) could have been caught earlier with E2E tests that verify actual database transactions and file system changes.

**Testing Philosophy:**
- **Unit tests** verify individual components in isolation (mocked dependencies)
- **E2E tests** verify complete workflows with real database transactions, file I/O, and cross-service integration
- **Both are essential** - unit tests catch logic bugs, E2E tests catch integration bugs

---

## Test Scenarios Overview

| Scenario ID | Scenario Name | Priority | Complexity | Test Type |
|------------|---------------|----------|------------|-----------|
| E2E-01 | Happy Path - Correct Feedback | HIGH | Medium | Full E2E |
| E2E-02 | Happy Path - Incomplete with Task Generation | CRITICAL | High | Full E2E |
| E2E-03 | Happy Path - Incorrect with Task Generation | CRITICAL | High | Full E2E |
| E2E-04 | Authentication & Authorization RBAC | HIGH | Low | API-only |
| E2E-05 | Validation Errors (Pydantic) | MEDIUM | Low | API-only |
| E2E-06 | Database Constraints & Foreign Keys | HIGH | Medium | DB-focused |
| E2E-07 | Field Mappings & Type Compatibility | CRITICAL | Medium | Full E2E |
| E2E-08 | Golden Set Workflow Integration (S127-S130) | HIGH | High | Full E2E |
| E2E-09 | Error Recovery & Transaction Rollback | HIGH | High | Full E2E |
| E2E-10 | Background Task Execution | MEDIUM | Medium | Async E2E |

---

## Testing Infrastructure

### Test Database Strategy

**Approach:** Use PostgreSQL test database with real transactions (not SQLite, not mocked)

**Rationale:**
- Catch PostgreSQL-specific constraint violations (ARRAY, UUID, ENUM types)
- Verify foreign key cascades work correctly
- Test actual transaction isolation and rollback behavior
- Validate JSON/JSONB field handling

**Implementation:**
```python
# tests/conftest.py

import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.ccnl_database import Base
from app.core.config import settings

# Use test database (separate from dev/prod)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/pratiko_ai", "/pratiko_ai_test")

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture
async def db_session(test_engine) -> AsyncSession:
    """Create database session with automatic rollback.

    Each test gets a fresh session that rolls back all changes,
    ensuring test isolation.
    """
    async_session_maker = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Start transaction
        async with session.begin():
            yield session
            # Rollback happens automatically when context exits
            await session.rollback()
```

### Test File System Strategy

**Approach:** Use temporary directories for file operations (task generation)

**Implementation:**
```python
import tempfile
from pathlib import Path
import pytest

@pytest.fixture
def temp_project_root(tmp_path):
    """Create temporary project root with required structure."""
    # Create QUERY_ISSUES_ROADMAP.md
    roadmap = tmp_path / "QUERY_ISSUES_ROADMAP.md"
    roadmap.write_text("""# PratikoAi - Query Issues Roadmap

## Development Process Issues (QUERY-01 to QUERY-07)

### QUERY-01: Test Process Issue
[Reserved for development process]

---

## Expert Feedback Issues (Auto-generated from QUERY-08)
""")

    return tmp_path
```

### Test Fixtures

**Core fixtures needed:**

```python
# tests/fixtures/expert_feedback_fixtures.py

import pytest
from uuid import uuid4
from app.models.user import User, UserRole
from app.models.quality_analysis import (
    ExpertProfile,
    ExpertCredentialType,
    ExpertFeedback,
    FeedbackType
)

@pytest.fixture
async def test_super_user(db_session) -> User:
    """Create test user with SUPER_USER role."""
    user = User(
        email="super_user@test.com",
        hashed_password="<hashed-test-password>",  # Not used in tests
        is_active=True,
        is_verified=True,
        role=UserRole.SUPER_USER.value
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def test_regular_user(db_session) -> User:
    """Create test user with regular USER role."""
    user = User(
        email="regular@test.com",
        hashed_password="<hashed-test-password>",
        is_active=True,
        is_verified=True,
        role=UserRole.USER.value
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def test_expert_profile(db_session, test_super_user) -> ExpertProfile:
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
        organization="Studio Test",
        location_city="Milano",
        is_verified=True,
        is_active=True
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile

@pytest.fixture
def sample_feedback_payload():
    """Sample feedback submission payload (JSON)."""
    return {
        "query_id": str(uuid4()),
        "feedback_type": "incomplete",
        "category": "calcolo_sbagliato",
        "query_text": "Come si calcola l'IVA per il regime forfettario?",
        "original_answer": "Nel regime forfettario non si applica l'IVA.",
        "expert_answer": "Nel regime forfettario non si applica l'IVA in fattura...",
        "improvement_suggestions": [
            "Aggiungere casi specifici per UE",
            "Citare normativa aggiornata"
        ],
        "regulatory_references": ["Art. 1, comma 54-89, L. 190/2014"],
        "confidence_score": 0.9,
        "time_spent_seconds": 180,
        "complexity_rating": 3,
        "additional_details": "La risposta non tratta i casi di cessione beni UE."
    }
```

---

## E2E Test Scenarios (Detailed)

### E2E-01: Happy Path - Correct Feedback

**Purpose:** Verify complete workflow for "correct" feedback (triggers Golden Set workflow S127-S130)

**Test Steps:**
1. Authenticate as SUPER_USER
2. Submit "correct" feedback via POST /api/v1/expert-feedback/submit
3. Verify HTTP 201 response with correct JSON structure
4. Verify feedback record exists in database with all fields
5. Verify `task_creation_attempted=True` (Golden Set workflow triggered)
6. Verify background task executed (check `generated_faq_id` populated)
7. Verify expert metrics updated (feedback_count, trust_score)

**Expected Outcomes:**
- ✅ HTTP 201 Created
- ✅ Feedback stored with `feedback_type='correct'`
- ✅ `task_creation_attempted=True`
- ✅ `generated_faq_id` is not null (if Golden Set workflow succeeds)
- ✅ `generated_task_id` is null (no task for correct feedback)
- ✅ Expert's `feedback_count` incremented

**Code Example:**
```python
# tests/e2e/test_expert_feedback_e2e.py

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_e2e_correct_feedback_golden_set_workflow(
    db_session,
    test_super_user,
    test_expert_profile,
    sample_feedback_payload
):
    """E2E-01: Verify complete workflow for CORRECT feedback."""

    # Modify payload for "correct" feedback
    payload = sample_feedback_payload.copy()
    payload["feedback_type"] = "correct"
    payload["category"] = None  # Optional for correct feedback
    payload.pop("additional_details")  # Not needed for correct

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Authenticate (override dependency)
        # NOTE: In real tests, use proper JWT token
        from app.api.v1.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: test_super_user

        # Step 2: Submit feedback
        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=payload
        )

        # Step 3: Verify HTTP response
        assert response.status_code == 201
        data = response.json()
        assert data["feedback_type"] == "correct"
        assert data["expert_trust_score"] == 0.92
        assert data["task_creation_attempted"] is True  # Golden Set workflow
        assert data["generated_task_id"] is None

        feedback_id = data["feedback_id"]

        # Step 4: Verify database record
        from sqlalchemy import select
        from app.models.quality_analysis import ExpertFeedback

        result = await db_session.execute(
            select(ExpertFeedback).where(ExpertFeedback.id == feedback_id)
        )
        feedback_record = result.scalar_one()

        assert feedback_record.feedback_type == FeedbackType.CORRECT
        assert feedback_record.query_text == payload["query_text"]
        assert feedback_record.original_answer == payload["original_answer"]
        assert feedback_record.confidence_score == 0.9
        assert feedback_record.time_spent_seconds == 180
        assert feedback_record.task_creation_attempted is True

        # Step 5: Verify Golden Set workflow executed
        # NOTE: This requires mocking or waiting for background task
        # For true E2E, we'd wait and check generated_faq_id
        # For faster tests, we mock the Golden Set orchestrator

        # Step 6: Verify expert metrics updated
        await db_session.refresh(test_expert_profile)
        assert test_expert_profile.feedback_count == 101  # Was 100
```

---

### E2E-02: Happy Path - Incomplete with Task Generation

**Purpose:** Verify complete workflow for "incomplete" feedback that generates a task in QUERY_ISSUES_ROADMAP.md

**Test Steps:**
1. Authenticate as SUPER_USER
2. Submit "incomplete" feedback with `additional_details`
3. Verify HTTP 201 response
4. Verify feedback record in database
5. **Verify task file created/updated** (QUERY_ISSUES_ROADMAP.md)
6. **Verify task content** (contains query, answer, expert details)
7. Verify `generated_task_id` populated
8. Verify record in `expert_generated_tasks` table
9. Verify `task_creation_success=True`

**Expected Outcomes:**
- ✅ HTTP 201 Created
- ✅ Feedback stored with `feedback_type='incomplete'`
- ✅ `task_creation_attempted=True`
- ✅ Task file updated with new task (QUERY-08, QUERY-09, etc.)
- ✅ Task content includes query_text, original_answer, additional_details
- ✅ `generated_task_id` populated (e.g., "QUERY-08")
- ✅ Record exists in `expert_generated_tasks` table
- ✅ `task_creation_success=True`

**Code Example:**
```python
@pytest.mark.asyncio
async def test_e2e_incomplete_feedback_task_generation(
    db_session,
    test_super_user,
    test_expert_profile,
    sample_feedback_payload,
    temp_project_root
):
    """E2E-02: Verify complete workflow for INCOMPLETE feedback with task generation."""

    # Patch TaskGeneratorService to use temp directory
    from app.services.task_generator_service import TaskGeneratorService
    original_project_root = TaskGeneratorService.__init__.__code__.co_consts

    with patch.object(TaskGeneratorService, "project_root", temp_project_root):
        payload = sample_feedback_payload.copy()
        payload["feedback_type"] = "incomplete"

        async with AsyncClient(app=app, base_url="http://test") as client:
            app.dependency_overrides[get_current_user] = lambda: test_super_user

            # Submit feedback
            response = await client.post(
                "/api/v1/expert-feedback/submit",
                json=payload
            )

            assert response.status_code == 201
            data = response.json()
            assert data["task_creation_attempted"] is True

            feedback_id = data["feedback_id"]

            # Wait for background task to complete (give it 2 seconds)
            import asyncio
            await asyncio.sleep(2)

            # Refresh feedback record to get updated task info
            from sqlalchemy import select
            from app.models.quality_analysis import ExpertFeedback

            result = await db_session.execute(
                select(ExpertFeedback).where(ExpertFeedback.id == feedback_id)
            )
            feedback_record = result.scalar_one()

            # Verify task ID populated
            assert feedback_record.generated_task_id is not None
            assert feedback_record.generated_task_id.startswith("QUERY-")
            assert feedback_record.task_creation_success is True

            task_id = feedback_record.generated_task_id

            # Verify file updated
            roadmap_file = temp_project_root / "QUERY_ISSUES_ROADMAP.md"
            assert roadmap_file.exists()

            content = roadmap_file.read_text()
            assert task_id in content
            assert payload["query_text"] in content
            assert payload["original_answer"] in content
            assert payload["additional_details"] in content
            assert f"Trust Score: {test_expert_profile.trust_score:.2f}" in content

            # Verify task record in database
            from app.models.quality_analysis import ExpertGeneratedTask

            result = await db_session.execute(
                select(ExpertGeneratedTask).where(
                    ExpertGeneratedTask.task_id == task_id
                )
            )
            task_record = result.scalar_one()

            assert task_record.feedback_id == feedback_id
            assert task_record.expert_id == test_expert_profile.id
            assert task_record.question == payload["query_text"]
            assert task_record.answer == payload["original_answer"]
            assert task_record.additional_details == payload["additional_details"]
            assert task_record.file_path == "QUERY_ISSUES_ROADMAP.md"
```

---

### E2E-03: Happy Path - Incorrect with Task Generation

**Purpose:** Verify "incorrect" feedback workflow (similar to E2E-02 but with `feedback_type='incorrect'`)

**Test Steps:** Same as E2E-02, but with `feedback_type='incorrect'`

**Expected Outcomes:** Same as E2E-02, task should include expert's suggested correction

**Code Example:**
```python
@pytest.mark.asyncio
async def test_e2e_incorrect_feedback_task_generation(
    db_session,
    test_super_user,
    test_expert_profile,
    sample_feedback_payload,
    temp_project_root
):
    """E2E-03: Verify complete workflow for INCORRECT feedback with task generation."""

    payload = sample_feedback_payload.copy()
    payload["feedback_type"] = "incorrect"
    payload["expert_answer"] = "La risposta corretta è: nel regime forfettario..."

    # ... (same test structure as E2E-02)

    # Additional verification: expert_answer included in task
    roadmap_file = temp_project_root / "QUERY_ISSUES_ROADMAP.md"
    content = roadmap_file.read_text()

    # Task should mention it's "Errata" (incorrect)
    assert "Errata" in content or "errata" in content
```

---

### E2E-04: Authentication & Authorization RBAC

**Purpose:** Verify role-based access control (only SUPER_USER can submit feedback)

**Test Steps:**
1. Attempt to submit feedback without authentication → 401 Unauthorized
2. Attempt to submit feedback as regular USER → 403 Forbidden
3. Attempt to submit feedback as SUPER_USER but without expert profile → 403 Forbidden
4. Attempt to submit feedback as SUPER_USER with inactive expert profile → 403 Forbidden
5. Successful submission as SUPER_USER with active expert profile → 201 Created

**Expected Outcomes:**
- ❌ 401 for unauthenticated requests
- ❌ 403 for regular users
- ❌ 403 for users without expert profile
- ❌ 403 for inactive expert profiles
- ✅ 201 for SUPER_USER with active expert profile

**Code Example:**
```python
@pytest.mark.asyncio
async def test_e2e_authentication_authorization_rbac(
    db_session,
    test_regular_user,
    test_super_user,
    test_expert_profile,
    sample_feedback_payload
):
    """E2E-04: Verify RBAC for expert feedback submission."""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test 1: Unauthenticated request
        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=sample_feedback_payload
        )
        assert response.status_code == 401

        # Test 2: Regular user (not SUPER_USER)
        app.dependency_overrides[get_current_user] = lambda: test_regular_user

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=sample_feedback_payload
        )
        assert response.status_code == 403
        assert "Only super users can provide feedback" in response.json()["detail"]

        # Test 3: SUPER_USER without expert profile
        super_user_no_profile = User(
            email="super_no_profile@test.com",
            role=UserRole.SUPER_USER.value,
            is_active=True,
            is_verified=True
        )
        db_session.add(super_user_no_profile)
        await db_session.commit()

        app.dependency_overrides[get_current_user] = lambda: super_user_no_profile

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=sample_feedback_payload
        )
        assert response.status_code == 403
        assert "not an expert" in response.json()["detail"]

        # Test 4: SUPER_USER with inactive expert profile
        test_expert_profile.is_active = False
        await db_session.commit()

        app.dependency_overrides[get_current_user] = lambda: test_super_user

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=sample_feedback_payload
        )
        assert response.status_code == 403
        assert "not active or verified" in response.json()["detail"]

        # Test 5: Success - SUPER_USER with active expert profile
        test_expert_profile.is_active = True
        await db_session.commit()

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=sample_feedback_payload
        )
        assert response.status_code == 201
```

---

### E2E-05: Validation Errors (Pydantic)

**Purpose:** Verify Pydantic validation catches invalid data

**Test Steps:**
1. Missing required field (`query_text`) → 422
2. Invalid `feedback_type` → 422
3. Invalid `confidence_score` (<0 or >1) → 422
4. Invalid `time_spent_seconds` (negative) → 422
5. Invalid `category` → 422
6. Placeholder `query_text` → 422

**Expected Outcomes:**
- ❌ 422 Validation Error for all invalid cases
- ✅ Error messages describe the validation failure

**Code Example:**
```python
@pytest.mark.asyncio
async def test_e2e_validation_errors(
    db_session,
    test_super_user,
    test_expert_profile,
    sample_feedback_payload
):
    """E2E-05: Verify Pydantic validation catches invalid data."""

    async with AsyncClient(app=app, base_url="http://test") as client:
        app.dependency_overrides[get_current_user] = lambda: test_super_user

        # Test 1: Missing required field
        invalid_payload = sample_feedback_payload.copy()
        del invalid_payload["query_text"]

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=invalid_payload
        )
        assert response.status_code == 422

        # Test 2: Invalid feedback_type
        invalid_payload = sample_feedback_payload.copy()
        invalid_payload["feedback_type"] = "invalid_type"

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=invalid_payload
        )
        assert response.status_code == 422

        # Test 3: Invalid confidence_score
        invalid_payload = sample_feedback_payload.copy()
        invalid_payload["confidence_score"] = 1.5  # >1.0

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=invalid_payload
        )
        assert response.status_code == 422

        # Test 4: Invalid time_spent_seconds
        invalid_payload = sample_feedback_payload.copy()
        invalid_payload["time_spent_seconds"] = -10  # Negative

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=invalid_payload
        )
        assert response.status_code == 422

        # Test 5: Placeholder query_text (catches API contract bug!)
        invalid_payload = sample_feedback_payload.copy()
        invalid_payload["query_text"] = "[Domanda precedente dell'utente]"

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=invalid_payload
        )
        assert response.status_code == 422
        assert "placeholder" in response.json()["detail"][0]["msg"].lower()
```

---

### E2E-06: Database Constraints & Foreign Keys

**Purpose:** Verify PostgreSQL constraints and foreign key relationships work correctly

**Test Steps:**
1. Create feedback with non-existent `expert_id` → Should fail (FK violation)
2. Create feedback with non-existent `query_id` → Should succeed (no FK constraint)
3. Delete expert profile → Should cascade delete feedback (if configured)
4. Verify `confidence_score` constraint (0.0-1.0)
5. Verify `complexity_rating` constraint (1-5)

**Expected Outcomes:**
- ❌ Foreign key violation for invalid `expert_id`
- ✅ Accepts non-existent `query_id` (no FK constraint)
- ✅ Check constraints enforced (ranges)

**Code Example:**
```python
@pytest.mark.asyncio
async def test_e2e_database_constraints(
    db_session,
    test_super_user,
    test_expert_profile
):
    """E2E-06: Verify database constraints and foreign keys."""

    from sqlalchemy.exc import IntegrityError
    from app.models.quality_analysis import ExpertFeedback, FeedbackType

    # Test 1: Invalid expert_id (FK violation)
    invalid_feedback = ExpertFeedback(
        query_id=uuid4(),
        expert_id=uuid4(),  # Non-existent expert
        feedback_type=FeedbackType.CORRECT,
        query_text="Test",
        original_answer="Test",
        confidence_score=0.8,
        time_spent_seconds=100
    )

    db_session.add(invalid_feedback)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()

    # Test 2: Invalid confidence_score (check constraint)
    invalid_feedback = ExpertFeedback(
        query_id=uuid4(),
        expert_id=test_expert_profile.id,
        feedback_type=FeedbackType.CORRECT,
        query_text="Test",
        original_answer="Test",
        confidence_score=1.5,  # >1.0
        time_spent_seconds=100
    )

    db_session.add(invalid_feedback)

    with pytest.raises(IntegrityError) as exc_info:
        await db_session.commit()

    assert "confidence_score_range" in str(exc_info.value)
    await db_session.rollback()
```

---

### E2E-07: Field Mappings & Type Compatibility

**Purpose:** Verify Italian UI labels map correctly to English API fields (catches API contract bugs!)

**Test Steps:**
1. Submit feedback with Italian category → Verify stored as English enum
2. Submit feedback with UUID as string → Verify stored as UUID type
3. Submit feedback with all optional fields → Verify all persisted
4. Verify ARRAY fields (improvement_suggestions, regulatory_references) stored correctly
5. Verify timestamp fields auto-populate

**Expected Outcomes:**
- ✅ Italian categories map to correct enum values
- ✅ UUID strings convert to UUID types
- ✅ ARRAY fields stored as PostgreSQL arrays
- ✅ Timestamps auto-populate

**Code Example:**
```python
@pytest.mark.asyncio
async def test_e2e_field_mappings_type_compatibility(
    db_session,
    test_super_user,
    test_expert_profile,
    sample_feedback_payload
):
    """E2E-07: Verify field mappings and type compatibility (API contract test)."""

    async with AsyncClient(app=app, base_url="http://test") as client:
        app.dependency_overrides[get_current_user] = lambda: test_super_user

        # Submit feedback with all fields populated
        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=sample_feedback_payload
        )

        assert response.status_code == 201
        feedback_id = response.json()["feedback_id"]

        # Retrieve from database and verify field types
        from sqlalchemy import select
        from app.models.quality_analysis import ExpertFeedback, ItalianFeedbackCategory

        result = await db_session.execute(
            select(ExpertFeedback).where(ExpertFeedback.id == feedback_id)
        )
        feedback_record = result.scalar_one()

        # Verify UUID type
        assert isinstance(feedback_record.id, UUID)
        assert isinstance(feedback_record.query_id, UUID)
        assert isinstance(feedback_record.expert_id, UUID)

        # Verify enum mapping
        assert feedback_record.category == ItalianFeedbackCategory.CALCOLO_SBAGLIATO

        # Verify ARRAY fields
        assert isinstance(feedback_record.improvement_suggestions, list)
        assert len(feedback_record.improvement_suggestions) == 2
        assert feedback_record.improvement_suggestions[0] == "Aggiungere casi specifici per UE"

        assert isinstance(feedback_record.regulatory_references, list)
        assert "Art. 1, comma 54-89, L. 190/2014" in feedback_record.regulatory_references

        # Verify timestamp auto-populated
        assert feedback_record.feedback_timestamp is not None
        assert feedback_record.created_at is not None
        assert feedback_record.updated_at is not None
```

---

### E2E-08: Golden Set Workflow Integration (S127-S130)

**Purpose:** Verify "correct" feedback triggers Golden Set workflow (S127-S130) and FAQ is created

**Test Steps:**
1. Submit "correct" feedback
2. Wait for background task to complete
3. Verify `generated_faq_id` populated
4. Verify FAQ entry exists in `faq_entries` table
5. Verify feedback linked to FAQ via foreign key
6. Verify cache invalidation triggered

**Expected Outcomes:**
- ✅ `generated_faq_id` populated after background task
- ✅ FAQ entry exists with correct content
- ✅ Foreign key relationship works (feedback → faq_entries)

**Code Example:**
```python
@pytest.mark.asyncio
async def test_e2e_golden_set_workflow_integration(
    db_session,
    test_super_user,
    test_expert_profile,
    sample_feedback_payload
):
    """E2E-08: Verify Golden Set workflow (S127-S130) integration."""

    payload = sample_feedback_payload.copy()
    payload["feedback_type"] = "correct"
    payload.pop("additional_details")  # Not needed for correct

    async with AsyncClient(app=app, base_url="http://test") as client:
        app.dependency_overrides[get_current_user] = lambda: test_super_user

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=payload
        )

        assert response.status_code == 201
        feedback_id = response.json()["feedback_id"]

        # Wait for background task (Golden Set workflow)
        import asyncio
        await asyncio.sleep(3)

        # Refresh feedback record
        from sqlalchemy import select
        from app.models.quality_analysis import ExpertFeedback

        result = await db_session.execute(
            select(ExpertFeedback).where(ExpertFeedback.id == feedback_id)
        )
        feedback_record = result.scalar_one()

        # Verify FAQ generated
        assert feedback_record.generated_faq_id is not None
        assert feedback_record.task_creation_success is True

        # Verify FAQ entry exists
        from app.models.faq import FAQEntry  # Assuming this model exists

        result = await db_session.execute(
            select(FAQEntry).where(FAQEntry.id == feedback_record.generated_faq_id)
        )
        faq_entry = result.scalar_one_or_none()

        assert faq_entry is not None
        assert payload["query_text"] in faq_entry.question
```

---

### E2E-09: Error Recovery & Transaction Rollback

**Purpose:** Verify graceful error handling and database transaction rollback

**Test Steps:**
1. Submit feedback that triggers file write failure → Verify transaction rolled back
2. Submit feedback with mock database failure → Verify no file created
3. Verify error messages are user-friendly (no stack traces in API response)

**Expected Outcomes:**
- ✅ Database rollback on file write failure
- ✅ No partial data persisted
- ✅ User-friendly error messages

**Code Example:**
```python
@pytest.mark.asyncio
async def test_e2e_error_recovery_transaction_rollback(
    db_session,
    test_super_user,
    test_expert_profile,
    sample_feedback_payload,
    temp_project_root
):
    """E2E-09: Verify error recovery and transaction rollback."""

    from unittest.mock import patch
    from app.services.task_generator_service import TaskGeneratorService

    # Force file write failure
    def mock_append_to_file_failure(*args, **kwargs):
        raise IOError("Disk full")

    with patch.object(TaskGeneratorService, "_append_to_file", side_effect=mock_append_to_file_failure):
        async with AsyncClient(app=app, base_url="http://test") as client:
            app.dependency_overrides[get_current_user] = lambda: test_super_user

            response = await client.post(
                "/api/v1/expert-feedback/submit",
                json=sample_feedback_payload
            )

            # API should still return 201 (feedback submission doesn't fail)
            # But task_creation_success should be False
            assert response.status_code == 201
            feedback_id = response.json()["feedback_id"]

            # Wait for background task to fail
            import asyncio
            await asyncio.sleep(2)

            # Verify feedback record updated with error
            from sqlalchemy import select
            from app.models.quality_analysis import ExpertFeedback

            result = await db_session.execute(
                select(ExpertFeedback).where(ExpertFeedback.id == feedback_id)
            )
            feedback_record = result.scalar_one()

            assert feedback_record.task_creation_attempted is True
            assert feedback_record.task_creation_success is False
            assert "Disk full" in feedback_record.task_creation_error
```

---

### E2E-10: Background Task Execution

**Purpose:** Verify background tasks execute asynchronously without blocking API response

**Test Steps:**
1. Submit feedback that triggers task generation
2. Measure API response time → Should be <1 second
3. Verify background task completes within 5 seconds
4. Submit multiple feedback requests concurrently → Verify all tasks complete

**Expected Outcomes:**
- ✅ API responds <1 second (doesn't wait for task)
- ✅ Background task completes within 5 seconds
- ✅ Concurrent requests handled correctly

**Code Example:**
```python
@pytest.mark.asyncio
async def test_e2e_background_task_execution(
    db_session,
    test_super_user,
    test_expert_profile,
    sample_feedback_payload,
    temp_project_root
):
    """E2E-10: Verify background tasks execute asynchronously."""

    import time

    async with AsyncClient(app=app, base_url="http://test") as client:
        app.dependency_overrides[get_current_user] = lambda: test_super_user

        start_time = time.time()

        response = await client.post(
            "/api/v1/expert-feedback/submit",
            json=sample_feedback_payload
        )

        api_response_time = time.time() - start_time

        # API should respond quickly (not wait for task generation)
        assert api_response_time < 1.0  # <1 second
        assert response.status_code == 201

        feedback_id = response.json()["feedback_id"]

        # Wait for background task to complete
        import asyncio
        await asyncio.sleep(5)

        # Verify task completed
        from sqlalchemy import select
        from app.models.quality_analysis import ExpertFeedback

        result = await db_session.execute(
            select(ExpertFeedback).where(ExpertFeedback.id == feedback_id)
        )
        feedback_record = result.scalar_one()

        assert feedback_record.task_creation_success is True
        assert feedback_record.generated_task_id is not None
```

---

## Test Execution

### Running E2E Tests

**Command:**
```bash
# Run all E2E tests
uv run pytest tests/e2e/test_expert_feedback_e2e.py -v

# Run specific scenario
uv run pytest tests/e2e/test_expert_feedback_e2e.py::test_e2e_incomplete_feedback_task_generation -v

# Run with coverage
uv run pytest tests/e2e/test_expert_feedback_e2e.py --cov=app --cov-report=html
```

### Test Execution Time

**Target:** <30 seconds total for all E2E tests

| Scenario | Estimated Time |
|----------|---------------|
| E2E-01 | 2s |
| E2E-02 | 4s (includes file I/O) |
| E2E-03 | 4s |
| E2E-04 | 3s |
| E2E-05 | 2s |
| E2E-06 | 2s |
| E2E-07 | 2s |
| E2E-08 | 5s (includes background task) |
| E2E-09 | 3s |
| E2E-10 | 6s (includes timing checks) |
| **Total** | **33s** |

**Optimization:** Use fixtures to avoid redundant database setup

---

## Test Data Cleanup

### Automatic Cleanup (Preferred)

**Approach:** Use database transactions with automatic rollback

```python
@pytest.fixture
async def db_session(test_engine):
    """Each test gets a fresh session with automatic rollback."""
    async with async_session_maker() as session:
        async with session.begin():
            yield session
            await session.rollback()  # Rollback all changes
```

### Manual Cleanup (If Needed)

**Approach:** Delete test data explicitly

```python
@pytest.fixture
async def cleanup_test_data(db_session):
    """Clean up test data after test runs."""
    yield

    # Delete test feedback
    await db_session.execute(
        delete(ExpertFeedback).where(
            ExpertFeedback.query_text.like("%TEST_%")
        )
    )
    await db_session.commit()
```

### File System Cleanup

**Approach:** Use temporary directories (`tmp_path` fixture)

```python
@pytest.fixture
def temp_project_root(tmp_path):
    """Temporary directory auto-deleted after test."""
    yield tmp_path
    # tmp_path automatically cleaned up by pytest
```

---

## CI/CD Integration

### GitHub Actions Workflow

**File:** `.github/workflows/e2e-tests.yml`

```yaml
name: E2E Integration Tests

on:
  pull_request:
    branches: [master, develop]
  push:
    branches: [master, develop]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: pratiko_ai_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: uv sync

      - name: Run database migrations
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/pratiko_ai_test
        run: uv run alembic upgrade head

      - name: Run E2E tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/pratiko_ai_test
          REDIS_URL: redis://localhost:6379
        run: |
          uv run pytest tests/e2e/test_expert_feedback_e2e.py -v \
            --cov=app \
            --cov-report=term \
            --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

---

## Implementation Checklist

### Phase 1: Setup (Day 1)
- [ ] Create test database configuration (`conftest.py`)
- [ ] Create test fixtures (`fixtures/expert_feedback_fixtures.py`)
- [ ] Set up temporary file system fixtures
- [ ] Verify test database connection

### Phase 2: Core E2E Tests (Days 2-4)
- [ ] Implement E2E-01: Correct feedback workflow
- [ ] Implement E2E-02: Incomplete feedback with task generation
- [ ] Implement E2E-03: Incorrect feedback with task generation
- [ ] Implement E2E-04: Authentication & authorization RBAC
- [ ] Implement E2E-05: Validation errors

### Phase 3: Advanced E2E Tests (Days 5-6)
- [ ] Implement E2E-06: Database constraints
- [ ] Implement E2E-07: Field mappings & type compatibility
- [ ] Implement E2E-08: Golden Set workflow integration
- [ ] Implement E2E-09: Error recovery & transaction rollback
- [ ] Implement E2E-10: Background task execution

### Phase 4: CI/CD & Documentation (Day 7)
- [ ] Add E2E tests to GitHub Actions workflow
- [ ] Document test execution instructions
- [ ] Update coverage thresholds (if needed)
- [ ] Create test data fixtures for manual testing

---

## Expected Coverage Impact

**Current Coverage:** ~4%
**After Unit Tests:** ~45% (API + Service layers)
**After E2E Tests:** ~55-60% (Full integration paths)

**Coverage Breakdown:**
- `app/api/v1/expert_feedback.py`: 80% → 95%
- `app/services/expert_feedback_collector.py`: 70% → 90%
- `app/services/task_generator_service.py`: 75% → 95%
- `app/schemas/expert_feedback.py`: 85% → 100%

---

## Success Criteria

### Test Quality
- ✅ All E2E tests pass consistently
- ✅ No flaky tests (tests pass 100% of the time)
- ✅ Tests complete in <30 seconds total
- ✅ Coverage increased to ≥55%

### Bug Detection
- ✅ API contract mismatches caught by E2E-07
- ✅ Database constraint violations caught by E2E-06
- ✅ File system errors caught by E2E-09
- ✅ Background task failures caught by E2E-10

### Maintainability
- ✅ Test fixtures reusable across scenarios
- ✅ Test data cleanup automatic
- ✅ Tests run in CI/CD pipeline
- ✅ Documentation clear and actionable

---

## FAQ

### Q: Why not mock the database?
**A:** Mocking the database hides integration bugs like constraint violations, type mismatches, and FK issues. E2E tests need real database transactions to catch these bugs.

### Q: How do we avoid slow tests?
**A:** Use database transaction rollback instead of recreating tables. Use temporary directories for file I/O. Run background tasks with shorter timeouts in tests.

### Q: What if tests are flaky due to background tasks?
**A:** Use explicit waits with timeouts. Check task completion status in database instead of relying on sleep(). Mock external dependencies (email, Redis) that introduce non-determinism.

### Q: Should we test the Golden Set workflow (S127-S130)?
**A:** Yes, but with mocked orchestrator steps to avoid complex LLM interactions. Verify the workflow is triggered and `generated_faq_id` is populated.

### Q: How do we test error scenarios?
**A:** Use `pytest.raises()` for expected exceptions. Use mocking to force error conditions (disk full, network timeout). Verify error messages are user-friendly.

---

## References

**Related Documents:**
- `EXPERT_FEEDBACK_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `DEPLOYMENT_EXPERT_FEEDBACK_SCHEMA.md` - Database schema
- `GOLDEN_SET_WORKFLOW_INTEGRATION.md` - Golden Set integration

**Code Files:**
- `app/api/v1/expert_feedback.py` - API endpoints
- `app/services/expert_feedback_collector.py` - Service layer
- `app/services/task_generator_service.py` - Task generation
- `app/schemas/expert_feedback.py` - Pydantic schemas
- `app/models/quality_analysis.py` - Database models

**Existing Tests:**
- `tests/api/test_expert_feedback.py` - API unit tests (17 tests)
- `tests/services/test_task_generator_service.py` - Service unit tests (18 tests)

---

**Document End**

Next Steps: Implement E2E test scenarios starting with Phase 1 (Setup) and Phase 2 (Core E2E Tests).
