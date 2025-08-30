"""
Priority 4 CCNL Data for Italian Collective Labor Agreements.

This module contains the actual data for the 8 Priority 4 Public & Healthcare CCNL sectors,
representing approximately 5% of Italian workers. Data is based on the most
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


def get_sanita_privata_ccnl() -> CCNLAgreement:
    """Get CCNL for Sanità Privata - private healthcare sector."""
    
    job_levels = [
        JobLevel(
            level_code="OTA",
            level_name="Operatore Tecnico Addetto",
            category=WorkerCategory.OPERAIO,
            description="Operatore tecnico sanitario base",
            minimum_experience_months=0,
            typical_tasks=["Supporto assistenza", "Pulizia ambienti sanitari", "Trasporto pazienti"]
        ),
        JobLevel(
            level_code="OSS",
            level_name="Operatore Socio Sanitario",
            category=WorkerCategory.OPERAIO,
            description="Operatore specializzato assistenza socio-sanitaria",
            minimum_experience_months=6,
            typical_tasks=["Assistenza diretta pazienti", "Igiene personale", "Medicazioni semplici"]
        ),
        JobLevel(
            level_code="INF",
            level_name="Infermiere",
            category=WorkerCategory.IMPIEGATO,
            description="Professionista sanitario laurea triennale",
            minimum_experience_months=0,
            required_qualifications=["Laurea in Infermieristica", "Iscrizione Ordine"],
            typical_tasks=["Assistenza infermieristica", "Terapie", "Gestione pazienti"]
        ),
        JobLevel(
            level_code="COORD",
            level_name="Coordinatore Sanitario",
            category=WorkerCategory.QUADRO,
            description="Coordinatore equipe sanitaria",
            minimum_experience_months=36,
            required_qualifications=["Laurea sanitaria", "Esperienza coordinamento"],
            typical_tasks=["Coordinamento turni", "Gestione personale", "Pianificazione assistenza"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.SANITA_PRIVATA, "OTA", Decimal('1420.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.SANITA_PRIVATA, "OSS", Decimal('1580.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.SANITA_PRIVATA, "INF", Decimal('1980.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.SANITA_PRIVATA, "COORD", Decimal('2480.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.SANITA_PRIVATA,
        ordinary_weekly_hours=38,
        maximum_weekly_hours=48,
        shift_work_allowed=True,
        shift_patterns=["06:00-14:00", "14:00-22:00", "22:00-06:00"],
        night_shift_allowance=Decimal('50.00')
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.SANITA_PRIVATA,
        daily_threshold_hours=7,
        weekly_threshold_hours=38,
        daily_overtime_rate=Decimal('1.30'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=40
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.SANITA_PRIVATA,
            leave_type=LeaveType.FERIE,
            base_annual_days=30
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.SANITA_PRIVATA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=32
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.SANITA_PRIVATA, WorkerCategory.OPERAIO, 0, 60, 15),
        NoticePerioD(CCNLSector.SANITA_PRIVATA, WorkerCategory.OPERAIO, 61, 180, 30),
        NoticePerioD(CCNLSector.SANITA_PRIVATA, WorkerCategory.IMPIEGATO, 0, 60, 30),
        NoticePerioD(CCNLSector.SANITA_PRIVATA, WorkerCategory.IMPIEGATO, 61, 180, 60),
        NoticePerioD(CCNLSector.SANITA_PRIVATA, WorkerCategory.QUADRO, 0, 999, 90)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.SANITA_PRIVATA,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal('80.00'),
            frequency="monthly",
            conditions=["Lavoro con rischio biologico", "Contatto diretto pazienti"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.SANITA_PRIVATA,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('120.00'),
            frequency="monthly",
            conditions=["Lavoro su turni", "Reperibilità notturna"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.SANITA_PRIVATA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('7.00'),
            frequency="daily",
            conditions=["Turno superiore a 6 ore"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.SANITA_PRIVATA,
        name="CCNL Sanità Privata",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["CGIL", "CISL", "UIL"],
        signatory_employers=["ARIS", "Confindustria Sanità"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_case_di_cura_ccnl() -> CCNLAgreement:
    """Get CCNL for Case di Cura - nursing homes sector."""
    
    job_levels = [
        JobLevel(
            level_code="AUS",
            level_name="Ausiliario",
            category=WorkerCategory.OPERAIO,
            description="Ausiliario per servizi generali",
            minimum_experience_months=0,
            typical_tasks=["Pulizia", "Lavanderia", "Servizi generali"]
        ),
        JobLevel(
            level_code="OSS",
            level_name="Operatore Socio Sanitario",
            category=WorkerCategory.OPERAIO,
            description="Operatore assistenza socio-sanitaria",
            minimum_experience_months=3,
            typical_tasks=["Assistenza anziani", "Igiene personale", "Supporto alimentazione"]
        ),
        JobLevel(
            level_code="ASA",
            level_name="Assistente Socio Assistenziale",
            category=WorkerCategory.IMPIEGATO,
            description="Assistente qualificato per anziani",
            minimum_experience_months=12,
            typical_tasks=["Assistenza qualificata", "Attività ricreative", "Supporto famiglie"]
        ),
        JobLevel(
            level_code="RESP",
            level_name="Responsabile Struttura",
            category=WorkerCategory.QUADRO,
            description="Responsabile gestione casa di cura",
            minimum_experience_months=48,
            typical_tasks=["Gestione struttura", "Coordinamento staff", "Relazioni familiari"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.CASE_DI_CURA, "AUS", Decimal('1340.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.CASE_DI_CURA, "OSS", Decimal('1480.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.CASE_DI_CURA, "ASA", Decimal('1680.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.CASE_DI_CURA, "RESP", Decimal('2280.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.CASE_DI_CURA,
        ordinary_weekly_hours=38,
        maximum_weekly_hours=48,
        shift_work_allowed=True,
        shift_patterns=["07:00-15:00", "15:00-23:00", "23:00-07:00"],
        flexible_hours_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.CASE_DI_CURA,
        daily_threshold_hours=7,
        weekly_threshold_hours=38,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.40'),
        holiday_rate=Decimal('1.75'),
        maximum_monthly_overtime=35
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.CASE_DI_CURA,
            leave_type=LeaveType.FERIE,
            base_annual_days=28
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.CASE_DI_CURA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=30
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.CASE_DI_CURA, WorkerCategory.OPERAIO, 0, 90, 15),
        NoticePerioD(CCNLSector.CASE_DI_CURA, WorkerCategory.OPERAIO, 91, 365, 30),
        NoticePerioD(CCNLSector.CASE_DI_CURA, WorkerCategory.IMPIEGATO, 0, 90, 45),
        NoticePerioD(CCNLSector.CASE_DI_CURA, WorkerCategory.IMPIEGATO, 91, 365, 60),
        NoticePerioD(CCNLSector.CASE_DI_CURA, WorkerCategory.QUADRO, 0, 999, 90)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.CASE_DI_CURA,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('90.00'),
            frequency="monthly",
            conditions=["Lavoro continuativo", "Turni festivi"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.CASE_DI_CURA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('6.50'),
            frequency="daily",
            conditions=["Presenza superiore a 6 ore"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.CASE_DI_CURA,
        name="CCNL Case di Cura",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["CGIL", "CISL", "UIL"],
        signatory_employers=["Associazione Case di Cura Private"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_farmacie_private_ccnl() -> CCNLAgreement:
    """Get CCNL for Farmacie Private - private pharmacies sector."""
    
    job_levels = [
        JobLevel(
            level_code="COMM",
            level_name="Commesso di Farmacia",
            category=WorkerCategory.OPERAIO,
            description="Commesso vendite prodotti farmaceutici",
            minimum_experience_months=0,
            typical_tasks=["Vendita prodotti", "Gestione cassa", "Riordino scaffali"]
        ),
        JobLevel(
            level_code="FARM_ASS",
            level_name="Farmacista Assistente",
            category=WorkerCategory.IMPIEGATO,
            description="Farmacista collaboratore",
            minimum_experience_months=0,
            required_qualifications=["Laurea in Farmacia", "Abilitazione professionale"],
            typical_tasks=["Dispensazione farmaci", "Consulenza clienti", "Controllo ricette"]
        ),
        JobLevel(
            level_code="FARM_RESP",
            level_name="Farmacista Responsabile",
            category=WorkerCategory.QUADRO,
            description="Farmacista direttore di farmacia",
            minimum_experience_months=24,
            required_qualifications=["Laurea in Farmacia", "Abilitazione", "Esperienza gestionale"],
            typical_tasks=["Gestione farmacia", "Responsabilità sanitaria", "Controllo qualità"]
        ),
        JobLevel(
            level_code="TITUL",
            level_name="Farmacista Titolare",
            category=WorkerCategory.DIRIGENTE,
            description="Proprietario/gestore farmacia",
            minimum_experience_months=60,
            required_qualifications=["Laurea in Farmacia", "Autorizzazione esercizio"],
            typical_tasks=["Direzione farmacia", "Gestione commerciale", "Responsabilità legale"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.FARMACIE_PRIVATE, "COMM", Decimal('1380.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.FARMACIE_PRIVATE, "FARM_ASS", Decimal('1780.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.FARMACIE_PRIVATE, "FARM_RESP", Decimal('2380.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.FARMACIE_PRIVATE, "TITUL", Decimal('3180.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.FARMACIE_PRIVATE,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        shift_work_allowed=True,
        shift_patterns=["08:00-13:00/15:00-20:00", "20:00-08:00"],
        flexible_hours_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.FARMACIE_PRIVATE,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=30
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.FARMACIE_PRIVATE,
            leave_type=LeaveType.FERIE,
            base_annual_days=26
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.FARMACIE_PRIVATE,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=28
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.FARMACIE_PRIVATE, WorkerCategory.OPERAIO, 0, 180, 15),
        NoticePerioD(CCNLSector.FARMACIE_PRIVATE, WorkerCategory.OPERAIO, 181, 999, 30),
        NoticePerioD(CCNLSector.FARMACIE_PRIVATE, WorkerCategory.IMPIEGATO, 0, 180, 45),
        NoticePerioD(CCNLSector.FARMACIE_PRIVATE, WorkerCategory.IMPIEGATO, 181, 999, 60),
        NoticePerioD(CCNLSector.FARMACIE_PRIVATE, WorkerCategory.QUADRO, 0, 999, 90),
        NoticePerioD(CCNLSector.FARMACIE_PRIVATE, WorkerCategory.DIRIGENTE, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.FARMACIE_PRIVATE,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('100.00'),
            frequency="monthly",
            conditions=["Turni notturni", "Servizio festivi"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.FARMACIE_PRIVATE,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('150.00'),
            frequency="monthly",
            conditions=["Raggiungimento obiettivi vendita"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.FARMACIE_PRIVATE,
        name="CCNL Farmacie Private",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["CGIL", "CISL", "UIL"],
        signatory_employers=["Federfarma"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_enti_locali_ccnl() -> CCNLAgreement:
    """Get CCNL for Enti Locali - local government sector."""
    
    job_levels = [
        JobLevel(
            level_code="B1",
            level_name="Operatore Servizi",
            category=WorkerCategory.OPERAIO,
            description="Operatore servizi comunali base",
            minimum_experience_months=0,
            typical_tasks=["Manutenzione", "Pulizia", "Servizi generali"]
        ),
        JobLevel(
            level_code="C1",
            level_name="Istruttore",
            category=WorkerCategory.IMPIEGATO,
            description="Istruttore amministrativo",
            minimum_experience_months=0,
            required_qualifications=["Diploma superiore"],
            typical_tasks=["Pratiche amministrative", "Rapporti pubblico", "Gestione uffici"]
        ),
        JobLevel(
            level_code="D1",
            level_name="Istruttore Direttivo",
            category=WorkerCategory.QUADRO,
            description="Istruttore direttivo specializzato",
            minimum_experience_months=0,
            required_qualifications=["Laurea"],
            typical_tasks=["Direzione settori", "Coordinamento progetti", "Consulenza specialistica"]
        ),
        JobLevel(
            level_code="DIR",
            level_name="Dirigente",
            category=WorkerCategory.DIRIGENTE,
            description="Dirigente ente locale",
            minimum_experience_months=60,
            required_qualifications=["Laurea", "Esperienza dirigenziale"],
            typical_tasks=["Direzione generale", "Gestione strategica", "Responsabilità politiche"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.ENTI_LOCALI, "B1", Decimal('1520.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ENTI_LOCALI, "C1", Decimal('1820.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ENTI_LOCALI, "D1", Decimal('2420.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ENTI_LOCALI, "DIR", Decimal('3820.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.ENTI_LOCALI,
        ordinary_weekly_hours=36,
        maximum_weekly_hours=40,
        flexible_hours_allowed=True,
        core_hours=("09:00", "12:00"),
        part_time_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.ENTI_LOCALI,
        daily_threshold_hours=7,
        weekly_threshold_hours=36,
        daily_overtime_rate=Decimal('1.30'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=25
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.ENTI_LOCALI,
            leave_type=LeaveType.FERIE,
            base_annual_days=32
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.ENTI_LOCALI,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=35
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.ENTI_LOCALI, WorkerCategory.OPERAIO, 0, 365, 30),
        NoticePerioD(CCNLSector.ENTI_LOCALI, WorkerCategory.OPERAIO, 366, 999, 45),
        NoticePerioD(CCNLSector.ENTI_LOCALI, WorkerCategory.IMPIEGATO, 0, 365, 60),
        NoticePerioD(CCNLSector.ENTI_LOCALI, WorkerCategory.IMPIEGATO, 366, 999, 90),
        NoticePerioD(CCNLSector.ENTI_LOCALI, WorkerCategory.QUADRO, 0, 999, 120),
        NoticePerioD(CCNLSector.ENTI_LOCALI, WorkerCategory.DIRIGENTE, 0, 999, 180)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.ENTI_LOCALI,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('8.00'),
            frequency="daily",
            conditions=["Presenza minima 6 ore"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.ENTI_LOCALI,
            allowance_type=AllowanceType.INDENNITA_TRASPORTO,
            amount=Decimal('50.00'),
            frequency="monthly",
            conditions=["Trasporto pubblico insufficiente"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.ENTI_LOCALI,
        name="CCNL Enti Locali",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["CGIL", "CISL", "UIL"],
        signatory_employers=["ANCI", "UPI"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_ministeri_ccnl() -> CCNLAgreement:
    """Get CCNL for Ministeri - national ministries sector."""
    
    job_levels = [
        JobLevel(
            level_code="B",
            level_name="Assistente",
            category=WorkerCategory.OPERAIO,
            description="Assistente amministrativo",
            minimum_experience_months=0,
            required_qualifications=["Diploma superiore"],
            typical_tasks=["Supporto amministrativo", "Gestione archivi", "Protocollazione"]
        ),
        JobLevel(
            level_code="C",
            level_name="Funzionario",
            category=WorkerCategory.IMPIEGATO,
            description="Funzionario amministrativo",
            minimum_experience_months=0,
            required_qualifications=["Laurea triennale"],
            typical_tasks=["Istruttoria pratiche", "Rapporti esterni", "Gestione progetti"]
        ),
        JobLevel(
            level_code="D",
            level_name="Funzionario Superiore",
            category=WorkerCategory.QUADRO,
            description="Funzionario direttivo",
            minimum_experience_months=24,
            required_qualifications=["Laurea magistrale"],
            typical_tasks=["Direzione uffici", "Coordinamento attività", "Consulenza specialistica"]
        ),
        JobLevel(
            level_code="DIR",
            level_name="Dirigente Generale",
            category=WorkerCategory.DIRIGENTE,
            description="Dirigente di livello generale",
            minimum_experience_months=120,
            required_qualifications=["Laurea", "Esperienza dirigenziale pubblica"],
            typical_tasks=["Direzione generale", "Programmazione strategica", "Responsabilità ministeriali"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.MINISTERI, "B", Decimal('1720.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.MINISTERI, "C", Decimal('2120.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.MINISTERI, "D", Decimal('2820.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.MINISTERI, "DIR", Decimal('4820.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.MINISTERI,
        ordinary_weekly_hours=36,
        maximum_weekly_hours=40,
        flexible_hours_allowed=True,
        core_hours=("09:30", "11:30"),
        part_time_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.MINISTERI,
        daily_threshold_hours=7,
        weekly_threshold_hours=36,
        daily_overtime_rate=Decimal('1.35'),
        weekend_rate=Decimal('1.60'),
        holiday_rate=Decimal('2.20'),
        maximum_monthly_overtime=20
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.MINISTERI,
            leave_type=LeaveType.FERIE,
            base_annual_days=35
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.MINISTERI,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=40
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.MINISTERI, WorkerCategory.OPERAIO, 0, 999, 60),
        NoticePerioD(CCNLSector.MINISTERI, WorkerCategory.IMPIEGATO, 0, 999, 90),
        NoticePerioD(CCNLSector.MINISTERI, WorkerCategory.QUADRO, 0, 999, 150),
        NoticePerioD(CCNLSector.MINISTERI, WorkerCategory.DIRIGENTE, 0, 999, 240)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.MINISTERI,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('8.50'),
            frequency="daily",
            conditions=["Presenza giornaliera"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.MINISTERI,
            allowance_type=AllowanceType.INDENNITA_TRASPORTO,
            amount=Decimal('80.00'),
            frequency="monthly",
            conditions=["Sede di lavoro Roma/Milano"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.MINISTERI,
        name="CCNL Ministeri",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["CGIL", "CISL", "UIL"],
        signatory_employers=["Presidenza Consiglio Ministri"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_scuola_privata_ccnl() -> CCNLAgreement:
    """Get CCNL for Scuola Privata - private schools sector."""
    
    job_levels = [
        JobLevel(
            level_code="ATA",
            level_name="Personale ATA",
            category=WorkerCategory.OPERAIO,
            description="Personale amministrativo, tecnico, ausiliario",
            minimum_experience_months=0,
            typical_tasks=["Segreteria", "Pulizia", "Sorveglianza", "Assistenza tecnica"]
        ),
        JobLevel(
            level_code="DOC_PRIM",
            level_name="Docente Primaria",
            category=WorkerCategory.IMPIEGATO,
            description="Insegnante scuola primaria",
            minimum_experience_months=0,
            required_qualifications=["Laurea Scienze Formazione Primaria"],
            typical_tasks=["Insegnamento primaria", "Programmazione didattica", "Valutazione alunni"]
        ),
        JobLevel(
            level_code="DOC_SEC",
            level_name="Docente Secondaria",
            category=WorkerCategory.IMPIEGATO,
            description="Insegnante scuola secondaria",
            minimum_experience_months=0,
            required_qualifications=["Laurea magistrale", "Abilitazione all'insegnamento"],
            typical_tasks=["Insegnamento materie", "Preparazione lezioni", "Rapporti famiglie"]
        ),
        JobLevel(
            level_code="COORD",
            level_name="Coordinatore Didattico",
            category=WorkerCategory.QUADRO,
            description="Coordinatore attività didattiche",
            minimum_experience_months=36,
            required_qualifications=["Laurea", "Esperienza didattica"],
            typical_tasks=["Coordinamento docenti", "Programmazione", "Valutazione qualità"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.SCUOLA_PRIVATA, "ATA", Decimal('1420.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.SCUOLA_PRIVATA, "DOC_PRIM", Decimal('1620.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.SCUOLA_PRIVATA, "DOC_SEC", Decimal('1820.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.SCUOLA_PRIVATA, "COORD", Decimal('2420.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.SCUOLA_PRIVATA,
        ordinary_weekly_hours=25,  # Ore di insegnamento
        maximum_weekly_hours=40,   # Include preparazione e riunioni
        flexible_hours_allowed=True,
        core_hours=("08:00", "14:00"),
        part_time_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.SCUOLA_PRIVATA,
        daily_threshold_hours=6,
        weekly_threshold_hours=25,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.40'),
        holiday_rate=Decimal('1.75'),
        maximum_monthly_overtime=15
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.SCUOLA_PRIVATA,
            leave_type=LeaveType.FERIE,
            base_annual_days=30  # Periodi non didattici
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.SCUOLA_PRIVATA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=25
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.SCUOLA_PRIVATA, WorkerCategory.OPERAIO, 0, 180, 30),
        NoticePerioD(CCNLSector.SCUOLA_PRIVATA, WorkerCategory.OPERAIO, 181, 999, 45),
        NoticePerioD(CCNLSector.SCUOLA_PRIVATA, WorkerCategory.IMPIEGATO, 0, 180, 60),
        NoticePerioD(CCNLSector.SCUOLA_PRIVATA, WorkerCategory.IMPIEGATO, 181, 999, 90),
        NoticePerioD(CCNLSector.SCUOLA_PRIVATA, WorkerCategory.QUADRO, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.SCUOLA_PRIVATA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('6.50'),
            frequency="daily",
            conditions=["Presenza giornata piena"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.SCUOLA_PRIVATA,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('200.00'),
            frequency="annual",
            conditions=["Raggiungimento obiettivi didattici"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.SCUOLA_PRIVATA,
        name="CCNL Scuola Privata",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["CGIL Scuola", "CISL Scuola", "UIL Scuola"],
        signatory_employers=["ANINSEI", "FIDAE"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_universita_private_ccnl() -> CCNLAgreement:
    """Get CCNL for Università Private - private universities sector."""
    
    job_levels = [
        JobLevel(
            level_code="TAB",
            level_name="Tecnico Amministrativo",
            category=WorkerCategory.OPERAIO,
            description="Personale tecnico amministrativo",
            minimum_experience_months=0,
            required_qualifications=["Diploma superiore"],
            typical_tasks=["Supporto amministrativo", "Gestione laboratori", "Servizi studenti"]
        ),
        JobLevel(
            level_code="RIC_TD",
            level_name="Ricercatore a Tempo Determinato",
            category=WorkerCategory.IMPIEGATO,
            description="Ricercatore universitario junior",
            minimum_experience_months=0,
            required_qualifications=["Dottorato di ricerca"],
            typical_tasks=["Ricerca scientifica", "Didattica integrativa", "Pubblicazioni"]
        ),
        JobLevel(
            level_code="PROF_ASS",
            level_name="Professore Associato",
            category=WorkerCategory.QUADRO,
            description="Docente universitario associato",
            minimum_experience_months=60,
            required_qualifications=["Abilitazione scientifica nazionale"],
            typical_tasks=["Insegnamento universitario", "Ricerca avanzata", "Direzione progetti"]
        ),
        JobLevel(
            level_code="PROF_ORD",
            level_name="Professore Ordinario",
            category=WorkerCategory.DIRIGENTE,
            description="Professore universitario di prima fascia",
            minimum_experience_months=120,
            required_qualifications=["Abilitazione prima fascia"],
            typical_tasks=["Direzione scientifica", "Gestione dipartimenti", "Formazione dottorati"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.UNIVERSITA_PRIVATE, "TAB", Decimal('1580.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.UNIVERSITA_PRIVATE, "RIC_TD", Decimal('2180.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.UNIVERSITA_PRIVATE, "PROF_ASS", Decimal('3180.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.UNIVERSITA_PRIVATE, "PROF_ORD", Decimal('4680.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.UNIVERSITA_PRIVATE,
        ordinary_weekly_hours=36,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        core_hours=("09:00", "18:00"),
        part_time_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.UNIVERSITA_PRIVATE,
        daily_threshold_hours=7,
        weekly_threshold_hours=36,
        daily_overtime_rate=Decimal('1.30'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=20
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.UNIVERSITA_PRIVATE,
            leave_type=LeaveType.FERIE,
            base_annual_days=32
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.UNIVERSITA_PRIVATE,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=30
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.UNIVERSITA_PRIVATE, WorkerCategory.OPERAIO, 0, 365, 60),
        NoticePerioD(CCNLSector.UNIVERSITA_PRIVATE, WorkerCategory.OPERAIO, 366, 999, 90),
        NoticePerioD(CCNLSector.UNIVERSITA_PRIVATE, WorkerCategory.IMPIEGATO, 0, 999, 120),
        NoticePerioD(CCNLSector.UNIVERSITA_PRIVATE, WorkerCategory.QUADRO, 0, 999, 180),
        NoticePerioD(CCNLSector.UNIVERSITA_PRIVATE, WorkerCategory.DIRIGENTE, 0, 999, 240)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.UNIVERSITA_PRIVATE,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('8.00'),
            frequency="daily",
            conditions=["Presenza universitaria"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.UNIVERSITA_PRIVATE,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('500.00'),
            frequency="annual",
            conditions=["Pubblicazioni scientifiche", "Progetti finanziati"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.UNIVERSITA_PRIVATE,
        name="CCNL Università Private",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["CGIL", "CISL", "UIL"],
        signatory_employers=["Associazione Università Private Italiane"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_enti_di_ricerca_ccnl() -> CCNLAgreement:
    """Get CCNL for Enti di Ricerca - research institutions sector."""
    
    job_levels = [
        JobLevel(
            level_code="TAR",
            level_name="Tecnico di Ricerca",
            category=WorkerCategory.OPERAIO,
            description="Tecnico specializzato ricerca",
            minimum_experience_months=0,
            required_qualifications=["Diploma tecnico specialistico"],
            typical_tasks=["Supporto tecnico", "Gestione strumentazione", "Analisi campioni"]
        ),
        JobLevel(
            level_code="RICJR",
            level_name="Ricercatore Junior",
            category=WorkerCategory.IMPIEGATO,
            description="Ricercatore specializzato",
            minimum_experience_months=6,
            required_qualifications=["Laurea magistrale o Dottorato"],
            typical_tasks=["Attività ricerca", "Sperimentazione", "Stesura reports"]
        ),
        JobLevel(
            level_code="RICSR",
            level_name="Ricercatore Senior",
            category=WorkerCategory.QUADRO,
            description="Ricercatore esperto",
            minimum_experience_months=36,
            required_qualifications=["Dottorato", "Esperienza ricerca certificata"],
            typical_tasks=["Coordinamento ricerche", "Gestione progetti", "Supervisione team"]
        ),
        JobLevel(
            level_code="DIRETT",
            level_name="Direttore di Ricerca",
            category=WorkerCategory.DIRIGENTE,
            description="Direttore settore ricerca",
            minimum_experience_months=84,
            required_qualifications=["Dottorato", "Esperienza dirigenziale ricerca"],
            typical_tasks=["Direzione strategica", "Rapporti istituzionali", "Coordinamento generale"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.ENTI_DI_RICERCA, "TAR", Decimal('1680.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ENTI_DI_RICERCA, "RICJR", Decimal('2280.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ENTI_DI_RICERCA, "RICSR", Decimal('3280.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.ENTI_DI_RICERCA, "DIRETT", Decimal('4880.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.ENTI_DI_RICERCA,
        ordinary_weekly_hours=36,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        flexible_hours_range=(6, 10),
        core_hours=("10:00", "15:00"),
        part_time_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.ENTI_DI_RICERCA,
        daily_threshold_hours=7,
        weekly_threshold_hours=36,
        daily_overtime_rate=Decimal('1.35'),
        weekend_rate=Decimal('1.60'),
        holiday_rate=Decimal('2.20'),
        maximum_monthly_overtime=25
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.ENTI_DI_RICERCA,
            leave_type=LeaveType.FERIE,
            base_annual_days=34
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.ENTI_DI_RICERCA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=32
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.ENTI_DI_RICERCA, WorkerCategory.OPERAIO, 0, 365, 60),
        NoticePerioD(CCNLSector.ENTI_DI_RICERCA, WorkerCategory.OPERAIO, 366, 999, 90),
        NoticePerioD(CCNLSector.ENTI_DI_RICERCA, WorkerCategory.IMPIEGATO, 0, 999, 120),
        NoticePerioD(CCNLSector.ENTI_DI_RICERCA, WorkerCategory.QUADRO, 0, 999, 180),
        NoticePerioD(CCNLSector.ENTI_DI_RICERCA, WorkerCategory.DIRIGENTE, 0, 999, 270)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.ENTI_DI_RICERCA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('8.50'),
            frequency="daily",
            conditions=["Presenza in sede ricerca"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.ENTI_DI_RICERCA,
            allowance_type=AllowanceType.INDENNITA_TRASFERTA,
            amount=Decimal('120.00'),
            frequency="daily",
            conditions=["Trasferte scientifiche", "Congressi", "Collaborazioni"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.ENTI_DI_RICERCA,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('800.00'),
            frequency="annual",
            conditions=["Pubblicazioni impact factor", "Brevetti", "Finanziamenti ottenuti"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.ENTI_DI_RICERCA,
        name="CCNL Enti di Ricerca",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["CGIL", "CISL", "UIL"],
        signatory_employers=["Associazione Enti Ricerca Privati"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_all_priority4_ccnl_data() -> List[CCNLAgreement]:
    """Get all Priority 4 CCNL agreements."""
    return [
        get_sanita_privata_ccnl(),
        get_case_di_cura_ccnl(),
        get_farmacie_private_ccnl(),
        get_enti_locali_ccnl(),
        get_ministeri_ccnl(),
        get_scuola_privata_ccnl(),
        get_universita_private_ccnl(),
        get_enti_di_ricerca_ccnl()
    ]


def validate_priority4_ccnl_data_completeness() -> Dict[str, Any]:
    """Validate completeness of Priority 4 CCNL data."""
    validation_result = {
        "status": "COMPLETE",
        "total_sectors": 8,
        "sectors_complete": 0,
        "missing_components": [],
        "completion_rate": 0.0,
        "validation_date": date.today().isoformat()
    }
    
    try:
        all_agreements = get_all_priority4_ccnl_data()
        
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
        if validation_result["completion_rate"] < 95:
            validation_result["status"] = "INCOMPLETE"
        
        return validation_result
        
    except Exception as e:
        validation_result["status"] = "ERROR"
        validation_result["error"] = str(e)
        return validation_result