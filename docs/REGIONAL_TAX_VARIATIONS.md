# Regional Tax Variations for PratikoAI

## Overview

The Regional Tax Variations system provides comprehensive support for Italian regional and municipal tax calculations, accounting for the significant variations in tax rates across Italy's 20 regions and 8,000+ municipalities.

This system handles:
- **IMU (Imposta Municipale Unica)** - Municipal property tax with rates varying by comune
- **IRAP (Imposta Regionale sulle Attività Produttive)** - Regional business tax with industry-specific rates
- **Addizionali IRPEF** - Regional and municipal income tax surcharges with local exemptions

## Key Features

### 🎯 Accurate Location-Based Calculations
- **CAP-to-Comune Mapping**: Precise identification of tax jurisdiction from postal codes
- **Real-Time Rate Lookup**: Current tax rates for all major Italian municipalities
- **Fallback Mechanisms**: Default rates when specific municipal data unavailable

### 🏛️ Complete Italian Tax Coverage
- **All 20 Regions**: Full support for regional tax variations including autonomous regions
- **Major Municipalities**: Detailed rates for 100+ largest Italian cities
- **Business Categories**: Differentiated IRAP rates for banks, insurance, agriculture, cooperatives

### ⚡ High-Performance API
- **Rate Limiting**: 50-200 requests per hour depending on endpoint complexity
- **Caching**: Redis-backed caching for fast response times
- **Batch Operations**: Support for multiple calculations in single request

## Architecture

### Database Schema

```sql
-- Regional tax rates (IRAP, addizionale regionale IRPEF)
CREATE TABLE regional_tax_rates (
    id UUID PRIMARY KEY,
    regione_id UUID REFERENCES regioni(id),
    tax_type VARCHAR(50) NOT NULL, -- IRAP, ADDIZIONALE_IRPEF
    rate_standard DECIMAL(5,2) NOT NULL,
    rate_banks DECIMAL(5,2), -- Higher rate for banks
    rate_insurance DECIMAL(5,2), -- Higher rate for insurance
    rate_agriculture DECIMAL(5,2), -- Lower rate for agriculture
    valid_from DATE NOT NULL,
    valid_to DATE
);

-- Municipal tax rates (IMU, addizionale comunale IRPEF)
CREATE TABLE comunal_tax_rates (
    id UUID PRIMARY KEY,
    comune_id UUID REFERENCES comuni(id),
    tax_type VARCHAR(50) NOT NULL, -- IMU, ADDIZIONALE_COMUNALE_IRPEF
    rate DECIMAL(5,2) NOT NULL,
    rate_prima_casa DECIMAL(5,2), -- Primary residence rate
    esenzione_prima_casa BOOLEAN DEFAULT FALSE,
    detrazioni JSONB, -- Deductions by category
    soglie JSONB, -- Income thresholds
    valid_from DATE NOT NULL,
    valid_to DATE
);
```

### Service Layer

The system is built with three main service layers:

1. **RegionalTaxService**: Core calculation engine
2. **ItalianLocationService**: Geographic data and CAP resolution
3. **TaxRateManagementService**: Data updates and rate management

## API Endpoints

### Tax Calculations

#### Calculate IMU
```http
POST /api/v1/taxes/regional-taxes/calculate/imu
Content-Type: application/json

{
    "property_value": 300000,
    "cap": "00100",
    "is_prima_casa": true,
    "property_type": "standard"
}
```

**Response:**
```json
{
    "location": {
        "comune": "Roma",
        "provincia": "RM",
        "cap": "00100"
    },
    "calculation": {
        "comune": "Roma",
        "provincia": "RM",
        "aliquota": 0,
        "base_imponibile": 189000,
        "imposta_lorda": 0,
        "detrazioni": 0,
        "imposta_dovuta": 0,
        "note": "Abitazione principale esente IMU"
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Calculate IRAP
```http
POST /api/v1/taxes/regional-taxes/calculate/irap
Content-Type: application/json

{
    "revenue": 1000000,
    "region": "Lazio",
    "business_type": "standard"
}
```

**Response:**
```json
{
    "region_info": {
        "regione": "Lazio",
        "tipo_attivita": "standard"
    },
    "calculation": {
        "regione": "Lazio",
        "aliquota": 4.82,
        "tipo_attivita": "standard",
        "fatturato": 1000000,
        "valore_produzione": 850000,
        "imposta_dovuta": 40970,
        "note": "Aliquota IRAP Lazio - standard"
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Calculate IRPEF Addizionali
```http
POST /api/v1/taxes/regional-taxes/calculate/irpef-addizionali
Content-Type: application/json

{
    "taxable_income": 50000,
    "cap": "00100"
}
```

**Response:**
```json
{
    "location": {
        "comune": "Roma",
        "provincia": "RM",
        "regione": "Lazio",
        "cap": "00100"
    },
    "calculation": {
        "comune": "Roma",
        "provincia": "RM",
        "regione": "Lazio",
        "reddito_imponibile": 50000,
        "addizionale_regionale": {
            "aliquota": 1.73,
            "importo": 865
        },
        "addizionale_comunale": {
            "aliquota": 0.9,
            "importo": 450
        },
        "totale_addizionali": 1315
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Complete Tax Calculation
```http
POST /api/v1/taxes/regional-taxes/calculate/complete
Content-Type: application/json

{
    "cap": "20100",
    "income": 50000,
    "property_value": 400000,
    "is_prima_casa": false,
    "business_revenue": 500000,
    "business_type": "standard"
}
```

### Location Services

#### Get Location by CAP
```http
GET /api/v1/taxes/regional-taxes/locations/20100
```

#### Search Locations
```http
POST /api/v1/taxes/regional-taxes/locations/search
Content-Type: application/json

{
    "query": "Milano",
    "region_filter": "Lombardia",
    "limit": 10
}
```

#### Tax Comparison
```http
GET /api/v1/taxes/regional-taxes/compare?cap1=00100&cap2=20100&income=50000&property_value=300000
```

## Regional Tax Variations

### IMU (Municipal Property Tax)

IMU rates vary significantly across Italian municipalities:

| City | Standard Rate | Primary Residence | Exemption |
|------|---------------|-------------------|-----------|
| Roma | 1.06% | 0.5% | ✅ Exempt |
| Milano | 1.04% | 0.6% | ❌ Not exempt |
| Napoli | 1.14% | 0.6% | ❌ Not exempt |
| Torino | 1.06% | 0.45% | ✅ Exempt |

**Key Features:**
- **Primary Residence Exemptions**: Many cities exempt primary residences
- **Deductions**: Fixed deductions (€200-€300) for primary residences
- **Property Type Variations**: Different rates for commercial, industrial, agricultural properties

### IRAP (Regional Business Tax)

IRAP rates vary by region and business sector:

| Region | Standard | Banks | Insurance | Agriculture |
|--------|----------|-------|-----------|-------------|
| Lazio | 4.82% | 5.57% | 6.82% | 1.9% |
| Lombardia | 3.9% | 5.57% | 6.82% | 1.9% |
| Campania | 3.9% | 5.57% | 6.82% | 1.9% |

**Key Features:**
- **Sectoral Differentiation**: Higher rates for banks and insurance companies
- **Agricultural Benefits**: Reduced rates for agricultural activities
- **Regional Autonomy**: Regions can modify the base 3.9% rate

### Addizionali IRPEF (Income Tax Surcharges)

#### Regional Addizionale IRPEF

| Region | Rate | Notes |
|--------|------|-------|
| Lazio | 1.73% | Standard rate |
| Lombardia | 1.73% | Standard rate |
| Campania | 2.03% | Higher rate |
| Bolzano | 1.23% | Lowest rate |

#### Municipal Addizionale IRPEF

| City | Rate | Exemption Threshold |
|------|------|-------------------|
| Roma | 0.9% | €11,000 |
| Milano | 0.8% | €15,000 |
| Napoli | 0.8% | €12,000 |
| Torino | 0.8% | €14,000 |

**Key Features:**
- **Income Thresholds**: Most municipalities exempt low incomes
- **Variable Rates**: Rates from 0% to 0.9% maximum
- **Progressive Exemptions**: Some cities use progressive exemption scales

## Implementation Examples

### Basic IMU Calculation

```python
from app.services.regional_tax_service import RegionalTaxService
from decimal import Decimal

async def calculate_property_tax():
    service = RegionalTaxService(db)
    
    result = await service.calculate_imu(
        property_value=Decimal("300000"),
        cap="00100",  # Roma
        is_prima_casa=True
    )
    
    # Result: €0 (Roma exempts primary residences)
    return result
```

### Tax Burden Comparison

```python
async def compare_cities():
    service = RegionalTaxService(db)
    
    comparison = await service.compare_regional_taxes(
        cap1="00100",  # Roma
        cap2="20100",  # Milano
        income=Decimal("50000"),
        property_value=Decimal("300000")
    )
    
    # Shows Milano has higher total tax burden
    return comparison
```

### Business Tax Calculation

```python
async def calculate_business_taxes():
    service = RegionalTaxService(db)
    
    irap_result = await service.calculate_irap(
        revenue=Decimal("1000000"),
        region="Lazio",
        business_type="banks"  # Higher rate
    )
    
    # Result: €47,345 (5.57% rate for banks in Lazio)
    return irap_result
```

## Data Sources and Updates

### Official Sources
- **Ministero dell'Economia e delle Finanze (MEF)**: National tax policy
- **Agenzia delle Entrate**: Tax administration and guidance
- **Municipal Deliberations**: Local tax rate decisions
- **Regional Laws**: Regional tax variations and autonomous provisions

### Update Frequency
- **Annual Updates**: Major rate changes effective January 1st
- **Quarterly Reviews**: Municipal deliberation monitoring
- **Emergency Updates**: Immediate updates for significant changes

### Data Import System

The system includes automated import capabilities:

```bash
# Import base regional data
python scripts/import_regional_rates.py

# Import from CSV file
python scripts/import_regional_rates.py csv data/imu_rates_2024.csv imu

# Validate imported data
python scripts/import_regional_rates.py validate
```

## Testing

### Comprehensive Test Coverage

The system includes extensive test coverage following TDD methodology:

```bash
# Run all regional tax tests
pytest tests/test_regional_taxes.py -v

# Run specific test categories
pytest tests/test_regional_taxes.py::TestIMUCalculations -v
pytest tests/test_regional_taxes.py::TestLocationDetection -v
pytest tests/test_regional_taxes.py::TestIRAPCalculations -v
```

### Test Categories

1. **Location Detection Tests**
   - CAP to comune mapping accuracy
   - Province to region relationships
   - Invalid input handling

2. **Tax Calculation Tests**
   - IMU calculations for major cities
   - IRAP calculations by region and business type
   - IRPEF addizionali with thresholds

3. **Integration Tests**
   - Complete tax burden calculations
   - Tax comparison functionality
   - API endpoint responses

4. **Performance Tests**
   - Response time under load
   - Caching effectiveness
   - Database query optimization

## Security and Compliance

### Data Protection
- **No Personal Data Storage**: Only aggregate tax rates and geographic data
- **Audit Logging**: All calculations logged for compliance
- **Rate Limiting**: Prevents abuse and ensures fair usage

### Legal Compliance
- **GDPR Compliant**: No personal data processing beyond user authentication
- **Official Rate Sources**: All rates traceable to official government sources
- **Disclaimer**: Calculations are indicative; users advised to consult official sources

## Performance Optimization

### Caching Strategy
- **Redis Caching**: Location data cached for 24 hours
- **Database Indexing**: Optimized queries on CAP codes and tax types
- **API Response Caching**: Frequent calculations cached for faster response

### Scalability
- **Async Operations**: All database operations use async/await
- **Connection Pooling**: Efficient database connection management
- **Load Balancing**: API designed for horizontal scaling

## Troubleshooting

### Common Issues

#### CAP Not Found
```json
{
  "detail": "CAP 99999 non trovato",
  "error_code": "LOCATION_NOT_FOUND"
}
```
**Solution**: Verify CAP format (5 digits) and check if it's a valid Italian postal code.

#### Tax Rates Unavailable
```json
{
  "detail": "Aliquote IMU non disponibili per Piccolo Comune",
  "error_code": "TAX_RATE_NOT_FOUND"
}
```
**Solution**: System falls back to regional default rates for small municipalities.

#### Invalid Calculation Parameters
```json
{
  "detail": "Il valore dell'immobile non può essere negativo",
  "error_code": "INVALID_TAX_CALCULATION"
}
```
**Solution**: Verify all numeric inputs are positive and within reasonable ranges.

### Monitoring and Alerts

- **Response Time Monitoring**: Alert if API response > 2 seconds
- **Error Rate Monitoring**: Alert if error rate > 5%
- **Data Freshness**: Alert if tax rates older than 1 year
- **Cache Hit Rate**: Monitor cache effectiveness

## Development Guidelines

### Adding New Tax Types

1. **Define Models**: Add new tax rate models in `app/models/regional_taxes.py`
2. **Implement Service**: Add calculation logic in `RegionalTaxService`
3. **Create API**: Add endpoints in `app/api/v1/regional_taxes.py`
4. **Write Tests**: Comprehensive test coverage required
5. **Update Documentation**: Update this documentation with new features

### Contributing Rate Data

1. **Official Sources Only**: Only use verified government sources
2. **Data Validation**: All imports must pass validation checks
3. **Audit Trail**: Maintain records of data sources and update dates
4. **Testing**: Test with known values before deployment

## API Rate Limits

| Endpoint Category | Requests/Hour | Use Case |
|------------------|---------------|----------|
| Location Lookup | 200 | High-frequency location queries |
| Tax Calculation | 50 | Standard tax calculations |
| Complete Calculation | 20 | Complex multi-tax calculations |
| Tax Comparison | 10 | Intensive comparison operations |

## Support and Resources

### Documentation
- **API Reference**: Available at `/docs` when running the application
- **Postman Collection**: Complete API collection for testing
- **Code Examples**: Sample implementations in multiple languages

### Support Channels
- **Technical Support**: `support@pratikoai.com`
- **Bug Reports**: GitHub Issues
- **Feature Requests**: Product roadmap discussions

### Legal Resources
- **Tax Law References**: Links to relevant Italian tax legislation
- **Municipal Websites**: Direct links to official rate publications
- **Professional Consultation**: Recommendation to consult tax professionals for complex cases

---

This documentation provides comprehensive coverage of the Regional Tax Variations system. For specific implementation details, refer to the source code and test files. For questions about Italian tax law, consult qualified tax professionals.