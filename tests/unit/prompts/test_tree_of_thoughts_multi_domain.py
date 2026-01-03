"""TDD Tests for Phase 9: tree_of_thoughts_multi_domain.md Prompt Template.

DEV-224: Create tree_of_thoughts_multi_domain.md Prompt Template.

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
        """tree_of_thoughts_multi_domain.md should load without errors."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Assumo un dipendente che ha anche una partita IVA come freelancer",
            kb_context="Contesto normativo su lavoro dipendente e partita IVA...",
            kb_sources="Art. 2094 c.c., Art. 5 TUIR, Circolare INPS 45/2022",
            domains="fiscale, lavoro",
        )
        assert content is not None
        assert len(content) > 0

    def test_prompt_exists_in_v1_directory(self):
        """Prompt file should exist in app/prompts/v1/."""
        prompt_path = PROMPTS_DIR / "v1" / "tree_of_thoughts_multi_domain.md"
        assert prompt_path.exists(), f"Prompt file not found at {prompt_path}"

    def test_prompt_is_markdown_file(self):
        """Prompt should be a .md file."""
        prompt_path = PROMPTS_DIR / "v1" / "tree_of_thoughts_multi_domain.md"
        assert prompt_path.suffix == ".md"


# =============================================================================
# Tests: Template Variables
# =============================================================================


class TestPromptVariablesSubstitute:
    """Test that all template variables work correctly."""

    def test_query_substitutes(self, loader):
        """query variable should substitute correctly."""
        test_query = "Licenziamento e TFR con partita IVA parallela"
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query=test_query,
            kb_context="Contesto normativo...",
            kb_sources="Art. 2120 c.c.",
            domains="fiscale, lavoro",
        )
        assert test_query in content

    def test_kb_context_substitutes(self, loader):
        """kb_context variable should substitute correctly."""
        test_context = "Contesto normativo sulla cessazione del rapporto di lavoro."
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context=test_context,
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert test_context in content

    def test_kb_sources_substitutes(self, loader):
        """kb_sources variable should substitute correctly."""
        test_sources = "Art. 2120 c.c., Art. 17 TUIR, CCNL Commercio"
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources=test_sources,
            domains="fiscale, lavoro",
        )
        assert test_sources in content

    def test_domains_substitutes(self, loader):
        """domains variable should substitute correctly."""
        test_domains = "fiscale, lavoro, legale"
        content = loader.load(
            "tree_of_thoughts_multi_domain",
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
                "tree_of_thoughts_multi_domain",
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
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "```json" in content, "Prompt should contain JSON code block"

    def test_prompt_json_schema_is_parseable(self, loader):
        """The JSON schema example in the prompt should be valid JSON."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        assert json_match is not None, "Could not find JSON code block"

        json_str = json_match.group(1)
        try:
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON schema in prompt is not valid: {e}")

    def test_prompt_json_has_domain_analyses_field(self, loader):
        """JSON schema should have domain_analyses field for parallel analysis."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        assert json_match is not None

        parsed = json.loads(json_match.group(1))
        assert "domain_analyses" in parsed, "JSON should have 'domain_analyses' field"
        assert isinstance(parsed["domain_analyses"], list), "domain_analyses should be a list"

    def test_prompt_json_has_conflicts_field(self, loader):
        """JSON schema should have conflicts field."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "conflicts" in parsed, "JSON should have 'conflicts' field"

    def test_prompt_json_has_synthesis_field(self, loader):
        """JSON schema should have synthesis field for cross-domain answer."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "synthesis" in parsed, "JSON should have 'synthesis' field"

    def test_prompt_json_has_answer_field(self, loader):
        """JSON schema should have answer field."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "answer" in parsed, "JSON should have 'answer' field"


# =============================================================================
# Tests: Parallel Domain Analysis
# =============================================================================


class TestParallelDomainAnalysis:
    """Test that the prompt specifies parallel domain analysis."""

    def test_prompt_mentions_parallel_analysis(self, loader):
        """Prompt should mention parallel domain analysis."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        parallel_terms = ["parallel", "parallelo", "simultaneo", "ciascun dominio", "ogni dominio"]
        matches = sum(1 for term in parallel_terms if term in content.lower())
        assert matches >= 1, "Should mention parallel analysis"

    def test_prompt_mentions_multiple_domains(self, loader):
        """Prompt should mention handling multiple domains."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        domain_terms = ["domini", "domain", "fiscale", "lavoro", "legale"]
        matches = sum(1 for term in domain_terms if term in content.lower())
        assert matches >= 3, "Should mention multiple domains"

    def test_prompt_json_domain_analysis_has_domain_field(self, loader):
        """Each domain_analysis should have domain identifier."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        domain_analyses = parsed.get("domain_analyses", [])
        if domain_analyses:
            first_analysis = domain_analyses[0]
            assert "domain" in first_analysis, "Each analysis should have 'domain' field"

    def test_prompt_json_domain_analysis_has_hypotheses(self, loader):
        """Each domain_analysis should have hypotheses."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        domain_analyses = parsed.get("domain_analyses", [])
        if domain_analyses:
            first_analysis = domain_analyses[0]
            assert "hypotheses" in first_analysis or "conclusion" in first_analysis, \
                "Each analysis should have hypotheses or conclusion"


# =============================================================================
# Tests: Domain Conflict Identification
# =============================================================================


class TestDomainConflictIdentification:
    """Test that the prompt specifies conflict identification."""

    def test_prompt_mentions_conflicts(self, loader):
        """Prompt should mention identifying conflicts."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        conflict_terms = ["conflitt", "conflict", "contrasto", "incompatibil", "divergen"]
        matches = sum(1 for term in conflict_terms if term in content.lower())
        assert matches >= 1, "Should mention conflict identification"

    def test_prompt_json_conflicts_has_structure(self, loader):
        """conflicts field should have proper structure."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        conflicts = parsed.get("conflicts", [])
        assert isinstance(conflicts, list), "conflicts should be a list"

    def test_prompt_mentions_conflict_resolution(self, loader):
        """Prompt should mention how to resolve conflicts."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        resolution_terms = ["risolv", "resolv", "priorit", "prevale", "gerarchia"]
        matches = sum(1 for term in resolution_terms if term in content.lower())
        assert matches >= 1, "Should mention conflict resolution"


# =============================================================================
# Tests: Cross-Domain Synthesis
# =============================================================================


class TestCrossDomainSynthesis:
    """Test that the prompt specifies cross-domain synthesis."""

    def test_prompt_mentions_synthesis(self, loader):
        """Prompt should mention synthesizing across domains."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        synthesis_terms = ["sintesi", "synthesis", "integra", "combina", "unifica"]
        matches = sum(1 for term in synthesis_terms if term in content.lower())
        assert matches >= 1, "Should mention synthesis"

    def test_prompt_json_synthesis_has_reasoning(self, loader):
        """synthesis field should have reasoning."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        synthesis = parsed.get("synthesis", {})
        assert isinstance(synthesis, dict), "synthesis should be a dict"
        # Should have reasoning or approach
        has_reasoning = "reasoning" in synthesis or "approach" in synthesis or "strategy" in synthesis
        assert has_reasoning, "synthesis should have reasoning"

    def test_prompt_json_synthesis_has_integrated_conclusion(self, loader):
        """synthesis should have integrated conclusion."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        synthesis = parsed.get("synthesis", {})
        # Should have conclusion or integrated_answer or integrated_conclusion
        has_conclusion = (
            "conclusion" in synthesis
            or "integrated_answer" in synthesis
            or "integrated_conclusion" in synthesis
            or "summary" in synthesis
        )
        assert has_conclusion, "synthesis should have conclusion"


# =============================================================================
# Tests: Italian Professional Language
# =============================================================================


class TestItalianProfessionalLanguage:
    """Test that the prompt uses Italian professional language."""

    def test_prompt_is_in_italian(self, loader):
        """Prompt should be primarily in Italian."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        italian_keywords = ["analizza", "dominio", "risposta", "fonti", "sintesi"]
        matches = sum(1 for kw in italian_keywords if kw in content.lower())
        assert matches >= 3, "Prompt should contain Italian language"

    def test_prompt_mentions_italian_domains(self, loader):
        """Prompt should mention Italian professional domains."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        domain_terms = ["fiscale", "lavoro", "legale", "previdenziale"]
        matches = sum(1 for term in domain_terms if term in content.lower())
        assert matches >= 2, "Should mention Italian domains"

    def test_prompt_has_professional_tone(self, loader):
        """Prompt should have professional tone."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
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
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "json" in content.lower()

    def test_prompt_json_has_sources_cited(self, loader):
        """JSON schema should have sources_cited field."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "sources_cited" in parsed, "JSON should have 'sources_cited' field"

    def test_prompt_json_has_suggested_actions(self, loader):
        """JSON schema should have suggested_actions field."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "suggested_actions" in parsed, "JSON should have 'suggested_actions' field"

    def test_prompt_json_has_confidence(self, loader):
        """JSON schema should have confidence field."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        # Confidence might be at top level or in synthesis
        has_confidence = (
            "confidence" in parsed
            or "confidence" in parsed.get("synthesis", {})
        )
        assert has_confidence, "JSON should have 'confidence' field"


# =============================================================================
# Tests: Domain-Specific Examples
# =============================================================================


class TestDomainSpecificExamples:
    """Test that the prompt has domain-specific examples."""

    def test_prompt_has_multi_domain_example(self, loader):
        """Prompt should have example involving multiple domains."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        # Should have example with both fiscal and labor aspects
        has_fiscal = "fiscale" in content.lower() or "iva" in content.lower() or "irpef" in content.lower()
        has_labor = "lavoro" in content.lower() or "dipendente" in content.lower() or "contratto" in content.lower()
        assert has_fiscal and has_labor, "Should have multi-domain example"
