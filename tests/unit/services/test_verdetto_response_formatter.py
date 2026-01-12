"""TDD tests for VerdettResponseFormatter service.

DEV-242: Tests for parsing INDICE DELLE FONTI tables.
"""

import pytest

from app.services.verdetto_response_formatter import (
    VerdettoParsedResponse,
    VerdettResponseFormatter,
)


class TestParseResponse:
    """Test parse_response method."""

    @pytest.fixture
    def formatter(self):
        return VerdettResponseFormatter()

    def test_parses_table_format(self, formatter):
        """Parses markdown table format."""
        content = """
Ecco la risposta alla tua domanda.

### INDICE DELLE FONTI
| # | Data | Ente | Tipo | Riferimento |
|---|------|------|------|-------------|
| 1 | 2024-01-15 | AdE | Circolare | Circolare n. 12/E |
| 2 | 2024-02-20 | INPS | Messaggio | Messaggio n. 500 |

Ulteriori informazioni...
"""
        result = formatter.parse_response(content)

        assert result.has_sources_table is True
        assert len(result.structured_sources) == 2
        assert result.structured_sources[0]["numero"] == 1
        assert result.structured_sources[0]["ente"] == "AdE"
        assert "INDICE DELLE FONTI" not in result.content

    def test_parses_numbered_list_format(self, formatter):
        """Parses numbered list format."""
        content = """
La risposta è la seguente.

### INDICE DELLE FONTI
1. Circolare AdE n. 12/E del 15/01/2024
2. Messaggio INPS n. 500 del 2024

Fine.
"""
        result = formatter.parse_response(content)

        assert result.has_sources_table is True
        assert len(result.structured_sources) == 2

    def test_returns_empty_for_no_table(self, formatter):
        """Returns empty sources when no table found."""
        content = "Ecco la risposta senza fonti."

        result = formatter.parse_response(content)

        assert result.has_sources_table is False
        assert len(result.structured_sources) == 0
        assert result.content == content

    def test_handles_empty_content(self, formatter):
        """Handles empty content gracefully."""
        result = formatter.parse_response("")

        assert result.content == ""
        assert result.structured_sources == []
        assert result.has_sources_table is False

    def test_handles_none_content(self, formatter):
        """Handles None content gracefully."""
        result = formatter.parse_response(None)

        assert result.content == ""
        assert result.structured_sources == []


class TestParseTableRows:
    """Test _parse_table_rows method."""

    @pytest.fixture
    def formatter(self):
        return VerdettResponseFormatter()

    def test_parses_standard_table(self, formatter):
        """Parses standard 5-column table."""
        table_content = """| 1 | 2024-01-15 | AdE | Circolare | Circ. 12/E |
| 2 | 2024-02-20 | INPS | Messaggio | Msg. 500 |"""

        sources = formatter._parse_table_rows(table_content)

        assert len(sources) == 2
        assert sources[0]["numero"] == 1
        assert sources[0]["data"] == "2024-01-15"
        assert sources[0]["ente"] == "AdE"
        assert sources[0]["tipo"] == "Circolare"
        assert sources[0]["riferimento"] == "Circ. 12/E"

    def test_skips_separator_rows(self, formatter):
        """Skips table separator rows."""
        table_content = """|---|------|------|------|-------------|
| 1 | 2024-01-15 | AdE | Circolare | Circ. 12/E |"""

        sources = formatter._parse_table_rows(table_content)

        assert len(sources) == 1

    def test_handles_extra_whitespace(self, formatter):
        """Handles extra whitespace in cells."""
        table_content = "|  1  |  2024-01-15  |  AdE  |  Circolare  |  Circ. 12/E  |"

        sources = formatter._parse_table_rows(table_content)

        assert len(sources) == 1
        assert sources[0]["ente"] == "AdE"


class TestParseNumberedList:
    """Test _parse_numbered_list method."""

    @pytest.fixture
    def formatter(self):
        return VerdettResponseFormatter()

    def test_parses_simple_list(self, formatter):
        """Parses simple numbered list."""
        list_content = """1. Prima fonte
2. Seconda fonte"""

        sources = formatter._parse_numbered_list(list_content)

        assert len(sources) == 2
        assert sources[0]["numero"] == 1
        assert sources[0]["riferimento"] == "Prima fonte"

    def test_extracts_date_from_reference(self, formatter):
        """Extracts date from reference text."""
        list_content = "1. Circolare del 15/01/2024 - dettagli"

        sources = formatter._parse_numbered_list(list_content)

        assert sources[0]["data"] == "15/01/2024"

    def test_extracts_ente_from_reference(self, formatter):
        """Extracts ente from reference text."""
        list_content = "1. Circolare Agenzia delle Entrate n. 12/E"

        sources = formatter._parse_numbered_list(list_content)

        assert "Agenzia" in sources[0]["ente"] or sources[0]["ente"] == "Agenzia delle Entrate"

    def test_extracts_tipo_from_reference(self, formatter):
        """Extracts tipo from reference text."""
        list_content = "1. Circolare n. 12/E del 2024"

        sources = formatter._parse_numbered_list(list_content)

        assert sources[0]["tipo"] == "Circolare"


class TestRemoveSourcesTable:
    """Test _remove_sources_table method."""

    @pytest.fixture
    def formatter(self):
        return VerdettResponseFormatter()

    def test_removes_table_section(self, formatter):
        """Removes entire table section."""
        content = """Introduzione.

### INDICE DELLE FONTI
| 1 | 2024 | AdE | Circ. | Ref |

Conclusione."""

        result = formatter._remove_sources_table(content)

        assert "INDICE DELLE FONTI" not in result
        assert "Introduzione." in result
        assert "Conclusione." in result

    def test_preserves_other_content(self, formatter):
        """Preserves content outside table."""
        content = """Prima parte.

### INDICE DELLE FONTI
1. Fonte 1

Seconda parte con ### intestazione."""

        result = formatter._remove_sources_table(content)

        assert "Prima parte" in result
        assert "Seconda parte" in result


class TestFormatSourcesForDisplay:
    """Test format_sources_for_display method."""

    @pytest.fixture
    def formatter(self):
        return VerdettResponseFormatter()

    def test_formats_sources_as_table(self, formatter):
        """Formats sources as markdown table."""
        sources = [
            {
                "numero": 1,
                "data": "2024-01-15",
                "ente": "AdE",
                "tipo": "Circolare",
                "riferimento": "Circ. 12/E",
            }
        ]

        result = formatter.format_sources_for_display(sources)

        assert "### INDICE DELLE FONTI" in result
        assert "| # | Data | Ente | Tipo | Riferimento |" in result
        assert "| 1 | 2024-01-15 | AdE | Circolare | Circ. 12/E |" in result

    def test_handles_empty_sources(self, formatter):
        """Returns empty string for empty sources."""
        result = formatter.format_sources_for_display([])
        assert result == ""


class TestIntegration:
    """Integration tests for complete parsing flow."""

    @pytest.fixture
    def formatter(self):
        return VerdettResponseFormatter()

    def test_realistic_response_parsing(self, formatter):
        """Parses realistic LLM response with sources."""
        content = """## Risposta

La rottamazione quinquies prevede le seguenti scadenze:
- Prima rata: 31 luglio 2026
- Seconda rata: 30 novembre 2026

### VERDETTO OPERATIVO
Presentare domanda entro il 30 aprile 2026.

### INDICE DELLE FONTI
| # | Data | Ente | Tipo | Riferimento |
|---|------|------|------|-------------|
| 1 | 30/12/2025 | MEF | Legge | Legge di bilancio 2026, art. 1 commi 231-252 |
| 2 | 15/01/2026 | AdE | Provvedimento | Provv. attuativo rottamazione quinquies |

Per ulteriori dettagli contattare il proprio commercialista.
"""
        result = formatter.parse_response(content)

        assert result.has_sources_table is True
        assert len(result.structured_sources) == 2
        assert result.structured_sources[0]["riferimento"] == "Legge di bilancio 2026, art. 1 commi 231-252"
        assert "rottamazione quinquies" in result.content.lower()
        assert "INDICE DELLE FONTI" not in result.content
