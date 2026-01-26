"""Result formatting for web verification.

Handles caveat generation and deduplication.
"""

from .constants import MIN_CAVEAT_CONFIDENCE
from .types import ContradictionInfo


class CaveatFormatter:
    """Formats and deduplicates caveats from contradictions."""

    def deduplicate_and_format_caveats(self, contradictions: list[ContradictionInfo]) -> list[str]:
        """Group contradictions by type and merge sources into deduplicated caveats.

        Args:
            contradictions: List of ContradictionInfo objects

        Returns:
            List of deduplicated caveat strings with merged source links
        """
        # Group by caveat type
        by_type: dict[str, list[ContradictionInfo]] = {}
        for c in contradictions:
            caveat_type = self._get_caveat_type(c)
            if caveat_type:
                by_type.setdefault(caveat_type, []).append(c)

        # Build deduplicated caveats with merged sources
        caveats = []
        for caveat_type, items in by_type.items():
            # Build source links - use markdown link format [title](url)
            # Frontend renders markdown, so this will be clickable
            source_links = []
            for item in items:
                if item.source_url and item.source_title:
                    # Use short title (first 40 chars) to keep it readable
                    short_title = item.source_title[:40] + "..." if len(item.source_title) > 40 else item.source_title
                    source_links.append(f"[{short_title}]({item.source_url})")
                elif item.source_url:
                    source_links.append(f"[\U0001f517]({item.source_url})")

            # Join sources with comma for readability
            sources_str = ", ".join(source_links) if source_links else ""

            # Get caveat text using first item's topic for context
            caveat_text = self._get_caveat_text(caveat_type, items[0].topic)

            # Combine caveat text with sources
            if sources_str:
                caveats.append(f"\U0001f4cc {caveat_text} Fonti: {sources_str}")
            else:
                caveats.append(f"\U0001f4cc {caveat_text}")

        return caveats

    def _get_caveat_type(self, contradiction: ContradictionInfo) -> str | None:
        """Get caveat type for a contradiction.

        Returns:
            Caveat type string or None if confidence too low
        """
        if contradiction.confidence < MIN_CAVEAT_CONFIDENCE:
            return None

        topic_lower = contradiction.topic.lower()

        if "scadenza" in topic_lower or "data" in topic_lower:
            return "scadenza"

        if any(t in topic_lower for t in ["tributi locali", "imu", "tasi", "tasse auto", "bollo"]):
            return "tributi_locali"

        if "irap" in topic_lower:
            return "irap"

        return "generic"

    def _get_caveat_text(self, caveat_type: str, topic: str) -> str:
        """Get caveat text without source links.

        Args:
            caveat_type: Type of caveat (scadenza, tributi_locali, irap, generic)
            topic: Original topic for context

        Returns:
            Caveat text string
        """
        if caveat_type == "scadenza":
            return (
                "**Nota sulla scadenza:** Fonti recenti indicano possibili aggiornamenti "
                "alle date. Verifica le scadenze ufficiali prima di procedere."
            )

        if caveat_type == "tributi_locali":
            return (
                f"**Nota sui tributi locali:** La definizione agevolata per tributi locali "
                f"come {topic} potrebbe richiedere l'accordo dell'ente locale competente. "
                f"Verifica con il tuo Comune/Regione."
            )

        if caveat_type == "irap":
            return (
                "**Nota sull'IRAP:** Potrebbero esserci distinzioni tra IRAP da dichiarazione "
                "e IRAP da accertamento. Verifica i criteri di ammissibilit\u00e0 specifici."
            )

        # Generic
        return (
            "**Nota:** Fonti recenti suggeriscono informazioni aggiuntive su questo argomento. "
            "Verifica con fonti ufficiali per i dettagli pi\u00f9 aggiornati."
        )

    def generate_caveat(self, contradiction: ContradictionInfo) -> str | None:
        """Generate a caveat message for a contradiction (legacy method).

        Note: This method is kept for backwards compatibility.
        New code should use deduplicate_and_format_caveats() instead.

        Args:
            contradiction: ContradictionInfo to generate caveat for

        Returns:
            Caveat string or None if confidence too low
        """
        caveat_type = self._get_caveat_type(contradiction)
        if not caveat_type:
            return None

        caveat_text = self._get_caveat_text(caveat_type, contradiction.topic)

        # Add source link
        if contradiction.source_url:
            return f"\U0001f4cc {caveat_text} [\U0001f517]({contradiction.source_url})"
        else:
            return f"\U0001f4cc {caveat_text} [Fonte: {contradiction.source_title}]"


# Singleton instance
caveat_formatter = CaveatFormatter()
