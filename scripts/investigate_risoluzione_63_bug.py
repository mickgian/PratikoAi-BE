#!/usr/bin/env python3
"""Investigation Script: Risoluzione 63 Search Bug

This script investigates why "Di cosa parla la risoluzione 63 dell'agenzia delle entrate?"
returns "Non ho trovato la Risoluzione n. 63 nel database" when the document exists
and is found by broader queries.

Investigation Steps:
1. Verify document exists in database
2. Test query normalization
3. Test BM25 search with different parameters
4. Compare with working broader query
5. Identify root cause
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AsyncSessionLocal
from app.services.knowledge_search_service import KnowledgeSearchService
from app.services.query_normalizer import QueryNormalizer


async def verify_document_exists():
    """Step 1: Verify Risoluzione 63 exists in the database."""
    print("=" * 80)
    print("STEP 1: VERIFY DOCUMENT EXISTS")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        # Search for any document with "63" in title
        result = await session.execute(
            text("""
                SELECT
                    id,
                    title,
                    source,
                    category,
                    publication_date,
                    created_at,
                    updated_at,
                    LENGTH(content) as content_length
                FROM knowledge_items
                WHERE title ILIKE '%63%'
                    AND (
                        title ILIKE '%risoluzione%'
                        OR title ILIKE '%risoluzion%'
                        OR category ILIKE '%risoluz%'
                    )
                ORDER BY updated_at DESC
                LIMIT 5
            """)
        )
        docs = result.fetchall()

        if docs:
            print(f"\n✅ Found {len(docs)} document(s) matching 'risoluzione' and '63':\n")
            for doc in docs:
                print(f"  ID: {doc.id}")
                print(f"  Title: {doc.title}")
                print(f"  Source: {doc.source}")
                print(f"  Category: {doc.category}")
                print(f"  Publication Date: {doc.publication_date}")
                print(f"  Content Length: {doc.content_length} chars")
                print(f"  Created: {doc.created_at}")
                print(f"  Updated: {doc.updated_at}")
                print()
        else:
            print("\n❌ NO documents found matching 'risoluzione' and '63'")
            print("   This means the document may not exist in the database.")

        # Also check for any document with "63" regardless of type
        result = await session.execute(
            text("""
                SELECT
                    id,
                    title,
                    source,
                    category
                FROM knowledge_items
                WHERE title ILIKE '%n. 63%' OR title ILIKE '%n.63%' OR title ILIKE '%numero 63%'
                ORDER BY updated_at DESC
                LIMIT 3
            """)
        )
        alt_docs = result.fetchall()

        if alt_docs:
            print(f"\n✅ Found {len(alt_docs)} document(s) with 'n. 63' pattern:\n")
            for doc in alt_docs:
                print(f"  ID: {doc.id}")
                print(f"  Title: {doc.title}")
                print(f"  Source: {doc.source}")
                print(f"  Category: {doc.category}")
                print()

        return docs if docs else []


async def check_knowledge_chunks():
    """Check if document has chunks in knowledge_chunks table."""
    print("=" * 80)
    print("STEP 2: CHECK KNOWLEDGE CHUNKS")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        # Check if knowledge_chunks table exists
        result = await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'knowledge_chunks'
                )
            """)
        )
        table_exists = result.scalar()

        if not table_exists:
            print("\nℹ️  knowledge_chunks table does not exist (may not be used)")
            return

        # Find chunks for risoluzione 63
        result = await session.execute(
            text("""
                SELECT
                    kc.id,
                    kc.knowledge_item_id,
                    ki.title,
                    kc.chunk_index,
                    LENGTH(kc.chunk_text) as chunk_length
                FROM knowledge_chunks kc
                JOIN knowledge_items ki ON ki.id = kc.knowledge_item_id
                WHERE ki.title ILIKE '%63%'
                    AND ki.title ILIKE '%risoluz%'
                ORDER BY kc.knowledge_item_id, kc.chunk_index
                LIMIT 10
            """)
        )
        chunks = result.fetchall()

        if chunks:
            print(f"\n✅ Found {len(chunks)} chunk(s) for Risoluzione 63:\n")
            for chunk in chunks:
                print(f"  Chunk ID: {chunk.id}")
                print(f"  Knowledge Item ID: {chunk.knowledge_item_id}")
                print(f"  Title: {chunk.title}")
                print(f"  Chunk Index: {chunk.chunk_index}")
                print(f"  Chunk Length: {chunk.chunk_length} chars")
                print()
        else:
            print("\n⚠️  No chunks found for Risoluzione 63")
            print("   Document may not be chunked or chunks not indexed")


async def test_query_normalization():
    """Step 3: Test query normalization with QueryNormalizer."""
    print("=" * 80)
    print("STEP 3: TEST QUERY NORMALIZATION")
    print("=" * 80)

    test_queries = [
        "Di cosa parla la risoluzione 63 dell'agenzia delle entrate?",
        "risoluzione 63",
        "risoluzione numero 63",
        "n. 63",
    ]

    normalizer = QueryNormalizer()

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            result = await normalizer.normalize(query)
            if result:
                print(f"  ✅ Normalized: {json.dumps(result, indent=4, ensure_ascii=False)}")
            else:
                print("  ⚠️  No normalization result (returned None)")
        except Exception as e:
            print(f"  ❌ Error: {e}")


async def test_bm25_search_direct():
    """Step 4: Test direct BM25 search with various query formats."""
    print("=" * 80)
    print("STEP 4: TEST DIRECT BM25 SEARCH")
    print("=" * 80)

    test_queries = [
        ("risoluzione 63", "Basic: document type + number"),
        ("risoluzion 63", "Stemmed: Italian plural form"),
        ("n. 63", "Abbreviated: n. + number"),
        ("numero 63", "Full form: numero + number"),
        ("63", "Number only"),
        ("risoluzione", "Document type only"),
        ("risoluzione & 63", "PostgreSQL AND syntax"),
        ("risoluzione | 63", "PostgreSQL OR syntax"),
    ]

    async with AsyncSessionLocal() as session:
        for search_query, description in test_queries:
            print(f"\n🔍 Test: {description}")
            print(f"   Query: '{search_query}'")

            try:
                # Test with websearch_to_tsquery (default)
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
                            AND source LIKE 'agenzia_entrate%'
                        ORDER BY
                            rank DESC
                        LIMIT 3
                    """),
                    {"search_term": search_query},
                )
                docs = result.fetchall()

                if docs:
                    print(f"   ✅ Found {len(docs)} result(s):")
                    for doc in docs:
                        title_short = doc.title[:60] + "..." if len(doc.title) > 60 else doc.title
                        print(f"      • {title_short} (rank: {doc.rank:.4f})")
                else:
                    print("   ❌ No results found")

            except Exception as e:
                print(f"   ❌ Error: {e}")

        # Test with title filter (SQL LIKE)
        print("\n🔍 Test: Title filter (SQL LIKE)")
        print("   Pattern: '%n. 63%'")

        try:
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        title,
                        source,
                        category
                    FROM knowledge_items
                    WHERE
                        title ILIKE '%n. 63%'
                        AND source LIKE 'agenzia_entrate%'
                    LIMIT 3
                """)
            )
            docs = result.fetchall()

            if docs:
                print(f"   ✅ Found {len(docs)} result(s):")
                for doc in docs:
                    print(f"      • {doc.title}")
            else:
                print("   ❌ No results found")

        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_knowledge_search_service():
    """Step 5: Test KnowledgeSearchService with actual query."""
    print("=" * 80)
    print("STEP 5: TEST KNOWLEDGE SEARCH SERVICE")
    print("=" * 80)

    test_queries = [
        {
            "query": "Di cosa parla la risoluzione 63 dell'agenzia delle entrate?",
            "description": "Full conversational query (failing case)",
            "canonical_facts": [],
        },
        {
            "query": "Di cosa parla la risoluzione 63 dell'agenzia delle entrate?",
            "description": "With canonical facts",
            "canonical_facts": ["Risoluzione n. 63", "Agenzia delle Entrate"],
        },
        {
            "query": "fammi un riassunto di tutte le risoluzioni dell'agenzia delle entrate di ottobre e novembre 2025",
            "description": "Broader aggregation query (working case)",
            "canonical_facts": [],
        },
    ]

    async with AsyncSessionLocal() as session:
        search_service = KnowledgeSearchService(db_session=session)

        for test_case in test_queries:
            print(f"\n🔍 Test: {test_case['description']}")
            print(f"   Query: '{test_case['query']}'")
            if test_case["canonical_facts"]:
                print(f"   Canonical Facts: {test_case['canonical_facts']}")

            query_data = {
                "query": test_case["query"],
                "canonical_facts": test_case["canonical_facts"],
                "user_id": "test_user",
                "session_id": "test_session",
                "trace_id": f"test_{datetime.now().timestamp()}",
                "search_mode": "hybrid",
                "filters": {},
                "max_results": 10,
            }

            try:
                results = await search_service.retrieve_topk(query_data)

                if results:
                    print(f"   ✅ Found {len(results)} result(s):")
                    for i, result in enumerate(results[:5], 1):
                        title_short = result.title[:60] + "..." if len(result.title) > 60 else result.title
                        print(f"      {i}. {title_short}")
                        print(
                            f"         Score: {result.score:.4f} (BM25: {result.bm25_score:.4f if result.bm25_score else 'N/A'})"
                        )
                        print(f"         Category: {result.category}, Source: {result.source}")

                    # Check if risoluzione 63 is in results
                    has_ris_63 = any("63" in r.title and "risoluz" in r.title.lower() for r in results)
                    if has_ris_63:
                        print("   ✅ Risoluzione 63 IS in results!")
                    else:
                        print("   ⚠️  Risoluzione 63 NOT in results")
                else:
                    print("   ❌ No results found")

            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback

                traceback.print_exc()


async def analyze_fts_index():
    """Step 6: Analyze FTS index for numbers."""
    print("=" * 80)
    print("STEP 6: ANALYZE FTS INDEX (NUMBER HANDLING)")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        # Check if numbers are indexed in search_vector
        print("\nChecking if numbers are indexed in search_vector...\n")

        result = await session.execute(
            text("""
                SELECT
                    id,
                    title,
                    to_tsvector('italian', title) as title_vector
                FROM knowledge_items
                WHERE title ILIKE '%risoluzione%' AND title ILIKE '%63%'
                LIMIT 1
            """)
        )
        doc = result.fetchone()

        if doc:
            print(f"Document: {doc.title}")
            print(f"Title Vector: {doc.title_vector}")
            print()

            # Check if '63' appears in vector
            if "63" in str(doc.title_vector):
                print("✅ Number '63' IS present in tsvector")
            else:
                print("❌ Number '63' is NOT present in tsvector")
                print("   This confirms PostgreSQL FTS does not index numbers!")

            # Test if we can search for it
            result = await session.execute(
                text("""
                    SELECT
                        to_tsvector('italian', :text) @@ to_tsquery('italian', :query) as matches
                """),
                {"text": doc.title, "query": "63"},
            )
            matches = result.fetchone()
            print(f"\nDirect tsquery test for '63': {matches.matches if matches else 'N/A'}")

            result = await session.execute(
                text("""
                    SELECT
                        to_tsvector('italian', :text) @@ websearch_to_tsquery('italian', :query) as matches
                """),
                {"text": doc.title, "query": "risoluzione 63"},
            )
            matches = result.fetchone()
            print(f"Websearch tsquery test for 'risoluzione 63': {matches.matches if matches else 'N/A'}")

        else:
            print("❌ Could not find a sample document with 'risoluzione' and '63'")


async def main():
    """Main investigation function."""
    print("\n" + "=" * 80)
    print(" 🐛 INVESTIGATION: Risoluzione 63 Search Bug")
    print("=" * 80 + "\n")

    try:
        # Step 1: Verify document exists
        docs = await verify_document_exists()

        # Step 2: Check knowledge chunks
        await check_knowledge_chunks()

        # Step 3: Test query normalization
        await test_query_normalization()

        # Step 4: Test direct BM25 search
        await test_bm25_search_direct()

        # Step 5: Test KnowledgeSearchService
        await test_knowledge_search_service()

        # Step 6: Analyze FTS index
        await analyze_fts_index()

        print("\n" + "=" * 80)
        print(" 📊 INVESTIGATION COMPLETE")
        print("=" * 80)

        print("\n🔍 KEY FINDINGS:")
        if docs:
            print(f"  ✅ Document exists in database (found {len(docs)} match(es))")
        else:
            print("  ❌ Document NOT found in database")

        print("\n📋 Next: Review the output above to identify:")
        print("  1. Whether FTS indexes numbers (likely NO)")
        print("  2. Whether organization filter is too restrictive")
        print("  3. Whether query simplification removes critical terms")
        print("  4. Which search path works for broader queries")

    except Exception as e:
        print(f"\n❌ Investigation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Investigation interrupted by user")
        sys.exit(1)
