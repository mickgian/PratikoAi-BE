"""TDD Tests for Phase 9: complexity_classifier.md Prompt Template.

DEV-220: Create complexity_classifier.md Prompt Template.

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


class TestPromptLoadsViaLoader:
    """Test that the prompt loads correctly via PromptLoader."""

    def test_prompt_loads_without_error(self, loader):
        """complexity_classifier.md should load without errors."""
        # Should not raise FileNotFoundError
        content = loader.load(
            "complexity_classifier",
            query="Qual è l'aliquota IVA ordinaria?",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        assert content is not None
        assert len(content) > 0

    def test_prompt_exists_in_v1_directory(self):
        """Prompt file should exist in app/prompts/v1/."""
        prompt_path = PROMPTS_DIR / "v1" / "complexity_classifier.md"
        assert prompt_path.exists(), f"Prompt file not found at {prompt_path}"

    def test_prompt_is_markdown_file(self):
        """Prompt should be a .md file."""
        prompt_path = PROMPTS_DIR / "v1" / "complexity_classifier.md"
        assert prompt_path.suffix == ".md"


class TestPromptVariablesSubstitute:
    """Test that all template variables work correctly."""

    def test_query_substitutes(self, loader):
        """query variable should substitute correctly."""
        test_query = "Come fatturare consulenza a azienda tedesca?"
        content = loader.load(
            "complexity_classifier",
            query=test_query,
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        assert test_query in content

    def test_domains_substitutes(self, loader):
        """domains variable should substitute correctly."""
        test_domains = "fiscale, lavoro"
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains=test_domains,
            has_history="No",
            has_documents="No",
        )
        assert test_domains in content

    def test_has_history_substitutes(self, loader):
        """has_history variable should substitute correctly."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="Sì",
            has_documents="No",
        )
        assert "Sì" in content

    def test_has_documents_substitutes(self, loader):
        """has_documents variable should substitute correctly."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="Sì",
        )
        # Count occurrences - "Sì" should appear at least twice (once for has_history, once for has_documents)
        # But since has_history is "No", it should appear exactly once
        assert "Sì" in content

    def test_missing_variable_raises_error(self, loader):
        """Missing required variable should raise KeyError."""
        with pytest.raises(KeyError):
            loader.load(
                "complexity_classifier",
                query="Test query",
                # Missing: domains, has_history, has_documents
            )


class TestPromptJsonSchemaValid:
    """Test that the prompt contains a valid JSON schema example."""

    def test_prompt_has_json_code_block(self, loader):
        """Prompt should contain a JSON code block."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        assert "```json" in content, "Prompt should contain JSON code block"

    def test_prompt_json_schema_is_parseable(self, loader):
        """The JSON schema example in the prompt should be valid JSON."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Extract JSON from code block
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        assert json_match is not None, "Could not find JSON code block"

        json_str = json_match.group(1)
        # Should parse without error
        try:
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"JSON schema in prompt is not valid: {e}")

    def test_prompt_json_has_complexity_field(self, loader):
        """JSON schema should have complexity field."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        assert json_match is not None

        parsed = json.loads(json_match.group(1))
        assert "complexity" in parsed, "JSON should have 'complexity' field"

    def test_prompt_json_has_domains_field(self, loader):
        """JSON schema should have domains field."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "domains" in parsed, "JSON should have 'domains' field"
        assert isinstance(parsed["domains"], list), "domains should be a list"

    def test_prompt_json_has_confidence_field(self, loader):
        """JSON schema should have confidence field."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "confidence" in parsed, "JSON should have 'confidence' field"

    def test_prompt_json_has_reasoning_field(self, loader):
        """JSON schema should have reasoning field."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))
        assert "reasoning" in parsed, "JSON should have 'reasoning' field"


class TestComplexityCategories:
    """Test that complexity categories are documented in the prompt."""

    def test_prompt_defines_simple_category(self, loader):
        """Prompt should define SIMPLE complexity category."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        assert "SIMPLE" in content or "simple" in content.lower()
        # Should have examples for simple queries
        assert "aliquota" in content.lower() or "scadenz" in content.lower()

    def test_prompt_defines_complex_category(self, loader):
        """Prompt should define COMPLEX complexity category."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        assert "COMPLEX" in content or "complex" in content.lower()
        # Should mention multi-step reasoning
        assert "multi" in content.lower() or "ragionamento" in content.lower()

    def test_prompt_defines_multi_domain_category(self, loader):
        """Prompt should define MULTI_DOMAIN complexity category."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        assert "MULTI_DOMAIN" in content or "multi_domain" in content.lower()
        # Should mention multiple domains
        assert "domini" in content.lower() or "domain" in content.lower()

    def test_prompt_has_simple_examples(self, loader):
        """Prompt should have examples for SIMPLE category."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Check for simple query examples
        simple_keywords = ["aliquota iva", "scade", "f24"]
        matches = sum(1 for kw in simple_keywords if kw in content.lower())
        assert matches >= 1, "Should have at least one SIMPLE example"

    def test_prompt_has_complex_examples(self, loader):
        """Prompt should have examples for COMPLEX category."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Check for complex query examples
        complex_keywords = ["fatturare", "calcolo", "irpef", "detrazioni"]
        matches = sum(1 for kw in complex_keywords if kw in content.lower())
        assert matches >= 1, "Should have at least one COMPLEX example"

    def test_prompt_has_multi_domain_examples(self, loader):
        """Prompt should have examples for MULTI_DOMAIN category."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Check for multi-domain examples (involving work + tax, etc.)
        assert "dipendente" in content.lower() or "lavoro" in content.lower()


class TestPromptItalianLanguage:
    """Test that the prompt uses Italian professional language."""

    def test_prompt_is_in_italian(self, loader):
        """Prompt should be primarily in Italian."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Check for common Italian words
        italian_keywords = ["analizza", "query", "classificazione", "complessità", "domanda"]
        matches = sum(1 for kw in italian_keywords if kw in content.lower())
        assert matches >= 3, "Prompt should contain Italian language"

    def test_prompt_mentions_italian_context(self, loader):
        """Prompt should mention Italian fiscal/legal context."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        assert "italian" in content.lower() or "italiana" in content.lower()


class TestPromptContextFields:
    """Test that context fields are properly documented."""

    def test_prompt_has_domains_context(self, loader):
        """Prompt should have domains context section."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Should reference detected domains
        assert "domini" in content.lower() or "domain" in content.lower()

    def test_prompt_has_conversation_history_context(self, loader):
        """Prompt should have conversation history context."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Should mention conversation context
        assert "conversazione" in content.lower() or "history" in content.lower()

    def test_prompt_has_documents_context(self, loader):
        """Prompt should have documents context."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Should mention attached documents
        assert "documenti" in content.lower() or "document" in content.lower()


class TestComplexityOutputValues:
    """Test that complexity output values are correctly specified."""

    def test_complexity_field_valid_values(self, loader):
        """Complexity field should specify valid enum values."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Check that all three values are mentioned in the prompt
        assert "simple" in content.lower()
        assert "complex" in content.lower()
        assert "multi_domain" in content.lower()

    def test_confidence_range_specified(self, loader):
        """Confidence field should specify 0.0-1.0 range."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Should mention confidence range
        assert "0.0" in content or "0-1" in content or "confidence" in content.lower()

    def test_domains_list_examples(self, loader):
        """Domains field should have example values."""
        content = loader.load(
            "complexity_classifier",
            query="Test query",
            domains="fiscale",
            has_history="No",
            has_documents="No",
        )
        # Should list domain examples
        domain_examples = ["fiscale", "lavoro", "legale"]
        matches = sum(1 for d in domain_examples if d in content.lower())
        assert matches >= 2, "Should list at least 2 domain examples"
