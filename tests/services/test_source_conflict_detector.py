"""Tests for SourceConflictDetector service (DEV-228).

Comprehensive test suite targeting 90%+ coverage of
app/services/source_conflict_detector.py (426 lines).

Covers every public and private method:
- SourceConflict dataclass and to_dict
- detect_conflicts: <2 sources, hierarchy pairs, temporal pairs, mixed
- analyze: full analysis with summary, counts, has_conflicts
- _detect_hierarchy_conflict: same level, diff=1 (low), diff=2 (medium), diff>=3 (high)
- _detect_temporal_conflict: different levels, same level w/ dates, same date,
  missing dates, severity by year gap
- _parse_date: None, datetime, date, str with 4 formats, invalid str, non-str
- _build_summary: no conflicts, only hierarchy, only temporal, mixed, singular/plural
- get_source_conflict_detector / reset_detector singleton
"""

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from app.services.source_conflict_detector import (
    SourceConflict,
    SourceConflictDetector,
    get_source_conflict_detector,
    reset_detector,
)
from app.services.source_hierarchy import SourceHierarchy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(
    source_type: str = "legge",
    content: str = "Some content",
    date_value: str | None = None,
) -> dict:
    d = {"type": source_type, "content": content}
    if date_value is not None:
        d["date"] = date_value
    return d


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure singleton is clean before each test."""
    reset_detector()
    yield
    reset_detector()


@pytest.fixture()
def detector() -> SourceConflictDetector:
    return SourceConflictDetector()


# ===========================================================================
# SourceConflict dataclass
# ===========================================================================


class TestSourceConflict:
    """Tests for the SourceConflict dataclass and to_dict."""

    def test_to_dict_structure(self):
        sc = SourceConflict(
            conflict_type="hierarchy",
            source_a={"type": "legge"},
            source_b={"type": "circolare"},
            preferred_source={"type": "legge"},
            severity="high",
            recommendation="Prefer legge.",
        )
        d = sc.to_dict()
        assert d["type"] == "hierarchy"
        assert d["sources"] == [{"type": "legge"}, {"type": "circolare"}]
        assert d["preferred_source"] == {"type": "legge"}
        assert d["severity"] == "high"
        assert d["recommendation"] == "Prefer legge."

    def test_to_dict_temporal_type(self):
        sc = SourceConflict(
            conflict_type="temporal",
            source_a={"type": "legge", "date": "2020-01-01"},
            source_b={"type": "legge", "date": "2023-01-01"},
            preferred_source={"type": "legge", "date": "2023-01-01"},
            severity="medium",
            recommendation="Newer prevails.",
        )
        d = sc.to_dict()
        assert d["type"] == "temporal"
        assert len(d["sources"]) == 2


# ===========================================================================
# detect_conflicts
# ===========================================================================


class TestDetectConflicts:
    """Tests for detect_conflicts."""

    def test_empty_list(self, detector):
        assert detector.detect_conflicts([]) == []

    def test_single_source(self, detector):
        assert detector.detect_conflicts([_make_source()]) == []

    def test_two_same_level_no_dates(self, detector):
        """Same level, no dates -> hierarchy conflict: no (same level), temporal: no (no dates)."""
        sources = [
            _make_source("legge"),
            _make_source("dpr"),
        ]
        conflicts = detector.detect_conflicts(sources)
        # legge and dpr are both level 1 => no hierarchy conflict
        # No dates => no temporal conflict
        assert len(conflicts) == 0

    def test_hierarchy_conflict_legge_vs_circolare(self, detector):
        sources = [
            _make_source("legge"),
            _make_source("circolare"),
        ]
        conflicts = detector.detect_conflicts(sources)
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "hierarchy"
        assert conflicts[0]["preferred_source"]["type"] == "legge"

    def test_hierarchy_conflict_severity_high(self, detector):
        """legge (level 1) vs interpello (level 4) = diff 3 => high."""
        sources = [
            _make_source("legge"),
            _make_source("interpello"),
        ]
        conflicts = detector.detect_conflicts(sources)
        hierarchy = [c for c in conflicts if c["type"] == "hierarchy"]
        assert len(hierarchy) == 1
        assert hierarchy[0]["severity"] == "high"

    def test_hierarchy_conflict_severity_medium(self, detector):
        """legge (level 1) vs circolare (level 3) = diff 2 => medium."""
        sources = [
            _make_source("legge"),
            _make_source("circolare"),
        ]
        conflicts = detector.detect_conflicts(sources)
        hierarchy = [c for c in conflicts if c["type"] == "hierarchy"]
        assert len(hierarchy) == 1
        assert hierarchy[0]["severity"] == "medium"

    def test_hierarchy_conflict_severity_low(self, detector):
        """legge (level 1) vs decreto_ministeriale (level 2) = diff 1 => low."""
        sources = [
            _make_source("legge"),
            _make_source("decreto_ministeriale"),
        ]
        conflicts = detector.detect_conflicts(sources)
        hierarchy = [c for c in conflicts if c["type"] == "hierarchy"]
        assert len(hierarchy) == 1
        assert hierarchy[0]["severity"] == "low"

    def test_temporal_conflict_same_level_with_dates(self, detector):
        """Two legge sources with different dates => temporal conflict."""
        sources = [
            _make_source("legge", date_value="2018-01-01"),
            _make_source("legge", date_value="2023-06-15"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal) == 1
        assert temporal[0]["preferred_source"]["date"] == "2023-06-15"

    def test_temporal_conflict_severity_high(self, detector):
        """More than 5 years apart => high severity."""
        sources = [
            _make_source("legge", date_value="2010-01-01"),
            _make_source("legge", date_value="2023-01-01"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal) == 1
        assert temporal[0]["severity"] == "high"

    def test_temporal_conflict_severity_medium(self, detector):
        """Between 2 and 5 years => medium severity."""
        sources = [
            _make_source("legge", date_value="2020-01-01"),
            _make_source("legge", date_value="2023-01-01"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal) == 1
        assert temporal[0]["severity"] == "medium"

    def test_temporal_conflict_severity_low(self, detector):
        """Less than 2 years => low severity."""
        sources = [
            _make_source("legge", date_value="2022-06-01"),
            _make_source("legge", date_value="2023-06-01"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal) == 1
        assert temporal[0]["severity"] == "low"

    def test_no_temporal_conflict_when_same_date(self, detector):
        sources = [
            _make_source("legge", date_value="2023-01-01"),
            _make_source("legge", date_value="2023-01-01"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal) == 0

    def test_no_temporal_conflict_different_levels(self, detector):
        """Temporal conflicts only apply at the same hierarchy level."""
        sources = [
            _make_source("legge", date_value="2010-01-01"),
            _make_source("circolare", date_value="2023-01-01"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal) == 0

    def test_both_hierarchy_and_no_temporal_for_different_levels(self, detector):
        """Different levels with dates: only hierarchy conflict, no temporal."""
        sources = [
            _make_source("legge", date_value="2020-01-01"),
            _make_source("circolare", date_value="2023-01-01"),
        ]
        conflicts = detector.detect_conflicts(sources)
        types = {c["type"] for c in conflicts}
        assert "hierarchy" in types
        assert "temporal" not in types

    def test_three_sources_pairwise_checks(self, detector):
        """With 3 sources, all 3 pairs are checked."""
        sources = [
            _make_source("legge"),
            _make_source("circolare"),
            _make_source("interpello"),
        ]
        conflicts = detector.detect_conflicts(sources)
        # legge vs circolare, legge vs interpello, circolare vs interpello
        assert len(conflicts) == 3

    def test_recommendation_contains_italian_text(self, detector):
        sources = [
            _make_source("legge"),
            _make_source("circolare"),
        ]
        conflicts = detector.detect_conflicts(sources)
        assert len(conflicts) == 1
        rec = conflicts[0]["recommendation"]
        assert "prevale" in rec
        assert "gerarchicamente" in rec

    def test_temporal_recommendation_contains_dates(self, detector):
        sources = [
            _make_source("legge", date_value="2018-01-01"),
            _make_source("legge", date_value="2023-06-15"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        rec = temporal[0]["recommendation"]
        assert "15/06/2023" in rec
        assert "01/01/2018" in rec
        assert "Lex posterior" in rec


# ===========================================================================
# _detect_hierarchy_conflict
# ===========================================================================


class TestDetectHierarchyConflict:
    """Tests for _detect_hierarchy_conflict."""

    def test_same_level_returns_none(self, detector):
        a = _make_source("legge")
        b = _make_source("dpr")
        assert detector._detect_hierarchy_conflict(a, b) is None

    def test_higher_a_lower_b(self, detector):
        a = _make_source("legge")
        b = _make_source("circolare")
        conflict = detector._detect_hierarchy_conflict(a, b)
        assert conflict is not None
        assert conflict.preferred_source == a

    def test_lower_a_higher_b(self, detector):
        a = _make_source("circolare")
        b = _make_source("legge")
        conflict = detector._detect_hierarchy_conflict(a, b)
        assert conflict is not None
        assert conflict.preferred_source == b

    def test_missing_type_uses_unknown(self, detector):
        a = {"content": "no type"}
        b = _make_source("legge")
        conflict = detector._detect_hierarchy_conflict(a, b)
        # unknown is level 99, legge is level 1, diff = 98 => high
        assert conflict is not None
        assert conflict.severity == "high"

    def test_both_unknown_returns_none(self, detector):
        a = {"content": "no type 1"}
        b = {"content": "no type 2"}
        # Both get level 99 => same level => None
        assert detector._detect_hierarchy_conflict(a, b) is None


# ===========================================================================
# _detect_temporal_conflict
# ===========================================================================


class TestDetectTemporalConflict:
    """Tests for _detect_temporal_conflict."""

    def test_different_levels_returns_none(self, detector):
        a = _make_source("legge", date_value="2020-01-01")
        b = _make_source("circolare", date_value="2023-01-01")
        assert detector._detect_temporal_conflict(a, b) is None

    def test_same_level_no_date_a_returns_none(self, detector):
        a = _make_source("legge")
        b = _make_source("legge", date_value="2023-01-01")
        assert detector._detect_temporal_conflict(a, b) is None

    def test_same_level_no_date_b_returns_none(self, detector):
        a = _make_source("legge", date_value="2023-01-01")
        b = _make_source("legge")
        assert detector._detect_temporal_conflict(a, b) is None

    def test_same_date_returns_none(self, detector):
        a = _make_source("legge", date_value="2023-01-01")
        b = _make_source("legge", date_value="2023-01-01")
        assert detector._detect_temporal_conflict(a, b) is None

    def test_newer_a_preferred(self, detector):
        a = _make_source("legge", date_value="2023-06-15")
        b = _make_source("legge", date_value="2020-01-01")
        conflict = detector._detect_temporal_conflict(a, b)
        assert conflict is not None
        assert conflict.preferred_source == a

    def test_newer_b_preferred(self, detector):
        a = _make_source("legge", date_value="2020-01-01")
        b = _make_source("legge", date_value="2023-06-15")
        conflict = detector._detect_temporal_conflict(a, b)
        assert conflict is not None
        assert conflict.preferred_source == b


# ===========================================================================
# _parse_date
# ===========================================================================


class TestParseDate:
    """Tests for _parse_date with various input types."""

    def test_none_returns_none(self, detector):
        assert detector._parse_date(None) is None

    def test_datetime_returns_date(self, detector):
        dt = datetime(2023, 6, 15, 12, 30)
        result = detector._parse_date(dt)
        assert result == date(2023, 6, 15)

    def test_date_returns_date(self, detector):
        d = date(2023, 6, 15)
        result = detector._parse_date(d)
        assert result == date(2023, 6, 15)

    def test_str_iso_format(self, detector):
        result = detector._parse_date("2023-06-15")
        assert result == date(2023, 6, 15)

    def test_str_italian_slash_format(self, detector):
        result = detector._parse_date("15/06/2023")
        assert result == date(2023, 6, 15)

    def test_str_italian_dash_format(self, detector):
        result = detector._parse_date("15-06-2023")
        assert result == date(2023, 6, 15)

    def test_str_year_slash_format(self, detector):
        result = detector._parse_date("2023/06/15")
        assert result == date(2023, 6, 15)

    def test_invalid_string_returns_none(self, detector):
        assert detector._parse_date("not-a-date") is None

    def test_empty_string_returns_none(self, detector):
        assert detector._parse_date("") is None

    def test_integer_returns_none(self, detector):
        assert detector._parse_date(20230615) is None

    def test_list_returns_none(self, detector):
        assert detector._parse_date([2023, 6, 15]) is None

    def test_partial_date_string_returns_none(self, detector):
        assert detector._parse_date("2023-06") is None


# ===========================================================================
# _build_summary
# ===========================================================================


class TestBuildSummary:
    """Tests for _build_summary with Italian singular/plural forms."""

    def test_no_conflicts(self, detector):
        summary = detector._build_summary([])
        assert summary == "Nessun conflitto rilevato tra le fonti normative."

    def test_one_hierarchy_conflict_singular(self, detector):
        conflicts = [{"type": "hierarchy"}]
        summary = detector._build_summary(conflicts)
        assert "1 conflitto gerarchico" in summary
        assert "Rilevati" in summary

    def test_multiple_hierarchy_conflicts_plural(self, detector):
        conflicts = [{"type": "hierarchy"}, {"type": "hierarchy"}]
        summary = detector._build_summary(conflicts)
        assert "2 conflitti gerarchici" in summary

    def test_one_temporal_conflict_singular(self, detector):
        conflicts = [{"type": "temporal"}]
        summary = detector._build_summary(conflicts)
        assert "1 conflitto temporale" in summary

    def test_multiple_temporal_conflicts_plural(self, detector):
        conflicts = [{"type": "temporal"}, {"type": "temporal"}, {"type": "temporal"}]
        summary = detector._build_summary(conflicts)
        assert "3 conflitti temporali" in summary

    def test_mixed_hierarchy_and_temporal(self, detector):
        conflicts = [
            {"type": "hierarchy"},
            {"type": "hierarchy"},
            {"type": "temporal"},
        ]
        summary = detector._build_summary(conflicts)
        assert "2 conflitti gerarchici" in summary
        assert "1 conflitto temporale" in summary
        assert " e " in summary


# ===========================================================================
# analyze
# ===========================================================================


class TestAnalyze:
    """Tests for the analyze method."""

    def test_no_conflicts(self, detector):
        result = detector.analyze([_make_source("legge")])
        assert result["has_conflicts"] is False
        assert result["conflict_count"] == 0
        assert result["hierarchy_conflicts"] == 0
        assert result["temporal_conflicts"] == 0
        assert "Nessun conflitto" in result["summary"]

    def test_hierarchy_only(self, detector):
        sources = [
            _make_source("legge"),
            _make_source("circolare"),
        ]
        result = detector.analyze(sources)
        assert result["has_conflicts"] is True
        assert result["conflict_count"] == 1
        assert result["hierarchy_conflicts"] == 1
        assert result["temporal_conflicts"] == 0

    def test_temporal_only(self, detector):
        sources = [
            _make_source("legge", date_value="2015-01-01"),
            _make_source("legge", date_value="2023-01-01"),
        ]
        result = detector.analyze(sources)
        assert result["has_conflicts"] is True
        assert result["hierarchy_conflicts"] == 0
        assert result["temporal_conflicts"] == 1

    def test_mixed_conflicts(self, detector):
        sources = [
            _make_source("legge", date_value="2015-01-01"),
            _make_source("legge", date_value="2023-01-01"),
            _make_source("circolare"),
        ]
        result = detector.analyze(sources)
        assert result["has_conflicts"] is True
        assert result["hierarchy_conflicts"] >= 1
        assert result["temporal_conflicts"] >= 1
        assert result["conflict_count"] >= 2

    def test_analyze_returns_conflicts_list(self, detector):
        sources = [
            _make_source("legge"),
            _make_source("circolare"),
        ]
        result = detector.analyze(sources)
        assert isinstance(result["conflicts"], list)
        assert len(result["conflicts"]) == result["conflict_count"]

    def test_analyze_summary_present(self, detector):
        sources = [
            _make_source("legge"),
            _make_source("circolare"),
        ]
        result = detector.analyze(sources)
        assert "summary" in result
        assert isinstance(result["summary"], str)


# ===========================================================================
# Singleton factory functions
# ===========================================================================


class TestSingleton:
    """Tests for get_source_conflict_detector and reset_detector."""

    def test_get_returns_instance(self):
        instance = get_source_conflict_detector()
        assert isinstance(instance, SourceConflictDetector)

    def test_get_returns_same_instance(self):
        a = get_source_conflict_detector()
        b = get_source_conflict_detector()
        assert a is b

    def test_reset_creates_new_instance(self):
        a = get_source_conflict_detector()
        reset_detector()
        b = get_source_conflict_detector()
        assert a is not b

    def test_multiple_resets(self):
        reset_detector()
        reset_detector()
        instance = get_source_conflict_detector()
        assert isinstance(instance, SourceConflictDetector)


# ===========================================================================
# Custom hierarchy injection
# ===========================================================================


class TestCustomHierarchy:
    """Test that SourceConflictDetector accepts a custom SourceHierarchy."""

    def test_custom_hierarchy_used(self):
        mock_hierarchy = MagicMock(spec=SourceHierarchy)
        mock_hierarchy.get_level.side_effect = lambda t: 1 if t == "alpha" else 5
        detector = SourceConflictDetector(source_hierarchy=mock_hierarchy)
        sources = [
            {"type": "alpha", "content": "A"},
            {"type": "beta", "content": "B"},
        ]
        conflicts = detector.detect_conflicts(sources)
        hierarchy = [c for c in conflicts if c["type"] == "hierarchy"]
        assert len(hierarchy) == 1
        assert hierarchy[0]["severity"] == "high"  # diff = 4

    def test_default_hierarchy_when_none(self):
        detector = SourceConflictDetector(source_hierarchy=None)
        assert detector.source_hierarchy is not None


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    """Edge cases for comprehensive coverage."""

    def test_sources_with_missing_type_key(self, detector):
        sources = [
            {"content": "no type field"},
            _make_source("legge"),
        ]
        conflicts = detector.detect_conflicts(sources)
        # unknown (level 99) vs legge (level 1) => hierarchy conflict
        assert len(conflicts) >= 1

    def test_temporal_boundary_exactly_5_years(self, detector):
        """Exactly 5 years = 1826 days (>1825) => high."""
        sources = [
            _make_source("legge", date_value="2018-01-01"),
            _make_source("legge", date_value="2023-01-02"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal) == 1
        assert temporal[0]["severity"] == "high"

    def test_temporal_boundary_exactly_2_years(self, detector):
        """Just over 2 years => medium."""
        sources = [
            _make_source("legge", date_value="2021-01-01"),
            _make_source("legge", date_value="2023-01-02"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal) == 1
        assert temporal[0]["severity"] == "medium"

    def test_temporal_under_2_years(self, detector):
        """Just under 2 years => low."""
        sources = [
            _make_source("legge", date_value="2022-01-01"),
            _make_source("legge", date_value="2023-06-01"),
        ]
        conflicts = detector.detect_conflicts(sources)
        temporal = [c for c in conflicts if c["type"] == "temporal"]
        assert len(temporal) == 1
        assert temporal[0]["severity"] == "low"

    def test_hierarchy_reversed_order_b_higher(self, detector):
        """When source_b is higher authority, preferred_source is b."""
        a = _make_source("interpello")
        b = _make_source("legge")
        conflict = detector._detect_hierarchy_conflict(a, b)
        assert conflict is not None
        assert conflict.preferred_source == b

    def test_parse_date_with_italian_slash_day_month_year(self, detector):
        """Test dd/mm/yyyy format specifically."""
        result = detector._parse_date("25/12/2023")
        assert result == date(2023, 12, 25)
