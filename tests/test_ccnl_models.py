"""
Test suite for CCNL (Collective Labor Agreements) data models.

This module tests the data structures used to represent Italian
collective labor agreements with comprehensive coverage of all
worker categories, salary scales, and employment conditions.
"""

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pytest

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
    ProbationPeriod,
    SalaryTable,
    SpecialAllowance,
    WorkerCategory,
    WorkingHours,
)


class TestCCNLSectorEnum:
    """Test CCNL sector enumeration."""

    def test_priority1_sectors_exist(self):
        """Test that all Priority 1 sectors are defined."""
        assert CCNLSector.METALMECCANICI_INDUSTRIA.value == "metalmeccanici_industria"
        assert CCNLSector.METALMECCANICI_ARTIGIANI.value == "metalmeccanici_artigiani"
        assert CCNLSector.COMMERCIO_TERZIARIO.value == "commercio_terziario"
        assert CCNLSector.EDILIZIA_INDUSTRIA.value == "edilizia_industria"
        assert CCNLSector.EDILIZIA_ARTIGIANATO.value == "edilizia_artigianato"
        assert CCNLSector.PUBBLICI_ESERCIZI.value == "pubblici_esercizi"
        assert CCNLSector.TURISMO.value == "turismo"
        assert CCNLSector.TRASPORTI_LOGISTICA.value == "trasporti_logistica"
        assert CCNLSector.CHIMICI_FARMACEUTICI.value == "chimici_farmaceutici"
        assert CCNLSector.TESSILI.value == "tessili"

    def test_sector_display_names(self):
        """Test Italian display names for sectors."""
        assert CCNLSector.METALMECCANICI_INDUSTRIA.italian_name() == "Metalmeccanici Industria"
        assert CCNLSector.COMMERCIO_TERZIARIO.italian_name() == "Commercio e Terziario"
        assert CCNLSector.PUBBLICI_ESERCIZI.italian_name() == "Pubblici Esercizi"

    def test_sector_from_string(self):
        """Test creating sector from description."""
        assert CCNLSector.from_description("metalmeccanici") == CCNLSector.METALMECCANICI_INDUSTRIA
        assert CCNLSector.from_description("commercio") == CCNLSector.COMMERCIO_TERZIARIO
        assert CCNLSector.from_description("edilizia") == CCNLSector.EDILIZIA_INDUSTRIA


class TestWorkerCategoryEnum:
    """Test worker category enumeration."""

    def test_worker_categories_exist(self):
        """Test that all worker categories are defined."""
        assert WorkerCategory.OPERAIO.value == "operaio"
        assert WorkerCategory.IMPIEGATO.value == "impiegato"
        assert WorkerCategory.QUADRO.value == "quadro"
        assert WorkerCategory.DIRIGENTE.value == "dirigente"
        assert WorkerCategory.APPRENDISTA.value == "apprendista"

    def test_category_hierarchy(self):
        """Test worker category hierarchy levels."""
        assert WorkerCategory.OPERAIO.hierarchy_level() == 1
        assert WorkerCategory.APPRENDISTA.hierarchy_level() == 1
        assert WorkerCategory.IMPIEGATO.hierarchy_level() == 2
        assert WorkerCategory.QUADRO.hierarchy_level() == 3
        assert WorkerCategory.DIRIGENTE.hierarchy_level() == 4

    def test_category_italian_names(self):
        """Test Italian display names."""
        assert WorkerCategory.OPERAIO.italian_name() == "Operaio"
        assert WorkerCategory.IMPIEGATO.italian_name() == "Impiegato"
        assert WorkerCategory.QUADRO.italian_name() == "Quadro"
        assert WorkerCategory.DIRIGENTE.italian_name() == "Dirigente"


class TestJobLevelModel:
    """Test job level data model."""

    def test_create_basic_job_level(self):
        """Test creating a basic job level."""
        level = JobLevel(
            level_code="C1",
            level_name="Operaio Comune",
            category=WorkerCategory.OPERAIO,
            description="Operaio addetto a mansioni generiche",
            minimum_experience_months=0,
        )

        assert level.level_code == "C1"
        assert level.category == WorkerCategory.OPERAIO
        assert level.minimum_experience_months == 0

    def test_create_detailed_job_level(self):
        """Test creating job level with detailed specifications."""
        level = JobLevel(
            level_code="D2",
            level_name="Impiegato di 2° Livello",
            category=WorkerCategory.IMPIEGATO,
            description="Impiegato con funzioni di coordinamento",
            minimum_experience_months=24,
            required_qualifications=["Diploma", "Esperienza settoriale"],
            typical_tasks=["Coordinamento attività", "Rapporti con clienti", "Controllo qualità"],
            decision_making_level="Medio",
            supervision_responsibilities=True,
        )

        assert level.level_code == "D2"
        assert len(level.required_qualifications) == 2
        assert len(level.typical_tasks) == 3
        assert level.supervision_responsibilities is True

    def test_level_comparison(self):
        """Test comparing job levels."""
        level1 = JobLevel("C1", "Operaio Base", WorkerCategory.OPERAIO)
        level2 = JobLevel("C3", "Operaio Specializzato", WorkerCategory.OPERAIO)
        level3 = JobLevel("D1", "Impiegato", WorkerCategory.IMPIEGATO)

        assert level1.is_lower_than(level2)
        assert level2.is_higher_than(level1)
        assert level3.is_higher_category_than(level1)


class TestSalaryTableModel:
    """Test salary table data model."""

    def test_create_basic_salary_table(self):
        """Test creating basic salary table."""
        salary_table = SalaryTable(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            level_code="C1",
            base_monthly_salary=Decimal("1450.00"),
            geographic_area=GeographicArea.NAZIONALE,
            valid_from=date(2024, 1, 1),
            valid_to=date(2026, 12, 31),
        )

        assert salary_table.base_monthly_salary == Decimal("1450.00")
        assert salary_table.geographic_area == GeographicArea.NAZIONALE
        assert salary_table.is_valid_on(date(2024, 6, 15))
        assert not salary_table.is_valid_on(date(2027, 1, 1))

    def test_create_geographic_salary_table(self):
        """Test salary table with geographic differentiation."""
        north_salary = SalaryTable(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            level_code="B1",
            base_monthly_salary=Decimal("1650.00"),
            geographic_area=GeographicArea.NORD,
            valid_from=date(2024, 1, 1),
        )

        south_salary = SalaryTable(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            level_code="B1",
            base_monthly_salary=Decimal("1550.00"),
            geographic_area=GeographicArea.SUD,
            valid_from=date(2024, 1, 1),
        )

        assert north_salary.base_monthly_salary > south_salary.base_monthly_salary
        assert north_salary.get_annual_salary() == Decimal("1650.00") * 12

    def test_salary_with_allowances(self):
        """Test salary calculation including allowances."""
        salary_table = SalaryTable(
            ccnl_sector=CCNLSector.TRASPORTI_LOGISTICA,
            level_code="A2",
            base_monthly_salary=Decimal("1800.00"),
            additional_allowances={"indennita_trasporto": Decimal("150.00"), "indennita_turno": Decimal("80.00")},
        )

        total_monthly = salary_table.get_total_monthly_salary()
        assert total_monthly == Decimal("2030.00")  # 1800 + 150 + 80

    def test_13th_14th_month_calculation(self):
        """Test 13th and 14th month salary calculation."""
        salary_table = SalaryTable(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            level_code="E1",
            base_monthly_salary=Decimal("1600.00"),
            thirteenth_month=True,
            fourteenth_month=True,
        )

        annual_salary = salary_table.get_annual_salary_with_additional_months()
        expected = Decimal("1600.00") * 14  # Base salary × 14 months
        assert annual_salary == expected


class TestWorkingHoursModel:
    """Test working hours data model."""

    def test_create_standard_working_hours(self):
        """Test creating standard working hours."""
        hours = WorkingHours(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            ordinary_weekly_hours=40,
            maximum_weekly_hours=48,
            daily_rest_hours=11,
            weekly_rest_hours=24,
        )

        assert hours.ordinary_weekly_hours == 40
        assert hours.get_ordinary_daily_hours() == 8  # 40/5 days

    def test_flexible_working_hours(self):
        """Test flexible working arrangements."""
        flexible_hours = WorkingHours(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            ordinary_weekly_hours=38,
            flexible_hours_allowed=True,
            flexible_hours_range=(6, 10),  # Min-max daily hours
            core_hours=("09:30", "16:00"),
            part_time_allowed=True,
            minimum_part_time_hours=20,
        )

        assert flexible_hours.flexible_hours_allowed is True
        assert flexible_hours.get_min_flexible_daily_hours() == 6
        assert flexible_hours.get_max_flexible_daily_hours() == 10

    def test_shift_work_hours(self):
        """Test shift work configurations."""
        shift_hours = WorkingHours(
            ccnl_sector=CCNLSector.TESSILI,
            ordinary_weekly_hours=40,
            shift_work_allowed=True,
            shift_patterns=["6-14", "14-22", "22-6"],
            night_shift_allowance=Decimal("25.00"),
        )

        assert shift_hours.shift_work_allowed is True
        assert len(shift_hours.shift_patterns) == 3
        assert shift_hours.night_shift_allowance == Decimal("25.00")


class TestOvertimeRulesModel:
    """Test overtime rules data model."""

    def test_basic_overtime_rules(self):
        """Test basic overtime compensation."""
        overtime = OvertimeRules(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            daily_threshold_hours=8,
            weekly_threshold_hours=40,
            daily_overtime_rate=Decimal("1.25"),
            weekend_rate=Decimal("1.50"),
            holiday_rate=Decimal("2.00"),
        )

        assert overtime.daily_overtime_rate == Decimal("1.25")
        assert overtime.holiday_rate == Decimal("2.00")

    def test_overtime_calculation(self):
        """Test overtime payment calculation."""
        overtime = OvertimeRules(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            daily_threshold_hours=8,
            daily_overtime_rate=Decimal("1.30"),
            maximum_monthly_overtime=20,
        )

        base_hourly = Decimal("12.50")
        overtime_pay = overtime.calculate_overtime_pay(base_hourly_rate=base_hourly, overtime_hours=5)

        expected = base_hourly * Decimal("1.30") * 5
        assert overtime_pay == expected

    def test_overtime_limits(self):
        """Test overtime limits and restrictions."""
        overtime = OvertimeRules(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            maximum_daily_overtime=4,
            maximum_weekly_overtime=12,
            maximum_annual_overtime=250,
        )

        assert overtime.is_overtime_allowed(daily_hours=3, weekly_total=10) is True
        assert overtime.is_overtime_allowed(daily_hours=5, weekly_total=10) is False
        assert overtime.is_overtime_allowed(daily_hours=3, weekly_total=15) is False


class TestLeaveEntitlementModel:
    """Test leave entitlement data model."""

    def test_basic_leave_entitlement(self):
        """Test basic vacation leave entitlement."""
        leave = LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.FERIE,
            base_annual_days=24,
            seniority_bonus_schedule={
                60: 2,  # +2 days after 5 years
                120: 4,  # +4 days after 10 years
            },
        )

        assert leave.get_annual_entitlement(months_seniority=30) == 24  # Less than 5 years
        assert leave.get_annual_entitlement(months_seniority=72) == 26  # 6 years = 24 + 2
        assert leave.get_annual_entitlement(months_seniority=150) == 28  # 12.5 years = 24 + 4

    def test_rol_ex_festivita(self):
        """Test ROL (ex-festività) entitlement."""
        rol = LeaveEntitlement(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            leave_type=LeaveType.ROL_EX_FESTIVITA,
            base_annual_hours=32,  # ROL typically in hours
            calculation_method="monthly_accrual",
        )

        monthly_accrual = rol.get_monthly_accrual()
        assert monthly_accrual == 32 / 12  # Hours per month

    def test_permessi_retribuiti(self):
        """Test paid leave permissions."""
        permessi = LeaveEntitlement(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_hours=64,
            minimum_usage_hours=2,
            advance_notice_hours=24,
        )

        assert permessi.base_annual_hours == 64
        assert permessi.minimum_usage_hours == 2

    def test_special_leaves(self):
        """Test special leave types."""
        maternity = LeaveEntitlement(
            ccnl_sector=CCNLSector.TESSILI,
            leave_type=LeaveType.CONGEDO_MATERNITA,
            base_annual_days=150,  # 5 months
            compensation_percentage=Decimal("0.80"),
            mandatory_period=True,
            additional_optional_days=30,
        )

        assert maternity.base_annual_days == 150
        assert maternity.compensation_percentage == Decimal("0.80")
        assert maternity.mandatory_period is True


class TestNoticePeriodsModel:
    """Test notice periods data model."""

    def test_notice_periods_by_category(self):
        """Test notice periods for different worker categories."""
        notices = [
            NoticePerioD(
                ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
                worker_category=WorkerCategory.OPERAIO,
                seniority_months_min=0,
                seniority_months_max=60,
                notice_days=15,
            ),
            NoticePerioD(
                ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
                worker_category=WorkerCategory.IMPIEGATO,
                seniority_months_min=0,
                seniority_months_max=24,
                notice_days=30,
            ),
            NoticePerioD(
                ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
                worker_category=WorkerCategory.QUADRO,
                seniority_months_min=0,
                seniority_months_max=60,
                notice_days=90,
            ),
        ]

        # Test that notice periods increase with worker category
        operaio_notice = next(n for n in notices if n.worker_category == WorkerCategory.OPERAIO)
        impiegato_notice = next(n for n in notices if n.worker_category == WorkerCategory.IMPIEGATO)
        quadro_notice = next(n for n in notices if n.worker_category == WorkerCategory.QUADRO)

        assert operaio_notice.notice_days < impiegato_notice.notice_days < quadro_notice.notice_days

    def test_notice_periods_by_seniority(self):
        """Test notice periods increasing with seniority."""
        short_seniority = NoticePerioD(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            worker_category=WorkerCategory.IMPIEGATO,
            seniority_months_min=0,
            seniority_months_max=24,
            notice_days=15,
        )

        long_seniority = NoticePerioD(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            worker_category=WorkerCategory.IMPIEGATO,
            seniority_months_min=120,  # 10 years
            seniority_months_max=999,
            notice_days=60,
        )

        assert short_seniority.notice_days < long_seniority.notice_days

    def test_notice_period_lookup(self):
        """Test finding correct notice period for given seniority."""
        notice = NoticePerioD(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            worker_category=WorkerCategory.OPERAIO,
            seniority_months_min=24,
            seniority_months_max=120,
            notice_days=30,
        )

        assert notice.applies_to_seniority(36) is True  # 3 years
        assert notice.applies_to_seniority(12) is False  # 1 year
        assert notice.applies_to_seniority(150) is False  # 12.5 years


class TestSpecialAllowanceModel:
    """Test special allowances data model."""

    def test_meal_allowance(self):
        """Test meal allowance."""
        meal_allowance = SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal("7.00"),
            frequency="daily",
            conditions=["Lavoro a tempo pieno", "Orario >= 6 ore"],
        )

        assert meal_allowance.allowance_type == AllowanceType.BUONI_PASTO
        assert meal_allowance.amount == Decimal("7.00")
        monthly_amount = meal_allowance.get_monthly_amount(working_days=22)
        assert monthly_amount == Decimal("7.00") * 22

    def test_travel_allowance(self):
        """Test travel/transport allowance."""
        transport = SpecialAllowance(
            ccnl_sector=CCNLSector.TRASPORTI_LOGISTICA,
            allowance_type=AllowanceType.INDENNITA_TRASPORTO,
            amount=Decimal("120.00"),
            frequency="monthly",
            geographic_areas=[GeographicArea.NORD, GeographicArea.CENTRO],
        )

        assert transport.frequency == "monthly"
        assert len(transport.geographic_areas) == 2
        assert transport.applies_to_area(GeographicArea.NORD) is True
        assert transport.applies_to_area(GeographicArea.SUD) is False

    def test_risk_allowance(self):
        """Test risk/danger allowance."""
        risk_allowance = SpecialAllowance(
            ccnl_sector=CCNLSector.CHIMICI_FARMACEUTICI,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal("200.00"),
            frequency="monthly",
            job_levels=["C3", "C4", "B1", "B2"],
            conditions=["Lavoro con sostanze pericolose", "Certificazione sicurezza"],
        )

        assert AllowanceType.INDENNITA_RISCHIO in [risk_allowance.allowance_type]
        assert "C3" in risk_allowance.job_levels
        assert len(risk_allowance.conditions) == 2


class TestCCNLAgreementModel:
    """Test complete CCNL agreement data model."""

    def test_create_metalmeccanici_ccnl(self):
        """Test creating complete Metalmeccanici CCNL."""
        ccnl = CCNLAgreement(
            sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            name="CCNL Metalmeccanici Industria",
            valid_from=date(2024, 1, 1),
            valid_to=date(2026, 12, 31),
            signatory_unions=["FIOM-CGIL", "FIM-CISL", "UILM-UIL"],
            signatory_employers=["Federmeccanica", "Assistal"],
            renewal_status="vigente",
        )

        assert ccnl.sector == CCNLSector.METALMECCANICI_INDUSTRIA
        assert len(ccnl.signatory_unions) == 3
        assert len(ccnl.signatory_employers) == 2
        assert ccnl.is_currently_valid()

    def test_ccnl_with_job_levels(self):
        """Test CCNL with complete job level structure."""
        job_levels = [
            JobLevel("C1", "Operaio Comune", WorkerCategory.OPERAIO, minimum_experience_months=0),
            JobLevel("C2", "Operaio Qualificato", WorkerCategory.OPERAIO, minimum_experience_months=12),
            JobLevel("C3", "Operaio Specializzato", WorkerCategory.OPERAIO, minimum_experience_months=24),
            JobLevel("D1", "Impiegato 1° Livello", WorkerCategory.IMPIEGATO, minimum_experience_months=0),
            JobLevel("D2", "Impiegato 2° Livello", WorkerCategory.IMPIEGATO, minimum_experience_months=24),
        ]

        ccnl = CCNLAgreement(
            sector=CCNLSector.COMMERCIO_TERZIARIO,
            name="CCNL Commercio e Terziario",
            valid_from=date(2024, 1, 1),
            job_levels=job_levels,
        )

        assert len(ccnl.job_levels) == 5
        operai_levels = ccnl.get_levels_by_category(WorkerCategory.OPERAIO)
        assert len(operai_levels) == 3

    def test_ccnl_with_salary_tables(self):
        """Test CCNL with complete salary structure."""
        salary_tables = [
            SalaryTable(
                ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
                level_code="A1",
                base_monthly_salary=Decimal("1850.00"),
                geographic_area=GeographicArea.NAZIONALE,
            ),
            SalaryTable(
                ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
                level_code="A2",
                base_monthly_salary=Decimal("1750.00"),
                geographic_area=GeographicArea.NAZIONALE,
            ),
        ]

        ccnl = CCNLAgreement(
            sector=CCNLSector.EDILIZIA_INDUSTRIA,
            name="CCNL Edilizia Industria",
            valid_from=date(2024, 1, 1),
            salary_tables=salary_tables,
        )

        a1_salary = ccnl.get_salary_for_level("A1")
        assert a1_salary.base_monthly_salary == Decimal("1850.00")

        a2_salary = ccnl.get_salary_for_level("A2")
        assert a2_salary.base_monthly_salary == Decimal("1750.00")


class TestCCNLCalculatorIntegration:
    """Test CCNL calculator integration with all models."""

    def test_calculate_total_compensation(self):
        """Test comprehensive compensation calculation."""
        # Create test CCNL data
        ccnl = CCNLAgreement(
            sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            name="Test CCNL",
            valid_from=date(2024, 1, 1),
            salary_tables=[
                SalaryTable(
                    ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
                    level_code="C2",
                    base_monthly_salary=Decimal("1650.00"),
                    thirteenth_month=True,
                    fourteenth_month=True,
                )
            ],
            special_allowances=[
                SpecialAllowance(
                    ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
                    allowance_type=AllowanceType.BUONI_PASTO,
                    amount=Decimal("7.00"),
                    frequency="daily",
                )
            ],
        )

        calculator = CCNLCalculator(ccnl)

        total_compensation = calculator.calculate_annual_compensation(
            level_code="C2", working_days_per_month=22, include_allowances=True
        )

        # Expected: (1650 * 14) + (7 * 22 * 12) = 23100 + 1848 = 24948
        expected = Decimal("24948.00")
        assert total_compensation == expected

    def test_calculate_notice_period(self):
        """Test notice period calculation."""
        notice_periods = [
            NoticePerioD(
                ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                worker_category=WorkerCategory.IMPIEGATO,
                seniority_months_min=0,
                seniority_months_max=24,
                notice_days=15,
            ),
            NoticePerioD(
                ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                worker_category=WorkerCategory.IMPIEGATO,
                seniority_months_min=24,
                seniority_months_max=120,
                notice_days=30,
            ),
        ]

        ccnl = CCNLAgreement(
            sector=CCNLSector.COMMERCIO_TERZIARIO,
            name="Test CCNL",
            valid_from=date(2024, 1, 1),
            notice_periods=notice_periods,
        )

        calculator = CCNLCalculator(ccnl)

        # Test different seniority levels
        notice_1_year = calculator.get_notice_period(worker_category=WorkerCategory.IMPIEGATO, seniority_months=12)
        assert notice_1_year == 15

        notice_5_years = calculator.get_notice_period(worker_category=WorkerCategory.IMPIEGATO, seniority_months=60)
        assert notice_5_years == 30

    def test_calculate_leave_entitlement(self):
        """Test leave entitlement calculation."""
        leave_entitlement = LeaveEntitlement(
            ccnl_sector=CCNLSector.TESSILI,
            leave_type=LeaveType.FERIE,
            base_annual_days=22,
            seniority_bonus_schedule={
                60: 2,  # +2 days after 5 years
                120: 4,  # +4 days total after 10 years
            },
        )

        ccnl = CCNLAgreement(
            sector=CCNLSector.TESSILI,
            name="Test CCNL",
            valid_from=date(2024, 1, 1),
            leave_entitlements=[leave_entitlement],
        )

        calculator = CCNLCalculator(ccnl)

        # Test leave calculation for different seniority
        leave_2_years = calculator.calculate_annual_leave(leave_type=LeaveType.FERIE, seniority_months=24)
        assert leave_2_years == 22  # Base entitlement

        leave_7_years = calculator.calculate_annual_leave(leave_type=LeaveType.FERIE, seniority_months=84)
        assert leave_7_years == 24  # Base + 2 bonus days


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.models.ccnl_data"])
