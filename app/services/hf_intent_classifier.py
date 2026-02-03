"""HuggingFace Zero-Shot Intent Classifier.

DEV-251 Phase 3: Uses pre-trained zero-shot classification model to replace GPT-4o-mini
router calls for high-confidence classifications.

Zero-shot classification allows classifying text into arbitrary categories without
specific training, using natural language descriptions of each category.

Default Model: MoritzLaurer/mDeBERTa-v3-base-mnli-xnli (280MB, native Italian support)
Alternative: facebook/bart-large-mnli (400MB, multilingual)

Configure via HF_INTENT_MODEL environment variable:
- "mdeberta" (default) -> MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
- "bart" -> facebook/bart-large-mnli

Performance:
- First call: ~5s (model download/load)
- Subsequent calls: <100ms
- Cost: $0 (runs locally on CPU)

Usage:
    from app.services.hf_intent_classifier import get_hf_intent_classifier

    classifier = get_hf_intent_classifier()
    result = await classifier.classify_async("Qual è l'aliquota IVA?")
    if not classifier.should_fallback_to_gpt(result):
        # Use HF result
        intent = result.intent
    else:
        # Fall back to GPT-4o-mini
        ...
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from transformers import pipeline

from app.core.config import HF_INTENT_MODEL, HF_MODEL_MAP
from app.core.logging import logger

# Thread executor for CPU-bound HuggingFace inference (avoids blocking event loop)
# Single worker prevents model loading race conditions and memory duplication
_hf_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hf-intent-")


@dataclass
class IntentResult:
    """Result of zero-shot intent classification.

    Attributes:
        intent: The classified intent (e.g., "chitchat", "technical_research")
        confidence: Confidence score for the top intent (0.0-1.0)
        all_scores: Dictionary mapping all intents to their scores
    """

    intent: str
    confidence: float
    all_scores: dict[str, float]


class HFIntentClassifier:
    """Zero-shot intent classifier using HuggingFace transformers.

    DEV-251: Provides fast, cost-free intent classification for query routing.
    Uses facebook/bart-large-mnli for zero-shot classification, which can classify
    text into any categories described in natural language.

    The model is loaded lazily on first use to avoid startup overhead.
    Falls back to GPT-4o-mini when confidence is below threshold.

    Example:
        classifier = HFIntentClassifier()
        result = classifier.classify("Ciao, come stai?")
        # result.intent = "chitchat", result.confidence = 0.92

        if classifier.should_fallback_to_gpt(result):
            # Use GPT-4o-mini for low confidence cases
            ...
    """

    # Intent labels with natural language descriptions for zero-shot classification.
    # These match the RoutingCategory enum in app.schemas.router.
    INTENT_LABELS = {
        "chitchat": "conversazione casuale, saluti, chiacchierata",
        "theoretical_definition": "richiesta di definizione o spiegazione di un concetto",
        "technical_research": "domanda tecnica complessa che richiede ricerca e analisi",
        "calculator": "richiesta di calcolo numerico o computazione",
        "golden_set": "riferimento specifico a legge, articolo, normativa o regolamento",
    }

    def __init__(
        self,
        model_name: str | None = None,
        confidence_threshold: float = 0.5,  # DEV-251: Lowered from 0.7→0.6→0.5 to reduce GPT fallbacks
    ):
        """Initialize the intent classifier.

        Args:
            model_name: HuggingFace model for zero-shot classification.
                        If None, uses HF_INTENT_MODEL env var (default: mDeBERTa).
                        Accepts short names ("mdeberta", "bart") or full model paths.
            confidence_threshold: Minimum confidence to use local result (0.0-1.0).
                                  Below this threshold, GPT fallback is recommended.
                                  DEV-251: Lowered from 0.7 to 0.5 to reduce GPT fallbacks.
        """
        self._classifier = None  # Lazy loading

        # Resolve model name from config if not provided
        if model_name is None:
            model_key = HF_INTENT_MODEL  # From env or default "mdeberta"
            model_name = HF_MODEL_MAP.get(model_key, HF_MODEL_MAP["mdeberta"])
        elif model_name in HF_MODEL_MAP:
            # Allow short names like "mdeberta" or "bart"
            model_name = HF_MODEL_MAP[model_name]

        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        logger.debug(
            "hf_intent_classifier_initialized",
            model=model_name,
            threshold=confidence_threshold,
            config_key=HF_INTENT_MODEL,
        )

    def _load_model(self) -> None:
        """Lazy load the model on first use.

        The model download takes ~5s on first run, then it's cached locally.
        Loading from cache takes ~2s. Subsequent calls are instant.

        Raises:
            RuntimeError: If model download or loading fails.
        """
        if self._classifier is None:
            logger.info("hf_intent_classifier_loading_model", model=self.model_name)
            try:
                self._classifier = pipeline(
                    "zero-shot-classification",
                    model=self.model_name,
                    device=-1,  # CPU only (device=-1 means CPU)
                )
                logger.info("hf_intent_classifier_model_loaded", model=self.model_name)
            except Exception as e:
                logger.error(
                    "hf_model_loading_failed",
                    model=self.model_name,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                raise RuntimeError(f"Failed to load HuggingFace model '{self.model_name}': {e}") from e

    def classify(self, query: str) -> IntentResult:
        """Classify query intent using zero-shot classification.

        Uses the HuggingFace zero-shot classification pipeline to determine
        the most likely intent category for the query.

        Args:
            query: User query to classify

        Returns:
            IntentResult containing:
            - intent: Most likely intent category
            - confidence: Confidence score (0.0-1.0)
            - all_scores: Scores for all intent categories
        """
        self._load_model()

        # Type assertion for mypy - _classifier is guaranteed non-None after _load_model()
        assert self._classifier is not None, "Model failed to load"

        labels = list(self.INTENT_LABELS.keys())

        # Italian hypothesis template for better classification
        hypothesis_template = "Questa domanda riguarda {}"

        result = self._classifier(
            query,
            candidate_labels=labels,
            hypothesis_template=hypothesis_template,
            multi_label=False,
        )

        top_intent = result["labels"][0]
        top_confidence = result["scores"][0]
        all_scores = dict(zip(result["labels"], result["scores"], strict=False))

        logger.info(
            "hf_classification_complete",
            intent=top_intent,
            confidence=round(top_confidence, 3),
            query_length=len(query),
            all_scores={k: round(v, 3) for k, v in all_scores.items()},
        )

        return IntentResult(
            intent=top_intent,
            confidence=top_confidence,
            all_scores=all_scores,
        )

    async def classify_async(self, query: str) -> IntentResult:
        """Async-safe classification that doesn't block the event loop.

        Runs the CPU-bound HuggingFace inference in a thread pool to prevent
        blocking the asyncio event loop during model loading (~5s first call)
        and inference (~100ms per query).

        This method should be used in async contexts (LangGraph nodes, FastAPI
        endpoints) instead of the synchronous classify() method.

        Args:
            query: User query to classify

        Returns:
            IntentResult containing intent, confidence, and all_scores
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_hf_executor, self.classify, query)

    def should_fallback_to_gpt(self, result: IntentResult) -> bool:
        """Check if GPT fallback is needed due to low confidence.

        When the zero-shot classifier is uncertain, it's safer to fall back
        to the GPT-4o-mini router for more accurate classification.

        Args:
            result: Classification result from classify()

        Returns:
            True if confidence is below threshold and GPT fallback is recommended
        """
        needs_fallback = result.confidence < self.confidence_threshold
        if needs_fallback:
            logger.info(
                "hf_classifier_fallback_needed",
                confidence=round(result.confidence, 3),
                threshold=self.confidence_threshold,
                intent=result.intent,
            )
        return needs_fallback


# Singleton instance
_classifier_instance: HFIntentClassifier | None = None


def get_hf_intent_classifier() -> HFIntentClassifier:
    """Get singleton HFIntentClassifier instance.

    Returns the same instance across all calls to avoid multiple model loads.

    Returns:
        Shared HFIntentClassifier instance
    """
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = HFIntentClassifier()
    return _classifier_instance


def reset_hf_intent_classifier() -> None:
    """Reset singleton instance (for testing).

    Clears the singleton to allow creating a fresh instance.
    Primarily used in tests to ensure isolation.
    """
    global _classifier_instance
    _classifier_instance = None
