#!/usr/bin/env python3
"""DEV-244: Fix wrong document code for Legge 199/2025.

The RSS feed stored the wrong code (25G00217 instead of 25G00212).
This script fixes the source_url for all Legge 199/2025 documents.

Correct URL: https://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00212/SG
Wrong URL:   https://www.gazzettaufficiale.it/eli/id/2025/12/30/25G00217/sg

Usage:
    uv run python scripts/fix_legge_199_code.py

    # Or with Docker:
    docker-compose exec app bash -c ". .venv/bin/activate && python scripts/fix_legge_199_code.py"
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


async def fix_knowledge_items(session: AsyncSession) -> int:
    """Fix wrong Gazzetta code in knowledge_items table.

    Returns:
        Number of URLs fixed
    """
    # Find all documents with wrong code
    result = await session.execute(
        text(
            "SELECT id, source_url FROM knowledge_items "
            "WHERE source_url LIKE '%gazzettaufficiale.it/eli/id/2025/12/30/25G00217%'"
        )
    )
    rows = result.fetchall()
    print(f"Found {len(rows)} knowledge_items with wrong code 25G00217")

    fixed = 0
    for row in rows:
        item_id, old_url = row
        # Replace wrong code with correct code
        new_url = old_url.replace("25G00217", "25G00212")
        # Also fix case: sg -> SG
        new_url = new_url.replace("/sg", "/SG")
        await session.execute(
            text("UPDATE knowledge_items SET source_url = :url WHERE id = :id"),
            {"url": new_url, "id": item_id},
        )
        fixed += 1
        if fixed <= 3:  # Show first 3
            print(f"  [{item_id}] Fixed: {new_url[:70]}...")

    return fixed


async def fix_knowledge_chunks(session: AsyncSession) -> int:
    """Fix wrong Gazzetta code in knowledge_chunks table.

    Returns:
        Number of URLs fixed
    """
    # Find all chunks with wrong code
    result = await session.execute(
        text(
            "SELECT id, source_url FROM knowledge_chunks "
            "WHERE source_url LIKE '%gazzettaufficiale.it/eli/id/2025/12/30/25G00217%'"
        )
    )
    rows = result.fetchall()
    print(f"Found {len(rows)} knowledge_chunks with wrong code 25G00217")

    fixed = 0
    for row in rows:
        chunk_id, old_url = row
        # Replace wrong code with correct code
        new_url = old_url.replace("25G00217", "25G00212")
        # Also fix case: sg -> SG
        new_url = new_url.replace("/sg", "/SG")
        await session.execute(
            text("UPDATE knowledge_chunks SET source_url = :url WHERE id = :id"),
            {"url": new_url, "id": chunk_id},
        )
        fixed += 1

    return fixed


async def main():
    """Run the fix."""
    print("DEV-244: Fixing wrong document code for Legge 199/2025")
    print("=" * 60)
    print("Wrong code: 25G00217 (RSS feed error)")
    print("Correct code: 25G00212 (verified on gazzettaufficiale.it)")
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
            # Fix knowledge_items
            items_fixed = await fix_knowledge_items(session)
            print(f"Fixed {items_fixed} URLs in knowledge_items")

            # Fix knowledge_chunks
            chunks_fixed = await fix_knowledge_chunks(session)
            print(f"Fixed {chunks_fixed} URLs in knowledge_chunks")

            # Commit all changes
            await session.commit()
            print("=" * 60)
            print(f"Fix complete! Total URLs fixed: {items_fixed + chunks_fixed}")

        except Exception as e:
            print(f"Error during fix: {e}")
            await session.rollback()
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
