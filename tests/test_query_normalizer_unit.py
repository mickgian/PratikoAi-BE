"""
TDD RED Phase 2-1: Unit tests for QueryNormalizer

These tests validate LLM-based query normalization functionality:
- Written numbers → digits ("sessantaquattro" → "64")
- Abbreviations → full words ("ris" → "risoluzione")
- Typos → correct spelling ("risouzione" → "risoluzione")
- Word order variations ("la 64" → document reference)
- Non-document queries → None
- LLM timeout/error handling

Expected: ALL tests will FAIL before implementation (QueryNormalizer doesn't exist)
"""

import json
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest

# This import will fail initially - that's expected for RED phase!
# from app.services.query_normalizer import QueryNormalizer


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""

    def _create_response(doc_type: str, doc_number: str):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"type": doc_type, "number": doc_number})
        return mock_response

    return _create_response


@pytest.mark.asyncio
async def test_normalizer_handles_written_numbers(mock_openai_response):
    """
    EXPECTED: FAIL (QueryNormalizer not implemented)
    Test: "risoluzione sessantaquattro" → {"type": "risoluzione", "number": "64"}

    LLM should convert Italian written numbers to digits.
    """
    # Will fail because QueryNormalizer doesn't exist yet
    try:
        from app.services.query_normalizer import QueryNormalizer

        normalizer = QueryNormalizer()

        # Mock LLM to return expected result (must use AsyncMock for async methods)
        mock_create = AsyncMock(return_value=mock_openai_response("risoluzione", "64"))
        with patch.object(normalizer.client.chat.completions, "create", mock_create):
            result = await normalizer.normalize("risoluzione sessantaquattro")

            assert result is not None, "Should return a result for document query"
            assert result["type"] == "risoluzione", "Should extract document type"
            assert result["number"] == "64", "Should convert 'sessantaquattro' to '64'"
    except ImportError:
        pytest.fail("QueryNormalizer class does not exist yet (expected in RED phase)")


@pytest.mark.asyncio
async def test_normalizer_handles_abbreviations(mock_openai_response):
    """
    EXPECTED: FAIL (QueryNormalizer not implemented)
    Test: "ris 64" → {"type": "risoluzione", "number": "64"}

    LLM should expand abbreviations to full document types.
    """
    try:
        from app.services.query_normalizer import QueryNormalizer

        normalizer = QueryNormalizer()

        mock_create = AsyncMock(return_value=mock_openai_response("risoluzione", "64"))
        with patch.object(normalizer.client.chat.completions, "create", mock_create):
            result = await normalizer.normalize("ris 64")

            assert result is not None
            assert result["type"] == "risoluzione", "Should expand 'ris' to 'risoluzione'"
            assert result["number"] == "64"
    except ImportError:
        pytest.fail("QueryNormalizer class does not exist yet (expected in RED phase)")


@pytest.mark.asyncio
async def test_normalizer_handles_any_typo(mock_openai_response):
    """
    EXPECTED: FAIL (QueryNormalizer not implemented)
    Test: "risouzione 64" → {"type": "risoluzione", "number": "64"}

    LLM should correct typos that regex can't catch.
    """
    try:
        from app.services.query_normalizer import QueryNormalizer

        normalizer = QueryNormalizer()

        mock_create = AsyncMock(return_value=mock_openai_response("risoluzione", "64"))
        with patch.object(normalizer.client.chat.completions, "create", mock_create):
            result = await normalizer.normalize("risouzione 64")  # Missing 'luz'

            assert result is not None
            assert result["type"] == "risoluzione", "Should correct typo 'risouzione'"
            assert result["number"] == "64"
    except ImportError:
        pytest.fail("QueryNormalizer class does not exist yet (expected in RED phase)")


@pytest.mark.asyncio
async def test_normalizer_handles_word_order_variation(mock_openai_response):
    """
    EXPECTED: FAIL (QueryNormalizer not implemented)
    Test: "cosa dice la 64?" → {"type": "risoluzione", "number": "64"}

    LLM should extract document reference even with unusual word order.
    """
    try:
        from app.services.query_normalizer import QueryNormalizer

        normalizer = QueryNormalizer()

        # LLM infers "risoluzione" from context (common Italian tax documents)
        mock_create = AsyncMock(return_value=mock_openai_response("risoluzione", "64"))
        with patch.object(normalizer.client.chat.completions, "create", mock_create):
            result = await normalizer.normalize("cosa dice la 64?")

            assert result is not None
            assert result["number"] == "64", "Should extract number even without document type"
    except ImportError:
        pytest.fail("QueryNormalizer class does not exist yet (expected in RED phase)")


@pytest.mark.asyncio
async def test_normalizer_returns_none_for_non_document_query():
    """
    EXPECTED: FAIL (QueryNormalizer not implemented)
    Test: "come calcolare le tasse" → None

    LLM should return None for generic queries (no document reference).
    """
    try:
        from app.services.query_normalizer import QueryNormalizer

        normalizer = QueryNormalizer()

        # Mock LLM to return null type (no document found)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"type": None})

        mock_create = AsyncMock(return_value=mock_response)
        with patch.object(normalizer.client.chat.completions, "create", mock_create):
            result = await normalizer.normalize("come calcolare le tasse")

            assert result is None, "Should return None for non-document query"
    except ImportError:
        pytest.fail("QueryNormalizer class does not exist yet (expected in RED phase)")


@pytest.mark.asyncio
async def test_normalizer_handles_llm_timeout_gracefully():
    """
    EXPECTED: FAIL (QueryNormalizer not implemented)
    Test: LLM timeout → returns None without crashing

    System should degrade gracefully if LLM fails.
    """
    try:
        from app.services.query_normalizer import QueryNormalizer

        normalizer = QueryNormalizer()

        # Mock LLM to raise timeout exception
        mock_create = AsyncMock(side_effect=TimeoutError("LLM timeout"))
        with patch.object(normalizer.client.chat.completions, "create", mock_create):
            result = await normalizer.normalize("risoluzione 64")

            # Should return None, not crash
            assert result is None, "Should return None on LLM timeout (graceful degradation)"
    except ImportError:
        pytest.fail("QueryNormalizer class does not exist yet (expected in RED phase)")


@pytest.mark.asyncio
async def test_normalizer_handles_invalid_json_response():
    """
    EXPECTED: FAIL (QueryNormalizer not implemented)
    Test: LLM returns invalid JSON → returns None

    System should handle malformed LLM responses gracefully.
    """
    try:
        from app.services.query_normalizer import QueryNormalizer

        normalizer = QueryNormalizer()

        # Mock LLM to return invalid JSON
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not JSON"

        mock_create = AsyncMock(return_value=mock_response)
        with patch.object(normalizer.client.chat.completions, "create", mock_create):
            result = await normalizer.normalize("risoluzione 64")

            assert result is None, "Should return None for invalid JSON (graceful degradation)"
    except ImportError:
        pytest.fail("QueryNormalizer class does not exist yet (expected in RED phase)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
