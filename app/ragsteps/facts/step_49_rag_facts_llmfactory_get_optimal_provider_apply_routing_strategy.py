#!/usr/bin/env python3
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs):  # fallback no-op
        return None

from app.core.llm.factory import get_llm_provider, RoutingStrategy, LLMFactory
from app.core.llm.base import LLMProvider
from app.schemas.chat import Message

STEP = 49
STEP_ID = "RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy"
NODE_LABEL = "RouteStrategy"
CATEGORY = "facts"
TYPE = "process"

"""
RAG STEP 49 — LLMFactory.get_optimal_provider Apply routing strategy
ID: RAG.facts.llmfactory.get.optimal.provider.apply.routing.strategy
Type: process
Category: facts
"""

__all__ = ["run", "apply_routing_strategy"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapter for RAG STEP 49: Apply routing strategy."""
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="routing_strategy_adapter",
            confidence=1.0,
            reasons=["adapter_sentinel"],
            trace_id=payload.get("trace_id") if isinstance(payload, dict) else None,
        )
    except Exception:
        pass

    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


def apply_routing_strategy(
    messages: List[Message],
    strategy: RoutingStrategy,
    max_cost_eur: Optional[float] = None,
    preferred_provider: Optional[str] = None,
    llm_factory: Optional[LLMFactory] = None,
) -> LLMProvider:
    """Apply routing strategy to get optimal LLM provider.

    This function implements RAG STEP 49, which applies the selected routing
    strategy through the LLMFactory to obtain the optimal provider based on
    the given constraints and strategy.

    Args:
        messages: List of conversation messages
        strategy: Routing strategy to apply
        max_cost_eur: Maximum acceptable cost in EUR
        preferred_provider: Preferred provider type
        llm_factory: LLM factory instance (optional, will create default if None)

    Returns:
        Optimal LLM provider based on routing strategy

    Raises:
        ValueError: If no suitable provider is found
    """
    try:
        # Use provided factory or get default
        if llm_factory is None:
            llm_factory = LLMFactory()

        # Apply the routing strategy through LLMFactory
        provider = llm_factory.get_optimal_provider(
            messages=messages,
            strategy=strategy,
            max_cost_eur=max_cost_eur,
            preferred_provider=preferred_provider
        )

        # Log successful routing strategy application
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="routing_strategy_applied",
            routing_strategy=strategy.value,
            max_cost_eur=max_cost_eur,
            preferred_provider=preferred_provider,
            provider_type=getattr(getattr(provider, "provider_type", None), "value", None),
            model=getattr(provider, "model", None),
            messages_count=len(messages),
            messages_empty=len(messages) == 0,
            processing_stage="completed",
        )

        return provider

    except Exception as e:
        # Log error during routing strategy application
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="routing_strategy_failed",
            error=str(e),
            routing_strategy=getattr(strategy, "value", None),
            max_cost_eur=max_cost_eur,
            preferred_provider=preferred_provider,
            messages_count=len(messages) if messages else 0,
            processing_stage="error",
        )

        # Re-raise the exception - let calling code handle fallback
        raise
