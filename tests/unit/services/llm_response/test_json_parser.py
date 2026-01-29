"""Tests for JSON and XML extraction and parsing functions."""

import pytest

from app.services.llm_response.json_parser import (
    extract_json_from_content,
    extract_xml_response,
    parse_unified_response,
)


class TestExtractJsonFromContent:
    """Tests for extract_json_from_content function."""

    def test_extracts_json_from_markdown_code_block(self):
        """Happy path: extracts JSON from markdown code block."""
        content = """Here is the response:
```json
{"answer": "Test answer", "reasoning": "Test reasoning"}
```
"""
        result = extract_json_from_content(content)

        assert result is not None
        assert result["answer"] == "Test answer"
        assert result["reasoning"] == "Test reasoning"

    def test_extracts_json_from_unmarked_code_block(self):
        """Extracts JSON from code block without json specifier."""
        content = """Response:
```
{"answer": "Test"}
```
"""
        result = extract_json_from_content(content)

        assert result is not None
        assert result["answer"] == "Test"

    def test_extracts_raw_json_object(self):
        """Extracts JSON object from plain text."""
        content = 'Some text {"answer": "Found"} more text'

        result = extract_json_from_content(content)

        assert result is not None
        assert result["answer"] == "Found"

    def test_parses_raw_json_string(self):
        """Parses raw JSON string without surrounding text."""
        content = '{"answer": "Direct JSON"}'

        result = extract_json_from_content(content)

        assert result is not None
        assert result["answer"] == "Direct JSON"

    def test_returns_none_for_empty_content(self):
        """Edge case: returns None for empty content."""
        assert extract_json_from_content("") is None
        assert extract_json_from_content(None) is None

    def test_returns_none_for_invalid_json(self):
        """Error case: returns None for malformed JSON."""
        content = '{"answer": "Missing quote}'

        result = extract_json_from_content(content)

        assert result is None

    def test_handles_nested_json_objects(self):
        """Handles nested JSON structures."""
        content = """```json
{"answer": "Test", "metadata": {"key": "value"}}
```"""
        result = extract_json_from_content(content)

        assert result is not None
        assert result["answer"] == "Test"
        assert result["metadata"]["key"] == "value"


class TestParseUnifiedResponse:
    """Tests for parse_unified_response function."""

    def test_parses_complete_unified_response(self):
        """Happy path: parses response with all expected fields."""
        content = """```json
{
    "reasoning": "Step by step analysis",
    "answer": "Final answer text",
    "sources_cited": [{"ref": "Legge 123/2024"}]
}
```"""
        result = parse_unified_response(content)

        assert result is not None
        assert result["reasoning"] == "Step by step analysis"
        assert result["answer"] == "Final answer text"
        assert len(result["sources_cited"]) == 1

    def test_parses_response_with_only_answer(self):
        """Parses response with just answer field."""
        content = '{"answer": "Only answer provided"}'

        result = parse_unified_response(content)

        assert result is not None
        assert result["answer"] == "Only answer provided"

    def test_returns_none_for_missing_expected_fields(self):
        """Returns None when no expected fields are present."""
        content = '{"unexpected_field": "value"}'

        result = parse_unified_response(content)

        assert result is None

    def test_returns_none_for_empty_content(self):
        """Edge case: returns None for empty content."""
        assert parse_unified_response("") is None
        assert parse_unified_response(None) is None

    def test_returns_none_for_invalid_json(self):
        """Error case: returns None for malformed JSON."""
        content = "Not valid JSON at all"

        result = parse_unified_response(content)

        assert result is None


class TestExtractXmlResponse:
    """Tests for extract_xml_response function (DEV-250)."""

    def test_extracts_complete_xml_response(self):
        """Happy path: extracts all XML tags from response."""
        content = """<response>
<reasoning>
Il tema riguarda la rottamazione quinquies.
Le fonti rilevanti sono Art. 1, L. 199/2025.
</reasoning>

<answer>
La rottamazione quinquies è una definizione agevolata dei carichi affidati.

## 1. Ambito
I carichi affidati dal 2000 al 2023.

## 2. Benefici
Stralcio sanzioni e interessi.
</answer>

<sources>
- title: Legge 199/2025
  url: https://example.com/legge
  type: kb
</sources>
</response>"""

        result = extract_xml_response(content)

        assert result is not None
        assert "rottamazione quinquies" in result["reasoning"]
        assert "## 1. Ambito" in result["answer"]
        assert "## 2. Benefici" in result["answer"]
        assert "Legge 199/2025" in result["sources_raw"]

    def test_extracts_answer_only(self):
        """Extracts answer when it's the only XML tag present."""
        content = """<answer>
Risposta semplice senza reasoning.
</answer>"""

        result = extract_xml_response(content)

        assert result is not None
        assert "Risposta semplice" in result["answer"]
        assert result["reasoning"] is None

    def test_handles_answer_with_markdown(self):
        """Handles answer containing markdown formatting."""
        content = """<answer>
## 1. Primo Punto
- Elemento 1
- Elemento 2

## 2. Secondo Punto
**Importante:** questo è il testo.

### 2.1 Sottosezione
Dettagli aggiuntivi.
</answer>"""

        result = extract_xml_response(content)

        assert result is not None
        assert "## 1. Primo Punto" in result["answer"]
        assert "## 2. Secondo Punto" in result["answer"]
        assert "### 2.1 Sottosezione" in result["answer"]
        assert "**Importante:**" in result["answer"]

    def test_handles_multiline_answer(self):
        """Handles answer with multiple paragraphs and newlines."""
        content = """<answer>
Paragrafo uno con informazioni importanti.

Paragrafo due con altri dettagli.

Paragrafo tre con conclusioni.
</answer>"""

        result = extract_xml_response(content)

        assert result is not None
        assert "Paragrafo uno" in result["answer"]
        assert "Paragrafo due" in result["answer"]
        assert "Paragrafo tre" in result["answer"]

    def test_returns_none_for_no_xml_tags(self):
        """Returns None when no XML tags are present."""
        content = "Plain text without any XML tags"

        result = extract_xml_response(content)

        assert result is None

    def test_returns_none_for_empty_content(self):
        """Edge case: returns None for empty content."""
        assert extract_xml_response("") is None
        assert extract_xml_response(None) is None

    def test_handles_nested_xml_in_answer(self):
        """Handles cases where answer might contain XML-like content."""
        content = """<answer>
Per configurare il file usa il tag <config> nel documento.
Esempio: <setting name="value"/>
</answer>"""

        result = extract_xml_response(content)

        assert result is not None
        assert "<config>" in result["answer"]
        assert "<setting" in result["answer"]

    def test_strips_whitespace_from_extracted_content(self):
        """Strips leading/trailing whitespace from extracted content."""
        content = """<answer>

   Risposta con whitespace intorno.

</answer>"""

        result = extract_xml_response(content)

        assert result is not None
        assert result["answer"] == "Risposta con whitespace intorno."

    def test_extracts_reasoning_separately(self):
        """Extracts reasoning tag content separately from answer."""
        content = """<reasoning>
Passo 1: Identifico il tema.
Passo 2: Trovo le fonti.
</reasoning>

<answer>
La risposta finale basata sull'analisi.
</answer>"""

        result = extract_xml_response(content)

        assert result is not None
        assert "Passo 1" in result["reasoning"]
        assert "Passo 2" in result["reasoning"]
        assert "risposta finale" in result["answer"]


class TestParseUnifiedResponseWithXml:
    """Tests for parse_unified_response with XML format (DEV-250)."""

    def test_prefers_xml_over_json(self):
        """XML format is tried first, JSON as fallback."""
        content = """<answer>
XML answer should be used.
</answer>"""

        result = parse_unified_response(content)

        assert result is not None
        assert "XML answer should be used" in result["answer"]

    def test_falls_back_to_json_when_no_xml(self):
        """Falls back to JSON parsing when no XML tags found."""
        content = '{"answer": "JSON fallback answer"}'

        result = parse_unified_response(content)

        assert result is not None
        assert result["answer"] == "JSON fallback answer"

    def test_xml_with_reasoning_sets_reasoning_field(self):
        """XML reasoning is extracted to reasoning field."""
        content = """<reasoning>
Analisi completa del tema.
</reasoning>
<answer>
Risposta basata sull'analisi.
</answer>"""

        result = parse_unified_response(content)

        assert result is not None
        assert "Analisi completa" in result["reasoning"]
        assert "Risposta basata" in result["answer"]
