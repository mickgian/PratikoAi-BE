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

        DEV-242: Fixed to produce grammatically correct Italian labels.
        - Truncates at word boundaries (no mid-word cuts)
        - Uses noun phrases instead of imperative verbs
        - Context-appropriate labels for values (dates vs amounts vs percentages)
        - Avoids double-verb patterns like "Approfondisci Verifica"

        Args:
            context: Response context for grounding

        Returns:
            List of safe fallback actions (max 3)
        """
        actions = []

        # Topic-based action with proper grammar
        if context.main_topic and len(context.main_topic) >= 5:
            # Truncate at word boundary to avoid mid-word cuts
            topic_clean = self._truncate_at_word_boundary(context.main_topic, 25)
            if topic_clean and not self._starts_with_verb(topic_clean):
                actions.append(
                    {
                        "id": "fallback_1",
                        "label": f"Dettagli su {topic_clean}",
                        "icon": "search",
                        "prompt": f"Vorrei maggiori dettagli su {context.main_topic}",
                        "source_basis": "topic_fallback",
                    }
                )

        # Value-based action with context-appropriate label
        if context.extracted_values:
            first_value = context.extracted_values[0]
            action = self._create_value_action(first_value)
            if action:
                actions.append(action)

        # Contextual deadline action (only if we have fewer than 2 actions)
        if len(actions) < 2:
            topic_context = (
                self._truncate_at_word_boundary(context.main_topic, 15) if context.main_topic else "questa pratica"
            )
            actions.append(
                {
                    "id": "fallback_3",
                    "label": "Prossime scadenze fiscali",
                    "icon": "calendar",
                    "prompt": f"Quali sono le scadenze rilevanti per {topic_context}?",
                    "source_basis": "deadline_fallback",
                }
            )

        return self._validate_fallback_grammar(actions[:3])

    def _truncate_at_word_boundary(self, text: str, max_length: int) -> str:
        """Truncate text at word boundary to avoid mid-word cuts.

        DEV-242: Ensures labels don't end with partial words like 'scaden...'

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text at word boundary, or original if short enough
        """
        if not text:
            return ""
        text = text.strip()
        if len(text) <= max_length:
            return text

        # Find last space within max_length
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")

        # If space found in reasonable position, truncate there
        if last_space > max_length // 2:
            result = truncated[:last_space].strip()
            # Also strip trailing punctuation
            return result.rstrip(".,;:-").strip()

        # Otherwise use full truncation but strip trailing punctuation
        return truncated.rstrip(".,;:-").strip()

    def _starts_with_verb(self, text: str) -> bool:
        """Check if text starts with an imperative verb.

        DEV-242: Detects common Italian imperative verbs to avoid
        double-verb patterns like "Dettagli su Verifica le scadenze"

        Args:
            text: Text to check

        Returns:
            True if starts with imperative verb
        """
        imperative_verbs = {
            "verifica",
            "calcola",
            "controlla",
            "consulta",
            "leggi",
            "vedi",
            "scopri",
            "approfondisci",
            "cerca",
            "trova",
            "monitora",
            "segui",
            "chiedi",
            "contatta",
        }
        first_word = text.lower().split()[0] if text else ""
        return first_word in imperative_verbs

    def _create_value_action(self, value: str) -> dict | None:
        """Create contextually appropriate action for extracted value.

        DEV-242: Creates different labels based on value type:
        - Percentages: "Calcolo con aliquota X%"
        - Euro amounts: "Calcolo importo €X"
        - Dates: "Scadenza del DD/MM/YYYY"

        Args:
            value: Extracted value (percentage, amount, or date)

        Returns:
            Action dict or None if value is invalid
        """
        if not value:
            return None

        if "%" in value:
            return {
                "id": "fallback_2",
                "label": f"Calcolo con aliquota {value}",
                "icon": "calculator",
                "prompt": f"Effettua un calcolo pratico applicando l'aliquota del {value}",
                "source_basis": "value_fallback",
            }
        elif "€" in value or "euro" in value.lower():
            return {
                "id": "fallback_2",
                "label": f"Calcolo importo {value}",
                "icon": "calculator",
                "prompt": f"Effettua un calcolo pratico considerando l'importo di {value}",
                "source_basis": "value_fallback",
            }
        elif "/" in value or "-" in value:
            # Date format - create deadline action
            return {
                "id": "fallback_2",
                "label": f"Scadenza del {value}",
                "icon": "calendar",
                "prompt": f"Dettagli sulla scadenza del {value}",
                "source_basis": "date_fallback",
            }
        else:
            # Generic numeric value
            return {
                "id": "fallback_2",
                "label": f"Esempio con {value}",
                "icon": "calculator",
                "prompt": f"Mostrami un esempio pratico con il valore {value}",
                "source_basis": "value_fallback",
            }

    def _validate_fallback_grammar(self, actions: list[dict]) -> list[dict]:
        """Ensure fallback actions have valid Italian grammar.

        DEV-242: Final validation to catch any remaining grammar issues.

        Args:
            actions: List of fallback actions

        Returns:
            List of grammatically valid actions
        """
        validated = []
        for action in actions:
            label = action.get("label", "")

            # Skip if label is too short
            if len(label) < 8:
                continue

            # Check for double-verb patterns and fix them
            words = label.split()
            if len(words) >= 2:
                first_word = words[0].lower()
                second_word = words[1] if len(words) > 1 else ""

                # If pattern is "Verb1 Verb2...", remove first verb
                if self._starts_with_verb(first_word) and second_word and second_word[0].isupper():
                    if self._starts_with_verb(second_word):
                        action = dict(action)
                        action["label"] = " ".join(words[1:])
                        label = action["label"]

            # Ensure label is still valid after fixes
            if len(label) >= 8:
                validated.append(action)

        return validated

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
            reasons.append(f'- "{label}": {reason}')

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
