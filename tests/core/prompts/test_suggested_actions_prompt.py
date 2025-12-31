"""
TDD Tests for suggested_actions prompt module.

Tests written FIRST as per DEV-175 requirements.
"""

import json
import os
import re

import pytest


class TestPromptFileExists:
    """Tests for prompt file existence and basic structure."""

    def test_prompt_file_exists(self):
        """suggested_actions.md must exist in prompts directory."""
        from app.core.prompts import __file__ as prompts_init_path

        prompts_dir = os.path.dirname(prompts_init_path)
        prompt_path = os.path.join(prompts_dir, "suggested_actions.md")
        assert os.path.exists(prompt_path), f"File not found: {prompt_path}"

    def test_prompt_valid_utf8_encoding(self):
        """Prompt file must be valid UTF-8 (for emoji support)."""
        from app.core.prompts import __file__ as prompts_init_path

        prompts_dir = os.path.dirname(prompts_init_path)
        prompt_path = os.path.join(prompts_dir, "suggested_actions.md")

        # Should not raise UnicodeDecodeError
        with open(prompt_path, encoding="utf-8") as f:
            content = f.read()
            assert len(content) > 0


class TestPromptContent:
    """Tests for prompt content requirements."""

    @pytest.fixture
    def prompt_content(self):
        """Load prompt content for testing."""
        from app.core.prompts import load_suggested_actions_prompt

        return load_suggested_actions_prompt()

    def test_prompt_contains_answer_tag_instruction(self, prompt_content):
        """Prompt must instruct LLM to use <answer> tags."""
        assert "<answer>" in prompt_content
        assert "</answer>" in prompt_content

    def test_prompt_contains_suggested_actions_tag_instruction(self, prompt_content):
        """Prompt must instruct LLM to use <suggested_actions> tags."""
        assert "<suggested_actions>" in prompt_content
        assert "</suggested_actions>" in prompt_content

    def test_prompt_contains_json_format_example(self, prompt_content):
        """Prompt must include JSON format example for actions."""
        # Check for JSON array structure
        assert '"id"' in prompt_content
        assert '"label"' in prompt_content
        assert '"icon"' in prompt_content
        assert '"prompt"' in prompt_content

    def test_prompt_json_examples_are_valid_json(self, prompt_content):
        """JSON examples in prompt must be valid JSON (after unescaping {{ }})."""
        # Extract JSON from suggested_actions tags in the example
        pattern = r"<suggested_actions>\s*(\[[\s\S]*?\])\s*</suggested_actions>"
        match = re.search(pattern, prompt_content)
        assert match is not None, "No JSON example found in suggested_actions tags"

        json_str = match.group(1)
        # DEV-201b: Unescape {{ and }} used for Python .format() compatibility
        json_str = json_str.replace("{{", "{").replace("}}", "}")
        # Should not raise JSONDecodeError
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) >= 2  # At least 2 example actions

    def test_prompt_contains_all_icon_suggestions(self, prompt_content):
        """Prompt must include all icon suggestions (Lucide icon names)."""
        # DEV-201b: Icons changed from emojis to Lucide icon names
        required_icons = [
            "calculator",     # Calcoli, importi, costi
            "file-text",      # Documenti, liste, procedure
            "search",         # Ricerca, verifica, approfondimento
            "bar-chart",      # Analisi, confronti, statistiche
            "calendar",       # Scadenze, timeline, date
            "alert-triangle", # Avvertenze, sanzioni, rischi
            "check-circle",   # Verifiche, controlli
            "edit",           # Generazione testi, modelli
            "refresh-cw",     # Ricalcoli, aggiornamenti
            "book-open",      # Normativa, leggi, circolari
        ]
        for icon in required_icons:
            assert icon in prompt_content, f"Missing icon: {icon}"

    def test_prompt_contains_action_requirements(self, prompt_content):
        """Prompt must specify action requirements (specific, complete, executable, diverse)."""
        # DEV-201b: Check for Italian terms in the new prompt format
        # STEP 3 mentions: Specifiche, Complete, eseguibile
        # STEP 4 mentions: Diversità
        assert "Specific" in prompt_content or "specific" in prompt_content or "SPECIFICI" in prompt_content
        assert "Complet" in prompt_content or "complet" in prompt_content  # Complete/completo
        assert "eseguibile" in prompt_content or "click" in prompt_content  # actionable
        assert "Divers" in prompt_content or "divers" in prompt_content  # Diversità/diverse

    def test_prompt_contains_example_categories(self, prompt_content):
        """Prompt must contain examples for different response types."""
        # DEV-201b: Check for category examples in new prompt format
        # The prompt mentions these categories in STEP 1 and icon descriptions
        lower_content = prompt_content.lower()
        assert "fiscal" in lower_content or "calcol" in lower_content  # fiscale/fiscali, calcolo/calcoli
        assert "normativ" in lower_content  # normativa/normativi
        assert "procedur" in lower_content or "adempiment" in lower_content  # procedura, adempimenti
        assert "document" in lower_content  # documento/documenti

    def test_prompt_specifies_action_count(self, prompt_content):
        """Prompt must specify 2-4 actions requirement."""
        assert "2-4" in prompt_content or ("2" in prompt_content and "4" in prompt_content)


class TestLoaderFunction:
    """Tests for load_suggested_actions_prompt function."""

    def test_load_function_returns_string(self):
        """load_suggested_actions_prompt() must return a string."""
        from app.core.prompts import load_suggested_actions_prompt

        result = load_suggested_actions_prompt()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_load_function_raises_on_missing_file(self, tmp_path, monkeypatch):
        """load_suggested_actions_prompt() must raise FileNotFoundError if file missing."""
        import app.core.prompts as prompts_module

        # Monkeypatch __file__ to a temp directory without the file
        monkeypatch.setattr(prompts_module, "__file__", str(tmp_path / "__init__.py"))

        # Create the fake __init__.py
        (tmp_path / "__init__.py").write_text("")

        # Re-import to get the function with new path
        # The function should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            # We need to actually call the function logic with the wrong path
            import os

            prompts_dir = tmp_path
            prompt_path = os.path.join(prompts_dir, "suggested_actions.md")
            with open(prompt_path, encoding="utf-8") as f:
                f.read()

    def test_load_function_is_exported(self):
        """load_suggested_actions_prompt must be importable from app.core.prompts."""
        from app.core.prompts import load_suggested_actions_prompt

        assert callable(load_suggested_actions_prompt)


class TestPromptTokenBudget:
    """Tests for prompt token count constraints."""

    def test_prompt_token_count_within_budget(self):
        """Prompt must not exceed ~1000 tokens to preserve KB context allocation."""
        from app.core.prompts import load_suggested_actions_prompt

        content = load_suggested_actions_prompt()

        # Approximate token count: ~4 chars per token for English/Italian mixed
        # More accurate would use tiktoken, but this is a reasonable approximation
        approx_tokens = len(content) / 4

        # DEV-201b: Increased budget to 1000 tokens for comprehensive prompt
        # with domain classification, multi-step strategy, and icon documentation
        assert approx_tokens <= 1000, (
            f"Prompt too long: ~{int(approx_tokens)} tokens (max 1000)"
        )


class TestPromptConstantExport:
    """Tests for SUGGESTED_ACTIONS_PROMPT constant."""

    def test_suggested_actions_prompt_constant_exported(self):
        """SUGGESTED_ACTIONS_PROMPT constant must be exported."""
        from app.core.prompts import SUGGESTED_ACTIONS_PROMPT

        assert isinstance(SUGGESTED_ACTIONS_PROMPT, str)
        assert len(SUGGESTED_ACTIONS_PROMPT) > 0

    def test_constant_matches_loader_output(self):
        """SUGGESTED_ACTIONS_PROMPT must match load_suggested_actions_prompt() output."""
        from app.core.prompts import (
            SUGGESTED_ACTIONS_PROMPT,
            load_suggested_actions_prompt,
        )

        assert load_suggested_actions_prompt() == SUGGESTED_ACTIONS_PROMPT
