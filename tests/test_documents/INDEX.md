# Italian Tax Document Test Samples

This directory contains sample Italian tax documents for testing the document upload and processing system. These documents are designed to test various aspects of the Italian tax document analysis pipeline.

## Document Types

### 📄 XML Documents

#### `sample_fattura_elettronica.xml`
- **Type**: Fattura Elettronica (Electronic Invoice)
- **Purpose**: Tests XML parsing for Italian SDI format invoices
- **Contains**:
  - Supplier data (Studio Commerciale Rossi & Associati SRL)
  - Customer data (Azienda Cliente SPA)
  - Invoice details with 22% IVA calculation
  - Payment terms and methods
- **Use Case**: Validates XML structure, VAT calculations, Italian business data extraction

### 📊 CSV Documents

#### `sample_bilancio.csv`
- **Type**: Balance Sheet (Stato Patrimoniale)
- **Purpose**: Tests CSV parsing of Italian accounting data
- **Contains**:
  - Chart of accounts in Italian
  - Asset and liability entries
  - Proper Italian decimal formatting (comma separator)
  - Italian accounting terminology
- **Use Case**: Tests CSV parsing with Italian number formats, accounting data extraction

#### `sample_registro_iva_vendite.csv`
- **Type**: VAT Sales Register (Registro IVA Vendite)
- **Purpose**: Tests VAT transaction processing
- **Contains**:
  - Monthly VAT sales transactions
  - Client data with Partita IVA
  - Different VAT rates (10%, 22%)
  - Italian date formatting (DD/MM/YYYY)
- **Use Case**: VAT compliance checking, date parsing, tax rate validation

### 📈 Excel Documents

#### `sample_f24.xlsx`
- **Type**: F24 Tax Payment Form
- **Purpose**: Tests Excel parsing for Italian tax payments
- **Contains**:
  - Tax code mappings (IRPEF, IVA, Addizionali)
  - Payment deadlines
  - Taxpayer identification data
- **Use Case**: Tax payment analysis, deadline tracking

#### `sample_registro_iva.xlsx`
- **Type**: VAT Register (Registro IVA)
- **Purpose**: Tests Excel VAT accounting data
- **Contains**:
  - Monthly VAT liquidations
  - VAT on sales vs. purchases
  - Net VAT positions
- **Use Case**: VAT compliance analysis, monthly tax calculations

#### `sample_documenti_fiscali_completi.xlsx`
- **Type**: Comprehensive Tax Documents
- **Purpose**: Tests multi-sheet Excel processing
- **Contains**:
  - F24 payments sheet
  - Tax declaration sheet (Dichiarazione dei Redditi)
  - Balance sheet data
- **Use Case**: Multi-document processing, cross-reference validation

## Test Scenarios

### Security Testing
- All documents are clean and safe for testing
- No malicious content or embedded scripts
- Realistic file sizes and structures
- Proper encoding (UTF-8 with BOM support)

### Data Extraction Testing
- Italian business names and addresses
- Partita IVA and Codice Fiscale formats
- Italian tax codes and descriptions
- Proper VAT calculations (22%, 10%, etc.)
- Italian date formats (DD/MM/YYYY)
- Italian number formats (comma as decimal separator)

### Format Validation Testing
- XML: SDI electronic invoice format
- CSV: Italian delimiter (semicolon)
- Excel: Multiple sheets with different data types

## Italian Tax Context

### Tax Codes (Codici Tributo)
- `1001`: IRPEF - Acconto Prima Rata
- `1040`: IRPEF - Saldo
- `3844`: IVA - Versamento Mensile
- `4033`: Addizionale Regionale IRPEF
- `6781`: Addizionale Comunale IRPEF

### VAT Rates (Aliquote IVA)
- `22%`: Standard rate (aliquota ordinaria)
- `10%`: Reduced rate (aliquota ridotta)
- `4%`: Super-reduced rate (aliquota agevolata)

### Document Types
- **Fattura Elettronica**: Electronic invoice for B2B/B2G transactions
- **F24**: Unified tax payment form
- **Registro IVA**: VAT register for compliance
- **Dichiarazione dei Redditi**: Annual tax return
- **Stato Patrimoniale**: Balance sheet

## Usage in Tests

These documents can be used to test:

1. **File Upload Validation**
   ```python
   # Test file type detection
   await uploader.validate_file(sample_xml_file)
   ```

2. **Content Processing**
   ```python
   # Test Italian document analysis
   analysis = await analyzer.analyze_italian_document(content)
   ```

3. **Data Extraction**
   ```python
   # Test specific data extraction
   vat_data = processor.extract_vat_data(csv_content)
   ```

4. **Security Scanning**
   ```python
   # Verify clean documents pass security checks
   scan_result = await scanner.scan_document(file_content)
   assert scan_result['clean'] == True
   ```

## Regenerating Documents

To recreate the Excel documents, run:

```bash
cd tests/test_documents
python create_simple_excel.py
```

## Notes

- All data is fictional and for testing purposes only
- Documents follow current Italian tax regulations (2024)
- Encoding is UTF-8 to support Italian characters
- File sizes are kept reasonable for testing (< 1MB each)
- All VAT calculations are mathematically correct
