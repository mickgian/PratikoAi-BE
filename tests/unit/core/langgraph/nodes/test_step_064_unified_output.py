"""TDD Tests for Phase 9: Step 64 Unified JSON Output with Reasoning.

DEV-214: Update Step 64 for Unified JSON Output with Reasoning.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 90%+ for new code.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.langgraph.nodes.step_064__llm_call import (
    _apply_source_hierarchy,
    _extract_json_from_content,
    _fallback_to_text,
    _parse_unified_response,
    node_step_64,
)

# Sample valid JSON response from LLM
VALID_JSON_RESPONSE = """{
  "reasoning": {
    "tema_identificato": "Aliquote IVA per beni ordinari",
    "fonti_utilizzate": ["Art. 16 DPR 633/72", "Circolare AdE 12/E/2024"],
    "elementi_chiave": ["Aliquota ordinaria 22%", "Aliquote ridotte 10%, 5%, 4%"],
    "conclusione": "L'aliquota IVA ordinaria in Italia è del 22%"
  },
  "answer": "L'aliquota IVA ordinaria in Italia è del 22%. Esistono anche aliquote ridotte del 10%, 5% e 4% per specifiche categorie di beni e servizi.",
  "sources_cited": [
    {
      "ref": "Art. 16 DPR 633/72",
      "relevance": "principale",
      "url": null
    },
    {
      "ref": "Circolare AdE n. 12/E del 2024",
      "relevance": "supporto",
      "url": null
    }
  ],
  "suggested_actions": [
    {
      "id": "action_calcola_iva",
      "label": "Calcola IVA applicabile",
      "icon": "calculator",
      "prompt": "Calcola l'importo IVA per una fattura di 1000 euro con aliquota al 22%",
      "source_basis": "Art. 16 DPR 633/72"
    }
  ]
}"""

# JSON response in markdown code block
MARKDOWN_JSON_RESPONSE = """Ecco la mia risposta:

```json
{
  "reasoning": {
    "tema_identificato": "Test",
    "fonti_utilizzate": ["Fonte 1"],
    "elementi_chiave": ["Elemento 1"],
    "conclusione": "Conclusione test"
  },
  "answer": "Risposta test in markdown",
  "sources_cited": [{"ref": "Legge 123/2020", "relevance": "principale", "url": null}],
  "suggested_actions": []
}
```

Spero di esserti stato utile!"""


@pytest.fixture
def base_state():
    """Create base RAG state for testing."""
    return {
        "messages": [],
        "user_message": "Qual è l'aliquota IVA?",
        "request_id": "test-request-123",
        "routing_decision": {"route": "technical_research"},
    }


@pytest.fixture
def mock_orchestrator_response():
    """Create mock orchestrator response with LLM content."""
    return {
        "llm_call_successful": True,
        "response": {"content": VALID_JSON_RESPONSE},
    }


class TestParseUnifiedResponse:
    """Test _parse_unified_response function."""

    def test_parses_valid_json(self):
        """Valid JSON should be parsed correctly."""
        result = _parse_unified_response(VALID_JSON_RESPONSE)

        assert result is not None
        assert "reasoning" in result
        assert "answer" in result
        assert "sources_cited" in result
        assert "suggested_actions" in result

    def test_parses_json_in_markdown_block(self):
        """JSON in markdown code block should be extracted and parsed."""
        result = _parse_unified_response(MARKDOWN_JSON_RESPONSE)

        assert result is not None
        assert result["answer"] == "Risposta test in markdown"

    def test_returns_none_for_invalid_json(self):
        """Invalid JSON should return None."""
        result = _parse_unified_response("This is not JSON at all")
        assert result is None

    def test_returns_none_for_empty_content(self):
        """Empty content should return None."""
        result = _parse_unified_response("")
        assert result is None

    def test_returns_none_for_none_content(self):
        """None content should return None."""
        result = _parse_unified_response(None)
        assert result is None

    def test_parses_partial_json(self):
        """Partial JSON with missing fields should parse available fields."""
        partial_json = '{"answer": "Just an answer", "reasoning": null}'
        result = _parse_unified_response(partial_json)

        assert result is not None
        assert result["answer"] == "Just an answer"


class TestExtractJsonFromContent:
    """Test _extract_json_from_content function."""

    def test_extracts_json_from_markdown_block(self):
        """Should extract JSON from ```json ... ``` blocks."""
        result = _extract_json_from_content(MARKDOWN_JSON_RESPONSE)

        assert result is not None
        assert "answer" in result

    def test_extracts_raw_json(self):
        """Should extract raw JSON objects."""
        result = _extract_json_from_content(VALID_JSON_RESPONSE)

        assert result is not None
        assert result["answer"] is not None

    def test_returns_none_for_no_json(self):
        """Should return None if no valid JSON found."""
        result = _extract_json_from_content("Plain text without any JSON")
        assert result is None

    def test_handles_json_with_extra_text(self):
        """Should extract JSON even with extra text before/after."""
        content = 'Some preamble text {"answer": "test"} and trailing text'
        result = _extract_json_from_content(content)

        assert result is not None
        assert result["answer"] == "test"

    def test_handles_truncated_json(self):
        """Should handle truncated/incomplete JSON gracefully."""
        truncated = '{"answer": "incomplete'
        result = _extract_json_from_content(truncated)
        assert result is None


class TestFallbackToText:
    """Test _fallback_to_text function."""

    def test_returns_content_as_answer(self):
        """Should use full content as answer."""
        content = "This is a plain text response"
        state = {"request_id": "test"}

        result = _fallback_to_text(content, state)

        assert result["answer"] == content

    def test_returns_empty_lists_for_optional_fields(self):
        """Should return empty lists for sources and actions."""
        content = "Plain response"
        state = {"request_id": "test"}

        result = _fallback_to_text(content, state)

        assert result["sources_cited"] == []
        assert result["suggested_actions"] == []

    def test_returns_none_reasoning(self):
        """Should return None for reasoning."""
        content = "Plain response"
        state = {"request_id": "test"}

        result = _fallback_to_text(content, state)

        assert result["reasoning"] is None


class TestApplySourceHierarchy:
    """Test _apply_source_hierarchy function."""

    def test_sorts_by_hierarchy(self):
        """Sources should be sorted by legal hierarchy (highest first)."""
        sources = [
            {"ref": "Circolare AdE 12/E/2024", "relevance": "supporto"},
            {"ref": "Legge 123/2020", "relevance": "principale"},
            {"ref": "DPR 633/72", "relevance": "principale"},
        ]

        result = _apply_source_hierarchy(sources)

        # Legge should be first, then DPR/Decreto, then Circolare
        assert result[0]["ref"] == "Legge 123/2020"
        assert result[1]["ref"] == "DPR 633/72"
        assert result[2]["ref"] == "Circolare AdE 12/E/2024"

    def test_adds_hierarchy_rank(self):
        """Should add hierarchy_rank field to each source."""
        sources = [{"ref": "Legge 123/2020", "relevance": "principale"}]

        result = _apply_source_hierarchy(sources)

        assert "hierarchy_rank" in result[0]
        assert result[0]["hierarchy_rank"] == 1  # Legge is rank 1

    def test_legge_ranked_highest(self):
        """Legge should have the highest rank (1)."""
        sources = [{"ref": "Legge 123/2020", "relevance": "principale"}]
        result = _apply_source_hierarchy(sources)
        assert result[0]["hierarchy_rank"] == 1

    def test_decreto_ranked_second(self):
        """Decreto/DPR/D.Lgs should have rank 2."""
        sources = [
            {"ref": "D.Lgs. 81/2008", "relevance": "principale"},
            {"ref": "DPR 633/72", "relevance": "principale"},
        ]
        result = _apply_source_hierarchy(sources)
        assert all(s["hierarchy_rank"] == 2 for s in result)

    def test_circolare_ranked_third(self):
        """Circolare should have rank 3."""
        sources = [{"ref": "Circolare AdE 12/E/2024", "relevance": "supporto"}]
        result = _apply_source_hierarchy(sources)
        assert result[0]["hierarchy_rank"] == 3

    def test_interpello_ranked_fourth(self):
        """Interpello/Risposta should have rank 4."""
        sources = [{"ref": "Interpello 456/2023", "relevance": "supporto"}]
        result = _apply_source_hierarchy(sources)
        assert result[0]["hierarchy_rank"] == 4

    def test_unknown_ranked_last(self):
        """Unknown sources should have rank 99."""
        sources = [{"ref": "Some random document", "relevance": "supporto"}]
        result = _apply_source_hierarchy(sources)
        assert result[0]["hierarchy_rank"] == 99

    def test_handles_empty_list(self):
        """Should handle empty source list."""
        result = _apply_source_hierarchy([])
        assert result == []


class TestStep64ParsesJsonResponse:
    """Test that Step 64 parses JSON responses correctly."""

    @pytest.mark.asyncio
    async def test_step64_extracts_answer(self, base_state, mock_orchestrator_response):
        """answer field should be extracted from JSON response."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_64(base_state)

            # The answer should be in the messages
            messages = result.get("messages", [])
            assert any("22%" in msg.get("content", "") for msg in messages if msg.get("role") == "assistant")

    @pytest.mark.asyncio
    async def test_step64_stores_reasoning_trace(self, base_state, mock_orchestrator_response):
        """reasoning_trace should be stored in state."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_64(base_state)

            assert "reasoning_trace" in result
            assert result["reasoning_trace"] is not None
            assert "tema_identificato" in result["reasoning_trace"]

    @pytest.mark.asyncio
    async def test_step64_stores_sources_cited(self, base_state, mock_orchestrator_response):
        """sources_cited should be stored in state with hierarchy."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_64(base_state)

            assert "sources_cited" in result
            assert isinstance(result["sources_cited"], list)
            # Should have hierarchy_rank added
            if result["sources_cited"]:
                assert "hierarchy_rank" in result["sources_cited"][0]

    @pytest.mark.asyncio
    async def test_step64_stores_suggested_actions(self, base_state, mock_orchestrator_response):
        """suggested_actions should be stored in state."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_64(base_state)

            assert "suggested_actions" in result
            assert isinstance(result["suggested_actions"], list)

    @pytest.mark.asyncio
    async def test_step64_sets_actions_source(self, base_state, mock_orchestrator_response):
        """actions_source should be set to 'unified_llm' for parsed JSON."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_64(base_state)

            assert result.get("actions_source") == "unified_llm"

    @pytest.mark.asyncio
    async def test_step64_sets_reasoning_type(self, base_state, mock_orchestrator_response):
        """reasoning_type should be set to 'cot' for Chain of Thought."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_64(base_state)

            assert result.get("reasoning_type") == "cot"


class TestStep64FallbackToText:
    """Test Step 64 fallback behavior when JSON parsing fails."""

    @pytest.mark.asyncio
    async def test_step64_fallback_on_plain_text(self, base_state):
        """Should fallback to text when response is not JSON."""
        mock_response = {
            "llm_call_successful": True,
            "response": {"content": "This is a plain text response without JSON."},
        }

        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await node_step_64(base_state)

            # Should mark for fallback
            assert result.get("actions_source") == "fallback_needed"

    @pytest.mark.asyncio
    async def test_step64_fallback_empty_response(self, base_state):
        """Should handle empty response gracefully."""
        mock_response = {
            "llm_call_successful": True,
            "response": {"content": ""},
        }

        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await node_step_64(base_state)

            # Should not crash, llm success depends on content
            assert "llm" in result


class TestStep64SourceHierarchyOrdering:
    """Test that sources are ordered by hierarchy in Step 64."""

    @pytest.mark.asyncio
    async def test_step64_sources_sorted_by_hierarchy(self, base_state):
        """Sources in response should be sorted by legal hierarchy."""
        json_with_unsorted_sources = json.dumps(
            {
                "reasoning": {"tema_identificato": "Test"},
                "answer": "Test answer",
                "sources_cited": [
                    {"ref": "Interpello 123/2023", "relevance": "supporto"},
                    {"ref": "Legge 456/2020", "relevance": "principale"},
                    {"ref": "Circolare 789/2024", "relevance": "supporto"},
                ],
                "suggested_actions": [],
            }
        )

        mock_response = {
            "llm_call_successful": True,
            "response": {"content": json_with_unsorted_sources},
        }

        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await node_step_64(base_state)

            sources = result.get("sources_cited", [])
            if len(sources) >= 3:
                # Legge should be first
                assert "Legge" in sources[0]["ref"]
                # Circolare should be second
                assert "Circolare" in sources[1]["ref"]
                # Interpello should be last
                assert "Interpello" in sources[2]["ref"]


class TestStep64ExistingBehaviorPreserved:
    """Test that existing Step 64 behavior is preserved."""

    @pytest.mark.asyncio
    async def test_step64_still_stores_llm_response(self, base_state, mock_orchestrator_response):
        """Step 64 should still store llm response in state."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_64(base_state)

            assert "llm" in result
            assert result["llm"].get("success") is True

    @pytest.mark.asyncio
    async def test_step64_still_adds_assistant_message(self, base_state, mock_orchestrator_response):
        """Step 64 should still add assistant message to messages list."""
        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_orchestrator_response,
        ):
            result = await node_step_64(base_state)

            messages = result.get("messages", [])
            assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
            assert len(assistant_msgs) > 0

    @pytest.mark.asyncio
    async def test_step64_deanonymization_still_works(self, base_state):
        """Deanonymization should still work after JSON parsing changes."""
        mock_response = {
            "llm_call_successful": True,
            "response": {
                "content": '{"answer": "Il codice fiscale [CF_ABC123] appartiene a...", "reasoning": null, "sources_cited": [], "suggested_actions": []}'
            },
        }
        base_state["privacy"] = {"document_deanonymization_map": {"[CF_ABC123]": "RSSMRA80A01H501U"}}

        with patch(
            "app.core.langgraph.nodes.step_064__llm_call.step_64__llmcall",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await node_step_64(base_state)

            # The placeholder should be replaced with original value
            messages = result.get("messages", [])
            assistant_content = next((m["content"] for m in messages if m.get("role") == "assistant"), "")
            assert "RSSMRA80A01H501U" in assistant_content
            assert "[CF_ABC123]" not in assistant_content
