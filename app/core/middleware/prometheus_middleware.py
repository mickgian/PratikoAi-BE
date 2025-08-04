"""Prometheus metrics middleware for HTTP request tracking."""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import logger
from app.core.monitoring.metrics import http_request_duration_seconds


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics for Prometheus."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track HTTP request metrics.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/endpoint to call
            
        Returns:
            The HTTP response
        """
        start_time = time.time()
        
        # Extract method and basic path
        method = request.method
        path = request.url.path
        
        # Normalize path to avoid high cardinality (group dynamic paths)
        normalized_path = self._normalize_path(path)
        
        try:
            # Process the request
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as e:
            # Track errors as 500s
            status_code = 500
            logger.error(
                "request_processing_error",
                method=method,
                path=path,
                error=str(e),
                exc_info=True
            )
            raise
            
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Track metrics
            try:
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=normalized_path,
                    status_code=str(status_code)
                ).observe(duration)
                
            except Exception as e:
                logger.error(
                    "request_metrics_tracking_failed",
                    method=method,
                    path=path,
                    error=str(e)
                )
        
        return response
    
    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize path to reduce cardinality in metrics.
        
        Args:
            path: Original request path
            
        Returns:
            Normalized path with parameters replaced
        """
        # Common API patterns to normalize
        normalized_patterns = {
            '/api/v1/auth': '/api/v1/auth',
            '/api/v1/chatbot': '/api/v1/chatbot',
            '/api/v1/payments': '/api/v1/payments',
            '/api/v1/analytics': '/api/v1/analytics',
            '/api/v1/italian': '/api/v1/italian',
            '/api/v1/search': '/api/v1/search',
            '/api/v1/security': '/api/v1/security',
            '/api/v1/performance': '/api/v1/performance',
            '/api/v1/monitoring': '/api/v1/monitoring',
            '/api/v1/privacy': '/api/v1/privacy',
            '/health': '/health',
            '/metrics': '/metrics',
            '/': '/',
        }
        
        # Check for exact matches first
        for pattern in normalized_patterns:
            if path.startswith(pattern):
                # For dynamic routes like /api/v1/payments/123/invoices
                if len(path) > len(pattern) and path[len(pattern)] == '/':
                    # Check if next segment looks like an ID
                    segments = path[len(pattern):].split('/')
                    if len(segments) > 1 and segments[1]:
                        # Replace ID-like segments with placeholder
                        if segments[1].isdigit() or len(segments[1]) > 10:
                            return f"{pattern}/{{id}}" + '/'.join([''] + segments[2:])
                
                return pattern
        
        # Default for unknown paths
        return '/other'