"""
Domain-Action Classification System for PratikoAI.

This service provides two-dimensional classification of Italian professional queries:
1. Domain: tax, legal, labor, business, accounting
2. Action: information_request, document_generation, document_analysis, 
          calculation_request, compliance_check, strategic_advice

Uses rule-based pattern matching with LLM fallback for ambiguous cases.
"""

import re
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.core.logging import logger
from app.core.llm.factory import get_llm_provider, RoutingStrategy


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


class DomainActionClassification(BaseModel):
    """Classification result with confidence and metadata"""
    domain: Domain
    action: Action
    confidence: float
    sub_domain: Optional[str] = None
    document_type: Optional[str] = None
    reasoning: Optional[str] = None
    fallback_used: bool = False


@dataclass
class PatternMatch:
    """Pattern matching result"""
    keywords: List[str]
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
                'keywords': [
                    # General tax terms
                    'iva', 'irpef', 'ires', 'irap', 'tasse', 'imposta', 'imposte', 'aliquota', 'aliquote',
                    'detrazione', 'detrazioni', 'deduzione', 'deduzioni', 'dedurre', 'detraibile',
                    'f24', '730', 'dichiarazione', 'accertamento', 'ravvedimento', 'agenzia entrate',
                    'codice fiscale', 'partita iva', 'regime forfettario', 'ordinario',
                    'minimi', 'semplificato', 'iva ordinaria', 'iva speciale',
                    'versamento', 'versamenti', 'scadenza', 'termine',
                    'contributi', 'ritenuta', 'ritenute', 'sostituto imposta',
                    'rimborso', 'credito', 'debito', 'saldo',
                    # Specific taxes
                    'iva comunitaria', 'iva intracomunitaria', 'reverse charge',
                    'split payment', 'scissione pagamenti',
                    'cedolare secca', 'tasi', 'imu', 'bollo',
                    'imposta registro', 'successioni', 'donazioni'
                ],
                'sub_domains': {
                    'iva': ['iva', 'imposta valore aggiunto', 'aliquota iva', 'reverse charge', 'split payment'],
                    'irpef': ['irpef', 'imposta reddito', 'persone fisiche', '730', 'unico'],
                    'ires': ['ires', 'imposta società', 'reddito società'],
                    'irap': ['irap', 'attività produttive', 'regionale'],
                    'forfettario': ['regime forfettario', 'forfettario', 'flat tax', '5%', '15%'],
                    'successioni': ['successione', 'eredità', 'donazione', 'imposta successioni']
                }
            },
            
            Domain.LEGAL: {
                'keywords': [
                    # Court and legal proceedings
                    'ricorso', 'atto', 'tribunale', 'giudice', 'decreto', 'sentenza',
                    'citazione', 'procura', 'intimazione', 'pignoramento', 'udienza',
                    'notifica', 'controversia', 'cassazione', 'tar', 'consiglio stato',
                    'appello', 'primo grado', 'secondo grado', 'legittimità',
                    # Legal documents and procedures
                    'contratto', 'clausola', 'clausole', 'accordo', 'transazione',
                    'risoluzione', 'rescissione', 'nullità', 'annullamento',
                    'inadempimento', 'mora', 'danni', 'risarcimento',
                    'responsabilità', 'garanzia', 'fideiussione',
                    # Legal entities and roles
                    'avvocato', 'legale', 'patrocinio', 'rappresentanza',
                    'mandato', 'procuratore', 'difensore'
                ],
                'sub_domains': {
                    'civile': ['civile', 'contratto', 'responsabilità', 'danni', 'risarcimento'],
                    'amministrativo': ['tar', 'consiglio stato', 'amministrativo', 'ricorso amministrativo'],
                    'tributario': ['commissione tributaria', 'ricorso tributario', 'accertamento'],
                    'societario': ['società', 'assemblea', 'delibera', 'socio', 'amministratore'],
                    'fallimentare': ['fallimento', 'concordato', 'liquidazione', 'insolvenza']
                }
            },
            
            Domain.LABOR: {
                'keywords': [
                    # Employment relationships
                    'licenziamento', 'ccnl', 'busta paga', 'tfr', 'assunzione', 'dimissioni',
                    'contratto lavoro', 'subordinato', 'autonomo', 'parasubordinato',
                    'apprendistato', 'tirocinio', 'stage', 'collaborazione',
                    # Benefits and contributions
                    'contributi', 'inps', 'inail', 'malattia', 'ferie', 'permessi',
                    'straordinario', 'festivo', 'notturno', 'reperibilità',
                    'maternità', 'paternità', 'congedo', 'aspettativa',
                    # Workplace issues
                    'mobbing', 'demansionamento', 'trasferimento', 'orario',
                    'sicurezza', 'infortunio', 'malattia professionale',
                    'disciplinare', 'sanzione', 'preavviso',
                    # CCNL-specific terms
                    'operaio', 'impiegato', 'dirigente', 'quadro', 'apprendista',
                    'metalmeccanico', 'edilizia', 'commercio', 'tessile', 'chimico', 'alimentare',
                    'trasporti', 'logistica', 'bancario', 'assicurazioni',
                    'stipendio', 'salario', 'retribuzione', 'paga', 'indennità',
                    'tredicesima', 'quattordicesima', 'premio', 'bonus',
                    'livello', 'categoria', 'inquadramento', 'mansioni',
                    'scatti', 'avanzamento', 'carriera', 'promozione',
                    'benefit', 'welfare', 'buoni pasto', 'mensa', 'trasporto',
                    'settore', 'comparto', 'sindacato', 'rappresentanza',
                    'zona geografica', 'nord', 'centro', 'sud', 'isole'
                ],
                'sub_domains': {
                    'subordinato': ['lavoro subordinato', 'dipendente', 'contratto lavoro'],
                    'autonomo': ['lavoro autonomo', 'partita iva', 'consulenza'],
                    'contributi': ['contributi', 'inps', 'inail', 'previdenza'],
                    'licenziamento': ['licenziamento', 'giusta causa', 'giustificato motivo'],
                    'ccnl': ['ccnl', 'contratto collettivo', 'categoria', 'settore', 'comparto'],
                    'salary': ['stipendio', 'salario', 'retribuzione', 'paga', 'tredicesima'],
                    'benefits': ['ferie', 'permessi', 'malattia', 'maternità', 'benefit', 'welfare'],
                    'sectors': ['metalmeccanico', 'edilizia', 'commercio', 'tessile', 'chimico', 'alimentare', 'trasporti', 'bancario'],
                    'job_levels': ['operaio', 'impiegato', 'dirigente', 'quadro', 'apprendista']
                }
            },
            
            Domain.BUSINESS: {
                'keywords': [
                    # Company types
                    'srl', 'spa', 'snc', 'sas', 'società', 'impresa',
                    'ditta individuale', 'startup', 'pmi',
                    # Corporate structure
                    'capitale sociale', 'assemblea', 'socio', 'soci', 'quote', 'azioni',
                    'partecipazioni', 'maggioranza', 'minoranza',
                    'amministratore', 'consiglio amministrazione', 'collegio sindacale',
                    # Corporate operations
                    'fusione', 'scissione', 'conferimento', 'trasformazione',
                    'liquidazione', 'cessione', 'acquisizione',
                    'holding', 'controllata', 'collegata', 'gruppo',
                    # Business strategy
                    'business plan', 'budget', 'investimento', 'finanziamento',
                    'fondo', 'venture capital', 'equity'
                ],
                'sub_domains': {
                    'costituzione': ['costituzione', 'startup', 'apertura', 'nuova società'],
                    'governance': ['assemblea', 'amministratore', 'sindaco', 'governance'],
                    'straordinaria': ['fusione', 'scissione', 'trasformazione', 'operazione straordinaria'],
                    'finanziamento': ['finanziamento', 'investimento', 'capitale', 'fondo']
                }
            },
            
            Domain.ACCOUNTING: {
                'keywords': [
                    # Financial statements
                    'bilancio', 'stato patrimoniale', 'conto economico',
                    'rendiconto finanziario', 'nota integrativa',
                    # Accounting principles and methods
                    'partita doppia', 'principi contabili', 'oic', 'ias', 'ifrs',
                    'ammortamento', 'svalutazione', 'accantonamento',
                    'ratei', 'risconti', 'rimanenze', 'lavori in corso',
                    # Accounting records
                    'fattura', 'fatture', 'contabilità', 'registrazione',
                    'libro giornale', 'mastro', 'prima nota',
                    'inventario', 'patrimoniale', 'economico',
                    # Analysis and reporting
                    'analisi bilancio', 'indici', 'ratio', 'marginalità',
                    'redditività', 'liquidità', 'solidità'
                ],
                'sub_domains': {
                    'bilancio': ['bilancio', 'stato patrimoniale', 'conto economico'],
                    'principi': ['principi contabili', 'oic', 'ias', 'ifrs'],
                    'analisi': ['analisi', 'indici', 'ratio', 'marginalità'],
                    'registrazioni': ['registrazione', 'contabilità', 'fattura']
                }
            }
        }
        
        # Action patterns with verb indicators
        self.action_patterns = {
            Action.DOCUMENT_GENERATION: {
                'verbs': [
                    'scrivi', 'redigi', 'prepara', 'crea', 'formula', 'predisponi',
                    'compila', 'draft', 'elabora', 'stendi', 'genera'
                ],
                'indicators': [
                    'modello', 'fac simile', 'bozza', 'template', 'schema'
                ],
                'document_types': {
                    'ricorso': ['ricorso', 'impugnazione', 'opposizione'],
                    'contratto': ['contratto', 'accordo', 'convenzione'],
                    'atto': ['atto', 'citazione', 'decreto', 'intimazione'],
                    'lettera': ['lettera', 'diffida', 'messa in mora'],
                    'dichiarazione': ['dichiarazione', 'autocertificazione'],
                    'istanza': ['istanza', 'domanda', 'richiesta'],
                    'procura': ['procura', 'mandato', 'delega']
                }
            },
            
            Action.DOCUMENT_ANALYSIS: {
                'verbs': [
                    'analizza', 'verifica', 'controlla', 'esamina', 'valuta',
                    'rivedi', 'leggi', 'interpreta', 'studia'
                ],
                'indicators': [
                    'ti allego', 'nel pdf', 'nel file', 'nel documento',
                    'ho allegato', 'in allegato', 'questo documento'
                ]
            },
            
            Action.CALCULATION_REQUEST: {
                'verbs': [
                    'calcola', 'determina', 'quantifica', 'computa', 'stima'
                ],
                'indicators': [
                    'quanto', 'qual è l\'importo', 'come si calcola',
                    'formula', 'percentuale', 'aliquota', 'importo',
                    'costo', 'prezzo', 'valore', 'ammontare'
                ]
            },
            
            Action.COMPLIANCE_CHECK: {
                'verbs': [
                    'posso', 'devo', 'è possibile', 'è necessario',
                    'è obbligatorio', 'è legale', 'è consentito'
                ],
                'indicators': [
                    'obbligo', 'divieto', 'permesso', 'autorizzazione',
                    'normativa', 'legge', 'regolamento', 'disposizione'
                ]
            },
            
            Action.STRATEGIC_ADVICE: {
                'verbs': [
                    'conviene', 'è meglio', 'consigli', 'suggerisci',
                    'raccomandi', 'dovrei'
                ],
                'indicators': [
                    'pro e contro', 'vantaggi', 'svantaggi', 'strategia',
                    'opportunità', 'rischi', 'alternativa', 'scelta',
                    'migliore', 'ottimale', 'consiglio'
                ]
            },
            
            Action.INFORMATION_REQUEST: {
                'indicators': [
                    'cos\'è', 'cosa significa', 'come funziona', 'spiegami',
                    'definizione', 'significato', 'che cos\'è',
                    'informazioni', 'dettagli', 'chiarimenti'
                ]
            },
            
            Action.CCNL_QUERY: {
                'verbs': [
                    'confronta', 'paragona', 'dimmi', 'trova', 'cerca'
                ],
                'indicators': [
                    'ccnl', 'contratto collettivo', 'categoria', 'settore',
                    'stipendio medio', 'quanto guadagna', 'salario',
                    'ferie', 'permessi', 'congedo', 'giorni di vacanza',
                    'preavviso', 'licenziamento', 'dimissioni',
                    'benefit', 'welfare', 'tredicesima', 'quattordicesima',
                    'operaio', 'impiegato', 'dirigente', 'apprendista',
                    'metalmeccanico', 'edilizia', 'commercio', 'tessile',
                    'nord', 'centro', 'sud', 'milano', 'roma', 'napoli',
                    'anni di esperienza', 'livello', 'inquadramento'
                ],
                'question_patterns': [
                    'quanto guadagna un', 'qual è lo stipendio di',
                    'quante ferie ha', 'quanto è il preavviso',
                    'confronta i settori', 'differenze tra',
                    'migliore contratto', 'conviene lavorare'
                ]
            }
        }
        
    async def classify(self, query: str) -> DomainActionClassification:
        """
        Main classification method with fallback strategy.
        
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
        combined_confidence = (domain_confidence * 0.6 + action_confidence * 0.4)
        
        # Extract metadata
        sub_domain = self._extract_sub_domain(query_lower, best_domain)
        document_type = self._extract_document_type(query_lower, best_action)
        
        # Use LLM fallback if confidence is too low
        fallback_used = False
        if combined_confidence < 0.6:
            logger.info(f"Low confidence classification ({combined_confidence:.2f}), using LLM fallback")
            try:
                llm_result = await self._llm_fallback_classification(query)
                if llm_result and llm_result.confidence > combined_confidence:
                    return llm_result._replace(fallback_used=True)
            except Exception as e:
                logger.warning(f"LLM fallback failed: {e}, using rule-based result")
        
        reasoning = self._generate_reasoning(query_lower, best_domain, best_action, domain_scores, action_scores)
        
        return DomainActionClassification(
            domain=best_domain,
            action=best_action,
            confidence=combined_confidence,
            sub_domain=sub_domain,
            document_type=document_type,
            reasoning=reasoning,
            fallback_used=fallback_used
        )
        
    def _calculate_domain_scores(self, query: str) -> Dict[Domain, float]:
        """Calculate confidence scores for each domain"""
        scores = {}
        
        for domain, patterns in self.domain_patterns.items():
            keywords = patterns['keywords']
            matches = []
            
            for keyword in keywords:
                if keyword in query:
                    # Calculate keyword density and position weight
                    count = query.count(keyword)
                    length_weight = len(keyword) / 20  # Longer keywords get higher weight
                    position_weight = 1.2 if query.find(keyword) < len(query) / 3 else 1.0  # Early position bonus
                    
                    match_score = count * (1 + length_weight) * position_weight
                    matches.append(match_score)
            
            if matches:
                # Score based on total matches with diminishing returns
                raw_score = sum(matches)
                normalized_score = min(raw_score / (raw_score + 5), 0.95)  # Max 0.95
                scores[domain] = normalized_score
            else:
                scores[domain] = 0.0
                
        return scores
        
    def _calculate_action_scores(self, query: str) -> Dict[Action, float]:
        """Calculate confidence scores for each action"""
        scores = {}
        
        for action, patterns in self.action_patterns.items():
            score = 0.0
            matches = []
            
            # Check verbs
            for verb in patterns.get('verbs', []):
                if verb in query:
                    # Higher weight for verbs at start of query
                    position = query.find(verb)
                    position_weight = 2.0 if position < 10 else 1.5 if position < 20 else 1.0
                    matches.append(2.0 * position_weight)
            
            # Check indicators
            for indicator in patterns.get('indicators', []):
                if indicator in query:
                    matches.append(1.5)
            
            # Check document types for document_generation
            if action == Action.DOCUMENT_GENERATION:
                for doc_type, terms in patterns.get('document_types', {}).items():
                    for term in terms:
                        if term in query:
                            matches.append(3.0)  # High weight for document type identification
            
            # Check question patterns for CCNL queries
            if action == Action.CCNL_QUERY:
                for pattern in patterns.get('question_patterns', []):
                    if pattern in query:
                        matches.append(4.0)  # Very high weight for CCNL-specific patterns
            
            if matches:
                raw_score = sum(matches)
                normalized_score = min(raw_score / (raw_score + 3), 0.95)
                scores[action] = normalized_score
            else:
                scores[action] = 0.0
                
        return scores
        
    def _extract_sub_domain(self, query: str, domain: Domain) -> Optional[str]:
        """Extract sub-domain from query based on domain patterns"""
        if domain not in self.domain_patterns:
            return None
            
        sub_domains = self.domain_patterns[domain].get('sub_domains', {})
        
        for sub_domain, keywords in sub_domains.items():
            for keyword in keywords:
                if keyword in query:
                    return sub_domain
                    
        return None
        
    def _extract_document_type(self, query: str, action: Action) -> Optional[str]:
        """Extract document type for document generation actions"""
        if action != Action.DOCUMENT_GENERATION:
            return None
            
        doc_patterns = self.action_patterns[action].get('document_types', {})
        
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
        domain_scores: Dict[Domain, float],
        action_scores: Dict[Action, float]
    ) -> str:
        """Generate human-readable reasoning for the classification"""
        
        domain_keywords = []
        for keyword in self.domain_patterns[domain]['keywords']:
            if keyword in query:
                domain_keywords.append(keyword)
        
        action_keywords = []
        patterns = self.action_patterns[action]
        for verb in patterns.get('verbs', []):
            if verb in query:
                action_keywords.append(verb)
        for indicator in patterns.get('indicators', []):
            if indicator in query:
                action_keywords.append(indicator)
        
        reasoning = f"Domain '{domain.value}' identified from keywords: {domain_keywords[:3]}. "
        reasoning += f"Action '{action.value}' identified from: {action_keywords[:3]}."
        
        return reasoning
        
    async def _llm_fallback_classification(self, query: str) -> Optional[DomainActionClassification]:
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
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Get cost-optimized LLM provider
            provider = get_llm_provider(
                messages=messages,
                strategy=RoutingStrategy.COST_OPTIMIZED,
                max_cost_eur=0.003  # Low cost for classification
            )
            
            response = await provider.chat_completion(messages=messages, temperature=0.1)
            
            # Parse JSON response
            import json
            try:
                result_data = json.loads(response.content)
                return DomainActionClassification(
                    domain=Domain(result_data['domain']),
                    action=Action(result_data['action']),
                    confidence=result_data['confidence'],
                    sub_domain=result_data.get('sub_domain'),
                    document_type=result_data.get('document_type'),
                    reasoning=result_data.get('reasoning'),
                    fallback_used=True
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to parse LLM classification response: {e}")
                return None
                
        except Exception as e:
            logger.error(f"LLM fallback classification failed: {e}")
            return None
            
    def get_classification_stats(self) -> Dict[str, Any]:
        """Get statistics about the classification patterns"""
        return {
            "domains": {
                domain.value: {
                    "keywords_count": len(patterns["keywords"]),
                    "sub_domains": list(patterns.get("sub_domains", {}).keys())
                }
                for domain, patterns in self.domain_patterns.items()
            },
            "actions": {
                action.value: {
                    "verbs_count": len(patterns.get("verbs", [])),
                    "indicators_count": len(patterns.get("indicators", []))
                }
                for action, patterns in self.action_patterns.items()
            }
        }