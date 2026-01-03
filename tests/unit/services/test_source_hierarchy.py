"""TDD tests for SourceHierarchy service (DEV-227).

Tests the Italian legal source hierarchy mapping and weighting service.
Tests written BEFORE implementation following TDD methodology.
"""

import pytest


class TestSourceHierarchyWeights:
    """Tests for source weight assignment."""

    def test_legge_has_weight_1_0(self):
        """Primary source 'legge' should have maximum weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("legge") == 1.0

    def test_decreto_legislativo_has_weight_1_0(self):
        """Primary source 'decreto_legislativo' should have maximum weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("decreto_legislativo") == 1.0

    def test_dpr_has_weight_1_0(self):
        """Primary source 'dpr' should have maximum weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("dpr") == 1.0

    def test_decreto_legge_has_weight_1_0(self):
        """Primary source 'decreto_legge' should have maximum weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("decreto_legge") == 1.0

    def test_decreto_ministeriale_has_weight_0_8(self):
        """Secondary source 'decreto_ministeriale' should have weight 0.8."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("decreto_ministeriale") == 0.8

    def test_regolamento_ue_has_weight_0_8(self):
        """Secondary source 'regolamento_ue' should have weight 0.8."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("regolamento_ue") == 0.8

    def test_circolare_has_weight_0_6(self):
        """Administrative practice 'circolare' should have weight 0.6."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("circolare") == 0.6

    def test_risoluzione_has_weight_0_6(self):
        """Administrative practice 'risoluzione' should have weight 0.6."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("risoluzione") == 0.6

    def test_provvedimento_has_weight_0_6(self):
        """Administrative practice 'provvedimento' should have weight 0.6."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("provvedimento") == 0.6

    def test_interpello_has_weight_0_4(self):
        """Interpretation 'interpello' should have weight 0.4."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("interpello") == 0.4

    def test_faq_has_weight_0_4(self):
        """Interpretation 'faq' should have weight 0.4."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("faq") == 0.4

    def test_cassazione_has_weight_0_9(self):
        """Case law 'cassazione' should have weight 0.9."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("cassazione") == 0.9

    def test_corte_costituzionale_has_weight_1_0(self):
        """Case law 'corte_costituzionale' should have maximum weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("corte_costituzionale") == 1.0

    def test_cgue_has_weight_0_95(self):
        """Case law 'cgue' should have weight 0.95."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("cgue") == 0.95

    def test_ctp_ctr_has_weight_0_5(self):
        """Lower court case law 'ctp_ctr' should have weight 0.5."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("ctp_ctr") == 0.5

    def test_unknown_type_defaults_to_0_5(self):
        """Unknown source types should default to 0.5."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("unknown_type") == 0.5
        assert hierarchy.get_weight("random_source") == 0.5

    def test_weight_case_insensitive(self):
        """Source type lookup should be case insensitive."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("LEGGE") == 1.0
        assert hierarchy.get_weight("Circolare") == 0.6
        assert hierarchy.get_weight("INTERPELLO") == 0.4


class TestSourceHierarchyAbbreviations:
    """Tests for abbreviated source type names."""

    def test_d_lgs_abbreviation(self):
        """D.Lgs. abbreviation should map to decreto_legislativo weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("d.lgs") == 1.0
        assert hierarchy.get_weight("d.lgs.") == 1.0

    def test_d_l_abbreviation(self):
        """D.L. abbreviation should map to decreto_legge weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("d.l.") == 1.0
        assert hierarchy.get_weight("d.l") == 1.0

    def test_d_m_abbreviation(self):
        """D.M. abbreviation should map to decreto_ministeriale weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("d.m.") == 0.8
        assert hierarchy.get_weight("d.m") == 0.8

    def test_d_p_r_abbreviation(self):
        """D.P.R. abbreviation should map to dpr weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_weight("d.p.r.") == 1.0
        assert hierarchy.get_weight("d.p.r") == 1.0


class TestSourceHierarchyLevels:
    """Tests for hierarchy level assignment."""

    def test_get_level_primary_sources(self):
        """Primary sources should be level 1."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_level("legge") == 1
        assert hierarchy.get_level("decreto_legislativo") == 1
        assert hierarchy.get_level("dpr") == 1
        assert hierarchy.get_level("decreto_legge") == 1

    def test_get_level_secondary_sources(self):
        """Secondary sources should be level 2."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_level("decreto_ministeriale") == 2
        assert hierarchy.get_level("regolamento_ue") == 2

    def test_get_level_administrative_practice(self):
        """Administrative practice should be level 3."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_level("circolare") == 3
        assert hierarchy.get_level("risoluzione") == 3
        assert hierarchy.get_level("provvedimento") == 3

    def test_get_level_interpretations(self):
        """Interpretations should be level 4."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_level("interpello") == 4
        assert hierarchy.get_level("faq") == 4

    def test_get_level_case_law(self):
        """Case law should be level 5."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_level("cassazione") == 5
        assert hierarchy.get_level("corte_costituzionale") == 5
        assert hierarchy.get_level("cgue") == 5
        assert hierarchy.get_level("ctp_ctr") == 5

    def test_get_level_unknown_defaults_to_99(self):
        """Unknown source types should default to level 99."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.get_level("unknown") == 99


class TestSourceHierarchyComparison:
    """Tests for source comparison functionality."""

    def test_compare_sources_legge_beats_circolare(self):
        """Legge should rank higher than circolare."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        result = hierarchy.compare_sources("legge", "circolare")
        assert result > 0  # Positive means first source is higher authority

    def test_compare_sources_circolare_lower_than_legge(self):
        """Circolare should rank lower than legge."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        result = hierarchy.compare_sources("circolare", "legge")
        assert result < 0  # Negative means first source is lower authority

    def test_compare_sources_same_level_returns_zero(self):
        """Same level sources should return zero."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        result = hierarchy.compare_sources("circolare", "risoluzione")
        assert result == 0

    def test_compare_sources_case_insensitive(self):
        """Source comparison should be case insensitive."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        result = hierarchy.compare_sources("LEGGE", "circolare")
        assert result > 0


class TestSourceHierarchyNormalization:
    """Tests for source type normalization."""

    def test_normalize_type_lowercase(self):
        """Normalization should convert to lowercase."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.normalize_type("LEGGE") == "legge"
        assert hierarchy.normalize_type("Circolare") == "circolare"

    def test_normalize_type_strips_whitespace(self):
        """Normalization should strip whitespace."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        assert hierarchy.normalize_type("  legge  ") == "legge"
        assert hierarchy.normalize_type("\tcircolare\n") == "circolare"

    def test_normalize_type_handles_abbreviations(self):
        """Normalization should handle common abbreviations."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        # Should normalize to canonical form
        assert hierarchy.normalize_type("D.Lgs.") in ("d.lgs.", "d.lgs", "decreto_legislativo")
        assert hierarchy.normalize_type("D.M.") in ("d.m.", "d.m", "decreto_ministeriale")


class TestSourceHierarchyListTypes:
    """Tests for listing source types."""

    def test_get_all_types_returns_all_known_types(self):
        """get_all_types should return all known source types."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        types = hierarchy.get_all_types()
        assert "legge" in types
        assert "circolare" in types
        assert "interpello" in types
        assert "cassazione" in types

    def test_get_types_at_level_1(self):
        """get_types_at_level(1) should return primary sources."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        types = hierarchy.get_types_at_level(1)
        assert "legge" in types
        assert "decreto_legislativo" in types
        assert "circolare" not in types

    def test_get_types_at_level_3(self):
        """get_types_at_level(3) should return administrative practice sources."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        types = hierarchy.get_types_at_level(3)
        assert "circolare" in types
        assert "risoluzione" in types
        assert "provvedimento" in types
        assert "legge" not in types


class TestSourceHierarchyWeightRange:
    """Tests for weight range validation."""

    def test_all_weights_between_0_and_1(self):
        """All weights should be between 0.0 and 1.0."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        for source_type in hierarchy.get_all_types():
            weight = hierarchy.get_weight(source_type)
            assert 0.0 <= weight <= 1.0, f"{source_type} weight {weight} out of range"

    def test_higher_level_has_higher_or_equal_weight(self):
        """Higher hierarchy levels should generally have higher weights."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        # Level 1 should be >= Level 3
        assert hierarchy.get_weight("legge") >= hierarchy.get_weight("circolare")
        # Level 3 should be >= Level 4
        assert hierarchy.get_weight("circolare") >= hierarchy.get_weight("interpello")


class TestSourceHierarchyProtocol:
    """Tests that SourceHierarchy implements the protocol."""

    def test_implements_source_hierarchy_protocol(self):
        """SourceHierarchy should implement SourceHierarchyProtocol."""
        from app.services.source_hierarchy import SourceHierarchy
        from app.services.tree_of_thoughts_reasoner import SourceHierarchyProtocol

        hierarchy = SourceHierarchy()
        # Should have get_weight method matching the protocol
        assert hasattr(hierarchy, "get_weight")
        assert callable(hierarchy.get_weight)
        # Verify it works as expected by protocol
        weight = hierarchy.get_weight("legge")
        assert isinstance(weight, float)


class TestSourceHierarchyFactoryFunction:
    """Tests for factory function."""

    def test_get_source_hierarchy_returns_instance(self):
        """get_source_hierarchy should return SourceHierarchy instance."""
        from app.services.source_hierarchy import get_source_hierarchy

        hierarchy = get_source_hierarchy()
        assert hierarchy is not None
        assert hasattr(hierarchy, "get_weight")

    def test_get_source_hierarchy_returns_singleton(self):
        """get_source_hierarchy should return the same instance."""
        from app.services.source_hierarchy import get_source_hierarchy

        h1 = get_source_hierarchy()
        h2 = get_source_hierarchy()
        assert h1 is h2


class TestSourceHierarchySourceInfo:
    """Tests for getting source info."""

    def test_get_source_info_returns_dict(self):
        """get_source_info should return a dictionary with source details."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        info = hierarchy.get_source_info("legge")
        assert isinstance(info, dict)
        assert "type" in info
        assert "weight" in info
        assert "level" in info
        assert "level_name" in info

    def test_get_source_info_correct_values(self):
        """get_source_info should return correct values."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        info = hierarchy.get_source_info("legge")
        assert info["type"] == "legge"
        assert info["weight"] == 1.0
        assert info["level"] == 1
        assert info["level_name"] == "primary"

    def test_get_source_info_circolare(self):
        """get_source_info for circolare should have correct level name."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        info = hierarchy.get_source_info("circolare")
        assert info["level"] == 3
        assert info["level_name"] == "administrative"


class TestSourceHierarchyScoreCalculation:
    """Tests for calculating source-weighted scores."""

    def test_calculate_source_score_single_source(self):
        """Should calculate score based on single source weight."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        sources = [{"type": "legge"}]
        score = hierarchy.calculate_source_score(sources)
        assert score == 1.0

    def test_calculate_source_score_multiple_sources(self):
        """Should calculate average score for multiple sources."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        sources = [{"type": "legge"}, {"type": "circolare"}]
        score = hierarchy.calculate_source_score(sources)
        # Average of 1.0 and 0.6 = 0.8
        assert score == pytest.approx(0.8, rel=0.01)

    def test_calculate_source_score_empty_list(self):
        """Should return 0.0 for empty source list."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        score = hierarchy.calculate_source_score([])
        assert score == 0.0

    def test_calculate_source_score_handles_missing_type(self):
        """Should handle sources without type field."""
        from app.services.source_hierarchy import SourceHierarchy

        hierarchy = SourceHierarchy()
        sources = [{"title": "Some doc"}]  # No type field
        score = hierarchy.calculate_source_score(sources)
        assert score == 0.5  # Default weight for unknown
