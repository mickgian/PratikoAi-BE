"""Knowledge Integration Service for Dynamic Knowledge Collection.

This service integrates new regulatory documents into the knowledge base,
handles updates, manages citations, and invalidates relevant caches.
"""

import hashlib
import time
from datetime import (
    UTC,
    datetime,
    timezone,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    and_,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chunking import chunk_document
from app.core.embed import (
    embedding_to_pgvector,
    generate_embedding,
)
from app.core.logging import logger
from app.models.knowledge import KnowledgeItem
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.cache import cache_service


class KnowledgeIntegrator:
    """Integrate regulatory documents into the knowledge base."""

    def __init__(self, db_session: AsyncSession):
        """Initialize knowledge integrator.

        Args:
            db_session: Database session for operations
        """
        self.db = db_session
        self.italian_months = {
            "gennaio": "01",
            "febbraio": "02",
            "marzo": "03",
            "aprile": "04",
            "maggio": "05",
            "giugno": "06",
            "luglio": "07",
            "agosto": "08",
            "settembre": "09",
            "ottobre": "10",
            "novembre": "11",
            "dicembre": "12",
        }

    async def update_knowledge_base(self, document_data: dict[str, Any]) -> dict[str, Any]:
        """Update knowledge base with new regulatory document.

        Args:
            document_data: Dictionary containing document information

        Returns:
            Result dictionary with success status and document ID
        """
        try:
            # Generate content hash for duplicate detection
            content_hash = self._generate_content_hash(document_data.get("content", ""))

            # Check if document already exists
            existing_doc = await self._find_existing_document(document_data.get("url", ""), content_hash)

            if existing_doc:
                # Document already exists, check if update is needed
                if existing_doc.content_hash != content_hash:
                    # Content has changed, create new version
                    result = await self.handle_document_update(document_data)
                    return result
                else:
                    logger.info("document_already_exists", url=document_data.get("url"), existing_id=existing_doc.id)
                    return {
                        "success": True,
                        "action": "skipped",
                        "document_id": str(existing_doc.id),
                        "reason": "Document already exists with same content",
                    }

            # Create new knowledge item
            kb_epoch = time.time()
            content = document_data.get("content", "")

            # Generate embedding for full content
            content_for_embedding = content[:30000]  # ~8k tokens
            embedding_vec = await generate_embedding(content_for_embedding)
            # For asyncpg, pass embedding list directly (not string format)
            embedding_data = embedding_vec if embedding_vec else None

            knowledge_item = KnowledgeItem(
                title=document_data.get("title", ""),
                content=content,
                category=self._determine_knowledge_category(document_data),
                subcategory=self._determine_knowledge_subcategory(document_data),
                source="regulatory_update",
                source_url=document_data.get("url", ""),
                content_hash=content_hash,
                extra_metadata=await self._prepare_metadata(document_data),
                relevance_score=self._calculate_relevance_score(document_data),
                language="it",
                status="active",
                kb_epoch=kb_epoch,
                embedding=embedding_data,
            )

            # Add to database
            self.db.add(knowledge_item)
            await self.db.flush()  # Get the ID before creating chunks

            # Chunk the document and create chunk records
            title = document_data.get("title", "")
            url = document_data.get("url", "")
            chunks = chunk_document(content=content, title=title, max_tokens=512, overlap_tokens=50)

            # Create KnowledgeChunk records with embeddings
            for chunk_dict in chunks:
                chunk_text = chunk_dict["chunk_text"]

                # Generate embedding for chunk
                chunk_embedding_vec = await generate_embedding(chunk_text)
                # For asyncpg, pass embedding list directly (not string format)
                chunk_embedding_data = chunk_embedding_vec if chunk_embedding_vec else None

                knowledge_chunk = KnowledgeChunk(
                    knowledge_item_id=knowledge_item.id,
                    chunk_text=chunk_text,
                    chunk_index=chunk_dict["chunk_index"],
                    token_count=chunk_dict["token_count"],
                    embedding=chunk_embedding_data,
                    kb_epoch=kb_epoch,
                    source_url=url,
                    document_title=title,
                    # Quality tracking from chunker
                    quality_score=chunk_dict.get("quality_score"),
                    junk=chunk_dict.get("junk", False),
                    ocr_used=chunk_dict.get("ocr_used", False),
                    start_char=chunk_dict.get("start_char"),
                    end_char=chunk_dict.get("end_char"),
                    created_at=datetime.now(UTC),
                )

                self.db.add(knowledge_chunk)

            await self.db.commit()
            await self.db.refresh(knowledge_item)

            logger.info(
                "knowledge_item_created_with_chunks", knowledge_item_id=knowledge_item.id, chunk_count=len(chunks)
            )

            # Also create regulatory document record
            await self._create_regulatory_document(document_data, knowledge_item.id)

            # Invalidate relevant caches
            await self.invalidate_relevant_caches(
                topics=document_data.get("metadata", {}).get("topics", []), source=document_data.get("source", "")
            )

            logger.info(
                "knowledge_base_updated",
                document_id=knowledge_item.id,
                title=document_data.get("title", "")[:100],
                category=knowledge_item.category,
            )

            return {
                "success": True,
                "action": "created",
                "document_id": str(knowledge_item.id),
                "knowledge_item_id": knowledge_item.id,
            }

        except Exception as e:
            await self.db.rollback()
            logger.error("knowledge_base_update_failed", document_data=document_data, error=str(e), exc_info=True)
            return {"success": False, "error": str(e), "action": "failed"}

    async def handle_document_update(self, document_data: dict[str, Any]) -> dict[str, Any]:
        """Handle document updates and versioning.

        Args:
            document_data: Updated document information

        Returns:
            Result dictionary with update information
        """
        try:
            # Find existing document
            existing_query = (
                select(KnowledgeItem)
                .where(KnowledgeItem.source_url == document_data.get("url", ""))
                .order_by(KnowledgeItem.created_at.desc())
            )

            result = await self.db.execute(existing_query)
            existing_item = result.scalar_one_or_none()

            if not existing_item:
                # No existing document, create new one
                return await self.update_knowledge_base(document_data)

            # Create new version with incremented version number
            new_version = getattr(existing_item, "version", 1) + 1
            new_content_hash = self._generate_content_hash(document_data.get("content", ""))

            # Prepare metadata for updated item
            prepared_metadata = await self._prepare_metadata(document_data)

            # Generate kb_epoch and embeddings
            kb_epoch = time.time()
            content = document_data.get("content", "")
            content_for_embedding = content[:30000]
            embedding_vec = await generate_embedding(content_for_embedding)
            # For asyncpg, pass embedding list directly (not string format)
            embedding_data = embedding_vec if embedding_vec else None

            # Create updated knowledge item
            updated_item = KnowledgeItem(
                title=document_data.get("title", "") + " (Aggiornata)",
                content=content,
                category=existing_item.category,
                subcategory=existing_item.subcategory,
                source=existing_item.source,
                source_url=document_data.get("url", ""),
                content_hash=new_content_hash,
                extra_metadata={
                    **existing_item.extra_metadata,
                    **prepared_metadata,
                    "version": new_version,
                    "previous_version_id": existing_item.id,
                },
                relevance_score=self._calculate_relevance_score(document_data),
                language="it",
                status="active",
                kb_epoch=kb_epoch,
                embedding=embedding_data,
            )

            # Mark old version as superseded
            existing_item.status = "superseded"
            existing_item.extra_metadata = {
                **existing_item.extra_metadata,
                "superseded_by": new_version,
                "superseded_at": datetime.now(UTC).isoformat(),
            }

            # Add new version to database
            self.db.add(updated_item)
            await self.db.flush()  # Get ID for chunks

            # Chunk the document and create chunk records
            title = document_data.get("title", "")
            url = document_data.get("url", "")
            chunks = chunk_document(content=content, title=title, max_tokens=512, overlap_tokens=50)

            # Create KnowledgeChunk records with embeddings
            for chunk_dict in chunks:
                chunk_text = chunk_dict["chunk_text"]

                # Generate embedding for chunk
                chunk_embedding_vec = await generate_embedding(chunk_text)
                # For asyncpg, pass embedding list directly (not string format)
                chunk_embedding_data = chunk_embedding_vec if chunk_embedding_vec else None

                knowledge_chunk = KnowledgeChunk(
                    knowledge_item_id=updated_item.id,
                    chunk_text=chunk_text,
                    chunk_index=chunk_dict["chunk_index"],
                    token_count=chunk_dict["token_count"],
                    embedding=chunk_embedding_data,
                    kb_epoch=kb_epoch,
                    source_url=url,
                    document_title=title,
                    quality_score=chunk_dict.get("quality_score"),
                    junk=chunk_dict.get("junk", False),
                    ocr_used=chunk_dict.get("ocr_used", False),
                    start_char=chunk_dict.get("start_char"),
                    end_char=chunk_dict.get("end_char"),
                    created_at=datetime.now(UTC),
                )

                self.db.add(knowledge_chunk)

            await self.db.commit()
            await self.db.refresh(updated_item)

            logger.info(
                "knowledge_item_updated_with_chunks",
                knowledge_item_id=updated_item.id,
                chunk_count=len(chunks),
                version=new_version,
            )

            # Update regulatory document record
            await self._update_regulatory_document(document_data, updated_item.id, new_version)

            # Invalidate caches
            await self.invalidate_relevant_caches(
                topics=document_data.get("metadata", {}).get("topics", []), source=document_data.get("source", "")
            )

            logger.info(
                "document_updated_with_versioning",
                new_document_id=updated_item.id,
                previous_document_id=existing_item.id,
                version=new_version,
            )

            return {
                "success": True,
                "action": "updated",
                "document_id": str(updated_item.id),
                "version": new_version,
                "previous_version_id": str(existing_item.id),
            }

        except Exception as e:
            await self.db.rollback()
            logger.error("document_update_failed", url=document_data.get("url"), error=str(e), exc_info=True)
            return {"success": False, "action": "update_failed", "error": str(e)}

    async def create_citation_data(self, document_data: dict[str, Any]) -> dict[str, Any]:
        """Create proper citation data for regulatory documents.

        Args:
            document_data: Document information

        Returns:
            Citation data dictionary
        """
        try:
            # Extract document type and number
            title = document_data.get("title", "")
            source = document_data.get("source", "")
            document_number = document_data.get("document_number", "")
            published_date = document_data.get("published_date")

            # Determine authority name
            authority_names = {
                "agenzia_entrate": "Agenzia delle Entrate",
                "inps": "INPS",
                "gazzetta_ufficiale": "Gazzetta Ufficiale",
                "governo": "Governo Italiano",
            }

            authority = authority_names.get(source, source.replace("_", " ").title())

            # Determine document type
            doc_type = "Documento"
            if "circolare" in title.lower():
                doc_type = "Circolare"
            elif "risoluzione" in title.lower():
                doc_type = "Risoluzione"
            elif "decreto" in title.lower():
                doc_type = "Decreto"
            elif "provvedimento" in title.lower():
                doc_type = "Provvedimento"

            # Format published date
            formatted_date = self._format_italian_date(published_date)

            # Create citation formats
            short_citation = f"{doc_type} {authority[:2].upper()} n. {document_number}/{published_date.year if published_date else ''}"
            full_citation = f"{authority}, {doc_type} n. {document_number} del {formatted_date}"

            citation_data = {
                "title": title,
                "source": authority,
                "document_type": doc_type,
                "document_number": document_number,
                "published_date": formatted_date,
                "url": document_data.get("url", ""),
                "short_citation": short_citation,
                "full_citation": full_citation,
            }

            return citation_data

        except Exception as e:
            logger.error("citation_creation_failed", document_data=document_data, error=str(e), exc_info=True)
            return {
                "title": document_data.get("title", ""),
                "source": document_data.get("source", ""),
                "error": str(e),
            }

    async def invalidate_relevant_caches(self, topics: list[str], source: str) -> None:
        """Invalidate caches related to the new document.

        Args:
            topics: List of document topics/keywords
            source: Document source authority
        """
        try:
            cache_patterns = []

            # Add topic-based cache patterns
            for topic in topics:
                cache_patterns.extend([f"search:*{topic.lower()}*", f"suggestions:*{topic.lower()}*"])

            # Add source-based cache patterns
            source_clean = source.replace("_", " ")
            cache_patterns.extend(
                [
                    f"search:*{source_clean.lower()}*",
                    f"search:*{source.lower()}*",
                    "suggestions:*",
                    "categories:*",
                    "knowledge:stats:*",
                ]
            )

            # Clear caches
            cleared_count = 0
            for pattern in cache_patterns:
                try:
                    count = await cache_service.clear_cache(pattern)
                    cleared_count += count
                except Exception as e:
                    logger.warning("cache_clear_pattern_failed", pattern=pattern, error=str(e))

            logger.info(
                "relevant_caches_invalidated",
                cleared_count=cleared_count,
                patterns_count=len(cache_patterns),
                topics=topics,
                source=source,
            )

        except Exception as e:
            logger.error("cache_invalidation_failed", topics=topics, source=source, error=str(e), exc_info=True)

    async def _find_existing_document(self, url: str, content_hash: str) -> KnowledgeItem | None:
        """Find existing document by URL or content hash.

        Args:
            url: Document URL
            content_hash: Content hash

        Returns:
            Existing KnowledgeItem or None
        """
        try:
            # First try to find by URL
            query = (
                select(KnowledgeItem)
                .where(and_(KnowledgeItem.source_url == url, KnowledgeItem.status == "active"))
                .order_by(KnowledgeItem.created_at.desc())
            )

            result = await self.db.execute(query)
            item = result.scalar_one_or_none()

            if item:
                return item

            # If not found by URL, try by content hash
            hash_query = (
                select(KnowledgeItem)
                .where(and_(KnowledgeItem.content_hash == content_hash, KnowledgeItem.status == "active"))
                .order_by(KnowledgeItem.created_at.desc())
            )

            hash_result = await self.db.execute(hash_query)
            return hash_result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "existing_document_search_failed", url=url, content_hash=content_hash, error=str(e), exc_info=True
            )
            return None

    async def _create_regulatory_document(self, document_data: dict[str, Any], knowledge_item_id: int) -> None:
        """Create regulatory document record.

        Args:
            document_data: Document information
            knowledge_item_id: ID of associated knowledge item
        """
        try:
            # Import here to avoid circular imports
            from app.models.regulatory_documents import RegulatoryDocument

            regulatory_doc = RegulatoryDocument(
                source=document_data.get("source", ""),
                source_type=document_data.get("source_type", ""),
                title=document_data.get("title", ""),
                url=document_data.get("url", ""),
                published_date=document_data.get("published_date"),
                content=document_data.get("content", ""),
                content_hash=self._generate_content_hash(document_data.get("content", "")),
                document_number=document_data.get("document_number"),
                metadata=document_data.get("metadata", {}),
                knowledge_item_id=knowledge_item_id,
                version=1,
                status="active",
            )

            self.db.add(regulatory_doc)
            await self.db.commit()

        except Exception as e:
            logger.error(
                "regulatory_document_creation_failed", knowledge_item_id=knowledge_item_id, error=str(e), exc_info=True
            )
            # Don't raise exception as this is supplementary data

    async def _update_regulatory_document(
        self, document_data: dict[str, Any], knowledge_item_id: int, version: int
    ) -> None:
        """Update regulatory document record with new version.

        Args:
            document_data: Updated document information
            knowledge_item_id: ID of associated knowledge item
            version: Version number
        """
        try:
            from app.models.regulatory_documents import RegulatoryDocument

            # Mark old version as superseded
            old_doc_query = (
                select(RegulatoryDocument)
                .where(RegulatoryDocument.url == document_data.get("url", ""))
                .order_by(RegulatoryDocument.created_at.desc())
            )

            result = await self.db.execute(old_doc_query)
            old_doc = result.scalar_one_or_none()

            if old_doc:
                old_doc.status = "superseded"

            # Create new version
            new_regulatory_doc = RegulatoryDocument(
                source=document_data.get("source", ""),
                source_type=document_data.get("source_type", ""),
                title=document_data.get("title", ""),
                url=document_data.get("url", ""),
                published_date=document_data.get("published_date"),
                content=document_data.get("content", ""),
                content_hash=self._generate_content_hash(document_data.get("content", "")),
                document_number=document_data.get("document_number"),
                metadata=document_data.get("metadata", {}),
                knowledge_item_id=knowledge_item_id,
                version=version,
                status="active",
            )

            self.db.add(new_regulatory_doc)
            await self.db.commit()

        except Exception as e:
            logger.error(
                "regulatory_document_update_failed",
                knowledge_item_id=knowledge_item_id,
                version=version,
                error=str(e),
                exc_info=True,
            )

    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash of content.

        Args:
            content: Text content

        Returns:
            SHA256 hash string
        """
        if not content:
            return ""

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _determine_knowledge_category(self, document_data: dict[str, Any]) -> str:
        """Determine knowledge category based on document data.

        Args:
            document_data: Document information

        Returns:
            Knowledge category string
        """
        source = document_data.get("source", "").lower()
        document_data.get("source_type", "").lower()
        title = document_data.get("title", "").lower()

        # Category mapping based on source and content
        if source == "agenzia_entrate":
            if "iva" in title or "imposta" in title:
                return "tax_guide"
            elif "dichiarazione" in title or "redditi" in title:
                return "tax_returns"
            else:
                return "agenzia_entrate_circolari"

        elif source == "inps":
            if "pensione" in title or "previdenza" in title:
                return "social_security"
            else:
                return "inps_circolari"

        elif source == "gazzetta_ufficiale":
            if "decreto" in title:
                return "legislation"
            else:
                return "official_acts"

        else:
            return "regulatory_update"

    def _determine_knowledge_subcategory(self, document_data: dict[str, Any]) -> str:
        """Determine knowledge subcategory.

        Args:
            document_data: Document information

        Returns:
            Knowledge subcategory string
        """
        source_type = document_data.get("source_type", "").lower()
        title = document_data.get("title", "").lower()

        if source_type:
            return source_type

        # Infer from title
        if "circolare" in title:
            return "circolari"
        elif "risoluzione" in title:
            return "risoluzioni"
        elif "decreto" in title:
            return "decreti"
        elif "provvedimento" in title:
            return "provvedimenti"
        else:
            return "documenti"

    async def _prepare_metadata(self, document_data: dict[str, Any]) -> dict[str, Any]:
        """Prepare metadata for storage.

        Args:
            document_data: Document information

        Returns:
            Prepared metadata dictionary
        """
        metadata = document_data.get("metadata", {}).copy()

        # Add extraction timestamp
        metadata["extracted_at"] = datetime.now(UTC).isoformat()

        # Add document identifiers
        if document_data.get("document_number"):
            metadata["document_number"] = document_data["document_number"]

        if document_data.get("published_date"):
            metadata["published_date"] = document_data["published_date"].isoformat()

        # Add authority information
        metadata["authority"] = document_data.get("authority", "")
        metadata["source_type"] = document_data.get("source_type", "")

        # Add citation data
        citation = await self.create_citation_data(document_data)
        if not isinstance(citation, dict) or "error" not in citation:
            metadata["citation"] = citation

        return metadata

    def _calculate_relevance_score(self, document_data: dict[str, Any]) -> float:
        """Calculate relevance score for the document.

        Args:
            document_data: Document information

        Returns:
            Relevance score between 0.0 and 1.0
        """
        score = 0.5  # Base score

        # Boost score based on source authority
        authority_scores = {"agenzia_entrate": 0.9, "inps": 0.85, "gazzetta_ufficiale": 0.95, "governo": 0.9}

        source = document_data.get("source", "")
        if source in authority_scores:
            score = authority_scores[source]

        # Adjust based on document type
        source_type = document_data.get("source_type", "").lower()
        if source_type in ["circolari", "decreto_legislativo", "legge"]:
            score += 0.05

        # Adjust based on content quality indicators
        content = document_data.get("content", "")
        if content:
            content_length = len(content)
            if content_length > 1000:
                score += 0.05
            if content_length > 5000:
                score += 0.05

        # Ensure score is within bounds
        return min(1.0, max(0.1, score))

    def _format_italian_date(self, date_obj: datetime | None) -> str:
        """Format date in Italian format.

        Args:
            date_obj: Date object to format

        Returns:
            Formatted Italian date string
        """
        if not date_obj:
            return ""

        try:
            italian_months_names = {
                1: "gennaio",
                2: "febbraio",
                3: "marzo",
                4: "aprile",
                5: "maggio",
                6: "giugno",
                7: "luglio",
                8: "agosto",
                9: "settembre",
                10: "ottobre",
                11: "novembre",
                12: "dicembre",
            }

            day = date_obj.day
            month = italian_months_names.get(date_obj.month, str(date_obj.month))
            year = date_obj.year

            return f"{day} {month} {year}"

        except Exception:
            return date_obj.strftime("%d/%m/%Y")


# Utility functions for external use


async def integrate_document(db_session: AsyncSession, document_data: dict[str, Any]) -> dict[str, Any]:
    """Convenience function to integrate a single document.

    Args:
        db_session: Database session
        document_data: Document information

    Returns:
        Integration result
    """
    integrator = KnowledgeIntegrator(db_session)
    return await integrator.update_knowledge_base(document_data)


async def create_document_citation(document_data: dict[str, Any]) -> dict[str, Any]:
    """Convenience function to create document citation.

    Args:
        document_data: Document information

    Returns:
        Citation data
    """
    # Create temporary integrator (no DB operations needed for citation)
    integrator = KnowledgeIntegrator(None)
    return await integrator.create_citation_data(document_data)
