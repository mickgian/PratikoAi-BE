"""Helper utilities for node wrappers."""

from typing import Any, Dict


def ns(state: dict[str, Any], key: str) -> dict[str, Any]:
    """Get or create a nested dict."""
    return state.setdefault(key, {})


def mirror(state: dict[str, Any], key: str, value: Any) -> None:
    """Additively mirror a value to top-level if not None."""
    if value is not None:
        state[key] = value
