"""Router Decision Schema for DEV-186.

Pydantic models and enums for LLM router per Section 13.4.4.
Replaces the regex-based GateDecision with structured semantic routing.

Usage:
    from app.schemas.router import RouterDecision, RoutingCategory, ExtractedEntity

    decision = RouterDecision(
        route=RoutingCategory.TECHNICAL_RESEARCH,
        confidence=0.92,
        reasoning="Query asks about P.IVA procedure",
        entities=[ExtractedEntity(text="P.IVA", type="ente", confidence=0.9)],
        requires_freshness=False,
        suggested_sources=["agenzia_entrate"],
    )
"""

from enum import Enum

from pydantic import BaseModel, Field, computed_field


class RoutingCategory(str, Enum):
    """Routing categories for LLM-based semantic classification.

    These categories replace the regex-based gate patterns with
    semantically-meaningful classifications.
    """

    CHITCHAT = "chitchat"
    """Casual conversation, greetings, off-topic queries."""

    THEORETICAL_DEFINITION = "theoretical_definition"
    """Requests for definitions, explanations of concepts."""

    TECHNICAL_RESEARCH = "technical_research"
    """Complex technical queries requiring RAG retrieval."""

    CALCULATOR = "calculator"
    """Calculation requests (tax, contributions, etc.)."""

    GOLDEN_SET = "golden_set"
    """Queries matching known high-value patterns (specific laws, articles)."""


class ExtractedEntity(BaseModel):
    """Entity extracted from the user query.

    Used by the router to identify specific legal references,
    dates, organizations, etc. that inform routing decisions.
    """

    text: str = Field(..., description="Entity text as found in query")
    type: str = Field(..., description="Entity type: legge, articolo, ente, data")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score",
    )


class RouterDecision(BaseModel):
    """LLM router decision with Chain-of-Thought reasoning.

    This model captures the full routing decision including:
    - The selected route category
    - Confidence level
    - Reasoning explanation (for debugging/audit)
    - Extracted entities
    - Additional metadata for downstream processing
    """

    route: RoutingCategory = Field(..., description="Selected routing category")
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Routing confidence score (0.0-1.0)",
    )
    reasoning: str = Field(
        ...,
        description="Chain-of-Thought explanation for the routing decision",
    )
    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Entities extracted from the query",
    )
    requires_freshness: bool = Field(
        default=False,
        description="Whether query requires fresh/recent data",
    )
    suggested_sources: list[str] = Field(
        default_factory=list,
        description="Suggested data sources for retrieval",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def needs_retrieval(self) -> bool:
        """Determine if this route requires RAG retrieval.

        Returns:
            True for routes that need document retrieval,
            False for routes that can be answered directly.
        """
        retrieval_routes = {
            RoutingCategory.TECHNICAL_RESEARCH,
            RoutingCategory.THEORETICAL_DEFINITION,
            RoutingCategory.GOLDEN_SET,
        }
        return self.route in retrieval_routes
