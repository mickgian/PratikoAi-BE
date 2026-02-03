"""Node wrapper for Step 64: LLM Call. DEV-250: Thin wrapper using llm_response service."""

import time
from typing import Any

from app.core.langgraph.node_utils import mirror, ns
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.providers import step_64__llmcall
from app.services.llm_response import (
    check_kb_empty_and_inject_warning,
    classify_query_complexity,
    deanonymize_response,
    extract_user_message,
    get_llm_orchestrator,
    process_unified_response,
    use_tree_of_thoughts,
    validate_citations_in_response,
)
from app.services.reasoning_trace_logger import log_reasoning_trace_recorded, log_tot_hypothesis_evaluated

STEP = 64


def _merge(d: dict[str, Any], p: dict[str, Any]) -> None:
    for k, v in (p or {}).items():
        d[k] = v if not isinstance(v, dict) or not isinstance(d.setdefault(k, {}), dict) else _merge(d[k], v) or d[k]


async def node_step_64(state: RAGState) -> RAGState:
    """Node wrapper for Step 64: LLM Call."""
    t0 = time.perf_counter()
    rag_step_log(STEP, "enter", provider=state.get("provider", {}).get("selected"))
    with rag_step_timer(STEP):
        if "kb_was_empty" not in state:
            state["kb_was_empty"] = check_kb_empty_and_inject_warning(state)
        cplx, ctx = await classify_query_complexity(state)
        state["query_complexity"], state["complexity_context"] = cplx, ctx

        tot_used = False
        tot_response = None  # DEV-251: Store ToT response for reuse
        if cplx in ("complex", "multi_domain"):
            try:
                tot = await use_tree_of_thoughts(state, cplx)
                state.update(
                    reasoning_type="tot",
                    reasoning_trace=tot.reasoning_trace,
                    tot_analysis={
                        "selected_hypothesis_id": tot.selected_hypothesis.id,
                        "selected_confidence": tot.selected_hypothesis.confidence,
                        "source_weight_score": tot.selected_hypothesis.source_weight_score,
                        "total_hypotheses": len(tot.all_hypotheses),
                        "complexity_used": tot.complexity_used,
                        "latency_ms": tot.total_latency_ms,
                    },
                )
                tot_used = True
                # DEV-251: Capture the LLM response from ToT for reuse
                tot_response = tot.llm_response
                for h in tot.all_hypotheses:
                    log_tot_hypothesis_evaluated(
                        state, h.id, h.confidence, h.source_weight_score, h.id == tot.selected_hypothesis.id
                    )
            except Exception:
                state.update(reasoning_type="cot", tot_fallback=True)

        from app.services.llm_orchestrator import QueryComplexity as QC  # noqa: N817

        user_msg, kb_ctx = extract_user_message(state), state.get("context", "") or state.get("kb_context", "")
        cplx_enum = {"simple": QC.SIMPLE, "complex": QC.COMPLEX, "multi_domain": QC.MULTI_DOMAIN}.get(cplx, QC.SIMPLE)

        # DEV-251 Part 3.2: Extract is_followup from routing_decision
        routing_decision = state.get("routing_decision", {})
        is_followup = routing_decision.get("is_followup", False)

        try:
            # DEV-251: Reuse ToT response if available, avoiding duplicate LLM call
            if tot_used and tot_response is not None:
                r = tot_response
                rag_step_log(STEP, "reusing_tot_response", model=r.model_used)
            else:
                r = await get_llm_orchestrator().generate_response(
                    query=user_msg,
                    kb_context=kb_ctx,
                    kb_sources_metadata=state.get("kb_sources_metadata", []),
                    complexity=cplx_enum,
                    conversation_history=state.get("messages", []),
                    web_sources_metadata=state.get("web_sources_metadata", []),
                    domains=state.get("detected_domains", []),
                    is_followup=is_followup,  # DEV-251 Part 3.2: Pass follow-up flag
                )
            res = {
                "llm_call_successful": True,
                "response": {"content": r.answer},
                "model": r.model_used,
                "tokens_used": {"input": r.tokens_input, "output": r.tokens_output},
                "cost_estimate": r.cost_euros,
            }
            if r.sources_cited:
                state["sources_cited"] = r.sources_cited
        except Exception:
            res = await step_64__llmcall(
                messages=state.get("messages"), ctx={**state, "query_complexity": cplx, "tot_used": tot_used}
            )

        llm, priv = ns(state, "llm"), state.get("privacy") or {}
        dmap = priv.get("document_deanonymization_map", {})
        if res.get("error"):
            llm["error"], llm["success"] = res["error"], False
        elif res.get("llm_call_successful") or res.get("response"):
            llm["success"] = res.get("llm_call_successful", True)
            if rsp := res.get("response") or res.get("llm_response"):
                llm["response"] = rsp
                mirror(state, "llm_response", rsp)
                if cnt := rsp.get("content") if isinstance(rsp, dict) else getattr(rsp, "content", None):
                    if dmap:
                        cnt = deanonymize_response(cnt, dmap)
                        priv["document_deanonymization_map"], state["privacy"] = {}, priv
                    disp = process_unified_response(cnt, state)
                    if hr := validate_citations_in_response(disp, kb_ctx, state):
                        state["hallucination_check_result"] = hr.to_dict()
                    llm["response"] = {"content": disp} if not isinstance(rsp, dict) else {**rsp, "content": disp}
                    mirror(state, "llm_response", llm["response"])
                    state.setdefault("messages", []).append({"role": "assistant", "content": disp})
        else:
            llm.setdefault("success", False)

        _merge(llm, res.get("llm_extra", {}))
        _merge(state.setdefault("decisions", {}), res.get("decisions", {}))
        for k in ("tokens_used", "cost_estimate"):
            if res.get(k):
                llm[k] = res[k]
        if res.get("model"):
            llm["model_used"] = state["model_used"] = res["model"]

    if state.get("reasoning_trace"):
        log_reasoning_trace_recorded(state, elapsed_ms=(time.perf_counter() - t0) * 1000)
    rag_step_log(STEP, "exit", llm_success=llm.get("success"), reasoning_type=state.get("reasoning_type"))
    return state
