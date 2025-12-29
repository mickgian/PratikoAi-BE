"""XML stripping utility for proactivity content (DEV-201).

Strips <answer> and <suggested_actions> XML tags from LLM responses
before displaying to users. The raw XML tags should never be visible.

Usage:
    from app.core.utils.xml_stripper import clean_proactivity_content

    clean_content = clean_proactivity_content(raw_llm_response)
"""

import re

# Pattern to match <answer> and </answer> tags (case insensitive)
ANSWER_TAG_PATTERN = re.compile(r"</?answer>", re.IGNORECASE)

# Pattern to match entire <suggested_actions>...</suggested_actions> block
# Uses DOTALL to match across multiple lines
SUGGESTED_ACTIONS_BLOCK_PATTERN = re.compile(
    r"<suggested_actions>.*?</suggested_actions>",
    re.DOTALL | re.IGNORECASE,
)


def strip_answer_tags(content: str) -> str:
    """Strip <answer> and </answer> tags from content.

    Args:
        content: Raw content that may contain answer tags

    Returns:
        Content with answer tags removed
    """
    return ANSWER_TAG_PATTERN.sub("", content)


def strip_suggested_actions_block(content: str) -> str:
    """Strip entire <suggested_actions>...</suggested_actions> block from content.

    Args:
        content: Raw content that may contain suggested_actions block

    Returns:
        Content with suggested_actions block removed
    """
    return SUGGESTED_ACTIONS_BLOCK_PATTERN.sub("", content)


def clean_proactivity_content(content: str) -> str:
    """Clean proactivity XML tags from LLM response content.

    Removes both:
    - <answer> and </answer> wrapper tags
    - Entire <suggested_actions>...</suggested_actions> block

    Args:
        content: Raw LLM response that may contain proactivity XML tags

    Returns:
        Cleaned content with XML tags stripped and whitespace trimmed
    """
    if not content:
        return ""

    # Strip answer tags first (they wrap the content)
    result = strip_answer_tags(content)

    # Strip suggested_actions block (appears after answer content)
    result = strip_suggested_actions_block(result)

    # Trim leading/trailing whitespace
    return result.strip()
