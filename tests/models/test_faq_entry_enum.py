"""Tests for FAQEntry UpdateSensitivity enum handling.

This test file validates that the UpdateSensitivity enum is properly converted
to its string value (e.g., "medium") when stored in the database, not its name
(e.g., "MEDIUM").

Bug Context: SQLModel was converting enum to name instead of value, causing:
    invalid input value for enum updatesensitivity: "MEDIUM"
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.faq import FAQEntry, UpdateSensitivity


@pytest.mark.asyncio
async def test_update_sensitivity_stores_lowercase_value(db_session: AsyncSession):
    """Test that UpdateSensitivity.MEDIUM is stored as 'medium' not 'MEDIUM'."""
    # Create FAQ entry with MEDIUM sensitivity
    faq = FAQEntry(
        question="Test question",
        answer="Test answer",
        category="test",
        update_sensitivity=UpdateSensitivity.MEDIUM,
    )

    # Add to database
    db_session.add(faq)
    await db_session.commit()
    await db_session.refresh(faq)

    # Verify the value stored is lowercase "medium"
    assert faq.update_sensitivity == UpdateSensitivity.MEDIUM
    assert faq.update_sensitivity.value == "medium"  # Should be lowercase

    # Query from database to verify actual stored value
    from sqlalchemy import select, text

    result = await db_session.execute(
        text("SELECT update_sensitivity FROM faq_entries WHERE id = :id"), {"id": faq.id}
    )
    stored_value = result.scalar_one()

    # The database should have stored "medium" (lowercase), not "MEDIUM"
    assert stored_value == "medium", f"Expected 'medium' but got '{stored_value}'"


@pytest.mark.asyncio
async def test_all_update_sensitivity_values(db_session: AsyncSession):
    """Test that all UpdateSensitivity enum values work correctly."""
    test_cases = [
        (UpdateSensitivity.LOW, "low"),
        (UpdateSensitivity.MEDIUM, "medium"),
        (UpdateSensitivity.HIGH, "high"),
    ]

    for enum_value, expected_string in test_cases:
        faq = FAQEntry(
            question=f"Test {enum_value.name}",
            answer="Test answer",
            category="test",
            update_sensitivity=enum_value,
        )

        db_session.add(faq)
        await db_session.commit()
        await db_session.refresh(faq)

        # Verify enum value
        assert faq.update_sensitivity == enum_value
        assert faq.update_sensitivity.value == expected_string

        # Verify database value
        from sqlalchemy import text

        result = await db_session.execute(
            text("SELECT update_sensitivity FROM faq_entries WHERE id = :id"),
            {"id": faq.id},
        )
        stored_value = result.scalar_one()

        assert stored_value == expected_string, f"Expected '{expected_string}' but got '{stored_value}'"


@pytest.mark.asyncio
async def test_default_update_sensitivity(db_session: AsyncSession):
    """Test that default UpdateSensitivity is MEDIUM."""
    faq = FAQEntry(
        question="Test default sensitivity",
        answer="Test answer",
        category="test",
        # Not specifying update_sensitivity - should default to MEDIUM
    )

    db_session.add(faq)
    await db_session.commit()
    await db_session.refresh(faq)

    # Should default to MEDIUM
    assert faq.update_sensitivity == UpdateSensitivity.MEDIUM
    assert faq.update_sensitivity.value == "medium"
