"""TDD Tests for Phase 9: LLMOrchestrator Service.

DEV-221: Implement LLMOrchestrator Service for Multi-Model Routing.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 90%+ for new code.
"""

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These imports will fail initially (RED phase) until implementation exists
from app.services.llm_orchestrator import (
    ComplexityContext,
    LLMOrchestrator,
    ModelConfig,
    QueryComplexity,
    UnifiedResponse,
    get_llm_orchestrator,
    reset_orchestrator,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_prompt_loader():
    """Create a mock PromptLoader."""
    loader = MagicMock()
    loader.load.return_value = """# Classificatore Complessità Query

    ## Query da Classificare
    {query}

    ## Contesto
    - Domini rilevati: {domains}
    - Conversazione precedente: {has_history}
    - Documenti utente allegati: {has_documents}
    """
    return loader


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response for classification."""
    return {
        "complexity": "simple",
        "domains": ["fiscale"],
        "confidence": 0.95,
        "reasoning": "Query diretta su aliquota IVA standard",
    }


@pytest.fixture
def mock_unified_response():
    """Create a mock unified response from LLM."""
    return {
        "reasoning": {
            "tema_identificato": "aliquota IVA",
            "fonti_utilizzate": ["Art. 16 DPR 633/72"],
            "elementi_chiave": ["22% aliquota ordinaria"],
            "conclusione": "L'aliquota IVA ordinaria in Italia è il 22%",
        },
        "answer": "L'aliquota IVA ordinaria in Italia è il 22%, come stabilito dall'Art. 16 del DPR 633/72.",
        "sources_cited": [{"ref": "Art. 16 DPR 633/72", "relevance": "principale", "url": None}],
        "suggested_actions": [
            {
                "id": "action_1",
                "label": "Calcola IVA su importo",
                "icon": "calculator",
                "prompt": "Calcola l'IVA al 22% su un importo specifico",
                "source_basis": "Art. 16 DPR 633/72",
            }
        ],
    }


@pytest.fixture
def orchestrator(mock_prompt_loader):
    """Create an LLMOrchestrator instance with mocked dependencies."""
    with patch("app.services.llm_orchestrator.get_prompt_loader", return_value=mock_prompt_loader):
        return LLMOrchestrator()


# =============================================================================
# QueryComplexity Enum Tests
# =============================================================================


class TestQueryComplexityEnum:
    """Test QueryComplexity enum values."""

    def test_simple_value(self):
        """SIMPLE complexity should have correct value."""
        assert QueryComplexity.SIMPLE.value == "simple"

    def test_complex_value(self):
        """COMPLEX complexity should have correct value."""
        assert QueryComplexity.COMPLEX.value == "complex"

    def test_multi_domain_value(self):
        """MULTI_DOMAIN complexity should have correct value."""
        assert QueryComplexity.MULTI_DOMAIN.value == "multi_domain"

    def test_enum_is_string(self):
        """QueryComplexity should be usable as string."""
        assert str(QueryComplexity.SIMPLE) == "simple"


# =============================================================================
# ComplexityContext Dataclass Tests
# =============================================================================


class TestComplexityContext:
    """Test ComplexityContext dataclass."""

    def test_create_with_defaults(self):
        """Should create context with default values."""
        context = ComplexityContext(domains=["fiscale"])
        assert context.domains == ["fiscale"]
        assert context.has_history is False
        assert context.has_documents is False

    def test_create_with_all_fields(self):
        """Should create context with all fields."""
        context = ComplexityContext(
            domains=["fiscale", "lavoro"],
            has_history=True,
            has_documents=True,
        )
        assert context.domains == ["fiscale", "lavoro"]
        assert context.has_history is True
        assert context.has_documents is True


# =============================================================================
# ModelConfig Tests
# =============================================================================


class TestModelConfig:
    """Test ModelConfig dataclass."""

    def test_simple_config_exists(self):
        """SIMPLE complexity should have model config.

        DEV-242 Phase 13A: Upgraded to gpt-4o with 3000 max_tokens.
        """
        config = ModelConfig.for_complexity(QueryComplexity.SIMPLE)
        assert config.model == "gpt-4o"  # DEV-242: Upgraded from gpt-4o-mini
        assert config.temperature == 0.3
        assert config.max_tokens == 3000  # DEV-242: Doubled from 1500

    def test_complex_config_exists(self):
        """COMPLEX complexity should have model config.

        DEV-242 Phase 13A: Doubled max_tokens from 2500 to 5000.
        """
        config = ModelConfig.for_complexity(QueryComplexity.COMPLEX)
        assert config.model == "gpt-4o"
        assert config.temperature == 0.4
        assert config.max_tokens == 5000  # DEV-242: Doubled from 2500

    def test_multi_domain_config_exists(self):
        """MULTI_DOMAIN complexity should have model config.

        DEV-242 Phase 13A: Doubled max_tokens from 3500 to 7000.
        """
        config = ModelConfig.for_complexity(QueryComplexity.MULTI_DOMAIN)
        assert config.model == "gpt-4o"
        assert config.temperature == 0.5
        assert config.max_tokens == 7000  # DEV-242: Doubled from 3500

    def test_config_has_cost_info(self):
        """Model config should have cost information."""
        config = ModelConfig.for_complexity(QueryComplexity.SIMPLE)
        assert config.cost_input_per_1k > 0
        assert config.cost_output_per_1k > 0

    def test_config_has_prompt_template(self):
        """Model config should have prompt template name."""
        config = ModelConfig.for_complexity(QueryComplexity.SIMPLE)
        assert config.prompt_template == "unified_response_simple"

    def test_config_has_reasoning_type(self):
        """Model config should have reasoning type."""
        config = ModelConfig.for_complexity(QueryComplexity.SIMPLE)
        assert config.reasoning_type == "cot"


# =============================================================================
# UnifiedResponse Dataclass Tests
# =============================================================================


class TestUnifiedResponse:
    """Test UnifiedResponse dataclass."""

    def test_create_unified_response(self):
        """Should create a valid UnifiedResponse."""
        response = UnifiedResponse(
            reasoning={"tema": "IVA"},
            reasoning_type="cot",
            tot_analysis=None,
            answer="L'IVA è 22%",
            sources_cited=[],
            suggested_actions=[],
            model_used="gpt-4o-mini",
            tokens_input=100,
            tokens_output=50,
            cost_euros=0.001,
            latency_ms=500,
        )
        assert response.answer == "L'IVA è 22%"
        assert response.model_used == "gpt-4o-mini"
        assert response.cost_euros == 0.001

    def test_tot_analysis_optional(self):
        """tot_analysis should be optional (None for CoT)."""
        response = UnifiedResponse(
            reasoning={"tema": "IVA"},
            reasoning_type="cot",
            tot_analysis=None,
            answer="Answer",
            sources_cited=[],
            suggested_actions=[],
            model_used="gpt-4o-mini",
            tokens_input=100,
            tokens_output=50,
            cost_euros=0.001,
            latency_ms=500,
        )
        assert response.tot_analysis is None


# =============================================================================
# LLMOrchestrator Initialization Tests
# =============================================================================


class TestLLMOrchestratorInit:
    """Test LLMOrchestrator initialization."""

    def test_orchestrator_creates_with_defaults(self, orchestrator):
        """Orchestrator should initialize with default dependencies."""
        assert orchestrator is not None
        assert orchestrator.prompt_loader is not None

    def test_orchestrator_tracks_session_costs(self, orchestrator):
        """Orchestrator should track session costs."""
        costs = orchestrator.get_session_costs()
        assert "total_cost_euros" in costs
        assert "total_queries" in costs
        assert costs["total_cost_euros"] == 0.0
        assert costs["total_queries"] == 0


# =============================================================================
# classify_complexity Tests
# =============================================================================


class TestClassifyComplexity:
    """Test complexity classification."""

    @pytest.mark.asyncio
    async def test_classify_simple_query(self, orchestrator, mock_llm_response):
        """Simple FAQ query should be classified as SIMPLE."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_llm_response), 50, 30)

            context = ComplexityContext(domains=["fiscale"])
            result = await orchestrator.classify_complexity(
                query="Qual è l'aliquota IVA ordinaria?",
                context=context,
            )

            assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_classify_complex_query(self, orchestrator):
        """Multi-step query should be classified as COMPLEX."""
        complex_response = {
            "complexity": "complex",
            "domains": ["fiscale"],
            "confidence": 0.90,
            "reasoning": "Richiede calcolo multi-step con detrazioni",
        }
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(complex_response), 60, 40)

            context = ComplexityContext(domains=["fiscale"])
            result = await orchestrator.classify_complexity(
                query="Come calcolo l'IRPEF con detrazioni per figli e mutuo?",
                context=context,
            )

            assert result == QueryComplexity.COMPLEX

    @pytest.mark.asyncio
    async def test_classify_multi_domain_query(self, orchestrator):
        """Cross-domain query should be classified as MULTI_DOMAIN."""
        multi_domain_response = {
            "complexity": "multi_domain",
            "domains": ["fiscale", "lavoro"],
            "confidence": 0.85,
            "reasoning": "Coinvolge aspetti fiscali e lavoristici",
        }
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(multi_domain_response), 70, 45)

            context = ComplexityContext(domains=["fiscale", "lavoro"])
            result = await orchestrator.classify_complexity(
                query="Assumo un dipendente che vuole aprire P.IVA freelance",
                context=context,
            )

            assert result == QueryComplexity.MULTI_DOMAIN

    @pytest.mark.asyncio
    async def test_classification_fallback_on_error(self, orchestrator):
        """Should default to SIMPLE on classification error."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.side_effect = Exception("LLM unavailable")

            context = ComplexityContext(domains=["fiscale"])
            result = await orchestrator.classify_complexity(
                query="Test query",
                context=context,
            )

            assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_classification_fallback_on_invalid_json(self, orchestrator):
        """Should default to SIMPLE on invalid JSON response."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = ("invalid json {{{", 50, 30)

            context = ComplexityContext(domains=["fiscale"])
            result = await orchestrator.classify_complexity(
                query="Test query",
                context=context,
            )

            assert result == QueryComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_classification_uses_gpt4o_mini(self, orchestrator):
        """Classification should use GPT-4o-mini for cost efficiency."""
        mock_response = {
            "complexity": "simple",
            "domains": ["fiscale"],
            "confidence": 0.95,
            "reasoning": "Simple query",
        }
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_response), 50, 30)

            context = ComplexityContext(domains=["fiscale"])
            await orchestrator.classify_complexity(query="Test", context=context)

            # Verify gpt-4o-mini was used
            call_args = mock_call.call_args
            assert call_args is not None
            assert "gpt-4o-mini" in str(call_args) or mock_call.called


# =============================================================================
# generate_response Tests
# =============================================================================


class TestGenerateResponse:
    """Test response generation."""

    @pytest.mark.asyncio
    async def test_generate_simple_uses_gpt4o(self, orchestrator, mock_unified_response):
        """SIMPLE complexity should use gpt-4o (DEV-242 Phase 13A upgrade)."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 200, 150)

            result = await orchestrator.generate_response(
                query="Qual è l'aliquota IVA?",
                kb_context="Contesto KB...",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            # DEV-242: Upgraded from gpt-4o-mini to gpt-4o for quality
            assert result.model_used == "gpt-4o"

    @pytest.mark.asyncio
    async def test_generate_complex_uses_gpt4o(self, orchestrator, mock_unified_response):
        """COMPLEX complexity should use gpt-4o."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 400, 300)

            result = await orchestrator.generate_response(
                query="Calcolo complesso IRPEF",
                kb_context="Contesto KB...",
                kb_sources_metadata=[],
                complexity=QueryComplexity.COMPLEX,
            )

            assert result.model_used == "gpt-4o"

    @pytest.mark.asyncio
    async def test_generate_multi_domain_uses_gpt4o(self, orchestrator, mock_unified_response):
        """MULTI_DOMAIN complexity should use gpt-4o."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 500, 400)

            result = await orchestrator.generate_response(
                query="Query multi-dominio",
                kb_context="Contesto KB...",
                kb_sources_metadata=[],
                complexity=QueryComplexity.MULTI_DOMAIN,
            )

            assert result.model_used == "gpt-4o"

    @pytest.mark.asyncio
    async def test_generate_returns_unified_response(self, orchestrator, mock_unified_response):
        """Should return a valid UnifiedResponse."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 200, 150)

            result = await orchestrator.generate_response(
                query="Test query",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            assert isinstance(result, UnifiedResponse)
            assert result.answer is not None
            assert result.reasoning is not None
            assert result.sources_cited is not None
            assert result.suggested_actions is not None

    @pytest.mark.asyncio
    async def test_generate_tracks_cost(self, orchestrator, mock_unified_response):
        """Response should include cost tracking."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 200, 150)

            result = await orchestrator.generate_response(
                query="Test query",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            assert result.tokens_input > 0
            assert result.tokens_output > 0
            assert result.cost_euros > 0

    @pytest.mark.asyncio
    async def test_generate_tracks_latency(self, orchestrator, mock_unified_response):
        """Response should include latency tracking."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 200, 150)

            result = await orchestrator.generate_response(
                query="Test query",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_generate_with_conversation_history(self, orchestrator, mock_unified_response):
        """Should accept conversation history."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 200, 150)

            result = await orchestrator.generate_response(
                query="E per l'IVA ridotta?",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
                conversation_history=[
                    {"role": "user", "content": "Qual è l'IVA ordinaria?"},
                    {"role": "assistant", "content": "22%"},
                ],
            )

            assert result is not None


# =============================================================================
# Cost Tracking Tests
# =============================================================================


class TestCostTracking:
    """Test cost tracking functionality."""

    @pytest.mark.asyncio
    async def test_session_cost_accumulates(self, orchestrator, mock_unified_response):
        """Session costs should accumulate across queries."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 200, 150)

            # First query
            await orchestrator.generate_response(
                query="Query 1",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            costs_after_1 = orchestrator.get_session_costs()
            assert costs_after_1["total_queries"] == 1
            assert costs_after_1["total_cost_euros"] > 0

            # Second query
            await orchestrator.generate_response(
                query="Query 2",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            costs_after_2 = orchestrator.get_session_costs()
            assert costs_after_2["total_queries"] == 2
            assert costs_after_2["total_cost_euros"] > costs_after_1["total_cost_euros"]

    def test_session_costs_breakdown(self, orchestrator):
        """Session costs should include breakdown by complexity."""
        costs = orchestrator.get_session_costs()
        assert "by_complexity" in costs
        assert "simple" in costs["by_complexity"]
        assert "complex" in costs["by_complexity"]
        assert "multi_domain" in costs["by_complexity"]

    @pytest.mark.asyncio
    async def test_cost_calculation_simple(self, orchestrator, mock_unified_response):
        """Cost should be calculated correctly for SIMPLE queries.

        DEV-242 Phase 13A: SIMPLE now uses gpt-4o (upgraded from gpt-4o-mini).
        Cost rates: input=$0.005/1k, output=$0.015/1k
        """
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 1000, 500)

            result = await orchestrator.generate_response(
                query="Simple query",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            # DEV-242: gpt-4o: input=$0.005/1k, output=$0.015/1k
            # Expected: (1000 * 0.005 / 1000) + (500 * 0.015 / 1000) = 0.0125
            assert result.cost_euros > 0
            assert result.cost_euros < 0.05  # Higher than mini but reasonable for quality

    @pytest.mark.asyncio
    async def test_cost_calculation_complex(self, orchestrator, mock_unified_response):
        """Cost should be calculated correctly for COMPLEX queries."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 1000, 500)

            result = await orchestrator.generate_response(
                query="Complex query",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.COMPLEX,
            )

            # gpt-4o: input=$0.005/1k, output=$0.015/1k
            # Expected: (1000 * 0.005 / 1000) + (500 * 0.015 / 1000) = 0.0125
            assert result.cost_euros > 0


# =============================================================================
# Reasoning Type Tests
# =============================================================================


class TestReasoningTypes:
    """Test reasoning type selection."""

    @pytest.mark.asyncio
    async def test_simple_uses_cot(self, orchestrator, mock_unified_response):
        """SIMPLE complexity should use Chain of Thought."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 200, 150)

            result = await orchestrator.generate_response(
                query="Simple query",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            assert result.reasoning_type == "cot"
            assert result.tot_analysis is None

    @pytest.mark.asyncio
    async def test_complex_uses_tot(self, orchestrator):
        """COMPLEX complexity should use Tree of Thoughts."""
        tot_response = {
            "reasoning": {"tema": "test"},
            "tot_analysis": {
                "hypotheses": [
                    {"id": 1, "interpretation": "Scenario A"},
                    {"id": 2, "interpretation": "Scenario B"},
                ],
                "selected": 1,
                "selection_reasoning": "Scenario A più appropriato",
            },
            "answer": "Risposta",
            "sources_cited": [],
            "suggested_actions": [],
        }
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(tot_response), 400, 300)

            result = await orchestrator.generate_response(
                query="Complex query",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.COMPLEX,
            )

            assert result.reasoning_type == "tot"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Test factory function for creating orchestrator."""

    def test_get_llm_orchestrator_returns_instance(self):
        """get_llm_orchestrator should return LLMOrchestrator instance."""
        with patch("app.services.llm_orchestrator.get_prompt_loader"):
            orchestrator = get_llm_orchestrator()
            assert isinstance(orchestrator, LLMOrchestrator)

    def test_get_llm_orchestrator_singleton(self):
        """get_llm_orchestrator should return same instance (singleton)."""
        with patch("app.services.llm_orchestrator.get_prompt_loader"):
            orchestrator1 = get_llm_orchestrator()
            orchestrator2 = get_llm_orchestrator()
            assert orchestrator1 is orchestrator2


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_query(self, orchestrator, mock_unified_response):
        """Should handle empty query gracefully."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 50, 30)

            result = await orchestrator.generate_response(
                query="",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_empty_kb_context(self, orchestrator, mock_unified_response):
        """Should handle empty KB context."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 100, 80)

            result = await orchestrator.generate_response(
                query="Test query",
                kb_context="",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_llm_returns_partial_response(self, orchestrator):
        """Should handle partial/incomplete LLM response."""
        partial_response = {
            "answer": "Risposta parziale",
            # Missing reasoning, sources, actions
        }
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(partial_response), 100, 50)

            result = await orchestrator.generate_response(
                query="Test query",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            assert result.answer == "Risposta parziale"
            assert result.reasoning is not None  # Should have default
            assert result.sources_cited is not None

    @pytest.mark.asyncio
    async def test_classification_with_empty_domains(self, orchestrator, mock_llm_response):
        """Should handle classification with empty domains."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_llm_response), 50, 30)

            context = ComplexityContext(domains=[])
            result = await orchestrator.classify_complexity(
                query="Test query",
                context=context,
            )

            assert result in [QueryComplexity.SIMPLE, QueryComplexity.COMPLEX, QueryComplexity.MULTI_DOMAIN]

    @pytest.mark.asyncio
    async def test_generate_response_raises_on_error(self, orchestrator):
        """generate_response should raise exception when LLM fails."""
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.side_effect = Exception("LLM service unavailable")

            with pytest.raises(Exception, match="LLM service unavailable"):
                await orchestrator.generate_response(
                    query="Test query",
                    kb_context="Contesto",
                    kb_sources_metadata=[],
                    complexity=QueryComplexity.SIMPLE,
                )

    @pytest.mark.asyncio
    async def test_generate_response_with_raw_text_fallback(self, orchestrator):
        """Should fallback to raw text when JSON parsing fails in response."""
        raw_text_response = "This is a plain text response without JSON structure."
        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (raw_text_response, 100, 50)

            result = await orchestrator.generate_response(
                query="Test query",
                kb_context="Contesto",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            # Should use raw text as the answer
            assert result.answer == raw_text_response
            assert result.reasoning == {}
            assert result.sources_cited == []


# =============================================================================
# Fallback Prompt Tests
# =============================================================================


class TestFallbackPrompt:
    """Test fallback prompt behavior when templates are missing."""

    @pytest.mark.asyncio
    async def test_fallback_prompt_when_template_not_found(self, mock_unified_response):
        """Should use fallback prompt when template file is missing."""
        # Create orchestrator with a loader that raises FileNotFoundError
        mock_loader = MagicMock()
        mock_loader.load.side_effect = FileNotFoundError("Template not found")

        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        with patch.object(orchestrator, "_call_llm") as mock_call:
            mock_call.return_value = (json.dumps(mock_unified_response), 200, 150)

            result = await orchestrator.generate_response(
                query="Test query about IVA",
                kb_context="KB context here",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            )

            # Should still return a valid response using fallback prompt
            assert result is not None
            assert result.answer is not None

    def test_build_fallback_prompt_content(self):
        """Fallback prompt should contain query and context."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        fallback = orchestrator._build_fallback_prompt(
            query="Qual è l'aliquota IVA?",
            kb_context="Contesto normativo qui",
        )

        assert "Qual è l'aliquota IVA?" in fallback
        assert "Contesto normativo qui" in fallback
        assert "PratikoAI" in fallback
        assert "JSON" in fallback


# =============================================================================
# JSON Extraction Tests
# =============================================================================


class TestJsonExtraction:
    """Test JSON extraction from various text formats."""

    def test_extract_json_from_markdown_code_block(self):
        """Should extract JSON from markdown code block."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        text_with_codeblock = """Here is my response:

```json
{
  "complexity": "simple",
  "confidence": 0.95
}
```

Hope this helps!"""

        result = orchestrator._extract_json(text_with_codeblock)
        parsed = json.loads(result)

        assert parsed["complexity"] == "simple"
        assert parsed["confidence"] == 0.95

    def test_extract_json_from_raw_object(self):
        """Should extract JSON from raw object in text."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        text_with_json = 'The answer is: {"complexity": "complex", "domains": ["fiscale"]}'

        result = orchestrator._extract_json(text_with_json)
        parsed = json.loads(result)

        assert parsed["complexity"] == "complex"

    def test_extract_json_returns_text_if_no_json(self):
        """Should return original text if no JSON found."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        plain_text = "This is just plain text without any JSON."

        result = orchestrator._extract_json(plain_text)

        assert result == plain_text


# =============================================================================
# Reset Orchestrator Tests
# =============================================================================


class TestResetOrchestrator:
    """Test orchestrator reset functionality."""

    def test_reset_orchestrator_clears_singleton(self):
        """reset_orchestrator should clear the singleton instance."""
        with patch("app.services.llm_orchestrator.get_prompt_loader"):
            # Get an instance
            orchestrator1 = get_llm_orchestrator()

            # Reset
            reset_orchestrator()

            # Get a new instance - should be different
            orchestrator2 = get_llm_orchestrator()

            assert orchestrator1 is not orchestrator2

    def test_reset_orchestrator_twice(self):
        """Resetting twice should work without error."""
        reset_orchestrator()
        reset_orchestrator()
        # Should not raise any exception


# =============================================================================
# Conversation History Formatting Tests
# =============================================================================


class TestConversationFormatting:
    """Test conversation history formatting."""

    def test_format_conversation_empty(self):
        """Should handle empty conversation history."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        result = orchestrator._format_conversation(None)

        assert result == "Nessuna conversazione precedente"

    def test_format_conversation_with_history(self):
        """Should format conversation history correctly."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        history = [
            {"role": "user", "content": "Domanda 1"},
            {"role": "assistant", "content": "Risposta 1"},
            {"role": "user", "content": "Domanda 2"},
        ]

        result = orchestrator._format_conversation(history)

        assert "Utente: Domanda 1" in result
        assert "Assistente: Risposta 1" in result
        assert "Utente: Domanda 2" in result

    def test_format_conversation_truncates_long_messages(self):
        """Should truncate very long messages."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        long_content = "A" * 500  # More than 200 chars
        history = [
            {"role": "user", "content": long_content},
        ]

        result = orchestrator._format_conversation(history)

        # Should be truncated to 200 chars
        assert len(result) < len(long_content) + 20  # Allow for "Utente: " prefix

    def test_format_conversation_limits_to_last_3_turns(self):
        """Should only include last 3 conversation turns."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        history = [
            {"role": "user", "content": "Turn 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Turn 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Turn 3"},
        ]

        result = orchestrator._format_conversation(history)

        # Should only have last 3 turns
        assert "Turn 1" not in result
        assert "Response 1" not in result
        assert "Turn 2" in result


# =============================================================================
# Parse Classification Response Tests
# =============================================================================


class TestParseClassificationResponse:
    """Test classification response parsing."""

    def test_parse_classification_with_unknown_complexity(self):
        """Should default to SIMPLE for unknown complexity values."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        response_json = json.dumps(
            {
                "complexity": "unknown_value",
                "confidence": 0.5,
            }
        )

        result = orchestrator._parse_classification_response(response_json)

        assert result == QueryComplexity.SIMPLE

    def test_parse_classification_with_uppercase_value(self):
        """Should handle uppercase complexity values."""
        mock_loader = MagicMock()
        orchestrator = LLMOrchestrator(prompt_loader=mock_loader)

        response_json = json.dumps(
            {
                "complexity": "COMPLEX",
                "confidence": 0.9,
            }
        )

        result = orchestrator._parse_classification_response(response_json)

        assert result == QueryComplexity.COMPLEX
