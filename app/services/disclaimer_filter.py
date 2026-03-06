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
# Shared professional role alternation — used across multiple patterns.
# IMPORTANT: when adding a new role, add it HERE so all patterns are updated.
_ROLES = r"(?:esperto|professionista|commercialista|consulente|avvocato|legale)"

DISCLAIMER_PATTERNS: list[str] = [
    # "consult an expert" variants — broad catch for any verb + professional role
    # Extended with [^.!?\n]* to remove the full clause through the professional reference
    rf"consult(?:a(?:re|ndo)?|i|o) (?:un |il )?{_ROLES}[^.!?\n]*",
    rf"rivolg[aei]r?[st]?i a (?:un |il )?{_ROLES}[^.!?\n]*",
    r"(?:è|e') consigliabile consultare[^.!?\n]*",
    r"si consiglia di consultare[^.!?\n]*",
    r"verifica (?:con|presso) (?:un professionista|fonti ufficiali)[^.!?\n]*",
    # "you should consult" variants (dovresti/dovrebbe/è opportuno/sarebbe bene)
    # Extended to eat the full clause including the target professional
    r"(?:dovresti|dovrebbe|dovrebbero) (?:consultare|contattare|rivolgersi)[^.!?\n]*",
    r"(?:è|e') (?:opportuno|consigliabile|bene|utile) (?:consultare|contattare|rivolgersi)[^.!?\n]*",
    r"(?:sarebbe|potrebbe essere) (?:bene|opportuno|utile) (?:consultare|contattare)[^.!?\n]*",
    # "I recommend consulting" personal/impersonal variants
    r"(?:ti |vi )?(?:consiglio|suggerisco|raccomando) di (?:consultare|contattare|rivolgerti|rivolgervi)[^.!?\n]*",
    # Compound professional references with "o" (un commercialista o un consulente del lavoro)
    r"un (?:commercialista|consulente del lavoro|avvocato|esperto|professionista|legale)"
    r"(?:\s*o\s*(?:un )?(?:commercialista|consulente del lavoro|avvocato|esperto|professionista|legale))+",
    # "è possibile approfondire con un professionista" variants (MUST be before "assistenza" pattern)
    # Fixed: use non-greedy *? to avoid eating entire clauses
    r"(?:è|e') possibile approfondire (?:ulteriormente )?(?:con\b[^.!?\n]*?)?",
    # "professional assistance" full phrases
    r"(?:con (?:l[''])?)?assistenza (?:di un )?(?:professionista|professionale|legale|fiscale|contabile)",
    r"(?:chiedere|sentire|prendere) (?:il )?(?:parere|consiglio|opinione) (?:di|a) un",
    rf"(?:contattare|interpellare) un {_ROLES}[^.!?\n]*",
    # "consulenza di un professionista" (noun form, bypasses verb-based patterns)
    rf"(?:si consiglia )?la consulenza di un {_ROLES}",
    # "verificare con un professionista" (imperative without "consult")
    rf"verificare con un {_ROLES}[^.!?\n]*",
    # "In case of doubt" + consult (or orphaned after earlier pattern removal)
    # Fixed: use non-greedy *? to avoid eating entire clauses
    r"[Ii]n caso di dubbi,?\s*(?:(?:consultare|contattare|rivolgersi)[^.!?\n]*?)?",
    # "check official sources" variants
    r"verifica sul sito (?:ufficiale|dell['']Agenzia)",
    r"per (?:maggiori informazioni|conferma)[,]? (?:consulta|verifica|controlla)",
    r"per una conferma definitiva",
    # "contact me" variants (inappropriate for AI)
    r"non esit[ai]r?e? a contattarmi",
    r"se (?:hai|avete) (?:domande|dubbi)",
    r"resto a disposizione",
    # Standalone catch-all: "a un professionista abilitato" (orphaned after verb removal
    # or when the verb and professional are in different streaming segments)
    rf",?\s*a un {_ROLES} abilitato[^.!?\n]*",
    # Broader catch-all: "professionista abilitato" without preceding article
    r"(?:professionista|commercialista|consulente|esperto) abilitato[^.!?\n]*",
    # "valutare/richiedere/ottenere una consulenza legale" (action verb + consulenza)
    # Catches borderline phrases like "valutare una consulenza legale mirata" while
    # preserving factual references like "il costo della consulenza legale"
    r"(?:valutare|richiedere|ottenere|chiedere|prendere in considerazione|considerare|prevedere)"
    r" (?:una |la )?consulenza (?:legale|fiscale|professionale|specialistica|specializzata)[^.!?\n]*",
    # --- Internal methodology leak: Tree of Thoughts ---
    # The LLM sometimes ignores prompt instructions and exposes the internal
    # reasoning methodology name or structure in user-facing text.
    r",?\s*applicando il metodo Tree of Thoughts[^.!?\n]*",
    r",?\s*(?:utilizzando|usando|con) (?:il metodo|la metodologia) Tree of Thoughts[^.!?\n]*",
    r",?\s*(?:attraverso|tramite|mediante) (?:il )?(?:metodo |metodologia )?Tree of Thoughts[^.!?\n]*",
    # ToT structural leaks: methodology terminology that exposes the reasoning process
    # "generando multiple ipotesi interpretative" / "multi-ipotesi"
    r",?\s*generando multiple ipotesi interpretative[^.!?\n]*",
    r"(?:analisi |approccio )?multi-ipotesi[^.!?\n]*",
    # "metodo di ragionamento" (generic methodology reference forbidden by prompt)
    r"(?:un |il )?metodo di ragionamento[^.!?\n]*",
    # "Valutazione delle Ipotesi" as section header (ToT evaluation step)
    r"#*\s*\d*\.?\s*Valutazione delle Ipotesi[^.!?\n]*",
    # "Ipotesi N:" numbered headers (ToT hypothesis labeling)
    # Only matches "Ipotesi" followed by a number and colon — not "nell'ipotesi di" (legal usage)
    r"#*\s*Ipotesi \d+\s*:[^\n]*",
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
