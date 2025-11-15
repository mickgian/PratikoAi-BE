"""
Tests for RAG Step 130: InvalidateFAQCache (CacheService.invalidate_faq by id or signature).

This step invalidates cached FAQ responses when an FAQ is published or updated.
"""

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRAGStep130InvalidateFAQCache:
    """Unit tests for Step 130: InvalidateFAQCache."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_130_invalidates_cache_by_faq_id(self, mock_rag_log):
        """Test Step 130: Invalidates cache by FAQ ID."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        ctx = {
            "published_faq": {
                "id": "faq_123",
                "question": "Test question",
                "answer": "Test answer",
                "category": "test",
            },
            "publication_metadata": {"faq_id": "faq_123", "operation": "created"},
            "request_id": "test-130-invalidate",
        }

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            mock_clear.return_value = 5  # 5 keys deleted

            result = await step_130__invalidate_faqcache(messages=[], ctx=ctx)

            assert isinstance(result, dict)
            assert "cache_invalidation" in result
            assert result["cache_invalidation"]["faq_id"] == "faq_123"
            assert result["cache_invalidation"]["keys_deleted"] == 5
            assert result["cache_invalidation"]["success"] is True

            # Verify cache was cleared with FAQ ID pattern
            mock_clear.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_130_invalidates_multiple_cache_patterns(self, mock_rag_log):
        """Test Step 130: Invalidates multiple cache patterns for FAQ."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        ctx = {
            "published_faq": {"id": "faq_456", "question": "Another question", "answer": "Another answer"},
            "publication_metadata": {"faq_id": "faq_456", "operation": "updated"},
            "request_id": "test-130-patterns",
        }

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            # Mock multiple clear calls for different patterns
            mock_clear.side_effect = [3, 2, 1]  # Different patterns return different counts

            result = await step_130__invalidate_faqcache(messages=[], ctx=ctx)

            assert "cache_invalidation" in result
            assert result["cache_invalidation"]["total_keys_deleted"] > 0
            assert result["cache_invalidation"]["patterns_cleared"] > 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_130_handles_cache_signature_invalidation(self, mock_rag_log):
        """Test Step 130: Handles cache invalidation by content signature."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        ctx = {
            "published_faq": {
                "id": "faq_789",
                "question": "Question with signature",
                "answer": "Answer with signature",
                "content_signature": "sig_abc123",
            },
            "publication_metadata": {"faq_id": "faq_789", "operation": "updated"},
            "request_id": "test-130-signature",
        }

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            mock_clear.return_value = 8

            result = await step_130__invalidate_faqcache(messages=[], ctx=ctx)

            assert "cache_invalidation" in result
            assert result["cache_invalidation"]["keys_deleted"] == 8
            assert "content_signature" in result["cache_invalidation"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_130_preserves_context(self, mock_rag_log):
        """Test Step 130: Preserves all context data."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        original_ctx = {
            "published_faq": {"id": "faq_ctx", "question": "Context test", "answer": "Context answer"},
            "publication_metadata": {"faq_id": "faq_ctx", "operation": "created"},
            "expert_id": "expert_123",
            "trust_score": 0.92,
            "user_data": {"id": "user_456"},
            "session_data": {"id": "session_789"},
            "request_id": "test-130-context",
        }

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            mock_clear.return_value = 3

            result = await step_130__invalidate_faqcache(messages=[], ctx=original_ctx.copy())

            # Verify all original context is preserved
            assert result["expert_id"] == original_ctx["expert_id"]
            assert result["trust_score"] == original_ctx["trust_score"]
            assert result["user_data"] == original_ctx["user_data"]
            assert result["session_data"] == original_ctx["session_data"]
            assert result["request_id"] == original_ctx["request_id"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_130_adds_invalidation_metadata(self, mock_rag_log):
        """Test Step 130: Adds cache invalidation metadata for tracking."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        ctx = {
            "published_faq": {"id": "faq_meta", "question": "Meta question", "answer": "Meta answer"},
            "publication_metadata": {"faq_id": "faq_meta", "operation": "updated"},
            "request_id": "test-130-metadata",
        }

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            mock_clear.return_value = 4

            result = await step_130__invalidate_faqcache(messages=[], ctx=ctx)

            assert "cache_invalidation" in result
            invalidation = result["cache_invalidation"]
            assert "invalidated_at" in invalidation
            assert "faq_id" in invalidation
            assert "operation" in invalidation
            assert "success" in invalidation

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_130_handles_no_cached_entries(self, mock_rag_log):
        """Test Step 130: Handles case where no cache entries exist."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        ctx = {
            "published_faq": {"id": "faq_empty", "question": "No cache question", "answer": "No cache answer"},
            "publication_metadata": {"faq_id": "faq_empty", "operation": "created"},
            "request_id": "test-130-empty",
        }

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            mock_clear.return_value = 0  # No keys deleted

            result = await step_130__invalidate_faqcache(messages=[], ctx=ctx)

            assert result["cache_invalidation"]["keys_deleted"] == 0
            assert result["cache_invalidation"]["success"] is True

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_130_handles_cache_service_error(self, mock_rag_log):
        """Test Step 130: Handles cache service errors gracefully."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        ctx = {
            "published_faq": {"id": "faq_error", "question": "Error question", "answer": "Error answer"},
            "publication_metadata": {"faq_id": "faq_error", "operation": "created"},
            "request_id": "test-130-error",
        }

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            mock_clear.side_effect = Exception("Redis connection error")

            result = await step_130__invalidate_faqcache(messages=[], ctx=ctx)

            assert "cache_invalidation" in result
            assert result["cache_invalidation"]["success"] is False
            assert "error" in result["cache_invalidation"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_130_logs_invalidation_details(self, mock_rag_log):
        """Test Step 130: Logs cache invalidation details for observability."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        ctx = {
            "published_faq": {"id": "faq_log", "question": "Log question", "answer": "Log answer"},
            "publication_metadata": {"faq_id": "faq_log", "operation": "updated"},
            "request_id": "test-130-logging",
        }

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            mock_clear.return_value = 7

            await step_130__invalidate_faqcache(messages=[], ctx=ctx)

            # Verify structured logging
            assert mock_rag_log.call_count >= 2
            final_call = None
            for call in mock_rag_log.call_args_list:
                if call[1].get("processing_stage") == "completed":
                    final_call = call[1]
                    break

            assert final_call is not None
            assert final_call["step"] == 130
            assert "faq_id" in final_call
            assert "keys_deleted" in final_call


class TestRAGStep130Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_130_parity_cache_invalidation(self):
        """Test Step 130 parity: Cache invalidation behavior unchanged."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        test_cases = [
            {"published_faq": {"id": "faq_1", "question": "Q1"}, "expected_calls": 1},
            {"published_faq": {"id": "faq_2", "question": "Q2", "content_signature": "sig_123"}, "expected_calls": 1},
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                "publication_metadata": {"faq_id": test_case["published_faq"]["id"]},
                "request_id": f"parity-{test_case['published_faq']['id']}",
            }

            with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
                mock_clear.return_value = 5

                with patch("app.orchestrators.preflight.rag_step_log"):
                    result = await step_130__invalidate_faqcache(messages=[], ctx=ctx)

                assert "cache_invalidation" in result
                assert mock_clear.call_count >= test_case["expected_calls"]


class TestRAGStep130Integration:
    """Integration tests for Step 130 with neighbors."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_publish_golden_to_130_integration(self, mock_preflight_log):
        """Test PublishGolden (Step 129) → Step 130 integration."""

        initial_ctx = {
            "published_faq": {
                "id": "faq_integration",
                "question": "Integration question",
                "answer": "Integration answer",
                "version": 2,
            },
            "publication_metadata": {
                "faq_id": "faq_integration",
                "operation": "updated",
                "published_at": datetime.now(UTC).isoformat(),
            },
            "operation": "updated",
            "request_id": "integration-129-130",
        }

        from app.orchestrators.preflight import step_130__invalidate_faqcache

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            mock_clear.return_value = 8

            result = await step_130__invalidate_faqcache(messages=[], ctx=initial_ctx)

            assert result["operation"] == "updated"
            assert "cache_invalidation" in result
            assert result["cache_invalidation"]["faq_id"] == "faq_integration"

    @pytest.mark.asyncio
    @patch("app.orchestrators.preflight.rag_step_log")
    async def test_step_130_completes_faq_publication_flow(self, mock_rag_log):
        """Test Step 130 completes the FAQ publication flow."""
        from app.orchestrators.preflight import step_130__invalidate_faqcache

        ctx = {
            "published_faq": {
                "id": "faq_complete",
                "question": "Complete flow question",
                "answer": "Complete flow answer",
            },
            "publication_metadata": {"faq_id": "faq_complete", "operation": "created"},
            "request_id": "test-130-complete",
        }

        with patch("app.services.cache.cache_service.clear_cache") as mock_clear:
            mock_clear.return_value = 3

            result = await step_130__invalidate_faqcache(messages=[], ctx=ctx)

            # Verify flow completion data
            assert "cache_invalidation" in result
            assert result["cache_invalidation"]["success"] is True
            assert "published_faq" in result  # Preserved for potential next steps
