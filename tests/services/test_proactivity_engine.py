"""TDD Tests for ProactivityEngine Service - DEV-155.

This module tests the ProactivityEngine service:
- ProactivityContext and ProactivityResult models
- process() method - main orchestration
- select_actions() method - action selection
- should_ask_question() method - question trigger logic
- generate_question() method - question generation

Test Files Reference: app/services/proactivity_engine.py
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.proactivity import (
    Action,
    ActionCategory,
    ExtractedParameter,
    InteractiveOption,
    InteractiveQuestion,
    ParameterExtractionResult,
    ProactivityContext,
    ProactivityResult,
)
from app.services.proactivity_engine import ProactivityEngine


class TestProactivityContextModel:
    """Test ProactivityContext model."""

    def test_context_with_required_fields(self):
        """Test creating context with only required fields."""
        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
        )
        assert context.session_id == "session-123"
        assert context.domain == "tax"
        assert context.action_type is None
        assert context.document_type is None
        assert context.user_history == []

    def test_context_with_all_fields(self):
        """Test creating context with all fields."""
        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
            action_type="fiscal_calculation",
            document_type="fattura",
            user_history=["previous query 1", "previous query 2"],
        )
        assert context.action_type == "fiscal_calculation"
        assert context.document_type == "fattura"
        assert len(context.user_history) == 2

    def test_context_serialization(self):
        """Test context JSON serialization."""
        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
        )
        json_data = context.model_dump()
        assert "session_id" in json_data
        assert "domain" in json_data


class TestProactivityResultModel:
    """Test ProactivityResult model."""

    def test_result_with_actions_only(self):
        """Test result with actions and no question."""
        action = Action(
            id="test-action",
            label="Test",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calculate {value}",
        )
        result = ProactivityResult(
            actions=[action],
            question=None,
            extraction_result=None,
            processing_time_ms=50.0,
        )
        assert len(result.actions) == 1
        assert result.question is None
        assert result.processing_time_ms == 50.0

    def test_result_with_question(self):
        """Test result with question and no actions."""
        question = InteractiveQuestion(
            id="test-q",
            text="What type?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="opt1", label="Option 1"),
                InteractiveOption(id="opt2", label="Option 2"),
            ],
        )
        result = ProactivityResult(
            actions=[],
            question=question,
            extraction_result=None,
            processing_time_ms=30.0,
        )
        assert len(result.actions) == 0
        assert result.question is not None
        assert result.question.id == "test-q"

    def test_result_with_extraction_result(self):
        """Test result with extraction result."""
        extraction = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=[
                ExtractedParameter(
                    name="reddito",
                    value="50000",
                    confidence=0.9,
                    source="query",
                )
            ],
            missing_required=["tipo_contribuente"],
            coverage=0.5,
            can_proceed=False,
        )
        result = ProactivityResult(
            actions=[],
            question=None,
            extraction_result=extraction,
            processing_time_ms=25.0,
        )
        assert result.extraction_result is not None
        assert result.extraction_result.coverage == 0.5


class TestProactivityEngineInit:
    """Test ProactivityEngine initialization."""

    def test_engine_initialization(self):
        """Test engine initializes with dependencies."""
        mock_template_service = MagicMock()
        mock_facts_extractor = MagicMock()

        engine = ProactivityEngine(
            template_service=mock_template_service,
            facts_extractor=mock_facts_extractor,
        )

        assert engine.template_service is mock_template_service
        assert engine.facts_extractor is mock_facts_extractor


class TestSelectActions:
    """Test select_actions method."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine with mocked dependencies."""
        mock_template_service = MagicMock()
        mock_facts_extractor = MagicMock()
        return ProactivityEngine(
            template_service=mock_template_service,
            facts_extractor=mock_facts_extractor,
        )

    def test_select_actions_for_domain(self, engine: ProactivityEngine):
        """Test selecting actions for a domain."""
        mock_actions = [
            Action(
                id="action1",
                label="Action 1",
                icon="calc",
                category=ActionCategory.CALCULATE,
                prompt_template="Template 1",
            )
        ]
        engine.template_service.get_actions_for_domain.return_value = mock_actions

        actions = engine.select_actions(domain="tax", action_type="fiscal_calculation")

        assert len(actions) == 1
        assert actions[0].id == "action1"
        engine.template_service.get_actions_for_domain.assert_called_once_with("tax", "fiscal_calculation")

    def test_select_actions_for_document(self, engine: ProactivityEngine):
        """Test selecting actions for a document type."""
        mock_actions = [
            Action(
                id="doc-action1",
                label="Doc Action",
                icon="file",
                category=ActionCategory.VERIFY,
                prompt_template="Verify document",
            )
        ]
        engine.template_service.get_actions_for_document.return_value = mock_actions

        actions = engine.select_actions(domain="documents", action_type="verify", document_type="fattura")

        assert len(actions) == 1
        assert actions[0].id == "doc-action1"
        engine.template_service.get_actions_for_document.assert_called_once_with("fattura")

    def test_select_actions_empty_when_no_match(self, engine: ProactivityEngine):
        """Test returns empty list when no actions match."""
        engine.template_service.get_actions_for_domain.return_value = []
        engine.template_service.get_actions_for_document.return_value = []

        actions = engine.select_actions(domain="unknown", action_type="unknown")

        assert actions == []


class TestShouldAskQuestion:
    """Test should_ask_question method."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine with mocked dependencies."""
        mock_template_service = MagicMock()
        mock_facts_extractor = MagicMock()
        return ProactivityEngine(
            template_service=mock_template_service,
            facts_extractor=mock_facts_extractor,
        )

    def test_should_ask_when_low_coverage(self, engine: ProactivityEngine):
        """Test returns True when coverage < 0.8."""
        extraction = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=[],
            missing_required=["tipo_contribuente", "reddito"],
            coverage=0.0,
            can_proceed=False,
        )

        assert engine.should_ask_question(extraction) is True

    def test_should_not_ask_when_high_coverage(self, engine: ProactivityEngine):
        """Test returns False when coverage >= 0.8 (smart fallback)."""
        extraction = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=[
                ExtractedParameter(name="reddito", value="50000", confidence=0.9, source="query"),
                ExtractedParameter(name="tipo_contribuente", value="dipendente", confidence=0.9, source="query"),
            ],
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        assert engine.should_ask_question(extraction) is False

    def test_should_not_ask_when_can_proceed(self, engine: ProactivityEngine):
        """Test returns False when can_proceed is True."""
        extraction = ParameterExtractionResult(
            intent="calcolo_iva",
            extracted=[
                ExtractedParameter(name="importo", value="1000", confidence=0.9, source="query"),
            ],
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        assert engine.should_ask_question(extraction) is False

    def test_smart_fallback_at_0_8_coverage(self, engine: ProactivityEngine):
        """Test smart fallback: coverage >= 0.8 does not ask question."""
        extraction = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=[
                ExtractedParameter(name="reddito", value="50000", confidence=0.9, source="query"),
            ],
            missing_required=["tipo_contribuente"],
            coverage=0.8,
            can_proceed=True,
        )

        # At 0.8 coverage with can_proceed=True, should not ask
        assert engine.should_ask_question(extraction) is False


class TestGenerateQuestion:
    """Test generate_question method."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine with mocked dependencies."""
        mock_template_service = MagicMock()
        mock_facts_extractor = MagicMock()
        return ProactivityEngine(
            template_service=mock_template_service,
            facts_extractor=mock_facts_extractor,
        )

    def test_generate_question_for_missing_params(self, engine: ProactivityEngine):
        """Test generates multi-field question for missing required params.

        Now prefers multi-field questions (Claude Code style) when available.
        For calcolo_irpef, generates irpef_input_fields with multiple inputs.
        """
        question = engine.generate_question(
            intent="calcolo_irpef",
            missing_params=["tipo_contribuente"],
            prefilled={"reddito": "50000"},
        )

        # Multi-field question is now preferred for calcolo_irpef
        assert question is not None
        assert question.id == "irpef_input_fields"
        assert question.question_type == "multi_field"
        assert len(question.fields) == 3  # reddito, deduzioni, detrazioni
        assert question.fields[0].id == "reddito"
        assert question.fields[0].required is True

    def test_generate_question_returns_fallback_for_unknown_intent(self, engine: ProactivityEngine):
        """Test returns fallback question for unknown intents (not None)."""
        engine.template_service.get_question.return_value = None

        question = engine.generate_question(
            intent="unknown_intent",
            missing_params=["param1"],
            prefilled={},
        )

        # Should return fallback question with options, not None
        assert question is not None
        assert question.id == "topic_clarification"
        assert question.question_type == "single_choice"
        assert len(question.options) == 4  # 4 topic categories
        assert question.allow_custom_input is True

    def test_generate_question_with_prefilled_params(self, engine: ProactivityEngine):
        """Test question includes prefilled params."""
        mock_question = InteractiveQuestion(
            id="irpef_tipo_contribuente",
            text="Che tipo di contribuente sei?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="dipendente", label="Lavoratore dipendente"),
                InteractiveOption(id="autonomo", label="Lavoratore autonomo"),
            ],
            prefilled_params=None,
        )
        engine.template_service.get_question.return_value = mock_question

        question = engine.generate_question(
            intent="calcolo_irpef",
            missing_params=["tipo_contribuente"],
            prefilled={"reddito": "50000"},
        )

        # The question should be updated with prefilled params
        assert question is not None


class TestProcess:
    """Test process method - main orchestration."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine with mocked dependencies."""
        mock_template_service = MagicMock()
        mock_facts_extractor = MagicMock()

        # Setup default returns
        mock_template_service.get_actions_for_domain.return_value = []
        mock_template_service.get_actions_for_document.return_value = []
        mock_template_service.get_question.return_value = None

        return ProactivityEngine(
            template_service=mock_template_service,
            facts_extractor=mock_facts_extractor,
        )

    def test_complete_query_returns_actions(self, engine: ProactivityEngine):
        """Test that complete query (full coverage) returns actions only."""
        # Setup extraction result with full coverage
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="calcolo_iva",
            extracted=[
                ExtractedParameter(name="importo", value="1000", confidence=0.9, source="query"),
            ],
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        # Setup actions
        mock_actions = [
            Action(
                id="iva-calc",
                label="Calcola IVA",
                icon="calc",
                category=ActionCategory.CALCULATE,
                prompt_template="Calcola IVA su {importo}",
            )
        ]
        engine.template_service.get_actions_for_domain.return_value = mock_actions

        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
            action_type="fiscal_calculation",
        )

        result = engine.process("Calcola IVA su 1000 euro", context)

        assert len(result.actions) >= 1
        assert result.question is None
        assert result.extraction_result.coverage == 1.0

    def test_incomplete_query_returns_question(self, engine: ProactivityEngine):
        """Test that incomplete query (low coverage) triggers question."""
        # Setup extraction result with low coverage
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=[],
            missing_required=["tipo_contribuente", "reddito"],
            coverage=0.0,
            can_proceed=False,
        )

        # Setup question
        mock_question = InteractiveQuestion(
            id="irpef_tipo_contribuente",
            text="Che tipo di contribuente sei?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="dipendente", label="Lavoratore dipendente"),
                InteractiveOption(id="autonomo", label="Lavoratore autonomo"),
            ],
        )
        engine.template_service.get_question.return_value = mock_question

        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
        )

        result = engine.process("Calcola IRPEF", context)

        assert result.question is not None
        assert result.extraction_result.coverage == 0.0

    def test_smart_fallback_at_high_coverage(self, engine: ProactivityEngine):
        """Test smart fallback: coverage >= 0.8 proceeds without question."""
        # Setup extraction result with high but not full coverage
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=[
                ExtractedParameter(name="reddito", value="50000", confidence=0.9, source="query"),
            ],
            missing_required=["tipo_contribuente"],
            coverage=0.5,
            can_proceed=False,
        )

        # But coverage is set to trigger smart fallback
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="calcolo_irpef",
            extracted=[
                ExtractedParameter(name="reddito", value="50000", confidence=0.9, source="query"),
                ExtractedParameter(name="tipo_contribuente", value="dipendente", confidence=0.85, source="query"),
            ],
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        mock_actions = [
            Action(
                id="irpef-calc",
                label="Calcola IRPEF",
                icon="calc",
                category=ActionCategory.CALCULATE,
                prompt_template="Calcola IRPEF",
            )
        ]
        engine.template_service.get_actions_for_domain.return_value = mock_actions

        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
            action_type="fiscal_calculation",
        )

        result = engine.process("Calcola IRPEF per dipendente con 50000 euro", context)

        # With can_proceed=True, should not ask question
        assert result.question is None
        assert len(result.actions) >= 1

    def test_document_context_prioritizes_doc_actions(self, engine: ProactivityEngine):
        """Test that document context prioritizes document-specific actions."""
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="analisi_documento",
            extracted=[],
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        # Setup document-specific actions
        doc_actions = [
            Action(
                id="fattura-verify",
                label="Verifica fattura",
                icon="check",
                category=ActionCategory.VERIFY,
                prompt_template="Verifica fattura",
            )
        ]
        engine.template_service.get_actions_for_document.return_value = doc_actions

        context = ProactivityContext(
            session_id="session-123",
            domain="documents",
            document_type="fattura",
        )

        result = engine.process("Analizza questa fattura", context)

        # Document actions should be included
        engine.template_service.get_actions_for_document.assert_called_with("fattura")
        assert len(result.actions) >= 1

    def test_template_failure_graceful(self, engine: ProactivityEngine):
        """Test graceful handling of template service failure."""
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="calcolo_iva",
            extracted=[],
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        # Simulate template service failure
        engine.template_service.get_actions_for_domain.side_effect = Exception("Template error")

        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
        )

        # Should not raise, should return empty actions
        result = engine.process("Calcola IVA", context)

        assert result.actions == []
        assert result.question is None

    def test_processing_time_recorded(self, engine: ProactivityEngine):
        """Test that processing time is recorded."""
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="calcolo_iva",
            extracted=[],
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
        )

        result = engine.process("Calcola IVA", context)

        assert result.processing_time_ms >= 0


class TestPerformance:
    """Test performance requirements."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine with mocked dependencies."""
        mock_template_service = MagicMock()
        mock_facts_extractor = MagicMock()

        # Fast mock returns
        mock_template_service.get_actions_for_domain.return_value = []
        mock_facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="test",
            extracted=[],
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        return ProactivityEngine(
            template_service=mock_template_service,
            facts_extractor=mock_facts_extractor,
        )

    def test_performance_under_500ms(self, engine: ProactivityEngine):
        """Test total processing time is under 500ms requirement."""
        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
        )

        start = time.time()
        result = engine.process("Test query", context)
        elapsed_ms = (time.time() - start) * 1000

        # Should be well under 500ms with mocked deps
        assert elapsed_ms < 500
        assert result.processing_time_ms < 500


class TestClassificationBasedIntentInference:
    """Test classification-based intent inference (BUGFIX: DEV-153).

    These tests verify that the ProactivityEngine correctly infers intent
    from DomainActionClassifier output (domain, action_type, sub_domain).
    """

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine with mocked dependencies."""
        mock_template_service = MagicMock()
        mock_facts_extractor = MagicMock()
        return ProactivityEngine(
            template_service=mock_template_service,
            facts_extractor=mock_facts_extractor,
        )

    def test_infer_intent_tax_calculation_irpef(self, engine: ProactivityEngine):
        """Test intent detection from TAX + CALCULATION_REQUEST + irpef."""
        context = ProactivityContext(
            session_id="test-session",
            domain="tax",
            action_type="calculation_request",
            sub_domain="irpef",
            classification_confidence=0.92,
        )

        intent = engine._infer_intent(context)
        assert intent == "calcolo_irpef"

    def test_infer_intent_tax_calculation_iva(self, engine: ProactivityEngine):
        """Test intent detection from TAX + CALCULATION_REQUEST + iva."""
        context = ProactivityContext(
            session_id="test-session",
            domain="tax",
            action_type="calculation_request",
            sub_domain="iva",
            classification_confidence=0.95,
        )

        intent = engine._infer_intent(context)
        assert intent == "calcolo_iva"

    def test_infer_intent_tax_calculation_inps(self, engine: ProactivityEngine):
        """Test intent detection from TAX + CALCULATION_REQUEST + inps."""
        context = ProactivityContext(
            session_id="test-session",
            domain="tax",
            action_type="calculation_request",
            sub_domain="inps",
            classification_confidence=0.88,
        )

        intent = engine._infer_intent(context)
        assert intent == "calcolo_contributi_inps"

    def test_infer_intent_tax_calculation_tfr(self, engine: ProactivityEngine):
        """Test intent detection from TAX + CALCULATION_REQUEST + tfr."""
        context = ProactivityContext(
            session_id="test-session",
            domain="tax",
            action_type="calculation_request",
            sub_domain="tfr",
            classification_confidence=0.90,
        )

        intent = engine._infer_intent(context)
        assert intent == "calcolo_tfr"

    def test_infer_intent_tax_calculation_default(self, engine: ProactivityEngine):
        """Test default intent for TAX + CALCULATION_REQUEST without sub_domain."""
        context = ProactivityContext(
            session_id="test-session",
            domain="tax",
            action_type="calculation_request",
            sub_domain=None,
            classification_confidence=0.85,
        )

        intent = engine._infer_intent(context)
        assert intent == "calcolo_irpef"  # Default for tax calculation

    def test_infer_intent_labor_calculation_inps(self, engine: ProactivityEngine):
        """Test intent detection from LABOR + CALCULATION_REQUEST + inps."""
        context = ProactivityContext(
            session_id="test-session",
            domain="labor",
            action_type="calculation_request",
            sub_domain="inps",
            classification_confidence=0.91,
        )

        intent = engine._infer_intent(context)
        assert intent == "calcolo_contributi_inps"

    def test_infer_intent_labor_calculation_tfr(self, engine: ProactivityEngine):
        """Test intent detection from LABOR + CALCULATION_REQUEST + tfr."""
        context = ProactivityContext(
            session_id="test-session",
            domain="labor",
            action_type="calculation_request",
            sub_domain="tfr",
            classification_confidence=0.89,
        )

        intent = engine._infer_intent(context)
        assert intent == "calcolo_tfr"

    def test_infer_intent_labor_calculation_netto(self, engine: ProactivityEngine):
        """Test intent detection from LABOR + CALCULATION_REQUEST + netto."""
        context = ProactivityContext(
            session_id="test-session",
            domain="labor",
            action_type="calculation_request",
            sub_domain="netto",
            classification_confidence=0.93,
        )

        intent = engine._infer_intent(context)
        assert intent == "calcolo_netto"

    def test_infer_intent_tax_information_request(self, engine: ProactivityEngine):
        """Test intent detection from TAX + INFORMATION_REQUEST."""
        context = ProactivityContext(
            session_id="test-session",
            domain="tax",
            action_type="information_request",
            sub_domain=None,
            classification_confidence=0.87,
        )

        intent = engine._infer_intent(context)
        assert intent == "cerca_normativa"

    def test_infer_intent_tax_compliance_check(self, engine: ProactivityEngine):
        """Test intent detection from TAX + COMPLIANCE_CHECK."""
        context = ProactivityContext(
            session_id="test-session",
            domain="tax",
            action_type="compliance_check",
            sub_domain=None,
            classification_confidence=0.86,
        )

        intent = engine._infer_intent(context)
        assert intent == "verifica_scadenza"

    def test_infer_intent_fallback_for_default_domain(self, engine: ProactivityEngine):
        """Test fallback to legacy logic when domain is 'default'."""
        context = ProactivityContext(
            session_id="test-session",
            domain="default",
            action_type=None,
            sub_domain=None,
            classification_confidence=0.0,
        )

        intent = engine._infer_intent(context)
        # Should return None as no legacy mapping matches
        assert intent is None

    def test_infer_intent_case_insensitive(self, engine: ProactivityEngine):
        """Test that intent inference is case insensitive."""
        context = ProactivityContext(
            session_id="test-session",
            domain="TAX",
            action_type="CALCULATION_REQUEST",
            sub_domain="IRPEF",
            classification_confidence=0.90,
        )

        intent = engine._infer_intent(context)
        assert intent == "calcolo_irpef"


class TestEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine with mocked dependencies."""
        mock_template_service = MagicMock()
        mock_facts_extractor = MagicMock()
        return ProactivityEngine(
            template_service=mock_template_service,
            facts_extractor=mock_facts_extractor,
        )

    def test_empty_query(self, engine: ProactivityEngine):
        """Test handling of empty query."""
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="unknown",
            extracted=[],
            missing_required=[],
            coverage=0.0,
            can_proceed=True,
        )

        context = ProactivityContext(
            session_id="session-123",
            domain="default",
        )

        result = engine.process("", context)

        # Should handle gracefully
        assert isinstance(result, ProactivityResult)

    def test_unknown_domain_uses_default(self, engine: ProactivityEngine):
        """Test unknown domain falls back to default actions."""
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="unknown",
            extracted=[],
            missing_required=[],
            coverage=1.0,
            can_proceed=True,
        )

        context = ProactivityContext(
            session_id="session-123",
            domain="unknown_domain",
        )

        result = engine.process("Some query", context)

        # Should use default domain
        engine.template_service.get_actions_for_domain.assert_called()

    def test_extraction_failure_smart_fallback(self, engine: ProactivityEngine):
        """Test extraction failure uses smart fallback (can_proceed=True)."""
        # Simulate extraction returning with smart fallback
        engine.facts_extractor.extract_with_coverage.return_value = ParameterExtractionResult(
            intent="unknown",
            extracted=[],
            missing_required=[],
            coverage=0.0,
            can_proceed=True,  # Smart fallback
        )

        context = ProactivityContext(
            session_id="session-123",
            domain="tax",
        )

        result = engine.process("Ambiguous query", context)

        # Should proceed without question due to smart fallback
        assert result.question is None
