"""Response compression system for optimizing API response sizes."""

import gzip
import json

try:
    import brotli

    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False
    brotli = None
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import logger


class CompressionType(str, Enum):
    """Supported compression types."""

    GZIP = "gzip"
    BROTLI = "br"
    NONE = "none"


@dataclass
class CompressionStats:
    """Compression statistics for monitoring."""

    total_requests: int = 0
    compressed_requests: int = 0
    total_bytes_original: int = 0
    total_bytes_compressed: int = 0
    compression_time: float = 0.0
    avg_compression_ratio: float = 0.0


class ResponseCompressor:
    """Handles response compression for API optimization."""

    def __init__(self):
        """Initialize response compressor."""
        self.enabled = True
        self.min_size_bytes = 500  # Only compress responses larger than 500 bytes
        self.compression_level_gzip = 6  # Balance between speed and compression
        self.compression_level_brotli = 4  # Brotli level (0-11)

        # Statistics tracking
        self.stats = CompressionStats()

        # Content types to compress
        self.compressible_types = {
            "application/json",
            "application/javascript",
            "text/plain",
            "text/html",
            "text/css",
            "text/xml",
            "application/xml",
            "application/rss+xml",
            "application/atom+xml",
            "image/svg+xml",
        }

        # Content types to never compress
        self.non_compressible_types = {
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "video/mp4",
            "audio/mpeg",
            "application/zip",
            "application/gzip",
            "application/pdf",
        }

    def should_compress(
        self, content: bytes, content_type: str | None = None, accept_encoding: str | None = None
    ) -> tuple[bool, CompressionType]:
        """Determine if response should be compressed and with which algorithm.

        Args:
            content: Response content bytes
            content_type: Response content type
            accept_encoding: Client's Accept-Encoding header

        Returns:
            Tuple of (should_compress, compression_type)
        """
        try:
            if not self.enabled:
                return False, CompressionType.NONE

            # Check minimum size threshold
            if len(content) < self.min_size_bytes:
                return False, CompressionType.NONE

            # Check content type
            if content_type:
                content_type = content_type.split(";")[0].strip().lower()

                if content_type in self.non_compressible_types:
                    return False, CompressionType.NONE

                if content_type not in self.compressible_types:
                    return False, CompressionType.NONE

            # Check client support
            if not accept_encoding:
                return False, CompressionType.NONE

            accept_encoding = accept_encoding.lower()

            # Prefer Brotli if supported (better compression)
            if "br" in accept_encoding:
                return True, CompressionType.BROTLI
            elif "gzip" in accept_encoding:
                return True, CompressionType.GZIP
            else:
                return False, CompressionType.NONE

        except Exception as e:
            logger.error(
                "compression_check_failed",
                content_size=len(content) if content else 0,
                content_type=content_type,
                error=str(e),
            )
            return False, CompressionType.NONE

    def compress_content(self, content: bytes, compression_type: CompressionType) -> tuple[bytes, float, float]:
        """Compress content using specified algorithm.

        Args:
            content: Content to compress
            compression_type: Compression algorithm to use

        Returns:
            Tuple of (compressed_content, compression_time, compression_ratio)
        """
        try:
            start_time = time.time()
            original_size = len(content)

            if compression_type == CompressionType.GZIP:
                compressed_content = gzip.compress(content, compresslevel=self.compression_level_gzip)
            elif compression_type == CompressionType.BROTLI:
                if BROTLI_AVAILABLE:
                    compressed_content = brotli.compress(content, quality=self.compression_level_brotli)
                else:
                    # Fallback to gzip if brotli not available
                    compressed_content = gzip.compress(content, compresslevel=self.compression_level_gzip)
            else:
                return content, 0.0, 1.0

            compression_time = time.time() - start_time
            compressed_size = len(compressed_content)
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0

            # Update statistics
            self.stats.total_requests += 1
            self.stats.compressed_requests += 1
            self.stats.total_bytes_original += original_size
            self.stats.total_bytes_compressed += compressed_size
            self.stats.compression_time += compression_time

            # Recalculate average compression ratio
            if self.stats.total_bytes_original > 0:
                self.stats.avg_compression_ratio = self.stats.total_bytes_compressed / self.stats.total_bytes_original

            logger.debug(
                "content_compressed",
                compression_type=compression_type.value,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=round(compression_ratio, 3),
                compression_time=round(compression_time * 1000, 2),  # ms
            )

            return compressed_content, compression_time, compression_ratio

        except Exception as e:
            logger.error(
                "content_compression_failed",
                compression_type=compression_type.value if compression_type else "none",
                content_size=len(content) if content else 0,
                error=str(e),
                exc_info=True,
            )

            # Update stats for failed compression
            self.stats.total_requests += 1
            return content, 0.0, 1.0

    def compress_json_response(self, data: Any, request: Request | None = None, status_code: int = 200) -> Response:
        """Create compressed JSON response.

        Args:
            data: Data to serialize and compress
            request: FastAPI request object for header analysis
            status_code: HTTP status code

        Returns:
            Compressed or uncompressed response
        """
        try:
            # Serialize data to JSON
            json_content = json.dumps(
                data,
                ensure_ascii=False,
                separators=(",", ":"),  # Minimize JSON size
            )
            content_bytes = json_content.encode("utf-8")

            # Determine compression
            accept_encoding = None
            if request:
                accept_encoding = request.headers.get("accept-encoding")

            should_compress, compression_type = self.should_compress(
                content_bytes, "application/json", accept_encoding
            )

            if should_compress:
                compressed_content, compression_time, compression_ratio = self.compress_content(
                    content_bytes, compression_type
                )

                headers = {
                    "content-encoding": compression_type.value,
                    "content-length": str(len(compressed_content)),
                    "vary": "Accept-Encoding",
                }

                return Response(
                    content=compressed_content, status_code=status_code, headers=headers, media_type="application/json"
                )
            else:
                # Update stats for uncompressed requests
                self.stats.total_requests += 1
                self.stats.total_bytes_original += len(content_bytes)
                self.stats.total_bytes_compressed += len(content_bytes)

                return JSONResponse(content=data, status_code=status_code)

        except Exception as e:
            logger.error(
                "json_response_compression_failed", data_type=type(data).__name__, error=str(e), exc_info=True
            )

            # Fallback to uncompressed response
            return JSONResponse(content=data, status_code=status_code)

    def optimize_json_payload(self, data: Any) -> Any:
        """Optimize JSON payload for better compression.

        Args:
            data: Data to optimize

        Returns:
            Optimized data structure
        """
        try:
            if isinstance(data, dict):
                optimized = {}
                for key, value in data.items():
                    # Recursively optimize nested structures
                    optimized_value = self.optimize_json_payload(value)

                    # Only include non-null values to reduce payload size
                    if optimized_value is not None:
                        optimized[key] = optimized_value

                return optimized

            elif isinstance(data, list):
                # Optimize list elements
                return [self.optimize_json_payload(item) for item in data if item is not None]

            elif isinstance(data, str):
                # Trim whitespace
                return data.strip() if data else data

            else:
                return data

        except Exception as e:
            logger.error("json_payload_optimization_failed", data_type=type(data).__name__, error=str(e))
            return data

    def create_optimized_response(
        self,
        data: Any,
        request: Request | None = None,
        optimize_payload: bool = True,
        cache_headers: bool = True,
        status_code: int = 200,
    ) -> Response:
        """Create optimized and compressed response with caching headers.

        Args:
            data: Response data
            request: FastAPI request object
            optimize_payload: Whether to optimize the payload structure
            cache_headers: Whether to add cache-control headers
            status_code: HTTP status code

        Returns:
            Optimized response
        """
        try:
            # Optimize payload if requested
            if optimize_payload:
                data = self.optimize_json_payload(data)

            # Create compressed response
            response = self.compress_json_response(data, request, status_code)

            # Add cache headers for better performance
            if cache_headers and status_code == 200:
                # Add cache headers for successful responses
                cache_control = "public, max-age=300"  # 5 minutes default

                # Adjust cache time based on data type
                if isinstance(data, dict):
                    if data.get("cached_at") or data.get("timestamp"):
                        cache_control = "public, max-age=60"  # 1 minute for timestamped data
                    elif "user_id" in data or "session_id" in data:
                        cache_control = "private, max-age=60"  # Private cache for user data

                response.headers["cache-control"] = cache_control
                response.headers["etag"] = f'W/"{hash(json.dumps(data, sort_keys=True))}"'

            return response

        except Exception as e:
            logger.error("optimized_response_creation_failed", error=str(e), exc_info=True)

            # Fallback to basic JSON response
            return JSONResponse(content=data, status_code=status_code)

    def get_compression_statistics(self) -> dict[str, Any]:
        """Get compression performance statistics.

        Returns:
            Compression statistics
        """
        try:
            stats = {
                "compression_enabled": self.enabled,
                "total_requests": self.stats.total_requests,
                "compressed_requests": self.stats.compressed_requests,
                "compression_rate": (
                    self.stats.compressed_requests / self.stats.total_requests * 100
                    if self.stats.total_requests > 0
                    else 0
                ),
                "bytes_saved": max(0, self.stats.total_bytes_original - self.stats.total_bytes_compressed),
                "avg_compression_ratio": round(self.stats.avg_compression_ratio, 3),
                "total_compression_time": round(self.stats.compression_time, 3),
                "avg_compression_time_ms": (
                    round(self.stats.compression_time / self.stats.compressed_requests * 1000, 2)
                    if self.stats.compressed_requests > 0
                    else 0
                ),
                "bandwidth_saved_percent": (
                    round((1 - self.stats.avg_compression_ratio) * 100, 1)
                    if self.stats.avg_compression_ratio > 0
                    else 0
                ),
                "settings": {
                    "min_size_bytes": self.min_size_bytes,
                    "compression_level_gzip": self.compression_level_gzip,
                    "compression_level_brotli": self.compression_level_brotli,
                    "compressible_types": list(self.compressible_types),
                },
            }

            return stats

        except Exception as e:
            logger.error("compression_statistics_failed", error=str(e), exc_info=True)
            return {"error": str(e)}

    def reset_statistics(self) -> bool:
        """Reset compression statistics.

        Returns:
            True if reset successful
        """
        try:
            self.stats = CompressionStats()
            logger.info("compression_statistics_reset")
            return True

        except Exception as e:
            logger.error("compression_statistics_reset_failed", error=str(e))
            return False


class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic response compression."""

    def __init__(self, app, compressor: ResponseCompressor):
        """Initialize compression middleware.

        Args:
            app: FastAPI application
            compressor: Response compressor instance
        """
        super().__init__(app)
        self.compressor = compressor

    async def dispatch(self, request: Request, call_next):
        """Apply compression to responses.

        Args:
            request: HTTP request
            call_next: Next middleware in chain

        Returns:
            Potentially compressed response
        """
        try:
            # Process request
            response = await call_next(request)

            # Only compress specific response types
            if not hasattr(response, "body") or response.status_code >= 400:
                return response

            # Get response content
            if hasattr(response, "body"):
                content = response.body
            else:
                # For streaming responses, don't compress
                return response

            if not content:
                return response

            # Check if compression is appropriate
            content_type = response.headers.get("content-type", "")
            accept_encoding = request.headers.get("accept-encoding", "")

            should_compress, compression_type = self.compressor.should_compress(content, content_type, accept_encoding)

            if should_compress:
                compressed_content, compression_time, compression_ratio = self.compressor.compress_content(
                    content, compression_type
                )

                # Update response headers
                response.headers["content-encoding"] = compression_type.value
                response.headers["content-length"] = str(len(compressed_content))
                response.headers["vary"] = "Accept-Encoding"

                # Create new response with compressed content
                from fastapi import Response as FastAPIResponse

                new_response = FastAPIResponse(
                    content=compressed_content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

                return new_response

            return response

        except Exception as e:
            logger.error("compression_middleware_failed", path=str(request.url.path), error=str(e), exc_info=True)
            return response


# Global instance
response_compressor = ResponseCompressor()
