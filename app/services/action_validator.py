"""ActionValidator service for validating LLM-generated actions.

DEV-215: Comprehensive validation layer for suggested actions including:
- Label length validation (8-40 chars)
- Prompt length validation (25+ chars)
- Generic label detection
- Forbidden pattern filtering
- Source grounding validation
- Icon normalization
- Quality scoring
"""

import re
from dataclasses import dataclass, field

from app.core.logging import logger

# Label length constraints
MIN_LABEL_LENGTH = 8
MAX_LABEL_LENGTH = 40
MIN_PROMPT_LENGTH = 25

# Generic labels that are too vague (Italian)
GENERIC_LABELS: frozenset[str] = frozenset(
    {
        "approfondisci",
        "calcola",
        "verifica",
        "scopri",
        "leggi",
        "vedi",
        "altro",
        "continua",
        "info",
        "dettagli",
        "più info",
        "saperne di più",
    }
)

# Valid icon values (text and emoji)
VALID_ICONS: frozenset[str] = frozenset(
    {
        # Text icons
        "calculator",
        "calendar",
        "document",
        "euro",
        "info",
        "warning",
        "check",
        "clock",
        "user",
        "building",
        "briefcase",
        "chart",
        "file",
        "folder",
        "search",
        "settings",
        "star",
        "tag",
        "truck",
        "wallet",
        # Emoji icons (for backward compatibility)
        "✅",
        "📅",
        "⚠️",
        "💰",
        "💡",
        "📞",
        "🔍",
        "📖",
        "🔄",
        "🤖",
        "📋",
        "📊",
        "🏠",
        "🌐",
        "⚖️",
        "🆘",
        "👤",
    }
)

DEFAULT_ICON = "calculator"

# Forbidden patterns - actions suggesting external consultation
# These violate system.md since PratikoAI users ARE the professionals
FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"contatt(?:a(?:re)?|i)\s+(?:un\s+)?commercialista", re.IGNORECASE),
    re.compile(r"contatt(?:a(?:re)?|i)\s+(?:un\s+)?consulente\s+del\s+lavoro", re.IGNORECASE),
    re.compile(r"contatt(?:a(?:re)?|i)\s+(?:un\s+)?avvocato", re.IGNORECASE),
    re.compile(r"contatt(?:a(?:re)?|i)\s+(?:un\s+)?esperto", re.IGNORECASE),
    re.compile(r"rivolgiti\s+(?:a\s+)?(?:un\s+)?professionista", re.IGNORECASE),
    re.compile(r"consult(?:a(?:re)?|i)\s+(?:un\s+)?esperto", re.IGNORECASE),
    re.compile(r"visita\s+il\s+sito\s+dell['']?Agenzia", re.IGNORECASE),
    re.compile(r"verifica\s+sul\s+sito\s+ufficiale", re.IGNORECASE),
    re.compile(r"chied(?:i|ere)\s+(?:a\s+)?(?:un\s+)?(?:commercialista|avvocato|esperto)", re.IGNORECASE),
    re.compile(r"consult(?:a(?:re)?|i)\s+(?:un\s+)?(?:commercialista|avvocato)", re.IGNORECASE),
    # Additional patterns from spec
    re.compile(r"consult[ai].*(?:commercialista|avvocato|esperto|professionista)", re.IGNORECASE),
    re.compile(r"contatt[ai].*(?:INPS|INAIL|Agenzia|ufficio)", re.IGNORECASE),
    re.compile(r"rivolgiti.*(?:CAF|patronato|studio)", re.IGNORECASE),
    re.compile(r"verifica.*(?:sul sito|online|portale)", re.IGNORECASE),
    re.compile(r"chiedi.*(?:consiglio|parere|aiuto)", re.IGNORECASE),
    re.compile(r"(?:cerca|trova).*(?:professionista|consulente)", re.IGNORECASE),
    # DEV-242: Anti-monitoring patterns - PratikoAI IS the monitoring service
    re.compile(r"monitor(?:a(?:re)?|i)\s+(?:(?:le|gli)\s+)?(?:comunicazioni|aggiornamenti)", re.IGNORECASE),
    re.compile(r"controlla(?:re)?\s+periodicamente", re.IGNORECASE),
    re.compile(r"tien[ei]\s+d['']?occhio", re.IGNORECASE),
    re.compile(r"segui(?:re)?\s+(?:le\s+)?novit[àa]", re.IGNORECASE),
    re.compile(r"rest(?:a(?:re)?|i)\s+aggiornat[oiae]", re.IGNORECASE),
    re.compile(r"verificare?\s+periodicamente", re.IGNORECASE),
    re.compile(r"consulta(?:re)?\s+regolarmente", re.IGNORECASE),
    re.compile(r"(?:le\s+)?fonti\s+ufficiali\s+per\s+aggiornamenti", re.IGNORECASE),
]


@dataclass
class ValidationResult:
    """Result of validating a single action."""

    is_valid: bool
    rejection_reason: str | None
    warnings: list[str] = field(default_factory=list)
    modified_action: dict | None = None


@dataclass
class BatchValidationResult:
    """Result of validating a batch of actions."""

    validated_actions: list[dict]
    rejected_count: int
    rejection_log: list[tuple[dict, str]]  # (action, reason)
    quality_score: float  # 0.0-1.0


class ActionValidator:
    """Validates LLM-generated actions against quality rules.

    DEV-215: Implements comprehensive validation including:
    - Label length (8-40 chars)
    - Prompt length (25+ chars)
    - Generic label detection
    - Forbidden pattern filtering
    - Source grounding checks
    - Icon normalization
    """

    def validate(self, action: dict, kb_sources: list[dict]) -> ValidationResult:
        """Validate a single action against all rules.

        Args:
            action: Action dict with label, prompt, and optional icon
            kb_sources: KB source metadata for grounding check

        Returns:
            ValidationResult with is_valid, rejection_reason, warnings, and modified_action
        """
        warnings: list[str] = []
        modified_action: dict | None = None

        # Check required fields exist
        if not isinstance(action, dict):
            return ValidationResult(
                is_valid=False,
                rejection_reason="Action must be a dictionary",
                warnings=[],
                modified_action=None,
            )

        label = action.get("label")
        prompt = action.get("prompt")

        # Check for missing required fields
        if label is None:
            return ValidationResult(
                is_valid=False,
                rejection_reason="Missing required field: label",
                warnings=[],
                modified_action=None,
            )

        if prompt is None:
            return ValidationResult(
                is_valid=False,
                rejection_reason="Missing required field: prompt",
                warnings=[],
                modified_action=None,
            )

        # Ensure strings
        if not isinstance(label, str):
            return ValidationResult(
                is_valid=False,
                rejection_reason="Label must be a string",
                warnings=[],
                modified_action=None,
            )

        if not isinstance(prompt, str):
            return ValidationResult(
                is_valid=False,
                rejection_reason="Prompt must be a string",
                warnings=[],
                modified_action=None,
            )

        # Check label length - too short is rejection
        label_result = self._check_label_length(label)
        if not label_result.is_valid:
            return label_result

        # Check for label truncation (too long)
        if len(label) > MAX_LABEL_LENGTH:
            modified_action = dict(action)
            modified_action["label"] = label[:MAX_LABEL_LENGTH]
            label = modified_action["label"]

        # Check prompt length
        prompt_result = self._check_prompt_length(prompt)
        if not prompt_result.is_valid:
            return prompt_result

        # Check for generic labels
        generic_result = self._check_generic_label(label)
        if not generic_result.is_valid:
            return generic_result

        # Check for forbidden patterns
        forbidden_result = self._check_forbidden_patterns(action)
        if not forbidden_result.is_valid:
            return forbidden_result

        # Check source grounding (warning only)
        grounding_result = self._check_source_grounding(action, kb_sources)
        if grounding_result.warnings:
            warnings.extend(grounding_result.warnings)

        # Normalize icon
        icon = action.get("icon", "")
        normalized_icon = self._normalize_icon(icon)
        if normalized_icon != icon or not icon:
            if modified_action is None:
                modified_action = dict(action)
            modified_action["icon"] = normalized_icon

        return ValidationResult(
            is_valid=True,
            rejection_reason=None,
            warnings=warnings,
            modified_action=modified_action,
        )

    def validate_batch(
        self,
        actions: list[dict],
        response_text: str,
        kb_sources: list[dict],
    ) -> BatchValidationResult:
        """Validate all actions, return filtered list with rejection log.

        Args:
            actions: List of action dicts to validate
            response_text: LLM response text (for context)
            kb_sources: KB source metadata for grounding checks

        Returns:
            BatchValidationResult with validated_actions, rejected_count, rejection_log, quality_score
        """
        if not actions:
            return BatchValidationResult(
                validated_actions=[],
                rejected_count=0,
                rejection_log=[],
                quality_score=0.0,
            )

        validated_actions: list[dict] = []
        rejection_log: list[tuple[dict, str]] = []

        for action in actions:
            result = self.validate(action, kb_sources)

            if result.is_valid:
                # Use modified action if available, otherwise original
                final_action = result.modified_action if result.modified_action else action
                validated_actions.append(final_action)

                # Log warnings
                for warning in result.warnings:
                    logger.warning(
                        "action_validation_warning",
                        warning=warning,
                        action_label=action.get("label", "")[:50],
                    )
            else:
                rejection_log.append((action, result.rejection_reason or "Unknown"))
                logger.info(
                    "action_rejected",
                    reason=result.rejection_reason,
                    action_label=action.get("label", "")[:50],
                )

        # Calculate quality score
        total = len(actions)
        valid_count = len(validated_actions)
        quality_score = valid_count / total if total > 0 else 0.0

        return BatchValidationResult(
            validated_actions=validated_actions,
            rejected_count=len(rejection_log),
            rejection_log=rejection_log,
            quality_score=quality_score,
        )

    def _check_label_length(self, label: str) -> ValidationResult:
        """Check label length constraints.

        Args:
            label: Action label text

        Returns:
            ValidationResult - invalid if too short, valid otherwise
        """
        if len(label) < MIN_LABEL_LENGTH:
            return ValidationResult(
                is_valid=False,
                rejection_reason=f"Label too short: {len(label)} chars (minimum {MIN_LABEL_LENGTH})",
                warnings=[],
                modified_action=None,
            )

        return ValidationResult(
            is_valid=True,
            rejection_reason=None,
            warnings=[],
            modified_action=None,
        )

    def _check_prompt_length(self, prompt: str) -> ValidationResult:
        """Check prompt length constraints.

        Args:
            prompt: Action prompt text

        Returns:
            ValidationResult - invalid if too short
        """
        if len(prompt) < MIN_PROMPT_LENGTH:
            return ValidationResult(
                is_valid=False,
                rejection_reason=f"Prompt too short: {len(prompt)} chars (minimum {MIN_PROMPT_LENGTH})",
                warnings=[],
                modified_action=None,
            )

        return ValidationResult(
            is_valid=True,
            rejection_reason=None,
            warnings=[],
            modified_action=None,
        )

    def _check_generic_label(self, label: str) -> ValidationResult:
        """Check for overly generic labels.

        Args:
            label: Action label text

        Returns:
            ValidationResult - invalid if label is generic
        """
        label_lower = label.lower().strip()

        if label_lower in GENERIC_LABELS:
            return ValidationResult(
                is_valid=False,
                rejection_reason=f"Generic label not allowed: '{label}'",
                warnings=[],
                modified_action=None,
            )

        return ValidationResult(
            is_valid=True,
            rejection_reason=None,
            warnings=[],
            modified_action=None,
        )

    def _check_forbidden_patterns(self, action: dict) -> ValidationResult:
        """Check for forbidden consultant/verify patterns.

        Args:
            action: Action dict with label and prompt

        Returns:
            ValidationResult - invalid if forbidden pattern found
        """
        label = action.get("label", "")
        prompt = action.get("prompt", "")
        text_to_check = f"{label} {prompt}"

        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text_to_check):
                return ValidationResult(
                    is_valid=False,
                    rejection_reason=f"Forbidden pattern detected: {pattern.pattern[:50]}",
                    warnings=[],
                    modified_action=None,
                )

        return ValidationResult(
            is_valid=True,
            rejection_reason=None,
            warnings=[],
            modified_action=None,
        )

    def _check_source_grounding(self, action: dict, kb_sources: list[dict]) -> ValidationResult:
        """Check if action references a KB source.

        Args:
            action: Action dict
            kb_sources: KB source metadata list

        Returns:
            ValidationResult - always valid but may include warning
        """
        if not kb_sources:
            return ValidationResult(
                is_valid=True,
                rejection_reason=None,
                warnings=["No KB sources available for grounding check"],
                modified_action=None,
            )

        # Extract action text for matching
        label = action.get("label", "").lower()
        prompt = action.get("prompt", "").lower()
        action_text = f"{label} {prompt}"

        # Check if any KB topic appears in action text
        for source in kb_sources:
            topics = source.get("key_topics", [])
            for topic in topics:
                if topic.lower() in action_text:
                    # Found grounding
                    return ValidationResult(
                        is_valid=True,
                        rejection_reason=None,
                        warnings=[],
                        modified_action=None,
                    )

        # No grounding found - warning only
        return ValidationResult(
            is_valid=True,
            rejection_reason=None,
            warnings=["No source grounding found - action may lack KB reference"],
            modified_action=None,
        )

    def _normalize_icon(self, icon: str) -> str:
        """Normalize icon to valid enum value or default.

        Args:
            icon: Icon value from action

        Returns:
            Valid icon value (original if valid, default otherwise)
        """
        if not icon:
            return DEFAULT_ICON
        # Check exact match first (for emojis)
        if icon in VALID_ICONS:
            return icon
        # Try lowercase match (for text icons)
        if icon.lower() in VALID_ICONS:
            return icon.lower()
        return DEFAULT_ICON

    def validate_batch_with_context(
        self,
        actions: list[dict],
        response_text: str,
        kb_sources: list[dict],
        previous_actions_used: list[str] | None = None,
    ) -> BatchValidationResult:
        """Validate actions with context awareness.

        DEV-242: Enhanced validation that considers:
        - Previously used actions (avoid repetition)
        - Semantic similarity (deduplicate similar actions)

        Args:
            actions: List of action dicts to validate
            response_text: LLM response text (for context)
            kb_sources: KB source metadata for grounding checks
            previous_actions_used: Labels of actions user already clicked

        Returns:
            BatchValidationResult with deduplicated, context-aware actions
        """
        # Standard validation first
        base_result = self.validate_batch(actions, response_text, kb_sources)

        if not base_result.validated_actions:
            return base_result

        # Remove actions similar to previously used
        filtered_actions = base_result.validated_actions
        if previous_actions_used:
            filtered_actions = self._filter_previously_used(
                filtered_actions,
                previous_actions_used,
            )

        # Deduplicate semantically similar actions
        deduplicated = self._deduplicate_actions(filtered_actions)

        # Recalculate quality score
        original_count = len(actions)
        final_count = len(deduplicated)
        quality_score = final_count / original_count if original_count > 0 else 0.0

        return BatchValidationResult(
            validated_actions=deduplicated,
            rejected_count=base_result.rejected_count + (len(filtered_actions) - len(deduplicated)),
            rejection_log=base_result.rejection_log,
            quality_score=quality_score,
        )

    def _deduplicate_actions(self, actions: list[dict]) -> list[dict]:
        """Remove semantically similar actions.

        DEV-242: Removes actions with >50% word overlap to avoid
        presenting nearly identical options to user.

        Args:
            actions: List of validated action dicts

        Returns:
            Deduplicated list of actions
        """
        if len(actions) <= 1:
            return actions

        deduplicated: list[dict] = []

        for action in actions:
            if not self._is_duplicate_of_any(action, deduplicated):
                deduplicated.append(action)

        if len(deduplicated) < len(actions):
            logger.info(
                "action_deduplication_applied",
                original_count=len(actions),
                deduplicated_count=len(deduplicated),
            )

        return deduplicated

    def _is_duplicate_of_any(self, action: dict, existing: list[dict]) -> bool:
        """Check if action is semantically similar to any existing action.

        Args:
            action: Action to check
            existing: List of already accepted actions

        Returns:
            True if action is a duplicate of any existing action
        """
        action_words = self._extract_significant_words(action)

        for existing_action in existing:
            existing_words = self._extract_significant_words(existing_action)
            overlap = self._calculate_word_overlap(action_words, existing_words)

            if overlap > 0.5:  # >50% overlap threshold
                logger.debug(
                    "action_duplicate_detected",
                    action_label=action.get("label", "")[:30],
                    existing_label=existing_action.get("label", "")[:30],
                    overlap=overlap,
                )
                return True

        return False

    def _extract_significant_words(self, action: dict) -> set[str]:
        """Extract significant words from action for comparison.

        Excludes common Italian stop words and short words.

        Args:
            action: Action dict with label and prompt

        Returns:
            Set of significant lowercase words
        """
        # Italian stop words to exclude
        stop_words = {
            "il",
            "lo",
            "la",
            "i",
            "gli",
            "le",
            "un",
            "una",
            "uno",
            "del",
            "della",
            "dello",
            "dei",
            "delle",
            "degli",
            "al",
            "alla",
            "allo",
            "ai",
            "alle",
            "agli",
            "da",
            "dal",
            "dalla",
            "dallo",
            "dai",
            "dalle",
            "dagli",
            "in",
            "nel",
            "nella",
            "nello",
            "nei",
            "nelle",
            "negli",
            "su",
            "sul",
            "sulla",
            "sullo",
            "sui",
            "sulle",
            "sugli",
            "con",
            "per",
            "tra",
            "fra",
            "di",
            "a",
            "e",
            "o",
            "che",
            "come",
            "cosa",
            "quale",
            "quali",
            "quanto",
            "quanti",
            "questo",
            "questa",
            "questi",
            "queste",
            "quello",
            "quella",
            "quelli",
            "quelle",
            "sono",
            "è",
            "hai",
            "ho",
            "ha",
            "hanno",
            "abbiamo",
            "essere",
            "avere",
            "fare",
            "dire",
        }

        label = action.get("label", "").lower()
        prompt = action.get("prompt", "").lower()
        text = f"{label} {prompt}"

        # Extract words, exclude stop words and short words
        words = set()
        for word in re.findall(r"\b\w+\b", text):
            if len(word) > 2 and word not in stop_words:
                words.add(word)

        return words

    def _calculate_word_overlap(self, words1: set[str], words2: set[str]) -> float:
        """Calculate Jaccard similarity between word sets.

        Args:
            words1: First set of words
            words2: Second set of words

        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _filter_previously_used(
        self,
        actions: list[dict],
        previous_labels: list[str],
    ) -> list[dict]:
        """Filter out actions similar to previously used ones.

        DEV-242: Prevents showing actions user already clicked/used.

        Args:
            actions: List of validated actions
            previous_labels: Labels of actions user already used

        Returns:
            Filtered list without previously-used-similar actions
        """
        if not previous_labels:
            return actions

        # Normalize previous labels for comparison
        normalized_previous = {label.lower().strip() for label in previous_labels}

        filtered: list[dict] = []
        for action in actions:
            action_label = action.get("label", "").lower().strip()

            # Check exact match
            if action_label in normalized_previous:
                logger.debug(
                    "action_filtered_previously_used",
                    action_label=action.get("label", "")[:30],
                )
                continue

            # Check word overlap with previous actions
            action_words = self._extract_significant_words(action)
            is_similar = False

            for prev_label in previous_labels:
                prev_words = self._extract_significant_words({"label": prev_label, "prompt": ""})
                overlap = self._calculate_word_overlap(action_words, prev_words)

                if overlap > 0.5:  # 50% overlap with previous = too similar
                    is_similar = True
                    logger.debug(
                        "action_filtered_similar_to_previous",
                        action_label=action.get("label", "")[:30],
                        previous_label=prev_label[:30],
                        overlap=overlap,
                    )
                    break

            if not is_similar:
                filtered.append(action)

        return filtered


# Singleton instance for convenience
action_validator = ActionValidator()
