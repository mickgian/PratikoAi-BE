"""ProactivityEngine Service for PratikoAI v1.5 - DEV-155.

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
from typing import TYPE_CHECKING

from app.schemas.proactivity import (
    Action,
    InteractiveQuestion,
    ParameterExtractionResult,
    ProactivityContext,
    ProactivityResult,
)

if TYPE_CHECKING:
    from app.services.action_template_service import ActionTemplateService
    from app.services.atomic_facts_extractor import AtomicFactsExtractor

logger = logging.getLogger(__name__)

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
            if self.should_ask_question(extraction_result):
                # Generate question for missing params
                prefilled = {
                    p.name: p.value for p in extraction_result.extracted
                }
                question = self.generate_question(
                    intent=extraction_result.intent,
                    missing_params=extraction_result.missing_required,
                    prefilled=prefilled,
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
                domain_actions = self.template_service.get_actions_for_domain(
                    domain, action_type
                )
                actions.extend(domain_actions)
            elif not document_type:
                # Fall back to general domain actions
                domain_actions = self.template_service.get_actions_for_domain(
                    domain, "general_search"
                )
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
    ) -> bool:
        """Determine if an interactive question should be asked.

        Returns True if:
        - Coverage is below threshold (< 0.8)
        - can_proceed is False
        - There are missing required parameters

        Args:
            extraction_result: Result of parameter extraction

        Returns:
            True if question should be asked
        """
        # Smart fallback: if can_proceed is True, don't ask question
        if extraction_result.can_proceed:
            return False

        # Ask question if coverage is low and there are missing params
        return extraction_result.coverage < 0.8 and bool(extraction_result.missing_required)

    def generate_question(
        self,
        intent: str,
        missing_params: list[str],
        prefilled: dict[str, str],
    ) -> InteractiveQuestion | None:
        """Generate an interactive question for missing parameters.

        Args:
            intent: Detected intent
            missing_params: List of missing required parameter names
            prefilled: Dict of already extracted parameters

        Returns:
            InteractiveQuestion or None if no suitable question found
        """
        if not missing_params:
            return None

        # Get the first missing param to ask about
        first_missing = missing_params[0]

        # Map to question ID
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
                question = question.model_copy(
                    update={"prefilled_params": prefilled}
                )

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

        Args:
            context: Proactivity context

        Returns:
            List of selected actions
        """
        return self.select_actions(
            domain=context.domain,
            action_type=context.action_type,
            document_type=context.document_type,
        )

    def _infer_intent(self, context: ProactivityContext) -> str | None:
        """Infer intent from context.

        Args:
            context: Proactivity context

        Returns:
            Inferred intent string or None
        """
        # Map domain/action_type to intent
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
