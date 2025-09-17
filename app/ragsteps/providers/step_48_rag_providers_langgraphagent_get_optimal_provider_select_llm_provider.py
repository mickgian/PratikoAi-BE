#!/usr/bin/env python3
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log
except Exception:  # pragma: no cover
    def rag_step_log(**kwargs):  # fallback no-op
        return None

# ✅ Correct location for RoutingStrategy & get_llm_provider
from app.core.llm.factory import get_llm_provider, RoutingStrategy

STEP = 48
STEP_ID = "RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider"
NODE_LABEL = "SelectProvider"
CATEGORY = "providers"
TYPE = "process"

"""
RAG STEP 48 — LangGraphAgent._get_optimal_provider Select LLM provider
ID: RAG.providers.langgraphagent.get.optimal.provider.select.llm.provider
Type: process
Category: providers
"""

__all__ = ["run", "select_optimal_provider"]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapter for RAG STEP 48: Select LLM provider."""
    try:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="select_optimal_provider",
            confidence=1.0,
            reasons=["adapter_sentinel"],
            trace_id=payload.get("trace_id") if isinstance(payload, dict) else None,
        )
    except Exception:
        pass

    return {"step": STEP, "step_id": STEP_ID, "node": NODE_LABEL, "ok": True}


def _enum_value(x: Any) -> Optional[str]:
    """Helper: return .value if Enum-like, else None."""
    if x is None:
        return None
    return getattr(x, "value", None)


def select_optimal_provider(
    messages: List[Any],
    classification: Optional[Any] = None,
    routing_strategy: Optional[str] = None,
    max_cost_eur: Optional[float] = None,
    preferred_provider: Optional[str] = None,
) -> Any:
    """Select optimal LLM provider based on context and constraints (STEP 48)."""

    # Determine routing strategy + baseline cost
    if routing_strategy:
        strategy = RoutingStrategy(routing_strategy)
    elif classification:
        domain = _enum_value(getattr(classification, "domain", None))
        action = _enum_value(getattr(classification, "action", None))

        # High-accuracy requirements
        if (domain, action) in {
            ("legal", "document_generation"),
            ("tax", "calculation_request"),
        }:
            strategy = RoutingStrategy.QUALITY_FIRST
            max_cost_eur = max_cost_eur or 0.030 if domain == "legal" else max(0.020, (max_cost_eur or 0.020))
        elif (domain, action) == ("labor", "ccnl_query"):
            strategy = RoutingStrategy.BALANCED
            max_cost_eur = max_cost_eur or 0.018
        elif (domain, action) == ("business", "information_request"):
            strategy = RoutingStrategy.COST_OPTIMIZED
            max_cost_eur = max_cost_eur or 0.015
        else:
            strategy = RoutingStrategy.BALANCED
            max_cost_eur = max_cost_eur or 0.020
    else:
        strategy = RoutingStrategy.COST_OPTIMIZED
        max_cost_eur = max_cost_eur or 0.020

    try:
        provider = get_llm_provider(
            messages=messages,
            strategy=strategy,
            max_cost_eur=max_cost_eur,
            preferred_provider=preferred_provider,
        )

        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="provider_selected",
            provider_type=getattr(getattr(provider, "provider_type", None), "value", None),
            model=getattr(provider, "model", None),
            routing_strategy=strategy.value,
            max_cost_eur=max_cost_eur,
            classification_used=classification is not None,
            domain=_enum_value(getattr(classification, "domain", None)),
            action=_enum_value(getattr(classification, "action", None)),
            classification_confidence=getattr(classification, "confidence", None),
            preferred_provider=preferred_provider,
            messages_count=len(messages),
            messages_empty=len(messages) == 0,
            processing_stage="completed",
        )
        return provider

    except Exception as e:
        rag_step_log(
            step=STEP,
            step_id=STEP_ID,
            node_label=NODE_LABEL,
            decision="fallback_to_legacy",
            error=str(e),
            routing_strategy=strategy.value if "strategy" in locals() else None,
            max_cost_eur=max_cost_eur,
            classification_used=classification is not None,
            processing_stage="error_fallback",
        )
        from app.core.llm.providers.openai_provider import OpenAIProvider
        from app.core.config import settings

        return OpenAIProvider(
            api_key=settings.LLM_API_KEY or settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL or settings.OPENAI_MODEL,
        )
