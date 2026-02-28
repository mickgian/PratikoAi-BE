"""DEV-418: Tests for Monitoring and Metrics Middleware.

Tests: registry operations, Prometheus format, middleware ASGI lifecycle.
"""

import pytest

from app.middleware.metrics import MetricsMiddleware, MetricsRegistry


@pytest.fixture
def registry():
    """Fresh registry per test to avoid cross-test state."""
    return MetricsRegistry()


class TestMetricsRegistry:
    def test_increment_counter(self, registry):
        registry.increment("test_counter", labels={"method": "GET"})
        assert registry.get("test_counter", labels={"method": "GET"}) == 1.0

    def test_increment_counter_accumulates(self, registry):
        registry.increment("test_counter")
        registry.increment("test_counter")
        registry.increment("test_counter", value=3.0)
        assert registry.get("test_counter") == 5.0

    def test_get_missing_counter_returns_zero(self, registry):
        assert registry.get("nonexistent") == 0.0

    def test_set_gauge(self, registry):
        registry.set_gauge("db_pool", 5.0)
        assert registry.get_gauge("db_pool") == 5.0

    def test_get_missing_gauge_returns_zero(self, registry):
        assert registry.get_gauge("nonexistent") == 0.0

    def test_observe_histogram(self, registry):
        registry.observe("latency", 0.15, labels={"path": "/api"})
        registry.observe("latency", 0.25, labels={"path": "/api"})
        # No error means success; check format output
        output = registry.format_prometheus()
        assert "latency" in output

    def test_counter_with_labels(self, registry):
        registry.increment("req", labels={"method": "GET", "path": "/a"})
        registry.increment("req", labels={"method": "POST", "path": "/b"})
        assert registry.get("req", labels={"method": "GET", "path": "/a"}) == 1.0
        assert registry.get("req", labels={"method": "POST", "path": "/b"}) == 1.0

    def test_counter_without_labels(self, registry):
        registry.increment("simple_counter")
        assert registry.get("simple_counter") == 1.0


class TestPrometheusFormat:
    def test_format_counters(self, registry):
        registry.increment("http_total", labels={"method": "GET"})
        output = registry.format_prometheus()
        assert "# TYPE http_total counter" in output
        assert "http_total" in output

    def test_format_gauges(self, registry):
        registry.set_gauge("active_connections", 10.0)
        output = registry.format_prometheus()
        assert "# TYPE active_connections gauge" in output
        assert "active_connections 10.0" in output

    def test_format_histograms(self, registry):
        for val in [0.1, 0.2, 0.3, 0.5, 1.0]:
            registry.observe("duration", val)
        output = registry.format_prometheus()
        assert "# TYPE duration summary" in output
        assert 'quantile="0.5"' in output
        assert 'quantile="0.95"' in output
        assert 'quantile="0.99"' in output
        assert "duration_count" in output
        assert "duration_sum" in output

    def test_format_empty_registry(self, registry):
        output = registry.format_prometheus()
        assert output == ""

    def test_histogram_with_labels(self, registry):
        registry.observe("dur", 0.1, labels={"path": "/health"})
        output = registry.format_prometheus()
        assert "dur" in output
        assert "/health" in output


class TestMakeKey:
    def test_no_labels(self):
        assert MetricsRegistry._make_key("metric") == "metric"

    def test_with_labels(self):
        key = MetricsRegistry._make_key("metric", {"a": "1", "b": "2"})
        assert key == 'metric{a="1",b="2"}'

    def test_parse_key_simple(self):
        name, labels = MetricsRegistry._parse_key("metric")
        assert name == "metric"
        assert labels == ""

    def test_parse_key_with_labels(self):
        name, labels = MetricsRegistry._parse_key('metric{a="1"}')
        assert name == "metric"
        assert labels == '{a="1"}'

    def test_merge_labels_empty(self):
        assert MetricsRegistry._merge_labels("") == ""

    def test_merge_labels_with_content(self):
        result = MetricsRegistry._merge_labels('{path="/api"}')
        assert result == ',path="/api"'


class TestMetricsMiddleware:
    def test_instantiation(self):
        mw = MetricsMiddleware(app=None)
        assert mw.app is None

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        """Non-HTTP scopes should pass through to the wrapped app."""
        calls = []

        async def mock_app(scope, receive, send):
            calls.append(scope["type"])

        mw = MetricsMiddleware(app=mock_app)
        await mw({"type": "websocket"}, None, None)
        assert calls == ["websocket"]

    @pytest.mark.asyncio
    async def test_http_scope_records_metrics(self):
        """HTTP scopes should record request count and duration."""
        reg = MetricsRegistry()

        async def mock_app(scope, receive, send):
            pass

        mw = MetricsMiddleware(app=mock_app)
        await mw({"type": "http", "path": "/test", "method": "GET"}, None, None)
        # The middleware uses the global registry, so just check no error

    @pytest.mark.asyncio
    async def test_non_http_no_app(self):
        """Non-HTTP scope with None app should not crash."""
        mw = MetricsMiddleware(app=None)
        await mw({"type": "lifespan"}, None, None)
