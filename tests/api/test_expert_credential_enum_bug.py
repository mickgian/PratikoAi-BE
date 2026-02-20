"""TDD Test for ExpertCredentialType ADMIN enum bug.

User reports 500 error when accessing /api/v1/expert-feedback/experts/me/profile:
"Failed to retrieve expert profile: 'ADMIN' is not among the defined enum values.
 Enum name: expert_credential_type. Possible values: dottore_com.., ..., admin"

Root cause investigation:
- Database column: expert_credential_type[] (native PostgreSQL enum)
- Model setting: native_enum=False (expects VARCHAR)
- Mismatch causes enum conversion errors when reading from database

TDD Approach:
1. RED: Test reading expert profile with credential_types from database
2. GREEN: Fix native_enum setting or enum conversion logic
3. REFACTOR: Ensure all enum arrays work correctly

NOTE: Skipped in CI - requires full database infrastructure.
"""

import os

import pytest

# Skip in CI - requires real database session
if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
    pytest.skip(
        "Expert credential enum tests require full DB infrastructure - skipped in CI",
        allow_module_level=True,
    )

from datetime import datetime

from sqlalchemy import select

from app.models.database import AsyncSessionLocal
from app.models.quality_analysis import ExpertCredentialType, ExpertProfile
from app.models.user import User, UserRole


@pytest.fixture
async def db_session():
    """Create async database session for testing."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture
async def test_user(db_session):
    """Create test user with SUPER_USER role."""
    user = User(
        email=f"credential-enum-test-{id(db_session)}@test.com",
        hashed_password="hashed",  # pragma: allowlist secret
        role=UserRole.SUPER_USER.value,
        name="Test User",
        created_at=datetime.now(),  # Naive datetime
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def expert_with_admin_credential(db_session, test_user):
    """Create expert profile with ADMIN credential type."""
    expert = ExpertProfile(
        user_id=test_user.id,
        credential_types=[ExpertCredentialType.ADMIN],  # This is the problematic field
        is_verified=True,
        is_active=True,
    )
    db_session.add(expert)
    await db_session.commit()
    await db_session.refresh(expert)
    return expert


class TestExpertCredentialTypeEnumBug:
    """Test expert credential_types enum reading from database.

    Bug: 'ADMIN' is not among the defined enum values
    Expected: Should read and convert enum values correctly
    """

    async def test_read_expert_with_admin_credential(self, db_session, expert_with_admin_credential):
        """Test reading expert profile with ADMIN credential from database.

        CURRENT STATE: ❌ FAILS (this is the bug)
        EXPECTED AFTER FIX: ✅ PASS

        This test reproduces the exact error the user is seeing.
        """
        # Query expert profile from database
        result = await db_session.execute(
            select(ExpertProfile).where(ExpertProfile.id == expert_with_admin_credential.id)
        )
        expert = result.scalar_one()

        # Should be able to access credential_types without error
        assert expert.credential_types is not None
        assert len(expert.credential_types) == 1

        # Should be ExpertCredentialType.ADMIN enum member
        assert expert.credential_types[0] == ExpertCredentialType.ADMIN
        assert expert.credential_types[0].value == "admin"
        assert expert.credential_types[0].name == "ADMIN"

    async def test_read_expert_with_multiple_credentials(self, db_session, test_user):
        """Test reading expert with multiple credential types.

        CURRENT STATE: ❌ FAILS
        EXPECTED AFTER FIX: ✅ PASS
        """
        expert = ExpertProfile(
            user_id=test_user.id,
            credential_types=[
                ExpertCredentialType.DOTTORE_COMMERCIALISTA,
                ExpertCredentialType.ADMIN,
            ],
            is_verified=True,
            is_active=True,
        )
        db_session.add(expert)
        await db_session.commit()

        # Clear session to force fresh query
        db_session.expunge_all()

        # Query back from database
        result = await db_session.execute(select(ExpertProfile).where(ExpertProfile.user_id == test_user.id))
        retrieved_expert = result.scalar_one()

        # Should have both credentials
        assert len(retrieved_expert.credential_types) == 2
        assert ExpertCredentialType.DOTTORE_COMMERCIALISTA in retrieved_expert.credential_types
        assert ExpertCredentialType.ADMIN in retrieved_expert.credential_types

    async def test_enum_value_conversion(self, db_session, expert_with_admin_credential):
        """Test that enum values convert correctly to strings for API response.

        CURRENT STATE: ❌ FAILS
        EXPECTED AFTER FIX: ✅ PASS

        This tests the line: credential_types=[ct.value for ct in expert.credential_types]
        """
        result = await db_session.execute(
            select(ExpertProfile).where(ExpertProfile.id == expert_with_admin_credential.id)
        )
        expert = result.scalar_one()

        # Should be able to extract .value from each credential
        credential_values = [ct.value for ct in expert.credential_types]
        assert credential_values == ["admin"]


# Run with: uv run pytest tests/api/test_expert_credential_enum_bug.py -xvs --tb=short
