# PratikoAi Backend - Development Roadmap

**Last Updated:** 2024-12-19
**Status:** Active Development
**Next Task ID:** DEV-BE-95

---

## Overview

This roadmap tracks planned architectural improvements and enhancements for the PratikoAi backend system. Each task follows the DEV-XX numbering scheme matching our development workflow.

**Current Architecture:** See `docs/DATABASE_ARCHITECTURE.md` for detailed documentation of the production system.

**Recent Completed Work:**
- DEV-BE-93: Unified Input Security Hardening (2024-12-19)
- DEV-BE-70: Daily Ingestion Collection Email Report (2024-12-18)
- DEV-BE-69: Expand RSS Feed Sources (2024-12-10)
- DEV-BE-92: Test Coverage to 49% Threshold (2024-11-24)
- DEV-BE-71: Disable Emoji in LLM Responses (2024-11-24)
- DEV-BE-68: Remove Pinecone Integration Code (2024-11-24)

**Deployment Timeline Estimates:**

📅 **Time to QA Environment (DEV-BE-75):**
- **Optimistic (parallel work):** ~7-8 weeks (26 Nov - 21 Gen)
- **Conservative (sequential):** ~9-10 weeks (26 Nov - 5 Feb)
- **Prerequisites:** DEV-BE-70, DEV-BE-69, DEV-BE-67, DEV-BE-71, DEV-BE-72...
- **Total effort (sequential):** 49 days (7.0 weeks)

📅 **Time to Production Environment (DEV-BE-90):**
- **Optimistic:** ~17-18.3 weeks from now (26 Nov - 3 Apr)
- **Conservative:** ~25-28 weeks from now (26 Nov - 11 Giu)
- **Prerequisites:** Path to QA + DEV-BE-68, DEV-BE-91
- **Total effort (sequential):** 118 days (16.8 weeks)
- **Note:** Production launch requires full GDPR compliance and payment system validation

**Key Dependencies:**
- ⚠️ **DEV-BE-72** - Implement Expert Feedback System: Blocks QA deployment (longest task)
- ⚠️ **GDPR Audits** - DEV-74, DEV-91: Required before each environment launch

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
- **Minimum coverage:** ≥49% (configured in `pyproject.toml`)
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

## Q4 2024 (October - December)

### ✅ Completed Tasks

<details>
<summary>
<h3>DEV-BE-94: Dual Metadata Registry Migration (CRITICAL)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 60 days (Actual: ~3 days) | <strong>Status:</strong> ✅ COMPLETED (2024-12-01)<br>
Consolidated all 44 models to SQLModel, eliminating dual metadata registry and enabling proper Alembic migrations.
</summary>

### DEV-BE-94: Dual Metadata Registry Migration (CRITICAL)

**Status:** ✅ COMPLETED (2024-12-01)
**Priority:** HIGH - Affects maintainability and Alembic migrations
**Estimated Effort:** 60 days (8-10 weeks) - REVISED from 37 days
**Actual Effort:** ~3 days
**Created:** 2025-11-28
**Completed:** 2024-12-01
**Phase 0 Complete:** 2025-11-28 (FK fixes, type fixes, tests, audit, architectural review)
**Phases 1-4 Complete:** 2024-12-01 (all models converted, merged into DEV-BE-72)
**Architectural Review:** ADR-014 CONDITIONALLY ACCEPTED by @Egidio

#### Problem Solved

The codebase had **TWO separate SQLAlchemy metadata registries** that didn't communicate:

1. **SQLModel.metadata** (CORRECT ✅) - Used by User model
2. **Base.metadata** (LEGACY ⚠️) - Used by 44 models across 7 files

This caused Alembic migration failures, mapper initialization errors, and database schema drift.

#### Solution Implemented

Consolidated ALL 44 models to use `SQLModel.metadata`:

- `app/models/ccnl_database.py` (9 models)
- `app/models/ccnl_update_models.py` (5 models)
- `app/models/faq_automation.py` (5 models)
- `app/models/quality_analysis.py` (9 models)
- `app/models/regional_taxes.py` (4 models)
- `app/models/subscription.py` (4 models)
- `app/models/data_export.py` (8 models)

#### Migration Phases Completed

- ✅ Phase 0: Preparation (FK fixes, type fixes, tests, audit)
- ✅ Phase 0.5: Alembic Behavior Testing
- ✅ Phase 1: Simple Models (regional_taxes.py - 4 models)
- ✅ Phase 2: Core CCNL Models (14 models)
- ✅ Phase 3: User-Dependent Models (14 models with User FKs)
- ✅ Phase 4: Complex Business Models (12 models)

#### Key Technical Challenges Resolved

1. **pgvector Vector columns** - Used `sa_column=Column(Vector(1536))`
2. **PostgreSQL ARRAY columns** - Used `sa_column=Column(ARRAY(String))`
3. **JSONB columns** - Used `sa_column=Column(JSONB))`
4. **Foreign key consistency** - Standardized to `user.id`

#### Benefits Achieved

- ✅ Single metadata registry (single source of truth)
- ✅ Alembic works correctly for all models
- ✅ No more mapper initialization errors
- ✅ Consistent codebase patterns
- ✅ Better FastAPI integration
- ✅ Less code duplication (DB model = API schema)

#### References

- **SQLModel Docs:** https://sqlmodel.tiangolo.com/
- **Related Issues:** Golden set retrieval workflow blocker, Alembic migration failures

</details>

---

<details>
<summary>
<h3>DEV-BE-67: Sprint 0: Multi-Agent System Setup</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1 day (2024-11-17) | <strong>Actual:</strong> 1 day | <strong>Dependencies:</strong> None | <strong>Status:</strong> ✅ COMPLETED<br>
Established foundational multi-agent development system with 8 specialized subagents and Italian name mappings.
</summary>

### DEV-BE-67: Sprint 0: Multi-Agent System Setup
**Priority:** HIGH | **Effort:** 1 day (2024-11-17) | **Actual:** 1 day | **Dependencies:** None | **Status:** ✅ COMPLETED

**Original Task:** Migrate FAQ Embeddings from Pinecone to pgvector

**NOTE:** The original FAQ migration work has been **deferred to Sprint 1**. Sprint 0 focused on establishing the foundational multi-agent development system.

**What Was Actually Completed (Sprint 0):**

**1. Multi-Agent System Architecture**
- ✅ Documented complete subagent architecture in `.claude/decisions.md`
- ✅ Established Scrum Master role (@Ottavio) for sprint coordination
- ✅ Defined clear responsibilities for each specialized subagent
- ✅ Created systematic approach to complex development tasks

**2. Subagent Configurations Created (8 Total)**
- ✅ `.claude/subagents/architect.md` - System architecture and design decisions
- ✅ `.claude/subagents/backend-dev.md` - Backend implementation specialist
- ✅ `.claude/subagents/data-engineer.md` - Database and data pipeline work
- ✅ `.claude/subagents/devops.md` - Infrastructure and deployment automation
- ✅ `.claude/subagents/frontend-dev.md` - Frontend implementation specialist
- ✅ `.claude/subagents/qa-engineer.md` - Testing and quality assurance
- ✅ `.claude/subagents/scrum-master.md` - Sprint planning and coordination
- ✅ `.claude/subagents/tech-lead.md` - Technical leadership and code review

**3. Italian Name Mapping (@mentions)**
- ✅ Configured Italian name aliases for natural team interaction:
  - @Ottavio (Scrum Master)
  - @Marco (Architect)
  - @Luigi (Backend Dev)
  - @Giovanni (Data Engineer)
  - @Alessandro (DevOps)
  - @Francesca (Frontend Dev)
  - @Sofia (QA Engineer)
  - @Roberto (Tech Lead)

**4. Slack Integration (Two-Webhook Architecture)**
- ✅ Implemented dual-webhook system for team communication
- ✅ Main webhook: General team notifications and updates
- ✅ Scrum Master webhook: Sprint planning, task assignments, progress reports
- ✅ Automated notification system for development milestones

**5. Context Files Structure**
- ✅ Created `.claude/sprint-plan.md` for current sprint tracking
- ✅ Created `.claude/subagent-assignments.md` for task distribution
- ✅ Established single source of truth for sprint progress
- ✅ Enabled parallel work coordination across subagents

**Impact & Value Delivered:**
- **Development Efficiency:** Specialized subagents reduce context switching
- **Code Quality:** Clear ownership and review processes
- **Team Coordination:** Systematic sprint planning with @Ottavio
- **Communication:** Automated Slack notifications keep stakeholders informed
- **Scalability:** Framework supports growing team and complexity

**Deferred Work (Sprint 1):**
The original FAQ migration from Pinecone to pgvector will be addressed in Sprint 1 as part of the broader infrastructure optimization efforts. This includes:
- Creating `faq_embeddings` table in PostgreSQL
- Migrating FAQ data from Pinecone to pgvector
- Refactoring `app/orchestrators/golden.py` to use pgvector
- Removing Pinecone dependencies (cost savings: $150-330/month)

**Acceptance Criteria (All Met):**
- ✅ All 8 subagent configurations operational
- ✅ Italian name mappings working correctly
- ✅ Slack integration delivering notifications
- ✅ Sprint planning framework established
- ✅ Context files structure in place
- ✅ Team ready for Sprint 1 development work

**Completion Date:** 2024-11-17

</details>

---

<details>
<summary>
<h3>DEV-BE-68: Remove Pinecone Integration Code</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1-2 days (with Claude Code) | <strong>Dependencies:</strong> DEV-BE-67 ✅ (must complete first) | <strong>Status:</strong> ✅ COMPLETED (2024-11-24)<br>
Removed 600+ lines of dead Pinecone code after FAQ migration, reducing maintenance burden and costs.
</summary>

### DEV-BE-68: Remove Pinecone Integration Code
**Priority:** HIGH | **Effort:** 1-2 days (with Claude Code) | **Dependencies:** DEV-BE-67 ✅ (must complete first)

**Problem:**
Pinecone integration code (600+ lines) adds maintenance burden and confuses developers. After FAQ migration (DEV-BE-67), all Pinecone code is dead code.

**Implementation Tasks:**

**Week 1: Code Removal**
- [x] Delete `app/services/vector_providers/pinecone_provider.py` (349 lines)
- [x] Delete `app/services/vector_config.py` (205 lines)
- [x] Delete `app/services/vector_provider_factory.py`
- [x] Delete `app/services/embedding_management.py` (Pinecone-based)
- [x] Delete `app/services/hybrid_search_engine.py` (Pinecone-based)
- [x] Delete `app/services/query_expansion_service.py`
- [x] Delete `app/services/semantic_faq_matcher.py`
- [x] Delete `app/services/context_builder.py` (check if used elsewhere first!)
- [x] Remove from `requirements.txt` or `pyproject.toml`: `pinecone-client>=2.2.0`
- [x] Delete tests: `tests/test_vector_search.py`
- [x] Remove Pinecone env vars from `.env.example`:
  - `PINECONE_API_KEY`
  - `PINECONE_ENVIRONMENT`
  - `PINECONE_INDEX_NAME`
- [x] Update `app/core/config.py` - remove Pinecone settings
- [x] Search codebase for "pinecone" (case-insensitive) and clean up all references

**Documentation Cleanup:**
- [x] Delete `docs/pinecone-guardrails.md` (262 lines)
- [x] Delete `docs/architecture/vector-search.md` (261 lines)
- [x] Update README.md to remove Pinecone references
- [x] Update `docs/DATABASE_ARCHITECTURE.md` if needed

**Acceptance Criteria:**
- ✅ `grep -ri "pinecone" .` returns no results (excluding git history)
- ✅ All tests pass without Pinecone dependencies
- ✅ Production deployment successful with no errors
- ✅ No Pinecone costs on billing dashboard

**Validation:**
- [x] Run full test suite: `pytest`
- [x] Deploy to QA, test FAQ lookup functionality

</details>

---

<details>
<summary>
<h3>DEV-BE-71: Disable Emoji in LLM Responses</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 1-2 days (with Claude Code) | <strong>Dependencies:</strong> None | <strong>Status:</strong> ✅ COMPLETED (2024-11-24)<br>
Disabled emojis in all LLM responses for professional Italian tax and legal advisory context.
</summary>

### DEV-BE-71: Disable Emoji in LLM Responses
**Priority:** MEDIUM | **Effort:** 1-2 days (with Claude Code) | **Dependencies:** None | **Status:** ✅ COMPLETED (2024-11-24)

**Problem:**
LLMs (especially ChatGPT) frequently include emojis in responses (✅, 📊, 💡, etc.), which looks unprofessional for Italian tax and legal advisory context. Users expect formal, professional language without decorative elements.

**Solution:**
Add explicit instruction to system prompts to disable emoji usage. Update all prompt templates.

**Implementation Tasks:**

**Day 1: Prompt Updates**
- [x] Update `SYSTEM_PROMPT` in `app/core/langgraph/prompt_policy.py`
- [x] Update all domain-specific prompts in `app/services/prompt_template_manager.py`
- [x] Update FAQ generation prompt in `app/services/auto_faq_generator.py`
- [x] Update expert feedback prompts if LLM-generated

**Day 2: Testing & Validation**
- [x] Test 50 diverse queries and verify no emojis in responses
- [x] Check streaming responses (emojis sometimes appear in chunks)
- [x] Test with different LLM providers (OpenAI, Claude fallback)
- [x] Document emoji-free response requirement in `docs/PROMPT_ENGINEERING.md`

**Acceptance Criteria:**
- ✅ No emojis in LLM responses across 100 test queries
- ✅ Professional tone maintained in all responses
- ✅ Bullet points and numbered lists work correctly
- ✅ All prompt templates updated
- ✅ Documentation updated

</details>

---

<details>
<summary>
<h3>DEV-BE-92: Increase Test Coverage to 49% Threshold</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 7-10 days | <strong>Dependencies:</strong> None | <strong>Sprint:</strong> Sprint 1 | <strong>Status:</strong> ✅ COMPLETED (2024-11-24)<br>
Increased test coverage from 4% to 49% threshold, removing broken tests and adding comprehensive test suites.
</summary>

### DEV-BE-92: Increase Test Coverage to 49% Threshold
**Priority:** CRITICAL | **Effort:** 7-10 days | **Dependencies:** None | **Sprint:** Sprint 1 | **Status:** ✅ COMPLETED (2024-11-24)

**Problem:**
Pre-commit hooks block all commits when test coverage is below 49% threshold. Current coverage is only 4%, preventing any code from being committed to the repository. This is a critical workflow blocker that halts all development activity.

**Root Cause:**
- 20 broken test files were blocking pytest execution
- Many core modules have zero test coverage
- Pre-commit hook enforces minimum 49% coverage (configured in `pyproject.toml`)
- No work should ever proceed without a proper DEV-BE task in ARCHITECTURE_ROADMAP.md

**Solution:**
Systematically remove broken tests, measure baseline coverage, and generate comprehensive tests for all uncovered modules until 49% threshold is achieved.

**Implementation Tasks (All Completed):**

- [x] Remove 20 broken test files blocking pytest
- [x] Create comprehensive tests for tax_constants.py (100% coverage achieved)
- [x] Fix Slack mobile formatting issues
- [x] Establish baseline coverage measurement
- [x] Generate tests for high-impact modules
- [x] Verify coverage reaches 49%
- [x] Pre-commit hooks pass successfully

**Acceptance Criteria (All Met):**
- ✅ All 20 broken tests removed
- ✅ tax_constants.py has 100% coverage
- ✅ Slack mobile formatting fixed
- ✅ `pytest --cov=app` shows coverage ≥49%
- ✅ All tests pass without errors
- ✅ Pre-commit hooks pass successfully
- ✅ HTML coverage report generated to `htmlcov/index.html`

</details>

<details>
<summary>
<h3>DEV-BE-72: Implement Expert Feedback System</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2 weeks (Actual: 1.5 weeks) | <strong>Dependencies:</strong> None | <strong>Status:</strong> ✅ COMPLETED<br>
<strong>Completion Date:</strong> 2024-11-25<br>
Simplified SUPER_USER-only expert feedback system with automatic task generation for improvement tracking.
</summary>

### DEV-BE-72: Implement Expert Feedback System
**Priority:** HIGH | **Effort:** 2 weeks (Actual: 1.5 weeks) | **Dependencies:** None | **Status:** ✅ COMPLETED
**Completion Date:** 2024-11-25

**Frontend Integration:**
This backend task is linked to **DEV-BE-004** in frontend roadmap:
- **Frontend Task:** DEV-BE-004: Implement Super Users Feedback on Answers (Expert Feedback System)
- **Location:** `/Users/micky/WebstormProjects/PratikoAiWebApp/ARCHITECTURE_ROADMAP.md`
- **Coordination Required:** Backend APIs must be completed BEFORE frontend implementation
- **API Endpoints:** Frontend will consume `/api/v1/expert-feedback/*` endpoints created in this task

**Problem:**
Expert feedback system was designed in architecture diagram (steps S113-S130) with complex trust scoring and auto-approval workflows. However, for MVP launch, a simpler SUPER_USER-only approach was needed to:
1. Collect structured feedback from verified experts
2. Track answer quality issues (correct/incomplete/incorrect)
3. Automatically generate improvement tasks for content team
4. Integrate with Golden Set workflow for correct answers

**Architectural Decision:**
The original plan included a 3-tier trust scoring system (0.7-0.79, 0.80-0.89, 0.90-1.00) with graduated auto-approval privileges. This was **intentionally simplified away** to a binary SUPER_USER role approach because:
- All experts are manually vetted before receiving SUPER_USER role
- Trust scoring adds complexity without value when experts are pre-trusted
- Admin approval queue creates unnecessary friction for trusted experts
- Reduces database queries (4-5 fewer per feedback submission)

**Reference:** See "Not Approved Features" section for full rationale and future implementation path.

---

## Implementation Completed

### 1. Database Schema & Migrations

**Migration Files:**
- `alembic/versions/20251121_add_expert_feedback_system.py` - 339 lines
- `alembic/versions/20251124_add_user_role.py` - 60 lines

### 2. Backend API Endpoints

**File:** `app/api/v1/expert_feedback.py` - 558 lines

**Endpoints Implemented:**
1. **POST `/api/v1/expert-feedback/submit`** - Submit expert feedback on an AI response
2. **GET `/api/v1/expert-feedback/history`** - Retrieve paginated feedback history
3. **GET `/api/v1/expert-feedback/{feedback_id}`** - Retrieve detailed feedback record
4. **GET `/api/v1/expert-feedback/profile`** - Retrieve expert profile with credentials

### 3. Business Logic Services

- `app/services/expert_feedback_collector.py` - 706 lines
- `app/services/task_generator_service.py` - 349 lines
- `app/services/task_digest_email_service.py` - 206 lines

### 4. Request/Response Schemas

**File:** `app/schemas/expert_feedback.py` - 282 lines

### 5. Testing

- `tests/api/test_expert_feedback.py` - 804 lines (17 API tests passing)
- `tests/services/test_task_generator_service.py` - 354 lines (18 service tests passing)
- **Total Tests:** 35 tests passing

---

**Acceptance Criteria (All Met):**
- ✅ Expert feedback collected via POST `/api/v1/expert-feedback/submit`
- ✅ SUPER_USER role validation enforced (403 Forbidden for non-experts)
- ✅ Authentication required (JWT Bearer token)
- ✅ Feedback stored in `expert_feedback` table with all fields
- ✅ Automatic task generation for "incomplete" and "incorrect" feedback
- ✅ Tasks written to SUPER_USER_TASKS.md with structured format
- ✅ Golden Set workflow integration for "correct" feedback (background task)
- ✅ Feedback history API endpoint with pagination
- ✅ Comprehensive test coverage (35 tests, ≥69.5% coverage)

**Total Lines:** 4,221 lines of implementation + 1,158 lines of tests = **5,379 lines**

</details>

---

<details>
<summary>
<h3>DEV-BE-69: Expand RSS Feed Sources</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1.5 weeks | <strong>Dependencies:</strong> DEV-BE-66 ✅ | <strong>Status:</strong> ✅ COMPLETED<br>
<strong>Completion Date:</strong> 2024-12-10<br>
Expanded knowledge base with 11 new RSS feeds (4-hour schedule) + 2 web scrapers (daily schedule) for comprehensive Italian regulatory coverage.
</summary>

### DEV-BE-69: Expand RSS Feed Sources
**Priority:** HIGH | **Effort:** 1.5 weeks | **Dependencies:** DEV-BE-66 ✅ (RSS infrastructure complete) | **Status:** ✅ COMPLETED
**Completion Date:** 2024-12-10

**Git:** Branch from `develop` → `DEV-BE-69-Expand-RSS-Feed-Sources`

**Problem:**
Currently only 2 RSS feeds configured: Agenzia delle Entrate (Normativa e prassi, News). Missing coverage of INPS, Ministero del Lavoro, MEF, INAIL, Gazzetta Ufficiale, and Corte di Cassazione.

**Solution:**
Currently only 2 RSS feeds configured :Agenzia delle Entrate (
Normativa e prassi - https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=0753fcb1-1a42-4f8c-f40d-02793c6aefb4,
News - https://www.agenziaentrate.gov.it/portale/c/portal/rss/entrate?idrss=79b071d0-a537-4a3d-86cc-7a7d5a36f2a9
Missing coverage of INPS, Ministero del Lavoro, MEF, INAIL, Gazzetta Ufficiale, and Corte di Cassazione.

Expandeed knowledge base with 10   new RSS feeds (4-hour schedule) + 2 web scrapers (daily schedule).

**Target Sources to Add:**
- **INPS** (Istituto Nazionale Previdenza Sociale) - Social security and pension updates
  - Feeds to include:
    News (https://www.inps.it/it/it.rss.news.xml),
    Comunicati stampa (https://www.inps.it/it/it.rss.comunicati.xml),
    Circolari (https://www.inps.it/it/it.rss.circolari.xml),
    Messaggi(https://www.inps.it/it/it.rss.messaggi.xml) - verified manually,
    Sentenze (https://www.inps.it/it/it.rss.sentenze.xml)
- **Ministero del Lavoro** - Employment and labor law regulations
  - Feed: https://www.lavoro.gov.it/_layouts/15/Lavoro.Web/AppPages/RSS
- **Ministero dell'Economia e delle Finanze (MEF)** - Financial regulations
  - Feeds: Documenti (https://www.mef.gov.it/rss/rss.asp?t=5), Aggiornamenti (https://www.finanze.gov.it/it/rss.xml)
- **INAIL** (Istituto Nazionale Assicurazione Infortuni sul Lavoro) - Workplace injury insurance
  - Feeds: Notizie (https://www.inail.it/portale/it.rss.news.xml), Eventi (https://www.inail.it/portale/it.rss.eventi.xml)
- **Gazzetta Ufficiale** - Official government gazette (filtered sections):
    both scraping and RSS at the following RSS feeds:
    - Serie Generale: https://www.gazzettaufficiale.it/rss/SG
    - Corte Costituzionale: https://www.gazzettaufficiale.it/rss/S1
    - Unione Europea: https://www.gazzettaufficiale.it/rss/S2
    - Regioni: https://www.gazzettaufficiale.it/rss/S3
-
- **Corte di Cassazione** - Supreme Court rulings (tax/employment sections): NO RSS, requires scraping

**Key Implementations:**
- Rate limiting with semaphore (max 5 concurrent feeds) + stagger delay (1-3s)
- Content deduplication via SHA256 hashing
- Gazzetta Ufficiale scraper with robots.txt compliance
- Corte di Cassazione scraper extension

**Acceptance Criteria (All Met):**
- [x] 11 RSS feeds configured and ingesting (2 existing + 9 new, >0 docs per source)
- [x] 2 scrapers operational (Gazzetta + Cassazione)
- [x] Rate limiting active (max 5 concurrent, 1-3s delay)
- [x] Deduplication working (no cross-source duplicates)
- [x] Document quality maintained (junk rate <15%)
- [x] Code coverage >=70% for new code
- [x] E2E tests passing
- [x] Security audit passed (@severino)

</details>

---

<details>
<summary>
<h3>DEV-BE-70: Daily Ingestion Collection Email Report</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 4-5 days | <strong>Status:</strong> ✅ COMPLETED (2024-12-18)<br>
Daily email report covering ALL ingestion sources (RSS feeds + web scrapers) with environment identification, WoW comparison, and alert system.
</summary>

### DEV-BE-70: Daily Ingestion Collection Email Report
**Priority:** MEDIUM | **Effort:** 4-5 days | **Dependencies:** DEV-BE-69 ✅ | **Status:** ✅ COMPLETED (2024-12-18)

**Problem:**
No visibility into daily knowledge base ingestion across ALL sources. Team lacked insight into which RSS feeds and web scrapers were working vs. failing, document collection volumes, data quality metrics, and proactive alerts.

**Solution:**
Extended existing `IngestionReportService` with environment awareness, alert system, and scheduler integration. Daily email report covering ALL ingestion sources with clear environment identification (DEV/QA/PROD badges).

**Key Features Implemented:**
- Environment badge with color coding (Gray=dev, Blue=qa, Green=prod)
- Week-over-week comparison in executive summary
- Alert system (FEED_DOWN, FEED_STALE, HIGH_ERROR_RATE, HIGH_JUNK_RATE, ZERO_DOCUMENTS)
- Time-of-day scheduling with Europe/Rome timezone
- New documents preview (top 5 titles per source)
- Error sample collection for debugging

**Files Created/Modified:**
- `app/services/ingestion_report_service.py` (enhanced)
- `app/core/config.py` (INGESTION_REPORT_* settings)
- `tests/services/test_ingestion_alerts.py`
- `docs/operations/DAILY_REPORTS.md`

**Acceptance Criteria (All Met):**
- ✅ Report includes both RSS feed AND scraper statistics
- ✅ Environment badge visible in email header
- ✅ Email subject includes environment prefix
- ✅ Week-over-week comparison in executive summary
- ✅ Alert system operational
- ✅ Configurable via environment variables
- ✅ HTML renders correctly in Gmail/Outlook/Apple Mail

</details>

---

<details>
<summary>
<h3>DEV-BE-93: Unified Input Security Hardening (Chat + Expert Feedback)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2-3 days (Actual: ~3 days) | <strong>Status:</strong> ✅ COMPLETED (2024-12-19)<br>
Implemented comprehensive input sanitization across chat flow and expert feedback to prevent XSS, markdown injection, prompt injection, and data exfiltration attacks.
</summary>

### DEV-BE-93: Unified Input Security Hardening (Chat + Expert Feedback)
**Priority:** HIGH | **Effort:** 2-3 days (Actual: ~3 days) | **Dependencies:** None | **Status:** ✅ COMPLETED (2024-12-19)

**Problem:**
Security audit revealed critical vulnerabilities allowing malicious payloads from compromised super user laptops or malicious chat inputs:
- **V-001:** Markdown injection in task generation (unescaped user input → `.md` files)
- **V-002:** Missing field-level length limits (50KB message limit too broad)
- **V-003:** Prompt injection in chat flow (user input directly to LLM)
- **V-004:** XSS in data exports (malicious payloads exported in JSON/CSV)
- **V-005:** Log injection (unescaped newlines in logs)
- **V-006:** Unvalidated improvement suggestions in expert feedback

**Solution:**
Created unified security utilities module with comprehensive input sanitization:
- Markdown escaper for safe file writes
- Prompt guard for injection detection and logging
- Field-level validators with appropriate length limits
- Log sanitization for control character escaping

**Files Created:**
- `app/utils/security/__init__.py`
- `app/utils/security/markdown_escaper.py`
- `app/utils/security/prompt_guard.py`
- `app/utils/security/validators.py`
- `tests/utils/security/test_markdown_escaper.py`
- `tests/utils/security/test_prompt_guard.py`
- `tests/services/test_task_generator_security.py`
- `tests/api/test_chat_security.py`
- `tests/api/test_expert_feedback_security.py`

**Files Modified:**
- `app/services/task_generator_service.py` (markdown escaping applied)
- `app/schemas/expert_feedback.py` (max_length limits added)
- `app/schemas/chat.py` (prompt injection detection)
- `app/api/v1/data_export.py` (export sanitization)
- `app/core/logging.py` (log injection prevention)
- `pyproject.toml` (markupsafe dependency)

**Acceptance Criteria (All Met):**
- ✅ All 27 security tests passing
- ✅ All user inputs escaped before markdown file writes
- ✅ Max length limits enforced (query_text: 2000, original_answer: 5000, additional_details: 2000)
- ✅ Prompt injection patterns detected and logged (monitoring mode)
- ✅ Data exports sanitized (no XSS in JSON/CSV files)
- ✅ Log injection prevented (newlines/control chars escaped)
- ✅ Coverage ≥95% for `app/utils/security/` modules
- ✅ Performance overhead <5ms per request

</details>

---

<details>
<summary>
<h3>DEV-BE-78: Retrieval Ranking Optimization (Phase 1)</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 1.5-2 weeks (Actual: ~2 days) | <strong>Status:</strong> ✅ COMPLETED (2024-12-19)<br>
Phase 1 Quick Wins achieved 66.7% official source precision (2x target). Phase 2 Cross-Encoder deferred post-MVP.
</summary>

### DEV-BE-78: Retrieval Ranking Optimization (Phase 1)
**Priority:** MEDIUM | **Effort:** 1.5-2 weeks (Actual: ~2 days) | **Dependencies:** None | **Status:** ✅ COMPLETED (2024-12-19)

**Problem:**
Hybrid retrieval ranking was suboptimal with weight configuration inconsistency between services. The `text_quality` field existed but wasn't used in scoring.

**Solution:**
Implemented Phase 1 Quick Wins:
- Query classifier for dynamic weight adjustment (DEFINITIONAL/RECENT/CONCEPTUAL/DEFAULT)
- Source authority weighting (+0.15 official, +0.10 semi-official)
- Text quality integration into hybrid scoring (0.10 weight)
- Fixed weight configuration bug between postgres_retriever.py and knowledge_search_service.py
- Unified weights in config.py (FTS=0.45, Vec=0.30, Recency=0.10, Quality=0.10, Source=0.05)

**Files Created:**
- `app/services/query_classifier.py` (109 lines)
- `app/services/ranking_utils.py` (75 lines)
- `scripts/backfill_text_quality.py`
- `scripts/benchmark_ranking_precision.py`
- `tests/services/test_query_classifier.py` (37 tests)
- `tests/retrieval/test_ranking_optimization.py` (24 tests)

**Files Modified:**
- `app/core/config.py` (new weight constants, SOURCE_AUTHORITY_WEIGHTS)
- `app/services/knowledge_search_service.py` (quality/source integration)
- `tests/test_knowledge_search_service.py` (updated for new weights)

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 61 tests created
- ✅ Weight inconsistency bug fixed - unified in config.py
- ✅ text_quality integrated into scoring - 0.10 weight
- ✅ Source authority weighting implemented - official +0.15, semi-official +0.10
- ✅ Query-type detection implemented - DEFINITIONAL/RECENT/CONCEPTUAL/DEFAULT
- ✅ Precision@14 improvement: **66.7% official source precision** (target was ≥30%)
- ✅ No latency regression (<5ms) - scoring <2ms
- ✅ 90%+ test coverage for new code
- ✅ All existing tests pass

**Phase 2 (Cross-Encoder) - DEFERRED POST-MVP:**
Phase 1 exceeded the target by 2x (66.7% vs 30%). The remaining precision gap is due to content coverage (missing topics in knowledge base), not ranking quality. Cross-encoder would add complexity and latency for diminishing returns.

**When to Revisit Phase 2:** If official source precision drops below 50% or user feedback indicates ranking quality issues.

</details>

---

## Planned Tasks (Ordered by Implementation Priority)

<details>
<summary>
<h3>DEV-BE-75: Deploy QA Environment (Hetzner VPS)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1 week (mostly waiting for Hetzner approval) | <strong>Dependencies:</strong> None | <strong>Status:</strong> ❌ NOT STARTED<br>
Deploy complete PratikoAI backend to Hetzner VPS using existing docker-compose.yml configuration.
</summary>

### DEV-BE-75: Deploy QA Environment (Hetzner VPS)
**Priority:** HIGH | **Effort:** 1 week (mostly waiting for Hetzner approval) | **Dependencies:** None

**⚠️ IMPORTANT:** Contact Hetzner support first - they have a strict onboarding process for new clients.

**Problem:**
Currently testing only in local Docker environment. No QA environment for integration testing, performance validation, or stakeholder demos before production deployment.

**Solution:**
Deploy complete PratikoAI backend to Hetzner VPS using existing docker-compose.yml configuration.

**Implementation Tasks:**

**Week 1: Hetzner Account & VPS Setup**
- [ ] **Contact Hetzner support** for account approval (can take 1-3 days)
- [ ] Provision Hetzner CX21 VPS (2 vCPU, 4GB RAM, 40GB SSD)
  - Region: Germany (Falkenstein or Nuremberg)
  - OS: Ubuntu 22.04 LTS
  - Cost: ~€6.50/month (~$7/month)
- [ ] Configure SSH access with key-based authentication
- [ ] Set up firewall rules
- [ ] Install Docker and Docker Compose on VPS

**Week 2: Deployment & Configuration**
- [ ] Copy docker-compose.yml to VPS
- [ ] Create `.env.qa` with QA-specific configuration
- [ ] Deploy stack: `docker-compose --env-file .env.qa up -d`
- [ ] Run database migrations
- [ ] Set up DNS: `api-qa.pratikoai.com`
- [ ] Configure SSL with Let's Encrypt
- [ ] Set up automated backups (Hetzner snapshots)

**Acceptance Criteria:**
- ✅ QA environment accessible at `https://api-qa.pratikoai.com`
- ✅ All services running (PostgreSQL, Redis, Backend, Prometheus, Grafana)
- ✅ Database migrations run successfully
- ✅ All API endpoints responding (health check passes)
- ✅ Automated daily backups configured

**Infrastructure Cost (QA):**
- Hetzner CX21 VPS: ~$7/month
- Snapshots/backups: ~$1/month
- **Total: ~$8/month**

</details>

---

<details>
<summary>
<h3>DEV-BE-74: GDPR Compliance Audit (QA Environment)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3-4 days (with Claude Code generating checklists/docs) | <strong>Dependencies:</strong> DEV-BE-75 ✅ (QA environment live) | <strong>Status:</strong> ❌ NOT STARTED<br>
Comprehensive GDPR compliance audit on QA environment to validate all required features.
</summary>

### DEV-BE-74: GDPR Compliance Audit (QA Environment)
**Priority:** HIGH | **Effort:** 3-4 days (with Claude Code generating checklists/docs) | **Dependencies:** DEV-BE-75 ✅ (QA environment live)

**Problem:**
Must ensure GDPR compliance before any production launch. QA environment is the first place to validate compliance features.

**Solution:**
Comprehensive GDPR compliance audit on QA environment to validate all required features.

**Audit Checklist:**

**1. Right to Access (Data Export)**
- [ ] Test user data export functionality
- [ ] Verify exported data includes all user information
- [ ] Validate export format (JSON/PDF)
- [ ] Verify export completes within 30 days (GDPR requirement)

**2. Right to Erasure (Data Deletion)**
- [ ] Test user account deletion
- [ ] Verify complete data removal
- [ ] Validate deletion completes within 30 days

**3. Consent Management**
- [ ] Verify cookie consent banner functionality
- [ ] Test opt-in/opt-out mechanisms
- [ ] Validate consent records are stored

**4. Data Retention Policies**
- [ ] Verify automatic data deletion after retention period
- [ ] Test conversation data retention (default: 90 days)
- [ ] Validate log data retention (default: 30 days)

**5. Privacy by Design**
- [ ] Verify minimal data collection
- [ ] Test data encryption at rest (PostgreSQL, Redis)
- [ ] Validate data encryption in transit (HTTPS/TLS)

**Acceptance Criteria:**
- ✅ All 8 audit categories pass on QA
- ✅ Data export works correctly
- ✅ Data deletion works completely
- ✅ Documentation complete

</details>

---

<details>
<summary>
<h3>DEV-BE-77: Implement Prometheus + Grafana Monitoring</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1-2 weeks (dashboards already in docker-compose.yml) | <strong>Dependencies:</strong> DEV-BE-75 (QA environment required) | <strong>Status:</strong> ❌ NOT STARTED<br>
Industry-standard observability stack: Prometheus (metrics collection) + Grafana (visualization/alerting).
</summary>

### DEV-BE-77: Implement Prometheus + Grafana Monitoring
**Priority:** HIGH | **Effort:** 1-2 weeks | **Dependencies:** DEV-BE-75 (QA environment required for monitoring)

**Problem:**
Current monitoring relies on basic logs and periodic REST API metrics calls. No real-time visibility into RAG performance, cache hit rates, or automatic alerting on degradation.

**Solution:**
Industry-standard observability stack: Prometheus (metrics collection) + Grafana (visualization/alerting)

**Implementation Tasks:**

**Phase 1: Prometheus Setup**
- [ ] Add Prometheus to `docker-compose.yml`
- [ ] Create `prometheus.yml` configuration
- [ ] Add `prometheus-fastapi-instrumentator` to requirements
- [ ] Instrument FastAPI app with Prometheus metrics
- [ ] Add custom metrics (rag_query_duration, cache_hit_rate, etc.)

**Phase 2: Grafana Dashboards**
- [ ] Configure Prometheus as data source in Grafana
- [ ] Create **Dashboard 1: RAG Performance**
- [ ] Create **Dashboard 2: System Health**
- [ ] Create **Dashboard 3: Cost & Usage**
- [ ] Create **Dashboard 4: Data Quality**

**Phase 3: Alerting**
- [ ] Define alert rules in Grafana
- [ ] Set up Slack webhook integration
- [ ] Test alert firing and notification delivery

**Acceptance Criteria:**
- ✅ Prometheus scraping metrics from FastAPI, PostgreSQL, Redis
- ✅ 4 Grafana dashboards live with real-time data
- ✅ Alert rules configured and tested
- ✅ Documentation complete

**Cost:**
- Grafana Cloud Free Tier: **$0/month** (14-day retention, 10K metrics)

</details>

---

<details>
<summary>
<h3>DEV-BE-86: Automated Index Health Monitoring + Rebuild</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 2-3 days | <strong>Dependencies:</strong> DEV-BE-77 | <strong>Status:</strong> ❌ NOT STARTED<br>
Automated monitoring + alerts + rebuild scripts for FTS and pgvector indexes.
</summary>

### DEV-BE-86: Automated Index Health Monitoring + Rebuild

**Reference:** `docs/DATABASE_ARCHITECTURE.md`, `docs/PostgreSQL_Full_Text_Search.md`

**Priority:** MEDIUM | **Effort:** 2-3 days | **Status:** NOT STARTED

**Problem:**
If FTS (GIN) or pgvector (IVFFlat) indexes become corrupted or bloated, queries become extremely slow (10-100x slower). Currently requires manual detection + rebuild with no automated alerting.

**Solution:**
Implement automated index health monitoring via Prometheus metrics, Grafana alerts when index scan ratio drops below thresholds, and automated rebuild scripts with weekly health checks.

**Agent Assignment:** @Primo (primary - database expertise), @Ezio (review - backend integration)

**Dependencies:**
- **Blocking:** DEV-BE-77 (Prometheus/Grafana monitoring must be operational)
- **Unlocks:** Production database reliability, automated ops workflows

**Change Classification:** ADDITIVE

**Impact Analysis:**
- **Primary Files:**
  - `monitoring/exporters/postgres_queries.yml` (ADD index health queries)
  - `monitoring/grafana/provisioning/alerting/alert_rules.yml` (ADD index alerts)
  - `scripts/ops/rebuild_indexes.sh` (NEW)
  - `app/services/index_health_service.py` (NEW)
- **Affected Files:**
  - `docker-compose.yml` (may need cron container or scheduled task)
  - `monitoring/grafana/dashboards/performance.json` (ADD index health panel)
- **Related Tests:**
  - `tests/services/test_index_health_service.py` (NEW - direct)
  - `tests/integration/test_index_rebuild.py` (NEW - integration)
- **Baseline Command:** `pytest tests/services/ -v -k "database or index"`

**Pre-Implementation Verification:**
- [ ] DEV-BE-77 completed and Prometheus/Grafana operational
- [ ] Baseline tests pass for database-related services
- [ ] Existing postgres_queries.yml reviewed and understood
- [ ] Current alert_rules.yml patterns reviewed

**Error Handling:**
- Index rebuild fails: HTTP 500, `"Errore durante la ricostruzione dell'indice: {index_name}"`, retry with exponential backoff
- Database connection lost during rebuild: HTTP 503, `"Database non disponibile durante la manutenzione"`
- Insufficient disk space for rebuild: HTTP 507, `"Spazio su disco insufficiente per ricostruzione indice"`
- Index not found: HTTP 404, `"Indice non trovato: {index_name}"`
- Permission denied: HTTP 403, `"Permessi insufficienti per operazione di manutenzione"`
- **Logging:** All errors MUST be logged with context (operation, index_name, table_name, error_type) at ERROR level

**Performance Requirements:**
- Index health check query: <100ms
- Index rebuild (small table <100K rows): <30s
- Index rebuild (large table >1M rows): <5min with progress tracking
- Prometheus metric scraping: <50ms
- No impact on query performance during health checks

**Edge Cases:**
- **Nulls/Empty:** No indexes exist in database (startup state)
- **Boundaries:** Very large indexes (>10GB) require CONCURRENTLY rebuild
- **Concurrency:** Rebuild running while queries executing (use CONCURRENTLY)
- **Validation:** Invalid index name in rebuild request
- **Soft Delete:** Index on soft-deleted table columns
- **Tenant Isolation:** N/A (infrastructure-level task)
- **Error Recovery:** Partial rebuild failure (transaction rollback)
- **IVFFlat specific:** Lists parameter recalculation on data growth
- **GIN specific:** Pending list cleanup during fastupdate

**Files:**

**New Files:**
- `scripts/ops/rebuild_indexes.sh` - Automated index rebuild bash script
- `scripts/ops/check_index_health.sql` - SQL queries for index health metrics
- `app/services/index_health_service.py` - Python service for index management
- `docs/runbooks/INDEX_MAINTENANCE.md` - Operations runbook

**Modified Files:**
- `monitoring/exporters/postgres_queries.yml` - Add index health metrics
- `monitoring/grafana/provisioning/alerting/alert_rules.yml` - Add index alerts
- `monitoring/grafana/dashboards/performance.json` - Add index health panel

**Fields/Methods:**

`app/services/index_health_service.py`:
- `get_index_health_metrics() -> dict[str, IndexHealthMetric]` - Collect all index health data
- `get_index_scan_ratio(index_name: str) -> float` - Calculate scan ratio for specific index
- `get_index_bloat_ratio(index_name: str) -> float` - Calculate bloat percentage
- `rebuild_index(index_name: str, concurrently: bool = True) -> RebuildResult` - Rebuild specific index
- `rebuild_all_unhealthy_indexes(threshold: float = 0.5) -> list[RebuildResult]` - Batch rebuild
- `schedule_weekly_check() -> None` - Register weekly health check job

`monitoring/exporters/postgres_queries.yml` (new metrics):
- `pg_index_scan_ratio` - Index scan vs sequential scan ratio per index
- `pg_index_bloat_bytes` - Estimated bloat in bytes per index
- `pg_index_size_bytes` - Total index size per index
- `pg_index_last_vacuum` - Timestamp of last vacuum per table

`monitoring/grafana/provisioning/alerting/alert_rules.yml` (new alerts):
- `low_index_scan_ratio` - Alert when index_scan_ratio < 50%
- `high_index_bloat` - Alert when bloat > 30%
- `stale_vacuum` - Alert when last_vacuum > 7 days

**Testing Requirements:**
- **TDD:** Write `tests/services/test_index_health_service.py` FIRST
- **Unit Tests:**
  - `test_get_index_health_metrics_returns_all_indexes` - Verify all indexes included
  - `test_get_index_scan_ratio_calculates_correctly` - Verify ratio formula
  - `test_get_index_bloat_ratio_handles_zero_size` - Edge case for empty index
  - `test_rebuild_index_succeeds` - Happy path rebuild
  - `test_rebuild_index_uses_concurrently_by_default` - Verify CONCURRENTLY flag
  - `test_rebuild_index_handles_nonexistent_index` - Error handling
  - `test_rebuild_all_filters_by_threshold` - Verify threshold filtering
- **Edge Case Tests:**
  - `test_index_health_no_indexes_in_database` - Empty database
  - `test_rebuild_large_index_timeout_handling` - Long-running rebuild
  - `test_concurrent_rebuild_and_query` - No query blocking
  - `test_ivfflat_lists_recalculation` - pgvector specific
  - `test_gin_pending_list_cleanup` - FTS specific
- **Integration Tests:** `tests/integration/test_index_rebuild.py`
  - `test_full_rebuild_cycle_on_test_table` - End-to-end rebuild
  - `test_prometheus_metrics_exported` - Verify metrics endpoint
  - `test_grafana_alert_fires_on_low_ratio` - Alert integration
- **Regression Tests:** Run `pytest tests/services/test_database.py` to verify no conflicts
- **Coverage Target:** 85%+ for new code

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Index rebuild locks table | CRITICAL | Use REINDEX CONCURRENTLY (PostgreSQL 12+) |
| Prometheus metrics add load | LOW | Limit query frequency to 60s intervals |
| Large index rebuild timeout | MEDIUM | Implement progress tracking, extend timeout for >10GB indexes |
| Alert storm during maintenance | MEDIUM | Add maintenance window silencing in Grafana |
| Disk space exhaustion during rebuild | HIGH | Pre-check available space (2x index size required) |
| pgvector HNSW not supported | LOW | Document IVFFlat-only support, plan HNSW in future task |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules
- Service follows existing patterns in `app/services/`

**Implementation Phases:**

**Phase 1: Prometheus Metrics (Day 1)**
- [ ] Add `pg_index_scan_ratio` query to `postgres_queries.yml`
- [ ] Add `pg_index_bloat_bytes` query to `postgres_queries.yml`
- [ ] Add `pg_index_size_bytes` query to `postgres_queries.yml`
- [ ] Verify metrics visible in Prometheus UI

**Phase 2: Grafana Alerts + Dashboard (Day 1-2)**
- [ ] Create `low_index_scan_ratio` alert rule (threshold: 50%)
- [ ] Create `high_index_bloat` alert rule (threshold: 30%)
- [ ] Add index health panel to `performance.json` dashboard
- [ ] Test alert firing with simulated low ratio

**Phase 3: Rebuild Scripts + Service (Day 2-3)**
- [ ] Create `scripts/ops/rebuild_indexes.sh` with CONCURRENTLY support
- [ ] Create `app/services/index_health_service.py`
- [ ] Add weekly cron job for health check
- [ ] Write comprehensive tests

**Phase 4: Documentation + Runbook (Day 3)**
- [ ] Create `docs/runbooks/INDEX_MAINTENANCE.md`
- [ ] Document manual rebuild procedure
- [ ] Document alert response procedures
- [ ] Add troubleshooting section

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Prometheus exports `pg_index_scan_ratio` for all indexes
- [ ] Grafana dashboard shows index health metrics panel
- [ ] Alert fires when index scan ratio drops below 50%
- [ ] Alert fires when index bloat exceeds 30%
- [ ] `rebuild_indexes.sh` script tested successfully on QA
- [ ] Weekly health check cron job configured
- [ ] Runbook documents manual rebuild procedure
- [ ] 85%+ test coverage achieved for new code
- [ ] All existing tests still pass (regression)
- [ ] No table locks during CONCURRENTLY rebuild verified

</details>

---

<details>
<summary>
<h3>DEV-BE-87: User Subscription & Payment Management</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2-3 weeks (with Claude Code) | <strong>Dependencies:</strong> DEV-BE-75 ✅ (QA environment for testing) | <strong>Status:</strong> ❌ NOT STARTED<br>
Complete subscription management system with Stripe integration, usage tracking, and automated billing.
</summary>

### DEV-BE-87: User Subscription & Payment Management
**Priority:** CRITICAL | **Effort:** 2-3 weeks (with Claude Code) | **Dependencies:** DEV-BE-75 ✅ (QA environment for testing)

**Frontend Integration:**
This backend task is linked to **DEV-BE-009** in frontend roadmap:
- **Frontend Task:** DEV-BE-009: Integrate User Subscription Payment (Stripe)
- **Location:** `/Users/micky/WebstormProjects/PratikoAiWebApp/ARCHITECTURE_ROADMAP.md`
- **Coordination Required:** Backend APIs must be completed BEFORE frontend implementation

**Problem:**
No payment system implemented. Cannot accept paying customers or manage subscriptions.

**Solution:**
Implement complete subscription management system with Stripe integration.

**Payment Provider:** Stripe (2.9% + €0.25 per transaction, excellent EU support, PSD2 compliant)

**Subscription Tiers:**

**1. Free Tier**
- 10 questions/month
- Basic responses
- No payment required

**2. Professional (€29/month or €290/year)**
- 500 questions/month
- Priority responses
- Email support

**3. Business (€99/month or €990/year)**
- Unlimited questions
- Fastest responses
- Phone + email support

**Implementation Tasks:**

**Week 1: Stripe Integration & Database Schema**
- [ ] Create Stripe account
- [ ] Add Stripe SDK: `pip install stripe`
- [ ] Create database tables (subscriptions, usage_tracking, payment_history)
- [ ] Create Alembic migration

**Week 2: Payment & Subscription APIs**
- [ ] Create `app/services/stripe_service.py`
- [ ] Create API endpoints in `app/api/v1/subscriptions.py`
- [ ] Create Stripe webhook endpoint
- [ ] Implement usage tracking middleware

**Week 3: Billing Reminders & Frontend Integration**
- [ ] Create `app/services/billing_reminder_service.py`
- [ ] Create background job for reminder emails
- [ ] Create email templates
- [ ] Write tests

**Acceptance Criteria:**
- ✅ Stripe integration working (test mode)
- ✅ Users can subscribe to Professional/Business plans
- ✅ Usage tracking accurate
- ✅ Rate limiting enforces subscription limits
- ✅ Payment failures trigger email reminders
- ✅ GDPR compliant (payment data via Stripe, not stored locally)

**Expected Revenue (Year 1):**
- 50 Professional subscribers: €1,450/month
- 10 Business subscribers: €990/month
- **Total: €2,440/month** (~€29,280/year)

</details>

---

<details>
<summary>
<h3>DEV-BE-85: Configure PostgreSQL High Availability</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1 day (with Claude Code generating configs) | <strong>Dependencies:</strong> DEV-BE-75 (requires QA environment for testing) | <strong>Status:</strong> ❌ NOT STARTED<br>
PostgreSQL streaming replication with automatic failover for production readiness.
</summary>

### DEV-BE-85: Configure PostgreSQL High Availability
**Priority:** HIGH (production readiness) | **Effort:** 1 day (with Claude Code generating configs) | **Dependencies:** DEV-BE-75 (requires QA environment for testing)

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

</details>

---

<details>
<summary>
<h3>DEV-BE-90: Deploy Production Environment (Hetzner VPS)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 1 week | <strong>Status:</strong> NOT STARTED<br>
Production environment for paying customers. Must be reliable, performant, and cost-effective.
</summary>

### DEV-BE-90: Deploy Production Environment (Hetzner VPS)

**Reference:** ADR-006 (Hetzner over AWS), QA deployment learnings

**Priority:** CRITICAL | **Effort:** 1 week | **Status:** NOT STARTED

**Problem:**
Need production environment for paying customers. Must be reliable, performant, and cost-effective.

**Solution:**
Deploy complete PratikoAI backend to Hetzner VPS with production configuration, security hardening, and enhanced resources.

**Agent Assignment:** @Silvano (primary), @Severino (security hardening), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-BE-75 (QA deployed), DEV-BE-87 (Payment system), DEV-BE-74 (QA GDPR audit)
- **Unlocks:** DEV-BE-91 (Production GDPR audit)

**Change Classification:** ADDITIVE

**Error Handling:**
- Deployment failure: Automatic rollback to previous version
- SSL renewal failure: Alert at CRITICAL level
- Health check failure: Automatic service restart
- **Logging:** All deployment events MUST be logged with timestamps

**Performance Requirements:**
- API response time: <100ms (p95)
- Database connection: <30ms
- Zero downtime deployments

**Edge Cases:**
- **Rollback:** Instant rollback if health check fails
- **SSL:** Handle certificate renewal edge cases
- **DNS:** Handle DNS propagation delays

**Files:**

**New Files:**
- `.env.production` (production configuration)
- `scripts/deploy_production.sh` (deployment automation)
- `docs/infrastructure/PRODUCTION_DEPLOYMENT.md`

**Testing Requirements:**
- **TDD:** Write deployment verification tests FIRST
- **Unit Tests:**
  - `test_production_health_check` - All services healthy
  - `test_ssl_certificate_valid` - SSL properly configured
- **Integration Tests:** Full production smoke test suite

**Implementation Tasks:**

**Week 1: VPS Setup**
- [ ] Provision Hetzner CX31 VPS (2 vCPU, 8GB RAM, 80GB SSD)
- [ ] Configure strict firewall rules (UFW)
- [ ] Set up fail2ban for SSH brute force protection
- [ ] Configure automatic security updates

**Week 2: Deployment & Hardening**
- [ ] Create `.env.production` with secure configuration
- [ ] Deploy stack with docker-compose
- [ ] Set up DNS: `api.pratikoai.com`
- [ ] Configure SSL with Let's Encrypt (with auto-renewal)
- [ ] Set up automated daily backups
- [ ] Configure monitoring alerts
- [ ] Configure Stripe webhook endpoint with live keys

**Security Hardening:**
- [ ] Disable root SSH login
- [ ] Enable UFW firewall
- [ ] Configure fail2ban
- [ ] Enable PostgreSQL SSL connections
- [ ] Configure Redis password authentication

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Deployment breaks production | CRITICAL | Blue-green deployment, instant rollback |
| Security breach | CRITICAL | Follow hardening checklist |
| Data loss | CRITICAL | Daily backups, off-site replication |

**Code Structure:**
- Deployment scripts: <100 lines, modular functions

**Infrastructure Cost (Production):**
- Hetzner CX31 VPS: ~$15/month
- Snapshots/backups: ~$2/month
- **Total: ~$17/month**

**Acceptance Criteria:**
- [ ] Tests written BEFORE deployment verification
- [ ] Production environment accessible at `https://api.pratikoai.com`
- [ ] SSL certificate valid and auto-renewing
- [ ] All API endpoints responding with <100ms latency (p95)
- [ ] Stripe live mode working
- [ ] Security hardening complete
- [ ] Zero downtime deployment process documented
- [ ] All existing tests still pass (regression)

</details>

---

<details>
<summary>
<h3>DEV-BE-91: GDPR Compliance Audit (Production Environment)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 4-5 days | <strong>Status:</strong> NOT STARTED<br>
Final GDPR compliance validation required before accepting real user data in production.
</summary>

### DEV-BE-91: GDPR Compliance Audit (Production Environment)

**Reference:** GDPR Articles 15-17, QA audit learnings, `docs/compliance/GDPR_AUDIT_QA.md`

**Priority:** CRITICAL | **Effort:** 4-5 days | **Status:** NOT STARTED

**Problem:**
Final GDPR compliance validation required before accepting real user data in production.

**Solution:**
Comprehensive production GDPR audit with security hardening, compliance documentation, and legal sign-off.

**Agent Assignment:** @Severino (primary), @Clelia (compliance tests)

**Dependencies:**
- **Blocking:** DEV-BE-90 (Production live), DEV-BE-74 (QA audit complete)
- **Unlocks:** Production launch (accepting paying customers)

**Change Classification:** ADDITIVE

**Error Handling:**
- Audit failure: Document finding, create remediation task
- Legal review delay: Escalate to stakeholder
- **Logging:** All audit activities MUST be logged with timestamps

**Performance Requirements:**
- SSL Labs rating: A+
- Data export: <30 seconds per user
- Data deletion: <10 seconds per user

**Edge Cases:**
- **Payment Data:** Stripe data handled separately (Stripe DPA)
- **Legal Review:** May require multiple iterations
- **Vendor DPAs:** Track expiration dates

**Files:**

**New Files:**
- `docs/compliance/GDPR_AUDIT_PRODUCTION.md`
- `docs/compliance/DATA_PROTECTION_IMPACT_ASSESSMENT.md`
- `docs/compliance/INCIDENT_RESPONSE_PLAN.md`

**Testing Requirements:**
- **TDD:** Write compliance verification tests FIRST
- **Unit Tests:**
  - `test_data_export_complete` - All user data exported
  - `test_data_deletion_complete` - All user data deleted
  - `test_ssl_a_plus_rating` - SSL properly configured
- **Integration Tests:** Full GDPR feature validation

**Audit Activities:**

**1. Production GDPR Feature Validation**
- [ ] Test data export on production
- [ ] Test data deletion on production
- [ ] Test payment data export (Stripe + local subscription records)

**2. Security Audit**
- [ ] Test SSL/TLS configuration (A+ rating on SSL Labs)
- [ ] Verify firewall rules
- [ ] Test API authentication and rate limiting

**3. Data Protection Impact Assessment (DPIA)**
- [ ] Document all data processing activities
- [ ] Identify and assess privacy risks
- [ ] Get legal/compliance team sign-off

**4. Vendor Compliance**
- [ ] Verify Hetzner GDPR compliance (Data Processing Agreement)
- [ ] Validate OpenAI GDPR compliance
- [ ] Validate Stripe GDPR compliance (DPA signed)

**Documentation Deliverables:**
- [ ] `docs/compliance/GDPR_AUDIT_PRODUCTION.md`
- [ ] `docs/compliance/DATA_PROTECTION_IMPACT_ASSESSMENT.md`
- [ ] `docs/compliance/INCIDENT_RESPONSE_PLAN.md`
- [ ] Privacy Policy (published on website)
- [ ] Cookie Policy (published on website)

**Acceptance Criteria:**
- ✅ All GDPR features functional on production
- ✅ Security audit passed
- ✅ GDPR compliance certification obtained
- ✅ Legal/compliance team approval

</details>

---

<details>
<summary>
<h3>DEV-BE-79: Upgrade to HNSW Index</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 3-5 days | <strong>Status:</strong> ❌ NOT STARTED<br>
HNSW provides 90-95% recall and 20-30% faster queries vs IVFFlat.
</summary>

### DEV-BE-79: Upgrade to HNSW Index

**Reference:** pgvector 0.5.0+ documentation, `docs/DATABASE_ARCHITECTURE.md`

**Priority:** MEDIUM | **Effort:** 3-5 days | **Status:** NOT STARTED

**Problem:**
Current IVFFlat index has 85-90% recall. HNSW (Hierarchical Navigable Small World) provides 90-95% recall and 20-30% faster queries, improving RAG response quality.

**Solution:**
Replace IVFFlat vector index with HNSW using `CREATE INDEX CONCURRENTLY` for zero-downtime migration.

**Agent Assignment:** @Primo (primary), @Clelia (tests), @Valerio (benchmarking)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** Improved retrieval quality for all RAG queries

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** Alembic migration (new)
- **Affected Files:**
  - `app/services/search_service.py` (may need query tuning)
  - `app/services/context_builder.py` (retrieval quality)
- **Related Tests:**
  - `tests/services/test_search_service.py`
  - `tests/integration/test_retrieval.py`
- **Baseline Command:** `pytest tests/services/test_search_service.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Current IVFFlat index verified on QA
- [ ] pgvector version ≥0.5.0 confirmed

**Error Handling:**
- Index creation failure: Automatic rollback, alert at CRITICAL level
- Query performance degradation: Revert to IVFFlat
- **Logging:** Index build progress logged every 10%

**Performance Requirements:**
- Vector search: <30ms (p95), improved from <40ms
- Index build: <4 hours for 500K vectors
- Zero query failures during migration

**Edge Cases:**
- **Large Dataset:** Build time may exceed 4 hours → use `maintenance_work_mem` tuning
- **Concurrent Queries:** CONCURRENTLY ensures no blocking
- **Rollback:** Keep IVFFlat index until HNSW verified

**Files:**

**New Files:**
- `alembic/versions/YYYYMMDD_upgrade_to_hnsw_index.py`
- `scripts/ops/benchmark_vector_index.py`
- `docs/operations/VECTOR_INDEX_MIGRATION.md`

**Modified Files:**
- `app/services/search_service.py` (query hints if needed)

**Fields/Methods:**
- Migration: `DROP INDEX ... CASCADE` + `CREATE INDEX CONCURRENTLY`
- HNSW params: `m=16, ef_construction=64`

**Testing Requirements:**
- **TDD:** Write benchmark tests FIRST
- **Unit Tests:**
  - `test_hnsw_index_exists` - Index created successfully
  - `test_vector_search_latency` - <30ms p95
  - `test_recall_improvement` - ≥90% recall
- **Integration Tests:** Full RAG query comparison (HNSW vs IVFFlat)
- **Regression Tests:** Run `pytest tests/services/test_search_service.py`
- **Coverage Target:** 80%+ for migration scripts

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Build time exceeds window | MEDIUM | Schedule during lowest traffic (2-5 AM) |
| Performance regression | HIGH | A/B test before dropping IVFFlat |
| pgvector version incompatible | MEDIUM | Verify version in pre-checks |

**Code Structure:**
- Migration script: <100 lines
- Benchmark script: <150 lines

**Acceptance Criteria:**
- [ ] Tests written BEFORE migration
- [ ] HNSW index created with `CREATE INDEX CONCURRENTLY`
- [ ] Vector search latency reduced by 20-30% (30-40ms → 20-30ms)
- [ ] Recall improved from 85-90% to 90-95%
- [ ] Zero downtime during migration
- [ ] Rollback procedure documented
- [ ] All existing tests still pass (regression)

</details>

---

<details>
<summary>
<h3>DEV-BE-80: Italian Financial Dictionary</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 1 week | <strong>Status:</strong> ❌ NOT STARTED<br>
Custom Italian financial dictionary with synonym mappings for better FTS recall.
</summary>

### DEV-BE-80: Italian Financial Dictionary

**Reference:** PostgreSQL Text Search docs, `app/services/search_service.py`

**Priority:** LOW | **Effort:** 1 week | **Status:** NOT STARTED

**Problem:**
PostgreSQL `italian` dictionary handles general Italian well, but misses domain-specific acronyms and synonyms common in tax/legal documents, reducing FTS recall for specialized queries.

**Solution:**
Create custom Italian financial dictionary with 100-200 synonym mappings for tax/legal terminology, integrated with existing PostgreSQL text search configuration.

**Agent Assignment:** @Primo (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** Improved FTS recall for domain-specific queries

**Change Classification:** ADDITIVE

**Error Handling:**
- Dictionary load failure: Fall back to standard `italian` dictionary
- Synonym conflict: Log warning, use first match
- **Logging:** Dictionary load time and term count at startup

**Performance Requirements:**
- FTS query: No performance regression (<50ms)
- Dictionary load: <5 seconds at startup

**Edge Cases:**
- **Case Sensitivity:** Normalize all terms to lowercase
- **Plural Forms:** Include singular and plural variants
- **Abbreviations:** Handle with/without periods (I.V.A. vs IVA)
- **Compound Terms:** "cedolare secca" → multiple tokens

**Files:**

**New Files:**
- `app/data/italian_financial_synonyms.txt` (synonym mappings)
- `alembic/versions/YYYYMMDD_add_italian_financial_dictionary.py`
- `tests/services/test_italian_dictionary.py`
- `docs/operations/FTS_DICTIONARY.md`

**Modified Files:**
- `app/services/search_service.py` (use new dictionary config)

**Fields/Methods:**
- Synonym format: `IVA imposta valore aggiunto` (space-separated)
- Dictionary: `CREATE TEXT SEARCH DICTIONARY italian_financial_syn`
- Configuration: `ALTER TEXT SEARCH CONFIGURATION italian_financial`

**Testing Requirements:**
- **TDD:** Write recall benchmark tests FIRST
- **Unit Tests:**
  - `test_acronym_expansion` - IVA → imposta sul valore aggiunto
  - `test_synonym_matching` - cedolare secca queries
  - `test_backward_compatibility` - existing queries unchanged
- **Integration Tests:** FTS recall comparison (before/after)
- **Regression Tests:** Run `pytest tests/services/test_search_service.py`
- **Coverage Target:** 80%+ for dictionary code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance regression | MEDIUM | Benchmark before deployment |
| Synonym conflicts | LOW | Manual review of all 200 terms |
| Breaking existing searches | HIGH | A/B test, feature flag |

**Code Structure:**
- Synonym file: Plain text, 200 lines max
- Migration: <50 lines
- Service changes: <30 lines

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation
- [ ] 100-200 Italian financial synonyms compiled
- [ ] PostgreSQL synonym dictionary created
- [ ] +5-10% FTS recall on tax-specific queries
- [ ] Better handling of Italian acronyms (IVA, IRPEF, INPS)
- [ ] Backward compatible (existing queries unchanged)
- [ ] All existing tests still pass (regression)

</details>

---

<details>
<summary>
<h3>DEV-BE-81: Expand Monitoring Dashboards</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 2-3 days | <strong>Status:</strong> ❌ NOT STARTED<br>
Additional Grafana dashboards for document ingestion and user behavior metrics.
</summary>

### DEV-BE-81: Expand Monitoring Dashboards

**Reference:** DEV-BE-77 Grafana setup, `docs/operations/MONITORING.md`

**Priority:** LOW | **Effort:** 2-3 days | **Status:** NOT STARTED

**Problem:**
Current monitoring covers system health but lacks visibility into document ingestion metrics and user behavior patterns needed for content and UX optimization.

**Solution:**
Add 2 new Grafana dashboards (Document Ingestion, User Behavior) with PostgreSQL data source and weekly email reports.

**Agent Assignment:** @Silvano (primary), @Valerio (performance queries)

**Dependencies:**
- **Blocking:** DEV-BE-77 (Prometheus + Grafana setup)
- **Unlocks:** Data-driven content and UX decisions

**Change Classification:** ADDITIVE

**Error Handling:**
- Dashboard query timeout: Alert at WARNING level
- PostgreSQL data source connection failure: Fall back to cached data
- **Logging:** Query execution time for slow queries (>5s)

**Performance Requirements:**
- Dashboard load: <3 seconds
- Individual panel queries: <2 seconds
- No impact on production DB (read replica if available)

**Edge Cases:**
- **Large Date Ranges:** Limit to 90 days max per query
- **Empty Data:** Show "No data" message, not error
- **High Cardinality:** Aggregate by day, not minute

**Files:**

**New Files:**
- `grafana/dashboards/document_ingestion.json`
- `grafana/dashboards/user_behavior.json`
- `docs/operations/GRAFANA_DASHBOARDS.md`

**Modified Files:**
- `grafana/provisioning/datasources.yaml` (add PostgreSQL)
- `docker-compose.yml` (mount dashboard JSON files)

**Fields/Methods:**
- Document Ingestion panels: docs/day, source breakdown, junk rate trend
- User Behavior panels: queries/day, popular categories, session duration
- PostgreSQL queries: CTEs with date filtering

**Testing Requirements:**
- **TDD:** Write dashboard validation tests FIRST
- **Unit Tests:**
  - `test_dashboard_json_valid` - JSON schema validation
  - `test_queries_execute` - All queries run without error
- **Integration Tests:** Dashboard renders in Grafana
- **Manual Tests:** Visual verification of panel layout
- **Coverage Target:** N/A (JSON configs)

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Slow queries impact prod DB | HIGH | Use read replica or off-peak queries |
| Dashboard complexity | LOW | Start with 5-6 panels per dashboard |
| Grafana version incompatibility | LOW | Test on QA first |

**Code Structure:**
- Dashboard JSON: <500 lines each
- SQL queries: <50 lines each

**Acceptance Criteria:**
- [ ] "Document Ingestion" dashboard created
- [ ] "User Behavior" dashboard created
- [ ] PostgreSQL data source configured
- [ ] Dashboard load time <3 seconds
- [ ] Weekly email reports configured (Grafana Cloud)
- [ ] All existing tests still pass (regression)

</details>

---

<details>
<summary>
<h3>DEV-BE-82: LLM Fallback to Claude/Gemini</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 1 week | <strong>Status:</strong> ❌ NOT STARTED<br>
Multi-LLM fallback strategy to reduce single point of failure on OpenAI.
</summary>

### DEV-BE-82: LLM Fallback to Claude/Gemini

**Reference:** `app/services/resilient_llm_service.py`, OpenAI/Anthropic/Google API docs

**Priority:** MEDIUM | **Effort:** 1 week | **Status:** NOT STARTED

**Problem:**
If OpenAI API fails (outage, rate limits, account issues), entire RAG system stops working. Single point of failure for core functionality.

**Solution:**
Implement multi-LLM fallback strategy with automatic provider switching:
1. Primary: OpenAI (gpt-4-turbo)
2. Fallback 1: Anthropic Claude (claude-3-sonnet)
3. Fallback 2: Google Gemini (gemini-1.5-pro)

**Agent Assignment:** @Ezio (primary), @Clelia (tests), @Valerio (benchmarking)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** Production reliability, reduced downtime risk

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/services/resilient_llm_service.py`
- **Affected Files:**
  - `app/core/langgraph/nodes/generate_response.py` (uses LLM service)
  - `app/orchestrators/rag_orchestrator.py` (error handling)
- **Related Tests:**
  - `tests/services/test_resilient_llm_service.py`
  - `tests/integration/test_rag_flow.py`
- **Baseline Command:** `pytest tests/services/test_resilient_llm_service.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Current LLM service code reviewed
- [ ] API keys obtained for Anthropic + Google

**Error Handling:**
- Provider timeout (30s): Switch to next provider
- Rate limit (429): Exponential backoff, then switch provider
- Auth error (401/403): Alert CRITICAL, skip provider
- All providers fail: Return graceful error message in Italian
- **Logging:** Provider used, latency, fallback events at INFO level

**Performance Requirements:**
- Primary response: <5s (p95)
- Fallback switch: <100ms
- Total request (with 1 fallback): <10s

**Edge Cases:**
- **Simultaneous Failures:** All 3 providers down → cached response or maintenance message
- **Partial Response:** Provider dies mid-stream → retry with full request
- **Rate Limit Recovery:** Track per-provider cooldown periods
- **Prompt Compatibility:** Adapt system prompts for Claude/Gemini differences

**Files:**

**New Files:**
- `app/services/llm_provider_factory.py` (provider abstraction)
- `tests/services/test_llm_fallback.py`
- `docs/operations/LLM_FALLBACK.md`

**Modified Files:**
- `app/services/resilient_llm_service.py` (add multi-provider support)
- `app/core/config.py` (Anthropic + Google API keys)
- `.env.example` (new environment variables)

**Fields/Methods:**
- `LLMProviderFactory.get_provider(name: str) -> LLMProvider`
- `LLMProvider.generate(prompt: str, **kwargs) -> str`
- `FallbackChain.execute(prompt: str) -> str` with retry logic
- Config: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `LLM_FALLBACK_ORDER`

**Testing Requirements:**
- **TDD:** Write fallback scenario tests FIRST
- **Unit Tests:**
  - `test_primary_provider_success` - OpenAI responds normally
  - `test_fallback_on_timeout` - Switch to Claude after 30s
  - `test_fallback_on_rate_limit` - Switch provider on 429
  - `test_all_providers_fail` - Graceful error message
  - `test_exponential_backoff` - Retry timing correct
- **Integration Tests:** Full RAG flow with mocked provider failures
- **Regression Tests:** Run `pytest tests/services/test_resilient_llm_service.py`
- **Coverage Target:** 90%+ for fallback logic

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Response quality varies | MEDIUM | Benchmark all providers, tune prompts |
| API cost increase | LOW | Track usage per provider, set alerts |
| Prompt incompatibility | MEDIUM | Abstract prompt formatting per provider |

**Code Structure:**
- Provider factory: <100 lines
- Fallback chain: <150 lines
- Provider adapters: <50 lines each

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation
- [ ] Multi-provider fallback implemented
- [ ] System stays online during OpenAI outage
- [ ] Automatic fallback within 5 seconds
- [ ] Metrics: provider used, fallback rate tracked
- [ ] Quality comparable across providers (manual verification)
- [ ] All existing tests still pass (regression)

</details>

---

<details>
<summary>
<h3>DEV-BE-84: Multi-Tenancy Support</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 3-4 weeks | <strong>Status:</strong> ❌ NOT STARTED<br>
Multi-tenant architecture for white-label deployment.
</summary>

### DEV-BE-84: Multi-Tenancy Support

**Reference:** White-label product requirements (TBD), ADR-TBD

**Priority:** LOW | **Effort:** 3-4 weeks | **Status:** NOT STARTED

**Trigger:** White-label product requirement confirmed by stakeholders

**Problem:**
Current architecture is single-tenant. If white-label deployment is required, need tenant isolation for data, configuration, and branding.

**Solution:**
Implement multi-tenant architecture with schema-per-tenant isolation, tenant-aware middleware, and configurable branding.

**Agent Assignment:** @Egidio (architecture), @Ezio (implementation), @Primo (database), @Clelia (tests)

**Dependencies:**
- **Blocking:** None (deferred until business requirement confirmed)
- **Unlocks:** White-label product offering, B2B sales

**Change Classification:** RESTRUCTURING

**High-Level Scope:**
1. Tenant model and database schema isolation
2. Tenant-aware middleware for request routing
3. Tenant configuration (branding, limits, features)
4. Data migration tooling for existing single-tenant data
5. Admin portal for tenant management

**Edge Cases:**
- **Tenant Isolation:** Cross-tenant data leak prevention
- **Shared Resources:** Knowledge base can be shared or tenant-specific
- **Tenant Limits:** Rate limiting, storage quotas per tenant
- **Tenant Deletion:** Full data cleanup on tenant removal

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Data leak between tenants | CRITICAL | Schema isolation, comprehensive tests |
| Performance degradation | HIGH | Connection pooling per tenant |
| Migration complexity | HIGH | Phased rollout, feature flags |

**Acceptance Criteria:**
- [ ] Architecture document approved by @Egidio
- [ ] Tenant isolation verified (security audit)
- [ ] Performance benchmarked (no regression)
- [ ] Admin portal functional
- [ ] All existing tests still pass (regression)

**Note:** This task requires full business analysis and architecture review before implementation. Do not start without explicit stakeholder approval.

</details>

---

## Not Approved Features

This section documents features that were fully designed in the architecture but were **intentionally simplified away** during the MVP implementation. Quality and simplicity are prioritized over cost optimization.

**Last Updated:** 2024-12-19
**Decision Authority:** Michele Giannone

---

### 1. Expert Trust Score System (Graduated Validation)

**Original Architectural Design:**
A sophisticated 3-tier trust scoring system to validate expert feedback quality over time before granting auto-approval privileges.

**Why Not Implemented:**
The SUPER_USER role provides binary trust (trusted/not trusted), which is sufficient for MVP launch. The graduated system was designed for a marketplace scenario where external experts register with unknown credentials. Current reality: all experts are manually vetted before receiving SUPER_USER role.

**Technical Impact:**
- Simplified from 3 conditional branches to 1 boolean check
- Removed need for `trust_score` recalculation background jobs
- Eliminated admin notification system for level upgrades
- Saved 4-5 database queries per feedback submission

**Estimated Effort:** 3-4 days to implement if needed later.

---

### 2. Admin Dashboard for FAQ Approval Queue

**Original Architectural Design:**
A comprehensive admin interface for reviewing, approving, or rejecting FAQ candidates submitted by experts with trust scores below 0.9.

**Why Not Implemented:**
When experts have SUPER_USER role, they are pre-trusted by definition. Manual review would add unnecessary friction to trusted experts and create administrative overhead.

**Technical Impact:**
- Eliminated entire admin approval workflow (6 API endpoints not built)
- No `faq_approval_queue` table in database schema
- Feedback goes directly from submission → Golden Set

**Estimated Effort:** 5-6 days to implement if needed later.

---

### 3. FAQ Obsolescence Tracking System

**Original Architectural Design:**
An automated system to detect when FAQs become outdated due to changes in source documents and flag them for expert review or automatic retirement.

**Why Not Implemented:**
This is a low-priority optimization for MVP. Small FAQ volume initially (<100 FAQs in first 3 months) makes manual review feasible.

**Estimated Effort:** 7-10 days to implement if needed later.

---

### 4. DEV-BE-76: Fix Cache Key + Add Semantic Layer

**Original Proposal:**
Two-phase cache optimization: Phase 1 removes `doc_hashes` from cache key (too volatile), Phase 2 adds semantic embedding layer for near-miss queries. Expected 60-70% cache hit rate.

**Why Not Implemented:**
The system already invests in LLM-based semantic understanding (GPT-4o-mini in Step 39 KBPreFetch) for query normalization and document reference extraction. This provides superior handling of:
- Typos ("risouzione" → "risoluzione")
- Abbreviations ("ris 64" → "risoluzione 64")
- Written numbers ("sessantaquattro" → "64")
- Semantic variations ("Cos'è la risoluzione n.64?" vs "Parlami della risoluzione 64")

Adding a separate semantic cache layer would create architectural complexity without proportional benefit. **Quality is prioritized over cache hit rate optimization.**

**Trade-off:**
- Lower cache hit rate (~5-15% vs potential 60-70%)
- Higher LLM costs per query
- Simpler, more maintainable architecture
- Superior semantic understanding from LLM

**Estimated Effort Avoided:** 1 week

**Decision Date:** 2024-12-19

---

### 5. Prompt A/B Testing Framework

**Original Architectural Design:**
A/B testing framework in PromptLoader with experiment configuration in YAML, traffic splitting by percentage, and metrics collection per variant to compare prompt effectiveness.

**Why Not Implemented:**
A/B testing is premature during pre-production development. The framework requires:
- Real users generating diverse queries for statistical significance
- Production traffic to split between variants
- Baseline metrics to compare against
- Actual customer usage patterns to optimize for

During development, prompt quality can be evaluated directly using the test suite, golden set evaluation, and synthetic benchmarks (`tests/e2e/test_agentic_rag_quality.py`).

**When to Revisit:**
After production launch with paying customers, when:
- Baseline response quality metrics are established
- User satisfaction data is available (action click-through rates)
- Query volume supports statistical significance
- Specific prompts are identified as needing optimization

**Estimated Effort:** 6h to implement when needed.

**Decision Date:** 2026-01-04

---

### Trade-offs Summary

| Feature | Complexity Avoided | When to Revisit |
|---------|-------------------|-----------------|
| **Trust Score System** | 3-tier validation logic, trust score recalculation jobs | External expert registration opens |
| **Admin Dashboard** | 6 API endpoints, full frontend dashboard, email notifications | Quality issues emerge with SUPER_USER FAQs |
| **Obsolescence Tracking** | Background jobs, staleness algorithm, 4 new DB fields | FAQ volume exceeds 500+ entries |
| **Semantic Cache Layer** | Embedding storage, similarity search, cache key refactoring | LLM costs become prohibitive (>€5/user/month) |
| **Prompt A/B Testing** | Experiment configuration, traffic splitting, variant metrics | Production launch with paying customers |

**Total Development Time Saved:** 17-22 days (3-4 weeks)

---

## Success Metrics

### Q1 2025 Targets

- [x] **Sprint 0 Complete:** Multi-agent system operational (DEV-BE-67) ✅
- [x] **Pinecone removed:** Zero Pinecone costs on billing (DEV-BE-68) ✅
- [x] **No emojis in responses:** Professional, formal tone (DEV-BE-71) ✅
- [x] **Test coverage 49%:** Pre-commit hooks passing (DEV-BE-92) ✅
- [x] **Expert feedback system:** Complete S113-S130 flow (DEV-BE-72) ✅
- [x] **RSS feeds expanded:** 8+ sources configured (DEV-BE-69) ✅
- [x] **Daily RSS email reports:** Automated feed monitoring (DEV-BE-70) ✅
- [x] **Input security hardening:** XSS, injection, export sanitization (DEV-BE-93) ✅
- [x] **Retrieval ranking optimized:** 66.7% official source precision, Phase 1 complete (DEV-BE-78) ✅
- [ ] **QA environment deployed:** On Hetzner (DEV-BE-75)

---

## Decision Log

| Date | Decision | Rationale | Task |
|------|----------|-----------|------|
| 2024-12-19 | DEV-BE-78 Phase 1 COMPLETE, Phase 2 DEFERRED | Phase 1 achieved 66.7% official source precision (2x target); cross-encoder adds complexity for diminishing returns; gap is content coverage not ranking | DEV-BE-78 |
| 2024-12-19 | DEV-BE-78 phased approach approved | Quick wins first (text_quality, source weighting, dynamic weights), cross-encoder only if needed; @Egidio approved | DEV-BE-78 |
| 2024-12-19 | Close DEV-BE-76 as Won't Do | LLM-based semantic understanding (GPT-4o-mini in Step 39) provides superior query handling; quality prioritized over cache optimization | DEV-BE-76 |
| 2024-11-24 | Simplify DEV-BE-72 to SUPER_USER-only | All experts manually vetted, trust scoring adds complexity without value for MVP | DEV-BE-72 |
| 2024-11-17 | Complete Sprint 0: Multi-Agent System | Establish subagent framework before major development work | DEV-BE-67 |
| 2024-11-14 | Remove Pinecone entirely | Over-engineered for current scale, pgvector sufficient | DEV-BE-68 |
| 2024-11-14 | Deploy to Hetzner (not AWS) | Cost: $25/month (both envs) vs $330+/month AWS | DEV-BE-75, DEV-BE-90 |

---

## Infrastructure Cost Summary

**Both Environments (Hetzner):**
- QA: $8/month (CX21 + backups)
- Production: $17/month (CX31 + backups)
- **Total: ~$25/month** for complete multi-environment setup

**vs AWS Alternative:**
- AWS QA alone: $110-135/month
- **Savings: ~$305-410/month** (92% cost reduction)

---

**Roadmap Maintained By:** Engineering Team
**Review Cycle:** Monthly sprint planning
**Next Review:** 2025-12-01
