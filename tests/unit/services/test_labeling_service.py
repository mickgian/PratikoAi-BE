"""TDD Tests for DEV-253: Intent Labeling Service.

Tests for expert labeling system to collect training data for HF intent classifier.

Run with: pytest tests/unit/services/test_labeling_service.py -v
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.intent_labeling import IntentLabel, LabeledQuery
from app.services.intent_labeling_service import (
    IntentLabelingService,
    intent_labeling_service,
)


@pytest.fixture
def labeling_service():
    """Create fresh labeling service instance for each test."""
    return IntentLabelingService()


@pytest.fixture
def mock_db():
    """Create a properly configured mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def sample_low_confidence_prediction():
    """Sample HF prediction with low confidence (below threshold)."""
    return {
        "query": "Come si calcola l'imposta sostitutiva?",
        "predicted_intent": "technical_research",
        "confidence": 0.45,  # Below 0.7 threshold
        "all_scores": {
            "technical_research": 0.45,
            "theoretical_definition": 0.30,
            "calculator": 0.15,
            "chitchat": 0.05,
            "golden_set": 0.05,
        },
        "source_query_id": uuid4(),
    }


@pytest.fixture
def sample_high_confidence_prediction():
    """Sample HF prediction with high confidence (above threshold)."""
    return {
        "query": "Ciao, come stai?",
        "predicted_intent": "chitchat",
        "confidence": 0.92,  # Above 0.7 threshold
        "all_scores": {
            "chitchat": 0.92,
            "technical_research": 0.03,
            "theoretical_definition": 0.02,
            "calculator": 0.02,
            "golden_set": 0.01,
        },
        "source_query_id": uuid4(),
    }


class TestCapturePrediction:
    """Test prediction capture for low-confidence classifications."""

    @pytest.mark.asyncio
    async def test_capture_low_confidence_prediction(
        self, labeling_service, mock_db, sample_low_confidence_prediction
    ):
        """Low confidence predictions should be captured for labeling."""
        result_id = await labeling_service.capture_prediction(
            query=sample_low_confidence_prediction["query"],
            predicted_intent=sample_low_confidence_prediction["predicted_intent"],
            confidence=sample_low_confidence_prediction["confidence"],
            all_scores=sample_low_confidence_prediction["all_scores"],
            source_query_id=sample_low_confidence_prediction["source_query_id"],
            db=mock_db,
        )

        # Should capture prediction
        assert result_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_high_confidence_predictions(
        self, labeling_service, mock_db, sample_high_confidence_prediction
    ):
        """High confidence predictions should NOT be captured (no need for labeling)."""
        result_id = await labeling_service.capture_prediction(
            query=sample_high_confidence_prediction["query"],
            predicted_intent=sample_high_confidence_prediction["predicted_intent"],
            confidence=sample_high_confidence_prediction["confidence"],
            all_scores=sample_high_confidence_prediction["all_scores"],
            source_query_id=sample_high_confidence_prediction["source_query_id"],
            db=mock_db,
        )

        # Should NOT capture prediction
        assert result_id is None
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_capture_with_boundary_confidence(self, labeling_service, mock_db):
        """Predictions at exactly the threshold should be captured."""
        result_id = await labeling_service.capture_prediction(
            query="Test query at boundary",
            predicted_intent="technical_research",
            confidence=0.7,  # Exactly at threshold
            all_scores={"technical_research": 0.7},
            source_query_id=uuid4(),
            db=mock_db,
        )

        # Should NOT capture (threshold is < 0.7, not <=)
        assert result_id is None

    @pytest.mark.asyncio
    async def test_capture_just_below_threshold(self, labeling_service, mock_db):
        """Predictions just below threshold should be captured."""
        result_id = await labeling_service.capture_prediction(
            query="Test query just below",
            predicted_intent="technical_research",
            confidence=0.69,  # Just below 0.7
            all_scores={"technical_research": 0.69},
            source_query_id=uuid4(),
            db=mock_db,
        )

        # Should capture
        assert result_id is not None


class TestGetQueue:
    """Test labeling queue retrieval."""

    @pytest.mark.asyncio
    async def test_get_queue_ordered_by_confidence_asc(self, labeling_service, mock_db):
        """Queue should return queries ordered by confidence (lowest first)."""
        # Mock query results - use SimpleNamespace for clean attribute access
        from types import SimpleNamespace

        mock_queries = [
            SimpleNamespace(
                id=uuid4(),
                query="Low conf query",
                predicted_intent="technical_research",
                confidence=0.35,
                all_scores={"technical_research": 0.35, "chitchat": 0.65},
                expert_intent=None,
                skip_count=0,
                created_at=datetime.utcnow(),
            ),
            SimpleNamespace(
                id=uuid4(),
                query="Medium conf query",
                predicted_intent="calculator",
                confidence=0.55,
                all_scores={"calculator": 0.55, "chitchat": 0.45},
                expert_intent=None,
                skip_count=0,
                created_at=datetime.utcnow(),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_queries
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_db.execute.side_effect = [mock_count_result, mock_result]

        response = await labeling_service.get_queue(page=1, page_size=50, db=mock_db)

        assert response.total_count == 2
        assert len(response.items) == 2
        # Verify order (lowest confidence first)
        assert response.items[0].confidence < response.items[1].confidence

    @pytest.mark.asyncio
    async def test_get_queue_excludes_already_labeled(self, labeling_service, mock_db):
        """Queue should exclude queries that already have expert_intent."""
        from types import SimpleNamespace

        mock_queries = [
            SimpleNamespace(
                id=uuid4(),
                query="Unlabeled query",
                predicted_intent="technical_research",
                confidence=0.45,
                all_scores={"technical_research": 0.45},
                expert_intent=None,
                skip_count=0,
                created_at=datetime.utcnow(),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_queries
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_db.execute.side_effect = [mock_count_result, mock_result]

        response = await labeling_service.get_queue(page=1, page_size=50, db=mock_db)

        assert response.total_count == 1
        assert all(item.expert_intent is None for item in response.items)

    @pytest.mark.asyncio
    async def test_get_queue_pagination(self, labeling_service, mock_db):
        """Queue should support pagination."""
        from types import SimpleNamespace

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 100

        mock_queries = [
            SimpleNamespace(
                id=uuid4(),
                query=f"Query {i}",
                predicted_intent="technical_research",
                confidence=0.5,
                all_scores={"technical_research": 0.5},
                expert_intent=None,
                skip_count=0,
                created_at=datetime.utcnow(),
            )
            for i in range(10)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_queries

        mock_db.execute.side_effect = [mock_count_result, mock_result]

        response = await labeling_service.get_queue(page=2, page_size=10, db=mock_db)

        assert response.total_count == 100
        assert response.page == 2
        assert response.page_size == 10
        assert len(response.items) == 10


class TestSubmitLabel:
    """Test label submission."""

    @pytest.mark.asyncio
    async def test_submit_label_validates_intent(self, labeling_service, mock_db):
        """Submitting label should validate intent is in allowed list."""
        query_id = uuid4()

        # Mock existing query - don't use spec=LabeledQuery to allow free attribute assignment
        mock_query = MagicMock()
        mock_query.id = query_id
        mock_query.query = "Test query text"
        mock_query.predicted_intent = "technical_research"
        mock_query.expert_intent = None
        mock_query.labeled_by = None
        mock_query.labeled_at = None
        mock_query.labeling_notes = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_query
        mock_db.execute.return_value = mock_result

        result = await labeling_service.submit_label(
            query_id=query_id,
            expert_intent=IntentLabel.TECHNICAL_RESEARCH,
            labeled_by=1,
            notes="Test label",
            db=mock_db,
        )

        assert result is not None
        assert mock_query.expert_intent == IntentLabel.TECHNICAL_RESEARCH.value

    @pytest.mark.asyncio
    async def test_invalid_intent_rejected(self, labeling_service, mock_db):
        """Invalid intent values should be rejected."""
        query_id = uuid4()

        with pytest.raises(ValueError, match="Intento non valido"):
            await labeling_service.submit_label(
                query_id=query_id,
                expert_intent="invalid_intent",  # Not in IntentLabel enum
                labeled_by=1,
                notes=None,
                db=mock_db,
            )

    @pytest.mark.asyncio
    async def test_submit_label_updates_timestamp(self, labeling_service, mock_db):
        """Submitting label should update labeled_at timestamp."""
        query_id = uuid4()

        mock_query = MagicMock()
        mock_query.id = query_id
        mock_query.query = "Test query text"
        mock_query.predicted_intent = "chitchat"
        mock_query.expert_intent = None
        mock_query.labeled_by = None
        mock_query.labeled_at = None
        mock_query.labeling_notes = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_query
        mock_db.execute.return_value = mock_result

        before_time = datetime.utcnow()

        await labeling_service.submit_label(
            query_id=query_id,
            expert_intent=IntentLabel.CHITCHAT,
            labeled_by=1,
            notes=None,
            db=mock_db,
        )

        assert mock_query.labeled_at is not None
        assert mock_query.labeled_at >= before_time

    @pytest.mark.asyncio
    async def test_submit_label_query_not_found(self, labeling_service, mock_db):
        """Should raise error if query not found."""
        query_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Query non trovata"):
            await labeling_service.submit_label(
                query_id=query_id,
                expert_intent=IntentLabel.CHITCHAT,
                labeled_by=1,
                notes=None,
                db=mock_db,
            )


class TestStats:
    """Test labeling statistics."""

    @pytest.mark.asyncio
    async def test_stats_calculation_accuracy(self, labeling_service, mock_db):
        """Stats should accurately calculate labeling progress."""
        # get_stats makes: 1 total count + 1 labeled count + 5 per-intent counts = 7 calls
        mock_total = MagicMock()
        mock_total.scalar.return_value = 100

        mock_labeled = MagicMock()
        mock_labeled.scalar.return_value = 45

        # Per-intent counts (5 intents: chitchat, theoretical_definition, technical_research, calculator, golden_set)
        intent_counts = [10, 5, 20, 8, 2]
        intent_mocks = []
        for count in intent_counts:
            m = MagicMock()
            m.scalar.return_value = count
            intent_mocks.append(m)

        mock_db.execute.side_effect = [mock_total, mock_labeled, *intent_mocks]

        stats = await labeling_service.get_stats(db=mock_db)

        assert stats.total_queries == 100
        assert stats.labeled_queries == 45
        assert stats.pending_queries == 55
        assert stats.completion_percentage == 45.0

    @pytest.mark.asyncio
    async def test_stats_handles_zero_total(self, labeling_service, mock_db):
        """Stats should handle zero total queries gracefully."""
        mock_total = MagicMock()
        mock_total.scalar.return_value = 0

        mock_labeled = MagicMock()
        mock_labeled.scalar.return_value = 0

        # Per-intent counts (all zero)
        intent_mocks = []
        for _ in range(5):
            m = MagicMock()
            m.scalar.return_value = 0
            intent_mocks.append(m)

        mock_db.execute.side_effect = [mock_total, mock_labeled, *intent_mocks]

        stats = await labeling_service.get_stats(db=mock_db)

        assert stats.total_queries == 0
        assert stats.labeled_queries == 0
        assert stats.completion_percentage == 0.0


class TestExport:
    """Test training data export."""

    @pytest.mark.asyncio
    async def test_export_jsonl_format(self, labeling_service, mock_db):
        """Export should produce valid JSONL format for HuggingFace."""
        # Mock labeled queries
        mock_queries = [
            MagicMock(
                id=uuid4(),
                query="Come si calcola l'IVA?",
                expert_intent="calculator",
                confidence=0.45,
                labeled_at=datetime.utcnow(),
            ),
            MagicMock(
                id=uuid4(),
                query="Ciao, buongiorno!",
                expert_intent="chitchat",
                confidence=0.55,
                labeled_at=datetime.utcnow(),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_queries
        mock_db.execute.return_value = mock_result

        content, count = await labeling_service.export_training_data(format="jsonl", db=mock_db)

        assert count == 2
        # JSONL: each line is a valid JSON object
        lines = content.strip().split("\n")
        assert len(lines) == 2

        import json

        for line in lines:
            data = json.loads(line)
            assert "text" in data
            assert "label" in data

    @pytest.mark.asyncio
    async def test_export_csv_format(self, labeling_service, mock_db):
        """Export should produce valid CSV format."""
        mock_queries = [
            MagicMock(
                id=uuid4(),
                query="Test query",
                expert_intent="technical_research",
                confidence=0.45,
                labeled_at=datetime.utcnow(),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_queries
        mock_db.execute.return_value = mock_result

        content, count = await labeling_service.export_training_data(format="csv", db=mock_db)

        assert count == 1
        lines = content.strip().split("\n")
        # Header + 1 data row
        assert len(lines) == 2
        assert "text" in lines[0]
        assert "label" in lines[0]

    @pytest.mark.asyncio
    async def test_export_only_labeled_queries(self, labeling_service, mock_db):
        """Export should only include queries with expert_intent."""
        mock_queries = []  # Empty - no labeled queries

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_queries
        mock_db.execute.return_value = mock_result

        content, count = await labeling_service.export_training_data(format="jsonl", db=mock_db)

        assert count == 0
        assert content == ""


class TestSkipQuery:
    """Test query skipping."""

    @pytest.mark.asyncio
    async def test_skip_increments_count(self, labeling_service, mock_db):
        """Skipping should increment skip_count."""
        query_id = uuid4()

        mock_query = MagicMock(spec=LabeledQuery)
        mock_query.id = query_id
        mock_query.skip_count = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_query
        mock_db.execute.return_value = mock_result

        await labeling_service.skip_query(query_id=query_id, db=mock_db)

        assert mock_query.skip_count == 1
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_query_not_found(self, labeling_service, mock_db):
        """Skip should raise error if query not found."""
        query_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Query non trovata"):
            await labeling_service.skip_query(query_id=query_id, db=mock_db)


class TestSingleton:
    """Test singleton pattern."""

    def test_singleton_instance_exists(self):
        """intent_labeling_service singleton should exist."""
        assert intent_labeling_service is not None
        assert isinstance(intent_labeling_service, IntentLabelingService)


class TestConfidenceThreshold:
    """Test configurable confidence threshold."""

    def test_default_threshold_is_0_7(self):
        """Default labeling threshold should be 0.7."""
        service = IntentLabelingService()
        assert service.LABELING_CONFIDENCE_THRESHOLD == 0.7

    @pytest.mark.asyncio
    async def test_custom_threshold(self, mock_db):
        """Service should respect custom threshold."""
        service = IntentLabelingService(labeling_threshold=0.8)

        # At 0.75 confidence: should capture with 0.8 threshold
        result_id = await service.capture_prediction(
            query="Test",
            predicted_intent="chitchat",
            confidence=0.75,
            all_scores={"chitchat": 0.75},
            source_query_id=uuid4(),
            db=mock_db,
        )

        assert result_id is not None  # Captured because 0.75 < 0.8
