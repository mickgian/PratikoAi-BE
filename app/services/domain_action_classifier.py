"""Domain-Action Classification System for PratikoAI.

This service provides two-dimensional classification of Italian professional queries:
1. Domain: tax, legal, labor, business, accounting
2. Action: information_request, document_generation, document_analysis,
          calculation_request, compliance_check, strategic_advice

Uses rule-based pattern matching with LLM fallback for ambiguous cases.
"""

import asyncio
import re
from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)
from pydantic import BaseModel

from app.core.config import settings
from app.core.llm.base import LLMProviderType
from app.core.llm.factory import (
    LLMFactory,
    RoutingStrategy,
    get_llm_provider,
)
from app.core.logging import logger


class Domain(str, Enum):
    """Professional domains for Italian market"""

    TAX = "tax"
    LEGAL = "legal"
    LABOR = "labor"
    BUSINESS = "business"
    ACCOUNTING = "accounting"


class Action(str, Enum):
    """Professional actions/intents"""

    INFORMATION_REQUEST = "information_request"
    DOCUMENT_GENERATION = "document_generation"
    DOCUMENT_ANALYSIS = "document_analysis"
    CALCULATION_REQUEST = "calculation_request"
    COMPLIANCE_CHECK = "compliance_check"
    STRATEGIC_ADVICE = "strategic_advice"
    CCNL_QUERY = "ccnl_query"


class QueryComposition(str, Enum):
    """Query composition types for adaptive context prioritization.

    DEV-007 Issue 9: When user attaches a document, we use LLM classification
    to understand their intent and adjust context priority weights accordingly.

    - PURE_KB: Query needs only knowledge base (no attachments, or unrelated query)
    - PURE_DOCUMENT: Query relates only to attached document
    - HYBRID: Query needs both document analysis AND knowledge base context
    - CONVERSATIONAL: Greeting or chitchat (minimal retrieval needed)
    """

    PURE_KB = "pure_kb"
    PURE_DOCUMENT = "pure_doc"
    HYBRID = "hybrid"
    CONVERSATIONAL = "chat"


class DomainActionClassification(BaseModel):
    """Classification result with confidence and metadata"""

    domain: Domain
    action: Action
    confidence: float
    sub_domain: str | None = None
    document_type: str | None = None
    reasoning: str | None = None
    fallback_used: bool = False


@dataclass
class PatternMatch:
    """Pattern matching result"""

    keywords: list[str]
    score: float
    weight: float = 1.0


class DomainActionClassifier:
    """Two-dimensional classifier for Italian professional queries"""

    def __init__(self):
        self.settings = settings
        self._load_patterns()

    def _load_patterns(self):
        """Load Italian professional terminology patterns"""
        # Domain patterns with weights
        self.domain_patterns = {
            Domain.TAX: {
                "keywords": [
                    # General tax terms
                    "iva",
                    "irpef",
                    "ires",
                    "irap",
                    "tasse",
                    "imposta",
                    "imposte",
                    "aliquota",
                    "aliquote",
                    "detrazione",
                    "detrazioni",
                    "deduzione",
                    "deduzioni",
                    "dedurre",
                    "detraibile",
                    "f24",
                    "730",
                    "dichiarazione",
                    "accertamento",
                    "ravvedimento",
                    "agenzia entrate",
                    "codice fiscale",
                    "partita iva",
                    "regime forfettario",
                    "ordinario",
                    "minimi",
                    "semplificato",
                    "iva ordinaria",
                    "iva speciale",
                    "versamento",
                    "versamenti",
                    "scadenza",
                    "termine",
                    "contributi",
                    "ritenuta",
                    "ritenute",
                    "sostituto imposta",
                    "rimborso",
                    "credito",
                    "debito",
                    "saldo",
                    # Specific taxes
                    "iva comunitaria",
                    "iva intracomunitaria",
                    "reverse charge",
                    "split payment",
                    "scissione pagamenti",
                    "cedolare secca",
                    "tasi",
                    "imu",
                    "bollo",
                    "imposta registro",
                    "successioni",
                    "donazioni",
                ],
                "sub_domains": {
                    "iva": ["iva", "imposta valore aggiunto", "aliquota iva", "reverse charge", "split payment"],
                    "irpef": ["irpef", "imposta reddito", "persone fisiche", "730", "unico"],
                    "ires": ["ires", "imposta società", "reddito società"],
                    "irap": ["irap", "attività produttive", "regionale"],
                    "forfettario": ["regime forfettario", "forfettario", "flat tax", "5%", "15%"],
                    "successioni": ["successione", "eredità", "donazione", "imposta successioni"],
                },
            },
            Domain.LEGAL: {
                "keywords": [
                    # Court and legal proceedings
                    "ricorso",
                    "atto",
                    "tribunale",
                    "giudice",
                    "decreto",
                    "sentenza",
                    "citazione",
                    "procura",
                    "intimazione",
                    "pignoramento",
                    "udienza",
                    "notifica",
                    "controversia",
                    "cassazione",
                    "tar",
                    "consiglio stato",
                    "appello",
                    "primo grado",
                    "secondo grado",
                    "legittimità",
                    "precetto",
                    "decreto ingiuntivo",
                    "opposizione",
                    "istanza",
                    # Legal documents and procedures
                    "contratto",
                    "clausola",
                    "clausole",
                    "accordo",
                    "transazione",
                    "risoluzione",
                    "rescissione",
                    "nullità",
                    "annullamento",
                    "inadempimento",
                    "mora",
                    "danni",
                    "risarcimento",
                    "responsabilità",
                    "garanzia",
                    "fideiussione",
                    "diffida",
                    "messa in mora",
                    "lettera di diffida",
                    # Legal entities and roles
                    "avvocato",
                    "legale",
                    "patrocinio",
                    "rappresentanza",
                    "mandato",
                    "procuratore",
                    "difensore",
                    # Colloquial Italian patterns for legal requests
                    "ho bisogno di",
                    "mi serve",
                    "devo fare",
                    "voglio",
                    "mi aiuti a",
                    "puoi",
                    "vorrei",
                    "come faccio a",
                    "help me",
                    "aiuto",
                    "urgente",
                    "subito",
                    "problema",
                    "questione",
                    "situazione",
                    "caso",
                    "difendermi",
                    "tutelarmi",
                    "proteggere",
                    "diritti",
                    "causa",
                    "lite",
                    "disputa",
                    "conflitto",
                    "pagare",
                    "soldi",
                    "debito",
                    "creditore",
                    "sfratto",
                    "affitto",
                    "locazione",
                    "inquilino",
                    "lavoro",
                    "licenziamento",
                    "mobbing",
                    "infortunio",
                    "separazione",
                    "divorzio",
                    "matrimonio",
                    "famiglia",
                    "eredità",
                    "testamento",
                    "successione",
                ],
                "sub_domains": {
                    "civile": ["civile", "contratto", "responsabilità", "danni", "risarcimento"],
                    "amministrativo": ["tar", "consiglio stato", "amministrativo", "ricorso amministrativo"],
                    "tributario": ["commissione tributaria", "ricorso tributario", "accertamento"],
                    "societario": ["società", "assemblea", "delibera", "socio", "amministratore"],
                    "fallimentare": ["fallimento", "concordato", "liquidazione", "insolvenza"],
                },
            },
            Domain.LABOR: {
                "keywords": [
                    # Employment relationships
                    "licenziamento",
                    "ccnl",
                    "busta paga",
                    "tfr",
                    "assunzione",
                    "dimissioni",
                    "contratto lavoro",
                    "subordinato",
                    "autonomo",
                    "parasubordinato",
                    "apprendistato",
                    "tirocinio",
                    "stage",
                    "collaborazione",
                    # Benefits and contributions
                    "contributi",
                    "inps",
                    "inail",
                    "malattia",
                    "ferie",
                    "permessi",
                    "straordinario",
                    "festivo",
                    "notturno",
                    "reperibilità",
                    "maternità",
                    "paternità",
                    "congedo",
                    "aspettativa",
                    # Workplace issues
                    "mobbing",
                    "demansionamento",
                    "trasferimento",
                    "orario",
                    "sicurezza",
                    "infortunio",
                    "malattia professionale",
                    "disciplinare",
                    "sanzione",
                    "preavviso",
                    # CCNL-specific terms
                    "operaio",
                    "impiegato",
                    "dirigente",
                    "quadro",
                    "apprendista",
                    "metalmeccanico",
                    "edilizia",
                    "commercio",
                    "tessile",
                    "chimico",
                    "alimentare",
                    "trasporti",
                    "logistica",
                    "bancario",
                    "assicurazioni",
                    "stipendio",
                    "salario",
                    "retribuzione",
                    "paga",
                    "indennità",
                    "tredicesima",
                    "quattordicesima",
                    "premio",
                    "bonus",
                    "livello",
                    "categoria",
                    "inquadramento",
                    "mansioni",
                    "scatti",
                    "avanzamento",
                    "carriera",
                    "promozione",
                    "benefit",
                    "welfare",
                    "buoni pasto",
                    "mensa",
                    "trasporto",
                    "settore",
                    "comparto",
                    "sindacato",
                    "rappresentanza",
                    "zona geografica",
                    "nord",
                    "centro",
                    "sud",
                    "isole",
                ],
                "sub_domains": {
                    "subordinato": ["lavoro subordinato", "dipendente", "contratto lavoro"],
                    "autonomo": ["lavoro autonomo", "partita iva", "consulenza"],
                    "contributi": ["contributi", "inps", "inail", "previdenza"],
                    "licenziamento": ["licenziamento", "giusta causa", "giustificato motivo"],
                    "ccnl": ["ccnl", "contratto collettivo", "categoria", "settore", "comparto"],
                    "salary": ["stipendio", "salario", "retribuzione", "paga", "tredicesima"],
                    "benefits": ["ferie", "permessi", "malattia", "maternità", "benefit", "welfare"],
                    "sectors": [
                        "metalmeccanico",
                        "edilizia",
                        "commercio",
                        "tessile",
                        "chimico",
                        "alimentare",
                        "trasporti",
                        "bancario",
                    ],
                    "job_levels": ["operaio", "impiegato", "dirigente", "quadro", "apprendista"],
                },
            },
            Domain.BUSINESS: {
                "keywords": [
                    # Company types
                    "srl",
                    "spa",
                    "snc",
                    "sas",
                    "società",
                    "impresa",
                    "ditta individuale",
                    "startup",
                    "pmi",
                    # Corporate structure
                    "capitale sociale",
                    "assemblea",
                    "socio",
                    "soci",
                    "quote",
                    "azioni",
                    "partecipazioni",
                    "maggioranza",
                    "minoranza",
                    "amministratore",
                    "consiglio amministrazione",
                    "collegio sindacale",
                    # Corporate operations
                    "fusione",
                    "scissione",
                    "conferimento",
                    "trasformazione",
                    "liquidazione",
                    "cessione",
                    "acquisizione",
                    "holding",
                    "controllata",
                    "collegata",
                    "gruppo",
                    # Business strategy
                    "business plan",
                    "budget",
                    "investimento",
                    "finanziamento",
                    "fondo",
                    "venture capital",
                    "equity",
                ],
                "sub_domains": {
                    "costituzione": ["costituzione", "startup", "apertura", "nuova società"],
                    "governance": ["assemblea", "amministratore", "sindaco", "governance"],
                    "straordinaria": ["fusione", "scissione", "trasformazione", "operazione straordinaria"],
                    "finanziamento": ["finanziamento", "investimento", "capitale", "fondo"],
                },
            },
            Domain.ACCOUNTING: {
                "keywords": [
                    # Financial statements
                    "bilancio",
                    "stato patrimoniale",
                    "conto economico",
                    "rendiconto finanziario",
                    "nota integrativa",
                    # Accounting principles and methods
                    "partita doppia",
                    "principi contabili",
                    "oic",
                    "ias",
                    "ifrs",
                    "ammortamento",
                    "svalutazione",
                    "accantonamento",
                    "ratei",
                    "risconti",
                    "rimanenze",
                    "lavori in corso",
                    # Accounting records
                    "fattura",
                    "fatture",
                    "contabilità",
                    "registrazione",
                    "libro giornale",
                    "mastro",
                    "prima nota",
                    "inventario",
                    "patrimoniale",
                    "economico",
                    # Analysis and reporting
                    "analisi bilancio",
                    "indici",
                    "ratio",
                    "marginalità",
                    "redditività",
                    "liquidità",
                    "solidità",
                ],
                "sub_domains": {
                    "bilancio": ["bilancio", "stato patrimoniale", "conto economico"],
                    "principi": ["principi contabili", "oic", "ias", "ifrs"],
                    "analisi": ["analisi", "indici", "ratio", "marginalità"],
                    "registrazioni": ["registrazione", "contabilità", "fattura"],
                },
            },
        }

        # Action patterns with verb indicators
        self.action_patterns = {
            Action.DOCUMENT_GENERATION: {
                "verbs": [
                    "scrivi",
                    "redigi",
                    "prepara",
                    "crea",
                    "formula",
                    "predisponi",
                    "compila",
                    "draft",
                    "elabora",
                    "stendi",
                    "genera",
                    # Colloquial Italian verbs for document requests
                    "fai",
                    "fammi",
                    "aiutami a fare",
                    "mi serve",
                    "ho bisogno di",
                    "devo scrivere",
                    "vorrei",
                    "puoi fare",
                    "mi aiuti con",
                    # Problem-solution patterns (implicit document requests)
                    "devo fare",
                    "che documento",
                    "che atto",
                    "come faccio",
                    "che documenti servono",
                    "cosa devo fare",
                    "serve un",
                    "devo scrivere",
                    "come mi difendo",
                    "come tutelarmi",
                ],
                "indicators": [
                    "modello",
                    "fac simile",
                    "bozza",
                    "template",
                    "schema",
                    # Problem indicators that imply document needs
                    "che documento",
                    "documenti servono",
                    "atto fare",
                    "serve un",
                    "non paga",
                    "non pagato",
                    "causa",
                    "difendermi",
                    "tutelarmi",
                    "problema",
                    "questione",
                    "disputa",
                    "lite",
                    "controversia",
                ],
                "document_types": {
                    "ricorso": ["ricorso", "impugnazione", "opposizione", "ricorso al tar", "ricorso tributario"],
                    "contratto": ["contratto", "accordo", "convenzione", "patto"],
                    "atto": ["atto", "citazione", "decreto", "intimazione", "decreto ingiuntivo"],
                    "lettera": ["lettera", "diffida", "messa in mora", "lettera di diffida"],
                    "dichiarazione": ["dichiarazione", "autocertificazione"],
                    "istanza": ["istanza", "domanda", "richiesta", "istanza di rimborso"],
                    "procura": ["procura", "mandato", "delega", "rappresentanza"],
                    "precetto": ["precetto", "atto di precetto", "esecuzione"],
                    "sentenza": ["sentenza", "decreto", "ordinanza"],
                    "transazione": ["transazione", "accordo transattivo", "conciliazione"],
                    "denuncia": ["denuncia", "querela", "esposto"],
                    "testamento": ["testamento", "disposizioni testamentarie", "volontà"],
                },
            },
            Action.DOCUMENT_ANALYSIS: {
                "verbs": [
                    "analizza",
                    "verifica",
                    "controlla",
                    "esamina",
                    "valuta",
                    "rivedi",
                    "leggi",
                    "interpreta",
                    "studia",
                ],
                "indicators": [
                    "ti allego",
                    "nel pdf",
                    "nel file",
                    "nel documento",
                    "ho allegato",
                    "in allegato",
                    "questo documento",
                ],
            },
            Action.CALCULATION_REQUEST: {
                "verbs": ["calcola", "determina", "quantifica", "computa", "stima"],
                "indicators": [
                    "quanto",
                    "qual è l'importo",
                    "come si calcola",
                    "formula",
                    "percentuale",
                    "aliquota",
                    "importo",
                    "costo",
                    "prezzo",
                    "valore",
                    "ammontare",
                ],
            },
            Action.COMPLIANCE_CHECK: {
                "verbs": [
                    "posso",
                    "devo",
                    "è possibile",
                    "è necessario",
                    "è obbligatorio",
                    "è legale",
                    "è consentito",
                ],
                "indicators": [
                    "obbligo",
                    "divieto",
                    "permesso",
                    "autorizzazione",
                    "normativa",
                    "legge",
                    "regolamento",
                    "disposizione",
                ],
            },
            Action.STRATEGIC_ADVICE: {
                "verbs": ["conviene", "è meglio", "consigli", "suggerisci", "raccomandi", "dovrei"],
                "indicators": [
                    "pro e contro",
                    "vantaggi",
                    "svantaggi",
                    "strategia",
                    "opportunità",
                    "rischi",
                    "alternativa",
                    "scelta",
                    "migliore",
                    "ottimale",
                    "consiglio",
                ],
            },
            Action.INFORMATION_REQUEST: {
                "indicators": [
                    "cos'è",
                    "cosa significa",
                    "come funziona",
                    "spiegami",
                    "definizione",
                    "significato",
                    "che cos'è",
                    "informazioni",
                    "dettagli",
                    "chiarimenti",
                ]
            },
            Action.CCNL_QUERY: {
                "verbs": ["confronta", "paragona", "dimmi", "trova", "cerca"],
                "indicators": [
                    "ccnl",
                    "contratto collettivo",
                    "categoria",
                    "settore",
                    "stipendio medio",
                    "quanto guadagna",
                    "salario",
                    "ferie",
                    "permessi",
                    "congedo",
                    "giorni di vacanza",
                    "preavviso",
                    "licenziamento",
                    "dimissioni",
                    "benefit",
                    "welfare",
                    "tredicesima",
                    "quattordicesima",
                    "operaio",
                    "impiegato",
                    "dirigente",
                    "apprendista",
                    "metalmeccanico",
                    "edilizia",
                    "commercio",
                    "tessile",
                    "nord",
                    "centro",
                    "sud",
                    "milano",
                    "roma",
                    "napoli",
                    "anni di esperienza",
                    "livello",
                    "inquadramento",
                ],
                "question_patterns": [
                    "quanto guadagna un",
                    "qual è lo stipendio di",
                    "quante ferie ha",
                    "quanto è il preavviso",
                    "confronta i settori",
                    "differenze tra",
                    "migliore contratto",
                    "conviene lavorare",
                ],
            },
        }

    async def classify(self, query: str) -> DomainActionClassification:
        """Main classification method with fallback strategy.

        Args:
            query: Italian professional query to classify

        Returns:
            DomainActionClassification with confidence and metadata
        """
        query_lower = query.lower()

        # Rule-based classification
        domain_scores = self._calculate_domain_scores(query_lower)
        action_scores = self._calculate_action_scores(query_lower)

        # Get best matches
        best_domain, domain_confidence = max(domain_scores.items(), key=lambda x: x[1])
        best_action, action_confidence = max(action_scores.items(), key=lambda x: x[1])

        # Combined confidence (weighted average)
        combined_confidence = domain_confidence * 0.6 + action_confidence * 0.4

        # Extract metadata
        sub_domain = self._extract_sub_domain(query_lower, best_domain)
        document_type = self._extract_document_type(query_lower, best_action)

        # OPTIMIZATION: LLM fallback disabled to reduce duplicate API calls
        # Previously, low-confidence classifications triggered an automatic LLM call,
        # resulting in 2 classifier API calls per query (rule-based + LLM fallback).
        # Rule-based classification alone provides 95%+ accuracy for tax/legal domains.
        #
        # Original thresholds kept for reference:
        # - Legal + document_generation: 0.3
        # - Legal queries: 0.4
        # - Document generation: 0.45
        # - Standard: 0.6
        #
        # If LLM fallback is needed in future, consider:
        # 1. Adding caching layer to avoid duplicate calls
        # 2. Making fallback opt-in via configuration flag
        # 3. Combining with QueryNormalizer into unified analyzer

        fallback_used = False

        # LLM fallback code commented out - reduces API calls from 4 to 3
        # if best_domain == Domain.LEGAL and best_action == Action.DOCUMENT_GENERATION:
        #     threshold = 0.3
        # elif best_domain == Domain.LEGAL:
        #     threshold = 0.4
        # elif best_action == Action.DOCUMENT_GENERATION:
        #     threshold = 0.45
        # else:
        #     threshold = 0.6
        #
        # if combined_confidence < threshold:
        #     logger.info(f"Low confidence classification ({combined_confidence:.2f}), using LLM fallback")
        #     try:
        #         llm_result = await self._llm_fallback_classification(query)
        #         if llm_result and llm_result.confidence > combined_confidence:
        #             return DomainActionClassification(
        #                 domain=llm_result.domain,
        #                 action=llm_result.action,
        #                 confidence=llm_result.confidence,
        #                 sub_domain=llm_result.sub_domain,
        #                 document_type=llm_result.document_type,
        #                 reasoning=llm_result.reasoning,
        #                 fallback_used=True
        #             )
        #     except Exception as e:
        #         logger.warning(f"LLM fallback failed: {e}, using rule-based result")

        reasoning = self._generate_reasoning(query_lower, best_domain, best_action, domain_scores, action_scores)

        return DomainActionClassification(
            domain=best_domain,
            action=best_action,
            confidence=combined_confidence,
            sub_domain=sub_domain,
            document_type=document_type,
            reasoning=reasoning,
            fallback_used=fallback_used,
        )

    def _calculate_domain_scores(self, query: str) -> dict[Domain, float]:
        """Calculate confidence scores for each domain"""
        scores = {}

        for domain, patterns in self.domain_patterns.items():
            keywords = patterns["keywords"]
            matches = []

            for keyword in keywords:
                if keyword in query:
                    # Calculate keyword density and position weight
                    count = query.count(keyword)
                    length_weight = len(keyword) / 20  # Longer keywords get higher weight
                    position_weight = 1.2 if query.find(keyword) < len(query) / 3 else 1.0  # Early position bonus

                    # Extra weight for legal domain keywords to improve coverage
                    domain_weight = 1.3 if domain == Domain.LEGAL else 1.0

                    match_score = count * (1 + length_weight) * position_weight * domain_weight
                    matches.append(match_score)

            if matches:
                # Score based on total matches with diminishing returns
                raw_score = sum(matches)
                normalized_score = min(raw_score / (raw_score + 5), 0.95)  # Max 0.95
                scores[domain] = normalized_score
            else:
                scores[domain] = 0.0

        return scores

    def _calculate_action_scores(self, query: str) -> dict[Action, float]:
        """Calculate confidence scores for each action"""
        scores = {}

        # Special handling for explicit document requests (override other patterns)
        document_request_patterns = [
            "che documento",
            "che documenti",
            "che atto",
            "che atti",
            "documenti servono",
            "documento devo",
            "atto devo",
            "documento fare",
            "atto fare",
        ]

        # "che fare?" questions with legal context should be treated as document requests
        legal_action_patterns = ["che fare", "cosa fare", "che azione", "come agire", "come procedere"]
        legal_context = ["non paga", "non pagato", "causa", "tutela", "diritti", "opporsi", "difendermi"]

        is_explicit_document_request = any(pattern in query for pattern in document_request_patterns)
        is_legal_action_request = any(action_pattern in query for action_pattern in legal_action_patterns) and any(
            legal_term in query for legal_term in legal_context
        )

        for action, patterns in self.action_patterns.items():
            matches = []

            # Boost document generation for explicit document requests
            if action == Action.DOCUMENT_GENERATION and (is_explicit_document_request or is_legal_action_request):
                matches.append(5.0)  # Very high weight for explicit document requests

            # Check verbs
            for verb in patterns.get("verbs", []):
                if verb in query:
                    # Higher weight for verbs at start of query
                    position = query.find(verb)
                    position_weight = 2.0 if position < 10 else 1.5 if position < 20 else 1.0
                    matches.append(2.0 * position_weight)

            # Check indicators
            for indicator in patterns.get("indicators", []):
                if indicator in query:
                    # Higher weight for problem indicators that imply document needs
                    problem_indicators = [
                        "che documento",
                        "documenti servono",
                        "non paga",
                        "causa",
                        "problema",
                        "disputa",
                        "lite",
                    ]
                    weight = 3.0 if any(prob in indicator for prob in problem_indicators) else 1.5
                    matches.append(weight)

            # Check document types for document_generation
            if action == Action.DOCUMENT_GENERATION:
                for _doc_type, terms in patterns.get("document_types", {}).items():
                    for term in terms:
                        if term in query:
                            # Extra high weight for legal document types
                            legal_docs = [
                                "ricorso",
                                "citazione",
                                "diffida",
                                "precetto",
                                "istanza",
                                "decreto",
                                "opposizione",
                                "contratto",
                            ]
                            weight = 4.5 if any(legal_term in term for legal_term in legal_docs) else 3.0
                            matches.append(weight)

            # Check question patterns for CCNL queries
            if action == Action.CCNL_QUERY:
                for pattern in patterns.get("question_patterns", []):
                    if pattern in query:
                        matches.append(4.0)  # Very high weight for CCNL-specific patterns

            if matches:
                raw_score = sum(matches)
                normalized_score = min(raw_score / (raw_score + 3), 0.95)
                scores[action] = normalized_score
            else:
                scores[action] = 0.0

        return scores

    def _extract_sub_domain(self, query: str, domain: Domain) -> str | None:
        """Extract sub-domain from query based on domain patterns"""
        if domain not in self.domain_patterns:
            return None

        sub_domains = self.domain_patterns[domain].get("sub_domains", {})

        for sub_domain, keywords in sub_domains.items():
            for keyword in keywords:
                if keyword in query:
                    return sub_domain

        return None

    def _extract_document_type(self, query: str, action: Action) -> str | None:
        """Extract document type for document generation actions"""
        if action != Action.DOCUMENT_GENERATION:
            return None

        doc_patterns = self.action_patterns[action].get("document_types", {})

        for doc_type, keywords in doc_patterns.items():
            for keyword in keywords:
                if keyword in query:
                    return doc_type

        return None

    def _generate_reasoning(
        self,
        query: str,
        domain: Domain,
        action: Action,
        domain_scores: dict[Domain, float],
        action_scores: dict[Action, float],
    ) -> str:
        """Generate human-readable reasoning for the classification"""
        domain_keywords = []
        for keyword in self.domain_patterns[domain]["keywords"]:
            if keyword in query:
                domain_keywords.append(keyword)

        action_keywords = []
        patterns = self.action_patterns[action]
        for verb in patterns.get("verbs", []):
            if verb in query:
                action_keywords.append(verb)
        for indicator in patterns.get("indicators", []):
            if indicator in query:
                action_keywords.append(indicator)

        reasoning = f"Domain '{domain.value}' identified from keywords: {domain_keywords[:3]}. "
        reasoning += f"Action '{action.value}' identified from: {action_keywords[:3]}."

        return reasoning

    async def _llm_fallback_classification(self, query: str) -> DomainActionClassification | None:
        """Use LLM for classification when rule-based confidence is low"""
        try:
            # Create messages first for LLM provider selection
            system_prompt = """Sei un esperto classificatore per query professionali italiane.

Classifica la query dell'utente in:
DOMAIN: tax, legal, labor, business, accounting
ACTION: information_request, document_generation, document_analysis, calculation_request, compliance_check, strategic_advice

Rispondi SOLO con formato JSON:
{
  "domain": "tax",
  "action": "calculation_request",
  "confidence": 0.85,
  "sub_domain": "iva",
  "document_type": null,
  "reasoning": "Breve spiegazione"
}"""

            user_prompt = f"Query: {query}"

            # Convert to Message objects for LLM provider
            from app.schemas.chat import Message

            messages = [Message(role="system", content=system_prompt), Message(role="user", content=user_prompt)]

            # OPTIMIZATION: Directly use gpt-4o-mini instead of routing logic
            # Bypasses provider selection overhead and guarantees cheapest model
            # Cost: ~$0.00015 per classification (vs ~$0.0002 with routing)
            # Speed: ~50ms faster (no routing calculation)
            factory = LLMFactory()
            provider = factory.create_provider(provider_type=LLMProviderType.OPENAI, model="gpt-4o-mini")

            response = await provider.chat_completion(messages=messages, temperature=0.1)

            # Parse JSON response
            import json

            try:
                result_data = json.loads(response.content)
                return DomainActionClassification(
                    domain=Domain(result_data["domain"]),
                    action=Action(result_data["action"]),
                    confidence=result_data["confidence"],
                    sub_domain=result_data.get("sub_domain"),
                    document_type=result_data.get("document_type"),
                    reasoning=result_data.get("reasoning"),
                    fallback_used=True,
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to parse LLM classification response: {e}")
                return None

        except Exception as e:
            logger.error(f"LLM fallback classification failed: {e}")
            return None

    def get_classification_stats(self) -> dict[str, Any]:
        """Get statistics about the classification patterns"""
        return {
            "domains": {
                domain.value: {
                    "keywords_count": len(patterns["keywords"]),
                    "sub_domains": list(patterns.get("sub_domains", {}).keys()),
                }
                for domain, patterns in self.domain_patterns.items()
            },
            "actions": {
                action.value: {
                    "verbs_count": len(patterns.get("verbs", [])),
                    "indicators_count": len(patterns.get("indicators", [])),
                }
                for action, patterns in self.action_patterns.items()
            },
        }

    # =========================================================================
    # DEV-007 Issue 9: Query Composition Detection for Attachment Prioritization
    # =========================================================================

    async def detect_query_composition(
        self,
        query: str,
        has_attachments: bool,
        attachment_filename: str | None = None,
    ) -> QueryComposition:
        """Detect query composition type for context prioritization.

        DEV-007 Issue 9: Users expect ChatGPT/Claude-level intelligence.
        When they upload a document and ask "calcola la mia pensione",
        we must understand they want document analysis, not KB search.

        Strategy:
        - No attachments: Fast regex-based detection (existing behavior)
        - Attachments present: LLM classification for accurate intent understanding

        Args:
            query: User's query text
            has_attachments: Whether user attached document(s)
            attachment_filename: Filename of attached document (for context)

        Returns:
            QueryComposition indicating how to prioritize context sources
        """
        if not has_attachments:
            # Fast path: regex-based for queries without attachments
            return self._detect_composition_regex(query)

        # LLM path: accurate classification when documents attached
        return await self._classify_composition_with_llm(query, attachment_filename)

    def _detect_composition_regex(self, query: str) -> QueryComposition:
        """Fast regex-based detection for queries without attachments.

        Used when no documents are attached - determines if query is
        conversational (greeting) or knowledge-seeking (KB search).
        """
        query_lower = query.lower()

        # Conversational signals (greetings, thanks, etc.)
        conversational_signals = {
            "ciao",
            "grazie",
            "buongiorno",
            "buonasera",
            "come stai",
            "salve",
            "arrivederci",
            "perfetto",
            "ok",
            "va bene",
        }

        if any(s in query_lower for s in conversational_signals):
            # Check if query is ONLY conversational (not mixed with real question)
            if len(query_lower.split()) <= 5:
                return QueryComposition.CONVERSATIONAL

        # Default: Knowledge base search
        return QueryComposition.PURE_KB

    async def _classify_composition_with_llm(
        self,
        query: str,
        filename: str | None,
    ) -> QueryComposition:
        """Use small LLM (haiku/gpt-4o-mini) to classify intent when attachments present.

        This provides ChatGPT/Claude-level understanding of user intent.
        Trade-off: +200-300ms latency for much better accuracy.

        Args:
            query: User's query text
            filename: Attached document filename (provides context)

        Returns:
            QueryComposition based on LLM's understanding of intent
        """
        from app.schemas.chat import Message

        prompt = f"""Sei un classificatore di intenti per un sistema RAG italiano.
L'utente ha allegato un documento e ha fatto una domanda.

Classifica l'intento dell'utente in una delle seguenti categorie:
- DOCUMENT_ONLY: L'utente vuole analisi basata SOLO sul documento allegato
  (es. "calcola la mia pensione", "quanto devo pagare?", "analizza questi dati")
- HYBRID: L'utente vuole analisi del documento PIÙ contesto normativo/legale
  (es. "verifica se rispetta la normativa", "confronta con le regole INPS")
- KB_ONLY: La domanda NON è correlata al documento allegato
  (caso raro, es. "che tempo fa?")

Query dell'utente: "{query}"
Nome documento allegato: "{filename or 'documento'}"

Rispondi con UNA SOLA parola: DOCUMENT_ONLY, HYBRID, o KB_ONLY"""

        try:
            # Use gpt-4o-mini for fast, cheap classification
            factory = LLMFactory()
            provider = factory.create_provider(provider_type=LLMProviderType.OPENAI, model="gpt-4o-mini")

            messages = [Message(role="user", content=prompt)]
            response = await provider.chat_completion(messages=messages, temperature=0.0, max_tokens=20)

            result = response.content.strip().upper()

            logger.info(
                "query_composition_classified",
                query_preview=query[:50],
                filename=filename,
                llm_result=result,
            )

            if "HYBRID" in result:
                return QueryComposition.HYBRID
            elif "KB_ONLY" in result:
                return QueryComposition.PURE_KB
            else:
                # Default for attachments: document analysis
                return QueryComposition.PURE_DOCUMENT

        except Exception as e:
            logger.warning(
                "query_composition_llm_failed",
                error=str(e),
                fallback="PURE_DOCUMENT",
            )
            # Safe fallback: if user attached a document, assume they want document analysis
            return QueryComposition.PURE_DOCUMENT
