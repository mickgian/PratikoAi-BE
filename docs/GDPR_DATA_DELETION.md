# GDPR Data Deletion System - PratikoAI

## Overview

PratikoAI implements a comprehensive GDPR Article 17 "Right to be forgotten" compliance system that ensures complete and irreversible deletion of user data within the mandatory 30-day deadline. The system handles actual data deletion (not just anonymization) across all systems including PostgreSQL, Redis, application logs, backups, and third-party services.

## Features

- **30-Day Deadline Compliance**: Automatic tracking and execution of deletion requests within GDPR's 30-day requirement
- **Complete Multi-System Deletion**: Removes data from PostgreSQL, Redis, logs, backups, and third-party services (Stripe)
- **Cascading Deletion**: Automatically identifies and deletes all related records across database tables
- **Audit Trail Preservation**: Maintains anonymized audit records for compliance documentation
- **Deletion Verification**: Comprehensive verification that all data has been completely removed
- **Compliance Certificates**: Generates legally-compliant deletion certificates with digital signatures
- **Automatic Scheduling**: Background jobs automatically process overdue deletion requests
- **Admin Management**: Full admin interface for monitoring and managing deletion requests
- **Compliance Reporting**: Detailed reports for GDPR compliance audits

## Architecture

### Core Components

1. **GDPRDeletionService**: Main service orchestrating deletion workflows
2. **UserDataDeletor**: Comprehensive data removal across all systems
3. **DeletionVerifier**: Verification and certificate generation
4. **GDPRScheduler**: Automated scheduling and monitoring
5. **GDPR API**: User and admin interfaces for deletion requests

### Data Flow

```
User Request → GDPRDeletionService → UserDataDeletor → DeletionVerifier → Certificate
     ↓                    ↓                ↓               ↓              ↓
Deadline Tracking → Multi-System → Comprehensive → Compliance → Legal
   (30 days)        Deletion      Verification    Certificate  Documentation
```

### Database Schema

#### GDPR Deletion Requests
- **gdpr_deletion_requests**: Main deletion request tracking
- **gdpr_deletion_audit_log**: Audit trail with anonymized records
- **gdpr_deletion_certificates**: Compliance certificates

## Configuration

### Environment Variables

```bash
# Required for GDPR deletion system
DB_ENCRYPTION_MASTER_KEY=your_encryption_key
POSTGRES_URL=postgresql+asyncpg://user:pass@host:port/db

# Optional - Redis for cache deletion
REDIS_URL=redis://localhost:6379

# Optional - Stripe for payment data deletion
STRIPE_SECRET_KEY=sk_test_or_live_key

# Scheduler configuration
GDPR_DELETION_INTERVAL_HOURS=4
GDPR_MAX_BATCH_SIZE=50
GDPR_ALERT_THRESHOLD_HOURS=2
```

### Service Configuration

```python
# GDPR deletion job configuration
job_config = {
    "execution_interval_hours": 4,      # Run every 4 hours
    "max_batch_size": 50,              # Max deletions per batch
    "retry_failed_deletions": True,     # Retry failed attempts
    "max_retry_attempts": 3,           # Maximum retry attempts
    "alert_threshold_hours": 2,        # Alert when overdue by 2+ hours
    "critical_threshold_hours": 24     # Critical alert at 24+ hours
}
```

## Usage

### User-Initiated Deletion

#### API Request
```python
# Create deletion request
POST /api/v1/gdpr/deletion-request
{
    "reason": "I want to delete my account and all personal data",
    "priority": "normal"
}

# Check deletion status
GET /api/v1/gdpr/deletion-request/status

# Download deletion certificate
GET /api/v1/gdpr/deletion-certificate/{certificate_id}
```

#### Example Response
```json
{
    "request_id": "gdpr_del_a1b2c3d4e5f6",
    "user_id": 123,
    "status": "pending",
    "initiated_by_user": true,
    "reason": "I want to delete my account and all personal data",
    "priority": "normal",
    "request_timestamp": "2025-08-05T14:30:00Z",
    "deletion_deadline": "2025-09-04T14:30:00Z",
    "completed_at": null,
    "deletion_certificate_id": null
}
```

### Admin Management

#### List Deletion Requests
```python
# Get all deletion requests with filtering
GET /api/v1/gdpr/admin/deletion-requests?status=pending&overdue_only=true

# Create admin-initiated deletion
POST /api/v1/gdpr/admin/deletion-request
{
    "user_id": 456,
    "reason": "Account inactive for 2 years - automated cleanup",
    "priority": "low"
}

# Execute overdue deletions
POST /api/v1/gdpr/admin/execute-overdue

# Verify specific user deletion
POST /api/v1/gdpr/admin/verify-deletion/123
```

#### Compliance Reporting
```python
# Generate compliance report
GET /api/v1/gdpr/admin/compliance-report?days=30

# Get deletion metrics
GET /api/v1/gdpr/admin/metrics

# Check deadline compliance
GET /api/v1/gdpr/admin/deadline-compliance
```

### Programmatic Usage

#### Direct Service Usage
```python
from app.services.gdpr_deletion_service import GDPRDeletionService
from app.services.user_data_deletor import UserDataDeletor
from app.services.deletion_verifier import DeletionVerifier

# Initialize services
gdpr_service = GDPRDeletionService(db_session)
await gdpr_service.initialize()

# Create deletion request
deletion_request = await gdpr_service.create_deletion_request(
    user_id=123,
    initiated_by_user=True,
    reason="User requested account deletion"
)

# Execute deletion
deletion_results = await gdpr_service.execute_overdue_deletions()

# Verify deletion
verifier = DeletionVerifier(db_session)
verification_result = await verifier.verify_user_deletion(123)

# Generate certificate
certificate = await verifier.generate_deletion_certificate(verification_result)
```

## Deletion Process

### Step 1: Request Creation
- User or admin creates deletion request
- System calculates 30-day deadline
- Request stored with unique ID and tracking information

### Step 2: Data Identification
- System scans all tables for user references
- Identifies related records in:
  - users (main user record)
  - sessions (user sessions)
  - query_logs (user queries)
  - subscription_data (payment information)
  - gdpr_deletion_requests (deletion request record)

### Step 3: Multi-System Deletion
- **PostgreSQL Database**: Complete record deletion with cascading
- **Redis Cache**: Pattern-based key deletion for user data
- **Application Logs**: PII anonymization in log files
- **Backup Systems**: User data anonymization in backup files
- **Stripe Integration**: Customer record deletion from payment system

### Step 4: Verification
- Comprehensive scan to verify complete deletion
- Checks all systems for remaining user data
- Calculates verification score (must be 100% for GDPR compliance)
- Identifies any remaining data issues

### Step 5: Certificate Generation
- Generates legally-compliant deletion certificate
- Includes digital signature and verification details
- Stores certificate for audit purposes
- Provides downloadable certificate to user

## Scheduling and Automation

### Automated Execution

The system includes a scheduler that automatically processes overdue deletion requests:

```python
# Cron job configuration (every 4 hours)
0 */4 * * * cd /path/to/pratikoai && python -c "
import asyncio
from app.services.gdpr_scheduler import run_gdpr_deletion_job
result = asyncio.run(run_gdpr_deletion_job())
print(f'Processed {result[\"successful_deletions\"]} deletions')
"
```

### Monitoring and Alerts

The scheduler generates alerts for:
- **Overdue Requests**: Deletions past 30-day deadline
- **Approaching Deadlines**: Requests within 7 days of deadline
- **System Failures**: Failed deletion attempts
- **Compliance Issues**: GDPR compliance violations

### Job Status Tracking

```python
# Get scheduler status
GET /api/v1/gdpr/admin/scheduler-status
{
    "scheduler_status": "active",
    "last_execution": "2025-08-05T10:00:00Z",
    "next_execution": "2025-08-05T14:00:00Z",
    "recent_success_rate": 98.5,
    "active_alerts": 2,
    "alert_breakdown": {
        "low": 0,
        "medium": 1,
        "high": 1,
        "critical": 0
    }
}
```

## Compliance Features

### GDPR Article 17 Requirements

✅ **Complete Deletion**: All personal data is irreversibly deleted, not just anonymized  
✅ **30-Day Deadline**: Automatic execution within mandatory timeframe  
✅ **User Rights**: Easy-to-use interface for users to request deletion  
✅ **Comprehensive Scope**: Covers all systems where data is stored  
✅ **Audit Trail**: Maintains compliance documentation  
✅ **Verification**: Proves complete deletion occurred  
✅ **Certificates**: Legal documentation of compliance  

### Italian Data Protection Compliance

✅ **Codice Fiscale Protection**: Special handling of Italian tax IDs  
✅ **Financial Data**: Secure deletion of payment and subscription data  
✅ **Multi-language Support**: Italian language compliance documentation  
✅ **Local Regulations**: Compliance with Italian privacy authorities  

### Data Categories Deleted

- **Identity Data**: Names, addresses, phone numbers, email addresses
- **Financial Data**: Payment methods, transaction history, subscription data
- **Behavioral Data**: Query logs, session data, usage patterns
- **System Data**: User preferences, settings, authentication tokens
- **Italian-Specific Data**: Codice Fiscale (tax IDs), Italian addresses

## Migration and Setup

### Database Migration

```bash
# Apply GDPR deletion system migration
alembic upgrade head

# Verify tables created
psql -d pratikoai -c "\dt gdpr_*"
```

### Service Initialization

```python
# Initialize GDPR services
from app.services.gdpr_deletion_service import GDPRDeletionService
from app.services.gdpr_scheduler import get_gdpr_scheduler

# Start scheduler
scheduler = await get_gdpr_scheduler()
print("GDPR deletion scheduler initialized")
```

### API Integration

Add to main FastAPI application:

```python
from app.api.v1.gdpr import router as gdpr_router

app.include_router(gdpr_router, prefix="/api/v1")
```

## Testing

### Test Suite Execution

```bash
# Run comprehensive GDPR deletion tests
pytest tests/test_gdpr_data_deletion.py -v

# Run specific test categories
pytest tests/test_gdpr_data_deletion.py::TestGDPRDeletionRequest -v
pytest tests/test_gdpr_data_deletion.py::TestUserDataIdentification -v
pytest tests/test_gdpr_data_deletion.py::TestActualDataDeletion -v
pytest tests/test_gdpr_data_deletion.py::TestDeletionVerification -v
```

### Test Coverage

The test suite includes:
- ✅ Deletion request creation and validation
- ✅ 30-day deadline tracking and automatic execution
- ✅ Complete user data identification across all tables
- ✅ Actual data deletion with verification
- ✅ Multi-system deletion (PostgreSQL, Redis, logs, backups, Stripe)
- ✅ Cascading deletion of related records
- ✅ Audit trail preservation during deletion
- ✅ Deletion verification and certificate generation
- ✅ Compliance reporting and metrics
- ✅ Performance and stress testing
- ✅ Error handling and recovery

### Performance Requirements

- **Deletion Speed**: Complete user deletion within 60 seconds for typical datasets
- **Batch Processing**: Handle up to 50 concurrent deletions efficiently  
- **System Impact**: <5% performance impact on normal operations
- **Scalability**: Support for millions of users and related records
- **Availability**: 99.9% uptime for deletion request processing

## Monitoring and Observability

### Metrics Tracking

Key metrics monitored:
- **Total Deletion Requests**: Historical count of all requests
- **Completion Rate**: Percentage of successfully completed deletions
- **Average Processing Time**: Time from request to completion
- **Compliance Rate**: Percentage of deletions within 30-day deadline
- **System Success Rates**: Per-system deletion success rates
- **Alert Frequency**: Number of alerts generated per day

### Health Checks

```bash
# Check GDPR service health
curl http://localhost:8000/api/v1/gdpr/health

# Monitor scheduler status
curl http://localhost:8000/api/v1/gdpr/admin/scheduler-status
```

### Logging

All GDPR deletion operations are logged with:
- **Structured Logging**: JSON format for parsing and analysis
- **Correlation IDs**: Track requests across all operations
- **PII Protection**: No personal data in logs (anonymized references only)
- **Audit Compliance**: Maintains required audit trail
- **Performance Metrics**: Timing and resource usage data

## Security Considerations

### Data Protection During Deletion

- **Encrypted Transit**: All deletion operations use encrypted connections
- **Access Controls**: Role-based access to deletion functions
- **Audit Logging**: Complete audit trail of all deletion activities
- **Verification**: Multi-step verification before irreversible deletion
- **Backup Security**: Secure anonymization in backup systems

### Administrative Access

- **Admin Authentication**: Strong authentication for admin functions
- **Role Separation**: Separate permissions for viewing vs. executing deletions
- **Approval Workflows**: Optional approval requirements for admin-initiated deletions
- **Activity Monitoring**: All admin actions logged and monitored

## Troubleshooting

### Common Issues

#### 1. Deletion Request Creation Fails
```
Error: User with ID 12345 does not exist
```
**Solution**: Verify user ID exists in database

#### 2. Deletion Verification Incomplete
```
Warning: Verification score 95% - remaining data found
```
**Solutions**:
- Check for custom tables with user references
- Verify Redis pattern matching covers all user keys
- Ensure backup anonymization completed

#### 3. Scheduled Job Not Executing
```
Error: GDPR scheduler inactive
```
**Solutions**:
- Check database connection configuration
- Verify cron job is configured correctly
- Review scheduler logs for initialization errors

#### 4. Certificate Generation Fails
```
Error: Failed to generate deletion certificate
```
**Solutions**:
- Ensure verification completed successfully
- Check database write permissions
- Verify certificate storage configuration

### Diagnostic Commands

```bash
# Check system health
curl http://localhost:8000/api/v1/gdpr/health

# Test deletion verification
python -c "
import asyncio
from app.services.deletion_verifier import DeletionVerifier
from app.core.database import get_async_db

async def test():
    async with get_async_db() as db:
        verifier = DeletionVerifier(db)
        result = await verifier.verify_user_deletion(123)
        print(f'Complete: {result.is_completely_deleted}')
        
asyncio.run(test())
"

# Check scheduler status
python -c "
import asyncio
from app.services.gdpr_scheduler import get_gdpr_scheduler_status

status = asyncio.run(get_gdpr_scheduler_status())
print(f'Scheduler: {status[\"scheduler_status\"]}')
"
```

### Performance Optimization

#### Large Dataset Handling
```python
# Configure batch sizes for large datasets
job_config = {
    "max_batch_size": 25,  # Reduce for slower systems
    "processing_delay_ms": 500,  # Add delay between operations
}

# Monitor processing times
GET /api/v1/gdpr/admin/metrics
# Look for average_processing_time_hours
```

#### Memory Usage
```python
# For systems with limited memory
deletion_config = {
    "batch_size": 500,  # Reduce batch size
    "use_streaming": True,  # Stream large result sets
    "cleanup_frequency": 10  # More frequent cleanup
}
```

## Legal and Compliance

### GDPR Article 17 Compliance Statement

This system implements complete compliance with GDPR Article 17 "Right to erasure" including:

1. **Right to Request**: Users can easily request deletion of their personal data
2. **Complete Erasure**: All personal data is irreversibly deleted, not just anonymized
3. **30-Day Deadline**: Automatic execution within the mandatory 30-day timeframe
4. **Comprehensive Scope**: Covers all systems and backups where data is stored
5. **Verification**: Provides verification that deletion was completed
6. **Documentation**: Generates legally-compliant certificates as proof
7. **Audit Trail**: Maintains anonymized audit records for compliance

### Data Controller Responsibilities

Under GDPR, the data controller (PratikoAI) must:

✅ **Respond Promptly**: Acknowledge deletion requests within 72 hours  
✅ **Execute Completely**: Delete all personal data within 30 days  
✅ **Verify Deletion**: Confirm complete removal of data  
✅ **Document Compliance**: Maintain records of deletion activities  
✅ **Inform Third Parties**: Notify any third parties of deletion requirements  
✅ **Provide Evidence**: Supply certificates or proof of deletion when requested  

### Italian Data Protection Authority Compliance

Additional requirements for Italian users:

✅ **Codice Fiscale Protection**: Special encryption and deletion procedures  
✅ **Financial Data Security**: Enhanced protection for payment information  
✅ **Local Language Support**: Italian language documentation and certificates  
✅ **Authority Reporting**: Capability to report to Italian privacy authorities  

## API Reference

### User Endpoints

#### Create Deletion Request
```http
POST /api/v1/gdpr/deletion-request
Content-Type: application/json
Authorization: Bearer {user_token}

{
    "reason": "I want to delete my account and all personal data",
    "priority": "normal"
}
```

#### Get Deletion Status
```http
GET /api/v1/gdpr/deletion-request/status
Authorization: Bearer {user_token}
```

#### Download Certificate
```http
GET /api/v1/gdpr/deletion-certificate/{certificate_id}
Authorization: Bearer {user_token}
```

### Admin Endpoints

#### List All Deletion Requests
```http
GET /api/v1/gdpr/admin/deletion-requests?status=pending&limit=50
Authorization: Bearer {admin_token}
```

#### Create Admin Deletion Request
```http
POST /api/v1/gdpr/admin/deletion-request
Content-Type: application/json
Authorization: Bearer {admin_token}

{
    "user_id": 123,
    "reason": "Account inactive for 2 years",
    "priority": "low"
}
```

#### Execute Overdue Deletions
```http
POST /api/v1/gdpr/admin/execute-overdue
Authorization: Bearer {admin_token}
```

#### Generate Compliance Report
```http
GET /api/v1/gdpr/admin/compliance-report?days=30
Authorization: Bearer {admin_token}
```

### System Endpoints

#### Execute Scheduled Deletions
```http
POST /api/v1/gdpr/system/execute-scheduled-deletions
```

#### Health Check
```http
GET /api/v1/gdpr/health
```

## Best Practices

### Implementation Guidelines

1. **Test Thoroughly**: Use comprehensive test suite before production deployment
2. **Monitor Actively**: Set up monitoring and alerting for all GDPR operations
3. **Document Everything**: Maintain detailed logs and audit trails
4. **Verify Regularly**: Perform periodic verification of deletion completeness
5. **Update Regularly**: Keep deletion logic updated as system evolves

### Operational Procedures

1. **Daily Monitoring**: Check for overdue requests and system alerts
2. **Weekly Reports**: Generate compliance reports for management review
3. **Monthly Audits**: Verify system is operating correctly and completely
4. **Quarterly Reviews**: Review and update deletion procedures as needed
5. **Annual Assessments**: Full compliance assessment and documentation review

### Development Guidelines

1. **New Features**: Always consider GDPR deletion impact when adding new features
2. **Data Storage**: Document all new user data storage locations
3. **Third-Party Integration**: Ensure all external services support data deletion
4. **Testing**: Include GDPR deletion tests for all new user data handling
5. **Documentation**: Update deletion documentation when data model changes

## Support and Maintenance

### Getting Help

1. **Check Logs**: Review application logs for error details
2. **Run Diagnostics**: Use provided diagnostic commands
3. **Review Documentation**: Check this guide and API documentation
4. **Test Environment**: Use test environment to reproduce issues
5. **Create Issues**: Document problems with full context and logs

### Emergency Procedures

For urgent GDPR compliance issues:

1. **Immediate Assessment**: Determine scope and impact of issue
2. **Execute Manual Deletion**: Use admin tools to manually process critical requests
3. **Generate Emergency Reports**: Document all actions taken
4. **Notify Stakeholders**: Inform legal and compliance teams
5. **Implement Fixes**: Deploy fixes and verify system operation

---

## Changelog

### v1.0.0 (2025-08-05)
- Initial implementation of comprehensive GDPR deletion system
- Complete multi-system deletion across PostgreSQL, Redis, logs, backups, Stripe
- 30-day deadline tracking with automatic execution
- Deletion verification and certificate generation
- Admin interface and compliance reporting
- Automated scheduling and monitoring
- Full test coverage and documentation

---

*This documentation is maintained as part of the PratikoAI GDPR compliance system. For updates and corrections, please refer to the latest version in the repository.*