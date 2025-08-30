"""
TDD Tests for Document Parser.

This module tests document parsing capabilities including Excel/CSV financial statements,
PDF invoices, and structured document validation for financial data extraction.
"""

import pytest
import tempfile
import os
from decimal import Decimal
from datetime import date
from typing import Dict, List, Optional, Any
from pathlib import Path

# These imports will fail initially - that's the TDD approach
from app.services.validators.document_parser import (
    DocumentParser,
    ParsedDocument,
    FinancialStatement,
    InvoiceData,
    DocumentType,
    ParseResult,
    ValidationError,
    ExcelParser,
    PDFParser,
    CSVParser,
    FinancialDataExtractor,
    DocumentValidationResult,
    ParsingError,
    SupportedFormat,
    DocumentMetadata,
    ExtractionConfidence
)


class TestDocumentParser:
    """Test suite for Document Parser using TDD methodology."""
    
    @pytest.fixture
    def parser(self):
        """Create document parser instance for tests."""
        return DocumentParser()
    
    @pytest.fixture
    def sample_excel_data(self):
        """Sample Excel financial statement data for testing."""
        return {
            'balance_sheet': {
                'headers': ['Account', '2023', '2022', '2021'],
                'data': [
                    ['Current Assets', '500000', '450000', '400000'],
                    ['Cash', '100000', '90000', '80000'],
                    ['Inventory', '150000', '140000', '130000'],
                    ['Current Liabilities', '300000', '280000', '260000'],
                    ['Total Assets', '2000000', '1800000', '1600000'],
                    ['Shareholders Equity', '1200000', '1100000', '1000000']
                ]
            },
            'income_statement': {
                'headers': ['Item', '2023', '2022', '2021'],
                'data': [
                    ['Revenue', '3000000', '2700000', '2400000'],
                    ['Cost of Goods Sold', '1800000', '1620000', '1440000'],
                    ['Gross Profit', '1200000', '1080000', '960000'],
                    ['Operating Expenses', '800000', '720000', '640000'],
                    ['Net Income', '280800', '252720', '224640']
                ]
            }
        }
    
    @pytest.fixture
    def sample_invoice_data(self):
        """Sample invoice data for testing."""
        return {
            'invoice_number': 'INV-2024-001',
            'date': date(2024, 3, 15),
            'due_date': date(2024, 4, 14),
            'supplier': {
                'name': 'Fornitore Test SRL',
                'vat_number': 'IT12345678901',
                'address': 'Via Roma 123, Milano, Italy'
            },
            'customer': {
                'name': 'Cliente Test SpA',
                'vat_number': 'IT98765432109',
                'address': 'Corso Buenos Aires 456, Milano, Italy'
            },
            'line_items': [
                {
                    'description': 'Servizi di consulenza',
                    'quantity': Decimal('10'),
                    'unit_price': Decimal('150.00'),
                    'net_amount': Decimal('1500.00'),
                    'vat_rate': Decimal('22'),
                    'vat_amount': Decimal('330.00'),
                    'gross_amount': Decimal('1830.00')
                },
                {
                    'description': 'Licenza software annuale',
                    'quantity': Decimal('1'),
                    'unit_price': Decimal('2000.00'),
                    'net_amount': Decimal('2000.00'),
                    'vat_rate': Decimal('22'),
                    'vat_amount': Decimal('440.00'),
                    'gross_amount': Decimal('2440.00')
                }
            ],
            'totals': {
                'net_total': Decimal('3500.00'),
                'vat_total': Decimal('770.00'),
                'gross_total': Decimal('4270.00')
            }
        }
    
    # =========================================================================
    # Excel Document Parsing Tests
    # =========================================================================
    
    def test_excel_balance_sheet_parsing(self, parser, sample_excel_data):
        """Test parsing of Excel balance sheet with financial data extraction."""
        # Arrange - Create temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            # Simulate Excel file creation with sample data
            excel_path = temp_file.name
            
            # In real implementation, this would create actual Excel file
            # For TDD, we'll simulate the parsing result
            
        try:
            # Act
            result = parser.parse_excel_balance_sheet(excel_path)
            
            # Assert
            assert isinstance(result, FinancialStatement)
            assert result.document_type == DocumentType.BALANCE_SHEET
            assert result.periods == ['2023', '2022', '2021']  # Three years of data
            
            # Check asset values
            assert result.current_assets['2023'] == Decimal('500000')
            assert result.cash['2023'] == Decimal('100000')
            assert result.inventory['2023'] == Decimal('150000')
            
            # Check liability and equity values
            assert result.current_liabilities['2023'] == Decimal('300000')
            assert result.total_assets['2023'] == Decimal('2000000')
            assert result.shareholders_equity['2023'] == Decimal('1200000')
            
            # Verify balance sheet equation: Assets = Liabilities + Equity
            total_liab_equity = (result.current_liabilities['2023'] + 
                               result.shareholders_equity['2023'] + 
                               result.long_term_debt.get('2023', Decimal('0')))
            
            # Should balance (with reasonable tolerance for rounding)
            assert abs(result.total_assets['2023'] - total_liab_equity) < Decimal('1000')
            
            # Check metadata
            assert result.extraction_confidence > Decimal('0.8')  # High confidence
            assert result.validation_errors == []  # No validation errors
            
        finally:
            # Cleanup
            if os.path.exists(excel_path):
                os.unlink(excel_path)
    
    def test_excel_income_statement_parsing(self, parser, sample_excel_data):
        """Test parsing of Excel income statement with P&L data extraction."""
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            excel_path = temp_file.name
            
        try:
            # Act
            result = parser.parse_excel_income_statement(excel_path)
            
            # Assert
            assert isinstance(result, FinancialStatement)
            assert result.document_type == DocumentType.INCOME_STATEMENT
            
            # Check revenue and cost data
            assert result.revenue['2023'] == Decimal('3000000')
            assert result.cost_of_goods_sold['2023'] == Decimal('1800000')
            assert result.gross_profit['2023'] == Decimal('1200000')
            assert result.operating_expenses['2023'] == Decimal('800000')
            assert result.net_income['2023'] == Decimal('280800')
            
            # Verify P&L calculations
            calculated_gross = result.revenue['2023'] - result.cost_of_goods_sold['2023']
            assert calculated_gross == result.gross_profit['2023']
            
            # Check year-over-year growth
            revenue_growth_2023 = ((result.revenue['2023'] - result.revenue['2022']) / 
                                  result.revenue['2022']) * 100
            assert abs(revenue_growth_2023 - Decimal('11.11')) < Decimal('0.1')  # ~11.11% growth
            
        finally:
            os.unlink(excel_path)
    
    def test_excel_multi_sheet_parsing(self, parser):
        """Test parsing Excel file with multiple sheets (Balance Sheet + Income Statement)."""
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            excel_path = temp_file.name
            
        try:
            # Act
            result = parser.parse_excel_multi_sheet(excel_path)
            
            # Assert
            assert isinstance(result, ParsedDocument)
            assert len(result.financial_statements) == 2  # BS + IS
            
            balance_sheet = next((fs for fs in result.financial_statements 
                                if fs.document_type == DocumentType.BALANCE_SHEET), None)
            income_statement = next((fs for fs in result.financial_statements 
                                   if fs.document_type == DocumentType.INCOME_STATEMENT), None)
            
            assert balance_sheet is not None
            assert income_statement is not None
            
            # Should have consistent periods across both statements
            assert balance_sheet.periods == income_statement.periods
            
            # Combined document metadata
            assert result.total_sheets == 2
            assert result.processing_time_ms > 0
            assert result.overall_confidence > Decimal('0.7')
            
        finally:
            os.unlink(excel_path)
    
    def test_excel_parsing_with_formulas_and_formatting(self, parser):
        """Test Excel parsing with complex formulas and formatting."""
        # Arrange
        complex_excel_data = {
            'cells_with_formulas': {
                'D5': '=SUM(D2:D4)',  # Total current assets
                'D15': '=D5-D10',     # Working capital
                'E20': '=D20/C20-1'   # Growth rate
            },
            'formatted_cells': {
                'currency_cells': ['B2:E20'],
                'percentage_cells': ['F2:F20'],
                'date_cells': ['A1']
            }
        }
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            excel_path = temp_file.name
            
        try:
            # Act
            result = parser.parse_excel_with_formulas(excel_path, evaluate_formulas=True)
            
            # Assert
            assert result.formulas_evaluated is True
            assert len(result.detected_formulas) >= 3
            assert result.formula_evaluation_errors == []
            
            # Should preserve formatting information
            assert result.formatting_preserved is True
            assert 'currency' in result.cell_formats
            assert 'percentage' in result.cell_formats
            
            # Calculated values should be available
            assert result.calculated_values['working_capital'] is not None
            assert result.calculated_values['growth_rates'] is not None
            
        finally:
            os.unlink(excel_path)
    
    # =========================================================================
    # PDF Invoice Parsing Tests
    # =========================================================================
    
    def test_pdf_invoice_parsing_italian_format(self, parser, sample_invoice_data):
        """Test parsing of Italian PDF invoice with VAT calculations."""
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            pdf_path = temp_file.name
            
        try:
            # Act
            result = parser.parse_pdf_invoice(pdf_path)
            
            # Assert
            assert isinstance(result, InvoiceData)
            assert result.document_type == DocumentType.INVOICE
            
            # Check invoice header information
            assert result.invoice_number == 'INV-2024-001'
            assert result.issue_date == date(2024, 3, 15)
            assert result.due_date == date(2024, 4, 14)
            
            # Check supplier information
            assert result.supplier.vat_number == 'IT12345678901'
            assert 'SRL' in result.supplier.name
            assert result.supplier.country == 'IT'  # Detected from VAT format
            
            # Check customer information
            assert result.customer.vat_number == 'IT98765432109'
            assert 'SpA' in result.customer.name
            
            # Check line items
            assert len(result.line_items) == 2
            
            first_item = result.line_items[0]
            assert first_item.description == 'Servizi di consulenza'
            assert first_item.quantity == Decimal('10')
            assert first_item.unit_price == Decimal('150.00')
            assert first_item.net_amount == Decimal('1500.00')
            assert first_item.vat_rate == Decimal('22')  # Standard Italian VAT
            assert first_item.vat_amount == Decimal('330.00')
            
            # Check totals
            assert result.totals.net_total == Decimal('3500.00')
            assert result.totals.vat_total == Decimal('770.00')
            assert result.totals.gross_total == Decimal('4270.00')
            
            # Verify VAT calculations
            calculated_vat = sum(item.vat_amount for item in result.line_items)
            assert calculated_vat == result.totals.vat_total
            
            # Check extraction confidence
            assert result.extraction_confidence > Decimal('0.75')  # Good confidence for structured invoice
            
        finally:
            os.unlink(pdf_path)
    
    def test_pdf_invoice_parsing_with_discounts(self, parser):
        """Test PDF invoice parsing with discounts and complex pricing."""
        # Arrange - Invoice with discounts
        discount_invoice_data = {
            'line_items': [
                {
                    'description': 'Software license',
                    'quantity': Decimal('5'),
                    'unit_price': Decimal('1000.00'),
                    'gross_line_total': Decimal('5000.00'),
                    'discount_percentage': Decimal('10'),  # 10% discount
                    'discount_amount': Decimal('500.00'),
                    'net_amount': Decimal('4500.00'),
                    'vat_rate': Decimal('22'),
                    'vat_amount': Decimal('990.00')
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            pdf_path = temp_file.name
            
        try:
            # Act
            result = parser.parse_pdf_invoice_with_discounts(pdf_path)
            
            # Assert
            first_item = result.line_items[0]
            assert first_item.has_discount is True
            assert first_item.discount_percentage == Decimal('10')
            assert first_item.discount_amount == Decimal('500.00')
            
            # Net amount should be gross minus discount
            expected_net = first_item.gross_line_total - first_item.discount_amount
            assert first_item.net_amount == expected_net
            
            # VAT should be calculated on net amount (after discount)
            expected_vat = first_item.net_amount * (first_item.vat_rate / Decimal('100'))
            assert abs(first_item.vat_amount - expected_vat) < Decimal('0.01')
            
        finally:
            os.unlink(pdf_path)
    
    def test_pdf_invoice_parsing_multiple_vat_rates(self, parser):
        """Test PDF invoice with multiple VAT rates (4%, 10%, 22%)."""
        # Arrange - Invoice with different VAT rates
        multi_vat_data = {
            'line_items': [
                {'description': 'Books', 'vat_rate': Decimal('4')},     # Super-reduced
                {'description': 'Food', 'vat_rate': Decimal('10')},    # Reduced
                {'description': 'Services', 'vat_rate': Decimal('22')} # Standard
            ]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            pdf_path = temp_file.name
            
        try:
            # Act
            result = parser.parse_pdf_invoice_multi_vat(pdf_path)
            
            # Assert
            vat_rates_found = {item.vat_rate for item in result.line_items}
            assert Decimal('4') in vat_rates_found
            assert Decimal('10') in vat_rates_found
            assert Decimal('22') in vat_rates_found
            
            # Should have VAT summary by rate
            assert len(result.vat_breakdown) == 3
            assert result.vat_breakdown[Decimal('4')] > Decimal('0')
            assert result.vat_breakdown[Decimal('10')] > Decimal('0')
            assert result.vat_breakdown[Decimal('22')] > Decimal('0')
            
            # Total VAT should equal sum of all VAT rates
            calculated_total_vat = sum(result.vat_breakdown.values())
            assert abs(calculated_total_vat - result.totals.vat_total) < Decimal('0.01')
            
        finally:
            os.unlink(pdf_path)
    
    # =========================================================================
    # CSV Financial Data Parsing Tests
    # =========================================================================
    
    def test_csv_bank_statement_parsing(self, parser):
        """Test parsing of CSV bank statement with transaction data."""
        # Arrange
        csv_data = """Date,Description,Debit,Credit,Balance
2024-01-01,Opening Balance,,-,100000.00
2024-01-02,Invoice Payment INV-001,-5000.00,,95000.00
2024-01-03,Customer Payment,,-8000.00,103000.00
2024-01-05,Office Rent,-2500.00,,100500.00
2024-01-10,Supplier Payment,-15000.00,,85500.00"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write(csv_data)
            csv_path = temp_file.name
            
        try:
            # Act
            result = parser.parse_csv_bank_statement(csv_path)
            
            # Assert
            assert isinstance(result, ParsedDocument)
            assert result.document_type == DocumentType.BANK_STATEMENT
            assert len(result.transactions) == 5  # Including opening balance
            
            # Check first transaction (opening balance)
            opening = result.transactions[0]
            assert opening.date == date(2024, 1, 1)
            assert opening.description == 'Opening Balance'
            assert opening.balance == Decimal('100000.00')
            
            # Check debit transaction
            debit_transaction = result.transactions[1]
            assert debit_transaction.debit_amount == Decimal('5000.00')
            assert debit_transaction.balance == Decimal('95000.00')
            
            # Check credit transaction
            credit_transaction = result.transactions[2]
            assert credit_transaction.credit_amount == Decimal('8000.00')
            assert credit_transaction.balance == Decimal('103000.00')
            
            # Calculate summary statistics
            assert result.summary.total_debits == Decimal('22500.00')  # Sum of all debits
            assert result.summary.total_credits == Decimal('8000.00')   # Sum of all credits
            assert result.summary.net_change == Decimal('-14500.00')   # Credits - Debits
            assert result.summary.final_balance == Decimal('85500.00')
            
        finally:
            os.unlink(csv_path)
    
    def test_csv_trial_balance_parsing(self, parser):
        """Test parsing of CSV trial balance with account codes."""
        # Arrange
        trial_balance_csv = """Account Code,Account Name,Debit,Credit
1000,Cash,50000.00,
1200,Accounts Receivable,75000.00,
1500,Inventory,100000.00,
2000,Accounts Payable,,45000.00
2100,Accrued Expenses,,15000.00
3000,Share Capital,,150000.00
4000,Sales Revenue,,200000.00
5000,Cost of Goods Sold,120000.00,
6000,Operating Expenses,65000.00,"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write(trial_balance_csv)
            csv_path = temp_file.name
            
        try:
            # Act
            result = parser.parse_csv_trial_balance(csv_path)
            
            # Assert
            assert result.document_type == DocumentType.TRIAL_BALANCE
            assert len(result.accounts) == 9
            
            # Check asset accounts (1000-1999)
            cash_account = next(a for a in result.accounts if a.code == '1000')
            assert cash_account.name == 'Cash'
            assert cash_account.debit_balance == Decimal('50000.00')
            assert cash_account.credit_balance == Decimal('0')
            assert cash_account.account_type == 'Asset'
            
            # Check liability accounts (2000-2999)
            payables = next(a for a in result.accounts if a.code == '2000')
            assert payables.credit_balance == Decimal('45000.00')
            assert payables.account_type == 'Liability'
            
            # Check equity accounts (3000-3999)
            share_capital = next(a for a in result.accounts if a.code == '3000')
            assert share_capital.credit_balance == Decimal('150000.00')
            assert share_capital.account_type == 'Equity'
            
            # Verify trial balance equation: Total Debits = Total Credits
            total_debits = sum(a.debit_balance for a in result.accounts)
            total_credits = sum(a.credit_balance for a in result.accounts)
            assert total_debits == total_credits  # Should balance
            assert result.is_balanced is True
            
        finally:
            os.unlink(csv_path)
    
    # =========================================================================
    # Document Validation Tests
    # =========================================================================
    
    def test_document_validation_completeness_check(self, parser, sample_excel_data):
        """Test document validation for completeness and accuracy."""
        # Arrange - Create document with some missing data
        incomplete_data = sample_excel_data.copy()
        incomplete_data['balance_sheet']['data'][1] = ['Cash', '', '90000', '80000']  # Missing 2023 cash
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            excel_path = temp_file.name
            
        try:
            # Act
            validation_result = parser.validate_document_completeness(excel_path)
            
            # Assert
            assert isinstance(validation_result, DocumentValidationResult)
            assert validation_result.is_complete is False  # Missing data detected
            assert len(validation_result.missing_fields) >= 1
            assert 'Cash 2023' in str(validation_result.missing_fields[0])
            
            # Should provide data quality score
            assert Decimal('0') <= validation_result.data_quality_score <= Decimal('100')
            assert validation_result.data_quality_score < Decimal('100')  # Not perfect due to missing data
            
            # Should suggest improvements
            assert len(validation_result.improvement_suggestions) >= 1
            
        finally:
            os.unlink(excel_path)
    
    def test_document_validation_financial_consistency(self, parser, sample_excel_data):
        """Test validation of financial statement consistency and accuracy."""
        # Arrange - Create data with intentional inconsistencies
        inconsistent_data = sample_excel_data.copy()
        # Make balance sheet not balance: Assets ≠ Liabilities + Equity
        inconsistent_data['balance_sheet']['data'][4] = ['Total Assets', '1900000', '1800000', '1600000']  # Wrong total
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            excel_path = temp_file.name
            
        try:
            # Act
            consistency_check = parser.validate_financial_consistency(excel_path)
            
            # Assert
            assert consistency_check.is_consistent is False
            assert len(consistency_check.inconsistencies) >= 1
            
            # Should detect balance sheet imbalance
            balance_error = next((err for err in consistency_check.inconsistencies 
                                if 'balance' in err.error_type.lower()), None)
            assert balance_error is not None
            assert balance_error.severity == 'High'
            
            # Should detect mathematical errors
            assert 'mathematical_error' in [err.error_category for err in consistency_check.inconsistencies]
            
        finally:
            os.unlink(excel_path)
    
    def test_document_validation_data_quality_assessment(self, parser):
        """Test comprehensive data quality assessment."""
        # Arrange - Document with various quality issues
        poor_quality_data = {
            'missing_values': 15,      # 15% missing values
            'duplicate_rows': 3,       # Some duplicate entries
            'inconsistent_formats': 8,  # Mixed date formats, number formats
            'outlier_values': 2,       # Suspicious outlier values
            'formula_errors': 1        # Excel #REF! error
        }
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            excel_path = temp_file.name
            
        try:
            # Act
            quality_assessment = parser.assess_data_quality(excel_path)
            
            # Assert
            assert isinstance(quality_assessment, DocumentValidationResult)
            assert quality_assessment.overall_quality_score < Decimal('75')  # Poor quality due to issues
            
            # Should identify different types of quality issues
            quality_issues = quality_assessment.quality_issues
            assert 'missing_values' in quality_issues
            assert 'duplicate_data' in quality_issues
            assert 'format_inconsistencies' in quality_issues
            assert 'outlier_detection' in quality_issues
            
            # Should provide remediation suggestions
            assert len(quality_assessment.remediation_steps) >= 4
            
            # Quality score should reflect severity of issues
            expected_deductions = (poor_quality_data['missing_values'] + 
                                 poor_quality_data['duplicate_rows'] + 
                                 poor_quality_data['inconsistent_formats'])
            assert quality_assessment.overall_quality_score < Decimal('100') - expected_deductions
            
        finally:
            os.unlink(excel_path)
    
    # =========================================================================
    # Advanced Document Processing Tests
    # =========================================================================
    
    def test_multi_format_document_batch_processing(self, parser):
        """Test batch processing of multiple document formats."""
        # Arrange - Multiple documents of different types
        document_paths = []
        
        # Create temporary files for different formats
        formats = ['.xlsx', '.pdf', '.csv']
        for fmt in formats:
            temp_file = tempfile.NamedTemporaryFile(suffix=fmt, delete=False)
            document_paths.append(temp_file.name)
            temp_file.close()
        
        try:
            # Act
            batch_result = parser.process_document_batch(document_paths)
            
            # Assert
            assert len(batch_result.processed_documents) == 3
            assert len(batch_result.successful_parses) >= 0  # Some may succeed
            assert len(batch_result.failed_parses) >= 0      # Some may fail
            
            # Should provide summary statistics
            assert batch_result.total_documents == 3
            assert batch_result.success_rate >= Decimal('0')
            assert batch_result.processing_time_ms > 0
            
            # Should categorize by document type
            document_types = [doc.document_type for doc in batch_result.processed_documents]
            assert len(set(document_types)) >= 1  # At least one type identified
            
        finally:
            # Cleanup all temporary files
            for path in document_paths:
                if os.path.exists(path):
                    os.unlink(path)
    
    def test_document_text_extraction_with_ocr(self, parser):
        """Test text extraction from scanned documents using OCR."""
        # Arrange - Simulated scanned PDF invoice
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            scanned_pdf_path = temp_file.name
            
        try:
            # Act
            ocr_result = parser.extract_text_with_ocr(
                scanned_pdf_path, 
                language='ita',  # Italian language
                confidence_threshold=0.8
            )
            
            # Assert
            assert isinstance(ocr_result, ParseResult)
            assert ocr_result.text_extracted is not None
            assert len(ocr_result.text_extracted) > 0
            
            # Should detect language
            assert ocr_result.detected_language == 'ita' or ocr_result.detected_language == 'it'
            
            # Should provide confidence metrics
            assert ocr_result.average_confidence >= Decimal('0.8')
            assert len(ocr_result.low_confidence_regions) >= 0  # May have some low confidence areas
            
            # Should identify structured elements
            if ocr_result.structured_data_detected:
                assert ocr_result.tables_found >= 0
                assert ocr_result.invoice_elements_found >= 0
                
        finally:
            os.unlink(scanned_pdf_path)
    
    def test_financial_data_extraction_confidence_scoring(self, parser, sample_excel_data):
        """Test confidence scoring for extracted financial data."""
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            excel_path = temp_file.name
            
        try:
            # Act
            extraction_result = parser.extract_financial_data_with_confidence(excel_path)
            
            # Assert
            assert isinstance(extraction_result.confidence, ExtractionConfidence)
            
            # Overall confidence should be reasonable
            assert Decimal('0') <= extraction_result.confidence.overall_confidence <= Decimal('1')
            
            # Should have confidence scores for different data types
            assert extraction_result.confidence.numerical_data_confidence >= Decimal('0.8')
            assert extraction_result.confidence.date_recognition_confidence >= Decimal('0.7')
            assert extraction_result.confidence.currency_detection_confidence >= Decimal('0.9')
            
            # Should identify high and low confidence fields
            assert len(extraction_result.confidence.high_confidence_fields) >= 5
            assert len(extraction_result.confidence.uncertain_fields) >= 0
            
            # Should provide extraction methodology explanation
            assert extraction_result.confidence.extraction_method in ['structured', 'pattern_matching', 'ml_inference']
            
        finally:
            os.unlink(excel_path)
    
    # =========================================================================
    # Error Handling and Edge Cases
    # =========================================================================
    
    def test_document_parsing_unsupported_format(self, parser):
        """Test error handling for unsupported document formats."""
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as temp_file:
            unsupported_path = temp_file.name
            
        try:
            # Act & Assert
            with pytest.raises(ParsingError, match="Unsupported document format"):
                parser.parse_document(unsupported_path)
                
        finally:
            os.unlink(unsupported_path)
    
    def test_document_parsing_corrupted_file(self, parser):
        """Test error handling for corrupted or invalid files."""
        # Arrange - Create corrupted Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            # Write invalid data to simulate corruption
            temp_file.write(b'This is not a valid Excel file')
            corrupted_path = temp_file.name
            
        try:
            # Act
            result = parser.parse_document_with_error_handling(corrupted_path)
            
            # Assert
            assert result.parsing_successful is False
            assert len(result.errors) >= 1
            assert 'corrupted' in result.errors[0].error_message.lower() or 'invalid' in result.errors[0].error_message.lower()
            assert result.error_recovery_attempted is True
            
        finally:
            os.unlink(corrupted_path)
    
    def test_document_parsing_performance_large_files(self, parser):
        """Test parsing performance with large documents."""
        import time
        
        # Arrange - Simulate large Excel file
        large_dataset_rows = 10000  # 10K rows of financial data
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            large_excel_path = temp_file.name
            
        try:
            # Act
            start_time = time.time()
            result = parser.parse_large_excel_file(
                large_excel_path, 
                chunk_size=1000,  # Process in chunks
                memory_efficient=True
            )
            end_time = time.time()
            
            # Assert
            processing_time = end_time - start_time
            assert processing_time < 30.0  # Should complete within 30 seconds
            assert result.rows_processed == large_dataset_rows
            assert result.memory_usage_mb < 500  # Reasonable memory usage
            assert result.chunked_processing is True
            
        finally:
            os.unlink(large_excel_path)
    
    def test_document_security_validation(self, parser):
        """Test document security validation and malware detection."""
        # Arrange - Document with potential security issues
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            potentially_malicious_path = temp_file.name
            
        try:
            # Act
            security_check = parser.validate_document_security(potentially_malicious_path)
            
            # Assert
            assert isinstance(security_check, DocumentValidationResult)
            assert security_check.security_scan_performed is True
            assert security_check.malware_detected is not None  # Boolean result
            assert security_check.macro_detected is not None    # Boolean result
            
            # Should check for various security risks
            security_risks = security_check.security_risks
            assert 'macro_analysis' in security_risks
            assert 'external_references' in security_risks
            assert 'suspicious_patterns' in security_risks
            
            # Should provide security recommendation
            if security_check.security_score < Decimal('80'):
                assert len(security_check.security_recommendations) >= 1
                
        finally:
            os.unlink(potentially_malicious_path)