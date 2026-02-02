"""TDD Tests for tree_of_thoughts_multi_domain.md Prompt Template.

DEV-224: Create tree_of_thoughts_multi_domain.md Prompt Template.
DEV-251: Updated for free-form responses (no JSON output required).

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 90%+ for new code.
"""

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
# Tests: Free-Form Output (DEV-251)
# =============================================================================


class TestFreeFormOutput:
    """Test that the prompt specifies free-form output (not JSON)."""

    def test_prompt_does_not_require_json_output(self, loader):
        """DEV-251: Prompt should NOT require JSON output format."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        # Should NOT have mandatory JSON output section
        assert "Output (JSON OBBLIGATORIO)" not in content
        assert "Rispondi SEMPRE con questo schema JSON" not in content

    def test_prompt_specifies_professional_document_format(self, loader):
        """Prompt should specify writing as a professional document."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "documento professionale" in content.lower()

    def test_prompt_specifies_prose_style(self, loader):
        """Prompt should specify using fluid prose."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "prosa fluida" in content.lower()

    def test_reasoning_is_internal_not_in_output(self, loader):
        """DEV-251: Reasoning process should be internal, not in output."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        # Should mention that reasoning is internal/mental
        assert "mentalmente" in content.lower() or "interno" in content.lower()


# =============================================================================
# Tests: COMPLETEZZA OBBLIGATORIA (DEV-251)
# =============================================================================


class TestCompletenessRequirements:
    """Test that the prompt specifies completeness requirements."""

    def test_prompt_has_completezza_section(self, loader):
        """Prompt should have COMPLETEZZA OBBLIGATORIA section."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "COMPLETEZZA OBBLIGATORIA" in content

    def test_prompt_requires_scadenze(self, loader):
        """Prompt should require including deadlines/dates."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "scadenze" in content.lower()

    def test_prompt_requires_importi(self, loader):
        """Prompt should require including amounts/rates."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "importi" in content.lower() or "aliquote" in content.lower()

    def test_prompt_requires_requisiti(self, loader):
        """Prompt should require including requirements."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "requisiti" in content.lower()

    def test_prompt_requires_esclusioni(self, loader):
        """Prompt should require including exclusions."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "esclusioni" in content.lower()

    def test_prompt_requires_conseguenze(self, loader):
        """Prompt should require including consequences."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "conseguenze" in content.lower()

    def test_prompt_requires_procedure(self, loader):
        """Prompt should require including procedures."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "procedure" in content.lower()

    def test_prompt_says_not_to_summarize(self, loader):
        """Prompt should explicitly say not to summarize."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "non riassumere" in content.lower()


# =============================================================================
# Tests: Multi-Domain Methodology (Internal Process)
# =============================================================================


class TestMultiDomainMethodology:
    """Test that the prompt specifies multi-domain analysis as internal process."""

    def test_prompt_mentions_parallel_domain_analysis(self, loader):
        """Prompt should mention parallel domain analysis."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        parallel_terms = ["parallel", "parallelo", "ciascun dominio", "ogni dominio"]
        matches = sum(1 for term in parallel_terms if term in content.lower())
        assert matches >= 1, "Should mention parallel analysis"

    def test_prompt_mentions_conflict_identification(self, loader):
        """Prompt should mention identifying conflicts between domains."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        conflict_terms = ["conflitt", "contrasto", "incompatibil", "divergen"]
        matches = sum(1 for term in conflict_terms if term in content.lower())
        assert matches >= 1, "Should mention conflict identification"

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

    def test_prompt_covers_fiscal_domain(self, loader):
        """Prompt should cover fiscal domain analysis."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "fiscale" in content.lower()

    def test_prompt_covers_labor_domain(self, loader):
        """Prompt should cover labor domain analysis."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "lavoro" in content.lower()

    def test_prompt_covers_legal_domain(self, loader):
        """Prompt should cover legal domain analysis."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "legale" in content.lower()


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
# Tests: Source Hierarchy
# =============================================================================


class TestSourceHierarchy:
    """Test that the prompt specifies source hierarchy for conflict resolution."""

    def test_prompt_mentions_legal_hierarchy(self, loader):
        """Prompt should mention Italian legal hierarchy."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        hierarchy_terms = ["gerarchia", "hierarchy", "legge", "decreto", "circolare"]
        matches = sum(1 for term in hierarchy_terms if term in content.lower())
        assert matches >= 2, "Should mention legal source hierarchy"

    def test_prompt_mentions_speciality_principle(self, loader):
        """Prompt should mention principle of speciality."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "special" in content.lower(), "Should mention principle of speciality"


# =============================================================================
# Tests: Anti-Hallucination Rules
# =============================================================================


class TestAntiHallucinationRules:
    """Test that the prompt includes anti-hallucination rules."""

    def test_prompt_has_anti_hallucination_section(self, loader):
        """Prompt should have anti-hallucination rules."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "anti-allucinazione" in content.lower() or "mai inventare" in content.lower()

    def test_prompt_forbids_inventing_law_numbers(self, loader):
        """Prompt should forbid inventing law numbers."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "mai inventare" in content.lower() or "non inventare" in content.lower()

    def test_prompt_requires_kb_verification(self, loader):
        """Prompt should require verifying sources against KB."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
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
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "inline" in content.lower() or "nel testo" in content.lower()

    def test_prompt_provides_citation_examples(self, loader):
        """Prompt should provide citation format examples."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        # Should have example like "Art. X, comma Y"
        assert "art." in content.lower() and "comma" in content.lower()

    def test_prompt_forbids_separate_sources_section(self, loader):
        """Prompt should forbid adding separate Sources section."""
        content = loader.load(
            "tree_of_thoughts_multi_domain",
            query="Test query",
            kb_context="Contesto...",
            kb_sources="Fonti...",
            domains="fiscale, lavoro",
        )
        assert "non aggiungere" in content.lower() and "fonti" in content.lower()
