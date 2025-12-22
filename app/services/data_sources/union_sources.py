# mypy: disable-error-code="no-any-return, attr-defined, has-type, assignment, arg-type, var-annotated"
"""Union Confederations Data Sources Integration.

This module integrates with major Italian union confederations:
- CGIL (Confederazione Generale Italiana del Lavoro)
- CISL (Confederazione Italiana Sindacati Lavoratori)
- UIL (Unione Italiana del Lavoro)
- UGL (Unione Generale del Lavoro)
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


class CGILDataSource(BaseDataSource):
    """CGIL (Confederazione Generale Italiana del Lavoro) data source."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="cgil_union",
            name="CGIL - Confederazione Generale Italiana del Lavoro",
            organization="CGIL",
            source_type=DataSourceType.UNION,
            base_url="https://www.cgil.it",
            description="Largest Italian trade union confederation representing various sectors",
            supported_sectors=list(CCNLSector),
            update_frequency=UpdateFrequency.DAILY,
            reliability_score=0.90,
            api_key_required=False,
            rate_limit=200,
            contact_info="info@cgil.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None
        self.sector_unions = {
            CCNLSector.METALMECCANICI_INDUSTRIA: ["FIOM-CGIL"],
            CCNLSector.EDILIZIA_INDUSTRIA: ["FILLEA-CGIL"],
            CCNLSector.COMMERCIO_TERZIARIO: ["FILCAMS-CGIL"],
            CCNLSector.TRASPORTI_LOGISTICA: ["FILT-CGIL"],
            CCNLSector.SANITA_PRIVATA: ["FP-CGIL"],
            CCNLSector.PUBBLICI_ESERCIZI: ["FILCAMS-CGIL"],
            CCNLSector.AGRICOLTURA: ["FLAI-CGIL"],
            CCNLSector.CHIMICI_FARMACEUTICI: ["FILCTEM-CGIL"],
            CCNLSector.TESSILI: ["FILTEA-CGIL"],
        }

    async def connect(self) -> bool:
        """Connect to CGIL website."""
        return await self._generic_union_connect()

    async def disconnect(self) -> None:
        """Disconnect from CGIL."""
        await self._generic_union_disconnect()

    async def test_connection(self) -> bool:
        """Test CGIL connection."""
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        """Search CGIL documents."""
        return await self._generic_union_search(query, self._build_cgil_search_urls(query))

    async def get_document_content(self, document_id: str) -> str | None:
        """Get CGIL document content."""
        return await self._generic_get_content(document_id)

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Get latest CGIL updates."""
        return await self._generic_get_latest_updates(since)

    def _build_cgil_search_urls(self, query: DataSourceQuery) -> list[str]:
        """Build CGIL-specific search URLs."""
        urls = []

        # Main CCNL section
        urls.append(f"{self.source_info.base_url}/contrattazione")

        # Sector-specific unions
        if query.sectors:
            for sector in query.sectors:
                if sector in self.sector_unions:
                    for union in self.sector_unions[sector]:
                        union_name = union.lower().replace("-cgil", "")
                        urls.append(f"{self.source_info.base_url}/{union_name}")

        return urls


class CISLDataSource(BaseDataSource):
    """CISL (Confederazione Italiana Sindacati Lavoratori) data source."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="cisl_union",
            name="CISL - Confederazione Italiana Sindacati Lavoratori",
            organization="CISL",
            source_type=DataSourceType.UNION,
            base_url="https://www.cisl.it",
            description="Major Italian trade union confederation with moderate approach",
            supported_sectors=list(CCNLSector),
            update_frequency=UpdateFrequency.DAILY,
            reliability_score=0.88,
            api_key_required=False,
            rate_limit=200,
            contact_info="info@cisl.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None
        self.sector_unions = {
            CCNLSector.METALMECCANICI_INDUSTRIA: ["FIM-CISL"],
            CCNLSector.EDILIZIA_INDUSTRIA: ["FILCA-CISL"],
            CCNLSector.COMMERCIO_TERZIARIO: ["FISASCAT-CISL"],
            CCNLSector.TRASPORTI_LOGISTICA: ["FIT-CISL"],
            CCNLSector.SANITA_PRIVATA: ["FPS-CISL"],
            CCNLSector.PUBBLICI_ESERCIZI: ["FISASCAT-CISL"],
            CCNLSector.AGRICOLTURA: ["FAI-CISL"],
            CCNLSector.CHIMICI_FARMACEUTICI: ["FEMCA-CISL"],
            CCNLSector.CREDITO_ASSICURAZIONI: ["FIRST-CISL"],
        }

    async def connect(self) -> bool:
        return await self._generic_union_connect()

    async def disconnect(self) -> None:
        await self._generic_union_disconnect()

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        return await self._generic_union_search(query, self._build_cisl_search_urls(query))

    async def get_document_content(self, document_id: str) -> str | None:
        return await self._generic_get_content(document_id)

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        return await self._generic_get_latest_updates(since)

    def _build_cisl_search_urls(self, query: DataSourceQuery) -> list[str]:
        urls = [f"{self.source_info.base_url}/contrattazione"]

        if query.sectors:
            for sector in query.sectors:
                if sector in self.sector_unions:
                    for union in self.sector_unions[sector]:
                        union_name = union.lower().replace("-cisl", "")
                        urls.append(f"{self.source_info.base_url}/{union_name}")

        return urls


class UILDataSource(BaseDataSource):
    """UIL (Unione Italiana del Lavoro) data source."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="uil_union",
            name="UIL - Unione Italiana del Lavoro",
            organization="UIL",
            source_type=DataSourceType.UNION,
            base_url="https://www.uil.it",
            description="Third largest Italian trade union confederation",
            supported_sectors=list(CCNLSector),
            update_frequency=UpdateFrequency.DAILY,
            reliability_score=0.85,
            api_key_required=False,
            rate_limit=200,
            contact_info="info@uil.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None
        self.sector_unions = {
            CCNLSector.METALMECCANICI_INDUSTRIA: ["UILM-UIL"],
            CCNLSector.TRASPORTI_LOGISTICA: ["UILTRASPORTI"],
            CCNLSector.COMMERCIO_TERZIARIO: ["UILTUCS"],
            CCNLSector.EDILIZIA_INDUSTRIA: ["UILA"],
            CCNLSector.SANITA_PRIVATA: ["UIL-FPL"],
            CCNLSector.CHIMICI_FARMACEUTICI: ["UILTEC"],
            CCNLSector.ICT: ["UILCOM"],
        }

    async def connect(self) -> bool:
        return await self._generic_union_connect()

    async def disconnect(self) -> None:
        await self._generic_union_disconnect()

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        return await self._generic_union_search(query, self._build_uil_search_urls(query))

    async def get_document_content(self, document_id: str) -> str | None:
        return await self._generic_get_content(document_id)

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        return await self._generic_get_latest_updates(since)

    def _build_uil_search_urls(self, query: DataSourceQuery) -> list[str]:
        urls = [f"{self.source_info.base_url}/contrattazione"]

        if query.sectors:
            for sector in query.sectors:
                if sector in self.sector_unions:
                    for union in self.sector_unions[sector]:
                        union_name = union.lower().replace("-uil", "").replace("uil", "")
                        urls.append(f"{self.source_info.base_url}/{union_name}")

        return urls


class UGLDataSource(BaseDataSource):
    """UGL (Unione Generale del Lavoro) data source."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="ugl_union",
            name="UGL - Unione Generale del Lavoro",
            organization="UGL",
            source_type=DataSourceType.UNION,
            base_url="https://www.ugl.it",
            description="Fourth largest Italian trade union confederation",
            supported_sectors=list(CCNLSector),
            update_frequency=UpdateFrequency.DAILY,
            reliability_score=0.82,
            api_key_required=False,
            rate_limit=150,
            contact_info="info@ugl.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        return await self._generic_union_connect()

    async def disconnect(self) -> None:
        await self._generic_union_disconnect()

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        urls = [f"{self.source_info.base_url}/contrattazione"]
        return await self._generic_union_search(query, urls)

    async def get_document_content(self, document_id: str) -> str | None:
        return await self._generic_get_content(document_id)

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        return await self._generic_get_latest_updates(since)


# Mixin class with common union functionality
class UnionSourceMixin:
    """Common functionality for union data sources."""

    async def _generic_union_connect(self) -> bool:
        """Generic connection method for unions."""
        try:
            if hasattr(self, "session") and self.session and not self.session.closed:
                await self.session.close()

            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "PratikoAI-CCNL-Research/1.0 (Labor Relations Research)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                },
            )

            async with self.session.get(self.source_info.base_url) as response:
                if response.status == 200:
                    self.source_info.status = DataSourceStatus.ACTIVE
                    self.source_info.last_updated = datetime.utcnow()
                    logger.info(f"Connected to {self.source_info.source_id}")
                    return True
                else:
                    self.source_info.status = DataSourceStatus.ERROR
                    return False

        except Exception as e:
            self.source_info.status = DataSourceStatus.ERROR
            logger.error(f"Error connecting to {self.source_info.source_id}: {str(e)}")
            return False

    async def _generic_union_disconnect(self) -> None:
        """Generic disconnect method."""
        if hasattr(self, "session") and self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE

    async def _generic_test_connection(self) -> bool:
        """Generic connection test."""
        if not hasattr(self, "session") or not self.session or self.session.closed:
            return await self._generic_union_connect()

        try:
            async with self.session.get(self.source_info.base_url, timeout=10) as response:
                return response.status == 200
        except Exception:
            return False

    async def _generic_union_search(self, query: DataSourceQuery, search_urls: list[str]) -> list[CCNLDocument]:
        """Generic search method for unions."""
        if not await self.check_rate_limit():
            return []

        documents = []

        try:
            for url in search_urls[:5]:  # Limit URLs to avoid overload
                docs = await self._search_union_url(url, query)
                documents.extend(docs)

                # Small delay between requests
                await asyncio.sleep(0.5)

            await self.record_request()

            # Remove duplicates and sort
            documents = self._deduplicate_union_documents(documents)

            return documents[: query.max_results]

        except Exception as e:
            logger.error(f"Error searching {self.source_info.source_id}: {str(e)}")
            return []

    async def _search_union_url(self, url: str, query: DataSourceQuery) -> list[CCNLDocument]:
        """Search a specific union URL."""
        documents = []

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Find contract-related links
                contract_patterns = [re.compile(r"contratto|ccnl|accordo|rinnovo", re.I), re.compile(r"\.pdf$", re.I)]

                for pattern in contract_patterns:
                    links = soup.find_all("a", href=pattern)
                    for link in links[:20]:  # Limit per pattern
                        doc = await self._extract_union_document(link, url, query)
                        if doc:
                            documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Error searching union URL {url}: {str(e)}")
            return []

    async def _extract_union_document(
        self, link_element, base_url: str, query: DataSourceQuery
    ) -> CCNLDocument | None:
        """Extract document from union link."""
        try:
            href = link_element.get("href", "")
            title = link_element.get_text(strip=True)

            if not href or not title:
                return None

            # Make absolute URL
            if href.startswith("/"):
                full_url = self.source_info.base_url + href
            elif not href.startswith("http"):
                full_url = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
            else:
                full_url = href

            # Generate document ID
            document_id = f"{self.source_info.source_id}_{hashlib.md5(full_url.encode()).hexdigest()}"

            # Detect sector
            sector = self._detect_union_sector(title, base_url)

            # Skip if sector doesn't match query
            if query.sectors and sector not in query.sectors:
                return None

            # Detect document type
            doc_type = self._detect_union_document_type(title, href)

            # Extract date
            pub_date = self._extract_union_date(title) or date.today()

            # Generate content hash
            content_hash = hashlib.md5(f"{title}{full_url}".encode()).hexdigest()

            return CCNLDocument(
                document_id=document_id,
                source_id=self.source_info.source_id,
                title=title,
                sector=sector,
                publication_date=pub_date,
                effective_date=pub_date,
                expiry_date=None,
                document_type=doc_type,
                url=full_url,
                content_hash=content_hash,
                confidence_score=0.75,  # Good confidence for union sources
            )

        except Exception as e:
            logger.error(f"Error extracting union document: {str(e)}")
            return None

    async def _generic_get_content(self, document_id: str) -> str | None:
        """Generic content retrieval."""
        if not await self.check_rate_limit():
            return None

        try:
            # Extract URL from document ID
            parts = document_id.split("_", 1)
            if len(parts) == 2 and parts[0] == self.source_info.source_id:
                # This is a simplified approach - in reality, would need URL mapping
                logger.info(f"Would retrieve content for document {document_id}")
                await self.record_request()
                return "Content retrieval not fully implemented for union sources"

            return None

        except Exception as e:
            logger.error(f"Error retrieving content from {self.source_info.source_id}: {str(e)}")
            return None

    async def _generic_get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Generic latest updates retrieval."""
        if not since:
            since = datetime.utcnow() - timedelta(days=30)

        # Create query for recent documents
        query = DataSourceQuery(date_from=since.date(), max_results=20, document_types=["agreement", "renewal"])

        return await self.search_documents(query)

    def _detect_union_sector(self, title: str, url: str) -> CCNLSector:
        """Detect sector from union document."""
        title_lower = title.lower()
        url_lower = url.lower()

        # Sector keywords mapping
        sector_keywords = {
            CCNLSector.METALMECCANICI_INDUSTRIA: ["metalmeccanic", "meccanica", "industria", "fiom", "fim", "uilm"],
            CCNLSector.COMMERCIO_TERZIARIO: ["commercio", "terziario", "filcams", "fisascat", "uiltucs"],
            CCNLSector.EDILIZIA_INDUSTRIA: ["edilizia", "costruzioni", "fillea", "filca", "uila"],
            CCNLSector.TRASPORTI_LOGISTICA: ["trasporti", "logistica", "filt", "fit", "uiltrasporti"],
            CCNLSector.SANITA_PRIVATA: ["sanità", "sanitario", "fp-cgil", "fps-cisl", "uil-fpl"],
            CCNLSector.CHIMICI_FARMACEUTICI: ["chimici", "farmaceutici", "filctem", "femca", "uiltec"],
            CCNLSector.AGRICOLTURA: ["agricoltura", "agricol", "flai", "fai", "uila"],
            CCNLSector.ICT: ["informatica", "tecnologia", "ict", "telecomunicazioni", "uilcom"],
        }

        for sector, keywords in sector_keywords.items():
            if any(keyword in title_lower or keyword in url_lower for keyword in keywords):
                return sector

        return CCNLSector.COMMERCIO_TERZIARIO  # Default

    def _detect_union_document_type(self, title: str, url: str) -> str:
        """Detect document type from union source."""
        title_lower = title.lower()

        if "rinnovo" in title_lower:
            return "renewal"
        elif any(term in title_lower for term in ["contratto", "ccnl", "accordo"]):
            return "agreement"
        elif "verbale" in title_lower:
            return "meeting_minutes"
        elif "comunicato" in title_lower:
            return "statement"
        else:
            return "document"

    def _extract_union_date(self, title: str) -> date | None:
        """Extract date from union document title."""
        # Look for date patterns
        patterns = [
            r"(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})",
            r"(\d{4})",  # Just year
        ]

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:  # Day/month/year
                        day, month, year = groups
                        return date(int(year), int(month), int(day))
                    elif len(groups) == 1:  # Just year
                        year = groups[0]
                        return date(int(year), 1, 1)
                except ValueError:
                    continue

        return None

    def _deduplicate_union_documents(self, documents: list[CCNLDocument]) -> list[CCNLDocument]:
        """Remove duplicate documents from union searches."""
        seen_hashes = set()
        unique_docs = []

        for doc in documents:
            if doc.content_hash not in seen_hashes:
                seen_hashes.add(doc.content_hash)
                unique_docs.append(doc)

        # Sort by date (newest first)
        unique_docs.sort(key=lambda x: x.publication_date, reverse=True)

        return unique_docs


# Apply mixin to all union classes
for union_class in [CGILDataSource, CISLDataSource, UILDataSource, UGLDataSource]:
    # Add mixin methods to union classes
    for method_name, method in UnionSourceMixin.__dict__.items():
        if callable(method) and not method_name.startswith("_"):
            continue
        if (
            method_name.startswith("_generic")
            or method_name.startswith("_detect")
            or method_name.startswith("_extract")
            or method_name.startswith("_deduplicate")
        ):
            setattr(union_class, method_name, method)
