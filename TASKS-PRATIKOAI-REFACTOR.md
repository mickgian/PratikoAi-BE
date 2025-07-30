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
**Priority:** MEDIUM | **Estimated Time:** 3 hours | **Status:** [ ]

**Implementation Tasks:**
- [ ] Add Pinecone/Weaviate integration
- [ ] Implement hybrid search
- [ ] Create knowledge embeddings
- [ ] Add semantic search capabilities

### 🔐 Enhanced Security
**Priority:** MEDIUM | **Estimated Time:** 2 hours | **Status:** [ ]

**Implementation Tasks:**
- [ ] Add API key rotation
- [ ] Implement request signing
- [ ] Add audit logging
- [ ] Create security monitoring

### 📈 Performance Optimization
**Priority:** MEDIUM | **Estimated Time:** 2 hours | **Status:** [ ]

**Implementation Tasks:**
- [ ] Database query optimization
- [ ] Response compression
- [ ] CDN integration
- [ ] Load testing and optimization

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
- **Vector Database:** [ ]
- **Enhanced Security:** [ ]
- **Performance Optimization:** [ ]

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
- [ ] **Provider Outage:** Multi-provider fallback implemented
- [ ] **Cost Overrun:** Real-time monitoring and circuit breakers
- [ ] **GDPR Violation:** Automated PII detection and audit trails
- [ ] **Security Breach:** Regular security audits and monitoring

### Contingency Plans
- [ ] Emergency provider switching procedure documented
- [ ] Cost circuit breaker thresholds configured
- [ ] Incident response playbook created
- [ ] Legal compliance review process established

---

*Last Updated: 2025-01-29*  
*Project: PratikoAI → NormoAI Transformation*  
*Developer: Solo Development (2-3 hours/day)*