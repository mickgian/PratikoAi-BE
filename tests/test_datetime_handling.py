"""
TDD Test Suite for DateTime Handling Bugs

These tests reproduce the datetime serialization/deserialization bugs that cause:
1. "'str' object has no attribute 'tzinfo'" errors
2. Resolution 64 search failures
3. Streaming interruptions

RED Phase: These tests should FAIL before fixes
GREEN Phase: These tests should PASS after fixes
"""

from datetime import (
    date,
    datetime,
    timezone,
)
from unittest.mock import Mock

import pytest

from app.services.search_service import SearchResult as SearchServiceResult


def test_search_result_datetime_serialization_deserialization():
    """
    BUG REPRODUCTION: SearchResult datetime fields become strings after cache roundtrip.

    Before fix: Fails with "'str' object has no attribute 'tzinfo'"
    After fix: Passes with datetime objects preserved
    """
    # Create SearchResult with datetime objects
    original = SearchServiceResult(
        id="1",
        title="Test Document",
        content="Test Content",
        category="test_category",
        rank_score=1.0,
        relevance_score=1.0,
        highlight="test",
        updated_at=datetime(2025, 11, 10, 12, 0, 0, tzinfo=timezone.utc),
        publication_date=date(2025, 11, 10),
    )

    # Simulate cache serialization (what happens in _serialize_result)
    serialized = {
        "id": original.id,
        "title": original.title,
        "content": original.content,
        "category": original.category,
        "rank_score": original.rank_score,
        "relevance_score": original.relevance_score,
        "highlight": original.highlight,
        "updated_at": original.updated_at.isoformat() if original.updated_at else None,
        "publication_date": original.publication_date.isoformat() if original.publication_date else None,
        "source": None,
        "source_url": None,
        "knowledge_item_id": None,
        "chunk_index": None,
    }

    # Simulate cache deserialization (JSON roundtrip)
    import json

    json_str = json.dumps(serialized, ensure_ascii=False)
    cached_data = json.loads(json_str)

    # Try to recreate SearchResult from cache
    restored = SearchServiceResult(**cached_data)

    # BUG: updated_at is now a string, not datetime
    assert isinstance(restored.updated_at, datetime), (
        f"Expected datetime, got {type(restored.updated_at).__name__}. " f"Value: {restored.updated_at}"
    )

    assert isinstance(restored.publication_date, date), (
        f"Expected date, got {type(restored.publication_date).__name__}. " f"Value: {restored.publication_date}"
    )

    # Verify datetime has timezone info
    assert restored.updated_at.tzinfo is not None, "DateTime should be timezone-aware after deserialization"


def test_recency_boost_handles_string_datetime():
    """
    BUG REPRODUCTION: _calculate_recency_boost crashes on string datetime.

    Before fix: Raises AttributeError: 'str' object has no attribute 'tzinfo'
    After fix: Handles string datetime gracefully
    """
    from app.services.knowledge_search_service import KnowledgeSearchService

    # Create service with minimal setup
    mock_session = Mock()
    service = KnowledgeSearchService(db_session=mock_session, vector_service=None)

    # BUG: Pass string datetime (what comes from cache after JSON deserialization)
    string_datetime = "2025-11-10T12:00:00+00:00"

    # Should NOT crash with AttributeError
    boost = service._calculate_recency_boost(string_datetime)

    # Should return valid boost value
    assert isinstance(boost, float), f"Expected float, got {type(boost).__name__}"

    assert 0.0 <= boost <= 1.0, f"Boost should be between 0 and 1, got {boost}"

    print(f"✓ Recency boost handles string datetime: {boost:.4f}")


def test_recency_boost_handles_naive_datetime():
    """
    TEST: _calculate_recency_boost handles timezone-naive datetimes.

    Should add UTC timezone automatically.
    """
    from app.services.knowledge_search_service import KnowledgeSearchService

    mock_session = Mock()
    service = KnowledgeSearchService(db_session=mock_session, vector_service=None)

    # Naive datetime (no timezone)
    naive_dt = datetime(2025, 11, 10, 12, 0, 0)

    # Should NOT crash
    boost = service._calculate_recency_boost(naive_dt)

    assert isinstance(boost, float)
    assert 0.0 <= boost <= 1.0

    print(f"✓ Recency boost handles naive datetime: {boost:.4f}")


def test_recency_boost_handles_none():
    """
    TEST: _calculate_recency_boost handles None gracefully.
    """
    from app.services.knowledge_search_service import KnowledgeSearchService

    mock_session = Mock()
    service = KnowledgeSearchService(db_session=mock_session, vector_service=None)

    # None value
    boost = service._calculate_recency_boost(None)

    assert boost == 0.0, "None should return 0.0 boost"

    print("✓ Recency boost handles None correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
