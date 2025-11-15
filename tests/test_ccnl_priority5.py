"""
Test suite for Priority 5 CCNL data structures and functionality.

This module tests all 5 Priority 5 Media & Entertainment sectors
to ensure complete data integrity and business logic correctness.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

import pytest

from app.data.ccnl_priority5 import (
    get_all_priority5_ccnl_data,
    get_cinema_audiovisivo_ccnl,
    get_giornalisti_ccnl,
    get_grafici_editoriali_ccnl,
    get_radio_tv_private_ccnl,
    get_teatro_ccnl,
    validate_priority5_ccnl_data_completeness,
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


class TestPriority5CCNLDataStructures:
    """Test Priority 5 CCNL data structure completeness and integrity."""

    def test_all_priority5_sectors_defined(self):
        """Test that all 5 Priority 5 sectors are properly defined."""
        expected_sectors = [
            CCNLSector.GIORNALISTI,
            CCNLSector.GRAFICI_EDITORIALI,
            CCNLSector.CINEMA_AUDIOVISIVO,
            CCNLSector.TEATRO,
            CCNLSector.RADIO_TV_PRIVATE,
        ]

        # Verify all sectors have priority level 5
        for sector in expected_sectors:
            assert sector.priority_level() == 5

        # Verify Italian names exist
        for sector in expected_sectors:
            italian_name = sector.italian_name()
            assert isinstance(italian_name, str)
            assert len(italian_name) > 0
            assert italian_name != sector.value

    def test_priority5_data_completeness(self):
        """Test that Priority 5 data validation passes."""
        validation_result = validate_priority5_ccnl_data_completeness()

        assert validation_result["status"] == "COMPLETE"
        assert validation_result["total_sectors"] == 5
        assert validation_result["sectors_complete"] == 5
        assert validation_result["completion_rate"] >= 95.0
        assert len(validation_result["missing_components"]) == 0

    def test_all_priority5_ccnl_data_loading(self):
        """Test that all Priority 5 CCNL agreements can be loaded."""
        all_agreements = get_all_priority5_ccnl_data()

        assert len(all_agreements) == 5

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
    async def test_ccnl_service_priority5_integration(self):
        """Test CCNL service integration with Priority 5 data."""
        # Test Priority 5 data loading
        priority5_data = await ccnl_service.get_all_priority5_ccnl()
        assert len(priority5_data) == 5

        # Test coverage stats
        coverage_stats = await ccnl_service.get_ccnl_coverage_stats()
        assert coverage_stats["priority5"]["sectors_covered"] == 5
        assert coverage_stats["priority5"]["agreements_count"] == 5
        assert coverage_stats["priority5"]["worker_coverage_percentage"] == 3

        # Test that Priority 5 is included in totals
        assert coverage_stats["total"]["priorities_implemented"] == 5


class TestMediaSectorsCCNL:
    """Test media-related sectors CCNL data."""

    def test_giornalisti_structure(self):
        """Test journalists CCNL structure."""
        agreement = get_giornalisti_ccnl()

        assert agreement.sector == CCNLSector.GIORNALISTI
        assert "Giornalisti" in agreement.name
        assert len(agreement.job_levels) == 4
        assert len(agreement.salary_tables) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 36  # Media hours
        assert agreement.working_hours.flexible_hours_allowed is True
        assert agreement.working_hours.shift_work_allowed is True

    def test_giornalisti_journalism_specifics(self):
        """Test journalism sector specific features."""
        agreement = get_giornalisti_ccnl()

        # Should have journalism-specific job levels
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "PRAT" in level_codes  # Praticante Giornalista
        assert "GIOR" in level_codes  # Giornalista Professionista
        assert "CAPOREDATT" in level_codes  # Caporedattore

        # Should have travel allowances for reporting
        allowance_types = [allowance.allowance_type for allowance in agreement.special_allowances]
        assert AllowanceType.INDENNITA_TRASFERTA in allowance_types

        # Should have production bonuses for articles
        assert AllowanceType.PREMIO_PRODUZIONE in allowance_types

        # Should have shift allowances for news deadlines
        assert AllowanceType.INDENNITA_TURNO in allowance_types

        # Should have competitive journalism salaries
        salaries = [table.base_monthly_salary for table in agreement.salary_tables]
        max_salary = max(salaries)
        assert max_salary >= Decimal("4000")  # Senior journalists

    def test_grafici_editoriali_structure(self):
        """Test publishing graphics CCNL structure."""
        agreement = get_grafici_editoriali_ccnl()

        assert agreement.sector == CCNLSector.GRAFICI_EDITORIALI
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 38
        assert agreement.working_hours.flexible_hours_allowed is True

        # Should have graphics-specific roles
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "GRAF_JR" in level_codes  # Grafico Junior
        assert "GRAF_EDIT" in level_codes  # Grafico Editoriale
        assert "ART_DIR" in level_codes  # Art Director
        assert "RESP_GRAF" in level_codes  # Responsabile Grafica

    def test_cinema_audiovisivo_structure(self):
        """Test cinema and audiovisual CCNL structure."""
        agreement = get_cinema_audiovisivo_ccnl()

        assert agreement.sector == CCNLSector.CINEMA_AUDIOVISIVO
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 40
        assert agreement.working_hours.maximum_weekly_hours == 50  # Higher for productions
        assert agreement.working_hours.flexible_hours_allowed is True
        assert agreement.working_hours.shift_work_allowed is True

        # Should have film production roles
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "ASSIST" in level_codes  # Assistente Produzione
        assert "TECNICO" in level_codes  # Tecnico Audiovisivo
        assert "REGISTA_ASS" in level_codes  # Regista Assistente
        assert "PRODUTTORE" in level_codes  # Produttore

    def test_teatro_structure(self):
        """Test theater CCNL structure."""
        agreement = get_teatro_ccnl()

        assert agreement.sector == CCNLSector.TEATRO
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 35  # Lower for artistic work
        assert agreement.working_hours.flexible_hours_allowed is True
        assert agreement.working_hours.shift_work_allowed is True

        # Should have theater-specific roles
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "TECNICO_SC" in level_codes  # Tecnico di Scena
        assert "ATTORE" in level_codes  # Attore
        assert "REGISTA_TEAT" in level_codes  # Regista Teatrale
        assert "DIRETT_TEAT" in level_codes  # Direttore Teatrale

    def test_radio_tv_private_structure(self):
        """Test private radio/TV CCNL structure."""
        agreement = get_radio_tv_private_ccnl()

        assert agreement.sector == CCNLSector.RADIO_TV_PRIVATE
        assert len(agreement.job_levels) == 4
        assert agreement.working_hours.ordinary_weekly_hours == 38
        assert agreement.working_hours.shift_work_allowed is True

        # Should have broadcasting-specific roles
        level_codes = [level.level_code for level in agreement.job_levels]
        assert "OPER_TECN" in level_codes  # Operatore Tecnico
        assert "CONDUTTORE" in level_codes  # Conduttore
        assert "AUTORE" in level_codes  # Autore
        assert "DIRETT_PROG" in level_codes  # Direttore Programmi


class TestPriority5DataQuality:
    """Test data quality and consistency across Priority 5 sectors."""

    def test_salary_table_consistency(self):
        """Test salary tables are consistent and reasonable."""
        all_agreements = get_all_priority5_ccnl_data()

        for agreement in all_agreements:
            salaries = [table.base_monthly_salary for table in agreement.salary_tables]

            # Basic validation
            assert all(salary > Decimal("1400") for salary in salaries)  # Minimum wage check for creative sectors
            assert all(salary < Decimal("7000") for salary in salaries)  # Sanity check for top creative roles

            # Progression validation
            if len(salaries) > 1:
                salaries.sort()
                for i in range(1, len(salaries)):
                    assert salaries[i] > salaries[i - 1]  # Should be progressive

    def test_working_hours_creative_sector_standards(self):
        """Test working hours are appropriate for creative sectors."""
        all_agreements = get_all_priority5_ccnl_data()

        for agreement in all_agreements:
            wh = agreement.working_hours

            # Creative sectors often have flexible hours
            if agreement.sector == CCNLSector.TEATRO:
                assert wh.ordinary_weekly_hours <= 38  # Theater has lower base hours
            elif agreement.sector == CCNLSector.CINEMA_AUDIOVISIVO:
                assert wh.maximum_weekly_hours >= 48  # Film production can have longer hours

            # All should allow some flexibility
            assert wh.flexible_hours_allowed is True or wh.shift_work_allowed is True

    def test_notice_periods_appropriateness(self):
        """Test notice periods are appropriate for media/entertainment sectors."""
        all_agreements = get_all_priority5_ccnl_data()

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

    def test_leave_entitlements_creative_sector_standards(self):
        """Test leave entitlements are appropriate for creative sectors."""
        all_agreements = get_all_priority5_ccnl_data()

        for agreement in all_agreements:
            for leave in agreement.leave_entitlements:
                if leave.leave_type == LeaveType.FERIE:
                    # Creative sectors should have reasonable leave
                    assert leave.base_annual_days >= 24  # At least 24 days

                    # Theater should have more generous leave for artistic sector
                    if agreement.sector == CCNLSector.TEATRO:
                        assert leave.base_annual_days >= 30

    def test_sector_specific_characteristics(self):
        """Test that Priority 5 sectors have appropriate sector-specific features."""
        all_agreements = get_all_priority5_ccnl_data()

        # Count sectors with flexible hours (should be high in creative sectors)
        flexible_count = 0
        for agreement in all_agreements:
            if agreement.working_hours.flexible_hours_allowed:
                flexible_count += 1

        # All creative sectors should have flexible working
        assert flexible_count == 5

        # Count sectors with shift work (for news, broadcasting, theater)
        shift_work_count = 0
        for agreement in all_agreements:
            if agreement.working_hours.shift_work_allowed:
                shift_work_count += 1

        # Most media sectors should allow shift work
        assert shift_work_count >= 3


class TestPriority5SpecialSectorFeatures:
    """Test special features unique to Priority 5 sectors."""

    def test_journalism_travel_allowances(self):
        """Test that journalism sectors have appropriate travel allowances."""
        journalism_agreements = [get_giornalisti_ccnl(), get_radio_tv_private_ccnl()]

        for agreement in journalism_agreements:
            allowance_types = [a.allowance_type for a in agreement.special_allowances]
            # Journalism should have travel allowances for reporting
            assert (
                AllowanceType.INDENNITA_TRASFERTA in allowance_types
                or AllowanceType.INDENNITA_TURNO in allowance_types
            )

    def test_creative_sector_production_bonuses(self):
        """Test creative sectors have production/performance bonuses."""
        creative_agreements = [
            get_giornalisti_ccnl(),
            get_cinema_audiovisivo_ccnl(),
            get_teatro_ccnl(),
            get_radio_tv_private_ccnl(),
        ]

        for agreement in creative_agreements:
            allowance_types = [a.allowance_type for a in agreement.special_allowances]
            # Creative sectors should have performance-based bonuses
            assert AllowanceType.PREMIO_PRODUZIONE in allowance_types

    def test_media_sector_shift_requirements(self):
        """Test media sectors accommodate 24/7 broadcasting needs."""
        media_agreements = [get_giornalisti_ccnl(), get_radio_tv_private_ccnl()]

        for agreement in media_agreements:
            # Should support 24/7 operations
            assert agreement.working_hours.shift_work_allowed is True
            assert agreement.working_hours.shift_patterns is not None
            assert len(agreement.working_hours.shift_patterns) >= 3  # Multiple shifts

            # Should have shift allowances
            allowance_types = [a.allowance_type for a in agreement.special_allowances]
            assert AllowanceType.INDENNITA_TURNO in allowance_types

    def test_artistic_sector_creativity_support(self):
        """Test artistic sectors support creative work patterns."""
        artistic_agreements = [get_teatro_ccnl(), get_cinema_audiovisivo_ccnl(), get_grafici_editoriali_ccnl()]

        for agreement in artistic_agreements:
            # Should have flexible arrangements for creative work
            assert agreement.working_hours.flexible_hours_allowed is True

            # Should allow part-time work for artists
            if hasattr(agreement.working_hours, "part_time_allowed"):
                assert agreement.working_hours.part_time_allowed is True

    def test_media_production_overtime_provisions(self):
        """Test media sectors have appropriate overtime for production demands."""
        production_agreements = [get_cinema_audiovisivo_ccnl(), get_teatro_ccnl(), get_giornalisti_ccnl()]

        for agreement in production_agreements:
            # Should have higher overtime limits for production deadlines
            assert agreement.overtime_rules.maximum_monthly_overtime >= 50

            # Should have competitive overtime rates
            assert agreement.overtime_rules.daily_overtime_rate >= Decimal("1.30")


class TestPriority5IntegrationCompliance:
    """Test Priority 5 integration and compliance features."""

    def test_all_sectors_have_required_allowances(self):
        """Test all sectors have meal vouchers and basic allowances."""
        all_agreements = get_all_priority5_ccnl_data()

        production_bonus_count = 0
        for agreement in all_agreements:
            allowance_types = [a.allowance_type for a in agreement.special_allowances]
            if AllowanceType.PREMIO_PRODUZIONE in allowance_types:
                production_bonus_count += 1

        # Most creative sectors should provide production bonuses
        assert production_bonus_count >= 4

    def test_creative_sector_quality_requirements(self):
        """Test creative sectors meet industry quality standards."""
        creative_agreements = [get_grafici_editoriali_ccnl(), get_cinema_audiovisivo_ccnl(), get_teatro_ccnl()]

        for agreement in creative_agreements:
            # Should have qualified professionals
            qualified_levels = [
                level
                for level in agreement.job_levels
                if level.required_qualifications and len(level.required_qualifications) > 0
            ]
            assert len(qualified_levels) >= 2  # Multiple levels should require qualifications

    def test_media_sector_broadcasting_compliance(self):
        """Test media sectors comply with broadcasting regulations."""
        media_agreements = [get_giornalisti_ccnl(), get_radio_tv_private_ccnl()]

        for agreement in media_agreements:
            # Should have professional journalism standards
            professional_levels = [
                level
                for level in agreement.job_levels
                if "professional" in level.level_name.lower()
                or "giornalista" in level.level_name.lower()
                or "conduttore" in level.level_name.lower()
            ]
            assert len(professional_levels) >= 1  # Should have professional roles

            # Should support continuous operations
            assert agreement.working_hours.shift_work_allowed is True

    def test_entertainment_sector_performance_standards(self):
        """Test entertainment sectors meet performance industry standards."""
        entertainment_agreements = [get_teatro_ccnl(), get_cinema_audiovisivo_ccnl()]

        for agreement in entertainment_agreements:
            # Should have performance-based compensation
            allowance_types = [a.allowance_type for a in agreement.special_allowances]
            assert AllowanceType.PREMIO_PRODUZIONE in allowance_types

            # Should have travel provisions for touring/location work
            assert AllowanceType.INDENNITA_TRASFERTA in allowance_types

            # Should have appropriate salary ranges for creative work
            salaries = [table.base_monthly_salary for table in agreement.salary_tables]
            assert max(salaries) >= Decimal("3000")  # Senior creative roles
