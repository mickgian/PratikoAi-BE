# Golden Set Workflow Integration (S119-S130)

## Overview

This document describes the implementation of the workflow integration that connects expert feedback submission (S119) to the Golden Set candidate proposal and publishing pipeline (S127-S130).

## Architecture Reference

See: `pratikoai_rag_hybrid.mmd` - Steps S113-S130

## Implementation Summary

### Goal
When a SUPER_USER expert provides "Corretta" (CORRECT) feedback on an AI-generated answer, automatically trigger the Golden Set workflow to:
1. Propose the Q&A pair as an FAQ candidate
2. Check if it meets auto-approval threshold (based on expert trust score)
3. Publish to Golden Set if approved
4. Invalidate related caches

### Components Modified

#### 1. API Endpoint (`app/api/v1/expert_feedback.py`)

**Changes:**
- Added `_trigger_golden_set_workflow()` async helper function (lines 40-154)
- Modified `submit_expert_feedback()` to trigger workflow for CORRECT feedback (lines 137-153)
- Updated response to include `generated_faq_id` field (line 152)

**Workflow Trigger Logic:**
```python
if submission.feedback_type == "correct":
    feedback.task_creation_attempted = True
    asyncio.create_task(_trigger_golden_set_workflow(feedback, expert, db))
```

**Background Task Pattern:**
- Uses `asyncio.create_task()` for fire-and-forget execution
- Does not block API response (sub-30 second requirement maintained)
- Updates `feedback.generated_faq_id` upon successful FAQ creation
- Sets `feedback.task_creation_success` based on outcome

#### 2. Service Layer (`app/services/expert_feedback_collector.py`)

**Changes:**
- Added `_trigger_golden_candidate_workflow()` method (lines 284-396)
- Modified `_create_feedback_record()` to trigger workflow (lines 249-276)

**Note:** This implementation mirrors the API endpoint approach for consistency. The service layer method can be used when creating feedback records programmatically.

#### 3. Pydantic Schemas (`app/schemas/expert_feedback.py`)

**Changes:**
- Added `generated_faq_id: str | None` to `FeedbackResult` (line 92-94)
- Added `generated_faq_id: str | None` to `FeedbackRecord` (line 126)
- Added `generated_faq_id: str | None` to `FeedbackDetailResponse` (line 186)
- Updated example JSON in `FeedbackResult` to show CORRECT feedback case

#### 4. Test Suite (`tests/api/test_expert_feedback.py`)

**Changes:**
- Updated `sample_feedback` fixture to include `generated_faq_id = None` (line 128)
- Updated all mock feedback objects to include `generated_faq_id` field (lines 190, 250, 444)
- Changed `task_creation_attempted` to `True` for CORRECT feedback test (line 248)

**Test Results:**
- All 16 tests passing
- No coverage regression

## Workflow Execution Steps

### S127: Golden Candidate Proposal
**Function:** `step_127__golden_candidate(ctx=ctx)`

**Input Context:**
```python
ctx = {
    "request_id": f"feedback_{feedback.id}",
    "expert_feedback": {
        "id": str(feedback.id),
        "query_text": feedback.query_text,
        "expert_answer": feedback.expert_answer or feedback.original_answer,
        "category": feedback.category.value if feedback.category else "generale",
        "regulatory_references": feedback.regulatory_references,
        "confidence_score": feedback.confidence_score,
        "frequency": 1,
    },
    "expert_id": str(expert.id),
    "trust_score": expert.trust_score,
}
```

**Output:**
```python
{
    "faq_candidate": {
        "question": query_text,
        "answer": expert_answer,
        "category": category,
        "regulatory_references": refs,
        "priority_score": float,
        "quality_score": float,
        "source": "expert_feedback",
        ...
    },
    "candidate_metadata": {...}
}
```

### S128: Golden Approval Decision
**Function:** `step_128__golden_approval(ctx=result_127)`

**Decision Logic:**
- Check expert `trust_score` against threshold
- Check `quality_score` against threshold
- Return approval decision with status

**Approval Statuses:**
- `auto_approved` - Expert trust score meets threshold, publish immediately
- `manual_approved` - Manually approved by admin
- `needs_review` - Below threshold, queue for manual review
- `rejected` - Quality too low, do not publish

**Thresholds (from orchestrator):**
- Auto-approval requires `trust_score >= 0.8` and `quality_score >= 0.7`

### S129: Publish to Golden Set
**Function:** `step_129__publish_golden(ctx=result_128)`

**Actions:**
1. Create or update FAQ entry in `faq_entries` table
2. Generate vector embedding via pgvector trigger
3. Version the entry (maintain history)
4. Return `published_faq_id`

**Output:**
```python
{
    "published_faq_id": str,  # e.g., "faq_123e4567-e89b-12d3-a456-426614174000"
    "version": int,
    "update_type": "create" | "update",
    ...
}
```

### S130: Cache Invalidation
**Function:** Handled automatically in `step_129__publish_golden()`

**Caches Invalidated:**
- FAQ lookup cache
- Vector search cache
- Golden Set metadata cache

## Database Schema

### ExpertFeedback Model (Already Exists)
```python
generated_faq_id: Mapped[str | None] = mapped_column(
    String(100),
    ForeignKey("faq_entries.id", ondelete="SET NULL"),
    nullable=True,
    index=True
)
```

**Foreign Key Constraint:**
- References: `faq_entries.id`
- On Delete: `SET NULL` (preserve feedback record if FAQ deleted)
- Indexed: Yes (for fast lookups)

## Error Handling

### Design Principle
**Feedback submission NEVER fails due to Golden Set workflow errors.**

### Error Cases Handled

1. **Import Error (Golden Set orchestrator not available):**
   ```python
   except ImportError as e:
       logger.error(f"Failed to import Golden Set orchestrator steps: {e}")
       feedback.task_creation_success = False
       feedback.task_creation_error = f"Import error: {str(e)}"
       # Continue - feedback is stored
   ```

2. **Workflow Execution Error:**
   ```python
   except Exception as e:
       logger.error(f"Failed to process Golden Set workflow: {e}", exc_info=True)
       feedback.task_creation_success = False
       feedback.task_creation_error = str(e)
       # Continue - feedback is stored
   ```

3. **No Candidate Proposed (S127):**
   - Log info message
   - Set `task_creation_success = False`
   - Return early, do not proceed to S128

4. **Candidate Not Approved (S128):**
   - Log info message with reason
   - Set `task_creation_success = False`
   - Return early, do not proceed to S129

### Logging Strategy

**Structured Logging:**
```python
logger.info(
    "S127: Proposing Golden Set candidate from feedback {feedback_id}",
    extra={
        "feedback_id": str(feedback.id),
        "expert_id": str(expert.id),
        "trust_score": expert.trust_score,
    }
)
```

**Step Markers:**
- `S127:` - Golden Candidate proposal
- `S128:` - Approval decision
- `S129:` - Publishing
- `S130:` - Cache invalidation

## API Response Format

### Success Response (CORRECT feedback with FAQ created)
```json
{
    "feedback_id": "123e4567-e89b-12d3-a456-426614174000",
    "feedback_type": "correct",
    "expert_trust_score": 0.92,
    "task_creation_attempted": true,
    "generated_task_id": null,
    "generated_faq_id": "faq_123e4567-e89b-12d3-a456-426614174000",
    "message": "Feedback submitted successfully"
}
```

### Success Response (CORRECT feedback, FAQ not created)
```json
{
    "feedback_id": "123e4567-e89b-12d3-a456-426614174000",
    "feedback_type": "correct",
    "expert_trust_score": 0.65,  // Below threshold
    "task_creation_attempted": true,
    "generated_task_id": null,
    "generated_faq_id": null,  // Not approved
    "message": "Feedback submitted successfully"
}
```

## Performance Considerations

### Non-Blocking Design
- Golden Set workflow runs as background task
- API response time: < 200ms (database write only)
- Workflow execution: 1-3 seconds (async, does not block)

### Database Transactions
- Feedback record committed BEFORE workflow starts
- Workflow updates `generated_faq_id` in separate transaction
- No rollback cascade (feedback preserved on workflow failure)

### Monitoring Metrics
Track these metrics for Golden Set workflow:
- Feedback submission latency (p50, p95, p99)
- Workflow success rate (%)
- FAQ creation rate from CORRECT feedback (%)
- Average workflow execution time (ms)

## Testing Strategy

### Unit Tests (Existing)
- `tests/api/test_expert_feedback.py` - 16 tests, all passing
- Mock-based testing of API endpoints
- Coverage: API layer, validation, authorization

### Integration Tests (Recommended)
Create new test file: `tests/integration/test_golden_set_workflow.py`

**Test Cases:**
1. `test_correct_feedback_creates_faq()` - High trust expert, auto-approved
2. `test_correct_feedback_needs_review()` - Low trust expert, queued
3. `test_correct_feedback_workflow_failure()` - Graceful degradation
4. `test_duplicate_faq_update()` - Update existing FAQ entry
5. `test_cache_invalidation()` - Verify caches cleared

### End-to-End Tests (QA)
1. Submit CORRECT feedback as verified expert (trust_score = 0.92)
2. Verify FAQ appears in Golden Set (`SELECT * FROM faq_entries`)
3. Query the FAQ via RAG pipeline
4. Verify `feedback.generated_faq_id` populated
5. Check logs for S127-S130 step markers

## Deployment Checklist

### Pre-Deployment
- [x] Code review completed
- [x] All tests passing (16/16)
- [x] Linting passed (Ruff)
- [x] Type checking passed (MyPy)
- [x] Documentation updated

### Deployment Steps
1. Merge to `develop` branch
2. Deploy to QA environment
3. Run integration tests on QA
4. Verify Golden Set workflow with test expert
5. Monitor logs for S127-S130 execution
6. Check `expert_feedback.generated_faq_id` values in QA DB
7. If successful, deploy to production

### Rollback Plan
If Golden Set workflow causes issues:
1. No code rollback needed (workflow failures are graceful)
2. To disable: Comment out workflow trigger in `submit_expert_feedback()`
3. Feedback submission will continue to work normally

## Future Enhancements

### Phase 2: Manual Approval Queue
- Admin dashboard to review candidates in `needs_review` status
- Approve/Reject actions update FAQ and link to feedback
- Email notifications for pending reviews

### Phase 3: FAQ Quality Metrics
- Track FAQ usage frequency (how often retrieved in RAG)
- Measure user satisfaction with FAQ answers
- Auto-deprecate low-quality FAQs

### Phase 4: Batch FAQ Import
- Bulk import from existing knowledge bases
- CSV/Excel upload with validation
- Map legacy IDs to new FAQ entries

## References

- Architecture Diagram: `pratikoai_rag_hybrid.mmd`
- Golden Set Orchestrator: `app/orchestrators/golden.py`
- Expert Feedback Models: `app/models/quality_analysis.py`
- RAG Pipeline Documentation: `docs/architecture/rag-pipeline.md`

## Contact

For questions or issues related to this implementation:
- Workflow Questions: @Ezio (Backend Expert)
- Database Schema: @DatabaseDesigner
- Architecture Decisions: @Architect
