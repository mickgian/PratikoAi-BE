"""Tests for response processing functions."""

from unittest.mock import patch

from app.services.llm_response.response_processor import (
    fallback_to_text,
    process_unified_response,
)


class TestFallbackToText:
    """Tests for fallback_to_text function."""

    def test_returns_dict_with_content_as_answer(self):
        """Happy path: returns dict with content as answer."""
        state = {"request_id": "test-123"}

        result = fallback_to_text("Plain text response", state)

        assert result["answer"] == "Plain text response"
        assert result["reasoning"] is None
        assert result["sources_cited"] == []

    def test_handles_empty_content(self):
        """Edge case: handles empty content."""
        state = {"request_id": "test-123"}

        result = fallback_to_text("", state)

        assert result["answer"] == ""

    def test_handles_none_content(self):
        """Edge case: handles None content (returns empty string)."""
        state = {"request_id": "test-123"}

        result = fallback_to_text(None, state)

        assert result["answer"] == ""


class TestProcessUnifiedResponse:
    """Tests for process_unified_response function."""

    @patch("app.services.disclaimer_filter.DisclaimerFilter")
    def test_processes_valid_json_response(self, mock_filter_class):
        """Happy path: processes valid JSON response."""
        mock_filter_class.filter_response.return_value = ("Filtered answer", [])
        state = {"request_id": "test-123"}
        content = """```json
{
    "reasoning": "Analysis steps",
    "answer": "Final answer",
    "sources_cited": [{"ref": "Legge 123/2024"}]
}
```"""

        result = process_unified_response(content, state)

        assert result == "Filtered answer"
        assert state["reasoning_type"] == "cot"
        assert state["reasoning_trace"] == "Analysis steps"
        assert len(state["sources_cited"]) == 1

    @patch("app.services.disclaimer_filter.DisclaimerFilter")
    def test_preserves_tot_reasoning_type(self, mock_filter_class):
        """Preserves ToT reasoning type if already set."""
        mock_filter_class.filter_response.return_value = ("Filtered answer", [])
        state = {
            "request_id": "test-123",
            "reasoning_type": "tot",
            "reasoning_trace": "ToT trace",
        }
        content = '{"answer": "Test", "reasoning": "Should not override"}'

        process_unified_response(content, state)

        assert state["reasoning_type"] == "tot"
        assert state["reasoning_trace"] == "ToT trace"

    @patch("app.services.disclaimer_filter.DisclaimerFilter")
    @patch("app.services.llm_response.response_processor.log_reasoning_trace_failed")
    def test_fallback_on_invalid_json(self, mock_log, mock_filter_class):
        """Falls back to text when JSON parsing fails."""
        mock_filter_class.filter_response.return_value = ("Plain text", [])
        state = {"request_id": "test-123"}

        result = process_unified_response("Not valid JSON", state)

        assert result == "Plain text"
        assert state["reasoning_type"] is None
        assert state["sources_cited"] == []

    @patch("app.services.disclaimer_filter.DisclaimerFilter")
    def test_filters_disclaimers_from_answer(self, mock_filter_class):
        """Filters unauthorized disclaimers from answer."""
        mock_filter_class.filter_response.return_value = ("Cleaned answer", ["Removed disclaimer"])
        state = {"request_id": "test-123"}
        content = '{"answer": "Answer with disclaimer", "reasoning": "Test"}'

        process_unified_response(content, state)

        mock_filter_class.filter_response.assert_called()

    @patch("app.services.disclaimer_filter.DisclaimerFilter")
    def test_applies_source_hierarchy(self, mock_filter_class):
        """Sources are sorted by hierarchy rank."""
        mock_filter_class.filter_response.return_value = ("Answer", [])
        state = {"request_id": "test-123"}
        content = """```json
{
    "answer": "Test",
    "sources_cited": [
        {"ref": "Interpello 42"},
        {"ref": "Legge 123"}
    ]
}
```"""

        process_unified_response(content, state)

        # Legge should be first (rank 1)
        assert state["sources_cited"][0]["ref"] == "Legge 123"
        assert state["sources_cited"][1]["ref"] == "Interpello 42"


class TestProcessUnifiedResponseXml:
    """Tests for process_unified_response with XML format (DEV-250)."""

    @patch("app.services.disclaimer_filter.DisclaimerFilter")
    def test_processes_xml_response(self, mock_filter_class):
        """Happy path: processes valid XML response."""
        mock_filter_class.filter_response.return_value = ("Filtered XML answer", [])
        state = {"request_id": "test-123"}
        content = """<reasoning>
Analisi del tema fiscale.
</reasoning>

<answer>
La risposta completa con tutti i dettagli.

## 1. Primo Punto
Dettagli importanti.

## 2. Secondo Punto
Altri dettagli.
</answer>"""

        result = process_unified_response(content, state)

        assert result == "Filtered XML answer"
        assert state["reasoning_type"] == "cot"
        assert "Analisi del tema" in state["reasoning_trace"]

    @patch("app.services.disclaimer_filter.DisclaimerFilter")
    def test_xml_preserves_markdown_formatting(self, mock_filter_class):
        """XML format preserves markdown in answer."""
        mock_filter_class.filter_response.return_value = (
            "## 1. Header\n**Bold text** and *italic*",
            [],
        )
        state = {"request_id": "test-123"}
        content = """<answer>
## 1. Header
**Bold text** and *italic*
</answer>"""

        result = process_unified_response(content, state)

        assert "## 1. Header" in result
        assert "**Bold text**" in result

    @patch("app.services.disclaimer_filter.DisclaimerFilter")
    def test_xml_without_reasoning_sets_none(self, mock_filter_class):
        """XML without reasoning tag sets reasoning_trace to None."""
        mock_filter_class.filter_response.return_value = ("Answer only", [])
        state = {"request_id": "test-123"}
        content = """<answer>
Answer without reasoning section.
</answer>"""

        process_unified_response(content, state)

        assert state["reasoning_type"] == "cot"
        assert state["reasoning_trace"] is None

    @patch("app.services.disclaimer_filter.DisclaimerFilter")
    def test_prefers_xml_over_json_in_same_content(self, mock_filter_class):
        """When both XML and JSON present, XML is used."""
        mock_filter_class.filter_response.return_value = ("XML answer used", [])
        state = {"request_id": "test-123"}
        # Content with both formats - XML should be preferred
        content = """<answer>
XML answer used
</answer>

Also here's JSON: {"answer": "JSON answer ignored"}"""

        result = process_unified_response(content, state)

        assert result == "XML answer used"
