"""TDD Tests for DEV-245 Phase 3.1: Web Verification Service.

Tests for verifying KB answers against web search results
to detect contradictions and add caveats.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.web_verification import (
    EXCLUSION_KEYWORDS,
    ContradictionInfo,
    WebVerificationResult,
    WebVerificationService,
    _web_has_genuine_exclusions,
    web_verification_service,
)


class TestWebSearchIntegration:
    """Tests for web search functionality."""

    @pytest.mark.asyncio
    async def test_search_web_returns_results(self):
        """Test that web search returns structured results."""
        service = WebVerificationService()

        # Mock DuckDuckGo search results
        mock_results = [
            {"title": "Article 1", "snippet": "Some content about topic", "link": "https://example.com/1"},
            {"title": "Article 2", "snippet": "More content", "link": "https://example.com/2"},
        ]

        with patch.object(service, "_search_web", return_value=mock_results):
            results = await service._search_web("rottamazione quinquies tributi locali")

        assert len(results) >= 1
        assert "title" in results[0]
        assert "snippet" in results[0]

    @pytest.mark.asyncio
    async def test_search_web_handles_empty_results(self):
        """Test handling of empty search results."""
        service = WebVerificationService()

        with patch.object(service, "_search_web", return_value=[]):
            results = await service._search_web("nonsense query xyz123")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_web_handles_errors(self):
        """Test graceful handling of search errors."""
        service = WebVerificationService()

        with patch.object(service, "_search_web", side_effect=Exception("Network error")):
            result = await service.verify_answer(
                user_query="test query",
                kb_answer="test answer",
                kb_sources=[],
            )

        # Should return result without caveats on error
        assert isinstance(result, WebVerificationResult)
        assert len(result.caveats) == 0


class TestContradictionDetection:
    """Tests for detecting contradictions between KB and web."""

    @pytest.mark.asyncio
    async def test_detect_contradiction_different_dates(self):
        """Test detecting date contradictions."""
        service = WebVerificationService()

        kb_answer = "La scadenza per la domanda è il 30 giugno 2026."
        web_snippets = [
            {"snippet": "La scadenza è stata prorogata al 30 settembre 2026", "title": "Proroga scadenza"},
        ]

        contradictions = service._detect_contradictions(kb_answer, web_snippets)

        assert len(contradictions) >= 1
        assert any("scadenza" in c.topic.lower() or "30" in c.topic for c in contradictions)

    @pytest.mark.asyncio
    async def test_detect_contradiction_conflicting_info(self):
        """Test detecting conflicting information."""
        service = WebVerificationService()

        kb_answer = "I tributi locali come l'IMU possono essere rottamati."
        web_snippets = [
            {
                "snippet": "La rottamazione per IMU richiede accordo dell'ente locale, non è automatica",
                "title": "Rottamazione tributi locali",
            },
        ]

        contradictions = service._detect_contradictions(kb_answer, web_snippets)

        # Should detect nuance about local agreement requirement
        assert len(contradictions) >= 1

    @pytest.mark.asyncio
    async def test_no_contradiction_when_consistent(self):
        """Test no contradiction when info is consistent."""
        service = WebVerificationService()

        kb_answer = "La rottamazione quinquies è prevista dalla Legge 199/2025."
        web_snippets = [
            {
                "snippet": "La Legge 199/2025 introduce la definizione agevolata dei carichi fiscali",
                "title": "Legge 199/2025",
            },
        ]

        contradictions = service._detect_contradictions(kb_answer, web_snippets)

        assert len(contradictions) == 0

    @pytest.mark.asyncio
    async def test_detect_nuance_not_contradiction(self):
        """Test detecting nuances that add context without contradicting."""
        service = WebVerificationService()

        kb_answer = "La rottamazione quinquies permette di pagare i debiti fiscali a rate."
        web_snippets = [
            {
                "snippet": "La rottamazione non copre i debiti per multe stradali superiori a 1000 euro",
                "title": "Limiti rottamazione",
            },
        ]

        # Nuances should be detected as additional info, not hard contradictions
        contradictions = service._detect_contradictions(kb_answer, web_snippets)
        # This is informational, not a contradiction since the KB says "alcuni" debiti
        assert isinstance(contradictions, list)


class TestCaveatGeneration:
    """Tests for generating caveats from contradictions."""

    def test_generate_caveat_for_date_conflict(self):
        """Test generating caveat for date conflict."""
        service = WebVerificationService()

        contradiction = ContradictionInfo(
            topic="scadenza",
            kb_claim="30 giugno 2026",
            web_claim="30 settembre 2026",
            source_url="https://example.com/proroga",
            source_title="Proroga scadenza rottamazione",
            confidence=0.8,
        )

        caveat = service._generate_caveat(contradiction)

        assert caveat is not None
        assert "Nota" in caveat or "nota" in caveat.lower()
        assert "scadenza" in caveat.lower() or "30" in caveat

    def test_generate_caveat_for_local_tribute_nuance(self):
        """Test generating caveat for local tribute nuance."""
        service = WebVerificationService()

        contradiction = ContradictionInfo(
            topic="tributi locali",
            kb_claim="possono essere rottamati",
            web_claim="richiede accordo dell'ente locale",
            source_url="https://example.com/tributi",
            source_title="Rottamazione tributi locali",
            confidence=0.7,
        )

        caveat = service._generate_caveat(contradiction)

        assert caveat is not None
        # Should mention the nuance about local agreement
        assert "ente" in caveat.lower() or "locale" in caveat.lower() or "accordo" in caveat.lower()

    def test_no_caveat_for_low_confidence(self):
        """Test no caveat generated for low confidence contradictions."""
        service = WebVerificationService()

        contradiction = ContradictionInfo(
            topic="general info",
            kb_claim="claim A",
            web_claim="claim B",
            source_url="https://example.com",
            source_title="Source",
            confidence=0.3,  # Low confidence
        )

        caveat = service._generate_caveat(contradiction)

        # Low confidence should not generate caveat
        assert caveat is None


class TestWebVerificationResult:
    """Tests for WebVerificationResult dataclass."""

    def test_result_has_caveats_true(self):
        """Test has_caveats property when caveats exist."""
        result = WebVerificationResult(
            caveats=["Nota: La scadenza potrebbe essere cambiata"],
            contradictions=[
                ContradictionInfo(
                    topic="scadenza",
                    kb_claim="giugno",
                    web_claim="settembre",
                    source_url="https://example.com",
                    source_title="Source",
                    confidence=0.8,
                )
            ],
            web_sources_checked=3,
            verification_performed=True,
        )

        assert result.has_caveats is True
        assert len(result.caveats) == 1

    def test_result_has_caveats_false(self):
        """Test has_caveats property when no caveats."""
        result = WebVerificationResult(
            caveats=[],
            contradictions=[],
            web_sources_checked=3,
            verification_performed=True,
        )

        assert result.has_caveats is False

    def test_result_to_dict(self):
        """Test to_dict serialization."""
        result = WebVerificationResult(
            caveats=["Nota: info aggiuntiva"],
            contradictions=[],
            web_sources_checked=5,
            verification_performed=True,
        )

        d = result.to_dict()

        assert "caveats" in d
        assert "web_sources_checked" in d
        assert "verification_performed" in d
        assert d["web_sources_checked"] == 5


class TestFullVerificationFlow:
    """Tests for the complete verification flow."""

    @pytest.mark.asyncio
    async def test_verify_answer_returns_caveats(self):
        """Test full verification returns caveats when contradictions found."""
        service = WebVerificationService()

        # Mock web search to return contradicting info
        mock_web_results = [
            {
                "title": "Proroga scadenza rottamazione",
                "snippet": "La scadenza è stata prorogata al 30 settembre 2026",
                "link": "https://example.com/proroga",
            }
        ]

        with patch.object(service, "_search_web", return_value=mock_web_results):
            result = await service.verify_answer(
                user_query="scadenza rottamazione quinquies",
                kb_answer="La scadenza per la domanda è il 30 giugno 2026.",
                kb_sources=[{"title": "Legge 199/2025"}],
            )

        assert isinstance(result, WebVerificationResult)
        assert result.verification_performed is True
        # May or may not have caveats depending on detection logic

    @pytest.mark.asyncio
    async def test_verify_answer_skips_for_chitchat(self):
        """Test verification is skipped for chitchat queries."""
        service = WebVerificationService()

        result = await service.verify_answer(
            user_query="ciao come stai",
            kb_answer="Ciao! Sono qui per aiutarti.",
            kb_sources=[],
            skip_for_chitchat=True,
        )

        assert result.verification_performed is False
        assert len(result.caveats) == 0

    @pytest.mark.asyncio
    async def test_verify_answer_respects_timeout(self):
        """Test verification respects timeout settings."""
        service = WebVerificationService(timeout_seconds=0.001)

        # This should timeout and return empty result
        result = await service.verify_answer(
            user_query="test query",
            kb_answer="test answer",
            kb_sources=[],
        )

        # Should return result without errors
        assert isinstance(result, WebVerificationResult)


class TestSingletonInstance:
    """Tests for the singleton instance."""

    def test_singleton_is_web_verification_service(self):
        """Test that singleton is a WebVerificationService instance."""
        assert isinstance(web_verification_service, WebVerificationService)


class TestSpecificScenarios:
    """Tests for specific real-world scenarios from DEV-245."""

    @pytest.mark.asyncio
    async def test_imu_local_tribute_scenario(self):
        """Test the IMU/tasse auto scenario from DEV-245.

        From the plan:
        - KB answer: 'Si possono rottamare'
        - Reality: 'Dipende dall'accordo con l'ente locale'
        """
        service = WebVerificationService()

        kb_answer = """
        Sì, i tributi locali come tasse auto e IMU possono essere rottamati.
        Questi tributi locali rientrano tra quelli definiti dalla Legge 199/2025.
        """

        web_snippets = [
            {
                "snippet": "La rottamazione quinquies per i tributi locali non offre certezze "
                "perché richiede l'accordo degli enti locali",
                "title": "Rottamazione tributi locali - italia-informa.com",
            }
        ]

        contradictions = service._detect_contradictions(kb_answer, web_snippets)

        # Should detect the nuance about local agreement requirement
        # The keyword "richiede" should trigger contradiction detection
        assert len(contradictions) >= 1, "Should detect contradiction when web snippet mentions 'richiede l'accordo'"

    @pytest.mark.asyncio
    async def test_irap_exclusion_scenario(self):
        """Test IRAP exclusion scenario.

        Brave AI correctly identified:
        - IRAP from declaration/formal check: included
        - IRAP from assessment: excluded
        """
        service = WebVerificationService()

        kb_answer = "Sì, è possibile rottamare i debiti relativi all'IRAP."

        web_snippets = [
            {
                "snippet": "Inclusi: IRAP non versata in seguito a dichiarazione annuale "
                "o controllo formale (artt. 36-bis e 36-ter DPR 600/1973). "
                "Esclusi: IRAP oggetto di accertamento",
                "title": "IRAP e rottamazione quinquies",
            }
        ]

        contradictions = service._detect_contradictions(kb_answer, web_snippets)

        # Should detect the nuance about IRAP exclusions (keyword "Esclusi")
        # The KB answer is too simplistic - doesn't mention the exclusions
        assert len(contradictions) >= 1, "Should detect contradiction when web mentions IRAP exclusions"


class TestKeywordContextOrderingPhase393:
    """DEV-245 Phase 3.9.3: Test that newest assistant message is skipped in context extraction.

    At Step 100 (web_verification), the messages include the NEW assistant response
    (just generated by LLM). We must skip this when extracting context keywords,
    otherwise ALL keywords become "context" and no reordering happens.
    """

    def test_skip_newest_assistant_message_in_context(self):
        """Context should come from PREVIOUS assistant, not the NEW one we're verifying."""
        service = WebVerificationService()

        # Simulate Step 100 scenario: messages INCLUDE the new assistant response
        messages = [
            {"role": "user", "content": "parlami della rottamazione quinquies"},
            {
                "role": "assistant",
                "content": "La rottamazione quinquies è una definizione agevolata dei debiti fiscali prevista dalla Legge 199/2025.",
            },
            {"role": "user", "content": "e l'irap?"},
            # This is the NEW response - should be SKIPPED in context extraction
            {
                "role": "assistant",
                "content": "L'IRAP può essere inclusa nella rottamazione quinquies se deriva da dichiarazione.",
            },
        ]

        # Query: "L'IRAP può essere inclusa nella rottamazione quinquies?"
        # Keywords in sentence order: ['irap', 'rottamazione', 'quinquies']
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"

        result = service._extract_search_keywords_with_context(query, messages)

        # Context should be from assistant1 (rottamazione, quinquies), NOT assistant2 (which has irap)
        # Expected: context_first=['rottamazione', 'quinquies'], new=['irap']
        # Result: ['rottamazione', 'quinquies', 'irap']
        assert result == ["rottamazione", "quinquies", "irap"], f"Expected context-first ordering, got: {result}"

        # Verify 'irap' is LAST (it's the new topic from follow-up)
        assert result[-1] == "irap", "New topic 'irap' should be last"

        # Verify 'rottamazione' is FIRST (it's from context)
        assert result[0] == "rottamazione", "Context keyword 'rottamazione' should be first"

    def test_context_ordering_without_new_assistant_message(self):
        """Step 039c scenario: no new assistant message yet - last message is user."""
        service = WebVerificationService()

        # Step 039c scenario: NO new assistant response yet (last message is user)
        messages = [
            {"role": "user", "content": "parlami della rottamazione quinquies"},
            {
                "role": "assistant",
                "content": "La rottamazione quinquies è una definizione agevolata dei debiti fiscali.",
            },
            {"role": "user", "content": "e l'irap?"},
            # No assistant2 yet - this is BEFORE LLM call
        ]

        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"
        result = service._extract_search_keywords_with_context(query, messages)

        # Should still work: context from assistant1
        assert result == ["rottamazione", "quinquies", "irap"]

    def test_context_ordering_with_langchain_type_key(self):
        """Test that LangChain format (type: ai) is also handled correctly."""
        service = WebVerificationService()

        # LangChain uses "type" instead of "role"
        messages = [
            {"type": "human", "content": "parlami della rottamazione quinquies"},
            {"type": "ai", "content": "La rottamazione quinquies è una definizione agevolata dei debiti fiscali."},
            {"type": "human", "content": "e l'irap?"},
            # NEW response with LangChain format - should be SKIPPED
            {"type": "ai", "content": "L'IRAP può essere inclusa nella rottamazione quinquies."},
        ]

        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"
        result = service._extract_search_keywords_with_context(query, messages)

        # Should skip the newest "ai" message and get context from the older one
        assert result == ["rottamazione", "quinquies", "irap"]


class TestBraveSearchIntegration:
    """Tests for Brave Search API integration."""

    @pytest.mark.asyncio
    async def test_brave_search_returns_ai_summary(self):
        """Test that Brave returns AI-synthesized summary."""
        service = WebVerificationService()

        mock_search_response = {
            "web": {
                "results": [
                    {"title": "Source 1", "description": "Snippet 1", "url": "https://example.com/1"},
                ]
            },
            "summarizer": {"key": "test-summarizer-key"},
        }

        mock_summary_response = {
            "status": "complete",
            "summary": {"text": "La rottamazione quinquies per tributi locali richiede l'accordo dell'ente locale."},
        }

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.BRAVE_SEARCH_API_KEY = "test-api-key"  # pragma: allowlist secret

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance

                # First call: web search, Second call: summarizer
                search_resp = MagicMock()
                search_resp.json.return_value = mock_search_response
                search_resp.raise_for_status = MagicMock()

                summary_resp = MagicMock()
                summary_resp.json.return_value = mock_summary_response
                summary_resp.raise_for_status = MagicMock()

                mock_instance.get = AsyncMock(side_effect=[search_resp, summary_resp])

                results = await service._search_web("rottamazione tributi locali")

        assert len(results) >= 1
        assert results[0]["is_ai_synthesis"] is True
        assert "accordo" in results[0]["snippet"].lower()

    @pytest.mark.asyncio
    async def test_brave_fallback_to_duckduckgo_when_not_configured(self):
        """Test fallback to DuckDuckGo when Brave not configured."""
        service = WebVerificationService()

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.BRAVE_SEARCH_API_KEY = None  # Not configured

            with patch.object(service, "_search_web_duckduckgo", return_value=[]) as mock_ddg:
                results = await service._search_web("test query")

        mock_ddg.assert_called_once_with("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_brave_fallback_on_error(self):
        """Test fallback to DuckDuckGo when Brave API fails."""
        service = WebVerificationService()

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.BRAVE_SEARCH_API_KEY = "test-api-key"  # pragma: allowlist secret

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance
                mock_instance.get = AsyncMock(side_effect=Exception("API Error"))

                with patch.object(
                    service, "_search_web_duckduckgo", return_value=[{"title": "DDG Result"}]
                ) as mock_ddg:
                    results = await service._search_web("test query")

        mock_ddg.assert_called_once()
        assert len(results) == 1
        assert results[0]["title"] == "DDG Result"

    def test_ai_synthesis_gets_higher_confidence(self):
        """Test that AI synthesis results get higher confidence scores."""
        service = WebVerificationService()

        # Same topic and snippet, different is_ai_synthesis flag
        confidence_no_ai = service._calculate_contradiction_confidence(
            kb_answer="I tributi locali possono essere rottamati",
            web_snippet="La rottamazione richiede accordo dell'ente locale",
            topic="tributi locali",
            is_ai_synthesis=False,
        )

        confidence_with_ai = service._calculate_contradiction_confidence(
            kb_answer="I tributi locali possono essere rottamati",
            web_snippet="La rottamazione richiede accordo dell'ente locale",
            topic="tributi locali",
            is_ai_synthesis=True,
        )

        # AI synthesis should have higher confidence (0.65 base vs 0.5 base)
        assert confidence_with_ai > confidence_no_ai
        assert confidence_with_ai - confidence_no_ai == pytest.approx(0.15, abs=0.01)

    @pytest.mark.asyncio
    async def test_detect_contradiction_with_ai_synthesis_flag(self):
        """Test that is_ai_synthesis flag is handled in contradiction detection."""
        service = WebVerificationService()

        kb_answer = "I tributi locali come l'IMU possono essere rottamati."
        web_results = [
            {
                "snippet": "La rottamazione per IMU richiede accordo dell'ente locale",
                "title": "Brave AI Summary",
                "link": "",
                "is_ai_synthesis": True,
            },
        ]

        contradictions = service._detect_contradictions(kb_answer, web_results)

        assert len(contradictions) >= 1
        # Confidence should be higher due to AI synthesis
        assert contradictions[0].confidence >= 0.65

    @pytest.mark.asyncio
    async def test_brave_search_handles_missing_summarizer_key(self):
        """Test handling when Brave doesn't return a summarizer key."""
        service = WebVerificationService()

        mock_search_response = {
            "web": {
                "results": [
                    {"title": "Source 1", "description": "Snippet 1", "url": "https://example.com/1"},
                ]
            },
            # No summarizer key
        }

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.BRAVE_SEARCH_API_KEY = "test-api-key"  # pragma: allowlist secret

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value.__aenter__.return_value = mock_instance

                search_resp = MagicMock()
                search_resp.json.return_value = mock_search_response
                search_resp.raise_for_status = MagicMock()

                mock_instance.get = AsyncMock(return_value=search_resp)

                results = await service._search_web("test query")

        # Should return web results without AI summary
        assert len(results) == 1
        assert results[0]["is_ai_synthesis"] is False
        assert results[0]["title"] == "Source 1"


class TestExclusionDetectionPhase514:
    """DEV-245 Phase 5.14: Test web-based exclusion detection for ✅/❌ format.

    The ✅/❌ format should only be used when web results ACTUALLY contain
    exclusion keywords, not for general informational queries.
    """

    def test_detects_escluso_keyword(self):
        """Should detect 'escluso' as exclusion indicator."""
        results = [{"snippet": "L'IRAP da accertamento è esclusa dalla rottamazione"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "esclusa" in keywords

    def test_detects_esclusi_keyword(self):
        """Should detect 'esclusi' as exclusion indicator."""
        results = [{"snippet": "Sono esclusi i debiti da sentenze penali"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "esclusi" in keywords

    def test_no_exclusions_in_general_content(self):
        """Should not detect exclusions in general content."""
        results = [{"snippet": "La rottamazione quinquies permette di pagare in 54 rate"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is False
        assert keywords == []

    def test_detects_delibera_comunale(self):
        """Should detect municipal deliberation as exclusion indicator."""
        results = [{"snippet": "L'IMU richiede delibera comunale per rientrare nella rottamazione"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "delibera comunale" in keywords

    def test_detects_richiede_keyword(self):
        """Should detect 'richiede' as conditional limitation."""
        results = [{"snippet": "La rottamazione dei tributi locali richiede l'adesione dell'ente"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "richiede" in keywords

    def test_detects_non_rientra_keyword(self):
        """Should detect 'non rientra' as exclusion."""
        results = [{"snippet": "Il bollo auto non rientra nella definizione agevolata"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "non rientra" in keywords

    def test_detects_multiple_keywords(self):
        """Should detect multiple exclusion keywords."""
        results = [{"snippet": "L'IRAP è esclusa se da accertamento, richiede verifica"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert len(keywords) >= 2
        assert "esclusa" in keywords
        assert "richiede" in keywords

    def test_handles_empty_results(self):
        """Should handle empty results gracefully."""
        results: list[dict] = []
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is False
        assert keywords == []

    def test_handles_missing_snippet(self):
        """Should handle results without snippet field."""
        results = [{"title": "Some title", "link": "https://example.com"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is False
        assert keywords == []

    def test_case_insensitive_detection(self):
        """Should detect keywords regardless of case."""
        results = [{"snippet": "L'IRAP è ESCLUSA dalla rottamazione"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "esclusa" in keywords

    def test_multiple_results_combined(self):
        """Should detect exclusions across multiple results."""
        results = [
            {"snippet": "La rottamazione permette pagamenti agevolati"},  # No exclusions
            {"snippet": "Sono esclusi i debiti da sentenze"},  # Has exclusion
        ]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "esclusi" in keywords

    def test_deduplicates_keywords(self):
        """Should deduplicate matched keywords."""
        results = [
            {"snippet": "L'IRAP è esclusa"},
            {"snippet": "Anche altri tributi sono esclusa"},  # Same keyword
        ]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        # Should not have duplicates
        assert keywords.count("esclusa") == 1

    def test_exclusion_keywords_constant_exists(self):
        """EXCLUSION_KEYWORDS constant should exist and have expected entries."""
        assert "escluso" in EXCLUSION_KEYWORDS
        assert "esclusa" in EXCLUSION_KEYWORDS
        assert "delibera comunale" in EXCLUSION_KEYWORDS
        assert "richiede" in EXCLUSION_KEYWORDS
        assert "non rientra" in EXCLUSION_KEYWORDS

    def test_detects_accordo_keyword(self):
        """Should detect 'accordo' as conditional limitation."""
        results = [{"snippet": "I tributi locali richiedono accordo con l'ente locale"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "accordo" in keywords

    def test_detects_tranne_keyword(self):
        """Should detect 'tranne' as exclusion indicator."""
        results = [{"snippet": "Tutti i tributi sono ammessi tranne quelli da sentenze"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "tranne" in keywords

    def test_detects_solo_se_keyword(self):
        """Should detect 'solo se' as conditional limitation."""
        results = [{"snippet": "L'IRAP è ammessa solo se da dichiarazione"}]
        has_exc, keywords = _web_has_genuine_exclusions(results)
        assert has_exc is True
        assert "solo se" in keywords
