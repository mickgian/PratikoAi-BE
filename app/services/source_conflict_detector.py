"""Source Conflict Detector Service for Italian Legal Sources (DEV-228).

This module detects conflicts between legal sources based on:
1. Hierarchy conflicts: Lower authority source contradicting higher authority
2. Temporal conflicts: Older source superseded by newer at same level

The service provides recommendations on which source to prefer and
flags conflicts by severity level.

Example:
    from app.services.source_conflict_detector import get_source_conflict_detector

    detector = get_source_conflict_detector()
    result = detector.analyze([
        {"type": "legge", "content": "Rule A", "date": "2020-01-01"},
        {"type": "circolare", "content": "Rule B", "date": "2021-01-01"},
    ])
    print(result["conflicts"])
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import structlog

from app.services.source_hierarchy import SourceHierarchy, get_source_hierarchy

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# =============================================================================
# Module-level singleton
# =============================================================================
_detector_instance: SourceConflictDetector | None = None


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SourceConflict:
    """Represents a conflict between two legal sources.

    Attributes:
        conflict_type: Type of conflict ("hierarchy" or "temporal")
        source_a: First source in the conflict
        source_b: Second source in the conflict
        preferred_source: The source that should be preferred
        severity: Conflict severity ("high", "medium", "low")
        recommendation: Italian language recommendation for resolution
    """

    conflict_type: str
    source_a: dict
    source_b: dict
    preferred_source: dict
    severity: str
    recommendation: str

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with conflict details.
        """
        return {
            "type": self.conflict_type,
            "sources": [self.source_a, self.source_b],
            "preferred_source": self.preferred_source,
            "severity": self.severity,
            "recommendation": self.recommendation,
        }


# =============================================================================
# Italian Recommendation Templates
# =============================================================================

HIERARCHY_RECOMMENDATION_TEMPLATE = (
    "La fonte {higher_type} prevale gerarchicamente sulla fonte {lower_type}. "
    "In caso di contrasto, si applica la norma di rango superiore."
)

TEMPORAL_RECOMMENDATION_TEMPLATE = (
    "La fonte più recente ({newer_date}) prevale sulla fonte precedente ({older_date}). "
    "Lex posterior derogat priori."
)

HIERARCHY_TEMPORAL_RECOMMENDATION_TEMPLATE = (
    "La fonte {higher_type} ha autorità superiore rispetto alla {lower_type}. "
    "Anche se la {lower_type} è più recente, la gerarchia normativa prevale."
)


# =============================================================================
# Source Conflict Detector Class
# =============================================================================


class SourceConflictDetector:
    """Service for detecting conflicts between Italian legal sources.

    Detects two types of conflicts:
    1. Hierarchy conflicts: When a lower-authority source contradicts a
       higher-authority source (e.g., circolare vs legge)
    2. Temporal conflicts: When an older source is superseded by a newer
       source at the same hierarchy level

    Example:
        >>> detector = SourceConflictDetector()
        >>> sources = [
        ...     {"type": "legge", "content": "IVA 22%", "date": "2020-01-01"},
        ...     {"type": "circolare", "content": "IVA 10%", "date": "2021-01-01"},
        ... ]
        >>> conflicts = detector.detect_conflicts(sources)
        >>> print(conflicts[0]["type"])
        'hierarchy'
    """

    def __init__(self, source_hierarchy: SourceHierarchy | None = None) -> None:
        """Initialize the conflict detector.

        Args:
            source_hierarchy: Optional SourceHierarchy instance for determining
                             authority levels. Uses default if not provided.
        """
        self.source_hierarchy = source_hierarchy or get_source_hierarchy()

    def detect_conflicts(self, sources: list[dict]) -> list[dict]:
        """Detect all conflicts among the provided sources.

        Args:
            sources: List of source dictionaries with 'type', 'content', and
                    optionally 'date' fields.

        Returns:
            List of conflict dictionaries with type, sources, preferred_source,
            severity, and recommendation.

        Example:
            >>> detector = SourceConflictDetector()
            >>> conflicts = detector.detect_conflicts([
            ...     {"type": "legge", "content": "A", "date": "2020-01-01"},
            ...     {"type": "circolare", "content": "B", "date": "2021-01-01"},
            ... ])
        """
        if len(sources) < 2:
            return []

        conflicts: list[SourceConflict] = []

        # Check all pairs of sources
        for i, source_a in enumerate(sources):
            for source_b in sources[i + 1 :]:
                # Check for hierarchy conflict
                hierarchy_conflict = self._detect_hierarchy_conflict(source_a, source_b)
                if hierarchy_conflict:
                    conflicts.append(hierarchy_conflict)

                # Check for temporal conflict (only same level)
                temporal_conflict = self._detect_temporal_conflict(source_a, source_b)
                if temporal_conflict:
                    conflicts.append(temporal_conflict)

        return [c.to_dict() for c in conflicts]

    def analyze(self, sources: list[dict]) -> dict[str, Any]:
        """Perform full conflict analysis on sources.

        Args:
            sources: List of source dictionaries.

        Returns:
            Analysis result with conflicts, summary, and counts.

        Example:
            >>> detector = SourceConflictDetector()
            >>> result = detector.analyze(sources)
            >>> print(result["has_conflicts"])
            True
        """
        conflicts = self.detect_conflicts(sources)

        hierarchy_count = sum(1 for c in conflicts if c["type"] == "hierarchy")
        temporal_count = sum(1 for c in conflicts if c["type"] == "temporal")

        summary = self._build_summary(conflicts)

        return {
            "conflicts": conflicts,
            "has_conflicts": len(conflicts) > 0,
            "conflict_count": len(conflicts),
            "hierarchy_conflicts": hierarchy_count,
            "temporal_conflicts": temporal_count,
            "summary": summary,
        }

    def _detect_hierarchy_conflict(self, source_a: dict, source_b: dict) -> SourceConflict | None:
        """Detect hierarchy conflict between two sources.

        A hierarchy conflict occurs when sources are at different authority
        levels in the Italian legal hierarchy.

        Args:
            source_a: First source dictionary.
            source_b: Second source dictionary.

        Returns:
            SourceConflict if conflict detected, None otherwise.
        """
        type_a = source_a.get("type", "unknown")
        type_b = source_b.get("type", "unknown")

        level_a = self.source_hierarchy.get_level(type_a)
        level_b = self.source_hierarchy.get_level(type_b)

        # No hierarchy conflict if same level or both unknown
        if level_a == level_b:
            return None

        # Determine which is higher authority (lower level number)
        if level_a < level_b:
            higher_source = source_a
            higher_type = type_a
            lower_type = type_b
            level_diff = level_b - level_a
        else:
            higher_source = source_b
            higher_type = type_b
            lower_type = type_a
            level_diff = level_a - level_b

        # Determine severity based on level difference
        if level_diff >= 3:
            severity = "high"
        elif level_diff >= 2:
            severity = "medium"
        else:
            severity = "low"

        # Build recommendation
        recommendation = HIERARCHY_RECOMMENDATION_TEMPLATE.format(higher_type=higher_type, lower_type=lower_type)

        logger.debug(
            "hierarchy_conflict_detected",
            higher_type=higher_type,
            lower_type=lower_type,
            severity=severity,
        )

        return SourceConflict(
            conflict_type="hierarchy",
            source_a=source_a,
            source_b=source_b,
            preferred_source=higher_source,
            severity=severity,
            recommendation=recommendation,
        )

    def _detect_temporal_conflict(self, source_a: dict, source_b: dict) -> SourceConflict | None:
        """Detect temporal conflict between two sources at the same level.

        A temporal conflict occurs when two sources at the same hierarchy
        level have different dates, with the newer one superseding the older.

        Args:
            source_a: First source dictionary.
            source_b: Second source dictionary.

        Returns:
            SourceConflict if conflict detected, None otherwise.
        """
        type_a = source_a.get("type", "unknown")
        type_b = source_b.get("type", "unknown")

        # Only check temporal conflicts for same hierarchy level
        level_a = self.source_hierarchy.get_level(type_a)
        level_b = self.source_hierarchy.get_level(type_b)

        if level_a != level_b:
            return None

        # Parse dates
        date_a = self._parse_date(source_a.get("date"))
        date_b = self._parse_date(source_b.get("date"))

        # Can't determine temporal conflict without dates
        if date_a is None or date_b is None:
            return None

        # Same date = no temporal conflict
        if date_a == date_b:
            return None

        # Determine which is newer
        if date_a > date_b:
            newer_source = source_a
            newer_date = date_a
            older_date = date_b
        else:
            newer_source = source_b
            newer_date = date_b
            older_date = date_a

        # Determine severity based on time difference
        days_diff = abs((newer_date - older_date).days)
        if days_diff > 365 * 5:  # More than 5 years
            severity = "high"
        elif days_diff > 365 * 2:  # More than 2 years
            severity = "medium"
        else:
            severity = "low"

        # Build recommendation
        recommendation = TEMPORAL_RECOMMENDATION_TEMPLATE.format(
            newer_date=newer_date.strftime("%d/%m/%Y"),
            older_date=older_date.strftime("%d/%m/%Y"),
        )

        logger.debug(
            "temporal_conflict_detected",
            newer_date=str(newer_date),
            older_date=str(older_date),
            severity=severity,
        )

        return SourceConflict(
            conflict_type="temporal",
            source_a=source_a,
            source_b=source_b,
            preferred_source=newer_source,
            severity=severity,
            recommendation=recommendation,
        )

    def _parse_date(self, date_value: Any) -> date | None:
        """Parse a date from various formats.

        Args:
            date_value: Date as string, date, datetime, or None.

        Returns:
            Parsed date object, or None if parsing fails.
        """
        if date_value is None:
            return None

        if isinstance(date_value, datetime):
            return date_value.date()

        if isinstance(date_value, date):
            return date_value

        if isinstance(date_value, str):
            # Try common formats
            formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt).date()
                except ValueError:
                    continue

        return None

    def _build_summary(self, conflicts: list[dict]) -> str:
        """Build a summary description of conflicts.

        Args:
            conflicts: List of conflict dictionaries.

        Returns:
            Italian language summary string.
        """
        if not conflicts:
            return "Nessun conflitto rilevato tra le fonti normative."

        hierarchy_count = sum(1 for c in conflicts if c["type"] == "hierarchy")
        temporal_count = sum(1 for c in conflicts if c["type"] == "temporal")

        parts = []
        if hierarchy_count > 0:
            parts.append(
                f"{hierarchy_count} conflitt{'o' if hierarchy_count == 1 else 'i'} "
                f"gerarchic{'o' if hierarchy_count == 1 else 'i'}"
            )
        if temporal_count > 0:
            parts.append(
                f"{temporal_count} conflitt{'o' if temporal_count == 1 else 'i'} "
                f"temporal{'e' if temporal_count == 1 else 'i'}"
            )

        return f"Rilevati {' e '.join(parts)} tra le fonti normative."


# =============================================================================
# Factory Function
# =============================================================================


def get_source_conflict_detector() -> SourceConflictDetector:
    """Get or create SourceConflictDetector singleton instance.

    Returns:
        SourceConflictDetector instance.

    Example:
        >>> detector = get_source_conflict_detector()
        >>> result = detector.analyze(sources)
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = SourceConflictDetector()
    return _detector_instance


def reset_detector() -> None:
    """Reset the singleton instance (for testing)."""
    global _detector_instance
    _detector_instance = None
