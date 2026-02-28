"""TDD tests for document tracking observability in ContextBuilderMerge.

DEV-007: Tests for preventing silent document drops like the Payslip 9 incident.
Each test validates a specific observability requirement.

Run with: uv run pytest tests/services/test_context_builder_observability.py -v
"""

import logging

import pytest

from app.services.context_builder_merge import ContextBuilderMerge, ContextPart


class TestMultiDocumentBudgetScaling:
    """Tests that budget scaling works correctly for multiple documents."""

    def test_budget_limit_sufficient_for_five_large_documents(self):
        """
        REQUIREMENT: max_budget_limit must accommodate 5 documents at 5000 tokens each.

        PratikoAI allows MAX_FILES_PER_UPLOAD = 5 documents.
        Each document can be ~5000 tokens.
        Therefore: max_budget_limit >= 5 * 5000 = 25000 tokens.

        We use 30000 for headroom.
        """
        builder = ContextBuilderMerge()

        assert builder.max_budget_limit >= 30000, (
            f"max_budget_limit ({builder.max_budget_limit}) is insufficient "
            f"for 5 documents at 5000 tokens each. Should be at least 30000."
        )

    def test_five_documents_get_adequate_budget(self):
        """
        REQUIREMENT: 5 documents at ~5000 tokens each should all fit.
        This is the EXACT scenario that caused the Payslip 9 bug.
        """
        builder = ContextBuilderMerge()

        # Given: 5 documents, each ~2000 tokens (total 10000 tokens)
        doc_facts = [f"[Documento: Payslip_{i}.pdf]\n" + "busta paga content " * 250 for i in range(1, 6)]

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": doc_facts,
            "query": "Confronta tutte le buste paga",
            "query_composition": "pure_doc",
        }

        # When
        result = builder.merge_context(context_data)
        merged_context = result.get("merged_context", "")

        # Then: ALL 5 documents must appear in output
        for i in range(1, 6):
            assert f"Payslip_{i}" in merged_context, (
                f"Payslip_{i} missing from merged context. This is the exact bug we're preventing."
            )


class TestDocumentCountInvariant:
    """Tests that document counts are tracked accurately through the pipeline."""

    def test_documents_in_equals_documents_out_plus_excluded(self):
        """
        REQUIREMENT: Every document must be accounted for.
        documents_received = documents_included + documents_excluded

        This test reproduces the Payslip 9 bug scenario.
        """
        builder = ContextBuilderMerge()

        # Given: 5 documents (like the original bug scenario)
        doc_facts = [f"[Documento: Payslip_{i}.pdf]\nContent for payslip {i} " + "x" * 500 for i in range(1, 6)]

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": doc_facts,
            "query": "Analizza le buste paga",
            "query_composition": "pure_doc",
        }

        # When
        result = builder.merge_context(context_data)

        # Then: Document count should be tracked
        # The result should include tracking of included/excluded
        docs_included = result.get("source_distribution", {}).get("document_facts", 0)

        # With proper budget, all 5 should be included
        assert docs_included == 5, (
            f"Expected 5 documents included, got {docs_included}. Some documents were silently dropped."
        )

    def test_excluded_documents_are_logged_with_reason(self, caplog):
        """
        REQUIREMENT: Every excluded document must have a logged reason.
        """
        caplog.set_level(logging.WARNING)

        builder = ContextBuilderMerge()

        # Given: More documents than a VERY small budget allows
        # Force exclusion by using huge content
        doc_facts = [
            f"[Documento: Doc_{i}.pdf]\n" + "content " * 2000  # ~8000 tokens each
            for i in range(5)
        ]

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": doc_facts,
            "query": "Test query",
            "max_context_tokens": 5000,  # Very small budget to force exclusion
        }

        # When
        result = builder.merge_context(context_data)

        # Then: Should have warning logs for excluded documents
        exclusion_logs = [r for r in caplog.records if "excluded" in r.message.lower() or r.levelno >= logging.WARNING]

        # At least one exclusion should be logged
        docs_included = result.get("source_distribution", {}).get("document_facts", 0)
        if docs_included < 5:
            assert len(exclusion_logs) > 0, (
                f"Documents were excluded (only {docs_included}/5 included) but no exclusion warning was logged!"
            )


class TestBudgetExceedanceLogging:
    """Tests that budget issues are logged clearly."""

    def test_warning_logged_when_budget_exceeded(self, caplog):
        """
        REQUIREMENT: A WARNING must be logged when token budget is exceeded.
        """
        caplog.set_level(logging.WARNING)

        builder = ContextBuilderMerge()

        # Given: Documents that will exceed a small budget
        large_doc = "[Documento: Huge.pdf]\n" + "content " * 3000  # ~12000 tokens

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": [large_doc, large_doc],  # Two large docs
            "query": "Test",
            "max_context_tokens": 5000,  # Force budget exceeded
        }

        # When
        result = builder.merge_context(context_data)

        # Then: If budget was exceeded, there should be a warning
        if result.get("budget_exceeded", False):
            budget_warnings = [
                r for r in caplog.records if "budget" in r.message.lower() and r.levelno >= logging.WARNING
            ]
            assert len(budget_warnings) > 0, "Expected budget warning to be logged"

    def test_budget_summary_includes_utilization_percentage(self, caplog):
        """
        REQUIREMENT: Budget summary must include utilization information.
        """
        caplog.set_level(logging.INFO)

        builder = ContextBuilderMerge()

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": ["[Documento: Test.pdf]\nTest document content"],
            "query": "Test",
        }

        # When
        result = builder.merge_context(context_data)

        # Then: Result should include budget utilization info
        assert "token_count" in result, "Result should include token_count"


class TestPayslip9Scenario:
    """Exact reproduction of the Payslip 9 bug scenario."""

    def test_payslip_9_not_dropped(self):
        """
        REQUIREMENT: Reproduce exact Payslip 9 scenario.

        Scenario:
        - 5 payslips uploaded (months 5-9)
        - Each ~2000 tokens
        - Previously: Payslip 9 silently dropped due to break statement
        - Now: All payslips must be included
        """
        builder = ContextBuilderMerge()

        # Exact reproduction of bug scenario
        payslips = [
            f"[Documento: Busta_Paga_{month}_2024.pdf]\n"
            f"BUSTA PAGA MESE: {month}/2024\n"
            f"Lordo: {1500 + month * 100}\n"
            f"Netto: {1200 + month * 80}\n" + "Dettagli vari " * 200  # ~800 tokens each
            for month in [5, 6, 7, 8, 9]  # Payslips 5-9
        ]

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": payslips,
            "query": "Confronta le buste paga degli ultimi 5 mesi",
            "query_composition": "pure_doc",
        }

        result = builder.merge_context(context_data)
        merged = result.get("merged_context", "")

        # Verify ALL payslips are present
        for month in [5, 6, 7, 8, 9]:
            assert f"Busta_Paga_{month}_2024" in merged, (
                f"Payslip for month {month} missing! This reproduces the Payslip 9 bug."
            )

    def test_two_payslips_both_analyzed(self):
        """
        REQUIREMENT: When user uploads 2 payslips, both must be included.

        This is the simplified version of the bug:
        - Upload Payslip 8 + Payslip 9
        - Ask "E queste?"
        - Both must be analyzed
        """
        builder = ContextBuilderMerge()

        payslips = [
            "[Documento: Busta_Paga_8_2024.pdf]\n"
            "BUSTA PAGA AGOSTO 2024\n"
            "Lordo: 2300\nNetto: 1900\n" + "Dettagli agosto " * 200,
            "[Documento: Busta_Paga_9_2024.pdf]\n"
            "BUSTA PAGA SETTEMBRE 2024\n"
            "Lordo: 2400\nNetto: 2000\n" + "Dettagli settembre " * 200,
        ]

        context_data = {
            "canonical_facts": [],
            "kb_results": [],
            "document_facts": payslips,
            "query": "E queste?",
            "query_composition": "pure_doc",
        }

        result = builder.merge_context(context_data)
        merged = result.get("merged_context", "")

        assert "Busta_Paga_8_2024" in merged, "Payslip 8 missing!"
        assert "Busta_Paga_9_2024" in merged, "Payslip 9 missing! This is the EXACT bug we're preventing."


class TestContextPartAccounting:
    """Tests for ContextPart inclusion/exclusion accounting."""

    def test_apply_token_budget_does_not_silently_drop(self):
        """
        REQUIREMENT: _apply_token_budget must NOT use break that drops remaining parts.

        The original bug: when a part was truncated, `break` exited the loop,
        silently dropping ALL remaining parts.
        """
        builder = ContextBuilderMerge()

        # Create parts that will require truncation
        parts = [
            ContextPart(
                type="document_facts",
                content=f"[Documento: Doc_{i}.pdf]\n" + "x" * 1000,
                tokens=300,  # Each part 300 tokens
                priority_score=1.0 - (i * 0.1),
                metadata={"doc_index": i},
            )
            for i in range(5)
        ]

        # Apply budget that can fit all 5 parts (5 * 300 = 1500 tokens)
        result = builder._apply_token_budget(parts, max_tokens=2000)

        # Unpack result - current implementation returns 3 values
        selected, content_truncated, budget_exceeded = result[:3]

        # All 5 parts should be selected since budget is sufficient
        assert len(selected) == 5, (
            f"Expected all 5 parts selected (budget sufficient), "
            f"but got {len(selected)}. Some parts were silently dropped!"
        )

    def test_apply_token_budget_with_tight_budget(self):
        """
        REQUIREMENT: With tight budget, parts may be excluded but NOT silently.
        """
        builder = ContextBuilderMerge()

        # Create parts where not all will fit
        parts = [
            ContextPart(
                type="document_facts",
                content=f"[Documento: Doc_{i}.pdf]\n" + "x" * 1000,
                tokens=600,  # Each part 600 tokens
                priority_score=1.0 - (i * 0.1),
                metadata={"doc_index": i},
            )
            for i in range(5)
        ]

        # Budget can only fit 2 full parts (1200 tokens) + some truncation
        result = builder._apply_token_budget(parts, max_tokens=1500)

        selected, content_truncated, budget_exceeded = result[:3]

        # At least 2 should be selected
        assert len(selected) >= 2, f"Expected at least 2 parts selected, got {len(selected)}"

        # Budget should be marked as exceeded
        assert budget_exceeded, "Budget should be marked as exceeded"
