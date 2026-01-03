"""TreeOfThoughtsReasoner Service for Multi-Hypothesis Reasoning.

DEV-225: Orchestrates multi-hypothesis reasoning with source weighting,
confidence scoring, and risk analysis for complex legal/tax queries.

Features:
- Generates multiple reasoning hypotheses
- Scores hypotheses using source hierarchy weights
- Selects best hypothesis with confidence scoring
- Handles multi-domain queries with parallel analysis
- Provides full reasoning trace for transparency

Usage:
    from app.services.tree_of_thoughts_reasoner import (
        TreeOfThoughtsReasoner,
        get_tree_of_thoughts_reasoner,
    )

    reasoner = get_tree_of_thoughts_reasoner()
    result = await reasoner.reason(
        query="Come si applica l'IVA?",
        kb_sources=sources,
        complexity="complex",
    )
"""

import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import structlog

from app.services.llm_orchestrator import (
    LLMOrchestrator,
    QueryComplexity,
    UnifiedResponse,
    get_llm_orchestrator,
)
from app.services.prompt_loader import PromptLoader, get_prompt_loader

logger = structlog.get_logger(__name__)


# =============================================================================
# Source Hierarchy Protocol (for DEV-227)
# =============================================================================


@runtime_checkable
class SourceHierarchyProtocol(Protocol):
    """Protocol for source hierarchy weighting.

    This protocol defines the interface that SourceHierarchy (DEV-227) will implement.
    For now, we provide a default implementation.
    """

    def get_weight(self, source_type: str) -> float:
        """Get weight for a source type (0.0 to 1.0)."""
        ...


class DefaultSourceHierarchy:
    """Default source hierarchy with Italian legal source weights.

    This is a minimal implementation until DEV-227 creates the full SourceHierarchy.
    """

    # Italian legal source hierarchy weights
    WEIGHTS = {
        # Level 1 - Primary Sources (weight: 1.0)
        "legge": 1.0,
        "decreto_legislativo": 1.0,
        "dpr": 1.0,
        "decreto_legge": 1.0,
        "d.lgs": 1.0,
        "d.l.": 1.0,
        # Level 2 - Secondary Sources (weight: 0.8)
        "decreto_ministeriale": 0.8,
        "regolamento_ue": 0.8,
        "d.m.": 0.8,
        # Level 3 - Administrative Practice (weight: 0.6)
        "circolare": 0.6,
        "risoluzione": 0.6,
        "provvedimento": 0.6,
        # Level 4 - Interpretations (weight: 0.4)
        "interpello": 0.4,
        "faq": 0.4,
        # Level 5 - Case Law (variable weight)
        "cassazione": 0.9,
        "corte_costituzionale": 1.0,
        "cgue": 0.95,
        "ctp_ctr": 0.5,
        # Default for unknown
        "prassi": 0.3,
    }

    def get_weight(self, source_type: str) -> float:
        """Get weight for a source type.

        Args:
            source_type: Type of legal source (e.g., "legge", "circolare")

        Returns:
            Weight between 0.0 and 1.0
        """
        return self.WEIGHTS.get(source_type.lower(), 0.3)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ToTHypothesis:
    """Single hypothesis in Tree of Thoughts reasoning.

    Represents one potential interpretation/answer path with its
    sources, confidence, and risk assessment.
    """

    id: str
    reasoning_path: str
    conclusion: str
    confidence: float
    sources_used: list[dict]
    source_weight_score: float
    risk_level: str | None = None
    risk_factors: list[str] | None = None


@dataclass
class ToTResult:
    """Result of Tree of Thoughts reasoning.

    Contains the selected hypothesis, all considered hypotheses,
    and full reasoning trace for transparency.
    """

    selected_hypothesis: ToTHypothesis
    all_hypotheses: list[ToTHypothesis]
    reasoning_trace: dict
    total_latency_ms: float
    complexity_used: str


# =============================================================================
# TreeOfThoughtsReasoner Service
# =============================================================================


class TreeOfThoughtsReasoner:
    """Orchestrates multi-hypothesis reasoning with source weighting.

    Uses Tree of Thoughts methodology to generate multiple interpretation
    paths, score them based on source authority, and select the best answer.

    Example:
        reasoner = TreeOfThoughtsReasoner(
            llm_orchestrator=orchestrator,
            source_hierarchy=hierarchy,
            prompt_loader=loader,
        )
        result = await reasoner.reason(
            query="Come si applica l'IVA?",
            kb_sources=sources,
            complexity="complex",
        )
    """

    def __init__(
        self,
        llm_orchestrator: LLMOrchestrator,
        source_hierarchy: SourceHierarchyProtocol | None = None,
        prompt_loader: PromptLoader | None = None,
    ):
        """Initialize TreeOfThoughtsReasoner.

        Args:
            llm_orchestrator: LLMOrchestrator for model routing and LLM calls
            source_hierarchy: Optional SourceHierarchy for source weighting
            prompt_loader: Optional PromptLoader for prompt templates
        """
        self.llm_orchestrator = llm_orchestrator
        self.source_hierarchy = source_hierarchy or DefaultSourceHierarchy()
        self.prompt_loader = prompt_loader or get_prompt_loader()
        self.default_max_hypotheses = 4

        logger.debug("tree_of_thoughts_reasoner_initialized")

    async def reason(
        self,
        query: str,
        kb_sources: list[dict],
        complexity: str,
        max_hypotheses: int = 4,
        domains: list[str] | None = None,
    ) -> ToTResult:
        """Execute Tree of Thoughts reasoning.

        Generates multiple hypotheses, scores them using source hierarchy,
        and selects the best answer with full reasoning trace.

        Args:
            query: User query to analyze
            kb_sources: Retrieved KB sources with metadata
            complexity: Query complexity ("simple", "complex", "multi_domain")
            max_hypotheses: Maximum hypotheses to generate (default: 4)
            domains: Optional list of domains for multi-domain queries

        Returns:
            ToTResult with selected hypothesis and full reasoning trace
        """
        start_time = time.perf_counter()
        complexity_used = complexity

        logger.info(
            "tot_reasoning_started",
            query_length=len(query),
            num_sources=len(kb_sources),
            complexity=complexity,
            max_hypotheses=max_hypotheses,
        )

        try:
            # Generate hypotheses via LLM
            hypotheses, tot_analysis = await self._generate_hypotheses(
                query=query,
                kb_sources=kb_sources,
                complexity=complexity,
                count=max_hypotheses,
                domains=domains,
            )

            # Score each hypothesis using source hierarchy
            for hypothesis in hypotheses:
                hypothesis.source_weight_score = self._score_hypothesis(
                    hypothesis, kb_sources
                )

            # Select best hypothesis
            selected = self._select_best(hypotheses)

            # Build reasoning trace
            reasoning_trace = self._build_reasoning_trace(
                hypotheses=hypotheses,
                selected=selected,
                tot_analysis=tot_analysis,
                domains=domains,
            )

            # Check if low confidence needs review
            if selected.confidence < 0.5:
                reasoning_trace["needs_review"] = True
                reasoning_trace["review_reason"] = "Low confidence score"

            total_latency_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "tot_reasoning_completed",
                selected_id=selected.id,
                selected_confidence=selected.confidence,
                num_hypotheses=len(hypotheses),
                latency_ms=total_latency_ms,
            )

            return ToTResult(
                selected_hypothesis=selected,
                all_hypotheses=hypotheses,
                reasoning_trace=reasoning_trace,
                total_latency_ms=total_latency_ms,
                complexity_used=complexity_used,
            )

        except Exception as e:
            logger.error(
                "tot_reasoning_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return fallback result
            return self._create_fallback_result(
                query=query,
                error=str(e),
                start_time=start_time,
            )

    async def _generate_hypotheses(
        self,
        query: str,
        kb_sources: list[dict],
        complexity: str,
        count: int,
        domains: list[str] | None = None,
    ) -> tuple[list[ToTHypothesis], dict]:
        """Generate multiple reasoning hypotheses via LLM.

        Args:
            query: User query
            kb_sources: KB sources with metadata
            complexity: Query complexity
            count: Number of hypotheses to generate
            domains: Optional domain list for multi-domain

        Returns:
            Tuple of (hypotheses list, raw tot_analysis dict)
        """
        # Map complexity string to enum
        complexity_enum = QueryComplexity(complexity)

        # Build KB context string
        kb_context = self._format_kb_context(kb_sources)

        # Get response from LLM
        response: UnifiedResponse = await self.llm_orchestrator.generate_response(
            query=query,
            kb_context=kb_context,
            kb_sources_metadata=kb_sources,
            complexity=complexity_enum,
        )

        # Parse hypotheses from response
        hypotheses = self._parse_hypotheses(response)

        # Get tot_analysis for trace
        tot_analysis = response.tot_analysis or {}

        return hypotheses, tot_analysis

    def _parse_hypotheses(self, response: UnifiedResponse) -> list[ToTHypothesis]:
        """Parse hypotheses from LLM response.

        Args:
            response: UnifiedResponse from LLM

        Returns:
            List of ToTHypothesis objects
        """
        hypotheses = []

        tot_analysis = response.tot_analysis or {}
        raw_hypotheses = tot_analysis.get("hypotheses", [])

        for raw in raw_hypotheses:
            hypothesis = ToTHypothesis(
                id=raw.get("id", f"H{len(hypotheses) + 1}"),
                reasoning_path=raw.get("scenario", ""),
                conclusion=raw.get("scenario", ""),  # Use scenario as conclusion
                confidence=self._parse_confidence(raw.get("confidence", "media")),
                sources_used=self._parse_sources(raw.get("sources", [])),
                source_weight_score=raw.get("score", 0.5),
                risk_level=self._parse_risk_level(raw.get("risks", "")),
                risk_factors=self._parse_risk_factors(raw.get("risks", "")),
            )
            hypotheses.append(hypothesis)

        # If no hypotheses from ToT, create one from the answer
        if not hypotheses:
            hypotheses.append(
                ToTHypothesis(
                    id="H1",
                    reasoning_path=response.answer,
                    conclusion=response.answer,
                    confidence=0.5,
                    sources_used=response.sources_cited,
                    source_weight_score=0.5,
                )
            )

        return hypotheses

    def _parse_confidence(self, confidence_value: Any) -> float:
        """Parse confidence to float.

        Args:
            confidence_value: Confidence as string or float

        Returns:
            Float confidence between 0.0 and 1.0
        """
        if isinstance(confidence_value, (int, float)):
            return float(confidence_value)

        # Map Italian confidence labels
        confidence_map = {
            "alta": 0.85,
            "high": 0.85,
            "media": 0.6,
            "medium": 0.6,
            "bassa": 0.35,
            "low": 0.35,
        }
        return confidence_map.get(str(confidence_value).lower(), 0.5)

    def _parse_sources(self, sources: list | str) -> list[dict]:
        """Parse sources to list of dicts.

        Args:
            sources: Sources as list or string

        Returns:
            List of source dicts
        """
        if isinstance(sources, list):
            return [
                {"ref": s} if isinstance(s, str) else s
                for s in sources
            ]
        return [{"ref": str(sources)}]

    def _parse_risk_level(self, risks: str) -> str | None:
        """Parse risk level from risks string.

        Args:
            risks: Risk description string

        Returns:
            Risk level or None
        """
        if not risks:
            return None

        risks_lower = risks.lower()
        if "alto" in risks_lower or "high" in risks_lower:
            return "alto"
        elif "medio" in risks_lower or "medium" in risks_lower or "moderato" in risks_lower:
            return "medio"
        elif "basso" in risks_lower or "low" in risks_lower or "nessun" in risks_lower:
            return "basso"
        return "medio"

    def _parse_risk_factors(self, risks: str) -> list[str] | None:
        """Parse risk factors from risks string.

        Args:
            risks: Risk description string

        Returns:
            List of risk factors or None
        """
        if not risks or risks.lower() in ("nessun rischio", "none", "nessuno"):
            return None
        return [risks]

    def _score_hypothesis(
        self,
        hypothesis: ToTHypothesis,
        kb_sources: list[dict],
    ) -> float:
        """Score hypothesis using source hierarchy weighting.

        Formula: score = weighted_average(source_weights) * confidence

        Args:
            hypothesis: Hypothesis to score
            kb_sources: Available KB sources

        Returns:
            Score between 0.0 and 1.0
        """
        if not hypothesis.sources_used:
            # No sources: use base confidence with penalty
            return hypothesis.confidence * 0.5

        # Calculate weighted average of source weights
        total_weight = 0.0
        source_count = 0

        for source in hypothesis.sources_used:
            source_type = self._extract_source_type(source)
            weight = self._get_source_weight(source_type)
            total_weight += weight
            source_count += 1

        if source_count == 0:
            return hypothesis.confidence * 0.5

        avg_source_weight = total_weight / source_count

        # Final score: source weight * confidence
        score = avg_source_weight * hypothesis.confidence

        return min(score, 1.0)

    def _extract_source_type(self, source: dict | str) -> str:
        """Extract source type from source reference.

        Args:
            source: Source dict or string

        Returns:
            Source type string
        """
        if isinstance(source, dict):
            # Try type field first
            if "type" in source:
                return source["type"]
            # Try to infer from ref
            ref = source.get("ref", "")
        else:
            ref = str(source)

        # Infer type from reference text
        ref_lower = ref.lower()
        if "legge" in ref_lower or "l." in ref_lower:
            return "legge"
        elif "d.lgs" in ref_lower or "decreto legislativo" in ref_lower:
            return "decreto_legislativo"
        elif "circolare" in ref_lower:
            return "circolare"
        elif "interpello" in ref_lower:
            return "interpello"
        elif "cassazione" in ref_lower:
            return "cassazione"
        elif "d.m." in ref_lower or "decreto ministeriale" in ref_lower:
            return "decreto_ministeriale"

        return "prassi"

    def _get_source_weight(self, source_type: str) -> float:
        """Get weight for a source type.

        Args:
            source_type: Type of source

        Returns:
            Weight between 0.0 and 1.0
        """
        return self.source_hierarchy.get_weight(source_type)

    def _select_best(self, hypotheses: list[ToTHypothesis]) -> ToTHypothesis:
        """Select the best hypothesis based on score.

        Args:
            hypotheses: List of scored hypotheses

        Returns:
            Best hypothesis
        """
        if not hypotheses:
            raise ValueError("No hypotheses to select from")

        if len(hypotheses) == 1:
            return hypotheses[0]

        # Sort by source_weight_score descending
        sorted_hypotheses = sorted(
            hypotheses,
            key=lambda h: h.source_weight_score,
            reverse=True,
        )

        return sorted_hypotheses[0]

    def _build_reasoning_trace(
        self,
        hypotheses: list[ToTHypothesis],
        selected: ToTHypothesis,
        tot_analysis: dict,
        domains: list[str] | None = None,
    ) -> dict:
        """Build reasoning trace for transparency.

        Args:
            hypotheses: All hypotheses considered
            selected: Selected hypothesis
            tot_analysis: Raw ToT analysis from LLM
            domains: Optional domain list

        Returns:
            Reasoning trace dict
        """
        trace = {
            "total_hypotheses": len(hypotheses),
            "selected_id": selected.id,
            "selected_confidence": selected.confidence,
            "selected_source_weight": selected.source_weight_score,
            "selection_reasoning": f"Hypothesis {selected.id} selected with highest weighted score",
            "hypotheses_summary": [
                {
                    "id": h.id,
                    "confidence": h.confidence,
                    "source_weight_score": h.source_weight_score,
                    "num_sources": len(h.sources_used),
                }
                for h in hypotheses
            ],
        }

        # Include domain analyses for multi-domain
        if domains and "domain_analyses" in tot_analysis:
            trace["domain_analyses"] = tot_analysis["domain_analyses"]

        # Include conflicts if present
        if "conflicts" in tot_analysis:
            trace["conflicts"] = tot_analysis["conflicts"]

        # Include synthesis if present
        if "synthesis" in tot_analysis:
            trace["synthesis"] = tot_analysis["synthesis"]

        return trace

    def _format_kb_context(self, kb_sources: list[dict]) -> str:
        """Format KB sources into context string.

        Args:
            kb_sources: List of KB source dicts

        Returns:
            Formatted context string
        """
        if not kb_sources:
            return "Nessun contesto disponibile."

        context_parts = []
        for source in kb_sources[:5]:  # Limit to top 5 sources
            title = source.get("title", "Documento")
            content = source.get("content", "")[:500]  # Truncate content
            context_parts.append(f"**{title}**\n{content}")

        return "\n\n---\n\n".join(context_parts)

    def _create_fallback_result(
        self,
        query: str,
        error: str,
        start_time: float,
    ) -> ToTResult:
        """Create fallback result when ToT reasoning fails.

        Args:
            query: Original query
            error: Error message
            start_time: Start time for latency calculation

        Returns:
            Fallback ToTResult
        """
        fallback_hypothesis = ToTHypothesis(
            id="FALLBACK",
            reasoning_path="Fallback path due to error",
            conclusion="Unable to complete full ToT reasoning",
            confidence=0.3,
            sources_used=[],
            source_weight_score=0.3,
            risk_level="alto",
            risk_factors=[f"ToT reasoning failed: {error}"],
        )

        total_latency_ms = (time.perf_counter() - start_time) * 1000

        return ToTResult(
            selected_hypothesis=fallback_hypothesis,
            all_hypotheses=[fallback_hypothesis],
            reasoning_trace={
                "fallback": True,
                "error": error,
                "needs_review": True,
            },
            total_latency_ms=total_latency_ms,
            complexity_used="fallback",
        )


# =============================================================================
# Factory Function (Singleton)
# =============================================================================

_reasoner_instance: TreeOfThoughtsReasoner | None = None


def get_tree_of_thoughts_reasoner() -> TreeOfThoughtsReasoner:
    """Get the singleton TreeOfThoughtsReasoner instance.

    Returns:
        TreeOfThoughtsReasoner instance
    """
    global _reasoner_instance
    if _reasoner_instance is None:
        _reasoner_instance = TreeOfThoughtsReasoner(
            llm_orchestrator=get_llm_orchestrator(),
            source_hierarchy=DefaultSourceHierarchy(),
            prompt_loader=get_prompt_loader(),
        )
    return _reasoner_instance


def reset_reasoner() -> None:
    """Reset the singleton instance (for testing)."""
    global _reasoner_instance
    _reasoner_instance = None
