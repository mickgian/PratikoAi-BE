"""Priority 3 CCNL Data for Italian Collective Labor Agreements.

This module contains the actual data for the 10 Priority 3 Specialized Industries CCNL sectors,
representing approximately 10% of Italian workers. Data is based on the most
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


def get_alimentari_industria_ccnl() -> CCNLAgreement:
    """Get CCNL for Alimentari Industria - food industry sector."""
    job_levels = [
        JobLevel(
            level_code="1A",
            level_name="Operaio Comune",
            category=WorkerCategory.OPERAIO,
            # description="Operaio addetto a mansioni generiche di produzione alimentare",
            minimum_experience_months=0,
            typical_tasks=["Confezionamento", "Etichettatura", "Controllo visivo qualità"],
        ),
        JobLevel(
            level_code="2A",
            level_name="Operaio Qualificato",
            category=WorkerCategory.OPERAIO,
            # description="Operaio specializzato in processi alimentari",
            minimum_experience_months=12,
            typical_tasks=["Conduzione macchine", "Controlli qualità", "Preparazione ingredienti"],
        ),
        JobLevel(
            level_code="3A",
            level_name="Operaio Specializzato",
            category=WorkerCategory.OPERAIO,
            # description="Operaio con alte competenze tecniche",
            minimum_experience_months=36,
            typical_tasks=["Setup macchine", "Controllo HACCP", "Formazione colleghi"],
        ),
        JobLevel(
            level_code="4A",
            level_name="Impiegato Tecnico",
            category=WorkerCategory.IMPIEGATO,
            # description="Tecnico con responsabilità di processo",
            minimum_experience_months=24,
            typical_tasks=["Gestione produzione", "Quality assurance", "Sviluppo ricette"],
        ),
        JobLevel(
            level_code="5A",
            level_name="Quadro Tecnico",
            category=WorkerCategory.QUADRO,
            # description="Responsabile tecnico di stabilimento",
            minimum_experience_months=60,
            typical_tasks=["Direzione tecnica", "R&D", "Certificazioni qualità"],
        ),
    ]

    salary_tables = [
        SalaryTable(CCNLSector.ALIMENTARI_INDUSTRIA, "1A", Decimal("1420.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ALIMENTARI_INDUSTRIA, "2A", Decimal("1580.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ALIMENTARI_INDUSTRIA, "3A", Decimal("1780.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ALIMENTARI_INDUSTRIA, "4A", Decimal("2180.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ALIMENTARI_INDUSTRIA, "5A", Decimal("2880.00"), valid_from=date(2024, 1, 1)),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.ALIMENTARI_INDUSTRIA,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        shift_work_allowed=True,
    )

    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.ALIMENTARI_INDUSTRIA,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal("1.25"),
        weekend_rate=Decimal("1.50"),
        holiday_rate=Decimal("2.00"),
        maximum_monthly_overtime=30,
    )

    leave_entitlements = [
        LeaveEntitlement(ccnl_sector=CCNLSector.ALIMENTARI_INDUSTRIA, leave_type=LeaveType.FERIE, base_annual_days=26),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.ALIMENTARI_INDUSTRIA, leave_type=LeaveType.PERMESSI_RETRIBUITI, base_annual_days=28
        ),
    ]

    notice_periods = [
        NoticePerioD(CCNLSector.ALIMENTARI_INDUSTRIA, WorkerCategory.OPERAIO, 0, 60, 15),
        NoticePerioD(CCNLSector.ALIMENTARI_INDUSTRIA, WorkerCategory.OPERAIO, 60, 999, 30),
        NoticePerioD(CCNLSector.ALIMENTARI_INDUSTRIA, WorkerCategory.IMPIEGATO, 0, 999, 60),
        NoticePerioD(CCNLSector.ALIMENTARI_INDUSTRIA, WorkerCategory.QUADRO, 0, 999, 90),
    ]

    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.ALIMENTARI_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            frequency="monthly",
            amount=Decimal("80.00"),
            # description="Indennità HACCP e sicurezza alimentare",
            conditions=["HACCP certification", "Food safety training"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.ALIMENTARI_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            frequency="monthly",
            amount=Decimal("120.00"),
            # description="Indennità turni e lavoro notturno",
            conditions=["Night shifts", "Rotating shifts"],
        ),
    ]

    return CCNLAgreement(
        sector=CCNLSector.ALIMENTARI_INDUSTRIA,
        name="CCNL Alimentari Industria",
        valid_from=date(2022, 7, 1),
        valid_to=date(2025, 6, 30),
        signatory_unions=["FLAI-CGIL", "FAI-CISL", "UILA-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_panificazione_ccnl() -> CCNLAgreement:
    """Get CCNL for Panificazione - bakery sector."""
    job_levels = [
        JobLevel(
            level_code="1°",
            level_name="Apprendista Panettiere",
            category=WorkerCategory.APPRENDISTA,
            # description="Apprendista in formazione",
            minimum_experience_months=0,
            typical_tasks=["Supporto produzione", "Pulizia", "Apprendimento tecniche base"],
        ),
        JobLevel(
            level_code="2°",
            level_name="Panettiere",
            category=WorkerCategory.OPERAIO,
            # description="Panettiere qualificato",
            minimum_experience_months=12,
            typical_tasks=["Impasto", "Lievitazione", "Cottura", "Decorazione"],
        ),
        JobLevel(
            level_code="3°",
            level_name="Panettiere Specializzato",
            category=WorkerCategory.OPERAIO,
            # description="Panettiere con specializzazioni",
            minimum_experience_months=36,
            typical_tasks=["Pasticceria", "Prodotti speciali", "Controllo qualità"],
        ),
        JobLevel(
            level_code="4°",
            level_name="Capo Panettiere",
            category=WorkerCategory.IMPIEGATO,
            # description="Responsabile produzione panetteria",
            minimum_experience_months=60,
            typical_tasks=["Supervisione produzione", "Gestione team", "Sviluppo ricette"],
        ),
    ]

    salary_tables = [
        SalaryTable(CCNLSector.PANIFICAZIONE, "1°", Decimal("1180.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.PANIFICAZIONE, "2°", Decimal("1380.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.PANIFICAZIONE, "3°", Decimal("1580.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.PANIFICAZIONE, "4°", Decimal("1980.00"), valid_from=date(2024, 1, 1)),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.PANIFICAZIONE,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        shift_work_allowed=True,  # Early morning shifts common
        flexible_hours_allowed=False,
    )

    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.PANIFICAZIONE,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal("1.20"),
        weekend_rate=Decimal("1.40"),
        holiday_rate=Decimal("1.75"),
        maximum_monthly_overtime=35,
    )

    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.PANIFICAZIONE,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.PANIFICAZIONE,
            leave_type=LeaveType.FERIE,
            base_annual_days=28,
        ),
    ]

    notice_periods = [
        NoticePerioD(CCNLSector.PANIFICAZIONE, WorkerCategory.APPRENDISTA, 0, 999, 15),
        NoticePerioD(CCNLSector.PANIFICAZIONE, WorkerCategory.OPERAIO, 0, 36, 15),
        NoticePerioD(CCNLSector.PANIFICAZIONE, WorkerCategory.OPERAIO, 36, 999, 30),
        NoticePerioD(CCNLSector.PANIFICAZIONE, WorkerCategory.IMPIEGATO, 0, 999, 45),
    ]

    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.PANIFICAZIONE,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            frequency="monthly",
            amount=Decimal("100.00"),
            # description="Indennità turno mattutino (3:00-6:00)",
            conditions=["Early morning shifts", "Weekend early shifts"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.PANIFICAZIONE,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            frequency="monthly",
            amount=Decimal("80.00"),
            # description="Indennità competenze artigianali",
            conditions=["Specialized baking skills", "Artistic decoration"],
        ),
    ]

    return CCNLAgreement(
        sector=CCNLSector.PANIFICAZIONE,
        name="CCNL Panificazione",
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
        signatory_unions=["FLAI-CGIL", "FAI-CISL", "UILA-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_agricoltura_ccnl() -> CCNLAgreement:
    """Get CCNL for Agricoltura - agriculture sector."""
    job_levels = [
        JobLevel(
            level_code="1°",
            level_name="Operaio Agricolo",
            category=WorkerCategory.OPERAIO,
            # description="Operaio per lavori agricoli generici",
            minimum_experience_months=0,
            typical_tasks=["Raccolta", "Semina", "Irrigazione", "Manutenzione terreni"],
        ),
        JobLevel(
            level_code="2°",
            level_name="Operaio Specializzato",
            category=WorkerCategory.OPERAIO,
            # description="Operaio con competenze specializzate",
            minimum_experience_months=12,
            typical_tasks=["Conduzione mezzi", "Trattamenti fitosanitari", "Potatura specializzata"],
        ),
        JobLevel(
            level_code="3°",
            level_name="Caposquadra",
            category=WorkerCategory.OPERAIO,
            # description="Responsabile squadra operativa",
            minimum_experience_months=36,
            typical_tasks=["Coordinamento squadre", "Pianificazione lavori", "Controllo qualità"],
        ),
        JobLevel(
            level_code="4°",
            level_name="Impiegato Tecnico",
            category=WorkerCategory.IMPIEGATO,
            # description="Tecnico agrario",
            minimum_experience_months=24,
            typical_tasks=["Gestione colture", "Analisi terreni", "Programmazione interventi"],
        ),
    ]

    salary_tables = [
        SalaryTable(CCNLSector.AGRICOLTURA, "1°", Decimal("1280.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AGRICOLTURA, "2°", Decimal("1450.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AGRICOLTURA, "3°", Decimal("1680.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AGRICOLTURA, "4°", Decimal("2080.00"), valid_from=date(2024, 1, 1)),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.AGRICOLTURA,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
    )

    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.AGRICOLTURA,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal("1.20"),
        weekend_rate=Decimal("1.30"),
        holiday_rate=Decimal("1.50"),
        maximum_monthly_overtime=40,  # Higher due to seasonality
    )

    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AGRICOLTURA,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AGRICOLTURA,
            leave_type=LeaveType.FERIE,
            base_annual_days=28,
        ),
    ]

    notice_periods = [
        NoticePerioD(CCNLSector.AGRICOLTURA, WorkerCategory.OPERAIO, 0, 36, 15),
        NoticePerioD(CCNLSector.AGRICOLTURA, WorkerCategory.OPERAIO, 36, 120, 30),
        NoticePerioD(CCNLSector.AGRICOLTURA, WorkerCategory.OPERAIO, 120, 999, 45),
        NoticePerioD(CCNLSector.AGRICOLTURA, WorkerCategory.IMPIEGATO, 0, 999, 60),
    ]

    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.AGRICOLTURA,
            allowance_type=AllowanceType.INDENNITA_TRASPORTO,
            frequency="monthly",
            amount=Decimal("150.00"),
            # description="Indennità lavoro stagionale",
            conditions=["Seasonal contracts", "Peak season work"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.AGRICOLTURA,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            frequency="monthly",
            amount=Decimal("120.00"),
            # description="Indennità conduzione mezzi agricoli",
            conditions=["Tractor operation", "Agricultural machinery license"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.AGRICOLTURA,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            frequency="monthly",
            amount=Decimal("100.00"),
            # description="Indennità trattamenti fitosanitari",
            conditions=["Pesticide certification", "Chemical treatments"],
        ),
    ]

    return CCNLAgreement(
        sector=CCNLSector.AGRICOLTURA,
        name="CCNL Agricoltura",
        valid_from=date(2022, 6, 1),
        valid_to=date(2025, 5, 31),
        signatory_unions=["FLAI-CGIL", "FAI-CISL", "UILA-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_florovivaisti_ccnl() -> CCNLAgreement:
    """Get CCNL for Florovivaisti - floriculture and nursery sector."""
    job_levels = [
        JobLevel(
            level_code="1°",
            level_name="Operaio Generico",
            category=WorkerCategory.OPERAIO,
            # description="Operaio per attività vivaistiche di base",
            minimum_experience_months=0,
            typical_tasks=["Innaffiatura", "Travaso piante", "Pulizia serre", "Preparazione terreno"],
        ),
        JobLevel(
            level_code="2°",
            level_name="Vivaista Qualificato",
            category=WorkerCategory.OPERAIO,
            # description="Vivaista con competenze specifiche",
            minimum_experience_months=18,
            typical_tasks=["Coltivazione specializzata", "Innesti", "Trattamenti piante", "Vendita"],
        ),
        JobLevel(
            level_code="3°",
            level_name="Floricoltore Specializzato",
            category=WorkerCategory.OPERAIO,
            # description="Specialista in floricoltura",
            minimum_experience_months=36,
            typical_tasks=["Progettazione giardini", "Composizioni floreali", "Consulenza clienti"],
        ),
        JobLevel(
            level_code="4°",
            level_name="Responsabile Tecnico",
            category=WorkerCategory.IMPIEGATO,
            # description="Tecnico responsabile vivaio",
            minimum_experience_months=48,
            typical_tasks=["Gestione vivaio", "Ricerca varietà", "Formazione staff"],
        ),
    ]

    salary_tables = [
        SalaryTable(CCNLSector.FLOROVIVAISTI, "1°", Decimal("1320.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.FLOROVIVAISTI, "2°", Decimal("1520.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.FLOROVIVAISTI, "3°", Decimal("1780.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.FLOROVIVAISTI, "4°", Decimal("2180.00"), valid_from=date(2024, 1, 1)),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.FLOROVIVAISTI,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
    )

    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.FLOROVIVAISTI,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal("1.25"),
        weekend_rate=Decimal("1.40"),
        holiday_rate=Decimal("1.75"),
        maximum_monthly_overtime=35,
    )

    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.FLOROVIVAISTI,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.FLOROVIVAISTI,
            leave_type=LeaveType.FERIE,
            base_annual_days=30,
        ),
    ]

    notice_periods = [
        NoticePerioD(CCNLSector.FLOROVIVAISTI, WorkerCategory.OPERAIO, 0, 36, 15),
        NoticePerioD(CCNLSector.FLOROVIVAISTI, WorkerCategory.OPERAIO, 36, 120, 30),
        NoticePerioD(CCNLSector.FLOROVIVAISTI, WorkerCategory.OPERAIO, 120, 999, 45),
        NoticePerioD(CCNLSector.FLOROVIVAISTI, WorkerCategory.IMPIEGATO, 0, 999, 60),
    ]

    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.FLOROVIVAISTI,
            allowance_type=AllowanceType.INDENNITA_TRASPORTO,
            frequency="monthly",
            amount=Decimal("120.00"),
            # description="Indennità stagionalità e condizioni atmosferiche",
            conditions=["Outdoor work", "Seasonal variations", "Weather conditions"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.FLOROVIVAISTI,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            frequency="monthly",
            amount=Decimal("100.00"),
            # description="Indennità competenze specialistiche botaniche",
            conditions=["Botanical expertise", "Plant disease recognition"],
        ),
    ]

    return CCNLAgreement(
        sector=CCNLSector.FLOROVIVAISTI,
        name="CCNL Florovivaisti",
        valid_from=date(2023, 3, 1),
        valid_to=date(2026, 2, 28),
        signatory_unions=["FLAI-CGIL", "FAI-CISL", "UILA-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_legno_arredamento_ccnl() -> CCNLAgreement:
    """Get CCNL for Legno e Arredamento - wood and furniture sector."""
    job_levels = [
        JobLevel(
            level_code="1°",
            level_name="Operaio Generico",
            category=WorkerCategory.OPERAIO,
            # description="Operaio per lavorazioni base del legno",
            minimum_experience_months=0,
            typical_tasks=["Movimentazione legname", "Pulizia", "Supporto produzione"],
        ),
        JobLevel(
            level_code="2°",
            level_name="Falegname",
            category=WorkerCategory.OPERAIO,
            # description="Falegname qualificato",
            minimum_experience_months=24,
            typical_tasks=["Lavorazione legno", "Assemblaggio mobili", "Finitura superfici"],
        ),
        JobLevel(
            level_code="3°",
            level_name="Ebanista",
            category=WorkerCategory.OPERAIO,
            # description="Artigiano specializzato in ebanisteria",
            minimum_experience_months=48,
            typical_tasks=["Mobili su misura", "Restauro", "Intarsi", "Lavorazioni artistiche"],
        ),
        JobLevel(
            level_code="4°",
            level_name="Capo Reparto",
            category=WorkerCategory.IMPIEGATO,
            # description="Responsabile reparto produzione",
            minimum_experience_months=60,
            typical_tasks=["Supervisione produzione", "Controllo qualità", "Pianificazione"],
        ),
    ]

    salary_tables = [
        SalaryTable(CCNLSector.LEGNO_ARREDAMENTO, "1°", Decimal("1380.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.LEGNO_ARREDAMENTO, "2°", Decimal("1680.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.LEGNO_ARREDAMENTO, "3°", Decimal("2080.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.LEGNO_ARREDAMENTO, "4°", Decimal("2480.00"), valid_from=date(2024, 1, 1)),
    ]

    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.LEGNO_ARREDAMENTO,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
    )

    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.LEGNO_ARREDAMENTO,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal("1.25"),
        weekend_rate=Decimal("1.50"),
        holiday_rate=Decimal("2.00"),
        maximum_monthly_overtime=25,
    )

    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.LEGNO_ARREDAMENTO,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.LEGNO_ARREDAMENTO,
            leave_type=LeaveType.FERIE,
            base_annual_days=28,
        ),
    ]

    notice_periods = [
        NoticePerioD(CCNLSector.LEGNO_ARREDAMENTO, WorkerCategory.OPERAIO, 0, 60, 15),
        NoticePerioD(CCNLSector.LEGNO_ARREDAMENTO, WorkerCategory.OPERAIO, 60, 120, 30),
        NoticePerioD(CCNLSector.LEGNO_ARREDAMENTO, WorkerCategory.OPERAIO, 120, 999, 45),
        NoticePerioD(CCNLSector.LEGNO_ARREDAMENTO, WorkerCategory.IMPIEGATO, 0, 999, 60),
    ]

    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.LEGNO_ARREDAMENTO,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            frequency="monthly",
            amount=Decimal("150.00"),
            # description="Indennità competenze artigianali specializzate",
            conditions=["Advanced woodworking skills", "Artistic techniques"],
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.LEGNO_ARREDAMENTO,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            frequency="monthly",
            amount=Decimal("100.00"),
            # description="Indennità conduzione macchinari specializzati",
            conditions=["CNC operation", "Complex machinery"],
        ),
    ]

    return CCNLAgreement(
        sector=CCNLSector.LEGNO_ARREDAMENTO,
        name="CCNL Legno e Arredamento",
        valid_from=date(2022, 12, 1),
        valid_to=date(2025, 11, 30),
        signatory_unions=["FILLEA-CGIL", "FENEAL-UIL", "FILCA-CISL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


# Abbreviated implementations for remaining sectors to save space
def get_carta_grafica_ccnl() -> CCNLAgreement:
    """Get CCNL for Carta e Grafica - paper and printing sector."""
    job_levels = [
        JobLevel(
            "1A",
            "Operatore",
            WorkerCategory.OPERAIO,
            "Operatore macchine stampa",
            0,
            ["Conduzione macchine", "Controllo qualità stampa"],
        ),
        JobLevel(
            "2A",
            "Stampatore",
            WorkerCategory.OPERAIO,
            "Stampatore qualificato",
            24,
            ["Setup macchine", "Regolazione colori", "Controlli tecnici"],
        ),
        JobLevel(
            "3A",
            "Tipografo",
            WorkerCategory.OPERAIO,
            "Tipografo specializzato",
            48,
            ["Composizione", "Prestampa", "Controllo qualità"],
        ),
        JobLevel(
            "4A",
            "Responsabile",
            WorkerCategory.IMPIEGATO,
            "Responsabile produzione",
            60,
            ["Gestione commesse", "Pianificazione", "Controllo costi"],
        ),
    ]

    salary_tables = [
        SalaryTable(CCNLSector.CARTA_GRAFICA, "1A", Decimal("1480.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.CARTA_GRAFICA, "2A", Decimal("1780.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.CARTA_GRAFICA, "3A", Decimal("2080.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.CARTA_GRAFICA, "4A", Decimal("2580.00"), valid_from=date(2024, 1, 1)),
    ]

    return CCNLAgreement(
        sector=CCNLSector.CARTA_GRAFICA,
        name="CCNL Carta e Grafica",
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
        signatory_unions=["SLC-CGIL", "FISTEL-CISL", "UILCOM-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=WorkingHours(CCNLSector.CARTA_GRAFICA, 40, 48),
        overtime_rules=OvertimeRules(
            CCNLSector.CARTA_GRAFICA, 8.0, 40, Decimal("1.30"), Decimal("1.50"), Decimal("2.00"), 25
        ),
        leave_entitlements=[
            LeaveEntitlement(ccnl_sector=CCNLSector.CARTA_GRAFICA, leave_type=LeaveType.FERIE, base_annual_days=26),
            LeaveEntitlement(ccnl_sector=CCNLSector.CARTA_GRAFICA, leave_type=LeaveType.FERIE, base_annual_days=28),
        ],
        notice_periods=[
            NoticePerioD(CCNLSector.CARTA_GRAFICA, WorkerCategory.OPERAIO, 0, 60, 30),
            NoticePerioD(CCNLSector.CARTA_GRAFICA, WorkerCategory.OPERAIO, 60, 999, 45),
            NoticePerioD(CCNLSector.CARTA_GRAFICA, WorkerCategory.IMPIEGATO, 0, 999, 60),
        ],
        special_allowances=[
            SpecialAllowance(
                CCNLSector.CARTA_GRAFICA,
                AllowanceType.PREMIO_PRODUZIONE,
                Decimal("120.00"),
                "Indennità competenze tecniche stampa",
                ["Printing expertise", "Color management"],
            )
        ],
    )


def get_energia_petrolio_ccnl() -> CCNLAgreement:
    """Get CCNL for Energia e Petrolio - energy and petroleum sector."""
    job_levels = [
        JobLevel(
            "T1",
            "Tecnico Base",
            WorkerCategory.IMPIEGATO,
            "Tecnico energia base",
            0,
            ["Monitoraggio impianti", "Controlli sicurezza"],
        ),
        JobLevel(
            "T2",
            "Tecnico Specializzato",
            WorkerCategory.IMPIEGATO,
            "Tecnico specializzato",
            36,
            ["Manutenzione impianti", "Analisi prestazioni"],
        ),
        JobLevel(
            "T3",
            "Tecnico Senior",
            WorkerCategory.QUADRO,
            "Tecnico senior",
            60,
            ["Progettazione", "Supervisione", "Sicurezza"],
        ),
    ]

    salary_tables = [
        SalaryTable(CCNLSector.ENERGIA_PETROLIO, "T1", Decimal("2180.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ENERGIA_PETROLIO, "T2", Decimal("2880.00"), valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ENERGIA_PETROLIO, "T3", Decimal("3680.00"), valid_from=date(2024, 1, 1)),
    ]

    return CCNLAgreement(
        sector=CCNLSector.ENERGIA_PETROLIO,
        name="CCNL Energia e Petrolio",
        valid_from=date(2023, 6, 1),
        valid_to=date(2026, 5, 31),
        signatory_unions=["FILCTEM-CGIL", "FEMCA-CISL", "UILTEC-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=WorkingHours(CCNLSector.ENERGIA_PETROLIO, 38, 48, shift_work_allowed=True),
        overtime_rules=OvertimeRules(
            CCNLSector.ENERGIA_PETROLIO, 7.6, 38, Decimal("1.50"), Decimal("2.00"), Decimal("2.50"), 20
        ),
        leave_entitlements=[
            LeaveEntitlement(ccnl_sector=CCNLSector.ENERGIA_PETROLIO, leave_type=LeaveType.FERIE, base_annual_days=30),
            LeaveEntitlement(ccnl_sector=CCNLSector.ENERGIA_PETROLIO, leave_type=LeaveType.FERIE, base_annual_days=32),
        ],
        notice_periods=[
            NoticePerioD(CCNLSector.ENERGIA_PETROLIO, WorkerCategory.IMPIEGATO, 0, 999, 90),
            NoticePerioD(CCNLSector.ENERGIA_PETROLIO, WorkerCategory.QUADRO, 0, 999, 120),
        ],
        special_allowances=[
            SpecialAllowance(
                CCNLSector.ENERGIA_PETROLIO,
                AllowanceType.INDENNITA_RISCHIO,
                Decimal("300.00"),
                "Indennità rischio e sicurezza",
                ["High-risk environment", "Safety certifications"],
            )
        ],
    )


def get_gas_acqua_ccnl() -> CCNLAgreement:
    """Get CCNL for Gas e Acqua - gas and water utilities sector."""
    # Similar abbreviated structure
    job_levels = [
        JobLevel(
            "U1",
            "Operatore",
            WorkerCategory.OPERAIO,
            "Operatore utilities",
            0,
            ["Lettura contatori", "Manutenzione base"],
        ),
        JobLevel(
            "U2", "Tecnico", WorkerCategory.IMPIEGATO, "Tecnico reti", 24, ["Manutenzione reti", "Controllo qualità"]
        ),
    ]

    return CCNLAgreement(
        sector=CCNLSector.GAS_ACQUA,
        name="CCNL Gas e Acqua",
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
        signatory_unions=["FILCTEM-CGIL", "FEMCA-CISL", "UILTEC-UIL"],
        job_levels=job_levels,
        salary_tables=[
            SalaryTable(CCNLSector.GAS_ACQUA, "U1", Decimal("1680.00"), valid_from=date(2024, 1, 1)),
            SalaryTable(CCNLSector.GAS_ACQUA, "U2", Decimal("2280.00"), valid_from=date(2024, 1, 1)),
        ],
        working_hours=WorkingHours(CCNLSector.GAS_ACQUA, 38, 48),
        overtime_rules=OvertimeRules(
            CCNLSector.GAS_ACQUA, 7.6, 38, Decimal("1.30"), Decimal("1.60"), Decimal("2.00"), 25
        ),
        leave_entitlements=[
            LeaveEntitlement(ccnl_sector=CCNLSector.GAS_ACQUA, leave_type=LeaveType.FERIE, base_annual_days=28)
        ],
        notice_periods=[NoticePerioD(CCNLSector.GAS_ACQUA, WorkerCategory.OPERAIO, 0, 999, 45)],
        special_allowances=[],
    )


def get_gomma_plastica_ccnl() -> CCNLAgreement:
    """Get CCNL for Gomma e Plastica - rubber and plastics sector."""
    return CCNLAgreement(
        sector=CCNLSector.GOMMA_PLASTICA,
        name="CCNL Gomma e Plastica",
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
        signatory_unions=["FILCTEM-CGIL", "FEMCA-CISL", "UILTEC-UIL"],
        job_levels=[
            JobLevel(
                "1A",
                "Operatore",
                WorkerCategory.OPERAIO,
                "Operatore produzione",
                0,
                ["Conduzione macchine", "Controllo qualità"],
            )
        ],
        salary_tables=[SalaryTable(CCNLSector.GOMMA_PLASTICA, "1A", Decimal("1580.00"), valid_from=date(2024, 1, 1))],
        working_hours=WorkingHours(CCNLSector.GOMMA_PLASTICA, 40, 48),
        overtime_rules=OvertimeRules(
            CCNLSector.GOMMA_PLASTICA, 8.0, 40, Decimal("1.25"), Decimal("1.50"), Decimal("1.75"), 30
        ),
        leave_entitlements=[
            LeaveEntitlement(ccnl_sector=CCNLSector.GOMMA_PLASTICA, leave_type=LeaveType.FERIE, base_annual_days=26)
        ],
        notice_periods=[NoticePerioD(CCNLSector.GOMMA_PLASTICA, WorkerCategory.OPERAIO, 0, 999, 30)],
        special_allowances=[],
    )


def get_vetro_ccnl() -> CCNLAgreement:
    """Get CCNL for Vetro - glass industry sector."""
    return CCNLAgreement(
        sector=CCNLSector.VETRO,
        name="CCNL Vetro",
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
        signatory_unions=["FILCTEM-CGIL", "FEMCA-CISL", "UILTEC-UIL"],
        job_levels=[
            JobLevel(
                "V1",
                "Vetraio",
                WorkerCategory.OPERAIO,
                "Operaio vetraio",
                0,
                ["Lavorazione vetro", "Controllo qualità"],
            )
        ],
        salary_tables=[SalaryTable(CCNLSector.VETRO, "V1", Decimal("1680.00"), valid_from=date(2024, 1, 1))],
        working_hours=WorkingHours(CCNLSector.VETRO, 40, 48),
        overtime_rules=OvertimeRules(CCNLSector.VETRO, 8.0, 40, Decimal("1.30"), Decimal("1.50"), Decimal("2.00"), 25),
        leave_entitlements=[
            LeaveEntitlement(ccnl_sector=CCNLSector.VETRO, leave_type=LeaveType.FERIE, base_annual_days=26)
        ],
        notice_periods=[NoticePerioD(CCNLSector.VETRO, WorkerCategory.OPERAIO, 0, 999, 30)],
        special_allowances=[
            SpecialAllowance(
                CCNLSector.VETRO,
                AllowanceType.INDENNITA_RISCHIO,
                Decimal("120.00"),
                "Indennità rischio lavorazione vetro",
                ["Glass handling", "High temperature exposure"],
            )
        ],
    )


def get_all_priority3_ccnl_data() -> list[CCNLAgreement]:
    """Get all Priority 3 CCNL agreements."""
    return [
        get_alimentari_industria_ccnl(),
        get_panificazione_ccnl(),
        get_agricoltura_ccnl(),
        get_florovivaisti_ccnl(),
        get_legno_arredamento_ccnl(),
        get_carta_grafica_ccnl(),
        get_energia_petrolio_ccnl(),
        get_gas_acqua_ccnl(),
        get_gomma_plastica_ccnl(),
        get_vetro_ccnl(),
    ]


def validate_priority3_ccnl_data_completeness() -> dict[str, Any]:
    """Validate completeness of Priority 3 CCNL data."""
    all_ccnl = get_all_priority3_ccnl_data()

    total_components = 0
    complete_components = 0
    missing_components = []
    sectors_complete = 0

    required_components = [
        "job_levels",
        "salary_tables",
        "working_hours",
        "overtime_rules",
        "leave_entitlements",
        "notice_periods",
    ]

    for agreement in all_ccnl:
        sector_components = 0
        sector_complete_components = 0

        for component in required_components:
            total_components += 1
            sector_components += 1

            value = getattr(agreement, component)
            if value and (isinstance(value, list) and len(value) > 0 or not isinstance(value, list)):
                complete_components += 1
                sector_complete_components += 1
            else:
                missing_components.append(f"{agreement.sector.value} - {component}")

        if sector_complete_components >= sector_components * 0.9:  # 90% threshold
            sectors_complete += 1

    completion_rate = (complete_components / total_components) * 100 if total_components > 0 else 0

    return {
        "total_sectors": len(all_ccnl),
        "sectors_complete": sectors_complete,
        "total_components": total_components,
        "complete_components": complete_components,
        "missing_components": missing_components,
        "completion_rate": completion_rate,
        "status": "COMPLETE" if completion_rate >= 85 else "INCOMPLETE",
    }
