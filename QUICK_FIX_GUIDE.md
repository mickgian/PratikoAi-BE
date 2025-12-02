# Quick Fix Guide - UUID to Integer

**URGENT:** Fix these 3 files BEFORE proceeding with SQLModel migration

**Estimated Time:** 30 minutes
**Risk Level:** LOW
**Downtime:** NONE

---

## Files to Fix

### 1. app/models/quality_analysis.py (Line 88)

**BEFORE:**
```python
user_id: Mapped[UUID] = mapped_column(
    PostgreSQLUUID(as_uuid=True),
    ForeignKey("user.id", use_alter=True, name="fk_expert_profiles_user_id"),
    nullable=False
)
```

**AFTER:**
```python
user_id: Mapped[int] = mapped_column(
    Integer,
    ForeignKey("user.id", name="fk_expert_profiles_user_id"),
    nullable=False
)
```

**Changes:**
1. `UUID` → `int`
2. `PostgreSQLUUID(as_uuid=True)` → `Integer`
3. Remove `use_alter=True` (not needed for Integer)

---

### 2. app/models/subscription.py (Line 184)

**BEFORE:**
```python
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
```

**AFTER:**
```python
user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
```

**Changes:**
1. `UUID(as_uuid=True)` → `Integer`

---

### 3. app/models/faq_automation.py (Line 329)

**BEFORE:**
```python
approved_by = Column(
    PG_UUID(as_uuid=True),
    ForeignKey("user.id", use_alter=True, name="fk_generated_faqs_approved_by")
)
```

**AFTER:**
```python
approved_by = Column(
    Integer,
    ForeignKey("user.id", name="fk_generated_faqs_approved_by")
)
```

**Changes:**
1. `PG_UUID(as_uuid=True)` → `Integer`
2. Remove `use_alter=True`

---

### 4. app/models/data_export.py (8 Locations)

**Lines:** 59, 227, 272, 310, 347, 379, 410, 442

**BEFORE:**
```python
user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
```

**AFTER:**
```python
user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
```

**Changes:**
1. `UUID(as_uuid=True)` → `Integer`

---

## Import Changes

### Remove These Imports (if no longer used):
```python
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
```

### Keep These Imports:
```python
from sqlalchemy import Integer, ForeignKey
```

---

## Testing Checklist

After making changes, run these tests:

### 1. Unit Tests
```bash
# Test quality_analysis models
pytest tests/models/test_quality_analysis.py -v

# Test subscription models
pytest tests/models/test_subscription.py -v

# Test all models (if exists)
pytest tests/models/ -v
```

### 2. API Endpoint Tests
```bash
# Test expert feedback endpoints
pytest tests/api/test_expert_feedback.py -v

# Test subscription endpoints (if exists)
pytest tests/api/test_subscription.py -v
```

### 3. Database Schema Validation
```bash
# Run validation script
PGPASSWORD=devpass psql -h localhost -U aifinance -d aifinance \
  -f scripts/validate_schema_alignment.sql
```

### 4. Alembic Check
```bash
# Should show NO pending changes
alembic revision --autogenerate -m "test" --dry-run
# Expected output: "No changes detected"
```

---

## Verification SQL Queries

### Check user.id type:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'user' AND column_name = 'id';
-- Expected: id | integer
```

### Check expert_profiles.user_id:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'expert_profiles' AND column_name = 'user_id';
-- Expected: user_id | integer
```

### Check FK constraint exists:
```sql
SELECT constraint_name, table_name, column_name
FROM information_schema.key_column_usage
WHERE table_name = 'expert_profiles' AND column_name = 'user_id';
-- Expected: fk_expert_profiles_user_id | expert_profiles | user_id
```

---

## Common Issues & Solutions

### Issue 1: Import Errors After Removing UUID
**Error:** `NameError: name 'UUID' is not defined`

**Solution:** Check if UUID is used elsewhere in the file (for id fields). Keep import if needed:
```python
from uuid import uuid4  # For default UUID primary keys
# But use Integer for user_id foreign keys!
```

---

### Issue 2: Type Checker Complains
**Error:** `Incompatible types in assignment (expression has type "int", variable has type "UUID")`

**Solution:** This is correct! The database IS integer. Update type hints:
```python
# OLD:
user_id: UUID
# NEW:
user_id: int
```

---

### Issue 3: Tests Fail With Type Mismatch
**Error:** `Expected UUID, got int`

**Solution:** Update test fixtures:
```python
# OLD:
expert_profile = ExpertProfile(user_id=UUID("..."))
# NEW:
expert_profile = ExpertProfile(user_id=1)  # Integer user ID
```

---

## Git Workflow

### 1. Create Branch
```bash
git checkout -b fix/schema-alignment-user-id-types
```

### 2. Make Changes
Edit the 4 files as documented above.

### 3. Run Tests
```bash
pytest tests/ -v
```

### 4. Check Alembic
```bash
# Should show no changes
alembic revision --autogenerate -m "verify_no_schema_changes" --sql > /tmp/check.sql
cat /tmp/check.sql
# Expected: Empty migration (no schema changes)
```

### 5. Commit
```bash
git add app/models/quality_analysis.py
git add app/models/subscription.py
git add app/models/faq_automation.py
git add app/models/data_export.py

git commit -m "fix: Change user_id declarations from UUID to Integer

- Fix ExpertProfile.user_id (quality_analysis.py:88)
- Fix Subscription.user_id (subscription.py:184)
- Fix GeneratedFAQ.approved_by (faq_automation.py:329)
- Fix 8 data_export.py models (lines 59,227,272,310,347,379,410,442)

Aligns code declarations with database reality (user.id is INTEGER).
Database schema unchanged - migrations already used correct types.

Blocks: SQLModel migration (prevents FK constraint failures)
Refs: SCHEMA_DRIFT_AUDIT.md, MIGRATION_STRATEGY.md Phase 1"
```

### 6. Push & Create PR
```bash
git push origin fix/schema-alignment-user-id-types

# Create PR with description:
# Title: "Fix user_id type declarations (UUID → Integer)"
# Body: See SCHEMA_DRIFT_AUDIT.md for context
```

---

## Why This Matters

**Database Reality:**
```sql
user.id = INTEGER (autoincrementing)
expert_profiles.user_id = INTEGER FK → user(id)
subscriptions.user_id = INTEGER FK → user(id)
```

**Code Declarations (WRONG):**
```python
user_id: Mapped[UUID]  # ❌ WRONG!
```

**Impact If Not Fixed:**
- SQLModel migration will try to create FK constraints: UUID → INTEGER
- PostgreSQL will reject: "foreign key constraint cannot be implemented"
- Migration fails catastrophically
- Hours of debugging and rollback

**Impact After Fix:**
- Code matches database ✅
- SQLModel migration succeeds ✅
- FK constraints work correctly ✅
- No schema drift ✅

---

## Rollback Plan

If something goes wrong:

```bash
# Rollback code changes
git checkout develop -- app/models/quality_analysis.py
git checkout develop -- app/models/subscription.py
git checkout develop -- app/models/faq_automation.py
git checkout develop -- app/models/data_export.py

# Or revert commit
git revert HEAD
```

**Note:** No database changes required for rollback (schema unchanged).

---

## Success Criteria

**Fix is successful when:**
- [ ] All 11 UUID→Integer changes committed
- [ ] All unit tests pass
- [ ] All API tests pass
- [ ] `alembic revision --autogenerate` shows no changes
- [ ] Schema validation script shows all INTEGER user_id columns
- [ ] PR approved and merged

---

## Estimated Timeline

- Code changes: 15 minutes
- Test execution: 10 minutes
- Validation: 5 minutes
- PR creation: 5 minutes
- **Total: ~35 minutes**

---

## Next Steps After This Fix

Once this PR is merged:

1. **Phase 2:** Review 36 missing Base model tables (see MIGRATION_STRATEGY.md)
2. **Phase 3:** Create migrations for needed tables (if any)
3. **Phase 4:** Begin SQLModel migration (file by file)
4. **Phase 5:** Final validation

**This fix unblocks the entire SQLModel migration!**

---

## Questions?

See detailed documentation:
- **SCHEMA_DRIFT_AUDIT.md** - Why this happened
- **FK_ANALYSIS.md** - User FK deep dive
- **MIGRATION_STRATEGY.md** - Full migration plan
- **ALEMBIC_AUDIT.md** - Migration history

Or contact:
- Database Designer (Primo) - Schema questions
- Architect - Design decisions
- Scrum Master - Timeline and priorities

---

**Let's fix this! 🚀**
