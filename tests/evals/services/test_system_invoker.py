"""Tests for SystemInvoker service.

TDD tests for the system integration layer that connects
the evaluation framework to actual RAG pipeline components.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from evals.schemas.test_case import (
    GradeResult,
    GraderType,
    TestCase,
    TestCaseCategory,
)


@pytest.fixture
def routing_test_case() -> TestCase:
    """Create a test case for routing evaluation."""
    return TestCase(
        id="ROUTING-001",
        category=TestCaseCategory.ROUTING,
        query="Qual è l'iter per aprire P.IVA forfettaria?",
        expected_route="technical_research",
        grader_type=GraderType.CODE,
        pass_threshold=0.7,
    )


@pytest.fixture
def retrieval_test_case() -> TestCase:
    """Create a test case for retrieval evaluation."""
    return TestCase(
        id="RETRIEVAL-001",
        category=TestCaseCategory.RETRIEVAL,
        query="Quali sono le scadenze IVA marzo 2025?",
        expected_sources=["ADE-SCADENZE-2025-03", "INPS-CIRC-001"],
        grader_type=GraderType.CODE,
        pass_threshold=0.7,
    )


@pytest.fixture
def response_test_case() -> TestCase:
    """Create a test case for response evaluation."""
    return TestCase(
        id="RESPONSE-001",
        category=TestCaseCategory.RESPONSE,
        query="Come funziona la Legge 104/1992?",
        expected_citations=["Legge 104/1992", "Art. 3"],
        grader_type=GraderType.MODEL,
        pass_threshold=0.7,
    )


class TestSystemInvokerRouter:
    """Tests for router invocation."""

    @pytest.mark.asyncio
    async def test_invoke_router_success(self) -> None:
        """Test successful router invocation returns expected format."""
        from evals.services.system_invoker import SystemInvoker

        # Mock the router service
        mock_decision = MagicMock()
        mock_decision.route.value = "technical_research"
        mock_decision.confidence = 0.85
        mock_decision.entities = [MagicMock(text="P.IVA", type="ente", confidence=0.9)]

        with (
            patch("app.services.llm_router_service.LLMRouterService") as mock_router_cls,
            patch("app.core.llm.model_config.get_model_config") as mock_config,
        ):
            mock_config.return_value = MagicMock()
            mock_router = AsyncMock()
            mock_router.route.return_value = mock_decision
            mock_router_cls.return_value = mock_router

            invoker = SystemInvoker()
            result = await invoker.invoke_router("Qual è l'iter per aprire P.IVA?")

        assert result["route"] == "technical_research"
        assert result["confidence"] == 0.85
        assert len(result["entities"]) == 1
        assert result["entities"][0]["text"] == "P.IVA"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_invoke_router_error_handling(self) -> None:
        """Test router invocation handles errors gracefully."""
        from evals.services.system_invoker import SystemInvoker

        with (
            patch("app.services.llm_router_service.LLMRouterService") as mock_router_cls,
            patch("app.core.llm.model_config.get_model_config") as mock_config,
        ):
            mock_config.return_value = MagicMock()
            mock_router = AsyncMock()
            mock_router.route.side_effect = Exception("LLM API error")
            mock_router_cls.return_value = mock_router

            invoker = SystemInvoker()
            result = await invoker.invoke_router("Test query")

        assert result["route"] is None
        assert result["confidence"] == 0.0
        assert "error" in result
        assert "LLM API error" in result["error"]

    @pytest.mark.asyncio
    async def test_invoke_router_empty_query(self) -> None:
        """Test router handles empty query gracefully."""
        from evals.services.system_invoker import SystemInvoker

        invoker = SystemInvoker()
        result = await invoker.invoke_router("")

        assert result["route"] is None or result.get("error")


class TestSystemInvokerRetrieval:
    """Tests for retrieval invocation."""

    @pytest.mark.asyncio
    async def test_invoke_retrieval_success(self) -> None:
        """Test successful retrieval invocation returns expected format."""
        from evals.services.system_invoker import SystemInvoker

        # Mock search results
        mock_results = [
            MagicMock(
                id="ADE-SCADENZE-2025-03",
                score=0.92,
                title="Scadenze IVA Marzo 2025",
                content="Le scadenze fiscali...",
                source="agenzia_entrate",
                source_url="https://example.com",
            ),
            MagicMock(
                id="INPS-CIRC-001",
                score=0.85,
                title="Circolare INPS",
                content="Comunicazione...",
                source="inps",
                source_url="https://example.com",
            ),
        ]

        with patch("app.services.knowledge_search_service.KnowledgeSearchService") as mock_kb_cls:
            mock_kb = AsyncMock()
            mock_kb.retrieve_topk.return_value = mock_results
            mock_kb_cls.return_value = mock_kb

            invoker = SystemInvoker()
            # Mock db session for retrieval
            mock_session = AsyncMock()
            result = await invoker.invoke_retrieval(
                "Quali sono le scadenze IVA?",
                db_session=mock_session,
            )

        assert len(result) == 2
        assert result[0]["id"] == "ADE-SCADENZE-2025-03"
        assert result[0]["score"] == 0.92
        assert result[1]["id"] == "INPS-CIRC-001"

    @pytest.mark.asyncio
    async def test_invoke_retrieval_no_db_session(self) -> None:
        """Test retrieval without db session returns error."""
        from evals.services.system_invoker import SystemInvoker

        invoker = SystemInvoker()
        result = await invoker.invoke_retrieval("Test query")

        # Should return empty list or error when no DB session
        assert isinstance(result, list)
        if result:
            assert "error" in result[0] or len(result) == 0

    @pytest.mark.asyncio
    async def test_invoke_retrieval_error_handling(self) -> None:
        """Test retrieval handles errors gracefully."""
        from evals.services.system_invoker import SystemInvoker

        with patch("app.services.knowledge_search_service.KnowledgeSearchService") as mock_kb_cls:
            mock_kb = AsyncMock()
            mock_kb.retrieve_topk.side_effect = Exception("Database connection error")
            mock_kb_cls.return_value = mock_kb

            invoker = SystemInvoker()
            mock_session = AsyncMock()
            result = await invoker.invoke_retrieval("Test query", db_session=mock_session)

        assert isinstance(result, list)
        # Either empty list or list with error info
        assert len(result) == 0 or (result and "error" in result[0])


class TestSystemInvokerResponse:
    """Tests for full pipeline response invocation."""

    @pytest.mark.asyncio
    async def test_invoke_response_success(self) -> None:
        """Test successful response invocation returns expected format."""
        from evals.services.system_invoker import SystemInvoker

        # Mock agent response
        mock_message = MagicMock()
        mock_message.content = "Secondo la Legge 104/1992, art. 3..."
        mock_message.role = "assistant"

        with patch("app.core.langgraph.graph.LangGraphAgent") as mock_agent_cls:
            mock_agent = AsyncMock()
            mock_agent.get_response.return_value = [mock_message]
            mock_agent_cls.return_value = mock_agent

            invoker = SystemInvoker()
            result = await invoker.invoke_response("Come funziona la Legge 104?")

        assert "text" in result
        assert "Legge 104/1992" in result["text"]
        assert "citations" in result
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_invoke_response_error_handling(self) -> None:
        """Test response invocation handles errors gracefully."""
        from evals.services.system_invoker import SystemInvoker

        with patch("app.core.langgraph.graph.LangGraphAgent") as mock_agent_cls:
            mock_agent = AsyncMock()
            mock_agent.get_response.side_effect = Exception("Agent execution error")
            mock_agent_cls.return_value = mock_agent

            invoker = SystemInvoker()
            result = await invoker.invoke_response("Test query")

        assert "error" in result
        assert "Agent execution error" in result["error"]


class TestEvalRunnerIntegration:
    """Tests for EvalRunner integration with SystemInvoker.

    These tests verify the integration mode (--integration flag) where
    the runner invokes the real system instead of using golden data.
    """

    @pytest.mark.asyncio
    async def test_grade_routing_test_case(self, routing_test_case: TestCase) -> None:
        """Test grading a routing test case through runner in integration mode."""
        from evals.config import create_fast_config
        from evals.runner import EvalRunner

        config = create_fast_config()
        config.integration_mode = True  # Enable integration mode to use SystemInvoker
        runner = EvalRunner(config)

        # Mock the system invoker
        with patch.object(runner, "invoker", create=True) as mock_invoker:
            mock_invoker.invoke_router = AsyncMock(
                return_value={
                    "route": "technical_research",
                    "confidence": 0.85,
                    "entities": [],
                }
            )

            result = await runner._grade_test_case(routing_test_case)

        assert isinstance(result, GradeResult)
        assert result.score > 0.0
        # Should pass since expected route matches
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_grade_retrieval_test_case(self, retrieval_test_case: TestCase) -> None:
        """Test grading a retrieval test case through runner in integration mode."""
        from evals.config import create_fast_config
        from evals.runner import EvalRunner

        config = create_fast_config()
        config.integration_mode = True  # Enable integration mode to use SystemInvoker
        runner = EvalRunner(config)

        # Mock the system invoker
        with patch.object(runner, "invoker", create=True) as mock_invoker:
            mock_invoker.invoke_retrieval = AsyncMock(
                return_value=[
                    {"id": "ADE-SCADENZE-2025-03", "score": 0.92},
                    {"id": "INPS-CIRC-001", "score": 0.85},
                ]
            )

            result = await runner._grade_test_case(retrieval_test_case)

        assert isinstance(result, GradeResult)
        # Should have high score since both expected sources were retrieved
        assert result.score >= 0.7

    @pytest.mark.asyncio
    async def test_grade_response_with_code_grader(self, response_test_case: TestCase) -> None:
        """Test grading response test case with citation grader in integration mode."""
        from evals.config import create_fast_config
        from evals.runner import EvalRunner

        # Override grader type to CODE for this test
        response_test_case.grader_type = GraderType.CODE

        config = create_fast_config()
        config.integration_mode = True  # Enable integration mode to use SystemInvoker
        runner = EvalRunner(config)

        # Mock the system invoker
        with patch.object(runner, "invoker", create=True) as mock_invoker:
            mock_invoker.invoke_response = AsyncMock(
                return_value={
                    "text": "Secondo la Legge 104/1992, art. 3 comma 2...",
                    "citations": [
                        {"text": "Legge 104/1992", "source_id": "law-104"},
                        {"text": "Art. 3", "source_id": "law-104-art3"},
                    ],
                }
            )
            mock_invoker.invoke_retrieval = AsyncMock(
                return_value=[
                    {"id": "law-104", "content": "Legge 104/1992 sui diritti..."},
                ]
            )

            result = await runner._grade_test_case(response_test_case)

        assert isinstance(result, GradeResult)
        # Should pass with valid citations
        assert result.score > 0.0

    @pytest.mark.asyncio
    async def test_grade_response_with_ollama(self, response_test_case: TestCase) -> None:
        """Test grading response with OllamaJudge when enabled in integration mode."""
        from evals.config import create_local_config
        from evals.runner import EvalRunner

        config = create_local_config()
        config.use_ollama = True
        config.integration_mode = True  # Enable integration mode to use SystemInvoker
        runner = EvalRunner(config)

        # Create mock invoker with proper async methods
        mock_invoker = MagicMock()
        mock_invoker.invoke_response = AsyncMock(
            return_value={
                "text": "La Legge 104/1992 prevede...",
                "citations": [],
            }
        )
        mock_invoker.invoke_retrieval = AsyncMock(return_value=[])

        # Create mock OllamaJudge
        mock_judge = MagicMock()
        mock_judge.is_available = AsyncMock(return_value=True)
        mock_judge.grade = AsyncMock(
            return_value=GradeResult(
                score=0.8,
                passed=True,
                reasoning="Risposta accurata e completa",
            )
        )

        # Replace runner's invoker and ollama_judge
        runner.invoker = mock_invoker
        runner.ollama_judge = mock_judge

        result = await runner._grade_test_case(response_test_case)

        assert isinstance(result, GradeResult)
        # Should use Ollama judge result
        assert result.score == 0.8
        assert "accurata" in result.reasoning


class TestEvalRunnerGoldenData:
    """Tests for EvalRunner using golden data (default mode, $0 cost)."""

    @pytest.mark.asyncio
    async def test_grade_routing_with_golden_data(self) -> None:
        """Test grading a routing test case using golden data."""
        from evals.config import create_fast_config
        from evals.runner import EvalRunner

        # Create test case with golden data
        test_case = TestCase(
            id="ROUTING-GOLDEN-001",
            category=TestCaseCategory.ROUTING,
            query="Ciao, come stai?",
            expected_route="chitchat",
            actual_output={
                "route": "chitchat",
                "confidence": 0.95,
                "entities": [],
            },
            grader_type=GraderType.CODE,
            pass_threshold=0.7,
        )

        config = create_fast_config()
        # integration_mode defaults to False
        runner = EvalRunner(config)

        result = await runner._grade_test_case(test_case)

        assert isinstance(result, GradeResult)
        assert result.score > 0.0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_grade_routing_missing_golden_data(self) -> None:
        """Test grading fails gracefully when golden data is missing."""
        from evals.config import create_fast_config
        from evals.runner import EvalRunner

        # Create test case WITHOUT golden data
        test_case = TestCase(
            id="ROUTING-MISSING-001",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            expected_route="chitchat",
            # actual_output is None (missing)
            grader_type=GraderType.CODE,
            pass_threshold=0.7,
        )

        config = create_fast_config()
        runner = EvalRunner(config)

        result = await runner._grade_test_case(test_case)

        assert isinstance(result, GradeResult)
        assert result.score == 0.0
        assert result.passed is False
        assert "actual_output" in result.reasoning
        assert "--integration" in result.reasoning

    @pytest.mark.asyncio
    async def test_grade_retrieval_with_golden_data(self) -> None:
        """Test grading a retrieval test case using golden data."""
        from evals.config import create_fast_config
        from evals.runner import EvalRunner

        test_case = TestCase(
            id="RETRIEVAL-GOLDEN-001",
            category=TestCaseCategory.RETRIEVAL,
            query="Scadenze fiscali marzo 2025",
            expected_sources=["ADE-SCADENZE-2025-03"],
            actual_output={
                "documents": [
                    {"id": "ADE-SCADENZE-2025-03", "score": 0.92},
                    {"id": "ADE-CALENDARIO-2025", "score": 0.78},
                ],
            },
            grader_type=GraderType.CODE,
            pass_threshold=0.7,
        )

        config = create_fast_config()
        runner = EvalRunner(config)

        result = await runner._grade_test_case(test_case)

        assert isinstance(result, GradeResult)
        assert result.score >= 0.7
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_grade_response_with_golden_data(self) -> None:
        """Test grading a response test case using golden data."""
        from evals.config import create_fast_config
        from evals.runner import EvalRunner

        test_case = TestCase(
            id="RESPONSE-GOLDEN-001",
            category=TestCaseCategory.RESPONSE,
            query="Come funziona la Legge 104/1992?",
            expected_citations=["Legge 104/1992", "Art. 3"],
            actual_output={
                "response": {
                    "text": "La Legge 104/1992 prevede benefici per disabili. Art. 3 descrive i permessi.",
                    "citations": [
                        {"text": "Legge 104/1992", "source_id": "law-104"},
                        {"text": "Art. 3", "source_id": "law-104-art3"},
                    ],
                },
                "source_docs": [
                    {"id": "LEGGE-104-1992", "content": "Legge 104/1992 sui diritti delle persone handicappate..."},
                ],
            },
            grader_type=GraderType.CODE,
            pass_threshold=0.7,
        )

        config = create_fast_config()
        runner = EvalRunner(config)

        result = await runner._grade_test_case(test_case)

        assert isinstance(result, GradeResult)
        assert result.score > 0.0


class TestSystemInvokerLazyInit:
    """Tests for lazy initialization behavior."""

    def test_invoker_creation_without_dependencies(self) -> None:
        """Test SystemInvoker can be created without immediate dependencies."""
        from evals.services.system_invoker import SystemInvoker

        invoker = SystemInvoker()
        assert invoker is not None
        # Should not have initialized services yet
        assert invoker._router_service is None
        assert invoker._kb_service is None

    @pytest.mark.asyncio
    async def test_lazy_init_router(self) -> None:
        """Test router service is lazily initialized on first use."""
        from evals.services.system_invoker import SystemInvoker

        with (
            patch("app.core.llm.model_config.get_model_config") as mock_config,
            patch("app.services.llm_router_service.LLMRouterService") as mock_router_cls,
        ):
            mock_config.return_value = MagicMock()
            mock_router = AsyncMock()
            mock_router.route.return_value = MagicMock(
                route=MagicMock(value="chitchat"),
                confidence=0.5,
                entities=[],
            )
            mock_router_cls.return_value = mock_router

            invoker = SystemInvoker()
            assert invoker._router_service is None

            # First invocation should initialize
            await invoker.invoke_router("Hello")

            # Now it should be initialized
            mock_router_cls.assert_called_once()
