"""Node wrapper for Step 1: Validate Request."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import platform as orchestrators

STEP = 1


async def node_step_1(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 1: Validate request and authenticate.

    Delegates to the orchestrator and updates state with validation results.
    """
    decisions = state.setdefault("decisions", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = await orchestrators.step_1__validate_request(ctx=dict(state), messages=state.get("messages"))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            # Copy validation results into decisions
            if "request_valid" in result:
                decisions["request_valid"] = bool(result["request_valid"])
            if "validation_successful" in result:
                decisions["validation_successful"] = bool(result["validation_successful"])
            if "authentication_successful" in result:
                decisions["authentication_successful"] = bool(result["authentication_successful"])

            # Copy session and user info if present
            if "session" in result:
                state["session"] = result["session"]
            if "user" in result:
                state["user"] = result["user"]
            if "validated_request" in result:
                state["validated_request"] = result["validated_request"]

        rag_types.rag_step_log(STEP, "exit", decisions=decisions, request_valid=decisions.get("request_valid"))

    return state
