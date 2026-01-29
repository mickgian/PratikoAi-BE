"""TDD Tests for Phase 9: Step 40 KB Document Preservation.

DEV-213: Update Step 40 to Preserve KB Documents and Metadata.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 90%+ for new code.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.langgraph.nodes.step_040__build_context import node_step_40

# Sample KB documents for testing (includes rrf_score for MIN_FONTI_RELEVANCE_SCORE filter)
SAMPLE_KB_DOCS = [
    {
        "id": "doc_001",
        "title": "Art. 16 DPR 633/72 - Aliquote IVA",
        "type": "dpr",
        "date": "1972-10-26",
        "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:dpr:1972;633",
        "content": "L'aliquota IVA ordinaria è del 22%. Aliquote ridotte: 10%, 5%, 4%.",
        "rrf_score": 0.05,  # Above MIN_FONTI_RELEVANCE_SCORE (0.008)
    },
    {
        "id": "doc_002",
        "title": "Circolare AdE n. 12/E del 2024",
        "type": "circolare",
        "date": "2024-03-15",
        "url": None,
        "content": "Chiarimenti sulle aliquote IVA per servizi digitali.",
        "rrf_score": 0.04,
    },
    {
        "id": "doc_003",
        "title": "Art. 2 D.Lgs. 81/2008 - Definizioni",
        "type": "decreto_legislativo",
        "date": "2008-04-09",
        "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:dlgs:2008;81",
        "content": "Definizioni per la sicurezza sul lavoro. Il datore di lavoro deve...",
        "rrf_score": 0.03,
    },
]


@pytest.fixture
def mock_orchestrator_response():
    """Create mock orchestrator response with KB documents."""
    return {
        "context_merged": True,
        "merged_context": "Merged context with KB docs...",
        "kb_results": SAMPLE_KB_DOCS,
        "source_distribution": {"facts": 0, "kb_docs": 3, "document_facts": 0},
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


class TestStep40PreservesKbDocuments:
    """Test that Step 40 preserves KB documents in state."""

    @pytest.mark.asyncio
    async def test_step40_preserves_kb_documents(self, base_state, mock_orchestrator_response):
        """kb_documents should be stored in state after Step 40."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)

            assert "kb_documents" in result
            assert isinstance(result["kb_documents"], list)
            assert len(result["kb_documents"]) == 3

    @pytest.mark.asyncio
    async def test_step40_kb_documents_contain_original_docs(self, base_state, mock_orchestrator_response):
        """kb_documents should contain the original document data."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)

            kb_docs = result["kb_documents"]
            assert kb_docs[0]["id"] == "doc_001"
            assert kb_docs[0]["title"] == "Art. 16 DPR 633/72 - Aliquote IVA"
            assert kb_docs[0]["type"] == "dpr"


class TestStep40PreservesKbMetadata:
    """Test that Step 40 preserves KB sources metadata."""

    @pytest.mark.asyncio
    async def test_step40_preserves_kb_metadata(self, base_state, mock_orchestrator_response):
        """kb_sources_metadata should be stored in state after Step 40."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)

            assert "kb_sources_metadata" in result
            assert isinstance(result["kb_sources_metadata"], list)
            assert len(result["kb_sources_metadata"]) == 3

    @pytest.mark.asyncio
    async def test_step40_metadata_has_correct_count(self, base_state, mock_orchestrator_response):
        """kb_sources_metadata count should match kb_documents count."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)

            assert len(result["kb_sources_metadata"]) == len(result["kb_documents"])


class TestStep40MetadataStructure:
    """Test metadata structure for each document."""

    @pytest.mark.asyncio
    async def test_step40_metadata_structure(self, base_state, mock_orchestrator_response):
        """Each metadata entry should have correct structure."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)

            metadata = result["kb_sources_metadata"][0]
            assert "id" in metadata
            assert "title" in metadata
            assert "type" in metadata
            assert "date" in metadata
            assert "url" in metadata
            assert "key_topics" in metadata
            assert "key_values" in metadata
            assert "hierarchy_weight" in metadata

    @pytest.mark.asyncio
    async def test_step40_metadata_id_matches_doc(self, base_state, mock_orchestrator_response):
        """Metadata ID should match document ID."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)

            for i, metadata in enumerate(result["kb_sources_metadata"]):
                assert metadata["id"] == result["kb_documents"][i]["id"]


class TestStep40HierarchyWeight:
    """Test hierarchy weight calculation for document types."""

    @pytest.mark.asyncio
    async def test_step40_hierarchy_weight_legge(self, base_state):
        """Legge should have hierarchy weight 1.0."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [{"id": "1", "title": "Test", "type": "legge", "content": "Test", "rrf_score": 0.05}],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            assert result["kb_sources_metadata"][0]["hierarchy_weight"] == 1.0

    @pytest.mark.asyncio
    async def test_step40_hierarchy_weight_dpr(self, base_state):
        """DPR should have hierarchy weight 1.0."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [{"id": "1", "title": "Test", "type": "dpr", "content": "Test", "rrf_score": 0.05}],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            assert result["kb_sources_metadata"][0]["hierarchy_weight"] == 1.0

    @pytest.mark.asyncio
    async def test_step40_hierarchy_weight_circolare(self, base_state):
        """Circolare should have hierarchy weight 0.6."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [{"id": "1", "title": "Test", "type": "circolare", "content": "Test", "rrf_score": 0.05}],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            assert result["kb_sources_metadata"][0]["hierarchy_weight"] == 0.6

    @pytest.mark.asyncio
    async def test_step40_hierarchy_weight_interpello(self, base_state):
        """Interpello should have hierarchy weight 0.4."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [{"id": "1", "title": "Test", "type": "interpello", "content": "Test", "rrf_score": 0.05}],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            assert result["kb_sources_metadata"][0]["hierarchy_weight"] == 0.4

    @pytest.mark.asyncio
    async def test_step40_hierarchy_weight_unknown_defaults(self, base_state):
        """Unknown document type should default to 0.5."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [{"id": "1", "title": "Test", "type": "unknown_type", "content": "Test", "rrf_score": 0.05}],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            assert result["kb_sources_metadata"][0]["hierarchy_weight"] == 0.5


class TestStep40ExtractTopics:
    """Test topic extraction from documents."""

    @pytest.mark.asyncio
    async def test_step40_extract_topics_from_title(self, base_state):
        """Topics should be extracted from document title."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [
                {
                    "id": "1",
                    "title": "Aliquote IVA - Art. 16 DPR 633/72",
                    "type": "dpr",
                    "content": "Test",
                    "rrf_score": 0.05,
                }
            ],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            topics = result["kb_sources_metadata"][0]["key_topics"]
            assert isinstance(topics, list)

    @pytest.mark.asyncio
    async def test_step40_extract_topics_returns_list(self, base_state, mock_orchestrator_response):
        """key_topics should always be a list."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)
            for metadata in result["kb_sources_metadata"]:
                assert isinstance(metadata["key_topics"], list)


class TestStep40ExtractValues:
    """Test value extraction (percentages, amounts, dates) from documents."""

    @pytest.mark.asyncio
    async def test_step40_extract_values_percentage(self, base_state):
        """Should extract percentage values from content."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [
                {
                    "id": "1",
                    "title": "Test",
                    "type": "dpr",
                    "content": "L'aliquota IVA è del 22% per beni ordinari.",
                    "rrf_score": 0.05,
                }
            ],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            values = result["kb_sources_metadata"][0]["key_values"]
            assert isinstance(values, list)
            assert "22%" in values

    @pytest.mark.asyncio
    async def test_step40_extract_values_euro_amounts(self, base_state):
        """Should extract euro amounts from content."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [
                {
                    "id": "1",
                    "title": "Test",
                    "type": "circolare",
                    "content": "Il limite è di 5.000 euro o €10.000.",
                    "rrf_score": 0.05,
                }
            ],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            values = result["kb_sources_metadata"][0]["key_values"]
            assert isinstance(values, list)

    @pytest.mark.asyncio
    async def test_step40_extract_values_returns_list(self, base_state, mock_orchestrator_response):
        """key_values should always be a list."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)
            for metadata in result["kb_sources_metadata"]:
                assert isinstance(metadata["key_values"], list)


class TestStep40EmptyKbDocs:
    """Test handling of empty KB documents."""

    @pytest.mark.asyncio
    async def test_step40_empty_kb_docs(self, base_state):
        """Empty KB results should set empty lists."""
        response = {
            "context_merged": True,
            "merged_context": "No KB docs available.",
            "kb_results": [],
            "source_distribution": {"facts": 0, "kb_docs": 0, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)

            assert result["kb_documents"] == []
            assert result["kb_sources_metadata"] == []


class TestStep40NullKbDocs:
    """Test handling of null/None KB documents."""

    @pytest.mark.asyncio
    async def test_step40_null_kb_docs(self, base_state):
        """None KB results should set empty lists."""
        response = {
            "context_merged": True,
            "merged_context": "No KB docs.",
            "kb_results": None,
            "source_distribution": {"facts": 0, "kb_docs": 0, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)

            assert result["kb_documents"] == []
            assert result["kb_sources_metadata"] == []

    @pytest.mark.asyncio
    async def test_step40_missing_kb_results_key(self, base_state):
        """Missing kb_results key should set empty lists."""
        response = {
            "context_merged": True,
            "merged_context": "No KB docs.",
            "source_distribution": {"facts": 0, "kb_docs": 0, "document_facts": 0},
            # kb_results key is missing
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)

            assert result["kb_documents"] == []
            assert result["kb_sources_metadata"] == []


class TestStep40LargeKbDocsCapped:
    """Test that large KB document sets are capped."""

    @pytest.mark.asyncio
    async def test_step40_large_kb_docs_capped_at_20(self, base_state):
        """KB documents should be capped at 20."""
        # Create 50 documents
        large_kb_docs = [
            {"id": f"doc_{i}", "title": f"Document {i}", "type": "circolare", "content": f"Content {i}"}
            for i in range(50)
        ]
        response = {
            "context_merged": True,
            "merged_context": "Many docs...",
            "kb_results": large_kb_docs,
            "source_distribution": {"facts": 0, "kb_docs": 50, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)

            assert len(result["kb_documents"]) <= 20
            assert len(result["kb_sources_metadata"]) <= 20


class TestStep40MalformedDocSkipped:
    """Test handling of malformed documents."""

    @pytest.mark.asyncio
    async def test_step40_malformed_doc_skipped(self, base_state):
        """Malformed documents should be skipped with warning."""
        docs_with_malformed = [
            {"id": "good_1", "title": "Good Doc", "type": "legge", "content": "Good content", "rrf_score": 0.05},
            None,  # Malformed: None instead of dict
            {"id": "good_2", "title": "Another Good", "type": "dpr", "content": "More content", "rrf_score": 0.04},
        ]
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": docs_with_malformed,
            "source_distribution": {"facts": 0, "kb_docs": 3, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)

            # Should have 2 valid docs (malformed one skipped)
            assert len(result["kb_documents"]) == 2
            assert len(result["kb_sources_metadata"]) == 2


class TestStep40MissingFieldsDefaults:
    """Test that missing fields get default values."""

    @pytest.mark.asyncio
    async def test_step40_missing_title_defaults(self, base_state):
        """Missing title should default to empty string."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [{"id": "1", "type": "legge", "content": "Content", "rrf_score": 0.05}],  # No title
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            assert result["kb_sources_metadata"][0]["title"] == ""

    @pytest.mark.asyncio
    async def test_step40_missing_type_defaults(self, base_state):
        """Missing type should default to empty string."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [{"id": "1", "title": "Test", "content": "Content", "rrf_score": 0.05}],  # No type
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            assert result["kb_sources_metadata"][0]["type"] == ""

    @pytest.mark.asyncio
    async def test_step40_missing_date_defaults_to_empty(self, base_state):
        """Missing date should default to empty string (DEV-245: no 'data non disponibile')."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            # Include rrf_score to pass MIN_FONTI_RELEVANCE_SCORE filter
            "kb_results": [{"id": "1", "title": "Test", "type": "legge", "content": "Content", "rrf_score": 0.05}],
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            assert result["kb_sources_metadata"][0]["date"] == ""

    @pytest.mark.asyncio
    async def test_step40_missing_url_defaults_to_none(self, base_state):
        """Missing URL should default to None."""
        response = {
            "context_merged": True,
            "merged_context": "...",
            "kb_results": [
                {"id": "1", "title": "Test", "type": "legge", "content": "Content", "rrf_score": 0.05}
            ],  # No URL
            "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        }
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await node_step_40(base_state)
            assert result["kb_sources_metadata"][0]["url"] is None


class TestStep40ExistingBehaviorUnchanged:
    """Test that existing Step 40 behavior is unchanged."""

    @pytest.mark.asyncio
    async def test_step40_still_stores_context(self, base_state, mock_orchestrator_response):
        """Step 40 should still store merged context in state."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)

            assert "context" in result
            assert result["context"] == "Merged context with KB docs..."

    @pytest.mark.asyncio
    async def test_step40_still_stores_context_metadata(self, base_state, mock_orchestrator_response):
        """Step 40 should still store context_metadata in state."""
        with patch(
            "app.core.langgraph.nodes.step_040__build_context.step_40__build_context",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_40(base_state)

            assert "context_metadata" in result
            assert result["context_metadata"]["kb_docs_count"] == 3


class TestDEV245FontiImprovements:
    """Tests for DEV-245: Fonti section display improvements."""

    def test_simplify_title_removes_article_reference(self):
        """simplify_title should remove ' - Art. X' and everything after."""
        from app.services.context_builder import simplify_title

        title = "LEGGE 30 dicembre 2025, n. 199 - Art. 1 - guenti: «33 per c…"
        result = simplify_title(title)
        assert result == "LEGGE 30 dicembre 2025, n. 199"

    def test_simplify_title_handles_articolo_spelled_out(self):
        """simplify_title should handle 'Articolo' spelled out."""
        from app.services.context_builder import simplify_title

        title = "D.Lgs. 81/2008 - Articolo 2 - Definizioni"
        result = simplify_title(title)
        assert result == "D.Lgs. 81/2008"

    def test_simplify_title_preserves_clean_title(self):
        """simplify_title should not modify titles without article references."""
        from app.services.context_builder import simplify_title

        title = "Circolare AdE n. 12/E del 2024"
        result = simplify_title(title)
        assert result == "Circolare AdE n. 12/E del 2024"

    def test_simplify_title_handles_empty_string(self):
        """simplify_title should return empty string for empty input."""
        from app.services.context_builder import simplify_title

        assert simplify_title("") == ""
        assert simplify_title(None) == ""

    def test_get_category_label_it_maps_regulatory_documents(self):
        """get_category_label_it should map 'regulatory_documents' to 'normativa'."""
        from app.services.context_builder import get_category_label_it

        assert get_category_label_it("regulatory_documents") == "normativa"

    def test_get_category_label_it_maps_known_types(self):
        """get_category_label_it should map all known document types."""
        from app.services.context_builder import get_category_label_it

        assert get_category_label_it("legge") == "legge"
        assert get_category_label_it("circolare") == "circolare"
        assert get_category_label_it("dpr") == "DPR"
        assert get_category_label_it("cassazione") == "Cassazione"

    def test_get_category_label_it_handles_unknown_type(self):
        """get_category_label_it should replace underscores for unknown types."""
        from app.services.context_builder import get_category_label_it

        assert get_category_label_it("some_unknown_type") == "some unknown type"

    def test_get_category_label_it_handles_empty_string(self):
        """get_category_label_it should return empty string for empty input."""
        from app.services.context_builder import get_category_label_it

        assert get_category_label_it("") == ""
        assert get_category_label_it(None) == ""
