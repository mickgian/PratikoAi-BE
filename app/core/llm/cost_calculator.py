"""Cost calculation utilities for LLM providers."""

from dataclasses import dataclass
from enum import Enum
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

from app.core.llm.base import (
    LLMModelTier,
    LLMProvider,
)
from app.core.llm.utils import (
    get_message_content,
    get_message_role,
)
from app.core.logging import logger
from app.schemas.chat import Message


class QueryComplexity(str, Enum):
    """Query complexity levels for cost optimization."""

    SIMPLE = "simple"  # Basic Q&A, factual queries
    MODERATE = "moderate"  # Some reasoning required
    COMPLEX = "complex"  # Multi-step reasoning, analysis
    ADVANCED = "advanced"  # Research, document analysis


@dataclass
class CostEstimate:
    """Estimated cost for an LLM operation."""

    input_tokens: int
    estimated_output_tokens: int
    total_cost_eur: float
    provider: str
    model: str
    confidence: float  # 0.0 to 1.0


class CostCalculator:
    """Utility class for calculating and optimizing LLM costs."""

    def __init__(self):
        """Initialize cost calculator."""
        # Average output token ratios by query complexity
        self.output_token_ratios = {
            QueryComplexity.SIMPLE: 0.3,  # Short answers
            QueryComplexity.MODERATE: 0.6,  # Medium responses
            QueryComplexity.COMPLEX: 1.2,  # Detailed explanations
            QueryComplexity.ADVANCED: 2.0,  # Comprehensive responses
        }

        # Cost optimization thresholds (EUR)
        self.cost_thresholds = {
            "low": 0.001,  # < €0.001 - use any model
            "medium": 0.005,  # < €0.005 - avoid premium models
            "high": 0.020,  # < €0.020 - use basic models only
        }

    def classify_query_complexity(self, messages: List[Message]) -> QueryComplexity:
        """Classify the complexity of a query based on content analysis.

        Args:
            messages: List of conversation messages

        Returns:
            QueryComplexity classification
        """
        if not messages:
            return QueryComplexity.SIMPLE

        # Analyze the latest user message (handle both dict and Message object)
        user_messages = [msg for msg in messages if get_message_role(msg) == "user"]
        if not user_messages:
            return QueryComplexity.SIMPLE

        latest_message = get_message_content(user_messages[-1]).lower()

        # Keywords that indicate complexity
        complex_keywords = [
            "analyze",
            "compare",
            "evaluate",
            "calculate",
            "explain why",
            "what are the implications",
            "how does this affect",
            "pros and cons",
            "step by step",
            "detailed analysis",
            "comprehensive review",
        ]

        advanced_keywords = [
            "research",
            "investigate",
            "full report",
            "detailed breakdown",
            "legal analysis",
            "tax implications",
            "regulatory compliance",
            "audit",
            "comprehensive study",
            "in-depth analysis",
        ]

        moderate_keywords = [
            "how to",
            "what is",
            "difference between",
            "example of",
            "summary",
            "overview",
            "brief explanation",
        ]

        # Count keyword occurrences
        complex_count = sum(1 for keyword in complex_keywords if keyword in latest_message)
        advanced_count = sum(1 for keyword in advanced_keywords if keyword in latest_message)
        moderate_count = sum(1 for keyword in moderate_keywords if keyword in latest_message)

        # Additional complexity indicators
        message_length = len(latest_message)
        has_context = len(messages) > 2  # Ongoing conversation

        if advanced_count > 0 or message_length > 500:
            return QueryComplexity.ADVANCED
        elif complex_count > 0 or (message_length > 200 and has_context):
            return QueryComplexity.COMPLEX
        elif moderate_count > 0 or message_length > 100:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE

    def estimate_output_tokens(self, input_tokens: int, complexity: QueryComplexity) -> Tuple[int, float]:
        """Estimate output tokens based on input and complexity.

        Args:
            input_tokens: Number of input tokens
            complexity: Query complexity level

        Returns:
            Tuple of (estimated_output_tokens, confidence_score)
        """
        ratio = self.output_token_ratios[complexity]
        estimated_tokens = int(input_tokens * ratio)

        # Confidence decreases with higher complexity
        confidence_map = {
            QueryComplexity.SIMPLE: 0.9,
            QueryComplexity.MODERATE: 0.8,
            QueryComplexity.COMPLEX: 0.7,
            QueryComplexity.ADVANCED: 0.6,
        }

        confidence = confidence_map[complexity]

        # Apply bounds
        min_tokens = 10
        max_tokens = 4000  # Reasonable maximum for most queries

        estimated_tokens = max(min_tokens, min(estimated_tokens, max_tokens))

        return estimated_tokens, confidence

    def calculate_cost_estimate(
        self, provider: LLMProvider, messages: List[Message], complexity: Optional[QueryComplexity] = None
    ) -> CostEstimate:
        """Calculate cost estimate for a query with a specific provider.

        Args:
            provider: LLM provider instance
            messages: List of conversation messages
            complexity: Optional pre-classified complexity

        Returns:
            CostEstimate with detailed cost breakdown
        """
        if complexity is None:
            complexity = self.classify_query_complexity(messages)

        input_tokens = provider.estimate_tokens(messages)
        estimated_output_tokens, confidence = self.estimate_output_tokens(input_tokens, complexity)

        total_cost = provider.estimate_cost(input_tokens, estimated_output_tokens)

        return CostEstimate(
            input_tokens=input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            total_cost_eur=total_cost,
            provider=provider.provider_type.value,
            model=provider.model,
            confidence=confidence,
        )

    def find_optimal_provider(
        self,
        providers: List[LLMProvider],
        messages: List[Message],
        max_cost_eur: Optional[float] = None,
        min_tier: Optional[LLMModelTier] = None,
    ) -> Tuple[LLMProvider, CostEstimate]:
        """Find the optimal provider based on cost and capability requirements.

        Args:
            providers: List of available providers
            messages: List of conversation messages
            max_cost_eur: Maximum acceptable cost in EUR
            min_tier: Minimum required model tier

        Returns:
            Tuple of (optimal_provider, cost_estimate)
        """
        if not providers:
            raise ValueError("No providers available")

        complexity = self.classify_query_complexity(messages)
        estimates = []

        # Calculate estimates for all providers
        for provider in providers:
            try:
                estimate = self.calculate_cost_estimate(provider, messages, complexity)

                # Check if provider meets requirements
                model_info = provider.supported_models.get(provider.model)
                if model_info and min_tier:
                    # Simple tier comparison (assuming enum values are ordered)
                    tier_order = {
                        LLMModelTier.BASIC: 1,
                        LLMModelTier.STANDARD: 2,
                        LLMModelTier.ADVANCED: 3,
                        LLMModelTier.PREMIUM: 4,
                    }
                    if tier_order.get(model_info.tier, 1) < tier_order.get(min_tier, 1):
                        continue

                # Check cost constraint
                if max_cost_eur and estimate.total_cost_eur > max_cost_eur:
                    continue

                estimates.append((provider, estimate))

            except Exception as e:
                logger.warning(
                    "cost_estimation_failed", provider=provider.provider_type.value, model=provider.model, error=str(e)
                )
                continue

        if not estimates:
            # If no provider meets requirements, return the cheapest one
            logger.warning(
                "no_provider_meets_requirements",
                max_cost_eur=max_cost_eur,
                min_tier=min_tier.value if min_tier else None,
            )
            fallback_estimates = [
                (provider, self.calculate_cost_estimate(provider, messages, complexity)) for provider in providers
            ]
            if fallback_estimates:
                estimates = [min(fallback_estimates, key=lambda x: x[1].total_cost_eur)]
            else:
                raise ValueError("No viable providers found")

        # Sort by cost (ascending) and confidence (descending)
        estimates.sort(key=lambda x: (x[1].total_cost_eur, -x[1].confidence))

        optimal_provider, optimal_estimate = estimates[0]

        logger.info(
            "optimal_provider_selected",
            provider=optimal_provider.provider_type.value,
            model=optimal_provider.model,
            estimated_cost_eur=optimal_estimate.total_cost_eur,
            complexity=complexity.value,
            confidence=optimal_estimate.confidence,
        )

        return optimal_provider, optimal_estimate

    def get_cost_tier(self, cost_eur: float) -> str:
        """Get cost tier for a given cost amount.

        Args:
            cost_eur: Cost in EUR

        Returns:
            Cost tier ('low', 'medium', 'high')
        """
        if cost_eur < self.cost_thresholds["low"]:
            return "low"
        elif cost_eur < self.cost_thresholds["medium"]:
            return "medium"
        else:
            return "high"

    def should_use_cache(self, cost_estimate: CostEstimate, cache_hit_probability: float = 0.3) -> bool:
        """Determine if caching would be beneficial for this query.

        Args:
            cost_estimate: Cost estimate for the query
            cache_hit_probability: Probability of cache hit for similar queries

        Returns:
            True if caching is recommended
        """
        # Cache if cost is above low threshold and there's reasonable hit probability
        cost_tier = self.get_cost_tier(cost_estimate.total_cost_eur)

        if cost_tier == "low":
            return cache_hit_probability > 0.5  # Only cache if high hit probability
        elif cost_tier == "medium":
            return cache_hit_probability > 0.2  # Cache for moderate hit probability
        else:
            return True  # Always cache expensive queries
