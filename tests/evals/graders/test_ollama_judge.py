"""Tests for Ollama LLM-as-judge grader.

TDD: RED phase - Write tests first, then implement.
"""

from unittest.mock import AsyncMock, patch

import pytest

from evals.graders.model_graders.ollama_judge import (
    JudgeResult,
    OllamaConfig,
    OllamaJudge,
)
from evals.schemas.test_case import (
    GradeResult,
    GraderType,
    TestCase,
    TestCaseCategory,
)


class TestOllamaConfig:
    """Tests for OllamaConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = OllamaConfig()
        assert config.base_url == "http://localhost:11434"
        assert config.model == "mistral:7b-instruct"
        assert config.timeout == 60.0

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = OllamaConfig(
            base_url="http://custom:11434",
            model="llama3.1:8b",
            timeout=120.0,
        )
        assert config.base_url == "http://custom:11434"
        assert config.model == "llama3.1:8b"


class TestJudgeResult:
    """Tests for JudgeResult."""

    def test_create_result(self) -> None:
        """Test creating a judge result."""
        result = JudgeResult(
            score=0.85,
            reasoning="The response is accurate and well-cited.",
            raw_response="Score: 0.85\nReasoning: ...",
        )
        assert result.score == 0.85
        assert "accurate" in result.reasoning


class TestOllamaJudge:
    """Tests for OllamaJudge."""

    @pytest.fixture
    def judge(self) -> OllamaJudge:
        """Create an Ollama judge instance."""
        return OllamaJudge()

    @pytest.fixture
    def mock_ollama_response(self) -> dict:
        """Mock successful Ollama API response."""
        return {
            "response": """
            SCORE: 0.85

            REASONING: La risposta è accurata e ben documentata.
            Le citazioni normative sono corrette e pertinenti.
            """,
            "done": True,
        }

    @pytest.mark.asyncio
    async def test_grade_with_mock_ollama(self, judge: OllamaJudge, mock_ollama_response: dict) -> None:
        """Test grading with mocked Ollama response."""
        test_case = TestCase(
            id="MODEL-001",
            category=TestCaseCategory.RESPONSE,
            query="Quali sono i benefici della Legge 104?",
            grader_type=GraderType.MODEL,
        )
        response = {
            "text": "La Legge 104/1992 prevede permessi lavorativi...",
        }

        with patch.object(judge, "_call_ollama", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_ollama_response
            result = await judge.grade(test_case, response)

        assert isinstance(result, GradeResult)
        assert result.score == 0.85
        assert result.metrics is not None
        assert result.metrics["raw_response"] is not None

    @pytest.mark.asyncio
    async def test_grade_parse_score_formats(self, judge: OllamaJudge) -> None:
        """Test parsing different score formats from LLM."""
        test_case = TestCase(
            id="MODEL-002",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
            grader_type=GraderType.MODEL,
        )
        response = {"text": "Test response"}

        # Test various score formats
        score_formats = [
            ("SCORE: 0.9", 0.9),
            ("Score: 0.75", 0.75),
            ("PUNTEGGIO: 0.8", 0.8),
            ("Valutazione: 8/10", 0.8),
            ("0.85", 0.85),
        ]

        for response_text, expected_score in score_formats:
            mock_response = {"response": response_text, "done": True}
            with patch.object(judge, "_call_ollama", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = mock_response
                result = await judge.grade(test_case, response)
                assert abs(result.score - expected_score) < 0.01, f"Failed for: {response_text}"

    @pytest.mark.asyncio
    async def test_grade_ollama_not_running(self, judge: OllamaJudge) -> None:
        """Test graceful handling when Ollama is not running."""
        test_case = TestCase(
            id="MODEL-003",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
            grader_type=GraderType.MODEL,
        )
        response = {"text": "Test response"}

        with patch.object(judge, "_call_ollama", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = ConnectionError("Connection refused")
            result = await judge.grade(test_case, response)

        assert result.passed is False
        assert result.score == 0.0
        assert "connection" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_grade_timeout_handling(self, judge: OllamaJudge) -> None:
        """Test handling of Ollama timeout."""
        test_case = TestCase(
            id="MODEL-004",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
            grader_type=GraderType.MODEL,
        )
        response = {"text": "Test response"}

        with patch.object(judge, "_call_ollama", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = TimeoutError("Request timeout")
            result = await judge.grade(test_case, response)

        assert result.passed is False
        assert "timeout" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_grade_with_rubric(self, judge: OllamaJudge) -> None:
        """Test grading with custom rubric."""
        test_case = TestCase(
            id="MODEL-005",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
            grader_type=GraderType.MODEL,
        )
        response = {"text": "Test response"}
        rubric = """
        Valuta la risposta secondo questi criteri:
        1.0 - ECCELLENTE: Citazioni corrette, informazioni accurate
        0.5 - SUFFICIENTE: Alcune imprecisioni
        0.0 - INSUFFICIENTE: Informazioni errate
        """

        mock_response = {"response": "SCORE: 0.9\nOttima risposta.", "done": True}
        with patch.object(judge, "_call_ollama", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            _ = await judge.grade(test_case, response, rubric=rubric)

        # Verify rubric was included in prompt
        call_args = mock_call.call_args
        assert rubric in call_args[0][0]  # First positional arg is prompt

    @pytest.mark.asyncio
    async def test_grade_empty_response(self, judge: OllamaJudge) -> None:
        """Test grading with empty response."""
        test_case = TestCase(
            id="MODEL-006",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
            grader_type=GraderType.MODEL,
        )

        result = await judge.grade(test_case, {})
        assert result.passed is False
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_grade_none_response(self, judge: OllamaJudge) -> None:
        """Test grading with None response."""
        test_case = TestCase(
            id="MODEL-007",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
            grader_type=GraderType.MODEL,
        )

        result = await judge.grade(test_case, None)
        assert result.passed is False
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_build_evaluation_prompt(self, judge: OllamaJudge) -> None:
        """Test building the evaluation prompt."""
        test_case = TestCase(
            id="MODEL-008",
            category=TestCaseCategory.RESPONSE,
            query="Qual è la scadenza per la rottamazione?",
            grader_type=GraderType.MODEL,
        )
        response = {"text": "La scadenza è il 31 dicembre 2025."}

        prompt = judge._build_prompt(test_case, response)

        assert "rottamazione" in prompt.lower()
        assert "31 dicembre 2025" in prompt
        assert "SCORE" in prompt or "PUNTEGGIO" in prompt

    @pytest.mark.asyncio
    async def test_is_available(self, judge: OllamaJudge) -> None:
        """Test checking if Ollama is available."""
        with patch.object(judge, "_check_connection", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True
            assert await judge.is_available() is True

            mock_check.return_value = False
            assert await judge.is_available() is False

    @pytest.mark.asyncio
    async def test_grade_italian_legal_rubric(self, judge: OllamaJudge) -> None:
        """Test with Italian legal accuracy rubric."""
        test_case = TestCase(
            id="MODEL-009",
            category=TestCaseCategory.RESPONSE,
            query="Quali sono gli obblighi INPS?",
            grader_type=GraderType.MODEL,
        )
        response = {
            "text": "Gli obblighi INPS includono il versamento contributi...",
        }

        mock_response = {
            "response": """
            SCORE: 0.8

            REASONING: La risposta è sostanzialmente corretta.
            Menziona correttamente gli obblighi contributivi.
            Mancano alcuni dettagli sulle scadenze.
            """,
            "done": True,
        }

        with patch.object(judge, "_call_ollama", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await judge.grade(test_case, response, rubric=judge.ITALIAN_LEGAL_RUBRIC)

        assert result.score == 0.8
        assert "corretta" in result.reasoning.lower() or "correct" in result.reasoning.lower()
