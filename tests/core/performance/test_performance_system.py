"""Comprehensive tests for the performance optimization system."""

import pytest
import asyncio
import time
import gzip
import brotli
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.core.performance import (
    database_optimizer,
    response_compressor,
    performance_monitor,
    cdn_manager
)
from app.core.performance.response_compressor import CompressionType, CompressionStats
from app.core.performance.performance_monitor import PerformanceAlert, RequestMetrics
from app.core.performance.cdn_integration import CDNProvider, CacheControl


class TestDatabaseOptimizer:
    """Test database optimization functionality."""
    
    @pytest.mark.asyncio
    async def test_monitor_query_basic(self):
        """Test basic query monitoring."""
        query = "SELECT * FROM users WHERE id = 1"
        execution_time = 0.5
        rows_affected = 1
        
        query_hash = await database_optimizer.monitor_query(
            query=query,
            execution_time=execution_time,
            rows_affected=rows_affected
        )
        
        assert query_hash
        assert len(query_hash) == 32  # MD5 hash length
        assert query_hash in database_optimizer.query_stats
        
        stats = database_optimizer.query_stats[query_hash]
        assert stats.execution_count == 1
        assert stats.total_time == execution_time
        assert stats.avg_time == execution_time
        assert stats.rows_affected == rows_affected
    
    @pytest.mark.asyncio
    async def test_monitor_query_aggregation(self):
        """Test query statistics aggregation."""
        query = "SELECT name FROM products WHERE price > 100"
        
        # Execute same query multiple times
        for i in range(5):
            execution_time = 0.1 + (i * 0.05)  # Varying execution times
            await database_optimizer.monitor_query(
                query=query,
                execution_time=execution_time,
                rows_affected=10 + i
            )
        
        # Find the query stats
        query_stats = list(database_optimizer.query_stats.values())
        aggregated_stats = next(
            (stats for stats in query_stats if "PRODUCTS" in stats.query_text),
            None
        )
        
        assert aggregated_stats is not None
        assert aggregated_stats.execution_count == 5
        assert aggregated_stats.total_time == sum(0.1 + (i * 0.05) for i in range(5))
        assert aggregated_stats.avg_time == aggregated_stats.total_time / 5
        assert aggregated_stats.min_time == 0.1
        assert aggregated_stats.max_time == 0.3
    
    def test_normalize_query(self):
        """Test query normalization for consistent tracking."""
        query1 = "SELECT * FROM users WHERE id = 123 AND name = 'John'"
        query2 = "SELECT * FROM users WHERE id = 456 AND name = 'Jane'"
        
        normalized1 = database_optimizer._normalize_query(query1)
        normalized2 = database_optimizer._normalize_query(query2)
        
        # Both queries should normalize to the same pattern
        assert normalized1 == normalized2
        assert "?" in normalized1  # Parameters should be replaced
        assert "123" not in normalized1
        assert "John" not in normalized1
    
    @pytest.mark.asyncio
    async def test_analyze_slow_queries(self):
        """Test slow query analysis."""
        # Add some fast and slow queries
        fast_query = "SELECT id FROM users LIMIT 10"
        slow_query = "SELECT * FROM orders o JOIN users u ON o.user_id = u.id ORDER BY o.created_at"
        
        await database_optimizer.monitor_query(fast_query, execution_time=0.1)
        await database_optimizer.monitor_query(slow_query, execution_time=2.5)
        await database_optimizer.monitor_query(slow_query, execution_time=3.0)
        
        slow_queries = await database_optimizer.analyze_slow_queries(limit=5)
        
        assert len(slow_queries) >= 1
        slowest_query = slow_queries[0]
        assert slowest_query.avg_time > database_optimizer.slow_query_threshold
        assert "ORDER BY" in slowest_query.query_text.upper()
    
    @pytest.mark.asyncio
    async def test_generate_index_recommendations(self):
        """Test index recommendation generation."""
        # Simulate queries that would benefit from indexes
        queries = [
            ("SELECT * FROM users WHERE email = 'test@example.com'", 2.1),
            ("SELECT * FROM orders WHERE user_id = 123 ORDER BY created_at", 1.8),
            ("SELECT COUNT(*) FROM products WHERE category_id = 5", 1.5)
        ]
        
        for query, execution_time in queries:
            for _ in range(15):  # Execute multiple times to meet threshold
                await database_optimizer.monitor_query(query, execution_time=execution_time)
        
        recommendations = await database_optimizer.generate_index_recommendations()
        
        assert len(recommendations) > 0
        
        # Check recommendation structure
        for rec in recommendations:
            assert rec.table_name
            assert rec.columns
            assert rec.index_type == "btree"
            assert rec.estimated_benefit > 0
    
    @pytest.mark.asyncio
    async def test_optimize_query_execution(self):
        """Test query execution optimization."""
        # Test query without LIMIT
        query = "SELECT * FROM users ORDER BY created_at DESC"
        
        optimized_query, hints = await database_optimizer.optimize_query_execution(query)
        
        assert "LIMIT" in optimized_query
        assert hints["optimization_applied"] is True
        assert "use_cache" in hints
    
    @pytest.mark.asyncio
    async def test_connection_pool_optimization(self):
        """Test connection pool optimization."""
        # Mock high overflow conditions
        with patch.object(database_optimizer, 'get_pool_statistics') as mock_stats:
            mock_stats.return_value = {"pool_overflows": 15, "long_running_connections": 2}
            
            results = await database_optimizer.optimize_connection_pool()
            
            assert results["optimization_applied"] is True
            assert len(results["improvements"]) > 0
            assert "pool size" in results["improvements"][0].lower()
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        summary = database_optimizer.get_performance_summary()
        
        assert isinstance(summary, dict)
        assert "monitoring_status" in summary
        assert "total_unique_queries" in summary
        assert "optimization_settings" in summary


class TestResponseCompressor:
    """Test response compression functionality."""
    
    def test_should_compress_json(self):
        """Test compression decision for JSON content."""
        content = b'{"test": "data", "array": [1, 2, 3, 4, 5]}'
        content_type = "application/json"
        accept_encoding = "gzip, deflate, br"
        
        should_compress, compression_type = response_compressor.should_compress(
            content, content_type, accept_encoding
        )
        
        assert should_compress is True
        assert compression_type == CompressionType.BROTLI  # Prefers Brotli
    
    def test_should_not_compress_small_content(self):
        """Test that small content is not compressed."""
        content = b'{"small": "data"}'  # Less than min_size_bytes
        content_type = "application/json"
        accept_encoding = "gzip, deflate"
        
        should_compress, compression_type = response_compressor.should_compress(
            content, content_type, accept_encoding
        )
        
        assert should_compress is False
        assert compression_type == CompressionType.NONE
    
    def test_should_not_compress_images(self):
        """Test that images are not compressed."""
        content = b"fake_image_data" * 100  # Large enough content
        content_type = "image/jpeg"
        accept_encoding = "gzip, deflate"
        
        should_compress, compression_type = response_compressor.should_compress(
            content, content_type, accept_encoding
        )
        
        assert should_compress is False
        assert compression_type == CompressionType.NONE
    
    def test_compress_content_gzip(self):
        """Test GZIP compression."""
        content = b'{"test": "data with some content to compress"}' * 20
        
        compressed_content, compression_time, compression_ratio = response_compressor.compress_content(
            content, CompressionType.GZIP
        )
        
        assert len(compressed_content) < len(content)
        assert compression_time > 0
        assert compression_ratio < 1.0
        
        # Verify it's actually GZIP compressed
        decompressed = gzip.decompress(compressed_content)
        assert decompressed == content
    
    def test_compress_content_brotli(self):
        """Test Brotli compression."""
        content = b'{"test": "data with some content to compress"}' * 20
        
        compressed_content, compression_time, compression_ratio = response_compressor.compress_content(
            content, CompressionType.BROTLI
        )
        
        assert len(compressed_content) < len(content)
        assert compression_time > 0
        assert compression_ratio < 1.0
        
        # Verify it's actually Brotli compressed
        decompressed = brotli.decompress(compressed_content)
        assert decompressed == content
    
    def test_optimize_json_payload(self):
        """Test JSON payload optimization."""
        data = {
            "name": "  John Doe  ",
            "email": "john@example.com",
            "age": None,
            "preferences": {
                "theme": "dark",
                "notifications": None,
                "language": "en"
            },
            "empty_list": [],
            "items": [
                {"id": 1, "name": "Item 1", "deleted": None},
                {"id": 2, "name": "Item 2", "deleted": False}
            ]
        }
        
        optimized = response_compressor.optimize_json_payload(data)
        
        # Check optimizations applied
        assert optimized["name"] == "John Doe"  # Trimmed whitespace
        assert "age" not in optimized  # Removed null values
        assert "notifications" not in optimized["preferences"]  # Removed null values
        assert len(optimized["items"]) == 2
        assert "deleted" not in optimized["items"][0]  # Removed null values
    
    def test_minify_css(self):
        """Test CSS minification."""
        css_content = """
        /* This is a comment */
        .container {
            padding: 10px;
            margin: 0 auto;
        }
        
        .button {
            background-color: blue;
            border: none;
        }
        """
        
        minified = response_compressor._minify_css(css_content)
        
        assert "/*" not in minified  # Comments removed
        assert minified.count(" ") < css_content.count(" ")  # Whitespace reduced
        assert "padding:10px" in minified  # Spaces after colons removed
    
    def test_minify_javascript(self):
        """Test JavaScript minification."""
        js_content = """
        // This is a comment
        function test() {
            var x = 1;
            var y = 2;
            return x + y;
        }
        
        /* Multi-line
           comment */
        var result = test();
        """
        
        minified = response_compressor._minify_javascript(js_content)
        
        assert "//" not in minified or "http" in minified  # Comments removed (except URLs)
        assert "/*" not in minified  # Multi-line comments removed
        assert minified.count(" ") < js_content.count(" ")  # Whitespace reduced
    
    def test_compression_statistics(self):
        """Test compression statistics tracking."""
        # Reset statistics
        response_compressor.reset_statistics()
        
        # Perform some compressions
        content = b'{"test": "data"}' * 50
        response_compressor.compress_content(content, CompressionType.GZIP)
        response_compressor.compress_content(content, CompressionType.BROTLI)
        
        stats = response_compressor.get_compression_statistics()
        
        assert stats["total_requests"] == 2
        assert stats["compressed_requests"] == 2
        assert stats["compression_rate"] == 100.0
        assert stats["avg_compression_ratio"] < 1.0
        assert stats["bandwidth_saved_percent"] > 0


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_record_request_metrics(self):
        """Test request metrics recording."""
        await performance_monitor.record_request_metrics(
            method="GET",
            path="/api/v1/test",
            status_code=200,
            response_time=0.5,
            request_size=1024,
            response_size=2048,
            user_id="test_user"
        )
        
        assert len(performance_monitor.request_metrics) > 0
        assert performance_monitor.counters["total_requests"] > 0
        
        latest_metric = performance_monitor.request_metrics[-1]
        assert latest_metric.method == "GET"
        assert latest_metric.path == "/api/v1/test"
        assert latest_metric.status_code == 200
        assert latest_metric.response_time == 0.5
    
    @pytest.mark.asyncio
    async def test_endpoint_metrics_aggregation(self):
        """Test endpoint metrics aggregation."""
        endpoint = "/api/v1/users"
        
        # Record multiple requests to same endpoint
        for i in range(10):
            await performance_monitor.record_request_metrics(
                method="GET",
                path=endpoint,
                status_code=200 if i < 8 else 500,  # 2 errors out of 10
                response_time=0.1 + (i * 0.05),
                request_size=500,
                response_size=1000
            )
        
        endpoint_key = f"GET {endpoint}"
        assert endpoint_key in performance_monitor.endpoint_metrics
        
        metrics = performance_monitor.endpoint_metrics[endpoint_key]
        assert metrics.request_count == 10
        assert metrics.error_count == 2
        assert metrics.error_rate == 0.2
        assert metrics.avg_response_time > 0.1
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        # Record cache hits and misses
        for _ in range(7):
            performance_monitor.record_cache_hit()
        
        for _ in range(3):
            performance_monitor.record_cache_miss()
        
        cache_stats = performance_monitor.get_cache_statistics()
        
        assert cache_stats["total_cache_hits"] == 7
        assert cache_stats["total_cache_misses"] == 3
        assert cache_stats["cache_hit_rate"] == 70.0
        assert cache_stats["cache_miss_rate"] == 30.0
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        summary = performance_monitor.get_performance_summary()
        
        assert isinstance(summary, dict)
        assert "monitoring_status" in summary
        assert "system_metrics" in summary
        assert "request_metrics" in summary
        assert "top_endpoints" in summary
        assert "baseline_metrics" in summary
    
    def test_endpoint_details(self):
        """Test endpoint details retrieval."""
        details = performance_monitor.get_endpoint_details()
        
        assert isinstance(details, list)
        
        if details:
            endpoint_detail = details[0]
            assert "endpoint" in endpoint_detail
            assert "request_count" in endpoint_detail
            assert "avg_response_time" in endpoint_detail
            assert "error_rate" in endpoint_detail
    
    @pytest.mark.asyncio
    async def test_performance_alert_triggering(self):
        """Test performance alert triggering."""
        # Simulate high error rate scenario
        for i in range(20):
            await performance_monitor.record_request_metrics(
                method="GET",
                path="/api/v1/error-prone",
                status_code=500,  # All errors
                response_time=0.1,
                request_size=100,
                response_size=100
            )
        
        # Trigger analysis manually
        await performance_monitor._analyze_request_performance()
        
        # Check if alert was triggered
        assert len(performance_monitor.active_alerts) > 0 or len(performance_monitor.alert_history) > 0


class TestCDNManager:
    """Test CDN management functionality."""
    
    def test_generate_asset_url(self):
        """Test CDN URL generation."""
        original_url = "https://example.com/images/logo.png"
        content_type = "image/png"
        
        cdn_url = cdn_manager.generate_asset_url(original_url, content_type)
        
        assert cdn_url != original_url
        assert "/cdn/" in cdn_url or cdn_manager.base_url in cdn_url
        
        # Check that asset was tracked
        asset_id = list(cdn_manager.assets.keys())[0] if cdn_manager.assets else None
        assert asset_id is not None
        
        asset = cdn_manager.assets[asset_id]
        assert asset.original_url == original_url
        assert asset.content_type == content_type
    
    def test_cache_control_for_content_types(self):
        """Test cache control determination for different content types."""
        # Test image cache control
        image_cache = cdn_manager._get_cache_control_for_type("image/jpeg")
        assert image_cache == CacheControl.LONG_TERM
        
        # Test JSON cache control
        json_cache = cdn_manager._get_cache_control_for_type("application/json")
        assert json_cache == CacheControl.SHORT_TERM
        
        # Test CSS cache control
        css_cache = cdn_manager._get_cache_control_for_type("text/css")
        assert css_cache == CacheControl.LONG_TERM
    
    @pytest.mark.asyncio
    async def test_optimize_content_delivery(self):
        """Test content optimization for CDN delivery."""
        css_content = b".test { padding: 10px; margin: 5px; }"
        content_type = "text/css"
        original_url = "https://example.com/styles.css"
        
        optimized_content, headers = await cdn_manager.optimize_content_delivery(
            css_content, content_type, original_url
        )
        
        assert len(optimized_content) <= len(css_content)  # Should be minified
        assert "cache-control" in headers
        assert "etag" in headers
    
    @pytest.mark.asyncio
    async def test_record_cdn_metrics(self):
        """Test CDN metrics recording."""
        # Generate an asset first
        asset_url = cdn_manager.generate_asset_url("https://example.com/test.js", "application/javascript")
        asset_id = list(cdn_manager.assets.keys())[0]
        
        # Record hits and misses
        await cdn_manager.record_cdn_hit(asset_id, response_time=0.05)
        await cdn_manager.record_cdn_hit(asset_id, response_time=0.03)
        await cdn_manager.record_cdn_miss(asset_id, response_time=0.2)
        
        asset = cdn_manager.assets[asset_id]
        assert asset.hit_count == 2
        assert asset.miss_count == 1
        
        # Check global stats
        assert cdn_manager.stats.total_requests == 3
        assert cdn_manager.stats.cache_hits == 2
        assert cdn_manager.stats.cache_misses == 1
    
    def test_purge_asset_cache(self):
        """Test CDN cache purging."""
        # Generate some assets
        url1 = cdn_manager.generate_asset_url("https://example.com/image1.jpg", "image/jpeg")
        url2 = cdn_manager.generate_asset_url("https://example.com/script.js", "application/javascript")
        
        asset_ids = list(cdn_manager.assets.keys())
        
        # Purge assets
        results = cdn_manager.purge_asset_cache(asset_ids)
        
        assert len(results) == len(asset_ids)
        assert all(success for success in results.values())
    
    @pytest.mark.asyncio
    async def test_optimize_for_region(self):
        """Test regional content optimization."""
        content_urls = [
            "https://example.com/image.jpg",
            "https://example.com/script.js",
            "https://example.com/style.css"
        ]
        region = "europe-west"
        
        optimized_urls = await cdn_manager.optimize_for_region(region, content_urls)
        
        assert len(optimized_urls) == len(content_urls)
        for original_url in content_urls:
            assert original_url in optimized_urls
            optimized_url = optimized_urls[original_url]
            assert optimized_url != original_url
            assert cdn_manager.base_url in optimized_url or "milan" in optimized_url
    
    def test_cdn_statistics(self):
        """Test CDN statistics generation."""
        stats = cdn_manager.get_cdn_statistics()
        
        assert isinstance(stats, dict)
        assert "provider" in stats
        assert "total_assets" in stats
        assert "cache_hit_rate" in stats
        assert "configuration" in stats
        assert "edge_locations" in stats


class TestPerformanceIntegration:
    """Test integration between performance components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_performance_monitoring(self):
        """Test complete performance monitoring flow."""
        # Simulate a request with database query and response compression
        start_time = time.time()
        
        # 1. Database query monitoring
        query = "SELECT * FROM users WHERE active = true"
        query_hash = await database_optimizer.monitor_query(
            query=query,
            execution_time=0.3,
            rows_affected=150
        )
        
        # 2. Request performance monitoring
        await performance_monitor.record_request_metrics(
            method="GET",
            path="/api/v1/users/active",
            status_code=200,
            response_time=time.time() - start_time,
            request_size=512,
            response_size=4096,
            user_id="test_user"
        )
        
        # 3. Response compression
        response_data = {"users": [{"id": i, "name": f"User {i}"} for i in range(50)]}
        import json
        content = json.dumps(response_data).encode()
        
        compressed_content, compression_time, compression_ratio = response_compressor.compress_content(
            content, CompressionType.GZIP
        )
        
        # 4. CDN asset handling
        cdn_url = cdn_manager.generate_asset_url(
            "/static/app.js", 
            "application/javascript"
        )
        
        # Verify all components recorded metrics
        assert query_hash in database_optimizer.query_stats
        assert len(performance_monitor.request_metrics) > 0
        assert len(compressed_content) < len(content)
        assert len(cdn_manager.assets) > 0
    
    def test_performance_optimization_recommendations(self):
        """Test that all performance components provide optimization recommendations."""
        # Database optimization summary
        db_summary = database_optimizer.get_performance_summary()
        assert "optimization_settings" in db_summary
        
        # Performance monitoring summary
        perf_summary = performance_monitor.get_performance_summary()
        assert "performance_thresholds" in perf_summary
        
        # Compression statistics
        compression_stats = response_compressor.get_compression_statistics()
        assert "settings" in compression_stats
        
        # CDN statistics
        cdn_stats = cdn_manager.get_cdn_statistics()
        assert "configuration" in cdn_stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])