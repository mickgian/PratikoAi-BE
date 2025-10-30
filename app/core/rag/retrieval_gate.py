"""Retrieval pre-gate for policy-gated autonomy.

This module provides a lightweight gate (S034a in the FSM) that decides
whether a query needs retrieval and tool calls based on pattern matching.

The gate returns True when the query likely needs external sources
(regulatory info, time-sensitive data, citations) and False for basic
reasoning that can be answered without retrieval.
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class GateDecision:
    """Decision from the retrieval gate.

    Attributes:
        needs_retrieval: True if query requires retrieval/tools, False otherwise
        reasons: List of pattern matches or reasoning for the decision
    """
    needs_retrieval: bool
    reasons: List[str]


# Patterns indicating time-sensitive or regulatory queries that need sources
TIME_SENSITIVE_HINTS = [
    r"\b20(2\d|3\d)\b",  # years like 2024, 2025, 2026+
    r"\baggiorn(ato|amenti|ata|ate)\b",  # aggiornato, aggiornamenti
    r"\bultim[ioe]\b",  # ultimo, ultime
    r"\bnovit[aà]\b",  # novità
    r"\bdecorrenza\b",  # effective date
    r"\bart\.\s*\d+",  # article references (art. 18)
    r"\bCCNL\b",  # Collective labor contracts
    r"\bGazzetta\b|\bG\.U\.\b",  # Official gazette
    r"\bINPS\b|\bAgenzia\s+Entrate\b|\bMEF\b|\bINAIL\b",  # Institutions
    r"\bcircolare\b|\brisoluzione\b",  # Official communications
    r"\bnormativ[aeo]\b",  # normativa, normativo
    r"\blegge\b|\bdecreto\b|\bD\.L\.\b|\bD\.Lgs\.\b",  # Laws and decrees
    r"\bcontratto\b.*\b(lavoro|collettiv[io])\b",  # labor contracts
    r"\baliquot[ae]\b",  # tax rates
    r"\bscadenz[ae]\b",  # deadlines
    r"\bregime\b.*(forfettari[io]|semplificat[io])",  # tax regimes
]

# Patterns indicating basic reasoning that doesn't need retrieval
BASIC_REASONING_HINTS = [
    r"^(\s*)\d+\s*[\+\-\*\/]\s*\d+(\s*)$",  # simple arithmetic
    r"\bcos['']?è\b|\bdefinizione\b",  # definitions
    r"\bcome\s+si\s+calcola\b",  # how to calculate (may need formula but not sources)
]


def retrieval_gate(query: str) -> GateDecision:
    """Decide if a query needs retrieval and tool calls.

    This is the S034a step in the FSM. It runs after domain classification
    (S034) and before retrieval (S039) or prompt selection (S041).

    Logic:
    1. Check for time-sensitive/regulatory hints
    2. If found, return needs_retrieval=True
    3. If not found, check for basic reasoning patterns
    4. If basic reasoning, return needs_retrieval=False
    5. Default to False (conservative - prefer fast answers)

    Args:
        query: The user's query text

    Returns:
        GateDecision with needs_retrieval bool and reasons list

    Examples:
        >>> gate = retrieval_gate("2+2")
        >>> gate.needs_retrieval
        False

        >>> gate = retrieval_gate("Quali sono i requisiti CCNL metalmeccanici 2024?")
        >>> gate.needs_retrieval
        True
    """
    if not query:
        return GateDecision(False, ["empty_query"])

    q_lower = query.lower()
    reasons = []

    # Check for time-sensitive/regulatory hints
    for pat in TIME_SENSITIVE_HINTS:
        if re.search(pat, query, flags=re.IGNORECASE):
            reasons.append(f"time_sensitive:{pat[:30]}")

    if reasons:
        return GateDecision(True, reasons)

    # Check for basic reasoning patterns
    for pat in BASIC_REASONING_HINTS:
        if re.search(pat, q_lower):
            return GateDecision(False, [f"basic_reasoning:{pat[:30]}"])

    # Default: no clear signals, prefer no retrieval for speed
    # (This is conservative - adjust if you want to allow retrieval by default)
    return GateDecision(False, ["no_time_sensitive_hints"])
