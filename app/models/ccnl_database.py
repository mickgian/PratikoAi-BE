"""Database models for Italian Collective Labor Agreements (CCNL).

This module provides SQLModel database models for persisting CCNL data
with proper relationships, constraints, and indexes for optimal performance.
"""

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel

from app.models.ccnl_data import AllowanceType, CCNLSector, CompanySize, GeographicArea, LeaveType, WorkerCategory


class CCNLSectorDB(SQLModel, table=True):
    """Database model for CCNL sectors."""

    __tablename__ = "ccnl_sectors"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Unique identifiers
    sector_code: str = Field(max_length=50, unique=True, index=True)

    # Core fields
    italian_name: str = Field(max_length=200)
    priority_level: int = Field(default=2)
    worker_coverage_percentage: Decimal = Field(default=Decimal("0.0"), sa_column=Column(Numeric(5, 2), default=0.0))
    active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    agreements: list["CCNLAgreementDB"] = Relationship(back_populates="sector")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_ccnl_sectors_priority_active", "priority_level", "active"),
        CheckConstraint("priority_level >= 1 AND priority_level <= 6", name="valid_priority_level"),
    )

    @classmethod
    def from_enum(cls, sector: CCNLSector) -> "CCNLSectorDB":
        """Create database model from sector enum."""
        return cls(
            sector_code=sector.value, italian_name=sector.italian_name(), priority_level=sector.priority_level()
        )

    def to_enum(self) -> CCNLSector:
        """Convert database model to sector enum."""
        return CCNLSector(self.sector_code)


class CCNLAgreementDB(SQLModel, table=True):
    """Database model for complete CCNL agreements."""

    __tablename__ = "ccnl_agreements"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Foreign keys
    sector_code: str = Field(foreign_key="ccnl_sectors.sector_code", max_length=50)

    # Core fields
    name: str = Field(max_length=500)
    valid_from: date = Field(sa_column=Column(Date, nullable=False))
    valid_to: date | None = Field(default=None, sa_column=Column(Date, nullable=True))

    # JSON fields (requires sa_column override)
    signatory_unions: list[str] = Field(default_factory=list, sa_column=Column(JSON, default=list))
    signatory_employers: list[str] = Field(default_factory=list, sa_column=Column(JSON, default=list))

    # Status fields
    renewal_status: str = Field(default="vigente", max_length=20)  # vigente, scaduto, in_rinnovo
    last_updated: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    data_source: str | None = Field(default=None, max_length=500)
    verification_date: date | None = Field(default=None, sa_column=Column(Date, nullable=True))

    # Metadata
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    sector: "CCNLSectorDB" = Relationship(back_populates="agreements")
    job_levels: list["JobLevelDB"] = Relationship(
        back_populates="agreement", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    salary_tables: list["SalaryTableDB"] = Relationship(
        back_populates="agreement", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    working_hours: list["WorkingHoursDB"] = Relationship(
        back_populates="agreement", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    overtime_rules: list["OvertimeRulesDB"] = Relationship(
        back_populates="agreement", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    leave_entitlements: list["LeaveEntitlementDB"] = Relationship(
        back_populates="agreement", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    notice_periods: list["NoticePeriodsDB"] = Relationship(
        back_populates="agreement", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    special_allowances: list["SpecialAllowanceDB"] = Relationship(
        back_populates="agreement", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Indexes
    __table_args__ = (
        Index("idx_ccnl_agreements_sector_valid", "sector_code", "valid_from", "valid_to"),
        Index("idx_ccnl_agreements_dates", "valid_from", "valid_to"),
    )

    def is_currently_valid(self) -> bool:
        """Check if CCNL agreement is currently valid."""
        today = date.today()
        if today < self.valid_from:
            return False
        return not (self.valid_to and today > self.valid_to)

    def get_levels_by_category(self, category: str) -> list["JobLevelDB"]:
        """Get all job levels for a specific worker category."""
        return [level for level in self.job_levels if level.worker_category == category]

    def get_salary_for_level(self, level_code: str, area: str = "nazionale") -> Optional["SalaryTableDB"]:
        """Get salary table for a specific level and geographic area."""
        for salary in self.salary_tables:
            if salary.level_code == level_code and salary.geographic_area == area and salary.is_valid_on(date.today()):
                return salary
        return None

    def get_allowances_for_level(self, level_code: str) -> list["SpecialAllowanceDB"]:
        """Get applicable allowances for a job level."""
        applicable = []
        for allowance in self.special_allowances:
            if not allowance.applicable_job_levels or level_code in allowance.applicable_job_levels:
                applicable.append(allowance)
        return applicable


class JobLevelDB(SQLModel, table=True):
    """Database model for job levels within CCNL agreements."""

    __tablename__ = "ccnl_job_levels"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Foreign keys
    agreement_id: int = Field(foreign_key="ccnl_agreements.id")

    # Core fields
    level_code: str = Field(max_length=10)
    level_name: str = Field(max_length=200)
    worker_category: str = Field(max_length=20)  # operaio, impiegato, quadro, dirigente
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    minimum_experience_months: int = Field(default=0)

    # JSON fields
    required_qualifications: list[str] = Field(default_factory=list, sa_column=Column(JSON, default=list))
    typical_tasks: list[str] = Field(default_factory=list, sa_column=Column(JSON, default=list))

    decision_making_level: str | None = Field(default=None, max_length=50)
    supervision_responsibilities: bool = Field(default=False)

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    agreement: "CCNLAgreementDB" = Relationship(back_populates="job_levels")

    # Indexes
    __table_args__ = (
        Index("idx_job_levels_agreement_code", "agreement_id", "level_code"),
        Index("idx_job_levels_category", "worker_category"),
    )

    def is_lower_than(self, other: "JobLevelDB") -> bool:
        """Check if this level is lower than another."""
        return self.level_code < other.level_code

    def is_higher_than(self, other: "JobLevelDB") -> bool:
        """Check if this level is higher than another."""
        return self.level_code > other.level_code

    def is_higher_category_than(self, other: "JobLevelDB") -> bool:
        """Check if this level is in a higher category than another."""
        category_hierarchy = {"operaio": 1, "apprendista": 1, "impiegato": 2, "quadro": 3, "dirigente": 4}
        return category_hierarchy.get(self.worker_category, 1) > category_hierarchy.get(other.worker_category, 1)


class SalaryTableDB(SQLModel, table=True):
    """Database model for salary tables."""

    __tablename__ = "ccnl_salary_tables"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Foreign keys
    agreement_id: int = Field(foreign_key="ccnl_agreements.id")

    # Core fields
    level_code: str = Field(max_length=10)
    base_monthly_salary: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    geographic_area: str = Field(default="nazionale", max_length=20)  # nazionale, nord, centro, sud, sud_isole
    valid_from: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    valid_to: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    thirteenth_month: bool = Field(default=True)
    fourteenth_month: bool = Field(default=False)

    # JSON fields
    additional_allowances: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    company_size_adjustments: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, default=dict))

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    agreement: "CCNLAgreementDB" = Relationship(back_populates="salary_tables")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_salary_tables_agreement_level", "agreement_id", "level_code", "geographic_area"),
        Index("idx_salary_tables_dates", "valid_from", "valid_to"),
        CheckConstraint("base_monthly_salary > 0", name="positive_salary"),
    )

    def is_valid_on(self, check_date: date) -> bool:
        """Check if salary table is valid on a specific date."""
        if self.valid_from and check_date < self.valid_from:
            return False
        return not (self.valid_to and check_date > self.valid_to)

    def get_annual_salary(self) -> Decimal:
        """Get base annual salary (12 months)."""
        return self.base_monthly_salary * 12

    def get_total_monthly_salary(self) -> Decimal:
        """Get total monthly salary including additional allowances."""
        total = self.base_monthly_salary
        for allowance_amount in (self.additional_allowances or {}).values():
            total += Decimal(str(allowance_amount))
        return total

    def get_annual_salary_with_additional_months(self) -> Decimal:
        """Get annual salary including 13th and 14th month."""
        months = 12
        if self.thirteenth_month:
            months += 1
        if self.fourteenth_month:
            months += 1
        return self.base_monthly_salary * months


class WorkingHoursDB(SQLModel, table=True):
    """Database model for working hours configurations."""

    __tablename__ = "ccnl_working_hours"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Foreign keys
    agreement_id: int = Field(foreign_key="ccnl_agreements.id")

    # Core fields
    ordinary_weekly_hours: int
    maximum_weekly_hours: int = Field(default=48)
    daily_rest_hours: int = Field(default=11)
    weekly_rest_hours: int = Field(default=24)
    flexible_hours_allowed: bool = Field(default=False)
    flexible_hours_range_min: int | None = Field(default=None)
    flexible_hours_range_max: int | None = Field(default=None)
    core_hours_start: str | None = Field(default=None, max_length=5)  # "09:00"
    core_hours_end: str | None = Field(default=None, max_length=5)  # "17:00"
    part_time_allowed: bool = Field(default=True)
    minimum_part_time_hours: int | None = Field(default=None)
    shift_work_allowed: bool = Field(default=False)

    # JSON field
    shift_patterns: list[Any] = Field(default_factory=list, sa_column=Column(JSON, default=list))

    night_shift_allowance: Decimal | None = Field(default=None, sa_column=Column(Numeric(6, 2), nullable=True))

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    agreement: "CCNLAgreementDB" = Relationship(back_populates="working_hours")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_working_hours_agreement", "agreement_id"),
        CheckConstraint("ordinary_weekly_hours > 0", name="positive_weekly_hours"),
        CheckConstraint("maximum_weekly_hours >= ordinary_weekly_hours", name="max_hours_valid"),
    )

    def get_ordinary_daily_hours(self) -> float:
        """Get ordinary daily hours (assuming 5-day work week)."""
        return self.ordinary_weekly_hours / 5.0


class OvertimeRulesDB(SQLModel, table=True):
    """Database model for overtime rules and compensation."""

    __tablename__ = "ccnl_overtime_rules"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Foreign keys
    agreement_id: int = Field(foreign_key="ccnl_agreements.id")

    # Core fields
    daily_threshold_hours: int = Field(default=8)
    weekly_threshold_hours: int = Field(default=40)
    daily_overtime_rate: Decimal = Field(
        default=Decimal("1.25"), sa_column=Column(Numeric(4, 2), default=Decimal("1.25"))
    )
    weekend_rate: Decimal = Field(default=Decimal("1.50"), sa_column=Column(Numeric(4, 2), default=Decimal("1.50")))
    holiday_rate: Decimal = Field(default=Decimal("2.00"), sa_column=Column(Numeric(4, 2), default=Decimal("2.00")))
    maximum_daily_overtime: int | None = Field(default=None)
    maximum_weekly_overtime: int | None = Field(default=None)
    maximum_monthly_overtime: int | None = Field(default=None)
    maximum_annual_overtime: int | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    agreement: "CCNLAgreementDB" = Relationship(back_populates="overtime_rules")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_overtime_rules_agreement", "agreement_id"),
        CheckConstraint("daily_overtime_rate >= 1.0", name="valid_overtime_rate"),
    )

    def calculate_overtime_pay(self, base_hourly_rate: Decimal, overtime_hours: int) -> Decimal:
        """Calculate overtime compensation."""
        return base_hourly_rate * self.daily_overtime_rate * overtime_hours

    def is_overtime_allowed(self, daily_hours: int, weekly_total: int) -> bool:
        """Check if overtime is allowed given daily and weekly totals."""
        if self.maximum_daily_overtime and daily_hours > self.maximum_daily_overtime:
            return False
        return not (self.maximum_weekly_overtime and weekly_total > self.maximum_weekly_overtime)


class LeaveEntitlementDB(SQLModel, table=True):
    """Database model for leave entitlements."""

    __tablename__ = "ccnl_leave_entitlements"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Foreign keys
    agreement_id: int = Field(foreign_key="ccnl_agreements.id")

    # Core fields
    leave_type: str = Field(max_length=50)  # ferie, permessi_retribuiti, etc.
    base_annual_days: int | None = Field(default=None)
    base_annual_hours: int | None = Field(default=None)

    # JSON field
    seniority_bonus_schedule: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, default=dict))

    calculation_method: str = Field(default="annual", max_length=20)
    minimum_usage_hours: int | None = Field(default=None)
    advance_notice_hours: int | None = Field(default=None)
    compensation_percentage: Decimal = Field(
        default=Decimal("1.00"), sa_column=Column(Numeric(4, 2), default=Decimal("1.00"))
    )
    mandatory_period: bool = Field(default=False)
    additional_optional_days: int | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    agreement: "CCNLAgreementDB" = Relationship(back_populates="leave_entitlements")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_leave_entitlements_agreement_type", "agreement_id", "leave_type"),
        CheckConstraint("compensation_percentage >= 0 AND compensation_percentage <= 1", name="valid_compensation"),
    )

    def get_annual_entitlement(self, months_seniority: int) -> int:
        """Get total annual entitlement including seniority bonuses."""
        base = self.base_annual_days or 0

        # Add seniority bonuses - find highest threshold met
        highest_bonus = 0
        for threshold_months, bonus in sorted((self.seniority_bonus_schedule or {}).items()):
            if months_seniority >= int(threshold_months):
                highest_bonus = bonus

        return base + highest_bonus

    def get_monthly_accrual(self) -> float:
        """Get monthly accrual amount."""
        if self.base_annual_hours:
            return self.base_annual_hours / 12.0
        elif self.base_annual_days:
            return self.base_annual_days / 12.0
        return 0.0


class NoticePeriodsDB(SQLModel, table=True):
    """Database model for notice period requirements."""

    __tablename__ = "ccnl_notice_periods"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Foreign keys
    agreement_id: int = Field(foreign_key="ccnl_agreements.id")

    # Core fields
    worker_category: str = Field(max_length=20)
    seniority_months_min: int
    seniority_months_max: int
    notice_days: int
    termination_by: str = Field(default="both", max_length=10)  # employer, employee, both

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    agreement: "CCNLAgreementDB" = Relationship(back_populates="notice_periods")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_notice_periods_agreement_category", "agreement_id", "worker_category"),
        CheckConstraint("seniority_months_max >= seniority_months_min", name="valid_seniority_range"),
        CheckConstraint("notice_days > 0", name="positive_notice_days"),
    )

    def applies_to_seniority(self, months_seniority: int) -> bool:
        """Check if this notice period applies to given seniority."""
        return self.seniority_months_min <= months_seniority <= self.seniority_months_max


class SpecialAllowanceDB(SQLModel, table=True):
    """Database model for special allowances and benefits."""

    __tablename__ = "ccnl_special_allowances"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Foreign keys
    agreement_id: int = Field(foreign_key="ccnl_agreements.id")

    # Core fields
    allowance_type: str = Field(max_length=50)  # buoni_pasto, indennita_trasporto, etc.
    amount: Decimal = Field(sa_column=Column(Numeric(8, 2), nullable=False))
    frequency: str = Field(max_length=10)  # daily, monthly, annual

    # JSON fields
    conditions: list[Any] = Field(default_factory=list, sa_column=Column(JSON, default=list))
    applicable_job_levels: list[str] = Field(default_factory=list, sa_column=Column(JSON, default=list))
    geographic_areas: list[str] = Field(default_factory=list, sa_column=Column(JSON, default=list))
    company_sizes: list[str] = Field(default_factory=list, sa_column=Column(JSON, default=list))

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    agreement: "CCNLAgreementDB" = Relationship(back_populates="special_allowances")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_special_allowances_agreement_type", "agreement_id", "allowance_type"),
        CheckConstraint("amount > 0", name="positive_allowance_amount"),
    )

    def get_monthly_amount(self, working_days: int = 22) -> Decimal:
        """Get monthly amount for this allowance."""
        if self.frequency == "monthly":
            return self.amount
        elif self.frequency == "daily":
            return self.amount * working_days
        elif self.frequency == "annual":
            return self.amount / 12
        return self.amount

    def applies_to_geographic_area(self, area: str) -> bool:
        """Check if allowance applies to specific geographic area."""
        if not self.geographic_areas:  # Empty list means national coverage
            return True
        return area in self.geographic_areas

    def applies_to_job_level(self, level_code: str) -> bool:
        """Check if allowance applies to specific job level."""
        if not self.applicable_job_levels:  # Empty list means all levels
            return True
        return level_code in self.applicable_job_levels

    def applies_to_company_size(self, company_size: str) -> bool:
        """Check if allowance applies to specific company size."""
        if not self.company_sizes:  # Empty list means all sizes
            return True
        return company_size in self.company_sizes
