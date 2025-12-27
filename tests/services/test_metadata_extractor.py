"""TDD Tests for DEV-191: Document Metadata Preservation Layer.

Tests for DocumentMetadata extraction and context formatting per Section 13.9.
"""

from datetime import datetime, timedelta

import pytest


class TestDocumentMetadataSchema:
    """Tests for DocumentMetadata dataclass."""

    def test_document_metadata_creation(self):
        """Test creating DocumentMetadata with all fields."""
        from app.services.metadata_extractor import DocumentMetadata

        doc = DocumentMetadata(
            document_id="doc_123",
            title="Circolare n. 9/E del 2025",
            date_published=datetime(2025, 3, 15),
            source_entity="Agenzia delle Entrate",
            document_type="circolare",
            hierarchy_level=3,
            reference_code="Circ. 9/E/2025",
            url="https://www.agenziaentrate.gov.it/circolare-9e",
            relevance_score=0.85,
            text_excerpt="Ai sensi dell'art. 13 del D.Lgs. 472/1997...",
        )

        assert doc.document_id == "doc_123"
        assert doc.title == "Circolare n. 9/E del 2025"
        assert doc.date_published == datetime(2025, 3, 15)
        assert doc.source_entity == "Agenzia delle Entrate"
        assert doc.document_type == "circolare"
        assert doc.hierarchy_level == 3
        assert doc.reference_code == "Circ. 9/E/2025"
        assert doc.url == "https://www.agenziaentrate.gov.it/circolare-9e"
        assert doc.relevance_score == 0.85
        assert "D.Lgs. 472/1997" in doc.text_excerpt

    def test_document_metadata_optional_url(self):
        """Test DocumentMetadata with optional URL as None."""
        from app.services.metadata_extractor import DocumentMetadata

        doc = DocumentMetadata(
            document_id="doc_456",
            title="FAQ Ravvedimento",
            date_published=datetime(2024, 1, 10),
            source_entity="Agenzia delle Entrate",
            document_type="faq",
            hierarchy_level=6,
            reference_code="FAQ-RAV-001",
            url=None,
            relevance_score=0.75,
            text_excerpt="Il ravvedimento operoso consente...",
        )

        assert doc.url is None
        assert doc.document_type == "faq"


class TestHierarchyLevels:
    """Tests for hierarchy level constants."""

    def test_hierarchy_levels_defined(self):
        """Test that hierarchy levels are properly defined."""
        from app.services.metadata_extractor import HIERARCHY_LEVELS

        assert HIERARCHY_LEVELS["legge"] == 1
        assert HIERARCHY_LEVELS["decreto"] == 2
        assert HIERARCHY_LEVELS["circolare"] == 3
        assert HIERARCHY_LEVELS["risoluzione"] == 4
        assert HIERARCHY_LEVELS["interpello"] == 5
        assert HIERARCHY_LEVELS["faq"] == 6

    def test_get_hierarchy_level_for_known_type(self):
        """Test getting hierarchy level for known document type."""
        from app.services.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()

        assert extractor.get_hierarchy_level("legge") == 1
        assert extractor.get_hierarchy_level("circolare") == 3
        assert extractor.get_hierarchy_level("faq") == 6

    def test_get_hierarchy_level_for_unknown_type(self):
        """Test getting hierarchy level for unknown document type returns default."""
        from app.services.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()

        # Unknown types should return highest level (lowest priority)
        assert extractor.get_hierarchy_level("unknown") == 99
        assert extractor.get_hierarchy_level("altro") == 99


class TestMetadataExtraction:
    """Tests for extracting metadata from RankedDocuments."""

    def test_extract_from_ranked_document(self):
        """Test extracting DocumentMetadata from RankedDocument."""
        from datetime import datetime

        from app.services.metadata_extractor import MetadataExtractor
        from app.services.parallel_retrieval import RankedDocument

        extractor = MetadataExtractor()

        ranked_doc = RankedDocument(
            document_id="doc_001",
            content="Contenuto del documento con riferimento all'art. 1...",
            score=0.9,
            rrf_score=0.045,
            source_type="legge",
            source_name="Legge 190/2014",
            published_date=datetime(2014, 12, 23),
            metadata={
                "title": "Legge di Stabilità 2015",
                "source_entity": "Parlamento Italiano",
                "reference_code": "Art. 1, commi 54-89, L. 190/2014",
                "url": "https://www.normattiva.it/legge-190-2014",
            },
        )

        doc_metadata = extractor.extract(ranked_doc)

        assert doc_metadata.document_id == "doc_001"
        assert doc_metadata.title == "Legge di Stabilità 2015"
        assert doc_metadata.document_type == "legge"
        assert doc_metadata.hierarchy_level == 1
        assert doc_metadata.relevance_score == 0.045  # Uses rrf_score

    def test_extract_with_missing_metadata_fields(self):
        """Test extraction handles missing metadata fields gracefully."""
        from datetime import datetime

        from app.services.metadata_extractor import MetadataExtractor
        from app.services.parallel_retrieval import RankedDocument

        extractor = MetadataExtractor()

        ranked_doc = RankedDocument(
            document_id="doc_002",
            content="Contenuto senza metadati extra...",
            score=0.8,
            rrf_score=0.035,
            source_type="circolare",
            source_name="Circolare 10/E/2024",
            published_date=datetime(2024, 5, 1),
            metadata={},  # Empty metadata
        )

        doc_metadata = extractor.extract(ranked_doc)

        # Should use source_name as fallback for title
        assert doc_metadata.title == "Circolare 10/E/2024"
        # Should derive reference_code from source_name
        assert "10/E/2024" in doc_metadata.reference_code
        # URL should be None
        assert doc_metadata.url is None


class TestDocumentSorting:
    """Tests for document sorting by date."""

    def test_documents_sorted_by_date_recent_first(self):
        """Test that documents are sorted by date with most recent first."""
        from app.services.metadata_extractor import DocumentMetadata, MetadataExtractor

        extractor = MetadataExtractor()

        docs = [
            DocumentMetadata(
                document_id="old",
                title="Old Document",
                date_published=datetime(2020, 1, 1),
                source_entity="Entity",
                document_type="legge",
                hierarchy_level=1,
                reference_code="REF-001",
                url=None,
                relevance_score=0.9,
                text_excerpt="Old content",
            ),
            DocumentMetadata(
                document_id="new",
                title="New Document",
                date_published=datetime(2025, 6, 15),
                source_entity="Entity",
                document_type="circolare",
                hierarchy_level=3,
                reference_code="REF-002",
                url=None,
                relevance_score=0.8,
                text_excerpt="New content",
            ),
            DocumentMetadata(
                document_id="mid",
                title="Mid Document",
                date_published=datetime(2023, 3, 10),
                source_entity="Entity",
                document_type="faq",
                hierarchy_level=6,
                reference_code="REF-003",
                url=None,
                relevance_score=0.7,
                text_excerpt="Mid content",
            ),
        ]

        sorted_docs = extractor.sort_by_date(docs)

        assert sorted_docs[0].document_id == "new"
        assert sorted_docs[1].document_id == "mid"
        assert sorted_docs[2].document_id == "old"

    def test_sort_handles_same_date(self):
        """Test sorting when documents have the same date."""
        from app.services.metadata_extractor import DocumentMetadata, MetadataExtractor

        extractor = MetadataExtractor()

        same_date = datetime(2024, 6, 1)
        docs = [
            DocumentMetadata(
                document_id="doc_a",
                title="Document A",
                date_published=same_date,
                source_entity="Entity",
                document_type="legge",
                hierarchy_level=1,
                reference_code="REF-A",
                url=None,
                relevance_score=0.5,
                text_excerpt="A",
            ),
            DocumentMetadata(
                document_id="doc_b",
                title="Document B",
                date_published=same_date,
                source_entity="Entity",
                document_type="circolare",
                hierarchy_level=3,
                reference_code="REF-B",
                url=None,
                relevance_score=0.9,
                text_excerpt="B",
            ),
        ]

        sorted_docs = extractor.sort_by_date(docs)

        # Should maintain stable sort or sort by relevance as secondary
        assert len(sorted_docs) == 2


class TestContextFormatting:
    """Tests for format_context_for_synthesis function."""

    def test_format_context_header(self):
        """Test that context includes header with statistics."""
        from app.services.metadata_extractor import MetadataExtractor
        from app.services.parallel_retrieval import RetrievalResult

        extractor = MetadataExtractor()

        result = RetrievalResult(
            documents=[],
            total_found=5,
            search_time_ms=250.5,
        )

        context = extractor.format_context_for_synthesis(result)

        assert "Documenti Recuperati: 0" in context
        assert "250" in context or "251" in context  # Rounded time

    def test_format_context_document_structure(self):
        """Test that each document has proper structure in context."""
        from app.services.metadata_extractor import MetadataExtractor
        from app.services.parallel_retrieval import RankedDocument, RetrievalResult

        extractor = MetadataExtractor()

        doc = RankedDocument(
            document_id="doc_test",
            content="Contenuto del documento di test...",
            score=0.9,
            rrf_score=0.05,
            source_type="circolare",
            source_name="Circolare 9/E/2025",
            published_date=datetime(2025, 3, 15),
            metadata={
                "title": "Circolare su regime forfettario",
                "source_entity": "Agenzia delle Entrate",
                "reference_code": "Circ. 9/E/2025",
                "url": "https://example.com/circ-9e",
            },
        )

        result = RetrievalResult(
            documents=[doc],
            total_found=1,
            search_time_ms=100.0,
        )

        context = extractor.format_context_for_synthesis(result)

        # Check document markers
        assert "DOCUMENTO 1" in context
        # Check date format (DD/MM/YYYY)
        assert "15/03/2025" in context
        # Check entity
        assert "Agenzia delle Entrate" in context
        # Check type and hierarchy
        assert "circolare" in context.lower()
        assert "Livello gerarchico" in context or "gerarchico" in context.lower()
        # Check reference
        assert "Circ. 9/E/2025" in context
        # Check URL
        assert "https://example.com/circ-9e" in context
        # Check content
        assert "Contenuto del documento di test" in context

    def test_format_context_url_na_when_missing(self):
        """Test that URL shows N/A when not available."""
        from app.services.metadata_extractor import MetadataExtractor
        from app.services.parallel_retrieval import RankedDocument, RetrievalResult

        extractor = MetadataExtractor()

        doc = RankedDocument(
            document_id="doc_no_url",
            content="Content without URL...",
            score=0.8,
            rrf_score=0.04,
            source_type="faq",
            source_name="FAQ-001",
            published_date=datetime(2024, 1, 1),
            metadata={},  # No URL in metadata
        )

        result = RetrievalResult(
            documents=[doc],
            total_found=1,
            search_time_ms=50.0,
        )

        context = extractor.format_context_for_synthesis(result)

        assert "N/A" in context or "n/a" in context.lower()

    def test_format_context_documents_sorted(self):
        """Test that documents in context are sorted by date (recent first)."""
        from app.services.metadata_extractor import MetadataExtractor
        from app.services.parallel_retrieval import RankedDocument, RetrievalResult

        extractor = MetadataExtractor()

        old_doc = RankedDocument(
            document_id="old",
            content="Old content",
            score=0.9,
            rrf_score=0.05,
            source_type="legge",
            source_name="Legge 2010",
            published_date=datetime(2010, 1, 1),
            metadata={"title": "Old Law"},
        )

        new_doc = RankedDocument(
            document_id="new",
            content="New content",
            score=0.8,
            rrf_score=0.04,
            source_type="circolare",
            source_name="Circolare 2025",
            published_date=datetime(2025, 6, 1),
            metadata={"title": "New Circular"},
        )

        result = RetrievalResult(
            documents=[old_doc, new_doc],  # Old first in input
            total_found=2,
            search_time_ms=100.0,
        )

        context = extractor.format_context_for_synthesis(result)

        # New document (2025) should appear before old document (2010)
        new_pos = context.find("2025")
        old_pos = context.find("2010")
        assert new_pos < old_pos, "Documents should be sorted by date (recent first)"


class TestReferenceCodeFormatting:
    """Tests for reference code formatting."""

    def test_format_reference_code_legge(self):
        """Test reference code formatting for legge."""
        from app.services.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()

        ref = extractor.format_reference_code(
            source_type="legge",
            source_name="Legge 190/2014",
            metadata={},
        )

        assert "L. 190/2014" in ref or "Legge 190/2014" in ref

    def test_format_reference_code_circolare(self):
        """Test reference code formatting for circolare."""
        from app.services.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()

        ref = extractor.format_reference_code(
            source_type="circolare",
            source_name="Circolare 9/E/2025",
            metadata={},
        )

        assert "Circ." in ref or "Circolare" in ref
        assert "9/E/2025" in ref

    def test_format_reference_code_from_metadata(self):
        """Test that explicit reference_code in metadata takes precedence."""
        from app.services.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()

        ref = extractor.format_reference_code(
            source_type="circolare",
            source_name="Something",
            metadata={"reference_code": "Art. 1, comma 3, Circ. 9/E/2025"},
        )

        assert ref == "Art. 1, comma 3, Circ. 9/E/2025"


class TestFullExtractionFlow:
    """Integration tests for full metadata extraction flow."""

    def test_extract_all_from_retrieval_result(self):
        """Test extracting all metadata from a RetrievalResult."""
        from app.services.metadata_extractor import MetadataExtractor
        from app.services.parallel_retrieval import RankedDocument, RetrievalResult

        extractor = MetadataExtractor()

        docs = [
            RankedDocument(
                document_id=f"doc_{i}",
                content=f"Content {i}",
                score=0.9 - (i * 0.1),
                rrf_score=0.05 - (i * 0.01),
                source_type=["legge", "circolare", "faq"][i],
                source_name=f"Source {i}",
                published_date=datetime(2025, 6, 15) - timedelta(days=i * 365),
                metadata={"title": f"Title {i}"},
            )
            for i in range(3)
        ]

        result = RetrievalResult(
            documents=docs,
            total_found=10,
            search_time_ms=200.0,
        )

        metadata_list = extractor.extract_all(result)

        assert len(metadata_list) == 3
        assert all(hasattr(m, "hierarchy_level") for m in metadata_list)

    def test_format_context_empty_result(self):
        """Test formatting context for empty retrieval result."""
        from app.services.metadata_extractor import MetadataExtractor
        from app.services.parallel_retrieval import RetrievalResult

        extractor = MetadataExtractor()

        result = RetrievalResult(
            documents=[],
            total_found=0,
            search_time_ms=50.0,
        )

        context = extractor.format_context_for_synthesis(result)

        assert "Documenti Recuperati: 0" in context
        # Should not have any document sections
        assert "DOCUMENTO 1" not in context


class TestPerformance:
    """Performance tests for metadata extraction."""

    def test_extraction_performance(self):
        """Test that extraction completes quickly."""
        import time

        from app.services.metadata_extractor import MetadataExtractor
        from app.services.parallel_retrieval import RankedDocument, RetrievalResult

        extractor = MetadataExtractor()

        # Create 100 documents
        docs = [
            RankedDocument(
                document_id=f"doc_{i}",
                content=f"Content {i} " * 100,  # Moderate content
                score=0.9,
                rrf_score=0.05,
                source_type="circolare",
                source_name=f"Circolare {i}/E/2025",
                published_date=datetime(2025, 1, 1),
                metadata={"title": f"Title {i}"},
            )
            for i in range(100)
        ]

        result = RetrievalResult(
            documents=docs,
            total_found=100,
            search_time_ms=500.0,
        )

        start = time.perf_counter()
        context = extractor.format_context_for_synthesis(result)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete in under 100ms for 100 documents
        assert elapsed_ms < 100, f"Took {elapsed_ms:.1f}ms, should be <100ms"
        assert len(context) > 0
