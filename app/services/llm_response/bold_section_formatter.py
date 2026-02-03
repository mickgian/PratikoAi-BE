"""DEV-251: Format plain numbered sections to bold markdown.

Transforms LLM responses that use plain numbered sections:
  "1. Scadenze" → "1. **Scadenze**:"

This ensures consistent formatting regardless of LLM behavior.
Industry best practice: Rely on deterministic post-processing for formatting,
let LLM focus on content.
"""

import re

from app.core.logging import logger


class BoldSectionFormatter:
    """Formats plain numbered sections to bold markdown.

    Transforms:
      - "1. Title" → "1. **Title**:"
      - "- Title:" → "- **Title**:"
      - "• Title:" → "• **Title**:"
    """

    # Pattern: "1. Title" at line start (not already bold)
    # Captures: number, title (uppercase start, may include accented chars)
    # Title can contain letters, spaces, slashes, and accented characters
    # Ends at newline OR at colon (existing colon)
    NUMBERED_SECTION_PATTERN = re.compile(
        r"^(\d+)\.\s+"  # "1. " at line start
        r"(?!\*\*)"  # NOT already bold (negative lookahead)
        r"([A-ZÀ-Ù][a-zà-ùA-ZÀ-Ù\s/]+?)"  # Title: uppercase start, non-greedy
        r"(?::?\s*)$",  # Optional colon, optional whitespace, then end of line
        re.MULTILINE,
    )

    # Pattern: "- Title:" or "• Title:" bullet subsection (not already bold)
    # Must have colon after title to distinguish from plain list items
    BULLET_SUBSECTION_PATTERN = re.compile(
        r"^(\s*[-•])\s+"  # Bullet at line start (with optional leading whitespace)
        r"(?!\*\*)"  # NOT already bold
        r"([A-ZÀ-Ù][a-zà-ùA-ZÀ-Ù\s]+)"  # Title: uppercase start
        r":\s*",  # Colon after title (required)
        re.MULTILINE,
    )

    @staticmethod
    def format_sections(response_text: str | None) -> str | None:
        """Format plain sections to bold markdown.

        Args:
            response_text: LLM response text

        Returns:
            Text with bold section titles, or None/empty if input was None/empty
        """
        if response_text is None:
            return None

        if not response_text:
            return response_text

        formatted = response_text

        # Track sections formatted for logging
        sections_formatted = 0

        # Format numbered sections: "1. Title" → "1. **Title**:"
        def format_numbered(match: re.Match[str]) -> str:
            nonlocal sections_formatted
            sections_formatted += 1
            number = match.group(1)
            title = match.group(2).strip()
            return f"{number}. **{title}**:\n"

        formatted = BoldSectionFormatter.NUMBERED_SECTION_PATTERN.sub(format_numbered, formatted)

        # Format bullet subsections: "- Title:" → "- **Title**:"
        bullets_formatted = 0

        def format_bullet(match: re.Match[str]) -> str:
            nonlocal bullets_formatted
            bullets_formatted += 1
            bullet = match.group(1)
            title = match.group(2).strip()
            return f"{bullet} **{title}**: "

        formatted = BoldSectionFormatter.BULLET_SUBSECTION_PATTERN.sub(format_bullet, formatted)

        if sections_formatted > 0 or bullets_formatted > 0:
            logger.info(
                "bold_section_formatting_applied",
                sections_formatted=sections_formatted,
                bullets_formatted=bullets_formatted,
            )

        return formatted
