#!/usr/bin/env python3
"""DEV-244: One-time migration to fix broken Gazzetta URLs in knowledge_items.

The eli/id URL format (e.g., https://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00217/sg)
doesn't work for direct access. This script transforms them to the working atto format.

Usage:
    uv run python scripts/fix_gazzetta_urls.py

    # Or with Docker:
    docker-compose exec app python scripts/fix_gazzetta_urls.py
"""

import asyncio
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def transform_gazzetta_url(url: str) -> str:
    """Transform Gazzetta eli/id URL to working atto format.

    Args:
        url: Original URL (e.g., https://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00217/sg)

    Returns:
        Transformed URL or original if not a Gazzetta eli/id URL
    """
    match = re.match(
        r"https?://(?:www\.)?gazzettaufficiale\.it/eli/id/(\d{4})/(\d{2})/(\d{2})/([^/]+)",
        url,
    )
    if match:
        year, month, day, code = match.groups()
        # Remove trailing /sg, /SG, /s1, /S1, etc. from code
        code = re.sub(r"/[sS]\d*[gG]?$", "", code)
        return (
            f"https://www.gazzettaufficiale.it/atto/serie_generale/caricaDettaglioAtto/originario"
            f"?atto.dataPubblicazioneGazzetta={year}-{month}-{day}&atto.codiceRedazionale={code.upper()}"
        )
    return url


async def migrate_knowledge_items(session: AsyncSession) -> int:
    """Migrate broken Gazzetta URLs in knowledge_items table.

    Returns:
        Number of URLs updated
    """
    # Find all eli/id URLs in knowledge_items
    result = await session.execute(
        text("SELECT id, source_url FROM knowledge_items WHERE source_url LIKE '%gazzettaufficiale.it/eli/id/%'")
    )
    rows = result.fetchall()
    print(f"Found {len(rows)} Gazzetta URLs in knowledge_items to check")

    updated = 0
    for row in rows:
        item_id, old_url = row
        new_url = transform_gazzetta_url(old_url)
        if new_url != old_url:
            await session.execute(
                text("UPDATE knowledge_items SET source_url = :url WHERE id = :id"),
                {"url": new_url, "id": item_id},
            )
            updated += 1
            if updated <= 5:  # Show first 5 transformations
                print(f"  [{item_id}] {old_url[:60]}... -> {new_url[:60]}...")

    return updated


async def migrate_knowledge_chunks(session: AsyncSession) -> int:
    """Migrate broken Gazzetta URLs in knowledge_chunks table.

    Returns:
        Number of URLs updated
    """
    # Find all eli/id URLs in knowledge_chunks
    result = await session.execute(
        text("SELECT id, source_url FROM knowledge_chunks WHERE source_url LIKE '%gazzettaufficiale.it/eli/id/%'")
    )
    rows = result.fetchall()
    print(f"Found {len(rows)} Gazzetta URLs in knowledge_chunks to check")

    updated = 0
    for row in rows:
        chunk_id, old_url = row
        new_url = transform_gazzetta_url(old_url)
        if new_url != old_url:
            await session.execute(
                text("UPDATE knowledge_chunks SET source_url = :url WHERE id = :id"),
                {"url": new_url, "id": chunk_id},
            )
            updated += 1

    return updated


async def main():
    """Run the migration."""
    print("DEV-244: Fixing broken Gazzetta Ufficiale URLs")
    print("=" * 60)

    # Create async engine
    # Use POSTGRES_URL from settings (the async-compatible URL)
    db_url = settings.POSTGRES_URL
    if not db_url:
        print("Error: POSTGRES_URL not configured in settings")
        return

    # Ensure URL uses asyncpg driver
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Migrate knowledge_items
            items_updated = await migrate_knowledge_items(session)
            print(f"Updated {items_updated} URLs in knowledge_items")

            # Migrate knowledge_chunks
            chunks_updated = await migrate_knowledge_chunks(session)
            print(f"Updated {chunks_updated} URLs in knowledge_chunks")

            # Commit all changes
            await session.commit()
            print("=" * 60)
            print(f"Migration complete! Total URLs updated: {items_updated + chunks_updated}")

        except Exception as e:
            print(f"Error during migration: {e}")
            await session.rollback()
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
