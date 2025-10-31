"""Prompt policy for tool usage in RAG system.

This module defines the policy text that explains to the LLM when and how
to use tools, ensuring policy-gated autonomy.
"""

# Policy text to be included in system prompts (S041)
TOOL_USAGE_POLICY = """
## Politica di utilizzo degli strumenti

Decidi quando usare gli strumenti disponibili:

**Quando USARE gli strumenti (KnowledgeSearchTool, CCNLTool, FAQTool):**
- La risposta richiede fonti normative aggiornate (CCNL, circolari, leggi, decreti)
- Sono menzionate istituzioni o enti ufficiali (Agenzia Entrate, INPS, MEF, INAIL, Gazzetta Ufficiale)
- La query contiene riferimenti a articoli di legge o contratti collettivi
- È richiesto un aggiornamento recente o una data specifica (es. "requisiti 2024")
- È necessario citare fonti primarie per garantire accuratezza

**Quando NON usare strumenti:**
- Operazioni aritmetiche semplici (calcoli, somme, percentuali)
- Definizioni generali o concetti di base già noti
- Ragionamenti che non richiedono fonti esterne
- Conversazioni informali o richieste di chiarimento

**Vincoli importanti:**
- **Massimo 1 strumento per turno** - scegli lo strumento più appropriato
- **Non ripetere chiamate identiche** - se uno strumento è già stato invocato con gli stessi parametri, non richiamarlo
- **Cita sempre le fonti** - quando usi uno strumento, sintetizza i risultati citando le fonti (articoli, circolari, CCNL, etc.)

Segui questa politica rigorosamente per garantire risposte accurate ed efficienti.
"""

# Shorter version for context-limited scenarios
TOOL_USAGE_POLICY_SHORT = """
Usa strumenti solo per query normative/regolamentari con fonti ufficiali.
Max 1 strumento/turno. Cita fonti quando usi strumenti.
"""


def get_tool_policy(short: bool = False) -> str:
    """Get the tool usage policy text.

    Args:
        short: If True, return the short version for context-limited scenarios

    Returns:
        Policy text to append to system prompts
    """
    return TOOL_USAGE_POLICY_SHORT if short else TOOL_USAGE_POLICY


def should_allow_tools(needs_retrieval: bool) -> bool:
    """Determine if tools should be allowed based on retrieval gate.

    This implements the policy decision: if the retrieval gate says no retrieval
    is needed, then tools should be disabled (tool_choice="none").

    Args:
        needs_retrieval: Result from retrieval gate (S034a)

    Returns:
        True if tools should be allowed, False if tool_choice should be "none"
    """
    return needs_retrieval
