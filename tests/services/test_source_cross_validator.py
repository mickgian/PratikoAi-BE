"""Tests for SourceCrossValidator service (DEV-242).

Comprehensive test suite targeting 90%+ coverage of
app/services/source_cross_validator.py (302 lines).

Covers every public and private method:
- SourceValidationResult dataclass
- CrossValidationResult dataclass
- validate_sources: empty KB, empty sources, all matched, none matched,
  partial matched, kb_was_empty flag, requires_web_fallback, is_valid logic
- _validate_single_source: missing ref, ref match, no match, warning text
- _extract_ref_components: article, law_type variants, law_number/year,
  year-only, circolare references, no matches
- _matches_kb_source: direct title match, direct ref match, law number+year,
  article match in title/ref, circolare match, key_topics match, no match
- validate_dates_in_response: suspicious years, grounded years, near-current years
- source_cross_validator singleton instance
"""

import pytest

from app.services.source_cross_validator import (
    CrossValidationResult,
    SourceCrossValidator,
    SourceValidationResult,
    source_cross_validator,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cited(ref: str, **kwargs) -> dict:
    d = {"ref": ref}
    d.update(kwargs)
    return d


def _make_kb(
    title: str = "",
    reference: str = "",
    doc_type: str = "",
    key_topics: list | None = None,
) -> dict:
    d = {
        "title": title,
        "reference": reference,
        "doc_type": doc_type,
    }
    if key_topics is not None:
        d["key_topics"] = key_topics
    return d


@pytest.fixture()
def validator() -> SourceCrossValidator:
    return SourceCrossValidator()


# ===========================================================================
# Dataclass defaults
# ===========================================================================


class TestDataclasses:
    """Tests for SourceValidationResult and CrossValidationResult."""

    def test_source_validation_result_valid(self):
        r = SourceValidationResult(is_valid=True, matched_kb_doc={"title": "X"})
        assert r.is_valid is True
        assert r.matched_kb_doc == {"title": "X"}
        assert r.warning is None

    def test_source_validation_result_invalid(self):
        r = SourceValidationResult(is_valid=False, warning="Not found")
        assert r.is_valid is False
        assert r.warning == "Not found"

    def test_cross_validation_result_defaults(self):
        r = CrossValidationResult(
            is_valid=True,
            validated_sources=[{"ref": "A"}],
            unmatched_sources=[],
        )
        assert r.warnings == []
        assert r.requires_web_fallback is False
        assert r.kb_was_empty is False


# ===========================================================================
# validate_sources
# ===========================================================================


class TestValidateSources:
    """Tests for the main validate_sources method."""

    def test_empty_kb_empty_sources(self, validator):
        """Both empty: valid, kb_was_empty=True, requires_web_fallback."""
        result = validator.validate_sources([], [], None)
        assert result.is_valid is True
        assert result.kb_was_empty is True
        assert result.requires_web_fallback is True
        assert len(result.warnings) >= 1
        assert len(result.validated_sources) == 0
        assert len(result.unmatched_sources) == 0

    def test_empty_kb_with_sources_cited(self, validator):
        """KB empty, sources cited: kb_was_empty=True, all unmatched, but is_valid=True (kb was empty)."""
        cited = [_make_cited("Art. 16 DPR 633/72")]
        result = validator.validate_sources(cited, [], None)
        assert result.kb_was_empty is True
        assert result.requires_web_fallback is True
        # All unmatched but kb was empty so is_valid is True
        assert result.is_valid is True
        assert len(result.unmatched_sources) == 1

    def test_empty_sources_with_kb(self, validator):
        """No sources cited, KB has items: is_valid=False (KB not empty but no citations)."""
        kb = [_make_kb(title="DPR 633/72")]
        result = validator.validate_sources([], kb, None)
        assert result.kb_was_empty is False
        assert result.is_valid is False
        assert len(result.validated_sources) == 0
        assert len(result.unmatched_sources) == 0

    def test_all_sources_matched(self, validator):
        """All cited sources match KB => is_valid=True."""
        cited = [_make_cited("DPR 633/72")]
        kb = [_make_kb(title="DPR 633/72")]
        result = validator.validate_sources(cited, kb, None)
        assert result.is_valid is True
        assert len(result.validated_sources) == 1
        assert len(result.unmatched_sources) == 0
        assert result.requires_web_fallback is False

    def test_no_sources_match_kb_not_empty(self, validator):
        """KB has items but no source matches => is_valid=False."""
        cited = [_make_cited("Legge 123/2020")]
        kb = [_make_kb(title="Completely Unrelated Document")]
        result = validator.validate_sources(cited, kb, None)
        assert result.is_valid is False
        assert len(result.unmatched_sources) == 1
        assert result.requires_web_fallback is True

    def test_partial_match(self, validator):
        """Some sources match, some do not => is_valid=True (not all unmatched)."""
        cited = [
            _make_cited("DPR 633/72"),
            _make_cited("Fantasy Law 999/2099"),
        ]
        kb = [_make_kb(title="DPR 633/72")]
        result = validator.validate_sources(cited, kb, None)
        assert result.is_valid is True
        assert len(result.validated_sources) == 1
        assert len(result.unmatched_sources) == 1

    def test_warnings_for_unmatched(self, validator):
        """Unmatched sources generate warnings."""
        cited = [_make_cited("Unknown Reference")]
        kb = [_make_kb(title="Something Else")]
        result = validator.validate_sources(cited, kb, None)
        assert len(result.warnings) >= 1
        assert any("non trovata" in w for w in result.warnings)

    def test_kb_was_empty_with_none_metadata(self, validator):
        """None passed as kb_sources_metadata treated as empty."""
        # The code checks `not kb_sources_metadata`, so None triggers empty
        result = validator.validate_sources([], None, None)
        assert result.kb_was_empty is True

    def test_response_text_param_accepted(self, validator):
        """response_text is accepted but not used for matching logic in validate_sources."""
        cited = [_make_cited("DPR 633/72")]
        kb = [_make_kb(title="DPR 633/72")]
        result = validator.validate_sources(cited, kb, "Some response text")
        assert result.is_valid is True

    def test_multiple_unmatched_sources_all_generate_warnings(self, validator):
        cited = [
            _make_cited("Unknown A"),
            _make_cited("Unknown B"),
            _make_cited("Unknown C"),
        ]
        kb = [_make_kb(title="Something")]
        result = validator.validate_sources(cited, kb, None)
        # 3 unmatched + potentially truncated warning text
        unmatched_warnings = [w for w in result.warnings if "non trovata" in w]
        assert len(unmatched_warnings) == 3


# ===========================================================================
# _validate_single_source
# ===========================================================================


class TestValidateSingleSource:
    """Tests for _validate_single_source."""

    def test_missing_ref_returns_invalid(self, validator):
        result = validator._validate_single_source({}, [])
        assert result.is_valid is False
        assert result.warning == "Fonte citata senza riferimento"

    def test_empty_ref_returns_invalid(self, validator):
        result = validator._validate_single_source({"ref": ""}, [])
        assert result.is_valid is False
        assert result.warning == "Fonte citata senza riferimento"

    def test_match_found(self, validator):
        source = _make_cited("DPR 633/72")
        kb = [_make_kb(title="DPR 633/72")]
        result = validator._validate_single_source(source, kb)
        assert result.is_valid is True
        assert result.matched_kb_doc is not None

    def test_no_match_found(self, validator):
        source = _make_cited("Unknown Doc")
        kb = [_make_kb(title="Something Else")]
        result = validator._validate_single_source(source, kb)
        assert result.is_valid is False
        assert "non trovata" in result.warning

    def test_warning_truncates_long_ref(self, validator):
        long_ref = "A" * 100
        source = _make_cited(long_ref)
        result = validator._validate_single_source(source, [_make_kb(title="X")])
        # Warning should contain first 50 chars
        assert result.warning is not None
        assert len(result.warning) < len(long_ref) + 50


# ===========================================================================
# _extract_ref_components
# ===========================================================================


class TestExtractRefComponents:
    """Tests for _extract_ref_components."""

    def test_article_extraction(self, validator):
        components = validator._extract_ref_components("Art. 16 DPR 633/72")
        assert components["article"] == "16"

    def test_article_no_dot(self, validator):
        components = validator._extract_ref_components("Art 5 Legge 123/2020")
        assert components["article"] == "5"

    def test_law_type_dpr(self, validator):
        components = validator._extract_ref_components("DPR 633/72")
        assert components["law_type"] == "DPR"

    def test_law_type_dlgs(self, validator):
        components = validator._extract_ref_components("D.Lgs. 196/2003")
        assert "law_type" in components

    def test_law_type_legge(self, validator):
        components = validator._extract_ref_components("Legge 190/2014")
        assert components["law_type"] == "Legge"

    def test_law_type_tuir(self, validator):
        components = validator._extract_ref_components("Art. 2 TUIR")
        assert components["law_type"] == "TUIR"

    def test_law_type_tus(self, validator):
        components = validator._extract_ref_components("TUS art. 10")
        assert components["law_type"] == "TUS"

    def test_law_number_and_year(self, validator):
        components = validator._extract_ref_components("DPR 633/72")
        assert components["law_number"] == "633"
        assert components["year"] == "72"

    def test_law_number_with_n_prefix(self, validator):
        components = validator._extract_ref_components("Legge n. 190/2014")
        assert components["law_number"] == "190"
        assert components["year"] == "2014"

    def test_year_only_no_number(self, validator):
        components = validator._extract_ref_components("Normativa del 2020")
        assert components["year"] == "2020"
        assert "law_number" not in components

    def test_circolare_extraction(self, validator):
        components = validator._extract_ref_components("Circolare n. 12/E del 2020")
        assert components.get("is_circolare") is True
        assert components["circolare_number"] == "12"

    def test_no_matches(self, validator):
        components = validator._extract_ref_components("something generic")
        assert "article" not in components
        assert "law_type" not in components
        assert "law_number" not in components
        assert "year" not in components
        assert components["original"] == "something generic"

    def test_original_always_present(self, validator):
        ref = "Art. 1 DPR 633/72"
        components = validator._extract_ref_components(ref)
        assert components["original"] == ref

    def test_four_digit_year_extraction(self, validator):
        components = validator._extract_ref_components("Legge 234/2021")
        assert components["law_number"] == "234"
        assert components["year"] == "2021"


# ===========================================================================
# _matches_kb_source
# ===========================================================================


class TestMatchesKbSource:
    """Tests for _matches_kb_source."""

    def test_direct_title_match(self, validator):
        ref_components = {"original": "dpr 633/72"}
        kb_source = _make_kb(title="DPR 633/72")
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_direct_reference_match(self, validator):
        ref_components = {"original": "dpr 633/72"}
        kb_source = _make_kb(reference="DPR 633/72")
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_law_number_year_match_in_title(self, validator):
        ref_components = {"original": "qualcosa", "law_number": "633", "year": "72"}
        kb_source = _make_kb(title="Decreto 633/72 sull'IVA")
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_law_number_year_match_in_reference(self, validator):
        ref_components = {"original": "qualcosa", "law_number": "190", "year": "2014"}
        kb_source = _make_kb(reference="L. 190/2014")
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_article_match_in_title(self, validator):
        ref_components = {"original": "something", "article": "16"}
        kb_source = _make_kb(title="Art. 16 del DPR")
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_article_match_in_reference(self, validator):
        ref_components = {"original": "something", "article": "5"}
        kb_source = _make_kb(reference="art 5 comma 3")
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_circolare_match(self, validator):
        ref_components = {
            "original": "something",
            "is_circolare": True,
            "circolare_number": "12",
        }
        kb_source = _make_kb(title="Circolare 12/E", doc_type="circolare")
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_circolare_no_match_wrong_type(self, validator):
        ref_components = {
            "original": "something",
            "is_circolare": True,
            "circolare_number": "12",
        }
        kb_source = _make_kb(title="12", doc_type="legge")
        assert validator._matches_kb_source(ref_components, kb_source) is False

    def test_key_topics_match(self, validator):
        ref_components = {"original": "iva agevolata"}
        kb_source = _make_kb(title="Unrelated", key_topics=["iva agevolata"])
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_key_topics_no_match(self, validator):
        ref_components = {"original": "something else"}
        kb_source = _make_kb(title="Unrelated", key_topics=["iva agevolata"])
        assert validator._matches_kb_source(ref_components, kb_source) is False

    def test_no_match_at_all(self, validator):
        ref_components = {"original": "totally different"}
        kb_source = _make_kb(title="Unrelated Document", reference="Other Ref")
        assert validator._matches_kb_source(ref_components, kb_source) is False

    def test_partial_original_in_title(self, validator):
        """Original ref is a substring of KB title => match."""
        ref_components = {"original": "dpr 633"}
        kb_source = _make_kb(title="Il DPR 633/72 sull'IVA")
        assert validator._matches_kb_source(ref_components, kb_source) is True

    def test_case_insensitive_match(self, validator):
        ref_components = {"original": "legge 190/2014"}
        kb_source = _make_kb(title="LEGGE 190/2014")
        assert validator._matches_kb_source(ref_components, kb_source) is True


# ===========================================================================
# validate_dates_in_response
# ===========================================================================


class TestValidateDatesInResponse:
    """Tests for validate_dates_in_response."""

    def test_no_years_in_response(self, validator):
        warnings = validator.validate_dates_in_response("Nessun anno menzionato.", [], 2024)
        assert warnings == []

    def test_year_grounded_in_kb(self, validator):
        warnings = validator.validate_dates_in_response(
            "La legge del 1972 stabilisce...",
            [_make_kb(title="DPR 633/1972")],
            2024,
        )
        assert warnings == []

    def test_current_year_not_flagged(self, validator):
        warnings = validator.validate_dates_in_response(
            "Nell'anno 2024 le aliquote sono cambiate.",
            [],
            2024,
        )
        assert warnings == []

    def test_next_year_not_flagged(self, validator):
        warnings = validator.validate_dates_in_response(
            "A partire dal 2025 entreranno in vigore...",
            [],
            2024,
        )
        assert warnings == []

    def test_previous_year_not_flagged(self, validator):
        warnings = validator.validate_dates_in_response(
            "Nel 2023 era diverso.",
            [],
            2024,
        )
        assert warnings == []

    def test_suspicious_year_not_in_kb(self, validator):
        warnings = validator.validate_dates_in_response(
            "La norma del 1985 prevede sanzioni.",
            [_make_kb(title="DPR 633/1972")],
            2024,
        )
        assert len(warnings) == 1
        assert "1985" in warnings[0]
        assert "non presente" in warnings[0]

    def test_multiple_suspicious_years(self, validator):
        warnings = validator.validate_dates_in_response(
            "Le norme del 1980 e del 1990 prevedono...",
            [],
            2024,
        )
        assert len(warnings) == 2

    def test_year_in_kb_reference_field(self, validator):
        warnings = validator.validate_dates_in_response(
            "Secondo la legge del 1990...",
            [_make_kb(reference="Legge 1990")],
            2024,
        )
        assert warnings == []

    def test_empty_response(self, validator):
        warnings = validator.validate_dates_in_response("", [], 2024)
        assert warnings == []

    def test_year_near_boundary_2_years_away(self, validator):
        """Year that is 2 away from current => flagged."""
        warnings = validator.validate_dates_in_response(
            "Nell'anno 2022 era in vigore.",
            [],
            2024,
        )
        assert len(warnings) == 1


# ===========================================================================
# Singleton instance
# ===========================================================================


class TestSingletonInstance:
    """Tests for the module-level singleton."""

    def test_module_singleton_exists(self):
        assert source_cross_validator is not None
        assert isinstance(source_cross_validator, SourceCrossValidator)

    def test_singleton_is_usable(self):
        result = source_cross_validator.validate_sources([], [], None)
        assert isinstance(result, CrossValidationResult)


# ===========================================================================
# Edge cases and integration
# ===========================================================================


class TestEdgeCases:
    """Edge cases for comprehensive coverage."""

    def test_source_without_ref_key_at_all(self, validator):
        """Source dict with no ref key => treated as empty ref."""
        result = validator._validate_single_source({"title": "Something"}, [])
        assert result.is_valid is False

    def test_circolare_without_number(self, validator):
        """Circolare pattern but no number doesn't set is_circolare."""
        components = validator._extract_ref_components("Circolare generica")
        assert components.get("is_circolare") is not True or "circolare_number" in components

    def test_ref_with_dl_type(self, validator):
        components = validator._extract_ref_components("D.L. 18/2020")
        assert "law_type" in components

    def test_ref_with_l_dot_type(self, validator):
        components = validator._extract_ref_components("L. 190/2014")
        assert "law_type" in components

    def test_multiple_kb_sources_first_match_wins(self, validator):
        source = _make_cited("DPR 633/72")
        kb = [
            _make_kb(title="Not This"),
            _make_kb(title="DPR 633/72"),
            _make_kb(title="Also DPR 633/72"),
        ]
        result = validator._validate_single_source(source, kb)
        assert result.is_valid is True
        assert result.matched_kb_doc == kb[1]

    def test_validate_sources_with_mixed_valid_invalid(self, validator):
        """Integration test with a realistic mix of sources."""
        cited = [
            _make_cited("Art. 16 DPR 633/72"),
            _make_cited("Legge 190/2014"),
            _make_cited("Fantasia 999/2099"),
        ]
        kb = [
            _make_kb(title="DPR 633/72", reference="Art. 16"),
            _make_kb(title="L. 190/2014"),
        ]
        result = validator.validate_sources(cited, kb, "Risposta di esempio")
        assert result.is_valid is True
        assert len(result.validated_sources) == 2
        assert len(result.unmatched_sources) == 1

    def test_kb_source_with_no_key_topics(self, validator):
        """KB source without key_topics key => empty list, no error."""
        ref_components = {"original": "zzz_unique_ref"}
        kb_source = {"title": "Unrelated Title", "reference": "other ref", "doc_type": "legge"}
        # Should not raise, just return False for no match
        result = validator._matches_kb_source(ref_components, kb_source)
        assert result is False

    def test_extract_ref_year_from_standalone_4_digit(self, validator):
        """Year extracted from standalone 4-digit number when no law_number/year."""
        components = validator._extract_ref_components("Normativa anno 2023")
        assert components["year"] == "2023"

    def test_validate_dates_kb_years_from_both_title_and_reference(self, validator):
        """Years extracted from both title and reference fields of KB sources."""
        warnings = validator.validate_dates_in_response(
            "Norme del 1972 e del 2003.",
            [
                _make_kb(title="DPR 633/1972"),
                _make_kb(reference="D.Lgs. 196/2003"),
            ],
            2024,
        )
        # Both years are grounded in KB
        assert warnings == []
