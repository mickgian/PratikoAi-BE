"""Middleware package."""

# Import middleware classes that are used by main.py
try:
    from .prometheus_middleware import PrometheusMiddleware as MetricsMiddleware
except ImportError:
    # Fallback if prometheus middleware not available
    class MetricsMiddleware:
        pass