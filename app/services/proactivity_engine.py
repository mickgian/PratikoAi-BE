"""ProactivityEngine Service for PratikoAI v1.5 - DEV-155.

DEPRECATED: This module is deprecated as of DEV-178.
Use app.services.proactivity_engine_simplified instead.

The simplified engine implements the LLM-First architecture from Section 12.7:
- No dependencies on ActionTemplateService or AtomicFactsExtractor
- Uses CALCULABLE_INTENTS and DOCUMENT_ACTION_TEMPLATES constants
- Three-step decision logic: calculable intent -> document -> LLM

This legacy engine remains for backwards compatibility but should not be used
for new integrations.

Original description:
This service orchestrates all proactive features:
- Parameter extraction and coverage calculation
- Action selection based on domain and context
- Interactive question generation for incomplete queries
- Smart fallback for near-complete queries

Performance Requirements:
- Full proactivity check: <500ms
- Action selection: <50ms
- Question generation: <100ms
- Coverage check: <10ms
"""

import logging
import time
from typing import TYPE_CHECKING, Any

from app.schemas.proactivity import (
    Action,
    InputField,
    InteractiveOption,
    InteractiveQuestion,
    ParameterExtractionResult,
    ProactivityContext,
    ProactivityResult,
)

if TYPE_CHECKING:
    # DEPRECATED: These services have been archived to archived/phase5_templates/
    # Kept for type hints only, actual imports will fail
    ActionTemplateService = Any
    AtomicFactsExtractor = Any

logger = logging.getLogger(__name__)

# Classification (domain, action, sub_domain) to intent mapping
# Maps DomainActionClassifier output to proactivity intent
CLASSIFICATION_TO_INTENT: dict[tuple[str, str, str | None], str] = {
    # TAX + CALCULATION_REQUEST
    ("tax", "calculation_request", "irpef"): "calcolo_irpef",
    ("tax", "calculation_request", "iva"): "calcolo_iva",
    ("tax", "calculation_request", "inps"): "calcolo_contributi_inps",
    ("tax", "calculation_request", "tfr"): "calcolo_tfr",
    ("tax", "calculation_request", None): "calcolo_irpef",  # default for tax calc
    # LABOR + CALCULATION_REQUEST
    ("labor", "calculation_request", "inps"): "calcolo_contributi_inps",
    ("labor", "calculation_request", "tfr"): "calcolo_tfr",
    ("labor", "calculation_request", "netto"): "calcolo_netto",
    ("labor", "calculation_request", None): "calcolo_contributi_inps",
    # TAX + INFORMATION_REQUEST
    ("tax", "information_request", None): "cerca_normativa",
    # TAX + COMPLIANCE_CHECK
    ("tax", "compliance_check", None): "verifica_scadenza",
    # Additional mappings for common misclassifications
    # LEGAL domain (often misclassified tax queries)
    ("legal", "compliance_check", None): "cerca_normativa",  # tax questions misclassified as legal
    ("legal", "information_request", None): "cerca_normativa",
    ("legal", "calculation_request", None): "cerca_normativa",
    # TAX + other actions
    ("tax", "document_generation", None): "verifica_scadenza",  # deadline questions
    ("tax", "general_assistance", None): "cerca_normativa",
    # DEFAULT domain fallbacks
    ("default", "calculation_request", None): "cerca_normativa",
    ("default", "information_request", None): "cerca_normativa",
    ("default", "compliance_check", None): "verifica_scadenza",
}

# Mapping from classifier action types to template action types
# The classifier returns actions like "information_request", but templates use "general_search"
CLASSIFIER_ACTION_TO_TEMPLATE_ACTION: dict[str, str] = {
    "information_request": "general_search",
    "calculation_request": "fiscal_calculation",
    "compliance_check": "general_verify",
    "document_generation": "general_export",
    "procedural_guidance": "general_explain",
    "general_assistance": "general_explain",
    # Legacy/direct mappings
    "cerca_normativa": "general_search",
    "verifica_scadenza": "general_verify",
    "calcolo_fiscale": "fiscal_calculation",
}

# LLM fallback confidence threshold
CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.6

# Intent to question mapping for generating questions
INTENT_QUESTION_MAP: dict[str, dict[str, str]] = {
    "calcolo_irpef": {
        "tipo_contribuente": "irpef_tipo_contribuente",
        "reddito": "irpef_reddito",
    },
    "calcolo_iva": {
        "importo": "iva_importo",
        "aliquota": "iva_aliquota",
    },
    "calcolo_contributi_inps": {
        "tipo_contribuente": "inps_tipo_contribuente",
        "importo": "inps_importo",
    },
}

# Intent to multi-field question mapping (Claude Code style)
# These questions collect all required parameters at once
INTENT_MULTIFIELD_QUESTIONS: dict[str, dict] = {
    "calcolo_irpef": {
        "id": "irpef_input_fields",
        "text": "Per calcolare l'IRPEF, inserisci i dati:",
        "fields": [
            {
                "id": "reddito",
                "label": "Reddito complessivo",
                "placeholder": "es. 45000",
                "input_type": "currency",
                "required": True,
            },
            {
                "id": "deduzioni",
                "label": "Deduzioni",
                "placeholder": "es. 5000 (opzionale)",
                "input_type": "currency",
                "required": False,
            },
            {
                "id": "detrazioni",
                "label": "Detrazioni",
                "placeholder": "es. 1200 (opzionale)",
                "input_type": "currency",
                "required": False,
            },
        ],
    },
    "calcolo_iva": {
        "id": "iva_input_fields",
        "text": "Per calcolare l'IVA, inserisci i dati:",
        "fields": [
            {
                "id": "importo",
                "label": "Importo imponibile",
                "placeholder": "es. 1000",
                "input_type": "currency",
                "required": True,
            },
            {
                "id": "aliquota",
                "label": "Aliquota IVA (%)",
                "placeholder": "es. 22",
                "input_type": "number",
                "required": True,
            },
        ],
    },
    "calcolo_contributi_inps": {
        "id": "inps_input_fields",
        "text": "Per calcolare i contributi INPS, inserisci i dati:",
        "fields": [
            {
                "id": "reddito",
                "label": "Reddito imponibile",
                "placeholder": "es. 30000",
                "input_type": "currency",
                "required": True,
            },
            {
                "id": "aliquota",
                "label": "Aliquota contributiva (%)",
                "placeholder": "es. 25.72",
                "input_type": "number",
                "required": False,
            },
        ],
    },
    "calcolo_tfr": {
        "id": "tfr_input_fields",
        "text": "Per calcolare il TFR, inserisci i dati:",
        "fields": [
            {
                "id": "retribuzione",
                "label": "Retribuzione annua lorda",
                "placeholder": "es. 35000",
                "input_type": "currency",
                "required": True,
            },
            {
                "id": "anni_servizio",
                "label": "Anni di servizio",
                "placeholder": "es. 5",
                "input_type": "number",
                "required": True,
            },
        ],
    },
    # Generic tax query - when user asks vague questions like "quanto devo pagare di tasse?"
    # Uses single_choice with specific tax categories (better UX than open text)
    "cerca_normativa": {
        "id": "tax_type_selection",
        "text": "Per fornirti informazioni precise, di quale tipo di imposta hai bisogno?",
        "question_type": "single_choice",
        "options": [
            {"id": "irpef", "label": "IRPEF (imposta sul reddito)"},
            {"id": "iva", "label": "IVA (imposta sul valore aggiunto)"},
            {"id": "contributi", "label": "Contributi INPS"},
            {"id": "imu_tari", "label": "IMU / TARI (imposte locali)"},
            {"id": "altro", "label": "Altro (specificare)"},
        ],
        "allow_custom_input": True,
        "custom_input_placeholder": "Descrivi la tua situazione fiscale...",
    },
    # Compliance/deadline checks
    "verifica_scadenza": {
        "id": "deadline_type_selection",
        "text": "Quale scadenza o adempimento ti interessa verificare?",
        "question_type": "single_choice",
        "options": [
            {"id": "f24", "label": "Pagamento F24"},
            {"id": "dichiarazione_redditi", "label": "Dichiarazione dei redditi"},
            {"id": "dichiarazione_iva", "label": "Dichiarazione IVA"},
            {"id": "inps", "label": "Contributi INPS"},
            {"id": "altro", "label": "Altro adempimento"},
        ],
        "allow_custom_input": True,
        "custom_input_placeholder": "Specifica l'adempimento...",
    },
}

# Fallback question for unknown/generic intents
# Uses single_choice with categories (better UX than open text field)
FALLBACK_CHOICE_QUESTION: dict = {
    "id": "topic_clarification",
    "text": "Per poterti aiutare al meglio, la tua domanda riguarda:",
    "question_type": "single_choice",
    "options": [
        {"id": "calcolo_tasse", "label": "Calcolo di imposte o contributi"},
        {"id": "scadenze", "label": "Scadenze e adempimenti fiscali"},
        {"id": "normativa", "label": "Normativa e regolamenti"},
        {"id": "situazione_specifica", "label": "Una situazione specifica"},
    ],
    "allow_custom_input": True,
    "custom_input_placeholder": "Descrivi brevemente la tua richiesta...",
}

# Keep old name for backwards compatibility
FALLBACK_MULTIFIELD_QUESTION = FALLBACK_CHOICE_QUESTION


class ProactivityEngine:
    """Orchestrates proactive features for PratikoAI.

    This engine coordinates parameter extraction, action selection,
    and interactive question generation to provide proactive assistance.

    Attributes:
        template_service: Service for loading action and question templates
        facts_extractor: Service for extracting parameters from queries
    """

    def __init__(
        self,
        template_service: "ActionTemplateService",
        facts_extractor: "AtomicFactsExtractor",
    ):
        """Initialize the engine with dependencies.

        Args:
            template_service: Service for template loading
            facts_extractor: Service for parameter extraction
        """
        self.template_service = template_service
        self.facts_extractor = facts_extractor

    def process(
        self,
        query: str,
        context: ProactivityContext,
    ) -> ProactivityResult:
        """Process a query and return proactive suggestions.

        Main orchestration method that:
        1. Extracts parameters from query
        2. Determines if question needed
        3. Selects appropriate actions
        4. Returns result with metrics

        Args:
            query: User query to process
            context: Proactivity context with session info

        Returns:
            ProactivityResult with actions, question, and metrics
        """
        start_time = time.time()

        # Default result
        actions: list[Action] = []
        question: InteractiveQuestion | None = None
        extraction_result: ParameterExtractionResult | None = None

        try:
            # Step 1: Extract parameters and calculate coverage
            extraction_result = self._extract_parameters(query, context)

            # Step 2: Determine if we should ask a question
            should_ask = self.should_ask_question(extraction_result)
            logger.debug(
                "proactivity_should_ask_decision",
                extra={
                    "should_ask": should_ask,
                    "coverage": extraction_result.coverage,
                    "can_proceed": extraction_result.can_proceed,
                    "intent": extraction_result.intent,
                },
            )
            if should_ask:
                # Generate question for missing params
                prefilled = {p.name: p.value for p in extraction_result.extracted}
                question = self.generate_question(
                    intent=extraction_result.intent,
                    missing_params=extraction_result.missing_required,
                    prefilled=prefilled,
                )
                logger.debug(
                    "proactivity_question_generated",
                    extra={
                        "question_generated": question is not None,
                        "intent": extraction_result.intent,
                        "missing_params": extraction_result.missing_required,
                    },
                )

            # Step 3: Select actions (even if asking question)
            actions = self._select_actions_for_context(context)

        except Exception as e:
            logger.warning(
                "proactivity_processing_error",
                extra={
                    "session_id": context.session_id,
                    "domain": context.domain,
                    "error": str(e),
                },
            )
            # Smart fallback - continue with empty actions

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        if processing_time_ms > 500:
            logger.warning(
                "proactivity_slow_processing",
                extra={
                    "session_id": context.session_id,
                    "processing_time_ms": processing_time_ms,
                },
            )

        logger.debug(
            "proactivity_processing_complete",
            extra={
                "session_id": context.session_id,
                "domain": context.domain,
                "action_count": len(actions),
                "has_question": question is not None,
                "coverage": extraction_result.coverage if extraction_result else 0.0,
                "processing_time_ms": processing_time_ms,
            },
        )

        return ProactivityResult(
            actions=actions,
            question=question,
            extraction_result=extraction_result,
            processing_time_ms=processing_time_ms,
        )

    def select_actions(
        self,
        domain: str,
        action_type: str | None = None,
        document_type: str | None = None,
    ) -> list[Action]:
        """Select actions based on domain and context.

        Args:
            domain: Domain classification
            action_type: Optional action type filter
            document_type: Optional document type for document-specific actions

        Returns:
            List of selected actions
        """
        actions: list[Action] = []

        try:
            # Prioritize document-specific actions
            if document_type:
                doc_actions = self.template_service.get_actions_for_document(document_type)
                actions.extend(doc_actions)

            # Add domain-specific actions
            if action_type:
                domain_actions = self.template_service.get_actions_for_domain(domain, action_type)
                actions.extend(domain_actions)
            elif not document_type:
                # Fall back to general domain actions
                domain_actions = self.template_service.get_actions_for_domain(domain, "general_search")
                actions.extend(domain_actions)

        except Exception as e:
            logger.warning(
                "action_selection_error",
                extra={
                    "domain": domain,
                    "action_type": action_type,
                    "document_type": document_type,
                    "error": str(e),
                },
            )

        return actions

    def should_ask_question(
        self,
        extraction_result: ParameterExtractionResult,
        query: str = "",
    ) -> bool:
        """Determine if an interactive question should be asked.

        PRE-RESPONSE questions should ONLY be shown for:
        1. Calculation intents missing required numeric parameters
        2. Truly vague queries with no specific topic

        NOT for:
        - Specific information requests (e.g., "Come funziona il regime forfettario?")
        - Questions about specific topics even without numeric parameters

        Args:
            extraction_result: Result of parameter extraction
            query: Original user query for specificity check

        Returns:
            True if question should be asked
        """
        # Smart fallback: if can_proceed is True, don't ask question
        if extraction_result.can_proceed:
            return False

        intent = extraction_result.intent or "unknown"

        # CALCULATION intents: Ask question if missing required numeric parameters
        calculation_intents = {
            "calcolo_irpef",
            "calcolo_iva",
            "calcolo_contributi_inps",
            "calcolo_tfr",
            "calcolo_netto",
            "calcolo_ravvedimento",
        }
        if intent in calculation_intents:
            # For calculations, ask if coverage is low and there are missing params
            should_ask = extraction_result.coverage < 0.8 and bool(extraction_result.missing_required)
            logger.debug(
                "should_ask_question_calculation",
                extra={
                    "intent": intent,
                    "coverage": extraction_result.coverage,
                    "missing": extraction_result.missing_required,
                    "should_ask": should_ask,
                },
            )
            return should_ask

        # INFORMATION/SEARCH intents: Only ask if query is truly vague
        # "Come funziona il regime forfettario?" is specific → go to LLM
        # "Quanto pago di tasse?" is vague → ask clarifying question
        information_intents = {"cerca_normativa", "verifica_scadenza", "unknown"}
        if intent in information_intents:
            # Check if query mentions a specific topic or document reference
            specific_terms = {
                # Tax regimes
                "regime forfettario",
                "forfettario",
                "regime ordinario",
                # Tax types
                "irpef",
                "iva",
                "inps",
                "imu",
                "tari",
                "irap",
                "tfr",
                "contributi",
                "fattura",
                "f24",
                "bilancio",
                # Business entities
                "ccnl",
                "contratto",
                "assunzione",
                "licenziamento",
                "partita iva",
                "srl",
                "srls",
                "spa",
                "ditta individuale",
                # Deductions and credits
                "detrazioni",
                "deduzioni",
                "bonus",
                "credito",
                # Declarations
                "scadenza",
                "dichiarazione",
                "modello",
                "unico",
                # Document types (specific document references should go to RAG)
                "risoluzione",
                "circolare",
                "decreto",
                "legge",
                "provvedimento",
                "interpello",
                "sentenza",
                "ordinanza",
                # Authorities
                "agenzia entrate",
                "agenzia delle entrate",
                "inail",
                "ministero",
                "cassazione",
                "corte",
                "tribunale",
            }
            query_lower = query.lower()
            has_specific_topic = any(term in query_lower for term in specific_terms)

            if has_specific_topic:
                # Query mentions a specific topic → go directly to LLM
                logger.debug(
                    "should_ask_question_specific_topic",
                    extra={
                        "intent": intent,
                        "query_preview": query[:50],
                        "has_specific_topic": True,
                        "should_ask": False,
                    },
                )
                return False

            # Query is vague (no specific topic) → ask clarifying question
            # But only if it's short and generic
            is_vague = len(query) < 50 and not has_specific_topic
            logger.debug(
                "should_ask_question_vague_check",
                extra={
                    "intent": intent,
                    "query_preview": query[:50],
                    "query_len": len(query),
                    "is_vague": is_vague,
                },
            )
            return is_vague

        # Default: don't ask pre-response questions for other intents
        return False

    def generate_question(
        self,
        intent: str,
        missing_params: list[str],
        prefilled: dict[str, str],
    ) -> InteractiveQuestion | None:
        """Generate an interactive question for missing parameters.

        Prefers multi-field questions (Claude Code style) when multiple
        parameters are missing, falls back to single-param questions.

        Args:
            intent: Detected intent
            missing_params: List of missing required parameter names
            prefilled: Dict of already extracted parameters

        Returns:
            InteractiveQuestion or None if no suitable question found
        """
        # For unknown intents, always try to generate a fallback question
        # even if missing_params is empty
        if not missing_params and intent != "unknown":
            return None

        # Try multi-field question first (better UX when multiple params missing)
        multifield_question = self._generate_multifield_question(intent, prefilled)
        if multifield_question:
            logger.debug(
                "multifield_question_generated",
                extra={
                    "intent": intent,
                    "question_id": multifield_question.id,
                    "field_count": len(multifield_question.fields),
                },
            )
            return multifield_question

        # Fallback to single-param question (legacy behavior)
        first_missing = missing_params[0]
        question_id = self._get_question_id_for_param(intent, first_missing)

        if not question_id:
            logger.debug(
                "no_question_template_for_param",
                extra={
                    "intent": intent,
                    "missing_param": first_missing,
                },
            )
            return None

        try:
            question = self.template_service.get_question(question_id)

            if question and prefilled:
                # Update question with prefilled params
                question = question.model_copy(update={"prefilled_params": prefilled})

            return question

        except Exception as e:
            logger.warning(
                "question_generation_error",
                extra={
                    "intent": intent,
                    "question_id": question_id,
                    "error": str(e),
                },
            )
            return None

    def _generate_multifield_question(
        self,
        intent: str,
        prefilled: dict[str, str],
        use_fallback: bool = True,
    ) -> InteractiveQuestion | None:
        """Generate a multi-field question for an intent.

        Creates a Claude Code style multi-field question that collects
        all required parameters at once.

        Args:
            intent: Detected intent (e.g., 'calcolo_irpef')
            prefilled: Dict of already extracted parameters
            use_fallback: Whether to use fallback question for unknown intents

        Returns:
            InteractiveQuestion with fields or None if not supported
        """
        if intent in INTENT_MULTIFIELD_QUESTIONS:
            config = INTENT_MULTIFIELD_QUESTIONS[intent]
        elif use_fallback:
            config = FALLBACK_MULTIFIELD_QUESTION
            logger.debug(
                "using_fallback_question",
                extra={"intent": intent},
            )
        else:
            return None

        # Determine question type from config (default to multi_field for backwards compat)
        question_type = config.get("question_type", "multi_field")

        # Build options for single_choice questions
        options = []
        if "options" in config:
            options = [
                InteractiveOption(
                    id=opt["id"],
                    label=opt["label"],
                    icon=opt.get("icon"),
                )
                for opt in config["options"]
            ]

        # Build InputField objects for multi_field questions
        fields = []
        if "fields" in config:
            fields = [
                InputField(
                    id=f["id"],
                    label=f["label"],
                    placeholder=f.get("placeholder"),
                    input_type=f.get("input_type", "text"),
                    required=f.get("required", True),
                    validation=f.get("validation"),
                )
                for f in config["fields"]
            ]

        # Create question with appropriate type
        return InteractiveQuestion(
            id=config["id"],
            text=config["text"],
            question_type=question_type,
            options=options,
            fields=fields,
            allow_custom_input=config.get("allow_custom_input", False),
            custom_input_placeholder=config.get("custom_input_placeholder"),
            prefilled_params=prefilled if prefilled else None,
        )

    def _extract_parameters(
        self,
        query: str,
        context: ProactivityContext,
    ) -> ParameterExtractionResult:
        """Extract parameters from query.

        Args:
            query: User query
            context: Proactivity context

        Returns:
            ParameterExtractionResult with coverage info
        """
        # Determine intent from domain/action_type
        intent = self._infer_intent(context)

        return self.facts_extractor.extract_with_coverage(query, intent)

    def _select_actions_for_context(
        self,
        context: ProactivityContext,
    ) -> list[Action]:
        """Select actions based on context.

        Maps classifier action types to template action types before lookup.

        Args:
            context: Proactivity context

        Returns:
            List of selected actions
        """
        # Map classifier action type to template action type
        action_type = context.action_type
        if action_type:
            action_type = CLASSIFIER_ACTION_TO_TEMPLATE_ACTION.get(action_type, action_type)
            logger.debug(
                "action_type_mapped",
                extra={
                    "original": context.action_type,
                    "mapped": action_type,
                    "domain": context.domain,
                },
            )

        return self.select_actions(
            domain=context.domain,
            action_type=action_type,
            document_type=context.document_type,
        )

    def _infer_intent(self, context: ProactivityContext) -> str | None:
        """Infer proactivity intent from classification context.

        Uses CLASSIFICATION_TO_INTENT mapping from DomainActionClassifier output,
        with fallback to legacy action_type mapping for backwards compatibility.

        Args:
            context: Proactivity context with domain, action_type, sub_domain

        Returns:
            Inferred intent string or None
        """
        # Use classification-based mapping if available (from DomainActionClassifier)
        if context.domain and context.domain != "default":
            domain = context.domain.lower()
            action = (context.action_type or "").lower()
            sub_domain = context.sub_domain.lower() if context.sub_domain else None

            # Try exact match with sub_domain
            key = (domain, action, sub_domain)
            if intent := CLASSIFICATION_TO_INTENT.get(key):
                logger.debug(
                    "intent_from_classification",
                    extra={
                        "domain": domain,
                        "action": action,
                        "sub_domain": sub_domain,
                        "intent": intent,
                    },
                )
                return intent

            # Try without sub_domain
            key_no_sub = (domain, action, None)
            if intent := CLASSIFICATION_TO_INTENT.get(key_no_sub):
                logger.debug(
                    "intent_from_classification_no_subdomain",
                    extra={
                        "domain": domain,
                        "action": action,
                        "intent": intent,
                    },
                )
                return intent

        # Legacy fallback for backwards compatibility
        return self._legacy_infer_intent(context)

    def _legacy_infer_intent(self, context: ProactivityContext) -> str | None:
        """Legacy intent inference for backwards compatibility.

        Args:
            context: Proactivity context

        Returns:
            Inferred intent string or None
        """
        # Map legacy action_type to intent
        if context.action_type:
            intent_map = {
                "fiscal_calculation": "calcolo_irpef",
                "iva_calculation": "calcolo_iva",
                "inps_calculation": "calcolo_contributi_inps",
                "tfr_calculation": "calcolo_tfr",
                "net_salary": "calcolo_netto",
            }
            return intent_map.get(context.action_type)

        # Default intent based on domain
        domain_intent_map = {
            "tax": "calcolo_irpef",
            "labor": "calcolo_contributi_inps",
        }
        return domain_intent_map.get(context.domain)

    def _get_question_id_for_param(
        self,
        intent: str,
        param_name: str,
    ) -> str | None:
        """Get question ID for a missing parameter.

        Args:
            intent: Intent name
            param_name: Parameter name

        Returns:
            Question ID or None
        """
        if intent in INTENT_QUESTION_MAP:
            return INTENT_QUESTION_MAP[intent].get(param_name)
        return None
