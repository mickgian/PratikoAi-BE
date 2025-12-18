"""This file contains the sanitization utilities for the application."""

import html
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)


def sanitize_string(value: str) -> str:
    """Sanitize a string to prevent XSS and other injection attacks.

    Args:
        value: The string to sanitize

    Returns:
        str: The sanitized string
    """
    # Convert to string if not already
    if not isinstance(value, str):
        value = str(value)

    # HTML escape to prevent XSS
    value = html.escape(value)

    # Remove any script tags that might have been escaped
    value = re.sub(r"&lt;script.*?&gt;.*?&lt;/script&gt;", "", value, flags=re.DOTALL)

    # Remove null bytes
    value = value.replace("\0", "")

    return value


def sanitize_email(email: str) -> str:
    """Sanitize an email address.

    Args:
        email: The email address to sanitize

    Returns:
        str: The sanitized email address
    """
    # Basic sanitization
    email = sanitize_string(email)

    # Ensure email format (simple check)
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("Invalid email format")

    return email.lower()


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize all string values in a dictionary.

    Args:
        data: The dictionary to sanitize

    Returns:
        Dict[str, Any]: The sanitized dictionary
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list(value)
        else:
            sanitized[key] = value
    return sanitized


def sanitize_list(data: list[Any]) -> list[Any]:
    """Recursively sanitize all string values in a list.

    Args:
        data: The list to sanitize

    Returns:
        List[Any]: The sanitized list
    """
    sanitized = []
    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_string(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item))
        else:
            sanitized.append(item)
    return sanitized


def sanitize_document_content(text: str) -> str:
    """Sanitize document content to prevent prompt injection attacks.

    DEV-007 Issue 11: This function detects and neutralizes common prompt injection
    patterns that could be embedded in user-uploaded documents to manipulate LLM behavior.

    Args:
        text: The document content to sanitize

    Returns:
        str: The sanitized document content with injection patterns neutralized
    """
    if not text:
        return text

    # Common prompt injection patterns to detect and neutralize
    injection_patterns = [
        # Direct instruction override attempts
        r"ignore\s+(all\s+)?previous\s+instructions?",
        r"disregard\s+(all\s+)?previous\s+(instructions?|context)",
        r"forget\s+(all\s+)?previous\s+(instructions?|context|rules)",
        # Role/mode manipulation
        r"you\s+are\s+now\s+in\s+\w+\s+mode",
        r"switch\s+to\s+\w+\s+mode",
        r"activate\s+\w+\s+mode",
        r"enter\s+(developer|admin|root|debug|jailbreak)\s+mode",
        # System prompt override attempts
        r"system\s*:\s*",
        r"<\s*system\s*>",
        r"\[system\]",
        r"##\s*system\s*prompt",
        # OpenAI special tokens (prevent token manipulation)
        r"<\|.*?\|>",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"<\|endoftext\|>",
        # Claude special sequences
        r"<\|assistant\|>",
        r"<\|human\|>",
        r"\[INST\]",
        r"\[/INST\]",
        # Delimiter manipulation
        r"```+\s*(system|prompt|instruction)",
        r"---+\s*(system|prompt|instruction)",
        # Italian variants (since PratikoAI is for Italian professionals)
        r"ignora\s+(tutte\s+le\s+)?istruzioni\s+precedenti",
        r"dimentica\s+(tutte\s+le\s+)?istruzioni",
    ]

    # Replace detected patterns with sanitized marker
    for pattern in injection_patterns:
        text = re.sub(pattern, "[CONTENUTO_FILTRATO]", text, flags=re.IGNORECASE)

    return text


def validate_password_strength(password: str) -> bool:
    """Validate password strength.

    Args:
        password: The password to validate

    Returns:
        bool: Whether the password is strong enough

    Raises:
        ValueError: If the password is not strong enough with reason
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character")

    return True
