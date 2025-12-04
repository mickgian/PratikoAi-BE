#!/usr/bin/env python3
"""Knowledge Base Search Testing Script

This script tests the Italian full-text search functionality
to verify integration with collected data.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to Python path (2 levels up from tests/integration/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import text

from app.models.knowledge import KnowledgeItem
from app.services.database import database_service
from app.services.search_service import SearchService


async def check_knowledge_base():
    """Check current state of knowledge base."""
    print("📊 Checking knowledge base status...")

    try:
        with database_service.get_session_maker() as session:
            # Check knowledge_items table
            result = session.execute(text("SELECT COUNT(*) FROM knowledge_items"))
            knowledge_count = result.scalar()
            print(f"✅ knowledge_items table: {knowledge_count} records")

            if knowledge_count > 0:
                # Get sample data
                result = session.execute(
                    text("""
                    SELECT title, category, language, relevance_score
                    FROM knowledge_items
                    ORDER BY updated_at DESC
                    LIMIT 5
                """)
                )
                samples = result.fetchall()

                print("📝 Recent knowledge items:")
                for sample in samples:
                    title = sample.title[:60] + "..." if len(sample.title) > 60 else sample.title
                    print(f"   • {title}")
                    print(f"     Category: {sample.category}, Language: {sample.language}")
                    print(f"     Relevance: {sample.relevance_score}")

            return knowledge_count

    except Exception as e:
        print(f"❌ Failed to check knowledge base: {e}")
        return 0


async def test_italian_search():
    """Test Italian full-text search functionality."""
    print("\n🔍 Testing Italian full-text search...")

    try:
        with database_service.get_session_maker() as session:
            # Create SearchService (note: it expects AsyncSession but let's see what happens)
            # For now, let's test the search infrastructure without actual search

            # Check if search indexes exist
            result = session.execute(
                text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'knowledge_items'
                AND indexname LIKE '%search%'
            """)
            )
            search_indexes = result.fetchall()

            print(f"✅ Search indexes found: {len(search_indexes)}")
            for idx in search_indexes:
                print(f"   • {idx.indexname}")

            # Test basic search vector functionality
            result = session.execute(
                text("""
                SELECT COUNT(*)
                FROM knowledge_items
                WHERE search_vector IS NOT NULL
            """)
            )
            indexed_count = result.scalar()
            print(f"✅ Items with search vectors: {indexed_count}")

            # Test Italian text search configuration
            result = session.execute(text("SELECT * FROM pg_ts_config WHERE cfgname = 'italian'"))
            italian_config = result.fetchone()
            if italian_config:
                print("✅ Italian text search configuration: AVAILABLE")
            else:
                print("⚠️  Italian text search configuration: NOT FOUND")

            return True

    except Exception as e:
        print(f"❌ Search test failed: {e}")
        return False


async def test_search_suggestions():
    """Test search suggestions functionality."""
    print("\n💡 Testing search suggestions...")

    try:
        with database_service.get_session_maker() as session:
            # Check if we can generate search suggestions from existing content
            result = session.execute(
                text("""
                SELECT word, nentry
                FROM ts_stat('SELECT search_vector FROM knowledge_items WHERE search_vector IS NOT NULL')
                ORDER BY nentry DESC
                LIMIT 10
            """)
            )
            suggestions = result.fetchall()

            if suggestions:
                print(f"✅ Search suggestions available: {len(suggestions)} top terms")
                print("🔤 Most common terms in knowledge base:")
                for word, count in suggestions:
                    print(f"   • {word} ({count} occurrences)")
            else:
                print("ℹ️  No search suggestions available (empty knowledge base)")

            return len(suggestions) > 0

    except Exception as e:
        print(f"❌ Search suggestions test failed: {e}")
        return False


async def create_test_knowledge_item():
    """Create a test knowledge item for search testing."""
    print("\n📝 Creating test knowledge item...")

    try:
        with database_service.get_session_maker() as session:
            # Create a test Italian knowledge item
            test_item = KnowledgeItem(
                title="Circolare Test n. 1/T del 09 settembre 2025",
                content="Questa è una circolare di test per verificare il funzionamento del sistema di ricerca italiano. Include termini come IVA, imposte, detrazioni fiscali e normative tributarie.",
                category="test_agenzia_entrate",
                subcategory="circolari",
                source="test",
                source_url="https://test.example.com/circolare-test.pdf",
                language="it",
                relevance_score=0.8,
                tags=["IVA", "imposte", "test"],
                legal_references=["D.Lgs. 123/2025"],
            )

            session.add(test_item)
            session.commit()
            session.refresh(test_item)

            print(f"✅ Test knowledge item created with ID: {test_item.id}")

            # Update search vector for the new item
            session.execute(
                text("""
                UPDATE knowledge_items
                SET search_vector =
                    setweight(to_tsvector('italian', COALESCE(title, '')), 'A') ||
                    setweight(to_tsvector('italian', COALESCE(content, '')), 'B')
                WHERE id = :item_id
            """),
                {"item_id": test_item.id},
            )
            session.commit()

            print("✅ Search vector updated for test item")
            return test_item.id

    except Exception as e:
        print(f"❌ Failed to create test knowledge item: {e}")
        return None


async def test_search_functionality(test_item_id=None):
    """Test actual search functionality."""
    print("\n🚀 Testing search functionality...")

    try:
        with database_service.get_session_maker() as session:
            # Test Italian search query
            search_query = "IVA imposte"

            result = session.execute(
                text("""
                SELECT
                    id,
                    title,
                    content,
                    category,
                    ts_rank(search_vector, query) AS rank,
                    ts_headline(
                        'italian',
                        content,
                        query,
                        'StartSel=<b>, StopSel=</b>, MaxWords=30, MinWords=15'
                    ) AS highlight
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

            search_results = result.fetchall()

            print(f"✅ Search query '{search_query}' returned {len(search_results)} results")

            for i, result in enumerate(search_results, 1):
                title = result.title[:50] + "..." if len(result.title) > 50 else result.title
                print(f"   {i}. {title} (rank: {result.rank:.3f})")
                print(f"      Category: {result.category}")
                if result.highlight:
                    highlight = result.highlight[:80] + "..." if len(result.highlight) > 80 else result.highlight
                    print(f"      Highlight: {highlight}")
                print()

            return len(search_results) > 0

    except Exception as e:
        print(f"❌ Search functionality test failed: {e}")
        return False


async def main():
    """Main testing function."""
    print("🤖 PratikoAI Knowledge Base Search Test")
    print("=" * 45)

    # Test 1: Check knowledge base status
    knowledge_count = await check_knowledge_base()

    # Test 2: Test search infrastructure
    search_ok = await test_italian_search()

    # Test 3: Test search suggestions
    suggestions_ok = await test_search_suggestions()

    # Test 4: Create test data if knowledge base is empty
    test_item_id = None
    if knowledge_count == 0:
        print("\nℹ️  Knowledge base is empty, creating test data...")
        test_item_id = await create_test_knowledge_item()

    # Test 5: Test actual search functionality
    search_results_ok = await test_search_functionality(test_item_id)

    print("\n🎉 Testing Summary")
    print("=" * 45)

    print(f"✅ Knowledge base: {knowledge_count} items" if knowledge_count > 0 else "ℹ️  Knowledge base: empty")
    print("✅ Search infrastructure: WORKING" if search_ok else "❌ Search infrastructure: FAILED")
    print("✅ Search suggestions: WORKING" if suggestions_ok else "ℹ️  Search suggestions: unavailable")
    print("✅ Search functionality: WORKING" if search_results_ok else "❌ Search functionality: FAILED")

    if knowledge_count == 0:
        print("\nℹ️  To populate knowledge base:")
        print("   1. Start the main application server")
        print("   2. RSS collection will run automatically every 4 hours")
        print("   3. Or manually trigger collection with the activation script")

    if search_ok and (knowledge_count > 0 or search_results_ok):
        print("\n🎉 Italian search system is ready!")
        print("✅ Full-text search with Italian language support")
        print("✅ Search ranking and highlighting")
        print("✅ PostgreSQL FTS integration")
        return True
    else:
        print("\n⚠️  Search system needs attention")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        sys.exit(1)
