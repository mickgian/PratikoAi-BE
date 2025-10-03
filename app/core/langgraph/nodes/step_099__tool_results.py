"""Node wrapper for Step 99: Tool Results."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.platform import step_99__tool_results

STEP = 99


async def node_step_99(state: RAGState) -> RAGState:
    """Node wrapper for Step 99: Process and aggregate tool results."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_99__tool_results(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Mark tool processing as complete
        if "tools" not in new_state:
            new_state["tools"] = {}
        new_state["tools"]["results_processed"] = True

        # Aggregate results for response path
        tool_results = []
        if "kb_results" in new_state.get("tools", {}):
            tool_results.append(new_state["tools"]["kb_results"])
        if "ccnl_results" in new_state.get("tools", {}):
            tool_results.append(new_state["tools"]["ccnl_results"])
        if "doc_results" in new_state.get("tools", {}):
            tool_results.append(new_state["tools"]["doc_results"])
        if "faq_results" in new_state.get("tools", {}):
            tool_results.append(new_state["tools"]["faq_results"])

        new_state["tools"]["results"] = tool_results

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state