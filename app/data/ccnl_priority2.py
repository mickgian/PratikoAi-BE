"""
Priority 2 CCNL Data for Italian Collective Labor Agreements.

This module contains the actual data for the 10 Priority 2 Service & Professional CCNL sectors,
representing approximately 25% of Italian workers. Data is based on the most
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


def get_telecomunicazioni_ccnl() -> CCNLAgreement:
    """Get CCNL for Telecomunicazioni - telecommunications sector."""
    
    job_levels = [
        # Impiegati levels
        JobLevel(
            level_code="4A",
            level_name="Impiegato di Concetto",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=0,
            typical_tasks=["Customer service", "Data entry", "Supporto tecnico base"]
        ),
        JobLevel(
            level_code="5A",
            level_name="Impiegato Specializzato",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=24,
            typical_tasks=["Network administration", "System support", "Technical analysis"]
        ),
        JobLevel(
            level_code="6A",
            level_name="Impiegato Coordinatore",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=60,
            typical_tasks=["Team coordination", "Project management", "Technical leadership"]
        ),
        # Quadri level
        JobLevel(
            level_code="7A",
            level_name="Quadro Tecnico",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=84,
            typical_tasks=["Strategic planning", "Department management", "Innovation projects"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.TELECOMUNICAZIONI, "4A", Decimal('1680.00'), 
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.TELECOMUNICAZIONI, "5A", Decimal('2145.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.TELECOMUNICAZIONI, "6A", Decimal('2680.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.TELECOMUNICAZIONI, "7A", Decimal('3250.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.TELECOMUNICAZIONI,
        ordinary_weekly_hours=38,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        shift_work_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.TELECOMUNICAZIONI,
        daily_threshold_hours=7.6,
        weekly_threshold_hours=38,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=20
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.TELECOMUNICAZIONI,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.TELECOMUNICAZIONI,
            leave_type=LeaveType.FERIE,
            base_annual_days=28,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.TELECOMUNICAZIONI, WorkerCategory.IMPIEGATO, 0, 36, 30),
        NoticePerioD(CCNLSector.TELECOMUNICAZIONI, WorkerCategory.IMPIEGATO, 36, 120, 45),
        NoticePerioD(CCNLSector.TELECOMUNICAZIONI, WorkerCategory.IMPIEGATO, 120, 999, 60),
        NoticePerioD(CCNLSector.TELECOMUNICAZIONI, WorkerCategory.QUADRO, 0, 999, 90)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.TELECOMUNICAZIONI,
            allowance_type=AllowanceType.INDENNITA_FUNZIONE,
            amount=Decimal('150.00'),
            frequency="monthly"
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.TELECOMUNICAZIONI,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('200.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.TELECOMUNICAZIONI,
        name="CCNL Telecomunicazioni",
        valid_from=date(2022, 1, 1),
        valid_to=date(2024, 12, 31),
        signatory_unions=["SLC-CGIL", "FISTEL-CISL", "UILCOM-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_credito_assicurazioni_ccnl() -> CCNLAgreement:
    """Get CCNL for Credito e Assicurazioni - banking and insurance sector."""
    
    job_levels = [
        JobLevel(
            level_code="1A",
            level_name="Impiegato di Prima Classe",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=0,
            typical_tasks=["Cassa", "Sportello clienti", "Back office semplice"]
        ),
        JobLevel(
            level_code="2A",
            level_name="Impiegato di Seconda Classe",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=24,
            typical_tasks=["Consulenza finanziaria", "Analisi rischio", "Gestione portafoglio"]
        ),
        JobLevel(
            level_code="3A",
            level_name="Impiegato Direttivo",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=60,
            typical_tasks=["Gestione filiale", "Supervisione team", "Sviluppo commerciale"]
        ),
        JobLevel(
            level_code="4A",
            level_name="Quadro Direttivo",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=96,
            typical_tasks=["Strategic planning", "Risk management", "Regional coordination"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.CREDITO_ASSICURAZIONI, "1A", Decimal('1890.00'),
                   GeographicArea.NORD, CompanySize.LARGE, date(2024, 1, 1)),
        SalaryTable(CCNLSector.CREDITO_ASSICURAZIONI, "2A", Decimal('2450.00'),
                   GeographicArea.NORD, CompanySize.LARGE, date(2024, 1, 1)),
        SalaryTable(CCNLSector.CREDITO_ASSICURAZIONI, "3A", Decimal('3180.00'),
                   GeographicArea.NORD, CompanySize.LARGE, date(2024, 1, 1)),
        SalaryTable(CCNLSector.CREDITO_ASSICURAZIONI, "4A", Decimal('4250.00'),
                   GeographicArea.NORD, CompanySize.LARGE, date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.CREDITO_ASSICURAZIONI,
        ordinary_weekly_hours=37,
        flexible_hours_allowed=True,
        shift_work_allowed=False
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.CREDITO_ASSICURAZIONI,
        daily_threshold_hours=7.4,
        weekly_threshold_hours=37,
        daily_overtime_rate=Decimal('1.30'),
        weekend_rate=Decimal('1.60'),
        holiday_rate=Decimal('2.20'),
        maximum_monthly_overtime=15
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.CREDITO_ASSICURAZIONI,
            leave_type=LeaveType.FERIE,
            base_annual_days=30,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.CREDITO_ASSICURAZIONI,
            leave_type=LeaveType.FERIE,
            base_annual_days=32,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.CREDITO_ASSICURAZIONI, WorkerCategory.IMPIEGATO, 0, 60, 45),
        NoticePerioD(CCNLSector.CREDITO_ASSICURAZIONI, WorkerCategory.IMPIEGATO, 60, 120, 75),
        NoticePerioD(CCNLSector.CREDITO_ASSICURAZIONI, WorkerCategory.IMPIEGATO, 120, 999, 90),
        NoticePerioD(CCNLSector.CREDITO_ASSICURAZIONI, WorkerCategory.QUADRO, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.CREDITO_ASSICURAZIONI,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal('120.00'),
            frequency="monthly"
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.CREDITO_ASSICURAZIONI,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('300.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.CREDITO_ASSICURAZIONI,
        name="CCNL Credito e Assicurazioni",
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
        signatory_unions=["FIRST-CISL", "FISAC-CGIL", "UILCA-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_studi_professionali_ccnl() -> CCNLAgreement:
    """Get CCNL for Studi Professionali - professional offices sector."""
    
    job_levels = [
        JobLevel(
            level_code="I",
            level_name="Impiegato di Segreteria",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=0,
            typical_tasks=["Segreteria", "Archivio", "Accoglienza clienti"]
        ),
        JobLevel(
            level_code="II",
            level_name="Contabile",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=12,
            typical_tasks=["Contabilità ordinaria", "Fatturazione", "Dichiarazioni fiscali"]
        ),
        JobLevel(
            level_code="III",
            level_name="Contabile Specializzato",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=36,
            typical_tasks=["Bilanci", "Consulenza fiscale", "Controllo di gestione"]
        ),
        JobLevel(
            level_code="IV",
            level_name="Collaboratore Professionale",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=60,
            typical_tasks=["Consulenza specialistica", "Gestione clienti", "Formazione junior"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.STUDI_PROFESSIONALI, "I", Decimal('1350.00'),
                   GeographicArea.NORD, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.STUDI_PROFESSIONALI, "II", Decimal('1580.00'),
                   GeographicArea.NORD, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.STUDI_PROFESSIONALI, "III", Decimal('1980.00'),
                   GeographicArea.NORD, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.STUDI_PROFESSIONALI, "IV", Decimal('2680.00'),
                   GeographicArea.NORD, CompanySize.SMALL, date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.STUDI_PROFESSIONALI,
        ordinary_weekly_hours=40,
        flexible_hours_allowed=True,
        shift_work_allowed=False
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.STUDI_PROFESSIONALI,
        daily_threshold_hours=8.0,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.15'),
        weekend_rate=Decimal('1.30'),
        holiday_rate=Decimal('1.50'),
        maximum_monthly_overtime=25
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.STUDI_PROFESSIONALI,
            leave_type=LeaveType.FERIE,
            base_annual_days=22,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.STUDI_PROFESSIONALI,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.STUDI_PROFESSIONALI, WorkerCategory.IMPIEGATO, 0, 24, 15),
        NoticePerioD(CCNLSector.STUDI_PROFESSIONALI, WorkerCategory.IMPIEGATO, 24, 60, 30),
        NoticePerioD(CCNLSector.STUDI_PROFESSIONALI, WorkerCategory.IMPIEGATO, 60, 999, 45),
        NoticePerioD(CCNLSector.STUDI_PROFESSIONALI, WorkerCategory.QUADRO, 0, 999, 60)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.STUDI_PROFESSIONALI,
            allowance_type=AllowanceType.INDENNITA_FUNZIONE,
            amount=Decimal('100.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.STUDI_PROFESSIONALI,
        name="CCNL Studi Professionali",
        valid_from=date(2022, 7, 1),
        valid_to=date(2025, 6, 30),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTuCS-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_servizi_pulizia_ccnl() -> CCNLAgreement:
    """Get CCNL for Servizi di Pulizia e Multiservizi."""
    
    job_levels = [
        JobLevel(
            level_code="1°",
            level_name="Ausiliario",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=0,
            typical_tasks=["Pulizie ordinarie", "Spazzamento", "Svuotamento cestini"]
        ),
        JobLevel(
            level_code="2°",
            level_name="Operatore Qualificato",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=6,
            typical_tasks=["Pulizie specializzate", "Sanificazione", "Manutenzione verde"]
        ),
        JobLevel(
            level_code="3°",
            level_name="Operatore Specializzato",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=18,
            typical_tasks=["Pulizie tecniche", "Formazione colleghi", "Controllo qualità"]
        ),
        JobLevel(
            level_code="4°",
            level_name="Caposquadra",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=36,
            typical_tasks=["Coordinamento squadre", "Pianificazione lavori", "Rapporti clienti"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.SERVIZI_PULIZIA, "1°", Decimal('1180.00'),
                   GeographicArea.CENTRO, CompanySize.MEDIUM, date(2024, 1, 1)),
        SalaryTable(CCNLSector.SERVIZI_PULIZIA, "2°", Decimal('1245.00'),
                   GeographicArea.CENTRO, CompanySize.MEDIUM, date(2024, 1, 1)),
        SalaryTable(CCNLSector.SERVIZI_PULIZIA, "3°", Decimal('1380.00'),
                   GeographicArea.CENTRO, CompanySize.MEDIUM, date(2024, 1, 1)),
        SalaryTable(CCNLSector.SERVIZI_PULIZIA, "4°", Decimal('1680.00'),
                   GeographicArea.CENTRO, CompanySize.MEDIUM, date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.SERVIZI_PULIZIA,
        ordinary_weekly_hours=40,
        flexible_hours_allowed=False,
        shift_work_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.SERVIZI_PULIZIA,
        daily_threshold_hours=8.0,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.20'),
        weekend_rate=Decimal('1.40'),
        holiday_rate=Decimal('1.75'),
        maximum_monthly_overtime=30
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.SERVIZI_PULIZIA,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.SERVIZI_PULIZIA,
            leave_type=LeaveType.FERIE,
            base_annual_days=28,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.SERVIZI_PULIZIA, WorkerCategory.OPERAIO, 0, 24, 8),
        NoticePerioD(CCNLSector.SERVIZI_PULIZIA, WorkerCategory.OPERAIO, 24, 60, 15),
        NoticePerioD(CCNLSector.SERVIZI_PULIZIA, WorkerCategory.OPERAIO, 60, 999, 30),
        NoticePerioD(CCNLSector.SERVIZI_PULIZIA, WorkerCategory.IMPIEGATO, 0, 999, 45)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.SERVIZI_PULIZIA,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal('80.00'),
            frequency="monthly"
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.SERVIZI_PULIZIA,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('120.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.SERVIZI_PULIZIA,
        name="CCNL Servizi di Pulizia e Multiservizi",
        valid_from=date(2023, 4, 1),
        valid_to=date(2026, 3, 31),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTuCS-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_vigilanza_privata_ccnl() -> CCNLAgreement:
    """Get CCNL for Vigilanza Privata - private security sector."""
    
    job_levels = [
        JobLevel(
            level_code="1°",
            level_name="Guardia Particolare Giurata",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=0,
            typical_tasks=["Controllo accessi", "Ronde di sorveglianza", "Monitoraggio TVCC"]
        ),
        JobLevel(
            level_code="2°",
            level_name="Guardia Specializzata",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=12,
            typical_tasks=["Sistemi antintrusione", "Controllo tecnologico", "Interventi specialistici"]
        ),
        JobLevel(
            level_code="3°",
            level_name="Caposervizio",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=36,
            typical_tasks=["Coordinamento servizi", "Pianificazione turni", "Formazione personale"]
        ),
        JobLevel(
            level_code="4°",
            level_name="Coordinatore",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=60,
            typical_tasks=["Gestione contratti", "Sviluppo commerciale", "Controllo qualità"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.VIGILANZA_PRIVATA, "1°", Decimal('1280.00'),
                   GeographicArea.CENTRO, CompanySize.MEDIUM, date(2024, 1, 1)),
        SalaryTable(CCNLSector.VIGILANZA_PRIVATA, "2°", Decimal('1420.00'),
                   GeographicArea.CENTRO, CompanySize.MEDIUM, date(2024, 1, 1)),
        SalaryTable(CCNLSector.VIGILANZA_PRIVATA, "3°", Decimal('1780.00'),
                   GeographicArea.CENTRO, CompanySize.MEDIUM, date(2024, 1, 1)),
        SalaryTable(CCNLSector.VIGILANZA_PRIVATA, "4°", Decimal('2380.00'),
                   GeographicArea.CENTRO, CompanySize.MEDIUM, date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.VIGILANZA_PRIVATA,
        ordinary_weekly_hours=40,
        flexible_hours_allowed=False,
        shift_work_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.VIGILANZA_PRIVATA,
        daily_threshold_hours=8.0,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=40
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.VIGILANZA_PRIVATA,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.VIGILANZA_PRIVATA,
            leave_type=LeaveType.FERIE,
            base_annual_days=28,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.VIGILANZA_PRIVATA, WorkerCategory.OPERAIO, 0, 36, 15),
        NoticePerioD(CCNLSector.VIGILANZA_PRIVATA, WorkerCategory.OPERAIO, 36, 120, 30),
        NoticePerioD(CCNLSector.VIGILANZA_PRIVATA, WorkerCategory.OPERAIO, 120, 999, 45),
        NoticePerioD(CCNLSector.VIGILANZA_PRIVATA, WorkerCategory.IMPIEGATO, 0, 999, 60)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.VIGILANZA_PRIVATA,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal('180.00'),
            frequency="monthly"
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.VIGILANZA_PRIVATA,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('220.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.VIGILANZA_PRIVATA,
        name="CCNL Vigilanza Privata",
        valid_from=date(2022, 10, 1),
        valid_to=date(2025, 9, 30),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTuCS-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_ict_ccnl() -> CCNLAgreement:
    """Get CCNL for ICT - Information Technology sector."""
    
    job_levels = [
        JobLevel(
            level_code="1°",
            level_name="Programmatore Junior",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=0,
            typical_tasks=["Sviluppo software base", "Testing", "Documentazione"]
        ),
        JobLevel(
            level_code="2°",
            level_name="Analista Programmatore",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=24,
            typical_tasks=["Analisi requisiti", "Sviluppo applicazioni", "Database design"]
        ),
        JobLevel(
            level_code="3°",
            level_name="System Administrator",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=36,
            typical_tasks=["Gestione infrastrutture", "Security", "Network management"]
        ),
        JobLevel(
            level_code="4°",
            level_name="Project Manager",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=60,
            typical_tasks=["Project management", "Team leadership", "Client relationship"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.ICT, "1°", Decimal('1980.00'),
                   GeographicArea.NORD, CompanySize.LARGE, date(2024, 1, 1)),
        SalaryTable(CCNLSector.ICT, "2°", Decimal('2680.00'),
                   GeographicArea.NORD, CompanySize.LARGE, date(2024, 1, 1)),
        SalaryTable(CCNLSector.ICT, "3°", Decimal('3280.00'),
                   GeographicArea.NORD, CompanySize.LARGE, date(2024, 1, 1)),
        SalaryTable(CCNLSector.ICT, "4°", Decimal('4180.00'),
                   GeographicArea.NORD, CompanySize.LARGE, date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.ICT,
        ordinary_weekly_hours=38,
        flexible_hours_allowed=True,
        shift_work_allowed=False
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.ICT,
        daily_threshold_hours=7.6,
        weekly_threshold_hours=38,
        daily_overtime_rate=Decimal('1.30'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=20
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.ICT,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.ICT,
            leave_type=LeaveType.FERIE,
            base_annual_days=30,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.ICT, WorkerCategory.IMPIEGATO, 0, 36, 30),
        NoticePerioD(CCNLSector.ICT, WorkerCategory.IMPIEGATO, 36, 120, 60),
        NoticePerioD(CCNLSector.ICT, WorkerCategory.IMPIEGATO, 120, 999, 90),
        NoticePerioD(CCNLSector.ICT, WorkerCategory.QUADRO, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.ICT,
            allowance_type=AllowanceType.INDENNITA_FUNZIONE,
            amount=Decimal('250.00'),
            frequency="monthly"
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.ICT,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('300.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.ICT,
        name="CCNL Settore ICT",
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
        signatory_unions=["SLC-CGIL", "FISTEL-CISL", "UILCOM-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_agenzie_viaggio_ccnl() -> CCNLAgreement:
    """Get CCNL for Agenzie di Viaggio - travel agencies sector."""
    
    job_levels = [
        JobLevel(
            level_code="1°",
            level_name="Impiegato di Agenzia",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=0,
            typical_tasks=["Accoglienza clienti", "Prenotazioni semplici", "Data entry"]
        ),
        JobLevel(
            level_code="2°",
            level_name="Consulente di Viaggio",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=12,
            typical_tasks=["Consulenza viaggi", "Itinerari personalizzati", "Gestione gruppi"]
        ),
        JobLevel(
            level_code="3°",
            level_name="Responsabile Agenzia",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=36,
            typical_tasks=["Gestione agenzia", "Sviluppo commerciale", "Supervisione staff"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.AGENZIE_VIAGGIO, "1°", Decimal('1380.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.AGENZIE_VIAGGIO, "2°", Decimal('1680.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.AGENZIE_VIAGGIO, "3°", Decimal('2180.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.AGENZIE_VIAGGIO,
        ordinary_weekly_hours=40,
        flexible_hours_allowed=True,
        shift_work_allowed=False
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.AGENZIE_VIAGGIO,
        daily_threshold_hours=8.0,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.20'),
        weekend_rate=Decimal('1.40'),
        holiday_rate=Decimal('1.60'),
        maximum_monthly_overtime=20
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AGENZIE_VIAGGIO,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.AGENZIE_VIAGGIO,
            leave_type=LeaveType.FERIE,
            base_annual_days=30,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.AGENZIE_VIAGGIO, WorkerCategory.IMPIEGATO, 0, 24, 15),
        NoticePerioD(CCNLSector.AGENZIE_VIAGGIO, WorkerCategory.IMPIEGATO, 24, 60, 30),
        NoticePerioD(CCNLSector.AGENZIE_VIAGGIO, WorkerCategory.IMPIEGATO, 60, 999, 45),
        NoticePerioD(CCNLSector.AGENZIE_VIAGGIO, WorkerCategory.QUADRO, 0, 999, 60)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.AGENZIE_VIAGGIO,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('150.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.AGENZIE_VIAGGIO,
        name="CCNL Agenzie di Viaggio",
        valid_from=date(2022, 1, 1),
        valid_to=date(2024, 12, 31),
        signatory_unions=["FILCAMS-CGIL", "FISASCAT-CISL", "UILTuCS-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_call_center_ccnl() -> CCNLAgreement:
    """Get CCNL for Call Center - call center services sector."""
    
    job_levels = [
        JobLevel(
            level_code="1°",
            level_name="Operatore Telefonico",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=0,
            typical_tasks=["Inbound calls", "Customer service", "Data entry"]
        ),
        JobLevel(
            level_code="2°",
            level_name="Operatore Specializzato",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=12,
            typical_tasks=["Outbound calls", "Vendita telefonica", "Problem solving"]
        ),
        JobLevel(
            level_code="3°",
            level_name="Team Leader",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=24,
            typical_tasks=["Supervisione team", "Coaching", "Quality control"]
        ),
        JobLevel(
            level_code="4°",
            level_name="Supervisore",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=48,
            typical_tasks=["Gestione operazioni", "KPI monitoring", "Staff development"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.CALL_CENTER, "1°", Decimal('1250.00'),
                   GeographicArea.SUD, CompanySize.LARGE, date(2024, 1, 1)),
        SalaryTable(CCNLSector.CALL_CENTER, "2°", Decimal('1380.00'),
                   GeographicArea.SUD, CompanySize.LARGE, date(2024, 1, 1)),
        SalaryTable(CCNLSector.CALL_CENTER, "3°", Decimal('1580.00'),
                   GeographicArea.SUD, CompanySize.LARGE, date(2024, 1, 1)),
        SalaryTable(CCNLSector.CALL_CENTER, "4°", Decimal('1980.00'),
                   GeographicArea.SUD, CompanySize.LARGE, date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.CALL_CENTER,
        ordinary_weekly_hours=39,
        flexible_hours_allowed=True,
        shift_work_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.CALL_CENTER,
        daily_threshold_hours=7.8,
        weekly_threshold_hours=39,
        daily_overtime_rate=Decimal('1.20'),
        weekend_rate=Decimal('1.40'),
        holiday_rate=Decimal('1.75'),
        maximum_monthly_overtime=25
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.CALL_CENTER,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.CALL_CENTER,
            leave_type=LeaveType.FERIE,
            base_annual_days=28,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.CALL_CENTER, WorkerCategory.IMPIEGATO, 0, 24, 15),
        NoticePerioD(CCNLSector.CALL_CENTER, WorkerCategory.IMPIEGATO, 24, 60, 30),
        NoticePerioD(CCNLSector.CALL_CENTER, WorkerCategory.IMPIEGATO, 60, 999, 45),
        NoticePerioD(CCNLSector.CALL_CENTER, WorkerCategory.QUADRO, 0, 999, 60)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.CALL_CENTER,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('120.00'),
            frequency="monthly"
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.CALL_CENTER,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('100.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.CALL_CENTER,
        name="CCNL Call Center",
        valid_from=date(2023, 1, 1),
        valid_to=date(2025, 12, 31),
        signatory_unions=["SLC-CGIL", "FISTEL-CISL", "UILCOM-UIL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_cooperative_sociali_ccnl() -> CCNLAgreement:
    """Get CCNL for Cooperative Sociali - social cooperatives sector."""
    
    job_levels = [
        JobLevel(
            level_code="A1",
            level_name="Operatore Socio Assistenziale",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=0,
            typical_tasks=["Assistenza diretta", "Accompagnamento", "Attività ricreative"]
        ),
        JobLevel(
            level_code="B1",
            level_name="Educatore Professionale",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=0,
            typical_tasks=["Progettazione educativa", "Interventi specialistici", "Coordinamento attività"]
        ),
        JobLevel(
            level_code="C1",
            level_name="Coordinatore",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=36,
            typical_tasks=["Coordinamento servizi", "Gestione équipe", "Rapporti istituzionali"]
        ),
        JobLevel(
            level_code="D1",
            level_name="Responsabile di Servizio",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=60,
            typical_tasks=["Direzione servizi", "Programmazione", "Budget management"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.COOPERATIVE_SOCIALI, "A1", Decimal('1280.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.COOPERATIVE_SOCIALI, "B1", Decimal('1580.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.COOPERATIVE_SOCIALI, "C1", Decimal('1980.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.COOPERATIVE_SOCIALI, "D1", Decimal('2480.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.COOPERATIVE_SOCIALI,
        ordinary_weekly_hours=38,
        flexible_hours_allowed=True,
        shift_work_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.COOPERATIVE_SOCIALI,
        daily_threshold_hours=7.6,
        weekly_threshold_hours=38,
        daily_overtime_rate=Decimal('1.20'),
        weekend_rate=Decimal('1.40'),
        holiday_rate=Decimal('1.75'),
        maximum_monthly_overtime=30
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.COOPERATIVE_SOCIALI,
            leave_type=LeaveType.FERIE,
            base_annual_days=28,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.COOPERATIVE_SOCIALI,
            leave_type=LeaveType.FERIE,
            base_annual_days=30,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.COOPERATIVE_SOCIALI,
            leave_type=LeaveType.FERIE,
            base_annual_days=32,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.COOPERATIVE_SOCIALI, WorkerCategory.OPERAIO, 0, 36, 15),
        NoticePerioD(CCNLSector.COOPERATIVE_SOCIALI, WorkerCategory.OPERAIO, 36, 120, 30),
        NoticePerioD(CCNLSector.COOPERATIVE_SOCIALI, WorkerCategory.OPERAIO, 120, 999, 45),
        NoticePerioD(CCNLSector.COOPERATIVE_SOCIALI, WorkerCategory.IMPIEGATO, 0, 999, 60),
        NoticePerioD(CCNLSector.COOPERATIVE_SOCIALI, WorkerCategory.QUADRO, 0, 999, 90)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.COOPERATIVE_SOCIALI,
            allowance_type=AllowanceType.INDENNITA_FUNZIONE,
            amount=Decimal('120.00'),
            frequency="monthly"
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.COOPERATIVE_SOCIALI,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal('80.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.COOPERATIVE_SOCIALI,
        name="CCNL Cooperative Sociali",
        valid_from=date(2022, 11, 1),
        valid_to=date(2025, 10, 31),
        signatory_unions=["FP-CGIL", "CISL-FP", "UIL-FPL"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_servizi_educativi_ccnl() -> CCNLAgreement:
    """Get CCNL for Servizi Educativi - educational services sector."""
    
    job_levels = [
        JobLevel(
            level_code="ES1",
            level_name="Ausiliario",
            category=WorkerCategory.OPERAIO,
            minimum_experience_months=0,
            typical_tasks=["Pulizia spazi", "Supporto logistico", "Sorveglianza mensa"]
        ),
        JobLevel(
            level_code="ES2",
            level_name="Educatore",
            category=WorkerCategory.IMPIEGATO,
            minimum_experience_months=0,
            typical_tasks=["Attività educative", "Progettazione didattica", "Rapporti famiglie"]
        ),
        JobLevel(
            level_code="ES3",
            level_name="Coordinatore Pedagogico",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=48,
            typical_tasks=["Coordinamento pedagogico", "Formazione staff", "Supervisione qualità"]
        ),
        JobLevel(
            level_code="ES4",
            level_name="Responsabile Servizio",
            category=WorkerCategory.QUADRO,
            minimum_experience_months=72,
            typical_tasks=["Gestione completa servizio", "Rapporti enti pubblici", "Budget e programmazione"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.SERVIZI_EDUCATIVI, "ES1", Decimal('1180.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.SERVIZI_EDUCATIVI, "ES2", Decimal('1480.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.SERVIZI_EDUCATIVI, "ES3", Decimal('1880.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1)),
        SalaryTable(CCNLSector.SERVIZI_EDUCATIVI, "ES4", Decimal('2380.00'),
                   GeographicArea.CENTRO, CompanySize.SMALL, date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.SERVIZI_EDUCATIVI,
        ordinary_weekly_hours=36,
        flexible_hours_allowed=True,
        shift_work_allowed=False
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.SERVIZI_EDUCATIVI,
        daily_threshold_hours=7.2,
        weekly_threshold_hours=36,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=20
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.SERVIZI_EDUCATIVI,
            leave_type=LeaveType.FERIE,
            base_annual_days=32,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.SERVIZI_EDUCATIVI,
            leave_type=LeaveType.FERIE,
            base_annual_days=34,
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.SERVIZI_EDUCATIVI,
            leave_type=LeaveType.FERIE,
            base_annual_days=36,
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.SERVIZI_EDUCATIVI, WorkerCategory.OPERAIO, 0, 24, 15),
        NoticePerioD(CCNLSector.SERVIZI_EDUCATIVI, WorkerCategory.OPERAIO, 24, 60, 30),
        NoticePerioD(CCNLSector.SERVIZI_EDUCATIVI, WorkerCategory.OPERAIO, 60, 999, 45),
        NoticePerioD(CCNLSector.SERVIZI_EDUCATIVI, WorkerCategory.IMPIEGATO, 0, 999, 60),
        NoticePerioD(CCNLSector.SERVIZI_EDUCATIVI, WorkerCategory.QUADRO, 0, 999, 90)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.SERVIZI_EDUCATIVI,
            allowance_type=AllowanceType.INDENNITA_FUNZIONE,
            amount=Decimal('150.00'),
            frequency="monthly"
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.SERVIZI_EDUCATIVI,
            allowance_type=AllowanceType.INDENNITA_FUNZIONE,
            amount=Decimal('100.00'),
            frequency="monthly"
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.SERVIZI_EDUCATIVI,
        name="CCNL Servizi Educativi",
        valid_from=date(2023, 9, 1),
        valid_to=date(2026, 8, 31),
        signatory_unions=["FLC-CGIL", "CISL-Scuola", "UIL-Scuola"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances,
    )


def get_all_priority2_ccnl_data() -> List[CCNLAgreement]:
    """Get all Priority 2 CCNL agreements."""
    return [
        get_telecomunicazioni_ccnl(),
        get_credito_assicurazioni_ccnl(),
        get_studi_professionali_ccnl(),
        get_servizi_pulizia_ccnl(),
        get_vigilanza_privata_ccnl(),
        get_ict_ccnl(),
        get_agenzie_viaggio_ccnl(),
        get_call_center_ccnl(),
        get_cooperative_sociali_ccnl(),
        get_servizi_educativi_ccnl()
    ]


def validate_priority2_ccnl_data_completeness() -> Dict[str, Any]:
    """Validate completeness of Priority 2 CCNL data."""
    all_ccnl = get_all_priority2_ccnl_data()
    
    total_components = 0
    complete_components = 0
    missing_components = []
    sectors_complete = 0
    
    required_components = [
        'job_levels', 'salary_tables', 'working_hours', 'overtime_rules',
        'leave_entitlements', 'notice_periods', 'special_allowances'
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
        
        if sector_complete_components == sector_components:
            sectors_complete += 1
    
    completion_rate = (complete_components / total_components) * 100 if total_components > 0 else 0
    
    return {
        "total_sectors": len(all_ccnl),
        "sectors_complete": sectors_complete,
        "total_components": total_components,
        "complete_components": complete_components,
        "missing_components": missing_components,
        "completion_rate": completion_rate,
        "status": "COMPLETE" if completion_rate >= 95 else "INCOMPLETE"
    }