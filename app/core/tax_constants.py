"""Italian Tax Constants and Configuration.

This module contains all the tax rates, brackets, thresholds, and constants
for Italian tax calculations as of 2024.
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List


class TaxRegime(Enum):
    """Tax regimes for different business types."""

    STANDARD = "standard"
    FLAT_RATE = "forfettario"
    SIMPLIFIED = "simplified"


class EmploymentType(Enum):
    """Types of employment relationships."""

    EMPLOYEE = "employee"
    EXECUTIVE = "executive"
    SELF_EMPLOYED = "self_employed"
    FREELANCER = "freelancer"


class BusinessType(Enum):
    """Types of business activities."""

    STANDARD = "standard"
    MANUFACTURING = "manufacturing"
    SERVICES = "services"
    HEALTHCARE = "healthcare"
    BANKING = "banking"


class VatCategory(Enum):
    """VAT categories with different rates."""

    STANDARD = "standard"
    REDUCED_10 = "reduced_10"
    REDUCED_4 = "reduced_4"
    EXEMPT = "exempt"


# IRPEF Tax Brackets for 2024
IRPEF_BRACKETS_2024 = [
    {
        "min_income": Decimal("0"),
        "max_income": Decimal("15000"),
        "rate": Decimal("23"),
        "description": "First bracket (23%)",
    },
    {
        "min_income": Decimal("15000"),
        "max_income": Decimal("28000"),
        "rate": Decimal("25"),
        "description": "Second bracket (25%)",
    },
    {
        "min_income": Decimal("28000"),
        "max_income": Decimal("55000"),
        "rate": Decimal("35"),
        "description": "Third bracket (35%)",
    },
    {
        "min_income": Decimal("55000"),
        "max_income": None,  # No upper limit
        "rate": Decimal("43"),
        "description": "Fourth bracket (43%)",
    },
]

# Regional IRPEF Surcharge Rates 2024 (%)
REGIONAL_IRPEF_SURCHARGE_2024 = {
    "Abruzzo": Decimal("1.73"),
    "Basilicata": Decimal("1.23"),
    "Calabria": Decimal("1.73"),
    "Campania": Decimal("1.73"),
    "Emilia-Romagna": Decimal("1.73"),
    "Friuli-Venezia Giulia": Decimal("1.23"),
    "Lazio": Decimal("1.73"),
    "Liguria": Decimal("1.68"),
    "Lombardia": Decimal("1.23"),
    "Marche": Decimal("1.73"),
    "Molise": Decimal("1.73"),
    "Piemonte": Decimal("1.68"),
    "Puglia": Decimal("1.73"),
    "Sardegna": Decimal("1.23"),
    "Sicilia": Decimal("1.73"),
    "Toscana": Decimal("1.73"),
    "Trentino-Alto Adige": Decimal("0.00"),  # Special status
    "Umbria": Decimal("1.73"),
    "Valle d'Aosta": Decimal("0.00"),  # Special status
    "Veneto": Decimal("1.23"),
}

# Municipal IRPEF Configuration 2024
MUNICIPAL_IRPEF_CONFIG = {
    "default_rate": Decimal("0.60"),
    "default_threshold": Decimal("11000"),
    "typical_rates": {
        "Milano": {"rate": Decimal("0.80"), "threshold": Decimal("12000")},
        "Roma": {"rate": Decimal("0.60"), "threshold": Decimal("11500")},
        "Napoli": {"rate": Decimal("0.80"), "threshold": Decimal("11000")},
        "Torino": {"rate": Decimal("0.80"), "threshold": Decimal("11000")},
        "Palermo": {"rate": Decimal("0.80"), "threshold": Decimal("11000")},
        "Genova": {"rate": Decimal("0.70"), "threshold": Decimal("11000")},
        "Bologna": {"rate": Decimal("0.80"), "threshold": Decimal("11500")},
        "Firenze": {"rate": Decimal("0.80"), "threshold": Decimal("12000")},
        "Bari": {"rate": Decimal("0.80"), "threshold": Decimal("11000")},
        "Catania": {"rate": Decimal("0.80"), "threshold": Decimal("11000")},
    },
}

# INPS Rates 2024
INPS_RATES_2024 = {
    "employee": {
        "rate": Decimal("9.19"),  # Employee portion
        "ceiling": Decimal("119650"),  # Annual contribution ceiling
        "description": "Employee INPS contributions",
    },
    "employer": {
        "rate": Decimal("30.00"),  # Average employer portion (varies by sector)
        "description": "Employer INPS contributions",
    },
    "executive": {
        "rate_below_ceiling": Decimal("10.00"),
        "rate_above_ceiling": Decimal("3.00"),
        "ceiling": Decimal("103055"),
        "description": "Executive INPS contributions",
    },
    "self_employed_separate": {
        "rate_exclusive_coverage": Decimal("25.98"),  # Without other pension coverage
        "rate_with_other_coverage": Decimal("25.98"),
        "rate_with_dis_coll": Decimal("25.72"),  # With unemployment coverage
        "rate_without_dis_coll": Decimal("25.98"),  # Without unemployment coverage
        "description": "Self-employed separate fund (Gestione Separata)",
    },
}

# VAT Rates 2024
VAT_RATES_2024 = {
    VatCategory.STANDARD: {"rate": Decimal("22"), "description": "Standard VAT rate - most goods and services"},
    VatCategory.REDUCED_10: {
        "rate": Decimal("10"),
        "description": "Reduced VAT rate - food, hotels, restaurants, books",
    },
    VatCategory.REDUCED_4: {
        "rate": Decimal("4"),
        "description": "Super reduced VAT rate - essential goods, newspapers",
    },
    VatCategory.EXEMPT: {
        "rate": Decimal("0"),
        "description": "VAT exempt - healthcare, education, financial services",
    },
}

# Corporate Tax Rates 2024
CORPORATE_TAX_RATES_2024 = {
    "ires": {
        "standard_rate": Decimal("24"),
        "reduced_rate_2025": Decimal("20"),  # Planned reduction
        "description": "IRES - Corporate Income Tax",
    },
    "irap": {
        "standard_rate": Decimal("3.9"),
        "banking_rate": Decimal("4.65"),
        "insurance_rate": Decimal("5.90"),
        "description": "IRAP - Regional Business Tax",
    },
}

# Property Tax (IMU) Configuration 2024
IMU_CONFIG_2024 = {
    "standard_rate": Decimal("0.86"),  # Standard municipal rate (per mille)
    "cadastral_value_multiplier": Decimal("1.05"),  # Revaluation coefficient
    "taxable_base_coefficient": Decimal("160"),  # Category multiplier for residential
    "exemptions": {
        "primary_residence": True,  # Prima casa exemption
        "luxury_categories": ["A/1", "A/8", "A/9"],  # Categories not exempt
    },
    "payment_schedule": {
        "first_installment": {"due_date": date(2024, 6, 17), "percentage": 50},
        "second_installment": {"due_date": date(2024, 12, 16), "percentage": 50},
    },
}

# Capital Gains Tax 2024
CAPITAL_GAINS_TAX_2024 = {
    "financial": {"rate": Decimal("26"), "description": "Capital gains on financial instruments"},
    "real_estate": {
        "rate": Decimal("26"),
        "exemption_period_days": 1825,  # 5 years for exemption
        "description": "Capital gains on real estate (within 5 years)",
    },
    "cryptocurrency": {
        "rate": Decimal("26"),
        "threshold": Decimal("2000"),  # Annual threshold for exemption
        "description": "Capital gains on cryptocurrencies",
    },
    "business": {
        "rate": Decimal("26"),
        "participation_exemption": True,
        "description": "Capital gains on business participations",
    },
}

# Flat Rate Regime (Regime Forfettario) 2024
FLAT_RATE_REGIME_2024 = {
    "revenue_threshold": Decimal("85000"),
    "standard_rate": Decimal("15"),  # Tax rate on taxable income
    "new_business_rate": Decimal("5"),  # First 5 years for new businesses
    "activity_coefficients": {
        "trade": Decimal("0.40"),
        "manufacturing": Decimal("0.86"),
        "construction": Decimal("0.86"),
        "services": Decimal("0.78"),
        "professional_services": Decimal("0.78"),
        "consulting": Decimal("0.67"),
        "technical_services": Decimal("0.78"),
        "healthcare": Decimal("0.67"),
        "education": Decimal("0.67"),
        "other_services": Decimal("0.67"),
    },
    "description": "Simplified tax regime for small businesses and professionals",
}

# Tax Deductions 2024
TAX_DEDUCTIONS_2024 = {
    "work_income": {
        "employee_base": Decimal("1880"),  # Base deduction for employees
        "pensioner_base": Decimal("1955"),  # Base deduction for pensioners
        "description": "Work income deductions",
    },
    "family": {
        "spouse": {
            "base_deduction": Decimal("800"),
            "income_threshold": Decimal("2840.51"),
            "description": "Spouse deduction",
        },
        "children": {
            "base_deduction": Decimal("950"),
            "under_3_additional": Decimal("270"),
            "disabled_additional": Decimal("400"),
            "description": "Children deductions",
        },
    },
    "medical_expenses": {
        "threshold": Decimal("129.11"),  # Franchise amount
        "deduction_rate": Decimal("19"),
        "description": "Medical expenses deduction",
    },
    "home_renovations": {
        "ecobonus": {
            "rate": Decimal("65"),
            "max_amount": Decimal("60000"),
            "description": "Energy efficiency renovations",
        },
        "sismabonus": {
            "rate": Decimal("110"),  # Superbonus rate
            "max_amount": Decimal("96000"),
            "description": "Seismic safety renovations",
        },
        "bonus_facciate": {
            "rate": Decimal("60"),
            "max_amount": Decimal("60000"),
            "description": "Building facade renovations",
        },
        "superbonus": {
            "rate": Decimal("90"),  # Reduced from 110% in 2024
            "max_amount": Decimal("96000"),
            "description": "Super energy efficiency bonus",
        },
    },
    "pension_contributions": {"max_amount": Decimal("5164.57"), "description": "Supplementary pension contributions"},
}

# Withholding Tax Rates 2024
WITHHOLDING_TAX_2024 = {
    "professional_services": Decimal("20"),
    "consulting": Decimal("20"),
    "dividends": Decimal("26"),
    "interest": Decimal("26"),
    "rental_income": Decimal("21"),  # Cedolare secca
    "employment_income": "progressive",  # Uses IRPEF brackets
    "pension_income": "progressive",
}

# Tax Calendar 2024
TAX_CALENDAR_2024 = {
    "income_tax_return": {
        "filing_deadline": date(2024, 10, 31),
        "payment_deadline": date(2024, 11, 30),
        "description": "Annual income tax return (Modello 730 or Redditi)",
    },
    "quarterly_payments": [
        {"quarter": 1, "deadline": date(2024, 6, 17), "description": "First quarterly advance payment"},
        {"quarter": 2, "deadline": date(2024, 11, 30), "description": "Second quarterly advance payment"},
    ],
    "vat_quarterly": [
        {"quarter": 1, "deadline": date(2024, 4, 16), "description": "Q1 VAT return"},
        {"quarter": 2, "deadline": date(2024, 7, 16), "description": "Q2 VAT return"},
        {"quarter": 3, "deadline": date(2024, 10, 16), "description": "Q3 VAT return"},
        {
            "quarter": 4,
            "deadline": date(2024, 1, 16),  # Following year
            "description": "Q4 VAT return",
        },
    ],
    "imu_payments": [
        {"installment": 1, "deadline": date(2024, 6, 17), "description": "First IMU installment"},
        {"installment": 2, "deadline": date(2024, 12, 16), "description": "Second IMU installment (balance)"},
    ],
}

# Regional Special Provisions
REGIONAL_SPECIAL_PROVISIONS = {
    "Trentino-Alto Adige": {"autonomous_province": True, "special_irpef_rates": True, "reduced_irap": True},
    "Valle d'Aosta": {"autonomous_region": True, "no_regional_surcharge": True, "reduced_irap": True},
    "Friuli-Venezia Giulia": {"autonomous_region": True, "reduced_regional_surcharge": True},
    "Sicilia": {"autonomous_region": True, "special_provisions": True},
    "Sardegna": {"autonomous_region": True, "reduced_regional_surcharge": True},
}

# Tax Optimization Thresholds
TAX_OPTIMIZATION_THRESHOLDS = {
    "flat_rate_threshold": Decimal("85000"),
    "vat_threshold": Decimal("65000"),
    "pension_contribution_optimal_rate": Decimal("10"),  # % of income
    "renovation_deduction_optimal": Decimal("50000"),
    "dividend_tax_optimization": Decimal("40000"),
    "real_estate_exemption_years": 5,
}

# Validation Limits
VALIDATION_LIMITS = {
    "max_annual_income": Decimal("10000000"),  # €10M
    "min_annual_income": Decimal("0"),
    "max_vat_amount": Decimal("1000000"),  # €1M
    "max_property_value": Decimal("50000000"),  # €50M
    "max_deduction_amount": Decimal("500000"),  # €500K
}

# Error Messages
ERROR_MESSAGES = {
    "negative_income": "Income cannot be negative",
    "exceeds_flat_rate_threshold": "Revenue exceeds flat-rate regime threshold",
    "invalid_location": "Invalid location or CAP code",
    "invalid_tax_type": "Unsupported tax type",
    "calculation_error": "Error in tax calculation",
    "data_not_found": "Tax data not found for specified parameters",
}
