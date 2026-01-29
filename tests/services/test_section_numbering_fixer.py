"""DEV-250: TDD tests for SectionNumberingFixer service.

Tests for post-LLM fixing of repeated section numbering in markdown responses.
"""

import pytest


class TestSectionNumberingFixerBasic:
    """Test basic section numbering fix functionality."""

    def test_fixes_repeated_h2_numbers(self):
        """## 1., ## 1., ## 1. → ## 1., ## 2., ## 3."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """## 1. Tipologie di Debiti

Contenuto primo paragrafo.

## 1. Benefici

Contenuto secondo paragrafo.

## 1. Modalità di Pagamento

Contenuto terzo paragrafo.

## 1. Scadenza

Contenuto quarto paragrafo."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "## 1. Tipologie di Debiti" in fixed
        assert "## 2. Benefici" in fixed
        assert "## 3. Modalità di Pagamento" in fixed
        assert "## 4. Scadenza" in fixed
        # Verify old repeated numbers are gone
        assert fixed.count("## 1.") == 1

    def test_fixes_repeated_h3_numbers(self):
        """### 1., ### 1. → ### 1., ### 2."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """### 1. Prima Sottosezione

Contenuto.

### 1. Seconda Sottosezione

Altro contenuto."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "### 1. Prima Sottosezione" in fixed
        assert "### 2. Seconda Sottosezione" in fixed
        assert fixed.count("### 1.") == 1

    def test_preserves_correct_numbering(self):
        """Already sequential numbers should not change."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """## 1. Prima Sezione

Contenuto.

## 2. Seconda Sezione

Altro contenuto.

## 3. Terza Sezione

Ultimo contenuto."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        # Should remain unchanged
        assert "## 1. Prima Sezione" in fixed
        assert "## 2. Seconda Sezione" in fixed
        assert "## 3. Terza Sezione" in fixed

    def test_handles_mixed_content(self):
        """Numbered sections with paragraphs between them."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """Introduzione al documento.

## 1. Prima Parte

Questo è il contenuto della prima parte.
Con più righe.

- Punto uno
- Punto due

## 1. Seconda Parte

Questo è il contenuto della seconda parte.

## 1. Terza Parte

Conclusione finale."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "## 1. Prima Parte" in fixed
        assert "## 2. Seconda Parte" in fixed
        assert "## 3. Terza Parte" in fixed
        # Preserve other content
        assert "Introduzione al documento." in fixed
        assert "- Punto uno" in fixed
        assert "- Punto due" in fixed


class TestSectionNumberingFixerEdgeCases:
    """Test edge cases for section numbering fix."""

    def test_empty_string_returns_empty(self):
        """Edge case: empty input."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        result = SectionNumberingFixer.fix_numbering("")
        assert result == ""

    def test_none_returns_none(self):
        """Edge case: None input."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        result = SectionNumberingFixer.fix_numbering(None)
        assert result is None

    def test_no_sections_returns_unchanged(self):
        """Text without numbered sections should remain unchanged."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = "Questo è un paragrafo semplice senza sezioni numerate."
        fixed = SectionNumberingFixer.fix_numbering(text)

        assert fixed == text

    def test_preserves_non_numbered_headers(self):
        """Headers without numbers should not be affected."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """## Introduzione

Contenuto.

## Conclusione

Altro contenuto."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "## Introduzione" in fixed
        assert "## Conclusione" in fixed

    def test_preserves_h1_headers(self):
        """H1 headers (single #) should not be affected."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """# 1. Main Title

## 1. First Section

Content.

## 1. Second Section

More content."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        # H1 should be preserved as-is
        assert "# 1. Main Title" in fixed
        # H2 sections should be fixed
        assert "## 1. First Section" in fixed
        assert "## 2. Second Section" in fixed

    def test_mixed_h2_and_h3(self):
        """H2 and H3 should have independent counters."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """## 1. Prima Sezione H2

### 1. Prima Sottosezione

### 1. Seconda Sottosezione

## 1. Seconda Sezione H2

### 1. Terza Sottosezione"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        # H2 counter: 1, 2
        assert "## 1. Prima Sezione H2" in fixed
        assert "## 2. Seconda Sezione H2" in fixed
        # H3 counter: 1, 2, 3 (continues across H2 sections)
        assert "### 1. Prima Sottosezione" in fixed
        assert "### 2. Seconda Sottosezione" in fixed
        assert "### 3. Terza Sottosezione" in fixed


class TestSectionNumberingFixerRealWorld:
    """Test with real-world examples from PratikoAI responses."""

    def test_rottamazione_quinquies_example(self):
        """DEV-250: Fix the exact pattern from the bug report."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """La Rottamazione Quinquies è una misura di definizione agevolata.

## 1. Tipologie di Debiti

Sono inclusi debiti IRPEF, IVA, IRAP da dichiarazione...

## 1. Benefici

I benefici includono l'annullamento di sanzioni e interessi di mora...

## 1. Modalità di Pagamento

È possibile pagare in un'unica soluzione o ratealmente...

## 1. Scadenza

La scadenza per la presentazione della domanda è il 30 aprile 2026."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        # Verify sequential numbering
        assert "## 1. Tipologie di Debiti" in fixed
        assert "## 2. Benefici" in fixed
        assert "## 3. Modalità di Pagamento" in fixed
        assert "## 4. Scadenza" in fixed

        # Verify content is preserved
        assert "La Rottamazione Quinquies" in fixed
        assert "30 aprile 2026" in fixed

    def test_preserves_inline_numbers(self):
        """Numbers in text (not headers) should not be affected."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """## 1. Scadenze Importanti

1. Prima scadenza: 30 aprile
2. Seconda scadenza: 31 luglio
3. Terza scadenza: 30 novembre

## 1. Aliquote

L'aliquota è del 22%."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        # Headers should be fixed
        assert "## 1. Scadenze Importanti" in fixed
        assert "## 2. Aliquote" in fixed

        # Inline numbered lists should be preserved
        assert "1. Prima scadenza: 30 aprile" in fixed
        assert "2. Seconda scadenza: 31 luglio" in fixed
        assert "3. Terza scadenza: 30 novembre" in fixed

    def test_preserves_other_numbered_patterns(self):
        """Other number patterns (like dates, amounts) should not be affected."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """## 1. Importi

L'importo minimo è € 1.000,00.
La data limite è il 1. gennaio 2026.

## 1. Procedure

Articolo 1. comma 2 del decreto."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        # Headers fixed
        assert "## 1. Importi" in fixed
        assert "## 2. Procedure" in fixed

        # Other numbers preserved
        assert "€ 1.000,00" in fixed
        assert "1. gennaio 2026" in fixed
        assert "Articolo 1. comma 2" in fixed


class TestPlainNumberedLists:
    """Test plain numbered list format (1. Title instead of ## 1. Title)."""

    def test_fixes_repeated_plain_numbers(self):
        """1., 1., 1., 1. → 1., 2., 3., 4."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1. Tipologie di Debiti
Content here.

1. Benefici per il Contribuente
More content.

1. Modalità di Pagamento
Even more.

1. Scadenza
Final content."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. Tipologie" in fixed
        assert "2. Benefici" in fixed
        assert "3. Modalità" in fixed
        assert "4. Scadenza" in fixed

    def test_rottamazione_quinquies_real_example(self):
        """DEV-250: Fix the exact format from screenshots."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """La Rottamazione Quinquies è una misura di definizione agevolata.

1. Tipologie di Debiti:
Sono inclusi debiti IRPEF, IVA, IRAP da dichiarazione...

1. Benefici per il Contribuente:
I benefici includono l'annullamento di sanzioni...

1. Modalità di Pagamento:
È possibile pagare in un'unica soluzione o ratealmente...

1. Scadenza per la Presentazione della Domanda:
La scadenza è il 30 aprile 2026."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. Tipologie di Debiti:" in fixed
        assert "2. Benefici per il Contribuente:" in fixed
        assert "3. Modalità di Pagamento:" in fixed
        assert "4. Scadenza per la Presentazione della Domanda:" in fixed

    def test_preserves_lowercase_numbered_items(self):
        """Don't renumber regular list items (lowercase start)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1. First Section

Some content with list:
1. first item
2. second item
3. third item

1. Second Section"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        # Section headers should be renumbered
        assert "1. First Section" in fixed
        assert "2. Second Section" in fixed
        # Lowercase list items should be preserved as-is
        assert "1. first item" in fixed
        assert "2. second item" in fixed

    def test_bold_numbered_sections(self):
        """**1.** Title format should also be fixed."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """**1.** Prima Sezione

Contenuto.

**1.** Seconda Sezione

Altro contenuto."""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "**1.** Prima Sezione" in fixed
        assert "**2.** Seconda Sezione" in fixed

    def test_bold_prefixed_sections(self):
        """1. **Title** format from real LLM output (DEV-250 iteration 3)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1.   **Ambito di Applicazione**: content

1.   **Benefici per il Contribuente**: more content

1.   **Modalità di Pagamento**: even more"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. **Ambito" in fixed
        assert "2. **Benefici" in fixed
        assert "3. **Modalità" in fixed


class TestAllEmphasisFormats:
    """DEV-250: Test ALL markdown emphasis formats to ensure comprehensive support."""

    def test_fixes_underscore_bold_sections(self):
        """__Title__ format (underscore bold)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1. __Ambito di Applicazione__: content here

1. __Benefici per il Contribuente__: more content

1. __Modalità di Pagamento__: even more"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. __Ambito" in fixed
        assert "2. __Benefici" in fixed
        assert "3. __Modalità" in fixed

    def test_fixes_asterisk_bold_sections(self):
        """**Title** format (asterisk bold)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1. **Ambito di Applicazione**: content here

1. **Benefici per il Contribuente**: more content

1. **Modalità di Pagamento**: even more"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. **Ambito" in fixed
        assert "2. **Benefici" in fixed
        assert "3. **Modalità" in fixed

    def test_fixes_underscore_italic_sections(self):
        """_Title_ format (underscore italic)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1. _Ambito di Applicazione_: content

1. _Benefici per il Contribuente_: more

1. _Modalità di Pagamento_: even more"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. _Ambito" in fixed
        assert "2. _Benefici" in fixed
        assert "3. _Modalità" in fixed

    def test_fixes_asterisk_italic_sections(self):
        """*Title* format (asterisk italic)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1. *Ambito di Applicazione*: content

1. *Benefici per il Contribuente*: more

1. *Modalità di Pagamento*: even more"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. *Ambito" in fixed
        assert "2. *Benefici" in fixed
        assert "3. *Modalità" in fixed

    def test_fixes_plain_sections_no_emphasis(self):
        """Plain Title format (no emphasis)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1. Ambito di Applicazione: content

1. Benefici per il Contribuente: more

1. Modalità di Pagamento: even more"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. Ambito" in fixed
        assert "2. Benefici" in fixed
        assert "3. Modalità" in fixed

    def test_mixed_emphasis_formats(self):
        """Mix of different emphasis formats in same response."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1. **Prima Sezione**: bold asterisk

1. __Seconda Sezione__: bold underscore

1. _Terza Sezione_: italic underscore

1. Quarta Sezione: plain text"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. **Prima" in fixed
        assert "2. __Seconda" in fixed
        assert "3. _Terza" in fixed
        assert "4. Quarta" in fixed


class TestInlineBoldNumberedSections:
    """DEV-250: Test inline bold numbered sections (not at line start)."""

    def test_preserves_already_correct_inline_numbering(self):
        """LLM output with correct 1,2,3,4 numbering should be preserved unchanged."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # Exact format from OpenAI logs - already correctly numbered
        text = (
            "La Rottamazione Quinquies è una misura. "
            "Ecco i punti principali: 1. **Ambito di Applicazione**: content "
            "2. **Benefici per il Contribuente**: more content "
            "3. **Modalità di Pagamento**: payment info "
            "4. **Scadenza per la Presentazione della Domanda**: deadline info"
        )

        fixed = SectionNumberingFixer.fix_numbering(text)

        # Should preserve correct numbering (not change anything)
        assert "1. **Ambito" in fixed
        assert "2. **Benefici" in fixed
        assert "3. **Modalità" in fixed
        assert "4. **Scadenza" in fixed
        # Verify only one of each number
        assert fixed.count("1. **") == 1
        assert fixed.count("2. **") == 1
        assert fixed.count("3. **") == 1
        assert fixed.count("4. **") == 1

    def test_inline_bold_numbered_sections_after_colon(self):
        """Fix inline sections like 'principali: 1. **Ambito' (after colon)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = (
            "Ecco i dettagli principali: 1. **Ambito di Applicazione**: content "
            "1. **Benefici per il Contribuente**: more "
            "1. **Modalità di Pagamento**: stuff "
            "1. **Scadenza**: end"
        )

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. **Ambito" in fixed
        assert "2. **Benefici" in fixed
        assert "3. **Modalità" in fixed
        assert "4. **Scadenza" in fixed
        # Original context preserved
        assert "Ecco i dettagli principali:" in fixed

    def test_inline_bold_numbered_sections_after_space(self):
        """Fix inline sections after regular space (not colon)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = "Here are the sections 1. **First Section**: content " "1. **Second Section**: more content"

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. **First" in fixed
        assert "2. **Second" in fixed

    def test_inline_bold_sections_real_llm_output(self):
        """DEV-250: Fix the exact format from debug logs."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # Exact format from logs: sections appear inline after colon
        text = (
            "La Rottamazione Quinquies è una misura di definizione agevolata. "
            "Ecco i dettagli principali: 1. **Ambito di Applicazione**: "
            "La rottamazione quinquies riguarda i carichi affidati... "
            "1. **Benefici per il Contribuente**: I principali vantaggi... "
            "1. **Modalità di Pagamento**: È possibile pagare in un'unica... "
            "1. **Scadenza per la Presentazione della Domanda**: La domanda..."
        )

        fixed = SectionNumberingFixer.fix_numbering(text)

        # All 4 sections should be sequentially numbered
        assert "1. **Ambito di Applicazione**" in fixed
        assert "2. **Benefici per il Contribuente**" in fixed
        assert "3. **Modalità di Pagamento**" in fixed
        assert "4. **Scadenza per la Presentazione della Domanda**" in fixed
        # Only one "1. **" should remain
        assert fixed.count("1. **") == 1

    def test_does_not_affect_line_start_bold_sections(self):
        """Line-start bold sections should still work (handled by PLAIN_LIST_PATTERN)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = """1. **Ambito di Applicazione**: content

1. **Benefici per il Contribuente**: more

1. **Modalità di Pagamento**: even more"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        assert "1. **Ambito" in fixed
        assert "2. **Benefici" in fixed
        assert "3. **Modalità" in fixed

    def test_does_not_match_plain_inline_numbers(self):
        """Plain inline numbers (without bold) should NOT be renumbered."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        text = "The steps are: 1. first step 1. second step 1. third step"

        fixed = SectionNumberingFixer.fix_numbering(text)

        # Should remain unchanged (no bold markers)
        assert fixed == text


class TestSectionNumberingFixerIntegration:
    """Test integration with response processing pipeline."""

    def test_works_after_disclaimer_filter(self):
        """Should work correctly on text that has already been disclaimer-filtered."""
        from app.services.disclaimer_filter import DisclaimerFilter
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # Simulate LLM response with disclaimer at end (common case)
        text = """## 1. Requisiti

I requisiti sono i seguenti.

## 1. Benefici

I benefici includono varie agevolazioni.

## 1. Scadenze

La scadenza è il 30 aprile. Consulta un esperto per dettagli."""

        # Apply disclaimer filter first
        filtered, removed = DisclaimerFilter.filter_response(text)

        # Then apply section numbering fix
        fixed = SectionNumberingFixer.fix_numbering(filtered)

        # Both fixes should be applied
        assert len(removed) > 0
        assert "consulta un esperto" not in fixed.lower()
        assert "## 1. Requisiti" in fixed
        assert "## 2. Benefici" in fixed
        assert "## 3. Scadenze" in fixed
        # Core content preserved
        assert "La scadenza è il 30 aprile" in fixed


class TestNoDoubleProcessing:
    """DEV-250: Tests to ensure no double-processing between INLINE and PLAIN_LIST patterns."""

    def test_no_double_processing_with_newlines(self):
        """Sections on separate lines should NOT match INLINE pattern.

        Bug: INLINE_BOLD_SECTION_PATTERN used \\s which matches newlines,
        causing sections at line start to be matched by BOTH patterns.
        Fix: Use [ \\t] instead of \\s to only match space/tab, not newlines.
        """
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # LLM output with sections on separate lines (newlines between)
        text = """Ecco i punti principali:

1. **Ambito di Applicazione**: content

1. **Benefici per il Contribuente**: more

1. **Modalità di Pagamento**: stuff

1. **Scadenza**: end"""

        fixed = SectionNumberingFixer.fix_numbering(text)

        # Should be fixed to sequential numbering (NOT corrupted by double-processing)
        assert "1. **Ambito" in fixed
        assert "2. **Benefici" in fixed
        assert "3. **Modalità" in fixed
        assert "4. **Scadenza" in fixed
        # Verify only one "1. **" exists (no double-processing corruption)
        assert fixed.count("1. **") == 1

    def test_inline_pattern_does_not_match_line_start(self):
        """INLINE pattern should only match after space/tab, not at line start."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # Line-start sections should be handled by PLAIN_LIST_PATTERN only
        text = """1. **First Section**: content
1. **Second Section**: more"""

        # Get the pattern to verify it doesn't match line-start
        pattern = SectionNumberingFixer.INLINE_BOLD_SECTION_PATTERN
        matches = list(pattern.finditer(text))

        # INLINE pattern should NOT match line-start sections
        # (they should only be matched by PLAIN_LIST_PATTERN)
        assert len(matches) == 0, f"INLINE pattern incorrectly matched line-start: {matches}"

    def test_inline_pattern_matches_after_colon_or_space(self):
        """INLINE pattern should correctly match after colon or space (not newline)."""
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # Inline text (sections after colon on same line)
        text = "Ecco i punti: 1. **Ambito**: content 1. **Benefici**: more"

        pattern = SectionNumberingFixer.INLINE_BOLD_SECTION_PATTERN
        matches = list(pattern.finditer(text))

        # Should match both inline sections
        assert len(matches) == 2


class TestDatabasePersistenceFix:
    """DEV-250: Tests for database persistence fix - ensure cleaned content is saved."""

    def test_rottamazione_quinquies_full_inline_response(self):
        """DEV-250: Test exact LLM output format - inline numbered sections.

        This is the exact format that was causing "1, 1, 1, 1" after page refresh.
        The sections appear inline (not at line start) after introductory text.
        """
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # Exact format from user's LLM response (all sections on same line)
        broken = (
            "La Rottamazione Quinquies è una misura introdotta dalla Legge n. 199/2025. "
            "Ecco i dettagli principali: 1. **Ambito di applicazione**: content here "
            "1. **Benefici per il contribuente**: more content "
            "1. **Modalità di pagamento**: payment info "
            "1. **Scadenza per la domanda**: deadline info"
        )

        fixed = SectionNumberingFixer.fix_numbering(broken)

        # All 4 sections should be sequentially numbered
        assert fixed.count("1. **") == 1
        assert "2. **Benefici" in fixed
        assert "3. **Modalità" in fixed
        assert "4. **Scadenza" in fixed

    def test_cleaned_content_for_database_save(self):
        """DEV-250: Verify the full pipeline produces correct content for database.

        This simulates what chatbot.py should save to the database after applying
        both SectionNumberingFixer and clean_proactivity_content.
        """
        from app.core.utils.xml_stripper import clean_proactivity_content
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # Simulate LLM response with broken numbering
        llm_response = (
            "La Rottamazione Quinquies è una misura agevolata. "
            "1. **Tipologie di Debiti**: IRPEF, IVA, IRAP "
            "1. **Benefici**: annullamento sanzioni "
            "1. **Modalità**: unica soluzione o rate "
            "1. **Scadenza**: 30 aprile 2026"
        )

        # Apply the same pipeline as chatbot.py
        numbering_fixed = SectionNumberingFixer.fix_numbering(llm_response)
        final_content = clean_proactivity_content(numbering_fixed)

        # Verify sequential numbering in final content (what gets saved to DB)
        assert "1. **Tipologie" in final_content
        assert "2. **Benefici" in final_content
        assert "3. **Modalità" in final_content
        assert "4. **Scadenza" in final_content
        # Verify only one "1. **" remains
        assert final_content.count("1. **") == 1
