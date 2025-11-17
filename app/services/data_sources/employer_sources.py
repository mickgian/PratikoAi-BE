"""Employer Associations Data Sources Integration.

This module integrates with major Italian employer associations:
- Confindustria (Confederazione Generale dell'Industria Italiana)
- Confcommercio (Confederazione Generale Italiana delle Imprese)
- Confartigianato (Confederazione Generale dell'Artigianato Italiano)
- Confapi (Confederazione Italiana della Piccola e Media Industria)
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


class ConfindustriaDataSource(BaseDataSource):
    """Confindustria (General Confederation of Italian Industry) data source."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="confindustria",
            name="Confindustria - Confederazione Generale dell'Industria Italiana",
            organization="Confindustria",
            source_type=DataSourceType.EMPLOYER_ASSOCIATION,
            base_url="https://www.confindustria.it",
            description="Main Italian employers' confederation representing industry",
            supported_sectors=[
                CCNLSector.METALMECCANICI_INDUSTRIA,
                CCNLSector.CHIMICI_FARMACEUTICI,
                CCNLSector.TESSILI,
                CCNLSector.ALIMENTARI_INDUSTRIA,
                CCNLSector.ENERGIA_PETROLIO,
                CCNLSector.CARTA_GRAFICA,
                CCNLSector.GOMMA_PLASTICA,
                CCNLSector.VETRO,
            ],
            update_frequency=UpdateFrequency.WEEKLY,
            reliability_score=0.92,
            api_key_required=False,
            rate_limit=150,
            contact_info="segreteria@confindustria.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None
        self.sector_associations = {
            CCNLSector.METALMECCANICI_INDUSTRIA: "Federmeccanica",
            CCNLSector.CHIMICI_FARMACEUTICI: "Federchimica",
            CCNLSector.TESSILI: "SMI Sistema Moda Italia",
            CCNLSector.ALIMENTARI_INDUSTRIA: "Federalimentare",
            CCNLSector.ENERGIA_PETROLIO: "Unione Petrolifera",
            CCNLSector.CARTA_GRAFICA: "Assocarta",
            CCNLSector.GOMMA_PLASTICA: "Federchimica",
            CCNLSector.VETRO: "Assovetro",
        }

    async def connect(self) -> bool:
        return await self._generic_employer_connect()

    async def disconnect(self) -> None:
        await self._generic_employer_disconnect()

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        search_urls = self._build_confindustria_search_urls(query)
        return await self._generic_employer_search(query, search_urls)

    async def get_document_content(self, document_id: str) -> str | None:
        return await self._generic_get_content(document_id)

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        return await self._generic_get_latest_updates(since)

    def _build_confindustria_search_urls(self, query: DataSourceQuery) -> list[str]:
        """Build Confindustria-specific search URLs."""
        urls = [
            f"{self.source_info.base_url}/il-sistema/relazioni-industriali/contrattazione",
            f"{self.source_info.base_url}/documenti-e-schede-informative",
        ]

        # Add sector-specific associations
        if query.sectors:
            for sector in query.sectors:
                if sector in self.sector_associations:
                    association = self.sector_associations[sector]
                    urls.append(f"{self.source_info.base_url}/federazioni/{association.lower()}")

        return urls


class ConfcommercioDataSource(BaseDataSource):
    """Confcommercio (General Confederation of Italian Enterprises) data source."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="confcommercio",
            name="Confcommercio - Confederazione Generale Italiana delle Imprese",
            organization="Confcommercio",
            source_type=DataSourceType.EMPLOYER_ASSOCIATION,
            base_url="https://www.confcommercio.it",
            description="Italian confederation representing commerce, tourism, and services",
            supported_sectors=[
                CCNLSector.COMMERCIO_TERZIARIO,
                CCNLSector.TURISMO,
                CCNLSector.PUBBLICI_ESERCIZI,
                CCNLSector.AGENZIE_VIAGGIO,
                CCNLSector.POMPE_FUNEBRI,
                CCNLSector.AUTONOLEGGIO,
                CCNLSector.IMPIANTI_SPORTIVI,
            ],
            update_frequency=UpdateFrequency.WEEKLY,
            reliability_score=0.89,
            api_key_required=False,
            rate_limit=150,
            contact_info="info@confcommercio.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        return await self._generic_employer_connect()

    async def disconnect(self) -> None:
        await self._generic_employer_disconnect()

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        urls = [
            f"{self.source_info.base_url}/lavoro-e-contrattazione",
            f"{self.source_info.base_url}/normativa-e-contratti",
        ]
        return await self._generic_employer_search(query, urls)

    async def get_document_content(self, document_id: str) -> str | None:
        return await self._generic_get_content(document_id)

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        return await self._generic_get_latest_updates(since)


class ConfartigianatoDataSource(BaseDataSource):
    """Confartigianato (General Confederation of Italian Handicrafts) data source."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="confartigianato",
            name="Confartigianato - Confederazione Generale dell'Artigianato Italiano",
            organization="Confartigianato",
            source_type=DataSourceType.EMPLOYER_ASSOCIATION,
            base_url="https://www.confartigianato.it",
            description="Italian confederation representing artisan enterprises and SMEs",
            supported_sectors=[
                CCNLSector.METALMECCANICI_ARTIGIANI,
                CCNLSector.EDILIZIA_ARTIGIANATO,
                CCNLSector.LEGNO_ARREDAMENTO,
                CCNLSector.ACCONCIATURA_ESTETICA,
                CCNLSector.PANIFICAZIONE,
                CCNLSector.AUTORIMESSE,
                CCNLSector.AUTOTRASPORTO_MERCI,
            ],
            update_frequency=UpdateFrequency.WEEKLY,
            reliability_score=0.87,
            api_key_required=False,
            rate_limit=120,
            contact_info="info@confartigianato.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        return await self._generic_employer_connect()

    async def disconnect(self) -> None:
        await self._generic_employer_disconnect()

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        urls = [
            f"{self.source_info.base_url}/lavoro-e-previdenza",
            f"{self.source_info.base_url}/contratti-collettivi",
        ]
        return await self._generic_employer_search(query, urls)

    async def get_document_content(self, document_id: str) -> str | None:
        return await self._generic_get_content(document_id)

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        return await self._generic_get_latest_updates(since)


class ConfapiDataSource(BaseDataSource):
    """Confapi (Italian Confederation of Small and Medium Industry) data source."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="confapi",
            name="Confapi - Confederazione Italiana della Piccola e Media Industria",
            organization="Confapi",
            source_type=DataSourceType.EMPLOYER_ASSOCIATION,
            base_url="https://www.confapi.it",
            description="Italian confederation representing small and medium industrial enterprises",
            supported_sectors=[
                CCNLSector.METALMECCANICI_INDUSTRIA,
                CCNLSector.ICT,
                CCNLSector.SERVIZI_PULIZIA,
                CCNLSector.VIGILANZA_PRIVATA,
                CCNLSector.CALL_CENTER,
                CCNLSector.TELECOMUNICAZIONI,
            ],
            update_frequency=UpdateFrequency.WEEKLY,
            reliability_score=0.85,
            api_key_required=False,
            rate_limit=100,
            contact_info="segreteria@confapi.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        return await self._generic_employer_connect()

    async def disconnect(self) -> None:
        await self._generic_employer_disconnect()

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        urls = [
            f"{self.source_info.base_url}/relazioni-industriali",
            f"{self.source_info.base_url}/contrattazione-collettiva",
        ]
        return await self._generic_employer_search(query, urls)

    async def get_document_content(self, document_id: str) -> str | None:
        return await self._generic_get_content(document_id)

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        return await self._generic_get_latest_updates(since)


# Mixin class for employer associations
class EmployerSourceMixin:
    """Common functionality for employer association data sources."""

    async def _generic_employer_connect(self) -> bool:
        """Generic connection method for employer associations."""
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

    async def _generic_employer_disconnect(self) -> None:
        """Generic disconnect method."""
        if hasattr(self, "session") and self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE

    async def _generic_test_connection(self) -> bool:
        """Generic connection test."""
        if not hasattr(self, "session") or not self.session or self.session.closed:
            return await self._generic_employer_connect()

        try:
            async with self.session.get(self.source_info.base_url, timeout=10) as response:
                return response.status == 200
        except Exception:
            return False

    async def _generic_employer_search(self, query: DataSourceQuery, search_urls: list[str]) -> list[CCNLDocument]:
        """Generic search method for employer associations."""
        if not await self.check_rate_limit():
            return []

        documents = []

        try:
            for url in search_urls[:3]:  # Limit URLs
                docs = await self._search_employer_url(url, query)
                documents.extend(docs)
                await asyncio.sleep(0.5)  # Rate limiting

            await self.record_request()

            # Deduplicate and filter
            documents = self._deduplicate_employer_documents(documents, query)

            return documents[: query.max_results]

        except Exception as e:
            logger.error(f"Error searching {self.source_info.source_id}: {str(e)}")
            return []

    async def _search_employer_url(self, url: str, query: DataSourceQuery) -> list[CCNLDocument]:
        """Search a specific employer association URL."""
        documents = []

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Find CCNL-related links
                patterns = ["contratto", "ccnl", "accordo", "rinnovo", "contrattazione", "relazioni industriali"]

                for pattern in patterns:
                    links = soup.find_all("a", string=re.compile(pattern, re.I))
                    links.extend(soup.find_all("a", href=re.compile(pattern, re.I)))

                    for link in links[:15]:  # Limit per pattern
                        doc = await self._extract_employer_document(link, url, query)
                        if doc:
                            documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Error searching employer URL {url}: {str(e)}")
            return []

    async def _extract_employer_document(
        self, link_element, base_url: str, query: DataSourceQuery
    ) -> CCNLDocument | None:
        """Extract document from employer association link."""
        try:
            href = link_element.get("href", "")
            title = link_element.get_text(strip=True)

            if not href or not title or len(title) < 10:
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
            sector = self._detect_employer_sector(title, full_url)

            # Filter by sector if specified
            if query.sectors and sector not in query.sectors:
                return None

            # Detect document type
            doc_type = self._detect_employer_document_type(title, href)

            # Extract date
            pub_date = self._extract_employer_date(title) or date.today()

            # Filter by date if specified
            if query.date_from and pub_date < query.date_from:
                return None
            if query.date_to and pub_date > query.date_to:
                return None

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
                confidence_score=0.80,  # Good confidence for employer sources
            )

        except Exception as e:
            logger.error(f"Error extracting employer document: {str(e)}")
            return None

    async def _generic_get_content(self, document_id: str) -> str | None:
        """Generic content retrieval for employer sources."""
        if not await self.check_rate_limit():
            return None

        try:
            # Simplified content retrieval - in practice would need URL mapping
            logger.info(f"Would retrieve content for document {document_id}")
            await self.record_request()
            return f"Content retrieval placeholder for {document_id}"

        except Exception as e:
            logger.error(f"Error retrieving content: {str(e)}")
            return None

    async def _generic_get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Generic latest updates for employer sources."""
        if not since:
            since = datetime.utcnow() - timedelta(days=30)

        query = DataSourceQuery(
            date_from=since.date(), max_results=15, document_types=["agreement", "renewal", "amendment"]
        )

        return await self.search_documents(query)

    def _detect_employer_sector(self, title: str, url: str) -> CCNLSector:
        """Detect sector from employer document."""
        title_lower = title.lower()
        url_lower = url.lower()

        sector_keywords = {
            CCNLSector.METALMECCANICI_INDUSTRIA: ["metalmeccanic", "meccanica", "federmeccanica", "industria"],
            CCNLSector.COMMERCIO_TERZIARIO: ["commercio", "terziario", "confcommercio", "distribuzione"],
            CCNLSector.EDILIZIA_INDUSTRIA: ["edilizia", "costruzioni", "ance", "lavori pubblici"],
            CCNLSector.ICT: ["informatica", "tecnologia", "ict", "software", "telecomunicazioni"],
            CCNLSector.TURISMO: ["turismo", "alberghi", "federalberghi", "ristoranti"],
            CCNLSector.CHIMICI_FARMACEUTICI: ["chimici", "farmaceutici", "federchimica", "chimica"],
            CCNLSector.TESSILI: ["tessile", "moda", "sistema moda", "abbigliamento"],
            CCNLSector.ALIMENTARI_INDUSTRIA: ["alimentare", "federalimentare", "food", "bevande"],
            CCNLSector.ENERGIA_PETROLIO: ["energia", "petrolio", "petrolifera", "gas"],
            CCNLSector.AUTOTRASPORTO_MERCI: ["autotrasporto", "trasporti", "logistica", "spedizioni"],
        }

        for sector, keywords in sector_keywords.items():
            if any(keyword in title_lower or keyword in url_lower for keyword in keywords):
                # Check if sector is supported by this source
                if sector in self.source_info.supported_sectors:
                    return sector

        # Return first supported sector as default
        return (
            self.source_info.supported_sectors[0]
            if self.source_info.supported_sectors
            else CCNLSector.COMMERCIO_TERZIARIO
        )

    def _detect_employer_document_type(self, title: str, url: str) -> str:
        """Detect document type from employer source."""
        title_lower = title.lower()

        if any(term in title_lower for term in ["rinnovo", "rinnovato"]):
            return "renewal"
        elif any(term in title_lower for term in ["contratto", "ccnl", "accordo"]):
            return "agreement"
        elif any(term in title_lower for term in ["modifica", "integrazione", "revisione"]):
            return "amendment"
        elif any(term in title_lower for term in ["comunicato", "nota", "posizione"]):
            return "statement"
        elif "verbale" in title_lower:
            return "meeting_minutes"
        else:
            return "document"

    def _extract_employer_date(self, title: str) -> date | None:
        """Extract date from employer document title."""
        patterns = [
            r"(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})",  # dd/mm/yyyy
            r"(\d{4})[/\.-](\d{1,2})[/\.-](\d{1,2})",  # yyyy/mm/dd
            r"(\d{4})",  # Just year
        ]

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if int(groups[0]) > 31:  # First group is year
                            year, month, day = groups
                        else:  # First group is day
                            day, month, year = groups
                        return date(int(year), int(month), int(day))
                    elif len(groups) == 1:  # Just year
                        year = groups[0]
                        return date(int(year), 1, 1)
                except ValueError:
                    continue

        return None

    def _deduplicate_employer_documents(
        self, documents: list[CCNLDocument], query: DataSourceQuery
    ) -> list[CCNLDocument]:
        """Deduplicate employer documents."""
        seen_hashes = set()
        unique_docs = []

        for doc in documents:
            # Skip exact duplicates
            if doc.content_hash in seen_hashes:
                continue
            seen_hashes.add(doc.content_hash)

            # Skip documents that don't match keywords
            if query.keywords:
                title_lower = doc.title.lower()
                if not any(keyword.lower() in title_lower for keyword in query.keywords):
                    continue

            unique_docs.append(doc)

        # Sort by publication date (newest first)
        unique_docs.sort(key=lambda x: x.publication_date, reverse=True)

        return unique_docs


# Apply mixin to all employer classes
for employer_class in [ConfindustriaDataSource, ConfcommercioDataSource, ConfartigianatoDataSource, ConfapiDataSource]:
    for method_name, method in EmployerSourceMixin.__dict__.items():
        if callable(method) and (
            method_name.startswith("_generic")
            or method_name.startswith("_detect")
            or method_name.startswith("_extract")
            or method_name.startswith("_deduplicate")
            or method_name.startswith("_search")
        ):
            setattr(employer_class, method_name, method)
