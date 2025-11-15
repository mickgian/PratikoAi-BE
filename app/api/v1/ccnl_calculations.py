"""API endpoints for CCNL calculations.

This module provides REST API endpoints for comprehensive CCNL calculations
including salary computations, leave calculations, and complex queries.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator

from app.api.v1.auth import get_current_user
from app.models.ccnl_data import CCNLSector, CompanySize, GeographicArea, LeaveType, WorkerCategory
from app.models.user import User
from app.services.ccnl_calculator_engine import CalculationPeriod
from app.services.ccnl_service import ccnl_service

router = APIRouter(prefix="/ccnl/calculations", tags=["CCNL Calculations"])


class CompensationRequest(BaseModel):
    """Request model for compensation calculation."""

    sector: CCNLSector = Field(..., description="CCNL sector")
    level_code: str = Field(..., description="Job level code (e.g., C1, C2, B1)")
    seniority_months: int = Field(default=0, ge=0, description="Months of seniority")
    geographic_area: GeographicArea = Field(default=GeographicArea.NAZIONALE)
    company_size: CompanySize | None = Field(default=None)
    working_days_per_month: int = Field(default=22, ge=1, le=31)
    overtime_hours_monthly: int = Field(default=0, ge=0)
    include_allowances: bool = Field(default=True)
    period: CalculationPeriod = Field(default=CalculationPeriod.ANNUAL)


class LeaveBalanceRequest(BaseModel):
    """Request model for leave balance calculation."""

    sector: CCNLSector
    seniority_months: int = Field(default=0, ge=0)
    used_days: dict[str, int] | None = Field(default=None)
    calculation_date: date | None = Field(default=None)


class SeniorityBenefitsRequest(BaseModel):
    """Request model for seniority benefits calculation."""

    sector: CCNLSector
    worker_category: WorkerCategory
    hire_date: date
    calculation_date: date | None = Field(default=None)


class ComplexQueryRequest(BaseModel):
    """Request model for complex CCNL queries."""

    sector: CCNLSector
    level_code: str
    worker_category: WorkerCategory
    geographic_area: GeographicArea = Field(default=GeographicArea.NAZIONALE)
    seniority_years: int = Field(ge=0)
    include_all_benefits: bool = Field(default=True)


class CompensationResponse(BaseModel):
    """Response model for compensation calculation."""

    base_salary: float
    thirteenth_month: float
    fourteenth_month: float
    overtime: float
    allowances: dict[str, float]
    deductions: dict[str, float]
    net_total: float
    gross_total: float
    period: str
    currency: str = "EUR"


class LeaveBalanceResponse(BaseModel):
    """Response model for leave balance."""

    leave_type: str
    annual_entitlement: int
    used_days: int
    remaining_days: int
    accrual_rate: float
    monetary_value: float | None = None
    expiry_date: str | None = None


class SeniorityBenefitsResponse(BaseModel):
    """Response model for seniority benefits."""

    seniority_months: int
    seniority_years: float
    notice_period_days: int
    severance_pay_months: float
    additional_leave_days: int
    salary_increases: float


@router.post("/compensation", response_model=CompensationResponse)
async def calculate_compensation(
    request: CompensationRequest, current_user: User = Depends(get_current_user)
) -> CompensationResponse:
    """Calculate comprehensive compensation for a CCNL position.

    This endpoint calculates total compensation including:
    - Base salary
    - 13th and 14th month payments
    - Overtime compensation
    - Applicable allowances
    - Tax and social security deductions

    The calculation can be returned for different periods (annual, monthly, etc.)
    """
    compensation = await ccnl_service.calculate_comprehensive_compensation(
        sector=request.sector,
        level_code=request.level_code,
        seniority_months=request.seniority_months,
        geographic_area=request.geographic_area,
        company_size=request.company_size,
        working_days_per_month=request.working_days_per_month,
        overtime_hours_monthly=request.overtime_hours_monthly,
        include_allowances=request.include_allowances,
        period=request.period,
    )

    if not compensation:
        raise HTTPException(
            status_code=404,
            detail=f"No CCNL data found for sector {request.sector.value} or level {request.level_code}",
        )

    return CompensationResponse(**compensation.to_dict())


@router.post("/leave-balances", response_model=list[LeaveBalanceResponse])
async def calculate_leave_balances(
    request: LeaveBalanceRequest, current_user: User = Depends(get_current_user)
) -> list[LeaveBalanceResponse]:
    """Calculate all leave balances for an employee.

    This endpoint calculates:
    - Annual leave entitlements based on seniority
    - Used and remaining days
    - Accrual rates
    - Expiry dates
    - Monetary value of unused leave (where applicable)
    """
    # Convert string keys to LeaveType enum
    used_days = None
    if request.used_days:
        used_days = {}
        for leave_type_str, days in request.used_days.items():
            try:
                leave_type = LeaveType(leave_type_str)
                used_days[leave_type] = days
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid leave type: {leave_type_str}")

    balances = await ccnl_service.calculate_all_leave_balances(
        sector=request.sector,
        seniority_months=request.seniority_months,
        used_days=used_days,
        calculation_date=request.calculation_date,
    )

    if not balances:
        raise HTTPException(status_code=404, detail=f"No CCNL data found for sector {request.sector.value}")

    return [LeaveBalanceResponse(**balance.to_dict()) for balance in balances]


@router.post("/seniority-benefits", response_model=SeniorityBenefitsResponse)
async def calculate_seniority_benefits(
    request: SeniorityBenefitsRequest, current_user: User = Depends(get_current_user)
) -> SeniorityBenefitsResponse:
    """Calculate all benefits based on seniority.

    This endpoint calculates:
    - Notice period requirements
    - Severance pay entitlements
    - Additional leave days from seniority
    - Salary increases based on tenure
    """
    benefits = await ccnl_service.calculate_all_seniority_benefits(
        sector=request.sector,
        worker_category=request.worker_category,
        hire_date=request.hire_date,
        calculation_date=request.calculation_date,
    )

    if not benefits:
        raise HTTPException(status_code=404, detail=f"No CCNL data found for sector {request.sector.value}")

    return SeniorityBenefitsResponse(**benefits.to_dict())


@router.post("/complex-query")
async def answer_complex_query(
    request: ComplexQueryRequest, current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """Answer complex CCNL queries with comprehensive information.

    This endpoint provides complete information for queries like:
    "What would be the total compensation for a C2 level metalworker
    in Northern Italy with 5 years of experience including all
    allowances and leave entitlements?"

    Returns:
    - Complete compensation breakdown
    - All leave entitlements
    - Seniority-based benefits
    - Working hours information
    - Summary statistics
    """
    result = await ccnl_service.answer_ccnl_query(
        sector=request.sector,
        level_code=request.level_code,
        worker_category=request.worker_category,
        geographic_area=request.geographic_area,
        seniority_years=request.seniority_years,
        include_all_benefits=request.include_all_benefits,
    )

    if not result:
        raise HTTPException(status_code=404, detail="No CCNL data found for the specified parameters")

    return result


@router.get("/overtime-scenarios")
async def get_overtime_scenarios(
    sector: CCNLSector = Query(..., description="CCNL sector"),
    monthly_salary: float = Query(..., gt=0, description="Base monthly salary"),
    working_days: int = Query(22, ge=1, le=31, description="Working days per month"),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Calculate various overtime scenarios for a given salary.

    Returns calculations for:
    - Weekday overtime rates and examples
    - Weekend overtime rates and examples
    - Holiday overtime rates and examples
    - Maximum overtime limits
    """
    # Get CCNL for sector
    ccnl_db = await ccnl_service.get_current_ccnl_by_sector(sector)
    if not ccnl_db:
        raise HTTPException(status_code=404, detail=f"No CCNL data found for sector {sector.value}")

    # Convert to domain model
    domain_ccnl = ccnl_service._convert_db_to_domain_model(ccnl_db)

    # Create calculator
    from app.services.ccnl_calculator_engine import EnhancedCCNLCalculator

    calculator = EnhancedCCNLCalculator(domain_ccnl)

    # Calculate scenarios
    scenarios = calculator.calculate_overtime_scenarios(
        base_monthly_salary=Decimal(str(monthly_salary)), working_days=working_days
    )

    return scenarios


@router.get("/geographic-differences")
async def get_geographic_differences(
    sector: CCNLSector = Query(..., description="CCNL sector"),
    level_code: str = Query(..., description="Job level code"),
    base_area: GeographicArea = Query(GeographicArea.NAZIONALE, description="Base area for comparison"),
    current_user: User = Depends(get_current_user),
) -> dict[str, dict[str, Any]]:
    """Calculate salary differences across geographic areas.

    Returns salary comparisons showing:
    - Monthly salary differences
    - Percentage differences
    - Annual impact
    """
    # Get CCNL for sector
    ccnl_db = await ccnl_service.get_current_ccnl_by_sector(sector)
    if not ccnl_db:
        raise HTTPException(status_code=404, detail=f"No CCNL data found for sector {sector.value}")

    # Convert to domain model
    domain_ccnl = ccnl_service._convert_db_to_domain_model(ccnl_db)

    # Create calculator
    from app.services.ccnl_calculator_engine import EnhancedCCNLCalculator

    calculator = EnhancedCCNLCalculator(domain_ccnl)

    # Calculate differences
    differences = calculator.calculate_geographic_differences(level_code=level_code, base_area=base_area)

    if not differences:
        raise HTTPException(status_code=404, detail=f"No salary data found for level {level_code}")

    return differences


@router.post("/career-progression")
async def calculate_career_progression(
    sector: CCNLSector,
    starting_level: str,
    progression_path: list[dict[str, int]],  # [{"level": "C2", "months": 36}, ...]
    starting_date: date,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Calculate earnings over a career progression path.

    This endpoint calculates cumulative earnings and progression through
    multiple job levels over time.

    Example progression_path:
    [
        {"level": "C1", "months": 24},
        {"level": "C2", "months": 36},
        {"level": "B1", "months": 60}
    ]
    """
    # Get CCNL for sector
    ccnl_db = await ccnl_service.get_current_ccnl_by_sector(sector)
    if not ccnl_db:
        raise HTTPException(status_code=404, detail=f"No CCNL data found for sector {sector.value}")

    # Convert to domain model
    domain_ccnl = ccnl_service._convert_db_to_domain_model(ccnl_db)

    # Create calculator
    from app.services.ccnl_calculator_engine import EnhancedCCNLCalculator

    calculator = EnhancedCCNLCalculator(domain_ccnl)

    # Convert progression path to tuples
    progression_tuples = [(item["level"], item["months"]) for item in progression_path]

    # Calculate progression
    result = calculator.calculate_career_progression(
        starting_level=starting_level, progression_path=progression_tuples, starting_date=starting_date
    )

    return result


@router.get("/compare-sectors")
async def compare_sectors(
    sector1: CCNLSector = Query(...),
    sector2: CCNLSector = Query(...),
    level_code: str = Query(...),
    comparison_aspects: list[str] = Query(default=["salary", "leave", "notice_period"]),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Compare provisions between two CCNL sectors.

    Available comparison aspects:
    - salary: Compare base salaries
    - leave: Compare leave entitlements
    - notice_period: Compare notice period requirements
    - overtime: Compare overtime rates
    """
    # Get CCNLs for both sectors
    ccnl1_db = await ccnl_service.get_current_ccnl_by_sector(sector1)
    ccnl2_db = await ccnl_service.get_current_ccnl_by_sector(sector2)

    if not ccnl1_db or not ccnl2_db:
        raise HTTPException(status_code=404, detail="CCNL data not found for one or both sectors")

    # Convert to domain models
    domain_ccnl1 = ccnl_service._convert_db_to_domain_model(ccnl1_db)
    domain_ccnl2 = ccnl_service._convert_db_to_domain_model(ccnl2_db)

    # Create calculator for first CCNL
    from app.services.ccnl_calculator_engine import EnhancedCCNLCalculator

    calculator = EnhancedCCNLCalculator(domain_ccnl1)

    # Compare with second CCNL
    comparisons = calculator.compare_with_other_ccnl(
        domain_ccnl2, level_code=level_code, comparison_aspects=comparison_aspects
    )

    return [comp.to_dict() for comp in comparisons]
