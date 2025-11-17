"""
Integration tests for Atomic Facts Extraction System in PratikoAI query processing pipeline.

Tests the complete integration flow from query input to enhanced classification and prompting.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.schemas import Message
from app.services.atomic_facts_extractor import AtomicFacts, AtomicFactsExtractor, DateFact, MonetaryAmount
from app.services.domain_action_classifier import Action, Domain, DomainActionClassification


class TestAtomicFactsIntegration:
    """Test integration of atomic facts extraction with query processing pipeline."""

    @pytest.fixture
    def agent(self):
        """Create LangGraphAgent for testing."""
        return LangGraphAgent()

    @pytest.fixture
    def sample_messages(self):
        """Sample conversation messages for testing."""
        return [
            Message(role="user", content="calcolo stipendio 35000 euro marzo 2024"),
            Message(role="assistant", content="Come posso aiutarti?"),
        ]

    def test_agent_has_atomic_facts_extractor(self, agent):
        """Test that LangGraphAgent has atomic facts extractor initialized."""
        assert hasattr(agent, "_atomic_facts_extractor")
        assert isinstance(agent._atomic_facts_extractor, AtomicFactsExtractor)
        assert agent._current_atomic_facts is None

    @pytest.mark.asyncio
    async def test_atomic_facts_extraction_in_classification(self, agent, sample_messages):
        """Test that atomic facts are extracted during query classification."""
        # Mock the domain classifier to focus on atomic facts extraction
        mock_classification = DomainActionClassification(
            domain=Domain.LABOR,
            action=Action.CALCULATION_REQUEST,
            confidence=0.8,
            sub_domain="stipendio",
            fallback_used=False,
        )

        with patch.object(agent._domain_classifier, "classify", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = mock_classification

            # Perform classification which should extract atomic facts
            await agent._classify_user_query(sample_messages)

            # Verify atomic facts were extracted and stored
            assert agent._current_atomic_facts is not None
            assert not agent._current_atomic_facts.is_empty()
            assert len(agent._current_atomic_facts.monetary_amounts) == 1
            assert agent._current_atomic_facts.monetary_amounts[0].amount == 35000.0
            assert agent._current_atomic_facts.monetary_amounts[0].currency == "EUR"

            # Verify classify was called with enhanced query
            mock_classify.assert_called_once()
            enhanced_query = mock_classify.call_args[0][0]
            assert "calcolo stipendio 35000 euro marzo 2024" in enhanced_query
            assert "[amounts: 35000.0 EUR" in enhanced_query

    def test_create_enhanced_query(self, agent):
        """Test enhanced query creation with atomic facts."""
        # Create sample atomic facts
        atomic_facts = AtomicFacts()
        atomic_facts.monetary_amounts = [MonetaryAmount(amount=35000.0, currency="EUR", confidence=0.9)]
        atomic_facts.dates = [DateFact(date_type="specific", iso_date="2024-03-01", confidence=0.85)]

        original_query = "calcolo stipendio marzo 2024"
        enhanced_query = agent._create_enhanced_query(original_query, atomic_facts)

        assert original_query in enhanced_query
        assert "amounts: 35000.0 EUR" in enhanced_query
        assert "dates: 2024-03-01" in enhanced_query
        assert enhanced_query.startswith(original_query)
        assert enhanced_query.endswith("]")

    def test_create_enhanced_query_empty_facts(self, agent):
        """Test enhanced query creation with empty atomic facts."""
        atomic_facts = AtomicFacts()  # Empty facts
        original_query = "ciao come stai?"
        enhanced_query = agent._create_enhanced_query(original_query, atomic_facts)

        # Should return original query unchanged
        assert enhanced_query == original_query

    def test_format_atomic_facts_for_context(self, agent):
        """Test formatting atomic facts for system prompt context."""
        # Create comprehensive atomic facts
        atomic_facts = AtomicFacts()
        atomic_facts.monetary_amounts = [
            MonetaryAmount(amount=35000.0, currency="EUR", confidence=0.9),
            MonetaryAmount(amount=22.0, currency="%", is_percentage=True, confidence=0.85),
        ]
        atomic_facts.dates = [
            DateFact(date_type="specific", iso_date="2024-03-01", confidence=0.85),
            DateFact(date_type="tax_year", tax_year=2023, confidence=0.9),
        ]

        context = agent._format_atomic_facts_for_context(atomic_facts)

        assert "Monetary amounts: 35,000.00 EUR, 22.0%" in context
        assert "Date: 2024-03-01" in context
        assert "Tax year: 2023" in context

    def test_format_atomic_facts_for_context_empty(self, agent):
        """Test formatting empty atomic facts returns empty string."""
        atomic_facts = AtomicFacts()  # Empty facts
        context = agent._format_atomic_facts_for_context(atomic_facts)

        assert context == ""

    @pytest.mark.asyncio
    async def test_classification_with_no_messages(self, agent):
        """Test classification with empty messages list."""
        classification = await agent._classify_user_query([])

        assert classification is None
        assert agent._current_atomic_facts is None

    @pytest.mark.asyncio
    async def test_classification_with_no_user_messages(self, agent):
        """Test classification with no user messages."""
        messages = [Message(role="assistant", content="Come posso aiutarti?")]
        classification = await agent._classify_user_query(messages)

        assert classification is None
        assert agent._current_atomic_facts is None

    @pytest.mark.asyncio
    async def test_classification_handles_extraction_errors(self, agent, sample_messages):
        """Test that classification continues even if atomic facts extraction fails."""
        # Mock extraction to raise an exception
        with patch.object(agent._atomic_facts_extractor, "extract", side_effect=Exception("Extraction failed")):
            with patch.object(agent._domain_classifier, "classify", new_callable=AsyncMock) as mock_classify:
                mock_classify.return_value = DomainActionClassification(
                    domain=Domain.BUSINESS, action=Action.INFORMATION_REQUEST, confidence=0.5, fallback_used=False
                )

                # Should not raise exception and return None
                classification = await agent._classify_user_query(sample_messages)

                assert classification is None  # Error should cause None return
                assert agent._current_atomic_facts is None

    def test_system_prompt_integration_with_atomic_facts(self, agent, sample_messages):
        """Test that system prompt generation includes atomic facts context."""
        # Set up atomic facts
        atomic_facts = AtomicFacts()
        atomic_facts.monetary_amounts = [MonetaryAmount(amount=35000.0, currency="EUR", confidence=0.9)]
        agent._current_atomic_facts = atomic_facts

        # Mock classification
        classification = DomainActionClassification(
            domain=Domain.LABOR,
            action=Action.CALCULATION_REQUEST,
            confidence=0.8,
            sub_domain="stipendio",
            fallback_used=False,
        )

        # Mock prompt template manager
        with patch.object(agent._prompt_template_manager, "get_prompt") as mock_get_prompt:
            mock_get_prompt.return_value = "Enhanced prompt with context"

            agent._get_system_prompt(sample_messages, classification)

            # Verify get_prompt was called with atomic facts context
            mock_get_prompt.assert_called_once()
            call_args = mock_get_prompt.call_args[1]

            assert "context" in call_args
            assert call_args["context"] is not None
            assert "Monetary amounts: 35,000.00 EUR" in call_args["context"]

    def test_performance_requirement_met(self, agent):
        """Test that atomic facts extraction meets <50ms performance requirement."""
        query = "calcolo stipendio 35000 euro marzo 2024 per CCNL metalmeccanici livello 5 a Milano"

        # Perform extraction
        facts = agent._atomic_facts_extractor.extract(query)

        # Verify performance requirement
        assert facts.extraction_time_ms < 50.0
        assert not facts.is_empty()
        assert facts.fact_count() > 0

    @pytest.mark.asyncio
    async def test_integration_end_to_end(self, agent):
        """Test complete integration flow from query to enhanced classification."""
        messages = [Message(role="user", content="stipendio 30000 euro CCNL commercio marzo 2024")]

        # Mock domain classifier
        mock_classification = DomainActionClassification(
            domain=Domain.LABOR,
            action=Action.CALCULATION_REQUEST,
            confidence=0.85,
            sub_domain="stipendio",
            fallback_used=False,
        )

        with patch.object(agent._domain_classifier, "classify", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = mock_classification

            # Perform classification
            classification = await agent._classify_user_query(messages)

            # Verify results
            assert classification == mock_classification
            assert agent._current_atomic_facts is not None

            # Verify atomic facts were extracted
            facts = agent._current_atomic_facts
            assert len(facts.monetary_amounts) == 1
            assert facts.monetary_amounts[0].amount == 30000.0

            # Verify enhanced query was used for classification
            enhanced_query = mock_classify.call_args[0][0]
            assert "30000 euro" in enhanced_query
            assert "amounts: 30000.0 EUR" in enhanced_query
            assert "professional: sector: commercio" in enhanced_query

            # Test system prompt generation with facts
            with patch.object(agent._prompt_template_manager, "get_prompt") as mock_get_prompt:
                mock_get_prompt.return_value = "Domain-specific prompt"

                agent._get_system_prompt(messages, classification)

                # Verify context was passed to prompt template
                call_args = mock_get_prompt.call_args[1]
                assert "context" in call_args
                context = call_args["context"]
                assert "Monetary amounts: 30,000.00 EUR" in context
                assert "CCNL sector: commercio" in context
