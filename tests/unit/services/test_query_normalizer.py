"""TDD Tests for QueryNormalizer Service.

DEV-251 Part 2: Tests for typo correction with conversation context.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.
Coverage Target: 80%+ for new code.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.query_normalizer import QueryNormalizer

# =============================================================================
# Tests: Conversation Context Parameter (DEV-251)
# =============================================================================


class TestConversationContextParameter:
    """Test that QueryNormalizer accepts optional conversation_context parameter."""

    @pytest.mark.asyncio
    async def test_normalize_accepts_conversation_context(self):
        """DEV-251: Normalizer should accept optional conversation_context parameter."""
        normalizer = QueryNormalizer()

        # Mock the OpenAI client to avoid real API calls
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content='{"type": "risoluzione", "number": "64", "year": null, "keywords": []}')
            )
        ]

        with patch.object(
            normalizer.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            # Should not raise TypeError when passing conversation_context
            result = await normalizer.normalize(
                query="e l'rap?",
                conversation_context="user: parlami della rottamazione quinquies",
            )
            assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_normalize_works_without_context(self):
        """DEV-251: Normalizer should work without conversation_context (backward compatible)."""
        normalizer = QueryNormalizer()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content='{"type": "risoluzione", "number": "64", "year": null, "keywords": []}')
            )
        ]

        with patch.object(
            normalizer.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            # Should work without conversation_context parameter
            result = await normalizer.normalize(query="risoluzione 64")
            assert result is not None
            assert result.get("type") == "risoluzione"
            assert result.get("number") == "64"

    @pytest.mark.asyncio
    async def test_normalize_passes_context_to_system_prompt(self):
        """DEV-251: Conversation context should be included in system prompt."""
        normalizer = QueryNormalizer()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"type": null, "number": null, "year": null, "keywords": ["IRAP"]}'))
        ]

        with patch.object(
            normalizer.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_create:
            await normalizer.normalize(
                query="e l'rap?",
                conversation_context="assistant: ...IRAP (Imposta Regionale)...",
            )

            # Verify the system message contains the conversation context
            call_args = mock_create.call_args
            messages = call_args.kwargs.get("messages", call_args[1].get("messages", []))
            system_message = next((m for m in messages if m.get("role") == "system"), None)

            assert system_message is not None
            assert "CONVERSATION CONTEXT" in system_message["content"]
            assert "IRAP" in system_message["content"]


# =============================================================================
# Tests: Typo Correction with Context (DEV-251)
# =============================================================================


class TestTypoCorrectionWithContext:
    """Test typo correction behavior when conversation context is provided."""

    @pytest.mark.asyncio
    async def test_context_enables_typo_correction_rules(self):
        """DEV-251: System prompt should include typo correction rules when context provided."""
        normalizer = QueryNormalizer()

        # Get system prompt with context
        system_prompt = normalizer._get_system_prompt(conversation_context="assistant: IRAP discussion...")

        # Should include typo correction section
        assert "TYPO CORRECTION" in system_prompt or "typo" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_context_not_included_when_none(self):
        """DEV-251: System prompt should NOT include context section when None."""
        normalizer = QueryNormalizer()

        # Get system prompt without context
        system_prompt = normalizer._get_system_prompt(conversation_context=None)

        # Should NOT include conversation context section
        assert "CONVERSATION CONTEXT" not in system_prompt

    def test_get_system_prompt_accepts_conversation_context(self):
        """DEV-251: _get_system_prompt should accept conversation_context parameter."""
        normalizer = QueryNormalizer()

        # Should not raise TypeError
        prompt_with_context = normalizer._get_system_prompt(conversation_context="Test context")
        prompt_without_context = normalizer._get_system_prompt()

        assert isinstance(prompt_with_context, str)
        assert isinstance(prompt_without_context, str)
        # Prompt with context should be longer due to additional section
        assert len(prompt_with_context) > len(prompt_without_context)


# =============================================================================
# Tests: System Prompt Content Validation (DEV-251)
# =============================================================================


class TestSystemPromptContent:
    """Test that system prompt contains correct typo correction instructions."""

    def test_system_prompt_has_typo_correction_examples(self):
        """DEV-251: System prompt with context should have typo correction examples."""
        normalizer = QueryNormalizer()

        system_prompt = normalizer._get_system_prompt(conversation_context="assistant: discussing IRAP tax...")

        # Should mention example typo corrections
        # rap -> IRAP, or similar patterns
        has_typo_mention = (
            "rap" in system_prompt.lower() or "typo" in system_prompt.lower() or "correct" in system_prompt.lower()
        )
        assert has_typo_mention

    def test_system_prompt_has_keyword_guidance(self):
        """System prompt should include keyword extraction guidance."""
        normalizer = QueryNormalizer()

        system_prompt = normalizer._get_system_prompt()

        assert "keywords" in system_prompt.lower()
        assert "json" in system_prompt.lower()


# =============================================================================
# Tests: Error Handling (DEV-251)
# =============================================================================


class TestErrorHandling:
    """Test error handling for conversation context scenarios."""

    @pytest.mark.asyncio
    async def test_empty_context_string_handled(self):
        """DEV-251: Empty string context should be handled gracefully."""
        normalizer = QueryNormalizer()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"type": null, "number": null, "year": null, "keywords": []}'))
        ]

        with patch.object(
            normalizer.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            # Should handle empty string context without error
            result = await normalizer.normalize(query="test query", conversation_context="")
            # Empty string treated as "no context"
            assert result is None or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_whitespace_only_context_handled(self):
        """DEV-251: Whitespace-only context should be handled gracefully."""
        normalizer = QueryNormalizer()

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"type": null, "number": null, "year": null, "keywords": []}'))
        ]

        with patch.object(
            normalizer.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            # Should handle whitespace-only context
            result = await normalizer.normalize(query="test query", conversation_context="   \n  ")
            assert result is None or isinstance(result, dict)
