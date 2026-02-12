"""Unified Document Ingestion Core.

This module provides a single source of truth for document ingestion,
handling both PDF and HTML content with proper extraction, chunking,
and quality tracking.

Used by:
- app/ingest/rss_normativa.py (direct ingestion)
- app/services/document_processor.py (API endpoint)
- scripts/ingest_rss.py (CLI tool)
"""

import asyncio
import hashlib
import re
import ssl
import tempfile
import time
from datetime import (
    UTC,
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
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chunking import chunk_document
from app.core.embed import generate_embedding, generate_embeddings_batch
from app.core.logging import logger
from app.core.text.clean import (
    extract_text_from_url_content,
    is_valid_text,
    validate_extracted_content,
)
from app.core.text.extract_pdf_plumber import extract_pdf_with_ocr_fallback_plumber
from app.models.knowledge import KnowledgeItem
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.article_extractor import article_extractor

# Domains that require relaxed SSL settings (older TLS ciphers)
RELAXED_SSL_DOMAINS = {"www.inail.it", "inail.it"}


def _get_ssl_context(url: str) -> ssl.SSLContext | bool:
    """Get appropriate SSL context for a URL.

    Some government sites (e.g., INAIL) use older TLS configurations
    that require relaxed cipher settings.

    Args:
        url: The URL to fetch

    Returns:
        SSLContext for relaxed domains, True for standard SSL verification
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if hostname in RELAXED_SSL_DOMAINS:
        # Create SSL context with relaxed security level for older servers
        ssl_context = ssl.create_default_context()
        ssl_context.set_ciphers("DEFAULT:@SECLEVEL=1")
        return ssl_context

    return True  # Use default SSL verification


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
    """Normalize document text to improve searchability.

    Fixes common PDF extraction issues:
    1. Broken hyphenation like "contri- buto" → "contributo"
    2. Broken years like "20 25" → "2025"
    3. Adds Italian month names after dates like "30/10/2025" → "30/10/2025 (ottobre)"

    This allows users to search for "ottobre 2025" even when documents
    only contain dates in DD/MM/YYYY format.

    Args:
        content: Raw extracted text

    Returns:
        Normalized text with fixed dates and added month names
    """
    # Fix 0: Repair broken hyphenation from PDF line breaks
    from app.core.text.hyphenation import repair_broken_hyphenation

    content = repair_broken_hyphenation(content)

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


def _is_gazzetta_ufficiale_url(url: str) -> bool:
    """Check if URL is from Gazzetta Ufficiale.

    Args:
        url: URL to check

    Returns:
        True if URL is from gazzettaufficiale.it
    """
    parsed = urlparse(url)
    return "gazzettaufficiale.it" in (parsed.hostname or "").lower()


def _extract_gazzetta_pdf_url(html_content: str, base_url: str) -> str | None:
    """Extract PDF download URL from Gazzetta Ufficiale HTML page.

    Gazzetta Ufficiale pages use iframes and JavaScript to load content.
    The PDF link provides the authoritative full document.

    Args:
        html_content: Raw HTML from the page
        base_url: Original page URL for constructing absolute URLs

    Returns:
        PDF URL if found, None otherwise
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Look for PDF links in various forms
        # 1. Direct PDF links with "/pdf" in path
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "/pdf" in href.lower() or href.endswith(".pdf"):
                # Make absolute URL if relative
                if href.startswith("/"):
                    parsed = urlparse(base_url)
                    return f"{parsed.scheme}://{parsed.netloc}{href}"
                elif href.startswith("http"):
                    return href

        # 2. Look for "Formato Grafico PDF" or similar text
        for link in soup.find_all("a", href=True):
            link_text = link.get_text().lower()
            if "pdf" in link_text or "formato grafico" in link_text:
                href = link.get("href", "")
                if href.startswith("/"):
                    parsed = urlparse(base_url)
                    return f"{parsed.scheme}://{parsed.netloc}{href}"
                elif href.startswith("http"):
                    return href

        # 3. Try to construct PDF URL from page URL pattern
        # Pattern: /eli/id/YYYY/MM/DD/CODE/SG -> /eli/gu/YYYY/MM/DD/NUM/so/SUPPL/sg/pdf
        # This is complex and varies, so we'll rely on found links first

        logger.warning(
            "gazzetta_pdf_url_not_found",
            base_url=base_url,
            message="Could not find PDF link in Gazzetta Ufficiale page",
        )
        return None

    except Exception as e:
        logger.error(
            "gazzetta_pdf_extraction_error",
            base_url=base_url,
            error=str(e),
        )
        return None


async def _download_gazzetta_pdf(pdf_url: str) -> dict[str, Any] | None:
    """Download and extract content from Gazzetta Ufficiale PDF.

    Args:
        pdf_url: URL to the PDF document

    Returns:
        Extraction result dict or None if failed
    """
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()

            # Save PDF to temporary file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            try:
                # DEV-242: Run CPU-bound PDF extraction in thread pool
                result = await asyncio.to_thread(extract_pdf_with_ocr_fallback_plumber, tmp_path)
                full_text = result.get("full_text", "")

                if not is_valid_text(full_text):
                    logger.warning(
                        "gazzetta_pdf_invalid_text",
                        pdf_url=pdf_url,
                        text_length=len(full_text) if full_text else 0,
                    )
                    return None

                logger.info(
                    "gazzetta_pdf_extracted",
                    pdf_url=pdf_url,
                    text_length=len(full_text),
                    extraction_method=result.get("extraction_method"),
                )

                return {
                    "content": full_text,
                    "extraction_method": f"gazzetta_pdf_{result.get('extraction_method', 'pdfplumber')}",
                    "text_quality": result.get("text_quality"),
                    "ocr_pages": result.get("ocr_pages", []),
                }

            finally:
                Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(
            "gazzetta_pdf_download_error",
            pdf_url=pdf_url,
            error=str(e),
        )
        return None


async def download_and_extract_document(url: str) -> dict[str, Any] | None:
    """Download and extract content from URL (PDF or HTML).

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
        # Get appropriate SSL context (relaxed for some government sites like INAIL)
        ssl_context = _get_ssl_context(url)
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=ssl_context) as client:
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
                    # DEV-242: Run CPU-bound PDF extraction in thread pool
                    # This prevents blocking the event loop during OCR processing
                    result = await asyncio.to_thread(extract_pdf_with_ocr_fallback_plumber, tmp_path)
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

                # Extract clean text (pass URL for quality logging)
                clean_text = extract_text_from_url_content(content, content_type, url=url)

                # Validate extracted content quality
                is_valid, validation_reason = validate_extracted_content(clean_text, url)

                # Special handling for Gazzetta Ufficiale: if HTML extraction failed,
                # try to get the PDF version instead
                if _is_gazzetta_ufficiale_url(url) and not is_valid:
                    logger.info(
                        "gazzetta_html_extraction_failed_trying_pdf",
                        url=url,
                        validation_reason=validation_reason,
                        html_content_length=len(clean_text) if clean_text else 0,
                    )

                    # Try to extract PDF URL from the page
                    pdf_url = _extract_gazzetta_pdf_url(content, url)
                    if pdf_url:
                        pdf_result = await _download_gazzetta_pdf(pdf_url)
                        if pdf_result:
                            return pdf_result
                        logger.warning(
                            "gazzetta_pdf_fallback_failed",
                            url=url,
                            pdf_url=pdf_url,
                        )
                    else:
                        logger.warning(
                            "gazzetta_no_pdf_url_found",
                            url=url,
                        )

                    # Return None if both HTML and PDF failed
                    return None

                if not is_valid_text(clean_text):
                    return None

                return {"content": clean_text, "extraction_method": "html", "text_quality": None, "ocr_pages": []}

    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None


def compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of text for deduplication.

    Args:
        text: Input text

    Returns:
        Hex digest of SHA256 hash
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def ingest_document_with_chunks(
    session: AsyncSession,
    title: str,
    url: str,
    content: str,
    extraction_method: str = "html",
    text_quality: float | None = None,
    ocr_pages: list[dict[str, Any]] | None = None,
    published_date: datetime | None = None,
    source: str = "regulatory_update",
    category: str = "regulatory_documents",
    subcategory: str = "general",
) -> int | None:
    """Ingest a single document with full chunking and embeddings.

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

        # Content-hash dedup: skip if identical content already exists
        from sqlalchemy import select

        existing = await session.execute(
            select(KnowledgeItem.id).where(
                KnowledgeItem.content_hash == content_hash,
                KnowledgeItem.status == "active",
            )
        )
        if existing.scalar_one_or_none() is not None:
            logger.info("duplicate_content_skipped", title=title, content_hash=content_hash)
            return None

        # Generate embedding for full content (token-truncated inside generate_embedding)
        embedding_vec = await generate_embedding(content)
        # For asyncpg, pass embedding list directly (not string format)
        embedding_data = embedding_vec if embedding_vec else None

        # Prepare OCR pages JSON
        ocr_pages_json = ocr_pages if ocr_pages else None

        # DEV-245: Extract article metadata for legal documents
        # This enables accurate citation of articolo/comma/lettera in responses
        article_metadata = article_extractor.extract_chunk_metadata(content)
        parsing_metadata_dict = {
            "article_references": article_metadata.get("article_references", []),
            "primary_article": article_metadata.get("primary_article"),
            "has_definitions": article_metadata.get("has_definitions", False),
            "comma_count": article_metadata.get("comma_count", 0),
        }

        logger.debug(
            "DEV245_article_metadata_extracted",
            title=title,
            primary_article=parsing_metadata_dict.get("primary_article"),
            reference_count=len(parsing_metadata_dict.get("article_references", [])),
        )

        knowledge_item = KnowledgeItem(
            title=title,
            content=content,
            content_hash=content_hash,
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
            # DEV-245: Article metadata for legal documents
            parsing_metadata=parsing_metadata_dict,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        session.add(knowledge_item)
        await session.flush()  # Get the ID

        knowledge_item_id = knowledge_item.id

        # Chunk the document
        ocr_used = extraction_method in ("mixed", "ocr")
        chunks = chunk_document(content=content, title=title, ocr_used=ocr_used)

        # Batch-generate embeddings for all chunks (P0-A: N chunks → ceil(N/20) API calls)
        chunk_texts = [c["chunk_text"] for c in chunks]
        chunk_embeddings = await generate_embeddings_batch(chunk_texts) if chunk_texts else []

        for chunk_dict, chunk_embedding_vec in zip(chunks, chunk_embeddings, strict=False):
            # For asyncpg, pass embedding list directly (not string format)
            chunk_embedding_data = chunk_embedding_vec if chunk_embedding_vec else None

            knowledge_chunk = KnowledgeChunk(
                knowledge_item_id=knowledge_item_id,
                chunk_text=chunk_dict["chunk_text"],
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

            session.add(knowledge_chunk)

        await session.commit()
        print(f"✅ Ingested: {title} ({len(chunks)} chunks)")
        return knowledge_item_id

    except Exception as e:
        await session.rollback()
        print(f"❌ Error ingesting {title}: {e}")
        return None


async def check_document_exists(session: AsyncSession, url: str) -> bool:
    """Check if document already exists in knowledge_items by URL.

    Args:
        session: Database session
        url: Document URL

    Returns:
        True if document exists
    """
    from sqlalchemy import select

    result = await session.execute(select(KnowledgeItem).where(KnowledgeItem.source_url == url))
    return result.scalar_one_or_none() is not None
