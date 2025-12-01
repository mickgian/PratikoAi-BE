# SQLModel Migration Strategy - Schema Alignment First

**Date:** 2025-11-28
**Author:** Database Designer (Primo)
**Status:** READY FOR REVIEW
**Risk Level:** HIGH → MEDIUM (after alignment)

---

## Executive Summary

**Critical Discovery:** Code declares UUID for user_id in 3 files, but database correctly uses INTEGER. We must align code with database BEFORE proceeding with SQLModel migration to prevent FK constraint failures.

**Recommended Strategy:** **Option C - Hybrid Approach**
1. Fix existing code type mismatches (UUID → Integer)
2. Create missing tables with correct types
3. Migrate existing tables to SQLModel
4. Validate schema alignment

**Timeline:** 6-8 hours spread over 2-3 days (includes testing)

---

## Option A: Fix Code to Match Database (SAFEST)

### Overview
Update all Base model UUID declarations to INTEGER to match database reality.

### Scope of Changes

#### Files to Modify (3 files)
1. `app/models/quality_analysis.py` - 1 line
2. `app/models/subscription.py` - 1 line
3. `app/models/faq_automation.py` - 1 line (table doesn't exist yet)

#### Code Changes Required

**1. app/models/quality_analysis.py:88**
```python
# BEFORE (WRONG):
user_id: Mapped[UUID] = mapped_column(
    PostgreSQLUUID(as_uuid=True),
    ForeignKey("user.id", use_alter=True, name="fk_expert_profiles_user_id"),
    nullable=False
)

# AFTER (CORRECT):
user_id: Mapped[int] = mapped_column(
    Integer,
    ForeignKey("user.id", name="fk_expert_profiles_user_id"),
    nullable=False
)
```

**2. app/models/subscription.py:184**
```python
# BEFORE (WRONG):
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)

# AFTER (CORRECT):
user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
```

**3. app/models/faq_automation.py:329**
```python
# BEFORE (WRONG):
approved_by = Column(
    PG_UUID(as_uuid=True),
    ForeignKey("user.id", use_alter=True, name="fk_generated_faqs_approved_by")
)

# AFTER (CORRECT):
approved_by = Column(
    Integer,
    ForeignKey("user.id", name="fk_generated_faqs_approved_by")
)
```

**4. app/models/data_export.py (8 locations)**
```python
# BEFORE (WRONG - lines 59, 227, 272, 310, 347, 379, 410, 442):
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)

# AFTER (CORRECT):
user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
```

### Pros
- ✅ Zero database changes required
- ✅ No downtime
- ✅ Preserves all existing data
- ✅ Low risk
- ✅ Aligns code with reality
- ✅ Quick to implement (1-2 hours)
- ✅ Easy to rollback (git revert)

### Cons
- ❌ Requires code changes in 4 files
- ❌ Must update type hints
- ❌ May affect application logic expecting UUID
- ❌ Requires testing of affected endpoints

### Testing Requirements
1. Run unit tests for affected models
2. Test API endpoints that use ExpertProfile, Subscription
3. Verify FK constraints still work
4. Check that ORM queries still work

### Rollback Plan
```bash
git revert <commit_hash>
# No database changes to rollback
```

### Timeline
- Code changes: 30 minutes
- Testing: 1 hour
- Code review: 30 minutes
- **Total: 2 hours**

---

## Option B: Migrate Database to Match Code (NOT RECOMMENDED)

### Overview
Change user.id from INTEGER to UUID to match code declarations.

### Scope of Changes

#### Database Changes Required
1. Create new UUID column in user table
2. Generate UUID for each existing user.id
3. Update all 11 FK references to use UUID
4. Drop old INTEGER user.id column
5. Rename UUID column to user.id

#### SQL Migration (COMPLEX!)
```sql
-- Step 1: Add UUID column
ALTER TABLE "user" ADD COLUMN id_uuid UUID DEFAULT gen_random_uuid();

-- Step 2: Populate UUID for existing users
UPDATE "user" SET id_uuid = gen_random_uuid();

-- Step 3: Create mapping table (user.id → user.id_uuid)
CREATE TEMP TABLE user_id_mapping AS
SELECT id as old_id, id_uuid as new_id FROM "user";

-- Step 4: Update ALL FK references (11 tables!)
ALTER TABLE customers ADD COLUMN user_id_uuid UUID;
UPDATE customers c SET user_id_uuid = m.new_id
FROM user_id_mapping m WHERE c.user_id = m.old_id;

ALTER TABLE document_analyses ADD COLUMN user_id_uuid UUID;
UPDATE document_analyses da SET user_id_uuid = m.new_id
FROM user_id_mapping m WHERE da.user_id = m.old_id;

-- ... repeat for 9 more tables!

-- Step 5: Drop old FK constraints
ALTER TABLE customers DROP CONSTRAINT customers_user_id_fkey;
ALTER TABLE document_analyses DROP CONSTRAINT document_analyses_user_id_fkey;
-- ... repeat for 9 more tables!

-- Step 6: Drop old INTEGER columns
ALTER TABLE customers DROP COLUMN user_id;
ALTER TABLE document_analyses DROP COLUMN user_id;
-- ... repeat for 9 more tables!

-- Step 7: Rename UUID columns
ALTER TABLE customers RENAME COLUMN user_id_uuid TO user_id;
ALTER TABLE document_analyses RENAME COLUMN user_id_uuid TO user_id;
-- ... repeat for 9 more tables!

-- Step 8: Add new FK constraints
ALTER TABLE customers ADD CONSTRAINT customers_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES "user"(id_uuid);
-- ... repeat for 10 more tables!

-- Step 9: Drop old user.id column
ALTER TABLE "user" DROP COLUMN id;
ALTER TABLE "user" RENAME COLUMN id_uuid TO id;

-- Step 10: Recreate primary key
ALTER TABLE "user" ADD PRIMARY KEY (id);
```

### Pros
- ✅ Code matches intent (UUID is more "modern")
- ✅ No code changes required
- ✅ UUIDs are globally unique

### Cons
- ❌ **REQUIRES DOWNTIME** (30-60 minutes for 100K+ users)
- ❌ **HIGH RISK** of data corruption
- ❌ Must update 11 FK constraints
- ❌ Must migrate all existing user IDs
- ❌ Requires full database backup
- ❌ Difficult to rollback
- ❌ May break external integrations expecting INTEGER
- ❌ Larger storage footprint (UUID = 16 bytes, INTEGER = 4 bytes)
- ❌ Slower index lookups (UUID vs INTEGER)
- ❌ May affect application sessions (if user_id cached)

### Risks
1. **Data Loss:** Migration fails halfway, orphaned records
2. **FK Constraint Failures:** Mismatch between old/new IDs
3. **Session Invalidation:** All logged-in users logged out
4. **External System Failures:** APIs expecting INTEGER user_id
5. **Performance Degradation:** UUID indexes slower than INTEGER

### Testing Requirements
1. Full database backup
2. Test on QA environment first
3. Dry-run migration on production replica
4. Verify all FK constraints exist
5. Verify all user sessions work
6. Test all API endpoints
7. Load test with UUIDs

### Rollback Plan
```sql
-- EXTREMELY COMPLEX - requires restoring from backup
-- and replaying all transactions since migration started
-- ESTIMATED ROLLBACK TIME: 2-4 hours
```

### Timeline
- Migration script development: 4 hours
- QA testing: 8 hours
- Production dry-run: 2 hours
- Backup creation: 1 hour
- Production migration: 1 hour (with downtime)
- Validation: 2 hours
- **Total: 18-20 hours + downtime**

### **RECOMMENDATION: DO NOT PURSUE THIS OPTION**

---

## Option C: Hybrid Approach (RECOMMENDED)

### Overview
1. Fix existing tables (use Option A for code)
2. Create missing tables with correct INTEGER types
3. Proceed with SQLModel migration
4. Validate schema alignment at each step

### Phase 1: Fix Existing Code Mismatches (IMMEDIATE)

**Scope:** 3 files with UUID declarations for existing tables

**Changes:**
1. Fix `quality_analysis.py:88` - ExpertProfile.user_id
2. Fix `subscription.py:184` - Subscription.user_id
3. Fix `faq_automation.py:329` - GeneratedFAQ.approved_by (no table yet)
4. Fix `data_export.py` - 8 models (no tables yet)

**Code Changes:**
```python
# Pattern for all 11 changes:
# OLD: Column(UUID(...), ForeignKey("user.id"), ...)
# NEW: Column(Integer, ForeignKey("user.id"), ...)

# OLD: Mapped[UUID] = mapped_column(PostgreSQLUUID(...), ForeignKey("user.id"), ...)
# NEW: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), ...)
```

**Testing:**
- Run pytest for quality_analysis, subscription models
- Test API endpoints: `/api/v1/expert_feedback/*`, `/api/v1/subscriptions/*`
- Verify FK constraints work

**Timeline:** 2 hours

---

### Phase 2: Audit Missing Base Model Tables (DECISION POINT)

**Scope:** Determine which of the 44 Base models are actually needed

**Questions for Each Model:**
1. Is this model used in application code?
2. Are there routes/services referencing it?
3. Was it planned for future features?
4. Should it be removed from codebase?

**Base Model Inventory:**

**regional_taxes.py (4 models):**
- [ ] Regione - Used? Future feature?
- [ ] Comune - Used? Future feature?
- [ ] RegionalTaxRate - Used? Future feature?
- [ ] ComunalTaxRate - Used? Future feature?

**ccnl_database.py (9 models):**
- [ ] CCNLSectorDB - Used? Future feature?
- [ ] CCNLAgreementDB - Used? Future feature?
- [ ] JobLevelDB - Used? Future feature?
- [ ] SalaryTableDB - Used? Future feature?
- [ ] WorkingHoursDB - Used? Future feature?
- [ ] OvertimeRulesDB - Used? Future feature?
- [ ] LeaveEntitlementDB - Used? Future feature?
- [ ] NoticePeriodsDB - Used? Future feature?
- [ ] SpecialAllowanceDB - Used? Future feature?

**ccnl_update_models.py (5 models):**
- [ ] CCNLDatabase - Used? Future feature?
- [ ] CCNLVersion - Used? Future feature?
- [ ] CCNLUpdateEvent - Used? Future feature?
- [ ] CCNLChangeLog - Used? Future feature?
- [ ] CCNLMonitoringMetric - Used? Future feature?

**quality_analysis.py (5 missing models):**
- [ ] PromptTemplate - Used? Future feature?
- [ ] FailurePattern - Used? Future feature?
- [ ] SystemImprovement - Used? Future feature?
- [ ] QualityMetric - Used? Future feature?
- [ ] ExpertValidation - Used? Future feature?

**faq_automation.py (5 models):**
- [ ] QueryCluster - Used? Future feature?
- [ ] FAQCandidate - Used? Future feature?
- [ ] GeneratedFAQ - Used? Future feature?
- [ ] RSSFAQImpact - Used? Future feature?
- [ ] FAQGenerationJob - Used? Future feature?

**subscription.py (2 missing models):**
- [ ] SubscriptionPlan - Used? Future feature?
- [ ] SubscriptionPlanChange - Used? Future feature?

**data_export.py (8 models):**
- [ ] DataExportRequest - Used? Future feature?
- [ ] ExportAuditLog - Used? Future feature?
- [ ] QueryHistory - Used? Future feature?
- [ ] DocumentAnalysis - CONFLICTS with existing table!
- [ ] TaxCalculation - CONFLICTS with existing table!
- [ ] FAQInteraction - Used? Future feature?
- [ ] KnowledgeBaseSearch - Used? Future feature?
- [ ] ElectronicInvoice - Used? Future feature?

**Decision Options:**
- **Option 1:** Delete unused Base models from codebase
- **Option 2:** Create tables for needed models (via Alembic migration)
- **Option 3:** Keep models but mark as "future feature" in comments

**Timeline:** 2 hours (requires Scrum Master / Architect review)

---

### Phase 3: Create Missing Tables (IF NEEDED)

**Scope:** Create Alembic migrations for needed Base models

**Migration Pattern:**
```python
# alembic/versions/YYYYMMDD_create_missing_base_tables.py

def upgrade():
    # Example: Create SubscriptionPlan table
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            description TEXT,
            billing_period VARCHAR(20) NOT NULL,  -- 'monthly' or 'yearly'
            base_price_cents INTEGER NOT NULL,
            stripe_price_id VARCHAR(255) UNIQUE NOT NULL,
            stripe_product_id VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            trial_period_days INTEGER DEFAULT 7,
            features JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX idx_subscription_plans_active ON subscription_plans(is_active);
        CREATE INDEX idx_subscription_plans_stripe_price ON subscription_plans(stripe_price_id);
    """)

    # Repeat for each needed table

def downgrade():
    op.drop_table('subscription_plans')
```

**Testing:**
1. Apply migration on QA database
2. Verify tables created with correct schema
3. Verify FK constraints work
4. Test ORM can query tables

**Timeline:** 4 hours (depends on number of tables)

---

### Phase 4: SQLModel Migration (MAIN MIGRATION)

**Scope:** Migrate existing Base models to SQLModel

**Approach:** Incremental file-by-file migration

**Priority Order:**
1. **quality_analysis.py** (4 models exist in DB)
2. **subscription.py** (2 models exist in DB)
3. **regional_taxes.py** (if tables created in Phase 3)
4. **faq_automation.py** (if tables created in Phase 3)
5. **ccnl_database.py** (if tables created in Phase 3)
6. **ccnl_update_models.py** (if tables created in Phase 3)
7. **data_export.py** (if tables created in Phase 3)

**Migration Pattern (Example: ExpertProfile):**
```python
# BEFORE (Base):
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey
Base = declarative_base()

class ExpertProfile(Base):
    __tablename__ = "expert_profiles"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID, primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    # ... rest of fields

# AFTER (SQLModel):
from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import UUID, uuid4

class ExpertProfile(SQLModel, table=True):
    __tablename__ = "expert_profiles"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    # ... rest of fields
```

**Testing Per File:**
1. Convert model file
2. Run pytest for that model
3. Test API endpoints using that model
4. Verify FK constraints work
5. Verify Alembic autogenerate shows no changes
6. Commit and move to next file

**Timeline:** 6-8 hours (1 hour per file)

---

### Phase 5: Validation & Cleanup

**Scope:** Verify schema alignment and clean up

**Validation Checklist:**
- [ ] All user_id columns are INTEGER
- [ ] All FK constraints exist
- [ ] No orphaned records
- [ ] Alembic autogenerate shows no pending changes
- [ ] All tests pass
- [ ] API endpoints work
- [ ] No Base models remain (or documented as future)

**SQL Validation Queries:**
```sql
-- 1. Verify all user_id are INTEGER
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE column_name IN ('user_id', 'approved_by')
    AND table_schema = 'public'
    AND data_type != 'integer';
-- Expected: 9 VARCHAR columns (legacy, no FK constraints)

-- 2. Verify all FK constraints exist
SELECT COUNT(*) as fk_count
FROM information_schema.table_constraints
WHERE constraint_type = 'FOREIGN KEY'
    AND constraint_name LIKE '%user_id%';
-- Expected: 11 FK constraints

-- 3. Check for orphaned records
SELECT 'expert_profiles' as table_name, COUNT(*) as orphaned
FROM expert_profiles WHERE user_id NOT IN (SELECT id FROM "user")
UNION ALL
SELECT 'subscriptions', COUNT(*)
FROM subscriptions WHERE user_id NOT IN (SELECT id FROM "user");
-- Expected: 0 orphaned records
```

**Timeline:** 2 hours

---

## Total Timeline Summary

### Option C (Recommended) - Phased Approach

| Phase | Description | Duration | Risk |
|-------|-------------|----------|------|
| 1 | Fix code type mismatches | 2 hours | LOW |
| 2 | Audit missing tables | 2 hours | LOW |
| 3 | Create missing tables (if needed) | 4 hours | MEDIUM |
| 4 | SQLModel migration | 6-8 hours | MEDIUM |
| 5 | Validation & cleanup | 2 hours | LOW |
| **TOTAL** | **16-18 hours** | **MEDIUM** |

**Spread Over:** 2-3 days (allows for testing between phases)

**Downtime Required:** NONE (all changes are additive or code-only)

---

## Risk Assessment

### Critical Risks (Option C)

**Risk 1: Code Change Breaks Existing Functionality**
- **Likelihood:** LOW
- **Impact:** MEDIUM
- **Mitigation:** Comprehensive testing, incremental changes
- **Rollback:** git revert (easy)

**Risk 2: Missing Table Migration Fails**
- **Likelihood:** LOW
- **Impact:** MEDIUM
- **Mitigation:** Test on QA first, use manual SQL (not autogenerate)
- **Rollback:** Drop tables, restore from backup

**Risk 3: SQLModel Migration Introduces Bugs**
- **Likelihood:** MEDIUM
- **Impact:** HIGH
- **Mitigation:** File-by-file migration, test each file, use type checking
- **Rollback:** git revert, no database changes

**Risk 4: Alembic Detects Unwanted Changes**
- **Likelihood:** MEDIUM
- **Impact:** LOW
- **Mitigation:** Run `alembic revision --autogenerate` after each file, review changes
- **Rollback:** Reject migration, fix code

**Risk 5: Performance Degradation**
- **Likelihood:** LOW
- **Impact:** MEDIUM
- **Mitigation:** No schema changes, INTEGER remains INTEGER
- **Rollback:** N/A (no performance changes expected)

---

## Rollback Plan

### Phase 1 Rollback (Code Changes)
```bash
git revert <commit_hash>
# Or: git reset --hard HEAD~1 (if not pushed)
```
**Time:** 5 minutes

### Phase 3 Rollback (Missing Tables)
```bash
alembic downgrade -1
# Or manual SQL: DROP TABLE IF EXISTS table_name CASCADE;
```
**Time:** 10 minutes

### Phase 4 Rollback (SQLModel Migration)
```bash
git revert <commit_hash>
# No database changes to rollback
```
**Time:** 5 minutes per file

---

## Success Criteria

### Phase 1 Success
- [ ] All 11 UUID → Integer changes committed
- [ ] All tests pass
- [ ] API endpoints work
- [ ] No runtime errors

### Phase 3 Success
- [ ] All needed tables created
- [ ] FK constraints exist
- [ ] No orphaned records
- [ ] ORM can query tables

### Phase 4 Success
- [ ] All Base models migrated to SQLModel
- [ ] Alembic shows no pending changes
- [ ] All tests pass
- [ ] API endpoints work

### Overall Success
- [ ] No Base models remain (or documented)
- [ ] All user_id columns are INTEGER with FK constraints (except 9 VARCHAR legacy)
- [ ] Code matches database schema
- [ ] Zero downtime
- [ ] All functionality preserved

---

## Approval & Sign-Off

**Requires Approval From:**
- [ ] Scrum Master - Phase planning, timeline approval
- [ ] Architect - Schema design approval, SQLModel migration strategy
- [ ] Backend Expert - Code review for Type changes, ORM changes

**Decision Needed:**
- [ ] Which missing Base models to keep vs delete (Phase 2)
- [ ] Whether to fix 9 VARCHAR user_id columns (optional)
- [ ] Timeline for execution (2-3 day window)

---

## Next Steps

**Immediate Actions:**
1. **Review this strategy document** with Scrum Master & Architect
2. **Get approval** for Option C (Hybrid Approach)
3. **Make decision** on missing Base models (Phase 2)
4. **Create GitHub issue** for Phase 1 (code fixes)
5. **Schedule work** for 2-3 day window

**Phase 1 Kickoff:**
1. Create feature branch: `fix/schema-alignment-user-id-types`
2. Fix 11 UUID → Integer changes
3. Run tests
4. Create PR for review
5. Merge to develop

**Phase 3 Kickoff (if needed):**
1. Create Alembic migration for missing tables
2. Test on QA
3. Apply to production
4. Validate

**Phase 4 Kickoff:**
1. Create feature branch: `migrate/sqlmodel-base-models`
2. Migrate one file at a time
3. Test each file
4. Create PRs for review
5. Merge incrementally

---

## Conclusion

**Recommended Strategy: Option C - Hybrid Approach**

**Why This Works:**
1. ✅ Aligns code with database reality (fixes UUID → Integer)
2. ✅ Creates missing tables with correct types (if needed)
3. ✅ Enables SQLModel migration without FK failures
4. ✅ Zero downtime
5. ✅ Low risk (incremental, testable, rollback-friendly)
6. ✅ Preserves all existing data and functionality

**Critical Success Factor:**
- Fix the 11 UUID → Integer code mismatches BEFORE creating any new tables or migrating to SQLModel

**This strategy prevents catastrophic FK constraint failures during migration.**

---

**End of Strategy Document**
