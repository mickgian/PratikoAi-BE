"""
Tests for RAG STEP 27 — KB newer than Golden as of or conflicting tags?

This step is a decision node that compares KB results from STEP 26 with Golden Set
to determine if KB has newer or conflicting information that requires merging context
instead of serving the Golden Set answer directly.
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from app.services.kb_delta_decision import KBDeltaDecision
from app.services.knowledge_search_service import SearchResult


class TestRAGStep27KBDelta:
    """Test suite for RAG STEP 27 - KB newer than Golden as of or conflicting tags?"""

    @pytest.fixture
    def kb_delta_decision(self):
        """Create KBDeltaDecision instance for testing."""
        return KBDeltaDecision()

    @pytest.fixture
    def golden_metadata(self):
        """Sample Golden Set metadata."""
        return {
            "id": "golden_123",
            "title": "Tax Deduction Guidelines",
            "category": "tax",
            "tags": ["business_tax", "deductions", "2023"],
            "updated_at": datetime.now(timezone.utc) - timedelta(days=30),  # 30 days old
            "confidence": 0.95,
            "source": "golden_set"
        }

    @pytest.fixture
    def newer_kb_results(self):
        """KB results that are newer than Golden Set."""
        now = datetime.now(timezone.utc)
        return [
            SearchResult(
                id="kb_1",
                title="Updated Tax Deduction Rules 2024",
                content="New tax deduction limits for 2024",
                category="tax",
                score=0.85,
                source="kb_rss",
                updated_at=now - timedelta(days=5),  # Much newer than golden
                metadata={
                    "tags": ["business_tax", "deductions", "2024", "rate_change"],
                    "conflict_detected": True,
                    "conflict_reasons": ["explicit_conflict_tags"]
                }
            ),
            SearchResult(
                id="kb_2", 
                title="Recent Tax Law Changes",
                content="Latest changes to business tax regulations",
                category="tax",
                score=0.78,
                source="kb_rss",
                updated_at=now - timedelta(days=10),  # Still newer than golden
                metadata={
                    "tags": ["business_tax", "law_change"],
                    "conflict_detected": True,
                    "conflict_reasons": ["same_category"]
                }
            )
        ]

    @pytest.fixture
    def older_kb_results(self):
        """KB results that are older than Golden Set."""
        golden_time = datetime.now(timezone.utc) - timedelta(days=30)
        return [
            SearchResult(
                id="kb_old",
                title="Old Tax Information",
                content="Outdated tax information",
                category="tax",
                score=0.65,
                source="kb_static",
                updated_at=golden_time - timedelta(days=10),  # Older than golden
                metadata={"tags": ["business_tax", "outdated"]}
            )
        ]

    @pytest.fixture
    def conflicting_kb_results(self):
        """KB results with conflicting tags but similar timestamp."""
        golden_time = datetime.now(timezone.utc) - timedelta(days=30)
        return [
            SearchResult(
                id="kb_conflict",
                title="Tax Rate Update", 
                content="Tax rates updated",
                category="tax",
                score=0.80,
                source="kb_rss",
                updated_at=golden_time + timedelta(hours=1),  # Slightly newer
                metadata={
                    "tags": ["business_tax", "rate_change", "supersedes_previous"],
                    "conflict_detected": True,
                    "conflict_reasons": ["explicit_conflict_tags", "overlapping_tags"]
                }
            )
        ]

    @pytest.fixture
    def decision_data_template(self):
        """Template for decision data."""
        return {
            "trace_id": "test_trace_001",
            "user_id": str(uuid.uuid4()),
            "session_id": "test_session_456"
        }

    @pytest.mark.asyncio
    @patch('app.services.kb_delta_decision.rag_step_log')
    async def test_kb_newer_than_golden_decision_yes(
        self,
        mock_log,
        kb_delta_decision,
        golden_metadata,
        newer_kb_results,
        decision_data_template
    ):
        """Test decision when KB has newer information than Golden Set."""
        decision_data = {
            **decision_data_template,
            "kb_results": newer_kb_results,
            "golden_metadata": golden_metadata
        }
        
        result = kb_delta_decision.evaluate_kb_vs_golden(decision_data)
        
        assert result["decision"] == "newer_kb"
        assert result["should_merge_context"] is True
        assert result["newer_count"] == 2
        assert result["conflict_count"] == 2
        assert "KB has 2 results newer than Golden Set" in result["reason"]

    @pytest.mark.asyncio
    @patch('app.services.kb_delta_decision.rag_step_log')
    async def test_kb_older_than_golden_decision_no(
        self,
        mock_log,
        kb_delta_decision,
        golden_metadata,
        older_kb_results,
        decision_data_template
    ):
        """Test decision when KB has no newer information than Golden Set."""
        decision_data = {
            **decision_data_template,
            "kb_results": older_kb_results,
            "golden_metadata": golden_metadata
        }
        
        result = kb_delta_decision.evaluate_kb_vs_golden(decision_data)
        
        assert result["decision"] == "no_newer_kb"
        assert result["should_merge_context"] is False
        assert result["newer_count"] == 0
        assert "No KB results newer than Golden Set" in result["reason"]

    @pytest.mark.asyncio
    @patch('app.services.kb_delta_decision.rag_step_log')
    async def test_kb_conflicting_tags_decision_yes(
        self,
        mock_log,
        kb_delta_decision,
        golden_metadata,
        conflicting_kb_results,
        decision_data_template
    ):
        """Test decision when KB has conflicting tags with Golden Set."""
        decision_data = {
            **decision_data_template,
            "kb_results": conflicting_kb_results,
            "golden_metadata": golden_metadata
        }
        
        result = kb_delta_decision.evaluate_kb_vs_golden(decision_data)
        
        assert result["decision"] == "newer_kb"
        assert result["should_merge_context"] is True
        assert result["conflict_count"] == 1
        assert "conflict_types" in result

    @pytest.mark.asyncio
    @patch('app.services.kb_delta_decision.rag_step_log')
    async def test_empty_kb_results_decision_no(
        self,
        mock_log,
        kb_delta_decision,
        golden_metadata,
        decision_data_template
    ):
        """Test decision when no KB results are available."""
        decision_data = {
            **decision_data_template,
            "kb_results": [],
            "golden_metadata": golden_metadata
        }
        
        result = kb_delta_decision.evaluate_kb_vs_golden(decision_data)
        
        assert result["decision"] == "no_newer_kb"
        assert result["should_merge_context"] is False
        assert result["reason"] == "No KB results to compare with Golden Set"

    @pytest.mark.asyncio
    @patch('app.services.kb_delta_decision.rag_step_log')
    async def test_missing_golden_metadata_decision_yes(
        self,
        mock_log,
        kb_delta_decision,
        newer_kb_results,
        decision_data_template
    ):
        """Test decision when Golden metadata is missing."""
        decision_data = {
            **decision_data_template,
            "kb_results": newer_kb_results,
            "golden_metadata": None
        }
        
        result = kb_delta_decision.evaluate_kb_vs_golden(decision_data)
        
        assert result["decision"] == "newer_kb"
        assert result["should_merge_context"] is True
        assert result["reason"] == "No Golden Set metadata available, using KB results"

    @pytest.mark.asyncio  
    @patch('app.services.kb_delta_decision.rag_step_log')
    async def test_mixed_kb_results_decision_yes(
        self,
        mock_log,
        kb_delta_decision,
        golden_metadata,
        decision_data_template
    ):
        """Test decision with mix of newer and older KB results."""
        # Mix of newer and older results
        mixed_results = [
            SearchResult(
                id="kb_newer",
                title="Recent Update",
                content="Recent information", 
                category="tax",
                score=0.85,
                source="kb_rss",
                updated_at=datetime.now(timezone.utc) - timedelta(days=5),  # Newer
                metadata={"conflict_detected": True}
            ),
            SearchResult(
                id="kb_older",
                title="Old Info",
                content="Older information",
                category="tax", 
                score=0.65,
                source="kb_static",
                updated_at=datetime.now(timezone.utc) - timedelta(days=60)  # Older
            )
        ]
        
        decision_data = {
            **decision_data_template,
            "kb_results": mixed_results,
            "golden_metadata": golden_metadata
        }
        
        result = kb_delta_decision.evaluate_kb_vs_golden(decision_data)
        
        assert result["decision"] == "newer_kb"
        assert result["newer_count"] == 1
        assert result["should_merge_context"] is True

    @pytest.mark.asyncio
    @patch('app.services.kb_delta_decision.rag_step_log')
    async def test_structured_logging_format(
        self,
        mock_log,
        kb_delta_decision,
        golden_metadata,
        newer_kb_results,
        decision_data_template
    ):
        """Test that structured logging follows correct format for STEP 27."""
        decision_data = {
            **decision_data_template,
            "kb_results": newer_kb_results,
            "golden_metadata": golden_metadata
        }
        
        result = kb_delta_decision.evaluate_kb_vs_golden(decision_data)
        
        # Verify the log was called with correct STEP 27 format
        mock_log.assert_called()
        
        # Find the decision log call (has decision field)
        decision_log_calls = [
            call for call in mock_log.call_args_list
            if (len(call[1]) > 3 and 
                call[1].get('step') == 27 and
                'decision' in call[1])
        ]
        
        # Should have at least one log call for the decision
        assert len(decision_log_calls) > 0
        
        # Verify required fields
        log_call = decision_log_calls[0] 
        assert log_call[1]['step'] == 27
        assert log_call[1]['step_id'] == "RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags"
        assert log_call[1]['node_label'] == "KBDelta"
        assert 'decision' in log_call[1]
        assert 'trace_id' in log_call[1]

    @pytest.mark.asyncio
    async def test_decision_edge_cases(self, kb_delta_decision, decision_data_template):
        """Test edge cases in decision logic."""
        
        # Case 1: KB result with same timestamp as Golden
        same_time = datetime.now(timezone.utc) - timedelta(days=30)
        same_timestamp_result = [
            SearchResult(
                id="kb_same",
                title="Same Time Result",
                content="Content",
                category="tax",
                score=0.70,
                source="kb_rss",
                updated_at=same_time,
                metadata={"conflict_detected": False}
            )
        ]
        
        golden_same_time = {
            "updated_at": same_time,
            "tags": ["business_tax"],
            "category": "tax"
        }
        
        decision_data = {
            **decision_data_template,
            "kb_results": same_timestamp_result,
            "golden_metadata": golden_same_time
        }
        
        result = kb_delta_decision.evaluate_kb_vs_golden(decision_data)
        # Same timestamp should result in no newer KB
        assert result["decision"] == "no_newer_kb"
        assert result["newer_count"] == 0