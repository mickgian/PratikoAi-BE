"""Step 35-38 Consolidated: LLM Fallback Resolution.

Performance optimization: merges LLMFallback (step 35), LLMBetter (step 36),
UseLLM (step 37), and UseRuleBased (step 38) into a single LangGraph node.

Eliminates 3 node transitions and 2 conditional routing decisions.
"""

import logging

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)

logger = logging.getLogger(__name__)


async def node_step_35_38(state: RAGState) -> RAGState:
    """Consolidated node: LLM Fallback + Compare + Resolve.

    Combines steps 35-38 into a single node:
    1. Run LLM fallback classification (step 35)
    2. Compare LLM vs rule-based (step 36)
    3. Use LLM (step 37) or rule-based (step 38) based on comparison

    On error, gracefully falls back to rule-based classification.
    """
    # Lazy imports to avoid database connection during module load
    from app.orchestrators.classify import step_35__llm_fallback
    from app.orchestrators.llm import step_36__llmbetter, step_37__use_llm
    from app.orchestrators.platform import step_38__use_rule_based

    rag_step_log(35, "enter", fallback_triggered=True)

    with rag_step_timer(35):
        try:
            # Step 35: LLM Fallback classification
            res = await step_35__llm_fallback(ctx=dict(state))

            classification = state.setdefault("classification", {})
            if "llm_domain" in res:
                classification["llm_domain"] = res["llm_domain"]
            if "llm_action" in res:
                classification["llm_action"] = res["llm_action"]
            if "llm_confidence" in res:
                classification["llm_confidence"] = res["llm_confidence"]
            classification["llm_fallback_used"] = res.get("fallback_used", True)

        except Exception as e:
            logger.warning(
                "step_035_038_llm_fallback_error: %s, falling_back_to_rule_based",
                str(e),
            )
            # On LLM error, use rule-based directly
            rb_res = await step_38__use_rule_based(messages=state.get("messages", []), ctx=dict(state))
            classification = state.setdefault("classification", {})
            classification["domain"] = rb_res.get("domain")
            classification["action"] = rb_res.get("action")
            classification["confidence"] = rb_res.get("confidence", 0.0)
            classification["method_used"] = "rule_based"
            classification["fallback_used"] = False
            rag_step_log(38, "exit", domain=classification.get("domain"), method="rule_based_error_fallback")
            return state

    with rag_step_timer(36):
        # Step 36: Compare LLM vs rule-based
        compare_res = await step_36__llmbetter(messages=state.get("messages", []), ctx=dict(state))
        llm_is_better = compare_res.get("llm_is_better", False)
        classification["llm_is_better"] = llm_is_better
        classification["comparison_reasoning"] = compare_res.get("reasoning")

    with rag_step_timer(37):
        if llm_is_better:
            # Step 37: Use LLM classification
            llm_res = await step_37__use_llm(messages=state.get("messages", []), ctx=dict(state))
            classification["domain"] = llm_res.get("domain")
            classification["action"] = llm_res.get("action")
            classification["confidence"] = llm_res.get("confidence", 0.0)
            classification["method_used"] = "llm"
            classification["fallback_used"] = True
        else:
            # Step 38: Use rule-based classification
            rb_res = await step_38__use_rule_based(messages=state.get("messages", []), ctx=dict(state))
            classification["domain"] = rb_res.get("domain")
            classification["action"] = rb_res.get("action")
            classification["confidence"] = rb_res.get("confidence", 0.0)
            classification["method_used"] = "rule_based"
            classification["fallback_used"] = False

    rag_step_log(
        38,
        "exit",
        domain=classification.get("domain"),
        confidence=classification.get("confidence"),
        method=classification.get("method_used"),
    )
    return state
