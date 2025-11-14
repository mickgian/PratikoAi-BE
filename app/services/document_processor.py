"""
Document Processor Service for Italian Regulatory Documents.

This service handles content extraction from PDF and HTML documents
retrieved from Italian regulatory authorities.
"""

import asyncio
import hashlib
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from app.core.logging import logger
from app.core.text.clean import is_valid_text
from app.core.text.extract_pdf_plumber import extract_pdf_with_ocr_fallback_plumber


class DocumentProcessor:
    """Process and extract content from regulatory documents."""

    def __init__(self, timeout: int = 60):
        """Initialize document processor.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.session = None
        self.supported_formats = {".pdf", ".html", ".htm", ".xml"}

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "User-Agent": "PratikoAI-Document-Processor/1.0 (https://pratiko.ai)",
                "Accept": "application/pdf, text/html, application/xml, text/xml, */*",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def extract_content_from_pdf(self, pdf_url: str) -> str:
        """Extract text content from PDF document.

        Args:
            pdf_url: URL of PDF document

        Returns:
            Extracted text content
        """
        try:
            # Download PDF content
            download_result = await self._download_document(pdf_url)
            if not download_result:
                return ""

            pdf_content, content_type = download_result

            # Extract text using pdfplumber + Tesseract
            text_content = await self._extract_pdf_text(pdf_content)

            # Clean and normalize extracted text
            cleaned_content = self._clean_extracted_text(text_content)

            logger.info(
                "pdf_content_extracted",
                pdf_url=pdf_url,
                content_length=len(cleaned_content),
                content_type=content_type,
            )

            return cleaned_content

        except Exception as e:
            logger.error("pdf_content_extraction_failed", pdf_url=pdf_url, error=str(e), exc_info=True)
            return ""

    async def extract_content_from_html(self, html_url: str) -> str:
        """Extract text content from HTML document.

        Args:
            html_url: URL of HTML document

        Returns:
            Extracted text content
        """
        try:
            # Download HTML content
            download_result = await self._download_document(html_url)
            if not download_result:
                return ""

            html_content, content_type = download_result

            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Extract text from main content areas
            text_content = self._extract_html_main_content(soup)

            # Clean and normalize extracted text
            cleaned_content = self._clean_extracted_text(text_content)

            logger.info(
                "html_content_extracted",
                html_url=html_url,
                content_length=len(cleaned_content),
                content_type=content_type,
            )

            return cleaned_content

        except Exception as e:
            logger.error("html_content_extraction_failed", html_url=html_url, error=str(e), exc_info=True)
            return ""

    async def extract_content_from_xml(self, xml_url: str) -> str:
        """Extract text content from XML document.

        Args:
            xml_url: URL of XML document

        Returns:
            Extracted text content
        """
        try:
            # Download XML content
            download_result = await self._download_document(xml_url)
            if not download_result:
                return ""

            xml_content, content_type = download_result

            # Parse XML and extract text
            soup = BeautifulSoup(xml_content, "xml")

            # Extract text content
            text_content = " ".join(soup.get_text().split())

            # Clean and normalize extracted text
            cleaned_content = self._clean_extracted_text(text_content)

            logger.info(
                "xml_content_extracted",
                xml_url=xml_url,
                content_length=len(cleaned_content),
                content_type=content_type,
            )

            return cleaned_content

        except Exception as e:
            logger.error("xml_content_extraction_failed", xml_url=xml_url, error=str(e), exc_info=True)
            return ""

    async def process_document(self, document_url: str) -> Dict[str, Any]:
        """Process document and extract content and metadata.

        Args:
            document_url: URL of document to process

        Returns:
            Dictionary containing extracted content and metadata
        """
        try:
            # Download document first to get content-type
            download_result = await self._download_document(document_url)
            if not download_result:
                return {
                    "url": document_url,
                    "content": "",
                    "content_hash": "",
                    "document_type": "unknown",
                    "metadata": {},
                    "processing_stats": {"error": "Download failed"},
                    "success": False,
                }

            document_content, content_type = download_result

            # Determine document type from content-type header (not URL!)
            doc_type = self._determine_document_type_from_header(content_type, document_url)

            # Extract content based on type
            if doc_type == "pdf":
                # Use our PDF extraction directly on the bytes
                text_content = await self._extract_pdf_text(document_content)
                content = self._clean_extracted_text(text_content)
            elif doc_type in ["html", "htm"]:
                # Parse HTML from bytes
                soup = BeautifulSoup(document_content, "html.parser")
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                text_content = self._extract_html_main_content(soup)
                content = self._clean_extracted_text(text_content)
            elif doc_type == "xml":
                # Parse XML from bytes
                soup = BeautifulSoup(document_content, "xml")
                text_content = " ".join(soup.get_text().split())
                content = self._clean_extracted_text(text_content)
            else:
                logger.warning("unsupported_document_type", url=document_url, type=doc_type, content_type=content_type)
                content = ""

            # Generate content hash for duplicate detection
            content_hash = self._generate_content_hash(content)

            # Extract metadata from content
            metadata = self._extract_content_metadata(content, document_url)

            # Calculate processing statistics
            processing_stats = {
                "content_length": len(content),
                "word_count": len(content.split()) if content else 0,
                "processing_time": datetime.now(),
                "document_type": doc_type,
                "content_type": content_type,
                "content_hash": content_hash,
            }

            result = {
                "url": document_url,
                "content": content,
                "content_hash": content_hash,
                "document_type": doc_type,
                "metadata": metadata,
                "processing_stats": processing_stats,
                "success": len(content) > 0,
            }

            logger.info(
                "document_processed",
                url=document_url,
                success=result["success"],
                content_length=len(content),
                document_type=doc_type,
                content_type=content_type,
            )

            return result

        except Exception as e:
            logger.error("document_processing_failed", url=document_url, error=str(e), exc_info=True)

            return {
                "url": document_url,
                "content": "",
                "content_hash": "",
                "document_type": "unknown",
                "metadata": {},
                "processing_stats": {"error": str(e)},
                "success": False,
            }

    async def process_documents_batch(self, document_urls: List[str], max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """Process multiple documents concurrently.

        Args:
            document_urls: List of document URLs to process
            max_concurrent: Maximum concurrent processing tasks

        Returns:
            List of processing results
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(url: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.process_document(url)

        # Create tasks for concurrent processing
        tasks = [asyncio.create_task(process_with_semaphore(url)) for url in document_urls]

        # Wait for all tasks to complete
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        "batch_document_processing_failed", url=document_urls[i], error=str(result), exc_info=True
                    )
                    processed_results.append(
                        {
                            "url": document_urls[i],
                            "content": "",
                            "content_hash": "",
                            "document_type": "unknown",
                            "metadata": {},
                            "processing_stats": {"error": str(result)},
                            "success": False,
                        }
                    )
                else:
                    processed_results.append(result)

            logger.info(
                "batch_document_processing_completed",
                total_documents=len(document_urls),
                successful=sum(1 for r in processed_results if r["success"]),
                failed=sum(1 for r in processed_results if not r["success"]),
            )

            return processed_results

        except Exception as e:
            logger.error("batch_document_processing_error", error=str(e), exc_info=True)
            return []

    async def _download_document(self, document_url: str) -> Optional[tuple[bytes, str]]:
        """Download document content from URL.

        Args:
            document_url: URL of document to download

        Returns:
            Tuple of (content bytes, content-type) or None on error
        """
        if not self.session:
            raise RuntimeError("DocumentProcessor must be used as async context manager")

        try:
            async with self.session.get(document_url) as response:
                if response.status == 200:
                    content = await response.read()
                    content_type = response.headers.get("content-type", "").lower()
                    logger.debug("document_downloaded", url=document_url, size=len(content), content_type=content_type)
                    return (content, content_type)
                else:
                    logger.warning("document_download_http_error", url=document_url, status_code=response.status)
                    return None

        except asyncio.TimeoutError:
            logger.error("document_download_timeout", url=document_url)
            return None
        except Exception as e:
            logger.error("document_download_failed", url=document_url, error=str(e), exc_info=True)
            return None

    async def _extract_pdf_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF content using pdfplumber + Tesseract OCR.

        Uses the production-grade extraction with quality-aware OCR fallback.
        Saves bytes to temporary file, extracts with pdfplumber, cleans up.

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            Extracted text content
        """
        try:
            # Save PDF bytes to temporary file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_content)
                tmp_path = tmp.name

            try:
                # Extract text using pdfplumber + Tesseract OCR
                result = extract_pdf_with_ocr_fallback_plumber(tmp_path)
                full_text = result.get("full_text", "")

                if not is_valid_text(full_text):
                    logger.warning("pdf_extraction_produced_invalid_text")
                    return ""

                logger.debug(
                    "pdf_text_extracted",
                    extraction_method=result.get("extraction_method"),
                    text_quality=result.get("text_quality"),
                    ocr_pages=len(result.get("ocr_pages", [])),
                )

                return full_text

            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error("pdf_text_extraction_failed", error=str(e), exc_info=True)
            return ""

    def _extract_html_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML soup object.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Extracted main content text
        """
        # Try to find main content areas
        main_selectors = [
            "main",
            "article",
            ".content",
            ".main-content",
            "#content",
            ".documento",  # Common in Italian official sites
            ".testo",  # Common content class
        ]

        for selector in main_selectors:
            element = soup.select_one(selector)
            if element:
                return " ".join(element.get_text().split())

        # Fallback: extract from body
        body = soup.find("body")
        if body:
            return " ".join(body.get_text().split())

        # Last resort: extract all text
        return " ".join(soup.get_text().split())

    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text content.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned and normalized text
        """
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common PDF artifacts
        text = re.sub(r"[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'àèéìíîòóùúÀÈÉÌÍÎÒÓÙÚâêôûÂÊÔÛäëïöüÄËÏÖÜçÇñÑ]", " ", text)

        # Normalize Italian accents and special characters
        text = self._normalize_italian_text(text)

        # Remove multiple spaces
        text = re.sub(r" +", " ", text)

        # Trim whitespace
        text = text.strip()

        return text

    def _normalize_italian_text(self, text: str) -> str:
        """Normalize Italian text for better processing.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Preserve Italian accented characters
        # This is a basic normalization - in production you might use
        # more sophisticated text normalization libraries

        # Remove page numbers and common PDF artifacts
        text = re.sub(r"\b\d+\b(?=\s*$)", "", text, flags=re.MULTILINE)

        # Normalize common Italian abbreviations
        replacements = {
            "art\.": "articolo",
            "artt\.": "articoli",
            "lett\.": "lettera",
            "c\.": "comma",
            "co\.": "comma",
            "n\.": "numero",
            "D\.L\.": "Decreto Legge",
            "D\.Lgs\.": "Decreto Legislativo",
        }

        for abbrev, full in replacements.items():
            text = re.sub(abbrev, full, text, flags=re.IGNORECASE)

        return text

    def _determine_document_type_from_header(self, content_type: str, document_url: str) -> str:
        """Determine document type from content-type header and URL.

        Priority: content-type header > URL extension

        Args:
            content_type: HTTP content-type header value
            document_url: Document URL (fallback)

        Returns:
            Document type (pdf, html, xml, etc.)
        """
        # Check content-type header first (most reliable)
        if "application/pdf" in content_type:
            return "pdf"
        elif "text/html" in content_type or "application/xhtml" in content_type:
            return "html"
        elif "text/xml" in content_type or "application/xml" in content_type:
            return "xml"

        # Fallback to URL-based detection
        return self._determine_document_type(document_url)

    def _determine_document_type(self, document_url: str) -> str:
        """Determine document type from URL.

        Args:
            document_url: Document URL

        Returns:
            Document type (pdf, html, xml, etc.)
        """
        parsed_url = urlparse(document_url)
        path = parsed_url.path.lower()

        if path.endswith(".pdf"):
            return "pdf"
        elif path.endswith((".html", ".htm")):
            return "html"
        elif path.endswith(".xml"):
            return "xml"
        elif "pdf" in path:
            return "pdf"
        elif any(format_type in path for format_type in [".aspx", ".jsp", ".php"]):
            return "html"
        else:
            # Default to HTML for web pages
            return "html"

    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash of content for duplicate detection.

        Args:
            content: Text content

        Returns:
            SHA256 hash string
        """
        if not content:
            return ""

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _extract_content_metadata(self, content: str, document_url: str) -> Dict[str, Any]:
        """Extract metadata from document content.

        Args:
            content: Extracted text content
            document_url: Original document URL

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {
            "url": document_url,
            "extraction_date": datetime.now().isoformat(),
            "content_length": len(content),
            "word_count": len(content.split()) if content else 0,
        }

        if content:
            # Extract common Italian regulatory document patterns

            # Look for document numbers
            doc_number_match = re.search(
                r"(?:Circolare|Risoluzione|Decreto)\s+n?\.?\s*(\d+(?:/[A-Z])?)", content, re.IGNORECASE
            )
            if doc_number_match:
                metadata["document_number"] = doc_number_match.group(1)

            # Look for dates
            date_patterns = [
                r"(\d{1,2})\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
                r"(\d{1,2})/(\d{1,2})/(\d{4})",
                r"(\d{4})-(\d{1,2})-(\d{1,2})",
            ]

            for pattern in date_patterns:
                date_match = re.search(pattern, content, re.IGNORECASE)
                if date_match:
                    metadata["document_date"] = date_match.group(0)
                    break

            # Extract key topics (simple keyword extraction)
            italian_tax_keywords = [
                "IVA",
                "imposta",
                "dichiarazione",
                "redditi",
                "società",
                "fattura",
                "contributi",
                "detrazioni",
                "deduzioni",
                "aliquota",
                "codice fiscale",
                "partita IVA",
                "INPS",
                "INAIL",
                "F24",
                "modello",
                "scadenza",
            ]

            found_keywords = []
            content_lower = content.lower()
            for keyword in italian_tax_keywords:
                if keyword.lower() in content_lower:
                    found_keywords.append(keyword)

            if found_keywords:
                metadata["topics"] = found_keywords[:10]  # Limit to 10 topics

            # Extract authority information
            if "agenzia delle entrate" in content_lower:
                metadata["authority"] = "Agenzia delle Entrate"
            elif "inps" in content_lower:
                metadata["authority"] = "INPS"
            elif "inail" in content_lower:
                metadata["authority"] = "INAIL"
            elif "gazzetta ufficiale" in content_lower:
                metadata["authority"] = "Gazzetta Ufficiale"

        return metadata


# Utility functions for external use


async def extract_pdf_content(pdf_url: str) -> str:
    """Convenience function to extract PDF content.

    Args:
        pdf_url: URL of PDF document

    Returns:
        Extracted text content
    """
    async with DocumentProcessor() as processor:
        return await processor.extract_content_from_pdf(pdf_url)


async def extract_html_content(html_url: str) -> str:
    """Convenience function to extract HTML content.

    Args:
        html_url: URL of HTML document

    Returns:
        Extracted text content
    """
    async with DocumentProcessor() as processor:
        return await processor.extract_content_from_html(html_url)


# Create shared instance
document_processor = DocumentProcessor()
