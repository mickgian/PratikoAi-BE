"""Tests for XML stripping utility (DEV-201).

TDD tests for clean_proactivity_content() function that strips
<answer> and <suggested_actions> XML tags from LLM responses.
"""

import pytest

from app.core.utils.xml_stripper import (
    clean_proactivity_content,
    strip_answer_tags,
    strip_caveat_blocks,
    strip_suggested_actions_block,
)


class TestStripAnswerTags:
    """Tests for strip_answer_tags() function."""

    def test_strips_opening_answer_tag(self) -> None:
        """Should remove <answer> tag."""
        content = "<answer>This is the response."
        result = strip_answer_tags(content)
        assert result == "This is the response."

    def test_strips_closing_answer_tag(self) -> None:
        """Should remove </answer> tag."""
        content = "This is the response.</answer>"
        result = strip_answer_tags(content)
        assert result == "This is the response."

    def test_strips_both_answer_tags(self) -> None:
        """Should remove both <answer> and </answer> tags."""
        content = "<answer>This is the response.</answer>"
        result = strip_answer_tags(content)
        assert result == "This is the response."

    def test_case_insensitive(self) -> None:
        """Should handle case variations."""
        content = "<ANSWER>Response</ANSWER>"
        result = strip_answer_tags(content)
        assert result == "Response"

    def test_preserves_content_without_tags(self) -> None:
        """Should return content unchanged if no answer tags."""
        content = "No tags here"
        result = strip_answer_tags(content)
        assert result == "No tags here"

    def test_handles_multiline_content(self) -> None:
        """Should handle multiline content inside answer tags."""
        content = "<answer>\nLine 1\nLine 2\nLine 3\n</answer>"
        result = strip_answer_tags(content)
        assert result == "\nLine 1\nLine 2\nLine 3\n"


class TestStripSuggestedActionsBlock:
    """Tests for strip_suggested_actions_block() function."""

    def test_strips_suggested_actions_block(self) -> None:
        """Should remove entire suggested_actions block."""
        content = 'Content before <suggested_actions>[{"id": "1"}]</suggested_actions> after'
        result = strip_suggested_actions_block(content)
        assert result == "Content before  after"

    def test_strips_multiline_suggested_actions(self) -> None:
        """Should handle multiline suggested_actions block."""
        content = """Response text.

<suggested_actions>
[
  {"id": "1", "label": "Action 1", "icon": "💰", "prompt": "Do action 1"},
  {"id": "2", "label": "Action 2", "icon": "📋", "prompt": "Do action 2"}
]
</suggested_actions>"""
        result = strip_suggested_actions_block(content)
        assert result == "Response text.\n\n"

    def test_case_insensitive(self) -> None:
        """Should handle case variations."""
        content = "<SUGGESTED_ACTIONS>[...]</SUGGESTED_ACTIONS>"
        result = strip_suggested_actions_block(content)
        assert result == ""

    def test_preserves_content_without_block(self) -> None:
        """Should return content unchanged if no suggested_actions block."""
        content = "No actions here"
        result = strip_suggested_actions_block(content)
        assert result == "No actions here"

    def test_handles_empty_block(self) -> None:
        """Should handle empty suggested_actions block."""
        content = "Text<suggested_actions></suggested_actions>"
        result = strip_suggested_actions_block(content)
        assert result == "Text"


class TestStripCaveatBlocks:
    """Tests for strip_caveat_blocks() function (DEV-250)."""

    def test_strips_caveat_with_emoji(self) -> None:
        """📌 Nota... patterns should be stripped."""
        content = """La risposta normale.

📌 **Nota sui tributi locali:** La definizione agevolata per tributi locali come imu potrebbe richiedere l'accordo dell'ente locale competente. Verifica con il tuo Comune/Regione. Fonti: [Rottamazione quinquies](https://example.com)

Altra parte della risposta."""

        result = strip_caveat_blocks(content)

        assert "📌" not in result
        assert "Nota sui tributi locali" not in result
        assert "La risposta normale." in result
        assert "Altra parte della risposta." in result

    def test_strips_multiple_caveats(self) -> None:
        """Multiple 📌 caveats should all be stripped."""
        content = """Risposta iniziale.

📌 **Nota sulla scadenza:** Info sulla scadenza importante.

Testo intermedio.

📌 **Nota sui tributi locali:** Info sui tributi."""

        result = strip_caveat_blocks(content)

        assert result.count("📌") == 0
        assert "Nota sulla scadenza" not in result
        assert "Nota sui tributi locali" not in result
        assert "Risposta iniziale." in result
        assert "Testo intermedio." in result

    def test_preserves_content_without_caveats(self) -> None:
        """Content without caveats should be unchanged."""
        content = "Risposta normale senza note o avvertenze."
        result = strip_caveat_blocks(content)
        assert result == content

    def test_strips_caveat_at_end_of_content(self) -> None:
        """Caveat at the end of content should be stripped."""
        content = """Ecco la risposta.

📌 **Nota importante:** Questa è una nota finale."""

        result = strip_caveat_blocks(content)

        assert "📌" not in result
        assert "Nota importante" not in result
        assert "Ecco la risposta." in result

    def test_strips_multiline_caveat(self) -> None:
        """Multi-line caveats should be fully stripped."""
        content = """Risposta.

📌 **Nota sui tributi locali:** La definizione agevolata
potrebbe richiedere l'accordo dell'ente locale competente.
Verifica con il tuo Comune/Regione.
Fonti: [link](url)

Fine risposta."""

        result = strip_caveat_blocks(content)

        assert "📌" not in result
        assert "tributi locali" not in result
        assert "Verifica con il tuo" not in result
        assert "Risposta." in result
        assert "Fine risposta." in result

    def test_handles_empty_string(self) -> None:
        """Should handle empty string input."""
        result = strip_caveat_blocks("")
        assert result == ""

    def test_preserves_other_emojis(self) -> None:
        """Should not strip content with other emojis."""
        content = "Risposta con emoji 👍 e 💰 e 📊 ma non 📌 Nota."
        # The 📌 Nota should be stripped but other emojis preserved
        result = strip_caveat_blocks(content)
        assert "👍" in result
        assert "💰" in result
        assert "📊" in result


class TestCleanProactivityContent:
    """Tests for clean_proactivity_content() main function."""

    def test_strips_both_answer_and_suggested_actions(self) -> None:
        """Should strip both types of tags."""
        content = """<answer>
This is the response.

<suggested_actions>
[{"id": "1", "label": "Action", "icon": "💰", "prompt": "Do it"}]
</suggested_actions>
</answer>"""
        result = clean_proactivity_content(content)
        assert "<answer>" not in result
        assert "</answer>" not in result
        assert "<suggested_actions>" not in result
        assert "This is the response." in result

    def test_strips_and_trims_whitespace(self) -> None:
        """Should strip tags and trim leading/trailing whitespace."""
        content = "  <answer>Response</answer>  "
        result = clean_proactivity_content(content)
        assert result == "Response"

    def test_handles_empty_string(self) -> None:
        """Should handle empty string input."""
        result = clean_proactivity_content("")
        assert result == ""

    def test_handles_content_without_any_tags(self) -> None:
        """Should return trimmed content if no tags present."""
        content = "  Plain text response  "
        result = clean_proactivity_content(content)
        assert result == "Plain text response"

    def test_real_world_example_with_actions(self) -> None:
        """Test with realistic LLM output containing suggested actions."""
        content = """<answer>
Il regime forfettario è un regime fiscale agevolato previsto dalla normativa italiana...

Per ulteriori informazioni, posso cercare nella knowledge base di PratikoAI.
</answer>

<suggested_actions>
[
  {"id": "1", "label": "Approfondisci requisiti", "icon": "📖", "prompt": "Quali sono i requisiti per accedere al regime forfettario?"},
  {"id": "2", "label": "Calcola tassazione", "icon": "💰", "prompt": "Calcola la tassazione per un forfettario con ricavi di 50000 euro"},
  {"id": "3", "label": "Confronta regimi", "icon": "📊", "prompt": "Confronta il regime forfettario con il regime ordinario"}
]
</suggested_actions>"""
        result = clean_proactivity_content(content)

        # Should not contain any XML tags
        assert "<answer>" not in result
        assert "</answer>" not in result
        assert "<suggested_actions>" not in result
        assert "</suggested_actions>" not in result

        # Should contain the actual response text
        assert "regime forfettario" in result
        assert "knowledge base" in result

        # Should not contain the JSON actions
        assert '"id"' not in result
        assert '"label"' not in result

    def test_preserves_markdown_formatting(self) -> None:
        """Should preserve markdown formatting in content."""
        content = """<answer>
# Heading

**Bold text** and *italic text*.

- List item 1
- List item 2

```python
code_block = True
```
</answer>"""
        result = clean_proactivity_content(content)
        assert "# Heading" in result
        assert "**Bold text**" in result
        assert "- List item 1" in result
        assert "code_block = True" in result

    def test_handles_nested_angle_brackets_in_content(self) -> None:
        """Should not strip angle brackets that aren't answer/suggested_actions tags."""
        content = "<answer>Use <tag> and </tag> in your code.</answer>"
        result = clean_proactivity_content(content)
        assert "<tag>" in result
        assert "</tag>" in result

    def test_strips_caveat_blocks_from_content(self) -> None:
        """Should strip 📌 caveat blocks (DEV-250)."""
        content = """<answer>
La risposta normale.

📌 **Nota sui tributi locali:** La definizione agevolata per tributi locali potrebbe richiedere l'accordo dell'ente locale.

Altra parte.
</answer>"""
        result = clean_proactivity_content(content)

        assert "📌" not in result
        assert "Nota sui tributi locali" not in result
        assert "La risposta normale." in result
        assert "Altra parte." in result

    def test_strips_all_proactivity_content_types(self) -> None:
        """Should strip answer tags, suggested_actions, AND caveats (DEV-250)."""
        content = """<answer>
Ecco la risposta completa.

📌 **Nota importante:** Questa è una nota che dovrebbe essere rimossa.

<suggested_actions>
[{"id": "1", "label": "Action", "icon": "💰", "prompt": "Do it"}]
</suggested_actions>
</answer>"""
        result = clean_proactivity_content(content)

        # Should not contain any proactivity markers
        assert "<answer>" not in result
        assert "</answer>" not in result
        assert "<suggested_actions>" not in result
        assert "📌" not in result
        assert "Nota importante" not in result

        # Should contain the actual response
        assert "Ecco la risposta completa." in result

    def test_real_world_caveat_example(self) -> None:
        """Test with real-world caveat from user bug report (DEV-250)."""
        content = """Ecco le informazioni sulla rottamazione.

📌 Nota sui tributi locali: La definizione agevolata per tributi locali come imu
potrebbe richiedere l'accordo dell'ente locale competente. Verifica con il tuo
Comune/Regione. Fonti: Rottamazione quinquies - FISCOeTASSE.com

Per ulteriori dettagli, consulta le fonti."""

        result = clean_proactivity_content(content)

        assert "📌" not in result
        assert "tributi locali" not in result
        assert "FISCOeTASSE" not in result
        assert "Ecco le informazioni" in result
        assert "consulta le fonti" in result

    def test_caveat_does_not_consume_numbered_list(self) -> None:
        """Caveat followed by numbered list (no blank line) should preserve list.

        Bug fix: CAVEAT_PATTERN was consuming numbered list content when there
        was no blank line between the caveat and the list.
        """
        content = """Risposta iniziale.

📌 Nota sui tributi locali: verifica importante.
1. Primo punto
1. Secondo punto

Fine."""

        result = strip_caveat_blocks(content)

        assert "📌" not in result
        assert "tributi locali" not in result
        # Numbered list MUST be preserved!
        assert "1. Primo punto" in result
        assert "1. Secondo punto" in result
        assert "Risposta iniziale." in result
        assert "Fine." in result

    def test_caveat_preserves_numbered_list_after_blank_line(self) -> None:
        """Caveat with blank line before numbered list works correctly."""
        content = """📌 Nota iniziale.

1. Primo
1. Secondo"""

        result = strip_caveat_blocks(content)

        assert "📌" not in result
        assert "1. Primo" in result
        assert "1. Secondo" in result

    def test_caveat_preserves_list_with_various_numbers(self) -> None:
        """Caveat should not consume lists starting with any digit."""
        content = """📌 Nota importante.
2. Secondo elemento
3. Terzo elemento
10. Decimo elemento"""

        result = strip_caveat_blocks(content)

        assert "📌" not in result
        assert "Nota importante" not in result
        assert "2. Secondo elemento" in result
        assert "3. Terzo elemento" in result
        assert "10. Decimo elemento" in result
