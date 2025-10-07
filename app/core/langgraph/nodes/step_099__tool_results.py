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
        # Call orchestrator
        result = await step_99__tool_results(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Mark tool processing as complete
        if "tools" not in state:
            state["tools"] = {}
        state["tools"]["results_processed"] = True

        # Aggregate results for response path
        tool_results = []
        if "kb_results" in state.get("tools", {}):
            tool_results.append(state["tools"]["kb_results"])
        if "ccnl_results" in state.get("tools", {}):
            tool_results.append(state["tools"]["ccnl_results"])
        if "doc_results" in state.get("tools", {}):
            tool_results.append(state["tools"]["doc_results"])
        if "faq_results" in state.get("tools", {}):
            tool_results.append(state["tools"]["faq_results"])

        state["tools"]["results"] = tool_results

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state