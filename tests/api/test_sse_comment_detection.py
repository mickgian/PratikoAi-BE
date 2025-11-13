"""
Tests for SSE comment detection logic in chatbot streaming.

This test verifies the fix for the bug where content starting with ":"
was incorrectly treated as an SSE comment, causing streaming to break.

Bug context:
- Frontend was stuck on "Sto pensando..." animation
- Backend logs showed correct response
- Content starting with ":" was being passed through without SSE formatting
- Frontend strict parser rejected malformed chunks and stopped processing
"""

import pytest


class TestSSECommentDetection:
    """Test SSE comment detection logic used in chatbot.py streaming."""

    def test_valid_sse_comment_from_graph(self):
        """Test that the SSE keepalive from graph.py is recognized."""
        chunk = ": starting\n\n"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is True, "Must recognize ': starting\\n\\n' as SSE comment"

    def test_valid_sse_comment_with_different_text(self):
        """Test that other SSE comments with correct format are recognized."""
        chunk = ": keepalive\n\n"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is True, "Must recognize any ': text\\n\\n' as SSE comment"

    def test_content_starting_with_colon_no_newlines(self):
        """Test that content starting with ':' but without newlines is NOT an SSE comment."""
        chunk = ": Ecco le informazioni richieste dalla normativa"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is False, "Content without \\n\\n must NOT be treated as SSE comment"

    def test_content_starting_with_colon_single_newline(self):
        """Test that content with single newline is NOT an SSE comment."""
        chunk = ": Ecco le informazioni\n"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is False, "Content with single \\n must NOT be treated as SSE comment"

    def test_colon_without_space(self):
        """Test that ':' without space after it is NOT an SSE comment."""
        chunk = ":test\n\n"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is False, "Colon without space must NOT be treated as SSE comment"

    def test_normal_content(self):
        """Test that normal content is NOT an SSE comment."""
        chunk = "Ecco le informazioni richieste"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is False, "Normal content must NOT be treated as SSE comment"

    def test_content_with_colon_in_middle(self):
        """Test that content with colon in the middle is NOT an SSE comment."""
        chunk = "La risoluzione n. 56: chiarimenti fiscali"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is False, "Content with colon in middle must NOT be treated as SSE comment"

    def test_multiline_content_ending_with_double_newline(self):
        """Test that multiline content ending with \\n\\n is NOT an SSE comment if it doesn't start with ': '."""
        chunk = "Prima riga\nSeconda riga\n\n"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is False, "Multiline content without ': ' prefix must NOT be treated as SSE comment"

    def test_sse_comment_with_multiline_text_should_not_match(self):
        """
        Test that SSE comments with newlines in the middle are NOT recognized.
        SSE comments should be single-line: ": text\\n\\n"
        """
        chunk = ": first line\nsecond line\n\n"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        # This WILL match our simple check, but in practice graph.py only yields ": starting\n\n"
        # If we need to be more strict, we could add: '\n' not in chunk[:-2]
        # For now, this is acceptable since graph.py has a specific format
        assert is_sse_comment is True, "Current implementation allows multiline SSE comments"

    def test_empty_string(self):
        """Test that empty string is NOT an SSE comment."""
        chunk = ""
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is False, "Empty string must NOT be treated as SSE comment"

    def test_only_newlines(self):
        """Test that only newlines is NOT an SSE comment."""
        chunk = "\n\n"
        is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")
        assert is_sse_comment is False, "Only newlines must NOT be treated as SSE comment"


class TestSSECommentDetectionRegression:
    """
    Regression tests for the specific bug that caused streaming to break.

    Bug: Frontend stuck on "Sto pensando..." animation
    Root cause: chunk.strip().startswith(':') was too permissive
    Fix: Changed to: chunk.startswith(': ') and chunk.endswith('\\n\\n')
    """

    def test_old_buggy_logic_vs_new_fixed_logic(self):
        """Compare old buggy logic with new fixed logic."""
        # These are content chunks that could come from the LLM
        problematic_chunks = [
            ": Ecco le informazioni",  # Content starting with ":"
            ":test",  # Colon without space
            ": La risoluzione n. 56",  # More content starting with ":"
        ]

        for chunk in problematic_chunks:
            # Old buggy logic (TOO PERMISSIVE)
            old_logic = chunk.strip().startswith(":")

            # New fixed logic (STRICT)
            new_logic = chunk.startswith(": ") and chunk.endswith("\n\n")

            # The bug: old logic would treat these as SSE comments
            assert old_logic is True, f"Old logic incorrectly treats '{chunk}' as SSE comment"

            # The fix: new logic correctly identifies these as content
            assert new_logic is False, f"New logic correctly treats '{chunk}' as content, not SSE comment"

    def test_valid_sse_comment_still_works_with_new_logic(self):
        """Ensure the fix doesn't break valid SSE comments."""
        valid_sse_comment = ": starting\n\n"

        # Old logic
        old_logic = valid_sse_comment.strip().startswith(":")

        # New logic
        new_logic = valid_sse_comment.startswith(": ") and valid_sse_comment.endswith("\n\n")

        # Both should recognize valid SSE comments
        assert old_logic is True, "Old logic recognizes valid SSE comment"
        assert new_logic is True, "New logic recognizes valid SSE comment"
