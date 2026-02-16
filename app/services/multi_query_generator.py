"""Multi-Query Generator Service for DEV-188.

Generates 3 query variants optimized for different search types:
- BM25-optimized (keywords, document types)
- Vector-optimized (semantic expansion)
- Entity-focused (legal references)

Usage:
    from app.services.multi_query_generator import MultiQueryGeneratorService

    service = MultiQueryGeneratorService(config=get_model_config())
    variants = await service.generate("Come apro P.IVA?", entities=[])
"""

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from app.core.llm.model_config import LLMModelConfig, ModelTier, resolve_model_from_env
from app.core.logging import logger
from app.schemas.chat import Message
from app.schemas.router import ExtractedEntity
from app.services.cache import cache_service


@dataclass
class QueryVariants:
    """Container for the 3 query variants plus the original.

    Attributes:
        bm25_query: Keywords optimized for BM25/lexical search
        vector_query: Semantically expanded for vector search
        entity_query: Focused on legal entities and references
        original_query: The original user query
        document_references: List of document references identified by LLM (ADR-022)
            E.g., ["Legge 199/2025", "LEGGE 30 dicembre 2025, n. 199"]
            None if no specific documents were identified.
        semantic_expansions: List of semantic equivalences for terminology bridging (DEV-242)
            Maps colloquial terms to official legal terminology and vice versa.
            E.g., ["pace fiscale", "pacificazione fiscale", "definizione agevolata"]
            None if no semantic expansions were identified.
    """

    bm25_query: str
    vector_query: str
    entity_query: str
    original_query: str
    document_references: list[str] | None = None
    semantic_expansions: list[str] | None = None


# System prompt for multi-query generation
MULTI_QUERY_SYSTEM_PROMPT = """Sei un assistente specializzato nella generazione di varianti di query per un sistema di ricerca fiscale/legale italiano.

Il tuo compito è generare 3 varianti ottimizzate della query dell'utente PIÙ identificare documenti e termini semanticamente equivalenti:

1. **bm25_query**: Query ottimizzata per ricerca lessicale (BM25)
   - Estrai solo le parole chiave rilevanti
   - Includi sinonimi tecnici italiani
   - Rimuovi articoli, preposizioni, verbi ausiliari
   - Aggiungi tipi di documento (circolare, decreto, legge)
   - Esempio: "contributi INPS artigiani 2024 gestione separata"

2. **vector_query**: Query ottimizzata per ricerca semantica (embedding)
   - Espandi semanticamente la domanda originale
   - Usa una frase completa e naturale
   - Aggiungi contesto implicito
   - Esempio: "Quali sono gli importi dei contributi previdenziali INPS per artigiani?"

3. **entity_query**: Query focalizzata sulle entità legali
   - Enfatizza riferimenti normativi (Legge X, Art. Y)
   - Includi enti (INPS, Agenzia Entrate, INAIL)
   - Aggiungi date e numeri di riferimento
   - Esempio: "Legge 104/1992 Art. 3 permessi INPS lavoratori"

4. **document_references**: Riferimenti a documenti specifici (ADR-022)
   - Identifica quale legge, decreto o documento normativo l'utente sta chiedendo
   - IMPORTANTE: Usa pattern che funzionano con ILIKE matching sui titoli dei documenti
   - Preferisci formato "n. XXX" (es. "n. 199") perché i titoli usano questo formato
   - Includi anche nomi colloquiali (es. "Legge di Bilancio 2026")
   - Se non riesci a identificare un documento specifico, lascia array vuoto []

   FORMATO TITOLI ITALIANI:
   - "LEGGE 30 dicembre 2025, n. 199" → usa "n. 199" o "dicembre 2025, n. 199"
   - "DECRETO-LEGGE 18 ottobre 2023, n. 145" → usa "n. 145" o "DL n. 145"

   Esempi:
   - "rottamazione quinquies" → ["n. 199", "dicembre 2025", "Legge di Bilancio 2026", "Rottamazione Quinquies", "AdER", "Regole Ufficiali"]
     (DEV-242 Phase 36B: Includi ANCHE "Rottamazione Quinquies" e "AdER" per trovare le regole ufficiali AdER oltre alla legge)
   - "bonus 110" → ["n. 34", "Decreto Rilancio", "maggio 2020"]
   - "flat tax" → ["n. 145", "Legge di Bilancio 2019"]
   - "Come funziona l'IVA?" → [] (domanda generica, nessun documento specifico)

5. **semantic_expansions**: Termini semanticamente equivalenti per colmare il gap terminologico (DEV-245)
   - CRITICO: I documenti legali usano terminologia DIVERSA da quella usata dagli utenti
   - NON memorizzare liste fisse - ANALIZZA semanticamente ogni query
   - Se non ci sono equivalenze semantiche rilevanti, lascia array vuoto []

   ## METODO DI ANALISI SEMANTICA (applica a QUALSIASI topic):

   Per ogni query, identifica e includi:

   1. **TERMINOLOGIA UFFICIALE**: Come appare nelle leggi italiane
      - Es: "rottamazione" → "definizione agevolata" (termine legale)
      - Es: "bonus 110" → "detrazione fiscale" (termine tecnico)

   2. **PROCEDURE ASSOCIATE**: Cosa succede durante il processo
      - Pagamento, versamento, rata, scadenza, domanda, adesione
      - Sospensione, proroga, decadenza, sanzione
      - Comunicazione, notifica, accoglimento

   3. **ASPETTI CRITICI**: Elementi che differenziano questa procedura
      - Tolleranza, margine, termine perentorio
      - Esclusione, requisito, condizione
      - Interessi, tasso, maggiorazione

   4. **ENTI COINVOLTI**: Chi gestisce la procedura
      - AdER, Agenzia Entrate, INPS, INAIL, Comuni

   5. **CONSEGUENZE**: Cosa succede in caso di inadempimento
      - Decadenza, revoca, perdita beneficio
      - Sanzione, interessi di mora
      - Debito residuo, riscossione coattiva

   ## ESEMPI DI ANALISI (diversi ambiti):

   Query: "rottamazione quinquies"
   → semantic_expansions: ["definizione agevolata", "pace fiscale", "sospensione riscossione",
      "decadenza", "tolleranza", "rate bimestrali", "scadenza domanda", "AdER"]
   (Nota: include "sospensione" e "tolleranza" per trovare info su aspetti critici)

   Query: "patent box"
   → semantic_expansions: ["agevolazione IP", "beni immateriali", "royalties",
      "proprietà intellettuale", "tassazione agevolata", "marchi", "brevetti"]

   Query: "modello 770"
   → semantic_expansions: ["dichiarazione sostituti", "ritenute", "CU",
      "certificazione unica", "versamenti fiscali", "scadenza trasmissione"]

   Query: "Come funziona l'IVA?"
   → semantic_expansions: [] (termine già tecnico, domanda generica)

RISPOSTA in formato JSON:
{
    "bm25_query": "<query keywords>",
    "vector_query": "<query semantica espansa>",
    "entity_query": "<query con entità legali>",
    "document_references": ["<riferimento 1>", "<riferimento 2>"],
    "semantic_expansions": ["<termine equivalente 1>", "<termine equivalente 2>"]
}

Rispondi SOLO con il JSON, senza testo aggiuntivo."""

MULTI_QUERY_USER_PROMPT_TEMPLATE = """Genera le 3 varianti per questa query:

Query originale: {query}
{entities_context}
Rispondi con il JSON delle varianti."""


class MultiQueryGeneratorService:
    """Service for generating optimized query variants.

    Generates 3 distinct query variants from a user query:
    - BM25: Keyword-focused for lexical search
    - Vector: Semantically expanded for embedding search
    - Entity: Focused on legal references and entities

    Example:
        config = get_model_config()
        service = MultiQueryGeneratorService(config=config)

        variants = await service.generate(
            query="Come apro P.IVA forfettaria?",
            entities=[ExtractedEntity(text="P.IVA", type="ente", confidence=0.9)]
        )
        print(variants.bm25_query)  # "P.IVA forfettaria apertura requisiti"
    """

    def __init__(self, config: LLMModelConfig):
        """Initialize the multi-query generator service.

        Args:
            config: LLM model configuration for accessing model settings
        """
        self._config = config
        self._provider, self._model = resolve_model_from_env("LLM_MODEL_MULTI_QUERY", config)
        self._timeout_ms = config.get_timeout(ModelTier.BASIC)
        self._temperature = config.get_temperature(ModelTier.BASIC)

    async def generate(
        self,
        query: str,
        entities: list[ExtractedEntity],
    ) -> QueryVariants:
        """Generate 3 optimized query variants.

        Uses GPT-4o-mini to generate BM25, vector, and entity-focused
        query variants. Falls back to original query on any error.

        DEV-251: Added caching to avoid redundant LLM calls for repeated queries.

        Args:
            query: User's original query
            entities: Extracted entities from router (may be empty)

        Returns:
            QueryVariants with all 3 variants plus original
        """
        # DEV-251: Generate query hash for caching
        query_hash = hashlib.md5(query.encode()).hexdigest()

        # DEV-251: Check cache first
        try:
            cached = await cache_service.get_cached_multi_query(query_hash=query_hash)
            if cached:
                logger.info(
                    "multiquery_cache_hit",
                    query_hash=query_hash[:12],
                )
                return QueryVariants(
                    bm25_query=cached.get("bm25_query", query),
                    vector_query=cached.get("vector_query", query),
                    entity_query=cached.get("entity_query", query),
                    original_query=query,
                    document_references=cached.get("document_references"),
                    semantic_expansions=cached.get("semantic_expansions"),
                )
        except Exception as e:
            logger.warning(
                "multiquery_cache_lookup_failed",
                error=str(e),
                query_hash=query_hash[:12],
            )
            # Continue with generation if cache fails

        try:
            # Build the prompt
            prompt = self._build_prompt(query, entities)

            # Call LLM with timeout
            timeout_seconds = self._timeout_ms / 1000
            variants = await asyncio.wait_for(
                self._call_llm(prompt, query),
                timeout=timeout_seconds,
            )

            logger.info(
                "multi_query_generated",
                original_length=len(query),
                bm25_length=len(variants.bm25_query),
                vector_length=len(variants.vector_query),
                entity_length=len(variants.entity_query),
                entity_count=len(entities),
                document_refs_count=len(variants.document_references) if variants.document_references else 0,
                semantic_expansions_count=len(variants.semantic_expansions) if variants.semantic_expansions else 0,
            )

            # DEV-251: Store result in cache
            try:
                cache_data = {
                    "bm25_query": variants.bm25_query,
                    "vector_query": variants.vector_query,
                    "entity_query": variants.entity_query,
                    "document_references": variants.document_references,
                    "semantic_expansions": variants.semantic_expansions,
                }
                await cache_service.cache_multi_query(
                    query_hash=query_hash,
                    multi_query_result=cache_data,
                )
            except Exception as e:
                logger.warning(
                    "multiquery_cache_store_failed",
                    error=str(e),
                    query_hash=query_hash[:12],
                )

            return variants

        except TimeoutError:
            logger.warning(
                "multi_query_timeout",
                query_length=len(query),
                timeout_ms=self._timeout_ms,
            )
            return self._fallback_variants(query)

        except Exception as e:
            logger.error(
                "multi_query_error",
                error=str(e),
                query_length=len(query),
            )
            return self._fallback_variants(query)

    def _build_prompt(
        self,
        query: str,
        entities: list[ExtractedEntity],
    ) -> str:
        """Build the generation prompt with query and entities.

        Args:
            query: User's query
            entities: Extracted entities to include

        Returns:
            Formatted prompt string
        """
        # Build entities context if available
        entities_context = ""
        if entities:
            entity_strings = [f"- {e.text} ({e.type}, confidence: {e.confidence:.2f})" for e in entities]
            entities_context = "\nEntità estratte:\n" + "\n".join(entity_strings) + "\n"

        return MULTI_QUERY_USER_PROMPT_TEMPLATE.format(
            query=query,
            entities_context=entities_context,
        )

    async def _call_llm(self, prompt: str, original_query: str) -> QueryVariants:
        """Call the LLM and parse the response.

        Args:
            prompt: The formatted prompt
            original_query: Original query for fallback

        Returns:
            Parsed QueryVariants

        Raises:
            Exception: On LLM API errors
            ValueError: On response parsing errors
        """
        from app.core.llm.factory import get_llm_factory

        factory = get_llm_factory()

        try:
            provider = factory.create_provider(
                provider_type=self._provider,
                model=self._model,
            )

            # Create messages for the LLM
            messages = [
                Message(role="system", content=MULTI_QUERY_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ]

            response = await provider.chat_completion(
                messages=messages,
                temperature=self._temperature,
                max_tokens=500,  # Increased for semantic_expansions (DEV-242)
            )

            return self._parse_response(response.content, original_query)

        except ValueError:
            # Re-raise parsing errors
            raise
        except Exception as e:
            logger.error(
                "multi_query_call_failed",
                error=str(e),
                model=self._model,
            )
            raise

    def _parse_response(self, response: str, original_query: str) -> QueryVariants:
        """Parse the LLM response into QueryVariants.

        Handles JSON responses with optional markdown code block wrappers.
        Missing fields fall back to the original query.

        Args:
            response: Raw LLM response string
            original_query: Original query for fallback

        Returns:
            Parsed QueryVariants

        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        # Strip whitespace
        response = response.strip()

        # Remove markdown code block wrapper if present
        if response.startswith("```"):
            # Find the end of the opening fence
            first_newline = response.find("\n")
            if first_newline > 0:
                response = response[first_newline + 1 :]

            # Remove closing fence
            if response.endswith("```"):
                response = response[:-3].strip()

        # DEBUG: Log raw response to understand why semantic_expansions is empty (DEV-250)
        logger.info(
            "multi_query_raw_response",
            response_length=len(response),
            response_preview=response[:500],
        )

        # Try to parse JSON
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(
                "multi_query_json_parse_error",
                error=str(e),
                response_preview=response[:100],
            )
            raise ValueError(f"Invalid JSON response: {e}")

        # Extract fields with fallback to original
        # ADR-022: Extract document_references if present (None if missing)
        document_refs = data.get("document_references")
        # DEV-242: Extract semantic_expansions for terminology bridging
        semantic_exps = data.get("semantic_expansions")

        # DEBUG: Log parsed values to understand what LLM returned (DEV-250)
        logger.info(
            "multi_query_parsed_response",
            has_bm25_query="bm25_query" in data,
            has_vector_query="vector_query" in data,
            has_entity_query="entity_query" in data,
            has_document_refs="document_references" in data,
            has_semantic_expansions="semantic_expansions" in data,
            document_refs_value=document_refs,
            semantic_expansions_value=semantic_exps,
        )

        return QueryVariants(
            bm25_query=data.get("bm25_query", original_query),
            vector_query=data.get("vector_query", original_query),
            entity_query=data.get("entity_query", original_query),
            original_query=original_query,
            document_references=document_refs,
            semantic_expansions=semantic_exps,
        )

    def _fallback_variants(self, query: str) -> QueryVariants:
        """Create fallback variants using original query.

        Called when LLM fails or times out.

        Args:
            query: Original query

        Returns:
            QueryVariants with original query for all variants
        """
        return QueryVariants(
            bm25_query=query,
            vector_query=query,
            entity_query=query,
            original_query=query,
            document_references=None,
            semantic_expansions=None,
        )
