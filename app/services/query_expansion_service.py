"""Italian Tax Query Expansion Service.

Expands queries with Italian tax terminology, acronyms, and related concepts
to improve search accuracy and recall for tax professionals.
"""

import asyncio
import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.services.cache import CacheService

if TYPE_CHECKING:
    # EmbeddingService is optional - only needed for async semantic expansion
    pass


@dataclass
class ExpansionCandidate:
    """Candidate term for query expansion"""

    term: str
    score: float
    source: str  # 'synonym', 'semantic', 'acronym', 'related'
    confidence: float


class ItalianTaxQueryExpander:
    """Advanced query expansion for Italian tax terminology.

    Provides multi-layered expansion including:
    - Direct tax terminology mappings
    - Acronym expansions (IVA → Imposta Valore Aggiunto)
    - Professional vs casual language variations
    - Semantic similarity via embeddings
    - Regional and dialectal variations
    """

    def __init__(self, embedding_service: Any | None = None, cache_service: CacheService | None = None):
        """Initialize the query expander.

        Args:
            embedding_service: Optional embedding service for semantic expansion.
                              Can be None for sync-only colloquial expansion.
            cache_service: Optional cache service for caching expansion results.
        """
        self.embeddings = embedding_service
        self.cache = cache_service

        # Performance settings
        self.semantic_similarity_threshold = 0.8
        self.max_semantic_expansions = 3
        self.expansion_cache_ttl = 7200  # 2 hours

        # Initialize Italian tax terminology mappings
        self.tax_expansions = self._build_tax_expansions()
        self.professional_terms = self._build_professional_terms()
        self.acronym_mappings = self._build_acronym_mappings()
        self.regional_variations = self._build_regional_variations()
        self.concept_relationships = self._build_concept_relationships()

    async def expand_query(
        self, query: str, max_expansions: int = 5, include_semantic: bool = True, min_confidence: float = 0.7
    ) -> list[str]:
        """Expand query with Italian tax terminology and related concepts.

        Args:
            query: Original query in Italian
            max_expansions: Maximum number of expansion terms
            include_semantic: Whether to include semantic expansions
            min_confidence: Minimum confidence for expansion terms

        Returns:
            List of expansion terms sorted by relevance
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Check cache first
            cache_key = self._generate_cache_key(query, max_expansions, include_semantic)
            if self.cache:
                cached_expansions = await self.cache.get(cache_key)
                if cached_expansions:
                    logger.debug(f"Cache hit for query expansion: {query[:50]}...")
                    return cached_expansions[:max_expansions]

            # Tokenize and normalize query
            tokens = self._tokenize_query(query)
            logger.debug(f"Expanding query: '{query}' -> tokens: {tokens}")

            # Collect expansion candidates from multiple sources
            candidates = []

            # 1. Direct terminology expansion
            candidates.extend(await self._expand_tax_terminology(tokens))

            # 2. Acronym expansion
            candidates.extend(await self._expand_acronyms(tokens))

            # 3. Professional term expansion
            candidates.extend(await self._expand_professional_terms(tokens))

            # 4. Regional variation expansion
            candidates.extend(await self._expand_regional_variations(tokens))

            # 5. Concept relationship expansion
            candidates.extend(await self._expand_related_concepts(tokens, query))

            # 6. Semantic expansion (if enabled)
            if include_semantic and len(candidates) < max_expansions:
                semantic_candidates = await self._semantic_expansion(query, max_expansions - len(candidates))
                candidates.extend(semantic_candidates)

            # Filter and rank candidates
            filtered_candidates = self._filter_candidates(candidates, query, min_confidence)

            # Convert to final expansion terms
            expansions = [candidate.term for candidate in filtered_candidates[:max_expansions]]

            # Cache results
            if self.cache and expansions:
                await self.cache.setex(cache_key, self.expansion_cache_ttl, expansions)

            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.info(f"Query expansion completed in {execution_time:.1f}ms: {len(expansions)} terms")

            # Ensure performance requirement (<50ms)
            if execution_time > 50:
                logger.warning(f"Query expansion exceeded 50ms target: {execution_time:.1f}ms")

            return expansions

        except Exception as e:
            logger.error(f"Query expansion failed for '{query}': {e}")
            return []

    def _tokenize_query(self, query: str) -> list[str]:
        """Tokenize query preserving Italian tax phrases"""
        # Preserve important multi-word terms
        protected_phrases = [
            "partita iva",
            "regime forfettario",
            "dichiarazione dei redditi",
            "fattura elettronica",
            "codice fiscale",
            "imposta sul reddito",
            "valore aggiunto",
            "modello 730",
            "modello unico",
            "f24 online",
        ]

        query_lower = query.lower()
        tokens = []

        # First, extract protected phrases
        remaining_query = query_lower
        for phrase in protected_phrases:
            if phrase in remaining_query:
                tokens.append(phrase)
                remaining_query = remaining_query.replace(phrase, " ")

        # Then tokenize remaining words
        words = [word.strip() for word in remaining_query.split() if len(word.strip()) > 2]
        tokens.extend(words)

        return list(set(tokens))  # Remove duplicates

    async def _expand_tax_terminology(self, tokens: list[str]) -> list[ExpansionCandidate]:
        """Expand with direct tax terminology mappings"""
        candidates = []

        for token in tokens:
            if token in self.tax_expansions:
                for expansion in self.tax_expansions[token]:
                    if expansion != token:  # Don't include the original term
                        candidates.append(
                            ExpansionCandidate(term=expansion, score=0.9, source="tax_terminology", confidence=0.95)
                        )

        return candidates

    async def _expand_acronyms(self, tokens: list[str]) -> list[ExpansionCandidate]:
        """Expand acronyms to full forms"""
        candidates = []

        for token in tokens:
            token_upper = token.upper()
            if token_upper in self.acronym_mappings:
                full_form = self.acronym_mappings[token_upper]
                candidates.append(ExpansionCandidate(term=full_form, score=0.95, source="acronym", confidence=0.9))

        return candidates

    async def _expand_professional_terms(self, tokens: list[str]) -> list[ExpansionCandidate]:
        """Expand with professional terminology variations"""
        candidates = []

        for token in tokens:
            if token in self.professional_terms:
                for variant in self.professional_terms[token]:
                    if variant != token:
                        candidates.append(
                            ExpansionCandidate(term=variant, score=0.8, source="professional", confidence=0.85)
                        )

        return candidates

    async def _expand_regional_variations(self, tokens: list[str]) -> list[ExpansionCandidate]:
        """Expand with regional and dialectal variations"""
        candidates = []

        for token in tokens:
            if token in self.regional_variations:
                for variation in self.regional_variations[token]:
                    if variation != token:
                        candidates.append(
                            ExpansionCandidate(term=variation, score=0.7, source="regional", confidence=0.75)
                        )

        return candidates

    async def _expand_related_concepts(self, tokens: list[str], full_query: str) -> list[ExpansionCandidate]:
        """Expand with conceptually related terms"""
        candidates = []

        # Check for concept relationships
        query_concepts = set()
        for token in tokens:
            if token in self.concept_relationships:
                query_concepts.update(self.concept_relationships[token])

        # Add related concepts as candidates
        for concept in query_concepts:
            if concept not in full_query.lower():
                candidates.append(ExpansionCandidate(term=concept, score=0.75, source="conceptual", confidence=0.8))

        return candidates

    async def _semantic_expansion(self, query: str, max_expansions: int) -> list[ExpansionCandidate]:
        """Find semantically related terms using embeddings"""
        try:
            if not self.embeddings:
                return []

            # Generate query embedding
            query_embedding = await self.embeddings.embed(query)
            if not query_embedding:
                return []

            # Search for similar terms in Italian tax terminology namespace
            similar_terms = await self.embeddings.find_similar_terms(
                query_embedding,
                namespace="italian_tax_terms",
                top_k=max_expansions * 2,  # Get more for filtering
            )

            candidates = []
            for term_data in similar_terms:
                if term_data["score"] >= self.semantic_similarity_threshold:
                    # Ensure term is not already in query
                    if term_data["text"].lower() not in query.lower():
                        candidates.append(
                            ExpansionCandidate(
                                term=term_data["text"],
                                score=term_data["score"],
                                source="semantic",
                                confidence=term_data["score"],
                            )
                        )

            return candidates[:max_expansions]

        except Exception as e:
            logger.error(f"Semantic expansion failed: {e}")
            return []

    def _filter_candidates(
        self, candidates: list[ExpansionCandidate], original_query: str, min_confidence: float
    ) -> list[ExpansionCandidate]:
        """Filter and rank expansion candidates"""
        # Remove duplicates and low-confidence candidates
        seen_terms = set()
        filtered = []

        for candidate in candidates:
            if (
                candidate.confidence >= min_confidence
                and candidate.term.lower() not in seen_terms
                and candidate.term.lower() not in original_query.lower()
            ):
                seen_terms.add(candidate.term.lower())
                filtered.append(candidate)

        # Sort by score, then confidence, then source priority
        source_priority = {
            "acronym": 4,
            "tax_terminology": 3,
            "semantic": 2,
            "professional": 1,
            "regional": 0,
            "conceptual": 0,
        }

        filtered.sort(key=lambda x: (x.score, x.confidence, source_priority.get(x.source, 0)), reverse=True)

        return filtered

    def _generate_cache_key(self, query: str, max_expansions: int, include_semantic: bool) -> str:
        """Generate cache key for expansion results"""
        key_string = f"{query}|{max_expansions}|{include_semantic}"
        return f"query_expansion:{hashlib.md5(key_string.encode()).hexdigest()}"

    def _build_tax_expansions(self) -> dict[str, list[str]]:
        """Build comprehensive Italian tax terminology mappings"""
        return {
            # IVA (Imposta sul Valore Aggiunto)
            "iva": [
                "imposta valore aggiunto",
                "imposta sul valore aggiunto",
                "aliquota iva",
                "regime iva",
                "fatturazione iva",
                "detraibile iva",
                "imponibile iva",
            ],
            "aliquota": [
                "aliquota iva",
                "aliquota ordinaria",
                "aliquota ridotta",
                "aliquota agevolata",
                "percentuale iva",
            ],
            # IRPEF (Imposta sul Reddito delle Persone Fisiche)
            "irpef": [
                "imposta reddito persone fisiche",
                "imposta sul reddito",
                "ritenuta irpef",
                "scaglioni irpef",
                "addizionale irpef",
            ],
            "reddito": [
                "reddito imponibile",
                "reddito complessivo",
                "reddito lordo",
                "reddito netto",
                "dichiarazione redditi",
            ],
            # Partita IVA
            "partita iva": [
                "p.iva",
                "piva",
                "numero iva",
                "codice iva",
                "apertura partita iva",
                "chiusura partita iva",
            ],
            "libero professionista": [
                "partita iva",
                "professionista autonomo",
                "lavoro autonomo",
                "attività professionale",
            ],
            # Fatturazione
            "fattura": [
                "fatturazione",
                "fattura elettronica",
                "e-fattura",
                "emissione fattura",
                "registrazione fattura",
                "sdi fattura",
            ],
            "fatturazione elettronica": [
                "fattura elettronica",
                "e-fattura",
                "xml fattura",
                "sistema interscambio",
                "sdi",
                "fatturazione digitale",
            ],
            # Modelli fiscali
            "f24": ["modello f24", "f24 online", "versamento f24", "delega f24", "compensazione f24"],
            "730": ["modello 730", "730 precompilato", "dichiarazione 730", "caf 730", "elaborazione 730"],
            "unico": ["modello unico", "unico persone fisiche", "unico società", "dichiarazione unico"],
            # Regime forfettario
            "regime forfettario": [
                "forfettario",
                "regime semplificato",
                "flat tax",
                "regime agevolato",
                "contribuenti minimi",
            ],
            "forfettario": [
                "regime forfettario",
                "coefficiente redditività",
                "soglia forfettario",
                "requisiti forfettario",
            ],
            # Detrazioni e deduzioni
            "detrazione": [
                "detrazioni fiscali",
                "detrazione irpef",
                "spese detraibili",
                "oneri detraibili",
                "rimborso detrazione",
            ],
            "deduzione": ["deduzioni fiscali", "oneri deducibili", "spese deducibili", "deduzione dal reddito"],
            # Tributi locali
            "imu": [
                "imposta municipale unica",
                "imposta municipale",
                "tassa casa",
                "tassa immobili",
                "tributo immobiliare",
            ],
            "tari": ["tassa rifiuti", "tributo rifiuti", "tassa ambientale", "tariffa rifiuti"],
            "tasi": ["tassa servizi indivisibili", "tributo servizi"],
            # Contributi previdenziali
            "contributi": [
                "contributi inps",
                "contributi previdenziali",
                "versamenti contributivi",
                "gestione separata",
            ],
            "inps": [
                "istituto previdenza sociale",
                "contributi inps",
                "gestione separata inps",
                "cassetto previdenziale",
            ],
            # Società e forme giuridiche
            "srl": ["società responsabilità limitata", "s.r.l.", "società di capitali", "srl semplificata"],
            "spa": ["società per azioni", "s.p.a.", "società di capitali", "consiglio amministrazione"],
            "snc": ["società nome collettivo", "s.n.c.", "società di persone", "responsabilità illimitata"],
            "sas": ["società accomandita semplice", "s.a.s.", "società di persone", "soci accomandanti"],
        }

    def _build_professional_terms(self) -> dict[str, list[str]]:
        """Build professional terminology variations"""
        return {
            "commercialista": [
                "dottore commercialista",
                "consulente fiscale",
                "consulente tributario",
                "esperto contabile",
            ],
            "consulente": ["commercialista", "consulente fiscale", "consulente del lavoro", "advisor fiscale"],
            "studio": ["studio commercialista", "studio fiscale", "studio tributario", "ufficio fiscale"],
            "cliente": ["contribuente", "soggetto passivo", "titolare partita iva", "impresa"],
            "assistenza": ["consulenza fiscale", "servizi fiscali", "supporto tributario", "adempimenti fiscali"],
            "dichiarazione": [
                "dichiarazione fiscale",
                "dichiarazione tributaria",
                "dichiarazione redditi",
                "adempimento dichiarativo",
            ],
            "versamento": [
                "pagamento imposte",
                "versamento tributi",
                "adempimento versamento",
                "liquidazione imposte",
            ],
            "scadenza": ["termine versamento", "scadenza fiscale", "termine adempimento", "deadline fiscale"],
        }

    def _build_acronym_mappings(self) -> dict[str, str]:
        """Build acronym to full form mappings"""
        return {
            "IVA": "imposta sul valore aggiunto",
            "IRPEF": "imposta sul reddito delle persone fisiche",
            "IRES": "imposta sul reddito delle società",
            "IRAP": "imposta regionale sulle attività produttive",
            "IMU": "imposta municipale unica",
            "TARI": "tassa rifiuti",
            "TASI": "tassa servizi indivisibili",
            "INPS": "istituto nazionale previdenza sociale",
            "INAIL": "istituto nazionale infortuni sul lavoro",
            "MEF": "ministero economia e finanze",
            "SDI": "sistema di interscambio",
            "PEC": "posta elettronica certificata",
            "CAF": "centro assistenza fiscale",
            "ISEE": "indicatore situazione economica equivalente",
            "DSU": "dichiarazione sostitutiva unica",
            "CUD": "certificazione unica dipendenti",
            "CU": "certificazione unica",
            "DURC": "documento unico regolarità contributiva",
            "SCIA": "segnalazione certificata inizio attività",
        }

    def _build_regional_variations(self) -> dict[str, list[str]]:
        """Build regional and dialectal variations"""
        return {
            "tasse": ["tasse", "tributi", "imposte", "balzelli", "gabelle", "contribuzioni"],
            "soldi": ["denaro", "quattrini", "euro", "importo", "somma", "capitale"],
            "pagare": ["versare", "saldare", "liquidare", "corrispondere", "adempiere", "estinguere"],
            "guadagno": ["reddito", "provento", "utile", "ricavo", "profitto", "entrata"],
            "spesa": ["costo", "onere", "esborso", "uscita", "spettanza", "erogazione"],
            "lavoro": ["attività", "prestazione", "servizio", "professione", "occupazione"],
        }

    def _build_concept_relationships(self) -> dict[str, list[str]]:
        """Build conceptual relationships between tax terms"""
        return {
            "fattura": [
                "corrispettivo",
                "documento fiscale",
                "prova vendita",
                "registrazione contabile",
                "detraibilità iva",
            ],
            "partita iva": [
                "codice fiscale",
                "regime fiscale",
                "obblighi dichiarativi",
                "versamenti periodici",
                "comunicazioni telematiche",
            ],
            "dichiarazione": [
                "modello fiscale",
                "termine presentazione",
                "rimborso",
                "accertamento",
                "controllo fiscale",
            ],
            "iva": ["base imponibile", "aliquota applicabile", "detrazione", "rivalsa", "registro iva"],
            "reddito": [
                "base imponibile",
                "scaglioni tassazione",
                "no tax area",
                "detrazioni personali",
                "addizionali",
            ],
            "contributi": [
                "minimale contributivo",
                "massimale contributivo",
                "aliquota contributiva",
                "cassa previdenza",
            ],
        }

    async def get_expansion_statistics(self) -> dict[str, Any]:
        """Get expansion service statistics"""
        try:
            if not self.cache:
                return {"error": "Cache service not available"}

            stats = await self.cache.get("expansion_stats") or {}

            return {
                "total_terms": len(self.tax_expansions) + len(self.professional_terms),
                "tax_terms": len(self.tax_expansions),
                "professional_terms": len(self.professional_terms),
                "acronyms": len(self.acronym_mappings),
                "regional_variations": len(self.regional_variations),
                "cache_hit_rate": stats.get("hit_rate", 0.0),
                "avg_expansion_time_ms": stats.get("avg_time", 0.0),
                "semantic_expansion_success": stats.get("semantic_success", 0.0),
                "performance_target_met": stats.get("avg_time", 0.0) < 50,
            }

        except Exception as e:
            logger.error(f"Failed to get expansion statistics: {e}")
            return {"error": str(e)}

    def add_custom_expansion(self, source_term: str, target_terms: list[str], category: str = "custom") -> bool:
        """Add custom expansion mapping"""
        try:
            if category == "tax":
                if source_term not in self.tax_expansions:
                    self.tax_expansions[source_term] = []
                self.tax_expansions[source_term].extend(target_terms)

            elif category == "professional":
                if source_term not in self.professional_terms:
                    self.professional_terms[source_term] = []
                self.professional_terms[source_term].extend(target_terms)

            elif category == "acronym":
                if len(target_terms) == 1:
                    self.acronym_mappings[source_term.upper()] = target_terms[0]

            logger.info(f"Added custom expansion: {source_term} -> {target_terms}")
            return True

        except Exception as e:
            logger.error(f"Failed to add custom expansion: {e}")
            return False
