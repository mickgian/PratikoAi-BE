"""Tests for CCNL update models."""

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.ccnl_update_models import (
    CCNLChangeLog,
    CCNLDatabase,
    CCNLMonitoringMetric,
    CCNLUpdateEvent,
    CCNLVersion,
    ChangeType,
    UpdateSource,
    UpdateStatus,
)


class TestUpdateSource:
    """Test UpdateSource enum."""

    def test_update_source_values(self):
        """Test that update sources have correct values."""
        assert UpdateSource.CGIL_RSS.value == "cgil_rss"
        assert UpdateSource.CISL_RSS.value == "cisl_rss"
        assert UpdateSource.UIL_RSS.value == "uil_rss"
        assert UpdateSource.UGL_RSS.value == "ugl_rss"
        assert UpdateSource.CONFINDUSTRIA_NEWS.value == "confindustria_news"
        assert UpdateSource.CONFCOMMERCIO_NEWS.value == "confcommercio_news"
        assert UpdateSource.CONFARTIGIANATO_NEWS.value == "confartigianato_news"
        assert UpdateSource.CONFAPI_NEWS.value == "confapi_news"
        assert UpdateSource.CNEL_OFFICIAL.value == "cnel_official"
        assert UpdateSource.MINISTRY_LABOR.value == "ministry_labor"
        assert UpdateSource.MANUAL_ENTRY.value == "manual_entry"

    def test_update_source_enum_members(self):
        """Test that all expected update sources exist."""
        expected = {
            "CGIL_RSS",
            "CISL_RSS",
            "UIL_RSS",
            "UGL_RSS",
            "CONFINDUSTRIA_NEWS",
            "CONFCOMMERCIO_NEWS",
            "CONFARTIGIANATO_NEWS",
            "CONFAPI_NEWS",
            "CNEL_OFFICIAL",
            "MINISTRY_LABOR",
            "MANUAL_ENTRY",
        }
        actual = {member.name for member in UpdateSource}
        assert actual == expected


class TestUpdateStatus:
    """Test UpdateStatus enum."""

    def test_update_status_values(self):
        """Test that update statuses have correct values."""
        assert UpdateStatus.DETECTED.value == "detected"
        assert UpdateStatus.PROCESSING.value == "processing"
        assert UpdateStatus.VERIFIED.value == "verified"
        assert UpdateStatus.INTEGRATED.value == "integrated"
        assert UpdateStatus.FAILED.value == "failed"
        assert UpdateStatus.DISMISSED.value == "dismissed"

    def test_update_status_enum_members(self):
        """Test that all expected update statuses exist."""
        expected = {"DETECTED", "PROCESSING", "VERIFIED", "INTEGRATED", "FAILED", "DISMISSED"}
        actual = {member.name for member in UpdateStatus}
        assert actual == expected


class TestChangeType:
    """Test ChangeType enum."""

    def test_change_type_values(self):
        """Test that change types have correct values."""
        assert ChangeType.RENEWAL.value == "renewal"
        assert ChangeType.AMENDMENT.value == "amendment"
        assert ChangeType.SALARY_UPDATE.value == "salary_update"
        assert ChangeType.NEW_AGREEMENT.value == "new_agreement"
        assert ChangeType.CORRECTION.value == "correction"
        assert ChangeType.TEMPORARY.value == "temporary"

    def test_change_type_enum_members(self):
        """Test that all expected change types exist."""
        expected = {"RENEWAL", "AMENDMENT", "SALARY_UPDATE", "NEW_AGREEMENT", "CORRECTION", "TEMPORARY"}
        actual = {member.name for member in ChangeType}
        assert actual == expected


class TestCCNLDatabase:
    """Test CCNLDatabase model."""

    def test_create_ccnl_database_minimal(self):
        """Test creating CCNL database entry with required fields."""
        ccnl = CCNLDatabase(
            sector_name="Metalmeccanici",
            ccnl_code="MET2025",
            official_name="CCNL Metalmeccanici Industria 2025",
        )

        assert ccnl.sector_name == "Metalmeccanici"
        assert ccnl.ccnl_code == "MET2025"
        assert ccnl.official_name == "CCNL Metalmeccanici Industria 2025"
        assert ccnl.id is None  # Not set until persisted
        assert ccnl.current_version_id is None
        # is_active default is set at DB level, not on object creation
        assert ccnl.is_active is None or ccnl.is_active is True

    def test_ccnl_database_with_version(self):
        """Test CCNL database with current version."""
        version_id = uuid.uuid4()

        ccnl = CCNLDatabase(
            sector_name="Commercio",
            ccnl_code="COM2025",
            official_name="CCNL Commercio e Terziario 2025",
            current_version_id=version_id,
        )

        assert ccnl.current_version_id == version_id

    def test_ccnl_database_inactive(self):
        """Test creating inactive CCNL database entry."""
        ccnl = CCNLDatabase(
            sector_name="Edilizia",
            ccnl_code="EDI2024",
            official_name="CCNL Edilizia 2024",
            is_active=False,
        )

        assert ccnl.is_active is False


class TestCCNLVersion:
    """Test CCNLVersion model."""

    def test_create_version_minimal(self):
        """Test creating CCNL version with required fields."""
        ccnl_id = uuid.uuid4()
        effective_date = date(2025, 1, 1)

        version = CCNLVersion(
            ccnl_id=ccnl_id,
            version_number="1.0",
            effective_date=effective_date,
        )

        assert version.ccnl_id == ccnl_id
        assert version.version_number == "1.0"
        assert version.effective_date == effective_date
        assert version.expiry_date is None
        assert version.signed_date is None
        # is_current default is set at DB level, not on object creation
        assert version.is_current is None or version.is_current is False

    def test_create_version_with_dates(self):
        """Test creating version with all dates."""
        ccnl_id = uuid.uuid4()
        signed_date = date(2024, 12, 15)
        effective_date = date(2025, 1, 1)
        expiry_date = date(2027, 12, 31)

        version = CCNLVersion(
            ccnl_id=ccnl_id,
            version_number="2.0",
            effective_date=effective_date,
            expiry_date=expiry_date,
            signed_date=signed_date,
            is_current=True,
        )

        assert version.signed_date == signed_date
        assert version.effective_date == effective_date
        assert version.expiry_date == expiry_date
        assert version.is_current is True

    def test_version_with_salary_data(self):
        """Test version with salary data."""
        ccnl_id = uuid.uuid4()
        salary_data = {
            "level_1": {"min": 1200, "max": 1500},
            "level_2": {"min": 1500, "max": 1800},
        }

        version = CCNLVersion(
            ccnl_id=ccnl_id,
            version_number="1.0",
            effective_date=date(2025, 1, 1),
            salary_data=salary_data,
        )

        assert version.salary_data == salary_data
        assert "level_1" in version.salary_data

    def test_version_with_working_conditions(self):
        """Test version with working conditions."""
        ccnl_id = uuid.uuid4()
        working_conditions = {
            "weekly_hours": 40,
            "overtime_rate": 1.25,
            "night_shift_bonus": 0.15,
        }

        version = CCNLVersion(
            ccnl_id=ccnl_id,
            version_number="1.0",
            effective_date=date(2025, 1, 1),
            working_conditions=working_conditions,
        )

        assert version.working_conditions == working_conditions


class TestCCNLUpdateEvent:
    """Test CCNLUpdateEvent model."""

    def test_create_update_event_minimal(self):
        """Test creating update event with required fields."""
        ccnl_id = uuid.uuid4()

        event = CCNLUpdateEvent(
            ccnl_id=ccnl_id,
            source="cgil_rss",
            title="Nuovo CCNL Metalmeccanici",
            classification_confidence=Decimal("0.95"),
            status="detected",
        )

        assert event.ccnl_id == ccnl_id
        assert event.source == "cgil_rss"
        assert event.title == "Nuovo CCNL Metalmeccanici"
        assert event.classification_confidence == Decimal("0.95")
        assert event.status == "detected"
        assert event.url is None
        assert event.content_summary is None

    def test_update_event_with_url(self):
        """Test update event with URL and content."""
        ccnl_id = uuid.uuid4()

        event = CCNLUpdateEvent(
            ccnl_id=ccnl_id,
            source="ministry_labor",
            title="Aggiornamento retribuzioni CCNL Commercio",
            url="https://lavoro.gov.it/ccnl/commercio-2025",
            content_summary="Aumento retribuzioni del 3.5% per tutti i livelli",
            classification_confidence=Decimal("0.88"),
            status="verified",
        )

        assert event.url == "https://lavoro.gov.it/ccnl/commercio-2025"
        assert event.content_summary is not None
        assert event.status == "verified"

    def test_update_event_processing(self):
        """Test update event in processing status."""
        ccnl_id = uuid.uuid4()
        processed_at = datetime(2025, 1, 15, 10, 30)

        event = CCNLUpdateEvent(
            ccnl_id=ccnl_id,
            source="cnel_official",
            title="CCNL Update",
            classification_confidence=Decimal("0.92"),
            status="processing",
            processed_at=processed_at,
        )

        assert event.status == "processing"
        assert event.processed_at == processed_at

    def test_update_event_failed(self):
        """Test failed update event."""
        ccnl_id = uuid.uuid4()

        event = CCNLUpdateEvent(
            ccnl_id=ccnl_id,
            source="manual_entry",
            title="Failed Update",
            classification_confidence=Decimal("0.45"),
            status="failed",
            error_message="Validation failed: incomplete data",
        )

        assert event.status == "failed"
        assert event.error_message is not None


class TestCCNLChangeLog:
    """Test CCNLChangeLog model."""

    def test_create_change_log_minimal(self):
        """Test creating change log with required fields."""
        ccnl_id = uuid.uuid4()
        new_version_id = uuid.uuid4()

        change_log = CCNLChangeLog(
            ccnl_id=ccnl_id,
            new_version_id=new_version_id,
            change_type="salary_update",
            changes_summary="Aumento retribuzioni 3.5%",
            detailed_changes={"salary_increase": "3.5%"},
            significance_score=Decimal("0.85"),
        )

        assert change_log.ccnl_id == ccnl_id
        assert change_log.new_version_id == new_version_id
        assert change_log.old_version_id is None
        assert change_log.change_type == "salary_update"
        assert change_log.significance_score == Decimal("0.85")

    def test_change_log_with_old_version(self):
        """Test change log comparing two versions."""
        ccnl_id = uuid.uuid4()
        old_version_id = uuid.uuid4()
        new_version_id = uuid.uuid4()

        change_log = CCNLChangeLog(
            ccnl_id=ccnl_id,
            old_version_id=old_version_id,
            new_version_id=new_version_id,
            change_type="renewal",
            changes_summary="Rinnovo contratto triennale",
            detailed_changes={"duration": "3 years", "changes": ["salary", "conditions"]},
            significance_score=Decimal("0.95"),
        )

        assert change_log.old_version_id == old_version_id
        assert change_log.new_version_id == new_version_id
        assert change_log.change_type == "renewal"

    def test_change_log_with_creator(self):
        """Test change log with creator information."""
        ccnl_id = uuid.uuid4()
        new_version_id = uuid.uuid4()

        change_log = CCNLChangeLog(
            ccnl_id=ccnl_id,
            new_version_id=new_version_id,
            change_type="amendment",
            changes_summary="Correzione normativa",
            detailed_changes={"section": "article_5", "correction": "typo fix"},
            significance_score=Decimal("0.25"),
            created_by="admin@example.com",
        )

        assert change_log.created_by == "admin@example.com"
        assert change_log.significance_score == Decimal("0.25")


class TestCCNLMonitoringMetric:
    """Test CCNLMonitoringMetric model."""

    def test_create_monitoring_metric_minimal(self):
        """Test creating monitoring metric with required fields."""
        metric = CCNLMonitoringMetric(
            metric_type="update_frequency",
            metric_name="updates_per_day",
            value=Decimal("5.2"),
        )

        assert metric.metric_type == "update_frequency"
        assert metric.metric_name == "updates_per_day"
        assert metric.value == Decimal("5.2")
        assert metric.unit is None
        assert metric.source is None

    def test_monitoring_metric_with_unit(self):
        """Test monitoring metric with unit."""
        metric = CCNLMonitoringMetric(
            metric_type="performance",
            metric_name="processing_time",
            value=Decimal("123.45"),
            unit="milliseconds",
        )

        assert metric.value == Decimal("123.45")
        assert metric.unit == "milliseconds"

    def test_monitoring_metric_with_source(self):
        """Test monitoring metric with source."""
        metric = CCNLMonitoringMetric(
            metric_type="data_quality",
            metric_name="classification_accuracy",
            value=Decimal("0.9234"),
            unit="percentage",
            source="cgil_rss",
        )

        assert metric.source == "cgil_rss"
        assert metric.value == Decimal("0.9234")

    def test_monitoring_metric_with_metadata(self):
        """Test monitoring metric with metadata."""
        metadata = {
            "sample_size": 1000,
            "period": "last_30_days",
            "algorithm_version": "2.1",
        }

        metric = CCNLMonitoringMetric(
            metric_type="algorithm_performance",
            metric_name="detection_rate",
            value=Decimal("0.876"),
            metric_metadata=metadata,
        )

        assert metric.metric_metadata == metadata
        assert "sample_size" in metric.metric_metadata

    def test_monitoring_metric_timestamp(self):
        """Test monitoring metric with timestamp."""
        timestamp = datetime(2025, 1, 15, 14, 30, 0)

        metric = CCNLMonitoringMetric(
            metric_type="system_health",
            metric_name="uptime",
            value=Decimal("99.95"),
            unit="percentage",
            timestamp=timestamp,
        )

        assert metric.timestamp == timestamp
