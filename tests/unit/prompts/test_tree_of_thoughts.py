"""TDD Tests for Phase 9: tree_of_thoughts.md Prompt Template.

DEV-223: Create tree_of_thoughts.md Prompt Template.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 90%+ for new code.
"""

import json
import re
from pathlib import Path

import pytest

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
        )
        assert test_domains in content

    def test_missing_variable_raises_error(self, loader):
        """Missing required variable should raise KeyError."""
        with pytest.raises(KeyError):
            loader.load(
                "tree_of_thoughts",
                query="Test query",
                # Missing: kb_context, kb_sources, domains
            )


# =============================================================================
# Tests: JSON Schema
# =============================================================================


class TestPromptJsonSchemaValid:
    """Test that the prompt contains a valid JSON schema example."""

    def test_prompt_has_json_code_block(self, loader):
        """Prompt should contain a JSON code block."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        assert "```json" in content, "Prompt should contain JSON code block"

    def test_prompt_json_schema_is_parseable(self, loader):
        """The JSON schema example in the prompt should be valid JSON."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        # Extract JSON from code block
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        assert json_match is not None, "Could not find JSON code block"

        json_str = json_match.group(1)
        try:
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON schema in prompt is not valid: {e}")

    def test_prompt_json_has_hypotheses_field(self, loader):
        """JSON schema should have hypotheses field."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        assert json_match is not None

        parsed = json.loads(json_match.group(1))
        assert "hypotheses" in parsed, "JSON should have 'hypotheses' field"
        assert isinstance(parsed["hypotheses"], list), "hypotheses should be a list"

    def test_prompt_json_has_selected_hypothesis_field(self, loader):
        """JSON schema should have selected_hypothesis field."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "selected_hypothesis" in parsed, "JSON should have 'selected_hypothesis' field"

    def test_prompt_json_has_answer_field(self, loader):
        """JSON schema should have answer field."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "answer" in parsed, "JSON should have 'answer' field"

    def test_prompt_json_has_sources_cited_field(self, loader):
        """JSON schema should have sources_cited field."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "sources_cited" in parsed, "JSON should have 'sources_cited' field"

    def test_prompt_json_has_alternatives_field(self, loader):
        """JSON schema should have alternatives field for documenting other scenarios."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "alternatives" in parsed, "JSON should have 'alternatives' field"


# =============================================================================
# Tests: Hypothesis Generation
# =============================================================================


class TestHypothesisGeneration:
    """Test that the prompt specifies hypothesis generation requirements."""

    def test_prompt_mentions_hypothesis_generation(self, loader):
        """Prompt should mention hypothesis generation."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        assert "ipotesi" in content.lower() or "hypothesis" in content.lower()

    def test_prompt_specifies_3_to_4_hypotheses(self, loader):
        """Prompt should specify generating 3-4 hypotheses."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        # Should mention 3-4 or "tre" or "quattro"
        has_count = (
            "3-4" in content
            or "3 a 4" in content
            or "tre" in content.lower()
            or "quattro" in content.lower()
            or "almeno 3" in content.lower()
        )
        assert has_count, "Prompt should specify 3-4 hypotheses"

    def test_prompt_has_hypothesis_structure(self, loader):
        """Prompt should define hypothesis structure with id, description, etc."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        # Check for hypothesis structure elements
        structure_elements = ["id", "description", "scenario"]
        matches = sum(1 for el in structure_elements if el in content.lower())
        assert matches >= 2, "Should define hypothesis structure"


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
        )
        # Should mention hierarchy concepts
        hierarchy_terms = ["gerarchia", "hierarchy", "legge", "decreto", "circolare"]
        matches = sum(1 for term in hierarchy_terms if term in content.lower())
        assert matches >= 2, "Should mention legal source hierarchy"

    def test_prompt_has_evaluation_criteria(self, loader):
        """Prompt should have evaluation criteria for hypotheses."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        # Should mention evaluation concepts
        eval_terms = ["valuta", "evaluat", "score", "punteggio", "criteri"]
        matches = sum(1 for term in eval_terms if term in content.lower())
        assert matches >= 1, "Should have evaluation criteria"

    def test_prompt_json_hypothesis_has_score(self, loader):
        """Each hypothesis in JSON should have a score field."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        assert json_match is not None

        parsed = json.loads(json_match.group(1))
        hypotheses = parsed.get("hypotheses", [])
        if hypotheses:
            first_hypothesis = hypotheses[0]
            assert "score" in first_hypothesis or "confidence" in first_hypothesis, \
                "Hypothesis should have score or confidence field"


# =============================================================================
# Tests: Best Hypothesis Selection
# =============================================================================


class TestBestHypothesisSelection:
    """Test that the prompt specifies best hypothesis selection with reasoning."""

    def test_prompt_mentions_selection(self, loader):
        """Prompt should mention selecting the best hypothesis."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        selection_terms = ["selezion", "scegli", "select", "migliore", "best"]
        matches = sum(1 for term in selection_terms if term in content.lower())
        assert matches >= 1, "Should mention hypothesis selection"

    def test_prompt_requires_selection_reasoning(self, loader):
        """Prompt should require reasoning for the selection."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        reasoning_terms = ["ragionamento", "reasoning", "motivazione", "perché", "motivo"]
        matches = sum(1 for term in reasoning_terms if term in content.lower())
        assert matches >= 1, "Should require selection reasoning"

    def test_prompt_json_selected_hypothesis_has_reasoning(self, loader):
        """selected_hypothesis in JSON should have reasoning field."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        selected = parsed.get("selected_hypothesis", {})
        assert "reasoning" in selected or "id" in selected, \
            "selected_hypothesis should have reasoning or at least an id"


# =============================================================================
# Tests: Alternative Documentation
# =============================================================================


class TestAlternativeDocumentation:
    """Test that the prompt specifies documenting alternatives."""

    def test_prompt_mentions_alternatives(self, loader):
        """Prompt should mention documenting alternative scenarios."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        alt_terms = ["alternativ", "altri scenari", "other scenario"]
        matches = sum(1 for term in alt_terms if term in content.lower())
        assert matches >= 1, "Should mention alternatives"

    def test_prompt_json_alternatives_has_structure(self, loader):
        """alternatives field should have proper structure."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        alternatives = parsed.get("alternatives", [])
        assert isinstance(alternatives, list), "alternatives should be a list"


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
        )
        # Should use formal language
        professional_indicators = ["professionale", "esperto", "consulente", "analisi"]
        matches = sum(1 for term in professional_indicators if term in content.lower())
        assert matches >= 1, "Should have professional tone"


# =============================================================================
# Tests: Output Structure
# =============================================================================


class TestOutputStructure:
    """Test that the prompt specifies correct output structure."""

    def test_prompt_specifies_json_output(self, loader):
        """Prompt should specify JSON output format."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        assert "json" in content.lower()

    def test_prompt_json_has_suggested_actions(self, loader):
        """JSON schema should have suggested_actions field."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "suggested_actions" in parsed, "JSON should have 'suggested_actions' field"

    def test_prompt_json_has_confidence(self, loader):
        """JSON schema should have confidence field."""
        content = loader.load(
            "tree_of_thoughts",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        # Confidence might be at top level or in selected_hypothesis
        has_confidence = (
            "confidence" in parsed
            or "confidence" in parsed.get("selected_hypothesis", {})
        )
        assert has_confidence, "JSON should have 'confidence' field"
