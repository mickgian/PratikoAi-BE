"""Integration tests for Step 39 → Step 40 data flow.

These tests verify that knowledge items retrieved in step 39 correctly flow
to step 40's context builder, preventing data loss between orchestration steps.
"""

from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest

from app.core.langgraph.nodes.step_039__kbpre_fetch import node_step_39
from app.orchestrators.facts import step_40__build_context


@pytest.mark.asyncio
async def test_knowledge_items_flow_from_step_39_to_step_40():
    """Test that knowledge_items from step 39 are accessible to step 40."""
    # Arrange - Step 39 search results
    mock_documents = [
        {
            "id": 56,
            "title": "Risoluzione 56 - Tardiva registrazione",
            "content": "La risoluzione 56 tratta della tardiva registrazione...",
            "category": "regulatory_documents",
            "source": "agenzia_entrate",
        }
    ]

    initial_state = {
        "user_query": "Cosa dice la risoluzione numero 56?",
        "messages": [],
        "request_id": "test-integration-001",
        "canonical_facts": ["risoluzione 56"],
    }

    orchestrator_39_response = {
        "knowledge_items": mock_documents,
        "total_results": 1,
        "search_mode": "hybrid",
        "timestamp": "2025-11-07T14:00:00Z",
    }

    # Act - Execute step 39
    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orch_39:
        mock_orch_39.return_value = orchestrator_39_response

        state_after_39 = await node_step_39(initial_state)

    # Assert - Step 39 stored data correctly
    assert "knowledge_items" in state_after_39, "knowledge_items must be in state for step 40"
    assert state_after_39["knowledge_items"] == mock_documents
    assert state_after_39["kb_results"]["doc_count"] == 1

    # Act - Execute step 40 with state from step 39
    mock_context_builder = MagicMock()
    mock_context_builder.merge_context.return_value = {
        "merged_context": "Context from Risoluzione 56...",
        "context_parts": ["facts", "kb_docs"],
        "token_count": 500,
        "source_distribution": {"facts": 1, "kb_docs": 1, "document_facts": 0},
        "context_quality_score": 0.8,
        "deduplication_applied": False,
        "content_truncated": False,
    }

    await step_40__build_context(
        messages=[], ctx=dict(state_after_39), context_builder_service=mock_context_builder
    )

    # Assert - Step 40 received knowledge_items
    # Verify context_builder_service was called with kb_results from step 39
    mock_context_builder.merge_context.assert_called_once()
    call_args = mock_context_builder.merge_context.call_args[0][0]

    assert "kb_results" in call_args
    assert call_args["kb_results"] == mock_documents, "Step 40 must receive knowledge_items as kb_results"
    assert len(call_args["kb_results"]) == 1
    assert call_args["kb_results"][0]["id"] == 56


@pytest.mark.asyncio
async def test_step_40_receives_non_zero_kb_results_count():
    """Test that step 40 logs show non-zero kb_results_count when documents exist."""
    # Arrange
    mock_documents = [{"id": 1}, {"id": 2}]

    state = {"user_query": "test", "messages": [], "canonical_facts": ["test fact"]}

    orchestrator_39_response = {"knowledge_items": mock_documents, "total_results": 2, "search_mode": "hybrid"}

    # Act - Step 39
    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orch_39:
        mock_orch_39.return_value = orchestrator_39_response
        state_after_39 = await node_step_39(state)

    # Mock context builder
    mock_context_builder = MagicMock()
    mock_context_builder.merge_context.return_value = {
        "merged_context": "Test context",
        "context_parts": [],
        "token_count": 100,
        "source_distribution": {"facts": 0, "kb_docs": 2, "document_facts": 0},
        "context_quality_score": 0.5,
    }

    # Act - Step 40 with mocked logging
    with patch("app.orchestrators.facts.rag_step_log") as mock_log:
        await step_40__build_context(
            messages=[], ctx=dict(state_after_39), context_builder_service=mock_context_builder
        )

        # Assert - Check that step 40 logged kb_results_count > 0
        # Find the "started" log call
        started_calls = [
            call
            for call in mock_log.call_args_list
            if len(call[1]) > 0 and call[1].get("processing_stage") == "started"
        ]

        assert len(started_calls) > 0, "Step 40 should log processing_stage='started'"
        started_call = started_calls[0]
        assert started_call[1].get("kb_results_count") == 2, "kb_results_count should be 2"


@pytest.mark.asyncio
async def test_context_builder_receives_kb_documents():
    """Test that ContextBuilderMerge receives actual document content."""
    # Arrange
    mock_doc = {
        "id": 56,
        "title": "Risoluzione 56",
        "content": "Important tax regulation content...",
        "category": "regulatory_documents",
    }

    state = {"user_query": "risoluzione 56", "messages": [], "canonical_facts": ["risoluzione 56"]}

    orchestrator_39_response = {"knowledge_items": [mock_doc], "total_results": 1, "search_mode": "hybrid"}

    # Act - Step 39
    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orch_39:
        mock_orch_39.return_value = orchestrator_39_response
        state_after_39 = await node_step_39(state)

    # Mock context builder
    mock_context_builder = MagicMock()
    mock_context_builder.merge_context.return_value = {
        "merged_context": f"Context: {mock_doc['content']}",
        "context_parts": ["kb_docs"],
        "token_count": 200,
        "source_distribution": {"facts": 0, "kb_docs": 1, "document_facts": 0},
        "context_quality_score": 0.9,
    }

    # Act - Step 40
    await step_40__build_context(
        messages=[], ctx=dict(state_after_39), context_builder_service=mock_context_builder
    )

    # Assert - Context builder received the document
    mock_context_builder.merge_context.assert_called_once()
    call_data = mock_context_builder.merge_context.call_args[0][0]

    assert len(call_data["kb_results"]) == 1
    assert call_data["kb_results"][0]["title"] == "Risoluzione 56"
    assert "Important tax regulation content" in call_data["kb_results"][0]["content"]


@pytest.mark.asyncio
async def test_empty_search_results_handled_gracefully():
    """Test that step 40 handles empty knowledge_items from step 39."""
    # Arrange - No search results
    state = {"user_query": "unknown query", "messages": [], "canonical_facts": []}

    orchestrator_39_response = {"knowledge_items": [], "total_results": 0, "search_mode": "hybrid"}  # Empty results

    # Act - Step 39
    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orch_39:
        mock_orch_39.return_value = orchestrator_39_response
        state_after_39 = await node_step_39(state)

    # Mock context builder
    mock_context_builder = MagicMock()
    mock_context_builder.merge_context.return_value = {
        "merged_context": "",  # No context from KB
        "context_parts": [],
        "token_count": 0,
        "source_distribution": {"facts": 0, "kb_docs": 0, "document_facts": 0},
        "context_quality_score": 0.0,
    }

    # Act - Step 40 should not crash with empty results
    result = await step_40__build_context(
        messages=[], ctx=dict(state_after_39), context_builder_service=mock_context_builder
    )

    # Assert - Step 40 handled empty results
    assert result["context_merged"] is True
    assert result["merged_context"] == ""

    # Verify context builder was called with empty kb_results
    call_data = mock_context_builder.merge_context.call_args[0][0]
    assert call_data["kb_results"] == []
