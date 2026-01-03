"""ActionRegenerator service for regenerating invalid actions.

DEV-217: Golden Loop implementation that regenerates actions when
ActionValidator rejects too many. Retries up to MAX_ATTEMPTS before
falling back to safe template actions.
"""

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.core.logging import logger
from app.services.action_validator import ActionValidator, BatchValidationResult

if TYPE_CHECKING:
    from app.services.prompt_loader import PromptLoader

# Maximum regeneration attempts before fallback
MAX_ATTEMPTS = 2

# Minimum valid actions to avoid regeneration
MIN_VALID_ACTIONS = 2


@dataclass
class ResponseContext:
    """Context for action regeneration."""

    answer: str
    primary_source: dict  # {ref, relevant_paragraph}
    extracted_values: list[str]  # Numbers, dates, percentages from response
    main_topic: str
    kb_sources: list[dict]


class ActionRegenerator:
    """Regenerates actions when validation fails.

    DEV-217: Implements the Golden Loop pattern:
    1. If validation fails (<2 valid actions), attempt regeneration
    2. Use action_regeneration.md prompt with rejection context
    3. Retry up to MAX_ATTEMPTS times
    4. Fall back to safe template actions if all attempts fail
    """

    def __init__(self, prompt_loader: "PromptLoader", llm_client: Any):
        """Initialize with dependencies.

        Args:
            prompt_loader: PromptLoader for loading action_regeneration.md
            llm_client: LLM client for generating new actions
        """
        self.prompt_loader = prompt_loader
        self.llm_client = llm_client
        self.validator = ActionValidator()

    async def regenerate_if_needed(
        self,
        original_actions: list[dict],
        validation_result: BatchValidationResult,
        response_context: ResponseContext,
    ) -> list[dict]:
        """Attempt to regenerate actions if too many were rejected.

        Args:
            original_actions: Actions from Step 64
            validation_result: Validation results with rejection reasons
            response_context: Contains answer, sources, extracted values

        Returns:
            List of valid actions (regenerated if necessary)
        """
        # If enough valid actions (>=2), return them
        if len(validation_result.validated_actions) >= MIN_VALID_ACTIONS:
            logger.debug(
                "action_regeneration_skipped",
                valid_count=len(validation_result.validated_actions),
                reason="enough_valid_actions",
            )
            return validation_result.validated_actions

        logger.info(
            "action_regeneration_starting",
            valid_count=len(validation_result.validated_actions),
            rejected_count=validation_result.rejected_count,
        )

        # Attempt regeneration up to MAX_ATTEMPTS
        for attempt in range(MAX_ATTEMPTS):
            try:
                regenerated = await self._attempt_regeneration(
                    attempt=attempt,
                    rejection_reasons=validation_result.rejection_log,
                    context=response_context,
                )

                if not regenerated:
                    logger.warning(
                        "action_regeneration_empty",
                        attempt=attempt + 1,
                    )
                    continue

                # Validate regenerated actions
                reval_result = self.validator.validate_batch(
                    regenerated,
                    response_context.answer,
                    response_context.kb_sources,
                )

                if len(reval_result.validated_actions) >= MIN_VALID_ACTIONS:
                    logger.info(
                        "action_regeneration_successful",
                        attempt=attempt + 1,
                        valid_count=len(reval_result.validated_actions),
                    )
                    return reval_result.validated_actions

                logger.info(
                    "action_regeneration_insufficient",
                    attempt=attempt + 1,
                    valid_count=len(reval_result.validated_actions),
                )

            except Exception as e:
                logger.error(
                    "action_regeneration_error",
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                continue

        # Max attempts reached - use safe fallback
        logger.warning(
            "action_regeneration_fallback",
            max_attempts=MAX_ATTEMPTS,
        )
        return self._generate_safe_fallback(response_context)

    async def _attempt_regeneration(
        self,
        attempt: int,
        rejection_reasons: list[tuple[dict, str]],
        context: ResponseContext,
    ) -> list[dict]:
        """Single regeneration attempt with correction prompt.

        Args:
            attempt: Current attempt number (0-indexed)
            rejection_reasons: List of (action, reason) tuples
            context: Response context for grounding

        Returns:
            List of regenerated action dicts
        """
        # Build prompt with rejection context
        rejection_text = self._build_rejection_reasons(rejection_reasons)
        values_text = ", ".join(context.extracted_values) if context.extracted_values else "Nessun valore specifico"

        # Get source info
        source_ref = context.primary_source.get("ref", "Fonte non specificata")
        source_paragraph = context.primary_source.get("relevant_paragraph", "")[:500]

        # Load and populate prompt
        prompt = self.prompt_loader.load(
            "action_regeneration",
            rejection_reasons=rejection_text,
            main_source_ref=source_ref,
            source_paragraph_text=source_paragraph,
            extracted_values=values_text,
        )

        logger.debug(
            "action_regeneration_prompt_built",
            attempt=attempt + 1,
            rejection_count=len(rejection_reasons),
        )

        # Call LLM
        response = await self.llm_client.generate(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        if not content:
            return []

        # Parse JSON response
        return self._parse_regenerated_actions(content)

    def _parse_regenerated_actions(self, content: str) -> list[dict]:
        """Parse regenerated actions from LLM response.

        Args:
            content: LLM response content

        Returns:
            List of action dicts, empty if parsing fails
        """
        if not content:
            return []

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```json\s*\n?(.*?)\n?```", content, re.DOTALL | re.IGNORECASE)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try generic code block
        code_match = re.search(r"```\s*\n?(.*?)\n?```", content, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try raw JSON array
        try:
            parsed = json.loads(content.strip())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        logger.warning(
            "action_regeneration_parse_failed",
            content_preview=content[:200],
        )
        return []

    def _generate_safe_fallback(self, context: ResponseContext) -> list[dict]:
        """Generate minimal safe actions when regeneration fails.

        Args:
            context: Response context for grounding

        Returns:
            List of safe fallback actions (max 3)
        """
        actions = []

        # Topic-based action
        if context.main_topic:
            topic_short = context.main_topic[:20]
            actions.append({
                "id": "fallback_1",
                "label": f"Approfondisci {topic_short}",
                "icon": "search",
                "prompt": f"Dimmi di più su {context.main_topic}",
                "source_basis": "topic_fallback",
            })

        # Calculation action if values present
        if context.extracted_values:
            first_value = context.extracted_values[0]
            actions.append({
                "id": "fallback_2",
                "label": f"Calcolo su {first_value}",
                "icon": "calculator",
                "prompt": f"Esegui un calcolo pratico considerando {first_value}",
                "source_basis": "value_fallback",
            })

        # Generic deadline action (always included)
        actions.append({
            "id": "fallback_3",
            "label": "Verifica scadenze",
            "icon": "calendar",
            "prompt": "Quali sono le scadenze rilevanti per questa situazione?",
            "source_basis": "deadline_fallback",
        })

        return actions[:3]

    def _build_rejection_reasons(self, rejection_log: list[tuple[dict, str]]) -> str:
        """Build rejection reasons text for prompt.

        Args:
            rejection_log: List of (action, reason) tuples

        Returns:
            Formatted rejection reasons as bullet points
        """
        if not rejection_log:
            return "- Nessun motivo specifico fornito"

        reasons = []
        for action, reason in rejection_log:
            label = action.get("label", "Unknown")[:30]
            reasons.append(f"- \"{label}\": {reason}")

        return "\n".join(reasons)

    def _extract_values_from_text(self, text: str) -> list[str]:
        """Extract numeric values from text.

        Args:
            text: Text to extract values from

        Returns:
            List of extracted values (percentages, amounts, dates)
        """
        values = []

        # Percentages (e.g., 22%, 10,5%)
        percentages = re.findall(r"\b\d+(?:[,\.]\d+)?%", text)
        values.extend(percentages)

        # Euro amounts (e.g., €15.000, 5.000 euro)
        euro_amounts = re.findall(r"€\s*[\d.,]+|\b[\d.]+(?:,\d+)?\s*euro\b", text, re.IGNORECASE)
        values.extend(euro_amounts[:5])

        # Dates (e.g., 16/03/2024)
        dates = re.findall(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b", text)
        values.extend(dates[:3])

        return list(dict.fromkeys(values))[:10]  # Deduplicate, max 10


# Singleton instance for convenience
action_regenerator: ActionRegenerator | None = None


def get_action_regenerator(prompt_loader: "PromptLoader", llm_client: Any) -> ActionRegenerator:
    """Get or create ActionRegenerator instance.

    Args:
        prompt_loader: PromptLoader for loading prompts
        llm_client: LLM client for generation

    Returns:
        ActionRegenerator instance
    """
    global action_regenerator
    if action_regenerator is None:
        action_regenerator = ActionRegenerator(prompt_loader, llm_client)
    return action_regenerator
