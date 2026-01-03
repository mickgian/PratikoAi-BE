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
GENERIC_LABELS: frozenset[str] = frozenset({
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
})

# Valid icon values
VALID_ICONS: frozenset[str] = frozenset({
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
})

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

    def _check_source_grounding(
        self, action: dict, kb_sources: list[dict]
    ) -> ValidationResult:
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
        if icon and icon.lower() in VALID_ICONS:
            return icon.lower()
        return DEFAULT_ICON


# Singleton instance for convenience
action_validator = ActionValidator()
