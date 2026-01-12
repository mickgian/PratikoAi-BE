"""TDD Tests for DEV-188: MultiQueryGeneratorService.

Tests for generating 3 query variants (BM25, Vector, Entity) per Section 13.5.
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.router import ExtractedEntity


class TestQueryVariantsSchema:
    """Tests for QueryVariants dataclass."""

    def test_query_variants_creation(self):
        """Test creating QueryVariants with all fields."""
        from app.services.multi_query_generator import QueryVariants

        variants = QueryVariants(
            bm25_query="tasse 730 reddito dichiarazione",
            vector_query="Come si presenta la dichiarazione dei redditi modello 730?",
            entity_query="modello 730 Agenzia delle Entrate dichiarazione",
            original_query="Come faccio il 730?",
        )

        assert variants.bm25_query == "tasse 730 reddito dichiarazione"
        assert variants.vector_query == "Come si presenta la dichiarazione dei redditi modello 730?"
        assert variants.entity_query == "modello 730 Agenzia delle Entrate dichiarazione"
        assert variants.original_query == "Come faccio il 730?"

    def test_query_variants_has_document_references_field(self):
        """ADR-022: QueryVariants should have document_references field for LLM-identified documents."""
        from app.services.multi_query_generator import QueryVariants

        # Should be able to create with document_references
        variants = QueryVariants(
            bm25_query="rottamazione quinquies definizione agevolata",
            vector_query="Quali sono le disposizioni sulla rottamazione quinquies?",
            entity_query="Legge 199/2025 definizione agevolata",
            original_query="Parlami della rottamazione quinquies",
            document_references=["Legge 199/2025", "LEGGE 30 dicembre 2025, n. 199"],
        )

        assert variants.document_references == ["Legge 199/2025", "LEGGE 30 dicembre 2025, n. 199"]

    def test_query_variants_document_references_optional(self):
        """ADR-022: document_references should be optional (None by default)."""
        from app.services.multi_query_generator import QueryVariants

        # Should work without document_references (backward compatible)
        variants = QueryVariants(
            bm25_query="test query",
            vector_query="test query",
            entity_query="test query",
            original_query="test query",
        )

        assert variants.document_references is None

    def test_query_variants_document_references_empty_list(self):
        """ADR-022: document_references can be an empty list when no documents identified."""
        from app.services.multi_query_generator import QueryVariants

        variants = QueryVariants(
            bm25_query="generic tax question",
            vector_query="generic tax question",
            entity_query="generic tax question",
            original_query="Come funziona il fisco?",
            document_references=[],
        )

        assert variants.document_references == []

    def test_query_variants_all_distinct(self):
        """Test that variants can be distinct."""
        from app.services.multi_query_generator import QueryVariants

        variants = QueryVariants(
            bm25_query="keywords version",
            vector_query="semantic expanded version",
            entity_query="entity focused version",
            original_query="original query",
        )

        # All 4 should be distinct
        all_queries = [
            variants.bm25_query,
            variants.vector_query,
            variants.entity_query,
            variants.original_query,
        ]
        assert len(set(all_queries)) == 4


class TestMultiQueryGeneratorServiceGeneration:
    """Tests for query generation functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 3000
        config.get_temperature.return_value = 0.3
        return config

    @pytest.mark.asyncio
    async def test_generates_3_distinct_queries(self, mock_config):
        """Test that generate() returns 3 distinct query variants."""
        from app.services.multi_query_generator import MultiQueryGeneratorService, QueryVariants

        service = MultiQueryGeneratorService(config=mock_config)

        mock_response = QueryVariants(
            bm25_query="P.IVA forfettaria apertura requisiti procedura",
            vector_query="Quali sono i passaggi per aprire una Partita IVA a regime forfettario?",
            entity_query="P.IVA forfettaria Agenzia Entrate regime agevolato",
            original_query="Come apro P.IVA forfettaria?",
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate("Come apro P.IVA forfettaria?", [])

        assert result.bm25_query != result.vector_query
        assert result.vector_query != result.entity_query
        assert result.bm25_query != result.entity_query
        assert result.original_query == "Come apro P.IVA forfettaria?"

    @pytest.mark.asyncio
    async def test_bm25_contains_keywords(self, mock_config):
        """Test that BM25 query contains relevant keywords."""
        from app.services.multi_query_generator import MultiQueryGeneratorService, QueryVariants

        service = MultiQueryGeneratorService(config=mock_config)

        mock_response = QueryVariants(
            bm25_query="contributi INPS artigiani commercianti 2024 gestione separata",
            vector_query="Qual è l'importo dei contributi previdenziali per artigiani e commercianti?",
            entity_query="INPS contributi artigiani commercianti gestione",
            original_query="Quanto pago di contributi INPS?",
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate("Quanto pago di contributi INPS?", [])

        # BM25 query should contain keywords without question structure
        assert "contributi" in result.bm25_query.lower()
        assert "INPS" in result.bm25_query or "inps" in result.bm25_query.lower()
        # Should not be a full question
        assert "?" not in result.bm25_query

    @pytest.mark.asyncio
    async def test_vector_semantically_expanded(self, mock_config):
        """Test that vector query is semantically expanded."""
        from app.services.multi_query_generator import MultiQueryGeneratorService, QueryVariants

        service = MultiQueryGeneratorService(config=mock_config)

        mock_response = QueryVariants(
            bm25_query="730 scadenza 2024 presentazione",
            vector_query="Qual è la scadenza per la presentazione della dichiarazione dei redditi modello 730 per l'anno fiscale 2024?",
            entity_query="modello 730 scadenza Agenzia Entrate 2024",
            original_query="Scadenza 730?",
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate("Scadenza 730?", [])

        # Vector query should be longer and more detailed than original
        assert len(result.vector_query) > len(result.original_query)
        # Should contain semantic expansion
        assert "dichiarazione" in result.vector_query.lower() or "redditi" in result.vector_query.lower()

    @pytest.mark.asyncio
    async def test_entity_includes_references(self, mock_config):
        """Test that entity query includes extracted legal references."""
        from app.services.multi_query_generator import MultiQueryGeneratorService, QueryVariants

        service = MultiQueryGeneratorService(config=mock_config)

        entities = [
            ExtractedEntity(text="Legge 104", type="legge", confidence=0.95),
            ExtractedEntity(text="Art. 3", type="articolo", confidence=0.9),
        ]

        mock_response = QueryVariants(
            bm25_query="Legge 104 permessi lavoratori disabili handicap",
            vector_query="Quali sono i benefici previsti dalla Legge 104 per i lavoratori con disabilità?",
            entity_query="Legge 104/1992 Art. 3 permessi retribuiti disabilità INPS",
            original_query="Cosa prevede la Legge 104?",
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate("Cosa prevede la Legge 104?", entities)

        # Entity query should include the extracted entities
        assert "Legge 104" in result.entity_query or "104" in result.entity_query
        assert "Art" in result.entity_query or "articolo" in result.entity_query.lower()

    @pytest.mark.asyncio
    async def test_generates_with_no_entities(self, mock_config):
        """Test generation works without entities."""
        from app.services.multi_query_generator import MultiQueryGeneratorService, QueryVariants

        service = MultiQueryGeneratorService(config=mock_config)

        mock_response = QueryVariants(
            bm25_query="tasse reddito imposta",
            vector_query="Come si calcolano le tasse sui redditi?",
            entity_query="imposte reddito IRPEF Agenzia Entrate",
            original_query="Come calcolo le tasse?",
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate("Come calcolo le tasse?", [])

        assert result.bm25_query is not None
        assert result.vector_query is not None
        assert result.entity_query is not None


class TestMultiQueryGeneratorServiceFallback:
    """Tests for fallback behavior."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 3000
        config.get_temperature.return_value = 0.3
        return config

    @pytest.mark.asyncio
    async def test_fallback_to_original_on_error(self, mock_config):
        """Test fallback to original query when LLM fails."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)
        original_query = "Test fallback query"

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM API error")

            result = await service.generate(original_query, [])

        # All variants should be the original query
        assert result.bm25_query == original_query
        assert result.vector_query == original_query
        assert result.entity_query == original_query
        assert result.original_query == original_query

    @pytest.mark.asyncio
    async def test_fallback_on_timeout(self, mock_config):
        """Test fallback when LLM times out."""
        import asyncio

        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)
        original_query = "Timeout test query"

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = TimeoutError()

            result = await service.generate(original_query, [])

        # All variants should be the original query
        assert result.bm25_query == original_query
        assert result.vector_query == original_query
        assert result.entity_query == original_query

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, mock_config):
        """Test fallback when LLM returns invalid JSON."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)
        original_query = "Invalid JSON test"

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = ValueError("Invalid JSON")

            result = await service.generate(original_query, [])

        assert result.bm25_query == original_query
        assert result.vector_query == original_query
        assert result.entity_query == original_query


class TestMultiQueryGeneratorServicePerformance:
    """Tests for performance requirements."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 3000
        config.get_temperature.return_value = 0.3
        return config

    @pytest.mark.asyncio
    async def test_latency_under_150ms_mocked(self, mock_config):
        """Test that generation completes under 150ms (mocked LLM)."""
        from app.services.multi_query_generator import MultiQueryGeneratorService, QueryVariants

        service = MultiQueryGeneratorService(config=mock_config)

        mock_response = QueryVariants(
            bm25_query="test keywords",
            vector_query="semantic test query",
            entity_query="entity test query",
            original_query="test query",
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            start = time.perf_counter()
            await service.generate("test query", [])
            elapsed = (time.perf_counter() - start) * 1000

        # With mocked LLM, should be very fast
        assert elapsed < 150, f"Generation took {elapsed:.1f}ms, should be <150ms"


class TestMultiQueryGeneratorServicePromptBuilding:
    """Tests for prompt construction."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 3000
        config.get_temperature.return_value = 0.3
        return config

    def test_build_prompt_includes_query(self, mock_config):
        """Test that built prompt includes the query."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        query = "Come si calcola l'IRPEF?"
        prompt = service._build_prompt(query, [])

        assert query in prompt

    def test_build_prompt_includes_entities(self, mock_config):
        """Test that built prompt includes extracted entities."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        entities = [
            ExtractedEntity(text="IRPEF", type="ente", confidence=0.9),
            ExtractedEntity(text="Art. 13", type="articolo", confidence=0.85),
        ]

        prompt = service._build_prompt("Come si calcola l'IRPEF?", entities)

        # Entities should be mentioned in the prompt
        assert "IRPEF" in prompt
        assert "Art. 13" in prompt or "articolo" in prompt.lower()

    def test_system_prompt_includes_query_types(self, mock_config):
        """Test that system prompt describes the 3 query types."""
        from app.services.multi_query_generator import MULTI_QUERY_SYSTEM_PROMPT

        assert "bm25" in MULTI_QUERY_SYSTEM_PROMPT.lower()
        assert "vector" in MULTI_QUERY_SYSTEM_PROMPT.lower()
        assert "entity" in MULTI_QUERY_SYSTEM_PROMPT.lower() or "entità" in MULTI_QUERY_SYSTEM_PROMPT.lower()

    def test_system_prompt_includes_document_references(self, mock_config):
        """ADR-022: Test that system prompt includes document_references instructions."""
        from app.services.multi_query_generator import MULTI_QUERY_SYSTEM_PROMPT

        # Should mention document_references field
        assert "document_references" in MULTI_QUERY_SYSTEM_PROMPT.lower()
        # Should provide Italian instructions about identifying normative documents
        prompt_lower = MULTI_QUERY_SYSTEM_PROMPT.lower()
        assert "legge" in prompt_lower or "decreto" in prompt_lower or "normativo" in prompt_lower


class TestMultiQueryGeneratorServiceResponseParsing:
    """Tests for response parsing."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 3000
        config.get_temperature.return_value = 0.3
        return config

    def test_parse_valid_json_response(self, mock_config):
        """Test parsing a valid JSON response."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        json_response = json.dumps(
            {
                "bm25_query": "keyword query",
                "vector_query": "semantic query",
                "entity_query": "entity query",
            }
        )

        result = service._parse_response(json_response, "original query")

        assert result.bm25_query == "keyword query"
        assert result.vector_query == "semantic query"
        assert result.entity_query == "entity query"
        assert result.original_query == "original query"

    def test_parse_response_with_document_references(self, mock_config):
        """ADR-022: Test parsing response that includes document_references."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        json_response = json.dumps(
            {
                "bm25_query": "rottamazione quinquies definizione agevolata",
                "vector_query": "Quali sono le disposizioni sulla rottamazione quinquies?",
                "entity_query": "Legge 199/2025 definizione agevolata",
                "document_references": ["Legge 199/2025", "LEGGE 30 dicembre 2025, n. 199"],
            }
        )

        result = service._parse_response(json_response, "rottamazione quinquies")

        assert result.document_references == ["Legge 199/2025", "LEGGE 30 dicembre 2025, n. 199"]

    def test_parse_response_without_document_references(self, mock_config):
        """ADR-022: Test that missing document_references defaults to None."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        json_response = json.dumps(
            {
                "bm25_query": "generic query",
                "vector_query": "generic semantic query",
                "entity_query": "generic entity query",
            }
        )

        result = service._parse_response(json_response, "generic question")

        assert result.document_references is None

    def test_parse_response_with_empty_document_references(self, mock_config):
        """ADR-022: Test parsing response with empty document_references array."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        json_response = json.dumps(
            {
                "bm25_query": "test query",
                "vector_query": "test semantic",
                "entity_query": "test entity",
                "document_references": [],
            }
        )

        result = service._parse_response(json_response, "test")

        assert result.document_references == []

    def test_parse_response_with_markdown_wrapper(self, mock_config):
        """Test parsing response wrapped in markdown code block."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        json_response = """```json
{
    "bm25_query": "wrapped keyword query",
    "vector_query": "wrapped semantic query",
    "entity_query": "wrapped entity query"
}
```"""

        result = service._parse_response(json_response, "original")

        assert result.bm25_query == "wrapped keyword query"
        assert result.vector_query == "wrapped semantic query"
        assert result.entity_query == "wrapped entity query"

    def test_parse_invalid_json_raises(self, mock_config):
        """Test that invalid JSON raises ValueError."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        with pytest.raises(ValueError):
            service._parse_response("not valid json", "original")

    def test_parse_missing_field_uses_original(self, mock_config):
        """Test that missing fields fall back to original query."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        # Only bm25_query provided
        json_response = json.dumps(
            {
                "bm25_query": "only bm25",
            }
        )

        result = service._parse_response(json_response, "original query")

        assert result.bm25_query == "only bm25"
        assert result.vector_query == "original query"  # Fallback
        assert result.entity_query == "original query"  # Fallback


class TestMultiQueryGeneratorServiceEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 3000
        config.get_temperature.return_value = 0.3
        return config

    @pytest.mark.asyncio
    async def test_short_query_still_generates(self, mock_config):
        """Test that short queries (<5 words) still generate variants."""
        from app.services.multi_query_generator import MultiQueryGeneratorService, QueryVariants

        service = MultiQueryGeneratorService(config=mock_config)

        mock_response = QueryVariants(
            bm25_query="730 scadenza termine",
            vector_query="Quando scade il termine per la dichiarazione 730?",
            entity_query="730 Agenzia Entrate scadenza",
            original_query="730?",
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate("730?", [])

        # Should still generate variants even for very short query
        assert result.bm25_query != result.original_query or len(result.original_query) < 5
        assert result.vector_query is not None

    @pytest.mark.asyncio
    async def test_entity_rich_query_preserves_entities(self, mock_config):
        """Test that entity-rich queries preserve entities in variants."""
        from app.services.multi_query_generator import MultiQueryGeneratorService, QueryVariants

        service = MultiQueryGeneratorService(config=mock_config)

        entities = [
            ExtractedEntity(text="Legge 104", type="legge", confidence=0.95),
            ExtractedEntity(text="Art. 3 comma 1", type="articolo", confidence=0.9),
            ExtractedEntity(text="INPS", type="ente", confidence=0.9),
        ]

        mock_response = QueryVariants(
            bm25_query="Legge 104 Art. 3 comma 1 permessi INPS requisiti",
            vector_query="Quali sono i requisiti per ottenere i permessi Legge 104 Art. 3 comma 1?",
            entity_query="Legge 104/1992 Art. 3 comma 1 INPS permessi lavorativi",
            original_query="Requisiti Legge 104 Art. 3?",
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate("Requisiti Legge 104 Art. 3?", entities)

        # Entity query should preserve all extracted entities
        assert "104" in result.entity_query
        assert "Art" in result.entity_query or "3" in result.entity_query
        assert "INPS" in result.entity_query


class TestSemanticExpansions:
    """DEV-242 Phase 16: Tests for semantic_expansions functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 3000
        config.get_temperature.return_value = 0.3
        return config

    def test_query_variants_has_semantic_expansions_field(self):
        """DEV-242: QueryVariants should have semantic_expansions field."""
        from app.services.multi_query_generator import QueryVariants

        variants = QueryVariants(
            bm25_query="rottamazione quinquies definizione agevolata",
            vector_query="Quali sono le disposizioni sulla rottamazione quinquies?",
            entity_query="Legge 199/2025 definizione agevolata",
            original_query="Parlami della rottamazione quinquies",
            document_references=["n. 199", "Legge di Bilancio 2026"],
            semantic_expansions=["pace fiscale", "pacificazione fiscale", "definizione agevolata"],
        )

        assert variants.semantic_expansions == ["pace fiscale", "pacificazione fiscale", "definizione agevolata"]

    def test_query_variants_semantic_expansions_optional(self):
        """DEV-242: semantic_expansions should be optional (None by default)."""
        from app.services.multi_query_generator import QueryVariants

        variants = QueryVariants(
            bm25_query="test query",
            vector_query="test query",
            entity_query="test query",
            original_query="test query",
        )

        assert variants.semantic_expansions is None

    def test_query_variants_semantic_expansions_empty_list(self):
        """DEV-242: semantic_expansions can be an empty list when no expansions identified."""
        from app.services.multi_query_generator import QueryVariants

        variants = QueryVariants(
            bm25_query="generic iva question",
            vector_query="generic iva question",
            entity_query="generic iva question",
            original_query="Come funziona l'IVA?",
            semantic_expansions=[],
        )

        assert variants.semantic_expansions == []

    def test_system_prompt_includes_semantic_expansions(self, mock_config):
        """DEV-242: Test that system prompt includes semantic_expansions instructions."""
        from app.services.multi_query_generator import MULTI_QUERY_SYSTEM_PROMPT

        # Should mention semantic_expansions field
        assert "semantic_expansions" in MULTI_QUERY_SYSTEM_PROMPT.lower()
        # Should provide examples of semantic gap bridging
        prompt_lower = MULTI_QUERY_SYSTEM_PROMPT.lower()
        assert "pace fiscale" in prompt_lower or "terminolog" in prompt_lower

    def test_parse_response_with_semantic_expansions(self, mock_config):
        """DEV-242: Test parsing response that includes semantic_expansions."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        json_response = json.dumps(
            {
                "bm25_query": "rottamazione quinquies definizione agevolata",
                "vector_query": "Quali sono le disposizioni sulla rottamazione quinquies?",
                "entity_query": "Legge 199/2025 definizione agevolata",
                "document_references": ["n. 199", "Legge di Bilancio 2026"],
                "semantic_expansions": ["pace fiscale", "pacificazione fiscale", "definizione agevolata"],
            }
        )

        result = service._parse_response(json_response, "rottamazione quinquies")

        assert result.semantic_expansions == ["pace fiscale", "pacificazione fiscale", "definizione agevolata"]

    def test_parse_response_without_semantic_expansions(self, mock_config):
        """DEV-242: Test that missing semantic_expansions defaults to None."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        json_response = json.dumps(
            {
                "bm25_query": "generic query",
                "vector_query": "generic semantic query",
                "entity_query": "generic entity query",
            }
        )

        result = service._parse_response(json_response, "generic question")

        assert result.semantic_expansions is None

    def test_parse_response_with_empty_semantic_expansions(self, mock_config):
        """DEV-242: Test parsing response with empty semantic_expansions array."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)

        json_response = json.dumps(
            {
                "bm25_query": "test query",
                "vector_query": "test semantic",
                "entity_query": "test entity",
                "semantic_expansions": [],
            }
        )

        result = service._parse_response(json_response, "test")

        assert result.semantic_expansions == []

    def test_fallback_variants_has_semantic_expansions_none(self, mock_config):
        """DEV-242: Test that fallback variants have semantic_expansions=None."""
        from app.services.multi_query_generator import MultiQueryGeneratorService

        service = MultiQueryGeneratorService(config=mock_config)
        fallback = service._fallback_variants("test query")

        assert fallback.semantic_expansions is None
        assert fallback.document_references is None

    @pytest.mark.asyncio
    async def test_generate_with_semantic_expansions(self, mock_config):
        """DEV-242: Test that generate() returns semantic_expansions when LLM provides them."""
        from app.services.multi_query_generator import MultiQueryGeneratorService, QueryVariants

        service = MultiQueryGeneratorService(config=mock_config)

        mock_response = QueryVariants(
            bm25_query="rottamazione quinquies pace fiscale definizione",
            vector_query="Quali sono le disposizioni sulla pace fiscale e rottamazione quinquies?",
            entity_query="Legge 199/2025 definizione agevolata pacificazione",
            original_query="Parlami della rottamazione quinquies",
            document_references=["n. 199", "Legge di Bilancio 2026"],
            semantic_expansions=["pace fiscale", "pacificazione fiscale", "definizione agevolata"],
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate("Parlami della rottamazione quinquies", [])

        assert result.semantic_expansions == ["pace fiscale", "pacificazione fiscale", "definizione agevolata"]
        assert result.document_references == ["n. 199", "Legge di Bilancio 2026"]
