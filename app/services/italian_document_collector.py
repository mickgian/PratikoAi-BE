"""Italian Document Collector Service

Automated collection of official Italian government documents from RSS feeds and web sources.
Implements the dynamic knowledge pipeline: Official Sources → RSS/Scraping → Processing → Vector DB
"""

import asyncio
import hashlib
import logging
import re
from datetime import (
    UTC,
    datetime,
    timedelta,
    timezone,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)
from urllib.parse import (
    urljoin,
    urlparse,
)

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from sqlalchemy import (
    and_,
    or_,
)
from sqlmodel import (
    Session,
    select,
)

from app.core.config import settings
from app.core.logging import logger
from app.models.italian_data import (
    DocumentCategory,
    ItalianKnowledgeSource,
    ItalianOfficialDocument,
)
from app.services.database import database_service
from app.services.vector_service import vector_service

# Official Italian RSS feeds configuration
ITALIAN_RSS_FEEDS = {
    "agenzia_entrate": {
        "authority": "Agenzia delle Entrate",
        "feeds": {
            "circolari": "https://www.agenziaentrate.gov.it/portale/rss/circolari.xml",
            "risoluzioni": "https://www.agenziaentrate.gov.it/portale/rss/risoluzioni.xml",
            "provvedimenti": "https://www.agenziaentrate.gov.it/portale/rss/provvedimenti.xml",
        },
    },
    "mef": {
        "authority": "Ministero dell'Economia e delle Finanze",
        "feeds": {"comunicati": "http://www.finanze.gov.it/rss.xml"},
    },
    "inps": {
        "authority": "INPS",
        "feeds": {
            "circolari": "https://www.inps.it/rss/circolari.xml",
            "messaggi": "https://www.inps.it/rss/messaggi.xml",
        },
    },
    "gazzetta_ufficiale": {
        "authority": "Gazzetta Ufficiale",
        "feeds": {"generale": "https://www.gazzettaufficiale.it/gazzetta/rss"},
    },
}

# Keywords for tax type classification
TAX_KEYWORDS = {
    "iva": ["iva", "imposta valore aggiunto", "vat", "fatturazione elettronica"],
    "irpef": ["irpef", "reddito persone fisiche", "imposta reddito"],
    "ires": ["ires", "imposta società", "reddito società"],
    "ritenuta": ["ritenuta", "ritenuta acconto", "withholding"],
    "irap": ["irap", "regionale attività produttive"],
    "imu": ["imu", "municipale unica", "imposta immobiliare"],
    "bollo": ["bollo", "imposta bollo"],
}


class ItalianDocumentCollector:
    """Collector for Italian official documents from RSS feeds and web sources."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "PratikoAI-DocumentCollector/1.0 (Tax Professional Knowledge System)"}
        )
        self.logger = logging.getLogger(__name__)

    async def collect_all_documents(self) -> dict[str, Any]:
        """Collect documents from all configured RSS feeds."""
        self.logger.info("Starting Italian document collection from all RSS feeds")

        collection_results = {
            "sources_processed": 0,
            "feeds_processed": 0,
            "documents_found": 0,
            "new_documents": 0,
            "errors": [],
            "sources": {},
        }

        # Process each authority's feeds
        for source_key, source_config in ITALIAN_RSS_FEEDS.items():
            authority = source_config["authority"]
            feeds = source_config["feeds"]

            source_results = {
                "authority": authority,
                "feeds_processed": 0,
                "documents_found": 0,
                "new_documents": 0,
                "errors": [],
            }

            self.logger.info(f"Processing {authority} with {len(feeds)} feeds")

            # Process each feed for this authority
            for feed_type, feed_url in feeds.items():
                try:
                    feed_results = await self._process_rss_feed(feed_url, authority, feed_type)

                    source_results["feeds_processed"] += 1
                    source_results["documents_found"] += feed_results["documents_found"]
                    source_results["new_documents"] += feed_results["new_documents"]

                    if feed_results["errors"]:
                        source_results["errors"].extend(feed_results["errors"])

                    collection_results["feeds_processed"] += 1
                    collection_results["documents_found"] += feed_results["documents_found"]
                    collection_results["new_documents"] += feed_results["new_documents"]

                except Exception as e:
                    error_msg = f"Error processing {authority} {feed_type} feed: {str(e)}"
                    self.logger.error(error_msg)
                    source_results["errors"].append(error_msg)
                    collection_results["errors"].append(error_msg)

            collection_results["sources"][source_key] = source_results
            collection_results["sources_processed"] += 1

        # Update knowledge sources statistics
        await self._update_source_statistics()

        self.logger.info(
            f"Document collection complete: {collection_results['new_documents']} new documents "
            f"from {collection_results['sources_processed']} sources"
        )

        return collection_results

    async def _process_rss_feed(self, feed_url: str, authority: str, feed_type: str) -> dict[str, Any]:
        """Process a single RSS feed and extract documents."""
        self.logger.info(f"Processing RSS feed: {feed_url}")

        results = {
            "feed_url": feed_url,
            "authority": authority,
            "feed_type": feed_type,
            "documents_found": 0,
            "new_documents": 0,
            "errors": [],
        }

        try:
            # Parse RSS feed
            feed = feedparser.parse(feed_url)

            if feed.bozo and feed.bozo_exception:
                error_msg = f"RSS feed parsing error: {feed.bozo_exception}"
                self.logger.warning(error_msg)
                results["errors"].append(error_msg)

            if not feed.entries:
                self.logger.warning(f"No entries found in RSS feed: {feed_url}")
                return results

            results["documents_found"] = len(feed.entries)
            self.logger.info(f"Found {len(feed.entries)} entries in {authority} {feed_type} feed")

            # Process each entry
            for entry in feed.entries:
                try:
                    document = await self._process_rss_entry(entry, authority, feed_type, feed_url)
                    if document:
                        results["new_documents"] += 1

                        # Process document content asynchronously
                        asyncio.create_task(self._enhance_document_content(document.id))

                except Exception as e:
                    error_msg = f"Error processing RSS entry: {str(e)}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Failed to process RSS feed {feed_url}: {str(e)}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    async def _process_rss_entry(
        self, entry: Any, authority: str, feed_type: str, feed_url: str
    ) -> ItalianOfficialDocument | None:
        """Process a single RSS entry and create document record."""
        try:
            # Extract basic information
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()

            if not title or not link:
                self.logger.warning(f"Missing title or link in RSS entry from {authority}")
                return None

            # Parse publication date
            pub_date_str = entry.get("published", entry.get("pubDate", ""))
            publication_date = self._parse_date(pub_date_str)

            if not publication_date:
                publication_date = datetime.now(UTC)
                self.logger.warning(f"Could not parse publication date for {title}, using current time")

            # Generate document ID and check for duplicates
            document_id = self._generate_document_id(authority, title, link)
            content_hash = self._generate_content_hash(title, summary, link)

            # Check if document already exists
            async with database_service.get_session() as session:
                existing_doc = await session.exec(
                    select(ItalianOfficialDocument).where(
                        or_(
                            ItalianOfficialDocument.document_id == document_id,
                            ItalianOfficialDocument.content_hash == content_hash,
                        )
                    )
                )

                if existing_doc.first():
                    self.logger.debug(f"Document already exists: {title}")
                    return None

                # Classify document category
                category = self._classify_document_category(title, summary, feed_type)

                # Extract tax types and keywords
                tax_types = self._extract_tax_types(title, summary)
                keywords = self._extract_keywords(title, summary)

                # Create new document record
                document = ItalianOfficialDocument(
                    document_id=document_id,
                    title=title,
                    category=category,
                    authority=authority,
                    source_url=link,
                    rss_feed=feed_url,
                    summary=summary,
                    content_hash=content_hash,
                    publication_date=publication_date,
                    tax_types=tax_types,
                    keywords=keywords,
                    processing_status="pending",
                )

                session.add(document)
                await session.commit()
                await session.refresh(document)

                self.logger.info(f"Added new document: {title} from {authority}")
                return document

        except Exception as e:
            self.logger.error(f"Error processing RSS entry: {str(e)}")
            return None

    async def _enhance_document_content(self, document_id: int) -> None:
        """Enhance document with full content and vector indexing."""
        try:
            async with database_service.get_session() as session:
                document = await session.get(ItalianOfficialDocument, document_id)
                if not document:
                    return

                # Try to fetch full content from the source URL
                full_content = await self._fetch_document_content(document.source_url)

                if full_content:
                    document.full_content = full_content

                    # Re-extract keywords from full content
                    enhanced_keywords = self._extract_keywords(document.title, full_content)
                    document.keywords = list(set(document.keywords + enhanced_keywords))

                    # Update tax types from full content
                    enhanced_tax_types = self._extract_tax_types(document.title, full_content)
                    document.tax_types = list(set(document.tax_types + enhanced_tax_types))

                # Index in vector database
                if vector_service:
                    vector_content = f"{document.title}\n\n{document.summary or ''}\n\n{document.full_content or ''}"
                    vector_metadata = {
                        "document_id": document.document_id,
                        "authority": document.authority,
                        "category": document.category,
                        "publication_date": document.publication_date.isoformat(),
                        "tax_types": document.tax_types,
                        "source_url": document.source_url,
                    }

                    vector_id = await vector_service.add_document(
                        content=vector_content, metadata=vector_metadata, namespace="italian_documents"
                    )

                    if vector_id:
                        document.vector_id = vector_id
                        document.indexed_at = datetime.now(UTC)

                document.processing_status = "completed"
                document.last_updated = datetime.now(UTC)

                await session.commit()

                self.logger.info(f"Enhanced document content: {document.title}")

        except Exception as e:
            self.logger.error(f"Error enhancing document {document_id}: {str(e)}")

            # Update status to failed
            try:
                async with database_service.get_session() as session:
                    document = await session.get(ItalianOfficialDocument, document_id)
                    if document:
                        document.processing_status = "failed"
                        await session.commit()
            except Exception:
                pass

    async def _fetch_document_content(self, url: str) -> str | None:
        """Fetch full document content from URL."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Parse HTML content
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract text content
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            # Limit content size (vector DB limits)
            if len(text) > 50000:  # 50KB limit
                text = text[:50000] + "... [content truncated]"

            return text

        except Exception as e:
            self.logger.warning(f"Could not fetch content from {url}: {str(e)}")
            return None

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date string from RSS feed."""
        if not date_str:
            return None

        try:
            # Try standard RSS date formats
            return date_parser.parse(date_str)
        except Exception:
            try:
                # Try common Italian date formats
                return datetime.strptime(date_str, "%d/%m/%Y")
            except Exception:
                self.logger.warning(f"Could not parse date: {date_str}")
                return None

    def _generate_document_id(self, authority: str, title: str, link: str) -> str:
        """Generate unique document ID."""
        # Create ID from authority, title, and URL hash
        content = f"{authority}:{title}:{link}"
        hash_obj = hashlib.md5(content.encode("utf-8"))
        return f"{authority.lower().replace(' ', '_')}_{hash_obj.hexdigest()[:12]}"

    def _generate_content_hash(self, title: str, summary: str, link: str) -> str:
        """Generate content hash for duplicate detection."""
        content = f"{title}:{summary}:{link}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _classify_document_category(self, title: str, summary: str, feed_type: str) -> DocumentCategory:
        """Classify document into appropriate category."""
        title_lower = title.lower()
        summary_lower = (summary or "").lower()
        text = f"{title_lower} {summary_lower}"

        # Map feed types to categories
        feed_category_map = {
            "circolari": DocumentCategory.CIRCOLARE,
            "risoluzioni": DocumentCategory.RISOLUZIONE,
            "provvedimenti": DocumentCategory.PROVVEDIMENTO,
            "messaggi": DocumentCategory.MESSAGGIO,
            "comunicati": DocumentCategory.COMUNICATO,
        }

        if feed_type in feed_category_map:
            return feed_category_map[feed_type]

        # Classification based on content
        if any(word in text for word in ["circolare", "chiarimento"]):
            return DocumentCategory.CIRCOLARE
        elif any(word in text for word in ["risoluzione", "risposta"]):
            return DocumentCategory.RISOLUZIONE
        elif any(word in text for word in ["provvedimento", "direttiva"]):
            return DocumentCategory.PROVVEDIMENTO
        elif any(word in text for word in ["decreto", "dpr"]):
            return DocumentCategory.DECRETO
        elif any(word in text for word in ["legge", "dlgs"]):
            return DocumentCategory.LEGGE
        elif any(word in text for word in ["messaggio", "comunicazione"]):
            return DocumentCategory.MESSAGGIO
        else:
            return DocumentCategory.ALTRO

    def _extract_tax_types(self, title: str, content: str) -> list[str]:
        """Extract relevant tax types from document content."""
        text = f"{title} {content or ''}".lower()
        found_tax_types = []

        for tax_type, keywords in TAX_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                found_tax_types.append(tax_type)

        return found_tax_types

    def _extract_keywords(self, title: str, content: str) -> list[str]:
        """Extract relevant keywords from document content."""
        text = f"{title} {content or ''}".lower()

        # Common Italian tax and legal keywords
        keywords = [
            "imposta",
            "tassa",
            "tributo",
            "contributo",
            "aliquota",
            "detrazioni",
            "deduzioni",
            "dichiarazione",
            "versamento",
            "scadenza",
            "termine",
            "adempimento",
            "sanzione",
            "ravvedimento",
            "rimborso",
            "credito",
            "partita iva",
            "codice fiscale",
            "fatturazione",
            "cessione",
            "prestazione",
        ]

        found_keywords = []
        for keyword in keywords:
            if keyword in text:
                found_keywords.append(keyword)

        # Limit to most relevant keywords
        return found_keywords[:20]

    async def _update_source_statistics(self) -> None:
        """Update statistics for knowledge sources."""
        try:
            async with database_service.get_session() as session:
                # Update each configured source
                for _source_key, source_config in ITALIAN_RSS_FEEDS.items():
                    authority = source_config["authority"]

                    # Count documents collected from this authority
                    doc_count = await session.exec(
                        select(ItalianOfficialDocument).where(ItalianOfficialDocument.authority == authority)
                    )
                    total_docs = len(list(doc_count))

                    # Find or create knowledge source record
                    source = await session.exec(
                        select(ItalianKnowledgeSource).where(ItalianKnowledgeSource.authority == authority)
                    )
                    source_record = source.first()

                    if source_record:
                        source_record.documents_collected = total_docs
                        source_record.last_accessed = datetime.now(UTC)
                        source_record.updated_at = datetime.now(UTC)
                    else:
                        # Create new source record
                        feeds = source_config["feeds"]
                        main_feed = list(feeds.values())[0] if feeds else ""

                        source_record = ItalianKnowledgeSource(
                            source_name=f"{authority} RSS Feeds",
                            source_type="official",
                            authority=authority,
                            base_url=main_feed.split("/")[0] + "//" + main_feed.split("/")[2] if main_feed else "",
                            rss_url=main_feed,
                            content_types=list(feeds.keys()),
                            update_frequency="daily",
                            language="it",
                            data_format="RSS/XML",
                            description=f"Official RSS feeds from {authority}",
                            documents_collected=total_docs,
                        )
                        session.add(source_record)

                await session.commit()

        except Exception as e:
            self.logger.error(f"Error updating source statistics: {str(e)}")

    async def get_collection_status(self) -> dict[str, Any]:
        """Get status of document collection."""
        async with database_service.get_session() as session:
            # Count documents by authority
            authorities = {}
            for source_config in ITALIAN_RSS_FEEDS.values():
                authority = source_config["authority"]

                docs = await session.exec(
                    select(ItalianOfficialDocument).where(ItalianOfficialDocument.authority == authority)
                )
                doc_list = list(docs)

                authorities[authority] = {
                    "total_documents": len(doc_list),
                    "pending_processing": len([d for d in doc_list if d.processing_status == "pending"]),
                    "completed_processing": len([d for d in doc_list if d.processing_status == "completed"]),
                    "failed_processing": len([d for d in doc_list if d.processing_status == "failed"]),
                    "latest_document": max([d.publication_date for d in doc_list]) if doc_list else None,
                }

            # Overall statistics
            all_docs = await session.exec(select(ItalianOfficialDocument))
            all_docs_list = list(all_docs)

            return {
                "total_documents": len(all_docs_list),
                "authorities": authorities,
                "processing_status": {
                    "pending": len([d for d in all_docs_list if d.processing_status == "pending"]),
                    "completed": len([d for d in all_docs_list if d.processing_status == "completed"]),
                    "failed": len([d for d in all_docs_list if d.processing_status == "failed"]),
                },
                "collection_date_range": {
                    "earliest": min([d.collected_at for d in all_docs_list]) if all_docs_list else None,
                    "latest": max([d.collected_at for d in all_docs_list]) if all_docs_list else None,
                },
            }

    async def invalidate_cache_for_updates(self) -> None:
        """Invalidate relevant cache entries when new documents are added."""
        try:
            from app.services.cache import cache_service

            # Clear Italian knowledge related caches using patterns that might exist
            cache_patterns = [
                "llm_response:*italian*",
                "llm_response:*iva*",
                "llm_response:*tax*",
                "llm_response:*fiscal*",
                "llm_response:*legal*",
                "llm_response:*regulation*",
            ]

            total_cleared = 0
            for pattern in cache_patterns:
                cleared = await cache_service.clear_cache(pattern)
                total_cleared += cleared

            self.logger.info(f"Invalidated {total_cleared} cache entries after document updates")

        except Exception as e:
            self.logger.error(f"Error invalidating cache: {str(e)}")


# Global instance
italian_document_collector = ItalianDocumentCollector()


async def collect_italian_documents_task() -> None:
    """Scheduled task to collect Italian documents."""
    try:
        logger.info("Starting scheduled Italian document collection")

        results = await italian_document_collector.collect_all_documents()

        # Log summary
        logger.info(
            f"Document collection completed: {results['new_documents']} new documents, {len(results['errors'])} errors"
        )

        # Invalidate cache if new documents were added
        if results["new_documents"] > 0:
            await italian_document_collector.invalidate_cache_for_updates()

    except Exception as e:
        logger.error(f"Error in Italian document collection task: {str(e)}")
