"""CCNL Search Examples.

This module demonstrates various search capabilities of the CCNL search system,
including natural language queries, faceted search, and comparisons.
"""

import asyncio
from decimal import Decimal
from typing import Any, Dict, List

from app.models.ccnl_data import AllowanceType, CCNLSector, CompanySize, GeographicArea, LeaveType, WorkerCategory
from app.services.ccnl_search_service import SearchFilters, ccnl_search_service


async def example_natural_language_search():
    """Demonstrate natural language search capabilities."""
    print("\n=== Natural Language Search Examples ===\n")

    queries = [
        "operaio metalmeccanico milano con 5 anni esperienza",
        "commercio part-time nord italia stipendio minimo 1500",
        "edilizia muratore ferie 30 giorni",
        "turismo cameriere turni weekend roma",
        "impiegato amministrativo quadro con buoni pasto",
        "trasporti autista notturno straordinari",
        "tessile operaio specializzato toscana",
        "dirigente IT stipendio tra 5000 e 8000 euro",
    ]

    for query in queries:
        print(f"Query: '{query}'")
        response = await ccnl_search_service.search(query=query, page_size=5)

        print(f"Found {response.total_count} results in {response.query_time_ms}ms")
        print(f"Interpreted as: {response.interpreted_query}")

        if response.spelling_corrections:
            print(f"Spelling corrections: {response.spelling_corrections}")

        if response.results:
            print("Top results:")
            for i, result in enumerate(response.results[:3], 1):
                print(f"  {i}. {result.agreement_name} ({result.sector_name})")
                print(f"     Relevance: {result.relevance_score:.2f}")
                if result.salary_range:
                    print(f"     Salary: €{result.salary_range[0]:.2f} - €{result.salary_range[1]:.2f}")
                if result.vacation_days:
                    print(f"     Vacation: {result.vacation_days} days")

        if response.suggested_queries:
            print(f"Suggestions: {', '.join(response.suggested_queries[:2])}")

        print("-" * 50)


async def example_faceted_search():
    """Demonstrate faceted search with refinement."""
    print("\n=== Faceted Search Example ===\n")

    # Initial broad search
    print("1. Initial search for all metalworking agreements:")
    response = await ccnl_search_service.search(
        filters=SearchFilters(sectors=[CCNLSector.METALMECCANICI_INDUSTRIA]), include_facets=True
    )

    print(f"Found {response.total_count} agreements")

    # Show facets
    print("\nAvailable facets for refinement:")
    for facet_type, facets in response.facets.items():
        print(f"\n{facet_type}:")
        for facet in facets[:5]:  # Top 5
            print(f"  - {facet.display_name or facet.value}: {facet.count}")

    # Refine search using facets
    print("\n2. Refined search - Northern Italy, Operaio category:")
    refined_response = await ccnl_search_service.search(
        filters=SearchFilters(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA],
            geographic_areas=[GeographicArea.NORD],
            worker_categories=[WorkerCategory.OPERAIO],
        ),
        include_facets=True,
    )

    print(f"Refined to {refined_response.total_count} agreements")

    # Further refinement with salary
    print("\n3. Further refined - Salary €1800-2500:")
    final_response = await ccnl_search_service.search(
        filters=SearchFilters(
            sectors=[CCNLSector.METALMECCANICI_INDUSTRIA],
            geographic_areas=[GeographicArea.NORD],
            worker_categories=[WorkerCategory.OPERAIO],
            min_salary=Decimal("1800"),
            max_salary=Decimal("2500"),
        )
    )

    print(f"Final results: {final_response.total_count} agreements")
    print(f"Average salary in results: €{final_response.avg_salary:.2f}")


async def example_complex_filters():
    """Demonstrate complex filtering capabilities."""
    print("\n=== Complex Filter Example ===\n")

    filters = SearchFilters(
        # Multiple sectors
        sectors=[CCNLSector.COMMERCIO_TERZIARIO, CCNLSector.TURISMO],
        # Geographic restriction
        geographic_areas=[GeographicArea.CENTRO, GeographicArea.NORD],
        regions=["lazio", "toscana", "lombardia"],
        # Worker specifications
        worker_categories=[WorkerCategory.IMPIEGATO],
        min_experience_months=36,  # 3 years
        # Salary requirements
        min_salary=Decimal("2000"),
        max_salary=Decimal("3500"),
        include_thirteenth=True,
        include_fourteenth=True,
        # Working conditions
        max_weekly_hours=40,
        flexible_hours_required=True,
        part_time_allowed=True,
        # Benefits
        min_vacation_days=26,
        required_allowances=[AllowanceType.BUONI_PASTO],
        company_sizes=[CompanySize.MEDIUM, CompanySize.LARGE],
        # Only active agreements
        active_only=True,
    )

    response = await ccnl_search_service.search(filters=filters)

    print(f"Complex search found {response.total_count} matching agreements")

    if response.results:
        print("\nMatching agreements:")
        for result in response.results[:5]:
            print(f"\n- {result.agreement_name}")
            print(f"  Sector: {result.sector_name}")
            print(f"  Salary range: €{result.salary_range[0]:.2f} - €{result.salary_range[1]:.2f}")
            print(f"  Vacation days: {result.vacation_days}")
            print(f"  Working hours: {result.working_hours}/week")
            print(f"  Matched fields: {', '.join(result.matched_fields)}")


async def example_sector_comparison():
    """Demonstrate sector comparison functionality."""
    print("\n=== Sector Comparison Example ===\n")

    comparison = await ccnl_search_service.compare_sectors(
        sector1=CCNLSector.METALMECCANICI_INDUSTRIA,
        sector2=CCNLSector.COMMERCIO_TERZIARIO,
        comparison_aspects=["salary", "vacation", "hours", "notice", "allowances"],
    )

    print(f"Comparing {comparison['sector1']['name']} vs {comparison['sector2']['name']}")

    if "salary" in comparison["differences"]:
        salary_diff = comparison["differences"]["salary"]
        print("\nSalary comparison:")
        print(f"  {comparison['sector1']['name']}:")
        print(f"    Average: €{salary_diff['sector1']['avg']:.2f}")
        print(f"    Range: €{salary_diff['sector1']['min']:.2f} - €{salary_diff['sector1']['max']:.2f}")
        print(f"  {comparison['sector2']['name']}:")
        print(f"    Average: €{salary_diff['sector2']['avg']:.2f}")
        print(f"    Range: €{salary_diff['sector2']['min']:.2f} - €{salary_diff['sector2']['max']:.2f}")

    if "vacation" in comparison["differences"]:
        vacation_diff = comparison["differences"]["vacation"]
        print("\nVacation days comparison:")
        print(f"  {comparison['sector1']['name']}: {vacation_diff['sector1']} days")
        print(f"  {comparison['sector2']['name']}: {vacation_diff['sector2']} days")
        print(f"  Difference: {vacation_diff['difference']} days")

    if "hours" in comparison["differences"]:
        hours_diff = comparison["differences"]["working_hours"]
        print("\nWorking hours comparison:")
        print(f"  {comparison['sector1']['name']}: {hours_diff['sector1']} hours/week")
        print(f"  {comparison['sector2']['name']}: {hours_diff['sector2']} hours/week")


async def example_search_by_specific_criteria():
    """Demonstrate specific search methods."""
    print("\n=== Specific Search Criteria Examples ===\n")

    # Search by geographic area
    print("1. Search by geographic area (Southern Italy + Islands):")
    geo_response = await ccnl_search_service.search_by_geographic_area(
        areas=[GeographicArea.SUD, GeographicArea.SUD_ISOLE], regions=["campania", "sicilia", "puglia"]
    )
    print(f"   Found {geo_response.total_count} agreements")

    # Search by salary range
    print("\n2. Search by salary range (€2500-4000):")
    salary_response = await ccnl_search_service.search_by_salary_range(
        min_salary=Decimal("2500"), max_salary=Decimal("4000"), include_benefits=True
    )
    print(f"   Found {salary_response.total_count} agreements")
    print(f"   Average salary: €{salary_response.avg_salary:.2f}")

    # Search by job category with experience
    print("\n3. Search for experienced quadri (5+ years):")
    category_response = await ccnl_search_service.search_by_job_category(
        categories=[WorkerCategory.QUADRO], experience_years=5
    )
    print(f"   Found {category_response.total_count} agreements")

    # Search by sector with related sectors
    print("\n4. Search construction sector (including related):")
    sector_response = await ccnl_search_service.search_by_sector(
        sectors=[CCNLSector.EDILIZIA_INDUSTRIA], include_related=True
    )
    print(f"   Found {sector_response.total_count} agreements")


async def example_autocomplete():
    """Demonstrate autocomplete functionality."""
    print("\n=== Autocomplete Examples ===\n")

    partial_queries = ["metal", "comm", "stipen", "fer", "milan", "oper"]

    for partial in partial_queries:
        suggestions = await ccnl_search_service.autocomplete(partial, limit=5)
        print(f"'{partial}' -> {suggestions}")


async def example_query_understanding():
    """Demonstrate query understanding and interpretation."""
    print("\n=== Query Understanding Examples ===\n")

    test_queries = [
        {
            "query": "metalworker milan 2000 euro overtime",
            "expected": "English query with sector, location, salary, and overtime",
        },
        {
            "query": "comercio roma flessibile",  # Misspelled commercio
            "expected": "Italian query with spelling error",
        },
        {
            "query": "construction worker 10 years experience vacation 30 days",
            "expected": "Complex requirements with experience and vacation",
        },
        {
            "query": "What are the salary ranges for metalworkers in Northern Italy?",
            "expected": "Natural question format",
        },
        {"query": "Compare vacation days between commerce and manufacturing sectors", "expected": "Comparison query"},
    ]

    for test in test_queries:
        print(f"\nQuery: '{test['query']}'")
        print(f"Expected: {test['expected']}")

        response = await ccnl_search_service.search(query=test["query"], page_size=3)

        print(f"Interpreted as: {response.interpreted_query}")
        if response.spelling_corrections:
            print(f"Corrections: {response.spelling_corrections}")
        print(f"Results found: {response.total_count}")


async def main():
    """Run all examples."""
    print("=" * 80)
    print("CCNL SEARCH SYSTEM EXAMPLES")
    print("=" * 80)

    # Run examples
    await example_natural_language_search()
    await example_faceted_search()
    await example_complex_filters()
    await example_sector_comparison()
    await example_search_by_specific_criteria()
    await example_autocomplete()
    await example_query_understanding()

    print("\n" + "=" * 80)
    print("EXAMPLES COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
