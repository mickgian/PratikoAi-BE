"""
Database models for Italian Collective Labor Agreements (CCNL).

This module provides SQLAlchemy database models for persisting CCNL data
with proper relationships, constraints, and indexes for optimal performance.
"""

import json
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Numeric,
    Boolean, JSON, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.ccnl_data import (
    CCNLSector, WorkerCategory, GeographicArea, 
    LeaveType, AllowanceType, CompanySize
)

Base = declarative_base()


class CCNLSectorDB(Base):
    """Database model for CCNL sectors."""
    
    __tablename__ = "ccnl_sectors"
    
    id = Column(Integer, primary_key=True)
    sector_code = Column(String(50), unique=True, nullable=False, index=True)
    italian_name = Column(String(200), nullable=False)
    priority_level = Column(Integer, nullable=False, default=2)
    worker_coverage_percentage = Column(Numeric(5, 2), default=0.0)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreements = relationship("CCNLAgreementDB", back_populates="sector")
    
    # Indexes
    __table_args__ = (
        Index('idx_ccnl_sectors_priority_active', 'priority_level', 'active'),
        CheckConstraint('priority_level >= 1 AND priority_level <= 6', name='valid_priority_level'),
    )
    
    @classmethod
    def from_enum(cls, sector: CCNLSector) -> "CCNLSectorDB":
        """Create database model from sector enum."""
        return cls(
            sector_code=sector.value,
            italian_name=sector.italian_name(),
            priority_level=sector.priority_level()
        )
    
    def to_enum(self) -> CCNLSector:
        """Convert database model to sector enum."""
        return CCNLSector(self.sector_code)


class CCNLAgreementDB(Base):
    """Database model for complete CCNL agreements."""
    
    __tablename__ = "ccnl_agreements"
    
    id = Column(Integer, primary_key=True)
    sector_code = Column(String(50), ForeignKey('ccnl_sectors.sector_code'), nullable=False)
    name = Column(String(500), nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    signatory_unions = Column(JSON, default=list)  # List of union names
    signatory_employers = Column(JSON, default=list)  # List of employer associations
    renewal_status = Column(String(20), default="vigente")  # vigente, scaduto, in_rinnovo
    last_updated = Column(DateTime, default=datetime.utcnow)
    data_source = Column(String(500), nullable=True)
    verification_date = Column(Date, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sector = relationship("CCNLSectorDB", back_populates="agreements")
    job_levels = relationship("JobLevelDB", back_populates="agreement", cascade="all, delete-orphan")
    salary_tables = relationship("SalaryTableDB", back_populates="agreement", cascade="all, delete-orphan")
    working_hours = relationship("WorkingHoursDB", back_populates="agreement", cascade="all, delete-orphan")
    overtime_rules = relationship("OvertimeRulesDB", back_populates="agreement", cascade="all, delete-orphan")
    leave_entitlements = relationship("LeaveEntitlementDB", back_populates="agreement", cascade="all, delete-orphan")
    notice_periods = relationship("NoticePeriodsDB", back_populates="agreement", cascade="all, delete-orphan")
    special_allowances = relationship("SpecialAllowanceDB", back_populates="agreement", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_ccnl_agreements_sector_valid', 'sector_code', 'valid_from', 'valid_to'),
        Index('idx_ccnl_agreements_dates', 'valid_from', 'valid_to'),
    )
    
    def is_currently_valid(self) -> bool:
        """Check if CCNL agreement is currently valid."""
        today = date.today()
        if today < self.valid_from:
            return False
        if self.valid_to and today > self.valid_to:
            return False
        return True
    
    def get_levels_by_category(self, category: str) -> List["JobLevelDB"]:
        """Get all job levels for a specific worker category."""
        return [level for level in self.job_levels if level.worker_category == category]
    
    def get_salary_for_level(self, level_code: str, area: str = "nazionale") -> Optional["SalaryTableDB"]:
        """Get salary table for a specific level and geographic area."""
        for salary in self.salary_tables:
            if (salary.level_code == level_code and 
                salary.geographic_area == area and 
                salary.is_valid_on(date.today())):
                return salary
        return None
    
    def get_allowances_for_level(self, level_code: str) -> List["SpecialAllowanceDB"]:
        """Get applicable allowances for a job level."""
        applicable = []
        for allowance in self.special_allowances:
            if (not allowance.applicable_job_levels or 
                level_code in allowance.applicable_job_levels):
                applicable.append(allowance)
        return applicable


class JobLevelDB(Base):
    """Database model for job levels within CCNL agreements."""
    
    __tablename__ = "ccnl_job_levels"
    
    id = Column(Integer, primary_key=True)
    agreement_id = Column(Integer, ForeignKey('ccnl_agreements.id'), nullable=False)
    level_code = Column(String(10), nullable=False)
    level_name = Column(String(200), nullable=False)
    worker_category = Column(String(20), nullable=False)  # operaio, impiegato, quadro, dirigente
    description = Column(Text, nullable=True)
    minimum_experience_months = Column(Integer, default=0)
    required_qualifications = Column(JSON, default=list)
    typical_tasks = Column(JSON, default=list)
    decision_making_level = Column(String(50), nullable=True)
    supervision_responsibilities = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("CCNLAgreementDB", back_populates="job_levels")
    
    # Indexes
    __table_args__ = (
        Index('idx_job_levels_agreement_code', 'agreement_id', 'level_code'),
        Index('idx_job_levels_category', 'worker_category'),
    )
    
    def is_lower_than(self, other: "JobLevelDB") -> bool:
        """Check if this level is lower than another."""
        return self.level_code < other.level_code
    
    def is_higher_than(self, other: "JobLevelDB") -> bool:
        """Check if this level is higher than another."""
        return self.level_code > other.level_code
    
    def is_higher_category_than(self, other: "JobLevelDB") -> bool:
        """Check if this level is in a higher category than another."""
        category_hierarchy = {
            "operaio": 1, "apprendista": 1, "impiegato": 2, 
            "quadro": 3, "dirigente": 4
        }
        return (category_hierarchy.get(self.worker_category, 1) > 
                category_hierarchy.get(other.worker_category, 1))


class SalaryTableDB(Base):
    """Database model for salary tables."""
    
    __tablename__ = "ccnl_salary_tables"
    
    id = Column(Integer, primary_key=True)
    agreement_id = Column(Integer, ForeignKey('ccnl_agreements.id'), nullable=False)
    level_code = Column(String(10), nullable=False)
    base_monthly_salary = Column(Numeric(10, 2), nullable=False)
    geographic_area = Column(String(20), default="nazionale")  # nazionale, nord, centro, sud, sud_isole
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    thirteenth_month = Column(Boolean, default=True)
    fourteenth_month = Column(Boolean, default=False)
    additional_allowances = Column(JSON, default=dict)  # Dict of allowance_name -> amount
    company_size_adjustments = Column(JSON, default=dict)  # Dict of size -> adjustment_amount
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("CCNLAgreementDB", back_populates="salary_tables")
    
    # Indexes
    __table_args__ = (
        Index('idx_salary_tables_agreement_level', 'agreement_id', 'level_code', 'geographic_area'),
        Index('idx_salary_tables_dates', 'valid_from', 'valid_to'),
        CheckConstraint('base_monthly_salary > 0', name='positive_salary'),
    )
    
    def is_valid_on(self, check_date: date) -> bool:
        """Check if salary table is valid on a specific date."""
        if self.valid_from and check_date < self.valid_from:
            return False
        if self.valid_to and check_date > self.valid_to:
            return False
        return True
    
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


class WorkingHoursDB(Base):
    """Database model for working hours configurations."""
    
    __tablename__ = "ccnl_working_hours"
    
    id = Column(Integer, primary_key=True)
    agreement_id = Column(Integer, ForeignKey('ccnl_agreements.id'), nullable=False)
    ordinary_weekly_hours = Column(Integer, nullable=False)
    maximum_weekly_hours = Column(Integer, default=48)
    daily_rest_hours = Column(Integer, default=11)
    weekly_rest_hours = Column(Integer, default=24)
    flexible_hours_allowed = Column(Boolean, default=False)
    flexible_hours_range_min = Column(Integer, nullable=True)
    flexible_hours_range_max = Column(Integer, nullable=True)
    core_hours_start = Column(String(5), nullable=True)  # "09:00"
    core_hours_end = Column(String(5), nullable=True)    # "17:00"
    part_time_allowed = Column(Boolean, default=True)
    minimum_part_time_hours = Column(Integer, nullable=True)
    shift_work_allowed = Column(Boolean, default=False)
    shift_patterns = Column(JSON, default=list)
    night_shift_allowance = Column(Numeric(6, 2), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("CCNLAgreementDB", back_populates="working_hours")
    
    # Indexes
    __table_args__ = (
        Index('idx_working_hours_agreement', 'agreement_id'),
        CheckConstraint('ordinary_weekly_hours > 0', name='positive_weekly_hours'),
        CheckConstraint('maximum_weekly_hours >= ordinary_weekly_hours', name='max_hours_valid'),
    )
    
    def get_ordinary_daily_hours(self) -> float:
        """Get ordinary daily hours (assuming 5-day work week)."""
        return self.ordinary_weekly_hours / 5.0


class OvertimeRulesDB(Base):
    """Database model for overtime rules and compensation."""
    
    __tablename__ = "ccnl_overtime_rules"
    
    id = Column(Integer, primary_key=True)
    agreement_id = Column(Integer, ForeignKey('ccnl_agreements.id'), nullable=False)
    daily_threshold_hours = Column(Integer, default=8)
    weekly_threshold_hours = Column(Integer, default=40)
    daily_overtime_rate = Column(Numeric(4, 2), default=Decimal('1.25'))
    weekend_rate = Column(Numeric(4, 2), default=Decimal('1.50'))
    holiday_rate = Column(Numeric(4, 2), default=Decimal('2.00'))
    maximum_daily_overtime = Column(Integer, nullable=True)
    maximum_weekly_overtime = Column(Integer, nullable=True)
    maximum_monthly_overtime = Column(Integer, nullable=True)
    maximum_annual_overtime = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("CCNLAgreementDB", back_populates="overtime_rules")
    
    # Indexes
    __table_args__ = (
        Index('idx_overtime_rules_agreement', 'agreement_id'),
        CheckConstraint('daily_overtime_rate >= 1.0', name='valid_overtime_rate'),
    )
    
    def calculate_overtime_pay(self, base_hourly_rate: Decimal, overtime_hours: int) -> Decimal:
        """Calculate overtime compensation."""
        return base_hourly_rate * self.daily_overtime_rate * overtime_hours
    
    def is_overtime_allowed(self, daily_hours: int, weekly_total: int) -> bool:
        """Check if overtime is allowed given daily and weekly totals."""
        if self.maximum_daily_overtime and daily_hours > self.maximum_daily_overtime:
            return False
        if self.maximum_weekly_overtime and weekly_total > self.maximum_weekly_overtime:
            return False
        return True


class LeaveEntitlementDB(Base):
    """Database model for leave entitlements."""
    
    __tablename__ = "ccnl_leave_entitlements"
    
    id = Column(Integer, primary_key=True)
    agreement_id = Column(Integer, ForeignKey('ccnl_agreements.id'), nullable=False)
    leave_type = Column(String(50), nullable=False)  # ferie, permessi_retribuiti, etc.
    base_annual_days = Column(Integer, nullable=True)
    base_annual_hours = Column(Integer, nullable=True)
    seniority_bonus_schedule = Column(JSON, default=dict)  # months_seniority -> bonus_days
    calculation_method = Column(String(20), default="annual")
    minimum_usage_hours = Column(Integer, nullable=True)
    advance_notice_hours = Column(Integer, nullable=True)
    compensation_percentage = Column(Numeric(4, 2), default=Decimal('1.00'))
    mandatory_period = Column(Boolean, default=False)
    additional_optional_days = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("CCNLAgreementDB", back_populates="leave_entitlements")
    
    # Indexes
    __table_args__ = (
        Index('idx_leave_entitlements_agreement_type', 'agreement_id', 'leave_type'),
        CheckConstraint('compensation_percentage >= 0 AND compensation_percentage <= 1', name='valid_compensation'),
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


class NoticePeriodsDB(Base):
    """Database model for notice period requirements."""
    
    __tablename__ = "ccnl_notice_periods"
    
    id = Column(Integer, primary_key=True)
    agreement_id = Column(Integer, ForeignKey('ccnl_agreements.id'), nullable=False)
    worker_category = Column(String(20), nullable=False)
    seniority_months_min = Column(Integer, nullable=False)
    seniority_months_max = Column(Integer, nullable=False)
    notice_days = Column(Integer, nullable=False)
    termination_by = Column(String(10), default="both")  # employer, employee, both
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("CCNLAgreementDB", back_populates="notice_periods")
    
    # Indexes
    __table_args__ = (
        Index('idx_notice_periods_agreement_category', 'agreement_id', 'worker_category'),
        CheckConstraint('seniority_months_max >= seniority_months_min', name='valid_seniority_range'),
        CheckConstraint('notice_days > 0', name='positive_notice_days'),
    )
    
    def applies_to_seniority(self, months_seniority: int) -> bool:
        """Check if this notice period applies to given seniority."""
        return self.seniority_months_min <= months_seniority <= self.seniority_months_max


class SpecialAllowanceDB(Base):
    """Database model for special allowances and benefits."""
    
    __tablename__ = "ccnl_special_allowances"
    
    id = Column(Integer, primary_key=True)
    agreement_id = Column(Integer, ForeignKey('ccnl_agreements.id'), nullable=False)
    allowance_type = Column(String(50), nullable=False)  # buoni_pasto, indennita_trasporto, etc.
    amount = Column(Numeric(8, 2), nullable=False)
    frequency = Column(String(10), nullable=False)  # daily, monthly, annual
    conditions = Column(JSON, default=list)
    applicable_job_levels = Column(JSON, default=list)
    geographic_areas = Column(JSON, default=list)  # Empty list means national
    company_sizes = Column(JSON, default=list)     # Empty list means all sizes
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("CCNLAgreementDB", back_populates="special_allowances")
    
    # Indexes
    __table_args__ = (
        Index('idx_special_allowances_agreement_type', 'agreement_id', 'allowance_type'),
        CheckConstraint('amount > 0', name='positive_allowance_amount'),
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