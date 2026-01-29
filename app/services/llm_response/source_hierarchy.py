"""Source hierarchy ranking for Italian legal documents.

Applies hierarchy ranks to sources based on their legal authority level.
"""

from .constants import SOURCE_HIERARCHY


def apply_source_hierarchy(sources: list[dict]) -> list[dict]:
    """Sort sources by Italian legal hierarchy and add hierarchy_rank.

    DEV-214: Italian legal source hierarchy (highest to lowest authority):
    1. Legge (L., Legge)
    2. Decreto (D.Lgs., DPR, Decreto)
    3. Circolare (Circolare AdE)
    4. Interpello (Interpello, Risposta)
    5. Other/Unknown

    Args:
        sources: List of source dicts from LLM response

    Returns:
        Sorted sources with hierarchy_rank added, highest authority first
    """
    if not sources:
        return []

    for source in sources:
        ref = source.get("ref", "").lower()

        # Determine hierarchy rank based on reference text
        if "legge" in ref or ref.startswith("l.") or " l. " in ref:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["legge"]
        elif any(term in ref for term in ["decreto", "d.lgs", "dpr", "d.l."]):
            source["hierarchy_rank"] = SOURCE_HIERARCHY["decreto"]
        elif "circolare" in ref:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["circolare"]
        elif any(term in ref for term in ["interpello", "risposta"]):
            source["hierarchy_rank"] = SOURCE_HIERARCHY["interpello"]
        elif any(term in ref for term in ["prassi", "risoluzione"]):
            source["hierarchy_rank"] = SOURCE_HIERARCHY["prassi"]
        else:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["unknown"]

    # Sort by hierarchy rank (lowest number = highest authority)
    return sorted(sources, key=lambda s: s.get("hierarchy_rank", 99))
