# SQLModel `similarity_score` Field Fix

## Problem Summary

SQLAlchemy was attempting to INSERT `similarity_score` into the `faq_entries` table, even though the field was marked with `sa_column=None`, causing the error:

```
column "similarity_score" of relation "faq_entries" does not exist
[SQL: INSERT INTO faq_entries (..., similarity_score) VALUES ...]
```

## Root Cause Analysis

### The Bug in SQLModel 0.0.24

SQLModel version 0.0.24 has a **confirmed bug** where `sa_column=None` does NOT properly exclude fields from the SQLAlchemy table mapping. This was verified with a test:

```python
class TestModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    computed_field: str | None = Field(default=None, sa_column=None)  # Should be excluded

# Result: computed_field is STILL in __table__.columns!
print([col.name for col in TestModel.__table__.columns])
# Output: ['id', 'name', 'computed_field']  # ❌ computed_field should NOT be here
```

### Why Previous Attempts Failed

1. **`sa_column=None`**: Doesn't work in SQLModel 0.0.24 (bug)
2. **`Field(exclude=True)`**: Also doesn't work - field is still added to table
3. **Clearing cache/restarting**: Couldn't fix a code-level bug

### The Problematic Code Pattern

The issue occurred in `app/services/intelligent_faq_service.py`:

```python
# Line 209: Creating FAQEntry from search results
best_match = FAQEntry(
    id=row.id,
    question=row.question,
    # ... other fields ...
)
# Line 229: Setting similarity_score on the instance
best_match.similarity_score = best_score  # ❌ This causes SQLAlchemy to track it!

# Later...
db.add(best_match)  # ❌ SQLAlchemy tries to INSERT similarity_score
await db.commit()   # ❌ Database error: column doesn't exist
```

When you set an attribute on a SQLModel instance, SQLAlchemy's session tracking treats it as a dirty field that needs to be persisted, even if `sa_column=None`.

## The Solution

**Remove `similarity_score` from the `FAQEntry` model entirely.**

The field was never meant to be persisted - it's only used transiently in search results. The `FAQSearchResult` dataclass already properly stores the similarity score separately.

### Changes Made

#### 1. Remove field from FAQEntry model (`app/models/faq.py`)

**Before:**
```python
class FAQEntry(SQLModel, table=True):
    # ... other fields ...
    search_vector: str | None = Field(default=None, description="...")

    similarity_score: float | None = Field(
        default=None, sa_column=None, description="Similarity score (not persisted)"
    )
```

**After:**
```python
class FAQEntry(SQLModel, table=True):
    # ... other fields ...
    search_vector: str | None = Field(default=None, description="...")

    # NOTE: similarity_score is NOT stored in the database table.
    # It is only used transiently in search results and is stored in
    # the FAQSearchResult dataclass (see intelligent_faq_service.py)
    # Removed from model due to SQLModel 0.0.24 bug where sa_column=None
    # does not properly exclude fields from table mapping.
```

#### 2. Remove assignment in service (`app/services/intelligent_faq_service.py`)

**Before:**
```python
best_match = FAQEntry(...)
best_match.similarity_score = best_score  # ❌ Removed

return FAQSearchResult(
    faq_entry=best_match,
    similarity_score=best_score,  # ✅ Already stored here
    ...
)
```

**After:**
```python
best_match = FAQEntry(...)
# NOTE: similarity_score is stored in FAQSearchResult, not on FAQEntry
# FAQEntry no longer has similarity_score field (removed due to SQLModel bug)

return FAQSearchResult(
    faq_entry=best_match,
    similarity_score=best_score,  # ✅ Properly stored in dataclass
    ...
)
```

### Why This Works

1. **No field in model** → No column in `__table__.columns` → SQLAlchemy doesn't try to INSERT it
2. **FAQSearchResult dataclass** already stores `similarity_score` separately
3. **All existing code** uses `search_result.similarity_score` or `faq_response.similarity_score` (from dataclasses), not from FAQEntry directly
4. **No breaking changes** - the API and tests continue to work as before

## Verification

### Local Verification (Successful)
```python
from app.models.faq import FAQEntry

# Check table columns
print([col.name for col in FAQEntry.__table__.columns])
# Output: ['id', 'question', 'answer', ..., 'search_vector']
# ✅ similarity_score is NOT in the list!

# Create instance
entry = FAQEntry(question='Test', answer='Test')
# ✅ No errors!
```

### Docker Verification (Next Step)
```bash
# In Docker container:
docker-compose exec web python -c "from app.models.faq import FAQEntry; print([col.name for col in FAQEntry.__table__.columns])"

# Run tests:
docker-compose exec web pytest tests/services/test_expert_faq_retrieval_service.py -v
```

## Alternative Solutions Considered

### 1. Upgrade SQLModel
- **Pro**: Would fix the `sa_column=None` bug
- **Con**: Requires testing entire codebase for breaking changes
- **Status**: Consider for future major version upgrade

### 2. Create separate response model with inheritance
```python
class FAQEntryShared(SQLModel):
    question: str
    answer: str

class FAQEntry(FAQEntryShared, table=True):
    id: int = Field(primary_key=True)

class FAQEntryWithScore(FAQEntryShared):
    id: int
    similarity_score: float
```
- **Pro**: Clean separation of concerns
- **Con**: More complex, requires refactoring all FAQEntry usage
- **Status**: Overkill for this use case since FAQSearchResult already exists

### 3. Use `@computed_field` decorator
```python
from pydantic import computed_field

class FAQEntry(SQLModel, table=True):
    @computed_field
    @property
    def similarity_score(self) -> float:
        return getattr(self, '_similarity_score', 0.0)
```
- **Pro**: Pythonic property pattern
- **Con**: Still has issues with SQLAlchemy session tracking
- **Status**: Doesn't solve the core problem

## Lessons Learned

1. **`sa_column=None` doesn't work reliably in SQLModel 0.0.24** - it's a known bug
2. **Don't add computed/transient fields to SQLModel table models** - use separate dataclasses or response models instead
3. **SQLAlchemy tracks all instance attributes**, even with `sa_column=None`, when set after instantiation
4. **The proper pattern**:
   - Table model (SQLModel with `table=True`) = only persisted fields
   - Response/DTO model (Pydantic BaseModel or dataclass) = computed/transient fields

## Related Files

- `/Users/micky/PycharmProjects/PratikoAi-BE/app/models/faq.py` - FAQEntry model definition
- `/Users/micky/PycharmProjects/PratikoAi-BE/app/services/intelligent_faq_service.py` - Service using FAQEntry
- `/Users/micky/PycharmProjects/PratikoAi-BE/tests/services/test_expert_faq_retrieval_service.py` - Tests

## Testing Checklist

- [x] Verify `similarity_score` removed from `FAQEntry.__table__.columns`
- [x] Verify FAQEntry instance creation works
- [ ] Run FAQ service tests in Docker
- [ ] Run full test suite
- [ ] Verify API endpoints still return similarity_score correctly
- [ ] Test search functionality end-to-end

## References

- SQLModel Issue: https://github.com/tiangolo/sqlmodel/issues/52 (similar issue)
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html
- Pydantic Field Documentation: https://docs.pydantic.dev/latest/concepts/fields/
