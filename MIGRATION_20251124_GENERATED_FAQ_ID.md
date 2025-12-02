# Migration: Add generated_faq_id to expert_feedback

**Migration ID:** `20251124_add_generated_faq_id`
**Created:** 2025-11-24
**Status:** Ready for deployment
**Database Designer:** PratikoAI Database Designer Subagent

---

## Overview

This migration adds the `generated_faq_id` field to the `expert_feedback` table to track which Golden Set (FAQ) entries were created from expert feedback marked as "Corretta" (correct).

## Business Context

When experts provide "Corretta" (correct) feedback, the system creates a new entry in the Golden Set (`faq_entries` table). This migration enables tracking of:

1. **Audit Trail**: Which expert validated this FAQ
2. **Quality Analysis**: Track feedback → FAQ conversion rate
3. **Duplicate Detection**: Prevent re-creating FAQs from the same feedback
4. **Expert Performance**: Measure how many FAQ entries each expert contributes

## Schema Changes

### Table: `expert_feedback`

#### New Column
```sql
generated_faq_id VARCHAR(100) NULL
```

**Properties:**
- Type: `VARCHAR(100)` (matches `faq_entries.id` type)
- Nullable: `TRUE` (most feedback won't generate FAQs)
- Default: `NULL`
- Index: `idx_expert_feedback_generated_faq_id` (B-tree)

#### Foreign Key Constraint
```sql
CONSTRAINT fk_expert_feedback_generated_faq_id
    FOREIGN KEY (generated_faq_id)
    REFERENCES faq_entries(id)
    ON DELETE SET NULL
```

**ON DELETE SET NULL Rationale:**
- If an FAQ entry is deleted, we keep the feedback record
- The feedback remains valuable for analysis even if FAQ is removed
- Prevents cascading deletes that could lose valuable feedback data

#### Index
```sql
CREATE INDEX idx_expert_feedback_generated_faq_id
    ON expert_feedback(generated_faq_id);
```

**Index Benefits:**
- Fast lookups: "Which feedback generated this FAQ?"
- Performance for JOIN queries between `expert_feedback` and `faq_entries`
- Efficient filtering: "Show all feedback that generated FAQs"

---

## Model Changes

### File: `app/models/quality_analysis.py`

```python
class ExpertFeedback(Base):
    # ... existing fields ...

    # Golden Set generation (DEV-BE-XX: Link feedback to generated FAQ entries)
    generated_faq_id: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey("faq_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
```

---

## Migration Files

### 1. Migration Script
**File:** `alembic/versions/20251124_add_generated_faq_id_to_expert_feedback.py`

**Upgrade:**
```python
def upgrade():
    # Add generated_faq_id column
    op.add_column('expert_feedback',
        sa.Column('generated_faq_id', sa.String(length=100), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_expert_feedback_generated_faq_id',
        'expert_feedback',
        'faq_entries',
        ['generated_faq_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index
    op.create_index(
        'idx_expert_feedback_generated_faq_id',
        'expert_feedback',
        ['generated_faq_id']
    )
```

**Downgrade:**
```python
def downgrade():
    # Drop index
    op.drop_index('idx_expert_feedback_generated_faq_id', 'expert_feedback')

    # Drop foreign key
    op.drop_constraint('fk_expert_feedback_generated_faq_id', 'expert_feedback', type_='foreignkey')

    # Drop column
    op.drop_column('expert_feedback', 'generated_faq_id')
```

---

## Migration Chain

```
20251121_expert_feedback
         ↓
20251124_add_user_role (Add RBAC roles)
         ↓
20251124_add_generated_faq_id (NEW: Add FAQ tracking) ← HEAD
```

---

## Testing

### 1. Validate Migration Structure
```bash
python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('migration', 'alembic/versions/20251124_add_generated_faq_id_to_expert_feedback.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(f'✓ Revision: {module.revision}')
print(f'✓ Down Revision: {module.down_revision}')
"
```

### 2. Check Migration History
```bash
alembic history | head -5
```

Expected output:
```
20251124_add_user_role -> 20251124_add_generated_faq_id (head), add generated_faq_id to expert_feedback
```

### 3. Apply Migration (QA Environment)
```bash
# Backup database first!
pg_dump -U aifinance -d aifinance > backup_before_generated_faq_id.sql

# Apply migration
alembic upgrade head

# Verify
psql -U aifinance -d aifinance -c "\d expert_feedback"
```

### 4. Verify Schema Changes
```bash
python test_migration_20251124_generated_faq_id.py
```

### 5. Test Rollback (QA Only)
```bash
# Rollback migration
alembic downgrade -1

# Verify column removed
psql -U aifinance -d aifinance -c "\d expert_feedback"

# Re-apply
alembic upgrade head
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] Migration reviewed by Backend Expert
- [ ] Migration reviewed by Architect
- [ ] QA database backup completed
- [ ] Migration tested on QA environment
- [ ] Rollback tested on QA environment
- [ ] Production database backup scheduled

### Deployment
- [ ] Production database backup completed
- [ ] Migration script validated (`alembic check`)
- [ ] Apply migration: `alembic upgrade head`
- [ ] Verify schema changes in production
- [ ] Monitor application logs for errors
- [ ] Test feedback → FAQ workflow

### Post-Deployment
- [ ] Verify new feedback records can be created
- [ ] Verify FAQ generation workflow works
- [ ] Monitor query performance (index usage)
- [ ] Update monitoring dashboards
- [ ] Document migration in CHANGELOG

---

## Performance Impact

### Expected Impact: **Minimal**

1. **Column Addition**: `VARCHAR(100) NULL`
   - Storage: ~100 bytes per row (when set)
   - Impact: Negligible (most rows will be NULL)

2. **Index Creation**: B-tree index on `generated_faq_id`
   - Size: ~16 bytes per row + overhead
   - Build time: <1 second (table has <10K rows currently)
   - Query impact: **Positive** (faster JOINs and lookups)

3. **Foreign Key Constraint**
   - INSERT impact: ~0.1ms (FK validation)
   - DELETE impact on `faq_entries`: SET NULL (fast operation)

### Monitoring Queries

```sql
-- Index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read
FROM pg_stat_user_indexes
WHERE indexname = 'idx_expert_feedback_generated_faq_id';

-- Foreign key validation performance
EXPLAIN ANALYZE
SELECT ef.*, fe.question
FROM expert_feedback ef
LEFT JOIN faq_entries fe ON ef.generated_faq_id = fe.id
WHERE ef.generated_faq_id IS NOT NULL;
```

---

## Rollback Plan

### If Migration Fails
```bash
# Automatic rollback by Alembic (transaction)
# No manual intervention needed
```

### If Issues Found Post-Deployment
```bash
# 1. Backup current state
pg_dump -U aifinance -d aifinance > backup_with_generated_faq_id.sql

# 2. Rollback migration
alembic downgrade -1

# 3. Verify rollback
psql -U aifinance -d aifinance -c "\d expert_feedback"

# 4. Restart application
systemctl restart pratiko-backend
```

---

## Usage Examples

### Set generated_faq_id When Creating FAQ
```python
from app.models.quality_analysis import ExpertFeedback
from app.models.faq import FAQEntry

# Expert provides "Corretta" feedback
feedback = ExpertFeedback(
    query_text="Come si calcola l'IVA per regime forfettario?",
    original_answer="L'IVA non si applica...",
    feedback_type=FeedbackType.CORRECT,
    expert_id=expert_id,
    # ... other fields ...
)

# Create FAQ from feedback
faq_entry = FAQEntry(
    question=feedback.query_text,
    answer=feedback.original_answer,
    category="regime_forfettario",
    # ... other fields ...
)
session.add(faq_entry)
session.flush()  # Get FAQ ID

# Link feedback to FAQ
feedback.generated_faq_id = faq_entry.id
session.add(feedback)
session.commit()
```

### Query Feedback That Generated FAQs
```python
# Get all feedback that generated FAQ entries
feedback_with_faqs = session.query(ExpertFeedback).filter(
    ExpertFeedback.generated_faq_id.isnot(None)
).all()

# Get FAQ entry from feedback
feedback = session.query(ExpertFeedback).first()
if feedback.generated_faq_id:
    faq = session.query(FAQEntry).filter(
        FAQEntry.id == feedback.generated_faq_id
    ).first()
```

### Analytics Query
```sql
-- FAQ generation rate by expert
SELECT
    ep.professional_registration_number,
    COUNT(*) as total_feedback,
    COUNT(ef.generated_faq_id) as faqs_generated,
    ROUND(COUNT(ef.generated_faq_id)::numeric / COUNT(*) * 100, 2) as faq_rate_pct
FROM expert_feedback ef
JOIN expert_profiles ep ON ef.expert_id = ep.id
WHERE ef.feedback_type = 'correct'
GROUP BY ep.id, ep.professional_registration_number
ORDER BY faqs_generated DESC;
```

---

## Related Tasks

- **DEV-BE-67**: Implement Golden Set (FAQ) management system
- **DEV-BE-68**: Expert feedback collection system (completed)
- **DEV-BE-XX**: Auto-generate FAQ entries from "Corretta" feedback (pending)

---

## References

- **Expert Feedback System**: `docs/QUALITY_ANALYSIS_SYSTEM.md`
- **FAQ System**: `docs/INTELLIGENT_FAQ_SYSTEM.md`
- **Database Architecture**: `docs/DATABASE_ARCHITECTURE.md`
- **Model Definition**: `app/models/quality_analysis.py`
- **FAQ Model**: `app/models/faq.py`

---

## Sign-off

**Database Designer:** PratikoAI Database Designer Subagent
**Date:** 2025-11-24
**Status:** ✅ Ready for Review

**Reviewed By:**
- [ ] Backend Expert (@Backend)
- [ ] Architect (@Architect)
- [ ] Scrum Master (@Scrum)

---

## Notes

1. **Type Compatibility**: Used `VARCHAR(100)` to match `faq_entries.id` type (not UUID)
2. **Nullable**: Column is nullable because most feedback won't generate FAQs
3. **ON DELETE SET NULL**: Preserves feedback even if FAQ is deleted
4. **Index**: B-tree index for fast lookups and JOINs
5. **No Breaking Changes**: Existing application code unaffected
