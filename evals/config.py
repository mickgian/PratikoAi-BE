"""Configuration for evaluation framework.

Provides configuration presets for different evaluation modes:
- PR: Fast code-only graders for blocking merges
- LOCAL: Full evaluation with Ollama for development
- NIGHTLY: Comprehensive with pass^k for regression detection
- WEEKLY: Full suite with extended consistency checks
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RunMode(str, Enum):
    """Evaluation run modes."""

    PR = "pr"  # Fast, code-only, blocks PR merge
    LOCAL = "local"  # Developer machine with Ollama
    NIGHTLY = "nightly"  # Scheduled with pass^k
    WEEKLY = "weekly"  # Extended with full consistency


@dataclass
class EvalConfig:
    """Configuration for evaluation runs.

    Attributes:
        mode: Run mode (PR, LOCAL, NIGHTLY, WEEKLY)
        graders: List of grader types to use ("code", "model")
        use_ollama: Whether to use Ollama for model graders
        ollama_model: Ollama model to use
        fail_threshold: Minimum pass rate to succeed (0.0-1.0)
        k_attempts: Number of attempts for consistency evaluation
        use_pass_all_k: Use pass^k instead of pass@k
        regression_only: Only run regression tests
        categories: Categories to run (None = all)
        report_dir: Directory for report output
        timeout_seconds: Timeout per test case
        verbose: Enable verbose output
        integration_mode: Invoke real system (costs money) vs golden data ($0)
    """

    mode: RunMode = RunMode.LOCAL
    graders: list[str] = field(default_factory=lambda: ["code"])
    use_ollama: bool = False
    ollama_model: str = "mistral:7b-instruct"
    fail_threshold: float = 1.0
    k_attempts: int = 1
    use_pass_all_k: bool = False
    regression_only: bool = False
    categories: list[str] | None = None
    report_dir: Path = field(default_factory=lambda: Path("evals/reports"))  # gitignored
    timeout_seconds: float = 60.0
    verbose: bool = False
    integration_mode: bool = False  # Invoke real system (costs money) vs golden data ($0)


def create_pr_config() -> EvalConfig:
    """Create configuration for PR evaluation.

    Fast, code-only graders that block merge on regression failure.
    Target: <5 minutes, 100% threshold.
    """
    return EvalConfig(
        mode=RunMode.PR,
        graders=["code"],
        use_ollama=False,
        fail_threshold=1.0,  # 100% required for PR
        k_attempts=1,
        use_pass_all_k=False,
        regression_only=True,
        timeout_seconds=30.0,
        verbose=False,
    )


def create_local_config() -> EvalConfig:
    """Create configuration for local development.

    Full evaluation with optional Ollama for model graders.
    For developer use before pushing.
    """
    return EvalConfig(
        mode=RunMode.LOCAL,
        graders=["code", "model"],
        use_ollama=True,
        ollama_model="mistral:7b-instruct",
        fail_threshold=0.9,
        k_attempts=1,
        use_pass_all_k=False,
        regression_only=False,
        timeout_seconds=60.0,
        verbose=True,
    )


def create_nightly_config() -> EvalConfig:
    """Create configuration for nightly evaluation.

    Comprehensive with pass^3 for consistency.
    Scheduled at 2am daily.
    """
    return EvalConfig(
        mode=RunMode.NIGHTLY,
        graders=["code", "model"],
        use_ollama=True,
        ollama_model="mistral:7b-instruct",
        fail_threshold=1.0,
        k_attempts=3,
        use_pass_all_k=True,  # All attempts must pass
        regression_only=False,
        timeout_seconds=120.0,
        verbose=False,
    )


def create_weekly_config() -> EvalConfig:
    """Create configuration for weekly evaluation.

    Extended with pass^5 for production reliability.
    Scheduled Sunday 4am.
    """
    return EvalConfig(
        mode=RunMode.WEEKLY,
        graders=["code", "model"],
        use_ollama=True,
        ollama_model="mistral:7b-instruct",
        fail_threshold=1.0,
        k_attempts=5,
        use_pass_all_k=True,
        regression_only=False,
        timeout_seconds=180.0,
        verbose=False,
    )


def create_fast_config() -> EvalConfig:
    """Create configuration for fast smoke tests.

    Quick check with code graders only.
    Target: <30 seconds.
    """
    return EvalConfig(
        mode=RunMode.LOCAL,
        graders=["code"],
        use_ollama=False,
        fail_threshold=1.0,
        k_attempts=1,
        regression_only=True,
        timeout_seconds=10.0,
        verbose=False,
    )
