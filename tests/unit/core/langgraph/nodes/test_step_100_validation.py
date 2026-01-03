"""TDD tests for Step 100 Action Validation with Golden Loop.

DEV-218: Tests written FIRST per TDD methodology.
Tests cover validation integration, regeneration triggering, and state storage.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Mock database service BEFORE importing any app modules
# =============================================================================
_mock_db_service = MagicMock()
_mock_db_service.engine = MagicMock()
_mock_db_service.get_session = MagicMock()
_mock_db_module = MagicMock()
_mock_db_module.database_service = _mock_db_service
_mock_db_module.DatabaseService = MagicMock(return_value=_mock_db_service)
sys.modules.setdefault("app.services.database", _mock_db_module)


# =============================================================================
# Test Fixtures
# =============================================================================
@pytest.fixture
def valid_action():
    """Create a valid action that passes validation."""
    return {
        "id": "action_1",
        "label": "Calcola IVA al 22%",  # 8-40 chars, specific
        "icon": "calculator",
        "prompt": "Calcola l'IVA al 22% sull'importo di €15.000",  # >25 chars
    }


@pytest.fixture
def valid_actions():
    """Create 3 valid actions that pass validation."""
    return [
        {
            "id": "action_1",
            "label": "Calcola IVA al 22%",
            "icon": "calculator",
            "prompt": "Calcola l'IVA al 22% sull'importo di €15.000",
        },
        {
            "id": "action_2",
            "label": "Verifica scadenza F24 marzo",
            "icon": "calendar",
            "prompt": "Controlla la scadenza del versamento F24 per marzo 2024",
        },
        {
            "id": "action_3",
            "label": "Stima contributi INPS",
            "icon": "euro",
            "prompt": "Stima i contributi INPS per il regime forfettario 2024",
        },
    ]


@pytest.fixture
def invalid_actions():
    """Create actions that will fail validation."""
    return [
        {
            "id": "bad_1",
            "label": "Calcola",  # Too short (<8 chars)
            "icon": "calculator",
            "prompt": "Calcola l'importo richiesto per il pagamento",
        },
        {
            "id": "bad_2",
            "label": "Contatta un commercialista",  # Forbidden pattern
            "icon": "phone",
            "prompt": "Contatta un commercialista per assistenza specializzata",
        },
    ]


@pytest.fixture
def kb_sources_metadata():
    """Sample KB source metadata for validation."""
    return [
        {
            "source_id": "src_1",
            "ref": "Circolare INPS 45/2024",
            "key_topics": ["contributi", "forfettario", "INPS"],
            "relevant_paragraph": "Il contributo minimo per i forfettari è pari a €4.200 annui.",
        },
        {
            "source_id": "src_2",
            "ref": "DPR 633/1972",
            "key_topics": ["IVA", "aliquote", "22%"],
            "relevant_paragraph": "L'aliquota ordinaria IVA è fissata al 22%.",
        },
    ]


@pytest.fixture
def base_state(valid_actions, kb_sources_metadata):
    """Base state for validation tests."""
    return {
        "request_id": "test-validation-001",
        "user_query": "Calcola l'IVA sulla fattura",
        "routing_decision": {"route": "technical_research", "confidence": 0.9},
        "suggested_actions": valid_actions,  # From Step 64
        "actions_source": "llm_structured",
        "kb_sources_metadata": kb_sources_metadata,
        "llm": {"response": {"content": "Ecco il calcolo dell'IVA al 22%..."}},
    }


# =============================================================================
# TestStep100ValidatesActions - Validation Called
# =============================================================================
class TestStep100ValidatesActions:
    """Test that Step 100 calls ActionValidator on actions."""

    @pytest.mark.asyncio
    async def test_step100_calls_validate_batch(self, base_state):
        """Step 100 calls action_validator.validate_batch()."""
        from app.services.action_validator import BatchValidationResult

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.return_value = BatchValidationResult(
                validated_actions=base_state["suggested_actions"],
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            )

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            await node_step_100(base_state)

            mock_validator.validate_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_step100_passes_actions_to_validator(self, base_state):
        """Validator receives the suggested_actions from state."""
        from app.services.action_validator import BatchValidationResult

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.return_value = BatchValidationResult(
                validated_actions=base_state["suggested_actions"],
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            )

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            await node_step_100(base_state)

            call_args = mock_validator.validate_batch.call_args
            actions_arg = call_args[1]["actions"] if "actions" in call_args[1] else call_args[0][0]
            assert actions_arg == base_state["suggested_actions"]


# =============================================================================
# TestStep100UsesKbSources - KB Sources Accessed
# =============================================================================
class TestStep100UsesKbSources:
    """Test that Step 100 uses kb_sources_metadata for validation."""

    @pytest.mark.asyncio
    async def test_step100_passes_kb_sources_to_validator(self, base_state):
        """Validator receives kb_sources_metadata from state."""
        from app.services.action_validator import BatchValidationResult

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.return_value = BatchValidationResult(
                validated_actions=base_state["suggested_actions"],
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            )

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            await node_step_100(base_state)

            call_args = mock_validator.validate_batch.call_args
            # Check kb_sources is passed
            kb_sources_arg = call_args[1].get("kb_sources") or (call_args[0][2] if len(call_args[0]) > 2 else None)
            assert kb_sources_arg == base_state["kb_sources_metadata"]

    @pytest.mark.asyncio
    async def test_step100_handles_missing_kb_sources(self, base_state):
        """Step 100 handles missing kb_sources_metadata gracefully."""
        del base_state["kb_sources_metadata"]

        from app.services.action_validator import BatchValidationResult

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.return_value = BatchValidationResult(
                validated_actions=base_state["suggested_actions"],
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            )

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(base_state)

            # Should not raise, should handle gracefully
            assert "proactivity" in result


# =============================================================================
# TestStep100TriggersRegeneration - Golden Loop
# =============================================================================
class TestStep100TriggersRegeneration:
    """Test that Step 100 triggers ActionRegenerator when <2 valid actions."""

    @pytest.mark.asyncio
    async def test_step100_triggers_regeneration_when_lt_2_valid(self, base_state, valid_action, invalid_actions):
        """Regeneration triggered when fewer than 2 actions are valid."""
        from app.services.action_validator import BatchValidationResult

        # Only 1 valid action (need >=2)
        validation_result = BatchValidationResult(
            validated_actions=[valid_action],
            rejected_count=2,
            rejection_log=[(invalid_actions[0], "Too short"), (invalid_actions[1], "Forbidden")],
            quality_score=0.33,
        )

        with (
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator,
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_regenerator") as mock_regenerator,
        ):
            mock_validator.validate_batch.return_value = validation_result
            mock_regenerator.regenerate_if_needed = AsyncMock(return_value=[valid_action, valid_action])

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            await node_step_100(base_state)

            mock_regenerator.regenerate_if_needed.assert_called_once()

    @pytest.mark.asyncio
    async def test_step100_uses_regenerated_actions(self, base_state, valid_action, invalid_actions):
        """Regenerated actions are returned when regeneration succeeds."""
        from app.services.action_validator import BatchValidationResult

        validation_result = BatchValidationResult(
            validated_actions=[valid_action],
            rejected_count=2,
            rejection_log=[(invalid_actions[0], "Too short"), (invalid_actions[1], "Forbidden")],
            quality_score=0.33,
        )

        regenerated_actions = [
            {
                "id": "regen_1",
                "label": "Calcola IVA specifica",
                "icon": "calculator",
                "prompt": "Calcola l'IVA al 22%",
            },
            {
                "id": "regen_2",
                "label": "Verifica aliquota base",
                "icon": "search",
                "prompt": "Verifica l'aliquota base",
            },
        ]

        with (
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator,
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_regenerator") as mock_regenerator,
        ):
            mock_validator.validate_batch.return_value = validation_result
            mock_regenerator.regenerate_if_needed = AsyncMock(return_value=regenerated_actions)

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(base_state)

            actions = result["proactivity"]["post_response"]["actions"]
            assert actions == regenerated_actions
            assert result["proactivity"]["post_response"]["source"] == "regenerated"

    @pytest.mark.asyncio
    async def test_step100_no_regeneration_when_2_or_more_valid(self, base_state, valid_actions):
        """No regeneration when 2 or more actions are valid."""
        from app.services.action_validator import BatchValidationResult

        # 2 valid actions - no regeneration needed
        validation_result = BatchValidationResult(
            validated_actions=valid_actions[:2],
            rejected_count=1,
            rejection_log=[(valid_actions[2], "Some reason")],
            quality_score=0.67,
        )

        with (
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator,
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_regenerator") as mock_regenerator,
        ):
            mock_validator.validate_batch.return_value = validation_result
            mock_regenerator.regenerate_if_needed = AsyncMock()

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            await node_step_100(base_state)

            mock_regenerator.regenerate_if_needed.assert_not_called()


# =============================================================================
# TestStep100StoresValidationResult - State Storage
# =============================================================================
class TestStep100StoresValidationResult:
    """Test that Step 100 stores validation results in state."""

    @pytest.mark.asyncio
    async def test_step100_stores_action_validation_result(self, base_state, valid_actions):
        """Validation result is stored in state."""
        from app.services.action_validator import BatchValidationResult

        validation_result = BatchValidationResult(
            validated_actions=valid_actions,
            rejected_count=0,
            rejection_log=[],
            quality_score=1.0,
        )

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.return_value = validation_result

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(base_state)

            assert "action_validation_result" in result
            avr = result["action_validation_result"]
            assert avr["validated_count"] == 3
            assert avr["rejected_count"] == 0
            assert avr["quality_score"] == 1.0
            assert avr["regeneration_used"] is False

    @pytest.mark.asyncio
    async def test_step100_stores_regeneration_flag(self, base_state, valid_action, invalid_actions):
        """Regeneration flag is stored in validation result."""
        from app.services.action_validator import BatchValidationResult

        validation_result = BatchValidationResult(
            validated_actions=[valid_action],
            rejected_count=2,
            rejection_log=[(invalid_actions[0], "Too short"), (invalid_actions[1], "Forbidden")],
            quality_score=0.33,
        )

        regenerated = [valid_action, valid_action]

        with (
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator,
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_regenerator") as mock_regenerator,
        ):
            mock_validator.validate_batch.return_value = validation_result
            mock_regenerator.regenerate_if_needed = AsyncMock(return_value=regenerated)

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(base_state)

            assert result["action_validation_result"]["regeneration_used"] is True


# =============================================================================
# TestStep100StoresValidationLog - Rejection Log Storage
# =============================================================================
class TestStep100StoresValidationLog:
    """Test that Step 100 stores rejection log in state."""

    @pytest.mark.asyncio
    async def test_step100_stores_actions_validation_log(self, base_state, valid_actions, invalid_actions):
        """Rejection log is stored in state."""
        from app.services.action_validator import BatchValidationResult

        validation_result = BatchValidationResult(
            validated_actions=valid_actions[:2],
            rejected_count=2,
            rejection_log=[
                (invalid_actions[0], "Label too short"),
                (invalid_actions[1], "Forbidden pattern"),
            ],
            quality_score=0.5,
        )

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.return_value = validation_result

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(base_state)

            assert "actions_validation_log" in result
            log = result["actions_validation_log"]
            assert len(log) == 2
            assert "Calcola: Label too short" in log
            assert "Contatta un commercialista: Forbidden pattern" in log


# =============================================================================
# TestStep100ReturnsValidatedActions - Filtered Actions
# =============================================================================
class TestStep100ReturnsValidatedActions:
    """Test that Step 100 returns validated actions."""

    @pytest.mark.asyncio
    async def test_step100_returns_only_validated_actions(self, base_state, valid_actions, invalid_actions):
        """Only validated actions are returned."""
        from app.services.action_validator import BatchValidationResult

        # Mix valid and invalid
        base_state["suggested_actions"] = [valid_actions[0], invalid_actions[0], valid_actions[1]]

        validation_result = BatchValidationResult(
            validated_actions=[valid_actions[0], valid_actions[1]],
            rejected_count=1,
            rejection_log=[(invalid_actions[0], "Too short")],
            quality_score=0.67,
        )

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.return_value = validation_result

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(base_state)

            actions = result["proactivity"]["post_response"]["actions"]
            assert len(actions) == 2
            assert actions[0]["id"] == "action_1"
            assert actions[1]["id"] == "action_2"


# =============================================================================
# TestStep100NoActionsFromStep64 - Fallback
# =============================================================================
class TestStep100NoActionsFromStep64:
    """Test fallback when Step 64 provides no actions."""

    @pytest.mark.asyncio
    async def test_step100_handles_empty_suggested_actions(self, base_state):
        """Step 100 handles empty suggested_actions from Step 64."""
        base_state["suggested_actions"] = []
        base_state["actions_source"] = "fallback_needed"

        from app.services.action_validator import BatchValidationResult

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            # Empty validation result
            mock_validator.validate_batch.return_value = BatchValidationResult(
                validated_actions=[],
                rejected_count=0,
                rejection_log=[],
                quality_score=0.0,
            )

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(base_state)

            # Should still have proactivity structure
            assert "proactivity" in result

    @pytest.mark.asyncio
    async def test_step100_uses_fallback_source_when_empty(self, base_state):
        """Fallback source is used when Step 64 provides empty actions."""
        base_state["suggested_actions"] = []
        base_state["actions_source"] = "fallback_needed"

        from app.services.action_validator import BatchValidationResult

        with (
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator,
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_regenerator") as mock_regenerator,
        ):
            mock_validator.validate_batch.return_value = BatchValidationResult(
                validated_actions=[],
                rejected_count=0,
                rejection_log=[],
                quality_score=0.0,
            )

            fallback_actions = [
                {"id": "fallback_1", "label": "Approfondisci tema", "icon": "search", "prompt": "Dimmi di più"},
            ]
            mock_regenerator.regenerate_if_needed = AsyncMock(return_value=fallback_actions)

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(base_state)

            source = result["proactivity"]["post_response"]["source"]
            assert source in ("regenerated", "fallback")


# =============================================================================
# TestStep100AllActionsValid - No Regeneration
# =============================================================================
class TestStep100AllActionsValid:
    """Test behavior when all actions are valid."""

    @pytest.mark.asyncio
    async def test_step100_returns_all_valid_actions(self, base_state, valid_actions):
        """All valid actions are returned when no regeneration needed."""
        from app.services.action_validator import BatchValidationResult

        validation_result = BatchValidationResult(
            validated_actions=valid_actions,
            rejected_count=0,
            rejection_log=[],
            quality_score=1.0,
        )

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.return_value = validation_result

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(base_state)

            actions = result["proactivity"]["post_response"]["actions"]
            assert len(actions) == 3
            assert result["action_validation_result"]["quality_score"] == 1.0


# =============================================================================
# TestStep100ValidationServiceFails - Graceful Degradation
# =============================================================================
class TestStep100ValidationServiceFails:
    """Test graceful degradation when validation service fails."""

    @pytest.mark.asyncio
    async def test_step100_handles_validator_exception(self, base_state):
        """Step 100 handles validator exception gracefully."""
        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.side_effect = Exception("Validator error")

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            # Should not raise
            result = await node_step_100(base_state)

            # Should return proactivity with empty or original actions
            assert "proactivity" in result

    @pytest.mark.asyncio
    async def test_step100_handles_regenerator_exception(self, base_state, valid_action, invalid_actions):
        """Step 100 handles regenerator exception gracefully."""
        from app.services.action_validator import BatchValidationResult

        validation_result = BatchValidationResult(
            validated_actions=[valid_action],
            rejected_count=2,
            rejection_log=[(invalid_actions[0], "Too short"), (invalid_actions[1], "Forbidden")],
            quality_score=0.33,
        )

        with (
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator,
            patch("app.core.langgraph.nodes.step_100__post_proactivity.action_regenerator") as mock_regenerator,
        ):
            mock_validator.validate_batch.return_value = validation_result
            mock_regenerator.regenerate_if_needed = AsyncMock(side_effect=Exception("Regenerator error"))

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            # Should not raise
            result = await node_step_100(base_state)

            # Should return proactivity with original validated actions
            assert "proactivity" in result


# =============================================================================
# TestStep100SkipLogic - Preserve Skip Behavior
# =============================================================================
class TestStep100SkipLogic:
    """Test that skip logic is preserved with validation."""

    @pytest.mark.asyncio
    async def test_step100_skips_validation_for_pre_proactivity(self, base_state):
        """Validation not called when pre-proactivity already triggered."""
        base_state["skip_rag_for_proactivity"] = True

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            await node_step_100(base_state)

            mock_validator.validate_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_step100_skips_validation_for_chitchat(self, base_state):
        """Validation not called for chitchat routes."""
        base_state["routing_decision"]["route"] = "chitchat"

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            await node_step_100(base_state)

            mock_validator.validate_batch.assert_not_called()


# =============================================================================
# TestStep100IntegrationWithExistingFlow - Backward Compatibility
# =============================================================================
class TestStep100IntegrationWithExistingFlow:
    """Test that DEV-218 changes work with existing Step 100 flows."""

    @pytest.mark.asyncio
    async def test_step100_still_handles_document_templates(self, kb_sources_metadata):
        """Document template actions still work with validation."""
        from app.services.action_validator import BatchValidationResult

        state = {
            "request_id": "test-compat-001",
            "user_query": "Analizza questo F24",
            "attachments": [{"document_type": "f24", "id": "doc-001"}],
            "llm": {"response": {"content": "Ho analizzato il tuo F24..."}},
            "kb_sources_metadata": kb_sources_metadata,
        }

        # Mock to allow template actions to pass through
        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            # Template actions should be validated too
            mock_validator.validate_batch.return_value = BatchValidationResult(
                validated_actions=[
                    {"id": "codes", "label": "Verifica codici tributo", "icon": "🔍", "prompt": "Verifica i codici"},
                    {"id": "deadline", "label": "Scadenza pagamento", "icon": "📅", "prompt": "Controlla scadenza"},
                ],
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            )

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(state)

            proactivity = result.get("proactivity", {})
            post_response = proactivity.get("post_response", {})
            actions = post_response.get("actions", [])

            assert len(actions) > 0

    @pytest.mark.asyncio
    async def test_step100_still_handles_verdetto_extraction(self, kb_sources_metadata):
        """VERDETTO extraction still works with validation."""
        from app.services.action_validator import BatchValidationResult

        state = {
            "request_id": "test-compat-002",
            "user_query": "Parlami della rottamazione",
            "routing_decision": {"route": "technical_research", "confidence": 0.9},
            "parsed_synthesis": {
                "verdetto": {
                    "azione_consigliata": "Verificare i requisiti per la rottamazione quinquies",
                    "scadenza": "30 aprile 2024 - Termine adesione",
                },
            },
            "llm": {"response": {"content": "..."}},
            "kb_sources_metadata": kb_sources_metadata,
        }

        with patch("app.core.langgraph.nodes.step_100__post_proactivity.action_validator") as mock_validator:
            mock_validator.validate_batch.return_value = BatchValidationResult(
                validated_actions=[
                    {
                        "id": "azione_consigliata",
                        "label": "Segui consiglio",
                        "icon": "✅",
                        "prompt": "Verificare requisiti",
                    },
                    {"id": "scadenza", "label": "Verifica scadenza", "icon": "📅", "prompt": "30 aprile 2024"},
                ],
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            )

            from app.core.langgraph.nodes.step_100__post_proactivity import node_step_100

            result = await node_step_100(state)

            actions = result["proactivity"]["post_response"]["actions"]
            assert len(actions) >= 1


# =============================================================================
# TestStep100ResponseContext - Context Building
# =============================================================================
class TestStep100ResponseContext:
    """Test ResponseContext building for regeneration."""

    def test_build_response_context_helper(self, base_state):
        """Test _build_response_context helper function directly."""
        from app.core.langgraph.nodes.step_100__post_proactivity import (
            _build_response_context,
        )
        from app.services.action_regenerator import ResponseContext

        context = _build_response_context(base_state)

        # Verify context was built correctly
        assert isinstance(context, ResponseContext)
        assert context.kb_sources == base_state["kb_sources_metadata"]
        assert len(context.main_topic) > 0
        assert context.primary_source["ref"] == "Circolare INPS 45/2024"

    def test_extract_values_from_text(self):
        """Test _extract_values_from_text helper function."""
        from app.core.langgraph.nodes.step_100__post_proactivity import (
            _extract_values_from_text,
        )

        text = "L'IVA al 22% su €15.000 deve essere versata entro il 16/03/2024"
        values = _extract_values_from_text(text)

        assert "22%" in values
        assert any("€" in v or "15" in v for v in values)
        assert "16/03/2024" in values

    def test_get_response_content_from_dict(self):
        """Test _get_response_content with dict response."""
        from app.core.langgraph.nodes.step_100__post_proactivity import (
            _get_response_content,
        )

        state = {"llm": {"response": {"content": "Test content"}}}
        content = _get_response_content(state)

        assert content == "Test content"

    def test_get_response_content_from_string(self):
        """Test _get_response_content with string response."""
        from app.core.langgraph.nodes.step_100__post_proactivity import (
            _get_response_content,
        )

        state = {"llm": {"response": "Direct string response"}}
        content = _get_response_content(state)

        assert content == "Direct string response"
