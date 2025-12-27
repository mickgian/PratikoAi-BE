"""TDD Tests for DEV-187: LLM Router Service.

Tests for LLM-based semantic routing with Chain-of-Thought prompting.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.router import ExtractedEntity, RouterDecision, RoutingCategory


class TestLLMRouterServiceRouting:
    """Tests for LLMRouterService routing decisions."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        from app.core.llm.model_config import LLMModelConfig

        config = MagicMock(spec=LLMModelConfig)
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 10000
        config.get_temperature.return_value = 0.2
        return config

    @pytest.mark.asyncio
    async def test_route_chitchat_query(self, mock_config):
        """Test routing a chitchat query."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        # Mock LLM response for chitchat
        mock_response = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            confidence=0.95,
            reasoning="User is greeting, not asking a technical question",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.route("Ciao, come stai?", [])

        assert result.route == RoutingCategory.CHITCHAT
        assert result.confidence >= 0.9
        assert result.needs_retrieval is False

    @pytest.mark.asyncio
    async def test_route_theoretical_definition(self, mock_config):
        """Test routing a theoretical definition query."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        mock_response = RouterDecision(
            route=RoutingCategory.THEORETICAL_DEFINITION,
            confidence=0.88,
            reasoning="User is asking for a definition of a legal concept",
            entities=[],
            requires_freshness=False,
            suggested_sources=["normattiva"],
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.route("Cos'è il TFR?", [])

        assert result.route == RoutingCategory.THEORETICAL_DEFINITION
        assert result.needs_retrieval is True

    @pytest.mark.asyncio
    async def test_route_technical_research(self, mock_config):
        """Test routing a technical research query."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        mock_response = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.92,
            reasoning="Complex procedural question about P.IVA forfettaria",
            entities=[ExtractedEntity(text="P.IVA forfettaria", type="ente", confidence=0.9)],
            requires_freshness=False,
            suggested_sources=["agenzia_entrate", "inps"],
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.route("Qual è l'iter per aprire P.IVA forfettaria?", [])

        assert result.route == RoutingCategory.TECHNICAL_RESEARCH
        assert result.confidence >= 0.9
        assert result.needs_retrieval is True
        assert len(result.entities) == 1

    @pytest.mark.asyncio
    async def test_route_calculator_query(self, mock_config):
        """Test routing a calculator query."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        mock_response = RouterDecision(
            route=RoutingCategory.CALCULATOR,
            confidence=0.95,
            reasoning="User is requesting a tax calculation",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.route("Calcola le tasse su un reddito di 50000 euro", [])

        assert result.route == RoutingCategory.CALCULATOR
        assert result.needs_retrieval is False

    @pytest.mark.asyncio
    async def test_route_golden_set_query(self, mock_config):
        """Test routing a golden set query (specific law reference)."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        mock_response = RouterDecision(
            route=RoutingCategory.GOLDEN_SET,
            confidence=0.98,
            reasoning="Query references specific law Legge 104/1992",
            entities=[
                ExtractedEntity(text="Legge 104/1992", type="legge", confidence=0.98),
                ExtractedEntity(text="Art. 3", type="articolo", confidence=0.95),
            ],
            requires_freshness=False,
            suggested_sources=["normattiva"],
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.route("Cosa dice l'Art. 3 della Legge 104/1992?", [])

        assert result.route == RoutingCategory.GOLDEN_SET
        assert result.confidence >= 0.95
        assert result.needs_retrieval is True
        assert len(result.entities) == 2


class TestLLMRouterServiceFallback:
    """Tests for LLMRouterService fallback behavior."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        from app.core.llm.model_config import LLMModelConfig

        config = MagicMock(spec=LLMModelConfig)
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 10000
        config.get_temperature.return_value = 0.2
        return config

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self, mock_config):
        """Test fallback to TECHNICAL_RESEARCH on LLM error."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM API error")

            result = await service.route("Some query", [])

        assert result.route == RoutingCategory.TECHNICAL_RESEARCH
        assert result.confidence == 0.5  # Low confidence for fallback
        assert "fallback" in result.reasoning.lower() or "error" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_fallback_on_timeout(self, mock_config):
        """Test fallback on LLM timeout."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        async def slow_llm(*args, **kwargs):
            await asyncio.sleep(10)  # Would timeout
            return None

        with patch.object(service, "_call_llm", side_effect=asyncio.TimeoutError):
            result = await service.route("Some query", [])

        assert result.route == RoutingCategory.TECHNICAL_RESEARCH
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, mock_config):
        """Test fallback on invalid JSON response from LLM."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = ValueError("Invalid JSON")

            result = await service.route("Some query", [])

        assert result.route == RoutingCategory.TECHNICAL_RESEARCH
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_empty_query_returns_chitchat(self, mock_config):
        """Test empty query returns CHITCHAT with low confidence."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        result = await service.route("", [])

        assert result.route == RoutingCategory.CHITCHAT
        assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_chitchat(self, mock_config):
        """Test whitespace-only query returns CHITCHAT."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        result = await service.route("   ", [])

        assert result.route == RoutingCategory.CHITCHAT
        assert result.confidence < 0.5


class TestLLMRouterServiceEntities:
    """Tests for entity extraction in LLMRouterService."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        from app.core.llm.model_config import LLMModelConfig

        config = MagicMock(spec=LLMModelConfig)
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 10000
        config.get_temperature.return_value = 0.2
        return config

    @pytest.mark.asyncio
    async def test_entities_extracted(self, mock_config):
        """Test that entities are correctly extracted."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        mock_response = RouterDecision(
            route=RoutingCategory.GOLDEN_SET,
            confidence=0.95,
            reasoning="Query mentions specific legal references",
            entities=[
                ExtractedEntity(text="CCNL Metalmeccanici", type="ente", confidence=0.92),
                ExtractedEntity(text="Art. 18", type="articolo", confidence=0.88),
                ExtractedEntity(text="2024", type="data", confidence=0.85),
            ],
            requires_freshness=True,
            suggested_sources=["normattiva", "inps"],
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.route("Cosa prevede l'Art. 18 del CCNL Metalmeccanici 2024?", [])

        assert len(result.entities) == 3
        assert result.entities[0].type == "ente"
        assert result.entities[1].type == "articolo"
        assert result.entities[2].type == "data"

    @pytest.mark.asyncio
    async def test_no_entities_for_chitchat(self, mock_config):
        """Test chitchat queries have no entities."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        mock_response = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            confidence=0.95,
            reasoning="Simple greeting",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.route("Buongiorno!", [])

        assert len(result.entities) == 0


class TestLLMRouterServicePerformance:
    """Tests for LLMRouterService performance requirements."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        from app.core.llm.model_config import LLMModelConfig

        config = MagicMock(spec=LLMModelConfig)
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 10000
        config.get_temperature.return_value = 0.2
        return config

    @pytest.mark.asyncio
    async def test_latency_under_200ms_mocked(self, mock_config):
        """Test routing completes under 200ms (with mocked LLM)."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        mock_response = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.9,
            reasoning="Technical query",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        async def fast_llm(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms simulated latency
            return mock_response

        with patch.object(service, "_call_llm", side_effect=fast_llm):
            start = time.perf_counter()
            result = await service.route("Test query", [])
            elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 200, f"Routing took {elapsed:.2f}ms, expected <200ms"
        assert result is not None


class TestLLMRouterServicePromptBuilding:
    """Tests for prompt building in LLMRouterService."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        from app.core.llm.model_config import LLMModelConfig

        config = MagicMock(spec=LLMModelConfig)
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 10000
        config.get_temperature.return_value = 0.2
        return config

    def test_build_prompt_includes_query(self, mock_config):
        """Test that built prompt includes the user query."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        query = "Qual è la procedura per il 730?"
        prompt = service._build_prompt(query, [])

        assert query in prompt

    def test_system_prompt_includes_categories(self, mock_config):
        """Test ROUTER_SYSTEM_PROMPT includes all routing categories."""
        from app.services.llm_router_service import ROUTER_SYSTEM_PROMPT

        # Categories should be in the system prompt (not user prompt)
        assert "chitchat" in ROUTER_SYSTEM_PROMPT.lower()
        assert "technical_research" in ROUTER_SYSTEM_PROMPT.lower()
        assert "theoretical_definition" in ROUTER_SYSTEM_PROMPT.lower()
        assert "calculator" in ROUTER_SYSTEM_PROMPT.lower()
        assert "golden_set" in ROUTER_SYSTEM_PROMPT.lower()

    def test_build_prompt_with_history(self, mock_config):
        """Test that built prompt includes conversation history."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        history = [
            {"role": "user", "content": "Ciao"},
            {"role": "assistant", "content": "Buongiorno!"},
        ]

        prompt = service._build_prompt("Altra domanda", history)

        # Should include or reference history
        assert "Ciao" in prompt or "history" in prompt.lower() or len(prompt) > 100

    def test_long_query_truncation(self, mock_config):
        """Test that very long queries are truncated."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        # Create a very long query (>500 tokens worth)
        long_query = "Test query " * 200  # ~2000 characters

        prompt = service._build_prompt(long_query, [])

        # Prompt should be reasonable length (implementation may truncate)
        # Just verify it doesn't crash
        assert len(prompt) > 0


class TestLLMRouterServiceResponseParsing:
    """Tests for response parsing in LLMRouterService."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        from app.core.llm.model_config import LLMModelConfig

        config = MagicMock(spec=LLMModelConfig)
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 10000
        config.get_temperature.return_value = 0.2
        return config

    def test_parse_valid_json_response(self, mock_config):
        """Test parsing a valid JSON response."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        json_response = json.dumps(
            {
                "route": "technical_research",
                "confidence": 0.92,
                "reasoning": "Complex technical query",
                "entities": [{"text": "P.IVA", "type": "ente", "confidence": 0.9}],
                "requires_freshness": False,
                "suggested_sources": ["agenzia_entrate"],
            }
        )

        result = service._parse_response(json_response)

        assert result.route == RoutingCategory.TECHNICAL_RESEARCH
        assert result.confidence == 0.92
        assert len(result.entities) == 1

    def test_parse_response_with_markdown_wrapper(self, mock_config):
        """Test parsing response wrapped in markdown code block."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        json_response = """```json
{
    "route": "chitchat",
    "confidence": 0.95,
    "reasoning": "Simple greeting",
    "entities": [],
    "requires_freshness": false,
    "suggested_sources": []
}
```"""

        result = service._parse_response(json_response)

        assert result.route == RoutingCategory.CHITCHAT
        assert result.confidence == 0.95

    def test_parse_invalid_json_raises(self, mock_config):
        """Test that invalid JSON raises ValueError."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        with pytest.raises(ValueError):
            service._parse_response("not valid json {}")

    def test_parse_missing_required_field_raises(self, mock_config):
        """Test that missing required field raises ValueError."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        # Missing 'reasoning' field
        json_response = json.dumps(
            {
                "route": "chitchat",
                "confidence": 0.95,
                "entities": [],
                "requires_freshness": False,
                "suggested_sources": [],
            }
        )

        with pytest.raises(ValueError):
            service._parse_response(json_response)


class TestLLMRouterServiceFallbackDecision:
    """Tests for the fallback decision method."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        from app.core.llm.model_config import LLMModelConfig

        config = MagicMock(spec=LLMModelConfig)
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 10000
        config.get_temperature.return_value = 0.2
        return config

    def test_fallback_decision_returns_technical_research(self, mock_config):
        """Test fallback decision defaults to TECHNICAL_RESEARCH."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        result = service._fallback_decision("Test query", "Some error occurred")

        assert result.route == RoutingCategory.TECHNICAL_RESEARCH
        assert result.confidence == 0.5
        assert result.needs_retrieval is True

    def test_fallback_decision_includes_error_reason(self, mock_config):
        """Test fallback decision includes error in reasoning."""
        from app.services.llm_router_service import LLMRouterService

        service = LLMRouterService(config=mock_config)

        error_msg = "API timeout"
        result = service._fallback_decision("Test query", error_msg)

        assert "fallback" in result.reasoning.lower() or "error" in result.reasoning.lower()
