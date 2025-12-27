"""TDD Tests for DEV-189: HyDEGeneratorService.

Tests for generating hypothetical documents in Italian bureaucratic style per Section 13.6.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.router import RoutingCategory


class TestHyDEResultSchema:
    """Tests for HyDEResult dataclass."""

    def test_hyde_result_creation(self):
        """Test creating HyDEResult with all fields."""
        from app.services.hyde_generator import HyDEResult

        result = HyDEResult(
            hypothetical_document="Ai sensi dell'art. 1 del D.Lgs. 123/2020...",
            word_count=175,
            skipped=False,
            skip_reason=None,
        )

        assert result.hypothetical_document == "Ai sensi dell'art. 1 del D.Lgs. 123/2020..."
        assert result.word_count == 175
        assert result.skipped is False
        assert result.skip_reason is None

    def test_hyde_result_skipped(self):
        """Test creating skipped HyDEResult."""
        from app.services.hyde_generator import HyDEResult

        result = HyDEResult(
            hypothetical_document="",
            word_count=0,
            skipped=True,
            skip_reason="chitchat",
        )

        assert result.skipped is True
        assert result.skip_reason == "chitchat"
        assert result.hypothetical_document == ""


class TestHyDEGeneratorServiceGeneration:
    """Tests for HyDE document generation."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 5000
        config.get_temperature.return_value = 0.4
        return config

    @pytest.mark.asyncio
    async def test_generates_bureaucratic_style(self, mock_config):
        """Test that generated document uses Italian bureaucratic style."""
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="""Ai sensi dell'art. 13 del D.Lgs. 472/1997 e successive modificazioni,
            il contribuente che intenda regolarizzare la propria posizione fiscale mediante l'istituto
            del ravvedimento operoso deve provvedere al versamento dell'imposta dovuta, maggiorata
            degli interessi legali e delle sanzioni ridotte. La procedura prevede la compilazione
            del modello F24 con l'indicazione del codice tributo appropriato e del periodo di
            riferimento. L'Agenzia delle Entrate, con la circolare n. 23/E del 2020, ha precisato
            le modalità operative e i termini entro i quali è possibile avvalersi di tale beneficio.
            Si ricorda che il ravvedimento deve essere effettuato prima che la violazione sia
            constatata ovvero siano iniziati accessi, ispezioni, verifiche o altre attività
            amministrative di accertamento delle quali l'autore abbia avuto formale conoscenza.""",
            word_count=150,
            skipped=False,
            skip_reason=None,
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate(
                query="Come funziona il ravvedimento operoso?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

        # Check for bureaucratic style markers
        doc = result.hypothetical_document.lower()
        assert any(marker in doc for marker in [
            "ai sensi", "d.lgs", "decreto", "circolare", "agenzia",
            "normativa", "comma", "articolo", "legge",
        ])

    @pytest.mark.asyncio
    async def test_document_length_150_250_words(self, mock_config):
        """Test that document length is between 150-250 words."""
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        # Generate a document with exactly 175 words
        mock_doc = " ".join(["parola"] * 175)
        mock_response = HyDEResult(
            hypothetical_document=mock_doc,
            word_count=175,
            skipped=False,
            skip_reason=None,
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate(
                query="Test query",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

        assert 150 <= result.word_count <= 250

    @pytest.mark.asyncio
    async def test_includes_normative_references(self, mock_config):
        """Test that document includes normative references."""
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="""La disciplina del regime forfettario è contenuta nella Legge 190/2014,
            come modificata dalla Legge 145/2018 (Legge di Bilancio 2019). L'art. 1, commi 54-89,
            stabilisce i requisiti di accesso e le cause di esclusione dal regime agevolato.
            L'Agenzia delle Entrate, con la circolare n. 9/E del 10 aprile 2019, ha fornito
            chiarimenti operativi in merito all'applicazione delle nuove disposizioni.
            Il contribuente che aderisce al regime forfettario beneficia di un'imposta sostitutiva
            del 15% (ridotta al 5% per le nuove attività), calcolata sul reddito determinato
            applicando al fatturato un coefficiente di redditività variabile in base al codice ATECO.""",
            word_count=120,
            skipped=False,
            skip_reason=None,
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate(
                query="Requisiti regime forfettario",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

        doc = result.hypothetical_document
        # Should include legal references
        assert any(ref in doc for ref in [
            "Legge", "D.Lgs", "art.", "comma", "circolare",
        ])


class TestHyDEGeneratorServiceSkipping:
    """Tests for HyDE skip logic."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 5000
        config.get_temperature.return_value = 0.4
        return config

    def test_should_generate_for_technical_research(self, mock_config):
        """Test that HyDE is generated for TECHNICAL_RESEARCH."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)
        assert service.should_generate(RoutingCategory.TECHNICAL_RESEARCH) is True

    def test_should_generate_for_theoretical_definition(self, mock_config):
        """Test that HyDE is generated for THEORETICAL_DEFINITION."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)
        assert service.should_generate(RoutingCategory.THEORETICAL_DEFINITION) is True

    def test_should_generate_for_golden_set(self, mock_config):
        """Test that HyDE is generated for GOLDEN_SET."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)
        assert service.should_generate(RoutingCategory.GOLDEN_SET) is True

    def test_skip_for_chitchat(self, mock_config):
        """Test that HyDE is skipped for CHITCHAT."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)
        assert service.should_generate(RoutingCategory.CHITCHAT) is False

    def test_skip_for_calculator(self, mock_config):
        """Test that HyDE is skipped for CALCULATOR."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)
        assert service.should_generate(RoutingCategory.CALCULATOR) is False

    @pytest.mark.asyncio
    async def test_generate_returns_skipped_for_chitchat(self, mock_config):
        """Test that generate returns skipped result for CHITCHAT."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        result = await service.generate(
            query="Ciao, come stai?",
            routing=RoutingCategory.CHITCHAT,
        )

        assert result.skipped is True
        assert result.skip_reason == "chitchat"
        assert result.hypothetical_document == ""
        assert result.word_count == 0

    @pytest.mark.asyncio
    async def test_generate_returns_skipped_for_calculator(self, mock_config):
        """Test that generate returns skipped result for CALCULATOR."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        result = await service.generate(
            query="Calcola le tasse su 50000 euro",
            routing=RoutingCategory.CALCULATOR,
        )

        assert result.skipped is True
        assert result.skip_reason == "calculator"


class TestHyDEGeneratorServiceFallback:
    """Tests for fallback behavior."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 5000
        config.get_temperature.return_value = 0.4
        return config

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self, mock_config):
        """Test fallback when LLM fails."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM API error")

            result = await service.generate(
                query="Test query",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

        assert result.skipped is True
        assert result.skip_reason == "error"

    @pytest.mark.asyncio
    async def test_fallback_on_timeout(self, mock_config):
        """Test fallback when LLM times out."""
        import asyncio

        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = asyncio.TimeoutError()

            result = await service.generate(
                query="Test query",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

        assert result.skipped is True
        assert result.skip_reason == "timeout"

    @pytest.mark.asyncio
    async def test_too_short_response_still_used(self, mock_config):
        """Test that short responses (>50 words) are still used."""
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        # 60 words - above minimum threshold
        mock_doc = " ".join(["parola"] * 60)
        mock_response = HyDEResult(
            hypothetical_document=mock_doc,
            word_count=60,
            skipped=False,
            skip_reason=None,
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate(
                query="Test query",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

        assert result.skipped is False
        assert result.word_count == 60


class TestHyDEGeneratorServicePerformance:
    """Tests for performance requirements."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 5000
        config.get_temperature.return_value = 0.4
        return config

    @pytest.mark.asyncio
    async def test_latency_under_200ms_mocked(self, mock_config):
        """Test that generation completes under 200ms (mocked LLM)."""
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Test document content",
            word_count=3,
            skipped=False,
            skip_reason=None,
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            start = time.perf_counter()
            await service.generate(
                query="Test query",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )
            elapsed = (time.perf_counter() - start) * 1000

        # With mocked LLM, should be very fast
        assert elapsed < 200, f"Generation took {elapsed:.1f}ms, should be <200ms"


class TestHyDEGeneratorServicePromptBuilding:
    """Tests for prompt construction."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 5000
        config.get_temperature.return_value = 0.4
        return config

    def test_build_prompt_includes_query(self, mock_config):
        """Test that built prompt includes the query."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        query = "Come funziona il ravvedimento operoso?"
        prompt = service._build_prompt(query)

        assert query in prompt

    def test_system_prompt_specifies_style(self, mock_config):
        """Test that system prompt specifies Italian bureaucratic style."""
        from app.services.hyde_generator import HYDE_SYSTEM_PROMPT

        prompt_lower = HYDE_SYSTEM_PROMPT.lower()
        assert "burocratico" in prompt_lower or "italiano" in prompt_lower or "stile" in prompt_lower
        assert "150" in HYDE_SYSTEM_PROMPT or "250" in HYDE_SYSTEM_PROMPT

    def test_system_prompt_mentions_word_count(self, mock_config):
        """Test that system prompt mentions word count requirements."""
        from app.services.hyde_generator import HYDE_SYSTEM_PROMPT

        assert "150" in HYDE_SYSTEM_PROMPT and "250" in HYDE_SYSTEM_PROMPT


class TestHyDEGeneratorServiceResponseParsing:
    """Tests for response parsing."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 5000
        config.get_temperature.return_value = 0.4
        return config

    def test_parse_response_counts_words(self, mock_config):
        """Test that response parser counts words correctly."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        # 10 words
        response = "Uno due tre quattro cinque sei sette otto nove dieci"
        result = service._parse_response(response)

        assert result.word_count == 10
        assert result.hypothetical_document == response

    def test_parse_response_handles_multiline(self, mock_config):
        """Test that response parser handles multiline text."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        response = """Prima riga con tre parole.
        Seconda riga con quattro parole qui.
        Terza riga finale."""

        result = service._parse_response(response)

        # Count all words across lines
        assert result.word_count > 0
        assert "\n" in result.hypothetical_document or len(result.hypothetical_document) > 0
