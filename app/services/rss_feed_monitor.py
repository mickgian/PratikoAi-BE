"""
RSS Feed Monitor Service for Italian Regulatory Sources.

This service monitors RSS feeds from Italian authorities for new documents
and provides parsed feed data for the Dynamic Knowledge Collection System.
"""

import asyncio
import feedparser
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from app.core.logging import logger


class RSSFeedMonitor:
    """Monitor RSS feeds from Italian regulatory authorities."""
    
    # Configuration for Italian regulatory RSS feeds
    ITALIAN_RSS_FEEDS = {
        'agenzia_entrate': {
            'authority': 'Agenzia delle Entrate',
            'feeds': {
                'circolari': 'https://www.agenziaentrate.gov.it/portale/rss/circolari.xml',
                'risoluzioni': 'https://www.agenziaentrate.gov.it/portale/rss/risoluzioni.xml',
                'provvedimenti': 'https://www.agenziaentrate.gov.it/portale/rss/provvedimenti.xml'
            }
        },
        'inps': {
            'authority': 'INPS',
            'feeds': {
                'circolari': 'https://www.inps.it/rss/circolari.xml',
                'messaggi': 'https://www.inps.it/rss/messaggi.xml'
            }
        },
        'gazzetta_ufficiale': {
            'authority': 'Gazzetta Ufficiale',
            'feeds': {
                'serie_generale': 'https://www.gazzettaufficiale.it/rss/serie_generale.xml',
                'decreti': 'https://www.gazzettaufficiale.it/rss/decreti.xml'
            }
        },
        'governo': {
            'authority': 'Governo Italiano',
            'feeds': {
                'decreti_legge': 'https://www.governo.it/rss/decreti-legge.xml',
                'dpcm': 'https://www.governo.it/rss/dpcm.xml'
            }
        }
    }
    
    def __init__(self, timeout: int = 30):
        """Initialize RSS feed monitor.
        
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                'User-Agent': 'PratikoAI-RSS-Monitor/1.0 (https://pratiko.ai)',
                'Accept': 'application/rss+xml, application/xml, text/xml'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def parse_agenzia_entrate_feed(
        self, 
        feed_url: str, 
        source_type: str
    ) -> List[Dict[str, Any]]:
        """Parse Agenzia delle Entrate RSS feed.
        
        Args:
            feed_url: RSS feed URL
            source_type: Type of documents (circolari, risoluzioni, provvedimenti)
            
        Returns:
            List of parsed feed items
        """
        try:
            # Fetch and parse feed
            feed_data = await self._fetch_feed(feed_url)
            if not feed_data:
                return []
            
            feed = feedparser.parse(feed_data)
            results = []
            
            for entry in feed.entries:
                # Extract publication date
                published_date = self._parse_feed_date(
                    getattr(entry, 'published_parsed', None)
                )
                
                # Create standardized feed item
                item = {
                    'title': entry.title,
                    'url': entry.link,
                    'description': getattr(entry, 'description', ''),
                    'published_date': published_date,
                    'source': 'agenzia_entrate',
                    'source_type': source_type,
                    'guid': getattr(entry, 'guid', entry.link),
                    'authority': 'Agenzia delle Entrate'
                }
                
                # Extract document number from title if possible
                doc_number = self._extract_document_number(entry.title, 'agenzia_entrate')
                if doc_number:
                    item['document_number'] = doc_number
                
                results.append(item)
            
            logger.info(
                "agenzia_entrate_feed_parsed",
                feed_url=feed_url,
                source_type=source_type,
                items_count=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "agenzia_entrate_feed_parse_failed",
                feed_url=feed_url,
                source_type=source_type,
                error=str(e),
                exc_info=True
            )
            return []
    
    async def parse_inps_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Parse INPS RSS feed.
        
        Args:
            feed_url: RSS feed URL
            
        Returns:
            List of parsed feed items
        """
        try:
            feed_data = await self._fetch_feed(feed_url)
            if not feed_data:
                return []
            
            feed = feedparser.parse(feed_data)
            results = []
            
            for entry in feed.entries:
                published_date = self._parse_feed_date(
                    getattr(entry, 'published_parsed', None)
                )
                
                item = {
                    'title': entry.title,
                    'url': entry.link,
                    'description': getattr(entry, 'description', ''),
                    'published_date': published_date,
                    'source': 'inps',
                    'source_type': 'circolari',  # Most INPS documents are circolari
                    'guid': getattr(entry, 'guid', entry.link),
                    'authority': 'INPS'
                }
                
                # Extract document number
                doc_number = self._extract_document_number(entry.title, 'inps')
                if doc_number:
                    item['document_number'] = doc_number
                
                results.append(item)
            
            logger.info(
                "inps_feed_parsed",
                feed_url=feed_url,
                items_count=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "inps_feed_parse_failed",
                feed_url=feed_url,
                error=str(e),
                exc_info=True
            )
            return []
    
    async def parse_gazzetta_ufficiale_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Parse Gazzetta Ufficiale RSS feed.
        
        Args:
            feed_url: RSS feed URL
            
        Returns:
            List of parsed feed items
        """
        try:
            feed_data = await self._fetch_feed(feed_url)
            if not feed_data:
                return []
            
            feed = feedparser.parse(feed_data)
            results = []
            
            for entry in feed.entries:
                published_date = self._parse_feed_date(
                    getattr(entry, 'published_parsed', None)
                )
                
                # Determine document type from title
                source_type = self._determine_gazzetta_document_type(entry.title)
                
                item = {
                    'title': entry.title,
                    'url': entry.link,
                    'description': getattr(entry, 'description', ''),
                    'published_date': published_date,
                    'source': 'gazzetta_ufficiale',
                    'source_type': source_type,
                    'guid': getattr(entry, 'guid', entry.link),
                    'authority': 'Gazzetta Ufficiale'
                }
                
                results.append(item)
            
            logger.info(
                "gazzetta_ufficiale_feed_parsed",
                feed_url=feed_url,
                items_count=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "gazzetta_ufficiale_feed_parse_failed",
                feed_url=feed_url,
                error=str(e),
                exc_info=True
            )
            return []
    
    async def parse_feed_with_error_handling(self, feed_url: str) -> List[Dict[str, Any]]:
        """Parse any RSS feed with comprehensive error handling.
        
        Args:
            feed_url: RSS feed URL
            
        Returns:
            List of parsed feed items (empty list on error)
        """
        try:
            # Determine feed type and parse accordingly
            if 'agenziaentrate.gov.it' in feed_url:
                source_type = self._extract_agenzia_entrate_type(feed_url)
                return await self.parse_agenzia_entrate_feed(feed_url, source_type)
            elif 'inps.it' in feed_url:
                return await self.parse_inps_feed(feed_url)
            elif 'gazzettaufficiale.it' in feed_url:
                return await self.parse_gazzetta_ufficiale_feed(feed_url)
            else:
                # Generic RSS parsing
                return await self._parse_generic_feed(feed_url)
                
        except Exception as e:
            logger.error(
                "feed_parse_error_handling_failed",
                feed_url=feed_url,
                error=str(e),
                exc_info=True
            )
            return []
    
    async def get_all_italian_feeds(self) -> Dict[str, str]:
        """Get dictionary of all configured Italian RSS feeds.
        
        Returns:
            Dictionary mapping feed names to URLs
        """
        feeds = {}
        
        for authority, config in self.ITALIAN_RSS_FEEDS.items():
            for feed_type, url in config['feeds'].items():
                feed_name = f"{authority}_{feed_type}"
                feeds[feed_name] = url
        
        return feeds
    
    async def _fetch_feed(self, feed_url: str) -> Optional[str]:
        """Fetch RSS feed content via HTTP.
        
        Args:
            feed_url: RSS feed URL
            
        Returns:
            Feed content as string or None on error
        """
        if not self.session:
            raise RuntimeError("RSSFeedMonitor must be used as async context manager")
        
        try:
            async with self.session.get(feed_url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.debug("feed_fetched_successfully", feed_url=feed_url)
                    return content
                else:
                    logger.warning(
                        "feed_fetch_http_error",
                        feed_url=feed_url,
                        status_code=response.status
                    )
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("feed_fetch_timeout", feed_url=feed_url)
            return None
        except Exception as e:
            logger.error(
                "feed_fetch_failed",
                feed_url=feed_url,
                error=str(e),
                exc_info=True
            )
            return None
    
    def _parse_feed_date(self, date_tuple: Optional[tuple]) -> datetime:
        """Parse RSS feed date tuple into datetime object.
        
        Args:
            date_tuple: Date tuple from feedparser
            
        Returns:
            Parsed datetime (defaults to now if parsing fails)
        """
        if not date_tuple:
            return datetime.now(timezone.utc)
        
        try:
            # Convert time.struct_time to datetime
            return datetime(*date_tuple[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            logger.warning("failed_to_parse_feed_date", date_tuple=date_tuple)
            return datetime.now(timezone.utc)
    
    def _extract_document_number(self, title: str, source: str) -> Optional[str]:
        """Extract document number from title.
        
        Args:
            title: Document title
            source: Source authority
            
        Returns:
            Document number if found
        """
        import re
        
        if source == 'agenzia_entrate':
            # Match patterns like "Circolare n. 15/E", "Risoluzione n. 45/E"
            match = re.search(r'n\.\s*(\d+(?:/[A-Z])?)', title)
            if match:
                return match.group(1)
        
        elif source == 'inps':
            # Match patterns like "Circolare INPS n. 82"
            match = re.search(r'n\.\s*(\d+)', title)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_agenzia_entrate_type(self, feed_url: str) -> str:
        """Extract document type from Agenzia Entrate feed URL.
        
        Args:
            feed_url: RSS feed URL
            
        Returns:
            Document type (circolari, risoluzioni, provvedimenti)
        """
        if 'circolari' in feed_url:
            return 'circolari'
        elif 'risoluzioni' in feed_url:
            return 'risoluzioni'
        elif 'provvedimenti' in feed_url:
            return 'provvedimenti'
        else:
            return 'documenti'
    
    def _determine_gazzetta_document_type(self, title: str) -> str:
        """Determine document type from Gazzetta Ufficiale title.
        
        Args:
            title: Document title
            
        Returns:
            Document type classification
        """
        title_lower = title.lower()
        
        if 'decreto legislativo' in title_lower:
            return 'decreto_legislativo'
        elif 'decreto legge' in title_lower:
            return 'decreto_legge'
        elif 'legge' in title_lower:
            return 'legge'
        elif 'dpcm' in title_lower or 'decreto del presidente' in title_lower:
            return 'dpcm'
        elif 'circolare' in title_lower:
            return 'circolare'
        else:
            return 'atto_normativo'
    
    async def _parse_generic_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Parse generic RSS feed when specific parser not available.
        
        Args:
            feed_url: RSS feed URL
            
        Returns:
            List of parsed feed items
        """
        try:
            feed_data = await self._fetch_feed(feed_url)
            if not feed_data:
                return []
            
            feed = feedparser.parse(feed_data)
            results = []
            
            # Extract domain for source identification
            parsed_url = urlparse(feed_url)
            domain = parsed_url.netloc.lower()
            
            for entry in feed.entries:
                published_date = self._parse_feed_date(
                    getattr(entry, 'published_parsed', None)
                )
                
                item = {
                    'title': entry.title,
                    'url': entry.link,
                    'description': getattr(entry, 'description', ''),
                    'published_date': published_date,
                    'source': domain.replace('.', '_'),
                    'source_type': 'documento',
                    'guid': getattr(entry, 'guid', entry.link),
                    'authority': domain
                }
                
                results.append(item)
            
            logger.info(
                "generic_feed_parsed",
                feed_url=feed_url,
                domain=domain,
                items_count=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "generic_feed_parse_failed",
                feed_url=feed_url,
                error=str(e),
                exc_info=True
            )
            return []


class FeedHealthMonitor:
    """Monitor health and status of RSS feeds."""
    
    def __init__(self):
        self.feed_status = {}
    
    async def check_feed_health(self, feed_url: str) -> Dict[str, Any]:
        """Check health status of an RSS feed.
        
        Args:
            feed_url: RSS feed URL to check
            
        Returns:
            Health status information
        """
        try:
            async with RSSFeedMonitor() as monitor:
                start_time = datetime.now()
                
                # Attempt to fetch and parse feed
                results = await monitor.parse_feed_with_error_handling(feed_url)
                
                response_time = (datetime.now() - start_time).total_seconds()
                
                status = {
                    'url': feed_url,
                    'status': 'healthy' if results else 'unhealthy',
                    'response_time_seconds': response_time,
                    'items_count': len(results),
                    'last_checked': datetime.now(timezone.utc),
                    'error': None
                }
                
                # Store status
                self.feed_status[feed_url] = status
                
                return status
                
        except Exception as e:
            error_status = {
                'url': feed_url,
                'status': 'error',
                'response_time_seconds': None,
                'items_count': 0,
                'last_checked': datetime.now(timezone.utc),
                'error': str(e)
            }
            
            self.feed_status[feed_url] = error_status
            
            logger.error(
                "feed_health_check_failed",
                feed_url=feed_url,
                error=str(e),
                exc_info=True
            )
            
            return error_status
    
    async def check_all_italian_feeds_health(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all configured Italian RSS feeds.
        
        Returns:
            Dictionary mapping feed names to health status
        """
        async with RSSFeedMonitor() as monitor:
            feeds = await monitor.get_all_italian_feeds()
            
            health_results = {}
            
            # Check feeds concurrently
            tasks = []
            for feed_name, feed_url in feeds.items():
                task = asyncio.create_task(
                    self.check_feed_health(feed_url),
                    name=f"health_check_{feed_name}"
                )
                tasks.append((feed_name, task))
            
            # Wait for all health checks to complete
            for feed_name, task in tasks:
                try:
                    health_status = await task
                    health_results[feed_name] = health_status
                except Exception as e:
                    logger.error(
                        "feed_health_check_task_failed",
                        feed_name=feed_name,
                        error=str(e)
                    )
                    health_results[feed_name] = {
                        'url': feeds.get(feed_name, ''),
                        'status': 'error',
                        'error': str(e),
                        'last_checked': datetime.now(timezone.utc)
                    }
            
            return health_results
    
    def get_feed_status_summary(self) -> Dict[str, Any]:
        """Get summary of feed health status.
        
        Returns:
            Summary statistics
        """
        if not self.feed_status:
            return {
                'total_feeds': 0,
                'healthy_feeds': 0,
                'unhealthy_feeds': 0,
                'error_feeds': 0,
                'average_response_time': None
            }
        
        total = len(self.feed_status)
        healthy = sum(1 for status in self.feed_status.values() if status['status'] == 'healthy')
        unhealthy = sum(1 for status in self.feed_status.values() if status['status'] == 'unhealthy')
        error = sum(1 for status in self.feed_status.values() if status['status'] == 'error')
        
        # Calculate average response time for successful checks
        response_times = [
            status['response_time_seconds'] 
            for status in self.feed_status.values() 
            if status['response_time_seconds'] is not None
        ]
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            'total_feeds': total,
            'healthy_feeds': healthy,
            'unhealthy_feeds': unhealthy,
            'error_feeds': error,
            'average_response_time': round(avg_response_time, 3) if avg_response_time else None,
            'last_updated': datetime.now(timezone.utc)
        }


# Create shared instances
rss_feed_monitor = RSSFeedMonitor()
feed_health_monitor = FeedHealthMonitor()