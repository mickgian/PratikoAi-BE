r"""Guardrail Stream Processor for real-time LLM streaming with safety filtering.

Implements Pattern 3 (Guardrail Streaming): applies per-sentence disclaimer
filtering and PII deanonymization on streaming chunks, then runs full-text
post-processing (section numbering, bold formatting, citation validation)
at finalization.

This preserves PratikoAI's critical safety guardrails (removing "consulta un
esperto" etc.) while enabling real-time token streaming from the LLM provider.

Architecture:
    LLM token stream
        → accumulate until sentence boundary (. ! ? \n)
        → DisclaimerFilter on sentence (<1ms regex)
        → deanonymize PII placeholders (<1ms string replace)
        → emit filtered sentence to client
        → [repeat until stream ends]
        → finalize: SectionNumberingFixer + BoldSectionFormatter on full text
"""

import re
from dataclasses import dataclass

from app.core.logging import logger
from app.core.utils.xml_stripper import strip_answer_tags, strip_caveat_blocks, strip_suggested_actions_block
from app.services.disclaimer_filter import DisclaimerFilter

# Matches sentence-ending punctuation after a letter (not digit).
# This avoids splitting on "1. " numbered list prefixes while still
# splitting on "punto." sentence endings. Digits before !? are allowed (e.g., "22%!").
_SENTENCE_END_AFTER_WORD = re.compile(r"[a-zA-ZÀ-ÿ%\)\"'][.!?]|\d[!?]")

# Common Italian abbreviations that should NOT be treated as sentence endings.
# These appear frequently in fiscal/legal text and cause false splits.
_ITALIAN_ABBREVIATIONS = frozenset(
    {
        "es",
        "ecc",
        "art",
        "artt",
        "co",
        "c",
        "dott",
        "sig",
        "prof",
        "avv",
        "ing",
        "geom",
        "rag",
        "n",
        "nr",
        "pag",
        "fig",
        "tab",
        "cfr",
        "vs",
        "ca",
        "lett",
        "comma",
        "d",
        "l",
        "r",
    }
)


@dataclass
class FinalizeResult:
    """Result of finalize() with full-text and stats."""

    remaining_text: str
    full_text: str
    chunks_processed: int
    disclaimers_removed: int


def _find_split_points(text: str) -> list[int]:
    """Find all positions where the text should be split for emission.

    Returns sorted list of split positions (exclusive end indices).
    """
    splits: list[int] = []

    # Split on newlines
    idx = 0
    while True:
        pos = text.find("\n", idx)
        if pos == -1:
            break
        splits.append(pos + 1)  # Include the newline in the segment
        idx = pos + 1

    # Split on sentence-ending punctuation followed by space (or end of text)
    for m in _SENTENCE_END_AFTER_WORD.finditer(text):
        end = m.end()  # Position after the punctuation char
        # Only split if followed by whitespace or at end of text
        if end >= len(text) or text[end] in (" ", "\t", "\n"):
            # Skip Italian abbreviations (e.g., "es.", "art.", "ecc.")
            # to avoid false sentence splits in legal/fiscal text.
            period_pos = end - 1
            word_start = period_pos - 1
            while word_start >= 0 and text[word_start].isalpha():
                word_start -= 1
            word_start += 1
            word = text[word_start:period_pos].lower()
            if word in _ITALIAN_ABBREVIATIONS:
                continue
            splits.append(end)

    return sorted(set(splits))


class GuardrailStreamProcessor:
    """Processes LLM streaming chunks with per-sentence guardrails.

    Accumulates tokens until a sentence boundary is detected, then applies
    lightweight filters (disclaimer removal, PII deanonymization) before
    emitting. Full-text formatting is applied at finalization.
    """

    def __init__(
        self,
        deanonymization_map: dict[str, str] | None = None,
        max_buffer_chars: int = 500,
    ) -> None:
        self._buffer: str = ""
        self._full_text_parts: list[str] = []
        self._deanonymization_map: dict[str, str] = deanonymization_map or {}
        self._max_buffer_chars: int = max_buffer_chars
        self._chunks_processed: int = 0
        self._disclaimers_removed: int = 0

    def process_chunk(self, chunk: str | None) -> list[str]:
        """Process a streaming chunk and return any complete filtered sentences.

        Args:
            chunk: Raw token(s) from the LLM stream.

        Returns:
            List of filtered sentences ready to emit to client.
            Empty list if no sentence boundary reached yet.
        """
        if not chunk:
            return []

        self._chunks_processed += 1
        self._buffer += chunk
        emitted: list[str] = []

        split_points = _find_split_points(self._buffer)

        if not split_points:
            # No boundaries found — check force-emit threshold
            if len(self._buffer) > self._max_buffer_chars:
                break_pos = self._buffer.rfind(" ", 0, self._max_buffer_chars)
                if break_pos == -1:
                    break_pos = self._max_buffer_chars
                forced = self._buffer[:break_pos]
                self._buffer = self._buffer[break_pos:]
                filtered = self._apply_sentence_guardrails(forced)
                if filtered.strip():
                    emitted.append(filtered)
                    self._full_text_parts.append(filtered)
            return emitted

        # Extract complete segments and keep remainder in buffer
        prev = 0
        for sp in split_points:
            segment = self._buffer[prev:sp]
            prev = sp
            if not segment:
                continue
            if not segment.strip():
                # Yield whitespace-only segments (blank lines) so the frontend
                # can reconstruct proper markdown with paragraph breaks.
                # Without these, "## Header\n\nContent" becomes "## Header\nContent"
                # which breaks markdown rendering when the full text is assembled.
                emitted.append(segment)
                self._full_text_parts.append(segment)
                continue
            filtered = self._apply_sentence_guardrails(segment)
            if filtered.strip():
                emitted.append(filtered)
                self._full_text_parts.append(filtered)

        # Keep the remainder (after last split point) in buffer
        self._buffer = self._buffer[prev:]

        return emitted

    def finalize(self) -> FinalizeResult:
        """Flush remaining buffer and apply full-text post-processing.

        Returns:
            FinalizeResult with remaining text, formatted full text, and stats.
        """
        from app.services.llm_response.bold_section_formatter import BoldSectionFormatter
        from app.services.llm_response.section_numbering_fixer import SectionNumberingFixer

        # Filter and emit remaining buffer
        remaining = ""
        if self._buffer.strip():
            remaining = self._apply_sentence_guardrails(self._buffer)
            if remaining.strip():
                self._full_text_parts.append(remaining)
            self._buffer = ""

        # Reconstruct full text preserving original structure for formatters
        full_text = "".join(self._full_text_parts)
        full_text = SectionNumberingFixer.fix_numbering(full_text) or full_text
        full_text = BoldSectionFormatter.format_sections(full_text) or full_text

        return FinalizeResult(
            remaining_text=remaining,
            full_text=full_text,
            chunks_processed=self._chunks_processed,
            disclaimers_removed=self._disclaimers_removed,
        )

    def _apply_sentence_guardrails(self, text: str) -> str:
        """Apply per-sentence safety filters.

        1. XML tag stripping (<answer>, <suggested_actions>, caveats)
        2. Disclaimer removal (regex, <1ms)
        3. PII deanonymization (string replace, <1ms)
        """
        # Preserve trailing whitespace (newlines) from the segment boundary.
        # DisclaimerFilter.filter_response() calls .strip() which removes trailing
        # newlines, but these are critical for markdown paragraph breaks.
        trailing_ws = ""
        stripped_text = text.rstrip()
        if len(stripped_text) < len(text):
            trailing_ws = text[len(stripped_text) :]

        # 1. Strip XML tags so frontend never sees them (prevents content_cleaned flash)
        # Use individual strippers instead of clean_proactivity_content() to avoid
        # .strip() which would collapse whitespace between streamed segments.
        filtered = stripped_text
        if "<" in filtered:
            filtered = strip_answer_tags(filtered)
            filtered = strip_suggested_actions_block(filtered)
        if "📌" in filtered:
            filtered = strip_caveat_blocks(filtered)

        # 2. Disclaimer filtering
        filtered, removed = DisclaimerFilter.filter_response(filtered)
        if removed:
            self._disclaimers_removed += len(removed)
            logger.debug(
                "guardrail_stream_disclaimer_removed",
                removed_count=len(removed),
                phrases=removed[:3],
            )

        # 2. PII deanonymization
        if self._deanonymization_map:
            for placeholder, original in sorted(
                self._deanonymization_map.items(),
                key=lambda x: len(x[0]),
                reverse=True,
            ):
                filtered = filtered.replace(placeholder, original)

        # Reattach trailing whitespace (newlines) stripped earlier
        return filtered + trailing_ws
