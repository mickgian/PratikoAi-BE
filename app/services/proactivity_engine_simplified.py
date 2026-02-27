"""Simplified ProactivityEngine for LLM-First architecture.

DEV-177: Simplify ProactivityEngine Decision Logic

This engine implements the simplified decision flow from Section 12.7:
1. Check if calculable intent with missing params -> InteractiveQuestion
2. Check if document present -> use DOCUMENT_ACTION_TEMPLATES
3. Otherwise -> LLM generates actions (use_llm_actions=True)

Reference: PRATIKO_1.5_REFERENCE.md Section 12.7
"""

import logging
import re
from typing import Any

from pydantic import BaseModel

from app.core.proactivity_constants import (
    CALCULABLE_INTENTS,
    DOCUMENT_ACTION_TEMPLATES,
    ActionTemplate,
)

logger = logging.getLogger(__name__)


class ProactivityResult(BaseModel):
    """Result of proactivity decision logic.

    Only one of these should be set (mutual exclusivity):
    - interactive_question: For calculable intents with missing params
    - template_actions: For recognized document types
    - use_llm_actions: For everything else (LLM generates actions)
    """

    interactive_question: dict | None = None
    template_actions: list[dict] | None = None
    use_llm_actions: bool = False


# Intent detection patterns - Must contain calculation keywords
# Only match if query is asking for a CALCULATION, not just mentioning the topic
INTENT_PATTERNS: dict[str, list[str]] = {
    "calcolo_irpef": [
        r"\bcalcola(re|mi|ndo)?\s+.*\birpef\b",
        r"\bcalcola(re|mi|ndo)?\s+l['\s]irpef\b",
        r"\birpef\s+.*\bcalcola(re|mi|ndo)?\b",
        r"\bquanto\s+.*\birpef\b",
        r"\birpef\s+.*\bquanto\b",
    ],
    "calcolo_iva": [
        r"\bcalcola(re|mi|ndo)?\s+.*\biva\b",
        r"\bcalcola(re|mi|ndo)?\s+l['\s]iva\b",
        r"\biva\s+.*\bcalcola(re|mi|ndo)?\b",
        r"\bquanto\s+.*\biva\b",
        r"\biva\s+.*\bquanto\b",
    ],
    "calcolo_contributi_inps": [
        r"\bcalcola(re|mi|ndo)?\s+.*\bcontributi\b",
        r"\bcalcola(re|mi|ndo)?\s+.*\binps\b",
        r"\bcontributi\s+inps\s+.*\bcalcola(re|mi|ndo)?\b",
        r"\bquanto\s+.*\bcontributi\b",
        r"\bquanto\s+.*\binps\b",
    ],
    "ravvedimento_operoso": [
        r"\bcalcola(re|mi|ndo)?\s+.*\bravvedimento\b",
        r"\bravvedimento\s+operoso\b",
    ],
    "calcolo_f24": [
        r"\bcompila(re|mi|ndo)?\s+.*\bf24\b",
        r"\bcompila(re|mi|ndo)?\s+.*\bmodello\s+f24\b",
        r"\bf24\s+.*\bcompila(re|mi|ndo)?\b",
    ],
}

# Parameter extraction patterns
PARAM_PATTERNS: dict[str, list[str]] = {
    "reddito": [
        r"(\d+(?:[.,]\d+)?)\s*(?:euro|€)",
        r"reddito\s+(?:di\s+)?(\d+(?:[.,]\d+)?)",
        r"(\d{4,})\s*(?:euro|€)?",  # 4+ digit numbers likely to be income
    ],
    "importo": [
        r"(\d+(?:[.,]\d+)?)\s*(?:euro|€)",
        r"importo\s+(?:di\s+)?(\d+(?:[.,]\d+)?)",
        r"su\s+(\d+(?:[.,]\d+)?)",
    ],
    "tipo_contribuente": [
        r"\b(dipendente|lavoratore\s+dipendente)\b",
        r"\b(autonomo|lavoratore\s+autonomo|partita\s+iva)\b",
        r"\b(pensionato|pensione)\b",
    ],
    "tipo_gestione": [
        r"\b(artigiani?|commercianti?|gestione\s+separata)\b",
    ],
    "importo_originale": [
        r"importo\s+(?:originale\s+)?(?:di\s+)?(\d+(?:[.,]\d+)?)",
        r"(\d+(?:[.,]\d+)?)\s*(?:euro|€)\s+(?:da pagare|originale)?",
    ],
    "data_scadenza": [
        r"scaden\w+\s+(?:del?\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ],
    "codice_tributo": [
        r"codice\s+(?:tributo\s+)?(\d{4})",
        r"tributo\s+(\d{4})",
    ],
}


class ProactivityEngine:
    """Simplified ProactivityEngine for LLM-First architecture.

    This engine makes three simple decisions:
    1. If query is a calculable intent with missing params -> InteractiveQuestion
    2. If document is recognized type -> template actions
    3. Otherwise -> use LLM actions
    """

    def __init__(self) -> None:
        """Initialize engine (no external dependencies needed)."""
        # Compile regex patterns for performance
        self._intent_patterns: dict[str, list[re.Pattern[str]]] = {}
        for intent, patterns in INTENT_PATTERNS.items():
            self._intent_patterns[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]

        self._param_patterns: dict[str, list[re.Pattern[str]]] = {}
        for param, patterns in PARAM_PATTERNS.items():
            self._param_patterns[param] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def process_query(
        self,
        query: str,
        document: dict | None = None,
        session_context: dict | None = None,
    ) -> ProactivityResult:
        """Process query and determine proactive response type.

        Decision logic (Section 12.7):
        1. Check calculable intent with missing params -> InteractiveQuestion
        2. Check document type -> template actions
        3. Otherwise -> use LLM actions

        Args:
            query: User query string
            document: Optional document dict with 'type' and 'content' keys
            session_context: Optional session context dict

        Returns:
            ProactivityResult with decision outcome
        """
        # Empty query -> LLM actions
        if not query or not query.strip():
            return ProactivityResult(use_llm_actions=True)

        # STEP 1: Check calculable intent with missing params
        question = self._check_calculable_intent(query)
        if question:
            logger.debug(
                "proactivity_calculable_intent",
                extra={"query_preview": query[:50], "has_question": True},
            )
            return ProactivityResult(interactive_question=question)

        # STEP 2: Check document type
        actions = self._get_document_actions(document)
        if actions:
            logger.debug(
                "proactivity_document_actions",
                extra={"doc_type": document.get("type") if document else None},
            )
            return ProactivityResult(template_actions=actions)

        # STEP 3: Default to LLM actions
        logger.debug(
            "proactivity_llm_actions",
            extra={"query_preview": query[:50]},
        )
        return ProactivityResult(use_llm_actions=True)

    def _check_calculable_intent(self, query: str) -> dict | None:
        """Check if query is a calculable intent with missing params.

        Args:
            query: User query string

        Returns:
            InteractiveQuestion dict if missing params, None otherwise
        """
        intent = self._classify_intent(query)
        if not intent or intent not in CALCULABLE_INTENTS:
            return None

        # Extract parameters
        extracted = self._extract_parameters(query, intent)

        # Check required parameters
        required = CALCULABLE_INTENTS[intent]["required"]
        missing = [p for p in required if p not in extracted]

        if missing:
            return self._build_question_for_missing(intent, missing, extracted)

        # All params present -> no question needed
        return None

    def _get_document_actions(self, document: dict | None) -> list[dict] | None:
        """Get template actions for document type.

        Args:
            document: Document dict with 'type' key

        Returns:
            List of action dicts or None if unknown type
        """
        if not document:
            return None

        doc_type = document.get("type")
        if not doc_type or doc_type not in DOCUMENT_ACTION_TEMPLATES:
            return None

        # Convert ActionTemplate to dict
        templates: list[ActionTemplate] = DOCUMENT_ACTION_TEMPLATES[doc_type]
        return [dict(t) for t in templates]

    def _classify_intent(self, query: str) -> str | None:
        """Classify query intent using pattern matching.

        Args:
            query: User query string

        Returns:
            Intent string or None if not a calculable intent
        """
        query_lower = query.lower()

        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if pattern.search(query_lower):
                    logger.debug(
                        "intent_classified",
                        extra={"intent": intent, "query_preview": query[:50]},
                    )
                    return intent

        return None

    def _extract_parameters(self, query: str, intent: str) -> dict[str, Any]:
        """Extract parameters from query for given intent.

        Args:
            query: User query string
            intent: Detected intent

        Returns:
            Dict of extracted parameter name -> value
        """
        if intent not in CALCULABLE_INTENTS:
            return {}

        required = CALCULABLE_INTENTS[intent]["required"]
        extracted: dict[str, Any] = {}

        for param in required:
            if param not in self._param_patterns:
                continue

            for pattern in self._param_patterns[param]:
                match = pattern.search(query)
                if match:
                    # Get the captured group
                    value = match.group(1) if match.groups() else match.group(0)
                    # Normalize numeric values
                    value = value.replace(",", ".").strip()
                    extracted[param] = value
                    break

        logger.debug(
            "parameters_extracted",
            extra={
                "intent": intent,
                "extracted_count": len(extracted),
                "required_count": len(required),
            },
        )

        return extracted

    def _build_question_for_missing(
        self,
        intent: str,
        missing: list[str],
        extracted: dict[str, Any],
    ) -> dict:
        """Build InteractiveQuestion for missing parameters.

        Args:
            intent: Detected intent
            missing: List of missing parameter names
            extracted: Dict of already extracted params

        Returns:
            InteractiveQuestion dict
        """
        intent_config = CALCULABLE_INTENTS[intent]
        question_flow = intent_config["question_flow"]

        # Build question text based on intent
        question_texts = {
            "calcolo_irpef": "Per calcolare l'IRPEF, ho bisogno di alcune informazioni:",
            "calcolo_iva": "Per calcolare l'IVA, ho bisogno di alcune informazioni:",
            "calcolo_contributi_inps": "Per calcolare i contributi INPS, ho bisogno di alcune informazioni:",
            "ravvedimento_operoso": "Per calcolare il ravvedimento operoso, ho bisogno di alcune informazioni:",
            "calcolo_f24": "Per compilare il modello F24, ho bisogno di alcune informazioni:",
        }

        # Build fields for missing parameters
        field_configs = {
            "tipo_contribuente": {
                "id": "tipo_contribuente",
                "label": "Tipo di contribuente",
                "input_type": "select",
                "options": [
                    {"id": "dipendente", "label": "Lavoratore dipendente"},
                    {"id": "autonomo", "label": "Lavoratore autonomo"},
                    {"id": "pensionato", "label": "Pensionato"},
                ],
                "required": True,
            },
            "reddito": {
                "id": "reddito",
                "label": "Reddito annuo lordo",
                "placeholder": "es. 35000",
                "input_type": "currency",
                "required": True,
            },
            "importo": {
                "id": "importo",
                "label": "Importo",
                "placeholder": "es. 1000",
                "input_type": "currency",
                "required": True,
            },
            "tipo_gestione": {
                "id": "tipo_gestione",
                "label": "Tipo di gestione",
                "input_type": "select",
                "options": [
                    {"id": "artigiani", "label": "Gestione Artigiani"},
                    {"id": "commercianti", "label": "Gestione Commercianti"},
                    {"id": "separata", "label": "Gestione Separata"},
                ],
                "required": True,
            },
            "importo_originale": {
                "id": "importo_originale",
                "label": "Importo originale da pagare",
                "placeholder": "es. 5000",
                "input_type": "currency",
                "required": True,
            },
            "data_scadenza": {
                "id": "data_scadenza",
                "label": "Data di scadenza originale",
                "placeholder": "gg/mm/aaaa",
                "input_type": "date",
                "required": True,
            },
            "codice_tributo": {
                "id": "codice_tributo",
                "label": "Codice tributo",
                "placeholder": "es. 1001",
                "input_type": "text",
                "required": True,
            },
        }

        fields = [field_configs[param] for param in missing if param in field_configs]

        return {
            "id": f"{question_flow}_question",
            "text": question_texts.get(intent, "Ho bisogno di alcune informazioni:"),
            "question_type": "multi_field",
            "fields": fields,
            "prefilled_params": extracted if extracted else None,
        }
