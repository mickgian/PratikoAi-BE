"""
TDD Tests: Complete Block Formatting for Streaming Content

Backend must send complete, well-formed HTML blocks.
No partial tags, no broken formatting.
Frontend should receive ready-to-display content.
"""

import pytest
from app.core.content_formatter import ContentFormatter, BlockBuffer


class TestCompleteBlockFormatting:
    """Test that backend sends complete HTML blocks."""
    
    def setup_method(self):
        self.formatter = ContentFormatter()
        self.block_buffer = BlockBuffer()
    
    # ========== PARAGRAPH BLOCK TESTS ==========
    
    def test_complete_paragraph_block(self):
        """Test complete paragraph formation."""
        text_chunks = [
            "Il regime forfettario è",
            " un regime fiscale",
            " semplificato per",
            " le persone fisiche."
        ]
        
        # Should accumulate until sentence is complete
        result_blocks = []
        for chunk in text_chunks:
            block = self.block_buffer.add_chunk(chunk)
            if block:
                formatted = self.formatter.format_block(block)
                result_blocks.append(formatted)
        
        # Should yield one complete paragraph
        assert len(result_blocks) == 1
        assert result_blocks[0] == "<p>Il regime forfettario è un regime fiscale semplificato per le persone fisiche.</p>"
    
    def test_multiple_paragraph_blocks(self):
        """Test multiple paragraph formation."""
        text_chunks = [
            "Il regime forfettario è semplificato.",
            "\n\n",
            "Tuttavia, ci sono limitazioni",
            " da considerare."
        ]
        
        result_blocks = []
        for chunk in text_chunks:
            blocks = self.block_buffer.add_chunk(chunk)
            if blocks:
                for block in blocks:
                    formatted = self.formatter.format_block(block)
                    result_blocks.append(formatted)
        
        expected_blocks = [
            "<p>Il regime forfettario è semplificato.</p>",
            "<p>Tuttavia, ci sono limitazioni da considerare.</p>"
        ]
        
        assert result_blocks == expected_blocks
    
    # ========== LIST BLOCK TESTS ==========
    
    def test_complete_bullet_list_block(self):
        """Test complete bullet list formation."""
        list_chunks = [
            "- Articolo 1, commi 54-89:",
            " definisce i requisiti\n",
            "- Articolo 1, comma 57:",
            " stabilisce le esclusioni\n",
            "- Decreto attuativo:",
            " dettagli operativi"
        ]
        
        result_blocks = []
        for chunk in list_chunks:
            block = self.block_buffer.add_chunk(chunk)
            if block:
                formatted = self.formatter.format_block(block)
                result_blocks.append(formatted)
        
        # Should yield one complete list
        assert len(result_blocks) == 1
        expected_html = """<ul>
<li>Articolo 1, commi 54-89: definisce i requisiti</li>
<li>Articolo 1, comma 57: stabilisce le esclusioni</li>
<li>Decreto attuativo: dettagli operativi</li>
</ul>"""
        
        assert result_blocks[0] == expected_html
    
    def test_complete_numbered_list_block(self):
        """Test complete numbered list formation."""
        list_chunks = [
            "1. Esempio 1:",
            " Un professionista non può\n",
            "2. Esempio 2:",
            " Un contribuente può\n",
            "3. Esempio 3:",
            " Caso particolare"
        ]
        
        result_blocks = []
        for chunk in list_chunks:
            block = self.block_buffer.add_chunk(chunk)
            if block:
                formatted = self.formatter.format_block(block)
                result_blocks.append(formatted)
        
        expected_html = """<ol>
<li>Esempio 1: Un professionista non può</li>
<li>Esempio 2: Un contribuente può</li>
<li>Esempio 3: Caso particolare</li>
</ol>"""
        
        assert len(result_blocks) == 1
        assert result_blocks[0] == expected_html
    
    # ========== HEADING BLOCK TESTS ==========
    
    def test_complete_heading_block(self):
        """Test complete heading formation."""
        heading_chunks = [
            "### 1. Definizione",
            "/Concetto",
            " principale"
        ]
        
        result_blocks = []
        for chunk in heading_chunks:
            block = self.block_buffer.add_chunk(chunk)
            if block:
                formatted = self.formatter.format_block(block)
                result_blocks.append(formatted)
        
        # Should yield one complete heading
        assert len(result_blocks) == 1
        assert result_blocks[0] == "<h3>1. Definizione/Concetto principale</h3>"
    
    def test_heading_with_subsequent_content(self):
        """Test heading followed by content."""
        content_chunks = [
            "### 2. Normativa\n\n",
            "La normativa di riferimento",
            " è contenuta nella",
            " Legge n.190/2014."
        ]
        
        result_blocks = []
        for chunk in content_chunks:
            blocks = self.block_buffer.add_chunk(chunk)
            if blocks:
                for block in blocks:
                    formatted = self.formatter.format_block(block)
                    result_blocks.append(formatted)
        
        expected_blocks = [
            "<h3>2. Normativa</h3>",
            "<p>La normativa di riferimento è contenuta nella Legge n.190/2014.</p>"
        ]
        
        assert result_blocks == expected_blocks
    
    # ========== TABLE BLOCK TESTS ==========
    
    def test_complete_table_block(self):
        """Test complete table formation."""
        table_chunks = [
            "| Regime | Aliquota | Soglia |\n",
            "| --- | --- | --- |\n",
            "| Ordinario | 23-43% | N/A |\n",
            "| Forfettario | 15% | €65.000 |\n",
            "| Semplificato | 10% | €30.000 |"
        ]
        
        result_blocks = []
        for chunk in table_chunks:
            block = self.block_buffer.add_chunk(chunk)
            if block:
                formatted = self.formatter.format_block(block)
                result_blocks.append(formatted)
        
        expected_html = """<table class="tax-comparison-table">
<thead>
<tr>
<th>Regime</th>
<th>Aliquota</th>
<th>Soglia</th>
</tr>
</thead>
<tbody>
<tr>
<td>Ordinario</td>
<td>23-43%</td>
<td>N/A</td>
</tr>
<tr>
<td>Forfettario</td>
<td>15%</td>
<td>€ 65.000</td>
</tr>
<tr>
<td>Semplificato</td>
<td>10%</td>
<td>€ 30.000</td>
</tr>
</tbody>
</table>"""
        
        assert len(result_blocks) == 1
        assert result_blocks[0] == expected_html
    
    # ========== COMPLEX BLOCK TESTS ==========
    
    def test_calculation_block_with_context(self):
        """Test calculation block with surrounding context."""
        content_chunks = [
            "Per il calcolo dell'imposta:\n\n",
            "Reddito: 50000\n",
            "Aliquota: 15%\n",
            "Imposta: 7500\n\n",
            "Questo risultato è valido",
            " per l'anno fiscale corrente."
        ]
        
        result_blocks = []
        for chunk in content_chunks:
            blocks = self.block_buffer.add_chunk(chunk)
            if blocks:
                for block in blocks:
                    formatted = self.formatter.format_block(block)
                    result_blocks.append(formatted)
        
        # Should get: intro paragraph, calculation block, conclusion paragraph
        assert len(result_blocks) == 3
        assert "<p>Per il calcolo dell'imposta:</p>" in result_blocks[0]
        assert '<div class="calculation">' in result_blocks[1]
        assert "<p>Questo risultato è valido per l'anno fiscale corrente.</p>" in result_blocks[2]
    
    def test_mixed_content_block_formation(self):
        """Test complex mixed content block formation."""
        mixed_chunks = [
            "### 3. Esempi concreti\n\n",
            "Consideriamo i seguenti casi:\n\n",
            "1. **Professionista**: ",
            "non può essere socio\n",
            "2. **Contribuente**: ",
            "può detenere partecipazioni\n\n",
            "Le limitazioni sono:",
            "\n\n- Attività commerciale",
            "\n- Soglie di fatturato",
            "\n- Requisiti temporali"
        ]
        
        result_blocks = []
        for chunk in mixed_chunks:
            blocks = self.block_buffer.add_chunk(chunk)
            if blocks:
                for block in blocks:
                    formatted = self.formatter.format_block(block)
                    result_blocks.append(formatted)
        
        # Should properly separate into distinct blocks
        assert len(result_blocks) >= 4  # Heading, intro, numbered list, bullet list
        
        # Check that each block is complete and well-formed
        for block in result_blocks:
            # No orphaned opening tags
            assert block.count("<") == block.count(">")
            # No unclosed tags
            for tag in ["h3", "p", "ol", "ul", "li", "strong"]:
                opening_count = block.count(f"<{tag}")
                closing_count = block.count(f"</{tag}>")
                assert opening_count == closing_count, f"Unclosed {tag} tags in: {block}"
    
    # ========== BLOCK BOUNDARY DETECTION ==========
    
    def test_paragraph_boundary_detection(self):
        """Test detection of paragraph boundaries."""
        test_cases = [
            ("Text.\n\nNew paragraph", True),  # Double newline
            ("Text. New sentence", False),     # Same paragraph
            ("Text.\n", False),                # Single newline (incomplete)
            ("Text.\n\n", True),               # Double newline (complete)
        ]
        
        for text, should_complete in test_cases:
            result = self.block_buffer.is_paragraph_complete(text)
            assert result == should_complete
    
    def test_list_boundary_detection(self):
        """Test detection of list boundaries."""
        test_cases = [
            ("- Item 1\n- Item 2\n\n", True),   # List with trailing newlines
            ("- Item 1\n- Item 2", False),      # Incomplete list
            ("1. Item 1\n2. Item 2\n", False), # Missing final boundary
            ("1. Item 1\n2. Item 2\n\n", True), # Complete numbered list
        ]
        
        for text, should_complete in test_cases:
            result = self.block_buffer.is_list_complete(text)
            assert result == should_complete
    
    def test_heading_boundary_detection(self):
        """Test detection of heading boundaries."""
        test_cases = [
            ("### Heading\n", True),           # Complete heading
            ("### Partial", False),            # Incomplete heading
            ("### Complete Heading\n\n", True), # Heading with content separator
        ]
        
        for text, should_complete in test_cases:
            result = self.block_buffer.is_heading_complete(text)
            assert result == should_complete
    
    # ========== ERROR HANDLING ==========
    
    def test_malformed_block_handling(self):
        """Test handling of malformed blocks."""
        malformed_blocks = [
            "### Incomplete heading without newline",
            "- Incomplete list item",
            "**Unclosed bold formatting",
            "`Unclosed code block",
        ]
        
        for malformed in malformed_blocks:
            # Should still produce valid HTML
            result = self.formatter.format_block(malformed)
            assert isinstance(result, str)
            assert len(result) > 0
            # Should not contain raw markdown syntax
            assert "###" not in result
            assert "**" not in result
            assert "`" not in result
    
    def test_empty_block_handling(self):
        """Test handling of empty or whitespace-only blocks."""
        empty_blocks = ["", "   ", "\n\n", "\t\t"]
        
        for empty in empty_blocks:
            result = self.formatter.format_block(empty)
            # Should either return empty string or valid empty element
            assert result == "" or result.startswith("<")
    
    # ========== BLOCK VALIDATION ==========
    
    def test_html_validity_of_blocks(self):
        """Test that all generated blocks are valid HTML."""
        test_blocks = [
            "### Test Heading",
            "Regular paragraph text.",
            "- List item 1\n- List item 2",
            "1. Numbered item 1\n2. Numbered item 2",
            "**Bold text** with *italic*",
            "Calculation: 100 × 15% = 15",
        ]
        
        for block_text in test_blocks:
            formatted = self.formatter.format_block(block_text)
            
            # Basic HTML validity checks
            assert formatted.count("<") == formatted.count(">")
            
            # No orphaned tags
            import re
            tag_pattern = r'<(\w+)[^>]*>'
            closing_pattern = r'</(\w+)>'
            
            opening_tags = re.findall(tag_pattern, formatted)
            closing_tags = re.findall(closing_pattern, formatted)
            
            # Self-closing tags don't need closing tags
            self_closing = {'br', 'hr', 'img', 'input', 'meta', 'link'}
            filtered_opening = [tag for tag in opening_tags if tag not in self_closing]
            
            assert len(filtered_opening) == len(closing_tags)
    
    def test_no_markdown_syntax_in_output(self):
        """Critical test: ensure no markdown syntax in formatted output."""
        markdown_syntax = [
            "###", "##", "#",           # Headers
            "**", "*",                  # Bold/italic
            "`", "```",                 # Code
            "- ", "* ",                 # Lists (with space)
            "[", "]", "(", ")",         # Links (when used as markdown)
        ]
        
        test_blocks = [
            "### Heading with **bold** and *italic*",
            "- List with `code` and **emphasis**",
            "**Bold** paragraph with ### heading syntax",
            "`Inline code` with **bold** formatting",
        ]
        
        for block_text in test_blocks:
            formatted = self.formatter.format_block(block_text)
            
            # Check for forbidden markdown syntax in output
            forbidden_found = []
            for syntax in markdown_syntax:
                if syntax in formatted:
                    # Exception: Allow hyphens in actual content (dates, numbers, etc.)
                    if syntax == "- " and any(word in formatted for word in ["2014", "n.", "art.", "comma"]):
                        continue
                    forbidden_found.append(syntax)
            
            assert not forbidden_found, f"Found markdown syntax {forbidden_found} in output: {formatted}"


class TestBlockBuffer:
    """Test the block buffering system for streaming."""
    
    def setup_method(self):
        self.buffer = BlockBuffer()
    
    def test_buffer_accumulation(self):
        """Test buffer accumulates content correctly."""
        chunks = ["First ", "part ", "of ", "sentence."]
        
        for chunk in chunks[:-1]:
            result = self.buffer.add_chunk(chunk)
            assert result is None  # Should not yield until complete
        
        # Last chunk should complete the block
        result = self.buffer.add_chunk(chunks[-1])
        assert result == "First part of sentence."
    
    def test_buffer_reset_after_yield(self):
        """Test buffer resets after yielding a complete block."""
        # Complete first block
        result1 = self.buffer.add_chunk("Complete sentence.\n\n")
        assert result1 == "Complete sentence."
        
        # Buffer should be empty for next content
        result2 = self.buffer.add_chunk("New content")
        assert result2 is None  # Should start accumulating new block
    
    def test_multiple_blocks_in_single_chunk(self):
        """Test handling multiple complete blocks in one chunk."""
        chunk = "First paragraph.\n\nSecond paragraph.\n\n### Heading\n\n"
        
        blocks = self.buffer.add_chunk(chunk)
        assert len(blocks) == 3
        assert blocks[0] == "First paragraph."
        assert blocks[1] == "Second paragraph."
        assert blocks[2] == "### Heading"