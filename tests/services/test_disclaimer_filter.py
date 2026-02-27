"""DEV-245 Phase 5.1: TDD tests for DisclaimerFilter service.

Tests for post-LLM filtering of prohibited disclaimer phrases.

DEV-251: Updated tests to verify phrase-only removal (not sentence removal).
"""

import pytest


class TestDisclaimerFilterBasic:
    """Test basic disclaimer filtering functionality."""

    def test_filter_consult_expert_italian(self):
        """Should remove 'consulta un esperto' phrase."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "L'IRAP può essere inclusa. Per una conferma definitiva, consulta un esperto fiscale."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "consulta un esperto" not in cleaned.lower()
        assert len(removed) > 0
        assert "L'IRAP può essere inclusa" in cleaned

    def test_filter_consult_professional(self):
        """Should remove 'si consiglia di consultare' phrase."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "La scadenza è il 30 aprile. Si consiglia di consultare un professionista per i dettagli."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "si consiglia di consultare" not in cleaned.lower()
        assert "La scadenza è il 30 aprile" in cleaned
        assert len(removed) > 0

    def test_filter_verify_official_sources(self):
        """Should remove 'verifica sul sito ufficiale' phrase."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "Il termine è prorogato. Per maggiori informazioni, verifica sul sito dell'Agenzia delle Entrate."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "verifica sul sito" not in cleaned.lower()
        assert "Il termine è prorogato" in cleaned

    def test_filter_definitive_confirmation(self):
        """Should remove 'per una conferma definitiva' phrase."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "L'aliquota è del 22%. Per una conferma definitiva sull'applicabilità, consultare fonti ufficiali."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "per una conferma definitiva" not in cleaned.lower()
        assert "L'aliquota è del 22%" in cleaned
        assert len(removed) > 0

    def test_filter_contact_me_phrases(self):
        """Should remove 'non esitare a contattarmi' and 'se hai domande' phrases."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = "Ecco le informazioni richieste. Se hai domande, non esitare a contattarmi."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "contattarmi" not in cleaned.lower()
        assert "se hai domande" not in cleaned.lower()
        assert "Ecco le informazioni richieste" in cleaned
        assert len(removed) >= 2  # Both phrases should be removed

    def test_filter_at_your_disposal(self):
        """Should remove 'resto a disposizione' phrase."""
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
        """Should filter the exact text from the bug report, preserving most content."""
        from app.services.disclaimer_filter import DisclaimerFilter

        # Exact text from the bug report
        text = (
            "L'IRAP può essere inclusa nella rottamazione quinquies se deriva da dichiarazione. "
            "Per una conferma definitiva sull'inclusione dell'IRAP, è consigliabile consultare "
            "fonti ufficiali o un esperto fiscale."
        )
        cleaned, removed = DisclaimerFilter.filter_response(text)

        assert "per una conferma definitiva" not in cleaned.lower()
        assert "è consigliabile consultare" not in cleaned.lower()
        assert "L'IRAP può essere inclusa nella rottamazione quinquies" in cleaned
        # DEV-251: Should preserve most of the content, only removing phrases
        assert "IRAP" in cleaned
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


class TestDisclaimerFilterFormattingPreservation:
    """DEV-250: Test that filtering preserves markdown formatting."""

    def test_filter_preserves_markdown_formatting(self):
        """DEV-250: Ensure filtering doesn't destroy markdown line breaks."""
        from app.services.disclaimer_filter import DisclaimerFilter

        formatted_response = """1. **Definizione**: La rottamazione è...

2. **Requisiti**: I contribuenti devono...

- Primo punto
- Secondo punto"""

        filtered, removed = DisclaimerFilter.filter_response(formatted_response)

        # Newlines should be preserved - no disclaimers to remove
        assert "\n\n" in filtered
        assert "1. **Definizione**" in filtered
        assert "2. **Requisiti**" in filtered
        assert removed == []

    def test_filter_preserves_newlines_after_disclaimer_removal(self):
        """DEV-250: Newlines should be preserved even after removing disclaimers."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = """1. **Primo punto**: Contenuto valido.

2. **Secondo punto**: Altro contenuto. Consulta un esperto fiscale.

3. **Terzo punto**: Ancora contenuto."""

        filtered, removed = DisclaimerFilter.filter_response(text)

        # Disclaimer should be removed
        assert "consulta un esperto" not in filtered.lower()
        assert len(removed) > 0

        # But paragraph structure should be preserved
        assert "1. **Primo punto**" in filtered
        assert "3. **Terzo punto**" in filtered
        # There should still be paragraph breaks (double newlines)
        assert "\n" in filtered

    def test_filter_preserves_bullet_list_structure(self):
        """DEV-250: Bullet lists should maintain their line break structure."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = """Ecco i requisiti:

- Requisito uno
- Requisito due
- Requisito tre

Conclusione finale."""

        filtered, removed = DisclaimerFilter.filter_response(text)

        # No disclaimers, structure should be fully preserved
        assert "- Requisito uno\n- Requisito due\n- Requisito tre" in filtered
        assert removed == []

    def test_only_collapses_multiple_spaces_not_newlines(self):
        """DEV-250: Multiple spaces should collapse, but not newlines."""
        from app.services.disclaimer_filter import DisclaimerFilter

        # Text with multiple spaces (should collapse) and newlines (should preserve)
        text = "Prima  riga   con   spazi.\n\nSeconda riga."

        filtered, removed = DisclaimerFilter.filter_response(text)

        # Multiple spaces collapsed to single space
        assert "Prima riga con spazi." in filtered
        # Double newline preserved
        assert "\n\n" in filtered
        assert "Seconda riga." in filtered


class TestDisclaimerFilterPhraseOnlyRemoval:
    """DEV-251: Test that only phrases are removed, not entire sentences."""

    def test_removes_only_phrase_not_sentence(self):
        """DEV-251: Should remove only the disclaimer phrase, preserving rest of sentence."""
        from app.services.disclaimer_filter import DisclaimerFilter

        # A sentence with a disclaimer phrase in the middle and substantial other content
        text = "La risposta è complessa. Per una conferma definitiva ti consiglio di leggere l'articolo 5."
        cleaned, removed = DisclaimerFilter.filter_response(text)

        # Phrase removed
        assert "per una conferma definitiva" not in cleaned.lower()
        # But key content preserved
        assert "La risposta è complessa" in cleaned
        assert "articolo 5" in cleaned
        assert len(removed) > 0

    def test_preserves_content_length_after_filtering(self):
        """DEV-251: Filtering should remove minimal content from long responses."""
        from app.services.disclaimer_filter import DisclaimerFilter

        # A long response with one disclaimer phrase (small % of total)
        text = (
            "La rottamazione quinquies permette di definire i debiti tributari. "
            "I requisiti sono i seguenti:\n"
            "1. Debiti affidati entro il 31 dicembre 2023\n"
            "2. Importo massimo di 1000 euro per singolo carico\n\n"
            "Per una conferma definitiva, si prega di verificare.\n\n"
            "Le scadenze sono:\n"
            "- Prima rata: 31 luglio 2024\n"
            "- Seconda rata: 30 novembre 2024"
        )
        original_length = len(text)
        cleaned, removed = DisclaimerFilter.filter_response(text)
        cleaned_length = len(cleaned)

        # Phrase should be removed
        assert "per una conferma definitiva" not in cleaned.lower()
        assert len(removed) > 0

        # Most content should be preserved (at least 85% since disclaimer is small)
        assert cleaned_length >= original_length * 0.85, (
            f"Too much content removed: {original_length} -> {cleaned_length} "
            f"({round((1 - cleaned_length / original_length) * 100, 1)}% removed)"
        )

        # All important content should still be present
        assert "rottamazione quinquies" in cleaned
        assert "31 dicembre 2023" in cleaned
        assert "31 luglio 2024" in cleaned
        assert "30 novembre 2024" in cleaned

    def test_multiple_phrases_removes_only_phrases(self):
        """DEV-251: Multiple phrases should each be removed, leaving other content."""
        from app.services.disclaimer_filter import DisclaimerFilter

        text = (
            "Ecco la risposta dettagliata.\n\n"
            "1. Primo punto importante con dettagli utili sulla normativa.\n"
            "2. Secondo punto cruciale con informazioni aggiuntive.\n"
            "3. Terzo punto conclusivo con note finali."
        )
        original_length = len(text)
        cleaned, removed = DisclaimerFilter.filter_response(text)
        cleaned_length = len(cleaned)

        # No disclaimer phrases in this text
        assert removed == []
        # All content preserved
        assert cleaned_length == original_length or cleaned == text.strip()

        # Key content preserved
        assert "Primo punto importante" in cleaned
        assert "Secondo punto cruciale" in cleaned
        assert "Terzo punto conclusivo" in cleaned

    def test_large_response_minimal_impact(self):
        """DEV-251: A 2000+ char response should stay mostly intact."""
        from app.services.disclaimer_filter import DisclaimerFilter

        # Simulate a real 2000+ char response with one disclaimer at the end
        text = """La rottamazione quinquies è una definizione agevolata prevista dalla legge di bilancio 2025.

## Requisiti di ammissibilità

Per poter aderire alla rottamazione quinquies, è necessario soddisfare i seguenti requisiti:

1. **Debiti tributari**: I debiti devono essere stati affidati all'Agente della riscossione entro il 31 dicembre 2023.

2. **Tipologia di debiti**: Sono ammessi i seguenti tipi di debiti:
   - Imposte sui redditi (IRPEF, IRES)
   - IVA
   - IRAP da dichiarazione
   - Contributi previdenziali

3. **Importi**: Non vi è un limite massimo per l'importo da rottamare.

## Vantaggi della rottamazione

Aderendo alla rottamazione si ottengono i seguenti benefici:
- Stralcio integrale delle sanzioni
- Stralcio degli interessi di mora
- Possibilità di rateizzare in 18 rate

## Scadenze importanti

Le date chiave sono:
- **Domanda**: entro il 30 aprile 2025
- **Prima rata**: 31 luglio 2025
- **Rate successive**: ogni 3 mesi

Per una conferma definitiva ti consiglio di verificare con le fonti ufficiali.

## Conclusione

La rottamazione quinquies rappresenta un'opportunità significativa per regolarizzare la propria posizione fiscale."""

        original_length = len(text)
        cleaned, removed = DisclaimerFilter.filter_response(text)
        cleaned_length = len(cleaned)

        # Should preserve >95% (only one small phrase removed)
        assert (
            cleaned_length >= original_length * 0.95
        ), f"Response too short: {cleaned_length} chars (was {original_length})"

        # Key structure preserved
        assert "## Requisiti di ammissibilità" in cleaned
        assert "## Vantaggi della rottamazione" in cleaned
        assert "## Scadenze importanti" in cleaned
        assert "## Conclusione" in cleaned

        # Disclaimer removed
        assert "per una conferma definitiva" not in cleaned.lower()


class TestDisclaimerFilterLogging:
    """DEV-251: Test logging behavior."""

    def test_logs_removal_stats(self, caplog):
        """DEV-251: Should log removal statistics."""
        import logging

        from app.services.disclaimer_filter import DisclaimerFilter

        caplog.set_level(logging.INFO)

        text = "Risposta importante. Per una conferma definitiva, verifica le fonti."
        DisclaimerFilter.filter_response(text)

        # Check that info log was emitted (we can check caplog.records)
        # Note: structlog may not appear in caplog depending on configuration
        # This test verifies the code path executes without error
