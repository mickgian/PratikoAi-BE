"""
Tests for RAG STEP 16 — AtomicFactsExtractor.canonicalize Normalize dates amounts rates (RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates)

This process step validates and ensures that all atomic facts from Step 14 are properly canonicalized.
Verifies normalization of monetary amounts, dates, legal entities, and other extracted facts.
"""

from unittest.mock import patch

import pytest


class TestRAGStep16CanonicalizeFacts:
    """Test suite for RAG STEP 16 - Atomic facts canonicalization."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_validates_monetary_canonicalization(self, mock_rag_log):
        """Test Step 16: Validates monetary amounts are properly canonicalized."""
        from app.orchestrators.facts import step_16__canonicalize_facts
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare Step 14 output with Italian formatted amount
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("Stipendio di €45.000 annui")

        ctx = {"atomic_facts": atomic_facts, "fact_count": atomic_facts.fact_count(), "request_id": "test-16-monetary"}

        result = await step_16__canonicalize_facts(messages=[], ctx=ctx)

        # Should validate canonicalization successful
        assert "canonicalization_valid" in result
        assert result["canonicalization_valid"] is True

        # Should preserve atomic facts
        assert "atomic_facts" in result
        assert result["atomic_facts"] == atomic_facts

        # Should have canonical monetary amount (45000.0)
        assert len(result["atomic_facts"].monetary_amounts) > 0
        assert 45000.0 in [amt.amount for amt in result["atomic_facts"].monetary_amounts]

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 16
        assert completed_log["node_label"] == "CanonicalizeFacts"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_validates_date_canonicalization(self, mock_rag_log):
        """Test Step 16: Validates dates are in ISO format."""
        from app.orchestrators.facts import step_16__canonicalize_facts
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare Step 14 output with Italian date
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("Scadenza 31/12/2024")

        ctx = {"atomic_facts": atomic_facts, "fact_count": atomic_facts.fact_count(), "request_id": "test-16-dates"}

        result = await step_16__canonicalize_facts(messages=[], ctx=ctx)

        # Should validate date facts exist
        assert result["canonicalization_valid"] is True
        assert len(result["atomic_facts"].dates) > 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_validates_entity_canonicalization(self, mock_rag_log):
        """Test Step 16: Validates legal entities are canonicalized."""
        from app.orchestrators.facts import step_16__canonicalize_facts
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare Step 14 output with legal entity
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("P.IVA 12345678901 per SRL")

        ctx = {"atomic_facts": atomic_facts, "fact_count": atomic_facts.fact_count(), "request_id": "test-16-entities"}

        result = await step_16__canonicalize_facts(messages=[], ctx=ctx)

        # Should validate entity canonicalization
        assert result["canonicalization_valid"] is True
        assert len(result["atomic_facts"].legal_entities) > 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_handles_empty_facts(self, mock_rag_log):
        """Test Step 16: Handles empty atomic facts gracefully."""
        from app.orchestrators.facts import step_16__canonicalize_facts
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare Step 14 output with no extractable facts
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("")

        ctx = {"atomic_facts": atomic_facts, "fact_count": 0, "request_id": "test-16-empty"}

        result = await step_16__canonicalize_facts(messages=[], ctx=ctx)

        # Should handle empty facts
        assert result["canonicalization_valid"] is True
        assert result["atomic_facts"].is_empty()
        assert result["fact_count"] == 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_validates_multiple_fact_types(self, mock_rag_log):
        """Test Step 16: Validates multiple canonicalized fact types."""
        from app.orchestrators.facts import step_16__canonicalize_facts
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare Step 14 output with complex query
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract(
            "Dipendente CCNL metalmeccanici a Milano, RAL €35.000, contratto da 01/01/2024"
        )

        ctx = {"atomic_facts": atomic_facts, "fact_count": atomic_facts.fact_count(), "request_id": "test-16-multiple"}

        result = await step_16__canonicalize_facts(messages=[], ctx=ctx)

        # Should validate all fact types
        assert result["canonicalization_valid"] is True
        assert result["fact_count"] >= 3  # Money, dates, geo/professional

        # All canonical forms should be present
        facts = result["atomic_facts"]
        assert len(facts.monetary_amounts) > 0
        assert len(facts.geographic_info) > 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_italian_number_formats(self, mock_rag_log):
        """Test Step 16: Validates Italian number format canonicalization."""
        from app.orchestrators.facts import step_16__canonicalize_facts
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Test various Italian number formats
        test_cases = [
            ("€1.500,50", 1500.50),  # Italian format with thousands separator
            ("€2.000", 2000.0),  # Italian thousands separator
            ("€500,75", 500.75),  # Italian decimal separator
        ]

        for query_text, expected_amount in test_cases:
            extractor = AtomicFactsExtractor()
            atomic_facts = extractor.extract(query_text)

            ctx = {
                "atomic_facts": atomic_facts,
                "fact_count": atomic_facts.fact_count(),
                "request_id": f"test-16-format-{expected_amount}",
            }

            result = await step_16__canonicalize_facts(messages=[], ctx=ctx)

            # Should have canonical amount
            assert result["canonicalization_valid"] is True
            amounts = [amt.amount for amt in result["atomic_facts"].monetary_amounts]
            assert expected_amount in amounts, f"Expected {expected_amount} in {amounts} for query '{query_text}'"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_routes_to_attachment_fingerprint(self, mock_rag_log):
        """Test Step 16: Routes to Step 17 (AttachmentFingerprint)."""
        from app.orchestrators.facts import step_16__canonicalize_facts
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare Step 14 output
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("Fattura €1.000")

        ctx = {"atomic_facts": atomic_facts, "fact_count": atomic_facts.fact_count(), "request_id": "test-16-route"}

        result = await step_16__canonicalize_facts(messages=[], ctx=ctx)

        # Should route to Step 17
        assert result["next_step"] == "attachment_fingerprint"


class TestRAGStep16Parity:
    """Parity tests proving Step 16 preserves existing canonicalization logic."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_parity_no_changes_to_facts(self, mock_rag_log):
        """Test Step 16: Does not modify atomic facts (validation only)."""
        from app.orchestrators.facts import step_16__canonicalize_facts
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Extract facts
        query = "CCNL commercio, stipendio €1.500, scadenza 31/12/2024"
        extractor = AtomicFactsExtractor()
        original_facts = extractor.extract(query)

        # Run Step 16
        ctx = {"atomic_facts": original_facts, "fact_count": original_facts.fact_count(), "request_id": "test-parity"}
        result = await step_16__canonicalize_facts(messages=[], ctx=ctx)

        # Facts should be identical (no modification)
        assert result["atomic_facts"] == original_facts
        assert result["atomic_facts"].fact_count() == original_facts.fact_count()
        assert len(result["atomic_facts"].monetary_amounts) == len(original_facts.monetary_amounts)
        assert len(result["atomic_facts"].dates) == len(original_facts.dates)


class TestRAGStep16Integration:
    """Integration tests for Step 14 → Step 16 → Step 17 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_to_16_integration(self, mock_facts_log):
        """Test Step 14 (ExtractFacts) → Step 16 (CanonicalizeFacts) integration."""
        from app.orchestrators.facts import step_14__extract_facts, step_16__canonicalize_facts

        # Step 14: Extract facts
        step_14_input = {
            "user_message": "Quanto costa un dipendente con RAL €40.000?",
            "request_id": "test-integration-14-16",
        }

        step_14_result = await step_14__extract_facts(messages=[], ctx=step_14_input)

        # Step 16: Validate canonicalization
        step_16_result = await step_16__canonicalize_facts(messages=[], ctx=step_14_result)

        # Should flow correctly
        assert step_14_result["next_step"] == "canonicalize_facts"
        assert step_16_result["next_step"] == "attachment_fingerprint"

        # Should preserve facts and add validation
        assert step_16_result["atomic_facts"] == step_14_result["atomic_facts"]
        assert step_16_result["canonicalization_valid"] is True
        assert step_16_result["fact_count"] == step_14_result["fact_count"]

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_16_context_preservation(self, mock_rag_log):
        """Test Step 16: Preserves context for Step 17."""
        from app.orchestrators.facts import step_16__canonicalize_facts
        from app.services.atomic_facts_extractor import AtomicFactsExtractor

        # Prepare context with extra fields
        extractor = AtomicFactsExtractor()
        atomic_facts = extractor.extract("Dipendente €30.000 annui")

        ctx = {
            "atomic_facts": atomic_facts,
            "fact_count": atomic_facts.fact_count(),
            "request_id": "test-16-context",
            "user_message": "Dipendente €30.000 annui",
            "some_other_field": "preserved_value",
        }

        result = await step_16__canonicalize_facts(messages=[], ctx=ctx)

        # Should preserve context fields
        assert result["request_id"] == "test-16-context"
        assert result["user_message"] == "Dipendente €30.000 annui"
        assert result["some_other_field"] == "preserved_value"

        # Should add validation fields
        assert "canonicalization_valid" in result
        assert result["canonicalization_valid"] is True

        # Context ready for Step 17
        assert result["next_step"] == "attachment_fingerprint"
