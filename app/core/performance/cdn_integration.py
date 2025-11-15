"""CDN integration for optimizing static content delivery and caching."""

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from app.core.config import settings
from app.core.logging import logger


class CDNProvider(str, Enum):
    """Supported CDN providers."""

    CLOUDFLARE = "cloudflare"
    AMAZON_CLOUDFRONT = "cloudfront"
    AZURE_CDN = "azure_cdn"
    GOOGLE_CDN = "google_cdn"
    LOCAL = "local"


class CacheControl(str, Enum):
    """Cache control strategies."""

    NO_CACHE = "no-cache"
    SHORT_TERM = "short-term"  # 5 minutes
    MEDIUM_TERM = "medium-term"  # 1 hour
    LONG_TERM = "long-term"  # 24 hours
    IMMUTABLE = "immutable"  # 1 year


@dataclass
class CDNAsset:
    """CDN asset information."""

    asset_id: str
    original_url: str
    cdn_url: str
    content_type: str
    size_bytes: int
    etag: str
    cache_control: CacheControl
    created_at: datetime
    last_accessed: datetime
    hit_count: int
    miss_count: int


@dataclass
class CDNStats:
    """CDN performance statistics."""

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    bytes_served: int = 0
    bytes_saved: int = 0
    avg_response_time: float = 0.0
    total_assets: int = 0


class CDNManager:
    """Manages CDN integration and content optimization."""

    def __init__(self):
        """Initialize CDN manager."""
        self.enabled = True
        self.provider = CDNProvider.LOCAL  # Default to local for development
        self.base_url = "https://cdn.normoai.com"  # Would be actual CDN URL

        # Asset tracking
        self.assets: dict[str, CDNAsset] = {}
        self.stats = CDNStats()

        # CDN configuration
        self.config = {
            "max_file_size_mb": 50,
            "supported_types": {
                "image/jpeg",
                "image/png",
                "image/gif",
                "image/webp",
                "text/css",
                "application/javascript",
                "application/json",
                "text/html",
                "application/pdf",
                "video/mp4",
            },
            "cache_rules": {
                "image/*": CacheControl.LONG_TERM,
                "text/css": CacheControl.LONG_TERM,
                "application/javascript": CacheControl.LONG_TERM,
                "application/json": CacheControl.SHORT_TERM,
                "text/html": CacheControl.MEDIUM_TERM,
                "application/pdf": CacheControl.LONG_TERM,
            },
            "compression_enabled": True,
            "minification_enabled": True,
        }

        # Edge locations for performance optimization
        self.edge_locations = {
            "europe-west": ["milan", "frankfurt", "paris"],
            "us-east": ["virginia", "ohio"],
            "us-west": ["oregon", "california"],
            "asia-pacific": ["singapore", "tokyo"],
        }

    def generate_asset_url(
        self, original_url: str, content_type: str | None = None, cache_control: CacheControl | None = None
    ) -> str:
        """Generate CDN URL for an asset.

        Args:
            original_url: Original asset URL
            content_type: MIME type of the content
            cache_control: Cache control strategy

        Returns:
            CDN URL for the asset
        """
        try:
            if not self.enabled:
                return original_url

            # Generate asset ID
            asset_id = hashlib.md5(original_url.encode()).hexdigest()

            # Determine cache control
            if not cache_control and content_type:
                cache_control = self._get_cache_control_for_type(content_type)

            # Create CDN URL
            if self.provider == CDNProvider.LOCAL:
                cdn_url = f"/cdn/{asset_id}"
            else:
                cdn_url = urljoin(self.base_url, f"assets/{asset_id}")

            # Track asset
            if asset_id not in self.assets:
                self.assets[asset_id] = CDNAsset(
                    asset_id=asset_id,
                    original_url=original_url,
                    cdn_url=cdn_url,
                    content_type=content_type or "application/octet-stream",
                    size_bytes=0,  # Would be determined during upload
                    etag=asset_id,
                    cache_control=cache_control or CacheControl.MEDIUM_TERM,
                    created_at=datetime.utcnow(),
                    last_accessed=datetime.utcnow(),
                    hit_count=0,
                    miss_count=0,
                )

                self.stats.total_assets += 1

            logger.debug(
                "cdn_url_generated",
                asset_id=asset_id,
                original_url=original_url,
                cdn_url=cdn_url,
                cache_control=cache_control.value if cache_control else None,
            )

            return cdn_url

        except Exception as e:
            logger.error("cdn_url_generation_failed", original_url=original_url, error=str(e), exc_info=True)
            return original_url

    def _get_cache_control_for_type(self, content_type: str) -> CacheControl:
        """Get appropriate cache control for content type."""
        content_type = content_type.lower()

        # Check specific rules first
        for pattern, cache_control in self.config["cache_rules"].items():
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if content_type.startswith(prefix):
                    return cache_control
            elif content_type == pattern:
                return cache_control

        # Default cache control
        return CacheControl.MEDIUM_TERM

    async def optimize_content_delivery(
        self, content: bytes, content_type: str, original_url: str
    ) -> tuple[bytes, dict[str, str]]:
        """Optimize content for CDN delivery.

        Args:
            content: Original content bytes
            content_type: MIME type
            original_url: Original URL

        Returns:
            Tuple of (optimized_content, headers)
        """
        try:
            optimized_content = content
            headers = {}

            # Apply content type specific optimizations
            if content_type.startswith("text/") or content_type == "application/javascript":
                optimized_content = await self._optimize_text_content(content, content_type)
            elif content_type.startswith("image/"):
                optimized_content = await self._optimize_image_content(content, content_type)

            # Set cache headers
            cache_control = self._get_cache_control_for_type(content_type)
            headers.update(self._get_cache_headers(cache_control))

            # Set compression headers
            if self.config["compression_enabled"] and len(optimized_content) > 500:
                headers["vary"] = "Accept-Encoding"

            # Set ETag
            etag = hashlib.md5(optimized_content).hexdigest()
            headers["etag"] = f'"{etag}"'

            # Security headers
            headers.update(self._get_security_headers(content_type))

            logger.debug(
                "content_optimized_for_cdn",
                original_size=len(content),
                optimized_size=len(optimized_content),
                content_type=content_type,
                compression_ratio=len(optimized_content) / len(content) if len(content) > 0 else 1.0,
            )

            return optimized_content, headers

        except Exception as e:
            logger.error(
                "content_optimization_failed",
                content_type=content_type,
                original_url=original_url,
                error=str(e),
                exc_info=True,
            )
            return content, {}

    async def _optimize_text_content(self, content: bytes, content_type: str) -> bytes:
        """Optimize text-based content."""
        try:
            text_content = content.decode("utf-8")

            if self.config["minification_enabled"]:
                if content_type == "text/css":
                    text_content = self._minify_css(text_content)
                elif content_type == "application/javascript":
                    text_content = self._minify_javascript(text_content)
                elif content_type == "text/html":
                    text_content = self._minify_html(text_content)

            return text_content.encode("utf-8")

        except Exception as e:
            logger.error("text_content_optimization_failed", content_type=content_type, error=str(e))
            return content

    def _minify_css(self, css_content: str) -> str:
        """Simple CSS minification."""
        import re

        # Remove comments
        css_content = re.sub(r"/\*.*?\*/", "", css_content, flags=re.DOTALL)

        # Remove extra whitespace
        css_content = re.sub(r"\s+", " ", css_content)
        css_content = re.sub(r";\s*}", "}", css_content)
        css_content = re.sub(r"{\s*", "{", css_content)
        css_content = re.sub(r"}\s*", "}", css_content)
        css_content = re.sub(r":\s*", ":", css_content)
        css_content = re.sub(r";\s*", ";", css_content)

        return css_content.strip()

    def _minify_javascript(self, js_content: str) -> str:
        """Simple JavaScript minification."""
        import re

        # Remove single-line comments (but preserve URLs)
        js_content = re.sub(r"//(?![^\n]*http).*?(?=\n|$)", "", js_content)

        # Remove multi-line comments
        js_content = re.sub(r"/\*.*?\*/", "", js_content, flags=re.DOTALL)

        # Remove extra whitespace
        js_content = re.sub(r"\s+", " ", js_content)
        js_content = re.sub(r";\s*", ";", js_content)
        js_content = re.sub(r"{\s*", "{", js_content)
        js_content = re.sub(r"}\s*", "}", js_content)

        return js_content.strip()

    def _minify_html(self, html_content: str) -> str:
        """Simple HTML minification."""
        import re

        # Remove HTML comments
        html_content = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)

        # Remove extra whitespace between tags
        html_content = re.sub(r">\s+<", "><", html_content)

        # Remove extra whitespace
        html_content = re.sub(r"\s+", " ", html_content)

        return html_content.strip()

    async def _optimize_image_content(self, content: bytes, content_type: str) -> bytes:
        """Optimize image content (placeholder for actual image optimization)."""
        # In a real implementation, this would:
        # - Compress images
        # - Convert to WebP if supported
        # - Resize if too large
        # - Apply quality optimization

        # For now, return original content
        return content

    def _get_cache_headers(self, cache_control: CacheControl) -> dict[str, str]:
        """Get cache control headers for the specified strategy."""
        headers = {}

        if cache_control == CacheControl.NO_CACHE:
            headers["cache-control"] = "no-cache, no-store, must-revalidate"
            headers["pragma"] = "no-cache"
            headers["expires"] = "0"

        elif cache_control == CacheControl.SHORT_TERM:
            headers["cache-control"] = "public, max-age=300"  # 5 minutes

        elif cache_control == CacheControl.MEDIUM_TERM:
            headers["cache-control"] = "public, max-age=3600"  # 1 hour

        elif cache_control == CacheControl.LONG_TERM:
            headers["cache-control"] = "public, max-age=86400"  # 24 hours

        elif cache_control == CacheControl.IMMUTABLE:
            headers["cache-control"] = "public, max-age=31536000, immutable"  # 1 year

        return headers

    def _get_security_headers(self, content_type: str) -> dict[str, str]:
        """Get security headers appropriate for content type."""
        headers = {}

        # Content Security Policy for HTML
        if content_type == "text/html":
            headers["content-security-policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:;"
            )
            headers["x-content-type-options"] = "nosniff"
            headers["x-frame-options"] = "DENY"
            headers["x-xss-protection"] = "1; mode=block"

        # CORS headers for API responses
        elif content_type == "application/json":
            headers["access-control-allow-origin"] = "*"
            headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            headers["access-control-allow-headers"] = "Content-Type, Authorization"

        return headers

    async def record_cdn_hit(self, asset_id: str, response_time: float = 0.0) -> None:
        """Record a CDN cache hit."""
        try:
            if asset_id in self.assets:
                asset = self.assets[asset_id]
                asset.hit_count += 1
                asset.last_accessed = datetime.utcnow()

                # Update stats
                self.stats.total_requests += 1
                self.stats.cache_hits += 1
                self.stats.bytes_served += asset.size_bytes

                # Update average response time
                if self.stats.total_requests > 1:
                    self.stats.avg_response_time = (
                        self.stats.avg_response_time * (self.stats.total_requests - 1) + response_time
                    ) / self.stats.total_requests
                else:
                    self.stats.avg_response_time = response_time

        except Exception as e:
            logger.error("cdn_hit_recording_failed", asset_id=asset_id, error=str(e))

    async def record_cdn_miss(self, asset_id: str, response_time: float = 0.0) -> None:
        """Record a CDN cache miss."""
        try:
            if asset_id in self.assets:
                asset = self.assets[asset_id]
                asset.miss_count += 1
                asset.last_accessed = datetime.utcnow()

                # Update stats
                self.stats.total_requests += 1
                self.stats.cache_misses += 1

        except Exception as e:
            logger.error("cdn_miss_recording_failed", asset_id=asset_id, error=str(e))

    def purge_asset_cache(self, asset_ids: list[str]) -> dict[str, bool]:
        """Purge assets from CDN cache.

        Args:
            asset_ids: List of asset IDs to purge

        Returns:
            Dictionary of asset_id -> success status
        """
        try:
            results = {}

            for asset_id in asset_ids:
                if asset_id in self.assets:
                    # In a real implementation, this would call CDN API
                    # For now, simulate successful purge
                    results[asset_id] = True

                    logger.info("cdn_asset_purged", asset_id=asset_id, original_url=self.assets[asset_id].original_url)
                else:
                    results[asset_id] = False
                    logger.warning("cdn_asset_purge_failed", asset_id=asset_id, reason="asset_not_found")

            return results

        except Exception as e:
            logger.error("cdn_cache_purge_failed", asset_ids=asset_ids, error=str(e), exc_info=True)
            return dict.fromkeys(asset_ids, False)

    def get_cdn_statistics(self) -> dict[str, Any]:
        """Get CDN performance statistics.

        Returns:
            CDN statistics and metrics
        """
        try:
            cache_hit_rate = (
                self.stats.cache_hits / self.stats.total_requests * 100 if self.stats.total_requests > 0 else 0
            )

            bandwidth_saved = (
                self.stats.bytes_saved / (self.stats.bytes_served + self.stats.bytes_saved) * 100
                if (self.stats.bytes_served + self.stats.bytes_saved) > 0
                else 0
            )

            # Top performing assets
            top_assets = sorted(self.assets.values(), key=lambda x: x.hit_count, reverse=True)[:10]

            # Assets needing attention (high miss rate)
            problematic_assets = [
                asset
                for asset in self.assets.values()
                if asset.miss_count > asset.hit_count and (asset.hit_count + asset.miss_count) > 10
            ]

            statistics = {
                "provider": self.provider.value,
                "enabled": self.enabled,
                "total_assets": self.stats.total_assets,
                "total_requests": self.stats.total_requests,
                "cache_hits": self.stats.cache_hits,
                "cache_misses": self.stats.cache_misses,
                "cache_hit_rate": round(cache_hit_rate, 2),
                "bytes_served_mb": round(self.stats.bytes_served / (1024 * 1024), 2),
                "bytes_saved_mb": round(self.stats.bytes_saved / (1024 * 1024), 2),
                "bandwidth_saved_percent": round(bandwidth_saved, 2),
                "avg_response_time_ms": round(self.stats.avg_response_time * 1000, 2),
                "top_assets": [
                    {
                        "asset_id": asset.asset_id,
                        "original_url": asset.original_url,
                        "hit_count": asset.hit_count,
                        "miss_count": asset.miss_count,
                        "cache_efficiency": (
                            asset.hit_count / (asset.hit_count + asset.miss_count) * 100
                            if (asset.hit_count + asset.miss_count) > 0
                            else 0
                        ),
                    }
                    for asset in top_assets
                ],
                "problematic_assets": [
                    {
                        "asset_id": asset.asset_id,
                        "original_url": asset.original_url,
                        "hit_count": asset.hit_count,
                        "miss_count": asset.miss_count,
                        "issue": "high_miss_rate",
                    }
                    for asset in problematic_assets[:5]
                ],
                "edge_locations": self.edge_locations,
                "configuration": {
                    "max_file_size_mb": self.config["max_file_size_mb"],
                    "compression_enabled": self.config["compression_enabled"],
                    "minification_enabled": self.config["minification_enabled"],
                    "supported_types_count": len(self.config["supported_types"]),
                },
            }

            return statistics

        except Exception as e:
            logger.error("cdn_statistics_generation_failed", error=str(e), exc_info=True)
            return {"error": str(e)}

    async def optimize_for_region(self, region: str, content_urls: list[str]) -> dict[str, str]:
        """Optimize content delivery for a specific region.

        Args:
            region: Target region
            content_urls: URLs to optimize

        Returns:
            Dictionary mapping original URLs to optimized URLs
        """
        try:
            optimized_urls = {}

            # Get edge locations for region
            edge_locations = self.edge_locations.get(region, ["global"])

            for url in content_urls:
                # Generate region-specific CDN URL
                asset_id = hashlib.md5(url.encode()).hexdigest()

                if region in self.edge_locations:
                    # Use region-specific edge location
                    edge_location = edge_locations[0]  # Use primary edge location
                    optimized_url = f"{self.base_url}/{edge_location}/assets/{asset_id}"
                else:
                    # Use global CDN
                    optimized_url = f"{self.base_url}/assets/{asset_id}"

                optimized_urls[url] = optimized_url

            logger.info(
                "content_optimized_for_region",
                region=region,
                urls_count=len(content_urls),
                edge_locations=edge_locations,
            )

            return optimized_urls

        except Exception as e:
            logger.error("regional_optimization_failed", region=region, error=str(e), exc_info=True)
            return {}


# Global instance
cdn_manager = CDNManager()
