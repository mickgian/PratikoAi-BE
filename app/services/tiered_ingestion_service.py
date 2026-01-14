"""Tiered Document Ingestion Service (ADR-023).

Orchestrates document classification, parsing, and storage based on tier.

Usage:
    from app.services.tiered_ingestion_service import TieredIngestionService

    async with AsyncSessionLocal() as db:
        service = TieredIngestionService(db_session=db)
        result = await service.ingest(
            title="LEGGE 30 dicembre 2025, n. 199",
            content=law_text,
            source="gazzetta_ufficiale",
        )
        print(f"Created {result.items_created} items ({result.articles_parsed} articles)")
"""

import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.knowledge import KnowledgeItem
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.document_classifier import (
    ClassificationResult,
    DocumentClassifier,
    DocumentTier,
    ParsingStrategy,
)
from app.services.italian_law_parser import ItalianLawParser, ParsedLaw

# Default chunk size for standard chunking
DEFAULT_CHUNK_SIZE = 1500
DEFAULT_CHUNK_OVERLAP = 150


@dataclass
class IngestionResult:
    """Result of tiered ingestion.

    Attributes:
        document_id: ID of the parent document (for Tier 1) or first chunk
        tier: Assigned tier (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE)
        items_created: Total number of knowledge items created
        articles_parsed: Number of articles parsed (Tier 1 only)
        topics_detected: List of detected topics
        parsing_strategy: Strategy used (article_level, standard_chunking, light_indexing)
    """

    document_id: int | None
    tier: int
    items_created: int
    articles_parsed: int
    topics_detected: list[str]
    parsing_strategy: str


class TieredIngestionService:
    """Service for tiered document ingestion.

    Routes documents to appropriate ingestion strategies based on tier:
    - Tier 1 (CRITICAL): Article-level parsing for laws, with topic tagging
    - Tier 2 (IMPORTANT): Standard chunking for circulars and guidance
    - Tier 3 (REFERENCE): Light indexing for news and communications

    Example:
        async with AsyncSessionLocal() as db:
            service = TieredIngestionService(db_session=db)

            # Ingest a critical law
            result = await service.ingest(
                title="LEGGE 30 dicembre 2025, n. 199",
                content=law_content,
                source="gazzetta_ufficiale",
                publication_date="2025-12-30",
            )

            print(f"Tier: {result.tier}")
            print(f"Articles: {result.articles_parsed}")
            print(f"Topics: {result.topics_detected}")
    """

    def __init__(
        self,
        db_session: AsyncSession,
        classifier: DocumentClassifier | None = None,
        law_parser: ItalianLawParser | None = None,
    ):
        """Initialize the ingestion service.

        Args:
            db_session: Async SQLAlchemy session for database operations
            classifier: DocumentClassifier instance (created if None)
            law_parser: ItalianLawParser instance (created if None)
        """
        self._db = db_session
        self._classifier = classifier or DocumentClassifier()
        self._law_parser = law_parser or ItalianLawParser()

    async def ingest(
        self,
        title: str,
        content: str,
        source: str,
        publication_date: str | date | None = None,
        category: str = "documento",
        metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """Ingest a document with appropriate tier handling.

        Classifies the document, then routes to the appropriate ingestion
        strategy based on the assigned tier.

        Args:
            title: Document title
            content: Full document content
            source: Source identifier (e.g., "gazzetta_ufficiale")
            publication_date: Publication date (string "YYYY-MM-DD" or date object)
            category: Document category for classification
            metadata: Additional metadata to store

        Returns:
            IngestionResult with ingestion details
        """
        # 1. Classify document
        classification = self._classifier.classify(
            title=title,
            source=source,
            content_preview=content[:500],
        )

        logger.info(
            "tiered_ingestion_classified",
            title=title[:100],
            tier=classification.tier.value,
            strategy=classification.parsing_strategy,
            confidence=classification.confidence,
            topics=classification.detected_topics,
        )

        # Parse publication date
        pub_date = self._parse_date(publication_date)

        # 2. Route to appropriate ingestion strategy
        if classification.parsing_strategy == ParsingStrategy.ARTICLE_LEVEL:
            return await self._ingest_article_level(
                title, content, source, pub_date, category, metadata, classification
            )
        elif classification.parsing_strategy == ParsingStrategy.STANDARD_CHUNKING:
            return await self._ingest_standard_chunking(
                title, content, source, pub_date, category, metadata, classification
            )
        else:
            return await self._ingest_light_indexing(
                title, content, source, pub_date, category, metadata, classification
            )

    async def _ingest_article_level(
        self,
        title: str,
        content: str,
        source: str,
        publication_date: date | None,
        category: str,
        metadata: dict[str, Any] | None,
        classification: ClassificationResult,
    ) -> IngestionResult:
        """Tier 1: Article-level parsing for critical documents.

        Parses the law into individual articles, each stored as a separate
        knowledge item with parent-child relationships.
        """
        # Parse law into articles
        parsed_law = self._law_parser.parse(content, title)

        # Create parent document record (stores reference to full law)
        parent_doc = KnowledgeItem(
            title=title,
            content=content[:10000],  # Store first 10k chars as reference
            source=source,
            category=category,
            publication_date=publication_date,
            tier=DocumentTier.CRITICAL,
            document_type="full_document",
            topics=classification.detected_topics,
            parsing_metadata={
                "law_number": parsed_law.law_number,
                "articles_count": len(parsed_law.articles),
                "allegati_count": len(parsed_law.allegati),
                "confidence": classification.confidence,
                "matched_pattern": classification.matched_pattern,
            },
            extra_metadata=metadata or {},
        )
        self._db.add(parent_doc)
        await self._db.flush()  # Get the ID

        items_created = 1
        all_topics = set(classification.detected_topics)

        # Create article records with corresponding chunks for FTS
        chunks_created = 0
        for article in parsed_law.articles:
            # Combine document-level and article-level topics
            article_topics = list(set(classification.detected_topics + article.topics))
            all_topics.update(article.topics)

            article_doc = KnowledgeItem(
                title=f"{title} - {article.display_title}",
                content=article.full_text,
                source=source,
                category=category,
                publication_date=publication_date,
                tier=DocumentTier.CRITICAL,
                parent_document_id=parent_doc.id,
                article_number=article.article_number,
                document_type="article",
                topics=article_topics,
                parsing_metadata={
                    "titolo": article.titolo,
                    "capo": article.capo,
                    "cross_references": article.cross_references,
                    "commi_count": len(article.commi),
                },
            )
            self._db.add(article_doc)
            await self._db.flush()  # Get the article ID for chunk linkage
            items_created += 1

            # DEV-242 ADR-023: Create KnowledgeChunk(s) for FTS search compatibility
            # The search queries knowledge_chunks with search_vector, so we need
            # to create chunks for each article to make them searchable.
            # DEV-242 Phase 5: Split large articles into multiple chunks so that
            # relevant content (e.g., rottamazione provisions at position 53K+)
            # can be found by FTS and sent to LLM without truncation.
            if article.full_text:
                article_text = article.full_text
                doc_title = f"{title} - {article.display_title}"

                # Split large articles into multiple chunks for better RAG retrieval
                if len(article_text) > DEFAULT_CHUNK_SIZE * 2:
                    # Large article: split into overlapping chunks
                    text_chunks = self._chunk_text(article_text, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)
                    for i, chunk_text in enumerate(text_chunks):
                        chunk = KnowledgeChunk(
                            knowledge_item_id=article_doc.id,
                            chunk_text=chunk_text,
                            chunk_index=i,
                            token_count=len(chunk_text.split()),
                            kb_epoch=time.time(),
                            document_title=doc_title,
                            junk=False,
                        )
                        self._db.add(chunk)
                        chunks_created += 1
                else:
                    # Small article: single chunk
                    chunk = KnowledgeChunk(
                        knowledge_item_id=article_doc.id,
                        chunk_text=article_text,
                        chunk_index=0,
                        token_count=len(article_text.split()),
                        kb_epoch=time.time(),
                        document_title=doc_title,
                        junk=False,
                    )
                    self._db.add(chunk)
                    chunks_created += 1

        # Create allegati records
        for allegato in parsed_law.allegati:
            allegato_doc = KnowledgeItem(
                title=f"{title} - Allegato {allegato['id']}",
                content=f"Allegato {allegato['id']}: {allegato.get('title', '')}",
                source=source,
                category=category,
                tier=DocumentTier.CRITICAL,
                parent_document_id=parent_doc.id,
                document_type="allegato",
                parsing_metadata=allegato,
            )
            self._db.add(allegato_doc)
            items_created += 1

        await self._db.commit()

        logger.info(
            "tiered_ingestion_article_level_complete",
            title=title[:100],
            parent_id=parent_doc.id,
            items_created=items_created,
            chunks_created=chunks_created,
            articles_parsed=len(parsed_law.articles),
            topics=list(all_topics),
        )

        return IngestionResult(
            document_id=parent_doc.id,
            tier=DocumentTier.CRITICAL,
            items_created=items_created,
            articles_parsed=len(parsed_law.articles),
            topics_detected=list(all_topics),
            parsing_strategy=ParsingStrategy.ARTICLE_LEVEL,
        )

    async def _ingest_standard_chunking(
        self,
        title: str,
        content: str,
        source: str,
        publication_date: date | None,
        category: str,
        metadata: dict[str, Any] | None,
        classification: ClassificationResult,
    ) -> IngestionResult:
        """Tier 2: Standard chunking for important documents.

        Splits content into overlapping chunks, preserving context.
        """
        chunks = self._chunk_text(content, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)
        items_created = 0
        first_id = None

        for i, chunk in enumerate(chunks):
            chunk_doc = KnowledgeItem(
                title=title,
                content=chunk,
                source=source,
                category=category,
                publication_date=publication_date,
                tier=DocumentTier.IMPORTANT,
                document_type="chunk",
                topics=classification.detected_topics,
                parsing_metadata={
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "confidence": classification.confidence,
                },
                extra_metadata=metadata or {},
            )
            self._db.add(chunk_doc)
            await self._db.flush()

            if i == 0:
                first_id = chunk_doc.id
            items_created += 1

        await self._db.commit()

        logger.info(
            "tiered_ingestion_standard_chunking_complete",
            title=title[:100],
            items_created=items_created,
            chunks=len(chunks),
        )

        return IngestionResult(
            document_id=first_id,
            tier=DocumentTier.IMPORTANT,
            items_created=items_created,
            articles_parsed=0,
            topics_detected=classification.detected_topics,
            parsing_strategy=ParsingStrategy.STANDARD_CHUNKING,
        )

    async def _ingest_light_indexing(
        self,
        title: str,
        content: str,
        source: str,
        publication_date: date | None,
        category: str,
        metadata: dict[str, Any] | None,
        classification: ClassificationResult,
    ) -> IngestionResult:
        """Tier 3: Light indexing for reference documents.

        Single record with truncated content for quick lookups.
        """
        # Store first 5000 chars
        doc = KnowledgeItem(
            title=title,
            content=content[:5000],
            source=source,
            category=category,
            publication_date=publication_date,
            tier=DocumentTier.REFERENCE,
            document_type="chunk",
            topics=classification.detected_topics,
            parsing_metadata={
                "original_length": len(content),
                "confidence": classification.confidence,
            },
            extra_metadata=metadata or {},
        )
        self._db.add(doc)
        await self._db.commit()

        logger.info(
            "tiered_ingestion_light_indexing_complete",
            title=title[:100],
            content_length=len(content),
        )

        return IngestionResult(
            document_id=doc.id,
            tier=DocumentTier.REFERENCE,
            items_created=1,
            articles_parsed=0,
            topics_detected=classification.detected_topics,
            parsing_strategy=ParsingStrategy.LIGHT_INDEXING,
        )

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size

            # Find a good break point (sentence end, paragraph)
            if end < text_length:
                # Try to find paragraph break
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + chunk_size // 2:
                    end = para_break + 2
                else:
                    # Try sentence break
                    for sep in [". ", ".\n", "? ", "! "]:
                        sentence_break = text.rfind(sep, start, end)
                        if sentence_break > start + chunk_size // 2:
                            end = sentence_break + len(sep)
                            break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap
            start = end - overlap if end - overlap > start else end

        return chunks

    def _parse_date(self, date_value: str | date | None) -> date | None:
        """Parse date from string or return as-is if already date.

        Args:
            date_value: Date string (YYYY-MM-DD) or date object

        Returns:
            date object or None
        """
        if date_value is None:
            return None
        if isinstance(date_value, date):
            return date_value
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Invalid date format: {date_value}")
                return None
        return None

    async def delete_existing_documents(self, title_pattern: str) -> int:
        """Delete existing documents matching a title pattern.

        Useful for re-ingesting updated documents.

        Args:
            title_pattern: SQL LIKE pattern (e.g., "%LEGGE 30 dicembre 2025%")

        Returns:
            Number of records deleted
        """
        result = await self._db.execute(
            text("DELETE FROM knowledge_items WHERE title ILIKE :pattern RETURNING id"),
            {"pattern": title_pattern},
        )
        deleted = result.rowcount
        await self._db.commit()

        logger.info(
            "tiered_ingestion_deleted_existing",
            pattern=title_pattern,
            count=deleted,
        )

        return deleted
