"""LLM Response Parser for LLM-First proactivity architecture.

DEV-176: Implement parse_llm_response Function

Extracts <answer> and <suggested_actions> from LLM output.
Handles all edge cases gracefully - never raises exceptions.

Reference: PRATIKO_1.5_REFERENCE.md Section 12.5.2
"""

import json
import logging
import re
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Compiled regex patterns for performance
ANSWER_PATTERN = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
ACTIONS_PATTERN = re.compile(
    r"<suggested_actions>\s*(\[.*?\])\s*</suggested_actions>", re.DOTALL
)

# Maximum number of actions to return
MAX_ACTIONS = 4


class SuggestedAction(BaseModel):
    """Single suggested action from LLM response."""

    id: str
    label: str
    icon: str
    prompt: str


class ParsedLLMResponse(BaseModel):
    """Parsed LLM response with answer and suggested actions."""

    answer: str
    suggested_actions: list[SuggestedAction]


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


def _validate_action(action_dict: dict) -> SuggestedAction | None:
    """Validate and create a SuggestedAction from dict.

    Args:
        action_dict: Dictionary with action fields.

    Returns:
        SuggestedAction if valid, None if missing required fields.
    """
    required_fields = {"id", "label", "icon", "prompt"}

    # Check all required fields are present and non-empty
    for field in required_fields:
        if field not in action_dict or not action_dict[field]:
            return None

    try:
        return SuggestedAction(
            id=str(action_dict["id"]),
            label=str(action_dict["label"]),
            icon=str(action_dict["icon"]),
            prompt=str(action_dict["prompt"]),
        )
    except Exception:
        return None


def _extract_actions(raw: str) -> list[SuggestedAction]:
    """Extract suggested actions from raw response.

    Args:
        raw: Raw LLM response string.

    Returns:
        List of valid SuggestedAction objects (max 4).
        Returns empty list on any parsing failure.
    """
    match = ACTIONS_PATTERN.search(raw)
    if not match:
        return []

    try:
        actions_json = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse suggested_actions JSON: %s", e)
        return []

    if not isinstance(actions_json, list):
        logger.warning("suggested_actions is not a list")
        return []

    valid_actions = []
    for action_dict in actions_json:
        if not isinstance(action_dict, dict):
            continue

        action = _validate_action(action_dict)
        if action:
            valid_actions.append(action)

        # Stop at max actions
        if len(valid_actions) >= MAX_ACTIONS:
            break

    return valid_actions


def parse_llm_response(raw_response: str) -> ParsedLLMResponse:
    """Parse LLM response with answer and suggested actions.

    This function NEVER raises exceptions. It handles all edge cases
    gracefully and always returns a valid ParsedLLMResponse.

    Args:
        raw_response: Raw LLM response string with optional <answer>
            and <suggested_actions> XML-like tags.

    Returns:
        ParsedLLMResponse with extracted answer and actions.
        - If no <answer> tag: full response used as answer
        - If no <suggested_actions> tag: empty actions list
        - If malformed JSON: empty actions list
        - If invalid action fields: action skipped
        - Max 4 actions returned
    """
    if not raw_response:
        return ParsedLLMResponse(answer="", suggested_actions=[])

    try:
        answer = _extract_answer(raw_response)
        actions = _extract_actions(raw_response)

        return ParsedLLMResponse(answer=answer, suggested_actions=actions)
    except Exception as e:
        # Catch-all: should never happen, but ensures we never crash
        logger.error("Unexpected error parsing LLM response: %s", e)
        return ParsedLLMResponse(answer=raw_response.strip(), suggested_actions=[])
