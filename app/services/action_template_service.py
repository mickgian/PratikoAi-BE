"""Action Template Service for PratikoAI v1.5 - DEV-151.

This service loads and manages action and question templates from YAML files.
Templates are cached in memory for fast lookup.

Features:
- Load action templates from app/core/templates/suggested_actions/
- Load question templates from app/core/templates/interactive_questions/
- Cache templates in memory for <5ms lookup
- Fall back to 'default' domain when requested domain not found
- Validate templates against Pydantic schemas
- Support hot-reload in development mode
"""

import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.schemas.proactivity import (
    Action,
    ActionCategory,
    InteractiveOption,
    InteractiveQuestion,
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when template configuration is invalid."""

    pass


class ActionTemplateService:
    """Service for loading and managing action and question templates.

    Attributes:
        templates_path: Base path for template directories
        _action_cache: Cached action templates by domain/action_type
        _question_cache: Cached question templates by question_id
        _document_action_cache: Cached document-specific actions
    """

    def __init__(self, templates_path: Path | None = None):
        """Initialize the service with optional custom templates path.

        Args:
            templates_path: Base path containing suggested_actions/ and
                            interactive_questions/ directories.
                            Defaults to app/core/templates/
        """
        if templates_path is None:
            templates_path = Path(__file__).parent.parent / "core" / "templates"

        self.templates_path = templates_path
        self._action_cache: dict[str, dict[str, list[Action]]] = {}
        self._question_cache: dict[str, InteractiveQuestion] = {}
        self._document_action_cache: dict[str, list[Action]] = {}
        self._action_ids_seen: set[str] = set()

    def load_templates(self) -> None:
        """Load all templates from YAML files.

        Loads both action templates from suggested_actions/ and
        question templates from interactive_questions/.

        Raises:
            ConfigurationError: If YAML syntax is invalid
        """
        self._action_cache.clear()
        self._question_cache.clear()
        self._document_action_cache.clear()
        self._action_ids_seen.clear()

        self._load_action_templates()
        self._load_question_templates()

    def _load_action_templates(self) -> None:
        """Load action templates from suggested_actions/ directory."""
        actions_dir = self.templates_path / "suggested_actions"

        if not actions_dir.exists():
            logger.warning(
                "action_templates_dir_not_found",
                extra={"templates_path": str(actions_dir)},
            )
            return

        for yaml_file in actions_dir.glob("*.yaml"):
            self._load_action_file(yaml_file)

    def _load_action_file(self, yaml_file: Path) -> None:
        """Load a single action template YAML file.

        Args:
            yaml_file: Path to the YAML file

        Raises:
            ConfigurationError: If YAML syntax is invalid
        """
        try:
            content = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if data is None:
                logger.warning(
                    "empty_yaml_file",
                    extra={"file": str(yaml_file)},
                )
                return

            domain = data.get("domain", "default")

            # Process regular actions
            if "actions" in data:
                self._process_domain_actions(domain, data["actions"])

            # Process document-specific actions
            if "document_actions" in data:
                self._process_document_actions(data["document_actions"])

        except yaml.YAMLError as e:
            logger.error(
                "yaml_syntax_error",
                extra={
                    "file": str(yaml_file),
                    "error": str(e),
                },
            )
            raise ConfigurationError(f"Invalid YAML syntax in {yaml_file}: {e}")

    def _process_domain_actions(self, domain: str, actions_data: dict[str, list[dict[str, Any]]]) -> None:
        """Process actions for a domain.

        Args:
            domain: Domain name (e.g., 'tax', 'labor')
            actions_data: Dict mapping action_type to list of action dicts
        """
        if domain not in self._action_cache:
            self._action_cache[domain] = {}

        for action_type, action_list in actions_data.items():
            if action_type not in self._action_cache[domain]:
                self._action_cache[domain][action_type] = []

            for action_dict in action_list:
                action = self._parse_action(action_dict)
                if action:
                    self._action_cache[domain][action_type].append(action)

    def _process_document_actions(self, document_actions: dict[str, list[dict[str, Any]]]) -> None:
        """Process document-specific actions.

        Args:
            document_actions: Dict mapping document_type to list of action dicts
        """
        for doc_type, action_list in document_actions.items():
            if doc_type not in self._document_action_cache:
                self._document_action_cache[doc_type] = []

            for action_dict in action_list:
                action = self._parse_action(action_dict)
                if action:
                    self._document_action_cache[doc_type].append(action)

    def _parse_action(self, action_dict: dict[str, Any]) -> Action | None:
        """Parse an action dict into an Action model.

        Args:
            action_dict: Raw action data from YAML

        Returns:
            Action model or None if validation fails
        """
        try:
            action_id = action_dict.get("id", "")

            # Check for duplicates
            if action_id in self._action_ids_seen:
                logger.warning(
                    "duplicate_action_id",
                    extra={"action_id": action_id},
                )
            self._action_ids_seen.add(action_id)

            # Convert category string to enum
            category_str = action_dict.get("category", "")
            try:
                category = ActionCategory(category_str)
            except ValueError:
                logger.error(
                    "invalid_action_category",
                    extra={
                        "action_id": action_id,
                        "category": category_str,
                    },
                )
                return None

            return Action(
                id=action_dict.get("id", ""),
                label=action_dict.get("label", ""),
                icon=action_dict.get("icon", ""),
                category=category,
                prompt_template=action_dict.get("prompt_template", ""),
                requires_input=action_dict.get("requires_input", False),
                input_placeholder=action_dict.get("input_placeholder"),
                input_type=action_dict.get("input_type"),
            )
        except Exception as e:
            logger.error(
                "action_validation_error",
                extra={
                    "action_id": action_dict.get("id", "unknown"),
                    "error": str(e),
                },
            )
            return None

    def _load_question_templates(self) -> None:
        """Load question templates from interactive_questions/ directory."""
        questions_dir = self.templates_path / "interactive_questions"

        if not questions_dir.exists():
            logger.warning(
                "question_templates_dir_not_found",
                extra={"templates_path": str(questions_dir)},
            )
            return

        for yaml_file in questions_dir.glob("*.yaml"):
            self._load_question_file(yaml_file)

    def _load_question_file(self, yaml_file: Path) -> None:
        """Load a single question template YAML file.

        Args:
            yaml_file: Path to the YAML file

        Raises:
            ConfigurationError: If YAML syntax is invalid
        """
        try:
            content = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if data is None or "questions" not in data:
                return

            for question_key, question_data in data["questions"].items():
                question = self._parse_question(question_data)
                if question:
                    self._question_cache[question.id] = question

        except yaml.YAMLError as e:
            logger.error(
                "yaml_syntax_error",
                extra={
                    "file": str(yaml_file),
                    "error": str(e),
                },
            )
            raise ConfigurationError(f"Invalid YAML syntax in {yaml_file}: {e}")

    def _parse_question(self, question_dict: dict[str, Any]) -> InteractiveQuestion | None:
        """Parse a question dict into an InteractiveQuestion model.

        Args:
            question_dict: Raw question data from YAML

        Returns:
            InteractiveQuestion model or None if validation fails
        """
        try:
            options = []
            for opt_dict in question_dict.get("options", []):
                option = InteractiveOption(
                    id=opt_dict.get("id", ""),
                    label=opt_dict.get("label", ""),
                    icon=opt_dict.get("icon"),
                    leads_to=opt_dict.get("leads_to"),
                    requires_input=opt_dict.get("requires_input", False),
                )
                options.append(option)

            return InteractiveQuestion(
                id=question_dict.get("id", ""),
                trigger_query=question_dict.get("trigger_query"),
                text=question_dict.get("text", ""),
                question_type=question_dict.get("question_type", "single_choice"),
                options=options,
                allow_custom_input=question_dict.get("allow_custom_input", False),
                custom_input_placeholder=question_dict.get("custom_input_placeholder"),
                prefilled_params=question_dict.get("prefilled_params"),
            )
        except Exception as e:
            logger.error(
                "question_validation_error",
                extra={
                    "question_id": question_dict.get("id", "unknown"),
                    "error": str(e),
                },
            )
            return None

    def get_actions_for_domain(self, domain: str, action_type: str) -> list[Action]:
        """Get actions for a specific domain and action type.

        Falls back to 'default' domain if the requested domain
        or action_type is not found.

        Args:
            domain: Domain name (e.g., 'tax', 'labor')
            action_type: Type of action (e.g., 'fiscal_calculation')

        Returns:
            List of Action models (may be empty)
        """
        # Try exact match
        if domain in self._action_cache:
            if action_type in self._action_cache[domain]:
                return self._action_cache[domain][action_type]

        # Fall back to default domain
        if "default" in self._action_cache:
            # Try matching action_type in default domain
            if action_type in self._action_cache["default"]:
                return self._action_cache["default"][action_type]

            # Return first available action type from default
            for actions in self._action_cache["default"].values():
                if actions:
                    return actions

        return []

    def get_actions_for_document(self, document_type: str) -> list[Action]:
        """Get actions for a specific document type.

        Args:
            document_type: Type of document (e.g., 'fattura', 'f24')

        Returns:
            List of Action models (may be empty)
        """
        return self._document_action_cache.get(document_type, [])

    def get_question(self, question_id: str) -> InteractiveQuestion | None:
        """Get a question by its ID.

        Args:
            question_id: Unique question identifier

        Returns:
            InteractiveQuestion or None if not found
        """
        return self._question_cache.get(question_id)

    def reload_templates(self) -> None:
        """Force reload all templates from disk.

        Useful for hot-reloading in development mode.
        """
        self.load_templates()

    def _validate_templates(self, templates_data: dict[str, Any]) -> list[str]:
        """Validate template data and return list of errors.

        Args:
            templates_data: Raw template data from YAML

        Returns:
            List of validation error messages
        """
        errors = []

        if "actions" in templates_data:
            for action_type, action_list in templates_data["actions"].items():
                for i, action_dict in enumerate(action_list):
                    action_errors = self._validate_action(action_dict, f"{action_type}[{i}]")
                    errors.extend(action_errors)

        return errors

    def _validate_action(self, action_dict: dict[str, Any], context: str) -> list[str]:
        """Validate a single action dict.

        Args:
            action_dict: Raw action data
            context: Context string for error messages

        Returns:
            List of validation error messages
        """
        errors = []
        required_fields = ["id", "label", "icon", "category", "prompt_template"]

        for field in required_fields:
            if field not in action_dict or not action_dict.get(field):
                errors.append(f"{context}: Missing required field '{field}'")

        return errors
