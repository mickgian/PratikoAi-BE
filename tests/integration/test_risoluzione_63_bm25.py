#!/usr/bin/env python3
"""Focused investigation: Why BM25 search fails for Risoluzione 63."""

import asyncio
import os
import sys

# Add project root to path (2 levels up from tests/integration/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import text

from app.models.database import AsyncSessionLocal


async def test_bm25_searches():
    """Test BM25 searches with different query patterns."""
    print("\n" + "=" * 80)
    print("TEST: PostgreSQL FTS Search for Risoluzione 63")
    print("=" * 80 + "\n")

    test_queries = [
        ("risoluzione 63", "Basic query"),
        ("risoluzion 63", "Stemmed Italian"),
        ("63", "Number only"),
        ("risoluzione", "Document type only"),
        ("risoluzione & 63", "AND operator"),
        ("risoluzione | 63", "OR operator"),
    ]

    async with AsyncSessionLocal() as session:
        print("Document ID 82: Risoluzione n. 63")
        print("Title: 'Istituzione dei codici tributo... (risoluzione n. 63)'")
        print("Source: agenzia_entrate_normativa\n")

        for search_query, description in test_queries:
            print(f"Query: '{search_query}' ({description})")
            print("-" * 80)

            # Test 1: BM25 with organization filter
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        title,
                        ts_rank(search_vector, query) AS rank
                    FROM
                        knowledge_items,
                        websearch_to_tsquery('italian', :search_term) query
                    WHERE
                        search_vector @@ query
                        AND source LIKE 'agenzia_entrate%'
                    ORDER BY
                        rank DESC
                    LIMIT 5
                """),
                {"search_term": search_query},
            )
            docs = result.fetchall()

            if docs:
                print(f"  ✅ WITH org filter: Found {len(docs)} result(s)")
                for doc in docs:
                    title_short = doc.title[:70] + "..." if len(doc.title) > 70 else doc.title
                    has_63 = "(ID 82)" if doc.id == 82 else ""
                    print(f"     • ID {doc.id} {has_63}: {title_short}")
                    print(f"       Rank: {doc.rank:.4f}")
            else:
                print("  ❌ WITH org filter: NO results")

            # Test 2: BM25 without organization filter
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        title,
                        source,
                        ts_rank(search_vector, query) AS rank
                    FROM
                        knowledge_items,
                        websearch_to_tsquery('italian', :search_term) query
                    WHERE
                        search_vector @@ query
                    ORDER BY
                        rank DESC
                    LIMIT 5
                """),
                {"search_term": search_query},
            )
            docs = result.fetchall()

            if docs:
                print(f"  ✅ WITHOUT org filter: Found {len(docs)} result(s)")
                for doc in docs:
                    title_short = doc.title[:70] + "..." if len(doc.title) > 70 else doc.title
                    has_63 = "(ID 82)" if doc.id == 82 else ""
                    print(f"     • ID {doc.id} {has_63}: {title_short}")
                    print(f"       Source: {doc.source}, Rank: {doc.rank:.4f}")
            else:
                print("  ❌ WITHOUT org filter: NO results")

            print()

        # Test 3: Direct title filter (bypassing FTS)
        print("\nTest: SQL LIKE filter on title (bypass FTS)")
        print("-" * 80)

        result = await session.execute(
            text("""
                SELECT
                    id,
                    title,
                    source
                FROM knowledge_items
                WHERE
                    (title ILIKE '%n. 63%' OR title ILIKE '%n.63%' OR title ILIKE '%risoluzione% 63%')
                    AND source LIKE 'agenzia_entrate%'
                ORDER BY updated_at DESC
                LIMIT 5
            """)
        )
        docs = result.fetchall()

        if docs:
            print(f"✅ LIKE filter: Found {len(docs)} result(s)")
            for doc in docs:
                has_63 = "(ID 82)" if doc.id == 82 else ""
                print(f"   • ID {doc.id} {has_63}: {doc.title[:100]}")
        else:
            print("❌ LIKE filter: NO results")

        # Test 4: Check what's in the FTS vector for doc 82
        print("\n\nTest: What's in the FTS vector for Risoluzione 63?")
        print("-" * 80)

        result = await session.execute(
            text("""
                SELECT
                    id,
                    title,
                    to_tsvector('italian', title) as title_vector,
                    search_vector
                FROM knowledge_items
                WHERE id = 82
            """)
        )
        doc = result.fetchone()

        if doc:
            print(f"Document ID 82: {doc.title[:80]}...")
            print("\nTitle Vector (from title column):")
            print(f"  {doc.title_vector}")
            print("\nSearch Vector (full tsvector):")
            print(f"  {str(doc.search_vector)[:500]}...")

            # Check if '63' is in the vector
            if "63" in str(doc.search_vector):
                print("\n✅ Number '63' IS in search_vector")
            else:
                print("\n❌ Number '63' is NOT in search_vector")
                print("   This confirms: PostgreSQL FTS does NOT index numbers!")

            # Test if tsquery matches
            result = await session.execute(
                text("""
                    SELECT
                        search_vector @@ websearch_to_tsquery('italian', 'risoluzione 63') as matches_both,
                        search_vector @@ websearch_to_tsquery('italian', 'risoluzione') as matches_type,
                        search_vector @@ websearch_to_tsquery('italian', '63') as matches_number
                    FROM knowledge_items
                    WHERE id = 82
                """)
            )
            matches = result.fetchone()

            print("\nTSQuery Match Tests:")
            print(f"  'risoluzione 63' (AND): {matches.matches_both}")
            print(f"  'risoluzione' only: {matches.matches_type}")
            print(f"  '63' only: {matches.matches_number}")


async def main():
    """Run BM25 search investigation."""
    try:
        await test_bm25_searches()

        print("\n" + "=" * 80)
        print("ROOT CAUSE ANALYSIS")
        print("=" * 80)
        print("""
🔍 KEY FINDINGS:

1. PostgreSQL FTS (to_tsvector) does NOT index numbers like '63'
   - This is by design in PostgreSQL's text search system
   - Numbers are not considered searchable tokens

2. Query 'risoluzione 63' becomes an AND search:
   - Must match both 'risoluzione' AND '63'
   - Since '63' is not in tsvector, the AND fails
   - Result: NO documents found

3. SQL LIKE filter on title DOES work:
   - Direct string matching finds 'n. 63' in title
   - But this is not used in the FTS search path

4. Broader queries work because:
   - "tutte le risoluzioni" searches only for 'risoluzione' (no number)
   - This matches many documents including #63
   - No AND requirement with a non-indexed number

RECOMMENDED FIXES:

A. Strip numbers from FTS queries (already partially implemented)
   - Before: "risoluzione 63" → AND search fails
   - After: "risoluzione" → finds all resoluzioni
   - Then use SQL title filter for "n. 63"

B. Add explicit title filter for document number queries
   - Detect "risoluzione N" pattern
   - Add: WHERE title ILIKE '%n. N%'
   - This bypasses FTS for the number part

C. Use OR instead of AND for FTS (fallback)
   - Change websearch_to_tsquery to use OR
   - "risoluzione 63" → "risoluzione OR 63"
   - At least matches on 'risoluzione'

D. Extract numbers and use SQL filter (BEST)
   - Parse query: "risoluzione 63" → type="risoluzione", number="63"
   - FTS search: "risoluzione" only
   - SQL filter: title ILIKE '%n. 63%'
   - Hybrid approach uses both FTS and exact matching
        """)

    except Exception as e:
        print(f"\n❌ Investigation failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
