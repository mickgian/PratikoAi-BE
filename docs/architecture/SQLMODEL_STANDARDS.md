# SQLModel Standards and Patterns

**Mandatory Reference for All Database Models**

This document defines the ONLY acceptable patterns for database models in PratikoAI. All models MUST follow these standards.

## Table of Contents

1. [Core Principle](#core-principle)
2. [Model Declaration](#model-declaration)
3. [Field Definitions](#field-definitions)
4. [Relationships](#relationships)
5. [Enums](#enums)
6. [Complex Types](#complex-types)
7. [Timestamps](#timestamps)
8. [Indexes and Constraints](#indexes-and-constraints)
9. [Forbidden Patterns](#forbidden-patterns)
10. [Testing Requirements](#testing-requirements)
11. [Performance Guidelines](#performance-guidelines)

## Core Principle

**Use SQLModel directly. No intermediate base classes unless absolutely necessary.**

```python
# ✅ CORRECT - Direct SQLModel inheritance
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    __tablename__ = "user"
    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)

# ❌ WRONG - Confusing intermediate class
from app.models.base import BaseModel
class User(BaseModel, table=True):  # Looks like old Base pattern!
    ...

# ✅ ACCEPTABLE - Only if truly needed, with CLEAR naming
from app.models.base_sqlmodel import BaseSQLModel
class User(BaseSQLModel, table=True):  # Clear: BaseSQLModel not BaseModel
    ...
```

**Critical**: If you need an intermediate class for shared fields, name it `BaseSQLModel` (NOT `BaseModel`).

## Model Declaration

### Standard Pattern

```python
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

class Product(SQLModel, table=True):
    """Product catalog entry.

    Attributes:
        id: Primary key (UUID)
        name: Product name
        price: Price in EUR (2 decimal places)
        category_id: Foreign key to category
        created_at: Creation timestamp (UTC)
    """
    __tablename__ = "products"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Basic fields
    name: str = Field(max_length=200, index=True)
    description: str | None = Field(default=None, max_length=2000)

    # Numeric with precision
    price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    # Foreign key
    category_id: UUID = Field(foreign_key="categories.id")

    # Relationships
    category: "Category" = Relationship(back_populates="products")

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
```

### Key Points

1. **Always use `table=True`** - This creates the database table
2. **Add `__tablename__`** - Explicit table names are clearer
3. **Include docstring** - Document purpose and fields
4. **Type hints required** - Use modern Python typing
5. **Forward references** - Use quotes for not-yet-defined types

## Field Definitions

### Basic Types

```python
from sqlmodel import Field

class Example(SQLModel, table=True):
    __tablename__ = "example"

    # Integer
    id: int = Field(default=None, primary_key=True)
    count: int = Field(ge=0, description="Non-negative count")

    # String with max length
    name: str = Field(max_length=100, index=True)
    email: str = Field(unique=True, max_length=255)

    # Optional string
    nickname: str | None = Field(default=None, max_length=50)

    # Boolean with default
    is_active: bool = Field(default=True)

    # Float (use Decimal for money!)
    rating: float = Field(ge=0.0, le=5.0)
```

### UUID Primary Keys

```python
from uuid import UUID, uuid4

class Model(SQLModel, table=True):
    __tablename__ = "model"

    # ✅ CORRECT - UUID with factory
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # ❌ WRONG - No default
    id: UUID = Field(primary_key=True)
```

### Decimal for Currency

```python
from decimal import Decimal
from sqlalchemy import Column, Numeric

class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    # ✅ CORRECT - Decimal with precision
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    # ❌ WRONG - Float loses precision
    amount: float = Field()
```

### Foreign Keys

```python
from uuid import UUID

class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # ✅ CORRECT - Foreign key to singular table name
    user_id: int = Field(foreign_key="user.id")

    # ❌ WRONG - References plural table name
    user_id: int = Field(foreign_key="users.id")

    # Relationship
    user: "User" = Relationship(back_populates="orders")
```

## Relationships

### One-to-Many

```python
from typing import List
from sqlmodel import Relationship

class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True)

    # ✅ CORRECT - Relationship() with List type hint
    orders: List["Order"] = Relationship(back_populates="user")

    # ❌ WRONG - Old SQLAlchemy relationship()
    # orders = relationship("Order", back_populates="user")

class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")

    # ✅ CORRECT - Relationship() with single type hint
    user: "User" = Relationship(back_populates="orders")
```

### Cascade Delete

```python
from sqlmodel import Relationship

class Parent(SQLModel, table=True):
    __tablename__ = "parents"

    id: int = Field(default=None, primary_key=True)

    # Cascade delete children when parent deleted
    children: List["Child"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class Child(SQLModel, table=True):
    __tablename__ = "children"

    id: int = Field(default=None, primary_key=True)
    parent_id: int = Field(foreign_key="parents.id")

    parent: "Parent" = Relationship(back_populates="children")
```

### Many-to-Many

```python
from sqlmodel import Field, Relationship, SQLModel
from typing import List

# Link table
class StudentCourseLink(SQLModel, table=True):
    __tablename__ = "student_course_link"

    student_id: int = Field(foreign_key="students.id", primary_key=True)
    course_id: int = Field(foreign_key="courses.id", primary_key=True)

class Student(SQLModel, table=True):
    __tablename__ = "students"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)

    courses: List["Course"] = Relationship(
        back_populates="students",
        link_model=StudentCourseLink
    )

class Course(SQLModel, table=True):
    __tablename__ = "courses"

    id: int = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)

    students: List["Student"] = Relationship(
        back_populates="courses",
        link_model=StudentCourseLink
    )
```

## Enums

### PostgreSQL Enum Type

```python
from enum import Enum
from sqlmodel import Field, SQLModel
from sqlalchemy import Column
from sqlalchemy.types import Enum as SQLEnum

class StatusType(str, Enum):
    """Status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: int = Field(default=None, primary_key=True)

    # ✅ CORRECT - Explicit enum name prevents migration conflicts
    status: StatusType = Field(
        sa_column=Column(
            SQLEnum(StatusType, name="task_status_enum"),
            nullable=False,
            server_default="pending"
        )
    )

    # ❌ WRONG - No explicit name causes migration issues
    # status: StatusType = Field(sa_column=Column(SQLEnum(StatusType)))
```

**Critical**: Always provide `name=` parameter to SQLEnum to prevent Alembic conflicts.

## Complex Types

### PostgreSQL ARRAY

```python
from typing import List
from sqlalchemy import Column, String, ARRAY

class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: int = Field(default=None, primary_key=True)

    # ✅ CORRECT - Array with sa_column
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(50)), nullable=False)
    )

    # ❌ WRONG - Native List doesn't map to PostgreSQL ARRAY
    # tags: List[str] = Field(default_factory=list)
```

### PostgreSQL JSONB

```python
from typing import Dict, Any, Optional
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

class Settings(SQLModel, table=True):
    __tablename__ = "settings"

    id: int = Field(default=None, primary_key=True)

    # ✅ CORRECT - JSONB with sa_column
    preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )

    metadata_: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False)
    )
```

Note: Use `metadata_` with `sa_column=Column("metadata", ...)` to avoid Python keyword conflict.

## Timestamps

### Timezone-Aware Timestamps

```python
from datetime import datetime
from sqlalchemy import Column, DateTime, func

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: int = Field(default=None, primary_key=True)

    # ✅ CORRECT - Timezone-aware with server default
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )
    )

    # Updated timestamp
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=func.now()
        )
    )

    # ❌ WRONG - No timezone awareness
    # created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Critical**: Always use `DateTime(timezone=True)` and `server_default=func.now()`.

## Indexes and Constraints

### Indexes

```python
from sqlalchemy import Index

class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str = Field(max_length=50, index=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    # Composite index
    __table_args__ = (
        Index("idx_user_username_created", "username", "created_at"),
    )
```

### Unique Constraints

```python
from sqlalchemy import UniqueConstraint

class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    plan_type: str = Field(max_length=50)
    valid_from: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    # Unique constraint on multiple columns
    __table_args__ = (
        UniqueConstraint("user_id", "plan_type", "valid_from", name="uq_user_plan_period"),
    )
```

## Forbidden Patterns

### ❌ NEVER Use These

```python
# ❌ SQLAlchemy Base
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
class Model(Base):
    ...

# ❌ Confusing BaseModel name
from app.models.base import BaseModel
class Model(BaseModel, table=True):
    ...

# ❌ Old relationship() function
from sqlalchemy.orm import relationship
items = relationship("Item")

# ❌ Column() for simple types
name = Column(String(100))

# ❌ Mutable defaults without factory
tags: List[str] = Field(default=[])  # Bug: shared between instances
metadata: Dict = Field(default={})    # Bug: shared between instances

# ❌ DateTime without timezone
created_at: datetime = Field(sa_column=Column(DateTime()))

# ❌ Enum without explicit name
status: StatusType = Field(sa_column=Column(SQLEnum(StatusType)))
```

### ✅ Use These Instead

```python
# ✅ Direct SQLModel
from sqlmodel import SQLModel, Field, Relationship
class Model(SQLModel, table=True):
    ...

# ✅ Clear BaseSQLModel if needed
from app.models.base_sqlmodel import BaseSQLModel
class Model(BaseSQLModel, table=True):
    ...

# ✅ Relationship() with capital R
items: List["Item"] = Relationship(back_populates="parent")

# ✅ Field() for simple types
name: str = Field(max_length=100)

# ✅ Mutable defaults with factory
tags: List[str] = Field(default_factory=list)
metadata: Dict = Field(default_factory=dict)

# ✅ DateTime with timezone
created_at: datetime = Field(
    sa_column=Column(DateTime(timezone=True), server_default=func.now())
)

# ✅ Enum with explicit name
status: StatusType = Field(
    sa_column=Column(SQLEnum(StatusType, name="status_enum"))
)
```

## Testing Requirements

Every model MUST have corresponding tests in `tests/models/test_<model>.py`:

```python
# tests/models/test_user.py
import pytest
from sqlmodel import Session, create_engine, SQLModel
from app.models.user import User

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_user_creation(session):
    """Test creating a user."""
    user = User(email="test@example.com", name="Test User")
    session.add(user)
    session.commit()

    assert user.id is not None
    assert user.email == "test@example.com"

def test_user_email_unique(session):
    """Test email uniqueness constraint."""
    user1 = User(email="test@example.com")
    session.add(user1)
    session.commit()

    user2 = User(email="test@example.com")
    session.add(user2)

    with pytest.raises(Exception):  # IntegrityError
        session.commit()
```

## Performance Guidelines

### Query Optimization

```python
from sqlmodel import select

# ✅ Eager load relationships to avoid N+1
statement = select(User).options(
    selectinload(User.orders)
)
users = session.exec(statement).all()

# ✅ Use pagination for large datasets
statement = select(User).offset(0).limit(100)
users = session.exec(statement).all()

# ✅ Index frequently queried fields
email: str = Field(unique=True, index=True)
created_at: datetime = Field(..., index=True)
```

### Migration Best Practices

1. **Always import sqlmodel** in migration files:
```python
import sqlmodel
from sqlalchemy.dialects import postgresql
```

2. **Use batch operations** for data migrations:
```python
op.execute("""
    UPDATE users SET status = 'active'
    WHERE created_at > now() - interval '30 days'
""")
```

3. **Create indexes concurrently** in production:
```python
op.create_index(
    'idx_user_email',
    'user',
    ['email'],
    unique=True,
    postgresql_concurrently=True
)
```

## Summary Checklist

Before committing a new model, verify:

- ✅ Inherits from `SQLModel, table=True` (NOT Base, NOT BaseModel)
- ✅ Has `__tablename__` explicitly set
- ✅ Has docstring documenting purpose and fields
- ✅ Uses `Field()` for all columns
- ✅ Uses `Relationship()` for relationships
- ✅ Has proper type hints
- ✅ Uses `DateTime(timezone=True)` for timestamps
- ✅ Uses `Decimal` for currency amounts
- ✅ Uses `sa_column=Column()` for complex types (ARRAY, JSONB, Enum)
- ✅ Provides `name=` for SQLEnum types
- ✅ Uses `default_factory` for mutable defaults
- ✅ Has corresponding test file
- ✅ Has Alembic migration
- ✅ Migration imports `sqlmodel`
- ✅ Follows naming conventions (BaseSQLModel if intermediate class needed)

## References

- [SQLModel Official Docs](https://sqlmodel.tiangolo.com/)
- [SQLModel GitHub](https://github.com/tiangolo/sqlmodel)
- ADR-014: SQLModel Exclusive ORM
- SQLMODEL_REVIEW_CHECKLIST.md
