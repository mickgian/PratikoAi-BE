"""Node wrapper for Step 57: Create Provider."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import providers as orchestrators

STEP = 57


def node_step_57(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 57: Create Provider.

    Delegates to the orchestrator and updates state with provider creation.
    """
    provider = state.setdefault("provider", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator
        result = orchestrators.step_57__create_provider(ctx=state)

        # Merge result fields into provider dict (preserving existing data)
        if isinstance(result, dict):
            if "provider_created" in result:
                provider["created"] = result["provider_created"]
            if "provider_instance" in result:
                provider["instance"] = result["provider_instance"]

        rag_types.rag_step_log(STEP, "exit", provider=provider, created=provider.get("created"))

    return state