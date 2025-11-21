#!/usr/bin/env python3
"""End-to-end test: Trace exactly what happens when searching for Risoluzione 63."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.models.database import AsyncSessionLocal
from app.services.knowledge_search_service import KnowledgeSearchService


async def test_search_pipeline():
    """Test the complete search pipeline for Risoluzione 63."""
    print("\n" + "=" * 80)
    print("END-TO-END TEST: Search for Risoluzione 63")
    print("=" * 80 + "\n")

    test_cases = [
        {
            "name": "User Query (failing case)",
            "query": "Di cosa parla la risoluzione 63 dell'agenzia delle entrate?",
            "canonical_facts": [],
        },
        {
            "name": "User Query + LLM facts",
            "query": "Di cosa parla la risoluzione 63 dell'agenzia delle entrate?",
            "canonical_facts": ["Risoluzione n. 63", "Agenzia delle Entrate"],
        },
        {
            "name": "Simplified query",
            "query": "risoluzione 63",
            "canonical_facts": [],
        },
        {
            "name": "Simplified query + facts",
            "query": "risoluzione 63",
            "canonical_facts": ["Risoluzione n. 63"],
        },
    ]

    async with AsyncSessionLocal() as session:
        search_service = KnowledgeSearchService(db_session=session)

        for test_case in test_cases:
            print(f"\nTest: {test_case['name']}")
            print("-" * 80)
            print(f"Query: '{test_case['query']}'")
            print(f"Canonical Facts: {test_case['canonical_facts']}")

            query_data = {
                "query": test_case["query"],
                "canonical_facts": test_case["canonical_facts"],
                "user_id": "test_user",
                "session_id": "test_session",
                "trace_id": f"test_{test_case['name'].replace(' ', '_')}",
                "search_mode": "bm25_only",  # Simplified: BM25 only
                "filters": {},
                "max_results": 5,
            }

            try:
                results = await search_service.retrieve_topk(query_data)

                if results:
                    print(f"\n✅ Found {len(results)} result(s):")
                    for i, result in enumerate(results, 1):
                        title_short = result.title[:70] + "..." if len(result.title) > 70 else result.title
                        is_63 = " (RISOLUZIONE 63!)" if "63" in result.title and "risoluz" in result.title.lower() else ""
                        print(f"   {i}. {title_short}{is_63}")
                        print(f"      Score: {result.score:.4f}, Source: {result.source}")
                else:
                    print("\n❌ NO RESULTS FOUND")
                    print("   This reproduces the bug!")

            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()

            print()


async def main():
    """Run end-to-end investigation."""
    try:
        await test_search_pipeline()

        print("\n" + "=" * 80)
        print("NEXT STEPS FOR DEBUGGING")
        print("=" * 80)
        print("""
Check the logs above for:

1. Whether 'search_path_title_based' log appears
   - This indicates title filter is being used
   - If missing, the title_pattern is not being set

2. Whether 'bm25_document_number_query_simplification' log appears
   - This indicates the document number was detected
   - Shows what simplified query was used

3. Whether 'organization_detected_from_canonical_facts' log appears
   - This shows if org filter is applied

4. Check for 'bm25_query_simplification' log
   - Shows if query was simplified for aggregation

To see these logs in real-time:
    tail -f logs/application.log | grep -E "search_path|bm25_|organization_detected"
        """)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
