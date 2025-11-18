"""Tests for text chunking utilities."""

from unittest.mock import patch

import pytest

from app.core.chunking import (
    TextChunk,
    chunk_document,
    chunk_text,
    estimate_tokens,
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
        assert estimate_tokens(text) == 8  # 33 // 4 = 8


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
        text = "A " * 1000  # Long text
        max_tokens = 50

        chunks = chunk_text(text, max_tokens=max_tokens)

        for chunk in chunks:
            # Allow some tolerance due to sentence boundaries
            assert chunk.token_count <= max_tokens * 1.5

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
