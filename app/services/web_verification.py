r"""Web Verification Service for DEV-245 Phase 3.1.

Verifies KB answers against web search results to detect contradictions
and add caveats when the KB answer may be incomplete or outdated.

Architecture:
    User Question
         ↓
    RAG Retrieval → KB Answer
         ↓
    Web Search (DuckDuckGo) → Recent Articles
         ↓
    Contradiction Detection
         ↓
    If contradiction found:
      → Add caveat: "Nota: [nuance from web]"
      → Or: "Questa risposta potrebbe essere incompleta. Verifica con [source]"

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
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.core.logging import logger

if TYPE_CHECKING:
    import httpx


@dataclass
class ContradictionInfo:
    """Information about a detected contradiction between KB and web."""

    topic: str  # What the contradiction is about
    kb_claim: str  # What the KB says
    web_claim: str  # What the web says
    source_url: str  # Web source URL
    source_title: str  # Web source title
    confidence: float  # Confidence in the contradiction (0.0-1.0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "topic": self.topic,
            "kb_claim": self.kb_claim,
            "web_claim": self.web_claim,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "confidence": self.confidence,
        }


@dataclass
class WebVerificationResult:
    """Result of web verification."""

    caveats: list[str] = field(default_factory=list)
    contradictions: list[ContradictionInfo] = field(default_factory=list)
    web_sources_checked: int = 0
    verification_performed: bool = False
    error: str | None = None
    # DEV-245: Brave AI synthesis fields
    brave_ai_summary: str | None = None  # Raw Brave AI summary
    synthesized_response: str | None = None  # LLM-synthesized KB + Brave response

    @property
    def has_synthesized_response(self) -> bool:
        """Check if a synthesized response is available."""
        return self.synthesized_response is not None and len(self.synthesized_response) > 0

    @property
    def has_caveats(self) -> bool:
        """Check if any caveats were generated."""
        return len(self.caveats) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "caveats": self.caveats,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "web_sources_checked": self.web_sources_checked,
            "verification_performed": self.verification_performed,
            "has_caveats": self.has_caveats,
            "error": self.error,
            # DEV-245: Brave AI synthesis fields
            "brave_ai_summary": self.brave_ai_summary,
            "synthesized_response": self.synthesized_response,
            "has_synthesized_response": self.has_synthesized_response,
        }


# Keywords that indicate potential contradictions
CONTRADICTION_KEYWORDS = {
    # Italian negation/exception words
    "non",
    "esclusi",
    "escluso",
    "esclusa",
    "tranne",
    "eccetto",
    "salvo",
    "ma",
    "però",
    "tuttavia",
    "invece",
    "attenzione",
    "importante",
    "dipende",
    "richiede",
    "necessario",
    "obbligatorio",
    "condizione",
    "requisito",
    "limite",
    "limitato",
    "solo",
    "soltanto",
    "parzialmente",
    "accordo",
    "delibera",
    "ente locale",
    # Date-related (potential updates)
    "prorogato",
    "prorogata",
    "proroga",
    "posticipato",
    "posticipata",
    "rinviato",
    "rinviata",
    "nuova scadenza",
    "aggiornato",
    "aggiornata",
    "modificato",
    "modificata",
}

# Topics that often have nuances requiring caveats
SENSITIVE_TOPICS = {
    "tributi locali",
    "imu",
    "tasi",
    "tasse auto",
    "bollo auto",
    "irap",
    "accertamento",
    "ente locale",
    "comune",
    "regione",
    "provincia",
}

# DEV-245 Phase 5.14: Keywords indicating genuine exclusions in web content
# Used to determine whether to use ✅/❌ format in synthesis prompts
EXCLUSION_KEYWORDS = {
    # Direct exclusions
    "escluso",
    "esclusa",
    "esclusi",
    "escluse",
    "non ammesso",
    "non ammessa",
    "non ammessi",
    "non rientra",
    "non rientrano",
    "non può",
    "non possono",
    # Conditional limitations
    "tranne",
    "eccetto",
    "salvo",
    "a condizione",
    "solo se",
    "dipende da",
    "richiede",
    # Specific to rottamazione/fiscal domain
    "delibera comunale",
    "delibera dell'ente",
    "accordo",
    "adesione dell'ente",
}

# Minimum confidence threshold for generating caveats
MIN_CAVEAT_CONFIDENCE = 0.5


def _web_has_genuine_exclusions(web_results: list[dict]) -> tuple[bool, list[str]]:
    """DEV-245 Phase 5.14: Check if web results contain genuine exclusion content.

    Used to determine whether to use ✅/❌ format in synthesis prompts.
    Only use the inclusion/exclusion format when web results ACTUALLY contain
    exclusion keywords, not for general informational queries.

    Args:
        web_results: List of web search results with snippets

    Returns:
        Tuple of (has_exclusions: bool, matched_keywords: list[str])
    """
    matched: list[str] = []
    for result in web_results:
        snippet = result.get("snippet", "").lower()
        for keyword in EXCLUSION_KEYWORDS:
            if keyword in snippet:
                matched.append(keyword)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_matched: list[str] = []
    for kw in matched:
        if kw not in seen:
            seen.add(kw)
            unique_matched.append(kw)

    return (len(unique_matched) > 0, unique_matched)


class WebVerificationService:
    """Service to verify KB answers against web search results.

    Detects contradictions and nuances between the KB answer and recent
    web articles to improve response quality.
    """

    def __init__(self, timeout_seconds: float = 15.0, max_web_results: int = 5):
        """Initialize the web verification service.

        Args:
            timeout_seconds: Timeout for web search operations
            max_web_results: Maximum number of web results to check
        """
        self._timeout_seconds = timeout_seconds
        self._max_web_results = max_web_results

    async def verify_answer(
        self,
        user_query: str,
        kb_answer: str,
        kb_sources: list[dict],
        skip_for_chitchat: bool = False,
        existing_web_sources: list[dict] | None = None,
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
    ) -> WebVerificationResult:
        """Verify a KB answer against web search results.

        DEV-245: With Parallel Hybrid RAG, web sources may already exist in state.
        If existing_web_sources is provided, skip the redundant web search and
        use those sources for contradiction detection instead.

        DEV-245 Phase 3.9: Accepts messages for context-aware keyword ordering
        in Brave web search. This ensures follow-up queries use correct
        keyword order (context first, then new keywords).

        DEV-245 Phase 5.3: Accepts topic_keywords for long conversation support.

        Args:
            user_query: The user's original question
            kb_answer: The answer generated from KB
            kb_sources: List of KB source metadata
            skip_for_chitchat: Whether to skip for chitchat queries
            existing_web_sources: DEV-245: Pre-fetched web sources from Parallel Hybrid RAG
            messages: DEV-245 Phase 3.9: Conversation history for context-aware keyword ordering
            topic_keywords: DEV-245 Phase 5.3: Pre-extracted topic keywords from state

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
            result = await asyncio.wait_for(
                self._do_verification(user_query, kb_answer, kb_sources, messages, topic_keywords),
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
        contradictions = self._detect_contradictions(kb_answer, web_results)

        # Generate deduplicated caveats
        caveats = self._deduplicate_and_format_caveats(contradictions)

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
    ) -> WebVerificationResult:
        """Perform the actual verification logic.

        DEV-245 Phase 3.9: Accepts messages for context-aware keyword ordering.
        DEV-245 Phase 5.3: Accepts topic_keywords for long conversation support.

        Args:
            user_query: User's query
            kb_answer: KB-generated answer
            kb_sources: KB source metadata
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)
            messages: Conversation history for context-aware keyword ordering

        Returns:
            WebVerificationResult
        """
        # Build search query focused on finding contradictions/updates
        # DEV-245 Phase 3.9: Pass messages for context-aware keyword ordering
        # DEV-245 Phase 5.3: Pass topic_keywords for long conversation support
        search_query = self._build_verification_query(user_query, kb_sources, messages, topic_keywords)

        # Search the web
        web_results = await self._search_web(search_query)

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

    def _extract_search_keywords(self, query: str) -> list[str]:
        """DEV-245 Phase 3.9: Extract significant keywords from query for Brave search.

        Natural language questions don't search well. Converting to keywords:
        "L'IRAP può essere inclusa nella rottamazione quinquies?"
        → ["irap", "rottamazione", "quinquies"]

        Args:
            query: The user query (natural language)

        Returns:
            List of significant keywords for search (lowercase), max 5 keywords
        """
        import re

        # Italian stop words to exclude (common words that don't add search value)
        stop_words = {
            # Articles
            "il",
            "lo",
            "la",
            "i",
            "gli",
            "le",
            "un",
            "uno",
            "una",
            # Prepositions
            "di",
            "a",
            "da",
            "in",
            "con",
            "su",
            "per",
            "tra",
            "fra",
            # Conjunctions
            "e",
            "o",
            "ma",
            "se",
            "che",
            "chi",
            # Question words
            "come",
            "dove",
            "quando",
            "perché",
            "quale",
            "quali",
            # Pronouns/demonstratives
            "questo",
            "quello",
            "suo",
            "loro",
            "mio",
            "tuo",
            # Common verbs
            "essere",
            "avere",
            "può",
            "sono",
            "è",
            "sia",
            "viene",
            "fare",
            # Preposition contractions
            "nel",
            "nella",
            "nei",
            "nelle",
            "del",
            "della",
            "dei",
            "delle",
            "al",
            "alla",
            "ai",
            "alle",
            "dal",
            "dalla",
            "sul",
            "sulla",
            # Other common words
            "non",
            "più",
            "anche",
            "solo",
            "già",
            "cosa",
            "tutto",
            "molto",
            # Question-specific
            "inclusa",
            "incluso",
            "rientra",
            "rientrare",
            "previsto",
            "prevista",
            # Conversational verbs
            "parlami",
            "dimmi",
            "spiegami",
            "raccontami",
            "descrivi",
            "vorrei",
            "sapere",
            "conoscere",
            "capire",
        }

        # Extract words (alphanumeric including Italian accents, 3+ chars)
        words = re.findall(r"\b[a-zA-ZàèéìòùÀÈÉÌÒÙ]{3,}\b", query.lower())

        # Filter out stop words, keep significant terms
        keywords = [w for w in words if w not in stop_words]

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        return unique[:5]  # Cap at 5 keywords for focused search

    def _extract_search_keywords_with_context(
        self,
        query: str,
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
    ) -> list[str]:
        """DEV-245 Phase 3.9: Extract keywords with context-first ordering.

        CRITICAL: Do NOT remove this method - it ensures Brave search uses
        optimal keyword ordering for follow-up queries.

        Industry standard (BruceClay): "Most relevant keyword first"

        For follow-up queries, orders keywords so conversation context comes first,
        then new keywords from the follow-up.

        Example:
            - Context: "parlami della rottamazione quinquies"
            - Follow-up: "L'IRAP può essere inclusa nella rottamazione quinquies?"
            - Result: ["rottamazione", "quinquies", "irap"] (context first!)
            - Brave search: "rottamazione quinquies irap 2026" ✅
            - NOT: "irap rottamazione quinquies 2026" ❌

        DEV-245 Phase 5.3: Added topic_keywords parameter.
            If topic_keywords is provided, use those as context keywords (from state).
            This ensures the main topic is NEVER lost, even at Q4+ where messages[-4:]
            would exclude the first query/response.

        Args:
            query: The user query
            messages: Conversation history for context extraction
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)

        Returns:
            List of keywords ordered: context keywords first, then new keywords
        """
        # Extract all keywords from query
        all_keywords = self._extract_search_keywords(query)

        # DEV-245 Phase 5.3: Check for topic_keywords FIRST before early return
        # If we have topic_keywords, we need to add them even if query has few keywords
        # DEV-245 Phase 5.4: Type safety - validate topic_keywords is actually a list
        if topic_keywords and isinstance(topic_keywords, list):
            # Use pre-extracted topic keywords from state (industry standard approach)
            # IMPORTANT: We ADD topic_keywords to the result, not just use them for ordering
            # This ensures the main topic is always in the search, even if not mentioned in query
            context_keywords = set(topic_keywords)
            logger.debug(
                "phase53_using_topic_keywords_web_verification",
                topic_keywords=topic_keywords,
            )

            # Combine: topic keywords first (context), then new query keywords
            new_keywords = [kw for kw in all_keywords if kw not in context_keywords]
            result = list(topic_keywords) + new_keywords
            result = result[:5]  # Cap at 5 keywords

            # Log for debugging
            if new_keywords:
                logger.debug(
                    "phase53_keyword_ordering_web_verification",
                    topic_keywords=topic_keywords,
                    query_keywords=all_keywords,
                    combined=result,
                )

            return result

        if len(all_keywords) <= 2:
            return all_keywords  # No reordering needed

        # DEV-245 Phase 5.3: Fallback path (no topic_keywords provided)
        # Extract context from messages for reordering
        fallback_context_keywords: set[str] = set()

        if messages:
            # DEV-245 Phase 3.9.3: Skip the LAST assistant message - it's the one we're verifying
            # At Step 100, the newest assistant message is the response just generated by LLM.
            # We want context from PREVIOUS assistant responses, not the current one.
            # Without this, ALL keywords become "context" and no reordering happens.
            #
            # Example:
            #   messages = [user1, assistant1 (old), user2, assistant2 (NEW)]
            #   We want context from assistant1, NOT assistant2
            messages_to_check = list(messages[-4:])  # Copy to avoid mutating original

            # Skip the last message if it's an assistant message (the one we're verifying)
            if messages_to_check:
                last_msg = messages_to_check[-1]
                if isinstance(last_msg, dict):
                    last_role = last_msg.get("role") or last_msg.get("type", "")
                else:
                    last_role = getattr(last_msg, "role", "") or getattr(last_msg, "type", "")

                if last_role in ("assistant", "ai"):
                    messages_to_check = messages_to_check[:-1]  # Exclude the newest assistant

            # Find context keywords from conversation history (excluding newest assistant)
            for msg in reversed(messages_to_check):
                # Handle both dict and LangChain message objects
                if isinstance(msg, dict):
                    # DEV-245 Phase 3.9.2: Check BOTH keys - dicts may use "role" (OpenAI)
                    # or "type" (LangChain serialization format)
                    role = msg.get("role") or msg.get("type", "")
                    content = msg.get("content", "")
                else:
                    role = getattr(msg, "role", "") or getattr(msg, "type", "")
                    content = getattr(msg, "content", "") or ""

                # DEV-245 Phase 3.9.1: Only extract context from ASSISTANT messages
                # User messages include the current follow-up query which would
                # incorrectly add new keywords to context, breaking the ordering
                if role in ("assistant", "ai") and content:
                    # Extract keywords from context message (first 500 chars)
                    msg_keywords = self._extract_search_keywords(content[:500])
                    fallback_context_keywords.update(msg_keywords[:5])

        # Separate: context keywords vs new keywords
        context_first = [kw for kw in all_keywords if kw in fallback_context_keywords]
        new_keywords = [kw for kw in all_keywords if kw not in fallback_context_keywords]

        result = context_first + new_keywords

        # Log for debugging keyword ordering
        if context_first and new_keywords:
            logger.debug(
                "web_verification_keyword_ordering",
                original_order=all_keywords,
                context_keywords=list(fallback_context_keywords)[:5],
                reordered=result,
            )

        return result

    def _build_verification_query(
        self,
        user_query: str,
        kb_sources: list[dict],  # Kept for API compatibility but not used
        messages: list[dict] | None = None,
        topic_keywords: list[str] | None = None,
    ) -> str:
        """DEV-245 Phase 3.9: Build keyword-based search query with context-first ordering.

        CRITICAL: This method uses keyword extraction instead of full natural language
        query because Brave search returns better results with keywords.

        Previous behavior (wrong): "L'IRAP può essere inclusa nella rottamazione quinquies? 2026"
        Current behavior (correct): "rottamazione quinquies irap 2026"

        DEV-245 Phase 5.3: Added topic_keywords for long conversation support.

        Args:
            user_query: Original user query
            kb_sources: KB sources (unused - kept for API compatibility)
            messages: Conversation history for context-aware keyword ordering
            topic_keywords: Pre-extracted topic keywords from state (Phase 5.3)

        Returns:
            Keyword-based search query string
        """
        # DEV-245 Phase 3.9: Use context-aware keyword extraction
        # DEV-245 Phase 5.3: Pass topic_keywords for long conversation support
        keywords = self._extract_search_keywords_with_context(user_query, messages, topic_keywords)

        if keywords:
            query = " ".join(keywords)
        else:
            # Fallback to original query if no keywords extracted
            query = user_query.strip()

        # DEV-245 Phase 3.9.1: Removed automatic year suffix per user feedback
        # Let Brave search naturally without forcing a year

        logger.debug(
            "web_verification_query_built",
            original_query=user_query[:80],
            keywords=keywords,
            final_query=query,
        )

        return query

    async def _search_web(self, query: str) -> list[dict]:
        """Search the web using Brave Search API with AI summarization.

        Falls back to DuckDuckGo if Brave API key is not configured.

        Args:
            query: Search query

        Returns:
            List of search result dicts with title, snippet, link, is_ai_synthesis
        """
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

            async with httpx.AsyncClient() as client:
                search_data = await self._call_brave_search(client, query, headers)
                ai_summary = await self._get_brave_summary(client, search_data, headers)

            results = self._parse_brave_results(search_data, ai_summary)

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

    async def _call_brave_search(self, client: "httpx.AsyncClient", query: str, headers: dict) -> dict:
        """Call Brave Search API with summary flag.

        Args:
            client: httpx AsyncClient
            query: Search query
            headers: Request headers with API key

        Returns:
            Search response data dict
        """
        logger.debug("BRAVE_api_call_starting", endpoint="web/search")

        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={
                "q": query,
                "summary": 1,
                "count": self._max_web_results,
            },
            headers=headers,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        web_results_count = len(data.get("web", {}).get("results", []))
        has_summarizer_key = bool(data.get("summarizer", {}).get("key"))

        logger.info(
            "BRAVE_api_call_complete",
            endpoint="web/search",
            status_code=response.status_code,
            web_results_count=web_results_count,
            has_summarizer_key=has_summarizer_key,
        )

        return data

    async def _get_brave_summary(self, client: "httpx.AsyncClient", search_data: dict, headers: dict) -> str | None:
        """Fetch AI summary from Brave Summarizer (FREE, doesn't count toward quota).

        Args:
            client: httpx AsyncClient
            search_data: Search response containing summarizer key
            headers: Request headers with API key

        Returns:
            AI summary text or None if unavailable
        """
        summarizer_key = search_data.get("summarizer", {}).get("key")
        if not summarizer_key:
            logger.debug("BRAVE_summarizer_no_key", reason="no summarizer key in response")
            return None

        logger.debug("BRAVE_summarizer_starting", key_preview=summarizer_key[:20] + "...")

        try:
            response = await client.get(
                "https://api.search.brave.com/res/v1/summarizer/search",
                params={"key": summarizer_key, "entity_info": 1},
                headers=headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            summary_data = response.json()
            status = summary_data.get("status")

            if status == "complete":
                summary_text = summary_data.get("summary", {}).get("text")
                logger.info(
                    "BRAVE_summarizer_complete",
                    status=status,
                    summary_length=len(summary_text) if summary_text else 0,
                )
                return summary_text
            else:
                logger.warning("BRAVE_summarizer_incomplete", status=status)
                return None

        except Exception as e:
            logger.warning(
                "BRAVE_summarizer_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def _parse_brave_results(self, search_data: dict, ai_summary: str | None) -> list[dict]:
        """Parse Brave search results into standard format.

        Args:
            search_data: Raw Brave search response
            ai_summary: AI summary text if available

        Returns:
            List of result dicts with title, snippet, link, is_ai_synthesis
        """
        results: list[dict] = []

        if ai_summary:
            results.append(
                {
                    "title": "Brave AI Summary",
                    "snippet": ai_summary,
                    "link": "",
                    "is_ai_synthesis": True,
                }
            )

        for item in search_data.get("web", {}).get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("description", ""),
                    "link": item.get("url", ""),
                    "is_ai_synthesis": False,
                }
            )

        return results

    async def _search_web_duckduckgo(self, query: str) -> list[dict]:
        """Fallback to DuckDuckGo search (no AI synthesis).

        Args:
            query: Search query

        Returns:
            List of search result dicts with title, snippet, link
        """
        try:
            # Lazy import to avoid circular dependencies
            from app.core.langgraph.tools.duckduckgo_search import duckduckgo_search_tool

            # Run DuckDuckGo search
            raw_results = await asyncio.to_thread(
                duckduckgo_search_tool.invoke,
                query,
            )

            # Parse results (DuckDuckGo returns string of results)
            results = self._parse_duckduckgo_results(raw_results)

            return results[: self._max_web_results]

        except Exception as e:
            logger.warning(
                "duckduckgo_search_failed",
                query=query[:100],
                error=str(e),
            )
            return []

    def _parse_duckduckgo_results(self, raw_results: str) -> list[dict]:
        """Parse DuckDuckGo search results string.

        Args:
            raw_results: Raw string from DuckDuckGo

        Returns:
            List of parsed result dicts
        """
        results = []

        if (
            not raw_results
            or isinstance(raw_results, str)
            and "No good DuckDuckGo Search Result was found" in raw_results
        ):
            return results

        # DuckDuckGo returns results in format: [title](url) snippet...
        # or as structured data depending on langchain version
        if isinstance(raw_results, list):
            for item in raw_results:
                if isinstance(item, dict):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", item.get("body", "")),
                            "link": item.get("link", item.get("url", "")),
                        }
                    )
        elif isinstance(raw_results, str):
            # Parse string format
            lines = raw_results.split("\n")
            for line in lines:
                # Try to extract link and title
                link_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", line)
                if link_match:
                    title = link_match.group(1)
                    url = link_match.group(2)
                    # Get snippet (rest of line after link)
                    snippet = line[link_match.end() :].strip()
                    if not snippet:
                        snippet = title
                    results.append(
                        {
                            "title": title,
                            "snippet": snippet,
                            "link": url,
                        }
                    )
                elif line.strip():
                    # Fallback: use line as snippet
                    results.append(
                        {
                            "title": "Web Result",
                            "snippet": line.strip(),
                            "link": "",
                        }
                    )

        return results

    def _detect_contradictions(
        self,
        kb_answer: str,
        web_results: list[dict],
    ) -> list[ContradictionInfo]:
        """Detect contradictions between KB answer and web results.

        Args:
            kb_answer: The KB-generated answer
            web_results: Web search results (may include is_ai_synthesis flag)

        Returns:
            List of detected contradictions
        """
        contradictions = []
        kb_lower = kb_answer.lower()

        for result in web_results:
            snippet = result.get("snippet", "")
            if not snippet:
                continue

            detected = self._find_contradiction_indicators(snippet.lower(), kb_lower)
            if detected:
                contradiction = self._build_contradiction(result, detected, kb_answer)
                contradictions.append(contradiction)

        logger.debug(
            "web_verification_contradictions_detected",
            count=len(contradictions),
            topics=[c.topic for c in contradictions],
        )

        return contradictions

    def _find_contradiction_indicators(self, snippet_lower: str, kb_lower: str) -> tuple[str, str] | None:
        """Find contradiction indicators between snippet and KB answer.

        Args:
            snippet_lower: Lowercased web snippet
            kb_lower: Lowercased KB answer

        Returns:
            Tuple of (detected_topic, web_claim) or None if no contradiction
        """
        for keyword in CONTRADICTION_KEYWORDS:
            if keyword not in snippet_lower:
                continue

            # Check if this is about a topic mentioned in KB
            for sensitive_topic in SENSITIVE_TOPICS:
                if sensitive_topic in kb_lower and sensitive_topic in snippet_lower:
                    return (sensitive_topic, snippet_lower[:200])

            # Check for date/deadline contradictions
            has_date_topic = any(term in kb_lower for term in ["scadenza", "data", "termine"])
            date_keywords = ["prorogato", "prorogata", "proroga", "posticipato", "nuova scadenza"]
            if has_date_topic and keyword in date_keywords:
                return ("scadenza/data", snippet_lower[:200])

        return None

    def _build_contradiction(
        self,
        result: dict,
        detected: tuple[str, str],
        kb_answer: str,
    ) -> ContradictionInfo:
        """Build a ContradictionInfo from detection results.

        Args:
            result: Web search result dict
            detected: Tuple of (topic, web_claim)
            kb_answer: Original KB answer

        Returns:
            ContradictionInfo instance
        """
        topic, web_claim = detected
        is_ai_synthesis = result.get("is_ai_synthesis", False)

        confidence = self._calculate_contradiction_confidence(
            kb_answer, result.get("snippet", ""), topic, is_ai_synthesis
        )

        return ContradictionInfo(
            topic=topic,
            kb_claim=self._extract_kb_claim(kb_answer, topic),
            web_claim=web_claim,
            source_url=result.get("link", ""),
            source_title=result.get("title", ""),
            confidence=confidence,
        )

    def _calculate_contradiction_confidence(
        self,
        kb_answer: str,
        web_snippet: str,
        topic: str,
        is_ai_synthesis: bool = False,
    ) -> float:
        """Calculate confidence score for a contradiction.

        Args:
            kb_answer: KB answer text
            web_snippet: Web snippet text
            topic: Detected topic
            is_ai_synthesis: Whether the web snippet is from AI synthesis (Brave AI)

        Returns:
            Confidence score 0.0-1.0
        """
        # AI synthesis gets higher base confidence (0.65 vs 0.5)
        confidence = 0.65 if is_ai_synthesis else 0.5

        # Higher confidence if topic is specific
        if topic in SENSITIVE_TOPICS:
            confidence += 0.15

        # Higher confidence if web snippet has specific details
        if re.search(r"\d{1,2}/\d{1,2}/\d{4}", web_snippet):  # Contains date
            confidence += 0.1
        if re.search(r"art\.?\s*\d+", web_snippet, re.IGNORECASE):  # Contains article ref
            confidence += 0.1

        # Higher confidence if contradiction keyword is explicit
        explicit_keywords = ["non", "esclusi", "escluso", "richiede", "dipende", "accordo"]
        if any(kw in web_snippet.lower() for kw in explicit_keywords):
            confidence += 0.15

        return min(confidence, 1.0)

    def _extract_kb_claim(self, kb_answer: str, topic: str) -> str:
        """Extract the KB's claim about a topic.

        Args:
            kb_answer: Full KB answer
            topic: Topic to extract claim for

        Returns:
            Extracted claim string
        """
        # Find sentence containing the topic
        sentences = re.split(r"[.!?]", kb_answer)
        for sentence in sentences:
            if topic in sentence.lower():
                return sentence.strip()[:200]

        # Fallback: return first 100 chars
        return kb_answer[:100]

    def _get_caveat_type(self, contradiction: ContradictionInfo) -> str | None:
        """Get caveat type for a contradiction.

        Returns:
            Caveat type string or None if confidence too low
        """
        if contradiction.confidence < MIN_CAVEAT_CONFIDENCE:
            return None

        topic_lower = contradiction.topic.lower()

        if "scadenza" in topic_lower or "data" in topic_lower:
            return "scadenza"

        if any(t in topic_lower for t in ["tributi locali", "imu", "tasi", "tasse auto", "bollo"]):
            return "tributi_locali"

        if "irap" in topic_lower:
            return "irap"

        return "generic"

    def _get_caveat_text(self, caveat_type: str, topic: str) -> str:
        """Get caveat text without source links.

        Args:
            caveat_type: Type of caveat (scadenza, tributi_locali, irap, generic)
            topic: Original topic for context

        Returns:
            Caveat text string
        """
        if caveat_type == "scadenza":
            return (
                "**Nota sulla scadenza:** Fonti recenti indicano possibili aggiornamenti "
                "alle date. Verifica le scadenze ufficiali prima di procedere."
            )

        if caveat_type == "tributi_locali":
            return (
                f"**Nota sui tributi locali:** La definizione agevolata per tributi locali "
                f"come {topic} potrebbe richiedere l'accordo dell'ente locale competente. "
                f"Verifica con il tuo Comune/Regione."
            )

        if caveat_type == "irap":
            return (
                "**Nota sull'IRAP:** Potrebbero esserci distinzioni tra IRAP da dichiarazione "
                "e IRAP da accertamento. Verifica i criteri di ammissibilità specifici."
            )

        # Generic
        return (
            "**Nota:** Fonti recenti suggeriscono informazioni aggiuntive su questo argomento. "
            "Verifica con fonti ufficiali per i dettagli più aggiornati."
        )

    def _deduplicate_and_format_caveats(self, contradictions: list[ContradictionInfo]) -> list[str]:
        """Group contradictions by type and merge sources into deduplicated caveats.

        Args:
            contradictions: List of ContradictionInfo objects

        Returns:
            List of deduplicated caveat strings with merged source links
        """
        # Group by caveat type
        by_type: dict[str, list[ContradictionInfo]] = {}
        for c in contradictions:
            caveat_type = self._get_caveat_type(c)
            if caveat_type:
                by_type.setdefault(caveat_type, []).append(c)

        # Build deduplicated caveats with merged sources
        caveats = []
        for caveat_type, items in by_type.items():
            # Build source links - use markdown link format [title](url)
            # Frontend renders markdown, so this will be clickable
            source_links = []
            for item in items:
                if item.source_url and item.source_title:
                    # Use short title (first 40 chars) to keep it readable
                    short_title = item.source_title[:40] + "..." if len(item.source_title) > 40 else item.source_title
                    source_links.append(f"[{short_title}]({item.source_url})")
                elif item.source_url:
                    source_links.append(f"[🔗]({item.source_url})")

            # Join sources with comma for readability
            sources_str = ", ".join(source_links) if source_links else ""

            # Get caveat text using first item's topic for context
            caveat_text = self._get_caveat_text(caveat_type, items[0].topic)

            # Combine caveat text with sources
            if sources_str:
                caveats.append(f"📌 {caveat_text} Fonti: {sources_str}")
            else:
                caveats.append(f"📌 {caveat_text}")

        return caveats

    def _generate_caveat(self, contradiction: ContradictionInfo) -> str | None:
        """Generate a caveat message for a contradiction (legacy method).

        Note: This method is kept for backwards compatibility.
        New code should use _deduplicate_and_format_caveats() instead.

        Args:
            contradiction: ContradictionInfo to generate caveat for

        Returns:
            Caveat string or None if confidence too low
        """
        caveat_type = self._get_caveat_type(contradiction)
        if not caveat_type:
            return None

        caveat_text = self._get_caveat_text(caveat_type, contradiction.topic)

        # Add source link
        if contradiction.source_url:
            return f"📌 {caveat_text} [🔗]({contradiction.source_url})"
        else:
            return f"📌 {caveat_text} [Fonte: {contradiction.source_title}]"

    async def synthesize_with_snippets(
        self,
        kb_answer: str,
        web_results: list[dict],
        user_query: str,
    ) -> str | None:
        """Use LLM to merge KB answer with web snippets (fallback when Brave AI unavailable).

        Creates a comprehensive response that combines:
        - KB answer accuracy and structure
        - Web snippets for additional context
        - Important conditions and warnings from web sources

        Args:
            kb_answer: Original answer from knowledge base
            web_results: List of web search results with snippets
            user_query: User's original question

        Returns:
            Synthesized response or None on error
        """
        try:
            from app.core.llm.factory import get_llm_factory
            from app.schemas.chat import Message

            # Build web context from snippets
            web_context_parts = []
            for i, result in enumerate(web_results[:5], 1):  # Limit to top 5 results
                title = result.get("title", "Fonte sconosciuta")
                snippet = result.get("snippet", "")
                if snippet:
                    web_context_parts.append(f"{i}. {title}:\n   {snippet}")

            if not web_context_parts:
                logger.debug("BRAVE_synthesis_snippets_no_context")
                return None

            web_context = "\n\n".join(web_context_parts)

            # DEV-245 Phase 5.14: Check if web has genuine exclusions
            # Only use ✅/❌ format when web results ACTUALLY contain exclusion keywords
            has_exclusions, matched_keywords = _web_has_genuine_exclusions(web_results)

            logger.info(
                "DEV245_synthesis_exclusion_check",
                has_exclusions=has_exclusions,
                matched_keywords=matched_keywords[:3] if matched_keywords else [],
                will_use_inclusion_exclusion_format=has_exclusions,
            )

            logger.info(
                "BRAVE_synthesis_snippets_starting",
                kb_answer_length=len(kb_answer),
                web_snippets_count=len(web_context_parts),
                web_context_length=len(web_context),
            )

            # DEV-245 Phase 5.14: Build conditional instruction based on exclusion presence
            if has_exclusions:
                exclusion_instruction = f"""4. **ESCLUSIONI TROVATE**: I risultati web contengono esclusioni ({', '.join(matched_keywords[:3])}).
   Evidenziale chiaramente usando questo formato:
   - ✅ Incluso: [caso ammissibile con riferimento normativo se presente]
   - ❌ Escluso: [caso NON ammissibile]
   Esempio: se IRAP da dichiarazione è inclusa ma IRAP da accertamento è esclusa, dì ENTRAMBE le cose!"""
            else:
                exclusion_instruction = """4. **FORMATO**: Usa un formato narrativo chiaro.
   NON usare ✅/❌ perché i risultati web non indicano esclusioni specifiche."""

            synthesis_prompt = f"""Arricchisci la risposta KB con informazioni rilevanti dai risultati web.

DOMANDA UTENTE: {user_query}

RISPOSTA KB (base affidabile):
{kb_answer}

RISULTATI WEB (da integrare se aggiungono valore):
{web_context}

ISTRUZIONI:
1. Mantieni la risposta KB come base principale - non modificare le informazioni corrette
2. Integra SOLO informazioni aggiuntive e pertinenti dai risultati web
3. Se i risultati web indicano condizioni, limitazioni o requisiti, aggiungili
{exclusion_instruction}
5. Se il web indica condizioni specifiche (articoli di legge, requisiti), includile esplicitamente
6. Mantieni un tono professionale in italiano
7. IMPORTANTE: NON aggiungere frasi generiche come "Se hai domande..." alla fine
8. Se i risultati web non aggiungono nulla di utile, restituisci solo la risposta KB migliorata

RISPOSTA ARRICCHITA:"""

            factory = get_llm_factory()
            from app.core.config import settings

            provider = factory.create_provider(
                provider_type="openai",
                model=settings.LLM_MODEL or "gpt-4o-mini",
            )

            messages = [
                Message(
                    role="system",
                    content="Sei un esperto di normativa fiscale italiana. Arricchisci risposte esistenti con informazioni web pertinenti. NON aggiungere mai frasi di chiusura generiche.",
                ),
                Message(role="user", content=synthesis_prompt),
            ]

            response = await provider.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
            )

            synthesized = response.content.strip() if response.content else None

            if synthesized:
                # DEV-245 Phase 2: Don't append inline "📚 Fonti web:" citations
                # Web sources are now in kb_sources_metadata and appear in the unified
                # Fonti section alongside KB sources (with "web" label).
                # Removing inline citations to avoid duplicate display.
                logger.info(
                    "BRAVE_synthesis_snippets_complete",
                    synthesized_length=len(synthesized),
                    original_kb_length=len(kb_answer),
                )

            return synthesized

        except Exception as e:
            logger.error(
                "BRAVE_synthesis_snippets_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    async def synthesize_with_brave(
        self,
        kb_answer: str,
        brave_summary: str,
        user_query: str,
    ) -> str | None:
        """Use LLM to merge KB answer with Brave AI insights.

        Creates a comprehensive response that combines:
        - KB answer accuracy and structure
        - Brave AI additional context and nuances
        - Important conditions and warnings

        Args:
            kb_answer: Original answer from knowledge base
            brave_summary: AI summary from Brave Search
            user_query: User's original question

        Returns:
            Synthesized response or None on error
        """
        try:
            from app.core.llm.factory import get_llm_factory
            from app.schemas.chat import Message

            # DEV-245 Phase 5.14: Check if Brave summary has genuine exclusions
            # Wrap brave_summary in a list structure for _web_has_genuine_exclusions
            has_exclusions, matched_keywords = _web_has_genuine_exclusions([{"snippet": brave_summary}])

            logger.info(
                "DEV245_synthesis_brave_exclusion_check",
                has_exclusions=has_exclusions,
                matched_keywords=matched_keywords[:3] if matched_keywords else [],
                will_use_inclusion_exclusion_format=has_exclusions,
            )

            logger.info(
                "BRAVE_synthesis_starting",
                kb_answer_length=len(kb_answer),
                brave_summary_length=len(brave_summary),
                user_query_length=len(user_query),
            )

            # DEV-245 Phase 5.14: Build conditional instruction based on exclusion presence
            if has_exclusions:
                exclusion_instruction = f"""4. **ESCLUSIONI TROVATE**: Brave indica esclusioni ({', '.join(matched_keywords[:3])}).
   Evidenziale chiaramente usando questo formato:
   - ✅ Incluso: [caso ammissibile con riferimento normativo se presente]
   - ❌ Escluso: [caso NON ammissibile]
   Esempio: se IRAP da dichiarazione è inclusa ma IRAP da accertamento è esclusa, dì ENTRAMBE le cose!"""
            else:
                exclusion_instruction = """4. **FORMATO**: Usa un formato narrativo chiaro.
   NON usare ✅/❌ perché Brave non indica esclusioni specifiche."""

            # Build synthesis prompt
            synthesis_prompt = f"""Combina queste due risposte in una risposta completa e coerente.

DOMANDA UTENTE: {user_query}

RISPOSTA KB (base affidabile, da mantenere come struttura principale):
{kb_answer}

APPROFONDIMENTO WEB (Brave AI - da integrare se aggiunge valore):
{brave_summary}

ISTRUZIONI:
1. Mantieni la risposta KB come base principale
2. Integra le informazioni aggiuntive da Brave SOLO se pertinenti e utili
3. Aggiungi condizioni, requisiti o avvertenze importanti dal web
{exclusion_instruction}
5. Se il web indica condizioni specifiche (articoli di legge, requisiti), includile esplicitamente
6. Mantieni un tono professionale in italiano
7. IMPORTANTE: NON aggiungere frasi generiche come "Se hai domande..." o "Non esitare a chiedere" alla fine
8. Termina con informazioni concrete, non con chiusure generiche

RISPOSTA COMBINATA:"""

            factory = get_llm_factory()
            # Use the default/basic provider for synthesis
            from app.core.config import settings

            provider = factory.create_provider(
                provider_type="openai",
                model=settings.LLM_MODEL or "gpt-4o-mini",
            )

            messages = [
                Message(
                    role="system",
                    content="Sei un esperto di normativa fiscale italiana. Il tuo compito è combinare informazioni da fonti diverse in risposte chiare e complete. NON aggiungere mai frasi di chiusura generiche.",
                ),
                Message(role="user", content=synthesis_prompt),
            ]

            response = await provider.chat_completion(
                messages=messages,
                temperature=0.3,  # Low temperature for consistency
                max_tokens=1000,
            )

            synthesized = response.content.strip() if response.content else None

            if synthesized:
                logger.info(
                    "BRAVE_synthesis_complete",
                    synthesized_length=len(synthesized),
                    original_kb_length=len(kb_answer),
                )

            return synthesized

        except Exception as e:
            logger.error(
                "BRAVE_synthesis_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None


# Singleton instance for convenience
web_verification_service = WebVerificationService()
