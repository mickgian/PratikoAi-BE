"""Direct test of search service with year filtering."""

import asyncio

from app.models.database import AsyncSessionLocal
from app.services.search_service import SearchService


async def test_search():
    """Test search with year parameter."""
    async with AsyncSessionLocal() as session:
        search = SearchService(session)

        # Test 1: Search with year 2025 and month October
        print("\n=== Test 1: Search for documents in October 2025 ===")
        results = await search.search(query="articolo ottobre", limit=10, publication_year=2025)

        print(f"Found {len(results)} results:")
        for r in results:
            print(f"  - {r.title[:80]}...")
            print(f"    Publication: {r.publication_date}, Updated: {r.updated_at}")
            print(f"    Rank: {r.rank_score:.4f}, Relevance: {r.relevance_score:.4f}")

        # Test 2: Search without year filter
        print("\n=== Test 2: Search for 'articolo ottobre' (no year filter) ===")
        results_no_year = await search.search(query="articolo ottobre", limit=10, publication_year=None)

        print(f"Found {len(results_no_year)} results (should be >= Test 1)")


if __name__ == "__main__":
    asyncio.run(test_search())
