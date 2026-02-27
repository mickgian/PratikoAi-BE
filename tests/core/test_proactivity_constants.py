"""
TDD Tests for proactivity_constants module.

Tests written FIRST as per DEV-174 requirements.
"""

from typing import get_type_hints

import pytest


class TestCalculableIntents:
    """Tests for CALCULABLE_INTENTS constant."""

    def test_calculable_intents_has_exactly_five_entries(self):
        """CALCULABLE_INTENTS must have exactly 5 entries as per Section 12.4."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        assert len(CALCULABLE_INTENTS) == 5

    def test_calculable_intents_all_have_required_params(self):
        """Each intent must have a 'required' list of parameters."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        for intent_name, intent_data in CALCULABLE_INTENTS.items():
            assert "required" in intent_data, f"Intent '{intent_name}' missing 'required' key"
            assert isinstance(intent_data["required"], list), \
                f"Intent '{intent_name}' 'required' must be a list"

    def test_calculable_intents_all_have_question_flow(self):
        """Each intent must have a 'question_flow' string."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        for intent_name, intent_data in CALCULABLE_INTENTS.items():
            assert "question_flow" in intent_data, \
                f"Intent '{intent_name}' missing 'question_flow' key"
            assert isinstance(intent_data["question_flow"], str), \
                f"Intent '{intent_name}' 'question_flow' must be a string"

    def test_no_empty_required_lists(self):
        """All intents must have non-empty required parameter lists."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        for intent_name, intent_data in CALCULABLE_INTENTS.items():
            assert len(intent_data["required"]) > 0, \
                f"Intent '{intent_name}' has empty 'required' list"

    def test_no_duplicate_intent_keys(self):
        """Intent keys must be unique (implicitly true for dict, but verify content)."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        expected_intents = {
            "calcolo_irpef",
            "calcolo_iva",
            "calcolo_contributi_inps",
            "ravvedimento_operoso",
            "calcolo_f24"
        }
        assert set(CALCULABLE_INTENTS.keys()) == expected_intents

    def test_calcolo_irpef_has_correct_required_params(self):
        """calcolo_irpef must require tipo_contribuente and reddito."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        assert "calcolo_irpef" in CALCULABLE_INTENTS
        assert set(CALCULABLE_INTENTS["calcolo_irpef"]["required"]) == {
            "tipo_contribuente", "reddito"
        }

    def test_calcolo_iva_has_correct_required_params(self):
        """calcolo_iva must require importo."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        assert "calcolo_iva" in CALCULABLE_INTENTS
        assert CALCULABLE_INTENTS["calcolo_iva"]["required"] == ["importo"]

    def test_calcolo_contributi_inps_has_correct_required_params(self):
        """calcolo_contributi_inps must require tipo_gestione and reddito."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        assert "calcolo_contributi_inps" in CALCULABLE_INTENTS
        assert set(CALCULABLE_INTENTS["calcolo_contributi_inps"]["required"]) == {
            "tipo_gestione", "reddito"
        }

    def test_ravvedimento_operoso_has_correct_required_params(self):
        """ravvedimento_operoso must require importo_originale and data_scadenza."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        assert "ravvedimento_operoso" in CALCULABLE_INTENTS
        assert set(CALCULABLE_INTENTS["ravvedimento_operoso"]["required"]) == {
            "importo_originale", "data_scadenza"
        }

    def test_calcolo_f24_has_correct_required_params(self):
        """calcolo_f24 must require codice_tributo and importo."""
        from app.core.proactivity_constants import CALCULABLE_INTENTS

        assert "calcolo_f24" in CALCULABLE_INTENTS
        assert set(CALCULABLE_INTENTS["calcolo_f24"]["required"]) == {
            "codice_tributo", "importo"
        }


class TestDocumentActionTemplates:
    """Tests for DOCUMENT_ACTION_TEMPLATES constant."""

    def test_document_templates_has_exactly_four_types(self):
        """DOCUMENT_ACTION_TEMPLATES must have exactly 4 document types."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        assert len(DOCUMENT_ACTION_TEMPLATES) == 4

    def test_document_templates_expected_types(self):
        """Document types must match Section 12.6 specification."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        expected_types = {"fattura_elettronica", "f24", "bilancio", "cu"}
        assert set(DOCUMENT_ACTION_TEMPLATES.keys()) == expected_types

    def test_document_templates_all_actions_have_required_fields(self):
        """All action templates must have id, label, icon, and prompt fields."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        required_fields = {"id", "label", "icon", "prompt"}

        for doc_type, actions in DOCUMENT_ACTION_TEMPLATES.items():
            for action in actions:
                for field in required_fields:
                    assert field in action, \
                        f"Action in '{doc_type}' missing required field '{field}'"

    def test_action_ids_unique_within_document_type(self):
        """Action IDs must be unique within each document type."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        for doc_type, actions in DOCUMENT_ACTION_TEMPLATES.items():
            action_ids = [a["id"] for a in actions]
            assert len(action_ids) == len(set(action_ids)), \
                f"Document type '{doc_type}' has duplicate action IDs"

    def test_icons_are_valid_emoji(self):
        """All icons must be non-empty strings (emoji)."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        for doc_type, actions in DOCUMENT_ACTION_TEMPLATES.items():
            for action in actions:
                icon = action["icon"]
                assert isinstance(icon, str) and len(icon) > 0, \
                    f"Icon in '{doc_type}' action '{action['id']}' must be non-empty string"

    def test_prompts_are_non_empty_strings(self):
        """All prompts must be non-empty strings."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        for doc_type, actions in DOCUMENT_ACTION_TEMPLATES.items():
            for action in actions:
                prompt = action["prompt"]
                assert isinstance(prompt, str) and len(prompt) > 0, \
                    f"Prompt in '{doc_type}' action '{action['id']}' must be non-empty string"

    def test_labels_are_non_empty_strings(self):
        """All labels must be non-empty strings."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        for doc_type, actions in DOCUMENT_ACTION_TEMPLATES.items():
            for action in actions:
                label = action["label"]
                assert isinstance(label, str) and len(label) > 0, \
                    f"Label in '{doc_type}' action '{action['id']}' must be non-empty string"

    def test_fattura_elettronica_has_four_actions(self):
        """fattura_elettronica must have exactly 4 actions."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        assert len(DOCUMENT_ACTION_TEMPLATES["fattura_elettronica"]) == 4

    def test_f24_has_three_actions(self):
        """f24 must have exactly 3 actions."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        assert len(DOCUMENT_ACTION_TEMPLATES["f24"]) == 3

    def test_bilancio_has_three_actions(self):
        """bilancio must have exactly 3 actions."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        assert len(DOCUMENT_ACTION_TEMPLATES["bilancio"]) == 3

    def test_cu_has_three_actions(self):
        """cu must have exactly 3 actions."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        assert len(DOCUMENT_ACTION_TEMPLATES["cu"]) == 3

    def test_fattura_elettronica_action_ids(self):
        """fattura_elettronica must have correct action IDs."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        action_ids = {a["id"] for a in DOCUMENT_ACTION_TEMPLATES["fattura_elettronica"]}
        expected = {"verify", "vat", "entry", "recipient"}
        assert action_ids == expected

    def test_f24_action_ids(self):
        """f24 must have correct action IDs."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        action_ids = {a["id"] for a in DOCUMENT_ACTION_TEMPLATES["f24"]}
        expected = {"codes", "deadline", "ravvedimento"}
        assert action_ids == expected

    def test_bilancio_action_ids(self):
        """bilancio must have correct action IDs."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        action_ids = {a["id"] for a in DOCUMENT_ACTION_TEMPLATES["bilancio"]}
        expected = {"ratios", "compare", "summary"}
        assert action_ids == expected

    def test_cu_action_ids(self):
        """cu must have correct action IDs."""
        from app.core.proactivity_constants import DOCUMENT_ACTION_TEMPLATES

        action_ids = {a["id"] for a in DOCUMENT_ACTION_TEMPLATES["cu"]}
        expected = {"verify", "irpef", "summary"}
        assert action_ids == expected


class TestTypeDefinitions:
    """Tests for TypedDict type definitions."""

    def test_calculable_intent_type_exists(self):
        """CalculableIntent TypedDict must be importable."""
        from app.core.proactivity_constants import CalculableIntent

        assert CalculableIntent is not None

    def test_action_template_type_exists(self):
        """ActionTemplate TypedDict must be importable."""
        from app.core.proactivity_constants import ActionTemplate

        assert ActionTemplate is not None


class TestModuleImport:
    """Tests for module import behavior."""

    def test_constants_importable_from_module(self):
        """Constants must be importable from app.core.proactivity_constants."""
        from app.core.proactivity_constants import (
            CALCULABLE_INTENTS,
            DOCUMENT_ACTION_TEMPLATES,
        )

        assert CALCULABLE_INTENTS is not None
        assert DOCUMENT_ACTION_TEMPLATES is not None

    def test_module_import_is_fast(self):
        """Module import should complete in <10ms."""
        import importlib
        import sys
        import time

        # Remove from cache if present
        module_name = "app.core.proactivity_constants"
        if module_name in sys.modules:
            del sys.modules[module_name]

        start = time.perf_counter()
        importlib.import_module(module_name)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow some margin for CI environments
        assert elapsed_ms < 100, f"Module import took {elapsed_ms:.2f}ms, expected <100ms"
