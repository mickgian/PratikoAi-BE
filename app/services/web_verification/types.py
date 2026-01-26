"""Type definitions for web verification.

Contains the data structures used throughout the web verification module.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContradictionInfo:
    """Information about a detected contradiction between KB and web."""

    topic: str  # What the contradiction is about
    kb_claim: str  # What the KB says
    web_claim: str  # What the web says
    source_url: str  # Web source URL
    source_title: str  # Web source title
    confidence: float  # Confidence in the contradiction (0.0-1.0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "topic": self.topic,
            "kb_claim": self.kb_claim,
            "web_claim": self.web_claim,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "confidence": self.confidence,
        }


@dataclass
class WebVerificationResult:
    """Result of web verification."""

    caveats: list[str] = field(default_factory=list)
    contradictions: list[ContradictionInfo] = field(default_factory=list)
    web_sources_checked: int = 0
    verification_performed: bool = False
    error: str | None = None
    # DEV-245: Brave AI synthesis fields
    brave_ai_summary: str | None = None  # Raw Brave AI summary
    synthesized_response: str | None = None  # LLM-synthesized KB + Brave response

    @property
    def has_synthesized_response(self) -> bool:
        """Check if a synthesized response is available."""
        return self.synthesized_response is not None and len(self.synthesized_response) > 0

    @property
    def has_caveats(self) -> bool:
        """Check if any caveats were generated."""
        return len(self.caveats) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "caveats": self.caveats,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "web_sources_checked": self.web_sources_checked,
            "verification_performed": self.verification_performed,
            "has_caveats": self.has_caveats,
            "error": self.error,
            # DEV-245: Brave AI synthesis fields
            "brave_ai_summary": self.brave_ai_summary,
            "synthesized_response": self.synthesized_response,
            "has_synthesized_response": self.has_synthesized_response,
        }
