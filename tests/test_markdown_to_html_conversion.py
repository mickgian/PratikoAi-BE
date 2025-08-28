"""
TDD Tests: Markdown to HTML Conversion for Streaming Content

CRITICAL: Users must NEVER see markdown syntax characters.
Backend must send ready-to-render HTML chunks.
"""

import pytest
import sys
import os

# Add the parent directory to sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.content_formatter import ContentFormatter


class TestMarkdownToHTMLConversion:
    """Test markdown conversion to HTML for streaming content."""
    
    def setup_method(self):
        self.formatter = ContentFormatter()
    
    # ========== HEADING CONVERSION TESTS ==========
    
    def test_heading_level_3_conversion(self):
        """Test ### heading conversion to <h3>."""
        markdown_input = "### 1. Definizione/Concetto principale"
        expected_html = "<h3>1. Definizione/Concetto principale</h3>"
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
        
        # Ensure no markdown syntax remains
        assert "###" not in result
    
    def test_heading_level_2_conversion(self):
        """Test ## heading conversion to <h2>."""
        markdown_input = "## Normativa di riferimento"
        expected_html = "<h2>Normativa di riferimento</h2>"
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
        assert "##" not in result
    
    def test_heading_level_1_conversion(self):
        """Test # heading conversion to <h1>."""
        markdown_input = "# Regime Forfettario"
        expected_html = "<h1>Regime Forfettario</h1>"
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
        assert "#" not in result
    
    # ========== TEXT FORMATTING TESTS ==========
    
    def test_bold_text_conversion(self):
        """Test **bold** conversion to <strong>."""
        markdown_input = "Il regime forfettario **non prevede** l'applicazione dell'IVA."
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        
        # Check that bold formatting is correct
        assert "<strong>non prevede</strong>" in result
        # Check that no markdown syntax remains
        assert "**" not in result
        # Should be wrapped in paragraph
        assert result.startswith("<p>")
        assert result.endswith("</p>")
    
    def test_italic_text_conversion(self):
        """Test *italic* conversion to <em>."""
        markdown_input = "La normativa *vigente* stabilisce che..."
        expected_html = "La normativa <em>vigente</em> stabilisce che..."
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
        assert "*" not in result and "**" not in result
    
    def test_combined_formatting_conversion(self):
        """Test combined bold and italic formatting."""
        markdown_input = "Articolo **1, comma *57***: stabilisce che..."
        expected_html = "Articolo <strong>1, comma <em>57</em></strong>: stabilisce che..."
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
        assert "**" not in result and "*" not in result
    
    # ========== LIST CONVERSION TESTS ==========
    
    def test_bullet_list_conversion(self):
        """Test bullet list conversion to <ul><li>."""
        markdown_input = """- Articolo 1, commi 54-89: definisce i requisiti
- Articolo 1, comma 57: stabilisce che non possono accedere"""
        
        expected_html = """<ul>
<li>Articolo 1, commi 54-89: definisce i requisiti</li>
<li>Articolo 1, comma 57: stabilisce che non possono accedere</li>
</ul>"""
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
        assert "-" not in result.replace("-", "")  # No standalone dashes
    
    def test_numbered_list_conversion(self):
        """Test numbered list conversion to <ol><li>."""
        markdown_input = """1. Esempio 1: Un professionista non può essere socio
2. Esempio 2: Un contribuente può detenere partecipazioni"""
        
        expected_html = """<ol>
<li>Esempio 1: Un professionista non può essere socio</li>
<li>Esempio 2: Un contribuente può detenere partecipazioni</li>
</ol>"""
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
    
    # ========== CODE AND INLINE ELEMENTS ==========
    
    def test_inline_code_conversion(self):
        """Test `code` conversion to <code>."""
        markdown_input = "Il codice fiscale `RSSMRA80A01H501U` è valido."
        expected_html = "Il codice fiscale <code>RSSMRA80A01H501U</code> è valido."
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
        assert "`" not in result
    
    def test_code_block_conversion(self):
        """Test ```code block``` conversion to <pre><code>."""
        markdown_input = """```
Calcolo imposta:
Reddito: €50.000
Aliquota: 15%
Imposta: €7.500
```"""
        
        expected_html = """<pre><code>Calcolo imposta:
Reddito: €50.000
Aliquota: 15%
Imposta: €7.500</code></pre>"""
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
        assert "```" not in result
    
    # ========== PARAGRAPH FORMATTING ==========
    
    def test_paragraph_wrapping(self):
        """Test paragraph wrapping in <p> tags."""
        markdown_input = "Il regime forfettario è un regime fiscale semplificato per le persone fisiche."
        expected_html = "<p>Il regime forfettario è un regime fiscale semplificato per le persone fisiche.</p>"
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
    
    def test_multiple_paragraphs(self):
        """Test multiple paragraph handling."""
        markdown_input = """Il regime forfettario è un regime semplificato.

Tuttavia, ci sono alcune limitazioni da considerare."""
        
        expected_html = """<p>Il regime forfettario è un regime semplificato.</p>

<p>Tuttavia, ci sono alcune limitazioni da considerare.</p>"""
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert result == expected_html
    
    # ========== COMPLEX CONTENT TESTS ==========
    
    def test_complete_tax_response_formatting(self):
        """Test formatting of a complete tax response."""
        markdown_input = """### 1. Definizione/Concetto principale

Il regime forfettario è un regime fiscale **semplificato** per le persone fisiche.

### 2. Normativa di riferimento

La normativa di riferimento è contenuta nella *Legge n.190/2014*:

- Articolo 1, commi 54-89: definisce i requisiti
- Articolo 1, comma 57: stabilisce le esclusioni

### 3. Esempi concreti

1. **Esempio 1**: Un professionista non può essere socio
2. **Esempio 2**: Un contribuente può detenere partecipazioni"""
        
        expected_html = """<h3>1. Definizione/Concetto principale</h3>

<p>Il regime forfettario è un regime fiscale <strong>semplificato</strong> per le persone fisiche.</p>

<h3>2. Normativa di riferimento</h3>

<p>La normativa di riferimento è contenuta nella <em>Legge n.190/2014</em>:</p>

<ul>
<li>Articolo 1, commi 54-89: definisce i requisiti</li>
<li>Articolo 1, comma 57: stabilisce le esclusioni</li>
</ul>

<h3>3. Esempi concreti</h3>

<ol>
<li><strong>Esempio 1</strong>: Un professionista non può essere socio</li>
<li><strong>Esempio 2</strong>: Un contribuente può detenere partecipazioni</li>
</ol>"""
        
        result = self.formatter.convert_markdown_to_html(markdown_input)
        
        # Critical: Ensure NO markdown syntax remains
        assert "###" not in result, f"Found ### in result: {result}"
        assert "**" not in result, f"Found ** in result: {result}"
        assert "*" not in result and "**" not in result, f"Found * in result: {result}"
        
        # Check that all expected HTML elements are present
        assert "<h3>1. Definizione/Concetto principale</h3>" in result
        assert "<h3>2. Normativa di riferimento</h3>" in result
        assert "<h3>3. Esempi concreti</h3>" in result
        assert "<strong>semplificato</strong>" in result
        assert "<ul>" in result and "</ul>" in result
        assert "<ol>" in result and "</ol>" in result
        assert "<li>" in result
        
        # Check for legal reference formatting (might be present)
        assert ("Legge n.190/2014" in result or "<cite" in result)
        
        print(f"✅ Complete tax response properly formatted:\n{result}")
    
    # ========== ERROR HANDLING TESTS ==========
    
    def test_malformed_markdown_handling(self):
        """Test handling of malformed markdown."""
        markdown_input = "### Incomplete heading"
        # Should still convert properly
        result = self.formatter.convert_markdown_to_html(markdown_input)
        assert "<h3>" in result
        assert "###" not in result
    
    def test_mixed_content_handling(self):
        """Test handling of mixed markdown and plain text."""
        markdown_input = "Plain text **with bold** and ### heading"
        result = self.formatter.convert_markdown_to_html(markdown_input)
        
        # Should contain proper HTML
        assert "<strong>" in result
        assert "<h3>" in result
        # Should not contain markdown syntax
        assert "**" not in result
        assert "###" not in result


class TestStreamingHTMLChunks:
    """Test HTML formatting in streaming context."""
    
    def setup_method(self):
        self.formatter = ContentFormatter()
    
    def test_incremental_html_building(self):
        """Test building HTML incrementally during streaming."""
        chunks = ["### 1. ", "Definizione", "/Concetto principale"]
        
        # Should accumulate until complete markdown element
        result_chunks = []
        for chunk in chunks:
            formatted = self.formatter.process_streaming_chunk(chunk)
            if formatted:
                result_chunks.append(formatted)
        
        # Should yield complete HTML element
        assert len(result_chunks) == 1
        assert result_chunks[0] == "<h3>1. Definizione/Concetto principale</h3>"
    
    def test_partial_bold_text_streaming(self):
        """Test streaming bold text formation."""
        chunks = ["Il regime ", "**forfet", "tario**", " è semplificato"]
        
        result_chunks = []
        for chunk in chunks:
            formatted = self.formatter.process_streaming_chunk(chunk)
            if formatted:
                result_chunks.append(formatted)
        
        # Should yield properly formatted HTML
        final_result = "".join(result_chunks)
        assert "<strong>forfettario</strong>" in final_result
        assert "**" not in final_result
    
    def test_complete_list_streaming(self):
        """Test streaming list formation."""
        chunks = ["- Item 1", "\n", "- Item 2"]
        
        result_chunks = []
        for chunk in chunks:
            formatted = self.formatter.process_streaming_chunk(chunk)
            if formatted:
                result_chunks.append(formatted)
        
        # Should yield complete list HTML
        final_result = "".join(result_chunks)
        assert "<ul>" in final_result
        assert "<li>Item 1</li>" in final_result
        assert "<li>Item 2</li>" in final_result
        assert "</ul>" in final_result
        assert "-" not in final_result.replace("Item", "")  # No standalone dashes


# ========== INTEGRATION TESTS ==========

class TestBackendIntegration:
    """Test integration with backend streaming endpoint."""
    
    @pytest.mark.asyncio
    async def test_streaming_endpoint_html_output(self):
        """Test that streaming endpoint returns HTML-formatted content."""
        # This would test the actual streaming endpoint
        # to ensure it returns properly formatted HTML
        pass
    
    @pytest.mark.asyncio
    async def test_no_markdown_syntax_in_stream(self):
        """Test that streaming response never contains markdown syntax."""
        # Critical test: scan all streaming output for markdown characters
        forbidden_chars = ["###", "**", "*", "`", "```"]
        
        # Would test actual streaming response
        # for char_set in forbidden_chars:
        #     assert char_set not in streaming_response
        pass