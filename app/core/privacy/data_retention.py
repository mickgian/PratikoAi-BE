"""Data Retention Enforcement Service for GDPR Article 5(1)(e).

Implements storage limitation principle: personal data must not be kept
longer than necessary for the purposes for which it is processed.

Retention periods aligned with Italian legal requirements:
- Identity data: 2555 days (7 years, Italian tax law)
- Contact data: 365 days (1 year)
- Financial data: 2555 days (7 years, Italian tax law)
- Behavioral data: 90 days (3 months)
- Technical data: 30 days (1 month)
- Content data: 365 days (1 year)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from app.core.logging import logger


class RetentionCategory(str, Enum):
    """Data categories with retention policies."""

    IDENTITY = "identity"
    CONTACT = "contact"
    FINANCIAL = "financial"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    CONTENT = "content"


@dataclass
class DataRetentionPolicy:
    """A single data retention policy."""

    category: RetentionCategory
    retention_days: int
    description: str

    def is_expired(self, created_at: datetime) -> bool:
        """Check if data created at the given time has expired.

        Uses exclusive boundary: data expires strictly after
        retention_days have passed.
        """
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        expiry = created_at + timedelta(days=self.retention_days)
        return datetime.now(UTC) > expiry


@dataclass
class RetentionEnforcementResult:
    """Result of a retention enforcement run for one category."""

    category: RetentionCategory
    records_checked: int
    records_expired: int
    records_deleted: int
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class DataRetentionService:
    """Manages and enforces data retention policies.

    Provides policy lookup, expiry checking, and enforcement
    for all GDPR data categories.
    """

    def __init__(self) -> None:
        self._policies: dict[RetentionCategory, DataRetentionPolicy] = {
            RetentionCategory.IDENTITY: DataRetentionPolicy(
                category=RetentionCategory.IDENTITY,
                retention_days=2555,
                description="Identity data (7 years, Italian tax law D.P.R. 600/1973)",
            ),
            RetentionCategory.CONTACT: DataRetentionPolicy(
                category=RetentionCategory.CONTACT,
                retention_days=365,
                description="Contact data (1 year after last interaction)",
            ),
            RetentionCategory.FINANCIAL: DataRetentionPolicy(
                category=RetentionCategory.FINANCIAL,
                retention_days=2555,
                description="Financial data (7 years, Italian tax law D.P.R. 600/1973)",
            ),
            RetentionCategory.BEHAVIORAL: DataRetentionPolicy(
                category=RetentionCategory.BEHAVIORAL,
                retention_days=90,
                description="Behavioral/conversation data (90 days)",
            ),
            RetentionCategory.TECHNICAL: DataRetentionPolicy(
                category=RetentionCategory.TECHNICAL,
                retention_days=30,
                description="Technical/log data (30 days)",
            ),
            RetentionCategory.CONTENT: DataRetentionPolicy(
                category=RetentionCategory.CONTENT,
                retention_days=365,
                description="User-generated content (1 year)",
            ),
        }

    def get_policy(self, category: RetentionCategory) -> DataRetentionPolicy | None:
        """Get retention policy for a category."""
        return self._policies.get(category)

    def get_all_policies(self) -> list[DataRetentionPolicy]:
        """Get all retention policies."""
        return list(self._policies.values())

    def is_data_expired(self, category: RetentionCategory, created_at: datetime) -> bool:
        """Check if data in a category has exceeded its retention period."""
        policy = self._policies.get(category)
        if policy is None:
            return False
        return policy.is_expired(created_at)

    def get_expiry_date(self, category: RetentionCategory, created_at: datetime) -> datetime:
        """Calculate the expiry date for data in a category."""
        policy = self._policies.get(category)
        if policy is None:
            raise ValueError(f"No retention policy for category: {category}")
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return created_at + timedelta(days=policy.retention_days)

    def get_policies_summary(self) -> dict[str, dict[str, Any]]:
        """Get a summary of all policies for reporting."""
        return {
            cat.value: {
                "retention_days": policy.retention_days,
                "description": policy.description,
            }
            for cat, policy in self._policies.items()
        }
