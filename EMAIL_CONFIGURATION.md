# 📧 Email Configuration Guide

This guide explains how to configure email settings for automated metrics reporting in PratikoAI.

## 🔧 Environment Variables

### Required Email Settings

```bash
# SMTP Server Configuration
SMTP_SERVER=smtp.gmail.com          # Your SMTP server
SMTP_PORT=587                       # SMTP port (587 for TLS, 465 for SSL)
SMTP_USERNAME=your-email@gmail.com  # SMTP username
SMTP_PASSWORD=your-app-password     # SMTP password (use app passwords for Gmail)
FROM_EMAIL=noreply@pratikoai.com    # From address for emails
```

### Metrics Report Recipients

```bash
# Primary recipients (comma-separated)
METRICS_REPORT_RECIPIENTS=admin@pratikoai.com,your-email@company.com

# Role-based recipients (optional)
METRICS_REPORT_RECIPIENTS_ADMIN=admin@pratikoai.com
METRICS_REPORT_RECIPIENTS_TECH=dev-team@pratikoai.com,your-email@company.com
METRICS_REPORT_RECIPIENTS_BUSINESS=business-team@pratikoai.com
```

## 🌍 Environment-Specific Configuration

### Development (.env.development)
```bash
# For solo development, use your personal email
METRICS_REPORT_RECIPIENTS=your-email@example.com
# Or include team emails
METRICS_REPORT_RECIPIENTS=dev-team@pratikoai.com,your-email@example.com
```

### Staging (.env.staging)
```bash
# Include QA team and key stakeholders
METRICS_REPORT_RECIPIENTS=staging-alerts@pratikoai.com,qa-team@pratikoai.com
METRICS_REPORT_RECIPIENTS_ADMIN=admin@pratikoai.com,staging-admin@pratikoai.com
```

### Production (.env.production)
```bash
# Include ops team, alerts, and business stakeholders
METRICS_REPORT_RECIPIENTS=alerts@pratikoai.com,ops-team@pratikoai.com
METRICS_REPORT_RECIPIENTS_ADMIN=admin@pratikoai.com,cto@pratikoai.com
METRICS_REPORT_RECIPIENTS_BUSINESS=business-metrics@pratikoai.com,ceo@pratikoai.com
```

## 📧 Gmail Configuration

### 1. Enable 2-Factor Authentication
- Go to your Google Account settings
- Enable 2-Factor Authentication

### 2. Generate App Password
- Go to Google Account → Security → 2-Step Verification → App passwords
- Generate a new app password for "Mail"
- Use this password in `SMTP_PASSWORD`

### 3. Configuration Example
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
FROM_EMAIL=noreply@pratikoai.com
```

## 🏢 Corporate Email Configuration

### Microsoft 365 / Outlook
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@company.com
SMTP_PASSWORD=your-password
```

### Custom SMTP Server
```bash
SMTP_SERVER=mail.yourcompany.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
```

## 🚀 Report Scheduling

### Automatic Reports
- Reports are sent every 12 hours automatically
- Configured in `app/services/scheduler_service.py`
- Uses recipients from environment variables

### Manual Reports
Send immediate reports via API:
```bash
curl -X POST "http://localhost:8000/api/v1/metrics/email-report" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_emails": ["admin@pratikoai.com", "dev-team@pratikoai.com"],
    "environments": ["development", "staging", "production"]
  }'
```

## 📊 Report Content

### Technical Metrics
- API response time (P95)
- Cache hit rate
- Test coverage
- Security vulnerabilities

### Business Metrics
- API cost per user
- System uptime
- User satisfaction
- GDPR compliance

### Multi-Environment Support
- Development metrics
- Staging metrics  
- Production metrics
- Comparative health scores

## 🔒 Security Best Practices

### 1. Use App Passwords
- Never use your main email password
- Use app-specific passwords for SMTP

### 2. Environment Variables
- Store all email settings in environment variables
- Never commit credentials to code repository

### 3. Recipient Lists
- Use role-based email addresses when possible
- Regularly review recipient lists
- Remove inactive users

### 4. Email Encryption
- Always use TLS/SSL for SMTP connections
- Verify SMTP server security settings

## 🛠️ Troubleshooting

### Common Issues

#### "Authentication Failed"
- Check SMTP username and password
- Ensure 2FA is enabled and app password is used
- Verify SMTP server and port settings

#### "No Recipients Configured"
- Check environment variables are set correctly
- Verify comma-separated format for multiple emails
- Check for typos in environment variable names

#### "SMTP Connection Failed"
- Verify SMTP server and port
- Check firewall settings
- Ensure TLS/SSL is properly configured

#### "Emails Not Being Sent"
- Check logs for error messages
- Verify scheduler service is running
- Test manual email sending via API

### Testing Email Configuration

```python
# Test script to verify email configuration
import asyncio
from app.services.email_service import email_service
from app.services.metrics_service import Environment

async def test_email():
    recipients = ["test@example.com"]
    environments = [Environment.DEVELOPMENT]
    
    success = await email_service.send_metrics_report(recipients, environments)
    print(f"Email test result: {'SUCCESS' if success else 'FAILED'}")

# Run test
asyncio.run(test_email())
```

## 📋 Configuration Checklist

- [ ] SMTP server settings configured
- [ ] App password generated (for Gmail)
- [ ] Environment variables set
- [ ] Recipient lists configured
- [ ] Email templates tested
- [ ] Scheduler service enabled
- [ ] Manual email API tested
- [ ] Production settings verified
- [ ] Security settings reviewed
- [ ] Backup recipients configured

## 🚨 Important Notes

1. **Never hardcode email addresses in code**
2. **Use environment-specific recipient lists**
3. **Regularly test email delivery**
4. **Monitor email sending errors in logs**
5. **Keep recipient lists up to date**
6. **Use secure SMTP connections only**