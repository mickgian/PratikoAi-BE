# mypy: disable-error-code="arg-type,call-overload,misc,assignment"
"""Tests for DataQualityAuditService - DEV-258.

Unit tests for the DataQualitySummary dataclass and DataQualityAuditService class.
Tests cover summary defaults, DB result mapping, NULL handling, and threshold alerts.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.data_quality_audit_service import (
    DataQualityAuditService,
    DataQualitySummary,
)
from app.services.ingestion_report_service import AlertSeverity, AlertType


class TestDataQualitySummary:
    """Tests for DataQualitySummary dataclass."""

    def test_summary_default_values(self):
        """Test that DataQualitySummary defaults all fields to 0/empty."""
        summary = DataQualitySummary()

        assert summary.total_items == 0
        assert summary.total_chunks == 0
        assert summary.url_duplicate_groups == 0
        assert summary.title_duplicate_groups == 0
        assert summary.navigation_contaminated_chunks == 0
        assert summary.html_artifact_items == 0
        assert summary.rss_fallback_docs == 0
        assert summary.broken_hyphenation_chunks == 0
        assert summary.chunk_stats == {}
        assert summary.junk_chunks_stored == 0
        assert summary.low_quality_chunks == 0
        assert summary.null_quality_chunks == 0
        assert summary.items_missing_embedding == 0
        assert summary.chunks_missing_embedding == 0
        assert summary.status_distribution == {}
        assert summary.old_active_documents == 0
        assert summary.no_publication_date == 0
        assert summary.null_text_quality == 0
        assert summary.nfd_unicode_chunks == 0


@pytest.mark.asyncio
class TestDataQualityAuditServiceRunSummary:
    """Tests for DataQualityAuditService.run_summary()."""

    @pytest.fixture
    def mock_db(self):
        """Create mock async database session with chained scalar responses."""
        mock = MagicMock()
        mock.execute = AsyncMock()
        return mock

    async def test_run_summary_returns_counts(self, mock_db):
        """Test that run_summary maps DB results to correct fields."""
        # Build a sequence of mock results for each query in order.
        # The service executes ~15 queries; we mock scalar() for COUNT queries
        # and fetchall()/fetchone() for grouped queries.

        call_index = 0
        scalar_values = [
            150,  # total_items
            800,  # total_chunks
            3,  # url_duplicate_groups
            5,  # title_duplicate_groups
            12,  # navigation_contaminated_chunks
            2,  # html_artifact_items (items with HTML tags)
            4,  # rss_fallback_docs
            7,  # broken_hyphenation_chunks
            # chunk_stats is fetchone(), handled separately
            10,  # junk_chunks_stored
            15,  # low_quality_chunks
            20,  # null_quality_chunks
            # status_distribution is fetchall(), handled separately
            1,  # items_missing_embedding
            3,  # chunks_missing_embedding
            8,  # old_active_documents
            25,  # no_publication_date
            30,  # null_text_quality
            6,  # nfd_unicode_chunks
        ]

        # Mock for chunk_stats fetchone (min, max, avg, median, p95)
        chunk_stats_row = MagicMock()
        chunk_stats_row.__getitem__ = lambda self, i: [10, 900, 350, 300, 750][i]

        # Mock for status_distribution fetchall
        status_rows = [
            MagicMock(**{"__getitem__": lambda self, i, vals=("active", 120): vals[i]}),
            MagicMock(**{"__getitem__": lambda self, i, vals=("superseded", 30): vals[i]}),
        ]

        async def mock_execute(query, params=None):
            nonlocal call_index
            result = MagicMock()

            # Determine which query this is by call order
            idx = call_index
            call_index += 1

            # Queries 0-7: scalar COUNT queries (total_items through broken_hyphenation)
            # Query 8: chunk_stats fetchone
            # Queries 9-11: scalar COUNT queries (junk, low_quality, null_quality)
            # Query 12: status_distribution fetchall
            # Queries 13-18: scalar COUNT queries (remaining)

            if idx == 8:
                # chunk_stats
                result.fetchone.return_value = chunk_stats_row
                result.scalar.return_value = None
            elif idx == 12:
                # status_distribution
                result.fetchall.return_value = status_rows
                result.scalar.return_value = None
            else:
                # Map to the right scalar value
                if idx < 8:
                    scalar_idx = idx
                elif idx < 12:
                    scalar_idx = idx - 1  # skip chunk_stats
                else:
                    scalar_idx = idx - 2  # skip chunk_stats and status_distribution
                result.scalar.return_value = scalar_values[scalar_idx] if scalar_idx < len(scalar_values) else 0
                result.fetchone.return_value = None
                result.fetchall.return_value = []

            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        service = DataQualityAuditService(mock_db)
        summary = await service.run_summary()

        assert summary.total_items == 150
        assert summary.total_chunks == 800
        assert summary.url_duplicate_groups == 3
        assert summary.title_duplicate_groups == 5
        assert summary.navigation_contaminated_chunks == 12
        assert summary.rss_fallback_docs == 4
        assert summary.broken_hyphenation_chunks == 7
        assert summary.junk_chunks_stored == 10
        assert summary.low_quality_chunks == 15
        assert summary.null_quality_chunks == 20
        assert summary.items_missing_embedding == 1
        assert summary.chunks_missing_embedding == 3
        assert summary.old_active_documents == 8
        assert summary.no_publication_date == 25
        assert summary.null_text_quality == 30
        assert summary.nfd_unicode_chunks == 6

    async def test_run_summary_handles_null_results(self, mock_db):
        """Test that DB returning NULL defaults to 0."""
        # All queries return NULL/None
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_result.fetchone.return_value = None
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = DataQualityAuditService(mock_db)
        summary = await service.run_summary()

        assert summary.total_items == 0
        assert summary.total_chunks == 0
        assert summary.url_duplicate_groups == 0
        assert summary.items_missing_embedding == 0
        assert summary.chunks_missing_embedding == 0
        assert summary.chunk_stats == {}
        assert summary.status_distribution == {}


class TestDataQualityThresholds:
    """Tests for DataQualityAuditService.check_thresholds()."""

    def test_threshold_clean_no_alerts(self):
        """Test that all-zero summary produces no alerts."""
        summary = DataQualitySummary()
        alerts = DataQualityAuditService.check_thresholds(summary)

        assert alerts == []

    def test_threshold_duplicates_alert(self):
        """Test that url_duplicate_groups > 0 triggers DQ_DUPLICATES alert."""
        summary = DataQualitySummary(url_duplicate_groups=1)
        alerts = DataQualityAuditService.check_thresholds(summary)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DQ_DUPLICATES
        assert alerts[0].severity == AlertSeverity.MEDIUM

    def test_threshold_nav_contamination_alert(self):
        """Test that navigation contamination > 10 triggers alert."""
        summary = DataQualitySummary(navigation_contaminated_chunks=15)
        alerts = DataQualityAuditService.check_thresholds(summary)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DQ_NAV_CONTAMINATION
        assert alerts[0].severity == AlertSeverity.HIGH

    def test_threshold_nav_contamination_below_threshold(self):
        """Test that navigation contamination <= 10 does NOT trigger alert."""
        summary = DataQualitySummary(navigation_contaminated_chunks=10)
        alerts = DataQualityAuditService.check_thresholds(summary)

        assert all(a.alert_type != AlertType.DQ_NAV_CONTAMINATION for a in alerts)

    def test_threshold_missing_embeddings_alert(self):
        """Test that missing embeddings triggers alert."""
        summary = DataQualitySummary(chunks_missing_embedding=5)
        alerts = DataQualityAuditService.check_thresholds(summary)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DQ_MISSING_EMBEDDINGS
        assert alerts[0].severity == AlertSeverity.HIGH

    def test_threshold_missing_embeddings_items(self):
        """Test that missing item embeddings also triggers alert."""
        summary = DataQualitySummary(items_missing_embedding=2)
        alerts = DataQualityAuditService.check_thresholds(summary)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DQ_MISSING_EMBEDDINGS

    def test_threshold_low_quality_alert(self):
        """Test that low quality ratio > 5% triggers alert."""
        summary = DataQualitySummary(total_chunks=100, low_quality_chunks=6)
        alerts = DataQualityAuditService.check_thresholds(summary)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DQ_LOW_QUALITY
        assert alerts[0].severity == AlertSeverity.MEDIUM

    def test_threshold_low_quality_below_threshold(self):
        """Test that low quality ratio <= 5% does NOT trigger alert."""
        summary = DataQualitySummary(total_chunks=100, low_quality_chunks=5)
        alerts = DataQualityAuditService.check_thresholds(summary)

        assert all(a.alert_type != AlertType.DQ_LOW_QUALITY for a in alerts)

    def test_threshold_multiple_alerts(self):
        """Test that multiple breached thresholds produce multiple alerts."""
        summary = DataQualitySummary(
            total_chunks=100,
            url_duplicate_groups=2,
            navigation_contaminated_chunks=20,
            chunks_missing_embedding=10,
            low_quality_chunks=10,
        )
        alerts = DataQualityAuditService.check_thresholds(summary)

        alert_types = {a.alert_type for a in alerts}
        assert AlertType.DQ_DUPLICATES in alert_types
        assert AlertType.DQ_NAV_CONTAMINATION in alert_types
        assert AlertType.DQ_MISSING_EMBEDDINGS in alert_types
        assert AlertType.DQ_LOW_QUALITY in alert_types
        assert len(alerts) == 4
