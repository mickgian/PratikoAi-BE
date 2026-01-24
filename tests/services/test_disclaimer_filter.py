"""DEV-245 Phase 5.1: TDD tests for DisclaimerFilter service.

Tests for post-LLM filtering of prohibited disclaimer phrases.
"""

import pytest


class TestDisclaimerFilterBasic:
    """Test basic disclaimer filtering functionality."""

    def test_filter_consult_expert_italian(self):
        """Should remove 'consulta un esperto' and similar phrases."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "L'IRAP può essere inclusa. Per una conferma definitiva, consulta un esperto fiscale."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "consulta un esperto" not in cleaned.lower()
        assert len(removed) > 0
        assert "L'IRAP può essere inclusa" in cleaned

    def test_filter_consult_professional(self):
        """Should remove 'consulta un professionista' variants."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "La scadenza è il 30 aprile. Si consiglia di consultare un professionista per i dettagli."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "consulta" not in cleaned.lower() or "professionista" not in cleaned.lower()
        assert "La scadenza è il 30 aprile" in cleaned

    def test_filter_verify_official_sources(self):
        """Should remove 'verifica sul sito ufficiale' and similar."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "Il termine è prorogato. Per maggiori informazioni, verifica sul sito dell'Agenzia delle Entrate."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "verifica sul sito" not in cleaned.lower()
        assert "Il termine è prorogato" in cleaned

    def test_filter_definitive_confirmation(self):
        """Should remove 'per una conferma definitiva' phrases."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "L'aliquota è del 22%. Per una conferma definitiva sull'applicabilità, consultare fonti ufficiali."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "per una conferma definitiva" not in cleaned.lower()
        assert "L'aliquota è del 22%" in cleaned

    def test_filter_contact_me_phrases(self):
        """Should remove 'non esitare a contattarmi' and similar."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "Ecco le informazioni richieste. Se hai domande, non esitare a contattarmi."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "contattarmi" not in cleaned.lower()
        assert "Ecco le informazioni richieste" in cleaned

    def test_filter_at_your_disposal(self):
        """Should remove 'resto a disposizione' phrases."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "La procedura prevede questi passaggi. Resto a disposizione per ulteriori chiarimenti."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "resto a disposizione" not in cleaned.lower()
        assert "La procedura prevede questi passaggi" in cleaned


class TestDisclaimerFilterEdgeCases:
    """Test edge cases for disclaimer filtering."""

    def test_no_disclaimer_returns_unchanged(self):
        """Text without disclaimers should remain unchanged."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "L'IRAP da dichiarazione è inclusa nella rottamazione quinquies. L'IRAP da accertamento è esclusa."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert cleaned == text
        assert removed == []

    def test_empty_string_returns_empty(self):
        """Empty string should return empty."""
        from app.services.disclaimer_filter import DisclaimerFilter

        cleaned, removed = DisclaimerFilter.filter_response("")
        assert cleaned == ""
        assert removed == []

    def test_multiple_disclaimers_all_removed(self):
        """Should remove multiple disclaimers in same text."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = (
            "L'aliquota è del 22%. Consulta un esperto per dettagli. "
            "La scadenza è il 30 aprile. Per una conferma definitiva, verifica sul sito ufficiale."
        )
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "consulta un esperto" not in cleaned.lower()
        assert "conferma definitiva" not in cleaned.lower()
        assert "verifica sul sito" not in cleaned.lower()
        assert len(removed) >= 2

    def test_preserves_legitimate_content(self):
        """Should preserve content that contains keywords but isn't a disclaimer."""
        from app.services.disclaimer_filter import DisclaimerFilter

        # "professionista" appears but not as "consulta un professionista"
        text = "Il professionista che presenta la dichiarazione deve rispettare i termini."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "professionista" in cleaned
        assert removed == []

    def test_case_insensitive_matching(self):
        """Should match disclaimers regardless of case."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "Info qui. CONSULTA UN ESPERTO per conferma."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "consulta un esperto" not in cleaned.lower()
        assert len(removed) > 0

    def test_handles_newlines_properly(self):
        """Should handle text with newlines."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "Prima riga.\n\nConsulta un esperto fiscale.\n\nTerza riga."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "consulta un esperto" not in cleaned.lower()
        assert "Prima riga" in cleaned
        assert "Terza riga" in cleaned


class TestDisclaimerFilterRealWorldCases:
    """Test with real-world examples from PratikoAI responses."""

    def test_irap_example_from_bug_report(self):
        """Should filter the exact text from the bug report."""
        from app.services.disclaimer_filter import DisclaimerFilter

        # Exact text from the bug report
        text = (
            "L'IRAP può essere inclusa nella rottamazione quinquies se deriva da dichiarazione. "
            "Per una conferma definitiva sull'inclusione dell'IRAP, è consigliabile consultare "
            "fonti ufficiali o un esperto fiscale."
        )
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "per una conferma definitiva" not in cleaned.lower()
        assert "consulta" not in cleaned.lower() or "esperto" not in cleaned.lower()
        assert "L'IRAP può essere inclusa nella rottamazione quinquies" in cleaned
        assert len(removed) > 0

    def test_preserves_valid_tax_content(self):
        """Should preserve all valid fiscal content."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = (
            "✅ Incluso: IRAP da dichiarazione (art. 36-bis DPR 600/1973)\n"
            "❌ Escluso: IRAP da accertamento fiscale\n\n"
            "La scadenza per la domanda è il 30 aprile 2026."
        )
        cleaned, removed = DisclaimerFilter.filter_response(text)

        # No disclaimers should be removed
        assert removed == []
        # All content should be preserved (whitespace may be normalized)
        assert "✅ Incluso: IRAP da dichiarazione" in cleaned
        assert "❌ Escluso: IRAP da accertamento fiscale" in cleaned
        assert "La scadenza per la domanda è il 30 aprile 2026" in cleaned

    def test_rivolgiti_variant(self):
        """Should filter 'rivolgiti a un commercialista' variant."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "Per casi complessi, rivolgiti a un commercialista di fiducia."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "rivolgiti" not in cleaned.lower() or "commercialista" not in cleaned.lower()
