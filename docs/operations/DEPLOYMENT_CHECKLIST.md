# PratikoAI Deployment Checklist

## Missing Configuration for Staging Environment

### 🔑 Required Secrets

**Pinecone Configuration**
- [ ] `PINECONE_API_KEY` - Staging Pinecone API key
- [ ] `PINECONE_ENVIRONMENT` - Set to `serverless` (or specific region)
- [ ] `PINECONE_INDEX_NAME` - Suggest: `pratikoai-staging` or `pratikoai-embed-384`

**Database Configuration**
- [ ] `POSTGRES_URL` - Staging PostgreSQL connection string
- [ ] Database credentials and connection details

**Authentication Secrets**
- [ ] `JWT_SECRET_KEY` - Staging JWT signing key (must be unique)
- [ ] `GOOGLE_CLIENT_ID` - Staging Google OAuth client ID
- [ ] `GOOGLE_CLIENT_SECRET` - Staging Google OAuth secret
- [ ] `LINKEDIN_CLIENT_ID` - Staging LinkedIn OAuth client ID
- [ ] `LINKEDIN_CLIENT_SECRET` - Staging LinkedIn OAuth secret

**LLM Configuration**
- [ ] `OPENAI_API_KEY` - OpenAI API key for staging
- [ ] `LLM_API_KEY` - Primary LLM service API key

**Monitoring & Observability**
- [ ] `LANGFUSE_PUBLIC_KEY` - Staging Langfuse public key
- [ ] `LANGFUSE_SECRET_KEY` - Staging Langfuse secret key

### 📋 Configuration Files Needed

**Create Environment File**
- [ ] Create `.env.staging` (copy from `.env.staging.example`)
- [ ] Populate all required secrets listed above
- [ ] Verify file is gitignored and not committed

**Docker Configuration**
- [ ] Update `docker-compose.yml` environment variables for staging
- [ ] Test with `APP_ENV=staging docker-compose up`

### 🧪 Staging Verification Steps

```bash
# 1. Set staging environment
export APP_ENV=staging

# 2. Test vector service initialization
python -c "from app.services.vector_service_enhanced import EnhancedVectorService; print('✅ OK' if EnhancedVectorService().is_available() else '❌ Failed')"

# 3. Test database connection
python -c "from app.services.database import get_session; print('✅ DB OK')"

# 4. Test Pinecone connection (if configured)
python -c "
config = VectorConfig()
if config.is_pinecone_configured():
    print('✅ Pinecone configured')
else:
    print('ℹ️ Pinecone not configured - using local fallback')
"
```

---

## Missing Configuration for Production Environment

### 🔑 Required Secrets

**Pinecone Configuration**
- [ ] `PINECONE_API_KEY` - Production Pinecone API key (separate from staging)
- [ ] `PINECONE_ENVIRONMENT` - Set to `serverless` or production-specific region
- [ ] `PINECONE_INDEX_NAME` - Suggest: `pratikoai-prod` or `pratikoai-embed-384`
- [ ] `PINECONE_NAMESPACE_PREFIX` - Set to `env=prod` (default)

**Database Configuration**
- [ ] `POSTGRES_URL` - Production PostgreSQL connection string (encrypted/secure)
- [ ] Database credentials with minimal required permissions
- [ ] Connection pooling configuration for production load

**Authentication Secrets**
- [ ] `JWT_SECRET_KEY` - Production JWT signing key (cryptographically strong)
- [ ] `GOOGLE_CLIENT_ID` - Production Google OAuth client ID
- [ ] `GOOGLE_CLIENT_SECRET` - Production Google OAuth secret
- [ ] `LINKEDIN_CLIENT_ID` - Production LinkedIn OAuth client ID
- [ ] `LINKEDIN_CLIENT_SECRET` - Production LinkedIn OAuth secret
- [ ] `OAUTH_REDIRECT_URI` - Production callback URL

**LLM Configuration**
- [ ] `OPENAI_API_KEY` - Production OpenAI API key with usage limits
- [ ] `LLM_API_KEY` - Production LLM service API key
- [ ] `DEFAULT_LLM_TEMPERATURE` - Production-tuned temperature setting

**Monitoring & Observability**
- [ ] `LANGFUSE_PUBLIC_KEY` - Production Langfuse public key
- [ ] `LANGFUSE_SECRET_KEY` - Production Langfuse secret key
- [ ] `LANGFUSE_HOST` - Production Langfuse endpoint

**Email Configuration** (for alerts/reports)
- [ ] `SMTP_SERVER` - Production SMTP server
- [ ] `SMTP_USERNAME` - Production email username
- [ ] `SMTP_PASSWORD` - Production email password/app password
- [ ] `FROM_EMAIL` - Production sender email address
- [ ] `METRICS_REPORT_RECIPIENTS` - Production alert recipients

**Rate Limiting & Security**
- [ ] `RATE_LIMIT_DEFAULT` - Production rate limiting settings
- [ ] `RATE_LIMIT_CHAT` - Production chat rate limits
- [ ] `ALLOWED_ORIGINS` - Production frontend URLs only

### 🏗️ Infrastructure Configuration

**Vector Search Production Settings**
- [ ] `VECTOR_STRICT_MODE` - Set to `true` for production
- [ ] `VECTOR_STRICT_EMBEDDER_MATCH` - Set to `true` for production
- [ ] Consider separate Pinecone indexes for different domains

**Performance Configuration**
- [ ] `POSTGRES_POOL_SIZE` - Tune for production load (suggest 20)
- [ ] `POSTGRES_MAX_OVERFLOW` - Set production overflow limit (suggest 30)
- [ ] `LOG_LEVEL` - Set to `INFO` or `WARNING` for production

### 📋 Production Deployment Files

**Create Production Environment File**
- [ ] Create `.env.production` (copy from `.env.production.example`)
- [ ] Populate all required secrets with production values
- [ ] Store sensitive secrets in AWS Secrets Manager or similar
- [ ] Use environment variable injection in production deployment

**Security Configuration**
- [ ] Enable TLS/HTTPS for all endpoints
- [ ] Configure firewall rules for database access
- [ ] Set up VPC/network isolation if using AWS
- [ ] Configure backup and disaster recovery procedures

### 🧪 Production Verification Steps

```bash
# 1. Set production environment
export APP_ENV=production

# 2. Test all services in production mode
python -c "
from app.services.vector_service_enhanced import EnhancedVectorService
service = EnhancedVectorService()
stats = service.get_service_stats()
print(f'Provider: {stats[\"provider_available\"]}')
print(f'Config: {stats[\"config\"][\"provider_preference\"]}')
print(f'Strict Mode: {stats[\"config\"][\"strict_mode\"]}')
"

# 3. Test production vector operations
python -c "
service = EnhancedVectorService()
# Test document storage
result = service.store_document('test-prod', 'test content', {'domain': 'fiscale'})
print(f'Storage: {\"✅ OK\" if result else \"❌ Failed\"}')
# Test search
results = service.search_similar('test query', top_k=1)
print(f'Search: {\"✅ OK\" if results else \"❌ Failed\"}')
"

# 4. Verify production settings
python -c "
from app.services.vector_config import VectorConfig
config = VectorConfig()
print(f'Strict Mode: {config.strict_mode}')
print(f'Provider: {config.get_provider_preference()}')
print(f'Fallback Allowed: {config.allow_fallback_in_production()}')
"
```

---

## Environment-Specific Index Strategy

### Development
- **Index**: `pratikoai-dev` ✅ (exists)
- **Namespace**: `env=dev,domain=*,tenant=default`
- **Data**: Test data, can be reset/cleared

### Staging
- **Index**: `pratikoai-staging` (create new)
- **Namespace**: `env=staging,domain=*,tenant=default`
- **Data**: Production-like data for testing

### Production
- **Index**: `pratikoai-prod` (create new)
- **Namespace**: `env=prod,domain=*,tenant=default`
- **Data**: Live production data
- **Backup**: Enable automated backups

## Security Best Practices

### 🔒 Secrets Management
- [ ] **Never commit secrets to git** - Use .env files that are gitignored
- [ ] **Use different API keys per environment** - Isolate development from production
- [ ] **Rotate API keys regularly** - Especially production keys
- [ ] **Use AWS Secrets Manager** - For production secret storage
- [ ] **Audit secret access** - Monitor who accesses production secrets

### 🛡️ Network Security
- [ ] **Enable VPC for production databases** - Isolate database access
- [ ] **Use TLS for all connections** - Encrypt data in transit
- [ ] **Configure firewall rules** - Allow only necessary connections
- [ ] **Monitor API usage** - Set up alerts for unusual activity
- [ ] **Enable request rate limiting** - Prevent abuse

### 📊 Monitoring Setup
- [ ] **Configure Langfuse for each environment** - Separate dashboards
- [ ] **Set up production alerts** - Monitor errors and performance
- [ ] **Configure log aggregation** - Centralized logging system
- [ ] **Monitor Pinecone usage** - Track API quotas and costs
- [ ] **Set up health checks** - Automated service monitoring

## Cost Optimization

### Pinecone Cost Management
- [ ] **Monitor index usage** - Track vector count and queries
- [ ] **Set up usage alerts** - Get notified of cost increases
- [ ] **Optimize index size** - Remove unused vectors periodically
- [ ] **Consider regional pricing** - Choose cost-effective regions

### Infrastructure Optimization
- [ ] **Right-size instances** - Match compute resources to usage
- [ ] **Enable auto-scaling** - Scale based on demand
- [ ] **Monitor database performance** - Optimize queries and indexes
- [ ] **Cache frequently accessed data** - Use Redis for hot data

---

## Deployment Commands

### Staging Deployment
```bash
# 1. Build staging image
docker build --build-arg APP_ENV=staging -t pratikoai-staging .

# 2. Run staging services
APP_ENV=staging docker-compose up -d

# 3. Verify staging deployment
curl http://localhost:8000/health
```

### Production Deployment
```bash
# 1. Build production image
docker build --build-arg APP_ENV=production -t pratikoai-prod .

# 2. Deploy to production infrastructure
# (specific commands depend on deployment platform: AWS, GCP, etc.)

# 3. Verify production deployment
curl https://api.pratikoai.com/health
```

This completes the configuration requirements for staging and production environments. Each environment should be configured and tested independently before deployment.
