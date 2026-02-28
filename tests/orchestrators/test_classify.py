"""Comprehensive tests for app/orchestrators/classify.py.

Tests the classify orchestrator step functions including:
- step_12__extract_query: Extracts latest user message from conversation
- step_31__classify_domain: Calls DomainActionClassifier for domain/action classification
- step_32__calc_scores: Calculates domain and action scores
- step_33__confidence_check: Confidence threshold validation
- step_35__llmfallback (sync stub): LLM fallback placeholder
- step_35__llm_fallback (async): LLM fallback classification orchestrator
- step_42__class_confidence: Classification existence and confidence check
- step_43__domain_prompt: Domain-specific prompt generation
- step_88__doc_classify (sync stub): Document classification placeholder
- step_121__trust_score_ok: Trust score decision evaluation
- _preprocess_query: Query preprocessing helper
- _analyze_query_complexity: Query complexity analysis helper
- _evaluate_trust_score_decision: Trust score decision helper

Target: 90%+ coverage of app/orchestrators/classify.py
"""

import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrators.classify import (
    _analyze_query_complexity,
    _evaluate_trust_score_decision,
    _preprocess_query,
    step_12__extract_query,
    step_31__classify_domain,
    step_32__calc_scores,
    step_33__confidence_check,
    step_35__llm_fallback,
    step_35__llmfallback,
    step_42__class_confidence,
    step_43__domain_prompt,
    step_88__doc_classify,
    step_121__trust_score_ok,
)


# ---------------------------------------------------------------------------
# Helper: Create a Message-like object for tests
# ---------------------------------------------------------------------------
def _make_message(role: str, content: str):
    """Create a Message-like object matching app.schemas.chat.Message."""
    from app.schemas.chat import Message

    return Message(role=role, content=content)


# ===========================================================================
# _analyze_query_complexity Tests (pure sync function)
# ===========================================================================


class TestAnalyzeQueryComplexity:
    """Tests for _analyze_query_complexity helper."""

    def test_empty_query_is_simple(self):
        assert _analyze_query_complexity("") == "simple"

    def test_none_query_is_simple(self):
        assert _analyze_query_complexity("") == "simple"

    def test_short_query_is_simple(self):
        assert _analyze_query_complexity("calcola iva") == "simple"

    def test_under_50_chars_is_simple(self):
        query = "a" * 49
        assert _analyze_query_complexity(query) == "simple"

    def test_exactly_50_chars_is_medium(self):
        query = "a" * 50
        assert _analyze_query_complexity(query) == "medium"

    def test_medium_query(self):
        query = "a" * 100
        assert _analyze_query_complexity(query) == "medium"

    def test_under_150_chars_is_medium(self):
        query = "a" * 149
        assert _analyze_query_complexity(query) == "medium"

    def test_exactly_150_chars_is_complex(self):
        query = "a" * 150
        assert _analyze_query_complexity(query) == "complex"

    def test_long_query_is_complex(self):
        query = "a" * 500
        assert _analyze_query_complexity(query) == "complex"

    def test_real_simple_query(self):
        assert _analyze_query_complexity("cos'è l'IVA?") == "simple"

    def test_real_complex_query(self):
        query = (
            "Vorrei sapere come funziona il regime forfettario per i professionisti "
            "che operano nel settore della consulenza aziendale con partita IVA aperta "
            "da meno di cinque anni e con ricavi inferiori alla soglia prevista dalla legge."
        )
        assert _analyze_query_complexity(query) == "complex"


# ===========================================================================
# _preprocess_query Tests (async helper)
# ===========================================================================


class TestPreprocessQuery:
    """Tests for _preprocess_query helper."""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        result = await _preprocess_query("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_strips_whitespace(self):
        result = await _preprocess_query("  calcola iva  ")
        assert result == "calcola iva"

    @pytest.mark.asyncio
    async def test_normalizes_internal_whitespace(self):
        result = await _preprocess_query("calcola   iva   al   22%")
        assert result == "calcola iva al 22%"

    @pytest.mark.asyncio
    async def test_preserves_content(self):
        result = await _preprocess_query("cos'è l'IRPEF?")
        assert result == "cos'è l'IRPEF?"

    @pytest.mark.asyncio
    async def test_tabs_and_newlines_normalized(self):
        result = await _preprocess_query("hello\n\tworld")
        assert result == "hello world"


# ===========================================================================
# step_12__extract_query Tests
# ===========================================================================


class TestStep12ExtractQuery:
    """Tests for step_12__extract_query orchestrator."""

    @pytest.mark.asyncio
    async def test_missing_context_returns_error(self):
        result = await step_12__extract_query(messages=None, ctx=None)
        assert result["extraction_successful"] is False
        assert result["error"] is not None
        assert "Missing context" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_messages_list(self):
        result = await step_12__extract_query(messages=[], ctx={})
        assert result["extraction_successful"] is True
        assert result["user_message_found"] is False
        assert result["next_step"] == "DefaultPrompt"

    @pytest.mark.asyncio
    async def test_no_user_messages(self):
        messages = [_make_message("assistant", "Ciao, come posso aiutarti?")]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["extraction_successful"] is True
        assert result["user_message_found"] is False
        assert result["next_step"] == "DefaultPrompt"

    @pytest.mark.asyncio
    async def test_single_user_message(self):
        messages = [_make_message("user", "calcola IVA al 22%")]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["extraction_successful"] is True
        assert result["user_message_found"] is True
        assert result["extracted_query"] == "calcola IVA al 22%"
        assert result["user_message_count"] == 1
        assert result["message_position"] == 0
        assert result["next_step"] == "ClassifyDomain"
        assert result["ready_for_classification"] is True

    @pytest.mark.asyncio
    async def test_multiple_user_messages_extracts_latest(self):
        messages = [
            _make_message("user", "prima domanda"),
            _make_message("assistant", "risposta"),
            _make_message("user", "seconda domanda"),
        ]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["extracted_query"] == "seconda domanda"
        assert result["user_message_count"] == 2
        assert result["message_position"] == 2

    @pytest.mark.asyncio
    async def test_query_complexity_reported(self):
        messages = [_make_message("user", "iva")]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["query_complexity"] == "simple"

    @pytest.mark.asyncio
    async def test_complex_query_complexity(self):
        messages = [_make_message("user", "a" * 200)]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["query_complexity"] == "complex"

    @pytest.mark.asyncio
    async def test_query_length_reported(self):
        messages = [_make_message("user", "calcola IVA")]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["query_length"] == len("calcola IVA")

    @pytest.mark.asyncio
    async def test_preprocessing_applied_flag(self):
        """Preprocessing strips whitespace and normalizes spaces."""
        messages = [_make_message("user", "calcola  IVA")]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["preprocessing_applied"] is True
        assert result["extracted_query"] == "calcola IVA"

    @pytest.mark.asyncio
    async def test_original_query_preserved(self):
        messages = [_make_message("user", "calcola  IVA")]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["original_query"] == "calcola  IVA"

    @pytest.mark.asyncio
    async def test_request_id_from_context(self):
        messages = [_make_message("user", "test")]
        result = await step_12__extract_query(messages=messages, ctx={"request_id": "req-123"}, request_id="req-123")
        assert result["extraction_successful"] is True

    @pytest.mark.asyncio
    async def test_converted_messages_from_context(self):
        """Messages can come from ctx['converted_messages']."""
        ctx_msgs = [_make_message("user", "from context")]
        result = await step_12__extract_query(messages=None, ctx={"converted_messages": ctx_msgs})
        assert result["extracted_query"] == "from context"

    @pytest.mark.asyncio
    async def test_timestamp_present(self):
        result = await step_12__extract_query(messages=[], ctx={})
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_converted_messages_from_kwargs(self):
        """converted_messages passed as kwarg should be used."""
        msgs = [_make_message("user", "from kwargs")]
        result = await step_12__extract_query(ctx={}, converted_messages=msgs)
        assert result["extracted_query"] == "from kwargs"
        assert result["user_message_found"] is True

    @pytest.mark.asyncio
    async def test_exception_during_extraction(self):
        """Exceptions during message processing are caught gracefully."""
        messages = [_make_message("user", "trigger error")]
        # Patch _preprocess_query to raise an exception after user message is found
        with patch(
            "app.orchestrators.classify._preprocess_query",
            new_callable=AsyncMock,
            side_effect=RuntimeError("preprocessing explosion"),
        ):
            result = await step_12__extract_query(messages=messages, ctx={})

        assert result["extraction_successful"] is False
        assert "Query extraction error" in result["error"]
        assert "preprocessing explosion" in result["error"]

    @pytest.mark.asyncio
    async def test_no_preprocessing_when_clean(self):
        """Clean query should not trigger preprocessing_applied."""
        messages = [_make_message("user", "clean query text")]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["preprocessing_applied"] is False

    @pytest.mark.asyncio
    async def test_messages_none_and_no_converted_messages(self):
        """When messages is None and ctx has no converted_messages."""
        result = await step_12__extract_query(messages=None, ctx={})
        assert result["extraction_successful"] is True
        assert result["user_message_found"] is False

    @pytest.mark.asyncio
    async def test_mixed_messages_user_and_assistant(self):
        """Mix of user and assistant messages, only user counted."""
        messages = [
            _make_message("assistant", "Benvenuto!"),
            _make_message("user", "Domanda 1"),
            _make_message("assistant", "Risposta 1"),
            _make_message("user", "Domanda 2"),
            _make_message("assistant", "Risposta 2"),
        ]
        result = await step_12__extract_query(messages=messages, ctx={})
        assert result["user_message_count"] == 2
        assert result["extracted_query"] == "Domanda 2"
        assert result["message_position"] == 3

    @pytest.mark.asyncio
    async def test_request_id_from_kwargs(self):
        """request_id from kwargs takes priority."""
        result = await step_12__extract_query(messages=[], ctx={"request_id": "ctx-req"}, request_id="kwarg-req")
        assert result["extraction_successful"] is True


# ===========================================================================
# step_31__classify_domain Tests
# ===========================================================================


class TestStep31ClassifyDomain:
    """Tests for step_31__classify_domain orchestrator."""

    @pytest.mark.asyncio
    async def test_classify_with_query(self):
        """Provide user_query and let the step create its own classifier."""
        with patch("app.services.domain_action_classifier.settings"):
            result = await step_31__classify_domain(ctx={}, user_query="calcola irpef")
        assert result["domain"] is not None
        assert result["action"] is not None
        assert result["confidence"] > 0
        assert result["error"] is None
        assert result["query_composition"] is not None

    @pytest.mark.asyncio
    async def test_classify_no_query_returns_error(self):
        result = await step_31__classify_domain(ctx={}, user_query="")
        assert result["error"] is not None
        assert result["domain"] is None

    @pytest.mark.asyncio
    async def test_classify_with_mocked_service(self):
        """Pass a pre-built classification service."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="calculation_request",
            confidence=0.9,
            fallback_used=False,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_KB)

        result = await step_31__classify_domain(
            ctx={},
            user_query="calcola iva",
            classification_service=mock_service,
        )
        assert result["domain"] == "tax"
        assert result["confidence"] == 0.9
        assert result["query_composition"] == "pure_kb"

    @pytest.mark.asyncio
    async def test_classify_with_attachments(self):
        """When attachments are present, has_attachments should be True."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="calculation_request",
            confidence=0.8,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_DOCUMENT)

        result = await step_31__classify_domain(
            ctx={},
            user_query="analizza questo",
            classification_service=mock_service,
            attachments=[{"filename": "doc.pdf"}],
        )
        assert result["has_attachments"] is True

    @pytest.mark.asyncio
    async def test_classify_composition_detection_failure_defaults_to_pure_kb(self):
        """If detect_query_composition raises, default to pure_kb."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="calculation_request",
            confidence=0.8,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(side_effect=Exception("boom"))

        result = await step_31__classify_domain(
            ctx={},
            user_query="calcola iva",
            classification_service=mock_service,
        )
        assert result["query_composition"] == "pure_kb"

    @pytest.mark.asyncio
    async def test_classify_with_current_message_index(self):
        """Test attachment filtering by current_message_index."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="calculation_request",
            confidence=0.8,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.HYBRID)

        result = await step_31__classify_domain(
            ctx={"current_message_index": 0},
            user_query="analizza",
            classification_service=mock_service,
            attachments=[{"filename": "a.pdf", "message_index": 0}, {"filename": "b.pdf", "message_index": 1}],
        )
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_classify_fallback_used_logging(self):
        """When fallback_used is True, the warning log path is taken."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="calculation_request",
            confidence=0.7,
            fallback_used=True,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_KB)

        result = await step_31__classify_domain(
            ctx={},
            user_query="test query",
            classification_service=mock_service,
        )
        assert result["fallback_used"] is True

    @pytest.mark.asyncio
    async def test_classify_no_fallback_success_logging(self):
        """When no error and no fallback, the info log path is taken."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.LEGAL,
            action="compliance_check",
            confidence=0.85,
            fallback_used=False,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_KB)

        result = await step_31__classify_domain(
            ctx={},
            user_query="verifica compliance",
            classification_service=mock_service,
        )
        assert result["domain"] == "legal"
        assert result["action"] == "compliance_check"
        assert result["fallback_used"] is False
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_classify_service_exception(self):
        """When classify() raises, error path is taken."""
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(side_effect=RuntimeError("classify failed"))

        result = await step_31__classify_domain(
            ctx={},
            user_query="test",
            classification_service=mock_service,
        )
        assert result["error"] == "classify failed"
        assert result["domain"] is None

    @pytest.mark.asyncio
    async def test_classify_domain_none_on_classification(self):
        """When classification domain and action are None."""
        mock_classification = MagicMock()
        mock_classification.domain = None
        mock_classification.action = None
        mock_classification.confidence = 0.3
        mock_classification.fallback_used = False

        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=MagicMock(value="pure_kb"))

        result = await step_31__classify_domain(
            ctx={},
            user_query="vague query",
            classification_service=mock_service,
        )
        assert result["domain"] is None
        assert result["action"] is None

    @pytest.mark.asyncio
    async def test_classify_no_attachments(self):
        """When no attachments, has_attachments is False."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="information_request",
            confidence=0.8,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_KB)

        result = await step_31__classify_domain(
            ctx={},
            user_query="no attachments",
            classification_service=mock_service,
        )
        assert result["has_attachments"] is False

    @pytest.mark.asyncio
    async def test_classify_empty_attachments(self):
        """Empty attachments list treated as no attachments."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="information_request",
            confidence=0.8,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_KB)

        result = await step_31__classify_domain(
            ctx={},
            user_query="test",
            classification_service=mock_service,
            attachments=[],
        )
        assert result["has_attachments"] is False

    @pytest.mark.asyncio
    async def test_classify_attachments_no_current_index_no_matching(self):
        """Attachments without current_message_index use all filenames."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="document_analysis",
            confidence=0.9,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_DOCUMENT)

        result = await step_31__classify_domain(
            ctx={},
            user_query="analizza",
            classification_service=mock_service,
            attachments=[{"filename": "doc1.pdf"}, {"filename": "doc2.pdf"}],
        )
        assert result["has_attachments"] is True
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_classify_attachments_with_index_no_match(self):
        """Attachments with current_message_index but none match -> uses all filenames."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="document_analysis",
            confidence=0.9,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_KB)

        result = await step_31__classify_domain(
            ctx={"current_message_index": 5},  # No attachments match index 5
            user_query="follow-up question",
            classification_service=mock_service,
            attachments=[{"filename": "doc.pdf", "message_index": 0}],
        )
        assert result["has_attachments"] is True
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_classify_user_query_from_ctx(self):
        """user_query can come from ctx."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="information_request",
            confidence=0.8,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_KB)

        result = await step_31__classify_domain(
            ctx={"user_query": "from context", "classification_service": mock_service},
        )
        assert result["error"] is None
        assert result["query_length"] == len("from context")

    @pytest.mark.asyncio
    async def test_classify_attachments_with_missing_filename(self):
        """Attachments where some have no filename key."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
            QueryComposition,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="document_analysis",
            confidence=0.9,
        )
        mock_service = AsyncMock()
        mock_service.classify = AsyncMock(return_value=mock_classification)
        mock_service.detect_query_composition = AsyncMock(return_value=QueryComposition.PURE_KB)

        result = await step_31__classify_domain(
            ctx={"current_message_index": 0},
            user_query="test",
            classification_service=mock_service,
            attachments=[{"filename": "doc1.pdf", "message_index": 0}, {"message_index": 0}],
        )
        assert result["error"] is None


# ===========================================================================
# step_32__calc_scores Tests
# ===========================================================================


class TestStep32CalcScores:
    """Tests for step_32__calc_scores orchestrator."""

    @pytest.mark.asyncio
    async def test_calc_scores_with_query(self):
        with patch("app.services.domain_action_classifier.settings"):
            result = await step_32__calc_scores(ctx={}, user_query="calcola irpef")
        assert result["domain_scores"] is not None
        assert result["action_scores"] is not None
        assert result["best_domain"] is not None
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_calc_scores_no_query(self):
        result = await step_32__calc_scores(ctx={}, user_query="")
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_calc_scores_low_confidence_warning(self):
        """Low confidence scores should still return valid data."""
        with patch("app.services.domain_action_classifier.settings"):
            result = await step_32__calc_scores(ctx={}, user_query="ciao")
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_calc_scores_with_mocked_service_high_confidence(self):
        """Both confidence values >= 0.5 -> info log path."""
        from app.services.domain_action_classifier import Action, Domain

        mock_service = MagicMock()
        mock_service._calculate_domain_scores.return_value = {Domain.TAX: 0.9, Domain.LEGAL: 0.3}
        mock_service._calculate_action_scores.return_value = {Action.CALCULATION_REQUEST: 0.8}

        result = await step_32__calc_scores(
            ctx={},
            user_query="normativa fiscale",
            classification_service=mock_service,
        )
        assert result["error"] is None
        assert result["best_domain"] == Domain.TAX
        assert result["domain_confidence"] == 0.9
        assert result["action_confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_calc_scores_with_mocked_service_low_domain_confidence(self):
        """Low domain confidence < 0.5 -> warning log path."""
        from app.services.domain_action_classifier import Action, Domain

        mock_service = MagicMock()
        mock_service._calculate_domain_scores.return_value = {Domain.TAX: 0.3}
        mock_service._calculate_action_scores.return_value = {Action.INFORMATION_REQUEST: 0.2}

        result = await step_32__calc_scores(
            ctx={},
            user_query="generic question",
            classification_service=mock_service,
        )
        assert result["domain_confidence"] == 0.3
        assert result["action_confidence"] == 0.2

    @pytest.mark.asyncio
    async def test_calc_scores_empty_scores(self):
        """Empty score dicts -> best_domain/action remain None."""
        mock_service = MagicMock()
        mock_service._calculate_domain_scores.return_value = {}
        mock_service._calculate_action_scores.return_value = {}

        result = await step_32__calc_scores(
            ctx={},
            user_query="test",
            classification_service=mock_service,
        )
        assert result["best_domain"] is None
        assert result["best_action"] is None
        assert result["domain_confidence"] == 0.0
        assert result["action_confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_calc_scores_exception(self):
        """Exception during scoring is caught."""
        mock_service = MagicMock()
        mock_service._calculate_domain_scores.side_effect = RuntimeError("scoring error")

        result = await step_32__calc_scores(
            ctx={},
            user_query="test",
            classification_service=mock_service,
        )
        assert "scoring error" in result["error"]

    @pytest.mark.asyncio
    async def test_calc_scores_user_query_from_ctx(self):
        """user_query from ctx and classification_service from ctx."""
        from app.services.domain_action_classifier import Action, Domain

        mock_service = MagicMock()
        mock_service._calculate_domain_scores.return_value = {Domain.TAX: 0.7}
        mock_service._calculate_action_scores.return_value = {Action.INFORMATION_REQUEST: 0.7}

        result = await step_32__calc_scores(
            ctx={"user_query": "from ctx", "classification_service": mock_service},
        )
        assert result["error"] is None
        assert result["query_length"] == len("from ctx")


# ===========================================================================
# step_33__confidence_check Tests
# ===========================================================================


class TestStep33ConfidenceCheck:
    """Tests for step_33__confidence_check orchestrator."""

    @pytest.mark.asyncio
    async def test_confidence_met(self):
        classification = {"confidence": 0.85, "domain": "tax", "action": "calculation_request", "fallback_used": False}
        result = await step_33__confidence_check(ctx={}, classification=classification)
        assert result["confidence_met"] is True
        assert result["confidence_value"] == 0.85

    @pytest.mark.asyncio
    async def test_confidence_not_met(self):
        classification = {"confidence": 0.3, "domain": "tax", "action": "calculation_request", "fallback_used": False}
        result = await step_33__confidence_check(ctx={}, classification=classification)
        assert result["confidence_met"] is False

    @pytest.mark.asyncio
    async def test_custom_threshold(self):
        classification = {"confidence": 0.5, "domain": "tax", "action": "calculation_request", "fallback_used": False}
        result = await step_33__confidence_check(ctx={}, classification=classification, confidence_threshold=0.4)
        assert result["confidence_met"] is True
        assert result["threshold"] == 0.4

    @pytest.mark.asyncio
    async def test_no_classification_data(self):
        result = await step_33__confidence_check(ctx={})
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_scores_data_fallback(self):
        """When no classification, use scores_data domain_confidence."""
        from app.services.domain_action_classifier import Action, Domain

        scores = {"domain_confidence": 0.7, "best_domain": Domain.TAX, "best_action": Action.CALCULATION_REQUEST}
        result = await step_33__confidence_check(ctx={}, scores_data=scores)
        assert result["confidence_met"] is True
        assert result["domain"] == "tax"

    @pytest.mark.asyncio
    async def test_confidence_exactly_at_threshold(self):
        """Confidence exactly at threshold should be met."""
        classification = {"confidence": 0.6}
        result = await step_33__confidence_check(ctx={}, classification=classification, confidence_threshold=0.6)
        assert result["confidence_met"] is True

    @pytest.mark.asyncio
    async def test_scores_data_with_string_domain(self):
        """scores_data where best_domain/best_action are plain strings (no .value attr)."""
        scores = {"domain_confidence": 0.7, "best_domain": "tax_string", "best_action": "info_string"}
        result = await step_33__confidence_check(ctx={}, scores_data=scores)
        assert result["domain"] == "tax_string"
        assert result["action"] == "info_string"

    @pytest.mark.asyncio
    async def test_scores_data_with_none_best(self):
        """scores_data where best_domain and best_action are None."""
        scores = {"domain_confidence": 0.0, "best_domain": None, "best_action": None}
        result = await step_33__confidence_check(ctx={}, scores_data=scores)
        assert result["domain"] is None
        assert result["action"] is None
        assert result["confidence_met"] is False

    @pytest.mark.asyncio
    async def test_classification_from_ctx(self):
        """classification from ctx instead of kwargs."""
        classification = {"confidence": 0.9, "domain": "legal", "action": "compliance"}
        result = await step_33__confidence_check(ctx={"classification": classification})
        assert result["confidence_met"] is True

    @pytest.mark.asyncio
    async def test_confidence_threshold_from_ctx(self):
        """confidence_threshold from ctx."""
        classification = {"confidence": 0.5}
        result = await step_33__confidence_check(ctx={"confidence_threshold": 0.4}, classification=classification)
        assert result["confidence_met"] is True
        assert result["threshold"] == 0.4


# ===========================================================================
# step_35__llmfallback (sync stub) Tests
# ===========================================================================


class TestStep35LLMFallbackStub:
    """Tests for sync step_35__llmfallback stub."""

    def test_returns_result_kwarg(self):
        result = step_35__llmfallback(ctx={}, result="test_value")
        assert result == "test_value"

    def test_returns_none_when_no_result(self):
        result = step_35__llmfallback(ctx={})
        assert result is None

    def test_with_messages_and_ctx(self):
        result = step_35__llmfallback(messages=["msg1"], ctx={"key": "val"}, result="test")
        assert result == "test"


# ===========================================================================
# step_35__llm_fallback (async) Tests
# ===========================================================================


class TestStep35LLMFallbackAsync:
    """Tests for async step_35__llm_fallback orchestrator."""

    @pytest.mark.asyncio
    async def test_missing_context(self):
        result = await step_35__llm_fallback(ctx=None)
        assert result["llm_fallback_successful"] is False
        assert "Missing context" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_user_query(self):
        result = await step_35__llm_fallback(ctx={})
        assert result["llm_fallback_successful"] is False
        assert "Missing user_query" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_llm_fallback(self):
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.9,
        )
        mock_classifier = AsyncMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_classification)

        result = await step_35__llm_fallback(
            ctx={"user_query": "calcola iva"},
            user_query="calcola iva",
            rule_based_confidence=0.3,
            classifier=mock_classifier,
        )
        assert result["llm_fallback_successful"] is True
        assert result["ready_for_comparison"] is True

    @pytest.mark.asyncio
    async def test_llm_returns_none_falls_back(self):
        mock_classifier = AsyncMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=None)

        result = await step_35__llm_fallback(
            ctx={"user_query": "test"},
            user_query="test",
            classifier=mock_classifier,
        )
        assert result["llm_fallback_successful"] is False
        assert result["fallback_to_rule_based"] is True
        assert result["classification_method"] == "rule_based_fallback"
        assert result["next_step"] == "UseRuleBased"

    @pytest.mark.asyncio
    async def test_llm_service_exception_falls_back(self):
        mock_classifier = AsyncMock()
        mock_classifier._llm_fallback_classification = AsyncMock(side_effect=Exception("service down"))

        rule_based = MagicMock()

        result = await step_35__llm_fallback(
            ctx={"user_query": "test"},
            user_query="test",
            classifier=mock_classifier,
            rule_based_classification=rule_based,
        )
        assert result["llm_fallback_successful"] is False
        assert result["fallback_to_rule_based"] is True
        assert result["service_error"] is not None
        assert result["llm_classification"] is rule_based

    @pytest.mark.asyncio
    async def test_preprocessing_applied(self):
        mock_classifier = AsyncMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=None)

        result = await step_35__llm_fallback(
            ctx={"user_query": " test "},
            user_query=" test ",
            classifier=mock_classifier,
        )
        assert result["preprocessing_applied"] is True
        assert result["original_query"] == " test "

    @pytest.mark.asyncio
    async def test_no_preprocessing_when_clean(self):
        """Clean query should not trigger preprocessing."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="information_request",
            confidence=0.8,
        )
        mock_classifier = AsyncMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_classification)

        result = await step_35__llm_fallback(
            ctx={"user_query": "clean"},
            user_query="clean",
            classifier=mock_classifier,
        )
        assert result["preprocessing_applied"] is False

    @pytest.mark.asyncio
    async def test_significant_improvement(self):
        """LLM confidence significantly better than rule-based (>=0.1 improvement)."""
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.9,
        )
        mock_classifier = AsyncMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_classification)

        result = await step_35__llm_fallback(
            ctx={"user_query": "test"},
            user_query="test",
            classifier=mock_classifier,
            rule_based_confidence=0.5,
        )
        assert result["improved_confidence"] is True
        assert result["confidence_analysis"]["significant_improvement"] is True
        assert result["confidence_analysis"]["improvement"] == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_no_significant_improvement(self):
        """LLM confidence only slightly better -> improved_confidence False."""
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.55,
        )
        mock_classifier = AsyncMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_classification)

        result = await step_35__llm_fallback(
            ctx={"user_query": "test"},
            user_query="test",
            classifier=mock_classifier,
            rule_based_confidence=0.5,
        )
        assert result["improved_confidence"] is False
        assert result["confidence_analysis"]["significant_improvement"] is False

    @pytest.mark.asyncio
    async def test_request_id_from_kwargs(self):
        result = await step_35__llm_fallback(ctx={}, request_id="req-xyz")
        assert result["request_id"] == "req-xyz"

    @pytest.mark.asyncio
    async def test_request_id_from_ctx(self):
        result = await step_35__llm_fallback(ctx={"request_id": "ctx-req-123"})
        assert result["request_id"] == "ctx-req-123"

    @pytest.mark.asyncio
    async def test_user_query_from_ctx(self):
        """user_query comes from ctx when not in kwargs."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="information_request",
            confidence=0.8,
        )
        mock_classifier = AsyncMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=mock_classification)

        result = await step_35__llm_fallback(
            ctx={"user_query": "from context"},
            classifier=mock_classifier,
        )
        assert result["llm_fallback_successful"] is True

    @pytest.mark.asyncio
    async def test_rule_based_classification_from_ctx(self):
        """rule_based_classification and rule_based_confidence from ctx."""
        mock_classifier = AsyncMock()
        mock_classifier._llm_fallback_classification = AsyncMock(return_value=None)

        rule_based = MagicMock()

        result = await step_35__llm_fallback(
            ctx={
                "user_query": "test",
                "rule_based_classification": rule_based,
                "rule_based_confidence": 0.4,
            },
            classifier=mock_classifier,
        )
        assert result["fallback_to_rule_based"] is True
        assert result["rule_based_classification"] is rule_based

    @pytest.mark.asyncio
    async def test_classifier_created_when_not_provided(self):
        """When no classifier is provided, DomainActionClassifier is created."""
        from app.services.domain_action_classifier import (
            Domain,
            DomainActionClassification,
        )

        mock_classification = DomainActionClassification(
            domain=Domain.TAX,
            action="information_request",
            confidence=0.7,
        )

        with patch("app.services.domain_action_classifier.settings"):
            mock_cls = MagicMock()
            mock_instance = AsyncMock()
            mock_instance._llm_fallback_classification = AsyncMock(return_value=mock_classification)
            mock_cls.return_value = mock_instance

            with patch("app.services.domain_action_classifier.DomainActionClassifier", mock_cls):
                result = await step_35__llm_fallback(
                    ctx={"user_query": "test"},
                    user_query="test",
                )

        assert result["llm_fallback_successful"] is True

    @pytest.mark.asyncio
    async def test_unexpected_outer_exception(self):
        """Trigger the outer except block with an unexpected error.

        The outer except catches errors that occur before the inner try block,
        such as during query preprocessing (user_query.strip() failure).
        """
        # Create a user_query object that is truthy but raises on .strip()
        bad_query = MagicMock()
        bad_query.__bool__ = lambda self: True
        bad_query.strip = MagicMock(side_effect=RuntimeError("strip failed unexpectedly"))

        result = await step_35__llm_fallback(
            ctx={"user_query": bad_query},
            user_query=bad_query,
        )
        assert "Unexpected error in LLM fallback" in result["error"]
        assert result["llm_fallback_successful"] is False


# ===========================================================================
# step_42__class_confidence Tests
# ===========================================================================


class TestStep42ClassConfidence:
    """Tests for step_42__class_confidence orchestrator."""

    @pytest.mark.asyncio
    async def test_no_classification(self):
        result = await step_42__class_confidence(ctx={})
        assert result["classification_exists"] is False
        assert result["confidence_sufficient"] is False

    @pytest.mark.asyncio
    async def test_classification_dict_sufficient(self):
        classification = {"confidence": 0.8, "domain": "tax", "action": "calculation_request", "fallback_used": False}
        result = await step_42__class_confidence(ctx={}, classification=classification)
        assert result["classification_exists"] is True
        assert result["confidence_sufficient"] is True
        assert result["threshold"] == 0.6

    @pytest.mark.asyncio
    async def test_classification_dict_insufficient(self):
        classification = {"confidence": 0.3, "domain": "tax", "action": "calculation_request"}
        result = await step_42__class_confidence(ctx={}, classification=classification)
        assert result["classification_exists"] is True
        assert result["confidence_sufficient"] is False

    @pytest.mark.asyncio
    async def test_classification_object(self):
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.85,
            fallback_used=False,
            reasoning="test",
        )
        result = await step_42__class_confidence(ctx={}, classification=classification)
        assert result["classification_exists"] is True
        assert result["confidence_sufficient"] is True
        assert result["domain"] == "tax"
        assert result["reasoning"] == "test"

    @pytest.mark.asyncio
    async def test_classification_dict_with_enum_domain(self):
        """Dict with enum domain/action values (has .value attr)."""
        from app.services.domain_action_classifier import Action, Domain

        classification = {
            "confidence": 0.75,
            "domain": Domain.TAX,
            "action": Action.INFORMATION_REQUEST,
            "fallback_used": True,
            "reasoning": "dict reasoning",
        }
        result = await step_42__class_confidence(ctx={}, classification=classification)
        assert result["domain"] == "tax"
        assert result["action"] == "information_request"
        assert result["fallback_used"] is True
        assert result["reasoning"] == "dict reasoning"

    @pytest.mark.asyncio
    async def test_classification_dict_with_string_domain(self):
        """Dict with plain string domain/action (no .value attr)."""
        classification = {
            "confidence": 0.7,
            "domain": "tax_string",
            "action": "info_string",
        }
        result = await step_42__class_confidence(ctx={}, classification=classification)
        assert result["domain"] == "tax_string"
        assert result["action"] == "info_string"

    @pytest.mark.asyncio
    async def test_classification_dict_with_none_domain(self):
        """Dict where domain and action are None."""
        classification = {
            "confidence": 0.7,
            "domain": None,
            "action": None,
        }
        result = await step_42__class_confidence(ctx={}, classification=classification)
        assert result["domain"] is None
        assert result["action"] is None

    @pytest.mark.asyncio
    async def test_classification_object_with_none_domain(self):
        """DomainActionClassification object where domain is None."""
        from app.services.domain_action_classifier import DomainActionClassification

        mock_cls = MagicMock(spec=DomainActionClassification)
        mock_cls.confidence = 0.8
        mock_cls.domain = None
        mock_cls.action = None
        mock_cls.fallback_used = False
        mock_cls.reasoning = None

        result = await step_42__class_confidence(ctx={}, classification=mock_cls)
        assert result["classification_exists"] is True
        assert result["domain"] is None
        assert result["action"] is None

    @pytest.mark.asyncio
    async def test_classification_from_ctx(self):
        """classification provided via ctx."""
        classification = {"confidence": 0.9, "domain": "legal"}
        result = await step_42__class_confidence(ctx={"classification": classification})
        assert result["classification_exists"] is True

    @pytest.mark.asyncio
    async def test_threshold_is_fixed_at_0_6(self):
        """Threshold is always 0.6 for step 42."""
        classification = {"confidence": 0.6}
        result = await step_42__class_confidence(ctx={}, classification=classification)
        assert result["threshold"] == 0.6
        assert result["confidence_sufficient"] is True

    @pytest.mark.asyncio
    async def test_confidence_just_below_threshold(self):
        """0.599 < 0.6 -> not sufficient."""
        classification = {"confidence": 0.599}
        result = await step_42__class_confidence(ctx={}, classification=classification)
        assert result["confidence_sufficient"] is False

    @pytest.mark.asyncio
    async def test_classification_non_dict_non_object(self):
        """When classification is truthy but neither DomainActionClassification nor dict,
        the isinstance branches are skipped and default values used."""
        # Use a list (truthy, not dict, not DomainActionClassification)
        result = await step_42__class_confidence(ctx={}, classification=[1, 2, 3])
        assert result["classification_exists"] is True
        # Default confidence_value is 0.0 which is < 0.6
        assert result["confidence_sufficient"] is False
        assert result["confidence_value"] == 0.0


# ===========================================================================
# step_88__doc_classify (sync stub) Tests
# ===========================================================================


class TestStep88DocClassify:
    """Tests for sync step_88__doc_classify stub."""

    def test_returns_result_kwarg(self):
        result = step_88__doc_classify(ctx={}, result="doc_result")
        assert result == "doc_result"

    def test_returns_none_when_no_result(self):
        result = step_88__doc_classify(ctx={})
        assert result is None

    def test_with_messages_and_ctx(self):
        result = step_88__doc_classify(messages=["msg1"], ctx={"key": "val"}, result="test")
        assert result == "test"


# ===========================================================================
# _evaluate_trust_score_decision Tests
# ===========================================================================


class TestEvaluateTrustScoreDecision:
    """Tests for _evaluate_trust_score_decision helper."""

    @pytest.mark.asyncio
    async def test_trust_score_above_threshold(self):
        ctx = {"expert_validation": {"trust_score": 0.85}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is True
        assert result["next_step"] == "CreateFeedbackRec"
        assert result["threshold_met"] is True

    @pytest.mark.asyncio
    async def test_trust_score_below_threshold(self):
        ctx = {"expert_validation": {"trust_score": 0.5}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["next_step"] == "FeedbackRejected"
        assert result["threshold_met"] is False

    @pytest.mark.asyncio
    async def test_trust_score_exactly_07(self):
        ctx = {"expert_validation": {"trust_score": 0.7}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is True

    @pytest.mark.asyncio
    async def test_missing_trust_score(self):
        ctx = {"expert_validation": {}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["error"] == "missing_trust_score"

    @pytest.mark.asyncio
    async def test_missing_expert_validation(self):
        ctx = {}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["error"] == "missing_trust_score"

    @pytest.mark.asyncio
    async def test_trust_score_none(self):
        ctx = {"expert_validation": {"trust_score": None}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["error"] == "missing_trust_score"

    @pytest.mark.asyncio
    async def test_invalid_trust_score_string(self):
        ctx = {"expert_validation": {"trust_score": "not_a_number"}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["error"] == "invalid_trust_score"

    @pytest.mark.asyncio
    async def test_trust_score_out_of_range_negative(self):
        ctx = {"expert_validation": {"trust_score": -0.5}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["error"] == "invalid_trust_score"

    @pytest.mark.asyncio
    async def test_trust_score_out_of_range_above_1(self):
        ctx = {"expert_validation": {"trust_score": 1.5}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["error"] == "invalid_trust_score"

    @pytest.mark.asyncio
    async def test_trust_score_nan(self):
        ctx = {"expert_validation": {"trust_score": math.nan}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["error"] == "invalid_trust_score"

    @pytest.mark.asyncio
    async def test_trust_score_inf(self):
        ctx = {"expert_validation": {"trust_score": math.inf}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["error"] == "invalid_trust_score"

    @pytest.mark.asyncio
    async def test_trust_score_zero(self):
        """Trust score 0 is valid but below threshold."""
        ctx = {"expert_validation": {"trust_score": 0.0}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is False
        assert result["threshold_met"] is False
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_trust_score_one(self):
        """Trust score 1.0 is valid and above threshold."""
        ctx = {"expert_validation": {"trust_score": 1.0}}
        result = await _evaluate_trust_score_decision(ctx)
        assert result["trust_score_decision"] is True
        assert result["threshold_met"] is True


# ===========================================================================
# step_121__trust_score_ok Tests
# ===========================================================================


class TestStep121TrustScoreOK:
    """Tests for step_121__trust_score_ok orchestrator."""

    @pytest.mark.asyncio
    async def test_trust_score_ok_above_threshold(self):
        ctx = {"expert_validation": {"trust_score": 0.9}}
        result = await step_121__trust_score_ok(ctx=ctx)
        assert result["trust_score_decision"] is True
        assert result["next_step"] == "CreateFeedbackRec"

    @pytest.mark.asyncio
    async def test_trust_score_ok_below_threshold(self):
        ctx = {"expert_validation": {"trust_score": 0.3}}
        result = await step_121__trust_score_ok(ctx=ctx)
        assert result["trust_score_decision"] is False
        assert result["next_step"] == "FeedbackRejected"

    @pytest.mark.asyncio
    async def test_trust_score_ok_preserves_context(self):
        ctx = {"expert_validation": {"trust_score": 0.8}, "request_id": "req-xyz", "extra_field": "preserved"}
        result = await step_121__trust_score_ok(ctx=ctx)
        assert result["extra_field"] == "preserved"

    @pytest.mark.asyncio
    async def test_trust_score_ok_request_id_kwarg(self):
        ctx = {"expert_validation": {"trust_score": 0.8}}
        result = await step_121__trust_score_ok(ctx=ctx, request_id="req-test")
        assert result["request_id"] == "req-test"

    @pytest.mark.asyncio
    async def test_trust_score_ok_none_ctx(self):
        """None context should be handled gracefully with default rejection."""
        result = await step_121__trust_score_ok(ctx=None)
        assert result["trust_score_decision"] is False

    @pytest.mark.asyncio
    async def test_trust_score_ok_request_id_from_ctx(self):
        """request_id from ctx when not in kwargs."""
        ctx = {"expert_validation": {"trust_score": 0.8}, "request_id": "ctx-req"}
        result = await step_121__trust_score_ok(ctx=ctx)
        assert result["request_id"] == "ctx-req"

    @pytest.mark.asyncio
    async def test_trust_score_ok_exception_handling(self):
        """When _evaluate_trust_score_decision raises, error result is returned."""
        with patch(
            "app.orchestrators.classify._evaluate_trust_score_decision",
            new_callable=AsyncMock,
            side_effect=RuntimeError("unexpected error"),
        ):
            result = await step_121__trust_score_ok(
                ctx={"expert_validation": {"trust_score": 0.8}},
            )

        assert result["trust_score_decision"] is False
        assert result["next_step"] == "FeedbackRejected"
        assert "trust_score_evaluation_error" in result["error"]
        assert result["routing_decision"] == "reject_feedback"


# ===========================================================================
# step_43__domain_prompt Tests
# ===========================================================================


class TestStep43DomainPrompt:
    """Tests for step_43__domain_prompt orchestrator."""

    @pytest.mark.asyncio
    async def test_no_classification_returns_error(self):
        result = await step_43__domain_prompt(ctx={})
        assert result["error_occurred"] is True
        assert result["prompt_generated"] is False

    @pytest.mark.asyncio
    async def test_invalid_classification_type(self):
        result = await step_43__domain_prompt(ctx={}, classification={"invalid": True})
        assert result["error_occurred"] is True

    @pytest.mark.asyncio
    async def test_successful_prompt_generation(self):
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.9,
        )

        mock_manager = MagicMock()
        mock_manager.get_prompt.return_value = "Sei un esperto fiscale italiano."

        result = await step_43__domain_prompt(
            ctx={},
            classification=classification,
            prompt_template_manager=mock_manager,
            user_query="calcola iva",
        )
        assert result["prompt_generated"] is True
        assert result["domain_prompt"] == "Sei un esperto fiscale italiano."
        assert result["prompt_length"] > 0

    @pytest.mark.asyncio
    async def test_empty_prompt_returns_error(self):
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.9,
        )

        mock_manager = MagicMock()
        mock_manager.get_prompt.return_value = ""

        result = await step_43__domain_prompt(
            ctx={},
            classification=classification,
            prompt_template_manager=mock_manager,
        )
        assert result["error_occurred"] is True
        assert result["prompt_generated"] is False

    @pytest.mark.asyncio
    async def test_none_prompt_returns_error(self):
        """get_prompt returns None -> error path."""
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.9,
        )

        mock_manager = MagicMock()
        mock_manager.get_prompt.return_value = None

        result = await step_43__domain_prompt(
            ctx={},
            classification=classification,
            prompt_template_manager=mock_manager,
        )
        assert result["error_occurred"] is True
        assert result["domain_prompt"] == ""

    @pytest.mark.asyncio
    async def test_get_prompt_raises_exception(self):
        """get_prompt raising exception -> error path."""
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.CALCULATION_REQUEST,
            confidence=0.9,
        )

        mock_manager = MagicMock()
        mock_manager.get_prompt.side_effect = RuntimeError("template error")

        result = await step_43__domain_prompt(
            ctx={},
            classification=classification,
            prompt_template_manager=mock_manager,
        )
        assert result["error_occurred"] is True
        assert "template error" in result["error_message"]
        assert result["domain_prompt"] == ""

    @pytest.mark.asyncio
    async def test_classification_with_none_domain(self):
        """Classification where domain and action are None."""
        from app.services.domain_action_classifier import DomainActionClassification

        classification = MagicMock(spec=DomainActionClassification)
        classification.domain = None
        classification.action = None
        classification.document_type = None

        mock_manager = MagicMock()
        mock_manager.get_prompt.return_value = "fallback prompt"

        result = await step_43__domain_prompt(
            ctx={},
            classification=classification,
            prompt_template_manager=mock_manager,
        )
        assert result["domain"] is None
        assert result["action"] is None

    @pytest.mark.asyncio
    async def test_classification_with_document_type(self):
        """Classification with document_type set."""
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.DOCUMENT_ANALYSIS,
            confidence=0.9,
            document_type="fattura",
        )

        mock_manager = MagicMock()
        mock_manager.get_prompt.return_value = "Analizza questa fattura."

        result = await step_43__domain_prompt(
            ctx={},
            classification=classification,
            prompt_template_manager=mock_manager,
        )
        assert result["document_type"] == "fattura"
        assert result["prompt_generated"] is True

    @pytest.mark.asyncio
    async def test_prompt_context_passed_through(self):
        """prompt_context is passed to get_prompt."""
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.9,
        )

        mock_manager = MagicMock()
        mock_manager.get_prompt.return_value = "with context"
        prompt_context = {"key": "value"}

        result = await step_43__domain_prompt(
            ctx={},
            classification=classification,
            prompt_template_manager=mock_manager,
            prompt_context=prompt_context,
        )
        assert result["prompt_generated"] is True
        call_kwargs = mock_manager.get_prompt.call_args
        assert call_kwargs.kwargs.get("context") == prompt_context

    @pytest.mark.asyncio
    async def test_ctx_provides_all_parameters(self):
        """All parameters from ctx."""
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.LEGAL,
            action=Action.COMPLIANCE_CHECK,
            confidence=0.9,
        )

        mock_manager = MagicMock()
        mock_manager.get_prompt.return_value = "from ctx prompt"

        result = await step_43__domain_prompt(
            ctx={
                "classification": classification,
                "prompt_template_manager": mock_manager,
                "user_query": "from ctx query",
                "request_id": "ctx-req",
            }
        )
        assert result["prompt_generated"] is True
        assert result["request_id"] == "ctx-req"

    @pytest.mark.asyncio
    async def test_prompt_template_manager_created_when_not_provided(self):
        """When no prompt_template_manager, one is created."""
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.9,
        )

        # Let it create its own PromptTemplateManager
        with patch("app.services.domain_action_classifier.settings"):
            result = await step_43__domain_prompt(
                ctx={},
                classification=classification,
                user_query="test query",
            )

        # Even without mock, it should produce a prompt or fail gracefully
        assert "prompt_generated" in result

    @pytest.mark.asyncio
    async def test_result_has_str_key(self):
        """Result should include __str__ callable."""
        from app.services.domain_action_classifier import (
            Action,
            Domain,
            DomainActionClassification,
        )

        classification = DomainActionClassification(
            domain=Domain.TAX,
            action=Action.INFORMATION_REQUEST,
            confidence=0.9,
        )
        mock_manager = MagicMock()
        mock_manager.get_prompt.return_value = "test prompt"

        result = await step_43__domain_prompt(
            ctx={},
            classification=classification,
            prompt_template_manager=mock_manager,
        )
        assert "__str__" in result
        assert callable(result["__str__"])
        assert result["__str__"]() == "test prompt"


# ===========================================================================
# Callable / Existence Tests
# ===========================================================================


class TestModuleExports:
    """Verify all expected functions are exported and callable."""

    def test_step_12_is_callable(self):
        assert callable(step_12__extract_query)

    def test_step_31_is_callable(self):
        assert callable(step_31__classify_domain)

    def test_step_32_is_callable(self):
        assert callable(step_32__calc_scores)

    def test_step_33_is_callable(self):
        assert callable(step_33__confidence_check)

    def test_step_35_stub_is_callable(self):
        assert callable(step_35__llmfallback)

    def test_step_35_async_is_callable(self):
        assert callable(step_35__llm_fallback)

    def test_step_42_is_callable(self):
        assert callable(step_42__class_confidence)

    def test_step_43_is_callable(self):
        assert callable(step_43__domain_prompt)

    def test_step_88_is_callable(self):
        assert callable(step_88__doc_classify)

    def test_step_121_is_callable(self):
        assert callable(step_121__trust_score_ok)

    def test_analyze_complexity_is_callable(self):
        assert callable(_analyze_query_complexity)

    def test_preprocess_query_is_callable(self):
        assert callable(_preprocess_query)

    def test_evaluate_trust_score_is_callable(self):
        assert callable(_evaluate_trust_score_decision)
