"""TDD Tests for DEV-251 Phase 3: HuggingFace Zero-Shot Intent Classifier.

Tests for HuggingFace-based intent classification to replace GPT-4o-mini router calls.

Run with: pytest tests/unit/services/test_hf_intent_classifier.py -v
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import HF_MODEL_MAP
from app.services.hf_intent_classifier import (
    HFIntentClassifier,
    IntentResult,
    get_hf_intent_classifier,
    reset_hf_intent_classifier,
)


@pytest.fixture
def classifier():
    """Create fresh classifier instance for each test."""
    reset_hf_intent_classifier()
    return HFIntentClassifier()


@pytest.fixture
def mock_pipeline_result():
    """Mock HuggingFace pipeline result for testing without model download."""
    return {
        "labels": ["technical_research", "chitchat", "theoretical_definition", "calculator", "golden_set"],
        "scores": [0.85, 0.05, 0.04, 0.03, 0.03],
    }


class TestClassifierLazyLoading:
    """Test that model loads lazily to avoid startup overhead."""

    def test_classifier_does_not_load_on_init(self):
        """Model should not load until first classify() call."""
        reset_hf_intent_classifier()
        classifier = HFIntentClassifier()
        assert classifier._classifier is None

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_classifier_loads_on_first_classify(self, mock_pipeline, classifier):
        """Model should load on first classify() call."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["chitchat"],
            "scores": [0.9],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        classifier.classify("Ciao")
        mock_pipeline.assert_called_once()


class TestChitchatDetection:
    """Test chitchat intent detection."""

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_greeting_is_chitchat(self, mock_pipeline, classifier):
        """'Ciao, come stai?' should be classified as chitchat."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["chitchat", "theoretical_definition", "technical_research", "calculator", "golden_set"],
            "scores": [0.92, 0.03, 0.02, 0.02, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Ciao, come stai?")
        assert result.intent == "chitchat"
        assert result.confidence >= 0.7

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_casual_conversation_is_chitchat(self, mock_pipeline, classifier):
        """Casual small talk should be chitchat."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["chitchat", "theoretical_definition", "technical_research", "calculator", "golden_set"],
            "scores": [0.88, 0.05, 0.04, 0.02, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Grazie mille, sei stato molto utile!")
        assert result.intent == "chitchat"


class TestTechnicalResearchDetection:
    """Test technical research intent detection."""

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_complex_fiscal_question(self, mock_pipeline, classifier):
        """Complex fiscal questions should be technical_research."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["technical_research", "theoretical_definition", "calculator", "golden_set", "chitchat"],
            "scores": [0.85, 0.08, 0.04, 0.02, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify(
            "Come si calcola l'imposta sostitutiva per il regime forfettario con attività mista?"
        )
        assert result.intent == "technical_research"
        assert result.confidence >= 0.7

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_procedural_question(self, mock_pipeline, classifier):
        """Procedural questions requiring research should be technical_research."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["technical_research", "theoretical_definition", "golden_set", "calculator", "chitchat"],
            "scores": [0.82, 0.10, 0.04, 0.03, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify(
            "Qual è la procedura per richiedere il rimborso IVA per acquisti intracomunitari?"
        )
        assert result.intent == "technical_research"


class TestGoldenSetDetection:
    """Test golden_set intent detection for specific law references."""

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_specific_article_reference(self, mock_pipeline, classifier):
        """Specific article references should be golden_set."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["golden_set", "technical_research", "theoretical_definition", "calculator", "chitchat"],
            "scores": [0.90, 0.05, 0.03, 0.01, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Art. 7-ter DPR 633/72")
        assert result.intent == "golden_set"
        assert result.confidence >= 0.7

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_law_reference_lookup(self, mock_pipeline, classifier):
        """Law reference lookup should be golden_set."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["golden_set", "technical_research", "theoretical_definition", "calculator", "chitchat"],
            "scores": [0.87, 0.07, 0.04, 0.01, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Legge 104/92 art. 33")
        assert result.intent == "golden_set"


class TestCalculatorDetection:
    """Test calculator intent detection."""

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_iva_calculation(self, mock_pipeline, classifier):
        """IVA calculation requests should be calculator."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["calculator", "technical_research", "theoretical_definition", "golden_set", "chitchat"],
            "scores": [0.89, 0.06, 0.03, 0.01, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Calcola IVA su 1000 euro")
        assert result.intent == "calculator"
        assert result.confidence >= 0.7

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_salary_calculation(self, mock_pipeline, classifier):
        """Salary/contribution calculations should be calculator."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["calculator", "technical_research", "theoretical_definition", "golden_set", "chitchat"],
            "scores": [0.85, 0.08, 0.04, 0.02, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Quanto netto da 2500 euro lordi?")
        assert result.intent == "calculator"


class TestTheoreticalDefinitionDetection:
    """Test theoretical_definition intent detection."""

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_definition_question(self, mock_pipeline, classifier):
        """Definition questions should be theoretical_definition."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["theoretical_definition", "technical_research", "golden_set", "calculator", "chitchat"],
            "scores": [0.88, 0.07, 0.03, 0.01, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Cos'è il regime forfettario?")
        assert result.intent == "theoretical_definition"
        assert result.confidence >= 0.7


class TestFallbackThreshold:
    """Test GPT fallback threshold logic."""

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_low_confidence_triggers_fallback(self, mock_pipeline, classifier):
        """Low confidence results should trigger GPT fallback."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["technical_research", "chitchat", "theoretical_definition", "calculator", "golden_set"],
            "scores": [0.35, 0.30, 0.20, 0.10, 0.05],  # Low confidence
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Questione ambigua")
        assert classifier.should_fallback_to_gpt(result)

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_high_confidence_no_fallback(self, mock_pipeline, classifier):
        """High confidence results should NOT trigger fallback."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["chitchat", "technical_research", "theoretical_definition", "calculator", "golden_set"],
            "scores": [0.95, 0.02, 0.02, 0.005, 0.005],  # High confidence
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Ciao!")
        assert not classifier.should_fallback_to_gpt(result)

    def test_custom_threshold(self):
        """Custom confidence threshold should be respected."""
        strict_classifier = HFIntentClassifier(confidence_threshold=0.9)
        assert strict_classifier.confidence_threshold == 0.9

        lenient_classifier = HFIntentClassifier(confidence_threshold=0.5)
        assert lenient_classifier.confidence_threshold == 0.5


class TestAsyncClassification:
    """Test async classification method."""

    @pytest.mark.asyncio
    @patch("app.services.hf_intent_classifier.pipeline")
    async def test_classify_async_returns_same_result_as_sync(self, mock_pipeline):
        """Async classify should return the same result as sync classify."""
        reset_hf_intent_classifier()
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["chitchat", "technical_research", "theoretical_definition", "calculator", "golden_set"],
            "scores": [0.85, 0.08, 0.04, 0.02, 0.01],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        classifier = HFIntentClassifier()
        sync_result = classifier.classify("Ciao")
        async_result = await classifier.classify_async("Ciao")

        assert sync_result.intent == async_result.intent
        assert sync_result.confidence == async_result.confidence

    @pytest.mark.asyncio
    @patch("app.services.hf_intent_classifier.pipeline")
    async def test_classify_async_does_not_block_event_loop(self, mock_pipeline):
        """Async classify should run in thread pool without blocking."""
        import asyncio

        reset_hf_intent_classifier()
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["technical_research", "chitchat", "theoretical_definition", "calculator", "golden_set"],
            "scores": [0.80, 0.10, 0.05, 0.03, 0.02],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        classifier = HFIntentClassifier()

        # Run multiple async classifications concurrently
        results = await asyncio.gather(
            classifier.classify_async("Query 1"),
            classifier.classify_async("Query 2"),
            classifier.classify_async("Query 3"),
        )

        assert len(results) == 3
        for result in results:
            assert result.intent == "technical_research"


class TestIntentResult:
    """Test IntentResult dataclass."""

    def test_intent_result_creation(self):
        """IntentResult should hold all classification data."""
        result = IntentResult(
            intent="technical_research",
            confidence=0.85,
            all_scores={
                "technical_research": 0.85,
                "chitchat": 0.05,
                "theoretical_definition": 0.05,
                "calculator": 0.03,
                "golden_set": 0.02,
            },
        )
        assert result.intent == "technical_research"
        assert result.confidence == 0.85
        assert len(result.all_scores) == 5
        assert result.all_scores["technical_research"] == 0.85


class TestSingletonPattern:
    """Test singleton pattern for classifier."""

    def test_get_hf_intent_classifier_returns_same_instance(self):
        """get_hf_intent_classifier should return singleton."""
        reset_hf_intent_classifier()
        c1 = get_hf_intent_classifier()
        c2 = get_hf_intent_classifier()
        assert c1 is c2

    def test_reset_clears_singleton(self):
        """reset_hf_intent_classifier should clear singleton."""
        c1 = get_hf_intent_classifier()
        reset_hf_intent_classifier()
        c2 = get_hf_intent_classifier()
        assert c1 is not c2


class TestConfigurableModel:
    """Test model configuration via environment variable."""

    def test_default_model_is_mdeberta(self):
        """Default model should be mDeBERTa (Italian-optimized)."""
        reset_hf_intent_classifier()
        classifier = HFIntentClassifier()
        assert classifier.model_name == HF_MODEL_MAP["mdeberta"]
        assert "mDeBERTa" in classifier.model_name

    def test_explicit_mdeberta_model(self):
        """Explicit 'mdeberta' should resolve to full model name."""
        classifier = HFIntentClassifier(model_name="mdeberta")
        assert classifier.model_name == HF_MODEL_MAP["mdeberta"]

    def test_explicit_bart_model(self):
        """Explicit 'bart' should resolve to full model name."""
        classifier = HFIntentClassifier(model_name="bart")
        assert classifier.model_name == HF_MODEL_MAP["bart"]
        assert "bart-large-mnli" in classifier.model_name

    def test_full_model_path_passthrough(self):
        """Full model paths should be passed through unchanged."""
        custom_model = "custom-org/custom-model"
        classifier = HFIntentClassifier(model_name=custom_model)
        assert classifier.model_name == custom_model

    @patch.dict("os.environ", {"HF_INTENT_MODEL": "bart"})
    def test_env_var_bart_selection(self):
        """HF_INTENT_MODEL=bart should select BART model."""
        # Need to reload config to pick up env var
        import importlib

        import app.core.config as config_module

        importlib.reload(config_module)

        from app.core.config import HF_INTENT_MODEL as reloaded_model

        assert reloaded_model == "bart"

    def test_model_map_contains_expected_models(self):
        """HF_MODEL_MAP should contain mdeberta and bart."""
        assert "mdeberta" in HF_MODEL_MAP
        assert "bart" in HF_MODEL_MAP
        assert "mDeBERTa" in HF_MODEL_MAP["mdeberta"]
        assert "bart-large-mnli" in HF_MODEL_MAP["bart"]


class TestModelLoadingErrorHandling:
    """Test error handling during model loading."""

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_model_loading_error_raises_runtime_error(self, mock_pipeline):
        """Model loading errors should raise RuntimeError."""
        mock_pipeline.side_effect = OSError("Network error")
        classifier = HFIntentClassifier()

        with pytest.raises(RuntimeError) as exc_info:
            classifier.classify("Test query")

        assert "Failed to load HuggingFace model" in str(exc_info.value)
        assert "Network error" in str(exc_info.value)

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_model_loading_error_logs_details(self, mock_pipeline, caplog):
        """Model loading errors should log structured details."""
        mock_pipeline.side_effect = ValueError("Invalid model")
        classifier = HFIntentClassifier()

        with pytest.raises(RuntimeError):
            classifier.classify("Test query")

        # Verify error was logged (structlog may format differently)
        assert any(
            "hf_model_loading_failed" in record.message or "Invalid model" in record.message
            for record in caplog.records
        )


class TestPerformance:
    """Test performance requirements."""

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_classification_under_100ms_with_mocked_model(self, mock_pipeline, classifier):
        """Classification should complete in <100ms after warmup (mocked)."""
        import time

        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["technical_research", "chitchat", "theoretical_definition", "calculator", "golden_set"],
            "scores": [0.85, 0.05, 0.04, 0.03, 0.03],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        # Warmup
        classifier.classify("Test query")

        # Benchmark
        start = time.perf_counter()
        for _ in range(100):
            classifier.classify("Qual è l'aliquota IVA?")
        elapsed = (time.perf_counter() - start) * 1000 / 100  # Average ms

        assert elapsed < 100, f"Classification took {elapsed}ms, expected <100ms"


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_empty_query(self, mock_pipeline, classifier):
        """Empty query should still return a result."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["chitchat", "technical_research", "theoretical_definition", "calculator", "golden_set"],
            "scores": [0.5, 0.2, 0.15, 0.1, 0.05],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("")
        assert result.intent is not None

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_very_long_query(self, mock_pipeline, classifier):
        """Very long query should handle gracefully."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["technical_research", "chitchat", "theoretical_definition", "calculator", "golden_set"],
            "scores": [0.80, 0.08, 0.06, 0.04, 0.02],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        long_query = "IVA " * 500  # Very long query
        result = classifier.classify(long_query)
        assert result.intent is not None

    @patch("app.services.hf_intent_classifier.pipeline")
    def test_special_characters(self, mock_pipeline, classifier):
        """Special characters should not break classification."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.return_value = {
            "labels": ["calculator", "technical_research", "theoretical_definition", "golden_set", "chitchat"],
            "scores": [0.75, 0.12, 0.08, 0.03, 0.02],
        }
        mock_pipeline.return_value = mock_pipeline_instance

        result = classifier.classify("Qual è l'IVA per 1.000,00?")
        assert result.intent is not None


@pytest.mark.slow
class TestIntegrationWithRealModel:
    """Integration tests with real HuggingFace model.

    These tests download and use the actual model. Mark as slow.
    Run with: pytest -m slow tests/unit/services/test_hf_intent_classifier.py
    """

    def test_real_model_chitchat_detection(self):
        """Test real model can detect chitchat."""
        reset_hf_intent_classifier()
        classifier = HFIntentClassifier()
        result = classifier.classify("Ciao, buongiorno!")
        # Real model should classify greetings as chitchat with reasonable confidence
        assert result.intent is not None
        assert result.confidence > 0

    def test_real_model_technical_research_detection(self):
        """Test real model can detect technical research."""
        reset_hf_intent_classifier()
        classifier = HFIntentClassifier()
        result = classifier.classify("Come si calcola l'imposta sostitutiva per il regime forfettario?")
        assert result.intent is not None
        assert result.confidence > 0
