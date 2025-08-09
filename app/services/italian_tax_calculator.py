"""
Comprehensive Italian Tax Calculator Service.

This service provides accurate calculations for all aspects of the Italian tax system,
including IRPEF, regional taxes, INPS contributions, VAT, corporate taxes, property taxes,
and capital gains taxes. It follows Test-Driven Development principles and integrates
with the existing PratikoAI architecture.

Key Features:
- IRPEF calculation with progressive brackets (2024 rates)
- Regional and municipal tax variations
- INPS social security contributions (employees, employers, self-employed)
- VAT calculations with different rates and categories
- Corporate taxes (IRES and IRAP)
- Property taxes (IMU) with regional variations
- Capital gains taxes for different asset types
- Tax deduction engine
- Tax optimization suggestions
- Freelancer and P.IVA calculations with flat-rate regime support
- Integration with CCNL salary calculations
"""

import asyncio
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple, Union
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.tax_constants import (
    IRPEF_BRACKETS_2024,
    REGIONAL_IRPEF_SURCHARGE_2024,
    MUNICIPAL_IRPEF_CONFIG,
    INPS_RATES_2024,
    VAT_RATES_2024,
    CORPORATE_TAX_RATES_2024,
    IMU_CONFIG_2024,
    CAPITAL_GAINS_TAX_2024,
    FLAT_RATE_REGIME_2024,
    TAX_DEDUCTIONS_2024,
    WITHHOLDING_TAX_2024,
    TAX_CALENDAR_2024,
    REGIONAL_SPECIAL_PROVISIONS,
    TAX_OPTIMIZATION_THRESHOLDS,
    VALIDATION_LIMITS,
    ERROR_MESSAGES,
    TaxRegime,
    EmploymentType,
    BusinessType,
    VatCategory
)
from app.services.regional_tax_service import RegionalTaxService
from app.services.cache import CacheService


# Custom Exceptions
class TaxCalculationError(Exception):
    """Base exception for tax calculation errors."""
    pass


class InvalidIncomeError(TaxCalculationError):
    """Raised when income value is invalid."""
    pass


class InvalidLocationError(TaxCalculationError):
    """Raised when location cannot be found or is invalid."""
    pass


class InvalidTaxTypeError(TaxCalculationError):
    """Raised when tax type is not supported."""
    pass


class IrpefCalculator:
    """Calculator for IRPEF (Personal Income Tax) with progressive brackets."""
    
    def __init__(self):
        self.brackets = IRPEF_BRACKETS_2024
    
    def calculate_irpef(self, income: Decimal) -> Dict[str, Any]:
        """
        Calculate IRPEF using progressive brackets.
        
        Args:
            income: Annual taxable income in euros
            
        Returns:
            Dictionary with calculation details
            
        Raises:
            InvalidIncomeError: If income is negative
        """
        if income < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        if income == 0:
            return {
                "income": income,
                "gross_tax": Decimal("0"),
                "effective_rate": Decimal("0"),
                "marginal_rate": Decimal("0"),
                "brackets_used": [],
                "bracket_details": []
            }
        
        total_tax = Decimal("0")
        brackets_used = []
        bracket_details = []
        remaining_income = income
        
        for bracket in self.brackets:
            if remaining_income <= 0:
                break
                
            bracket_min = bracket["min_income"]
            bracket_max = bracket["max_income"] or Decimal("999999999")  # Infinite for top bracket
            bracket_rate = bracket["rate"]
            
            if income > bracket_min:
                # Calculate taxable amount in this bracket
                if bracket_max == Decimal("999999999"):  # Top bracket
                    bracket_income = remaining_income
                else:
                    # For other brackets, take the lesser of:
                    # 1. Remaining income to tax
                    # 2. The bracket width (max - min)
                    bracket_width = bracket_max - bracket_min
                    bracket_income = min(remaining_income, bracket_width)
                bracket_tax = bracket_income * bracket_rate / 100
                
                total_tax += bracket_tax
                brackets_used.append(bracket["description"].lower().replace(" ", "_"))
                bracket_details.append({
                    "bracket": bracket["description"],
                    "rate": bracket_rate,
                    "taxable_income": bracket_income,
                    "tax_amount": bracket_tax,
                    "income_range": f"{bracket_min} - {bracket_max if bracket_max < 999999999 else '∞'}"
                })
                
                remaining_income -= bracket_income
        
        # Calculate effective and marginal rates
        effective_rate = (total_tax / income * 100).quantize(Decimal("0.01"))
        marginal_rate = self._get_marginal_rate(income)
        
        return {
            "income": income,
            "gross_tax": total_tax.quantize(Decimal("0.01")),
            "effective_rate": effective_rate,
            "marginal_rate": marginal_rate,
            "brackets_used": brackets_used,
            "bracket_details": bracket_details
        }
    
    def calculate_irpef_with_deductions(
        self, 
        income: Decimal, 
        deductions: Dict[str, Decimal]
    ) -> Dict[str, Any]:
        """
        Calculate IRPEF with various deductions applied.
        
        Args:
            income: Gross income before deductions
            deductions: Dictionary of deduction types and amounts
            
        Returns:
            Dictionary with detailed calculation including deductions
        """
        total_deductions = sum(deductions.values())
        taxable_income = max(income - total_deductions, Decimal("0"))
        
        irpef_result = self.calculate_irpef(taxable_income)
        
        return {
            "gross_income": income,
            "total_deductions": total_deductions,
            "deduction_details": deductions,
            "taxable_income": taxable_income,
            "net_tax": irpef_result["gross_tax"],
            "effective_rate": irpef_result["effective_rate"],
            "tax_savings": self.calculate_irpef(income)["gross_tax"] - irpef_result["gross_tax"],
            "bracket_details": irpef_result["bracket_details"]
        }
    
    def _get_marginal_rate(self, income: Decimal) -> Decimal:
        """Get the marginal tax rate for a given income level."""
        for bracket in self.brackets:
            bracket_min = bracket["min_income"]
            bracket_max = bracket["max_income"] or Decimal("999999999")
            
            if bracket_min <= income <= bracket_max:
                return bracket["rate"]
        
        return self.brackets[-1]["rate"]  # Return highest rate if not found


class InpsCalculator:
    """Calculator for INPS social security contributions."""
    
    def __init__(self):
        self.rates = INPS_RATES_2024
    
    def calculate_employee_contribution(self, gross_salary: Decimal) -> Dict[str, Any]:
        """Calculate INPS contribution for employees."""
        if gross_salary < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        employee_config = self.rates["employee"]
        contribution_base = min(gross_salary, employee_config["ceiling"])
        employee_contribution = contribution_base * employee_config["rate"] / 100
        
        return {
            "gross_salary": gross_salary,
            "contribution_base": contribution_base,
            "employee_contribution": employee_contribution.quantize(Decimal("0.01")),
            "contribution_rate": employee_config["rate"],
            "ceiling": employee_config["ceiling"],
            "pension_contribution": employee_contribution * Decimal("0.8"),  # Approximate pension portion
            "other_contributions": employee_contribution * Decimal("0.2")  # Other social security
        }
    
    def calculate_employer_contribution(self, gross_salary: Decimal) -> Dict[str, Any]:
        """Calculate INPS contribution for employers."""
        if gross_salary < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        employer_config = self.rates["employer"]
        employer_contribution = gross_salary * employer_config["rate"] / 100
        
        return {
            "gross_salary": gross_salary,
            "employer_contribution": employer_contribution.quantize(Decimal("0.01")),
            "contribution_rate": employer_config["rate"],
            "total_cost": gross_salary + employer_contribution,
            "note": "Rate varies by sector and company size"
        }
    
    def calculate_executive_contribution(self, income: Decimal) -> Dict[str, Any]:
        """Calculate INPS contribution for commercial executives."""
        if income < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        exec_config = self.rates["executive"]
        ceiling = exec_config["ceiling"]
        
        if income <= ceiling:
            contribution = income * exec_config["rate_below_ceiling"] / 100
            rate_used = exec_config["rate_below_ceiling"]
        else:
            first_part = ceiling * exec_config["rate_below_ceiling"] / 100
            second_part = (income - ceiling) * exec_config["rate_above_ceiling"] / 100
            contribution = first_part + second_part
            rate_used = "variable"
        
        return {
            "income": income,
            "total_contribution": contribution.quantize(Decimal("0.01")),
            "rate_used": rate_used,
            "ceiling": ceiling,
            "rate_below_ceiling": exec_config["rate_below_ceiling"],
            "rate_above_ceiling": exec_config["rate_above_ceiling"]
        }
    
    def calculate_self_employed_contribution(self, annual_income: Decimal) -> Dict[str, Any]:
        """Calculate INPS contribution for self-employed individuals."""
        if annual_income < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        self_emp_config = self.rates["self_employed_separate"]
        
        # Use standard rate for those with other mandatory coverage
        rate = self_emp_config["rate_with_other_coverage"]
        contribution = annual_income * rate / 100
        
        return {
            "annual_income": annual_income,
            "contribution": contribution.quantize(Decimal("0.01")),
            "contribution_rate": rate,
            "regime": "separate_social_security",
            "alternative_rates": {
                "exclusive_coverage": self_emp_config["rate_exclusive_coverage"],
                "with_dis_coll": self_emp_config["rate_with_dis_coll"],
                "without_dis_coll": self_emp_config["rate_without_dis_coll"]
            }
        }


class VatCalculator:
    """Calculator for VAT (IVA) with different rates and categories."""
    
    def __init__(self):
        self.rates = VAT_RATES_2024
    
    def calculate_vat(self, net_amount: Decimal, category: str) -> Dict[str, Any]:
        """
        Calculate VAT for a given net amount and category.
        
        Args:
            net_amount: Net amount before VAT
            category: VAT category (standard, reduced_10, reduced_4, exempt)
            
        Returns:
            Dictionary with VAT calculation details
        """
        if net_amount < 0:
            raise ValueError("Net amount cannot be negative")
        
        try:
            vat_category = VatCategory(category)
        except ValueError:
            raise InvalidTaxTypeError(f"Invalid VAT category: {category}")
        
        vat_config = self.rates[vat_category]
        vat_rate = vat_config["rate"]
        vat_amount = net_amount * vat_rate / 100
        gross_amount = net_amount + vat_amount
        
        result = {
            "net_amount": net_amount,
            "vat_rate": vat_rate,
            "vat_amount": vat_amount.quantize(Decimal("0.01")),
            "gross_amount": gross_amount.quantize(Decimal("0.01")),
            "category": category,
            "description": vat_config["description"]
        }
        
        if vat_category == VatCategory.EXEMPT:
            result["exemption_reason"] = "VAT exempt category"
        
        return result
    
    def calculate_reverse_vat(self, gross_amount: Decimal, category: str) -> Dict[str, Any]:
        """Calculate net amount and VAT from gross amount."""
        if gross_amount < 0:
            raise ValueError("Gross amount cannot be negative")
        
        try:
            vat_category = VatCategory(category)
        except ValueError:
            raise InvalidTaxTypeError(f"Invalid VAT category: {category}")
        
        vat_config = self.rates[vat_category]
        vat_rate = vat_config["rate"]
        
        if vat_rate == 0:
            net_amount = gross_amount
            vat_amount = Decimal("0")
        else:
            net_amount = gross_amount / (1 + vat_rate / 100)
            vat_amount = gross_amount - net_amount
        
        return {
            "gross_amount": gross_amount,
            "net_amount": net_amount.quantize(Decimal("0.01")),
            "vat_amount": vat_amount.quantize(Decimal("0.01")),
            "vat_rate": vat_rate,
            "category": category
        }
    
    def calculate_eu_vat(
        self, 
        net_amount: Decimal, 
        origin_country: str, 
        destination_country: str,
        service_type: str = "standard"
    ) -> Dict[str, Any]:
        """Calculate VAT for EU cross-border transactions."""
        if net_amount < 0:
            raise ValueError("Net amount cannot be negative")
        
        # B2B services: reverse charge mechanism
        if service_type in ["consulting", "legal", "technical"]:
            return {
                "net_amount": net_amount,
                "italian_vat": Decimal("0"),
                "vat_treatment": "reverse_charge",
                "foreign_vat_applicable": True,
                "origin_country": origin_country,
                "destination_country": destination_country,
                "note": "Customer responsible for VAT in destination country"
            }
        
        # Standard B2B goods: reverse charge if over threshold
        return {
            "net_amount": net_amount,
            "italian_vat": Decimal("0"),
            "vat_treatment": "reverse_charge",
            "foreign_vat_applicable": True,
            "origin_country": origin_country,
            "destination_country": destination_country
        }


class CorporateTaxCalculator:
    """Calculator for corporate taxes (IRES and IRAP)."""
    
    def __init__(self):
        self.rates = CORPORATE_TAX_RATES_2024
    
    def calculate_ires(self, taxable_income: Decimal) -> Dict[str, Any]:
        """Calculate IRES (Corporate Income Tax)."""
        if taxable_income < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        ires_config = self.rates["ires"]
        tax_rate = ires_config["standard_rate"]
        ires_tax = taxable_income * tax_rate / 100
        
        return {
            "taxable_income": taxable_income,
            "tax_rate": tax_rate,
            "ires_tax": ires_tax.quantize(Decimal("0.01")),
            "description": ires_config["description"],
            "reduced_rate_2025": ires_config["reduced_rate_2025"]
        }
    
    def calculate_irap(
        self, 
        production_value: Decimal, 
        region: str, 
        business_type: str = "standard"
    ) -> Dict[str, Any]:
        """Calculate IRAP (Regional Business Tax)."""
        if production_value < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        irap_config = self.rates["irap"]
        
        # Get base rate for business type
        rate_key = f"{business_type}_rate"
        if rate_key in irap_config:
            base_rate = irap_config[rate_key]
        else:
            base_rate = irap_config["standard_rate"]
        
        # Apply regional variations (simplified - would need regional data)
        tax_rate = base_rate
        irap_tax = production_value * tax_rate / 100
        
        return {
            "production_value": production_value,
            "business_type": business_type,
            "region": region,
            "tax_rate": tax_rate,
            "irap_tax": irap_tax.quantize(Decimal("0.01")),
            "base_rate": base_rate,
            "description": irap_config["description"]
        }
    
    def calculate_combined_corporate_tax(
        self,
        taxable_income: Decimal,
        production_value: Decimal,
        region: str = "Lombardia",
        business_type: str = "standard"
    ) -> Dict[str, Any]:
        """Calculate combined IRES + IRAP."""
        ires_result = self.calculate_ires(taxable_income)
        irap_result = self.calculate_irap(production_value, region, business_type)
        
        total_tax = ires_result["ires_tax"] + irap_result["irap_tax"]
        effective_rate = (total_tax / taxable_income * 100).quantize(Decimal("0.01")) if taxable_income > 0 else Decimal("0")
        
        return {
            "taxable_income": taxable_income,
            "production_value": production_value,
            "region": region,
            "business_type": business_type,
            "ires_tax": ires_result["ires_tax"],
            "irap_tax": irap_result["irap_tax"],
            "total_corporate_tax": total_tax.quantize(Decimal("0.01")),
            "effective_rate": effective_rate,
            "ires_rate": ires_result["tax_rate"],
            "irap_rate": irap_result["tax_rate"]
        }


class PropertyTaxCalculator:
    """Calculator for property taxes (IMU)."""
    
    def __init__(self, regional_tax_service: Optional[RegionalTaxService] = None):
        self.config = IMU_CONFIG_2024
        self.regional_service = regional_tax_service
    
    async def calculate_imu(
        self,
        cadastral_value: Decimal,
        cap: str,
        is_primary_residence: bool = False,
        property_type: str = "standard"
    ) -> Dict[str, Any]:
        """
        Calculate IMU (Municipal Property Tax).
        
        Args:
            cadastral_value: Cadastral value of property
            cap: Postal code of property location
            is_primary_residence: Whether it's primary residence
            property_type: Type of property
            
        Returns:
            Dictionary with IMU calculation details
        """
        if cadastral_value < 0:
            raise ValueError("Cadastral value cannot be negative")
        
        # Check for primary residence exemption
        if is_primary_residence and self.config["exemptions"]["primary_residence"]:
            return {
                "cadastral_value": cadastral_value,
                "taxable_base": Decimal("0"),
                "tax_rate": Decimal("0"),
                "imu_tax": Decimal("0"),
                "exemption": True,
                "exemption_reason": "primary_residence",
                "property_type": property_type,
                "location_cap": cap
            }
        
        # Calculate taxable base
        cadastral_adjusted = cadastral_value * self.config["cadastral_value_multiplier"]
        taxable_base = cadastral_adjusted * self.config["taxable_base_coefficient"]
        
        # Use regional service if available, otherwise use standard rate
        if self.regional_service:
            try:
                imu_result = await self.regional_service.calculate_imu(
                    property_value=taxable_base,
                    cap=cap,
                    is_prima_casa=is_primary_residence,
                    property_type=property_type
                )
                return {
                    **imu_result,
                    "cadastral_value": cadastral_value,
                    "cadastral_adjusted": cadastral_adjusted,
                    "taxable_base": taxable_base,
                    "exemption": False
                }
            except Exception as e:
                logger.warning(f"Regional IMU calculation failed: {e}")
                # Fall back to standard calculation
        
        # Standard calculation
        tax_rate = self.config["standard_rate"]
        imu_tax = taxable_base * tax_rate / 100
        
        return {
            "cadastral_value": cadastral_value,
            "cadastral_adjusted": cadastral_adjusted,
            "taxable_base": taxable_base,
            "tax_rate": tax_rate,
            "imu_tax": imu_tax.quantize(Decimal("0.01")),
            "exemption": False,
            "property_type": property_type,
            "location_cap": cap,
            "payment_schedule": self.config["payment_schedule"]
        }


class CapitalGainsTaxCalculator:
    """Calculator for capital gains taxes on different asset types."""
    
    def __init__(self):
        self.rates = CAPITAL_GAINS_TAX_2024
    
    def calculate_capital_gains_tax(
        self,
        purchase_price: Decimal,
        sale_price: Decimal,
        asset_type: str,
        holding_period_days: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate capital gains tax.
        
        Args:
            purchase_price: Original purchase price
            sale_price: Sale price
            asset_type: Type of asset (financial, real_estate, cryptocurrency, etc.)
            holding_period_days: Number of days the asset was held
            
        Returns:
            Dictionary with capital gains calculation
        """
        if purchase_price < 0 or sale_price < 0:
            raise ValueError("Prices cannot be negative")
        
        capital_gain = sale_price - purchase_price
        
        if capital_gain <= 0:
            return {
                "purchase_price": purchase_price,
                "sale_price": sale_price,
                "capital_gain": capital_gain,
                "tax_amount": Decimal("0"),
                "tax_rate": Decimal("0"),
                "asset_type": asset_type,
                "note": "No gain or loss - no tax due"
            }
        
        # Get tax configuration for asset type
        if asset_type not in self.rates:
            raise InvalidTaxTypeError(f"Unsupported asset type: {asset_type}")
        
        tax_config = self.rates[asset_type]
        
        # Check for exemptions
        if asset_type == "real_estate":
            if holding_period_days >= tax_config["exemption_period_days"]:
                return {
                    "purchase_price": purchase_price,
                    "sale_price": sale_price,
                    "capital_gain": capital_gain,
                    "tax_amount": Decimal("0"),
                    "tax_rate": Decimal("0"),
                    "asset_type": asset_type,
                    "holding_period_days": holding_period_days,
                    "exemption": True,
                    "exemption_reason": "long_term_holding"
                }
        
        # Check threshold for cryptocurrency
        if asset_type == "cryptocurrency":
            threshold = tax_config.get("threshold", Decimal("0"))
            if capital_gain <= threshold:
                return {
                    "purchase_price": purchase_price,
                    "sale_price": sale_price,
                    "capital_gain": capital_gain,
                    "tax_amount": Decimal("0"),
                    "tax_rate": Decimal("0"),
                    "asset_type": asset_type,
                    "threshold": threshold,
                    "exemption": True,
                    "exemption_reason": "below_threshold"
                }
        
        # Calculate tax
        tax_rate = tax_config["rate"]
        tax_amount = capital_gain * tax_rate / 100
        
        return {
            "purchase_price": purchase_price,
            "sale_price": sale_price,
            "capital_gain": capital_gain,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount.quantize(Decimal("0.01")),
            "asset_type": asset_type,
            "holding_period_days": holding_period_days,
            "description": tax_config["description"]
        }


class TaxDeductionEngine:
    """Engine for calculating various tax deductions."""
    
    def __init__(self):
        self.deductions = TAX_DEDUCTIONS_2024
    
    def calculate_employee_deductions(self, income: Decimal) -> Dict[str, Any]:
        """Calculate standard work deductions for employees."""
        if income < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        work_config = self.deductions["work_income"]
        base_deduction = work_config["employee_base"]
        
        # Apply income-based calculation (simplified)
        if income <= Decimal("15000"):
            work_deduction = base_deduction
        elif income <= Decimal("28000"):
            # Gradual reduction
            work_deduction = base_deduction - (income - Decimal("15000")) * Decimal("0.02")
        elif income <= Decimal("55000"):
            # Further reduction
            work_deduction = Decimal("1610") - (income - Decimal("28000")) * Decimal("0.019")
        else:
            work_deduction = Decimal("1097")
        
        work_deduction = max(work_deduction, Decimal("0"))
        
        return {
            "income": income,
            "work_deduction": work_deduction.quantize(Decimal("0.01")),
            "base_deduction": base_deduction,
            "total_deductions": work_deduction.quantize(Decimal("0.01"))
        }
    
    def calculate_family_deductions(
        self,
        dependent_children: int = 0,
        dependent_spouse: bool = False,
        children_ages: List[int] = None,
        spouse_income: Decimal = Decimal("0")
    ) -> Dict[str, Any]:
        """Calculate family-related deductions."""
        family_config = self.deductions["family"]
        children_ages = children_ages or []
        
        # Spouse deduction
        spouse_deduction = Decimal("0")
        if dependent_spouse and spouse_income <= family_config["spouse"]["income_threshold"]:
            spouse_deduction = family_config["spouse"]["base_deduction"]
        
        # Children deductions
        children_deduction = Decimal("0")
        if dependent_children > 0:
            base_per_child = family_config["children"]["base_deduction"]
            under_3_additional = family_config["children"]["under_3_additional"]
            
            for i, age in enumerate(children_ages[:dependent_children]):
                child_deduction = base_per_child
                if age < 3:
                    child_deduction += under_3_additional
                children_deduction += child_deduction
            
            # For any children without specified age, use base deduction
            remaining_children = max(0, dependent_children - len(children_ages))
            children_deduction += remaining_children * base_per_child
        
        total_family_deductions = spouse_deduction + children_deduction
        
        return {
            "spouse_deduction": spouse_deduction,
            "children_deduction": children_deduction,
            "dependent_children": dependent_children,
            "dependent_spouse": dependent_spouse,
            "total_family_deductions": total_family_deductions.quantize(Decimal("0.01"))
        }
    
    def calculate_medical_deductions(self, medical_expenses: Decimal) -> Dict[str, Any]:
        """Calculate medical expense deductions."""
        if medical_expenses < 0:
            raise ValueError("Medical expenses cannot be negative")
        
        medical_config = self.deductions["medical_expenses"]
        threshold = medical_config["threshold"]
        
        deductible_amount = max(medical_expenses - threshold, Decimal("0"))
        
        return {
            "total_expenses": medical_expenses,
            "threshold": threshold,
            "deductible_amount": deductible_amount.quantize(Decimal("0.01")),
            "deduction_rate": medical_config["deduction_rate"]
        }
    
    def calculate_renovation_deductions(
        self,
        expenses: Decimal,
        renovation_type: str = "energy_efficiency"
    ) -> Dict[str, Any]:
        """Calculate home renovation deductions."""
        if expenses < 0:
            raise ValueError("Renovation expenses cannot be negative")
        
        renovation_config = self.deductions["home_renovations"]
        
        # Map renovation types to config keys
        config_mapping = {
            "energy_efficiency": "ecobonus",
            "structural": "sismabonus",
            "facade": "bonus_facciate",
            "super": "superbonus"
        }
        
        config_key = config_mapping.get(renovation_type, "ecobonus")
        renovation_data = renovation_config[config_key]
        
        deduction_rate = renovation_data["rate"]
        max_amount = renovation_data["max_amount"]
        
        eligible_expenses = min(expenses, max_amount)
        deductible_amount = eligible_expenses * deduction_rate / 100
        spread_years = 10  # Standard spread period
        annual_deduction = deductible_amount / spread_years
        
        return {
            "total_expenses": expenses,
            "eligible_expenses": eligible_expenses,
            "deduction_rate": deduction_rate,
            "max_amount": max_amount,
            "deductible_amount": deductible_amount.quantize(Decimal("0.01")),
            "spread_over_years": spread_years,
            "annual_deduction": annual_deduction.quantize(Decimal("0.01")),
            "renovation_type": renovation_type
        }


class FreelancerTaxCalculator:
    """Calculator for freelancer and P.IVA taxes."""
    
    def __init__(self):
        self.flat_rate_config = FLAT_RATE_REGIME_2024
        self.irpef_calculator = IrpefCalculator()
        self.inps_calculator = InpsCalculator()
        self.vat_calculator = VatCalculator()
    
    def calculate_flat_rate_tax(
        self,
        annual_revenue: Decimal,
        activity_category: str,
        is_new_business: bool = False
    ) -> Dict[str, Any]:
        """Calculate tax under flat-rate regime (Regime Forfettario)."""
        if annual_revenue < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        if annual_revenue > self.flat_rate_config["revenue_threshold"]:
            raise ValueError(ERROR_MESSAGES["exceeds_flat_rate_threshold"])
        
        # Get activity coefficient
        coefficient = self.flat_rate_config["activity_coefficients"].get(
            activity_category, 
            self.flat_rate_config["activity_coefficients"]["other_services"]
        )
        
        # Calculate taxable income
        taxable_income = annual_revenue * coefficient
        
        # Get tax rate
        if is_new_business:
            tax_rate = self.flat_rate_config["new_business_rate"]
        else:
            tax_rate = self.flat_rate_config["standard_rate"]
        
        # Calculate tax
        tax_amount = taxable_income * tax_rate / 100
        
        return {
            "annual_revenue": annual_revenue,
            "activity_category": activity_category,
            "activity_coefficient": coefficient,
            "taxable_income": taxable_income.quantize(Decimal("0.01")),
            "tax_rate": tax_rate,
            "tax_amount": tax_amount.quantize(Decimal("0.01")),
            "is_new_business": is_new_business,
            "regime": "forfettario",
            "vat_exempt": True,
            "inps_exempt": False  # Still need to pay INPS
        }
    
    def calculate_standard_regime_tax(
        self,
        annual_revenue: Decimal,
        business_expenses: Decimal,
        region: str,
        municipality: str
    ) -> Dict[str, Any]:
        """Calculate freelancer tax under standard regime."""
        if annual_revenue < 0 or business_expenses < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        # Calculate taxable income
        taxable_income = annual_revenue - business_expenses
        
        # Calculate IRPEF
        irpef_result = self.irpef_calculator.calculate_irpef(taxable_income)
        
        # Calculate INPS (simplified)
        inps_result = self.inps_calculator.calculate_self_employed_contribution(taxable_income)
        
        # Regional surcharge (simplified - would use regional service)
        regional_rate = REGIONAL_IRPEF_SURCHARGE_2024.get(region, Decimal("1.73"))
        regional_surcharge = taxable_income * regional_rate / 100
        
        # Municipal surcharge (simplified)
        municipal_config = MUNICIPAL_IRPEF_CONFIG["typical_rates"].get(
            municipality,
            {"rate": MUNICIPAL_IRPEF_CONFIG["default_rate"], "threshold": MUNICIPAL_IRPEF_CONFIG["default_threshold"]}
        )
        
        municipal_surcharge = Decimal("0")
        if taxable_income > municipal_config["threshold"]:
            municipal_surcharge = taxable_income * municipal_config["rate"] / 100
        
        # Total tax calculation
        total_tax = (
            irpef_result["gross_tax"] +
            regional_surcharge +
            municipal_surcharge +
            inps_result["contribution"]
        )
        
        return {
            "annual_revenue": annual_revenue,
            "business_expenses": business_expenses,
            "taxable_income": taxable_income,
            "irpef_tax": irpef_result["gross_tax"],
            "regional_surcharge": regional_surcharge.quantize(Decimal("0.01")),
            "municipal_surcharge": municipal_surcharge.quantize(Decimal("0.01")),
            "inps_contribution": inps_result["contribution"],
            "total_tax": total_tax.quantize(Decimal("0.01")),
            "effective_rate": (total_tax / annual_revenue * 100).quantize(Decimal("0.01")),
            "regime": "standard",
            "vat_applicable": True
        }
    
    def calculate_quarterly_payments(
        self,
        previous_year_total_tax: Decimal,
        current_quarter_revenue: Decimal,
        quarter: int
    ) -> Dict[str, Any]:
        """Calculate quarterly advance tax payments."""
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Quarter must be between 1 and 4")
        
        # Quarterly payment based on previous year
        quarterly_payment = previous_year_total_tax / 4
        
        # Payment due dates
        due_dates = {
            1: date(2024, 6, 17),
            2: date(2024, 11, 30),
            3: date(2024, 2, 28),  # Following year
            4: date(2024, 5, 31)   # Following year
        }
        
        return {
            "quarter": quarter,
            "previous_year_tax": previous_year_total_tax,
            "quarterly_payment": quarterly_payment.quantize(Decimal("0.01")),
            "current_quarter_revenue": current_quarter_revenue,
            "payment_due_date": due_dates[quarter],
            "cumulative_payments": quarterly_payment * quarter
        }


class TaxOptimizationEngine:
    """Engine for tax optimization suggestions."""
    
    def __init__(self):
        self.thresholds = TAX_OPTIMIZATION_THRESHOLDS
        self.irpef_calculator = IrpefCalculator()
        self.freelancer_calculator = FreelancerTaxCalculator()
        self.inps_calculator = InpsCalculator()
    
    def compare_employment_types(self, gross_income: Decimal) -> Dict[str, Any]:
        """Compare tax burden between employee and contractor."""
        # Employee calculation
        employee_irpef = self.irpef_calculator.calculate_irpef(gross_income)
        employee_inps = self.inps_calculator.calculate_employee_contribution(gross_income)
        employee_net = gross_income - employee_irpef["gross_tax"] - employee_inps["employee_contribution"]
        
        # Contractor calculation (simplified)
        contractor_expenses = gross_income * Decimal("0.15")  # Assume 15% expenses
        contractor_result = self.freelancer_calculator.calculate_standard_regime_tax(
            annual_revenue=gross_income,
            business_expenses=contractor_expenses,
            region="Lombardia",
            municipality="Milano"
        )
        contractor_net = gross_income - contractor_result["total_tax"]
        
        savings_potential = contractor_net - employee_net
        
        return {
            "gross_income": gross_income,
            "employee": {
                "irpef_tax": employee_irpef["gross_tax"],
                "inps_contribution": employee_inps["employee_contribution"],
                "net_income": employee_net.quantize(Decimal("0.01")),
                "tax_rate": (employee_irpef["gross_tax"] + employee_inps["employee_contribution"]) / gross_income * 100
            },
            "contractor": {
                "total_tax": contractor_result["total_tax"],
                "net_income": contractor_net.quantize(Decimal("0.01")),
                "tax_rate": contractor_result["effective_rate"]
            },
            "savings_potential": savings_potential.quantize(Decimal("0.01")),
            "recommendation": "contractor" if savings_potential > 0 else "employee"
        }
    
    def optimize_pension_contributions(
        self,
        annual_income: Decimal,
        current_contributions: Decimal
    ) -> Dict[str, Any]:
        """Optimize pension contributions for tax savings."""
        deductions_config = TAX_DEDUCTIONS_2024["pension_contributions"]
        max_deductible = deductions_config["max_amount"]
        
        # Calculate optimal contribution (10% of income or maximum deductible)
        optimal_rate = self.thresholds["pension_contribution_optimal_rate"] / 100
        optimal_contribution = min(annual_income * optimal_rate, max_deductible)
        
        # Calculate tax savings
        marginal_rate = self._get_marginal_tax_rate(annual_income)
        additional_contribution = max(optimal_contribution - current_contributions, Decimal("0"))
        tax_savings = additional_contribution * marginal_rate / 100
        
        return {
            "annual_income": annual_income,
            "current_contributions": current_contributions,
            "recommended_contribution": optimal_contribution.quantize(Decimal("0.01")),
            "additional_contribution": additional_contribution.quantize(Decimal("0.01")),
            "tax_savings": tax_savings.quantize(Decimal("0.01")),
            "marginal_rate": marginal_rate,
            "deduction_rate": Decimal("100.00"),
            "max_deductible": max_deductible
        }
    
    def _get_marginal_tax_rate(self, income: Decimal) -> Decimal:
        """Get marginal tax rate including IRPEF and surcharges."""
        irpef_result = self.irpef_calculator.calculate_irpef(income)
        marginal_irpef = irpef_result["marginal_rate"]
        
        # Add average regional and municipal surcharges
        avg_regional = Decimal("1.73")
        avg_municipal = Decimal("0.60")
        
        return marginal_irpef + avg_regional + avg_municipal


class ItalianTaxCalculator:
    """Main Italian Tax Calculator service integrating all components."""
    
    def __init__(self, db: Optional[AsyncSession] = None, cache: Optional[CacheService] = None):
        self.db = db
        self.cache = cache
        
        # Initialize all calculators
        self.irpef_calculator = IrpefCalculator()
        self.inps_calculator = InpsCalculator()
        self.vat_calculator = VatCalculator()
        self.corporate_calculator = CorporateTaxCalculator()
        self.capital_gains_calculator = CapitalGainsTaxCalculator()
        self.deduction_engine = TaxDeductionEngine()
        self.freelancer_calculator = FreelancerTaxCalculator()
        self.optimization_engine = TaxOptimizationEngine()
        
        # Regional service (if database available)
        if self.db:
            self.regional_service = RegionalTaxService(self.db, cache)
            self.property_calculator = PropertyTaxCalculator(self.regional_service)
        else:
            self.regional_service = None
            self.property_calculator = PropertyTaxCalculator()
    
    async def calculate_net_salary(
        self,
        gross_salary: Decimal,
        location: str,
        employment_type: str = "employee",
        family_status: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calculate net salary with all applicable taxes and contributions.
        
        Args:
            gross_salary: Gross annual salary
            location: CAP or city name
            employment_type: Type of employment
            family_status: Family situation for deductions
            
        Returns:
            Complete net salary calculation
        """
        if gross_salary < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        family_status = family_status or {}
        
        # Calculate base IRPEF
        irpef_result = self.irpef_calculator.calculate_irpef(gross_salary)
        
        # Calculate INPS contributions
        if employment_type == "employee":
            inps_result = self.inps_calculator.calculate_employee_contribution(gross_salary)
        elif employment_type == "executive":
            inps_result = self.inps_calculator.calculate_executive_contribution(gross_salary)
        else:
            inps_result = self.inps_calculator.calculate_self_employed_contribution(gross_salary)
        
        # Calculate regional and municipal surcharges
        regional_municipal_result = await self._calculate_regional_municipal_taxes(gross_salary, location)
        
        # Calculate deductions
        work_deductions = self.deduction_engine.calculate_employee_deductions(gross_salary)
        family_deductions = self.deduction_engine.calculate_family_deductions(**family_status)
        
        total_deductions = work_deductions["total_deductions"] + family_deductions["total_family_deductions"]
        
        # Recalculate IRPEF with deductions
        taxable_income = max(gross_salary - total_deductions, Decimal("0"))
        irpef_with_deductions = self.irpef_calculator.calculate_irpef(taxable_income)
        
        # Calculate total taxes
        total_irpef = irpef_with_deductions["gross_tax"]
        total_inps = inps_result.get("employee_contribution", inps_result.get("contribution", Decimal("0")))
        total_regional = regional_municipal_result["regional_surcharge"]
        total_municipal = regional_municipal_result["municipal_surcharge"]
        
        total_taxes = total_irpef + total_inps + total_regional + total_municipal
        net_salary = gross_salary - total_taxes
        tax_burden_percentage = (total_taxes / gross_salary * 100).quantize(Decimal("0.01"))
        
        return {
            "gross_salary": gross_salary,
            "location": location,
            "employment_type": employment_type,
            "taxable_income": taxable_income,
            "irpef_tax": total_irpef,
            "regional_surcharge": total_regional,
            "municipal_surcharge": total_municipal,
            "inps_employee": total_inps,
            "total_deductions": total_deductions,
            "total_taxes": total_taxes.quantize(Decimal("0.01")),
            "net_salary": net_salary.quantize(Decimal("0.01")),
            "tax_burden_percentage": tax_burden_percentage,
            "effective_rate": irpef_with_deductions["effective_rate"],
            "marginal_rate": irpef_with_deductions["marginal_rate"],
            "deduction_breakdown": {
                "work_deductions": work_deductions["total_deductions"],
                "family_deductions": family_deductions["total_family_deductions"]
            }
        }
    
    async def calculate_freelancer_taxes(
        self,
        annual_revenue: Decimal,
        location: str,
        activity_type: str,
        regime: str = "standard",
        business_expenses: Decimal = Decimal("0")
    ) -> Dict[str, Any]:
        """
        Calculate complete freelancer tax burden.
        
        Args:
            annual_revenue: Annual revenue
            location: CAP or city name  
            activity_type: Type of freelance activity
            regime: Tax regime (standard or forfettario)
            business_expenses: Business expenses (for standard regime)
            
        Returns:
            Complete freelancer tax calculation
        """
        if annual_revenue < 0:
            raise InvalidIncomeError(ERROR_MESSAGES["negative_income"])
        
        if regime == "forfettario":
            # Flat-rate regime calculation
            is_new = annual_revenue <= FLAT_RATE_REGIME_2024["revenue_threshold"]
            tax_result = self.freelancer_calculator.calculate_flat_rate_tax(
                annual_revenue=annual_revenue,
                activity_category=activity_type,
                is_new_business=is_new
            )
            
            # INPS still applies in flat-rate regime
            inps_result = self.inps_calculator.calculate_self_employed_contribution(
                tax_result["taxable_income"]
            )
            
            total_tax_burden = tax_result["tax_amount"] + inps_result["contribution"]
            
            return {
                **tax_result,
                "inps_contribution": inps_result["contribution"],
                "total_tax_burden": total_tax_burden.quantize(Decimal("0.01")),
                "net_income": (annual_revenue - total_tax_burden).quantize(Decimal("0.01")),
                "vat_due": Decimal("0"),  # VAT exempt in flat-rate regime
                "quarterly_payments": await self._calculate_quarterly_estimates(total_tax_burden)
            }
        else:
            # Standard regime calculation
            region, municipality = await self._extract_location_info(location)
            
            tax_result = self.freelancer_calculator.calculate_standard_regime_tax(
                annual_revenue=annual_revenue,
                business_expenses=business_expenses,
                region=region,
                municipality=municipality
            )
            
            # Calculate VAT on revenue
            vat_result = self.vat_calculator.calculate_vat(annual_revenue, "standard")
            
            return {
                **tax_result,
                "vat_due": vat_result["vat_amount"],
                "quarterly_payments": await self._calculate_quarterly_estimates(tax_result["total_tax"]),
                "net_income": (annual_revenue - tax_result["total_tax"]).quantize(Decimal("0.01"))
            }
    
    def compare_scenarios(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare tax burden across multiple scenarios."""
        results = []
        
        for scenario in scenarios:
            # This would call the appropriate calculation method based on scenario type
            # Simplified implementation for now
            results.append({
                "scenario": scenario,
                "net_income": Decimal("30000"),  # Placeholder
                "tax_burden": Decimal("10000"),  # Placeholder
                "effective_rate": Decimal("25.00")  # Placeholder
            })
        
        # Find best scenario
        best_scenario = max(results, key=lambda x: x["net_income"])
        worst_scenario = min(results, key=lambda x: x["net_income"])
        tax_savings = best_scenario["net_income"] - worst_scenario["net_income"]
        
        return {
            "scenarios": results,
            "best_option": best_scenario,
            "worst_option": worst_scenario,
            "tax_savings": tax_savings.quantize(Decimal("0.01"))
        }
    
    def process_natural_language_query(self, query: str) -> Dict[str, Any]:
        """Process natural language tax queries."""
        query_lower = query.lower()
        
        # Simple pattern matching (would use more sophisticated NLP in production)
        if "net salary" in query_lower or "stipendio netto" in query_lower:
            # Extract gross income and location
            income_match = re.search(r'(\d+[.,]?\d*)', query)
            location_match = re.search(r'(milan|roma|napoli|torino|milano)', query_lower)
            
            gross_income = Decimal(income_match.group(1).replace(',', '')) if income_match else Decimal("35000")
            location = location_match.group(1) if location_match else "Milan"
            
            return {
                "understood_intent": "net_salary_calculation",
                "extracted_parameters": {
                    "gross_income": gross_income,
                    "location": location
                },
                "calculation_result": None  # Would call calculate_net_salary
            }
        
        return {
            "understood_intent": "unknown",
            "query": query,
            "suggestions": ["Try asking about net salary calculations", "Ask about freelancer taxes"]
        }
    
    def get_tax_calendar(self, taxpayer_type: str, current_date: date) -> Dict[str, Any]:
        """Get relevant tax calendar and deadlines."""
        calendar = TAX_CALENDAR_2024
        upcoming_deadlines = []
        
        # Income tax return
        if current_date < calendar["income_tax_return"]["filing_deadline"]:
            upcoming_deadlines.append({
                "type": "income_tax_return",
                "deadline": calendar["income_tax_return"]["filing_deadline"],
                "description": calendar["income_tax_return"]["description"]
            })
        
        # Quarterly payments for freelancers
        if taxpayer_type == "freelancer":
            for payment in calendar["quarterly_payments"]:
                if current_date < payment["deadline"]:
                    upcoming_deadlines.append({
                        "type": "quarterly_payment",
                        "deadline": payment["deadline"],
                        "description": payment["description"],
                        "quarter": payment["quarter"]
                    })
        
        return {
            "taxpayer_type": taxpayer_type,
            "current_date": current_date.isoformat(),
            "upcoming_deadlines": upcoming_deadlines,
            "quarterly_payments": calendar["quarterly_payments"] if taxpayer_type == "freelancer" else []
        }
    
    async def _calculate_regional_municipal_taxes(
        self, 
        income: Decimal, 
        location: str
    ) -> Dict[str, Any]:
        """Calculate regional and municipal IRPEF surcharges."""
        if self.regional_service:
            try:
                # Use regional service if available
                result = await self.regional_service.calculate_irpef_addizionali(income, location)
                return {
                    "regional_surcharge": Decimal(str(result["addizionale_regionale"]["importo"])),
                    "municipal_surcharge": Decimal(str(result["addizionale_comunale"]["importo"])),
                    "location": result["comune"],
                    "region": result["regione"]
                }
            except Exception as e:
                logger.warning(f"Regional tax calculation failed: {e}")
        
        # Fallback to defaults
        return {
            "regional_surcharge": income * Decimal("1.73") / 100,  # Default regional rate
            "municipal_surcharge": income * Decimal("0.60") / 100,  # Default municipal rate
            "location": location,
            "region": "Unknown"
        }
    
    async def _extract_location_info(self, location: str) -> Tuple[str, str]:
        """Extract region and municipality from location string."""
        if self.regional_service:
            try:
                if len(location) == 5 and location.isdigit():  # CAP
                    comune = await self.regional_service.get_comune_by_cap(location)
                    if comune:
                        regione = await self.regional_service.get_regione_by_id(comune.regione_id)
                        return regione.nome if regione else "Lombardia", comune.nome
                else:  # City name
                    comune = await self.regional_service.get_comune_by_name(location)
                    if comune:
                        regione = await self.regional_service.get_regione_by_id(comune.regione_id)
                        return regione.nome if regione else "Lombardia", comune.nome
            except Exception as e:
                logger.warning(f"Location extraction failed: {e}")
        
        # Default fallback
        return "Lombardia", location
    
    async def _calculate_quarterly_estimates(self, annual_tax: Decimal) -> List[Dict[str, Any]]:
        """Calculate quarterly tax payment estimates."""
        quarterly_amount = annual_tax / 4
        
        return [
            {
                "quarter": 1,
                "amount": quarterly_amount.quantize(Decimal("0.01")),
                "due_date": date(2024, 6, 17),
                "description": "First quarterly advance payment"
            },
            {
                "quarter": 2, 
                "amount": quarterly_amount.quantize(Decimal("0.01")),
                "due_date": date(2024, 11, 30),
                "description": "Second quarterly advance payment"
            }
        ]