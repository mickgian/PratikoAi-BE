"""Comprehensive CCNL Search and Query Service.

This service provides advanced search capabilities for Italian Collective Labor
Agreements including full-text search, faceted search, natural language queries,
and intelligent filtering with fuzzy matching support.
"""

import asyncio
import difflib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, case, func, or_, select, text
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import Select

from app.core.logging import logger
from app.models.ccnl_data import AllowanceType, CCNLSector, CompanySize, GeographicArea, LeaveType, WorkerCategory
from app.models.ccnl_database import (
    CCNLAgreementDB,
    CCNLSectorDB,
    JobLevelDB,
    LeaveEntitlementDB,
    NoticePeriodsDB,
    SalaryTableDB,
    SpecialAllowanceDB,
    WorkingHoursDB,
)
from app.services.database import database_service
from app.services.vector_service import vector_service


@dataclass
class SearchFilters:
    """Advanced search filters for CCNL queries."""

    # Sector filters
    sectors: list[CCNLSector] | None = None
    sector_keywords: list[str] | None = None

    # Geographic filters
    geographic_areas: list[GeographicArea] | None = None
    regions: list[str] | None = None
    provinces: list[str] | None = None

    # Worker category filters
    worker_categories: list[WorkerCategory] | None = None
    job_levels: list[str] | None = None

    # Salary filters
    min_salary: Decimal | None = None
    max_salary: Decimal | None = None
    include_thirteenth: bool = True
    include_fourteenth: bool = True

    # Experience/seniority filters
    min_experience_months: int | None = None
    max_experience_months: int | None = None

    # Working conditions filters
    max_weekly_hours: int | None = None
    flexible_hours_required: bool | None = None
    part_time_allowed: bool | None = None
    shift_work_allowed: bool | None = None

    # Leave filters
    min_vacation_days: int | None = None
    leave_types_required: list[LeaveType] | None = None

    # Benefits filters
    required_allowances: list[AllowanceType] | None = None
    company_sizes: list[CompanySize] | None = None

    # Date filters
    valid_on_date: date | None = None
    active_only: bool = True

    # Text search
    keywords: str | None = None
    search_in_provisions: bool = True
    search_in_job_descriptions: bool = True
    search_in_allowances: bool = True


@dataclass
class SearchResult:
    """Individual search result with relevance scoring."""

    agreement_id: int
    sector: CCNLSector
    sector_name: str
    agreement_name: str
    relevance_score: float
    matched_fields: list[str] = field(default_factory=list)
    highlights: dict[str, str] = field(default_factory=dict)
    summary: str | None = None

    # Key information
    salary_range: tuple[Decimal, Decimal] | None = None
    vacation_days: int | None = None
    working_hours: int | None = None
    geographic_coverage: list[str] = field(default_factory=list)


@dataclass
class FacetCount:
    """Facet count for search refinement."""

    value: str
    count: int
    display_name: str | None = None


@dataclass
class SearchResponse:
    """Complete search response with results and metadata."""

    results: list[SearchResult]
    total_count: int
    page: int
    page_size: int
    query_time_ms: int

    # Facets for refinement
    facets: dict[str, list[FacetCount]] = field(default_factory=dict)

    # Query understanding
    interpreted_query: str | None = None
    suggested_queries: list[str] = field(default_factory=list)
    spelling_corrections: dict[str, str] = field(default_factory=dict)

    # Statistics
    min_salary: Decimal | None = None
    max_salary: Decimal | None = None
    avg_salary: Decimal | None = None


class NaturalLanguageProcessor:
    """Process natural language queries for CCNL search."""

    def __init__(self):
        """Initialize NLP processor with Italian language patterns."""
        # Sector keywords mapping
        self.sector_keywords = {
            CCNLSector.METALMECCANICI_INDUSTRIA: [
                "metalmeccanici",
                "metalmeccanico",
                "metal",
                "meccanica",
                "industria meccanica",
                "operaio metalmeccanico",
            ],
            CCNLSector.COMMERCIO_TERZIARIO: [
                "commercio",
                "commerciale",
                "negozio",
                "vendita",
                "terziario",
                "commesso",
                "cassiere",
                "retail",
            ],
            CCNLSector.EDILIZIA_INDUSTRIA: [
                "edilizia",
                "edile",
                "costruzione",
                "costruzioni",
                "cantiere",
                "muratore",
                "carpentiere",
                "construction",
            ],
            CCNLSector.TURISMO: [
                "turismo",
                "turistico",
                "hotel",
                "albergo",
                "ristorante",
                "cameriere",
                "receptionist",
                "hospitality",
            ],
            CCNLSector.TRASPORTI_LOGISTICA: [
                "trasporti",
                "trasporto",
                "logistica",
                "autista",
                "spedizioni",
                "magazzino",
                "corriere",
                "delivery",
            ],
        }

        # Worker category patterns
        self.category_patterns = {
            WorkerCategory.OPERAIO: [r"\boperai[oi]?\b", r"\blavorator[ei]\b", r"\baddett[oi]\b"],
            WorkerCategory.IMPIEGATO: [r"\bimpiegat[oi]?\b", r"\bufficio\b", r"\bamministrativ[oi]\b"],
            WorkerCategory.QUADRO: [r"\bquadr[oi]?\b", r"\bresponsabil[ei]\b", r"\bcoordinator[ei]\b"],
            WorkerCategory.DIRIGENTE: [r"\bdirigent[ei]?\b", r"\bdirettor[ei]\b", r"\bmanager\b"],
        }

        # Geographic patterns
        self.geographic_patterns = {
            "nord": ["nord", "settentrionale", "lombardia", "milano", "torino", "veneto"],
            "centro": ["centro", "centrale", "roma", "lazio", "toscana", "firenze"],
            "sud": ["sud", "meridionale", "napoli", "campania", "puglia", "bari"],
            "isole": ["sicilia", "sardegna", "palermo", "cagliari", "isole"],
        }

        # Numeric patterns
        self.salary_pattern = re.compile(
            r"(?:stipendi[oi]?|salari[oi]?|retribuzion[ei]?|paga)\s*(?:di|da|tra)?\s*"
            r"(\d+(?:\.\d+)?)\s*(?:a|e|-)\s*(\d+(?:\.\d+)?)\s*(?:euro|€)?",
            re.IGNORECASE,
        )
        self.experience_pattern = re.compile(r"(\d+)\s*ann[oi]?\s*(?:di\s*)?(?:esperienza|anzianità)", re.IGNORECASE)
        self.hours_pattern = re.compile(r"(\d+)\s*ore\s*(?:settimanal[ei]|a\s*settimana)", re.IGNORECASE)

    def parse_query(self, query: str) -> SearchFilters:
        """Parse natural language query into search filters."""
        query_lower = query.lower()
        filters = SearchFilters()

        # Extract sectors
        detected_sectors = []
        for sector, keywords in self.sector_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_sectors.append(sector)
        if detected_sectors:
            filters.sectors = detected_sectors

        # Extract worker categories
        detected_categories = []
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected_categories.append(category)
                    break
        if detected_categories:
            filters.worker_categories = detected_categories

        # Extract geographic areas
        detected_areas = []
        for area, keywords in self.geographic_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                if area == "nord":
                    detected_areas.append(GeographicArea.NORD)
                elif area == "centro":
                    detected_areas.append(GeographicArea.CENTRO)
                elif area == "sud":
                    detected_areas.append(GeographicArea.SUD)
                elif area == "isole":
                    detected_areas.append(GeographicArea.SUD_ISOLE)
        if detected_areas:
            filters.geographic_areas = detected_areas

        # Extract salary range
        salary_match = self.salary_pattern.search(query)
        if salary_match:
            filters.min_salary = Decimal(salary_match.group(1))
            filters.max_salary = Decimal(salary_match.group(2))
        else:
            # Try to find single salary amount
            single_salary_pattern = re.compile(
                r"(?:stipendi[oi]?|salari[oi]?|paga).*?(\d+).*?(?:euro|€)?", re.IGNORECASE
            )
            single_match = single_salary_pattern.search(query)
            if single_match:
                filters.min_salary = Decimal(single_match.group(1))

        # Extract experience
        experience_match = self.experience_pattern.search(query)
        if experience_match:
            years = int(experience_match.group(1))
            filters.min_experience_months = years * 12

        # Extract working hours
        hours_match = self.hours_pattern.search(query)
        if hours_match:
            filters.max_weekly_hours = int(hours_match.group(1))

        # Check for specific requirements
        if any(word in query_lower for word in ["flessibile", "flessibilità", "flexible"]):
            filters.flexible_hours_required = True

        if any(word in query_lower for word in ["part-time", "part time", "mezza giornata"]):
            filters.part_time_allowed = True

        if any(word in query_lower for word in ["turni", "turno", "shift"]):
            filters.shift_work_allowed = True

        # Extract vacation/leave requirements
        if "ferie" in query_lower or "vacanza" in query_lower:
            filters.leave_types_required = [LeaveType.FERIE]
            # Try to extract minimum days
            vacation_pattern = re.compile(r"(\d+)\s*giorn[oi]?\s*(?:di\s*)?ferie")
            vacation_match = vacation_pattern.search(query_lower)
            if vacation_match:
                filters.min_vacation_days = int(vacation_match.group(1))

        # Set keywords for full-text search
        filters.keywords = query

        return filters

    def suggest_query_improvements(self, query: str, results_count: int) -> list[str]:
        """Suggest query improvements based on results."""
        suggestions = []

        if results_count == 0:
            # Suggest broader queries
            suggestions.append("Prova a rimuovere alcuni filtri per ottenere più risultati")
            suggestions.append("Usa termini più generali come 'commercio' invece di nomi specifici")
        elif results_count > 100:
            # Suggest more specific queries
            suggestions.append("Aggiungi la zona geografica (es. 'nord Italia')")
            suggestions.append("Specifica il livello lavorativo (es. 'impiegato', 'operaio')")
            suggestions.append("Indica l'esperienza richiesta (es. '5 anni esperienza')")

        return suggestions


class CCNLSearchService:
    """Comprehensive search service for CCNL data."""

    def __init__(self):
        """Initialize search service."""
        self.logger = logger
        self.nlp_processor = NaturalLanguageProcessor()
        self._init_search_indexes()

    def _init_search_indexes(self):
        """Initialize search indexes and caches."""
        # Initialize synonym mappings
        self.synonyms = {
            "stipendio": ["salario", "retribuzione", "paga", "compenso"],
            "ferie": ["vacanze", "riposo", "congedo"],
            "operaio": ["lavoratore", "addetto", "manovale"],
            "impiegato": ["amministrativo", "ufficio"],
            "permesso": ["congedo", "assenza"],
            "orario": ["ore", "tempo", "turno"],
        }

        # Common misspellings
        self.common_misspellings = {
            "comercio": "commercio",
            "metalmeccanico": "metalmeccanici",
            "edilizia": "edilizia",
            "transporti": "trasporti",
            "toursimo": "turismo",
        }

    async def search(
        self,
        query: str | None = None,
        filters: SearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "relevance",
        include_facets: bool = True,
    ) -> SearchResponse:
        """Perform comprehensive CCNL search.

        Args:
            query: Natural language search query
            filters: Structured search filters
            page: Page number (1-based)
            page_size: Results per page
            sort_by: Sort order (relevance, salary_asc, salary_desc, name)
            include_facets: Include facet counts for filtering

        Returns:
            SearchResponse with results and metadata
        """
        start_time = datetime.utcnow()

        try:
            # Parse natural language query if provided
            if query and not filters:
                filters = self.nlp_processor.parse_query(query)
            elif query and filters:
                # Merge natural language parsing with provided filters
                nl_filters = self.nlp_processor.parse_query(query)
                filters = self._merge_filters(filters, nl_filters)
            elif not filters:
                filters = SearchFilters()

            # Correct common misspellings in keywords
            if filters.keywords:
                filters.keywords = self._correct_spelling(filters.keywords)

            # Build and execute search query
            search_query = self._build_search_query(filters)

            # Get total count
            count_query = select(func.count()).select_from(search_query.subquery())
            with database_service.get_session_maker() as session:
                total_count = session.exec(count_query).first() or 0

            # Apply pagination
            offset = (page - 1) * page_size
            search_query = search_query.offset(offset).limit(page_size)

            # Apply sorting
            search_query = self._apply_sorting(search_query, sort_by, filters)

            # Execute main search
            with database_service.get_session_maker() as session:
                results_raw = session.exec(search_query).all()

            # Process results
            results = []
            for row in results_raw:
                result = await self._process_search_result(row, filters)
                results.append(result)

            # Calculate facets if requested
            facets = {}
            if include_facets:
                facets = await self._calculate_facets(filters)

            # Calculate statistics
            stats = await self._calculate_statistics(filters)

            # Generate suggestions
            suggestions = self.nlp_processor.suggest_query_improvements(query or filters.keywords or "", total_count)

            query_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return SearchResponse(
                results=results,
                total_count=total_count,
                page=page,
                page_size=page_size,
                query_time_ms=query_time_ms,
                facets=facets,
                interpreted_query=self._explain_filters(filters),
                suggested_queries=suggestions,
                spelling_corrections=self._get_spelling_corrections(filters.keywords) if filters.keywords else {},
                min_salary=stats.get("min_salary"),
                max_salary=stats.get("max_salary"),
                avg_salary=stats.get("avg_salary"),
            )

        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return SearchResponse(results=[], total_count=0, page=page, page_size=page_size, query_time_ms=0)

    def _build_search_query(self, filters: SearchFilters) -> Select:
        """Build SQLAlchemy query from search filters."""
        # Start with base query
        query = (
            select(
                CCNLAgreementDB,
                CCNLSectorDB,
                func.coalesce(func.avg(SalaryTableDB.base_monthly_salary), 0).label("avg_salary"),
            )
            .join(CCNLSectorDB, CCNLAgreementDB.sector_code == CCNLSectorDB.sector_code)
            .outerjoin(SalaryTableDB, CCNLAgreementDB.id == SalaryTableDB.agreement_id)
            .group_by(CCNLAgreementDB.id, CCNLSectorDB.id)
        )

        # Apply filters
        conditions = []

        # Sector filters
        if filters.sectors:
            sector_codes = [s.value for s in filters.sectors]
            conditions.append(CCNLAgreementDB.sector_code.in_(sector_codes))

        # Date filters
        if filters.active_only:
            today = date.today()
            conditions.append(
                and_(
                    CCNLAgreementDB.valid_from <= today,
                    or_(CCNLAgreementDB.valid_to.is_(None), CCNLAgreementDB.valid_to >= today),
                )
            )
        elif filters.valid_on_date:
            conditions.append(
                and_(
                    CCNLAgreementDB.valid_from <= filters.valid_on_date,
                    or_(CCNLAgreementDB.valid_to.is_(None), CCNLAgreementDB.valid_to >= filters.valid_on_date),
                )
            )

        # Apply all conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Apply salary filters using HAVING clause
        having_conditions = []
        if filters.min_salary:
            having_conditions.append(
                func.coalesce(func.avg(SalaryTableDB.base_monthly_salary), 0) >= filters.min_salary
            )
        if filters.max_salary:
            having_conditions.append(
                func.coalesce(func.avg(SalaryTableDB.base_monthly_salary), 0) <= filters.max_salary
            )

        if having_conditions:
            query = query.having(and_(*having_conditions))

        # Apply text search if keywords provided
        if filters.keywords:
            search_conditions = self._build_text_search_conditions(filters.keywords, filters)
            if search_conditions:
                query = query.where(or_(*search_conditions))

        return query

    def _build_text_search_conditions(self, keywords: str, filters: SearchFilters) -> list:
        """Build text search conditions for various fields."""
        conditions = []
        search_terms = keywords.lower().split()

        # Expand search terms with synonyms
        expanded_terms = []
        for term in search_terms:
            expanded_terms.append(term)
            if term in self.synonyms:
                expanded_terms.extend(self.synonyms[term])

        # Search in agreement name and sector name
        for term in expanded_terms:
            pattern = f"%{term}%"
            conditions.append(CCNLAgreementDB.name.ilike(pattern))
            conditions.append(CCNLSectorDB.italian_name.ilike(pattern))

        return conditions

    def _apply_sorting(self, query: Select, sort_by: str, filters: SearchFilters) -> Select:
        """Apply sorting to search query."""
        if sort_by == "salary_asc":
            return query.order_by(func.coalesce(func.avg(SalaryTableDB.base_monthly_salary), 0))
        elif sort_by == "salary_desc":
            return query.order_by(func.coalesce(func.avg(SalaryTableDB.base_monthly_salary), 0).desc())
        elif sort_by == "name":
            return query.order_by(CCNLAgreementDB.name)
        else:  # relevance (default)
            # Simple relevance based on matches
            return query.order_by(CCNLAgreementDB.valid_from.desc())

    async def _process_search_result(self, row: Any, filters: SearchFilters) -> SearchResult:
        """Process raw search result into SearchResult object."""
        agreement, sector, avg_salary = row

        # Get additional information
        with database_service.get_session_maker() as session:
            # Get salary range
            salary_query = select(
                func.min(SalaryTableDB.base_monthly_salary), func.max(SalaryTableDB.base_monthly_salary)
            ).where(SalaryTableDB.agreement_id == agreement.id)
            salary_range = session.exec(salary_query).first()

            # Get vacation days
            vacation_query = select(LeaveEntitlementDB.base_annual_days).where(
                and_(
                    LeaveEntitlementDB.agreement_id == agreement.id,
                    LeaveEntitlementDB.leave_type == LeaveType.FERIE.value,
                )
            )
            vacation_days = session.exec(vacation_query).first()

            # Get working hours
            hours_query = select(WorkingHoursDB.ordinary_weekly_hours).where(
                WorkingHoursDB.agreement_id == agreement.id
            )
            working_hours = session.exec(hours_query).first()

        # Calculate relevance score (simplified)
        relevance_score = 1.0
        matched_fields = []

        if filters.keywords:
            keywords_lower = filters.keywords.lower()
            if keywords_lower in agreement.name.lower():
                relevance_score += 2.0
                matched_fields.append("agreement_name")
            if keywords_lower in sector.italian_name.lower():
                relevance_score += 1.5
                matched_fields.append("sector_name")

        return SearchResult(
            agreement_id=agreement.id,
            sector=CCNLSector(agreement.sector_code),
            sector_name=sector.italian_name,
            agreement_name=agreement.name,
            relevance_score=relevance_score,
            matched_fields=matched_fields,
            salary_range=(salary_range[0], salary_range[1]) if salary_range[0] else None,
            vacation_days=vacation_days,
            working_hours=working_hours,
            summary=self._generate_result_summary(agreement, sector),
        )

    def _generate_result_summary(self, agreement: CCNLAgreementDB, sector: CCNLSectorDB) -> str:
        """Generate a summary for search result."""
        summary_parts = []

        if agreement.is_currently_valid():
            summary_parts.append("Attualmente in vigore")
        else:
            summary_parts.append("Scaduto")

        if agreement.valid_to:
            summary_parts.append(f"Valido fino al {agreement.valid_to.strftime('%d/%m/%Y')}")

        if agreement.signatory_unions:
            summary_parts.append(f"Firmato da {len(agreement.signatory_unions)} sindacati")

        return " • ".join(summary_parts)

    async def _calculate_facets(self, filters: SearchFilters) -> dict[str, list[FacetCount]]:
        """Calculate facet counts for search refinement."""
        facets = {}

        with database_service.get_session_maker() as session:
            # Sector facets
            sector_query = (
                select(CCNLSectorDB.sector_code, CCNLSectorDB.italian_name, func.count(CCNLAgreementDB.id))
                .join(CCNLAgreementDB, CCNLSectorDB.sector_code == CCNLAgreementDB.sector_code)
                .group_by(CCNLSectorDB.sector_code, CCNLSectorDB.italian_name)
            )

            sector_results = session.exec(sector_query).all()
            facets["sectors"] = [
                FacetCount(value=code, count=count, display_name=name) for code, name, count in sector_results
            ]

            # Worker category facets (from job levels)
            category_query = select(
                JobLevelDB.worker_category, func.count(func.distinct(JobLevelDB.agreement_id))
            ).group_by(JobLevelDB.worker_category)

            category_results = session.exec(category_query).all()
            facets["worker_categories"] = [
                FacetCount(value=category, count=count, display_name=WorkerCategory(category).italian_name())
                for category, count in category_results
            ]

            # Geographic area facets
            area_query = select(
                SalaryTableDB.geographic_area, func.count(func.distinct(SalaryTableDB.agreement_id))
            ).group_by(SalaryTableDB.geographic_area)

            area_results = session.exec(area_query).all()
            facets["geographic_areas"] = [
                FacetCount(value=area, count=count, display_name=area.replace("_", " ").title())
                for area, count in area_results
            ]

        return facets

    async def _calculate_statistics(self, filters: SearchFilters) -> dict[str, Any]:
        """Calculate statistics for search results."""
        stats = {}

        with database_service.get_session_maker() as session:
            # Build base query for statistics
            query = select(
                func.min(SalaryTableDB.base_monthly_salary),
                func.max(SalaryTableDB.base_monthly_salary),
                func.avg(SalaryTableDB.base_monthly_salary),
            ).join(CCNLAgreementDB, SalaryTableDB.agreement_id == CCNLAgreementDB.id)

            # Apply sector filter if present
            if filters.sectors:
                sector_codes = [s.value for s in filters.sectors]
                query = query.where(CCNLAgreementDB.sector_code.in_(sector_codes))

            result = session.exec(query).first()
            if result:
                stats["min_salary"] = result[0]
                stats["max_salary"] = result[1]
                stats["avg_salary"] = result[2]

        return stats

    def _merge_filters(self, filters1: SearchFilters, filters2: SearchFilters) -> SearchFilters:
        """Merge two sets of search filters."""
        merged = SearchFilters()

        # Merge lists (union)
        for field in ["sectors", "geographic_areas", "worker_categories", "required_allowances"]:
            val1 = getattr(filters1, field) or []
            val2 = getattr(filters2, field) or []
            merged_val = list(set(val1 + val2)) if val1 or val2 else None
            setattr(merged, field, merged_val)

        # Take more restrictive values for min/max
        merged.min_salary = max(filters1.min_salary or 0, filters2.min_salary or 0) or None
        merged.max_salary = (
            min(filters1.max_salary or Decimal("999999"), filters2.max_salary or Decimal("999999"))
            if filters1.max_salary or filters2.max_salary
            else None
        )

        # Merge booleans (AND logic)
        for field in ["active_only", "flexible_hours_required", "part_time_allowed"]:
            setattr(merged, field, getattr(filters1, field) and getattr(filters2, field))

        # Merge keywords
        keywords = []
        if filters1.keywords:
            keywords.append(filters1.keywords)
        if filters2.keywords:
            keywords.append(filters2.keywords)
        merged.keywords = " ".join(keywords) if keywords else None

        return merged

    def _correct_spelling(self, text: str) -> str:
        """Correct common misspellings in search text."""
        words = text.split()
        corrected_words = []

        for word in words:
            word_lower = word.lower()
            if word_lower in self.common_misspellings:
                corrected_words.append(self.common_misspellings[word_lower])
            else:
                corrected_words.append(word)

        return " ".join(corrected_words)

    def _get_spelling_corrections(self, text: str) -> dict[str, str]:
        """Get spelling corrections made to the query."""
        corrections = {}
        words = text.split()

        for word in words:
            word_lower = word.lower()
            if word_lower in self.common_misspellings:
                corrections[word] = self.common_misspellings[word_lower]

        return corrections

    def _explain_filters(self, filters: SearchFilters) -> str:
        """Generate human-readable explanation of applied filters."""
        explanations = []

        if filters.sectors:
            sector_names = [s.italian_name() for s in filters.sectors]
            explanations.append(f"Settore: {', '.join(sector_names)}")

        if filters.worker_categories:
            category_names = [c.italian_name() for c in filters.worker_categories]
            explanations.append(f"Categoria: {', '.join(category_names)}")

        if filters.geographic_areas:
            area_names = [a.value.replace("_", " ").title() for a in filters.geographic_areas]
            explanations.append(f"Area geografica: {', '.join(area_names)}")

        if filters.min_salary or filters.max_salary:
            if filters.min_salary and filters.max_salary:
                explanations.append(f"Stipendio: €{filters.min_salary} - €{filters.max_salary}")
            elif filters.min_salary:
                explanations.append(f"Stipendio minimo: €{filters.min_salary}")
            else:
                explanations.append(f"Stipendio massimo: €{filters.max_salary}")

        return " | ".join(explanations) if explanations else "Tutti i CCNL"

    async def search_by_sector(self, sectors: list[CCNLSector], include_related: bool = True) -> SearchResponse:
        """Search CCNL agreements by sector with optional related sectors."""
        filters = SearchFilters(sectors=sectors)

        if include_related:
            # Add related sectors based on similarity
            related_sectors = self._get_related_sectors(sectors)
            filters.sectors.extend(related_sectors)

        return await self.search(filters=filters)

    def _get_related_sectors(self, sectors: list[CCNLSector]) -> list[CCNLSector]:
        """Get related sectors based on similarity."""
        related = []

        # Define sector relationships
        sector_relationships = {
            CCNLSector.METALMECCANICI_INDUSTRIA: [CCNLSector.METALMECCANICI_ARTIGIANI],
            CCNLSector.EDILIZIA_INDUSTRIA: [CCNLSector.EDILIZIA_ARTIGIANATO],
            CCNLSector.COMMERCIO_TERZIARIO: [CCNLSector.PUBBLICI_ESERCIZI, CCNLSector.TURISMO],
            CCNLSector.TRASPORTI_LOGISTICA: [CCNLSector.SERVIZI_PULIZIA],
        }

        for sector in sectors:
            if sector in sector_relationships:
                related.extend(sector_relationships[sector])

        return list(set(related) - set(sectors))

    async def search_by_geographic_area(
        self, areas: list[GeographicArea], regions: list[str] | None = None, provinces: list[str] | None = None
    ) -> SearchResponse:
        """Search CCNL agreements by geographic area."""
        filters = SearchFilters(geographic_areas=areas, regions=regions, provinces=provinces)

        return await self.search(filters=filters)

    async def search_by_salary_range(
        self, min_salary: Decimal | None, max_salary: Decimal | None, include_benefits: bool = True
    ) -> SearchResponse:
        """Search CCNL agreements by salary range."""
        filters = SearchFilters(
            min_salary=min_salary,
            max_salary=max_salary,
            include_thirteenth=include_benefits,
            include_fourteenth=include_benefits,
        )

        return await self.search(filters=filters)

    async def search_by_job_category(
        self, categories: list[WorkerCategory], experience_years: int | None = None
    ) -> SearchResponse:
        """Search CCNL agreements by job category."""
        filters = SearchFilters(worker_categories=categories)

        if experience_years:
            filters.min_experience_months = experience_years * 12

        return await self.search(filters=filters)

    async def compare_sectors(
        self, sector1: CCNLSector, sector2: CCNLSector, comparison_aspects: list[str]
    ) -> dict[str, Any]:
        """Compare two sectors across multiple aspects."""
        comparison = {
            "sector1": {"code": sector1.value, "name": sector1.italian_name()},
            "sector2": {"code": sector2.value, "name": sector2.italian_name()},
            "differences": {},
            "similarities": {},
        }

        with database_service.get_session_maker() as session:
            # Get current agreements for both sectors
            agreement1 = session.exec(
                select(CCNLAgreementDB)
                .where(CCNLAgreementDB.sector_code == sector1.value)
                .order_by(CCNLAgreementDB.valid_from.desc())
            ).first()

            agreement2 = session.exec(
                select(CCNLAgreementDB)
                .where(CCNLAgreementDB.sector_code == sector2.value)
                .order_by(CCNLAgreementDB.valid_from.desc())
            ).first()

            if not agreement1 or not agreement2:
                return comparison

            # Compare salary ranges
            if "salary" in comparison_aspects:
                salary1 = session.exec(
                    select(
                        func.min(SalaryTableDB.base_monthly_salary),
                        func.max(SalaryTableDB.base_monthly_salary),
                        func.avg(SalaryTableDB.base_monthly_salary),
                    ).where(SalaryTableDB.agreement_id == agreement1.id)
                ).first()

                salary2 = session.exec(
                    select(
                        func.min(SalaryTableDB.base_monthly_salary),
                        func.max(SalaryTableDB.base_monthly_salary),
                        func.avg(SalaryTableDB.base_monthly_salary),
                    ).where(SalaryTableDB.agreement_id == agreement2.id)
                ).first()

                comparison["differences"]["salary"] = {
                    "sector1": {
                        "min": float(salary1[0]) if salary1[0] else 0,
                        "max": float(salary1[1]) if salary1[1] else 0,
                        "avg": float(salary1[2]) if salary1[2] else 0,
                    },
                    "sector2": {
                        "min": float(salary2[0]) if salary2[0] else 0,
                        "max": float(salary2[1]) if salary2[1] else 0,
                        "avg": float(salary2[2]) if salary2[2] else 0,
                    },
                }

            # Compare vacation days
            if "vacation" in comparison_aspects:
                vacation1 = session.exec(
                    select(LeaveEntitlementDB).where(
                        and_(
                            LeaveEntitlementDB.agreement_id == agreement1.id,
                            LeaveEntitlementDB.leave_type == LeaveType.FERIE.value,
                        )
                    )
                ).first()

                vacation2 = session.exec(
                    select(LeaveEntitlementDB).where(
                        and_(
                            LeaveEntitlementDB.agreement_id == agreement2.id,
                            LeaveEntitlementDB.leave_type == LeaveType.FERIE.value,
                        )
                    )
                ).first()

                if vacation1 and vacation2:
                    comparison["differences"]["vacation"] = {
                        "sector1": vacation1.base_annual_days,
                        "sector2": vacation2.base_annual_days,
                        "difference": (vacation1.base_annual_days or 0) - (vacation2.base_annual_days or 0),
                    }

            # Compare working hours
            if "hours" in comparison_aspects:
                hours1 = session.exec(
                    select(WorkingHoursDB).where(WorkingHoursDB.agreement_id == agreement1.id)
                ).first()

                hours2 = session.exec(
                    select(WorkingHoursDB).where(WorkingHoursDB.agreement_id == agreement2.id)
                ).first()

                if hours1 and hours2:
                    comparison["differences"]["working_hours"] = {
                        "sector1": hours1.ordinary_weekly_hours,
                        "sector2": hours2.ordinary_weekly_hours,
                        "difference": hours1.ordinary_weekly_hours - hours2.ordinary_weekly_hours,
                    }

        return comparison

    async def get_popular_searches(self) -> list[str]:
        """Get popular search queries."""
        return [
            "metalmeccanici milano stipendio",
            "commercio terziario ferie",
            "edilizia operaio 5 anni esperienza",
            "turismo cameriere part-time",
            "trasporti autista turni notturni",
            "impiegato amministrativo nord italia",
            "quadro responsabile produzione",
            "apprendista meccanico primo livello",
        ]

    async def autocomplete(self, partial_query: str, limit: int = 10) -> list[str]:
        """Provide autocomplete suggestions for search queries."""
        suggestions = []
        partial_lower = partial_query.lower()

        # Sector suggestions
        for sector in CCNLSector:
            if partial_lower in sector.italian_name().lower():
                suggestions.append(sector.italian_name())

        # Category suggestions
        for category in WorkerCategory:
            if partial_lower in category.italian_name().lower():
                suggestions.append(category.italian_name())

        # Common search terms
        common_terms = [
            "stipendio",
            "salario",
            "ferie",
            "permessi",
            "orario",
            "turni",
            "straordinari",
            "tredicesima",
            "quattordicesima",
            "nord",
            "centro",
            "sud",
            "milano",
            "roma",
            "napoli",
        ]

        for term in common_terms:
            if partial_lower in term:
                suggestions.append(term)

        # Use simple fuzzy matching for better suggestions
        if len(suggestions) < limit:
            all_terms = []
            for keywords in self.sector_keywords.values():
                all_terms.extend(keywords)
            all_terms.extend(common_terms)

            # Simple fuzzy matching using difflib
            fuzzy_matches = difflib.get_close_matches(
                partial_query.lower(), all_terms, n=limit - len(suggestions), cutoff=0.6
            )
            suggestions.extend(fuzzy_matches)

        return suggestions[:limit]


# Service instance
ccnl_search_service = CCNLSearchService()
