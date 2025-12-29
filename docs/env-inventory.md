# Environment Inventory Report
## PratikoAI Backend - Python/FastAPI Application

**Generated**: 2025-09-11  
**Version**: 1.0.0  
**Application**: PratikoAI Backend (FastAPI)

---

## 1. Environment Configuration Overview

### Environment Selection Method
The application uses the `APP_ENV` environment variable to determine the runtime environment through the `Environment` enum in `app/core/config.py`:

- **Development**: `APP_ENV=development` (default)  
- **Staging**: `APP_ENV=staging`  
- **Production**: `APP_ENV=production`  
- **Test**: `APP_ENV=test`

### Environment File Loading Priority
The configuration system loads .env files in the following priority order:
1. `.env.{environment}.local` (highest priority)
2. `.env.{environment}`  
3. `.env.local`
4. `.env` (lowest priority)

### Environment-Specific Overrides
Automatic overrides are applied based on the selected environment:

| Setting | Development | Staging | Production | Test |
|---------|-------------|---------|------------|------|
| DEBUG | true | false | false | true |
| LOG_LEVEL | DEBUG | INFO | WARNING | DEBUG |
| LOG_FORMAT | console | json | json | console |
| Rate Limits | 1000/day, 200/hour | 500/day, 100/hour | 200/day, 50/hour | 1000/day, 1000/hour |

---

## 2. Configuration Files Analysis

### Available Configuration Files

| File | Status | Purpose |
|------|--------|---------|
| `.env.development` | ✅ Exists | Active development configuration |
| `.env.example` | ✅ Exists | Template with minimal configuration |
| `.env.staging.example` | ✅ Exists | Staging environment template |
| `.env.production.example` | ✅ Exists | Production environment template |
| `.env.staging` | ❌ Missing | Actual staging configuration |
| `.env.production` | ❌ Missing | Actual production configuration |

### Configuration Variables by Category

#### Core Application Settings
```bash
PROJECT_NAME="Web Assistant"
VERSION="1.0.0"
API_V1_STR="/api/v1"
BASE_URL="http://localhost:8000" (dev) | "https://api-qa.pratiko.app" (qa) | "https://api.pratiko.app" (prod)
DEBUG=true (dev) | false (qa/prod)
```

#### Database Configuration
```bash
# Development
POSTGRES_URL="postgresql://aifinance:devpass@localhost:5432/aifinance"

# Staging (template)
POSTGRES_URL="postgresql+asyncpg://username:password@staging-db-host:5432/pratikoai_staging"

# Production (template)  
POSTGRES_URL="postgresql+asyncpg://username:password@prod-db-host:5432/pratikoai_prod?ssl=require"

# Connection Pool Settings
POSTGRES_POOL_SIZE=5 (dev) | 20 (prod)
POSTGRES_MAX_OVERFLOW=10 (dev) | 10 (prod)
```

#### Authentication & Security
```bash
JWT_SECRET_KEY="your-jwt-secret-key"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_HOURS=720 (30 days dev) | 720 (staging) | 168 (7 days prod)
JWT_REFRESH_TOKEN_EXPIRE_DAYS=365 (dev) | 365 (staging) | 90 (prod)

# OAuth Providers
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
LINKEDIN_CLIENT_ID="your-linkedin-client-id"
LINKEDIN_CLIENT_SECRET="your-linkedin-client-secret"
OAUTH_REDIRECT_URI="http://localhost:8000/api/v1/auth/oauth/callback"
```

#### Vector Database Configuration (Pinecone)
```bash
PINECONE_API_KEY=""
PINECONE_ENVIRONMENT=""  
PINECONE_INDEX_NAME="normoai-knowledge" (dev) | "pratikoai-knowledge-staging" (staging) | "pratikoai-knowledge-prod" (production)
VECTOR_DIMENSION=384
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
VECTOR_SIMILARITY_THRESHOLD=0.7
MAX_SEARCH_RESULTS=10
```

#### LLM Provider Configuration
```bash
# OpenAI
LLM_API_KEY="sk-proj-..." (legacy)
OPENAI_API_KEY="sk-proj-..."  
OPENAI_MODEL="gpt-4o-mini"

# Anthropic
ANTHROPIC_API_KEY=""
ANTHROPIC_MODEL="claude-3-haiku-20240307"

# Routing & Cost Control
LLM_ROUTING_STRATEGY="cost_optimized" # cost_optimized, quality_first, balanced, failover
LLM_MAX_COST_EUR=0.020  # Max €0.02 per request
LLM_PREFERRED_PROVIDER="" # openai, anthropic
DEFAULT_LLM_TEMPERATURE=0.2
MAX_TOKENS=2000
MAX_LLM_CALL_RETRIES=3
```

#### Monitoring & Observability
```bash
# Langfuse
LANGFUSE_PUBLIC_KEY="your-langfuse-public-key"
LANGFUSE_SECRET_KEY="your-langfuse-secret-key" 
LANGFUSE_HOST="https://cloud.langfuse.com"

# Logging
LOG_LEVEL="DEBUG" (dev) | "INFO" (staging) | "WARNING" (prod)
LOG_FORMAT="console" (dev) | "json" (staging/prod)
LOG_DIR="logs"
```

#### Payment Integration (Stripe)
```bash
# Development/Staging (Test Mode)
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_PUBLISHABLE_KEY="pk_test_..."

# Production (Live Mode)
STRIPE_SECRET_KEY="sk_live_..."
STRIPE_PUBLISHABLE_KEY="pk_live_..."

STRIPE_WEBHOOK_SECRET="whsec_..."
STRIPE_MONTHLY_PRICE_ID="price_..." # €69/month
STRIPE_TRIAL_PERIOD_DAYS=7
```

#### Email Configuration
```bash
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
FROM_EMAIL="noreply@pratikoai.com"

# Metrics Recipients
METRICS_REPORT_RECIPIENTS="michele.giannone@gmail.com"
METRICS_REPORT_RECIPIENTS_ADMIN="michele.giannone@gmail.com"  
METRICS_REPORT_RECIPIENTS_TECH="michele.giannone@gmail.com"
METRICS_REPORT_RECIPIENTS_BUSINESS="michele.giannone@gmail.com"
```

#### Rate Limiting
```bash
RATE_LIMIT_DEFAULT="1000 per day,200 per hour" (dev) | "500 per day,100 per hour" (staging) | "200 per day,50 per hour" (prod)
RATE_LIMIT_CHAT="100 per minute"
RATE_LIMIT_CHAT_STREAM="100 per minute"
RATE_LIMIT_MESSAGES="200 per minute"
RATE_LIMIT_LOGIN="100 per minute"
```

---

## 3. Vector Search Provider Analysis

### Current Implementation: Pinecone
- **Provider**: Pinecone (Serverless)
- **Model**: sentence-transformers/all-MiniLM-L6-v2
- **Dimensions**: 384
- **Dependencies**: `pinecone>=5.0.0`, `sentence-transformers>=2.2.0`
- **Fallback**: Service gracefully degrades if dependencies unavailable

### Environment-Specific Configuration

| Environment | Index Name | Region | API Key Status |
|-------------|------------|--------|---------------|
| Development | `pratikoai-dev` | us-east-1 | ✅ Configured |
| Staging | `pratikoai-knowledge-staging` | us-east-1 (planned) | ❌ Template only |
| Production | `pratikoai-knowledge-prod` | us-east-1 (planned) | ❌ Template only |

### Capabilities
- ✅ Semantic document search
- ✅ Italian regulation storage and search  
- ✅ CCNL (labor contract) data indexing
- ✅ Tax rate information storage
- ✅ Legal template management
- ✅ Hybrid search (semantic + keyword)

---

## 4. Current Pinecone Setup Details

### Active Development Index
```yaml
Index Name: pratikoai-dev
Environment: serverless
Cloud Provider: AWS
Region: us-east-1  
Dimensions: 384
Metric: cosine
Embedding Model: sentence-transformers/all-MiniLM-L6-v2
API Key: pcsk_48WQzH_... (configured in .env.development)
```

### Index Statistics (Live)
- **Status**: Available
- **Vector Count**: Variable (depends on data ingestion)
- **Namespace Policy**: Default (no explicit namespaces)
- **Similarity Threshold**: 0.7
- **Max Search Results**: 10

### Supported Document Types
- Italian regulations (`regulation_*`)
- Tax rates (`tax_rate_*`)  
- Legal templates (`template_*`)
- CCNL agreements (`ccnl_*`)
- CCNL salary data (`ccnl_salary_*`)
- CCNL benefits (`ccnl_benefit_*`)

---

## 5. Docker & Container Configuration

### Docker Compose Environment Handling
```yaml
# Dynamic environment selection
APP_ENV: ${APP_ENV:-development}

# Environment file loading  
env_file:
  - .env.${APP_ENV:-development}

# Service configuration per environment
services:
  app:
    build:
      args:
        APP_ENV: ${APP_ENV:-development}
    environment:
      - APP_ENV=${APP_ENV:-development}
```

### Environment-Specific Services

| Service | Development | QA | Production |
|---------|-------------|---------|------------|
| Cluster | pratiko-dev | pratiko-qa | pratiko-prod |
| Service | pratiko-backend-dev | pratiko-backend-qa | pratiko-backend |
| Health URL | http://localhost:8000/health | https://api-qa.pratiko.app/health | https://api.pratiko.app/health |
| Min Replicas | 1 | 2 | 3 |
| Max Replicas | 2 | 4 | 10 |

---

## 6. CI/CD Integration

### GitHub Actions Environment Secrets
Required secrets per environment:

#### Global Secrets
- `GITHUB_TOKEN` (repo access)
- `CROSS_REPO_TOKEN` (cross-repo deployment)
- `VERSION_REGISTRY_URL`
- `VERSION_REGISTRY_TOKEN`

#### AWS Deployment
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` (us-east-1)

#### Environment-Specific Secrets
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `JWT_SECRET_KEY`
- `PINECONE_API_KEY` (per environment)

#### Notification Integration
- `SLACK_WEBHOOK_URL`
- `ORCHESTRATOR_WEBHOOK_URL`
- `ORCHESTRATOR_TOKEN`

### Deployment Strategy by Environment
- **Development**: Fast/Rolling updates
- **Staging**: Canary deployment  
- **Production**: Blue-Green deployment

---

## 7. Gaps & Missing Secrets Analysis

### Critical Missing Configurations

#### Staging Environment
- ❌ `.env.staging` file (actual configuration)
- ❌ `PINECONE_API_KEY` (staging-specific)
- ❌ `LANGFUSE_SECRET_KEY` (staging keys)
- ❌ Database connection strings (real staging DB)
- ❌ Stripe keys (staging environment)

#### Production Environment
- ❌ `.env.production` file (actual configuration)
- ❌ `PINECONE_API_KEY` (production-specific)
- ❌ `LANGFUSE_SECRET_KEY` (production keys)
- ❌ Database connection strings (real production DB)
- ❌ Stripe keys (live mode)
- ❌ SSL certificates configuration

#### Security Concerns
- ⚠️ API keys exposed in `.env.development` (development only)
- ⚠️ Default JWT secrets in templates
- ⚠️ Missing encryption key rotation configuration
- ⚠️ Default database credentials in docker-compose.yml

### Required Actions by Environment

#### Development ✅ 
**Status**: Fully configured
```bash
PINECONE_API_KEY="pk-dev-xxxxx"
PINECONE_ENVIRONMENT="us-east-1-gcp"  
PINECONE_INDEX_NAME="pratikoai-dev"
```

#### Staging ❌
**Status**: Template only - requires actual values
```bash
PINECONE_API_KEY="pk-staging-xxxxx"
PINECONE_ENVIRONMENT="us-east-1-gcp"
PINECONE_INDEX_NAME="pratikoai-staging"
```

#### Production ❌
**Status**: Template only - requires actual values  
```bash
PINECONE_API_KEY="pk-prod-xxxxx" 
PINECONE_ENVIRONMENT="us-east-1-gcp"
PINECONE_INDEX_NAME="pratikoai-prod"
```

---

## 8. Deployment Readiness Matrix

| Component | Development | Staging | Production |
|-----------|-------------|---------|------------|
| **Environment Files** | ✅ Ready | ❌ Missing | ❌ Missing |
| **Database Config** | ✅ Ready | ❌ Template | ❌ Template |
| **Vector Search** | ✅ Ready | ❌ Missing Keys | ❌ Missing Keys |
| **Authentication** | ✅ Ready | ❌ Missing Secrets | ❌ Missing Secrets |
| **Payment Processing** | ✅ Ready | ❌ Test Keys Needed | ❌ Live Keys Needed |
| **Monitoring** | ✅ Ready | ❌ Missing Keys | ❌ Missing Keys |
| **CI/CD Secrets** | ✅ Ready | ❌ Partial | ❌ Missing |

---

## 9. Next Steps & Recommendations

### Immediate Actions Required

1. **Create Missing Environment Files**
   - Copy `.env.staging.example` → `.env.staging`
   - Copy `.env.production.example` → `.env.production`
   - Fill in actual values (never commit to version control)

2. **Set Up Vector Search Environments**  
   - Create Pinecone indexes for staging and production
   - Generate environment-specific API keys
   - Configure index dimensions and regions

3. **Configure Authentication Secrets**
   - Generate strong JWT secrets per environment
   - Set up OAuth applications for each environment
   - Configure proper redirect URLs

4. **Payment Integration Setup**
   - Create Stripe test environment for staging
   - Set up live Stripe account for production
   - Configure webhooks per environment

5. **Monitoring & Observability**
   - Set up Langfuse projects per environment  
   - Configure environment-specific observability keys
   - Set up alerting channels

### Security Improvements

1. **Secret Management**
   - Implement AWS Secrets Manager or similar
   - Enable secret rotation for production
   - Remove hardcoded secrets from configuration files

2. **Database Security**
   - Enable SSL for all database connections
   - Use proper database credentials (not defaults)
   - Implement database connection encryption

3. **Network Security**  
   - Configure proper CORS origins per environment
   - Enable SSL redirect in production
   - Set up proper firewall rules

### Monitoring & Maintenance

1. **Health Checks**
   - Implement comprehensive health endpoints
   - Set up automated health monitoring
   - Configure alerting for service degradation

2. **Performance Monitoring**
   - Enable application performance monitoring
   - Set up database performance tracking
   - Configure cost monitoring for LLM usage

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-09-11  
**Next Review**: 2025-10-11  
**Owner**: DevOps Team  
**Classification**: Internal Use Only