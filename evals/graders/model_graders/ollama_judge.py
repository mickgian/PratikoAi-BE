"""Ollama LLM-as-judge for local model-based evaluation.

Uses Ollama to run local LLM evaluation of responses,
providing zero-cost development-time evaluation with
Italian legal domain rubrics.
"""

import re
from dataclasses import dataclass
from typing import Any

import httpx

from evals.schemas.test_case import GradeResult, TestCase


@dataclass
class OllamaConfig:
    """Configuration for Ollama connection.

    Attributes:
        base_url: Ollama API base URL
        model: Model to use for evaluation
        timeout: Request timeout in seconds
    """

    base_url: str = "http://localhost:11434"
    model: str = "mistral:7b-instruct"
    timeout: float = 60.0


@dataclass
class JudgeResult:
    """Result from LLM judge evaluation.

    Attributes:
        score: Numeric score (0.0-1.0)
        reasoning: Explanation from the LLM
        raw_response: Raw response from Ollama
    """

    score: float
    reasoning: str
    raw_response: str


class OllamaJudge:
    """LLM-as-judge grader using local Ollama.

    Provides model-based evaluation for responses using locally
    running LLMs via Ollama. Supports Italian legal domain rubrics.

    Example:
        ```python
        judge = OllamaJudge()
        if await judge.is_available():
            result = await judge.grade(test_case, response)
        ```
    """

    # Italian legal accuracy rubric
    ITALIAN_LEGAL_RUBRIC = """
Valuta la risposta secondo questi criteri di accuratezza legale italiana:

1.0 - ECCELLENTE: Citazioni normative corrette, articoli accurati, date corrette.
      La risposta è completa e priva di errori.

0.8 - BUONO: Sostanzialmente corretto, con imprecisioni minori che non
      compromettono la validità della risposta.

0.6 - ACCETTABILE: Corretto nella sostanza ma con citazioni incomplete
      o mancanti di alcuni dettagli importanti.

0.4 - INSUFFICIENTE: Errori nelle citazioni normative o informazioni
      parzialmente errate.

0.2 - SCARSO: Citazioni inventate o informazioni significativamente errate.

0.0 - INACCETTABILE: Allucinazioni complete, informazioni totalmente false.

Fornisci la tua valutazione nel formato:
SCORE: [punteggio da 0.0 a 1.0]

REASONING: [spiegazione in italiano]
"""

    def __init__(self, config: OllamaConfig | None = None):
        """Initialize Ollama judge.

        Args:
            config: Optional configuration, uses defaults if not provided
        """
        self.config = config or OllamaConfig()

    async def grade(
        self,
        test_case: TestCase,
        response: dict[str, Any] | None,
        rubric: str | None = None,
    ) -> GradeResult:
        """Grade a response using Ollama LLM.

        Args:
            test_case: Test case with query
            response: Response to evaluate
            rubric: Optional custom rubric (uses default if not provided)

        Returns:
            GradeResult with score, pass/fail, reasoning, and metrics
        """
        if response is None or not response:
            return GradeResult(
                score=0.0,
                passed=False,
                reasoning="Response is missing or empty.",
                metrics={"raw_response": None, "model": self.config.model},
            )

        prompt = self._build_prompt(test_case, response, rubric)

        try:
            ollama_response = await self._call_ollama(prompt)
            judge_result = self._parse_response(ollama_response)

            passed = judge_result.score >= test_case.pass_threshold

            return GradeResult(
                score=judge_result.score,
                passed=passed,
                reasoning=judge_result.reasoning,
                metrics={
                    "raw_response": judge_result.raw_response,
                    "model": self.config.model,
                },
            )

        except ConnectionError as e:
            return GradeResult(
                score=0.0,
                passed=False,
                reasoning=f"Ollama connection error: {e}",
                metrics={"error": str(e), "model": self.config.model},
            )
        except TimeoutError as e:
            return GradeResult(
                score=0.0,
                passed=False,
                reasoning=f"Ollama timeout error: {e}",
                metrics={"error": str(e), "model": self.config.model},
            )

    async def is_available(self) -> bool:
        """Check if Ollama is available.

        Returns:
            True if Ollama is running and accessible
        """
        return await self._check_connection()

    async def _check_connection(self) -> bool:
        """Check connection to Ollama server.

        Returns:
            True if connection successful
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.config.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def _call_ollama(self, prompt: str) -> dict[str, Any]:
        """Call Ollama API with prompt.

        Args:
            prompt: Evaluation prompt

        Returns:
            Ollama API response

        Raises:
            ConnectionError: If connection fails
            TimeoutError: If request times out
        """
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.config.base_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Connection refused: {e}") from e
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timeout: {e}") from e

    def _build_prompt(
        self,
        test_case: TestCase,
        response: dict[str, Any],
        rubric: str | None = None,
    ) -> str:
        """Build evaluation prompt for LLM.

        Args:
            test_case: Test case with query
            response: Response to evaluate
            rubric: Optional custom rubric

        Returns:
            Complete evaluation prompt
        """
        rubric_text = rubric or self.ITALIAN_LEGAL_RUBRIC
        response_text = response.get("text", str(response))

        return f"""Sei un valutatore esperto di risposte nel dominio legale/fiscale italiano.

DOMANDA DELL'UTENTE:
{test_case.query}

RISPOSTA DA VALUTARE:
{response_text}

RUBRICA DI VALUTAZIONE:
{rubric_text}

Valuta la risposta secondo la rubrica fornita.
Rispondi SOLO nel formato richiesto con SCORE e REASONING.
"""

    def _parse_response(self, ollama_response: dict[str, Any]) -> JudgeResult:
        """Parse Ollama response to extract score and reasoning.

        Args:
            ollama_response: Raw Ollama API response

        Returns:
            JudgeResult with parsed score and reasoning
        """
        raw_text = ollama_response.get("response", "")

        # Try to extract score using various patterns
        score = self._extract_score(raw_text)
        reasoning = self._extract_reasoning(raw_text)

        return JudgeResult(
            score=score,
            reasoning=reasoning,
            raw_response=raw_text,
        )

    def _extract_score(self, text: str) -> float:
        """Extract score from LLM response text.

        Handles various formats:
        - SCORE: 0.85
        - Punteggio: 0.8
        - Valutazione: 8/10
        - Just a number: 0.75

        Args:
            text: Raw response text

        Returns:
            Extracted score (0.0 to 1.0)
        """
        # Pattern for "SCORE: X.XX" or "PUNTEGGIO: X.XX"
        score_patterns = [
            r"SCORE:\s*([\d.]+)",
            r"Score:\s*([\d.]+)",
            r"PUNTEGGIO:\s*([\d.]+)",
            r"Punteggio:\s*([\d.]+)",
            r"Valutazione:\s*([\d.]+)(?:/10)?",
        ]

        for pattern in score_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                # Handle X/10 format
                if score > 1.0 and score <= 10.0:
                    score = score / 10.0
                return min(1.0, max(0.0, score))

        # Try to find any decimal number between 0 and 1
        decimal_match = re.search(r"\b(0\.\d+|1\.0|0|1)\b", text)
        if decimal_match:
            return float(decimal_match.group(1))

        # Default to 0 if no score found
        return 0.0

    def _extract_reasoning(self, text: str) -> str:
        """Extract reasoning from LLM response text.

        Args:
            text: Raw response text

        Returns:
            Extracted reasoning or full text if not found
        """
        # Look for REASONING: section
        reasoning_patterns = [
            r"REASONING:\s*(.+?)(?=\n\n|\Z)",
            r"Reasoning:\s*(.+?)(?=\n\n|\Z)",
            r"MOTIVAZIONE:\s*(.+?)(?=\n\n|\Z)",
        ]

        for pattern in reasoning_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()

        # Return text after SCORE line if no REASONING found
        lines = text.split("\n")
        after_score = False
        reasoning_lines = []

        for line in lines:
            if after_score:
                reasoning_lines.append(line)
            if "SCORE" in line.upper():
                after_score = True

        if reasoning_lines:
            return "\n".join(reasoning_lines).strip()

        return text.strip()
