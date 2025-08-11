# GDPR Article 20 Data Export System

This document provides comprehensive documentation for PratikoAI's GDPR Article 20 "Right to data portability" compliance system, specifically designed for Italian users with full privacy protection and regulatory compliance.

## Overview

The GDPR Data Export System enables Italian users to export their complete personal data in machine-readable formats (JSON and CSV), with comprehensive privacy controls, security measures, and full compliance with Italian data protection laws.

### Key Features

- **Complete Data Export**: All user data including queries, documents, subscriptions, and usage history
- **Italian Compliance**: Full support for Codice Fiscale, Partita IVA, and fattura elettronica
- **Multiple Formats**: JSON and CSV exports with Italian formatting and Excel compatibility
- **Privacy Protection**: Advanced anonymization options and PII masking
- **Secure Delivery**: Encrypted storage, rate limiting, and automatic expiry
- **Background Processing**: Asynchronous processing for large exports
- **Comprehensive Auditing**: Complete audit trail for compliance

## Architecture

### Core Components

```
GDPR Data Export System
├── Models (app/models/data_export.py)
│   ├── DataExportRequest - Export request tracking
│   ├── ExportAuditLog - Compliance audit logging
│   └── Supporting models for data collection
├── Services
│   ├── DataExportService - Core export logic
│   ├── ExportFileGenerator - Format generation (JSON/CSV/ZIP)
│   └── ExportProgressTracker - Real-time progress tracking
├── API (app/api/v1/data_export.py)
│   ├── Export management endpoints
│   ├── Progress tracking endpoints
│   └── Compliance information endpoints
├── Background Jobs (app/jobs/data_export_jobs.py)
│   ├── Celery task processing
│   ├── Automated cleanup
│   └── Health monitoring
└── Tests (tests/test_data_export.py)
    └── Comprehensive TDD test suite (1,500+ lines)
```

### Technology Stack

- **FastAPI**: REST API with comprehensive validation
- **SQLAlchemy 2.0**: Async database operations
- **Celery**: Background job processing
- **Redis**: Caching and job queuing
- **AWS S3**: Secure file storage with encryption
- **ReportLab**: PDF generation
- **Italian Compliance**: Custom formatting and validation

## Legal Compliance

### GDPR Article 20 Implementation

**Legal Basis**: "The data subject shall have the right to receive the personal data concerning him or her, which he or she has provided to a controller, in a structured, commonly used and machine-readable format."

**Italian Implementation**:
- Full compliance with Codice Privacy (D.Lgs. 196/2003)
- Integration with Italian tax data regulations
- Electronic invoice (fattura elettronica) handling
- Regional data protection requirements

### Data Controller Information

```yaml
Data Controller: PratikoAI SRL
Address: Via dell'Innovazione 123, 00100 Roma, IT
Email: privacy@pratikoai.com
PEC: privacy@pec.pratikoai.it
DPO: dpo@pratikoai.com
Jurisdiction: Italy
```

## Quick Start

### Environment Setup

```bash
# Required environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/pratikoai"
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="redis://localhost:6379/0"
export AWS_ACCESS_KEY_ID="your-aws-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret"
export EXPORT_S3_BUCKET="pratikoai-exports"

# Optional settings
export EXPORT_RETENTION_HOURS=24
export MAX_EXPORTS_PER_DAY=5
export MAX_DOWNLOAD_COUNT=10
```

### Database Setup

```bash
# Run migrations to create export tables
uv run alembic upgrade head

# Tables created:
# - data_export_requests
# - export_audit_logs  
# - query_history
# - document_analysis
# - tax_calculations
# - faq_interactions
# - knowledge_base_searches
# - electronic_invoices
```

### Background Worker Setup

```bash
# Start Celery worker for export processing
celery -A app.jobs.data_export_jobs worker --loglevel=info --queues=exports,maintenance,monitoring

# Start Celery beat for scheduled tasks
celery -A app.jobs.data_export_jobs beat --loglevel=info

# Monitor Celery with Flower (optional)
celery -A app.jobs.data_export_jobs flower
```

## API Usage

### Authentication

All export endpoints require user authentication:

```bash
# Login to get access token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token in subsequent requests
export ACCESS_TOKEN="eyJ0eXAiOiJKV1Q..."
```

### Request Data Export

```bash
curl -X POST "http://localhost:8000/api/v1/gdpr/data-export/request" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "both",
    "privacy_level": "full",
    "include_sensitive": true,
    "anonymize_pii": false,
    "date_from": "2024-01-01",
    "date_to": "2024-12-31",
    "include_fatture": true,
    "include_f24": true,
    "mask_codice_fiscale": false,
    "include_profile": true,
    "include_queries": true,
    "include_documents": true,
    "include_calculations": true,
    "include_subscriptions": true,
    "include_invoices": true,
    "include_usage_stats": true,
    "include_faq_interactions": true,
    "include_knowledge_searches": true
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "format": "both",
  "privacy_level": "full",
  "requested_at": "2024-12-05T15:30:00",
  "expires_at": "2024-12-06T15:30:00",
  "file_size_mb": null,
  "download_count": 0,
  "max_downloads": 10,
  "is_expired": false,
  "is_downloadable": false,
  "processing_time_seconds": null,
  "time_until_expiry_hours": 24.0,
  "error_message": null,
  "data_categories": {
    "profile": true,
    "queries": true,
    "documents": true,
    "calculations": true,
    "subscriptions": true,
    "invoices": true,
    "usage_stats": true,
    "faq_interactions": true,
    "knowledge_searches": true
  },
  "italian_options": {
    "include_fatture": true,
    "include_f24": true,
    "include_dichiarazioni": true,
    "mask_codice_fiscale": false
  },
  "privacy_options": {
    "include_sensitive": true,
    "anonymize_pii": false
  }
}
```

### Check Export Status

```bash
curl -X GET "http://localhost:8000/api/v1/gdpr/data-export/550e8400-e29b-41d4-a716-446655440000/status" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Monitor Export Progress

```bash
curl -X GET "http://localhost:8000/api/v1/gdpr/data-export/550e8400-e29b-41d4-a716-446655440000/progress" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Response:
```json
{
  "export_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": {
    "step": "Generazione file export",
    "current": 3,
    "total": 8,
    "percentage": 37.5,
    "updated_at": "2024-12-05T15:35:00"
  },
  "estimated_completion": "2024-12-05T15:40:00"
}
```

### Download Completed Export

```bash
curl -X GET "http://localhost:8000/api/v1/gdpr/data-export/550e8400-e29b-41d4-a716-446655440000/download" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -L -o "export_dati.zip"
```

### Get Export History

```bash
curl -X GET "http://localhost:8000/api/v1/gdpr/data-export/history?limit=10&offset=0" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Data Categories

### Core Data Types

#### 1. User Profile
- Email address (encrypted)
- Full name (encrypted)
- Registration date
- Account status
- Language and timezone preferences
- Italian tax identifiers (Codice Fiscale, Partita IVA)

#### 2. Query History
- All questions asked to the AI system
- Response metadata (cached status, response time, token usage)
- Cost information
- Italian content classification
- Session tracking

#### 3. Document Analysis
- File metadata (name, type, size, upload date)
- Analysis type and results summary
- Processing time and confidence scores
- Italian document categories (fattura, ricevuta, F24, etc.)
- **Note**: No actual document content is included for privacy

#### 4. Tax Calculations
- All tax calculations performed (IVA, IRPEF, IMU, etc.)
- Input parameters and results
- Regional and municipal information
- Tax year associations

#### 5. Subscription History
- Plan details and billing history
- Subscription status changes
- Italian invoice information
- Business customer data (Partita IVA)

#### 6. Invoice Data
- Invoice numbers and dates
- Amount breakdowns (imponibile, IVA, totale)
- Payment status and dates
- Stripe integration details

#### 7. Usage Statistics
- Aggregate usage metrics
- Performance statistics
- Cache hit rates
- Cost analysis

#### 8. FAQ Interactions
- FAQ items viewed
- User ratings and feedback
- Time spent on content
- Italian content classification

#### 9. Knowledge Base Searches
- Search queries performed
- Results clicked and positions
- Search filters used
- Regulatory content interactions

### Italian-Specific Data

#### Electronic Invoices (Fatture Elettroniche)
- Complete XML content for SDI compliance
- Transmission IDs and status
- Acceptance/rejection details
- **Only for business customers with Partita IVA**

#### F24 Forms
- Tax form metadata and processing results
- Payment details and status
- **Highly sensitive fiscal data**

#### Tax Declarations
- Declaration metadata and key information
- Processing timestamps and status
- **Extremely sensitive data with additional protection**

## Export Formats

### JSON Export

**Structure**:
```json
{
  "export_info": {
    "generated_at": "05/12/2024 15:30:00",
    "format_version": "1.2",
    "export_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "date_range": {
      "from": "01/01/2024",
      "to": "31/12/2024"
    },
    "privacy_level": "full",
    "italian_compliance": true,
    "gdpr_article": "Article 20 - Right to data portability"
  },
  "profile": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "mario.rossi@example.it",
    "full_name": "Mario Rossi",
    "created_at": "15/01/2024 10:30:00",
    "language": "it_IT",
    "timezone": "Europe/Rome",
    "account_status": "active",
    "business_info": {
      "is_business": true,
      "partita_iva": "12345678903"
    },
    "codice_fiscale": "RSSMRA80A01H501U"
  },
  "queries": [
    {
      "id": "query-uuid-1",
      "timestamp": "01/03/2024 10:00:00",
      "query": "Come calcolare l'IVA al 22%?",
      "response_cached": false,
      "response_time_ms": 1200,
      "tokens_used": 150,
      "cost_cents": 5,
      "model_used": "gpt-4o-mini",
      "query_type": "tax_calculation",
      "italian_content": true
    }
  ],
  "compliance_info": {
    "gdpr_compliance": {
      "legal_basis": "GDPR Article 20 - Right to data portability",
      "data_controller": {
        "name": "PratikoAI SRL",
        "address": "Via dell'Innovazione 123, 00100 Roma, IT",
        "contact": "privacy@pratikoai.com",
        "country": "IT"
      }
    }
  }
}
```

**Italian Formatting**:
- Dates: DD/MM/YYYY format
- Decimals: Comma separator (€ 1.234,56)
- Currency: Euro symbol with Italian formatting
- UTF-8 encoding without BOM

### CSV Export

**Multiple Files Generated**:
- `profilo.csv` - User profile data
- `domande.csv` - Query history
- `documenti.csv` - Document metadata
- `calcoli_fiscali.csv` - Tax calculations
- `abbonamenti.csv` - Subscription history
- `fatture.csv` - Invoice data
- `fatture_elettroniche.csv` - Electronic invoices
- `interazioni_faq.csv` - FAQ interactions
- `ricerche_conoscenza.csv` - Knowledge searches
- `statistiche_uso.csv` - Usage statistics

**Italian CSV Formatting**:
- Delimiter: Semicolon (;) for Italian Excel compatibility
- Encoding: UTF-8 with BOM for Excel compatibility
- Headers: Italian language
- Dates: DD/MM/YYYY format
- Decimals: Comma separator for amounts

**Example CSV (domande.csv)**:
```csv
Data;Ora;Domanda;Tipo Domanda;Tempo Risposta (ms);Token Utilizzati;Costo (€);Da Cache;Modello AI;Contenuto Italiano
01/03/2024;10:00:00;Come calcolare l'IVA al 22%?;Calcolo Fiscale;1200;150;0,05;No;gpt-4o-mini;Sì
02/03/2024;14:30:00;Regime forfettario partita iva;Generale;800;120;0,04;Sì;gpt-4o-mini;Sì
```

### ZIP Archive

**Automatic Creation**:
- Created when multiple files present OR total size > 10MB
- Compressed using ZIP_DEFLATED for optimal size
- Contains all export files plus manifest

**Structure**:
```
export_dati_USER_ID_YYYYMMDD_HHMMSS.zip
├── LEGGIMI.txt (Italian manifest)
├── dati_completi.json (if JSON format requested)
├── profilo.csv
├── domande.csv
├── documenti.csv
├── calcoli_fiscali.csv
├── abbonamenti.csv
├── fatture.csv
├── fatture_elettroniche.csv
├── interazioni_faq.csv
├── ricerche_conoscenza.csv
└── statistiche_uso.csv
```

## Privacy Protection

### Privacy Levels

#### Full Data Export
- **Description**: Complete export with all available data
- **Use Case**: Complete data backup or migration
- **Risk Level**: High - includes all sensitive information
- **Includes**: All data types without modification

#### Anonymized Export
- **Description**: PII masked for privacy protection
- **Use Case**: Data analysis while protecting identity
- **Risk Level**: Medium - reduced identifiability
- **Masking Applied**:
  - Email: `m***o@example.com` 
  - Names: `***`
  - Codice Fiscale: `************501U` (last 4 chars visible)
  - Partita IVA: `***78903` (last 5 chars visible)
  - Query text: Truncated to 50 characters

#### Minimal Export
- **Description**: Essential data only, excludes sensitive information
- **Use Case**: Basic data portability with minimal privacy risk
- **Risk Level**: Low - non-sensitive data only
- **Excludes**: All PII, financial data, and sensitive identifiers

### Data Exclusions

**Never Exported**:
- Passwords or password hashes
- JWT tokens or refresh tokens
- API keys or secret keys
- Session tokens
- Private encryption keys
- Other users' data from shared resources

**Conditionally Excluded**:
- Document content (only metadata exported)
- Credit card numbers (never stored anyway)
- Bank account details (never stored anyway)
- Social security equivalents beyond Codice Fiscale

### Codice Fiscale Protection

**Standard Format**: `RSSMRA80A01H501U`

**Masking Options**:
- **Full**: `RSSMRA80A01H501U` (complete code)
- **Masked**: `************501U` (last 4 characters visible)
- **Excluded**: Not included in export

**Legal Considerations**:
- Codice Fiscale is sensitive personal data under Italian law
- Users can choose masking level based on their needs
- Business customers may need full codes for accounting

## Security Measures

### Rate Limiting

**Export Requests**:
- Maximum 5 exports per user per 24-hour period
- Prevents abuse and system overload
- Automatic reset after 24 hours

**Download Limits**:
- Maximum 10 downloads per export
- Prevents unauthorized sharing
- Each download tracked with IP address

### Access Control

**Authentication Required**:
- Valid JWT token required for all operations
- User can only access their own exports
- No administrative override capabilities

**Authorization Checks**:
- Export ownership verified on every access
- Download permissions validated
- Audit trail for all access attempts

### Encryption and Storage

**Data at Rest**:
- All export files encrypted using AWS S3 server-side encryption (AES-256)
- Database encryption for sensitive fields
- No plaintext storage of export files

**Data in Transit**:
- HTTPS/TLS 1.3 for all API communications
- Signed URLs for secure download links
- VPN access for administrative functions

**Key Management**:
- AWS KMS for encryption key management
- Regular key rotation
- Separation of encryption and data access

### Audit Logging

**Complete Audit Trail**:
```sql
-- Example audit log entries
INSERT INTO export_audit_logs (
  export_request_id,
  user_id,
  activity_type,
  activity_timestamp,
  ip_address,
  user_agent,
  activity_data
) VALUES (
  '550e8400-e29b-41d4-a716-446655440000',
  '123e4567-e89b-12d3-a456-426614174000', 
  'downloaded',
  '2024-12-05 15:40:00',
  '192.168.1.100',
  'Mozilla/5.0...',
  '{"download_count": 1, "file_size_mb": 2.5}'
);
```

**Logged Activities**:
- Export request creation
- Processing start/completion
- Download attempts (successful and failed)
- Status changes
- Security events (suspicious activity)

### Automatic Cleanup

**24-Hour Expiry**:
- All exports automatically expire after 24 hours
- Files removed from storage
- Download links become invalid
- Database status updated to 'expired'

**Daily Cleanup Job**:
```python
# Runs daily at 2 AM
@celery_app.task(name="cleanup_expired_exports")
def cleanup_expired_exports():
    # Remove expired files from S3
    # Update database status
    # Generate cleanup report
```

## Italian Market Compliance

### Regulatory Framework

**Primary Legislation**:
- GDPR (Regolamento UE 2016/679)
- Codice Privacy (D.Lgs. 196/2003 e successive modifiche)
- CAD - Codice dell'Amministrazione Digitale (D.Lgs. 82/2005)

**Tax Data Specific**:
- Decreto Ministeriale del 23 gennaio 2004 (fatturazione elettronica)
- Provvedimento del Garante Privacy del 26 ottobre 2016
- Circolare Agenzia delle Entrate n. 18/E del 2019

### Data Localization

**Storage Requirements**:
- EU data residency compliance
- AWS Frankfurt region for Italian user data
- No data transfer outside EU without adequate protection

**Processing Location**:
- All processing within EU boundaries
- Italian language support throughout system
- Local time zone handling (Europe/Rome)

### Electronic Invoice Integration

**SDI Compliance**:
- XML format validation against Italian schema
- Proper transmission ID handling
- Status tracking (sent, accepted, rejected)

**Business Customer Requirements**:
- Partita IVA validation using Luhn algorithm
- SDI destination code or PEC email required
- Complete XML content available for export

**Example Electronic Invoice Export**:
```json
{
  "fatture_elettroniche": [
    {
      "id": "fe-uuid-1",
      "invoice_number": "2024/0001", 
      "invoice_date": "01/02/2024",
      "xml_hash": "sha256:abc123...",
      "sdi_transmission_id": "IT12345678901_00001",
      "sdi_status": "accepted",
      "created_at": "01/02/2024 10:00:00",
      "transmitted_at": "01/02/2024 10:15:00",
      "accepted_at": "01/02/2024 11:30:00",
      "xml_content": "<p:FatturaElettronica>...</p:FatturaElettronica>"
    }
  ]
}
```

### Regional Data Protection

**Garante per la Protezione dei Dati Personali**:
- Registration and compliance reporting
- Privacy impact assessments
- Breach notification procedures

**Regional Variations**:
- Sicily: Additional regional tax data requirements
- Trentino-Alto Adige: Multilingual support considerations
- Vatican City: Special jurisdiction handling

## Background Processing

### Celery Task Architecture

**Task Queues**:
- `exports`: High-priority export processing
- `maintenance`: Daily cleanup and maintenance
- `monitoring`: Health checks and metrics

**Task Configuration**:
```python
# Export processing task
@celery_app.task(bind=True, name="process_export_request")
def process_export_request(self, export_id: str):
    # Rate limit: 10 exports per minute
    # Time limit: 1 hour timeout
    # Soft limit: 55 minutes
    # Retry: Up to 2 retries with exponential backoff
```

### Progress Tracking

**Real-time Updates**:
```python
# Progress steps tracked
steps = [
    "Inizializzazione export",      # 1/8 - 12.5%
    "Raccolta dati utente",         # 2/8 - 25.0%
    "Generazione file export",      # 3/8 - 37.5%
    "Creazione archivio",           # 4/8 - 50.0%
    "Caricamento sicuro",           # 5/8 - 62.5%
    "Finalizzazione",               # 6/8 - 75.0%
    "Invio notifica",              # 7/8 - 87.5%
    "Export completato"            # 8/8 - 100%
]
```

**Redis Storage**:
```json
{
  "step": "Generazione file export",
  "current": 3,
  "total": 8,
  "percentage": 37.5,
  "updated_at": "2024-12-05T15:35:00"
}
```

### Scheduled Tasks

**Daily Cleanup (2:00 AM)**:
- Remove expired exports from storage
- Update database status
- Generate cleanup reports
- Free storage space

**Health Monitoring (Every 15 minutes)**:
- Check for stuck exports (>2 hours processing)
- Monitor system resource usage
- Validate queue health
- Alert on performance issues

**Metrics Collection (Hourly)**:
- Export volume and success rates
- Processing time statistics
- Storage usage metrics
- User activity patterns

### Error Handling

**Retry Logic**:
```python
# Automatic retry for transient failures
if self.request.retries < 2:
    raise self.retry(
        countdown=60 * (2 ** self.request.retries),  # Exponential backoff
        max_retries=2
    )
```

**Failure Classification**:
- **Retryable**: Network timeouts, temporary service unavailability
- **Non-retryable**: Invalid user data, permission errors
- **Critical**: System errors requiring immediate attention

## Monitoring and Metrics

### Performance Metrics

**Export Processing**:
- Average processing time: Target <5 minutes
- Success rate: Target >98%
- Queue processing rate: Target <1 minute wait
- File generation speed: Target >1MB/minute

**System Resources**:
- CPU usage during export processing
- Memory consumption patterns
- Disk I/O for large exports
- Network bandwidth for file uploads

**User Experience**:
- Time from request to completion
- Download success rates
- User satisfaction (if feedback implemented)
- Support ticket correlation

### Health Checks

**Automated Monitoring**:
```python
# Health check results
{
  "timestamp": "2024-12-05T15:30:00",
  "stuck_exports": [],
  "stuck_count": 0,
  "average_processing_time": 287.5,  # seconds
  "max_processing_time": 1200,
  "exports_last_24h": 45,
  "status_breakdown": {
    "completed": 38,
    "failed": 2,
    "processing": 3,
    "pending": 2
  },
  "system_healthy": true
}
```

**Alert Thresholds**:
- Stuck exports: >0 (immediate alert)
- Average processing time: >30 minutes
- Success rate: <95%
- Queue backlog: >50 pending exports

### Compliance Monitoring

**GDPR Compliance Metrics**:
- Export request response time (must be <1 month)
- Data completeness verification
- Privacy setting usage patterns
- Audit log completeness

**Italian Specific Monitoring**:
- Electronic invoice export success rate
- Codice Fiscale masking usage
- Business vs individual customer patterns
- Regional data distribution

## Troubleshooting

### Common Issues

#### Export Request Fails with Rate Limit Error

**Error**: `429 Too Many Requests - Massimo 5 export al giorno raggiunti`

**Solution**:
```bash
# Check current rate limit status
curl -X GET "http://localhost:8000/api/v1/gdpr/data-export/history" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Wait for 24-hour reset or contact support for legitimate need
```

#### Export Stuck in Processing Status

**Error**: Export shows "processing" for >2 hours

**Investigation**:
```bash
# Check Celery worker status
celery -A app.jobs.data_export_jobs inspect active

# Check Redis queue
redis-cli llen export_queue

# Check system health
curl -X GET "http://localhost:8000/api/v1/gdpr/data-export/compliance/info"
```

**Resolution**:
- Restart Celery workers if needed
- Check system resources (CPU, memory, disk)
- Review error logs for specific failures
- Use retry endpoint if available

#### Download Link Expired

**Error**: `410 Gone - Export scaduto il 05/12/2024 alle 15:30`

**Solution**:
```bash
# Check if one-time extension is available
curl -X PUT "http://localhost:8000/api/v1/gdpr/data-export/EXPORT_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"extend_expiry": true}'

# If not available, create new export request
```

#### Large Export Fails with Timeout

**Error**: Export fails for users with extensive data

**Investigation**:
- Check file size limits in configuration
- Review Celery task timeout settings
- Verify S3 upload permissions and limits

**Solution**:
```python
# Adjust Celery configuration
CELERY_TASK_TIME_LIMIT = 7200  # 2 hours
CELERY_TASK_SOFT_TIME_LIMIT = 6600  # 1h 50m

# Implement chunked processing for very large exports
```

#### CSV Files Not Opening Correctly in Excel

**Issue**: Italian CSV files display incorrectly in Excel

**Cause**: Encoding or delimiter issues

**Solution**:
- Verify UTF-8 with BOM encoding
- Confirm semicolon delimiter usage
- Check Italian number formatting (comma decimal separator)

**Excel Import Settings**:
```
File Origin: UTF-8
Delimiter: Semicolon (;)
Text Qualifier: " (double quote)
```

### Performance Optimization

#### Slow Export Processing

**Optimization Strategies**:

1. **Database Query Optimization**:
```python
# Use selective loading
stmt = select(QueryHistory).options(
    selectinload(QueryHistory.user)
).where(QueryHistory.user_id == user_id)

# Add appropriate indexes
CREATE INDEX idx_query_history_user_timestamp 
ON query_history(user_id, timestamp DESC);
```

2. **Parallel Processing**:
```python
# Process data categories in parallel
async def collect_user_data_parallel(self, user_id, export_request):
    tasks = [
        self._collect_profile_data(user_id, export_request),
        self._collect_query_history(user_id, export_request),
        self._collect_document_metadata(user_id, export_request)
    ]
    results = await asyncio.gather(*tasks)
    return combine_results(results)
```

3. **Memory Management**:
```python
# Stream large datasets
async def stream_query_history(self, user_id):
    async for batch in self.db.stream(
        select(QueryHistory)
        .where(QueryHistory.user_id == user_id)
        .yield_per(1000)
    ):
        yield batch
```

#### Storage Optimization

**S3 Configuration**:
```python
# Use intelligent tiering
s3_client.put_object(
    Bucket=bucket,
    Key=key,
    Body=content,
    StorageClass='INTELLIGENT_TIERING',
    ServerSideEncryption='AES256'
)

# Implement lifecycle policies
lifecycle_config = {
    'Rules': [{
        'Status': 'Enabled',
        'Transitions': [{
            'Days': 1,
            'StorageClass': 'GLACIER'
        }],
        'Expiration': {'Days': 30}
    }]
}
```

### Security Incident Response

#### Suspected Data Breach

**Immediate Actions**:
1. Isolate affected systems
2. Preserve audit logs
3. Identify scope of potential breach
4. Notify security team and DPO

**Investigation Steps**:
```sql
-- Check for unusual export activity
SELECT 
  u.email,
  er.requested_at,
  er.download_count,
  al.ip_address,
  al.activity_type
FROM data_export_requests er
JOIN users u ON er.user_id = u.id
LEFT JOIN export_audit_logs al ON er.id = al.export_request_id
WHERE er.requested_at > NOW() - INTERVAL '7 days'
  AND (er.download_count > 5 OR al.suspicious_activity = true)
ORDER BY er.requested_at DESC;
```

**Notification Requirements**:
- GDPR: 72 hours to supervisory authority
- Italian law: Immediate notification to Garante
- Users: Without undue delay

#### Unauthorized Access Attempt

**Detection**:
- Multiple failed authentication attempts
- Access from unusual IP addresses
- Attempts to access other users' exports

**Response**:
```python
# Automatic account lockout
if failed_attempts > 5:
    user.locked_until = datetime.utcnow() + timedelta(hours=1)
    
# Enhanced monitoring
audit_log.suspicious_activity = True
audit_log.security_notes = "Multiple failed access attempts"
```

## Deployment Guide

### Production Configuration

#### Environment Variables

```bash
# Database
DATABASE_URL="postgresql://user:password@db.example.com:5432/pratikoai"
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis
REDIS_URL="redis://redis.example.com:6379/0"
REDIS_PASSWORD="secure-password"

# Celery
CELERY_BROKER_URL="redis://redis.example.com:6379/1"
CELERY_RESULT_BACKEND="redis://redis.example.com:6379/2"
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000

# AWS S3
AWS_ACCESS_KEY_ID="AKIA..."
AWS_SECRET_ACCESS_KEY="..."
AWS_REGION="eu-central-1"
EXPORT_S3_BUCKET="pratikoai-exports-prod"

# Security
JWT_SECRET_KEY="very-secure-secret-key"
ENCRYPTION_KEY="32-byte-encryption-key"

# Export Configuration
MAX_EXPORTS_PER_DAY=5
MAX_DOWNLOAD_COUNT=10
EXPORT_RETENTION_HOURS=24
MAX_EXPORT_FILE_SIZE_MB=100

# Monitoring
SENTRY_DSN="https://..."
LOG_LEVEL="INFO"
```

#### Docker Configuration

```dockerfile
# Dockerfile for export worker
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run Celery worker
CMD ["celery", "-A", "app.jobs.data_export_jobs", "worker", 
     "--loglevel=info", "--concurrency=4", 
     "--queues=exports,maintenance,monitoring"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/pratikoai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  export-worker:
    build: .
    command: celery -A app.jobs.data_export_jobs worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/pratikoai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  export-beat:
    build: .
    command: celery -A app.jobs.data_export_jobs beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/pratikoai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=pratikoai
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
```

### Scaling Considerations

#### Horizontal Scaling

**Multiple Workers**:
```bash
# Scale Celery workers
celery -A app.jobs.data_export_jobs worker --concurrency=8 --hostname=worker1@%h
celery -A app.jobs.data_export_jobs worker --concurrency=8 --hostname=worker2@%h
celery -A app.jobs.data_export_jobs worker --concurrency=8 --hostname=worker3@%h
```

**Load Balancing**:
- Use Redis Cluster for queue distribution
- Implement consistent hashing for user-based routing
- Monitor queue sizes across workers

#### Database Scaling

**Read Replicas**:
```python
# Use read replica for export data collection
@read_replica
async def collect_user_data(self, user_id):
    # Read-only operations on replica
    pass

# Use primary for status updates
@primary_db
async def update_export_status(self, export_id, status):
    # Write operations on primary
    pass
```

**Connection Pooling**:
```python
# Optimize connection pools
engine = create_async_engine(
    DATABASE_URL,
    pool_size=30,
    max_overflow=50,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Monitoring Setup

#### Prometheus Metrics

```python
# Custom metrics for export system
from prometheus_client import Counter, Histogram, Gauge

export_requests_total = Counter(
    'export_requests_total',
    'Total export requests',
    ['format', 'privacy_level']
)

export_processing_duration = Histogram(
    'export_processing_duration_seconds',
    'Export processing time',
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]
)

active_exports = Gauge(
    'active_exports',
    'Currently processing exports'
)
```

#### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "GDPR Data Export System",
    "panels": [
      {
        "title": "Export Requests Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(export_requests_total[5m])",
            "legendFormat": "{{format}} - {{privacy_level}}"
          }
        ]
      },
      {
        "title": "Processing Time Distribution",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(export_processing_duration_seconds_bucket[5m])"
          }
        ]
      },
      {
        "title": "Success Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(export_requests_total{status=\"completed\"}[1h]) / rate(export_requests_total[1h]) * 100"
          }
        ]
      }
    ]
  }
}
```

## Future Enhancements

### Planned Features

#### Enhanced Privacy Controls
- Granular data category selection
- Time-based data retention policies
- Advanced anonymization techniques
- Privacy-preserving analytics

#### Additional Export Formats
- PDF reports with Italian formatting
- XML format for structured data exchange
- ODS (OpenDocument Spreadsheet) for LibreOffice
- Custom format templates

#### Advanced Italian Compliance
- Integration with Sistema Tessera Sanitaria
- INPS data handling
- Regional tax authority integration
- Automated compliance reporting

#### API Enhancements
- GraphQL endpoint for flexible data queries
- Webhook notifications for export completion
- Bulk export operations for organizations
- Advanced filtering and search capabilities

### Technical Improvements

#### Performance Optimizations
- Incremental export updates
- Delta exports (only changed data)
- Parallel processing optimization
- Advanced caching strategies

#### Security Enhancements
- Zero-knowledge export encryption
- Client-side decryption options
- Advanced threat detection
- Biometric authentication integration

#### Monitoring and Analytics
- Predictive export time estimation
- User behavior analytics
- Compliance risk assessment
- Automated privacy impact assessment

---

**Last Updated**: December 5, 2024  
**Version**: 1.0  
**Authors**: PratikoAI Development Team

For questions, support, or compliance inquiries regarding the GDPR Data Export System, contact:
- **Technical Support**: support@pratikoai.com
- **Privacy Officer**: privacy@pratikoai.com  
- **Data Protection Officer**: dpo@pratikoai.com