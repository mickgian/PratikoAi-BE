"""
Test suite for Priority 4 CCNL data structures and functionality.

This module tests all 8 Priority 4 Public & Healthcare sectors
to ensure complete data integrity and business logic correctness.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

import pytest

from app.data.ccnl_priority4 import (
    get_all_priority4_ccnl_data,
    get_case_di_cura_ccnl,
    get_enti_di_ricerca_ccnl,
    get_enti_locali_ccnl,
    get_farmacie_private_ccnl,
    get_ministeri_ccnl,
    get_sanita_privata_ccnl,
    get_scuola_privata_ccnl,
    get_universita_private_ccnl,
    validate_priority4_ccnl_data_completeness,
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


class TestPriority4CCNLDataStructures:
    """Test Priority 4 CCNL data structure completeness and integrity."""

    def test_all_priority4_sectors_defined(self):
        """Test that all 8 Priority 4 sectors are properly defined."""
        expected_sectors = [
            CCNLSector.SANITA_PRIVATA,
            CCNLSector.CASE_DI_CURA,
            CCNLSector.FARMACIE_PRIVATE,
            CCNLSector.ENTI_LOCALI,
            CCNLSector.MINISTERI,
            CCNLSector.SCUOLA_PRIVATA,
            CCNLSector.UNIVERSITA_PRIVATE,
            CCNLSector.ENTI_DI_RICERCA,
        ]

        # Verify all sectors have priority level 4
        for sector in expected_sectors:
            assert sector.priority_level() == 4

        # Verify Italian names exist
        for sector in expected_sectors:
            italian_name = sector.italian_name()
            assert isinstance(italian_name, str)
            assert len(italian_name) > 0
            assert italian_name != sector.value

    def test_priority4_data_completeness(self):
        """Test that Priority 4 data validation passes."""
        validation_result = validate_priority4_ccnl_data_completeness()

        assert validation_result["status"] == "COMPLETE"
        assert validation_result["total_sectors"] == 8
        assert validation_result["sectors_complete"] == 8
        assert validation_result["completion_rate"] >= 95.0
        assert len(validation_result["missing_components"]) == 0

    def test_all_priority4_ccnl_data_loading(self):
        """Test that all Priority 4 CCNL agreements can be loaded."""
        all_agreements = get_all_priority4_ccnl_data()

        assert len(all_agreements) == 8

        # Verify each agreement is complete
        for agreement in all_agreements:
            assert isinstance(agreement, CCNLAgreement)
            assert agreement.sector is not None
            assert len(agreement.job_levels) > 0
            assert len(agreement.salary_tables) > 0
            assert agreement.working_hours is not None
            assert agreement.overtime_rules is not None
            assert len(agreement.leave_entitlements) > 0
            assert len(agreement.notice_periods) > 0

    @pytest.mark.asyncio
    async def test_ccnl_service_priority4_integration(self):
        """Test CCNL service integration with Priority 4 data."""
        # Test Priority 4 data loading
        priority4_data = await ccnl_service.get_all_priority4_ccnl()
        assert len(priority4_data) == 8

        # Test coverage stats
        coverage_stats = await ccnl_service.get_ccnl_coverage_stats()
        assert coverage_stats["priority4"]["sectors_covered"] == 8
        assert coverage_stats["priority4"]["agreements_count"] == 8
        assert coverage_stats["priority4"]["worker_coverage_percentage"] == 5

        # Test that Priority 4 is included in totals
        assert coverage_stats["total"]["priorities_implemented"] == 4


class TestHealthcareSectorsCCNL:
    """Test healthcare-related sectors CCNL data."""

    def test_sanita_privata_structure(self):
        """Test private healthcare CCNL structure."""
        agreement = get_sanita_privata_ccnl()

        assert agreement.sector == CCNLSector.SANITA_PRIVATA
        assert "Sanità Privata" in agreement.name
        assert len(agreement.job_levels) == 4
        assert len(agreement.salary_tables) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 38
        assert agreement.working_hours.shift_work_allowed is True

    def test_sanita_privata_healthcare_specifics(self):
        """Test healthcare sector specific features."""
        agreement = get_sanita_privata_ccnl()

        # Should have healthcare-specific job levels
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "OSS" in level_codes  # Operatore Socio Sanitario
        assert "INF" in level_codes  # Infermiere

        # Should have risk allowances for biological hazards
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.INDENNITA_RISCHIO in allowance_types

        # Should have shift allowances for 24/7 operation
        assert AllowanceType.INDENNITA_TURNO in allowance_types

        # Should have competitive healthcare salaries
        salaries = [table.base_monthly_salary for table in agreement.salary_tables]
        max_salary = max(salaries)
        assert max_salary >= Decimal("2400")  # Healthcare professionals

    def test_case_di_cura_structure(self):
        """Test nursing homes CCNL structure."""
        agreement = get_case_di_cura_ccnl()

        assert agreement.sector == CCNLSector.CASE_DI_CURA
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.shift_work_allowed is True

        # Should have elderly care specific roles
        level_names = [level.level_name for level in agreement.job_levels]
        assert any("Socio" in name for name in level_names)

    def test_farmacie_private_structure(self):
        """Test private pharmacies CCNL structure."""
        agreement = get_farmacie_private_ccnl()

        assert agreement.sector == CCNLSector.FARMACIE_PRIVATE
        assert len(agreement.job_levels) == 4

        # Should have pharmacy-specific roles
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "FARM_ASS" in level_codes  # Farmacista Assistente
        assert "COMM" in level_codes  # Commesso

        # Should have professional salaries for pharmacists
        [table.base_monthly_salary for table in agreement.salary_tables]
        pharmacist_salaries = [
            table.base_monthly_salary for table in agreement.salary_tables if "FARM" in table.level_code
        ]
        assert all(salary >= Decimal("1700") for salary in pharmacist_salaries)


class TestPublicSectorsCCNL:
    """Test public sector CCNL data."""

    def test_enti_locali_structure(self):
        """Test local government CCNL structure."""
        agreement = get_enti_locali_ccnl()

        assert agreement.sector == CCNLSector.ENTI_LOCALI
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 36  # Public sector hours
        assert agreement.working_hours.flexible_hours_allowed is True

        # Should have public administration job levels
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "B1" in level_codes  # Base level
        assert "C1" in level_codes  # Administrative
        assert "D1" in level_codes  # Directive
        assert "DIR" in level_codes  # Management

    def test_ministeri_structure(self):
        """Test national ministries CCNL structure."""
        agreement = get_ministeri_ccnl()

        assert agreement.sector == CCNLSector.MINISTERI
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 36

        # Should have higher salaries than local government
        ministeri_salaries = [table.base_monthly_salary for table in agreement.salary_tables]
        enti_locali_salaries = [table.base_monthly_salary for table in get_enti_locali_ccnl().salary_tables]

        # Compare highest levels
        assert max(ministeri_salaries) > max(enti_locali_salaries)

    def test_public_sector_leave_entitlements(self):
        """Test that public sector has generous leave entitlements."""
        public_agreements = [get_enti_locali_ccnl(), get_ministeri_ccnl()]

        for agreement in public_agreements:
            leave_days = [leave.base_annual_days for leave in agreement.leave_entitlements]
            # Public sector should have at least 30 days annual leave
            assert max(leave_days) >= 30


class TestEducationSectorsCCNL:
    """Test education sector CCNL data."""

    def test_scuola_privata_structure(self):
        """Test private schools CCNL structure."""
        agreement = get_scuola_privata_ccnl()

        assert agreement.sector == CCNLSector.SCUOLA_PRIVATA
        assert len(agreement.job_levels) == 4

        # Should have education-specific roles
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "DOC_PRIM" in level_codes  # Primary teacher
        assert "DOC_SEC" in level_codes  # Secondary teacher
        assert "ATA" in level_codes  # Administrative staff

        # Should have teaching-specific working hours
        assert agreement.working_hours.ordinary_weekly_hours == 25  # Teaching hours
        assert agreement.working_hours.maximum_weekly_hours == 40  # Including preparation

    def test_universita_private_structure(self):
        """Test private universities CCNL structure."""
        agreement = get_universita_private_ccnl()

        assert agreement.sector == CCNLSector.UNIVERSITA_PRIVATE
        assert len(agreement.job_levels) == 4

        # Should have academic hierarchy
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "RIC_TD" in level_codes  # Researcher
        assert "PROF_ASS" in level_codes  # Associate Professor
        assert "PROF_ORD" in level_codes  # Full Professor

        # Should have higher salaries than schools
        university_salaries = [table.base_monthly_salary for table in agreement.salary_tables]
        school_salaries = [table.base_monthly_salary for table in get_scuola_privata_ccnl().salary_tables]

        assert max(university_salaries) > max(school_salaries)

    def test_enti_di_ricerca_structure(self):
        """Test research institutions CCNL structure."""
        agreement = get_enti_di_ricerca_ccnl()

        assert agreement.sector == CCNLSector.ENTI_DI_RICERCA
        assert len(agreement.job_levels) == 4

        # Should have research-specific roles
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "TAR" in level_codes  # Technical Research
        assert "RICJR" in level_codes  # Junior Researcher
        assert "RICSR" in level_codes  # Senior Researcher
        assert "DIRETT" in level_codes  # Research Director

        # Should have flexible research hours
        assert agreement.working_hours.flexible_hours_allowed is True
        assert agreement.working_hours.flexible_hours_range is not None


class TestPriority4DataQuality:
    """Test data quality and consistency across Priority 4 sectors."""

    def test_salary_table_consistency(self):
        """Test salary tables are consistent and reasonable."""
        all_agreements = get_all_priority4_ccnl_data()

        for agreement in all_agreements:
            salaries = [table.base_monthly_salary for table in agreement.salary_tables]

            # Basic validation
            assert all(salary > Decimal("1200") for salary in salaries)  # Minimum wage check
            assert all(salary < Decimal("6000") for salary in salaries)  # Sanity check for non-executives

            # Progression validation
            if len(salaries) > 1:
                salaries.sort()
                for i in range(1, len(salaries)):
                    assert salaries[i] > salaries[i - 1]  # Should be progressive

    def test_working_hours_reasonableness(self):
        """Test working hours are within reasonable bounds."""
        all_agreements = get_all_priority4_ccnl_data()

        for agreement in all_agreements:
            wh = agreement.working_hours

            # Most public/healthcare sectors have reduced hours
            assert 25 <= wh.ordinary_weekly_hours <= 40
            assert wh.maximum_weekly_hours <= 48  # EU working time directive

    def test_notice_periods_appropriateness(self):
        """Test notice periods are appropriate for public/healthcare sectors."""
        all_agreements = get_all_priority4_ccnl_data()

        for agreement in all_agreements:
            # Group by worker category
            categories = {}
            for notice in agreement.notice_periods:
                if notice.worker_category not in categories:
                    categories[notice.worker_category] = []
                categories[notice.worker_category].append(notice)

            # Check that higher categories have longer notice periods
            if WorkerCategory.DIRIGENTE in categories and WorkerCategory.OPERAIO in categories:
                dirigente_max = max(n.notice_days for n in categories[WorkerCategory.DIRIGENTE])
                operaio_max = max(n.notice_days for n in categories[WorkerCategory.OPERAIO])
                assert dirigente_max > operaio_max

    def test_leave_entitlements_public_sector_standards(self):
        """Test leave entitlements meet public sector standards."""
        all_agreements = get_all_priority4_ccnl_data()

        for agreement in all_agreements:
            for leave in agreement.leave_entitlements:
                if leave.leave_type == LeaveType.FERIE:
                    # Public sector should have generous leave
                    assert leave.base_annual_days >= 25

    def test_sector_specific_characteristics(self):
        """Test that Priority 4 sectors have appropriate sector-specific features."""
        all_agreements = get_all_priority4_ccnl_data()

        # Count sectors with flexible hours (should be high in public sector)
        flexible_count = 0
        for agreement in all_agreements:
            if agreement.working_hours.flexible_hours_allowed:
                flexible_count += 1

        # At least 5 out of 8 should have flexible working
        assert flexible_count >= 5

        # Count sectors with part-time allowed (should be high in public sector)
        part_time_count = 0
        for agreement in all_agreements:
            if agreement.working_hours.part_time_allowed:
                part_time_count += 1

        # Most public sector should allow part-time
        assert part_time_count >= 6


class TestPriority4SpecialSectorFeatures:
    """Test special features unique to Priority 4 sectors."""

    def test_healthcare_risk_allowances(self):
        """Test that healthcare sectors have appropriate risk allowances."""
        healthcare_agreements = [get_sanita_privata_ccnl(), get_case_di_cura_ccnl(), get_farmacie_private_ccnl()]

        for agreement in healthcare_agreements:
            allowance_types = [a.allowance_type for a in agreement.special_allowances]
            # Healthcare should have risk allowances
            assert (
                AllowanceType.INDENNITA_RISCHIO in allowance_types or AllowanceType.INDENNITA_TURNO in allowance_types
            )

    def test_education_sector_working_patterns(self):
        """Test education sector working patterns."""
        education_agreements = [get_scuola_privata_ccnl(), get_universita_private_ccnl(), get_enti_di_ricerca_ccnl()]

        for agreement in education_agreements:
            # Education should have flexible arrangements
            assert agreement.working_hours.flexible_hours_allowed is True

            # Should allow part-time work
            assert agreement.working_hours.part_time_allowed is True

    def test_public_administration_hierarchy(self):
        """Test public administration proper hierarchy."""
        public_agreements = [get_enti_locali_ccnl(), get_ministeri_ccnl()]

        for agreement in public_agreements:
            # Should have clear hierarchy in job levels
            categories = [level.category for level in agreement.job_levels]

            # Should have multiple categories
            unique_categories = set(categories)
            assert len(unique_categories) >= 3

            # Should include dirigente level
            assert WorkerCategory.DIRIGENTE in unique_categories

    def test_research_sector_innovation_focus(self):
        """Test research sector innovation and publication focus."""
        research_agreements = [get_universita_private_ccnl(), get_enti_di_ricerca_ccnl()]

        for agreement in research_agreements:
            # Should have production bonuses for research output
            allowance_types = [a.allowance_type for a in agreement.special_allowances]
            assert AllowanceType.PREMIO_PRODUZIONE in allowance_types

            # Should have higher maximum salaries for senior researchers
            salaries = [table.base_monthly_salary for table in agreement.salary_tables]
            assert max(salaries) >= Decimal("3000")


class TestPriority4IntegrationCompliance:
    """Test Priority 4 integration and compliance features."""

    def test_all_sectors_have_required_allowances(self):
        """Test all sectors have meal vouchers and basic allowances."""
        all_agreements = get_all_priority4_ccnl_data()

        buoni_pasto_count = 0
        for agreement in all_agreements:
            allowance_types = [a.allowance_type for a in agreement.special_allowances]
            if AllowanceType.BUONI_PASTO in allowance_types:
                buoni_pasto_count += 1

        # Most sectors should provide meal vouchers
        assert buoni_pasto_count >= 6

    def test_public_sector_transparency_requirements(self):
        """Test public sector meets transparency and governance requirements."""
        public_agreements = [get_enti_locali_ccnl(), get_ministeri_ccnl()]

        for agreement in public_agreements:
            # Should have longer notice periods for transparency
            max_notice = max(n.notice_days for n in agreement.notice_periods)
            assert max_notice >= 60  # Public sector requires longer notice

            # Should have structured job levels
            assert len(agreement.job_levels) >= 4

    def test_healthcare_compliance_standards(self):
        """Test healthcare sector compliance with health regulations."""
        healthcare_agreements = [get_sanita_privata_ccnl(), get_case_di_cura_ccnl(), get_farmacie_private_ccnl()]

        for agreement in healthcare_agreements:
            # Should have shift work capabilities for 24/7 coverage
            if agreement.sector in [CCNLSector.SANITA_PRIVATA, CCNLSector.CASE_DI_CURA]:
                assert agreement.working_hours.shift_work_allowed is True

        # Pharmacy specifically should have professional qualification requirements
        farmacie_agreement = get_farmacie_private_ccnl()
        qualified_levels = [
            level
            for level in farmacie_agreement.job_levels
            if level.required_qualifications and len(level.required_qualifications) > 0
        ]
        assert len(qualified_levels) >= 2  # Pharmacists need qualifications
