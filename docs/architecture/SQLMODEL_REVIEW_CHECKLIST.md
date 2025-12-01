# SQLModel Code Review Checklist

**Mandatory checklist for ALL pull requests modifying database models**

Use this checklist when reviewing PRs that touch files in `app/models/` or create new Alembic migrations.

## Quick Commands for Reviewers

```bash
# Check for forbidden Base imports
rg "from.*declarative_base" app/models/
rg "^Base = declarative_base" app/models/

# Check for confusing BaseModel imports (should be BaseSQLModel if needed)
rg "from app.models.base import BaseModel" app/models/

# Check for old relationship() usage
rg "from sqlalchemy.orm import relationship" app/models/
rg "= relationship\(" app/models/

# Check for SQLModel imports
rg "from sqlmodel import" app/models/

# Check migration includes sqlmodel
rg "^import sqlmodel" alembic/versions/

# Verify test exists for new model
ls tests/models/test_*.py
```

## Checklist Sections

1. [Model Declaration](#1-model-declaration)
2. [Field Definitions](#2-field-definitions)
3. [Relationships](#3-relationships)
4. [Enums](#4-enums)
5. [Timestamps](#5-timestamps)
6. [Indexes & Constraints](#6-indexes--constraints)
7. [Testing](#7-testing)
8. [Performance](#8-performance)
9. [Security & GDPR](#9-security--gdpr)
10. [Documentation](#10-documentation)

---

## 1. Model Declaration

### ✅ Required

- [ ] Model inherits from `SQLModel, table=True`
- [ ] Has explicit `__tablename__` attribute
- [ ] Has class docstring explaining purpose
- [ ] All fields have type hints
- [ ] Model is imported in `alembic/env.py`

### ❌ Blocking Issues (Auto-reject PR)

- [ ] ❌ Inherits from SQLAlchemy `Base` instead of `SQLModel`
- [ ] ❌ Imports `BaseModel` from `app.models.base` (confusing - use `BaseSQLModel` or direct `SQLModel`)
- [ ] ❌ Uses `table=True` with SQLAlchemy Base (should be SQLModel)
- [ ] ❌ Missing type hints on fields

### Example

```python
# ✅ CORRECT
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    """User account model."""
    __tablename__ = "user"
    id: int = Field(default=None, primary_key=True)

# ❌ WRONG - SQLAlchemy Base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
class User(Base):
    __tablename__ = "user"

# ❌ WRONG - Confusing BaseModel
from app.models.base import BaseModel
class User(BaseModel, table=True):
    ...

# ✅ ACCEPTABLE - Clear BaseSQLModel naming
from app.models.base_sqlmodel import BaseSQLModel
class User(BaseSQLModel, table=True):
    ...
```

---

## 2. Field Definitions

### ✅ Required

- [ ] All fields use `Field()` not `Column()`
- [ ] UUID primary keys use `default_factory=uuid4`
- [ ] Currency fields use `Decimal` with `Numeric(10, 2)`
- [ ] Strings have `max_length` constraint
- [ ] Foreign keys reference singular table name (e.g., `"user.id"` not `"users.id"`)
- [ ] Optional fields use `| None` type hint and `default=None`
- [ ] Mutable defaults use `default_factory` not `default`

### ❌ Blocking Issues (Auto-reject PR)

- [ ] ❌ Uses `Column()` for simple types (should use `Field()`)
- [ ] ❌ Foreign key references plural table name
- [ ] ❌ Mutable default without `default_factory` (e.g., `default=[]`)
- [ ] ❌ Currency field uses `float` instead of `Decimal`
- [ ] ❌ No type hints on fields

### Example

```python
from uuid import UUID, uuid4
from decimal import Decimal
from sqlalchemy import Column, Numeric

# ✅ CORRECT
class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: int = Field(foreign_key="user.id")  # Singular!
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    tags: List[str] = Field(default_factory=list)

# ❌ WRONG
class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True)  # Wrong: Column()
    user_id: int = Field(foreign_key="users.id")  # Wrong: plural
    amount: float = Field()  # Wrong: float for money
    tags: List[str] = Field(default=[])  # Wrong: mutable default
```

---

## 3. Relationships

### ✅ Required

- [ ] Uses `Relationship()` with capital R (not `relationship()`)
- [ ] Has matching `back_populates` on both sides
- [ ] One-to-many uses `List["Model"]` type hint
- [ ] Many-to-one uses `"Model"` type hint (no List)
- [ ] Cascade delete uses `sa_relationship_kwargs={"cascade": "..."}`

### ❌ Blocking Issues (Auto-reject PR)

- [ ] ❌ Uses SQLAlchemy `relationship()` instead of `Relationship()`
- [ ] ❌ Missing `back_populates` causing orphaned relationships
- [ ] ❌ Wrong type hint (e.g., `List` on many-to-one side)

### Example

```python
from sqlmodel import Relationship
from typing import List

# ✅ CORRECT
class User(SQLModel, table=True):
    __tablename__ = "user"
    id: int = Field(default=None, primary_key=True)

    orders: List["Order"] = Relationship(back_populates="user")

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")

    user: "User" = Relationship(back_populates="orders")

# ❌ WRONG
from sqlalchemy.orm import relationship

class User(SQLModel, table=True):
    orders = relationship("Order")  # Wrong: lowercase relationship()
```

---

## 4. Enums

### ✅ Required

- [ ] Uses `SQLEnum` with explicit `name=` parameter
- [ ] Inherits from `str, Enum` for JSON serialization
- [ ] Has meaningful enum values (not just integers)
- [ ] Enum name follows pattern: `{table}_{field}_enum`

### ❌ Blocking Issues (Auto-reject PR)

- [ ] ❌ Enum without explicit `name=` parameter
- [ ] ❌ Uses string literals instead of proper Enum class

### Example

```python
from enum import Enum
from sqlalchemy import Column
from sqlalchemy.types import Enum as SQLEnum

# ✅ CORRECT
class StatusType(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    status: StatusType = Field(
        sa_column=Column(
            SQLEnum(StatusType, name="task_status_enum"),
            server_default="pending"
        )
    )

# ❌ WRONG
class Task(SQLModel, table=True):
    status: StatusType = Field(
        sa_column=Column(SQLEnum(StatusType))  # Missing name=
    )
```

---

## 5. Timestamps

### ✅ Required

- [ ] Uses `DateTime(timezone=True)` for timestamp fields
- [ ] Uses `server_default=func.now()` for creation timestamp
- [ ] Uses `onupdate=func.now()` for update timestamp
- [ ] Import `func` from sqlalchemy

### ❌ Blocking Issues (Auto-reject PR)

- [ ] ❌ DateTime without `timezone=True`
- [ ] ❌ Uses Python `default_factory=datetime.utcnow` instead of `server_default`
- [ ] ❌ Missing timezone handling

### Example

```python
from datetime import datetime
from sqlalchemy import Column, DateTime, func

# ✅ CORRECT
class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=func.now()
        )
    )

# ❌ WRONG
class AuditLog(SQLModel, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)  # No timezone!
    updated_at: datetime = Field(sa_column=Column(DateTime()))  # No timezone!
```

---

## 6. Indexes & Constraints

### ✅ Required

- [ ] Unique constraints have explicit names
- [ ] Foreign keys are indexed
- [ ] Email fields are indexed
- [ ] Frequently queried fields are indexed
- [ ] Composite indexes use meaningful names
- [ ] Index names follow pattern: `idx_{table}_{columns}`

### ⚠️ Warning Issues

- [ ] ⚠️ More than 5 indexes on single table (performance impact)
- [ ] ⚠️ Index on low-cardinality field (boolean, small enum)
- [ ] ⚠️ Missing index on foreign key

### Example

```python
from sqlalchemy import Index, UniqueConstraint

# ✅ CORRECT
class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    email: str = Field(unique=True, index=True)

    __table_args__ = (
        UniqueConstraint("user_id", "plan_type", name="uq_user_plan"),
        Index("idx_subscription_active", "user_id", "is_active"),
    )
```

---

## 7. Testing

### ✅ Required

- [ ] Test file exists at `tests/models/test_{model}.py`
- [ ] Tests model creation
- [ ] Tests unique constraints
- [ ] Tests foreign key relationships
- [ ] Tests enum validation
- [ ] Tests required field validation
- [ ] Tests timestamp defaults

### ❌ Blocking Issues (Auto-reject PR)

- [ ] ❌ No test file exists for new model
- [ ] ❌ Test file doesn't import the model
- [ ] ❌ No tests for unique constraints
- [ ] ❌ No tests for relationships

### Example

```python
# tests/models/test_user.py
import pytest
from sqlmodel import Session, create_engine, SQLModel
from app.models.user import User

def test_user_creation():
    """Test creating a user."""
    user = User(email="test@example.com")
    assert user.email == "test@example.com"

def test_user_email_unique(session):
    """Test email uniqueness constraint."""
    user1 = User(email="test@example.com")
    session.add(user1)
    session.commit()

    user2 = User(email="test@example.com")
    session.add(user2)

    with pytest.raises(Exception):
        session.commit()
```

---

## 8. Performance

### ✅ Required

- [ ] Foreign keys are indexed
- [ ] Large text fields use `Text()` not `String(10000)`
- [ ] Decimal precision matches business requirements
- [ ] Soft deletes use indexed `deleted_at` column
- [ ] Composite indexes ordered by selectivity (high to low)

### ⚠️ Warning Issues

- [ ] ⚠️ JSONB field without GIN index for searches
- [ ] ⚠️ Text field with full-text search needs tsvector
- [ ] ⚠️ Missing pagination on list endpoints
- [ ] ⚠️ N+1 query risk (missing eager loading)

### Example

```python
# ✅ CORRECT - Indexed soft delete
class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: int = Field(default=None, primary_key=True)
    deleted_at: datetime | None = Field(default=None, index=True)

    # Composite index with high selectivity first
    __table_args__ = (
        Index("idx_product_active", "category_id", "is_active", "created_at"),
    )
```

---

## 9. Security & GDPR

### ✅ Required

- [ ] PII fields (email, name, phone) documented as sensitive
- [ ] Password fields use `hashed_password` naming
- [ ] No plaintext passwords or tokens stored
- [ ] IP addresses anonymized before storage
- [ ] Soft delete for user data (not hard delete)

### ❌ Blocking Issues (Auto-reject PR)

- [ ] ❌ Field named `password` (should be `hashed_password`)
- [ ] ❌ Storing OAuth tokens without encryption
- [ ] ❌ Hard delete of user data (GDPR right to be forgotten requires audit trail)

### Example

```python
# ✅ CORRECT
class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)  # PII
    hashed_password: str | None = Field(default=None)  # Not "password"
    deleted_at: datetime | None = Field(default=None)  # Soft delete

# ❌ WRONG
class User(SQLModel, table=True):
    password: str = Field()  # NEVER store plaintext!
```

---

## 10. Documentation

### ✅ Required

- [ ] Model has class docstring
- [ ] Docstring lists key attributes
- [ ] Complex business logic explained in docstring
- [ ] Migration has descriptive revision message
- [ ] README updated if new model category added
- [ ] `alembic/env.py` imports the new model

### ❌ Blocking Issues (Auto-reject PR)

- [ ] ❌ No Alembic migration included
- [ ] ❌ Migration doesn't import `sqlmodel`
- [ ] ❌ Model not imported in `alembic/env.py`
- [ ] ❌ No docstring on model class

### Example

```python
# ✅ CORRECT
class User(SQLModel, table=True):
    """User account model.

    Represents a user account with authentication and profile data.
    Supports both email/password and OAuth authentication.

    Attributes:
        id: Primary key
        email: Unique email address (PII)
        hashed_password: Bcrypt hashed password (nullable for OAuth)
        provider: Auth provider ('email', 'google', 'linkedin')
        sessions: Related chat sessions
    """
    __tablename__ = "user"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
```

---

## Pre-commit Hooks

Ensure these hooks pass before PR:

```bash
# Check SQLModel compliance
python scripts/check_sqlmodel_compliance.py app/models/

# Run model tests
pytest tests/models/ -v

# Type checking
mypy app/models/

# Format check
ruff check app/models/
ruff format --check app/models/
```

---

## Final Approval Checklist

Before approving PR:

- [ ] All blocking issues (❌) resolved
- [ ] Warning issues (⚠️) acknowledged or resolved
- [ ] Tests pass locally and in CI
- [ ] Migration tested locally
- [ ] Documentation updated
- [ ] Code follows SQLModel standards
- [ ] No `Base` or `BaseModel` imports (use `BaseSQLModel` if needed)
- [ ] No old `relationship()` usage
- [ ] All enums have explicit names
- [ ] All timestamps are timezone-aware
- [ ] Pre-commit hooks pass

---

## References

- ADR-014: SQLModel Exclusive ORM
- SQLMODEL_STANDARDS.md
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

## Questions?

If unsure about any checklist item, ask in PR comments and tag:
- @backend-expert for model design
- @database-designer for schema optimization
- @test-generation for testing guidance
