"""Step 31+32 Consolidated: Classify Domain and Calculate Scores.

Performance optimization: merges ClassifyDomain (step 31) and CalcScores
(step 32) into a single LangGraph node, eliminating one node transition.

Both steps run sequentially (CalcScores depends on classification output)
but removing the graph transition overhead saves ~200-500ms.
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


async def node_step_31_32(state: RAGState) -> RAGState:
    """Consolidated node: Classify Domain + Calculate Scores.

    Combines steps 31 and 32 to reduce LangGraph node transition overhead.
    Logic is identical to the original separate nodes.
    """
    # Lazy imports to avoid database connection during module load
    from app.orchestrators.classify import step_31__classify_domain, step_32__calc_scores

    rag_step_log(31, "enter", domain=state.get("classification", {}).get("domain", "unknown"))

    with rag_step_timer(31):
        # Step 31: Classify Domain
        res = await step_31__classify_domain(messages=state.get("messages", []), ctx=dict(state))

        state["classification"] = {
            "timestamp": res.get("timestamp"),
            "domain": res.get("domain"),
            "action": res.get("action"),
            "confidence": res.get("confidence", 0.0),
            "fallback_used": res.get("fallback_used", False),
            "query_length": res.get("query_length", 0),
            "error": res.get("error"),
        }
        state["query_composition"] = res.get("query_composition")

        if "classification" in res and isinstance(res["classification"], dict):
            state["classification"].update(res["classification"])

    with rag_step_timer(32):
        # Step 32: Calculate Scores
        score_res = await step_32__calc_scores(messages=state.get("messages", []), ctx=dict(state))

        classification = state["classification"]
        if "domain_scores" in score_res:
            classification["domain_scores"] = score_res["domain_scores"]
        if "action_scores" in score_res:
            classification["action_scores"] = score_res["action_scores"]
        if "matched_keywords" in score_res:
            classification["matched_keywords"] = score_res["matched_keywords"]

    rag_step_log(
        32,
        "exit",
        domain=state["classification"].get("domain"),
        confidence=state["classification"].get("confidence"),
        scores_calculated=True,
    )
    return state
