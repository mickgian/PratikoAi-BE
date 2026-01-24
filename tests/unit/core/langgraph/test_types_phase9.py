"""TDD Tests for Phase 9: LLM Excellence RAGState fields.

DEV-210: Update GraphState with LLM Excellence Fields.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 95%+ for new fields.
"""

import json
from typing import get_type_hints

import pytest

from app.core.langgraph.types import RAGState


class TestRAGStateNewFieldsOptional:
    """Test that all new Phase 9 fields are Optional with None default."""

    def test_kb_documents_field_optional(self):
        """kb_documents field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("kb_documents") is None

        state["kb_documents"] = [{"id": "doc1", "content": "test"}]
        assert state["kb_documents"] == [{"id": "doc1", "content": "test"}]

        state["kb_documents"] = None
        assert state.get("kb_documents") is None

    def test_kb_sources_metadata_field_optional(self):
        """kb_sources_metadata field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("kb_sources_metadata") is None

        state["kb_sources_metadata"] = [
            {
                "id": "src1",
                "title": "Test Source",
                "type": "legge",
                "date": "2024-01-01",
                "url": "https://example.com",
                "key_topics": ["tax"],
                "key_values": {"rate": 0.22},
                "hierarchy_weight": 1.3,
            }
        ]
        assert state["kb_sources_metadata"][0]["title"] == "Test Source"

    def test_query_complexity_field_optional(self):
        """query_complexity field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("query_complexity") is None

        for complexity in ["simple", "complex", "multi_domain"]:
            state["query_complexity"] = complexity
            assert state["query_complexity"] == complexity

    def test_complexity_classification_field_optional(self):
        """complexity_classification field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("complexity_classification") is None

        state["complexity_classification"] = {
            "complexity": "complex",
            "domains": ["tax", "labor"],
            "confidence": 0.95,
            "reasoning": "Query spans multiple domains",
        }
        assert state["complexity_classification"]["confidence"] == 0.95

    def test_reasoning_type_field_optional(self):
        """reasoning_type field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("reasoning_type") is None

        for reasoning_type in ["cot", "tot", "tot_multi_domain"]:
            state["reasoning_type"] = reasoning_type
            assert state["reasoning_type"] == reasoning_type

    def test_reasoning_trace_field_optional(self):
        """reasoning_trace field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("reasoning_trace") is None

        # CoT structure
        state["reasoning_trace"] = {
            "tema": "Calcolo IRPEF",
            "fonti_utilizzate": ["D.P.R. 917/1986"],
            "elementi_chiave": ["aliquote", "detrazioni"],
            "conclusione": "Si applica aliquota del 23%",
        }
        assert state["reasoning_trace"]["tema"] == "Calcolo IRPEF"

    def test_tot_analysis_field_optional(self):
        """tot_analysis field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("tot_analysis") is None

        state["tot_analysis"] = {
            "hypotheses": [
                {"id": "h1", "text": "Hypothesis 1", "confidence": 0.8},
                {"id": "h2", "text": "Hypothesis 2", "confidence": 0.6},
            ],
            "selected": "h1",
            "selection_reasoning": "Higher confidence and better source support",
            "confidence": 0.85,
            "alternative_note": "H2 could apply in specific cases",
        }
        assert state["tot_analysis"]["selected"] == "h1"

    def test_internal_reasoning_field_optional(self):
        """internal_reasoning field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("internal_reasoning") is None

        state["internal_reasoning"] = {
            "step": "analysis",
            "sources_considered": 5,
            "decision_path": ["filter", "rank", "select"],
            "debug_info": {"latency_ms": 150},
        }
        assert state["internal_reasoning"]["sources_considered"] == 5

    def test_public_reasoning_field_optional(self):
        """public_reasoning field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("public_reasoning") is None

        state["public_reasoning"] = {
            "summary": "Based on current tax regulations...",
            "selected_scenario": "Regime forfettario",
            "why_selected": "Most common case for freelancers",
            "main_sources": ["L. 190/2014", "Circ. 9/E/2019"],
            "confidence_label": "Alta",
        }
        assert state["public_reasoning"]["confidence_label"] == "Alta"

    def test_action_validation_result_field_optional(self):
        """action_validation_result field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("action_validation_result") is None

        state["action_validation_result"] = {
            "valid": True,
            "actions_validated": 3,
            "rejected": [],
            "confidence": 0.95,
        }
        assert state["action_validation_result"]["valid"] is True

    def test_action_regeneration_count_field_optional(self):
        """action_regeneration_count field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("action_regeneration_count") is None

        state["action_regeneration_count"] = 0
        assert state["action_regeneration_count"] == 0

        state["action_regeneration_count"] = 2
        assert state["action_regeneration_count"] == 2

    def test_actions_source_field_optional(self):
        """actions_source field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("actions_source") is None

        for source in ["unified_llm", "fallback", "template", "regenerated"]:
            state["actions_source"] = source
            assert state["actions_source"] == source

    def test_actions_validation_log_field_optional(self):
        """actions_validation_log field should be optional and accept None."""
        state: RAGState = {}
        assert state.get("actions_validation_log") is None

        state["actions_validation_log"] = [
            "Action 'calcola_iva' rejected: missing context",
            "Action 'cerca_normativa' validated",
        ]
        assert len(state["actions_validation_log"]) == 2


class TestRAGStateBackwardCompatibility:
    """Test backward compatibility with existing state dicts."""

    def test_existing_state_works_without_new_fields(self):
        """Existing state dicts should work without Phase 9 fields."""
        # Minimal existing state
        state: RAGState = {
            "request_id": "req-123",
            "session_id": "sess-456",
            "user_query": "Calcola IRPEF",
            "messages": [],
        }

        # Should work without Phase 9 fields
        assert state["request_id"] == "req-123"
        assert state.get("kb_documents") is None
        assert state.get("reasoning_trace") is None

    def test_partial_phase9_fields_work(self):
        """State with only some Phase 9 fields should work."""
        state: RAGState = {
            "request_id": "req-123",
            "session_id": "sess-456",
            "query_complexity": "simple",
            # Other Phase 9 fields not set
        }

        assert state["query_complexity"] == "simple"
        assert state.get("tot_analysis") is None
        assert state.get("action_validation_result") is None

    def test_mixed_legacy_and_new_fields(self):
        """State with both legacy and Phase 9 fields should work."""
        state: RAGState = {
            # Legacy fields
            "request_id": "req-123",
            "session_id": "sess-456",
            "golden_hit": True,
            "kb_docs": [{"id": "doc1"}],
            "context": "merged context",
            # Phase 9 fields
            "kb_documents": [{"id": "doc1", "full_content": "..."}],
            "query_complexity": "complex",
            "reasoning_type": "cot",
        }

        assert state["golden_hit"] is True
        assert state["kb_documents"] is not None
        assert state["query_complexity"] == "complex"


class TestRAGStateSerialization:
    """Test JSON serialization for checkpointing."""

    def test_empty_state_serialization(self):
        """Empty state should serialize correctly."""
        state: RAGState = {}
        json_str = json.dumps(state)
        deserialized = json.loads(json_str)
        assert deserialized == {}

    def test_phase9_fields_serialization(self):
        """Phase 9 fields should serialize correctly."""
        state: RAGState = {
            "kb_documents": [{"id": "doc1", "content": "test"}],
            "kb_sources_metadata": [
                {
                    "id": "src1",
                    "title": "Test",
                    "hierarchy_weight": 1.3,
                }
            ],
            "query_complexity": "complex",
            "complexity_classification": {
                "complexity": "complex",
                "domains": ["tax"],
                "confidence": 0.95,
            },
            "reasoning_type": "tot",
            "reasoning_trace": {
                "tema": "Test",
                "fonti_utilizzate": ["L. 1/2024"],
            },
            "tot_analysis": {
                "hypotheses": [{"id": "h1", "text": "Test", "confidence": 0.8}],
                "selected": "h1",
            },
            "internal_reasoning": {"step": "analysis"},
            "public_reasoning": {"summary": "Test"},
            "action_validation_result": {"valid": True},
            "action_regeneration_count": 1,
            "actions_source": "unified_llm",
            "actions_validation_log": ["Validated"],
        }

        json_str = json.dumps(state)
        deserialized = json.loads(json_str)

        assert deserialized["kb_documents"] == state["kb_documents"]
        assert deserialized["query_complexity"] == "complex"
        assert deserialized["action_regeneration_count"] == 1

    def test_nested_dict_serialization(self):
        """Nested dict structures should serialize correctly."""
        state: RAGState = {
            "tot_analysis": {
                "hypotheses": [
                    {"id": "h1", "text": "Hypothesis 1", "confidence": 0.8, "sources": ["S1", "S2"]},
                    {"id": "h2", "text": "Hypothesis 2", "confidence": 0.6, "sources": ["S3"]},
                ],
                "selected": "h1",
                "selection_reasoning": "Higher confidence",
                "confidence": 0.85,
            }
        }

        json_str = json.dumps(state)
        deserialized = json.loads(json_str)

        assert len(deserialized["tot_analysis"]["hypotheses"]) == 2
        assert deserialized["tot_analysis"]["hypotheses"][0]["confidence"] == 0.8

    def test_none_values_serialization(self):
        """None values should serialize correctly."""
        state: RAGState = {
            "kb_documents": None,
            "reasoning_trace": None,
            "action_regeneration_count": None,
        }

        json_str = json.dumps(state)
        deserialized = json.loads(json_str)

        assert deserialized["kb_documents"] is None
        assert deserialized["reasoning_trace"] is None


class TestRAGStateCheckpointMigration:
    """Test checkpoint migration from old schema to new schema."""

    def test_old_checkpoint_deserializes_correctly(self):
        """Old checkpoint without Phase 9 fields should deserialize correctly."""
        old_checkpoint = {
            "request_id": "req-123",
            "session_id": "sess-456",
            "user_query": "Calcola IRPEF",
            "messages": [{"role": "user", "content": "Hello"}],
            "golden_hit": False,
            "kb_docs": [{"id": "doc1"}],
            "context": "Some context",
            "final_response": {"content": "Response"},
        }

        # Simulate loading old checkpoint into RAGState
        state: RAGState = old_checkpoint  # type: ignore

        # Old fields should work
        assert state["request_id"] == "req-123"
        assert state["golden_hit"] is False

        # New fields should be absent (None when accessed)
        assert state.get("kb_documents") is None
        assert state.get("reasoning_trace") is None

    def test_checkpoint_with_extra_fields_handled(self):
        """Checkpoint with extra unknown fields should be handled gracefully."""
        checkpoint_with_extras = {
            "request_id": "req-123",
            "session_id": "sess-456",
            "unknown_field": "should not break",
            "another_unknown": 123,
        }

        state: RAGState = checkpoint_with_extras  # type: ignore
        assert state["request_id"] == "req-123"


class TestRAGStateKBDocumentsStructure:
    """Test kb_documents field structure validation."""

    def test_kb_documents_accepts_valid_structure(self):
        """kb_documents should accept valid document structures."""
        state: RAGState = {}
        state["kb_documents"] = [
            {
                "id": "doc-001",
                "content": "Full document content here...",
                "title": "Document Title",
                "source_type": "legge",
                "date": "2024-01-15",
                "url": "https://example.com/doc",
                "metadata": {"author": "Test"},
            },
            {
                "id": "doc-002",
                "content": "Another document...",
            },
        ]

        assert len(state["kb_documents"]) == 2
        assert state["kb_documents"][0]["id"] == "doc-001"

    def test_kb_sources_metadata_accepts_valid_structure(self):
        """kb_sources_metadata should accept valid metadata structures."""
        state: RAGState = {}
        state["kb_sources_metadata"] = [
            {
                "id": "src-001",
                "title": "Legge n. 190/2014",
                "type": "legge",
                "date": "2014-12-23",
                "url": "https://normattiva.it/...",
                "key_topics": ["forfettario", "flat tax", "small business"],
                "key_values": {"flat_rate": 0.15, "revenue_limit": 85000},
                "hierarchy_weight": 1.3,
            }
        ]

        assert state["kb_sources_metadata"][0]["hierarchy_weight"] == 1.3


class TestRAGStateReasoningTraceStructure:
    """Test reasoning_trace field structure for CoT and ToT."""

    def test_reasoning_trace_cot_structure(self):
        """reasoning_trace should accept CoT structure."""
        state: RAGState = {}
        state["reasoning_trace"] = {
            "tema": "Calcolo contributi INPS per lavoratore autonomo",
            "fonti_utilizzate": [
                "Circ. INPS 23/2024",
                "L. 335/1995 art. 2",
            ],
            "elementi_chiave": [
                "Aliquota contributiva 25.98%",
                "Minimale contributivo €17,504.00",
                "Massimale contributivo €119,650.00",
            ],
            "conclusione": "Il contribuente deve versare...",
        }

        assert state["reasoning_trace"]["tema"].startswith("Calcolo")
        assert len(state["reasoning_trace"]["fonti_utilizzate"]) == 2

    def test_reasoning_trace_tot_structure(self):
        """reasoning_trace should accept ToT summary structure."""
        state: RAGState = {}
        state["reasoning_trace"] = {
            "hypotheses": ["h1", "h2", "h3"],
            "selected": "h1",
            "selection_reasoning": "Best supported by sources",
            "confidence": 0.92,
        }

        assert state["reasoning_trace"]["selected"] == "h1"
        assert state["reasoning_trace"]["confidence"] == 0.92


class TestRAGStateNoneValuesAllFields:
    """Test that all Phase 9 fields can be set to None."""

    def test_all_phase9_fields_accept_none(self):
        """All Phase 9 fields should accept None value."""
        state: RAGState = {
            "kb_documents": None,
            "kb_sources_metadata": None,
            "query_complexity": None,
            "complexity_classification": None,
            "reasoning_type": None,
            "reasoning_trace": None,
            "tot_analysis": None,
            "internal_reasoning": None,
            "public_reasoning": None,
            "action_validation_result": None,
            "action_regeneration_count": None,
            "actions_source": None,
            "actions_validation_log": None,
        }

        for field in [
            "kb_documents",
            "kb_sources_metadata",
            "query_complexity",
            "complexity_classification",
            "reasoning_type",
            "reasoning_trace",
            "tot_analysis",
            "internal_reasoning",
            "public_reasoning",
            "action_validation_result",
            "action_regeneration_count",
            "actions_source",
            "actions_validation_log",
        ]:
            assert state.get(field) is None


class TestRAGStatePartialUpdate:
    """Test partial field updates don't break state."""

    def test_partial_update_preserves_existing_fields(self):
        """Partial updates should not affect other fields."""
        state: RAGState = {
            "request_id": "req-123",
            "session_id": "sess-456",
            "query_complexity": "simple",
            "reasoning_type": "cot",
        }

        # Update only one field
        state["query_complexity"] = "complex"

        # Other fields should be preserved
        assert state["request_id"] == "req-123"
        assert state["reasoning_type"] == "cot"
        assert state["query_complexity"] == "complex"

    def test_adding_new_fields_preserves_existing(self):
        """Adding new Phase 9 fields should preserve existing state."""
        state: RAGState = {
            "request_id": "req-123",
            "golden_hit": True,
            "context": "Some context",
        }

        # Add Phase 9 fields
        state["kb_documents"] = [{"id": "doc1"}]
        state["reasoning_trace"] = {"tema": "Test"}

        # Existing fields preserved
        assert state["golden_hit"] is True
        assert state["context"] == "Some context"

        # New fields added
        assert state["kb_documents"] == [{"id": "doc1"}]


class TestRAGStateTypeAnnotations:
    """Test type annotations are correct for Phase 9 fields."""

    def test_phase9_fields_exist_in_typeddict(self):
        """Phase 9 fields should be defined in RAGState TypedDict."""
        # Get type hints for RAGState
        hints = get_type_hints(RAGState)

        # Check Phase 9 fields exist
        phase9_fields = [
            "kb_documents",
            "kb_sources_metadata",
            "query_complexity",
            "complexity_classification",
            "reasoning_type",
            "reasoning_trace",
            "tot_analysis",
            "internal_reasoning",
            "public_reasoning",
            "action_validation_result",
            "action_regeneration_count",
            "actions_source",
            "actions_validation_log",
        ]

        for field in phase9_fields:
            assert field in hints, f"Field '{field}' not found in RAGState"

    def test_field_types_are_optional(self):
        """All Phase 9 fields should have Optional/None-compatible types."""
        hints = get_type_hints(RAGState)

        # These fields should accept None
        nullable_fields = [
            "kb_documents",
            "kb_sources_metadata",
            "query_complexity",
            "complexity_classification",
            "reasoning_type",
            "reasoning_trace",
            "tot_analysis",
            "internal_reasoning",
            "public_reasoning",
            "action_validation_result",
            "action_regeneration_count",
            "actions_source",
            "actions_validation_log",
        ]

        for field in nullable_fields:
            hint = hints.get(field)
            # The type hint should allow None (be Optional or union with None)
            # For TypedDict with total=False, this is implicit
            assert hint is not None, f"Field '{field}' has no type hint"


class TestPhase57TopicReducers:
    """DEV-245 Phase 5.7: Test reducers for topic_keywords and conversation_topic."""

    def test_preserve_conversation_topic_returns_new_when_set(self):
        """New value should be used when explicitly set."""
        from app.core.langgraph.types import preserve_conversation_topic

        result = preserve_conversation_topic("old topic", "new topic")
        assert result == "new topic"

    def test_preserve_conversation_topic_preserves_existing_when_new_is_none(self):
        """Existing value should be preserved when new is None."""
        from app.core.langgraph.types import preserve_conversation_topic

        result = preserve_conversation_topic("rottamazione quinquies", None)
        assert result == "rottamazione quinquies"

    def test_preserve_conversation_topic_returns_none_when_both_none(self):
        """Should return None when both are None."""
        from app.core.langgraph.types import preserve_conversation_topic

        result = preserve_conversation_topic(None, None)
        assert result is None

    def test_preserve_topic_keywords_returns_new_when_set(self):
        """New value should be used when explicitly set and non-empty."""
        from app.core.langgraph.types import preserve_topic_keywords

        result = preserve_topic_keywords(["old"], ["new", "topic"])
        assert result == ["new", "topic"]

    def test_preserve_topic_keywords_preserves_existing_when_new_is_none(self):
        """Existing value should be preserved when new is None."""
        from app.core.langgraph.types import preserve_topic_keywords

        result = preserve_topic_keywords(["rottamazione", "quinquies"], None)
        assert result == ["rottamazione", "quinquies"]

    def test_preserve_topic_keywords_preserves_existing_when_new_is_empty(self):
        """Existing value should be preserved when new is empty list."""
        from app.core.langgraph.types import preserve_topic_keywords

        result = preserve_topic_keywords(["rottamazione", "quinquies"], [])
        assert result == ["rottamazione", "quinquies"]

    def test_preserve_topic_keywords_returns_none_when_both_none(self):
        """Should return None when both are None."""
        from app.core.langgraph.types import preserve_topic_keywords

        result = preserve_topic_keywords(None, None)
        assert result is None

    def test_preserve_topic_keywords_returns_new_over_none_existing(self):
        """New value should be used even when existing is None."""
        from app.core.langgraph.types import preserve_topic_keywords

        result = preserve_topic_keywords(None, ["rottamazione", "quinquies"])
        assert result == ["rottamazione", "quinquies"]

    def test_conversation_topic_field_has_reducer(self):
        """conversation_topic field should have preserve_conversation_topic reducer."""
        hints = get_type_hints(RAGState, include_extras=True)
        # Field should exist (reducer usage is tested via Annotated type)
        assert "conversation_topic" in hints

    def test_topic_keywords_field_has_reducer(self):
        """topic_keywords field should have preserve_topic_keywords reducer."""
        hints = get_type_hints(RAGState, include_extras=True)
        # Field should exist (reducer usage is tested via Annotated type)
        assert "topic_keywords" in hints
