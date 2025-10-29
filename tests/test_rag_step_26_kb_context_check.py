"""
Tests for RAG STEP 26 — KnowledgeSearch.context_topk fetch recent KB for changes

This step is specifically for checking recent KB changes when a Golden Set hit occurs,
to determine if KB has newer or conflicting information that should be merged with
the Golden Set response.
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.langgraph.graph import GraphState
from app.services.knowledge_search_service import KnowledgeSearchService, SearchResult, KnowledgeSearchConfig


class TestRAGStep26KBContextCheck:
    """Test suite for RAG STEP 26 - KnowledgeSearch.context_topk fetch recent KB for changes."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_vector_service(self):
        """Mock vector service."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = True
        mock_service.create_embedding.return_value = [0.1, 0.2, 0.3]
        mock_service.search_similar.return_value = []
        return mock_service

    @pytest.fixture
    def knowledge_search_service(self, mock_db_session, mock_vector_service):
        """Create KnowledgeSearchService instance for testing."""
        config = KnowledgeSearchConfig(
            max_results=5,
            recency_weight=0.3,  # Higher weight for recency for context check
            bm25_weight=0.4,
            vector_weight=0.3
        )
        return KnowledgeSearchService(
            db_session=mock_db_session,
            vector_service=mock_vector_service,
            config=config
        )

    @pytest.fixture
    def sample_kb_results(self):
        """Sample knowledge base results for testing."""
        now = datetime.now(timezone.utc)
        return [
            SearchResult(
                id="kb_1",
                title="Recent Tax Changes 2024",
                content="Important tax updates for 2024 fiscal year",
                category="tax",
                score=0.85,
                source="kb_rss",
                updated_at=now - timedelta(days=1),  # Very recent
                bm25_score=0.7,
                vector_score=0.8,
                recency_score=0.95
            ),
            SearchResult(
                id="kb_2", 
                title="Updated Labor Law Provisions",
                content="New labor law changes effective January 2024",
                category="labor",
                score=0.75,
                source="kb_rss",
                updated_at=now - timedelta(days=7),  # Recent
                bm25_score=0.6,
                vector_score=0.7,
                recency_score=0.85
            ),
            SearchResult(
                id="kb_3",
                title="Old Tax Guide",
                content="Outdated tax information from 2022",
                category="tax",
                score=0.45,
                source="kb_static",
                updated_at=now - timedelta(days=365),  # Old
                bm25_score=0.8,
                vector_score=0.6,
                recency_score=0.1
            )
        ]

    @pytest.fixture
    def context_check_query_data(self):
        """Query data for context check scenario."""
        return {
            "query": "tax deductions for small business",
            "canonical_facts": ["tax", "business", "deductions"],
            "user_id": str(uuid.uuid4()),
            "session_id": "test_session_123",
            "trace_id": "trace_001",
            "golden_timestamp": datetime.now(timezone.utc) - timedelta(days=30),  # Golden is 30 days old
            "context_check": True,  # Flag to indicate this is for context checking
            "recency_threshold_days": 14  # Only consider KB items newer than 14 days
        }

    @pytest.mark.asyncio
    @patch('app.services.knowledge_search_service.rag_step_log')
    @patch('app.services.knowledge_search_service.rag_step_timer')
    async def test_fetch_recent_kb_for_changes_basic(
        self, 
        mock_timer, 
        mock_log,
        knowledge_search_service,
        context_check_query_data,
        sample_kb_results
    ):
        """Test basic functionality of fetching recent KB for changes."""
        # Mock the timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Mock the search service to return sample results
        with patch.object(knowledge_search_service, '_perform_hybrid_search', return_value=sample_kb_results):
            
            results = await knowledge_search_service.fetch_recent_kb_for_changes(context_check_query_data)
            
            # Should return only recent results (within 14 days)
            assert len(results) == 2  # kb_1 and kb_2, but not kb_3 (too old)
            assert results[0].id == "kb_1"  # Most recent first
            assert results[1].id == "kb_2"
            
            # Verify structured logging was called
            mock_log.assert_called()
            mock_timer.assert_called_once_with(
                26,
                "RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes", 
                "KBContextCheck",
                query="tax deductions for small business",
                trace_id="trace_001"
            )

    @pytest.mark.asyncio
    @patch('app.services.knowledge_search_service.rag_step_log')
    async def test_fetch_recent_kb_no_recent_changes(
        self,
        mock_log,
        knowledge_search_service,
        context_check_query_data
    ):
        """Test when no recent KB changes exist."""
        # Only old results
        old_results = [
            SearchResult(
                id="kb_old",
                title="Old Information",
                content="Outdated content",
                category="tax",
                score=0.8,
                source="kb_static",
                updated_at=datetime.now(timezone.utc) - timedelta(days=60),
                recency_score=0.05
            )
        ]
        
        with patch.object(knowledge_search_service, '_perform_hybrid_search', return_value=old_results):
            
            results = await knowledge_search_service.fetch_recent_kb_for_changes(context_check_query_data)
            
            # Should return empty list since no recent changes
            assert len(results) == 0
            
            # Verify logging
            mock_log.assert_called()
            log_calls = [call for call in mock_log.call_args_list if 'no_recent_changes' in str(call)]
            assert len(log_calls) > 0

    @pytest.mark.asyncio
    @patch('app.services.knowledge_search_service.rag_step_log')
    async def test_fetch_recent_kb_with_golden_timestamp_comparison(
        self,
        mock_log,
        knowledge_search_service,
        context_check_query_data,
        sample_kb_results
    ):
        """Test filtering based on Golden Set timestamp."""
        # Set Golden timestamp to 10 days ago
        context_check_query_data["golden_timestamp"] = datetime.now(timezone.utc) - timedelta(days=10)
        
        with patch.object(knowledge_search_service, '_perform_hybrid_search', return_value=sample_kb_results):
            
            results = await knowledge_search_service.fetch_recent_kb_for_changes(context_check_query_data)
            
            # Should only return kb_1 (1 day old) as it's newer than Golden (10 days old)
            # kb_2 is 7 days old, which is newer than 10 days, so it should be included too
            assert len(results) == 2
            assert all(r.updated_at > context_check_query_data["golden_timestamp"] for r in results)

    @pytest.mark.asyncio
    @patch('app.services.knowledge_search_service.rag_step_log')
    async def test_detect_conflicting_information(
        self,
        mock_log,
        knowledge_search_service,
        context_check_query_data
    ):
        """Test detection of conflicting information with Golden Set."""
        # Mock results with conflicting tags/categories
        conflicting_results = [
            SearchResult(
                id="kb_conflict",
                title="Tax Rate Update - 22% to 25%",
                content="Tax rates have been updated from 22% to 25%",
                category="tax",
                score=0.9,
                source="kb_rss",
                updated_at=datetime.now(timezone.utc) - timedelta(days=1),
                metadata={"conflict_tags": ["rate_change", "supersedes_previous"]}
            )
        ]
        
        # Add conflict detection metadata to query
        context_check_query_data["golden_metadata"] = {
            "category": "tax",
            "tags": ["rate_22_percent"],
            "content_hash": "original_content_hash"
        }
        
        with patch.object(knowledge_search_service, '_perform_hybrid_search', return_value=conflicting_results):
            
            results = await knowledge_search_service.fetch_recent_kb_for_changes(context_check_query_data)
            
            assert len(results) == 1
            # Should flag as potential conflict
            log_calls = mock_log.call_args_list
            conflict_logs = [call for call in log_calls if 'potential_conflict' in str(call)]
            assert len(conflict_logs) > 0

    @pytest.mark.asyncio
    @patch('app.services.knowledge_search_service.rag_step_log')
    async def test_error_handling_fetch_recent_kb(
        self,
        mock_log,
        knowledge_search_service,
        context_check_query_data
    ):
        """Test error handling in fetch_recent_kb_for_changes."""
        # Mock search to raise exception
        with patch.object(knowledge_search_service, '_perform_hybrid_search', side_effect=Exception("Search failed")):
            
            results = await knowledge_search_service.fetch_recent_kb_for_changes(context_check_query_data)
            
            # Should return empty list on error (graceful degradation)
            assert len(results) == 0
            
            # Verify error logging
            error_logs = [call for call in mock_log.call_args_list if 'ERROR' in str(call)]
            assert len(error_logs) > 0

    @pytest.mark.asyncio
    async def test_context_check_integration_with_graph_state(self, mock_db_session, mock_vector_service):
        """Test integration with GraphState for context checking."""
        # Create minimal GraphState
        state = GraphState(
            messages=[],
            session_id="test_session_123"
        )
        
        # Mock query data from state
        query_data = {
            "query": "business tax rates",
            "user_id": str(uuid.uuid4()),  # user_id comes from elsewhere, not GraphState
            "session_id": state.session_id,
            "trace_id": "integration_test",
            "context_check": True,
            "golden_timestamp": datetime.now(timezone.utc) - timedelta(days=30)
        }
        
        service = KnowledgeSearchService(mock_db_session, mock_vector_service)
        
        # Mock the search to return empty results
        with patch.object(service, '_perform_hybrid_search', return_value=[]):
            results = await service.fetch_recent_kb_for_changes(query_data)
            assert isinstance(results, list)

    @pytest.mark.asyncio
    @patch('app.services.knowledge_search_service.rag_step_log')  
    async def test_structured_logging_format(
        self,
        mock_log,
        knowledge_search_service,
        context_check_query_data,
        sample_kb_results
    ):
        """Test that structured logging follows the correct format for STEP 26."""
        with patch.object(knowledge_search_service, '_perform_hybrid_search', return_value=sample_kb_results):
            
            await knowledge_search_service.fetch_recent_kb_for_changes(context_check_query_data)
            
            # Verify the log format matches RAG STEP 26 specification
            mock_log.assert_called()
            
            # Find the completed log call (has recent_changes_count)
            completed_log_calls = [
                call for call in mock_log.call_args_list 
                if (len(call[1]) > 5 and 
                    call[1].get('step') == 26 and 
                    call[1].get('processing_stage') == 'completed')
            ]
            assert len(completed_log_calls) > 0
            
            # Verify required fields in completed log call
            log_call = completed_log_calls[0]
            assert log_call[1]['step'] == 26
            assert log_call[1]['step_id'] == "RAG.kb.knowledgesearch.context.topk.fetch.recent.kb.for.changes"
            assert log_call[1]['node_label'] == "KBContextCheck"
            assert 'query' in log_call[1]
            assert 'trace_id' in log_call[1]
            assert 'recent_changes_count' in log_call[1]