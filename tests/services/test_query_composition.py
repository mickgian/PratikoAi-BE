"""Unit tests for Query Composition Detection (DEV-007 Issue 9).

Tests the adaptive context prioritization feature that uses LLM-based classification
when attachments are present and regex-based detection otherwise.

The QueryComposition system enables:
- PURE_DOCUMENT: User wants analysis based solely on their uploaded document
- HYBRID: User wants document analysis PLUS regulatory/knowledge base context
- PURE_KB: Standard knowledge base query (no attachments or unrelated question)
- CONVERSATIONAL: Greetings and chitchat
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock database-related modules before importing app modules
# This prevents database connections during test collection
sys.modules.setdefault("app.services.database", MagicMock())

# Now import the modules we need to test
from app.services.context_builder_merge import (
    COMPOSITION_PRIORITY_WEIGHTS,
    get_composition_priority_weights,
)
from app.services.domain_action_classifier import (
    DomainActionClassifier,
    QueryComposition,
)


class TestQueryCompositionEnum:
    """Tests for QueryComposition enum values."""

    def test_enum_values_exist(self):
        """Verify all composition types have correct string values."""
        assert QueryComposition.PURE_KB.value == "pure_kb"
        assert QueryComposition.PURE_DOCUMENT.value == "pure_doc"
        assert QueryComposition.HYBRID.value == "hybrid"
        assert QueryComposition.CONVERSATIONAL.value == "chat"

    def test_enum_is_string_enum(self):
        """QueryComposition should be a string enum for easy serialization."""
        assert isinstance(QueryComposition.PURE_KB, str)
        assert isinstance(QueryComposition.PURE_DOCUMENT, str)


class TestCompositionPriorityWeights:
    """Tests for COMPOSITION_PRIORITY_WEIGHTS and get_composition_priority_weights()."""

    def test_weights_dict_has_all_compositions(self):
        """All composition types should have defined weights."""
        assert "pure_kb" in COMPOSITION_PRIORITY_WEIGHTS
        assert "pure_doc" in COMPOSITION_PRIORITY_WEIGHTS
        assert "hybrid" in COMPOSITION_PRIORITY_WEIGHTS
        assert "chat" in COMPOSITION_PRIORITY_WEIGHTS

    def test_pure_document_prioritizes_doc_facts(self):
        """PURE_DOCUMENT should give highest weight to document_facts."""
        weights = COMPOSITION_PRIORITY_WEIGHTS["pure_doc"]
        assert weights["document_facts"] == 0.6
        assert weights["document_facts"] > weights["kb_docs"]
        assert weights["document_facts"] > weights["facts"]

    def test_hybrid_balances_doc_and_kb(self):
        """HYBRID should balance document_facts and kb_docs equally."""
        weights = COMPOSITION_PRIORITY_WEIGHTS["hybrid"]
        assert weights["document_facts"] == 0.5
        assert weights["kb_docs"] == 0.5

    def test_pure_kb_prioritizes_kb_docs(self):
        """PURE_KB should give highest weight to kb_docs."""
        weights = COMPOSITION_PRIORITY_WEIGHTS["pure_kb"]
        assert weights["kb_docs"] == 0.6
        assert weights["kb_docs"] > weights["document_facts"]

    def test_conversational_prioritizes_facts(self):
        """CONVERSATIONAL should give highest weight to facts."""
        weights = COMPOSITION_PRIORITY_WEIGHTS["chat"]
        assert weights["facts"] == 0.5

    def test_get_composition_priority_weights_returns_correct_weights(self):
        """get_composition_priority_weights() should return correct weights for each type."""
        assert get_composition_priority_weights("pure_doc") == COMPOSITION_PRIORITY_WEIGHTS["pure_doc"]
        assert get_composition_priority_weights("hybrid") == COMPOSITION_PRIORITY_WEIGHTS["hybrid"]
        assert get_composition_priority_weights("pure_kb") == COMPOSITION_PRIORITY_WEIGHTS["pure_kb"]
        assert get_composition_priority_weights("chat") == COMPOSITION_PRIORITY_WEIGHTS["chat"]

    def test_get_composition_priority_weights_defaults_to_pure_kb(self):
        """Unknown composition types should default to pure_kb weights."""
        assert get_composition_priority_weights(None) == COMPOSITION_PRIORITY_WEIGHTS["pure_kb"]
        assert get_composition_priority_weights("unknown") == COMPOSITION_PRIORITY_WEIGHTS["pure_kb"]
        assert get_composition_priority_weights("") == COMPOSITION_PRIORITY_WEIGHTS["pure_kb"]


class TestRegexBasedCompositionDetection:
    """Tests for regex-based composition detection (no attachments path)."""

    @pytest.fixture
    def classifier(self):
        """Create DomainActionClassifier instance."""
        return DomainActionClassifier()

    def test_conversational_greeting_ciao(self, classifier):
        """'ciao' should be classified as CONVERSATIONAL."""
        result = classifier._detect_composition_regex("ciao!")
        assert result == QueryComposition.CONVERSATIONAL

    def test_conversational_greeting_grazie(self, classifier):
        """'grazie' should be classified as CONVERSATIONAL."""
        result = classifier._detect_composition_regex("grazie mille")
        assert result == QueryComposition.CONVERSATIONAL

    def test_conversational_greeting_buongiorno(self, classifier):
        """'buongiorno' should be classified as CONVERSATIONAL."""
        result = classifier._detect_composition_regex("Buongiorno!")
        assert result == QueryComposition.CONVERSATIONAL

    def test_conversational_come_stai(self, classifier):
        """'come stai' should be classified as CONVERSATIONAL."""
        result = classifier._detect_composition_regex("come stai?")
        assert result == QueryComposition.CONVERSATIONAL

    def test_pure_kb_tax_question(self, classifier):
        """Tax questions without attachments should be PURE_KB."""
        result = classifier._detect_composition_regex("Quali sono le aliquote IVA 2024?")
        assert result == QueryComposition.PURE_KB

    def test_pure_kb_regulation_question(self, classifier):
        """Regulation questions should be PURE_KB."""
        result = classifier._detect_composition_regex("Cosa dice la circolare INPS n. 23?")
        assert result == QueryComposition.PURE_KB

    def test_pure_kb_generic_question(self, classifier):
        """Generic questions should default to PURE_KB."""
        result = classifier._detect_composition_regex("Come funziona la detrazione fiscale?")
        assert result == QueryComposition.PURE_KB


class TestLLMBasedCompositionDetection:
    """Tests for LLM-based composition detection (attachments present path)."""

    @pytest.fixture
    def classifier(self):
        """Create DomainActionClassifier instance."""
        return DomainActionClassifier()

    @pytest.mark.asyncio
    async def test_detect_with_attachment_uses_llm(self, classifier):
        """When attachments present, should call LLM classification."""
        with patch.object(classifier, "_classify_composition_with_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = QueryComposition.PURE_DOCUMENT

            result = await classifier.detect_query_composition(
                query="calcola la mia pensione",
                has_attachments=True,
                attachment_filename="fondo_pensione.xlsx",
            )

            mock_llm.assert_called_once_with("calcola la mia pensione", "fondo_pensione.xlsx")
            assert result == QueryComposition.PURE_DOCUMENT

    @pytest.mark.asyncio
    async def test_detect_without_attachment_uses_regex(self, classifier):
        """When no attachments, should use regex-based detection."""
        with patch.object(classifier, "_detect_composition_regex") as mock_regex:
            mock_regex.return_value = QueryComposition.PURE_KB

            result = await classifier.detect_query_composition(
                query="aliquote IVA 2024",
                has_attachments=False,
            )

            mock_regex.assert_called_once_with("aliquote IVA 2024")
            assert result == QueryComposition.PURE_KB

    @pytest.mark.asyncio
    async def test_llm_returns_document_only(self, classifier):
        """LLM returning DOCUMENT_ONLY maps to PURE_DOCUMENT."""
        mock_response = MagicMock()
        mock_response.content = "DOCUMENT_ONLY"

        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)

        mock_factory = MagicMock()
        mock_factory.create_provider = MagicMock(return_value=mock_provider)

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._classify_composition_with_llm(
                "calcola la mia pensione",
                "fondo_pensione.xlsx",
            )

        assert result == QueryComposition.PURE_DOCUMENT

    @pytest.mark.asyncio
    async def test_llm_returns_hybrid(self, classifier):
        """LLM returning HYBRID maps to HYBRID."""
        mock_response = MagicMock()
        mock_response.content = "HYBRID"

        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)

        mock_factory = MagicMock()
        mock_factory.create_provider = MagicMock(return_value=mock_provider)

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._classify_composition_with_llm(
                "verifica se i dati rispettano la normativa",
                "CUD_2024.pdf",
            )

        assert result == QueryComposition.HYBRID

    @pytest.mark.asyncio
    async def test_llm_returns_kb_only(self, classifier):
        """LLM returning KB_ONLY maps to PURE_KB."""
        mock_response = MagicMock()
        mock_response.content = "KB_ONLY"

        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)

        mock_factory = MagicMock()
        mock_factory.create_provider = MagicMock(return_value=mock_provider)

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._classify_composition_with_llm(
                "che tempo fa domani?",
                "documento.pdf",
            )

        assert result == QueryComposition.PURE_KB

    @pytest.mark.asyncio
    async def test_llm_error_defaults_to_pure_document(self, classifier):
        """LLM errors should default to PURE_DOCUMENT (safe for attachments)."""
        mock_factory = MagicMock()
        mock_factory.create_provider.side_effect = Exception("LLM unavailable")

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._classify_composition_with_llm(
                "calcola la pensione",
                "fondo.xlsx",
            )

        # Should default to PURE_DOCUMENT as safest option for attachments
        assert result == QueryComposition.PURE_DOCUMENT

    @pytest.mark.asyncio
    async def test_llm_ambiguous_response_defaults_to_pure_document(self, classifier):
        """Ambiguous LLM responses should default to PURE_DOCUMENT."""
        mock_response = MagicMock()
        mock_response.content = "I'm not sure"  # Not a valid classification

        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)

        mock_factory = MagicMock()
        mock_factory.create_provider = MagicMock(return_value=mock_provider)

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier._classify_composition_with_llm(
                "analizza questo",
                "file.xlsx",
            )

        # Should default to PURE_DOCUMENT
        assert result == QueryComposition.PURE_DOCUMENT


class TestRealWorldScenarios:
    """Tests for realistic user scenarios as described in ADR-017."""

    @pytest.fixture
    def classifier(self):
        """Create DomainActionClassifier instance."""
        return DomainActionClassifier()

    @pytest.mark.asyncio
    async def test_scenario_simple_pension_calculation(self, classifier):
        """User uploads fondo_pensione.xlsx and asks 'calcola la mia pensione netta'."""
        mock_response = MagicMock()
        mock_response.content = "DOCUMENT_ONLY"

        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)

        mock_factory = MagicMock()
        mock_factory.create_provider = MagicMock(return_value=mock_provider)

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier.detect_query_composition(
                query="calcola la mia pensione netta",
                has_attachments=True,
                attachment_filename="fondo_pensione.xlsx",
            )

        # Document-only analysis expected
        assert result == QueryComposition.PURE_DOCUMENT

    @pytest.mark.asyncio
    async def test_scenario_invoice_payment(self, classifier):
        """User uploads fattura_2024.pdf and asks 'quanto devo pagare?'."""
        mock_response = MagicMock()
        mock_response.content = "DOCUMENT_ONLY"

        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)

        mock_factory = MagicMock()
        mock_factory.create_provider = MagicMock(return_value=mock_provider)

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier.detect_query_composition(
                query="quanto devo pagare?",
                has_attachments=True,
                attachment_filename="fattura_2024.pdf",
            )

        assert result == QueryComposition.PURE_DOCUMENT

    @pytest.mark.asyncio
    async def test_scenario_cud_with_regulation_check(self, classifier):
        """User uploads CUD_2024.pdf and asks 'verifica se i dati sono corretti secondo normativa'."""
        mock_response = MagicMock()
        mock_response.content = "HYBRID"

        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)

        mock_factory = MagicMock()
        mock_factory.create_provider = MagicMock(return_value=mock_provider)

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier.detect_query_composition(
                query="verifica se i dati sono corretti secondo normativa",
                has_attachments=True,
                attachment_filename="CUD_2024.pdf",
            )

        # Hybrid - needs both document and regulatory context
        assert result == QueryComposition.HYBRID

    @pytest.mark.asyncio
    async def test_scenario_balance_with_legal_requirements(self, classifier):
        """User uploads bilancio.xlsx and asks 'analizza e dimmi se rispetta i requisiti di legge'."""
        mock_response = MagicMock()
        mock_response.content = "HYBRID"

        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)

        mock_factory = MagicMock()
        mock_factory.create_provider = MagicMock(return_value=mock_provider)

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier.detect_query_composition(
                query="analizza e dimmi se rispetta i requisiti di legge",
                has_attachments=True,
                attachment_filename="bilancio.xlsx",
            )

        assert result == QueryComposition.HYBRID

    @pytest.mark.asyncio
    async def test_scenario_unrelated_weather_question(self, classifier):
        """User has document but asks 'che tempo fa domani?' (unrelated)."""
        mock_response = MagicMock()
        mock_response.content = "KB_ONLY"

        mock_provider = AsyncMock()
        mock_provider.chat_completion = AsyncMock(return_value=mock_response)

        mock_factory = MagicMock()
        mock_factory.create_provider = MagicMock(return_value=mock_provider)

        with patch("app.services.domain_action_classifier.LLMFactory", return_value=mock_factory):
            result = await classifier.detect_query_composition(
                query="che tempo fa domani?",
                has_attachments=True,
                attachment_filename="random.pdf",
            )

        # Rare case: question unrelated to document
        assert result == QueryComposition.PURE_KB

    @pytest.mark.asyncio
    async def test_scenario_no_attachment_iva_question(self, classifier):
        """User asks 'aliquote IVA 2024?' without attachment (uses regex)."""
        result = await classifier.detect_query_composition(
            query="aliquote IVA 2024?",
            has_attachments=False,
        )

        # Should use regex path, return PURE_KB
        assert result == QueryComposition.PURE_KB

    @pytest.mark.asyncio
    async def test_scenario_no_attachment_greeting(self, classifier):
        """User says 'ciao!' without attachment (uses regex)."""
        result = await classifier.detect_query_composition(
            query="ciao!",
            has_attachments=False,
        )

        # Should use regex path, return CONVERSATIONAL
        assert result == QueryComposition.CONVERSATIONAL
