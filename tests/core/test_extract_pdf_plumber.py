"""Tests for PDF text extraction post-processing (E.12, E.14)."""

import pytest

from app.core.text.extract_pdf_plumber import (
    normalize_ligatures,
    strip_page_numbers,
)


class TestStripPageNumbers:
    """E.12: Tests for page number and running header removal."""

    def test_strip_dash_page_numbers(self):
        """Happy path: '- 15 -' style page numbers are removed."""
        text = "Contenuto della pagina. - 15 - Continua il contenuto dopo il numero."
        result = strip_page_numbers(text)

        assert "- 15 -" not in result
        assert "Contenuto della pagina" in result
        assert "Continua il contenuto" in result

    def test_strip_pagina_pattern(self):
        """'Pagina 1 di 5' style page numbers are removed."""
        text = "Primo paragrafo del documento.\nPagina 1 di 5\nSecondo paragrafo del documento."
        result = strip_page_numbers(text)

        assert "Pagina 1 di 5" not in result
        assert "Primo paragrafo" in result
        assert "Secondo paragrafo" in result

    def test_strip_pag_abbreviation(self):
        """'Pag. 3 di 10' abbreviated form is removed."""
        text = "Contenuto rilevante. Pag. 3 di 10 Altro contenuto."
        result = strip_page_numbers(text)

        assert "Pag. 3 di 10" not in result
        assert "Contenuto rilevante" in result

    def test_strip_gu_running_headers(self):
        """Gazzetta Ufficiale running headers are removed."""
        text = (
            "Gazzetta Ufficiale della Repubblica Italiana\nArt. 1\nLe disposizioni del presente decreto si applicano."
        )
        result = strip_page_numbers(text)

        assert "Gazzetta Ufficiale" not in result
        assert "Art. 1" in result

    def test_strip_serie_generale_header(self):
        """'Serie generale - n. 123' running header is removed."""
        text = "Serie generale - n. 123\nArt. 2\nContenuto dell'articolo."
        result = strip_page_numbers(text)

        assert "Serie generale" not in result
        assert "Art. 2" in result

    def test_preserve_numeric_content(self):
        """Numbers in legal context (penalty amounts, dates) are preserved."""
        text = (
            "La sanzione prevista è pari a euro 15.000 "
            "per ciascuna violazione accertata. "
            "Il termine scade il 15 - 03 - 2024."
        )
        result = strip_page_numbers(text)

        assert "15.000" in result
        assert "15 - 03 - 2024" in result

    def test_strip_standalone_page_number(self):
        """Standalone number on its own line (page number) is removed."""
        text = "Contenuto prima.\n15\nContenuto dopo."
        result = strip_page_numbers(text)

        assert "Contenuto prima" in result
        assert "Contenuto dopo" in result

    def test_no_page_numbers_unchanged(self):
        """Text without page numbers is returned unchanged."""
        text = "Art. 1\nLe disposizioni si applicano a tutti i soggetti."
        result = strip_page_numbers(text)

        assert result == text

    def test_multiple_page_patterns(self):
        """Multiple different page number patterns in same text are all removed."""
        text = "Prima sezione.\n- 1 -\nSeconda sezione.\nPagina 2 di 10\nTerza sezione.\n- 3 -"
        result = strip_page_numbers(text)

        assert "- 1 -" not in result
        assert "Pagina 2 di 10" not in result
        assert "- 3 -" not in result
        assert "Prima sezione" in result
        assert "Seconda sezione" in result
        assert "Terza sezione" in result


class TestNormalizeLigatures:
    """E.14: Tests for PDF ligature normalization."""

    def test_replace_fi_ligature(self):
        """The fi ligature (U+FB01) is replaced with 'fi'."""
        text = "La modi\ufb01ca è stata approvata."
        result = normalize_ligatures(text)

        assert "\ufb01" not in result
        assert "modifica" in result

    def test_replace_fl_ligature(self):
        """The fl ligature (U+FB02) is replaced with 'fl'."""
        text = "Il con\ufb02itto è stato risolto."
        result = normalize_ligatures(text)

        assert "\ufb02" not in result
        assert "conflitto" in result

    def test_replace_ff_ligature(self):
        """The ff ligature (U+FB00) is replaced with 'ff'."""
        text = "L'e\ufb00etto è immediato."
        result = normalize_ligatures(text)

        assert "\ufb00" not in result
        assert "effetto" in result

    def test_replace_ffi_ligature(self):
        """The ffi ligature (U+FB03) is replaced with 'ffi'."""
        text = "L'u\ufb03cio competente."
        result = normalize_ligatures(text)

        assert "\ufb03" not in result
        assert "ufficio" in result

    def test_replace_ffl_ligature(self):
        """The ffl ligature (U+FB04) is replaced with 'ffl'."""
        text = "Il su\ufb04ato arriva."
        result = normalize_ligatures(text)

        assert "\ufb04" not in result
        assert "sufflato" in result

    def test_multiple_ligatures_in_text(self):
        """Multiple different ligatures in same text are all replaced."""
        text = "Modi\ufb01ca e con\ufb02itto nell'u\ufb03cio."
        result = normalize_ligatures(text)

        assert "\ufb01" not in result
        assert "\ufb02" not in result
        assert "\ufb03" not in result
        assert "Modifica" in result
        assert "conflitto" in result
        assert "ufficio" in result

    def test_no_ligatures_unchanged(self):
        """Text without ligatures is returned unchanged."""
        text = "Art. 1 Le disposizioni si applicano."
        result = normalize_ligatures(text)

        assert result == text

    def test_empty_text(self):
        """Empty text returns empty string."""
        assert normalize_ligatures("") == ""
