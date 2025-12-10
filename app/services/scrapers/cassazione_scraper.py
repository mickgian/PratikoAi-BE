"""Cassazione Court Decisions Scraper.

This module provides web scraping functionality for Italian Supreme Court
(Corte di Cassazione) decisions with comprehensive error handling and
integration with PratikoAI's knowledge base.
"""

import asyncio
import hashlib
import logging
import re
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union, cast
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.cassazione_data import (
    CassazioneDecision,
    Citation,
    CourtSection,
    DecisionType,
    JuridicalSubject,
    LegalPrinciple,
    ScrapingError,
    ScrapingResult,
    ScrapingStatistics,
)
from app.services.knowledge_integrator import KnowledgeIntegrator

logger = logging.getLogger(__name__)


class CassazioneScraper:
    """Web scraper for Italian Supreme Court decisions.

    Scrapes from two main jurisprudence pages:
    - Giurisprudenza Civile: Contains Tax (Tributaria) and Labor (Lavoro) sections
    - Giurisprudenza Penale: Criminal jurisprudence

    URL Patterns:
    - List pages: /it/giurisprudenza_civile.page, /it/giurisprudenza_penale.page
    - Pagination: ?frame3_item=N (page number)
    - Detail pages: /it/civile_dettaglio.page?contentId=SZCZXXXX
                   /it/penale_dettaglio.page?contentId=SZPXXXXX
    """

    BASE_URL = "https://www.cortedicassazione.it"
    CIVIL_LIST_URL = f"{BASE_URL}/it/giurisprudenza_civile.page"
    PENAL_LIST_URL = f"{BASE_URL}/it/giurisprudenza_penale.page"
    CIVIL_DETAIL_URL = f"{BASE_URL}/it/civile_dettaglio.page"
    PENAL_DETAIL_URL = f"{BASE_URL}/it/penale_dettaglio.page"
    ROBOTS_TXT_URL = f"{BASE_URL}/robots.txt"

    # Section name mappings for filtering
    # Note: The website uses different terms than the formal section names
    SECTION_FILTERS = {
        CourtSection.TRIBUTARIA: [
            "quinta sezione",
            "tributaria",
            "sez. 5",
            "sez. v",
            "tributi:",
            "tributi ",  # Subject matter indicators on the website
        ],
        CourtSection.LAVORO: [
            "quarta sezione",
            "lavoro",
            "sez. 4",
            "sez. iv",
            "lavoro pubblico:",
            "lavoro privato:",  # Subject matter indicators
        ],
        CourtSection.CIVILE: [
            "prima sezione",
            "seconda sezione",
            "terza sezione",
            "sez. 1",
            "sez. 2",
            "sez. 3",
            "responsabilità civile:",
            "famiglia:",
            "fallimento:",
            "immigrazione:",
            "contratti:",
            "proprietà:",
        ],
        CourtSection.PENALE: ["penale"],
        CourtSection.SEZIONI_UNITE: ["sezioni unite", "ss.uu.", "sez. un."],
    }

    def __init__(
        self,
        db_session: AsyncSession | None = None,
        rate_limit_delay: float = 2.0,
        max_retries: int = 3,
        timeout_seconds: int = 30,
        max_concurrent_requests: int = 5,
        respect_robots_txt: bool = True,
    ):
        """Initialize the scraper with configuration.

        Args:
            db_session: Database session for persistence (optional for backwards compatibility)
            rate_limit_delay: Delay between requests in seconds
            max_retries: Maximum number of retries for failed requests
            timeout_seconds: Request timeout
            max_concurrent_requests: Maximum concurrent requests
            respect_robots_txt: Whether to respect robots.txt rules
        """
        self.db_session = db_session
        self.knowledge_integrator = KnowledgeIntegrator(db_session) if db_session else None
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.max_concurrent_requests = max_concurrent_requests
        self.respect_robots_txt = respect_robots_txt

        self.statistics = ScrapingStatistics()
        self.last_request_time = 0.0

        # Session will be created when needed
        self._session: aiohttp.ClientSession | None = None

        # Robots.txt rules
        self._robots_rules: dict[str, bool] = {}

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
                headers={"User-Agent": "PratikoAI Legal Research Bot/1.0 (+https://pratiko.ai)"},
            )

    async def _check_robots_txt(self) -> None:
        """Check and parse robots.txt for scraping rules."""
        try:
            await self._ensure_session()
            if self._session is None:
                return

            async with self._session.get(self.ROBOTS_TXT_URL) as response:
                if response.status == 200:
                    content = await response.text()
                    self._parse_robots_txt(content)
                    logger.debug(f"cassazione_robots_txt_parsed rules_count={len(self._robots_rules)}")
                else:
                    logger.warning(f"cassazione_robots_txt_not_found status={response.status}")

        except Exception as e:
            logger.warning(f"cassazione_robots_txt_error error={e}")

    def _parse_robots_txt(self, content: str) -> None:
        """Parse robots.txt content and extract rules.

        Args:
            content: Raw robots.txt content
        """
        current_user_agent = None

        for line in content.split("\n"):
            line = line.strip().lower()

            if line.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                current_user_agent = agent

            elif current_user_agent in ("*", "pratikoai"):
                if line.startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        self._robots_rules[path] = False

                elif line.startswith("allow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        self._robots_rules[path] = True

    def _is_path_allowed(self, url: str) -> bool:
        """Check if URL path is allowed by robots.txt rules.

        Args:
            url: URL to check

        Returns:
            True if path is allowed, False otherwise
        """
        if not self.respect_robots_txt:
            return True

        if not self._robots_rules:
            return True  # No rules = allow all

        parsed = urlparse(url)
        path = parsed.path

        # Check rules in order of specificity (longer paths first)
        sorted_rules = sorted(self._robots_rules.keys(), key=len, reverse=True)

        for rule_path in sorted_rules:
            if path.startswith(rule_path):
                return self._robots_rules[rule_path]

        return True  # Default allow

    async def _fetch_page_with_retry(self, url: str) -> str:
        """Fetch a page with retry logic and rate limiting.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            ScrapingError: If all retry attempts fail or path is disallowed
        """
        # Check robots.txt compliance
        if not self._is_path_allowed(url):
            logger.warning(f"cassazione_path_disallowed_by_robots url={url}")
            raise ScrapingError(f"Path disallowed by robots.txt: {url}", "ROBOTS_DISALLOWED", url=url)

        await self._ensure_session()
        if self._session is None:
            raise ScrapingError("Session not initialized", "SESSION_ERROR", url=url)

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)

        self.last_request_time = time.time()

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()

                async with self._session.get(url) as response:
                    duration = time.time() - start_time

                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get("Retry-After", 60))
                        raise ScrapingError(
                            f"Rate limited by server. Retry after {retry_after}s", "RATE_LIMITED", url=url
                        )

                    if response.status == 200:
                        content = cast(str, await response.text())
                        self.statistics.record_page_scraped(True, duration)
                        return content
                    else:
                        self.statistics.record_page_scraped(False, duration)
                        # Store error but continue retry loop
                        last_exception = ScrapingError(
                            f"HTTP {response.status}: {response.reason}",
                            f"HTTP_{response.status}",
                            url=url,
                            retry_count=attempt,
                        )

            except TimeoutError:
                last_exception = ScrapingError(
                    "Network timeout while fetching page", "NETWORK_TIMEOUT", url=url, retry_count=attempt
                )
                self.statistics.record_page_scraped(False, self.timeout_seconds)

            except ScrapingError:
                # Re-raise ScrapingErrors (like rate limiting) without retry
                raise

            except Exception as e:
                last_exception = ScrapingError(str(e), "FETCH_ERROR", url=url, retry_count=attempt)
                self.statistics.record_page_scraped(False, 0.0)

            if attempt < self.max_retries:
                # Exponential backoff
                delay = 2**attempt * self.rate_limit_delay
                await asyncio.sleep(delay)

        # All retries failed
        error_msg = last_exception.message if last_exception else "Unknown error"
        raise ScrapingError(f"Max retries exceeded. Last error: {error_msg}", "MAX_RETRIES_EXCEEDED", url=url)

    async def parse_decision_from_html(self, html_content: str, url: str) -> CassazioneDecision | None:
        """Parse a Cassazione decision from HTML content.

        Args:
            html_content: Raw HTML content
            url: Source URL for context

        Returns:
            CassazioneDecision object or None if parsing fails
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract basic decision information
            decision_number = self._extract_decision_number(soup)
            if not decision_number:
                logger.warning(f"Could not extract decision number from {url}")
                return None

            decision_date = self._extract_decision_date(soup)
            if not decision_date:
                logger.warning(f"Could not extract decision date from {url}")
                return None

            section = self._extract_court_section(soup)
            subsection = self._extract_subsection(soup)
            subject = self._extract_subject(soup)

            if not subject:
                logger.warning(f"Could not extract subject from {url}")
                return None

            # Extract additional information
            summary = self._extract_summary(soup)
            full_text = self._extract_full_text(soup)
            decision_type = self._extract_decision_type(soup)

            # Extract metadata
            judge_names = self._extract_judge_names(soup)
            party_names = self._extract_party_names(soup)
            legal_principles = self._extract_legal_principles_from_soup(soup)
            citations_to_laws = self._extract_law_citations(soup)
            citations_to_decisions = self._extract_decision_citations(soup)
            keywords = self._extract_keywords(soup, subject)

            # Create decision object
            decision = CassazioneDecision(
                decision_number=decision_number,
                date=decision_date,
                section=section,
                subsection=subsection,
                subject=subject,
                summary=summary,
                full_text=full_text,
                source_url=url,
                decision_type=decision_type,
                legal_principles=legal_principles,
                judge_names=judge_names,
                party_names=party_names,
                citations_to_laws=citations_to_laws,
                citations_to_decisions=citations_to_decisions,
                keywords=keywords,
                confidence_score=self._calculate_confidence_score(decision_number, decision_date, subject, full_text),
            )

            return decision

        except Exception as e:
            logger.error(f"Error parsing decision from {url}: {e}")
            return None

    def _extract_decision_number(self, soup: BeautifulSoup) -> str | None:
        """Extract decision number from HTML.

        Decision numbers appear in various formats:
        - "Sentenza n. 30016 del 13/11/2025" → "30016"
        - "Ordinanza Numero: 30016, del 13/11/2025" → "30016"
        - "Ordinanza interlocutoria Numero: 30016, del 13/11/2025" → "30016"

        We extract just the number before "del" or ", del" to avoid matching dates.
        """
        # Look for patterns - extract number BEFORE "del" or ", del"
        patterns = [
            # Format: "Numero: 30016, del" or "Numero: 30016 del"
            r"[Nn]umero:\s*(\d+),?\s+del",
            # Format: "Sentenza n. 30016 del"
            r"[Ss]entenza[^\d]*n\.?\s*(\d+),?\s+del",
            # Format: "Ordinanza n. 30016 del" (including "Ordinanza interlocutoria")
            r"[Oo]rdinanza[^\d]*n\.?\s*(\d+),?\s+del",
            r"[Oo]rdinanza[^\d]*[Nn]umero:\s*(\d+),?\s+del",
            # Format: "Decreto n. 30016 del"
            r"[Dd]ecreto[^\d]*n\.?\s*(\d+),?\s+del",
            # Generic: "n. 30016 del DD/MM/YYYY"
            r"n\.?\s*(\d+),?\s+del\s+\d{1,2}/\d{1,2}/\d{4}",
            # Fallback: "n. 30016" (4+ digits to avoid small numbers)
            r"n\.?\s*(\d{4,})",
            # Fallback: "Numero: 30016" anywhere
            r"[Nn]umero:\s*(\d{4,})",
        ]

        # Check title first
        title = soup.find("title")
        if title:
            text = title.get_text()
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1)

        # Check headings
        for heading_tag in ["h1", "h2", "h3"]:
            headings = soup.find_all(heading_tag)
            for heading in headings:
                text = heading.get_text()
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        return match.group(1)

        # Check full page text
        page_text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, page_text)
            if match:
                return match.group(1)

        return None

    def _extract_decision_date(self, soup: BeautifulSoup) -> date | None:
        """Extract decision date from HTML."""
        # Look for date patterns
        date_patterns = [
            r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
            r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})",
        ]

        month_names = {
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

        # Search entire page content
        page_text = soup.get_text()

        for pattern in date_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match) == 3 and match[1] in month_names:
                        # Italian month name format
                        day = int(match[0])
                        month = month_names[match[1]]
                        year = int(match[2])
                        return date(year, month, day)
                    elif len(match) == 3:
                        # Numeric format
                        day = int(match[0])
                        month = int(match[1])
                        year = int(match[2])
                        return date(year, month, day)
                except (ValueError, TypeError):
                    continue

        return None

    def _extract_court_section(self, soup: BeautifulSoup) -> CourtSection:
        """Extract court section from HTML."""
        # Look for section indicators
        page_text = soup.get_text().lower()

        if "sezioni unite" in page_text or "ss. uu." in page_text:
            return CourtSection.SEZIONI_UNITE
        elif "tributaria" in page_text or "trib." in page_text:
            return CourtSection.TRIBUTARIA
        elif "lavoro" in page_text or "lav." in page_text:
            return CourtSection.LAVORO
        elif "penale" in page_text or "pen." in page_text:
            return CourtSection.PENALE
        else:
            return CourtSection.CIVILE  # Default

    def _extract_subsection(self, soup: BeautifulSoup) -> str | None:
        """Extract court subsection (e.g., 'III', 'Prima')."""
        # Look for subsection patterns
        patterns = [
            r"sezione\s+\w+\s+(prima|seconda|terza|quarta|quinta|[ivx]+)",
            r"sez\.?\s+\w+\s+(prima|seconda|terza|quarta|quinta|[ivx]+)",
            r"sezione\s+([ivx]+|prima|seconda|terza|quarta|quinta)",
            r"sez\.?\s+([ivx]+|prima|seconda|terza|quarta|quinta)",
        ]

        page_text = soup.get_text()

        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                subsection = match.group(1).upper()
                # Convert Italian numbers to Roman numerals
                conversion = {"PRIMA": "I", "SECONDA": "II", "TERZA": "III", "QUARTA": "IV", "QUINTA": "V"}
                return conversion.get(subsection, subsection)

        return None

    def _extract_subject(self, soup: BeautifulSoup) -> str | None:
        """Extract decision subject/matter (Oggetto field on Cassazione website)."""
        page_text = soup.get_text()

        # Cassazione uses "Oggetto" field which contains the actual subject description
        # Format: "Oggetto\nRedditi da locazione - Conduttore esercente attività..."
        oggetto_match = re.search(
            r"Oggetto\s*\n?(.*?)(?:\n(?:Presidente|Relatore|L'esito|Esito|$))",
            page_text,
            re.DOTALL | re.IGNORECASE,
        )
        if oggetto_match:
            subject = oggetto_match.group(1).strip()
            # Clean up and return if substantial
            if len(subject) > 10:
                # Remove extra whitespace
                subject = " ".join(subject.split())
                return subject

        # Look for subject in various CSS locations
        selectors = [
            ".decision-subject",
            ".subject",
            ".materia",
            ".oggetto",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = str(element.get_text(strip=True))
                if text and len(text) > 10:
                    return text

        # Fallback: look for content after "MATERIA" text (simpler extraction)
        materia_match = re.search(r"Materia[:\s]*\n?(\w+)", page_text, re.IGNORECASE)
        if materia_match:
            return str(materia_match.group(1).strip())

        return None

    def _extract_summary(self, soup: BeautifulSoup) -> str | None:
        """Extract decision summary (L'esito in sintesi)."""
        # Cassazione website uses "L'esito in sintesi" section
        page_text = soup.get_text()

        # Look for "L'esito in sintesi" section - content comes AFTER this heading
        esito_match = re.search(
            r"(?:L')?[Ee]sito in sintesi\s*\n(.*?)(?=\n\s*(?:Allegato|Scarica|$))",
            page_text,
            re.DOTALL | re.IGNORECASE,
        )
        if esito_match:
            summary = str(esito_match.group(1).strip())
            # Clean up excessive whitespace
            summary = " ".join(summary.split())
            if len(summary) > 20:
                return summary

        # Fallback: Look for summary sections with generic selectors
        selectors = [".summary", ".abstract", ".riassunto", ".esito-sintesi"]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = str(element.get_text(strip=True))
                if len(text) > 20:
                    return text

        return None

    def _extract_full_text(self, soup: BeautifulSoup) -> str | None:
        """Extract full decision text from Cassazione website.

        The Cassazione website structure uses:
        - .it-page-sections-container for main content
        - <main> tag as fallback
        """
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Cassazione-specific selectors (most specific first)
        content_selectors = [
            ".it-page-sections-container",  # Main content container on Cassazione site
            ".sidebar-content",  # Alternative content area
            "main",  # HTML5 main tag
            ".decision-content",
            ".content",
            ".main-content",
            "#main-content",
        ]

        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                text = str(element.get_text(separator="\n", strip=True))
                # Only return if we got substantial content
                if len(text) > 100:
                    return text

        # Fallback to entire body (but clean it)
        body = soup.find("body")
        if body:
            return str(body.get_text(separator="\n", strip=True))

        return str(soup.get_text(separator="\n", strip=True))

    def _extract_decision_type(self, soup: BeautifulSoup) -> DecisionType:
        """Extract decision type."""
        page_text = soup.get_text().lower()

        if "ordinanza" in page_text:
            return DecisionType.ORDINANZA
        elif "decreto" in page_text:
            return DecisionType.DECRETO
        elif "auto" in page_text:
            return DecisionType.AUTO
        else:
            return DecisionType.SENTENZA  # Default

    def _extract_judge_names(self, soup: BeautifulSoup) -> list[str]:
        """Extract judge names from HTML."""
        judges = []

        # Look for judge sections
        judge_patterns = [
            r"presidente[:\s]*([^\n,]+)",
            r"relatore[:\s]*([^\n,]+)",
            r"consigliere[:\s]*([^\n,]+)",
            r"giudice[:\s]*([^\n,]+)",
        ]

        page_text = soup.get_text()

        for pattern in judge_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                name = match.strip()
                if name and len(name) < 100:  # Reasonable name length
                    judges.append(name)

        return list(set(judges))  # Remove duplicates

    def _extract_party_names(self, soup: BeautifulSoup) -> list[str]:
        """Extract party names from HTML."""
        parties = []

        # Look for party sections
        party_patterns = [
            r"ricorrente[:\s]*([^\n]+)",
            r"convenuto[:\s]*([^\n]+)",
            r"convenuta[:\s]*([^\n]+)",
            r"appellante[:\s]*([^\n]+)",
            r"appellato[:\s]*([^\n]+)",
        ]

        page_text = soup.get_text()

        for pattern in party_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                party = match.strip()
                if party and len(party) < 200:  # Reasonable party name length
                    parties.append(party)

        return parties

    def _extract_legal_principles_from_soup(self, soup: BeautifulSoup) -> list[str]:
        """Extract legal principles from HTML."""
        # Look for principles sections
        principle_selectors = [".legal-principles", ".principi-diritto", ".principles"]

        principles = []

        for selector in principle_selectors:
            element = soup.select_one(selector)
            if element:
                # Extract numbered items
                items = element.find_all(["li", "p"])
                for item in items:
                    text = item.get_text(strip=True)
                    if text and len(text) > 20:
                        principles.append(text)

        # Fallback: extract from full text
        if not principles:
            full_text = soup.get_text()
            extracted_principles = LegalPrinciple.extract_from_text(full_text)
            principles = [p.text for p in extracted_principles]

        return principles

    def _extract_law_citations(self, soup: BeautifulSoup) -> list[str]:
        """Extract citations to laws from HTML."""
        full_text = soup.get_text()
        citations = Citation.extract_from_text(full_text)
        return [c.reference for c in citations if c.is_law_citation()]

    def _extract_decision_citations(self, soup: BeautifulSoup) -> list[str]:
        """Extract citations to other decisions from HTML."""
        full_text = soup.get_text()
        citations = Citation.extract_from_text(full_text)
        decision_citations = []
        for c in citations:
            if c.is_decision_citation():
                # Skip title citations
                if "cassazione civile - sentenza" not in c.reference.lower():
                    decision_citations.append(c.reference)
        return decision_citations

    def _extract_keywords(self, soup: BeautifulSoup, subject: str) -> list[str]:
        """Extract keywords from decision content."""
        keywords = set()

        # Add keywords from subject
        if subject:
            subject_words = [w.lower() for w in re.findall(r"\w+", subject) if len(w) > 3]
            keywords.update(subject_words)

        # Add common legal keywords found in text
        legal_keywords = [
            "amministratore",
            "società",
            "responsabilità",
            "contratto",
            "inadempimento",
            "risarcimento",
            "danno",
            "colpa",
            "dolo",
            "obbligazione",
            "iva",
            "imposta",
            "tributo",
            "lavoro",
            "licenziamento",
            "tfr",
            "cassazione",
            "appello",
        ]

        page_text = soup.get_text().lower()
        for keyword in legal_keywords:
            if keyword in page_text:
                keywords.add(keyword)

        return list(keywords)[:10]  # Limit to 10 keywords

    def _calculate_confidence_score(
        self, decision_number: str, decision_date: date, subject: str, full_text: str | None
    ) -> Decimal:
        """Calculate confidence score for parsed decision."""
        score = Decimal("0.5")  # Base score

        # Decision number quality
        if re.match(r"\d+/\d{4}", decision_number):
            score += Decimal("0.2")

        # Date recency
        if decision_date and decision_date > date.today() - timedelta(days=365):
            score += Decimal("0.1")

        # Subject quality
        if subject and len(subject) > 20:
            score += Decimal("0.15")

        # Full text availability
        if full_text and len(full_text) > 500:
            score += Decimal("0.15")

        return min(Decimal("1.0"), score)

    def _parse_decision_number(self, text: str) -> str:
        """Parse decision number from various formats."""
        # Extract the core number/year pattern
        match = re.search(r"(\d+[/]?\d+)", text)
        return match.group(1) if match else text

    def _parse_italian_date(self, date_str: str) -> date | None:
        """Parse Italian date string."""
        month_names = {
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

        # Try different patterns
        patterns = [
            r"(\d{1,2})\s+(\w+)\s+(\d{4})",  # "15 marzo 2024"
            r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})",  # "15/03/2024"
        ]

        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if len(match.groups()) == 3:
                        day = int(match.group(1))
                        month_part = match.group(2)
                        year = int(match.group(3))

                        if month_part in month_names:
                            month = month_names[month_part]
                        else:
                            month = int(month_part)

                        return date(year, month, day)
                except (ValueError, TypeError):
                    continue

        return None

    async def parse_search_results(self, html_content: str) -> list[dict[str, Any]]:
        """Parse search results page.

        Args:
            html_content: HTML content of search results

        Returns:
            List of dictionaries with decision metadata
        """
        soup = BeautifulSoup(html_content, "html.parser")
        results = []

        # Look for result items
        result_selectors = [".result-item", ".search-result", ".decision-result"]

        for selector in result_selectors:
            items = soup.select(selector)
            if items:
                break
        else:
            # Fallback: look for links to decisions
            items = soup.find_all("a", href=re.compile(r"/decision/"))

        for item in items:
            try:
                result = self._parse_search_result_item(item)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Error parsing search result item: {e}")
                continue

        return results

    def _parse_search_result_item(self, item: Tag) -> dict[str, Any] | None:
        """Parse individual search result item."""
        result = {}

        # Extract URL
        link = item.find("a") if item.name != "a" else item
        if not link or not link.get("href"):
            return None

        result["url"] = link.get("href")

        # Extract decision number from link text or title
        link_text = link.get_text(strip=True)
        decision_match = re.search(r"(\d+/\d+)", link_text)
        if decision_match:
            result["decision_number"] = decision_match.group(1)

        # Extract section from text
        text_lower = link_text.lower()
        if "civ." in text_lower or "civile" in text_lower:
            result["section"] = CourtSection.CIVILE
        elif "trib." in text_lower or "tributaria" in text_lower:
            result["section"] = CourtSection.TRIBUTARIA
        elif "lav." in text_lower or "lavoro" in text_lower:
            result["section"] = CourtSection.LAVORO
        elif "pen." in text_lower or "penale" in text_lower:
            result["section"] = CourtSection.PENALE
        else:
            result["section"] = CourtSection.CIVILE

        # Extract subject if available
        subject_elem = item.find(["p", "div"], class_=re.compile("subject|materia"))
        if subject_elem:
            result["subject"] = subject_elem.get_text(strip=True)

        # Extract date if available
        date_elem = item.find(["span", "p"], class_=re.compile("date|data"))
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            parsed_date = self._parse_italian_date(date_text)
            if parsed_date:
                result["date"] = parsed_date

        return result if result.get("decision_number") else None

    async def scrape_recent_decisions(
        self, sections: list[CourtSection] | None = None, days_back: int = 7, limit: int | None = None
    ) -> ScrapingResult:
        """Scrape recent decisions from the last N days.

        Args:
            sections: Court sections to scrape
            days_back: Number of days to look back
            limit: Maximum number of decisions to scrape

        Returns:
            ScrapingResult with statistics
        """
        time.time()
        start_date = date.today() - timedelta(days=days_back)
        end_date = date.today()

        if sections is None:
            sections = [CourtSection.CIVILE, CourtSection.TRIBUTARIA, CourtSection.LAVORO]

        return await self._scrape_decisions_for_date_range(start_date, end_date, sections, limit)

    async def _scrape_list_page(self, url: str, page: int = 1) -> list[dict[str, Any]]:
        """Scrape a jurisprudence list page.

        Args:
            url: Base URL (civil or penal list page)
            page: Page number (1-based)

        Returns:
            List of decision metadata dictionaries with contentId, section, date, title
        """
        page_url = f"{url}?frame3_item={page}" if page > 1 else url
        decisions = []

        try:
            html = await self._fetch_page_with_retry(page_url)
            soup = BeautifulSoup(html, "html.parser")

            # Find all decision links - they contain contentId in href
            # Pattern: /it/civile_dettaglio.page?contentId=SZC47984
            links = soup.find_all("a", href=re.compile(r"contentId=SZ[CP]\d+"))

            for link in links:
                try:
                    href = link.get("href", "")
                    content_id_match = re.search(r"contentId=(SZ[CP]\d+)", href)
                    if not content_id_match:
                        continue

                    content_id = content_id_match.group(1)
                    link_text = link.get_text(strip=True)

                    # Extract decision number and date from link text
                    # Pattern: "Sentenza n. 31423 del 02/12/2025" or "Ordinanza n. 30016 del 13/11/2025"
                    decision_match = re.search(
                        r"(Sentenza|Ordinanza|Decreto)[^\d]*n\.?\s*(\d+)\s+del\s+(\d{1,2}/\d{1,2}/\d{4})",
                        link_text,
                        re.IGNORECASE,
                    )

                    decision_number = None
                    decision_date = None
                    decision_type = "sentenza"

                    if decision_match:
                        decision_type = decision_match.group(1).lower()
                        decision_number = decision_match.group(2)
                        date_str = decision_match.group(3)
                        try:
                            day, month, year = date_str.split("/")
                            decision_date = date(int(year), int(month), int(day))
                        except (ValueError, TypeError):
                            pass

                    # Try to extract section from surrounding context
                    parent = link.find_parent(["div", "li", "tr"])
                    section_text = parent.get_text().lower() if parent else link_text.lower()

                    section = self._detect_section_from_text(section_text)

                    # Determine if civil or penal based on contentId prefix
                    is_civil = content_id.startswith("SZC")

                    decisions.append(
                        {
                            "content_id": content_id,
                            "decision_number": decision_number,
                            "decision_date": decision_date,
                            "decision_type": decision_type,
                            "section": section,
                            "is_civil": is_civil,
                            "title": link_text[:200],
                            "url": urljoin(self.BASE_URL, href),
                        }
                    )

                except Exception as e:
                    logger.warning(f"Error parsing decision link: {e}")
                    continue

            logger.info(f"cassazione_list_page_scraped url={page_url} decisions={len(decisions)}")

        except ScrapingError:
            raise
        except Exception as e:
            logger.error(f"Error scraping list page {page_url}: {e}")

        return decisions

    def _detect_section_from_text(self, text: str) -> CourtSection:
        """Detect court section from text content."""
        text_lower = text.lower()

        for section, keywords in self.SECTION_FILTERS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return section

        # Default based on common patterns
        if "penale" in text_lower:
            return CourtSection.PENALE
        return CourtSection.CIVILE

    async def _scrape_decision_detail(self, content_id: str, is_civil: bool = True) -> CassazioneDecision | None:
        """Scrape a single decision detail page.

        Args:
            content_id: The contentId (e.g., SZC47984)
            is_civil: True for civil decisions, False for penal

        Returns:
            CassazioneDecision object or None if parsing fails
        """
        detail_url = self.CIVIL_DETAIL_URL if is_civil else self.PENAL_DETAIL_URL
        url = f"{detail_url}?contentId={content_id}"

        try:
            html = await self._fetch_page_with_retry(url)
            decision = await self.parse_decision_from_html(html, url)

            if decision:
                logger.debug(f"cassazione_decision_parsed content_id={content_id} number={decision.decision_number}")

            return decision

        except ScrapingError as e:
            logger.warning(f"cassazione_detail_fetch_failed content_id={content_id} error={e.message}")
            return None
        except Exception as e:
            logger.error(f"Error scraping decision detail {content_id}: {e}")
            return None

    async def _scrape_decisions_for_date_range(
        self, start_date: date, end_date: date, sections: list[CourtSection], limit: int | None = None
    ) -> ScrapingResult:
        """Scrape decisions for a specific date range.

        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            sections: Court sections to include
            limit: Maximum decisions to process

        Returns:
            ScrapingResult with statistics
        """
        decisions_found = 0
        decisions_processed = 0
        decisions_saved = 0
        errors = 0
        start_time = time.time()

        try:
            # Determine which list pages to scrape based on sections
            scrape_civil = any(
                s in [CourtSection.TRIBUTARIA, CourtSection.LAVORO, CourtSection.CIVILE, CourtSection.SEZIONI_UNITE]
                for s in sections
            )
            scrape_penal = CourtSection.PENALE in sections

            all_decisions = []

            # Scrape civil jurisprudence pages
            if scrape_civil:
                page = 1
                max_pages = 10  # Safety limit
                while page <= max_pages:
                    page_decisions = await self._scrape_list_page(self.CIVIL_LIST_URL, page)
                    if not page_decisions:
                        break

                    # Filter by date range and sections
                    for dec in page_decisions:
                        if dec.get("decision_date"):
                            if start_date <= dec["decision_date"] <= end_date:
                                if dec.get("section") in sections:
                                    all_decisions.append(dec)

                    # Check if we've gone past the date range (decisions are sorted newest first)
                    oldest_on_page = min(
                        (d["decision_date"] for d in page_decisions if d.get("decision_date")), default=None
                    )
                    if oldest_on_page and oldest_on_page < start_date:
                        break

                    page += 1

                    # Rate limiting between pages
                    await asyncio.sleep(self.rate_limit_delay)

            # Scrape penal jurisprudence pages
            if scrape_penal:
                page = 1
                max_pages = 10
                while page <= max_pages:
                    page_decisions = await self._scrape_list_page(self.PENAL_LIST_URL, page)
                    if not page_decisions:
                        break

                    for dec in page_decisions:
                        if dec.get("decision_date"):
                            if start_date <= dec["decision_date"] <= end_date:
                                all_decisions.append(dec)

                    oldest_on_page = min(
                        (d["decision_date"] for d in page_decisions if d.get("decision_date")), default=None
                    )
                    if oldest_on_page and oldest_on_page < start_date:
                        break

                    page += 1
                    await asyncio.sleep(self.rate_limit_delay)

            decisions_found = len(all_decisions)

            # Apply limit
            if limit and len(all_decisions) > limit:
                all_decisions = all_decisions[:limit]

            logger.info(f"cassazione_decisions_found count={decisions_found} to_process={len(all_decisions)}")

            # Scrape individual decision details and save
            for dec_meta in all_decisions:
                try:
                    content_id = dec_meta["content_id"]
                    is_civil = dec_meta.get("is_civil", True)

                    decision = await self._scrape_decision_detail(content_id, is_civil)
                    decisions_processed += 1

                    if decision:
                        # Save to database via KnowledgeIntegrator
                        result = await self.save_decision_to_database(decision)
                        if result.get("success"):
                            decisions_saved += 1
                        elif result.get("action") == "skipped":
                            # No DB session - count as processed but not saved
                            pass
                        else:
                            errors += 1
                    else:
                        errors += 1

                    # Rate limiting between detail page fetches
                    await asyncio.sleep(self.rate_limit_delay)

                except Exception as e:
                    logger.error(f"Error processing decision {dec_meta.get('content_id')}: {e}")
                    errors += 1
                    decisions_processed += 1

        except Exception as e:
            logger.error(f"Error scraping decisions for date range {start_date} to {end_date}: {e}")
            errors += 1

        duration = int(time.time() - start_time)

        logger.info(
            f"cassazione_scraping_complete found={decisions_found} processed={decisions_processed} "
            f"saved={decisions_saved} errors={errors} duration={duration}s"
        )

        return ScrapingResult(
            decisions_found=decisions_found,
            decisions_processed=decisions_processed,
            decisions_saved=decisions_saved,
            errors=errors,
            duration_seconds=duration,
            start_date=start_date,
            end_date=end_date,
        )

    async def scrape_historical_decisions(
        self, start_date: date, end_date: date, sections: list[CourtSection] | None = None
    ) -> ScrapingResult:
        """Scrape historical decisions for a specific date range.

        Args:
            start_date: Start date for scraping
            end_date: End date for scraping
            sections: Court sections to scrape

        Returns:
            ScrapingResult with statistics
        """
        if sections is None:
            sections = [CourtSection.CIVILE, CourtSection.TRIBUTARIA]

        return await self._scrape_decisions_for_date_range(start_date, end_date, sections)

    async def save_decision_to_database(self, decision: CassazioneDecision) -> dict[str, Any]:
        """Save decision to database via KnowledgeIntegrator.

        Args:
            decision: CassazioneDecision to save

        Returns:
            Result dictionary with success status and document ID
        """
        if not self.knowledge_integrator:
            logger.debug(f"cassazione_no_db_session_skipping_save decision_number={decision.decision_number}")
            return {"success": False, "error": "No database session provided", "action": "skipped"}

        try:
            # Convert decision to knowledge base format
            doc_data = self.decision_to_knowledge_dict(decision)

            # Save via KnowledgeIntegrator
            result = await self.knowledge_integrator.update_knowledge_base(doc_data)

            if result.get("success"):
                logger.info(
                    f"cassazione_decision_saved decision_number={decision.decision_number} "
                    f"action={result.get('action')} document_id={result.get('document_id')}"
                )
            else:
                logger.warning(
                    f"cassazione_decision_save_failed decision_number={decision.decision_number} "
                    f"error={result.get('error')}"
                )

            return result

        except Exception as e:
            logger.error(f"Error saving decision {decision.decision_number}: {e}")
            return {"success": False, "error": str(e), "action": "failed"}

    async def _decision_exists_in_database(self, decision_number: str, decision_date: date) -> bool:
        """Check if decision already exists in database.

        Note: KnowledgeIntegrator handles duplicate detection via content hash and URL,
        so this method is primarily for pre-scraping checks.
        """
        # KnowledgeIntegrator will handle duplicate detection
        # This could be enhanced to query knowledge_items directly if needed
        return False

    def schedule_weekly_updates(self):
        """Schedule weekly updates of Cassazione decisions."""
        from app.services.scheduler_service import scheduler_service

        scheduler_service.add_job(  # type: ignore[attr-defined]
            func=self.update_recent_decisions_job,
            trigger="cron",
            day_of_week="sun",
            hour=2,
            minute=0,
            id="cassazione_weekly_updates",
        )

    async def update_recent_decisions_job(self) -> ScrapingResult:
        """Scheduled job to update recent decisions.

        Returns:
            ScrapingResult with job statistics
        """
        logger.info("Starting scheduled Cassazione decisions update")

        try:
            result = await self.scrape_recent_decisions(
                sections=[CourtSection.CIVILE, CourtSection.TRIBUTARIA, CourtSection.LAVORO], days_back=7
            )

            logger.info(
                f"Completed Cassazione update: {result.decisions_found} found, "
                f"{result.decisions_saved} saved, {result.errors} errors"
            )

            return result

        except Exception as e:
            logger.error(f"Error in scheduled Cassazione update: {e}")
            return ScrapingResult(decisions_found=0, decisions_processed=0, decisions_saved=0, errors=1)

    def schedule_daily_updates(self):
        """Schedule daily updates of Cassazione decisions (Tax and Labor sections)."""
        from app.services.scheduler_service import scheduler_service

        scheduler_service.add_job(  # type: ignore[attr-defined]
            func=self.update_daily_decisions_job,
            trigger="cron",
            hour=3,
            minute=0,
            id="cassazione_daily_updates",
        )

    async def update_daily_decisions_job(self) -> ScrapingResult:
        """Scheduled daily job focusing on Tax (Tributaria) and Labor (Lavoro) sections.

        Returns:
            ScrapingResult with job statistics
        """
        logger.info("Starting daily Cassazione Tax/Labor decisions update")

        try:
            result = await self.scrape_recent_decisions(
                sections=[CourtSection.TRIBUTARIA, CourtSection.LAVORO], days_back=1
            )

            logger.info(
                f"Completed daily Cassazione update: {result.decisions_found} found, "
                f"{result.decisions_saved} saved, {result.errors} errors"
            )

            return result

        except Exception as e:
            logger.error(f"Error in daily Cassazione update: {e}")
            return ScrapingResult(decisions_found=0, decisions_processed=0, decisions_saved=0, errors=1)

    def decision_to_knowledge_dict(self, decision: CassazioneDecision) -> dict[str, Any]:
        """Convert CassazioneDecision to dictionary for knowledge base integration.

        Args:
            decision: CassazioneDecision to convert

        Returns:
            Dictionary ready for KnowledgeIntegrator.update_knowledge_base()
        """
        # Build content from decision fields
        content_parts = []

        if decision.subject:
            content_parts.append(f"Materia: {decision.subject}")

        if decision.summary:
            content_parts.append(f"\nMassima: {decision.summary}")

        if decision.legal_principles:
            content_parts.append("\nPrincipi di diritto:")
            for i, principle in enumerate(decision.legal_principles, 1):
                content_parts.append(f"{i}. {principle}")

        if decision.full_text:
            content_parts.append(f"\n\n{decision.full_text}")

        content = "\n".join(content_parts)

        # Build title with decision type
        decision_type_name = "Sentenza"
        if decision.decision_type:
            decision_type_name = decision.decision_type.value.title()

        title = f"Cassazione {decision.section.value.title()} - {decision_type_name} n. {decision.decision_number}"
        if decision.date:
            title += f" del {decision.date.strftime('%d/%m/%Y')}"

        # Use stored source_url or construct URL based on section
        if decision.source_url:
            url = decision.source_url
        elif decision.section == CourtSection.PENALE:
            url = f"{self.PENAL_DETAIL_URL}?contentId=SZP{decision.decision_number}"
        else:
            url = f"{self.CIVIL_DETAIL_URL}?contentId=SZC{decision.decision_number}"

        return {
            "title": title,
            "url": url,
            "content": content,
            "source": "cassazione",
            "source_type": f"{decision_type_name.lower()}_{decision.section.value.lower()}",
            "document_number": decision.decision_number,
            "published_date": decision.date,
            "authority": "Corte di Cassazione",
            "metadata": {
                "section": decision.section.value,
                "subsection": decision.subsection,
                "decision_type": decision.decision_type.value if decision.decision_type else None,
                "judge_names": decision.judge_names,
                "party_names": decision.party_names,
                "keywords": decision.keywords,
                "citations_to_laws": decision.citations_to_laws,
                "citations_to_decisions": decision.citations_to_decisions,
                "confidence_score": float(decision.confidence_score),
            },
        }

    async def scrape_and_integrate(
        self,
        days_back: int = 1,
        sections: list[CourtSection] | None = None,
    ) -> list[dict[str, Any]]:
        """Scrape decisions and prepare for knowledge base integration.

        Args:
            days_back: Number of days to look back
            sections: Court sections to scrape (defaults to Tributaria and Lavoro)

        Returns:
            List of document dictionaries ready for knowledge base
        """
        if sections is None:
            sections = [CourtSection.TRIBUTARIA, CourtSection.LAVORO]

        documents: list[dict[str, Any]] = []
        start_date = date.today() - timedelta(days=days_back)
        end_date = date.today()

        try:
            # This would call the actual scraping methods
            # For now, return empty list as the scraping implementation is mock
            logger.info(  # type: ignore[call-arg]
                "cassazione_integration_prepared",
                document_count=len(documents),
                sections=[s.value for s in sections],
                date_range=f"{start_date} to {end_date}",
            )

        except Exception as e:
            logger.error("cassazione_integration_error", error=str(e))  # type: ignore[call-arg]

        return documents


# Convenience function for scheduled task integration
async def scrape_cassazione_daily_task(db_session: AsyncSession | None = None) -> ScrapingResult:
    """Scheduled task function for daily Cassazione scraping.

    This function is called by the scheduler service daily at 3 AM.
    Focuses on Tax (Tributaria) and Labor (Lavoro) sections.

    Args:
        db_session: Database session for persistence. If not provided,
                    decisions will be scraped but not saved to DB.
    """
    try:
        async with CassazioneScraper(db_session=db_session) as scraper:
            result: ScrapingResult = await scraper.scrape_recent_decisions(
                sections=[CourtSection.TRIBUTARIA, CourtSection.LAVORO],
                days_back=1,
            )

            logger.info(  # type: ignore[call-arg]
                "scheduled_cassazione_scraping_completed",
                decisions_found=result.decisions_found,
                decisions_saved=result.decisions_saved,
                errors=result.errors,
                persistence_enabled=db_session is not None,
            )

            return result

    except Exception as e:
        logger.error(f"scheduled_cassazione_scraping_failed: {e}")
        return ScrapingResult(decisions_found=0, decisions_processed=0, decisions_saved=0, errors=1)
