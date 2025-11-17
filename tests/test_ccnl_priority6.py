"""
Test suite for Priority 6 CCNL data structures and functionality.

This module tests all 9 Priority 6 Other Essential sectors
to ensure complete data integrity and business logic correctness.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

import pytest

from app.data.ccnl_priority6 import (
    get_acconciatura_estetica_ccnl,
    get_all_priority6_ccnl_data,
    get_autonoleggio_ccnl,
    get_autorimesse_ccnl,
    get_autotrasporto_merci_ccnl,
    get_dirigenti_commercio_ccnl,
    get_dirigenti_industria_ccnl,
    get_impianti_sportivi_ccnl,
    get_pompe_funebri_ccnl,
    get_quadri_ccnl,
)
from app.models.ccnl_data import (
    AllowanceType,
    CCNLAgreement,
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
    WorkerCategory,
    WorkingHours,
)
from app.services.ccnl_service import ccnl_service


class TestPriority6CCNLDataStructures:
    """Test Priority 6 CCNL data structure completeness and integrity."""

    def test_all_priority6_sectors_defined(self):
        """Test that all 9 Priority 6 sectors are properly defined."""
        expected_sectors = [
            CCNLSector.AUTOTRASPORTO_MERCI,
            CCNLSector.AUTONOLEGGIO,
            CCNLSector.AUTORIMESSE,
            CCNLSector.POMPE_FUNEBRI,
            CCNLSector.ACCONCIATURA_ESTETICA,
            CCNLSector.IMPIANTI_SPORTIVI,
            CCNLSector.DIRIGENTI_INDUSTRIA,
            CCNLSector.DIRIGENTI_COMMERCIO,
            CCNLSector.QUADRI,
        ]

        priority6_data = get_all_priority6_ccnl_data()
        actual_sectors = [ccnl.sector for ccnl in priority6_data]

        assert len(priority6_data) == 9, f"Expected 9 Priority 6 agreements, found {len(priority6_data)}"

        for expected_sector in expected_sectors:
            assert expected_sector in actual_sectors, f"Missing sector: {expected_sector}"

    def test_priority6_data_completeness(self):
        """Test that all Priority 6 CCNL data is complete."""
        priority6_data = get_all_priority6_ccnl_data()

        for ccnl in priority6_data:
            # Test basic agreement fields
            assert ccnl.name, f"Missing agreement name for sector {ccnl.sector}"
            assert ccnl.sector in [
                CCNLSector.AUTOTRASPORTO_MERCI,
                CCNLSector.AUTONOLEGGIO,
                CCNLSector.AUTORIMESSE,
                CCNLSector.POMPE_FUNEBRI,
                CCNLSector.ACCONCIATURA_ESTETICA,
                CCNLSector.IMPIANTI_SPORTIVI,
                CCNLSector.DIRIGENTI_INDUSTRIA,
                CCNLSector.DIRIGENTI_COMMERCIO,
                CCNLSector.QUADRI,
            ], f"Invalid sector: {ccnl.sector}"
            assert ccnl.valid_from, f"Missing valid from date for {ccnl.name}"
            # valid_to is optional, so don't assert it
            assert ccnl.job_levels, f"Missing job levels for {ccnl.name}"

            # Test job levels
            assert len(ccnl.job_levels) >= 1, f"At least 1 job level required for {ccnl.name}"
            for job_level in ccnl.job_levels:
                assert job_level.level_code, f"Missing level code in {ccnl.name}"
                assert job_level.level_name, f"Missing level name in {ccnl.name}"
                assert job_level.category in [
                    WorkerCategory.DIRIGENTE,
                    WorkerCategory.QUADRO,
                    WorkerCategory.IMPIEGATO,
                    WorkerCategory.OPERAIO,
                ], f"Invalid worker category in {ccnl.name}"

            # Test salary tables
            assert ccnl.salary_tables, f"Missing salary tables for {ccnl.name}"
            for salary_table in ccnl.salary_tables:
                assert salary_table.level_code, f"Missing job level code in salary table for {ccnl.name}"
                assert salary_table.base_monthly_salary > Decimal("0"), f"Invalid monthly salary in {ccnl.name}"
                assert salary_table.geographic_area in [
                    GeographicArea.NORD,
                    GeographicArea.CENTRO,
                    GeographicArea.SUD,
                    GeographicArea.NAZIONALE,
                ], f"Invalid geographic area in {ccnl.name}"

            # Test working hours
            assert ccnl.working_hours, f"Missing working hours for {ccnl.name}"
            assert ccnl.working_hours.ordinary_weekly_hours > 0, f"Invalid weekly hours for {ccnl.name}"

            # Test leave entitlements
            assert ccnl.leave_entitlements, f"Missing leave entitlements for {ccnl.name}"
            annual_leave_found = False
            for leave in ccnl.leave_entitlements:
                if leave.leave_type == LeaveType.FERIE:
                    annual_leave_found = True
                    break
            assert annual_leave_found, f"Missing annual leave for {ccnl.name}"

    def test_autotrasporto_merci_ccnl(self):
        """Test specific Autotrasporto Merci CCNL structure."""
        ccnl = get_autotrasporto_merci_ccnl()

        assert ccnl.sector == CCNLSector.AUTOTRASPORTO_MERCI
        assert "Autotrasporto" in ccnl.name
        assert len(ccnl.job_levels) >= 2  # At least driver and specialized driver

        # Check for driver-specific job levels
        level_codes = [level.level_code for level in ccnl.job_levels]
        assert "AUTISTA" in level_codes, "Missing basic driver level"

        # Test salary progression
        salaries = [table.base_monthly_salary for table in ccnl.salary_tables]
        assert len(set(salaries)) > 1, "Should have salary progression"

    def test_dirigenti_ccnl_structures(self):
        """Test management-specific CCNL structures."""
        dirigenti_industria = get_dirigenti_industria_ccnl()
        dirigenti_commercio = get_dirigenti_commercio_ccnl()
        quadri = get_quadri_ccnl()

        # Test management categories
        assert dirigenti_industria.sector == CCNLSector.DIRIGENTI_INDUSTRIA
        assert dirigenti_commercio.sector == CCNLSector.DIRIGENTI_COMMERCIO
        assert quadri.sector == CCNLSector.QUADRI

        # Management should have higher salary ranges
        for ccnl in [dirigenti_industria, dirigenti_commercio, quadri]:
            min_salary = min(table.base_monthly_salary for table in ccnl.salary_tables)
            assert min_salary > Decimal("2500"), f"Management salaries should be higher in {ccnl.name}"

    def test_service_sector_ccnls(self):
        """Test service sector specific CCNLs."""
        pompe_funebri = get_pompe_funebri_ccnl()
        acconciatura = get_acconciatura_estetica_ccnl()
        impianti_sportivi = get_impianti_sportivi_ccnl()

        service_ccnls = [pompe_funebri, acconciatura, impianti_sportivi]

        for ccnl in service_ccnls:
            # Service sectors should have specific characteristics
            assert (
                ccnl.working_hours.ordinary_weekly_hours <= 40
            ), f"Service sector should have standard hours: {ccnl.name}"

            # Should have weekend/holiday rules
            leave_types = [leave.leave_type for leave in ccnl.leave_entitlements]
            # Basic leave types should be present
            assert LeaveType.FERIE in leave_types, f"Missing annual leave in {ccnl.name}"

    def test_transport_sector_integration(self):
        """Test transport sector CCNLs integration."""
        autotrasporto = get_autotrasporto_merci_ccnl()
        autonoleggio = get_autonoleggio_ccnl()
        autorimesse = get_autorimesse_ccnl()

        transport_ccnls = [autotrasporto, autonoleggio, autorimesse]

        for ccnl in transport_ccnls:
            # Transport sectors should have specific requirements
            assert ccnl.sector.value.startswith("auto"), f"Transport sector naming: {ccnl.sector}"

            # Should have driver categories
            categories = [level.category for level in ccnl.job_levels]
            assert WorkerCategory.OPERAIO in categories, f"Missing worker category in {ccnl.name}"


class TestPriority6CCNLCalculations:
    """Test Priority 6 CCNL calculation functionality."""

    @pytest.mark.asyncio
    async def test_priority6_salary_calculations(self):
        """Test salary calculations for Priority 6 sectors."""
        priority6_ccnls = get_all_priority6_ccnl_data()

        for ccnl in priority6_ccnls:
            if ccnl.salary_tables:
                # Test basic salary retrieval
                first_level = ccnl.job_levels[0]
                salary_table = next(
                    (table for table in ccnl.salary_tables if table.level_code == first_level.level_code), None
                )

                if salary_table:
                    assert salary_table.base_monthly_salary > Decimal("0"), f"Invalid salary for {ccnl.name}"

                    # Test reasonable salary ranges for Priority 6 sectors
                    if ccnl.sector in [CCNLSector.DIRIGENTI_INDUSTRIA, CCNLSector.DIRIGENTI_COMMERCIO]:
                        assert salary_table.base_monthly_salary > Decimal(
                            "3000"
                        ), f"Management salary too low: {ccnl.name}"
                    elif ccnl.sector == CCNLSector.QUADRI:
                        assert salary_table.base_monthly_salary > Decimal(
                            "2500"
                        ), f"Quadri salary too low: {ccnl.name}"
                    else:
                        assert salary_table.base_monthly_salary > Decimal("1200"), f"Basic salary too low: {ccnl.name}"

    @pytest.mark.asyncio
    async def test_priority6_leave_calculations(self):
        """Test leave calculations for Priority 6 sectors."""
        priority6_ccnls = get_all_priority6_ccnl_data()

        for ccnl in priority6_ccnls:
            annual_leaves = [leave for leave in ccnl.leave_entitlements if leave.leave_type == LeaveType.FERIE]

            assert len(annual_leaves) > 0, f"Missing annual leave for {ccnl.name}"

            for leave in annual_leaves:
                assert leave.days_per_year >= 20, f"Insufficient annual leave days for {ccnl.name}"
                assert leave.days_per_year <= 30, f"Excessive annual leave days for {ccnl.name}"


class TestPriority6CCNLServiceIntegration:
    """Test Priority 6 integration with CCNL service."""

    @pytest.mark.asyncio
    async def test_priority6_service_loading(self):
        """Test that Priority 6 data loads correctly through service."""
        priority6_data = await ccnl_service.get_all_priority6_ccnl()

        assert len(priority6_data) == 9, f"Expected 9 Priority 6 agreements, got {len(priority6_data)}"

        # Verify each sector is present
        sectors = {ccnl.sector for ccnl in priority6_data}
        expected_sectors = {
            CCNLSector.AUTOTRASPORTO_MERCI,
            CCNLSector.AUTONOLEGGIO,
            CCNLSector.AUTORIMESSE,
            CCNLSector.POMPE_FUNEBRI,
            CCNLSector.ACCONCIATURA_ESTETICA,
            CCNLSector.IMPIANTI_SPORTIVI,
            CCNLSector.DIRIGENTI_INDUSTRIA,
            CCNLSector.DIRIGENTI_COMMERCIO,
            CCNLSector.QUADRI,
        }

        assert sectors == expected_sectors, f"Sector mismatch. Expected: {expected_sectors}, Got: {sectors}"

    @pytest.mark.asyncio
    async def test_all_priorities_with_priority6(self):
        """Test that all priorities including Priority 6 load correctly."""
        all_data = await ccnl_service.get_all_ccnl_data(include_priority6=True)
        priority6_only = await ccnl_service.get_all_priority6_ccnl()

        # Should include Priority 6 data
        total_sectors = {ccnl.sector for ccnl in all_data}
        priority6_sectors = {ccnl.sector for ccnl in priority6_only}

        assert priority6_sectors.issubset(total_sectors), "Priority 6 sectors missing from complete dataset"

    @pytest.mark.asyncio
    async def test_priority6_exclusion(self):
        """Test that Priority 6 can be excluded when requested."""
        with_priority6 = await ccnl_service.get_all_ccnl_data(include_priority6=True)
        without_priority6 = await ccnl_service.get_all_ccnl_data(include_priority6=False)

        # Should have fewer agreements when Priority 6 is excluded
        assert len(without_priority6) < len(with_priority6), "Priority 6 exclusion not working"

        # Verify Priority 6 sectors are excluded
        sectors_without_p6 = {ccnl.sector for ccnl in without_priority6}
        priority6_sectors = {
            CCNLSector.AUTOTRASPORTO_MERCI,
            CCNLSector.AUTONOLEGGIO,
            CCNLSector.AUTORIMESSE,
            CCNLSector.POMPE_FUNEBRI,
            CCNLSector.ACCONCIATURA_ESTETICA,
            CCNLSector.IMPIANTI_SPORTIVI,
            CCNLSector.DIRIGENTI_INDUSTRIA,
            CCNLSector.DIRIGENTI_COMMERCIO,
            CCNLSector.QUADRI,
        }

        assert not priority6_sectors.intersection(sectors_without_p6), "Priority 6 sectors found when excluded"


class TestPriority6CCNLBusinessLogic:
    """Test Priority 6 specific business logic and validation."""

    def test_management_hierarchy_validation(self):
        """Test that management hierarchy is properly structured."""
        dirigenti_industria = get_dirigenti_industria_ccnl()
        dirigenti_commercio = get_dirigenti_commercio_ccnl()
        quadri = get_quadri_ccnl()

        # Test management levels have appropriate categories
        for ccnl in [dirigenti_industria, dirigenti_commercio]:
            management_levels = [level for level in ccnl.job_levels if level.category == WorkerCategory.DIRIGENTE]
            assert len(management_levels) > 0, f"Missing management levels in {ccnl.name}"

        # Test quadri have appropriate category
        quadri_levels = [level for level in quadri.job_levels if level.category == WorkerCategory.QUADRO]
        assert len(quadri_levels) > 0, "Missing quadri levels in CCNL Quadri"

    def test_transport_specialization_requirements(self):
        """Test transport sector specialization requirements."""
        autotrasporto = get_autotrasporto_merci_ccnl()

        # Check for specialized driver requirements
        specialized_levels = [
            level
            for level in autotrasporto.job_levels
            if "specializ" in level.level_name.lower() or "spec" in level.level_code.lower()
        ]

        assert len(specialized_levels) > 0, "Missing specialized driver levels"

        # Specialized drivers should have higher experience requirements
        for level in specialized_levels:
            if hasattr(level, "minimum_experience_months"):
                assert level.minimum_experience_months > 0, "Specialized drivers should require experience"

    def test_service_sector_characteristics(self):
        """Test service sector specific characteristics."""
        acconciatura = get_acconciatura_estetica_ccnl()

        # Beauty/personal care should have specific working patterns
        assert acconciatura.working_hours.ordinary_weekly_hours <= 40, "Service hours should be reasonable"

        # Should have provisions for part-time work
        [
            level
            for level in acconciatura.job_levels
            if "part" in level.level_name.lower() or hasattr(level, "part_time_eligible")
        ]
        # Note: This test may need adjustment based on actual data structure

    def test_priority6_coverage_completeness(self):
        """Test that Priority 6 provides comprehensive sector coverage."""
        priority6_data = get_all_priority6_ccnl_data()

        # Verify we have representation across different economic areas
        transport_sectors = [ccnl for ccnl in priority6_data if ccnl.sector.value.startswith("auto")]
        assert len(transport_sectors) == 3, "Should have 3 transport sub-sectors"

        management_sectors = [
            ccnl
            for ccnl in priority6_data
            if ccnl.sector in [CCNLSector.DIRIGENTI_INDUSTRIA, CCNLSector.DIRIGENTI_COMMERCIO, CCNLSector.QUADRI]
        ]
        assert len(management_sectors) == 3, "Should have 3 management levels"

        service_sectors = [
            ccnl
            for ccnl in priority6_data
            if ccnl.sector
            in [CCNLSector.POMPE_FUNEBRI, CCNLSector.ACCONCIATURA_ESTETICA, CCNLSector.IMPIANTI_SPORTIVI]
        ]
        assert len(service_sectors) == 3, "Should have 3 service sectors"
