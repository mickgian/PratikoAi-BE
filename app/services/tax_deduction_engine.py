"""
Italian Tax Deduction Rules and Timelines Engine.

This module provides comprehensive handling of Italian tax deductions with specific
rules, eligibility criteria, documentation requirements, and submission timelines.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from app.core.tax_constants import TAX_DEDUCTIONS_2024, TAX_CALENDAR_2024
from app.core.logging import logger


class DeductionCategory(str, Enum):
    """Categories of tax deductions."""
    WORK_RELATED = "work_related"
    FAMILY = "family"
    HEALTH = "health"
    EDUCATION = "education"
    CHARITY = "charity"
    HOME_RENOVATIONS = "home_renovations"
    PENSION = "pension"
    PROFESSIONAL = "professional"
    BUSINESS = "business"


class DeductionType(str, Enum):
    """Types of deduction calculations."""
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"
    PROGRESSIVE = "progressive"
    CAPPED_PERCENTAGE = "capped_percentage"


class DocumentType(str, Enum):
    """Required documentation types."""
    RECEIPT = "receipt"
    INVOICE = "invoice"
    CERTIFICATE = "certificate"
    BANK_STATEMENT = "bank_statement"
    MEDICAL_PRESCRIPTION = "medical_prescription"
    UNIVERSITY_ENROLLMENT = "university_enrollment"
    DONATION_RECEIPT = "donation_receipt"


@dataclass
class DeductionRule:
    """Complete deduction rule with eligibility and timeline."""
    id: str
    name: str
    category: DeductionCategory
    deduction_type: DeductionType
    
    # Financial parameters
    max_amount: Optional[Decimal]
    rate: Optional[Decimal]
    threshold: Optional[Decimal]
    income_cap: Optional[Decimal]
    
    # Timeline requirements
    expense_period_start: date
    expense_period_end: date
    submission_deadline: date
    payment_deadline: Optional[date]
    
    # Eligibility criteria
    min_income: Optional[Decimal]
    max_income: Optional[Decimal]
    age_restrictions: Optional[Tuple[int, int]]
    family_status_required: Optional[str]
    
    # Documentation requirements
    required_documents: List[DocumentType]
    retention_period_years: int
    
    # Special conditions
    conditions: List[str]
    exclusions: List[str]
    
    description: str
    legal_reference: str


class ItalianTaxDeductionEngine:
    """Comprehensive engine for Italian tax deductions with rules and timelines."""
    
    def __init__(self):
        self.deduction_rules = self._initialize_deduction_rules()
        self.current_year = datetime.now().year
        
    def _initialize_deduction_rules(self) -> Dict[str, DeductionRule]:
        """Initialize comprehensive deduction rules for 2024."""
        rules = {}
        
        # Medical Expenses Deductions
        rules["medical_basic"] = DeductionRule(
            id="medical_basic",
            name="Spese Mediche e Sanitarie",
            category=DeductionCategory.HEALTH,
            deduction_type=DeductionType.CAPPED_PERCENTAGE,
            max_amount=None,
            rate=Decimal("19"),
            threshold=Decimal("129.11"),
            income_cap=None,
            expense_period_start=date(2024, 1, 1),
            expense_period_end=date(2024, 12, 31),
            submission_deadline=date(2025, 7, 31),  # 730 deadline
            payment_deadline=None,
            min_income=None,
            max_income=None,
            age_restrictions=None,
            family_status_required=None,
            required_documents=[DocumentType.RECEIPT, DocumentType.MEDICAL_PRESCRIPTION],
            retention_period_years=5,
            conditions=[
                "Spese sostenute per sé, coniuge e familiari a carico",
                "Franchise di €129.11 applicabile",
                "Include: visite mediche, esami, medicine, protesi, occhiali"
            ],
            exclusions=[
                "Spese rimborsate da assicurazioni o SSN",
                "Medicine senza prescrizione medica (salvo casi specifici)"
            ],
            description="Detrazioni per spese mediche e sanitarie con detrazione 19%",
            legal_reference="Art. 15, comma 1, lett. c) TUIR"
        )
        
        # Home Renovation Deductions
        rules["ecobonus_65"] = DeductionRule(
            id="ecobonus_65",
            name="Ecobonus 65% - Efficienza Energetica",
            category=DeductionCategory.HOME_RENOVATIONS,
            deduction_type=DeductionType.PERCENTAGE,
            max_amount=Decimal("60000"),
            rate=Decimal("65"),
            threshold=None,
            income_cap=None,
            expense_period_start=date(2024, 1, 1),
            expense_period_end=date(2024, 12, 31),
            submission_deadline=date(2025, 2, 28),  # Comunicazione ENEA
            payment_deadline=None,
            min_income=None,
            max_income=None,
            age_restrictions=None,
            family_status_required=None,
            required_documents=[
                DocumentType.INVOICE,
                DocumentType.BANK_STATEMENT,
                DocumentType.CERTIFICATE
            ],
            retention_period_years=10,
            conditions=[
                "Interventi su unità immobiliari esistenti",
                "Comunicazione ENEA entro 90 giorni",
                "Pagamento tramite bonifico parlante",
                "Asseverazione tecnica obbligatoria"
            ],
            exclusions=[
                "Immobili di nuova costruzione",
                "Lavori iniziati prima del 1° gennaio 2024"
            ],
            description="Detrazione 65% per interventi di efficienza energetica",
            legal_reference="Art. 14 D.L. 63/2013, L. 90/2013"
        )
        
        rules["superbonus_90"] = DeductionRule(
            id="superbonus_90",
            name="Superbonus 90% - Anno 2024",
            category=DeductionCategory.HOME_RENOVATIONS,
            deduction_type=DeductionType.PERCENTAGE,
            max_amount=Decimal("96000"),
            rate=Decimal("90"),
            threshold=None,
            income_cap=Decimal("25000"),  # For 2024
            expense_period_start=date(2024, 1, 1),
            expense_period_end=date(2024, 12, 31),
            submission_deadline=date(2025, 2, 28),
            payment_deadline=None,
            min_income=None,
            max_income=Decimal("25000"),
            age_restrictions=None,
            family_status_required=None,
            required_documents=[
                DocumentType.INVOICE,
                DocumentType.BANK_STATEMENT,
                DocumentType.CERTIFICATE
            ],
            retention_period_years=10,
            conditions=[
                "ISEE non superiore a €25.000 per unifamiliari",
                "Interventi trainanti + trainati",
                "Miglioramento di almeno 2 classi energetiche",
                "Comunicazione ENEA entro 90 giorni",
                "Asseverazione tecnica e visto conformità obbligatori"
            ],
            exclusions=[
                "Seconde case (salvo condomini)",
                "ISEE superiore a €25.000",
                "Immobili di lusso categorie A/1, A/8, A/9"
            ],
            description="Superbonus 90% per efficienza energetica e sismica (2024)",
            legal_reference="Art. 119 D.L. 34/2020"
        )
        
        # Education Deductions
        rules["university_fees"] = DeductionRule(
            id="university_fees",
            name="Spese Universitarie",
            category=DeductionCategory.EDUCATION,
            deduction_type=DeductionType.CAPPED_PERCENTAGE,
            max_amount=Decimal("3700"),  # For private universities
            rate=Decimal("19"),
            threshold=None,
            income_cap=None,
            expense_period_start=date(2024, 1, 1),
            expense_period_end=date(2024, 12, 31),
            submission_deadline=date(2025, 7, 31),
            payment_deadline=None,
            min_income=None,
            max_income=None,
            age_restrictions=None,
            family_status_required=None,
            required_documents=[DocumentType.UNIVERSITY_ENROLLMENT, DocumentType.RECEIPT],
            retention_period_years=5,
            conditions=[
                "Tasse e contributi obbligatori",
                "Università statali: importo effettivo",
                "Università non statali: max €3.700",
                "Master e corsi post-laurea inclusi"
            ],
            exclusions=[
                "Tasse per esami integrativi",
                "Spese per alloggi e vitto"
            ],
            description="Detrazione 19% per spese universitarie",
            legal_reference="Art. 15, comma 1, lett. e) TUIR"
        )
        
        # Charity Donations
        rules["charity_donations"] = DeductionRule(
            id="charity_donations",
            name="Donazioni ONLUS e Enti Benefici",
            category=DeductionCategory.CHARITY,
            deduction_type=DeductionType.CAPPED_PERCENTAGE,
            max_amount=Decimal("70000"),
            rate=Decimal("30"),  # Alternative: 26% on total income
            threshold=None,
            income_cap=None,
            expense_period_start=date(2024, 1, 1),
            expense_period_end=date(2024, 12, 31),
            submission_deadline=date(2025, 7, 31),
            payment_deadline=None,
            min_income=None,
            max_income=None,
            age_restrictions=None,
            family_status_required=None,
            required_documents=[DocumentType.DONATION_RECEIPT],
            retention_period_years=5,
            conditions=[
                "ONLUS, OdV, APS, enti religiosi riconosciuti",
                "Versamento tramite banca, posta, carte di pagamento",
                "Ricevuta con codice fiscale dell'ente"
            ],
            exclusions=[
                "Donazioni in contanti",
                "Enti non qualificati",
                "Donazioni a partiti politici"
            ],
            description="Detrazione 30% per donazioni a ONLUS ed enti benefici",
            legal_reference="Art. 15, comma 1.1 TUIR"
        )
        
        # Family Deductions with Complex Rules
        rules["dependent_children"] = DeductionRule(
            id="dependent_children",
            name="Figli a Carico",
            category=DeductionCategory.FAMILY,
            deduction_type=DeductionType.PROGRESSIVE,
            max_amount=Decimal("1620"),  # Under 3 with disability
            rate=None,
            threshold=None,
            income_cap=Decimal("95000"),
            expense_period_start=date(2024, 1, 1),
            expense_period_end=date(2024, 12, 31),
            submission_deadline=date(2025, 7, 31),
            payment_deadline=None,
            min_income=None,
            max_income=Decimal("95000"),
            age_restrictions=None,
            family_status_required=None,
            required_documents=[DocumentType.CERTIFICATE],
            retention_period_years=5,
            conditions=[
                "Reddito complessivo figlio < €4.000 (o €2.840.51 se > 24 anni)",
                "Base: €950 per figlio",
                "Maggiorazione €270 se età < 3 anni",
                "Maggiorazione €400 se disabile",
                "Detrazione spetta al 50% per ciascun genitore"
            ],
            exclusions=[
                "Reddito genitori > €95.000",
                "Figlio con reddito superiore ai limiti"
            ],
            description="Detrazioni per figli fiscalmente a carico",
            legal_reference="Art. 12 TUIR"
        )
        
        # Professional Expenses
        rules["professional_training"] = DeductionRule(
            id="professional_training",
            name="Spese Formazione Professionale",
            category=DeductionCategory.PROFESSIONAL,
            deduction_type=DeductionType.PERCENTAGE,
            max_amount=Decimal("10000"),
            rate=Decimal("19"),
            threshold=None,
            income_cap=None,
            expense_period_start=date(2024, 1, 1),
            expense_period_end=date(2024, 12, 31),
            submission_deadline=date(2025, 7, 31),
            payment_deadline=None,
            min_income=None,
            max_income=None,
            age_restrictions=(18, 65),
            family_status_required=None,
            required_documents=[DocumentType.INVOICE, DocumentType.CERTIFICATE],
            retention_period_years=5,
            conditions=[
                "Corsi di formazione, aggiornamento, qualificazione",
                "Finalizzati all'attività lavorativa",
                "Enti riconosciuti o università",
                "Include spese di iscrizione e frequenza"
            ],
            exclusions=[
                "Corsi non inerenti l'attività professionale",
                "Spese per hobby o svago"
            ],
            description="Detrazione 19% per spese di formazione professionale",
            legal_reference="Art. 15, comma 1, lett. i-octies) TUIR"
        )
        
        return rules
    
    def get_eligible_deductions(
        self,
        income: Decimal,
        family_status: str = "single",
        age: int = 35,
        has_dependents: bool = False
    ) -> List[DeductionRule]:
        """Get all eligible deductions based on taxpayer profile."""
        eligible = []
        
        for rule in self.deduction_rules.values():
            if self._check_eligibility(rule, income, family_status, age, has_dependents):
                eligible.append(rule)
        
        return eligible
    
    def _check_eligibility(
        self,
        rule: DeductionRule,
        income: Decimal,
        family_status: str,
        age: int,
        has_dependents: bool
    ) -> bool:
        """Check if taxpayer is eligible for specific deduction."""
        
        # Income checks
        if rule.min_income and income < rule.min_income:
            return False
        if rule.max_income and income > rule.max_income:
            return False
        
        # Age restrictions
        if rule.age_restrictions:
            min_age, max_age = rule.age_restrictions
            if age < min_age or age > max_age:
                return False
        
        # Family status requirements
        if rule.family_status_required:
            if family_status != rule.family_status_required:
                return False
        
        return True
    
    def calculate_deduction_amount(
        self,
        rule_id: str,
        expense_amount: Decimal,
        income: Decimal = None,
        additional_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Calculate the actual deduction amount for a specific rule."""
        
        rule = self.deduction_rules.get(rule_id)
        if not rule:
            raise ValueError(f"Deduction rule {rule_id} not found")
        
        result = {
            "rule_id": rule_id,
            "rule_name": rule.name,
            "expense_amount": float(expense_amount),
            "deduction_type": rule.deduction_type.value,
            "deductible_amount": Decimal("0"),
            "tax_savings": Decimal("0"),
            "applicable_rate": rule.rate,
            "conditions_met": True,
            "warnings": [],
            "next_deadline": None
        }
        
        # Apply threshold if exists
        if rule.threshold:
            if expense_amount <= rule.threshold:
                result["deductible_amount"] = Decimal("0")
                result["conditions_met"] = False
                result["warnings"].append(f"Expense below threshold of €{rule.threshold}")
                return result
            expense_amount = expense_amount - rule.threshold
        
        # Calculate based on deduction type
        if rule.deduction_type == DeductionType.PERCENTAGE:
            deductible = expense_amount * (rule.rate / 100)
        elif rule.deduction_type == DeductionType.FIXED_AMOUNT:
            deductible = rule.rate  # In this case, rate is the fixed amount
        elif rule.deduction_type == DeductionType.CAPPED_PERCENTAGE:
            deductible = expense_amount * (rule.rate / 100)
        else:  # Progressive
            deductible = self._calculate_progressive_deduction(rule, expense_amount, additional_params)
        
        # Apply maximum cap
        if rule.max_amount and deductible > rule.max_amount:
            deductible = rule.max_amount
            result["warnings"].append(f"Deduction capped at maximum €{rule.max_amount}")
        
        result["deductible_amount"] = float(deductible.quantize(Decimal('0.01'), ROUND_HALF_UP))
        
        # Calculate tax savings (assuming average 35% marginal rate)
        marginal_rate = self._estimate_marginal_rate(income) if income else Decimal("35")
        result["tax_savings"] = float((deductible * marginal_rate / 100).quantize(Decimal('0.01'), ROUND_HALF_UP))
        
        # Add timeline information
        result["next_deadline"] = rule.submission_deadline.isoformat()
        
        return result
    
    def _calculate_progressive_deduction(
        self,
        rule: DeductionRule,
        expense_amount: Decimal,
        additional_params: Dict[str, Any]
    ) -> Decimal:
        """Calculate progressive deduction (complex family deductions)."""
        
        if rule.id == "dependent_children":
            # Base deduction
            base_deduction = Decimal("950")
            
            # Age bonus
            if additional_params and additional_params.get("child_age", 0) < 3:
                base_deduction += Decimal("270")
            
            # Disability bonus
            if additional_params and additional_params.get("disabled", False):
                base_deduction += Decimal("400")
            
            return base_deduction
        
        return expense_amount * (rule.rate / 100) if rule.rate else Decimal("0")
    
    def _estimate_marginal_rate(self, income: Decimal) -> Decimal:
        """Estimate marginal tax rate based on income."""
        if income <= 15000:
            return Decimal("23")
        elif income <= 28000:
            return Decimal("25")
        elif income <= 55000:
            return Decimal("35")
        else:
            return Decimal("43")
    
    def get_upcoming_deadlines(self, days_ahead: int = 90) -> List[Dict[str, Any]]:
        """Get upcoming deduction-related deadlines."""
        cutoff_date = datetime.now().date() + timedelta(days=days_ahead)
        deadlines = []
        
        for rule in self.deduction_rules.values():
            if rule.submission_deadline <= cutoff_date:
                days_left = (rule.submission_deadline - datetime.now().date()).days
                
                deadlines.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "deadline": rule.submission_deadline.isoformat(),
                    "days_left": days_left,
                    "category": rule.category.value,
                    "urgency": "urgent" if days_left <= 30 else "moderate" if days_left <= 60 else "normal",
                    "required_documents": [doc.value for doc in rule.required_documents]
                })
        
        return sorted(deadlines, key=lambda x: x["days_left"])
    
    def get_deduction_documentation_requirements(self, rule_id: str) -> Dict[str, Any]:
        """Get detailed documentation requirements for a deduction."""
        rule = self.deduction_rules.get(rule_id)
        if not rule:
            return {"error": "Rule not found"}
        
        return {
            "rule_name": rule.name,
            "required_documents": [doc.value for doc in rule.required_documents],
            "retention_period_years": rule.retention_period_years,
            "submission_deadline": rule.submission_deadline.isoformat(),
            "conditions": rule.conditions,
            "exclusions": rule.exclusions,
            "legal_reference": rule.legal_reference,
            "documentation_tips": self._get_documentation_tips(rule)
        }
    
    def _get_documentation_tips(self, rule: DeductionRule) -> List[str]:
        """Get documentation tips for a specific deduction."""
        tips = []
        
        if DocumentType.RECEIPT in rule.required_documents:
            tips.append("Conservare ricevute fiscali originali con data, importo e causale")
        
        if DocumentType.BANK_STATEMENT in rule.required_documents:
            tips.append("Utilizzare bonifico parlante con causale specifica per lavori edilizi")
        
        if DocumentType.MEDICAL_PRESCRIPTION in rule.required_documents:
            tips.append("Necessaria prescrizione medica per farmaci e dispositivi medici")
        
        if rule.category == DeductionCategory.HOME_RENOVATIONS:
            tips.extend([
                "Comunicazione ENEA entro 90 giorni dalla fine lavori",
                "Asseverazione tecnica obbligatoria per alcuni interventi",
                "Fatture elettroniche obbligatorie"
            ])
        
        return tips
    
    def validate_deduction_claim(
        self,
        rule_id: str,
        expense_amount: Decimal,
        expense_date: date,
        taxpayer_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a deduction claim against rules and deadlines."""
        rule = self.deduction_rules.get(rule_id)
        if not rule:
            return {"valid": False, "error": "Rule not found"}
        
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        # Date validation
        if expense_date < rule.expense_period_start or expense_date > rule.expense_period_end:
            validation_result["errors"].append(
                f"Expense date must be between {rule.expense_period_start} and {rule.expense_period_end}"
            )
            validation_result["valid"] = False
        
        # Submission deadline
        if datetime.now().date() > rule.submission_deadline:
            validation_result["errors"].append(
                f"Submission deadline ({rule.submission_deadline}) has passed"
            )
            validation_result["valid"] = False
        
        # Amount validation
        if rule.max_amount and expense_amount > rule.max_amount:
            validation_result["warnings"].append(
                f"Expense exceeds maximum deductible amount of €{rule.max_amount}"
            )
        
        # Eligibility check
        if not self._check_eligibility(
            rule,
            taxpayer_profile.get("income", Decimal("0")),
            taxpayer_profile.get("family_status", "single"),
            taxpayer_profile.get("age", 35),
            taxpayer_profile.get("has_dependents", False)
        ):
            validation_result["errors"].append("Taxpayer not eligible for this deduction")
            validation_result["valid"] = False
        
        return validation_result


# Singleton instance
deduction_engine = ItalianTaxDeductionEngine()