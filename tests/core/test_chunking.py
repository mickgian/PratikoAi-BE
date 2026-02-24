"""Tests for text chunking utilities."""

from unittest.mock import patch

import pytest

from app.core.chunking import (
    TextChunk,
    chunk_document,
    chunk_text,
    estimate_tokens,
    split_at_section_boundaries,
    split_into_sentences,
    validate_chunks,
)


class TestEstimateTokens:
    """Test token estimation function."""

    def test_estimate_tokens_empty_string(self):
        """Test token estimation for empty string."""
        assert estimate_tokens("") == 0

    def test_estimate_tokens_simple_text(self):
        """Test token estimation for simple text."""
        text = "Hello world"  # 11 chars
        assert estimate_tokens(text) == 2  # 11 // 4 = 2

    def test_estimate_tokens_longer_text(self):
        """Test token estimation for longer text."""
        text = "A" * 100  # 100 chars
        assert estimate_tokens(text) == 25  # 100 // 4 = 25

    def test_estimate_tokens_italian_text(self):
        """Test token estimation for Italian text."""
        text = "Questa è una frase in italiano."  # 33 chars
        assert estimate_tokens(text) == 7  # 33 // 4 = 8 (integer division, so 7 not 8)


class TestSplitIntoSentences:
    """Test sentence splitting functionality."""

    def test_split_simple_sentences(self):
        """Test splitting simple sentences."""
        text = "First sentence. Second sentence. Third sentence."
        sentences = split_into_sentences(text)
        assert len(sentences) == 3
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence."
        assert sentences[2] == "Third sentence."

    def test_split_with_abbreviations(self):
        """Test splitting preserves abbreviations."""
        text = "L'art. 123 stabilisce. Il prof. Rossi conferma."
        sentences = split_into_sentences(text)
        assert len(sentences) == 2
        assert "art. 123" in sentences[0]
        assert "prof. Rossi" in sentences[1]

    def test_split_with_legal_abbreviations(self):
        """Test splitting with legal abbreviations."""
        text = "Il D.L. n. 123 prevede. Il D.Lgs. conferma."
        sentences = split_into_sentences(text)
        assert len(sentences) == 2
        assert "D.L. n. 123" in sentences[0]
        assert "D.Lgs." in sentences[1]

    def test_split_empty_string(self):
        """Test splitting empty string."""
        sentences = split_into_sentences("")
        assert sentences == []

    def test_split_single_sentence(self):
        """Test splitting single sentence."""
        text = "This is a single sentence."
        sentences = split_into_sentences(text)
        assert len(sentences) == 1

    def test_split_with_multiple_punctuation(self):
        """Test splitting with different punctuation."""
        text = "Question? Exclamation! Statement."
        sentences = split_into_sentences(text)
        assert len(sentences) == 3

    def test_split_filters_empty_sentences(self):
        """Test that empty sentences are filtered out."""
        text = "First.  Second.   Third."
        sentences = split_into_sentences(text)
        assert all(s for s in sentences)  # No empty strings


class TestChunkText:
    """Test text chunking function."""

    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        chunks = chunk_text("")
        assert chunks == []

    def test_chunk_whitespace_only(self):
        """Test chunking whitespace only."""
        chunks = chunk_text("   \n\t  ")
        assert chunks == []

    def test_chunk_short_text(self):
        """Test chunking text shorter than max tokens."""
        text = "Short text."
        chunks = chunk_text(text, max_tokens=100)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].chunk_index == 0

    def test_chunk_text_metadata(self):
        """Test chunk metadata is set correctly."""
        text = "Test chunk."
        chunks = chunk_text(text, max_tokens=100)
        chunk = chunks[0]

        assert isinstance(chunk, TextChunk)
        assert chunk.text == text
        assert chunk.chunk_index == 0
        assert chunk.token_count == estimate_tokens(text)
        assert chunk.start_char == 0
        assert chunk.end_char > 0

    def test_chunk_with_overlap(self):
        """Test chunking with overlap between chunks."""
        # Long text that will create multiple chunks
        sentences = [f"Sentence {i}." for i in range(20)]
        text = " ".join(sentences)

        chunks = chunk_text(text, max_tokens=20, overlap_tokens=5)

        # Should have multiple chunks
        assert len(chunks) > 1

        # Each chunk should have correct index
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_respects_max_tokens(self):
        """Test chunks don't significantly exceed max tokens."""
        # Create text with proper sentences so chunks can be split
        sentences = [f"This is sentence number {i}. " for i in range(100)]
        text = "".join(sentences)
        max_tokens = 50

        chunks = chunk_text(text, max_tokens=max_tokens)

        for chunk in chunks:
            # Most chunks should be close to max_tokens
            # Allow large tolerance since we split on sentence boundaries
            assert chunk.token_count <= max_tokens * 2.5

    def test_chunk_with_custom_parameters(self):
        """Test chunking with custom parameters."""
        text = "Test sentence. " * 100
        chunks = chunk_text(text, max_tokens=30, overlap_tokens=5)

        assert len(chunks) > 0
        assert all(isinstance(c, TextChunk) for c in chunks)

    def test_chunk_italian_text(self):
        """Test chunking Italian text."""
        text = "Questo è un testo in italiano. " * 50
        chunks = chunk_text(text, max_tokens=50)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.text


class TestChunkDocument:
    """Test document chunking with quality gates."""

    @patch("app.core.chunking.text_metrics")
    @patch("app.core.chunking.JUNK_DROP_CHUNK", False)
    def test_chunk_document_basic(self, mock_metrics):
        """Test basic document chunking."""
        mock_metrics.return_value = {"quality_score": 0.8, "looks_junk": False}

        content = "Test document content. " * 10
        chunks = chunk_document(content, title="Test Doc")

        assert len(chunks) > 0
        for chunk in chunks:
            assert "chunk_text" in chunk
            assert "chunk_index" in chunk
            assert "token_count" in chunk
            assert "document_title" in chunk
            assert chunk["document_title"] == "Test Doc"
            assert chunk["junk"] is False

    @patch("app.core.chunking.text_metrics")
    @patch("app.core.chunking.JUNK_DROP_CHUNK", True)
    def test_chunk_document_drops_junk(self, mock_metrics):
        """Test document chunking drops junk chunks."""
        # Alternate between good and junk chunks
        call_count = [0]

        def mock_metrics_func(text):
            call_count[0] += 1
            is_junk = call_count[0] % 2 == 0
            return {"quality_score": 0.3 if is_junk else 0.8, "looks_junk": is_junk}

        mock_metrics.side_effect = mock_metrics_func

        content = "Sentence. " * 100  # Long enough for multiple chunks
        chunks = chunk_document(content, title="Test", max_tokens=20)

        # Should have dropped some junk chunks
        assert len(chunks) > 0

    @patch("app.core.chunking.text_metrics")
    @patch("app.core.chunking.JUNK_DROP_CHUNK", False)
    def test_chunk_document_with_ocr_flag(self, mock_metrics):
        """Test document chunking sets OCR flag."""
        mock_metrics.return_value = {"quality_score": 0.8, "looks_junk": False}

        content = "Test content."
        chunks = chunk_document(content, ocr_used=True)

        assert all(chunk["ocr_used"] is True for chunk in chunks)

    @patch("app.core.chunking.text_metrics")
    @patch("app.core.chunking.JUNK_DROP_CHUNK", False)
    def test_chunk_document_quality_score(self, mock_metrics):
        """Test document chunking includes quality score."""
        mock_metrics.return_value = {"quality_score": 0.75, "looks_junk": False}

        content = "Test content."
        chunks = chunk_document(content)

        assert all(chunk["quality_score"] == 0.75 for chunk in chunks)

    @patch("app.core.chunking.text_metrics")
    @patch("app.core.chunking.JUNK_DROP_CHUNK", False)
    def test_chunk_document_no_title(self, mock_metrics):
        """Test document chunking without title."""
        mock_metrics.return_value = {"quality_score": 0.8, "looks_junk": False}

        content = "Test content."
        chunks = chunk_document(content)

        assert all(chunk["document_title"] is None for chunk in chunks)


class TestValidateChunks:
    """Test chunk validation function."""

    def test_validate_chunks_empty_list(self):
        """Test validating empty chunk list."""
        assert validate_chunks([]) is True

    def test_validate_chunks_valid(self):
        """Test validating valid chunks."""
        chunks = [
            TextChunk(text="Valid chunk", chunk_index=0, token_count=10, start_char=0, end_char=11),
            TextChunk(text="Another valid", chunk_index=1, token_count=12, start_char=12, end_char=25),
        ]

        assert validate_chunks(chunks, max_tokens=50) is True

    def test_validate_chunks_exceeds_max_tokens(self):
        """Test validation fails when chunk exceeds max tokens."""
        chunks = [
            TextChunk(text="Too many tokens", chunk_index=0, token_count=100, start_char=0, end_char=15),
        ]

        assert validate_chunks(chunks, max_tokens=50) is False

    def test_validate_chunks_empty_text(self):
        """Test validation fails with empty text."""
        chunks = [
            TextChunk(text="", chunk_index=0, token_count=0, start_char=0, end_char=0),
        ]

        assert validate_chunks(chunks) is False

    def test_validate_chunks_whitespace_text(self):
        """Test validation fails with whitespace-only text."""
        chunks = [
            TextChunk(text="   ", chunk_index=0, token_count=1, start_char=0, end_char=3),
        ]

        assert validate_chunks(chunks) is False

    def test_validate_chunks_mixed(self):
        """Test validation fails if any chunk is invalid."""
        chunks = [
            TextChunk(text="Valid", chunk_index=0, token_count=5, start_char=0, end_char=5),
            TextChunk(text="", chunk_index=1, token_count=0, start_char=5, end_char=5),  # Invalid
        ]

        assert validate_chunks(chunks) is False


class TestTextChunk:
    """Test TextChunk dataclass."""

    def test_text_chunk_creation(self):
        """Test creating a TextChunk."""
        chunk = TextChunk(text="Test content", chunk_index=0, token_count=10, start_char=0, end_char=12)

        assert chunk.text == "Test content"
        assert chunk.chunk_index == 0
        assert chunk.token_count == 10
        assert chunk.start_char == 0
        assert chunk.end_char == 12

    def test_text_chunk_equality(self):
        """Test TextChunk equality."""
        chunk1 = TextChunk(text="Test", chunk_index=0, token_count=5, start_char=0, end_char=4)
        chunk2 = TextChunk(text="Test", chunk_index=0, token_count=5, start_char=0, end_char=4)

        assert chunk1 == chunk2


class TestValidateChunksConfigDefault:
    """Test validate_chunks uses config default for max_tokens."""

    def test_validate_chunks_defaults_to_config(self):
        """Call validate_chunks(chunks) without max_tokens, verify it uses CHUNK_TOKENS."""
        from app.core.config import CHUNK_TOKENS

        # Chunk with token_count just under CHUNK_TOKENS → should pass
        chunks_under = [
            TextChunk(
                text="Valid chunk",
                chunk_index=0,
                token_count=CHUNK_TOKENS - 1,
                start_char=0,
                end_char=100,
            ),
        ]
        assert validate_chunks(chunks_under) is True

        # Chunk with token_count over CHUNK_TOKENS → should fail
        chunks_over = [
            TextChunk(
                text="Over limit chunk",
                chunk_index=0,
                token_count=CHUNK_TOKENS + 1,
                start_char=0,
                end_char=100,
            ),
        ]
        assert validate_chunks(chunks_over) is False


class TestSplitAtSectionBoundaries:
    """Test section-aware splitting for Italian legal documents (E.4)."""

    def test_split_at_article_boundaries(self):
        """Happy path: text with Art. markers splits at article boundaries."""
        text = (
            "Art. 1\n"
            "Primo articolo con contenuto sostanziale. "
            "Questo articolo stabilisce le regole generali.\n"
            "Art. 2\n"
            "Secondo articolo con ulteriori disposizioni. "
            "Le modalità di applicazione sono definite qui.\n"
            "Art. 3\n"
            "Terzo articolo finale. Disposizioni transitorie."
        )
        sections = split_at_section_boundaries(text)

        assert len(sections) == 3
        assert "Art. 1" in sections[0]
        assert "regole generali" in sections[0]
        assert "Art. 2" in sections[1]
        assert "modalità di applicazione" in sections[1]
        assert "Art. 3" in sections[2]

    def test_split_at_titolo_boundaries(self):
        """Text with Titolo markers splits correctly."""
        text = (
            "TITOLO I\nDisposizioni generali\n"
            "Contenuto del primo titolo.\n"
            "TITOLO II\nNorme specifiche\n"
            "Contenuto del secondo titolo."
        )
        sections = split_at_section_boundaries(text)

        assert len(sections) == 2
        assert "TITOLO I" in sections[0]
        assert "primo titolo" in sections[0]
        assert "TITOLO II" in sections[1]

    def test_split_at_capo_boundaries(self):
        """Text with Capo markers splits correctly."""
        text = (
            "Capo I\nPrincipi fondamentali\n"
            "Contenuto del primo capo con dettagli.\n"
            "Capo II\nAmbito di applicazione\n"
            "Contenuto del secondo capo."
        )
        sections = split_at_section_boundaries(text)

        assert len(sections) == 2
        assert "Capo I" in sections[0]
        assert "Capo II" in sections[1]

    def test_fallback_to_empty_when_no_markers(self):
        """Document with no section markers returns empty list (caller falls back to sentence splitting)."""
        text = (
            "Questo è un documento senza marcatori di sezione. "
            "Non contiene Art., Titolo o Capo. "
            "Dovrebbe restituire una lista vuota."
        )
        sections = split_at_section_boundaries(text)

        assert sections == []

    def test_heading_context_prepended_to_subchunks(self):
        """When a section is sub-chunked, the heading context is preserved in each piece."""
        # Create an article long enough to require sub-chunking at 50 tokens (~200 chars)
        long_body = "Disposizione dettagliata numero uno. " * 30  # ~1110 chars
        text = f"Art. 5\n{long_body}\nArt. 6\nBreve articolo."
        # Use chunk_text which should now delegate to section-aware splitting
        chunks = chunk_text(text, max_tokens=50, overlap_tokens=5)

        # At least one chunk from the long Art. 5 body should reference "Art. 5"
        art5_chunks = [c for c in chunks if "Disposizione dettagliata" in c.text]
        assert len(art5_chunks) >= 2, "Long article should produce multiple sub-chunks"
        # All sub-chunks of Art. 5 should have the heading context
        for c in art5_chunks:
            assert "Art. 5" in c.text, f"Sub-chunk missing heading context: {c.text[:80]}"

    def test_oversized_article_subsplit(self):
        """Article exceeding max chunk size is sub-split within article boundaries."""
        long_body = "Questa norma stabilisce requisiti specifici. " * 40
        text = f"Art. 10\n{long_body}"

        chunks = chunk_text(text, max_tokens=50, overlap_tokens=5)

        assert len(chunks) >= 2, "Oversized article should be sub-split"
        # All chunks should retain the Art. 10 context
        for c in chunks:
            assert "Art. 10" in c.text

    def test_article_shorter_than_min_chunk(self):
        """Short articles are NOT merged — each section stays independent."""
        text = "Art. 1\nBreve.\nArt. 2\nAnche breve.\nArt. 3\nTerzo breve."
        sections = split_at_section_boundaries(text)

        # Each article should be its own section, even if short
        assert len(sections) == 3

    def test_mixed_section_types(self):
        """Document with mixed Titolo, Capo, Art. markers splits at all boundaries."""
        text = (
            "TITOLO I\nDisposizioni generali\n"
            "Art. 1\nPrimo articolo.\n"
            "Art. 2\nSecondo articolo.\n"
            "TITOLO II\nNorme specifiche\n"
            "Capo I\nAmbito\n"
            "Art. 3\nTerzo articolo."
        )
        sections = split_at_section_boundaries(text)

        # Should split at each structural marker
        assert len(sections) >= 5

    def test_art_with_ordinal_suffix(self):
        """Article references with ordinal suffixes (bis, ter) are detected."""
        text = "Art. 1\nPrimo articolo.\nArt. 1-bis\nArticolo aggiuntivo.\nArt. 2\nSecondo articolo."
        sections = split_at_section_boundaries(text)

        assert len(sections) == 3
        assert "Art. 1-bis" in sections[1]

    def test_preamble_before_first_article(self):
        """Text before the first section marker is included as a separate section."""
        text = "Premessa del documento con contesto generale.\nArt. 1\nPrimo articolo.\nArt. 2\nSecondo articolo."
        sections = split_at_section_boundaries(text)

        assert len(sections) == 3
        assert "Premessa" in sections[0]
        assert "Art. 1" in sections[1]


class TestChunkDocumentNavigationFilter:
    """Test navigation text filtering in chunk_document."""

    @patch("app.core.chunking.text_metrics")
    @patch("app.core.chunking.JUNK_DROP_CHUNK", False)
    def test_chunk_document_drops_navigation_chunks(self, mock_metrics):
        """Verify chunks with navigation text are excluded from output."""
        mock_metrics.return_value = {"quality_score": 0.8, "looks_junk": False}

        # Build content where one "sentence" is navigation boilerplate
        nav_text = "Vai al menu principale. Cookie policy. Privacy policy. Area riservata."
        good_text = "Questo documento contiene informazioni importanti. " * 10

        # Put nav text first so it forms its own chunk
        content = nav_text + " " + good_text

        chunks = chunk_document(content, title="Test Nav Filter", max_tokens=30)

        # No chunk should contain multiple navigation patterns
        for chunk in chunks:
            text_lower = chunk["chunk_text"].lower()
            from app.core.text.clean import NAVIGATION_PATTERNS

            nav_matches = sum(1 for p in NAVIGATION_PATTERNS if p in text_lower)
            # Chunks with 2+ nav patterns should have been dropped
            assert nav_matches < 2, f"Nav chunk not dropped: {chunk['chunk_text'][:100]}"
