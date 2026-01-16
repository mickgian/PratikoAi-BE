#!/usr/bin/env python3
"""DEV-244: Revert Gazzetta URL transformation.

The transformation to atto/serie_generale format was incorrect.
The eli/id format works fine - this script reverts the URLs back.

Usage:
    uv run python scripts/revert_gazzetta_urls.py

    # Or with Docker:
    docker-compose exec app python scripts/revert_gazzetta_urls.py
"""

import asyncio
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def revert_gazzetta_url(url: str) -> str:
    """Transform atto format back to eli/id format.

    Args:
        url: Transformed URL in atto/serie_generale format

    Returns:
        Original eli/id format URL or unchanged if not matching
    """
    parsed = urlparse(url)
    if "atto/serie_generale/caricaDettaglioAtto" in parsed.path:
        params = parse_qs(parsed.query)
        date = params.get("atto.dataPubblicazioneGazzetta", [""])[0]  # 2025-12-30
        code = params.get("atto.codiceRedazionale", [""])[0]  # 25G00217
        if date and code:
            year, month, day = date.split("-")
            return f"https://www.gazzettaufficiale.it/eli/id/{year}/{month}/{day}/{code}/sg"
    return url


async def revert_knowledge_items(session: AsyncSession) -> int:
    """Revert transformed Gazzetta URLs in knowledge_items table.

    Returns:
        Number of URLs reverted
    """
    # Find all transformed URLs
    result = await session.execute(
        text(
            "SELECT id, source_url FROM knowledge_items "
            "WHERE source_url LIKE '%gazzettaufficiale.it/atto/serie_generale/caricaDettaglioAtto%'"
        )
    )
    rows = result.fetchall()
    print(f"Found {len(rows)} transformed URLs in knowledge_items to revert")

    reverted = 0
    for row in rows:
        item_id, old_url = row
        new_url = revert_gazzetta_url(old_url)
        if new_url != old_url:
            await session.execute(
                text("UPDATE knowledge_items SET source_url = :url WHERE id = :id"),
                {"url": new_url, "id": item_id},
            )
            reverted += 1
            if reverted <= 5:  # Show first 5 reversions
                print(f"  [{item_id}] Reverted to: {new_url[:70]}...")

    return reverted


async def revert_knowledge_chunks(session: AsyncSession) -> int:
    """Revert transformed Gazzetta URLs in knowledge_chunks table.

    Returns:
        Number of URLs reverted
    """
    # Find all transformed URLs
    result = await session.execute(
        text(
            "SELECT id, source_url FROM knowledge_chunks "
            "WHERE source_url LIKE '%gazzettaufficiale.it/atto/serie_generale/caricaDettaglioAtto%'"
        )
    )
    rows = result.fetchall()
    print(f"Found {len(rows)} transformed URLs in knowledge_chunks to revert")

    reverted = 0
    for row in rows:
        chunk_id, old_url = row
        new_url = revert_gazzetta_url(old_url)
        if new_url != old_url:
            await session.execute(
                text("UPDATE knowledge_chunks SET source_url = :url WHERE id = :id"),
                {"url": new_url, "id": chunk_id},
            )
            reverted += 1

    return reverted


async def main():
    """Run the revert migration."""
    print("DEV-244: Reverting Gazzetta URL transformation")
    print("=" * 60)
    print("The eli/id format works - reverting atto/ format back to eli/id")
    print("=" * 60)

    # Create async engine
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
            # Revert knowledge_items
            items_reverted = await revert_knowledge_items(session)
            print(f"Reverted {items_reverted} URLs in knowledge_items")

            # Revert knowledge_chunks
            chunks_reverted = await revert_knowledge_chunks(session)
            print(f"Reverted {chunks_reverted} URLs in knowledge_chunks")

            # Commit all changes
            await session.commit()
            print("=" * 60)
            print(f"Revert complete! Total URLs reverted: {items_reverted + chunks_reverted}")

        except Exception as e:
            print(f"Error during revert: {e}")
            await session.rollback()
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
