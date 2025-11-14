"""Utility functions for LLM message handling."""

from typing import (
    Any,
    Union,
)

from app.schemas.chat import Message


def get_message_role(msg: Union[dict, Message, Any]) -> str:
    """Safely get the role from a message (dict or Message object).

    Args:
        msg: Message as dict or Message object

    Returns:
        The role string ('user', 'assistant', 'system')
    """
    if isinstance(msg, dict):
        return msg.get("role", "")
    return getattr(msg, "role", "")


def get_message_content(msg: Union[dict, Message, Any]) -> str:
    """Safely get the content from a message (dict or Message object).

    Args:
        msg: Message as dict or Message object

    Returns:
        The content string
    """
    if isinstance(msg, dict):
        return msg.get("content", "")
    return getattr(msg, "content", "")
