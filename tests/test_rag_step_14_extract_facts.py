"""
Tests for RAG STEP 14 — AtomicFactsExtractor.extract Extract atomic facts (RAG.facts.atomicfactsextractor.extract.extract.atomic.facts)

This process step extracts atomic facts from Italian professional queries.
Identifies monetary amounts, dates, legal entities, professional categories, and geographic info.
"""

from unittest.mock import patch

import pytest


class TestRAGStep14ExtractFacts:
    """Test suite for RAG STEP 14 - Atomic facts extraction."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_extract_monetary_amounts(self, mock_rag_log):
        """Test Step 14: Extract Italian monetary amounts."""
        from app.orchestrators.facts import step_14__extract_facts

        ctx = {
            "user_message": "Quanto costa assumere un dipendente con RAL di €45.000 annui?",
            "request_id": "test-14-monetary",
        }

        result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Should extract atomic facts
        assert isinstance(result, dict)
        assert "atomic_facts" in result
        assert "fact_count" in result

        atomic_facts = result["atomic_facts"]
        assert atomic_facts.fact_count() > 0
        assert len(atomic_facts.monetary_amounts) > 0

        # Should find €45.000
        amounts = [amt.amount for amt in atomic_facts.monetary_amounts]
        assert 45000.0 in amounts

        # Verify structured logging
        assert mock_rag_log.call_count >= 2
        completed_logs = [
            call for call in mock_rag_log.call_args_list if call[1].get("processing_stage") == "completed"
        ]

        assert len(completed_logs) > 0
        completed_log = completed_logs[0][1]
        assert completed_log["step"] == 14
        assert completed_log["node_label"] == "ExtractFacts"
        assert "fact_count" in completed_log

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_extract_dates(self, mock_rag_log):
        """Test Step 14: Extract Italian dates and tax years."""
        from app.orchestrators.facts import step_14__extract_facts

        ctx = {"user_message": "Le scadenze per il 730 del 2024 sono il 30 settembre", "request_id": "test-14-dates"}

        result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Should extract date facts
        atomic_facts = result["atomic_facts"]
        assert len(atomic_facts.dates) > 0

        # Should find tax year 2024 or date references
        date_texts = [d.original_text for d in atomic_facts.dates]
        assert any("2024" in text or "30 settembre" in text.lower() for text in date_texts)

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_extract_legal_entities(self, mock_rag_log):
        """Test Step 14: Extract legal entities (CF, P.IVA, document types)."""
        from app.orchestrators.facts import step_14__extract_facts

        ctx = {
            "user_message": "La mia P.IVA è 12345678901 e devo emettere una fattura elettronica",
            "request_id": "test-14-legal",
        }

        result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Should extract legal entities
        atomic_facts = result["atomic_facts"]
        assert len(atomic_facts.legal_entities) > 0

        # Should find P.IVA or fattura references
        entity_types = [e.entity_type for e in atomic_facts.legal_entities]
        assert "partita_iva" in entity_types or "document_type" in entity_types

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_extract_professional_categories(self, mock_rag_log):
        """Test Step 14: Extract professional categories (CCNL, contract types)."""
        from app.orchestrators.facts import step_14__extract_facts

        ctx = {
            "user_message": "CCNL commercio per un dirigente a tempo indeterminato",
            "request_id": "test-14-professional",
        }

        result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Should extract professional categories
        atomic_facts = result["atomic_facts"]
        assert len(atomic_facts.professional_categories) > 0

        # Should find CCNL sector or contract type
        category_texts = [c.original_text for c in atomic_facts.professional_categories]
        assert any(
            "commercio" in text.lower() or "dirigente" in text.lower() or "indeterminato" in text.lower()
            for text in category_texts
        )

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_extract_geographic_info(self, mock_rag_log):
        """Test Step 14: Extract geographic information."""
        from app.orchestrators.facts import step_14__extract_facts

        ctx = {
            "user_message": "Agevolazioni per imprese in Lombardia, sede a Milano",
            "request_id": "test-14-geographic",
        }

        result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Should extract geographic info
        atomic_facts = result["atomic_facts"]
        assert len(atomic_facts.geographic_info) > 0

        # Should find Milan or Lombardy
        geo_texts = [g.original_text for g in atomic_facts.geographic_info]
        assert any("Milano" in text or "Lombardia" in text for text in geo_texts)

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_empty_query(self, mock_rag_log):
        """Test Step 14: Handle empty or null query gracefully."""
        from app.orchestrators.facts import step_14__extract_facts

        ctx = {"user_message": "", "request_id": "test-14-empty"}

        result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Should handle empty query
        atomic_facts = result["atomic_facts"]
        assert atomic_facts.is_empty()
        assert atomic_facts.fact_count() == 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_complex_query(self, mock_rag_log):
        """Test Step 14: Extract multiple fact types from complex query."""
        from app.orchestrators.facts import step_14__extract_facts

        ctx = {
            "user_message": "Dipendente CCNL metalmeccanici a Milano, RAL €35.000, contratto da gennaio 2024",
            "request_id": "test-14-complex",
        }

        result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Should extract multiple fact types
        atomic_facts = result["atomic_facts"]
        assert atomic_facts.fact_count() >= 3  # At least money, geo, and professional

        # Verify different types
        assert len(atomic_facts.monetary_amounts) > 0
        assert len(atomic_facts.geographic_info) > 0
        assert len(atomic_facts.professional_categories) > 0 or len(atomic_facts.dates) > 0

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_routes_to_canonicalize(self, mock_rag_log):
        """Test Step 14: Routes to Step 16 (CanonicalizeFacts)."""
        from app.orchestrators.facts import step_14__extract_facts

        ctx = {"user_message": "Stipendio di 2000 euro al mese", "request_id": "test-14-route"}

        result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Should route to Step 16
        assert result["next_step"] == "canonicalize_facts"


class TestRAGStep14Parity:
    """Parity tests proving Step 14 preserves existing extraction logic."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_parity_with_direct_call(self, mock_rag_log):
        """Test Step 14: Parity with direct AtomicFactsExtractor.extract() call."""
        from app.orchestrators.facts import step_14__extract_facts

        # DEV-178: AtomicFactsExtractor archived
        from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

        query = "CCNL commercio, stipendio €1.500, scadenza 31/12/2024"

        # Direct service call
        extractor = AtomicFactsExtractor()
        direct_result = extractor.extract(query)

        # Orchestrator call
        ctx = {"user_message": query, "request_id": "test-parity"}
        orch_result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Results should be identical
        assert orch_result["atomic_facts"].fact_count() == direct_result.fact_count()
        assert len(orch_result["atomic_facts"].monetary_amounts) == len(direct_result.monetary_amounts)
        assert len(orch_result["atomic_facts"].dates) == len(direct_result.dates)
        assert len(orch_result["atomic_facts"].legal_entities) == len(direct_result.legal_entities)
        assert len(orch_result["atomic_facts"].professional_categories) == len(direct_result.professional_categories)


class TestRAGStep14Integration:
    """Integration tests for Step 13 → Step 14 → Step 16 flow."""

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_13_to_14_integration(self, mock_facts_log):
        """Test Step 13 (MessageExists) → Step 14 (ExtractFacts) integration."""
        from app.orchestrators.facts import step_14__extract_facts

        # Simulate Step 13 output (user message extracted)
        step_13_output = {
            "user_message": "Quanto costa un dipendente con RAL €40.000?",
            "user_message_exists": True,
            "request_id": "test-integration-13-14",
            "next_step": "extract_facts",
        }

        # Step 14: Extract atomic facts from Step 13 output
        step_14_result = await step_14__extract_facts(messages=[], ctx=step_13_output)

        # Should extract facts successfully
        assert step_14_result["atomic_facts"].fact_count() > 0
        assert step_14_result["next_step"] == "canonicalize_facts"

        # Should preserve Step 13 context
        assert step_14_result["user_message_exists"] is True
        assert step_14_result["request_id"] == "test-integration-13-14"

    @pytest.mark.asyncio
    @patch("app.orchestrators.facts.rag_step_log")
    async def test_step_14_context_preservation(self, mock_rag_log):
        """Test Step 14: Preserves context for Step 16."""
        from app.orchestrators.facts import step_14__extract_facts

        ctx = {
            "user_message": "Dipendente €30.000 annui, Milano",
            "request_id": "test-14-context",
            "some_other_field": "preserved_value",
        }

        result = await step_14__extract_facts(messages=[], ctx=ctx)

        # Should preserve context fields
        assert result["request_id"] == "test-14-context"
        assert result["some_other_field"] == "preserved_value"

        # Should add new fields
        assert "atomic_facts" in result
        assert "fact_count" in result

        # Context ready for Step 16
        assert result["next_step"] == "canonicalize_facts"
