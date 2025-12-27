"""TDD Tests for DEV-193: Verdetto Operativo Output Parser.

Tests for VerdettoOperativoParser per Section 13.8.4.
"""

import pytest

# Sample LLM response with complete Verdetto Operativo
SAMPLE_COMPLETE_RESPONSE = """
Il regime forfettario è disciplinato dalla Legge 190/2014, successivamente modificata.
I requisiti principali riguardano il limite di ricavi/compensi e l'assenza di cause ostative.

In base alla Circolare 9/E del 2025, il limite è stato confermato a €85.000 annui.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        VERDETTO OPERATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ AZIONE CONSIGLIATA
   Verificare il superamento del limite di €85.000 per l'anno fiscale corrente.
   Se in dubbio, mantenere una contabilità ordinaria di riserva.

⚠️ ANALISI DEL RISCHIO
   Il superamento del limite comporta l'uscita dal regime forfettario dall'anno successivo.
   Sanzioni per errata applicazione: dal 100% al 200% dell'imposta evasa.

📅 SCADENZA IMMINENTE
   30/06/2025 - Termine per la dichiarazione dei redditi forfettari

📁 DOCUMENTAZIONE NECESSARIA
   Documenti da conservare per eventuale difesa legale:
   - Fatture emesse con numerazione progressiva
   - Estratti conto bancari
   - Registro degli incassi

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        INDICE DELLE FONTI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| # | Data       | Ente            | Tipo        | Riferimento        |
|---|------------|-----------------|-------------|--------------------|
| 1 | 10/03/2025 | Agenzia Entrate | Circolare   | Circ. 9/E/2025    |
| 2 | 30/12/2024 | Parlamento      | Legge       | L. 234/2024 art.5  |
"""

SAMPLE_PARTIAL_RESPONSE = """
La risposta riguarda il ravvedimento operoso.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        VERDETTO OPERATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ AZIONE CONSIGLIATA
   Procedere con il ravvedimento operoso entro i termini.

📅 SCADENZA IMMINENTE
   Nessuna scadenza critica rilevata
"""

SAMPLE_NO_VERDETTO_RESPONSE = """
Il codice tributo 1040 si utilizza per il versamento delle ritenute d'acconto
operate sui compensi per lavoro autonomo.

La ritenuta standard è del 20% sul compenso lordo.
"""

SAMPLE_MALFORMED_RESPONSE = """
VERDETTO OPERATIVO incomplete
✅ missing proper format
random text here
"""


class TestVerdettoParserSchema:
    """Tests for Verdetto schema classes."""

    def test_fonte_reference_schema_exists(self):
        """Test that FonteReference schema is defined."""
        from app.schemas.verdetto import FonteReference

        fonte = FonteReference(
            numero=1,
            data="10/03/2025",
            ente="Agenzia Entrate",
            tipo="Circolare",
            riferimento="Circ. 9/E/2025",
        )
        assert fonte.numero == 1
        assert fonte.data == "10/03/2025"
        assert fonte.ente == "Agenzia Entrate"

    def test_verdetto_operativo_schema_exists(self):
        """Test that VerdettoOperativo schema is defined."""
        from app.schemas.verdetto import VerdettoOperativo

        verdetto = VerdettoOperativo()
        assert verdetto.azione_consigliata is None
        assert verdetto.analisi_rischio is None
        assert verdetto.scadenza is None
        assert verdetto.documentazione == []
        assert verdetto.indice_fonti == []

    def test_verdetto_operativo_with_values(self):
        """Test VerdettoOperativo with actual values."""
        from app.schemas.verdetto import FonteReference, VerdettoOperativo

        verdetto = VerdettoOperativo(
            azione_consigliata="Test action",
            analisi_rischio="Test risk",
            scadenza="30/06/2025",
            documentazione=["Doc 1", "Doc 2"],
            indice_fonti=[
                FonteReference(
                    numero=1,
                    data="10/03/2025",
                    ente="Test",
                    tipo="Circolare",
                    riferimento="Test ref",
                )
            ],
        )
        assert verdetto.azione_consigliata == "Test action"
        assert len(verdetto.documentazione) == 2
        assert len(verdetto.indice_fonti) == 1

    def test_parsed_synthesis_schema_exists(self):
        """Test that ParsedSynthesis schema is defined."""
        from app.schemas.verdetto import ParsedSynthesis

        parsed = ParsedSynthesis(
            answer_text="Test answer",
            raw_response="Full response",
        )
        assert parsed.answer_text == "Test answer"
        assert parsed.verdetto is None
        assert parsed.raw_response == "Full response"
        assert parsed.parse_successful is True

    def test_parsed_synthesis_with_verdetto(self):
        """Test ParsedSynthesis with verdetto."""
        from app.schemas.verdetto import ParsedSynthesis, VerdettoOperativo

        parsed = ParsedSynthesis(
            answer_text="Test answer",
            verdetto=VerdettoOperativo(azione_consigliata="Test action"),
            raw_response="Full response",
        )
        assert parsed.verdetto is not None
        assert parsed.verdetto.azione_consigliata == "Test action"


class TestVerdettoOperativoParser:
    """Tests for VerdettoOperativoParser class."""

    def _get_parser(self):
        """Get VerdettoOperativoParser instance."""
        from app.services.verdetto_parser import VerdettoOperativoParser

        return VerdettoOperativoParser()

    def test_parser_instantiation(self):
        """Test that VerdettoOperativoParser can be instantiated."""
        parser = self._get_parser()
        assert parser is not None

    def test_parse_returns_parsed_synthesis(self):
        """Test that parse() returns ParsedSynthesis."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        from app.schemas.verdetto import ParsedSynthesis

        assert isinstance(result, ParsedSynthesis)

    def test_parse_complete_verdetto(self):
        """Test parsing a complete verdetto with all sections."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        assert result.verdetto is not None
        assert result.verdetto.azione_consigliata is not None
        assert "€85.000" in result.verdetto.azione_consigliata
        assert result.verdetto.analisi_rischio is not None
        assert "100%" in result.verdetto.analisi_rischio
        assert result.verdetto.scadenza is not None
        assert "30/06/2025" in result.verdetto.scadenza
        assert len(result.verdetto.documentazione) > 0
        assert result.parse_successful is True

    def test_parse_extracts_azione_consigliata(self):
        """Test extraction of AZIONE CONSIGLIATA section."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        assert result.verdetto is not None
        assert result.verdetto.azione_consigliata is not None
        assert "Verificare" in result.verdetto.azione_consigliata

    def test_parse_extracts_analisi_rischio(self):
        """Test extraction of ANALISI DEL RISCHIO section."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        assert result.verdetto is not None
        assert result.verdetto.analisi_rischio is not None
        assert "Sanzioni" in result.verdetto.analisi_rischio

    def test_parse_extracts_scadenza(self):
        """Test extraction of SCADENZA IMMINENTE section."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        assert result.verdetto is not None
        assert result.verdetto.scadenza is not None
        assert "30/06/2025" in result.verdetto.scadenza

    def test_parse_extracts_documentazione(self):
        """Test extraction of DOCUMENTAZIONE NECESSARIA list."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        assert result.verdetto is not None
        assert len(result.verdetto.documentazione) >= 3
        assert any("Fatture" in doc for doc in result.verdetto.documentazione)

    def test_parse_extracts_fonti_table(self):
        """Test extraction of INDICE DELLE FONTI table."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        assert result.verdetto is not None
        assert len(result.verdetto.indice_fonti) == 2
        assert result.verdetto.indice_fonti[0].numero == 1
        assert result.verdetto.indice_fonti[0].data == "10/03/2025"
        assert result.verdetto.indice_fonti[0].ente == "Agenzia Entrate"
        assert result.verdetto.indice_fonti[0].tipo == "Circolare"
        assert result.verdetto.indice_fonti[0].riferimento == "Circ. 9/E/2025"

    def test_parse_partial_verdetto(self):
        """Test parsing a partial verdetto with missing sections."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_PARTIAL_RESPONSE)

        assert result.verdetto is not None
        assert result.verdetto.azione_consigliata is not None
        # Missing sections should be None or empty
        assert result.verdetto.analisi_rischio is None
        assert result.verdetto.scadenza is not None
        assert "Nessuna scadenza" in result.verdetto.scadenza
        assert result.parse_successful is True

    def test_parse_no_verdetto_returns_answer(self):
        """Test that response without verdetto returns answer only."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_NO_VERDETTO_RESPONSE)

        assert result.verdetto is None
        assert result.answer_text is not None
        assert "codice tributo 1040" in result.answer_text
        assert result.parse_successful is True

    def test_graceful_on_malformed(self):
        """Test graceful handling of malformed input."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_MALFORMED_RESPONSE)

        # Should never raise, should return raw text
        assert result is not None
        assert result.raw_response == SAMPLE_MALFORMED_RESPONSE
        assert result.parse_successful is True

    def test_empty_response(self):
        """Test handling of empty response."""
        parser = self._get_parser()
        result = parser.parse("")

        assert result.answer_text == ""
        assert result.verdetto is None
        assert result.raw_response == ""
        assert result.parse_successful is True

    def test_answer_text_extraction(self):
        """Test that text before VERDETTO OPERATIVO is extracted."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        assert result.answer_text is not None
        assert "regime forfettario" in result.answer_text.lower()
        assert "Legge 190/2014" in result.answer_text
        # Verdetto content should NOT be in answer_text
        assert "AZIONE CONSIGLIATA" not in result.answer_text

    def test_scadenza_nessuna(self):
        """Test parsing 'Nessuna scadenza critica rilevata'."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_PARTIAL_RESPONSE)

        assert result.verdetto is not None
        assert result.verdetto.scadenza is not None
        assert "Nessuna scadenza" in result.verdetto.scadenza

    def test_fonti_table_with_multiple_rows(self):
        """Test parsing fonti table with multiple rows."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        assert result.verdetto is not None
        assert len(result.verdetto.indice_fonti) == 2
        # Check second row
        assert result.verdetto.indice_fonti[1].numero == 2
        assert result.verdetto.indice_fonti[1].data == "30/12/2024"
        assert result.verdetto.indice_fonti[1].ente == "Parlamento"

    def test_raw_response_preserved(self):
        """Test that raw_response contains original text."""
        parser = self._get_parser()
        result = parser.parse(SAMPLE_COMPLETE_RESPONSE)

        assert result.raw_response == SAMPLE_COMPLETE_RESPONSE

    def test_whitespace_handling(self):
        """Test that whitespace in sections is handled correctly."""
        response_with_whitespace = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        VERDETTO OPERATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ AZIONE CONSIGLIATA
   Test with extra whitespace

   And multiple lines

⚠️ ANALISI DEL RISCHIO
   Risk analysis text
"""
        parser = self._get_parser()
        result = parser.parse(response_with_whitespace)

        assert result.verdetto is not None
        assert result.verdetto.azione_consigliata is not None
        assert "Test with extra whitespace" in result.verdetto.azione_consigliata


class TestVerdettoParserEdgeCases:
    """Edge case tests for VerdettoOperativoParser."""

    def _get_parser(self):
        """Get parser instance."""
        from app.services.verdetto_parser import VerdettoOperativoParser

        return VerdettoOperativoParser()

    def test_none_input_handled(self):
        """Test that None input is handled gracefully."""
        parser = self._get_parser()
        # Parser should handle None without raising
        result = parser.parse(None)
        assert result is not None
        assert result.parse_successful is True

    def test_only_verdetto_no_answer(self):
        """Test response that is only verdetto without answer text."""
        response = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        VERDETTO OPERATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ AZIONE CONSIGLIATA
   Direct action without preamble
"""
        parser = self._get_parser()
        result = parser.parse(response)

        assert result.verdetto is not None
        # Answer text should be empty or minimal
        assert result.answer_text.strip() == ""

    def test_fonti_table_with_extra_columns(self):
        """Test fonti table parsing with extra or missing columns."""
        response = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        VERDETTO OPERATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ AZIONE CONSIGLIATA
   Test

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        INDICE DELLE FONTI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| # | Data       | Ente    |
|---|------------|---------|
| 1 | 10/03/2025 | Test    |
"""
        parser = self._get_parser()
        result = parser.parse(response)

        # Should handle gracefully even with incomplete table
        assert result.parse_successful is True

    def test_documentazione_single_item(self):
        """Test documentazione list with single item."""
        response = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        VERDETTO OPERATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ AZIONE CONSIGLIATA
   Test action

📁 DOCUMENTAZIONE NECESSARIA
   - Solo questo documento
"""
        parser = self._get_parser()
        result = parser.parse(response)

        assert result.verdetto is not None
        assert len(result.verdetto.documentazione) == 1
        assert "Solo questo documento" in result.verdetto.documentazione[0]

    def test_unicode_and_emojis_preserved(self):
        """Test that Unicode characters and emojis are preserved."""
        response = """
Test con caratteri speciali: àèìòù €100

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        VERDETTO OPERATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ AZIONE CONSIGLIATA
   Pagare €1.000,50 entro il termine
"""
        parser = self._get_parser()
        result = parser.parse(response)

        assert "àèìòù" in result.answer_text
        assert "€100" in result.answer_text
        assert result.verdetto is not None
        assert "€1.000,50" in result.verdetto.azione_consigliata
