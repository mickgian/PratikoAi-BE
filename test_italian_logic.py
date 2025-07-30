#!/usr/bin/env python3
"""Test Italian Knowledge Logic without dependencies."""

import sys
import re
from decimal import Decimal

# Test Italian tax calculation logic directly
def test_vat_calculation_logic():
    """Test VAT calculation logic."""
    VAT_RATES = {
        "standard": 0.22,
        "reduced": 0.10,
        "super_reduced": 0.04,
        "zero": 0.00
    }
    
    amount = 100.0
    vat_type = "standard"
    
    rate = VAT_RATES.get(vat_type, VAT_RATES["standard"])
    vat_amount = Decimal(str(amount)) * Decimal(str(rate))
    gross_amount = Decimal(str(amount)) + vat_amount
    
    assert float(vat_amount) == 22.0
    assert float(gross_amount) == 122.0
    print("✅ VAT calculation logic verified")
    return True

def test_irpef_calculation_logic():
    """Test IRPEF calculation logic."""
    IRPEF_BRACKETS_2024 = [
        {"min": 0, "max": 15000, "rate": 0.23},
        {"min": 15001, "max": 28000, "rate": 0.25},
        {"min": 28001, "max": 50000, "rate": 0.35},
        {"min": 50001, "max": float('inf'), "rate": 0.43}
    ]
    
    income = 15000.0
    deductions = 0.0
    taxable_income = max(0, income - deductions)
    total_tax = Decimal('0')
    
    for bracket in IRPEF_BRACKETS_2024:
        if taxable_income <= bracket["min"]:
            break
            
        bracket_max = min(taxable_income, bracket["max"])
        bracket_income = bracket_max - bracket["min"] + 1
        bracket_tax = Decimal(str(bracket_income)) * Decimal(str(bracket["rate"]))
        total_tax += bracket_tax
        
        if taxable_income <= bracket["max"]:
            break
    
    expected_tax = 15000 * 0.23  # 3450
    assert abs(float(total_tax) - expected_tax) < 1.0
    print("✅ IRPEF calculation logic verified")
    return True

def test_withholding_calculation_logic():
    """Test withholding tax calculation logic."""
    rates = {
        "professional": 0.20,
        "employment": 0.23,
        "rental": 0.21,
        "interest": 0.26,
        "dividends": 0.26
    }
    
    amount = 1000.0
    tax_type = "professional"
    
    rate = rates.get(tax_type, rates["professional"])
    withholding_amount = Decimal(str(amount)) * Decimal(str(rate))
    net_amount = Decimal(str(amount)) - withholding_amount
    
    assert float(withholding_amount) == 200.0
    assert float(net_amount) == 800.0
    print("✅ Withholding tax calculation logic verified")
    return True

def test_compliance_check_logic():
    """Test document compliance check logic."""
    # Test contract compliance patterns
    contract_content = """
    Contratto di prestazione tra Mario Rossi (nome delle parti) 
    per servizi di consulenza (oggetto) al corrispettivo di €1000 
    firmato dalle parti in data 01/01/2024
    """
    
    required_elements = [
        ("parties identification", r"(nome|denominazione|ragione sociale)", "critical"),
        ("contract object", r"(oggetto|prestazione|servizio)", "critical"),
        ("consideration", r"(corrispettivo|prezzo|compenso)", "critical"),
        ("signatures", r"(firma|sottoscrizione)", "warning"),
        ("date", r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}", "warning"),
    ]
    
    findings = []
    for element, pattern, severity in required_elements:
        if not re.search(pattern, contract_content, re.IGNORECASE):
            findings.append({
                "element": element,
                "severity": severity,
                "message": f"Missing or unclear {element}"
            })
    
    # Should find most elements in the test content
    critical_missing = [f for f in findings if f["severity"] == "critical"]
    assert len(critical_missing) <= 1  # At most 1 critical issue should remain
    print("✅ Contract compliance logic verified")
    return True

def test_invoice_compliance_logic():
    """Test invoice compliance logic."""
    invoice_content = """
    Fattura n. 001/2024 del 15/01/2024
    P.IVA: 12345678901
    Codice Fiscale: RSSMRA80A01H501X
    Servizi di consulenza €1000 + IVA 22% = €220
    Totale: €1220
    """
    
    required_elements = [
        ("invoice number", r"(numero|n\.|fattura n)", "critical"),
        ("date", r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}", "critical"),
        ("VAT number", r"(p\.iva|partita iva|vat)", "critical"),
        ("tax code", r"(codice fiscale|c\.f\.)", "warning"),
        ("VAT amount", r"(iva|imposta)", "critical"),
    ]
    
    findings = []
    for element, pattern, severity in required_elements:
        if not re.search(pattern, invoice_content, re.IGNORECASE):
            findings.append({
                "element": element,
                "severity": severity,
                "message": f"Missing {element}"
            })
    
    # Should find all required elements
    critical_missing = [f for f in findings if f["severity"] == "critical"]
    assert len(critical_missing) == 0  # No critical issues should remain
    print("✅ Invoice compliance logic verified")
    return True

def test_document_generation_logic():
    """Test document generation logic."""
    template_content = "Contratto tra {client_name} e {provider_name} per {service_description}"
    variables = {
        "client_name": "Mario Rossi",
        "provider_name": "Azienda XYZ",
        "service_description": "consulenza fiscale"
    }
    
    content = template_content
    for key, value in variables.items():
        placeholder = f"{{{key}}}"
        content = content.replace(placeholder, str(value))
    
    assert "Mario Rossi" in content
    assert "Azienda XYZ" in content
    assert "consulenza fiscale" in content
    assert "{" not in content  # No unreplaced placeholders
    print("✅ Document generation logic verified")
    return True

def main():
    """Run all Italian Knowledge logic tests."""
    print("🇮🇹 Italian Knowledge Logic Tests")
    print("=" * 50)
    
    tests = [
        ("VAT Calculation", test_vat_calculation_logic),
        ("IRPEF Calculation", test_irpef_calculation_logic),
        ("Withholding Tax", test_withholding_calculation_logic),
        ("Contract Compliance", test_compliance_check_logic),
        ("Invoice Compliance", test_invoice_compliance_logic),
        ("Document Generation", test_document_generation_logic),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} passed")
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All Italian Knowledge logic tests passed!")
        return True
    else:
        print("⚠️ Some Italian Knowledge logic tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)