"""
Backfill publication_date for existing knowledge_items.

Extracts dates from document content for existing records that don't have publication_date set.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.text.date_parser import extract_publication_date
from app.models.database import AsyncSessionLocal
from app.models.knowledge import KnowledgeItem


async def backfill_publication_dates():
    """Backfill publication_date for all knowledge_items without it."""
    async with AsyncSessionLocal() as session:
        # Find all items without publication_date
        result = await session.execute(select(KnowledgeItem).where(KnowledgeItem.publication_date is None))
        items = result.scalars().all()

        print(f"\n📋 Found {len(items)} items without publication_date")

        if not items:
            print("✅ No items to backfill")
            return

        updated = 0
        failed = 0

        for idx, item in enumerate(items, 1):
            # Extract publication date from content
            pub_date = extract_publication_date(item.content, item.title)

            if pub_date:
                item.publication_date = pub_date
                updated += 1
                print(f"  [{idx}/{len(items)}] ✅ {item.title[:60]}... → {pub_date}")
            else:
                failed += 1
                print(f"  [{idx}/{len(items)}] ⚠️  {item.title[:60]}... → No date found")

            # Commit every 10 items
            if idx % 10 == 0:
                await session.commit()
                print(f"\n💾 Committed {idx}/{len(items)} items\n")

        # Final commit
        await session.commit()

        print("\n✅ Backfill complete:")
        print(f"   - Updated: {updated} items")
        print(f"   - No date found: {failed} items")
        print(f"   - Total processed: {len(items)} items")


if __name__ == "__main__":
    asyncio.run(backfill_publication_dates())
