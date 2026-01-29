"""JSON and XML extraction and parsing for LLM responses.

Handles extraction of structured responses from various formats:
- XML tags (preferred for DEV-250 - allows free-form writing)
- JSON in markdown code blocks
- Raw JSON objects
"""

import json
import re


def extract_xml_response(content: str) -> dict | None:
    """Extract response from XML tags.

    DEV-250: XML format allows LLM to write naturally within tags,
    avoiding JSON escaping issues and producing better quality responses.

    Expected format:
        <response>
        <reasoning>...</reasoning>
        <answer>...</answer>
        <sources>...</sources>
        </response>

    Or minimal format:
        <answer>...</answer>

    Args:
        content: LLM response content

    Returns:
        Dict with 'answer', 'reasoning' (optional), 'sources_raw' (optional)
        None if no XML tags found
    """
    if not content:
        return None

    result = {}

    # Extract <answer> tag (required)
    answer_pattern = r"<answer>\s*(.*?)\s*</answer>"
    answer_match = re.search(answer_pattern, content, re.DOTALL)
    if answer_match:
        result["answer"] = answer_match.group(1).strip()
    else:
        return None  # answer tag is required

    # Extract <reasoning> tag (optional)
    reasoning_pattern = r"<reasoning>\s*(.*?)\s*</reasoning>"
    reasoning_match = re.search(reasoning_pattern, content, re.DOTALL)
    if reasoning_match:
        result["reasoning"] = reasoning_match.group(1).strip()
    else:
        result["reasoning"] = None

    # Extract <sources> tag (optional, kept as raw text)
    sources_pattern = r"<sources>\s*(.*?)\s*</sources>"
    sources_match = re.search(sources_pattern, content, re.DOTALL)
    if sources_match:
        result["sources_raw"] = sources_match.group(1).strip()
    else:
        result["sources_raw"] = None

    return result


def extract_json_from_content(content: str) -> dict | None:
    """Extract JSON from response that may contain markdown code blocks.

    DEV-214: Handles multiple JSON formats:
    - ```json ... ``` markdown blocks
    - Raw JSON objects
    - JSON with surrounding text

    Args:
        content: LLM response content

    Returns:
        Parsed dict if valid JSON found, None otherwise
    """
    if not content:
        return None

    # Try 1: Extract from markdown ```json ... ``` block
    json_block_pattern = r"```json\s*\n?(.*?)\n?```"
    match = re.search(json_block_pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try 2: Extract from ``` ... ``` block (without json specifier)
    code_block_pattern = r"```\s*\n?(.*?)\n?```"
    match = re.search(code_block_pattern, content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try 3: Find JSON object in content (starts with { ends with })
    # Use greedy matching to find the largest JSON object
    json_object_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = re.findall(json_object_pattern, content, re.DOTALL)
    for potential_json in reversed(matches):  # Try largest matches first
        try:
            return json.loads(potential_json)
        except json.JSONDecodeError:
            continue

    # Try 4: Raw JSON parsing of entire content
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    return None


def parse_unified_response(content: str) -> dict | None:
    """Parse unified response from LLM (XML preferred, JSON fallback).

    DEV-250: Tries XML format first (better response quality),
    then falls back to JSON for backward compatibility.

    Args:
        content: LLM response content

    Returns:
        Parsed dict with reasoning, answer, sources.
        None if parsing fails.
    """
    if not content:
        return None

    # DEV-250: Try XML extraction first (preferred format)
    xml_result = extract_xml_response(content)
    if xml_result is not None:
        return xml_result

    # Fallback: JSON extraction (backward compatibility)
    parsed = extract_json_from_content(content)

    if parsed is None:
        return None

    # Validate that it has at least one expected field
    expected_fields = {"reasoning", "answer", "sources_cited"}
    if not any(field in parsed for field in expected_fields):
        return None

    return parsed
