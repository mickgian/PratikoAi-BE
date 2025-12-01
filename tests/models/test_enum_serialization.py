"""Tests for database enum serialization and deserialization.

These tests validate that Python enum values are correctly written to and read from
PostgreSQL ENUM columns. This is critical for the Expert Feedback System which uses
4 enum fields.

BUGS THIS WOULD HAVE CAUGHT:
- Bug #4: Foreign key to non-existent table (constraint creation issues)
- Bug #6: String to enum conversion (FeedbackType("incomplete") vs FeedbackType.INCOMPLETE)
- Bug #7: Enum serialization (writing enum.value vs enum.name to database)
- Bug #8: Enum deserialization (reading from database and converting back to Python enum)
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AsyncSessionLocal
from app.models.quality_analysis import (
    ExpertCredentialType,
    ExpertFeedback,
    ExpertProfile,
    FeedbackType,
    ItalianFeedbackCategory,
)
from app.models.user import User, UserRole


@pytest.fixture
async def db():
    """Create async database session for testing."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture
async def test_user(db: AsyncSession):
    """Create test user for expert profile."""
    user = User(
        email=f"enum_test_{id(db)}@test.com",
        hashed_password="hashed",
        role=UserRole.SUPER_USER.value,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def test_expert(db: AsyncSession, test_user: User):
    """Create test expert profile."""
    expert = ExpertProfile(
        user_id=test_user.id,
        credential_types=[ExpertCredentialType.DOTTORE_COMMERCIALISTA],
        is_verified=True,
        is_active=True,
    )
    db.add(expert)
    await db.commit()
    await db.refresh(expert)
    return expert


class TestFeedbackTypeEnumSerialization:
    """Test FeedbackType enum serialization/deserialization.

    BUG #6: String to enum conversion
    BUG #7: Enum serialization (value vs name)
    BUG #8: Enum deserialization (reading from database)
    """

    @pytest.mark.asyncio
    async def test_feedback_type_correct_roundtrip(self, db: AsyncSession, test_expert: ExpertProfile):
        """Test CORRECT feedback type enum roundtrip to database."""
        from uuid import uuid4

        feedback = ExpertFeedback(
            query_id=uuid4(),
            expert_id=test_expert.id,
            feedback_type=FeedbackType.CORRECT,  # Bug #6: Use enum directly, not string
            query_text="Test question",
            original_answer="Test answer",
            confidence_score=0.9,
            time_spent_seconds=100,
        )

        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        # Verify it was written correctly (Bug #7: Should store value, not name)
        assert feedback.feedback_type == FeedbackType.CORRECT
        assert feedback.feedback_type.value == "correct"
        assert feedback.feedback_type.name == "CORRECT"

        # Load from database and verify deserialization (Bug #8)
        loaded = await db.get(ExpertFeedback, feedback.id)
        assert loaded is not None
        assert loaded.feedback_type == FeedbackType.CORRECT
        assert loaded.feedback_type.value == "correct"
        assert isinstance(loaded.feedback_type, FeedbackType)

    @pytest.mark.asyncio
    async def test_feedback_type_incomplete_roundtrip(self, db: AsyncSession, test_expert: ExpertProfile):
        """Test INCOMPLETE feedback type enum roundtrip to database."""
        from uuid import uuid4

        feedback = ExpertFeedback(
            query_id=uuid4(),
            expert_id=test_expert.id,
            feedback_type=FeedbackType.INCOMPLETE,
            query_text="Test question",
            original_answer="Test answer",
            confidence_score=0.8,
            time_spent_seconds=120,
        )

        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        assert feedback.feedback_type == FeedbackType.INCOMPLETE
        assert feedback.feedback_type.value == "incomplete"

        # Load from database
        loaded = await db.get(ExpertFeedback, feedback.id)
        assert loaded.feedback_type == FeedbackType.INCOMPLETE
        assert loaded.feedback_type.value == "incomplete"

    @pytest.mark.asyncio
    async def test_feedback_type_incorrect_roundtrip(self, db: AsyncSession, test_expert: ExpertProfile):
        """Test INCORRECT feedback type enum roundtrip to database."""
        from uuid import uuid4

        feedback = ExpertFeedback(
            query_id=uuid4(),
            expert_id=test_expert.id,
            feedback_type=FeedbackType.INCORRECT,
            query_text="Test question",
            original_answer="Test answer",
            confidence_score=0.7,
            time_spent_seconds=150,
        )

        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        assert feedback.feedback_type == FeedbackType.INCORRECT
        assert feedback.feedback_type.value == "incorrect"

        # Load from database
        loaded = await db.get(ExpertFeedback, feedback.id)
        assert loaded.feedback_type == FeedbackType.INCORRECT
        assert loaded.feedback_type.value == "incorrect"

    @pytest.mark.asyncio
    async def test_feedback_type_string_conversion(self, db: AsyncSession, test_expert: ExpertProfile):
        """Test converting string to FeedbackType enum (Bug #6).

        The API receives strings from JSON, which must be converted to enums.
        """
        from uuid import uuid4

        # Simulate API receiving string value
        feedback_type_str = "incomplete"
        feedback_type_enum = FeedbackType(feedback_type_str)  # Bug #6: This conversion must work

        feedback = ExpertFeedback(
            query_id=uuid4(),
            expert_id=test_expert.id,
            feedback_type=feedback_type_enum,
            query_text="Test question",
            original_answer="Test answer",
            confidence_score=0.8,
            time_spent_seconds=100,
        )

        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        assert feedback.feedback_type == FeedbackType.INCOMPLETE
        assert feedback.feedback_type.value == "incomplete"


class TestItalianFeedbackCategoryEnumSerialization:
    """Test ItalianFeedbackCategory enum serialization/deserialization (nullable)."""

    @pytest.mark.asyncio
    async def test_category_roundtrip(self, db: AsyncSession, test_expert: ExpertProfile):
        """Test category enum roundtrip to database."""
        from uuid import uuid4

        feedback = ExpertFeedback(
            query_id=uuid4(),
            expert_id=test_expert.id,
            feedback_type=FeedbackType.INCOMPLETE,
            category=ItalianFeedbackCategory.CALCOLO_SBAGLIATO,  # Enum, not string
            query_text="Test question",
            original_answer="Test answer",
            confidence_score=0.8,
            time_spent_seconds=100,
        )

        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        assert feedback.category == ItalianFeedbackCategory.CALCOLO_SBAGLIATO
        assert feedback.category.value == "calcolo_sbagliato"

        # Load from database
        loaded = await db.get(ExpertFeedback, feedback.id)
        assert loaded.category == ItalianFeedbackCategory.CALCOLO_SBAGLIATO
        assert loaded.category.value == "calcolo_sbagliato"

    @pytest.mark.asyncio
    async def test_category_nullable(self, db: AsyncSession, test_expert: ExpertProfile):
        """Test category can be NULL (optional field)."""
        from uuid import uuid4

        feedback = ExpertFeedback(
            query_id=uuid4(),
            expert_id=test_expert.id,
            feedback_type=FeedbackType.CORRECT,
            category=None,  # NULL is allowed
            query_text="Test question",
            original_answer="Test answer",
            confidence_score=0.9,
            time_spent_seconds=100,
        )

        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        assert feedback.category is None

        # Load from database
        loaded = await db.get(ExpertFeedback, feedback.id)
        assert loaded.category is None

    @pytest.mark.asyncio
    async def test_all_category_values(self, db: AsyncSession, test_expert: ExpertProfile):
        """Test all category enum values can be stored and retrieved."""
        from uuid import uuid4

        categories = [
            ItalianFeedbackCategory.NORMATIVA_OBSOLETA,
            ItalianFeedbackCategory.INTERPRETAZIONE_ERRATA,
            ItalianFeedbackCategory.CASO_MANCANTE,
            ItalianFeedbackCategory.CALCOLO_SBAGLIATO,
            ItalianFeedbackCategory.TROPPO_GENERICO,
        ]

        feedback_ids = []
        for category in categories:
            feedback = ExpertFeedback(
                query_id=uuid4(),
                expert_id=test_expert.id,
                feedback_type=FeedbackType.INCOMPLETE,
                category=category,
                query_text=f"Test {category.value}",
                original_answer="Test answer",
                confidence_score=0.8,
                time_spent_seconds=100,
            )
            db.add(feedback)
            await db.flush()
            feedback_ids.append(feedback.id)

        await db.commit()

        # Verify all were stored correctly
        for i, category in enumerate(categories):
            loaded = await db.get(ExpertFeedback, feedback_ids[i])
            assert loaded.category == category
            assert loaded.category.value == category.value


class TestExpertCredentialTypeArrayEnumSerialization:
    """Test ExpertCredentialType ARRAY enum serialization/deserialization.

    BUG #4: PostgreSQL enum type name mismatch
    BUG #7: Enum serialization for array fields
    BUG #8: Enum deserialization for array fields
    """

    @pytest.mark.asyncio
    async def test_credential_types_single_value(self, db: AsyncSession, test_user: User):
        """Test single credential type in array."""
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[ExpertCredentialType.DOTTORE_COMMERCIALISTA],
            is_verified=True,
            is_active=True,
        )

        db.add(expert)
        await db.commit()
        await db.refresh(expert)

        assert len(expert.credential_types) == 1
        assert ExpertCredentialType.DOTTORE_COMMERCIALISTA in expert.credential_types

        # Load from database
        loaded = await db.get(ExpertProfile, expert.id)
        assert len(loaded.credential_types) == 1
        assert ExpertCredentialType.DOTTORE_COMMERCIALISTA in loaded.credential_types

    @pytest.mark.asyncio
    async def test_credential_types_multiple_values(self, db: AsyncSession, test_user: User):
        """Test multiple credential types in array (Bug #7: array enum serialization)."""
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[
                ExpertCredentialType.DOTTORE_COMMERCIALISTA,
                ExpertCredentialType.REVISORE_LEGALE,
                ExpertCredentialType.CONSULENTE_FISCALE,
            ],
            is_verified=True,
            is_active=True,
        )

        db.add(expert)
        await db.commit()
        await db.refresh(expert)

        assert len(expert.credential_types) == 3
        assert ExpertCredentialType.DOTTORE_COMMERCIALISTA in expert.credential_types
        assert ExpertCredentialType.REVISORE_LEGALE in expert.credential_types
        assert ExpertCredentialType.CONSULENTE_FISCALE in expert.credential_types

        # Load from database (Bug #8: array enum deserialization)
        loaded = await db.get(ExpertProfile, expert.id)
        assert len(loaded.credential_types) == 3
        assert ExpertCredentialType.DOTTORE_COMMERCIALISTA in loaded.credential_types
        assert ExpertCredentialType.REVISORE_LEGALE in loaded.credential_types
        assert ExpertCredentialType.CONSULENTE_FISCALE in loaded.credential_types

    @pytest.mark.asyncio
    async def test_credential_types_empty_array(self, db: AsyncSession, test_user: User):
        """Test empty credential types array."""
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[],  # Empty array
            is_verified=True,
            is_active=True,
        )

        db.add(expert)
        await db.commit()
        await db.refresh(expert)

        assert expert.credential_types == []

        # Load from database
        loaded = await db.get(ExpertProfile, expert.id)
        assert loaded.credential_types == []

    @pytest.mark.asyncio
    async def test_credential_types_admin(self, db: AsyncSession, test_user: User):
        """Test ADMIN credential type (Bug #4: enum type must include ADMIN)."""
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[ExpertCredentialType.ADMIN],
            is_verified=True,
            is_active=True,
        )

        db.add(expert)
        await db.commit()
        await db.refresh(expert)

        assert len(expert.credential_types) == 1
        assert ExpertCredentialType.ADMIN in expert.credential_types

        # Load from database
        loaded = await db.get(ExpertProfile, expert.id)
        assert ExpertCredentialType.ADMIN in loaded.credential_types

    @pytest.mark.asyncio
    async def test_all_credential_types(self, db: AsyncSession, test_user: User):
        """Test all credential types can be stored and retrieved."""
        all_types = [
            ExpertCredentialType.DOTTORE_COMMERCIALISTA,
            ExpertCredentialType.REVISORE_LEGALE,
            ExpertCredentialType.CONSULENTE_FISCALE,
            ExpertCredentialType.CONSULENTE_LAVORO,
            ExpertCredentialType.CAF_OPERATOR,
            ExpertCredentialType.ADMIN,
        ]

        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=all_types,
            is_verified=True,
            is_active=True,
        )

        db.add(expert)
        await db.commit()
        await db.refresh(expert)

        assert len(expert.credential_types) == 6
        for cred_type in all_types:
            assert cred_type in expert.credential_types

        # Load from database
        loaded = await db.get(ExpertProfile, expert.id)
        assert len(loaded.credential_types) == 6
        for cred_type in all_types:
            assert cred_type in loaded.credential_types


class TestEnumQueryFiltering:
    """Test filtering database queries by enum values."""

    @pytest.mark.asyncio
    async def test_filter_by_feedback_type(self, db: AsyncSession, test_expert: ExpertProfile):
        """Test querying feedback by feedback_type enum."""
        from uuid import uuid4

        # Create feedback with different types
        feedback1 = ExpertFeedback(
            query_id=uuid4(),
            expert_id=test_expert.id,
            feedback_type=FeedbackType.CORRECT,
            query_text="Test 1",
            original_answer="Answer 1",
            confidence_score=0.9,
            time_spent_seconds=100,
        )

        feedback2 = ExpertFeedback(
            query_id=uuid4(),
            expert_id=test_expert.id,
            feedback_type=FeedbackType.INCOMPLETE,
            query_text="Test 2",
            original_answer="Answer 2",
            confidence_score=0.8,
            time_spent_seconds=120,
        )

        db.add_all([feedback1, feedback2])
        await db.commit()

        # Query for INCOMPLETE feedback
        result = await db.execute(
            select(ExpertFeedback).where(ExpertFeedback.feedback_type == FeedbackType.INCOMPLETE)
        )
        incomplete_feedback = result.scalars().all()

        assert len(incomplete_feedback) >= 1
        for f in incomplete_feedback:
            assert f.feedback_type == FeedbackType.INCOMPLETE

    @pytest.mark.asyncio
    async def test_filter_by_category(self, db: AsyncSession, test_expert: ExpertProfile):
        """Test querying feedback by category enum."""
        from uuid import uuid4

        feedback = ExpertFeedback(
            query_id=uuid4(),
            expert_id=test_expert.id,
            feedback_type=FeedbackType.INCOMPLETE,
            category=ItalianFeedbackCategory.CALCOLO_SBAGLIATO,
            query_text="Test question",
            original_answer="Test answer",
            confidence_score=0.8,
            time_spent_seconds=100,
        )

        db.add(feedback)
        await db.commit()

        # Query for specific category
        result = await db.execute(
            select(ExpertFeedback).where(ExpertFeedback.category == ItalianFeedbackCategory.CALCOLO_SBAGLIATO)
        )
        category_feedback = result.scalars().all()

        assert len(category_feedback) >= 1
        for f in category_feedback:
            assert f.category == ItalianFeedbackCategory.CALCOLO_SBAGLIATO

    @pytest.mark.asyncio
    async def test_filter_by_credential_type_array_contains(self, db: AsyncSession, test_user: User):
        """Test querying experts by credential_types array contains."""
        expert1 = ExpertProfile(
            user_id=test_user.id,
            credential_types=[ExpertCredentialType.DOTTORE_COMMERCIALISTA],
            is_verified=True,
            is_active=True,
        )

        db.add(expert1)
        await db.commit()

        # Query for experts with specific credential
        # Note: SQLAlchemy syntax for array contains
        result = await db.execute(
            select(ExpertProfile).where(
                ExpertProfile.credential_types.any(ExpertCredentialType.DOTTORE_COMMERCIALISTA)
            )
        )
        experts = result.scalars().all()

        # At least our test expert should be found
        found = any(e.id == expert1.id for e in experts)
        assert found
