"""Scrapers package for Italian regulatory document sources.

This package contains web scrapers for Italian legal and regulatory sources
that do not provide RSS feeds, requiring direct web scraping.

Scrapers:
- GazzettaScraper: Italian Official Gazette (Gazzetta Ufficiale)
- CassazioneScraper: Italian Supreme Court decisions (Corte di Cassazione)

All scrapers:
- Respect robots.txt
- Implement rate limiting
- Support GDPR compliance
- Integrate with knowledge base
"""

from app.services.scrapers.cassazione_scraper import CassazioneScraper
from app.services.scrapers.gazzetta_scraper import GazzettaScraper

__all__ = [
    "CassazioneScraper",
    "GazzettaScraper",
]
