#!/usr/bin/env python
"""Re-ingest a critical law with article-level parsing (ADR-023).

This script re-ingests critical Italian laws using the TieredIngestionService,
which provides article-level parsing for better RAG retrieval.

Usage:
    # Re-ingest from a PDF file
    python scripts/reingest_critical_law.py \\
        --title "LEGGE 30 dicembre 2025, n. 199" \\
        --pdf /path/to/legge_bilancio_2026.pdf

    # Re-ingest from a URL (Gazzetta Ufficiale)
    python scripts/reingest_critical_law.py \\
        --title "LEGGE 30 dicembre 2025, n. 199" \\
        --url "https://www.gazzettaufficiale.it/..."

    # Re-ingest from existing database content
    python scripts/reingest_critical_law.py \\
        --title "LEGGE 30 dicembre 2025, n. 199" \\
        --from-db

    # Dry run (show what would be done)
    python scripts/reingest_critical_law.py \\
        --title "LEGGE 30 dicembre 2025, n. 199" \\
        --pdf /path/to/file.pdf \\
        --dry-run

Related to:
    - DEV-242: Response Quality & Suggested Actions Fixes
    - ADR-023: Tiered Document Ingestion
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def extract_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text content
    """
    from app.services.document_processor import extract_text_from_pdf

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    print(f"Extracting text from PDF: {pdf_path}")
    content = await extract_text_from_pdf(str(path))
    print(f"Extracted {len(content)} characters")

    return content


async def fetch_from_url(url: str) -> str:
    """Fetch and extract document from URL.

    Args:
        url: Document URL (e.g., Gazzetta Ufficiale)

    Returns:
        Extracted text content
    """
    import httpx

    print(f"Fetching document from URL: {url}")

    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        # If it's a PDF, extract text
        if "application/pdf" in response.headers.get("content-type", ""):
            from io import BytesIO

            from app.services.document_processor import extract_text_from_pdf_bytes

            content = await extract_text_from_pdf_bytes(BytesIO(response.content))
        else:
            # Assume HTML, extract text
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")
            content = soup.get_text(separator="\n")

    print(f"Fetched {len(content)} characters")
    return content


async def get_existing_content(title_pattern: str) -> str | None:
    """Get existing document content from database.

    Args:
        title_pattern: SQL LIKE pattern to find the document

    Returns:
        Combined content from existing chunks, or None
    """
    from sqlalchemy import text

    from app.models.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT content FROM knowledge_items
                WHERE title ILIKE :pattern
                ORDER BY id
            """
            ),
            {"pattern": f"%{title_pattern}%"},
        )
        rows = result.fetchall()

        if not rows:
            print(f"No existing records found for: {title_pattern}")
            return None

        print(f"Found {len(rows)} existing records")
        content = "\n\n".join(row[0] for row in rows if row[0])
        print(f"Combined content: {len(content)} characters")
        return content


async def delete_existing(title_pattern: str, dry_run: bool = False) -> int:
    """Delete existing records matching the title pattern.

    Args:
        title_pattern: SQL LIKE pattern
        dry_run: If True, don't actually delete

    Returns:
        Number of records deleted (or would be deleted)
    """
    from sqlalchemy import text

    from app.models.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Count existing records
        result = await db.execute(
            text("SELECT COUNT(*) FROM knowledge_items WHERE title ILIKE :pattern"),
            {"pattern": f"%{title_pattern}%"},
        )
        count = result.scalar()

        if dry_run:
            print(f"[DRY RUN] Would delete {count} existing records")
            return count

        if count > 0:
            # First delete related knowledge_chunks (foreign key constraint)
            await db.execute(
                text(
                    """
                    DELETE FROM knowledge_chunks
                    WHERE knowledge_item_id IN (
                        SELECT id FROM knowledge_items WHERE title ILIKE :pattern
                    )
                    """
                ),
                {"pattern": f"%{title_pattern}%"},
            )
            # Then delete the knowledge_items
            await db.execute(
                text("DELETE FROM knowledge_items WHERE title ILIKE :pattern"),
                {"pattern": f"%{title_pattern}%"},
            )
            await db.commit()
            print(f"Deleted {count} existing records")

        return count


async def reingest_law(
    title: str,
    content: str,
    source: str = "gazzetta_ufficiale_reingest",
    publication_date: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Re-ingest a law with tiered ingestion.

    Args:
        title: Law title
        content: Full law content
        source: Source identifier
        publication_date: Publication date (YYYY-MM-DD)
        dry_run: If True, don't actually ingest

    Returns:
        Ingestion result dictionary
    """
    from app.models.database import AsyncSessionLocal
    from app.services.tiered_ingestion_service import TieredIngestionService

    if dry_run:
        # Just classify and show what would happen
        from app.services.document_classifier import DocumentClassifier
        from app.services.italian_law_parser import ItalianLawParser

        classifier = DocumentClassifier()
        parser = ItalianLawParser()

        classification = classifier.classify(title, source, content[:500])
        parsed = parser.parse(content, title)

        print("\n[DRY RUN] Would ingest with:")
        print(f"  Title: {title}")
        print(f"  Tier: {classification.tier.value} ({classification.tier.name})")
        print(f"  Strategy: {classification.parsing_strategy}")
        print(f"  Confidence: {classification.confidence}")
        print(f"  Topics detected: {classification.detected_topics}")
        print(f"  Articles to parse: {len(parsed.articles)}")
        print(f"  Allegati: {len(parsed.allegati)}")
        print(f"  Law number: {parsed.law_number}")

        if parsed.articles:
            print("\n  First 5 articles:")
            for article in parsed.articles[:5]:
                print(f"    - {article.display_title}")
                if article.topics:
                    print(f"      Topics: {article.topics}")

        return {
            "dry_run": True,
            "tier": classification.tier.value,
            "articles": len(parsed.articles),
            "topics": classification.detected_topics,
        }

    # Actually ingest
    async with AsyncSessionLocal() as db:
        service = TieredIngestionService(db_session=db)

        result = await service.ingest(
            title=title,
            content=content,
            source=source,
            publication_date=publication_date,
            category="legge",
        )

        print("\nIngestion complete:")
        print(f"  Document ID: {result.document_id}")
        print(f"  Tier: {result.tier}")
        print(f"  Items created: {result.items_created}")
        print(f"  Articles parsed: {result.articles_parsed}")
        print(f"  Topics: {result.topics_detected}")
        print(f"  Strategy: {result.parsing_strategy}")

        return {
            "document_id": result.document_id,
            "tier": result.tier,
            "items_created": result.items_created,
            "articles_parsed": result.articles_parsed,
            "topics": result.topics_detected,
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Re-ingest a critical law with article-level parsing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--title",
        required=True,
        help="Law title (e.g., 'LEGGE 30 dicembre 2025, n. 199')",
    )

    # Content sources (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--pdf",
        help="Path to PDF file",
    )
    source_group.add_argument(
        "--url",
        help="URL to fetch document from",
    )
    source_group.add_argument(
        "--from-db",
        action="store_true",
        help="Use existing content from database",
    )
    source_group.add_argument(
        "--text-file",
        help="Path to plain text file",
    )

    parser.add_argument(
        "--source",
        default="gazzetta_ufficiale_reingest",
        help="Source identifier for the document",
    )
    parser.add_argument(
        "--publication-date",
        help="Publication date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Don't delete existing records before re-ingesting",
    )

    args = parser.parse_args()

    # Get content
    content = None

    if args.pdf:
        content = await extract_from_pdf(args.pdf)
    elif args.url:
        content = await fetch_from_url(args.url)
    elif args.from_db:
        content = await get_existing_content(args.title)
        if not content:
            print("ERROR: No existing content found in database")
            sys.exit(1)
    elif args.text_file:
        path = Path(args.text_file)
        if not path.exists():
            print(f"ERROR: Text file not found: {args.text_file}")
            sys.exit(1)
        content = path.read_text()
        print(f"Read {len(content)} characters from {args.text_file}")

    if not content:
        print("ERROR: No content to ingest")
        sys.exit(1)

    # Delete existing records unless --keep-existing
    if not args.keep_existing:
        await delete_existing(args.title, dry_run=args.dry_run)

    # Re-ingest
    result = await reingest_law(
        title=args.title,
        content=content,
        source=args.source,
        publication_date=args.publication_date,
        dry_run=args.dry_run,
    )

    return result


if __name__ == "__main__":
    asyncio.run(main())
