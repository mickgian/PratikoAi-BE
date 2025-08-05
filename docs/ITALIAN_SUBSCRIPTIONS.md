# Italian Market Annual Subscription Plans

This document provides comprehensive documentation for the Italian market subscription system with support for annual plans, IVA calculations, and electronic invoicing compliance.

## Overview

PratikoAI's Italian subscription system supports both monthly and annual billing with full compliance to Italian tax regulations and electronic invoicing requirements. The system provides a 27.7% discount for annual subscribers and handles all Italian market requirements including Partita IVA validation, Codice Fiscale processing, and fattura elettronica generation.

### Key Features

- **Annual Subscription Plans**: €599/year with 27.7% savings vs monthly (€229 annual savings)
- **Monthly Subscription Plans**: €69/month (unchanged from existing pricing)
- **Italian VAT Compliance**: 22% IVA calculations for all customers
- **B2B Support**: Partita IVA validation using Luhn algorithm
- **B2C Support**: Codice Fiscale validation with pattern matching
- **Electronic Invoicing**: Complete fattura elettronica XML generation for SDI compliance
- **Plan Changes**: Seamless upgrades/downgrades with proper proration
- **Stripe Integration**: Full payment processing with Italian tax rates
- **MRR Calculation**: Proper monthly recurring revenue tracking for annual plans

## Architecture

### Core Components

```
Italian Subscription System
├── Models (app/models/subscription.py)
│   ├── SubscriptionPlan - Plan definitions with Italian pricing
│   ├── Subscription - User subscriptions with Italian tax data
│   ├── SubscriptionPlanChange - Plan change tracking
│   └── Invoice - Italian invoices with fattura elettronica
├── Services
│   ├── ItalianSubscriptionService - Core subscription logic
│   └── ItalianInvoiceService - Invoice and XML generation
├── API (app/api/v1/italian_subscriptions.py)
│   ├── Subscription management endpoints
│   ├── Invoice download endpoints
│   └── Tax validation endpoints
└── Tests (tests/test_annual_subscriptions.py)
    └── Comprehensive TDD test suite
```

### Technology Stack

- **FastAPI**: REST API endpoints with comprehensive validation
- **SQLAlchemy 2.0**: Async database operations with PostgreSQL
- **Stripe**: Payment processing with Italian tax rates
- **Pydantic**: Request/response validation with Italian tax data
- **ReportLab**: PDF invoice generation with Italian formatting
- **XML ElementTree**: Fattura elettronica XML generation

## Quick Start

### Environment Setup

```bash
# Required environment variables
export STRIPE_SECRET_KEY="sk_test_..." # Stripe secret key
export COMPANY_PARTITA_IVA="12345678901" # Your company's Partita IVA
export COMPANY_CODICE_FISCALE="12345678901" # Your company's Codice Fiscale

# Optional settings
export JWT_ACCESS_TOKEN_EXPIRE_HOURS=720 # 30 days
export JWT_REFRESH_TOKEN_EXPIRE_DAYS=365 # 1 year
```

### Database Setup

```bash
# Run migrations to create subscription tables
uv run alembic upgrade head

# The following tables will be created:
# - subscription_plans (plan definitions)
# - subscriptions (user subscriptions)
# - subscription_plan_changes (plan change history)
# - invoices (Italian invoices with XML)
```

### Stripe Configuration

Create the following in your Stripe dashboard:

```javascript
// Monthly Plan
stripe.prices.create({
  unit_amount: 6900, // €69.00 in cents
  currency: 'eur',
  recurring: {interval: 'month'},
  product: 'prod_professional_it',
  nickname: 'Professional Monthly IT'
});

// Annual Plan
stripe.prices.create({
  unit_amount: 59900, // €599.00 in cents
  currency: 'eur',
  recurring: {interval: 'year'},
  product: 'prod_professional_it',
  nickname: 'Professional Annual IT'
});

// Italian Tax Rate (22% IVA)
stripe.taxRates.create({
  display_name: 'IVA',
  description: 'Italian VAT',
  jurisdiction: 'IT',
  percentage: 22.0,
  inclusive: false
});
```

## API Usage

### Authentication

All subscription endpoints require authentication:

```bash
# Login to get access token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token in subsequent requests
export ACCESS_TOKEN="eyJ0eXAiOiJKV1Q..."
```

### Get Available Plans

```bash
curl -X GET "http://localhost:8000/api/v1/billing/italian-subscriptions/plans" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Response:
```json
[
  {
    "id": "uuid-monthly",
    "name": "Professionale Mensile",
    "billing_period": "monthly",
    "base_price": 69.00,
    "iva_amount": 15.18,
    "price_with_iva": 84.18,
    "monthly_equivalent": 69.00,
    "annual_savings": 0.00,
    "discount_percentage": 0.00,
    "trial_period_days": 7,
    "currency": "EUR",
    "iva_rate": 22.0
  },
  {
    "id": "uuid-annual",
    "name": "Professionale Annuale",
    "billing_period": "annual",
    "base_price": 599.00,
    "iva_amount": 131.78,
    "price_with_iva": 730.78,
    "monthly_equivalent": 49.92,
    "annual_savings": 229.00,
    "discount_percentage": 27.7,
    "trial_period_days": 7,
    "currency": "EUR",
    "iva_rate": 22.0,
    "popular": true,
    "savings_message": "Risparmi €229 all'anno!",
    "monthly_equivalent_message": "Solo €49.92/mese"
  }
]
```

### Create Subscription (B2B Customer)

```bash
curl -X POST "http://localhost:8000/api/v1/billing/italian-subscriptions/create" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_type": "annual",
    "payment_method_id": "pm_1234567890",
    "customer_data": {
      "is_business": true,
      "partita_iva": "12345678903",
      "invoice_name": "Acme SRL",
      "invoice_address": "Via Roma 123",
      "invoice_cap": "00100",
      "invoice_city": "Roma",
      "invoice_province": "RM",
      "sdi_code": "ABCDEFG",
      "pec_email": "fatture@acme.it"
    },
    "trial_days": 7
  }'
```

### Create Subscription (B2C Customer)

```bash
curl -X POST "http://localhost:8000/api/v1/billing/italian-subscriptions/create" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_type": "monthly",
    "payment_method_id": "pm_1234567890",
    "customer_data": {
      "is_business": false,
      "codice_fiscale": "RSSMRA80A01H501U",
      "invoice_name": "Mario Rossi",
      "invoice_address": "Via Milano 456",
      "invoice_cap": "20100",
      "invoice_city": "Milano",
      "invoice_province": "MI"
    }
  }'
```

### Change Plan (Monthly to Annual)

```bash
curl -X PUT "http://localhost:8000/api/v1/billing/italian-subscriptions/{subscription_id}/change-plan" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_plan_type": "annual",
    "prorate": true
  }'
```

Response:
```json
{
  "success": true,
  "subscription": { ... },
  "new_plan": { ... },
  "prorated_charge": 530.00,
  "credit_applied": 69.00,
  "message": "Piano cambiato con successo"
}
```

### Download Invoice PDF

```bash
curl -X GET "http://localhost:8000/api/v1/billing/italian-subscriptions/{subscription_id}/invoices/{invoice_id}/pdf" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --output "fattura_2024_0001.pdf"
```

### Download Electronic Invoice XML

```bash
curl -X GET "http://localhost:8000/api/v1/billing/italian-subscriptions/{subscription_id}/invoices/{invoice_id}/xml" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --output "fattura_elettronica_2024_0001.xml"
```

## Italian Tax Compliance

### Partita IVA Validation

The system validates Italian VAT numbers using the Luhn algorithm:

```python
def validate_partita_iva(partita_iva: str) -> bool:
    """Validate 11-digit Italian VAT number"""
    if len(partita_iva) != 11 or not partita_iva.isdigit():
        return False
    
    # Luhn algorithm implementation
    total = 0
    for i in range(10):
        digit = int(partita_iva[i])
        if i % 2 == 0:
            total += digit
        else:
            doubled = digit * 2
            total += doubled if doubled < 10 else doubled - 9
    
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(partita_iva[10])
```

Valid examples:
- `12345678903` ✅
- `01234567890` ✅
- `11111111111` ❌ (fails Luhn check)

### Codice Fiscale Validation

Basic format validation for Italian tax codes:

```python
def validate_codice_fiscale(codice_fiscale: str) -> bool:
    """Validate 16-character Italian tax code format"""
    pattern = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
    return bool(re.match(pattern, codice_fiscale.upper()))
```

Valid examples:
- `RSSMRA80A01H501U` ✅
- `BNCGVN85T50F205X` ✅
- `INVALID123456789` ❌

### IVA Calculations

All prices include 22% Italian VAT:

```python
# Pricing breakdown
base_price = Decimal("599.00")  # Annual plan base price
iva_rate = Decimal("22.00")     # Italian VAT rate
iva_amount = base_price * (iva_rate / 100)  # €131.78
total_price = base_price + iva_amount       # €730.78

# Monthly equivalent for annual plan
monthly_equivalent = base_price / 12        # €49.92/month

# Annual savings vs monthly
monthly_total = Decimal("69.00") * 12       # €828
annual_savings = monthly_total - base_price # €229
discount_percentage = (annual_savings / monthly_total) * 100  # 27.7%
```

## Electronic Invoicing (Fattura Elettronica)

### Requirements

Business customers (B2B) with Partita IVA require electronic invoices for SDI compliance:

- **SDI Code**: 7-character destination code for electronic transmission
- **PEC Email**: Certified email address for invoice delivery
- **XML Format**: Specific XML structure required by Italian regulations

### XML Generation

The system generates compliant fattura elettronica XML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" 
  xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
  xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente>
        <IdPaese>IT</IdPaese>
        <IdCodice>12345678901</IdCodice>
      </IdTrasmittente>
      <ProgressivoInvio>ABC12</ProgressivoInvio>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>ABCDEFG</CodiceDestinatario>
    </DatiTrasmissione>
    
    <CedentePrestatore>
      <!-- Supplier data (PratikoAI) -->
    </CedentePrestatore>
    
    <CessionarioCommittente>
      <!-- Customer data -->
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Divisa>EUR</Divisa>
        <Data>2024-12-05</Data>
        <Numero>2024/0001</Numero>
        <ImportoTotaleDocumento>730.78</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    
    <DatiBeni>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Abbonamento Professionale Annuale</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>599.00</PrezzoUnitario>
        <PrezzoTotale>599.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
    </DatiBeni>
    
    <DatiRiepilogo>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>599.00</ImponibileImporto>
        <Imposta>131.78</Imposta>
      </DatiRiepilogo>
    </DatiRiepilogo>
    
    <DatiPagamento>
      <CondizioniPagamento>TP02</CondizioniPagamento>
      <DettaglioPagamento>
        <ModalitaPagamento>MP05</ModalitaPagamento>
        <DataScadenzaPagamento>2025-01-04</DataScadenzaPagamento>
        <ImportoPagamento>730.78</ImportoPagamento>
      </DettaglioPagamento>
    </DatiPagamento>
  </FatturaElettronicaBody>
</p:FatturaElettronica>
```

### SDI Transmission

The system queues electronic invoices for SDI transmission:

1. **Generation**: XML created upon subscription/payment
2. **Validation**: Schema validation against Italian requirements
3. **Queue**: Background job queues invoice for transmission
4. **Transmission**: Simulated SDI submission (production would use actual SDI API)
5. **Status Tracking**: Monitor transmission status and responses

## Plan Changes and Proration

### Upgrade (Monthly → Annual)

When a customer upgrades from monthly to annual:

```python
# Example: Customer paid €69 on Dec 1, wants to upgrade on Dec 15
current_plan_price = Decimal("69.00")        # Monthly plan
new_plan_price = Decimal("599.00")           # Annual plan

# Calculate unused portion of monthly plan
days_in_month = 31
days_used = 14      # Dec 1 to Dec 15
days_remaining = 17 # Dec 15 to Dec 31

# Proration credit
monthly_daily_rate = current_plan_price / days_in_month  # €2.23/day
credit_amount = monthly_daily_rate * days_remaining      # €37.87

# Immediate charge
immediate_charge = new_plan_price - credit_amount        # €561.13
```

### Downgrade (Annual → Monthly)

When a customer downgrades from annual to monthly:

```python
# Example: Customer paid €599 on Jan 1, wants to downgrade on Jun 1
current_plan_price = Decimal("599.00")       # Annual plan
new_plan_price = Decimal("69.00")            # Monthly plan

# Calculate unused portion of annual plan
days_in_year = 365
days_used = 151     # Jan 1 to Jun 1
days_remaining = 214 # Jun 1 to Dec 31

# Proration credit
annual_daily_rate = current_plan_price / days_in_year    # €1.64/day
credit_amount = annual_daily_rate * days_remaining       # €351.01

# Since credit exceeds monthly price, customer gets full credit
# No immediate charge, credit applied to future bills
immediate_charge = Decimal("0.00")
```

## MRR Calculation

Monthly Recurring Revenue is calculated correctly for annual subscriptions:

```python
def calculate_mrr(subscription):
    """Calculate MRR for subscription"""
    if subscription.plan.billing_period == "annual":
        # Annual: €599/year = €49.92/month for MRR purposes
        return subscription.plan.base_price / 12
    else:
        # Monthly: €69/month
        return subscription.plan.base_price

# Example MRR calculations:
# - Monthly subscriber: €69.00/month MRR
# - Annual subscriber: €49.92/month MRR (€599 ÷ 12)
```

This ensures accurate revenue reporting where:
- Annual subscribers contribute €49.92/month to MRR
- Monthly subscribers contribute €69.00/month to MRR
- Total MRR reflects actual monthly revenue equivalent

## Testing

### TDD Test Suite

Comprehensive test coverage in `tests/test_annual_subscriptions.py`:

```python
# Test categories covered:
class TestSubscriptionCreation:
    """Test subscription creation with various scenarios"""
    
class TestPlanChanges:
    """Test plan upgrades/downgrades with proration"""
    
class TestItalianInvoices:
    """Test Italian invoice generation and XML creation"""
    
class TestFinancialReporting:
    """Test MRR calculations and financial metrics"""
    
class TestValidation:
    """Test Partita IVA and Codice Fiscale validation"""
```

### Running Tests

```bash
# Run full test suite
pytest tests/test_annual_subscriptions.py -v

# Run specific test category
pytest tests/test_annual_subscriptions.py::TestSubscriptionCreation -v

# Run with coverage
pytest tests/test_annual_subscriptions.py --cov=app.services --cov-report=html
```

### Test Data

Tests use realistic Italian tax data:

```python
# Business customer test data
business_customer = {
    "is_business": True,
    "partita_iva": "12345678903",  # Valid Luhn check
    "invoice_name": "Test SRL",
    "invoice_address": "Via Test 123",
    "invoice_cap": "00100",
    "invoice_city": "Roma",
    "invoice_province": "RM",
    "sdi_code": "ABCDEFG",
    "pec_email": "test@pec.it"
}

# Individual customer test data
individual_customer = {
    "is_business": False,
    "codice_fiscale": "RSSMRA80A01H501U",  # Valid format
    "invoice_name": "Mario Rossi",
    "invoice_address": "Via Milano 456",
    "invoice_cap": "20100",
    "invoice_city": "Milano",
    "invoice_province": "MI"
}
```

## Error Handling

### Common Validation Errors

```json
{
  "detail": "Dati non validi: Partita IVA non valida, Codice destinatario SDI o email PEC richiesti per fattura elettronica"
}
```

### Business Logic Errors

```json
{
  "detail": "User already has an active subscription"
}
```

### Payment Errors

```json
{
  "detail": "Errore di pagamento: Your card was declined."
}
```

### System Errors

```json
{
  "detail": "Errore interno del sistema"
}
```

## Monitoring and Analytics

### Key Metrics

Track the following metrics for Italian subscriptions:

```python
# Subscription metrics
- Total active subscriptions
- Monthly vs Annual distribution
- Churn rate by plan type
- Upgrade/downgrade frequency
- Average revenue per user (ARPU)

# Financial metrics
- Monthly Recurring Revenue (MRR)
- Annual Recurring Revenue (ARR)
- Customer Lifetime Value (CLV)
- Revenue per plan type

# Italian market specific
- B2B vs B2C distribution
- Electronic invoice success rate
- Tax validation error rates
- Regional distribution
```

### Performance Monitoring

```python
# Response time targets
- Subscription creation: <5 seconds
- Plan changes: <3 seconds
- Invoice generation: <2 seconds
- PDF download: <1 second
- XML generation: <1 second

# Error rate targets
- Tax validation: <0.1% false negatives
- Payment processing: <1% failures
- Invoice generation: <0.1% failures
```

## Security Considerations

### Data Protection

- **PII Encryption**: Partita IVA and Codice Fiscale encrypted at rest
- **Access Control**: Role-based access to subscription data
- **Audit Logging**: All subscription changes logged
- **GDPR Compliance**: Right to export/delete customer data

### Payment Security

- **PCI Compliance**: No card data stored locally
- **Stripe Security**: All payments processed via Stripe
- **Token Security**: JWT tokens with short expiration
- **API Security**: Rate limiting and authentication required

### Italian Compliance

- **Tax Data**: Secure handling of Italian tax identifiers
- **Electronic Invoices**: Encrypted XML storage
- **Audit Trail**: Complete history of all transactions
- **Data Residency**: Consider EU data storage requirements

## Troubleshooting

### Common Issues

#### Subscription Creation Fails

```bash
# Check user authentication
curl -X GET "$API_BASE/auth/me" -H "Authorization: Bearer $TOKEN"

# Validate customer data
curl -X POST "$API_BASE/billing/italian-subscriptions/validate-partita-iva" \
  -d "12345678903"

# Check Stripe payment method
stripe payment_methods retrieve pm_1234567890
```

#### Plan Change Fails

```bash
# Check subscription status
curl -X GET "$API_BASE/billing/italian-subscriptions/current" \
  -H "Authorization: Bearer $TOKEN"

# Verify proration calculation
# Review subscription.current_period_start/end dates
# Check for pending invoices or failed payments
```

#### Invoice Generation Fails

```bash
# Check subscription invoice data
psql -c "SELECT * FROM subscriptions WHERE id = 'subscription-uuid';"

# Verify company configuration
echo $COMPANY_PARTITA_IVA
echo $COMPANY_CODICE_FISCALE

# Test PDF generation
python -c "from reportlab.pdfgen import canvas; print('ReportLab working')"
```

#### Electronic Invoice Issues

```bash
# Validate XML structure
xmllint --schema fattura_pa_v1.2.xsd fattura.xml

# Check SDI requirements
# - Verify customer has Partita IVA
# - Confirm SDI code or PEC email present
# - Validate XML against Italian schema
```

### Performance Issues

#### Slow Subscription Creation

```python
# Common causes:
1. Stripe API latency - Check Stripe status
2. Database connection pool exhaustion
3. Tax validation API timeouts
4. Email service delays

# Solutions:
- Implement async processing
- Add connection pooling
- Cache tax validation results
- Use background jobs for emails
```

#### Invoice Generation Timeouts

```python
# Common causes:
1. Large PDF generation
2. Complex XML structure
3. Database query performance
4. File system I/O

# Solutions:
- Optimize PDF generation
- Cache generated invoices
- Add database indexes
- Use async file operations
```

## Migration Guide

### From Existing Payment System

If migrating from an existing payment system:

1. **Data Migration**: Export existing customer and subscription data
2. **Stripe Setup**: Create products and prices in Stripe
3. **Customer Migration**: Create Stripe customers for existing users
4. **Subscription Transfer**: Recreate subscriptions in new system
5. **Invoice History**: Import historical invoices if needed

### Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Stripe products and prices created
- [ ] Tax rates configured in Stripe
- [ ] Company tax information set
- [ ] Email templates configured
- [ ] Monitoring and alerts set up
- [ ] Test subscriptions verified
- [ ] Electronic invoice testing completed
- [ ] Production Stripe webhook configured

## Future Enhancements

### Planned Features

1. **Multi-Currency Support**: Support for other EU markets
2. **Advanced Reporting**: Detailed financial analytics dashboard
3. **Automated Dunning**: Failed payment recovery workflows
4. **Customer Portal**: Self-service subscription management
5. **Mobile API**: Native mobile app support
6. **Advanced Proration**: More flexible proration rules
7. **Bulk Operations**: Batch subscription management
8. **Integration APIs**: Third-party accounting system integration

### Italian Market Expansions

1. **Additional Tax Regimes**: Support for regime forfettario
2. **Regional Variations**: Handle regional tax differences
3. **Professional Categories**: Specialized pricing for professionals
4. **Educational Discounts**: Student and academic pricing
5. **Government Customers**: Public sector compliance requirements

---

**Last Updated**: December 5, 2024  
**Version**: 1.0  
**Authors**: PratikoAI Development Team

For questions or support with Italian subscriptions, contact the development team or refer to the troubleshooting section above.