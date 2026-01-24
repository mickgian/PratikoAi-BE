"""LLM Response Parser for extracting answer content.

DEV-176: Implement parse_llm_response Function
DEV-245 Phase 5.15: Removed suggested_actions parsing (feature removed per user feedback)

Extracts <answer> content from LLM output.
Handles all edge cases gracefully - never raises exceptions.

Reference: PRATIKO_1.5_REFERENCE.md Section 12.5.2
"""

import logging
import re

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Compiled regex patterns for performance
ANSWER_PATTERN = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
# DEV-245 Phase 5.15: Removed ACTIONS_PATTERN - suggested_actions feature removed


class ParsedLLMResponse(BaseModel):
    """Parsed LLM response with answer content.

    DEV-245 Phase 5.15: suggested_actions field removed per user feedback.
    """

    answer: str


def _extract_answer(raw: str) -> str:
    """Extract answer text from raw response.

    Args:
        raw: Raw LLM response string.

    Returns:
        Extracted answer text, trimmed. If no <answer> tag found,
        returns the full raw response.
    """
    match = ANSWER_PATTERN.search(raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def parse_llm_response(raw_response: str) -> ParsedLLMResponse:
    """Parse LLM response to extract answer content.

    This function NEVER raises exceptions. It handles all edge cases
    gracefully and always returns a valid ParsedLLMResponse.

    DEV-245 Phase 5.15: suggested_actions parsing removed per user feedback.

    Args:
        raw_response: Raw LLM response string with optional <answer>
            XML-like tags.

    Returns:
        ParsedLLMResponse with extracted answer.
        - If no <answer> tag: full response used as answer
    """
    if not raw_response:
        return ParsedLLMResponse(answer="")

    try:
        answer = _extract_answer(raw_response)
        return ParsedLLMResponse(answer=answer)
    except Exception as e:
        # Catch-all: should never happen, but ensures we never crash
        logger.error("Unexpected error parsing LLM response: %s", e)
        return ParsedLLMResponse(answer=raw_response.strip())
