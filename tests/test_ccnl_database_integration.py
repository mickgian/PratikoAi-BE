"""
Test suite for CCNL Database Integration with Automatic Updates.

This test suite follows TDD methodology to implement a comprehensive CCNL database
system with automatic update monitoring, version control, and change detection.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from app.models.ccnl_update_models import (
    CCNLChangeLog,
    CCNLDatabase,
    CCNLUpdateEvent,
    CCNLVersion,
    ChangeType,
    UpdateSource,
    UpdateStatus,
)
from app.services.ccnl_rss_monitor import CCNLUpdateDetector, RSSFeedMonitor, UpdateClassifier
from app.services.ccnl_update_processor import CCNLUpdateProcessor
from app.services.ccnl_version_manager import CCNLVersionManager


class TestCCNLDatabaseModels:
    """Test CCNL database models and versioning."""

    def test_ccnl_database_model_creation(self):
        """Test creating a CCNL database entry."""
        ccnl_db = CCNLDatabase(
            id=uuid4(),
            sector_name="Metalmeccanici Industria",
            ccnl_code="MM_IND_2024",
            official_name="CCNL per i dipendenti delle aziende industriali metalmeccaniche",
            current_version_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        assert ccnl_db.sector_name == "Metalmeccanici Industria"
        assert ccnl_db.ccnl_code == "MM_IND_2024"
        assert ccnl_db.is_active is True
        assert ccnl_db.current_version_id is None

    def test_ccnl_version_model_creation(self):
        """Test creating a CCNL version entry."""
        version = CCNLVersion(
            id=uuid4(),
            ccnl_id=uuid4(),
            version_number="2024.1",
            effective_date=date(2024, 1, 1),
            expiry_date=date(2026, 12, 31),
            signed_date=date(2023, 12, 15),
            document_url="https://example.com/ccnl_mm_2024.pdf",
            salary_data={"minimum_wages": {"level_1": 1500, "level_2": 1700}},
            working_conditions={"weekly_hours": 40, "overtime_rate": 1.5},
            leave_provisions={"annual_leave": 26, "sick_leave": 180},
            created_at=datetime.utcnow(),
            is_current=True,
        )

        assert version.version_number == "2024.1"
        assert version.effective_date == date(2024, 1, 1)
        assert version.is_current is True
        assert "minimum_wages" in version.salary_data

    def test_ccnl_update_event_model(self):
        """Test CCNL update event tracking."""
        update_event = CCNLUpdateEvent(
            id=uuid4(),
            ccnl_id=uuid4(),
            source=UpdateSource.CGIL_RSS,
            detected_at=datetime.utcnow(),
            title="Rinnovo CCNL Metalmeccanici 2024",
            url="https://cgil.it/news/rinnovo-ccnl-metalmeccanici",
            content_summary="Accordo raggiunto per rinnovo triennale",
            classification_confidence=0.95,
            status=UpdateStatus.DETECTED,
            processed_at=None,
            error_message=None,
        )

        assert update_event.source == UpdateSource.CGIL_RSS
        assert update_event.status == UpdateStatus.DETECTED
        assert update_event.classification_confidence == 0.95
        assert update_event.processed_at is None


class TestRSSFeedMonitoring:
    """Test RSS feed monitoring for CCNL updates."""

    @pytest.fixture
    def rss_monitor(self):
        """Create RSS feed monitor instance."""
        return RSSFeedMonitor()

    @pytest.fixture
    def sample_rss_feeds(self):
        """Sample RSS feed URLs for testing."""
        return [
            "https://cgil.it/feed",
            "https://cisl.it/rss",
            "https://uil.it/news/rss",
            "https://confindustria.it/feed",
        ]

    def test_rss_monitor_initialization(self, rss_monitor):
        """Test RSS monitor initialization."""
        assert rss_monitor is not None
        assert hasattr(rss_monitor, "feeds")
        assert hasattr(rss_monitor, "last_check")
        assert hasattr(rss_monitor, "check_interval")

    def test_add_rss_feed(self, rss_monitor):
        """Test adding RSS feeds to monitor."""
        feed_url = "https://cgil.it/feed"
        rss_monitor.add_feed(feed_url, "CGIL", UpdateSource.CGIL_RSS)

        assert len(rss_monitor.feeds) == 1
        assert rss_monitor.feeds[0]["url"] == feed_url
        assert rss_monitor.feeds[0]["source"] == UpdateSource.CGIL_RSS

    def test_ccnl_keyword_detection(self, rss_monitor):
        """Test CCNL keyword detection in RSS feeds."""
        test_titles = [
            "Rinnovo CCNL Metalmeccanici 2024 - Accordo raggiunto",
            "Nuovo contratto collettivo commercio firmato oggi",
            "Accordo siglato per CCNL sanità privata",
            "Aumento minimi tabellari settore alimentare",
            "Cronaca locale - notizie varie",  # Should not match
            "Firma contratto nazionale edilizia",
        ]

        ccnl_titles = [title for title in test_titles if rss_monitor.contains_ccnl_keywords(title)]

        assert len(ccnl_titles) == 5  # All except "Cronaca locale"
        assert "Cronaca locale - notizie varie" not in ccnl_titles

    @pytest.mark.asyncio
    async def test_fetch_rss_updates(self, rss_monitor):
        """Test fetching updates from RSS feeds."""
        # Mock RSS feed data
        mock_feed_data = [
            {
                "title": "Rinnovo CCNL Metalmeccanici 2024",
                "link": "https://cgil.it/news/ccnl-metalmeccanici",
                "published": datetime.utcnow() - timedelta(hours=2),
                "summary": "Raggiunto accordo per il rinnovo del contratto collettivo",
            }
        ]

        # Add mock feed
        rss_monitor.add_feed("mock://cgil.feed", "CGIL", UpdateSource.CGIL_RSS)

        # Mock the fetch method to return our test data
        async def mock_fetch_feed(feed_url):
            return mock_feed_data

        rss_monitor._fetch_feed = mock_fetch_feed

        updates = await rss_monitor.fetch_all_updates()

        assert len(updates) == 1
        assert updates[0]["title"] == "Rinnovo CCNL Metalmeccanici 2024"
        assert updates[0]["source"] == UpdateSource.CGIL_RSS


class TestCCNLUpdateDetection:
    """Test CCNL update detection and classification."""

    @pytest.fixture
    def update_detector(self):
        """Create update detector instance."""
        return CCNLUpdateDetector()

    def test_sector_classification(self, update_detector):
        """Test classifying CCNL updates by sector."""
        test_cases = [
            ("Rinnovo CCNL Metalmeccanici industria", "metalmeccanici"),
            ("Accordo commercio e terziario", "commercio"),
            ("Contratto edilizia e costruzioni", "edilizia"),
            ("CCNL sanità privata rinnovato", "sanita"),
            ("Firma contratto turismo", "turismo"),
        ]

        for title, expected_sector in test_cases:
            detected = update_detector.classify_sector(title)
            assert expected_sector in detected.lower()

    def test_update_type_classification(self, update_detector):
        """Test classifying type of CCNL update."""
        test_cases = [
            ("Rinnovo CCNL Metalmeccanici", "renewal"),
            ("Nuovo contratto collettivo", "new_agreement"),
            ("Modifica accordo esistente", "amendment"),
            ("Aumento minimi tabellari", "salary_update"),
            ("Firma contratto nazionale", "signing"),
        ]

        for title, expected_type in test_cases:
            detected = update_detector.classify_update_type(title)
            assert detected == expected_type

    def test_priority_calculation(self, update_detector):
        """Test calculating update priority."""
        high_priority_cases = [
            "Rinnovo CCNL Metalmeccanici - 2 milioni di lavoratori",
            "Nuovo contratto commercio nazionale",
        ]

        low_priority_cases = ["Modifica minore accordo aziendale", "Chiarimenti interpretativi CCNL"]

        for title in high_priority_cases:
            priority = update_detector.calculate_priority(title, "")
            assert priority >= 0.8

        for title in low_priority_cases:
            priority = update_detector.calculate_priority(title, "")
            assert priority <= 0.4

    @pytest.mark.asyncio
    async def test_ai_classification(self, update_detector):
        """Test AI-powered update classification."""
        sample_content = """
        È stato raggiunto l'accordo per il rinnovo del CCNL Metalmeccanici
        che riguarda circa 1.8 milioni di lavoratori. L'accordo prevede
        aumenti salariali del 3% e nuove disposizioni sul lavoro agile.
        """

        classification = await update_detector.ai_classify_update("Accordo CCNL Metalmeccanici", sample_content)

        assert classification["sector"] == "metalmeccanici"
        assert classification["update_type"] == "renewal"
        assert classification["confidence"] >= 0.8
        assert "salary_increase" in classification["changes_detected"]


class TestCCNLVersionManager:
    """Test CCNL version management and comparison."""

    @pytest.fixture
    def version_manager(self):
        """Create version manager instance."""
        return CCNLVersionManager()

    def test_version_creation(self, version_manager):
        """Test creating a new CCNL version."""
        ccnl_id = uuid4()
        version_data = {
            "version_number": "2024.1",
            "effective_date": date(2024, 1, 1),
            "salary_data": {"minimum_wages": {"level_1": 1500}},
            "working_conditions": {"weekly_hours": 40},
        }

        version = version_manager.create_version(ccnl_id, version_data)

        assert version.ccnl_id == ccnl_id
        assert version.version_number == "2024.1"
        assert version.is_current is True

    def test_version_comparison(self, version_manager):
        """Test comparing CCNL versions."""
        old_version = CCNLVersion(
            id=uuid4(),
            ccnl_id=uuid4(),
            version_number="2023.1",
            salary_data={"minimum_wages": {"level_1": 1400}},
            working_conditions={"weekly_hours": 40},
            effective_date=date(2023, 1, 1),
            created_at=datetime.utcnow(),
            is_current=False,
        )

        new_version = CCNLVersion(
            id=uuid4(),
            ccnl_id=old_version.ccnl_id,
            version_number="2024.1",
            salary_data={"minimum_wages": {"level_1": 1500}},
            working_conditions={"weekly_hours": 38},
            effective_date=date(2024, 1, 1),
            created_at=datetime.utcnow(),
            is_current=True,
        )

        changes = version_manager.compare_versions(old_version, new_version)

        assert "salary_data" in changes["modified"]
        assert "working_conditions" in changes["modified"]
        assert changes["modified"]["salary_data"]["level_1"]["old"] == 1400
        assert changes["modified"]["salary_data"]["level_1"]["new"] == 1500
        assert changes["modified"]["working_conditions"]["weekly_hours"]["old"] == 40
        assert changes["modified"]["working_conditions"]["weekly_hours"]["new"] == 38

    def test_version_history_tracking(self, version_manager):
        """Test tracking version history."""
        ccnl_id = uuid4()

        # Create multiple versions
        versions = [
            {"version_number": "2022.1", "effective_date": date(2022, 1, 1)},
            {"version_number": "2023.1", "effective_date": date(2023, 1, 1)},
            {"version_number": "2024.1", "effective_date": date(2024, 1, 1)},
        ]

        created_versions = []
        for version_data in versions:
            version = version_manager.create_version(ccnl_id, version_data)
            created_versions.append(version)

        history = version_manager.get_version_history(ccnl_id)

        assert len(history) == 3
        assert history[0].version_number == "2024.1"  # Most recent first
        assert history[-1].version_number == "2022.1"  # Oldest last

    def test_rollback_capability(self, version_manager):
        """Test rolling back to previous version."""
        ccnl_id = uuid4()

        # Create current version with error
        version_manager.create_version(
            ccnl_id,
            {
                "version_number": "2024.1",
                "salary_data": {"minimum_wages": {"level_1": -1500}},  # Invalid negative wage
            },
        )

        # Create previous good version
        previous_version = version_manager.create_version(
            ccnl_id, {"version_number": "2023.1", "salary_data": {"minimum_wages": {"level_1": 1400}}}
        )

        # Rollback to previous version
        rollback_result = version_manager.rollback_to_version(ccnl_id, previous_version.id)

        assert rollback_result is True
        current = version_manager.get_current_version(ccnl_id)
        assert current.version_number == "2023.1"


class TestCCNLUpdateProcessor:
    """Test CCNL update processing workflow."""

    @pytest.fixture
    def update_processor(self):
        """Create update processor instance."""
        return CCNLUpdateProcessor()

    @pytest.mark.asyncio
    async def test_update_processing_workflow(self, update_processor):
        """Test complete update processing workflow."""
        # Create mock update event
        update_event = CCNLUpdateEvent(
            id=uuid4(),
            ccnl_id=uuid4(),
            source=UpdateSource.CGIL_RSS,
            detected_at=datetime.utcnow(),
            title="Rinnovo CCNL Metalmeccanici 2024",
            url="https://example.com/ccnl-update",
            content_summary="Nuovo accordo con aumenti salariali",
            classification_confidence=0.95,
            status=UpdateStatus.DETECTED,
        )

        # Process the update
        result = await update_processor.process_update(update_event)

        assert result["status"] == "processed"
        assert result["created_version"] is not None
        assert result["changes_detected"] > 0

    def test_document_download_and_parsing(self, update_processor):
        """Test downloading and parsing CCNL documents."""
        mock_pdf_url = "https://example.com/ccnl.pdf"

        # Mock document content
        expected_content = {
            "salary_tables": {"level_1": 1500, "level_2": 1700},
            "working_hours": 38,
            "overtime_rates": {"weekday": 1.25, "weekend": 1.5},
        }

        # Mock the parsing method
        def mock_parse_document(url):
            return expected_content

        update_processor._parse_document = mock_parse_document

        parsed_content = update_processor.download_and_parse_document(mock_pdf_url)

        assert parsed_content == expected_content
        assert "salary_tables" in parsed_content

    def test_validation_checks(self, update_processor):
        """Test validation checks for CCNL updates."""
        valid_update_data = {
            "salary_tables": {"level_1": 1500, "level_2": 1700},
            "working_hours": 38,
            "overtime_rates": {"weekday": 1.25},
        }

        invalid_update_data = {
            "salary_tables": {"level_1": -100},  # Invalid negative salary
            "working_hours": 80,  # Invalid excessive hours
            "overtime_rates": {"weekday": 0.5},  # Invalid low overtime rate
        }

        # Valid data should pass
        validation_result = update_processor.validate_update_data(valid_update_data)
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0

        # Invalid data should fail
        validation_result = update_processor.validate_update_data(invalid_update_data)
        assert validation_result["is_valid"] is False
        assert len(validation_result["errors"]) > 0
        assert "negative salary" in str(validation_result["errors"])

    @pytest.mark.asyncio
    async def test_cross_source_verification(self, update_processor):
        """Test cross-referencing updates across multiple sources."""
        # Create multiple update events for same CCNL
        ccnl_id = uuid4()
        update_events = [
            CCNLUpdateEvent(
                id=uuid4(),
                ccnl_id=ccnl_id,
                source=UpdateSource.CGIL_RSS,
                title="CCNL Metalmeccanici rinnovato",
                detected_at=datetime.utcnow(),
            ),
            CCNLUpdateEvent(
                id=uuid4(),
                ccnl_id=ccnl_id,
                source=UpdateSource.CONFINDUSTRIA_NEWS,
                title="Accordo Metalmeccanici siglato",
                detected_at=datetime.utcnow(),
            ),
        ]

        verification_result = await update_processor.cross_verify_updates(update_events)

        assert verification_result["sources_count"] == 2
        assert verification_result["confidence_boost"] > 0
        assert verification_result["verified"] is True


class TestCCNLChangeDetection:
    """Test CCNL change detection and analysis."""

    def test_salary_change_detection(self):
        """Test detecting salary table changes."""
        old_salary_data = {"minimum_wages": {"level_1": 1400, "level_2": 1600, "level_3": 1800}}

        new_salary_data = {
            "minimum_wages": {
                "level_1": 1500,  # Increased
                "level_2": 1600,  # Unchanged
                "level_3": 1900,  # Increased
                "level_4": 2100,  # New level
            }
        }

        from app.services.ccnl_change_detector import CCNLChangeDetector

        change_detector = CCNLChangeDetector()

        changes = change_detector.detect_salary_changes(old_salary_data, new_salary_data)

        assert "level_1" in changes["increased"]
        assert changes["increased"]["level_1"]["old"] == 1400
        assert changes["increased"]["level_1"]["new"] == 1500

        assert "level_2" in changes["unchanged"]

        assert "level_4" in changes["added"]
        assert changes["added"]["level_4"] == 2100

    def test_working_conditions_change_detection(self):
        """Test detecting working conditions changes."""
        old_conditions = {"weekly_hours": 40, "overtime_rate": 1.5, "vacation_days": 26}

        new_conditions = {
            "weekly_hours": 38,  # Reduced
            "overtime_rate": 1.5,  # Unchanged
            "vacation_days": 28,  # Increased
            "remote_work_days": 2,  # New provision
        }

        from app.services.ccnl_change_detector import CCNLChangeDetector

        change_detector = CCNLChangeDetector()

        changes = change_detector.detect_working_conditions_changes(old_conditions, new_conditions)

        assert "weekly_hours" in changes["modified"]
        assert changes["modified"]["weekly_hours"]["change"] == -2

        assert "remote_work_days" in changes["added"]
        assert changes["added"]["remote_work_days"] == 2

    def test_change_significance_scoring(self):
        """Test scoring the significance of changes."""
        changes = {
            "salary_increases": {"level_1": {"percentage": 7.1}},  # Significant
            "working_hours_reduction": {"hours": 2},  # Moderate
            "new_benefits": ["remote_work", "flexible_hours"],  # Significant
        }

        from app.services.ccnl_change_detector import CCNLChangeDetector

        change_detector = CCNLChangeDetector()

        significance_score = change_detector.calculate_significance_score(changes)

        assert significance_score >= 0.8  # Should be high due to salary increases and new benefits


class TestMonitoringDashboard:
    """Test CCNL monitoring dashboard functionality."""

    def test_dashboard_data_aggregation(self):
        """Test aggregating data for monitoring dashboard."""
        from app.services.ccnl_monitoring_dashboard import CCNLMonitoringDashboard

        dashboard = CCNLMonitoringDashboard()

        # Mock recent update events
        recent_updates = [
            {"sector": "metalmeccanici", "date": datetime.utcnow() - timedelta(hours=2)},
            {"sector": "commercio", "date": datetime.utcnow() - timedelta(hours=6)},
            {"sector": "edilizia", "date": datetime.utcnow() - timedelta(days=1)},
        ]

        dashboard_data = dashboard.aggregate_dashboard_data(recent_updates)

        assert "total_ccnls_monitored" in dashboard_data
        assert "updates_last_24h" in dashboard_data
        assert "pending_reviews" in dashboard_data
        assert dashboard_data["updates_last_24h"] == 3

    def test_source_reliability_metrics(self):
        """Test calculating source reliability metrics."""
        from app.services.ccnl_monitoring_dashboard import CCNLMonitoringDashboard

        dashboard = CCNLMonitoringDashboard()

        source_stats = [
            {"source": "CGIL_RSS", "successful_detections": 45, "false_positives": 3},
            {"source": "CISL_RSS", "successful_detections": 38, "false_positives": 2},
            {"source": "CONFINDUSTRIA_NEWS", "successful_detections": 42, "false_positives": 5},
        ]

        reliability_metrics = dashboard.calculate_source_reliability(source_stats)

        cgil_reliability = reliability_metrics["CGIL_RSS"]["reliability_score"]
        assert cgil_reliability > 0.9  # Should be high with low false positives

        confindustria_reliability = reliability_metrics["CONFINDUSTRIA_NEWS"]["reliability_score"]
        assert confindustria_reliability < cgil_reliability  # Should be lower due to more false positives


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_full_integration_workflow(self):
        """Test complete integration workflow from RSS detection to database update."""
        # This test simulates the full workflow:
        # 1. RSS feed detects CCNL update
        # 2. Update is classified and processed
        # 3. New version is created
        # 4. Changes are detected and logged
        # 5. Notifications are sent

        from app.services.ccnl_integration_orchestrator import CCNLIntegrationOrchestrator

        orchestrator = CCNLIntegrationOrchestrator()

        # Simulate RSS update detection
        mock_rss_item = {
            "title": "Firmato rinnovo CCNL Metalmeccanici 2024",
            "link": "https://cgil.it/news/ccnl-metalmeccanici-2024",
            "published": datetime.utcnow(),
            "summary": "Accordo raggiunto con aumenti del 5% e riduzione orario a 38 ore",
        }

        # Process the complete workflow
        result = await orchestrator.process_full_workflow(mock_rss_item, UpdateSource.CGIL_RSS)

        assert result["detection_successful"] is True
        assert result["classification_confidence"] > 0.8
        assert result["version_created"] is True
        assert result["changes_detected"] > 0
        assert result["notifications_sent"] > 0

    def test_handling_partial_updates(self):
        """Test handling partial CCNL updates (not full renewals)."""
        # Test scenario: Only salary tables updated, other provisions unchanged
        pass

    def test_handling_temporary_agreements(self):
        """Test handling temporary agreements (like COVID-related provisions)."""
        # Test scenario: Temporary provisions with specific expiry dates
        pass

    def test_handling_regional_variations(self):
        """Test handling regional variations of national CCNLs."""
        # Test scenario: National CCNL with regional salary adjustments
        pass

    def test_error_recovery_and_rollback(self):
        """Test error recovery and rollback mechanisms."""
        # Test scenario: Failed update processing and automatic rollback
        pass

    def test_performance_under_load(self):
        """Test system performance under high update volume."""
        # Test scenario: Multiple simultaneous CCNL updates
        pass


class TestUpdateNotifications:
    """Test notification system for CCNL updates."""

    def test_notification_generation(self):
        """Test generating notifications for CCNL updates."""
        from app.services.ccnl_notification_service import CCNLNotificationService

        notification_service = CCNLNotificationService()

        update_data = {
            "ccnl_name": "CCNL Metalmeccanici",
            "changes": {
                "salary_increases": {"level_1": {"old": 1400, "new": 1500}},
                "working_hours": {"old": 40, "new": 38},
            },
            "effective_date": date(2024, 1, 1),
        }

        notification = notification_service.generate_update_notification(update_data)

        assert "CCNL Metalmeccanici" in notification["title"]
        assert "aggiornato" in notification["message"].lower()
        assert notification["priority"] == "high"
        assert len(notification["affected_users"]) > 0

    def test_notification_targeting(self):
        """Test targeting notifications to relevant users."""
        # Test that users interested in specific sectors receive relevant notifications
        pass


# Mock classes for testing (would normally be in separate files)


class MockRSSFeedMonitor:
    """Mock RSS feed monitor for testing."""

    def __init__(self):
        self.feeds = []
        self.last_check = None
        self.check_interval = timedelta(hours=2)

    def add_feed(self, url: str, name: str, source: UpdateSource):
        self.feeds.append({"url": url, "name": name, "source": source})

    def contains_ccnl_keywords(self, title: str) -> bool:
        keywords = ["rinnovo ccnl", "contratto collettivo", "accordo siglato", "firma contratto", "minimi tabellari"]
        return any(keyword in title.lower() for keyword in keywords)

    async def fetch_all_updates(self) -> list[dict]:
        # Mock implementation
        return []


class MockCCNLUpdateDetector:
    """Mock update detector for testing."""

    def classify_sector(self, title: str) -> str:
        sector_keywords = {
            "metalmeccanic": "metalmeccanici",
            "commercio": "commercio",
            "edilizia": "edilizia",
            "sanità": "sanita",
            "turismo": "turismo",
        }

        for keyword, sector in sector_keywords.items():
            if keyword in title.lower():
                return sector
        return "unknown"

    def classify_update_type(self, title: str) -> str:
        if "rinnovo" in title.lower():
            return "renewal"
        elif "nuovo contratto" in title.lower():
            return "new_agreement"
        elif "modifica" in title.lower():
            return "amendment"
        elif "minimi tabellari" in title.lower():
            return "salary_update"
        elif "firma" in title.lower():
            return "signing"
        return "unknown"

    def calculate_priority(self, title: str, content: str) -> float:
        # Simple priority calculation for testing
        if "milioni di lavoratori" in (title + " " + content).lower():
            return 0.9
        elif "nazionale" in title.lower():
            return 0.7
        elif "aziendale" in title.lower():
            return 0.3
        return 0.5

    async def ai_classify_update(self, title: str, content: str) -> dict[str, Any]:
        # Mock AI classification
        return {
            "sector": "metalmeccanici",
            "update_type": "renewal",
            "confidence": 0.85,
            "changes_detected": ["salary_increase", "working_hours_reduction"],
        }
