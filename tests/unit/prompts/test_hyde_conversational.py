"""TDD Tests for hyde_conversational.md Prompt Template (DEV-233).

Tests written BEFORE implementation following RED-GREEN-REFACTOR methodology.
Tests cover:
- Template loading via PromptLoader
- Variable substitution (conversation_history, current_query)
- Italian language content
- Pronoun resolution instructions
- Conversation context handling
"""

import pytest

# =============================================================================
# Template Loading Tests
# =============================================================================


class TestHydeConversationalTemplateLoading:
    """Tests for template loading via PromptLoader."""

    def test_template_exists_and_loads(self) -> None:
        """Test that hyde_conversational.md exists and loads successfully."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        # Should not raise FileNotFoundError
        prompts = loader.list_prompts()
        assert "hyde_conversational" in prompts

    def test_template_loads_without_error(self) -> None:
        """Test that template loads without syntax errors."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        # Should load with required variables
        content = loader.load(
            "hyde_conversational",
            conversation_history="Utente: Test\nAssistente: Response",
            current_query="Test query",
        )
        assert content is not None
        assert len(content) > 0

    def test_template_has_required_variables(self) -> None:
        """Test that template contains conversation_history and current_query placeholders."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()

        # Load raw template (without substitution)
        content = loader.load("hyde_conversational")

        # Template should contain the required variable placeholders
        assert "{conversation_history}" in content
        assert "{current_query}" in content


# =============================================================================
# Variable Substitution Tests
# =============================================================================


class TestVariableSubstitution:
    """Tests for variable substitution in the template."""

    def test_conversation_history_substitution(self) -> None:
        """Test that conversation_history is properly substituted."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        history = """Utente: Quanto costa l'IRPEF?
Assistente: L'IRPEF dipende dallo scaglione di reddito."""

        content = loader.load(
            "hyde_conversational",
            conversation_history=history,
            current_query="E per l'IVA?",
        )

        assert "Quanto costa l'IRPEF" in content
        assert "scaglione di reddito" in content

    def test_current_query_substitution(self) -> None:
        """Test that current_query is properly substituted."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        query = "Quali sono le aliquote IVA per i beni alimentari?"

        content = loader.load(
            "hyde_conversational",
            conversation_history="Nessun contesto",
            current_query=query,
        )

        assert "aliquote IVA per i beni alimentari" in content

    def test_empty_conversation_history_allowed(self) -> None:
        """Test that empty conversation history is handled gracefully."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()

        content = loader.load(
            "hyde_conversational",
            conversation_history="",
            current_query="Test query",
        )

        # Should still produce valid output
        assert content is not None
        assert "Test query" in content


# =============================================================================
# Italian Language Content Tests
# =============================================================================


class TestItalianContent:
    """Tests for Italian language content in the template."""

    def test_template_title_in_italian(self) -> None:
        """Test that template has Italian title."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(
            "hyde_conversational",
            conversation_history="Test",
            current_query="Test",
        )

        # Should contain Italian keywords
        assert "HyDE" in content or "Ipotetico" in content or "Documento" in content

    def test_template_instructions_in_italian(self) -> None:
        """Test that instructions are in Italian."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(
            "hyde_conversational",
            conversation_history="Test",
            current_query="Test",
        )

        # Should contain Italian instruction keywords
        italian_keywords = ["genera", "risposta", "query", "contesto", "conversazione"]
        content_lower = content.lower()

        found_keywords = [kw for kw in italian_keywords if kw in content_lower]
        assert len(found_keywords) >= 2, f"Expected Italian keywords, found: {found_keywords}"


# =============================================================================
# Pronoun Resolution Instructions Tests
# =============================================================================


class TestPronounResolutionInstructions:
    """Tests for pronoun resolution instructions in the template."""

    def test_template_mentions_pronoun_resolution(self) -> None:
        """Test that template instructs LLM to resolve pronouns."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(
            "hyde_conversational",
            conversation_history="Test",
            current_query="Test",
        )

        content_lower = content.lower()

        # Should mention pronouns or implicit references
        pronoun_related = [
            "pronomi",
            "riferimenti",
            "impliciti",
            "questo",
            "quello",
            "risolvi",
        ]

        found = [term for term in pronoun_related if term in content_lower]
        assert len(found) >= 1, f"Expected pronoun resolution instructions, found: {found}"

    def test_template_handles_followup_patterns(self) -> None:
        """Test that template mentions handling follow-up query patterns."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(
            "hyde_conversational",
            conversation_history="Test",
            current_query="Test",
        )

        content_lower = content.lower()

        # Should mention common follow-up patterns
        followup_patterns = ["e per", "e se", "invece", "anche"]

        found = [pattern for pattern in followup_patterns if pattern in content_lower]
        # At least one follow-up pattern should be mentioned
        assert len(found) >= 1 or "follow" in content_lower or "seguito" in content_lower


# =============================================================================
# Conversation Context Handling Tests
# =============================================================================


class TestConversationContextHandling:
    """Tests for conversation context handling in the template."""

    def test_template_has_conversation_section(self) -> None:
        """Test that template has a dedicated conversation context section."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(
            "hyde_conversational",
            conversation_history="Test history",
            current_query="Test query",
        )

        content_lower = content.lower()

        # Should have section for conversation
        context_keywords = ["contesto", "conversazione", "storia", "history"]
        found = [kw for kw in context_keywords if kw in content_lower]
        assert len(found) >= 1

    def test_template_has_query_section(self) -> None:
        """Test that template has a dedicated current query section."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(
            "hyde_conversational",
            conversation_history="Test history",
            current_query="Test query",
        )

        content_lower = content.lower()

        # Should have section for query
        query_keywords = ["query", "domanda", "richiesta", "corrente", "attuale"]
        found = [kw for kw in query_keywords if kw in content_lower]
        assert len(found) >= 1

    def test_template_instructs_document_generation(self) -> None:
        """Test that template instructs generation of hypothetical document."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(
            "hyde_conversational",
            conversation_history="Test",
            current_query="Test",
        )

        content_lower = content.lower()

        # Should mention generating hypothetical document
        generation_keywords = ["genera", "documento", "ipotetico", "risposta"]
        found = [kw for kw in generation_keywords if kw in content_lower]
        assert len(found) >= 2


# =============================================================================
# Output Format Tests
# =============================================================================


class TestOutputFormat:
    """Tests for output format instructions in the template."""

    def test_template_specifies_output_format(self) -> None:
        """Test that template has output format instructions."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(
            "hyde_conversational",
            conversation_history="Test",
            current_query="Test",
        )

        content_lower = content.lower()

        # Should have output/format section
        format_keywords = ["output", "formato", "risposta", "risultato"]
        found = [kw for kw in format_keywords if kw in content_lower]
        assert len(found) >= 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for hyde_conversational template."""

    def test_full_prompt_with_realistic_history(self) -> None:
        """Test template with realistic conversation history."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()

        history = """Utente: Come si calcola l'IRPEF per un lavoratore dipendente?
Assistente: L'IRPEF per i lavoratori dipendenti si calcola applicando le aliquote progressive agli scaglioni di reddito. Gli scaglioni 2024 sono: fino a 28.000 euro al 23%, da 28.000 a 50.000 euro al 35%, oltre 50.000 euro al 43%.

Utente: Ci sono detrazioni?
Assistente: Sì, esistono diverse detrazioni per lavoro dipendente che riducono l'imposta lorda. Le detrazioni variano in base al reddito complessivo."""

        query = "E per i pensionati?"

        content = loader.load(
            "hyde_conversational",
            conversation_history=history,
            current_query=query,
        )

        # History should be included
        assert "IRPEF" in content
        assert "scaglioni" in content or "reddito" in content

        # Query should be included
        assert "pensionati" in content

    def test_prompt_handles_ambiguous_followup(self) -> None:
        """Test template with ambiguous follow-up query."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()

        history = """Utente: Quali sono le scadenze per la dichiarazione IVA?
Assistente: La dichiarazione IVA annuale va presentata entro il 30 aprile dell'anno successivo."""

        query = "E questa invece?"  # Ambiguous - "this" refers to something

        content = loader.load(
            "hyde_conversational",
            conversation_history=history,
            current_query=query,
        )

        # Should include both context and query
        assert "IVA" in content
        assert "questa" in content.lower() or query in content

    def test_prompt_length_reasonable(self) -> None:
        """Test that generated prompt has reasonable length."""
        from app.services.prompt_loader import PromptLoader

        loader = PromptLoader()

        content = loader.load(
            "hyde_conversational",
            conversation_history="Short history",
            current_query="Short query",
        )

        # Should be substantial but not excessive (without the variable content)
        base_length = len(content) - len("Short history") - len("Short query")
        assert base_length > 200, "Template too short"
        assert base_length < 5000, "Template too long"
