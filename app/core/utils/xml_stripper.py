"""XML stripping utility for proactivity content (DEV-201, DEV-250).

Strips <answer> and <suggested_actions> XML tags from LLM responses
before displaying to users. Also strips 📌 caveat blocks that should
not appear inline (DEV-250). The raw tags/caveats should never be visible.

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

# Pattern to match 📌 caveat blocks (DEV-250)
# Matches: 📌 followed by text until double newline, numbered list, or end of string
# This captures multi-line caveats that continue until a blank line or numbered list
# The |\d+\. in lookahead stops at lines starting with "1.", "2.", etc.
CAVEAT_PATTERN = re.compile(
    r"\n*📌[^\n]*(?:\n(?!\n|\d+\.)[^\n]*)*",
    re.MULTILINE,
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


def strip_caveat_blocks(content: str) -> str:
    """Strip 📌 caveat blocks from content (DEV-250).

    Caveats are inline notes added by WebVerificationService that should
    not appear in the chat response. Their sources are already included
    in web_verification_metadata for the Fonti section.

    Example caveats stripped:
        📌 **Nota sui tributi locali:** La definizione agevolata...
        📌 Nota importante: Verifica con il tuo Comune.

    Args:
        content: Raw content that may contain caveat blocks

    Returns:
        Content with caveat blocks removed
    """
    if not content:
        return ""
    return CAVEAT_PATTERN.sub("", content)


def clean_proactivity_content(content: str) -> str:
    """Clean proactivity XML tags and caveats from LLM response content.

    Removes:
    - <answer> and </answer> wrapper tags
    - Entire <suggested_actions>...</suggested_actions> block
    - 📌 caveat blocks (DEV-250)

    Args:
        content: Raw LLM response that may contain proactivity XML tags

    Returns:
        Cleaned content with XML tags and caveats stripped and whitespace trimmed
    """
    if not content:
        return ""

    # Strip answer tags first (they wrap the content)
    result = strip_answer_tags(content)

    # Strip suggested_actions block (appears after answer content)
    result = strip_suggested_actions_block(result)

    # Strip caveat blocks (DEV-250)
    result = strip_caveat_blocks(result)

    # Trim leading/trailing whitespace
    return result.strip()
