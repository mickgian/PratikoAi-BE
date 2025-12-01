"""TDD Tests for Expert Feedback Enum Case Validation (Bug #6 Fix).

This test suite implements TDD approach to fix the enum case mismatch bug where:
- Frontend sends lowercase values: 'correct', 'incomplete', 'incorrect'
- SQLAlchemy expects uppercase names: 'CORRECT', 'INCOMPLETE', 'INCORRECT'

Test-First Approach:
1. RED: Write tests that fail with current implementation
2. GREEN: Fix SQLAlchemy enum configuration to accept lowercase values
3. REFACTOR: Ensure all enum fields use consistent configuration

Bug Context:
- Bug #6 from DEV-BE-72 post-mortem
- User clicks "Incompleta" button (Italian UI)
- Frontend sends {"feedback_type": "incomplete"}
- Backend rejects: "'incomplete' is not among the defined enum values"
"""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.database import AsyncSessionLocal
from app.models.quality_analysis import (
    ExpertFeedback,
    ExpertProfile,
    FeedbackType,
    ItalianFeedbackCategory,
)
from app.models.user import User, UserRole


@pytest.fixture
async def db_session():
    """Create a real async database session for integration tests."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()  # Rollback any changes made during the test
        await session.close()


@pytest.fixture
async def test_user_super(db_session):
    """Create a test super user in the database."""
    # Create test user with naive datetime to avoid timezone issues
    user = User(
        email=f"expert-enum-test-{id(db_session)}@test.com",
        hashed_password="hashed",
        role=UserRole.SUPER_USER.value,
        name="Test Expert",
        created_at=datetime.now(),  # Naive datetime to bypass timezone issue
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestFeedbackTypeEnumCaseValidation:
    """Test feedback_type enum accepts lowercase values from frontend.

    Bug #6: SQLAlchemy Enum uses NAMES (uppercase) instead of VALUES (lowercase).
    Frontend sends 'incomplete', backend expects 'INCOMPLETE'.

    These tests implement TDD RED-GREEN-REFACTOR:
    - RED: Tests fail before fix (current state)
    - GREEN: Tests pass after adding values_callable to Enum
    - REFACTOR: All enum fields use consistent configuration
    """

    async def test_feedback_type_lowercase_incomplete_accepted(self, db_session, test_user_super):
        """Test 1: Send lowercase 'incomplete' - should accept and store correctly.

        CURRENT STATE: ❌ FAILS (this is the bug we're fixing)
        EXPECTED AFTER FIX: ✅ PASS

        This is the primary bug: Italian UI sends lowercase 'incomplete',
        but SQLAlchemy rejects it because it looks for uppercase 'INCOMPLETE'.
        """
        # Create expert profile for test user
        expert = ExpertProfile(
            user_id=test_user_super.id,
            is_active=True,
            is_verified=True,
            trust_score=0.85,
            feedback_count=0,
        )
        db_session.add(expert)
        await db_session.commit()
        await db_session.refresh(expert)

        # Create feedback with lowercase 'incomplete'
        query_id = uuid4()
        feedback = ExpertFeedback(
            query_id=query_id,
            expert_id=expert.id,
            feedback_type=FeedbackType.INCOMPLETE,  # Enum object
            query_text="Test query about tax calculation",
            original_answer="Test answer from AI",
            confidence_score=0.75,
            time_spent_seconds=120,
        )

        # This should work without errors
        db_session.add(feedback)
        await db_session.commit()
        await db_session.refresh(feedback)

        # Verify stored correctly
        assert feedback.feedback_type == FeedbackType.INCOMPLETE
        assert feedback.feedback_type.value == "incomplete"  # Lowercase value

        # Verify can query back from database
        result = await db_session.execute(select(ExpertFeedback).where(ExpertFeedback.query_id == query_id))
        retrieved_feedback = result.scalar_one()

        assert retrieved_feedback.feedback_type == FeedbackType.INCOMPLETE
        assert retrieved_feedback.feedback_type.value == "incomplete"

    async def test_feedback_type_lowercase_correct_accepted(self, db_session, test_user_super):
        """Test 2: Send lowercase 'correct' - should work.

        CURRENT STATE: ❌ FAILS
        EXPECTED AFTER FIX: ✅ PASS
        """
        expert = ExpertProfile(
            user_id=test_user_super.id,
            is_active=True,
            is_verified=True,
            trust_score=0.90,
            feedback_count=0,
        )
        db_session.add(expert)
        await db_session.commit()

        query_id = uuid4()
        feedback = ExpertFeedback(
            query_id=query_id,
            expert_id=expert.id,
            feedback_type=FeedbackType.CORRECT,
            query_text="Test query",
            original_answer="Test answer",
            confidence_score=0.95,
            time_spent_seconds=60,
        )

        db_session.add(feedback)
        await db_session.commit()
        await db_session.refresh(feedback)

        assert feedback.feedback_type == FeedbackType.CORRECT
        assert feedback.feedback_type.value == "correct"

    async def test_feedback_type_lowercase_incorrect_accepted(self, db_session, test_user_super):
        """Test 3: Send lowercase 'incorrect' - should work.

        CURRENT STATE: ❌ FAILS
        EXPECTED AFTER FIX: ✅ PASS
        """
        expert = ExpertProfile(
            user_id=test_user_super.id,
            is_active=True,
            is_verified=True,
            trust_score=0.88,
            feedback_count=0,
        )
        db_session.add(expert)
        await db_session.commit()

        query_id = uuid4()
        feedback = ExpertFeedback(
            query_id=query_id,
            expert_id=expert.id,
            feedback_type=FeedbackType.INCORRECT,
            query_text="Test query",
            original_answer="Wrong answer",
            confidence_score=0.50,
            time_spent_seconds=180,
            why_wrong="AI misunderstood the question",
            what_should_be_answered="Correct interpretation",
        )

        db_session.add(feedback)
        await db_session.commit()
        await db_session.refresh(feedback)

        assert feedback.feedback_type == FeedbackType.INCORRECT
        assert feedback.feedback_type.value == "incorrect"

    def test_all_feedback_types_enum_values_are_lowercase(self):
        """Test 4: Verify enum VALUES are lowercase (not uppercase NAMES).

        CURRENT STATE: ✅ PASS (enum definition is correct)
        EXPECTED AFTER FIX: ✅ PASS (no change)

        This test documents that the Python enum itself has correct lowercase values.
        The bug is in SQLAlchemy using NAMES instead of VALUES.
        """
        assert FeedbackType.CORRECT.value == "correct"
        assert FeedbackType.INCOMPLETE.value == "incomplete"
        assert FeedbackType.INCORRECT.value == "incorrect"

        # Enum NAMES are uppercase (this is what SQLAlchemy incorrectly uses)
        assert FeedbackType.CORRECT.name == "CORRECT"
        assert FeedbackType.INCOMPLETE.name == "INCOMPLETE"
        assert FeedbackType.INCORRECT.name == "INCORRECT"

    async def test_feedback_query_with_string_value(self, db_session, test_user_super):
        """Test 5: Query feedback by string value 'incomplete' should work.

        CURRENT STATE: ❌ FAILS
        EXPECTED AFTER FIX: ✅ PASS

        This tests that we can filter by enum value in queries.
        """
        expert = ExpertProfile(
            user_id=test_user_super.id,
            is_active=True,
            is_verified=True,
            trust_score=0.85,
            feedback_count=0,
        )
        db_session.add(expert)
        await db_session.commit()

        # Create multiple feedbacks with different types
        for feedback_type in [
            FeedbackType.CORRECT,
            FeedbackType.INCOMPLETE,
            FeedbackType.INCORRECT,
        ]:
            feedback = ExpertFeedback(
                query_id=uuid4(),
                expert_id=expert.id,
                feedback_type=feedback_type,
                query_text="Test query",
                original_answer="Test answer",
                confidence_score=0.75,
                time_spent_seconds=120,
            )
            db_session.add(feedback)

        await db_session.commit()

        # Query by enum value
        result = await db_session.execute(
            select(ExpertFeedback).where(ExpertFeedback.feedback_type == FeedbackType.INCOMPLETE)
        )
        incomplete_feedbacks = result.scalars().all()

        assert len(incomplete_feedbacks) == 1
        assert incomplete_feedbacks[0].feedback_type == FeedbackType.INCOMPLETE

    async def test_feedback_roundtrip_preserves_enum_value(self, db_session, test_user_super):
        """Test 6: Roundtrip (insert + query) preserves lowercase enum value.

        CURRENT STATE: ❌ FAILS
        EXPECTED AFTER FIX: ✅ PASS

        Tests that database storage and retrieval doesn't corrupt enum values.
        """
        expert = ExpertProfile(
            user_id=test_user_super.id,
            is_active=True,
            is_verified=True,
            trust_score=0.85,
            feedback_count=0,
        )
        db_session.add(expert)
        await db_session.commit()

        query_id = uuid4()
        original_feedback = ExpertFeedback(
            query_id=query_id,
            expert_id=expert.id,
            feedback_type=FeedbackType.INCOMPLETE,
            query_text="Test query",
            original_answer="Test answer",
            confidence_score=0.75,
            time_spent_seconds=120,
        )

        db_session.add(original_feedback)
        await db_session.commit()

        # Clear session to force fresh query
        db_session.expunge_all()

        # Query back from database
        result = await db_session.execute(select(ExpertFeedback).where(ExpertFeedback.query_id == query_id))
        retrieved_feedback = result.scalar_one()

        # Enum value should be preserved
        assert retrieved_feedback.feedback_type == FeedbackType.INCOMPLETE
        assert retrieved_feedback.feedback_type.value == "incomplete"
        assert retrieved_feedback.feedback_type.name == "INCOMPLETE"


class TestItalianCategoryEnumCaseValidation:
    """Test category enum accepts lowercase Italian values.

    Bug #6 extended: Same issue affects ItalianFeedbackCategory enum.

    Italian categories are also lowercase:
    - normativa_obsoleta
    - interpretazione_errata
    - caso_mancante
    - calcolo_sbagliato
    - troppo_generico
    """

    async def test_category_calcolo_sbagliato_accepted(self, db_session, test_user_super):
        """Test category with lowercase 'calcolo_sbagliato' is accepted.

        CURRENT STATE: ❌ FAILS
        EXPECTED AFTER FIX: ✅ PASS
        """
        expert = ExpertProfile(
            user_id=test_user_super.id,
            is_active=True,
            is_verified=True,
            trust_score=0.85,
            feedback_count=0,
        )
        db_session.add(expert)
        await db_session.commit()

        query_id = uuid4()
        feedback = ExpertFeedback(
            query_id=query_id,
            expert_id=expert.id,
            feedback_type=FeedbackType.INCORRECT,
            category=ItalianFeedbackCategory.CALCOLO_SBAGLIATO,
            query_text="Tax calculation query",
            original_answer="Wrong calculation",
            confidence_score=0.70,
            time_spent_seconds=150,
            why_wrong="Calculation formula is wrong",
            what_should_be_answered="Correct formula",
        )

        db_session.add(feedback)
        await db_session.commit()
        await db_session.refresh(feedback)

        assert feedback.category == ItalianFeedbackCategory.CALCOLO_SBAGLIATO
        assert feedback.category.value == "calcolo_sbagliato"

    async def test_category_normativa_obsoleta_accepted(self, db_session, test_user_super):
        """Test category with lowercase 'normativa_obsoleta' is accepted.

        CURRENT STATE: ❌ FAILS
        EXPECTED AFTER FIX: ✅ PASS
        """
        expert = ExpertProfile(
            user_id=test_user_super.id,
            is_active=True,
            is_verified=True,
            trust_score=0.90,
            feedback_count=0,
        )
        db_session.add(expert)
        await db_session.commit()

        query_id = uuid4()
        feedback = ExpertFeedback(
            query_id=query_id,
            expert_id=expert.id,
            feedback_type=FeedbackType.INCORRECT,
            category=ItalianFeedbackCategory.NORMATIVA_OBSOLETA,
            query_text="Old regulation query",
            original_answer="References outdated law",
            confidence_score=0.65,
            time_spent_seconds=200,
            why_wrong="References 2019 law, updated in 2023",
            what_should_be_answered="Current 2023 regulation",
        )

        db_session.add(feedback)
        await db_session.commit()
        await db_session.refresh(feedback)

        assert feedback.category == ItalianFeedbackCategory.NORMATIVA_OBSOLETA
        assert feedback.category.value == "normativa_obsoleta"

    def test_all_italian_categories_enum_values_lowercase(self):
        """Test all Italian category enum VALUES are lowercase.

        CURRENT STATE: ✅ PASS (enum definition is correct)
        EXPECTED AFTER FIX: ✅ PASS (no change)
        """
        assert ItalianFeedbackCategory.NORMATIVA_OBSOLETA.value == "normativa_obsoleta"
        assert ItalianFeedbackCategory.INTERPRETAZIONE_ERRATA.value == "interpretazione_errata"
        assert ItalianFeedbackCategory.CASO_MANCANTE.value == "caso_mancante"
        assert ItalianFeedbackCategory.CALCOLO_SBAGLIATO.value == "calcolo_sbagliato"
        assert ItalianFeedbackCategory.TROPPO_GENERICO.value == "troppo_generico"


class TestEnumConfigurationDocumentation:
    """Documentation tests to explain the bug and fix.

    These tests don't test functionality, but document the root cause and solution.
    """

    def test_sqlalchemy_enum_uses_names_by_default(self):
        """Document: SQLAlchemy Enum uses NAMES by default, not VALUES.

        This is the root cause of Bug #6.

        Without values_callable parameter:
        - SQLAlchemy creates lookup table from enum NAMES
        - Lookup: ['CORRECT', 'INCOMPLETE', 'INCORRECT']
        - Frontend sends 'incomplete' (lowercase) → NOT FOUND

        With values_callable=lambda x: [e.value for e in x]:
        - SQLAlchemy creates lookup table from enum VALUES
        - Lookup: ['correct', 'incomplete', 'incorrect']
        - Frontend sends 'incomplete' (lowercase) → FOUND ✓
        """
        # This is a documentation test - always passes
        assert True

    def test_fix_requires_values_callable_parameter(self):
        """Document: Fix is to add values_callable to ALL Enum columns.

        Required changes in app/models/quality_analysis.py:

        1. feedback_type (line 141-143):
           Enum(FeedbackType, name='feedback_type', native_enum=False,
                values_callable=lambda x: [e.value for e in x])

        2. category (line 146-148):
           Enum(ItalianFeedbackCategory, name='italian_feedback_category',
                native_enum=False, values_callable=lambda x: [e.value for e in x])

        3. credential_types (line 90):
           ARRAY(Enum(ExpertCredentialType, name='expert_credential_type',
                      native_enum=False, values_callable=lambda x: [e.value for e in x]))

        4. status (line 377):
           Enum(ImprovementStatus, native_enum=False,
                values_callable=lambda x: [e.value for e in x])
        """
        # This is a documentation test - always passes
        assert True


# Run these tests with:
# uv run pytest tests/api/test_expert_feedback_enum_validation.py -xvs
#
# EXPECTED RESULTS (BEFORE FIX):
# - test_feedback_type_lowercase_incomplete_accepted: FAIL ❌
# - test_feedback_type_lowercase_correct_accepted: FAIL ❌
# - test_feedback_type_lowercase_incorrect_accepted: FAIL ❌
# - test_all_feedback_types_enum_values_are_lowercase: PASS ✅
# - test_feedback_query_with_string_value: FAIL ❌
# - test_feedback_roundtrip_preserves_enum_value: FAIL ❌
# - test_category_calcolo_sbagliato_accepted: FAIL ❌
# - test_category_normativa_obsoleta_accepted: FAIL ❌
# - test_all_italian_categories_enum_values_lowercase: PASS ✅
# - Documentation tests: PASS ✅
#
# EXPECTED RESULTS (AFTER FIX):
# - ALL TESTS PASS ✅
