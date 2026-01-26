r"""Web Verification Service for DEV-245 Phase 3.1.

Verifies KB answers against web search results to detect contradictions
and add caveats when the KB answer may be incomplete or outdated.

Architecture:
    User Question
         \u2193
    RAG Retrieval \u2192 KB Answer
         \u2193
    Web Search (DuckDuckGo) \u2192 Recent Articles
         \u2193
    Contradiction Detection
         \u2193
    If contradiction found:
      \u2192 Add caveat: "Nota: [nuance from web]"
      \u2192 Or: "Questa risposta potrebbe essere incompleta. Verifica con [source]"

Usage:
    from app.services.web_verification import web_verification_service

    result = await web_verification_service.verify_answer(
        user_query="rottamazione quinquies tributi locali",
        kb_answer="Si possono rottamare i tributi locali.",
        kb_sources=[{"title": "Legge 199/2025"}],
    )

    if result.has_caveats:
        for caveat in result.caveats:
            response += f"\\n\\n{caveat}"
"""

import asyncio

from app.core.logging import logger

from .brave_search import BraveSearchClient
from .contradiction_detector import ContradictionDetector
from .keyword_extractor import KeywordExtractor
from .result_formatter import CaveatFormatter
from .synthesis import ResponseSynthesizer
from .types import WebVerificationResult


class WebVerificationService:
    """Service to verify KB answers against web search results.

    Detects contradictions and nuances between the KB answer and recent
    web articles to improve response quality.
    """

    # DEV-246: Brave Search API cost estimation
    # Free tier: 2,000 queries/month, then $3/1000 queries
    # We track all calls for cost reporting
    BRAVE_COST_PER_QUERY_EUR = 0.003  # ~\u20ac0.003 per query (~$3/1000)

    def __init__(
        self,
        timeout_seconds: float = 15.0,
        max_web_results: int = 5,
        keyword_extractor: KeywordExtractor | None = None,
        brave_client: BraveSearchClient | None = None,
        contradiction_detector: ContradictionDetector | None = None,
        caveat_formatter: CaveatFormatter | None = None,
        synthesizer: ResponseSynthesizer | None = None,
    ):
        """Initialize the web verification service.

        Args:
            timeout_seconds: Timeout for web search operations
            max_web_results: Maximum number of web results to check
            keyword_extractor: Optional keyword extractor (for testing)
            brave_client: Optional Brave client (for testing)
            contradiction_detector: Optional detector (for testing)
            caveat_formatter: Optional formatter (for testing)
            synthesizer: Optional synthesizer (for testing)
        """
        self._timeout_seconds = timeout_seconds
        self._max_web_results = max_web_results

        # Use injected dependencies or create defaults
        self._keyword_extractor = keyword_extractor or KeywordExtractor()
        self._brave_client = brave_client or BraveSearchClient(timeout_seconds, max_web_results)
        self._contradiction_detector = contradiction_detector or ContradictionDetector()
        self._caveat_formatter = caveat_formatter or CaveatFormatter()
        self._synthesizer = synthesizer or ResponseSynthesizer()

    async def verify_answer(
        self,
        user_query: str,
        kb_answer: str,
        kb_sources: list[dict],
        skip_for_chitchat: bool = False,
        existing_web_sources: list[dict] | None = None,
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> WebVerificationResult:
        """Verify a KB answer against web search results.

        DEV-245: With Parallel Hybrid RAG, web sources may already exist in state.
        If existing_web_sources is provided, skip the redundant web search and
        use those sources for contradiction detection instead.

        DEV-245 Phase 3.9: Accepts messages for context-aware keyword ordering
        in Brave web search. This ensures follow-up queries use correct
        keyword order (context first, then new keywords).

        DEV-245 Phase 5.3: Accepts topic_keywords for long conversation support.

        DEV-246: Accepts user_id and session_id for Brave API cost tracking.

        Args:
            user_query: The user's original question
            kb_answer: The answer generated from KB
            kb_sources: List of KB source metadata
            skip_for_chitchat: Whether to skip for chitchat queries
            existing_web_sources: DEV-245: Pre-fetched web sources from Parallel Hybrid RAG
            messages: DEV-245 Phase 3.9: Conversation history for context-aware keyword ordering
            topic_keywords: DEV-245 Phase 5.3: Pre-extracted topic keywords from state
            user_id: DEV-246: User ID for cost tracking
            session_id: DEV-246: Session ID for cost tracking

        Returns:
            WebVerificationResult with caveats if contradictions found
        """
        if skip_for_chitchat:
            return WebVerificationResult(verification_performed=False)

        if not user_query or not kb_answer:
            return WebVerificationResult(verification_performed=False)

        # DEV-245: If we already have web sources from Parallel Hybrid RAG,
        # use them for contradiction detection instead of making a new search
        if existing_web_sources:
            logger.info(
                "DEV245_using_existing_web_sources",
                existing_sources_count=len(existing_web_sources),
                skipping_web_search=True,
            )
            return self._verify_with_existing_sources(kb_answer, existing_web_sources)

        try:
            # Run verification with timeout (traditional path - new web search)
            # DEV-245 Phase 3.9: Pass messages for context-aware keyword ordering
            # DEV-245 Phase 5.3: Pass topic_keywords for long conversation support
            # DEV-246: Pass user_id/session_id for Brave API cost tracking
            result = await asyncio.wait_for(
                self._do_verification(
                    user_query, kb_answer, kb_sources, messages, topic_keywords, user_id, session_id
                ),
                timeout=self._timeout_seconds,
            )
            return result

        except TimeoutError:
            logger.warning(
                "web_verification_timeout",
                timeout_seconds=self._timeout_seconds,
            )
            return WebVerificationResult(
                verification_performed=False,
                error="Verification timed out",
            )

        except Exception as e:
            logger.error(
                "web_verification_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return WebVerificationResult(
                verification_performed=False,
                error=str(e),
            )

    def _verify_with_existing_sources(
        self,
        kb_answer: str,
        existing_web_sources: list[dict],
    ) -> WebVerificationResult:
        """Verify answer using pre-fetched web sources from Parallel Hybrid RAG.

        DEV-245: This skips the web search call since we already have web sources
        from the retrieval phase. No LLM synthesis is needed since the main LLM
        already received both KB and web context.

        Args:
            kb_answer: The KB-generated answer
            existing_web_sources: Web sources from state (web_sources_metadata)

        Returns:
            WebVerificationResult with caveats from existing sources
        """
        # Convert web_sources_metadata format to web search result format
        web_results = []
        for source in existing_web_sources:
            web_results.append(
                {
                    "title": source.get("title", ""),
                    "snippet": source.get("excerpt", source.get("title", "")),  # Use excerpt if available
                    "link": source.get("url", ""),
                    "is_ai_synthesis": source.get("is_ai_synthesis", False),
                }
            )

        if not web_results:
            return WebVerificationResult(
                verification_performed=True,
                web_sources_checked=0,
            )

        # Detect contradictions using existing sources
        contradictions = self._contradiction_detector.detect_contradictions(kb_answer, web_results)

        # Generate deduplicated caveats
        caveats = self._caveat_formatter.deduplicate_and_format_caveats(contradictions)

        logger.info(
            "DEV245_verification_with_existing_sources_complete",
            web_sources_checked=len(web_results),
            contradictions_found=len(contradictions),
            caveats_generated=len(caveats),
        )

        return WebVerificationResult(
            caveats=caveats,
            contradictions=contradictions,
            web_sources_checked=len(web_results),
            verification_performed=True,
            # No synthesis - LLM already received both KB and web context
            brave_ai_summary=None,
            synthesized_response=None,
        )

    async def _do_verification(
        self,
        user_query: str,
        kb_answer: str,
        kb_sources: list[dict],
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> WebVerificationResult:
        """Perform the actual verification logic.

        DEV-245 Phase 3.9: Accepts messages for context-aware keyword ordering.
        DEV-245 Phase 5.3: Accepts topic_keywords for long conversation support.
        DEV-246: Accepts user_id and session_id for Brave API cost tracking.

        Args:
            user_query: User's query
            kb_answer: KB-generated answer
            kb_sources: KB source metadata
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)
            messages: Conversation history for context-aware keyword ordering
            user_id: DEV-246: User ID for cost tracking
            session_id: DEV-246: Session ID for cost tracking

        Returns:
            WebVerificationResult
        """
        # Build search query focused on finding contradictions/updates
        # DEV-245 Phase 3.9: Pass messages for context-aware keyword ordering
        # DEV-245 Phase 5.3: Pass topic_keywords for long conversation support
        search_query = self._build_verification_query(user_query, kb_sources, messages, topic_keywords)

        # Search the web
        # DEV-246: Pass user_id/session_id for Brave API cost tracking
        web_results = await self._search_web(search_query, user_id, session_id)

        if not web_results:
            logger.debug(
                "web_verification_no_results",
                search_query=search_query[:100],
            )
            return WebVerificationResult(
                verification_performed=True,
                web_sources_checked=0,
            )

        # Extract Brave AI summary if available (result with is_ai_synthesis=True)
        brave_ai_summary = None
        for result in web_results:
            if result.get("is_ai_synthesis"):
                brave_ai_summary = result.get("snippet")
                break

        # Synthesize KB + web for enriched response
        synthesized_response = None
        if brave_ai_summary:
            # Option 1: Use Brave AI summary (premium tier)
            logger.info(
                "BRAVE_ai_summary_found",
                summary_length=len(brave_ai_summary),
            )
            synthesized_response = await self.synthesize_with_brave(
                kb_answer=kb_answer,
                brave_summary=brave_ai_summary,
                user_query=user_query,
            )
        elif web_results:
            # Option 2: Fallback to snippet-based synthesis (free tier)
            logger.info(
                "BRAVE_using_snippet_synthesis",
                web_results_count=len(web_results),
            )
            synthesized_response = await self.synthesize_with_snippets(
                kb_answer=kb_answer,
                web_results=web_results,
                user_query=user_query,
            )
        else:
            logger.debug(
                "BRAVE_no_synthesis_possible",
                reason="no AI summary and no web results",
            )

        # Detect contradictions
        contradictions = self._detect_contradictions(kb_answer, web_results)

        # Generate deduplicated caveats with merged sources
        caveats = self._deduplicate_and_format_caveats(contradictions)

        logger.info(
            "BRAVE_web_verification_complete",
            web_sources_checked=len(web_results),
            contradictions_found=len(contradictions),
            caveats_generated=len(caveats),
            has_ai_summary=bool(brave_ai_summary),
            has_synthesized_response=bool(synthesized_response),
        )

        return WebVerificationResult(
            caveats=caveats,
            contradictions=contradictions,
            web_sources_checked=len(web_results),
            verification_performed=True,
            brave_ai_summary=brave_ai_summary,
            synthesized_response=synthesized_response,
        )

    # Delegate methods to maintain API compatibility

    def _extract_search_keywords(self, query: str) -> list[str]:
        """Extract significant keywords from query for Brave search."""
        return self._keyword_extractor.extract_search_keywords(query)

    def _extract_search_keywords_with_context(
        self,
        query: str,
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
    ) -> list[str]:
        """Extract keywords with context-first ordering."""
        return self._keyword_extractor.extract_search_keywords_with_context(query, messages, topic_keywords)

    def _build_verification_query(
        self,
        user_query: str,
        kb_sources: list[dict],
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
    ) -> str:
        """Build keyword-based search query with context-first ordering."""
        return self._keyword_extractor.build_verification_query(user_query, kb_sources, messages, topic_keywords)

    async def _search_web(
        self,
        query: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict]:
        """Search the web using Brave Search API with AI summarization.

        Falls back to DuckDuckGo if Brave API key is not configured.

        Args:
            query: Search query
            user_id: User ID for cost tracking
            session_id: Session ID for cost tracking

        Returns:
            List of search result dicts
        """
        import time

        try:
            from app.core.config import settings

            if not settings.BRAVE_SEARCH_API_KEY:
                logger.info("BRAVE_not_configured", fallback="duckduckgo")
                return await self._search_web_duckduckgo(query)

            logger.info("BRAVE_search_starting", query=query[:80])

            import httpx

            headers = {
                "X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY,
                "Accept": "application/json",
            }

            start_time = time.time()
            api_calls = 0

            async with httpx.AsyncClient() as client:
                search_data = await self._brave_client._call_brave_search(client, query, headers)
                api_calls += 1
                ai_summary = await self._brave_client._get_brave_summary(client, search_data, headers)
                if ai_summary:
                    api_calls += 1  # Summarizer is a separate API call

            response_time_ms = int((time.time() - start_time) * 1000)

            # DEV-246: Track Brave API cost
            await self._brave_client._track_brave_api_usage(
                user_id=user_id,
                session_id=session_id,
                api_calls=api_calls,
                response_time_ms=response_time_ms,
            )

            results = self._brave_client._parse_brave_results(search_data, ai_summary)

            logger.info(
                "BRAVE_search_complete",
                query=query[:50],
                results_count=len(results),
                has_ai_summary=bool(ai_summary),
                ai_summary_preview=ai_summary[:100] if ai_summary else None,
            )

            return results[: self._max_web_results]

        except Exception as e:
            logger.warning(
                "BRAVE_search_failed",
                query=query[:100],
                error=str(e),
                error_type=type(e).__name__,
                fallback="duckduckgo",
            )
            return await self._search_web_duckduckgo(query)

    async def _search_web_duckduckgo(self, query: str) -> list[dict]:
        """Fallback to DuckDuckGo search (no AI synthesis)."""
        return await self._brave_client._search_duckduckgo(query)

    async def _track_brave_api_usage(
        self,
        user_id: str | None,
        session_id: str | None,
        api_calls: int,
        response_time_ms: int,
        error_occurred: bool = False,
    ) -> None:
        """Track Brave Search API usage for cost reporting."""
        await self._brave_client._track_brave_api_usage(
            user_id, session_id, api_calls, response_time_ms, error_occurred
        )

    def _detect_contradictions(
        self,
        kb_answer: str,
        web_results: list[dict],
    ) -> list:
        """Detect contradictions between KB answer and web results."""
        return self._contradiction_detector.detect_contradictions(kb_answer, web_results)

    def _calculate_contradiction_confidence(
        self,
        kb_answer: str,
        web_snippet: str,
        topic: str,
        is_ai_synthesis: bool = False,
    ) -> float:
        """Calculate confidence score for a contradiction."""
        return self._contradiction_detector._calculate_contradiction_confidence(
            kb_answer, web_snippet, topic, is_ai_synthesis
        )

    def _deduplicate_and_format_caveats(self, contradictions: list) -> list[str]:
        """Group contradictions by type and merge sources into deduplicated caveats."""
        return self._caveat_formatter.deduplicate_and_format_caveats(contradictions)

    def _generate_caveat(self, contradiction) -> str | None:
        """Generate a caveat message for a contradiction (legacy method)."""
        return self._caveat_formatter.generate_caveat(contradiction)

    async def synthesize_with_snippets(
        self,
        kb_answer: str,
        web_results: list[dict],
        user_query: str,
    ) -> str | None:
        """Use LLM to merge KB answer with web snippets."""
        return await self._synthesizer.synthesize_with_snippets(kb_answer, web_results, user_query)

    async def synthesize_with_brave(
        self,
        kb_answer: str,
        brave_summary: str,
        user_query: str,
    ) -> str | None:
        """Use LLM to merge KB answer with Brave AI insights."""
        return await self._synthesizer.synthesize_with_brave(kb_answer, brave_summary, user_query)


# Singleton instance for convenience
web_verification_service = WebVerificationService()
