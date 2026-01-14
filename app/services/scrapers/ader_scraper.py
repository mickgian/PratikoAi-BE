"""AdER (Agenzia Entrate-Riscossione) Scraper.

This module provides web scraping functionality for the Italian Tax Collection Agency
(Agenzia delle Entrate-Riscossione) with comprehensive error handling and integration
with PratikoAI's knowledge base.

Target content:
- Rottamazione rules and deadlines
- Payment plans and schedules
- Official communications
- Regulatory updates

Schedule: Daily (every 24 hours)

DEV-242 Phase 38: Recurring ingestion for AdER to capture critical content like
5-day grace period rules and interest rates.
"""

import asyncio
import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, Tag
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.services.knowledge_integrator import KnowledgeIntegrator


@dataclass
class AdERDocument:
    """Represents a document from AdER (Agenzia Entrate-Riscossione)."""

    title: str
    url: str
    document_type: str  # news, comunicazione, regole
    published_date: date | None = None
    summary: str | None = None
    full_text: str | None = None
    authority: str = "Agenzia delle Entrate-Riscossione"
    topics: list[str] = field(default_factory=list)
    content_hash: str | None = None

    def generate_content_hash(self) -> str:
        """Generate SHA256 hash of document content."""
        content = f"{self.title}{self.full_text or ''}{self.published_date}"
        self.content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return self.content_hash

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for knowledge base integration."""
        return {
            "title": self.title,
            "url": self.url,
            "content": self.full_text or self.summary or "",
            "source": "agenzia_entrate_riscossione",
            "source_type": self.document_type,
            "published_date": self.published_date,
            "authority": self.authority,
            "metadata": {
                "topics": self.topics,
            },
        }


@dataclass
class ScrapingResult:
    """Result of a scraping operation."""

    documents_found: int = 0
    documents_processed: int = 0
    documents_saved: int = 0
    errors: int = 0
    duration_seconds: int = 0
    start_date: date | None = None
    end_date: date | None = None

    @property
    def duration_minutes(self) -> float:
        """Duration in minutes."""
        return self.duration_seconds / 60


class AdERScraper:
    """Web scraper for AdER (Agenzia Entrate-Riscossione).

    Respects robots.txt and implements rate limiting for polite scraping.
    """

    BASE_URL = "https://www.agenziaentrateriscossione.gov.it"
    NEWS_URL = f"{BASE_URL}/it/il-gruppo/lagenzia-comunica/novita/"
    ROBOTS_TXT_URL = f"{BASE_URL}/robots.txt"

    # Topic keywords for filtering relevant content
    RELEVANT_KEYWORDS = [
        "rottamazione",
        "definizione agevolata",
        "pace fiscale",
        "rateizzazione",
        "sospensione",
        "pagamento",
        "scadenza",
        "contribuente",
        "cartella",
        "intimazione",
        "dilazione",
        "rata",
        "decadenza",
        "tolleranza",
        "bilancio",
    ]

    def __init__(
        self,
        db_session: AsyncSession | None = None,
        rate_limit_delay: float = 2.0,
        max_retries: int = 3,
        timeout_seconds: int = 30,
        max_concurrent_requests: int = 3,
        respect_robots_txt: bool = True,
    ):
        """Initialize the scraper with configuration.

        Args:
            db_session: Database session for persistence (optional)
            rate_limit_delay: Delay between requests in seconds
            max_retries: Maximum number of retries for failed requests
            timeout_seconds: Request timeout
            max_concurrent_requests: Maximum concurrent requests
            respect_robots_txt: Whether to respect robots.txt
        """
        self.db_session = db_session
        self.knowledge_integrator = KnowledgeIntegrator(db_session) if db_session else None
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.max_concurrent_requests = max_concurrent_requests
        self.respect_robots_txt = respect_robots_txt

        self.last_request_time = 0.0
        self._session: aiohttp.ClientSession | None = None
        self._robots_rules: dict[str, bool] = {}
        self._robots_checked = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        if self.respect_robots_txt:
            await self._check_robots_txt()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if not self._session:
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent_requests, limit_per_host=self.max_concurrent_requests
            )
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "User-Agent": "PratikoAI Legal Research Bot/1.0 (+https://pratiko.ai)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
                    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                },
            )

    async def _check_robots_txt(self):
        """Check and parse robots.txt for scraping rules."""
        if self._robots_checked:
            return

        try:
            await self._ensure_session()
            assert self._session is not None
            async with self._session.get(self.ROBOTS_TXT_URL) as response:
                if response.status == 200:
                    content = await response.text()
                    self._parse_robots_txt(content)
                    logger.info("ader_robots_txt_parsed", rules_count=len(self._robots_rules))
                else:
                    logger.warning("ader_robots_txt_not_found", status=response.status)
        except Exception as e:
            logger.warning("ader_robots_txt_error", error=str(e))

        self._robots_checked = True

    def _parse_robots_txt(self, content: str):
        """Parse robots.txt content."""
        current_user_agent = None

        for line in content.split("\n"):
            line = line.strip().lower()

            if line.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                current_user_agent = agent

            elif line.startswith("disallow:") and current_user_agent in ["*", "pratikoai"]:
                path = line.split(":", 1)[1].strip()
                if path:
                    self._robots_rules[path] = False

            elif line.startswith("allow:") and current_user_agent in ["*", "pratikoai"]:
                path = line.split(":", 1)[1].strip()
                if path:
                    self._robots_rules[path] = True

    def _is_path_allowed(self, url: str) -> bool:
        """Check if URL path is allowed by robots.txt."""
        if not self.respect_robots_txt or not self._robots_rules:
            return True

        parsed = urlparse(url)
        path = parsed.path

        for rule_path, allowed in sorted(self._robots_rules.items(), key=lambda x: -len(x[0])):
            if path.startswith(rule_path):
                return allowed

        return True

    async def _fetch_page_with_retry(self, url: str) -> str | None:
        """Fetch a page with retry logic and rate limiting.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string or None on error
        """
        if not self._is_path_allowed(url):
            logger.warning("ader_path_disallowed_by_robots", url=url)
            return None

        await self._ensure_session()
        assert self._session is not None

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)

        self.last_request_time = time.time()

        for attempt in range(self.max_retries + 1):
            try:
                async with self._session.get(url) as response:
                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning("ader_rate_limited", retry_after=retry_after)
                        await asyncio.sleep(retry_after)
                        continue

                    if response.status == 200:
                        content = cast(str, await response.text())
                        logger.debug("ader_page_fetched", url=url)
                        return content
                    else:
                        logger.warning("ader_http_error", url=url, status=response.status)

            except TimeoutError:
                logger.warning("ader_timeout", url=url, attempt=attempt)

            except Exception as e:
                logger.warning("ader_fetch_error", url=url, error=str(e), attempt=attempt)

            if attempt < self.max_retries:
                delay = 2**attempt * self.rate_limit_delay
                await asyncio.sleep(delay)

        logger.error("ader_max_retries_exceeded", url=url)
        return None

    async def scrape_recent_documents(
        self,
        days_back: int = 7,
        limit: int | None = None,
    ) -> ScrapingResult:
        """Scrape recent documents from AdER news section.

        Args:
            days_back: Number of days to look back
            limit: Maximum documents to scrape

        Returns:
            ScrapingResult with statistics
        """
        start_time = time.time()
        start_date = date.today() - timedelta(days=days_back)
        end_date = date.today()

        result = ScrapingResult(start_date=start_date, end_date=end_date)

        try:
            # Scrape the news listing page
            documents = await self._scrape_news_list(start_date, end_date)
            result.documents_found = len(documents)

            # Filter by relevant keywords
            documents = self._filter_documents_by_topics(documents)

            # Apply limit
            if limit:
                documents = documents[:limit]

            # Process each document
            for doc in documents:
                try:
                    # Fetch full document content
                    full_doc = await self._fetch_document_content(doc)
                    if full_doc:
                        result.documents_processed += 1

                        # Save to knowledge base via KnowledgeIntegrator
                        if self.knowledge_integrator:
                            doc_data = full_doc.to_dict()
                            integration_result = await self.knowledge_integrator.update_knowledge_base(doc_data)
                            if integration_result.get("success"):
                                result.documents_saved += 1
                                logger.info(
                                    "ader_document_saved",
                                    url=doc.url,
                                    action=integration_result.get("action"),
                                    document_id=integration_result.get("document_id"),
                                )
                            else:
                                logger.warning(
                                    "ader_document_save_failed",
                                    url=doc.url,
                                    error=integration_result.get("error"),
                                )
                                result.errors += 1
                        else:
                            logger.debug("ader_no_db_session_skipping_save", url=doc.url)
                except Exception as e:
                    logger.error("ader_document_processing_error", url=doc.url, error=str(e))
                    result.errors += 1

        except Exception as e:
            logger.error("ader_scraping_failed", error=str(e))
            result.errors += 1

        result.duration_seconds = int(time.time() - start_time)

        logger.info(
            "ader_scraping_completed",
            documents_found=result.documents_found,
            documents_saved=result.documents_saved,
            errors=result.errors,
            duration_seconds=result.duration_seconds,
        )

        return result

    async def _scrape_news_list(
        self,
        start_date: date,
        end_date: date,
    ) -> list[AdERDocument]:
        """Scrape document listings from AdER news section.

        Args:
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of AdERDocument objects (without full text)
        """
        documents: list[AdERDocument] = []

        logger.info("ader_fetching_news_list", url=self.NEWS_URL)

        html_content = await self._fetch_page_with_retry(self.NEWS_URL)
        if not html_content:
            logger.warning("ader_news_list_fetch_failed")
            return documents

        soup = BeautifulSoup(html_content, "html.parser")

        # AdER news items are typically in article or card elements
        # Look for common patterns in AdER site structure
        news_items = soup.find_all("article") or soup.find_all("div", class_=re.compile(r"news|card|item"))

        # Also look for links in the news section
        news_links = soup.find_all("a", href=re.compile(r"/novita/|/comunicati/|/news/"))

        for link in news_links:
            try:
                href = link.get("href", "")
                title = link.get_text(strip=True)

                if not href or not title:
                    continue

                # Skip navigation and utility links
                if len(title) < 15:
                    continue

                # Make URL absolute
                url = urljoin(self.BASE_URL, href)

                # Skip non-content URLs
                if any(skip in url.lower() for skip in ["#", "javascript:", "mailto:", ".pdf", ".zip"]):
                    continue

                # Try to extract date from URL or surrounding text
                published_date = self._extract_date_from_url(href) or self._extract_date_from_context(link)

                # Filter by date range if we have a date
                if published_date:
                    if published_date < start_date or published_date > end_date:
                        continue

                doc = AdERDocument(
                    title=title,
                    url=url,
                    document_type=self._determine_document_type(title, url),
                    published_date=published_date,
                )

                # Avoid duplicates
                if not any(d.url == doc.url for d in documents):
                    documents.append(doc)

            except Exception as e:
                logger.debug("ader_parse_link_error", error=str(e))

        logger.info("ader_news_list_scraped", documents_count=len(documents))
        return documents

    def _extract_date_from_url(self, url: str) -> date | None:
        """Extract date from URL pattern."""
        patterns = [
            r"/(\d{4})/(\d{2})/(\d{2})/",  # /2026/01/12/
            r"/(\d{4})(\d{2})(\d{2})/",  # /20260112/
            r"-(\d{4})(\d{2})(\d{2})",  # -20260112
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    return date(year, month, day)
                except ValueError:
                    pass

        return None

    def _extract_date_from_context(self, element: Tag) -> date | None:
        """Extract date from surrounding HTML context."""
        # Look for date in parent elements or siblings
        for parent in element.parents:
            if parent.name in ["article", "div", "li"]:
                text = parent.get_text()
                extracted = self._extract_date_from_text(text)
                if extracted:
                    return extracted
            if parent.name == "body":
                break
        return None

    def _extract_date_from_text(self, text: str) -> date | None:
        """Extract date from Italian text."""
        italian_months = {
            "gennaio": 1,
            "febbraio": 2,
            "marzo": 3,
            "aprile": 4,
            "maggio": 5,
            "giugno": 6,
            "luglio": 7,
            "agosto": 8,
            "settembre": 9,
            "ottobre": 10,
            "novembre": 11,
            "dicembre": 12,
        }

        # Pattern: "15 marzo 2024" or "15 Marzo 2024"
        pattern = r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})"
        match = re.search(pattern, text.lower())

        if match:
            try:
                day = int(match.group(1))
                month = italian_months[match.group(2)]
                year = int(match.group(3))
                return date(year, month, day)
            except (ValueError, KeyError):
                pass

        # Pattern: "15/03/2024" or "15-03-2024"
        pattern = r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})"
        match = re.search(pattern, text)

        if match:
            try:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                return date(year, month, day)
            except ValueError:
                pass

        return None

    def _determine_document_type(self, title: str, url: str) -> str:
        """Determine document type from title and URL."""
        combined = f"{title} {url}".lower()

        if "rottamazione" in combined or "definizione agevolata" in combined:
            return "regole_rottamazione"
        elif "comunicat" in combined:
            return "comunicazione"
        elif "scaden" in combined or "calendar" in combined:
            return "scadenza"
        elif "novit" in combined or "news" in combined:
            return "news"
        else:
            return "comunicazione"

    def _filter_documents_by_topics(
        self,
        documents: list[AdERDocument],
    ) -> list[AdERDocument]:
        """Filter documents by relevant topic keywords.

        Args:
            documents: List of documents to filter

        Returns:
            Filtered list of documents
        """
        filtered = []

        for doc in documents:
            title_lower = doc.title.lower()
            summary_lower = (doc.summary or "").lower()
            combined_text = f"{title_lower} {summary_lower}"

            # Check if any keyword matches
            if any(kw.lower() in combined_text for kw in self.RELEVANT_KEYWORDS):
                doc.topics = [kw for kw in self.RELEVANT_KEYWORDS if kw.lower() in combined_text]
                filtered.append(doc)

        logger.info(
            "ader_documents_filtered",
            original_count=len(documents),
            filtered_count=len(filtered),
        )

        return filtered

    async def _fetch_document_content(self, doc: AdERDocument) -> AdERDocument | None:
        """Fetch full document content.

        Args:
            doc: AdERDocument with URL

        Returns:
            AdERDocument with full text or None
        """
        html_content = await self._fetch_page_with_retry(doc.url)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Look for main content area - AdER-specific selectors
        content_selectors = [
            ".contenuto-principale",
            ".content-main",
            ".article-content",
            ".news-content",
            ".page-content",
            "article",
            "main",
            "#content",
        ]

        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break

        if content_element:
            doc.full_text = content_element.get_text(separator="\n", strip=True)
        else:
            # Fallback to body
            body = soup.find("body")
            if body:
                doc.full_text = body.get_text(separator="\n", strip=True)

        # Clean up text
        if doc.full_text:
            # Remove excessive whitespace
            doc.full_text = re.sub(r"\n{3,}", "\n\n", doc.full_text)
            doc.full_text = re.sub(r" {2,}", " ", doc.full_text)

            # Minimum content length check
            if len(doc.full_text.strip()) < 200:
                logger.warning("ader_content_too_short", url=doc.url, length=len(doc.full_text))
                return None

        # Generate content hash
        doc.generate_content_hash()

        return doc


# Convenience function for scheduled task integration
async def scrape_ader_daily_task(db_session: AsyncSession | None = None) -> ScrapingResult:
    """Scheduled task function for daily AdER scraping.

    This function is called by the scheduler service daily.

    Args:
        db_session: Database session for persistence. If not provided,
                    documents will be scraped but not saved to DB.
    """
    try:
        async with AdERScraper(db_session=db_session) as scraper:
            result = await scraper.scrape_recent_documents(
                days_back=7,  # Look back 7 days to catch any missed items
            )

            logger.info(
                "scheduled_ader_scraping_completed",
                documents_found=result.documents_found,
                documents_saved=result.documents_saved,
                errors=result.errors,
                persistence_enabled=db_session is not None,
            )

            return cast(ScrapingResult, result)

    except Exception as e:
        logger.error("scheduled_ader_scraping_failed", error=str(e))
        return ScrapingResult(errors=1)
