#!/usr/bin/env python3
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs):  # fallback no-op
        return None

from app.core.llm.factory import RoutingStrategy
from app.schemas.chat import Message

STEP = 50
STEP_ID = "RAG.platform.routing.strategy"
NODE_LABEL = "StrategyType"
CATEGORY = "platform"
TYPE = "decision"

"""
RAG STEP 50 — Routing strategy? (decision)
ID: RAG.platform.routing.strategy
Type: decision
Category: platform
"""

__all__ = ["run", "determine_routing_strategy_path"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapter for RAG STEP 50: Routing strategy? decision."""
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="routing_strategy_decision_adapter",
            confidence=1.0,
            reasons=["adapter_sentinel"],
            trace_id=payload.get("trace_id") if isinstance(payload, dict) else None,
        )
    except Exception:
        pass

    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


def determine_routing_strategy_path(
    messages: List[Message],
    strategy: RoutingStrategy,
    max_cost_eur: Optional[float] = None,
    preferred_provider: Optional[str] = None,
    **kwargs
) -> str:
    """Determine the next step based on routing strategy.

    This function implements RAG STEP 50, which is a decision node that determines
    which specific provider selection strategy to execute based on the RoutingStrategy.

    Args:
        messages: List of conversation messages
        strategy: Routing strategy to evaluate
        max_cost_eur: Maximum acceptable cost in EUR
        preferred_provider: Preferred provider type
        **kwargs: Additional context parameters

    Returns:
        Next step name based on routing strategy:
        - "CheapProvider" for COST_OPTIMIZED
        - "BestProvider" for QUALITY_FIRST
        - "BalanceProvider" for BALANCED
        - "PrimaryProvider" for FAILOVER
    """
    try:
        # Map routing strategy to next step
        strategy_to_step = {
            RoutingStrategy.COST_OPTIMIZED: ("CheapProvider", "routing_to_cost_optimized"),
            RoutingStrategy.QUALITY_FIRST: ("BestProvider", "routing_to_quality_first"),
            RoutingStrategy.BALANCED: ("BalanceProvider", "routing_to_balanced"),
            RoutingStrategy.FAILOVER: ("PrimaryProvider", "routing_to_failover"),
        }

        # Get the next step and decision label
        if strategy in strategy_to_step:
            next_step, decision = strategy_to_step[strategy]
            fallback_reason = None
        else:
            # Fallback to balanced for unsupported strategies
            next_step = "BalanceProvider"
            decision = "routing_fallback_to_balanced"
            fallback_reason = getattr(strategy, 'value', str(strategy))

        # Log the routing decision
        log_params = {
            'step': STEP,
            'step_id': STEP_ID,
            'node_label': NODE_LABEL,
            'decision': decision,
            'routing_strategy': getattr(strategy, 'value', str(strategy)),
            'next_step': next_step,
            'max_cost_eur': max_cost_eur,
            'preferred_provider': preferred_provider,
            'messages_count': len(messages),
            'messages_empty': len(messages) == 0,
            'processing_stage': "completed",
        }

        # Add fallback reason if applicable
        if fallback_reason:
            log_params['fallback_reason'] = fallback_reason

        # Add any additional context from kwargs
        for key, value in kwargs.items():
            if key not in log_params and value is not None:
                log_params[key] = value

        rag_step_log(**log_params)

        return next_step

    except Exception as e:
        # Log error during routing decision
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="routing_decision_failed",
            error=str(e),
            routing_strategy=getattr(strategy, 'value', None) if strategy else None,
            messages_count=len(messages) if messages else 0,
            processing_stage="error",
        )

        # Fallback to balanced strategy on error
        return "BalanceProvider"
