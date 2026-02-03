"""HyDE Generator Service for DEV-189 and DEV-235.

Generates hypothetical documents in Italian bureaucratic style for improved
vector search retrieval. Based on the HyDE (Hypothetical Document Embeddings)
technique from Section 13.6.

DEV-235: Added conversation awareness with:
- QueryAmbiguityDetector integration for ambiguity detection
- Multi-variant generation for ambiguous queries
- Conversational prompt support using hyde_conversational.md

Usage:
    from app.services.hyde_generator import HyDEGeneratorService

    service = HyDEGeneratorService(config=get_model_config())
    result = await service.generate(
        query="Come funziona il ravvedimento operoso?",
        routing=RoutingCategory.TECHNICAL_RESEARCH,
        conversation_history=[{"role": "user", "content": "..."}],
    )
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import asdict, dataclass, field
from typing import Optional

from app.core.llm.model_config import LLMModelConfig, ModelTier
from app.core.logging import logger
from app.schemas.chat import Message
from app.schemas.router import RoutingCategory
from app.services.cache import cache_service
from app.services.prompt_loader import get_prompt_loader
from app.services.query_ambiguity_detector import get_query_ambiguity_detector


@dataclass
class HyDEResult:
    """Result from HyDE document generation.

    Attributes:
        hypothetical_document: Generated document in Italian bureaucratic style
        word_count: Number of words in the document
        skipped: Whether HyDE was skipped (for chitchat, calculator, or errors)
        skip_reason: Reason for skipping (if applicable)
        variants: List of variant documents for ambiguous queries (DEV-235)
    """

    hypothetical_document: str
    word_count: int
    skipped: bool
    skip_reason: str | None
    variants: list[HyDEResult] | None = field(default=None)


# Categories that should skip HyDE generation
SKIP_HYDE_CATEGORIES = {
    RoutingCategory.CHITCHAT,
    RoutingCategory.CALCULATOR,
}

# System prompt for HyDE generation
HYDE_SYSTEM_PROMPT = """Sei un esperto di normativa fiscale e legale italiana.
Il tuo compito è generare un documento ipotetico che risponda alla domanda dell'utente.

STILE RICHIESTO:
- Stile burocratico/amministrativo italiano
- Linguaggio formale e tecnico
- Riferimenti normativi (Leggi, Decreti, Circolari)
- Struttura tipica dei documenti ufficiali

REQUISITI:
- Lunghezza: 150-250 parole
- Includi riferimenti a leggi, decreti, articoli specifici
- Usa formule come "Ai sensi dell'art.", "In conformità al D.Lgs.", "La circolare n. X prevede"
- Menziona enti (Agenzia delle Entrate, INPS, INAIL) quando pertinente

FORMATO:
Scrivi SOLO il documento ipotetico, senza introduzioni o commenti.
Il documento deve sembrare un estratto di una risposta ufficiale o di una circolare."""

HYDE_USER_PROMPT_TEMPLATE = """Genera un documento ipotetico (150-250 parole) in stile burocratico italiano che risponda a questa domanda:

Domanda: {query}

Documento ipotetico:"""


class HyDEGeneratorService:
    """Service for generating hypothetical documents for improved retrieval.

    HyDE (Hypothetical Document Embeddings) generates a hypothetical answer
    document whose embedding is closer to real documents than the query
    embedding. This improves vector search recall.

    Example:
        config = get_model_config()
        service = HyDEGeneratorService(config=config)

        result = await service.generate(
            query="Come funziona il ravvedimento operoso?",
            routing=RoutingCategory.TECHNICAL_RESEARCH,
        )
        print(result.hypothetical_document)
    """

    def __init__(self, config: LLMModelConfig):
        """Initialize the HyDE generator service.

        Args:
            config: LLM model configuration for accessing model settings

        DEV-251 Phase 5b: Uses HyDE-specific model (Claude Haiku) instead of
        BASIC tier to reduce latency from ~20s to ~3-5s. Falls back to BASIC
        tier if HYDE_PROVIDER/HYDE_MODEL not configured.
        """
        from app.core.config import HYDE_MODEL, HYDE_PROVIDER

        self._config = config

        # DEV-251 Phase 5b: Use HyDE-specific model (Haiku) instead of BASIC tier
        # This reduces HyDE latency from ~20s (GPT-4o-mini) to ~3-5s (Haiku)
        self._provider = HYDE_PROVIDER or config.get_provider(ModelTier.BASIC)
        self._model = HYDE_MODEL or config.get_model(ModelTier.BASIC)

        self._timeout_ms = config.get_timeout(ModelTier.BASIC)
        self._temperature = config.get_temperature(ModelTier.BASIC)

    def should_generate(self, routing: RoutingCategory) -> bool:
        """Check if HyDE should be generated for this routing category.

        HyDE is skipped for chitchat and calculator queries as they don't
        benefit from document retrieval.

        Args:
            routing: The routing category from the router

        Returns:
            True if HyDE should be generated, False otherwise
        """
        return routing not in SKIP_HYDE_CATEGORIES

    async def generate(
        self,
        query: str,
        routing: RoutingCategory,
        conversation_history: list[dict] | None = None,
    ) -> HyDEResult:
        """Generate a hypothetical document for the query.

        Uses GPT-4o-mini to generate a 150-250 word document in Italian
        bureaucratic style. Skips generation for chitchat and calculator.

        DEV-235: Now supports conversation awareness:
        - Checks query ambiguity using QueryAmbiguityDetector
        - Generates multi-variant HyDE for ambiguous queries
        - Uses conversational prompt when history is provided

        DEV-251 Phase 5: Added Redis caching:
        - Checks cache first before making LLM call
        - Stores results in cache with 24h TTL
        - Cache key: hyde:{routing_category}:{query_hash}

        Args:
            query: User's query
            routing: Routing category from router
            conversation_history: Optional conversation history for context
                Format: [{"role": "user"|"assistant", "content": str}, ...]

        Returns:
            HyDEResult with document or skip information
        """
        # Check if we should skip
        if not self.should_generate(routing):
            skip_reason = routing.value
            logger.info(
                "hyde_skipped",
                reason=skip_reason,
                query_length=len(query),
            )
            return HyDEResult(
                hypothetical_document="",
                word_count=0,
                skipped=True,
                skip_reason=skip_reason,
            )

        # DEV-251 Phase 5: Check cache first
        query_hash = hashlib.md5(query.encode()).hexdigest()
        try:
            cached = await cache_service.get_cached_hyde_document(
                query_hash=query_hash,
                routing_category=routing.value,
            )
            if cached:
                logger.info(
                    "hyde_cache_hit",
                    query_hash=query_hash[:12],
                    routing_category=routing.value,
                )
                return HyDEResult(**cached)
        except Exception as e:
            logger.warning(
                "hyde_cache_lookup_failed",
                error=str(e),
                query_hash=query_hash[:12],
            )
            # Continue with generation if cache fails

        try:
            # DEV-235: Check query ambiguity
            ambiguity_result = self._check_ambiguity(query, conversation_history)
            strategy = ambiguity_result.recommended_strategy if ambiguity_result else "standard"

            # DEV-235: Generate based on strategy
            if strategy == "multi_variant":
                result = await self._generate_multi_variant(query, conversation_history, ambiguity_result)
            elif strategy == "conversational" and conversation_history:
                result = await self._generate_conversational(query, conversation_history)
            else:
                result = await self._generate_standard(query)

            # DEV-251 Phase 5: Store result in cache
            if not result.skipped:
                try:
                    await cache_service.cache_hyde_document(
                        query_hash=query_hash,
                        routing_category=routing.value,
                        hyde_result=asdict(result),
                    )
                except Exception as e:
                    logger.warning(
                        "hyde_cache_store_failed",
                        error=str(e),
                        query_hash=query_hash[:12],
                    )

            return result

        except TimeoutError:
            logger.warning(
                "hyde_timeout",
                query_length=len(query),
                timeout_ms=self._timeout_ms,
            )
            return HyDEResult(
                hypothetical_document="",
                word_count=0,
                skipped=True,
                skip_reason="timeout",
            )

        except Exception as e:
            logger.error(
                "hyde_error",
                error=str(e),
                query_length=len(query),
            )
            return HyDEResult(
                hypothetical_document="",
                word_count=0,
                skipped=True,
                skip_reason="error",
            )

    def _check_ambiguity(self, query: str, conversation_history: list[dict] | None):
        """Check query ambiguity using QueryAmbiguityDetector.

        Args:
            query: User's query
            conversation_history: Optional conversation history

        Returns:
            AmbiguityResult or None on error
        """
        try:
            detector = get_query_ambiguity_detector()
            return detector.detect(query, conversation_history)
        except Exception as e:
            logger.warning(
                "ambiguity_detection_failed",
                error=str(e),
                query_length=len(query),
            )
            return None

    async def _generate_standard(self, query: str) -> HyDEResult:
        """Generate standard single HyDE document.

        Args:
            query: User's query

        Returns:
            HyDEResult with single document
        """
        prompt = self._build_prompt(query)
        timeout_seconds = self._timeout_ms / 1000

        result = await asyncio.wait_for(
            self._call_llm(prompt),
            timeout=timeout_seconds,
        )

        logger.info(
            "hyde_generated",
            strategy="standard",
            model=self._model,
            provider=self._provider,
            query_length=len(query),
            doc_length=len(result.hypothetical_document),
            word_count=result.word_count,
        )

        return result

    async def _generate_conversational(self, query: str, conversation_history: list[dict]) -> HyDEResult:
        """Generate HyDE document using conversational context.

        Args:
            query: User's query
            conversation_history: Conversation history for context

        Returns:
            HyDEResult with contextual document
        """
        # Format conversation history
        history_text = self._format_conversation_history(conversation_history)

        # Load conversational prompt
        loader = get_prompt_loader()
        prompt = loader.load(
            "hyde_conversational",
            conversation_history=history_text,
            current_query=query,
        )

        timeout_seconds = self._timeout_ms / 1000
        result = await asyncio.wait_for(
            self._call_llm_with_prompt(prompt),
            timeout=timeout_seconds,
        )

        logger.info(
            "hyde_generated",
            strategy="conversational",
            model=self._model,
            provider=self._provider,
            query_length=len(query),
            history_turns=len(conversation_history) // 2,
            doc_length=len(result.hypothetical_document),
            word_count=result.word_count,
        )

        return result

    async def _generate_multi_variant(
        self,
        query: str,
        conversation_history: list[dict] | None,
        ambiguity_result,
    ) -> HyDEResult:
        """Generate multiple HyDE document variants for ambiguous queries.

        Args:
            query: User's query
            conversation_history: Optional conversation history
            ambiguity_result: Ambiguity detection result

        Returns:
            HyDEResult with variants list
        """
        # Determine number of variants based on ambiguity score
        num_variants = 3 if ambiguity_result and ambiguity_result.score >= 0.7 else 2

        variants: list[HyDEResult] = []
        timeout_seconds = self._timeout_ms / 1000

        # Generate variants with different interpretation angles
        variant_prompts = self._build_variant_prompts(query, conversation_history, num_variants)

        for i, prompt in enumerate(variant_prompts):
            try:
                result = await asyncio.wait_for(
                    self._call_llm_with_prompt(prompt),
                    timeout=timeout_seconds,
                )
                variants.append(result)
            except Exception as e:
                logger.warning(
                    "hyde_variant_failed",
                    variant_index=i,
                    error=str(e),
                )
                continue

        # Use first variant as main document
        main_doc = (
            variants[0]
            if variants
            else HyDEResult(
                hypothetical_document="",
                word_count=0,
                skipped=True,
                skip_reason="all_variants_failed",
            )
        )

        logger.info(
            "hyde_generated",
            strategy="multi_variant",
            model=self._model,
            provider=self._provider,
            query_length=len(query),
            num_variants=len(variants),
            doc_length=len(main_doc.hypothetical_document),
        )

        return HyDEResult(
            hypothetical_document=main_doc.hypothetical_document,
            word_count=main_doc.word_count,
            skipped=main_doc.skipped,
            skip_reason=main_doc.skip_reason,
            variants=variants if len(variants) > 1 else None,
        )

    def _build_variant_prompts(
        self,
        query: str,
        conversation_history: list[dict] | None,
        num_variants: int,
    ) -> list[str]:
        """Build prompts for multi-variant generation.

        Args:
            query: User's query
            conversation_history: Optional conversation history
            num_variants: Number of variants to generate

        Returns:
            List of prompts for variant generation
        """
        # Define interpretation angles for variants
        angles = [
            "definizione e concetti base",
            "procedure e scadenze",
            "calcolo e importi",
            "sanzioni e ravvedimento",
        ]

        prompts = []
        history_text = self._format_conversation_history(conversation_history)

        for i in range(min(num_variants, len(angles))):
            angle = angles[i]
            prompt = f"""Genera un documento ipotetico (150-250 parole) in stile burocratico italiano che risponda a questa domanda:

Domanda: {query}

Contesto conversazione: {history_text}

FOCUS SPECIFICO: Concentrati sull'aspetto di "{angle}" della domanda.

Documento ipotetico:"""
            prompts.append(prompt)

        return prompts

    def _format_conversation_history(
        self,
        history: list[dict] | None,
        max_turns: int = 3,
    ) -> str:
        """Format last N conversation turns for prompt injection.

        Args:
            history: Full conversation history
            max_turns: Maximum turns to include (default 3)

        Returns:
            Formatted string of recent conversation
        """
        if not history:
            return "Nessun contesto conversazionale disponibile."

        # Get last N turns (each turn = user + assistant = 2 messages)
        max_messages = max_turns * 2
        recent_history = history[-max_messages:] if len(history) > max_messages else history

        formatted_lines = []
        for msg in recent_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            role_label = "Utente" if role == "user" else "Assistente"
            formatted_lines.append(f"{role_label}: {content}")

        return "\n".join(formatted_lines)

    async def _call_llm_with_prompt(self, prompt: str) -> HyDEResult:
        """Call the LLM with a custom prompt.

        Args:
            prompt: The full prompt to send

        Returns:
            Parsed HyDEResult

        Raises:
            Exception: On LLM API errors
        """
        from app.core.llm.factory import get_llm_factory

        factory = get_llm_factory()

        try:
            # DEV-251 Phase 5b: Log which model is being used for HyDE
            logger.info(
                "hyde_llm_call_start",
                provider=self._provider,
                model=self._model,
                prompt_length=len(prompt),
            )

            provider = factory.create_provider(
                provider_type=self._provider,
                model=self._model,
            )

            # Create messages for the LLM
            messages = [
                Message(role="system", content=HYDE_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ]

            response = await provider.chat_completion(
                messages=messages,
                temperature=self._temperature,
                max_tokens=500,
            )

            return self._parse_response(response.content)

        except Exception as e:
            logger.error(
                "hyde_call_failed",
                error=str(e),
                provider=self._provider,
                model=self._model,
            )
            raise

    def _build_prompt(self, query: str) -> str:
        """Build the HyDE generation prompt.

        Args:
            query: User's query

        Returns:
            Formatted prompt string
        """
        return HYDE_USER_PROMPT_TEMPLATE.format(query=query)

    async def _call_llm(self, prompt: str) -> HyDEResult:
        """Call the LLM and parse the response.

        Args:
            prompt: The formatted prompt

        Returns:
            Parsed HyDEResult

        Raises:
            Exception: On LLM API errors
        """
        from app.core.llm.factory import get_llm_factory

        factory = get_llm_factory()

        try:
            # DEV-251 Phase 5b: Log which model is being used for HyDE
            logger.info(
                "hyde_llm_call_start",
                provider=self._provider,
                model=self._model,
                prompt_length=len(prompt),
            )

            provider = factory.create_provider(
                provider_type=self._provider,
                model=self._model,
            )

            # Create messages for the LLM
            messages = [
                Message(role="system", content=HYDE_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ]

            response = await provider.chat_completion(
                messages=messages,
                temperature=self._temperature,
                max_tokens=500,
            )

            return self._parse_response(response.content)

        except Exception as e:
            logger.error(
                "hyde_call_failed",
                error=str(e),
                provider=self._provider,
                model=self._model,
            )
            raise

    def _parse_response(self, response: str) -> HyDEResult:
        """Parse the LLM response into a HyDEResult.

        Args:
            response: Raw LLM response string

        Returns:
            Parsed HyDEResult with word count
        """
        # Clean up the response
        document = response.strip()

        # Count words (split on whitespace)
        words = document.split()
        word_count = len(words)

        return HyDEResult(
            hypothetical_document=document,
            word_count=word_count,
            skipped=False,
            skip_reason=None,
        )
