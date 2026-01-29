"""DEV-250: Fix repeated section numbering in markdown responses.

The LLM sometimes ignores prompt instructions about sequential numbering,
producing responses where all section headers show "## 1." instead of
"## 1., ## 2., ## 3., ## 4.".

This post-processor fixes the numbering programmatically.
"""

import re

from app.core.logging import logger


class SectionNumberingFixer:
    """Fixes repeated markdown section numbers (## 1. → ## 1., ## 2., ## 3.)."""

    # Pattern matches: ## 1. or ### 1. at start of line
    # Captures: (hashes) (number) (rest of line)
    HEADER_PATTERN = re.compile(r"^(#{2,3})\s+\d+\.\s+", re.MULTILINE)

    # Pattern for plain numbered lists with ANY emphasis format at LINE START:
    # - 1. Title (plain)
    # - 1. **Title** (asterisk bold)
    # - 1. __Title__ (underscore bold)
    # - 1. _Title_ (underscore italic)
    # - 1. *Title* (asterisk italic)
    # Must be followed by uppercase letter (to distinguish from regular list items)
    PLAIN_LIST_PATTERN = re.compile(
        r"^(\d+)\.\s+"  # Number + dot + whitespace
        r"((?:\*\*|__|_|\*)?)"  # Optional emphasis opener: ** __ _ *
        r"([A-Z])"  # Uppercase letter (section start indicator)
    )

    # Pattern for bold numbered sections: "**1.** Title" at line start
    BOLD_PATTERN = re.compile(r"^(\*\*)\d+\.(\*\*)\s+([A-Z])")

    # DEV-250: Pattern for INLINE bold numbered sections (not at line start)
    # Matches sections that appear after text like "principali: 1. **Ambito"
    # Examples:
    #   - "principali: 1. **Ambito" (inline after colon)
    #   - "content 1. **Benefici" (inline after space)
    # Does NOT match line-start patterns (handled by PLAIN_LIST_PATTERN)
    # IMPORTANT: Use [ \t] not \s - \s matches newlines causing double-processing!
    INLINE_BOLD_SECTION_PATTERN = re.compile(
        r"((?::[ \t]*|[ \t]))"  # Context: colon+space/tab OR space/tab (NOT newline)
        r"(\d+)\.\s+"  # Number + dot + whitespace
        r"(\*\*)"  # Bold markers (REQUIRED - distinguishes from plain lists)
        r"([A-Z])"  # Uppercase first letter
    )

    @staticmethod
    def fix_numbering(response_text: str) -> str:
        """Fix repeated section numbering to be sequential.

        Detects patterns like:
          ## 1. First Section    (markdown headers)
          1. First Section       (plain numbered lists with uppercase)
          1. **First Section**   (bold with asterisks)
          1. __First Section__   (bold with underscores)
          1. _First Section_     (italic with underscore)
          1. *First Section*     (italic with asterisk)
          **1.** First Section   (bold numbered sections)
          text: 1. **Section**   (inline bold sections after colon/space)

        And converts to sequential numbering (1, 2, 3, 4...).

        Args:
            response_text: The LLM response text to fix

        Returns:
            The text with sequential section numbering
        """
        if not response_text:
            return response_text

        # DEV-250: Debug logging to trace numbering corruption
        # Extract existing numbers for comparison
        import re as _re

        existing_inline_numbers = _re.findall(r"(?::\s*|\s)(\d+)\.\s+\*\*[A-Z]", response_text)
        logger.debug(
            "section_numbering_input",
            text_preview=response_text[:500] if response_text else "",
            text_length=len(response_text) if response_text else 0,
            existing_inline_numbers=existing_inline_numbers,
            has_inline_pattern=bool(SectionNumberingFixer.INLINE_BOLD_SECTION_PATTERN.search(response_text)),
        )

        # DEV-250: First, check for inline bold sections (full-text replacement)
        # This handles patterns like "principali: 1. **Ambito" where sections
        # appear inline after colons or spaces, not at line start.
        inline_sections_fixed = 0
        if SectionNumberingFixer.INLINE_BOLD_SECTION_PATTERN.search(response_text):
            inline_counter = [0]

            def replace_inline_bold_section(match: re.Match[str]) -> str:
                inline_counter[0] += 1
                prefix = match.group(1)  # space or colon+space
                bold = match.group(3)  # **
                letter = match.group(4)  # A, B, M, S, etc.
                return f"{prefix}{inline_counter[0]}. {bold}{letter}"

            response_text = SectionNumberingFixer.INLINE_BOLD_SECTION_PATTERN.sub(
                replace_inline_bold_section, response_text
            )
            inline_sections_fixed = inline_counter[0]

            # DEV-250: Log after inline fix
            if inline_sections_fixed > 0:
                result_numbers = _re.findall(r"(?::\s*|\s)(\d+)\.\s+\*\*[A-Z]", response_text)
                logger.info(
                    "section_numbering_inline_fixed",
                    sections_fixed=inline_sections_fixed,
                    result_numbers=result_numbers,
                    result_preview=response_text[:500],
                )

        lines = response_text.split("\n")
        result_lines = []
        header_counter: dict[str, int] = {}  # Track counter per header level (## or ###)
        plain_list_counter = 0
        bold_counter = 0

        for line in lines:
            # Check for markdown headers first (## 1. or ### 1.)
            header_match = SectionNumberingFixer.HEADER_PATTERN.match(line)
            if header_match:
                hashes = header_match.group(1)  # ## or ###

                # Initialize or increment counter for this level
                if hashes not in header_counter:
                    header_counter[hashes] = 1
                else:
                    header_counter[hashes] += 1

                # Replace the number with sequential number
                new_line = SectionNumberingFixer.HEADER_PATTERN.sub(f"{hashes} {header_counter[hashes]}. ", line)
                result_lines.append(new_line)
                continue

            # Check for plain numbered lists (1. Title or 1. **Title** or 1. __Title__ etc.)
            plain_match = SectionNumberingFixer.PLAIN_LIST_PATTERN.match(line)
            if plain_match:
                plain_list_counter += 1
                # Preserve emphasis markers: ** or __ or _ or * or empty
                emphasis = plain_match.group(2) or ""
                title_letter = plain_match.group(3)
                new_line = SectionNumberingFixer.PLAIN_LIST_PATTERN.sub(
                    f"{plain_list_counter}. {emphasis}{title_letter}", line
                )
                result_lines.append(new_line)
                continue

            # Check for bold numbered sections (**1.** Title)
            bold_match = SectionNumberingFixer.BOLD_PATTERN.match(line)
            if bold_match:
                bold_counter += 1
                title_letter = bold_match.group(3)
                new_line = SectionNumberingFixer.BOLD_PATTERN.sub(f"**{bold_counter}.**" + f" {title_letter}", line)
                result_lines.append(new_line)
                continue

            result_lines.append(line)

        fixed_text = "\n".join(result_lines)

        # Log with detailed information about what was fixed
        total_fixed = sum(header_counter.values()) + plain_list_counter + bold_counter + inline_sections_fixed
        if total_fixed > 0:
            # DEV-250: Extract final numbers for verification
            final_inline_numbers = _re.findall(r"(?::\s*|\s)(\d+)\.\s+\*\*[A-Z]", fixed_text)
            logger.info(
                "section_numbering_fixed",
                original_length=len(response_text),
                fixed_length=len(fixed_text),
                headers_fixed=sum(header_counter.values()),
                plain_lists_fixed=plain_list_counter,
                bold_sections_fixed=bold_counter,
                inline_sections_fixed=inline_sections_fixed,
                final_inline_numbers=final_inline_numbers,
            )
        else:
            logger.debug(
                "section_numbering_no_changes",
                reason="no_patterns_matched",
                text_preview=response_text[:200] if response_text else "",
            )

        return fixed_text
