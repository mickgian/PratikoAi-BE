"""Account code generator for user identification in Langfuse.

Generates human-readable account codes in the format: {3_letters}{hundreds}{2_random}-{sequence}
Example: MGI70021-1 (from michele.giannone@gmail.com)

Used as the Langfuse user_id for readable analytics instead of opaque numeric IDs.
"""

import random


def generate_account_code(email: str, sequence: int = 1) -> str:
    """Generate a unique account code from email.

    Format: {first_3_letters}{hundreds}{2_random}-{sequence}
    Example: MGI70021-1 (from michele.giannone@gmail.com)

    Args:
        email: User's email address for prefix extraction.
        sequence: Sequence number appended after the dash. Defaults to 1.

    Returns:
        Account code string, max 20 characters.
    """
    # Extract first 3 alphabetic chars from email local part (before @)
    local_part = email.split("@")[0]
    prefix = "".join(c for c in local_part if c.isalpha())[:3].upper()
    if len(prefix) < 3:
        prefix = prefix.ljust(3, "X")  # Pad with X if needed

    # Random hundreds (200-900)
    hundreds = random.choice([2, 3, 4, 5, 6, 7, 8, 9]) * 100

    # 2 random digits (00-99)
    random_suffix = random.randint(0, 99)

    return f"{prefix}{hundreds}{random_suffix:02d}-{sequence}"
