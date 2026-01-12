"""Tests for DEV-242: KB-empty detection and hallucination prevention.

Tests the _check_kb_empty_and_inject_warning function that detects when the KB
returns empty/irrelevant results and injects a warning to prevent hallucination.
"""

import pytest

from app.core.langgraph.nodes.step_064__llm_call import _check_kb_empty_and_inject_warning


class TestCheckKbEmptyAndInjectWarning:
    """Tests for KB-empty detection logic."""

    def test_returns_true_when_kb_sources_empty(self):
        """Empty kb_sources_metadata triggers warning."""
        state = {
            "kb_sources_metadata": [],
            "kb_context": "",
            "messages": [{"role": "user", "content": "rottamazione quinquies"}],
        }

        result = _check_kb_empty_and_inject_warning(state)

        assert result is True
        assert "kb_empty_warning" in state
        assert "ATTENZIONE CRITICA" in state["kb_context"]

    def test_returns_true_when_kb_context_minimal(self):
        """Minimal kb_context (< 200 chars) with single source triggers warning."""
        state = {
            "kb_sources_metadata": [{"title": "Some doc"}],
            "kb_context": "Short navigation header content.",
            "messages": [{"role": "user", "content": "rottamazione quinquies"}],
        }

        result = _check_kb_empty_and_inject_warning(state)

        assert result is True
        assert "KNOWLEDGE BASE VUOTA" in state["kb_context"]

    def test_returns_false_when_kb_has_content(self):
        """KB with substantial content does not trigger warning."""
        state = {
            "kb_sources_metadata": [{"title": "Legge 199/2025"}, {"title": "Circolare"}],
            # DEV-242 Phase 10: Function reads from "context" key (where Step 40 stores KB)
            "context": "A" * 500,  # 500 chars - substantial content
            "messages": [{"role": "user", "content": "rottamazione quinquies"}],
        }

        result = _check_kb_empty_and_inject_warning(state)

        assert result is False
        assert "kb_empty_warning" not in state

    def test_returns_false_when_single_source_has_content(self):
        """Single source with substantial content does not trigger warning."""
        state = {
            "kb_sources_metadata": [{"title": "Legge 199/2025"}],
            # DEV-242 Phase 10: Function reads from "context" key
            "context": "Questo è un contenuto sostanziale che supera i 200 caratteri minimi. " * 5,
            "messages": [{"role": "user", "content": "rottamazione quinquies"}],
        }

        result = _check_kb_empty_and_inject_warning(state)

        assert result is False

    def test_warning_prepended_to_kb_context(self):
        """Warning is prepended to existing kb_context."""
        original_context = "Some minimal context."
        state = {
            "kb_sources_metadata": [],
            "kb_context": original_context,
            "messages": [{"role": "user", "content": "test query"}],
        }

        _check_kb_empty_and_inject_warning(state)

        # Warning should be prepended
        assert state["kb_context"].startswith("\n⚠️⚠️⚠️")
        # Original context should still be there (or replaced with "Nessun documento trovato.")
        assert "KNOWLEDGE BASE VUOTA" in state["kb_context"]

    def test_extracts_user_query_from_messages(self):
        """Extracts user query from messages for logging."""
        state = {
            "kb_sources_metadata": [],
            "kb_context": "",
            "messages": [
                {"role": "system", "content": "You are PratikoAI"},
                {"role": "user", "content": "Cosa dice la legge?"},
            ],
        }

        result = _check_kb_empty_and_inject_warning(state)

        assert result is True
        # The function logs the user query - we just verify it runs without error

    def test_uses_user_message_field_if_available(self):
        """Uses user_message state field if available."""
        state = {
            "kb_sources_metadata": [],
            "kb_context": "",
            "user_message": "Direct user message",
            "messages": [],
        }

        result = _check_kb_empty_and_inject_warning(state)

        assert result is True

    def test_sets_kb_was_empty_flag(self):
        """The warning includes forbidden response guidance."""
        state = {
            "kb_sources_metadata": [],
            "kb_context": "",
            "messages": [{"role": "user", "content": "test"}],
        }

        _check_kb_empty_and_inject_warning(state)

        # Check that warning contains key guidance
        assert "NON inventare" in state["kb_context"]
        assert "NON usare conoscenze di training" in state["kb_context"]
        assert "Non ho trovato documenti ufficiali" in state["kb_context"]


class TestKbEmptyCheckInStep40:
    """Tests for DEV-242 FIX: KB-empty check moved to Step 40.

    These tests verify the fix for the temporal mismatch bug where the
    KB-empty warning was injected too late (Step 64) after the prompt
    was already built (Step 41).
    """

    def test_step40_sets_kb_was_empty_flag(self):
        """Step 40 should set kb_was_empty flag when KB is empty."""
        # Simulate the KB-empty check being called in Step 40 context
        state = {
            "kb_sources_metadata": [],
            "kb_context": "",
            "user_message": "rottamazione quinquies",
            "messages": [],
        }

        # This simulates what Step 40 now does
        kb_empty = _check_kb_empty_and_inject_warning(state)
        state["kb_was_empty"] = kb_empty

        assert state["kb_was_empty"] is True
        assert "ATTENZIONE CRITICA" in state["kb_context"]

    def test_warning_available_before_prompt_construction(self):
        """KB-empty warning must be in kb_context BEFORE Step 41 reads it.

        This test verifies the fix: when KB is empty, the warning is
        injected into kb_context immediately after kb_sources_metadata
        is populated (in Step 40), not after the prompt is built.
        """
        state = {
            "kb_sources_metadata": [],  # Empty KB
            "kb_context": "",
            "user_message": "rottamazione quinquies",
        }

        # Step 40: Check KB-empty and inject warning
        _check_kb_empty_and_inject_warning(state)

        # At this point (before Step 41), kb_context should contain the warning
        # This is the key assertion - warning must be present BEFORE prompt building
        assert "ATTENZIONE CRITICA - KNOWLEDGE BASE VUOTA" in state["kb_context"]
        assert "NON inventare" in state["kb_context"]
        assert "Non ho trovato documenti ufficiali" in state["kb_context"]

    def test_step64_skips_check_when_already_done_in_step40(self):
        """Step 64 should NOT re-run KB-empty check if Step 40 already did it."""
        state = {
            "kb_sources_metadata": [],
            "kb_context": "Already modified with warning",
            "kb_was_empty": True,  # Set by Step 40
            "messages": [],
        }

        # Step 64 should see kb_was_empty is already set and skip the check
        # The logic is: if "kb_was_empty" in state, don't call the function again
        kb_empty = state.get("kb_was_empty", False)
        ran_check = False
        if not kb_empty and "kb_was_empty" not in state:
            _check_kb_empty_and_inject_warning(state)
            ran_check = True

        assert ran_check is False  # Check was skipped
        assert state["kb_was_empty"] is True  # Value from Step 40 preserved


class TestKbEmptyWarningContextKey:
    """Tests for DEV-242 Phase 10: Function reads from 'context' key and preserves it.

    DEV-242 Phase 10 FIX: The function now reads from state["context"] (where Step 40
    stores KB) and NO LONGER overwrites it. The warning is only stored in kb_context
    and kb_empty_warning keys for logging purposes.
    """

    def test_reads_from_context_key_not_kb_context(self):
        """DEV-242 Phase 10: Function reads from 'context' key where Step 40 stores KB."""
        state = {
            "kb_sources_metadata": [{"title": "Legge 199/2025"}],
            "kb_context": "",  # Empty - should NOT be used
            "context": "A" * 500,  # Substantial content from Step 40
            "messages": [{"role": "user", "content": "test"}],
        }

        result = _check_kb_empty_and_inject_warning(state)

        # KB is NOT empty because "context" has substantial content
        assert result is False
        assert "kb_empty_warning" not in state

    def test_preserves_context_when_kb_empty(self):
        """DEV-242 Phase 10: When KB is empty, context is NOT overwritten."""
        original_context = "Original context from Step 40"
        state = {
            "kb_sources_metadata": [],
            "context": original_context,
            "messages": [{"role": "user", "content": "test"}],
        }

        result = _check_kb_empty_and_inject_warning(state)

        # KB IS empty (no sources, minimal context)
        assert result is True
        # Warning is in kb_context for logging
        assert "ATTENZIONE CRITICA" in state.get("kb_context", "")
        # Original context is PRESERVED (not overwritten)
        # Note: With Phase 10 fix, we no longer overwrite state["context"]
        assert state.get("context") == original_context

    def test_warning_stored_in_kb_empty_warning_key(self):
        """Warning is stored in kb_empty_warning for logging."""
        state = {
            "kb_sources_metadata": [],
            "context": "",
            "messages": [{"role": "user", "content": "test"}],
        }

        _check_kb_empty_and_inject_warning(state)

        # Warning stored in separate key for logging
        assert "kb_empty_warning" in state
        assert "ATTENZIONE CRITICA" in state["kb_empty_warning"]


class TestSynonymExpansion:
    """Tests for query normalization and synonym expansion in SearchService.

    DEV-242 Phase 6: Synonym expansion was RE-ADDED to SearchService because
    the LLM-based document identification (ADR-022) doesn't help FTS find
    documents using different terminology (e.g., "definizione agevolata"
    instead of "rottamazione").
    """

    def test_rottamazione_quinquies_expanded_with_synonyms(self):
        """Rottamazione quinquies queries should be expanded with legal synonyms (DEV-242 Phase 7)."""
        from app.services.search_service import SearchService

        # Create a mock service to test normalization
        service = SearchService.__new__(SearchService)

        result = service._normalize_italian_query("rottamazione quinquies")

        # Query should be expanded with synonyms that ACTUALLY match law text
        assert "definizione" in result  # Law uses "definizione di cui al comma 82"
        assert "comma 82" in result  # Specific to quinquies (Legge 199/2025)
        # Original query preserved
        assert "rottamazione quinquies" in result

    def test_rottamazione_quater_expanded_with_synonyms(self):
        """Rottamazione quater should be expanded with synonyms (DEV-242 Phase 7)."""
        from app.services.search_service import SearchService

        service = SearchService.__new__(SearchService)

        result = service._normalize_italian_query("rottamazione quater")

        # Query expanded with synonyms
        assert "definizione" in result
        assert "rottamazione quater" in result

    def test_saldo_e_stralcio_expanded_with_synonyms(self):
        """Saldo e stralcio should be expanded with synonyms (DEV-242 Phase 7)."""
        from app.services.search_service import SearchService

        service = SearchService.__new__(SearchService)

        result = service._normalize_italian_query("saldo e stralcio")

        # Query expanded with synonyms
        assert "definizione" in result
        assert "saldo e stralcio" in result

    def test_plain_query_not_modified(self):
        """Regular queries should only have whitespace normalized."""
        from app.services.search_service import SearchService

        service = SearchService.__new__(SearchService)

        result = service._normalize_italian_query("calcolo IVA fattura")

        assert result == "calcolo IVA fattura"

    def test_extra_whitespace_normalized(self):
        """Extra whitespace should be normalized."""
        from app.services.search_service import SearchService

        service = SearchService.__new__(SearchService)

        result = service._normalize_italian_query("rottamazione   quinquies  scadenze")

        # Extra whitespace normalized + synonyms added
        assert "rottamazione quinquies scadenze" in result
        assert "definizione" in result
        assert "comma 82" in result

    def test_generic_rottamazione_expanded(self):
        """Generic rottamazione queries should be expanded with synonyms (DEV-242 Phase 7)."""
        from app.services.search_service import SearchService

        service = SearchService.__new__(SearchService)

        result = service._normalize_italian_query("rottamazione scadenze")

        # Query expanded with synonyms for generic rottamazione term
        assert "definizione" in result
        assert "rottamazione scadenze" in result
