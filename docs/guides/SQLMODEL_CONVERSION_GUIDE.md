# SQLModel Conversion Guide

**Version:** 1.0
**Date:** 2025-11-28
**Purpose:** Comprehensive guide for converting SQLAlchemy Base models to SQLModel

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Conversion Patterns](#conversion-patterns)
3. [Special Cases](#special-cases)
4. [Testing Checklist](#testing-checklist)
5. [Common Pitfalls](#common-pitfalls)

---

## Prerequisites

### Before Starting

✅ **Phase 0 Complete:**
- [x] FK table name consistency fixed (`user.id` not `users.id`)
- [x] UUID→Integer type mismatches fixed
- [x] Baseline TDD tests written
- [x] Schema drift audit complete
- [x] Alembic migration history verified

### Required Knowledge

- SQLAlchemy ORM basics
- SQLModel fundamentals (inherits from SQLAlchemy + Pydantic)
- PostgreSQL column types
- Alembic migrations

### Tools Needed

- ✅ Baseline tests (created by Clelia)
- ✅ Schema validation script (`scripts/validate_schema_alignment.sql`)
- ✅ Audit documents (created by Primo)

---

## Conversion Patterns

### Pattern 1: Basic Model Conversion

**BEFORE (SQLAlchemy Base):**
```python
from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.models.ccnl_database import Base

class ExampleModel(Base):
    __tablename__ = "examples"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    count = Column(Integer, default=0)
    active = Column(Boolean, default=True)
```

**AFTER (SQLModel):**
```python
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel

class ExampleModel(SQLModel, table=True):
    __tablename__ = "examples"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100)
    count: int = Field(default=0)
    active: bool = Field(default=True)
```

**Key Changes:**
1. `Base` → `SQLModel, table=True`
2. `Column()` → type annotations with `Field()`
3. `PG_UUID(as_uuid=True)` → `UUID` (native Python type)
4. `default=uuid4` → `default_factory=uuid4`
5. `nullable=False` is implied (use `Optional[str]` or `str | None` for nullable)

---

### Pattern 2: PostgreSQL ARRAY Columns

**BEFORE:**
```python
from sqlalchemy import Column, ARRAY, String

tags = Column(ARRAY(String(50)), default=list)
```

**AFTER:**
```python
from sqlmodel import Field, Column
from sqlalchemy import ARRAY, String

tags: list[str] = Field(
    default_factory=list,
    sa_column=Column(ARRAY(String(50)))
)
```

**Why `sa_column`?**
- SQLModel doesn't natively support PostgreSQL ARRAY
- Use `sa_column` to pass raw SQLAlchemy Column definition
- Keeps type hints Pythonic (`list[str]`) while maintaining DB schema

**Total in codebase:** 38 ARRAY columns need this pattern

---

### Pattern 3: PostgreSQL JSONB Columns

**BEFORE:**
```python
from sqlalchemy import Column, JSONB

metadata_json = Column(JSONB, default=dict)
```

**AFTER:**
```python
from sqlmodel import Field, Column
from sqlalchemy.dialects.postgresql import JSONB

metadata_json: dict = Field(
    default_factory=dict,
    sa_column=Column(JSONB)
)
```

**Key Points:**
- Use `default_factory=dict` not `default={}` (mutable default)
- Import `JSONB` from `sqlalchemy.dialects.postgresql`
- Type hint as `dict` or `dict[str, Any]`

**Total in codebase:** 24 JSONB columns need this pattern

---

### Pattern 4: pgvector Embeddings (CRITICAL)

**BEFORE:**
```python
from sqlalchemy import Column
from pgvector.sqlalchemy import Vector

embedding = Column(Vector(1536))
```

**AFTER:**
```python
from sqlmodel import Field, Column
from pgvector.sqlalchemy import Vector

embedding: list[float] | None = Field(
    default=None,
    sa_column=Column(Vector(1536)),
    description="1536-d vector embedding (pgvector)"
)
```

**Reference Implementation:**
See `app/models/knowledge_chunk.py:45-48` (already migrated)

**Models Affected:**
- `faq_automation.py`: GeneratedFAQ.embedding
- `quality_analysis.py`: ExpertProfile.embedding (if exists)

**Total in codebase:** 2-4 Vector columns

---

### Pattern 5: Enum Columns

**BEFORE:**
```python
from sqlalchemy import Column, Enum
from enum import Enum as PyEnum

class Status(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"

status = Column(Enum(Status), default=Status.PENDING)
```

**AFTER:**
```python
from enum import Enum as PyEnum
from sqlmodel import Field

class Status(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"

status: Status = Field(default=Status.PENDING)
```

**Key Points:**
- SQLModel natively supports Python Enums
- No `sa_column` override needed
- Enum must inherit from `str` for proper DB serialization

**Total in codebase:** 15 enum columns (already work!)

---

### Pattern 6: Foreign Keys

**BEFORE:**
```python
from sqlalchemy import Column, Integer, ForeignKey

user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
```

**AFTER:**
```python
from sqlmodel import Field

user_id: int = Field(foreign_key="user.id")
```

**Relationship Pattern:**

**BEFORE:**
```python
from sqlalchemy.orm import relationship

approver = relationship("User", foreign_keys=[approved_by])
```

**AFTER:**
```python
from sqlmodel import Relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User

approver: "User | None" = Relationship(
    sa_relationship_kwargs={"foreign_keys": "[ExampleModel.user_id]"}
)
```

**Critical Notes:**
1. Use `TYPE_CHECKING` imports to avoid circular imports
2. Relationship names should be descriptive (`approver`, not `user`)
3. Always specify `foreign_keys` explicitly for clarity

---

### Pattern 7: Indexes and Constraints

**BEFORE:**
```python
from sqlalchemy import Column, String, Index, CheckConstraint

class ExampleModel(Base):
    __tablename__ = "examples"

    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)

    __table_args__ = (
        Index('idx_name_email', 'name', 'email'),
        CheckConstraint('char_length(name) > 0', name='ck_name_not_empty'),
    )
```

**AFTER:**
```python
from sqlmodel import Field, SQLModel
from sqlalchemy import Index, CheckConstraint

class ExampleModel(SQLModel, table=True):
    __tablename__ = "examples"

    name: str = Field(max_length=100)
    email: str = Field(max_length=255, unique=True, index=True)

    __table_args__ = (
        Index('idx_name_email', 'name', 'email'),
        CheckConstraint('char_length(name) > 0', name='ck_name_not_empty'),
    )
```

**Key Points:**
- `__table_args__` works identically in SQLModel
- Use `Field(index=True, unique=True)` for simple indexes
- Complex indexes still use `Index()` in `__table_args__`

**Total in codebase:** 80+ indexes, 28 check constraints

---

## Special Cases

### Case 1: Models with Multiple Bases

**Problem:**
```python
# ccnl_update_models.py has its OWN Base!
Base = declarative_base()  # ❌ Separate metadata registry
```

**Solution:**
- Remove local `Base = declarative_base()`
- Import SQLModel from `sqlmodel`
- All models use same `SQLModel.metadata`

---

### Case 2: Nullable vs Not-Nullable

**SQLAlchemy (explicit):**
```python
name = Column(String(100), nullable=False)  # Required
email = Column(String(255), nullable=True)  # Optional
```

**SQLModel (type-hint based):**
```python
name: str = Field(max_length=100)              # NOT NULL (required)
email: str | None = Field(default=None, max_length=255)  # NULL (optional)
```

**Rules:**
- `str` → NOT NULL
- `str | None` or `Optional[str]` → NULL
- Always specify `default=None` for optional fields

---

### Case 3: Timestamps with server_default

**BEFORE:**
```python
from sqlalchemy import Column, DateTime, func

created_at = Column(DateTime(timezone=True), server_default=func.now())
updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**AFTER:**
```python
from sqlmodel import Field, Column
from sqlalchemy import DateTime, func
from datetime import datetime

created_at: datetime = Field(
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
)
updated_at: datetime | None = Field(
    default=None,
    sa_column=Column(DateTime(timezone=True), onupdate=func.now())
)
```

**Why `sa_column`?**
- `server_default=func.now()` is PostgreSQL-specific
- `onupdate` requires SQLAlchemy Column
- Type hint remains `datetime` for Pydantic validation

---

### Case 4: Tables That Don't Exist Yet

**36 tables are missing from database!**

**Options:**
1. **Create tables via Alembic** (recommended)
   - Generate migration: `alembic revision --autogenerate -m "Create missing Base model tables"`
   - Review SQL carefully (verify types match database)
   - Apply: `alembic upgrade head`

2. **Delete unused models**
   - If model was never used, delete it
   - Document in migration guide why it was removed

**For Phase 3 (faq_automation, quality_analysis):**
- Tables will be created during SQLModel migration
- Use corrected types (Integer for user_id)
- Alembic will detect new tables automatically

---

## Testing Checklist

### Before Migration (Baseline)

- [ ] Run baseline tests: `uv run pytest tests/models/baseline_migration/`
- [ ] Document current pass/fail state
- [ ] Verify schema matches database: `psql ... < scripts/validate_schema_alignment.sql`

### During Migration (Per File)

- [ ] Convert model syntax (Base → SQLModel)
- [ ] Update imports
- [ ] Handle ARRAY/JSONB/Vector with `sa_column`
- [ ] Update relationships to `Relationship`
- [ ] Remove `Base` import
- [ ] Generate Alembic migration: `alembic revision --autogenerate`
- [ ] Review migration SQL (verify no unintended changes)

### After Migration (Validation)

- [ ] Run same baseline tests (must pass!)
- [ ] Check Alembic detects schema changes: `alembic revision --autogenerate -m "test"`
- [ ] Verify no pending migrations: Should say "No changes detected"
- [ ] Run full test suite: `uv run pytest`
- [ ] Manual smoke test (create, read, update, delete)

---

## Common Pitfalls

### ❌ Pitfall 1: Mutable Defaults

**WRONG:**
```python
tags: list[str] = Field(default=[])  # ❌ Shared mutable object!
metadata_json: dict = Field(default={})  # ❌ Same dict for all instances!
```

**CORRECT:**
```python
tags: list[str] = Field(default_factory=list)  # ✅ New list per instance
metadata_json: dict = Field(default_factory=dict)  # ✅ New dict per instance
```

---

### ❌ Pitfall 2: UUID Default

**WRONG:**
```python
id: UUID = Field(default=uuid4(), primary_key=True)  # ❌ Same UUID for all!
```

**CORRECT:**
```python
id: UUID = Field(default_factory=uuid4, primary_key=True)  # ✅ New UUID per instance
```

---

### ❌ Pitfall 3: Forgetting sa_column

**WRONG:**
```python
tags: list[str] = Field(default_factory=list)  # ❌ Alembic sees TEXT, not ARRAY!
```

**CORRECT:**
```python
tags: list[str] = Field(
    default_factory=list,
    sa_column=Column(ARRAY(String(50)))  # ✅ Preserves PostgreSQL ARRAY
)
```

---

### ❌ Pitfall 4: Circular Imports

**WRONG:**
```python
from app.models.user import User  # ❌ Circular import at module load!

class Example(SQLModel, table=True):
    approver: User = Relationship()  # ❌ Tries to resolve User at import time
```

**CORRECT:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # ✅ Only imported during type checking
    from app.models.user import User

class Example(SQLModel, table=True):
    approver: "User | None" = Relationship()  # ✅ String annotation
```

---

### ❌ Pitfall 5: Wrong Nullable Logic

**WRONG:**
```python
# Database: user_id INTEGER NOT NULL
user_id: int | None = Field(foreign_key="user.id")  # ❌ Allows NULL!
```

**CORRECT:**
```python
# Database: user_id INTEGER NOT NULL
user_id: int = Field(foreign_key="user.id")  # ✅ NOT NULL
```

---

## Migration Order (Phase by Phase)

### Phase 1: Simple Models (Proof of Concept)

**File:** `app/models/regional_taxes.py`
**Models:** 4 (RegionalTax, TaxCalculator, TaxExemption, TaxUpdate)
**Why First:** No User FKs, no pgvector, simple JSONB only
**Estimated Time:** 4-6 hours

**Checklist:**
- [ ] Convert all 4 models to SQLModel
- [ ] Test JSONB handling
- [ ] Generate Alembic migration
- [ ] Verify migration SQL
- [ ] Apply migration
- [ ] Run baseline tests
- [ ] Document learnings

---

### Phase 2: CCNL Models (Consolidate Metadata)

**Files:**
- `app/models/ccnl_database.py` (9 models)
- `app/models/ccnl_update_models.py` (5 models)

**Critical:** Remove 2 separate `Base = declarative_base()` definitions
**Estimated Time:** 8-12 hours

**Checklist:**
- [ ] Remove `Base = declarative_base()` from both files
- [ ] Import `SQLModel` from `sqlmodel`
- [ ] Convert all 14 models
- [ ] Handle complex relationships
- [ ] Test cascade deletes
- [ ] Generate Alembic migration
- [ ] Verify no orphaned metadata

---

### Phase 3: User-Dependent Models (CRITICAL - Fixes Corretta)

**Files:**
- `app/models/quality_analysis.py` (9 models)
- `app/models/faq_automation.py` (5 models)

**Blockers Resolved:** UUID→Integer type mismatches already fixed
**Estimated Time:** 12-16 hours

**Critical Models:**
- GeneratedFAQ (pgvector, User FK)
- ExpertProfile (pgvector, User FK)
- ExpertFAQCandidate (User FK)

**Checklist:**
- [ ] Convert all 14 models to SQLModel
- [ ] Handle pgvector Vector(1536) columns
- [ ] Remove lambda relationship workarounds
- [ ] Remove `use_alter=True` hacks
- [ ] Test User relationships thoroughly
- [ ] Generate Alembic migration
- [ ] **TEST CORRETTA BUTTON** ← PRIMARY SUCCESS METRIC!

---

### Phase 4: Business Models

**Files:**
- `app/models/subscription.py` (4 models)
- `app/models/data_export.py` (8 models)

**Focus:** Payment workflows, GDPR exports
**Estimated Time:** 8-10 hours

---

### Phase 5: Final Validation

**Estimated Time:** 4-6 hours

**Checklist:**
- [ ] All 44 models migrated
- [ ] Zero `declarative_base()` references
- [ ] Alembic autogenerate works for all models
- [ ] All baseline tests pass
- [ ] Corretta button works
- [ ] Production deployment successful

---

## Success Criteria

✅ **Technical:**
- All 44 models inherit from `SQLModel`
- Single metadata registry (`SQLModel.metadata`)
- Alembic detects schema changes for all models
- Zero FK type mismatches
- All baseline tests pass

✅ **Functional:**
- Corretta button works (no mapper errors)
- Golden set workflow functions
- All relationships resolve correctly
- No database schema drift

✅ **Process:**
- Comprehensive documentation
- Rollback plan exists
- Team trained on SQLModel patterns
- Migration completed within 4-6 weeks

---

## Resources

- **SQLModel Docs:** https://sqlmodel.tiangolo.com/
- **Baseline Tests:** `tests/models/baseline_migration/`
- **Schema Audit:** `SCHEMA_DRIFT_AUDIT.md`
- **FK Analysis:** `FK_ANALYSIS.md`
- **Quick Fix Guide:** `QUICK_FIX_GUIDE.md`
- **Reference Implementation:** `app/models/knowledge_chunk.py` (pgvector example)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-28
**Next Review:** After Phase 1 completion

---

*This guide will be updated after each phase based on lessons learned.*
