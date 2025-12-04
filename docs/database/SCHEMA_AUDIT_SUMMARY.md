# Schema Drift Audit - Executive Summary

**Date:** 2025-11-28
**Auditor:** Database Designer (Primo)
**Status:** 🔴 CRITICAL ISSUES FOUND - ACTION REQUIRED

---

## TL;DR - What You Need to Know

**The Good News:**
- ✅ Database schema is CORRECT (uses INTEGER for user_id)
- ✅ All 19 Alembic migrations applied successfully
- ✅ Foreign key constraints are working properly

**The Bad News:**
- ❌ **3 code files** declare UUID when database uses INTEGER
- ❌ **40 Base models** have NO tables in database (code-only)
- ❌ **Schema drift** between code declarations and database reality

**The Risk:**
- 🚨 SQLModel migration will FAIL if we don't fix UUID→Integer mismatches first
- 🚨 FK constraint errors when creating new tables with UUID foreign keys
- 🚨 Misleading code that doesn't match database

---

## Critical Findings

### Finding 1: Code Declares UUID, Database Uses INTEGER ⚠️

**3 files need fixing BEFORE SQLModel migration:**

1. **app/models/quality_analysis.py:88**
   - Code: `user_id: Mapped[UUID]`
   - Database: `user_id INTEGER`
   - Table: `expert_profiles` ✅ EXISTS

2. **app/models/subscription.py:184**
   - Code: `user_id = Column(UUID(...))`
   - Database: `user_id INTEGER`
   - Table: `subscriptions` ✅ EXISTS

3. **app/models/faq_automation.py:329**
   - Code: `approved_by = Column(PG_UUID(...))`
   - Database: TABLE DOESN'T EXIST ❌
   - Risk: Will fail when table created

**Impact:** BLOCKS SQLModel migration until fixed

---

### Finding 2: 44 Base Models, 0 Tables in Database ⚠️

**Why this happened:**
- Alembic ONLY tracks `SQLModel.metadata`
- Base models use separate `Base.metadata`
- Alembic autogenerate NEVER detected Base models
- Only 4 Base model tables exist (created by manual SQL)

**Missing Tables by File:**
- `regional_taxes.py` - 4 models, 0 tables
- `ccnl_database.py` - 9 models, 0 tables
- `ccnl_update_models.py` - 5 models, 0 tables
- `quality_analysis.py` - 9 models, 4 tables (5 missing)
- `faq_automation.py` - 5 models, 0 tables
- `subscription.py` - 4 models, 2 tables (2 missing)
- `data_export.py` - 8 models, 0 tables (2 conflicts with existing!)

**Impact:** MEDIUM - Code references tables that don't exist

---

### Finding 3: Migrations Used Correct Types (Despite Code) ✅

**Example:** `20251121_add_expert_feedback_system.py`

**Code declares:**
```python
user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(...), ...)
```

**Migration used:**
```sql
user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE
```

**Migration comment:**
```python
# NOTE: user_id is UUID but references user.id (INTEGER)
# This is intentional for future-proofing when user table migrates to UUID
```

**Conclusion:** Migration author MANUALLY overrode code declarations! ✅

---

### Finding 4: User Table is INTEGER (Source of Truth) ✅

```sql
-- Table: public.user
id | integer | not null | nextval('user_id_seq'::regclass)
```

**11 tables with INTEGER user_id + FK constraints:** ✅
- customers, document_analyses, documents, expert_faq_candidates,
  expert_profiles, faq_usage_logs, faq_variation_cache, invoices,
  payments, session, subscriptions

**9 tables with VARCHAR user_id, NO FK constraints:** ⚠️
- compliance_checks, cost_alerts, cost_optimization_suggestions,
  knowledge_feedback, query_normalization_log, tax_calculations,
  usage_events, usage_quotas, user_usage_summaries

---

## Recommended Action Plan

### ✅ RECOMMENDED: Option C - Hybrid Approach

**Phase 1: Fix Code Type Mismatches (IMMEDIATE)**
- Change 3 files: UUID → Integer declarations
- Timeline: 2 hours
- Risk: LOW
- Downtime: NONE

**Phase 2: Audit Missing Base Models (DECISION POINT)**
- Decide which 40 Base models to keep vs delete
- Timeline: 2 hours
- Risk: LOW
- Requires: Scrum Master + Architect approval

**Phase 3: Create Missing Tables (IF NEEDED)**
- Create Alembic migrations for needed tables
- Use INTEGER for all user_id foreign keys
- Timeline: 4 hours
- Risk: MEDIUM
- Downtime: NONE

**Phase 4: SQLModel Migration**
- Migrate Base models to SQLModel (file by file)
- Timeline: 6-8 hours
- Risk: MEDIUM
- Downtime: NONE

**Phase 5: Validation**
- Verify schema alignment
- Timeline: 2 hours
- Risk: LOW

**TOTAL TIMELINE:** 16-18 hours over 2-3 days
**DOWNTIME REQUIRED:** NONE

---

## What NOT To Do

### ❌ DO NOT: Migrate User Table to UUID

**Why this is a bad idea:**
- Requires downtime (30-60 minutes)
- Must update 11 FK constraints
- Must migrate all existing user IDs
- High risk of data corruption
- Difficult rollback
- Larger storage footprint (UUID = 16 bytes, INTEGER = 4 bytes)
- Slower index lookups

**Estimated effort:** 18-20 hours + downtime + high risk

**RECOMMENDATION:** Keep user.id as INTEGER

---

## Document Reference

This audit produced 4 detailed documents:

### 1. SCHEMA_DRIFT_AUDIT.md (Main Audit)
**Purpose:** Complete table-by-table comparison of code vs database

**Contents:**
- All 44 Base models analyzed
- Missing tables identified
- UUID vs INTEGER mismatches
- Alembic metadata issue explained
- Table name conflicts documented

**Use this for:** Understanding the full scope of schema drift

---

### 2. FK_ANALYSIS.md (User FK Deep Dive)
**Purpose:** Detailed analysis of all user.id foreign key references

**Contents:**
- All 20 user_id columns analyzed
- 11 proper FK constraints (INTEGER) ✅
- 9 VARCHAR columns without FKs ⚠️
- Code vs database comparison for each
- SQL validation queries

**Use this for:** Understanding user FK relationships and risks

---

### 3. MIGRATION_STRATEGY.md (Action Plan)
**Purpose:** Step-by-step plan to align schema before SQLModel migration

**Contents:**
- Option A: Fix code only (SAFEST)
- Option B: Migrate database to UUID (NOT RECOMMENDED)
- Option C: Hybrid approach (RECOMMENDED)
- Phased timeline with risk assessment
- Code change examples
- Rollback plans
- Success criteria

**Use this for:** Planning and executing the schema alignment

---

### 4. ALEMBIC_AUDIT.md (Migration History)
**Purpose:** Verify Alembic status and migration completeness

**Contents:**
- All 19 migrations listed
- Migration chain verified
- Base model migration gaps identified
- Expert feedback migration analysis (how it got types right)
- Alembic configuration explained

**Use this for:** Understanding why Base models have no migrations

---

## Immediate Next Steps

### Step 1: Review Documents (30 minutes)
**Who:** Scrum Master, Architect, Backend Expert
**What:** Read SCHEMA_AUDIT_SUMMARY.md (this file) + MIGRATION_STRATEGY.md
**Decision:** Approve Option C (Hybrid Approach)

---

### Step 2: Fix Critical Code Mismatches (2 hours)
**Who:** Backend Expert or Database Designer
**What:** Change UUID → Integer in 3 files
**Files:**
1. `app/models/quality_analysis.py:88`
2. `app/models/subscription.py:184`
3. `app/models/faq_automation.py:329`
4. `app/models/data_export.py` (8 locations)

**Code Change Pattern:**
```python
# BEFORE:
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)

# AFTER:
user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
```

**Testing:**
- Run pytest for affected models
- Test API endpoints: `/api/v1/expert_feedback/*`, `/api/v1/subscriptions/*`
- Verify FK constraints work

**Branch:** `fix/schema-alignment-user-id-types`
**PR Review:** Required before merge

---

### Step 3: Decide on Missing Base Models (2 hours)
**Who:** Scrum Master + Architect
**What:** Review list of 40 Base models, decide for each:
- [ ] Keep and create table (create migration)
- [ ] Keep as code-only (document as "future feature")
- [ ] Delete from codebase (not needed)

**Use:** MIGRATION_STRATEGY.md Phase 2 checklist

---

### Step 4: Create GitHub Issues (30 minutes)
**Who:** Scrum Master
**What:** Create issues for:
1. Phase 1: Fix UUID→Integer code mismatches
2. Phase 2: Audit and decide on Base models
3. Phase 3: Create migrations for needed tables
4. Phase 4: SQLModel migration (per file)

---

### Step 5: Execute Migration Strategy (16-18 hours)
**Who:** Backend Expert + Database Designer
**What:** Follow MIGRATION_STRATEGY.md Option C
**Timeline:** 2-3 days (allows testing between phases)

---

## Success Criteria

**Schema Alignment Successful When:**
- [ ] All user_id columns in code declare Integer (not UUID)
- [ ] All needed Base model tables exist in database
- [ ] All FK constraints use INTEGER → user(id)
- [ ] Alembic autogenerate shows no pending changes
- [ ] All tests pass
- [ ] API endpoints work
- [ ] No schema drift between code and database

**Ready for SQLModel Migration When:**
- [ ] All above criteria met
- [ ] Base models either migrated to SQLModel or deleted
- [ ] Only one metadata source (SQLModel.metadata)
- [ ] Schema validation tests in CI/CD

---

## Risk Assessment

### Current Risk Level: 🔴 HIGH

**Why HIGH:**
- Code doesn't match database (3 files with UUID declarations)
- 40 Base models have no tables (potential runtime errors)
- SQLModel migration will fail on FK constraints if not fixed

### After Phase 1: 🟡 MEDIUM

**Why MEDIUM:**
- Code matches database (UUID→Integer fixed)
- Still have missing Base model tables
- SQLModel migration unblocked

### After Phase 5: 🟢 LOW

**Why LOW:**
- All schema aligned
- Single metadata source
- Validation tests in place
- Ready for production

---

## Questions & Answers

### Q: Why did the expert_feedback migration work if code declares UUID?
**A:** Migration author MANUALLY wrote SQL with INTEGER, overriding the code declaration.

### Q: Should we migrate user.id to UUID to match code?
**A:** NO. Too risky, requires downtime, high effort (18-20 hours). Fix code instead (2 hours).

### Q: Why are 9 tables using VARCHAR for user_id?
**A:** Legacy tables or external system integrations. They don't have FK constraints (no referential integrity).

### Q: Can we proceed with SQLModel migration without fixing this?
**A:** NO. FK constraint errors will occur when Alembic tries to create foreign keys with UUID → INTEGER references.

### Q: How long will this delay the SQLModel migration?
**A:** Phase 1 (fix code) takes 2 hours. Can start SQLModel migration immediately after. No delay if we act fast.

### Q: What if we just delete all Base models?
**A:** Possible, but need to verify nothing references them. Some (like expert_profiles) are actively used.

---

## Approval Checklist

**Required Approvals:**
- [ ] **Scrum Master** - Approve timeline and phased approach
- [ ] **Architect** - Approve schema design decisions
- [ ] **Backend Expert** - Approve code changes and testing plan

**Decision Needed:**
- [ ] Approve Option C (Hybrid Approach) from MIGRATION_STRATEGY.md
- [ ] Assign developer for Phase 1 (fix code mismatches)
- [ ] Schedule review meeting for Phase 2 (Base model decisions)
- [ ] Set timeline for 2-3 day execution window

---

## Conclusion

**The database is correct. The code is wrong.**

**Immediate action required:**
1. Fix 3 files (UUID → Integer) - 2 hours
2. Decide on 40 missing Base models - 2 hours
3. Proceed with phased migration - 12-14 hours

**This audit prevents a catastrophic SQLModel migration failure.**

**Total effort to align schema: 16-18 hours over 2-3 days with ZERO downtime.**

---

## Contact

**Questions?** Contact:
- **Database Designer (Primo)** - Schema alignment, Alembic migrations
- **Architect** - Overall design decisions, SQLModel migration strategy
- **Scrum Master** - Timeline, prioritization, resource allocation

---

**Read the detailed documents for complete analysis:**
1. `SCHEMA_DRIFT_AUDIT.md` - Full audit findings
2. `FK_ANALYSIS.md` - User FK deep dive
3. `MIGRATION_STRATEGY.md` - Detailed action plan
4. `ALEMBIC_AUDIT.md` - Migration history analysis

---

**End of Summary**
