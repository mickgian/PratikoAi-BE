"""
Cassazione (Italian Supreme Court) Data Source Integration.

This module integrates with the Italian Supreme Court (Corte di Cassazione)
database and other legal databases to provide access to labor law jurisprudence,
legal precedents, and court decisions relevant to CCNL interpretation.
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
from urllib.parse import urljoin, urlparse, quote

from app.models.ccnl_data import CCNLSector
from app.models.cassazione import (
    CassazioneSection, DecisionType, LegalPrincipleArea,
    CassazioneDecision, CassazioneSearchQuery, CassazioneSearchResult,
    extract_legal_keywords, classify_precedent_value, determine_related_sectors
)
from .base_source import (
    BaseDataSource, DataSourceInfo, DataSourceType, DataSourceStatus,
    UpdateFrequency, CCNLDocument, DataSourceQuery
)

logger = logging.getLogger(__name__)


class CassazioneDataSource(BaseDataSource):
    """Cassazione (Italian Supreme Court) Data Source for Labor Law Jurisprudence."""
    
    def __init__(self):
        source_info = DataSourceInfo(
            source_id="cassazione",
            name="Corte di Cassazione - Sezioni Civili e del Lavoro",
            organization="Corte Suprema di Cassazione",
            source_type=DataSourceType.GOVERNMENT,
            base_url="https://www.cortedicassazione.it",
            description="Italian Supreme Court jurisprudence and legal precedents for labor law and CCNL interpretation",
            supported_sectors=list(CCNLSector),  # Jurisprudence applies to all sectors
            update_frequency=UpdateFrequency.DAILY,
            reliability_score=0.99,  # Highest reliability for Supreme Court
            api_key_required=False,
            rate_limit=30,  # Respectful rate limiting for court website
            contact_info="webmaster@cortedicassazione.it"
        )
        super().__init__(source_info)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Cassazione-specific endpoints and search parameters
        self.endpoints = {
            "civil_decisions": "/ricerca-semplice-civil",
            "labor_decisions": "/ricerca-semplice-lavoro", 
            "united_sections": "/ricerca-sezioni-unite",
            "recent_decisions": "/novita/sentenze-recenti",
            "legal_principles": "/massimario",
            "advanced_search": "/ricerca-avanzata"
        }
        
        # Legal areas mapping for Italian court system
        self.legal_area_mapping = {
            "contratto di lavoro": LegalPrincipleArea.CONTRATTO_LAVORO,
            "contratti collettivi": LegalPrincipleArea.CCNL_INTERPRETAZIONE,
            "licenziamento": LegalPrincipleArea.LICENZIAMENTO,
            "retribuzione": LegalPrincipleArea.RETRIBUZIONE,
            "orario di lavoro": LegalPrincipleArea.ORARIO_LAVORO,
            "ferie": LegalPrincipleArea.FERIE_PERMESSI,
            "contributi previdenziali": LegalPrincipleArea.CONTRIBUTI_PREVIDENZA,
            "sicurezza sul lavoro": LegalPrincipleArea.SICUREZZA_LAVORO,
            "discriminazione": LegalPrincipleArea.DISCRIMINAZIONE,
            "diritti sindacali": LegalPrincipleArea.SINDACATO,
            "sciopero": LegalPrincipleArea.SCIOPERO,
            "maternità": LegalPrincipleArea.MATERNITA_PATERNITA,
            "malattia professionale": LegalPrincipleArea.MALATTIA_INFORTUNIO
        }
        
    async def connect(self) -> bool:
        """Connect to Cassazione data source."""
        try:
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=45)
                headers = {
                    'User-Agent': 'PratikoAI Legal Research Bot/1.0 (legal.research@pratikoai.com)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'it-IT,it;q=0.9,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',  # Do Not Track
                    'Connection': 'keep-alive'
                }
                self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
            
            # Test connection with main page
            async with self.session.get(self.source_info.base_url) as response:
                if response.status == 200:
                    self.source_info.status = DataSourceStatus.ACTIVE
                    self.source_info.last_updated = datetime.now()
                    logger.info("Successfully connected to Cassazione data source")
                    return True
                else:
                    logger.warning(f"Cassazione returned status {response.status}")
                    
        except Exception as e:
            logger.error(f"Failed to connect to Cassazione: {e}")
            self.source_info.status = DataSourceStatus.ERROR
            
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from Cassazione data source."""
        if self.session:
            await self.session.close()
            self.session = None
        self.source_info.status = DataSourceStatus.INACTIVE
        
    async def test_connection(self) -> bool:
        """Test connection to Cassazione."""
        if not self.session:
            return await self.connect()
        
        try:
            async with self.session.get(f"{self.source_info.base_url}/") as response:
                return response.status == 200
        except Exception:
            return False
    
    async def search_documents(self, query: DataSourceQuery) -> List[CCNLDocument]:
        """Search for legal documents from Cassazione."""
        if not await self.test_connection():
            return []
            
        documents = []
        
        try:
            # Convert general query to Cassazione-specific search
            cassazione_query = self._convert_to_cassazione_query(query)
            
            # Search across multiple Cassazione endpoints
            search_tasks = [
                self._search_labor_decisions(cassazione_query),
                self._search_civil_decisions(cassazione_query),
                self._search_recent_decisions(cassazione_query),
                self._search_legal_principles(cassazione_query)
            ]
            
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    documents.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in Cassazione search: {result}")
            
            # Remove duplicates and limit results
            unique_documents = self._deduplicate_legal_documents(documents)
            
        except Exception as e:
            logger.error(f"Error searching Cassazione documents: {e}")
            
        return unique_documents[:query.max_results]
    
    def _convert_to_cassazione_query(self, query: DataSourceQuery) -> CassazioneSearchQuery:
        """Convert general query to Cassazione-specific search parameters."""
        # Map general keywords to legal terms
        legal_keywords = []
        if query.keywords:
            for keyword in query.keywords:
                legal_keywords.extend(self._expand_legal_keywords(keyword))
        
        # Determine legal areas from sectors and keywords
        legal_areas = self._determine_legal_areas(query.sectors, legal_keywords)
        
        return CassazioneSearchQuery(
            keywords=legal_keywords,
            legal_areas=legal_areas,
            sectors=query.sectors,
            date_from=query.date_from,
            date_to=query.date_to,
            max_results=query.max_results,
            include_full_text=query.include_content,
            sort_by="decision_date",
            sort_order="desc"
        )
    
    def _expand_legal_keywords(self, keyword: str) -> List[str]:
        """Expand general keywords to include legal synonyms."""
        keyword_lower = keyword.lower()
        expansions = {
            "ccnl": ["contratto collettivo", "contrattazione collettiva", "accordo collettivo"],
            "lavoro": ["rapporto di lavoro", "contratto di lavoro", "prestazione lavorativa"],
            "licenziamento": ["risoluzione rapporto", "cessazione lavoro", "dimissioni"],
            "retribuzione": ["salario", "stipendio", "compenso", "emolumento"],
            "orario": ["orario di lavoro", "tempo di lavoro", "turni"],
            "ferie": ["congedi", "permessi", "aspettativa"],
            "sindacato": ["organizzazione sindacale", "rappresentanza sindacale"],
            "sciopero": ["astensione dal lavoro", "agitazione sindacale"],
            "contributi": ["contributi previdenziali", "previdenza sociale", "inps"]
        }
        
        result = [keyword]
        for key, synonyms in expansions.items():
            if key in keyword_lower:
                result.extend(synonyms)
        
        return result
    
    def _determine_legal_areas(self, sectors: Optional[List[CCNLSector]], keywords: List[str]) -> List[LegalPrincipleArea]:
        """Determine relevant legal areas from query parameters."""
        legal_areas = []
        keywords_text = " ".join(keywords).lower() if keywords else ""
        
        # Map keywords to legal areas
        if any(term in keywords_text for term in ["ccnl", "contratto collettivo", "contrattazione"]):
            legal_areas.append(LegalPrincipleArea.CCNL_INTERPRETAZIONE)
        
        if any(term in keywords_text for term in ["licenziamento", "risoluzione", "cessazione"]):
            legal_areas.append(LegalPrincipleArea.LICENZIAMENTO)
            
        if any(term in keywords_text for term in ["retribuzione", "salario", "stipendio"]):
            legal_areas.append(LegalPrincipleArea.RETRIBUZIONE)
            
        if any(term in keywords_text for term in ["orario", "tempo di lavoro"]):
            legal_areas.append(LegalPrincipleArea.ORARIO_LAVORO)
            
        if any(term in keywords_text for term in ["ferie", "congedi", "permessi"]):
            legal_areas.append(LegalPrincipleArea.FERIE_PERMESSI)
            
        if any(term in keywords_text for term in ["contributi", "previdenza", "inps"]):
            legal_areas.append(LegalPrincipleArea.CONTRIBUTI_PREVIDENZA)
            
        if any(term in keywords_text for term in ["sicurezza", "infortunio"]):
            legal_areas.append(LegalPrincipleArea.SICUREZZA_LAVORO)
            
        if any(term in keywords_text for term in ["discriminazione", "pari opportunità"]):
            legal_areas.append(LegalPrincipleArea.DISCRIMINAZIONE)
            
        if any(term in keywords_text for term in ["sindacato", "rappresentanza"]):
            legal_areas.append(LegalPrincipleArea.SINDACATO)
            
        if any(term in keywords_text for term in ["sciopero", "astensione"]):
            legal_areas.append(LegalPrincipleArea.SCIOPERO)
        
        # Default to general contract law if no specific area identified
        if not legal_areas:
            legal_areas.append(LegalPrincipleArea.CONTRATTO_LAVORO)
        
        return legal_areas
    
    async def _search_labor_decisions(self, query: CassazioneSearchQuery) -> List[CCNLDocument]:
        """Search labor section decisions."""
        documents = []
        
        try:
            search_url = f"{self.source_info.base_url}{self.endpoints['labor_decisions']}"
            
            # Build search parameters for labor section
            params = {
                "sezione": "lavoro",
                "tipo": "sentenze",
                "parole_chiave": " ".join(query.keywords) if query.keywords else "",
                "data_da": query.date_from.strftime("%d/%m/%Y") if query.date_from else "",
                "data_a": query.date_to.strftime("%d/%m/%Y") if query.date_to else "",
                "max_risultati": min(query.max_results, 100)
            }
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    documents.extend(await self._extract_cassazione_decisions(soup, search_url, "labor"))
                else:
                    logger.warning(f"Labor decisions search failed with status {response.status}")
                    
        except Exception as e:
            logger.error(f"Error searching labor decisions: {e}")
            
        return documents
    
    async def _search_civil_decisions(self, query: CassazioneSearchQuery) -> List[CCNLDocument]:
        """Search civil section decisions."""
        documents = []
        
        try:
            search_url = f"{self.source_info.base_url}{self.endpoints['civil_decisions']}"
            
            # Build search parameters for civil sections
            params = {
                "sezione": "civile",
                "tipo": "sentenze",
                "materia": "lavoro",  # Focus on labor-related civil decisions
                "parole_chiave": " ".join(query.keywords) if query.keywords else "",
                "data_da": query.date_from.strftime("%d/%m/%Y") if query.date_from else "",
                "data_a": query.date_to.strftime("%d/%m/%Y") if query.date_to else "",
                "max_risultati": min(query.max_results, 100)
            }
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    documents.extend(await self._extract_cassazione_decisions(soup, search_url, "civil"))
                    
        except Exception as e:
            logger.error(f"Error searching civil decisions: {e}")
            
        return documents
    
    async def _search_recent_decisions(self, query: CassazioneSearchQuery) -> List[CCNLDocument]:
        """Search recent decisions."""
        documents = []
        
        try:
            search_url = f"{self.source_info.base_url}{self.endpoints['recent_decisions']}"
            
            async with self.session.get(search_url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Filter recent decisions for labor-related content
                    recent_docs = await self._extract_cassazione_decisions(soup, search_url, "recent")
                    
                    # Filter by query criteria
                    filtered_docs = []
                    for doc in recent_docs:
                        if self._document_matches_query(doc, query):
                            filtered_docs.append(doc)
                    
                    documents.extend(filtered_docs)
                    
        except Exception as e:
            logger.error(f"Error searching recent decisions: {e}")
            
        return documents
    
    async def _search_legal_principles(self, query: CassazioneSearchQuery) -> List[CCNLDocument]:
        """Search legal principles and maxims."""
        documents = []
        
        try:
            search_url = f"{self.source_info.base_url}{self.endpoints['legal_principles']}"
            
            params = {
                "tipo": "massime",
                "materia": "diritto_del_lavoro",
                "parole_chiave": " ".join(query.keywords) if query.keywords else "",
                "max_risultati": min(query.max_results, 50)
            }
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    documents.extend(await self._extract_legal_principles(soup, search_url))
                    
        except Exception as e:
            logger.error(f"Error searching legal principles: {e}")
            
        return documents
    
    async def _extract_cassazione_decisions(self, soup: BeautifulSoup, base_url: str, search_type: str) -> List[CCNLDocument]:
        """Extract decision information from Cassazione HTML."""
        documents = []
        
        try:
            # Look for decision entries - common patterns in Cassazione website
            decision_selectors = [
                ".sentenza-item",
                ".decision-entry", 
                ".risultato-ricerca",
                ".lista-sentenze li",
                "div[class*='sentenza']",
                "div[class*='decision']"
            ]
            
            decision_elements = []
            for selector in decision_selectors:
                elements = soup.select(selector)
                if elements:
                    decision_elements = elements
                    break
            
            # If no structured elements found, look for generic containers
            if not decision_elements:
                decision_elements = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'(sentenza|decision|risultato)'))
            
            for element in decision_elements[:50]:  # Limit processing
                doc = await self._extract_single_decision(element, base_url, search_type)
                if doc:
                    documents.append(doc)
                    
        except Exception as e:
            logger.error(f"Error extracting Cassazione decisions: {e}")
            
        return documents
    
    async def _extract_single_decision(self, element, base_url: str, search_type: str) -> Optional[CCNLDocument]:
        """Extract a single decision from HTML element."""
        try:
            # Extract basic information
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a']) or element
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            if not title or len(title) < 10:
                return None
            
            # Extract decision number and year from title
            decision_match = re.search(r'n\.\s*(\d+)/(\d{4})', title)
            if decision_match:
                decision_number = int(decision_match.group(1))
                decision_year = int(decision_match.group(2))
            else:
                # Try alternative patterns
                alt_match = re.search(r'(\d+)/(\d{4})', title)
                if alt_match:
                    decision_number = int(alt_match.group(1))
                    decision_year = int(alt_match.group(2))
                else:
                    decision_number = 0
                    decision_year = datetime.now().year
            
            # Extract document URL
            link_elem = element.find('a', href=True)
            if link_elem and link_elem.get('href'):
                doc_url = urljoin(self.source_info.base_url, link_elem['href'])
            else:
                doc_url = base_url
            
            # Extract dates
            decision_date = self._extract_decision_date(element) or date.today()
            
            # Extract section information
            section = self._determine_cassazione_section(element, title)
            
            # Extract summary/abstract
            summary_elem = element.find(['p', 'div'], class_=re.compile(r'(abstract|summary|riassunto)'))
            summary = summary_elem.get_text(strip=True) if summary_elem else ""
            
            # Determine document type
            doc_type = self._determine_decision_type(title, element)
            
            # Extract legal areas and keywords
            legal_keywords = extract_legal_keywords(f"{title} {summary}")
            legal_areas = [area for keyword in legal_keywords 
                          for area_name, area in self.legal_area_mapping.items() 
                          if keyword in area_name]
            
            # Determine related sectors
            related_sectors = determine_related_sectors(f"{title} {summary}", legal_areas)
            
            # Create document ID
            decision_id = f"Cass.{section}.{decision_number}.{decision_year}"
            doc_id = hashlib.sha256(f"cassazione_{decision_id}_{title}".encode()).hexdigest()[:16]
            
            return CCNLDocument(
                document_id=doc_id,
                source_id=self.source_info.source_id,
                title=f"{decision_id} - {title}",
                sector=related_sectors[0] if related_sectors else CCNLSector.METALMECCANICI_INDUSTRIA,
                publication_date=decision_date,
                effective_date=decision_date,
                expiry_date=None,
                document_type="jurisprudence",
                url=doc_url,
                content_hash=hashlib.sha256(f"{title}{summary}".encode()).hexdigest()[:16],
                confidence_score=0.95,  # High confidence for Supreme Court
                raw_content=summary if summary else None,
                extracted_data={
                    "decision_number": decision_number,
                    "decision_year": decision_year,
                    "section": section,
                    "legal_areas": legal_areas,
                    "legal_keywords": legal_keywords,
                    "related_sectors": [s.value for s in related_sectors],
                    "precedent_value": "high",  # Cassazione decisions are high precedent
                    "decision_type": doc_type
                }
            )
            
        except Exception as e:
            logger.error(f"Error extracting single decision: {e}")
            return None
    
    async def _extract_legal_principles(self, soup: BeautifulSoup, base_url: str) -> List[CCNLDocument]:
        """Extract legal principles and maxims."""
        documents = []
        
        try:
            principle_elements = soup.find_all(['div', 'li'], class_=re.compile(r'(massima|principio|principle)'))
            
            for element in principle_elements[:25]:  # Limit processing
                title_elem = element.find(['h1', 'h2', 'h3', 'strong'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract principle text
                principle_text = element.get_text(strip=True)
                
                # Extract related decision reference
                decision_ref_match = re.search(r'Cass\.\s*[^,]*,?\s*n\.\s*(\d+)/(\d{4})', principle_text)
                if decision_ref_match:
                    decision_number = int(decision_ref_match.group(1))
                    decision_year = int(decision_ref_match.group(2))
                else:
                    decision_number = 0
                    decision_year = datetime.now().year
                
                # Determine legal areas
                legal_keywords = extract_legal_keywords(principle_text)
                legal_areas = [area for keyword in legal_keywords 
                              for area_name, area in self.legal_area_mapping.items() 
                              if keyword in area_name]
                
                related_sectors = determine_related_sectors(principle_text, legal_areas)
                
                doc_id = hashlib.sha256(f"cassazione_principle_{title}".encode()).hexdigest()[:16]
                
                document = CCNLDocument(
                    document_id=doc_id,
                    source_id=self.source_info.source_id,
                    title=f"Principio di Diritto - {title}",
                    sector=related_sectors[0] if related_sectors else CCNLSector.METALMECCANICI_INDUSTRIA,
                    publication_date=date.today(),
                    effective_date=date.today(),
                    expiry_date=None,
                    document_type="legal_principle",
                    url=base_url,
                    content_hash=hashlib.sha256(principle_text.encode()).hexdigest()[:16],
                    confidence_score=0.90,
                    raw_content=principle_text,
                    extracted_data={
                        "decision_number": decision_number,
                        "decision_year": decision_year,
                        "legal_areas": legal_areas,
                        "legal_keywords": legal_keywords,
                        "related_sectors": [s.value for s in related_sectors],
                        "precedent_value": "high",
                        "document_type": "legal_principle"
                    }
                )
                
                documents.append(document)
                
        except Exception as e:
            logger.error(f"Error extracting legal principles: {e}")
            
        return documents
    
    def _extract_decision_date(self, element) -> Optional[date]:
        """Extract decision date from HTML element."""
        # Look for date patterns in the element text
        text = element.get_text() if hasattr(element, 'get_text') else str(element)
        
        # Italian date patterns
        date_patterns = [
            r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})',
            r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',
            r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})',
        ]
        
        italian_months = {
            'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
            'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
            'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
        }
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match) == 3 and match[1] in italian_months:
                        # Italian month format
                        day, month_name, year = match
                        return date(int(year), italian_months[month_name.lower()], int(day))
                    elif len(match) == 3:
                        # Numeric format - try both DD/MM/YYYY and YYYY/MM/DD
                        if len(match[2]) == 4:  # DD/MM/YYYY
                            day, month, year = match
                            return date(int(year), int(month), int(day))
                        else:  # YYYY/MM/DD
                            year, month, day = match
                            return date(int(year), int(month), int(day))
                except ValueError:
                    continue
        
        return None
    
    def _determine_cassazione_section(self, element, title: str) -> str:
        """Determine the Cassazione section from element or title."""
        text = f"{title} {element.get_text()}".lower()
        
        if "sezioni unite" in text:
            return "S.U."
        elif "lavoro" in text or "sez. lav" in text:
            return "Lav."
        elif "prima sezione" in text or "sez. i" in text:
            return "I"
        elif "seconda sezione" in text or "sez. ii" in text:
            return "II" 
        elif "terza sezione" in text or "sez. iii" in text:
            return "III"
        else:
            return "Civ."
    
    def _determine_decision_type(self, title: str, element) -> str:
        """Determine the type of decision."""
        text = f"{title} {element.get_text()}".lower()
        
        if "ordinanza" in text:
            return "ordinanza"
        elif "decreto" in text:
            return "decreto"
        elif "massima" in text or "principio" in text:
            return "massima"
        else:
            return "sentenza"
    
    def _document_matches_query(self, document: CCNLDocument, query: CassazioneSearchQuery) -> bool:
        """Check if document matches the Cassazione query criteria."""
        # Check keywords
        if query.keywords:
            text = f"{document.title} {document.raw_content or ''}".lower()
            if not any(keyword.lower() in text for keyword in query.keywords):
                return False
        
        # Check sectors
        if query.sectors:
            doc_sectors = document.extracted_data.get("related_sectors", []) if document.extracted_data else []
            query_sector_values = [s.value for s in query.sectors]
            if not any(sector in query_sector_values for sector in doc_sectors):
                return False
        
        # Check date range
        if query.date_from and document.publication_date < query.date_from:
            return False
        if query.date_to and document.publication_date > query.date_to:
            return False
        
        return True
    
    def _deduplicate_legal_documents(self, documents: List[CCNLDocument]) -> List[CCNLDocument]:
        """Remove duplicate legal documents based on content and decision numbers."""
        seen_hashes = set()
        seen_decisions = set()
        unique_docs = []
        
        for doc in documents:
            # Check content hash
            if doc.content_hash in seen_hashes:
                continue
            
            # Check decision number for jurisprudence
            if doc.extracted_data and doc.extracted_data.get("decision_number"):
                decision_key = f"{doc.extracted_data.get('decision_number')}/{doc.extracted_data.get('decision_year')}"
                if decision_key in seen_decisions:
                    continue
                seen_decisions.add(decision_key)
            
            seen_hashes.add(doc.content_hash)
            unique_docs.append(doc)
        
        return unique_docs
    
    async def get_document_content(self, document_id: str) -> Optional[str]:
        """Retrieve full content of a Cassazione decision."""
        try:
            # In a full implementation, this would fetch the complete decision text
            logger.info(f"Full decision content retrieval not implemented for {self.source_info.source_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving Cassazione document content: {e}")
            return None
    
    async def get_latest_updates(self, since: Optional[datetime] = None) -> List[CCNLDocument]:
        """Get latest Cassazione decisions."""
        try:
            since_date = since.date() if since else date.today() - timedelta(days=30)
            
            query = DataSourceQuery(
                keywords=["lavoro", "ccnl", "contratto collettivo"],
                date_from=since_date,
                max_results=50,
                include_content=True
            )
            
            return await self.search_documents(query)
        except Exception as e:
            logger.error(f"Error getting latest Cassazione updates: {e}")
            return []


# Utility functions for Cassazione data processing

async def extract_decision_citations(text: str) -> List[str]:
    """Extract citations to other Cassazione decisions from text."""
    citation_patterns = [
        r'Cass\.\s*[^,]*,?\s*n\.\s*(\d+)/(\d{4})',
        r'Cassazione\s*[^,]*,?\s*n\.\s*(\d+)/(\d{4})',
        r'Sezioni\s*Unite\s*[^,]*,?\s*n\.\s*(\d+)/(\d{4})'
    ]
    
    citations = []
    for pattern in citation_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            citation = f"{match[0]}/{match[1]}"
            citations.append(citation)
    
    return list(set(citations))  # Remove duplicates


async def analyze_jurisprudence_consistency(decisions: List[CCNLDocument]) -> Dict[str, Any]:
    """Analyze consistency in jurisprudence across multiple decisions."""
    if not decisions:
        return {"consistency_score": 0.0, "analysis": "No decisions provided"}
    
    # Group decisions by legal area
    by_legal_area = {}
    for decision in decisions:
        if decision.extracted_data and decision.extracted_data.get("legal_areas"):
            for area in decision.extracted_data["legal_areas"]:
                if area not in by_legal_area:
                    by_legal_area[area] = []
                by_legal_area[area].append(decision)
    
    analysis = {
        "total_decisions": len(decisions),
        "legal_areas_covered": len(by_legal_area),
        "decisions_by_area": {area: len(docs) for area, docs in by_legal_area.items()},
        "consistency_score": 0.8,  # Placeholder - would need more sophisticated analysis
        "temporal_distribution": _analyze_temporal_distribution(decisions),
        "section_distribution": _analyze_section_distribution(decisions)
    }
    
    return analysis


def _analyze_temporal_distribution(decisions: List[CCNLDocument]) -> Dict[str, int]:
    """Analyze temporal distribution of decisions."""
    distribution = {}
    for decision in decisions:
        year = decision.publication_date.year
        distribution[str(year)] = distribution.get(str(year), 0) + 1
    return distribution


def _analyze_section_distribution(decisions: List[CCNLDocument]) -> Dict[str, int]:
    """Analyze distribution of decisions by court section."""
    distribution = {}
    for decision in decisions:
        if decision.extracted_data and decision.extracted_data.get("section"):
            section = decision.extracted_data["section"]
            distribution[section] = distribution.get(section, 0) + 1
    return distribution