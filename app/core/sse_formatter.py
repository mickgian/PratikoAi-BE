"""SSE (Server-Sent Events) format utility.

This module provides utilities for formatting and validating Server-Sent Events
to ensure compatibility with EventSource API and prevent format-related bugs.

SSE Format Specification:
- Must start with "data: "
- Must contain valid JSON payload
- Must end with exactly two newlines (\n\n)
- JSON must conform to StreamResponse schema
"""

import json

from app.schemas.chat import StreamResponse


def format_sse_event(response: StreamResponse) -> str:
    """Format a StreamResponse as a valid SSE event with validation.

    This function ensures that all SSE events follow the correct format:
    1. Starts with "data: "
    2. Contains valid JSON from StreamResponse
    3. Ends with two newlines

    Args:
        response: StreamResponse object to format

    Returns:
        str: Properly formatted SSE event string

    Raises:
        ValueError: If the formatted event fails validation

    Example:
        >>> response = StreamResponse(content="Hello", done=False)
        >>> event = format_sse_event(response)
        >>> print(event)
        data: {"content":"Hello","done":false}\n\n
    """
    # Serialize to JSON
    json_str = response.model_dump_json()

    # Format as SSE event
    sse_event = f"data: {json_str}\n\n"

    # Validate before returning
    _validate_sse_format(sse_event)

    return sse_event


def format_sse_done() -> str:
    """Format a final 'done' SSE event.

    Returns:
        str: Properly formatted SSE done event

    Example:
        >>> done_event = format_sse_done()
        >>> print(done_event)
        data: {"content":"","done":true}\n\n
    """
    done_response = StreamResponse(content="", done=True)
    return format_sse_event(done_response)


def _validate_sse_format(sse_event: str) -> None:
    """Validate that an SSE event follows the correct format.

    Validates:
    1. Starts with "data: "
    2. Ends with exactly two newlines
    3. Contains valid JSON between
    4. JSON can be parsed as StreamResponse

    Args:
        sse_event: The SSE event string to validate

    Raises:
        ValueError: If validation fails with detailed error message
    """
    # Check starts with "data: "
    if not sse_event.startswith("data: "):
        raise ValueError(f"SSE event must start with 'data: ' but got: {sse_event[:20]!r}")

    # Check ends with exactly two newlines
    if not sse_event.endswith("\n\n"):
        raise ValueError(f"SSE event must end with exactly two newlines but got: {sse_event[-10:]!r}")

    # Extract JSON payload
    # Format is: "data: <json>\n\n"
    json_start = len("data: ")
    json_end = len(sse_event) - 2  # Remove trailing \n\n
    json_str = sse_event[json_start:json_end]

    # Validate JSON is parseable
    try:
        json_obj = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"SSE event contains invalid JSON: {e}. JSON was: {json_str[:100]!r}")

    # Validate JSON conforms to StreamResponse schema
    try:
        StreamResponse(**json_obj)
    except Exception as e:
        raise ValueError(f"SSE event JSON does not conform to StreamResponse schema: {e}. " f"JSON was: {json_obj}")


def is_valid_sse_event(sse_event: str) -> bool:
    """Check if a string is a valid SSE event.

    Args:
        sse_event: String to validate

    Returns:
        bool: True if valid SSE event, False otherwise
    """
    try:
        _validate_sse_format(sse_event)
        return True
    except ValueError:
        return False


def extract_content_from_sse(sse_event: str) -> str:
    """Extract content from an SSE event.

    Args:
        sse_event: Valid SSE event string

    Returns:
        str: The content field from the StreamResponse

    Raises:
        ValueError: If SSE event is invalid

    Example:
        >>> event = 'data: {"content":"Hello","done":false}\\n\\n'
        >>> content = extract_content_from_sse(event)
        >>> print(content)
        Hello
    """
    _validate_sse_format(sse_event)

    # Extract JSON
    json_start = len("data: ")
    json_end = len(sse_event) - 2
    json_str = sse_event[json_start:json_end]

    # Parse and extract content
    json_obj = json.loads(json_str)
    return json_obj.get("content", "")


def is_done_event(sse_event: str) -> bool:
    """Check if an SSE event is a 'done' event.

    Args:
        sse_event: SSE event string (may be valid or invalid)

    Returns:
        bool: True if this is a done event (done=true), False otherwise (including invalid events)
    """
    # SSE comments (starting with :) are not done events
    if sse_event.startswith(":"):
        return False

    # Invalid events that don't start with data: are not done events
    if not sse_event.startswith("data: "):
        return False

    # Validate format - if invalid, return False
    try:
        _validate_sse_format(sse_event)
    except ValueError:
        return False

    # Extract JSON
    json_start = len("data: ")
    json_end = len(sse_event) - 2
    json_str = sse_event[json_start:json_end]

    # Parse and check done flag
    try:
        json_obj = json.loads(json_str)
        return json_obj.get("done", False)
    except Exception:
        return False
