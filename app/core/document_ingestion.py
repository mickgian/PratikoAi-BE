"""
Unified Document Ingestion Core.

This module provides a single source of truth for document ingestion,
handling both PDF and HTML content with proper extraction, chunking,
and quality tracking.

Used by:
- app/ingest/rss_normativa.py (direct ingestion)
- app/services/document_processor.py (API endpoint)
- scripts/ingest_rss.py (CLI tool)
"""

import hashlib
import re
import tempfile
import time
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chunking import chunk_document
from app.core.embed import generate_embedding
from app.core.text.clean import (
    extract_text_from_url_content,
    is_valid_text,
)
from app.core.text.extract_pdf_plumber import extract_pdf_with_ocr_fallback_plumber
from app.models.knowledge import KnowledgeItem
from app.models.knowledge_chunk import KnowledgeChunk

# Italian month name mapping for date normalization
ITALIAN_MONTHS = {
    "01": "gennaio",
    "02": "febbraio",
    "03": "marzo",
    "04": "aprile",
    "05": "maggio",
    "06": "giugno",
    "07": "luglio",
    "08": "agosto",
    "09": "settembre",
    "10": "ottobre",
    "11": "novembre",
    "12": "dicembre",
}


def normalize_document_text(content: str) -> str:
    """
    Normalize document text to improve searchability.

    Fixes common PDF extraction issues:
    1. Broken years like "20 25" → "2025"
    2. Adds Italian month names after dates like "30/10/2025" → "30/10/2025 (ottobre)"

    This allows users to search for "ottobre 2025" even when documents
    only contain dates in DD/MM/YYYY format.

    Args:
        content: Raw extracted text

    Returns:
        Normalized text with fixed dates and added month names
    """
    # Fix 1: Repair broken years "20 XX" → "20XX" (e.g., "20 25" → "2025")
    # Pattern: date like DD/MM/20 followed by space and 2 digits
    content = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{2})\s+(\d{2})\b", r"\1/\2/\3\4", content)

    # Fix 2: Add Italian month names after dates for searchability
    # Pattern: DD/MM/YYYY dates (like "30/10/2025")
    def add_month_name(match):
        day = match.group(1)
        month = match.group(2)
        year = match.group(3)
        month_name = ITALIAN_MONTHS.get(month, "")

        # Only add month name if we found a valid one
        if month_name:
            return f"{day}/{month}/{year} ({month_name})"
        return match.group(0)  # Return original if invalid month

    # Apply month name addition to dates
    # This transforms "Roma, 30/10/2025 OGGETTO:" → "Roma, 30/10/2025 (ottobre) OGGETTO:"
    content = re.sub(r"\b(\d{1,2})/(\d{2})/(\d{4})\b", add_month_name, content)

    return content


async def download_and_extract_document(url: str) -> Optional[Dict[str, Any]]:
    """
    Download and extract content from URL (PDF or HTML).

    Handles both:
    - PDF documents: Downloads binary, extracts with pdfplumber + Tesseract
    - HTML pages: Extracts text with BeautifulSoup

    Args:
        url: Document URL

    Returns:
        Dictionary with:
        - content: Extracted text
        - extraction_method: 'pdfplumber', 'mixed', or 'html'
        - text_quality: Quality score (0.0-1.0) for PDFs
        - ocr_pages: List of OCR'd pages for PDFs
        Or None if extraction failed
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()

            # Handle PDF documents
            if "application/pdf" in content_type:
                # Save PDF to temporary file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(response.content)  # Binary content
                    tmp_path = tmp.name

                try:
                    # Extract text using pdfplumber + Tesseract OCR
                    result = extract_pdf_with_ocr_fallback_plumber(tmp_path)
                    full_text = result.get("full_text", "")

                    if not is_valid_text(full_text):
                        return None

                    return {
                        "content": full_text,
                        "extraction_method": result.get("extraction_method", "pdfplumber"),
                        "text_quality": result.get("text_quality"),
                        "ocr_pages": result.get("ocr_pages", []),
                    }

                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)

            # Handle HTML/text documents
            else:
                content = response.text  # Text decoding for HTML

                # Extract clean text
                clean_text = extract_text_from_url_content(content, content_type)

                if not is_valid_text(clean_text):
                    return None

                return {"content": clean_text, "extraction_method": "html", "text_quality": None, "ocr_pages": []}

    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None


def compute_content_hash(text: str) -> str:
    """
    Compute SHA256 hash of text for deduplication.

    Args:
        text: Input text

    Returns:
        Hex digest of SHA256 hash
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()  # type: ignore[arg-type]


async def ingest_document_with_chunks(
    session: AsyncSession,
    title: str,
    url: str,
    content: str,
    extraction_method: str = "html",
    text_quality: Optional[float] = None,
    ocr_pages: Optional[List[Dict[str, Any]]] = None,
    published_date: Optional[datetime] = None,
    source: str = "regulatory_update",
    category: str = "regulatory_documents",
    subcategory: str = "general",
) -> Optional[int]:
    """
    Ingest a single document with full chunking and embeddings.

    This is the unified ingestion function used by all ingestion paths.

    Args:
        session: Database session
        title: Document title
        url: Document URL
        content: Clean text content
        extraction_method: How content was extracted ('pdfplumber', 'mixed', 'html')
        text_quality: PDF quality score (0.0-1.0), None for HTML
        ocr_pages: List of OCR'd pages for PDFs
        published_date: Publication date
        source: Source identifier
        category: Document category
        subcategory: Document subcategory

    Returns:
        knowledge_item_id if successful, None otherwise
    """
    try:
        # Normalize content to fix PDF extraction issues and improve searchability
        # - Fixes broken dates like "30/10/20 25" → "30/10/2025"
        # - Adds month names: "30/10/2025" → "30/10/2025 (ottobre)"
        content = normalize_document_text(content)

        # Publication date: prioritize RSS feed date, fallback to content extraction
        if published_date is None:
            # Only parse from content if no RSS/API date provided
            from app.core.text.date_parser import extract_publication_date as parse_date

            publication_date = parse_date(content, title)
        else:
            # Use RSS-provided date (more reliable than content parsing)
            publication_date = published_date.date() if hasattr(published_date, "date") else published_date

        # Create knowledge item
        kb_epoch = time.time()
        content_hash = compute_content_hash(content)

        # Generate embedding for full content (truncated if needed)
        content_for_embedding = content[:30000]  # ~8k tokens
        embedding_vec = await generate_embedding(content_for_embedding)
        # For asyncpg, pass embedding list directly (not string format)
        embedding_data = embedding_vec if embedding_vec else None

        # Prepare OCR pages JSON
        ocr_pages_json = ocr_pages if ocr_pages else None

        knowledge_item = KnowledgeItem(
            title=title,
            content=content,
            category=category,
            subcategory=subcategory,
            source=source,
            source_url=url,
            language="it",
            kb_epoch=kb_epoch,
            embedding=embedding_data,
            status="active",
            # Quality tracking fields
            extraction_method=extraction_method,
            text_quality=text_quality,
            ocr_pages=ocr_pages_json,
            # Publication metadata
            publication_date=publication_date,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        session.add(knowledge_item)
        await session.flush()  # Get the ID

        knowledge_item_id = knowledge_item.id

        # Chunk the document
        ocr_used = extraction_method in ("mixed", "ocr")
        chunks = chunk_document(content=content, title=title, max_tokens=512, overlap_tokens=50, ocr_used=ocr_used)

        # Process each chunk
        for chunk_dict in chunks:
            chunk_text = chunk_dict["chunk_text"]

            # Generate embedding for chunk
            chunk_embedding_vec = await generate_embedding(chunk_text)
            # For asyncpg, pass embedding list directly (not string format)
            chunk_embedding_data = chunk_embedding_vec if chunk_embedding_vec else None

            knowledge_chunk = KnowledgeChunk(
                knowledge_item_id=knowledge_item_id,
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
                created_at=datetime.now(timezone.utc),
            )

            session.add(knowledge_chunk)

        await session.commit()
        print(f"✅ Ingested: {title} ({len(chunks)} chunks)")
        return knowledge_item_id

    except Exception as e:
        await session.rollback()
        print(f"❌ Error ingesting {title}: {e}")
        return None


async def check_document_exists(session: AsyncSession, url: str) -> bool:
    """
    Check if document already exists in knowledge_items by URL.

    Args:
        session: Database session
        url: Document URL

    Returns:
        True if document exists
    """
    from sqlalchemy import select

    result = await session.execute(
        select(KnowledgeItem).where(KnowledgeItem.source_url == url)  # type: ignore[arg-type]
    )
    return result.scalar_one_or_none() is not None
