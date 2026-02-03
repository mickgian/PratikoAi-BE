"""DEV-251: TDD tests for BoldSectionFormatter service.

Transforms plain numbered sections to bold markdown:
  "1. Scadenze" → "1. **Scadenze**:"

This ensures consistent formatting regardless of LLM behavior.
"""

import pytest


class TestBoldSectionFormatterBasic:
    """Test basic bold formatting transformations."""

    def test_transforms_plain_numbered_section_to_bold(self):
        """Plain '1. Scadenze' becomes '1. **Scadenze**:'"""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. Scadenze
La domanda deve essere presentata entro il 30 aprile."""

        formatted = BoldSectionFormatter.format_sections(text)

        assert "1. **Scadenze**:" in formatted
        assert "La domanda deve essere presentata" in formatted

    def test_transforms_multiple_sections(self):
        """Multiple sections are all transformed."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. Definizione
La Rottamazione Quinquies è una misura.

2. Requisiti
Possono aderire i contribuenti.

3. Scadenze
Entro il 30 aprile 2026."""

        formatted = BoldSectionFormatter.format_sections(text)

        assert "1. **Definizione**:" in formatted
        assert "2. **Requisiti**:" in formatted
        assert "3. **Scadenze**:" in formatted

    def test_preserves_already_bold_sections(self):
        """Already bold sections are not double-bolded."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = "1. **Definizione**: La Rottamazione..."

        formatted = BoldSectionFormatter.format_sections(text)

        # Should NOT become 1. ****Definizione****:
        assert formatted.count("**") == 2
        assert "1. **Definizione**:" in formatted

    def test_formats_bullet_point_subsections(self):
        """Bullet subsections like '- Presentazione domanda' become bold."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """3. **Scadenze**:
- Presentazione domanda: entro il 30 aprile
- Pagamento prima rata: 31 luglio 2026"""

        formatted = BoldSectionFormatter.format_sections(text)

        assert "- **Presentazione domanda**:" in formatted
        assert "- **Pagamento prima rata**:" in formatted


class TestBoldSectionFormatterEdgeCases:
    """Test edge cases for bold section formatting."""

    def test_empty_string_returns_empty(self):
        """Edge case: empty input."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        result = BoldSectionFormatter.format_sections("")
        assert result == ""

    def test_none_returns_none(self):
        """Edge case: None input."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        result = BoldSectionFormatter.format_sections(None)
        assert result is None

    def test_no_sections_returns_unchanged(self):
        """Text without numbered sections should remain unchanged."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = "Questo è un paragrafo semplice senza sezioni numerate."
        formatted = BoldSectionFormatter.format_sections(text)

        assert formatted == text

    def test_preserves_lowercase_numbered_items(self):
        """Don't format regular list items (lowercase start)."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """Some content with list:
1. first item
2. second item
3. third item"""

        formatted = BoldSectionFormatter.format_sections(text)

        # Lowercase items should not be bolded
        assert "1. first item" in formatted
        assert "2. second item" in formatted
        assert "**" not in formatted

    def test_handles_accented_titles(self):
        """Italian accented characters are handled correctly."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. Modalità di Pagamento
2. Scadenze Tributarie"""

        formatted = BoldSectionFormatter.format_sections(text)

        assert "1. **Modalità di Pagamento**:" in formatted
        assert "2. **Scadenze Tributarie**:" in formatted

    def test_preserves_content_after_title(self):
        """Content following the title is preserved intact."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. Definizione
La Rottamazione Quinquies è una misura di definizione agevolata introdotta dalla Legge n. 199/2025."""

        formatted = BoldSectionFormatter.format_sections(text)

        assert "La Rottamazione Quinquies" in formatted
        assert "Legge n. 199/2025" in formatted


class TestBoldSectionFormatterBulletPoints:
    """Test bullet point subsection formatting."""

    def test_formats_dash_bullets(self):
        """Dash bullets are formatted."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """- Prima scadenza: 30 aprile 2026
- Seconda scadenza: 31 luglio 2026"""

        formatted = BoldSectionFormatter.format_sections(text)

        assert "- **Prima scadenza**:" in formatted
        assert "- **Seconda scadenza**:" in formatted

    def test_formats_bullet_symbol(self):
        """Unicode bullet symbol is handled."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """• Presentazione domanda: entro il 30 aprile
• Pagamento rata: entro il 31 luglio"""

        formatted = BoldSectionFormatter.format_sections(text)

        assert "• **Presentazione domanda**:" in formatted
        assert "• **Pagamento rata**:" in formatted

    def test_preserves_indented_bullets(self):
        """Indented bullets are also formatted."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. **Scadenze**:
   - Prima scadenza: entro il 30 aprile
   - Seconda scadenza: entro il 31 luglio"""

        formatted = BoldSectionFormatter.format_sections(text)

        assert "- **Prima scadenza**:" in formatted
        assert "- **Seconda scadenza**:" in formatted

    def test_does_not_double_bold_bullet_subsections(self):
        """Already bold bullet subsections are not double-bolded."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """- **Presentazione domanda**: entro il 30 aprile"""

        formatted = BoldSectionFormatter.format_sections(text)

        # Should NOT become - ****Presentazione domanda****:
        assert formatted.count("**") == 2
        assert "- **Presentazione domanda**:" in formatted


class TestBoldSectionFormatterRealWorld:
    """Test with real-world examples from PratikoAI responses."""

    def test_rottamazione_quinquies_broken_format(self):
        """DEV-251: Fix the exact broken format from screenshots."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        # This is what the LLM outputs (broken format)
        text = """1. Scadenze
La domanda di adesione deve essere presentata entro il 30 aprile 2026.

2. Importi e Aliquote
L'importo dovuto include solo il capitale e le spese di notifica."""

        formatted = BoldSectionFormatter.format_sections(text)

        # Should become bold with colons
        assert "1. **Scadenze**:" in formatted
        assert "2. **Importi e Aliquote**:" in formatted
        # Content preserved
        assert "La domanda di adesione" in formatted
        assert "30 aprile 2026" in formatted

    def test_expected_good_format(self):
        """The good format should pass through unchanged."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        # This is the desired format (from Screenshot 1)
        text = """1. **Definizione**: La Rottamazione Quinquies è...
2. **Requisiti**: Possono aderire...
3. **Scadenze**:
   • **Presentazione della domanda**: entro il 30 aprile..."""

        formatted = BoldSectionFormatter.format_sections(text)

        # Should remain unchanged (already correctly formatted)
        assert "1. **Definizione**:" in formatted
        assert "2. **Requisiti**:" in formatted
        assert "3. **Scadenze**:" in formatted
        assert "• **Presentazione della domanda**:" in formatted

    def test_mixed_format_sections(self):
        """Mix of plain and bold sections should work correctly."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. **Definizione**: La Rottamazione è una misura.

2. Requisiti
Possono aderire i contribuenti.

3. **Scadenze**: Entro il 30 aprile 2026."""

        formatted = BoldSectionFormatter.format_sections(text)

        assert "1. **Definizione**:" in formatted
        assert "2. **Requisiti**:" in formatted
        assert "3. **Scadenze**:" in formatted

    def test_section_with_colon_already_present(self):
        """Sections that already have colon after title."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. Scadenze:
La domanda deve essere presentata entro il 30 aprile."""

        formatted = BoldSectionFormatter.format_sections(text)

        # Should add bold but not duplicate colon
        assert "1. **Scadenze**:" in formatted
        # Should NOT have double colon "1. **Scadenze**::"
        assert "**::" not in formatted


class TestBoldSectionFormatterIntegration:
    """Test integration with SectionNumberingFixer."""

    def test_works_after_numbering_fix(self):
        """Should work correctly on text that has had numbering fixed."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # Broken LLM response with both issues
        text = """1. Scadenze
La domanda deve essere presentata.

1. Importi
L'importo dovuto include il capitale.

1. Modalità
È possibile pagare in rate."""

        # Apply numbering fix first
        numbering_fixed = SectionNumberingFixer.fix_numbering(text)

        # Then apply bold formatting
        formatted = BoldSectionFormatter.format_sections(numbering_fixed)

        # Both fixes should be applied
        assert "1. **Scadenze**:" in formatted
        assert "2. **Importi**:" in formatted
        assert "3. **Modalità**:" in formatted

    def test_works_after_disclaimer_filter(self):
        """Should work correctly on disclaimer-filtered text."""
        from app.services.disclaimer_filter import DisclaimerFilter
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. Requisiti
I requisiti sono i seguenti.

2. Benefici
I benefici includono varie agevolazioni.

Consulta un professionista per dettagli."""

        # Apply disclaimer filter first
        filtered, removed = DisclaimerFilter.filter_response(text)

        # Then apply bold formatting
        formatted = BoldSectionFormatter.format_sections(filtered)

        # Disclaimer removed and sections bolded
        assert len(removed) > 0
        assert "consulta un professionista" not in formatted.lower()
        assert "1. **Requisiti**:" in formatted
        assert "2. **Benefici**:" in formatted


class TestBoldSectionFormatterTitleVariations:
    """Test various title formats that should be detected."""

    def test_single_word_title(self):
        """Single word titles work."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. Definizione
La definizione è la seguente."""

        formatted = BoldSectionFormatter.format_sections(text)
        assert "1. **Definizione**:" in formatted

    def test_multi_word_title(self):
        """Multi-word titles work."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. Ambito di Applicazione della Norma
La norma si applica a tutti."""

        formatted = BoldSectionFormatter.format_sections(text)
        assert "1. **Ambito di Applicazione della Norma**:" in formatted

    def test_title_with_slash(self):
        """Titles with slash work (common in legal text)."""
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter

        text = """1. Sanzioni/Interessi
Le sanzioni sono annullate."""

        formatted = BoldSectionFormatter.format_sections(text)
        assert "1. **Sanzioni/Interessi**:" in formatted
