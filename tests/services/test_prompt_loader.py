"""Tests for PromptLoader service.

Validates prompt loading, variable substitution, component loading,
composition, caching, reload, listing, and singleton behavior.
Uses tmp_path fixture to create isolated test directory structures.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.prompt_loader import PromptLoader, get_prompt_loader


@pytest.fixture()
def prompt_dir(tmp_path: Path) -> Path:
    """Create a temporary prompts directory with test files."""
    # Create v1 directory with prompt files
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()

    # Simple prompt without variables
    (v1_dir / "greeting.md").write_text("Hello, welcome to PratikoAI!", encoding="utf-8")

    # Prompt with variables
    (v1_dir / "response.md").write_text("User asked: {query}\nContext: {context}\nPlease respond.", encoding="utf-8")

    # Prompt with single variable
    (v1_dir / "simple.md").write_text("Answer this: {question}", encoding="utf-8")

    # Empty prompt
    (v1_dir / "empty.md").write_text("", encoding="utf-8")

    # Prompt with no placeholders but multiple lines
    (v1_dir / "system.md").write_text("You are a helpful assistant.\nBe concise.", encoding="utf-8")

    # Create v2 directory
    v2_dir = tmp_path / "v2"
    v2_dir.mkdir()
    (v2_dir / "greeting.md").write_text("Ciao, benvenuto su PratikoAI!", encoding="utf-8")

    # Create components directory
    components_dir = tmp_path / "components"
    components_dir.mkdir()
    (components_dir / "disclaimer.md").write_text("DISCLAIMER: This is AI-generated content.", encoding="utf-8")
    (components_dir / "footer.md").write_text("End of response.", encoding="utf-8")

    return tmp_path


@pytest.fixture()
def loader(prompt_dir: Path) -> PromptLoader:
    """Create a PromptLoader instance pointed at the test directory."""
    return PromptLoader(prompts_dir=prompt_dir, version="v1")


class TestPromptLoaderInit:
    """Tests for PromptLoader constructor."""

    def test_init_with_defaults(self, prompt_dir: Path):
        """PromptLoader initializes with provided prompts_dir and default version."""
        loader = PromptLoader(prompts_dir=prompt_dir)
        assert loader.prompts_dir == prompt_dir
        assert loader.version == "v1"
        assert loader._cache == {}

    def test_init_with_custom_version(self, prompt_dir: Path):
        """PromptLoader initializes with custom version."""
        loader = PromptLoader(prompts_dir=prompt_dir, version="v2")
        assert loader.version == "v2"

    def test_init_with_none_prompts_dir_uses_default(self):
        """PromptLoader uses DEFAULT_PROMPTS_DIR when prompts_dir is None."""
        from app.services.prompt_loader import DEFAULT_PROMPTS_DIR

        loader = PromptLoader(prompts_dir=None)
        assert loader.prompts_dir == DEFAULT_PROMPTS_DIR


class TestPromptLoaderLoad:
    """Tests for PromptLoader.load()."""

    def test_load_simple_prompt(self, loader: PromptLoader):
        """load() returns content of an .md file without variables."""
        result = loader.load("greeting")
        assert result == "Hello, welcome to PratikoAI!"

    def test_load_with_variable_substitution(self, loader: PromptLoader):
        """load() substitutes {var} placeholders with provided values."""
        result = loader.load("response", query="What is IRPEF?", context="Tax context")
        assert result == "User asked: What is IRPEF?\nContext: Tax context\nPlease respond."

    def test_load_single_variable(self, loader: PromptLoader):
        """load() substitutes a single variable."""
        result = loader.load("simple", question="How does TFR work?")
        assert result == "Answer this: How does TFR work?"

    def test_load_empty_prompt(self, loader: PromptLoader):
        """load() returns empty string for an empty .md file."""
        result = loader.load("empty")
        assert result == ""

    def test_load_multiline_prompt(self, loader: PromptLoader):
        """load() returns full multiline content."""
        result = loader.load("system")
        assert "You are a helpful assistant." in result
        assert "Be concise." in result

    def test_load_missing_file_raises_file_not_found(self, loader: PromptLoader):
        """load() raises FileNotFoundError for a non-existent prompt."""
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            loader.load("nonexistent")

    def test_load_missing_variable_raises_key_error(self, loader: PromptLoader):
        """load() raises KeyError when a required variable is not provided."""
        with pytest.raises(KeyError, match="query"):
            # response.md requires {query} and {context}, providing only context
            loader.load("response", context="some context")

    def test_load_caches_content(self, loader: PromptLoader):
        """load() caches prompt content after first load."""
        loader.load("greeting")
        assert "v1/greeting" in loader._cache
        assert loader._cache["v1/greeting"] == "Hello, welcome to PratikoAI!"

    def test_load_uses_cache_on_second_call(self, loader: PromptLoader):
        """load() uses cached content on subsequent calls."""
        result1 = loader.load("greeting")
        # Modify the cache to prove it is used
        loader._cache["v1/greeting"] = "CACHED CONTENT"
        result2 = loader.load("greeting")
        assert result1 == "Hello, welcome to PratikoAI!"
        assert result2 == "CACHED CONTENT"

    def test_load_with_extra_variables_ignores_them(self, loader: PromptLoader):
        """load() ignores extra variables not present in the template."""
        result = loader.load("simple", question="Test?", extra_var="unused")
        assert result == "Answer this: Test?"

    def test_load_variable_substitution_converts_to_string(self, loader: PromptLoader):
        """load() converts variable values to strings."""
        result = loader.load("simple", question=42)
        assert result == "Answer this: 42"


class TestPromptLoaderLoadComponent:
    """Tests for PromptLoader.load_component()."""

    def test_load_component_happy_path(self, loader: PromptLoader):
        """load_component() loads a component file from the components/ directory."""
        result = loader.load_component("disclaimer")
        assert result == "DISCLAIMER: This is AI-generated content."

    def test_load_component_caches_content(self, loader: PromptLoader):
        """load_component() caches component content."""
        loader.load_component("disclaimer")
        assert "components/disclaimer" in loader._cache

    def test_load_component_uses_cache(self, loader: PromptLoader):
        """load_component() returns cached content on second call."""
        loader.load_component("footer")
        loader._cache["components/footer"] = "CACHED FOOTER"
        result = loader.load_component("footer")
        assert result == "CACHED FOOTER"

    def test_load_component_missing_raises_file_not_found(self, loader: PromptLoader):
        """load_component() raises FileNotFoundError for missing component."""
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            loader.load_component("nonexistent")


class TestPromptLoaderCompose:
    """Tests for PromptLoader.compose()."""

    def test_compose_multiple_parts(self, loader: PromptLoader):
        """compose() joins multiple parts with default separator."""
        result = loader.compose("Part A", "Part B", "Part C")
        assert result == "Part A\n\n---\n\nPart B\n\n---\n\nPart C"

    def test_compose_custom_separator(self, loader: PromptLoader):
        """compose() uses custom separator."""
        result = loader.compose("Part A", "Part B", separator="\n\n")
        assert result == "Part A\n\nPart B"

    def test_compose_single_part(self, loader: PromptLoader):
        """compose() returns single part unchanged."""
        result = loader.compose("Only Part")
        assert result == "Only Part"

    def test_compose_no_parts(self, loader: PromptLoader):
        """compose() returns empty string when no parts given."""
        result = loader.compose()
        assert result == ""

    def test_compose_with_loaded_prompts(self, loader: PromptLoader):
        """compose() works with content from load() and load_component()."""
        greeting = loader.load("greeting")
        disclaimer = loader.load_component("disclaimer")
        result = loader.compose(greeting, disclaimer, separator="\n")
        assert "Hello, welcome to PratikoAI!" in result
        assert "DISCLAIMER:" in result


class TestPromptLoaderReload:
    """Tests for PromptLoader.reload()."""

    def test_reload_all_clears_entire_cache(self, loader: PromptLoader):
        """reload() with no arguments clears the entire cache."""
        loader.load("greeting")
        loader.load("system")
        assert len(loader._cache) == 2
        loader.reload()
        assert len(loader._cache) == 0

    def test_reload_specific_prompt_clears_only_that_entry(self, loader: PromptLoader):
        """reload(name) clears only the named prompt from cache."""
        loader.load("greeting")
        loader.load("system")
        assert len(loader._cache) == 2
        loader.reload("greeting")
        assert "v1/greeting" not in loader._cache
        assert "v1/system" in loader._cache

    def test_reload_nonexistent_key_does_not_raise(self, loader: PromptLoader):
        """reload() with a non-cached name does not raise."""
        loader.reload("nonexistent")  # Should not raise

    def test_reload_forces_file_reread(self, loader: PromptLoader, prompt_dir: Path):
        """reload() followed by load() rereads from disk."""
        loader.load("greeting")
        # Modify the file on disk
        (prompt_dir / "v1" / "greeting.md").write_text("Updated greeting!", encoding="utf-8")
        # Without reload, cache returns old content
        assert loader.load("greeting") == "Hello, welcome to PratikoAI!"
        # After reload, file is reread
        loader.reload("greeting")
        assert loader.load("greeting") == "Updated greeting!"


class TestPromptLoaderListPrompts:
    """Tests for PromptLoader.list_prompts()."""

    def test_list_prompts_returns_sorted_names(self, loader: PromptLoader):
        """list_prompts() returns sorted list of prompt names without .md extension."""
        result = loader.list_prompts()
        assert result == sorted(["empty", "greeting", "response", "simple", "system"])

    def test_list_prompts_for_nonexistent_version(self, prompt_dir: Path):
        """list_prompts() returns empty list for nonexistent version directory."""
        loader = PromptLoader(prompts_dir=prompt_dir, version="v999")
        result = loader.list_prompts()
        assert result == []

    def test_list_prompts_for_empty_version(self, tmp_path: Path):
        """list_prompts() returns empty list when version directory has no .md files."""
        v1_dir = tmp_path / "v1"
        v1_dir.mkdir()
        loader = PromptLoader(prompts_dir=tmp_path, version="v1")
        result = loader.list_prompts()
        assert result == []


class TestPromptLoaderGetVersion:
    """Tests for PromptLoader.get_version()."""

    def test_get_version_returns_v1_default(self, loader: PromptLoader):
        """get_version() returns default version 'v1'."""
        assert loader.get_version() == "v1"

    def test_get_version_returns_custom_version(self, prompt_dir: Path):
        """get_version() returns the custom version."""
        loader = PromptLoader(prompts_dir=prompt_dir, version="v2")
        assert loader.get_version() == "v2"


class TestPromptLoaderVersionSwitching:
    """Tests for using PromptLoader with different versions."""

    def test_different_versions_load_different_content(self, prompt_dir: Path):
        """Different version loaders return different content for same prompt name."""
        loader_v1 = PromptLoader(prompts_dir=prompt_dir, version="v1")
        loader_v2 = PromptLoader(prompts_dir=prompt_dir, version="v2")
        assert loader_v1.load("greeting") == "Hello, welcome to PratikoAI!"
        assert loader_v2.load("greeting") == "Ciao, benvenuto su PratikoAI!"


class TestGetPromptLoaderSingleton:
    """Tests for get_prompt_loader() singleton factory."""

    def test_get_prompt_loader_returns_prompt_loader(self):
        """get_prompt_loader() returns a PromptLoader instance."""
        with patch("app.services.prompt_loader._default_loader", None):
            loader = get_prompt_loader()
            assert isinstance(loader, PromptLoader)

    def test_get_prompt_loader_returns_same_instance(self):
        """get_prompt_loader() returns the same instance on subsequent calls."""
        with patch("app.services.prompt_loader._default_loader", None):
            loader1 = get_prompt_loader()
            loader2 = get_prompt_loader()
            assert loader1 is loader2

    def test_get_prompt_loader_uses_default_version(self):
        """get_prompt_loader() creates loader with default v1 version."""
        with patch("app.services.prompt_loader._default_loader", None):
            loader = get_prompt_loader()
            assert loader.get_version() == "v1"
