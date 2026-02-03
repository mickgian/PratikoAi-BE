"""TDD Tests for tree_of_thoughts.md Prompt Template.

DEV-223: Create tree_of_thoughts.md Prompt Template.
DEV-251: Updated for free-form responses (no JSON output required).
DEV-251 Part 3.2: Updated for structural completeness_section variable.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 90%+ for new code.
"""

from pathlib import Path

import pytest

from app.services.llm_orchestrator import COMPLETENESS_SECTION_FULL
from app.services.prompt_loader import PromptLoader

# Path to the actual prompts directory
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "app" / "prompts"


@pytest.fixture
def loader():
    """Create a PromptLoader instance with actual prompts directory."""
    return PromptLoader(prompts_dir=PROMPTS_DIR)


# =============================================================================
# Tests: Prompt Loading
# =============================================================================


class TestPromptLoadsViaLoader:
    """Test that the prompt loads correctly via PromptLoader."""

    def test_prompt_loads_without_error(self, loader):
        """tree_of_thoughts.md should load without errors."""
        content = loader.load(
            "tree_of_thoughts",
            query="Come fatturare consulenza a azienda tedesca?",
            kb_context="Contesto normativo sulla fatturazione internazionale...",
            kb_sources="Art. 7-ter DPR 633/72, Direttiva UE 2006/112/CE",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert content is not None
        assert len(content) > 0

    def test_prompt_exists_in_v1_directory(self):
        """Prompt file should exist in app/prompts/v1/."""
        prompt_path = PROMPTS_DIR / "v1" / "tree_of_thoughts.md"
        assert prompt_path.exists(), f"Prompt file not found at {prompt_path}"

    def test_prompt_is_markdown_file(self):
        """Prompt should be a .md file."""
        prompt_path = PROMPTS_DIR / "v1" / "tree_of_thoughts.md"
        assert prompt_path.suffix == ".md"


# =============================================================================
# Tests: Template Variables
# =============================================================================


class TestPromptVariablesSubstitute:
    """Test that all template variables work correctly."""

    def test_query_substitutes(self, loader):
        """query variable should substitute correctly."""
        test_query = "Come fatturare consulenza a azienda tedesca?"
        content = loader.load(
            "tree_of_thoughts",
            query=test_query,
            kb_context="Contesto normativo...",
            kb_sources="Art. 7-ter DPR 633/72",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert test_query in content

    def test_kb_context_substitutes(self, loader):
        """kb_context variable should substitute correctly."""
        test_context = "Contesto normativo sulla fatturazione verso paesi UE e extra-UE."
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context=test_context,
            kb_sources="Art. 7-ter DPR 633/72",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert test_context in content

    def test_kb_sources_substitutes(self, loader):
        """kb_sources variable should substitute correctly."""
        test_sources = "Art. 7-ter DPR 633/72, Circolare AdE 12/E/2024"
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources=test_sources,
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert test_sources in content

    def test_domains_substitutes(self, loader):
        """domains variable should substitute correctly."""
        test_domains = "fiscale, lavoro"
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains=test_domains,
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert test_domains in content

    def test_conversation_context_substitutes(self, loader):
        """DEV-251: conversation_context variable should substitute correctly."""
        test_context = "Conversazione precedente sulla rottamazione quinquies..."
        content = loader.load(
            "tree_of_thoughts",
            query="E l'IMU?",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context=test_context,
            is_followup_mode="",
            completeness_section="",
        )
        assert test_context in content

    def test_missing_variable_raises_error(self, loader):
        """Missing required variable should raise KeyError."""
        with pytest.raises(KeyError):
            loader.load(
                "tree_of_thoughts",
                query="Test query",
                # Missing: kb_context, kb_sources, domains, conversation_context
            )


# =============================================================================
# Tests: Free-Form Output (DEV-251)
# =============================================================================


class TestFreeFormOutput:
    """Test that the prompt specifies free-form output (not JSON)."""

    def test_prompt_does_not_require_json_output(self, loader):
        """DEV-251: Prompt should NOT require JSON output format."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should NOT have mandatory JSON output section
        assert "Output (JSON OBBLIGATORIO)" not in content
        assert "Rispondi SEMPRE con questo schema JSON" not in content

    def test_prompt_specifies_professional_document_format(self, loader):
        """Prompt should specify writing as a professional document."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "documento professionale" in content.lower()

    def test_prompt_specifies_prose_style(self, loader):
        """Prompt should specify using fluid prose."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "prosa fluida" in content.lower()


# =============================================================================
# Tests: Hypothesis Generation (Internal Process)
# =============================================================================


class TestHypothesisGeneration:
    """Test that the prompt specifies hypothesis generation as internal process."""

    def test_prompt_mentions_hypothesis_generation(self, loader):
        """Prompt should mention hypothesis generation."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "ipotesi" in content.lower()

    def test_prompt_specifies_3_to_4_hypotheses(self, loader):
        """Prompt should specify generating 3-4 hypotheses."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should mention 3-4 or related
        has_count = (
            "3-4" in content
            or "3 a 4" in content
            or "tre" in content.lower()
            or "quattro" in content.lower()
            or "almeno 3" in content.lower()
        )
        assert has_count, "Prompt should specify 3-4 hypotheses"

    def test_reasoning_is_internal_not_in_output(self, loader):
        """DEV-251: Reasoning process should be internal, not in output."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should mention that reasoning is internal/mental
        assert "mentalmente" in content.lower() or "interno" in content.lower()


# =============================================================================
# Tests: Source-Weighted Evaluation
# =============================================================================


class TestSourceWeightedEvaluation:
    """Test that the prompt specifies source-weighted evaluation."""

    def test_prompt_mentions_source_evaluation(self, loader):
        """Prompt should mention source-based evaluation."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "fonte" in content.lower() or "source" in content.lower()

    def test_prompt_mentions_legal_hierarchy(self, loader):
        """Prompt should mention Italian legal hierarchy for source weighting."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should mention hierarchy concepts
        hierarchy_terms = ["gerarchia", "hierarchy", "legge", "decreto", "circolare"]
        matches = sum(1 for term in hierarchy_terms if term in content.lower())
        assert matches >= 2, "Should mention legal source hierarchy"


# =============================================================================
# Tests: COMPLETEZZA OBBLIGATORIA (DEV-251)
# =============================================================================


class TestCompletenessRequirements:
    """Test that the prompt specifies completeness requirements.

    DEV-251 Part 3.2: These tests verify completeness rules when the
    completeness_section variable contains the full requirements (new questions).
    For follow-up questions, completeness_section is empty.
    """

    def test_prompt_has_completezza_section_when_passed(self, loader):
        """DEV-251 Part 3.2: Prompt should have COMPLETEZZA section when variable contains it."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section=COMPLETENESS_SECTION_FULL,
        )
        assert "COMPLETEZZA OBBLIGATORIA" in content

    def test_prompt_no_completezza_section_when_followup(self, loader):
        """DEV-251 Part 3.2: Follow-up mode should NOT include completeness section."""
        content = loader.load(
            "tree_of_thoughts",
            query="E l'IMU?",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="Conversazione precedente...",
            is_followup_mode="MODALITÀ FOLLOW-UP ATTIVA",
            completeness_section="",  # Empty for follow-ups
        )
        # When completeness_section is empty, COMPLETEZZA should NOT appear
        assert "COMPLETEZZA OBBLIGATORIA" not in content

    def test_prompt_requires_scadenze(self, loader):
        """Prompt should require including deadlines/dates."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section=COMPLETENESS_SECTION_FULL,
        )
        assert "scadenze" in content.lower()

    def test_prompt_requires_importi(self, loader):
        """Prompt should require including amounts/rates."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section=COMPLETENESS_SECTION_FULL,
        )
        assert "importi" in content.lower() or "aliquote" in content.lower()

    def test_prompt_requires_requisiti(self, loader):
        """Prompt should require including requirements."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section=COMPLETENESS_SECTION_FULL,
        )
        assert "requisiti" in content.lower()

    def test_prompt_requires_esclusioni(self, loader):
        """Prompt should require including exclusions."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section=COMPLETENESS_SECTION_FULL,
        )
        assert "esclusioni" in content.lower()

    def test_prompt_requires_conseguenze(self, loader):
        """Prompt should require including consequences."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section=COMPLETENESS_SECTION_FULL,
        )
        assert "conseguenze" in content.lower()

    def test_prompt_requires_procedure(self, loader):
        """Prompt should require including procedures."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section=COMPLETENESS_SECTION_FULL,
        )
        assert "procedure" in content.lower()

    def test_prompt_says_not_to_summarize(self, loader):
        """Prompt should explicitly say not to summarize."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section=COMPLETENESS_SECTION_FULL,
        )
        assert "non riassumere" in content.lower()


# =============================================================================
# Tests: Italian Professional Language
# =============================================================================


class TestItalianProfessionalLanguage:
    """Test that the prompt uses Italian professional language."""

    def test_prompt_is_in_italian(self, loader):
        """Prompt should be primarily in Italian."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Check for common Italian words
        italian_keywords = ["analizza", "ipotesi", "risposta", "fonti", "valuta"]
        matches = sum(1 for kw in italian_keywords if kw in content.lower())
        assert matches >= 3, "Prompt should contain Italian language"

    def test_prompt_mentions_italian_legal_context(self, loader):
        """Prompt should mention Italian legal/fiscal context."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        italian_legal_terms = ["italiana", "italian", "dpr", "d.lgs", "legge"]
        matches = sum(1 for term in italian_legal_terms if term in content.lower())
        assert matches >= 1, "Should mention Italian legal context"

    def test_prompt_has_professional_tone(self, loader):
        """Prompt should have professional tone."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should use formal language
        professional_indicators = ["professionale", "esperto", "consulente", "analisi"]
        matches = sum(1 for term in professional_indicators if term in content.lower())
        assert matches >= 1, "Should have professional tone"


# =============================================================================
# Tests: Anti-Hallucination Rules
# =============================================================================


class TestAntiHallucinationRules:
    """Test that the prompt includes anti-hallucination rules."""

    def test_prompt_has_anti_hallucination_section(self, loader):
        """Prompt should have anti-hallucination rules."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "anti-allucinazione" in content.lower() or "mai inventare" in content.lower()

    def test_prompt_forbids_inventing_law_numbers(self, loader):
        """Prompt should forbid inventing law numbers."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "mai inventare" in content.lower() or "non inventare" in content.lower()

    def test_prompt_requires_kb_verification(self, loader):
        """Prompt should require verifying sources against KB."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "verifica" in content.lower()


# =============================================================================
# Tests: Inline Citations
# =============================================================================


class TestInlineCitations:
    """Test that the prompt specifies inline citation format."""

    def test_prompt_specifies_inline_citations(self, loader):
        """Prompt should specify citing sources inline."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "inline" in content.lower() or "nel testo" in content.lower()

    def test_prompt_provides_citation_examples(self, loader):
        """Prompt should provide citation format examples."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should have example like "Art. X, comma Y"
        assert "art." in content.lower() and "comma" in content.lower()

    def test_prompt_forbids_separate_sources_section(self, loader):
        """Prompt should forbid adding separate Sources section."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "non aggiungere" in content.lower() and "fonti" in content.lower()


# =============================================================================
# Tests: Conversation Context (DEV-251: Follow-up Handling)
# =============================================================================


class TestConversationContext:
    """Test that the prompt supports conversation context for follow-up questions."""

    def test_prompt_has_conversation_context_placeholder(self, loader):
        """DEV-251: Prompt should have conversation_context placeholder."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="Conversazione precedente...",
            is_followup_mode="",
            completeness_section="",
        )
        assert "Conversazione precedente..." in content

    def test_conversation_context_section_exists(self, loader):
        """Prompt should have a Contesto Conversazione section."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="Test context",
            is_followup_mode="",
            completeness_section="",
        )
        assert "Contesto Conversazione" in content or "contesto conversazione" in content.lower()

    def test_prompt_has_follow_up_handling_section(self, loader):
        """DEV-251: Prompt should have follow-up handling instructions."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "follow-up" in content.lower()

    def test_prompt_mentions_non_repetition_rule(self, loader):
        """DEV-251: Prompt should mention not repeating information."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        assert "non ripetere" in content.lower()

    def test_prompt_recognizes_follow_up_patterns(self, loader):
        """DEV-251: Prompt should recognize follow-up question patterns."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should mention patterns like "E l'IMU?", "E per l'IRAP?"
        assert "e l'" in content.lower() or "e per" in content.lower()

    def test_completeness_is_context_aware(self, loader):
        """DEV-251: Completeness rule should differ for new vs follow-up questions."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should mention different behavior for new questions vs follow-ups
        has_new_question_rule = "nuove" in content.lower() or "nuova" in content.lower()
        has_followup_rule = "follow-up" in content.lower()
        assert has_new_question_rule and has_followup_rule


# =============================================================================
# Tests: Unknown Term Handling (DEV-251 Part 2)
# =============================================================================


class TestUnknownTermHandling:
    """Test that the prompt includes unknown term handling rules to prevent hallucination."""

    def test_prompt_has_unknown_term_section(self, loader):
        """DEV-251: Prompt must have unknown term handling section."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Must have section for handling unknown/ambiguous terms
        assert "Gestione Termini Sconosciuti" in content or "termini sconosciuti" in content.lower()

    def test_prompt_forbids_inventing_meanings(self, loader):
        """DEV-251: Prompt must explicitly forbid inventing meanings for unknown terms."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Must have explicit "NON INVENTARE" instruction
        assert "non inventare" in content.lower()

    def test_prompt_has_typo_correction_guidance(self, loader):
        """DEV-251: Prompt must have typo correction guidance using context."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Must mention typo correction or error correction
        has_typo_section = (
            "Correzione Errori di Battitura" in content
            or "errore di battitura" in content.lower()
            or "errori di battitura" in content.lower()
        )
        assert has_typo_section

    def test_prompt_has_clarification_instruction(self, loader):
        """DEV-251: Prompt must instruct to ask for clarification on unknown terms."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should mention asking for clarification
        has_clarification = (
            "chiedi chiarimento" in content.lower()
            or "chiedere chiarimento" in content.lower()
            or "chiedi conferma" in content.lower()
        )
        assert has_clarification

    def test_prompt_has_confidence_threshold(self, loader):
        """DEV-251: Prompt should mention confidence threshold for typo correction."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should mention confidence threshold (80% or similar)
        has_confidence = "80%" in content or "sicuro" in content.lower() or "confidenza" in content.lower()
        assert has_confidence

    def test_prompt_has_typo_examples(self, loader):
        """DEV-251: Prompt should have examples of common typos."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should have at least one example like "rap" → "IRAP"
        has_examples = "rap" in content.lower() or "irap" in content.lower() or "imu" in content.lower()
        assert has_examples

    def test_prompt_has_assumo_tu_intenda_pattern(self, loader):
        """DEV-251: Prompt should show "Assumo tu intenda" pattern for typo correction."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should have the "Assumo tu intenda" pattern
        has_pattern = "assumo tu intenda" in content.lower() or "assumo intenda" in content.lower()
        assert has_pattern

    def test_prompt_handles_truly_unknown_terms(self, loader):
        """DEV-251: Prompt should have guidance for truly unknown terms (not typos)."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
            conversation_context="",
            is_followup_mode="",
            completeness_section="",
        )
        # Should mention handling of truly unknown terms (like "XYZ")
        has_unknown_handling = "non riconosco" in content.lower() or "sconosciuto" in content.lower()
        assert has_unknown_handling
