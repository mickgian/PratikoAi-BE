"""TDD Tests for Simplified ProactivityEngine - DEV-177.

This module tests the LLM-First ProactivityEngine with simplified decision logic:
1. Check calculable intent with missing params -> InteractiveQuestion
2. Check document type -> DOCUMENT_ACTION_TEMPLATES
3. Otherwise -> use_llm_actions flag

Reference: PRATIKO_1.5_REFERENCE.md Section 12.7
"""

import pytest

from app.core.proactivity_constants import (
    CALCULABLE_INTENTS,
    DOCUMENT_ACTION_TEMPLATES,
)
from app.services.proactivity_engine_simplified import (
    ProactivityEngine,
    ProactivityResult,
)


class TestProactivityResultModel:
    """Test the new ProactivityResult model."""

    def test_result_with_interactive_question(self):
        """Test result with interactive question (calculable intent case)."""
        result = ProactivityResult(
            interactive_question={"id": "test", "text": "Test question"},
            template_actions=None,
            use_llm_actions=False,
        )
        assert result.interactive_question is not None
        assert result.template_actions is None
        assert result.use_llm_actions is False

    def test_result_with_template_actions(self):
        """Test result with template actions (document case)."""
        result = ProactivityResult(
            interactive_question=None,
            template_actions=[{"id": "verify", "label": "Verifica"}],
            use_llm_actions=False,
        )
        assert result.interactive_question is None
        assert result.template_actions is not None
        assert len(result.template_actions) == 1
        assert result.use_llm_actions is False

    def test_result_with_llm_flag(self):
        """Test result with use_llm_actions flag (default case)."""
        result = ProactivityResult(
            interactive_question=None,
            template_actions=None,
            use_llm_actions=True,
        )
        assert result.interactive_question is None
        assert result.template_actions is None
        assert result.use_llm_actions is True


class TestProactivityEngineInit:
    """Test ProactivityEngine initialization."""

    def test_engine_initialization_no_dependencies(self):
        """Test engine initializes without external dependencies."""
        engine = ProactivityEngine()
        assert engine is not None

    def test_engine_has_constants_loaded(self):
        """Test engine has CALCULABLE_INTENTS and DOCUMENT_ACTION_TEMPLATES."""
        engine = ProactivityEngine()
        # Engine should reference the constants
        assert len(CALCULABLE_INTENTS) == 5
        assert len(DOCUMENT_ACTION_TEMPLATES) == 4


class TestCalculableIntentsQuestions:
    """Test InteractiveQuestion for calculable intents with missing params."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine instance."""
        return ProactivityEngine()

    def test_process_query_calcolo_irpef_missing_params_returns_question(self, engine: ProactivityEngine):
        """Test calcolo_irpef with missing params returns InteractiveQuestion."""
        result = engine.process_query(
            query="Calcola l'IRPEF",
            document=None,
            session_context=None,
        )

        assert result.interactive_question is not None
        assert result.template_actions is None
        assert result.use_llm_actions is False

    def test_process_query_calcolo_irpef_complete_params_no_question(self, engine: ProactivityEngine):
        """Test calcolo_irpef with complete params uses LLM actions."""
        result = engine.process_query(
            query="Calcola l'IRPEF per un dipendente con reddito di 50000 euro",
            document=None,
            session_context=None,
        )

        # All required params present -> no question, use LLM
        assert result.interactive_question is None
        assert result.use_llm_actions is True

    def test_process_query_calcolo_iva_missing_params(self, engine: ProactivityEngine):
        """Test calcolo_iva with missing importo returns question."""
        result = engine.process_query(
            query="Calcola l'IVA",
            document=None,
            session_context=None,
        )

        assert result.interactive_question is not None
        assert result.use_llm_actions is False

    def test_process_query_calcolo_iva_complete_params(self, engine: ProactivityEngine):
        """Test calcolo_iva with importo uses LLM actions."""
        result = engine.process_query(
            query="Calcola l'IVA su 1000 euro",
            document=None,
            session_context=None,
        )

        assert result.interactive_question is None
        assert result.use_llm_actions is True

    def test_all_five_calculable_intents_trigger_questions(self, engine: ProactivityEngine):
        """Test all 5 calculable intents trigger questions when params missing."""
        test_queries = {
            "calcolo_irpef": "Calcola l'IRPEF",
            "calcolo_iva": "Calcola l'IVA",
            "calcolo_contributi_inps": "Calcola i contributi INPS",
            "ravvedimento_operoso": "Calcola il ravvedimento operoso",
            "calcolo_f24": "Compila il modello F24",
        }

        for intent, query in test_queries.items():
            result = engine.process_query(query=query, document=None, session_context=None)
            assert result.interactive_question is not None, (
                f"Intent {intent} should return question for incomplete query"
            )
            assert result.use_llm_actions is False

    def test_partial_parameters_asks_for_missing_only(self, engine: ProactivityEngine):
        """Test that partial params still trigger question for missing ones."""
        # calcolo_irpef requires: tipo_contribuente, reddito
        # Provide only reddito
        result = engine.process_query(
            query="Calcola l'IRPEF su 50000 euro",  # Has reddito, missing tipo_contribuente
            document=None,
            session_context=None,
        )

        assert result.interactive_question is not None
        # Question should ask for missing tipo_contribuente


class TestDocumentActionTemplates:
    """Test template actions for recognized document types."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine instance."""
        return ProactivityEngine()

    def test_process_query_fattura_returns_template_actions(self, engine: ProactivityEngine):
        """Test fattura document returns template actions."""
        mock_document = {"type": "fattura_elettronica", "content": "..."}

        result = engine.process_query(
            query="Analizza questa fattura",
            document=mock_document,
            session_context=None,
        )

        assert result.template_actions is not None
        assert len(result.template_actions) == 4  # fattura_elettronica has 4 actions
        assert result.interactive_question is None
        assert result.use_llm_actions is False

    def test_process_query_f24_returns_template_actions(self, engine: ProactivityEngine):
        """Test F24 document returns template actions."""
        mock_document = {"type": "f24", "content": "..."}

        result = engine.process_query(
            query="Verifica questo F24",
            document=mock_document,
            session_context=None,
        )

        assert result.template_actions is not None
        assert len(result.template_actions) == 3  # f24 has 3 actions
        assert result.use_llm_actions is False

    def test_process_query_bilancio_returns_template_actions(self, engine: ProactivityEngine):
        """Test bilancio document returns template actions."""
        mock_document = {"type": "bilancio", "content": "..."}

        result = engine.process_query(
            query="Analizza questo bilancio",
            document=mock_document,
            session_context=None,
        )

        assert result.template_actions is not None
        assert len(result.template_actions) == 3  # bilancio has 3 actions

    def test_process_query_cu_returns_template_actions(self, engine: ProactivityEngine):
        """Test CU document returns template actions."""
        mock_document = {"type": "cu", "content": "..."}

        result = engine.process_query(
            query="Verifica questa CU",
            document=mock_document,
            session_context=None,
        )

        assert result.template_actions is not None
        assert len(result.template_actions) == 3  # cu has 3 actions

    def test_all_four_document_types_return_templates(self, engine: ProactivityEngine):
        """Test all 4 document types return their template actions."""
        document_types = {
            "fattura_elettronica": 4,
            "f24": 3,
            "bilancio": 3,
            "cu": 3,
        }

        for doc_type, expected_actions in document_types.items():
            mock_document = {"type": doc_type, "content": "..."}
            result = engine.process_query(
                query="Analizza questo documento",
                document=mock_document,
                session_context=None,
            )

            assert result.template_actions is not None, f"Document type {doc_type} should return template actions"
            assert len(result.template_actions) == expected_actions, (
                f"Document type {doc_type} should have {expected_actions} actions"
            )

    def test_process_query_unknown_document_uses_llm(self, engine: ProactivityEngine):
        """Test unknown document type uses LLM actions."""
        mock_document = {"type": "unknown_type", "content": "..."}

        result = engine.process_query(
            query="Analizza questo documento",
            document=mock_document,
            session_context=None,
        )

        assert result.template_actions is None
        assert result.use_llm_actions is True


class TestLLMActionsFlag:
    """Test use_llm_actions flag for generic queries."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine instance."""
        return ProactivityEngine()

    def test_process_query_generic_returns_llm_flag(self, engine: ProactivityEngine):
        """Test generic query returns use_llm_actions=True."""
        result = engine.process_query(
            query="Come funziona il regime forfettario?",
            document=None,
            session_context=None,
        )

        assert result.interactive_question is None
        assert result.template_actions is None
        assert result.use_llm_actions is True

    def test_process_query_unknown_intent_uses_llm(self, engine: ProactivityEngine):
        """Test unknown intent uses LLM actions."""
        result = engine.process_query(
            query="Quali sono le novità fiscali 2024?",
            document=None,
            session_context=None,
        )

        assert result.use_llm_actions is True

    def test_process_query_information_request_uses_llm(self, engine: ProactivityEngine):
        """Test information request uses LLM actions."""
        result = engine.process_query(
            query="Spiegami la differenza tra IRPEF e IRES",
            document=None,
            session_context=None,
        )

        assert result.use_llm_actions is True


class TestEdgeCases:
    """Test edge cases for ProactivityEngine."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine instance."""
        return ProactivityEngine()

    def test_empty_query_returns_llm_flag(self, engine: ProactivityEngine):
        """Test empty query returns use_llm_actions=True."""
        result = engine.process_query(
            query="",
            document=None,
            session_context=None,
        )

        assert result.use_llm_actions is True

    def test_none_document_processes_normally(self, engine: ProactivityEngine):
        """Test None document is handled correctly."""
        result = engine.process_query(
            query="Calcola l'IVA su 1000 euro",
            document=None,
            session_context=None,
        )

        # No document, complete params -> LLM actions
        assert result.use_llm_actions is True

    def test_session_context_passed_through(self, engine: ProactivityEngine):
        """Test session context is accepted."""
        session_ctx = {"user_id": "123", "history": []}

        result = engine.process_query(
            query="Calcola l'IRPEF",
            document=None,
            session_context=session_ctx,
        )

        # Should not raise, should process normally
        assert isinstance(result, ProactivityResult)


class TestDecisionPriority:
    """Test decision priority: calculable intent > document > LLM."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine instance."""
        return ProactivityEngine()

    def test_calculable_intent_takes_priority_over_document(self, engine: ProactivityEngine):
        """Test that calculable intent with missing params takes priority."""
        # Even with a document, if it's a calculable intent with missing params,
        # InteractiveQuestion should be returned
        mock_document = {"type": "fattura_elettronica", "content": "..."}

        result = engine.process_query(
            query="Calcola l'IRPEF su questa fattura",  # Calculable intent, missing params
            document=mock_document,
            session_context=None,
        )

        # Calculable intent takes priority
        assert result.interactive_question is not None
        assert result.template_actions is None

    def test_document_takes_priority_over_llm(self, engine: ProactivityEngine):
        """Test that document actions take priority over LLM actions."""
        mock_document = {"type": "bilancio", "content": "..."}

        result = engine.process_query(
            query="Cosa ne pensi?",  # Generic query
            document=mock_document,
            session_context=None,
        )

        # Document template actions should be used
        assert result.template_actions is not None
        assert result.use_llm_actions is False


class TestPerformance:
    """Test performance requirements."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine instance."""
        return ProactivityEngine()

    def test_decision_logic_under_10ms(self, engine: ProactivityEngine):
        """Test decision logic completes in <10ms."""
        import time

        start = time.time()
        result = engine.process_query(
            query="Calcola l'IRPEF per dipendente con 50000 euro",
            document=None,
            session_context=None,
        )
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 10, f"Decision logic took {elapsed_ms}ms, should be <10ms"
        assert isinstance(result, ProactivityResult)


class TestIntentClassification:
    """Test intent classification helper."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine instance."""
        return ProactivityEngine()

    def test_classify_intent_irpef(self, engine: ProactivityEngine):
        """Test IRPEF intent classification."""
        intent = engine._classify_intent("Calcola l'IRPEF sul mio reddito")
        assert intent == "calcolo_irpef"

    def test_classify_intent_iva(self, engine: ProactivityEngine):
        """Test IVA intent classification."""
        intent = engine._classify_intent("Quanto è l'IVA?")
        assert intent == "calcolo_iva"

    def test_classify_intent_inps(self, engine: ProactivityEngine):
        """Test INPS intent classification."""
        intent = engine._classify_intent("Calcola i contributi INPS")
        assert intent == "calcolo_contributi_inps"

    def test_classify_intent_ravvedimento(self, engine: ProactivityEngine):
        """Test ravvedimento intent classification."""
        intent = engine._classify_intent("Calcola il ravvedimento operoso")
        assert intent == "ravvedimento_operoso"

    def test_classify_intent_f24(self, engine: ProactivityEngine):
        """Test F24 intent classification."""
        intent = engine._classify_intent("Compila il modello F24")
        assert intent == "calcolo_f24"

    def test_classify_intent_unknown(self, engine: ProactivityEngine):
        """Test unknown intent returns None."""
        intent = engine._classify_intent("Come stai?")
        assert intent is None


class TestParameterExtraction:
    """Test parameter extraction helper."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine instance."""
        return ProactivityEngine()

    def test_extract_reddito(self, engine: ProactivityEngine):
        """Test reddito extraction from query."""
        params = engine._extract_parameters(
            query="Calcola l'IRPEF su 50000 euro",
            intent="calcolo_irpef",
        )
        assert "reddito" in params
        assert params["reddito"] == "50000"

    def test_extract_tipo_contribuente_dipendente(self, engine: ProactivityEngine):
        """Test tipo_contribuente extraction for dipendente."""
        params = engine._extract_parameters(
            query="Calcola l'IRPEF per un lavoratore dipendente",
            intent="calcolo_irpef",
        )
        assert "tipo_contribuente" in params
        assert "dipendente" in params["tipo_contribuente"].lower()

    def test_extract_importo_for_iva(self, engine: ProactivityEngine):
        """Test importo extraction for IVA."""
        params = engine._extract_parameters(
            query="Calcola l'IVA su 1500 euro",
            intent="calcolo_iva",
        )
        assert "importo" in params
        assert params["importo"] == "1500"

    def test_extract_empty_for_incomplete_query(self, engine: ProactivityEngine):
        """Test returns empty dict for incomplete query."""
        params = engine._extract_parameters(
            query="Calcola l'IRPEF",
            intent="calcolo_irpef",
        )
        # No numeric values, no contributor type mentioned
        assert len(params) == 0 or "reddito" not in params


class TestBuildQuestion:
    """Test question building helper."""

    @pytest.fixture
    def engine(self) -> ProactivityEngine:
        """Create engine instance."""
        return ProactivityEngine()

    def test_build_question_for_irpef_missing_all(self, engine: ProactivityEngine):
        """Test building question for IRPEF with all params missing."""
        question = engine._build_question_for_missing(
            intent="calcolo_irpef",
            missing=["tipo_contribuente", "reddito"],
            extracted={},
        )

        assert question is not None
        assert question.get("id") is not None
        assert question.get("text") is not None

    def test_build_question_includes_prefilled(self, engine: ProactivityEngine):
        """Test question includes already extracted params."""
        question = engine._build_question_for_missing(
            intent="calcolo_irpef",
            missing=["tipo_contribuente"],
            extracted={"reddito": "50000"},
        )

        assert question is not None
        # Prefilled values should be included
        prefilled = question.get("prefilled_params", {})
        assert "reddito" in prefilled or question.get("prefilled_params") is not None
