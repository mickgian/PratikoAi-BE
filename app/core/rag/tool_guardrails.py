"""Tool calling guardrails for policy-gated autonomy.

This module enforces constraints on tool usage:
- Maximum 1 tool call per turn
- Deduplication of identical tool calls
- Structured logging of tool decisions
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.logging import logger

# Policy constant: maximum tool calls allowed per turn
MAX_TOOL_CALLS_PER_TURN = 1


@dataclass
class ToolDecision:
    """Decision about whether to execute a tool call.

    Attributes:
        should_execute: True if the tool call should be executed
        reason: Human-readable reason for the decision
        tool_name: Name of the tool being evaluated
        tool_call_hash: Hash of the tool call for deduplication
    """

    should_execute: bool
    reason: str
    tool_name: str
    tool_call_hash: str


def _generate_tool_call_key(tool_call: dict[str, Any]) -> str:
    """Generate a unique key for a tool call for deduplication.

    Args:
        tool_call: Tool call dictionary with 'function' containing 'name' and 'arguments'

    Returns:
        Unique string key combining tool name and arguments hash
    """
    if not tool_call or "function" not in tool_call:
        return "unknown|invalid"

    function = tool_call["function"]
    tool_name = function.get("name", "unknown")
    arguments = function.get("arguments", "")

    # Hash the arguments for deduplication
    args_hash = hashlib.sha256(arguments.encode("utf-8")).hexdigest()[:16]

    return f"{tool_name}|{args_hash}"


def should_execute_tool_call(
    prev_calls: list[dict[str, Any]], new_call: dict[str, Any], state: str = "S075"
) -> ToolDecision:
    """Decide if a tool call should be executed based on guardrails.

    Guardrails enforced:
    1. Maximum 1 tool call per turn (MAX_TOOL_CALLS_PER_TURN)
    2. Deduplication - don't execute identical calls

    Args:
        prev_calls: List of previous tool calls in this turn
        new_call: New tool call to evaluate
        state: FSM state for logging (default: S075)

    Returns:
        ToolDecision with should_execute bool and reason

    Examples:
        >>> prev = []
        >>> new = {"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}}
        >>> decision = should_execute_tool_call(prev, new)
        >>> decision.should_execute
        True

        >>> prev = [{"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}}]
        >>> decision = should_execute_tool_call(prev, new)
        >>> decision.should_execute
        False
    """
    # Extract tool name for logging
    tool_name = new_call.get("function", {}).get("name", "unknown")
    new_key = _generate_tool_call_key(new_call)

    # Check 1: Maximum calls per turn
    if len(prev_calls) >= MAX_TOOL_CALLS_PER_TURN:
        decision = ToolDecision(
            should_execute=False,
            reason=f"max_calls_reached:{MAX_TOOL_CALLS_PER_TURN}",
            tool_name=tool_name,
            tool_call_hash=new_key,
        )

        logger.info(
            {
                "event": "tool_decision",
                "state": state,
                "action": "skip",
                "reason": "max_reached",
                "tool_name": tool_name,
                "prev_count": len(prev_calls),
                "max_allowed": MAX_TOOL_CALLS_PER_TURN,
            }
        )

        return decision

    # Check 2: Deduplication
    for prev_call in prev_calls:
        prev_key = _generate_tool_call_key(prev_call)
        if prev_key == new_key:
            decision = ToolDecision(
                should_execute=False, reason="duplicate_call", tool_name=tool_name, tool_call_hash=new_key
            )

            logger.info(
                {
                    "event": "tool_decision",
                    "state": state,
                    "action": "skip",
                    "reason": "duplicate",
                    "tool_name": tool_name,
                    "tool_hash": new_key[:16],
                }
            )

            return decision

    # All checks passed - allow execution
    decision = ToolDecision(
        should_execute=True, reason="passed_guardrails", tool_name=tool_name, tool_call_hash=new_key
    )

    logger.info(
        {
            "event": "tool_decision",
            "state": state,
            "action": "execute",
            "reason": "allowed",
            "tool_name": tool_name,
            "tool_hash": new_key[:16],
            "prev_count": len(prev_calls),
        }
    )

    return decision


def filter_tool_calls(
    tool_calls: list[dict[str, Any]], prev_calls: list[dict[str, Any]] | None = None, state: str = "S075"
) -> list[dict[str, Any]]:
    """Filter a list of tool calls according to guardrails.

    This function processes all tool calls and returns only those that pass
    the guardrails (max 1, no duplicates).

    Args:
        tool_calls: List of tool calls to filter
        prev_calls: Previously executed calls in this turn (optional)
        state: FSM state for logging

    Returns:
        Filtered list of tool calls (max 1 element)
    """
    if not tool_calls:
        return []

    prev = prev_calls or []
    allowed = []

    for tool_call in tool_calls:
        decision = should_execute_tool_call(prev + allowed, tool_call, state)
        if decision.should_execute:
            allowed.append(tool_call)

        # Stop as soon as we hit the limit
        if len(allowed) >= MAX_TOOL_CALLS_PER_TURN:
            break

    if len(tool_calls) > len(allowed):
        logger.warning(
            {
                "event": "tools_filtered",
                "state": state,
                "requested": len(tool_calls),
                "allowed": len(allowed),
                "filtered": len(tool_calls) - len(allowed),
            }
        )

    return allowed
