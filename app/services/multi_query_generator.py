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
import json
from dataclasses import dataclass
from typing import Any

from app.core.llm.model_config import LLMModelConfig, ModelTier
from app.core.logging import logger
from app.schemas.chat import Message
from app.schemas.router import ExtractedEntity


@dataclass
class QueryVariants:
    """Container for the 3 query variants plus the original.

    Attributes:
        bm25_query: Keywords optimized for BM25/lexical search
        vector_query: Semantically expanded for vector search
        entity_query: Focused on legal entities and references
        original_query: The original user query
    """

    bm25_query: str
    vector_query: str
    entity_query: str
    original_query: str


# System prompt for multi-query generation
MULTI_QUERY_SYSTEM_PROMPT = """Sei un assistente specializzato nella generazione di varianti di query per un sistema di ricerca fiscale/legale italiano.

Il tuo compito è generare 3 varianti ottimizzate della query dell'utente:

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

RISPOSTA in formato JSON:
{
    "bm25_query": "<query keywords>",
    "vector_query": "<query semantica espansa>",
    "entity_query": "<query con entità legali>"
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
        self._model = config.get_model(ModelTier.BASIC)  # Use GPT-4o-mini
        self._provider = config.get_provider(ModelTier.BASIC)
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

        Args:
            query: User's original query
            entities: Extracted entities from router (may be empty)

        Returns:
            QueryVariants with all 3 variants plus original
        """
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
            )

            return variants

        except asyncio.TimeoutError:
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
            entity_strings = [
                f"- {e.text} ({e.type}, confidence: {e.confidence:.2f})"
                for e in entities
            ]
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
                max_tokens=400,
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
        return QueryVariants(
            bm25_query=data.get("bm25_query", original_query),
            vector_query=data.get("vector_query", original_query),
            entity_query=data.get("entity_query", original_query),
            original_query=original_query,
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
        )
