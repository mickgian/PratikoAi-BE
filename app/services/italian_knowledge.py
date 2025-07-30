"""Italian knowledge service for tax calculations and legal compliance."""

import re
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from sqlmodel import select
from sqlalchemy.exc import NoResultFound

from app.core.logging import logger
from app.services.database import database_service
from app.models.italian_data import (
    ItalianTaxRate, ItalianLegalTemplate, ItalianRegulation, 
    TaxCalculation, ComplianceCheck, ItalianKnowledgeSource,
    TaxType, DocumentType, ComplianceStatus
)


class ItalianTaxCalculator:
    """Italian tax calculation utilities."""
    
    # 2024 IRPEF (Income Tax) brackets for individuals
    IRPEF_BRACKETS_2024 = [
        {"min": 0, "max": 15000, "rate": 0.23},
        {"min": 15001, "max": 28000, "rate": 0.25},
        {"min": 28001, "max": 50000, "rate": 0.35},
        {"min": 50001, "max": float('inf'), "rate": 0.43}
    ]
    
    # Standard VAT rates
    VAT_RATES = {
        "standard": 0.22,  # 22%
        "reduced": 0.10,   # 10%
        "super_reduced": 0.04,  # 4%
        "zero": 0.00       # 0%
    }
    
    # Regional IRAP rates (approximate, varies by region)
    IRAP_RATE_DEFAULT = 0.0398  # 3.98%
    
    def calculate_vat(self, amount: float, vat_type: str = "standard") -> Dict[str, Any]:
        """Calculate Italian VAT (IVA).
        
        Args:
            amount: Net amount before VAT
            vat_type: VAT rate type (standard, reduced, super_reduced, zero)
            
        Returns:
            Dictionary with VAT calculation details
        """
        try:
            rate = self.VAT_RATES.get(vat_type, self.VAT_RATES["standard"])
            vat_amount = Decimal(str(amount)) * Decimal(str(rate))
            gross_amount = Decimal(str(amount)) + vat_amount
            
            return {
                "net_amount": float(amount),
                "vat_rate": rate,
                "vat_amount": float(vat_amount),
                "gross_amount": float(gross_amount),
                "vat_type": vat_type,
                "calculation_date": datetime.utcnow().isoformat(),
                "legal_reference": "DPR 633/1972 - Italian VAT Law"
            }
            
        except Exception as e:
            logger.error("vat_calculation_failed", error=str(e), amount=amount, vat_type=vat_type)
            raise ValueError(f"VAT calculation failed: {str(e)}")
    
    def calculate_irpef(self, income: float, deductions: float = 0) -> Dict[str, Any]:
        """Calculate Italian personal income tax (IRPEF).
        
        Args:
            income: Annual gross income
            deductions: Total deductions
            
        Returns:
            Dictionary with IRPEF calculation details
        """
        try:
            taxable_income = max(0, income - deductions)
            total_tax = Decimal('0')
            breakdown = []
            
            for bracket in self.IRPEF_BRACKETS_2024:
                if taxable_income <= bracket["min"]:
                    break
                    
                bracket_max = min(taxable_income, bracket["max"])
                bracket_income = bracket_max - bracket["min"] + 1
                bracket_tax = Decimal(str(bracket_income)) * Decimal(str(bracket["rate"]))
                total_tax += bracket_tax
                
                breakdown.append({
                    "bracket": f"€{bracket['min']:,} - €{bracket['max']:,}" if bracket['max'] != float('inf') else f"€{bracket['min']:,}+",
                    "rate": bracket["rate"],
                    "taxable_amount": float(bracket_income),
                    "tax_amount": float(bracket_tax)
                })
                
                if taxable_income <= bracket["max"]:
                    break
            
            effective_rate = float(total_tax / Decimal(str(taxable_income))) if taxable_income > 0 else 0
            
            return {
                "gross_income": income,
                "deductions": deductions,
                "taxable_income": taxable_income,
                "total_tax": float(total_tax),
                "effective_rate": effective_rate,
                "breakdown": breakdown,
                "calculation_date": datetime.utcnow().isoformat(),
                "legal_reference": "TUIR (Testo Unico Imposte sui Redditi) - DPR 917/1986"
            }
            
        except Exception as e:
            logger.error("irpef_calculation_failed", error=str(e), income=income, deductions=deductions)
            raise ValueError(f"IRPEF calculation failed: {str(e)}")
    
    def calculate_withholding_tax(self, amount: float, tax_type: str = "professional") -> Dict[str, Any]:
        """Calculate Italian withholding tax (Ritenuta d'acconto).
        
        Args:
            amount: Gross amount subject to withholding
            tax_type: Type of withholding (professional, employment, etc.)
            
        Returns:
            Dictionary with withholding tax calculation
        """
        try:
            # Standard rates for different types
            rates = {
                "professional": 0.20,  # 20% for professionals
                "employment": 0.23,    # 23% for employment (varies by bracket)
                "rental": 0.21,        # 21% for rental income
                "interest": 0.26,      # 26% for interest income
                "dividends": 0.26      # 26% for dividends
            }
            
            rate = rates.get(tax_type, rates["professional"])
            withholding_amount = Decimal(str(amount)) * Decimal(str(rate))
            net_amount = Decimal(str(amount)) - withholding_amount
            
            return {
                "gross_amount": amount,
                "withholding_rate": rate,
                "withholding_amount": float(withholding_amount),
                "net_amount": float(net_amount),
                "tax_type": tax_type,
                "calculation_date": datetime.utcnow().isoformat(),
                "legal_reference": "DPR 600/1973 - Italian Withholding Tax Regulation"
            }
            
        except Exception as e:
            logger.error("withholding_calculation_failed", error=str(e), amount=amount, tax_type=tax_type)
            raise ValueError(f"Withholding tax calculation failed: {str(e)}")
    
    def calculate_social_contributions(self, income: float, category: str = "employee") -> Dict[str, Any]:
        """Calculate Italian social security contributions.
        
        Args:
            income: Annual income
            category: Contributor category (employee, self_employed, etc.)
            
        Returns:
            Dictionary with social contributions calculation
        """
        try:
            # 2024 contribution rates (approximate)
            rates = {
                "employee": {
                    "pension": 0.0919,      # 9.19%
                    "unemployment": 0.0068,  # 0.68%
                    "health": 0.0,          # Covered by employer
                    "total": 0.0987         # Total employee contribution
                },
                "employer": {
                    "pension": 0.2340,      # 23.40%
                    "unemployment": 0.0141,  # 1.41%
                    "health": 0.0734,       # 7.34%
                    "inail": 0.0016,        # 0.16% (varies by sector)
                    "total": 0.3231         # Total employer contribution
                },
                "self_employed": {
                    "pension": 0.2475,      # 24.75%
                    "health": 0.0734,       # 7.34%
                    "total": 0.3209         # Total self-employed contribution
                }
            }
            
            if category not in rates:
                raise ValueError(f"Unknown contributor category: {category}")
            
            category_rates = rates[category]
            contributions = {}
            total_contribution = Decimal('0')
            
            for contrib_type, rate in category_rates.items():
                if contrib_type != "total":
                    amount = Decimal(str(income)) * Decimal(str(rate))
                    contributions[contrib_type] = float(amount)
                    total_contribution += amount
            
            return {
                "income": income,
                "category": category,
                "contributions": contributions,
                "total_contribution": float(total_contribution),
                "net_income": income - float(total_contribution),
                "calculation_date": datetime.utcnow().isoformat(),
                "legal_reference": "Law 335/1995 - Italian Social Security Reform"
            }
            
        except Exception as e:
            logger.error("social_contributions_calculation_failed", error=str(e), income=income, category=category)
            raise ValueError(f"Social contributions calculation failed: {str(e)}")


class ItalianLegalService:
    """Italian legal document and compliance service."""
    
    def __init__(self):
        self.tax_calculator = ItalianTaxCalculator()
    
    async def get_tax_rates(self, tax_type: TaxType, date_ref: Optional[date] = None) -> List[ItalianTaxRate]:
        """Get current tax rates for a specific tax type.
        
        Args:
            tax_type: Type of tax
            date_ref: Reference date (default: current date)
            
        Returns:
            List of applicable tax rates
        """
        try:
            if date_ref is None:
                date_ref = date.today()
            
            async with database_service.get_db() as db:
                query = select(ItalianTaxRate).where(
                    ItalianTaxRate.tax_type == tax_type,
                    ItalianTaxRate.valid_from <= date_ref,
                    (ItalianTaxRate.valid_to >= date_ref) | (ItalianTaxRate.valid_to == None)
                )
                
                result = await db.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            logger.error("tax_rates_retrieval_failed", tax_type=tax_type.value, error=str(e))
            return []
    
    async def get_legal_template(self, template_code: str) -> Optional[ItalianLegalTemplate]:
        """Get a legal document template by code.
        
        Args:
            template_code: Unique template code
            
        Returns:
            Template if found, None otherwise
        """
        try:
            async with database_service.get_db() as db:
                query = select(ItalianLegalTemplate).where(
                    ItalianLegalTemplate.template_code == template_code,
                    ItalianLegalTemplate.valid_from <= date.today(),
                    (ItalianLegalTemplate.valid_to >= date.today()) | (ItalianLegalTemplate.valid_to == None)
                )
                
                result = await db.execute(query)
                return result.scalar_one_or_none()
                
        except Exception as e:
            logger.error("legal_template_retrieval_failed", template_code=template_code, error=str(e))
            return None
    
    async def search_regulations(self, keywords: List[str], subjects: Optional[List[str]] = None) -> List[ItalianRegulation]:
        """Search Italian regulations by keywords and subjects.
        
        Args:
            keywords: Search keywords
            subjects: Subject matter filters
            
        Returns:
            List of matching regulations
        """
        try:
            async with database_service.get_db() as db:
                query = select(ItalianRegulation).where(
                    ItalianRegulation.repealed_date == None  # Only active regulations
                )
                
                # Add keyword filtering (this would be more sophisticated in production)
                if keywords:
                    keyword_filter = None
                    for keyword in keywords:
                        condition = ItalianRegulation.title.contains(keyword) | \
                                   ItalianRegulation.summary.contains(keyword)
                        keyword_filter = condition if keyword_filter is None else keyword_filter | condition
                    
                    if keyword_filter is not None:
                        query = query.where(keyword_filter)
                
                # Add subject filtering
                if subjects:
                    # This would use array operations in PostgreSQL
                    pass  # Simplified for now
                
                query = query.order_by(ItalianRegulation.enacted_date.desc()).limit(50)
                
                result = await db.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            logger.error("regulation_search_failed", keywords=keywords, error=str(e))
            return []
    
    async def perform_tax_calculation(self, user_id: str, session_id: str, calculation_request: Dict[str, Any]) -> TaxCalculation:
        """Perform a tax calculation and store the result.
        
        Args:
            user_id: User performing calculation
            session_id: Session ID
            calculation_request: Calculation parameters
            
        Returns:
            Tax calculation record
        """
        try:
            tax_type = TaxType(calculation_request["tax_type"])
            base_amount = float(calculation_request["amount"])
            tax_year = calculation_request.get("tax_year", date.today().year)
            
            # Perform calculation based on tax type
            if tax_type == TaxType.VAT:
                result = self.tax_calculator.calculate_vat(
                    base_amount, 
                    calculation_request.get("vat_type", "standard")
                )
            elif tax_type == TaxType.INCOME_TAX:
                result = self.tax_calculator.calculate_irpef(
                    base_amount,
                    calculation_request.get("deductions", 0)
                )
            elif tax_type == TaxType.WITHHOLDING_TAX:
                result = self.tax_calculator.calculate_withholding_tax(
                    base_amount,
                    calculation_request.get("withholding_type", "professional")
                )
            else:
                raise ValueError(f"Unsupported tax type: {tax_type}")
            
            # Store calculation record
            calculation = TaxCalculation(
                user_id=user_id,
                session_id=session_id,
                calculation_type=tax_type,
                base_amount=Decimal(str(base_amount)),
                tax_year=tax_year,
                input_parameters=calculation_request,
                tax_amount=Decimal(str(result.get("tax_amount", result.get("vat_amount", result.get("total_tax", 0))))),
                effective_rate=Decimal(str(result.get("effective_rate", result.get("vat_rate", 0)))),
                breakdown=result,
                regulations_used=[],  # Would be populated with actual regulation IDs
                tax_rates_used=[],    # Would be populated with actual tax rate IDs
                calculation_method="built_in_calculator",
                confidence_score=0.95
            )
            
            async with database_service.get_db() as db:
                db.add(calculation)
                await db.commit()
                await db.refresh(calculation)
            
            logger.info(
                "tax_calculation_completed",
                user_id=user_id,
                tax_type=tax_type.value,
                amount=base_amount,
                result_amount=float(calculation.tax_amount)
            )
            
            return calculation
            
        except Exception as e:
            logger.error(
                "tax_calculation_failed",
                user_id=user_id,
                calculation_request=calculation_request,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Tax calculation failed: {str(e)}")
    
    async def check_document_compliance(self, user_id: str, session_id: str, document: Dict[str, Any]) -> ComplianceCheck:
        """Check document compliance with Italian regulations.
        
        Args:
            user_id: User requesting check
            session_id: Session ID
            document: Document data to check
            
        Returns:
            Compliance check record
        """
        try:
            document_type = DocumentType(document.get("type", DocumentType.FORM))
            document_content = document.get("content", "")
            
            # Perform basic compliance checks
            findings = []
            compliance_score = 1.0
            
            # Check for required elements based on document type
            if document_type == DocumentType.CONTRACT:
                findings.extend(self._check_contract_compliance(document_content))
            elif document_type == DocumentType.INVOICE:
                findings.extend(self._check_invoice_compliance(document_content))
            elif document_type == DocumentType.PRIVACY_POLICY:
                findings.extend(self._check_privacy_policy_compliance(document_content))
            
            # Calculate overall compliance score
            critical_issues = len([f for f in findings if f.get("severity") == "critical"])
            warning_issues = len([f for f in findings if f.get("severity") == "warning"])
            
            compliance_score = max(0, 1.0 - (critical_issues * 0.3) - (warning_issues * 0.1))
            
            # Determine overall status
            if compliance_score >= 0.9:
                status = ComplianceStatus.COMPLIANT
            elif compliance_score >= 0.7:
                status = ComplianceStatus.WARNING
            elif compliance_score >= 0.5:
                status = ComplianceStatus.NEEDS_REVIEW
            else:
                status = ComplianceStatus.NON_COMPLIANT
            
            # Generate recommendations
            recommendations = self._generate_recommendations(findings)
            
            # Store compliance check record
            check = ComplianceCheck(
                user_id=user_id,
                session_id=session_id,
                check_type=f"{document_type.value}_compliance",
                document_type=document_type,
                document_content=document_content,
                check_parameters=document,
                overall_status=status,
                compliance_score=compliance_score,
                findings=findings,
                recommendations=recommendations,
                regulations_checked=[],  # Would be populated with actual regulation IDs
                citations=[],            # Would be populated with legal citations
                check_method="rule_based_checker",
                follow_up_required=status in [ComplianceStatus.NON_COMPLIANT, ComplianceStatus.NEEDS_REVIEW]
            )
            
            async with database_service.get_db() as db:
                db.add(check)
                await db.commit()
                await db.refresh(check)
            
            logger.info(
                "compliance_check_completed",
                user_id=user_id,
                document_type=document_type.value,
                compliance_score=compliance_score,
                status=status.value
            )
            
            return check
            
        except Exception as e:
            logger.error(
                "compliance_check_failed",
                user_id=user_id,
                document=document,
                error=str(e),
                exc_info=True
            )
            raise ValueError(f"Compliance check failed: {str(e)}")
    
    def _check_contract_compliance(self, content: str) -> List[Dict[str, Any]]:
        """Check contract-specific compliance requirements."""
        findings = []
        
        # Check for required contract elements
        required_elements = [
            ("parties identification", r"(nome|denominazione|ragione sociale)", "critical"),
            ("contract object", r"(oggetto|prestazione|servizio)", "critical"),
            ("consideration", r"(corrispettivo|prezzo|compenso)", "critical"),
            ("signatures", r"(firma|sottoscrizione)", "warning"),
            ("date", r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}", "warning"),
        ]
        
        for element, pattern, severity in required_elements:
            if not re.search(pattern, content, re.IGNORECASE):
                findings.append({
                    "element": element,
                    "severity": severity,
                    "message": f"Missing or unclear {element}",
                    "regulation": "Art. 1321 Codice Civile"
                })
        
        return findings
    
    def _check_invoice_compliance(self, content: str) -> List[Dict[str, Any]]:
        """Check invoice-specific compliance requirements."""
        findings = []
        
        # Check for required invoice elements (Italian tax requirements)
        required_elements = [
            ("invoice number", r"(numero|n\.|fattura n)", "critical"),
            ("date", r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}", "critical"),
            ("VAT number", r"(p\.iva|partita iva|vat)", "critical"),
            ("tax code", r"(codice fiscale|c\.f\.)", "warning"),
            ("VAT amount", r"(iva|imposta)", "critical"),
        ]
        
        for element, pattern, severity in required_elements:
            if not re.search(pattern, content, re.IGNORECASE):
                findings.append({
                    "element": element,
                    "severity": severity,
                    "message": f"Missing {element}",
                    "regulation": "DPR 633/1972 - Art. 21"
                })
        
        return findings
    
    def _check_privacy_policy_compliance(self, content: str) -> List[Dict[str, Any]]:
        """Check privacy policy GDPR compliance."""
        findings = []
        
        # Check GDPR requirements
        gdpr_elements = [
            ("data controller", r"(titolare|controller)", "critical"),
            ("legal basis", r"(base giuridica|legal basis)", "critical"),
            ("data subject rights", r"(diritti|rights)", "critical"),
            ("data retention", r"(conservazione|retention)", "warning"),
            ("contact information", r"(contatto|contact)", "warning"),
        ]
        
        for element, pattern, severity in gdpr_elements:
            if not re.search(pattern, content, re.IGNORECASE):
                findings.append({
                    "element": element,
                    "severity": severity,
                    "message": f"Missing GDPR requirement: {element}",
                    "regulation": "GDPR Art. 13-14"
                })
        
        return findings
    
    def _generate_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on compliance findings."""
        recommendations = []
        
        critical_findings = [f for f in findings if f.get("severity") == "critical"]
        warning_findings = [f for f in findings if f.get("severity") == "warning"]
        
        if critical_findings:
            recommendations.append("Address critical compliance issues immediately to ensure legal validity")
            
        if warning_findings:
            recommendations.append("Review and improve document to address warnings")
            
        if len(findings) > 5:
            recommendations.append("Consider consulting with a legal professional for comprehensive review")
            
        return recommendations
    
    async def generate_document_from_template(self, template_code: str, variables: Dict[str, Any]) -> Optional[str]:
        """Generate a document from a legal template.
        
        Args:
            template_code: Template code
            variables: Variables to substitute in template
            
        Returns:
            Generated document content
        """
        try:
            template = await self.get_legal_template(template_code)
            if not template:
                return None
            
            content = template.content
            
            # Simple variable substitution (would be more sophisticated in production)
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                content = content.replace(placeholder, str(value))
            
            logger.info(
                "document_generated_from_template",
                template_code=template_code,
                variables_count=len(variables)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "document_generation_failed",
                template_code=template_code,
                error=str(e)
            )
            return None


# Global instance
italian_knowledge_service = ItalianLegalService()