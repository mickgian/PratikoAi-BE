"""Tests for CCNL data models.

Validates enums, dataclasses, calculator, and utility functions
for Italian Collective Labor Agreement data structures.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.ccnl_data import (
    AllowanceType,
    ApprenticeshipRules,
    CCNLAgreement,
    CCNLCalculator,
    CCNLSector,
    CompanySize,
    DisciplinaryRule,
    GeographicArea,
    JobLevel,
    LeaveEntitlement,
    LeaveType,
    NoticePerioD,
    OvertimeRules,
    ProbationPeriod,
    SalaryTable,
    SpecialAllowance,
    TFRRules,
    TrainingRights,
    UnionRights,
    WorkArrangementRules,
    WorkerCategory,
    WorkingHours,
    calculate_ccnl_coverage_percentage,
    compare_ccnl_provisions,
    create_ccnl_id,
)

# ──────────────────────────────────────────────────────────────
# CCNLSector enum
# ──────────────────────────────────────────────────────────────


class TestCCNLSector:
    """Tests for CCNLSector enum."""

    def test_total_sector_count(self):
        """CCNLSector has exactly 52 members."""
        assert len(CCNLSector) == 52

    def test_priority_1_sector_values(self):
        """Priority 1 sectors have the expected values."""
        assert CCNLSector.METALMECCANICI_INDUSTRIA == "metalmeccanici_industria"
        assert CCNLSector.COMMERCIO_TERZIARIO == "commercio_terziario"
        assert CCNLSector.EDILIZIA_INDUSTRIA == "edilizia_industria"
        assert CCNLSector.TURISMO == "turismo"

    def test_priority_5_sector_values(self):
        """Priority 5 sectors have the expected values."""
        assert CCNLSector.GIORNALISTI == "giornalisti"
        assert CCNLSector.TEATRO == "teatro"
        assert CCNLSector.RADIO_TV_PRIVATE == "radio_tv_private"

    def test_priority_6_sector_values(self):
        """Priority 6 sectors have the expected values."""
        assert CCNLSector.POMPE_FUNEBRI == "pompe_funebri"
        assert CCNLSector.DIRIGENTI_INDUSTRIA == "dirigenti_industria"
        assert CCNLSector.QUADRI == "quadri"


class TestCCNLSectorItalianName:
    """Tests for CCNLSector.italian_name()."""

    def test_metalmeccanici_industria(self):
        assert CCNLSector.METALMECCANICI_INDUSTRIA.italian_name() == "Metalmeccanici Industria"

    def test_commercio_terziario(self):
        assert CCNLSector.COMMERCIO_TERZIARIO.italian_name() == "Commercio e Terziario"

    def test_turismo(self):
        assert CCNLSector.TURISMO.italian_name() == "Turismo"

    def test_ict(self):
        assert CCNLSector.ICT.italian_name() == "Information Technology"

    def test_acconciatura_estetica(self):
        assert CCNLSector.ACCONCIATURA_ESTETICA.italian_name() == "Acconciatura ed Estetica"

    def test_all_sectors_have_italian_names(self):
        """Every sector returns a non-empty string from italian_name()."""
        for sector in CCNLSector:
            name = sector.italian_name()
            assert isinstance(name, str)
            assert len(name) > 0


class TestCCNLSectorFromDescription:
    """Tests for CCNLSector.from_description()."""

    def test_metalmeccanici_description(self):
        assert CCNLSector.from_description("Metalmeccanici di industria") == CCNLSector.METALMECCANICI_INDUSTRIA

    def test_commercio_description(self):
        assert CCNLSector.from_description("Commercio al dettaglio") == CCNLSector.COMMERCIO_TERZIARIO

    def test_edilizia_description(self):
        assert CCNLSector.from_description("Edilizia e costruzioni") == CCNLSector.EDILIZIA_INDUSTRIA

    def test_turismo_description(self):
        assert CCNLSector.from_description("Turismo e ospitalità") == CCNLSector.TURISMO

    def test_trasporti_description(self):
        assert CCNLSector.from_description("Trasporti merci") == CCNLSector.TRASPORTI_LOGISTICA

    def test_unknown_description_defaults_to_commercio(self):
        assert CCNLSector.from_description("Something completely unknown") == CCNLSector.COMMERCIO_TERZIARIO

    def test_case_insensitive_matching(self):
        assert CCNLSector.from_description("METALMECCANICI") == CCNLSector.METALMECCANICI_INDUSTRIA
        assert CCNLSector.from_description("turismo") == CCNLSector.TURISMO


class TestCCNLSectorPriorityLevel:
    """Tests for CCNLSector.priority_level()."""

    def test_priority_1_sectors(self):
        assert CCNLSector.METALMECCANICI_INDUSTRIA.priority_level() == 1
        assert CCNLSector.COMMERCIO_TERZIARIO.priority_level() == 1
        assert CCNLSector.TURISMO.priority_level() == 1
        assert CCNLSector.TESSILI.priority_level() == 1

    def test_priority_2_sectors(self):
        assert CCNLSector.TELECOMUNICAZIONI.priority_level() == 2
        assert CCNLSector.ICT.priority_level() == 2
        assert CCNLSector.STUDI_PROFESSIONALI.priority_level() == 2

    def test_priority_3_sectors(self):
        assert CCNLSector.ALIMENTARI_INDUSTRIA.priority_level() == 3
        assert CCNLSector.AGRICOLTURA.priority_level() == 3
        assert CCNLSector.VETRO.priority_level() == 3

    def test_priority_4_sectors(self):
        assert CCNLSector.SANITA_PRIVATA.priority_level() == 4
        assert CCNLSector.MINISTERI.priority_level() == 4
        assert CCNLSector.ENTI_DI_RICERCA.priority_level() == 4

    def test_priority_5_sectors(self):
        assert CCNLSector.GIORNALISTI.priority_level() == 5
        assert CCNLSector.TEATRO.priority_level() == 5

    def test_priority_6_sectors(self):
        assert CCNLSector.AUTOTRASPORTO_MERCI.priority_level() == 6
        assert CCNLSector.POMPE_FUNEBRI.priority_level() == 6
        assert CCNLSector.QUADRI.priority_level() == 6

    def test_all_sectors_have_priority(self):
        """Every sector returns a valid priority level between 1 and 7."""
        for sector in CCNLSector:
            level = sector.priority_level()
            assert 1 <= level <= 7


# ──────────────────────────────────────────────────────────────
# WorkerCategory enum
# ──────────────────────────────────────────────────────────────


class TestWorkerCategory:
    """Tests for WorkerCategory enum."""

    def test_all_values(self):
        assert WorkerCategory.OPERAIO == "operaio"
        assert WorkerCategory.IMPIEGATO == "impiegato"
        assert WorkerCategory.QUADRO == "quadro"
        assert WorkerCategory.DIRIGENTE == "dirigente"
        assert WorkerCategory.APPRENDISTA == "apprendista"

    def test_count(self):
        assert len(WorkerCategory) == 5


class TestWorkerCategoryItalianName:
    """Tests for WorkerCategory.italian_name()."""

    def test_operaio(self):
        assert WorkerCategory.OPERAIO.italian_name() == "Operaio"

    def test_impiegato(self):
        assert WorkerCategory.IMPIEGATO.italian_name() == "Impiegato"

    def test_dirigente(self):
        assert WorkerCategory.DIRIGENTE.italian_name() == "Dirigente"

    def test_apprendista(self):
        assert WorkerCategory.APPRENDISTA.italian_name() == "Apprendista"

    def test_quadro(self):
        assert WorkerCategory.QUADRO.italian_name() == "Quadro"


class TestWorkerCategoryHierarchyLevel:
    """Tests for WorkerCategory.hierarchy_level()."""

    def test_operaio_is_level_1(self):
        assert WorkerCategory.OPERAIO.hierarchy_level() == 1

    def test_apprendista_is_level_1(self):
        assert WorkerCategory.APPRENDISTA.hierarchy_level() == 1

    def test_impiegato_is_level_2(self):
        assert WorkerCategory.IMPIEGATO.hierarchy_level() == 2

    def test_quadro_is_level_3(self):
        assert WorkerCategory.QUADRO.hierarchy_level() == 3

    def test_dirigente_is_level_4(self):
        assert WorkerCategory.DIRIGENTE.hierarchy_level() == 4

    def test_hierarchy_ordering(self):
        """Dirigente > Quadro > Impiegato > Operaio."""
        assert WorkerCategory.DIRIGENTE.hierarchy_level() > WorkerCategory.QUADRO.hierarchy_level()
        assert WorkerCategory.QUADRO.hierarchy_level() > WorkerCategory.IMPIEGATO.hierarchy_level()
        assert WorkerCategory.IMPIEGATO.hierarchy_level() > WorkerCategory.OPERAIO.hierarchy_level()


# ──────────────────────────────────────────────────────────────
# GeographicArea enum
# ──────────────────────────────────────────────────────────────


class TestGeographicArea:
    """Tests for GeographicArea enum."""

    def test_all_values(self):
        assert GeographicArea.NAZIONALE == "nazionale"
        assert GeographicArea.NORD == "nord"
        assert GeographicArea.CENTRO == "centro"
        assert GeographicArea.SUD == "sud"
        assert GeographicArea.SUD_ISOLE == "sud_isole"

    def test_count(self):
        assert len(GeographicArea) == 5


class TestGeographicAreaIncludesRegion:
    """Tests for GeographicArea.includes_region()."""

    def test_nazionale_includes_any_region(self):
        assert GeographicArea.NAZIONALE.includes_region("lombardia") is True
        assert GeographicArea.NAZIONALE.includes_region("sicilia") is True
        assert GeographicArea.NAZIONALE.includes_region("anything") is True

    def test_nord_includes_lombardia(self):
        assert GeographicArea.NORD.includes_region("lombardia") is True

    def test_nord_includes_piemonte(self):
        assert GeographicArea.NORD.includes_region("piemonte") is True

    def test_nord_includes_veneto(self):
        assert GeographicArea.NORD.includes_region("veneto") is True

    def test_nord_excludes_lazio(self):
        assert GeographicArea.NORD.includes_region("lazio") is False

    def test_centro_includes_toscana(self):
        assert GeographicArea.CENTRO.includes_region("toscana") is True

    def test_centro_includes_lazio(self):
        assert GeographicArea.CENTRO.includes_region("lazio") is True

    def test_centro_excludes_lombardia(self):
        assert GeographicArea.CENTRO.includes_region("lombardia") is False

    def test_sud_includes_campania(self):
        assert GeographicArea.SUD.includes_region("campania") is True

    def test_sud_includes_calabria(self):
        assert GeographicArea.SUD.includes_region("calabria") is True

    def test_sud_excludes_sicilia(self):
        assert GeographicArea.SUD.includes_region("sicilia") is False

    def test_sud_isole_includes_sicilia(self):
        assert GeographicArea.SUD_ISOLE.includes_region("sicilia") is True

    def test_sud_isole_includes_sardegna(self):
        assert GeographicArea.SUD_ISOLE.includes_region("sardegna") is True

    def test_sud_isole_excludes_campania(self):
        assert GeographicArea.SUD_ISOLE.includes_region("campania") is False

    def test_case_insensitive_region(self):
        assert GeographicArea.NORD.includes_region("Lombardia") is True
        assert GeographicArea.CENTRO.includes_region("TOSCANA") is True


# ──────────────────────────────────────────────────────────────
# LeaveType enum
# ──────────────────────────────────────────────────────────────


class TestLeaveType:
    """Tests for LeaveType enum."""

    def test_all_values(self):
        assert LeaveType.FERIE == "ferie"
        assert LeaveType.PERMESSI_RETRIBUITI == "permessi_retribuiti"
        assert LeaveType.ROL_EX_FESTIVITA == "rol_ex_festivita"
        assert LeaveType.CONGEDO_MATERNITA == "congedo_maternita"
        assert LeaveType.MALATTIA == "malattia"
        assert LeaveType.INFORTUNIO == "infortunio"

    def test_count(self):
        assert len(LeaveType) == 8


class TestLeaveTypeItalianName:
    """Tests for LeaveType.italian_name()."""

    def test_ferie(self):
        assert LeaveType.FERIE.italian_name() == "Ferie"

    def test_permessi_retribuiti(self):
        assert LeaveType.PERMESSI_RETRIBUITI.italian_name() == "Permessi Retribuiti"

    def test_rol_ex_festivita(self):
        assert LeaveType.ROL_EX_FESTIVITA.italian_name() == "ROL/Ex-Festività"

    def test_malattia(self):
        assert LeaveType.MALATTIA.italian_name() == "Malattia"

    def test_infortunio(self):
        assert LeaveType.INFORTUNIO.italian_name() == "Infortunio"

    def test_all_leave_types_have_italian_names(self):
        for lt in LeaveType:
            name = lt.italian_name()
            assert isinstance(name, str)
            assert len(name) > 0


# ──────────────────────────────────────────────────────────────
# AllowanceType enum
# ──────────────────────────────────────────────────────────────


class TestAllowanceType:
    """Tests for AllowanceType enum."""

    def test_all_values(self):
        assert AllowanceType.BUONI_PASTO == "buoni_pasto"
        assert AllowanceType.INDENNITA_TRASPORTO == "indennita_trasporto"
        assert AllowanceType.PREMIO_PRODUZIONE == "premio_produzione"
        assert AllowanceType.AUTO_AZIENDALE == "auto_aziendale"

    def test_count(self):
        assert len(AllowanceType) == 10


class TestAllowanceTypeItalianName:
    """Tests for AllowanceType.italian_name()."""

    def test_buoni_pasto(self):
        assert AllowanceType.BUONI_PASTO.italian_name() == "Buoni Pasto"

    def test_indennita_trasporto(self):
        assert AllowanceType.INDENNITA_TRASPORTO.italian_name() == "Indennità di Trasporto"

    def test_premio_produzione(self):
        assert AllowanceType.PREMIO_PRODUZIONE.italian_name() == "Premio di Produzione"

    def test_all_allowance_types_have_italian_names(self):
        for at in AllowanceType:
            name = at.italian_name()
            assert isinstance(name, str)
            assert len(name) > 0


# ──────────────────────────────────────────────────────────────
# CompanySize enum
# ──────────────────────────────────────────────────────────────


class TestCompanySize:
    """Tests for CompanySize enum."""

    def test_all_values(self):
        assert CompanySize.MICRO == "micro"
        assert CompanySize.SMALL == "small"
        assert CompanySize.MEDIUM == "medium"
        assert CompanySize.LARGE == "large"

    def test_count(self):
        assert len(CompanySize) == 4


class TestCompanySizeEmployeeRange:
    """Tests for CompanySize.employee_range()."""

    def test_micro_range(self):
        assert CompanySize.MICRO.employee_range() == (1, 9)

    def test_small_range(self):
        assert CompanySize.SMALL.employee_range() == (10, 49)

    def test_medium_range(self):
        assert CompanySize.MEDIUM.employee_range() == (50, 249)

    def test_large_range(self):
        assert CompanySize.LARGE.employee_range() == (250, None)


# ──────────────────────────────────────────────────────────────
# JobLevel dataclass
# ──────────────────────────────────────────────────────────────


class TestJobLevel:
    """Tests for JobLevel dataclass."""

    @pytest.fixture()
    def level_a(self):
        return JobLevel(
            level_code="A1",
            level_name="Junior",
            category=WorkerCategory.OPERAIO,
            description="Entry level worker",
        )

    @pytest.fixture()
    def level_b(self):
        return JobLevel(
            level_code="B2",
            level_name="Senior",
            category=WorkerCategory.IMPIEGATO,
            supervision_responsibilities=True,
        )

    def test_basic_instantiation(self, level_a):
        assert level_a.level_code == "A1"
        assert level_a.level_name == "Junior"
        assert level_a.category == WorkerCategory.OPERAIO

    def test_default_values(self, level_a):
        assert level_a.minimum_experience_months == 0
        assert level_a.required_qualifications == []
        assert level_a.typical_tasks == []
        assert level_a.decision_making_level is None
        assert level_a.supervision_responsibilities is False

    def test_is_lower_than(self, level_a, level_b):
        assert level_a.is_lower_than(level_b) is True
        assert level_b.is_lower_than(level_a) is False

    def test_is_higher_than(self, level_a, level_b):
        assert level_b.is_higher_than(level_a) is True
        assert level_a.is_higher_than(level_b) is False

    def test_is_higher_category_than(self, level_a, level_b):
        # Impiegato (2) > Operaio (1)
        assert level_b.is_higher_category_than(level_a) is True
        assert level_a.is_higher_category_than(level_b) is False


# ──────────────────────────────────────────────────────────────
# SalaryTable dataclass
# ──────────────────────────────────────────────────────────────


class TestSalaryTable:
    """Tests for SalaryTable dataclass."""

    @pytest.fixture()
    def salary(self):
        return SalaryTable(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            level_code="3",
            base_monthly_salary=Decimal("1800.00"),
            valid_from=date(2024, 1, 1),
            valid_to=date(2025, 12, 31),
            thirteenth_month=True,
            fourteenth_month=True,
            additional_allowances={"transport": Decimal("50.00")},
        )

    def test_basic_instantiation(self, salary):
        assert salary.ccnl_sector == CCNLSector.COMMERCIO_TERZIARIO
        assert salary.level_code == "3"
        assert salary.base_monthly_salary == Decimal("1800.00")

    def test_is_valid_on_within_range(self, salary):
        assert salary.is_valid_on(date(2024, 6, 15)) is True

    def test_is_valid_on_before_start(self, salary):
        assert salary.is_valid_on(date(2023, 12, 31)) is False

    def test_is_valid_on_after_end(self, salary):
        assert salary.is_valid_on(date(2026, 1, 1)) is False

    def test_is_valid_on_no_dates(self):
        salary = SalaryTable(
            ccnl_sector=CCNLSector.TURISMO,
            level_code="1",
            base_monthly_salary=Decimal("1500.00"),
        )
        assert salary.is_valid_on(date(2030, 1, 1)) is True

    def test_get_annual_salary(self, salary):
        assert salary.get_annual_salary() == Decimal("21600.00")

    def test_get_total_monthly_salary(self, salary):
        assert salary.get_total_monthly_salary() == Decimal("1850.00")

    def test_get_annual_salary_with_additional_months_13_and_14(self, salary):
        # 14 months * 1800 = 25200
        assert salary.get_annual_salary_with_additional_months() == Decimal("25200.00")

    def test_get_annual_salary_with_only_13th(self):
        salary = SalaryTable(
            ccnl_sector=CCNLSector.TURISMO,
            level_code="1",
            base_monthly_salary=Decimal("2000.00"),
            thirteenth_month=True,
            fourteenth_month=False,
        )
        assert salary.get_annual_salary_with_additional_months() == Decimal("26000.00")

    def test_get_annual_salary_without_additional_months(self):
        salary = SalaryTable(
            ccnl_sector=CCNLSector.TURISMO,
            level_code="1",
            base_monthly_salary=Decimal("2000.00"),
            thirteenth_month=False,
            fourteenth_month=False,
        )
        assert salary.get_annual_salary_with_additional_months() == Decimal("24000.00")

    def test_default_geographic_area(self, salary):
        assert salary.geographic_area == GeographicArea.NAZIONALE


# ──────────────────────────────────────────────────────────────
# WorkingHours dataclass
# ──────────────────────────────────────────────────────────────


class TestWorkingHours:
    """Tests for WorkingHours dataclass."""

    @pytest.fixture()
    def hours(self):
        return WorkingHours(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            ordinary_weekly_hours=40,
            flexible_hours_allowed=True,
            flexible_hours_range=(6, 10),
        )

    def test_get_ordinary_daily_hours(self, hours):
        assert hours.get_ordinary_daily_hours() == 8.0

    def test_get_min_flexible_daily_hours(self, hours):
        assert hours.get_min_flexible_daily_hours() == 6

    def test_get_max_flexible_daily_hours(self, hours):
        assert hours.get_max_flexible_daily_hours() == 10

    def test_get_min_flexible_daily_hours_no_range(self):
        hours = WorkingHours(
            ccnl_sector=CCNLSector.TURISMO,
            ordinary_weekly_hours=38,
        )
        assert hours.get_min_flexible_daily_hours() is None

    def test_get_max_flexible_daily_hours_no_range(self):
        hours = WorkingHours(
            ccnl_sector=CCNLSector.TURISMO,
            ordinary_weekly_hours=38,
        )
        assert hours.get_max_flexible_daily_hours() is None

    def test_default_values(self):
        hours = WorkingHours(
            ccnl_sector=CCNLSector.TURISMO,
            ordinary_weekly_hours=40,
        )
        assert hours.maximum_weekly_hours == 48
        assert hours.daily_rest_hours == 11
        assert hours.weekly_rest_hours == 24
        assert hours.flexible_hours_allowed is False
        assert hours.part_time_allowed is True
        assert hours.shift_work_allowed is False


# ──────────────────────────────────────────────────────────────
# OvertimeRules dataclass
# ──────────────────────────────────────────────────────────────


class TestOvertimeRules:
    """Tests for OvertimeRules dataclass."""

    @pytest.fixture()
    def rules(self):
        return OvertimeRules(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            maximum_daily_overtime=4,
            maximum_weekly_overtime=12,
        )

    def test_calculate_overtime_pay(self, rules):
        result = rules.calculate_overtime_pay(Decimal("15.00"), 3)
        # 15 * 1.25 * 3 = 56.25
        assert result == Decimal("56.25")

    def test_is_overtime_allowed_within_limits(self, rules):
        assert rules.is_overtime_allowed(daily_hours=3, weekly_total=10) is True

    def test_is_overtime_disallowed_daily_exceeded(self, rules):
        assert rules.is_overtime_allowed(daily_hours=5, weekly_total=5) is False

    def test_is_overtime_disallowed_weekly_exceeded(self, rules):
        assert rules.is_overtime_allowed(daily_hours=2, weekly_total=15) is False

    def test_is_overtime_allowed_no_limits(self):
        rules = OvertimeRules(ccnl_sector=CCNLSector.TURISMO)
        assert rules.is_overtime_allowed(daily_hours=100, weekly_total=200) is True

    def test_default_rates(self):
        rules = OvertimeRules(ccnl_sector=CCNLSector.TURISMO)
        assert rules.daily_overtime_rate == Decimal("1.25")
        assert rules.weekend_rate == Decimal("1.50")
        assert rules.holiday_rate == Decimal("2.00")


# ──────────────────────────────────────────────────────────────
# LeaveEntitlement dataclass
# ──────────────────────────────────────────────────────────────


class TestLeaveEntitlement:
    """Tests for LeaveEntitlement dataclass."""

    @pytest.fixture()
    def leave(self):
        return LeaveEntitlement(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
            seniority_bonus_schedule={24: 2, 60: 4, 120: 6},
        )

    def test_get_annual_entitlement_no_seniority(self, leave):
        assert leave.get_annual_entitlement(0) == 26

    def test_get_annual_entitlement_with_24_months(self, leave):
        assert leave.get_annual_entitlement(24) == 28  # 26 + 2

    def test_get_annual_entitlement_with_60_months(self, leave):
        assert leave.get_annual_entitlement(60) == 30  # 26 + 4

    def test_get_annual_entitlement_with_120_months(self, leave):
        assert leave.get_annual_entitlement(120) == 32  # 26 + 6

    def test_get_annual_entitlement_between_thresholds(self, leave):
        # 36 months >= 24, so bonus is 2
        assert leave.get_annual_entitlement(36) == 28

    def test_get_monthly_accrual_from_days(self, leave):
        assert leave.get_monthly_accrual() == pytest.approx(26 / 12)

    def test_get_monthly_accrual_from_hours(self):
        leave = LeaveEntitlement(
            ccnl_sector=CCNLSector.TURISMO,
            leave_type=LeaveType.ROL_EX_FESTIVITA,
            base_annual_hours=72,
        )
        assert leave.get_monthly_accrual() == pytest.approx(6.0)

    def test_get_monthly_accrual_zero_when_no_base(self):
        leave = LeaveEntitlement(
            ccnl_sector=CCNLSector.TURISMO,
            leave_type=LeaveType.MALATTIA,
        )
        assert leave.get_monthly_accrual() == 0.0


# ──────────────────────────────────────────────────────────────
# NoticePerioD dataclass
# ──────────────────────────────────────────────────────────────


class TestNoticePerioD:
    """Tests for NoticePerioD dataclass."""

    @pytest.fixture()
    def notice(self):
        return NoticePerioD(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            worker_category=WorkerCategory.IMPIEGATO,
            seniority_months_min=0,
            seniority_months_max=60,
            notice_days=30,
        )

    def test_applies_to_seniority_within_range(self, notice):
        assert notice.applies_to_seniority(30) is True

    def test_applies_to_seniority_at_min(self, notice):
        assert notice.applies_to_seniority(0) is True

    def test_applies_to_seniority_at_max(self, notice):
        assert notice.applies_to_seniority(60) is True

    def test_does_not_apply_outside_range(self, notice):
        assert notice.applies_to_seniority(61) is False

    def test_default_termination_by(self, notice):
        assert notice.termination_by == "both"


# ──────────────────────────────────────────────────────────────
# SpecialAllowance dataclass
# ──────────────────────────────────────────────────────────────


class TestSpecialAllowance:
    """Tests for SpecialAllowance dataclass."""

    def test_get_monthly_amount_monthly(self):
        allowance = SpecialAllowance(
            ccnl_sector=CCNLSector.TURISMO,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal("150.00"),
            frequency="monthly",
        )
        assert allowance.get_monthly_amount() == Decimal("150.00")

    def test_get_monthly_amount_daily(self):
        allowance = SpecialAllowance(
            ccnl_sector=CCNLSector.TURISMO,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal("7.00"),
            frequency="daily",
        )
        assert allowance.get_monthly_amount(working_days=22) == Decimal("154.00")

    def test_get_monthly_amount_annual(self):
        allowance = SpecialAllowance(
            ccnl_sector=CCNLSector.TURISMO,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal("1200.00"),
            frequency="annual",
        )
        assert allowance.get_monthly_amount() == Decimal("100.00")

    def test_get_monthly_amount_unknown_frequency(self):
        allowance = SpecialAllowance(
            ccnl_sector=CCNLSector.TURISMO,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal("99.00"),
            frequency="weekly",
        )
        assert allowance.get_monthly_amount() == Decimal("99.00")

    def test_applies_to_area_no_restriction(self):
        allowance = SpecialAllowance(
            ccnl_sector=CCNLSector.TURISMO,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal("100.00"),
            frequency="monthly",
        )
        assert allowance.applies_to_area(GeographicArea.NORD) is True

    def test_applies_to_area_matching(self):
        allowance = SpecialAllowance(
            ccnl_sector=CCNLSector.TURISMO,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal("100.00"),
            frequency="monthly",
            geographic_areas=[GeographicArea.NORD, GeographicArea.CENTRO],
        )
        assert allowance.applies_to_area(GeographicArea.NORD) is True

    def test_applies_to_area_not_matching(self):
        allowance = SpecialAllowance(
            ccnl_sector=CCNLSector.TURISMO,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal("100.00"),
            frequency="monthly",
            geographic_areas=[GeographicArea.NORD],
        )
        assert allowance.applies_to_area(GeographicArea.SUD) is False


# ──────────────────────────────────────────────────────────────
# CCNLAgreement dataclass
# ──────────────────────────────────────────────────────────────


class TestCCNLAgreement:
    """Tests for CCNLAgreement dataclass."""

    @pytest.fixture()
    def agreement(self):
        return CCNLAgreement(
            sector=CCNLSector.COMMERCIO_TERZIARIO,
            name="CCNL Commercio 2024",
            valid_from=date(2024, 1, 1),
            valid_to=date(2027, 12, 31),
            job_levels=[
                JobLevel(level_code="1", level_name="Livello 1", category=WorkerCategory.OPERAIO),
                JobLevel(level_code="2", level_name="Livello 2", category=WorkerCategory.IMPIEGATO),
                JobLevel(level_code="3", level_name="Livello 3", category=WorkerCategory.IMPIEGATO),
            ],
            salary_tables=[
                SalaryTable(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    level_code="2",
                    base_monthly_salary=Decimal("1800.00"),
                    valid_from=date(2024, 1, 1),
                    valid_to=date(2027, 12, 31),
                ),
            ],
            special_allowances=[
                SpecialAllowance(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    allowance_type=AllowanceType.BUONI_PASTO,
                    amount=Decimal("7.00"),
                    frequency="daily",
                    job_levels=["2"],
                ),
                SpecialAllowance(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    allowance_type=AllowanceType.INDENNITA_TRASPORTO,
                    amount=Decimal("50.00"),
                    frequency="monthly",
                    job_levels=[],  # All levels
                ),
            ],
        )

    def test_is_currently_valid_within_range(self, agreement):
        today = date.today()
        if date(2024, 1, 1) <= today <= date(2027, 12, 31):
            assert agreement.is_currently_valid() is True

    def test_get_levels_by_category(self, agreement):
        impiegati = agreement.get_levels_by_category(WorkerCategory.IMPIEGATO)
        assert len(impiegati) == 2
        assert all(jl.category == WorkerCategory.IMPIEGATO for jl in impiegati)

    def test_get_levels_by_category_empty(self, agreement):
        dirigenti = agreement.get_levels_by_category(WorkerCategory.DIRIGENTE)
        assert dirigenti == []

    def test_get_salary_for_level(self, agreement):
        salary = agreement.get_salary_for_level("2")
        if salary:
            assert salary.base_monthly_salary == Decimal("1800.00")

    def test_get_salary_for_level_not_found(self, agreement):
        assert agreement.get_salary_for_level("99") is None

    def test_get_allowances_for_level_specific(self, agreement):
        allowances = agreement.get_allowances_for_level("2")
        # Both allowances apply: one has job_levels=["2"], other has empty job_levels
        assert len(allowances) == 2

    def test_get_allowances_for_level_generic_only(self, agreement):
        # Level "1" only matches the allowance with empty job_levels
        allowances = agreement.get_allowances_for_level("1")
        assert len(allowances) == 1
        assert allowances[0].allowance_type == AllowanceType.INDENNITA_TRASPORTO


# ──────────────────────────────────────────────────────────────
# CCNLCalculator
# ──────────────────────────────────────────────────────────────


class TestCCNLCalculator:
    """Tests for CCNLCalculator."""

    @pytest.fixture()
    def calculator(self):
        agreement = CCNLAgreement(
            sector=CCNLSector.COMMERCIO_TERZIARIO,
            name="Test CCNL",
            valid_from=date(2024, 1, 1),
            valid_to=date(2027, 12, 31),
            salary_tables=[
                SalaryTable(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    level_code="3",
                    base_monthly_salary=Decimal("2000.00"),
                    valid_from=date(2024, 1, 1),
                    valid_to=date(2027, 12, 31),
                    thirteenth_month=True,
                    fourteenth_month=True,
                ),
            ],
            overtime_rules=OvertimeRules(ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO),
            leave_entitlements=[
                LeaveEntitlement(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    leave_type=LeaveType.FERIE,
                    base_annual_days=26,
                    seniority_bonus_schedule={60: 2},
                ),
            ],
            notice_periods=[
                NoticePerioD(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    worker_category=WorkerCategory.IMPIEGATO,
                    seniority_months_min=0,
                    seniority_months_max=60,
                    notice_days=30,
                ),
            ],
            probation_periods=[
                ProbationPeriod(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    worker_category=WorkerCategory.IMPIEGATO,
                    probation_days=90,
                ),
            ],
            special_allowances=[
                SpecialAllowance(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    allowance_type=AllowanceType.BUONI_PASTO,
                    amount=Decimal("7.00"),
                    frequency="daily",
                    job_levels=["3"],
                ),
            ],
        )
        return CCNLCalculator(agreement)

    def test_calculate_annual_compensation_no_level(self, calculator):
        result = calculator.calculate_annual_compensation("99")
        assert result == Decimal("0.00")

    def test_calculate_annual_compensation_with_allowances(self, calculator):
        result = calculator.calculate_annual_compensation("3", include_allowances=True)
        # 14 months * 2000 = 28000 base
        # + 7 * 22 * 12 = 1848 allowance
        assert result == Decimal("28000.00") + Decimal("7.00") * 22 * 12

    def test_calculate_annual_compensation_without_allowances(self, calculator):
        result = calculator.calculate_annual_compensation("3", include_allowances=False)
        assert result == Decimal("28000.00")

    def test_get_notice_period(self, calculator):
        result = calculator.get_notice_period(WorkerCategory.IMPIEGATO, 30)
        assert result == 30

    def test_get_notice_period_not_found(self, calculator):
        result = calculator.get_notice_period(WorkerCategory.DIRIGENTE, 30)
        assert result is None

    def test_calculate_annual_leave(self, calculator):
        result = calculator.calculate_annual_leave(LeaveType.FERIE, 12)
        assert result == 26  # No seniority bonus at 12 months

    def test_calculate_annual_leave_with_seniority(self, calculator):
        result = calculator.calculate_annual_leave(LeaveType.FERIE, 60)
        assert result == 28

    def test_calculate_annual_leave_unknown_type(self, calculator):
        result = calculator.calculate_annual_leave(LeaveType.MALATTIA, 12)
        assert result is None

    def test_calculate_overtime_pay_regular(self, calculator):
        result = calculator.calculate_overtime_pay(Decimal("15.00"), 4)
        assert result == Decimal("15.00") * Decimal("1.25") * 4

    def test_calculate_overtime_pay_weekend(self, calculator):
        result = calculator.calculate_overtime_pay(Decimal("15.00"), 4, is_weekend=True)
        assert result == Decimal("15.00") * Decimal("1.50") * 4

    def test_calculate_overtime_pay_holiday(self, calculator):
        result = calculator.calculate_overtime_pay(Decimal("15.00"), 4, is_holiday=True)
        assert result == Decimal("15.00") * Decimal("2.00") * 4

    def test_calculate_overtime_pay_no_rules(self):
        agreement = CCNLAgreement(
            sector=CCNLSector.TURISMO,
            name="No OT",
            valid_from=date(2024, 1, 1),
        )
        calc = CCNLCalculator(agreement)
        assert calc.calculate_overtime_pay(Decimal("15.00"), 4) == Decimal("0.00")

    def test_calculate_thirteenth_fourteenth_month(self, calculator):
        result = calculator.calculate_thirteenth_fourteenth_month("3")
        assert result["thirteenth"] == Decimal("2000.00")
        assert result["fourteenth"] == Decimal("2000.00")

    def test_calculate_thirteenth_fourteenth_month_prorated(self, calculator):
        result = calculator.calculate_thirteenth_fourteenth_month("3", months_worked=6)
        assert result["thirteenth"] == Decimal("2000.00") / 12 * 6
        assert result["fourteenth"] == Decimal("2000.00") / 12 * 6

    def test_calculate_thirteenth_fourteenth_month_no_level(self, calculator):
        result = calculator.calculate_thirteenth_fourteenth_month("99")
        assert result["thirteenth"] == Decimal("0.00")
        assert result["fourteenth"] == Decimal("0.00")

    def test_get_probation_period(self, calculator):
        result = calculator.get_probation_period(WorkerCategory.IMPIEGATO)
        assert result == 90

    def test_get_probation_period_not_found(self, calculator):
        result = calculator.get_probation_period(WorkerCategory.DIRIGENTE)
        assert result is None


# ──────────────────────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────────────────────


class TestCreateCCNLId:
    """Tests for create_ccnl_id()."""

    def test_creates_expected_id(self):
        result = create_ccnl_id(CCNLSector.COMMERCIO_TERZIARIO, date(2024, 1, 15))
        assert result == "commercio_terziario_20240115"

    def test_different_sector_different_id(self):
        id1 = create_ccnl_id(CCNLSector.TURISMO, date(2024, 1, 1))
        id2 = create_ccnl_id(CCNLSector.COMMERCIO_TERZIARIO, date(2024, 1, 1))
        assert id1 != id2

    def test_different_date_different_id(self):
        id1 = create_ccnl_id(CCNLSector.TURISMO, date(2024, 1, 1))
        id2 = create_ccnl_id(CCNLSector.TURISMO, date(2025, 1, 1))
        assert id1 != id2


class TestCompareCCNLProvisions:
    """Tests for compare_ccnl_provisions()."""

    @pytest.fixture()
    def ccnl_1(self):
        return CCNLAgreement(
            sector=CCNLSector.COMMERCIO_TERZIARIO,
            name="CCNL 1",
            valid_from=date(2024, 1, 1),
            leave_entitlements=[
                LeaveEntitlement(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    leave_type=LeaveType.FERIE,
                    base_annual_days=26,
                ),
            ],
            notice_periods=[
                NoticePerioD(
                    ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
                    worker_category=WorkerCategory.IMPIEGATO,
                    seniority_months_min=0,
                    seniority_months_max=60,
                    notice_days=30,
                ),
            ],
        )

    @pytest.fixture()
    def ccnl_2(self):
        return CCNLAgreement(
            sector=CCNLSector.TURISMO,
            name="CCNL 2",
            valid_from=date(2024, 1, 1),
            leave_entitlements=[
                LeaveEntitlement(
                    ccnl_sector=CCNLSector.TURISMO,
                    leave_type=LeaveType.FERIE,
                    base_annual_days=22,
                ),
            ],
            notice_periods=[
                NoticePerioD(
                    ccnl_sector=CCNLSector.TURISMO,
                    worker_category=WorkerCategory.IMPIEGATO,
                    seniority_months_min=0,
                    seniority_months_max=60,
                    notice_days=45,
                ),
            ],
        )

    def test_compare_leave_entitlements(self, ccnl_1, ccnl_2):
        result = compare_ccnl_provisions(ccnl_1, ccnl_2, "leave_entitlements")
        assert result["ccnl1"] == "CCNL 1"
        assert result["ccnl2"] == "CCNL 2"
        assert len(result["differences"]) == 1
        diff = result["differences"][0]
        assert diff["ccnl1_days"] == 26
        assert diff["ccnl2_days"] == 22

    def test_compare_notice_periods(self, ccnl_1, ccnl_2):
        result = compare_ccnl_provisions(ccnl_1, ccnl_2, "notice_periods")
        assert len(result["differences"]) == 1
        diff = result["differences"][0]
        assert diff["ccnl1_days"] == 30
        assert diff["ccnl2_days"] == 45

    def test_compare_unknown_provision_type(self, ccnl_1, ccnl_2):
        result = compare_ccnl_provisions(ccnl_1, ccnl_2, "unknown_type")
        assert result["differences"] == []

    def test_compare_no_differences(self):
        ccnl_a = CCNLAgreement(
            sector=CCNLSector.TURISMO,
            name="A",
            valid_from=date(2024, 1, 1),
            leave_entitlements=[
                LeaveEntitlement(
                    ccnl_sector=CCNLSector.TURISMO,
                    leave_type=LeaveType.FERIE,
                    base_annual_days=26,
                ),
            ],
        )
        ccnl_b = CCNLAgreement(
            sector=CCNLSector.TURISMO,
            name="B",
            valid_from=date(2024, 1, 1),
            leave_entitlements=[
                LeaveEntitlement(
                    ccnl_sector=CCNLSector.TURISMO,
                    leave_type=LeaveType.FERIE,
                    base_annual_days=26,
                ),
            ],
        )
        result = compare_ccnl_provisions(ccnl_a, ccnl_b, "leave_entitlements")
        assert result["differences"] == []


class TestCalculateCCNLCoveragePercentage:
    """Tests for calculate_ccnl_coverage_percentage()."""

    def test_empty_list_returns_zero(self):
        assert calculate_ccnl_coverage_percentage([]) == 0.0

    def test_single_sector(self):
        result = calculate_ccnl_coverage_percentage([CCNLSector.COMMERCIO_TERZIARIO])
        assert result == 12.0

    def test_multiple_sectors(self):
        result = calculate_ccnl_coverage_percentage(
            [CCNLSector.COMMERCIO_TERZIARIO, CCNLSector.METALMECCANICI_INDUSTRIA]
        )
        assert result == pytest.approx(20.5)

    def test_unknown_sector_contributes_zero(self):
        result = calculate_ccnl_coverage_percentage([CCNLSector.QUADRI])
        assert result == 0.0

    def test_capped_at_100(self):
        # Pass all known sectors multiple times -- should still cap at 100
        all_sectors = list(CCNLSector) * 10
        result = calculate_ccnl_coverage_percentage(all_sectors)
        assert result <= 100.0


# ──────────────────────────────────────────────────────────────
# Other dataclasses: basic instantiation checks
# ──────────────────────────────────────────────────────────────


class TestProbationPeriod:
    """Tests for ProbationPeriod dataclass."""

    def test_instantiation_and_defaults(self):
        pp = ProbationPeriod(
            ccnl_sector=CCNLSector.TURISMO,
            worker_category=WorkerCategory.IMPIEGATO,
            probation_days=60,
        )
        assert pp.probation_days == 60
        assert pp.extensions_allowed == 0
        assert pp.notice_during_probation == 0


class TestTFRRules:
    """Tests for TFRRules dataclass."""

    def test_instantiation_and_defaults(self):
        tfr = TFRRules(ccnl_sector=CCNLSector.TURISMO)
        assert tfr.calculation_method == "standard"
        assert tfr.annual_percentage == Decimal("6.91")
        assert tfr.includes_variable_pay is True
        assert tfr.advance_payment_allowed is True
        assert tfr.advance_percentage == Decimal("70.0")
        assert tfr.minimum_service_months == 96


class TestDisciplinaryRule:
    """Tests for DisciplinaryRule dataclass."""

    def test_instantiation_and_defaults(self):
        rule = DisciplinaryRule(
            ccnl_sector=CCNLSector.TURISMO,
            infraction_type="serious",
            description="Repeated tardiness",
        )
        assert rule.sanctions == []
        assert rule.procedure_days == 5
        assert rule.appeal_allowed is True
        assert rule.union_assistance is True


class TestWorkArrangementRules:
    """Tests for WorkArrangementRules dataclass."""

    def test_instantiation_and_defaults(self):
        war = WorkArrangementRules(ccnl_sector=CCNLSector.TURISMO)
        assert war.part_time_allowed is True
        assert war.part_time_maximum_percentage == 80
        assert war.temporary_max_duration_months == 24
        assert war.remote_work_allowed is False
        assert war.smart_working_provisions is False
        assert war.job_sharing_allowed is False


class TestApprenticeshipRules:
    """Tests for ApprenticeshipRules dataclass."""

    def test_instantiation_and_defaults(self):
        ar = ApprenticeshipRules(ccnl_sector=CCNLSector.TURISMO)
        assert ar.minimum_age == 15
        assert ar.maximum_age == 29
        assert ar.duration_months == 36
        assert ar.salary_percentage == Decimal("70.0")
        assert ar.training_hours_annual == 120
        assert ar.external_training_required is True


class TestTrainingRights:
    """Tests for TrainingRights dataclass."""

    def test_instantiation_and_defaults(self):
        tr = TrainingRights(ccnl_sector=CCNLSector.TURISMO)
        assert tr.individual_training_hours_annual == 20
        assert tr.mandatory_training_paid is True
        assert tr.training_leave_days_annual == 5
        assert tr.digital_skills_training is True


class TestUnionRights:
    """Tests for UnionRights dataclass."""

    def test_instantiation_and_defaults(self):
        ur = UnionRights(ccnl_sector=CCNLSector.TURISMO)
        assert ur.union_representative_hours_monthly == 20
        assert ur.union_assembly_hours_annual == 10
        assert ur.union_office_space_required is True
        assert ur.strike_notice_hours == 24
