"""Proactivity constants for LLM-First architecture.

DEV-174: Define CALCULABLE_INTENTS and DOCUMENT_ACTION_TEMPLATES

Reference: PRATIKO_1.5_REFERENCE.md Section 12.4 and 12.6
"""

from typing import TypedDict


class CalculableIntent(TypedDict):
    """Type definition for calculable intent structure."""

    required: list[str]
    question_flow: str


class ActionTemplate(TypedDict):
    """Type definition for document action template."""

    id: str
    label: str
    icon: str
    prompt: str


# =============================================================================
# CALCULABLE_INTENTS - Section 12.4
# =============================================================================
# These intents trigger InteractiveQuestion when required parameters are missing.
# All other intents use LLM-generated SuggestedActions.

CALCULABLE_INTENTS: dict[str, CalculableIntent] = {
    "calcolo_irpef": {
        "required": ["tipo_contribuente", "reddito"],
        "question_flow": "irpef_flow",
    },
    "calcolo_iva": {
        "required": ["importo"],
        "question_flow": "iva_flow",
    },
    "calcolo_contributi_inps": {
        "required": ["tipo_gestione", "reddito"],
        "question_flow": "contributi_flow",
    },
    "ravvedimento_operoso": {
        "required": ["importo_originale", "data_scadenza"],
        "question_flow": "ravvedimento_flow",
    },
    "calcolo_f24": {
        "required": ["codice_tributo", "importo"],
        "question_flow": "f24_flow",
    },
}


# =============================================================================
# DOCUMENT_ACTION_TEMPLATES - Section 12.6
# =============================================================================
# Template actions for recognized document types.
# These have priority over LLM-generated actions when a document is present.

DOCUMENT_ACTION_TEMPLATES: dict[str, list[ActionTemplate]] = {
    "fattura_elettronica": [
        {
            "id": "verify",
            "label": "Verifica formale",
            "icon": "✅",
            "prompt": "Verifica la correttezza formale di questa fattura elettronica",
        },
        {
            "id": "vat",
            "label": "Calcola IVA",
            "icon": "💰",
            "prompt": "Calcola l'IVA di questa fattura",
        },
        {
            "id": "entry",
            "label": "Registrazione",
            "icon": "📒",
            "prompt": "Genera la scrittura contabile per questa fattura",
        },
        {
            "id": "recipient",
            "label": "Verifica P.IVA",
            "icon": "🔍",
            "prompt": "Verifica la Partita IVA del destinatario",
        },
    ],
    "f24": [
        {
            "id": "codes",
            "label": "Verifica codici",
            "icon": "🔍",
            "prompt": "Verifica la correttezza dei codici tributo",
        },
        {
            "id": "deadline",
            "label": "Scadenza",
            "icon": "📅",
            "prompt": "Verifica la scadenza di pagamento",
        },
        {
            "id": "ravvedimento",
            "label": "Ravvedimento",
            "icon": "⚠️",
            "prompt": "Calcola ravvedimento operoso se in ritardo",
        },
    ],
    "bilancio": [
        {
            "id": "ratios",
            "label": "Indici",
            "icon": "📊",
            "prompt": "Calcola i principali indici di bilancio",
        },
        {
            "id": "compare",
            "label": "Confronta",
            "icon": "📈",
            "prompt": "Confronta con l'esercizio precedente",
        },
        {
            "id": "summary",
            "label": "Riepilogo",
            "icon": "📋",
            "prompt": "Estrai i dati principali in formato tabellare",
        },
    ],
    "cu": [
        {
            "id": "verify",
            "label": "Verifica",
            "icon": "✅",
            "prompt": "Verifica la coerenza dei dati della CU",
        },
        {
            "id": "irpef",
            "label": "Simula IRPEF",
            "icon": "💰",
            "prompt": "Simula la dichiarazione redditi da questa CU",
        },
        {
            "id": "summary",
            "label": "Riepilogo",
            "icon": "📋",
            "prompt": "Estrai riepilogo compensi e ritenute",
        },
    ],
}
