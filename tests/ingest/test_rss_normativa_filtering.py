"""Tests for Gazzetta Ufficiale relevance filtering in RSS ingestion.

DEV-247: Filter irrelevant Gazzetta Ufficiale content from KB ingestion.

These tests follow TDD - written BEFORE implementation.
"""

import pytest

from app.ingest.rss_normativa import is_relevant_for_pratikoai


class TestIsRelevantForPratikoai:
    """Test cases for the is_relevant_for_pratikoai filtering function."""

    # --- Tax-related documents (should pass filter) ---

    def test_is_relevant_tax_document_tributi(self):
        """Tax documents with 'tribut' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Decreto tributario 2025",
            summary="Nuove disposizioni in materia tributaria",
        )

    def test_is_relevant_tax_document_imposta(self):
        """Tax documents with 'imposta' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Imposta sul reddito delle persone fisiche",
            summary="Modifiche alle aliquote IRPEF",
        )

    def test_is_relevant_tax_document_iva(self):
        """Tax documents with 'IVA' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Aliquote IVA aggiornate",
            summary="Nuove aliquote IVA per beni e servizi",
        )

    def test_is_relevant_tax_document_irpef(self):
        """Tax documents with 'irpef' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="IRPEF 2025: nuove detrazioni",
            summary="",
        )

    def test_is_relevant_tax_document_ires(self):
        """Tax documents with 'ires' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="IRES: modifiche per le imprese",
            summary="",
        )

    def test_is_relevant_tax_document_agevolazioni(self):
        """Tax documents with 'agevolazion' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Agevolazioni fiscali per le startup",
            summary="",
        )

    def test_is_relevant_tax_document_detrazioni(self):
        """Tax documents with 'detrazion' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Detrazioni per ristrutturazioni edilizie",
            summary="",
        )

    # --- Labor-related documents (should pass filter) ---

    def test_is_relevant_labor_document_lavoro(self):
        """Labor documents with 'lavoro' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Normativa sul lavoro a tempo determinato",
            summary="Nuove disposizioni sul lavoro",
        )

    def test_is_relevant_labor_document_pensione(self):
        """Labor documents with 'pensione' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Requisiti per la pensione anticipata",
            summary="",
        )

    def test_is_relevant_labor_document_inps(self):
        """Labor documents with 'inps' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Circolare INPS n. 123/2025",
            summary="",
        )

    def test_is_relevant_labor_document_inail(self):
        """Labor documents with 'inail' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="INAIL: premi assicurativi 2025",
            summary="",
        )

    def test_is_relevant_labor_document_tfr(self):
        """Labor documents with 'tfr' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="TFR: modalita di calcolo",
            summary="",
        )

    def test_is_relevant_labor_document_ccnl(self):
        """Labor documents with 'ccnl' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Rinnovo CCNL metalmeccanici",
            summary="",
        )

    # --- Legal documents (should pass filter) ---

    def test_is_relevant_legal_document_legge(self):
        """Legal documents with 'legge' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="LEGGE 30 dicembre 2025, n. 199",
            summary="Legge di bilancio 2026",
        )

    def test_is_relevant_legal_document_decreto_legge(self):
        """Legal documents with 'decreto-legge' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Decreto-legge 15 gennaio 2025, n. 5",
            summary="",
        )

    def test_is_relevant_legal_document_decreto_legislativo(self):
        """Legal documents with 'decreto legislativo' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Decreto legislativo 9 luglio 1997, n. 241",
            summary="",
        )

    def test_is_relevant_legal_document_circolare(self):
        """Legal documents with 'circolare' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Circolare n. 10/E del 2025",
            summary="",
        )

    def test_is_relevant_legal_document_risoluzione(self):
        """Legal documents with 'risoluzione' keyword should be relevant."""
        assert is_relevant_for_pratikoai(
            title="Risoluzione n. 56/E",
            summary="",
        )

    # --- Irrelevant documents (should be filtered out) ---

    def test_is_irrelevant_concorso(self):
        """Concorso documents should be filtered out."""
        assert not is_relevant_for_pratikoai(
            title="Concorso pubblico per 100 posti di funzionario",
            summary="Bando di concorso per assunzioni",
        )

    def test_is_irrelevant_concorso_variant(self):
        """Concorso documents with 'concorsi' should be filtered out."""
        assert not is_relevant_for_pratikoai(
            title="Concorsi pubblici 2025",
            summary="Elenco dei concorsi banditi",
        )

    def test_is_irrelevant_nomina(self):
        """Nomina documents should be filtered out."""
        assert not is_relevant_for_pratikoai(
            title="Nomina del nuovo direttore generale",
            summary="Decreto di nomina",
        )

    def test_is_irrelevant_nomine_plural(self):
        """Nomine (plural) documents should be filtered out."""
        assert not is_relevant_for_pratikoai(
            title="Nomine dirigenziali",
            summary="Elenco delle nomine",
        )

    def test_is_irrelevant_graduatoria(self):
        """Graduatoria documents should be filtered out."""
        assert not is_relevant_for_pratikoai(
            title="Graduatoria finale del concorso",
            summary="Pubblicazione graduatoria",
        )

    def test_is_irrelevant_bando(self):
        """Bando documents should be filtered out."""
        assert not is_relevant_for_pratikoai(
            title="Bando per mobilita volontaria",
            summary="Avviso pubblico",
        )

    def test_is_irrelevant_avviso(self):
        """Avviso documents should be filtered out."""
        assert not is_relevant_for_pratikoai(
            title="Avviso di selezione pubblica",
            summary="",
        )

    def test_is_irrelevant_estratto(self):
        """Estratto documents should be filtered out."""
        assert not is_relevant_for_pratikoai(
            title="Estratto del verbale di gara",
            summary="",
        )

    # --- Mixed content: whitelist takes precedence over blacklist ---

    def test_mixed_content_whitelist_wins_concorso_tributi(self):
        """Document with both blacklist and whitelist keywords should be kept (whitelist wins)."""
        # A tax-related concorso should be kept because it contains tax keywords
        assert is_relevant_for_pratikoai(
            title="Concorso per funzionari tributari",
            summary="Selezione esperti in materia fiscale",
        )

    def test_mixed_content_whitelist_wins_nomina_lavoro(self):
        """Nomina in labor context should be kept (CCNL is in whitelist)."""
        assert is_relevant_for_pratikoai(
            title="Nomina commissione paritetica CCNL",
            summary="Rinnovo lavoro",
        )

    def test_mixed_content_whitelist_wins_bando_imposta(self):
        """Bando related to tax should be kept."""
        assert is_relevant_for_pratikoai(
            title="Bando per agevolazioni fiscali",
            summary="Incentivi imposta sul reddito",
        )

    # --- Edge cases ---

    def test_empty_title_passes(self):
        """Empty title should pass filter (benefit of doubt)."""
        assert is_relevant_for_pratikoai(title="", summary="")

    def test_none_values_pass(self):
        """None values should be handled gracefully and pass filter."""
        assert is_relevant_for_pratikoai(title=None, summary=None)  # type: ignore

    def test_case_insensitive_uppercase(self):
        """Keyword matching should be case-insensitive (uppercase)."""
        assert is_relevant_for_pratikoai(
            title="TRIBUTI LOCALI 2025",
            summary="IMPOSTA COMUNALE",
        )

    def test_case_insensitive_mixed(self):
        """Keyword matching should be case-insensitive (mixed case)."""
        assert is_relevant_for_pratikoai(
            title="Irpef e Ires: novita",
            summary="",
        )

    def test_case_insensitive_blacklist(self):
        """Blacklist matching should also be case-insensitive."""
        assert not is_relevant_for_pratikoai(
            title="CONCORSO PUBBLICO",
            summary="",
        )

    def test_unicode_characters_accents(self):
        """Should handle Italian accented characters correctly."""
        assert is_relevant_for_pratikoai(
            title="Agevolazioni per attivita imprenditoriali",
            summary="Detrazioni per societa",
        )

    def test_unicode_characters_in_blacklist(self):
        """Should handle accented characters in blacklist terms."""
        assert not is_relevant_for_pratikoai(
            title="Graduatoria definitiva",
            summary="Elenco candidati ammessi",
        )

    def test_partial_keyword_match_tribut(self):
        """'tribut' should match 'tributario', 'tributi', 'tributaria'."""
        assert is_relevant_for_pratikoai(title="Sistema tributario italiano", summary="")
        assert is_relevant_for_pratikoai(title="Tributi locali", summary="")
        assert is_relevant_for_pratikoai(title="Materia tributaria", summary="")

    def test_partial_keyword_match_contribut(self):
        """'contribut' should match 'contributi', 'contributivo', 'contribuzione'."""
        assert is_relevant_for_pratikoai(title="Contributi previdenziali", summary="")
        assert is_relevant_for_pratikoai(title="Sistema contributivo", summary="")

    def test_partial_keyword_match_concors(self):
        """'concors' should match 'concorso', 'concorsi', 'concorsuale'."""
        assert not is_relevant_for_pratikoai(title="Procedura concorsuale", summary="")

    def test_keyword_in_summary_only(self):
        """Keywords in summary should also be detected."""
        assert is_relevant_for_pratikoai(
            title="Documento generico",
            summary="Riguarda le imposte sui redditi",
        )

    def test_blacklist_in_summary_only(self):
        """Blacklist keywords in summary should also be detected."""
        assert not is_relevant_for_pratikoai(
            title="Documento generico",
            summary="Pubblicazione graduatoria finale",
        )

    # --- Real-world examples from Gazzetta Ufficiale ---

    def test_real_example_legge_bilancio(self):
        """Real example: Legge di Bilancio should be relevant."""
        assert is_relevant_for_pratikoai(
            title="LEGGE 30 dicembre 2025, n. 199",
            summary="Bilancio di previsione dello Stato per l'anno finanziario 2026",
        )

    def test_real_example_decreto_lavoro(self):
        """Real example: Decreto-Legge Lavoro should be relevant."""
        assert is_relevant_for_pratikoai(
            title="DECRETO-LEGGE 4 maggio 2023, n. 48",
            summary="Misure urgenti per l'inclusione sociale e l'accesso al mondo del lavoro",
        )

    def test_real_example_concorso_ministero(self):
        """Real example: Concorso Ministero without tax/labor context should be filtered."""
        assert not is_relevant_for_pratikoai(
            title="Concorso pubblico, per titoli ed esami, a 50 posti di funzionario",
            summary="Ministero della Giustizia - Area amministrativa",
        )

    def test_real_example_nomina_direttore(self):
        """Real example: Nomina direttore without tax/labor context should be filtered."""
        assert not is_relevant_for_pratikoai(
            title="Nomina del direttore generale dell'Agenzia",
            summary="Provvedimento di incarico dirigenziale",
        )


class TestFilteringIntegration:
    """Integration tests for filtering in RSS ingestion context."""

    def test_gazzetta_serie_generale_tax_law(self):
        """Serie Generale tax law should pass."""
        assert is_relevant_for_pratikoai(
            title="DECRETO LEGISLATIVO 9 luglio 1997, n. 241",
            summary="Norme di semplificazione degli adempimenti dei contribuenti",
        )

    def test_gazzetta_serie_generale_concorso(self):
        """Serie Generale concorso without tax/labor context should be filtered."""
        assert not is_relevant_for_pratikoai(
            title="Concorso pubblico per 200 posti di personale",
            summary="Area funzionari - profilo informatico",
        )

    def test_gazzetta_corte_costituzionale_relevant(self):
        """Corte Costituzionale ruling on taxes should pass."""
        assert is_relevant_for_pratikoai(
            title="Sentenza della Corte Costituzionale n. 10/2025",
            summary="Illegittimita costituzionale dell'imposta locale",
        )

    def test_document_without_keywords_filtered(self):
        """Documents without any relevant keywords should be filtered."""
        assert not is_relevant_for_pratikoai(
            title="Regolamento sulla tutela ambientale",
            summary="Norme per la protezione delle aree naturali",
        )
