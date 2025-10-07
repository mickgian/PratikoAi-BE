"""Node wrapper for Step 8: Init Agent."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import response as orchestrators

STEP = 8


async def node_step_8(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 8: Initialize Workflow.

    Delegates to the orchestrator and initializes the agent workflow.
    """
    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = await orchestrators.step_8__init_agent(ctx=dict(state), messages=state.get("messages"))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            if "agent_initialized" in result:
                state["agent_initialized"] = bool(result["agent_initialized"])
            if "workflow_ready" in result:
                state["workflow_ready"] = bool(result["workflow_ready"])

        rag_types.rag_step_log(STEP, "exit", agent_initialized=state.get("agent_initialized"))

    return state
