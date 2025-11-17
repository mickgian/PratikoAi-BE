"""
Tests for RAG STEP 27 Orchestrator — KB newer than Golden as of or conflicting tags?
(RAG.golden.kb.newer.than.golden.as.of.or.conflicting.tags)

This decision orchestrator evaluates whether KB has newer content or conflicting tags compared
to the Golden Set match. Routes to ServeGolden (Step 28) if no conflict, or to
PreContextFromGolden (Step 29) if KB has updates that should be merged.
"""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRAGStep27KBDeltaOrchestrator:
    """Test suite for RAG STEP 27 orchestrator - KB delta/conflict evaluation."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_27_no_kb_changes_routes_to_serve_golden(self, mock_rag_log):
        """Test Step 27: No KB changes routes to ServeGolden."""
        from app.orchestrators.golden import step_27__kbdelta

        ctx = {
            "golden_match": {
                "faq_id": "faq_001",
                "answer": "Detrazioni al 22%",
                "updated_at": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
            },
            "kb_recent_changes": [],  # No recent KB changes from Step 26
            "has_recent_changes": False,
            "request_id": "test-27-no-changes",
        }

        result = await step_27__kbdelta(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert result["kb_has_delta"] is False
        assert result["next_step"] == "serve_golden"  # Routes to Step 28
        assert result["conflict_reason"] is None

        assert mock_rag_log.call_count >= 2

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_27_newer_kb_routes_to_merge(self, mock_rag_log):
        """Test Step 27: Newer KB content routes to context merge."""
        from app.orchestrators.golden import step_27__kbdelta

        golden_timestamp = datetime.now(UTC) - timedelta(days=30)
        kb_timestamp = datetime.now(UTC) - timedelta(days=5)

        ctx = {
            "golden_match": {
                "faq_id": "faq_001",
                "updated_at": golden_timestamp.isoformat(),
                "metadata": {"category": "tax"},
            },
            "kb_recent_changes": [
                {
                    "id": "kb_new",
                    "title": "Tax Update 2024",
                    "content": "New tax rates",
                    "updated_at": kb_timestamp.isoformat(),
                    "metadata": {"category": "tax"},
                }
            ],
            "has_recent_changes": True,
            "request_id": "test-27-newer",
        }

        result = await step_27__kbdelta(messages=[], ctx=ctx)

        assert result["kb_has_delta"] is True
        assert result["next_step"] == "pre_context_from_golden"  # Routes to Step 29
        assert result["conflict_reason"] == "newer_kb_content"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_27_conflicting_tags_routes_to_merge(self, mock_rag_log):
        """Test Step 27: Conflicting tags route to context merge."""
        from app.orchestrators.golden import step_27__kbdelta

        same_timestamp = datetime.now(UTC).isoformat()
        ctx = {
            "golden_match": {
                "faq_id": "faq_001",
                "updated_at": same_timestamp,
                "metadata": {"tags": ["rate_22", "deduction"]},
            },
            "kb_recent_changes": [
                {
                    "id": "kb_conflict",
                    "content": "Rate changed to 25%",
                    "updated_at": same_timestamp,
                    "metadata": {"tags": ["rate_25", "supersedes", "deduction"]},
                }
            ],
            "has_recent_changes": True,
            "request_id": "test-27-conflict",
        }

        result = await step_27__kbdelta(messages=[], ctx=ctx)

        assert result["kb_has_delta"] is True
        assert result["next_step"] == "pre_context_from_golden"
        assert result["conflict_reason"] == "conflicting_tags"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_27_preserves_context(self, mock_rag_log):
        """Test Step 27: Preserves all context from previous steps."""
        from app.orchestrators.golden import step_27__kbdelta

        ctx = {
            "user_query": "Test query",
            "golden_match": {"faq_id": "faq_001", "updated_at": datetime.now(UTC).isoformat()},
            "kb_recent_changes": [],
            "has_recent_changes": False,
            "high_confidence_match": True,
            "similarity_score": 0.95,
            "canonical_facts": ["test"],
            "request_id": "test-27-context",
        }

        result = await step_27__kbdelta(messages=[], ctx=ctx)

        assert result["user_query"] == "Test query"
        assert result["golden_match"]["faq_id"] == "faq_001"
        assert result["high_confidence_match"] is True
        assert result["similarity_score"] == 0.95
        assert result["canonical_facts"] == ["test"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_27_includes_delta_metadata(self, mock_rag_log):
        """Test Step 27: Includes delta evaluation metadata."""
        from app.orchestrators.golden import step_27__kbdelta

        ctx = {
            "golden_match": {"faq_id": "faq_001", "updated_at": datetime.now(UTC).isoformat()},
            "kb_recent_changes": [],
            "has_recent_changes": False,
            "request_id": "test-27-metadata",
        }

        result = await step_27__kbdelta(messages=[], ctx=ctx)

        assert "delta_evaluation" in result
        eval_data = result["delta_evaluation"]
        assert "kb_has_delta" in eval_data
        assert "conflict_reason" in eval_data
        assert "evaluation_timestamp" in eval_data

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_27_logs_delta_decision(self, mock_rag_log):
        """Test Step 27: Logs delta evaluation decision."""
        from app.orchestrators.golden import step_27__kbdelta

        ctx = {
            "golden_match": {"faq_id": "faq_001", "updated_at": datetime.now(UTC).isoformat()},
            "kb_recent_changes": [],
            "has_recent_changes": False,
            "request_id": "test-27-logging",
        }

        await step_27__kbdelta(messages=[], ctx=ctx)

        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        log = completed_logs[0][1]
        assert log["step"] == 27
        assert log["node_label"] == "KBDelta"
        assert "kb_has_delta" in log
        assert "next_step" in log

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_27_handles_missing_timestamps(self, mock_rag_log):
        """Test Step 27: Handles missing timestamps gracefully."""
        from app.orchestrators.golden import step_27__kbdelta

        ctx = {
            "golden_match": {"faq_id": "faq_001"},  # No updated_at
            "kb_recent_changes": [],
            "has_recent_changes": False,
            "request_id": "test-27-missing",
        }

        result = await step_27__kbdelta(messages=[], ctx=ctx)

        # Should default to no delta if timestamps are missing
        assert result["kb_has_delta"] is False
        assert result["next_step"] == "serve_golden"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_27_supersedes_tag_triggers_conflict(self, mock_rag_log):
        """Test Step 27: 'supersedes' tag triggers conflict detection."""
        from app.orchestrators.golden import step_27__kbdelta

        same_timestamp = datetime.now(UTC).isoformat()
        ctx = {
            "golden_match": {"faq_id": "faq_001", "updated_at": same_timestamp, "metadata": {}},
            "kb_recent_changes": [
                {"id": "kb_001", "updated_at": same_timestamp, "metadata": {"tags": ["supersedes", "update"]}}
            ],
            "has_recent_changes": True,
            "request_id": "test-27-supersedes",
        }

        result = await step_27__kbdelta(messages=[], ctx=ctx)

        assert result["kb_has_delta"] is True
        assert result["conflict_reason"] == "conflicting_tags"


class TestRAGStep27Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_27_parity_delta_logic(self):
        """Test Step 27: Delta evaluation logic matches expected behavior."""
        from app.orchestrators.golden import step_27__kbdelta

        test_cases = [
            # (has_recent_changes, expected_delta, expected_route)
            (False, False, "serve_golden"),
            (True, True, "pre_context_from_golden"),
        ]

        for has_changes, expected_delta, expected_route in test_cases:
            ctx = {
                "golden_match": {"faq_id": "test", "updated_at": datetime.now(UTC).isoformat()},
                "kb_recent_changes": [{"id": "kb_1", "updated_at": datetime.now(UTC).isoformat()}]
                if has_changes
                else [],
                "has_recent_changes": has_changes,
                "request_id": f"parity-{has_changes}",
            }

            result = await step_27__kbdelta(messages=[], ctx=ctx)

            assert (
                result["kb_has_delta"] == expected_delta
            ), f"has_changes={has_changes}: expected delta={expected_delta}, got {result['kb_has_delta']}"
            assert (
                result["next_step"] == expected_route
            ), f"has_changes={has_changes}: expected route={expected_route}, got {result['next_step']}"


class TestRAGStep27Integration:
    """Integration tests - prove Step 26 → 27 → 28/29 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_26_to_27_no_delta_integration(self, MockService, mock_golden_log):
        """Test Step 26 → 27 integration: No KB delta flows to ServeGolden."""
        from app.orchestrators.golden import step_27__kbdelta
        from app.orchestrators.kb import step_26__kbcontext_check

        initial_ctx = {
            "user_query": "Detrazioni fiscali 2024",
            "golden_match": {
                "faq_id": "faq_001",
                "answer": "Detrazioni...",
                "updated_at": (datetime.now(UTC) - timedelta(days=5)).isoformat(),
            },
            "request_id": "integration-26-27-no-delta",
        }

        mock_service = MockService.return_value
        mock_service.fetch_recent_kb_for_changes = AsyncMock(return_value=[])

        step_26_result = await step_26__kbcontext_check(messages=[], ctx=initial_ctx)

        assert step_26_result["has_recent_changes"] is False
        assert step_26_result["next_step"] == "kb_delta_check"

        step_27_result = await step_27__kbdelta(messages=[], ctx=step_26_result)

        assert step_27_result["kb_has_delta"] is False
        assert step_27_result["next_step"] == "serve_golden"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    @patch("app.services.knowledge_search_service.KnowledgeSearchService")
    async def test_step_26_to_27_with_delta_integration(self, MockService, mock_golden_log):
        """Test Step 26 → 27 integration: KB delta flows to context merge."""
        from app.orchestrators.golden import step_27__kbdelta
        from app.orchestrators.kb import step_26__kbcontext_check

        initial_ctx = {
            "user_query": "Tax rates 2024",
            "golden_match": {"faq_id": "faq_001", "updated_at": (datetime.now(UTC) - timedelta(days=30)).isoformat()},
            "request_id": "integration-26-27-delta",
        }

        mock_service = MockService.return_value
        mock_service.fetch_recent_kb_for_changes = AsyncMock(
            return_value=[
                MagicMock(
                    id="kb_new",
                    title="New rates",
                    content="Updated tax rates",
                    updated_at=datetime.now(UTC) - timedelta(days=3),
                    metadata={},
                )
            ]
        )

        step_26_result = await step_26__kbcontext_check(messages=[], ctx=initial_ctx)

        assert step_26_result["has_recent_changes"] is True

        step_27_result = await step_27__kbdelta(messages=[], ctx=step_26_result)

        assert step_27_result["kb_has_delta"] is True
        assert step_27_result["next_step"] == "pre_context_from_golden"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_27_prepares_for_step_28(self, mock_rag_log):
        """Test Step 27: Prepares context correctly for Step 28 (ServeGolden)."""
        from app.orchestrators.golden import step_27__kbdelta

        ctx = {
            "user_query": "Pensione anticipata",
            "golden_match": {
                "faq_id": "faq_002",
                "question": "Pensione anticipata?",
                "answer": "La pensione anticipata...",
                "updated_at": datetime.now(UTC).isoformat(),
            },
            "kb_recent_changes": [],
            "has_recent_changes": False,
            "request_id": "test-27-to-28",
        }

        result = await step_27__kbdelta(messages=[], ctx=ctx)

        assert result["next_step"] == "serve_golden"
        assert result["kb_has_delta"] is False
        assert result["golden_match"]["faq_id"] == "faq_002"
        assert "answer" in result["golden_match"]
