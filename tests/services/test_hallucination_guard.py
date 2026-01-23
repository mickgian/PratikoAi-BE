"""TDD Tests for DEV-245: Hallucination Guard Service.

Tests for validating law citations in LLM responses against KB context.
"""

import pytest

from app.services.hallucination_guard import (
    CitationValidationResult,
    HallucinationGuard,
    hallucination_guard,
)


class TestCitationExtraction:
    """Tests for extracting law citations from text."""

    def test_extract_legge_with_n(self):
        """Test extracting 'Legge n. X/YYYY' pattern."""
        guard = HallucinationGuard()
        text = "La rottamazione è disciplinata dalla Legge n. 199/2025."
        citations = guard.extract_citations(text)

        assert len(citations) == 1
        assert "Legge n. 199/2025" in citations[0]

    def test_extract_legge_without_n(self):
        """Test extracting 'Legge X/YYYY' pattern."""
        guard = HallucinationGuard()
        text = "Secondo la Legge 197/2022, si applica..."
        citations = guard.extract_citations(text)

        assert len(citations) == 1
        assert "197/2022" in citations[0]

    def test_extract_dlgs_pattern(self):
        """Test extracting 'D.Lgs. X/YYYY' pattern."""
        guard = HallucinationGuard()
        text = "Il D.Lgs. 81/2008 disciplina la sicurezza sul lavoro."
        citations = guard.extract_citations(text)

        assert len(citations) == 1
        assert "81/2008" in citations[0]

    def test_extract_dpr_pattern(self):
        """Test extracting 'DPR X/YYYY' pattern."""
        guard = HallucinationGuard()
        text = "L'IVA è regolata dal DPR 633/72."
        citations = guard.extract_citations(text)

        assert len(citations) == 1
        assert "633/72" in citations[0]

    def test_extract_multiple_citations(self):
        """Test extracting multiple citations from text."""
        guard = HallucinationGuard()
        text = """
        La Legge n. 199/2025 (Legge di Bilancio 2026) introduce la rottamazione quinquies.
        Si applica in deroga al D.Lgs. 46/1999 e al DPR 602/1973.
        """
        citations = guard.extract_citations(text)

        assert len(citations) >= 3
        # Check that key citations are found
        normalized = " ".join(citations).lower()
        assert "199/2025" in normalized
        assert "46/1999" in normalized
        assert "602/1973" in normalized

    def test_extract_no_citations(self):
        """Test extracting from text without citations."""
        guard = HallucinationGuard()
        text = "Buongiorno, come posso aiutarti oggi?"
        citations = guard.extract_citations(text)

        assert len(citations) == 0

    def test_extract_empty_text(self):
        """Test extracting from empty text."""
        guard = HallucinationGuard()
        citations = guard.extract_citations("")

        assert len(citations) == 0

    def test_extract_circolare_pattern(self):
        """Test extracting 'Circolare' pattern."""
        guard = HallucinationGuard()
        text = "Come chiarito dalla Circolare AdE n. 12/E del 2024."
        citations = guard.extract_citations(text)

        assert len(citations) >= 1


class TestCitationValidation:
    """Tests for validating citations against KB context."""

    def test_validate_citation_exists_in_context(self):
        """Test that valid citation is correctly identified."""
        guard = HallucinationGuard()
        response = "La rottamazione è disciplinata dalla Legge n. 199/2025."
        context = "I commi da 231 a 252 della Legge 30 dicembre 2025 n. 199 disciplinano..."

        result = guard.validate_citations(response, context)

        assert len(result.valid_citations) == 1
        assert len(result.hallucinated_citations) == 0
        assert not result.has_hallucinations

    def test_validate_hallucinated_citation(self):
        """Test that hallucinated citation is correctly identified."""
        guard = HallucinationGuard()
        response = "La rottamazione è disciplinata dalla Legge n. 197/2022."
        context = "I commi da 231 a 252 della Legge 30 dicembre 2025 n. 199 disciplinano..."

        result = guard.validate_citations(response, context)

        assert len(result.hallucinated_citations) == 1
        assert "197/2022" in result.hallucinated_citations[0]
        assert result.has_hallucinations

    def test_validate_mixed_citations(self):
        """Test validation with both valid and hallucinated citations."""
        guard = HallucinationGuard()
        response = """
        La Legge n. 199/2025 introduce la rottamazione quinquies.
        In base alla Legge n. 197/2022, erano previste diverse condizioni.
        """
        context = "La Legge n. 199/2025 (Legge di Bilancio 2026) disciplina la definizione agevolata."

        result = guard.validate_citations(response, context)

        assert len(result.valid_citations) == 1
        assert len(result.hallucinated_citations) == 1
        assert result.has_hallucinations
        assert 0 < result.hallucination_rate < 1

    def test_validate_no_citations_in_response(self):
        """Test validation when response has no citations."""
        guard = HallucinationGuard()
        response = "La rottamazione permette di pagare i debiti fiscali a rate."
        context = "La Legge n. 199/2025 disciplina la definizione agevolata."

        result = guard.validate_citations(response, context)

        assert len(result.extracted_citations) == 0
        assert not result.has_hallucinations
        assert result.hallucination_rate == 0.0

    def test_validate_different_format_same_law(self):
        """Test that different formats of the same law are matched."""
        guard = HallucinationGuard()
        response = "La L. 199/2025 introduce nuove disposizioni."
        context = "La Legge n. 199/2025 disciplina la definizione agevolata."

        result = guard.validate_citations(response, context)

        # Both should be recognized as the same law
        assert len(result.hallucinated_citations) == 0, "Same law in different format should not be hallucinated"

    def test_validate_two_digit_year_normalized(self):
        """Test that 2-digit years are normalized to 4-digit."""
        guard = HallucinationGuard()
        response = "Il DPR 633/72 regola l'IVA."
        context = "Come previsto dal DPR 633/1972 sull'imposta sul valore aggiunto."

        result = guard.validate_citations(response, context)

        # "633/72" should match "633/1972"
        assert len(result.hallucinated_citations) == 0


class TestValidationResult:
    """Tests for CitationValidationResult dataclass."""

    def test_result_has_hallucinations_true(self):
        """Test has_hallucinations property when hallucinations exist."""
        result = CitationValidationResult(
            extracted_citations=["Legge 197/2022"],
            valid_citations=[],
            hallucinated_citations=["Legge 197/2022"],
        )

        assert result.has_hallucinations is True

    def test_result_has_hallucinations_false(self):
        """Test has_hallucinations property when no hallucinations."""
        result = CitationValidationResult(
            extracted_citations=["Legge 199/2025"],
            valid_citations=["Legge 199/2025"],
            hallucinated_citations=[],
        )

        assert result.has_hallucinations is False

    def test_result_hallucination_rate(self):
        """Test hallucination_rate calculation."""
        result = CitationValidationResult(
            extracted_citations=["Legge 199/2025", "Legge 197/2022"],
            valid_citations=["Legge 199/2025"],
            hallucinated_citations=["Legge 197/2022"],
        )

        assert result.hallucination_rate == 0.5

    def test_result_hallucination_rate_zero(self):
        """Test hallucination_rate with no citations."""
        result = CitationValidationResult()

        assert result.hallucination_rate == 0.0

    def test_result_to_dict(self):
        """Test to_dict serialization."""
        result = CitationValidationResult(
            extracted_citations=["Legge 199/2025"],
            valid_citations=["Legge 199/2025"],
            hallucinated_citations=[],
            context_citations=["Legge 199/2025"],
        )

        d = result.to_dict()

        assert "extracted_citations" in d
        assert "valid_citations" in d
        assert "hallucinated_citations" in d
        assert "has_hallucinations" in d
        assert "hallucination_rate" in d
        assert d["has_hallucinations"] is False


class TestCorrectionSuggestions:
    """Tests for correction suggestion generation."""

    def test_suggestion_for_hallucinated_citation(self):
        """Test getting correction suggestion for hallucinated citation."""
        guard = HallucinationGuard()
        result = CitationValidationResult(
            extracted_citations=["Legge 197/2022"],
            valid_citations=[],
            hallucinated_citations=["Legge 197/2022"],
            context_citations=["Legge 199/2025"],
        )

        suggestion = guard.get_correction_suggestion(result)

        assert suggestion is not None
        assert "Legge 197/2022" in suggestion
        assert "→" in suggestion

    def test_no_suggestion_when_valid(self):
        """Test no suggestion when all citations are valid."""
        guard = HallucinationGuard()
        result = CitationValidationResult(
            extracted_citations=["Legge 199/2025"],
            valid_citations=["Legge 199/2025"],
            hallucinated_citations=[],
            context_citations=["Legge 199/2025"],
        )

        suggestion = guard.get_correction_suggestion(result)

        assert suggestion is None


class TestSingletonInstance:
    """Tests for the singleton instance."""

    def test_singleton_is_hallucination_guard(self):
        """Test that singleton is a HallucinationGuard instance."""
        assert isinstance(hallucination_guard, HallucinationGuard)

    def test_singleton_can_validate(self):
        """Test that singleton can perform validation."""
        result = hallucination_guard.validate_citations(
            "La Legge 199/2025 è importante.",
            "La Legge 199/2025 disciplina...",
        )

        assert isinstance(result, CitationValidationResult)
        assert not result.has_hallucinations


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_citation_with_comma_article(self):
        """Test handling citations with article/comma references."""
        guard = HallucinationGuard()
        text = "Art. 1, comma 231, Legge 199/2025"
        citations = guard.extract_citations(text)

        # Should extract the law citation
        assert any("199/2025" in c for c in citations)

    def test_legge_di_bilancio_pattern(self):
        """Test extracting 'Legge di Bilancio YYYY' pattern."""
        guard = HallucinationGuard()
        text = "La Legge di Bilancio 2026 introduce nuove misure."
        citations = guard.extract_citations(text)

        assert len(citations) >= 1
        assert any("Bilancio 2026" in c for c in citations)

    def test_case_insensitivity(self):
        """Test that extraction is case-insensitive."""
        guard = HallucinationGuard()
        text = "la LEGGE N. 199/2025 disciplina..."
        citations = guard.extract_citations(text)

        assert len(citations) == 1

    def test_decreto_legislativo_full_form(self):
        """Test extracting full 'Decreto Legislativo' form."""
        guard = HallucinationGuard()
        text = "Il Decreto Legislativo n. 81/2008 sulla sicurezza."
        citations = guard.extract_citations(text)

        assert len(citations) >= 1
        assert any("81/2008" in c for c in citations)
