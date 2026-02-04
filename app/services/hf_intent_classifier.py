"""HuggingFace Intent Classifier (Zero-Shot + Fine-Tuned).

DEV-251 Phase 3: Zero-shot classification to replace GPT-4o-mini router calls.
DEV-253: Dual-mode support for fine-tuned text-classification models.

The classifier auto-detects the pipeline type based on the model config:
- Known zero-shot NLI models → "zero-shot-classification" pipeline
- Fine-tuned models with intent id2label → "text-classification" pipeline

Configure via HF_INTENT_MODEL environment variable:
- "mdeberta" (default) → MoritzLaurer/mDeBERTa-v3-base-mnli-xnli (zero-shot)
- "bart" → facebook/bart-large-mnli (zero-shot)
- "pratikoai/intent-classifier-v1" → fine-tuned text-classification model
- Any HuggingFace Hub path or local directory

Performance:
- First call: ~5s (model download/load)
- Subsequent calls: <100ms
- Cost: $0 (runs locally on CPU)

Usage:
    from app.services.hf_intent_classifier import get_hf_intent_classifier

    classifier = get_hf_intent_classifier()
    result = await classifier.classify_async("Qual e l'aliquota IVA?")
    if not classifier.should_fallback_to_gpt(result):
        intent = result.intent
    else:
        # Fall back to GPT-4o-mini
        ...
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from transformers import AutoConfig, pipeline

from app.core.config import HF_INTENT_MODEL, HF_MODEL_MAP
from app.core.logging import logger

# Thread executor for CPU-bound HuggingFace inference (avoids blocking event loop)
# Single worker prevents model loading race conditions and memory duplication
_hf_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hf-intent-")

# NLI label sets that indicate a zero-shot model (not fine-tuned for our intents)
_NLI_LABEL_SETS = [
    {"ENTAILMENT", "NEUTRAL", "CONTRADICTION"},
    {"entailment", "neutral", "contradiction"},
]


@dataclass
class IntentResult:
    """Result of intent classification.

    Attributes:
        intent: The classified intent (e.g., "chitchat", "technical_research")
        confidence: Confidence score for the top intent (0.0-1.0)
        all_scores: Dictionary mapping all intents to their scores
    """

    intent: str
    confidence: float
    all_scores: dict[str, float]


def _is_finetuned_model(model_name: str) -> bool:
    """Check if a model is fine-tuned for our intents (not a generic NLI model).

    Inspects the model's id2label config to determine if it was fine-tuned
    for our specific intent categories, or if it's a generic NLI model.

    Args:
        model_name: HuggingFace model name or path

    Returns:
        True if the model has intent-specific labels (fine-tuned),
        False if it has NLI labels or config can't be loaded.
    """
    try:
        config = AutoConfig.from_pretrained(model_name)
        if not hasattr(config, "id2label") or not config.id2label:
            return False

        model_labels = set(config.id2label.values())
        if model_labels in _NLI_LABEL_SETS:
            return False

        # Check if at least one of our intent labels is present
        our_intents = {"chitchat", "theoretical_definition", "technical_research", "calculator", "golden_set"}
        return bool(model_labels & our_intents)
    except Exception:
        logger.debug("hf_config_check_failed", model=model_name)
        return False


class HFIntentClassifier:
    """Dual-mode intent classifier using HuggingFace transformers.

    Supports both zero-shot and fine-tuned models. The pipeline type is
    auto-detected from the model config on first use.

    Example:
        classifier = HFIntentClassifier()
        result = classifier.classify("Ciao, come stai?")
        # result.intent = "chitchat", result.confidence = 0.92
    """

    # Intent labels with natural language descriptions for zero-shot classification.
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
        confidence_threshold: float = 0.5,
    ):
        """Initialize the intent classifier.

        Args:
            model_name: HuggingFace model name or path. If None, uses
                        HF_INTENT_MODEL env var. Accepts short names
                        ("mdeberta", "bart") or full model paths.
            confidence_threshold: Minimum confidence to use local result.
        """
        self._classifier = None  # Lazy loading
        self._is_finetuned: bool | None = None

        # Resolve model name from config if not provided
        if model_name is None:
            model_key = HF_INTENT_MODEL
            model_name = HF_MODEL_MAP.get(model_key, model_key)
        elif model_name in HF_MODEL_MAP:
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

        Auto-detects whether to use zero-shot or text-classification pipeline
        based on the model's id2label config.

        Raises:
            RuntimeError: If model download or loading fails.
        """
        if self._classifier is None:
            logger.info("hf_intent_classifier_loading_model", model=self.model_name)
            try:
                self._is_finetuned = _is_finetuned_model(self.model_name)
                pipeline_task = "text-classification" if self._is_finetuned else "zero-shot-classification"

                logger.info(
                    "hf_intent_classifier_pipeline_selected",
                    model=self.model_name,
                    pipeline=pipeline_task,
                    is_finetuned=self._is_finetuned,
                )

                self._classifier = pipeline(
                    pipeline_task,
                    model=self.model_name,
                    device=-1,
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

    def _classify_zero_shot(self, query: str) -> IntentResult:
        """Classify using zero-shot NLI pipeline."""
        assert self._classifier is not None

        labels = list(self.INTENT_LABELS.keys())
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

        return IntentResult(intent=top_intent, confidence=top_confidence, all_scores=all_scores)

    def _classify_finetuned(self, query: str) -> IntentResult:
        """Classify using fine-tuned text-classification pipeline.

        Normalizes the output to the same IntentResult format as zero-shot.
        Handles models that return top-k or top-1 results.
        """
        assert self._classifier is not None

        results = self._classifier(query, top_k=len(self.INTENT_LABELS))

        # Build all_scores from results
        all_scores: dict[str, float] = {}
        for item in results:
            all_scores[item["label"]] = item["score"]

        # Fill missing intents with 0.0
        for intent in self.INTENT_LABELS:
            if intent not in all_scores:
                all_scores[intent] = 0.0

        top_intent = results[0]["label"]
        top_confidence = results[0]["score"]

        return IntentResult(intent=top_intent, confidence=top_confidence, all_scores=all_scores)

    def classify(self, query: str) -> IntentResult:
        """Classify query intent.

        Auto-selects between zero-shot and fine-tuned classification
        based on the loaded model type.

        Args:
            query: User query to classify

        Returns:
            IntentResult with intent, confidence, and all_scores
        """
        self._load_model()

        if self._is_finetuned:
            result = self._classify_finetuned(query)
        else:
            result = self._classify_zero_shot(query)

        logger.info(
            "hf_classification_complete",
            intent=result.intent,
            confidence=round(result.confidence, 3),
            query_length=len(query),
            all_scores={k: round(v, 3) for k, v in result.all_scores.items()},
            is_finetuned=self._is_finetuned,
        )

        return result

    async def classify_async(self, query: str) -> IntentResult:
        """Async-safe classification that doesn't block the event loop.

        Runs CPU-bound inference in a thread pool.

        Args:
            query: User query to classify

        Returns:
            IntentResult with intent, confidence, and all_scores
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_hf_executor, self.classify, query)

    def should_fallback_to_gpt(self, result: IntentResult) -> bool:
        """Check if GPT fallback is needed due to low confidence.

        Args:
            result: Classification result from classify()

        Returns:
            True if confidence is below threshold
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
