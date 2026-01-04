"""TDD Tests for DEV-235: HyDE Generator Conversation Awareness.

Tests written BEFORE implementation following RED-GREEN-REFACTOR methodology.
Tests cover:
- Conversation history parameter acceptance
- QueryAmbiguityDetector integration
- Multi-variant generation for ambiguous queries
- Conversational prompt usage
- Conversation history formatting
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Conversation History Parameter Tests
# =============================================================================


class TestConversationHistoryParameter:
    """Tests for conversation_history parameter support."""

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
    async def test_generate_accepts_conversation_history(self, mock_config):
        """Test that generate method accepts conversation_history parameter."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Test document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            # Should not raise - conversation_history is a valid parameter
            result = await service.generate(
                query="E per l'IVA?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
                conversation_history=[
                    {"role": "user", "content": "Come funziona l'IRPEF?"},
                    {"role": "assistant", "content": "L'IRPEF è l'imposta..."},
                ],
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_generate_works_without_conversation_history(self, mock_config):
        """Test that generate works when conversation_history is None."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Test document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate(
                query="Come funziona il ravvedimento?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
                conversation_history=None,
            )

            assert result is not None
            assert result.skipped is False

    @pytest.mark.asyncio
    async def test_generate_works_with_empty_conversation_history(self, mock_config):
        """Test that generate works when conversation_history is empty list."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Test document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.generate(
                query="Come funziona il ravvedimento?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
                conversation_history=[],
            )

            assert result is not None


# =============================================================================
# QueryAmbiguityDetector Integration Tests
# =============================================================================


class TestAmbiguityDetectorIntegration:
    """Tests for QueryAmbiguityDetector integration."""

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
    async def test_ambiguity_checked_before_generation(self, mock_config):
        """Test that ambiguity is checked before generating HyDE."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Test document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        with (
            patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            mock_llm.return_value = mock_response
            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=False,
                score=0.1,
                recommended_strategy="standard",
            )
            mock_detector_factory.return_value = mock_detector

            await service.generate(
                query="E per l'IVA?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

            # Detector should be called
            mock_detector.detect.assert_called_once()

    @pytest.mark.asyncio
    async def test_ambiguity_detector_receives_conversation_history(self, mock_config):
        """Test that ambiguity detector receives conversation history."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Test document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        history = [
            {"role": "user", "content": "Come funziona l'IRPEF?"},
            {"role": "assistant", "content": "L'IRPEF è..."},
        ]

        with (
            patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            mock_llm.return_value = mock_response
            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=False,
                score=0.1,
                recommended_strategy="standard",
            )
            mock_detector_factory.return_value = mock_detector

            await service.generate(
                query="E per l'IVA?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
                conversation_history=history,
            )

            # Detector should receive conversation history
            mock_detector.detect.assert_called_once_with("E per l'IVA?", history)


# =============================================================================
# Multi-Variant Generation Tests
# =============================================================================


class TestMultiVariantGeneration:
    """Tests for multi-variant HyDE generation."""

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
    async def test_multi_variant_generated_for_ambiguous_query(self, mock_config):
        """Test that multiple variants are generated for ambiguous queries."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        with (
            patch.object(service, "_call_llm_with_prompt", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            # Return different docs for each call
            mock_llm.side_effect = [
                HyDEResult(
                    hypothetical_document="Variant 1 about IVA rates",
                    word_count=5,
                    skipped=False,
                    skip_reason=None,
                ),
                HyDEResult(
                    hypothetical_document="Variant 2 about IVA deadlines",
                    word_count=5,
                    skipped=False,
                    skip_reason=None,
                ),
                HyDEResult(
                    hypothetical_document="Variant 3 about IVA exemptions",
                    word_count=5,
                    skipped=False,
                    skip_reason=None,
                ),
            ]

            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=True,
                score=0.7,
                recommended_strategy="multi_variant",
                indicators=["short_query", "followup_pattern"],
            )
            mock_detector_factory.return_value = mock_detector

            result = await service.generate(
                query="E per l'IVA?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

            # Should return multiple variants
            assert result.variants is not None
            assert len(result.variants) >= 2

    @pytest.mark.asyncio
    async def test_variants_cover_different_scenarios(self, mock_config):
        """Test that variants cover different interpretation scenarios."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        with (
            patch.object(service, "_call_llm_with_prompt", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            mock_llm.side_effect = [
                HyDEResult(
                    hypothetical_document="Document about aliquote IVA",
                    word_count=4,
                    skipped=False,
                    skip_reason=None,
                ),
                HyDEResult(
                    hypothetical_document="Document about scadenze IVA",
                    word_count=4,
                    skipped=False,
                    skip_reason=None,
                ),
            ]

            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=True,
                score=0.6,
                recommended_strategy="multi_variant",
                indicators=["short_query"],
            )
            mock_detector_factory.return_value = mock_detector

            result = await service.generate(
                query="IVA?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

            # Variants should be different
            if result.variants:
                variant_texts = [v.hypothetical_document for v in result.variants]
                # All variants should be unique
                assert len(set(variant_texts)) == len(variant_texts)

    @pytest.mark.asyncio
    async def test_single_variant_for_non_ambiguous_query(self, mock_config):
        """Test that single variant is generated for non-ambiguous queries."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Single document about ravvedimento operoso",
            word_count=5,
            skipped=False,
            skip_reason=None,
        )

        with (
            patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            mock_llm.return_value = mock_response

            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=False,
                score=0.1,
                recommended_strategy="standard",
                indicators=[],
            )
            mock_detector_factory.return_value = mock_detector

            result = await service.generate(
                query="Come funziona il ravvedimento operoso per le imposte non pagate?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

            # Should return single variant or no variants list
            assert result.variants is None or len(result.variants) == 1


# =============================================================================
# Conversational Prompt Tests
# =============================================================================


class TestConversationalPrompt:
    """Tests for conversational prompt usage."""

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
    async def test_uses_conversational_prompt_with_history(self, mock_config):
        """Test that conversational prompt is used when history is provided."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Test document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        history = [
            {"role": "user", "content": "Come funziona l'IRPEF?"},
            {"role": "assistant", "content": "L'IRPEF è l'imposta..."},
        ]

        with (
            patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
            patch("app.services.hyde_generator.get_prompt_loader") as mock_loader_factory,
        ):
            mock_llm.return_value = mock_response

            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=False,
                score=0.2,
                recommended_strategy="conversational",
                indicators=["followup_pattern"],
            )
            mock_detector_factory.return_value = mock_detector

            mock_loader = MagicMock()
            mock_loader.load.return_value = "Conversational prompt content"
            mock_loader_factory.return_value = mock_loader

            await service.generate(
                query="E per i pensionati?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
                conversation_history=history,
            )

            # Should use hyde_conversational template
            mock_loader.load.assert_called()
            call_args = mock_loader.load.call_args
            assert "hyde_conversational" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_uses_basic_prompt_without_history(self, mock_config):
        """Test that basic prompt is used when no history is provided."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Test document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        with (
            patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            mock_llm.return_value = mock_response

            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=False,
                score=0.1,
                recommended_strategy="standard",
                indicators=[],
            )
            mock_detector_factory.return_value = mock_detector

            await service.generate(
                query="Come funziona il ravvedimento operoso?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
                conversation_history=None,
            )

            # Should use basic prompt (the default)
            mock_llm.assert_called_once()


# =============================================================================
# Conversation History Formatting Tests
# =============================================================================


class TestConversationHistoryFormatting:
    """Tests for conversation history formatting."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock()
        config.get_model.return_value = "gpt-4o-mini"
        config.get_provider.return_value = "openai"
        config.get_timeout.return_value = 5000
        config.get_temperature.return_value = 0.4
        return config

    def test_format_conversation_history_last_3_turns(self, mock_config):
        """Test that only last 3 turns are formatted."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        history = [
            {"role": "user", "content": "Turn 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Turn 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Turn 3"},
            {"role": "assistant", "content": "Response 3"},
            {"role": "user", "content": "Turn 4"},
            {"role": "assistant", "content": "Response 4"},
        ]

        formatted = service._format_conversation_history(history, max_turns=3)

        # Should only include last 3 turns (6 messages)
        assert "Turn 4" in formatted
        assert "Turn 3" in formatted
        assert "Turn 2" in formatted
        assert "Turn 1" not in formatted

    def test_format_conversation_history_handles_empty(self, mock_config):
        """Test formatting empty history returns placeholder."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        formatted = service._format_conversation_history(None)

        assert formatted is not None
        assert len(formatted) > 0

    def test_format_conversation_history_handles_none(self, mock_config):
        """Test formatting None history returns placeholder."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        formatted = service._format_conversation_history(None)

        assert "Nessun contesto" in formatted or len(formatted) > 0

    def test_format_conversation_history_includes_roles(self, mock_config):
        """Test that formatted history includes role labels."""
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        history = [
            {"role": "user", "content": "Domanda utente"},
            {"role": "assistant", "content": "Risposta assistente"},
        ]

        formatted = service._format_conversation_history(history)

        # Should include role indicators
        assert "Utente" in formatted or "user" in formatted.lower()
        assert "Assistente" in formatted or "assistant" in formatted.lower()
        assert "Domanda utente" in formatted
        assert "Risposta assistente" in formatted


# =============================================================================
# HyDEResult Variants Field Tests
# =============================================================================


class TestHyDEResultVariants:
    """Tests for HyDEResult variants field."""

    def test_hyde_result_has_variants_field(self):
        """Test that HyDEResult has variants field."""
        from app.services.hyde_generator import HyDEResult

        result = HyDEResult(
            hypothetical_document="Main document",
            word_count=2,
            skipped=False,
            skip_reason=None,
            variants=None,
        )

        assert hasattr(result, "variants")

    def test_hyde_result_variants_can_be_list(self):
        """Test that variants can be a list of HyDEResult."""
        from app.services.hyde_generator import HyDEResult

        variant1 = HyDEResult(
            hypothetical_document="Variant 1",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )
        variant2 = HyDEResult(
            hypothetical_document="Variant 2",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        result = HyDEResult(
            hypothetical_document="Main",
            word_count=1,
            skipped=False,
            skip_reason=None,
            variants=[variant1, variant2],
        )

        assert result.variants is not None
        assert len(result.variants) == 2

    def test_hyde_result_variants_default_none(self):
        """Test that variants defaults to None."""
        from app.services.hyde_generator import HyDEResult

        result = HyDEResult(
            hypothetical_document="Main document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        # variants should default to None for backward compatibility
        assert result.variants is None


# =============================================================================
# Strategy-Based Generation Tests
# =============================================================================


class TestStrategyBasedGeneration:
    """Tests for strategy-based HyDE generation."""

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
    async def test_standard_strategy_single_generation(self, mock_config):
        """Test that standard strategy generates single document."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Standard document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        with (
            patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            mock_llm.return_value = mock_response

            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=False,
                score=0.1,
                recommended_strategy="standard",
                indicators=[],
            )
            mock_detector_factory.return_value = mock_detector

            result = await service.generate(
                query="Come funziona il ravvedimento operoso per imposte non pagate?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

            # LLM should be called only once for standard strategy
            assert mock_llm.call_count == 1
            assert result.variants is None

    @pytest.mark.asyncio
    async def test_conversational_strategy_uses_context(self, mock_config):
        """Test that conversational strategy uses conversation context."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Contextual document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        history = [
            {"role": "user", "content": "Come funziona l'IRPEF?"},
            {"role": "assistant", "content": "L'IRPEF è..."},
        ]

        with (
            patch.object(service, "_call_llm_with_prompt", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            mock_llm.return_value = mock_response

            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=True,
                score=0.4,
                recommended_strategy="conversational",
                indicators=["pronoun_ambiguity"],
            )
            mock_detector_factory.return_value = mock_detector

            result = await service.generate(
                query="E questo come si calcola?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
                conversation_history=history,
            )

            # Should generate with context (single call for conversational)
            assert mock_llm.call_count >= 1
            assert result is not None

    @pytest.mark.asyncio
    async def test_multi_variant_strategy_generates_multiple(self, mock_config):
        """Test that multi_variant strategy generates multiple documents."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        with (
            patch.object(service, "_call_llm_with_prompt", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            mock_llm.side_effect = [
                HyDEResult(
                    hypothetical_document="Variant 1",
                    word_count=2,
                    skipped=False,
                    skip_reason=None,
                ),
                HyDEResult(
                    hypothetical_document="Variant 2",
                    word_count=2,
                    skipped=False,
                    skip_reason=None,
                ),
                HyDEResult(
                    hypothetical_document="Variant 3",
                    word_count=2,
                    skipped=False,
                    skip_reason=None,
                ),
            ]

            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=True,
                score=0.8,
                recommended_strategy="multi_variant",
                indicators=["short_query", "missing_fiscal_terms"],
            )
            mock_detector_factory.return_value = mock_detector

            result = await service.generate(
                query="Cosa devo fare?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

            # LLM should be called multiple times for multi_variant
            assert mock_llm.call_count >= 2
            assert result.variants is not None
            assert len(result.variants) >= 2


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCasesAndErrors:
    """Tests for edge cases and error handling."""

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
    async def test_skipped_categories_bypass_ambiguity_check(self, mock_config):
        """Test that skipped categories don't check ambiguity."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService

        service = HyDEGeneratorService(config=mock_config)

        with patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory:
            mock_detector = MagicMock()
            mock_detector_factory.return_value = mock_detector

            result = await service.generate(
                query="Ciao!",
                routing=RoutingCategory.CHITCHAT,
            )

            # Should skip without checking ambiguity
            assert result.skipped is True
            mock_detector.detect.assert_not_called()

    @pytest.mark.asyncio
    async def test_ambiguity_detector_error_falls_back_to_standard(self, mock_config):
        """Test that detector error falls back to standard generation."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        mock_response = HyDEResult(
            hypothetical_document="Fallback document",
            word_count=2,
            skipped=False,
            skip_reason=None,
        )

        with (
            patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            mock_llm.return_value = mock_response
            mock_detector = MagicMock()
            mock_detector.detect.side_effect = Exception("Detector error")
            mock_detector_factory.return_value = mock_detector

            result = await service.generate(
                query="Test query",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

            # Should fall back to standard generation
            assert result.skipped is False
            assert result.hypothetical_document == "Fallback document"

    @pytest.mark.asyncio
    async def test_partial_variant_failure_returns_successful_variants(self, mock_config):
        """Test that partial variant failures still return successful variants."""
        from app.schemas.router import RoutingCategory
        from app.services.hyde_generator import HyDEGeneratorService, HyDEResult

        service = HyDEGeneratorService(config=mock_config)

        with (
            patch.object(service, "_call_llm_with_prompt", new_callable=AsyncMock) as mock_llm,
            patch("app.services.hyde_generator.get_query_ambiguity_detector") as mock_detector_factory,
        ):
            # First succeeds, second fails, third succeeds
            mock_llm.side_effect = [
                HyDEResult(
                    hypothetical_document="Variant 1",
                    word_count=2,
                    skipped=False,
                    skip_reason=None,
                ),
                Exception("LLM error"),
                HyDEResult(
                    hypothetical_document="Variant 3",
                    word_count=2,
                    skipped=False,
                    skip_reason=None,
                ),
            ]

            mock_detector = MagicMock()
            mock_detector.detect.return_value = MagicMock(
                is_ambiguous=True,
                score=0.7,
                recommended_strategy="multi_variant",
                indicators=["short_query"],
            )
            mock_detector_factory.return_value = mock_detector

            result = await service.generate(
                query="IVA?",
                routing=RoutingCategory.TECHNICAL_RESEARCH,
            )

            # Should return at least the successful variants
            assert result.variants is not None
            assert len(result.variants) >= 1
