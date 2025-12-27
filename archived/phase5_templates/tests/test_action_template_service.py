"""Tests for ActionTemplateService - DEV-151.

TDD: Tests written BEFORE implementation.
Tests cover loading, caching, fallback, and validation of YAML templates.
"""

import tempfile
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from app.schemas.proactivity import Action, ActionCategory, InteractiveOption, InteractiveQuestion


class TestActionTemplateServiceLoading:
    """Test template loading functionality."""

    def test_load_valid_yaml(self, tmp_path: Path):
        """Test successfully loading valid YAML templates."""
        from app.services.action_template_service import ActionTemplateService

        # Create a valid template file
        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        tax_yaml = {
            "domain": "tax",
            "actions": {
                "fiscal_calculation": [
                    {
                        "id": "calculate_irpef",
                        "label": "Calcola IRPEF",
                        "icon": "calculate",
                        "category": "calculate",
                        "prompt_template": "Calcola IRPEF per {reddito}",
                    }
                ]
            },
        }

        (templates_dir / "tax.yaml").write_text(yaml.dump(tax_yaml))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        actions = service.get_actions_for_domain("tax", "fiscal_calculation")
        assert len(actions) == 1
        assert actions[0].id == "calculate_irpef"
        assert actions[0].label == "Calcola IRPEF"
        assert actions[0].category == ActionCategory.CALCULATE

    def test_load_multiple_files(self, tmp_path: Path):
        """Test loading templates from multiple YAML files."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        # Create tax.yaml
        tax_yaml = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    {
                        "id": "tax_action",
                        "label": "Tax Action",
                        "icon": "tax",
                        "category": "calculate",
                        "prompt_template": "Tax {amount}",
                    }
                ]
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(tax_yaml))

        # Create labor.yaml
        labor_yaml = {
            "domain": "labor",
            "actions": {
                "contracts": [
                    {
                        "id": "labor_action",
                        "label": "Labor Action",
                        "icon": "contract",
                        "category": "search",
                        "prompt_template": "Labor {type}",
                    }
                ]
            },
        }
        (templates_dir / "labor.yaml").write_text(yaml.dump(labor_yaml))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        tax_actions = service.get_actions_for_domain("tax", "fiscal")
        labor_actions = service.get_actions_for_domain("labor", "contracts")

        assert len(tax_actions) == 1
        assert tax_actions[0].id == "tax_action"
        assert len(labor_actions) == 1
        assert labor_actions[0].id == "labor_action"

    def test_load_action_with_all_fields(self, tmp_path: Path):
        """Test loading action with all optional fields."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    {
                        "id": "recalculate",
                        "label": "Ricalcola",
                        "icon": "refresh",
                        "category": "calculate",
                        "prompt_template": "Ricalcola con {amount}",
                        "requires_input": True,
                        "input_placeholder": "Nuovo importo",
                        "input_type": "number",
                    }
                ]
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        actions = service.get_actions_for_domain("tax", "fiscal")
        assert len(actions) == 1
        assert actions[0].requires_input is True
        assert actions[0].input_placeholder == "Nuovo importo"
        assert actions[0].input_type == "number"


class TestActionTemplateServiceFallback:
    """Test fallback behavior."""

    def test_domain_fallback(self, tmp_path: Path):
        """Test falling back to default domain when requested domain not found."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        # Only create default.yaml
        default_yaml = {
            "domain": "default",
            "actions": {
                "general": [
                    {
                        "id": "default_action",
                        "label": "Default Action",
                        "icon": "star",
                        "category": "explain",
                        "prompt_template": "Explain {topic}",
                    }
                ]
            },
        }
        (templates_dir / "default.yaml").write_text(yaml.dump(default_yaml))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        # Request non-existent domain, should fall back to default
        actions = service.get_actions_for_domain("nonexistent", "general")
        assert len(actions) == 1
        assert actions[0].id == "default_action"

    def test_action_type_fallback(self, tmp_path: Path):
        """Test falling back when action_type not found in domain."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    {
                        "id": "tax_action",
                        "label": "Tax Action",
                        "icon": "tax",
                        "category": "calculate",
                        "prompt_template": "Tax {amount}",
                    }
                ]
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        default_yaml = {
            "domain": "default",
            "actions": {
                "general": [
                    {
                        "id": "default_general",
                        "label": "Default General",
                        "icon": "star",
                        "category": "explain",
                        "prompt_template": "Explain {topic}",
                    }
                ]
            },
        }
        (templates_dir / "default.yaml").write_text(yaml.dump(default_yaml))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        # Domain exists but action_type doesn't, should fall back to default
        actions = service.get_actions_for_domain("tax", "nonexistent_type")
        assert len(actions) == 1
        assert actions[0].id == "default_general"


class TestActionTemplateServiceCache:
    """Test caching functionality."""

    def test_cache_hit(self, tmp_path: Path):
        """Test that second lookup uses cache."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    {
                        "id": "cached_action",
                        "label": "Cached Action",
                        "icon": "cache",
                        "category": "calculate",
                        "prompt_template": "Cache {value}",
                    }
                ]
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        # First call
        actions1 = service.get_actions_for_domain("tax", "fiscal")

        # Second call should use cache (same object)
        actions2 = service.get_actions_for_domain("tax", "fiscal")

        assert actions1 is actions2
        assert len(actions1) == 1

    def test_reload_templates(self, tmp_path: Path):
        """Test that reload_templates refreshes the cache."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        # Initial content
        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    {
                        "id": "original_action",
                        "label": "Original",
                        "icon": "original",
                        "category": "calculate",
                        "prompt_template": "Original {value}",
                    }
                ]
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        actions1 = service.get_actions_for_domain("tax", "fiscal")
        assert actions1[0].id == "original_action"

        # Update file
        yaml_content["actions"]["fiscal"][0]["id"] = "updated_action"  # type: ignore[index]
        yaml_content["actions"]["fiscal"][0]["label"] = "Updated"  # type: ignore[index]
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        # Reload
        service.reload_templates()

        actions2 = service.get_actions_for_domain("tax", "fiscal")
        assert actions2[0].id == "updated_action"


class TestActionTemplateServiceDocuments:
    """Test document-type specific actions."""

    def test_document_type_lookup(self, tmp_path: Path):
        """Test getting actions for specific document types."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        documents_yaml = {
            "domain": "documents",
            "document_actions": {
                "fattura": [
                    {
                        "id": "verify_fattura",
                        "label": "Verifica Fattura",
                        "icon": "check",
                        "category": "verify",
                        "prompt_template": "Verifica fattura {numero}",
                    }
                ],
                "f24": [
                    {
                        "id": "calculate_f24",
                        "label": "Calcola F24",
                        "icon": "calculate",
                        "category": "calculate",
                        "prompt_template": "Calcola F24 {codice}",
                    }
                ],
            },
        }
        (templates_dir / "documents.yaml").write_text(yaml.dump(documents_yaml))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        fattura_actions = service.get_actions_for_document("fattura")
        f24_actions = service.get_actions_for_document("f24")

        assert len(fattura_actions) == 1
        assert fattura_actions[0].id == "verify_fattura"
        assert len(f24_actions) == 1
        assert f24_actions[0].id == "calculate_f24"

    def test_document_type_not_found(self, tmp_path: Path):
        """Test graceful handling when document type not found."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        documents_yaml = {
            "domain": "documents",
            "document_actions": {
                "fattura": [
                    {
                        "id": "verify_fattura",
                        "label": "Verifica",
                        "icon": "check",
                        "category": "verify",
                        "prompt_template": "Verifica {doc}",
                    }
                ]
            },
        }
        (templates_dir / "documents.yaml").write_text(yaml.dump(documents_yaml))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        # Non-existent document type should return empty list
        actions = service.get_actions_for_document("unknown_doc")
        assert actions == []


class TestActionTemplateServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_file_graceful(self, tmp_path: Path):
        """Test graceful handling of missing template files."""
        from app.services.action_template_service import ActionTemplateService

        # Create empty templates directory
        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        # Should return empty list, not error
        actions = service.get_actions_for_domain("tax", "fiscal")
        assert actions == []

    def test_invalid_yaml_error(self, tmp_path: Path):
        """Test that invalid YAML syntax raises ConfigurationError."""
        from app.services.action_template_service import ActionTemplateService, ConfigurationError

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        # Write invalid YAML
        (templates_dir / "invalid.yaml").write_text("invalid: yaml: syntax: [unclosed")

        service = ActionTemplateService(templates_path=tmp_path)

        with pytest.raises(ConfigurationError) as exc_info:
            service.load_templates()

        assert "YAML" in str(exc_info.value) or "syntax" in str(exc_info.value).lower()

    def test_schema_validation_failure_skips_invalid(self, tmp_path: Path, caplog):
        """Test that schema validation failures skip invalid templates."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    # Valid action
                    {
                        "id": "valid_action",
                        "label": "Valid",
                        "icon": "check",
                        "category": "calculate",
                        "prompt_template": "Valid {value}",
                    },
                    # Invalid action - missing required fields
                    {
                        "id": "invalid_action",
                        # Missing label, icon, category, prompt_template
                    },
                ]
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        actions = service.get_actions_for_domain("tax", "fiscal")
        # Only valid action should be loaded
        assert len(actions) == 1
        assert actions[0].id == "valid_action"

    def test_duplicate_id_warning(self, tmp_path: Path, caplog):
        """Test that duplicate action IDs log a warning."""
        import logging

        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    {
                        "id": "duplicate_id",
                        "label": "First",
                        "icon": "one",
                        "category": "calculate",
                        "prompt_template": "First {value}",
                    },
                    {
                        "id": "duplicate_id",
                        "label": "Second",
                        "icon": "two",
                        "category": "calculate",
                        "prompt_template": "Second {value}",
                    },
                ]
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        with caplog.at_level(logging.WARNING):
            service = ActionTemplateService(templates_path=tmp_path)
            service.load_templates()

        # Should have logged a warning about duplicate
        assert any("duplicate" in record.message.lower() for record in caplog.records)

        # Last definition wins
        actions = service.get_actions_for_domain("tax", "fiscal")
        # Both are loaded but warning is issued
        assert len(actions) >= 1

    def test_empty_directory(self, tmp_path: Path):
        """Test handling of empty templates directory."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        assert service.get_actions_for_domain("any", "any") == []

    def test_empty_actions_list(self, tmp_path: Path):
        """Test handling of empty actions list in template."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [],  # Empty list
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        actions = service.get_actions_for_domain("tax", "fiscal")
        assert actions == []


class TestActionTemplateServiceValidation:
    """Test template validation functionality."""

    def test_validate_templates_returns_errors(self, tmp_path: Path):
        """Test that validation returns list of errors."""
        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    {
                        "id": "missing_fields",
                        # Missing required fields
                    }
                ]
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        errors = service._validate_templates(yaml_content)

        assert len(errors) > 0
        assert any("label" in error.lower() or "required" in error.lower() for error in errors)


class TestInteractiveQuestionTemplateLoading:
    """Test loading of interactive question templates."""

    def test_load_question_templates(self, tmp_path: Path):
        """Test loading interactive question templates."""
        from app.services.action_template_service import ActionTemplateService

        questions_dir = tmp_path / "interactive_questions"
        questions_dir.mkdir(parents=True)

        yaml_content = {
            "questions": {
                "irpef_tipo": {
                    "id": "irpef_tipo",
                    "text": "Per quale contribuente?",
                    "question_type": "single_choice",
                    "options": [
                        {"id": "dipendente", "label": "Dipendente"},
                        {"id": "autonomo", "label": "Autonomo"},
                    ],
                }
            }
        }
        (questions_dir / "calculations.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        question = service.get_question("irpef_tipo")
        assert question is not None
        assert question.id == "irpef_tipo"
        assert question.text == "Per quale contribuente?"
        assert len(question.options) == 2

    def test_question_not_found(self, tmp_path: Path):
        """Test graceful handling when question not found."""
        from app.services.action_template_service import ActionTemplateService

        questions_dir = tmp_path / "interactive_questions"
        questions_dir.mkdir(parents=True)

        yaml_content = {
            "questions": {
                "existing": {
                    "id": "existing",
                    "text": "Question?",
                    "question_type": "single_choice",
                    "options": [
                        {"id": "a", "label": "A"},
                        {"id": "b", "label": "B"},
                    ],
                }
            }
        }
        (questions_dir / "test.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        question = service.get_question("nonexistent")
        assert question is None

    def test_load_question_with_leads_to(self, tmp_path: Path):
        """Test loading question with leads_to references."""
        from app.services.action_template_service import ActionTemplateService

        questions_dir = tmp_path / "interactive_questions"
        questions_dir.mkdir(parents=True)

        yaml_content = {
            "questions": {
                "first": {
                    "id": "first",
                    "text": "First question?",
                    "question_type": "single_choice",
                    "options": [
                        {"id": "opt1", "label": "Option 1", "leads_to": "second"},
                        {"id": "opt2", "label": "Option 2"},
                    ],
                },
                "second": {
                    "id": "second",
                    "text": "Second question?",
                    "question_type": "single_choice",
                    "options": [
                        {"id": "a", "label": "A"},
                        {"id": "b", "label": "B"},
                    ],
                },
            }
        }
        (questions_dir / "test.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        question = service.get_question("first")
        assert question is not None
        assert question.options[0].leads_to == "second"


class TestActionTemplateServiceAdditionalEdgeCases:
    """Additional edge case tests for coverage."""

    def test_empty_yaml_file(self, tmp_path: Path, caplog):
        """Test handling of empty YAML file."""
        import logging

        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        # Write empty file (None when parsed)
        (templates_dir / "empty.yaml").write_text("")

        with caplog.at_level(logging.WARNING):
            service = ActionTemplateService(templates_path=tmp_path)
            service.load_templates()

        # Should log warning about empty file
        assert any("empty" in record.message.lower() for record in caplog.records)
        # Should not raise error
        assert service.get_actions_for_domain("any", "any") == []

    def test_default_path_initialization(self):
        """Test that default path is set correctly when None is passed."""
        from app.services.action_template_service import ActionTemplateService

        service = ActionTemplateService(templates_path=None)
        assert service.templates_path is not None
        assert "templates" in str(service.templates_path)

    def test_missing_actions_directory_warning(self, tmp_path: Path, caplog):
        """Test warning when suggested_actions directory does not exist."""
        import logging

        from app.services.action_template_service import ActionTemplateService

        with caplog.at_level(logging.WARNING):
            service = ActionTemplateService(templates_path=tmp_path)
            service.load_templates()

        # Should log warning about missing directory
        assert any(
            "not_found" in record.message.lower() or "action" in record.message.lower() for record in caplog.records
        )

    def test_missing_questions_directory_warning(self, tmp_path: Path, caplog):
        """Test warning when interactive_questions directory does not exist."""
        import logging

        from app.services.action_template_service import ActionTemplateService

        # Create only actions dir, not questions dir
        actions_dir = tmp_path / "suggested_actions"
        actions_dir.mkdir(parents=True)

        with caplog.at_level(logging.WARNING):
            service = ActionTemplateService(templates_path=tmp_path)
            service.load_templates()

        # Should log warning about missing questions directory
        assert any(
            "question" in record.message.lower() or "not_found" in record.message.lower() for record in caplog.records
        )

    def test_question_without_questions_key(self, tmp_path: Path):
        """Test handling YAML file without 'questions' key."""
        from app.services.action_template_service import ActionTemplateService

        questions_dir = tmp_path / "interactive_questions"
        questions_dir.mkdir(parents=True)

        # Write YAML without 'questions' key
        (questions_dir / "invalid.yaml").write_text("other_key: value")

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        # Should not error, just have no questions
        assert service.get_question("any") is None

    def test_invalid_question_yaml_syntax(self, tmp_path: Path):
        """Test that invalid YAML in questions raises ConfigurationError."""
        from app.services.action_template_service import ActionTemplateService, ConfigurationError

        questions_dir = tmp_path / "interactive_questions"
        questions_dir.mkdir(parents=True)

        # Write invalid YAML
        (questions_dir / "invalid.yaml").write_text("questions: [unclosed")

        service = ActionTemplateService(templates_path=tmp_path)

        with pytest.raises(ConfigurationError) as exc_info:
            service.load_templates()

        assert "YAML" in str(exc_info.value) or "syntax" in str(exc_info.value).lower()

    def test_question_parsing_exception(self, tmp_path: Path, caplog):
        """Test handling of exception during question parsing."""
        import logging

        from app.services.action_template_service import ActionTemplateService

        questions_dir = tmp_path / "interactive_questions"
        questions_dir.mkdir(parents=True)

        # Create question with invalid structure that causes exception in parsing
        yaml_content = {
            "questions": {
                "invalid_q": {
                    "id": "invalid_q",
                    "text": "Test?",
                    "question_type": "single_choice",
                    "options": "not_a_list",  # Should be a list
                }
            }
        }
        import yaml

        (questions_dir / "invalid.yaml").write_text(yaml.dump(yaml_content))

        with caplog.at_level(logging.ERROR):
            service = ActionTemplateService(templates_path=tmp_path)
            service.load_templates()

        # Should log error about question validation
        assert any(
            "question" in record.message.lower() or "error" in record.message.lower() for record in caplog.records
        )
        # Question should not be loaded
        assert service.get_question("invalid_q") is None

    def test_action_with_invalid_category_enum(self, tmp_path: Path, caplog):
        """Test handling of action with invalid category value."""
        import logging

        import yaml

        from app.services.action_template_service import ActionTemplateService

        templates_dir = tmp_path / "suggested_actions"
        templates_dir.mkdir(parents=True)

        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    {
                        "id": "invalid_category_action",
                        "label": "Test",
                        "icon": "test",
                        "category": "invalid_category_value",  # Invalid enum value
                        "prompt_template": "Test {value}",
                    }
                ]
            },
        }
        (templates_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        with caplog.at_level(logging.ERROR):
            service = ActionTemplateService(templates_path=tmp_path)
            service.load_templates()

        # Should log error about invalid category
        assert any(
            "category" in record.message.lower() or "invalid" in record.message.lower() for record in caplog.records
        )
        # Action should not be loaded
        actions = service.get_actions_for_domain("tax", "fiscal")
        assert len(actions) == 0

    def test_question_with_all_optional_fields(self, tmp_path: Path):
        """Test loading question with all optional fields filled."""
        import yaml

        from app.services.action_template_service import ActionTemplateService

        questions_dir = tmp_path / "interactive_questions"
        questions_dir.mkdir(parents=True)

        yaml_content = {
            "questions": {
                "full_question": {
                    "id": "full_question",
                    "trigger_query": "calcola.*irpef",
                    "text": "Full question?",
                    "question_type": "multi_choice",
                    "options": [
                        {
                            "id": "opt1",
                            "label": "Option 1",
                            "icon": "icon1",
                            "leads_to": "next_q",
                            "requires_input": True,
                        },
                        {"id": "opt2", "label": "Option 2"},
                    ],
                    "allow_custom_input": True,
                    "custom_input_placeholder": "Enter value",
                    "prefilled_params": {"reddito": "50000"},
                }
            }
        }
        (questions_dir / "full.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        question = service.get_question("full_question")
        assert question is not None
        assert question.trigger_query == "calcola.*irpef"
        assert question.allow_custom_input is True
        assert question.custom_input_placeholder == "Enter value"
        assert question.prefilled_params == {"reddito": "50000"}
        assert question.options[0].icon == "icon1"
        assert question.options[0].requires_input is True


class TestActionTemplateServiceIntegration:
    """Integration tests for the complete service."""

    def test_full_workflow(self, tmp_path: Path):
        """Test complete workflow with actions and questions."""
        from app.services.action_template_service import ActionTemplateService

        # Create actions directory
        actions_dir = tmp_path / "suggested_actions"
        actions_dir.mkdir(parents=True)

        # Create questions directory
        questions_dir = tmp_path / "interactive_questions"
        questions_dir.mkdir(parents=True)

        # Create action templates
        tax_yaml = {
            "domain": "tax",
            "actions": {
                "fiscal_calculation": [
                    {
                        "id": "calculate_irpef",
                        "label": "Calcola IRPEF",
                        "icon": "calculate",
                        "category": "calculate",
                        "prompt_template": "Calcola IRPEF",
                    }
                ]
            },
        }
        (actions_dir / "tax.yaml").write_text(yaml.dump(tax_yaml))

        # Create question templates
        questions_yaml = {
            "questions": {
                "irpef_tipo": {
                    "id": "irpef_tipo",
                    "text": "Tipo contribuente?",
                    "question_type": "single_choice",
                    "options": [
                        {"id": "a", "label": "A"},
                        {"id": "b", "label": "B"},
                    ],
                }
            }
        }
        (questions_dir / "calculations.yaml").write_text(yaml.dump(questions_yaml))

        # Test service
        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        # Verify actions loaded
        actions = service.get_actions_for_domain("tax", "fiscal_calculation")
        assert len(actions) == 1

        # Verify questions loaded
        question = service.get_question("irpef_tipo")
        assert question is not None

    def test_all_templates_json_serializable(self, tmp_path: Path):
        """Test that all loaded templates can be serialized to JSON."""
        import json

        from app.services.action_template_service import ActionTemplateService

        actions_dir = tmp_path / "suggested_actions"
        actions_dir.mkdir(parents=True)

        yaml_content = {
            "domain": "tax",
            "actions": {
                "fiscal": [
                    {
                        "id": "action1",
                        "label": "Action 1",
                        "icon": "icon1",
                        "category": "calculate",
                        "prompt_template": "Template {value}",
                        "requires_input": True,
                        "input_placeholder": "Enter value",
                        "input_type": "number",
                    }
                ]
            },
        }
        (actions_dir / "tax.yaml").write_text(yaml.dump(yaml_content))

        service = ActionTemplateService(templates_path=tmp_path)
        service.load_templates()

        actions = service.get_actions_for_domain("tax", "fiscal")

        # Should be JSON serializable
        for action in actions:
            json_str = json.dumps(action.model_dump())
            assert json_str is not None
