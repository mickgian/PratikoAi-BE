"""
Performance budget helpers for Phase 9 testing.

Provides configurable performance budgets via environment variables
or pytest CLI options. Budgets are generous to avoid flaky tests.
"""

import os
from typing import Optional


# Default budgets in milliseconds (generous to avoid flakes)
DEFAULT_BUDGETS = {
    "CACHE": 25,      # Cache lookup/store operations
    "LLM": 400,       # LLM call wrapper overhead
    "TOOLS": 200,     # Tool execution wrapper overhead
    "STREAM": 150,    # Streaming setup/write operations
    "PROVIDER": 50,   # Provider selection/routing
    "PRIVACY": 30,    # Privacy checks
    "GOLDEN": 40,     # Golden lookup/matching
}


def get_budget(budget_name: str, default: Optional[int] = None) -> int:
    """
    Get performance budget from environment or use default.

    Args:
        budget_name: Budget name (CACHE, LLM, TOOLS, etc.)
        default: Optional default value override

    Returns:
        Budget value in milliseconds

    Environment variables checked:
        RAG_BUDGET_P95_<NAME>_MS (e.g., RAG_BUDGET_P95_CACHE_MS)
    """
    env_var = f"RAG_BUDGET_P95_{budget_name.upper()}_MS"
    env_value = os.getenv(env_var)

    if env_value is not None:
        try:
            return int(env_value)
        except ValueError:
            pass

    if default is not None:
        return default

    return DEFAULT_BUDGETS.get(budget_name.upper(), 100)


def assert_within_budget(actual_ms: float, budget_ms: int, label: str) -> None:
    """
    Assert that actual time is within budget.

    Args:
        actual_ms: Actual time in milliseconds
        budget_ms: Budget limit in milliseconds
        label: Descriptive label for error message

    Raises:
        AssertionError: If actual exceeds budget
    """
    assert actual_ms <= budget_ms, (
        f"Performance budget exceeded for {label}:\n"
        f"  Actual:  {actual_ms:.2f} ms\n"
        f"  Budget:  {budget_ms} ms\n"
        f"  Overrun: {actual_ms - budget_ms:.2f} ms ({((actual_ms / budget_ms - 1) * 100):.1f}%)"
    )


def calculate_p95(durations: list[float]) -> float:
    """
    Calculate P95 (95th percentile) from a list of durations.

    Args:
        durations: List of duration values in milliseconds

    Returns:
        P95 value in milliseconds
    """
    if not durations:
        return 0.0

    sorted_durations = sorted(durations)
    index = int(len(sorted_durations) * 0.95)

    # Handle edge case where index is at the end
    if index >= len(sorted_durations):
        index = len(sorted_durations) - 1

    return sorted_durations[index]


def should_skip_perf_tests() -> bool:
    """
    Check if performance tests should be skipped.

    Returns:
        True if RAG_SKIP_PERF=1 is set

    Usage in tests:
        @pytest.mark.skipif(should_skip_perf_tests(), reason="Performance tests disabled")
    """
    return os.getenv("RAG_SKIP_PERF", "0") == "1"


class PerformanceBudget:
    """
    Context manager for tracking execution time against a budget.

    Usage:
        with PerformanceBudget("cache_check", get_budget("CACHE")) as perf:
            # ... code to measure ...
            pass
        # Automatically asserts within budget on exit
    """

    def __init__(self, label: str, budget_ms: int):
        self.label = label
        self.budget_ms = budget_ms
        self.start_ns: Optional[int] = None
        self.duration_ms: Optional[float] = None

    def __enter__(self):
        import time
        self.start_ns = time.perf_counter_ns()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Don't check budget if an exception occurred
            return False

        import time
        end_ns = time.perf_counter_ns()
        self.duration_ms = (end_ns - self.start_ns) / 1_000_000  # Convert to ms

        assert_within_budget(self.duration_ms, self.budget_ms, self.label)
        return False


# Convenience budget getters

def get_cache_budget() -> int:
    """Get cache operation budget in ms."""
    return get_budget("CACHE")


def get_llm_budget() -> int:
    """Get LLM wrapper budget in ms."""
    return get_budget("LLM")


def get_tools_budget() -> int:
    """Get tools wrapper budget in ms."""
    return get_budget("TOOLS")


def get_stream_budget() -> int:
    """Get streaming budget in ms."""
    return get_budget("STREAM")


def get_provider_budget() -> int:
    """Get provider selection budget in ms."""
    return get_budget("PROVIDER")


def get_privacy_budget() -> int:
    """Get privacy check budget in ms."""
    return get_budget("PRIVACY")


def get_golden_budget() -> int:
    """Get golden lookup budget in ms."""
    return get_budget("GOLDEN")
