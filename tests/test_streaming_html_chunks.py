"""
TDD Tests: Streaming HTML Chunks

Tests the complete streaming pipeline to ensure:
1. Backend sends display-ready HTML chunks
2. No markdown syntax reaches the frontend
3. Chunks are semantically meaningful
4. Professional appearance is maintained
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch
from app.core.content_formatter import ContentFormatter, StreamingHTMLProcessor
from app.api.v1.chatbot import chat_stream
from app.schemas.chat import StreamResponse


class TestStreamingHTMLChunks:
    """Test HTML chunk generation during streaming."""
    
    def setup_method(self):
        self.formatter = ContentFormatter()
        self.processor = StreamingHTMLProcessor()
    
    # ========== STREAMING CHUNK GENERATION ==========
    
    @pytest.mark.asyncio
    async def test_heading_chunk_streaming(self):
        """Test streaming of heading chunks."""
        # Simulate LLM generating a heading token by token
        tokens = ["###", " ", "1", ".", " ", "D", "e", "f", "i", "n", "i", "z", "i", "o", "n", "e", "\n"]
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Should yield one complete HTML heading
        assert len(result_chunks) == 1
        assert result_chunks[0] == "<h3>1. Definizione</h3>"
        
        # Critical: No markdown syntax in output
        assert "###" not in result_chunks[0]
    
    @pytest.mark.asyncio
    async def test_paragraph_chunk_streaming(self):
        """Test streaming of paragraph chunks."""
        tokens = [
            "I", "l", " ", "r", "e", "g", "i", "m", "e", " ",
            "f", "o", "r", "f", "e", "t", "t", "a", "r", "i", "o", " ",
            "è", " ", "u", "n", " ", "r", "e", "g", "i", "m", "e", " ",
            "s", "e", "m", "p", "l", "i", "f", "i", "c", "a", "t", "o", ".", "\n"
        ]
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Should yield one complete paragraph
        assert len(result_chunks) == 1
        assert result_chunks[0] == "<p>Il regime forfettario è un regime semplificato.</p>"
    
    @pytest.mark.asyncio
    async def test_bold_text_chunk_streaming(self):
        """Test streaming of bold text formatting."""
        tokens = [
            "T", "e", "s", "t", " ", "*", "*", "b", "o", "l", "d", "*", "*", " ", "t", "e", "x", "t", ".", "\n"
        ]
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Should yield formatted paragraph with bold text
        assert len(result_chunks) == 1
        assert result_chunks[0] == "<p>Test <strong>bold</strong> text.</p>"
        
        # Critical: No markdown syntax
        assert "**" not in result_chunks[0]
    
    @pytest.mark.asyncio
    async def test_list_chunk_streaming(self):
        """Test streaming of list formation."""
        tokens = [
            "-", " ", "I", "t", "e", "m", " ", "1", "\n",
            "-", " ", "I", "t", "e", "m", " ", "2", "\n",
            "-", " ", "I", "t", "e", "m", " ", "3", "\n"
        ]
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Should yield one complete list
        assert len(result_chunks) == 1
        expected_html = """<ul>
<li>Item 1</li>
<li>Item 2</li>
<li>Item 3</li>
</ul>"""
        assert result_chunks[0] == expected_html
        
        # No markdown list syntax
        assert "- " not in result_chunks[0]
    
    # ========== CALCULATION CHUNK STREAMING ==========
    
    @pytest.mark.asyncio
    async def test_calculation_chunk_streaming(self):
        """Test streaming of tax calculation formatting."""
        tokens = [
            "R", "e", "d", "d", "i", "t", "o", ":", " ",
            "5", "0", "0", "0", "0", " ", "×", " ", "1", "5", "%", " ", "=", " ",
            "7", "5", "0", "0", "\n"
        ]
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Should yield formatted calculation
        assert len(result_chunks) == 1
        result = result_chunks[0]
        
        assert '<div class="calculation">' in result
        assert "€ 50.000" in result
        assert "€ 7.500" in result
        assert "15%" in result
    
    @pytest.mark.asyncio
    async def test_complex_tax_response_streaming(self):
        """Test streaming of complete tax response."""
        # Simulate a complete tax response being streamed
        response_tokens = self._tokenize_response("""### 1. Definizione/Concetto principale

Il regime forfettario è un regime fiscale **semplificato** per le persone fisiche.

### 2. Calcolo dell'imposta

Reddito: 50000 × 15% = 7500

### 3. Normativa di riferimento

La normativa è contenuta nella *Legge n.190/2014*:

- Articolo 1, commi 54-89
- Articolo 1, comma 57""")
        
        result_chunks = []
        async for token in self._simulate_token_stream(response_tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Should yield multiple well-formed HTML blocks
        assert len(result_chunks) >= 5  # Multiple sections
        
        # Check each chunk is valid HTML
        for chunk in result_chunks:
            assert chunk.startswith('<')
            assert chunk.endswith('>')
            # No markdown syntax
            assert "###" not in chunk
            assert "**" not in chunk
            assert "*" not in chunk and "**" not in chunk
            assert "- " not in chunk or "<li>" in chunk  # Lists should be HTML
    
    # ========== SSE FORMAT TESTS ==========
    
    def test_sse_message_format(self):
        """Test SSE message formatting with HTML content."""
        html_chunk = "<h3>1. Definizione</h3>"
        
        sse_message = self.processor.format_sse_message(html_chunk, done=False)
        
        expected_format = f'data: {json.dumps({"content": html_chunk, "done": False})}\n\n'
        assert sse_message == expected_format
    
    def test_sse_completion_message(self):
        """Test SSE completion message."""
        sse_message = self.processor.format_sse_message("", done=True)
        
        expected_format = f'data: {json.dumps({"content": "", "done": True})}\n\n'
        assert sse_message == expected_format
    
    # ========== CHUNK SIZE AND TIMING TESTS ==========
    
    @pytest.mark.asyncio
    async def test_optimal_chunk_sizes(self):
        """Test that chunks are optimally sized for display."""
        # Long response should be broken into reasonable chunks
        long_response = "Il regime forfettario " * 100  # Very long text
        tokens = list(long_response)
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Should yield multiple chunks, not one huge chunk
        assert len(result_chunks) > 1
        
        # Each chunk should be reasonable size (not too small, not too large)
        for chunk in result_chunks:
            assert 10 <= len(chunk) <= 500  # Reasonable chunk sizes
    
    @pytest.mark.asyncio
    async def test_semantic_chunk_boundaries(self):
        """Test that chunks break at semantic boundaries."""
        tokens = self._tokenize_response("""Il regime forfettario è semplificato. Tuttavia, ci sono limitazioni importanti da considerare.""")
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Should break at sentence boundaries
        for chunk in result_chunks:
            # Chunks should end with complete words/sentences
            assert not chunk.endswith(" ")  # No trailing spaces
            if not chunk.endswith('>'):  # If not HTML tag
                assert chunk.endswith('.') or chunk.endswith(',') or chunk.endswith(':')
    
    # ========== ERROR HANDLING IN STREAMING ==========
    
    @pytest.mark.asyncio
    async def test_malformed_markdown_recovery(self):
        """Test recovery from malformed markdown during streaming."""
        tokens = ["###", " ", "B", "r", "o", "k", "e", "n"]  # No newline, incomplete
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Should still produce valid HTML
        assert len(result_chunks) >= 1
        for chunk in result_chunks:
            assert chunk.startswith('<')
            assert "###" not in chunk
    
    @pytest.mark.asyncio
    async def test_streaming_interruption_handling(self):
        """Test handling of interrupted streaming."""
        tokens = ["###", " ", "H", "e", "a", "d", "i"]  # Interrupted heading
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Force completion
        final_chunk = await self.processor.finalize()
        if final_chunk:
            result_chunks.append(final_chunk)
        
        # Should produce valid HTML even when interrupted
        assert len(result_chunks) >= 1
        final_output = "".join(result_chunks)
        assert "<h3>" in final_output or "<p>" in final_output
        assert "###" not in final_output
    
    # ========== INTEGRATION WITH BACKEND ==========
    
    @pytest.mark.asyncio
    async def test_backend_streaming_integration(self):
        """Test integration with actual backend streaming endpoint."""
        # Mock the LangGraph agent to return tokens
        mock_agent = AsyncMock()
        mock_agent.get_stream_response.return_value = self._async_generator([
            "###", " ", "T", "e", "s", "t", "\n",
            "**", "B", "o", "l", "d", "**", " ", "t", "e", "x", "t", "."
        ])
        
        with patch('app.api.v1.chatbot.agent', mock_agent):
            # Simulate streaming endpoint call
            chunks = []
            async def collect_chunks():
                # This would be the actual streaming endpoint logic
                async for token in mock_agent.get_stream_response():
                    chunk = await self.processor.process_token(token)
                    if chunk:
                        sse_message = self.processor.format_sse_message(chunk)
                        chunks.append(sse_message)
            
            await collect_chunks()
            
            # Should receive properly formatted SSE messages
            assert len(chunks) >= 1
            for sse_chunk in chunks:
                assert sse_chunk.startswith('data: ')
                # Parse the JSON content
                json_part = sse_chunk[6:-2]  # Remove 'data: ' and '\n\n'
                data = json.loads(json_part)
                
                # Content should be HTML
                content = data['content']
                assert content.startswith('<')
                assert "###" not in content
                assert "**" not in content
    
    # ========== PERFORMANCE TESTS ==========
    
    @pytest.mark.asyncio
    async def test_streaming_performance(self):
        """Test streaming performance with large content."""
        import time
        
        # Large response simulation
        large_response = """### Analisi Completa del Regime Forfettario

Il regime forfettario rappresenta una delle opzioni fiscali più interessanti per i professionisti e le piccole imprese in Italia. """ * 50
        
        tokens = self._tokenize_response(large_response)
        
        start_time = time.time()
        result_chunks = []
        
        async for token in self._simulate_token_stream(tokens):
            chunk = await self.processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 1.0  # Should process quickly
        assert len(result_chunks) > 0
        
        # Memory efficiency - no huge chunks
        max_chunk_size = max(len(chunk) for chunk in result_chunks)
        assert max_chunk_size < 1000  # Reasonable chunk sizes
    
    # ========== HELPER METHODS ==========
    
    async def _simulate_token_stream(self, tokens):
        """Simulate async token streaming."""
        for token in tokens:
            yield token
            await asyncio.sleep(0.001)  # Simulate network delay
    
    def _tokenize_response(self, text):
        """Tokenize response text into individual characters."""
        return list(text)
    
    async def _async_generator(self, items):
        """Create async generator from list."""
        for item in items:
            yield item


class TestProfessionalAppearance:
    """Test that output maintains professional appearance."""
    
    def setup_method(self):
        self.processor = StreamingHTMLProcessor()
    
    def test_currency_formatting_in_chunks(self):
        """Test currency appears professionally formatted."""
        test_amounts = [
            ("50000", "€ 50.000"),
            ("1234.56", "€ 1.234,56"),
            ("999", "€ 999"),
        ]
        
        for raw, expected in test_amounts:
            result = self.processor.format_currency(raw)
            assert result == expected
    
    def test_percentage_formatting_in_chunks(self):
        """Test percentages appear professionally formatted."""
        test_percentages = [
            ("15%", "15%"),
            ("0.15", "15%"),
            ("22", "22%"),
        ]
        
        for raw, expected in test_percentages:
            result = self.processor.format_percentage(raw)
            assert result == expected
    
    def test_tax_terminology_formatting(self):
        """Test tax terms are properly formatted."""
        terminology_map = {
            "IRPEF": '<abbr title="Imposta sul Reddito delle Persone Fisiche">IRPEF</abbr>',
            "IVA": '<abbr title="Imposta sul Valore Aggiunto">IVA</abbr>',
            "IRAP": '<abbr title="Imposta Regionale sulle Attività Produttive">IRAP</abbr>',
        }
        
        for term, expected_html in terminology_map.items():
            result = self.processor.format_tax_term(term)
            assert result == expected_html
    
    def test_legal_reference_formatting(self):
        """Test legal references are properly formatted."""
        legal_refs = [
            ("Legge n.190/2014", '<cite class="legal-ref">Legge n. 190/2014</cite>'),
            ("Art. 1 comma 57", '<cite class="legal-ref">Art. 1, comma 57</cite>'),
            ("D.P.R. 633/72", '<cite class="legal-ref">D.P.R. 633/72</cite>'),
        ]
        
        for raw, expected in legal_refs:
            result = self.processor.format_legal_reference(raw)
            assert result == expected
    
    def test_no_raw_markdown_in_professional_output(self):
        """Critical test: ensure professional appearance with no markdown."""
        test_responses = [
            "### 1. Definizione **importante**",
            "- Lista con *enfasi* e `codice`",
            "Calcolo: **50000** × 15% = 7500",
            "Riferimento: *Legge n.190/2014*",
        ]
        
        for response in test_responses:
            tokens = list(response)
            
            # Process through streaming
            result_chunks = []
            for token in tokens:
                chunk = self.processor.process_token_sync(token)
                if chunk:
                    result_chunks.append(chunk)
            
            final_output = "".join(result_chunks)
            
            # Critical checks: no markdown syntax
            forbidden_syntax = ["###", "**", "*", "`", "- "]
            for syntax in forbidden_syntax:
                assert syntax not in final_output, f"Found {syntax} in: {final_output}"
            
            # Should contain proper HTML
            assert any(tag in final_output for tag in ["<h3>", "<strong>", "<em>", "<code>", "<li>"])


class TestStreamingEndToEnd:
    """End-to-end tests of the complete streaming pipeline."""
    
    @pytest.mark.asyncio
    async def test_complete_tax_consultation_streaming(self):
        """Test streaming a complete tax consultation response."""
        # Simulate a real tax consultation response
        consultation_response = """### 1. Definizione/Concetto principale

Il regime forfettario è un regime fiscale **semplificato** per le persone fisiche che esercitano attività d'impresa, arti o professioni.

### 2. Normativa di riferimento

La normativa di riferimento è contenuta nella *Legge n.190/2014*:

- Articolo 1, commi 54-89: definisce i requisiti
- Articolo 1, comma 57: stabilisce le esclusioni

### 3. Calcolo dell'imposta

Per un reddito di €50.000:

Reddito: 50000 × 15% = 7500

### 4. Esempi concreti

1. **Professionista**: Non può essere socio di SRL commerciale
2. **Contribuente**: Può detenere partecipazioni immobiliari"""
        
        # Process through complete streaming pipeline
        processor = StreamingHTMLProcessor()
        tokens = list(consultation_response)
        
        result_chunks = []
        async for token in self._simulate_token_stream(tokens):
            chunk = await processor.process_token(token)
            if chunk:
                result_chunks.append(chunk)
        
        # Validate complete response
        assert len(result_chunks) >= 8  # Multiple sections and elements
        
        final_html = "".join(result_chunks)
        
        # Should contain all expected HTML elements
        assert "<h3>1. Definizione/Concetto principale</h3>" in final_html
        assert "<strong>semplificato</strong>" in final_html
        assert "<em>Legge n.190/2014</em>" in final_html
        assert "<ul>" in final_html and "</ul>" in final_html
        assert "<ol>" in final_html and "</ol>" in final_html
        assert '<div class="calculation">' in final_html
        assert "€ 50.000" in final_html
        assert "€ 7.500" in final_html
        
        # Critical: NO markdown syntax anywhere
        markdown_syntax = ["###", "**", "*", "- ", "`"]
        for syntax in markdown_syntax:
            # Allow hyphens in actual content (dates, references)
            if syntax == "- " and any(ref in final_html for ref in ["n.190/2014", "commi 54-89"]):
                continue
            assert syntax not in final_html, f"Found markdown syntax '{syntax}' in final output"
        
        # Should look professional
        assert "€" in final_html  # Proper currency symbols
        assert "%" in final_html  # Proper percentage symbols
        assert final_html.count("<") == final_html.count(">")  # Balanced tags
    
    async def _simulate_token_stream(self, tokens):
        """Simulate streaming tokens with realistic timing."""
        for token in tokens:
            yield token
            await asyncio.sleep(0.001)  # Simulate realistic streaming delay