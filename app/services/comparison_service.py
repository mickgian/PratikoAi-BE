"""Comparison service for multi-model LLM comparison feature (DEV-256)."""

import asyncio
import contextlib
import hashlib
import json
import time
from datetime import datetime, timedelta
from uuid import uuid4

from langfuse import get_client as get_langfuse_client
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.llm.base import LLMProviderType, LLMResponse
from app.core.llm.factory import LLMFactory
from app.core.logging import logger
from app.models.comparison import (
    ComparisonStatus,
    ModelComparisonResponse,
    ModelComparisonSession,
    ModelEloRating,
    PendingComparison,
    UserModelPreference,
)
from app.observability.langfuse_config import (
    _current_observation_id,
    _current_trace_id,
)
from app.schemas.chat import Message
from app.schemas.comparison import (
    AvailableModel,
    ComparisonResponse,
    ComparisonStats,
    ExistingModelResponse,
    ModelRanking,
    ModelResponseInfo,
    PendingComparisonData,
    VoteResponse,
)
from app.services.exchange_rate_service import convert_usd_to_eur, get_eur_to_usd_rate
from app.services.usage_tracker import usage_tracker

# Constants
ELO_K_FACTOR = 32
ELO_MIN = 0
ELO_MAX = 3000
DEFAULT_ELO = 1500.0
MODEL_TIMEOUT_SECONDS = 90  # DEV-256: Increased from 30s to handle large enriched prompts
MAX_MODELS_PER_COMPARISON = 6
MIN_MODELS_PER_COMPARISON = 2
MAX_ERROR_MESSAGE_LENGTH = 1000  # Database column limit


def _truncate_error_message(error: str) -> str:
    """Truncate error message to fit database column limit."""
    if len(error) <= MAX_ERROR_MESSAGE_LENGTH:
        return error
    return error[: MAX_ERROR_MESSAGE_LENGTH - 3] + "..."


def _get_registry():
    """Lazy import to avoid circular dependencies."""
    from app.core.llm.model_registry import get_model_registry

    return get_model_registry()


class ComparisonService:
    """Service for managing multi-model LLM comparisons."""

    def __init__(self):
        """Initialize the comparison service."""
        self._factory = LLMFactory()

    def _parse_model_id(self, model_id: str) -> tuple[str, str]:
        """Parse model_id into (provider, model_name).

        Args:
            model_id: Model ID in format "provider:model_name"

        Returns:
            Tuple of (provider, model_name)

        Raises:
            ValueError: If model_id format is invalid
        """
        if ":" not in model_id:
            raise ValueError(f"Invalid model_id format: {model_id}. Expected 'provider:model_name'")
        parts = model_id.split(":", 1)
        return parts[0], parts[1]

    def _get_model_display_name(self, model_id: str) -> str:
        """Get display name for a model."""
        return _get_registry().get_display_name(model_id)

    @staticmethod
    def _get_user_account_code(user_id: int) -> str | None:
        """Look up user's account_code for Langfuse tracking.

        Uses sync session for a lightweight read-only lookup.
        Returns None on any failure (graceful degradation).
        """
        try:
            from sqlmodel import select as sql_select

            from app.models.database import get_sync_session
            from app.models.user import User

            with get_sync_session() as sync_db:
                stmt = sql_select(User.account_code).where(User.id == user_id)
                return sync_db.exec(stmt).first()
        except Exception:
            return None

    def _hash_query(self, query: str) -> str:
        """Generate SHA256 hash of query for grouping."""
        return hashlib.sha256(query.encode()).hexdigest()

    def get_current_model_id(self) -> str:
        """Get the current production model ID in canonical provider:model format.

        Resolves PRODUCTION_LLM_MODEL via model registry to ensure the returned
        value always has the provider prefix (e.g., "mistral:mistral-large-latest"
        even if the env var is just "mistral-large-latest").

        Returns:
            Model ID in format "provider:model" (e.g., "mistral:mistral-large-latest")
        """
        entry = _get_registry().resolve(settings.PRODUCTION_LLM_MODEL)
        return entry.model_id

    def get_default_comparison_model_ids(self) -> list[str]:
        """Get default models for comparison: current + best from each provider.

        Returns list of model IDs including:
        - Current production model (from PRODUCTION_LLM_MODEL)
        - Best model from each available provider (avoiding duplicates)

        Returns:
            List of model IDs for comparison
        """
        current_model = self.get_current_model_id()

        # Start with current production model
        model_ids = [current_model]

        # Add best models from each available provider (skip if same as current)
        for provider, model_id in _get_registry().get_best_models().items():
            if model_id != current_model:
                model_ids.append(model_id)

        return model_ids

    async def _call_single_model(
        self,
        model_id: str,
        query: str,
        batch_id: str,
        enriched_prompt: str | None = None,
        user_id: int | None = None,
        exchange_rate: float = 1.0,
    ) -> ModelResponseInfo:
        """Call a single model and return response info.

        Args:
            model_id: Model ID (e.g., "openai:gpt-4o")
            query: Query to send (fallback if no enriched_prompt)
            batch_id: Batch ID for tracing
            enriched_prompt: DEV-256: Full prompt with KB context, web results, etc.
            user_id: DEV-257: User ID for usage tracking
            exchange_rate: ADR-026: EUR to USD exchange rate

        Returns:
            ModelResponseInfo with response or error
        """
        provider_name, model_name = self._parse_model_id(model_id)
        comparison_trace_id = f"comparison-{batch_id}-{model_id.replace(':', '-')}"
        start_time = time.time()

        # DEV-256: Initialize Langfuse client for cost tracking
        langfuse_client = None
        try:
            langfuse_client = get_langfuse_client()
        except Exception as lf_err:
            logger.warning(
                "comparison_langfuse_init_error",
                error=str(lf_err),
                model_id=model_id,
            )

        # Execute with or without Langfuse context
        if langfuse_client and settings.LANGFUSE_PUBLIC_KEY:
            # Use context manager pattern - IDs are retrieved from SDK's internal state
            # CRITICAL: start_as_current_span() sets up proper trace context, then
            # get_current_trace_id() retrieves the REAL ID (not None like start_span())
            with langfuse_client.start_as_current_span(
                name=f"comparison-{model_id}",
                metadata={
                    "batch_id": batch_id,
                    "provider": provider_name,
                    "comparison_trace_id": comparison_trace_id,
                },
            ):
                langfuse_trace_id = langfuse_client.get_current_trace_id()
                langfuse_observation_id = langfuse_client.get_current_observation_id()

                # Set user_id on trace for Langfuse UI filtering (DEV-256)
                # Prefer account_code for readable analytics (same as main chat)
                if user_id is not None:
                    account_code = self._get_user_account_code(user_id)
                    langfuse_client.update_current_trace(
                        user_id=account_code or str(user_id),
                    )

                # Set contextvars so provider's _report_langfuse_generation() works
                _current_trace_id.set(langfuse_trace_id)
                _current_observation_id.set(langfuse_observation_id)

                logger.debug(
                    "comparison_langfuse_context_set",
                    model_id=model_id,
                    trace_id=langfuse_trace_id,
                    observation_id=langfuse_observation_id,
                )

                try:
                    result = await self._execute_model_call(
                        model_id=model_id,
                        provider_name=provider_name,
                        model_name=model_name,
                        query=query,
                        enriched_prompt=enriched_prompt,
                        batch_id=batch_id,
                        start_time=start_time,
                        langfuse_trace_id=langfuse_trace_id,
                        comparison_trace_id=comparison_trace_id,
                        langfuse_client=langfuse_client,
                        user_id=user_id,
                        exchange_rate=exchange_rate,
                    )
                    return result
                finally:
                    # Reset contextvars to prevent leakage
                    _current_trace_id.set(None)
                    _current_observation_id.set(None)
                    langfuse_client.flush()
        else:
            # No Langfuse - execute without tracing
            return await self._execute_model_call(
                model_id=model_id,
                provider_name=provider_name,
                model_name=model_name,
                query=query,
                enriched_prompt=enriched_prompt,
                batch_id=batch_id,
                start_time=start_time,
                langfuse_trace_id=None,
                comparison_trace_id=comparison_trace_id,
                langfuse_client=None,
                user_id=user_id,
                exchange_rate=exchange_rate,
            )

    async def _execute_model_call(
        self,
        model_id: str,
        provider_name: str,
        model_name: str,
        query: str,
        enriched_prompt: str | None,
        batch_id: str,
        start_time: float,
        langfuse_trace_id: str | None,
        comparison_trace_id: str,
        langfuse_client,
        user_id: int | None = None,
        exchange_rate: float = 1.0,
    ) -> ModelResponseInfo:
        """Execute the actual model call (extracted for Langfuse context management).

        Args:
            model_id: Full model ID (e.g., "openai:gpt-4o")
            provider_name: Provider name
            model_name: Model name
            query: Query to send (fallback if no enriched_prompt)
            enriched_prompt: Full prompt with KB context
            exchange_rate: ADR-026: EUR to USD exchange rate
            batch_id: Batch ID for tracing
            start_time: Start time for latency calculation
            langfuse_trace_id: Langfuse trace ID if available
            comparison_trace_id: Fallback trace ID
            langfuse_client: Langfuse client for span updates
            user_id: DEV-257: User ID for usage tracking

        Returns:
            ModelResponseInfo with response or error
        """
        try:
            # Create provider
            provider_type = LLMProviderType(provider_name)
            provider = self._factory.create_provider(provider_type, model_name)

            # DEV-256: Use enriched_prompt if available (contains KB context, web results, etc.)
            # This ensures comparison models receive the SAME context as the production model
            prompt_content = enriched_prompt if enriched_prompt else query
            messages = [Message(role="user", content=prompt_content)]

            # Call with timeout
            response = await asyncio.wait_for(
                provider.chat_completion(messages),
                timeout=MODEL_TIMEOUT_SECONDS,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract token info
            input_tokens = None
            output_tokens = None
            if isinstance(response.tokens_used, dict):
                input_tokens = response.tokens_used.get("input")
                output_tokens = response.tokens_used.get("output")
            elif isinstance(response.tokens_used, int):
                output_tokens = response.tokens_used

            # DEV-256: Update current span on success
            # Note: The provider's _report_langfuse_generation() already created a nested
            # generation with cost/tokens, so we just update metadata on the parent span
            if langfuse_client:
                try:
                    langfuse_client.update_current_span(
                        output=response.content[:500] if response.content else "",
                        metadata={
                            "status": "success",
                            "latency_ms": latency_ms,
                            "cost_usd": response.cost_estimate,
                        },
                    )
                except Exception as lf_err:
                    logger.warning("comparison_langfuse_update_error", error=str(lf_err))

            # DEV-257: Track usage in UsageEvent table for cost reporting
            if user_id is not None:
                try:
                    # Create LLMResponse for usage tracker
                    llm_response_for_tracking = LLMResponse(
                        content=response.content,
                        model=model_name,
                        provider=provider_name,
                        tokens_used={"input": input_tokens or 0, "output": output_tokens or 0},
                        cost_estimate=response.cost_estimate,
                    )
                    await usage_tracker.track_llm_usage(
                        user_id=user_id,
                        session_id=f"comparison-{batch_id}",
                        provider=provider_name,
                        model=model_name,
                        llm_response=llm_response_for_tracking,
                        response_time_ms=latency_ms,
                        cache_hit=False,
                    )
                except Exception as track_err:
                    logger.warning(
                        "comparison_usage_tracking_failed",
                        model_id=model_id,
                        error=str(track_err),
                    )

            return ModelResponseInfo(
                model_id=model_id,
                provider=provider_name,
                model_name=model_name,
                response_text=response.content,
                latency_ms=latency_ms,
                cost_usd=response.cost_estimate,  # Now in USD (vendor pricing)
                cost_eur=convert_usd_to_eur(response.cost_estimate, exchange_rate),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                status=ComparisonStatus.SUCCESS.value,
                trace_id=langfuse_trace_id or comparison_trace_id,
            )

        except TimeoutError:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "comparison_model_timeout",
                model_id=model_id,
                batch_id=batch_id,
                latency_ms=latency_ms,
            )
            # DEV-256: Update span with timeout error
            if langfuse_client:
                with contextlib.suppress(Exception):
                    langfuse_client.update_current_span(
                        metadata={
                            "status": "timeout",
                            "error": f"Timeout after {MODEL_TIMEOUT_SECONDS}s",
                        },
                    )
            return ModelResponseInfo(
                model_id=model_id,
                provider=provider_name,
                model_name=model_name,
                response_text="",
                latency_ms=latency_ms,
                cost_eur=None,
                input_tokens=None,
                output_tokens=None,
                status=ComparisonStatus.TIMEOUT.value,
                error_message=f"Request timed out after {MODEL_TIMEOUT_SECONDS}s",
                trace_id=langfuse_trace_id or comparison_trace_id,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "comparison_model_error",
                model_id=model_id,
                batch_id=batch_id,
                error_type=type(e).__name__,
                error_message=_truncate_error_message(str(e)),
            )
            # DEV-256: Update span with error
            if langfuse_client:
                with contextlib.suppress(Exception):
                    langfuse_client.update_current_span(
                        metadata={
                            "status": "error",
                            "error": _truncate_error_message(str(e))[:200],
                        },
                    )
            return ModelResponseInfo(
                model_id=model_id,
                provider=provider_name,
                model_name=model_name,
                response_text="",
                latency_ms=latency_ms,
                cost_eur=None,
                input_tokens=None,
                output_tokens=None,
                status=ComparisonStatus.ERROR.value,
                error_message=_truncate_error_message(str(e)),
                trace_id=langfuse_trace_id or comparison_trace_id,
            )

    async def run_comparison(
        self,
        query: str,
        user_id: int,
        db: AsyncSession,
        model_ids: list[str] | None = None,
        enriched_prompt: str | None = None,
    ) -> ComparisonResponse:
        """Run a multi-model comparison.

        Args:
            query: Query to compare
            user_id: User ID
            db: Database session
            model_ids: Optional list of model IDs to compare
            enriched_prompt: DEV-256: Full prompt with KB context, web results, etc.

        Returns:
            ComparisonResponse with all model responses

        Raises:
            ValueError: If validation fails
        """
        # Validate query
        if not query or not query.strip():
            raise ValueError("La domanda non può essere vuota")
        if len(query) > 2000:
            raise ValueError("La domanda supera il limite di 2000 caratteri")

        # Get model IDs from preferences if not provided
        if model_ids is None:
            model_ids = await self._get_enabled_model_ids(user_id, db)

        # DEV-256: Filter out disabled providers
        model_ids = [m for m in model_ids if m.split(":")[0] not in _get_registry().get_disabled_providers()]

        # Validate model count
        if len(model_ids) < MIN_MODELS_PER_COMPARISON:
            raise ValueError("Seleziona almeno 2 modelli per il confronto")
        if len(model_ids) > MAX_MODELS_PER_COMPARISON:
            raise ValueError("Massimo 6 modelli per confronto")

        # Generate batch ID
        batch_id = str(uuid4())[:8]

        # ADR-026: Fetch exchange rate for USD cost display
        exchange_rate = await get_eur_to_usd_rate()

        logger.info(
            "comparison_started",
            batch_id=batch_id,
            user_id=user_id,
            model_count=len(model_ids),
            has_enriched_prompt=enriched_prompt is not None,
            exchange_rate=exchange_rate,
        )

        # Run all models in parallel
        # DEV-256: Pass enriched_prompt so all models receive same context as production
        # DEV-257: Pass user_id for usage tracking
        # ADR-026: Pass exchange_rate for USD cost calculation
        tasks = [
            self._call_single_model(
                model_id, query, batch_id, enriched_prompt, user_id=user_id, exchange_rate=exchange_rate
            )
            for model_id in model_ids
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses
        response_infos: list[ModelResponseInfo] = []
        for resp in responses:
            if isinstance(resp, BaseException):
                logger.error("comparison_task_exception", error=str(resp))
                continue
            response_infos.append(resp)

        # Check if all models failed
        successful = [r for r in response_infos if r.status == ComparisonStatus.SUCCESS.value]
        if not successful:
            raise ValueError("Tutti i modelli hanno fallito. Riprova più tardi.")

        # Create session in database
        session = ModelComparisonSession(
            batch_id=batch_id,
            user_id=user_id,
            query_text=query,
            query_hash=self._hash_query(query),
            models_compared=json.dumps(model_ids),
        )
        db.add(session)
        await db.flush()

        # Create response records
        for resp in response_infos:
            db_response = ModelComparisonResponse(
                session_id=session.id,
                provider=resp.provider,
                model_name=resp.model_name,
                response_text=resp.response_text,
                trace_id=resp.trace_id,
                latency_ms=resp.latency_ms,
                cost_eur=resp.cost_eur,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                status=resp.status,
                error_message=resp.error_message,
            )
            db.add(db_response)

        await db.commit()

        logger.info(
            "comparison_completed",
            batch_id=batch_id,
            successful_count=len(successful),
            total_count=len(response_infos),
        )

        return ComparisonResponse(
            batch_id=batch_id,
            query=query,
            responses=response_infos,
            created_at=session.created_at,
        )

    async def run_comparison_with_existing(
        self,
        query: str,
        user_id: int,
        db: AsyncSession,
        existing_response: ExistingModelResponse,
        enriched_prompt: str | None = None,
        model_ids: list[str] | None = None,
    ) -> ComparisonResponse:
        """Run comparison reusing an existing response from main chat.

        This method avoids re-calling the current model by reusing the response
        already obtained in the main chat. Only calls the other selected models.

        Args:
            query: Query to compare
            user_id: User ID
            db: Database session
            existing_response: Existing response from main chat to reuse
            enriched_prompt: DEV-256: Full prompt with KB context, web results, etc.
            model_ids: DEV-257: User-selected model IDs from chat. If None, uses default best models.

        Returns:
            ComparisonResponse with all model responses (existing + new)

        Raises:
            ValueError: If validation fails
        """
        # Validate query
        if not query or not query.strip():
            raise ValueError("La domanda non può essere vuota")
        if len(query) > 2000:
            raise ValueError("La domanda supera il limite di 2000 caratteri")

        # DEV-257: Use user-selected models if provided, otherwise use default best models
        current_model_id = existing_response.model_id
        disabled_providers = _get_registry().get_disabled_providers()
        if model_ids:
            # User selected models from chat - filter out current model and disabled providers
            other_model_ids = [
                model_id
                for model_id in model_ids
                if model_id != current_model_id and model_id.split(":")[0] not in disabled_providers
            ]
        else:
            # Default behavior: use best models from each provider
            other_model_ids = [
                model_id
                for model_id in self.get_default_comparison_model_ids()
                if model_id != current_model_id and model_id.split(":")[0] not in disabled_providers
            ]

        # Generate batch ID
        batch_id = str(uuid4())[:8]

        # ADR-026: Fetch exchange rate for USD cost display
        exchange_rate = await get_eur_to_usd_rate()

        logger.info(
            "comparison_with_existing_started",
            batch_id=batch_id,
            user_id=user_id,
            existing_model=current_model_id,
            other_model_count=len(other_model_ids),
            has_enriched_prompt=enriched_prompt is not None,
            exchange_rate=exchange_rate,
        )

        # Convert existing response to ModelResponseInfo
        # Note: existing_response.cost_eur is actually USD now (from provider's cost_estimate)
        # The field name in ExistingModelResponse is still cost_eur for backward compatibility
        # but the value coming from providers is now in USD
        provider, model_name = self._parse_model_id(current_model_id)
        existing_info = ModelResponseInfo(
            model_id=current_model_id,
            provider=provider,
            model_name=model_name,
            response_text=existing_response.response_text,
            latency_ms=existing_response.latency_ms,
            cost_usd=existing_response.cost_eur,  # cost_eur field contains USD (from provider)
            cost_eur=convert_usd_to_eur(existing_response.cost_eur, exchange_rate),
            input_tokens=existing_response.input_tokens,
            output_tokens=existing_response.output_tokens,
            status=ComparisonStatus.SUCCESS.value,
            trace_id=existing_response.trace_id or f"main-chat-{batch_id}",
        )

        # Call only the other models in parallel
        # DEV-256: Pass enriched_prompt so all models receive same context as production
        # DEV-257: Pass user_id for usage tracking
        # ADR-026: Pass exchange_rate for USD cost calculation
        tasks = [
            self._call_single_model(
                model_id, query, batch_id, enriched_prompt, user_id=user_id, exchange_rate=exchange_rate
            )
            for model_id in other_model_ids
        ]
        other_responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine: existing + new responses
        response_infos: list[ModelResponseInfo] = [existing_info]
        for resp in other_responses:
            if isinstance(resp, BaseException):
                logger.error("comparison_task_exception", error=str(resp))
                continue
            response_infos.append(resp)

        # Check we have at least the existing response
        successful = [r for r in response_infos if r.status == ComparisonStatus.SUCCESS.value]
        if len(successful) < MIN_MODELS_PER_COMPARISON:
            raise ValueError("Troppi modelli hanno fallito. Riprova più tardi.")

        # All model IDs for session record
        all_model_ids = [current_model_id] + other_model_ids

        # Create session in database
        session = ModelComparisonSession(
            batch_id=batch_id,
            user_id=user_id,
            query_text=query,
            query_hash=self._hash_query(query),
            models_compared=json.dumps(all_model_ids),
        )
        db.add(session)
        await db.flush()

        # Create response records
        for resp in response_infos:
            db_response = ModelComparisonResponse(
                session_id=session.id,
                provider=resp.provider,
                model_name=resp.model_name,
                response_text=resp.response_text,
                trace_id=resp.trace_id,
                latency_ms=resp.latency_ms,
                cost_eur=resp.cost_eur,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                status=resp.status,
                error_message=resp.error_message,
            )
            db.add(db_response)

        await db.commit()

        logger.info(
            "comparison_with_existing_completed",
            batch_id=batch_id,
            successful_count=len(successful),
            total_count=len(response_infos),
            reused_model=current_model_id,
        )

        return ComparisonResponse(
            batch_id=batch_id,
            query=query,
            responses=response_infos,
            created_at=session.created_at,
        )

    async def submit_vote(
        self,
        batch_id: str,
        winner_model_id: str,
        user_id: int,
        db: AsyncSession,
        comment: str | None = None,
    ) -> VoteResponse:
        """Submit a vote for the best model in a comparison.

        Args:
            batch_id: Batch ID of the comparison
            winner_model_id: Model ID of the winner
            user_id: User ID
            db: Database session
            comment: Optional comment

        Returns:
            VoteResponse with result

        Raises:
            ValueError: If validation fails
        """
        # Find session
        result = await db.execute(
            select(ModelComparisonSession).where(
                ModelComparisonSession.batch_id == batch_id,
                ModelComparisonSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise ValueError("Sessione di confronto non trovata")

        # Check if already voted
        if session.winner_model is not None:
            raise ValueError("Voto già registrato per questa sessione")

        # Validate winner was in comparison
        models_compared = json.loads(session.models_compared)
        if winner_model_id not in models_compared:
            raise ValueError("Modello non valido per questa sessione")

        # Update session with vote
        session.winner_model = winner_model_id
        session.vote_timestamp = datetime.utcnow()
        session.vote_comment = comment

        # Update Elo ratings
        elo_changes = await self._update_elo_ratings(winner_model_id, models_compared, db)

        await db.commit()

        logger.info(
            "vote_submitted",
            batch_id=batch_id,
            winner=winner_model_id,
            user_id=user_id,
        )

        return VoteResponse(
            success=True,
            message="Voto registrato con successo",
            winner_model_id=winner_model_id,
            elo_changes=elo_changes,
        )

    async def _update_elo_ratings(
        self,
        winner_model_id: str,
        all_model_ids: list[str],
        db: AsyncSession,
    ) -> dict[str, float]:
        """Update Elo ratings after a vote.

        Args:
            winner_model_id: Winner model ID
            all_model_ids: All model IDs in comparison
            db: Database session

        Returns:
            Dict of model_id -> rating change
        """
        elo_changes: dict[str, float] = {}

        # Get or create ratings for all models
        ratings: dict[str, ModelEloRating] = {}
        for model_id in all_model_ids:
            provider, model_name = self._parse_model_id(model_id)
            result = await db.execute(
                select(ModelEloRating).where(
                    ModelEloRating.provider == provider,
                    ModelEloRating.model_name == model_name,
                )
            )
            rating = result.scalar_one_or_none()

            if not rating:
                rating = ModelEloRating(
                    provider=provider,
                    model_name=model_name,
                    elo_rating=DEFAULT_ELO,
                )
                db.add(rating)

            ratings[model_id] = rating

        # Calculate Elo changes
        winner_rating = ratings[winner_model_id]
        loser_ids = [m for m in all_model_ids if m != winner_model_id]

        # Winner gains against each loser
        total_gain = 0.0
        for loser_id in loser_ids:
            loser_rating = ratings[loser_id]
            gain, loss = self._calculate_elo_update(
                winner_rating.elo_rating,
                loser_rating.elo_rating,
            )
            total_gain += gain
            elo_changes[loser_id] = -loss

            # Update loser
            loser_rating.elo_rating = max(ELO_MIN, min(ELO_MAX, loser_rating.elo_rating - loss))
            loser_rating.total_comparisons += 1
            loser_rating.last_updated = datetime.utcnow()

        # Distribute total gain (average against all losers)
        avg_gain = total_gain / len(loser_ids) if loser_ids else 0
        elo_changes[winner_model_id] = avg_gain

        # Update winner
        winner_rating.elo_rating = max(ELO_MIN, min(ELO_MAX, winner_rating.elo_rating + avg_gain))
        winner_rating.total_comparisons += 1
        winner_rating.wins += 1
        winner_rating.last_updated = datetime.utcnow()

        return elo_changes

    def _calculate_elo_update(
        self,
        winner_rating: float,
        loser_rating: float,
        k_factor: int = ELO_K_FACTOR,
    ) -> tuple[float, float]:
        """Calculate Elo rating changes after a match.

        Args:
            winner_rating: Winner's current rating
            loser_rating: Loser's current rating
            k_factor: K-factor for calculation

        Returns:
            Tuple of (winner_gain, loser_loss)
        """
        # Expected scores
        expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
        expected_loser = 1 - expected_winner

        # Actual scores (winner=1, loser=0)
        winner_gain = k_factor * (1 - expected_winner)
        loser_loss = k_factor * expected_loser

        return winner_gain, loser_loss

    async def get_available_models(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> list[AvailableModel]:
        """Get all available models with user preferences.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            List of available models with is_best and is_current flags
        """
        models: list[AvailableModel] = []

        # Get best model IDs and current model for flagging
        best_model_ids = set(_get_registry().get_best_models().values())
        current_model_id = self.get_current_model_id()

        # Get all configured providers
        for provider_type in [
            LLMProviderType.OPENAI,
            LLMProviderType.ANTHROPIC,
            LLMProviderType.GEMINI,
            LLMProviderType.MISTRAL,
        ]:
            try:
                provider = self._factory.create_provider(provider_type)
                for model_name in provider.supported_models:
                    model_id = f"{provider_type.value}:{model_name}"

                    # Get Elo rating
                    result = await db.execute(
                        select(ModelEloRating).where(
                            ModelEloRating.provider == provider_type.value,
                            ModelEloRating.model_name == model_name,
                        )
                    )
                    rating = result.scalar_one_or_none()

                    # Get user preference
                    result = await db.execute(
                        select(UserModelPreference).where(
                            UserModelPreference.user_id == user_id,
                            UserModelPreference.provider == provider_type.value,
                            UserModelPreference.model_name == model_name,
                        )
                    )
                    pref = result.scalar_one_or_none()

                    # DEV-256: Check if provider is globally disabled
                    is_provider_disabled = provider_type.value in _get_registry().get_disabled_providers()
                    # User preference only applies if provider is not globally disabled
                    is_enabled = False if is_provider_disabled else (pref.is_enabled if pref else True)

                    models.append(
                        AvailableModel(
                            model_id=model_id,
                            provider=provider_type.value,
                            model_name=model_name,
                            display_name=self._get_model_display_name(model_id),
                            is_enabled=is_enabled,
                            is_best=model_id in best_model_ids,
                            is_current=model_id == current_model_id,
                            elo_rating=rating.elo_rating if rating else None,
                            total_comparisons=rating.total_comparisons if rating else 0,
                            wins=rating.wins if rating else 0,
                            is_disabled=is_provider_disabled,  # DEV-256: Flag for UI to show as disabled
                        )
                    )
            except (ValueError, ImportError):
                # Provider not configured or package not installed
                continue

        return models

    async def _get_enabled_model_ids(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> list[str]:
        """Get enabled model IDs for a user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            List of enabled model IDs
        """
        models = await self.get_available_models(user_id, db)
        return [m.model_id for m in models if m.is_enabled]

    async def update_preferences(
        self,
        user_id: int,
        enabled_model_ids: list[str],
        db: AsyncSession,
    ) -> None:
        """Update user model preferences.

        Args:
            user_id: User ID
            enabled_model_ids: List of model IDs to enable
            db: Database session
        """
        # Get all available models
        all_models = await self.get_available_models(user_id, db)

        for model in all_models:
            provider, model_name = self._parse_model_id(model.model_id)
            is_enabled = model.model_id in enabled_model_ids

            # Find or create preference
            result = await db.execute(
                select(UserModelPreference).where(
                    UserModelPreference.user_id == user_id,
                    UserModelPreference.provider == provider,
                    UserModelPreference.model_name == model_name,
                )
            )
            pref = result.scalar_one_or_none()

            if pref:
                pref.is_enabled = is_enabled
            else:
                pref = UserModelPreference(
                    user_id=user_id,
                    provider=provider,
                    model_name=model_name,
                    is_enabled=is_enabled,
                )
                db.add(pref)

        await db.commit()

    async def get_leaderboard(
        self,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[ModelRanking]:
        """Get model leaderboard sorted by Elo rating.

        Args:
            db: Database session
            limit: Maximum number of results

        Returns:
            List of model rankings
        """
        result = await db.execute(select(ModelEloRating).order_by(ModelEloRating.elo_rating.desc()).limit(limit))  # type: ignore[attr-defined]
        ratings = result.scalars().all()

        rankings = []
        for rank, rating in enumerate(ratings, 1):
            model_id = f"{rating.provider}:{rating.model_name}"
            win_rate = rating.wins / rating.total_comparisons if rating.total_comparisons > 0 else 0.0
            rankings.append(
                ModelRanking(
                    rank=rank,
                    model_id=model_id,
                    provider=rating.provider,
                    model_name=rating.model_name,
                    display_name=self._get_model_display_name(model_id),
                    elo_rating=rating.elo_rating,
                    total_comparisons=rating.total_comparisons,
                    wins=rating.wins,
                    win_rate=win_rate,
                )
            )

        return rankings

    async def get_user_stats(
        self,
        user_id: int,
        db: AsyncSession,
    ) -> ComparisonStats:
        """Get comparison statistics for a user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            User comparison statistics
        """
        # Total comparisons
        result = await db.execute(
            select(func.count(ModelComparisonSession.id)).where(ModelComparisonSession.user_id == user_id)
        )
        total_comparisons = result.scalar() or 0

        # Total votes
        result = await db.execute(
            select(func.count(ModelComparisonSession.id)).where(
                ModelComparisonSession.user_id == user_id,
                ModelComparisonSession.winner_model.isnot(None),  # type: ignore[union-attr]
            )
        )
        total_votes = result.scalar() or 0

        # This week's stats
        week_ago = datetime.utcnow() - timedelta(days=7)

        result = await db.execute(
            select(func.count(ModelComparisonSession.id)).where(
                ModelComparisonSession.user_id == user_id,
                ModelComparisonSession.created_at >= week_ago,
            )
        )
        comparisons_this_week = result.scalar() or 0

        result = await db.execute(
            select(func.count(ModelComparisonSession.id)).where(
                ModelComparisonSession.user_id == user_id,
                ModelComparisonSession.winner_model.isnot(None),  # type: ignore[union-attr]
                ModelComparisonSession.created_at >= week_ago,
            )
        )
        votes_this_week = result.scalar() or 0

        # Favorite model
        result = await db.execute(
            select(
                ModelComparisonSession.winner_model,
                func.count(ModelComparisonSession.id).label("count"),
            )
            .where(
                ModelComparisonSession.user_id == user_id,
                ModelComparisonSession.winner_model.isnot(None),  # type: ignore[union-attr]
            )
            .group_by(ModelComparisonSession.winner_model)
            .order_by(func.count(ModelComparisonSession.id).desc())
            .limit(1)
        )
        fav = result.first()
        favorite_model = fav[0] if fav else None
        favorite_model_vote_count = fav[1] if fav else 0

        return ComparisonStats(
            total_comparisons=total_comparisons,
            total_votes=total_votes,
            comparisons_this_week=comparisons_this_week,
            votes_this_week=votes_this_week,
            favorite_model=favorite_model,
            favorite_model_vote_count=favorite_model_vote_count,
        )

    async def create_pending_comparison(
        self,
        user_id: int,
        query: str,
        response: str,
        model_id: str,
        db: AsyncSession,
        enriched_prompt: str | None = None,
        latency_ms: int | None = None,
        cost_eur: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        trace_id: str | None = None,
    ) -> str:
        """Create a pending comparison record.

        Stores the query and response from main chat so the comparison page
        can retrieve it. Records expire after 1 hour.

        Args:
            user_id: User ID
            query: The user's question
            response: The AI response
            model_id: Model ID that generated the response
            db: Database session
            enriched_prompt: DEV-256: Full prompt with KB context, web results, etc.
            latency_ms: DEV-256: Response latency in milliseconds
            cost_eur: DEV-256: Estimated cost in EUR
            input_tokens: DEV-256: Number of input tokens
            output_tokens: DEV-256: Number of output tokens
            trace_id: DEV-256: Langfuse trace ID

        Returns:
            UUID string of the pending comparison
        """
        # Always use the resolved production model ID (canonical provider:model format)
        # The frontend may send a stale or incorrect model_id
        resolved_model_id = self.get_current_model_id()

        pending = PendingComparison(
            user_id=user_id,
            query=query,
            response=response,
            model_id=resolved_model_id,
            enriched_prompt=enriched_prompt,
            latency_ms=latency_ms,
            cost_eur=cost_eur,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            trace_id=trace_id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(pending)
        await db.commit()
        await db.refresh(pending)

        logger.info(
            "pending_comparison_created",
            pending_id=str(pending.id),
            user_id=user_id,
            model_id=resolved_model_id,
            original_model_id=model_id,
            has_enriched_prompt=enriched_prompt is not None,
            has_metrics=latency_ms is not None,
        )

        return str(pending.id)

    async def get_pending_comparison(
        self,
        pending_id: str,
        user_id: int,
        db: AsyncSession,
    ) -> PendingComparisonData | None:
        """Retrieve and delete a pending comparison.

        Retrieves the pending comparison data and deletes it (one-time use).
        Only the user who created the pending comparison can retrieve it.

        Args:
            pending_id: UUID of the pending comparison
            user_id: User ID (must match creator)
            db: Database session

        Returns:
            PendingComparisonData or None if not found/wrong user
        """
        from uuid import UUID

        try:
            uuid_id = UUID(pending_id)
        except ValueError:
            logger.warning("invalid_pending_id", pending_id=pending_id)
            return None

        result = await db.execute(
            select(PendingComparison).where(
                PendingComparison.id == uuid_id,
                PendingComparison.user_id == user_id,
            )
        )
        pending = result.scalar_one_or_none()

        if not pending:
            logger.warning(
                "pending_comparison_not_found",
                pending_id=pending_id,
                user_id=user_id,
            )
            return None

        # Extract data before deletion
        data = PendingComparisonData(
            query=pending.query,
            response=pending.response,
            model_id=pending.model_id,
            enriched_prompt=pending.enriched_prompt,
            latency_ms=pending.latency_ms,
            cost_eur=pending.cost_eur,
            input_tokens=pending.input_tokens,
            output_tokens=pending.output_tokens,
            trace_id=pending.trace_id,
        )

        # Delete after retrieval (one-time use)
        await db.delete(pending)
        await db.commit()

        logger.info(
            "pending_comparison_retrieved_and_deleted",
            pending_id=pending_id,
            user_id=user_id,
        )

        return data


# Global instance
_comparison_service: ComparisonService | None = None


def get_comparison_service() -> ComparisonService:
    """Get the global comparison service instance."""
    global _comparison_service
    if _comparison_service is None:
        _comparison_service = ComparisonService()
    return _comparison_service
