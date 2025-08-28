"""
TDD Tests: Tax Calculation Formatting for Beautiful Display

Tax calculations must be formatted as beautiful, professional-looking HTML
with proper currency formatting, mathematical symbols, and visual emphasis.
"""

import pytest
from app.core.content_formatter import ContentFormatter
from decimal import Decimal


class TestTaxCalculationFormatting:
    """Test professional tax calculation formatting."""
    
    def setup_method(self):
        self.formatter = ContentFormatter()
    
    # ========== BASIC CALCULATION FORMATTING ==========
    
    def test_simple_tax_calculation_formatting(self):
        """Test basic tax calculation with percentage."""
        raw_calculation = "50000 × 15% = 7500"
        
        expected_html = """<div class="calculation">
    <span class="formula">50.000 × 15%</span> = <strong class="result">€ 7.500</strong>
</div>"""
        
        result = self.formatter.format_tax_calculation(raw_calculation)
        assert result == expected_html
    
    def test_vat_calculation_formatting(self):
        """Test VAT calculation formatting."""
        raw_calculation = "Imponibile: 10000 + IVA 22% = 2200 → Totale: 12200"
        
        expected_html = """<div class="calculation vat-calculation">
    <div class="calculation-line">
        <span class="label">Imponibile:</span> <span class="amount">€ 10.000</span>
    </div>
    <div class="calculation-line">
        <span class="label">IVA 22%:</span> <span class="amount">€ 2.200</span>
    </div>
    <div class="calculation-total">
        <span class="label">Totale:</span> <strong class="result">€ 12.200</strong>
    </div>
</div>"""
        
        result = self.formatter.format_tax_calculation(raw_calculation)
        assert result == expected_html
    
    def test_tax_brackets_formatting(self):
        """Test progressive tax brackets formatting."""
        raw_calculation = """Reddito: 75000
Scaglione 1: 28000 × 23% = 6440
Scaglione 2: 27000 × 25% = 6750  
Scaglione 3: 20000 × 35% = 7000
Totale imposta: 20190"""
        
        expected_html = """<div class="calculation tax-brackets">
    <div class="calculation-header">
        <span class="label">Reddito:</span> <span class="amount">€ 75.000</span>
    </div>
    <div class="tax-bracket">
        <span class="bracket-label">Scaglione 1:</span> 
        <span class="formula">€ 28.000 × 23%</span> = 
        <span class="bracket-result">€ 6.440</span>
    </div>
    <div class="tax-bracket">
        <span class="bracket-label">Scaglione 2:</span> 
        <span class="formula">€ 27.000 × 25%</span> = 
        <span class="bracket-result">€ 6.750</span>
    </div>
    <div class="tax-bracket">
        <span class="bracket-label">Scaglione 3:</span> 
        <span class="formula">€ 20.000 × 35%</span> = 
        <span class="bracket-result">€ 7.000</span>
    </div>
    <div class="calculation-total">
        <span class="label">Totale imposta:</span> <strong class="result">€ 20.190</strong>
    </div>
</div>"""
        
        result = self.formatter.format_tax_calculation(raw_calculation)
        assert result == expected_html
    
    # ========== CURRENCY FORMATTING TESTS ==========
    
    def test_euro_formatting(self):
        """Test proper Euro currency formatting."""
        amounts = [
            ("1000", "€ 1.000"),
            ("1000.50", "€ 1.000,50"),
            ("1234567", "€ 1.234.567"),
            ("1234567.89", "€ 1.234.567,89"),
            ("0.50", "€ 0,50"),
        ]
        
        for raw_amount, expected in amounts:
            result = self.formatter.format_currency(raw_amount)
            assert result == expected
    
    def test_percentage_formatting(self):
        """Test percentage formatting in calculations."""
        percentages = [
            ("15%", "15%"),
            ("22%", "22%"),
            ("0.15", "15%"),
            ("0.22", "22%"),
            ("15", "15%"),
        ]
        
        for raw_percentage, expected in percentages:
            result = self.formatter.format_percentage(raw_percentage)
            assert result == expected
    
    # ========== COMPLEX CALCULATION SCENARIOS ==========
    
    def test_deduction_calculation_formatting(self):
        """Test deduction calculation with breakdown."""
        raw_calculation = """Reddito lordo: 60000
Deduzioni personali: 3000
Deduzioni lavoro dipendente: 1880
Reddito imponibile: 55120
Imposta lorda: 11524
Detrazioni: 1840
Imposta netta: 9684"""
        
        expected_html = """<div class="calculation deduction-calculation">
    <div class="calculation-step">
        <span class="label">Reddito lordo:</span> <span class="amount">€ 60.000</span>
    </div>
    <div class="deduction-group">
        <div class="deduction-item">
            <span class="deduction-label">Deduzioni personali:</span> 
            <span class="deduction-amount">- € 3.000</span>
        </div>
        <div class="deduction-item">
            <span class="deduction-label">Deduzioni lavoro dipendente:</span> 
            <span class="deduction-amount">- € 1.880</span>
        </div>
    </div>
    <div class="calculation-step">
        <span class="label">Reddito imponibile:</span> <span class="amount">€ 55.120</span>
    </div>
    <div class="calculation-step">
        <span class="label">Imposta lorda:</span> <span class="amount">€ 11.524</span>
    </div>
    <div class="deduction-item">
        <span class="deduction-label">Detrazioni:</span> 
        <span class="deduction-amount">- € 1.840</span>
    </div>
    <div class="calculation-total">
        <span class="label">Imposta netta:</span> <strong class="result">€ 9.684</strong>
    </div>
</div>"""
        
        result = self.formatter.format_tax_calculation(raw_calculation)
        assert result == expected_html
    
    def test_regime_forfettario_calculation(self):
        """Test regime forfettario specific calculation."""
        raw_calculation = """Fatturato annuo: 65000
Coefficiente di redditività: 78%
Reddito imponibile: 50700
Imposta sostitutiva 15%: 7605"""
        
        expected_html = """<div class="calculation forfettario-calculation">
    <div class="calculation-step">
        <span class="label">Fatturato annuo:</span> <span class="amount">€ 65.000</span>
    </div>
    <div class="calculation-step">
        <span class="label">Coefficiente di redditività:</span> <span class="percentage">78%</span>
    </div>
    <div class="calculation-step">
        <span class="label">Reddito imponibile:</span> 
        <span class="formula">€ 65.000 × 78%</span> = 
        <span class="amount">€ 50.700</span>
    </div>
    <div class="calculation-total">
        <span class="label">Imposta sostitutiva 15%:</span> 
        <span class="formula">€ 50.700 × 15%</span> = 
        <strong class="result">€ 7.605</strong>
    </div>
</div>"""
        
        result = self.formatter.format_tax_calculation(raw_calculation)
        assert result == expected_html
    
    # ========== COMPARISON CALCULATIONS ==========
    
    def test_regime_comparison_formatting(self):
        """Test comparison between tax regimes."""
        raw_calculation = """REGIME ORDINARIO:
Imposta IRPEF: 15000
IRAP: 1200
IVA da versare: 8000
Totale: 24200

REGIME FORFETTARIO:
Imposta sostitutiva: 7605
Nessuna IRAP
Nessuna IVA
Totale: 7605

Risparmio: 16595"""
        
        expected_html = """<div class="calculation comparison-calculation">
    <div class="regime-comparison">
        <div class="regime-section ordinary">
            <h4 class="regime-title">REGIME ORDINARIO</h4>
            <div class="calculation-item">
                <span class="label">Imposta IRPEF:</span> <span class="amount">€ 15.000</span>
            </div>
            <div class="calculation-item">
                <span class="label">IRAP:</span> <span class="amount">€ 1.200</span>
            </div>
            <div class="calculation-item">
                <span class="label">IVA da versare:</span> <span class="amount">€ 8.000</span>
            </div>
            <div class="regime-total">
                <span class="label">Totale:</span> <span class="result">€ 24.200</span>
            </div>
        </div>
        
        <div class="regime-section forfettario">
            <h4 class="regime-title">REGIME FORFETTARIO</h4>
            <div class="calculation-item">
                <span class="label">Imposta sostitutiva:</span> <span class="amount">€ 7.605</span>
            </div>
            <div class="calculation-item exemption">
                <span class="label">IRAP:</span> <span class="exemption-text">Nessuna</span>
            </div>
            <div class="calculation-item exemption">
                <span class="label">IVA:</span> <span class="exemption-text">Nessuna</span>
            </div>
            <div class="regime-total">
                <span class="label">Totale:</span> <span class="result">€ 7.605</span>
            </div>
        </div>
    </div>
    
    <div class="savings-highlight">
        <span class="savings-label">Risparmio:</span> 
        <strong class="savings-amount">€ 16.595</strong>
    </div>
</div>"""
        
        result = self.formatter.format_tax_calculation(raw_calculation)
        assert result == expected_html
    
    # ========== MATHEMATICAL SYMBOLS AND FORMATTING ==========
    
    def test_mathematical_symbols_formatting(self):
        """Test proper mathematical symbols in calculations."""
        raw_calculation = "100000 / 12 * 15% = 1250"
        
        expected_html = """<div class="calculation">
    <span class="formula">€ 100.000 ÷ 12 × 15%</span> = <strong class="result">€ 1.250</strong>
</div>"""
        
        result = self.formatter.format_tax_calculation(raw_calculation)
        assert result == expected_html
        
        # Should use proper mathematical symbols
        assert "÷" in result  # Division
        assert "×" in result  # Multiplication
    
    def test_formula_highlighting(self):
        """Test formula components are properly highlighted."""
        raw_calculation = "Reddito 50000 * Aliquota 15% = Imposta 7500"
        
        result = self.formatter.format_tax_calculation(raw_calculation)
        
        # Should contain proper CSS classes for styling
        assert 'class="formula"' in result
        assert 'class="result"' in result
        assert 'class="amount"' in result
    
    # ========== ERROR HANDLING ==========
    
    def test_invalid_calculation_handling(self):
        """Test handling of malformed calculations."""
        invalid_calculations = [
            "",  # Empty
            "Invalid text without numbers",  # No numbers
            "123 + abc = xyz",  # Invalid numbers
        ]
        
        for invalid_calc in invalid_calculations:
            result = self.formatter.format_tax_calculation(invalid_calc)
            # Should return safe fallback
            assert isinstance(result, str)
            assert "<div" in result  # Still wrapped in proper HTML
    
    def test_zero_amounts_formatting(self):
        """Test formatting of zero amounts."""
        raw_calculation = "Detrazioni: 0, Imposta: 0"
        
        result = self.formatter.format_tax_calculation(raw_calculation)
        assert "€ 0" in result or "€ 0,00" in result


class TestCalculationStreaming:
    """Test tax calculation formatting in streaming context."""
    
    def setup_method(self):
        self.formatter = ContentFormatter()
    
    def test_incremental_calculation_building(self):
        """Test building calculations incrementally."""
        chunks = [
            "Reddito: ",
            "50000",
            " × 15%",
            " = 7500"
        ]
        
        # Should wait for complete calculation before formatting
        result_chunks = []
        for chunk in chunks:
            formatted = self.formatter.process_calculation_chunk(chunk)
            if formatted:
                result_chunks.append(formatted)
        
        # Should yield complete formatted calculation
        assert len(result_chunks) == 1
        final_result = result_chunks[0]
        assert '<div class="calculation">' in final_result
        assert "€ 50.000" in final_result
        assert "€ 7.500" in final_result
    
    def test_multi_line_calculation_streaming(self):
        """Test streaming multi-line calculations."""
        chunks = [
            "Scaglione 1: 28000 × 23% = 6440\n",
            "Scaglione 2: 27000 × 25% = 6750\n",
            "Totale: 13190"
        ]
        
        result_chunks = []
        for chunk in chunks:
            formatted = self.formatter.process_calculation_chunk(chunk)
            if formatted:
                result_chunks.append(formatted)
        
        final_result = "".join(result_chunks)
        assert "tax-brackets" in final_result
        assert "€ 28.000" in final_result
        assert "€ 6.440" in final_result