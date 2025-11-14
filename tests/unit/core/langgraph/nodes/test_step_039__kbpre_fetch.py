"""Unit tests for Step 39 Node Wrapper: KB Pre-Fetch.

Tests verify that the node wrapper correctly maps orchestrator response keys
to RAGState, preventing data loss between steps 39 and 40.
"""

from unittest.mock import (
    AsyncMock,
    patch,
)

import pytest

from app.core.langgraph.nodes.step_039__kbpre_fetch import node_step_39


@pytest.mark.asyncio
async def test_node_step_39_maps_knowledge_items_correctly():
    """Test that knowledge_items from orchestrator is correctly mapped to state."""
    # Arrange
    mock_documents = [
        {"id": 56, "title": "Risoluzione 56", "content": "Test content"},
        {"id": 57, "title": "Risoluzione 57", "content": "Test content 2"},
    ]

    state = {"user_query": "Cosa dice la risoluzione numero 56?", "messages": [], "request_id": "test-123"}

    # Mock the orchestrator response
    orchestrator_response = {
        "knowledge_items": mock_documents,
        "total_results": 2,
        "search_mode": "hybrid",
        "timestamp": "2025-11-07T14:00:00Z",
    }

    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orchestrator:
        mock_orchestrator.return_value = orchestrator_response

        # Act
        result_state = await node_step_39(state)

        # Assert
        assert "kb_results" in result_state
        assert result_state["kb_results"]["documents"] == mock_documents
        assert result_state["kb_results"]["doc_count"] == 2
        assert result_state["kb_results"]["retrieval_method"] == "hybrid"

        # Critical: knowledge_items must be at state root level for step 40
        assert "knowledge_items" in result_state
        assert result_state["knowledge_items"] == mock_documents


@pytest.mark.asyncio
async def test_node_step_39_handles_empty_results():
    """Test that empty search results are handled gracefully."""
    # Arrange
    state = {"user_query": "unknown query", "messages": [], "request_id": "test-456"}

    orchestrator_response = {
        "knowledge_items": [],
        "total_results": 0,
        "search_mode": "hybrid",
        "timestamp": "2025-11-07T14:00:00Z",
    }

    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orchestrator:
        mock_orchestrator.return_value = orchestrator_response

        # Act
        result_state = await node_step_39(state)

        # Assert
        assert result_state["kb_results"]["documents"] == []
        assert result_state["kb_results"]["doc_count"] == 0
        assert result_state["knowledge_items"] == []


@pytest.mark.asyncio
async def test_node_step_39_stores_knowledge_items_in_state():
    """Test that knowledge_items is stored at state root level (not just in kb_results)."""
    # Arrange
    mock_documents = [{"id": 56, "title": "Test"}]

    state = {"user_query": "test query", "messages": []}

    orchestrator_response = {"knowledge_items": mock_documents, "total_results": 1, "search_mode": "hybrid"}

    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orchestrator:
        mock_orchestrator.return_value = orchestrator_response

        # Act
        result_state = await node_step_39(state)

        # Assert - verify both storage locations
        assert result_state["knowledge_items"] == mock_documents, "knowledge_items must be at state root"
        assert result_state["kb_results"]["documents"] == mock_documents, "documents must be in kb_results"


@pytest.mark.asyncio
async def test_node_step_39_maps_total_results_to_doc_count():
    """Test that total_results from orchestrator is mapped to doc_count."""
    # Arrange
    state = {"user_query": "test", "messages": []}

    orchestrator_response = {
        "knowledge_items": [{"id": 1}, {"id": 2}, {"id": 3}],
        "total_results": 3,  # This should map to doc_count
        "search_mode": "hybrid",
    }

    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orchestrator:
        mock_orchestrator.return_value = orchestrator_response

        # Act
        result_state = await node_step_39(state)

        # Assert
        assert result_state["kb_results"]["doc_count"] == 3


@pytest.mark.asyncio
async def test_node_step_39_maps_search_mode_to_retrieval_method():
    """Test that search_mode from orchestrator is mapped to retrieval_method."""
    # Arrange
    state = {"user_query": "test", "messages": []}

    orchestrator_response = {
        "knowledge_items": [],
        "total_results": 0,
        "search_mode": "bm25_only",  # This should map to retrieval_method
        "timestamp": "2025-11-07T14:00:00Z",
    }

    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orchestrator:
        mock_orchestrator.return_value = orchestrator_response

        # Act
        result_state = await node_step_39(state)

        # Assert
        assert result_state["kb_results"]["retrieval_method"] == "bm25_only"


@pytest.mark.asyncio
async def test_node_step_39_handles_missing_optional_fields():
    """Test that missing optional fields (timestamp, search_mode) are handled."""
    # Arrange
    state = {"user_query": "test", "messages": []}

    # Minimal orchestrator response (only required fields)
    orchestrator_response = {
        "knowledge_items": [{"id": 1}],
        "total_results": 1,
        # No search_mode or timestamp
    }

    with patch(
        "app.core.langgraph.nodes.step_039__kbpre_fetch.step_39__kbpre_fetch", new_callable=AsyncMock
    ) as mock_orchestrator:
        mock_orchestrator.return_value = orchestrator_response

        # Act
        result_state = await node_step_39(state)

        # Assert - should use defaults
        assert result_state["kb_results"]["retrieval_method"] == "hybrid"  # Default
        assert result_state["kb_results"]["timestamp"] is None
        assert result_state["kb_results"]["doc_count"] == 1
