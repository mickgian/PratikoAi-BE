#!/usr/bin/env python3
"""Re-ingest a single Gazzetta Ufficiale document.

Usage:
    python scripts/reingest_gazzetta_document.py <url>

Example:
    python scripts/reingest_gazzetta_document.py http://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00212/SG
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.document_ingestion import (
    download_and_extract_document,
    ingest_document_with_chunks,
)
from app.models.knowledge import KnowledgeItem
from app.models.knowledge_chunk import KnowledgeChunk


async def delete_existing_document(session: AsyncSession, url: str) -> bool:
    """Delete existing document and its chunks by URL.

    Args:
        session: Database session
        url: Document URL to delete

    Returns:
        True if document was deleted, False if not found
    """
    # Find the knowledge item
    result = await session.execute(select(KnowledgeItem).where(KnowledgeItem.source_url == url))
    item = result.scalar_one_or_none()

    if not item:
        print(f"⚠️  Document not found in database: {url}")
        return False

    print(f"🗑️  Deleting existing document: {item.title}")
    print(f"   ID: {item.id}")

    # Delete chunks first (foreign key constraint)
    await session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.knowledge_item_id == item.id))

    # Delete the knowledge item
    await session.execute(delete(KnowledgeItem).where(KnowledgeItem.id == item.id))

    await session.commit()
    print("✅ Deleted existing document and its chunks")
    return True


async def reingest_document(session: AsyncSession, url: str) -> bool:
    """Re-ingest a document from URL.

    Args:
        session: Database session
        url: Document URL to ingest

    Returns:
        True if successful, False otherwise
    """
    print(f"\n📥 Downloading and extracting: {url}")

    # Download and extract (will use PDF fallback for Gazzetta Ufficiale)
    extraction_result = await download_and_extract_document(url)

    if not extraction_result:
        print(f"❌ Failed to extract content from: {url}")
        return False

    content = extraction_result["content"]
    print(f"✅ Extracted {len(content):,} characters")
    print(f"   Method: {extraction_result['extraction_method']}")

    # Preview content
    preview = content[:500].replace("\n", " ")
    print(f"   Preview: {preview}...")

    # Check if it contains rottamazione
    if "rottamazione" in content.lower():
        print("✅ Content contains 'rottamazione' - this is the correct content!")
    else:
        print("⚠️  Content does NOT contain 'rottamazione' - may be incomplete")

    # Ingest with chunking
    print("\n📝 Ingesting document...")

    # Extract title from content or URL
    title = "LEGGE 30 dicembre 2025, n. 199"  # Default title

    result = await ingest_document_with_chunks(
        session=session,
        title=title,
        url=url,
        content=content,
        extraction_method=extraction_result["extraction_method"],
        text_quality=extraction_result.get("text_quality"),
        ocr_pages=extraction_result.get("ocr_pages", []),
        source="gazzetta_ufficiale_reingest",
        category="regulatory_documents",
        subcategory="gazzetta_ufficiale",
    )

    if result:
        print(f"✅ Successfully ingested with ID: {result}")
        return True
    else:
        print("❌ Failed to ingest document")
        return False


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/reingest_gazzetta_document.py <url>")
        print(
            "Example: python scripts/reingest_gazzetta_document.py http://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00212/SG"
        )
        sys.exit(1)

    url = sys.argv[1]

    # Convert sync URL to async URL
    postgres_url = settings.POSTGRES_URL
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session_maker() as session:
            print("=" * 80)
            print("Gazzetta Ufficiale Document Re-Ingestion")
            print("=" * 80)
            print(f"URL: {url}")
            print("=" * 80)

            # Delete existing document first
            await delete_existing_document(session, url)

            # Re-ingest
            success = await reingest_document(session, url)

            print()
            print("=" * 80)
            if success:
                print("✅ Re-ingestion completed successfully!")
            else:
                print("❌ Re-ingestion failed!")
            print("=" * 80)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
