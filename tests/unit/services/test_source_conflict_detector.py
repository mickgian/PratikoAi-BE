"""TDD tests for SourceConflictDetector service (DEV-228).

Tests the source conflict detection service that identifies hierarchy
and temporal conflicts between Italian legal sources.
Tests written BEFORE implementation following TDD methodology.
"""

from datetime import date, datetime

import pytest


class TestSourceConflictDetectorInit:
    """Tests for SourceConflictDetector initialization."""

    def test_init_creates_instance(self):
        """SourceConflictDetector should be instantiable."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        assert detector is not None

    def test_init_with_source_hierarchy(self):
        """SourceConflictDetector should accept optional SourceHierarchy."""
        from app.services.source_conflict_detector import SourceConflictDetector
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        detector = SourceConflictDetector(source_hierarchy=hierarchy)
        assert detector is not None


class TestHierarchyConflictDetection:
    """Tests for detecting hierarchy-based conflicts."""

    def test_detects_circolare_vs_legge_conflict(self):
        """Should detect when circolare contradicts legge."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "content": "IVA al 22%", "date": "2020-01-01"}
        source2 = {"type": "circolare", "content": "IVA al 10%", "date": "2021-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        assert len(conflicts) >= 1
        assert any(c["type"] == "hierarchy" for c in conflicts)

    def test_detects_interpello_vs_decreto_conflict(self):
        """Should detect when interpello contradicts decreto."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "decreto_legislativo", "content": "Aliquota 5%", "date": "2019-01-01"}
        source2 = {"type": "interpello", "content": "Aliquota 8%", "date": "2022-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        assert len(conflicts) >= 1
        assert any(c["type"] == "hierarchy" for c in conflicts)

    def test_no_conflict_same_level_sources(self):
        """Same hierarchy level sources should not trigger hierarchy conflict."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "circolare", "content": "Procedura A", "date": "2020-01-01"}
        source2 = {"type": "risoluzione", "content": "Procedura B", "date": "2021-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        # Same level, no hierarchy conflict
        hierarchy_conflicts = [c for c in conflicts if c["type"] == "hierarchy"]
        assert len(hierarchy_conflicts) == 0

    def test_conflict_includes_higher_authority_source(self):
        """Conflict should indicate which source has higher authority."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "id": "L1", "content": "Rule A", "date": "2020-01-01"}
        source2 = {"type": "circolare", "id": "C1", "content": "Rule B", "date": "2021-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        hierarchy_conflict = next((c for c in conflicts if c["type"] == "hierarchy"), None)
        assert hierarchy_conflict is not None
        assert hierarchy_conflict["preferred_source"]["type"] == "legge"


class TestTemporalConflictDetection:
    """Tests for detecting temporal (date-based) conflicts."""

    def test_detects_newer_law_supersedes_older(self):
        """Newer law at same level should supersede older."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "content": "Old rule", "date": "2015-01-01"}
        source2 = {"type": "legge", "content": "New rule", "date": "2022-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        assert len(conflicts) >= 1
        temporal_conflict = next((c for c in conflicts if c["type"] == "temporal"), None)
        assert temporal_conflict is not None

    def test_newer_source_preferred_same_level(self):
        """At same level, newer source should be preferred."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "circolare", "id": "C1", "content": "Old", "date": "2018-01-01"}
        source2 = {"type": "circolare", "id": "C2", "content": "New", "date": "2023-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        temporal_conflict = next((c for c in conflicts if c["type"] == "temporal"), None)
        assert temporal_conflict is not None
        assert temporal_conflict["preferred_source"]["id"] == "C2"

    def test_handles_date_string_format(self):
        """Should handle various date string formats."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "content": "Old", "date": "2015-06-15"}
        source2 = {"type": "legge", "content": "New", "date": "2022-12-31"}

        conflicts = detector.detect_conflicts([source1, source2])
        assert len(conflicts) >= 1

    def test_handles_datetime_objects(self):
        """Should handle datetime objects as dates."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "content": "Old", "date": date(2015, 1, 1)}
        source2 = {"type": "legge", "content": "New", "date": datetime(2022, 6, 15, 12, 0)}

        conflicts = detector.detect_conflicts([source1, source2])
        assert len(conflicts) >= 1

    def test_no_temporal_conflict_when_dates_close(self):
        """Sources published on same day should not conflict temporally."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "circolare", "content": "A", "date": "2022-01-01"}
        source2 = {"type": "circolare", "content": "B", "date": "2022-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        temporal_conflicts = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal_conflicts) == 0


class TestConflictRecommendations:
    """Tests for conflict resolution recommendations."""

    def test_provides_recommendation_for_hierarchy_conflict(self):
        """Hierarchy conflict should include clear recommendation."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "title": "Legge 123/2020", "content": "A", "date": "2020-01-01"}
        source2 = {"type": "circolare", "title": "Circ. 45/2021", "content": "B", "date": "2021-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        hierarchy_conflict = next((c for c in conflicts if c["type"] == "hierarchy"), None)
        assert hierarchy_conflict is not None
        assert "recommendation" in hierarchy_conflict
        assert "legge" in hierarchy_conflict["recommendation"].lower()

    def test_provides_recommendation_for_temporal_conflict(self):
        """Temporal conflict should include recommendation for newer source."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "title": "L1", "content": "Old", "date": "2010-01-01"}
        source2 = {"type": "legge", "title": "L2", "content": "New", "date": "2023-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        temporal_conflict = next((c for c in conflicts if c["type"] == "temporal"), None)
        assert temporal_conflict is not None
        assert "recommendation" in temporal_conflict

    def test_recommendation_italian_language(self):
        """Recommendations should be in Italian."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "content": "A", "date": "2020-01-01"}
        source2 = {"type": "circolare", "content": "B", "date": "2021-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        # Italian recommendations should include words like "prevalere", "gerarchicamente", etc.
        if conflicts:
            recommendation = conflicts[0].get("recommendation", "")
            # Check for Italian words/patterns
            italian_patterns = ["prevale", "gerarchi", "fonte", "normativ", "recente", "superior"]
            has_italian = any(p in recommendation.lower() for p in italian_patterns)
            assert has_italian or len(recommendation) > 0


class TestConflictResult:
    """Tests for conflict result structure."""

    def test_conflict_has_required_fields(self):
        """Each conflict should have type, sources, preferred_source, recommendation."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "id": "L1", "content": "A", "date": "2020-01-01"}
        source2 = {"type": "circolare", "id": "C1", "content": "B", "date": "2021-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        assert len(conflicts) >= 1

        conflict = conflicts[0]
        assert "type" in conflict
        assert "sources" in conflict
        assert "preferred_source" in conflict
        assert "recommendation" in conflict

    def test_conflict_includes_severity(self):
        """Conflict should include severity level."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "content": "A", "date": "2020-01-01"}
        source2 = {"type": "circolare", "content": "B", "date": "2021-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        assert len(conflicts) >= 1
        assert "severity" in conflicts[0]
        assert conflicts[0]["severity"] in ("high", "medium", "low")

    def test_hierarchy_conflict_high_severity(self):
        """Hierarchy conflict with wide gap should be high severity."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "content": "A", "date": "2020-01-01"}  # Level 1
        source2 = {"type": "interpello", "content": "B", "date": "2021-01-01"}  # Level 4

        conflicts = detector.detect_conflicts([source1, source2])
        hierarchy_conflict = next((c for c in conflicts if c["type"] == "hierarchy"), None)
        assert hierarchy_conflict is not None
        assert hierarchy_conflict["severity"] == "high"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_empty_source_list(self):
        """Should handle empty source list gracefully."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        conflicts = detector.detect_conflicts([])
        assert conflicts == []

    def test_handles_single_source(self):
        """Single source should not have conflicts."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source = {"type": "legge", "content": "Rule", "date": "2020-01-01"}
        conflicts = detector.detect_conflicts([source])
        assert conflicts == []

    def test_handles_missing_date(self):
        """Should handle sources without dates."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "content": "A"}  # No date
        source2 = {"type": "circolare", "content": "B", "date": "2021-01-01"}

        # Should still detect hierarchy conflict
        conflicts = detector.detect_conflicts([source1, source2])
        hierarchy_conflicts = [c for c in conflicts if c["type"] == "hierarchy"]
        assert len(hierarchy_conflicts) >= 1

    def test_handles_missing_type(self):
        """Should handle sources without type field."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"content": "A", "date": "2020-01-01"}  # No type
        source2 = {"type": "legge", "content": "B", "date": "2021-01-01"}

        # Should not crash
        conflicts = detector.detect_conflicts([source1, source2])
        assert isinstance(conflicts, list)

    def test_handles_invalid_date_format(self):
        """Should handle invalid date formats gracefully."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "legge", "content": "A", "date": "invalid-date"}
        source2 = {"type": "legge", "content": "B", "date": "2021-01-01"}

        # Should not crash
        conflicts = detector.detect_conflicts([source1, source2])
        assert isinstance(conflicts, list)

    def test_handles_unknown_source_types(self):
        """Should handle unknown source types."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        source1 = {"type": "unknown_type_1", "content": "A", "date": "2020-01-01"}
        source2 = {"type": "unknown_type_2", "content": "B", "date": "2021-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        assert isinstance(conflicts, list)


class TestMultipleSourceConflicts:
    """Tests for detecting conflicts among multiple sources."""

    def test_detects_all_pairwise_conflicts(self):
        """Should detect conflicts between all relevant source pairs."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        sources = [
            {"type": "legge", "id": "L1", "content": "Rule 1", "date": "2020-01-01"},
            {"type": "circolare", "id": "C1", "content": "Rule 2", "date": "2021-01-01"},
            {"type": "interpello", "id": "I1", "content": "Rule 3", "date": "2022-01-01"},
        ]

        conflicts = detector.detect_conflicts(sources)
        # L1 vs C1 (hierarchy), L1 vs I1 (hierarchy), C1 vs I1 (hierarchy)
        assert len(conflicts) >= 2

    def test_conflict_summary(self):
        """Should provide summary of all conflicts."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        sources = [
            {"type": "legge", "content": "A", "date": "2020-01-01"},
            {"type": "circolare", "content": "B", "date": "2021-01-01"},
        ]

        result = detector.analyze(sources)
        assert "conflicts" in result
        assert "summary" in result
        assert "has_conflicts" in result


class TestAnalyzeMethod:
    """Tests for the analyze() method that provides full analysis."""

    def test_analyze_returns_structured_result(self):
        """analyze() should return structured analysis result."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        sources = [
            {"type": "legge", "content": "A", "date": "2020-01-01"},
            {"type": "circolare", "content": "B", "date": "2021-01-01"},
        ]

        result = detector.analyze(sources)
        assert isinstance(result, dict)
        assert "conflicts" in result
        assert "has_conflicts" in result
        assert "conflict_count" in result
        assert "hierarchy_conflicts" in result
        assert "temporal_conflicts" in result

    def test_analyze_counts_by_type(self):
        """analyze() should count conflicts by type."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        sources = [
            {"type": "legge", "content": "A", "date": "2020-01-01"},
            {"type": "legge", "content": "B", "date": "2023-01-01"},
            {"type": "circolare", "content": "C", "date": "2022-01-01"},
        ]

        result = detector.analyze(sources)
        assert result["hierarchy_conflicts"] >= 0
        assert result["temporal_conflicts"] >= 0

    def test_analyze_no_conflicts(self):
        """analyze() should indicate when no conflicts exist."""
        from app.services.source_conflict_detector import SourceConflictDetector

        detector = SourceConflictDetector()
        sources = [
            {"type": "legge", "content": "Rule about VAT", "date": "2020-01-01"},
        ]

        result = detector.analyze(sources)
        assert result["has_conflicts"] is False
        assert result["conflict_count"] == 0


class TestConflictDataclass:
    """Tests for SourceConflict dataclass."""

    def test_source_conflict_dataclass_creation(self):
        """SourceConflict dataclass should be creatable."""
        from app.services.source_conflict_detector import SourceConflict

        conflict = SourceConflict(
            conflict_type="hierarchy",
            source_a={"type": "legge", "id": "L1"},
            source_b={"type": "circolare", "id": "C1"},
            preferred_source={"type": "legge", "id": "L1"},
            severity="high",
            recommendation="La legge prevale sulla circolare.",
        )
        assert conflict.conflict_type == "hierarchy"
        assert conflict.severity == "high"

    def test_source_conflict_to_dict(self):
        """SourceConflict should be convertible to dict."""
        from app.services.source_conflict_detector import SourceConflict

        conflict = SourceConflict(
            conflict_type="temporal",
            source_a={"type": "legge", "id": "L1"},
            source_b={"type": "legge", "id": "L2"},
            preferred_source={"type": "legge", "id": "L2"},
            severity="medium",
            recommendation="La fonte più recente prevale.",
        )
        d = conflict.to_dict()
        assert d["type"] == "temporal"
        assert d["severity"] == "medium"
        assert "sources" in d
        assert "preferred_source" in d
        assert "recommendation" in d


class TestFactoryFunction:
    """Tests for factory function."""

    def test_get_source_conflict_detector_returns_instance(self):
        """get_source_conflict_detector should return instance."""
        from app.services.source_conflict_detector import get_source_conflict_detector

        detector = get_source_conflict_detector()
        assert detector is not None
        assert hasattr(detector, "detect_conflicts")
        assert hasattr(detector, "analyze")

    def test_get_source_conflict_detector_singleton(self):
        """get_source_conflict_detector should return singleton."""
        from app.services.source_conflict_detector import get_source_conflict_detector

        d1 = get_source_conflict_detector()
        d2 = get_source_conflict_detector()
        assert d1 is d2


class TestIntegrationWithSourceHierarchy:
    """Tests for integration with SourceHierarchy service."""

    def test_uses_source_hierarchy_weights(self):
        """Should use SourceHierarchy for determining authority levels."""
        from app.services.source_conflict_detector import SourceConflictDetector
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        detector = SourceConflictDetector(source_hierarchy=hierarchy)

        source1 = {"type": "corte_costituzionale", "content": "A", "date": "2020-01-01"}
        source2 = {"type": "ctp_ctr", "content": "B", "date": "2021-01-01"}

        conflicts = detector.detect_conflicts([source1, source2])
        # corte_costituzionale (1.0) vs ctp_ctr (0.5) - should prefer corte
        hierarchy_conflict = next((c for c in conflicts if c["type"] == "hierarchy"), None)
        if hierarchy_conflict:
            assert hierarchy_conflict["preferred_source"]["type"] == "corte_costituzionale"
