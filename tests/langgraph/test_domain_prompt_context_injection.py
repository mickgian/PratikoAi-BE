"""TDD Tests for Domain Prompt Context Injection.

DEV-007: Verify merged_context from Step 40 reaches LLM via domain prompt path.

ROOT CAUSE FIXED: In Step 41, the Domain Prompt path (high confidence) was
NOT passing ctx to step_43, so the "context" field with document content
was lost. Fix adds **(ctx or {}) and context injection after step_43 returns.

Written to prevent regression of the Payslip 9 ignored bug.
"""

from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class MockDomain(Enum):
    TAX = "tax"
    LABOR = "labor"


class MockAction(Enum):
    EXPLAIN_DOCUMENT = "explain_document"
    ANALYZE = "analyze"


class TestDomainPromptContextInjection:
    """Tests verifying merged_context is injected into domain prompt."""

    @pytest.mark.asyncio
    async def test_domain_prompt_path_receives_context(self):
        """CRITICAL: When classification confidence is high, context must still reach domain prompt.

        This is THE critical regression test for the Payslip 9 ignored bug.
        The bug was: Domain prompt path used explicit ctx dict WITHOUT **(ctx or {})
        """
        from app.orchestrators.prompting import step_41__select_prompt

        # Given: High-confidence classification that triggers Domain Prompt path
        mock_classification = MagicMock()
        mock_classification.confidence = 0.85  # Above 0.6 threshold
        mock_classification.domain = MockDomain.TAX
        mock_classification.action = MockAction.EXPLAIN_DOCUMENT

        # Mock prompt template manager
        mock_prompt_manager = MagicMock()
        mock_prompt_manager.has_template.return_value = True

        # Context from Step 40 with merged document content
        ctx_with_context = {
            "context": "PAYSLIP_8_CONTENT\nPAYSLIP_9_CONTENT",  # This is the merged_context
            "query_composition": "pure_doc",
            "classification": mock_classification,
            "prompt_template_manager": mock_prompt_manager,
            "user_query": "E queste?",
            "request_id": "test-123",
        }

        # Mock step_43 to capture what ctx it receives
        captured_ctx = {}

        async def mock_step_43(*, messages=None, ctx=None, **kwargs):
            captured_ctx.update(ctx or {})
            return {
                "prompt_generated": True,
                "domain_prompt": "You are a tax expert.",
            }

        with patch("app.orchestrators.classify.step_43__domain_prompt", mock_step_43):
            # When: Step 41 processes with high-confidence classification
            result = await step_41__select_prompt(
                messages=[{"role": "user", "content": "E queste?"}],
                ctx=ctx_with_context,
            )

        # Then: Step 43 must have received the "context" field
        assert "context" in captured_ctx, (
            "DEV-007 REGRESSION: Step 43 did not receive 'context' field! "
            "The domain prompt path must include **(ctx or {}) to preserve context."
        )
        assert "PAYSLIP_8_CONTENT" in captured_ctx["context"], "Payslip 8 content must be in context"
        assert "PAYSLIP_9_CONTENT" in captured_ctx["context"], "Payslip 9 content must be in context"

    @pytest.mark.asyncio
    async def test_domain_prompt_includes_context_section(self):
        """Domain prompt must include the context section with document content."""
        from app.orchestrators.prompting import step_41__select_prompt

        # Given: High-confidence classification
        mock_classification = MagicMock()
        mock_classification.confidence = 0.85
        mock_classification.domain = MockDomain.TAX
        mock_classification.action = MockAction.EXPLAIN_DOCUMENT

        mock_prompt_manager = MagicMock()
        mock_prompt_manager.has_template.return_value = True

        ctx_with_context = {
            "context": "DOCUMENT_CONTENT_UNIQUE_MARKER_12345",
            "query_composition": "pure_doc",
            "classification": mock_classification,
            "prompt_template_manager": mock_prompt_manager,
            "user_query": "E queste?",
            "request_id": "test-456",
        }

        async def mock_step_43(*, messages=None, ctx=None, **kwargs):
            return {
                "prompt_generated": True,
                "domain_prompt": "You are a tax expert. Analyze documents.",
            }

        with patch("app.orchestrators.classify.step_43__domain_prompt", mock_step_43):
            result = await step_41__select_prompt(
                messages=[{"role": "user", "content": "E queste?"}],
                ctx=ctx_with_context,
            )

        # Then: The selected prompt must contain the document content
        selected_prompt = result.get("selected_prompt", "")
        assert "DOCUMENT_CONTENT_UNIQUE_MARKER_12345" in selected_prompt, (
            "DEV-007 REGRESSION: Document content not injected into domain prompt! "
            f"Got prompt: {selected_prompt[:200]}..."
        )

    @pytest.mark.asyncio
    async def test_default_path_also_includes_context(self):
        """Default prompt path (low confidence) must also include context."""
        from app.orchestrators.prompting import step_41__select_prompt

        # Given: Low-confidence classification that triggers Default path
        mock_classification = MagicMock()
        mock_classification.confidence = 0.3  # Below 0.6 threshold

        ctx_with_context = {
            "context": "DEFAULT_PATH_DOCUMENT_CONTENT",
            "query_composition": "pure_doc",
            "classification": mock_classification,
            "user_query": "Spiegami",
            "request_id": "test-789",
        }

        # When: Step 41 processes with low-confidence classification
        result = await step_41__select_prompt(
            messages=[{"role": "user", "content": "Spiegami"}],
            ctx=ctx_with_context,
        )

        # Then: The selected prompt must contain the document content
        selected_prompt = result.get("selected_prompt", "")
        assert "DEFAULT_PATH_DOCUMENT_CONTENT" in selected_prompt, (
            f"Default path should include context! Got prompt: {selected_prompt[:200]}..."
        )


class TestMultipleAttachmentsInDomainPrompt:
    """Regression tests for multiple attachments reaching domain prompt."""

    @pytest.mark.asyncio
    async def test_both_payslips_in_domain_prompt_context(self):
        """CRITICAL: Both Payslip 8 AND Payslip 9 must appear in domain prompt.

        This is the exact regression scenario from the user bug report.
        """
        from app.orchestrators.prompting import step_41__select_prompt

        # Given: Context with BOTH payslips (as merged by Step 40)
        mock_classification = MagicMock()
        mock_classification.confidence = 0.85
        mock_classification.domain = MockDomain.TAX
        mock_classification.action = MockAction.EXPLAIN_DOCUMENT

        mock_prompt_manager = MagicMock()
        mock_prompt_manager.has_template.return_value = True

        # This is what Step 40 would produce for two payslips
        merged_context = """DOCUMENTO ALLEGATO: Payslip 8 - Agosto 2025.pdf
UNIQUE_MARKER_PAYSLIP_8_AGOSTO
Periodo: 01/08/2025 - 31/08/2025

DOCUMENTO ALLEGATO: Payslip 9 - Settembre 2025.pdf
UNIQUE_MARKER_PAYSLIP_9_SETTEMBRE
Periodo: 01/09/2025 - 30/09/2025"""

        ctx_with_both_payslips = {
            "context": merged_context,
            "query_composition": "pure_doc",
            "classification": mock_classification,
            "prompt_template_manager": mock_prompt_manager,
            "user_query": "E queste?",
            "request_id": "test-regression",
        }

        async def mock_step_43(*, messages=None, ctx=None, **kwargs):
            return {
                "prompt_generated": True,
                "domain_prompt": "Sei un esperto fiscale italiano.",
            }

        with patch("app.orchestrators.classify.step_43__domain_prompt", mock_step_43):
            result = await step_41__select_prompt(
                messages=[{"role": "user", "content": "E queste?"}],
                ctx=ctx_with_both_payslips,
            )

        selected_prompt = result.get("selected_prompt", "")

        # BOTH payslips must be in the final prompt sent to LLM
        assert "UNIQUE_MARKER_PAYSLIP_8_AGOSTO" in selected_prompt, (
            f"Payslip 8 (August) must be in domain prompt! Got: {selected_prompt[:300]}..."
        )
        assert "UNIQUE_MARKER_PAYSLIP_9_SETTEMBRE" in selected_prompt, (
            "DEV-007 BUG: Payslip 9 (September) must be in domain prompt! "
            "This was the original bug - Payslip 9 was ignored. "
            f"Got: {selected_prompt[:300]}..."
        )
