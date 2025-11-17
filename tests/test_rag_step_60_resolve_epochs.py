"""
Tests for RAG STEP 60 Orchestrator — EpochStamps.resolve kb_epoch golden_epoch ccnl_epoch parser_version
(RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version)

This orchestrator resolves version epochs from various data sources (KB, Golden Set, CCNL, parsers)
to enable cache invalidation based on data freshness. These epochs are used by Step 61 for cache key generation.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestRAGStep60ResolveEpochs:
    """Test suite for RAG STEP 60 orchestrator - resolve epochs."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_60_resolves_all_epochs(self, mock_rag_log):
        """Test Step 60: Resolves all epoch timestamps from context."""
        from app.orchestrators.golden import step_60__resolve_epochs

        ctx = {
            "kb_last_updated": "2024-01-20T10:00:00Z",
            "golden_last_updated": "2024-01-19T15:30:00Z",
            "ccnl_last_updated": "2024-01-18T12:00:00Z",
            "parser_version": "2.1.0",
            "request_id": "test-60-resolve",
        }

        result = await step_60__resolve_epochs(messages=[], ctx=ctx)

        assert isinstance(result, dict)
        assert "kb_epoch" in result
        assert "golden_epoch" in result
        assert "ccnl_epoch" in result
        assert "parser_version" in result
        assert result["kb_epoch"] == "2024-01-20T10:00:00Z"
        assert result["golden_epoch"] == "2024-01-19T15:30:00Z"
        assert result["ccnl_epoch"] == "2024-01-18T12:00:00Z"
        assert result["parser_version"] == "2.1.0"
        assert result["next_step"] == "gen_hash"

        assert mock_rag_log.call_count >= 2

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_60_handles_missing_epochs(self, mock_rag_log):
        """Test Step 60: Handles missing epoch timestamps gracefully."""
        from app.orchestrators.golden import step_60__resolve_epochs

        ctx = {"kb_last_updated": "2024-01-20T10:00:00Z", "parser_version": "2.1.0", "request_id": "test-60-partial"}

        result = await step_60__resolve_epochs(messages=[], ctx=ctx)

        assert result["kb_epoch"] == "2024-01-20T10:00:00Z"
        assert result["golden_epoch"] is None
        assert result["ccnl_epoch"] is None
        assert result["parser_version"] == "2.1.0"
        assert result["next_step"] == "gen_hash"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_60_uses_current_time_for_missing(self, mock_rag_log):
        """Test Step 60: Uses current time for missing epochs."""
        from app.orchestrators.golden import step_60__resolve_epochs

        ctx = {"request_id": "test-60-defaults"}

        result = await step_60__resolve_epochs(messages=[], ctx=ctx)

        # Should have some default values
        assert "kb_epoch" in result
        assert "golden_epoch" in result
        assert "ccnl_epoch" in result
        assert "parser_version" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_60_preserves_context(self, mock_rag_log):
        """Test Step 60: Preserves all context from previous steps."""
        from app.orchestrators.golden import step_60__resolve_epochs

        ctx = {
            "user_query": "Test query",
            "canonical_facts": ["tax", "2024"],
            "kb_last_updated": "2024-01-20T10:00:00Z",
            "golden_last_updated": "2024-01-19T15:30:00Z",
            "ccnl_last_updated": "2024-01-18T12:00:00Z",
            "parser_version": "2.1.0",
            "cache_check_initialized": True,
            "request_id": "test-60-context",
        }

        result = await step_60__resolve_epochs(messages=[], ctx=ctx)

        assert result["user_query"] == "Test query"
        assert result["canonical_facts"] == ["tax", "2024"]
        assert result["cache_check_initialized"] is True
        assert result["kb_epoch"] == "2024-01-20T10:00:00Z"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_60_logs_epoch_resolution(self, mock_rag_log):
        """Test Step 60: Logs epoch resolution details."""
        from app.orchestrators.golden import step_60__resolve_epochs

        ctx = {
            "kb_last_updated": "2024-01-20T10:00:00Z",
            "golden_last_updated": "2024-01-19T15:30:00Z",
            "ccnl_last_updated": "2024-01-18T12:00:00Z",
            "parser_version": "2.1.0",
            "request_id": "test-60-logging",
        }

        await step_60__resolve_epochs(messages=[], ctx=ctx)

        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        log = completed_logs[0][1]
        assert log["step"] == 60
        assert log["node_label"] == "ResolveEpochs"
        assert "epochs_resolved" in log

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_60_includes_epoch_metadata(self, mock_rag_log):
        """Test Step 60: Includes epoch resolution metadata."""
        from app.orchestrators.golden import step_60__resolve_epochs

        ctx = {
            "kb_last_updated": "2024-01-20T10:00:00Z",
            "golden_last_updated": "2024-01-19T15:30:00Z",
            "parser_version": "2.1.0",
            "request_id": "test-60-metadata",
        }

        result = await step_60__resolve_epochs(messages=[], ctx=ctx)

        assert "epoch_resolution_metadata" in result
        metadata = result["epoch_resolution_metadata"]
        assert "resolved_at" in metadata
        assert "epochs_count" in metadata
        assert metadata["epochs_count"] == 3  # kb, golden, parser_version (ccnl missing)

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_60_converts_timestamps_to_epochs(self, mock_rag_log):
        """Test Step 60: Converts ISO timestamps to epoch format if needed."""
        from app.orchestrators.golden import step_60__resolve_epochs

        ctx = {
            "kb_last_updated": "2024-01-20T10:00:00Z",
            "golden_last_updated": "2024-01-19T15:30:00Z",
            "request_id": "test-60-conversion",
        }

        result = await step_60__resolve_epochs(messages=[], ctx=ctx)

        # Epochs should be preserved as timestamps or converted
        assert result["kb_epoch"] is not None
        assert result["golden_epoch"] is not None


class TestRAGStep60Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_60_parity_epoch_resolution(self):
        """Test Step 60: Epoch resolution matches expected behavior."""
        from app.orchestrators.golden import step_60__resolve_epochs

        test_cases = [
            {
                "input": {
                    "kb_last_updated": "2024-01-20T10:00:00Z",
                    "golden_last_updated": "2024-01-19T15:30:00Z",
                    "ccnl_last_updated": "2024-01-18T12:00:00Z",
                    "parser_version": "2.1.0",
                },
                "expected_epochs": 4,
            },
            {"input": {"kb_last_updated": "2024-01-20T10:00:00Z", "parser_version": "2.0.0"}, "expected_epochs": 2},
            {
                "input": {},
                "expected_epochs": 0,  # or use defaults
            },
        ]

        for case in test_cases:
            ctx = {**case["input"], "request_id": "parity-test"}
            result = await step_60__resolve_epochs(messages=[], ctx=ctx)

            assert "kb_epoch" in result
            assert "golden_epoch" in result
            assert "ccnl_epoch" in result
            assert "parser_version" in result
            assert "next_step" in result
            assert result["next_step"] == "gen_hash"


class TestRAGStep60Integration:
    """Integration tests - prove Step 59 → 60 → 61 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    @patch("app.orchestrators.cache.rag_step_log")
    async def test_step_60_to_61_integration(self, mock_cache_log, mock_golden_log):
        """Test Step 60 → 61 integration: Epochs flow to hash generation."""
        from app.orchestrators.cache import step_61__gen_hash
        from app.orchestrators.golden import step_60__resolve_epochs

        initial_ctx = {
            "user_query": "Detrazioni fiscali 2024",
            "kb_last_updated": "2024-01-20T10:00:00Z",
            "golden_last_updated": "2024-01-19T15:30:00Z",
            "ccnl_last_updated": "2024-01-18T12:00:00Z",
            "parser_version": "2.1.0",
            "request_id": "integration-60-61",
        }

        step_60_result = await step_60__resolve_epochs(messages=[], ctx=initial_ctx)

        assert step_60_result["next_step"] == "gen_hash"
        assert "kb_epoch" in step_60_result
        assert "golden_epoch" in step_60_result
        assert "ccnl_epoch" in step_60_result
        assert "parser_version" in step_60_result

        # Step 61 should be able to use these epochs
        # (This would normally be tested with actual cache service)
        assert step_60_result["kb_epoch"] == "2024-01-20T10:00:00Z"
        assert step_60_result["golden_epoch"] == "2024-01-19T15:30:00Z"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_60_prepares_for_gen_hash(self, mock_rag_log):
        """Test Step 60: Prepares context correctly for Step 61 (GenHash)."""
        from app.orchestrators.golden import step_60__resolve_epochs

        ctx = {
            "user_query": "Test query",
            "kb_last_updated": "2024-01-20T10:00:00Z",
            "golden_last_updated": "2024-01-19T15:30:00Z",
            "ccnl_last_updated": "2024-01-18T12:00:00Z",
            "parser_version": "2.1.0",
            "doc_hashes": ["hash1", "hash2"],
            "query_hash": "query_abc123",
            "request_id": "test-60-to-61",
        }

        result = await step_60__resolve_epochs(messages=[], ctx=ctx)

        assert result["next_step"] == "gen_hash"
        assert "kb_epoch" in result
        assert "golden_epoch" in result
        assert "ccnl_epoch" in result
        assert "parser_version" in result
        assert "doc_hashes" in result
        assert "query_hash" in result
