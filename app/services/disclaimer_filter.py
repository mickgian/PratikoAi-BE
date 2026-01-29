"""DEV-245 Phase 5.1: Post-LLM disclaimer filtering.

Removes prohibited disclaimer phrases that damage PratikoAI's reputation
as an authoritative fiscal assistant.

The user IS the "esperto fiscale" using our tool. Telling them to "consult an expert"
is both unhelpful and damages our brand as a trusted AI assistant.

Industry best practice: Output filtering with regex/pattern matching as a safety net
when prompt instructions are ignored by the LLM.
"""

import re

from app.core.logging import logger

# Patterns that match prohibited disclaimer phrases in Italian
# Each pattern should match a complete sentence or phrase to remove
DISCLAIMER_PATTERNS: list[str] = [
    # "consult an expert" variants
    r"consult[ai] un (esperto|professionista|commercialista|consulente)",
    r"rivolg[aei]r?[st]?i a un (esperto|professionista|commercialista)",
    r"è consigliabile consultare",
    r"si consiglia di consultare",
    r"verifica (con|presso) (un professionista|fonti ufficiali)",
    # "check official sources" variants
    r"verifica sul sito (ufficiale|dell['']Agenzia)",
    r"per (maggiori informazioni|conferma)[,]? (consulta|verifica|controlla)",
    r"per una conferma definitiva",
    # "contact me" variants (inappropriate for AI)
    r"non esit[ai]r?e? a contattarmi",
    r"se (hai|avete) (domande|dubbi)",
    r"resto a disposizione",
]

# Compile patterns for efficiency
_COMPILED_PATTERNS: list[re.Pattern] = [re.compile(pattern, re.IGNORECASE) for pattern in DISCLAIMER_PATTERNS]


class DisclaimerFilter:
    """Filters LLM responses to remove unauthorized disclaimers.

    This is a safety net for when the LLM ignores prompt instructions
    that prohibit suggesting users "consult an expert".
    """

    @staticmethod
    def filter_response(response_text: str) -> tuple[str, list[str]]:
        """Remove disclaimer phrases from LLM response.

        Finds sentences containing prohibited phrases and removes them entirely.
        This ensures clean output without awkward partial sentences.

        Args:
            response_text: The raw LLM response text

        Returns:
            tuple: (cleaned_text, list_of_removed_phrases)
                - cleaned_text: Response with disclaimers removed
                - removed_phrases: List of matched patterns for logging
        """
        if not response_text:
            return "", []

        removed: list[str] = []
        cleaned = response_text

        for pattern in _COMPILED_PATTERNS:
            # Check if pattern exists in text
            match = pattern.search(cleaned)
            if match:
                removed.append(match.group(0))

                # Remove the entire sentence containing the disclaimer
                # A sentence is bounded by . ! ? or start/end of string
                sentence_pattern = rf"[^.!?\n]*{pattern.pattern}[^.!?\n]*[.!?]?\s*"
                cleaned = re.sub(sentence_pattern, "", cleaned, flags=re.IGNORECASE)

        # Clean up any double spaces or trailing whitespace
        # DEV-250: Only collapse multiple spaces, preserve newlines for markdown formatting
        cleaned = re.sub(r" {2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        if removed:
            logger.warning(
                "disclaimer_phrases_removed",
                removed_count=len(removed),
                phrases=removed[:5],  # Log first 5 for brevity
            )

        return cleaned, removed

    @staticmethod
    def contains_disclaimer(text: str) -> bool:
        """Check if text contains any prohibited disclaimer phrases.

        Useful for quick checks without performing the full filtering.

        Args:
            text: Text to check

        Returns:
            bool: True if text contains any disclaimer phrases
        """
        if not text:
            return False

        return any(pattern.search(text) for pattern in _COMPILED_PATTERNS)


# Singleton instance for convenience
disclaimer_filter = DisclaimerFilter()
