"""TDD Tests for Step 34a: LLM Router Node (DEV-194).

This node integrates LLMRouterService into the RAG pipeline for semantic
query classification. It replaces the regex-based routing with LLM-based
semantic understanding.

DEV-251: Tests updated to mock HFIntentClassifier (now runs before GPT).

Test Strategy:
- Mock LLMRouterService to test node wrapper logic in isolation
- Mock HFIntentClassifier to control HF vs GPT fallback behavior
- Verify routing_decision is correctly stored in state
- Verify state preservation and error handling
- Verify fallback behavior on service errors
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.hf_intent_classifier import IntentResult

# =============================================================================
# Mock database service BEFORE importing any app modules
# This prevents the database connection attempt during module import
# =============================================================================
_mock_db_service = MagicMock()
_mock_db_service.engine = MagicMock()
_mock_db_service.get_session = MagicMock()

# Create a mock module for app.services.database
_mock_db_module = MagicMock()
_mock_db_module.database_service = _mock_db_service
_mock_db_module.DatabaseService = MagicMock(return_value=_mock_db_service)

# Inject the mock into sys.modules BEFORE any imports
sys.modules.setdefault("app.services.database", _mock_db_module)


# Import the node module once at module level to avoid re-import issues
# The actual LLMRouterService will be mocked in each test
from app.core.langgraph.nodes.step_034a__llm_router import node_step_34a  # noqa: E402
from app.schemas.router import ExtractedEntity, RouterDecision, RoutingCategory  # noqa: E402


def _create_low_confidence_hf_mock():
    """Create a mock HF classifier that returns low confidence to force GPT fallback."""
    mock_hf = MagicMock()
    # DEV-251: classify_async is an async method, use AsyncMock for return value
    mock_hf.classify_async = AsyncMock(
        return_value=IntentResult(
            intent="technical_research",
            confidence=0.5,  # Below threshold (0.7), forces GPT fallback
            all_scores={"technical_research": 0.5, "chitchat": 0.2},
        )
    )
    mock_hf.should_fallback_to_gpt.return_value = True
    mock_hf.confidence_threshold = 0.7
    return mock_hf


# =============================================================================
# TestNodeStep34aLLMRouter - Core Functionality Tests
# =============================================================================
class TestNodeStep34aLLMRouter:
    """Tests for Step 34a LLM Router node wrapper."""

    @pytest.mark.asyncio
    async def test_successful_routing_technical_research(self):
        """Test successful routing to TECHNICAL_RESEARCH category via GPT fallback."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.92,
            reasoning="Query asks about P.IVA procedure",
            entities=[ExtractedEntity(text="P.IVA", type="ente", confidence=0.9)],
            requires_freshness=False,
            suggested_sources=["agenzia_entrate"],
        )

        # DEV-251: Mock HF classifier to return low confidence, forcing GPT fallback
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-req-001",
                "user_query": "Come si apre una P.IVA?",
                "messages": [{"role": "user", "content": "Come si apre una P.IVA?"}],
            }

            result = await node_step_34a(state)

            assert "routing_decision" in result
            routing_decision = result["routing_decision"]
            assert routing_decision["route"] == "technical_research"
            assert routing_decision["confidence"] == 0.92
            assert routing_decision["reasoning"] == "Query asks about P.IVA procedure"
            assert routing_decision["needs_retrieval"] is True
            assert len(routing_decision["entities"]) == 1
            assert routing_decision["entities"][0]["text"] == "P.IVA"

    @pytest.mark.asyncio
    async def test_successful_routing_chitchat(self):
        """Test successful routing to CHITCHAT category via GPT fallback."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            confidence=0.95,
            reasoning="Casual greeting detected",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        # DEV-251: Mock HF classifier to return low confidence, forcing GPT fallback
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-chitchat-002",
                "user_query": "Ciao! Come stai?",
                "messages": [{"role": "user", "content": "Ciao! Come stai?"}],
            }

            result = await node_step_34a(state)

            assert result["routing_decision"]["route"] == "chitchat"
            assert result["routing_decision"]["confidence"] == 0.95
            assert result["routing_decision"]["needs_retrieval"] is False

    @pytest.mark.asyncio
    async def test_successful_routing_calculator(self):
        """Test successful routing to CALCULATOR category via GPT fallback."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.CALCULATOR,
            confidence=0.88,
            reasoning="User requesting tax calculation",
            entities=[ExtractedEntity(text="IRPEF", type="imposta", confidence=0.85)],
            requires_freshness=False,
            suggested_sources=["calculators"],
        )

        # DEV-251: Mock HF classifier to return low confidence, forcing GPT fallback
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-calc-003",
                "user_query": "Calcola la mia IRPEF",
                "messages": [{"role": "user", "content": "Calcola la mia IRPEF"}],
            }

            result = await node_step_34a(state)

            assert result["routing_decision"]["route"] == "calculator"
            assert result["routing_decision"]["needs_retrieval"] is False

    @pytest.mark.asyncio
    async def test_successful_routing_normative_reference(self):
        """Test successful routing to NORMATIVE_REFERENCE category via GPT fallback."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.NORMATIVE_REFERENCE,
            confidence=0.96,
            reasoning="Query matches known legal reference pattern",
            entities=[
                ExtractedEntity(text="Art. 53", type="articolo", confidence=0.95),
                ExtractedEntity(text="Costituzione", type="legge", confidence=0.90),
            ],
            requires_freshness=False,
            suggested_sources=["normative_reference", "normattiva"],
        )

        # DEV-251: Mock HF classifier to return low confidence, forcing GPT fallback
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-golden-004",
                "user_query": "Cosa dice l'Art. 53 della Costituzione?",
                "messages": [
                    {
                        "role": "user",
                        "content": "Cosa dice l'Art. 53 della Costituzione?",
                    }
                ],
            }

            result = await node_step_34a(state)

            assert result["routing_decision"]["route"] == "normative_reference"
            assert result["routing_decision"]["confidence"] == 0.96
            assert result["routing_decision"]["needs_retrieval"] is True
            assert len(result["routing_decision"]["entities"]) == 2

    @pytest.mark.asyncio
    async def test_successful_routing_theoretical_definition(self):
        """Test successful routing to THEORETICAL_DEFINITION category via GPT fallback."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.THEORETICAL_DEFINITION,
            confidence=0.89,
            reasoning="User asking for a definition of a fiscal concept",
            entities=[ExtractedEntity(text="cedolare secca", type="concetto", confidence=0.87)],
            requires_freshness=False,
            suggested_sources=["kb_definitions"],
        )

        # DEV-251: Mock HF classifier to return low confidence, forcing GPT fallback
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-theory-005",
                "user_query": "Cos'e la cedolare secca?",
                "messages": [{"role": "user", "content": "Cos'e la cedolare secca?"}],
            }

            result = await node_step_34a(state)

            assert result["routing_decision"]["route"] == "theoretical_definition"
            assert result["routing_decision"]["needs_retrieval"] is True


# =============================================================================
# TestNodeStep34aErrorHandling - Error and Fallback Tests
# =============================================================================
class TestNodeStep34aErrorHandling:
    """Tests for error handling and fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_on_service_error(self):
        """Test fallback to TECHNICAL_RESEARCH when both HF and GPT services fail."""
        mock_service = AsyncMock()
        mock_service.route.side_effect = Exception("LLM service unavailable")

        # DEV-251: Mock HF classifier to also force GPT fallback
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-error-006",
                "user_query": "Test query",
                "messages": [{"role": "user", "content": "Test query"}],
            }

            result = await node_step_34a(state)

            # Should fallback to TECHNICAL_RESEARCH
            assert result["routing_decision"]["route"] == "technical_research"
            assert result["routing_decision"]["confidence"] <= 0.5
            assert "fallback" in result["routing_decision"]["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_handles_missing_user_query_gracefully(self):
        """Test handling when user_query is missing from state."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.5,
            reasoning="No query provided, defaulting",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        # DEV-251: Mock HF classifier
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-no-query-007",
                "messages": [{"role": "user", "content": "Some content"}],
                # user_query is missing
            }

            result = await node_step_34a(state)

            # Should still work, extracting query from messages if needed
            assert "routing_decision" in result


# =============================================================================
# TestNodeStep34aStateManagement - State Preservation Tests
# =============================================================================
class TestNodeStep34aStateManagement:
    """Tests for state preservation and proper data handling."""

    @pytest.mark.asyncio
    async def test_existing_state_preserved(self):
        """Test that existing state fields are preserved after routing."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.85,
            reasoning="Technical query",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        # DEV-251: Mock HF classifier
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-preserve-008",
                "session_id": "session-abc",
                "user_query": "Test query",
                "messages": [{"role": "user", "content": "Test query"}],
                "classification": {"domain": "tax", "action": "query"},
                "existing_data": "should_remain",
            }

            result = await node_step_34a(state)

            # Verify existing state is preserved
            assert result["request_id"] == "test-preserve-008"
            assert result["session_id"] == "session-abc"
            assert result["existing_data"] == "should_remain"
            assert result["classification"] == {"domain": "tax", "action": "query"}
            # And new routing_decision is added
            assert "routing_decision" in result

    @pytest.mark.asyncio
    async def test_conversation_history_passed_to_service(self):
        """Test that conversation history is passed to LLMRouterService."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.85,
            reasoning="Follow-up question",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        conversation_history = [
            {"role": "user", "content": "Cos'e l'IRPEF?"},
            {"role": "assistant", "content": "L'IRPEF e l'Imposta sul Reddito..."},
            {"role": "user", "content": "Come si calcola?"},
        ]

        # DEV-251: Mock HF classifier to force GPT fallback so we can verify GPT call
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-history-009",
                "user_query": "Come si calcola?",
                "messages": conversation_history,
            }

            await node_step_34a(state)

            # Verify service was called with history
            mock_service.route.assert_called_once()
            call_args = mock_service.route.call_args
            assert call_args[1]["history"] == conversation_history

    @pytest.mark.asyncio
    async def test_routing_decision_structure_is_serializable(self):
        """Test that routing_decision is a serializable dict, not Pydantic model."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.85,
            reasoning="Technical query",
            entities=[ExtractedEntity(text="test", type="ente", confidence=0.8)],
            requires_freshness=True,
            suggested_sources=["source1"],
        )

        # DEV-251: Mock HF classifier
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-serialize-010",
                "user_query": "Test",
                "messages": [],
            }

            result = await node_step_34a(state)

            routing_decision = result["routing_decision"]

            # Must be a dict, not Pydantic model (for state serialization)
            assert isinstance(routing_decision, dict)
            assert isinstance(routing_decision["route"], str)
            assert isinstance(routing_decision["confidence"], float)
            assert isinstance(routing_decision["entities"], list)
            if routing_decision["entities"]:
                assert isinstance(routing_decision["entities"][0], dict)


# =============================================================================
# TestNodeStep34aLogging - Observability Tests
# =============================================================================
class TestNodeStep34aLogging:
    """Tests for logging and observability."""

    @pytest.mark.asyncio
    async def test_logs_entry_and_exit(self):
        """Test that node logs entry and exit events."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            confidence=0.9,
            reasoning="Test",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        # DEV-251: Mock HF classifier
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
            patch("app.core.langgraph.nodes.step_034a__llm_router.rag_step_log") as mock_log,
        ):
            state = {
                "request_id": "test-log-011",
                "user_query": "Hello",
                "messages": [],
            }

            await node_step_34a(state)

            # Verify logging calls
            assert mock_log.call_count >= 2  # At least enter and exit
            # Check first call is "enter"
            first_call = mock_log.call_args_list[0]
            assert "34a" in str(first_call) or first_call[0][1] == "enter"

    @pytest.mark.asyncio
    async def test_timer_context_manager_used(self):
        """Test that timing context manager is used."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            confidence=0.9,
            reasoning="Test",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        mock_timer = MagicMock()
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock(return_value=None)

        # DEV-251: Mock HF classifier
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
            patch(
                "app.core.langgraph.nodes.step_034a__llm_router.rag_step_timer",
                mock_timer,
            ),
        ):
            state = {
                "request_id": "test-timer-012",
                "user_query": "Hello",
                "messages": [],
            }

            await node_step_34a(state)

            # Verify timer was invoked as context manager
            mock_timer.assert_called()


# =============================================================================
# TestNodeStep34aIntegration - Integration-style Tests
# =============================================================================
class TestNodeStep34aIntegration:
    """Integration-style tests for Step 34a flow."""

    @pytest.mark.asyncio
    async def test_routing_decision_contains_needs_retrieval_for_conditional_routing(
        self,
    ):
        """Test that routing_decision.needs_retrieval is available for conditional edges.

        This is critical for the graph to route to either:
        - Retrieval lane (for TECHNICAL_RESEARCH, THEORETICAL_DEFINITION, NORMATIVE_REFERENCE)
        - Direct response lane (for CHITCHAT, CALCULATOR)
        """
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.CALCULATOR,
            confidence=0.9,
            reasoning="Calculator request",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        # DEV-251: Mock HF classifier
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-needs-retrieval-013",
                "user_query": "Calculate my taxes",
                "messages": [],
            }

            result = await node_step_34a(state)

            # needs_retrieval must be in routing_decision for conditional edges
            assert "needs_retrieval" in result["routing_decision"]
            assert result["routing_decision"]["needs_retrieval"] is False  # CALCULATOR

    @pytest.mark.asyncio
    async def test_requires_freshness_propagated(self):
        """Test that requires_freshness flag is propagated for cache decisions."""
        mock_service = AsyncMock()
        mock_service.route.return_value = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.87,
            reasoning="Query about recent tax changes",
            entities=[],
            requires_freshness=True,  # Needs fresh data
            suggested_sources=["agenzia_entrate"],
        )

        # DEV-251: Mock HF classifier
        with (
            patch(
                "app.services.hf_intent_classifier.get_hf_intent_classifier",
                return_value=_create_low_confidence_hf_mock(),
            ),
            patch(
                "app.services.llm_router_service.LLMRouterService",
                return_value=mock_service,
            ),
        ):
            state = {
                "request_id": "test-fresh-014",
                "user_query": "What are the new tax rates for 2025?",
                "messages": [],
            }

            result = await node_step_34a(state)

            assert result["routing_decision"]["requires_freshness"] is True
