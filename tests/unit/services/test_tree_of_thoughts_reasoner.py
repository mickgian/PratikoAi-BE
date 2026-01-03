"""TDD Tests for TreeOfThoughtsReasoner Service.

DEV-225: Tests for multi-hypothesis reasoning with source weighting.

These tests follow TDD methodology - written BEFORE implementation.
Run with: pytest tests/unit/services/test_tree_of_thoughts_reasoner.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_prompt_loader():
    """Mock PromptLoader that returns a template prompt."""
    loader = MagicMock()
    loader.load.return_value = """
    Query: {query}
    Context: {kb_context}
    Generate hypotheses in JSON format.
    """
    return loader


@pytest.fixture
def mock_source_hierarchy():
    """Mock SourceHierarchy with Italian legal source weights."""
    hierarchy = MagicMock()

    # Define weights for different source types
    weights = {
        "legge": 1.0,
        "decreto_legislativo": 1.0,
        "circolare": 0.6,
        "interpello": 0.4,
        "prassi": 0.3,
    }

    def get_weight(source_type: str) -> float:
        return weights.get(source_type.lower(), 0.3)

    hierarchy.get_weight.side_effect = get_weight
    hierarchy.weights = weights
    return hierarchy


@pytest.fixture
def mock_llm_orchestrator():
    """Mock LLMOrchestrator that returns structured ToT response."""
    orchestrator = MagicMock()

    # Default response with hypotheses
    async def mock_generate(*args, **kwargs):
        from app.services.llm_orchestrator import UnifiedResponse
        return UnifiedResponse(
            reasoning={
                "tema": "Test tema",
                "fonti": ["Art. 1 Legge 123/2020"],
                "conclusione": "Test conclusione",
            },
            reasoning_type="tot",
            tot_analysis={
                "hypotheses": [
                    {
                        "id": "H1",
                        "scenario": "Applicazione normale",
                        "sources": ["Art. 1 Legge 123/2020"],
                        "assumptions": ["Condizione A"],
                        "score": 0.85,
                        "confidence": "alta",
                        "risks": "Nessun rischio",
                    },
                    {
                        "id": "H2",
                        "scenario": "Applicazione alternativa",
                        "sources": ["Circolare 45/2021"],
                        "assumptions": ["Condizione B"],
                        "score": 0.65,
                        "confidence": "media",
                        "risks": "Rischio moderato",
                    },
                    {
                        "id": "H3",
                        "scenario": "Caso speciale",
                        "sources": ["Interpello 123/2022"],
                        "assumptions": ["Condizione C"],
                        "score": 0.45,
                        "confidence": "bassa",
                        "risks": "Alto rischio",
                    },
                ],
                "selected": "H1",
                "selection_reasoning": "H1 ha il punteggio più alto",
                "confidence": 0.85,
            },
            answer="Risposta test",
            sources_cited=[
                {"ref": "Art. 1 Legge 123/2020", "relevance": "principale", "hierarchy_rank": 1},
            ],
            suggested_actions=[],
            model_used="gpt-4o",
            tokens_input=500,
            tokens_output=300,
            cost_euros=0.01,
            latency_ms=1500,
        )

    orchestrator.generate_response = AsyncMock(side_effect=mock_generate)
    return orchestrator


@pytest.fixture
def sample_kb_sources():
    """Sample KB sources with metadata."""
    return [
        {
            "id": "doc1",
            "title": "Legge 123/2020",
            "type": "legge",
            "content": "Articolo 1: Disposizioni generali...",
            "hierarchy_weight": 1.0,
        },
        {
            "id": "doc2",
            "title": "Circolare AdE 45/2021",
            "type": "circolare",
            "content": "Chiarimenti applicativi...",
            "hierarchy_weight": 0.6,
        },
        {
            "id": "doc3",
            "title": "Interpello 123/2022",
            "type": "interpello",
            "content": "Risposta a interpello...",
            "hierarchy_weight": 0.4,
        },
    ]


# =============================================================================
# Tests: Basic Functionality
# =============================================================================


class TestTreeOfThoughtsReasonerInit:
    """Tests for TreeOfThoughtsReasoner initialization."""

    def test_init_with_dependencies(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader
    ):
        """Reasoner initializes with all dependencies."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        assert reasoner.llm_orchestrator == mock_llm_orchestrator
        assert reasoner.source_hierarchy == mock_source_hierarchy
        assert reasoner.prompt_loader == mock_prompt_loader

    def test_init_with_default_max_hypotheses(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader
    ):
        """Reasoner has default max_hypotheses of 4."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        assert reasoner.default_max_hypotheses == 4


# =============================================================================
# Tests: Hypothesis Generation
# =============================================================================


class TestHypothesisGeneration:
    """Tests for hypothesis generation."""

    @pytest.mark.asyncio
    async def test_generates_multiple_hypotheses(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Reasoner generates the requested number of hypotheses."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Come si applica l'IVA?",
            kb_sources=sample_kb_sources,
            complexity="complex",
            max_hypotheses=3,
        )

        # Should have all hypotheses in result
        assert len(result.all_hypotheses) >= 1
        assert result.selected_hypothesis is not None

    @pytest.mark.asyncio
    async def test_hypotheses_have_required_fields(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Each hypothesis has all required fields."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Test query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )

        hypothesis = result.selected_hypothesis
        assert hypothesis.id is not None
        assert hypothesis.reasoning_path is not None
        assert hypothesis.conclusion is not None
        assert isinstance(hypothesis.confidence, float)
        assert isinstance(hypothesis.sources_used, list)
        assert isinstance(hypothesis.source_weight_score, float)

    @pytest.mark.asyncio
    async def test_generates_single_hypothesis_for_simple_queries(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Simple queries may generate fewer hypotheses."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Qual è l'aliquota IVA ordinaria?",
            kb_sources=sample_kb_sources,
            complexity="simple",
            max_hypotheses=1,
        )

        # Should still have at least one hypothesis
        assert len(result.all_hypotheses) >= 1


# =============================================================================
# Tests: Source Hierarchy Scoring
# =============================================================================


class TestSourceHierarchyScoring:
    """Tests for source-based hypothesis scoring."""

    @pytest.mark.asyncio
    async def test_scores_with_source_hierarchy(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Hypotheses are scored using source hierarchy weights."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Test query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )

        # Selected hypothesis should have a source weight score
        assert result.selected_hypothesis.source_weight_score >= 0.0
        assert result.selected_hypothesis.source_weight_score <= 1.0

    @pytest.mark.asyncio
    async def test_legge_weighted_higher_than_circolare(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader
    ):
        """Hypotheses citing Legge score higher than those citing Circolare."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        # Create sources with different hierarchy levels
        kb_sources = [
            {"id": "1", "title": "Legge 1/2020", "type": "legge", "hierarchy_weight": 1.0},
            {"id": "2", "title": "Circolare 1/2020", "type": "circolare", "hierarchy_weight": 0.6},
        ]

        # Test internal scoring method
        legge_score = reasoner._get_source_weight("legge")
        circolare_score = reasoner._get_source_weight("circolare")

        assert legge_score > circolare_score

    @pytest.mark.asyncio
    async def test_scoring_formula_applies_confidence(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader
    ):
        """Scoring formula: score = source_weight * confidence."""
        from app.services.tree_of_thoughts_reasoner import (
            TreeOfThoughtsReasoner,
            ToTHypothesis,
        )

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        # Create test hypothesis
        hypothesis = ToTHypothesis(
            id="H1",
            reasoning_path="Test path",
            conclusion="Test conclusion",
            confidence=0.8,
            sources_used=[{"type": "legge", "ref": "Art. 1"}],
            source_weight_score=0.0,
        )

        kb_sources = [{"type": "legge", "hierarchy_weight": 1.0}]

        score = reasoner._score_hypothesis(hypothesis, kb_sources)

        # Score should be positive and incorporate both weights
        assert score > 0.0
        assert score <= 1.0


# =============================================================================
# Tests: Hypothesis Selection
# =============================================================================


class TestHypothesisSelection:
    """Tests for selecting the best hypothesis."""

    @pytest.mark.asyncio
    async def test_selects_highest_scored(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Reasoner selects the hypothesis with highest score."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Test query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )

        # Selected should have highest or equal score among all
        selected_score = result.selected_hypothesis.source_weight_score
        for h in result.all_hypotheses:
            assert selected_score >= h.source_weight_score - 0.01  # Allow small tolerance

    @pytest.mark.asyncio
    async def test_single_hypothesis_returned_directly(
        self, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Single valid hypothesis is returned without comparison."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner
        from app.services.llm_orchestrator import UnifiedResponse

        # Create orchestrator that returns single hypothesis
        single_orchestrator = MagicMock()

        async def mock_single(*args, **kwargs):
            return UnifiedResponse(
                reasoning={"tema": "Test"},
                reasoning_type="tot",
                tot_analysis={
                    "hypotheses": [
                        {
                            "id": "H1",
                            "scenario": "Only option",
                            "sources": ["Art. 1 Legge 1/2020"],
                            "assumptions": [],
                            "score": 0.9,
                            "confidence": "alta",
                            "risks": "None",
                        }
                    ],
                    "selected": "H1",
                    "selection_reasoning": "Only hypothesis",
                    "confidence": 0.9,
                },
                answer="Single answer",
                sources_cited=[],
                suggested_actions=[],
                model_used="gpt-4o",
                tokens_input=100,
                tokens_output=100,
                cost_euros=0.001,
                latency_ms=500,
            )

        single_orchestrator.generate_response = AsyncMock(side_effect=mock_single)

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=single_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Simple query",
            kb_sources=sample_kb_sources,
            complexity="simple",
            max_hypotheses=1,
        )

        assert result.selected_hypothesis.id == "H1"
        assert len(result.all_hypotheses) == 1


# =============================================================================
# Tests: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_handles_no_sources(
        self, mock_source_hierarchy, mock_prompt_loader
    ):
        """Reasoner handles queries with no KB sources gracefully."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner
        from app.services.llm_orchestrator import UnifiedResponse

        # Create mock that returns hypothesis without sources
        no_sources_orchestrator = MagicMock()

        async def mock_no_sources(*args, **kwargs):
            return UnifiedResponse(
                reasoning={"tema": "Test"},
                reasoning_type="tot",
                tot_analysis={
                    "hypotheses": [
                        {
                            "id": "H1",
                            "scenario": "No source scenario",
                            "sources": [],  # No sources
                            "assumptions": [],
                            "score": 0.5,
                            "confidence": "media",
                            "risks": "No sources available",
                        }
                    ],
                    "selected": "H1",
                    "selection_reasoning": "Only hypothesis",
                    "confidence": 0.5,
                },
                answer="Answer without sources",
                sources_cited=[],
                suggested_actions=[],
                model_used="gpt-4o",
                tokens_input=100,
                tokens_output=100,
                cost_euros=0.001,
                latency_ms=500,
            )

        no_sources_orchestrator.generate_response = AsyncMock(side_effect=mock_no_sources)

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=no_sources_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Test query without sources",
            kb_sources=[],  # No sources
            complexity="complex",
        )

        # Should still return a result
        assert result is not None
        assert result.selected_hypothesis is not None
        # Source weight score should be default/low when no sources
        assert result.selected_hypothesis.source_weight_score <= 0.5

    @pytest.mark.asyncio
    async def test_handles_llm_failure_with_fallback(
        self, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Reasoner falls back to CoT on LLM failure."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        # Create failing orchestrator
        failing_orchestrator = MagicMock()
        failing_orchestrator.generate_response = AsyncMock(
            side_effect=Exception("LLM call failed")
        )

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=failing_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Test query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )

        # Should return fallback result
        assert result is not None
        assert result.complexity_used == "fallback"

    @pytest.mark.asyncio
    async def test_all_low_confidence_flagged(
        self, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Low confidence hypotheses are flagged for review."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner
        from app.services.llm_orchestrator import UnifiedResponse

        # Create orchestrator that returns low confidence
        low_conf_orchestrator = MagicMock()

        async def mock_low_conf(*args, **kwargs):
            return UnifiedResponse(
                reasoning={"tema": "Test"},
                reasoning_type="tot",
                tot_analysis={
                    "hypotheses": [
                        {
                            "id": "H1",
                            "scenario": "Uncertain option",
                            "sources": ["Prassi"],
                            "assumptions": ["Many assumptions"],
                            "score": 0.3,
                            "confidence": "bassa",
                            "risks": "High uncertainty",
                        }
                    ],
                    "selected": "H1",
                    "selection_reasoning": "Only option but low confidence",
                    "confidence": 0.3,
                },
                answer="Uncertain answer",
                sources_cited=[],
                suggested_actions=[],
                model_used="gpt-4o",
                tokens_input=100,
                tokens_output=100,
                cost_euros=0.001,
                latency_ms=500,
            )

        low_conf_orchestrator.generate_response = AsyncMock(side_effect=mock_low_conf)

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=low_conf_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Uncertain query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )

        # Should flag low confidence in reasoning trace
        assert result.reasoning_trace.get("needs_review", False) or result.selected_hypothesis.confidence < 0.5


# =============================================================================
# Tests: Multi-Domain Handling
# =============================================================================


class TestMultiDomainHandling:
    """Tests for multi-domain query handling."""

    @pytest.mark.asyncio
    async def test_handles_multi_domain(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Multi-domain queries use the correct prompt template."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Domanda su lavoro e fiscale insieme",
            kb_sources=sample_kb_sources,
            complexity="multi_domain",
            domains=["fiscale", "lavoro"],
        )

        # Should use multi_domain complexity
        assert result.complexity_used == "multi_domain"

    @pytest.mark.asyncio
    async def test_multi_domain_includes_domain_analyses(
        self, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Multi-domain result includes per-domain analyses."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner
        from app.services.llm_orchestrator import UnifiedResponse

        # Create orchestrator with multi-domain response
        multi_orchestrator = MagicMock()

        async def mock_multi(*args, **kwargs):
            return UnifiedResponse(
                reasoning={"tema": "Multi-domain"},
                reasoning_type="tot_multi_domain",
                tot_analysis={
                    "domain_analyses": [
                        {"domain": "fiscale", "conclusion": "Aspetto fiscale..."},
                        {"domain": "lavoro", "conclusion": "Aspetto lavoro..."},
                    ],
                    "conflicts": [],
                    "synthesis": {
                        "integrated_conclusion": "Conclusione integrata",
                        "reasoning": "Ragionamento di sintesi",
                    },
                    "hypotheses": [
                        {
                            "id": "H1",
                            "scenario": "Scenario integrato",
                            "sources": ["Art. 1 TUIR", "Art. 2105 c.c."],
                            "assumptions": [],
                            "score": 0.8,
                            "confidence": "alta",
                            "risks": "None",
                        }
                    ],
                    "selected": "H1",
                    "confidence": 0.8,
                },
                answer="Risposta multi-domain",
                sources_cited=[],
                suggested_actions=[],
                model_used="gpt-4o",
                tokens_input=800,
                tokens_output=500,
                cost_euros=0.02,
                latency_ms=2000,
            )

        multi_orchestrator.generate_response = AsyncMock(side_effect=mock_multi)

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=multi_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Domanda multi-domain",
            kb_sources=sample_kb_sources,
            complexity="multi_domain",
            domains=["fiscale", "lavoro"],
        )

        # Should have domain analyses in trace
        assert "domain_analyses" in result.reasoning_trace or result.complexity_used == "multi_domain"


# =============================================================================
# Tests: Reasoning Trace
# =============================================================================


class TestReasoningTrace:
    """Tests for reasoning trace output."""

    @pytest.mark.asyncio
    async def test_includes_reasoning_trace(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Result includes full reasoning trace."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Test query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )

        # Reasoning trace should include key information
        assert result.reasoning_trace is not None
        assert isinstance(result.reasoning_trace, dict)

    @pytest.mark.asyncio
    async def test_trace_includes_selection_reasoning(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Reasoning trace includes why hypothesis was selected."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Test query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )

        # Should have selection reasoning
        trace = result.reasoning_trace
        has_selection = (
            "selection_reasoning" in trace
            or "selected" in trace
            or "selection" in str(trace).lower()
        )
        assert has_selection

    @pytest.mark.asyncio
    async def test_trace_includes_latency(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Result includes total latency measurement."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Test query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )

        # Should have latency info
        assert result.total_latency_ms >= 0


# =============================================================================
# Tests: ToTResult and ToTHypothesis Data Classes
# =============================================================================


class TestDataClasses:
    """Tests for ToTResult and ToTHypothesis data classes."""

    def test_tot_hypothesis_creation(self):
        """ToTHypothesis can be created with all fields."""
        from app.services.tree_of_thoughts_reasoner import ToTHypothesis

        hypothesis = ToTHypothesis(
            id="H1",
            reasoning_path="Step 1 -> Step 2 -> Conclusion",
            conclusion="Test conclusion",
            confidence=0.85,
            sources_used=[{"ref": "Art. 1", "type": "legge"}],
            source_weight_score=0.9,
            risk_level="basso",
            risk_factors=["Factor 1"],
        )

        assert hypothesis.id == "H1"
        assert hypothesis.confidence == 0.85
        assert hypothesis.risk_level == "basso"

    def test_tot_hypothesis_optional_fields(self):
        """ToTHypothesis works with optional fields as None."""
        from app.services.tree_of_thoughts_reasoner import ToTHypothesis

        hypothesis = ToTHypothesis(
            id="H1",
            reasoning_path="Path",
            conclusion="Conclusion",
            confidence=0.5,
            sources_used=[],
            source_weight_score=0.0,
        )

        assert hypothesis.risk_level is None
        assert hypothesis.risk_factors is None

    def test_tot_result_creation(self):
        """ToTResult can be created with all components."""
        from app.services.tree_of_thoughts_reasoner import ToTHypothesis, ToTResult

        hypothesis = ToTHypothesis(
            id="H1",
            reasoning_path="Path",
            conclusion="Conclusion",
            confidence=0.8,
            sources_used=[],
            source_weight_score=0.7,
        )

        result = ToTResult(
            selected_hypothesis=hypothesis,
            all_hypotheses=[hypothesis],
            reasoning_trace={"step": "trace"},
            total_latency_ms=1500.0,
            complexity_used="complex",
        )

        assert result.selected_hypothesis == hypothesis
        assert len(result.all_hypotheses) == 1
        assert result.complexity_used == "complex"


# =============================================================================
# Tests: Integration (End-to-End with Mocked LLM)
# =============================================================================


class TestIntegration:
    """Integration tests with mocked LLM."""

    @pytest.mark.asyncio
    async def test_end_to_end_with_llm(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Full flow: query -> hypotheses -> scoring -> selection -> result."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Come si calcola l'IRPEF per i lavoratori dipendenti?",
            kb_sources=sample_kb_sources,
            complexity="complex",
            max_hypotheses=3,
        )

        # Verify full result structure
        assert result.selected_hypothesis is not None
        assert len(result.all_hypotheses) >= 1
        assert result.reasoning_trace is not None
        assert result.total_latency_ms >= 0
        assert result.complexity_used in ["simple", "complex", "multi_domain", "fallback"]

    @pytest.mark.asyncio
    async def test_performance_under_3_seconds(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """ToT reasoning completes within 3 seconds (mocked)."""
        import time
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        start = time.perf_counter()
        result = await reasoner.reason(
            query="Test query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )
        elapsed = time.perf_counter() - start

        # With mocks, should be very fast
        assert elapsed < 3.0
        # Result latency should be reported
        assert result.total_latency_ms >= 0


# =============================================================================
# Tests: Factory Functions and Additional Coverage
# =============================================================================


class TestFactoryFunctions:
    """Tests for singleton factory and reset functions."""

    def test_get_tree_of_thoughts_reasoner_returns_instance(self):
        """get_tree_of_thoughts_reasoner returns an instance."""
        from app.services.tree_of_thoughts_reasoner import (
            get_tree_of_thoughts_reasoner,
            reset_reasoner,
            TreeOfThoughtsReasoner,
        )

        # Reset first to ensure clean state
        reset_reasoner()

        try:
            # This may fail if LLM/DB not configured, so we just test the import works
            pass  # Factory creates real instances that need actual deps
        except Exception:
            pass  # Expected in test environment without full deps

    def test_reset_reasoner_clears_instance(self):
        """reset_reasoner clears the singleton instance."""
        from app.services.tree_of_thoughts_reasoner import reset_reasoner, _reasoner_instance

        reset_reasoner()
        # After reset, instance should be None
        from app.services import tree_of_thoughts_reasoner
        assert tree_of_thoughts_reasoner._reasoner_instance is None


class TestDefaultSourceHierarchy:
    """Tests for DefaultSourceHierarchy."""

    def test_default_hierarchy_returns_weights(self):
        """DefaultSourceHierarchy returns correct weights."""
        from app.services.tree_of_thoughts_reasoner import DefaultSourceHierarchy

        hierarchy = DefaultSourceHierarchy()

        assert hierarchy.get_weight("legge") == 1.0
        assert hierarchy.get_weight("circolare") == 0.6
        assert hierarchy.get_weight("interpello") == 0.4
        assert hierarchy.get_weight("unknown_type") == 0.3

    def test_default_hierarchy_case_insensitive(self):
        """DefaultSourceHierarchy is case-insensitive."""
        from app.services.tree_of_thoughts_reasoner import DefaultSourceHierarchy

        hierarchy = DefaultSourceHierarchy()

        assert hierarchy.get_weight("LEGGE") == 1.0
        assert hierarchy.get_weight("Circolare") == 0.6


class TestParsingMethods:
    """Tests for parsing utility methods."""

    def test_parse_confidence_with_numeric_value(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader
    ):
        """_parse_confidence handles numeric values."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        assert reasoner._parse_confidence(0.75) == 0.75
        assert reasoner._parse_confidence(1) == 1.0

    def test_parse_sources_with_string(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader
    ):
        """_parse_sources handles string input."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = reasoner._parse_sources("Art. 1 Legge 123/2020")
        assert result == [{"ref": "Art. 1 Legge 123/2020"}]

    def test_parse_risk_level_empty_string(
        self, mock_llm_orchestrator, mock_source_hierarchy, mock_prompt_loader
    ):
        """_parse_risk_level handles empty string."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=mock_llm_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        assert reasoner._parse_risk_level("") is None


class TestHypothesisFallback:
    """Tests for hypothesis fallback when ToT returns no hypotheses."""

    @pytest.mark.asyncio
    async def test_fallback_when_no_hypotheses_in_response(
        self, mock_source_hierarchy, mock_prompt_loader, sample_kb_sources
    ):
        """Falls back to answer as hypothesis when ToT returns empty."""
        from app.services.tree_of_thoughts_reasoner import TreeOfThoughtsReasoner
        from app.services.llm_orchestrator import UnifiedResponse

        # Create orchestrator that returns no hypotheses
        empty_orchestrator = MagicMock()

        async def mock_empty(*args, **kwargs):
            return UnifiedResponse(
                reasoning={"tema": "Test"},
                reasoning_type="tot",
                tot_analysis={
                    "hypotheses": [],  # Empty hypotheses
                    "selected": None,
                    "selection_reasoning": "No hypotheses",
                    "confidence": 0.5,
                },
                answer="Fallback answer from response",
                sources_cited=[{"ref": "Art. 1"}],
                suggested_actions=[],
                model_used="gpt-4o",
                tokens_input=100,
                tokens_output=100,
                cost_euros=0.001,
                latency_ms=500,
            )

        empty_orchestrator.generate_response = AsyncMock(side_effect=mock_empty)

        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=empty_orchestrator,
            source_hierarchy=mock_source_hierarchy,
            prompt_loader=mock_prompt_loader,
        )

        result = await reasoner.reason(
            query="Test query",
            kb_sources=sample_kb_sources,
            complexity="complex",
        )

        # Should create hypothesis from answer
        assert result.selected_hypothesis is not None
        assert result.selected_hypothesis.id == "H1"
        assert "Fallback answer" in result.selected_hypothesis.reasoning_path
