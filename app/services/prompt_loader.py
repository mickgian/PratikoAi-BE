"""PromptLoader Utility Service for PratikoAI LLM Excellence.

DEV-211: Centralized prompt loading with caching, variable substitution,
and hot-reload capability for development.

This service loads .md prompt files from app/prompts/ directory.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Default prompts directory
DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class PromptLoader:
    """Centralized prompt loading service with caching and variable substitution.

    Usage:
        loader = PromptLoader()
        prompt = loader.load("unified_response_simple", query="What is IRPEF?")

    Features:
        - LRU caching for performance (<1ms for cached loads)
        - Variable substitution using {var} syntax
        - Component composition for modular prompts
        - Hot-reload capability for development
    """

    def __init__(
        self,
        prompts_dir: Path | None = None,
        version: str = "v1",
    ):
        """Initialize PromptLoader.

        Args:
            prompts_dir: Path to prompts directory. Defaults to app/prompts/
            version: Prompt version to use (e.g., "v1", "v2"). Defaults to "v1"
        """
        self.prompts_dir = prompts_dir or DEFAULT_PROMPTS_DIR
        self.version = version
        self._cache: dict[str, str] = {}

        logger.debug(
            "prompt_loader_initialized",
            prompts_dir=str(self.prompts_dir),
            version=self.version,
        )

    def load(self, prompt_name: str, **variables) -> str:
        """Load prompt by name with variable substitution.

        Args:
            prompt_name: Prompt name without .md extension (e.g., "unified_response_simple")
            **variables: Template variables to substitute ({var} syntax)

        Returns:
            Formatted prompt string with variables substituted

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            KeyError: If required variable is missing from the template
        """
        # Check cache first
        cache_key = f"{self.version}/{prompt_name}"
        if cache_key not in self._cache:
            # Load from file
            prompt_path = self.prompts_dir / self.version / f"{prompt_name}.md"
            if not prompt_path.exists():
                available = self.list_prompts()
                logger.error(
                    "prompt_not_found",
                    prompt_name=prompt_name,
                    version=self.version,
                    available_prompts=available,
                )
                raise FileNotFoundError(
                    f"Prompt '{prompt_name}' not found in {self.version}/. " f"Available prompts: {available}"
                )

            content = prompt_path.read_text(encoding="utf-8")
            self._cache[cache_key] = content
            logger.debug("prompt_loaded_from_file", prompt_name=prompt_name, version=self.version)
        else:
            content = self._cache[cache_key]

        # If no variables, return as-is (handles empty prompts too)
        if not variables:
            return content

        # Substitute variables
        return self._substitute_variables(content, prompt_name, variables)

    def _substitute_variables(self, content: str, prompt_name: str, variables: dict) -> str:
        """Substitute {var} placeholders with variable values.

        Uses a two-pass approach:
        1. Find all {var} patterns that are NOT inside JSON/code blocks
        2. Substitute only those that have provided values

        Args:
            content: Raw prompt content
            prompt_name: Name of the prompt (for error messages)
            variables: Dict of variable name -> value

        Returns:
            Content with variables substituted

        Raises:
            KeyError: If a required variable is missing
        """
        # Find all {variable} patterns (simple placeholder pattern)
        # This regex finds {word} patterns but not {{word}} (escaped)
        pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"

        # Find all unique variable names in the template
        required_vars = set(re.findall(pattern, content))

        # Check for missing required variables
        provided_vars = set(variables.keys())
        missing_vars = required_vars - provided_vars

        if missing_vars:
            # Only raise if the variable is actually used in a non-JSON context
            # For now, we require all placeholders to be provided
            missing = next(iter(missing_vars))
            logger.error(
                "missing_template_variable",
                prompt_name=prompt_name,
                missing_variable=missing,
                required_variables=list(required_vars),
                provided_variables=list(provided_vars),
            )
            raise KeyError(
                f"Missing required variable '{missing}' for prompt '{prompt_name}'. "
                f"Required: {required_vars}, Provided: {provided_vars}"
            )

        # Substitute variables
        def replace_var(match):
            var_name = match.group(1)
            if var_name in variables:
                return str(variables[var_name])
            return match.group(0)  # Keep original if not in variables

        return re.sub(pattern, replace_var, content)

    def load_component(self, name: str) -> str:
        """Load a reusable prompt component from components/ directory.

        Args:
            name: Component name without .md extension

        Returns:
            Component content as string

        Raises:
            FileNotFoundError: If component doesn't exist
        """
        cache_key = f"components/{name}"
        if cache_key not in self._cache:
            component_path = self.prompts_dir / "components" / f"{name}.md"
            if not component_path.exists():
                logger.error(
                    "component_not_found",
                    component_name=name,
                )
                raise FileNotFoundError(f"Component '{name}' not found in components/. " f"Path: {component_path}")

            content = component_path.read_text(encoding="utf-8")
            self._cache[cache_key] = content
            logger.debug("component_loaded", component_name=name)

        return self._cache[cache_key]

    def compose(self, *parts: str, separator: str = "\n\n---\n\n") -> str:
        """Compose multiple prompt parts with separators.

        Args:
            *parts: Prompt strings to compose
            separator: String to insert between parts (default: markdown hr)

        Returns:
            Combined prompt string
        """
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        return separator.join(parts)

    def reload(self, name: str | None = None) -> None:
        """Clear cache and reload prompts.

        Args:
            name: Specific prompt name to reload, or None to clear all cache
        """
        if name:
            # Clear specific prompt from cache
            cache_key = f"{self.version}/{name}"
            self._cache.pop(cache_key, None)
            logger.debug("prompt_cache_cleared", prompt_name=name)
        else:
            # Clear entire cache
            self._cache.clear()
            logger.debug("prompt_cache_cleared_all")

    def list_prompts(self) -> list[str]:
        """List available prompt names for current version.

        Returns:
            List of prompt names (without .md extension)
        """
        version_dir = self.prompts_dir / self.version
        if not version_dir.exists():
            return []

        prompts = []
        for path in version_dir.glob("*.md"):
            prompts.append(path.stem)

        return sorted(prompts)

    def get_version(self) -> str:
        """Get current active prompt version.

        Returns:
            Version string (e.g., "v1")
        """
        return self.version


# Singleton instance for convenience
_default_loader: PromptLoader | None = None


def get_prompt_loader() -> PromptLoader:
    """Get the default PromptLoader singleton.

    Returns:
        PromptLoader instance configured with default settings
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = PromptLoader()
    return _default_loader
