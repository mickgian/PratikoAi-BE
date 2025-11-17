"""CCNL Calculation Engine - Enhanced calculator for Italian Collective Labor Agreements.

This module provides comprehensive business logic for CCNL-related calculations
including salary computations, leave calculations, notice periods, and complex
scenario analysis.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.models.ccnl_data import (
    AllowanceType,
    CCNLAgreement,
    CCNLCalculator,
    CCNLSector,
    CompanySize,
    GeographicArea,
    JobLevel,
    LeaveEntitlement,
    LeaveType,
    NoticePerioD,
    OvertimeRules,
    SalaryTable,
    SpecialAllowance,
    TFRRules,
    WorkerCategory,
    WorkingHours,
)
from app.services.validators.italian_tax_calculator import ItalianTaxCalculator


class CalculationPeriod(str, Enum):
    """Time periods for calculations."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


@dataclass
class CompensationBreakdown:
    """Detailed compensation breakdown."""

    base_salary: Decimal
    thirteenth_month: Decimal
    fourteenth_month: Decimal
    overtime: Decimal
    allowances: dict[str, Decimal]
    deductions: dict[str, Decimal]
    net_total: Decimal
    gross_total: Decimal
    period: CalculationPeriod
    currency: str = "EUR"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "base_salary": float(self.base_salary),
            "thirteenth_month": float(self.thirteenth_month),
            "fourteenth_month": float(self.fourteenth_month),
            "overtime": float(self.overtime),
            "allowances": {k: float(v) for k, v in self.allowances.items()},
            "deductions": {k: float(v) for k, v in self.deductions.items()},
            "net_total": float(self.net_total),
            "gross_total": float(self.gross_total),
            "period": self.period.value,
            "currency": self.currency,
        }


@dataclass
class LeaveBalance:
    """Leave balance and accrual information."""

    leave_type: LeaveType
    annual_entitlement: int
    used_days: int
    remaining_days: int
    accrual_rate: float  # Days per month
    monetary_value: Decimal | None = None
    expiry_date: date | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "leave_type": self.leave_type.value,
            "annual_entitlement": self.annual_entitlement,
            "used_days": self.used_days,
            "remaining_days": self.remaining_days,
            "accrual_rate": self.accrual_rate,
            "monetary_value": float(self.monetary_value) if self.monetary_value else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
        }


@dataclass
class SeniorityBenefits:
    """Benefits based on seniority."""

    seniority_months: int
    seniority_years: float
    notice_period_days: int
    severance_pay_months: float
    additional_leave_days: int
    salary_increases: Decimal

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "seniority_months": self.seniority_months,
            "seniority_years": self.seniority_years,
            "notice_period_days": self.notice_period_days,
            "severance_pay_months": float(self.severance_pay_months),
            "additional_leave_days": self.additional_leave_days,
            "salary_increases": float(self.salary_increases),
        }


@dataclass
class NetSalaryCalculation:
    """Net salary calculation with Italian tax breakdown."""

    gross_monthly_salary: Decimal
    irpef_tax: Decimal
    inps_employee: Decimal
    inail_employee: Decimal
    regional_tax: Decimal
    municipal_tax: Decimal
    total_deductions: Decimal
    net_monthly_salary: Decimal
    effective_tax_rate: Decimal

    # Additional components
    thirteenth_month_net: Decimal | None = None
    fourteenth_month_net: Decimal | None = None
    holiday_allowance: Decimal | None = None


@dataclass
class HolidayAccrual:
    """Holiday/vacation accrual calculation."""

    accrual_period_start: date
    accrual_period_end: date
    base_annual_days: int
    seniority_bonus_days: int
    total_annual_entitlement: int
    months_worked: int
    accrued_days: Decimal
    used_days: int
    remaining_days: Decimal
    monetary_value_per_day: Decimal
    total_monetary_value: Decimal


@dataclass
class OvertimeCalculation:
    """Overtime compensation calculation."""

    regular_hours: int
    overtime_hours: int
    hourly_base_rate: Decimal
    overtime_rate: Decimal  # e.g., 1.25 for 25% premium
    overtime_premium: Decimal
    total_overtime_pay: Decimal
    weekend_hours: int = 0
    weekend_premium: Decimal = Decimal("0.00")
    holiday_hours: int = 0
    holiday_premium: Decimal = Decimal("0.00")
    total_premium_pay: Decimal = Decimal("0.00")


@dataclass
class TFRAccrual:
    """TFR (Severance) accrual calculation."""

    monthly_salary_basis: Decimal
    annual_accrual: Decimal
    total_service_months: int
    accumulated_tfr: Decimal
    revaluation_rate: Decimal  # Annual inflation + 1.5%
    advance_eligible_amount: Decimal | None = None  # 70% after 8 years
    monthly_accrual: Decimal = Decimal("0.00")


@dataclass
class MaternityPaternityLeave:
    """Maternity/Paternity leave calculation."""

    leave_type: str  # "maternity", "paternity", "parental"
    total_entitled_days: int
    paid_days: int
    unpaid_days: int
    compensation_rate: Decimal  # Usually 80% for maternity, 100% for paternity
    daily_compensation: Decimal
    total_compensation: Decimal
    inps_contribution: Decimal
    start_date: date | None = None
    end_date: date | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "seniority_months": self.seniority_months,
            "seniority_years": self.seniority_years,
            "notice_period_days": self.notice_period_days,
            "severance_pay_months": self.severance_pay_months,
            "additional_leave_days": self.additional_leave_days,
            "salary_increases": float(self.salary_increases),
        }


@dataclass
class CCNLComparisonDetail:
    """Detailed comparison between CCNLs."""

    aspect: str
    ccnl1_value: Any
    ccnl2_value: Any
    difference: Any
    percentage_difference: float | None = None
    favors_ccnl: int | None = None  # 1 or 2

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "aspect": self.aspect,
            "ccnl1_value": self.ccnl1_value,
            "ccnl2_value": self.ccnl2_value,
            "difference": self.difference,
            "percentage_difference": self.percentage_difference,
            "favors_ccnl": self.favors_ccnl,
        }


class EnhancedCCNLCalculator(CCNLCalculator):
    """Enhanced CCNL calculator with comprehensive calculation capabilities."""

    def __init__(self, ccnl: CCNLAgreement):
        """Initialize enhanced calculator."""
        super().__init__(ccnl)
        self.logger = logger

    # Enhanced Compensation Calculations

    def calculate_comprehensive_compensation(
        self,
        level_code: str,
        seniority_months: int = 0,
        geographic_area: GeographicArea = GeographicArea.NAZIONALE,
        company_size: CompanySize | None = None,
        working_days_per_month: int = 22,
        overtime_hours_monthly: int = 0,
        include_allowances: bool = True,
        period: CalculationPeriod = CalculationPeriod.ANNUAL,
    ) -> CompensationBreakdown:
        """Calculate comprehensive compensation with all components."""
        try:
            # Get base salary table
            salary_table = self.ccnl.get_salary_for_level(level_code, geographic_area)
            if not salary_table:
                return self._empty_compensation_breakdown(period)

            # Calculate base components
            base_monthly = salary_table.base_monthly_salary

            # Apply company size adjustments if applicable
            if company_size and company_size in salary_table.company_size_adjustments:
                adjustment = salary_table.company_size_adjustments[company_size]
                base_monthly += adjustment

            # Calculate annual base
            annual_base = base_monthly * 12

            # Calculate 13th and 14th month
            thirteenth = base_monthly if salary_table.thirteenth_month else Decimal("0")
            fourteenth = base_monthly if salary_table.fourteenth_month else Decimal("0")

            # Calculate overtime
            overtime_pay = Decimal("0")
            if overtime_hours_monthly > 0 and self.ccnl.overtime_rules:
                hourly_rate = self._calculate_hourly_rate(base_monthly, working_days_per_month)
                overtime_pay = self.calculate_overtime_pay(hourly_rate, overtime_hours_monthly) * 12  # Annual

            # Calculate allowances
            allowances = {}
            total_allowances = Decimal("0")

            if include_allowances:
                applicable_allowances = self._get_applicable_allowances(level_code, geographic_area, company_size)

                for allowance in applicable_allowances:
                    monthly_amount = allowance.get_monthly_amount(working_days_per_month)
                    annual_amount = monthly_amount * 12
                    allowances[allowance.allowance_type.italian_name()] = annual_amount
                    total_allowances += annual_amount

            # Calculate gross total
            gross_total = annual_base + thirteenth + fourteenth + overtime_pay + total_allowances

            # Estimate deductions (simplified - actual would need tax tables)
            deductions = self._estimate_deductions(gross_total)
            total_deductions = sum(deductions.values())

            # Calculate net total
            net_total = gross_total - total_deductions

            # Create breakdown
            breakdown = CompensationBreakdown(
                base_salary=annual_base,
                thirteenth_month=thirteenth,
                fourteenth_month=fourteenth,
                overtime=overtime_pay,
                allowances=allowances,
                deductions=deductions,
                net_total=net_total,
                gross_total=gross_total,
                period=CalculationPeriod.ANNUAL,
            )

            # Convert to requested period
            if period != CalculationPeriod.ANNUAL:
                breakdown = self._convert_compensation_period(breakdown, period)

            return breakdown

        except Exception as e:
            self.logger.error(f"Error calculating comprehensive compensation: {e}")
            return self._empty_compensation_breakdown(period)

    def _calculate_hourly_rate(self, monthly_salary: Decimal, working_days: int = 22) -> Decimal:
        """Calculate hourly rate from monthly salary."""
        if self.ccnl.working_hours:
            weekly_hours = self.ccnl.working_hours.ordinary_weekly_hours
            monthly_hours = (weekly_hours / 5) * working_days  # Assuming 5-day week
        else:
            monthly_hours = 8 * working_days  # Default 8 hours/day

        return (monthly_salary / Decimal(str(monthly_hours))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _get_applicable_allowances(
        self, level_code: str, geographic_area: GeographicArea, company_size: CompanySize | None = None
    ) -> list[SpecialAllowance]:
        """Get allowances applicable to specific conditions."""
        applicable = []

        for allowance in self.ccnl.special_allowances:
            # Check job level
            if allowance.job_levels and level_code not in allowance.job_levels:
                continue

            # Check geographic area
            if allowance.geographic_areas and not allowance.applies_to_area(geographic_area):
                continue

            # Check company size
            if allowance.company_sizes and company_size not in allowance.company_sizes:
                continue

            applicable.append(allowance)

        return applicable

    def _estimate_deductions(self, gross_annual: Decimal) -> dict[str, Decimal]:
        """Estimate tax and social security deductions (simplified)."""
        deductions = {}

        # Social security (approximately 9.19% for employees)
        deductions["Contributi INPS"] = (gross_annual * Decimal("0.0919")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Income tax (IRPEF) - simplified progressive calculation
        irpef = self._calculate_irpef(gross_annual)
        deductions["IRPEF"] = irpef

        # Regional tax (approximately 1.23%)
        deductions["Addizionale Regionale"] = (gross_annual * Decimal("0.0123")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Municipal tax (approximately 0.8%)
        deductions["Addizionale Comunale"] = (gross_annual * Decimal("0.008")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return deductions

    def _calculate_irpef(self, gross_annual: Decimal) -> Decimal:
        """Calculate IRPEF (simplified tax brackets as of 2024)."""
        irpef = Decimal("0")

        # Tax brackets (simplified)
        if gross_annual <= 15000:
            irpef = gross_annual * Decimal("0.23")
        elif gross_annual <= 28000:
            irpef = Decimal("3450") + (gross_annual - 15000) * Decimal("0.25")
        elif gross_annual <= 50000:
            irpef = Decimal("6700") + (gross_annual - 28000) * Decimal("0.35")
        else:
            irpef = Decimal("14400") + (gross_annual - 50000) * Decimal("0.43")

        return irpef.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _convert_compensation_period(
        self, breakdown: CompensationBreakdown, target_period: CalculationPeriod
    ) -> CompensationBreakdown:
        """Convert compensation breakdown to different period."""
        # Conversion factors from annual
        factors = {
            CalculationPeriod.DAILY: Decimal("365"),
            CalculationPeriod.WEEKLY: Decimal("52"),
            CalculationPeriod.MONTHLY: Decimal("12"),
            CalculationPeriod.QUARTERLY: Decimal("4"),
            CalculationPeriod.ANNUAL: Decimal("1"),
        }

        factor = factors[target_period]

        return CompensationBreakdown(
            base_salary=(breakdown.base_salary / factor).quantize(Decimal("0.01")),
            thirteenth_month=(breakdown.thirteenth_month / factor).quantize(Decimal("0.01")),
            fourteenth_month=(breakdown.fourteenth_month / factor).quantize(Decimal("0.01")),
            overtime=(breakdown.overtime / factor).quantize(Decimal("0.01")),
            allowances={k: (v / factor).quantize(Decimal("0.01")) for k, v in breakdown.allowances.items()},
            deductions={k: (v / factor).quantize(Decimal("0.01")) for k, v in breakdown.deductions.items()},
            net_total=(breakdown.net_total / factor).quantize(Decimal("0.01")),
            gross_total=(breakdown.gross_total / factor).quantize(Decimal("0.01")),
            period=target_period,
            currency=breakdown.currency,
        )

    def _empty_compensation_breakdown(self, period: CalculationPeriod) -> CompensationBreakdown:
        """Create empty compensation breakdown."""
        return CompensationBreakdown(
            base_salary=Decimal("0"),
            thirteenth_month=Decimal("0"),
            fourteenth_month=Decimal("0"),
            overtime=Decimal("0"),
            allowances={},
            deductions={},
            net_total=Decimal("0"),
            gross_total=Decimal("0"),
            period=period,
        )

    # Enhanced Leave Calculations

    def calculate_leave_balances(
        self, seniority_months: int, used_days: dict[LeaveType, int] = None, calculation_date: date | None = None
    ) -> list[LeaveBalance]:
        """Calculate all leave balances for an employee."""
        if used_days is None:
            used_days = {}

        if calculation_date is None:
            calculation_date = date.today()

        balances = []

        for leave_entitlement in self.ccnl.leave_entitlements:
            # Get annual entitlement
            annual_days = leave_entitlement.get_annual_entitlement(seniority_months)

            # Get used days
            used = used_days.get(leave_entitlement.leave_type, 0)

            # Calculate remaining
            remaining = annual_days - used

            # Calculate accrual rate
            accrual_rate = leave_entitlement.get_monthly_accrual()

            # Calculate monetary value if applicable
            monetary_value = None
            if leave_entitlement.compensation_percentage != Decimal("1.00"):
                # Leave has different compensation rate
                monetary_value = self._calculate_leave_monetary_value(leave_entitlement.leave_type, remaining)

            # Determine expiry date
            expiry_date = self._calculate_leave_expiry(leave_entitlement.leave_type, calculation_date)

            balance = LeaveBalance(
                leave_type=leave_entitlement.leave_type,
                annual_entitlement=annual_days,
                used_days=used,
                remaining_days=remaining,
                accrual_rate=accrual_rate,
                monetary_value=monetary_value,
                expiry_date=expiry_date,
            )

            balances.append(balance)

        return balances

    def _calculate_leave_monetary_value(self, leave_type: LeaveType, days: int) -> Decimal:
        """Calculate monetary value of unused leave days."""
        # This is a simplified calculation
        # In reality, this would depend on specific CCNL rules
        return Decimal("0")  # Placeholder

    def _calculate_leave_expiry(self, leave_type: LeaveType, calculation_date: date) -> date | None:
        """Calculate when leave expires."""
        # Most leave expires at end of year + grace period
        if leave_type == LeaveType.FERIE:
            # Vacation typically expires June 30 of following year
            return date(calculation_date.year + 1, 6, 30)
        elif leave_type == LeaveType.PERMESSI_RETRIBUITI:
            # Paid leave typically expires end of year
            return date(calculation_date.year, 12, 31)
        return None

    # Enhanced Seniority Calculations

    def calculate_seniority_benefits(
        self, worker_category: WorkerCategory, hire_date: date, calculation_date: date | None = None
    ) -> SeniorityBenefits:
        """Calculate all benefits based on seniority."""
        if calculation_date is None:
            calculation_date = date.today()

        # Calculate seniority
        seniority_months = self._calculate_months_between(hire_date, calculation_date)
        seniority_years = seniority_months / 12

        # Get notice period
        notice_days = self.get_notice_period(worker_category, seniority_months) or 0

        # Calculate severance pay (TFR - Trattamento di Fine Rapporto)
        severance_months = self._calculate_severance_pay_months(seniority_years)

        # Calculate additional leave days from seniority
        additional_leave = 0
        for leave in self.ccnl.leave_entitlements:
            if leave.leave_type == LeaveType.FERIE:
                base_days = leave.base_annual_days or 0
                total_days = leave.get_annual_entitlement(seniority_months)
                additional_leave = total_days - base_days
                break

        # Calculate salary increases from seniority (simplified)
        salary_increases = self._calculate_seniority_salary_increases(worker_category, seniority_years)

        return SeniorityBenefits(
            seniority_months=seniority_months,
            seniority_years=round(seniority_years, 2),
            notice_period_days=notice_days,
            severance_pay_months=severance_months,
            additional_leave_days=additional_leave,
            salary_increases=salary_increases,
        )

    def _calculate_months_between(self, start_date: date, end_date: date) -> int:
        """Calculate months between two dates."""
        months = (end_date.year - start_date.year) * 12
        months += end_date.month - start_date.month
        if end_date.day < start_date.day:
            months -= 1
        return max(0, months)

    def _calculate_severance_pay_months(self, years: float) -> float:
        """Calculate severance pay in months of salary."""
        # Italian TFR is approximately 1 month per year of service
        return round(years, 2)

    def _calculate_seniority_salary_increases(self, worker_category: WorkerCategory, years: float) -> Decimal:
        """Calculate salary increases from seniority (simplified)."""
        # This is highly CCNL-specific
        # Simplified: 2% increase every 3 years
        increases = int(years / 3) * Decimal("0.02")
        return increases

    # Geographic Difference Calculations

    def calculate_geographic_differences(
        self, level_code: str, base_area: GeographicArea = GeographicArea.NAZIONALE
    ) -> dict[str, dict[str, Any]]:
        """Calculate salary differences across geographic areas."""
        differences = {}

        # Get base salary
        base_salary_table = self.ccnl.get_salary_for_level(level_code, base_area)
        if not base_salary_table:
            return differences

        base_salary = base_salary_table.base_monthly_salary

        # Compare with other areas
        for area in GeographicArea:
            if area == base_area:
                continue

            area_salary_table = self.ccnl.get_salary_for_level(level_code, area)
            if area_salary_table:
                area_salary = area_salary_table.base_monthly_salary
                difference = area_salary - base_salary
                percentage = (difference / base_salary * 100) if base_salary > 0 else 0

                differences[area.value] = {
                    "monthly_salary": float(area_salary),
                    "difference": float(difference),
                    "percentage_difference": round(float(percentage), 2),
                    "annual_difference": float(difference * 12),
                }

        return differences

    # Overtime Calculations

    def calculate_overtime_scenarios(
        self, base_monthly_salary: Decimal, working_days: int = 22
    ) -> dict[str, dict[str, Any]]:
        """Calculate various overtime scenarios."""
        if not self.ccnl.overtime_rules:
            return {}

        hourly_rate = self._calculate_hourly_rate(base_monthly_salary, working_days)

        scenarios = {
            "weekday_overtime": {
                "rate_multiplier": float(self.ccnl.overtime_rules.daily_overtime_rate),
                "hourly_rate": float(hourly_rate * self.ccnl.overtime_rules.daily_overtime_rate),
                "examples": {
                    "1_hour": float(self.calculate_overtime_pay(hourly_rate, 1)),
                    "5_hours": float(self.calculate_overtime_pay(hourly_rate, 5)),
                    "10_hours": float(self.calculate_overtime_pay(hourly_rate, 10)),
                },
            },
            "weekend_overtime": {
                "rate_multiplier": float(self.ccnl.overtime_rules.weekend_rate),
                "hourly_rate": float(hourly_rate * self.ccnl.overtime_rules.weekend_rate),
                "examples": {
                    "1_hour": float(self.calculate_overtime_pay(hourly_rate, 1, is_weekend=True)),
                    "5_hours": float(self.calculate_overtime_pay(hourly_rate, 5, is_weekend=True)),
                    "10_hours": float(self.calculate_overtime_pay(hourly_rate, 10, is_weekend=True)),
                },
            },
            "holiday_overtime": {
                "rate_multiplier": float(self.ccnl.overtime_rules.holiday_rate),
                "hourly_rate": float(hourly_rate * self.ccnl.overtime_rules.holiday_rate),
                "examples": {
                    "1_hour": float(self.calculate_overtime_pay(hourly_rate, 1, is_holiday=True)),
                    "5_hours": float(self.calculate_overtime_pay(hourly_rate, 5, is_holiday=True)),
                    "10_hours": float(self.calculate_overtime_pay(hourly_rate, 10, is_holiday=True)),
                },
            },
        }

        # Add limits if defined
        if self.ccnl.overtime_rules.maximum_daily_overtime:
            scenarios["limits"] = {
                "daily_max": self.ccnl.overtime_rules.maximum_daily_overtime,
                "weekly_max": self.ccnl.overtime_rules.maximum_weekly_overtime,
                "monthly_max": self.ccnl.overtime_rules.maximum_monthly_overtime,
                "annual_max": self.ccnl.overtime_rules.maximum_annual_overtime,
            }

        return scenarios

    # Comparison Calculations

    def compare_with_other_ccnl(
        self, other_ccnl: CCNLAgreement, level_code: str, comparison_aspects: list[str] = None
    ) -> list[CCNLComparisonDetail]:
        """Compare provisions with another CCNL."""
        if comparison_aspects is None:
            comparison_aspects = ["salary", "leave", "notice_period", "overtime"]

        comparisons = []

        # Compare salaries
        if "salary" in comparison_aspects:
            salary1 = self.ccnl.get_salary_for_level(level_code)
            salary2 = other_ccnl.get_salary_for_level(level_code)

            if salary1 and salary2:
                diff = salary1.base_monthly_salary - salary2.base_monthly_salary
                pct_diff = (diff / salary2.base_monthly_salary * 100) if salary2.base_monthly_salary > 0 else 0

                comparisons.append(
                    CCNLComparisonDetail(
                        aspect="Monthly Base Salary",
                        ccnl1_value=float(salary1.base_monthly_salary),
                        ccnl2_value=float(salary2.base_monthly_salary),
                        difference=float(diff),
                        percentage_difference=round(float(pct_diff), 2),
                        favors_ccnl=1 if diff > 0 else 2,
                    )
                )

        # Compare leave entitlements
        if "leave" in comparison_aspects:
            for leave_type in LeaveType:
                leave1 = self.calculate_annual_leave(leave_type, 0)
                leave2 = CCNLCalculator(other_ccnl).calculate_annual_leave(leave_type, 0)

                if leave1 is not None and leave2 is not None:
                    diff = leave1 - leave2
                    comparisons.append(
                        CCNLComparisonDetail(
                            aspect=f"{leave_type.italian_name()} (days)",
                            ccnl1_value=leave1,
                            ccnl2_value=leave2,
                            difference=diff,
                            favors_ccnl=1 if diff > 0 else 2,
                        )
                    )

        return comparisons

    # Complex Scenario Calculations

    def calculate_career_progression(
        self,
        starting_level: str,
        progression_path: list[tuple[str, int]],  # [(level, months_at_level), ...]
        starting_date: date,
    ) -> dict[str, Any]:
        """Calculate compensation over a career progression path."""
        progression_data = []
        current_date = starting_date
        cumulative_earnings = Decimal("0")

        for level_code, months in progression_path:
            # Get salary for this level
            salary_table = self.ccnl.get_salary_for_level(level_code)
            if not salary_table:
                continue

            # Calculate earnings for this period
            monthly_salary = salary_table.base_monthly_salary
            period_earnings = monthly_salary * Decimal(str(months))

            # Add 13th/14th months proportionally
            if salary_table.thirteenth_month:
                period_earnings += monthly_salary * (Decimal(str(months)) / Decimal("12"))
            if salary_table.fourteenth_month:
                period_earnings += monthly_salary * (Decimal(str(months)) / Decimal("12"))

            cumulative_earnings += period_earnings

            # Calculate end date for this level
            end_date = current_date + timedelta(days=30 * months)  # Approximate

            progression_data.append(
                {
                    "level": level_code,
                    "start_date": current_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "months": months,
                    "monthly_salary": float(monthly_salary),
                    "period_earnings": float(period_earnings),
                    "cumulative_earnings": float(cumulative_earnings),
                }
            )

            current_date = end_date

        total_months = sum(months for _, months in progression_path)
        return {
            "progression_path": progression_data,
            "total_months": total_months,
            "total_earnings": float(cumulative_earnings),
            "average_monthly": float(cumulative_earnings / Decimal(str(total_months))),
        }

    def answer_complex_query(
        self,
        level_code: str,
        worker_category: WorkerCategory,
        geographic_area: GeographicArea,
        seniority_years: int,
        include_all_benefits: bool = True,
    ) -> dict[str, Any]:
        """Answer complex queries like 'What would be the total compensation for a C2 level
        metalworker in Northern Italy with 5 years of experience including all allowances
        and leave entitlements?'
        """
        seniority_months = seniority_years * 12

        # Calculate comprehensive compensation
        compensation = self.calculate_comprehensive_compensation(
            level_code=level_code,
            seniority_months=seniority_months,
            geographic_area=geographic_area,
            include_allowances=include_all_benefits,
        )

        # Calculate leave balances
        leave_balances = self.calculate_leave_balances(seniority_months)

        # Calculate seniority benefits
        hire_date = date.today() - timedelta(days=365 * seniority_years)
        seniority_benefits = self.calculate_seniority_benefits(worker_category=worker_category, hire_date=hire_date)

        # Get working hours
        working_hours_info = None
        if self.ccnl.working_hours:
            working_hours_info = {
                "weekly_hours": self.ccnl.working_hours.ordinary_weekly_hours,
                "daily_hours": self.ccnl.working_hours.get_ordinary_daily_hours(),
                "flexible_hours": self.ccnl.working_hours.flexible_hours_allowed,
            }

        # Compile comprehensive answer
        return {
            "query_parameters": {
                "sector": self.ccnl.sector.italian_name(),
                "level": level_code,
                "worker_category": worker_category.italian_name(),
                "geographic_area": geographic_area.value,
                "seniority_years": seniority_years,
            },
            "compensation": compensation.to_dict(),
            "leave_entitlements": [balance.to_dict() for balance in leave_balances],
            "seniority_benefits": seniority_benefits.to_dict(),
            "working_hours": working_hours_info,
            "summary": {
                "annual_gross_total": float(compensation.gross_total),
                "annual_net_total": float(compensation.net_total),
                "monthly_gross": float(compensation.gross_total / 12),
                "monthly_net": float(compensation.net_total / 12),
                "total_leave_days": sum(b.annual_entitlement for b in leave_balances),
                "notice_period_days": seniority_benefits.notice_period_days,
            },
        }

    # Automatic Calculation Methods

    def calculate_net_salary_from_gross(
        self,
        gross_monthly_salary: Decimal,
        has_dependents: bool = False,
        additional_deductions: Decimal = Decimal("0.00"),
        year: int = 2024,
    ) -> NetSalaryCalculation:
        """Automatically calculate net salary from gross with Italian tax system."""
        try:
            # Initialize Italian tax calculator
            tax_calculator = ItalianTaxCalculator()

            # Calculate annual gross for tax purposes
            annual_gross = gross_monthly_salary * 12

            # Calculate IRPEF (Personal Income Tax)
            irpef_annual = tax_calculator.calculate_irpef(annual_gross)
            irpef_monthly = irpef_annual / 12

            # Calculate INPS employee contribution (9.19% for most employees)
            inps_rate = Decimal("0.0919")
            inps_monthly = gross_monthly_salary * inps_rate

            # Calculate INAIL employee contribution (varies, typically 0.3-0.5%)
            inail_rate = Decimal("0.004")
            inail_monthly = gross_monthly_salary * inail_rate

            # Regional tax (IRAP) - not typically deducted from employee
            regional_tax = Decimal("0.00")

            # Municipal tax - varies by city
            municipal_tax = Decimal("0.00")

            # Total deductions
            total_deductions = irpef_monthly + inps_monthly + inail_monthly + additional_deductions

            # Net salary
            net_monthly = gross_monthly_salary - total_deductions

            # Effective tax rate
            effective_rate = (
                (total_deductions / gross_monthly_salary * 100) if gross_monthly_salary > 0 else Decimal("0.00")
            )

            return NetSalaryCalculation(
                gross_monthly_salary=gross_monthly_salary,
                irpef_tax=irpef_monthly,
                inps_employee=inps_monthly,
                inail_employee=inail_monthly,
                regional_tax=regional_tax,
                municipal_tax=municipal_tax,
                total_deductions=total_deductions,
                net_monthly_salary=net_monthly,
                effective_tax_rate=effective_rate,
            )

        except Exception as e:
            self.logger.error(f"Error calculating net salary: {e}")
            return NetSalaryCalculation(
                gross_monthly_salary=gross_monthly_salary,
                irpef_tax=Decimal("0.00"),
                inps_employee=Decimal("0.00"),
                inail_employee=Decimal("0.00"),
                regional_tax=Decimal("0.00"),
                municipal_tax=Decimal("0.00"),
                total_deductions=Decimal("0.00"),
                net_monthly_salary=gross_monthly_salary,
                effective_tax_rate=Decimal("0.00"),
            )

    def calculate_holiday_accrual(
        self, hire_date: date, calculation_date: date = None, used_holiday_days: int = 0, seniority_months: int = None
    ) -> HolidayAccrual:
        """Automatically calculate holiday/vacation accrual."""
        try:
            if calculation_date is None:
                calculation_date = date.today()

            # Calculate seniority if not provided
            if seniority_months is None:
                seniority_months = int((calculation_date - hire_date).days / 30.44)  # Average month

            # Find vacation leave entitlement
            vacation_leave = None
            for leave in self.ccnl.leave_entitlements:
                if leave.leave_type == LeaveType.FERIE:
                    vacation_leave = leave
                    break

            if not vacation_leave:
                # Default Italian minimum
                base_days = 20
                seniority_bonus = 0
            else:
                base_days = vacation_leave.base_annual_days or 20
                seniority_bonus = vacation_leave.get_annual_entitlement(seniority_months) - base_days

            # Calculate accrual period
            year = calculation_date.year
            accrual_start = date(year, 1, 1)
            accrual_end = date(year, 12, 31)

            # If hired during the year, adjust start date
            if hire_date.year == year:
                accrual_start = hire_date

            # Calculate months worked in accrual period
            if calculation_date < accrual_end:
                accrual_end = calculation_date

            months_worked = int((accrual_end - accrual_start).days / 30.44)
            if months_worked > 12:
                months_worked = 12

            # Calculate accrued days (proportional to months worked)
            total_entitlement = base_days + seniority_bonus
            accrued_days = Decimal(str(total_entitlement * months_worked / 12))

            # Remaining days
            remaining_days = accrued_days - Decimal(str(used_holiday_days))

            # Calculate monetary value (average daily wage)
            salary_table = self.ccnl.get_salary_for_level(
                self.ccnl.job_levels[0].level_code if self.ccnl.job_levels else "DEFAULT"
            )

            if salary_table:
                daily_value = salary_table.base_monthly_salary * 12 / 260  # 260 working days/year
                total_value = remaining_days * daily_value
            else:
                daily_value = Decimal("0.00")
                total_value = Decimal("0.00")

            return HolidayAccrual(
                accrual_period_start=accrual_start,
                accrual_period_end=accrual_end,
                base_annual_days=base_days,
                seniority_bonus_days=seniority_bonus,
                total_annual_entitlement=total_entitlement,
                months_worked=months_worked,
                accrued_days=accrued_days,
                used_days=used_holiday_days,
                remaining_days=remaining_days,
                monetary_value_per_day=daily_value,
                total_monetary_value=total_value,
            )

        except Exception as e:
            self.logger.error(f"Error calculating holiday accrual: {e}")
            return self._empty_holiday_accrual()

    def calculate_notice_period_by_tenure(
        self, worker_category: WorkerCategory, hire_date: date, termination_date: date = None
    ) -> int:
        """Automatically calculate notice period based on tenure."""
        try:
            if termination_date is None:
                termination_date = date.today()

            # Calculate seniority in months
            seniority_months = int((termination_date - hire_date).days / 30.44)

            # Find applicable notice period
            for notice in self.ccnl.notice_periods:
                if notice.worker_category == worker_category and notice.applies_to_seniority(seniority_months):
                    return notice.notice_days

            # Default notice periods by category if not found in CCNL
            default_notice = {
                WorkerCategory.OPERAIO: 15,
                WorkerCategory.IMPIEGATO: 30,
                WorkerCategory.QUADRO: 60,
                WorkerCategory.DIRIGENTE: 90,
                WorkerCategory.APPRENDISTA: 15,
            }

            return default_notice.get(worker_category, 30)

        except Exception as e:
            self.logger.error(f"Error calculating notice period: {e}")
            return 30  # Default

    def calculate_overtime_compensation(
        self,
        base_hourly_rate: Decimal,
        regular_hours_worked: int,
        total_hours_worked: int,
        weekend_hours: int = 0,
        holiday_hours: int = 0,
        night_hours: int = 0,
    ) -> OvertimeCalculation:
        """Automatically calculate overtime compensation."""
        try:
            # Get overtime rules from CCNL
            overtime_rules = self.ccnl.overtime_rules
            if not overtime_rules:
                # Default Italian overtime rates
                daily_rate = Decimal("1.25")
                weekend_rate = Decimal("1.50")
                holiday_rate = Decimal("2.00")
            else:
                daily_rate = overtime_rules.daily_overtime_rate
                weekend_rate = overtime_rules.weekend_rate
                holiday_rate = overtime_rules.holiday_rate

            # Calculate overtime hours
            overtime_hours = max(0, total_hours_worked - regular_hours_worked)

            # Calculate premiums
            overtime_premium = base_hourly_rate * (daily_rate - Decimal("1.00")) * overtime_hours
            weekend_premium = base_hourly_rate * (weekend_rate - Decimal("1.00")) * weekend_hours
            holiday_premium = base_hourly_rate * (holiday_rate - Decimal("1.00")) * holiday_hours

            # Total overtime pay (base pay + premium)
            total_overtime_pay = base_hourly_rate * overtime_hours + overtime_premium
            total_premium_pay = overtime_premium + weekend_premium + holiday_premium

            return OvertimeCalculation(
                regular_hours=regular_hours_worked,
                overtime_hours=overtime_hours,
                hourly_base_rate=base_hourly_rate,
                overtime_rate=daily_rate,
                overtime_premium=overtime_premium,
                total_overtime_pay=total_overtime_pay,
                weekend_hours=weekend_hours,
                weekend_premium=weekend_premium,
                holiday_hours=holiday_hours,
                holiday_premium=holiday_premium,
                total_premium_pay=total_premium_pay,
            )

        except Exception as e:
            self.logger.error(f"Error calculating overtime: {e}")
            return self._empty_overtime_calculation()

    def calculate_thirteenth_fourteenth_month(
        self,
        level_code: str,
        months_worked: int = 12,
        bonus_included: bool = False,
        geographic_area: GeographicArea = GeographicArea.NAZIONALE,
    ) -> dict[str, Decimal]:
        """Calculate 13th and 14th month salary portions."""
        try:
            # Get salary table
            salary_table = self.ccnl.get_salary_for_level(level_code, geographic_area)
            if not salary_table:
                return {"thirteenth": Decimal("0.00"), "fourteenth": Decimal("0.00")}

            base_monthly = salary_table.base_monthly_salary

            # Calculate proportional amounts based on months worked
            thirteenth = Decimal("0.00")
            fourteenth = Decimal("0.00")

            if salary_table.thirteenth_month:
                thirteenth = (base_monthly / 12) * months_worked

            if salary_table.fourteenth_month:
                fourteenth = (base_monthly / 12) * months_worked

            return {
                "thirteenth": thirteenth.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "fourteenth": fourteenth.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "total": (thirteenth + fourteenth).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            }

        except Exception as e:
            self.logger.error(f"Error calculating 13th/14th month: {e}")
            return {"thirteenth": Decimal("0.00"), "fourteenth": Decimal("0.00"), "total": Decimal("0.00")}

    def calculate_tfr_accrual(
        self,
        monthly_salary: Decimal,
        service_months: int,
        includes_allowances: bool = False,
        annual_inflation_rate: Decimal = Decimal("2.50"),
    ) -> TFRAccrual:
        """Automatically calculate TFR (severance) accrual."""
        try:
            # Get TFR rules from CCNL or use defaults
            tfr_rules = getattr(self.ccnl, "tfr_rules", None)
            if not tfr_rules:
                # Standard Italian TFR calculation
                Decimal("6.91")  # 1/13.5 ≈ 7.41% minus advance to state
                advance_eligible = service_months >= 96  # 8 years
                advance_percentage = Decimal("70.0")
            else:
                advance_eligible = service_months >= tfr_rules.minimum_service_months
                advance_percentage = tfr_rules.advance_percentage

            # Calculate annual accrual (monthly salary * 13.5 months / 13.5 = 1 month equivalent)
            annual_salary_basis = monthly_salary * 12
            if includes_allowances:
                # Add estimated allowances (simplified)
                annual_salary_basis *= Decimal("1.15")

            annual_accrual = annual_salary_basis / Decimal("13.5")
            monthly_accrual = annual_accrual / 12

            # Calculate total accumulated with revaluation
            # Simplified calculation - in reality this would compound annually
            revaluation_rate = Decimal("1.015")  # 1.5% fixed + inflation component
            years_service = Decimal(str(service_months)) / 12
            accumulated_tfr = annual_accrual * years_service * revaluation_rate

            # Calculate advance eligible amount
            advance_eligible_amount = None
            if advance_eligible:
                advance_eligible_amount = accumulated_tfr * (advance_percentage / 100)

            return TFRAccrual(
                monthly_salary_basis=monthly_salary,
                annual_accrual=annual_accrual,
                total_service_months=service_months,
                accumulated_tfr=accumulated_tfr,
                revaluation_rate=revaluation_rate,
                advance_eligible_amount=advance_eligible_amount,
                monthly_accrual=monthly_accrual,
            )

        except Exception as e:
            self.logger.error(f"Error calculating TFR accrual: {e}")
            return self._empty_tfr_accrual()

    def calculate_maternity_paternity_leave(
        self, leave_type: str, daily_salary: Decimal, start_date: date, is_employee: bool = True
    ) -> MaternityPaternityLeave:
        """Calculate maternity/paternity leave entitlements."""
        try:
            # Italian statutory entitlements
            if leave_type.lower() == "maternity":
                total_days = 150  # 5 months
                paid_days = 150
                compensation_rate = Decimal("0.80")  # 80% salary
            elif leave_type.lower() == "paternity":
                total_days = 10  # Mandatory paternity leave
                paid_days = 10
                compensation_rate = Decimal("1.00")  # 100% salary
            elif leave_type.lower() == "parental":
                total_days = 180  # Up to 6 months until child is 12
                paid_days = 90  # First 3 months at 30% salary
                compensation_rate = Decimal("0.30")  # 30% salary
            else:
                total_days = 0
                paid_days = 0
                compensation_rate = Decimal("0.00")

            unpaid_days = total_days - paid_days

            # Calculate compensation
            daily_compensation = daily_salary * compensation_rate
            total_compensation = daily_compensation * paid_days

            # INPS covers the cost, employer may top up
            inps_contribution = total_compensation

            # Calculate dates
            end_date = start_date + timedelta(days=total_days) if start_date else None

            return MaternityPaternityLeave(
                leave_type=leave_type.lower(),
                total_entitled_days=total_days,
                paid_days=paid_days,
                unpaid_days=unpaid_days,
                compensation_rate=compensation_rate,
                daily_compensation=daily_compensation,
                total_compensation=total_compensation,
                inps_contribution=inps_contribution,
                start_date=start_date,
                end_date=end_date,
            )

        except Exception as e:
            self.logger.error(f"Error calculating maternity/paternity leave: {e}")
            return self._empty_maternity_paternity()

    # Helper methods for empty/default calculations

    def _empty_holiday_accrual(self) -> HolidayAccrual:
        """Return empty holiday accrual."""
        return HolidayAccrual(
            accrual_period_start=date.today(),
            accrual_period_end=date.today(),
            base_annual_days=0,
            seniority_bonus_days=0,
            total_annual_entitlement=0,
            months_worked=0,
            accrued_days=Decimal("0.00"),
            used_days=0,
            remaining_days=Decimal("0.00"),
            monetary_value_per_day=Decimal("0.00"),
            total_monetary_value=Decimal("0.00"),
        )

    def _empty_overtime_calculation(self) -> OvertimeCalculation:
        """Return empty overtime calculation."""
        return OvertimeCalculation(
            regular_hours=0,
            overtime_hours=0,
            hourly_base_rate=Decimal("0.00"),
            overtime_rate=Decimal("1.00"),
            overtime_premium=Decimal("0.00"),
            total_overtime_pay=Decimal("0.00"),
        )

    def _empty_tfr_accrual(self) -> TFRAccrual:
        """Return empty TFR accrual."""
        return TFRAccrual(
            monthly_salary_basis=Decimal("0.00"),
            annual_accrual=Decimal("0.00"),
            total_service_months=0,
            accumulated_tfr=Decimal("0.00"),
            revaluation_rate=Decimal("1.015"),
        )

    def _empty_maternity_paternity(self) -> MaternityPaternityLeave:
        """Return empty maternity/paternity calculation."""
        return MaternityPaternityLeave(
            leave_type="unknown",
            total_entitled_days=0,
            paid_days=0,
            unpaid_days=0,
            compensation_rate=Decimal("0.00"),
            daily_compensation=Decimal("0.00"),
            total_compensation=Decimal("0.00"),
            inps_contribution=Decimal("0.00"),
        )


def create_calculator_for_sector(sector: CCNLSector) -> EnhancedCCNLCalculator | None:
    """Factory method to create calculator for a specific sector."""
    # This would typically load the CCNL from database
    # For now, returning None as placeholder
    return None
