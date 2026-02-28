#!/usr/bin/env python
"""Test script for Cassazione scraper with detailed reporting."""

import asyncio
import sys

sys.path.insert(0, "/Users/micky/PycharmProjects/PratikoAi-BE")

from app.models.database import AsyncSessionLocal
from app.services.scrapers.cassazione_scraper import CassazioneScraper, CourtSection


async def test_cassazione_scraper():
    """Run Cassazione scraper with detailed reporting."""
    print("=" * 80)
    print("CASSAZIONE SCRAPER TEST - DETAILED REPORT")
    print("=" * 80)

    async with AsyncSessionLocal() as session, CassazioneScraper(
        db_session=session,
        rate_limit_delay=2.0,
    ) as scraper:
        print("\n[1] SCRAPING LIST PAGES...")
        print("-" * 40)

        # First, let's see what's on the list page
        list_decisions = await scraper._scrape_list_page(scraper.CIVIL_LIST_URL, page=1)

        print(f"Found {len(list_decisions)} decisions on first page")
        print(f"Source URL: {scraper.CIVIL_LIST_URL}")
        print()

        # Show first 10 decisions from list
        print("[2] DECISIONS FOUND ON LIST PAGE (first 10):")
        print("-" * 40)
        for i, dec in enumerate(list_decisions[:10], 1):
            print(f"{i}. Number: {dec.get('decision_number')}")
            print(f"   Date: {dec.get('decision_date')}")
            print(f"   Type: {dec.get('decision_type')}")
            print(f"   Section: {dec.get('section')}")
            print(f"   Content ID: {dec.get('content_id')}")
            print(f"   URL: {dec.get('url')}")
            print()

        # Now scrape with limit
        print("\n[3] SCRAPING DETAILS (limit=3, Tax+Labor sections)...")
        print("-" * 40)

        result = await scraper.scrape_recent_decisions(
            sections=[CourtSection.TRIBUTARIA, CourtSection.LAVORO],
            days_back=30,  # Last 30 days
            limit=3,
        )

        print("\nScraping Result:")
        print(f"  - Decisions Found: {result.decisions_found}")
        print(f"  - Decisions Processed: {result.decisions_processed}")
        print(f"  - Decisions Saved: {result.decisions_saved}")
        print(f"  - Errors: {result.errors}")
        print(f"  - Duration: {result.duration_seconds}s")

    # Now check what was saved to database
    print("\n[4] DOCUMENTS STORED IN DATABASE:")
    print("-" * 40)

    async with AsyncSessionLocal() as session:
        from sqlalchemy import text

        result = await session.execute(
            text("""
            SELECT id, title, source, source_url, created_at
            FROM knowledge_items
            WHERE source = 'cassazione'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        )
        rows = result.fetchall()

        if rows:
            for row in rows:
                print(f"ID: {row[0]}")
                print(f"  Title: {row[1][:80]}..." if len(row[1]) > 80 else f"  Title: {row[1]}")
                print(f"  Source: {row[2]}")
                print(f"  URL: {row[3]}")
                print(f"  Created: {row[4]}")
                print()
        else:
            print("No Cassazione documents found in database yet.")

        # Also check chunks
        result2 = await session.execute(
            text("""
            SELECT COUNT(*) FROM knowledge_chunks kc
            JOIN knowledge_items ki ON ki.id = kc.knowledge_item_id
            WHERE ki.source = 'cassazione'
        """)
        )
        chunk_count = result2.scalar()
        print(f"\nTotal chunks for Cassazione documents: {chunk_count}")


if __name__ == "__main__":
    asyncio.run(test_cassazione_scraper())
