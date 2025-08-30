"""
CCNL RSS Feed Monitor Service.

This service monitors RSS feeds from unions, employer associations, and official sources
to detect CCNL updates and changes. It follows TDD methodology and provides automatic
classification and processing of CCNL-related news.
"""

import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import logging
import aiohttp
import feedparser
from urllib.parse import urljoin

from app.models.ccnl_update_models import UpdateSource, UpdateStatus
from app.models.ccnl_data import CCNLSector

logger = logging.getLogger(__name__)


@dataclass
class RSSFeedItem:
    """Represents an RSS feed item."""
    title: str
    link: str
    description: str
    published: datetime
    guid: str
    source: UpdateSource
    content: Optional[str] = None


@dataclass
class CCNLDetection:
    """Represents a detected CCNL update."""
    feed_item: RSSFeedItem
    sector: Optional[CCNLSector]
    update_type: str
    confidence_score: float
    keywords_matched: List[str]
    priority: float


class RSSFeedMonitor:
    """Monitor RSS feeds for CCNL updates."""
    
    def __init__(self):
        self.feeds: List[Dict[str, Any]] = []
        self.last_check: Optional[datetime] = None
        self.check_interval = timedelta(hours=2)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # CCNL detection keywords
        self.ccnl_keywords = [
            "rinnovo ccnl", "nuovo contratto collettivo", "accordo siglato",
            "firma contratto nazionale", "aumento minimi tabellari",
            "contratto collettivo", "ccnl", "accordo sindacale",
            "rinnovo contratto", "firma accordo", "intesa raggiunta",
            "protocollo d'intesa", "ipotesi di accordo", "accordo di rinnovo"
        ]
        
        # Initialize default RSS feeds
        self._initialize_default_feeds()
    
    def _initialize_default_feeds(self):
        """Initialize default RSS feeds for monitoring."""
        default_feeds = [
            # Union Confederations
            {"url": "https://www.cgil.it/feed/", "name": "CGIL", "source": UpdateSource.CGIL_RSS},
            {"url": "https://www.cisl.it/rss.xml", "name": "CISL", "source": UpdateSource.CISL_RSS},
            {"url": "https://www.uil.it/news/rss", "name": "UIL", "source": UpdateSource.UIL_RSS},
            {"url": "https://www.ugl.it/feed/", "name": "UGL", "source": UpdateSource.UGL_RSS},
            
            # Employer Associations
            {"url": "https://www.confindustria.it/feed/", "name": "Confindustria", "source": UpdateSource.CONFINDUSTRIA_NEWS},
            {"url": "https://www.confcommercio.it/rss", "name": "Confcommercio", "source": UpdateSource.CONFCOMMERCIO_NEWS},
            {"url": "https://www.confartigianato.it/feed/", "name": "Confartigianato", "source": UpdateSource.CONFARTIGIANATO_NEWS},
            {"url": "https://www.confapi.it/rss.xml", "name": "Confapi", "source": UpdateSource.CONFAPI_NEWS},
            
            # Official Sources
            {"url": "https://www.cnel.it/feed", "name": "CNEL", "source": UpdateSource.CNEL_OFFICIAL},
            {"url": "https://www.lavoro.gov.it/rss", "name": "Ministry of Labor", "source": UpdateSource.MINISTRY_LABOR},
        ]
        
        for feed in default_feeds:
            self.add_feed(feed["url"], feed["name"], feed["source"])
    
    def add_feed(self, url: str, name: str, source: UpdateSource):
        """Add a RSS feed to monitor."""
        feed_config = {
            "url": url,
            "name": name, 
            "source": source,
            "last_checked": None,
            "last_etag": None,
            "last_modified": None,
            "consecutive_failures": 0,
            "is_active": True
        }
        self.feeds.append(feed_config)
        logger.info(f"Added RSS feed: {name} ({url})")
    
    def contains_ccnl_keywords(self, text: str) -> bool:
        """Check if text contains CCNL-related keywords."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.ccnl_keywords)
    
    def get_matched_keywords(self, text: str) -> List[str]:
        """Get list of matched CCNL keywords from text."""
        text_lower = text.lower()
        matched = []
        for keyword in self.ccnl_keywords:
            if keyword in text_lower:
                matched.append(keyword)
        return matched
    
    async def initialize_session(self):
        """Initialize HTTP session."""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': 'PratikoAI-CCNL-Monitor/1.0 (Labor Relations Research Bot)',
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*'
                }
            )
    
    async def close_session(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def fetch_feed(self, feed_config: Dict[str, Any]) -> List[RSSFeedItem]:
        """Fetch items from a single RSS feed."""
        feed_items = []
        
        try:
            await self.initialize_session()
            
            headers = {}
            if feed_config["last_etag"]:
                headers['If-None-Match'] = feed_config["last_etag"]
            if feed_config["last_modified"]:
                headers['If-Modified-Since'] = feed_config["last_modified"]
            
            async with self.session.get(feed_config["url"], headers=headers) as response:
                if response.status == 304:  # Not modified
                    logger.debug(f"Feed {feed_config['name']} not modified since last check")
                    return feed_items
                
                if response.status != 200:
                    logger.warning(f"Failed to fetch feed {feed_config['name']}: HTTP {response.status}")
                    feed_config["consecutive_failures"] += 1
                    return feed_items
                
                # Update cache headers
                feed_config["last_etag"] = response.headers.get("ETag")
                feed_config["last_modified"] = response.headers.get("Last-Modified")
                feed_config["consecutive_failures"] = 0
                
                content = await response.text()
                
                # Parse RSS/Atom feed
                feed_data = feedparser.parse(content)
                
                if feed_data.bozo:
                    logger.warning(f"Feed {feed_config['name']} has parsing errors: {feed_data.bozo_exception}")
                
                # Process feed entries
                cutoff_time = datetime.now() - timedelta(days=7)  # Only check last 7 days
                
                for entry in feed_data.entries[:50]:  # Limit to 50 most recent entries
                    published = self._parse_published_date(entry)
                    
                    if published and published < cutoff_time:
                        continue  # Skip old entries
                    
                    # Create feed item
                    item = RSSFeedItem(
                        title=entry.get('title', ''),
                        link=entry.get('link', ''),
                        description=entry.get('summary', entry.get('description', '')),
                        published=published or datetime.now(),
                        guid=entry.get('id', entry.get('guid', entry.get('link', ''))),
                        source=feed_config["source"],
                        content=entry.get('content', [{}])[0].get('value') if entry.get('content') else None
                    )
                    
                    # Only include items with CCNL keywords
                    full_text = f"{item.title} {item.description} {item.content or ''}"
                    if self.contains_ccnl_keywords(full_text):
                        feed_items.append(item)
                
                feed_config["last_checked"] = datetime.now()
                logger.info(f"Fetched {len(feed_items)} CCNL-related items from {feed_config['name']}")
                
        except Exception as e:
            logger.error(f"Error fetching feed {feed_config['name']}: {str(e)}")
            feed_config["consecutive_failures"] += 1
            
            # Disable feed after 5 consecutive failures
            if feed_config["consecutive_failures"] >= 5:
                feed_config["is_active"] = False
                logger.warning(f"Disabled feed {feed_config['name']} after 5 consecutive failures")
        
        return feed_items
    
    def _parse_published_date(self, entry: Dict[str, Any]) -> Optional[datetime]:
        """Parse published date from feed entry."""
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                try:
                    import time
                    time_struct = getattr(entry, field)
                    return datetime.fromtimestamp(time.mktime(time_struct))
                except (ValueError, TypeError):
                    continue
        
        # Try string date fields
        string_fields = ['published', 'updated', 'created']
        for field in string_fields:
            if hasattr(entry, field) and getattr(entry, field):
                try:
                    from dateutil import parser
                    return parser.parse(getattr(entry, field))
                except (ValueError, TypeError):
                    continue
        
        return None
    
    async def fetch_all_updates(self) -> List[RSSFeedItem]:
        """Fetch updates from all active RSS feeds."""
        all_items = []
        
        # Fetch feeds concurrently
        tasks = []
        for feed_config in self.feeds:
            if feed_config["is_active"]:
                task = asyncio.create_task(self.fetch_feed(feed_config))
                tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Feed fetch failed: {str(result)}")
                else:
                    all_items.extend(result)
        
        # Remove duplicates based on GUID
        seen_guids = set()
        unique_items = []
        for item in all_items:
            if item.guid not in seen_guids:
                seen_guids.add(item.guid)
                unique_items.append(item)
        
        self.last_check = datetime.now()
        logger.info(f"Fetched {len(unique_items)} unique CCNL items from {len([f for f in self.feeds if f['is_active']])} feeds")
        
        return unique_items
    
    def get_feed_statistics(self) -> Dict[str, Any]:
        """Get statistics about monitored feeds."""
        total_feeds = len(self.feeds)
        active_feeds = len([f for f in self.feeds if f["is_active"]])
        failed_feeds = len([f for f in self.feeds if f["consecutive_failures"] > 0])
        
        return {
            "total_feeds": total_feeds,
            "active_feeds": active_feeds,
            "failed_feeds": failed_feeds,
            "last_check": self.last_check,
            "feeds": [
                {
                    "name": f["name"],
                    "url": f["url"],
                    "source": f["source"].value,
                    "is_active": f["is_active"],
                    "last_checked": f["last_checked"],
                    "consecutive_failures": f["consecutive_failures"]
                }
                for f in self.feeds
            ]
        }


class CCNLUpdateDetector:
    """Detect and classify CCNL updates from RSS feed items."""
    
    def __init__(self):
        # Sector detection patterns
        self.sector_patterns = {
            CCNLSector.METALMECCANICI_INDUSTRIA: [
                "metalmeccanic", "meccanica", "industria", "fiom", "fim", "uilm", 
                "federmeccanica", "metalmeccanici", "siderurgia"
            ],
            CCNLSector.COMMERCIO_TERZIARIO: [
                "commercio", "terziario", "distribuzione", "vendita", "retail",
                "filcams", "fisascat", "uiltucs", "confcommercio"
            ],
            CCNLSector.EDILIZIA_INDUSTRIA: [
                "edilizia", "costruzioni", "cantieri", "fillea", "filca", "uila",
                "ance", "costruttori", "lavori pubblici"
            ],
            CCNLSector.SANITA_PRIVATA: [
                "sanità", "sanitario", "cliniche", "ospedali privati", "rsa",
                "fp-cgil", "fps-cisl", "uil-fpl", "aiop"
            ],
            CCNLSector.TRASPORTI_LOGISTICA: [
                "trasporti", "logistica", "autotrasporto", "spedizioni",
                "filt", "fit", "uiltrasporti", "corrieri"
            ],
            CCNLSector.TURISMO: [
                "turismo", "alberghi", "hotel", "ristoranti", "federalberghi",
                "fipe", "pubblici esercizi"
            ],
            CCNLSector.ICT: [
                "informatica", "tecnologia", "ict", "software", "telecomunicazioni",
                "uilcom", "slc", "asstel"
            ],
            CCNLSector.AGRICOLTURA: [
                "agricoltura", "agricol", "agrario", "flai", "fai", "coldiretti",
                "confagricoltura", "cia"
            ],
            CCNLSector.CHIMICI_FARMACEUTICI: [
                "chimici", "farmaceutici", "chimica", "farmacia", "filctem",
                "femca", "uiltec", "federchimica"
            ],
            CCNLSector.CREDITO_ASSICURAZIONI: [
                "credito", "banche", "assicurazioni", "first-cisl", "falcri",
                "uilca", "abi", "ania"
            ]
        }
        
        # Update type patterns
        self.update_type_patterns = {
            "renewal": ["rinnovo", "rinnovato", "rinnovamento", "rinnova"],
            "new_agreement": ["nuovo contratto", "nuova intesa", "nuovo accordo"],
            "signing": ["firma", "firmato", "sottoscritto", "siglato"],
            "amendment": ["modifica", "modificato", "integrazione", "revisione"],
            "salary_update": ["aumento", "minimi tabellari", "incremento salariale", "adeguamento retributivo"],
            "negotiation": ["trattativa", "negoziato", "confronto", "tavolo"],
            "agreement": ["accordo", "intesa", "protocollo"]
        }
    
    def classify_sector(self, title: str, content: str = "") -> Optional[CCNLSector]:
        """Classify which CCNL sector an update refers to."""
        text = f"{title} {content}".lower()
        
        best_match = None
        highest_score = 0
        
        for sector, patterns in self.sector_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in text:
                    # Give more weight to matches in title
                    if pattern in title.lower():
                        score += 2
                    else:
                        score += 1
            
            if score > highest_score:
                highest_score = score
                best_match = sector
        
        return best_match if highest_score > 0 else None
    
    def classify_update_type(self, title: str, content: str = "") -> str:
        """Classify the type of CCNL update."""
        text = f"{title} {content}".lower()
        
        best_match = "unknown"
        highest_score = 0
        
        for update_type, patterns in self.update_type_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in text:
                    # Give more weight to matches in title
                    if pattern in title.lower():
                        score += 2
                    else:
                        score += 1
            
            if score > highest_score:
                highest_score = score
                best_match = update_type
        
        return best_match
    
    def calculate_priority(self, title: str, content: str = "", sector: Optional[CCNLSector] = None) -> float:
        """Calculate priority score for an update (0.0 to 1.0)."""
        priority = 0.5  # Base priority
        
        text = f"{title} {content}".lower()
        
        # High priority indicators
        high_priority_terms = [
            "milioni di lavoratori", "nazionale", "rinnovo ccnl", 
            "firmato", "siglato", "accordo raggiunto"
        ]
        
        for term in high_priority_terms:
            if term in text:
                priority += 0.1
        
        # Sector-based priority adjustments
        high_priority_sectors = [
            CCNLSector.METALMECCANICI_INDUSTRIA,
            CCNLSector.COMMERCIO_TERZIARIO,
            CCNLSector.EDILIZIA_INDUSTRIA
        ]
        
        if sector in high_priority_sectors:
            priority += 0.2
        
        # Source reliability bonus (would be implemented based on source)
        # This would be enhanced with actual source reliability metrics
        
        return min(1.0, priority)  # Cap at 1.0
    
    def calculate_confidence(self, matched_keywords: List[str], sector: Optional[CCNLSector], 
                           update_type: str) -> float:
        """Calculate confidence score for classification."""
        confidence = 0.0
        
        # Base confidence from keyword matches
        keyword_confidence = min(0.5, len(matched_keywords) * 0.1)
        confidence += keyword_confidence
        
        # Sector classification confidence
        if sector:
            confidence += 0.3
        
        # Update type confidence
        if update_type != "unknown":
            confidence += 0.2
        
        return min(1.0, confidence)
    
    async def detect_ccnl_updates(self, feed_items: List[RSSFeedItem]) -> List[CCNLDetection]:
        """Detect and classify CCNL updates from feed items."""
        detections = []
        
        for item in feed_items:
            full_text = f"{item.title} {item.description} {item.content or ''}"
            
            # Get matched keywords
            matched_keywords = []
            for keyword in ["rinnovo ccnl", "contratto collettivo", "accordo siglato"]:  # Simplified for now
                if keyword in full_text.lower():
                    matched_keywords.append(keyword)
            
            # Classify sector and update type
            sector = self.classify_sector(item.title, item.description)
            update_type = self.classify_update_type(item.title, item.description)
            priority = self.calculate_priority(item.title, item.description, sector)
            confidence = self.calculate_confidence(matched_keywords, sector, update_type)
            
            # Create detection if confidence is above threshold
            if confidence >= 0.3:  # Minimum confidence threshold
                detection = CCNLDetection(
                    feed_item=item,
                    sector=sector,
                    update_type=update_type,
                    confidence_score=confidence,
                    keywords_matched=matched_keywords,
                    priority=priority
                )
                detections.append(detection)
        
        # Sort by priority and confidence
        detections.sort(key=lambda d: (d.priority, d.confidence_score), reverse=True)
        
        logger.info(f"Detected {len(detections)} CCNL updates from {len(feed_items)} feed items")
        
        return detections
    
    async def ai_classify_update(self, title: str, content: str) -> Dict[str, Any]:
        """AI-powered classification of CCNL updates (mock implementation)."""
        # This would integrate with an actual AI/LLM service
        # For now, return a mock classification
        
        sector = self.classify_sector(title, content)
        update_type = self.classify_update_type(title, content)
        
        # Mock changes detection
        changes_detected = []
        if "aumento" in (title + content).lower():
            changes_detected.append("salary_increase")
        if "orario" in (title + content).lower():
            changes_detected.append("working_hours_change")
        
        return {
            "sector": sector.value if sector else "unknown",
            "update_type": update_type,
            "confidence": 0.85,
            "changes_detected": changes_detected,
            "summary": f"CCNL update detected for {sector.value if sector else 'unknown sector'}"
        }


class UpdateClassifier:
    """Enhanced classifier for CCNL updates using multiple methods."""
    
    def __init__(self):
        self.detector = CCNLUpdateDetector()
        self.confidence_threshold = 0.7
        self.ai_classification_enabled = True
    
    async def classify_update(self, feed_item: RSSFeedItem) -> Dict[str, Any]:
        """Classify a CCNL update using multiple methods."""
        
        # Rule-based classification
        sector = self.detector.classify_sector(feed_item.title, feed_item.description)
        update_type = self.detector.classify_update_type(feed_item.title, feed_item.description)
        priority = self.detector.calculate_priority(feed_item.title, feed_item.description, sector)
        
        # AI-enhanced classification (if enabled)
        ai_result = {}
        if self.ai_classification_enabled:
            ai_result = await self.detector.ai_classify_update(
                feed_item.title, 
                feed_item.description
            )
        
        # Combine results
        final_classification = {
            "sector": sector.value if sector else ai_result.get("sector", "unknown"),
            "update_type": update_type if update_type != "unknown" else ai_result.get("update_type", "unknown"),
            "priority": priority,
            "confidence": ai_result.get("confidence", 0.5),
            "changes_detected": ai_result.get("changes_detected", []),
            "classification_method": "hybrid" if ai_result else "rule_based"
        }
        
        return final_classification


# Global instances
rss_monitor = RSSFeedMonitor()
update_detector = CCNLUpdateDetector()
update_classifier = UpdateClassifier()