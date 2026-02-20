"""Document Metadata Preservation Layer for DEV-191.

Extracts and formats document metadata for synthesis per Section 13.9.
Preserves metadata from retrieval through to LLM synthesis step.

Usage:
    from app.services.metadata_extractor import MetadataExtractor

    extractor = MetadataExtractor()
    context = extractor.format_context_for_synthesis(retrieval_result)
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.core.logging import logger
from app.services.parallel_retrieval import RankedDocument, RetrievalResult

# Hierarchy levels per Section 13.9.2
# Lower number = higher authority
HIERARCHY_LEVELS: dict[str, int] = {
    "legge": 1,
    "decreto": 2,
    "circolare": 3,
    "risoluzione": 4,
    "interpello": 5,
    "faq": 6,
    "guida": 7,
}

# Default hierarchy level for unknown types
DEFAULT_HIERARCHY_LEVEL = 99


@dataclass
class DocumentMetadata:
    """Metadata preserved for each retrieved document.

    Per Section 13.9.2, this structure preserves all metadata needed
    for chronological analysis and source hierarchy in synthesis.

    Attributes:
        document_id: Unique identifier for the document
        title: Document title
        date_published: Publication date
        source_entity: Issuing entity (e.g., "Agenzia delle Entrate")
        document_type: Type (legge, circolare, faq, etc.)
        hierarchy_level: Authority level (1=highest)
        reference_code: Formatted reference (e.g., "Circ. 9/E/2025")
        url: Original source URL (optional)
        relevance_score: RRF relevance score from retrieval
        text_excerpt: Relevant text content
    """

    document_id: str
    title: str
    date_published: datetime
    source_entity: str
    document_type: str
    hierarchy_level: int
    reference_code: str
    url: str | None
    relevance_score: float
    text_excerpt: str


class MetadataExtractor:
    """Service for extracting and formatting document metadata.

    Extracts DocumentMetadata from RankedDocuments and formats
    context for the synthesis LLM per Section 13.9.3.

    Example:
        extractor = MetadataExtractor()

        # Extract metadata from retrieval results
        metadata_list = extractor.extract_all(retrieval_result)

        # Format context for synthesis
        context = extractor.format_context_for_synthesis(retrieval_result)
    """

    def get_hierarchy_level(self, document_type: str) -> int:
        """Get hierarchy level for a document type.

        Lower numbers indicate higher authority.

        Args:
            document_type: Type of document (legge, circolare, etc.)

        Returns:
            Hierarchy level (1=highest, 99=unknown)
        """
        return HIERARCHY_LEVELS.get(document_type.lower(), DEFAULT_HIERARCHY_LEVEL)

    def extract(self, ranked_doc: RankedDocument) -> DocumentMetadata:
        """Extract DocumentMetadata from a RankedDocument.

        Maps fields from RankedDocument to DocumentMetadata,
        deriving missing fields when possible.

        Args:
            ranked_doc: Document from parallel retrieval

        Returns:
            Extracted DocumentMetadata
        """
        metadata = ranked_doc.metadata or {}

        # Get title from metadata or fall back to source_name
        title = metadata.get("title") or ranked_doc.source_name

        # Get source entity from metadata
        source_entity = metadata.get("source_entity") or self._derive_source_entity(ranked_doc.source_type)

        # Get hierarchy level
        hierarchy_level = self.get_hierarchy_level(ranked_doc.source_type)

        # Format reference code
        reference_code = self.format_reference_code(
            source_type=ranked_doc.source_type,
            source_name=ranked_doc.source_name,
            metadata=metadata,
        )

        # Get URL from metadata
        url = metadata.get("url")

        return DocumentMetadata(
            document_id=ranked_doc.document_id,
            title=title,
            date_published=ranked_doc.published_date or datetime.now(),
            source_entity=source_entity,
            document_type=ranked_doc.source_type,
            hierarchy_level=hierarchy_level,
            reference_code=reference_code,
            url=url,
            relevance_score=ranked_doc.rrf_score,
            text_excerpt=ranked_doc.content,
        )

    def extract_all(self, retrieval_result: RetrievalResult) -> list[DocumentMetadata]:
        """Extract metadata from all documents in a retrieval result.

        Args:
            retrieval_result: Result from ParallelRetrievalService

        Returns:
            List of DocumentMetadata objects
        """
        return [self.extract(doc) for doc in retrieval_result.documents]

    def sort_by_date(self, docs: list[DocumentMetadata], reverse: bool = True) -> list[DocumentMetadata]:
        """Sort documents by publication date.

        Args:
            docs: List of DocumentMetadata
            reverse: If True, most recent first (default)

        Returns:
            Sorted list of documents
        """
        return sorted(docs, key=lambda d: d.date_published, reverse=reverse)

    def format_reference_code(
        self,
        source_type: str,
        source_name: str,
        metadata: dict[str, Any],
    ) -> str:
        """Format reference code for a document.

        Uses explicit reference_code from metadata if available,
        otherwise derives from source_type and source_name.

        Args:
            source_type: Document type
            source_name: Document name
            metadata: Document metadata dict

        Returns:
            Formatted reference code string
        """
        # Use explicit reference_code if provided
        if metadata.get("reference_code"):
            return metadata["reference_code"]

        # Derive reference code from source_type and source_name
        source_type_lower = source_type.lower()

        if source_type_lower == "legge":
            # Extract number pattern like "190/2014"
            match = re.search(r"(\d+/\d+)", source_name)
            if match:
                return f"L. {match.group(1)}"
            return source_name

        elif source_type_lower == "circolare":
            # Extract number pattern like "9/E/2025" or "10/E/2024"
            match = re.search(r"(\d+/[A-Z]/\d+)", source_name)
            if match:
                return f"Circ. {match.group(1)}"
            return f"Circ. {source_name}"

        elif source_type_lower == "decreto":
            match = re.search(r"(\d+/\d+)", source_name)
            if match:
                return f"D.Lgs. {match.group(1)}"
            return source_name

        elif source_type_lower == "risoluzione":
            match = re.search(r"(\d+/[A-Z]/\d+|\d+/\d+)", source_name)
            if match:
                return f"Ris. {match.group(1)}"
            return source_name

        else:
            return source_name

    def format_context_for_synthesis(self, retrieval_result: RetrievalResult) -> str:
        """Format context for the synthesis LLM.

        Creates formatted context per Section 13.9.3 with:
        - Header with statistics
        - Documents sorted by date (most recent first)
        - Structured metadata for each document

        Args:
            retrieval_result: Result from ParallelRetrievalService

        Returns:
            Formatted context string for synthesis
        """
        context_parts: list[str] = []

        # Header with statistics
        num_docs = len(retrieval_result.documents)
        context_parts.append(
            f"""
## Documenti Recuperati: {num_docs}
## Tempo Retrieval: {retrieval_result.search_time_ms:.0f}ms
"""
        )

        if not retrieval_result.documents:
            return "\n".join(context_parts)

        # Extract and sort metadata
        metadata_list = self.extract_all(retrieval_result)
        sorted_metadata = self.sort_by_date(metadata_list)

        # Format each document
        for i, doc in enumerate(sorted_metadata, 1):
            date_str = doc.date_published.strftime("%d/%m/%Y")
            url_str = doc.url or "N/A"

            context_parts.append(
                f"""
━━━ DOCUMENTO {i} ━━━
📅 Data: {date_str}
🏛️ Ente: {doc.source_entity}
📄 Tipo: {doc.document_type} (Livello gerarchico: {doc.hierarchy_level})
📌 Riferimento: {doc.reference_code}
🔗 URL: {url_str}
📊 Relevance: {doc.relevance_score:.2f}

CONTENUTO:
{doc.text_excerpt}
"""
            )

        logger.info(
            "context_formatted_for_synthesis",
            num_documents=num_docs,
            total_found=retrieval_result.total_found,
        )

        return "\n".join(context_parts)

    def _derive_source_entity(self, source_type: str) -> str:
        """Derive source entity from document type.

        Args:
            source_type: Document type

        Returns:
            Likely source entity name
        """
        source_type_lower = source_type.lower()

        # Common mappings for Italian fiscal/legal documents
        entity_mappings = {
            "circolare": "Agenzia delle Entrate",
            "risoluzione": "Agenzia delle Entrate",
            "interpello": "Agenzia delle Entrate",
            "faq": "Agenzia delle Entrate",
            "legge": "Parlamento Italiano",
            "decreto": "Governo Italiano",
            "guida": "Agenzia delle Entrate",
        }

        return entity_mappings.get(source_type_lower, "Fonte non specificata")
