"""CNEL (Consiglio Nazionale dell'Economia e del Lavoro) Data Source Integration.

This module integrates with the official CNEL archive, which is the authoritative
source for Italian collective labor agreements and labor market data.
"""

import asyncio
import hashlib
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from app.models.ccnl_data import CCNLSector

from .base_source import (
    BaseDataSource,
    CCNLDocument,
    DataSourceInfo,
    DataSourceQuery,
    DataSourceStatus,
    DataSourceType,
    UpdateFrequency,
)

logger = logging.getLogger(__name__)


class CNELDataSource(BaseDataSource):
    """Data source for CNEL (National Council for Economics and Labor)."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="cnel_official",
            name="CNEL - Consiglio Nazionale dell'Economia e del Lavoro",
            organization="Governo Italiano",
            source_type=DataSourceType.GOVERNMENT,
            base_url="https://www.cnel.it",
            description="Official archive of Italian collective labor agreements and economic analysis",
            supported_sectors=list(CCNLSector),  # CNEL covers all sectors
            update_frequency=UpdateFrequency.DAILY,
            reliability_score=0.95,  # Highest reliability as official source
            api_key_required=False,
            rate_limit=100,  # Conservative rate limit
            contact_info="segreteria@cnel.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None
        self.base_urls = {
            "agreements": f"{source_info.base_url}/Archivio-Contratti",
            "documents": f"{source_info.base_url}/Documenti",
            "search": f"{source_info.base_url}/ricerca",
            "latest": f"{source_info.base_url}/ultime-pubblicazioni",
        }

    async def connect(self) -> bool:
        """Establish connection to CNEL website."""
        try:
            if self.session and not self.session.closed:
                await self.session.close()

            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "PratikoAI-CCNL-Integration/1.0 (Labor Law Research)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                },
            )

            # Test connection
            async with self.session.get(self.source_info.base_url) as response:
                if response.status == 200:
                    self.source_info.status = DataSourceStatus.ACTIVE
                    self.source_info.last_updated = datetime.utcnow()
                    logger.info("Successfully connected to CNEL")
                    return True
                else:
                    self.source_info.status = DataSourceStatus.ERROR
                    logger.error(f"CNEL connection failed with status {response.status}")
                    return False

        except Exception as e:
            self.source_info.status = DataSourceStatus.ERROR
            logger.error(f"Error connecting to CNEL: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """Close connection to CNEL."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE
        logger.info("Disconnected from CNEL")

    async def test_connection(self) -> bool:
        """Test if connection to CNEL is working."""
        if not self.session or self.session.closed:
            return await self.connect()

        try:
            async with self.session.get(self.source_info.base_url, timeout=10) as response:
                return response.status == 200
        except Exception:
            return False

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        """Search for CCNL documents in CNEL archive."""
        if not await self.check_rate_limit():
            logger.warning("Rate limit exceeded for CNEL")
            return []

        documents = []

        try:
            # Build search parameters
            search_params = await self._build_search_params(query)

            # Search main agreements archive
            agreements = await self._search_agreements_archive(search_params)
            documents.extend(agreements)

            # Search documents section
            docs = await self._search_documents_section(search_params)
            documents.extend(docs)

            # Search latest publications if no date filter
            if not query.date_from:
                latest = await self._get_latest_publications()
                documents.extend(latest[:10])  # Limit to 10 latest

            await self.record_request()

            # Remove duplicates and filter by query parameters
            documents = await self._filter_and_deduplicate(documents, query)

            logger.info(f"Found {len(documents)} documents from CNEL")
            return documents[: query.max_results]

        except Exception as e:
            logger.error(f"Error searching CNEL: {str(e)}")
            return []

    async def get_document_content(self, document_id: str) -> str | None:
        """Retrieve full content of a CNEL document."""
        if not await self.check_rate_limit():
            return None

        try:
            # Extract URL from document ID (format: cnel_url_encoded_url)
            if document_id.startswith("cnel_"):
                url = document_id[5:].replace("_", "/")

                async with self.session.get(url) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        # Extract main content from HTML
                        content = await self._extract_content_from_html(html_content)
                        await self.record_request()
                        return content

            return None

        except Exception as e:
            logger.error(f"Error retrieving document content from CNEL: {str(e)}")
            return None

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Get latest CCNL updates from CNEL."""
        if not since:
            since = datetime.utcnow() - timedelta(days=30)

        try:
            latest_docs = await self._get_latest_publications()

            # Filter by date
            filtered_docs = []
            for doc in latest_docs:
                if doc.publication_date >= since.date():
                    filtered_docs.append(doc)

            return filtered_docs

        except Exception as e:
            logger.error(f"Error getting latest updates from CNEL: {str(e)}")
            return []

    async def _build_search_params(self, query: DataSourceQuery) -> dict[str, Any]:
        """Build search parameters for CNEL queries."""
        params = {}

        # Sector mapping to CNEL categories
        if query.sectors:
            sector_terms = []
            for sector in query.sectors:
                sector_terms.extend(self._map_sector_to_cnel_terms(sector))
            params["sectors"] = sector_terms

        # Date range
        if query.date_from:
            params["data_da"] = query.date_from.strftime("%d/%m/%Y")
        if query.date_to:
            params["data_a"] = query.date_to.strftime("%d/%m/%Y")

        # Keywords
        if query.keywords:
            params["keywords"] = " ".join(query.keywords)

        # Document types
        if query.document_types:
            params["tipo_documento"] = query.document_types

        return params

    async def _search_agreements_archive(self, params: dict[str, Any]) -> list[CCNLDocument]:
        """Search the CNEL agreements archive."""
        documents = []

        try:
            # CNEL agreements archive URL
            url = self.base_urls["agreements"]

            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Find agreement listings (this would need to be adapted based on actual CNEL HTML structure)
                agreement_links = soup.find_all("a", href=re.compile(r"contratto|accordo|ccnl", re.I))

                for link in agreement_links[:50]:  # Limit to avoid overload
                    doc = await self._extract_document_from_link(link, url)
                    if doc and self._matches_search_params(doc, params):
                        documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Error searching CNEL agreements archive: {str(e)}")
            return []

    async def _search_documents_section(self, params: dict[str, Any]) -> list[CCNLDocument]:
        """Search the CNEL documents section."""
        documents = []

        try:
            url = self.base_urls["documents"]

            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Find document listings
                doc_links = soup.find_all("a", href=re.compile(r"\.pdf|documento|pubblicazione", re.I))

                for link in doc_links[:30]:  # Limit to avoid overload
                    doc = await self._extract_document_from_link(link, url)
                    if doc and self._matches_search_params(doc, params):
                        documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Error searching CNEL documents section: {str(e)}")
            return []

    async def _get_latest_publications(self) -> list[CCNLDocument]:
        """Get latest publications from CNEL."""
        documents = []

        try:
            url = self.base_urls["latest"]

            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Extract latest publications (adapt based on actual HTML structure)
                recent_items = soup.find_all(["div", "li"], class_=re.compile(r"recent|latest|nuovo", re.I))

                for item in recent_items[:20]:
                    link = item.find("a", href=True)
                    if link:
                        doc = await self._extract_document_from_link(link, url)
                        if doc:
                            documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Error getting latest publications from CNEL: {str(e)}")
            return []

    async def _extract_document_from_link(self, link_element, base_url: str) -> CCNLDocument | None:
        """Extract document information from a link element."""
        try:
            href = link_element.get("href", "")
            title = link_element.get_text(strip=True)

            if not href or not title:
                return None

            # Make absolute URL
            if href.startswith("/"):
                full_url = self.source_info.base_url + href
            elif not href.startswith("http"):
                full_url = f"{base_url}/{href}"
            else:
                full_url = href

            # Generate document ID
            document_id = f"cnel_{hashlib.md5(full_url.encode()).hexdigest()}"

            # Detect sector from title
            sector = self._detect_sector_from_title(title)

            # Detect document type
            doc_type = self._detect_document_type(title, href)

            # Extract dates if possible
            pub_date = self._extract_date_from_title(title)
            if not pub_date:
                pub_date = date.today()

            # Generate content hash
            content_hash = hashlib.md5(f"{title}{full_url}".encode()).hexdigest()

            return CCNLDocument(
                document_id=document_id,
                source_id=self.source_info.source_id,
                title=title,
                sector=sector,
                publication_date=pub_date,
                effective_date=pub_date,
                expiry_date=None,  # Would need to extract from content
                document_type=doc_type,
                url=full_url,
                content_hash=content_hash,
                confidence_score=0.8,  # High confidence for official source
            )

        except Exception as e:
            logger.error(f"Error extracting document from link: {str(e)}")
            return None

    def _map_sector_to_cnel_terms(self, sector: CCNLSector) -> list[str]:
        """Map CCNL sector to CNEL search terms."""
        sector_mapping = {
            CCNLSector.METALMECCANICI_INDUSTRIA: ["metalmeccanici", "industria", "meccanica"],
            CCNLSector.COMMERCIO_TERZIARIO: ["commercio", "terziario", "distribuzione"],
            CCNLSector.EDILIZIA_INDUSTRIA: ["edilizia", "costruzioni", "lavori pubblici"],
            CCNLSector.SANITA_PRIVATA: ["sanità", "sanitario", "cliniche private"],
            CCNLSector.ICT: ["informatica", "tecnologia", "telecomunicazioni", "ICT"],
            CCNLSector.TRASPORTI_LOGISTICA: ["trasporti", "logistica", "spedizioni"],
            CCNLSector.TURISMO: ["turismo", "alberghi", "ristoranti", "pubblici esercizi"],
            CCNLSector.AGRICOLTURA: ["agricoltura", "coltivatori", "florovivaismo"],
            CCNLSector.CREDITO_ASSICURAZIONI: ["banche", "assicurazioni", "credito", "finanza"],
            CCNLSector.CHIMICI_FARMACEUTICI: ["chimici", "farmaceutici", "chimica", "farmacia"],
        }

        return sector_mapping.get(sector, [sector.value.replace("_", " ")])

    def _detect_sector_from_title(self, title: str) -> CCNLSector:
        """Detect CCNL sector from document title."""
        title_lower = title.lower()

        # Sector detection patterns
        for sector in CCNLSector:
            terms = self._map_sector_to_cnel_terms(sector)
            for term in terms:
                if term.lower() in title_lower:
                    return sector

        # Default fallback
        return CCNLSector.COMMERCIO_TERZIARIO

    def _detect_document_type(self, title: str, url: str) -> str:
        """Detect document type from title and URL."""
        title_lower = title.lower()
        url.lower()

        if any(term in title_lower for term in ["rinnovo", "rinnovato"]):
            return "renewal"
        elif any(term in title_lower for term in ["accordo", "contratto", "ccnl"]):
            return "agreement"
        elif any(term in title_lower for term in ["modifica", "integrazione"]):
            return "amendment"
        elif any(term in title_lower for term in ["interpretazione", "chiarimento"]):
            return "interpretation"
        else:
            return "document"

    def _extract_date_from_title(self, title: str) -> date | None:
        """Extract date from document title."""
        # Look for date patterns in Italian format
        date_patterns = [
            r"(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})",  # dd/mm/yyyy
            r"(\d{4})[/\.-](\d{1,2})[/\.-](\d{1,2})",  # yyyy/mm/dd
            r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
        ]

        month_mapping = {
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

        for pattern in date_patterns:
            match = re.search(pattern, title.lower())
            if match:
                try:
                    if "gennaio" in pattern:  # Italian month format
                        day, month_name, year = match.groups()
                        month = month_mapping.get(month_name, 1)
                        return date(int(year), month, int(day))
                    else:
                        # Assume first group is day, second is month for dd/mm/yyyy
                        day, month, year = match.groups()
                        if len(year) == 4:  # yyyy format
                            return date(int(year), int(month), int(day))
                        else:  # Assume first is year for yyyy/mm/dd
                            year, month, day = match.groups()
                            return date(int(year), int(month), int(day))
                except ValueError:
                    continue

        return None

    def _matches_search_params(self, doc: CCNLDocument, params: dict[str, Any]) -> bool:
        """Check if document matches search parameters."""
        # Check sector filter
        if "sectors" in params:
            sector_terms = params["sectors"]
            title_lower = doc.title.lower()
            if not any(term.lower() in title_lower for term in sector_terms):
                return False

        # Check date range
        if "data_da" in params:
            from_date = datetime.strptime(params["data_da"], "%d/%m/%Y").date()
            if doc.publication_date < from_date:
                return False

        if "data_a" in params:
            to_date = datetime.strptime(params["data_a"], "%d/%m/%Y").date()
            if doc.publication_date > to_date:
                return False

        # Check keywords
        if "keywords" in params:
            keywords = params["keywords"].lower()
            title_lower = doc.title.lower()
            if keywords not in title_lower:
                return False

        return True

    async def _extract_content_from_html(self, html_content: str) -> str:
        """Extract main content from HTML page."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Try to find main content area
            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", class_=re.compile(r"content|main|body", re.I))
                or soup.find("div", id=re.compile(r"content|main|body", re.I))
            )

            if main_content:
                return main_content.get_text(strip=True)
            else:
                # Fallback to body text
                return soup.get_text(strip=True)

        except Exception as e:
            logger.error(f"Error extracting content from HTML: {str(e)}")
            return html_content

    async def _filter_and_deduplicate(
        self, documents: list[CCNLDocument], query: DataSourceQuery
    ) -> list[CCNLDocument]:
        """Filter and deduplicate documents."""
        seen_hashes = set()
        filtered_docs = []

        for doc in documents:
            # Skip duplicates
            if doc.content_hash in seen_hashes:
                continue
            seen_hashes.add(doc.content_hash)

            # Apply additional filters
            if query.sectors and doc.sector not in query.sectors:
                continue

            if query.document_types and doc.document_type not in query.document_types:
                continue

            filtered_docs.append(doc)

        # Sort by publication date (newest first)
        filtered_docs.sort(key=lambda x: x.publication_date, reverse=True)

        return filtered_docs
