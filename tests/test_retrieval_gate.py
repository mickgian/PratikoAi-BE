"""Unit tests for retrieval gate (S034a)."""

import pytest

from app.core.rag.retrieval_gate import GateDecision, retrieval_gate


class TestRetrievalGate:
    """Test suite for the retrieval pre-gate."""

    def test_basic_arithmetic_no_retrieval(self):
        """Test that simple arithmetic doesn't trigger retrieval."""
        query = "2+2"
        decision = retrieval_gate(query)

        assert decision.needs_retrieval is False
        assert any("basic_reasoning" in r for r in decision.reasons)

    def test_simple_definition_no_retrieval(self):
        """Test that simple definitions don't trigger retrieval (if not tax regime)."""
        query = "Cos'è un contratto?"
        decision = retrieval_gate(query)

        assert decision.needs_retrieval is False

    def test_ccnl_query_needs_retrieval(self):
        """Test that CCNL queries trigger retrieval."""
        query = "Quali sono i requisiti CCNL metalmeccanici 2024?"
        decision = retrieval_gate(query)

        assert decision.needs_retrieval is True
        assert len(decision.reasons) > 0
        # Should match CCNL pattern and year pattern
        assert any("2024" in str(r) or "CCNL" in str(r) for r in decision.reasons)

    def test_year_reference_needs_retrieval(self):
        """Test that queries with year references trigger retrieval."""
        query = "Quali sono le novità fiscali del 2025?"
        decision = retrieval_gate(query)

        assert decision.needs_retrieval is True

    def test_institution_reference_needs_retrieval(self):
        """Test that institutional references trigger retrieval."""
        queries = ["Come dice l'Agenzia Entrate sul tema?", "Circolare INPS numero 10", "Risoluzione MEF del 2024"]

        for query in queries:
            decision = retrieval_gate(query)
            assert decision.needs_retrieval is True, f"Failed for: {query}"

    def test_article_reference_needs_retrieval(self):
        """Test that article references trigger retrieval."""
        query = "Cosa dice l'art. 18 dello Statuto dei Lavoratori?"
        decision = retrieval_gate(query)

        assert decision.needs_retrieval is True

    def test_normativa_reference_needs_retrieval(self):
        """Test that normativa references trigger retrieval."""
        queries = ["Qual è la normativa applicabile?", "Secondo il decreto legislativo...", "La legge prevede che..."]

        for query in queries:
            decision = retrieval_gate(query)
            assert decision.needs_retrieval is True, f"Failed for: {query}"

    def test_empty_query(self):
        """Test handling of empty query."""
        decision = retrieval_gate("")

        assert decision.needs_retrieval is False
        assert "empty_query" in decision.reasons

    def test_none_query(self):
        """Test handling of None query."""
        decision = retrieval_gate(None)

        assert decision.needs_retrieval is False
        assert "empty_query" in decision.reasons

    def test_general_question_no_clear_signal(self):
        """Test that general questions without clear signals default to no retrieval."""
        query = "Come posso migliorare la mia situazione?"
        decision = retrieval_gate(query)

        assert decision.needs_retrieval is False
        assert "no_time_sensitive_hints" in decision.reasons

    def test_aggiornamento_trigger(self):
        """Test that 'aggiornamento' triggers retrieval."""
        query = "Ci sono aggiornamenti sulla deducibilità?"
        decision = retrieval_gate(query)

        assert decision.needs_retrieval is True

    def test_decorrenza_trigger(self):
        """Test that 'decorrenza' triggers retrieval."""
        query = "Quando è la decorrenza della nuova aliquota?"
        decision = retrieval_gate(query)

        assert decision.needs_retrieval is True

    def test_multiple_hints(self):
        """Test query with multiple time-sensitive hints."""
        query = "Quali sono gli aggiornamenti CCNL 2024 secondo l'Agenzia Entrate?"
        decision = retrieval_gate(query)

        assert decision.needs_retrieval is True
        # Should have multiple reasons
        assert len(decision.reasons) > 1

    def test_case_insensitive(self):
        """Test that pattern matching is case-insensitive."""
        queries = ["ccnl metalmeccanici", "CCNL METALMECCANICI", "Ccnl Metalmeccanici"]

        for query in queries:
            decision = retrieval_gate(query)
            assert decision.needs_retrieval is True, f"Failed for: {query}"
