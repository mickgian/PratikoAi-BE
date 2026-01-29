"""TDD Tests for Phase 9: Paragraph-Level Source Grounding (DEV-236).

DEV-236: Update Source Schema for Paragraph-Level Grounding.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 90%+ for new code.
"""

from unittest.mock import AsyncMock, patch

import pytest

# Sample KB documents with paragraph content for testing
# DEV-244: Include rrf_score >= 0.008 (MIN_FONTI_RELEVANCE_SCORE) to pass filter
SAMPLE_KB_DOCS_WITH_PARAGRAPHS = [
    {
        "id": "doc_001",
        "title": "Art. 16 DPR 633/72 - Aliquote IVA",
        "type": "dpr",
        "date": "1972-10-26",
        "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:dpr:1972;633",
        "rrf_score": 0.05,  # Above MIN_FONTI_RELEVANCE_SCORE (0.008)
        "content": """1. L'aliquota IVA ordinaria è del 22% per la maggior parte dei beni e servizi.

2. Aliquote ridotte sono previste per specifiche categorie:
   - 10% per prodotti alimentari, servizi turistici e ristrutturazioni
   - 5% per alcune prestazioni socio-sanitarie
   - 4% per beni di prima necessità (pane, latte, frutta, verdura)

3. Le cessioni intracomunitarie sono esenti con diritto a detrazione.""",
    },
    {
        "id": "doc_002",
        "title": "Circolare AdE n. 12/E del 2024",
        "type": "circolare",
        "date": "2024-03-15",
        "url": None,
        "rrf_score": 0.03,  # Above MIN_FONTI_RELEVANCE_SCORE (0.008)
        "content": "Chiarimenti sulle aliquote IVA per servizi digitali. La presente circolare fornisce indicazioni operative.",
    },
]


@pytest.fixture
def mock_orchestrator_response_with_paragraphs():
    """Create mock orchestrator response with KB documents containing paragraphs."""
    return {
        "context_merged": True,
        "merged_context": "Merged context with KB docs...",
        "kb_results": SAMPLE_KB_DOCS_WITH_PARAGRAPHS,
        "source_distribution": {"facts": 0, "kb_docs": 2, "document_facts": 0},
        "token_count": 500,
        "context_quality_score": 0.85,
        "timestamp": "2024-12-31T12:00:00Z",
    }


@pytest.fixture
def base_state():
    """Create base RAG state for testing."""
    return {
        "messages": [],
        "user_message": "Qual è l'aliquota IVA?",
        "request_id": "test-request-123",
    }


class TestParagraphIdGeneration:
    """Test paragraph_id generation for source metadata."""

    def test_generate_paragraph_id_creates_unique_id(self):
        """paragraph_id should be unique within a document."""
        from app.services.context_builder import generate_paragraph_id

        doc_id = "doc_001"
        paragraph_index = 0

        paragraph_id = generate_paragraph_id(doc_id, paragraph_index)

        assert paragraph_id is not None
        assert doc_id in paragraph_id
        assert "p0" in paragraph_id or "0" in paragraph_id

    def test_generate_paragraph_id_different_for_different_paragraphs(self):
        """Different paragraphs should have different IDs."""
        from app.services.context_builder import generate_paragraph_id

        doc_id = "doc_001"

        id_1 = generate_paragraph_id(doc_id, 0)
        id_2 = generate_paragraph_id(doc_id, 1)

        assert id_1 != id_2

    def test_generate_paragraph_id_deterministic(self):
        """Same inputs should produce same paragraph_id."""
        from app.services.context_builder import generate_paragraph_id

        doc_id = "doc_001"
        paragraph_index = 2

        id_1 = generate_paragraph_id(doc_id, paragraph_index)
        id_2 = generate_paragraph_id(doc_id, paragraph_index)

        assert id_1 == id_2

    def test_generate_paragraph_id_handles_empty_doc_id(self):
        """Should handle empty doc_id gracefully."""
        from app.services.context_builder import generate_paragraph_id

        paragraph_id = generate_paragraph_id("", 0)

        assert paragraph_id is not None
        assert len(paragraph_id) > 0


class TestParagraphExcerptExtraction:
    """Test paragraph excerpt extraction from document content."""

    def test_extract_paragraph_excerpt_first_paragraph(self):
        """Should extract first meaningful paragraph as excerpt."""
        from app.services.context_builder import extract_paragraph_excerpt

        content = """1. L'aliquota IVA ordinaria è del 22% per la maggior parte dei beni.

2. Aliquote ridotte sono previste per specifiche categorie."""

        excerpt = extract_paragraph_excerpt(content, max_length=150)

        assert excerpt is not None
        assert len(excerpt) <= 153  # 150 + possible "..."
        assert "22%" in excerpt or "aliquota" in excerpt.lower()

    def test_extract_paragraph_excerpt_respects_max_length(self):
        """Excerpt should not exceed max_length."""
        from app.services.context_builder import extract_paragraph_excerpt

        long_content = "A" * 500

        excerpt = extract_paragraph_excerpt(long_content, max_length=100)

        assert len(excerpt) <= 103  # 100 + "..."

    def test_extract_paragraph_excerpt_adds_ellipsis_when_truncated(self):
        """Should add ellipsis when content is truncated."""
        from app.services.context_builder import extract_paragraph_excerpt

        long_content = "Questo è un contenuto molto lungo che supera il limite. " * 10

        excerpt = extract_paragraph_excerpt(long_content, max_length=50)

        assert excerpt.endswith("...")

    def test_extract_paragraph_excerpt_empty_content(self):
        """Should handle empty content gracefully."""
        from app.services.context_builder import extract_paragraph_excerpt

        excerpt = extract_paragraph_excerpt("", max_length=100)

        assert excerpt == ""

    def test_extract_paragraph_excerpt_none_content(self):
        """Should handle None content gracefully."""
        from app.services.context_builder import extract_paragraph_excerpt

        excerpt = extract_paragraph_excerpt(None, max_length=100)

        assert excerpt == ""

    def test_extract_paragraph_excerpt_whitespace_only(self):
        """Should handle whitespace-only content."""
        from app.services.context_builder import extract_paragraph_excerpt

        excerpt = extract_paragraph_excerpt("   \n\n  \t  ", max_length=100)

        assert excerpt.strip() == ""


class TestStep40ParagraphIdInMetadata:
    """Test that Step 40 includes paragraph_id in kb_sources_metadata."""

    @pytest.mark.asyncio
    async def test_step40_metadata_has_paragraph_id(self, base_state, mock_orchestrator_response_with_paragraphs):
        """kb_sources_metadata should include paragraph_id field."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response_with_paragraphs,
        ):
            result = await node_step_40(base_state)

            assert "kb_sources_metadata" in result
            for metadata in result["kb_sources_metadata"]:
                assert "paragraph_id" in metadata

    @pytest.mark.asyncio
    async def test_step40_paragraph_id_is_string(self, base_state, mock_orchestrator_response_with_paragraphs):
        """paragraph_id should be a string."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response_with_paragraphs,
        ):
            result = await node_step_40(base_state)

            for metadata in result["kb_sources_metadata"]:
                assert isinstance(metadata["paragraph_id"], str)

    @pytest.mark.asyncio
    async def test_step40_paragraph_id_contains_doc_id(self, base_state, mock_orchestrator_response_with_paragraphs):
        """paragraph_id should contain the document ID for traceability."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response_with_paragraphs,
        ):
            result = await node_step_40(base_state)

            for i, metadata in enumerate(result["kb_sources_metadata"]):
                doc_id = result["kb_documents"][i]["id"]
                assert doc_id in metadata["paragraph_id"]


class TestStep40ParagraphExcerptInMetadata:
    """Test that Step 40 includes paragraph_excerpt in kb_sources_metadata."""

    @pytest.mark.asyncio
    async def test_step40_metadata_has_paragraph_excerpt(self, base_state, mock_orchestrator_response_with_paragraphs):
        """kb_sources_metadata should include paragraph_excerpt field."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response_with_paragraphs,
        ):
            result = await node_step_40(base_state)

            assert "kb_sources_metadata" in result
            for metadata in result["kb_sources_metadata"]:
                assert "paragraph_excerpt" in metadata

    @pytest.mark.asyncio
    async def test_step40_paragraph_excerpt_is_string(self, base_state, mock_orchestrator_response_with_paragraphs):
        """paragraph_excerpt should be a string."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response_with_paragraphs,
        ):
            result = await node_step_40(base_state)

            for metadata in result["kb_sources_metadata"]:
                assert isinstance(metadata["paragraph_excerpt"], str)

    @pytest.mark.asyncio
    async def test_step40_paragraph_excerpt_max_length_150(
        self, base_state, mock_orchestrator_response_with_paragraphs
    ):
        """paragraph_excerpt should not exceed 150 characters for tooltip display."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response_with_paragraphs,
        ):
            result = await node_step_40(base_state)

            for metadata in result["kb_sources_metadata"]:
                assert len(metadata["paragraph_excerpt"]) <= 153  # 150 + "..."

    @pytest.mark.asyncio
    async def test_step40_paragraph_excerpt_from_content(self, base_state, mock_orchestrator_response_with_paragraphs):
        """paragraph_excerpt should be extracted from document content."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response_with_paragraphs,
        ):
            result = await node_step_40(base_state)

            # First doc has "22%" in content
            first_metadata = result["kb_sources_metadata"][0]
            first_doc_content = result["kb_documents"][0]["content"]

            # Excerpt should be a substring of the content (ignoring ellipsis)
            excerpt_without_ellipsis = first_metadata["paragraph_excerpt"].rstrip(".")
            assert excerpt_without_ellipsis in first_doc_content or len(first_doc_content) > 150


class TestStep40EmptyContentHandling:
    """Test handling of documents with empty or missing content."""

    @pytest.mark.asyncio
    async def test_step40_empty_content_paragraph_id(self, base_state):
        """Document with empty content should still have paragraph_id."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [
                # DEV-244: Include rrf_score to pass MIN_FONTI_RELEVANCE_SCORE filter
                {"id": "doc_empty", "title": "Empty Doc", "type": "legge", "content": "", "rrf_score": 0.05}
            ],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)

            assert "paragraph_id" in result["kb_sources_metadata"][0]
            assert result["kb_sources_metadata"][0]["paragraph_id"] is not None

    @pytest.mark.asyncio
    async def test_step40_empty_content_paragraph_excerpt(self, base_state):
        """Document with empty content should have empty paragraph_excerpt."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [
                # DEV-244: Include rrf_score to pass MIN_FONTI_RELEVANCE_SCORE filter
                {"id": "doc_empty", "title": "Empty Doc", "type": "legge", "content": "", "rrf_score": 0.05}
            ],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)

            assert result["kb_sources_metadata"][0]["paragraph_excerpt"] == ""

    @pytest.mark.asyncio
    async def test_step40_missing_content_paragraph_excerpt(self, base_state):
        """Document with missing content key should have empty paragraph_excerpt."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [
                # DEV-244: Include rrf_score to pass MIN_FONTI_RELEVANCE_SCORE filter
                {"id": "doc_no_content", "title": "No Content", "type": "dpr", "rrf_score": 0.05}  # No content key
            ],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)

            assert result["kb_sources_metadata"][0]["paragraph_excerpt"] == ""


class TestStep40BackwardCompatibility:
    """Test that existing kb_sources_metadata fields are preserved."""

    @pytest.mark.asyncio
    async def test_step40_preserves_existing_fields(self, base_state, mock_orchestrator_response_with_paragraphs):
        """All existing metadata fields should still be present."""
        from app.core.langgraph.nodes.step_040__build_context import node_step_40

        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response_with_paragraphs,
        ):
            result = await node_step_40(base_state)

            existing_fields = [
                "id",
                "title",
                "type",
                "date",
                "url",
                "key_topics",
                "key_values",
                "hierarchy_weight",
            ]

            for metadata in result["kb_sources_metadata"]:
                for field in existing_fields:
                    assert field in metadata, f"Missing field: {field}"
