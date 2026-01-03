"""Source Hierarchy Service for Italian Legal Sources (DEV-227).

This module provides hierarchical weighting for Italian legal source types,
used by the Tree of Thoughts reasoner and other components that need to
evaluate source authority.

Italian Legal Source Hierarchy:
- Level 1 (Primary): Legge, Decreto Legislativo, DPR, Decreto Legge
- Level 2 (Secondary): Decreto Ministeriale, Regolamento UE
- Level 3 (Administrative): Circolare, Risoluzione, Provvedimento
- Level 4 (Interpretations): Interpello, FAQ
- Level 5 (Case Law): Cassazione, Corte Costituzionale, CGUE, CTP/CTR
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# =============================================================================
# Module-level singleton
# =============================================================================
_source_hierarchy_instance: SourceHierarchy | None = None


# =============================================================================
# Level Name Constants
# =============================================================================
LEVEL_NAMES = {
    1: "primary",
    2: "secondary",
    3: "administrative",
    4: "interpretation",
    5: "case_law",
    99: "unknown",
}


# =============================================================================
# Source Type Definitions
# =============================================================================

# Level 1 - Primary Sources (weight: 1.0)
LEVEL_1_TYPES = {
    "legge",
    "decreto_legislativo",
    "dpr",
    "decreto_legge",
    # Abbreviations
    "d.lgs",
    "d.lgs.",
    "d.l",
    "d.l.",
    "d.p.r",
    "d.p.r.",
}

# Level 2 - Secondary Sources (weight: 0.8)
LEVEL_2_TYPES = {
    "decreto_ministeriale",
    "regolamento_ue",
    # Abbreviations
    "d.m",
    "d.m.",
}

# Level 3 - Administrative Practice (weight: 0.6)
LEVEL_3_TYPES = {
    "circolare",
    "risoluzione",
    "provvedimento",
}

# Level 4 - Interpretations (weight: 0.4)
LEVEL_4_TYPES = {
    "interpello",
    "faq",
}

# Level 5 - Case Law (variable weight - stored separately)
LEVEL_5_TYPES = {
    "cassazione",
    "corte_costituzionale",
    "cgue",
    "ctp_ctr",
}


# =============================================================================
# Source Hierarchy Class
# =============================================================================


class SourceHierarchy:
    """Service for Italian legal source hierarchy weighting.

    Provides methods to:
    - Get weight for any source type (0.0 to 1.0)
    - Get hierarchy level (1-5, or 99 for unknown)
    - Compare source authority
    - List types at each level
    - Calculate weighted scores for source lists

    Example:
        >>> hierarchy = SourceHierarchy()
        >>> hierarchy.get_weight("legge")
        1.0
        >>> hierarchy.get_weight("circolare")
        0.6
        >>> hierarchy.compare_sources("legge", "circolare")
        1  # legge is higher authority
    """

    # Full weight mapping for all known source types
    WEIGHTS: dict[str, float] = {
        # Level 1 - Primary Sources (weight: 1.0)
        "legge": 1.0,
        "decreto_legislativo": 1.0,
        "dpr": 1.0,
        "decreto_legge": 1.0,
        "d.lgs": 1.0,
        "d.lgs.": 1.0,
        "d.l": 1.0,
        "d.l.": 1.0,
        "d.p.r": 1.0,
        "d.p.r.": 1.0,
        # Level 2 - Secondary Sources (weight: 0.8)
        "decreto_ministeriale": 0.8,
        "regolamento_ue": 0.8,
        "d.m": 0.8,
        "d.m.": 0.8,
        # Level 3 - Administrative Practice (weight: 0.6)
        "circolare": 0.6,
        "risoluzione": 0.6,
        "provvedimento": 0.6,
        # Level 4 - Interpretations (weight: 0.4)
        "interpello": 0.4,
        "faq": 0.4,
        # Level 5 - Case Law (variable weight)
        "cassazione": 0.9,
        "corte_costituzionale": 1.0,
        "cgue": 0.95,
        "ctp_ctr": 0.5,
        # Default for soft/generic sources
        "prassi": 0.3,
    }

    # Default weight for unknown source types
    DEFAULT_WEIGHT: float = 0.5

    def get_weight(self, source_type: str) -> float:
        """Get weight for a source type.

        Args:
            source_type: Type of legal source (e.g., "legge", "circolare").
                        Case insensitive.

        Returns:
            Weight between 0.0 and 1.0. Unknown types return 0.5.

        Example:
            >>> hierarchy = SourceHierarchy()
            >>> hierarchy.get_weight("legge")
            1.0
            >>> hierarchy.get_weight("unknown_type")
            0.5
        """
        normalized = self.normalize_type(source_type)
        return self.WEIGHTS.get(normalized, self.DEFAULT_WEIGHT)

    def get_level(self, source_type: str) -> int:
        """Get hierarchy level for a source type.

        Args:
            source_type: Type of legal source. Case insensitive.

        Returns:
            Level 1-5 for known types, 99 for unknown.
            Lower numbers indicate higher authority.

        Example:
            >>> hierarchy = SourceHierarchy()
            >>> hierarchy.get_level("legge")
            1
            >>> hierarchy.get_level("circolare")
            3
        """
        normalized = self.normalize_type(source_type)

        if normalized in LEVEL_1_TYPES:
            return 1
        elif normalized in LEVEL_2_TYPES:
            return 2
        elif normalized in LEVEL_3_TYPES:
            return 3
        elif normalized in LEVEL_4_TYPES:
            return 4
        elif normalized in LEVEL_5_TYPES:
            return 5
        else:
            return 99

    def normalize_type(self, source_type: str) -> str:
        """Normalize a source type string.

        Args:
            source_type: Source type to normalize.

        Returns:
            Normalized source type (lowercase, stripped whitespace).

        Example:
            >>> hierarchy = SourceHierarchy()
            >>> hierarchy.normalize_type("  LEGGE  ")
            'legge'
        """
        return source_type.strip().lower()

    def compare_sources(self, source1: str, source2: str) -> int:
        """Compare two sources by authority level.

        Args:
            source1: First source type.
            source2: Second source type.

        Returns:
            Positive if source1 has higher authority (lower level number).
            Negative if source1 has lower authority.
            Zero if same authority level.

        Example:
            >>> hierarchy = SourceHierarchy()
            >>> hierarchy.compare_sources("legge", "circolare")
            1  # legge is higher authority
            >>> hierarchy.compare_sources("circolare", "legge")
            -1  # circolare is lower authority
        """
        level1 = self.get_level(source1)
        level2 = self.get_level(source2)

        if level1 < level2:
            return 1  # source1 has higher authority (lower level)
        elif level1 > level2:
            return -1  # source1 has lower authority (higher level)
        else:
            return 0  # same level

    def get_all_types(self) -> list[str]:
        """Get all known source types.

        Returns:
            List of all source types (excluding abbreviation variants).

        Example:
            >>> hierarchy = SourceHierarchy()
            >>> "legge" in hierarchy.get_all_types()
            True
        """
        # Return canonical types (not abbreviations)
        canonical_types = [
            # Level 1
            "legge",
            "decreto_legislativo",
            "dpr",
            "decreto_legge",
            # Level 2
            "decreto_ministeriale",
            "regolamento_ue",
            # Level 3
            "circolare",
            "risoluzione",
            "provvedimento",
            # Level 4
            "interpello",
            "faq",
            # Level 5
            "cassazione",
            "corte_costituzionale",
            "cgue",
            "ctp_ctr",
        ]
        return canonical_types

    def get_types_at_level(self, level: int) -> list[str]:
        """Get all source types at a specific hierarchy level.

        Args:
            level: Hierarchy level (1-5).

        Returns:
            List of canonical source types at that level.

        Example:
            >>> hierarchy = SourceHierarchy()
            >>> hierarchy.get_types_at_level(1)
            ['legge', 'decreto_legislativo', 'dpr', 'decreto_legge']
        """
        level_map = {
            1: ["legge", "decreto_legislativo", "dpr", "decreto_legge"],
            2: ["decreto_ministeriale", "regolamento_ue"],
            3: ["circolare", "risoluzione", "provvedimento"],
            4: ["interpello", "faq"],
            5: ["cassazione", "corte_costituzionale", "cgue", "ctp_ctr"],
        }
        return level_map.get(level, [])

    def get_source_info(self, source_type: str) -> dict:
        """Get detailed information about a source type.

        Args:
            source_type: Type of legal source.

        Returns:
            Dictionary with type, weight, level, and level_name.

        Example:
            >>> hierarchy = SourceHierarchy()
            >>> info = hierarchy.get_source_info("legge")
            >>> info["level_name"]
            'primary'
        """
        normalized = self.normalize_type(source_type)
        level = self.get_level(source_type)
        weight = self.get_weight(source_type)
        level_name = LEVEL_NAMES.get(level, "unknown")

        return {
            "type": normalized,
            "weight": weight,
            "level": level,
            "level_name": level_name,
        }

    def calculate_source_score(self, sources: list[dict]) -> float:
        """Calculate weighted score for a list of sources.

        Args:
            sources: List of source dictionaries with 'type' field.

        Returns:
            Average weight of all sources. Returns 0.0 for empty list.

        Example:
            >>> hierarchy = SourceHierarchy()
            >>> sources = [{"type": "legge"}, {"type": "circolare"}]
            >>> hierarchy.calculate_source_score(sources)
            0.8  # Average of 1.0 and 0.6
        """
        if not sources:
            return 0.0

        total_weight = 0.0
        for source in sources:
            source_type = source.get("type", "unknown")
            total_weight += self.get_weight(source_type)

        return total_weight / len(sources)


# =============================================================================
# Factory Function
# =============================================================================


def get_source_hierarchy() -> SourceHierarchy:
    """Get or create SourceHierarchy singleton instance.

    Returns:
        SourceHierarchy instance.

    Example:
        >>> hierarchy = get_source_hierarchy()
        >>> hierarchy.get_weight("legge")
        1.0
    """
    global _source_hierarchy_instance
    if _source_hierarchy_instance is None:
        _source_hierarchy_instance = SourceHierarchy()
    return _source_hierarchy_instance
