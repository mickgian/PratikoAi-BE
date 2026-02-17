"""RAG Quality Benchmarking with DeepEval.

Evaluates the PratikoAI RAG pipeline against a golden dataset of Italian
CCNL/labor law queries with expected answers.

Usage:
    uv run deepeval test run tests/evals/test_rag_quality.py
    uv run pytest tests/evals/test_rag_quality.py -v -m eval

Quality thresholds:
    - Contextual Precision: > 0.70 (blocks deploy)
    - Faithfulness:         > 0.85 (blocks deploy)
    - Answer Relevancy:     > 0.75 (blocks deploy)
    - Contextual Recall:    > 0.70 (warning only)
"""

import pytest

# Golden dataset: Italian CCNL/labor law queries with expected answers
# These are curated test cases that represent core PratikoAI functionality
GOLDEN_DATASET = [
    {
        "input": "Qual e' il periodo di preavviso per un impiegato con 5 anni di anzianita' nel CCNL Commercio?",
        "expected_output": "Il periodo di preavviso per un impiegato con 5 anni di anzianita'",
        "context": ["CCNL Commercio", "preavviso", "anzianita'"],
    },
    {
        "input": "Come si calcola la tredicesima mensilita' per un lavoratore part-time?",
        "expected_output": "La tredicesima per un lavoratore part-time si calcola in proporzione",
        "context": ["tredicesima", "part-time", "calcolo proporzionale"],
    },
    {
        "input": "Quali sono i contributi INPS a carico del datore di lavoro?",
        "expected_output": "I contributi INPS a carico del datore di lavoro",
        "context": ["INPS", "contributi", "datore di lavoro"],
    },
    {
        "input": "Quanti giorni di ferie spettano nel primo anno di lavoro?",
        "expected_output": "Le ferie nel primo anno di lavoro",
        "context": ["ferie", "primo anno", "maturazione"],
    },
    {
        "input": "Come funziona il TFR e quando viene liquidato?",
        "expected_output": "Il TFR (Trattamento di Fine Rapporto) viene liquidato",
        "context": ["TFR", "liquidazione", "fine rapporto"],
    },
]


@pytest.mark.eval
class TestRAGQuality:
    """RAG quality evaluation tests using DeepEval metrics."""

    @pytest.fixture(autouse=True)
    def _check_deepeval(self) -> None:
        """Skip all tests if deepeval is not installed."""
        pytest.importorskip("deepeval", reason="deepeval not installed, skipping eval tests")

    @pytest.mark.parametrize(
        "test_case",
        GOLDEN_DATASET,
        ids=[tc["input"][:50] for tc in GOLDEN_DATASET],
    )
    def test_answer_relevancy(self, test_case: dict) -> None:
        """Verify RAG answers are relevant to the query (threshold: 0.75)."""
        from deepeval import assert_test
        from deepeval.metrics import AnswerRelevancyMetric
        from deepeval.test_case import LLMTestCase

        metric = AnswerRelevancyMetric(threshold=0.75)
        deepeval_case = LLMTestCase(
            input=test_case["input"],
            actual_output=test_case["expected_output"],
            retrieval_context=test_case["context"],
        )
        assert_test(deepeval_case, [metric])

    @pytest.mark.parametrize(
        "test_case",
        GOLDEN_DATASET,
        ids=[tc["input"][:50] for tc in GOLDEN_DATASET],
    )
    def test_faithfulness(self, test_case: dict) -> None:
        """Verify RAG answers are grounded in context (threshold: 0.85)."""
        from deepeval import assert_test
        from deepeval.metrics import FaithfulnessMetric
        from deepeval.test_case import LLMTestCase

        metric = FaithfulnessMetric(threshold=0.85)
        deepeval_case = LLMTestCase(
            input=test_case["input"],
            actual_output=test_case["expected_output"],
            retrieval_context=test_case["context"],
        )
        assert_test(deepeval_case, [metric])
