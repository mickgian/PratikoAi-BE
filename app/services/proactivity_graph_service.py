"""ProactivityGraphService for LangGraph nodes.

DEV-200: Unified proactivity logic extracted from chatbot.py for use by
Step 14 (Pre-Response Proactivity) and Step 100 (Post-Response Proactivity).

This service provides:
- check_calculable_intent: Detect if query needs parameters before RAG
- get_document_actions: Get template actions for document types
- parse_llm_actions: Extract suggested actions from LLM response
- build_proactivity_result: Build state-serializable proactivity result
"""

import logging
import re
from typing import Any

from app.core.proactivity_constants import (
    CALCULABLE_INTENTS,
    DOCUMENT_ACTION_TEMPLATES,
)
from app.services.llm_response_parser import parse_llm_response

logger = logging.getLogger(__name__)

# Intent detection patterns - Must contain calculation keywords
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
        r"(\d{4,})\s*(?:euro|€)?",
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

# Question text by intent
QUESTION_TEXTS: dict[str, str] = {
    "calcolo_irpef": "Per calcolare l'IRPEF, ho bisogno di alcune informazioni:",
    "calcolo_iva": "Per calcolare l'IVA, ho bisogno di alcune informazioni:",
    "calcolo_contributi_inps": "Per calcolare i contributi INPS, ho bisogno di alcune informazioni:",
    "ravvedimento_operoso": "Per calcolare il ravvedimento operoso, ho bisogno di alcune informazioni:",
    "calcolo_f24": "Per compilare il modello F24, ho bisogno di alcune informazioni:",
}

# Field configurations for InteractiveQuestion
FIELD_CONFIGS: dict[str, dict[str, Any]] = {
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


class ProactivityGraphService:
    """Service for proactivity logic in LangGraph nodes.

    Provides methods for:
    - Pre-response proactivity (Step 14): Check calculable intents
    - Post-response proactivity (Step 100): Get suggested actions
    """

    def __init__(self) -> None:
        """Initialize service with compiled regex patterns."""
        self._intent_patterns: dict[str, list[re.Pattern[str]]] = {}
        for intent, patterns in INTENT_PATTERNS.items():
            self._intent_patterns[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]

        self._param_patterns: dict[str, list[re.Pattern[str]]] = {}
        for param, patterns in PARAM_PATTERNS.items():
            self._param_patterns[param] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def check_calculable_intent(
        self,
        query: str,
        routing_decision: dict | None = None,
    ) -> tuple[bool, dict | None]:
        """Check if query is a calculable intent with missing parameters.

        Args:
            query: User query string
            routing_decision: Optional routing decision from Step 34a

        Returns:
            Tuple of (needs_question, interactive_question_dict)
            - (True, question_dict) if parameters are missing
            - (False, None) if no question needed
        """
        if not query or not query.strip():
            return False, None

        try:
            intent = self._classify_intent(query)
            if not intent or intent not in CALCULABLE_INTENTS:
                return False, None

            extracted = self._extract_parameters(query, intent)
            required = CALCULABLE_INTENTS[intent]["required"]
            missing = [p for p in required if p not in extracted]

            if not missing:
                logger.debug(
                    "proactivity_all_params_present",
                    extra={"intent": intent, "extracted": list(extracted.keys())},
                )
                return False, None

            question = self._build_question(intent, missing, extracted)
            logger.info(
                "proactivity_question_generated",
                extra={
                    "intent": intent,
                    "missing_params": missing,
                    "question_id": question.get("id"),
                },
            )
            return True, question

        except Exception as e:
            logger.warning(
                "proactivity_check_failed",
                extra={"error": str(e), "query_preview": query[:50]},
            )
            return False, None

    def get_document_actions(
        self,
        document_type: str | None,
    ) -> list[dict] | None:
        """Get template actions for a document type.

        Args:
            document_type: Document type string (e.g., "fattura_elettronica", "f24")

        Returns:
            List of action dicts if document type recognized, None otherwise
        """
        if not document_type:
            return None

        templates = DOCUMENT_ACTION_TEMPLATES.get(document_type)
        if not templates:
            logger.debug(
                "proactivity_unknown_document_type",
                extra={"document_type": document_type},
            )
            return None

        logger.info(
            "proactivity_document_actions",
            extra={"document_type": document_type, "action_count": len(templates)},
        )
        return [dict(t) for t in templates]

    def parse_llm_actions(
        self,
        llm_response: str,
        routing_decision: dict | None = None,
    ) -> list[dict]:
        """Parse suggested actions from LLM response.

        Args:
            llm_response: Raw LLM response string
            routing_decision: Optional routing decision for context

        Returns:
            List of action dicts parsed from response, empty list on failure
        """
        if not llm_response:
            return []

        try:
            parsed = parse_llm_response(llm_response)
            actions = [a.model_dump() for a in parsed.suggested_actions]
            logger.debug(
                "proactivity_llm_actions_parsed",
                extra={"action_count": len(actions)},
            )
            return actions
        except Exception as e:
            logger.warning(
                "proactivity_llm_parse_failed",
                extra={"error": str(e)},
            )
            return []

    def build_proactivity_result(
        self,
        pre_response: dict | None = None,
        post_response: dict | None = None,
    ) -> dict:
        """Build state-serializable proactivity result.

        Args:
            pre_response: Pre-response proactivity data (question, skip_rag)
            post_response: Post-response proactivity data (actions, source)

        Returns:
            Dict suitable for storing in RAGState.proactivity
        """
        return {
            "pre_response": pre_response or {"question": None, "skip_rag": False},
            "post_response": post_response or {"actions": [], "source": None},
        }

    def _classify_intent(self, query: str) -> str | None:
        """Classify query intent using pattern matching."""
        query_lower = query.lower()

        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if pattern.search(query_lower):
                    logger.debug(
                        "proactivity_intent_classified",
                        extra={"intent": intent, "query_preview": query[:50]},
                    )
                    return intent

        return None

    def _extract_parameters(self, query: str, intent: str) -> dict[str, Any]:
        """Extract parameters from query for given intent."""
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
                    value = match.group(1) if match.groups() else match.group(0)
                    value = value.replace(",", ".").strip()
                    extracted[param] = value
                    break

        return extracted

    def _build_question(
        self,
        intent: str,
        missing: list[str],
        extracted: dict[str, Any],
    ) -> dict:
        """Build InteractiveQuestion dict for missing parameters."""
        intent_config = CALCULABLE_INTENTS[intent]
        question_flow = intent_config["question_flow"]

        # Build fields for missing parameters
        fields = []
        for param in missing:
            if param in FIELD_CONFIGS:
                fields.append(FIELD_CONFIGS[param].copy())

        # Include extracted params as pre-filled
        prefilled = {}
        for param, value in extracted.items():
            prefilled[param] = value

        return {
            "id": f"{intent}_input_fields",
            "question_type": "multi_field",
            "text": QUESTION_TEXTS.get(intent, "Ho bisogno di alcune informazioni:"),
            "fields": fields,
            "prefilled": prefilled if prefilled else None,
            "flow_id": question_flow,
        }


# Singleton instance
_proactivity_graph_service: ProactivityGraphService | None = None


def get_proactivity_graph_service() -> ProactivityGraphService:
    """Get or create the ProactivityGraphService singleton.

    Returns:
        ProactivityGraphService instance
    """
    global _proactivity_graph_service
    if _proactivity_graph_service is None:
        _proactivity_graph_service = ProactivityGraphService()
    return _proactivity_graph_service
