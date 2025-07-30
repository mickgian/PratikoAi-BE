# 🚨 PratikoAI Incident Response Playbook

## Quick Reference

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| **P0 - Critical** | 15 minutes | Immediate |
| **P1 - High** | 1 hour | 2 hours |
| **P2 - Medium** | 4 hours | 24 hours |
| **P3 - Low** | 24 hours | 48 hours |

## 🔧 Monitoring Systems Overview

### Automated Alerts
- **Metrics Reports**: Every 12 hours via configured recipients
- **Performance Alerts**: Real-time via performance monitor
- **Security Alerts**: Immediate via security monitor
- **Cost Alerts**: When approaching €2/user/month threshold

### Key Dashboards
- **Health Summary**: `GET /api/v1/metrics/health-summary`
- **Performance**: `GET /api/v1/performance/overview`
- **Security**: `GET /api/v1/security/stats`
- **Costs**: `GET /api/v1/analytics/cost-summary`

---

## 🚨 P0 - Critical Incidents

### Definition
- Complete system outage
- Data breach or security compromise
- Payment processing failure
- GDPR compliance violation

### Immediate Actions (0-15 minutes)

1. **Acknowledge & Assess**
   ```bash
   # Check system health
   curl -X GET "${API_BASE_URL}/api/v1/metrics/health-summary"
   
   # Check performance metrics
   curl -X GET "${API_BASE_URL}/api/v1/performance/overview"
   ```

2. **Communicate**
   - Update status page
   - Notify stakeholders via configured email lists
   - Start incident log

3. **Emergency Switches**
   ```bash
   # Enable maintenance mode (if available)
   # Switch to backup provider
   # Activate cost circuit breakers
   ```

### P0 Specific Scenarios

#### System Outage
```bash
# Check database connectivity
curl -X GET "${API_BASE_URL}/api/v1/health"

# Check LLM providers
curl -X GET "${API_BASE_URL}/api/v1/llm/health"

# Failover to backup provider
export LLM_PREFERRED_PROVIDER="anthropic"  # or "openai"
```

#### Security Breach
```bash
# Get security alerts
curl -X GET "${API_BASE_URL}/api/v1/security/alerts"

# Check for suspicious activity
curl -X GET "${API_BASE_URL}/api/v1/security/threats"

# Rotate API keys immediately
# Block suspicious IPs
# Export audit logs
```

#### Payment Failure
```bash
# Check Stripe webhook status
curl -X GET "${API_BASE_URL}/api/v1/payments/webhook-status"

# Verify payment processing
curl -X GET "${API_BASE_URL}/api/v1/payments/health"

# Contact Stripe support if needed
```

---

## 🔥 P1 - High Priority Incidents

### Definition
- Partial system degradation
- High error rates (>5%)
- Performance issues (response time >1s)
- Cost threshold exceeded

### Response Actions (0-1 hour)

#### Performance Degradation
```bash
# Check slow queries
curl -X GET "${API_BASE_URL}/api/v1/performance/database/stats"

# Optimize connection pool
curl -X POST "${API_BASE_URL}/api/v1/performance/database/optimize-pool"

# Check cache hit rates
curl -X GET "${API_BASE_URL}/api/v1/performance/monitoring/endpoints"
```

#### Cost Threshold Exceeded
```bash
# Get cost breakdown
curl -X GET "${API_BASE_URL}/api/v1/analytics/cost-summary"

# Check LLM usage
curl -X GET "${API_BASE_URL}/api/v1/analytics/llm-usage"

# Activate cost limiting
curl -X POST "${API_BASE_URL}/api/v1/analytics/enable-cost-limits"
```

---

## ⚠️ P2 - Medium Priority Incidents

### Definition
- Individual feature failures
- Minor performance issues
- Non-critical security alerts
- Cache misses >20%

### Response Actions (0-4 hours)

#### Cache Performance Issues
```bash
# Check cache statistics
curl -X GET "${API_BASE_URL}/api/v1/performance/compression/stats"

# Reset cache if needed
curl -X POST "${API_BASE_URL}/api/v1/performance/compression/reset-stats"
```

#### Feature-specific Issues
```bash
# Check Italian knowledge service
curl -X GET "${API_BASE_URL}/api/v1/italian/health"

# Check vector search
curl -X GET "${API_BASE_URL}/api/v1/search/health"

# Test payment flows
curl -X GET "${API_BASE_URL}/api/v1/payments/test"
```

---

## 📊 P3 - Low Priority Incidents

### Definition
- Minor bugs
- Documentation issues
- Non-urgent maintenance
- Performance optimizations

### Response Actions (within 24 hours)

- Log in issue tracker
- Schedule for next maintenance window
- Document workarounds if needed

---

## 🔍 Diagnostic Commands

### System Health Check
```bash
#!/bin/bash
echo "=== PratikoAI Health Check ==="

API_BASE_URL=${API_BASE_URL:-"https://api.pratikoai.com"}

echo "1. Overall Health:"
curl -s -X GET "${API_BASE_URL}/api/v1/metrics/health-summary" | jq

echo "2. Performance Metrics:"
curl -s -X GET "${API_BASE_URL}/api/v1/performance/overview" | jq

echo "3. Security Status:"
curl -s -X GET "${API_BASE_URL}/api/v1/security/stats" | jq

echo "4. Cost Status:"
curl -s -X GET "${API_BASE_URL}/api/v1/analytics/cost-summary" | jq

echo "5. Database Performance:"
curl -s -X GET "${API_BASE_URL}/api/v1/performance/database/stats" | jq
```

### Emergency Provider Switch
```bash
#!/bin/bash
echo "Switching to backup LLM provider..."

# Update environment variable
export LLM_PREFERRED_PROVIDER="anthropic"  # or "openai"

# Restart application or update config
# Verify switch worked
curl -X GET "${API_BASE_URL}/api/v1/llm/current-provider"
```

### Cost Emergency Brake
```bash
#!/bin/bash
echo "Activating emergency cost controls..."

# Enable strict rate limiting
curl -X POST "${API_BASE_URL}/api/v1/analytics/emergency-limits"

# Switch to cheapest model
export LLM_MODEL="gpt-4o-mini"

# Verify limits are active
curl -X GET "${API_BASE_URL}/api/v1/analytics/current-limits"
```

---

## 📞 Escalation Contacts

### Contact Configuration
All contact information is configured via environment variables:

```bash
# Internal Team Contacts
INCIDENT_PRIMARY_CONTACT=${INCIDENT_PRIMARY_CONTACT}
INCIDENT_TECHNICAL_CONTACT=${INCIDENT_TECHNICAL_CONTACT}
INCIDENT_BUSINESS_CONTACT=${INCIDENT_BUSINESS_CONTACT}

# External Vendor Contacts
STRIPE_SUPPORT_CONTACT=${STRIPE_SUPPORT_CONTACT:-"https://support.stripe.com"}
OPENAI_SUPPORT_CONTACT=${OPENAI_SUPPORT_CONTACT:-"https://help.openai.com"}
ANTHROPIC_SUPPORT_CONTACT=${ANTHROPIC_SUPPORT_CONTACT:-"https://support.anthropic.com"}
PINECONE_SUPPORT_CONTACT=${PINECONE_SUPPORT_CONTACT:-"https://support.pinecone.io"}
```

### Environment Variable Setup
Add these to your environment files:

```bash
# .env.production
INCIDENT_PRIMARY_CONTACT=primary-oncall@pratikoai.com
INCIDENT_TECHNICAL_CONTACT=tech-team@pratikoai.com
INCIDENT_BUSINESS_CONTACT=business-alerts@pratikoai.com

# .env.staging  
INCIDENT_PRIMARY_CONTACT=staging-alerts@pratikoai.com
INCIDENT_TECHNICAL_CONTACT=dev-team@pratikoai.com
INCIDENT_BUSINESS_CONTACT=qa-team@pratikoai.com

# .env.development
INCIDENT_PRIMARY_CONTACT=dev-alerts@pratikoai.com
INCIDENT_TECHNICAL_CONTACT=dev-team@pratikoai.com
INCIDENT_BUSINESS_CONTACT=admin@pratikoai.com
```

### Emergency Procedures
1. **Database Issues**: Contact hosting provider
2. **DNS Issues**: Contact domain registrar  
3. **SSL Issues**: Contact certificate provider
4. **DDoS**: Contact CDN provider

---

## 🚨 Automated Incident Notification

### Email Integration
The system uses the existing email service for incident notifications:

```bash
# Send incident notification to configured recipients
curl -X POST "${API_BASE_URL}/api/v1/metrics/email-report" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_emails": ["${INCIDENT_PRIMARY_CONTACT}", "${INCIDENT_TECHNICAL_CONTACT}"],
    "environments": ["production"]
  }'
```

### Notification Recipients
Incident notifications use the same environment-based email configuration:

- **INCIDENT_PRIMARY_CONTACT**: First responder
- **INCIDENT_TECHNICAL_CONTACT**: Technical team
- **INCIDENT_BUSINESS_CONTACT**: Business stakeholders
- **METRICS_REPORT_RECIPIENTS_ADMIN**: Admin notifications

---

## 📝 Post-Incident Actions

### Immediate (within 2 hours)
1. **Document timeline** of incident
2. **Identify root cause**
3. **Verify fix is stable**
4. **Update status page** - incident resolved

### Follow-up (within 48 hours)
1. **Post-mortem meeting**
2. **Action items** to prevent recurrence
3. **Update monitoring** if needed
4. **Review and update** this playbook

### Post-Mortem Template
```markdown
# Incident Post-Mortem: [Date] - [Brief Description]

## Summary
- **Start**: [Time]
- **End**: [Time]
- **Duration**: [Minutes]
- **Severity**: [P0/P1/P2/P3]

## Impact
- **Users affected**: [Number/Percentage]
- **Revenue impact**: [Amount if applicable]
- **Services affected**: [List]

## Root Cause
[Detailed explanation]

## Timeline
- [Time]: [Event]
- [Time]: [Action taken]
- [Time]: [Resolution]

## What Went Well
- [Things that worked]

## What Could Be Improved
- [Areas for improvement]

## Action Items
- [ ] [Action] - Owner: [Name] - Due: [Date]
- [ ] [Action] - Owner: [Name] - Due: [Date]
```

---

## 🔄 Playbook Maintenance

### Monthly Review
- Update contact information in environment variables
- Review and test diagnostic commands
- Validate escalation procedures
- Update based on recent incidents

### Quarterly Testing
- Conduct tabletop exercises
- Test backup procedures
- Verify monitoring alerts work
- Update emergency contacts in environment files

---

## 🚀 Quick Recovery Checklist

### For Any Incident:
- [ ] Incident acknowledged within SLA
- [ ] Stakeholders notified via configured contacts
- [ ] Diagnostic commands run
- [ ] Fix applied and tested
- [ ] Monitoring confirms resolution
- [ ] Post-incident review scheduled

### For P0 Incidents:
- [ ] Emergency contacts notified (from environment variables)
- [ ] Status page updated
- [ ] Customer communication sent
- [ ] Executive team informed
- [ ] External vendor support engaged if needed

---

## ⚙️ Configuration Setup

To fully activate incident response, ensure these environment variables are configured:

```bash
# Required for incident notifications
INCIDENT_PRIMARY_CONTACT=your-primary-contact@example.com
INCIDENT_TECHNICAL_CONTACT=your-tech-team@example.com  
INCIDENT_BUSINESS_CONTACT=your-business-team@example.com

# API endpoint for health checks
API_BASE_URL=https://your-api-domain.com

# Optional: Custom support contacts
STRIPE_SUPPORT_CONTACT=your-stripe-contact
OPENAI_SUPPORT_CONTACT=your-openai-contact
```

**Remember**: All sensitive information (emails, contacts, URLs) should be configured via environment variables, never hardcoded in this playbook.