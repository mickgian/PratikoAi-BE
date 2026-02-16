"""Brave Search API client for web verification.

Handles web search using Brave Search API with AI summarization,
falling back to DuckDuckGo when Brave is unavailable.
"""

import asyncio
import re
import time
from typing import TYPE_CHECKING

from app.core.logging import logger

if TYPE_CHECKING:
    import httpx


class BraveSearchClient:
    """Client for Brave Search API with DuckDuckGo fallback."""

    # DEV-246: Brave Search API cost estimation
    # Free tier: 2,000 queries/month, then $3/1000 queries
    BRAVE_COST_PER_QUERY_EUR = 0.003  # ~0.003 per query (~$3/1000)

    def __init__(self, timeout_seconds: float = 15.0, max_results: int = 5):
        """Initialize the Brave search client.

        Args:
            timeout_seconds: Timeout for search operations
            max_results: Maximum number of results to return
        """
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results

    async def search(
        self,
        query: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict]:
        """Search the web using Brave Search API with AI summarization.

        Falls back to DuckDuckGo if Brave API key is not configured.

        DEV-246: Tracks Brave API costs for daily cost reporting.

        Args:
            query: Search query
            user_id: DEV-246: User ID for cost tracking
            session_id: DEV-246: Session ID for cost tracking

        Returns:
            List of search result dicts with title, snippet, link, is_ai_synthesis
        """
        try:
            from app.core.config import settings

            if not settings.BRAVE_SEARCH_API_KEY:
                logger.info("BRAVE_not_configured", fallback="duckduckgo")
                return await self._search_duckduckgo(query)

            logger.info("BRAVE_search_starting", query=query[:80])

            import httpx

            headers = {
                "X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY,
                "Accept": "application/json",
            }

            start_time = time.time()
            api_calls = 0

            async with httpx.AsyncClient() as client:
                search_data = await self._call_brave_search(client, query, headers)
                api_calls += 1
                ai_summary = await self._get_brave_summary(client, search_data, headers)
                if ai_summary:
                    api_calls += 1  # Summarizer is a separate API call

            response_time_ms = int((time.time() - start_time) * 1000)

            # DEV-246: Track Brave API cost
            await self._track_brave_api_usage(
                user_id=user_id,
                session_id=session_id,
                api_calls=api_calls,
                response_time_ms=response_time_ms,
            )

            results = self._parse_brave_results(search_data, ai_summary)

            logger.info(
                "BRAVE_search_complete",
                query=query[:50],
                results_count=len(results),
                has_ai_summary=bool(ai_summary),
                ai_summary_preview=ai_summary[:100] if ai_summary else None,
            )

            return results[: self._max_results]

        except Exception as e:
            logger.warning(
                "BRAVE_search_failed",
                query=query[:100],
                error=str(e),
                error_type=type(e).__name__,
                fallback="duckduckgo",
            )
            return await self._search_duckduckgo(query)

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
                "count": self._max_results,
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

    async def _search_duckduckgo(self, query: str) -> list[dict]:
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

            return results[: self._max_results]

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

    async def _track_brave_api_usage(
        self,
        user_id: str | None,
        session_id: str | None,
        api_calls: int,
        response_time_ms: int,
        error_occurred: bool = False,
    ) -> None:
        """Track Brave Search API usage for cost reporting.

        DEV-246: Tracks API calls to usage_events table for daily cost reporting.

        Args:
            user_id: User ID (uses "system" if None)
            session_id: Session ID (uses "web_verification" if None)
            api_calls: Number of API calls made
            response_time_ms: Total response time in milliseconds
            error_occurred: Whether an error occurred
        """
        try:
            from app.services.usage_tracker import usage_tracker

            # DEV-257: Skip tracking if no valid user_id (UsageEvent.user_id is FK to user.id)
            if not user_id:
                logger.debug(
                    "BRAVE_usage_tracking_skipped",
                    reason="no_user_id",
                    api_calls=api_calls,
                )
                return

            effective_session_id = session_id or "web_verification"

            # Calculate cost (Brave free tier is 2000/month, then $3/1000)
            cost_eur = api_calls * self.BRAVE_COST_PER_QUERY_EUR

            await usage_tracker.track_third_party_api(
                user_id=user_id,
                session_id=effective_session_id,
                api_type="brave_search",
                cost_eur=cost_eur,
                response_time_ms=response_time_ms,
                request_count=api_calls,
                error_occurred=error_occurred,
            )

            logger.debug(
                "BRAVE_usage_tracked",
                user_id=user_id,
                api_calls=api_calls,
                cost_eur=cost_eur,
            )

        except Exception as e:
            # Don't fail the main flow if tracking fails
            logger.warning(
                "BRAVE_usage_tracking_failed",
                error=str(e),
                user_id=user_id,
            )


# Singleton instance
brave_search_client = BraveSearchClient()
