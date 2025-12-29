"""HyDE Generator Service for DEV-189.

Generates hypothetical documents in Italian bureaucratic style for improved
vector search retrieval. Based on the HyDE (Hypothetical Document Embeddings)
technique from Section 13.6.

Usage:
    from app.services.hyde_generator import HyDEGeneratorService

    service = HyDEGeneratorService(config=get_model_config())
    result = await service.generate(
        query="Come funziona il ravvedimento operoso?",
        routing=RoutingCategory.TECHNICAL_RESEARCH,
    )
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

from app.core.llm.model_config import LLMModelConfig, ModelTier
from app.core.logging import logger
from app.schemas.chat import Message
from app.schemas.router import RoutingCategory


@dataclass
class HyDEResult:
    """Result from HyDE document generation.

    Attributes:
        hypothetical_document: Generated document in Italian bureaucratic style
        word_count: Number of words in the document
        skipped: Whether HyDE was skipped (for chitchat, calculator, or errors)
        skip_reason: Reason for skipping (if applicable)
    """

    hypothetical_document: str
    word_count: int
    skipped: bool
    skip_reason: Optional[str]


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
        """
        self._config = config
        self._model = config.get_model(ModelTier.BASIC)  # Use GPT-4o-mini
        self._provider = config.get_provider(ModelTier.BASIC)
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
    ) -> HyDEResult:
        """Generate a hypothetical document for the query.

        Uses GPT-4o-mini to generate a 150-250 word document in Italian
        bureaucratic style. Skips generation for chitchat and calculator.

        Args:
            query: User's query
            routing: Routing category from router

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

        try:
            # Build the prompt
            prompt = self._build_prompt(query)

            # Call LLM with timeout
            timeout_seconds = self._timeout_ms / 1000
            result = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=timeout_seconds,
            )

            logger.info(
                "hyde_generated",
                query_length=len(query),
                doc_length=len(result.hypothetical_document),
                word_count=result.word_count,
            )

            return result

        except asyncio.TimeoutError:
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
