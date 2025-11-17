#!/usr/bin/env python3
"""
Tests for RAG STEP 61 — CacheService.generate_response_key Generate cache key from signature and document hashes and epochs and version

This step generates comprehensive cache keys from query signatures, document hashes, epochs, and versions.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.orchestrators.cache import step_61__gen_hash


class TestRAGStep61GenHash:
    """Test suite for RAG STEP 61 - Generate cache key"""

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_61_hash_generation_success(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 61: Successful cache key generation"""

        # Mock cache service
        mock_cache_service.enabled = True
        mock_cache_service.generate_response_key.return_value = "cache_key_abc123def456"

        ctx = {
            "query_hash": "hash123",
            "doc_hashes": ["doc1", "doc2"],
            "kb_epoch": 1234567890,
            "golden_epoch": 1234567891,
            "ccnl_epoch": 1234567892,
            "parser_version": "2.1.0",
            "model": "gpt-4",
            "temperature": 0.2,
        }

        # Call the orchestrator function
        result = await step_61__gen_hash(ctx=ctx)

        # Verify the result structure
        assert isinstance(result, dict)
        assert result["cache_key_generated"] is True
        assert result["cache_key"] == "cache_key_abc123def456"
        assert result["query_hash"] == "hash123"
        assert result["doc_hashes"] == ["doc1", "doc2"]
        assert result["kb_epoch"] == 1234567890
        assert result["golden_epoch"] == 1234567891
        assert result["ccnl_epoch"] == 1234567892
        assert result["parser_version"] == "2.1.0"
        assert "timestamp" in result

        # Verify cache service was called correctly
        mock_cache_service.generate_response_key.assert_called_once()
        call_args = mock_cache_service.generate_response_key.call_args
        assert call_args[1]["query_hash"] == "hash123"
        assert call_args[1]["doc_hashes"] == ["doc1", "doc2"]
        assert call_args[1]["kb_epoch"] == 1234567890

        # Verify logging was called
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args
        assert "Cache key generated" in log_call[0][0]
        assert log_call[1]["extra"]["cache_event"] == "key_generated"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_61_cache_disabled(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 61: Cache key generation with cache service disabled"""

        # Mock cache service as disabled
        mock_cache_service.enabled = False

        ctx = {"query_hash": "hash123", "model": "gpt-3.5-turbo"}

        result = await step_61__gen_hash(ctx=ctx)

        assert result["cache_key_generated"] is False
        assert result["cache_key"] is None
        assert result["error"] == "Cache service disabled"

        # Should not call key generation
        mock_cache_service.generate_response_key.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_61_missing_query_hash(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 61: Handle missing query hash"""

        mock_cache_service.enabled = True

        ctx = {
            "model": "gpt-4"
            # Missing query_hash
        }

        result = await step_61__gen_hash(ctx=ctx)

        # Should return error result
        assert result["cache_key_generated"] is False
        assert result["error"] == "Missing required parameter: query_hash"

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Cache key generation failed" in error_call[0][0]

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_61_default_values(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 61: Default values for missing optional parameters"""

        mock_cache_service.enabled = True
        mock_cache_service.generate_response_key.return_value = "default_key_123"

        ctx = {
            "query_hash": "hash123"
            # Missing optional parameters
        }

        result = await step_61__gen_hash(ctx=ctx)

        assert result["cache_key_generated"] is True
        assert result["cache_key"] == "default_key_123"
        assert result["doc_hashes"] == []
        assert result["kb_epoch"] is None
        assert result["golden_epoch"] is None
        assert result["ccnl_epoch"] is None
        assert result["parser_version"] is None

        # Verify defaults were passed to service
        call_args = mock_cache_service.generate_response_key.call_args
        assert call_args[1]["doc_hashes"] == []
        assert call_args[1]["kb_epoch"] is None

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_61_key_generation_error(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 61: Handle key generation service error"""

        mock_cache_service.enabled = True
        mock_cache_service.generate_response_key.side_effect = Exception("Key generation failed")

        ctx = {"query_hash": "hash123", "model": "gpt-4"}

        result = await step_61__gen_hash(ctx=ctx)

        # Should return error result
        assert result["cache_key_generated"] is False
        assert result["error"] == "Key generation failed"

        # Verify error was logged
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_61_kwargs_parameters(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 61: Parameters passed via kwargs"""

        mock_cache_service.enabled = True
        mock_cache_service.generate_response_key.return_value = "kwargs_key_456"

        # Call with kwargs instead of ctx
        result = await step_61__gen_hash(
            query_hash="kwargs_hash",
            doc_hashes=["doc3", "doc4"],
            kb_epoch=9876543210,
            model="claude-3",
            temperature=0.5,
        )

        # Verify kwargs are processed correctly
        assert result["cache_key_generated"] is True
        assert result["cache_key"] == "kwargs_key_456"
        assert result["query_hash"] == "kwargs_hash"
        assert result["doc_hashes"] == ["doc3", "doc4"]
        assert result["kb_epoch"] == 9876543210

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service", None)
    async def test_step_61_no_cache_service(self, mock_logger, mock_rag_log):
        """Test Step 61: Handle missing cache service"""

        ctx = {"query_hash": "hash123", "model": "gpt-4"}

        result = await step_61__gen_hash(ctx=ctx)

        assert result["cache_key_generated"] is False
        assert result["cache_key"] is None
        assert result["error"] == "Cache service not available"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_61_complex_document_hashes(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 61: Complex document hash arrays"""

        mock_cache_service.enabled = True
        mock_cache_service.generate_response_key.return_value = "complex_key_789"

        ctx = {
            "query_hash": "complex_hash",
            "doc_hashes": [
                "doc_hash_1_very_long_sha256_string",
                "doc_hash_2_another_long_sha256_string",
                "doc_hash_3_third_long_sha256_string",
            ],
            "kb_epoch": 1700000000,
            "golden_epoch": 1700000001,
            "ccnl_epoch": 1700000002,
            "parser_version": "3.2.1",
        }

        result = await step_61__gen_hash(ctx=ctx)

        assert result["cache_key_generated"] is True
        assert result["cache_key"] == "complex_key_789"
        assert len(result["doc_hashes"]) == 3
        assert result["doc_hashes"][0].startswith("doc_hash_1_")

        # Verify all parameters passed correctly
        call_args = mock_cache_service.generate_response_key.call_args
        assert len(call_args[1]["doc_hashes"]) == 3
        assert call_args[1]["parser_version"] == "3.2.1"

    @pytest.mark.asyncio
    @patch("app.orchestrators.cache.rag_step_log")
    @patch("app.core.logging.logger")
    @patch("app.services.cache.cache_service")
    async def test_step_61_performance_tracking(self, mock_cache_service, mock_logger, mock_rag_log):
        """Test Step 61: Performance tracking with timer"""

        with patch("app.orchestrators.cache.rag_step_timer") as mock_timer:
            # Mock the timer context manager
            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            mock_cache_service.enabled = True
            mock_cache_service.generate_response_key.return_value = "perf_key_123"

            # Call the orchestrator function
            await step_61__gen_hash(ctx={"query_hash": "perf_hash", "model": "gpt-4"})

            # Verify timer was used
            mock_timer.assert_called_with(
                61,
                "RAG.cache.cacheservice.generate.response.key.sig.and.doc.hashes.and.epochs.and.versions",
                "GenHash",
                stage="start",
            )
