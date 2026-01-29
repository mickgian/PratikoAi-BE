"""TDD Tests for Phase 9: unified_response_simple.md Prompt Template.

DEV-212: Create unified_response_simple.md Prompt Template.

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
        """unified_response_simple.md should load without errors."""
        # Should not raise FileNotFoundError
        content = loader.load(
            "unified_response_simple",
            kb_context="Test context",
            kb_sources_metadata="[]",
            query="Test query",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        assert content is not None
        assert len(content) > 0

    def test_prompt_exists_in_v1_directory(self):
        """Prompt file should exist in app/prompts/v1/."""
        prompt_path = PROMPTS_DIR / "v1" / "unified_response_simple.md"
        assert prompt_path.exists(), f"Prompt file not found at {prompt_path}"

    def test_prompt_is_markdown_file(self):
        """Prompt should be a .md file."""
        prompt_path = PROMPTS_DIR / "v1" / "unified_response_simple.md"
        assert prompt_path.suffix == ".md"


@pytest.mark.skip(reason="DEV-250: Prompt refactored to prose format, JSON schema removed")
class TestPromptContainsJsonSchema:
    """Test that the prompt contains a valid JSON schema example."""

    def test_prompt_has_json_code_block(self, loader):
        """Prompt should contain a JSON code block."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test context",
            kb_sources_metadata="[]",
            query="Test query",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        assert "```json" in content, "Prompt should contain JSON code block"

    def test_prompt_json_schema_is_parseable(self, loader):
        """The JSON schema example in the prompt should be valid JSON."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test context",
            kb_sources_metadata="[]",
            query="Test query",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
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

    def test_prompt_json_has_required_fields(self, loader):
        """JSON schema should have required output fields."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test context",
            kb_sources_metadata="[]",
            query="Test query",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        assert json_match is not None

        parsed = json.loads(json_match.group(1))

        # Required top-level fields
        assert "reasoning" in parsed, "JSON should have 'reasoning' field"
        assert "answer" in parsed, "JSON should have 'answer' field"
        assert "sources_cited" in parsed, "JSON should have 'sources_cited' field"
        assert "suggested_actions" in parsed, "JSON should have 'suggested_actions' field"

    def test_prompt_reasoning_has_cot_structure(self, loader):
        """JSON reasoning field should have CoT structure."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test context",
            kb_sources_metadata="[]",
            query="Test query",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        reasoning = parsed.get("reasoning", {})
        assert "tema_identificato" in reasoning, "Reasoning should have 'tema_identificato'"
        assert "fonti_utilizzate" in reasoning, "Reasoning should have 'fonti_utilizzate'"
        assert "elementi_chiave" in reasoning, "Reasoning should have 'elementi_chiave'"
        assert "conclusione" in reasoning, "Reasoning should have 'conclusione'"


class TestPromptVariablesSubstitute:
    """Test that all template variables work correctly."""

    def test_kb_context_substitutes(self, loader):
        """kb_context variable should substitute correctly."""
        test_context = "Questo è il contesto di test per IVA"
        content = loader.load(
            "unified_response_simple",
            kb_context=test_context,
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        assert test_context in content

    def test_kb_sources_metadata_substitutes(self, loader):
        """kb_sources_metadata variable should substitute correctly."""
        test_metadata = '[{"source": "DPR 633/72", "type": "normativa"}]'
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata=test_metadata,
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        assert test_metadata in content

    def test_query_substitutes(self, loader):
        """query variable should substitute correctly."""
        test_query = "Qual è l'aliquota IVA per i libri?"
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query=test_query,
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        assert test_query in content

    def test_conversation_context_substitutes(self, loader):
        """conversation_context variable should substitute correctly."""
        test_conv = "User: Ciao\\nAssistant: Buongiorno!"
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context=test_conv,
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        assert test_conv in content

    def test_current_date_substitutes(self, loader):
        """current_date variable should substitute correctly."""
        test_date = "2024-12-31"
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date=test_date,
            web_sources_metadata="[]",
        )
        assert test_date in content

    def test_missing_variable_raises_error(self, loader):
        """Missing required variable should raise KeyError."""
        with pytest.raises(KeyError):
            loader.load(
                "unified_response_simple",
                kb_context="Test",
                # Missing: kb_sources_metadata, query, conversation_context, current_date
            )


class TestPromptReasoningStructure:
    """Test Chain of Thought (CoT) reasoning structure is present."""

    def test_prompt_has_cot_instructions(self, loader):
        """Prompt should have Chain of Thought instructions."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        # Check for CoT keywords in Italian
        assert "ragionamento" in content.lower() or "chain of thought" in content.lower()

    def test_prompt_has_step_by_step_guidance(self, loader):
        """Prompt should guide step-by-step reasoning."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        # Should have numbered steps or clear structure
        assert "TEMA" in content or "tema" in content.lower()
        assert "FONTI" in content or "fonti" in content.lower()
        assert "ELEMENTI" in content or "elementi" in content.lower()
        assert "CONCLUSIONE" in content or "conclusione" in content.lower()


@pytest.mark.skip(reason="DEV-250: Prompt refactored to prose format, JSON schema removed")
class TestPromptActionRulesPresent:
    """Test that action generation rules are documented."""

    def test_prompt_has_action_rules_section(self, loader):
        """Prompt should have rules for action generation."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        # Should mention action rules
        assert "azioni" in content.lower() or "actions" in content.lower()

    def test_prompt_specifies_action_constraints(self, loader):
        """Prompt should specify constraints for actions."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        # Should mention character limits or constraints
        assert "caratteri" in content.lower() or "characters" in content.lower()

    def test_prompt_forbids_generic_actions(self, loader):
        """Prompt should forbid generic placeholder actions."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        # Should explicitly forbid generic actions
        assert "vietat" in content.lower() or "mai" in content.lower() or "non" in content.lower()

    def test_prompt_requires_source_based_actions(self, loader):
        """Prompt should require actions to be based on KB sources."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        # Should mention source basis
        assert "fonte" in content.lower() or "source" in content.lower()


class TestPromptCitationRules:
    """Test that citation rules are documented."""

    def test_prompt_has_citation_rules(self, loader):
        """Prompt should have citation rules."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        # Should mention citations
        assert "citazion" in content.lower() or "citation" in content.lower()

    def test_prompt_specifies_citation_format(self, loader):
        """Prompt should specify Italian citation format."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        # Should mention Italian legal format
        assert "Art." in content or "D.Lgs." in content or "DPR" in content


class TestPromptItalianLanguage:
    """Test that the prompt uses Italian professional language."""

    def test_prompt_is_in_italian(self, loader):
        """Prompt should be primarily in Italian."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        # Check for common Italian words
        italian_keywords = ["risposta", "domanda", "contesto", "fonti", "italiano"]
        matches = sum(1 for kw in italian_keywords if kw in content.lower())
        assert matches >= 3, "Prompt should contain Italian language"

    def test_prompt_mentions_pratikoai_role(self, loader):
        """Prompt should define PratikoAI role."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        assert "PratikoAI" in content


@pytest.mark.skip(reason="DEV-250: Prompt refactored to prose format, JSON schema removed")
class TestPromptActionSchema:
    """Test the action schema structure in JSON."""

    def test_action_schema_has_required_fields(self, loader):
        """Action objects in JSON should have required fields."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        actions = parsed.get("suggested_actions", [])
        assert len(actions) > 0, "JSON should have example actions"

        action = actions[0]
        assert "id" in action, "Action should have 'id' field"
        assert "label" in action, "Action should have 'label' field"
        assert "icon" in action, "Action should have 'icon' field"
        assert "prompt" in action, "Action should have 'prompt' field"
        assert "source_basis" in action, "Action should have 'source_basis' field"

    def test_action_icon_is_valid(self, loader):
        """Action icon should be from allowed list."""
        valid_icons = {
            "calculator",
            "search",
            "calendar",
            "file-text",
            "alert-triangle",
            "check-circle",
            "edit",
            "refresh-cw",
            "book-open",
            "bar-chart",
        }

        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        actions = parsed.get("suggested_actions", [])
        for action in actions:
            icon = action.get("icon", "")
            assert icon in valid_icons, f"Icon '{icon}' is not in allowed list"


@pytest.mark.skip(reason="DEV-250: Prompt refactored to prose format, JSON schema removed")
class TestPromptSourceSchema:
    """Test the source citation schema structure."""

    def test_source_schema_has_required_fields(self, loader):
        """Source objects in JSON should have required fields."""
        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        sources = parsed.get("sources_cited", [])
        assert len(sources) > 0, "JSON should have example sources"

        source = sources[0]
        assert "ref" in source, "Source should have 'ref' field"
        assert "relevance" in source, "Source should have 'relevance' field"

    def test_source_relevance_is_valid(self, loader):
        """Source relevance should be valid value."""
        valid_relevance = {"principale", "supporto"}

        content = loader.load(
            "unified_response_simple",
            kb_context="Test",
            kb_sources_metadata="[]",
            query="Test",
            conversation_context="",
            current_date="2024-12-31",
            web_sources_metadata="[]",
        )
        json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        parsed = json.loads(json_match.group(1))

        sources = parsed.get("sources_cited", [])
        for source in sources:
            relevance = source.get("relevance", "")
            assert relevance in valid_relevance, f"Relevance '{relevance}' is not valid"
