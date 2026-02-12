# mypy: disable-error-code="arg-type,call-overload,misc,assignment"
"""Data Quality Audit Service for DEV-258.

Runs lightweight COUNT queries against the knowledge base to produce a
DataQualitySummary.  Used by:
  - IngestionReportService (daily email)
  - scripts/audit_data_quality.py (CLI)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text.clean import NAVIGATION_PATTERNS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DataQualitySummary:
    """Aggregated data-quality metrics (all counts)."""

    total_items: int = 0
    total_chunks: int = 0

    # Duplicates
    url_duplicate_groups: int = 0
    title_duplicate_groups: int = 0

    # Content quality
    navigation_contaminated_chunks: int = 0
    html_artifact_items: int = 0
    rss_fallback_docs: int = 0
    broken_hyphenation_chunks: int = 0

    # Chunk size distribution
    chunk_stats: dict = field(default_factory=dict)

    # Quality scores
    junk_chunks_stored: int = 0
    low_quality_chunks: int = 0
    null_quality_chunks: int = 0

    # Embeddings
    items_missing_embedding: int = 0
    chunks_missing_embedding: int = 0

    # Staleness
    status_distribution: dict = field(default_factory=dict)
    old_active_documents: int = 0
    no_publication_date: int = 0
    null_text_quality: int = 0

    # Unicode
    nfd_unicode_chunks: int = 0


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------


def _build_navigation_contamination_sql() -> str:
    """Build SQL that mirrors ``chunk_contains_navigation()`` logic.

    A chunk is contaminated when it matches >= 2 patterns,
    **or** 1 pattern and has < 300 characters.
    """
    nav_patterns = list(NAVIGATION_PATTERNS)

    like_conditions = [f"LOWER(chunk_text) LIKE '%{p}%'" for p in nav_patterns]
    count_expr = " + ".join(f"CASE WHEN {c} THEN 1 ELSE 0 END" for c in like_conditions)
    any_condition = " OR ".join(like_conditions)

    return (
        f"SELECT COUNT(*) FROM knowledge_chunks "
        f"WHERE ({any_condition}) "
        f"AND (({count_expr}) >= 2 "
        f"OR (({count_expr}) >= 1 AND LENGTH(chunk_text) < 300))"
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DataQualityAuditService:
    """Runs fast COUNT queries and returns a :class:`DataQualitySummary`."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_summary(self) -> DataQualitySummary:
        """Execute all diagnostic counts and return a summary."""
        s = DataQualitySummary()

        # 1. Overview
        s.total_items = await self._scalar("SELECT COUNT(*) FROM knowledge_items")
        s.total_chunks = await self._scalar("SELECT COUNT(*) FROM knowledge_chunks")

        # 2. Duplicates
        s.url_duplicate_groups = await self._scalar(
            "SELECT COUNT(*) FROM ("
            "  SELECT source_url FROM knowledge_items"
            "  WHERE source_url IS NOT NULL"
            "  GROUP BY source_url HAVING COUNT(*) > 1"
            ") sub"
        )
        s.title_duplicate_groups = await self._scalar(
            "SELECT COUNT(*) FROM ("
            "  SELECT title FROM knowledge_items"
            "  WHERE title IS NOT NULL AND title != ''"
            "  GROUP BY title HAVING COUNT(*) > 1"
            ") sub"
        )

        # 3. Navigation contamination
        s.navigation_contaminated_chunks = await self._scalar(_build_navigation_contamination_sql())

        # 4. HTML artifacts
        s.html_artifact_items = await self._scalar(
            "SELECT COUNT(*) FROM knowledge_items "
            "WHERE content LIKE '%<p>%' OR content LIKE '%<strong>%' "
            "OR content LIKE '%<a %' OR content LIKE '%&amp;%'"
        )
        s.rss_fallback_docs = await self._scalar(
            "SELECT COUNT(*) FROM knowledge_items WHERE extraction_method = 'rss_summary_fallback'"
        )

        # 5. Broken hyphenation
        s.broken_hyphenation_chunks = await self._scalar(
            "SELECT COUNT(*) FROM knowledge_chunks WHERE chunk_text ~ '[a-zàèéìòù]- [a-zàèéìòù]'"
        )

        # 6. Chunk size distribution
        row = await self._fetchone(
            "SELECT "
            "  MIN(token_count), MAX(token_count), "
            "  AVG(token_count)::int, "
            "  percentile_cont(0.5) WITHIN GROUP (ORDER BY token_count)::int, "
            "  percentile_cont(0.95) WITHIN GROUP (ORDER BY token_count)::int "
            "FROM knowledge_chunks"
        )
        if row:
            s.chunk_stats = {
                "min": row[0],
                "max": row[1],
                "avg": row[2],
                "median": row[3],
                "p95": row[4],
            }

        # 7. Quality scores
        s.junk_chunks_stored = await self._scalar("SELECT COUNT(*) FROM knowledge_chunks WHERE junk = TRUE")
        s.low_quality_chunks = await self._scalar(
            "SELECT COUNT(*) FROM knowledge_chunks WHERE quality_score IS NOT NULL AND quality_score < 0.5"
        )
        s.null_quality_chunks = await self._scalar("SELECT COUNT(*) FROM knowledge_chunks WHERE quality_score IS NULL")

        # 8. Status distribution
        rows = await self._fetchall(
            "SELECT status, COUNT(*) FROM knowledge_items GROUP BY status ORDER BY COUNT(*) DESC"
        )
        s.status_distribution = {row[0] or "NULL": row[1] for row in rows}

        # 9. Missing embeddings
        s.items_missing_embedding = await self._scalar("SELECT COUNT(*) FROM knowledge_items WHERE embedding IS NULL")
        s.chunks_missing_embedding = await self._scalar(
            "SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NULL"
        )

        # 10. Staleness
        s.old_active_documents = await self._scalar(
            "SELECT COUNT(*) FROM knowledge_items WHERE status = 'active' AND created_at < NOW() - INTERVAL '365 days'"
        )
        s.no_publication_date = await self._scalar(
            "SELECT COUNT(*) FROM knowledge_items WHERE publication_date IS NULL"
        )
        s.null_text_quality = await self._scalar("SELECT COUNT(*) FROM knowledge_items WHERE text_quality IS NULL")

        # 11. Unicode normalization
        s.nfd_unicode_chunks = await self._scalar(
            r"SELECT COUNT(*) FROM knowledge_chunks " r"WHERE chunk_text ~ E'[\u0300-\u036f]'"
        )

        return s

    # ------------------------------------------------------------------
    # Threshold checks
    # ------------------------------------------------------------------

    @staticmethod
    def check_thresholds(summary: DataQualitySummary) -> list:
        """Compare summary metrics against thresholds and return alerts.

        Returns a list of ``IngestionAlert`` objects.  Import is deferred to
        avoid circular dependency at module level.
        """
        from app.services.ingestion_report_service import (
            AlertSeverity,
            AlertType,
            IngestionAlert,
        )

        alerts: list[IngestionAlert] = []

        # DQ_DUPLICATES: any URL-based duplicate groups
        if summary.url_duplicate_groups > 0:
            alerts.append(
                IngestionAlert(
                    alert_type=AlertType.DQ_DUPLICATES,
                    severity=AlertSeverity.MEDIUM,
                    message=(f"{summary.url_duplicate_groups} duplicate URL group(s) detected"),
                )
            )

        # DQ_NAV_CONTAMINATION: more than 10 contaminated chunks
        if summary.navigation_contaminated_chunks > 10:
            alerts.append(
                IngestionAlert(
                    alert_type=AlertType.DQ_NAV_CONTAMINATION,
                    severity=AlertSeverity.HIGH,
                    message=(f"{summary.navigation_contaminated_chunks} chunks contain navigation boilerplate"),
                )
            )

        # DQ_MISSING_EMBEDDINGS: any items or chunks without embeddings
        if summary.items_missing_embedding > 0 or summary.chunks_missing_embedding > 0:
            total_missing = summary.items_missing_embedding + summary.chunks_missing_embedding
            alerts.append(
                IngestionAlert(
                    alert_type=AlertType.DQ_MISSING_EMBEDDINGS,
                    severity=AlertSeverity.HIGH,
                    message=(
                        f"{total_missing} item(s)/chunk(s) missing embeddings "
                        f"({summary.items_missing_embedding} items, "
                        f"{summary.chunks_missing_embedding} chunks)"
                    ),
                )
            )

        # DQ_LOW_QUALITY: > 5% of chunks are low quality
        if summary.total_chunks > 0:
            ratio = summary.low_quality_chunks / summary.total_chunks
            if ratio > 0.05:
                alerts.append(
                    IngestionAlert(
                        alert_type=AlertType.DQ_LOW_QUALITY,
                        severity=AlertSeverity.MEDIUM,
                        message=(
                            f"{summary.low_quality_chunks}/{summary.total_chunks} chunks "
                            f"({ratio:.1%}) have quality_score < 0.5"
                        ),
                    )
                )

        return alerts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _scalar(self, sql: str) -> int:
        """Execute a COUNT query and return the integer result (0 on NULL)."""
        result = await self.db.execute(text(sql))
        return result.scalar() or 0

    async def _fetchone(self, sql: str):
        """Execute a query and return the first row (or None)."""
        result = await self.db.execute(text(sql))
        return result.fetchone()

    async def _fetchall(self, sql: str) -> list:
        """Execute a query and return all rows."""
        result = await self.db.execute(text(sql))
        return result.fetchall()
