"""
Ministry of Labor and Government Publications Data Sources.

This module integrates with official Italian government sources for CCNL data,
including the Ministry of Labor (Ministero del Lavoro), INPS, INAIL, and other
authoritative government agencies that publish labor agreement information.
"""

import asyncio
import hashlib
import re
import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import aiohttp
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, urlparse

from app.models.ccnl_data import CCNLSector
from .base_source import (
    BaseDataSource, DataSourceInfo, DataSourceType, DataSourceStatus,
    UpdateFrequency, CCNLDocument, DataSourceQuery
)

logger = logging.getLogger(__name__)


class MinistryOfLaborDataSource(BaseDataSource):
    """Ministry of Labor (Ministero del Lavoro e delle Politiche Sociali) Data Source."""
    
    def __init__(self):
        source_info = DataSourceInfo(
            source_id="ministry_labor",
            name="Ministero del Lavoro e delle Politiche Sociali",
            organization="Governo Italiano - Ministero del Lavoro",
            source_type=DataSourceType.GOVERNMENT,
            base_url="https://www.lavoro.gov.it",
            description="Official Italian Ministry of Labor - authoritative source for CCNL registrations and labor law",
            supported_sectors=list(CCNLSector),  # Government source supports all sectors
            update_frequency=UpdateFrequency.DAILY,
            reliability_score=0.98,  # Highest reliability for official government source
            api_key_required=False,
            rate_limit=60,  # Respectful rate limiting for government site
            contact_info="webmaster@lavoro.gov.it"
        )
        super().__init__(source_info)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Ministry of Labor specific endpoints
        self.endpoints = {
            "ccnl_archive": "/documenti/ccnl",
            "labour_law": "/normative",
            "statistics": "/statistiche",
            "registrations": "/registrazioni-ccnl",
            "circolars": "/circolari",
            "press_releases": "/comunicati-stampa"
        }
        
    async def connect(self) -> bool:
        """Connect to Ministry of Labor data source."""
        try:
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=45)
                headers = {
                    'User-Agent': 'PratikoAI CCNL Integration Bot/1.0 (contact: support@pratikoai.com)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'it-IT,it;q=0.8,en;q=0.6',
                    'Accept-Encoding': 'gzip, deflate'
                }
                self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
            
            # Test connection with main page
            async with self.session.get(self.source_info.base_url) as response:
                if response.status == 200:
                    self.source_info.status = DataSourceStatus.ACTIVE
                    self.source_info.last_updated = datetime.now()
                    logger.info("Successfully connected to Ministry of Labor data source")
                    return True
                else:
                    logger.warning(f"Ministry of Labor returned status {response.status}")
                    
        except Exception as e:
            logger.error(f"Failed to connect to Ministry of Labor: {e}")
            self.source_info.status = DataSourceStatus.ERROR
            
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from Ministry of Labor data source."""
        if self.session:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE
        
    async def test_connection(self) -> bool:
        """Test connection to Ministry of Labor."""
        if not self.session:
            return await self.connect()
        
        try:
            async with self.session.get(f"{self.source_info.base_url}/") as response:
                return response.status == 200
        except Exception:
            return False
    
    async def search_documents(self, query: DataSourceQuery) -> List[CCNLDocument]:
        """Search for CCNL documents from Ministry of Labor."""
        if not await self.test_connection():
            return []
            
        documents = []
        
        try:
            # Search across multiple Ministry endpoints
            search_tasks = [
                self._search_ccnl_archive(query),
                self._search_labour_law(query),
                self._search_circulars(query),
                self._search_press_releases(query)
            ]
            
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    documents.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in Ministry search: {result}")
            
            # Remove duplicates and limit results
            unique_documents = self._deduplicate_documents(documents)
            
        except Exception as e:
            logger.error(f"Error searching Ministry of Labor documents: {e}")
            
        return unique_documents[:query.max_results]
    
    async def _search_ccnl_archive(self, query: DataSourceQuery) -> List[CCNLDocument]:
        """Search the Ministry's CCNL archive."""
        documents = []
        
        try:
            url = f"{self.source_info.base_url}{self.endpoints['ccnl_archive']}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents
                    
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for CCNL document links
                ccnl_links = soup.find_all(['a', 'div'], class_=re.compile(r'ccnl|contratto|documento'))
                
                for link in ccnl_links:
                    doc = await self._extract_ministry_document(link, url, "ccnl_archive")
                    if doc and self._document_matches_query(doc, query):
                        documents.append(doc)
                        
        except Exception as e:
            logger.error(f"Error searching CCNL archive: {e}")
            
        return documents
    
    async def _search_labour_law(self, query: DataSourceQuery) -> List[CCNLDocument]:
        """Search Ministry's labour law publications."""
        documents = []
        
        try:
            url = f"{self.source_info.base_url}{self.endpoints['labour_law']}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents
                    
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for normative documents
                law_links = soup.find_all(['a', 'div'], class_=re.compile(r'normativ|legge|decreto|circolare'))
                
                for link in law_links:
                    doc = await self._extract_ministry_document(link, url, "labour_law")
                    if doc and self._document_matches_query(doc, query):
                        documents.append(doc)
                        
        except Exception as e:
            logger.error(f"Error searching labour law: {e}")
            
        return documents
    
    async def _search_circulars(self, query: DataSourceQuery) -> List[CCNLDocument]:
        """Search Ministry's circulars and interpretive documents."""
        documents = []
        
        try:
            url = f"{self.source_info.base_url}{self.endpoints['circulars']}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents
                    
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for circular documents
                circular_links = soup.find_all(['a', 'div'], class_=re.compile(r'circolare|interpretazione|chiarimento'))
                
                for link in circular_links:
                    doc = await self._extract_ministry_document(link, url, "circular")
                    if doc and self._document_matches_query(doc, query):
                        documents.append(doc)
                        
        except Exception as e:
            logger.error(f"Error searching circulars: {e}")
            
        return documents
    
    async def _search_press_releases(self, query: DataSourceQuery) -> List[CCNLDocument]:
        """Search Ministry's press releases for CCNL-related news."""
        documents = []
        
        try:
            url = f"{self.source_info.base_url}{self.endpoints['press_releases']}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return documents
                    
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for press releases about labor agreements
                press_links = soup.find_all(['a', 'div'], class_=re.compile(r'comunicato|stampa|notizia'))
                
                for link in press_links:
                    if self._contains_ccnl_keywords(link.get_text()):
                        doc = await self._extract_ministry_document(link, url, "press_release")
                        if doc and self._document_matches_query(doc, query):
                            documents.append(doc)
                            
        except Exception as e:
            logger.error(f"Error searching press releases: {e}")
            
        return documents
    
    async def _extract_ministry_document(
        self, element, base_url: str, doc_category: str
    ) -> Optional[CCNLDocument]:
        """Extract document information from Ministry HTML element."""
        try:
            # Extract title
            title_elem = element.find(['h1', 'h2', 'h3', 'h4']) or element
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            if not title or len(title) < 10:
                return None
                
            # Extract document URL
            link_elem = element.find('a', href=True) if element.name != 'a' else element
            if link_elem and link_elem.get('href'):
                doc_url = urljoin(self.source_info.base_url, link_elem['href'])
            else:
                doc_url = base_url
                
            # Determine sector from title content
            sector = self._determine_sector_from_content(title)
            
            # Determine document type
            doc_type = self._determine_document_type(title, doc_category)
            
            # Extract dates
            pub_date = self._extract_publication_date(element) or date.today()
            effective_date = self._extract_effective_date(element) or pub_date
            
            # Generate unique document ID
            doc_id = hashlib.sha256(
                f"{self.source_info.source_id}_{doc_url}_{title}".encode()
            ).hexdigest()[:16]
            
            return CCNLDocument(
                document_id=doc_id,
                source_id=self.source_info.source_id,
                title=title,
                sector=sector,
                publication_date=pub_date,
                effective_date=effective_date,
                expiry_date=self._extract_expiry_date(element),
                document_type=doc_type,
                url=doc_url,
                content_hash=hashlib.sha256(title.encode()).hexdigest()[:16],
                confidence_score=0.95  # High confidence for government source
            )
            
        except Exception as e:
            logger.error(f"Error extracting Ministry document: {e}")
            return None
    
    def _determine_sector_from_content(self, content: str) -> CCNLSector:
        """Determine CCNL sector from document content."""
        content_lower = content.lower()
        
        # Sector mapping based on keywords
        sector_keywords = {
            CCNLSector.METALMECCANICI_INDUSTRIA: ['metalmeccanici', 'meccanica', 'siderurgia', 'metallurgia'],
            CCNLSector.EDILIZIA_INDUSTRIA: ['edilizia', 'costruzioni', 'cantieri', 'opere pubbliche'],
            CCNLSector.COMMERCIO_TERZIARIO: ['commercio', 'distribuzione', 'vendita', 'negozi'],
            CCNLSector.SANITA_PRIVATA: ['sanità', 'sanitario', 'ospedale', 'clinica'],
            CCNLSector.SCUOLA_PRIVATA: ['scuola', 'educazione', 'istruzione', 'formazione'],
            CCNLSector.TRASPORTI_LOGISTICA: ['trasporti', 'logistica', 'autotrasporti', 'spedizioni'],
            CCNLSector.TURISMO: ['turismo', 'alberghi', 'hotel', 'ristorazione'],
            CCNLSector.CHIMICI_FARMACEUTICI: ['chimico', 'farmaceutico', 'farmacia'],
            CCNLSector.ALIMENTARI_INDUSTRIA: ['alimentare', 'alimentari', 'food', 'bevande'],
            CCNLSector.TESSILI: ['tessile', 'abbigliamento', 'moda', 'confezioni']
        }
        
        for sector, keywords in sector_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return sector
        
        # Default to generic industry if no specific match
        return CCNLSector.METALMECCANICI_INDUSTRIA
    
    def _determine_document_type(self, title: str, category: str) -> str:
        """Determine document type based on title and category."""
        title_lower = title.lower()
        
        if category == "ccnl_archive":
            if "rinnovo" in title_lower or "renewal" in title_lower:
                return "renewal"
            elif "modifica" in title_lower or "amendment" in title_lower:
                return "amendment"
            else:
                return "agreement"
        elif category == "labour_law":
            return "regulation"
        elif category == "circular":
            return "interpretation"
        elif category == "press_release":
            return "announcement"
        else:
            return "document"
    
    def _extract_publication_date(self, element) -> Optional[date]:
        """Extract publication date from document element."""
        date_patterns = [
            r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',  # DD/MM/YYYY
            r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})',  # YYYY/MM/DD
            r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})'
        ]
        
        italian_months = {
            'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
            'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
            'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
        }
        
        text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match) == 3 and match[1] in italian_months:
                        # Italian month format
                        day, month_name, year = match
                        return date(int(year), italian_months[month_name.lower()], int(day))
                    elif len(match) == 3:
                        # Numeric format
                        if len(match[2]) == 4:  # DD/MM/YYYY
                            day, month, year = match
                        else:  # YYYY/MM/DD
                            year, month, day = match
                        return date(int(year), int(month), int(day))
                except ValueError:
                    continue
                    
        return None
    
    def _extract_effective_date(self, element) -> Optional[date]:
        """Extract effective date from document element."""
        text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        # Look for effective date keywords
        effective_patterns = [
            r'efficacia.{0,20}(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',
            r'vigore.{0,20}(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',
            r'decorrenza.{0,20}(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})'
        ]
        
        for pattern in effective_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    day, month, year = match
                    return date(int(year), int(month), int(day))
                except ValueError:
                    continue
                    
        return None
    
    def _extract_expiry_date(self, element) -> Optional[date]:
        """Extract expiry date from document element."""
        text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        # Look for expiry date keywords
        expiry_patterns = [
            r'scadenza.{0,20}(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',
            r'termine.{0,20}(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',
            r'fino al.{0,20}(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})'
        ]
        
        for pattern in expiry_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    day, month, year = match
                    return date(int(year), int(month), int(day))
                except ValueError:
                    continue
                    
        return None
    
    def _contains_ccnl_keywords(self, text: str) -> bool:
        """Check if text contains CCNL-related keywords."""
        ccnl_keywords = [
            'ccnl', 'contratto collettivo', 'contratti collettivi',
            'accordo sindacale', 'rinnovo contratto', 'negoziazione',
            'sindacato', 'lavoro', 'salario', 'stipendio'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in ccnl_keywords)
    
    def _document_matches_query(self, document: CCNLDocument, query: DataSourceQuery) -> bool:
        """Check if document matches the search query."""
        # Sector filter
        if query.sectors and document.sector not in query.sectors:
            return False
        
        # Date range filter
        if query.date_from and document.publication_date < query.date_from:
            return False
        if query.date_to and document.publication_date > query.date_to:
            return False
        
        # Document type filter
        if query.document_types and document.document_type not in query.document_types:
            return False
        
        # Keywords filter
        if query.keywords:
            title_lower = document.title.lower()
            if not any(keyword.lower() in title_lower for keyword in query.keywords):
                return False
        
        return True
    
    def _deduplicate_documents(self, documents: List[CCNLDocument]) -> List[CCNLDocument]:
        """Remove duplicate documents based on content hash."""
        seen_hashes = set()
        unique_docs = []
        
        for doc in documents:
            if doc.content_hash not in seen_hashes:
                seen_hashes.add(doc.content_hash)
                unique_docs.append(doc)
        
        return unique_docs
    
    async def get_document_content(self, document_id: str) -> Optional[str]:
        """Retrieve the full content of a specific document."""
        try:
            # In a full implementation, this would fetch the document by ID
            # and extract the full text content
            logger.info(f"Document content retrieval not fully implemented for {self.source_info.source_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving document content: {e}")
            return None
    
    async def get_latest_updates(self, since: Optional[datetime] = None) -> List[CCNLDocument]:
        """Get documents updated since the specified time."""
        try:
            # Create query for recent updates
            since_date = since.date() if since else date.today() - timedelta(days=7)
            
            query = DataSourceQuery(
                date_from=since_date,
                max_results=50,
                include_content=False
            )
            
            return await self.search_documents(query)
        except Exception as e:
            logger.error(f"Error getting latest updates: {e}")
            return []


class INPSDataSource(BaseDataSource):
    """INPS (National Institute for Social Security) Data Source."""
    
    def __init__(self):
        source_info = DataSourceInfo(
            source_id="inps",
            name="INPS - Istituto Nazionale della Previdenza Sociale",
            organization="INPS",
            source_type=DataSourceType.GOVERNMENT,
            base_url="https://www.inps.it",
            description="National Institute for Social Security - contribution rates and social security data",
            supported_sectors=list(CCNLSector),  # INPS covers all sectors
            update_frequency=UpdateFrequency.WEEKLY,
            reliability_score=0.96,
            api_key_required=False,
            rate_limit=30,
            contact_info="info@inps.it"
        )
        super().__init__(source_info)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self) -> bool:
        """Connect to INPS data source."""
        try:
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=30)
                headers = {
                    'User-Agent': 'PratikoAI CCNL Integration Bot/1.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
                self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
            
            async with self.session.get(f"{self.source_info.base_url}/") as response:
                if response.status == 200:
                    self.source_info.status = DataSourceStatus.ACTIVE
                    self.source_info.last_updated = datetime.now()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to connect to INPS: {e}")
            self.source_info.status = DataSourceStatus.ERROR
            
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from INPS data source."""
        if self.session:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE
    
    async def test_connection(self) -> bool:
        """Test connection to INPS."""
        if not self.session:
            return await self.connect()
        
        try:
            async with self.session.get(self.source_info.base_url) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def search_documents(self, query: DataSourceQuery) -> List[CCNLDocument]:
        """Search for INPS documents - primarily contribution rate tables."""
        if not await self.test_connection():
            return []
        
        documents = []
        
        try:
            # Search INPS circulars and contribution rate updates
            search_urls = [
                f"{self.source_info.base_url}/circolari",
                f"{self.source_info.base_url}/aliquote-contributive",
                f"{self.source_info.base_url}/normativa"
            ]
            
            for url in search_urls:
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            soup = BeautifulSoup(content, 'html.parser')
                            
                            # Extract INPS documents
                            links = soup.find_all('a', href=True)
                            for link in links:
                                text = link.get_text(strip=True).lower()
                                if any(keyword in text for keyword in ['aliquot', 'contributi', 'ccnl', 'contratt']):
                                    doc = await self._create_inps_document(link, url)
                                    if doc:
                                        documents.append(doc)
                except Exception as e:
                    logger.error(f"Error searching INPS URL {url}: {e}")
            
        except Exception as e:
            logger.error(f"Error searching INPS documents: {e}")
        
        return documents[:query.max_results]
    
    async def _create_inps_document(self, link, base_url: str) -> Optional[CCNLDocument]:
        """Create INPS document from link."""
        try:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                return None
            
            doc_url = urljoin(self.source_info.base_url, href) if href else base_url
            
            doc_id = hashlib.sha256(f"{self.source_info.source_id}_{doc_url}".encode()).hexdigest()[:16]
            
            return CCNLDocument(
                document_id=doc_id,
                source_id=self.source_info.source_id,
                title=title,
                sector=CCNLSector.METALMECCANICI_INDUSTRIA,  # Default sector
                publication_date=date.today(),
                effective_date=date.today(),
                expiry_date=None,
                document_type="regulation",
                url=doc_url,
                content_hash=hashlib.sha256(title.encode()).hexdigest()[:16],
                confidence_score=0.90
            )
        except Exception as e:
            logger.error(f"Error creating INPS document: {e}")
            return None
    
    async def get_document_content(self, document_id: str) -> Optional[str]:
        """Retrieve document content."""
        logger.info(f"Document content retrieval not implemented for {self.source_info.source_id}")
        return None
    
    async def get_latest_updates(self, since: Optional[datetime] = None) -> List[CCNLDocument]:
        """Get latest INPS updates."""
        query = DataSourceQuery(
            date_from=since.date() if since else date.today() - timedelta(days=30),
            max_results=20
        )
        return await self.search_documents(query)


# Government sources registry
GOVERNMENT_SOURCES = {
    "ministry_labor": MinistryOfLaborDataSource,
    "inps": INPSDataSource,
}


async def get_all_government_sources() -> List[BaseDataSource]:
    """Get all available government data sources."""
    sources = []
    for source_class in GOVERNMENT_SOURCES.values():
        try:
            source = source_class()
            sources.append(source)
        except Exception as e:
            logger.error(f"Error initializing government source {source_class.__name__}: {e}")
    return sources