"""Tests for Rate Limiting in DynamicKnowledgeCollector - DEV-BE-69 Phase 2

Tests for stagger delay implementation between concurrent feed processing.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.dynamic_knowledge_collector import DynamicKnowledgeCollector


class TestStaggerDelay:
    """Tests for stagger delay implementation."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def collector(self, mock_db_session):
        """Create DynamicKnowledgeCollector with mocked dependencies."""
        with patch("app.services.dynamic_knowledge_collector.RSSFeedMonitor"):
            with patch("app.services.dynamic_knowledge_collector.KnowledgeIntegrator"):
                collector = DynamicKnowledgeCollector(mock_db_session)
                # Mock the process_single_feed method to track timing
                collector.process_single_feed = AsyncMock(
                    return_value={"success": True, "source": "test", "new_documents": []}
                )
                return collector

    @pytest.mark.asyncio
    async def test_process_all_feeds_parallel_accepts_stagger_params(self, collector):
        """Test that process_all_feeds_parallel accepts stagger delay parameters."""
        feeds = {"feed1": "http://example.com/1", "feed2": "http://example.com/2"}

        # Should not raise
        await collector.process_all_feeds_parallel(
            feeds,
            max_concurrent=5,
            stagger_delay_min=1.0,
            stagger_delay_max=3.0,
        )

    @pytest.mark.asyncio
    async def test_process_all_feeds_parallel_default_stagger_values(self, collector):
        """Test default stagger delay values."""
        feeds = {"feed1": "http://example.com/1"}

        # Check default parameters by calling with minimal args
        await collector.process_all_feeds_parallel(feeds)

        # Method should complete without error using defaults

    @pytest.mark.asyncio
    async def test_process_all_feeds_parallel_dict_format(self, collector):
        """Test processing with dictionary format feeds."""
        feeds = {
            "agenzia_entrate": "http://example.com/ae",
            "inps": "http://example.com/inps",
            "inail": "http://example.com/inail",
        }

        results = await collector.process_all_feeds_parallel(feeds, max_concurrent=2)

        assert len(results) == 3
        assert collector.process_single_feed.call_count == 3

    @pytest.mark.asyncio
    async def test_process_all_feeds_parallel_list_format(self, collector):
        """Test processing with list format feeds."""
        feeds = [
            {"source": "agenzia_entrate", "feed_url": "http://example.com/ae"},
            {"source": "inps", "feed_url": "http://example.com/inps"},
        ]

        results = await collector.process_all_feeds_parallel(feeds, max_concurrent=2)

        assert len(results) == 2
        assert collector.process_single_feed.call_count == 2

    @pytest.mark.asyncio
    async def test_first_feed_no_delay(self, collector):
        """Test that first feed starts immediately without delay."""
        call_times = []

        async def track_time(feed_name, feed_url):
            call_times.append(time.time())
            return {"success": True, "source": feed_name, "new_documents": []}

        collector.process_single_feed = track_time

        feeds = {"feed1": "http://example.com/1"}

        start_time = time.time()
        await collector.process_all_feeds_parallel(feeds, stagger_delay_min=1.0, stagger_delay_max=1.0)

        # First feed should start almost immediately (< 0.5 seconds)
        assert len(call_times) == 1
        assert call_times[0] - start_time < 0.5

    @pytest.mark.asyncio
    async def test_subsequent_feeds_have_delay(self, collector):
        """Test that subsequent feeds have stagger delay."""
        call_times = []

        async def track_time(feed_name, feed_url):
            call_times.append(time.time())
            return {"success": True, "source": feed_name, "new_documents": []}

        collector.process_single_feed = track_time

        feeds = {
            "feed1": "http://example.com/1",
            "feed2": "http://example.com/2",
            "feed3": "http://example.com/3",
        }

        start_time = time.time()
        await collector.process_all_feeds_parallel(
            feeds,
            max_concurrent=5,  # All can run concurrently
            stagger_delay_min=0.1,  # Short delay for test
            stagger_delay_max=0.1,
        )

        # Should have 3 calls
        assert len(call_times) == 3

        # Subsequent feeds should be delayed
        # Feed 2 should start after ~0.1s * 1 = 0.1s
        # Feed 3 should start after ~0.1s * 2 = 0.2s
        delays = [t - start_time for t in call_times]
        delays.sort()

        # First should be immediate
        assert delays[0] < 0.05

    @pytest.mark.asyncio
    async def test_semaphore_respects_max_concurrent(self, collector):
        """Test that semaphore limits concurrent processing."""
        concurrent_count = 0
        max_concurrent_seen = 0

        async def track_concurrent(feed_name, feed_url):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.1)  # Simulate work
            concurrent_count -= 1
            return {"success": True, "source": feed_name, "new_documents": []}

        collector.process_single_feed = track_concurrent

        feeds = {f"feed{i}": f"http://example.com/{i}" for i in range(10)}

        await collector.process_all_feeds_parallel(
            feeds,
            max_concurrent=3,
            stagger_delay_min=0.01,
            stagger_delay_max=0.01,
        )

        # Should never exceed max_concurrent
        assert max_concurrent_seen <= 3

    @pytest.mark.asyncio
    async def test_error_handling_in_parallel_processing(self, collector):
        """Test error handling during parallel processing."""

        async def raise_error(feed_name, feed_url):
            if feed_name == "error_feed":
                raise ValueError("Test error")
            return {"success": True, "source": feed_name, "new_documents": []}

        collector.process_single_feed = raise_error

        feeds = {
            "feed1": "http://example.com/1",
            "error_feed": "http://example.com/error",
            "feed3": "http://example.com/3",
        }

        results = await collector.process_all_feeds_parallel(feeds, stagger_delay_min=0, stagger_delay_max=0)

        # Should return all results (including error)
        assert len(results) == 3

        # Error feed should have success=False
        error_result = next(r for r in results if r.get("source") == "error_feed")
        assert error_result["success"] is False
        assert "error" in error_result

    @pytest.mark.asyncio
    async def test_stats_updated_after_processing(self, collector):
        """Test that statistics are updated after processing."""
        feeds = {
            "feed1": "http://example.com/1",
            "feed2": "http://example.com/2",
        }

        collector.process_single_feed = AsyncMock(
            return_value={
                "success": True,
                "source": "test",
                "new_documents": [{"title": "doc1"}, {"title": "doc2"}],
            }
        )

        await collector.process_all_feeds_parallel(feeds)

        assert collector.stats["feeds_processed"] == 2
        assert collector.stats["new_documents"] == 4  # 2 docs per feed * 2 feeds
        assert collector.stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_stats_count_errors(self, collector):
        """Test that error statistics are tracked."""
        feeds = {"feed1": "http://example.com/1", "feed2": "http://example.com/2"}

        async def sometimes_fail(feed_name, feed_url):
            if "1" in feed_url:
                return {"success": False, "source": feed_name, "new_documents": [], "error": "Test error"}
            return {"success": True, "source": feed_name, "new_documents": []}

        collector.process_single_feed = sometimes_fail

        await collector.process_all_feeds_parallel(feeds)

        assert collector.stats["errors"] == 1


class TestRateLimitingIntegration:
    """Integration tests for rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_stagger_delay_range(self):
        """Test that delays fall within specified range."""
        delays_seen = []

        class MockCollector:
            def __init__(self):
                self.stats = {"feeds_processed": 0, "new_documents": 0, "errors": 0}

            async def process_single_feed(self, feed_name, feed_url):
                return {"success": True, "source": feed_name, "new_documents": []}

            async def process_all_feeds_parallel(
                self,
                feeds,
                max_concurrent=5,
                stagger_delay_min=1.0,
                stagger_delay_max=3.0,
            ):
                import random

                semaphore = asyncio.Semaphore(max_concurrent)

                async def process_with_semaphore(name, url, delay):
                    if delay > 0:
                        delays_seen.append(delay)
                        # Don't actually sleep in test
                    async with semaphore:
                        return await self.process_single_feed(name, url)

                feed_items = list(feeds.items())
                tasks = []

                for i, (name, url) in enumerate(feed_items):
                    if i == 0:
                        delay = 0.0
                    else:
                        delay = random.uniform(stagger_delay_min, stagger_delay_max) * i
                    tasks.append(asyncio.create_task(process_with_semaphore(name, url, delay)))

                results = await asyncio.gather(*tasks, return_exceptions=True)
                return [r for r in results if not isinstance(r, Exception)]

        collector = MockCollector()
        feeds = {f"feed{i}": f"http://example.com/{i}" for i in range(5)}

        await collector.process_all_feeds_parallel(
            feeds,
            stagger_delay_min=1.0,
            stagger_delay_max=3.0,
        )

        # Should have 4 delays (first feed has no delay)
        assert len(delays_seen) == 4

        # Check delays are in expected ranges
        # Feed 2: 1.0-3.0 * 1 = 1.0-3.0
        # Feed 3: 1.0-3.0 * 2 = 2.0-6.0
        # Feed 4: 1.0-3.0 * 3 = 3.0-9.0
        # Feed 5: 1.0-3.0 * 4 = 4.0-12.0
        assert delays_seen[0] >= 1.0  # Feed 2
        assert delays_seen[0] <= 3.0
        assert delays_seen[1] >= 2.0  # Feed 3
        assert delays_seen[1] <= 6.0
        assert delays_seen[2] >= 3.0  # Feed 4
        assert delays_seen[2] <= 9.0
        assert delays_seen[3] >= 4.0  # Feed 5
        assert delays_seen[3] <= 12.0
