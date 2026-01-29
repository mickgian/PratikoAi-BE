"""KB empty detection and warning injection.

Detects when KB returns empty/irrelevant results and injects warnings
to prevent LLM hallucinations.
"""

from typing import Any

from app.core.logging import logger

# Type alias for RAG state dict
RAGStateDict = dict[str, Any]


def check_kb_empty_and_inject_warning(state: RAGStateDict) -> bool:
    """Check if KB returned empty/irrelevant results and inject warning.

    DEV-242: When KB returns no relevant documents, the LLM tends to hallucinate
    from training data. This check detects empty KB and injects a strong warning
    into the context to force the LLM to respond with "Non ho trovato".

    Args:
        state: RAG state with kb_sources_metadata

    Returns:
        True if KB is empty/irrelevant and warning was injected
    """
    kb_sources = state.get("kb_sources_metadata", [])
    # DEV-242 Phase 10: Read from "context" key (where Step 40 stores KB)
    # Fall back to "kb_context" for backward compatibility
    kb_context = state.get("context", "") or state.get("kb_context", "")

    # Check if KB is empty
    is_kb_empty = len(kb_sources) == 0

    # Check if KB context is too short (just headers/navigation)
    is_kb_context_minimal = len(kb_context.strip()) < 200

    # If KB has sources but context is minimal, treat as effectively empty
    kb_effectively_empty = is_kb_empty or (is_kb_context_minimal and len(kb_sources) <= 1)

    if kb_effectively_empty:
        # Extract user query for logging
        user_message = state.get("user_message", "")
        if not user_message:
            messages = state.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break

        # DEV-242: Inject critical KB-empty warning by prepending to kb_context
        # This ensures the warning flows through the existing prompt system
        kb_empty_warning = """
⚠️⚠️⚠️ ATTENZIONE CRITICA - KNOWLEDGE BASE VUOTA ⚠️⚠️⚠️

La Knowledge Base NON ha restituito documenti rilevanti per questa query.

REGOLE OBBLIGATORIE CHE DEVI SEGUIRE:
1. NON inventare NESSUNA informazione, data, articolo di legge o riferimento normativo
2. NON usare conoscenze di training per rispondere su questo argomento
3. RISPONDI SOLO con: "Non ho trovato documenti ufficiali su [argomento della query] nel database di PratikoAI."
4. Puoi suggerire all'utente di riformulare la domanda con termini diversi

⛔ RISPOSTA VIETATA: Inventare date, scadenze, o dettagli normativi non presenti nel contesto.

--- FINE AVVERTIMENTO KB VUOTA ---

"""
        # Prepend warning to kb_context
        state["kb_context"] = kb_empty_warning + (kb_context or "Nessun documento trovato.")
        state["kb_empty_warning"] = kb_empty_warning  # Also store for logging

        # DEV-242 Phase 10: DO NOT overwrite state["context"] - it contains good KB chunks!
        # The warning is stored in kb_context and kb_empty_warning for logging purposes only.
        # Overwriting context destroys the KB retrieval results that Step 40 built.

        logger.warning(
            "step64_kb_empty_warning_injected",
            is_kb_empty=is_kb_empty,
            is_kb_context_minimal=is_kb_context_minimal,
            kb_sources_count=len(kb_sources),
            kb_context_length=len(kb_context),
            user_query=user_message[:100] if user_message else "",
            request_id=state.get("request_id"),
        )

        return True

    return False
