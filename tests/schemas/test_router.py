"""TDD Tests for DEV-186: RouterDecision Schema and Constants.

Tests for Pydantic models and enums for LLM router per Section 13.4.4.
"""

import json

import pytest
from pydantic import ValidationError


class TestRoutingCategory:
    """Tests for RoutingCategory enum."""

    def test_routing_category_values(self):
        """Test all 5 routing categories are defined."""
        from app.schemas.router import RoutingCategory

        assert RoutingCategory.CHITCHAT == "chitchat"
        assert RoutingCategory.THEORETICAL_DEFINITION == "theoretical_definition"
        assert RoutingCategory.TECHNICAL_RESEARCH == "technical_research"
        assert RoutingCategory.CALCULATOR == "calculator"
        assert RoutingCategory.NORMATIVE_REFERENCE == "normative_reference"

    def test_routing_category_count(self):
        """Test exactly 5 routing categories exist."""
        from app.schemas.router import RoutingCategory

        assert len(RoutingCategory) == 5

    def test_routing_category_is_string_enum(self):
        """Test RoutingCategory is a string enum."""
        from app.schemas.router import RoutingCategory

        assert isinstance(RoutingCategory.CHITCHAT, str)
        assert RoutingCategory.CHITCHAT.value == "chitchat"


class TestExtractedEntity:
    """Tests for ExtractedEntity model."""

    def test_extracted_entity_creation(self):
        """Test creating ExtractedEntity with all fields."""
        from app.schemas.router import ExtractedEntity

        entity = ExtractedEntity(
            text="Legge 104/1992",
            type="legge",
            confidence=0.95,
        )

        assert entity.text == "Legge 104/1992"
        assert entity.type == "legge"
        assert entity.confidence == 0.95

    def test_extracted_entity_valid_types(self):
        """Test ExtractedEntity with various entity types."""
        from app.schemas.router import ExtractedEntity

        # Test different entity types
        types = ["legge", "articolo", "ente", "data"]
        for entity_type in types:
            entity = ExtractedEntity(
                text="test",
                type=entity_type,
                confidence=0.8,
            )
            assert entity.type == entity_type

    def test_extracted_entity_confidence_bounds(self):
        """Test ExtractedEntity confidence must be 0.0-1.0."""
        from app.schemas.router import ExtractedEntity

        # Valid bounds
        entity_low = ExtractedEntity(text="test", type="legge", confidence=0.0)
        assert entity_low.confidence == 0.0

        entity_high = ExtractedEntity(text="test", type="legge", confidence=1.0)
        assert entity_high.confidence == 1.0

        # Invalid bounds
        with pytest.raises(ValidationError):
            ExtractedEntity(text="test", type="legge", confidence=-0.1)

        with pytest.raises(ValidationError):
            ExtractedEntity(text="test", type="legge", confidence=1.1)

    def test_extracted_entity_json_serialization(self):
        """Test ExtractedEntity JSON serialization."""
        from app.schemas.router import ExtractedEntity

        entity = ExtractedEntity(
            text="Art. 2 comma 1",
            type="articolo",
            confidence=0.85,
        )

        json_str = entity.model_dump_json()
        data = json.loads(json_str)

        assert data["text"] == "Art. 2 comma 1"
        assert data["type"] == "articolo"
        assert data["confidence"] == 0.85


class TestRouterDecision:
    """Tests for RouterDecision model."""

    def test_router_decision_valid_creation(self):
        """Test creating RouterDecision with all fields."""
        from app.schemas.router import ExtractedEntity, RouterDecision, RoutingCategory

        decision = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.92,
            reasoning="Query asks about P.IVA forfettaria opening procedure",
            entities=[ExtractedEntity(text="P.IVA forfettaria", type="ente", confidence=0.9)],
            requires_freshness=False,
            suggested_sources=["agenzia_entrate", "inps"],
        )

        assert decision.route == RoutingCategory.TECHNICAL_RESEARCH
        assert decision.confidence == 0.92
        assert decision.reasoning == "Query asks about P.IVA forfettaria opening procedure"
        assert len(decision.entities) == 1
        assert decision.requires_freshness is False
        assert decision.suggested_sources == ["agenzia_entrate", "inps"]

    def test_router_decision_confidence_bounds(self):
        """Test RouterDecision confidence must be 0.0-1.0."""
        from app.schemas.router import RouterDecision, RoutingCategory

        # Valid bounds
        decision_low = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            confidence=0.0,
            reasoning="Low confidence",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )
        assert decision_low.confidence == 0.0

        decision_high = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            confidence=1.0,
            reasoning="High confidence",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )
        assert decision_high.confidence == 1.0

        # Invalid bounds
        with pytest.raises(ValidationError):
            RouterDecision(
                route=RoutingCategory.CHITCHAT,
                confidence=-0.1,
                reasoning="Invalid",
                entities=[],
                requires_freshness=False,
                suggested_sources=[],
            )

        with pytest.raises(ValidationError):
            RouterDecision(
                route=RoutingCategory.CHITCHAT,
                confidence=1.5,
                reasoning="Invalid",
                entities=[],
                requires_freshness=False,
                suggested_sources=[],
            )

    def test_router_decision_empty_entities(self):
        """Test RouterDecision with empty entities list."""
        from app.schemas.router import RouterDecision, RoutingCategory

        decision = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            confidence=0.95,
            reasoning="Simple greeting",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        assert decision.entities == []

    def test_router_decision_multiple_entities(self):
        """Test RouterDecision with multiple entities."""
        from app.schemas.router import ExtractedEntity, RouterDecision, RoutingCategory

        entities = [
            ExtractedEntity(text="Legge 104", type="legge", confidence=0.9),
            ExtractedEntity(text="Art. 3", type="articolo", confidence=0.85),
            ExtractedEntity(text="INPS", type="ente", confidence=0.95),
        ]

        decision = RouterDecision(
            route=RoutingCategory.NORMATIVE_REFERENCE,
            confidence=0.88,
            reasoning="Query references specific law and article",
            entities=entities,
            requires_freshness=False,
            suggested_sources=["normattiva"],
        )

        assert len(decision.entities) == 3

    def test_needs_retrieval_computed_technical_research(self):
        """Test needs_retrieval is True for TECHNICAL_RESEARCH."""
        from app.schemas.router import RouterDecision, RoutingCategory

        decision = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.9,
            reasoning="Technical query",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        assert decision.needs_retrieval is True

    def test_needs_retrieval_computed_normative_reference(self):
        """Test needs_retrieval is True for NORMATIVE_REFERENCE."""
        from app.schemas.router import RouterDecision, RoutingCategory

        decision = RouterDecision(
            route=RoutingCategory.NORMATIVE_REFERENCE,
            confidence=0.9,
            reasoning="Normative reference query",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        assert decision.needs_retrieval is True

    def test_needs_retrieval_computed_theoretical_definition(self):
        """Test needs_retrieval is True for THEORETICAL_DEFINITION."""
        from app.schemas.router import RouterDecision, RoutingCategory

        decision = RouterDecision(
            route=RoutingCategory.THEORETICAL_DEFINITION,
            confidence=0.9,
            reasoning="Definition query",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        assert decision.needs_retrieval is True

    def test_needs_retrieval_computed_chitchat(self):
        """Test needs_retrieval is False for CHITCHAT."""
        from app.schemas.router import RouterDecision, RoutingCategory

        decision = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            confidence=0.95,
            reasoning="Greeting",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        assert decision.needs_retrieval is False

    def test_needs_retrieval_computed_calculator(self):
        """Test needs_retrieval is False for CALCULATOR."""
        from app.schemas.router import RouterDecision, RoutingCategory

        decision = RouterDecision(
            route=RoutingCategory.CALCULATOR,
            confidence=0.9,
            reasoning="Calculation request",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        assert decision.needs_retrieval is False

    def test_router_decision_json_serialization(self):
        """Test RouterDecision JSON serialization."""
        from app.schemas.router import ExtractedEntity, RouterDecision, RoutingCategory

        decision = RouterDecision(
            route=RoutingCategory.TECHNICAL_RESEARCH,
            confidence=0.88,
            reasoning="Test reasoning",
            entities=[ExtractedEntity(text="Test", type="legge", confidence=0.9)],
            requires_freshness=True,
            suggested_sources=["source1", "source2"],
        )

        json_str = decision.model_dump_json()
        data = json.loads(json_str)

        assert data["route"] == "technical_research"
        assert data["confidence"] == 0.88
        assert data["reasoning"] == "Test reasoning"
        assert len(data["entities"]) == 1
        assert data["requires_freshness"] is True
        assert data["suggested_sources"] == ["source1", "source2"]
        assert data["needs_retrieval"] is True

    def test_router_decision_from_json(self):
        """Test RouterDecision deserialization from JSON."""
        from app.schemas.router import RouterDecision

        json_data = {
            "route": "normative_reference",
            "confidence": 0.95,
            "reasoning": "References specific law",
            "entities": [{"text": "Legge 104", "type": "legge", "confidence": 0.9}],
            "requires_freshness": False,
            "suggested_sources": ["normattiva"],
        }

        decision = RouterDecision.model_validate(json_data)

        assert decision.route.value == "normative_reference"
        assert decision.confidence == 0.95
        assert len(decision.entities) == 1
        assert decision.needs_retrieval is True

    def test_router_decision_invalid_route(self):
        """Test RouterDecision rejects invalid route."""
        from app.schemas.router import RouterDecision

        with pytest.raises(ValidationError):
            RouterDecision(
                route="invalid_route",
                confidence=0.9,
                reasoning="Test",
                entities=[],
                requires_freshness=False,
                suggested_sources=[],
            )

    def test_router_decision_requires_reasoning(self):
        """Test RouterDecision requires reasoning field."""
        from app.schemas.router import RouterDecision, RoutingCategory

        with pytest.raises(ValidationError):
            RouterDecision(
                route=RoutingCategory.CHITCHAT,
                confidence=0.9,
                # missing reasoning
                entities=[],
                requires_freshness=False,
                suggested_sources=[],
            )

    def test_router_decision_default_confidence(self):
        """Test RouterDecision uses default confidence when not provided."""
        from app.schemas.router import RouterDecision, RoutingCategory

        # Note: Based on task spec, missing confidence should default to 0.5
        decision = RouterDecision(
            route=RoutingCategory.CHITCHAT,
            reasoning="Test",
            entities=[],
            requires_freshness=False,
            suggested_sources=[],
        )

        assert decision.confidence == 0.5
