"""Tests for Knowledge models."""

from datetime import UTC, datetime

import pytest

from app.models.knowledge import (
    KnowledgeFeedback,
    KnowledgeItem,
    KnowledgeQuery,
    KnowledgeSearchResponse,
)


class TestKnowledgeItem:
    """Test KnowledgeItem model."""

    def test_knowledge_item_creation(self):
        """Test creating a KnowledgeItem."""
        item = KnowledgeItem(
            title="Tax Article",
            content="Content about taxes",
            category="tax",
            source="official_docs",
        )

        assert item.title == "Tax Article"
        assert item.content == "Content about taxes"
        assert item.category == "tax"
        assert item.source == "official_docs"

    def test_knowledge_item_default_language(self):
        """Test KnowledgeItem default language is Italian."""
        item = KnowledgeItem(
            title="Test",
            content="Content",
            category="test",
            source="test",
        )

        assert item.language == "it"

    def test_knowledge_item_default_content_type(self):
        """Test KnowledgeItem default content type."""
        item = KnowledgeItem(
            title="Test",
            content="Content",
            category="test",
            source="test",
        )

        assert item.content_type == "text"

    def test_knowledge_item_default_relevance(self):
        """Test KnowledgeItem default relevance score."""
        item = KnowledgeItem(
            title="Test",
            content="Content",
            category="test",
            source="test",
        )

        assert item.relevance_score == 0.5

    def test_knowledge_item_with_tags(self):
        """Test KnowledgeItem with tags."""
        item = KnowledgeItem(
            title="Test",
            content="Content",
            category="test",
            source="test",
            tags=["irpef", "taxes", "2024"],
        )

        assert len(item.tags) == 3
        assert "irpef" in item.tags

    def test_knowledge_item_default_status(self):
        """Test KnowledgeItem default status."""
        item = KnowledgeItem(
            title="Test",
            content="Content",
            category="test",
            source="test",
        )

        assert item.status == "active"

    def test_knowledge_item_default_version(self):
        """Test KnowledgeItem default version."""
        item = KnowledgeItem(
            title="Test",
            content="Content",
            category="test",
            source="test",
        )

        assert item.version == "1.0"

    def test_knowledge_item_with_subcategory(self):
        """Test KnowledgeItem with subcategory."""
        item = KnowledgeItem(
            title="Test",
            content="Content",
            category="tax",
            subcategory="irpef",
            source="test",
        )

        assert item.subcategory == "irpef"

    def test_knowledge_item_usage_tracking(self):
        """Test KnowledgeItem usage tracking fields."""
        item = KnowledgeItem(
            title="Test",
            content="Content",
            category="test",
            source="test",
        )

        assert item.view_count == 0
        assert item.last_accessed is None

    def test_knowledge_item_quality_metrics(self):
        """Test KnowledgeItem quality metrics."""
        item = KnowledgeItem(
            title="Test",
            content="Content",
            category="test",
            source="test",
        )

        assert item.feedback_count == 0
        assert item.accuracy_score is None
        assert item.user_feedback_score is None


class TestKnowledgeQuery:
    """Test KnowledgeQuery model."""

    def test_knowledge_query_creation(self):
        """Test creating a KnowledgeQuery."""
        query = KnowledgeQuery(query="What are IRPEF brackets?")

        assert query.query == "What are IRPEF brackets?"

    def test_knowledge_query_default_language(self):
        """Test KnowledgeQuery default language."""
        query = KnowledgeQuery(query="Test query")

        assert query.language == "it"

    def test_knowledge_query_default_limit(self):
        """Test KnowledgeQuery default limit."""
        query = KnowledgeQuery(query="Test query")

        assert query.limit == 20

    def test_knowledge_query_default_offset(self):
        """Test KnowledgeQuery default offset."""
        query = KnowledgeQuery(query="Test query")

        assert query.offset == 0

    def test_knowledge_query_default_min_relevance(self):
        """Test KnowledgeQuery default min relevance."""
        query = KnowledgeQuery(query="Test query")

        assert query.min_relevance == 0.01

    def test_knowledge_query_with_category_filter(self):
        """Test KnowledgeQuery with category filter."""
        query = KnowledgeQuery(query="Test", category="tax")

        assert query.category == "tax"

    def test_knowledge_query_with_all_filters(self):
        """Test KnowledgeQuery with all filters."""
        query = KnowledgeQuery(
            query="Test",
            category="tax",
            subcategory="irpef",
            source="official_docs",
            language="it",
            limit=10,
            offset=5,
            min_relevance=0.5,
        )

        assert query.category == "tax"
        assert query.subcategory == "irpef"
        assert query.limit == 10


class TestKnowledgeSearchResponse:
    """Test KnowledgeSearchResponse model."""

    def test_search_response_creation(self):
        """Test creating a KnowledgeSearchResponse."""
        response = KnowledgeSearchResponse(
            query="Test query",
            results=[],
            total_count=0,
            page_size=20,
            page=1,
            search_time_ms=15.5,
        )

        assert response.query == "Test query"
        assert response.total_count == 0
        assert response.search_time_ms == 15.5

    def test_search_response_with_results(self):
        """Test search response with results."""
        results = [
            {"id": 1, "title": "Result 1"},
            {"id": 2, "title": "Result 2"},
        ]
        response = KnowledgeSearchResponse(
            query="Test",
            results=results,
            total_count=2,
            page_size=20,
            page=1,
            search_time_ms=10.0,
        )

        assert len(response.results) == 2
        assert response.total_count == 2

    def test_search_response_default_suggestions(self):
        """Test search response default suggestions."""
        response = KnowledgeSearchResponse(
            query="Test",
            results=[],
            total_count=0,
            page_size=20,
            page=1,
            search_time_ms=10.0,
        )

        assert response.suggestions == []


class TestKnowledgeFeedback:
    """Test KnowledgeFeedback model."""

    def test_feedback_creation(self):
        """Test creating KnowledgeFeedback."""
        feedback = KnowledgeFeedback(
            knowledge_item_id=1,
            user_id="user123",
            session_id="session456",
            rating=5,
            feedback_type="helpful",
        )

        assert feedback.knowledge_item_id == 1
        assert feedback.user_id == "user123"
        assert feedback.rating == 5
        assert feedback.feedback_type == "helpful"

    def test_feedback_with_text(self):
        """Test feedback with text."""
        feedback = KnowledgeFeedback(
            knowledge_item_id=1,
            user_id="user123",
            session_id="session456",
            rating=4,
            feedback_type="accurate",
            feedback_text="Very helpful article",
        )

        assert feedback.feedback_text == "Very helpful article"

    def test_feedback_with_search_query(self):
        """Test feedback with search query context."""
        feedback = KnowledgeFeedback(
            knowledge_item_id=1,
            user_id="user123",
            session_id="session456",
            rating=5,
            feedback_type="helpful",
            search_query="IRPEF 2024",
        )

        assert feedback.search_query == "IRPEF 2024"

    def test_feedback_rating_range(self):
        """Test feedback rating is in valid range."""
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            feedback = KnowledgeFeedback(
                knowledge_item_id=1,
                user_id="user123",
                session_id="session456",
                rating=rating,
                feedback_type="test",
            )
            assert feedback.rating == rating
