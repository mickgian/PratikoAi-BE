"""Validation tests for action templates YAML files.

DEV-152: Create Action Templates YAML Files

This module tests that all action template YAML files:
- Parse correctly as valid YAML
- Conform to the Action schema from app/schemas/proactivity.py
- Have unique action IDs within each domain
- Have valid prompt templates with proper placeholders

Test Files:
- app/core/templates/suggested_actions/tax.yaml
- app/core/templates/suggested_actions/labor.yaml
- app/core/templates/suggested_actions/legal.yaml
- app/core/templates/suggested_actions/documents.yaml
- app/core/templates/suggested_actions/default.yaml
"""

import re
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from app.schemas.proactivity import Action, ActionCategory

# Path to suggested_actions templates
TEMPLATES_PATH = Path(__file__).parent.parent.parent / "app" / "core" / "templates" / "suggested_actions"


class TestActionTemplatesValidYaml:
    """Test that all YAML files are valid."""

    @pytest.fixture
    def yaml_files(self) -> list[Path]:
        """Get all YAML files in the suggested_actions directory."""
        return list(TEMPLATES_PATH.glob("*.yaml"))

    def test_templates_directory_exists(self):
        """Test that the templates directory exists."""
        assert TEMPLATES_PATH.exists(), f"Templates directory not found: {TEMPLATES_PATH}"

    def test_all_expected_files_exist(self):
        """Test that all expected template files exist."""
        expected_files = ["tax.yaml", "labor.yaml", "legal.yaml", "documents.yaml", "default.yaml"]
        for filename in expected_files:
            file_path = TEMPLATES_PATH / filename
            assert file_path.exists(), f"Expected template file not found: {filename}"

    def test_all_templates_valid_yaml(self, yaml_files: list[Path]):
        """Test that all YAML files parse correctly."""
        assert len(yaml_files) >= 5, "Expected at least 5 YAML files"

        for yaml_file in yaml_files:
            try:
                content = yaml_file.read_text(encoding="utf-8")
                data = yaml.safe_load(content)
                assert data is not None, f"Empty YAML file: {yaml_file.name}"
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML syntax in {yaml_file.name}: {e}")

    def test_all_templates_have_domain(self, yaml_files: list[Path]):
        """Test that all templates have a domain field."""
        for yaml_file in yaml_files:
            content = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            assert "domain" in data, f"Missing 'domain' field in {yaml_file.name}"
            assert isinstance(data["domain"], str), f"'domain' must be a string in {yaml_file.name}"


class TestActionTemplatesSchema:
    """Test that all templates conform to the Action schema."""

    @pytest.fixture
    def all_actions(self) -> list[tuple[str, str, dict]]:
        """Load all actions from all YAML files."""
        actions = []
        for yaml_file in TEMPLATES_PATH.glob("*.yaml"):
            content = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if data is None:
                continue

            domain = data.get("domain", "unknown")

            # Process regular actions
            if "actions" in data:
                for action_type, action_list in data["actions"].items():
                    for action_dict in action_list:
                        actions.append((yaml_file.name, f"{domain}/{action_type}", action_dict))

            # Process document actions
            if "document_actions" in data:
                for doc_type, action_list in data["document_actions"].items():
                    for action_dict in action_list:
                        actions.append((yaml_file.name, f"{domain}/doc_{doc_type}", action_dict))

        return actions

    def test_all_actions_have_required_fields(self, all_actions: list[tuple[str, str, dict]]):
        """Test that all actions have required fields."""
        required_fields = ["id", "label", "icon", "category", "prompt_template"]

        for filename, action_path, action_dict in all_actions:
            for field in required_fields:
                assert field in action_dict, f"Missing required field '{field}' in {filename} ({action_path})"
                assert action_dict[field], f"Empty required field '{field}' in {filename} ({action_path})"

    def test_all_actions_have_valid_category(self, all_actions: list[tuple[str, str, dict]]):
        """Test that all actions have a valid ActionCategory."""
        valid_categories = {cat.value for cat in ActionCategory}

        for filename, action_path, action_dict in all_actions:
            category = action_dict.get("category", "")
            assert category in valid_categories, (
                f"Invalid category '{category}' in {filename} ({action_path}). "
                f"Valid categories: {valid_categories}"
            )

    def test_all_actions_validate_against_schema(self, all_actions: list[tuple[str, str, dict]]):
        """Test that all actions can be validated by Pydantic Action model."""
        for filename, action_path, action_dict in all_actions:
            try:
                action = Action(
                    id=action_dict.get("id", ""),
                    label=action_dict.get("label", ""),
                    icon=action_dict.get("icon", ""),
                    category=ActionCategory(action_dict.get("category", "")),
                    prompt_template=action_dict.get("prompt_template", ""),
                    requires_input=action_dict.get("requires_input", False),
                    input_placeholder=action_dict.get("input_placeholder"),
                    input_type=action_dict.get("input_type"),
                )
                assert action is not None
            except Exception as e:
                pytest.fail(f"Action validation failed in {filename} ({action_path}): {e}")

    def test_requires_input_has_placeholder(self, all_actions: list[tuple[str, str, dict]]):
        """Test that actions with requires_input=True have input_placeholder."""
        for filename, action_path, action_dict in all_actions:
            if action_dict.get("requires_input", False):
                assert action_dict.get("input_placeholder"), (
                    f"Action with requires_input=True is missing input_placeholder " f"in {filename} ({action_path})"
                )


class TestActionTemplatesUniqueIds:
    """Test that action IDs are unique."""

    def test_no_duplicate_action_ids_within_file(self):
        """Test that action IDs are unique within each file."""
        for yaml_file in TEMPLATES_PATH.glob("*.yaml"):
            content = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if data is None:
                continue

            ids_seen: set[str] = set()
            duplicates: list[str] = []

            # Check regular actions
            if "actions" in data:
                for action_type, action_list in data["actions"].items():
                    for action_dict in action_list:
                        action_id = action_dict.get("id", "")
                        if action_id in ids_seen:
                            duplicates.append(action_id)
                        ids_seen.add(action_id)

            # Check document actions
            if "document_actions" in data:
                for doc_type, action_list in data["document_actions"].items():
                    for action_dict in action_list:
                        action_id = action_dict.get("id", "")
                        if action_id in ids_seen:
                            duplicates.append(action_id)
                        ids_seen.add(action_id)

            assert not duplicates, f"Duplicate action IDs in {yaml_file.name}: {duplicates}"

    def test_no_duplicate_action_ids_across_files(self):
        """Test that action IDs are unique across all files."""
        all_ids: dict[str, str] = {}  # id -> filename
        duplicates: list[tuple[str, str, str]] = []  # (id, file1, file2)

        for yaml_file in TEMPLATES_PATH.glob("*.yaml"):
            content = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if data is None:
                continue

            # Check regular actions
            if "actions" in data:
                for action_type, action_list in data["actions"].items():
                    for action_dict in action_list:
                        action_id = action_dict.get("id", "")
                        if action_id in all_ids:
                            duplicates.append((action_id, all_ids[action_id], yaml_file.name))
                        else:
                            all_ids[action_id] = yaml_file.name

            # Check document actions
            if "document_actions" in data:
                for doc_type, action_list in data["document_actions"].items():
                    for action_dict in action_list:
                        action_id = action_dict.get("id", "")
                        if action_id in all_ids:
                            duplicates.append((action_id, all_ids[action_id], yaml_file.name))
                        else:
                            all_ids[action_id] = yaml_file.name

        assert not duplicates, f"Duplicate action IDs across files: {duplicates}"


class TestActionTemplatesPromptTemplates:
    """Test prompt template formatting."""

    @pytest.fixture
    def all_prompt_templates(self) -> list[tuple[str, str, str]]:
        """Load all prompt templates from all YAML files."""
        templates = []
        for yaml_file in TEMPLATES_PATH.glob("*.yaml"):
            content = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if data is None:
                continue

            # Process regular actions
            if "actions" in data:
                for action_type, action_list in data["actions"].items():
                    for action_dict in action_list:
                        action_id = action_dict.get("id", "")
                        prompt = action_dict.get("prompt_template", "")
                        templates.append((yaml_file.name, action_id, prompt))

            # Process document actions
            if "document_actions" in data:
                for doc_type, action_list in data["document_actions"].items():
                    for action_dict in action_list:
                        action_id = action_dict.get("id", "")
                        prompt = action_dict.get("prompt_template", "")
                        templates.append((yaml_file.name, action_id, prompt))

        return templates

    def test_all_prompt_templates_not_empty(self, all_prompt_templates: list[tuple[str, str, str]]):
        """Test that all prompt templates are not empty."""
        for filename, action_id, prompt in all_prompt_templates:
            assert prompt.strip(), f"Empty prompt_template for {action_id} in {filename}"

    def test_prompt_templates_have_valid_placeholders(self, all_prompt_templates: list[tuple[str, str, str]]):
        """Test that prompt templates use valid placeholder syntax {name}."""
        placeholder_pattern = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

        for filename, action_id, prompt in all_prompt_templates:
            # Find all placeholders (validation only, not used)
            _ = placeholder_pattern.findall(prompt)

            # Check for unclosed braces
            open_count = prompt.count("{")
            close_count = prompt.count("}")
            assert open_count == close_count, (
                f"Mismatched braces in prompt for {action_id} in {filename}: "
                f"'{prompt}' (opens: {open_count}, closes: {close_count})"
            )

            # Check for empty placeholders {}
            if "{}" in prompt:
                pytest.fail(f"Empty placeholder {{}} found in prompt for {action_id} in {filename}")

    def test_prompt_templates_have_minimum_length(self, all_prompt_templates: list[tuple[str, str, str]]):
        """Test that prompt templates have reasonable minimum length."""
        min_length = 10

        for filename, action_id, prompt in all_prompt_templates:
            assert len(prompt) >= min_length, (
                f"Prompt template too short for {action_id} in {filename}: "
                f"'{prompt}' (length: {len(prompt)}, min: {min_length})"
            )


class TestActionTemplatesDocumentCoverage:
    """Test that all required document types are covered."""

    def test_document_types_covered(self):
        """Test that all required document types have actions."""
        required_doc_types = {"fattura", "f24", "bilancio", "cu", "busta_paga", "contratto"}

        documents_file = TEMPLATES_PATH / "documents.yaml"
        assert documents_file.exists(), "documents.yaml not found"

        content = documents_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        assert "document_actions" in data, "Missing 'document_actions' in documents.yaml"

        covered_types = set(data["document_actions"].keys())

        missing_types = required_doc_types - covered_types
        assert not missing_types, f"Missing document types: {missing_types}"

    def test_each_document_type_has_actions(self):
        """Test that each document type has at least one action."""
        documents_file = TEMPLATES_PATH / "documents.yaml"
        content = documents_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        for doc_type, actions in data.get("document_actions", {}).items():
            assert actions, f"No actions defined for document type: {doc_type}"
            assert len(actions) >= 2, f"Document type {doc_type} should have at least 2 actions"


class TestActionTemplatesDomainCoverage:
    """Test that all required domains are covered."""

    def test_all_domains_have_files(self):
        """Test that all required domains have template files."""
        required_domains = {"tax", "labor", "legal", "documents", "default"}

        for domain in required_domains:
            file_path = TEMPLATES_PATH / f"{domain}.yaml"
            assert file_path.exists(), f"Missing template file for domain: {domain}"

    def test_each_domain_has_multiple_action_types(self):
        """Test that each domain file has multiple action types."""
        for yaml_file in TEMPLATES_PATH.glob("*.yaml"):
            if yaml_file.name == "documents.yaml":
                continue  # documents.yaml uses document_actions instead

            content = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)

            if "actions" in data:
                action_types = list(data["actions"].keys())
                assert len(action_types) >= 2, (
                    f"{yaml_file.name} should have at least 2 action types, " f"found: {action_types}"
                )

    def test_default_domain_has_fallback_actions(self):
        """Test that default domain has general fallback actions."""
        default_file = TEMPLATES_PATH / "default.yaml"
        content = default_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        assert data.get("domain") == "default", "default.yaml should have domain='default'"
        assert "actions" in data, "default.yaml should have 'actions'"

        # Check for essential action types
        action_types = set(data["actions"].keys())
        essential_types = {"general_search", "general_explain"}

        missing = essential_types - action_types
        assert not missing, f"default.yaml missing essential action types: {missing}"
