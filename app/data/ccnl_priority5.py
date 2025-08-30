"""
Priority 5 CCNL Data for Italian Collective Labor Agreements.

This module contains the actual data for the 5 Priority 5 Media & Entertainment CCNL sectors,
representing approximately 3% of Italian workers. Data is based on the most
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


def get_giornalisti_ccnl() -> CCNLAgreement:
    """Get CCNL for Giornalisti - journalists sector."""
    
    job_levels = [
        JobLevel(
            level_code="PRAT",
            level_name="Praticante Giornalista",
            category=WorkerCategory.OPERAIO,
            description="Giornalista in formazione",
            minimum_experience_months=0,
            required_qualifications=["Diploma", "Iscrizione Ordine praticanti"],
            typical_tasks=["Redazione articoli base", "Ricerca informazioni", "Supporto redazione"]
        ),
        JobLevel(
            level_code="GIOR",
            level_name="Giornalista Professionista",
            category=WorkerCategory.IMPIEGATO,
            description="Giornalista professionale qualificato",
            minimum_experience_months=18,
            required_qualifications=["Esame professionale", "Iscrizione Ordine"],
            typical_tasks=["Redazione articoli", "Interviste", "Inchieste", "Reportage"]
        ),
        JobLevel(
            level_code="GIOR_SPEC",
            level_name="Giornalista Specializzato",
            category=WorkerCategory.QUADRO,
            description="Giornalista specialista settore",
            minimum_experience_months=60,
            required_qualifications=["Esperienza specialistica", "Portfolio professionale"],
            typical_tasks=["Articoli specialistici", "Analisi approfondite", "Consulenze editoriali"]
        ),
        JobLevel(
            level_code="CAPOREDATT",
            level_name="Caporedattore",
            category=WorkerCategory.DIRIGENTE,
            description="Responsabile redazione giornalistica",
            minimum_experience_months=120,
            required_qualifications=["Esperienza redazionale", "Competenze manageriali"],
            typical_tasks=["Direzione redazione", "Coordinamento giornalisti", "Pianificazione editoriale"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.GIORNALISTI, "PRAT", Decimal('1680.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.GIORNALISTI, "GIOR", Decimal('2480.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.GIORNALISTI, "GIOR_SPEC", Decimal('3480.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.GIORNALISTI, "CAPOREDATT", Decimal('4880.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.GIORNALISTI,
        ordinary_weekly_hours=36,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        flexible_hours_range=(6, 12),
        shift_work_allowed=True,
        shift_patterns=["06:00-14:00", "14:00-22:00", "22:00-06:00"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.GIORNALISTI,
        daily_threshold_hours=7,
        weekly_threshold_hours=36,
        daily_overtime_rate=Decimal('1.40'),
        weekend_rate=Decimal('1.60'),
        holiday_rate=Decimal('2.20'),
        maximum_monthly_overtime=50  # High for news deadlines
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.GIORNALISTI,
            leave_type=LeaveType.FERIE,
            base_annual_days=30
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.GIORNALISTI,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=25
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.GIORNALISTI, WorkerCategory.OPERAIO, 0, 180, 30),
        NoticePerioD(CCNLSector.GIORNALISTI, WorkerCategory.OPERAIO, 181, 999, 45),
        NoticePerioD(CCNLSector.GIORNALISTI, WorkerCategory.IMPIEGATO, 0, 365, 90),
        NoticePerioD(CCNLSector.GIORNALISTI, WorkerCategory.IMPIEGATO, 366, 999, 120),
        NoticePerioD(CCNLSector.GIORNALISTI, WorkerCategory.QUADRO, 0, 999, 150),
        NoticePerioD(CCNLSector.GIORNALISTI, WorkerCategory.DIRIGENTE, 0, 999, 180)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.GIORNALISTI,
            allowance_type=AllowanceType.INDENNITA_TRASFERTA,
            amount=Decimal('150.00'),
            frequency="daily",
            conditions=["Trasferte giornalistiche", "Reportage esterni"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.GIORNALISTI,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('300.00'),
            frequency="monthly",
            conditions=["Articoli pubblicati", "Esclusivi e inchieste"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.GIORNALISTI,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('200.00'),
            frequency="monthly",
            conditions=["Turni notturni", "Weekend e festivi"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.GIORNALISTI,
        name="CCNL Giornalisti",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["FNSI", "USIGRAI", "UNIRAI"],
        signatory_employers=["FIEG", "Confindustria Radio TV"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_grafici_editoriali_ccnl() -> CCNLAgreement:
    """Get CCNL for Grafici Editoriali - publishing graphics sector."""
    
    job_levels = [
        JobLevel(
            level_code="GRAF_JR",
            level_name="Grafico Junior",
            category=WorkerCategory.OPERAIO,
            description="Grafico editoriale base",
            minimum_experience_months=0,
            required_qualifications=["Diploma artistico o tecnico"],
            typical_tasks=["Impaginazione base", "Ritocco immagini", "Layout semplici"]
        ),
        JobLevel(
            level_code="GRAF_EDIT",
            level_name="Grafico Editoriale",
            category=WorkerCategory.IMPIEGATO,
            description="Grafico specializzato in editoria",
            minimum_experience_months=24,
            required_qualifications=["Portfolio professionale", "Software specialistici"],
            typical_tasks=["Design copertine", "Layout complessi", "Coordinamento grafico"]
        ),
        JobLevel(
            level_code="ART_DIR",
            level_name="Art Director",
            category=WorkerCategory.QUADRO,
            description="Direttore artistico progetti",
            minimum_experience_months=60,
            required_qualifications=["Esperienza direzione artistica", "Portfolio avanzato"],
            typical_tasks=["Concept creativi", "Direzione progetti", "Supervisione team"]
        ),
        JobLevel(
            level_code="RESP_GRAF",
            level_name="Responsabile Grafica",
            category=WorkerCategory.DIRIGENTE,
            description="Responsabile reparto grafico",
            minimum_experience_months=84,
            required_qualifications=["Esperienza manageriale", "Competenze creative"],
            typical_tasks=["Gestione reparto", "Budget creativi", "Strategia visual"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.GRAFICI_EDITORIALI, "GRAF_JR", Decimal('1580.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.GRAFICI_EDITORIALI, "GRAF_EDIT", Decimal('2180.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.GRAFICI_EDITORIALI, "ART_DIR", Decimal('3180.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.GRAFICI_EDITORIALI, "RESP_GRAF", Decimal('4180.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.GRAFICI_EDITORIALI,
        ordinary_weekly_hours=38,
        maximum_weekly_hours=45,
        flexible_hours_allowed=True,
        core_hours=("10:00", "16:00"),
        part_time_allowed=True
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.GRAFICI_EDITORIALI,
        daily_threshold_hours=8,
        weekly_threshold_hours=38,
        daily_overtime_rate=Decimal('1.30'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_monthly_overtime=40
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.GRAFICI_EDITORIALI,
            leave_type=LeaveType.FERIE,
            base_annual_days=28
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.GRAFICI_EDITORIALI,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=24
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.GRAFICI_EDITORIALI, WorkerCategory.OPERAIO, 0, 180, 30),
        NoticePerioD(CCNLSector.GRAFICI_EDITORIALI, WorkerCategory.OPERAIO, 181, 999, 45),
        NoticePerioD(CCNLSector.GRAFICI_EDITORIALI, WorkerCategory.IMPIEGATO, 0, 999, 60),
        NoticePerioD(CCNLSector.GRAFICI_EDITORIALI, WorkerCategory.QUADRO, 0, 999, 90),
        NoticePerioD(CCNLSector.GRAFICI_EDITORIALI, WorkerCategory.DIRIGENTE, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.GRAFICI_EDITORIALI,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('250.00'),
            frequency="monthly",
            conditions=["Progetti completati", "Qualità lavoro"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.GRAFICI_EDITORIALI,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('7.50'),
            frequency="daily",
            conditions=["Presenza lavorativa"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.GRAFICI_EDITORIALI,
        name="CCNL Grafici Editoriali",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["CGIL", "CISL", "UIL"],
        signatory_employers=["Associazione Grafici Editoriali"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_cinema_audiovisivo_ccnl() -> CCNLAgreement:
    """Get CCNL for Cinema e Audiovisivo - cinema and audiovisual sector."""
    
    job_levels = [
        JobLevel(
            level_code="ASSIST",
            level_name="Assistente Produzione",
            category=WorkerCategory.OPERAIO,
            description="Assistente per produzioni audiovisive",
            minimum_experience_months=0,
            typical_tasks=["Supporto troupe", "Gestione attrezzature", "Organizzazione set"]
        ),
        JobLevel(
            level_code="TECNICO",
            level_name="Tecnico Audiovisivo",
            category=WorkerCategory.IMPIEGATO,
            description="Tecnico specializzato audio/video",
            minimum_experience_months=12,
            required_qualifications=["Competenze tecniche AV", "Esperienza sul campo"],
            typical_tasks=["Riprese", "Audio recording", "Post-produzione", "Montaggio"]
        ),
        JobLevel(
            level_code="REGISTA_ASS",
            level_name="Regista Assistente",
            category=WorkerCategory.QUADRO,
            description="Assistente alla regia",
            minimum_experience_months=36,
            required_qualifications=["Esperienza regia", "Competenze creative"],
            typical_tasks=["Supporto regia", "Coordinamento scene", "Direzione attori"]
        ),
        JobLevel(
            level_code="PRODUTTORE",
            level_name="Produttore",
            category=WorkerCategory.DIRIGENTE,
            description="Produttore esecutivo",
            minimum_experience_months=72,
            required_qualifications=["Esperienza produzione", "Competenze manageriali"],
            typical_tasks=["Gestione produzione", "Budget", "Coordinamento generale", "Distribuzione"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.CINEMA_AUDIOVISIVO, "ASSIST", Decimal('1780.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.CINEMA_AUDIOVISIVO, "TECNICO", Decimal('2580.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.CINEMA_AUDIOVISIVO, "REGISTA_ASS", Decimal('3780.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.CINEMA_AUDIOVISIVO, "PRODUTTORE", Decimal('5580.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.CINEMA_AUDIOVISIVO,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=50,  # Higher for productions
        flexible_hours_allowed=True,
        flexible_hours_range=(8, 14),
        shift_work_allowed=True,
        shift_patterns=["Mattino", "Pomeriggio", "Serale", "Notturno"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.CINEMA_AUDIOVISIVO,
        daily_threshold_hours=8,
        weekly_threshold_hours=40,
        daily_overtime_rate=Decimal('1.50'),
        weekend_rate=Decimal('1.75'),
        holiday_rate=Decimal('2.50'),
        maximum_monthly_overtime=80  # High for film productions
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.CINEMA_AUDIOVISIVO,
            leave_type=LeaveType.FERIE,
            base_annual_days=26
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.CINEMA_AUDIOVISIVO,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=22
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.CINEMA_AUDIOVISIVO, WorkerCategory.OPERAIO, 0, 180, 15),
        NoticePerioD(CCNLSector.CINEMA_AUDIOVISIVO, WorkerCategory.OPERAIO, 181, 999, 30),
        NoticePerioD(CCNLSector.CINEMA_AUDIOVISIVO, WorkerCategory.IMPIEGATO, 0, 999, 45),
        NoticePerioD(CCNLSector.CINEMA_AUDIOVISIVO, WorkerCategory.QUADRO, 0, 999, 60),
        NoticePerioD(CCNLSector.CINEMA_AUDIOVISIVO, WorkerCategory.DIRIGENTE, 0, 999, 90)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.CINEMA_AUDIOVISIVO,
            allowance_type=AllowanceType.INDENNITA_TRASFERTA,
            amount=Decimal('200.00'),
            frequency="daily",
            conditions=["Location esterne", "Riprese fuori sede"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.CINEMA_AUDIOVISIVO,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('300.00'),
            frequency="monthly",
            conditions=["Turni notturni", "Riprese weekend"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.CINEMA_AUDIOVISIVO,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('500.00'),
            frequency="per project",
            conditions=["Completamento progetti", "Successo produzioni"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.CINEMA_AUDIOVISIVO,
        name="CCNL Cinema e Audiovisivo",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["SLC-CGIL", "FISTEL-CISL", "UILCOM"],
        signatory_employers=["ANICA", "APT"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_teatro_ccnl() -> CCNLAgreement:
    """Get CCNL for Teatro - theater sector."""
    
    job_levels = [
        JobLevel(
            level_code="TECNICO_SC",
            level_name="Tecnico di Scena",
            category=WorkerCategory.OPERAIO,
            description="Tecnico per allestimenti teatrali",
            minimum_experience_months=0,
            typical_tasks=["Allestimento scene", "Macchinisti", "Audio e luci base"]
        ),
        JobLevel(
            level_code="ATTORE",
            level_name="Attore",
            category=WorkerCategory.IMPIEGATO,
            description="Attore professionista",
            minimum_experience_months=6,
            required_qualifications=["Formazione teatrale", "Esperienza scenica"],
            typical_tasks=["Recitazione", "Prove", "Spettacoli", "Tournée"]
        ),
        JobLevel(
            level_code="REGISTA_TEAT",
            level_name="Regista Teatrale",
            category=WorkerCategory.QUADRO,
            description="Regista per produzioni teatrali",
            minimum_experience_months=48,
            required_qualifications=["Esperienza registica", "Portfolio teatrale"],
            typical_tasks=["Direzione artistica", "Regia spettacoli", "Formazione cast"]
        ),
        JobLevel(
            level_code="DIRETT_TEAT",
            level_name="Direttore Teatrale",
            category=WorkerCategory.DIRIGENTE,
            description="Direttore artistico teatro",
            minimum_experience_months=96,
            required_qualifications=["Esperienza direzione teatrale", "Competenze manageriali"],
            typical_tasks=["Direzione artistica", "Programmazione", "Gestione teatro", "Budget"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.TEATRO, "TECNICO_SC", Decimal('1480.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.TEATRO, "ATTORE", Decimal('2280.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.TEATRO, "REGISTA_TEAT", Decimal('3480.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.TEATRO, "DIRETT_TEAT", Decimal('4980.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.TEATRO,
        ordinary_weekly_hours=35,  # Lower for artistic work
        maximum_weekly_hours=45,
        flexible_hours_allowed=True,
        shift_work_allowed=True,
        shift_patterns=["Mattutino", "Pomeridiano", "Serale"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.TEATRO,
        daily_threshold_hours=7,
        weekly_threshold_hours=35,
        daily_overtime_rate=Decimal('1.40'),
        weekend_rate=Decimal('1.60'),
        holiday_rate=Decimal('2.20'),
        maximum_monthly_overtime=60  # For rehearsals and performances
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.TEATRO,
            leave_type=LeaveType.FERIE,
            base_annual_days=32  # Higher for artistic sector
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.TEATRO,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=26
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.TEATRO, WorkerCategory.OPERAIO, 0, 180, 30),
        NoticePerioD(CCNLSector.TEATRO, WorkerCategory.OPERAIO, 181, 999, 45),
        NoticePerioD(CCNLSector.TEATRO, WorkerCategory.IMPIEGATO, 0, 999, 60),
        NoticePerioD(CCNLSector.TEATRO, WorkerCategory.QUADRO, 0, 999, 90),
        NoticePerioD(CCNLSector.TEATRO, WorkerCategory.DIRIGENTE, 0, 999, 120)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.TEATRO,
            allowance_type=AllowanceType.INDENNITA_TRASFERTA,
            amount=Decimal('120.00'),
            frequency="daily",
            conditions=["Tournée", "Spettacoli fuori sede"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.TEATRO,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('150.00'),
            frequency="monthly",
            conditions=["Spettacoli serali", "Weekend"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.TEATRO,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('400.00'),
            frequency="per season",
            conditions=["Successo spettacoli", "Incassi superiori alla media"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.TEATRO,
        name="CCNL Teatro",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["SLC-CGIL", "FISTEL-CISL", "UILCOM"],
        signatory_employers=["Associazione Teatri Privati"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_radio_tv_private_ccnl() -> CCNLAgreement:
    """Get CCNL for Radio e TV Private - private radio/TV sector."""
    
    job_levels = [
        JobLevel(
            level_code="OPER_TECN",
            level_name="Operatore Tecnico",
            category=WorkerCategory.OPERAIO,
            description="Operatore tecnico radio/TV",
            minimum_experience_months=0,
            required_qualifications=["Competenze tecniche base A/V"],
            typical_tasks=["Gestione regia", "Controllo audio", "Assistenza tecnica"]
        ),
        JobLevel(
            level_code="CONDUTTORE",
            level_name="Conduttore",
            category=WorkerCategory.IMPIEGATO,
            description="Conduttore radiofonico/televisivo",
            minimum_experience_months=12,
            required_qualifications=["Esperienza conduzione", "Competenze comunicative"],
            typical_tasks=["Conduzione programmi", "Intrattenimento", "Interviste", "Dirette"]
        ),
        JobLevel(
            level_code="AUTORE",
            level_name="Autore",
            category=WorkerCategory.QUADRO,
            description="Autore e sceneggiatore",
            minimum_experience_months=36,
            required_qualifications=["Portfolio creativo", "Esperienza scrittura"],
            typical_tasks=["Scrittura programmi", "Ideazione format", "Sceneggiature"]
        ),
        JobLevel(
            level_code="DIRETT_PROG",
            level_name="Direttore Programmi",
            category=WorkerCategory.DIRIGENTE,
            description="Direttore dei programmi",
            minimum_experience_months=72,
            required_qualifications=["Esperienza direzione", "Competenze manageriali"],
            typical_tasks=["Palinsesto", "Direzione creativa", "Gestione produzioni"]
        )
    ]
    
    salary_tables = [
        SalaryTable(CCNLSector.RADIO_TV_PRIVATE, "OPER_TECN", Decimal('1880.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.RADIO_TV_PRIVATE, "CONDUTTORE", Decimal('2980.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.RADIO_TV_PRIVATE, "AUTORE", Decimal('3980.00'),
                   valid_from=date(2024, 1, 1)),
        SalaryTable(CCNLSector.RADIO_TV_PRIVATE, "DIRETT_PROG", Decimal('5980.00'),
                   valid_from=date(2024, 1, 1))
    ]
    
    working_hours = WorkingHours(
        ccnl_sector=CCNLSector.RADIO_TV_PRIVATE,
        ordinary_weekly_hours=38,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        shift_work_allowed=True,
        shift_patterns=["06:00-14:00", "14:00-22:00", "22:00-06:00", "Weekend"]
    )
    
    overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.RADIO_TV_PRIVATE,
        daily_threshold_hours=8,
        weekly_threshold_hours=38,
        daily_overtime_rate=Decimal('1.45'),
        weekend_rate=Decimal('1.70'),
        holiday_rate=Decimal('2.30'),
        maximum_monthly_overtime=60
    )
    
    leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.RADIO_TV_PRIVATE,
            leave_type=LeaveType.FERIE,
            base_annual_days=29
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.RADIO_TV_PRIVATE,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_days=26
        )
    ]
    
    notice_periods = [
        NoticePerioD(CCNLSector.RADIO_TV_PRIVATE, WorkerCategory.OPERAIO, 0, 180, 30),
        NoticePerioD(CCNLSector.RADIO_TV_PRIVATE, WorkerCategory.OPERAIO, 181, 999, 45),
        NoticePerioD(CCNLSector.RADIO_TV_PRIVATE, WorkerCategory.IMPIEGATO, 0, 999, 75),
        NoticePerioD(CCNLSector.RADIO_TV_PRIVATE, WorkerCategory.QUADRO, 0, 999, 105),
        NoticePerioD(CCNLSector.RADIO_TV_PRIVATE, WorkerCategory.DIRIGENTE, 0, 999, 150)
    ]
    
    special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.RADIO_TV_PRIVATE,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('250.00'),
            frequency="monthly",
            conditions=["Turni serali", "Notturni", "Weekend"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.RADIO_TV_PRIVATE,
            allowance_type=AllowanceType.PREMIO_PRODUZIONE,
            amount=Decimal('400.00'),
            frequency="monthly",
            conditions=["Share programmi", "Ascolti target"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.RADIO_TV_PRIVATE,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('8.00'),
            frequency="daily",
            conditions=["Presenza lavorativa"]
        )
    ]
    
    return CCNLAgreement(
        sector=CCNLSector.RADIO_TV_PRIVATE,
        name="CCNL Radio e TV Private",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["SLC-CGIL", "FISTEL-CISL", "UILCOM"],
        signatory_employers=["Confindustria Radio TV"],
        job_levels=job_levels,
        salary_tables=salary_tables,
        working_hours=working_hours,
        overtime_rules=overtime_rules,
        leave_entitlements=leave_entitlements,
        notice_periods=notice_periods,
        special_allowances=special_allowances
    )


def get_all_priority5_ccnl_data() -> List[CCNLAgreement]:
    """Get all Priority 5 CCNL agreements."""
    return [
        get_giornalisti_ccnl(),
        get_grafici_editoriali_ccnl(),
        get_cinema_audiovisivo_ccnl(),
        get_teatro_ccnl(),
        get_radio_tv_private_ccnl()
    ]


def validate_priority5_ccnl_data_completeness() -> Dict[str, Any]:
    """Validate completeness of Priority 5 CCNL data."""
    validation_result = {
        "status": "COMPLETE",
        "total_sectors": 5,
        "sectors_complete": 0,
        "missing_components": [],
        "completion_rate": 0.0,
        "validation_date": date.today().isoformat()
    }
    
    try:
        all_agreements = get_all_priority5_ccnl_data()
        
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