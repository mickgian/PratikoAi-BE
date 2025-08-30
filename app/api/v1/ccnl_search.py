"""
CCNL Search API endpoints.

This module provides REST API endpoints for comprehensive CCNL search functionality
including natural language queries, faceted search, and comparisons.
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field, ConfigDict

from app.models.ccnl_data import (
    CCNLSector, WorkerCategory, GeographicArea,
    LeaveType, AllowanceType, CompanySize
)
from app.services.ccnl_search_service import (
    ccnl_search_service, SearchFilters, SearchResponse,
    SearchResult, FacetCount
)
from app.api.v1.auth import get_current_user
from app.models.user import User


# Pydantic models for API

class SearchFiltersRequest(BaseModel):
    """Search filters request model."""
    model_config = ConfigDict(use_enum_values=True)
    
    # Sector filters
    sectors: Optional[List[CCNLSector]] = Field(None, description="CCNL sectors to search")
    sector_keywords: Optional[List[str]] = Field(None, description="Keywords for sector matching")
    
    # Geographic filters
    geographic_areas: Optional[List[GeographicArea]] = Field(None, description="Geographic areas")
    regions: Optional[List[str]] = Field(None, description="Italian regions")
    provinces: Optional[List[str]] = Field(None, description="Italian provinces")
    
    # Worker category filters
    worker_categories: Optional[List[WorkerCategory]] = Field(None, description="Worker categories")
    job_levels: Optional[List[str]] = Field(None, description="Specific job level codes")
    
    # Salary filters
    min_salary: Optional[Decimal] = Field(None, description="Minimum monthly salary")
    max_salary: Optional[Decimal] = Field(None, description="Maximum monthly salary")
    include_thirteenth: bool = Field(True, description="Include 13th month in calculations")
    include_fourteenth: bool = Field(True, description="Include 14th month in calculations")
    
    # Experience filters
    min_experience_months: Optional[int] = Field(None, description="Minimum experience in months")
    max_experience_months: Optional[int] = Field(None, description="Maximum experience in months")
    
    # Working conditions
    max_weekly_hours: Optional[int] = Field(None, description="Maximum weekly working hours")
    flexible_hours_required: Optional[bool] = Field(None, description="Flexible hours required")
    part_time_allowed: Optional[bool] = Field(None, description="Part-time work allowed")
    shift_work_allowed: Optional[bool] = Field(None, description="Shift work allowed")
    
    # Leave filters
    min_vacation_days: Optional[int] = Field(None, description="Minimum annual vacation days")
    leave_types_required: Optional[List[LeaveType]] = Field(None, description="Required leave types")
    
    # Benefits filters
    required_allowances: Optional[List[AllowanceType]] = Field(None, description="Required allowances")
    company_sizes: Optional[List[CompanySize]] = Field(None, description="Company size categories")
    
    # Date filters
    valid_on_date: Optional[date] = Field(None, description="CCNL valid on specific date")
    active_only: bool = Field(True, description="Only show currently active CCNLs")
    
    # Text search
    keywords: Optional[str] = Field(None, description="Full-text search keywords")
    search_in_provisions: bool = Field(True, description="Search in CCNL provisions")
    search_in_job_descriptions: bool = Field(True, description="Search in job descriptions")
    search_in_allowances: bool = Field(True, description="Search in allowances")


class SearchResultResponse(BaseModel):
    """Individual search result response."""
    agreement_id: int
    sector: str
    sector_name: str
    agreement_name: str
    relevance_score: float
    matched_fields: List[str]
    highlights: Dict[str, str]
    summary: Optional[str]
    salary_range: Optional[Dict[str, float]]
    vacation_days: Optional[int]
    working_hours: Optional[int]
    geographic_coverage: List[str]


class FacetCountResponse(BaseModel):
    """Facet count response."""
    value: str
    count: int
    display_name: Optional[str]


class SearchResponseModel(BaseModel):
    """Complete search response model."""
    results: List[SearchResultResponse]
    total_count: int
    page: int
    page_size: int
    query_time_ms: int
    facets: Dict[str, List[FacetCountResponse]]
    interpreted_query: Optional[str]
    suggested_queries: List[str]
    spelling_corrections: Dict[str, str]
    min_salary: Optional[float]
    max_salary: Optional[float]
    avg_salary: Optional[float]


class NaturalLanguageSearchRequest(BaseModel):
    """Natural language search request."""
    query: str = Field(..., description="Natural language search query in Italian or English")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Results per page")
    include_facets: bool = Field(True, description="Include facet counts")


class ComparisonRequest(BaseModel):
    """Sector comparison request."""
    sector1: CCNLSector = Field(..., description="First sector to compare")
    sector2: CCNLSector = Field(..., description="Second sector to compare")
    comparison_aspects: List[str] = Field(
        ["salary", "vacation", "hours", "notice", "allowances"],
        description="Aspects to compare"
    )


class AutocompleteRequest(BaseModel):
    """Autocomplete request."""
    partial_query: str = Field(..., min_length=2, description="Partial search query")
    limit: int = Field(10, ge=1, le=50, description="Maximum suggestions")


# API Router
router = APIRouter(prefix="/api/v1/ccnl/search", tags=["CCNL Search"])


@router.post("/", response_model=SearchResponseModel)
async def search_ccnl(
    request: SearchFiltersRequest = Body(None),
    query: Optional[str] = Query(None, description="Natural language search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    sort_by: str = Query("relevance", description="Sort order: relevance, salary_asc, salary_desc, name"),
    include_facets: bool = Query(True, description="Include facet counts"),
    current_user: User = Depends(get_current_user)
) -> SearchResponseModel:
    """
    Search CCNL agreements with advanced filters and natural language support.
    
    You can either:
    1. Use natural language query (e.g., "metalmeccanici milano stipendio 2000 euro")
    2. Use structured filters in the request body
    3. Combine both for more precise results
    
    Example natural language queries:
    - "operaio edile con 5 anni esperienza roma"
    - "impiegato commercio part-time nord italia"
    - "quadro metalmeccanico stipendio minimo 3000"
    - "turismo ferie minimo 30 giorni"
    """
    # Convert request to search filters
    filters = None
    if request:
        filters = SearchFilters(
            sectors=request.sectors,
            sector_keywords=request.sector_keywords,
            geographic_areas=request.geographic_areas,
            regions=request.regions,
            provinces=request.provinces,
            worker_categories=request.worker_categories,
            job_levels=request.job_levels,
            min_salary=request.min_salary,
            max_salary=request.max_salary,
            include_thirteenth=request.include_thirteenth,
            include_fourteenth=request.include_fourteenth,
            min_experience_months=request.min_experience_months,
            max_experience_months=request.max_experience_months,
            max_weekly_hours=request.max_weekly_hours,
            flexible_hours_required=request.flexible_hours_required,
            part_time_allowed=request.part_time_allowed,
            shift_work_allowed=request.shift_work_allowed,
            min_vacation_days=request.min_vacation_days,
            leave_types_required=request.leave_types_required,
            required_allowances=request.required_allowances,
            company_sizes=request.company_sizes,
            valid_on_date=request.valid_on_date,
            active_only=request.active_only,
            keywords=request.keywords,
            search_in_provisions=request.search_in_provisions,
            search_in_job_descriptions=request.search_in_job_descriptions,
            search_in_allowances=request.search_in_allowances
        )
    
    # Perform search
    response = await ccnl_search_service.search(
        query=query,
        filters=filters,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        include_facets=include_facets
    )
    
    # Convert response to API model
    return SearchResponseModel(
        results=[
            SearchResultResponse(
                agreement_id=r.agreement_id,
                sector=r.sector.value,
                sector_name=r.sector_name,
                agreement_name=r.agreement_name,
                relevance_score=r.relevance_score,
                matched_fields=r.matched_fields,
                highlights=r.highlights,
                summary=r.summary,
                salary_range={
                    "min": float(r.salary_range[0]),
                    "max": float(r.salary_range[1])
                } if r.salary_range else None,
                vacation_days=r.vacation_days,
                working_hours=r.working_hours,
                geographic_coverage=r.geographic_coverage
            )
            for r in response.results
        ],
        total_count=response.total_count,
        page=response.page,
        page_size=response.page_size,
        query_time_ms=response.query_time_ms,
        facets={
            key: [
                FacetCountResponse(
                    value=f.value,
                    count=f.count,
                    display_name=f.display_name
                )
                for f in facets
            ]
            for key, facets in response.facets.items()
        },
        interpreted_query=response.interpreted_query,
        suggested_queries=response.suggested_queries,
        spelling_corrections=response.spelling_corrections,
        min_salary=float(response.min_salary) if response.min_salary else None,
        max_salary=float(response.max_salary) if response.max_salary else None,
        avg_salary=float(response.avg_salary) if response.avg_salary else None
    )


@router.post("/natural-language", response_model=SearchResponseModel)
async def natural_language_search(
    request: NaturalLanguageSearchRequest,
    current_user: User = Depends(get_current_user)
) -> SearchResponseModel:
    """
    Search using natural language queries in Italian or English.
    
    Examples:
    - "Quanto guadagna un operaio metalmeccanico a Milano?"
    - "Construction workers in Rome with overtime"
    - "Commercio part-time con buoni pasto"
    - "Dirigente IT con 10 anni esperienza"
    """
    response = await ccnl_search_service.search(
        query=request.query,
        page=request.page,
        page_size=request.page_size,
        include_facets=request.include_facets
    )
    
    # Convert response (same as above)
    return SearchResponseModel(
        results=[
            SearchResultResponse(
                agreement_id=r.agreement_id,
                sector=r.sector.value,
                sector_name=r.sector_name,
                agreement_name=r.agreement_name,
                relevance_score=r.relevance_score,
                matched_fields=r.matched_fields,
                highlights=r.highlights,
                summary=r.summary,
                salary_range={
                    "min": float(r.salary_range[0]),
                    "max": float(r.salary_range[1])
                } if r.salary_range else None,
                vacation_days=r.vacation_days,
                working_hours=r.working_hours,
                geographic_coverage=r.geographic_coverage
            )
            for r in response.results
        ],
        total_count=response.total_count,
        page=response.page,
        page_size=response.page_size,
        query_time_ms=response.query_time_ms,
        facets={
            key: [
                FacetCountResponse(
                    value=f.value,
                    count=f.count,
                    display_name=f.display_name
                )
                for f in facets
            ]
            for key, facets in response.facets.items()
        },
        interpreted_query=response.interpreted_query,
        suggested_queries=response.suggested_queries,
        spelling_corrections=response.spelling_corrections,
        min_salary=float(response.min_salary) if response.min_salary else None,
        max_salary=float(response.max_salary) if response.max_salary else None,
        avg_salary=float(response.avg_salary) if response.avg_salary else None
    )


@router.get("/by-sector/{sector}", response_model=SearchResponseModel)
async def search_by_sector(
    sector: CCNLSector,
    include_related: bool = Query(True, description="Include related sectors"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> SearchResponseModel:
    """Search CCNL agreements by sector with optional related sectors."""
    response = await ccnl_search_service.search_by_sector(
        sectors=[sector],
        include_related=include_related
    )
    
    # Convert response (reuse conversion logic)
    return _convert_search_response(response)


@router.get("/by-geographic-area", response_model=SearchResponseModel)
async def search_by_geographic_area(
    areas: List[GeographicArea] = Query(..., description="Geographic areas"),
    regions: Optional[List[str]] = Query(None, description="Italian regions"),
    provinces: Optional[List[str]] = Query(None, description="Italian provinces"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> SearchResponseModel:
    """Search CCNL agreements by geographic area."""
    response = await ccnl_search_service.search_by_geographic_area(
        areas=areas,
        regions=regions,
        provinces=provinces
    )
    
    return _convert_search_response(response)


@router.get("/by-salary-range", response_model=SearchResponseModel)
async def search_by_salary_range(
    min_salary: Optional[Decimal] = Query(None, description="Minimum monthly salary"),
    max_salary: Optional[Decimal] = Query(None, description="Maximum monthly salary"),
    include_benefits: bool = Query(True, description="Include 13th/14th month"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> SearchResponseModel:
    """Search CCNL agreements by salary range."""
    response = await ccnl_search_service.search_by_salary_range(
        min_salary=min_salary,
        max_salary=max_salary,
        include_benefits=include_benefits
    )
    
    return _convert_search_response(response)


@router.get("/by-job-category", response_model=SearchResponseModel)
async def search_by_job_category(
    categories: List[WorkerCategory] = Query(..., description="Worker categories"),
    experience_years: Optional[int] = Query(None, description="Years of experience"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> SearchResponseModel:
    """Search CCNL agreements by job category."""
    response = await ccnl_search_service.search_by_job_category(
        categories=categories,
        experience_years=experience_years
    )
    
    return _convert_search_response(response)


@router.post("/compare-sectors")
async def compare_sectors(
    request: ComparisonRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Compare two CCNL sectors across multiple aspects.
    
    Available comparison aspects:
    - salary: Compare salary ranges and averages
    - vacation: Compare vacation day entitlements
    - hours: Compare working hours
    - notice: Compare notice periods
    - allowances: Compare special allowances
    """
    comparison = await ccnl_search_service.compare_sectors(
        sector1=request.sector1,
        sector2=request.sector2,
        comparison_aspects=request.comparison_aspects
    )
    
    return comparison


@router.get("/popular-searches")
async def get_popular_searches(
    current_user: User = Depends(get_current_user)
) -> List[str]:
    """Get list of popular search queries."""
    return await ccnl_search_service.get_popular_searches()


@router.post("/autocomplete")
async def autocomplete(
    request: AutocompleteRequest,
    current_user: User = Depends(get_current_user)
) -> List[str]:
    """Get autocomplete suggestions for search queries."""
    return await ccnl_search_service.autocomplete(
        partial_query=request.partial_query,
        limit=request.limit
    )


@router.get("/sectors")
async def get_all_sectors(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, str]]:
    """Get all available CCNL sectors."""
    return [
        {
            "code": sector.value,
            "name": sector.italian_name(),
            "priority": sector.priority_level()
        }
        for sector in CCNLSector
    ]


@router.get("/worker-categories")
async def get_worker_categories(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, str]]:
    """Get all worker categories."""
    return [
        {
            "code": category.value,
            "name": category.italian_name(),
            "hierarchy_level": category.hierarchy_level()
        }
        for category in WorkerCategory
    ]


@router.get("/geographic-areas")
async def get_geographic_areas(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, str]]:
    """Get all geographic areas."""
    return [
        {
            "code": area.value,
            "name": area.value.replace("_", " ").title()
        }
        for area in GeographicArea
    ]


# Helper function to convert search response
def _convert_search_response(response: SearchResponse) -> SearchResponseModel:
    """Convert internal SearchResponse to API model."""
    return SearchResponseModel(
        results=[
            SearchResultResponse(
                agreement_id=r.agreement_id,
                sector=r.sector.value,
                sector_name=r.sector_name,
                agreement_name=r.agreement_name,
                relevance_score=r.relevance_score,
                matched_fields=r.matched_fields,
                highlights=r.highlights,
                summary=r.summary,
                salary_range={
                    "min": float(r.salary_range[0]),
                    "max": float(r.salary_range[1])
                } if r.salary_range else None,
                vacation_days=r.vacation_days,
                working_hours=r.working_hours,
                geographic_coverage=r.geographic_coverage
            )
            for r in response.results
        ],
        total_count=response.total_count,
        page=response.page,
        page_size=response.page_size,
        query_time_ms=response.query_time_ms,
        facets={
            key: [
                FacetCountResponse(
                    value=f.value,
                    count=f.count,
                    display_name=f.display_name
                )
                for f in facets
            ]
            for key, facets in response.facets.items()
        },
        interpreted_query=response.interpreted_query,
        suggested_queries=response.suggested_queries,
        spelling_corrections=response.spelling_corrections,
        min_salary=float(response.min_salary) if response.min_salary else None,
        max_salary=float(response.max_salary) if response.max_salary else None,
        avg_salary=float(response.avg_salary) if response.avg_salary else None
    )