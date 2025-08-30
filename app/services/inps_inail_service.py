"""
INPS/INAIL Integration Service for Italian social security contributions.

This service handles the integration with INPS (Istituto Nazionale della Previdenza Sociale)
and INAIL (Istituto Nazionale per l'Assicurazione contro gli Infortuni sul Lavoro)
contribution rates and calculations.
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import logging

from app.models.ccnl_data import CCNLSector, WorkerCategory

logger = logging.getLogger(__name__)


class ContributionType(str, Enum):
    """Types of social security contributions."""
    INPS_EMPLOYEE = "inps_employee"  # INPS employee contribution
    INPS_EMPLOYER = "inps_employer"  # INPS employer contribution
    INAIL_EMPLOYER = "inail_employer"  # INAIL employer contribution (only employer pays)
    ADDITIONAL_CONTRIBUTIONS = "additional_contributions"  # Additional sector-specific contributions


class RiskClass(str, Enum):
    """INAIL risk classes for different sectors."""
    CLASS_1 = "class_1"  # Low risk (offices, commerce)
    CLASS_2 = "class_2"  # Medium-low risk (light industry)
    CLASS_3 = "class_3"  # Medium risk (manufacturing)
    CLASS_4 = "class_4"  # High risk (construction, chemicals)
    CLASS_5 = "class_5"  # Very high risk (mining, heavy industry)


@dataclass
class ContributionRate:
    """Represents a contribution rate."""
    contribution_type: ContributionType
    rate_percentage: Decimal
    applicable_sectors: List[CCNLSector]
    worker_categories: List[WorkerCategory]
    min_contribution: Optional[Decimal] = None
    max_contribution: Optional[Decimal] = None
    valid_from: date = None
    valid_to: Optional[date] = None
    description: str = ""
    
    def __post_init__(self):
        if self.valid_from is None:
            self.valid_from = date(2024, 1, 1)


@dataclass
class INAILRate:
    """INAIL contribution rate based on risk class."""
    risk_class: RiskClass
    base_rate: Decimal
    sectors: List[CCNLSector]
    valid_from: date
    valid_to: Optional[date] = None
    
    def get_effective_rate(self, company_size: str = "medium") -> Decimal:
        """Get effective INAIL rate based on company characteristics."""
        rate = self.base_rate
        
        # Small companies (< 10 employees) may have reduced rates
        if company_size == "small":
            rate *= Decimal('0.95')
        
        # Large companies (> 250 employees) may have additional charges
        elif company_size == "large":
            rate *= Decimal('1.05')
        
        return rate


@dataclass
class ContributionCalculation:
    """Result of contribution calculation."""
    gross_salary: Decimal
    inps_employee: Decimal
    inps_employer: Decimal
    inail_employer: Decimal
    total_employee_contributions: Decimal
    total_employer_contributions: Decimal
    net_salary: Decimal
    contribution_breakdown: Dict[str, Decimal]
    sector: CCNLSector
    worker_category: WorkerCategory
    calculation_date: date


class INPSINAILService:
    """Service for INPS/INAIL contribution management."""
    
    def __init__(self):
        self.contribution_rates = self._initialize_contribution_rates()
        self.inail_rates = self._initialize_inail_rates()
        self.sector_risk_mapping = self._initialize_sector_risk_mapping()
    
    def _initialize_contribution_rates(self) -> Dict[ContributionType, ContributionRate]:
        """Initialize current INPS contribution rates."""
        rates = {
            ContributionType.INPS_EMPLOYEE: ContributionRate(
                contribution_type=ContributionType.INPS_EMPLOYEE,
                rate_percentage=Decimal('9.19'),  # Standard employee rate
                applicable_sectors=list(CCNLSector),
                worker_categories=[WorkerCategory.OPERAIO, WorkerCategory.IMPIEGATO],
                description="Contributi INPS a carico del lavoratore"
            ),
            ContributionType.INPS_EMPLOYER: ContributionRate(
                contribution_type=ContributionType.INPS_EMPLOYER,
                rate_percentage=Decimal('23.81'),  # Standard employer rate
                applicable_sectors=list(CCNLSector),
                worker_categories=[WorkerCategory.OPERAIO, WorkerCategory.IMPIEGATO],
                description="Contributi INPS a carico del datore di lavoro"
            )
        }
        
        # Special rates for quadri (middle management)
        rates[f"{ContributionType.INPS_EMPLOYEE}_quadri"] = ContributionRate(
            contribution_type=ContributionType.INPS_EMPLOYEE,
            rate_percentage=Decimal('9.49'),
            applicable_sectors=list(CCNLSector),
            worker_categories=[WorkerCategory.QUADRO],
            description="Contributi INPS quadri a carico del lavoratore"
        )
        
        rates[f"{ContributionType.INPS_EMPLOYER}_quadri"] = ContributionRate(
            contribution_type=ContributionType.INPS_EMPLOYER,
            rate_percentage=Decimal('24.11'),
            applicable_sectors=list(CCNLSector),
            worker_categories=[WorkerCategory.QUADRO],
            description="Contributi INPS quadri a carico del datore di lavoro"
        )
        
        return rates
    
    def _initialize_inail_rates(self) -> Dict[RiskClass, INAILRate]:
        """Initialize INAIL rates by risk class."""
        return {
            RiskClass.CLASS_1: INAILRate(
                risk_class=RiskClass.CLASS_1,
                base_rate=Decimal('0.65'),  # 0.65% for low-risk activities
                sectors=[
                    CCNLSector.COMMERCIO_TERZIARIO,
                    CCNLSector.TELECOMUNICAZIONI,
                    CCNLSector.CREDITO_ASSICURAZIONI,
                    CCNLSector.STUDI_PROFESSIONALI,
                    CCNLSector.ICT
                ],
                valid_from=date(2024, 1, 1)
            ),
            RiskClass.CLASS_2: INAILRate(
                risk_class=RiskClass.CLASS_2,
                base_rate=Decimal('1.15'),  # 1.15% for medium-low risk
                sectors=[
                    CCNLSector.ALIMENTARI_INDUSTRIA,
                    CCNLSector.TESSILI,
                    CCNLSector.PUBBLICI_ESERCIZI,
                    CCNLSector.TURISMO
                ],
                valid_from=date(2024, 1, 1)
            ),
            RiskClass.CLASS_3: INAILRate(
                risk_class=RiskClass.CLASS_3,
                base_rate=Decimal('2.15'),  # 2.15% for medium risk
                sectors=[
                    CCNLSector.METALMECCANICI_INDUSTRIA,
                    CCNLSector.METALMECCANICI_ARTIGIANI,
                    CCNLSector.LEGNO_ARREDAMENTO,
                    CCNLSector.CARTA_GRAFICA
                ],
                valid_from=date(2024, 1, 1)
            ),
            RiskClass.CLASS_4: INAILRate(
                risk_class=RiskClass.CLASS_4,
                base_rate=Decimal('3.65'),  # 3.65% for high risk
                sectors=[
                    CCNLSector.EDILIZIA_INDUSTRIA,
                    CCNLSector.EDILIZIA_ARTIGIANATO,
                    CCNLSector.CHIMICI_FARMACEUTICI,
                    CCNLSector.ENERGIA_PETROLIO
                ],
                valid_from=date(2024, 1, 1)
            ),
            RiskClass.CLASS_5: INAILRate(
                risk_class=RiskClass.CLASS_5,
                base_rate=Decimal('5.85'),  # 5.85% for very high risk
                sectors=[
                    CCNLSector.TRASPORTI_LOGISTICA,
                    CCNLSector.AUTOTRASPORTO_MERCI,
                    CCNLSector.GOMMA_PLASTICA
                ],
                valid_from=date(2024, 1, 1)
            )
        }
    
    def _initialize_sector_risk_mapping(self) -> Dict[CCNLSector, RiskClass]:
        """Create mapping between sectors and INAIL risk classes."""
        mapping = {}
        
        for risk_class, inail_rate in self.inail_rates.items():
            for sector in inail_rate.sectors:
                mapping[sector] = risk_class
        
        return mapping
    
    async def get_contribution_rates(self, sector: CCNLSector, worker_category: WorkerCategory) -> Dict[str, Decimal]:
        """Get applicable contribution rates for a sector and worker category."""
        rates = {}
        
        # INPS rates
        if worker_category == WorkerCategory.QUADRO:
            rates["inps_employee"] = self.contribution_rates[f"{ContributionType.INPS_EMPLOYEE}_quadri"].rate_percentage
            rates["inps_employer"] = self.contribution_rates[f"{ContributionType.INPS_EMPLOYER}_quadri"].rate_percentage
        elif worker_category in [WorkerCategory.OPERAIO, WorkerCategory.IMPIEGATO]:
            rates["inps_employee"] = self.contribution_rates[ContributionType.INPS_EMPLOYEE].rate_percentage
            rates["inps_employer"] = self.contribution_rates[ContributionType.INPS_EMPLOYER].rate_percentage
        else:  # DIRIGENTE
            rates["inps_employee"] = Decimal('0.00')  # Dirigenti have separate pension schemes
            rates["inps_employer"] = Decimal('0.00')
        
        # INAIL rates (only employer pays)
        risk_class = self.sector_risk_mapping.get(sector, RiskClass.CLASS_2)
        inail_rate = self.inail_rates[risk_class]
        rates["inail_employer"] = inail_rate.get_effective_rate()
        
        return rates
    
    async def calculate_contributions(
        self,
        gross_salary: Decimal,
        sector: CCNLSector,
        worker_category: WorkerCategory,
        company_size: str = "medium"
    ) -> ContributionCalculation:
        """Calculate total contributions for a given salary and sector."""
        
        # Get contribution rates
        rates = await self.get_contribution_rates(sector, worker_category)
        
        # Calculate contributions
        inps_employee = gross_salary * (rates.get("inps_employee", Decimal('0')) / Decimal('100'))
        inps_employer = gross_salary * (rates.get("inps_employer", Decimal('0')) / Decimal('100'))
        inail_employer = gross_salary * (rates.get("inail_employer", Decimal('0')) / Decimal('100'))
        
        # Additional contributions (TFR, etc.)
        tfr_contribution = gross_salary * Decimal('0.0691')  # 6.91% TFR
        
        total_employee = inps_employee
        total_employer = inps_employer + inail_employer + tfr_contribution
        net_salary = gross_salary - total_employee
        
        contribution_breakdown = {
            "inps_employee": inps_employee,
            "inps_employer": inps_employer,
            "inail_employer": inail_employer,
            "tfr_contribution": tfr_contribution,
            "total_employee": total_employee,
            "total_employer": total_employer
        }
        
        return ContributionCalculation(
            gross_salary=gross_salary,
            inps_employee=inps_employee,
            inps_employer=inps_employer,
            inail_employer=inail_employer,
            total_employee_contributions=total_employee,
            total_employer_contributions=total_employer,
            net_salary=net_salary,
            contribution_breakdown=contribution_breakdown,
            sector=sector,
            worker_category=worker_category,
            calculation_date=date.today()
        )
    
    async def get_sector_risk_class(self, sector: CCNLSector) -> RiskClass:
        """Get INAIL risk class for a sector."""
        return self.sector_risk_mapping.get(sector, RiskClass.CLASS_2)
    
    async def update_contribution_rates(self, new_rates: Dict[ContributionType, Decimal]):
        """Update contribution rates (e.g., when government changes rates)."""
        logger.info("Updating INPS/INAIL contribution rates")
        
        for contribution_type, rate in new_rates.items():
            if contribution_type in self.contribution_rates:
                old_rate = self.contribution_rates[contribution_type].rate_percentage
                self.contribution_rates[contribution_type].rate_percentage = rate
                logger.info(f"Updated {contribution_type.value} rate from {old_rate}% to {rate}%")
    
    async def get_contribution_history(self, sector: CCNLSector) -> List[Dict[str, Any]]:
        """Get historical contribution rates for a sector."""
        # In a real implementation, this would query historical data
        return [
            {
                "year": 2024,
                "inps_employee": Decimal('9.19'),
                "inps_employer": Decimal('23.81'),
                "inail_rate": self.inail_rates[self.sector_risk_mapping[sector]].base_rate,
                "changes": []
            },
            {
                "year": 2023,
                "inps_employee": Decimal('9.19'),
                "inps_employer": Decimal('23.81'),
                "inail_rate": self.inail_rates[self.sector_risk_mapping[sector]].base_rate,
                "changes": ["Updated INAIL base rates"]
            }
        ]
    
    async def validate_contribution_calculation(self, calculation: ContributionCalculation) -> bool:
        """Validate a contribution calculation for accuracy."""
        # Recalculate and compare
        recalc = await self.calculate_contributions(
            calculation.gross_salary,
            calculation.sector,
            calculation.worker_category
        )
        
        tolerance = Decimal('0.01')  # 1 cent tolerance
        
        return (
            abs(calculation.inps_employee - recalc.inps_employee) <= tolerance and
            abs(calculation.inps_employer - recalc.inps_employer) <= tolerance and
            abs(calculation.inail_employer - recalc.inail_employer) <= tolerance
        )
    
    async def get_annual_contribution_summary(
        self,
        sector: CCNLSector,
        worker_category: WorkerCategory,
        annual_salary: Decimal
    ) -> Dict[str, Any]:
        """Get annual contribution summary."""
        monthly_salary = annual_salary / Decimal('12')
        monthly_calc = await self.calculate_contributions(monthly_salary, sector, worker_category)
        
        return {
            "sector": sector.italian_name(),
            "worker_category": worker_category.value,
            "annual_gross_salary": annual_salary,
            "monthly_gross_salary": monthly_salary,
            "annual_contributions": {
                "inps_employee": monthly_calc.inps_employee * 12,
                "inps_employer": monthly_calc.inps_employer * 12,
                "inail_employer": monthly_calc.inail_employer * 12,
                "total_employee": monthly_calc.total_employee_contributions * 12,
                "total_employer": monthly_calc.total_employer_contributions * 12
            },
            "contribution_rates": await self.get_contribution_rates(sector, worker_category),
            "risk_class": await self.get_sector_risk_class(sector)
        }


# Global instance
inps_inail_service = INPSINAILService()