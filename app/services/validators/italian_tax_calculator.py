"""Italian Tax Calculator service following TDD principles.

This module provides the classes and methods required by the test suite
to implement comprehensive Italian tax calculations.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Import the main calculator from the services module
from app.services.italian_tax_calculator import ItalianTaxCalculator as MainCalculator


class TaxYear(Enum):
    """Supported tax years."""

    YEAR_2023 = 2023
    YEAR_2024 = 2024
    YEAR_2025 = 2025


class IVARate(Enum):
    """IVA (VAT) rate categories."""

    STANDARD = "standard"  # 22%
    REDUCED = "reduced_10"  # 10%
    SUPER_REDUCED = "reduced_4"  # 4%
    EXEMPT = "exempt"  # 0%


class DeductionType(Enum):
    """Types of tax deductions."""

    EMPLOYEE = "employee"
    SPOUSE = "spouse"
    CHILD = "child"
    MEDICAL = "medical"
    RENOVATION = "renovation"
    PENSION = "pension"


class TaxCreditType(Enum):
    """Types of tax credits."""

    SPOUSE = "spouse"
    CHILD = "child"
    WORK = "work"
    PENSION = "pension"


@dataclass
class IRPEFBracket:
    """IRPEF tax bracket definition."""

    min_income: Decimal
    max_income: Decimal | None
    rate: Decimal
    description: str


@dataclass
class TaxResult:
    """Result of tax calculation with detailed breakdown."""

    gross_amount: Decimal
    tax_amount: Decimal
    effective_rate: Decimal
    taxable_income: Decimal | None = None
    deductions_applied: Decimal = field(default_factory=lambda: Decimal("0"))
    tax_credits_applied: Decimal = field(default_factory=lambda: Decimal("0"))
    calculation_steps: list[dict[str, Any]] = field(default_factory=list)
    formula: str = ""

    # VAT-specific fields
    net_amount: Decimal | None = None
    iva_amount: Decimal | None = None
    gross_amount_vat: Decimal | None = None
    rate_applied: Decimal | None = None

    # Withholding tax fields
    withholding_amount: Decimal | None = None
    net_payment: Decimal | None = None

    # IRAP fields
    taxable_base: Decimal | None = None


class ItalianTaxCalculator:
    """TDD-compliant Italian Tax Calculator."""

    def __init__(self, tax_year: int = 2024):
        """Initialize calculator for specified tax year."""
        if tax_year < 2020 or tax_year > 2029:
            raise ValueError("Tax year must be between 2020 and 2029")

        self.tax_year = tax_year
        self._main_calculator = MainCalculator()

        # IRPEF brackets for 2024 (updated to match TDD test expectations)
        self.irpef_brackets = [
            IRPEFBracket(Decimal("0"), Decimal("15000"), Decimal("23"), "0 - 15,000 (23%)"),
            IRPEFBracket(Decimal("15000"), Decimal("28000"), Decimal("25"), "15,000 - 28,000 (25%)"),
            IRPEFBracket(Decimal("28000"), Decimal("55000"), Decimal("35"), "28,000 - 55,000 (35%)"),
            IRPEFBracket(Decimal("55000"), None, Decimal("43"), "55,000+ (43%)"),
        ]

    def calculate_irpef(
        self, gross_income: Decimal, deductions: list[dict[str, Any]] = None, tax_credits: list[dict[str, Any]] = None
    ) -> TaxResult:
        """Calculate IRPEF with deductions and tax credits."""
        if gross_income < 0:
            raise ValueError("Income cannot be negative")

        deductions = deductions or []
        tax_credits = tax_credits or []

        if gross_income == 0:
            return TaxResult(
                gross_amount=gross_income,
                tax_amount=Decimal("0"),
                effective_rate=Decimal("0"),
                taxable_income=Decimal("0"),
                calculation_steps=[],
                formula="IRPEF 2024: €0 income = €0 tax",
            )

        # Apply deductions
        total_deductions = sum(d["amount"] for d in deductions)
        taxable_income = max(gross_income - total_deductions, Decimal("0"))

        # Calculate tax using brackets
        tax_amount = Decimal("0")
        calculation_steps = []
        remaining_income = taxable_income

        for bracket in self.irpef_brackets:
            if remaining_income <= 0:
                break

            bracket_min = bracket.min_income
            bracket_max = bracket.max_income or Decimal("999999999")

            if taxable_income > bracket_min:
                if bracket.max_income is None:  # Top bracket
                    bracket_income = remaining_income
                else:
                    bracket_width = bracket_max - bracket_min
                    bracket_income = min(remaining_income, bracket_width)

                bracket_tax = bracket_income * bracket.rate / 100
                tax_amount += bracket_tax

                calculation_steps.append(
                    {
                        "bracket": f"{bracket.rate}%",
                        "taxable_amount": bracket_income,
                        "amount": bracket_tax,
                        "type": "irpef_bracket",
                    }
                )

                remaining_income -= bracket_income

        # Apply tax credits
        total_credits = sum(c["amount"] for c in tax_credits)

        for credit in tax_credits:
            calculation_steps.append(
                {
                    "type": f"{credit['type'].value}_credit",
                    "amount": credit["amount"],
                    "description": f"Tax credit: {credit['type'].value}",
                }
            )

        final_tax = max(tax_amount - total_credits, Decimal("0"))
        effective_rate = (final_tax / gross_income * 100) if gross_income > 0 else Decimal("0")

        formula = f"IRPEF {self.tax_year}: "
        if len(calculation_steps) > 0:
            formula += f"Tax on €{taxable_income:,.2f}"
            if total_credits > 0:
                formula += f" - €{total_credits:,.2f} credits"
            formula += f" = €{final_tax:,.2f}"

        return TaxResult(
            gross_amount=gross_income,
            tax_amount=final_tax.quantize(Decimal("0.01")),
            effective_rate=effective_rate.quantize(Decimal("0.01")),
            taxable_income=taxable_income,
            deductions_applied=total_deductions,
            tax_credits_applied=total_credits,
            calculation_steps=calculation_steps,
            formula=formula,
        )

    def calculate_iva(self, net_amount: Decimal, rate: IVARate, calculation_type: str = "add_iva") -> TaxResult:
        """Calculate IVA (VAT)."""
        if net_amount < 0:
            raise ValueError("Net amount cannot be negative")

        if not isinstance(rate, IVARate):
            raise ValueError("Invalid IVA rate")

        # Map IVA rates
        rate_map = {
            IVARate.STANDARD: Decimal("22"),
            IVARate.REDUCED: Decimal("10"),
            IVARate.SUPER_REDUCED: Decimal("4"),
            IVARate.EXEMPT: Decimal("0"),
        }

        iva_rate = rate_map[rate]

        if calculation_type == "add_iva":
            iva_amount = net_amount * iva_rate / 100
            gross_amount = net_amount + iva_amount
            formula = f"€{net_amount:,.2f} + (€{net_amount:,.2f} × {iva_rate}%) = €{gross_amount:,.2f}"
        elif calculation_type == "extract_iva":
            # Reverse calculation
            if iva_rate == 0:
                iva_amount = Decimal("0")
                actual_net = net_amount
            else:
                divisor = 1 + iva_rate / 100
                actual_net = net_amount / divisor
                iva_amount = net_amount - actual_net
            gross_amount = net_amount
            net_amount = actual_net
            formula = f"€{gross_amount:,.2f} ÷ {divisor:.2f} = €{net_amount:,.2f} (net) + €{iva_amount:,.2f} (IVA)"
        else:
            raise ValueError("Invalid calculation type")

        return TaxResult(
            net_amount=net_amount.quantize(Decimal("0.01")),
            iva_amount=iva_amount.quantize(Decimal("0.01")),
            gross_amount_vat=gross_amount.quantize(Decimal("0.01")),
            rate_applied=iva_rate,
            formula=formula,
            # Legacy fields for compatibility
            gross_amount=gross_amount.quantize(Decimal("0.01")),
            tax_amount=iva_amount.quantize(Decimal("0.01")),
            effective_rate=iva_rate,
        )

    def calculate_ires(self, taxable_income: Decimal, startup_incentive: bool = False) -> TaxResult:
        """Calculate IRES (Corporate Income Tax)."""
        if taxable_income < 0:
            raise ValueError("Taxable income cannot be negative")

        if startup_incentive:
            rate = Decimal("12")  # Reduced rate for startups
        else:
            rate = Decimal("24")  # Standard IRES rate

        tax_amount = taxable_income * rate / 100

        formula = f"IRES: €{taxable_income:,.2f} × {rate}% = €{tax_amount:,.2f}"
        if startup_incentive:
            formula += " (startup incentive rate)"

        return TaxResult(
            gross_amount=taxable_income,
            tax_amount=tax_amount.quantize(Decimal("0.01")),
            effective_rate=rate,
            rate_applied=rate,
            formula=formula,
        )

    def calculate_irap(self, production_value: Decimal, deductions: list[dict[str, Any]] = None) -> TaxResult:
        """Calculate IRAP (Regional Business Tax)."""
        if production_value < 0:
            raise ValueError("Production value cannot be negative")

        deductions = deductions or []
        total_deductions = sum(d["amount"] for d in deductions)
        taxable_base = max(production_value - total_deductions, Decimal("0"))

        rate = Decimal("3.9")  # Standard IRAP rate
        tax_amount = taxable_base * rate / 100

        formula = f"IRAP: €{production_value:,.2f}"
        if total_deductions > 0:
            formula += f" - €{total_deductions:,.2f} (deductions)"
        formula += f" × {rate}% = €{tax_amount:,.2f}"

        return TaxResult(
            gross_amount=production_value,
            taxable_income=taxable_base,
            taxable_base=taxable_base,
            tax_amount=tax_amount.quantize(Decimal("0.01")),
            effective_rate=rate,
            rate_applied=rate,
            deductions_applied=total_deductions,
            formula=formula,
        )

    def calculate_withholding_tax(self, gross_amount: Decimal, withholding_type: str, rate: Decimal) -> TaxResult:
        """Calculate withholding tax (Ritenuta d'Acconto)."""
        if gross_amount < 0:
            raise ValueError("Gross amount cannot be negative")

        withholding_amount = gross_amount * rate / 100
        net_payment = gross_amount - withholding_amount

        rate_str = f"{rate:.0f}" if rate == int(rate) else f"{rate:.2f}"
        formula = f"Ritenuta: €{gross_amount:,.2f} × {rate_str}% = €{withholding_amount:,.2f}"

        return TaxResult(
            gross_amount=gross_amount,
            tax_amount=withholding_amount.quantize(Decimal("0.01")),
            withholding_amount=withholding_amount.quantize(Decimal("0.01")),
            net_payment=net_payment.quantize(Decimal("0.01")),
            rate_applied=rate,
            effective_rate=rate,
            formula=formula,
        )

    def calculate_complete_individual_taxes(
        self,
        gross_income: Decimal,
        deductions: list[dict[str, Any]] = None,
        tax_credits: list[dict[str, Any]] = None,
        region: str = "lombardy",
    ) -> dict[str, Any]:
        """Calculate complete individual tax burden."""
        deductions = deductions or []
        tax_credits = tax_credits or []

        # IRPEF calculation
        irpef_result = self.calculate_irpef(gross_income, deductions, tax_credits)

        # Regional and municipal taxes (simplified)
        regional_rate = Decimal("1.73")  # Average rate
        municipal_rate = Decimal("0.60")  # Average rate

        regional_tax = irpef_result.taxable_income * regional_rate / 100
        municipal_tax = irpef_result.taxable_income * municipal_rate / 100

        total_tax = irpef_result.tax_amount + regional_tax + municipal_tax

        return {
            "irpef": {
                "amount": irpef_result.tax_amount,
                "rate": irpef_result.effective_rate,
                "taxable_income": irpef_result.taxable_income,
            },
            "regional_tax": {"amount": regional_tax.quantize(Decimal("0.01")), "rate": regional_rate},
            "municipal_tax": {"amount": municipal_tax.quantize(Decimal("0.01")), "rate": municipal_rate},
            "total_tax": {
                "amount": total_tax.quantize(Decimal("0.01")),
                "effective_rate": (total_tax / gross_income * 100).quantize(Decimal("0.01")),
            },
            "calculation_summary": [
                f"IRPEF: €{irpef_result.tax_amount:,.2f}",
                f"Regional surcharge: €{regional_tax:,.2f}",
                f"Municipal surcharge: €{municipal_tax:,.2f}",
                f"Total: €{total_tax:,.2f}",
            ],
        }

    def calculate_complete_company_taxes(
        self, taxable_income: Decimal, production_value: Decimal, region: str = "lazio"
    ) -> dict[str, Any]:
        """Calculate complete company tax burden."""
        ires_result = self.calculate_ires(taxable_income)
        irap_result = self.calculate_irap(production_value)

        total_tax = ires_result.tax_amount + irap_result.tax_amount

        return {
            "ires": {
                "amount": ires_result.tax_amount,
                "rate": ires_result.rate_applied,
                "taxable_income": taxable_income,
            },
            "irap": {
                "amount": irap_result.tax_amount,
                "rate": irap_result.rate_applied,
                "production_value": production_value,
            },
            "total_tax": {
                "amount": total_tax.quantize(Decimal("0.01")),
                "effective_rate": (total_tax / taxable_income * 100).quantize(Decimal("0.01")),
            },
        }
