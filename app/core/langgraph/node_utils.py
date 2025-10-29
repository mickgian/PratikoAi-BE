"""Helper utilities for node wrappers."""

from typing import Any, Dict


def ns(state: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Get or create a nested dict."""
    return state.setdefault(key, {})


def mirror(state: Dict[str, Any], key: str, value: Any) -> None:
    """Additively mirror a value to top-level if not None."""
    if value is not None:
        state[key] = value
