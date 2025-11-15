"""Base classes and interfaces for CCNL data source integration.

This module defines the abstract base classes for integrating with various
Italian labor data sources including unions, employer associations, and government agencies.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.models.ccnl_data import CCNLAgreement, CCNLSector

logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    """Types of CCNL data sources."""

    GOVERNMENT = "government"  # Official government sources
    UNION = "union"  # Union confederations
    EMPLOYER_ASSOCIATION = "employer_association"  # Employer associations
    SECTOR_ASSOCIATION = "sector_association"  # Sector-specific associations
    REGIONAL = "regional"  # Regional labor offices
    RESEARCH = "research"  # Research institutions


class DataSourceStatus(str, Enum):
    """Status of data source connection."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    RATE_LIMITED = "rate_limited"


class UpdateFrequency(str, Enum):
    """Frequency of data source updates."""

    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


@dataclass
class DataSourceInfo:
    """Information about a data source."""

    source_id: str
    name: str
    organization: str
    source_type: DataSourceType
    base_url: str
    description: str
    supported_sectors: list[CCNLSector]
    update_frequency: UpdateFrequency
    reliability_score: float  # 0.0 to 1.0
    last_updated: datetime | None = None
    status: DataSourceStatus = DataSourceStatus.INACTIVE
    api_key_required: bool = False
    rate_limit: int | None = None  # requests per hour
    contact_info: str | None = None


@dataclass
class CCNLDocument:
    """Represents a CCNL document from a data source."""

    document_id: str
    source_id: str
    title: str
    sector: CCNLSector
    publication_date: date
    effective_date: date
    expiry_date: date | None
    document_type: str  # "agreement", "renewal", "amendment", "interpretation"
    url: str
    content_hash: str
    raw_content: str | None = None
    extracted_data: dict[str, Any] | None = None
    confidence_score: float = 0.0  # Quality/confidence in extracted data


@dataclass
class DataSourceQuery:
    """Query parameters for data source searches."""

    sectors: list[CCNLSector] | None = None
    date_from: date | None = None
    date_to: date | None = None
    document_types: list[str] | None = None
    keywords: list[str] | None = None
    max_results: int = 100
    include_content: bool = False


class BaseDataSource(ABC):
    """Abstract base class for CCNL data sources."""

    def __init__(self, source_info: DataSourceInfo):
        self.source_info = source_info
        self.logger = logging.getLogger(f"{__name__}.{source_info.source_id}")
        self._last_request_time: datetime | None = None
        self._request_count: int = 0

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the data source."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the data source."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection to the data source is working."""
        pass

    @abstractmethod
    async def search_documents(self, query: DataSourceQuery) -> list[CCNLDocument]:
        """Search for CCNL documents in the data source."""
        pass

    @abstractmethod
    async def get_document_content(self, document_id: str) -> str | None:
        """Retrieve the full content of a specific document."""
        pass

    @abstractmethod
    async def get_latest_updates(self, since: datetime | None = None) -> list[CCNLDocument]:
        """Get documents updated since the specified time."""
        pass

    async def check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        if not self.source_info.rate_limit:
            return True

        now = datetime.utcnow()
        if self._last_request_time:
            time_diff = (now - self._last_request_time).total_seconds()
            if time_diff < 3600:  # Within the last hour
                if self._request_count >= self.source_info.rate_limit:
                    return False
            else:
                # Reset counter for new hour
                self._request_count = 0

        return True

    async def record_request(self) -> None:
        """Record a request for rate limiting purposes."""
        self._last_request_time = datetime.utcnow()
        self._request_count += 1

    async def get_source_statistics(self) -> dict[str, Any]:
        """Get statistics about the data source."""
        return {
            "source_id": self.source_info.source_id,
            "status": self.source_info.status.value,
            "last_updated": self.source_info.last_updated.isoformat() if self.source_info.last_updated else None,
            "supported_sectors": [sector.value for sector in self.source_info.supported_sectors],
            "reliability_score": self.source_info.reliability_score,
            "requests_this_hour": self._request_count,
            "rate_limit": self.source_info.rate_limit,
        }


class DataSourceRegistry:
    """Registry for managing multiple data sources."""

    def __init__(self):
        self.sources: dict[str, BaseDataSource] = {}
        self.source_priority: dict[str, int] = {}  # Higher number = higher priority

    def register_source(self, source: BaseDataSource, priority: int = 1):
        """Register a data source."""
        self.sources[source.source_info.source_id] = source
        self.source_priority[source.source_info.source_id] = priority
        logger.info(f"Registered data source: {source.source_info.source_id}")

    def unregister_source(self, source_id: str):
        """Unregister a data source."""
        if source_id in self.sources:
            del self.sources[source_id]
            del self.source_priority[source_id]
            logger.info(f"Unregistered data source: {source_id}")

    def get_source(self, source_id: str) -> BaseDataSource | None:
        """Get a specific data source."""
        return self.sources.get(source_id)

    def get_sources_by_type(self, source_type: DataSourceType) -> list[BaseDataSource]:
        """Get all sources of a specific type."""
        return [source for source in self.sources.values() if source.source_info.source_type == source_type]

    def get_sources_for_sector(self, sector: CCNLSector) -> list[BaseDataSource]:
        """Get all sources that support a specific sector."""
        return [source for source in self.sources.values() if sector in source.source_info.supported_sectors]

    def get_prioritized_sources(self) -> list[BaseDataSource]:
        """Get sources ordered by priority (highest first)."""
        return sorted(
            self.sources.values(), key=lambda s: self.source_priority.get(s.source_info.source_id, 0), reverse=True
        )

    async def search_all_sources(
        self, query: DataSourceQuery, source_types: list[DataSourceType] | None = None
    ) -> dict[str, list[CCNLDocument]]:
        """Search across multiple data sources."""
        results = {}

        # Filter sources by type if specified
        sources_to_search = []
        for source in self.sources.values():
            if source_types and source.source_info.source_type not in source_types:
                continue
            sources_to_search.append(source)

        # Search each source
        for source in sources_to_search:
            try:
                if await source.test_connection():
                    documents = await source.search_documents(query)
                    results[source.source_info.source_id] = documents
                    logger.info(f"Found {len(documents)} documents from {source.source_info.source_id}")
                else:
                    logger.warning(f"Cannot connect to source {source.source_info.source_id}")
                    results[source.source_info.source_id] = []
            except Exception as e:
                logger.error(f"Error searching source {source.source_info.source_id}: {str(e)}")
                results[source.source_info.source_id] = []

        return results

    async def get_source_health_status(self) -> dict[str, dict[str, Any]]:
        """Get health status of all registered sources."""
        health_status = {}

        for source_id, source in self.sources.items():
            try:
                is_connected = await source.test_connection()
                stats = await source.get_source_statistics()

                health_status[source_id] = {
                    "connected": is_connected,
                    "status": source.source_info.status.value,
                    "last_updated": source.source_info.last_updated.isoformat()
                    if source.source_info.last_updated
                    else None,
                    "reliability_score": source.source_info.reliability_score,
                    "statistics": stats,
                }
            except Exception as e:
                health_status[source_id] = {"connected": False, "status": "error", "error": str(e), "statistics": None}

        return health_status


# Global registry instance
data_source_registry = DataSourceRegistry()
