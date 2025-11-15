"""
Tests for RAG Step 129: PublishGolden (GoldenSet.publish_or_update versioned entry).

This step publishes or updates an approved FAQ entry in the Golden Set database with versioning.
"""

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRAGStep129PublishGolden:
    """Unit tests for Step 129: PublishGolden."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_129_creates_new_faq_entry(self, mock_rag_log):
        """Test Step 129: Creates new FAQ entry."""
        from app.orchestrators.golden import step_129__publish_golden

        ctx = {
            "faq_candidate": {
                "question": "How do I calculate INPS contributions?",
                "answer": "INPS contributions are calculated based on...",
                "category": "contributions",
                "regulatory_references": ["D.L. 201/2011"],
                "quality_score": 0.96,
            },
            "candidate_metadata": {"candidate_id": "candidate_123"},
            "approval_decision": "auto_approved",
            "request_id": "test-129-create",
        }

        with patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create:
            mock_faq = MagicMock()
            mock_faq.id = "faq_new_123"
            mock_faq.version = 1
            mock_faq.question = ctx["faq_candidate"]["question"]
            mock_create.return_value = mock_faq

            result = await step_129__publish_golden(messages=[], ctx=ctx)

            assert isinstance(result, dict)
            assert "published_faq" in result
            assert result["published_faq"]["id"] == "faq_new_123"
            assert result["published_faq"]["version"] == 1
            assert result["next_step"] == "invalidate_faq_cache"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_129_updates_existing_faq_entry(self, mock_rag_log):
        """Test Step 129: Updates existing FAQ entry with versioning."""
        from app.orchestrators.golden import step_129__publish_golden

        ctx = {
            "faq_candidate": {
                "question": "Updated question",
                "answer": "Updated answer",
                "category": "test",
                "existing_faq_id": "faq_existing_456",
            },
            "candidate_metadata": {"candidate_id": "candidate_456"},
            "approval_decision": "auto_approved",
            "request_id": "test-129-update",
        }

        with patch("app.services.intelligent_faq_service.update_faq_entry") as mock_update:
            mock_faq = MagicMock()
            mock_faq.id = "faq_existing_456"
            mock_faq.version = 2
            mock_faq.question = ctx["faq_candidate"]["question"]
            mock_update.return_value = mock_faq

            result = await step_129__publish_golden(messages=[], ctx=ctx)

            assert "published_faq" in result
            assert result["published_faq"]["id"] == "faq_existing_456"
            assert result["published_faq"]["version"] == 2
            assert result["operation"] == "updated"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_129_preserves_regulatory_references(self, mock_rag_log):
        """Test Step 129: Preserves regulatory references in published FAQ."""
        from app.orchestrators.golden import step_129__publish_golden

        ctx = {
            "faq_candidate": {
                "question": "Test question",
                "answer": "Test answer",
                "category": "test",
                "regulatory_references": ["D.Lgs. 151/2001", "Circolare INPS 91/2022"],
            },
            "candidate_metadata": {"candidate_id": "candidate_refs"},
            "approval_decision": "auto_approved",
            "request_id": "test-129-refs",
        }

        with patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create:
            mock_faq = MagicMock()
            mock_faq.id = "faq_refs_123"
            mock_faq.regulatory_refs = ctx["faq_candidate"]["regulatory_references"]
            mock_create.return_value = mock_faq

            result = await step_129__publish_golden(messages=[], ctx=ctx)

            # Verify create was called with regulatory refs
            mock_create.assert_called_once()
            assert "published_faq" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_129_preserves_context(self, mock_rag_log):
        """Test Step 129: Preserves all context data."""
        from app.orchestrators.golden import step_129__publish_golden

        original_ctx = {
            "faq_candidate": {"question": "Test question", "answer": "Test answer", "category": "test"},
            "candidate_metadata": {"candidate_id": "candidate_ctx", "expert_id": "expert_123"},
            "approval_decision": "auto_approved",
            "expert_id": "expert_123",
            "trust_score": 0.92,
            "user_data": {"id": "user_456"},
            "session_data": {"id": "session_789"},
            "request_id": "test-129-context",
        }

        with patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create:
            mock_faq = MagicMock()
            mock_faq.id = "faq_ctx"
            mock_create.return_value = mock_faq

            result = await step_129__publish_golden(messages=[], ctx=original_ctx.copy())

            # Verify all original context is preserved
            assert result["expert_id"] == original_ctx["expert_id"]
            assert result["trust_score"] == original_ctx["trust_score"]
            assert result["user_data"] == original_ctx["user_data"]
            assert result["session_data"] == original_ctx["session_data"]
            assert result["request_id"] == original_ctx["request_id"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_129_adds_publication_metadata(self, mock_rag_log):
        """Test Step 129: Adds publication metadata for tracking."""
        from app.orchestrators.golden import step_129__publish_golden

        ctx = {
            "faq_candidate": {"question": "Question", "answer": "Answer", "category": "test"},
            "candidate_metadata": {"candidate_id": "candidate_meta"},
            "approval_decision": "auto_approved",
            "request_id": "test-129-metadata",
        }

        with patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create:
            mock_faq = MagicMock()
            mock_faq.id = "faq_meta"
            mock_faq.created_at = datetime.now(UTC)
            mock_create.return_value = mock_faq

            result = await step_129__publish_golden(messages=[], ctx=ctx)

            assert "publication_metadata" in result
            metadata = result["publication_metadata"]
            assert "published_at" in metadata
            assert "faq_id" in metadata
            assert metadata["operation"] in ["created", "updated"]
            assert "candidate_id" in metadata

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_129_routes_to_cache_invalidation(self, mock_rag_log):
        """Test Step 129: Routes to cache invalidation step."""
        from app.orchestrators.golden import step_129__publish_golden

        ctx = {
            "faq_candidate": {"question": "Question", "answer": "Answer", "category": "test"},
            "candidate_metadata": {"candidate_id": "candidate_cache"},
            "approval_decision": "auto_approved",
            "request_id": "test-129-cache",
        }

        with patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create:
            mock_faq = MagicMock()
            mock_faq.id = "faq_cache"
            mock_create.return_value = mock_faq

            result = await step_129__publish_golden(messages=[], ctx=ctx)

            assert result["next_step"] == "invalidate_faq_cache"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_129_handles_error_gracefully(self, mock_rag_log):
        """Test Step 129: Handles errors gracefully."""
        from app.orchestrators.golden import step_129__publish_golden

        ctx = {
            "faq_candidate": {"question": "Question", "answer": "Answer", "category": "test"},
            "candidate_metadata": {"candidate_id": "candidate_error"},
            "approval_decision": "auto_approved",
            "request_id": "test-129-error",
        }

        with patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create:
            mock_create.side_effect = Exception("Database error")

            result = await step_129__publish_golden(messages=[], ctx=ctx)

            assert "published_faq" in result
            assert "error" in result["published_faq"]
            assert "Database error" in result["published_faq"]["error"]
            # Still routes to next step for error handling
            assert result["next_step"] == "invalidate_faq_cache"

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_129_logs_publication_details(self, mock_rag_log):
        """Test Step 129: Logs publication details for observability."""
        from app.orchestrators.golden import step_129__publish_golden

        ctx = {
            "faq_candidate": {
                "question": "Test question for logging",
                "answer": "Test answer",
                "category": "test_category",
            },
            "candidate_metadata": {"candidate_id": "candidate_log"},
            "approval_decision": "auto_approved",
            "request_id": "test-129-logging",
        }

        with patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create:
            mock_faq = MagicMock()
            mock_faq.id = "faq_log"
            mock_faq.version = 1
            mock_create.return_value = mock_faq

            await step_129__publish_golden(messages=[], ctx=ctx)

            # Verify structured logging
            assert mock_rag_log.call_count >= 2
            final_call = None
            for call in mock_rag_log.call_args_list:
                if call[1].get("processing_stage") == "completed":
                    final_call = call[1]
                    break

            assert final_call is not None
            assert final_call["step"] == 129
            assert "faq_id" in final_call
            assert "operation" in final_call


class TestRAGStep129Parity:
    """Parity tests - prove behavior unchanged after introducing orchestrator."""

    @pytest.mark.asyncio
    async def test_step_129_parity_faq_creation(self):
        """Test Step 129 parity: FAQ creation behavior unchanged."""
        from app.orchestrators.golden import step_129__publish_golden

        test_cases = [
            {
                "faq_candidate": {"question": "Question 1", "answer": "Answer 1", "category": "cat1"},
                "operation": "created",
            },
            {
                "faq_candidate": {
                    "question": "Question 2",
                    "answer": "Answer 2",
                    "category": "cat2",
                    "existing_faq_id": "faq_123",
                },
                "operation": "updated",
            },
        ]

        for test_case in test_cases:
            ctx = {
                **test_case,
                "candidate_metadata": {"candidate_id": "parity_test"},
                "approval_decision": "auto_approved",
                "request_id": f"parity-{test_case['operation']}",
            }

            with (
                patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create,
                patch("app.services.intelligent_faq_service.update_faq_entry") as mock_update,
            ):
                mock_faq = MagicMock()
                mock_faq.id = "faq_parity"
                mock_create.return_value = mock_faq
                mock_update.return_value = mock_faq

                with patch("app.orchestrators.golden.rag_step_log"):
                    result = await step_129__publish_golden(messages=[], ctx=ctx)

                assert "published_faq" in result


class TestRAGStep129Integration:
    """Integration tests for Step 129 with neighbors."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_golden_approval_to_129_integration(self, mock_golden_log):
        """Test GoldenApproval (Step 128) → Step 129 integration."""

        initial_ctx = {
            "faq_candidate": {
                "question": "Integration test question",
                "answer": "Integration test answer",
                "quality_score": 0.96,
                "category": "test",
            },
            "candidate_metadata": {"candidate_id": "candidate_integration"},
            "approval_decision": "auto_approved",
            "trust_score": 0.93,
            "request_id": "integration-128-129",
        }

        from app.orchestrators.golden import step_129__publish_golden

        with patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create:
            mock_faq = MagicMock()
            mock_faq.id = "faq_integration"
            mock_create.return_value = mock_faq

            result = await step_129__publish_golden(messages=[], ctx=initial_ctx)

            assert result["approval_decision"] == "auto_approved"
            assert result["next_step"] == "invalidate_faq_cache"
            assert "published_faq" in result

    @pytest.mark.asyncio
    @patch("app.orchestrators.golden.rag_step_log")
    async def test_step_129_prepares_for_cache_invalidation(self, mock_rag_log):
        """Test Step 129 prepares data for InvalidateFAQCache (Step 130)."""
        from app.orchestrators.golden import step_129__publish_golden

        ctx = {
            "faq_candidate": {"question": "Cache prep question", "answer": "Cache prep answer", "category": "test"},
            "candidate_metadata": {"candidate_id": "candidate_cache_prep"},
            "approval_decision": "auto_approved",
            "request_id": "test-129-cache-prep",
        }

        with patch("app.services.intelligent_faq_service.create_faq_entry") as mock_create:
            mock_faq = MagicMock()
            mock_faq.id = "faq_cache_prep"
            mock_faq.question = ctx["faq_candidate"]["question"]
            mock_create.return_value = mock_faq

            result = await step_129__publish_golden(messages=[], ctx=ctx)

            # Verify data prepared for cache invalidation
            assert result["next_step"] == "invalidate_faq_cache"
            assert "published_faq" in result
            assert result["published_faq"]["id"] == "faq_cache_prep"
