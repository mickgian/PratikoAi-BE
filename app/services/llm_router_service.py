"""LLM Router Service for DEV-187.

LLM-based semantic routing with Chain-of-Thought prompting.
Replaces regex-based routing with GPT-4o-mini for query classification.

Usage:
    from app.services.llm_router_service import LLMRouterService

    service = LLMRouterService(config=get_model_config())
    decision = await service.route("Qual è l'iter per aprire P.IVA?", history=[])
"""

import asyncio
import json
import re
from typing import Any

from app.core.llm.model_config import LLMModelConfig, ModelTier
from app.core.logging import logger
from app.schemas.chat import Message
from app.schemas.router import ExtractedEntity, RouterDecision, RoutingCategory

# Maximum query length in characters before truncation
MAX_QUERY_LENGTH = 2000

# Router prompt template
ROUTER_SYSTEM_PROMPT = """Sei un router intelligente per un assistente fiscale/legale italiano.
Il tuo compito è classificare le domande degli utenti in una delle seguenti categorie:

CATEGORIE:
1. **chitchat** - Saluti, conversazione casuale, domande non pertinenti
2. **theoretical_definition** - Richieste di definizioni, spiegazioni di concetti
3. **technical_research** - Domande tecniche complesse che richiedono ricerca documentale
4. **calculator** - Richieste di calcoli (tasse, contributi, stipendi)
5. **golden_set** - Riferimenti specifici a leggi, articoli, normative (es. "Legge 104", "Art. 18")

ISTRUZIONI:
1. Analizza la domanda dell'utente
2. Identifica la categoria più appropriata
3. Estrai eventuali entità legali/fiscali menzionate
4. Fornisci un ragionamento breve ma chiaro
5. **DEV-245 FOLLOW-UP DETECTION**: Determina se è una domanda di follow-up

RILEVAMENTO FOLLOW-UP (is_followup):
Imposta "is_followup": true SE la domanda:
- Inizia con congiunzioni di continuazione: "e", "ma", "però", "anche", "invece"
- Usa riferimenti anaforici: "questo", "quello", "lo stesso", "anche per"
- È una domanda breve (<5 parole) che assume contesto precedente
- Chiede chiarimenti o approfondimenti su un argomento già discusso
- Esempi di follow-up: "e l'IRAP?", "si può pagare a rate?", "quali sono i requisiti?"

Imposta "is_followup": false SE la domanda:
- Introduce un argomento completamente nuovo
- È autosufficiente senza contesto precedente
- È la prima domanda della conversazione (nessun contesto)

RISPOSTA in formato JSON:
{
    "route": "<categoria>",
    "confidence": <0.0-1.0>,
    "reasoning": "<spiegazione breve>",
    "entities": [
        {"text": "<testo>", "type": "<legge|articolo|ente|data>", "confidence": <0.0-1.0>}
    ],
    "requires_freshness": <true|false>,
    "suggested_sources": ["<fonte1>", "<fonte2>"],
    "is_followup": <true|false>
}

Rispondi SOLO con il JSON, senza testo aggiuntivo."""

ROUTER_USER_PROMPT_TEMPLATE = """Classifica questa domanda:

{history_context}
Domanda: {query}

Rispondi con il JSON di routing."""


class LLMRouterService:
    """LLM-based semantic router using Chain-of-Thought prompting.

    This service classifies user queries into routing categories using
    GPT-4o-mini with structured JSON output. It provides fallback behavior
    for error cases and extracts entities from queries.

    Example:
        config = get_model_config()
        service = LLMRouterService(config=config)

        decision = await service.route(
            query="Qual è l'iter per aprire P.IVA forfettaria?",
            history=[]
        )
        print(decision.route)  # RoutingCategory.TECHNICAL_RESEARCH
    """

    def __init__(self, config: LLMModelConfig):
        """Initialize the LLM router service.

        Args:
            config: LLM model configuration for accessing model settings
        """
        self._config = config
        self._model = config.get_model(ModelTier.BASIC)  # Use GPT-4o-mini
        self._provider = config.get_provider(ModelTier.BASIC)
        self._timeout_ms = config.get_timeout(ModelTier.BASIC)
        self._temperature = config.get_temperature(ModelTier.BASIC)

    async def route(
        self,
        query: str,
        history: list[dict[str, Any]],
    ) -> RouterDecision:
        """Route a user query to the appropriate category.

        Uses GPT-4o-mini with Chain-of-Thought prompting to semantically
        classify the query. Falls back to TECHNICAL_RESEARCH on errors.

        Args:
            query: User's query text
            history: Conversation history (list of message dicts)

        Returns:
            RouterDecision with routing category, confidence, and extracted entities
        """
        # Handle empty/whitespace queries
        if not query or not query.strip():
            return RouterDecision(
                route=RoutingCategory.CHITCHAT,
                confidence=0.3,
                reasoning="Empty or whitespace-only query",
                entities=[],
                requires_freshness=False,
                suggested_sources=[],
                is_followup=False,  # DEV-245: Empty queries are not follow-ups
            )

        try:
            # Build the prompt
            prompt = self._build_prompt(query.strip(), history)

            # Call LLM with timeout
            timeout_seconds = self._timeout_ms / 1000
            decision = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=timeout_seconds,
            )

            logger.info(
                "llm_router_decision",
                route=decision.route.value,
                confidence=decision.confidence,
                entity_count=len(decision.entities),
                query_length=len(query),
                is_followup=decision.is_followup,  # DEV-245
            )

            return decision

        except TimeoutError:
            logger.warning(
                "llm_router_timeout",
                query_length=len(query),
                timeout_ms=self._timeout_ms,
            )
            return self._fallback_decision(query, "LLM timeout")

        except Exception as e:
            logger.error(
                "llm_router_error",
                error=str(e),
                query_length=len(query),
            )
            return self._fallback_decision(query, str(e))

    def _build_prompt(
        self,
        query: str,
        history: list[dict[str, Any]],
    ) -> str:
        """Build the routing prompt with query and history.

        Args:
            query: User's query (already stripped)
            history: Conversation history

        Returns:
            Formatted prompt string
        """
        # Truncate very long queries
        if len(query) > MAX_QUERY_LENGTH:
            query = query[:MAX_QUERY_LENGTH] + "..."

        # Build history context
        history_context = ""
        if history:
            history_lines = []
            for msg in history[-3:]:  # Last 3 messages for context
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if content:
                    # Truncate long history messages
                    if len(content) > 200:
                        content = content[:200] + "..."
                    history_lines.append(f"{role}: {content}")

            if history_lines:
                history_context = "Contesto conversazione:\n" + "\n".join(history_lines) + "\n\n"

        return ROUTER_USER_PROMPT_TEMPLATE.format(
            history_context=history_context,
            query=query,
        )

    async def _call_llm(self, prompt: str) -> RouterDecision:
        """Call the LLM and parse the response.

        Args:
            prompt: The formatted prompt

        Returns:
            Parsed RouterDecision

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
                Message(role="system", content=ROUTER_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ]

            response = await provider.chat_completion(
                messages=messages,
                temperature=self._temperature,
                max_tokens=500,
            )

            return self._parse_response(response.content)

        except ValueError:
            # Re-raise parsing errors
            raise
        except Exception as e:
            logger.error(
                "llm_router_call_failed",
                error=str(e),
                model=self._model,
            )
            raise

    def _parse_response(self, response: str) -> RouterDecision:
        """Parse the LLM response into a RouterDecision.

        Handles JSON responses with optional markdown code block wrappers.

        Args:
            response: Raw LLM response string

        Returns:
            Parsed RouterDecision

        Raises:
            ValueError: If response cannot be parsed
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
                "llm_router_json_parse_error",
                error=str(e),
                response_preview=response[:100],
            )
            raise ValueError(f"Invalid JSON response: {e}")

        # Validate and create RouterDecision
        try:
            # Parse entities
            entities = []
            for entity_data in data.get("entities", []):
                entities.append(
                    ExtractedEntity(
                        text=entity_data["text"],
                        type=entity_data["type"],
                        confidence=entity_data.get("confidence", 0.8),
                    )
                )

            decision = RouterDecision(
                route=RoutingCategory(data["route"]),
                confidence=data.get("confidence", 0.5),
                reasoning=data["reasoning"],
                entities=entities,
                requires_freshness=data.get("requires_freshness", False),
                suggested_sources=data.get("suggested_sources", []),
                is_followup=data.get("is_followup", False),  # DEV-245: Follow-up detection
            )

            return decision

        except (KeyError, ValueError) as e:
            logger.warning(
                "llm_router_validation_error",
                error=str(e),
                data=data,
            )
            raise ValueError(f"Invalid router decision data: {e}")

    def _fallback_decision(
        self,
        query: str,
        error_reason: str,
    ) -> RouterDecision:
        """Create a fallback decision when routing fails.

        Falls back to TECHNICAL_RESEARCH as the safest default,
        ensuring queries get RAG retrieval when uncertain.

        Args:
            query: Original query
            error_reason: Description of the error

        Returns:
            Safe fallback RouterDecision
        """
        return RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.5,
            reasoning=f"Fallback due to error: {error_reason}",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
            is_followup=False,  # DEV-245: Default to not follow-up on error
        )
