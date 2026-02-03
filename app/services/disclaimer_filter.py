"""DEV-245 Phase 5.1: Post-LLM disclaimer filtering.

Removes prohibited disclaimer phrases that damage PratikoAI's reputation
as an authoritative fiscal assistant.

The user IS the "esperto fiscale" using our tool. Telling them to "consult an expert"
is both unhelpful and damages our brand as a trusted AI assistant.

Industry best practice: Output filtering with regex/pattern matching as a safety net
when prompt instructions are ignored by the LLM.

DEV-251: Fixed to remove only the disclaimer phrase, not entire sentences.
This prevents excessive content removal that was causing 2000+ char responses
to be truncated to 300-400 chars.
"""

import re

from app.core.logging import logger

# Patterns that match prohibited disclaimer phrases in Italian
# DEV-251: Patterns now remove only the matched phrase, not the entire sentence
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
_COMPILED_PATTERNS: list[re.Pattern[str]] = [re.compile(pattern, re.IGNORECASE) for pattern in DISCLAIMER_PATTERNS]


class DisclaimerFilter:
    """Filters LLM responses to remove unauthorized disclaimers.

    This is a safety net for when the LLM ignores prompt instructions
    that prohibit suggesting users "consult an expert".
    """

    @staticmethod
    def filter_response(response_text: str) -> tuple[str, list[str]]:
        """Remove disclaimer phrases from LLM response.

        DEV-251: Changed to remove only the matched phrase, not the entire sentence.
        This preserves sentence structure while removing just the problematic content.

        Args:
            response_text: The raw LLM response text

        Returns:
            tuple: (cleaned_text, list_of_removed_phrases)
                - cleaned_text: Response with disclaimers removed
                - removed_phrases: List of matched patterns for logging
        """
        if not response_text:
            return "", []

        original_length = len(response_text)
        removed: list[str] = []
        cleaned = response_text

        for pattern in _COMPILED_PATTERNS:
            # Find all matches for this pattern
            match = pattern.search(cleaned)
            while match:
                matched_text = match.group(0)
                logger.debug(
                    "disclaimer_phrase_matched",
                    pattern=pattern.pattern,
                    matched_text=matched_text,
                    position=match.start(),
                )
                removed.append(matched_text)

                # DEV-251: Remove only the matched phrase, not the entire sentence
                # This preserves the sentence structure while removing the disclaimer
                cleaned = pattern.sub("", cleaned, count=1)

                # Check for more matches of this pattern
                match = pattern.search(cleaned)

        # Clean up artifacts left by phrase removal
        # Remove leading punctuation/connectors that now start a sentence
        cleaned = re.sub(r"([.!?]\s*)[,;:]\s*", r"\1", cleaned)
        # Remove double punctuation
        cleaned = re.sub(r"([.!?])\s*[.!?]", r"\1", cleaned)
        # Remove orphaned standalone connectors at end of sentences (with word boundaries)
        # \b ensures we match whole words only, not "e" at end of "richieste"
        cleaned = re.sub(r",?\s+\b(per|o|e)\b\s*[.!?]", ".", cleaned)
        # Clean up any double spaces or trailing whitespace
        # DEV-250: Only collapse multiple spaces, preserve newlines for markdown formatting
        cleaned = re.sub(r" {2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        # DEV-251: Log length change for debugging content loss issues
        cleaned_length = len(cleaned)
        chars_removed = original_length - cleaned_length

        if removed:
            logger.info(
                "disclaimer_filter_applied",
                original_length=original_length,
                cleaned_length=cleaned_length,
                chars_removed=chars_removed,
                removal_percentage=round((chars_removed / original_length) * 100, 1) if original_length > 0 else 0,
                phrases_removed=removed[:5],  # Log first 5 for brevity
            )

            # DEV-251: Warn if excessive content removal detected
            if original_length > 0 and chars_removed > original_length * 0.5:
                logger.warning(
                    "disclaimer_filter_excessive_removal",
                    original_length=original_length,
                    cleaned_length=cleaned_length,
                    chars_removed=chars_removed,
                    removal_percentage=round((chars_removed / original_length) * 100, 1),
                    phrases_removed=removed,
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
