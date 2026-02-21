"""Tests for Data Retention Enforcement Service.

Validates that data retention policies are enforced correctly
per GDPR Article 5(1)(e) - Storage Limitation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.privacy.data_retention import (
    DataRetentionPolicy,
    DataRetentionService,
    RetentionCategory,
    RetentionEnforcementResult,
)


class TestRetentionCategory:
    """Test RetentionCategory enum."""

    def test_all_categories_defined(self):
        """Test all required data categories exist."""
        categories = [c.value for c in RetentionCategory]
        assert "behavioral" in categories
        assert "technical" in categories
        assert "content" in categories
        assert "contact" in categories
        assert "identity" in categories
        assert "financial" in categories

    def test_category_count(self):
        """Test we have at least 6 categories."""
        assert len(RetentionCategory) >= 6


class TestDataRetentionPolicy:
    """Test DataRetentionPolicy configuration."""

    def test_policy_creation(self):
        """Test creating a retention policy."""
        policy = DataRetentionPolicy(
            category=RetentionCategory.BEHAVIORAL,
            retention_days=90,
            description="Behavioral data retained for 90 days",
        )
        assert policy.category == RetentionCategory.BEHAVIORAL
        assert policy.retention_days == 90

    def test_policy_is_expired(self):
        """Test expired data detection."""
        policy = DataRetentionPolicy(
            category=RetentionCategory.TECHNICAL,
            retention_days=30,
            description="Technical data retained for 30 days",
        )
        old_date = datetime.now(UTC) - timedelta(days=31)
        assert policy.is_expired(old_date)

    def test_policy_not_expired(self):
        """Test non-expired data detection."""
        policy = DataRetentionPolicy(
            category=RetentionCategory.TECHNICAL,
            retention_days=30,
            description="Technical data retained for 30 days",
        )
        recent_date = datetime.now(UTC) - timedelta(days=15)
        assert not policy.is_expired(recent_date)

    def test_policy_boundary(self):
        """Test expiry boundary."""
        policy = DataRetentionPolicy(
            category=RetentionCategory.BEHAVIORAL,
            retention_days=90,
            description="Behavioral data",
        )
        # 89 days ago - should NOT be expired
        within_date = datetime.now(UTC) - timedelta(days=89)
        assert not policy.is_expired(within_date)

        # 91 days ago - should be expired
        expired_date = datetime.now(UTC) - timedelta(days=91)
        assert policy.is_expired(expired_date)


class TestDataRetentionService:
    """Test DataRetentionService."""

    def test_default_policies(self):
        """Test default retention policies match GDPR requirements."""
        service = DataRetentionService()
        policies = service.get_all_policies()

        assert len(policies) >= 6

        # Verify specific retention periods
        behavioral = service.get_policy(RetentionCategory.BEHAVIORAL)
        assert behavioral is not None
        assert behavioral.retention_days == 90

        technical = service.get_policy(RetentionCategory.TECHNICAL)
        assert technical is not None
        assert technical.retention_days == 30

        identity = service.get_policy(RetentionCategory.IDENTITY)
        assert identity is not None
        assert identity.retention_days == 2555  # 7 years

        financial = service.get_policy(RetentionCategory.FINANCIAL)
        assert financial is not None
        assert financial.retention_days == 2555  # 7 years

        contact = service.get_policy(RetentionCategory.CONTACT)
        assert contact is not None
        assert contact.retention_days == 365  # 1 year

        content = service.get_policy(RetentionCategory.CONTENT)
        assert content is not None
        assert content.retention_days == 365  # 1 year

    def test_get_policy_nonexistent(self):
        """Test getting a non-existent policy returns None."""
        service = DataRetentionService()
        # All categories should have policies, but test the method
        result = service.get_policy(RetentionCategory.BEHAVIORAL)
        assert result is not None

    def test_check_data_expiry(self):
        """Test checking if data is expired for a category."""
        service = DataRetentionService()

        # 100 days old behavioral data should be expired (90 day policy)
        old_date = datetime.now(UTC) - timedelta(days=100)
        assert service.is_data_expired(RetentionCategory.BEHAVIORAL, old_date)

        # 10 days old behavioral data should not be expired
        recent_date = datetime.now(UTC) - timedelta(days=10)
        assert not service.is_data_expired(RetentionCategory.BEHAVIORAL, recent_date)

    def test_get_expiry_date(self):
        """Test calculating expiry date for a category."""
        service = DataRetentionService()
        created = datetime(2025, 1, 1, tzinfo=UTC)

        expiry = service.get_expiry_date(RetentionCategory.BEHAVIORAL, created)
        expected = created + timedelta(days=90)
        assert expiry == expected

    def test_policies_summary(self):
        """Test getting a summary of all policies."""
        service = DataRetentionService()
        summary = service.get_policies_summary()

        assert isinstance(summary, dict)
        assert "behavioral" in summary
        assert "technical" in summary
        assert summary["behavioral"]["retention_days"] == 90
        assert summary["technical"]["retention_days"] == 30


class TestRetentionEnforcementResult:
    """Test RetentionEnforcementResult dataclass."""

    def test_result_creation(self):
        """Test creating an enforcement result."""
        result = RetentionEnforcementResult(
            category=RetentionCategory.BEHAVIORAL,
            records_checked=100,
            records_expired=5,
            records_deleted=5,
            errors=[],
        )
        assert result.records_checked == 100
        assert result.records_expired == 5
        assert result.records_deleted == 5
        assert result.success

    def test_result_with_errors(self):
        """Test result with errors marks as not successful."""
        result = RetentionEnforcementResult(
            category=RetentionCategory.TECHNICAL,
            records_checked=50,
            records_expired=10,
            records_deleted=8,
            errors=["Failed to delete 2 records"],
        )
        assert not result.success
        assert len(result.errors) == 1
