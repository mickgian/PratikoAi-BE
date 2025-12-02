# User Foreign Key Reference Analysis

**Date:** 2025-11-28
**Auditor:** Database Designer (Primo)
**Purpose:** Comprehensive analysis of all user.id foreign key references

---

## Executive Summary

**Total User FK References:** 20 columns across 20 tables
- **11 columns** with proper FK constraints (INTEGER) ✅
- **9 columns** without FK constraints (VARCHAR) ⚠️

**User Table (Source of Truth):**
- `user.id` = **INTEGER** (autoincrementing serial)
- `user_id_seq` sequence generates INTEGER IDs

---

## Category 1: Proper FK References (11 Tables)

### All Use INTEGER and Have FK Constraints ✅

#### 1. customers.user_id
```sql
Column: user_id | integer | not null
Constraint: customers_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
Status: ✅ CORRECT
```

#### 2. document_analyses.user_id
```sql
Column: user_id | integer | not null
Constraint: document_analyses_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
Status: ✅ CORRECT
Note: Table exists but different from data_export.py:301 Base model
```

#### 3. documents.user_id
```sql
Column: user_id | integer | not null
Constraint: documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
Status: ✅ CORRECT
```

#### 4. expert_faq_candidates.approved_by
```sql
Column: approved_by | integer | nullable
Constraint: expert_faq_candidates_approved_by_fkey FOREIGN KEY (approved_by)
           REFERENCES "user"(id) ON DELETE SET NULL
Status: ✅ CORRECT
Note: Code declares UUID (quality_analysis.py:258) but migration used INTEGER
```

#### 5. expert_profiles.user_id
```sql
Column: user_id | integer | not null | UNIQUE
Constraint: expert_profiles_user_id_fkey FOREIGN KEY (user_id)
           REFERENCES "user"(id) ON DELETE CASCADE
Status: ✅ CORRECT
Note: Code declares UUID (quality_analysis.py:88) but migration used INTEGER
Migration comment: "user_id is UUID but references user.id (INTEGER)"
```

#### 6. faq_usage_logs.user_id
```sql
Column: user_id | integer | nullable
Constraint: faq_usage_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
Status: ✅ CORRECT
```

#### 7. faq_variation_cache.user_id
```sql
Column: user_id | integer | nullable
Constraint: faq_variation_cache_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
Status: ✅ CORRECT
```

#### 8. invoices.user_id
```sql
Column: user_id | integer | not null
Constraint: invoices_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
Status: ✅ CORRECT
```

#### 9. payments.user_id
```sql
Column: user_id | integer | not null
Constraint: payments_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
Status: ✅ CORRECT
```

#### 10. session.user_id
```sql
Column: user_id | integer | not null
Constraint: session_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
Status: ✅ CORRECT
```

#### 11. subscriptions.user_id
```sql
Column: user_id | integer | not null
Constraint: subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id)
Status: ✅ CORRECT
Note: Code declares UUID (subscription.py:184) but migration used INTEGER
```

---

## Category 2: VARCHAR Without FK Constraints (9 Tables)

### All Use VARCHAR and Have NO FK Constraints ⚠️

#### 12. compliance_checks.user_id
```sql
Column: user_id | character varying
Constraint: NONE
Status: ⚠️ NO FK CONSTRAINT
Risk: Orphaned records possible, no referential integrity
Source: Unknown (likely legacy or external system integration)
```

#### 13. cost_alerts.user_id
```sql
Column: user_id | character varying
Constraint: NONE
Status: ⚠️ NO FK CONSTRAINT
Risk: Orphaned records possible
Source: Cost management system
```

#### 14. cost_optimization_suggestions.user_id
```sql
Column: user_id | character varying
Constraint: NONE
Status: ⚠️ NO FK CONSTRAINT
Risk: Orphaned records possible
Source: Cost management system
```

#### 15. knowledge_feedback.user_id
```sql
Column: user_id | character varying
Constraint: NONE
Status: ⚠️ NO FK CONSTRAINT
Risk: Orphaned records possible
Source: Knowledge base feedback system
```

#### 16. query_normalization_log.user_id
```sql
Column: user_id | character varying
Constraint: NONE
Status: ⚠️ NO FK CONSTRAINT
Risk: Orphaned records possible
Source: Query normalization system
```

#### 17. tax_calculations.user_id
```sql
Column: user_id | character varying (4 columns total)
Constraint: NONE
Status: ⚠️ NO FK CONSTRAINT
Risk: Orphaned records possible
Note: CONFLICTS with data_export.py:338 Base model (if it were created)
```

#### 18. usage_events.user_id
```sql
Column: user_id | character varying
Constraint: NONE
Status: ⚠️ NO FK CONSTRAINT
Risk: Orphaned records possible
Source: Usage tracking system
```

#### 19. usage_quotas.user_id
```sql
Column: user_id | character varying
Constraint: NONE
Status: ⚠️ NO FK CONSTRAINT
Risk: Orphaned records possible
Source: Usage quota management
```

#### 20. user_usage_summaries.user_id
```sql
Column: user_id | character varying
Constraint: NONE
Status: ⚠️ NO FK CONSTRAINT
Risk: Orphaned records possible
Source: Usage summary reports
```

---

## Code vs Database Comparison

### Critical Mismatches (Code Declares UUID, Database Uses INTEGER)

#### 1. ExpertProfile.user_id
**File:** `app/models/quality_analysis.py:88`
```python
user_id: Mapped[UUID] = mapped_column(
    PostgreSQLUUID(as_uuid=True),
    ForeignKey("user.id", use_alter=True, name="fk_expert_profiles_user_id"),
    nullable=False
)
```

**Database:**
```sql
expert_profiles.user_id | integer | not null | UNIQUE
FK: expert_profiles_user_id_fkey → user(id)
```

**Status:** CODE WRONG, DATABASE CORRECT
**Action:** Change code to use Integer instead of UUID

---

#### 2. Subscription.user_id
**File:** `app/models/subscription.py:184`
```python
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
```

**Database:**
```sql
subscriptions.user_id | integer | not null
FK: subscriptions_user_id_fkey → user(id)
```

**Status:** CODE WRONG, DATABASE CORRECT
**Action:** Change code to use Integer instead of UUID

---

#### 3. ExpertFAQCandidate.approved_by
**File:** `app/models/quality_analysis.py:258` (NOT SHOWN IN GREP, CHECK MODEL)
**Database:**
```sql
expert_faq_candidates.approved_by | integer | nullable
FK: expert_faq_candidates_approved_by_fkey → user(id) ON DELETE SET NULL
```

**Status:** DATABASE CORRECT
**Action:** Verify code matches (likely correct already)

---

### Models Declaring UUID for Missing Tables

#### 4. GeneratedFAQ.approved_by
**File:** `app/models/faq_automation.py:329`
```python
approved_by = Column(
    PG_UUID(as_uuid=True),
    ForeignKey("user.id", use_alter=True, name="fk_generated_faqs_approved_by")
)
```

**Database:** TABLE DOES NOT EXIST
**Status:** CODE WRONG (should be Integer)
**Action:** Change to Integer before creating table

---

#### 5-12. data_export.py Models (8 models)
**Files:** `app/models/data_export.py` lines 59, 227, 272, 310, 347, 379, 410, 442

**All declare:**
```python
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
```

**Database:** ALL TABLES MISSING
**Status:** CODE WRONG (should be Integer)
**Action:** Change to Integer before creating tables

**Models:**
- DataExportRequest (line 59)
- ExportAuditLog (line 227)
- QueryHistory (line 272)
- DocumentAnalysis (line 310) - CONFLICTS with existing table!
- TaxCalculation (line 347) - CONFLICTS with existing table!
- FAQInteraction (line 379)
- KnowledgeBaseSearch (line 410)
- ElectronicInvoice (line 442)

---

## Migration Analysis

### How Migrations Got It Right

**Example: 20251121_add_expert_feedback_system.py**

**Code declares UUID:**
```python
# quality_analysis.py:88
user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ...)
```

**Migration uses INTEGER:**
```sql
-- Line 88 of migration
user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE

-- Comment line 83:
-- NOTE: user_id is UUID but references user.id (INTEGER)
-- This is intentional for future-proofing when user table migrates to UUID
```

**Result:** Migration author MANUALLY overrode the model declaration!

**Conclusion:** Manual SQL in migrations saved us from UUID/INTEGER FK mismatch errors.

---

## Referential Integrity Risks

### High Risk: VARCHAR Columns Without FKs

**9 tables** with `user_id VARCHAR` and no FK constraints:

**Risks:**
1. **Orphaned Records:** User deleted but records remain
2. **Invalid References:** user_id values that don't exist in user table
3. **Data Type Mismatch:** Storing non-numeric IDs (strings, UUIDs, etc.)
4. **No Cascade Deletes:** Manual cleanup required when users deleted
5. **Query Performance:** Cannot use indexes effectively

**Mitigation Needed:**
```sql
-- Option 1: Convert VARCHAR to INTEGER and add FK (RECOMMENDED)
ALTER TABLE compliance_checks
    ALTER COLUMN user_id TYPE INTEGER USING user_id::INTEGER,
    ADD CONSTRAINT compliance_checks_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES "user"(id);

-- Option 2: Document why FK is not needed (if intentional)
-- Add comment explaining VARCHAR usage
```

---

## Recommendations

### Immediate Actions (Before SQLModel Migration)

#### 1. Fix Code Type Mismatches (HIGH PRIORITY)
**Files to Change:**
- `app/models/quality_analysis.py:88` - ExpertProfile.user_id: UUID → Integer
- `app/models/subscription.py:184` - Subscription.user_id: UUID → Integer
- `app/models/faq_automation.py:329` - GeneratedFAQ.approved_by: UUID → Integer
- `app/models/data_export.py:59,227,272,310,347,379,410,442` - All user_id: UUID → Integer

**Code Change Pattern:**
```python
# BEFORE (WRONG):
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)

# AFTER (CORRECT):
user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

# Or with Mapped (for SQLAlchemy 2.0):
user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
```

---

#### 2. Audit VARCHAR user_id Columns (MEDIUM PRIORITY)

**For each of the 9 VARCHAR columns, determine:**

**Questions:**
1. Why is it VARCHAR instead of INTEGER?
2. Does it store actual user.id values (as strings)?
3. Does it store external system IDs?
4. Should it have a FK constraint?
5. Are there orphaned records?

**SQL to Check:**
```sql
-- Check for orphaned records
SELECT DISTINCT user_id
FROM compliance_checks
WHERE user_id NOT IN (SELECT id::VARCHAR FROM "user");

-- Check data type patterns
SELECT user_id, COUNT(*)
FROM compliance_checks
GROUP BY user_id
ORDER BY COUNT(*) DESC
LIMIT 10;

-- Check if all values are numeric
SELECT COUNT(*) as total,
       COUNT(CASE WHEN user_id ~ '^[0-9]+$' THEN 1 END) as numeric,
       COUNT(CASE WHEN user_id !~ '^[0-9]+$' THEN 1 END) as non_numeric
FROM compliance_checks;
```

---

#### 3. Add Missing FK Constraints (MEDIUM PRIORITY)

**If VARCHAR columns store user.id values:**

**Migration Pattern:**
```python
def upgrade():
    # Step 1: Clean orphaned records
    op.execute("""
        DELETE FROM compliance_checks
        WHERE user_id::INTEGER NOT IN (SELECT id FROM "user");
    """)

    # Step 2: Convert to INTEGER
    op.execute("""
        ALTER TABLE compliance_checks
        ALTER COLUMN user_id TYPE INTEGER USING user_id::INTEGER;
    """)

    # Step 3: Add FK constraint
    op.create_foreign_key(
        'compliance_checks_user_id_fkey',
        'compliance_checks',
        'user',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade():
    op.drop_constraint('compliance_checks_user_id_fkey', 'compliance_checks')
    op.execute("ALTER TABLE compliance_checks ALTER COLUMN user_id TYPE VARCHAR;")
```

---

#### 4. Validate All FK References (HIGH PRIORITY)

**SQL Validation:**
```sql
-- Count orphaned records across all tables
SELECT 'customers' as table_name, COUNT(*) as orphaned
FROM customers WHERE user_id NOT IN (SELECT id FROM "user")
UNION ALL
SELECT 'document_analyses', COUNT(*)
FROM document_analyses WHERE user_id NOT IN (SELECT id FROM "user")
UNION ALL
SELECT 'expert_profiles', COUNT(*)
FROM expert_profiles WHERE user_id NOT IN (SELECT id FROM "user")
-- ... repeat for all FK tables
;

-- Expected result: 0 orphaned records (FKs prevent them)
```

---

## SQLModel Migration Blockers

### Must Fix Before Migration

**Critical Blockers:**
1. ✅ **user.id is INTEGER** - Confirmed, no change needed
2. ❌ **Code declares UUID** - MUST fix 3 files (quality_analysis.py, subscription.py, faq_automation.py)
3. ❌ **data_export.py models** - MUST fix 8 UUID declarations before creating tables

**Migration Strategy:**
```python
# Phase 1: Fix code type mismatches
# 1. Change UUID → Integer in 3 existing model files
# 2. Test existing tables still work
# 3. Commit code changes

# Phase 2: Create missing tables (if needed)
# 1. Decide which data_export.py models to keep
# 2. Create Alembic migrations with INTEGER user_id
# 3. Test FK constraints work

# Phase 3: Proceed with SQLModel migration
# 1. Convert models from Base → SQLModel
# 2. Use Integer for all user_id references
# 3. Maintain FK constraints
```

---

## Appendix: SQL Queries for Validation

### 1. List All User FK Columns
```sql
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    c.udt_name,
    c.is_nullable,
    CASE
        WHEN fk.constraint_name IS NOT NULL THEN 'FK: ' || fk.constraint_name
        ELSE 'NO FK'
    END as fk_constraint
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
) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
WHERE c.column_name IN ('user_id', 'approved_by')
    AND c.table_schema = 'public'
ORDER BY
    CASE WHEN c.data_type = 'integer' THEN 1 ELSE 2 END,
    c.table_name;
```

### 2. Check for Orphaned Records (VARCHAR Tables)
```sql
-- Compliance checks
SELECT 'compliance_checks' as table_name,
       COUNT(*) as total_records,
       COUNT(CASE WHEN user_id::INTEGER NOT IN (SELECT id FROM "user") THEN 1 END) as orphaned
FROM compliance_checks
WHERE user_id ~ '^[0-9]+$';  -- Only check numeric values

-- Repeat for each VARCHAR table
```

### 3. Verify FK Constraint Details
```sql
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    tc.constraint_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND ccu.table_name = 'user'
ORDER BY tc.table_name;
```

---

## Conclusion

**Summary:**
- **11 tables** have proper INTEGER FK constraints ✅
- **9 tables** use VARCHAR without FKs ⚠️
- **3 code files** incorrectly declare UUID (must fix before migration)
- **8 data_export.py models** incorrectly declare UUID (must fix before creating tables)

**Critical Path:**
1. Fix the 3 UUID code mismatches (quality_analysis.py, subscription.py, faq_automation.py)
2. Decide on VARCHAR user_id columns (convert to INTEGER or document rationale)
3. Fix data_export.py UUID declarations before creating tables
4. Validate all FK references are working
5. Proceed with SQLModel migration using INTEGER for user_id

**This analysis ensures referential integrity during the migration.**

---

**End of Report**
