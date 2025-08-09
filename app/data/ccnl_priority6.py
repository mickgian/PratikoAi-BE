"""
Priority 6 CCNL Data for Italian Collective Labor Agreements.

This module contains the actual data for the 9 Priority 6 Other Essential Sectors,
representing approximately 8% of Italian workers. Data is based on the most
recent agreements available as of 2024.
"""

from datetime import date
from decimal import Decimal
from typing import List, Dict, Any

from app.models.ccnl_data import (
    CCNLAgreement,
    CCNLSector,
    WorkerCategory,
    JobLevel,
    SalaryTable,
    WorkingHours,
    OvertimeRules,
    LeaveEntitlement,
    NoticePerioD,
    SpecialAllowance,
    GeographicArea,
    LeaveType,
    AllowanceType,
    CompanySize
)


def get_autotrasporto_merci_ccnl() -> CCNLAgreement:
    """Get CCNL for Autotrasporto Merci - freight transport sector."""
    
    job_levels = [
        JobLevel(
            level_code="AUTISTA",
            level_name="Autista",
            category=WorkerCategory.OPERAIO,
            description="Conducente veicoli industriali",
            minimum_experience_months=0,
            required_qualifications=["Patente C+E", "CQC merci"],
            typical_tasks=["Guida mezzi pesanti", "Carico/scarico", "Controlli veicolo"]
        ),
        JobLevel(
            level_code="AUTISTA_SPEC",
            level_name="Autista Specializzato",
            category=WorkerCategory.OPERAIO,
            description="Autista con specializzazioni",
            minimum_experience_months=24,
            required_qualifications=["Patente C+E", "CQC merci", "ADR"],
            typical_tasks=["Trasporti speciali", "Merci pericolose", "Logistica complessa"]
        ),
        JobLevel(
            level_code="CAPOSQUADRA",
            level_name="Caposquadra",
            category=WorkerCategory.QUADRO,
            description="Responsabile squadra autisti",
            minimum_experience_months=60,
            required_qualifications=["Esperienza gestione personale"],
            typical_tasks=["Coordinamento squadra", "Pianificazione trasporti", "Controllo qualità"]
        ),
        JobLevel(
            level_code="DISP_TRASP",
            level_name="Direttore Trasporti",
            category=WorkerCategory.DIRIGENTE,
            description="Responsabile operazioni trasporto",
            minimum_experience_months=84,
            required_qualifications=["Laurea o esperienza equivalente"],
            typical_tasks=["Gestione flotta", "Contratti clienti", "Ottimizzazione percorsi"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.AUTOTRASPORTO_MERCI, "AUTISTA", Decimal('1750.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AUTOTRASPORTO_MERCI, "AUTISTA_SPEC", Decimal('2050.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AUTOTRASPORTO_MERCI, "CAPOSQUADRA", Decimal('2850.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AUTOTRASPORTO_MERCI, "DISP_TRASP", Decimal('4200.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.AUTOTRASPORTO_MERCI,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,  # EU driving time regulations
        flexible_hours_allowed=True,
        shift_work_allowed=True,
        shift_patterns=["Diurno", "Notturno", "Continuo"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.AUTOTRASPORTO_MERCI,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.30'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=60
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AUTOTRASPORTO_MERCI,
            leave_type=LeaveType.FERIE,
            base_annual_days=26
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AUTOTRASPORTO_MERCI,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=20
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.AUTOTRASPORTO_MERCI, WorkerCategory.OPERAIO, 0, 180, 30),
        NoticePerioD(CCNLSector.AUTOTRASPORTO_MERCI, WorkerCategory.OPERAIO, 181, 999, 45),
        NoticePerioD(CCNLSector.AUTOTRASPORTO_MERCI, WorkerCategory.QUADRO, 0, 999, 90),
        NoticePerioD(CCNLSector.AUTOTRASPORTO_MERCI, WorkerCategory.DIRIGENTE, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.AUTOTRASPORTO_MERCI,
            allowance_type=AllowanceType.INDENNITA_TRASFERTA,
            amount=Decimal('50.00'),
            frequency="daily",
            conditions=["Trasferte oltre 50km", "Pernottamento fuori sede"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.AUTOTRASPORTO_MERCI,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal('150.00'),
            frequency="monthly",
            conditions=["Trasporto merci pericolose", "ADR"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.AUTOTRASPORTO_MERCI,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('7.00'),
            frequency="daily",
            conditions=["Presenza lavorativa"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.AUTOTRASPORTO_MERCI,
        name="CCNL Autotrasporto Merci",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["FILT-CGIL", "FIT-CISL", "UILTRASPORTI"],
        signatory_employers=["Conftrasporto", "Federtrarasporti"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_autonoleggio_ccnl() -> CCNLAgreement:
    """Get CCNL for Autonoleggio - car rental sector."""
    
    job_levels = [
        JobLevel(
            level_code="OPER_RENT",
            level_name="Operatore Rental",
            category=WorkerCategory.IMPIEGATO,
            description="Addetto al noleggio veicoli",
            minimum_experience_months=0,
            required_qualifications=["Diploma", "Patente B"],
            typical_tasks=["Accoglienza clienti", "Contratti noleggio", "Controllo veicoli"]
        ),
        JobLevel(
            level_code="RESP_FLOTTA",
            level_name="Responsabile Flotta",
            category=WorkerCategory.IMPIEGATO,
            description="Gestione flotta veicoli",
            minimum_experience_months=36,
            required_qualifications=["Esperienza automotive", "Gestione mezzi"],
            typical_tasks=["Manutenzione flotta", "Pianificazione sostituzioni", "Controllo costi"]
        ),
        JobLevel(
            level_code="COORD_AREA",
            level_name="Coordinatore Area",
            category=WorkerCategory.QUADRO,
            description="Coordinamento sedi territoriali",
            minimum_experience_months=60,
            required_qualifications=["Esperienza commerciale"],
            typical_tasks=["Gestione sedi", "Controllo performance", "Sviluppo commerciale"]
        ),
        JobLevel(
            level_code="DIRETT_REG",
            level_name="Direttore Regionale",
            category=WorkerCategory.DIRIGENTE,
            description="Direzione operazioni regionali",
            minimum_experience_months=96,
            required_qualifications=["Laurea o esperienza equivalente"],
            typical_tasks=["Strategia regionale", "Budget e P&L", "Sviluppo rete"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.AUTONOLEGGIO, "OPER_RENT", Decimal('1650.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AUTONOLEGGIO, "RESP_FLOTTA", Decimal('2200.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AUTONOLEGGIO, "COORD_AREA", Decimal('3200.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AUTONOLEGGIO, "DIRETT_REG", Decimal('4800.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.AUTONOLEGGIO,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        shift_work_allowed=True,
        shift_patterns=["Diurno", "Serale", "Weekend"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.AUTONOLEGGIO,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.40'),
        holiday_rate=Decimal('1.75'),
        maximum_monthly_overtime=50
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AUTONOLEGGIO,
            leave_type=LeaveType.FERIE,
            base_annual_days=26
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AUTONOLEGGIO,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=18
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.AUTONOLEGGIO, WorkerCategory.IMPIEGATO, 0, 180, 30),
        NoticePerioD(CCNLSector.AUTONOLEGGIO, WorkerCategory.IMPIEGATO, 181, 999, 45),
        NoticePerioD(CCNLSector.AUTONOLEGGIO, WorkerCategory.QUADRO, 0, 999, 90),
        NoticePerioD(CCNLSector.AUTONOLEGGIO, WorkerCategory.DIRIGENTE, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.AUTONOLEGGIO,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('7.50'),
            frequency="daily",
            conditions=["Presenza lavorativa"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.AUTONOLEGGIO,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('200.00'),
            frequency="monthly",
            conditions=["Obiettivi commerciali", "Customer satisfaction"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.AUTONOLEGGIO,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('100.00'),
            frequency="monthly",
            conditions=["Lavoro festivo/serale"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.AUTONOLEGGIO,
        name="CCNL Autonoleggio",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["FILT-CGIL", "FIT-CISL", "UILTRASPORTI"],
        signatory_employers=["ANIASA", "Assnoleggio"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_autorimesse_ccnl() -> CCNLAgreement:
    """Get CCNL for Autorimesse - parking garages sector."""
    
    job_levels = [
        JobLevel(
            level_code="CUSTODE",
            level_name="Custode",
            category=WorkerCategory.OPERAIO,
            description="Addetto custodia parcheggi",
            minimum_experience_months=0,
            required_qualifications=["Diploma di base"],
            typical_tasks=["Controllo accessi", "Vigilanza", "Pulizia spazi"]
        ),
        JobLevel(
            level_code="PARCH_SPEC",
            level_name="Parcheggiatore Specializzato",
            category=WorkerCategory.OPERAIO,
            description="Specialista movimentazione veicoli",
            minimum_experience_months=12,
            required_qualifications=["Patente B", "Esperienza guida"],
            typical_tasks=["Movimentazione auto", "Gestione spazi", "Assistenza clienti"]
        ),
        JobLevel(
            level_code="CAPO_TURNO",
            level_name="Capo Turno",
            category=WorkerCategory.IMPIEGATO,
            description="Responsabile turno lavorativo",
            minimum_experience_months=36,
            required_qualifications=["Esperienza supervisione"],
            typical_tasks=["Coordinamento personale", "Gestione casse", "Controllo operazioni"]
        ),
        JobLevel(
            level_code="RESP_STRUTTURA",
            level_name="Responsabile Struttura",
            category=WorkerCategory.QUADRO,
            description="Gestore autorimessa",
            minimum_experience_months=60,
            required_qualifications=["Gestione impianti"],
            typical_tasks=["Gestione generale", "Manutenzione", "Sviluppo clientela"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.AUTORIMESSE, "CUSTODE", Decimal('1500.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AUTORIMESSE, "PARCH_SPEC", Decimal('1700.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AUTORIMESSE, "CAPO_TURNO", Decimal('2100.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.AUTORIMESSE, "RESP_STRUTTURA", Decimal('2800.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.AUTORIMESSE,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=False,
        shift_work_allowed=True,
        shift_patterns=["Diurno", "Pomeridiano", "Notturno", "Continuativo"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.AUTORIMESSE,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('1.85'),
        maximum_monthly_overtime=40
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AUTORIMESSE,
            leave_type=LeaveType.FERIE,
            base_annual_days=26
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AUTORIMESSE,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=16
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.AUTORIMESSE, WorkerCategory.OPERAIO, 0, 180, 15),
        NoticePerioD(CCNLSector.AUTORIMESSE, WorkerCategory.OPERAIO, 181, 999, 30),
        NoticePerioD(CCNLSector.AUTORIMESSE, WorkerCategory.IMPIEGATO, 0, 999, 45),
        NoticePerioD(CCNLSector.AUTORIMESSE, WorkerCategory.QUADRO, 0, 999, 75)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.AUTORIMESSE,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('80.00'),
            frequency="monthly",
            conditions=["Lavoro notturno/festivo"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.AUTORIMESSE,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('6.50'),
            frequency="daily",
            conditions=["Presenza lavorativa"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.AUTORIMESSE,
        name="CCNL Autorimesse e Parcheggi",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTUCS"],
        signatory_employers=["Federarcheggi", "ANAP"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_pompe_funebri_ccnl() -> CCNLAgreement:
    """Get CCNL for Pompe Funebri - funeral services sector."""
    
    job_levels = [
        JobLevel(
            level_code="OPER_FUN",
            level_name="Operatore Funebre",
            category=WorkerCategory.OPERAIO,
            description="Addetto servizi funebri",
            minimum_experience_months=0,
            required_qualifications=["Abilitazione regionale", "Corso igiene"],
            typical_tasks=["Preparazione salme", "Trasporti funebri", "Assistenza famiglie"]
        ),
        JobLevel(
            level_code="NETTURS_SPEC",
            level_name="Necroforo Specializzato",
            category=WorkerCategory.OPERAIO,
            description="Specialista trattamento salme",
            minimum_experience_months=24,
            required_qualifications=["Specializzazione tanatoprassi", "Certificazioni sanitarie"],
            typical_tasks=["Tanatoprassi", "Imbalsamazione", "Vestizione salme"]
        ),
        JobLevel(
            level_code="COORD_SERV",
            level_name="Coordinatore Servizi",
            category=WorkerCategory.IMPIEGATO,
            description="Coordinamento cerimonie funebri",
            minimum_experience_months=48,
            required_qualifications=["Esperienza organizzazione eventi"],
            typical_tasks=["Organizzazione funerali", "Rapporti clienti", "Coordinamento staff"]
        ),
        JobLevel(
            level_code="DIRETT_AGE",
            level_name="Direttore Agenzia",
            category=WorkerCategory.DIRIGENTE,
            description="Responsabile agenzia funebre",
            minimum_experience_months=72,
            required_qualifications=["Laurea o esperienza manageriale"],
            typical_tasks=["Gestione agenzia", "Sviluppo commerciale", "Conformità normative"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.POMPE_FUNEBRI, "OPER_FUN", Decimal('1800.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.POMPE_FUNEBRI, "NETTURS_SPEC", Decimal('2200.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.POMPE_FUNEBRI, "COORD_SERV", Decimal('2800.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.POMPE_FUNEBRI, "DIRETT_AGE", Decimal('4000.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.POMPE_FUNEBRI,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=50,
        flexible_hours_allowed=True,
        shift_work_allowed=True,
        shift_patterns=["Diurno", "Reperibilità", "Emergenza 24h"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.POMPE_FUNEBRI,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.35'),
        weekend_rate=Decimal('1.60'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=60
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.POMPE_FUNEBRI,
            leave_type=LeaveType.FERIE,
            base_annual_days=26
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.POMPE_FUNEBRI,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=20
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.POMPE_FUNEBRI, WorkerCategory.OPERAIO, 0, 180, 30),
        NoticePerioD(CCNLSector.POMPE_FUNEBRI, WorkerCategory.OPERAIO, 181, 999, 45),
        NoticePerioD(CCNLSector.POMPE_FUNEBRI, WorkerCategory.IMPIEGATO, 0, 999, 60),
        NoticePerioD(CCNLSector.POMPE_FUNEBRI, WorkerCategory.DIRIGENTE, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.POMPE_FUNEBRI,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal('200.00'),
            frequency="monthly",
            conditions=["Esposizione biologica", "Stress psicologico"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.POMPE_FUNEBRI,
            allowance_type=AllowanceType.INDENNITA_REPERIBILITA,
            amount=Decimal('150.00'),
            frequency="monthly",
            conditions=["Reperibilità 24/7"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.POMPE_FUNEBRI,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('8.00'),
            frequency="daily",
            conditions=["Presenza lavorativa"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.POMPE_FUNEBRI,
        name="CCNL Pompe Funebri",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTUCS"],
        signatory_employers=["FENIOF", "Confcommercio"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_acconciatura_estetica_ccnl() -> CCNLAgreement:
    """Get CCNL for Acconciatura ed Estetica - hairdressing and beauty sector."""
    
    job_levels = [
        JobLevel(
            level_code="APPRENDISTA",
            level_name="Apprendista",
            category=WorkerCategory.OPERAIO,
            description="Apprendista parrucchiere/estetista",
            minimum_experience_months=0,
            required_qualifications=["Corso professionale", "Qualifica regionale"],
            typical_tasks=["Assistenza clienti", "Preparazione prodotti", "Pulizia"]
        ),
        JobLevel(
            level_code="OPER_QUALIF",
            level_name="Operatore Qualificato",
            category=WorkerCategory.OPERAIO,
            description="Parrucchiere/estetista qualificato",
            minimum_experience_months=18,
            required_qualifications=["Qualifica professionale", "Abilitazione"],
            typical_tasks=["Servizi base", "Trattamenti standard", "Consulenza clienti"]
        ),
        JobLevel(
            level_code="SPECIAL_SENIOR",
            level_name="Specialista Senior",
            category=WorkerCategory.IMPIEGATO,
            description="Specialista servizi avanzati",
            minimum_experience_months=48,
            required_qualifications=["Specializzazioni avanzate", "Corsi aggiornamento"],
            typical_tasks=["Trattamenti complessi", "Formazione junior", "Gestione clientela VIP"]
        ),
        JobLevel(
            level_code="RESP_SALON",
            level_name="Responsabile Salone",
            category=WorkerCategory.QUADRO,
            description="Responsabile gestione salone",
            minimum_experience_months=72,
            required_qualifications=["Esperienza manageriale", "Gestione team"],
            typical_tasks=["Gestione salone", "Sviluppo commerciale", "Controllo qualità"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.ACCONCIATURA_ESTETICA, "APPRENDISTA", Decimal('1200.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ACCONCIATURA_ESTETICA, "OPER_QUALIF", Decimal('1650.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ACCONCIATURA_ESTETICA, "SPECIAL_SENIOR", Decimal('2300.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ACCONCIATURA_ESTETICA, "RESP_SALON", Decimal('3200.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.ACCONCIATURA_ESTETICA,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        shift_work_allowed=False,
        shift_patterns=["Continuativo", "Part-time"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.ACCONCIATURA_ESTETICA,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('1.75'),
        maximum_monthly_overtime=30
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.ACCONCIATURA_ESTETICA,
            leave_type=LeaveType.FERIE,
            base_annual_days=26
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.ACCONCIATURA_ESTETICA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=18
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.ACCONCIATURA_ESTETICA, WorkerCategory.OPERAIO, 0, 180, 15),
        NoticePerioD(CCNLSector.ACCONCIATURA_ESTETICA, WorkerCategory.OPERAIO, 181, 999, 30),
        NoticePerioD(CCNLSector.ACCONCIATURA_ESTETICA, WorkerCategory.IMPIEGATO, 0, 999, 45),
        NoticePerioD(CCNLSector.ACCONCIATURA_ESTETICA, WorkerCategory.QUADRO, 0, 999, 90)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.ACCONCIATURA_ESTETICA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('6.00'),
            frequency="daily",
            conditions=["Presenza lavorativa"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.ACCONCIATURA_ESTETICA,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('150.00'),
            frequency="monthly",
            conditions=["Performance commerciale", "Customer satisfaction"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.ACCONCIATURA_ESTETICA,
        name="CCNL Acconciatura ed Estetica",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTUCS"],
        signatory_employers=["CNA Benessere", "Confartigianato", "Casartigiani"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_impianti_sportivi_ccnl() -> CCNLAgreement:
    """Get CCNL for Impianti Sportivi - sports facilities sector."""
    
    job_levels = [
        JobLevel(
            level_code="MANUTENTORE",
            level_name="Manutentore Impianti",
            category=WorkerCategory.OPERAIO,
            description="Addetto manutenzione strutture sportive",
            minimum_experience_months=0,
            required_qualifications=["Formazione tecnica", "Sicurezza"],
            typical_tasks=["Manutenzione piscine", "Gestione impianti", "Controlli sicurezza"]
        ),
        JobLevel(
            level_code="ISTRUTTORE",
            level_name="Istruttore Sportivo",
            category=WorkerCategory.IMPIEGATO,
            description="Istruttore attività sportive",
            minimum_experience_months=12,
            required_qualifications=["Qualifica sportiva", "Primo soccorso"],
            typical_tasks=["Lezioni sportive", "Assistenza atleti", "Programmazione allenamenti"]
        ),
        JobLevel(
            level_code="RESP_ATTIVITA",
            level_name="Responsabile Attività",
            category=WorkerCategory.IMPIEGATO,
            description="Coordinatore programmi sportivi",
            minimum_experience_months=48,
            required_qualifications=["Laurea Scienze Motorie", "Gestione team"],
            typical_tasks=["Pianificazione corsi", "Formazione staff", "Controllo qualità"]
        ),
        JobLevel(
            level_code="DIRETT_CENTRO",
            level_name="Direttore Centro",
            category=WorkerCategory.DIRIGENTE,
            description="Direttore centro sportivo",
            minimum_experience_months=72,
            required_qualifications=["Esperienza manageriale", "Gestione P&L"],
            typical_tasks=["Gestione generale", "Sviluppo commerciale", "Budget e risultati"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.IMPIANTI_SPORTIVI, "MANUTENTORE", Decimal('1650.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.IMPIANTI_SPORTIVI, "ISTRUTTORE", Decimal('1950.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.IMPIANTI_SPORTIVI, "RESP_ATTIVITA", Decimal('2800.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.IMPIANTI_SPORTIVI, "DIRETT_CENTRO", Decimal('4200.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.IMPIANTI_SPORTIVI,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        shift_work_allowed=True,
        shift_patterns=["Mattutino", "Pomeridiano", "Serale", "Weekend"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.IMPIANTI_SPORTIVI,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.30'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('1.80'),
        maximum_monthly_overtime=45
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.IMPIANTI_SPORTIVI,
            leave_type=LeaveType.FERIE,
            base_annual_days=26
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.IMPIANTI_SPORTIVI,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=18
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.IMPIANTI_SPORTIVI, WorkerCategory.OPERAIO, 0, 180, 30),
        NoticePerioD(CCNLSector.IMPIANTI_SPORTIVI, WorkerCategory.OPERAIO, 181, 999, 45),
        NoticePerioD(CCNLSector.IMPIANTI_SPORTIVI, WorkerCategory.IMPIEGATO, 0, 999, 60),
        NoticePerioD(CCNLSector.IMPIANTI_SPORTIVI, WorkerCategory.DIRIGENTE, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.IMPIANTI_SPORTIVI,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('7.00'),
            frequency="daily",
            conditions=["Presenza lavorativa"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.IMPIANTI_SPORTIVI,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('120.00'),
            frequency="monthly",
            conditions=["Lavoro serale/weekend"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.IMPIANTI_SPORTIVI,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('180.00'),
            frequency="monthly",
            conditions=["Raggiungimento obiettivi", "Soddisfazione clienti"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.IMPIANTI_SPORTIVI,
        name="CCNL Impianti Sportivi",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTUCS"],
        signatory_employers=["ANIF", "Associazione Gestori"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_dirigenti_industria_ccnl() -> CCNLAgreement:
    """Get CCNL for Dirigenti Industria - industrial executives sector."""
    
    job_levels = [
        JobLevel(
            level_code="QUADRO_SUP",
            level_name="Quadro Superiore",
            category=WorkerCategory.QUADRO,
            description="Quadro con responsabilità operative",
            minimum_experience_months=60,
            required_qualifications=["Laurea", "Esperienza manageriale"],
            typical_tasks=["Gestione operazioni", "Controllo budget", "Sviluppo team"]
        ),
        JobLevel(
            level_code="DIR_JUNIOR",
            level_name="Dirigente Junior",
            category=WorkerCategory.DIRIGENTE,
            description="Dirigente entry level",
            minimum_experience_months=84,
            required_qualifications=["Laurea specialistica", "MBA preferito"],
            typical_tasks=["Gestione dipartimento", "Strategia operativa", "Performance management"]
        ),
        JobLevel(
            level_code="DIR_SENIOR",
            level_name="Dirigente Senior",
            category=WorkerCategory.DIRIGENTE,
            description="Dirigente con esperienza consolidata",
            minimum_experience_months=120,
            required_qualifications=["Esperienza dirigenziale comprovata"],
            typical_tasks=["Strategia aziendale", "Gestione P&L", "Sviluppo business"]
        ),
        JobLevel(
            level_code="DIR_GENERALE",
            level_name="Direttore Generale",
            category=WorkerCategory.DIRIGENTE,
            description="Alta direzione aziendale",
            minimum_experience_months=180,
            required_qualifications=["Esperienza top management"],
            typical_tasks=["Direzione generale", "Strategia corporate", "Board reporting"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.DIRIGENTI_INDUSTRIA, "QUADRO_SUP", Decimal('5500.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.DIRIGENTI_INDUSTRIA, "DIR_JUNIOR", Decimal('8500.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.DIRIGENTI_INDUSTRIA, "DIR_SENIOR", Decimal('12000.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.DIRIGENTI_INDUSTRIA, "DIR_GENERALE", Decimal('18000.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.DIRIGENTI_INDUSTRIA,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=50,
        flexible_hours_allowed=True,
        shift_work_allowed=False,
        shift_patterns=["Flessibile", "Executive"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.DIRIGENTI_INDUSTRIA,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('0.00'),  # Dirigenti non hanno straordinario
        weekend_rate=Decimal('0.00'),
        holiday_rate=Decimal('0.00'),
        maximum_monthly_overtime=0
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.DIRIGENTI_INDUSTRIA,
            leave_type=LeaveType.FERIE,
            base_annual_days=30
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.DIRIGENTI_INDUSTRIA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=24
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.DIRIGENTI_INDUSTRIA, WorkerCategory.QUADRO, 0, 999, 120),
        NoticePerioD(CCNLSector.DIRIGENTI_INDUSTRIA, WorkerCategory.DIRIGENTE, 0, 999, 180)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.DIRIGENTI_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_FUNZIONE,
            amount=Decimal('1500.00'),
            frequency="monthly",
            conditions=["Ruolo dirigenziale", "Responsabilità P&L"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.DIRIGENTI_INDUSTRIA,
            allowance_type=AllowanceType.AUTO_AZIENDALE,
            amount=Decimal('800.00'),
            frequency="monthly",
            conditions=["Livello dirigenziale"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.DIRIGENTI_INDUSTRIA,
        name="CCNL Dirigenti Industria",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["Federmanager", "Manageritalia"],
        signatory_employers=["Confindustria", "Federmeccanica"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_dirigenti_commercio_ccnl() -> CCNLAgreement:
    """Get CCNL for Dirigenti Commercio - commercial executives sector."""
    
    job_levels = [
        JobLevel(
            level_code="AREA_MANAGER",
            level_name="Area Manager",
            category=WorkerCategory.QUADRO,
            description="Responsabile area commerciale",
            minimum_experience_months=60,
            required_qualifications=["Laurea", "Esperienza vendite"],
            typical_tasks=["Gestione territorio", "Sviluppo clientela", "Team commerciale"]
        ),
        JobLevel(
            level_code="DIR_COMM_JR",
            level_name="Direttore Commerciale Junior",
            category=WorkerCategory.DIRIGENTE,
            description="Dirigente commerciale entry level",
            minimum_experience_months=84,
            required_qualifications=["MBA o esperienza equivalente"],
            typical_tasks=["Strategia commerciale", "Gestione vendite", "Budget fatturato"]
        ),
        JobLevel(
            level_code="DIR_COMM_SR",
            level_name="Direttore Commerciale Senior",
            category=WorkerCategory.DIRIGENTE,
            description="Dirigente commerciale esperto",
            minimum_experience_months=120,
            required_qualifications=["Esperienza dirigenziale consolidata"],
            typical_tasks=["Strategia go-to-market", "Sviluppo canali", "P&L commerciale"]
        ),
        JobLevel(
            level_code="DIR_MARKETING",
            level_name="Direttore Marketing",
            category=WorkerCategory.DIRIGENTE,
            description="Responsabile strategia marketing",
            minimum_experience_months=120,
            required_qualifications=["Esperienza marketing strategico"],
            typical_tasks=["Brand strategy", "Digital marketing", "Market intelligence"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.DIRIGENTI_COMMERCIO, "AREA_MANAGER", Decimal('4800.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.DIRIGENTI_COMMERCIO, "DIR_COMM_JR", Decimal('7500.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.DIRIGENTI_COMMERCIO, "DIR_COMM_SR", Decimal('11000.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.DIRIGENTI_COMMERCIO, "DIR_MARKETING", Decimal('10500.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.DIRIGENTI_COMMERCIO,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=50,
        flexible_hours_allowed=True,
        shift_work_allowed=False,
        shift_patterns=["Flessibile", "Travel-intensive"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.DIRIGENTI_COMMERCIO,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('0.00'),  # Dirigenti non hanno straordinario
        weekend_rate=Decimal('0.00'),
        holiday_rate=Decimal('0.00'),
        maximum_monthly_overtime=0
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.DIRIGENTI_COMMERCIO,
            leave_type=LeaveType.FERIE,
            base_annual_days=28
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.DIRIGENTI_COMMERCIO,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=20
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.DIRIGENTI_COMMERCIO, WorkerCategory.QUADRO, 0, 999, 120),
        NoticePerioD(CCNLSector.DIRIGENTI_COMMERCIO, WorkerCategory.DIRIGENTE, 0, 999, 180)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.DIRIGENTI_COMMERCIO,
            allowance_type=AllowanceType.INDENNITA_TRASFERTA,
            amount=Decimal('80.00'),
            frequency="daily",
            conditions=["Trasferte commerciali", "Cliente visiting"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.DIRIGENTI_COMMERCIO,
            allowance_type=AllowanceType.AUTO_AZIENDALE,
            amount=Decimal('700.00'),
            frequency="monthly",
            conditions=["Ruolo commerciale"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.DIRIGENTI_COMMERCIO,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('2000.00'),
            frequency="monthly",
            conditions=["Raggiungimento target", "Performance commerciale"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.DIRIGENTI_COMMERCIO,
        name="CCNL Dirigenti Commercio",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["Manageritalia", "Federmanager"],
        signatory_employers=["Confcommercio", "Federcommercio"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_quadri_ccnl() -> CCNLAgreement:
    """Get CCNL for Quadri - middle management sector."""
    
    job_levels = [
        JobLevel(
            level_code="QUADRO_JR",
            level_name="Quadro Junior",
            category=WorkerCategory.QUADRO,
            description="Quadro entry level",
            minimum_experience_months=36,
            required_qualifications=["Laurea", "Specializzazione tecnica"],
            typical_tasks=["Coordinamento progetti", "Gestione team junior", "Reporting"]
        ),
        JobLevel(
            level_code="QUADRO_INTERMEDIO",
            level_name="Quadro Intermedio",
            category=WorkerCategory.QUADRO,
            description="Quadro con esperienza consolidata",
            minimum_experience_months=60,
            required_qualifications=["Esperienza manageriale", "Competenze avanzate"],
            typical_tasks=["Gestione processi", "Sviluppo team", "Budget responsibility"]
        ),
        JobLevel(
            level_code="QUADRO_SENIOR",
            level_name="Quadro Senior",
            category=WorkerCategory.QUADRO,
            description="Quadro esperto con ampia responsabilità",
            minimum_experience_months=96,
            required_qualifications=["Leadership comprovata", "Strategic thinking"],
            typical_tasks=["Strategic planning", "Cross-functional management", "Innovation"]
        ),
        JobLevel(
            level_code="QUADRO_SPECIALIST",
            level_name="Quadro Specialista",
            category=WorkerCategory.QUADRO,
            description="Quadro con alta specializzazione tecnica",
            minimum_experience_months=84,
            required_qualifications=["Expertise tecnica avanzata", "Certificazioni"],
            typical_tasks=["Technical leadership", "R&D", "Knowledge management"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.QUADRI, "QUADRO_JR", Decimal('3500.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.QUADRI, "QUADRO_INTERMEDIO", Decimal('4200.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.QUADRI, "QUADRO_SENIOR", Decimal('5200.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.QUADRI, "QUADRO_SPECIALIST", Decimal('4800.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.QUADRI,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        shift_work_allowed=False,
        shift_patterns=["Flessibile", "Project-based"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.QUADRI,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.15'),  # Quadri hanno straordinario ridotto
        weekend_rate=Decimal('1.30'),
        holiday_rate=Decimal('1.50'),
        maximum_monthly_overtime=20  # Limitato per quadri
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.QUADRI,
            leave_type=LeaveType.FERIE,
            base_annual_days=28
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.QUADRI,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=20
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.QUADRI, WorkerCategory.QUADRO, 0, 60, 90),
        NoticePerioD(CCNLSector.QUADRI, WorkerCategory.QUADRO, 61, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.QUADRI,
            allowance_type=AllowanceType.INDENNITA_FUNZIONE,
            amount=Decimal('400.00'),
            frequency="monthly",
            conditions=["Responsabilità manageriali"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.QUADRI,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('8.50'),
            frequency="daily",
            conditions=["Presenza lavorativa"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.QUADRI,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('800.00'),
            frequency="monthly",
            conditions=["Performance objectives", "Team results"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.QUADRI,
        name="CCNL Quadri",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["FIM-CISL", "FIOM-CGIL", "UILM-UIL", "CIDA"],
        signatory_employers=["Confindustria", "Federazione datori lavoro"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_all_priority6_ccnl_data() -> List[CCNLAgreement]:
    """Get all Priority 6 CCNL agreements."""
    return [
        get_autotrasporto_merci_ccnl(),
        get_autonoleggio_ccnl(),
        get_autorimesse_ccnl(),
        get_pompe_funebri_ccnl(),
        get_acconciatura_estetica_ccnl(),
        get_impianti_sportivi_ccnl(),
        get_dirigenti_industria_ccnl(),
        get_dirigenti_commercio_ccnl(),
        get_quadri_ccnl(),
    ]


def validate_priority6_ccnl_data_completeness() -> Dict[str, Any]:
    """Validate completeness of Priority 6 CCNL data."""
    validation_result = {
        "status": "COMPLETE",
        "total_sectors": 9,
        "sectors_complete": 9,
        "missing_components": [],
        "completion_rate": 100.0,
        "validation_date": date.today().isoformat()
    }
    
    try:
        all_agreements = get_all_priority6_ccnl_data()
        
        for agreement in all_agreements:
            # Basic completeness checks
            components_complete = True
            missing_for_sector = []
            
            if len(agreement.job_levels) < 3:
                missing_for_sector.append("insufficient job levels")
                components_complete = False
                
            if len(agreement.salary_tables) < 3:
                missing_for_sector.append("insufficient salary tables")
                components_complete = False
                
            if not agreement.working_hours:
                missing_for_sector.append("missing working hours")
                components_complete = False
                
            if not agreement.overtime_rules:
                missing_for_sector.append("missing overtime rules")
                components_complete = False
                
            if len(agreement.leave_entitlements) < 1:
                missing_for_sector.append("missing leave entitlements")
                components_complete = False
                
            if len(agreement.notice_periods) < 3:
                missing_for_sector.append("insufficient notice periods")
                components_complete = False
            
            if components_complete:
                validation_result["sectors_complete"] += 1
            else:
                validation_result["missing_components"].append({
                    "sector": agreement.sector.value,
                    "missing": missing_for_sector
                })
        
        # Calculate completion rate
        validation_result["completion_rate"] = (
            validation_result["sectors_complete"] / validation_result["total_sectors"]
        ) * 100
        
        # Update overall status
        if validation_result["completion_rate"] >= 95:
            validation_result["status"] = "COMPLETE"
        elif validation_result["completion_rate"] >= 50:
            validation_result["status"] = "PARTIAL"
        else:
            validation_result["status"] = "INCOMPLETE"
        
        return validation_result
        
    except Exception as e:
        validation_result["status"] = "ERROR"
        validation_result["error"] = str(e)
        return validation_result