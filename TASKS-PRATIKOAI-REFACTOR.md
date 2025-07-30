# 🚀 PratikoAI → NormoAI Refactoring Tasks

## Project Overview
Transforming PratikoAI into a specialized AI assistant for Italian tax/legal professionals.

**Target:** €25k ARR (50 customers @ €69/month)  
**Timeline:** 4 weeks  
**Focus:** Modularity, cost control, GDPR compliance

---

## 📋 Priority 1: Critical Foundation (Week 1)

### ✅ Task Status Legend
- [ ] Not Started
- [🔄] In Progress  
- [✅] Completed
- [❌] Blocked

---

### 🤖 LLM Provider Abstraction
**Priority:** CRITICAL | **Estimated Time:** 3 hours | **Status:** [✅]

**Why Critical:** Currently hardcoded to OpenAI - prevents cost optimization and provider switching.

**Implementation Tasks:**
- [✅] Create `app/core/llm/base.py` - Abstract base class for all providers
- [✅] Create `app/core/llm/providers/openai_provider.py` - OpenAI implementation
- [✅] Create `app/core/llm/providers/anthropic_provider.py` - Anthropic implementation  
- [✅] Create `app/core/llm/factory.py` - Provider factory and routing logic
- [✅] Create `app/core/llm/cost_calculator.py` - Cost estimation per provider
- [✅] Update `app/core/langgraph/graph.py` - Use new abstraction
- [✅] Update `app/core/config.py` - Add multi-provider settings
- [✅] Create tests in `tests/core/llm/`
- [✅] Update dependencies (added anthropic package)

**Success Criteria:**
- Can switch between OpenAI and Anthropic without code changes
- Cost estimation working for both providers
- All existing functionality preserved
- Tests passing with 80%+ coverage

---

### 💾 Caching Foundation  
**Priority:** CRITICAL | **Estimated Time:** 2.5 hours | **Status:** [✅]

**Why Critical:** Will reduce API costs from ~€6/user to ~€2/user target.

**Implementation Tasks:**
- [✅] Add Redis configuration to `app/core/config.py`
- [✅] Create `app/services/cache.py` - Core caching service
- [✅] Create `app/core/decorators/cache.py` - Caching decorators
- [✅] Update `app/core/langgraph/graph.py` - Add query caching
- [✅] Update `pyproject.toml` - Add redis dependencies
- [✅] Create `docker-compose.yml` Redis service
- [✅] Create tests in `tests/services/`
- [✅] Add cache monitoring to health check

**Success Criteria:**
- Redis connection working
- Query deduplication active (80%+ cache hit rate expected)
- Conversation caching implemented
- Performance monitoring integrated

---

### 🔒 Query Anonymization
**Priority:** CRITICAL | **Estimated Time:** 2 hours | **Status:** [✅]

**Why Critical:** GDPR compliance requirement for Italian market.

**Implementation Tasks:**
- [✅] Create `app/core/privacy/anonymizer.py` - PII detection and removal
- [✅] Create `app/core/privacy/gdpr.py` - GDPR compliance utilities
- [✅] Update `app/core/logging.py` - Anonymize all logs
- [✅] Update `app/api/v1/chatbot.py` - Anonymize requests
- [✅] Create `app/schemas/privacy.py` - Privacy-related schemas
- [✅] Create tests in `tests/core/privacy/`
- [✅] Add GDPR audit logging
- [✅] Create `app/api/v1/privacy.py` - Privacy management API

**Success Criteria:**
- No PII in logs or cached data
- GDPR-compliant data handling
- Audit trail for compliance verification
- Italian language PII detection working

---

### 📊 Cost Tracking
**Priority:** CRITICAL | **Estimated Time:** 2.5 hours | **Status:** [✅]

**Why Critical:** Need to maintain €2/user/month target cost.

**Implementation Tasks:**
- [✅] Create `app/models/usage.py` - Usage tracking models
- [✅] Create `app/services/usage_tracker.py` - Usage tracking service
- [✅] Update `app/core/langgraph/graph.py` - Track all LLM calls
- [✅] Create `app/api/v1/analytics.py` - Cost monitoring endpoints
- [✅] Create `app/core/middleware/cost_limiter.py` - Cost-based rate limiting
- [✅] Create tests in `tests/services/`
- [✅] Add usage tracking and optimization suggestions

**Success Criteria:**
- Real-time cost tracking per user
- Cost-based rate limiting active
- Usage analytics available
- Cost alerts when approaching limits

---

## 📋 Priority 2: Business Features (Week 2)

### 💳 Payment Integration
**Priority:** HIGH | **Estimated Time:** 4 hours | **Status:** [✅]

**Why Critical:** Essential for revenue generation and subscription management for €25k ARR target.

**Implementation Tasks:**
- [✅] Create `app/models/payment.py` - Payment, subscription, and invoice models
- [✅] Create `app/services/stripe_service.py` - Complete Stripe integration service
- [✅] Create `app/api/v1/payments.py` - Payment API endpoints
- [✅] Create `app/schemas/payment.py` - Payment schemas and validation
- [✅] Create `migrations/create_payment_tables.sql` - Database schema
- [✅] Integrate Stripe for €69/month subscriptions with 7-day trial
- [✅] Create subscription management (create, cancel, update)
- [✅] Add payment webhooks with signature verification
- [✅] Implement trial periods and billing cycles
- [✅] Add invoice generation and PDF download
- [✅] Create comprehensive test suite in `tests/services/test_stripe_service.py`
- [✅] Create API endpoint tests in `tests/api/v1/test_payments.py`
- [✅] Add cost limiter middleware integration
- [✅] Update API router with payment endpoints
- [✅] Create `PAYMENT_SETUP.md` - Setup and configuration guide

**Success Criteria:**
- Complete Stripe integration with €69/month pricing
- 7-day free trial implementation
- Secure webhook processing
- Customer and subscription management
- Invoice generation and billing history
- Cost enforcement middleware active
- Comprehensive test coverage (>80%)
- Italian market support (EUR, VAT, GDPR compliant)

### 🇮🇹 Italian Knowledge Base
**Priority:** HIGH | **Estimated Time:** 3 hours | **Status:** [✅]

**Why Critical:** Core business value for Italian tax/legal professionals target market.

**Implementation Tasks:**
- [✅] Create `app/models/italian_data.py` - Complete Italian tax and legal data models
- [✅] Create `app/services/italian_knowledge.py` - Comprehensive Italian knowledge service
- [✅] Create `app/api/v1/italian.py` - Italian-specific API endpoints with full functionality
- [✅] Create Italian tax calculation tools (VAT, IRPEF, withholding, social contributions)
- [✅] Add legal document templates system (contracts, forms, compliance checks)
- [✅] Integrate official tax rates and legal regulation framework
- [✅] Add citation tracking and source verification system
- [✅] Create compliance checking workflows (GDPR, contract, invoice validation)
- [✅] Create comprehensive tests in `tests/services/test_italian_knowledge.py`
- [✅] Add Italian language support and tax calculation localization
- [✅] Update API router to include Italian endpoints

**Success Criteria:**
- Complete Italian tax calculation system (VAT, IRPEF, withholding, social contributions)
- Legal document template generation and compliance checking
- GDPR-compliant privacy policy validation
- Contract and invoice compliance verification
- Italian tax rate and regulation database structure
- Comprehensive API endpoints for tax professionals
- Full test coverage for all calculation methods
- Italian language support throughout the system

---

## 📋 Priority 3: Production Ready (Week 3-4)

### 🗄️ Vector Database Integration
**Priority:** MEDIUM | **Estimated Time:** 3 hours | **Status:** [✅]

**Why Important:** Enables semantic search for Italian regulations, tax rates, and legal templates to enhance knowledge retrieval.

**Implementation Tasks:**
- [✅] Create `app/services/vector_service.py` - Complete vector database service with Pinecone integration
- [✅] Create `app/api/v1/search.py` - Semantic and hybrid search API endpoints
- [✅] Add sentence-transformers embedding model for multilingual support
- [✅] Implement hybrid search combining semantic and keyword search
- [✅] Create specialized Italian knowledge indexing methods
- [✅] Add vector service integration to Italian knowledge service
- [✅] Update `app/core/config.py` - Add vector database configuration
- [✅] Create comprehensive tests in `tests/test_vector_service.py`
- [✅] Update API router to include search endpoints
- [✅] Create database migration `migrations/create_vector_metadata_tables.sql`
- [✅] Add Italian regulation, tax rate, and template indexing support

**Success Criteria:**
- Pinecone integration working with 384-dimension embeddings
- Semantic search for Italian knowledge base functional
- Hybrid search combining semantic and keyword results
- Vector metadata tracking in PostgreSQL
- Comprehensive test coverage for all vector operations
- Search APIs available at `/api/v1/search/` endpoints
- Italian language support with multilingual embeddings

### 🔐 Enhanced Security
**Priority:** MEDIUM | **Estimated Time:** 2 hours | **Status:** [✅]

**Why Important:** Provides enterprise-grade security for API protection, threat detection, and compliance auditing.

**Implementation Tasks:**
- [✅] Create `app/core/security/api_key_rotation.py` - Complete API key lifecycle management
- [✅] Create `app/core/security/request_signing.py` - HMAC-SHA256 request signing system
- [✅] Create `app/core/security/audit_logger.py` - Comprehensive security audit logging
- [✅] Create `app/core/security/security_monitor.py` - Real-time threat detection and response
- [✅] Create `app/api/v1/security.py` - Security management API endpoints
- [✅] Create `app/core/middleware/security_middleware.py` - Security monitoring middleware
- [✅] Create comprehensive tests in `tests/core/security/test_security_system.py`
- [✅] Update API router to include security endpoints
- [✅] Create security module initialization and exports

**Success Criteria:**
- API key rotation with 30-day lifecycle and 7-day grace period
- HMAC-SHA256 request signing with timestamp validation
- Complete security audit logging for GDPR compliance
- Real-time threat detection (brute force, API abuse, signature failures)  
- Automated response actions (blocking, rate limiting, alerting)
- Security monitoring dashboard and statistics
- Comprehensive API endpoints for security management
- Integration with existing authentication and payment systems
- Bot detection and suspicious activity monitoring
- Compliance reporting for audit purposes

### 📈 Performance Optimization
**Priority:** MEDIUM | **Estimated Time:** 2 hours | **Status:** [✅]

**Why Important:** Provides enterprise-grade performance optimization for reduced costs, improved user experience, and better scalability.

**Implementation Tasks:**
- [✅] Create `app/core/performance/database_optimizer.py` - Database query optimization and monitoring
- [✅] Create `app/core/performance/response_compressor.py` - Response compression (Gzip/Brotli) with content minification
- [✅] Create `app/core/performance/performance_monitor.py` - Real-time performance monitoring with alerts
- [✅] Create `app/core/performance/cdn_integration.py` - CDN management for asset optimization
- [✅] Create `app/core/middleware/performance_middleware.py` - Performance monitoring middleware
- [✅] Create `app/api/v1/performance.py` - Performance management API endpoints
- [✅] Create comprehensive tests in `tests/core/performance/test_performance_system.py`
- [✅] Update API router to include performance endpoints
- [✅] Create performance optimization module initialization

**Success Criteria:**
- Database query optimization with monitoring and index recommendations
- Response compression (Gzip/Brotli) with 60%+ bandwidth savings
- Real-time performance monitoring with alerts and metrics tracking
- CDN integration for asset optimization and regional delivery
- Performance middleware for automatic request optimization
- Comprehensive API endpoints for performance management
- Extensive test coverage for all performance components
- Integration with existing systems and middleware

---

## 📋 Priority 4: Nice to Have (Future)

### 📱 Mobile API Enhancements
**Priority:** LOW | **Estimated Time:** 2 hours | **Status:** [ ]

### 🎨 Admin Dashboard
**Priority:** LOW | **Estimated Time:** 3 hours | **Status:** [ ]

### 🔄 Multi-language Support
**Priority:** LOW | **Estimated Time:** 4 hours | **Status:** [ ]

---

## 📊 Progress Tracking

### Week 1 Target: Priority 1 Complete
- **LLM Abstraction:** [✅] 
- **Caching Foundation:** [✅]
- **Query Anonymization:** [✅]
- **Cost Tracking:** [✅]

### Week 2 Target: Priority 2 Complete
- **Payment Integration:** [✅]
- **Italian Knowledge:** [✅]

### Week 3-4 Target: Production Ready
- **Vector Database:** [✅]
- **Enhanced Security:** [✅]
- **Performance Optimization:** [✅]

---

## 🎯 Success Metrics

### Technical Metrics
- [ ] API response time < 500ms (P95)
- [ ] Cache hit rate > 80%
- [ ] Test coverage > 80%
- [ ] Zero critical security vulnerabilities

### Business Metrics  
- [ ] API cost < €2/user/month
- [ ] System uptime > 99.5%
- [ ] User satisfaction > 4.5/5
- [ ] GDPR compliance verified

---

## 🚨 Risk Mitigation

### High Risk Items
- [✅] **Provider Outage:** Multi-provider fallback implemented (OpenAI + Anthropic with cost-based routing)
- [✅] **Cost Overrun:** Real-time monitoring and circuit breakers (Usage tracking + cost-based rate limiting)
- [✅] **GDPR Violation:** Automated PII detection and audit trails (Query anonymization + privacy middleware)
- [✅] **Security Breach:** Regular security audits and monitoring (Enhanced security system + pre-commit checks)

### Contingency Plans
- [✅] Emergency provider switching procedure documented (LLM routing with failover)
- [✅] Cost circuit breaker thresholds configured (Cost-based rate limiting middleware)
- [✅] Incident response playbook created (Complete playbook with environment-based configuration)
- [✅] Legal compliance review process established (GDPR compliance scoring + audit trails)

---

## 🎉 PROJECT STATUS: PRODUCTION READY

### ✅ **All Priority 1-3 Tasks Completed:**
- **Week 1:** LLM Abstraction, Caching, Privacy, Cost Tracking ✅
- **Week 2:** Payment Integration, Italian Knowledge Base ✅  
- **Week 3-4:** Vector DB, Enhanced Security, Performance Optimization ✅
- **Security:** Comprehensive sensitive data protection system ✅

### 🚀 **Ready for €25k ARR Target:**
- Cost-optimized LLM routing (targeting <€2/user/month) ✅
- Complete payment system (€69/month subscriptions) ✅
- Italian tax/legal knowledge integration ✅
- Enterprise-grade security and monitoring ✅
- Automated metrics reporting and alerting ✅

---

*Last Updated: 2025-01-30*  
*Project: PratikoAI → NormoAI Transformation*  
*Status: **PRODUCTION READY***  
*Developer: Solo Development (2-3 hours/day)*