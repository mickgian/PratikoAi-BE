"""Tests for Step 64 de-anonymization functionality.

DEV-007 PII: Tests that PII placeholders in LLM responses are correctly
restored to original values before returning to user.
"""

import pytest


class TestDeanonymizeResponse:
    """Test suite for _deanonymize_response function."""

    def test_deanonymize_simple_name(self):
        """Test de-anonymizing a simple name placeholder."""
        from app.core.langgraph.nodes.step_064__llm_call import _deanonymize_response

        content = "Il documento appartiene a [NOME_ABC123]."
        deanonymization_map = {"[NOME_ABC123]": "Giancarlo Rossi"}

        result = _deanonymize_response(content, deanonymization_map)

        assert result == "Il documento appartiene a Giancarlo Rossi."

    def test_deanonymize_multiple_pii_types(self):
        """Test de-anonymizing multiple PII types in same response."""
        from app.core.langgraph.nodes.step_064__llm_call import _deanonymize_response

        content = (
            "Il contribuente [NOME_ABC123] con codice fiscale [CF_XYZ789] "
            "e IBAN [IBAN_DEF456] ha presentato la dichiarazione."
        )
        deanonymization_map = {
            "[NOME_ABC123]": "Mario Bianchi",
            "[CF_XYZ789]": "BNCMRA85M01H501Z",
            "[IBAN_DEF456]": "IT60X0542811101000000123456",
        }

        result = _deanonymize_response(content, deanonymization_map)

        assert result == (
            "Il contribuente Mario Bianchi con codice fiscale BNCMRA85M01H501Z "
            "e IBAN IT60X0542811101000000123456 ha presentato la dichiarazione."
        )

    def test_deanonymize_repeated_placeholder(self):
        """Test that same placeholder is replaced multiple times."""
        from app.core.langgraph.nodes.step_064__llm_call import _deanonymize_response

        content = (
            "[NOME_ABC123] ha richiesto informazioni. " "Pertanto, [NOME_ABC123] dovrà presentare la documentazione."
        )
        deanonymization_map = {"[NOME_ABC123]": "Lucia Verdi"}

        result = _deanonymize_response(content, deanonymization_map)

        assert "[NOME_ABC123]" not in result
        assert result.count("Lucia Verdi") == 2

    def test_deanonymize_empty_map(self):
        """Test that empty map returns content unchanged."""
        from app.core.langgraph.nodes.step_064__llm_call import _deanonymize_response

        content = "Nessun dato personale presente."
        deanonymization_map = {}

        result = _deanonymize_response(content, deanonymization_map)

        assert result == content

    def test_deanonymize_empty_content(self):
        """Test that empty content returns empty."""
        from app.core.langgraph.nodes.step_064__llm_call import _deanonymize_response

        deanonymization_map = {"[NOME_ABC123]": "Test"}

        result = _deanonymize_response("", deanonymization_map)

        assert result == ""

    def test_deanonymize_none_content(self):
        """Test that None content returns None."""
        from app.core.langgraph.nodes.step_064__llm_call import _deanonymize_response

        deanonymization_map = {"[NOME_ABC123]": "Test"}

        result = _deanonymize_response(None, deanonymization_map)

        assert result is None

    def test_deanonymize_preserves_unmatched_text(self):
        """Test that text without placeholders is preserved."""
        from app.core.langgraph.nodes.step_064__llm_call import _deanonymize_response

        content = "Calcolo IVA: 22% su €1000 = €220"
        deanonymization_map = {"[NOME_ABC123]": "Test"}

        result = _deanonymize_response(content, deanonymization_map)

        assert result == content

    def test_deanonymize_long_placeholder_first(self):
        """Test that longer placeholders are replaced first to avoid partial matches."""
        from app.core.langgraph.nodes.step_064__llm_call import _deanonymize_response

        # This tests the sorting by length descending
        content = "[NOME_ABC] e [NOME_ABC123] sono clienti."
        deanonymization_map = {
            "[NOME_ABC]": "Short",
            "[NOME_ABC123]": "LongerName",
        }

        result = _deanonymize_response(content, deanonymization_map)

        # Both should be replaced correctly without overlap issues
        assert result == "Short e LongerName sono clienti."

    def test_deanonymize_all_pii_types(self):
        """Test de-anonymizing all supported PII types."""
        from app.core.langgraph.nodes.step_064__llm_call import _deanonymize_response

        content = (
            "Cliente: [NOME_001]\n"
            "Codice Fiscale: [CF_002]\n"
            "Indirizzo: [INDIRIZZO_003]\n"
            "IBAN: [IBAN_004]\n"
            "Partita IVA: [PIVA_005]\n"
            "Email: [EMAIL_006]\n"
            "Telefono: [TEL_007]\n"
            "Carta: [CC_008]"
        )
        deanonymization_map = {
            "[NOME_001]": "Giuseppe Verdi",
            "[CF_002]": "VRDGPP80A01H501X",
            "[INDIRIZZO_003]": "Via Roma 123, Milano",
            "[IBAN_004]": "IT60X0542811101000000123456",
            "[PIVA_005]": "12345678901",
            "[EMAIL_006]": "giuseppe.verdi@email.com",
            "[TEL_007]": "+39 02 1234567",
            "[CC_008]": "4111111111111111",
        }

        result = _deanonymize_response(content, deanonymization_map)

        assert "Giuseppe Verdi" in result
        assert "VRDGPP80A01H501X" in result
        assert "Via Roma 123, Milano" in result
        assert "IT60X0542811101000000123456" in result
        assert "12345678901" in result
        assert "giuseppe.verdi@email.com" in result
        assert "+39 02 1234567" in result
        assert "4111111111111111" in result
        # No placeholders should remain
        assert "[NOME_" not in result
        assert "[CF_" not in result
