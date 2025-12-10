"""Gazzetta Ufficiale Scraper for Italian Official Gazette.

This module provides web scraping functionality for the Italian Official Gazette
(Gazzetta Ufficiale) with comprehensive error handling and integration with
PratikoAI's knowledge base.

Target content:
- Tax/finance laws (leggi tributarie)
- Labor/employment laws (leggi sul lavoro)
- All official acts (atti ufficiali)

Schedule: Daily (every 24 hours)
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
class GazzettaDocument:
    """Represents a document from Gazzetta Ufficiale."""

    title: str
    url: str
    document_type: str  # legge, decreto, dpcm, circolare, etc.
    document_number: str | None = None
    published_date: date | None = None
    summary: str | None = None
    full_text: str | None = None
    series: str = "serie_generale"  # serie_generale, serie_speciale, etc.
    authority: str = "Gazzetta Ufficiale"
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
            "source": "gazzetta_ufficiale",
            "source_type": self.document_type,
            "document_number": self.document_number,
            "published_date": self.published_date,
            "authority": self.authority,
            "metadata": {
                "series": self.series,
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


class GazzettaScraper:
    """Web scraper for Italian Official Gazette (Gazzetta Ufficiale).

    Respects robots.txt and implements rate limiting for polite scraping.
    """

    BASE_URL = "https://www.gazzettaufficiale.it"
    SEARCH_URL = f"{BASE_URL}/ricerca"
    ROBOTS_TXT_URL = f"{BASE_URL}/robots.txt"

    # Document type keywords for filtering
    TAX_KEYWORDS = [
        "tribut",
        "fiscal",
        "imposta",
        "iva",
        "irpef",
        "ires",
        "tasse",
        "contribut",
        "agevolazion",
        "detrazion",
        "deduzion",
    ]

    LABOR_KEYWORDS = [
        "lavoro",
        "occupazion",
        "licenziament",
        "assunzion",
        "contratt",
        "retribuzion",
        "pensione",
        "previdenza",
        "inps",
        "inail",
        "tfr",
        "ccnl",
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
            db_session: Database session for persistence (optional for backwards compatibility)
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
            assert self._session is not None  # guaranteed by _ensure_session
            async with self._session.get(self.ROBOTS_TXT_URL) as response:
                if response.status == 200:
                    content = await response.text()
                    self._parse_robots_txt(content)
                    logger.info("gazzetta_robots_txt_parsed", rules_count=len(self._robots_rules))
                else:
                    logger.warning("gazzetta_robots_txt_not_found", status=response.status)
        except Exception as e:
            logger.warning("gazzetta_robots_txt_error", error=str(e))

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

        # Check most specific rules first
        for rule_path, allowed in sorted(self._robots_rules.items(), key=lambda x: -len(x[0])):
            if path.startswith(rule_path):
                return allowed

        return True  # Default allow

    async def _fetch_page_with_retry(self, url: str) -> str | None:
        """Fetch a page with retry logic and rate limiting.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string or None on error
        """
        if not self._is_path_allowed(url):
            logger.warning("gazzetta_path_disallowed_by_robots", url=url)
            return None

        await self._ensure_session()
        assert self._session is not None  # guaranteed by _ensure_session

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
                        logger.warning("gazzetta_rate_limited", retry_after=retry_after)
                        await asyncio.sleep(retry_after)
                        continue

                    if response.status == 200:
                        content = cast(str, await response.text())
                        logger.debug("gazzetta_page_fetched", url=url)
                        return content
                    else:
                        logger.warning("gazzetta_http_error", url=url, status=response.status)

            except TimeoutError:
                logger.warning("gazzetta_timeout", url=url, attempt=attempt)

            except Exception as e:
                logger.warning("gazzetta_fetch_error", url=url, error=str(e), attempt=attempt)

            if attempt < self.max_retries:
                # Exponential backoff
                delay = 2**attempt * self.rate_limit_delay
                await asyncio.sleep(delay)

        logger.error("gazzetta_max_retries_exceeded", url=url)
        return None

    async def scrape_recent_documents(
        self,
        days_back: int = 1,
        document_types: list[str] | None = None,
        filter_tax: bool = True,
        filter_labor: bool = True,
        limit: int | None = None,
    ) -> ScrapingResult:
        """Scrape recent documents from Gazzetta Ufficiale.

        Args:
            days_back: Number of days to look back
            document_types: Specific document types to scrape
            filter_tax: Include tax-related documents
            filter_labor: Include labor-related documents
            limit: Maximum documents to scrape

        Returns:
            ScrapingResult with statistics
        """
        start_time = time.time()
        start_date = date.today() - timedelta(days=days_back)
        end_date = date.today()

        result = ScrapingResult(start_date=start_date, end_date=end_date)

        try:
            # Scrape the main listing page
            documents = await self._scrape_document_list(start_date, end_date, document_types)
            result.documents_found = len(documents)

            # Filter documents based on topics
            if filter_tax or filter_labor:
                documents = self._filter_documents_by_topics(documents, filter_tax, filter_labor)

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
                                    "gazzetta_document_saved",
                                    url=doc.url,
                                    action=integration_result.get("action"),
                                    document_id=integration_result.get("document_id"),
                                )
                            else:
                                logger.warning(
                                    "gazzetta_document_save_failed",
                                    url=doc.url,
                                    error=integration_result.get("error"),
                                )
                                result.errors += 1
                        else:
                            # No db_session provided - backwards compatible mode
                            logger.debug("gazzetta_no_db_session_skipping_save", url=doc.url)
                except Exception as e:
                    logger.error("gazzetta_document_processing_error", url=doc.url, error=str(e))
                    result.errors += 1

        except Exception as e:
            logger.error("gazzetta_scraping_failed", error=str(e))
            result.errors += 1

        result.duration_seconds = int(time.time() - start_time)

        logger.info(
            "gazzetta_scraping_completed",
            documents_found=result.documents_found,
            documents_saved=result.documents_saved,
            errors=result.errors,
            duration_seconds=result.duration_seconds,
        )

        return result

    async def _scrape_document_list(
        self,
        start_date: date,
        end_date: date,
        document_types: list[str] | None = None,
    ) -> list[GazzettaDocument]:
        """Scrape document listings from Gazzetta Ufficiale archive.

        Uses the new URL structure (as of 2025):
        1. Archive listing: /ricercaArchivioCompleto/serie_generale/{year}
        2. Issue detail: /gazzetta/serie_generale/caricaDettaglio?dataPubblicazioneGazzetta=YYYY-MM-DD&numeroGazzetta=N
        3. Document detail: /atto/serie_generale/caricaDettaglioAtto/originario?...

        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            document_types: Specific document types

        Returns:
            List of GazzettaDocument objects (without full text)
        """
        documents = []

        # Get unique years to scrape
        years = set()
        current = start_date
        while current <= end_date:
            years.add(current.year)
            current = date(current.year + 1, 1, 1) if current.month == 12 else current.replace(month=current.month + 1)
        years.add(end_date.year)

        # For each year, get the archive listing to find gazette issues
        for year in sorted(years):
            archive_url = f"{self.BASE_URL}/ricercaArchivioCompleto/serie_generale/{year}"
            logger.info("gazzetta_fetching_archive", url=archive_url, year=year)

            html_content = await self._fetch_page_with_retry(archive_url)
            if not html_content:
                logger.warning("gazzetta_archive_fetch_failed", year=year)
                continue

            # Parse gazette issue links from archive
            gazette_issues = self._parse_archive_page(html_content, start_date, end_date)
            logger.info("gazzetta_issues_found", year=year, count=len(gazette_issues))

            # For each gazette issue, fetch the document list
            for issue_date, issue_number in gazette_issues:
                issue_docs = await self._scrape_gazette_issue(issue_date, issue_number, document_types)
                documents.extend(issue_docs)

        logger.info("gazzetta_document_list_scraped", documents_count=len(documents))
        return documents

    def _parse_archive_page(
        self,
        html_content: str,
        start_date: date,
        end_date: date,
    ) -> list[tuple[date, int]]:
        """Parse archive page to extract gazette issue dates and numbers.

        Args:
            html_content: HTML content of archive page
            start_date: Minimum date filter
            end_date: Maximum date filter

        Returns:
            List of (publication_date, issue_number) tuples
        """
        issues = []
        soup = BeautifulSoup(html_content, "html.parser")

        # Look for links to gazette issues
        # Pattern: /gazzetta/serie_generale/caricaDettaglio?dataPubblicazioneGazzetta=2025-12-04&numeroGazzetta=282
        issue_links = soup.find_all("a", href=re.compile(r"caricaDettaglio.*dataPubblicazioneGazzetta"))

        for link in issue_links:
            href = link.get("href", "")
            try:
                # Extract date from URL parameter
                date_match = re.search(r"dataPubblicazioneGazzetta=(\d{4}-\d{2}-\d{2})", href)
                num_match = re.search(r"numeroGazzetta=(\d+)", href)

                if date_match and num_match:
                    pub_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
                    issue_num = int(num_match.group(1))

                    # Filter by date range
                    if start_date <= pub_date <= end_date:
                        issues.append((pub_date, issue_num))

            except (ValueError, AttributeError) as e:
                logger.debug("gazzetta_parse_issue_link_error", href=href, error=str(e))

        # Remove duplicates and sort by date descending
        issues = list(set(issues))
        issues.sort(key=lambda x: x[0], reverse=True)

        return issues

    async def _scrape_gazette_issue(
        self,
        issue_date: date,
        issue_number: int,
        document_types: list[str] | None = None,
    ) -> list[GazzettaDocument]:
        """Scrape documents from a specific gazette issue.

        Args:
            issue_date: Publication date of the gazette
            issue_number: Issue number
            document_types: Specific document types to filter

        Returns:
            List of GazzettaDocument objects
        """
        documents: list[GazzettaDocument] = []

        # Build issue detail URL
        issue_url = (
            f"{self.BASE_URL}/gazzetta/serie_generale/caricaDettaglio"
            f"?dataPubblicazioneGazzetta={issue_date.strftime('%Y-%m-%d')}"
            f"&numeroGazzetta={issue_number}"
        )

        logger.debug("gazzetta_fetching_issue", date=str(issue_date), number=issue_number)

        html_content = await self._fetch_page_with_retry(issue_url)
        if not html_content:
            return documents

        soup = BeautifulSoup(html_content, "html.parser")

        # Find document links
        # Pattern: /atto/serie_generale/caricaDettaglioAtto/originario?atto.dataPubblicazioneGazzetta=...&atto.codiceRedazionale=...
        doc_links = soup.find_all("a", href=re.compile(r"/atto/serie_generale/caricaDettaglioAtto"))

        for link in doc_links:
            try:
                href = link.get("href", "")
                title = link.get_text(strip=True)

                if not href or not title:
                    continue

                # Skip navigation/utility links
                if len(title) < 10:
                    continue

                # Make URL absolute
                url = urljoin(self.BASE_URL, href)

                # Extract document code from URL
                code_match = re.search(r"codiceRedazionale=([A-Z0-9]+)", href)
                document_code = code_match.group(1) if code_match else None

                # Determine document type
                doc_type = self._determine_document_type(title)

                # Filter by document type if specified
                if document_types and doc_type not in document_types:
                    continue

                doc = GazzettaDocument(
                    title=title,
                    url=url,
                    document_type=doc_type,
                    document_number=document_code or self._extract_document_number(title),
                    published_date=issue_date,
                    series="serie_generale",
                )

                documents.append(doc)

            except Exception as e:
                logger.debug("gazzetta_parse_doc_link_error", error=str(e))

        logger.debug(
            "gazzetta_issue_scraped",
            date=str(issue_date),
            number=issue_number,
            documents=len(documents),
        )

        return documents

    def _parse_document_link(
        self,
        link: Tag,
        start_date: date,
        end_date: date,
    ) -> GazzettaDocument | None:
        """Parse a document link from the listing page.

        Args:
            link: BeautifulSoup Tag element
            start_date: Minimum date filter
            end_date: Maximum date filter

        Returns:
            GazzettaDocument or None
        """
        href = link.get("href", "")
        if not href:
            return None

        # Make URL absolute
        url = urljoin(self.BASE_URL, href)

        # Extract title
        title = link.get_text(strip=True)
        if not title:
            return None

        # Determine document type from title
        document_type = self._determine_document_type(title)

        # Extract document number if present
        document_number = self._extract_document_number(title)

        # Try to extract date from title or URL
        published_date = self._extract_date_from_text(title) or self._extract_date_from_url(href)

        # Filter by date
        if published_date:
            if published_date < start_date or published_date > end_date:
                return None

        return GazzettaDocument(
            title=title,
            url=url,
            document_type=document_type,
            document_number=document_number,
            published_date=published_date,
        )

    def _determine_document_type(self, title: str) -> str:
        """Determine document type from title."""
        title_lower = title.lower()

        if "decreto legislativo" in title_lower or "d.lgs" in title_lower:
            return "decreto_legislativo"
        elif "decreto legge" in title_lower or "d.l." in title_lower:
            return "decreto_legge"
        elif "dpcm" in title_lower or "decreto del presidente del consiglio" in title_lower:
            return "dpcm"
        elif "decreto" in title_lower:
            return "decreto"
        elif "legge" in title_lower:
            return "legge"
        elif "circolare" in title_lower:
            return "circolare"
        elif "ordinanza" in title_lower:
            return "ordinanza"
        elif "delibera" in title_lower:
            return "delibera"
        else:
            return "atto_normativo"

    def _extract_document_number(self, title: str) -> str | None:
        """Extract document number from title."""
        # Pattern: "n. 123" or "n.123" or "numero 123"
        patterns = [
            r"n\.\s*(\d+(?:/\d+)?)",
            r"numero\s+(\d+(?:/\d+)?)",
            r"(\d+/\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_date_from_text(self, text: str) -> date | None:
        """Extract date from text."""
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

        # Pattern: "15 marzo 2024"
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

    def _extract_date_from_url(self, url: str) -> date | None:
        """Extract date from URL pattern."""
        # Pattern: /2024/03/15/ or /20240315/
        patterns = [
            r"/(\d{4})/(\d{2})/(\d{2})/",
            r"/(\d{4})(\d{2})(\d{2})/",
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

    def _filter_documents_by_topics(
        self,
        documents: list[GazzettaDocument],
        filter_tax: bool,
        filter_labor: bool,
    ) -> list[GazzettaDocument]:
        """Filter documents by topic keywords.

        Args:
            documents: List of documents to filter
            filter_tax: Include tax-related documents
            filter_labor: Include labor-related documents

        Returns:
            Filtered list of documents
        """
        if not filter_tax and not filter_labor:
            return documents

        filtered = []
        keywords = []

        if filter_tax:
            keywords.extend(self.TAX_KEYWORDS)
        if filter_labor:
            keywords.extend(self.LABOR_KEYWORDS)

        for doc in documents:
            title_lower = doc.title.lower()
            summary_lower = (doc.summary or "").lower()
            combined_text = f"{title_lower} {summary_lower}"

            # Check if any keyword matches
            if any(kw in combined_text for kw in keywords):
                # Extract matching topics
                doc.topics = [kw for kw in keywords if kw in combined_text]
                filtered.append(doc)

        logger.info(
            "gazzetta_documents_filtered",
            original_count=len(documents),
            filtered_count=len(filtered),
        )

        return filtered

    async def _fetch_document_content(self, doc: GazzettaDocument) -> GazzettaDocument | None:
        """Fetch full document content.

        Args:
            doc: GazzettaDocument with URL

        Returns:
            GazzettaDocument with full text or None
        """
        html_content = await self._fetch_page_with_retry(doc.url)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        # Look for main content area
        content_selectors = [
            ".contenuto-atto",
            ".testo-atto",
            "#contenuto-principale",
            ".article-content",
            "article",
            "main",
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

        # Generate content hash
        doc.generate_content_hash()

        return doc

    async def scrape_and_integrate(
        self,
        days_back: int = 1,
        filter_tax: bool = True,
        filter_labor: bool = True,
    ) -> list[dict[str, Any]]:
        """Scrape documents and prepare for knowledge base integration.

        Args:
            days_back: Number of days to look back
            filter_tax: Include tax-related documents
            filter_labor: Include labor-related documents

        Returns:
            List of document dictionaries ready for knowledge base
        """
        documents = []

        # Scrape document list
        start_date = date.today() - timedelta(days=days_back)
        end_date = date.today()

        doc_list = await self._scrape_document_list(start_date, end_date, None)

        # Filter by topics
        if filter_tax or filter_labor:
            doc_list = self._filter_documents_by_topics(doc_list, filter_tax, filter_labor)

        # Fetch full content for each document
        for doc in doc_list:
            try:
                full_doc = await self._fetch_document_content(doc)
                if full_doc and full_doc.full_text:
                    documents.append(full_doc.to_dict())
            except Exception as e:
                logger.error("gazzetta_integration_error", url=doc.url, error=str(e))

        logger.info("gazzetta_integration_prepared", document_count=len(documents))

        return documents


# Convenience function for scheduled task integration
async def scrape_gazzetta_daily_task(db_session: AsyncSession | None = None) -> ScrapingResult:
    """Scheduled task function for daily Gazzetta Ufficiale scraping.

    This function is called by the scheduler service daily.

    Args:
        db_session: Database session for persistence. If not provided,
                    documents will be scraped but not saved to DB.
    """
    try:
        async with GazzettaScraper(db_session=db_session) as scraper:
            result = await scraper.scrape_recent_documents(
                days_back=1,
                filter_tax=True,
                filter_labor=True,
            )

            logger.info(
                "scheduled_gazzetta_scraping_completed",
                documents_found=result.documents_found,
                documents_saved=result.documents_saved,
                errors=result.errors,
                persistence_enabled=db_session is not None,
            )

            return cast(ScrapingResult, result)

    except Exception as e:
        logger.error("scheduled_gazzetta_scraping_failed", error=str(e))
        return ScrapingResult(errors=1)
