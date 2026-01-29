"""Type definitions for LLM response processing.

Contains data structures used throughout the llm_response module.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedResponse:
    """Parsed LLM response with reasoning, answer, and sources."""

    reasoning: str | None = None
    answer: str = ""
    sources_cited: list[dict[str, Any]] = field(default_factory=list)
    parse_successful: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "reasoning": self.reasoning,
            "answer": self.answer,
            "sources_cited": self.sources_cited,
            "parse_successful": self.parse_successful,
        }
