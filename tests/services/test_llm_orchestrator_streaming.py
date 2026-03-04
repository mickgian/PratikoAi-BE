"""TDD tests for LLMOrchestrator.generate_response_stream().

Tests streaming response generation with guardrail processing.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.llm.base import LLMStreamResponse


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider that yields stream chunks."""
    provider = AsyncMock()

    async def mock_stream(*args, **kwargs):
        chunks = [
            LLMStreamResponse(content="L'aliquota ", done=False, model="gpt-4o", provider="openai"),
            LLMStreamResponse(content="è del 22%.", done=False, model="gpt-4o", provider="openai"),
            LLMStreamResponse(content=" La scadenza", done=False, model="gpt-4o", provider="openai"),
            LLMStreamResponse(content=" è il 30 aprile.", done=False, model="gpt-4o", provider="openai"),
            LLMStreamResponse(content="", done=True, model="gpt-4o", provider="openai"),
        ]
        for chunk in chunks:
            yield chunk

    provider.stream_completion = mock_stream
    return provider


@pytest.fixture
def mock_provider_with_disclaimer():
    """Provider that generates response containing a disclaimer."""
    provider = AsyncMock()

    async def mock_stream(*args, **kwargs):
        chunks = [
            LLMStreamResponse(content="L'IRAP può essere inclusa.", done=False, model="gpt-4o", provider="openai"),
            LLMStreamResponse(
                content=" Consulta un esperto fiscale per conferma.", done=False, model="gpt-4o", provider="openai"
            ),
            LLMStreamResponse(content="", done=True, model="gpt-4o", provider="openai"),
        ]
        for chunk in chunks:
            yield chunk

    provider.stream_completion = mock_stream
    return provider


class TestGenerateResponseStream:
    """Test LLMOrchestrator.generate_response_stream()."""

    @pytest.mark.asyncio
    async def test_yields_filtered_chunks(self, mock_provider):
        """Should yield chunks as sentences are completed."""
        from app.services.llm_orchestrator import LLMOrchestrator, QueryComplexity

        orchestrator = LLMOrchestrator()

        with (
            patch.object(orchestrator, "_get_stream_provider", return_value=mock_provider),
            patch.object(orchestrator, "_build_response_prompt", return_value="test prompt"),
        ):
            chunks = []
            async for chunk in orchestrator.generate_response_stream(
                query="Qual è l'aliquota?",
                kb_context="context",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            ):
                chunks.append(chunk)

            # Should have yielded at least one content chunk
            assert len(chunks) >= 1
            # Combined text should contain the answer
            combined = "".join(chunks)
            assert "22%" in combined
            assert "30 aprile" in combined

    @pytest.mark.asyncio
    async def test_filters_disclaimers_in_stream(self, mock_provider_with_disclaimer):
        """Should remove disclaimers from streamed chunks."""
        from app.services.llm_orchestrator import LLMOrchestrator, QueryComplexity

        orchestrator = LLMOrchestrator()

        with (
            patch.object(orchestrator, "_get_stream_provider", return_value=mock_provider_with_disclaimer),
            patch.object(orchestrator, "_build_response_prompt", return_value="test prompt"),
        ):
            chunks = []
            async for chunk in orchestrator.generate_response_stream(
                query="L'IRAP è inclusa?",
                kb_context="context",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
            ):
                chunks.append(chunk)

            combined = "".join(chunks)
            assert "consulta un esperto" not in combined.lower()
            assert "IRAP" in combined

    @pytest.mark.asyncio
    async def test_deanonymizes_pii_in_stream(self, mock_provider):
        """Should deanonymize PII placeholders during streaming."""
        from app.services.llm_orchestrator import LLMOrchestrator, QueryComplexity

        provider = AsyncMock()

        async def mock_stream(*args, **kwargs):
            chunks = [
                LLMStreamResponse(content="Il contribuente [PERSON_1] deve pagare.", done=False),
                LLMStreamResponse(content="", done=True),
            ]
            for chunk in chunks:
                yield chunk

        provider.stream_completion = mock_stream
        orchestrator = LLMOrchestrator()
        dmap = {"[PERSON_1]": "Mario Rossi"}

        with (
            patch.object(orchestrator, "_get_stream_provider", return_value=provider),
            patch.object(orchestrator, "_build_response_prompt", return_value="test prompt"),
        ):
            chunks = []
            async for chunk in orchestrator.generate_response_stream(
                query="test",
                kb_context="context",
                kb_sources_metadata=[],
                complexity=QueryComplexity.SIMPLE,
                deanonymization_map=dmap,
            ):
                chunks.append(chunk)

            combined = "".join(chunks)
            assert "Mario Rossi" in combined
            assert "[PERSON_1]" not in combined
