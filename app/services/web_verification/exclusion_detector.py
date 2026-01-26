"""Exclusion detection for web verification.

DEV-245 Phase 5.14: Detects genuine exclusions in web content to determine
whether to use checkmark/cross format in synthesis prompts.
"""

from .constants import EXCLUSION_KEYWORDS


def _web_has_genuine_exclusions(web_results: list[dict]) -> tuple[bool, list[str]]:
    """DEV-245 Phase 5.14: Check if web results contain genuine exclusion content.

    Used to determine whether to use checkmark/cross format in synthesis prompts.
    Only use the inclusion/exclusion format when web results ACTUALLY contain
    exclusion keywords, not for general informational queries.

    Args:
        web_results: List of web search results with snippets

    Returns:
        Tuple of (has_exclusions: bool, matched_keywords: list[str])
    """
    matched: list[str] = []
    for result in web_results:
        snippet = result.get("snippet", "").lower()
        for keyword in EXCLUSION_KEYWORDS:
            if keyword in snippet:
                matched.append(keyword)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_matched: list[str] = []
    for kw in matched:
        if kw not in seen:
            seen.add(kw)
            unique_matched.append(kw)

    return (len(unique_matched) > 0, unique_matched)
