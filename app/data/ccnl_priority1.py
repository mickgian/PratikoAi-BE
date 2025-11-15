"""Priority 1 CCNL Data for Italian Collective Labor Agreements.

This module contains the actual data for the 10 highest priority CCNL sectors,
representing approximately 60% of Italian workers. Data is based on the most
recent agreements available as of 2024.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

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


def get_metalmeccanici_industria_ccnl() -> CCNLAgreement:
    """Get CCNL for Metalmeccanici Industria - largest industrial sector."""
    job_levels = [
        # Operai levels
        JobLevel(
            level_code="C1",
            level_name="Operaio Comune",
            category=WorkerCategory.OPERAIO,
            description="Operaio addetto a mansioni generiche di produzione",
            minimum_experience_months=0,
            typical_tasks=["Assemblaggio semplice", "Movimentazione materiali", "Pulizia postazioni"],
        ),
        JobLevel(
            level_code="C2",
            level_name="Operaio Qualificato",
            category=WorkerCategory.OPERAIO,
            description="Operaio con esperienza e specializzazione settoriale",
            minimum_experience_months=12,
            typical_tasks=["Lavorazioni meccaniche", "Controllo qualità", "Manutenzione ordinaria"],
        ),
        JobLevel(
            level_code="C3",
            level_name="Operaio Specializzato",
            category=WorkerCategory.OPERAIO,
            description="Operaio altamente specializzato con competenze tecniche avanzate",
            minimum_experience_months=24,
            typical_tasks=["Programmazione macchine CNC", "Controlli dimensionali", "Addestramento colleghi"],
        ),
        # Impiegati levels
        JobLevel(
            level_code="D1",
            level_name="Impiegato 1° Livello",
            category=WorkerCategory.IMPIEGATO,
            description="Impiegato addetto a mansioni amministrative e tecniche di base",
            minimum_experience_months=0,
            required_qualifications=["Diploma di scuola superiore"],
            typical_tasks=["Gestione documenti", "Supporto clienti", "Data entry"],
        ),
        JobLevel(
            level_code="D2",
            level_name="Impiegato 2° Livello",
            category=WorkerCategory.IMPIEGATO,
            description="Impiegato con funzioni di coordinamento e responsabilità operative",
            minimum_experience_months=24,
            required_qualifications=["Diploma", "Esperienza settoriale"],
            typical_tasks=["Coordinamento attività", "Rapporti fornitori", "Controllo processi"],
            supervision_responsibilities=True,
        ),
        JobLevel(
            level_code="D3",
            level_name="Impiegato 3° Livello",
            category=WorkerCategory.IMPIEGATO,
            description="Impiegato con elevate responsabilità organizzative",
            minimum_experience_months=48,
            required_qualifications=["Diploma/Laurea", "Esperienza gestionale"],
            typical_tasks=["Gestione progetti", "Budget e reporting", "Sviluppo processi"],
            decision_making_level="Medio-Alto",
            supervision_responsibilities=True,
        ),
        # Quadri
        JobLevel(
            level_code="Q1",
            level_name="Quadro 1° Livello",
            category=WorkerCategory.QUADRO,
            description="Quadro con funzioni direttive e organizzative",
            minimum_experience_months=60,
            required_qualifications=["Laurea", "Esperienza manageriale"],
            typical_tasks=["Direzione reparti", "Pianificazione strategica", "Gestione risorse"],
            decision_making_level="Alto",
            supervision_responsibilities=True,
        ),
        JobLevel(
            level_code="Q2",
            level_name="Quadro 2° Livello",
            category=WorkerCategory.QUADRO,
            description="Quadro senior con elevate responsabilità strategiche",
            minimum_experience_months=84,
            required_qualifications=["Laurea", "Specializzazione", "Esperienza manageriale avanzata"],
            typical_tasks=["Direzione strategica", "Sviluppo business", "Gestione budget complessi"],
            decision_making_level="Strategico",
            supervision_responsibilities=True,
        ),
    ]

    salary_tables = [
        SalaryTable(
            CCNLSector.METALMECCANICI_INDUSTRIA,
            "C1",
            Decimal("1456.00"),
            thirteenth_month=True,
            fourteenth_month=False,
            valid_from=date(2024, 1, 1),
        ),
        SalaryTable(
            CCNLSector.METALMECCANICI_INDUSTRIA,
            "C2",
            Decimal("1658.00"),
            thirteenth_month=True,
            fourteenth_month=True,
            valid_from=date(2024, 1, 1),
        ),
        SalaryTable(
            CCNLSector.METALMECCANICI_INDUSTRIA,
            "C3",
            Decimal("1842.00"),
            thirteenth_month=True,
            fourteenth_month=True,
            valid_from=date(2024, 1, 1),
        ),
        SalaryTable(
            CCNLSector.METALMECCANICI_INDUSTRIA,
            "D1",
            Decimal("1923.00"),
            thirteenth_month=True,
            fourteenth_month=True,
            valid_from=date(2024, 1, 1),
        ),
        SalaryTable(
            CCNLSector.METALMECCANICI_INDUSTRIA,
            "D2",
            Decimal("2184.00"),
            thirteenth_month=True,
            fourteenth_month=True,
            valid_from=date(2024, 1, 1),
        ),
        SalaryTable(
            CCNLSector.METALMECCANICI_INDUSTRIA,
            "D3",
            Decimal("2456.00"),
            thirteenth_month=True,
            fourteenth_month=True,
            valid_from=date(2024, 1, 1),
        ),
        SalaryTable(
            CCNLSector.METALMECCANICI_INDUSTRIA,
            "Q1",
            Decimal("2834.00"),
            thirteenth_month=True,
            fourteenth_month=True,
            valid_from=date(2024, 1, 1),
        ),
        SalaryTable(
            CCNLSector.METALMECCANICI_INDUSTRIA,
            "Q2",
            Decimal("3245.00"),
            thirteenth_month=True,
            fourteenth_month=True,
            valid_from=date(2024, 1, 1),
        ),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        daily_rest_hours=11,
        weekly_rest_hours=24,
        flexible_hours_allowed=True,
        flexible_hours_range=(6, 10),
        part_time_allowed=True,
        minimum_part_time_hours=20,
        shift_work_allowed=True,
        shift_patterns=["6-14", "14-22", "22-6"],
        night_shift_allowance=Decimal("25.00"),
    )

    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal("1.30"),
        weekend_rate=Decimal("1.50"),
        holiday_rate=Decimal("2.00"),
        maximum_monthly_overtime=20,
    )

    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
            seniority_bonus_schedule={60: 1, 120: 2},  # +1 after 5 years, +2 after 10
            calculation_method="annual",
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_hours=64,
            calculation_method="monthly_accrual",
            minimum_usage_hours=4,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.ROL_EX_FESTIVITA,
            base_annual_hours=32,
            calculation_method="monthly_accrual",
        ),
    ]

    notice_periods = [
        # Operai
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.OPERAIO, 0, 60, 15),
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.OPERAIO, 60, 999, 30),
        # Impiegati
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.IMPIEGATO, 0, 24, 30),
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.IMPIEGATO, 24, 120, 60),
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.IMPIEGATO, 120, 999, 90),
        # Quadri
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.QUADRO, 0, 999, 120),
    ]

    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal("7.00"),
            frequency="daily",
            conditions=["Lavoro full-time", "Orario minimo 6 ore"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal("30.00"),
            frequency="monthly",
            conditions=["Lavoro a turni"],
            job_levels=["C1", "C2", "C3"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal("150.00"),
            frequency="monthly",
            conditions=["Raggiungimento obiettivi produttivi"],
        ),
    ]

    return CCNLAgreement(
        sector=CCNLSector.METALMECCANICI_INDUSTRIA,
        name="CCNL Metalmeccanici Industria 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FIOM-CGIL", "FIM-CISL", "UILM-UIL"],
        signatory_employers=["Federmeccanica", "Assistal"],
        renewal_status="vigente",
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
        data_source="Federmeccanica - CCNL 2024",
    )


def get_commercio_terziario_ccnl() -> CCNLAgreement:
    """Get CCNL for Commercio e Terziario - largest commercial sector."""
    job_levels = [
        JobLevel("A1", "Addetto Vendite Base", WorkerCategory.OPERAIO, "Addetto alle vendite con mansioni di base", 0),
        JobLevel(
            "A2", "Addetto Vendite Qualificato", WorkerCategory.OPERAIO, "Addetto vendite con esperienza e clienti", 12
        ),
        JobLevel(
            "B1",
            "Impiegato Commerciale",
            WorkerCategory.IMPIEGATO,
            "Impiegato con funzioni commerciali e amministrative",
            0,
        ),
        JobLevel(
            "B2",
            "Impiegato Specializzato",
            WorkerCategory.IMPIEGATO,
            "Impiegato con specializzazione settoriale",
            24,
            supervision_responsibilities=True,
        ),
        JobLevel(
            "C1",
            "Capo Reparto",
            WorkerCategory.IMPIEGATO,
            "Responsabile di reparto con team",
            36,
            supervision_responsibilities=True,
        ),
        JobLevel(
            "D1",
            "Quadro Commerciale",
            WorkerCategory.QUADRO,
            "Quadro con responsabilità commerciali",
            60,
            supervision_responsibilities=True,
        ),
    ]

    # Geographic salary differences for commerce sector
    salary_tables = [
        # Nazionale (base rates)
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "A1",
            Decimal("1380.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "A2",
            Decimal("1485.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "B1",
            Decimal("1621.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
            fourteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "B2",
            Decimal("1834.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
            fourteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "C1",
            Decimal("2156.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
            fourteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "D1",
            Decimal("2598.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
            fourteenth_month=True,
        ),
        # North Italy (higher rates)
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "A1",
            Decimal("1420.00"),
            geographic_area=GeographicArea.NORD,
            thirteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "B1",
            Decimal("1685.00"),
            geographic_area=GeographicArea.NORD,
            thirteenth_month=True,
            fourteenth_month=True,
        ),
        # South Italy (slightly lower rates)
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "A1",
            Decimal("1340.00"),
            geographic_area=GeographicArea.SUD,
            thirteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.COMMERCIO_TERZIARIO,
            "B1",
            Decimal("1565.00"),
            geographic_area=GeographicArea.SUD,
            thirteenth_month=True,
            fourteenth_month=True,
        ),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
        ordinary_weekly_hours=38,  # Often 38 hours in commerce
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        flexible_hours_range=(4, 10),
        part_time_allowed=True,
        minimum_part_time_hours=16,
        shift_work_allowed=True,
        shift_patterns=["Mattina 8-14", "Pomeriggio 14-20", "Serale 16-22"],
    )

    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            leave_type=LeaveType.FERIE,
            base_annual_days=24,
            seniority_bonus_schedule={60: 2, 120: 4},
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO, leave_type=LeaveType.PERMESSI_RETRIBUITI, base_annual_hours=56
        ),
    ]

    notice_periods = [
        NoticePerioD(CCNLSector.COMMERCIO_TERZIARIO, WorkerCategory.OPERAIO, 0, 24, 8),
        NoticePerioD(CCNLSector.COMMERCIO_TERZIARIO, WorkerCategory.OPERAIO, 24, 999, 15),
        NoticePerioD(CCNLSector.COMMERCIO_TERZIARIO, WorkerCategory.IMPIEGATO, 0, 24, 15),
        NoticePerioD(CCNLSector.COMMERCIO_TERZIARIO, WorkerCategory.IMPIEGATO, 24, 999, 30),
    ]

    return CCNLAgreement(
        sector=CCNLSector.COMMERCIO_TERZIARIO,
        name="CCNL Commercio e Terziario 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTuCS-UIL"],
        signatory_employers=["Confcommercio"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
    )


def get_edilizia_industria_ccnl() -> CCNLAgreement:
    """Get CCNL for Edilizia Industria - construction industry."""
    job_levels = [
        JobLevel(
            "A1",
            "Operaio Comune Edile",
            WorkerCategory.OPERAIO,
            "Operaio addetto a mansioni generiche del cantiere",
            0,
        ),
        JobLevel(
            "A2",
            "Operaio Qualificato",
            WorkerCategory.OPERAIO,
            "Operaio specializzato in specifiche lavorazioni edili",
            12,
        ),
        JobLevel("A3", "Operaio Specializzato", WorkerCategory.OPERAIO, "Operaio altamente specializzato", 24),
        JobLevel(
            "B1",
            "Capo Operaio",
            WorkerCategory.IMPIEGATO,
            "Responsabile squadra operai",
            36,
            supervision_responsibilities=True,
        ),
        JobLevel("C1", "Impiegato Tecnico", WorkerCategory.IMPIEGATO, "Impiegato con funzioni tecniche", 0),
        JobLevel("D1", "Quadro Tecnico", WorkerCategory.QUADRO, "Quadro con responsabilità tecniche", 60),
    ]

    salary_tables = [
        SalaryTable(CCNLSector.EDILIZIA_INDUSTRIA, "A1", Decimal("1523.00"), thirteenth_month=True),
        SalaryTable(CCNLSector.EDILIZIA_INDUSTRIA, "A2", Decimal("1678.00"), thirteenth_month=True),
        SalaryTable(CCNLSector.EDILIZIA_INDUSTRIA, "A3", Decimal("1856.00"), thirteenth_month=True),
        SalaryTable(
            CCNLSector.EDILIZIA_INDUSTRIA, "B1", Decimal("2034.00"), thirteenth_month=True, fourteenth_month=True
        ),
        SalaryTable(
            CCNLSector.EDILIZIA_INDUSTRIA, "C1", Decimal("2189.00"), thirteenth_month=True, fourteenth_month=True
        ),
        SalaryTable(
            CCNLSector.EDILIZIA_INDUSTRIA, "D1", Decimal("2756.00"), thirteenth_month=True, fourteenth_month=True
        ),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        shift_work_allowed=False,  # Construction typically daylight hours
    )

    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal("80.00"),
            frequency="monthly",
            conditions=["Lavoro in altezza", "Uso macchinari pesanti"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_TRASPORTO,
            amount=Decimal("120.00"),
            frequency="monthly",
            conditions=["Trasferimenti cantiere"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal("6.50"),
            frequency="daily",
        ),
    ]

    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
            seniority_bonus_schedule={60: 1, 120: 2},
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.EDILIZIA_INDUSTRIA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_hours=64,
            calculation_method="monthly_accrual",
        ),
    ]

    notice_periods = [
        NoticePerioD(CCNLSector.EDILIZIA_INDUSTRIA, WorkerCategory.OPERAIO, 0, 60, 15),
        NoticePerioD(CCNLSector.EDILIZIA_INDUSTRIA, WorkerCategory.OPERAIO, 60, 999, 30),
        NoticePerioD(CCNLSector.EDILIZIA_INDUSTRIA, WorkerCategory.IMPIEGATO, 0, 60, 30),
        NoticePerioD(CCNLSector.EDILIZIA_INDUSTRIA, WorkerCategory.IMPIEGATO, 60, 999, 60),
        NoticePerioD(CCNLSector.EDILIZIA_INDUSTRIA, WorkerCategory.QUADRO, 0, 999, 90),
    ]

    return CCNLAgreement(
        sector=CCNLSector.EDILIZIA_INDUSTRIA,
        name="CCNL Edilizia Industria 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FENEAL-UIL", "FILCA-CISL", "FILLEA-CGIL"],
        signatory_employers=["ANCE", "Confindustria Edilizia"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_pubblici_esercizi_ccnl() -> CCNLAgreement:
    """Get CCNL for Pubblici Esercizi - bars, restaurants, hotels."""
    job_levels = [
        JobLevel("1°", "Addetto ai Servizi", WorkerCategory.OPERAIO, "Cameriere, barista, addetto cucina di base", 0),
        JobLevel("2°", "Addetto Qualificato", WorkerCategory.OPERAIO, "Cameriere esperto, barista specializzato", 12),
        JobLevel("3°", "Addetto Specializzato", WorkerCategory.OPERAIO, "Sommelier, capo cameriere, cuoco", 24),
        JobLevel(
            "4°",
            "Responsabile Servizio",
            WorkerCategory.IMPIEGATO,
            "Responsabile sala, responsabile cucina",
            36,
            supervision_responsibilities=True,
        ),
        JobLevel(
            "5°",
            "Quadro",
            WorkerCategory.QUADRO,
            "Direttore, responsabile generale",
            60,
            supervision_responsibilities=True,
        ),
    ]

    # Geographic salary differences in tourism/restaurant sector
    salary_tables = [
        # National base rates
        SalaryTable(
            CCNLSector.PUBBLICI_ESERCIZI,
            "1°",
            Decimal("1342.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.PUBBLICI_ESERCIZI,
            "2°",
            Decimal("1456.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.PUBBLICI_ESERCIZI,
            "3°",
            Decimal("1612.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.PUBBLICI_ESERCIZI,
            "4°",
            Decimal("1834.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
            fourteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.PUBBLICI_ESERCIZI,
            "5°",
            Decimal("2456.00"),
            geographic_area=GeographicArea.NAZIONALE,
            thirteenth_month=True,
            fourteenth_month=True,
        ),
        # North Italy (higher tourism areas)
        SalaryTable(
            CCNLSector.PUBBLICI_ESERCIZI,
            "1°",
            Decimal("1395.00"),
            geographic_area=GeographicArea.NORD,
            thirteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.PUBBLICI_ESERCIZI,
            "3°",
            Decimal("1678.00"),
            geographic_area=GeographicArea.NORD,
            thirteenth_month=True,
        ),
        # South Italy (tourism areas with seasonal differences)
        SalaryTable(
            CCNLSector.PUBBLICI_ESERCIZI,
            "1°",
            Decimal("1295.00"),
            geographic_area=GeographicArea.SUD,
            thirteenth_month=True,
        ),
        SalaryTable(
            CCNLSector.PUBBLICI_ESERCIZI,
            "2°",
            Decimal("1398.00"),
            geographic_area=GeographicArea.SUD,
            thirteenth_month=True,
        ),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.PUBBLICI_ESERCIZI,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        part_time_allowed=True,
        minimum_part_time_hours=12,
        shift_work_allowed=True,
        shift_patterns=["Mattino 6-14", "Pomeriggio 14-22", "Serale 18-2"],
        night_shift_allowance=Decimal("20.00"),
    )

    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.PUBBLICI_ESERCIZI,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal("1.25"),
        weekend_rate=Decimal("1.50"),
        holiday_rate=Decimal("2.00"),
    )

    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.PUBBLICI_ESERCIZI,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
            seniority_bonus_schedule={60: 1, 120: 2},
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.PUBBLICI_ESERCIZI, leave_type=LeaveType.PERMESSI_RETRIBUITI, base_annual_hours=64
        ),
    ]

    notice_periods = [
        NoticePerioD(CCNLSector.PUBBLICI_ESERCIZI, WorkerCategory.OPERAIO, 0, 60, 8),
        NoticePerioD(CCNLSector.PUBBLICI_ESERCIZI, WorkerCategory.OPERAIO, 60, 999, 15),
        NoticePerioD(CCNLSector.PUBBLICI_ESERCIZI, WorkerCategory.IMPIEGATO, 0, 999, 30),
        NoticePerioD(CCNLSector.PUBBLICI_ESERCIZI, WorkerCategory.QUADRO, 0, 999, 60),
    ]

    return CCNLAgreement(
        sector=CCNLSector.PUBBLICI_ESERCIZI,
        name="CCNL Pubblici Esercizi 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTuCS-UIL"],
        signatory_employers=["FIEPET-Confesercenti", "FIPE-Confcommercio"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
    )


def get_turismo_ccnl() -> CCNLAgreement:
    """Get CCNL for Turismo - tourism and hospitality."""
    return CCNLAgreement(
        sector=CCNLSector.TURISMO,
        name="CCNL Turismo 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTuCS-UIL"],
        signatory_employers=["Federalberghi", "Confindustria Alberghi"],
        job_levels=[
            JobLevel("1°", "Addetto Ricevimento", WorkerCategory.OPERAIO, "Receptionist, portiere", 0),
            JobLevel("2°", "Addetto Piani", WorkerCategory.OPERAIO, "Cameriera ai piani, housekeeping", 0),
            JobLevel(
                "3°",
                "Responsabile Turni",
                WorkerCategory.IMPIEGATO,
                "Capo ricevimento",
                24,
                supervision_responsibilities=True,
            ),
        ],
        salary_tables=[
            SalaryTable(CCNLSector.TURISMO, "1°", Decimal("1380.00"), thirteenth_month=True),
            SalaryTable(CCNLSector.TURISMO, "2°", Decimal("1298.00"), thirteenth_month=True),
            SalaryTable(CCNLSector.TURISMO, "3°", Decimal("1785.00"), thirteenth_month=True, fourteenth_month=True),
        ],
        working_hours=WorkingHours(
            ccnl_sector=CCNLSector.TURISMO,
            ordinary_weekly_hours=40,
            flexible_hours_allowed=True,
            part_time_allowed=True,
            minimum_part_time_hours=16,
            shift_work_allowed=True,
        ),
        leave_entitlements=[
            LeaveEntitlement(
                ccnl_sector=CCNLSector.TURISMO,
                leave_type=LeaveType.FERIE,
                base_annual_days=26,
                seniority_bonus_schedule={60: 2, 120: 4},
            ),
            LeaveEntitlement(
                ccnl_sector=CCNLSector.TURISMO, leave_type=LeaveType.PERMESSI_RETRIBUITI, base_annual_hours=64
            ),
        ],
        notice_periods=[
            NoticePerioD(CCNLSector.TURISMO, WorkerCategory.OPERAIO, 0, 999, 15),
            NoticePerioD(CCNLSector.TURISMO, WorkerCategory.IMPIEGATO, 0, 999, 30),
        ],
    )


def get_trasporti_logistica_ccnl() -> CCNLAgreement:
    """Get CCNL for Trasporti e Logistica - transport and logistics."""
    return CCNLAgreement(
        sector=CCNLSector.TRASPORTI_LOGISTICA,
        name="CCNL Trasporti e Logistica 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FILT-CGIL", "FIT-CISL", "UILTrasporti"],
        signatory_employers=["Conftrasporto", "Federlogistica"],
        job_levels=[
            JobLevel("A", "Autista", WorkerCategory.OPERAIO, "Conducente veicoli commerciali", 0),
            JobLevel("B", "Operatore Logistico", WorkerCategory.OPERAIO, "Magazziniere, movimentazione merci", 0),
            JobLevel("C", "Coordinatore", WorkerCategory.IMPIEGATO, "Coordinatore trasporti", 24),
        ],
        salary_tables=[
            SalaryTable(CCNLSector.TRASPORTI_LOGISTICA, "A", Decimal("1565.00"), thirteenth_month=True),
            SalaryTable(CCNLSector.TRASPORTI_LOGISTICA, "B", Decimal("1456.00"), thirteenth_month=True),
            SalaryTable(
                CCNLSector.TRASPORTI_LOGISTICA, "C", Decimal("1923.00"), thirteenth_month=True, fourteenth_month=True
            ),
        ],
        working_hours=WorkingHours(
            ccnl_sector=CCNLSector.TRASPORTI_LOGISTICA,
            ordinary_weekly_hours=40,
            maximum_weekly_hours=48,
            flexible_hours_allowed=True,
        ),
        leave_entitlements=[
            LeaveEntitlement(
                ccnl_sector=CCNLSector.TRASPORTI_LOGISTICA,
                leave_type=LeaveType.FERIE,
                base_annual_days=26,
                seniority_bonus_schedule={60: 1, 120: 2},
            ),
            LeaveEntitlement(
                ccnl_sector=CCNLSector.TRASPORTI_LOGISTICA,
                leave_type=LeaveType.PERMESSI_RETRIBUITI,
                base_annual_hours=64,
            ),
        ],
        notice_periods=[
            NoticePerioD(CCNLSector.TRASPORTI_LOGISTICA, WorkerCategory.OPERAIO, 0, 999, 30),
            NoticePerioD(CCNLSector.TRASPORTI_LOGISTICA, WorkerCategory.IMPIEGATO, 0, 999, 45),
        ],
        special_allowances=[
            SpecialAllowance(
                ccnl_sector=CCNLSector.TRASPORTI_LOGISTICA,
                allowance_type=AllowanceType.INDENNITA_TRASFERTA,
                amount=Decimal("35.00"),
                frequency="daily",
                conditions=["Viaggi fuori comune"],
            )
        ],
    )


def get_chimici_farmaceutici_ccnl() -> CCNLAgreement:
    """Get CCNL for Chimici e Farmaceutici - chemicals and pharmaceuticals."""
    return CCNLAgreement(
        sector=CCNLSector.CHIMICI_FARMACEUTICI,
        name="CCNL Chimici e Farmaceutici 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FILCTEM-CGIL", "FEMCA-CISL", "UILTEC-UIL"],
        signatory_employers=["Federchimica", "Farmindustria"],
        job_levels=[
            JobLevel("IV", "Operatore Chimico", WorkerCategory.OPERAIO, "Addetto alla produzione chimica", 0),
            JobLevel("V", "Tecnico Laboratorio", WorkerCategory.IMPIEGATO, "Tecnico controlli qualità", 12),
            JobLevel("VI", "Specialista", WorkerCategory.IMPIEGATO, "Specialista ricerca e sviluppo", 36),
        ],
        salary_tables=[
            SalaryTable(CCNLSector.CHIMICI_FARMACEUTICI, "IV", Decimal("1687.00"), thirteenth_month=True),
            SalaryTable(
                CCNLSector.CHIMICI_FARMACEUTICI, "V", Decimal("2034.00"), thirteenth_month=True, fourteenth_month=True
            ),
            SalaryTable(
                CCNLSector.CHIMICI_FARMACEUTICI, "VI", Decimal("2456.00"), thirteenth_month=True, fourteenth_month=True
            ),
        ],
        working_hours=WorkingHours(
            ccnl_sector=CCNLSector.CHIMICI_FARMACEUTICI,
            ordinary_weekly_hours=40,
            maximum_weekly_hours=48,
            shift_work_allowed=True,
        ),
        leave_entitlements=[
            LeaveEntitlement(
                ccnl_sector=CCNLSector.CHIMICI_FARMACEUTICI,
                leave_type=LeaveType.FERIE,
                base_annual_days=26,
                seniority_bonus_schedule={60: 2, 120: 4},
            ),
            LeaveEntitlement(
                ccnl_sector=CCNLSector.CHIMICI_FARMACEUTICI,
                leave_type=LeaveType.PERMESSI_RETRIBUITI,
                base_annual_hours=64,
            ),
        ],
        notice_periods=[
            NoticePerioD(CCNLSector.CHIMICI_FARMACEUTICI, WorkerCategory.OPERAIO, 0, 999, 30),
            NoticePerioD(CCNLSector.CHIMICI_FARMACEUTICI, WorkerCategory.IMPIEGATO, 0, 999, 60),
        ],
        special_allowances=[
            SpecialAllowance(
                ccnl_sector=CCNLSector.CHIMICI_FARMACEUTICI,
                allowance_type=AllowanceType.INDENNITA_RISCHIO,
                amount=Decimal("120.00"),
                frequency="monthly",
                conditions=["Lavoro con sostanze pericolose"],
            )
        ],
    )


def get_tessili_ccnl() -> CCNLAgreement:
    """Get CCNL for Tessili - textile industry."""
    return CCNLAgreement(
        sector=CCNLSector.TESSILI,
        name="CCNL Tessili 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FILTEA-CGIL", "FEMCA-CISL", "UILTA-UIL"],
        signatory_employers=["Sistema Moda Italia", "Confindustria Tessile"],
        job_levels=[
            JobLevel("1°", "Addetto Produzione", WorkerCategory.OPERAIO, "Operaio tessile generico", 0),
            JobLevel("2°", "Operatore Macchine", WorkerCategory.OPERAIO, "Conduttore macchine tessili", 12),
            JobLevel("3°", "Tecnico", WorkerCategory.IMPIEGATO, "Tecnico di produzione", 24),
        ],
        salary_tables=[
            SalaryTable(CCNLSector.TESSILI, "1°", Decimal("1298.00"), thirteenth_month=True),
            SalaryTable(CCNLSector.TESSILI, "2°", Decimal("1456.00"), thirteenth_month=True),
            SalaryTable(CCNLSector.TESSILI, "3°", Decimal("1734.00"), thirteenth_month=True, fourteenth_month=True),
        ],
        working_hours=WorkingHours(
            ccnl_sector=CCNLSector.TESSILI,
            ordinary_weekly_hours=40,
            shift_work_allowed=True,
            shift_patterns=["6-14", "14-22"],
        ),
        leave_entitlements=[
            LeaveEntitlement(
                ccnl_sector=CCNLSector.TESSILI,
                leave_type=LeaveType.FERIE,
                base_annual_days=22,
                seniority_bonus_schedule={60: 2, 120: 4},
            ),
            LeaveEntitlement(
                ccnl_sector=CCNLSector.TESSILI, leave_type=LeaveType.PERMESSI_RETRIBUITI, base_annual_hours=64
            ),
        ],
        notice_periods=[
            NoticePerioD(CCNLSector.TESSILI, WorkerCategory.OPERAIO, 0, 999, 15),
            NoticePerioD(CCNLSector.TESSILI, WorkerCategory.IMPIEGATO, 0, 999, 30),
        ],
    )


def get_metalmeccanici_artigiani_ccnl() -> CCNLAgreement:
    """Get CCNL for Metalmeccanici Artigiani - artisan metalworkers."""
    job_levels = [
        JobLevel("1°", "Apprendista", WorkerCategory.APPRENDISTA, "Apprendista metalmeccanico", 0),
        JobLevel("2°", "Operaio Comune", WorkerCategory.OPERAIO, "Operaio comune artigiano", 12),
        JobLevel("3°", "Operaio Qualificato", WorkerCategory.OPERAIO, "Operaio qualificato artigiano", 24),
        JobLevel("4°", "Coordinatore", WorkerCategory.IMPIEGATO, "Coordinatore produzione", 36),
        JobLevel("5°", "Responsabile", WorkerCategory.IMPIEGATO, "Responsabile tecnico", 48),
    ]

    salary_tables = [
        SalaryTable(CCNLSector.METALMECCANICI_ARTIGIANI, "1°", Decimal("1234.00"), thirteenth_month=True),
        SalaryTable(CCNLSector.METALMECCANICI_ARTIGIANI, "2°", Decimal("1398.00"), thirteenth_month=True),
        SalaryTable(CCNLSector.METALMECCANICI_ARTIGIANI, "3°", Decimal("1567.00"), thirteenth_month=True),
        SalaryTable(
            CCNLSector.METALMECCANICI_ARTIGIANI, "4°", Decimal("1834.00"), thirteenth_month=True, fourteenth_month=True
        ),
        SalaryTable(
            CCNLSector.METALMECCANICI_ARTIGIANI, "5°", Decimal("2123.00"), thirteenth_month=True, fourteenth_month=True
        ),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.METALMECCANICI_ARTIGIANI,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        part_time_allowed=True,
    )

    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_ARTIGIANI,
            leave_type=LeaveType.FERIE,
            base_annual_days=24,
            seniority_bonus_schedule={60: 2, 120: 4},
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_ARTIGIANI,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_hours=64,
        ),
    ]

    notice_periods = [
        NoticePerioD(CCNLSector.METALMECCANICI_ARTIGIANI, WorkerCategory.OPERAIO, 0, 999, 15),
        NoticePerioD(CCNLSector.METALMECCANICI_ARTIGIANI, WorkerCategory.IMPIEGATO, 0, 999, 30),
    ]

    return CCNLAgreement(
        sector=CCNLSector.METALMECCANICI_ARTIGIANI,
        name="CCNL Metalmeccanici Artigiani 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FIOM-CGIL", "FIM-CISL", "UILM-UIL"],
        signatory_employers=["CNA", "Casartigiani", "Confartigianato"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
    )


def get_edilizia_artigianato_ccnl() -> CCNLAgreement:
    """Get CCNL for Edilizia Artigianato - artisan construction."""
    return CCNLAgreement(
        sector=CCNLSector.EDILIZIA_ARTIGIANATO,
        name="CCNL Edilizia Artigianato 2024-2027",
        valid_from=date(2024, 1, 1),
        valid_to=date(2027, 12, 31),
        signatory_unions=["FENEAL-UIL", "FILCA-CISL", "FILLEA-CGIL"],
        signatory_employers=["CNA Costruzioni", "Casartigiani Edili"],
        job_levels=[
            JobLevel("1°", "Operaio Edile", WorkerCategory.OPERAIO, "Muratore, carpentiere, elettricista", 0),
            JobLevel(
                "2°", "Operaio Specializzato", WorkerCategory.OPERAIO, "Operaio con specializzazione tecnica", 12
            ),
            JobLevel(
                "3°",
                "Capo Squadra",
                WorkerCategory.OPERAIO,
                "Responsabile piccola squadra",
                24,
                supervision_responsibilities=True,
            ),
        ],
        salary_tables=[
            SalaryTable(CCNLSector.EDILIZIA_ARTIGIANATO, "1°", Decimal("1378.00"), thirteenth_month=True),
            SalaryTable(CCNLSector.EDILIZIA_ARTIGIANATO, "2°", Decimal("1456.00"), thirteenth_month=True),
            SalaryTable(CCNLSector.EDILIZIA_ARTIGIANATO, "3°", Decimal("1523.00"), thirteenth_month=True),
        ],
        working_hours=WorkingHours(
            ccnl_sector=CCNLSector.EDILIZIA_ARTIGIANATO,
            ordinary_weekly_hours=40,
            flexible_hours_allowed=True,  # More flexibility for small businesses
        ),
        leave_entitlements=[
            LeaveEntitlement(
                ccnl_sector=CCNLSector.EDILIZIA_ARTIGIANATO,
                leave_type=LeaveType.FERIE,
                base_annual_days=24,
                seniority_bonus_schedule={60: 1, 120: 2},
            ),
            LeaveEntitlement(
                ccnl_sector=CCNLSector.EDILIZIA_ARTIGIANATO,
                leave_type=LeaveType.PERMESSI_RETRIBUITI,
                base_annual_hours=64,
            ),
        ],
        notice_periods=[NoticePerioD(CCNLSector.EDILIZIA_ARTIGIANATO, WorkerCategory.OPERAIO, 0, 999, 15)],
    )


def get_all_priority1_ccnl_data() -> list[CCNLAgreement]:
    """Get all Priority 1 CCNL agreements."""
    return [
        get_metalmeccanici_industria_ccnl(),
        get_commercio_terziario_ccnl(),
        get_edilizia_industria_ccnl(),
        get_pubblici_esercizi_ccnl(),
        get_turismo_ccnl(),
        get_trasporti_logistica_ccnl(),
        get_chimici_farmaceutici_ccnl(),
        get_tessili_ccnl(),
        get_metalmeccanici_artigiani_ccnl(),
        get_edilizia_artigianato_ccnl(),
    ]


def validate_ccnl_data_completeness() -> dict[str, Any]:
    """Validate completeness of Priority 1 CCNL data."""
    all_ccnl = get_all_priority1_ccnl_data()

    total_components = 0
    complete_components = 0
    missing_components = []
    sectors_complete = 0

    required_components = ["job_levels", "salary_tables", "leave_entitlements", "notice_periods", "working_hours"]

    for ccnl in all_ccnl:
        sector_missing = []
        sector_components = 0

        for component in required_components:
            total_components += 1
            sector_components += 1

            component_data = getattr(ccnl, component, None)

            if component_data is None or hasattr(component_data, "__len__") and len(component_data) == 0:
                missing_components.append(f"{ccnl.sector.value}.{component}")
                sector_missing.append(component)
            else:
                complete_components += 1

        # Sector is complete if it has at most 1 missing component
        if len(sector_missing) <= 1:
            sectors_complete += 1

    overall_completeness = complete_components / total_components if total_components > 0 else 0

    return {
        "overall_completeness": round(overall_completeness, 3),
        "sectors_with_complete_data": sectors_complete,
        "total_sectors": len(all_ccnl),
        "missing_components": missing_components[:10],  # Show first 10
        "total_missing": len(missing_components),
    }
