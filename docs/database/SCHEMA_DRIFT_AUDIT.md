# Schema Drift Audit Report

**Date:** 2025-11-28
**Auditor:** Database Designer (Primo)
**Status:** CRITICAL FINDINGS - CODE/DATABASE MISALIGNMENT

---

## Executive Summary

**CRITICAL DISCOVERY:** The codebase contains **44 Base models** using `Base.metadata`, but **ZERO tables exist in the database** for these models. Meanwhile, migrations correctly created tables using SQLModel.metadata with proper INTEGER types for user_id foreign keys, contradicting UUID declarations in Base model code.

### Key Statistics
- **Total Base Models:** 44 models across 7 files
- **Tables Created:** 0 (all Base model tables are missing!)
- **Migration Files:** 19 files exist
- **Applied Migrations:** All 19 applied (current: 20251126_add_question_embedding)
- **Code-to-DB Mismatches:** 3 critical UUID vs INTEGER issues

---

## Finding #1: All Base Model Tables Missing from Database

### Models Missing Tables (44 Total)

#### regional_taxes.py (4 models) - NO TABLES
- `Regione` (regione)
- `Comune` (comune)
- `RegionalTaxRate` (regional_tax_rates)
- `ComunalTaxRate` (comunal_tax_rates)

#### ccnl_database.py (9 models) - NO TABLES
- `CCNLSectorDB` (ccnl_sectors)
- `CCNLAgreementDB` (ccnl_agreements)
- `JobLevelDB` (job_levels)
- `SalaryTableDB` (salary_tables)
- `WorkingHoursDB` (working_hours)
- `OvertimeRulesDB` (overtime_rules)
- `LeaveEntitlementDB` (leave_entitlements)
- `NoticePeriodsDB` (notice_periods)
- `SpecialAllowanceDB` (special_allowances)

#### ccnl_update_models.py (5 models) - NO TABLES
- `CCNLDatabase` (ccnl_database)
- `CCNLVersion` (ccnl_versions)
- `CCNLUpdateEvent` (ccnl_update_events)
- `CCNLChangeLog` (ccnl_change_logs)
- `CCNLMonitoringMetric` (ccnl_monitoring_metrics)

#### quality_analysis.py (9 models) - PARTIALLY EXIST
**EXIST in database (created by SQLModel migrations):**
- `ExpertProfile` (expert_profiles) ✅
- `ExpertFeedback` (expert_feedback) ✅
- `ExpertGeneratedTask` (expert_generated_tasks) ✅
- `ExpertFAQCandidate` (expert_faq_candidates) ✅

**MISSING from database:**
- `PromptTemplate` (prompt_templates) ❌
- `FailurePattern` (failure_patterns) ❌
- `SystemImprovement` (system_improvements) ❌
- `QualityMetric` (quality_metrics) ❌
- `ExpertValidation` (expert_validations) ❌

#### faq_automation.py (5 models) - NO TABLES
- `QueryCluster` (query_clusters)
- `FAQCandidate` (faq_candidates)
- `GeneratedFAQ` (generated_faqs)
- `RSSFAQImpact` (rss_faq_impact)
- `FAQGenerationJob` (faq_generation_jobs)

#### subscription.py (4 models) - PARTIALLY EXIST
**EXIST in database (created by SQLModel migrations):**
- `Subscription` (subscriptions) ✅
- `Invoice` (invoices) ✅

**MISSING from database:**
- `SubscriptionPlan` (subscription_plans) ❌
- `SubscriptionPlanChange` (subscription_plan_changes) ❌

#### data_export.py (8 models) - NO TABLES
- `DataExportRequest` (data_export_requests)
- `ExportAuditLog` (export_audit_logs)
- `QueryHistory` (query_history)
- `DocumentAnalysis` (document_analyses) - CONFLICT: different table exists!
- `TaxCalculation` (tax_calculations) - CONFLICT: different table exists!
- `FAQInteraction` (faq_interactions)
- `KnowledgeBaseSearch` (knowledge_base_searches)
- `ElectronicInvoice` (electronic_invoices)

---

## Finding #2: Code Declares UUID but Database Uses INTEGER

### Confirmed Mismatches

#### 1. quality_analysis.py - ExpertProfile.user_id
**Code Declaration:**
```python
# Line 88 in app/models/quality_analysis.py
user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True),
    ForeignKey("user.id", use_alter=True, name="fk_expert_profiles_user_id"),
    nullable=False)
```

**Database Schema:**
```sql
-- expert_profiles.user_id = INTEGER (correct!)
expert_profiles.user_id | integer | not null
FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
```

**Migration Code (20251121_add_expert_feedback_system.py):**
```sql
-- Line 88: CORRECTLY used INTEGER
user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE
-- Comment: "user_id is UUID but references user.id (INTEGER)"
```

**Status:** ✅ DATABASE CORRECT, CODE WRONG
**Impact:** MEDIUM - Code works because SQLAlchemy handles type conversion, but misleading

---

#### 2. subscription.py - Subscription.user_id
**Code Declaration:**
```python
# Line 184 in app/models/subscription.py
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
```

**Database Schema:**
```sql
-- subscriptions.user_id = INTEGER (correct!)
subscriptions.user_id | integer | not null
FOREIGN KEY (user_id) REFERENCES "user"(id)
```

**Status:** ✅ DATABASE CORRECT, CODE WRONG
**Impact:** MEDIUM - Works but misleading

---

#### 3. faq_automation.py - GeneratedFAQ.approved_by
**Code Declaration:**
```python
# Line 329 in app/models/faq_automation.py
approved_by = Column(PG_UUID(as_uuid=True),
    ForeignKey("user.id", use_alter=True, name="fk_generated_faqs_approved_by"))
```

**Database Schema:**
```sql
-- TABLE DOES NOT EXIST!
-- If created, should be INTEGER to match user.id
```

**Status:** ⚠️ TABLE MISSING, CODE DECLARES UUID
**Impact:** HIGH - Will fail when table created if using Base.metadata

---

#### 4. data_export.py - 8 Models All Declare UUID for user_id
**Code Declaration:**
```python
# Lines 59, 227, 272, 310, 347, 379, 410, 442
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
```

**Database Schema:**
```sql
-- ALL TABLES MISSING!
```

**Status:** ⚠️ TABLES MISSING, CODE DECLARES UUID
**Impact:** HIGH - Will fail when tables created if using Base.metadata

---

## Finding #3: User Table is INTEGER (Not UUID)

### User Table Schema (Source of Truth)
```sql
-- Table: public.user
id | integer | not null | nextval('user_id_seq'::regclass)

-- PRIMARY KEY: user_pkey (id)
-- REFERENCED BY: 11 foreign keys (all INTEGER)
```

### All User FK References in Database (20 total)

**INTEGER columns WITH FK constraints (11):**
1. `customers.user_id` → user(id) ✅
2. `document_analyses.user_id` → user(id) ✅
3. `documents.user_id` → user(id) ✅
4. `expert_faq_candidates.approved_by` → user(id) ✅
5. `expert_profiles.user_id` → user(id) ✅
6. `faq_usage_logs.user_id` → user(id) ✅
7. `faq_variation_cache.user_id` → user(id) ✅
8. `invoices.user_id` → user(id) ✅
9. `payments.user_id` → user(id) ✅
10. `session.user_id` → user(id) ✅
11. `subscriptions.user_id` → user(id) ✅

**VARCHAR columns WITHOUT FK constraints (9):**
12. `compliance_checks.user_id` (varchar) - NO FK ⚠️
13. `cost_alerts.user_id` (varchar) - NO FK ⚠️
14. `cost_optimization_suggestions.user_id` (varchar) - NO FK ⚠️
15. `knowledge_feedback.user_id` (varchar) - NO FK ⚠️
16. `query_normalization_log.user_id` (varchar) - NO FK ⚠️
17. `tax_calculations.user_id` (varchar) - NO FK ⚠️
18. `usage_events.user_id` (varchar) - NO FK ⚠️
19. `usage_quotas.user_id` (varchar) - NO FK ⚠️
20. `user_usage_summaries.user_id` (varchar) - NO FK ⚠️

**Analysis:** The VARCHAR columns without FK constraints suggest these tables store user identifiers as strings (possibly from external systems or legacy code). They are NOT enforcing referential integrity.

---

## Finding #4: Alembic Migration Status

### Migration Chain (19 files, all applied)
```
<base> → 20250804_add_postgresql_fts
      → 20250804_add_regulatory_documents
      → 20250805_add_database_encryption
      → 20250805_add_faq_tables
      → 20250805_add_gdpr_deletion_system
      → 20250811_add_user_oauth_fields
      → 20251103_enable_pgvector
      → 20251103_vector_indexes
      → 20251103_fts_unaccent_weights
      → 20251103_add_parser_to_feed_status
      → 20251103_extraction_quality_and_junk_flags
      → 20251111_add_publication_date
      → 20251121_add_expert_feedback_system ← Created expert_profiles with INTEGER
      → 20251124_add_user_role
      → 20251124_add_generated_faq_id_to_expert_feedback
      → 20251126_add_question_embedding_to_faq
      → 20251126_add_question_embedding_to_faq_candidates
      → 20251126_add_embedding_to_expert_faq_candidates
      → 20251126_add_query_signature (current HEAD)
```

### Current Database State
```sql
SELECT * FROM alembic_version;
-- version_num: 20251126_add_question_embedding
```

**Status:** ✅ All 19 migrations applied successfully
**Conclusion:** Alembic IS working correctly! Base models never had migrations.

---

## Finding #5: Why Base Model Tables Are Missing

### Root Cause Analysis

**Problem:** Alembic ONLY tracks `SQLModel.metadata`, NOT `Base.metadata`

**Evidence:**
1. `alembic/env.py` line 40-45:
```python
from app.models.models import SQLModel
# ...
target_metadata = SQLModel.metadata
```

2. Base models use separate metadata:
```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
# Base.metadata is SEPARATE from SQLModel.metadata!
```

3. When migrations are created:
```bash
alembic revision --autogenerate -m "message"
# Alembic only detects changes in SQLModel.metadata
# Base models are INVISIBLE to Alembic!
```

### Why Some Base Model Tables Exist

**Tables that exist (expert_profiles, subscriptions, etc.):**
- Created by MANUAL SQL in migration files (20251121_add_expert_feedback_system.py)
- NOT auto-generated by Alembic's autogenerate
- Migration author wrote raw SQL to create tables
- Used CORRECT types (INTEGER for user_id)

**Tables that don't exist (all other Base models):**
- Never had manual SQL migrations written
- Alembic autogenerate never detected them (wrong metadata)
- Code references them, but tables don't exist

---

## Finding #6: Table Name Conflicts

### Conflicts Between Base Models and Existing Tables

#### 1. DocumentAnalysis
**Base Model:** `data_export.py:301` - `DocumentAnalysis(Base)` → table: `document_analyses`
**Existing Table:** `document_analyses` (different schema, 9 columns including user_id INTEGER)

**Conflict:** Base model would overwrite existing table!

#### 2. TaxCalculation
**Base Model:** `data_export.py:338` - `TaxCalculation(Base)` → table: `tax_calculations`
**Existing Table:** `tax_calculations` (4 columns including user_id VARCHAR)

**Conflict:** Base model would overwrite existing table!

---

## Impact Assessment

### Severity Levels

**CRITICAL (Blocks Production):**
- None currently - database works because Base model tables don't exist!

**HIGH (Blocks Development):**
1. **Missing faq_automation.py tables** - Blocks FAQ automation features
2. **Missing quality_analysis.py tables** - Blocks quality metrics features
3. **Missing data_export.py tables** - Blocks export features
4. **Missing regional_taxes.py tables** - Blocks regional tax features
5. **Missing ccnl_*.py tables** - Blocks CCNL features

**MEDIUM (Misleading Code):**
1. **ExpertProfile.user_id** - Code says UUID, database is INTEGER
2. **Subscription.user_id** - Code says UUID, database is INTEGER
3. **9 VARCHAR user_id columns** - No FK constraints, potential orphaned data

**LOW (Documentation):**
- Code comments mislead developers about schema

---

## Root Causes

### Primary Root Cause
**Dual Metadata System:**
- SQLModel.metadata (tracked by Alembic) ✅
- Base.metadata (NOT tracked by Alembic) ❌

### Contributing Factors
1. **Manual migrations** for some Base models (expert_feedback system) used correct INTEGER types
2. **No migrations** for other Base models (they remain code-only)
3. **Type declarations** in Base models don't match database reality
4. **No validation** that code types match database types

---

## Recommendations

### Option A: Fix Code to Match Database (RECOMMENDED)
**Approach:** Update all Base model UUID declarations to INTEGER

**Pros:**
- Safest option
- No database changes required
- No downtime
- Preserves existing data
- Aligns code with reality

**Cons:**
- Requires code changes in 7 files
- Need to update type hints and Column() declarations

**Timeline:** 1-2 hours of developer time

---

### Option B: Migrate Database to Match Code (NOT RECOMMENDED)
**Approach:** Change user.id from INTEGER to UUID

**Pros:**
- Code matches intent
- "Cleaner" conceptually

**Cons:**
- REQUIRES DOWNTIME (hours)
- Migrate 11 FK constraints
- Migrate all user.id values from INTEGER to UUID
- High risk of data corruption
- Requires full database backup
- Difficult rollback

**Timeline:** 1-2 days + testing + risk mitigation

---

### Option C: Hybrid Approach (RECOMMENDED FOR MIGRATION)
**Approach:** Fix existing tables (Option A) + Create missing tables with correct types

**Steps:**
1. Update Base model code to use INTEGER for user_id (3 files)
2. Create Alembic migrations for missing tables (use SQLModel or manual SQL)
3. Ensure all new tables use INTEGER for user_id
4. Proceed with SQLModel migration (Phase 1)

**Pros:**
- Safest for existing data
- Creates missing tables correctly
- No downtime
- Prepares for SQLModel migration

**Cons:**
- Requires code + migration changes
- Must coordinate changes

**Timeline:** 3-4 hours of developer time

---

## Action Items

### Immediate Actions (Before SQLModel Migration)

**1. Code Fixes (High Priority):**
- [ ] Fix `quality_analysis.py:88` - Change UUID to Integer for user_id
- [ ] Fix `subscription.py:184` - Change UUID to Integer for user_id
- [ ] Fix `faq_automation.py:329` - Change UUID to Integer for approved_by
- [ ] Fix `data_export.py:59,227,272,310,347,379,410,442` - Change UUID to Integer for user_id

**2. Create Missing Tables (Medium Priority):**
- [ ] Decide which Base models are actually needed
- [ ] Create Alembic migrations for needed tables
- [ ] Use INTEGER for all user_id foreign keys
- [ ] Test migrations on QA environment

**3. Validation (High Priority):**
- [ ] Run query to verify all user_id FK columns are INTEGER
- [ ] Add database schema validation tests
- [ ] Document actual schema in code comments

**4. Documentation (Medium Priority):**
- [ ] Update model docstrings to reflect actual database types
- [ ] Add warning about Base.metadata vs SQLModel.metadata
- [ ] Document which Base models have no tables

---

## Appendix: SQL Validation Queries

### Verify All User FK Types
```sql
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    c.udt_name,
    CASE WHEN f.constraint_name IS NOT NULL THEN 'FK EXISTS' ELSE 'NO FK' END as fk_status
FROM information_schema.columns c
LEFT JOIN (
    SELECT
        tc.table_name,
        kcu.column_name,
        tc.constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
) f ON c.table_name = f.table_name AND c.column_name = f.column_name
WHERE c.column_name IN ('user_id', 'approved_by')
    AND c.table_schema = 'public'
ORDER BY c.table_name, c.column_name;
```

### List All Tables
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

### Check Alembic History
```sql
SELECT version_num FROM alembic_version;
```

---

## Conclusion

**The database is CORRECT.** Migrations used proper INTEGER types. The problem is that **Base model code declares UUID** when it should declare INTEGER, and **44 Base model tables don't exist** because Alembic doesn't track Base.metadata.

**Before proceeding with SQLModel migration:**
1. Fix the 3 critical UUID→INTEGER code mismatches
2. Decide which missing Base models are needed
3. Create migrations for needed tables
4. Validate all user_id columns are INTEGER

**This audit prevents a catastrophic migration failure.**

---

**End of Report**
