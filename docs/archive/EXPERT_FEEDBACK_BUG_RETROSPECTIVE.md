# Expert Feedback System Bug Retrospective (DEV-BE-72)

**Date:** 2025-11-25
**Session:** Manual testing of Expert Feedback System
**Branch:** DEV-BE-72-expert-feedback-database-schema

## Executive Summary

Three critical bugs were discovered during manual testing that blocked the Expert Feedback System from functioning:

1. **Missing Context File** - ExpertStatusContext.tsx was never created
2. **Schema Mismatch** - Frontend validation checked wrong fields (message_id/session_id vs query_id)
3. **FK Constraint Error** - Foreign key referenced non-existent faq_entries table

All three bugs were fixed within the session, enabling end-to-end testing.

---

## Bug 1: Missing ExpertStatusContext.tsx

### Symptoms
```
Module not found: Can't resolve '@/contexts/ExpertStatusContext'
at src/app/chat/components/AIMessageV2.tsx
```

### Root Cause
The Context file was **never created** during implementation. AIMessageV2.tsx was importing it, but the file didn't exist in the working directory at all.

### Agent/Process Failure
- **Agent responsible:** livia (Frontend Expert)
- **What was missed:** When optimizing from hook to Context pattern, the Context file implementation was never completed
- **Why it happened:** Partial implementation - the import was updated but the Context Provider was never created
- **Task tracking:** Not explicitly tracked in todo list

### Fix Applied
Created `/Users/micky/WebstormProjects/PratikoAiWebApp/src/contexts/ExpertStatusContext.tsx`:
- React Context Provider for expert status
- Single API call cached for entire page
- Graceful degradation for non-experts
- Wrapped chat page with ExpertStatusProvider

**Files Modified:**
- `src/contexts/ExpertStatusContext.tsx` (created, 121 lines)
- `src/app/chat/page.tsx` (added provider wrapper)

---

## Bug 2: Frontend Validation Schema Mismatch

### Symptoms
```
Campi obbligatori mancanti (Required fields missing)
When clicking "Incompleta" and filling "Dettagli aggiuntivi"
```

### Root Cause
**Complete schema mismatch** between validation layer and implementation:

- **Validation checked:** `message_id`, `session_id` (old schema from early design)
- **Component sent:** `query_id`, `query_text`, `original_answer`, etc. (correct backend schema)
- **Backend expected:** `query_id` + required fields (no session_id)

The validation layer was checking for fields that no longer existed in the schema, causing false failures.

### Agent/Process Failure
- **Agent responsible:** livia (Frontend Expert)
- **What was missed:** Frontend validation was never updated when backend schema was finalized
- **Why it happened:**
  - TypeScript interfaces not aligned with Pydantic schemas
  - No contract validation test between frontend/backend
  - Schema evolved but validation didn't track changes
- **Task tracking:** Schema alignment was not in todo list

### Fix Applied
1. Updated `src/types/expertFeedback.ts`:
   - Replaced `message_id` with `query_id`
   - Removed `session_id` field
   - Added all required backend fields
   - Created `FeedbackTypeAPI` for English values

2. Updated `src/lib/api/expertFeedback.ts` validation:
   - Check `query_id`, `query_text`, `original_answer`
   - Validate `confidence_score` (0.0-1.0 range)
   - Validate `time_spent_seconds` (> 0)
   - Updated `additional_details` check for English feedback types

**Files Modified:**
- `src/types/expertFeedback.ts` (schema alignment)
- `src/lib/api/expertFeedback.ts` (validation rewrite, lines 88-113)

---

## Bug 3: Foreign Key Constraint Error

### Symptoms
```
Foreign key associated with column 'expert_feedback.generated_faq_id'
could not find table 'faq_entries' with which to generate a foreign key
to target column 'id'
```

### Root Cause
SQLAlchemy model defined FK constraint to non-existent table:

```python
generated_faq_id: Mapped[str | None] = mapped_column(
    String(100), ForeignKey("faq_entries.id", ondelete="SET NULL"), ...
)
```

The `faq_entries` table was never created because:
- FAQ tables migration exists (`20250805_add_faq_tables.py`) but was never run
- Golden Set integration not implemented yet
- Expert Feedback was built with forward reference to future feature

### Agent/Process Failure
- **Agent responsible:** ezio (Backend Expert)
- **What was missed:** FK constraint added for table that doesn't exist yet
- **Why it happened:**
  - Forward integration planning (referencing future Golden Set feature)
  - Migration dependency not validated
  - Database state not checked before adding FK
  - No database constraint validation in tests
- **Task tracking:** Golden Set integration tracked separately, dependency not explicit

### Fix Applied
Removed FK constraint temporarily from `app/models/quality_analysis.py`:

```python
# Golden Set generation (DEV-BE-XX: Link feedback to generated FAQ entries)
# Note: FK constraint temporarily removed - faq_entries table not created yet
generated_faq_id: Mapped[str | None] = mapped_column(
    String(100), nullable=True, index=True,
    comment="FK to faq_entries.id (table not created yet)"
)
```

**Trade-offs:**
- ✅ Expert feedback works immediately
- ✅ Column exists for future use
- ⚠️ Temporarily loses referential integrity
- ⚠️ Can store invalid FAQ IDs (acceptable since Golden Set not implemented)

**Future work:**
- Run FAQ migrations when implementing Golden Set
- Restore FK constraint after table creation

**Files Modified:**
- `app/models/quality_analysis.py` (lines 172-176)

---

## Process Improvements

### 1. Frontend-Backend Contract Testing
**Problem:** Schema mismatch not caught until manual testing

**Prevention:**
- Add contract tests validating TypeScript interfaces match Pydantic schemas
- Use schema generation tools (e.g., openapi-typescript)
- Add pre-commit hook checking API contract alignment

**Responsible agents:** livia (frontend) + ezio (backend) + clelia (testing)

### 2. Database Dependency Validation
**Problem:** FK constraint added before table exists

**Prevention:**
- Add database state validation before FK constraint definition
- Document migration dependencies explicitly
- Add test checking all FKs reference existing tables
- Use SQLAlchemy reflection to validate schema before startup

**Responsible agents:** primo (database) + ezio (backend)

### 3. Implementation Completeness Checks
**Problem:** Context file never created despite being referenced

**Prevention:**
- Add "implementation audit" step before marking tasks complete
- Check all imports resolve before committing
- Add build/compile step to CI that catches missing modules
- Require agent to confirm all new imports have corresponding implementations

**Responsible agents:** livia (frontend) + tiziano (debugging)

### 4. Feature Dependency Mapping
**Problem:** Expert Feedback referenced Golden Set before it existed

**Prevention:**
- Document feature dependencies in ARCHITECTURE_ROADMAP.md
- Make forward references explicit and optional
- Use nullable FKs without constraints for future features
- Add "dependency readiness" check before integration

**Responsible agents:** egidio (architecture) + ezio (backend)

---

## Testing Gaps Identified

### Unit Tests Missing
- Frontend validation logic (expertFeedback.ts)
- TypeScript interface compatibility with backend schemas
- ExpertStatusContext provider logic

### Integration Tests Missing
- Frontend → Backend API contract validation
- Complete feedback submission flow (UI → API → Database)
- Expert status check with role-based authorization

### Database Tests Missing
- Foreign key constraint validation
- Migration dependency verification
- Schema integrity checks

### E2E Tests Missing
- Full feedback submission workflow
- Expert UI visibility based on role
- Error handling for each bug scenario

**Responsible agent for test generation:** clelia

---

## User Feedback Incorporated

**Critical user feedback during session:**
> "The fact that a file is not committed does not mean the implementation does not work for that reason."

**Learning:** Initial retrospective incorrectly blamed git workflow. The root cause was incomplete implementation (file never created), not lack of commits.

**Process adjustment:** Focus on implementation completeness, not commit discipline, when diagnosing bugs.

---

## Accountability Matrix

| Bug | Agent Responsible | Missed Step | Prevention |
|-----|------------------|-------------|------------|
| Missing Context File | livia (Frontend) | File creation | Implementation audit, import validation |
| Schema Mismatch | livia (Frontend) | Schema alignment | Contract tests, schema generation |
| FK Constraint Error | ezio (Backend) | Table existence check | DB validation, dependency mapping |

---

## Success Criteria Met

✅ All three bugs fixed
✅ Frontend loads successfully
✅ Validation passes with correct data
✅ Database operations complete without FK errors
✅ System ready for end-to-end manual testing

---

## Conclusion

The bugs discovered during manual testing revealed **gaps in cross-layer validation**:
- Frontend and backend schemas were not validated against each other
- Database constraints referenced non-existent tables
- Implementation was partially complete (imports without files)

All bugs were resolved with minimal code changes. The system is now functional for manual testing.

**Recommended next steps:**
1. Run full manual test suite with super_user account
2. Implement contract tests (livia + ezio + clelia)
3. Add database constraint validation (primo + ezio)
4. Document feature dependencies explicitly (egidio)
5. Run FAQ migrations when Golden Set feature is prioritized
