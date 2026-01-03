"""GoldenLoopController service for iteration control and metrics.

DEV-219: Wraps ActionValidator and ActionRegenerator with:
- Configurable iteration limits
- Exponential backoff strategy
- Prometheus metrics for monitoring
- Structured logging for each iteration
"""

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from prometheus_client import Counter, Gauge, Histogram

from app.core.logging import logger

if TYPE_CHECKING:
    from app.services.action_regenerator import ActionRegenerator, ResponseContext
    from app.services.action_validator import ActionValidator, BatchValidationResult

# =============================================================================
# Prometheus Metrics
# =============================================================================
golden_loop_iterations_total = Counter(
    "golden_loop_iterations_total",
    "Total Golden Loop iterations executed",
    ["success"],
)

golden_loop_regeneration_total = Counter(
    "golden_loop_regeneration_total",
    "Total regeneration triggers",
    [],
)

golden_loop_duration_seconds = Histogram(
    "golden_loop_duration_seconds",
    "Total Golden Loop duration in seconds",
    [],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

golden_loop_final_valid_actions = Gauge(
    "golden_loop_final_valid_actions",
    "Final valid actions count after loop",
    [],
)


# =============================================================================
# Configuration
# =============================================================================
@dataclass
class GoldenLoopConfig:
    """Configuration for Golden Loop iteration control."""

    max_iterations: int = 2
    initial_backoff_ms: int = 100
    backoff_multiplier: float = 2.0
    max_backoff_ms: int = 1000
    min_valid_actions: int = 2


# =============================================================================
# Result
# =============================================================================
@dataclass
class GoldenLoopResult:
    """Result of Golden Loop execution."""

    actions: list[dict]
    iterations_used: int
    total_latency_ms: float
    final_valid_count: int
    regeneration_triggered: bool


# =============================================================================
# Controller
# =============================================================================
class GoldenLoopController:
    """Controls Golden Loop iteration with backoff and metrics.

    DEV-219: Wraps ActionValidator and ActionRegenerator to provide:
    - Iteration control with configurable max attempts
    - Exponential backoff between retries
    - Prometheus metrics for monitoring
    - Structured logging for debugging
    """

    def __init__(
        self,
        validator: "ActionValidator",
        regenerator: "ActionRegenerator",
        config: GoldenLoopConfig | None = None,
    ):
        """Initialize with dependencies.

        Args:
            validator: ActionValidator instance for validation
            regenerator: ActionRegenerator instance for regeneration
            config: Optional configuration (uses defaults if None)
        """
        self.validator = validator
        self.regenerator = regenerator
        self.config = config or GoldenLoopConfig()

    async def execute(
        self,
        actions: list[dict],
        kb_sources: list[dict],
        response_text: str,
    ) -> GoldenLoopResult:
        """Execute Golden Loop with iteration control.

        Args:
            actions: Initial suggested actions from Step 64
            kb_sources: KB sources for validation context
            response_text: LLM response text for context

        Returns:
            GoldenLoopResult with validated/regenerated actions and metrics
        """
        start_time = time.perf_counter()
        iteration = 0
        current_actions = actions
        regeneration_triggered = False
        best_validated: list[dict] = []
        best_valid_count = 0

        logger.debug(
            "golden_loop_start",
            initial_action_count=len(actions),
            max_iterations=self.config.max_iterations,
            min_valid_actions=self.config.min_valid_actions,
        )

        # Handle empty input
        if not actions:
            logger.debug("golden_loop_empty_input")
            result = GoldenLoopResult(
                actions=[],
                iterations_used=1,
                total_latency_ms=(time.perf_counter() - start_time) * 1000,
                final_valid_count=0,
                regeneration_triggered=False,
            )
            self._emit_metrics(result)
            return result

        while iteration < self.config.max_iterations:
            iteration += 1

            # Apply backoff if not first iteration
            if iteration > 1:
                backoff_ms = self._calculate_backoff(iteration - 1)
                if backoff_ms > 0:
                    logger.debug(
                        "golden_loop_backoff",
                        iteration=iteration,
                        backoff_ms=backoff_ms,
                    )
                    await asyncio.sleep(backoff_ms / 1000)

            # Validate current actions
            validation_result = self.validator.validate_batch(
                actions=current_actions,
                response_text=response_text,
                kb_sources=kb_sources,
            )

            valid_count = len(validation_result.validated_actions)

            logger.info(
                "golden_loop_iteration",
                iteration=iteration,
                action_count=len(current_actions),
                valid_count=valid_count,
                rejected_count=validation_result.rejected_count,
                quality_score=validation_result.quality_score,
            )

            # Track best result
            if valid_count > best_valid_count:
                best_valid_count = valid_count
                best_validated = validation_result.validated_actions

            # Check if we have enough valid actions
            if valid_count >= self.config.min_valid_actions:
                logger.debug(
                    "golden_loop_success",
                    iteration=iteration,
                    valid_count=valid_count,
                )
                result = GoldenLoopResult(
                    actions=validation_result.validated_actions,
                    iterations_used=iteration,
                    total_latency_ms=(time.perf_counter() - start_time) * 1000,
                    final_valid_count=valid_count,
                    regeneration_triggered=regeneration_triggered,
                )
                self._emit_metrics(result)
                return result

            # Not enough valid actions - try regeneration if not last iteration
            if iteration < self.config.max_iterations:
                logger.info(
                    "golden_loop_regeneration_triggered",
                    iteration=iteration,
                    valid_count=valid_count,
                    min_required=self.config.min_valid_actions,
                )
                regeneration_triggered = True

                try:
                    # Build response context for regeneration
                    from app.services.action_regenerator import ResponseContext

                    response_context = ResponseContext(
                        answer=response_text[:1000],
                        primary_source=kb_sources[0] if kb_sources else {"ref": "N/A", "relevant_paragraph": ""},
                        extracted_values=[],
                        main_topic="",
                        kb_sources=kb_sources,
                    )

                    regenerated = await self.regenerator.regenerate_if_needed(
                        original_actions=current_actions,
                        validation_result=validation_result,
                        response_context=response_context,
                    )

                    if regenerated:
                        current_actions = regenerated
                        logger.debug(
                            "golden_loop_regenerated",
                            regenerated_count=len(regenerated),
                        )
                    else:
                        # Regeneration returned empty - break loop
                        logger.warning(
                            "golden_loop_regeneration_empty",
                            iteration=iteration,
                        )
                        break

                except Exception as e:
                    logger.error(
                        "golden_loop_regeneration_error",
                        iteration=iteration,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    break

        # Max iterations reached or regeneration failed
        logger.warning(
            "golden_loop_max_iterations",
            iterations_used=iteration,
            best_valid_count=best_valid_count,
        )

        # Return best validated actions or try fallback
        final_actions = best_validated
        if not final_actions and hasattr(self.regenerator, "_generate_safe_fallback"):
            try:
                from app.services.action_regenerator import ResponseContext

                response_context = ResponseContext(
                    answer=response_text[:500],
                    primary_source=kb_sources[0] if kb_sources else {"ref": "N/A", "relevant_paragraph": ""},
                    extracted_values=[],
                    main_topic="",
                    kb_sources=kb_sources,
                )
                final_actions = self.regenerator._generate_safe_fallback(response_context)
            except Exception:
                final_actions = []

        result = GoldenLoopResult(
            actions=final_actions,
            iterations_used=iteration,
            total_latency_ms=(time.perf_counter() - start_time) * 1000,
            final_valid_count=len(final_actions),
            regeneration_triggered=regeneration_triggered,
        )
        self._emit_metrics(result)
        return result

    def _calculate_backoff(self, iteration: int) -> int:
        """Calculate backoff delay for given iteration.

        Args:
            iteration: Current iteration number (1-based for backoff)

        Returns:
            Backoff delay in milliseconds (clamped to valid range)
        """
        if iteration <= 0:
            return 0

        # Calculate exponential backoff
        initial = max(0, self.config.initial_backoff_ms)
        multiplier = max(1.0, self.config.backoff_multiplier)

        backoff = int(initial * (multiplier ** (iteration - 1)))

        # Clamp to max
        max_backoff = max(0, self.config.max_backoff_ms)
        return min(backoff, max_backoff)

    def _emit_metrics(self, result: GoldenLoopResult) -> None:
        """Emit Prometheus metrics for the execution result.

        Args:
            result: GoldenLoopResult with execution data
        """
        try:
            # Increment iteration counter
            success = result.final_valid_count >= self.config.min_valid_actions
            golden_loop_iterations_total.labels(success=str(success).lower()).inc(result.iterations_used)

            # Increment regeneration counter if triggered
            if result.regeneration_triggered:
                golden_loop_regeneration_total.inc()

            # Record duration
            golden_loop_duration_seconds.observe(result.total_latency_ms / 1000)

            # Set gauge for valid actions
            golden_loop_final_valid_actions.set(result.final_valid_count)

        except Exception as e:
            # Non-blocking - log and continue
            logger.warning(
                "golden_loop_metrics_error",
                error=str(e),
                error_type=type(e).__name__,
            )


# =============================================================================
# Factory Function
# =============================================================================
def get_golden_loop_controller(
    validator: "ActionValidator",
    regenerator: "ActionRegenerator",
    config: GoldenLoopConfig | None = None,
) -> GoldenLoopController:
    """Factory function for creating GoldenLoopController.

    Args:
        validator: ActionValidator instance
        regenerator: ActionRegenerator instance
        config: Optional configuration

    Returns:
        Configured GoldenLoopController instance
    """
    return GoldenLoopController(
        validator=validator,
        regenerator=regenerator,
        config=config,
    )
