"""
TDD Tests for Document Upload & Processing System.

Comprehensive test suite for Italian tax document processing including
PDF, Excel, CSV processing with drag & drop functionality.
"""

import pytest
import asyncio
import io
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, BinaryIO
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_simple import (
    Document, DocumentAnalysis, DocumentType, ProcessingStatus,
    ItalianDocumentCategory, DOCUMENT_CONFIG
)
from app.services.document_processing_service import DocumentProcessor, DocumentProcessingError
from app.services.document_uploader import DocumentUploader, UploadValidationError
from app.services.italian_document_analyzer import ItalianDocumentAnalyzer
from app.services.secure_document_storage import SecureDocumentStorage


class TestDocumentUploadValidation:
    """Test document upload validation and security"""
    
    @pytest.fixture
    def document_uploader(self):
        return DocumentUploader()
    
    @pytest.mark.asyncio
    async def test_validate_pdf_file_success(self, document_uploader):
        """Test successful PDF file validation"""
        
        # Create mock PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        upload_file = UploadFile(
            filename="fattura_123.pdf",
            file=io.BytesIO(pdf_content),
            content_type="application/pdf",
            size=len(pdf_content)
        )
        
        validation_result = await document_uploader.validate_file(upload_file)
        
        assert validation_result["is_valid"] == True
        assert validation_result["file_type"] == DocumentType.PDF
        assert validation_result["mime_type"] == "application/pdf"
        assert validation_result["file_size"] == len(pdf_content)
        assert validation_result["security_threats"] == []
    
    @pytest.mark.asyncio
    async def test_validate_excel_file_success(self, document_uploader):
        """Test successful Excel file validation"""
        
        # Create mock Excel content (minimal XLSX structure)
        excel_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"  # ZIP header for XLSX
        
        upload_file = UploadFile(
            filename="bilancio_2024.xlsx",
            file=io.BytesIO(excel_content),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            size=len(excel_content)
        )
        
        validation_result = await document_uploader.validate_file(upload_file)
        
        assert validation_result["is_valid"] == True
        assert validation_result["file_type"] == DocumentType.EXCEL_XLSX
        assert validation_result["file_size"] == len(excel_content)
    
    @pytest.mark.asyncio
    async def test_validate_csv_file_success(self, document_uploader):
        """Test successful CSV file validation"""
        
        csv_content = "Data,Descrizione,Importo\n01/01/2024,Fattura 001,\"1.234,56\"\n"
        csv_bytes = csv_content.encode('utf-8-sig')  # BOM for Italian compatibility
        
        upload_file = UploadFile(
            filename="registro_iva.csv",
            file=io.BytesIO(csv_bytes),
            content_type="text/csv",
            size=len(csv_bytes)
        )
        
        validation_result = await document_uploader.validate_file(upload_file)
        
        assert validation_result["is_valid"] == True
        assert validation_result["file_type"] == DocumentType.CSV
        assert validation_result["encoding"] == "utf-8-sig"
    
    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, document_uploader):
        """Test file size validation - file too large"""
        
        large_content = b"x" * (DOCUMENT_CONFIG["MAX_FILE_SIZE_MB"] * 1024 * 1024 + 1)
        
        upload_file = UploadFile(
            filename="large_file.pdf",
            file=io.BytesIO(large_content),
            content_type="application/pdf",
            size=len(large_content)
        )
        
        with pytest.raises(UploadValidationError) as exc_info:
            await document_uploader.validate_file(upload_file)
        
        assert "file too large" in str(exc_info.value).lower()
        assert f"{DOCUMENT_CONFIG['MAX_FILE_SIZE_MB']}MB" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_unsupported_file_type(self, document_uploader):
        """Test validation failure for unsupported file type"""
        
        upload_file = UploadFile(
            filename="malicious.exe",
            file=io.BytesIO(b"MZ\x90\x00"),  # PE executable header
            content_type="application/octet-stream",
            size=100
        )
        
        with pytest.raises(UploadValidationError) as exc_info:
            await document_uploader.validate_file(upload_file)
        
        assert "unsupported file type" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_validate_malicious_filename(self, document_uploader):
        """Test validation of malicious filenames"""
        
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\windows\\system32\\config",
            "file<script>alert('xss')</script>.pdf",
            "file\x00.pdf.exe"
        ]
        
        for filename in malicious_filenames:
            upload_file = UploadFile(
                filename=filename,
                file=io.BytesIO(b"%PDF-1.4\n"),
                content_type="application/pdf",
                size=20
            )
            
            validation_result = await document_uploader.validate_file(upload_file)
            
            # Should sanitize filename
            assert ".." not in validation_result["safe_filename"]
            assert "<" not in validation_result["safe_filename"]
            assert "\x00" not in validation_result["safe_filename"]
    
    @pytest.mark.asyncio
    async def test_virus_scan_simulation(self, document_uploader):
        """Test virus scanning simulation"""
        
        # Mock virus scanner
        with patch.object(document_uploader, '_scan_for_viruses') as mock_scan:
            mock_scan.return_value = {"clean": True, "threats": []}
            
            upload_file = UploadFile(
                filename="clean_file.pdf",
                file=io.BytesIO(b"%PDF-1.4\n"),
                content_type="application/pdf",
                size=20
            )
            
            validation_result = await document_uploader.validate_file(upload_file)
            
            assert validation_result["virus_scan"]["clean"] == True
            assert validation_result["virus_scan"]["threats"] == []
            mock_scan.assert_called_once()


class TestPDFDocumentProcessing:
    """Test PDF document processing for Italian tax documents"""
    
    @pytest.fixture
    def pdf_processor(self):
        return DocumentProcessor()
    
    @pytest.mark.asyncio
    async def test_extract_text_from_fattura_elettronica_pdf(self, pdf_processor):
        """Test text extraction from Italian electronic invoice PDF"""
        
        # Mock PDF content for Fattura Elettronica
        mock_pdf_text = """
        FATTURA ELETTRONICA
        Numero: FE001/2024
        Data: 15/03/2024
        
        Cedente / Prestatore:
        ABC S.R.L.
        Partita IVA: IT01234567890
        Codice Fiscale: 01234567890
        
        Cessionario / Committente:
        XYZ S.P.A.
        Partita IVA: IT09876543210
        
        Dettaglio Linee:
        Descrizione: Consulenza fiscale
        Quantità: 1
        Prezzo Unitario: 1.000,00 EUR
        Sconto: 0,00%
        Imponibile: 1.000,00 EUR
        Aliquota IVA: 22,00%
        Imposta: 220,00 EUR
        
        Totale Documento: 1.220,00 EUR
        """
        
        # Mock PDF extraction
        with patch('PyPDF2.PdfReader') as mock_pdf_reader:
            mock_page = Mock()
            mock_page.extract_text.return_value = mock_pdf_text
            mock_pdf_reader.return_value.pages = [mock_page]
            
            document = Document(
                id=uuid4(),
                filename="test_fattura.pdf",
                original_filename="FE001_2024.pdf",
                file_type=DocumentType.PDF.value,
                file_size=50000
            )
            
            extraction_result = await pdf_processor.extract_text(document)
            
            assert extraction_result["success"] == True
            assert "FATTURA ELETTRONICA" in extraction_result["text"]
            assert extraction_result["text_length"] > 100
            assert extraction_result["page_count"] == 1
    
    @pytest.mark.asyncio
    async def test_extract_structured_data_from_fattura(self, pdf_processor):
        """Test structured data extraction from Italian invoice"""
        
        mock_text = """
        FATTURA ELETTRONICA FE001/2024 del 15/03/2024
        Cedente: ABC S.R.L. - P.IVA IT01234567890
        Cessionario: XYZ S.P.A. - P.IVA IT09876543210
        Imponibile: 1.000,00 EUR
        IVA 22%: 220,00 EUR
        Totale: 1.220,00 EUR
        """
        
        document = Document(
            id=uuid4(),
            extracted_text=mock_text,
            file_type=DocumentType.PDF.value
        )
        
        extraction_result = await pdf_processor.extract_structured_data(document)
        
        assert extraction_result["success"] == True
        
        extracted = extraction_result["data"]
        assert extracted["document_type"] == "fattura_elettronica"
        assert extracted["numero"] == "FE001/2024"
        assert extracted["data"] == "15/03/2024"
        assert extracted["cedente"]["partita_iva"] == "IT01234567890"
        assert extracted["cessionario"]["partita_iva"] == "IT09876543210"
        assert extracted["totali"]["imponibile"] == 1000.00
        assert extracted["totali"]["iva"] == 220.00
        assert extracted["totali"]["totale"] == 1220.00
        assert extracted["aliquota_iva"] == 22.0
    
    @pytest.mark.asyncio
    async def test_extract_f24_data(self, pdf_processor):
        """Test F24 tax payment form data extraction"""
        
        f24_text = """
        MODELLO F24
        Anno di riferimento: 2024
        Codice Fiscale: RSSMRA80A01H501Z
        
        Sezione Erario:
        Codice Tributo: 4001 - IRPEF Acconto 1° rata
        Anno di riferimento: 2024
        Importo a debito: 1.500,00
        
        Codice Tributo: 6001 - IVA Mensile
        Periodo: 03/2024
        Importo a debito: 2.200,00
        
        Totale versamenti: 3.700,00
        """
        
        document = Document(
            id=uuid4(),
            extracted_text=f24_text,
            file_type=DocumentType.PDF.value
        )
        
        extraction_result = await pdf_processor.extract_structured_data(document)
        
        assert extraction_result["success"] == True
        
        extracted = extraction_result["data"]
        assert extracted["document_type"] == "f24"
        assert extracted["anno_riferimento"] == "2024"
        assert extracted["codice_fiscale"] == "RSSMRA80A01H501Z"
        
        tributi = extracted["tributi"]
        assert len(tributi) == 2
        assert tributi[0]["codice"] == "4001"
        assert tributi[0]["descrizione"] == "IRPEF Acconto 1° rata"
        assert tributi[0]["importo"] == 1500.00
        assert tributi[1]["codice"] == "6001"
        assert tributi[1]["importo"] == 2200.00
        
        assert extracted["totale_versamenti"] == 3700.00
    
    @pytest.mark.asyncio
    async def test_classify_italian_document_type(self, pdf_processor):
        """Test automatic classification of Italian document types"""
        
        test_cases = [
            {
                "text": "FATTURA ELETTRONICA Progressivo Invio FE001",
                "expected": ItalianDocumentCategory.FATTURA_ELETTRONICA,
                "confidence": 95
            },
            {
                "text": "MODELLO F24 Codice Tributo 4001 Versamento",
                "expected": ItalianDocumentCategory.F24,
                "confidence": 90
            },
            {
                "text": "MODELLO 730 Dichiarazione dei redditi",
                "expected": ItalianDocumentCategory.DICHIARAZIONE_730,
                "confidence": 88
            },
            {
                "text": "BILANCIO 2024 Stato Patrimoniale Conto Economico",
                "expected": ItalianDocumentCategory.BILANCIO,
                "confidence": 85
            }
        ]
        
        for case in test_cases:
            document = Document(
                id=uuid4(),
                extracted_text=case["text"],
                file_type=DocumentType.PDF.value
            )
            
            classification = await pdf_processor.classify_document(document)
            
            assert classification["category"] == case["expected"].value
            assert classification["confidence"] >= case["confidence"]
    
    @pytest.mark.asyncio
    async def test_handle_scanned_pdf_ocr(self, pdf_processor):
        """Test OCR processing for scanned PDFs"""
        
        # Mock OCR processing
        with patch('pytesseract.image_to_string') as mock_ocr:
            mock_ocr.return_value = "FATTURA ELETTRONICA\nNumero: FE001/2024"
            
            # Mock PDF with no extractable text (scanned)
            with patch('PyPDF2.PdfReader') as mock_pdf:
                mock_page = Mock()
                mock_page.extract_text.return_value = ""  # No text, needs OCR
                mock_pdf.return_value.pages = [mock_page]
                
                document = Document(
                    id=uuid4(),
                    filename="scanned_fattura.pdf",
                    file_type=DocumentType.PDF.value,
                    file_size=100000
                )
                
                extraction_result = await pdf_processor.extract_text(document)
                
                assert extraction_result["success"] == True
                assert extraction_result["ocr_used"] == True
                assert "FATTURA ELETTRONICA" in extraction_result["text"]
                mock_ocr.assert_called_once()


class TestExcelCSVProcessing:
    """Test Excel and CSV processing for Italian financial data"""
    
    @pytest.fixture
    def excel_processor(self):
        return DocumentProcessor()
    
    @pytest.mark.asyncio
    async def test_process_excel_bilancio(self, excel_processor):
        """Test processing Excel bilancio (financial statement)"""
        
        # Mock Excel data structure for Italian bilancio
        mock_balance_sheet = {
            "Stato Patrimoniale": [
                ["ATTIVO", "", ""],
                ["Immobilizzazioni", "100.000", ""],
                ["- Materiali", "80.000", ""],
                ["- Immateriali", "20.000", ""],
                ["Attivo Circolante", "50.000", ""],
                ["- Rimanenze", "30.000", ""],
                ["- Crediti", "20.000", ""],
                ["TOTALE ATTIVO", "150.000", ""],
                ["", "", ""],
                ["PASSIVO", "", ""],
                ["Patrimonio Netto", "100.000", ""],
                ["- Capitale Sociale", "50.000", ""],
                ["- Riserve", "50.000", ""],
                ["Debiti", "50.000", ""],
                ["TOTALE PASSIVO", "150.000", ""]
            ],
            "Conto Economico": [
                ["RICAVI", "200.000"],
                ["Vendite", "200.000"],
                ["COSTI", "180.000"],
                ["Materie Prime", "100.000"],
                ["Servizi", "50.000"],
                ["Personale", "30.000"],
                ["EBITDA", "20.000"],
                ["Ammortamenti", "5.000"],
                ["EBIT", "15.000"],
                ["Imposte", "3.000"],
                ["UTILE NETTO", "12.000"]
            ]
        }
        
        with patch('openpyxl.load_workbook') as mock_workbook:
            # Mock worksheet data
            mock_ws_sp = Mock()
            mock_ws_sp.title = "Stato Patrimoniale"
            mock_ws_sp.max_row = len(mock_balance_sheet["Stato Patrimoniale"])
            mock_ws_sp.iter_rows.return_value = [
                [Mock(value=cell) for cell in row] 
                for row in mock_balance_sheet["Stato Patrimoniale"]
            ]
            
            mock_ws_ce = Mock()
            mock_ws_ce.title = "Conto Economico"
            mock_ws_ce.max_row = len(mock_balance_sheet["Conto Economico"])
            mock_ws_ce.iter_rows.return_value = [
                [Mock(value=cell) for cell in row] 
                for row in mock_balance_sheet["Conto Economico"]
            ]
            
            mock_workbook.return_value.worksheets = [mock_ws_sp, mock_ws_ce]
            
            document = Document(
                id=uuid4(),
                filename="bilancio_2024.xlsx",
                file_type=DocumentType.EXCEL_XLSX.value,
                file_size=25000
            )
            
            processing_result = await excel_processor.process_excel(document)
            
            assert processing_result["success"] == True
            assert processing_result["sheets_processed"] == 2
            
            extracted_tables = processing_result["tables"]
            assert "Stato Patrimoniale" in extracted_tables
            assert "Conto Economico" in extracted_tables
            
            # Check financial analysis
            analysis = processing_result["financial_analysis"]
            assert analysis["totale_attivo"] == 150000
            assert analysis["totale_passivo"] == 150000
            assert analysis["patrimonio_netto"] == 100000
            assert analysis["utile_netto"] == 12000
            assert analysis["ebitda"] == 20000
            assert analysis["leverage_ratio"] == 0.5  # Debiti / Patrimonio Netto
    
    @pytest.mark.asyncio
    async def test_process_csv_registro_iva(self, excel_processor):
        """Test processing CSV IVA register"""
        
        csv_data = """Data,Numero,Cliente,Imponibile,Aliquota,Imposta,Totale
01/01/2024,001,Cliente A,"1.000,00",22,"220,00","1.220,00"
02/01/2024,002,Cliente B,"500,00",22,"110,00","610,00"
03/01/2024,003,Cliente C,"2.000,00",10,"200,00","2.200,00"
04/01/2024,004,Cliente D,"800,00",22,"176,00","976,00"
"""
        
        # Mock CSV reading
        with patch('pandas.read_csv') as mock_read_csv:
            import pandas as pd
            
            # Convert Italian number format
            df_data = [
                ["01/01/2024", "001", "Cliente A", "1.000,00", 22, "220,00", "1.220,00"],
                ["02/01/2024", "002", "Cliente B", "500,00", 22, "110,00", "610,00"],
                ["03/01/2024", "003", "Cliente C", "2.000,00", 10, "200,00", "2.200,00"],
                ["04/01/2024", "004", "Cliente D", "800,00", 22, "176,00", "976,00"]
            ]
            
            df = pd.DataFrame(df_data, columns=[
                "Data", "Numero", "Cliente", "Imponibile", "Aliquota", "Imposta", "Totale"
            ])
            mock_read_csv.return_value = df
            
            document = Document(
                id=uuid4(),
                filename="registro_iva.csv",
                file_type=DocumentType.CSV.value,
                file_size=500
            )
            
            processing_result = await excel_processor.process_csv(document)
            
            assert processing_result["success"] == True
            assert processing_result["rows_processed"] == 4
            assert processing_result["columns"] == 7
            
            # Check IVA analysis
            iva_analysis = processing_result["iva_analysis"]
            assert iva_analysis["totale_imponibile"] == 4300.00  # Sum of all imponibili
            assert iva_analysis["totale_imposta"] == 706.00     # Sum of all imposte
            assert iva_analysis["totale_fatturato"] == 5006.00  # Sum of all totali
            
            # Check by aliquota
            by_aliquota = iva_analysis["by_aliquota"]
            assert by_aliquota["22"]["count"] == 3
            assert by_aliquota["22"]["imponibile"] == 2300.00
            assert by_aliquota["10"]["count"] == 1
            assert by_aliquota["10"]["imponibile"] == 2000.00
    
    @pytest.mark.asyncio
    async def test_handle_italian_number_formats(self, excel_processor):
        """Test handling of Italian number formats in CSV/Excel"""
        
        test_numbers = [
            ("1.234,56", 1234.56),    # Italian thousands separator
            ("10.000,00", 10000.00),  # Large number
            ("0,50", 0.50),           # Decimal only
            ("1.000.000,99", 1000000.99),  # Million
            ("-500,25", -500.25),     # Negative
            ("1.234.567,89", 1234567.89)   # Complex
        ]
        
        for italian_str, expected_float in test_numbers:
            result = await excel_processor._parse_italian_number(italian_str)
            assert abs(result - expected_float) < 0.01, f"Failed for {italian_str}"
    
    @pytest.mark.asyncio
    async def test_detect_csv_encoding_with_bom(self, excel_processor):
        """Test detection of CSV encoding with Italian BOM"""
        
        # CSV with BOM and Italian characters
        csv_content = "\ufeffData,Descrizione,Importo\n01/01/2024,Società àèì,\"1.234,56\"\n"
        csv_bytes = csv_content.encode('utf-8-sig')
        
        document = Document(
            id=uuid4(),
            filename="test.csv",
            file_type=DocumentType.CSV.value
        )
        
        # Mock file reading
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = csv_bytes
            
            encoding_result = await excel_processor._detect_encoding(document)
            
            assert encoding_result["encoding"] == "utf-8-sig"
            assert encoding_result["has_bom"] == True
            assert encoding_result["confidence"] > 0.9


class TestDocumentAnalysisAI:
    """Test AI-powered document analysis"""
    
    @pytest.fixture
    def doc_analyzer(self):
        return ItalianDocumentAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_fattura_compliance(self, doc_analyzer):
        """Test AI analysis of invoice compliance"""
        
        fattura_data = {
            "document_type": "fattura_elettronica",
            "numero": "FE001/2024",
            "data": "15/03/2024",
            "cedente": {"partita_iva": "IT01234567890"},
            "cessionario": {"partita_iva": "IT09876543210"},
            "totali": {"imponibile": 1000.00, "iva": 220.00, "totale": 1220.00},
            "aliquota_iva": 22.0
        }
        
        query = "La fattura è compliant con la normativa italiana?"
        
        # Mock LLM analysis
        with patch.object(doc_analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "analysis": {
                    "compliance_status": "compliant",
                    "compliance_score": 95,
                    "issues": [],
                    "recommendations": []
                },
                "response": "La fattura elettronica FE001/2024 è conforme alla normativa italiana. Tutti i campi obbligatori sono presenti e l'IVA è calcolata correttamente al 22%."
            }
            
            analysis_result = await doc_analyzer.analyze_document(
                document_data=fattura_data,
                query=query,
                analysis_type="compliance_check"
            )
            
            assert analysis_result["success"] == True
            assert analysis_result["analysis"]["compliance_status"] == "compliant"
            assert analysis_result["analysis"]["compliance_score"] == 95
            assert analysis_result["confidence_score"] > 90
            assert "conforme" in analysis_result["response"]
    
    @pytest.mark.asyncio
    async def test_analyze_bilancio_financial_health(self, doc_analyzer):
        """Test financial health analysis of bilancio"""
        
        bilancio_data = {
            "document_type": "bilancio",
            "stato_patrimoniale": {
                "totale_attivo": 150000,
                "totale_passivo": 150000,
                "patrimonio_netto": 100000,
                "debiti": 50000
            },
            "conto_economico": {
                "ricavi": 200000,
                "costi": 180000,
                "ebitda": 20000,
                "utile_netto": 12000
            }
        }
        
        query = "Come sta andando finanziariamente l'azienda?"
        
        with patch.object(doc_analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "analysis": {
                    "financial_health": "good",
                    "health_score": 78,
                    "key_ratios": {
                        "leverage_ratio": 0.5,
                        "roe": 0.12,
                        "ebitda_margin": 0.10
                    },
                    "strengths": ["Utile positivo", "Leverage contenuto"],
                    "concerns": ["Margini migliorabili"]
                },
                "response": "L'azienda mostra una situazione finanziaria buona con un utile netto di €12.000 e un leverage ratio contenuto al 50%."
            }
            
            analysis_result = await doc_analyzer.analyze_document(
                document_data=bilancio_data,
                query=query,
                analysis_type="financial_analysis"
            )
            
            assert analysis_result["success"] == True
            assert analysis_result["analysis"]["financial_health"] == "good"
            assert analysis_result["analysis"]["health_score"] == 78
            assert "buona" in analysis_result["response"]
    
    @pytest.mark.asyncio
    async def test_multi_document_comparison(self, doc_analyzer):
        """Test comparison analysis across multiple documents"""
        
        documents_data = [
            {
                "filename": "bilancio_2023.xlsx",
                "data": {"utile_netto": 10000, "ricavi": 180000}
            },
            {
                "filename": "bilancio_2024.xlsx", 
                "data": {"utile_netto": 12000, "ricavi": 200000}
            }
        ]
        
        query = "Come sono cambiati i risultati tra 2023 e 2024?"
        
        with patch.object(doc_analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "analysis": {
                    "comparison_type": "year_over_year",
                    "changes": {
                        "ricavi": {"2023": 180000, "2024": 200000, "growth": "11.1%"},
                        "utile_netto": {"2023": 10000, "2024": 12000, "growth": "20.0%"}
                    },
                    "trend": "positive"
                },
                "response": "I risultati mostrano una crescita positiva: ricavi aumentati dell'11,1% e utile netto cresciuto del 20%."
            }
            
            comparison_result = await doc_analyzer.compare_documents(
                documents_data=documents_data,
                query=query
            )
            
            assert comparison_result["success"] == True
            assert comparison_result["analysis"]["trend"] == "positive"
            assert "crescita" in comparison_result["response"]
    
    @pytest.mark.asyncio
    async def test_extract_actionable_insights(self, doc_analyzer):
        """Test extraction of actionable business insights"""
        
        f24_data = {
            "document_type": "f24",
            "tributi": [
                {"codice": "4001", "importo": 1500.00, "descrizione": "IRPEF Acconto"},
                {"codice": "6001", "importo": 2200.00, "descrizione": "IVA Mensile"}
            ],
            "totale_versamenti": 3700.00
        }
        
        query = "Quali sono i prossimi adempimenti fiscali da considerare?"
        
        with patch.object(doc_analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "analysis": {
                    "next_deadlines": [
                        {"description": "Seconda rata acconto IRPEF", "date": "30/11/2024"},
                        {"description": "IVA mensile prossimo periodo", "date": "16/05/2024"}
                    ],
                    "recommendations": [
                        "Monitorare cashflow per versamenti novembre",
                        "Verificare detrazioni disponibili per ridurre acconto"
                    ]
                },
                "response": "Prossimi adempimenti: seconda rata acconto IRPEF (30/11) e IVA maggio (16/05). Consiglio di monitorare il cashflow."
            }
            
            insights_result = await doc_analyzer.generate_insights(
                document_data=f24_data,
                query=query
            )
            
            assert insights_result["success"] == True
            assert len(insights_result["analysis"]["next_deadlines"]) == 2
            assert len(insights_result["analysis"]["recommendations"]) == 2
            assert "cashflow" in insights_result["response"]


class TestSecureDocumentStorage:
    """Test secure document storage and cleanup"""
    
    @pytest.fixture
    def secure_storage(self):
        return SecureDocumentStorage()
    
    @pytest.mark.asyncio
    async def test_store_document_encrypted(self, secure_storage):
        """Test encrypted document storage"""
        
        document_content = b"Sample PDF content for encryption test"
        document = Document(
            id=uuid4(),
            filename="test_doc.pdf",
            file_type=DocumentType.PDF.value,
            file_size=len(document_content)
        )
        
        storage_result = await secure_storage.store_document(
            document=document,
            content=document_content
        )
        
        assert storage_result["success"] == True
        assert storage_result["encrypted"] == True
        assert storage_result["storage_path"] is not None
        assert storage_result["encryption_key_id"] is not None
    
    @pytest.mark.asyncio
    async def test_retrieve_document_decrypted(self, secure_storage):
        """Test document retrieval with decryption"""
        
        document_id = uuid4()
        original_content = b"Original document content"
        
        # Mock encrypted storage
        with patch.object(secure_storage, '_encrypt_content') as mock_encrypt:
            mock_encrypt.return_value = b"encrypted_content"
            
            with patch.object(secure_storage, '_decrypt_content') as mock_decrypt:
                mock_decrypt.return_value = original_content
                
                # Store document
                document = Document(id=document_id, filename="test.pdf")
                await secure_storage.store_document(document, original_content)
                
                # Retrieve document
                retrieval_result = await secure_storage.retrieve_document(document_id)
                
                assert retrieval_result["success"] == True
                assert retrieval_result["content"] == original_content
                assert retrieval_result["decrypted"] == True
    
    @pytest.mark.asyncio
    async def test_document_expiration_cleanup(self, secure_storage):
        """Test automatic cleanup of expired documents"""
        
        # Create expired document
        expired_document = Document(
            id=uuid4(),
            filename="expired.pdf",
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            is_deleted=False
        )
        
        cleanup_result = await secure_storage.cleanup_expired_documents()
        
        assert cleanup_result["success"] == True
        assert cleanup_result["documents_cleaned"] >= 0
        assert cleanup_result["storage_freed"] >= 0
    
    @pytest.mark.asyncio
    async def test_gdpr_compliant_deletion(self, secure_storage):
        """Test GDPR-compliant document deletion"""
        
        document_id = uuid4()
        document = Document(
            id=document_id,
            filename="gdpr_test.pdf",
            user_id=uuid4()
        )
        
        deletion_result = await secure_storage.gdpr_delete_document(
            document_id=document_id,
            user_id=document.user_id,
            reason="user_request"
        )
        
        assert deletion_result["success"] == True
        assert deletion_result["deletion_method"] == "secure_overwrite"
        assert deletion_result["audit_logged"] == True
        assert deletion_result["gdpr_compliant"] == True


@pytest.fixture
async def db_session():
    """Database session fixture for testing"""
    # Mock database session
    session = AsyncMock()
    yield session


@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return {
        "pdf_fattura": {
            "filename": "fattura_001.pdf",
            "content": b"%PDF-1.4\nSample fattura content",
            "content_type": "application/pdf"
        },
        "excel_bilancio": {
            "filename": "bilancio_2024.xlsx", 
            "content": b"PK\x03\x04\x14\x00\x00\x00\x08\x00",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        },
        "csv_registro": {
            "filename": "registro_iva.csv",
            "content": "Data,Importo\n01/01/2024,\"1.234,56\"\n".encode('utf-8-sig'),
            "content_type": "text/csv"
        }
    }


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])