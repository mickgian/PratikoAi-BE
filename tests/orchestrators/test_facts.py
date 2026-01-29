"""Tests for facts orchestrator functions.

DEV-242: Tests for step_40__build_context retrieval_result integration.
"""

import pytest

from app.orchestrators.facts import step_40__build_context


class TestStep40RetrievalResultIntegration:
    """DEV-242: Ensure step_40 uses parallel retrieval results from retrieval_result."""

    @pytest.mark.asyncio
    async def test_step40_reads_retrieval_result_documents(self):
        """step_40 should use ctx['retrieval_result']['documents'] as kb_results.

        This test verifies that when Step 39c stores documents in retrieval_result,
        Step 40 can find and use them even if knowledge_items and kb_docs are empty.
        """
        ctx = {
            "retrieval_result": {
                "documents": [
                    {
                        "document_id": "doc1",
                        "content": "Test content about rottamazione quinquies",
                        "score": 0.9,
                        "rrf_score": 0.85,
                        "source_type": "legge",
                        "source_name": "Legge 199/2025",
                        "published_date": "2025-01-01",
                        "metadata": {},
                    }
                ],
                "total_found": 1,
                "search_time_ms": 50.0,
                "skipped": False,
                "error": False,
            },
            "canonical_facts": [],
            "user_message": "Parlami della rottamazione quinquies",
            "request_id": "test-request-123",
        }

        result = await step_40__build_context(ctx=ctx)

        # Should have used the document from retrieval_result
        # DEV-242: Fields are now transformed (document_id -> id)
        kb_results = result.get("kb_results", [])
        assert len(kb_results) == 1, f"Expected 1 kb_result, got {len(kb_results)}"
        assert kb_results[0].get("id") == "doc1"

    @pytest.mark.asyncio
    async def test_step40_prefers_retrieval_result_over_knowledge_items(self):
        """DEV-244: retrieval_result now takes priority over knowledge_items.

        This is because only retrieval_result (after transformation) has source_url
        for proper citation links in the Fonti section. knowledge_items from
        legacy Step 39 lacks source_url.
        """
        ctx = {
            "knowledge_items": [
                {
                    "id": "ki1",
                    "content": "Knowledge item content",
                    "title": "Legacy doc (no source_url)",
                }
            ],
            "retrieval_result": {
                "documents": [
                    {
                        "document_id": "doc1",
                        "content": "Retrieval result content",
                        "source_url": "https://example.com/doc1",  # Has source_url!
                        "score": 0.9,
                    }
                ],
                "total_found": 1,
            },
            "canonical_facts": [],
            "user_message": "test query",
            "request_id": "test-request-456",
        }

        result = await step_40__build_context(ctx=ctx)

        # DEV-244: Should use retrieval_result since it has source_url for Fonti
        kb_results = result.get("kb_results", [])
        assert len(kb_results) == 1
        # retrieval_result has 'document_id' which becomes 'id' after transformation
        assert kb_results[0].get("id") == "doc1" or kb_results[0].get("content") == "Retrieval result content"

    @pytest.mark.asyncio
    async def test_step40_handles_empty_retrieval_result(self):
        """Empty retrieval_result should not cause errors."""
        ctx = {
            "retrieval_result": {
                "documents": [],
                "total_found": 0,
                "skipped": True,
            },
            "canonical_facts": [],
            "user_message": "test query",
            "request_id": "test-request-789",
        }

        result = await step_40__build_context(ctx=ctx)

        # Should complete without error
        assert result is not None
        assert "merged_context" in result or "context" in result or "kb_results" in result

    @pytest.mark.asyncio
    async def test_step40_handles_missing_retrieval_result(self):
        """Missing retrieval_result key should not cause errors."""
        ctx = {
            "canonical_facts": [],
            "user_message": "test query",
            "request_id": "test-request-000",
        }

        result = await step_40__build_context(ctx=ctx)

        # Should complete without error
        assert result is not None


class TestStep40FieldTransformation:
    """DEV-242: Ensure retrieval_result fields are transformed to context builder format."""

    @pytest.mark.asyncio
    async def test_step40_transforms_retrieval_result_fields(self):
        """retrieval_result fields should be transformed to context builder format.

        Step 39c uses: document_id, source_name, source_type, published_date
        Context builder expects: id, title, type, publication_date
        """
        ctx = {
            "retrieval_result": {
                "documents": [
                    {
                        "document_id": "doc1",
                        "content": "Test content about rottamazione quinquies",
                        "score": 0.9,
                        "source_name": "Legge 199/2025",  # Step 39c field
                        "source_type": "legge",
                        "published_date": "2025-01-01",
                        "metadata": {},
                    }
                ],
                "total_found": 1,
            },
            "canonical_facts": [],
            "user_message": "rottamazione quinquies",
            "request_id": "test-field-transform",
        }

        result = await step_40__build_context(ctx=ctx)

        kb_results = result.get("kb_results", [])
        assert len(kb_results) == 1, f"Expected 1 kb_result, got {len(kb_results)}"

        doc = kb_results[0]
        # Verify fields are transformed for context builder
        assert doc.get("id") == "doc1", f"Expected id='doc1', got {doc.get('id')}"
        assert doc.get("title") == "Legge 199/2025", f"Expected title='Legge 199/2025', got {doc.get('title')}"
        assert doc.get("type") == "legge", f"Expected type='legge', got {doc.get('type')}"

    @pytest.mark.asyncio
    async def test_step40_preserves_original_fields_when_already_correct(self):
        """Documents with correct field names should pass through unchanged."""
        ctx = {
            "retrieval_result": {
                "documents": [
                    {
                        "id": "doc2",  # Already correct
                        "title": "Already Correct Title",  # Already correct
                        "content": "Test content",
                        "type": "circolare",  # Already correct
                        "score": 0.8,
                    }
                ],
                "total_found": 1,
            },
            "canonical_facts": [],
            "user_message": "test query",
            "request_id": "test-preserve-fields",
        }

        result = await step_40__build_context(ctx=ctx)

        kb_results = result.get("kb_results", [])
        assert len(kb_results) == 1

        doc = kb_results[0]
        assert doc.get("id") == "doc2"
        assert doc.get("title") == "Already Correct Title"
        assert doc.get("type") == "circolare"


class TestStep40AuthorityBoostPreservation:
    """DEV-250: Ensure authority_boost survives transformation chain for high-authority source exemption."""

    @pytest.mark.asyncio
    async def test_step40_preserves_authority_boost_from_metadata(self):
        """DEV-250: authority_boost in metadata should survive transformation to kb_results.

        High-authority sources (legge, decreto, circolare) should bypass the low-score
        filter in kb_metadata_builder. This requires authority_boost to flow through:
        parallel_retrieval -> facts._transform_retrieval_documents -> kb_metadata_builder
        """
        ctx = {
            "retrieval_result": {
                "documents": [
                    {
                        "document_id": "legge-199-2025",
                        "content": "LEGGE 30 dicembre 2025, n. 199 - Rottamazione quinquies",
                        "score": 0.003,  # Low score that would normally be filtered
                        "rrf_score": 0.003,
                        "source_name": "LEGGE 30 dicembre 2025, n. 199",
                        "source_type": "legge",
                        "published_date": "2025-12-30",
                        "metadata": {
                            "authority_boost": 1.8,  # High authority from GERARCHIA_FONTI
                            "source_url": "https://gazzettaufficiale.it/eli/id/2025/12/31/199/sg",
                        },
                    }
                ],
                "total_found": 1,
            },
            "canonical_facts": [],
            "user_message": "parlami della rottamazione quinquies",
            "request_id": "test-authority-boost",
        }

        result = await step_40__build_context(ctx=ctx)

        kb_results = result.get("kb_results", [])
        assert len(kb_results) == 1, f"Expected 1 kb_result, got {len(kb_results)}"

        doc = kb_results[0]
        # Verify authority_boost is preserved for kb_metadata_builder exemption
        assert (
            doc.get("authority_boost") == 1.8
        ), f"Expected authority_boost=1.8 to survive transformation, got {doc.get('authority_boost')}"

    @pytest.mark.asyncio
    async def test_step40_preserves_authority_boost_from_top_level(self):
        """DEV-250: authority_boost at document top-level should also be preserved."""
        ctx = {
            "retrieval_result": {
                "documents": [
                    {
                        "document_id": "decreto-123",
                        "content": "DECRETO test content",
                        "score": 0.002,
                        "rrf_score": 0.002,
                        "authority_boost": 1.6,  # At top level (from _apply_boosts)
                        "source_name": "DECRETO 123",
                        "source_type": "decreto",
                        "metadata": {},
                    }
                ],
                "total_found": 1,
            },
            "canonical_facts": [],
            "user_message": "test query",
            "request_id": "test-authority-boost-top-level",
        }

        result = await step_40__build_context(ctx=ctx)

        kb_results = result.get("kb_results", [])
        assert len(kb_results) == 1

        doc = kb_results[0]
        assert doc.get("authority_boost") == 1.6, f"Expected authority_boost=1.6, got {doc.get('authority_boost')}"

    @pytest.mark.asyncio
    async def test_step40_defaults_authority_boost_to_1_when_missing(self):
        """DEV-250: Missing authority_boost should default to 1.0 (no exemption)."""
        ctx = {
            "retrieval_result": {
                "documents": [
                    {
                        "document_id": "generic-doc",
                        "content": "Generic content without authority boost",
                        "score": 0.5,
                        "source_name": "Generic Document",
                        "source_type": "unknown",
                        "metadata": {},  # No authority_boost
                    }
                ],
                "total_found": 1,
            },
            "canonical_facts": [],
            "user_message": "test query",
            "request_id": "test-no-authority-boost",
        }

        result = await step_40__build_context(ctx=ctx)

        kb_results = result.get("kb_results", [])
        assert len(kb_results) == 1

        doc = kb_results[0]
        # Should default to 1.0 (no exemption from low-score filter)
        assert (
            doc.get("authority_boost") == 1.0
        ), f"Expected authority_boost=1.0 as default, got {doc.get('authority_boost')}"
