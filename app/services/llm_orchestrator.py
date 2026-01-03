"""LLMOrchestrator Service for Multi-Model Routing.

DEV-221: Implements intelligent complexity-based routing to select
appropriate LLM models (GPT-4o-mini vs GPT-4o) based on query complexity.

Features:
- Query complexity classification (SIMPLE, COMPLEX, MULTI_DOMAIN)
- Cost-optimized model selection
- Per-session cost tracking
- Reasoning type selection (CoT vs ToT)

Usage:
    from app.services.llm_orchestrator import get_llm_orchestrator

    orchestrator = get_llm_orchestrator()
    complexity = await orchestrator.classify_complexity(query, context)
    response = await orchestrator.generate_response(query, kb_context, [], complexity)
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.logging import logger
from app.schemas.chat import Message
from app.services.prompt_loader import PromptLoader, get_prompt_loader

# =============================================================================
# Enums and Constants
# =============================================================================


class QueryComplexity(str, Enum):
    """Query complexity levels for model routing.

    SIMPLE: Direct questions, definitions, standard rates/deadlines
    COMPLEX: Multi-step reasoning, specific cases, conflicting regulations
    MULTI_DOMAIN: Cross-domain queries spanning fiscal/labor/legal
    """

    SIMPLE = "simple"
    COMPLEX = "complex"
    MULTI_DOMAIN = "multi_domain"

    def __str__(self) -> str:
        """Return the value as string for compatibility."""
        return self.value


# =============================================================================
# Model Configuration
# =============================================================================


@dataclass
class ModelConfig:
    """Configuration for a specific complexity level.

    Contains model selection, parameters, and cost information.
    """

    model: str
    temperature: float
    max_tokens: int
    cost_input_per_1k: float
    cost_output_per_1k: float
    prompt_template: str
    reasoning_type: str
    timeout_seconds: int

    @classmethod
    def for_complexity(cls, complexity: QueryComplexity) -> "ModelConfig":
        """Get the model configuration for a given complexity level.

        Args:
            complexity: The query complexity level

        Returns:
            ModelConfig for the specified complexity
        """
        configs = {
            QueryComplexity.SIMPLE: cls(
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=1500,
                cost_input_per_1k=0.00015,
                cost_output_per_1k=0.0006,
                prompt_template="unified_response_simple",
                reasoning_type="cot",
                timeout_seconds=30,
            ),
            QueryComplexity.COMPLEX: cls(
                model="gpt-4o",
                temperature=0.4,
                max_tokens=2500,
                cost_input_per_1k=0.005,
                cost_output_per_1k=0.015,
                prompt_template="tree_of_thoughts",
                reasoning_type="tot",
                timeout_seconds=45,
            ),
            QueryComplexity.MULTI_DOMAIN: cls(
                model="gpt-4o",
                temperature=0.5,
                max_tokens=3500,
                cost_input_per_1k=0.005,
                cost_output_per_1k=0.015,
                prompt_template="tree_of_thoughts_multi_domain",
                reasoning_type="tot_multi_domain",
                timeout_seconds=60,
            ),
        }
        return configs[complexity]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ComplexityContext:
    """Context information for complexity classification.

    Attributes:
        domains: List of detected domains (fiscale, lavoro, legale)
        has_history: Whether conversation history is present
        has_documents: Whether user documents are attached
    """

    domains: list[str]
    has_history: bool = False
    has_documents: bool = False


@dataclass
class UnifiedResponse:
    """Unified response from LLM with metadata.

    Contains the structured response, reasoning traces,
    cost tracking, and performance metrics.
    """

    reasoning: dict
    reasoning_type: str
    tot_analysis: dict | None
    answer: str
    sources_cited: list[dict]
    suggested_actions: list[dict]
    model_used: str
    tokens_input: int
    tokens_output: int
    cost_euros: float
    latency_ms: int


@dataclass
class SessionCosts:
    """Tracks costs for a session.

    Accumulates costs across queries with breakdown by complexity.
    """

    total_cost_euros: float = 0.0
    total_queries: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    by_complexity: dict = field(
        default_factory=lambda: {
            "simple": {"count": 0, "cost": 0.0},
            "complex": {"count": 0, "cost": 0.0},
            "multi_domain": {"count": 0, "cost": 0.0},
        }
    )


# =============================================================================
# LLM Orchestrator Service
# =============================================================================


class LLMOrchestrator:
    """Orchestrates LLM calls with complexity-based routing.

    Provides intelligent model selection based on query complexity,
    cost tracking, and reasoning type selection.

    Example:
        orchestrator = LLMOrchestrator()
        complexity = await orchestrator.classify_complexity(query, context)
        response = await orchestrator.generate_response(
            query=query,
            kb_context=context,
            kb_sources_metadata=[],
            complexity=complexity,
        )
    """

    def __init__(self, prompt_loader: PromptLoader | None = None):
        """Initialize the LLM Orchestrator.

        Args:
            prompt_loader: Optional PromptLoader instance. Uses default if None.
        """
        self.prompt_loader = prompt_loader or get_prompt_loader()
        self._session_costs = SessionCosts()
        self._llm_client = None  # Lazy initialization

        logger.debug("llm_orchestrator_initialized")

    async def classify_complexity(
        self,
        query: str,
        context: ComplexityContext,
    ) -> QueryComplexity:
        """Classify query complexity using GPT-4o-mini.

        Uses the complexity_classifier prompt to determine the appropriate
        complexity level for model routing.

        Args:
            query: The user's query to classify
            context: Context including domains, history, documents

        Returns:
            QueryComplexity enum value

        Note:
            Defaults to SIMPLE on any error for cost optimization.
        """
        try:
            # Load classification prompt
            prompt = self.prompt_loader.load(
                "complexity_classifier",
                query=query,
                domains=", ".join(context.domains) if context.domains else "non specificato",
                has_history="Sì" if context.has_history else "No",
                has_documents="Sì" if context.has_documents else "No",
            )

            # Call LLM for classification
            response_text, tokens_in, tokens_out = await self._call_llm(
                prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.1,
                max_tokens=200,
            )

            # Parse response
            result = self._parse_classification_response(response_text)

            logger.info(
                "complexity_classified",
                query_length=len(query),
                complexity=result.value,
                domains=context.domains,
            )

            return result

        except Exception as e:
            logger.warning(
                "complexity_classification_failed_defaulting_to_simple",
                error=str(e),
                error_type=type(e).__name__,
            )
            return QueryComplexity.SIMPLE

    async def generate_response(
        self,
        query: str,
        kb_context: str,
        kb_sources_metadata: list[dict],
        complexity: QueryComplexity,
        conversation_history: list[dict] | None = None,
    ) -> UnifiedResponse:
        """Generate response with appropriate model and reasoning strategy.

        Selects model and prompt template based on complexity, tracks costs,
        and returns a structured UnifiedResponse.

        Args:
            query: User's query
            kb_context: Knowledge base context
            kb_sources_metadata: Metadata for KB sources
            complexity: Pre-determined complexity level
            conversation_history: Optional conversation history

        Returns:
            UnifiedResponse with answer, reasoning, sources, actions, and metrics
        """
        start_time = time.perf_counter()
        config = ModelConfig.for_complexity(complexity)

        try:
            # Build prompt based on complexity/reasoning type
            prompt = self._build_response_prompt(
                query=query,
                kb_context=kb_context,
                kb_sources_metadata=kb_sources_metadata,
                config=config,
                conversation_history=conversation_history,
            )

            # Call LLM
            response_text, tokens_input, tokens_output = await self._call_llm(
                prompt=prompt,
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

            # Calculate latency and cost
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            cost_euros = self._calculate_cost(tokens_input, tokens_output, config)

            # Parse response
            parsed = self._parse_unified_response(response_text, config)

            # Build response
            response = UnifiedResponse(
                reasoning=parsed.get("reasoning", {}),
                reasoning_type=config.reasoning_type,
                tot_analysis=parsed.get("tot_analysis"),
                answer=parsed.get("answer", ""),
                sources_cited=parsed.get("sources_cited", []),
                suggested_actions=parsed.get("suggested_actions", []),
                model_used=config.model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_euros=cost_euros,
                latency_ms=latency_ms,
            )

            # Track session costs
            self._track_costs(complexity, cost_euros, tokens_input, tokens_output)

            logger.info(
                "llm_response_generated",
                complexity=complexity.value,
                model=config.model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_euros=cost_euros,
                latency_ms=latency_ms,
            )

            return response

        except Exception as e:
            logger.error(
                "llm_response_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
                complexity=complexity.value,
            )
            raise

    def get_session_costs(self) -> dict:
        """Get detailed cost breakdown for current session.

        Returns:
            Dictionary with total costs, query count, and breakdown by complexity
        """
        return {
            "total_cost_euros": self._session_costs.total_cost_euros,
            "total_queries": self._session_costs.total_queries,
            "total_tokens_input": self._session_costs.total_tokens_input,
            "total_tokens_output": self._session_costs.total_tokens_output,
            "by_complexity": self._session_costs.by_complexity,
        }

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _call_llm(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, int, int]:
        """Make an LLM call and return response with token counts.

        Args:
            prompt: The prompt to send
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Tuple of (response_text, tokens_input, tokens_output)
        """
        # Import here to avoid circular imports
        from app.core.llm.base import LLMProviderType
        from app.core.llm.factory import get_llm_factory

        factory = get_llm_factory()

        # Determine provider based on model
        provider_type = LLMProviderType.OPENAI if "gpt" in model else LLMProviderType.ANTHROPIC

        provider = factory.create_provider(
            provider_type=provider_type,
            model=model,
        )

        # Build messages using Message schema
        messages = [Message(role="user", content=prompt)]

        # Make the call
        response = await provider.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Handle optional tokens_used with sensible defaults
        tokens_total = response.tokens_used or 0
        tokens_output = tokens_total // 3  # Rough estimate: output is ~1/3 of total

        return (
            response.content,
            tokens_total,
            tokens_output,
        )

    def _build_response_prompt(
        self,
        query: str,
        kb_context: str,
        kb_sources_metadata: list[dict],
        config: ModelConfig,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """Build the response prompt based on configuration.

        Args:
            query: User query
            kb_context: KB context string
            kb_sources_metadata: Source metadata for grounding
            config: Model configuration with template name
            conversation_history: Optional conversation history

        Returns:
            Formatted prompt string
        """
        import datetime

        try:
            # Try to load the template
            prompt = self.prompt_loader.load(
                config.prompt_template,
                query=query,
                kb_context=kb_context or "Nessun contesto disponibile.",
                kb_sources_metadata=json.dumps(kb_sources_metadata, ensure_ascii=False),
                conversation_context=self._format_conversation(conversation_history),
                current_date=datetime.date.today().isoformat(),
            )
            return prompt
        except FileNotFoundError:
            # Fallback to basic prompt if template not found
            logger.warning(
                "prompt_template_not_found_using_fallback",
                template=config.prompt_template,
            )
            return self._build_fallback_prompt(query, kb_context)

    def _build_fallback_prompt(self, query: str, kb_context: str) -> str:
        """Build a fallback prompt when template is not available.

        Args:
            query: User query
            kb_context: KB context

        Returns:
            Basic prompt string
        """
        return f"""Sei PratikoAI, assistente esperto in normativa fiscale, del lavoro e legale italiana.

## Contesto
{kb_context}

## Domanda
{query}

## Istruzioni
Rispondi in modo professionale e accurato. Cita sempre le fonti normative.

Fornisci la risposta in formato JSON:
{{
  "reasoning": {{"tema": "...", "fonti": [...], "conclusione": "..."}},
  "answer": "La tua risposta qui",
  "sources_cited": [{{"ref": "...", "relevance": "principale"}}],
  "suggested_actions": []
}}
"""

    def _format_conversation(self, history: list[dict] | None) -> str:
        """Format conversation history for prompt inclusion.

        Args:
            history: List of conversation turns

        Returns:
            Formatted string or "Nessuna conversazione precedente"
        """
        if not history:
            return "Nessuna conversazione precedente"

        formatted = []
        for turn in history[-3:]:  # Last 3 turns
            role = "Utente" if turn.get("role") == "user" else "Assistente"
            content = turn.get("content", "")[:200]  # Truncate
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)

    def _parse_classification_response(self, response: str) -> QueryComplexity:
        """Parse the classification response from LLM.

        Args:
            response: Raw LLM response

        Returns:
            QueryComplexity enum value
        """
        try:
            # Try to extract JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            complexity_str = data.get("complexity", "simple").lower()

            # Map to enum
            mapping = {
                "simple": QueryComplexity.SIMPLE,
                "complex": QueryComplexity.COMPLEX,
                "multi_domain": QueryComplexity.MULTI_DOMAIN,
            }

            return mapping.get(complexity_str, QueryComplexity.SIMPLE)

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "classification_parse_failed",
                error=str(e),
                response_sample=response[:100],
            )
            return QueryComplexity.SIMPLE

    def _parse_unified_response(self, response: str, config: ModelConfig) -> dict:
        """Parse unified response from LLM.

        Args:
            response: Raw LLM response
            config: Model configuration

        Returns:
            Parsed dictionary with response fields
        """
        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            # Ensure required fields with defaults
            return {
                "reasoning": data.get("reasoning", {}),
                "tot_analysis": data.get("tot_analysis"),
                "answer": data.get("answer", response),  # Fallback to raw response
                "sources_cited": data.get("sources_cited", []),
                "suggested_actions": data.get("suggested_actions", []),
            }

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "response_parse_failed_using_raw",
                error=str(e),
                response_length=len(response),
            )
            # Return raw response as answer
            return {
                "reasoning": {},
                "tot_analysis": None,
                "answer": response,
                "sources_cited": [],
                "suggested_actions": [],
            }

    def _extract_json(self, text: str) -> str:
        """Extract JSON from text that may contain markdown code blocks.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string
        """
        import re

        # Try to find JSON in markdown code block
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()

        # Try to find raw JSON object
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json_match.group(0)

        return text

    def _calculate_cost(
        self,
        tokens_input: int,
        tokens_output: int,
        config: ModelConfig,
    ) -> float:
        """Calculate cost in euros for the LLM call.

        Args:
            tokens_input: Input token count
            tokens_output: Output token count
            config: Model configuration with cost info

        Returns:
            Cost in euros
        """
        input_cost = (tokens_input / 1000) * config.cost_input_per_1k
        output_cost = (tokens_output / 1000) * config.cost_output_per_1k
        return input_cost + output_cost

    def _track_costs(
        self,
        complexity: QueryComplexity,
        cost: float,
        tokens_input: int,
        tokens_output: int,
    ) -> None:
        """Track costs for the session.

        Args:
            complexity: Query complexity
            cost: Cost in euros
            tokens_input: Input tokens
            tokens_output: Output tokens
        """
        self._session_costs.total_cost_euros += cost
        self._session_costs.total_queries += 1
        self._session_costs.total_tokens_input += tokens_input
        self._session_costs.total_tokens_output += tokens_output

        complexity_key = str(complexity)
        self._session_costs.by_complexity[complexity_key]["count"] += 1
        self._session_costs.by_complexity[complexity_key]["cost"] += cost


# =============================================================================
# Factory Function (Singleton)
# =============================================================================

_orchestrator_instance: LLMOrchestrator | None = None


def get_llm_orchestrator() -> LLMOrchestrator:
    """Get the singleton LLMOrchestrator instance.

    Returns:
        LLMOrchestrator instance
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = LLMOrchestrator()
    return _orchestrator_instance


def reset_orchestrator() -> None:
    """Reset the singleton instance (for testing)."""
    global _orchestrator_instance
    _orchestrator_instance = None
