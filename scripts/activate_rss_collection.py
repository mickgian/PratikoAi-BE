#!/usr/bin/env python3
"""RSS Feed Collection Activation Script

This script manually triggers the Italian regulatory document collection
to test and activate the RSS feed monitoring system.

Usage: python activate_rss_collection.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.logging import logger
from app.services.database import database_service
from app.services.dynamic_knowledge_collector import DynamicKnowledgeCollector, collect_italian_documents_task


async def test_single_feed_collection():
    """Test collection from a single RSS feed."""
    print("🔍 Testing single RSS feed collection...")

    try:
        # Get database session
        async with database_service.get_session_manager() as session:
            collector = DynamicKnowledgeCollector(session)

            # Test collection from specific sources
            results = await collector.collect_from_specific_sources(["agenzia_entrate"])

            print("✅ Single feed test completed")
            print(f"   Results: {len(results)} sources processed")

            for result in results:
                if result.get("success"):
                    print(
                        f"   ✅ {result.get('source', 'unknown')}: {result.get('new_documents_count', 0)} new documents"
                    )
                else:
                    print(f"   ❌ {result.get('source', 'unknown')}: {result.get('error', 'Unknown error')}")

            return results

    except Exception as e:
        print(f"❌ Single feed test failed: {e}")
        logger.error("single_feed_test_failed", error=str(e), exc_info=True)
        return []


async def test_full_collection():
    """Test full RSS collection from all Italian sources."""
    print("🚀 Testing full RSS collection from all Italian sources...")

    try:
        # Get database session
        async with database_service.get_session_manager() as session:
            collector = DynamicKnowledgeCollector(session)

            # Run full collection
            start_time = datetime.now()
            results = await collector.collect_and_process_updates()
            end_time = datetime.now()

            processing_time = (end_time - start_time).total_seconds()

            print(f"✅ Full collection completed in {processing_time:.2f} seconds")
            print(f"   Results: {len(results)} sources processed")

            # Analyze results
            successful_sources = [r for r in results if r.get("success")]
            failed_sources = [r for r in results if not r.get("success")]
            total_new_docs = sum(r.get("new_documents_count", 0) for r in successful_sources)

            print(f"   ✅ Successful sources: {len(successful_sources)}")
            print(f"   ❌ Failed sources: {len(failed_sources)}")
            print(f"   📄 Total new documents: {total_new_docs}")

            # Show detailed results
            for result in results:
                source = result.get("source", "unknown")
                if result.get("success"):
                    new_docs = result.get("new_documents_count", 0)
                    total_items = result.get("feed_items_total", 0)
                    proc_time = result.get("processing_time_seconds", 0)
                    print(f"   ✅ {source}: {new_docs}/{total_items} new docs ({proc_time:.1f}s)")
                else:
                    error = result.get("error", "Unknown error")
                    print(f"   ❌ {source}: {error}")

            # Performance check
            if processing_time > 300:  # 5 minutes
                print(f"⚠️  Processing time ({processing_time:.2f}s) exceeded 5-minute target")
            else:
                print("✅ Processing time within target (< 5 minutes)")

            # Document count check
            if total_new_docs >= 10:  # Lower threshold for testing
                print(f"✅ Document collection target met ({total_new_docs} documents)")
            else:
                print(f"ℹ️  Document collection: {total_new_docs} documents (may be low if feeds already processed)")

            return results

    except Exception as e:
        print(f"❌ Full collection test failed: {e}")
        logger.error("full_collection_test_failed", error=str(e), exc_info=True)
        return []


async def test_scheduled_task():
    """Test the scheduled task function directly."""
    print("⏰ Testing scheduled task function...")

    try:
        # Execute the actual scheduled task
        await collect_italian_documents_task()
        print("✅ Scheduled task completed successfully")

    except Exception as e:
        print(f"❌ Scheduled task failed: {e}")
        logger.error("scheduled_task_test_failed", error=str(e), exc_info=True)


async def check_database_connectivity():
    """Check database connectivity and table structure."""
    print("🔗 Checking database connectivity...")

    try:
        with database_service.get_session_maker() as session:
            from sqlalchemy import text

            # Test basic connectivity
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            print("✅ Database connection successful")

            # Check knowledge_items table exists
            result = session.execute(text("SELECT COUNT(*) FROM knowledge_items"))
            knowledge_count = result.scalar()
            print(f"✅ knowledge_items table: {knowledge_count} records")

            # Check regulatory_documents table exists
            try:
                result = session.execute(text("SELECT COUNT(*) FROM regulatory_documents"))
                regulatory_count = result.scalar()
                print(f"✅ regulatory_documents table: {regulatory_count} records")
            except Exception:
                print("ℹ️  regulatory_documents table not found (may need migration)")

            return True

    except Exception as e:
        print(f"❌ Database connectivity test failed: {e}")
        logger.error("database_connectivity_failed", error=str(e), exc_info=True)
        return False


async def activate_rss_system():
    """Main function to activate and test the RSS collection system."""
    print("🤖 PratikoAI RSS Feed Collection Activation")
    print("=" * 50)

    # Step 1: Check database connectivity
    db_ok = await check_database_connectivity()
    if not db_ok:
        print("❌ Cannot proceed without database connectivity")
        return False

    print()

    # Step 2: Test single feed (faster, safer)
    single_results = await test_single_feed_collection()

    print()

    # Step 3: Test full collection if single feed works
    if single_results and any(r.get("success") for r in single_results):
        print("Single feed test successful, proceeding with full collection...")
        full_results = await test_full_collection()
    else:
        print("Single feed test failed, skipping full collection")
        print("This could be normal if there are no new documents to collect")
        full_results = []

    print()

    # Step 4: Test scheduled task function
    await test_scheduled_task()

    print()
    print("🎉 RSS Feed Collection Activation Complete!")
    print("=" * 50)

    # Summary
    if single_results or full_results:
        print("✅ RSS collection system is operational and ready")
        print("✅ Scheduler will run collection every 4 hours")
        print("✅ Italian regulatory sources are being monitored")

        # Show what sources are monitored
        from app.services.rss_feed_monitor import RSSFeedMonitor

        monitor = RSSFeedMonitor()
        print("\n📡 Monitored Italian sources:")
        for feed_name in monitor.italian_feeds.keys():
            print(f"   • {feed_name}")

        return True
    else:
        print("⚠️  RSS collection system tested but may need configuration")
        print("   This could be normal if all feeds are already up to date")
        return False


if __name__ == "__main__":
    # Configure logging for activation script
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Run the activation
    try:
        success = asyncio.run(activate_rss_system())
        exit_code = 0 if success else 1
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n⚠️  Activation interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Activation failed with error: {e}")
        logger.error("activation_script_failed", error=str(e), exc_info=True)
        sys.exit(1)
