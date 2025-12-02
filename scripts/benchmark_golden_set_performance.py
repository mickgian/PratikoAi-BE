#!/usr/bin/env python3
"""Benchmark script for Golden Set FAQ retrieval performance.

Usage:
    python scripts/benchmark_golden_set_performance.py

Environment variables:
    DATABASE_URL: PostgreSQL connection string
    REDIS_URL: Redis connection string
    OPENAI_API_KEY: OpenAI API key for embeddings
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from app.core.database import get_db_session
from app.services.expert_faq_retrieval_service_optimized import ExpertFAQRetrievalServiceOptimized


async def benchmark_cold_cache():
    """Benchmark cold cache performance (first query)."""
    print("\n" + "=" * 60)
    print("BENCHMARK 1: Cold Cache (First Query)")
    print("=" * 60)

    async with get_db_session() as db:
        service = ExpertFAQRetrievalServiceOptimized(db)

        # Clear cache
        redis_client = await service._get_redis()
        if redis_client:
            await redis_client.flushdb()
            print("✅ Cache cleared")

        query = "Come si calcola l'IVA?"

        start = time.time()
        faqs = await service.find_matching_faqs(query)
        latency_ms = (time.time() - start) * 1000

        print(f"\nQuery: {query}")
        print(f"Results: {len(faqs)}")
        print(f"Latency: {latency_ms:.2f}ms")
        print("Target: <100ms (p99)")

        if latency_ms < 100:
            print("✅ PASS")
        else:
            print("❌ FAIL")

        return latency_ms


async def benchmark_warm_cache():
    """Benchmark warm cache performance (embedding cached)."""
    print("\n" + "=" * 60)
    print("BENCHMARK 2: Warm Cache (Embedding Cached)")
    print("=" * 60)

    async with get_db_session() as db:
        service = ExpertFAQRetrievalServiceOptimized(db)

        query = "Come si calcola l'IVA?"

        # First query to warm up embedding cache
        await service.find_matching_faqs(query)

        # Clear result cache only
        redis_client = await service._get_redis()
        if redis_client:
            result_key = service._generate_result_cache_key(query, 0.85, 10)
            await redis_client.delete(result_key)

        # Second query (embedding cached, search executed)
        start = time.time()
        faqs = await service.find_matching_faqs(query)
        latency_ms = (time.time() - start) * 1000

        print(f"\nQuery: {query}")
        print(f"Results: {len(faqs)}")
        print(f"Latency: {latency_ms:.2f}ms")
        print("Target: <50ms (p95)")

        if latency_ms < 50:
            print("✅ PASS")
        else:
            print("❌ FAIL")

        return latency_ms


async def benchmark_hot_cache():
    """Benchmark hot cache performance (result cached)."""
    print("\n" + "=" * 60)
    print("BENCHMARK 3: Hot Cache (Result Cached)")
    print("=" * 60)

    async with get_db_session() as db:
        service = ExpertFAQRetrievalServiceOptimized(db)

        query = "Come si calcola l'IVA?"

        # Warm up all caches
        await service.find_matching_faqs(query)

        # Third query (result cached)
        start = time.time()
        faqs = await service.find_matching_faqs(query)
        latency_ms = (time.time() - start) * 1000

        print(f"\nQuery: {query}")
        print(f"Results: {len(faqs)}")
        print(f"Latency: {latency_ms:.2f}ms")
        print("Target: <20ms (p50)")

        if latency_ms < 20:
            print("✅ PASS")
        else:
            print("❌ FAIL")

        return latency_ms


async def benchmark_percentiles():
    """Benchmark latency percentiles over 100 queries."""
    print("\n" + "=" * 60)
    print("BENCHMARK 4: Latency Percentiles (100 Queries)")
    print("=" * 60)

    async with get_db_session() as db:
        service = ExpertFAQRetrievalServiceOptimized(db)

        # Warm up
        await service.find_matching_faqs("warm up")

        # Run 100 queries (50% duplicates)
        latencies = []

        for i in range(100):
            query = f"query {i % 50}"
            start = time.time()
            await service.find_matching_faqs(query, min_similarity=0.7)
            latency_ms = (time.time() - start) * 1000
            latencies.append(latency_ms)

        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)

        print("\nPercentiles:")
        print(f"  p50: {p50:.2f}ms (target: <20ms)")
        print(f"  p95: {p95:.2f}ms (target: <50ms)")
        print(f"  p99: {p99:.2f}ms (target: <100ms)")

        passed = p50 < 20 and p95 < 50 and p99 < 100

        if passed:
            print("\n✅ ALL TARGETS MET")
        else:
            print("\n❌ SOME TARGETS MISSED")

        return p50, p95, p99


async def benchmark_concurrent():
    """Benchmark concurrent query performance."""
    print("\n" + "=" * 60)
    print("BENCHMARK 5: Concurrent Queries (20 concurrent)")
    print("=" * 60)

    async with get_db_session() as db:
        service = ExpertFAQRetrievalServiceOptimized(db)

        # Warm up
        await service.find_matching_faqs("warm up")

        async def query_task(i: int):
            start = time.time()
            await service.find_matching_faqs(f"concurrent query {i % 10}")
            return (time.time() - start) * 1000

        # Execute 20 concurrent queries
        start = time.time()
        latencies = await asyncio.gather(*[query_task(i) for i in range(20)])
        total_time_ms = (time.time() - start) * 1000

        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)

        print("\nConcurrent queries: 20")
        print(f"Total time: {total_time_ms:.2f}ms")
        print(f"Avg latency: {avg_latency:.2f}ms")
        print(f"p95 latency: {p95_latency:.2f}ms (target: <100ms)")

        if p95_latency < 100:
            print("✅ PASS")
        else:
            print("❌ FAIL")

        return avg_latency, p95_latency


async def main():
    """Run all benchmarks."""
    print("\n" + "=" * 60)
    print("GOLDEN SET PERFORMANCE BENCHMARK")
    print("=" * 60)

    try:
        # Run benchmarks
        cold_latency = await benchmark_cold_cache()
        warm_latency = await benchmark_warm_cache()
        hot_latency = await benchmark_hot_cache()
        p50, p95, p99 = await benchmark_percentiles()
        avg_concurrent, p95_concurrent = await benchmark_concurrent()

        # Summary
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)

        print("\nLatency Targets:")
        print(f"  Cold cache (p99): {cold_latency:.2f}ms / 100ms {'✅' if cold_latency < 100 else '❌'}")
        print(f"  Warm cache (p95): {warm_latency:.2f}ms / 50ms {'✅' if warm_latency < 50 else '❌'}")
        print(f"  Hot cache (p50): {hot_latency:.2f}ms / 20ms {'✅' if hot_latency < 20 else '❌'}")

        print("\nPercentiles (100 queries):")
        print(f"  p50: {p50:.2f}ms / 20ms {'✅' if p50 < 20 else '❌'}")
        print(f"  p95: {p95:.2f}ms / 50ms {'✅' if p95 < 50 else '❌'}")
        print(f"  p99: {p99:.2f}ms / 100ms {'✅' if p99 < 100 else '❌'}")

        print("\nConcurrent (20 queries):")
        print(f"  Avg: {avg_concurrent:.2f}ms")
        print(f"  p95: {p95_concurrent:.2f}ms / 100ms {'✅' if p95_concurrent < 100 else '❌'}")

        # Overall pass/fail
        all_passed = (
            cold_latency < 100
            and warm_latency < 50
            and hot_latency < 20
            and p50 < 20
            and p95 < 50
            and p99 < 100
            and p95_concurrent < 100
        )

        print("\n" + "=" * 60)
        if all_passed:
            print("✅ ALL BENCHMARKS PASSED")
        else:
            print("❌ SOME BENCHMARKS FAILED")
        print("=" * 60 + "\n")

        return 0 if all_passed else 1

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
