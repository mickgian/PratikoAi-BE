"""Tests for knowledge chunk models."""

from datetime import UTC, datetime
import time

import pytest

from app.models.knowledge_chunk import KnowledgeChunk


class TestKnowledgeChunk:
    """Test KnowledgeChunk model."""

    def test_create_chunk_minimal(self):
        """Test creating knowledge chunk with required fields."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            chunk_text="Questo è un chunk di prova per il sistema RAG.",
            chunk_index=0,
            token_count=12,
            kb_epoch=kb_epoch,
        )

        assert chunk.chunk_text == "Questo è un chunk di prova per il sistema RAG."
        assert chunk.chunk_index == 0
        assert chunk.token_count == 12
        assert chunk.kb_epoch == kb_epoch
        assert chunk.knowledge_item_id is None
        assert chunk.search_vector is None
        assert chunk.embedding is None
        assert chunk.source_url is None
        assert chunk.document_title is None
        assert chunk.quality_score is None
        assert chunk.junk is False
        assert chunk.ocr_used is False
        assert chunk.start_char is None
        assert chunk.end_char is None

    def test_create_chunk_with_parent(self):
        """Test creating chunk with parent knowledge item."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            knowledge_item_id=123,
            chunk_text="Chunk con riferimento al parent.",
            chunk_index=2,
            token_count=8,
            kb_epoch=kb_epoch,
        )

        assert chunk.knowledge_item_id == 123
        assert chunk.chunk_index == 2

    def test_create_chunk_with_embeddings(self):
        """Test creating chunk with vector embeddings."""
        kb_epoch = time.time()
        # Simulate 1536-dimensional embedding (just first few dimensions for test)
        embedding = [0.1] * 1536

        chunk = KnowledgeChunk(
            chunk_text="Chunk con embedding vettoriale.",
            chunk_index=0,
            token_count=6,
            kb_epoch=kb_epoch,
            embedding=embedding,
        )

        assert chunk.embedding is not None
        assert len(chunk.embedding) == 1536
        assert chunk.embedding[0] == 0.1

    def test_create_chunk_with_metadata(self):
        """Test creating chunk with complete metadata."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            knowledge_item_id=456,
            chunk_text="Le detrazioni fiscali per il 2025 includono...",
            chunk_index=1,
            token_count=15,
            kb_epoch=kb_epoch,
            source_url="https://agenziaentrate.gov.it/detrazioni-2025",
            document_title="Guida Detrazioni Fiscali 2025",
        )

        assert chunk.source_url == "https://agenziaentrate.gov.it/detrazioni-2025"
        assert chunk.document_title == "Guida Detrazioni Fiscali 2025"

    def test_create_chunk_with_quality_tracking(self):
        """Test creating chunk with quality metrics."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            chunk_text="High quality chunk content.",
            chunk_index=0,
            token_count=5,
            kb_epoch=kb_epoch,
            quality_score=0.95,
            junk=False,
            ocr_used=False,
        )

        assert chunk.quality_score == 0.95
        assert chunk.junk is False
        assert chunk.ocr_used is False

    def test_create_chunk_low_quality(self):
        """Test creating low quality/junk chunk."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            chunk_text="���garbled text���",
            chunk_index=5,
            token_count=3,
            kb_epoch=kb_epoch,
            quality_score=0.15,
            junk=True,
        )

        assert chunk.quality_score == 0.15
        assert chunk.junk is True

    def test_create_chunk_with_ocr(self):
        """Test creating chunk extracted via OCR."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            chunk_text="Testo estratto tramite OCR da PDF scansionato.",
            chunk_index=0,
            token_count=10,
            kb_epoch=kb_epoch,
            quality_score=0.78,
            ocr_used=True,
        )

        assert chunk.ocr_used is True
        assert chunk.quality_score == 0.78

    def test_create_chunk_with_character_positions(self):
        """Test creating chunk with character position tracking."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            knowledge_item_id=789,
            chunk_text="Chunk dal documento originale.",
            chunk_index=3,
            token_count=6,
            kb_epoch=kb_epoch,
            start_char=1500,
            end_char=1530,
        )

        assert chunk.start_char == 1500
        assert chunk.end_char == 1530
        assert chunk.end_char - chunk.start_char == 30

    def test_chunk_timestamp_auto_created(self):
        """Test that timestamp is automatically created."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            chunk_text="Test chunk for timestamp.",
            chunk_index=0,
            token_count=5,
            kb_epoch=kb_epoch,
        )

        assert chunk.created_at is not None
        assert isinstance(chunk.created_at, datetime)

    def test_create_chunk_first_in_document(self):
        """Test creating first chunk of a document."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            knowledge_item_id=1,
            chunk_text="Questo è il primo chunk del documento. Introduce l'argomento principale.",
            chunk_index=0,
            token_count=16,
            kb_epoch=kb_epoch,
            start_char=0,
            end_char=73,
            quality_score=0.92,
        )

        assert chunk.chunk_index == 0
        assert chunk.start_char == 0
        assert chunk.quality_score == 0.92

    def test_create_chunk_middle_of_document(self):
        """Test creating middle chunk of a document."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            knowledge_item_id=1,
            chunk_text="Dettagli tecnici della normativa fiscale italiana del 2025.",
            chunk_index=5,
            token_count=12,
            kb_epoch=kb_epoch,
            start_char=2500,
            end_char=2561,
            quality_score=0.88,
        )

        assert chunk.chunk_index == 5
        assert chunk.start_char > 0

    def test_create_chunk_with_search_vector(self):
        """Test creating chunk with search vector (normally set by DB trigger)."""
        kb_epoch = time.time()

        chunk = KnowledgeChunk(
            chunk_text="Tasse e contributi INPS per il 2025.",
            chunk_index=0,
            token_count=8,
            kb_epoch=kb_epoch,
            search_vector="'2025':5 'contributi':3 'inps':4 'tasse':1",
        )

        assert chunk.search_vector is not None
        assert "tasse" in chunk.search_vector.lower()

    def test_chunk_kb_epoch_recency(self):
        """Test kb_epoch for recency tracking."""
        old_epoch = time.time() - (365 * 24 * 60 * 60)  # 1 year ago
        recent_epoch = time.time()

        old_chunk = KnowledgeChunk(
            chunk_text="Old content from 2024",
            chunk_index=0,
            token_count=5,
            kb_epoch=old_epoch,
        )

        recent_chunk = KnowledgeChunk(
            chunk_text="Recent content from 2025",
            chunk_index=0,
            token_count=5,
            kb_epoch=recent_epoch,
        )

        assert old_chunk.kb_epoch < recent_chunk.kb_epoch

    def test_create_multiple_chunks_from_same_document(self):
        """Test creating multiple chunks from the same document."""
        kb_epoch = time.time()
        doc_id = 100

        chunks = [
            KnowledgeChunk(
                knowledge_item_id=doc_id,
                chunk_text="Primo chunk del documento.",
                chunk_index=0,
                token_count=5,
                kb_epoch=kb_epoch,
                start_char=0,
                end_char=26,
            ),
            KnowledgeChunk(
                knowledge_item_id=doc_id,
                chunk_text="Secondo chunk del documento.",
                chunk_index=1,
                token_count=5,
                kb_epoch=kb_epoch,
                start_char=27,
                end_char=55,
            ),
            KnowledgeChunk(
                knowledge_item_id=doc_id,
                chunk_text="Terzo chunk del documento.",
                chunk_index=2,
                token_count=5,
                kb_epoch=kb_epoch,
                start_char=56,
                end_char=82,
            ),
        ]

        # Verify all chunks have same parent
        assert all(c.knowledge_item_id == doc_id for c in chunks)
        # Verify indices are sequential
        assert [c.chunk_index for c in chunks] == [0, 1, 2]
        # Verify character positions don't overlap
        assert chunks[0].end_char < chunks[1].start_char
        assert chunks[1].end_char < chunks[2].start_char

    def test_chunk_with_all_fields(self):
        """Test creating chunk with all possible fields populated."""
        kb_epoch = time.time()
        embedding = [0.05] * 1536

        chunk = KnowledgeChunk(
            knowledge_item_id=999,
            chunk_text="Chunk completo con tutti i campi popolati per test di copertura.",
            chunk_index=7,
            token_count=13,
            search_vector="'campi':5 'chunk':1 'completo':2",
            embedding=embedding,
            kb_epoch=kb_epoch,
            source_url="https://example.com/document.pdf",
            document_title="Documento di Test Completo",
            quality_score=0.87,
            junk=False,
            ocr_used=True,
            start_char=3500,
            end_char=3565,
        )

        # Verify all fields are set
        assert chunk.knowledge_item_id == 999
        assert chunk.chunk_index == 7
        assert chunk.token_count == 13
        assert chunk.search_vector is not None
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 1536
        assert chunk.source_url is not None
        assert chunk.document_title is not None
        assert chunk.quality_score == 0.87
        assert chunk.junk is False
        assert chunk.ocr_used is True
        assert chunk.start_char == 3500
        assert chunk.end_char == 3565
        assert chunk.created_at is not None
