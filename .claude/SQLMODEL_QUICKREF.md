# SQLModel Quick Reference Guide

**CRITICAL:** PratikoAI uses **SQLModel ONLY**. SQLAlchemy Base patterns are FORBIDDEN.

---

## Table of Contents
1. [Why SQLModel?](#why-sqlmodel)
2. [Basic Model Definition](#basic-model-definition)
3. [Common Patterns](#common-patterns)
4. [Foreign Keys & Relationships](#foreign-keys--relationships)
5. [Advanced Column Types](#advanced-column-types)
6. [Anti-Patterns (DO NOT USE)](#anti-patterns-do-not-use)
7. [Migration from SQLAlchemy Base](#migration-from-sqlalchemy-base)
8. [Testing SQLModel Models](#testing-sqlmodel-models)

---

## Why SQLModel?

**SQLModel** combines the best of SQLAlchemy and Pydantic:
- **Type safety:** Full Python type hints with IDE autocomplete
- **Data validation:** Pydantic validators on model fields
- **Code reduction:** One class for both database and API schemas
- **Migration complete:** All 46 PratikoAI models now use SQLModel

**Status:** Migration completed November 2025. SQLAlchemy Base is deprecated.

---

## Basic Model Definition

### ✅ CORRECT: SQLModel Pattern

```python
from datetime import UTC, datetime
from sqlmodel import Field, SQLModel

class User(SQLModel, table=True):
    """User model with SQLModel.

    Attributes:
        id: Primary key (auto-increment)
        email: User's unique email address
        name: User's full name
        created_at: Timestamp of user creation
    """

    __tablename__ = "user"

    # Primary key
    id: int = Field(default=None, primary_key=True)

    # Regular columns
    email: str = Field(unique=True, index=True, max_length=255)
    name: str | None = Field(default=None, max_length=255)

    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

**Key Points:**
- Inherit from `SQLModel` with `table=True`
- Use Python 3.10+ union types: `str | None` (not `Optional[str]`)
- Use `Field()` for column configuration
- Use `__tablename__` to specify table name

### ❌ FORBIDDEN: SQLAlchemy Base Pattern

```python
# DO NOT USE THIS - DEPRECATED
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Why Not:**
- No type hints → No IDE autocomplete
- No Pydantic validation
- Verbose column definitions
- Deprecated in PratikoAI codebase

---

## Common Patterns

### BaseModel (Common Fields)

All models inherit from `BaseModel` for `created_at`:

```python
# app/models/base.py
from datetime import UTC, datetime
from sqlmodel import Field, SQLModel

class BaseModel(SQLModel):
    """Base model with common fields."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

**Usage:**
```python
from app.models.base import BaseModel

class FAQ(BaseModel, table=True):
    """FAQ model inheriting created_at from BaseModel."""

    __tablename__ = "faq_entries"

    id: str = Field(primary_key=True, max_length=100)
    question: str = Field(sa_column=Column(Text))
    answer: str = Field(sa_column=Column(Text))
    # created_at inherited from BaseModel
```

### Enums

Use Python `Enum` with SQLModel:

```python
from enum import Enum
from sqlmodel import Field, SQLModel

class UpdateSensitivity(str, Enum):
    """FAQ update sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class FAQ(SQLModel, table=True):
    __tablename__ = "faq_entries"

    id: str = Field(primary_key=True)
    update_sensitivity: UpdateSensitivity = Field(default=UpdateSensitivity.MEDIUM)
```

**Key Points:**
- Inherit from both `str` and `Enum` for database compatibility
- SQLModel handles enum serialization automatically

### UUID Primary Keys

```python
from uuid import uuid4
from sqlmodel import Field, SQLModel

class FAQ(SQLModel, table=True):
    __tablename__ = "faq_entries"

    # UUID primary key with default factory
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        max_length=100
    )
```

### Timestamps with Timezone

```python
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

class FAQ(SQLModel, table=True):
    __tablename__ = "faq_entries"

    id: str = Field(primary_key=True)

    # Timezone-aware timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True))
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True))
    )
```

---

## Foreign Keys & Relationships

### ✅ CORRECT: SQLModel Foreign Keys

```python
from sqlmodel import Field, Relationship, SQLModel

class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)

    # Relationship to sessions
    sessions: list["Session"] = Relationship(back_populates="user")

class Session(SQLModel, table=True):
    __tablename__ = "session"

    id: int = Field(default=None, primary_key=True)

    # Foreign key to user
    user_id: int = Field(foreign_key="user.id", index=True)

    # Relationship to user
    user: "User" = Relationship(back_populates="sessions")
```

**Key Points:**
- Use `Field(foreign_key="table.column")` for FK
- Use `Relationship(back_populates="field_name")` for navigation
- Use forward references with strings: `"Session"` for type hints
- Always index foreign key columns: `index=True`

### TYPE_CHECKING Pattern

Avoid circular imports with `TYPE_CHECKING`:

```python
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.session import Session

class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int = Field(default=None, primary_key=True)
    sessions: list["Session"] = Relationship(back_populates="user")
```

**Why:**
- Prevents circular imports at runtime
- Provides type hints for IDE autocomplete
- Standard pattern in PratikoAI codebase

---

## Advanced Column Types

### Text (Large Strings)

```python
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

class FAQ(SQLModel, table=True):
    __tablename__ = "faq_entries"

    id: str = Field(primary_key=True)

    # Use sa_column for Text type
    question: str = Field(sa_column=Column(Text))
    answer: str = Field(sa_column=Column(Text))
```

### JSONB (Structured Data)

```python
from typing import Any
from sqlalchemy import Column
from sqlmodel import JSON, Field, SQLModel

class FAQ(SQLModel, table=True):
    __tablename__ = "faq_entries"

    id: str = Field(primary_key=True)

    # JSONB column
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
```

### ARRAY (PostgreSQL Arrays)

```python
from sqlalchemy import String
from sqlmodel import ARRAY, Column, Field, SQLModel

class FAQ(SQLModel, table=True):
    __tablename__ = "faq_entries"

    id: str = Field(primary_key=True)

    # Array of strings
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String))
    )
```

### Vector (pgvector)

```python
from pgvector.sqlalchemy import Vector
from sqlmodel import Field, SQLModel

class KnowledgeChunk(SQLModel, table=True):
    __tablename__ = "knowledge_chunks"

    id: int = Field(default=None, primary_key=True)
    text: str = Field(sa_column=Column(Text))

    # 1536-dimensional embedding vector
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1536))
    )
```

### Exclude Fields from Schema

```python
from sqlmodel import Field, SQLModel

class FAQ(SQLModel, table=True):
    __tablename__ = "faq_entries"

    id: str = Field(primary_key=True)
    question: str

    # Computed field, not stored in database
    similarity_score: float | None = Field(
        default=None,
        exclude=True  # Exclude from table and API schemas
    )
```

---

## Anti-Patterns (DO NOT USE)

### ❌ 1. SQLAlchemy Base

```python
# FORBIDDEN - Use SQLModel instead
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class User(Base):
    __tablename__ = "user"
```

### ❌ 2. Column() for Simple Types

```python
# FORBIDDEN - Use Field() instead
from sqlalchemy import Column, Integer, String
from sqlmodel import SQLModel

class User(SQLModel, table=True):
    id = Column(Integer, primary_key=True)  # DON'T DO THIS
    email = Column(String(255))             # DON'T DO THIS
```

**Use Field() instead:**
```python
# CORRECT
id: int = Field(default=None, primary_key=True)
email: str = Field(max_length=255)
```

### ❌ 3. Optional[] Instead of Union

```python
# OUTDATED - Python 3.10+ style preferred
from typing import Optional

class User(SQLModel, table=True):
    name: Optional[str] = None  # Old style
```

**Use union syntax:**
```python
# CORRECT
class User(SQLModel, table=True):
    name: str | None = None  # Modern Python 3.10+ style
```

### ❌ 4. Missing table=True

```python
# INCORRECT - Not a database table
class User(SQLModel):
    id: int
```

**Always specify table=True:**
```python
# CORRECT
class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
```

### ❌ 5. Importing from Wrong Module

```python
# FORBIDDEN - Don't use Base
from app.models.database import Base

# FORBIDDEN - Don't use Column for simple types
from sqlalchemy import Column, Integer, String
```

**Correct imports:**
```python
# CORRECT
from sqlmodel import Field, Relationship, SQLModel
from app.models.base import BaseModel  # For created_at
```

---

## Migration from SQLAlchemy Base

### Before (SQLAlchemy Base)

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.database import Base
import datetime

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sessions = relationship("Session", back_populates="user")

class Session(Base):
    __tablename__ = "session"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    user = relationship("User", back_populates="sessions")
```

### After (SQLModel)

```python
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.session import Session

class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    sessions: list["Session"] = Relationship(back_populates="user")

class Session(SQLModel, table=True):
    __tablename__ = "session"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    user: "User" = Relationship(back_populates="sessions")
```

### Migration Checklist

- [ ] Replace `Base` with `SQLModel, table=True`
- [ ] Convert `Column()` to `Field()` for simple types
- [ ] Add type hints to all fields
- [ ] Use `str | None` instead of `Optional[str]`
- [ ] Replace `relationship()` with `Relationship()`
- [ ] Use `foreign_key=` parameter in `Field()`
- [ ] Add `TYPE_CHECKING` for forward references
- [ ] Replace `datetime.utcnow` with `datetime.now(UTC)`
- [ ] Test model CRUD operations
- [ ] Update related tests

---

## Testing SQLModel Models

### Basic CRUD Tests

```python
import pytest
from sqlmodel import Session, create_engine, select
from app.models.user import User

@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

def test_create_user(db_session: Session):
    """Test creating a user."""
    user = User(email="test@example.com", name="Test User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"

def test_query_user(db_session: Session):
    """Test querying a user."""
    user = User(email="query@example.com", name="Query User")
    db_session.add(user)
    db_session.commit()

    # Use select() for type-safe queries
    statement = select(User).where(User.email == "query@example.com")
    result = db_session.exec(statement).first()

    assert result is not None
    assert result.name == "Query User"
```

### Relationship Tests

```python
def test_user_sessions_relationship(db_session: Session):
    """Test user-session relationship."""
    user = User(email="rel@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    session1 = Session(user_id=user.id, title="Session 1")
    session2 = Session(user_id=user.id, title="Session 2")
    db_session.add_all([session1, session2])
    db_session.commit()

    # Refresh to load relationships
    db_session.refresh(user)

    assert len(user.sessions) == 2
    assert session1.user.email == "rel@example.com"
```

### Validation Tests

```python
import pytest
from pydantic import ValidationError

def test_user_validation():
    """Test Pydantic validation on SQLModel."""
    # Valid user
    user = User(email="valid@example.com")
    assert user.email == "valid@example.com"

    # Invalid email (if validator added)
    with pytest.raises(ValidationError):
        User(email="not-an-email")
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Forgetting table=True

**Problem:**
```python
class User(SQLModel):  # Missing table=True
    id: int
```

**Solution:**
```python
class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
```

### Pitfall 2: Circular Imports

**Problem:**
```python
# user.py
from app.models.session import Session  # Circular import!

class User(SQLModel, table=True):
    sessions: list[Session] = Relationship(...)
```

**Solution:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.session import Session

class User(SQLModel, table=True):
    sessions: list["Session"] = Relationship(...)  # String forward reference
```

### Pitfall 3: Missing sa_column for Complex Types

**Problem:**
```python
class FAQ(SQLModel, table=True):
    question: str  # Default VARCHAR(255), might be too short
```

**Solution:**
```python
from sqlalchemy import Column, Text

class FAQ(SQLModel, table=True):
    question: str = Field(sa_column=Column(Text))
```

### Pitfall 4: Timezone-Naive Datetimes

**Problem:**
```python
from datetime import datetime

class User(SQLModel, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Naive!
```

**Solution:**
```python
from datetime import UTC, datetime

class User(SQLModel, table=True):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

---

## Quick Command Reference

### Create New Model
```bash
# 1. Create model file
touch app/models/my_model.py

# 2. Define model with SQLModel
# (See examples above)

# 3. Create Alembic migration
alembic revision -m "add_my_model_table"

# 4. Write migration SQL
# Edit alembic/versions/XXXX_add_my_model_table.py

# 5. Apply migration
alembic upgrade head

# 6. Write tests
touch tests/models/test_my_model.py
pytest tests/models/test_my_model.py
```

### Query Patterns

```python
from sqlmodel import Session, select

# Select all
statement = select(User)
users = session.exec(statement).all()

# Filter
statement = select(User).where(User.email == "test@example.com")
user = session.exec(statement).first()

# Join (with relationship)
statement = select(User).where(User.id == 1)
user = session.exec(statement).first()
# Relationships auto-loaded
sessions = user.sessions

# Count
statement = select(User).where(User.provider == "google")
count = session.exec(statement).count()
```

---

## Resources

- **SQLModel Docs:** https://sqlmodel.tiangolo.com/
- **Pydantic V2 Docs:** https://docs.pydantic.dev/latest/
- **PratikoAI BaseModel:** `/Users/micky/PycharmProjects/PratikoAi-BE/app/models/base.py`
- **Example Models:** `/Users/micky/PycharmProjects/PratikoAi-BE/app/models/user.py`
- **Migration History:** 46 models migrated November 2025

---

## Summary

**ALWAYS:**
- Use `SQLModel` with `table=True`
- Use `Field()` for column configuration
- Use type hints: `str`, `int`, `str | None`
- Use `Relationship()` for foreign keys
- Use `TYPE_CHECKING` for circular imports
- Test models with pytest

**NEVER:**
- Use SQLAlchemy `Base`
- Use `Column()` for simple types
- Use `Optional[]` (use `str | None`)
- Forget `table=True`
- Import circular dependencies directly

---

**Last Updated:** 2025-11-28
**Migration Status:** Complete (46/46 models)
**Enforcement:** Pre-commit hooks prevent Base usage
