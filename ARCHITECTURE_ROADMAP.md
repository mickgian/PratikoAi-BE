# PratikoAi Backend - Development Roadmap

**Last Updated:** 2025-11-14
**Status:** Active Development
**Next Task ID:** DEV-92

---

## Overview

This roadmap tracks planned architectural improvements and enhancements for the PratikoAi backend system. Each task follows the DEV-XX numbering scheme matching our development workflow.

**Current Architecture:** See `docs/DATABASE_ARCHITECTURE.md` for detailed documentation of the production system.

**Recent Completed Work:**
- DEV-66: RSS feed setup and initial monitoring (2025-11-13)

**Deployment Timeline Estimates:**

📅 **Time to QA Environment (DEV-75):**
- **Optimistic (parallel work):** ~2-3 weeks (15 Nov - 6 Dic)
- **Conservative (sequential):** ~3-4 weeks (15 Nov - 10 Dic)
- **Prerequisites:** DEV-71, DEV-69, DEV-74, DEV-70, DEV-68...
- **Critical path:** 14 days (2.0 weeks)

📅 **Time to Preprod Environment (DEV-88):**
- **Optimistic:** ~2-4 weeks from now (15 Nov - 13 Dic)
- **Conservative:** ~3-5 weeks from now (15 Nov - 19 Dic)
- **Prerequisites:** Path to QA + DEV-74, DEV-72, DEV-87
- **Critical path:** 14 days (2.0 weeks)

📅 **Time to Production Environment (DEV-90):**
- **Optimistic:** ~3-4.5 weeks from now (15 Nov - 17 Dic)
- **Conservative:** ~4-8 weeks from now (15 Nov - 7 Gen)
- **Prerequisites:** Path to Preprod + DEV-72, DEV-87, DEV-88
- **Note:** Production launch requires full GDPR compliance and payment system validation

**Key Dependencies:**
- ⚠️ **DEV-72** - Implement Expert Feedback System: Blocks QA deployment (longest task)
- ⚠️ **GDPR Audits** - DEV-74, DEV-89, DEV-91: Required before each environment launch

---

## Development Standards

**All tasks in this roadmap must follow these requirements:**

### Test-Driven Development (TDD)
- **Write tests FIRST, then implement features**
- Follow the Red-Green-Refactor cycle:
  1. 🔴 Write failing test
  2. 🟢 Write minimal code to pass test
  3. 🔵 Refactor while keeping tests green

### Code Coverage Requirements
- **Minimum coverage:** ≥69.5% (configured in `pyproject.toml`)
- **Pre-commit enforcement:** Commits will be blocked if coverage falls below threshold
- **Test command:** `uv run pytest --cov=app --cov-report=html`
- **Coverage report:** Generated to `htmlcov/index.html`

### Code Quality & Style
- **Linting:** All code must pass Ruff linter checks
  - Ruff replaces: `flake8`, `pylint`, `isort`, `pyupgrade`, `black`
  - Run: `uv run ruff check . --fix`
- **Formatting:** Use Ruff formatter (enforces consistent style)
  - Run: `uv run ruff format .`
- **Type Hints:** Add type hints to all new functions
  - Checked by MyPy: `uv run mypy app/`
  - Start with function signatures, gradually increase strictness
- **Import Management:** Unused imports automatically removed by Ruff
- **Commented Code:** Eradicate commented-out code (detected by Ruff ERA rules)
- **Pre-commit Hooks:** All checks run automatically before commits
  - Ruff linter + formatter
  - MyPy type checker
  - Tests with coverage
  - Security checks
- **Manual Quality Check:** Run before creating PRs:
  ```bash
  ./scripts/check_code.sh          # Run all checks
  ./scripts/check_code.sh --fix    # Auto-fix issues
  ./scripts/check_code.sh --no-test # Skip tests (faster)
  ```

### Quality Commands Reference
```bash
# Fix all auto-fixable issues (run before commit)
uv run ruff check . --fix
uv run ruff format .

# Type check (non-blocking warnings)
uv run mypy app/

# Run all checks + tests
./scripts/check_code.sh

# Fix and format in one command
./scripts/check_code.sh --fix
```

### Why These Standards?
- **Prevent compilation errors** - MyPy catches type errors before runtime
- **Eliminate unused imports** - Ruff automatically removes them
- **Consistent code style** - Ruff formatter enforces uniform formatting
- **Catch bugs early** - Ruff detects common Python anti-patterns
- **Save commit time** - Pre-commit hooks prevent bad code from being committed
- **Code quality metrics** - Configured in `pyproject.toml` with detailed comments

---

## Q1 2025 (January - March)

### DEV-67: Migrate FAQ Embeddings from Pinecone to pgvector
**Priority:** HIGH | **Effort:** 3-5 days (with Claude Code) | **Dependencies:** None

**Problem:**
FAQ/Golden set embeddings currently use Pinecone (`app/orchestrators/golden.py:1197`), but main knowledge base uses pgvector. Dual systems add complexity ($150-330/month extra cost) and operational overhead.

**Implementation Tasks:**

**Phase 1: Schema & Migration Prep**
- [ ] Create `faq_embeddings` table in PostgreSQL
  ```sql
  CREATE TABLE faq_embeddings (
      id SERIAL PRIMARY KEY,
      faq_id TEXT UNIQUE NOT NULL,
      question TEXT NOT NULL,
      answer TEXT NOT NULL,
      embedding vector(1536),
      metadata JSONB,
      category TEXT,
      quality_score FLOAT,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ DEFAULT NOW()
  );
  ```
- [ ] Create index: `CREATE INDEX idx_faq_embedding_ivfflat ON faq_embeddings USING ivfflat (embedding vector_cosine_ops);`
- [ ] Create Alembic migration: `alembic revision -m "add_faq_embeddings_table"`
- [ ] Export existing FAQ embeddings from Pinecone (backup)

**Phase 2: Code Refactoring**
- [ ] Create `app/services/faq_vector_service.py` (pgvector-based FAQ storage/retrieval)
- [ ] Refactor `app/orchestrators/golden.py` step_131 to use new FAQ service
- [ ] Replace `EmbeddingManager.update_pinecone_embeddings()` calls with pgvector inserts
- [ ] Update FAQ lookup queries to use `faq_embeddings` table

**Phase 3: Testing & Migration**
- [ ] Write tests: `tests/services/test_faq_vector_service.py`
- [ ] Migrate existing FAQs from Pinecone to PostgreSQL (one-time script)
- [ ] Feature flag: `USE_PINECONE_FOR_FAQS` (default: False, fallback to Pinecone if needed)
- [ ] Deploy to QA environment, test FAQ hit rate ≥70%

**Phase 4: Coverage Improvement (CRITICAL)**
- [ ] **IMPORTANT:** Current test coverage is ~4%, target is ≥69.5% (configured in `pyproject.toml`)
- [ ] Write comprehensive unit tests across the codebase to reach 69.5% threshold
- [ ] Focus areas for test coverage:
  - [ ] `app/services/*` - All service layer modules
  - [ ] `app/orchestrators/*` - LangGraph orchestration logic
  - [ ] `app/api/v1/*` - API endpoint handlers
  - [ ] `app/core/*` - Core utilities and helpers
  - [ ] `app/models/*` - Database models and schemas
- [ ] Run `uv run pytest --cov=app --cov-report=html` to verify coverage
- [ ] Ensure pre-commit hook passes (blocks commits if coverage < 69.5%)
- [ ] **Note:** This should ideally be a separate task, but included here to unblock development

**Acceptance Criteria:**
- ✅ All FAQs stored in PostgreSQL `faq_embeddings` table
- ✅ `app/orchestrators/golden.py` no longer calls Pinecone
- ✅ FAQ hit rate maintains ≥70% performance
- ✅ No Pinecone API calls in production logs
- ✅ Cost savings: $150-330/month eliminated
- ✅ **Test coverage ≥69.5%** (matching frontend jest.config.js threshold)
- ✅ Pre-commit hooks pass successfully

**Rollback Plan:**
- No rollback plan, Pinecone is not used and we never hit production yet

---

### DEV-68: Remove Pinecone Integration Code
**Priority:** HIGH | **Effort:** 1-2 days (with Claude Code) | **Dependencies:** DEV-67 ✅ (must complete first)

**Problem:**
Pinecone integration code (600+ lines) adds maintenance burden and confuses developers. After FAQ migration (DEV-67), all Pinecone code is dead code.

**Implementation Tasks:**

**Week 1: Code Removal**
- [ ] Delete `app/services/vector_providers/pinecone_provider.py` (349 lines)
- [ ] Delete `app/services/vector_config.py` (205 lines)
- [ ] Delete `app/services/vector_provider_factory.py`
- [ ] Delete `app/services/embedding_management.py` (Pinecone-based)
- [ ] Delete `app/services/hybrid_search_engine.py` (Pinecone-based)
- [ ] Delete `app/services/query_expansion_service.py`
- [ ] Delete `app/services/semantic_faq_matcher.py`
- [ ] Delete `app/services/context_builder.py` (check if used elsewhere first!)
- [ ] Remove from `requirements.txt` or `pyproject.toml`: `pinecone-client>=2.2.0`
- [ ] Delete tests: `tests/test_vector_search.py`
- [ ] Remove Pinecone env vars from `.env.example`:
  - `PINECONE_API_KEY`
  - `PINECONE_ENVIRONMENT`
  - `PINECONE_INDEX_NAME`
- [ ] Update `app/core/config.py` - remove Pinecone settings
- [ ] Search codebase for "pinecone" (case-insensitive) and clean up all references

**Documentation Cleanup:**
- [ ] Delete `docs/pinecone-guardrails.md` (262 lines)
- [ ] Delete `docs/architecture/vector-search.md` (261 lines)
- [ ] Update README.md to remove Pinecone references
- [ ] Update `docs/DATABASE_ARCHITECTURE.md` if needed

**Acceptance Criteria:**
- ✅ `grep -ri "pinecone" .` returns no results (excluding git history)
- ✅ All tests pass without Pinecone dependencies
- ✅ Production deployment successful with no errors
- ✅ No Pinecone costs on billing dashboard

**Validation:**
- [ ] Run full test suite: `pytest`
- [ ] Deploy to QA, test FAQ lookup functionality

---

### DEV-69: Expand RSS Feed Sources Beyond Agenzia delle Entrate
**Priority:** HIGH | **Effort:** 1 week (with Claude Code) | **Dependencies:** DEV-66 ✅ (RSS infrastructure complete)

**Problem:**
Currently only 2 RSS feeds configured (both from Agenzia delle Entrate). Missing coverage of other critical Italian regulatory sources.

**Target Sources to Add:**
- **INPS** (Istituto Nazionale Previdenza Sociale) - Social security and pension updates
- **Ministero del Lavoro** - Employment and labor law regulations
- **Corte di Cassazione** - Supreme Court rulings (tax/employment sections)
- **Ministero dell'Economia e delle Finanze (MEF)** - Financial regulations
- **INAIL** (Istituto Nazionale Assicurazione Infortuni sul Lavoro) - Workplace injury insurance
- **Gazzetta Ufficiale** - Official government gazette (filtered sections)

**Implementation Tasks:**

**Week 1: Feed Discovery & Configuration**
- [ ] Research RSS/Atom feed URLs for each target source
- [ ] Verify feed quality (update frequency, content completeness)
- [ ] Add new feed entries to `feed_status` table:
  ```sql
  INSERT INTO feed_status (source_name, feed_url, is_active, last_check_at)
  VALUES
    ('INPS', 'https://www.inps.it/feed/rss/...', true, NOW()),
    ('Ministero del Lavoro', 'https://www.lavoro.gov.it/rss/...', true, NOW()),
    -- ... etc
  ;
  ```
- [ ] Create source-specific parsers in `app/ingest/parsers/` if needed (each source may have different XML structure)

**Week 2: Monitoring & Quality Control**
- [ ] Add feed health metrics to monitoring (response time, item counts, parse errors)
- [ ] Test ingestion pipeline with new feeds (verify documents appear in `knowledge_items`)
- [ ] Implement duplicate detection (same regulation published by multiple sources)
- [ ] Add feed-specific quality scoring (some sources have higher authority)

**Week 3: Deployment & Testing**
- [ ] Deploy to QA environment
- [ ] Monitor ingestion for 1 week (verify no parsing errors)
- [ ] Validate document quality (check `junk` rate for new sources)
- [ ] Deploy to production with all feeds enabled

**Acceptance Criteria:**
- ✅ At least 8 RSS feeds configured (2 existing + 6 new)
- ✅ All feeds successfully ingested (>0 documents from each source)
- ✅ Feed health monitoring operational (alerts on feed failures)
- ✅ Duplicate detection working (same doc from multiple sources = 1 entry)
- ✅ Document quality maintained (junk rate <15%)

**Expected Impact:**
- 5-10x increase in regulatory document coverage
- Better coverage of employment law, social security, court rulings
- More comprehensive answers for users

---

### DEV-70: Daily RSS Collection Email Report
**Priority:** MEDIUM | **Effort:** 2-3 days (with Claude Code) | **Dependencies:** DEV-69 ✅ (RSS feeds expanded)

**Problem:**
No visibility into daily RSS feed ingestion. Team doesn't know if feeds are working, how many documents were added, or if there are errors.

**Solution:**
Automated daily email report showing RSS collection activity and DB additions.

**Report Contents:**

**1. Daily Summary**
- Total documents collected (last 24 hours)
- Total documents added to DB (after deduplication)
- Duplicate rate (% of collected docs already in DB)
- Error rate (% of feeds with parsing errors)

**2. Per-Feed Breakdown**
- Source name (e.g., "Agenzia delle Entrate - Normativa")
- Documents collected
- Documents added to DB
- Parse errors (if any)
- Last successful check time

**3. Data Quality Metrics**
- Average text quality score for new documents
- Junk detection rate (% marked as junk)
- Top 5 new documents by title (preview)

**4. Alerts**
- Feeds down (HTTP errors, timeouts)
- Feeds stale (no new items in 7+ days)
- High junk rate (>25% for a specific feed)

**Implementation Tasks:**

**Week 1: Email Service + Report Generation**
- [ ] Add email service to config (use AWS SES or SendGrid)
- [ ] Create `app/services/rss_report_service.py`:
  ```python
  class RSSReportService:
      async def generate_daily_report(self, date: datetime.date) -> Dict:
          # Query feed_status + knowledge_items for last 24 hours
          # Aggregate stats per feed
          # Generate HTML email template
  ```
- [ ] Create HTML email template: `templates/email/daily_rss_report.html`
- [ ] Add cron job to `docker-compose.yml` or use Celery Beat:
  ```yaml
  rss_reporter:
    image: pratikoai-backend:latest
    command: python -m app.jobs.daily_rss_report
    environment:
      SCHEDULE: "0 8 * * *"  # 8am daily
  ```
- [ ] Write tests: `tests/test_rss_report_service.py`

**Acceptance Criteria:**
- ✅ Daily email sent at 8am (configurable time)
- ✅ Email includes all report sections (summary, per-feed, quality, alerts)
- ✅ Email recipients configurable in environment variables
- ✅ HTML email renders correctly in Gmail/Outlook
- ✅ Email sent even if no new documents (shows "0 documents collected")

**Recipients Configuration:**
```env
RSS_REPORT_RECIPIENTS=dev-team@pratikoai.com,stakeholders@pratikoai.com
RSS_REPORT_TIME=08:00  # Daily at 8am
```

**Expected Impact:**
- Proactive feed failure detection (team notified within 24 hours)
- Better understanding of knowledge base growth
- Easier to identify low-quality feed sources

---

### DEV-71: Disable Emoji in LLM Responses
**Priority:** MEDIUM | **Effort:** 1-2 days (with Claude Code) | **Dependencies:** None

**Problem:**
LLMs (especially ChatGPT) frequently include emojis in responses (✅, 📊, 💡, etc.), which looks unprofessional for Italian tax and legal advisory context. Users expect formal, professional language without decorative elements.

**Solution:**
Add explicit instruction to system prompts to disable emoji usage. Update all prompt templates.

**Implementation Tasks:**

**Day 1: Prompt Updates**
- [ ] Update `SYSTEM_PROMPT` in `app/core/langgraph/prompt_policy.py`:
  ```python
  SYSTEM_PROMPT = """You are PratikoAI, an expert Italian tax and employment law assistant.

  IMPORTANT FORMATTING RULES:
  - Do NOT use emojis in your responses
  - Use professional, formal Italian language
  - Use bullet points (•) or numbers (1., 2.) instead of emoji bullets
  - Use text labels instead of emoji indicators (e.g., "ATTENZIONE:" instead of ⚠️)
  """
  ```
- [ ] Update all domain-specific prompts in `app/services/prompt_template_manager.py`:
  - Fiscal domain prompt
  - Employment law prompt
  - Corporate law prompt
  - CCNL domain prompt
- [ ] Update FAQ generation prompt in `app/services/auto_faq_generator.py`
- [ ] Update expert feedback prompts if LLM-generated

**Day 2: Testing & Validation**
- [ ] Test 50 diverse queries and verify no emojis in responses
- [ ] Check streaming responses (emojis sometimes appear in chunks)
- [ ] Test with different LLM providers (OpenAI, Claude fallback)
- [ ] Document emoji-free response requirement in `docs/PROMPT_ENGINEERING.md`

**Acceptance Criteria:**
- ✅ No emojis in LLM responses across 100 test queries
- ✅ Professional tone maintained in all responses
- ✅ Bullet points and numbered lists work correctly
- ✅ All prompt templates updated
- ✅ Documentation updated

**Testing Queries:**
```
- "Quali sono le scadenze fiscali di gennaio?" (Tax deadlines)
- "Come si calcola il TFR?" (Severance pay calculation)
- "Dimmi le novità sulle detrazioni fiscali" (Tax deduction updates)
```

---

### DEV-72: Implement Expert Feedback System
**Priority:** HIGH | **Effort:** 2 weeks (with Claude Code) | **Dependencies:** None

**Frontend Integration:**
This backend task is linked to **DEV-004** in frontend roadmap:
- **Frontend Task:** DEV-004: Implement Super Users Feedback on Answers (Expert Feedback System)
- **Location:** `/Users/micky/WebstormProjects/PratikoAiWebApp/ARCHITECTURE_ROADMAP.md`
- **Coordination Required:** Backend APIs must be completed BEFORE frontend implementation
- **API Endpoints:** Frontend will consume `/api/v1/feedback/*` endpoints created in this task

**Problem:**
Expert feedback system is designed in architecture diagram (steps S113-S131) but NOT fully connected. When experts provide feedback, it should:
1. Validate expert credentials and trust score
2. Collect feedback with Italian categorization
3. Update expert metrics
4. Propose Golden Set candidates from high-quality feedback
5. Auto-approve FAQs from trusted experts

**Current State:**
- ✅ `app/services/expert_feedback_collector.py` exists
- ✅ `app/models/quality_analysis.py` has expert models
- ✅ UI feedback buttons designed
- ❌ NOT connected to Golden Set updater
- ❌ Auto-approval logic NOT implemented
- ❌ Trust score validation NOT enforced

**Solution:**
Complete integration following architecture diagram (S113-S131).

**Implementation Tasks:**

**Week 1: Expert Validation & Feedback Collection**
- [ ] Implement S113-S119: Feedback collection pipeline
  - Create `app/api/v1/feedback.py` with endpoints:
    - `POST /api/v1/feedback/faq` (S117)
    - `POST /api/v1/feedback/knowledge` (S118)
  - Update `expert_feedback_collector.py` to handle both types
- [ ] Implement S120-S121: Expert credential validation
  ```python
  class ExpertValidator:
      def validate_credentials(self, user_id: UUID) -> ExpertProfile:
          # Check expert_profiles table
          # Verify is_active and is_verified
          # Return expert with trust_score

      def check_trust_threshold(self, trust_score: float) -> bool:
          # S121: Trust score at least 0.7?
          return trust_score >= 0.7
  ```
- [ ] Implement S122-S124: Feedback processing
  - S122: Reject feedback if trust_score < 0.7
  - S123: Create ExpertFeedback record
  - S124: Update expert metrics (accuracy, feedback_count)
- [ ] Implement S125: Cache feedback (1h TTL)
  ```python
  await cache_service.set(
      f"expert_feedback:{feedback_id}",
      feedback_data,
      ttl=3600  # 1 hour
  )
  ```

**Week 2: Golden Set Integration & Auto-Approval**
- [ ] Implement S126-S127: Golden Set candidate proposal
  ```python
  class GoldenSetUpdater:
      async def propose_candidate_from_expert_feedback(
          self,
          feedback_id: UUID
      ) -> FAQCandidate:
          # Extract question + answer from feedback
          # Create FAQ candidate entry
          # Link to expert who provided it
  ```
- [ ] Implement S128: Auto-approval logic
  ```python
  async def determine_action(self, candidate: FAQCandidate) -> Action:
      if candidate.expert_trust_score >= 0.9:
          return Action.AUTO_APPROVE
      elif candidate.expert_trust_score >= 0.7:
          return Action.QUEUE_FOR_REVIEW
      else:
          return Action.REJECT
  ```
- [ ] Implement S129-S131: Golden Set publishing
  - S129: Publish or update versioned entry in Golden Set
  - S130: Invalidate FAQ cache by id or signature
  - S131: Update vector embeddings for new/updated FAQs
- [ ] Create admin UI endpoint: `GET /api/v1/admin/faq-candidates`
  - Show pending FAQs (trust_score 0.7-0.9)
  - Manual approve/reject buttons
  - Display expert info and trust score

**Database Schema Updates:**
```sql
CREATE TABLE expert_feedback (
    id UUID PRIMARY KEY,
    expert_id UUID REFERENCES expert_profiles(id) NOT NULL,
    conversation_id UUID REFERENCES conversations(id),
    feedback_type VARCHAR(20) NOT NULL,  -- 'correct', 'incomplete', 'wrong'
    feedback_text TEXT,
    suggested_answer TEXT,
    trust_score_at_time FLOAT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE faq_candidates (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    source VARCHAR(20) NOT NULL,  -- 'expert_feedback', 'auto_generated'
    expert_id UUID REFERENCES expert_profiles(id),
    expert_trust_score FLOAT,
    approval_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Acceptance Criteria:**
- ✅ Expert feedback collected via POST /api/v1/feedback/faq
- ✅ Trust score validation enforces 0.7 minimum threshold
- ✅ High-trust experts (≥0.9) trigger auto-approved FAQs
- ✅ Medium-trust experts (0.7-0.9) queue for manual review
- ✅ Expert metrics updated (accuracy, feedback count)
- ✅ Golden Set automatically updated with approved FAQs
- ✅ FAQ cache invalidated on updates
- ✅ Vector embeddings updated for new FAQs
- ✅ Admin dashboard shows pending candidates

**Expected Impact:**
- Faster FAQ creation (from days to seconds for trusted experts)
- Higher quality FAQs (expert-validated answers)
- Reduced manual work for content team
- Better coverage of user questions over time
- Continuous improvement from expert feedback loop

**Code Locations:**
- `app/api/v1/feedback.py` (NEW)
- `app/services/expert_feedback_collector.py` (UPDATE)
- `app/services/golden_set_updater.py` (NEW)
- `app/models/expert_feedback.py` (NEW)

**Testing:**
- [ ] Write tests: `tests/test_expert_feedback_system.py`
- [ ] Test with mock expert (trust_score = 0.95) → auto-approve
- [ ] Test with medium expert (trust_score = 0.75) → queue
- [ ] Test with low expert (trust_score = 0.5) → reject
- [ ] Verify Golden Set updates and cache invalidation

---

### DEV-74: GDPR Compliance Audit (QA Environment)
**Priority:** HIGH | **Effort:** 3-4 days (with Claude Code generating checklists/docs) | **Dependencies:** DEV-73 ✅ (QA environment live)

**Problem:**
Must ensure GDPR compliance before any production launch. QA environment is the first place to validate compliance features.

**Solution:**
Comprehensive GDPR compliance audit on QA environment to validate all required features.

**Audit Checklist:**

**1. Right to Access (Data Export)**
- [ ] Test user data export functionality
- [ ] Verify exported data includes all user information:
  - Personal information (name, email)
  - Conversation history
  - Document uploads
  - Feedback submissions
- [ ] Validate export format (JSON/PDF)
- [ ] Test export delivery (email or download link)
- [ ] Verify export completes within 30 days (GDPR requirement)

**2. Right to Erasure (Data Deletion)**
- [ ] Test user account deletion
- [ ] Verify complete data removal:
  - User profile deleted
  - Conversations deleted or anonymized
  - Document references removed
  - Personal data removed from logs
- [ ] Validate deletion completes within 30 days
- [ ] Test anonymization of historical data (if required for business)

**3. Consent Management**
- [ ] Verify cookie consent banner functionality
- [ ] Test opt-in/opt-out mechanisms
- [ ] Validate consent records are stored
- [ ] Test consent withdrawal functionality

**4. Data Retention Policies**
- [ ] Verify automatic data deletion after retention period
- [ ] Test conversation data retention (default: 90 days)
- [ ] Validate log data retention (default: 30 days)
- [ ] Test backup data retention policies

**5. Privacy by Design**
- [ ] Verify minimal data collection (only necessary data)
- [ ] Test data encryption at rest (PostgreSQL, Redis)
- [ ] Validate data encryption in transit (HTTPS/TLS)
- [ ] Test API authentication and authorization

**6. Cross-Border Data Transfers**
- [ ] Verify data storage location (EU servers for EU users)
- [ ] Validate data processing agreements with third parties
- [ ] Test data localization requirements

**7. Data Breach Notification**
- [ ] Document breach notification procedures
- [ ] Test breach detection mechanisms
- [ ] Verify breach notification timeline (72 hours)

**8. Documentation & Policies**
- [ ] Review and update Privacy Policy
- [ ] Review and update Cookie Policy
- [ ] Document data processing activities
- [ ] Create GDPR compliance checklist

**Implementation Tasks:**

**Week 1: Audit & Testing**
- [ ] Run through complete audit checklist on QA
- [ ] Document any missing features or issues
- [ ] Create tasks for GDPR gaps (if any found)
- [ ] Test with sample user data
- [ ] Validate all GDPR endpoints work correctly

**Acceptance Criteria:**
- ✅ All 8 audit categories pass on QA
- ✅ Data export works correctly
- ✅ Data deletion works completely
- ✅ Consent management functional
- ✅ Privacy policies up to date
- ✅ Documentation complete
- ✅ No GDPR compliance gaps identified

**Findings Documentation:**
- [ ] Create `docs/compliance/GDPR_AUDIT_QA.md` with findings
- [ ] List any compliance gaps discovered
- [ ] Create remediation tasks for gaps
- [ ] Document test results

**Reference Files:**
- `docs/GDPR_DATA_EXPORT.md` (existing)
- `docs/GDPR_DATA_DELETION.md` (existing)

---


### DEV-75: Deploy QA Environment (Hetzner VPS)
**Priority:** HIGH | **Effort:** 1 week (mostly waiting for Hetzner approval) | **Dependencies:** None

**⚠️ IMPORTANT:** Contact Hetzner support first - they have a strict onboarding process for new clients.

**Problem:**
Currently testing only in local Docker environment. No QA environment for integration testing, performance validation, or stakeholder demos before production deployment.

**Solution:**
Deploy complete PratikoAI backend to Hetzner VPS using existing docker-compose.yml configuration.

**Implementation Tasks:**

**Week 1: Hetzner Account & VPS Setup**
- [ ] **Contact Hetzner support** for account approval (can take 1-3 days)
- [ ] Create Hetzner account and verify identity
- [ ] Provision Hetzner CX21 VPS (2 vCPU, 4GB RAM, 40GB SSD)
  - Region: Germany (Falkenstein or Nuremberg)
  - OS: Ubuntu 22.04 LTS
  - Cost: ~€6.50/month (~$7/month)
- [ ] Configure SSH access with key-based authentication
- [ ] Set up firewall rules:
  - Allow: 22 (SSH), 80 (HTTP), 443 (HTTPS)
  - Allow: 8000 (API), 3000 (Grafana), 9090 (Prometheus) from your IP only
- [ ] Install Docker and Docker Compose on VPS

**Week 2: Deployment & Configuration**
- [ ] Copy docker-compose.yml to VPS
- [ ] Create `.env.qa` with QA-specific configuration:
  ```env
  APP_ENV=qa
  POSTGRES_USER=aifinance
  POSTGRES_PASSWORD=<generate-strong-password>
  POSTGRES_DB=aifinance
  OPENAI_API_KEY=<qa-api-key>
  LOG_LEVEL=DEBUG
  ALLOWED_ORIGINS=http://<qa-frontend-url>
  ```
- [ ] Deploy stack: `docker-compose --env-file .env.qa up -d`
- [ ] Run database migrations: `docker-compose exec app alembic upgrade head`
- [ ] Set up DNS: `api-qa.pratikoai.com` pointing to Hetzner VPS IP
- [ ] Configure SSL with Let's Encrypt (using Certbot or Caddy)
- [ ] Set up automated backups (Hetzner snapshots: ~€1/month)

**Acceptance Criteria:**
- ✅ QA environment accessible at `https://api-qa.pratikoai.com`
- ✅ All services running (PostgreSQL, Redis, Backend, Prometheus, Grafana)
- ✅ Database migrations run successfully
- ✅ All API endpoints responding (health check passes)
- ✅ Can query knowledge base and get responses
- ✅ Grafana accessible at `https://api-qa.pratikoai.com:3000`
- ✅ Automated daily backups configured

**Infrastructure Cost (QA):**
- Hetzner CX21 VPS: ~$7/month
- Snapshots/backups: ~$1/month
- **Total: ~$8/month**

**Post-Deployment Testing:**
- [ ] Verify RAG query responses match local environment
- [ ] Test RSS feed ingestion
- [ ] Validate cache behavior
- [ ] Performance testing (50 concurrent queries)
- [ ] Share QA URL with stakeholders for feedback

---

### DEV-76: Fix Cache Key + Add Semantic Layer
**Priority:** HIGH | **Effort:** 1 week (with Claude Code) | **Dependencies:** None

**Problem:**
Current Redis cache is **implemented but broken**. The cache key is TOO STRICT:

**Current cache key includes:**
```python
cache_key = sha256({
    query_hash,        # User question
    doc_hashes,        # ← PROBLEM: Changes if retrieved docs differ
    kb_epoch,          # ← PROBLEM: Invalidates on any KB update
    golden_epoch,
    ccnl_epoch,
    parser_version,
    model,
    temperature
})
```

**Why it fails:**
- Same question → Slightly different retrieved documents (order, top-14 vary) → Different `doc_hashes` → Cache miss
- Any KB update → All cache invalidated (aggressive invalidation)
- **Result:** Effective hit rate ~0-5% (not 20-30% as assumed)

**User observation:** "Same question from backend always calls LLM" ← Confirms cache is broken

**Solution (Two-Phase Fix):**

**Phase 1: Fix Current Cache Key (1 week)**
- Remove `doc_hashes` from cache key (too volatile)
- Keep `epochs` but make invalidation smarter (only invalidate if answer would actually change)
- Simplified key: `sha256(query_hash + model + temperature + kb_epoch)`
- Expected improvement: 0-5% → 20-30% hit rate

**Phase 2: Add Semantic Layer (1-2 weeks)**
- Add embedding similarity search for near-miss queries
- Expected improvement: 20-30% → 60-70% hit rate

**Implementation Tasks:**

**Phase 1: Fix Cache Key (Week 1)**
- [ ] **Audit current cache key generation** in `app/orchestrators/cache.py` Step 61
- [ ] **Remove `doc_hashes`** from cache key (causes 95%+ cache misses)
- [ ] **Simplify cache key** to: `sha256(query_hash + model + temperature + kb_epoch)`
- [ ] **Smarter epoch invalidation:**
  - Don't invalidate on every KB update
  - Only invalidate if the updated documents would affect cached answers
  - Implement "last_answer_affecting_update" timestamp
- [ ] **Add cache hit/miss logging** to understand actual hit rate
- [ ] **Test on QA:** Ask same question 10 times, verify cache hit after first call
- [ ] **Deploy to production:** Monitor hit rate (expect 20-30%)

**Phase 1 Acceptance Criteria:**
- ✅ Same question asked twice → Second call is cache hit (0% → 100% for identical queries)
- ✅ Cache hit rate: 0-5% → 20-30%
- ✅ Cache logs show "cache_hit" events in production
- ✅ No breaking changes (existing cache still works)

**Phase 2: Add Semantic Layer (Weeks 2-3)**
- [ ] Create `query_cache_embeddings` table:
  ```sql
  CREATE TABLE query_cache_embeddings (
      id SERIAL PRIMARY KEY,
      query_text TEXT NOT NULL,
      query_embedding vector(1536),
      cache_key TEXT NOT NULL,  -- Links to Redis hash
      cached_at TIMESTAMPTZ DEFAULT NOW(),
      hits INTEGER DEFAULT 0,
      last_accessed_at TIMESTAMPTZ DEFAULT NOW()
  );
  CREATE INDEX idx_qce_embedding_ivfflat
  ON query_cache_embeddings
  USING ivfflat (query_embedding vector_cosine_ops);
  ```
- [ ] Implement `app/services/semantic_cache_service.py`:
  - `async def find_similar_cached_queries(query_embedding, threshold=0.95, max_age_hours=1)`
  - `async def store_query_cache_entry(query_text, query_embedding, cache_key)`
- [ ] Update `app/orchestrators/cache.py` Step 62:
  1. Check Redis for exact hash match (Phase 1 key)
  2. **IF MISS:** Generate query embedding, search `query_cache_embeddings`
  3. **IF SIMILAR FOUND (≥0.95):** Use that cache_key
  4. **IF NO MATCH:** Proceed to RAG, store new entry
- [ ] Write tests: `tests/test_semantic_cache.py`
- [ ] A/B test: Monitor hit rate improvement
- [ ] Tune similarity threshold (0.90, 0.95, 0.98)

**Phase 2 Acceptance Criteria:**
- ✅ Total cache hit rate >60% (hash-based + semantic)
- ✅ Paraphrase queries hit cache: "come calcolare IVA" → "calcolo dell'IVA" (cache hit)
- ✅ Lookup latency <15ms for semantic search (p95)
- ✅ Backward compatible with Phase 1 cache

**Expected Impact:**
- **Before DEV-77:** 0-5% hit rate (broken cache)
- **After Phase 1:** 20-30% hit rate (fixed hash-based cache)
- **After Phase 2:** 60-70% hit rate (hash + semantic)
- **Cost savings:** At 60% hit rate, save $1,500-1,800/month in LLM costs (at 500 users × 50 queries/day)

---

### DEV-77: Implement Prometheus + Grafana Monitoring
**Priority:** HIGH | **Effort:** 1-2 weeks (dashboards already in docker-compose.yml) | **Dependencies:** None

**Problem:**
Current monitoring relies on basic logs and periodic REST API metrics calls. No real-time visibility into RAG performance,
cache hit rates, or automatic alerting on degradation.

**Solution:**
Industry-standard observability stack: Prometheus (metrics collection) + Grafana (visualization/alerting)

**Implementation Tasks:**

**Phase 1: Prometheus Setup**
- [ ] Add Prometheus to `docker-compose.yml`:
  ```yaml
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
  ```
- [ ] Create `prometheus.yml` configuration (scrape targets)
- [ ] Add `prometheus-fastapi-instrumentator` to `requirements.txt`
- [ ] Instrument FastAPI app: `app/main.py` with Prometheus metrics
- [ ] Add custom metrics to `app/retrieval/postgres_retriever.py`:
  - `rag_query_duration_seconds` (histogram)
  - `rag_retrieval_results_count` (gauge)
  - `rag_cache_hit_total` / `rag_cache_miss_total` (counters)
- [ ] Add PostgreSQL exporter to docker-compose (postgres_exporter)
- [ ] Add Redis exporter to docker-compose (already exists at port 9121)

**Phase 2: Grafana Dashboards**
- [ ] Sign up for Grafana Cloud Free Tier (or self-host)
- [ ] Configure Prometheus as data source in Grafana
- [ ] Create **Dashboard 1: RAG Performance**
  - Query latency over time (p50, p95, p99 lines)
  - Cache hit rate gauge (target: >60%)
  - Retrieval results distribution histogram
  - Hybrid search component breakdown (FTS vs Vector vs Recency)
- [ ] Create **Dashboard 2: System Health**
  - PostgreSQL connection pool usage
  - Redis memory usage trend
  - API request rate (requests/second by endpoint)
  - Error rate by endpoint (4xx, 5xx)
- [ ] Create **Dashboard 3: Cost & Usage**
  - LLM token usage over time (input vs output)
  - Estimated API cost per hour/day/month
  - Document ingestion rate
- [ ] Create **Dashboard 4: Data Quality**
  - Document count growth over time
  - Junk chunk rate trend
  - Average text quality score

**Phase 3: Alerting**
- [ ] Define alert rules in Grafana:
  - **Critical:** `rag_query_duration_seconds{quantile="0.95"} > 2.0 for 5min` → "RAG latency degraded"
  - **Critical:** `postgres_active_connections > 90 for 2min` → "PostgreSQL connection pool exhausted"
  - **Critical:** `api_error_rate > 0.05 for 3min` → "High API error rate (>5%)"
  - **Warning:** `rag_cache_hit_rate < 0.40 for 10min` → "Cache hit rate below target"
  - **Warning:** `llm_api_duration_seconds{quantile="0.95"} > 10.0 for 5min` → "LLM API slow"
- [ ] Set up Slack webhook integration
- [ ] Test alert firing and notification delivery

**Phase 4: Testing & Documentation**
- [ ] Load testing to validate metrics accuracy
- [ ] Document dashboard usage: `docs/monitoring/GRAFANA_DASHBOARDS.md`
- [ ] Document alert response procedures: `docs/monitoring/ALERT_RUNBOOK.md`
- [ ] Train team on using Grafana for debugging

**Acceptance Criteria:**
- ✅ Prometheus scraping metrics from FastAPI, PostgreSQL, Redis
- ✅ 4 Grafana dashboards live with real-time data
- ✅ Alert rules configured and tested (Slack notifications working)
- ✅ Documentation complete
- ✅ Team trained on dashboard usage

**Cost:**
- Grafana Cloud Free Tier: **$0/month** (14-day retention, 10K metrics)
- Self-hosted: ~$10-30/month (EC2 t3.small)

**Deployment:**
- Start with Grafana Cloud Free Tier for rapid deployment
- Migrate to self-hosted if >14 day retention needed

---

### DEV-78: Cross-Encoder Reranking
**Priority:** MEDIUM | **Effort:** 1 week (with Claude Code) | **Dependencies:** None

**Problem:**
Hybrid retrieval returns top-14 candidates, but ranking may not be optimal. Adding a reranking stage can improve precision by 10-15%.

**Solution:**
Two-stage retrieval:
1. **Stage 1 (Broad):** Hybrid retrieval → top 30 candidates (FTS + Vector + Recency)
2. **Stage 2 (Precision):** Cross-encoder reranks top 30 → final top 14

**Implementation Tasks:**

**Week 1: Model Selection**
- [ ] Evaluate cross-encoder models:
  - `cross-encoder/ms-marco-MiniLM-L-12-v2` (general English)
  - `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilingual)
  - Fine-tune on Italian financial/legal queries (ideal, but optional)
- [ ] Benchmark latency: Target <100ms for reranking 30 candidates
- [ ] Choose model based on Italian performance + latency

**Week 2: Implementation**
- [ ] Add `sentence-transformers` to `requirements.txt`
- [ ] Create `app/retrieval/reranker.py`:
  ```python
  from sentence_transformers import CrossEncoder

  class CrossEncoderReranker:
      def __init__(self, model_name='cross-encoder/ms-marco-MiniLM-L-12-v2'):
          self.model = CrossEncoder(model_name)

      async def rerank(self, query: str, candidates: List[Dict], top_k: int = 14) -> List[Dict]:
          scores = self.model.predict([(query, c['chunk_text']) for c in candidates])
          ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
          return [c for c, _ in ranked[:top_k]]
  ```
- [ ] Update `app/retrieval/postgres_retriever.py`:
  - Change `hybrid_retrieve()` to return top 30 (configurable)
  - Add optional `rerank=True` parameter
  - Call `CrossEncoderReranker.rerank()` if enabled

**Week 3: Testing & A/B**
- [ ] Write tests: `tests/test_reranker.py`
- [ ] Create test set: 50 Italian queries with manually labeled relevance
- [ ] Measure precision@14 before/after reranking
- [ ] A/B test: 50% with reranking, 50% without
- [ ] Monitor latency impact (should be +50-100ms max)

**Week 4: Tuning & Deployment**
- [ ] Optimize: Load model once, reuse across requests
- [ ] Consider GPU inference if latency >200ms
- [ ] Feature flag: `ENABLE_CROSS_ENCODER_RERANKING` (default: False)
- [ ] Deploy to QA, then production with flag enabled

**Acceptance Criteria:**
- ✅ Precision@14 improvement: +10-15%
- ✅ Latency increase: <100ms (p95)
- ✅ Fallback to hybrid-only if reranking fails
- ✅ A/B test shows statistically significant quality improvement

**Expected Impact:**
- Precision@14: 75% → 85-90%
- Latency: <100ms → <200ms (still under 300ms target)
- User satisfaction: Higher quality results

---

## Q2 2025 (April - June)

### DEV-79: Upgrade to HNSW Index
**Priority:** MEDIUM | **Effort:** 3-5 days (with Claude Code) | **Dependencies:** None

**Problem:**
Current IVFFlat index has 85-90% recall. HNSW (Hierarchical Navigable Small World) provides 90-95% recall and 20-30% faster queries.

**Implementation:**
```sql
-- Drop existing IVFFlat
DROP INDEX idx_kc_embedding_ivfflat_1536;

-- Create HNSW (requires pgvector 0.5.0+)
CREATE INDEX CONCURRENTLY idx_kc_embedding_hnsw_1536
ON knowledge_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Tasks:**
- [ ] Test HNSW build time on QA (expect 2-4 hours for 500K vectors)
- [ ] Benchmark query performance (HNSW vs IVFFlat)
- [ ] Plan production migration: Create index CONCURRENTLY during low-traffic window
- [ ] Document rollback procedure

**Acceptance Criteria:**
- ✅ Vector search latency reduced by 20-30% (30-40ms → 20-30ms)
- ✅ Recall improved from 85-90% to 90-95%
- ✅ Zero downtime during migration

---

### DEV-80: Italian Financial Dictionary
**Priority:** LOW | **Effort:** 1 week (with Claude Code generating dictionary) | **Dependencies:** None

**Problem:**
PostgreSQL `italian` dictionary handles general Italian well, but misses domain-specific acronyms and synonyms common in tax/legal documents.

**Solution:**
Custom Italian financial dictionary with synonym mappings:

**Tasks:**
- [ ] Compile synonym list (100-200 terms):
  - "IVA" → "imposta sul valore aggiunto"
  - "IRPEF" → "imposta sul reddito delle persone fisiche"
  - "cedolare secca" → "regime di tassazione sostitutiva"
- [ ] Create PostgreSQL synonym dictionary:
  ```sql
  CREATE TEXT SEARCH DICTIONARY italian_financial (
      TEMPLATE = synonym,
      SYNONYMS = italian_financial_synonyms
  );
  ```
- [ ] Update search configuration
- [ ] Test FTS recall improvement on domain queries

**Acceptance Criteria:**
- ✅ +5-10% FTS recall on tax-specific queries
- ✅ Better handling of Italian acronyms
- ✅ Backward compatible (doesn't break existing queries)

---

### DEV-81: Expand Monitoring Dashboards
**Priority:** LOW | **Effort:** 2-3 days (with Claude Code) | **Dependencies:** DEV-77 ✅

**Tasks:**
- [ ] Add "Document Ingestion" dashboard
- [ ] Add "User Behavior" dashboard (query patterns, popular categories)
- [ ] Set up Grafana data source for PostgreSQL (direct DB queries)
- [ ] Create weekly email reports (Grafana Cloud feature)

---

## Backlog (Q3+ or Deferred)

### DEV-82: LLM Fallback to Claude/Gemini
**Effort:** 1 week (with Claude Code) | **Priority:** MEDIUM (reduces SPOF)

**Problem:** If OpenAI API fails (outage, rate limits, account issues), entire RAG system stops working. No answers for users.

**Solution:** Multi-LLM fallback strategy:
1. Primary: OpenAI (gpt-4-turbo)
2. Fallback 1: Anthropic Claude (claude-3-sonnet)
3. Fallback 2: Google Gemini (gemini-1.5-pro)

**Tasks:**
- [ ] Create `app/services/llm_provider.py` with fallback logic
- [ ] Add Anthropic + Google API keys to config
- [ ] Implement retry logic with exponential backoff (3 attempts per provider)
- [ ] Add metrics: LLM provider used per request, fallback rate
- [ ] Test all three providers with identical prompts (ensure quality)

**Acceptance Criteria:**
- ✅ System stays online during OpenAI outage
- ✅ Automatic fallback to Claude within 5 seconds
- ✅ Quality comparable across providers (manual evaluation on 50 queries)
- ✅ Grafana dashboard shows LLM provider distribution

**Trigger:** After DEV-77 (monitoring) is complete

---

### DEV-83: Multi-Region PostgreSQL Replica
**Effort:** 2-3 weeks (with Claude Code for config/scripts) | **Priority:** LOW (only if needed for compliance/DR)

**Problem:** Single-region PostgreSQL deployment. If region fails, complete data loss (unless backups restore, which takes hours).

**Solution:** Hetzner multi-datacenter replica (Germany + Finland)

**Tasks:**
- [ ] Create PostgreSQL read replica in Hetzner Finland datacenter
- [ ] Configure streaming replication lag monitoring (<10s target)
- [ ] Implement automatic failover to replica if primary datacenter down
- [ ] Test failover procedure (planned failover drill)
- [ ] Document disaster recovery runbook

**Cost:** +$15/month (replica VPS in Finland)

**Trigger:** Multi-region compliance requirement OR disaster recovery SLA

---

### DEV-84: Multi-Tenancy Support
**Effort:** 3-4 weeks (with Claude Code) | **Priority:** LOW (only if white-label deployment needed)

**Trigger:** White-label product requirement

---

### DEV-85: Configure PostgreSQL High Availability
**Effort:** 1 day (with Claude Code generating configs) | **Priority:** HIGH (production readiness)

**What is High Availability?**

For Hetzner VPS deployment, implement PostgreSQL replication and automatic failover within same datacenter.

**Problem:**
Current deployment has single PostgreSQL instance. If it fails, database goes down.

**Solution:**
Set up PostgreSQL streaming replication with automatic failover using Patroni or similar.

**Tasks:**
- [ ] Set up PostgreSQL streaming replication
- [ ] Configure automatic failover (using Patroni/repmgr)
- [ ] Test failover procedure
- [ ] Document failover behavior

**Cost:** Requires additional VPS (~$7-15/month for standby)

**Trigger:** Before production launch with paying customers

---

### DEV-86: Automated Index Health Monitoring + Rebuild
**Effort:** 2-3 days (with Claude Code generating scripts/dashboards) | **Priority:** MEDIUM

**Problem:** If FTS (GIN) or pgvector (IVFFlat) indexes become corrupted, queries become extremely slow (10-100x slower). Currently requires manual detection + rebuild.

**Solution:** Automated monitoring + alerts + rebuild scripts.

**Tasks:**
- [ ] Add Prometheus metric: `pg_index_health` (monitors index bloat, corruption)
- [ ] Create Grafana alert: "Index scan ratio <50%" (suggests index not being used)
- [ ] Create automated rebuild script: `scripts/ops/rebuild_indexes.sh`
  - Checks index health
  - Rebuilds with `REINDEX INDEX CONCURRENTLY` (zero downtime)
  - Logs to monitoring
- [ ] Schedule weekly index health check (cron job)
- [ ] Document manual rebuild procedure in runbook

**Acceptance Criteria:**
- ✅ Grafana dashboard shows index health metrics
- ✅ Alert fires when index scan ratio drops below 50%
- ✅ Automated rebuild script tested on QA
- ✅ Runbook documents emergency rebuild procedure

**Trigger:** After DEV-77 (Prometheus/Grafana monitoring)

---

### DEV-87: User Subscription & Payment Management
**Priority:** CRITICAL | **Effort:** 2-3 weeks (with Claude Code) | **Dependencies:** DEV-73 ✅ (QA environment for testing)

**Frontend Integration:**
This backend task is linked to **DEV-009** in frontend roadmap:
- **Frontend Task:** DEV-009: Integrate User Subscription Payment (Stripe)
- **Location:** `/Users/micky/WebstormProjects/PratikoAiWebApp/ARCHITECTURE_ROADMAP.md`
- **Coordination Required:** Backend APIs must be completed BEFORE frontend implementation
- **API Endpoints:** Frontend will consume `/api/v1/subscriptions/*` and `/api/v1/webhooks/stripe` endpoints
- **Stripe Configuration:** Both frontend and backend must use matching Stripe publishable/secret keys
- **Subscription Plans:** €69/month with 7-day trial (configured in both frontend and backend)

**Problem:**
No payment system implemented. Cannot accept paying customers or manage subscriptions. Need billing, payment processing, subscription management, and automated reminders.

**Solution:**
Implement complete subscription management system with Stripe integration, usage tracking, and automated billing.

**Payment Provider Selection:**
- **Stripe** (recommended): 2.9% + €0.25 per transaction, excellent EU support, PSD2 compliant
- SCA (Strong Customer Authentication) compliant for EU
- Supports Italian payment methods (cards, SEPA, Satispay)

**Subscription Tiers:**

**1. Free Tier**
- 10 questions/month
- Basic responses
- Community support
- No payment required

**2. Professional (€29/month or €290/year)**
- 500 questions/month
- Priority responses
- Email support
- Document upload (5 docs/month)

**3. Business (€99/month or €990/year)**
- Unlimited questions
- Fastest responses
- Phone + email support
- Unlimited document uploads
- Custom integrations

**Implementation Tasks:**

**Week 1: Stripe Integration & Database Schema**
- [ ] Create Stripe account (business verification required)
- [ ] Add Stripe SDK: `pip install stripe`
- [ ] Create database tables:
  ```sql
  CREATE TABLE subscriptions (
      id UUID PRIMARY KEY,
      user_id UUID REFERENCES users(id) NOT NULL,
      stripe_customer_id VARCHAR(100) UNIQUE,
      stripe_subscription_id VARCHAR(100) UNIQUE,
      plan_tier VARCHAR(20) NOT NULL,  -- 'free', 'professional', 'business'
      status VARCHAR(20) NOT NULL,     -- 'active', 'canceled', 'past_due', 'paused'
      current_period_start TIMESTAMPTZ,
      current_period_end TIMESTAMPTZ,
      cancel_at_period_end BOOLEAN DEFAULT FALSE,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ
  );

  CREATE TABLE usage_tracking (
      id UUID PRIMARY KEY,
      user_id UUID REFERENCES users(id) NOT NULL,
      month_year VARCHAR(7) NOT NULL,  -- '2025-01'
      questions_count INTEGER DEFAULT 0,
      documents_uploaded INTEGER DEFAULT 0,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      UNIQUE(user_id, month_year)
  );

  CREATE TABLE payment_history (
      id UUID PRIMARY KEY,
      user_id UUID REFERENCES users(id) NOT NULL,
      stripe_payment_intent_id VARCHAR(100) UNIQUE,
      amount_cents INTEGER NOT NULL,
      currency VARCHAR(3) DEFAULT 'EUR',
      status VARCHAR(20) NOT NULL,  -- 'succeeded', 'failed', 'refunded'
      description TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
  );
  ```
- [ ] Create Alembic migration: `alembic revision -m "add_subscription_tables"`
- [ ] Create `app/models/subscription.py` with SQLAlchemy models

**Week 2: Payment & Subscription APIs**
- [ ] Create `app/services/stripe_service.py`:
  ```python
  class StripeService:
      async def create_customer(user_id, email) -> str
      async def create_subscription(customer_id, plan_tier) -> Dict
      async def cancel_subscription(subscription_id) -> Dict
      async def update_payment_method(customer_id, payment_method_id) -> Dict
      async def handle_webhook(event_type, data) -> None
  ```
- [ ] Create API endpoints in `app/api/v1/subscriptions.py`:
  - `POST /api/v1/subscriptions` - Create subscription
  - `GET /api/v1/subscriptions/current` - Get user's current subscription
  - `PUT /api/v1/subscriptions/cancel` - Cancel subscription
  - `PUT /api/v1/subscriptions/resume` - Resume canceled subscription
  - `POST /api/v1/subscriptions/payment-method` - Update payment method
  - `GET /api/v1/subscriptions/usage` - Get current usage stats
- [ ] Create Stripe webhook endpoint: `POST /api/v1/webhooks/stripe`
  - Handle `invoice.payment_succeeded`
  - Handle `invoice.payment_failed`
  - Handle `customer.subscription.deleted`
  - Handle `customer.subscription.updated`
- [ ] Implement usage tracking middleware:
  - Increment `questions_count` on each chat request
  - Check subscription limits before processing request
  - Return 429 error if limit exceeded

**Week 3: Billing Reminders & Frontend Integration**
- [ ] Create `app/services/billing_reminder_service.py`:
  ```python
  class BillingReminderService:
      async def send_payment_failed_email(user_id) -> None
      async def send_trial_ending_email(user_id, days_left) -> None
      async def send_usage_limit_warning(user_id, usage_percent) -> None
      async def send_subscription_canceled_email(user_id) -> None
  ```
- [ ] Create background job for reminder emails (Celery/cron):
  - Daily: Check for failed payments (send reminder after 3, 7, 14 days)
  - Daily: Check usage limits (send warning at 80%, 95%, 100%)
  - Weekly: Check expiring subscriptions (send notice 7 days before)
- [ ] Create email templates:
  - `templates/email/payment_failed.html`
  - `templates/email/trial_ending.html`
  - `templates/email/usage_limit_warning.html`
  - `templates/email/subscription_canceled.html`
  - `templates/email/payment_successful.html`
- [ ] Add rate limiting based on subscription tier:
  ```python
  TIER_LIMITS = {
      'free': {'questions_per_month': 10, 'documents_per_month': 0},
      'professional': {'questions_per_month': 500, 'documents_per_month': 5},
      'business': {'questions_per_month': -1, 'documents_per_month': -1}  # unlimited
  }
  ```
- [ ] Write tests: `tests/test_subscription_service.py`, `tests/test_stripe_webhooks.py`
- [ ] Document subscription API in OpenAPI spec

**Acceptance Criteria:**
- ✅ Stripe integration working (test mode)
- ✅ Users can subscribe to Professional/Business plans
- ✅ Usage tracking accurate (questions + documents counted)
- ✅ Rate limiting enforces subscription limits
- ✅ Payment failures trigger email reminders
- ✅ Webhooks handle all Stripe events correctly
- ✅ Subscription cancellation works (end of period)
- ✅ Admin dashboard shows subscription metrics
- ✅ All emails render correctly in Gmail/Outlook
- ✅ GDPR compliant (payment data via Stripe, not stored locally)

**Security Considerations:**
- [ ] Stripe webhook signature verification (prevent spoofing)
- [ ] PCI DSS compliance (never store card details)
- [ ] Use Stripe's hosted payment page (no card data touches backend)
- [ ] Encrypt Stripe API keys in environment variables
- [ ] Log all payment events for audit trail

**Expected Revenue (Year 1):**
- 50 Professional subscribers: €1,450/month
- 10 Business subscribers: €990/month
- **Total: €2,440/month** (~€29,280/year before costs)
- Stripe fees: ~€85/month
- **Net revenue: ~€2,355/month** (~€28,260/year)

**Cost to Implement:**
- Stripe account: Free (pay per transaction)
- Development time: 2-3 weeks
- Testing: 1 week

---

### DEV-88: Deploy Preprod Environment (Hetzner VPS)
**Priority:** HIGH | **Effort:** 3-4 days (QA is template) | **Dependencies:** DEV-73 ✅ (QA deployment complete) + DEV-87 ✅ (payment system testable)

**Problem:**
Need production-like environment for final testing before deploying to production. QA is for feature testing, Preprod is for release validation.

**Solution:**
Deploy complete PratikoAI backend to separate Hetzner VPS with production-like configuration.

**Implementation Tasks:**

**Week 1: VPS Setup & Deployment**
- [ ] Provision Hetzner CX21 VPS for Preprod (2 vCPU, 4GB RAM)
  - Same specs as QA for consistency
  - Different IP address and VPS instance
  - Cost: ~€6.50/month (~$7/month)
- [ ] Configure firewall rules (same as QA)
- [ ] Install Docker and Docker Compose
- [ ] Copy docker-compose.yml to Preprod VPS
- [ ] Create `.env.preprod` with production-like configuration:
  ```env
  APP_ENV=preprod
  POSTGRES_USER=aifinance
  POSTGRES_PASSWORD=<generate-strong-password>
  POSTGRES_DB=aifinance
  OPENAI_API_KEY=<preprod-api-key>
  STRIPE_SECRET_KEY=<test-mode-key>
  LOG_LEVEL=INFO  # Production log level
  ALLOWED_ORIGINS=http://<preprod-frontend-url>
  ```
- [ ] Deploy stack: `docker-compose --env-file .env.preprod up -d`
- [ ] Run database migrations
- [ ] Set up DNS: `api-preprod.pratikoai.com`
- [ ] Configure SSL with Let's Encrypt
- [ ] Set up automated backups (Hetzner snapshots)

**Acceptance Criteria:**
- ✅ Preprod environment accessible at `https://api-preprod.pratikoai.com`
- ✅ All services running with production-like configuration
- ✅ Database migrations run successfully
- ✅ All API endpoints responding
- ✅ Stripe test mode working (test payments successful)
- ✅ Production-level monitoring active (Prometheus + Grafana)
- ✅ Automated daily backups configured

**Infrastructure Cost (Preprod):**
- Hetzner CX21 VPS: ~$7/month
- Snapshots/backups: ~$1/month
- **Total: ~$8/month**

**Configuration Differences from QA:**
- LOG_LEVEL=INFO (not DEBUG)
- Stricter rate limiting
- Production-like secrets rotation policy
- Stripe test mode enabled

**Use Cases:**
- Final release candidate testing
- Stakeholder demos before production release
- Payment flow end-to-end testing
- Performance testing with production-like data
- Integration testing with production frontend

---

### DEV-89: GDPR Compliance Audit (Preprod Environment)
**Priority:** HIGH | **Effort:** 2-3 days (QA audit is template) | **Dependencies:** DEV-88 ✅ (Preprod live) + DEV-75 ✅ (QA audit complete)

**Problem:**
Need to validate GDPR compliance with production-like configuration and data before production launch.

**Solution:**
Run same GDPR audit on Preprod environment with production-like data and configuration.

**Audit Focus Areas:**

**1. Production-Like Data Testing**
- [ ] Test data export with realistic data volume
- [ ] Test data deletion with production-like database size
- [ ] Validate performance of GDPR operations at scale

**2. Configuration Validation**
- [ ] Verify production log levels don't expose PII
- [ ] Test production monitoring doesn't log sensitive data
- [ ] Validate production error messages are GDPR-safe

**3. Third-Party Integrations**
- [ ] Verify OpenAI API usage is GDPR compliant
- [ ] Verify Stripe payment data handling is GDPR compliant
- [ ] Test data processing agreements with vendors
- [ ] Validate no PII sent to analytics/monitoring tools

**4. Cross-Border Transfers**
- [ ] Verify Hetzner Germany location for EU compliance
- [ ] Test geolocation restrictions (if applicable)
- [ ] Validate data residency requirements

**Implementation Tasks:**

**Days 1-2: Compliance Testing**
- [ ] Run full GDPR audit checklist from DEV-74
- [ ] Test with production-like data volume
- [ ] Validate all remediation from QA audit
- [ ] Test payment data handling (GDPR Article 15 - Right to Access)
- [ ] Verify subscription data included in data export

**Days 3-4: Documentation & Sign-off**
- [ ] Create `docs/compliance/GDPR_AUDIT_PREPROD.md`
- [ ] Document any production-specific findings
- [ ] Get stakeholder sign-off on GDPR compliance
- [ ] Create final production deployment checklist

**Acceptance Criteria:**
- ✅ All GDPR features work at production scale
- ✅ Payment data handling is GDPR compliant
- ✅ No performance issues with GDPR operations
- ✅ Production configuration is GDPR-safe
- ✅ All third-party integrations validated
- ✅ Stakeholder approval obtained
- ✅ Ready for production GDPR audit

---

### DEV-90: Deploy Production Environment (Hetzner VPS)
**Priority:** CRITICAL | **Effort:** 1 week (with production hardening) | **Dependencies:** DEV-88 ✅ (Preprod validated) + DEV-89 ✅ (Preprod GDPR audit passed)

**Problem:**
Need production environment for paying customers. Must be reliable, performant, and cost-effective.

**Solution:**
Deploy complete PratikoAI backend to Hetzner VPS with production configuration and enhanced resources.

**Implementation Tasks:**

**Week 1: VPS Setup**
- [ ] Provision Hetzner CX31 VPS (2 vCPU, 8GB RAM, 80GB SSD)
  - Larger instance for production load
  - Region: Germany (for EU data residency/GDPR)
  - Cost: ~€12.90/month (~$15/month)
- [ ] Configure strict firewall rules:
  - Allow: 22 (SSH - restricted to specific IPs)
  - Allow: 80 (HTTP - redirects to HTTPS)
  - Allow: 443 (HTTPS - public)
  - Block: All other ports from internet
  - Allow: 3000, 9090 (monitoring - VPN/specific IPs only)
- [ ] Install Docker and Docker Compose
- [ ] Set up fail2ban for SSH brute force protection
- [ ] Configure automatic security updates

**Week 2: Deployment & Hardening**
- [ ] Copy docker-compose.yml to Production VPS
- [ ] Create `.env.production` with secure configuration:
  ```env
  APP_ENV=production
  POSTGRES_USER=aifinance
  POSTGRES_PASSWORD=<cryptographically-strong-password>
  POSTGRES_DB=aifinance
  OPENAI_API_KEY=<production-api-key>
  STRIPE_SECRET_KEY=<live-mode-key>
  STRIPE_WEBHOOK_SECRET=<webhook-signing-secret>
  LOG_LEVEL=WARNING  # Production log level
  ALLOWED_ORIGINS=https://app.pratikoai.com
  RATE_LIMIT_DEFAULT=100/minute
  RATE_LIMIT_CHAT=20/minute
  ```
- [ ] Deploy stack: `docker-compose --env-file .env.production up -d`
- [ ] Run database migrations
- [ ] Set up DNS: `api.pratikoai.com` pointing to production VPS
- [ ] Configure SSL with Let's Encrypt (with auto-renewal)
- [ ] Set up automated daily backups (Hetzner snapshots + off-site backup)
- [ ] Configure monitoring alerts (email/Slack for critical issues)
- [ ] Enable Docker container restart policies
- [ ] Set up log rotation to prevent disk space issues
- [ ] Configure Stripe webhook endpoint with live keys

**Security Hardening:**
- [ ] Disable root SSH login
- [ ] Enable UFW firewall
- [ ] Configure fail2ban
- [ ] Set up automated security updates
- [ ] Implement secrets rotation policy
- [ ] Enable PostgreSQL SSL connections
- [ ] Configure Redis password authentication
- [ ] Verify Stripe webhook signature validation

**Acceptance Criteria:**
- ✅ Production environment accessible at `https://api.pratikoai.com`
- ✅ All services running with production configuration
- ✅ SSL certificate valid and auto-renewing
- ✅ All API endpoints responding with <100ms latency (p95)
- ✅ Stripe live mode working (real payments processed)
- ✅ Security hardening complete (firewall, fail2ban, etc.)
- ✅ Automated daily backups + weekly off-site backups
- ✅ Monitoring alerts configured and tested
- ✅ Zero downtime deployment process documented

**Infrastructure Cost (Production):**
- Hetzner CX31 VPS: ~$15/month
- Snapshots/backups (2 weeks retention): ~$2/month
- **Total: ~$17/month**

**Scaling Plan:**
- Current: CX31 (2 vCPU, 8GB RAM) → Supports 100-500 users
- Next: CX41 (4 vCPU, 16GB RAM, ~$28/month) → Supports 500-2000 users
- Future: CX51 (8 vCPU, 32GB RAM, ~$54/month) → Supports 2000-5000 users

**Deployment Process:**
1. Test on QA
2. Validate on Preprod
3. Deploy to Production during low-traffic window
4. Monitor for 24 hours
5. Notify team of successful deployment

---

### DEV-91: GDPR Compliance Audit (Production Environment)
**Priority:** CRITICAL | **Effort:** 4-5 days (requires legal review) | **Dependencies:** DEV-90 ✅ (Production live) + DEV-89 ✅ (Preprod audit complete)

**Problem:**
Final GDPR compliance validation required before accepting real user data in production.

**Solution:**
Comprehensive production GDPR audit with security hardening and compliance documentation.

**Audit Activities:**

**1. Production GDPR Feature Validation**
- [ ] Test data export on production
- [ ] Test data deletion on production
- [ ] Test payment data export (Stripe + local subscription records)
- [ ] Verify consent management works correctly
- [ ] Validate all privacy policies are live and linked

**2. Security Audit**
- [ ] Test SSL/TLS configuration (A+ rating on SSL Labs)
- [ ] Verify firewall rules block unauthorized access
- [ ] Test API authentication and rate limiting
- [ ] Validate no PII in production logs
- [ ] Test Stripe webhook security (signature verification)

**3. Data Protection Impact Assessment (DPIA)**
- [ ] Document all data processing activities
- [ ] Document payment data handling via Stripe
- [ ] Identify and assess privacy risks
- [ ] Document risk mitigation measures
- [ ] Get legal/compliance team sign-off

**4. Breach Response Testing**
- [ ] Test breach detection mechanisms
- [ ] Verify breach notification procedures
- [ ] Document incident response plan
- [ ] Test 72-hour notification timeline

**5. Vendor Compliance**
- [ ] Verify Hetzner GDPR compliance (Data Processing Agreement)
- [ ] Validate OpenAI GDPR compliance
- [ ] Validate Stripe GDPR compliance (DPA signed)
- [ ] Document all sub-processors
- [ ] Maintain vendor compliance records

**6. User Rights Management**
- [ ] Test subject access request (SAR) workflow
- [ ] Verify data portability works correctly
- [ ] Test right to rectification
- [ ] Validate right to object functionality
- [ ] Test subscription data deletion

**7. Monitoring & Auditing**
- [ ] Set up GDPR compliance monitoring
- [ ] Create audit log for data access
- [ ] Implement alerts for suspicious data access
- [ ] Document regular compliance review schedule

**Implementation Tasks:**

**Week 1: Production Audit & Certification**
- [ ] Day 1-2: Run complete GDPR audit on production
- [ ] Day 3: Security penetration testing
- [ ] Day 4: Document all findings and remediation
- [ ] Day 5: Final compliance documentation and sign-off

**Acceptance Criteria:**
- ✅ All GDPR features functional on production
- ✅ Payment data handling is GDPR compliant
- ✅ Security audit passed (no critical findings)
- ✅ Data Protection Impact Assessment complete
- ✅ Breach response plan tested and documented
- ✅ All vendor compliance verified (including Stripe DPA)
- ✅ GDPR compliance certification obtained
- ✅ Legal/compliance team approval

**Documentation Deliverables:**
- [ ] `docs/compliance/GDPR_AUDIT_PRODUCTION.md`
- [ ] `docs/compliance/DATA_PROTECTION_IMPACT_ASSESSMENT.md`
- [ ] `docs/compliance/INCIDENT_RESPONSE_PLAN.md`
- [ ] `docs/compliance/VENDOR_COMPLIANCE_RECORDS.md`
- [ ] `docs/compliance/STRIPE_DATA_PROCESSING_AGREEMENT.pdf`
- [ ] Privacy Policy (published on website)
- [ ] Cookie Policy (published on website)

**Compliance Maintenance:**
- [ ] Schedule quarterly GDPR compliance reviews
- [ ] Set up annual DPIA reviews
- [ ] Document compliance as ongoing process
- [ ] Train team on GDPR requirements

**Post-Audit Actions:**
- [ ] Create GDPR compliance badge for website
- [ ] Notify users of privacy rights
- [ ] Set up user rights request portal
- [ ] Monitor for regulatory changes

---

## Success Metrics

### Q1 2025 Targets

- [ ] **Pinecone removed:** Zero Pinecone costs on billing (DEV-67, DEV-68)
- [ ] **RSS feeds expanded:** 8+ sources configured (DEV-69)
- [ ] **Daily RSS email reports:** Automated feed monitoring (DEV-70)
- [ ] **No emojis in responses:** Professional, formal tone for Italian tax/legal context (DEV-71)
- [ ] **Expert feedback system:** Complete S113-S131 flow, auto-approval for trusted experts (DEV-72)
- [ ] **QA environment deployed:** On Hetzner (DEV-73)
- [ ] **QA GDPR audit complete:** (DEV-75)
- [ ] **Payment system live:** Stripe integration, subscriptions, reminders (DEV-87)
- [ ] **All environments deployed:** Preprod, Production on Hetzner (DEV-88, DEV-90)
- [ ] **GDPR compliance:** All audits complete and certified (DEV-75, DEV-89, DEV-91)
- [ ] **Cache hit rate >60%:** Hash + semantic caching (DEV-76)
- [ ] **Monitoring live:** 4 Grafana dashboards operational, alerts configured (DEV-77)
- [ ] **Reranking deployed:** +10% precision improvement (DEV-78)
- [ ] **Query latency p95 <200ms:** With all enhancements enabled

### Q2 2025 Targets

- [ ] **HNSW index deployed:** 20-30% vector search latency reduction (DEV-79)
- [ ] **Italian dictionary live:** +5% FTS recall improvement (DEV-80)
- [ ] **Extended dashboards:** Document ingestion + user behavior metrics (DEV-81)

### 6-Month (End of Q2 2025)

- [ ] **Overall retrieval precision@14 >80%:** Manual evaluation on test set
- [ ] **pgvector confirmed:** Long-term solution validated, no migration to external vector DB needed
- [ ] **Technical debt resolved:** All Q1 priorities complete

---

## Decision Log

| Date | Decision | Rationale | Task |
|------|----------|-----------|------|
| 2025-11-14 | Migrate FAQs to pgvector | Simplify architecture, reduce cost $150-330/month | DEV-67 |
| 2025-11-14 | Remove Pinecone entirely | Over-engineered for current scale, never used in main KB, pgvector sufficient | DEV-68 |
| 2025-11-14 | Expand RSS feeds | Better regulatory coverage (INPS, MEF, Corte di Cassazione, etc.) | DEV-69 |
| 2025-11-14 | Daily RSS email reports | Proactive feed monitoring and quality tracking | DEV-70 |
| 2025-11-14 | Disable emoji in LLM responses | Professional Italian tax/legal context requires formal tone | DEV-71 |
| 2025-11-14 | Implement expert feedback system | Complete S113-S131 architecture flow with auto-approval | DEV-72 |
| 2025-11-14 | Deploy to Hetzner (not AWS) | Cost: $33/month (all 3 envs) vs $330+/month AWS | DEV-73, DEV-88, DEV-90 |
| 2025-11-14 | GDPR compliance audits | Required before production launch with real users | DEV-75, DEV-89, DEV-91 |
| 2025-11-14 | Stripe payment integration | Enable subscription revenue, €2,440/month projected | DEV-87 |
| 2025-11-14 | Fix cache key (remove doc_hashes) | Improve hit rate from 0-5% to 60-70%, save $1,500-1,800/month | DEV-76 |
| 2025-11-14 | Implement Prometheus + Grafana | Industry standard monitoring, automatic alerting | DEV-77 |
| 2025-11-14 | Add cross-encoder reranking | +10-15% precision improvement | DEV-78 |
| 2025-11-11 | Add publication_date to knowledge_items | Temporal filtering for regulations | Completed |
| 2025-11-03 | Add junk detection and text_quality | Filter low-quality extractions | Completed |
| 2025-11-03 | Implement SSE keepalive (backend) | Prevent timeout on long RAG queries (15-20s) | Completed |

---

## Infrastructure Cost Summary

**All 3 Environments (Hetzner):**
- QA: $8/month (CX21 + backups)
- Preprod: $8/month (CX21 + backups)
- Production: $17/month (CX31 + backups)
- **Total: ~$33/month** for complete multi-environment setup

**vs AWS Alternative:**
- AWS QA alone: $110-135/month
- **Savings: ~$297-402/month** (90% cost reduction)

---

## Related Documentation

- **Current Architecture:** `docs/DATABASE_ARCHITECTURE.md` - Detailed technical documentation
- **Advanced Patterns:** `docs/ADVANCED_VECTOR_SEARCH.md` - pgvector query optimization guide
- **Monitoring:** `docs/monitoring/` - Grafana dashboards and alert runbooks (after DEV-78)
- **GDPR Compliance:** `docs/compliance/` - GDPR audit reports and compliance documentation
- **Deployment:** `docs/deployment/` - Hetzner deployment guides for all environments

---

**Roadmap Maintained By:** Engineering Team
**Review Cycle:** Monthly sprint planning
**Next Review:** 2025-12-01
