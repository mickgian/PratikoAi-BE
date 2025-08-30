"""
CCNL Integration Tool for LangGraph.

This tool enables the LLM to access Italian Collective Labor Agreements (CCNL) data
through natural language queries, providing information about salaries, benefits,
working conditions, and labor law compliance.
"""

import json
from typing import Dict, List, Any, Optional, Union
from datetime import date, datetime
from decimal import Decimal

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.ccnl_search_service import CCNLSearchService
from app.services.ccnl_calculator_engine import EnhancedCCNLCalculator
from app.services.vector_service import vector_service
from app.services.ccnl_response_formatter import ccnl_response_formatter
from app.core.monitoring.metrics import track_ccnl_query, track_ccnl_cache_hit
from app.models.ccnl_data import (
    CCNLSector, WorkerCategory, GeographicArea, 
    LeaveType, AllowanceType, CompanySize
)
from app.core.logging import logger


class CCNLQueryInput(BaseModel):
    """Input schema for CCNL queries."""
    query_type: str = Field(
        description="Type of query: 'search', 'salary_calculation', 'leave_calculation', 'notice_period', 'comparison', 'sector_info'"
    )
    sector: Optional[str] = Field(
        default=None,
        description="CCNL sector (e.g., 'metalworking', 'construction', 'commerce', 'textile', 'chemical')"
    )
    job_category: Optional[str] = Field(
        default=None,
        description="Job category/level (e.g., 'worker', 'employee', 'manager', 'apprentice')"
    )
    geographic_area: Optional[str] = Field(
        default=None,
        description="Geographic area (e.g., 'north', 'center', 'south', 'milan', 'rome')"
    )
    experience_years: Optional[int] = Field(
        default=None,
        description="Years of work experience"
    )
    company_size: Optional[str] = Field(
        default=None,
        description="Company size ('small', 'medium', 'large')"
    )
    search_terms: Optional[str] = Field(
        default=None,
        description="Free text search terms for general information queries"
    )
    calculation_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional parameters for calculations (salary base, hours, etc.)"
    )


class CCNLTool(BaseTool):
    """LangGraph tool for accessing CCNL (Italian Collective Labor Agreements) data."""
    
    name: str = "ccnl_query"
    description: str = """
    Access Italian Collective Labor Agreements (CCNL) data to answer questions about:
    - Salary ranges and compensation for specific job categories and sectors
    - Leave entitlements (vacation days, sick leave, maternity/paternity)
    - Notice periods for termination
    - Working hours and overtime rules
    - Benefits and allowances
    - Cross-sector comparisons
    - Geographic differences in labor agreements
    
    Use this tool when users ask about Italian labor law, worker rights, salaries,
    benefits, or employment conditions. Provide specific sector, job category, and
    location when possible for more accurate results.
    """
    
    def __init__(self):
        super().__init__()
        # Initialize services lazily to avoid Pydantic field issues
        self._search_service = None
        self._calculator_engine = None
    
    @property
    def search_service(self):
        if self._search_service is None:
            self._search_service = CCNLSearchService()
        return self._search_service
    
    @property
    def calculator_engine(self):
        if self._calculator_engine is None:
            self._calculator_engine = EnhancedCCNLCalculator()
        return self._calculator_engine
    
    def _run(self, **kwargs) -> str:
        """Execute CCNL query (synchronous version)."""
        # This shouldn't be called in async context, but provide fallback
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.arun(**kwargs))
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.arun(**kwargs))
            finally:
                loop.close()
    
    async def _arun(
        self,
        query_type: str,
        sector: Optional[str] = None,
        job_category: Optional[str] = None,
        geographic_area: Optional[str] = None,
        experience_years: Optional[int] = None,
        company_size: Optional[str] = None,
        search_terms: Optional[str] = None,
        calculation_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Execute CCNL query asynchronously."""
        import time
        start_time = time.time()
        semantic_search_used = False
        
        try:
            logger.info(
                "ccnl_query_initiated",
                query_type=query_type,
                sector=sector,
                job_category=job_category,
                geographic_area=geographic_area,
                search_terms=search_terms
            )
            
            # Route to appropriate handler based on query type
            if query_type == "search":
                result = await self._handle_search_query(
                    search_terms=search_terms,
                    sector=sector,
                    job_category=job_category,
                    geographic_area=geographic_area
                )
            elif query_type == "salary_calculation":
                result = await self._handle_salary_calculation(
                    sector=sector,
                    job_category=job_category,
                    geographic_area=geographic_area,
                    experience_years=experience_years,
                    company_size=company_size,
                    calculation_params=calculation_params or {}
                )
            elif query_type == "leave_calculation":
                result = await self._handle_leave_calculation(
                    sector=sector,
                    job_category=job_category,
                    experience_years=experience_years,
                    calculation_params=calculation_params or {}
                )
            elif query_type == "notice_period":
                result = await self._handle_notice_period_query(
                    sector=sector,
                    job_category=job_category,
                    experience_years=experience_years
                )
            elif query_type == "comparison":
                result = await self._handle_comparison_query(
                    sectors=[sector] if sector else None,
                    job_category=job_category,
                    geographic_area=geographic_area,
                    calculation_params=calculation_params or {}
                )
            elif query_type == "sector_info":
                result = await self._handle_sector_info_query(
                    sector=sector,
                    search_terms=search_terms
                )
            else:
                result = {
                    "success": False,
                    "error": f"Unknown query type: {query_type}",
                    "available_types": ["search", "salary_calculation", "leave_calculation", "notice_period", "comparison", "sector_info"]
                }
            
            # Check if semantic search was used in the result
            if result.get("semantic_search_used", False):
                semantic_search_used = True
            
            # Format response for LLM consumption using specialized formatter
            formatted_response = ccnl_response_formatter.format_ccnl_response(result)
            
            # Track successful query metrics
            duration_seconds = time.time() - start_time
            track_ccnl_query(
                query_type=query_type,
                sector=sector or "unknown",
                status="success",
                duration_seconds=duration_seconds,
                semantic_search_used=semantic_search_used
            )
            
            return formatted_response
            
        except Exception as e:
            # Track failed query metrics
            duration_seconds = time.time() - start_time
            track_ccnl_query(
                query_type=query_type,
                sector=sector or "unknown", 
                status="error",
                duration_seconds=duration_seconds,
                semantic_search_used=semantic_search_used
            )
            
            logger.error(
                "ccnl_query_failed",
                query_type=query_type,
                error=str(e),
                exc_info=True
            )
            return json.dumps({
                "success": False,
                "error": f"CCNL query failed: {str(e)}",
                "message": "Si è verificato un errore durante la ricerca dei dati CCNL. Riprova con parametri diversi."
            })
    
    async def _handle_search_query(
        self,
        search_terms: Optional[str],
        sector: Optional[str],
        job_category: Optional[str],
        geographic_area: Optional[str]
    ) -> Dict[str, Any]:
        """Handle general search queries using both traditional and semantic search."""
        try:
            # Parse sector enum
            parsed_sector = self._parse_sector(sector)
            parsed_category = self._parse_worker_category(job_category)
            parsed_area = self._parse_geographic_area(geographic_area)
            
            # Perform traditional database search
            traditional_results = await self.search_service.search_ccnl_agreements(
                query=search_terms or "",
                sector=parsed_sector,
                worker_category=parsed_category,
                geographic_area=parsed_area,
                limit=5
            )
            
            # Perform semantic search if vector service is available
            semantic_results = []
            if vector_service.is_available() and search_terms:
                semantic_results = vector_service.search_ccnl_semantic(
                    query=search_terms,
                    sector_filter=sector.lower() if sector else None
                )
            
            # Combine results
            combined_results = []
            
            # Add traditional results
            for result in traditional_results.results:
                combined_results.append({
                    **result,
                    "source": "database",
                    "relevance_score": 0.8  # Default relevance for database results
                })
            
            # Add semantic results (avoid duplicates)
            existing_ids = {r.get("id", r.get("ccnl_id")) for r in combined_results}
            for result in semantic_results:
                result_id = result.get("metadata", {}).get("ccnl_id") or result.get("id")
                if result_id not in existing_ids:
                    combined_results.append({
                        "id": result_id,
                        "title": result.get("agreement_title", ""),
                        "sector": result.get("sector", ""),
                        "description": result.get("description", ""),
                        "source": "semantic",
                        "relevance_score": result.get("relevance_score", 0.7)
                    })
            
            # Sort by relevance score
            combined_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            return {
                "success": True,
                "query_type": "search",
                "results": combined_results[:5],  # Top 5 results
                "total_found": traditional_results.total_count + len(semantic_results),
                "search_terms": search_terms,
                "semantic_search_used": len(semantic_results) > 0,
                "filters": {
                    "sector": sector,
                    "job_category": job_category,
                    "geographic_area": geographic_area
                }
            }
            
        except Exception as e:
            logger.error("ccnl_search_query_failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _handle_salary_calculation(
        self,
        sector: Optional[str],
        job_category: Optional[str],
        geographic_area: Optional[str],
        experience_years: Optional[int],
        company_size: Optional[str],
        calculation_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle salary calculation queries."""
        try:
            # Parse enums
            parsed_sector = self._parse_sector(sector)
            parsed_category = self._parse_worker_category(job_category)
            parsed_area = self._parse_geographic_area(geographic_area)
            parsed_size = self._parse_company_size(company_size)
            
            if not parsed_sector:
                return {
                    "success": False,
                    "error": "Sector is required for salary calculations",
                    "available_sectors": [s.value for s in CCNLSector]
                }
            
            # Get salary calculation
            salary_result = await self.calculator_engine.calculate_monthly_salary(
                sector=parsed_sector,
                worker_category=parsed_category or WorkerCategory.WORKER,
                experience_years=experience_years or 0,
                geographic_area=parsed_area,
                company_size=parsed_size,
                job_level_id=calculation_params.get("job_level_id"),
                include_allowances=calculation_params.get("include_allowances", True)
            )
            
            return {
                "success": True,
                "query_type": "salary_calculation",
                "result": salary_result,
                "parameters": {
                    "sector": sector,
                    "job_category": job_category,
                    "geographic_area": geographic_area,
                    "experience_years": experience_years,
                    "company_size": company_size
                }
            }
            
        except Exception as e:
            logger.error("ccnl_salary_calculation_failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _handle_leave_calculation(
        self,
        sector: Optional[str],
        job_category: Optional[str],
        experience_years: Optional[int],
        calculation_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle leave entitlement calculations."""
        try:
            parsed_sector = self._parse_sector(sector)
            parsed_category = self._parse_worker_category(job_category)
            
            if not parsed_sector:
                return {
                    "success": False,
                    "error": "Sector is required for leave calculations",
                    "available_sectors": [s.value for s in CCNLSector]
                }
            
            # Get leave entitlements
            leave_result = await self.calculator_engine.calculate_leave_entitlements(
                sector=parsed_sector,
                worker_category=parsed_category or WorkerCategory.WORKER,
                experience_years=experience_years or 0,
                leave_types=calculation_params.get("leave_types"),
                reference_date=datetime.now().date()
            )
            
            return {
                "success": True,
                "query_type": "leave_calculation",
                "result": leave_result,
                "parameters": {
                    "sector": sector,
                    "job_category": job_category,
                    "experience_years": experience_years
                }
            }
            
        except Exception as e:
            logger.error("ccnl_leave_calculation_failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _handle_notice_period_query(
        self,
        sector: Optional[str],
        job_category: Optional[str],
        experience_years: Optional[int]
    ) -> Dict[str, Any]:
        """Handle notice period queries."""
        try:
            parsed_sector = self._parse_sector(sector)
            parsed_category = self._parse_worker_category(job_category)
            
            if not parsed_sector:
                return {
                    "success": False,
                    "error": "Sector is required for notice period calculations",
                    "available_sectors": [s.value for s in CCNLSector]
                }
            
            # Get notice periods
            notice_result = await self.calculator_engine.calculate_notice_period(
                sector=parsed_sector,
                worker_category=parsed_category or WorkerCategory.WORKER,
                experience_years=experience_years or 0
            )
            
            return {
                "success": True,
                "query_type": "notice_period",
                "result": notice_result,
                "parameters": {
                    "sector": sector,
                    "job_category": job_category,
                    "experience_years": experience_years
                }
            }
            
        except Exception as e:
            logger.error("ccnl_notice_period_failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _handle_comparison_query(
        self,
        sectors: Optional[List[str]],
        job_category: Optional[str],
        geographic_area: Optional[str],
        calculation_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle cross-sector comparison queries."""
        try:
            # Parse sectors for comparison
            parsed_sectors = []
            if sectors:
                for sector in sectors:
                    parsed_sector = self._parse_sector(sector)
                    if parsed_sector:
                        parsed_sectors.append(parsed_sector)
            
            if not parsed_sectors:
                # Default to major sectors for comparison
                parsed_sectors = [
                    CCNLSector.METALWORKING, 
                    CCNLSector.CONSTRUCTION, 
                    CCNLSector.COMMERCE
                ]
            
            parsed_category = self._parse_worker_category(job_category)
            parsed_area = self._parse_geographic_area(geographic_area)
            
            # Perform comparison
            comparison_result = await self.calculator_engine.compare_sectors(
                sectors=parsed_sectors,
                worker_category=parsed_category or WorkerCategory.WORKER,
                geographic_area=parsed_area,
                experience_years=calculation_params.get("experience_years", 5),
                comparison_metrics=calculation_params.get("metrics", ["salary", "leave", "notice_period"])
            )
            
            return {
                "success": True,
                "query_type": "comparison",
                "result": comparison_result,
                "parameters": {
                    "sectors": sectors,
                    "job_category": job_category,
                    "geographic_area": geographic_area
                }
            }
            
        except Exception as e:
            logger.error("ccnl_comparison_failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _handle_sector_info_query(
        self,
        sector: Optional[str],
        search_terms: Optional[str]
    ) -> Dict[str, Any]:
        """Handle sector-specific information queries."""
        try:
            parsed_sector = self._parse_sector(sector)
            
            if not parsed_sector:
                return {
                    "success": False,
                    "error": "Sector is required for sector info queries",
                    "available_sectors": [s.value for s in CCNLSector]
                }
            
            # Get sector information
            sector_info = await self.search_service.get_sector_overview(
                sector=parsed_sector,
                include_statistics=True
            )
            
            return {
                "success": True,
                "query_type": "sector_info",
                "result": sector_info,
                "parameters": {
                    "sector": sector,
                    "search_terms": search_terms
                }
            }
            
        except Exception as e:
            logger.error("ccnl_sector_info_failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    def _parse_sector(self, sector_str: Optional[str]) -> Optional[CCNLSector]:
        """Parse sector string to enum."""
        if not sector_str:
            return None
        
        # Create mapping of common terms to sectors
        sector_mapping = {
            "metalworking": CCNLSector.METALWORKING,
            "metalmeccanico": CCNLSector.METALWORKING,
            "metalmeccanica": CCNLSector.METALWORKING,
            "construction": CCNLSector.CONSTRUCTION,
            "edilizia": CCNLSector.CONSTRUCTION,
            "costruzioni": CCNLSector.CONSTRUCTION,
            "commerce": CCNLSector.COMMERCE,
            "commercio": CCNLSector.COMMERCE,
            "retail": CCNLSector.COMMERCE,
            "textile": CCNLSector.TEXTILE,
            "tessile": CCNLSector.TEXTILE,
            "chemical": CCNLSector.CHEMICAL,
            "chimico": CCNLSector.CHEMICAL,
            "chimica": CCNLSector.CHEMICAL,
            "food": CCNLSector.FOOD,
            "alimentare": CCNLSector.FOOD,
            "transport": CCNLSector.TRANSPORT,
            "trasporti": CCNLSector.TRANSPORT,
            "logistics": CCNLSector.LOGISTICS,
            "logistica": CCNLSector.LOGISTICS,
            "banking": CCNLSector.BANKING,
            "bancario": CCNLSector.BANKING,
            "banche": CCNLSector.BANKING,
            "insurance": CCNLSector.INSURANCE,
            "assicurazioni": CCNLSector.INSURANCE
        }
        
        sector_lower = sector_str.lower().strip()
        return sector_mapping.get(sector_lower)
    
    def _parse_worker_category(self, category_str: Optional[str]) -> Optional[WorkerCategory]:
        """Parse worker category string to enum."""
        if not category_str:
            return None
        
        category_mapping = {
            "worker": WorkerCategory.WORKER,
            "operaio": WorkerCategory.WORKER,
            "employee": WorkerCategory.EMPLOYEE,
            "impiegato": WorkerCategory.EMPLOYEE,
            "manager": WorkerCategory.MANAGER,
            "dirigente": WorkerCategory.MANAGER,
            "executive": WorkerCategory.MANAGER,
            "apprentice": WorkerCategory.APPRENTICE,
            "apprendista": WorkerCategory.APPRENTICE,
            "intern": WorkerCategory.INTERN,
            "stagista": WorkerCategory.INTERN,
            "tirocinio": WorkerCategory.INTERN
        }
        
        category_lower = category_str.lower().strip()
        return category_mapping.get(category_lower)
    
    def _parse_geographic_area(self, area_str: Optional[str]) -> Optional[GeographicArea]:
        """Parse geographic area string to enum."""
        if not area_str:
            return None
        
        area_mapping = {
            "north": GeographicArea.NORTH,
            "nord": GeographicArea.NORTH,
            "center": GeographicArea.CENTER,
            "centro": GeographicArea.CENTER,
            "south": GeographicArea.SOUTH,
            "sud": GeographicArea.SOUTH,
            "islands": GeographicArea.ISLANDS,
            "isole": GeographicArea.ISLANDS,
            # Major cities mapping to areas
            "milan": GeographicArea.NORTH,
            "milano": GeographicArea.NORTH,
            "turin": GeographicArea.NORTH,
            "torino": GeographicArea.NORTH,
            "rome": GeographicArea.CENTER,
            "roma": GeographicArea.CENTER,
            "florence": GeographicArea.CENTER,
            "firenze": GeographicArea.CENTER,
            "naples": GeographicArea.SOUTH,
            "napoli": GeographicArea.SOUTH,
            "palermo": GeographicArea.ISLANDS,
            "catania": GeographicArea.ISLANDS
        }
        
        area_lower = area_str.lower().strip()
        return area_mapping.get(area_lower)
    
    def _parse_company_size(self, size_str: Optional[str]) -> Optional[CompanySize]:
        """Parse company size string to enum."""
        if not size_str:
            return None
        
        size_mapping = {
            "small": CompanySize.SMALL,
            "piccola": CompanySize.SMALL,
            "micro": CompanySize.SMALL,
            "medium": CompanySize.MEDIUM,
            "media": CompanySize.MEDIUM,
            "large": CompanySize.LARGE,
            "grande": CompanySize.LARGE
        }
        
        size_lower = size_str.lower().strip()
        return size_mapping.get(size_lower)
    


# Create tool instance
ccnl_tool = CCNLTool()