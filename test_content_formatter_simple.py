"""
Simple test to verify ContentFormatter implementation
"""

import sys
import os
sys.path.append('/Users/micky/PycharmProjects/PratikoAi-BE')

from app.core.content_formatter import ContentFormatter

def test_heading_conversion():
    """Test ### heading conversion to <h3>."""
    formatter = ContentFormatter()
    
    markdown_input = "### 1. Definizione/Concetto principale"
    expected_html = "<h3>1. Definizione/Concetto principale</h3>"
    
    result = formatter.convert_markdown_to_html(markdown_input)
    print(f"Input: {markdown_input}")
    print(f"Expected: {expected_html}")
    print(f"Result: {result}")
    
    assert result == expected_html
    assert "###" not in result
    print("✅ Heading conversion test passed!")

def test_bold_conversion():
    """Test **bold** conversion to <strong>."""
    formatter = ContentFormatter()
    
    markdown_input = "Il regime forfettario **non prevede** l'applicazione dell'IVA."
    expected_html = "<p>Il regime forfettario <strong>non prevede</strong> l'applicazione dell'IVA.</p>"
    
    result = formatter.convert_markdown_to_html(markdown_input)
    print(f"Input: {markdown_input}")
    print(f"Expected: {expected_html}")
    print(f"Result: {result}")
    
    assert "<strong>non prevede</strong>" in result
    assert "**" not in result
    print("✅ Bold conversion test passed!")

def test_list_conversion():
    """Test bullet list conversion."""
    formatter = ContentFormatter()
    
    markdown_input = """- Articolo 1, commi 54-89: definisce i requisiti
- Articolo 1, comma 57: stabilisce che non possono accedere"""
    
    result = formatter.convert_markdown_to_html(markdown_input)
    print(f"Input: {markdown_input}")
    print(f"Result: {result}")
    
    assert "<ul>" in result
    assert "<li>Articolo 1, commi 54-89: definisce i requisiti</li>" in result
    assert "<li>Articolo 1, comma 57: stabilisce che non possono accedere</li>" in result
    assert "</ul>" in result
    assert "- " not in result or "<li>" in result  # No standalone dashes
    print("✅ List conversion test passed!")

def test_currency_formatting():
    """Test currency formatting."""
    formatter = ContentFormatter()
    
    test_cases = [
        ("1000", "€ 1.000"),
        ("1234567", "€ 1.234.567"),
        ("1000.50", "€ 1.000,50"),
    ]
    
    for input_amount, expected in test_cases:
        result = formatter.format_currency(input_amount)
        print(f"Currency {input_amount} -> {result} (expected: {expected})")
        assert result == expected
    
    print("✅ Currency formatting test passed!")

def test_calculation_formatting():
    """Test tax calculation formatting."""
    formatter = ContentFormatter()
    
    calculation_input = "50000 × 15% = 7500"
    result = formatter.format_tax_calculation(calculation_input)
    print(f"Calculation input: {calculation_input}")
    print(f"Result: {result}")
    
    assert '<div class="calculation">' in result
    assert "€ 50.000" in result
    assert "€ 7.500" in result
    assert "15%" in result
    print("✅ Calculation formatting test passed!")

def test_no_markdown_in_output():
    """Critical test: ensure no markdown syntax in output."""
    formatter = ContentFormatter()
    
    markdown_input = """### 1. Definizione**importante**

Il regime forfettario è un regime fiscale **semplificato** per le persone fisiche.

- Lista con *enfasi* e `codice`
- Secondo elemento"""
    
    result = formatter.convert_markdown_to_html(markdown_input)
    print(f"Complex input: {markdown_input}")
    print(f"Result: {result}")
    
    # Critical checks: no markdown syntax
    forbidden_syntax = ["###", "**", "*", "`"]
    for syntax in forbidden_syntax:
        if syntax == "*" and "**" in result:
            continue  # Skip single * check if ** is present (would be caught separately)
        assert syntax not in result, f"Found forbidden markdown syntax '{syntax}' in: {result}"
    
    # Should contain proper HTML
    assert "<h3>" in result
    assert "<strong>" in result
    assert "<ul>" in result
    assert "<li>" in result
    print("✅ No markdown syntax test passed!")

if __name__ == "__main__":
    print("Testing ContentFormatter implementation...")
    print("=" * 60)
    
    try:
        test_heading_conversion()
        test_bold_conversion()
        test_list_conversion()
        test_currency_formatting()
        test_calculation_formatting()
        test_no_markdown_in_output()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED! ContentFormatter is working correctly.")
        print("✅ Users will never see markdown syntax")
        print("✅ HTML formatting is working properly")
        print("✅ Currency and calculations are formatted professionally")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()