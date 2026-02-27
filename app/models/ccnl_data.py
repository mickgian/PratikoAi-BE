"""Data models for Italian Collective Labor Agreements (CCNL).

This module provides comprehensive data structures for storing and manipulating
CCNL agreements including job classifications, salary tables, working hours,
leave entitlements, and calculation engines.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class CCNLSector(str, Enum):
    """Enumeration of CCNL sectors with priority levels."""

    # PRIORITY 1 - Major Industrial & Commercial Sectors
    METALMECCANICI_INDUSTRIA = "metalmeccanici_industria"
    METALMECCANICI_ARTIGIANI = "metalmeccanici_artigiani"
    COMMERCIO_TERZIARIO = "commercio_terziario"
    EDILIZIA_INDUSTRIA = "edilizia_industria"
    EDILIZIA_ARTIGIANATO = "edilizia_artigianato"
    PUBBLICI_ESERCIZI = "pubblici_esercizi"
    TURISMO = "turismo"
    TRASPORTI_LOGISTICA = "trasporti_logistica"
    CHIMICI_FARMACEUTICI = "chimici_farmaceutici"
    TESSILI = "tessili"

    # PRIORITY 2 - Service & Professional Sectors
    TELECOMUNICAZIONI = "telecomunicazioni"
    CREDITO_ASSICURAZIONI = "credito_assicurazioni"
    STUDI_PROFESSIONALI = "studi_professionali"
    SERVIZI_PULIZIA = "servizi_pulizia"
    VIGILANZA_PRIVATA = "vigilanza_privata"
    ICT = "ict"
    AGENZIE_VIAGGIO = "agenzie_viaggio"
    CALL_CENTER = "call_center"
    COOPERATIVE_SOCIALI = "cooperative_sociali"
    SERVIZI_EDUCATIVI = "servizi_educativi"

    # PRIORITY 3 - Specialized Industries
    ALIMENTARI_INDUSTRIA = "alimentari_industria"
    PANIFICAZIONE = "panificazione"
    AGRICOLTURA = "agricoltura"
    FLOROVIVAISTI = "florovivaisti"
    LEGNO_ARREDAMENTO = "legno_arredamento"
    CARTA_GRAFICA = "carta_grafica"
    ENERGIA_PETROLIO = "energia_petrolio"
    GAS_ACQUA = "gas_acqua"
    GOMMA_PLASTICA = "gomma_plastica"
    VETRO = "vetro"

    # PRIORITY 4 - Public & Healthcare
    SANITA_PRIVATA = "sanita_privata"
    CASE_DI_CURA = "case_di_cura"
    FARMACIE_PRIVATE = "farmacie_private"
    ENTI_LOCALI = "enti_locali"
    MINISTERI = "ministeri"
    SCUOLA_PRIVATA = "scuola_privata"
    UNIVERSITA_PRIVATE = "universita_private"
    ENTI_DI_RICERCA = "enti_di_ricerca"

    # PRIORITY 5 - Media & Entertainment
    GIORNALISTI = "giornalisti"
    GRAFICI_EDITORIALI = "grafici_editoriali"
    CINEMA_AUDIOVISIVO = "cinema_audiovisivo"
    TEATRO = "teatro"
    RADIO_TV_PRIVATE = "radio_tv_private"

    # PRIORITY 6 - Other Essential Sectors
    AUTOTRASPORTO_MERCI = "autotrasporto_merci"
    AUTONOLEGGIO = "autonoleggio"
    AUTORIMESSE = "autorimesse"
    POMPE_FUNEBRI = "pompe_funebri"
    ACCONCIATURA_ESTETICA = "acconciatura_estetica"
    IMPIANTI_SPORTIVI = "impianti_sportivi"
    DIRIGENTI_INDUSTRIA = "dirigenti_industria"
    DIRIGENTI_COMMERCIO = "dirigenti_commercio"
    QUADRI = "quadri"

    def italian_name(self) -> str:
        """Get Italian display name for the sector."""
        names = {
            self.METALMECCANICI_INDUSTRIA: "Metalmeccanici Industria",
            self.METALMECCANICI_ARTIGIANI: "Metalmeccanici Artigiani",
            self.COMMERCIO_TERZIARIO: "Commercio e Terziario",
            self.EDILIZIA_INDUSTRIA: "Edilizia Industria",
            self.EDILIZIA_ARTIGIANATO: "Edilizia Artigianato",
            self.PUBBLICI_ESERCIZI: "Pubblici Esercizi",
            self.TURISMO: "Turismo",
            self.TRASPORTI_LOGISTICA: "Trasporti e Logistica",
            self.CHIMICI_FARMACEUTICI: "Chimici e Farmaceutici",
            self.TESSILI: "Tessili",
            self.TELECOMUNICAZIONI: "Telecomunicazioni",
            self.CREDITO_ASSICURAZIONI: "Credito e Assicurazioni",
            self.STUDI_PROFESSIONALI: "Studi Professionali",
            self.SERVIZI_PULIZIA: "Servizi di Pulizia e Multiservizi",
            self.VIGILANZA_PRIVATA: "Vigilanza Privata",
            self.ICT: "Information Technology",
            self.AGENZIE_VIAGGIO: "Agenzie di Viaggio",
            self.CALL_CENTER: "Call Center",
            self.COOPERATIVE_SOCIALI: "Cooperative Sociali",
            self.SERVIZI_EDUCATIVI: "Servizi Educativi",
            self.ALIMENTARI_INDUSTRIA: "Alimentari Industria",
            self.PANIFICAZIONE: "Panificazione",
            self.AGRICOLTURA: "Agricoltura",
            self.FLOROVIVAISTI: "Florovivaisti",
            self.LEGNO_ARREDAMENTO: "Legno e Arredamento",
            self.CARTA_GRAFICA: "Carta e Grafica",
            self.ENERGIA_PETROLIO: "Energia e Petrolio",
            self.GAS_ACQUA: "Gas e Acqua",
            self.GOMMA_PLASTICA: "Gomma e Plastica",
            self.VETRO: "Vetro",
            self.SANITA_PRIVATA: "Sanità Privata",
            self.CASE_DI_CURA: "Case di Cura",
            self.FARMACIE_PRIVATE: "Farmacie Private",
            self.ENTI_LOCALI: "Enti Locali",
            self.MINISTERI: "Ministeri",
            self.SCUOLA_PRIVATA: "Scuola Privata",
            self.UNIVERSITA_PRIVATE: "Università Private",
            self.ENTI_DI_RICERCA: "Enti di Ricerca",
            self.GIORNALISTI: "Giornalisti",
            self.GRAFICI_EDITORIALI: "Grafici Editoriali",
            self.CINEMA_AUDIOVISIVO: "Cinema e Audiovisivo",
            self.TEATRO: "Teatro",
            self.RADIO_TV_PRIVATE: "Radio e TV Private",
            self.AUTOTRASPORTO_MERCI: "Autotrasporto Merci",
            self.AUTONOLEGGIO: "Autonoleggio",
            self.AUTORIMESSE: "Autorimesse",
            self.POMPE_FUNEBRI: "Pompe Funebri",
            self.ACCONCIATURA_ESTETICA: "Acconciatura ed Estetica",
            self.IMPIANTI_SPORTIVI: "Impianti Sportivi",
            self.DIRIGENTI_INDUSTRIA: "Dirigenti Industria",
            self.DIRIGENTI_COMMERCIO: "Dirigenti Commercio",
            self.QUADRI: "Quadri",
        }
        return names.get(self, self.value.replace("_", " ").title())

    @classmethod
    def from_description(cls, description: str) -> "CCNLSector":
        """Create sector from description string."""
        desc_lower = description.lower()
        if "metalmeccanici" in desc_lower:
            return cls.METALMECCANICI_INDUSTRIA
        elif "commercio" in desc_lower:
            return cls.COMMERCIO_TERZIARIO
        elif "edilizia" in desc_lower:
            return cls.EDILIZIA_INDUSTRIA
        elif "turismo" in desc_lower:
            return cls.TURISMO
        elif "trasporti" in desc_lower:
            return cls.TRASPORTI_LOGISTICA
        else:
            return cls.COMMERCIO_TERZIARIO  # Default fallback

    def priority_level(self) -> int:
        """Get priority level for implementation order."""
        priority_1 = [
            self.METALMECCANICI_INDUSTRIA,
            self.METALMECCANICI_ARTIGIANI,
            self.COMMERCIO_TERZIARIO,
            self.EDILIZIA_INDUSTRIA,
            self.EDILIZIA_ARTIGIANATO,
            self.PUBBLICI_ESERCIZI,
            self.TURISMO,
            self.TRASPORTI_LOGISTICA,
            self.CHIMICI_FARMACEUTICI,
            self.TESSILI,
        ]
        priority_2 = [
            self.TELECOMUNICAZIONI,
            self.CREDITO_ASSICURAZIONI,
            self.STUDI_PROFESSIONALI,
            self.SERVIZI_PULIZIA,
            self.VIGILANZA_PRIVATA,
            self.ICT,
            self.AGENZIE_VIAGGIO,
            self.CALL_CENTER,
            self.COOPERATIVE_SOCIALI,
            self.SERVIZI_EDUCATIVI,
        ]
        priority_3 = [
            self.ALIMENTARI_INDUSTRIA,
            self.PANIFICAZIONE,
            self.AGRICOLTURA,
            self.FLOROVIVAISTI,
            self.LEGNO_ARREDAMENTO,
            self.CARTA_GRAFICA,
            self.ENERGIA_PETROLIO,
            self.GAS_ACQUA,
            self.GOMMA_PLASTICA,
            self.VETRO,
        ]
        priority_4 = [
            self.SANITA_PRIVATA,
            self.CASE_DI_CURA,
            self.FARMACIE_PRIVATE,
            self.ENTI_LOCALI,
            self.MINISTERI,
            self.SCUOLA_PRIVATA,
            self.UNIVERSITA_PRIVATE,
            self.ENTI_DI_RICERCA,
        ]
        priority_5 = [
            self.GIORNALISTI,
            self.GRAFICI_EDITORIALI,
            self.CINEMA_AUDIOVISIVO,
            self.TEATRO,
            self.RADIO_TV_PRIVATE,
        ]
        priority_6 = [
            self.AUTOTRASPORTO_MERCI,
            self.AUTONOLEGGIO,
            self.AUTORIMESSE,
            self.POMPE_FUNEBRI,
            self.ACCONCIATURA_ESTETICA,
            self.IMPIANTI_SPORTIVI,
            self.DIRIGENTI_INDUSTRIA,
            self.DIRIGENTI_COMMERCIO,
            self.QUADRI,
        ]

        if self in priority_1:
            return 1
        elif self in priority_2:
            return 2
        elif self in priority_3:
            return 3
        elif self in priority_4:
            return 4
        elif self in priority_5:
            return 5
        elif self in priority_6:
            return 6
        else:
            return 7  # Priority 7 and beyond


class WorkerCategory(str, Enum):
    """Enumeration of worker categories in Italian labor law."""

    OPERAIO = "operaio"
    IMPIEGATO = "impiegato"
    QUADRO = "quadro"
    DIRIGENTE = "dirigente"
    APPRENDISTA = "apprendista"

    def italian_name(self) -> str:
        """Get Italian display name."""
        names = {
            self.OPERAIO: "Operaio",
            self.IMPIEGATO: "Impiegato",
            self.QUADRO: "Quadro",
            self.DIRIGENTE: "Dirigente",
            self.APPRENDISTA: "Apprendista",
        }
        return names[self]

    def hierarchy_level(self) -> int:
        """Get hierarchy level (1=lowest, 4=highest)."""
        levels = {self.OPERAIO: 1, self.APPRENDISTA: 1, self.IMPIEGATO: 2, self.QUADRO: 3, self.DIRIGENTE: 4}
        return levels[self]


class GeographicArea(str, Enum):
    """Geographic areas for differentiated CCNL provisions."""

    NAZIONALE = "nazionale"
    NORD = "nord"
    CENTRO = "centro"
    SUD = "sud"
    SUD_ISOLE = "sud_isole"

    def includes_region(self, region: str) -> bool:
        """Check if area includes a specific region."""
        region_mapping = {
            self.NORD: [
                "lombardia",
                "piemonte",
                "veneto",
                "liguria",
                "emilia-romagna",
                "trentino",
                "valle-aosta",
                "friuli",
            ],
            self.CENTRO: ["toscana", "lazio", "umbria", "marche"],
            self.SUD: ["campania", "puglia", "calabria", "basilicata", "abruzzo", "molise"],
            self.SUD_ISOLE: ["sicilia", "sardegna"],
        }

        if self == self.NAZIONALE:
            return True

        return region.lower() in region_mapping.get(self, [])


class LeaveType(str, Enum):
    """Types of leave entitlements."""

    FERIE = "ferie"  # Vacation leave
    PERMESSI_RETRIBUITI = "permessi_retribuiti"  # Paid personal leave
    ROL_EX_FESTIVITA = "rol_ex_festivita"  # ROL (Riduzione Orario Lavoro)
    CONGEDO_MATERNITA = "congedo_maternita"  # Maternity leave
    CONGEDO_PATERNITA = "congedo_paternita"  # Paternity leave
    CONGEDO_PARENTALE = "congedo_parentale"  # Parental leave
    MALATTIA = "malattia"  # Sick leave
    INFORTUNIO = "infortunio"  # Work accident leave

    def italian_name(self) -> str:
        """Get Italian display name."""
        names = {
            self.FERIE: "Ferie",
            self.PERMESSI_RETRIBUITI: "Permessi Retribuiti",
            self.ROL_EX_FESTIVITA: "ROL/Ex-Festività",
            self.CONGEDO_MATERNITA: "Congedo di Maternità",
            self.CONGEDO_PATERNITA: "Congedo di Paternità",
            self.CONGEDO_PARENTALE: "Congedo Parentale",
            self.MALATTIA: "Malattia",
            self.INFORTUNIO: "Infortunio",
        }
        return names[self]


class AllowanceType(str, Enum):
    """Types of special allowances."""

    BUONI_PASTO = "buoni_pasto"  # Meal vouchers
    INDENNITA_TRASPORTO = "indennita_trasporto"  # Transport allowance
    INDENNITA_RISCHIO = "indennita_rischio"  # Risk/danger allowance
    INDENNITA_TURNO = "indennita_turno"  # Shift allowance
    INDENNITA_REPERIBILITA = "indennita_reperibilita"  # On-call allowance
    INDENNITA_TRASFERTA = "indennita_trasferta"  # Travel allowance
    INDENNITA_FUNZIONE = "indennita_funzione"  # Role/function allowance
    PREMIO_PRODUZIONE = "premio_produzione"  # Production bonus
    AUTO_AZIENDALE = "auto_aziendale"  # Company car allowance
    ASSEGNO_NUCLEO_FAMILIARE = "assegno_nucleo_familiare"  # Family allowance

    def italian_name(self) -> str:
        """Get Italian display name."""
        names = {
            self.BUONI_PASTO: "Buoni Pasto",
            self.INDENNITA_TRASPORTO: "Indennità di Trasporto",
            self.INDENNITA_RISCHIO: "Indennità di Rischio",
            self.INDENNITA_TURNO: "Indennità di Turno",
            self.INDENNITA_REPERIBILITA: "Indennità di Reperibilità",
            self.INDENNITA_TRASFERTA: "Indennità di Trasferta",
            self.INDENNITA_FUNZIONE: "Indennità di Funzione",
            self.PREMIO_PRODUZIONE: "Premio di Produzione",
            self.AUTO_AZIENDALE: "Auto Aziendale",
            self.ASSEGNO_NUCLEO_FAMILIARE: "Assegno per il Nucleo Familiare",
        }
        return names[self]


class CompanySize(str, Enum):
    """Company size categories affecting CCNL provisions."""

    MICRO = "micro"  # < 10 employees
    SMALL = "small"  # 10-49 employees
    MEDIUM = "medium"  # 50-249 employees
    LARGE = "large"  # 250+ employees

    def employee_range(self) -> tuple[int, int | None]:
        """Get employee count range for this size category."""
        ranges = {self.MICRO: (1, 9), self.SMALL: (10, 49), self.MEDIUM: (50, 249), self.LARGE: (250, None)}
        return ranges[self]


@dataclass
class JobLevel:
    """Represents a job level/classification within a CCNL."""

    level_code: str
    level_name: str
    category: WorkerCategory
    description: str | None = None
    minimum_experience_months: int = 0
    required_qualifications: list[str] = field(default_factory=list)
    typical_tasks: list[str] = field(default_factory=list)
    decision_making_level: str | None = None
    supervision_responsibilities: bool = False

    def is_lower_than(self, other: "JobLevel") -> bool:
        """Check if this level is lower than another."""
        # Simple comparison based on level codes (assumes alphanumeric ordering)
        return self.level_code < other.level_code

    def is_higher_than(self, other: "JobLevel") -> bool:
        """Check if this level is higher than another."""
        return self.level_code > other.level_code

    def is_higher_category_than(self, other: "JobLevel") -> bool:
        """Check if this level is in a higher category than another."""
        return self.category.hierarchy_level() > other.category.hierarchy_level()


@dataclass
class SalaryTable:
    """Represents salary information for a specific job level."""

    ccnl_sector: CCNLSector
    level_code: str
    base_monthly_salary: Decimal
    geographic_area: GeographicArea = GeographicArea.NAZIONALE
    valid_from: date | None = None
    valid_to: date | None = None
    thirteenth_month: bool = True
    fourteenth_month: bool = False
    additional_allowances: dict[str, Decimal] = field(default_factory=dict)
    company_size_adjustments: dict[CompanySize, Decimal] = field(default_factory=dict)

    def is_valid_on(self, check_date: date) -> bool:
        """Check if salary table is valid on a specific date."""
        if self.valid_from and check_date < self.valid_from:
            return False
        return not (self.valid_to and check_date > self.valid_to)

    def get_annual_salary(self) -> Decimal:
        """Get base annual salary (12 months)."""
        return self.base_monthly_salary * 12

    def get_total_monthly_salary(self) -> Decimal:
        """Get total monthly salary including additional allowances."""
        total = self.base_monthly_salary
        for allowance_amount in self.additional_allowances.values():
            total += allowance_amount
        return total

    def get_annual_salary_with_additional_months(self) -> Decimal:
        """Get annual salary including 13th and 14th month."""
        months = 12
        if self.thirteenth_month:
            months += 1
        if self.fourteenth_month:
            months += 1
        return self.base_monthly_salary * months


@dataclass
class WorkingHours:
    """Represents working hours configuration for a CCNL."""

    ccnl_sector: CCNLSector
    ordinary_weekly_hours: int
    maximum_weekly_hours: int = 48
    daily_rest_hours: int = 11
    weekly_rest_hours: int = 24
    flexible_hours_allowed: bool = False
    flexible_hours_range: tuple[int, int] | None = None  # (min, max) daily hours
    core_hours: tuple[str, str] | None = None  # ("09:00", "17:00")
    part_time_allowed: bool = True
    minimum_part_time_hours: int | None = None
    shift_work_allowed: bool = False
    shift_patterns: list[str] = field(default_factory=list)
    night_shift_allowance: Decimal | None = None

    def get_ordinary_daily_hours(self) -> float:
        """Get ordinary daily hours (assuming 5-day work week)."""
        return self.ordinary_weekly_hours / 5

    def get_min_flexible_daily_hours(self) -> int | None:
        """Get minimum daily hours in flexible arrangements."""
        return self.flexible_hours_range[0] if self.flexible_hours_range else None

    def get_max_flexible_daily_hours(self) -> int | None:
        """Get maximum daily hours in flexible arrangements."""
        return self.flexible_hours_range[1] if self.flexible_hours_range else None


@dataclass
class OvertimeRules:
    """Represents overtime rules and compensation."""

    ccnl_sector: CCNLSector
    daily_threshold_hours: int = 8
    weekly_threshold_hours: int = 40
    daily_overtime_rate: Decimal = Decimal("1.25")
    weekend_rate: Decimal = Decimal("1.50")
    holiday_rate: Decimal = Decimal("2.00")
    maximum_daily_overtime: int | None = None
    maximum_weekly_overtime: int | None = None
    maximum_monthly_overtime: int | None = None
    maximum_annual_overtime: int | None = None

    def calculate_overtime_pay(self, base_hourly_rate: Decimal, overtime_hours: int) -> Decimal:
        """Calculate overtime compensation."""
        return base_hourly_rate * self.daily_overtime_rate * overtime_hours

    def is_overtime_allowed(self, daily_hours: int, weekly_total: int) -> bool:
        """Check if overtime is allowed given daily and weekly totals."""
        if self.maximum_daily_overtime and daily_hours > self.maximum_daily_overtime:
            return False
        return not (self.maximum_weekly_overtime and weekly_total > self.maximum_weekly_overtime)


@dataclass
class LeaveEntitlement:
    """Represents leave entitlements for a specific type."""

    ccnl_sector: CCNLSector
    leave_type: LeaveType
    base_annual_days: int | None = None
    base_annual_hours: int | None = None
    seniority_bonus_schedule: dict[int, int] = field(default_factory=dict)  # months -> bonus days/hours
    calculation_method: str = "annual"  # "annual", "monthly_accrual", "hourly_accrual"
    minimum_usage_hours: int | None = None
    advance_notice_hours: int | None = None
    compensation_percentage: Decimal = Decimal("1.00")  # 100% salary
    mandatory_period: bool = False
    additional_optional_days: int | None = None

    def get_annual_entitlement(self, months_seniority: int) -> int:
        """Get total annual entitlement including seniority bonuses."""
        base = self.base_annual_days or 0

        # Add seniority bonuses - find highest threshold met
        highest_bonus = 0
        for threshold_months, bonus in sorted(self.seniority_bonus_schedule.items()):
            if months_seniority >= threshold_months:
                highest_bonus = bonus

        return base + highest_bonus

    def get_monthly_accrual(self) -> float:
        """Get monthly accrual amount."""
        if self.base_annual_hours:
            return self.base_annual_hours / 12
        elif self.base_annual_days:
            return self.base_annual_days / 12
        return 0.0


@dataclass
class NoticePerioD:
    """Represents notice period requirements."""

    ccnl_sector: CCNLSector
    worker_category: WorkerCategory
    seniority_months_min: int
    seniority_months_max: int
    notice_days: int
    termination_by: str = "both"  # "employer", "employee", "both"

    def applies_to_seniority(self, months_seniority: int) -> bool:
        """Check if this notice period applies to given seniority."""
        return self.seniority_months_min <= months_seniority <= self.seniority_months_max


@dataclass
class ProbationPeriod:
    """Represents probation period rules."""

    ccnl_sector: CCNLSector
    worker_category: WorkerCategory
    probation_days: int
    extensions_allowed: int = 0
    notice_during_probation: int = 0  # Days notice required during probation


@dataclass
class TFRRules:
    """Represents TFR (Trattamento di Fine Rapporto) severance rules."""

    ccnl_sector: CCNLSector
    calculation_method: str = "standard"  # "standard", "enhanced", "custom"
    annual_percentage: Decimal = Decimal("6.91")  # Standard 6.91% + 1.5% inflation
    includes_variable_pay: bool = True
    includes_allowances: bool = False
    maximum_monthly_basis: Decimal | None = None
    advance_payment_allowed: bool = True
    advance_percentage: Decimal = Decimal("70.0")  # Max advance 70%
    minimum_service_months: int = 96  # Minimum 8 years for advance


@dataclass
class DisciplinaryRule:
    """Represents disciplinary procedures and sanctions."""

    ccnl_sector: CCNLSector
    infraction_type: str  # "light", "serious", "grave"
    description: str
    sanctions: list[str] = field(
        default_factory=list
    )  # ["verbal_warning", "written_warning", "suspension", "dismissal"]
    procedure_days: int = 5  # Days for employee response
    appeal_allowed: bool = True
    union_assistance: bool = True


@dataclass
class WorkArrangementRules:
    """Represents work arrangement rules (part-time, temporary, remote work)."""

    ccnl_sector: CCNLSector
    part_time_allowed: bool = True
    part_time_minimum_hours: int | None = None
    part_time_maximum_percentage: int = 80  # Max 80% of full time
    temporary_work_allowed: bool = True
    temporary_max_duration_months: int = 24
    remote_work_allowed: bool = False
    remote_work_max_days_weekly: int = 0
    smart_working_provisions: bool = False
    flexible_entry_exit: bool = False
    job_sharing_allowed: bool = False


@dataclass
class ApprenticeshipRules:
    """Represents apprenticeship rules and provisions."""

    ccnl_sector: CCNLSector
    apprenticeship_types: list[str] = field(default_factory=list)  # ["professional", "higher_education", "research"]
    minimum_age: int = 15
    maximum_age: int = 29
    duration_months: int = 36
    salary_percentage: Decimal = Decimal("70.0")  # % of normal salary
    training_hours_annual: int = 120
    external_training_required: bool = True
    confirmation_rate_target: Decimal = Decimal("60.0")  # Target confirmation %


@dataclass
class TrainingRights:
    """Represents training rights and obligations."""

    ccnl_sector: CCNLSector
    individual_training_hours_annual: int = 20
    mandatory_training_paid: bool = True
    professional_development_fund: bool = False
    training_leave_days_annual: int = 5
    certification_support: bool = True
    language_training_support: bool = False
    digital_skills_training: bool = True
    career_development_programs: bool = False


@dataclass
class UnionRights:
    """Represents union rights and provisions."""

    ccnl_sector: CCNLSector
    union_representative_hours_monthly: int = 20
    union_assembly_hours_annual: int = 10
    union_office_space_required: bool = True
    union_information_board_required: bool = True
    union_dues_collection_allowed: bool = True
    strike_notice_hours: int = 24
    essential_services_strike_rules: bool = False


@dataclass
class SpecialAllowance:
    """Represents special allowances and benefits."""

    ccnl_sector: CCNLSector
    allowance_type: AllowanceType
    amount: Decimal
    frequency: str  # "daily", "monthly", "annual"
    conditions: list[str] = field(default_factory=list)
    job_levels: list[str] = field(default_factory=list)
    geographic_areas: list[GeographicArea] = field(default_factory=list)
    company_sizes: list[CompanySize] = field(default_factory=list)

    def get_monthly_amount(self, working_days: int = 22) -> Decimal:
        """Get monthly amount for this allowance."""
        if self.frequency == "monthly":
            return self.amount
        elif self.frequency == "daily":
            return self.amount * working_days
        elif self.frequency == "annual":
            return self.amount / 12
        return self.amount

    def applies_to_area(self, area: GeographicArea) -> bool:
        """Check if allowance applies to specific geographic area."""
        if not self.geographic_areas:
            return True
        return area in self.geographic_areas


@dataclass
class CCNLAgreement:
    """Represents a complete CCNL agreement."""

    sector: CCNLSector
    name: str
    valid_from: date
    valid_to: date | None = None
    signatory_unions: list[str] = field(default_factory=list)
    signatory_employers: list[str] = field(default_factory=list)
    renewal_status: str = "vigente"  # "vigente", "scaduto", "in_rinnovo"

    # Core CCNL components
    job_levels: list[JobLevel] = field(default_factory=list)
    salary_tables: list[SalaryTable] = field(default_factory=list)
    working_hours: WorkingHours | None = None
    overtime_rules: OvertimeRules | None = None
    leave_entitlements: list[LeaveEntitlement] = field(default_factory=list)
    notice_periods: list[NoticePerioD] = field(default_factory=list)
    probation_periods: list[ProbationPeriod] = field(default_factory=list)
    special_allowances: list[SpecialAllowance] = field(default_factory=list)

    # Enhanced CCNL components
    tfr_rules: TFRRules | None = None
    disciplinary_rules: list[DisciplinaryRule] = field(default_factory=list)
    work_arrangement_rules: WorkArrangementRules | None = None
    apprenticeship_rules: ApprenticeshipRules | None = None
    training_rights: TrainingRights | None = None
    union_rights: UnionRights | None = None

    # Metadata
    last_updated: datetime | None = None
    data_source: str | None = None
    verification_date: date | None = None

    def is_currently_valid(self) -> bool:
        """Check if CCNL is currently valid."""
        today = date.today()
        if today < self.valid_from:
            return False
        return not (self.valid_to and today > self.valid_to)

    def get_levels_by_category(self, category: WorkerCategory) -> list[JobLevel]:
        """Get all job levels for a specific worker category."""
        return [level for level in self.job_levels if level.category == category]

    def get_salary_for_level(
        self, level_code: str, area: GeographicArea = GeographicArea.NAZIONALE
    ) -> SalaryTable | None:
        """Get salary table for a specific level and area."""
        for salary in self.salary_tables:
            if salary.level_code == level_code and salary.geographic_area == area:
                if salary.is_valid_on(date.today()):
                    return salary
        return None

    def get_allowances_for_level(self, level_code: str) -> list[SpecialAllowance]:
        """Get applicable allowances for a job level."""
        applicable = []
        for allowance in self.special_allowances:
            if not allowance.job_levels or level_code in allowance.job_levels:
                applicable.append(allowance)
        return applicable


class CCNLCalculator:
    """Calculator for CCNL-based computations."""

    def __init__(self, ccnl: CCNLAgreement):
        """Initialize calculator with CCNL agreement."""
        self.ccnl = ccnl

    def calculate_annual_compensation(
        self,
        level_code: str,
        working_days_per_month: int = 22,
        include_allowances: bool = True,
        area: GeographicArea = GeographicArea.NAZIONALE,
    ) -> Decimal:
        """Calculate total annual compensation."""
        salary_table = self.ccnl.get_salary_for_level(level_code, area)
        if not salary_table:
            return Decimal("0.00")

        # Base salary with 13th/14th month
        annual_salary = salary_table.get_annual_salary_with_additional_months()

        if include_allowances:
            # Add allowances
            allowances = self.ccnl.get_allowances_for_level(level_code)
            for allowance in allowances:
                monthly_allowance = allowance.get_monthly_amount(working_days_per_month)
                annual_salary += monthly_allowance * 12

        return annual_salary

    def get_notice_period(self, worker_category: WorkerCategory, seniority_months: int) -> int | None:
        """Get notice period in days for given category and seniority."""
        for notice in self.ccnl.notice_periods:
            if notice.worker_category == worker_category and notice.applies_to_seniority(seniority_months):
                return notice.notice_days
        return None

    def calculate_annual_leave(self, leave_type: LeaveType, seniority_months: int) -> int | None:
        """Calculate annual leave entitlement."""
        for leave in self.ccnl.leave_entitlements:
            if leave.leave_type == leave_type:
                return leave.get_annual_entitlement(seniority_months)
        return None

    def calculate_overtime_pay(
        self, base_hourly_rate: Decimal, overtime_hours: int, is_weekend: bool = False, is_holiday: bool = False
    ) -> Decimal:
        """Calculate overtime compensation."""
        if not self.ccnl.overtime_rules:
            return Decimal("0.00")

        if is_holiday:
            rate = self.ccnl.overtime_rules.holiday_rate
        elif is_weekend:
            rate = self.ccnl.overtime_rules.weekend_rate
        else:
            rate = self.ccnl.overtime_rules.daily_overtime_rate

        return base_hourly_rate * rate * overtime_hours

    def calculate_thirteenth_fourteenth_month(
        self, level_code: str, months_worked: int = 12, area: GeographicArea = GeographicArea.NAZIONALE
    ) -> dict[str, Decimal]:
        """Calculate 13th and 14th month payments."""
        salary_table = self.ccnl.get_salary_for_level(level_code, area)
        if not salary_table:
            return {"thirteenth": Decimal("0.00"), "fourteenth": Decimal("0.00")}

        monthly_salary = salary_table.base_monthly_salary

        # Prorate based on months worked
        thirteenth = Decimal("0.00")
        fourteenth = Decimal("0.00")

        if salary_table.thirteenth_month:
            thirteenth = (monthly_salary / 12) * months_worked

        if salary_table.fourteenth_month:
            fourteenth = (monthly_salary / 12) * months_worked

        return {"thirteenth": thirteenth, "fourteenth": fourteenth}

    def get_probation_period(self, worker_category: WorkerCategory) -> int | None:
        """Get probation period in days for worker category."""
        for probation in self.ccnl.probation_periods:
            if probation.worker_category == worker_category:
                return probation.probation_days
        return None


# Utility functions for CCNL data management


def create_ccnl_id(sector: CCNLSector, valid_from: date) -> str:
    """Create standardized CCNL ID."""
    date_str = valid_from.strftime("%Y%m%d")
    return f"{sector.value}_{date_str}"


def compare_ccnl_provisions(ccnl1: CCNLAgreement, ccnl2: CCNLAgreement, provision_type: str) -> dict[str, Any]:
    """Compare specific provisions between two CCNLs."""
    differences: list[dict[str, Any]] = []
    comparison: dict[str, Any] = {
        "ccnl1": ccnl1.name,
        "ccnl2": ccnl2.name,
        "provision_type": provision_type,
        "differences": differences,
    }

    if provision_type == "leave_entitlements":
        for leave1 in ccnl1.leave_entitlements:
            for leave2 in ccnl2.leave_entitlements:
                if leave1.leave_type == leave2.leave_type:
                    if leave1.base_annual_days != leave2.base_annual_days:
                        differences.append(
                            {
                                "leave_type": leave1.leave_type.value,
                                "ccnl1_days": leave1.base_annual_days,
                                "ccnl2_days": leave2.base_annual_days,
                            }
                        )

    elif provision_type == "notice_periods":
        # Compare notice periods for same categories
        for notice1 in ccnl1.notice_periods:
            for notice2 in ccnl2.notice_periods:
                if (
                    notice1.worker_category == notice2.worker_category
                    and notice1.seniority_months_min == notice2.seniority_months_min
                ):
                    if notice1.notice_days != notice2.notice_days:
                        differences.append(
                            {
                                "category": notice1.worker_category.value,
                                "seniority_months": notice1.seniority_months_min,
                                "ccnl1_days": notice1.notice_days,
                                "ccnl2_days": notice2.notice_days,
                            }
                        )

    return comparison


def calculate_ccnl_coverage_percentage(covered_sectors: list[CCNLSector]) -> float:
    """Calculate what percentage of Italian workers are covered by implemented CCNLs."""
    # Approximate worker distribution by sector (based on ISTAT data)
    sector_worker_percentages = {
        CCNLSector.METALMECCANICI_INDUSTRIA: 8.5,
        CCNLSector.COMMERCIO_TERZIARIO: 12.0,
        CCNLSector.EDILIZIA_INDUSTRIA: 6.0,
        CCNLSector.PUBBLICI_ESERCIZI: 5.5,
        CCNLSector.TRASPORTI_LOGISTICA: 4.0,
        CCNLSector.TESSILI: 2.5,
        CCNLSector.CHIMICI_FARMACEUTICI: 3.0,
        CCNLSector.TURISMO: 4.5,
        # Add more sectors as needed
    }

    total_coverage = sum(sector_worker_percentages.get(sector, 0.0) for sector in covered_sectors)

    return min(total_coverage, 100.0)  # Cap at 100%
