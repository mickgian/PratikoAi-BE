# ADR-014: SQLModel as Exclusive ORM Standard

## Status
**ACCEPTED** - Mandatory for all new and existing models

## Context

### The Problem
During the development of PratikoAI, we encountered critical schema drift issues caused by mixing multiple ORM patterns:

1. **SQLAlchemy Base pattern** (`declarative_base()`)
2. **SQLModel pattern** (FastAPI native)
3. **Intermediate base classes** that caused confusion

This mixing led to:
- Alembic migration detection failures
- Schema drift between models and database
- Confusion about which pattern to use
- Failed migrations due to NameError with sqlmodel types
- Developer cognitive overhead switching between patterns

### The Migration
A comprehensive 4-phase migration was completed:
- **Phase 1**: 15 models converted (payment, usage, quality_analysis)
- **Phase 2**: 6 models converted (faq, faq_automation)
- **Phase 3**: 21 models converted (knowledge, documents, regulatory, italian_data, etc.)
- **Phase 4**: 4 models converted (regional_taxes)
- **Total**: 46 models, 100% coverage achieved

### Key Lessons Learned
1. **Name confusion is dangerous**: `Base` vs `BaseModel` creates same problem
2. **Simplicity wins**: Direct inheritance from SQLModel is clearest
3. **Type hints matter**: SQLModel's Pydantic integration provides runtime validation
4. **Migration tooling**: Alembic needs explicit sqlmodel imports in migrations
5. **Documentation is critical**: Clear standards prevent future confusion

## Decision

### MANDATORY Standard

**We adopt SQLModel as the EXCLUSIVE ORM for ALL database models in PratikoAI.**

All models MUST use this pattern:

```python
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from datetime import datetime

class ModelName(SQLModel, table=True):
    """Model description."""
    __tablename__ = "table_name"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Fields with type hints
    name: str = Field(max_length=100, index=True)
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    # Relationships
    items: List["Item"] = Relationship(back_populates="parent")

    # Timestamps (if needed, add explicitly)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
```

### FORBIDDEN Patterns

These patterns are **PERMANENTLY BANNED** and will cause PR rejection:

```python
# ❌ NEVER USE - SQLAlchemy Base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
class Model(Base):
    __tablename__ = "table"
    id = Column(Integer, primary_key=True)

# ❌ NEVER USE - BaseModel intermediate class
from app.models.base import BaseModel
class Model(BaseModel, table=True):  # Confusing - looks like old Base pattern
    __tablename__ = "table"

# ❌ NEVER USE - relationship() function
from sqlalchemy.orm import relationship
items = relationship("Item", back_populates="parent")  # Wrong - use Relationship()

# ❌ NEVER USE - Column() for simple types
from sqlalchemy import Column, String
name = Column(String(100))  # Wrong - use Field()
```

### ACCEPTABLE Alternative (If Truly Needed)

If you absolutely need shared fields across models, use this pattern with CLEAR naming:

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
from sqlalchemy import Column, DateTime, func

class BaseSQLModel(SQLModel):
    """Shared timestamp fields for all models.

    Note: Name is BaseSQLModel (NOT BaseModel) to avoid confusion
    with old SQLAlchemy Base pattern.
    """
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

# Use it like this
class User(BaseSQLModel, table=True):
    __tablename__ = "user"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
```

**Critical Rule**: If using intermediate class, name it `BaseSQLModel` NOT `BaseModel`

## Consequences

### Positive
1. **Single source of truth**: One ORM pattern for entire codebase
2. **FastAPI integration**: Native Pydantic validation
3. **Type safety**: Full mypy/pyright support
4. **Clear migrations**: Alembic detects all changes correctly
5. **Developer clarity**: No confusion about which pattern to use
6. **Easier onboarding**: New developers learn one pattern
7. **Better errors**: Pydantic provides clear validation errors

### Negative
1. **Complex types require sa_column**: PostgreSQL ARRAY, JSONB, etc. need explicit Column()
2. **Learning curve**: Team needs to learn SQLModel Field syntax
3. **Migration work**: Existing Base models need conversion (COMPLETED)

### Mitigation
- Comprehensive documentation (this ADR + standards guide)
- PR review checklist for all model changes
- Pre-commit hooks to enforce standards
- CI/CD validation for SQLModel compliance
- Training session for team

## Enforcement

### Pre-commit Hooks

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: check-sqlmodel-compliance
      name: Check SQLModel Compliance
      entry: python scripts/check_sqlmodel_compliance.py
      language: python
      files: ^app/models/.*\.py$
      pass_filenames: true
```

### CI/CD Validation

Add to GitHub Actions:

```yaml
- name: Validate SQLModel Compliance
  run: |
    python scripts/check_sqlmodel_compliance.py app/models/
    if [ $? -ne 0 ]; then
      echo "❌ SQLModel compliance check failed"
      echo "All models must inherit from SQLModel, not Base"
      exit 1
    fi
```

### Code Review Checklist

Every PR touching `app/models/*.py` MUST be reviewed against:
- ✅ Uses `SQLModel, table=True` (NOT Base, NOT BaseModel)
- ✅ Uses `Field()` for simple types
- ✅ Uses `Relationship()` for relationships
- ✅ Has proper type hints
- ✅ Includes Alembic migration
- ✅ Alembic migration imports sqlmodel
- ✅ Has corresponding test file
- ✅ Follows naming conventions (BaseSQLModel if intermediate class needed)

## References

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [FastAPI SQLModel Tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- ADR-012: Pre-commit Test Enforcement
- ADR-013: TDD Methodology
- docs/architecture/SQLMODEL_STANDARDS.md
- docs/architecture/SQLMODEL_REVIEW_CHECKLIST.md

## Revision History

- 2025-11-28: Initial version - Established SQLModel as exclusive ORM
- 2025-11-28: Clarified BaseModel vs BaseSQLModel naming to avoid confusion
