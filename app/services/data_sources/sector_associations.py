"""Sector-Specific Associations Data Sources Integration.

This module integrates with Italian sector-specific labor associations that provide
specialized CCNL information for their respective industries. These associations
complement the broader union and employer confederations with detailed,
industry-focused labor agreement data.
"""

import asyncio
import hashlib
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set

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


class FedermeccanicaDataSource(BaseDataSource):
    """Federmeccanica - Italian Metalworking Industries Federation."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="federmeccanica",
            name="Federmeccanica - Federazione Sindacale dell'Industria Metalmeccanica Italiana",
            organization="Federmeccanica",
            source_type=DataSourceType.SECTOR_ASSOCIATION,
            base_url="https://www.federmeccanica.it",
            description="Italian metalworking industries federation - authoritative source for metal-mechanical CCNLs",
            supported_sectors=[CCNLSector.METALMECCANICI_INDUSTRIA, CCNLSector.METALMECCANICI_ARTIGIANI],
            update_frequency=UpdateFrequency.WEEKLY,
            reliability_score=0.95,  # High reliability for authoritative source
            api_key_required=False,
            rate_limit=100,
            contact_info="info@federmeccanica.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        """Connect to Federmeccanica data source."""
        try:
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=30)
                headers = {
                    "User-Agent": "PratikoAI CCNL Integration Bot/1.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

            # Test connection with the main page
            async with self.session.get(f"{self.source_info.base_url}/contrattazione") as response:
                if response.status == 200:
                    self.source_info.status = DataSourceStatus.ACTIVE
                    self.source_info.last_updated = datetime.now()
                    logger.info("Successfully connected to Federmeccanica data source")
                    return True

        except Exception as e:
            logger.error(f"Failed to connect to Federmeccanica: {e}")
            self.source_info.status = DataSourceStatus.ERROR

        return False

    async def disconnect(self) -> None:
        """Disconnect from Federmeccanica data source."""
        if self.session:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE

    async def test_connection(self) -> bool:
        """Test connection to Federmeccanica."""
        if not self.session:
            return await self.connect()

        try:
            async with self.session.get(self.source_info.base_url) as response:
                return response.status == 200
        except Exception:
            return False

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        """Search for CCNL documents from Federmeccanica."""
        if not await self.test_connection():
            return []

        documents = []

        # Filter query for supported sectors only
        relevant_sectors = [
            sector
            for sector in (query.sectors or self.source_info.supported_sectors)
            if sector in self.source_info.supported_sectors
        ]

        if not relevant_sectors:
            return []

        try:
            # Search for metalworking CCNLs
            search_urls = [
                f"{self.source_info.base_url}/contrattazione/ccnl",
                f"{self.source_info.base_url}/relazioni-industriali/contratti",
            ]

            for url in search_urls:
                docs = await self._scrape_federmeccanica_documents(url, query, relevant_sectors)
                documents.extend(docs)

        except Exception as e:
            logger.error(f"Error searching Federmeccanica documents: {e}")

        return documents

    async def _scrape_federmeccanica_documents(
        self, url: str, query: DataSourceQuery, sectors: list[CCNLSector]
    ) -> list[CCNLDocument]:
        """Scrape documents from Federmeccanica pages."""
        documents = []

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents

                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")

                # Look for CCNL links and document metadata
                ccnl_links = soup.find_all(["a", "div"], class_=re.compile(r"ccnl|contract|documento"))

                for link in ccnl_links:
                    doc = await self._extract_federmeccanica_document(link, url, sectors)
                    if doc:
                        documents.append(doc)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

        return documents[: query.max_results]

    async def _extract_federmeccanica_document(
        self, element, base_url: str, sectors: list[CCNLSector]
    ) -> CCNLDocument | None:
        """Extract document information from HTML element."""
        try:
            # Extract basic document information
            title_elem = element.find("h3") or element.find("h2") or element
            title = title_elem.get_text(strip=True) if title_elem else ""

            if not title or not any(keyword in title.lower() for keyword in ["ccnl", "metalmeccanico", "contratto"]):
                return None

            # Extract document URL
            link = element.get("href") or element.find("a", href=True)
            if isinstance(link, str):
                doc_url = link if link.startswith("http") else f"{self.source_info.base_url}{link}"
            else:
                doc_url = base_url

            # Determine sector based on title content
            sector = self._determine_sector_from_title(title)
            if sector not in sectors:
                return None

            # Generate document ID
            doc_id = hashlib.sha256(f"{self.source_info.source_id}_{doc_url}_{title}".encode()).hexdigest()[:16]

            # Extract dates (try to parse from title or use defaults)
            pub_date = self._extract_date_from_title(title) or date.today()
            effective_date = pub_date

            return CCNLDocument(
                document_id=doc_id,
                source_id=self.source_info.source_id,
                title=title,
                sector=sector,
                publication_date=pub_date,
                effective_date=effective_date,
                expiry_date=None,
                document_type="agreement",
                url=doc_url,
                content_hash=hashlib.sha256(title.encode()).hexdigest()[:16],
                confidence_score=0.85,  # High confidence for authoritative source
            )

        except Exception as e:
            logger.error(f"Error extracting document: {e}")
            return None

    def _determine_sector_from_title(self, title: str) -> CCNLSector:
        """Determine CCNL sector from document title."""
        title_lower = title.lower()

        if any(keyword in title_lower for keyword in ["artigian", "piccole"]):
            return CCNLSector.METALMECCANICI_ARTIGIANI
        else:
            return CCNLSector.METALMECCANICI_INDUSTRIA

    def _extract_date_from_title(self, title: str) -> date | None:
        """Extract date from document title."""
        # Look for date patterns in title
        date_patterns = [
            r"(\d{1,2})/(\d{1,2})/(\d{4})",  # DD/MM/YYYY
            r"(\d{4})-(\d{2})-(\d{2})",  # YYYY-MM-DD
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",  # DD.MM.YYYY
        ]

        for pattern in date_patterns:
            match = re.search(pattern, title)
            if match:
                try:
                    if "/" in pattern or "\\." in pattern:  # DD/MM/YYYY or DD.MM.YYYY
                        day, month, year = match.groups()
                        return date(int(year), int(month), int(day))
                    else:  # YYYY-MM-DD
                        year, month, day = match.groups()
                        return date(int(year), int(month), int(day))
                except ValueError:
                    continue

        return None

    async def get_document_content(self, document_id: str) -> str | None:
        """Retrieve the full content of a specific document."""
        try:
            # For now, return None as we'd need to implement document-specific retrieval
            # In a full implementation, this would fetch the document content by ID
            logger.info(f"Document content retrieval not implemented for {self.source_info.source_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving document content: {e}")
            return None

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Get documents updated since the specified time."""
        try:
            # Create a query for recent updates
            query = DataSourceQuery(
                sectors=self.source_info.supported_sectors,
                date_from=since.date() if since else date.today() - timedelta(days=30),
                max_results=20,
            )

            # Use regular search for now - in a full implementation this would be optimized
            return await self.search_documents(query)
        except Exception as e:
            logger.error(f"Error getting latest updates: {e}")
            return []


class FederchimicaDataSource(BaseDataSource):
    """Federchimica - Italian Chemical Industries Federation."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="federchimica",
            name="Federchimica - Federazione Nazionale dell'Industria Chimica",
            organization="Federchimica",
            source_type=DataSourceType.SECTOR_ASSOCIATION,
            base_url="https://www.federchimica.it",
            description="Italian chemical industries federation - authoritative source for chemical sector CCNLs",
            supported_sectors=[CCNLSector.CHIMICI_FARMACEUTICI, CCNLSector.GOMMA_PLASTICA],
            update_frequency=UpdateFrequency.WEEKLY,
            reliability_score=0.93,
            api_key_required=False,
            rate_limit=100,
            contact_info="info@federchimica.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        """Connect to Federchimica data source."""
        return await self._generic_sector_connect("contratti-collettivi")

    async def disconnect(self) -> None:
        """Disconnect from Federchimica data source."""
        if self.session:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE

    async def test_connection(self) -> bool:
        """Test connection to Federchimica."""
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        """Search for CCNL documents from Federchimica."""
        return await self._generic_sector_search(query, ["contratti", "chimici", "farmaceutici", "gomma", "plastica"])

    async def _generic_sector_connect(self, endpoint: str) -> bool:
        """Generic connection method for sector associations."""
        try:
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=30)
                headers = {
                    "User-Agent": "PratikoAI CCNL Integration Bot/1.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

            test_url = f"{self.source_info.base_url}/{endpoint}" if endpoint else self.source_info.base_url
            async with self.session.get(test_url) as response:
                if response.status == 200:
                    self.source_info.status = DataSourceStatus.ACTIVE
                    self.source_info.last_updated = datetime.now()
                    logger.info(f"Successfully connected to {self.source_info.name}")
                    return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.source_info.name}: {e}")
            self.source_info.status = DataSourceStatus.ERROR

        return False

    async def _generic_test_connection(self) -> bool:
        """Generic connection test."""
        if not self.session:
            return await self.connect()

        try:
            async with self.session.get(self.source_info.base_url) as response:
                return response.status == 200
        except Exception:
            return False

    async def _generic_sector_search(self, query: DataSourceQuery, keywords: list[str]) -> list[CCNLDocument]:
        """Generic search method for sector associations."""
        if not await self.test_connection():
            return []

        documents = []
        relevant_sectors = [
            sector
            for sector in (query.sectors or self.source_info.supported_sectors)
            if sector in self.source_info.supported_sectors
        ]

        if not relevant_sectors:
            return []

        try:
            # Generic search endpoints
            search_urls = [
                f"{self.source_info.base_url}/contratti",
                f"{self.source_info.base_url}/contratti-collettivi",
                f"{self.source_info.base_url}/ccnl",
                f"{self.source_info.base_url}/relazioni-industriali",
            ]

            for url in search_urls:
                docs = await self._scrape_generic_documents(url, query, relevant_sectors, keywords)
                documents.extend(docs)

        except Exception as e:
            logger.error(f"Error searching {self.source_info.name} documents: {e}")

        return documents[: query.max_results]

    async def get_document_content(self, document_id: str) -> str | None:
        """Retrieve the full content of a specific document."""
        try:
            logger.info(f"Document content retrieval not implemented for {self.source_info.source_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving document content: {e}")
            return None

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Get documents updated since the specified time."""
        try:
            query = DataSourceQuery(
                sectors=self.source_info.supported_sectors,
                date_from=since.date() if since else date.today() - timedelta(days=30),
                max_results=20,
            )
            return await self.search_documents(query)
        except Exception as e:
            logger.error(f"Error getting latest updates: {e}")
            return []

    async def _scrape_generic_documents(
        self, url: str, query: DataSourceQuery, sectors: list[CCNLSector], keywords: list[str]
    ) -> list[CCNLDocument]:
        """Generic document scraping method."""
        documents = []

        try:
            async with self.session.get(url) as response:
                if response.status == 404:
                    return documents  # Skip non-existent endpoints
                if response.status != 200:
                    return documents

                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")

                # Look for document links
                links = soup.find_all("a", href=True)
                for link in links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True).lower()

                    # Check if link is relevant based on keywords
                    if any(keyword in text or keyword in href.lower() for keyword in keywords):
                        doc = await self._create_generic_document(link, url, sectors)
                        if doc:
                            documents.append(doc)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")

        return documents

    async def _create_generic_document(self, link, base_url: str, sectors: list[CCNLSector]) -> CCNLDocument | None:
        """Create a generic CCNL document from link."""
        try:
            title = link.get_text(strip=True)
            href = link.get("href", "")

            if not title or len(title) < 5:
                return None

            # Determine document URL
            if href.startswith("http"):
                doc_url = href
            elif href.startswith("/"):
                doc_url = f"{self.source_info.base_url}{href}"
            else:
                doc_url = f"{base_url}/{href}"

            # Determine sector (use first supported sector as default)
            sector = sectors[0] if sectors else self.source_info.supported_sectors[0]

            # Generate document ID
            doc_id = hashlib.sha256(f"{self.source_info.source_id}_{doc_url}".encode()).hexdigest()[:16]

            return CCNLDocument(
                document_id=doc_id,
                source_id=self.source_info.source_id,
                title=title,
                sector=sector,
                publication_date=date.today(),
                effective_date=date.today(),
                expiry_date=None,
                document_type="agreement",
                url=doc_url,
                content_hash=hashlib.sha256(title.encode()).hexdigest()[:16],
                confidence_score=0.80,
            )

        except Exception as e:
            logger.error(f"Error creating document: {e}")
            return None


class FederalimentareDataSource(BaseDataSource):
    """Federalimentare - Italian Food Industries Federation."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="federalimentare",
            name="Federalimentare - Federazione Italiana dell'Industria Alimentare",
            organization="Federalimentare",
            source_type=DataSourceType.SECTOR_ASSOCIATION,
            base_url="https://www.federalimentare.it",
            description="Italian food industries federation - authoritative source for food sector CCNLs",
            supported_sectors=[CCNLSector.ALIMENTARI_INDUSTRIA, CCNLSector.PANIFICAZIONE],
            update_frequency=UpdateFrequency.WEEKLY,
            reliability_score=0.91,
            api_key_required=False,
            rate_limit=100,
            contact_info="info@federalimentare.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        return await self._generic_sector_connect("relazioni-industriali")

    async def disconnect(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        return await self._generic_sector_search(query, ["alimentare", "panificazione", "ccnl", "contratti"])

    # Inherit generic methods from FederchimicaDataSource
    async def _generic_sector_connect(self, endpoint: str) -> bool:
        federchimica_instance = FederchimicaDataSource()
        federchimica_instance.source_info = self.source_info
        federchimica_instance.session = self.session
        result = await federchimica_instance._generic_sector_connect(endpoint)
        self.session = federchimica_instance.session
        return result

    async def _generic_test_connection(self) -> bool:
        federchimica_instance = FederchimicaDataSource()
        federchimica_instance.source_info = self.source_info
        federchimica_instance.session = self.session
        return await federchimica_instance._generic_test_connection()

    async def _generic_sector_search(self, query: DataSourceQuery, keywords: list[str]) -> list[CCNLDocument]:
        federchimica_instance = FederchimicaDataSource()
        federchimica_instance.source_info = self.source_info
        federchimica_instance.session = self.session
        result = await federchimica_instance._generic_sector_search(query, keywords)
        self.session = federchimica_instance.session
        return result

    async def get_document_content(self, document_id: str) -> str | None:
        """Retrieve the full content of a specific document."""
        try:
            logger.info(f"Document content retrieval not implemented for {self.source_info.source_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving document content: {e}")
            return None

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Get documents updated since the specified time."""
        try:
            query = DataSourceQuery(
                sectors=self.source_info.supported_sectors,
                date_from=since.date() if since else date.today() - timedelta(days=30),
                max_results=20,
            )
            return await self.search_documents(query)
        except Exception as e:
            logger.error(f"Error getting latest updates: {e}")
            return []


class ASSINFORMDataSource(BaseDataSource):
    """ASSINFORM - Italian ICT Industries Association."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="assinform",
            name="ASSINFORM - Associazione per l'Information & Communication Technology",
            organization="ASSINFORM",
            source_type=DataSourceType.SECTOR_ASSOCIATION,
            base_url="https://www.assinform.it",
            description="Italian ICT industries association - specialized ICT sector labor agreements",
            supported_sectors=[CCNLSector.ICT, CCNLSector.TELECOMUNICAZIONI],
            update_frequency=UpdateFrequency.MONTHLY,
            reliability_score=0.87,
            api_key_required=False,
            rate_limit=80,
            contact_info="info@assinform.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        return await self._generic_sector_connect("lavoro")

    async def disconnect(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        return await self._generic_sector_search(query, ["ict", "telecomunicazioni", "informatica", "tecnologia"])

    # Inherit generic methods
    async def _generic_sector_connect(self, endpoint: str) -> bool:
        federchimica_instance = FederchimicaDataSource()
        federchimica_instance.source_info = self.source_info
        federchimica_instance.session = self.session
        result = await federchimica_instance._generic_sector_connect(endpoint)
        self.session = federchimica_instance.session
        return result

    async def _generic_test_connection(self) -> bool:
        federchimica_instance = FederchimicaDataSource()
        federchimica_instance.source_info = self.source_info
        federchimica_instance.session = self.session
        return await federchimica_instance._generic_test_connection()

    async def _generic_sector_search(self, query: DataSourceQuery, keywords: list[str]) -> list[CCNLDocument]:
        federchimica_instance = FederchimicaDataSource()
        federchimica_instance.source_info = self.source_info
        federchimica_instance.session = self.session
        result = await federchimica_instance._generic_sector_search(query, keywords)
        self.session = federchimica_instance.session
        return result

    async def get_document_content(self, document_id: str) -> str | None:
        """Retrieve the full content of a specific document."""
        try:
            logger.info(f"Document content retrieval not implemented for {self.source_info.source_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving document content: {e}")
            return None

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Get documents updated since the specified time."""
        try:
            query = DataSourceQuery(
                sectors=self.source_info.supported_sectors,
                date_from=since.date() if since else date.today() - timedelta(days=30),
                max_results=20,
            )
            return await self.search_documents(query)
        except Exception as e:
            logger.error(f"Error getting latest updates: {e}")
            return []


class ASSOMARMIDataSource(BaseDataSource):
    """ASSOMARMI - Italian Stone/Marble Industries Association."""

    def __init__(self):
        source_info = DataSourceInfo(
            source_id="assomarmi",
            name="ASSOMARMI - Associazione Nazionale degli Industriali Marmisti",
            organization="ASSOMARMI",
            source_type=DataSourceType.SECTOR_ASSOCIATION,
            base_url="https://www.assomarmi.it",
            description="Italian stone and marble industries association",
            supported_sectors=[CCNLSector.EDILIZIA_INDUSTRIA, CCNLSector.EDILIZIA_ARTIGIANATO],
            update_frequency=UpdateFrequency.MONTHLY,
            reliability_score=0.85,
            api_key_required=False,
            rate_limit=60,
            contact_info="info@assomarmi.it",
        )
        super().__init__(source_info)
        self.session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        return await self._generic_sector_connect("")

    async def disconnect(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE

    async def test_connection(self) -> bool:
        return await self._generic_test_connection()

    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        return await self._generic_sector_search(query, ["edilizia", "marmi", "pietre", "costruzioni"])

    # Inherit generic methods
    async def _generic_sector_connect(self, endpoint: str) -> bool:
        federchimica_instance = FederchimicaDataSource()
        federchimica_instance.source_info = self.source_info
        federchimica_instance.session = self.session
        result = await federchimica_instance._generic_sector_connect(endpoint)
        self.session = federchimica_instance.session
        return result

    async def _generic_test_connection(self) -> bool:
        federchimica_instance = FederchimicaDataSource()
        federchimica_instance.source_info = self.source_info
        federchimica_instance.session = self.session
        return await federchimica_instance._generic_test_connection()

    async def _generic_sector_search(self, query: DataSourceQuery, keywords: list[str]) -> list[CCNLDocument]:
        federchimica_instance = FederchimicaDataSource()
        federchimica_instance.source_info = self.source_info
        federchimica_instance.session = self.session
        result = await federchimica_instance._generic_sector_search(query, keywords)
        self.session = federchimica_instance.session
        return result

    async def get_document_content(self, document_id: str) -> str | None:
        """Retrieve the full content of a specific document."""
        try:
            logger.info(f"Document content retrieval not implemented for {self.source_info.source_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving document content: {e}")
            return None

    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Get documents updated since the specified time."""
        try:
            query = DataSourceQuery(
                sectors=self.source_info.supported_sectors,
                date_from=since.date() if since else date.today() - timedelta(days=30),
                max_results=20,
            )
            return await self.search_documents(query)
        except Exception as e:
            logger.error(f"Error getting latest updates: {e}")
            return []


# Sector associations registry
SECTOR_ASSOCIATIONS = {
    "federmeccanica": FedermeccanicaDataSource,
    "federchimica": FederchimicaDataSource,
    "federalimentare": FederalimentareDataSource,
    "assinform": ASSINFORMDataSource,
    "assomarmi": ASSOMARMIDataSource,
}


async def get_all_sector_associations() -> list[BaseDataSource]:
    """Get all available sector association data sources."""
    sources = []
    for source_class in SECTOR_ASSOCIATIONS.values():
        try:
            source = source_class()
            sources.append(source)
        except Exception as e:
            logger.error(f"Error initializing sector association {source_class.__name__}: {e}")
    return sources


async def get_sector_associations_for_sectors(sectors: list[CCNLSector]) -> list[BaseDataSource]:
    """Get sector associations that support the specified sectors."""
    all_sources = await get_all_sector_associations()
    relevant_sources = []

    for source in all_sources:
        if any(sector in source.source_info.supported_sectors for sector in sectors):
            relevant_sources.append(source)

    return relevant_sources
