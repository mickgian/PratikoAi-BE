"""Tests for PII restoration functions."""

import pytest

from app.services.llm_response.pii_restorer import deanonymize_response


class TestDeanonymizeResponse:
    """Tests for deanonymize_response function."""

    def test_restores_single_placeholder(self):
        """Happy path: restores single PII placeholder."""
        content = "Gentile [NOME_ABC123], la sua richiesta è stata processata."
        deanonymization_map = {"[NOME_ABC123]": "Mario Rossi"}

        result = deanonymize_response(content, deanonymization_map)

        assert result == "Gentile Mario Rossi, la sua richiesta è stata processata."

    def test_restores_multiple_placeholders(self):
        """Restores multiple different PII placeholders."""
        content = "[NOME_A] e [NOME_B] hanno firmato il contratto."
        deanonymization_map = {
            "[NOME_A]": "Mario Rossi",
            "[NOME_B]": "Luigi Verdi",
        }

        result = deanonymize_response(content, deanonymization_map)

        assert result == "Mario Rossi e Luigi Verdi hanno firmato il contratto."

    def test_handles_longer_placeholders_first(self):
        """Longer placeholders are replaced before shorter ones to avoid partial matches."""
        content = "[NOME_ABC] and [NOME_ABC123] should both be replaced."
        deanonymization_map = {
            "[NOME_ABC]": "Short",
            "[NOME_ABC123]": "LongerName",
        }

        result = deanonymize_response(content, deanonymization_map)

        assert "[NOME_ABC]" not in result
        assert "[NOME_ABC123]" not in result
        assert "LongerName" in result
        assert "Short" in result

    def test_returns_original_for_empty_map(self):
        """Edge case: returns original content when map is empty."""
        content = "Original text with [PLACEHOLDER]"

        result = deanonymize_response(content, {})

        assert result == content

    def test_returns_original_for_none_map(self):
        """Edge case: returns original content when map is None."""
        content = "Original text"

        result = deanonymize_response(content, None)

        assert result == content

    def test_returns_empty_for_empty_content(self):
        """Edge case: returns empty string for empty content."""
        deanonymization_map = {"[NOME]": "Test"}

        assert deanonymize_response("", deanonymization_map) == ""

    def test_returns_content_for_none_content(self):
        """Edge case: handles None content."""
        deanonymization_map = {"[NOME]": "Test"}

        result = deanonymize_response(None, deanonymization_map)

        assert result is None

    def test_handles_repeated_placeholder(self):
        """Replaces all occurrences of same placeholder."""
        content = "[NOME] ha chiamato [NOME] per confermare."
        deanonymization_map = {"[NOME]": "Mario"}

        result = deanonymize_response(content, deanonymization_map)

        assert result == "Mario ha chiamato Mario per confermare."
