"""DEV-331: Tests for CommunicationGenerationTool — LLM communication generation.

TDD RED phase: These tests define the expected behaviour of the LangGraph
tool that generates communication drafts using LLM with regulation context.
"""

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def comm_tool():
    from app.core.langgraph.tools.communication_tool import CommunicationGenerationTool

    return CommunicationGenerationTool()


@pytest.fixture
def regulation_context() -> str:
    """Sample normative / regulation context for draft generation."""
    return "Art. 17 DPR 633/72 — Liquidazione IVA trimestrale. I soggetti trimestrali devono versare l'IVA entro il 16 del secondo mese successivo al trimestre. Scadenza: 16 marzo 2026."


@pytest.fixture
def client_context() -> dict:
    """Sample client profile context for draft generation."""
    return {
        "client_id": 1,
        "nome": "Mario Rossi",
        "tipo_cliente": "ditta_individuale",
        "email": "mario.rossi@example.com",
        "partita_iva": "12345678901",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCommunicationGenerationTool:
    """Test CommunicationGenerationTool LLM draft generation."""

    @pytest.mark.asyncio
    async def test_generate_draft_with_context(
        self,
        comm_tool,
        regulation_context: str,
    ) -> None:
        """Happy path: generate a draft with regulation context."""
        result = await comm_tool.generate(
            regulation_context=regulation_context,
            tone="formale",
        )

        assert result is not None
        assert result.subject
        assert result.content
        assert result.suggested_channel

    @pytest.mark.asyncio
    async def test_generate_draft_with_client(
        self,
        comm_tool,
        regulation_context: str,
        client_context: dict,
    ) -> None:
        """Happy path: generate a draft that includes client-specific info."""
        result = await comm_tool.generate(
            regulation_context=regulation_context,
            client_context=client_context,
            tone="formale",
        )

        assert result is not None
        assert "Mario Rossi" in result.subject or "Mario Rossi" in result.content

    @pytest.mark.asyncio
    async def test_generate_returns_structured_output(
        self,
        comm_tool,
        regulation_context: str,
    ) -> None:
        """Output must be a CommunicationDraft with subject, content, channel."""
        from app.core.langgraph.tools.communication_tool import CommunicationDraft

        result = await comm_tool.generate(
            regulation_context=regulation_context,
            tone="formale",
        )

        assert isinstance(result, CommunicationDraft)
        assert isinstance(result.subject, str)
        assert isinstance(result.content, str)
        assert isinstance(result.suggested_channel, str)
        assert len(result.subject) > 0
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_missing_context_raises(
        self,
        comm_tool,
    ) -> None:
        """Error: calling without required regulation_context must raise ValueError."""
        with pytest.raises(ValueError):
            await comm_tool.generate(
                regulation_context="",
                tone="formale",
            )

    def test_suggest_channel_email_default(self, comm_tool) -> None:
        """Default channel should be email when no phone in context."""
        assert comm_tool._suggest_channel(None) == "email"
        assert comm_tool._suggest_channel({"nome": "Test"}) == "email"

    def test_suggest_channel_whatsapp_with_phone(self, comm_tool) -> None:
        """When client has phone, suggest whatsapp."""
        assert comm_tool._suggest_channel({"phone": "+39123456789"}) == "whatsapp"

    def test_to_tool_definition(self, comm_tool) -> None:
        """Tool definition must have name, description, and parameters."""
        defn = comm_tool.to_tool_definition()
        assert defn["name"] == "generate_communication"
        assert "description" in defn
        assert "parameters" in defn
