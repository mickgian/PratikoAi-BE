"""Unit tests for two-tier matching in IntelligentFAQService.find_best_match().

This test module verifies the two-tier similarity threshold logic that prevents
regression of the Golden Set bug where similarity_score was incorrectly returning 0.0.

Two-tier thresholds:
- Entity match (same document number, year, etc.): 0.70 threshold
- No entity match (generic semantic similarity): 0.85 threshold

Bug Context:
    Query "Cos'e' la risoluzione n.65 dell'agenzia delle entrate?"
    FAQ "Parlami della risoluzione 65 dell'agenzia dell'entrate"
    Actual similarity: 0.8043

    With single 0.85 threshold: REJECTED (0.8043 < 0.85)
    With two-tier matching: ACCEPTED (entity match + 0.8043 >= 0.70)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.intelligent_faq_service import IntelligentFAQService


class TestTwoTierMatchingThresholds:
    """Test suite for two-tier similarity thresholds in find_best_match()."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create IntelligentFAQService with mocked database."""
        return IntelligentFAQService(mock_db)

    def _create_mock_row(
        self,
        question: str,
        similarity: float,
        id: str = "test-uuid-12345",
        answer: str = "Test answer content",
        category: str = "generale",
    ):
        """Helper to create mock database row with all required attributes."""
        row = MagicMock()
        row.id = id
        row.question = question
        row.answer = answer
        row.similarity = similarity
        row.category = category
        row.tags = []
        row.language = "it"
        row.last_validated = datetime.now(UTC)
        row.needs_review = False
        row.regulatory_refs = {}
        row.update_sensitivity = "medium"
        row.hit_count = 0
        row.last_used = None
        row.avg_helpfulness = 0.0
        row.version = 1
        row.previous_version_id = None
        row.created_at = datetime.now(UTC)
        row.updated_at = datetime.now(UTC)
        row.search_vector = None
        return row

    # ========================================
    # Entity Match Threshold Tests (0.70)
    # ========================================

    @pytest.mark.asyncio
    async def test_entity_match_at_0_70_accepted(self, service):
        """Entity match with similarity exactly at 0.70 should be ACCEPTED."""
        mock_row = self._create_mock_row(
            question="Parlami della risoluzione 65 dell'agenzia dell'entrate",
            similarity=0.70,
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            result = await service.find_best_match("Cos'e' la risoluzione 65?")

        assert result.faq_entry is not None
        assert result.similarity_score == 0.70

    @pytest.mark.asyncio
    async def test_entity_match_at_0_69_rejected(self, service):
        """Entity match with similarity at 0.69 should be REJECTED (below 0.70)."""
        mock_row = self._create_mock_row(
            question="Parlami della risoluzione 65 dell'agenzia dell'entrate",
            similarity=0.69,
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            result = await service.find_best_match("Cos'e' la risoluzione 65?")

        # Should be rejected - similarity too low even with entity match
        assert result.faq_entry is None
        assert result.similarity_score == 0.0

    @pytest.mark.asyncio
    async def test_entity_match_at_0_80_accepted(self, service):
        """Entity match with similarity at 0.80 should be ACCEPTED (well above 0.70)."""
        mock_row = self._create_mock_row(
            question="Parlami della risoluzione 65 dell'agenzia dell'entrate",
            similarity=0.80,
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            result = await service.find_best_match("Cos'e' la risoluzione n.65?")

        assert result.faq_entry is not None
        assert result.similarity_score == 0.80

    # ========================================
    # No Entity Match Threshold Tests (0.85)
    # ========================================

    @pytest.mark.asyncio
    async def test_no_entity_at_0_85_accepted(self, service):
        """No entity match with similarity exactly at 0.85 should be ACCEPTED."""
        mock_row = self._create_mock_row(
            question="Come si calcola l'IVA ordinaria in Italia?",
            similarity=0.85,
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            # Query without specific entities
            result = await service.find_best_match("Qual è l'aliquota IVA?")

        assert result.faq_entry is not None
        assert result.similarity_score == 0.85

    @pytest.mark.asyncio
    async def test_no_entity_at_0_69_rejected(self, service):
        """Query without entities with similarity at 0.69 should be REJECTED.

        Note: When query has no entities, _validate_entity_match returns True
        (no constraints to violate), so the 0.70 threshold applies.
        """
        mock_row = self._create_mock_row(
            question="Come si calcola l'IVA ordinaria in Italia?",
            similarity=0.69,
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            result = await service.find_best_match("Qual è l'aliquota IVA?")

        # Should be rejected - below 0.70 threshold
        assert result.faq_entry is None
        assert result.similarity_score == 0.0

    @pytest.mark.asyncio
    async def test_no_entity_at_0_90_accepted(self, service):
        """No entity match with similarity at 0.90 should be ACCEPTED (well above 0.85)."""
        mock_row = self._create_mock_row(
            question="Come si calcola l'IVA ordinaria in Italia?",
            similarity=0.90,
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            result = await service.find_best_match("Qual è l'aliquota IVA ordinaria?")

        assert result.faq_entry is not None
        assert result.similarity_score == 0.90


class TestEntityMismatchRejection:
    """Test suite for entity mismatch scenarios - the original bug case.

    Entity validation is a HARD requirement:
    - Entity mismatch (e.g., risoluzione 63 vs 64) → REJECT entirely
    - This prevents high-similarity semantic matches from returning wrong documents
    """

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create IntelligentFAQService with mocked database."""
        return IntelligentFAQService(mock_db)

    def _create_mock_row(self, question: str, similarity: float, id: str = "test-uuid"):
        """Helper to create mock database row."""
        row = MagicMock()
        row.id = id
        row.question = question
        row.answer = "Test answer"
        row.similarity = similarity
        row.category = "generale"
        row.tags = []
        row.language = "it"
        row.last_validated = datetime.now(UTC)
        row.needs_review = False
        row.regulatory_refs = {}
        row.update_sensitivity = "medium"
        row.hit_count = 0
        row.last_used = None
        row.avg_helpfulness = 0.0
        row.version = 1
        row.previous_version_id = None
        row.created_at = datetime.now(UTC)
        row.updated_at = datetime.now(UTC)
        row.search_vector = None
        return row

    @pytest.mark.asyncio
    async def test_entity_mismatch_at_0_91_rejected(self, service):
        """Entity MISMATCH with high similarity (0.91) should be REJECTED entirely.

        This is the original bug case: risoluzione 63 query matching risoluzione 64 FAQ
        with 91.68% semantic similarity. Entity mismatch = REJECT regardless of score.
        """
        mock_row = self._create_mock_row(
            question="Parlami della risoluzione 64 dell'agenzia dell'entrate",
            similarity=0.91,
            id="wrong-faq-uuid",
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            # Query for risoluzione 63, but only risoluzione 64 exists
            result = await service.find_best_match("Parlami della risoluzione 63")

        # Should be REJECTED - entity mismatch (63 vs 64) = hard reject
        assert result.faq_entry is None
        assert result.similarity_score == 0.0

    @pytest.mark.asyncio
    async def test_entity_mismatch_skips_to_next_row(self, service):
        """When first row has entity mismatch, should skip to next valid row."""
        # First row: wrong entity (risoluzione 64), high similarity - SKIP
        wrong_row = self._create_mock_row(
            question="Parlami della risoluzione 64 dell'agenzia dell'entrate",
            similarity=0.91,
            id="wrong-uuid",
        )

        # Second row: correct entity (risoluzione 63), lower similarity - ACCEPT
        correct_row = self._create_mock_row(
            question="Risoluzione 63 dell'agenzia delle entrate",
            similarity=0.75,
            id="correct-uuid",
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [wrong_row, correct_row]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            result = await service.find_best_match("Parlami della risoluzione 63")

        # Should skip first row (entity mismatch) and accept second row
        assert result.faq_entry is not None
        assert result.faq_entry.id == "correct-uuid"
        assert result.similarity_score == 0.75


class TestMultirowIteration:
    """Test suite for multirow iteration logic."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create IntelligentFAQService with mocked database."""
        return IntelligentFAQService(mock_db)

    def _create_mock_row(self, question: str, similarity: float, id: str):
        """Helper to create mock database row."""
        row = MagicMock()
        row.id = id
        row.question = question
        row.answer = f"Answer for {id}"
        row.similarity = similarity
        row.category = "generale"
        row.tags = []
        row.language = "it"
        row.last_validated = datetime.now(UTC)
        row.needs_review = False
        row.regulatory_refs = {}
        row.update_sensitivity = "medium"
        row.hit_count = 0
        row.last_used = None
        row.avg_helpfulness = 0.0
        row.version = 1
        row.previous_version_id = None
        row.created_at = datetime.now(UTC)
        row.updated_at = datetime.now(UTC)
        row.search_vector = None
        return row

    @pytest.mark.asyncio
    async def test_iterates_through_rows_until_valid_match(self, service):
        """Should iterate through rows and find first row that passes validation."""
        # Row 1: Below 0.70 threshold - SKIP (even though entity validation passes)
        row1 = self._create_mock_row(
            question="Come funziona la tassazione?",
            similarity=0.65,
            id="row1",
        )

        # Row 2: Below 0.70 threshold - SKIP
        row2 = self._create_mock_row(
            question="Qual è l'aliquota fiscale?",
            similarity=0.68,
            id="row2",
        )

        # Row 3: At 0.70 threshold - ACCEPT (first valid match)
        row3 = self._create_mock_row(
            question="Calcolo delle imposte sui redditi",
            similarity=0.70,
            id="row3",
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [row1, row2, row3]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            result = await service.find_best_match("Come calcolo le tasse?")

        # Should skip first two (below threshold) and accept third
        assert result.faq_entry is not None
        assert result.faq_entry.id == "row3"
        assert result.similarity_score == 0.70

    @pytest.mark.asyncio
    async def test_returns_none_when_all_rows_rejected(self, service):
        """Should return None when all rows fail validation (entity mismatch)."""
        # All rows have entity mismatch with query (risoluzione 63 vs 64/65/66)
        row1 = self._create_mock_row(
            question="Risoluzione 64 dell'agenzia",
            similarity=0.90,
            id="row1",
        )
        row2 = self._create_mock_row(
            question="Risoluzione 65 dell'agenzia",
            similarity=0.88,
            id="row2",
        )
        row3 = self._create_mock_row(
            question="Risoluzione 66 dell'agenzia",
            similarity=0.85,
            id="row3",
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [row1, row2, row3]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            # Query for risoluzione 63, but all FAQs have different numbers
            result = await service.find_best_match("Parlami della risoluzione 63")

        # All rows should be rejected due to entity mismatch
        assert result.faq_entry is None
        assert result.similarity_score == 0.0

    @pytest.mark.asyncio
    async def test_empty_result_set(self, service):
        """Should return None when database returns no rows."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            result = await service.find_best_match("Any query")

        assert result.faq_entry is None
        assert result.similarity_score == 0.0


class TestEmbeddingFailure:
    """Test suite for embedding generation failure handling."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create IntelligentFAQService with mocked database."""
        return IntelligentFAQService(mock_db)

    @pytest.mark.asyncio
    async def test_returns_zero_when_embedding_fails(self, service):
        """Should return similarity_score 0.0 when embedding generation fails."""
        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=None):
            result = await service.find_best_match("Any query")

        assert result.faq_entry is None
        assert result.similarity_score == 0.0
        assert result.cache_hit is False


class TestRealWorldScenario:
    """Test the exact real-world scenario that caused the original bug."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create IntelligentFAQService with mocked database."""
        return IntelligentFAQService(mock_db)

    def _create_mock_row(self, question: str, similarity: float, id: str):
        """Helper to create mock database row."""
        row = MagicMock()
        row.id = id
        row.question = question
        row.answer = f"Answer for {question[:30]}"
        row.similarity = similarity
        row.category = "fiscale"
        row.tags = ["agenzia-entrate", "risoluzione"]
        row.language = "it"
        row.last_validated = datetime.now(UTC)
        row.needs_review = False
        row.regulatory_refs = {}
        row.update_sensitivity = "medium"
        row.hit_count = 5
        row.last_used = datetime.now(UTC)
        row.avg_helpfulness = 0.8
        row.version = 1
        row.previous_version_id = None
        row.created_at = datetime.now(UTC)
        row.updated_at = datetime.now(UTC)
        row.search_vector = None
        return row

    @pytest.mark.asyncio
    async def test_golden_set_scenario_0_8043_similarity(self, service):
        """Test exact scenario: 0.8043 similarity with entity match should be ACCEPTED.

        This is the exact bug fix scenario:
        - Query: "Cos'e' la risoluzione n.65 dell'agenzia delle entrate?"
        - FAQ: "Parlami della risoluzione 65 dell'agenzia dell'entrate"
        - Actual similarity: 0.8043

        With old 0.85 threshold: REJECTED
        With two-tier matching: ACCEPTED (entity match + 0.8043 >= 0.70)
        """
        mock_row = self._create_mock_row(
            question="Parlami della risoluzione 65 dell'agenzia dell'entrate",
            similarity=0.8043,  # Exact real-world similarity
            id="golden-faq-uuid",
        )

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        service.db.execute = AsyncMock(return_value=mock_result)

        with patch("app.core.embed.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 1536):
            result = await service.find_best_match("Cos'e' la risoluzione n.65 dell'agenzia delle entrate?")

        # Should be ACCEPTED - entity match (65 in both) and 0.8043 >= 0.70
        assert result.faq_entry is not None
        assert result.faq_entry.id == "golden-faq-uuid"
        assert result.similarity_score == 0.8043
