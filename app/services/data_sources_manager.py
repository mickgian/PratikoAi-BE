"""CCNL Data Sources Manager.

This service orchestrates all CCNL data sources including CNEL, union confederations,
employer associations, and sector-specific organizations to provide comprehensive
and up-to-date labor agreement information.
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from app.models.ccnl_data import CCNLSector
from app.services.data_sources.base_source import (
    BaseDataSource,
    CCNLDocument,
    DataSourceQuery,
    DataSourceRegistry,
    DataSourceStatus,
    DataSourceType,
    data_source_registry,
)
from app.services.data_sources.cassazione_source import CassazioneDataSource
from app.services.data_sources.cnel_source import CNELDataSource
from app.services.data_sources.employer_sources import (
    ConfapiDataSource,
    ConfartigianatoDataSource,
    ConfcommercioDataSource,
    ConfindustriaDataSource,
)
from app.services.data_sources.government_sources import (
    INPSDataSource,
    MinistryOfLaborDataSource,
    get_all_government_sources,
)
from app.services.data_sources.sector_associations import (
    ASSINFORMDataSource,
    ASSOMARMIDataSource,
    FederalimentareDataSource,
    FederchimicaDataSource,
    FedermeccanicaDataSource,
    get_all_sector_associations,
)
from app.services.data_sources.union_sources import CGILDataSource, CISLDataSource, UGLDataSource, UILDataSource

logger = logging.getLogger(__name__)


@dataclass
class DataSourceSummary:
    """Summary of data source search results."""

    total_documents: int
    documents_by_source: dict[str, int]
    documents_by_sector: dict[CCNLSector, int]
    documents_by_type: dict[str, int]
    coverage_score: float  # 0.0 to 1.0 - how well query was covered
    search_duration: float  # seconds
    errors: list[str]


@dataclass
class DocumentRelevance:
    """Document relevance scoring."""

    document: CCNLDocument
    relevance_score: float
    source_reliability: float
    freshness_score: float
    final_score: float
    ranking_factors: dict[str, float]


class DataSourcesManager:
    """Manager for all CCNL data sources."""

    def __init__(self):
        self.registry = data_source_registry
        self.initialized = False
        self.update_tasks: dict[str, asyncio.Task] = {}
        self.source_priorities = {
            DataSourceType.GOVERNMENT: 1.0,
            DataSourceType.UNION: 0.85,
            DataSourceType.EMPLOYER_ASSOCIATION: 0.80,
            DataSourceType.SECTOR_ASSOCIATION: 0.75,
            DataSourceType.REGIONAL: 0.70,
            DataSourceType.RESEARCH: 0.60,
        }

    async def initialize(self):
        """Initialize all data sources."""
        if self.initialized:
            return

        logger.info("Initializing CCNL data sources manager")

        # Register all data sources
        await self._register_all_sources()

        # Connect to all sources
        await self._connect_all_sources()

        # Start background update tasks
        await self._start_background_tasks()

        self.initialized = True
        logger.info("CCNL data sources manager initialized")

    async def _register_all_sources(self):
        """Register all available data sources."""
        sources = [
            # Government sources (highest priority)
            (CNELDataSource(), 10),
            (CassazioneDataSource(), 10),  # Italian Supreme Court - highest reliability
            (MinistryOfLaborDataSource(), 10),  # Official Ministry of Labor
            (INPSDataSource(), 9),  # National social security institute
            # Union confederations
            (CGILDataSource(), 8),
            (CISLDataSource(), 8),
            (UILDataSource(), 7),
            (UGLDataSource(), 6),
            # Employer associations
            (ConfindustriaDataSource(), 7),
            (ConfcommercioDataSource(), 7),
            (ConfartigianatoDataSource(), 6),
            (ConfapiDataSource(), 6),
            # Sector-specific associations
            (FedermeccanicaDataSource(), 6),
            (FederchimicaDataSource(), 6),
            (FederalimentareDataSource(), 6),
            (ASSINFORMDataSource(), 5),
            (ASSOMARMIDataSource(), 5),
        ]

        for source, priority in sources:
            self.registry.register_source(source, priority)

        logger.info(f"Registered {len(sources)} data sources")

    async def _connect_all_sources(self):
        """Connect to all registered sources."""
        connection_tasks = []

        for source in self.registry.sources.values():
            task = asyncio.create_task(self._safe_connect(source))
            connection_tasks.append(task)

        results = await asyncio.gather(*connection_tasks, return_exceptions=True)

        connected_count = sum(1 for result in results if result is True)
        logger.info(f"Connected to {connected_count}/{len(connection_tasks)} data sources")

    async def _safe_connect(self, source: BaseDataSource) -> bool:
        """Safely connect to a data source."""
        try:
            return await source.connect()
        except Exception as e:
            logger.error(f"Error connecting to {source.source_info.source_id}: {str(e)}")
            return False

    async def _start_background_tasks(self):
        """Start background update tasks."""
        # Start periodic health checks
        self.update_tasks["health_check"] = asyncio.create_task(self._periodic_health_check())

        # Start data refresh tasks for each source type
        self.update_tasks["refresh_government"] = asyncio.create_task(
            self._periodic_data_refresh(DataSourceType.GOVERNMENT, hours=6)
        )
        self.update_tasks["refresh_unions"] = asyncio.create_task(
            self._periodic_data_refresh(DataSourceType.UNION, hours=12)
        )
        self.update_tasks["refresh_employers"] = asyncio.create_task(
            self._periodic_data_refresh(DataSourceType.EMPLOYER_ASSOCIATION, hours=24)
        )

    async def comprehensive_search(
        self,
        query: DataSourceQuery,
        include_source_types: list[DataSourceType] | None = None,
        exclude_unreliable: bool = True,
        max_concurrent_sources: int = 5,
    ) -> DataSourceSummary:
        """Perform comprehensive search across all relevant data sources."""
        start_time = datetime.utcnow()

        if not self.initialized:
            await self.initialize()

        # Filter sources based on criteria
        sources_to_search = await self._filter_sources_for_search(query, include_source_types, exclude_unreliable)

        # Search sources concurrently with semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent_sources)
        search_tasks = [self._search_source_with_semaphore(source, query, semaphore) for source in sources_to_search]

        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Process results
        all_documents = []
        documents_by_source = {}
        errors = []

        for i, result in enumerate(results):
            source = sources_to_search[i]
            source_id = source.source_info.source_id

            if isinstance(result, Exception):
                error_msg = f"Error searching {source_id}: {str(result)}"
                errors.append(error_msg)
                logger.error(error_msg)
                documents_by_source[source_id] = 0
            else:
                documents = result
                all_documents.extend(documents)
                documents_by_source[source_id] = len(documents)
                logger.info(f"Found {len(documents)} documents from {source_id}")

        # Rank and deduplicate documents
        ranked_documents = await self._rank_and_deduplicate_documents(all_documents, query)

        # Calculate summary statistics
        search_duration = (datetime.utcnow() - start_time).total_seconds()

        return DataSourceSummary(
            total_documents=len(ranked_documents),
            documents_by_source=documents_by_source,
            documents_by_sector=self._count_by_sector(ranked_documents),
            documents_by_type=self._count_by_type(ranked_documents),
            coverage_score=self._calculate_coverage_score(ranked_documents, query),
            search_duration=search_duration,
            errors=errors,
        )

    async def _filter_sources_for_search(
        self, query: DataSourceQuery, include_source_types: list[DataSourceType] | None, exclude_unreliable: bool
    ) -> list[BaseDataSource]:
        """Filter sources based on search criteria."""
        candidate_sources = []

        # Get all active sources
        for source in self.registry.sources.values():
            # Check if source is active
            if source.source_info.status != DataSourceStatus.ACTIVE:
                continue

            # Check source type filter
            if include_source_types and source.source_info.source_type not in include_source_types:
                continue

            # Check reliability filter
            if exclude_unreliable and source.source_info.reliability_score < 0.7:
                continue

            # Check if source supports any of the requested sectors
            if query.sectors:
                source_sectors = set(source.source_info.supported_sectors)
                query_sectors = set(query.sectors)
                if not source_sectors.intersection(query_sectors):
                    continue

            candidate_sources.append(source)

        # Sort by priority (highest first)
        candidate_sources.sort(
            key=lambda s: self.registry.source_priority.get(s.source_info.source_id, 0), reverse=True
        )

        return candidate_sources

    async def _search_source_with_semaphore(
        self, source: BaseDataSource, query: DataSourceQuery, semaphore: asyncio.Semaphore
    ) -> list[CCNLDocument]:
        """Search a source with semaphore-based rate limiting."""
        async with semaphore:
            try:
                # Test connection before searching
                if not await source.test_connection():
                    logger.warning(f"Cannot connect to {source.source_info.source_id}")
                    return []

                # Perform search
                documents = await source.search_documents(query)

                # Add source reliability to documents
                for doc in documents:
                    doc.confidence_score *= source.source_info.reliability_score

                return documents

            except Exception as e:
                logger.error(f"Error searching {source.source_info.source_id}: {str(e)}")
                raise

    async def _rank_and_deduplicate_documents(
        self, documents: list[CCNLDocument], query: DataSourceQuery
    ) -> list[DocumentRelevance]:
        """Rank and deduplicate documents based on relevance and quality."""
        # First pass: remove exact duplicates by content hash
        unique_docs = {}
        for doc in documents:
            if doc.content_hash not in unique_docs:
                unique_docs[doc.content_hash] = doc
            else:
                # Keep the one with higher confidence
                existing = unique_docs[doc.content_hash]
                if doc.confidence_score > existing.confidence_score:
                    unique_docs[doc.content_hash] = doc

        # Second pass: calculate relevance scores
        ranked_docs = []
        for doc in unique_docs.values():
            relevance = await self._calculate_document_relevance(doc, query)
            ranked_docs.append(relevance)

        # Third pass: remove near-duplicates by title similarity
        final_docs = await self._remove_near_duplicates(ranked_docs)

        # Sort by final score
        final_docs.sort(key=lambda x: x.final_score, reverse=True)

        return final_docs

    async def _calculate_document_relevance(self, document: CCNLDocument, query: DataSourceQuery) -> DocumentRelevance:
        """Calculate relevance score for a document."""
        # Base relevance from source confidence
        relevance_score = document.confidence_score

        # Sector relevance
        if query.sectors:
            if document.sector in query.sectors:
                relevance_score += 0.3
            else:
                relevance_score -= 0.1

        # Document type relevance
        if query.document_types:
            if document.document_type in query.document_types:
                relevance_score += 0.2

        # Keyword relevance
        if query.keywords:
            title_lower = document.title.lower()
            keyword_matches = sum(1 for keyword in query.keywords if keyword.lower() in title_lower)
            relevance_score += (keyword_matches / len(query.keywords)) * 0.3

        # Get source reliability
        source = self.registry.get_source(document.source_id)
        source_reliability = source.source_info.reliability_score if source else 0.5

        # Calculate freshness score (newer is better)
        days_old = (date.today() - document.publication_date).days
        if days_old <= 30:
            freshness_score = 1.0
        elif days_old <= 180:
            freshness_score = 0.8
        elif days_old <= 365:
            freshness_score = 0.6
        else:
            freshness_score = max(0.2, 1.0 - (days_old - 365) / 1825)  # Decay over 5 years

        # Calculate final score
        final_score = relevance_score * 0.4 + source_reliability * 0.3 + freshness_score * 0.3

        ranking_factors = {
            "relevance": relevance_score,
            "source_reliability": source_reliability,
            "freshness": freshness_score,
            "sector_match": 1.0 if query.sectors and document.sector in query.sectors else 0.0,
            "type_match": 1.0 if query.document_types and document.document_type in query.document_types else 0.0,
        }

        return DocumentRelevance(
            document=document,
            relevance_score=relevance_score,
            source_reliability=source_reliability,
            freshness_score=freshness_score,
            final_score=final_score,
            ranking_factors=ranking_factors,
        )

    async def _remove_near_duplicates(self, documents: list[DocumentRelevance]) -> list[DocumentRelevance]:
        """Remove near-duplicate documents based on title similarity."""

        def title_similarity(title1: str, title2: str) -> float:
            """Simple title similarity based on word overlap."""
            words1 = set(title1.lower().split())
            words2 = set(title2.lower().split())

            if not words1 or not words2:
                return 0.0

            intersection = words1.intersection(words2)
            union = words1.union(words2)

            return len(intersection) / len(union) if union else 0.0

        unique_docs = []

        for doc in documents:
            is_duplicate = False

            for existing in unique_docs:
                similarity = title_similarity(doc.document.title, existing.document.title)

                if similarity > 0.8:  # 80% similarity threshold
                    # Keep the one with higher score
                    if doc.final_score > existing.final_score:
                        unique_docs.remove(existing)
                        unique_docs.append(doc)
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_docs.append(doc)

        return unique_docs

    def _count_by_sector(self, documents: list[DocumentRelevance]) -> dict[CCNLSector, int]:
        """Count documents by sector."""
        counts = {}
        for doc_rel in documents:
            sector = doc_rel.document.sector
            counts[sector] = counts.get(sector, 0) + 1
        return counts

    def _count_by_type(self, documents: list[DocumentRelevance]) -> dict[str, int]:
        """Count documents by type."""
        counts = {}
        for doc_rel in documents:
            doc_type = doc_rel.document.document_type
            counts[doc_type] = counts.get(doc_type, 0) + 1
        return counts

    def _calculate_coverage_score(self, documents: list[DocumentRelevance], query: DataSourceQuery) -> float:
        """Calculate how well the search covered the query requirements."""
        if not documents:
            return 0.0

        score = 0.0
        factors = 0

        # Sector coverage
        if query.sectors:
            found_sectors = {doc.document.sector for doc in documents}
            sector_coverage = len(found_sectors) / len(query.sectors)
            score += sector_coverage
            factors += 1

        # Document type coverage
        if query.document_types:
            found_types = {doc.document.document_type for doc in documents}
            type_coverage = len(found_types) / len(query.document_types)
            score += type_coverage
            factors += 1

        # Date range coverage
        if query.date_from or query.date_to:
            date_scores = []
            for doc in documents:
                date_score = 1.0
                if (
                    query.date_from
                    and doc.document.publication_date < query.date_from
                    or query.date_to
                    and doc.document.publication_date > query.date_to
                ):
                    date_score = 0.0
                date_scores.append(date_score)

            if date_scores:
                score += sum(date_scores) / len(date_scores)
                factors += 1

        # Base coverage from having documents
        if documents:
            score += min(1.0, len(documents) / max(1, query.max_results))
            factors += 1

        return score / max(1, factors)

    async def _periodic_health_check(self):
        """Periodic health check of all data sources."""
        while True:
            try:
                logger.info("Starting periodic health check of data sources")

                health_status = await self.registry.get_source_health_status()

                inactive_count = sum(1 for status in health_status.values() if not status.get("connected", False))

                if inactive_count > 0:
                    logger.warning(f"{inactive_count} data sources are inactive")

                # Try to reconnect failed sources
                for source_id, status in health_status.items():
                    if not status.get("connected", False):
                        source = self.registry.get_source(source_id)
                        if source:
                            logger.info(f"Attempting to reconnect {source_id}")
                            await self._safe_connect(source)

                # Wait 30 minutes before next check
                await asyncio.sleep(30 * 60)

            except Exception as e:
                logger.error(f"Error in health check: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _periodic_data_refresh(self, source_type: DataSourceType, hours: int):
        """Periodic data refresh for a specific source type."""
        while True:
            try:
                logger.info(f"Starting data refresh for {source_type.value} sources")

                sources = self.registry.get_sources_by_type(source_type)

                # Get latest updates from each source
                for source in sources:
                    if source.source_info.status == DataSourceStatus.ACTIVE:
                        try:
                            since = datetime.utcnow() - timedelta(hours=hours * 2)
                            updates = await source.get_latest_updates(since)
                            logger.info(f"Got {len(updates)} updates from {source.source_info.source_id}")
                        except Exception as e:
                            logger.error(f"Error getting updates from {source.source_info.source_id}: {str(e)}")

                # Wait for the specified interval
                await asyncio.sleep(hours * 3600)

            except Exception as e:
                logger.error(f"Error in data refresh for {source_type.value}: {str(e)}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def get_sources_status(self) -> dict[str, Any]:
        """Get comprehensive status of all data sources."""
        if not self.initialized:
            await self.initialize()

        health_status = await self.registry.get_source_health_status()

        status_summary = {
            "total_sources": len(self.registry.sources),
            "active_sources": sum(1 for status in health_status.values() if status.get("connected", False)),
            "sources_by_type": {},
            "overall_reliability": 0.0,
            "sources_detail": health_status,
        }

        # Count by type and calculate average reliability
        total_reliability = 0.0
        for source in self.registry.sources.values():
            source_type = source.source_info.source_type.value
            if source_type not in status_summary["sources_by_type"]:
                status_summary["sources_by_type"][source_type] = 0
            status_summary["sources_by_type"][source_type] += 1
            total_reliability += source.source_info.reliability_score

        if self.registry.sources:
            status_summary["overall_reliability"] = total_reliability / len(self.registry.sources)

        return status_summary

    async def shutdown(self):
        """Shutdown the data sources manager."""
        logger.info("Shutting down CCNL data sources manager")

        # Cancel background tasks
        for task_name, task in self.update_tasks.items():
            if not task.done():
                logger.info(f"Cancelling {task_name} task")
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        # Disconnect all sources
        disconnect_tasks = []
        for source in self.registry.sources.values():
            task = asyncio.create_task(self._safe_disconnect(source))
            disconnect_tasks.append(task)

        await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        self.initialized = False
        logger.info("CCNL data sources manager shutdown complete")

    async def _safe_disconnect(self, source: BaseDataSource):
        """Safely disconnect from a data source."""
        try:
            await source.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting from {source.source_info.source_id}: {str(e)}")

    async def get_sector_associations(self) -> list[dict[str, Any]]:
        """Get information about all sector-specific associations."""
        sector_sources = []

        for source in self.registry.sources.values():
            if source.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION:
                status = await source.test_connection()
                sector_sources.append(
                    {
                        "source_id": source.source_info.source_id,
                        "name": source.source_info.name,
                        "organization": source.source_info.organization,
                        "base_url": source.source_info.base_url,
                        "supported_sectors": [sector.value for sector in source.source_info.supported_sectors],
                        "reliability_score": source.source_info.reliability_score,
                        "update_frequency": source.source_info.update_frequency.value,
                        "status": "active" if status else "inactive",
                        "last_updated": source.source_info.last_updated.isoformat()
                        if source.source_info.last_updated
                        else None,
                    }
                )

        return sector_sources

    async def search_sector_specific(
        self, sectors: list[CCNLSector], keywords: list[str] | None = None, max_results: int = 50
    ) -> dict[str, Any]:
        """Search specifically in sector associations for detailed industry information."""
        query = DataSourceQuery(sectors=sectors, keywords=keywords, max_results=max_results, include_content=True)

        # Search only sector association sources
        summary = await self.comprehensive_search(
            query=query,
            include_source_types=[DataSourceType.SECTOR_ASSOCIATION],
            exclude_unreliable=False,  # Include all sector sources for comprehensive coverage
            max_concurrent_sources=3,
        )

        return {
            "search_query": {
                "sectors": [sector.value for sector in sectors],
                "keywords": keywords,
                "max_results": max_results,
            },
            "results": {
                "total_documents": summary.total_documents,
                "documents_by_source": summary.documents_by_source,
                "documents_by_sector": {sector.value: count for sector, count in summary.documents_by_sector.items()},
                "coverage_score": summary.coverage_score,
                "search_duration": summary.search_duration,
            },
            "sector_associations_used": [
                source_id
                for source_id in summary.documents_by_source.keys()
                if any(
                    s.source_info.source_id == source_id
                    and s.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION
                    for s in self.registry.sources.values()
                )
            ],
            "errors": summary.errors,
        }

    async def get_sector_association_coverage(self) -> dict[CCNLSector, list[str]]:
        """Get mapping of sectors to their covering sector associations."""
        coverage = {}

        for source in self.registry.sources.values():
            if source.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION:
                for sector in source.source_info.supported_sectors:
                    if sector not in coverage:
                        coverage[sector] = []
                    coverage[sector].append(source.source_info.source_id)

        return coverage

    async def validate_sector_associations_connectivity(self) -> dict[str, Any]:
        """Validate connectivity and data quality of sector associations."""
        validation_results = {
            "tested_at": datetime.utcnow().isoformat(),
            "total_associations": 0,
            "active_associations": 0,
            "association_details": [],
            "coverage_gaps": [],
            "recommendations": [],
        }

        sector_sources = [
            source
            for source in self.registry.sources.values()
            if source.source_info.source_type == DataSourceType.SECTOR_ASSOCIATION
        ]

        validation_results["total_associations"] = len(sector_sources)

        for source in sector_sources:
            connection_ok = await source.test_connection()
            if connection_ok:
                validation_results["active_associations"] += 1

            # Test with a simple query
            test_query = DataSourceQuery(sectors=source.source_info.supported_sectors[:1], max_results=5)

            try:
                test_docs = await source.search_documents(test_query)
                data_quality = "good" if len(test_docs) > 0 else "limited"
            except Exception as e:
                data_quality = "error"
                logger.error(f"Error testing {source.source_info.source_id}: {e}")

            validation_results["association_details"].append(
                {
                    "source_id": source.source_info.source_id,
                    "name": source.source_info.name,
                    "connection_status": "ok" if connection_ok else "failed",
                    "data_quality": data_quality,
                    "supported_sectors": [s.value for s in source.source_info.supported_sectors],
                    "reliability_score": source.source_info.reliability_score,
                }
            )

        # Check for coverage gaps
        all_sectors = set(CCNLSector)
        covered_sectors = set()
        for source in sector_sources:
            covered_sectors.update(source.source_info.supported_sectors)

        uncovered_sectors = all_sectors - covered_sectors
        validation_results["coverage_gaps"] = [sector.value for sector in uncovered_sectors]

        # Generate recommendations
        if validation_results["active_associations"] < validation_results["total_associations"]:
            validation_results["recommendations"].append(
                "Some sector associations are not responding - check network connectivity and API endpoints"
            )

        if len(uncovered_sectors) > 10:
            validation_results["recommendations"].append(
                f"Consider adding sector associations for {len(uncovered_sectors)} uncovered sectors"
            )

        if validation_results["active_associations"] / max(1, validation_results["total_associations"]) < 0.8:
            validation_results["recommendations"].append(
                "Less than 80% of sector associations are active - review data source configurations"
            )

        return validation_results

    async def get_government_sources(self) -> list[dict[str, Any]]:
        """Get information about all government data sources."""
        government_sources = []

        for source in self.registry.sources.values():
            if source.source_info.source_type == DataSourceType.GOVERNMENT:
                status = await source.test_connection()
                government_sources.append(
                    {
                        "source_id": source.source_info.source_id,
                        "name": source.source_info.name,
                        "organization": source.source_info.organization,
                        "base_url": source.source_info.base_url,
                        "supported_sectors": [sector.value for sector in source.source_info.supported_sectors],
                        "reliability_score": source.source_info.reliability_score,
                        "update_frequency": source.source_info.update_frequency.value,
                        "status": "active" if status else "inactive",
                        "last_updated": source.source_info.last_updated.isoformat()
                        if source.source_info.last_updated
                        else None,
                        "priority": self.registry.source_priority.get(source.source_info.source_id, 0),
                    }
                )

        # Sort by priority (highest first)
        government_sources.sort(key=lambda x: x["priority"], reverse=True)
        return government_sources

    async def search_government_sources(
        self, sectors: list[CCNLSector] | None = None, keywords: list[str] | None = None, max_results: int = 50
    ) -> dict[str, Any]:
        """Search specifically within government sources for authoritative data."""
        query = DataSourceQuery(sectors=sectors, keywords=keywords, max_results=max_results, include_content=True)

        # Search only government sources
        summary = await self.comprehensive_search(
            query=query,
            include_source_types=[DataSourceType.GOVERNMENT],
            exclude_unreliable=False,  # Include all government sources
            max_concurrent_sources=3,
        )

        return {
            "search_query": {
                "sectors": [sector.value for sector in sectors] if sectors else [],
                "keywords": keywords,
                "max_results": max_results,
            },
            "results": {
                "total_documents": summary.total_documents,
                "documents_by_source": summary.documents_by_source,
                "documents_by_sector": {sector.value: count for sector, count in summary.documents_by_sector.items()},
                "coverage_score": summary.coverage_score,
                "search_duration": summary.search_duration,
            },
            "government_sources_used": [
                source_id
                for source_id in summary.documents_by_source.keys()
                if any(
                    s.source_info.source_id == source_id and s.source_info.source_type == DataSourceType.GOVERNMENT
                    for s in self.registry.sources.values()
                )
            ],
            "errors": summary.errors,
        }

    async def validate_government_sources_connectivity(self) -> dict[str, Any]:
        """Validate connectivity and data quality of government sources."""
        validation_results = {
            "tested_at": datetime.utcnow().isoformat(),
            "total_government_sources": 0,
            "active_government_sources": 0,
            "government_source_details": [],
            "reliability_assessment": {},
            "recommendations": [],
        }

        government_sources = [
            source
            for source in self.registry.sources.values()
            if source.source_info.source_type == DataSourceType.GOVERNMENT
        ]

        validation_results["total_government_sources"] = len(government_sources)

        for source in government_sources:
            connection_ok = await source.test_connection()
            if connection_ok:
                validation_results["active_government_sources"] += 1

            # Test with a simple query
            test_query = DataSourceQuery(
                sectors=source.source_info.supported_sectors[:3] if source.source_info.supported_sectors else [],
                max_results=3,
            )

            try:
                test_docs = await source.search_documents(test_query)
                data_quality = "excellent" if len(test_docs) > 0 else "limited"
            except Exception as e:
                data_quality = "error"
                logger.error(f"Error testing government source {source.source_info.source_id}: {e}")

            validation_results["government_source_details"].append(
                {
                    "source_id": source.source_info.source_id,
                    "name": source.source_info.name,
                    "connection_status": "ok" if connection_ok else "failed",
                    "data_quality": data_quality,
                    "reliability_score": source.source_info.reliability_score,
                    "update_frequency": source.source_info.update_frequency.value,
                    "priority": self.registry.source_priority.get(source.source_info.source_id, 0),
                }
            )

        # Calculate reliability assessment
        if government_sources:
            avg_reliability = sum(s.source_info.reliability_score for s in government_sources) / len(
                government_sources
            )
            active_ratio = (
                validation_results["active_government_sources"] / validation_results["total_government_sources"]
            )

            validation_results["reliability_assessment"] = {
                "average_reliability_score": avg_reliability,
                "active_sources_ratio": active_ratio,
                "overall_status": "excellent"
                if active_ratio > 0.8 and avg_reliability > 0.95
                else "good"
                if active_ratio > 0.6 and avg_reliability > 0.9
                else "needs_attention",
            }

        # Generate recommendations
        if validation_results["active_government_sources"] < validation_results["total_government_sources"]:
            validation_results["recommendations"].append(
                "Some government sources are not responding - verify network connectivity and endpoints"
            )

        if validation_results.get("reliability_assessment", {}).get("overall_status") == "needs_attention":
            validation_results["recommendations"].append(
                "Government sources reliability is below optimal - review configuration and connectivity"
            )

        if validation_results["total_government_sources"] < 3:
            validation_results["recommendations"].append(
                "Consider adding more government sources for comprehensive official data coverage"
            )

        return validation_results


# Global instance
ccnl_data_sources_manager = DataSourcesManager()
