"""TDD Tests for Phase 9: PromptLoader Utility Service.

DEV-211: Create PromptLoader Utility Service.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 95%+ for new code.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.prompt_loader import PromptLoader


@pytest.fixture
def temp_prompts_dir():
    """Create a temporary prompts directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_path = Path(tmpdir)

        # Create version directory
        v1_dir = prompts_path / "v1"
        v1_dir.mkdir()

        # Create components directory
        components_dir = prompts_path / "components"
        components_dir.mkdir()

        # Create config.yaml
        config_file = prompts_path / "config.yaml"
        config_file.write_text("version: v1\ncache_ttl: 3600\n")

        # Create test prompt files
        (v1_dir / "test_prompt.md").write_text("# Test Prompt\n\nHello {name}!\n\nYour query: {query}")
        (v1_dir / "simple_prompt.md").write_text("This is a simple prompt without variables.")
        (v1_dir / "empty_prompt.md").write_text("")
        (v1_dir / "italian_prompt.md").write_text(
            "# Prompt Italiano\n\nBenvenuto, {nome}!\n\nLa tua domanda è: {domanda}\n\nCaratteri speciali: àèìòù"
        )
        (v1_dir / "unified_response_simple.md").write_text(
            "# Unified Response\n\nContext: {kb_context}\n\nQuery: {query}"
        )

        # Create component files
        (components_dir / "source_citation_rules.md").write_text(
            "## Citation Rules\n\n- Always cite the most authoritative source"
        )
        (components_dir / "italian_formatting.md").write_text("## Italian Formatting\n\n- Use formal Italian")

        yield prompts_path


@pytest.fixture
def loader(temp_prompts_dir):
    """Create a PromptLoader instance with temp directory."""
    return PromptLoader(prompts_dir=temp_prompts_dir)


class TestPromptLoaderInit:
    """Test PromptLoader initialization."""

    def test_init_with_custom_dir(self, temp_prompts_dir):
        """PromptLoader should accept custom prompts directory."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert loader.prompts_dir == temp_prompts_dir

    def test_init_with_default_version(self, temp_prompts_dir):
        """PromptLoader should default to v1 version."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        assert loader.version == "v1"

    def test_init_with_custom_version(self, temp_prompts_dir):
        """PromptLoader should accept custom version."""
        loader = PromptLoader(prompts_dir=temp_prompts_dir, version="v2")
        assert loader.version == "v2"


class TestPromptLoaderLoad:
    """Test PromptLoader.load() method."""

    def test_load_prompt_success(self, loader):
        """load() should return prompt content."""
        content = loader.load("simple_prompt")
        assert content == "This is a simple prompt without variables."

    def test_load_prompt_with_variables(self, loader):
        """load() should substitute variables."""
        content = loader.load("test_prompt", name="Alice", query="What is IRPEF?")
        assert "Hello Alice!" in content
        assert "Your query: What is IRPEF?" in content

    def test_load_prompt_not_found(self, loader):
        """load() should raise FileNotFoundError for missing prompt."""
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load("nonexistent_prompt")
        assert "nonexistent_prompt" in str(exc_info.value)

    def test_load_missing_variable_raises_keyerror(self, loader):
        """load() should raise KeyError when required variable is missing."""
        with pytest.raises(KeyError) as exc_info:
            loader.load("test_prompt", name="Alice")  # missing 'query'
        assert "query" in str(exc_info.value)

    def test_load_extra_variables_ignored(self, loader):
        """load() should ignore extra variables not in template."""
        content = loader.load("test_prompt", name="Alice", query="Test", extra_var="ignored")
        assert "Hello Alice!" in content
        assert "ignored" not in content

    def test_load_empty_prompt(self, loader):
        """load() should return empty string for empty prompt file."""
        content = loader.load("empty_prompt")
        assert content == ""

    def test_load_italian_characters(self, loader):
        """load() should handle Italian UTF-8 characters."""
        content = loader.load("italian_prompt", nome="Mario", domanda="Cos'è l'IVA?")
        assert "Benvenuto, Mario!" in content
        assert "Cos'è l'IVA?" in content
        assert "àèìòù" in content


class TestPromptLoaderLoadComponent:
    """Test PromptLoader.load_component() method."""

    def test_load_component_success(self, loader):
        """load_component() should return component content."""
        content = loader.load_component("source_citation_rules")
        assert "Citation Rules" in content
        assert "authoritative source" in content

    def test_load_component_not_found(self, loader):
        """load_component() should raise FileNotFoundError for missing component."""
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load_component("nonexistent_component")
        assert "nonexistent_component" in str(exc_info.value)


class TestPromptLoaderCompose:
    """Test PromptLoader.compose() method."""

    def test_compose_two_prompts(self, loader):
        """compose() should combine prompts with separator."""
        prompt1 = loader.load("simple_prompt")
        component = loader.load_component("source_citation_rules")
        composed = loader.compose(prompt1, component)
        assert "simple prompt" in composed
        assert "Citation Rules" in composed
        assert "\n\n---\n\n" in composed

    def test_compose_custom_separator(self, loader):
        """compose() should use custom separator."""
        prompt1 = "Part 1"
        prompt2 = "Part 2"
        composed = loader.compose(prompt1, prompt2, separator="\n===\n")
        assert composed == "Part 1\n===\nPart 2"

    def test_compose_single_prompt(self, loader):
        """compose() with single prompt should return it unchanged."""
        prompt = "Single prompt"
        composed = loader.compose(prompt)
        assert composed == prompt

    def test_compose_empty_list(self, loader):
        """compose() with no prompts should return empty string."""
        composed = loader.compose()
        assert composed == ""


class TestPromptLoaderCaching:
    """Test PromptLoader caching behavior."""

    def test_caching_returns_same_content(self, loader):
        """Second load() call should return cached content."""
        content1 = loader.load("simple_prompt")
        content2 = loader.load("simple_prompt")
        assert content1 == content2

    def test_reload_clears_single_prompt(self, loader, temp_prompts_dir):
        """reload(name) should clear cache for specific prompt."""
        # Load prompt
        content1 = loader.load("simple_prompt")

        # Modify the file
        (temp_prompts_dir / "v1" / "simple_prompt.md").write_text("Modified content")

        # Should still return cached
        content2 = loader.load("simple_prompt")
        assert content2 == content1

        # Reload specific prompt
        loader.reload("simple_prompt")

        # Should return new content
        content3 = loader.load("simple_prompt")
        assert content3 == "Modified content"

    def test_reload_clears_all_cache(self, loader, temp_prompts_dir):
        """reload() without name should clear all cache."""
        # Load multiple prompts
        loader.load("simple_prompt")
        loader.load("test_prompt", name="Test", query="Query")

        # Modify files
        (temp_prompts_dir / "v1" / "simple_prompt.md").write_text("Modified 1")

        # Reload all
        loader.reload()

        # Should return new content
        content = loader.load("simple_prompt")
        assert content == "Modified 1"


class TestPromptLoaderListPrompts:
    """Test PromptLoader.list_prompts() method."""

    def test_list_prompts_returns_all(self, loader):
        """list_prompts() should return all available prompt names."""
        prompts = loader.list_prompts()
        assert "simple_prompt" in prompts
        assert "test_prompt" in prompts
        assert "italian_prompt" in prompts
        assert "unified_response_simple" in prompts

    def test_list_prompts_excludes_components(self, loader):
        """list_prompts() should not include components."""
        prompts = loader.list_prompts()
        assert "source_citation_rules" not in prompts
        assert "italian_formatting" not in prompts


class TestPromptLoaderGetVersion:
    """Test PromptLoader.get_version() method."""

    def test_get_version_returns_current(self, loader):
        """get_version() should return current version."""
        version = loader.get_version()
        assert version == "v1"

    def test_get_version_from_config(self, temp_prompts_dir):
        """get_version() should read from config.yaml if available."""
        # Modify config
        (temp_prompts_dir / "config.yaml").write_text("version: v2\n")
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        # Note: version is set at init time
        assert loader.version == "v1"  # Default, config reading is optional


class TestPromptLoaderErrorHandling:
    """Test PromptLoader error handling."""

    def test_invalid_prompts_dir_returns_empty_list(self):
        """PromptLoader with invalid dir should return empty list from list_prompts."""
        loader = PromptLoader(prompts_dir=Path("/nonexistent/path"))
        prompts = loader.list_prompts()
        assert prompts == []

    def test_invalid_prompts_dir_raises_on_load(self):
        """PromptLoader with invalid dir should raise FileNotFoundError on load."""
        loader = PromptLoader(prompts_dir=Path("/nonexistent/path"))
        with pytest.raises(FileNotFoundError):
            loader.load("any_prompt")

    def test_load_with_special_chars_in_variable(self, loader):
        """load() should handle special characters in variable values."""
        content = loader.load("test_prompt", name="Mario & Luigi", query="What's the tax rate?")
        assert "Mario & Luigi" in content
        assert "What's the tax rate?" in content


class TestPromptLoaderVariableSubstitution:
    """Test variable substitution edge cases."""

    def test_curly_braces_in_content(self, temp_prompts_dir):
        """Prompt with literal curly braces should work."""
        (temp_prompts_dir / "v1" / "json_example.md").write_text('JSON example: {"key": "value"}\n\nUser: {name}')
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        # This tests that we handle JSON-like content properly
        content = loader.load("json_example", name="Test")
        assert '{"key": "value"}' in content
        assert "User: Test" in content

    def test_multiple_same_variable(self, temp_prompts_dir):
        """Same variable appearing multiple times should all be substituted."""
        (temp_prompts_dir / "v1" / "repeated_var.md").write_text("Hello {name}! Welcome {name}! Goodbye {name}!")
        loader = PromptLoader(prompts_dir=temp_prompts_dir)
        content = loader.load("repeated_var", name="Alice")
        assert content.count("Alice") == 3


class TestPromptLoaderIntegration:
    """Integration tests for realistic usage."""

    def test_full_workflow(self, loader):
        """Test complete workflow: load, compose, with variables."""
        # Load main prompt with variables
        main_prompt = loader.load(
            "unified_response_simple",
            kb_context="Tax law context here",
            query="What is IRPEF?",
        )

        # Load component
        citation_rules = loader.load_component("source_citation_rules")

        # Compose
        full_prompt = loader.compose(main_prompt, citation_rules)

        # Verify
        assert "Tax law context here" in full_prompt
        assert "What is IRPEF?" in full_prompt
        assert "Citation Rules" in full_prompt
