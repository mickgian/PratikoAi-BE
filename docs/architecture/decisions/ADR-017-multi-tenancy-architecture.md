# ADR-017: Multi-Tenancy Architecture with studio_id and Row-Level Security

**Status:** PROPOSED
**Date:** 2025-12-15
**Decision Makers:** PratikoAI Architect (Egidio), Michele Giannone (Stakeholder)
**Context Review:** PratikoAI 2.0 - Professional Engagement Platform

---

## Context

### Current State (PratikoAI 1.0)

PratikoAI 1.0 is a **single-user system** where each user has their own data, isolated by `user_id` foreign keys:

```python
# Current pattern - single user isolation
class ChatHistory(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id")

class UserDocument(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id")
```

This pattern works for individual users but does NOT support:
- **Studi professionali** (professional firms) with multiple operators
- **Client database** per studio (100 clients per studio)
- **Shared resources** within a studio (clients, communications, guides)
- **Future B2B model** (studio-level subscriptions)

### PratikoAI 2.0 Requirements

The new professional engagement platform requires:

1. **Studio → Client hierarchy**: Each studio manages up to 100 clients
2. **Multi-operator support**: Multiple users per studio (future)
3. **Data isolation**: Studio A cannot access Studio B's clients
4. **GDPR compliance**: Clear data ownership and deletion paths
5. **Client-aware features**: Matching, communications, calculations per client

### The Problem

We need to decide:
1. **Schema approach**: How to model studio-client-user relationships
2. **Isolation strategy**: How to ensure data isolation between studios
3. **Migration path**: How to transition existing users to studios
4. **Performance impact**: How to maintain query performance

---

## Decision

### ADOPT: Row-Level Isolation with `studio_id` Foreign Key

We will implement multi-tenancy using a **row-level isolation pattern** with `studio_id` as the tenant discriminator, with PostgreSQL RLS (Row-Level Security) as an optional future enhancement.

### Schema Design

```python
# New: Studio model (tenant root)
class Studio(SQLModel, table=True):
    __tablename__ = "studio"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=200)
    slug: str = Field(unique=True, max_length=50)  # URL-safe identifier
    settings: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    max_clients: int = Field(default=100)
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now()))

# Modified: User belongs to Studio
class User(SQLModel, table=True):
    __tablename__ = "user"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    studio_id: UUID | None = Field(foreign_key="studio.id", index=True)  # Nullable for migration
    # ... existing fields ...

# New: Client belongs to Studio
class Client(SQLModel, table=True):
    __tablename__ = "client"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    studio_id: UUID = Field(foreign_key="studio.id", index=True)  # Required
    codice_fiscale: str = Field(sa_column=Column(EncryptedTaxID))  # Encrypted
    # ... other fields ...
```

### Isolation Implementation

**Phase 1 (MVP): Application-Level Isolation**

```python
# Service layer enforces isolation
class ClientService:
    async def list_clients(self, user: User) -> list[Client]:
        if not user.studio_id:
            raise PermissionDenied("User must belong to a studio")

        return await self.db.exec(
            select(Client).where(Client.studio_id == user.studio_id)
        )

    async def get_client(self, user: User, client_id: UUID) -> Client:
        client = await self.db.get(Client, client_id)
        if client.studio_id != user.studio_id:
            raise PermissionDenied("Access denied")
        return client
```

**Phase 2 (Post-MVP): PostgreSQL RLS**

```sql
-- Enable RLS on client table
ALTER TABLE client ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their studio's clients
CREATE POLICY client_studio_isolation ON client
    FOR ALL
    USING (studio_id = current_setting('app.current_studio_id')::uuid);

-- Set context in middleware
SET LOCAL app.current_studio_id = 'uuid-of-studio';
```

### Migration Path

**Step 1: Create Studio for Each Existing User**

```python
# Migration script
async def migrate_users_to_studios():
    users = await db.exec(select(User).where(User.studio_id == None))

    for user in users:
        studio = Studio(
            name=f"Studio di {user.name or user.email}",
            slug=generate_slug(user.email),
            max_clients=100
        )
        await db.add(studio)
        user.studio_id = studio.id
        await db.commit()
```

**Step 2: Migrate User-Owned Data to Studio**

Tables that need `studio_id` added:
- `chat_history` (already has `user_id`, add `studio_id` for consistency)
- `user_document` → rename to `document`, add `studio_id` and `client_id`
- New tables: `client`, `client_profile`, `communication`, `guide_progress`

---

## Alternatives Considered

### 1. Schema-per-Tenant (REJECTED)

```sql
CREATE SCHEMA studio_abc;
CREATE TABLE studio_abc.clients (...);
```

**Pros:**
- Complete isolation
- Easy to delete entire studio

**Cons:**
- Alembic migration complexity (100+ schemas)
- Connection pooling issues
- Cross-tenant queries impossible
- Not supported by SQLModel/SQLAlchemy patterns

### 2. Database-per-Tenant (REJECTED)

**Pros:**
- Maximum isolation

**Cons:**
- Operational nightmare (100+ databases)
- Backup/restore complexity
- Cross-tenant analytics impossible

### 3. Shared Database with `tenant_id` Column (SELECTED)

**Pros:**
- Simple schema
- Single Alembic migration
- Established pattern (Stripe, Slack use this)
- Easy cross-tenant analytics
- SQLModel compatible

**Cons:**
- Requires explicit filtering (mitigated by RLS)
- Potential for bugs if filter forgotten (mitigated by service layer)

---

## Consequences

### Positive

1. **Simple migration**: One Alembic migration adds `studio_id` column
2. **Established pattern**: Well-documented approach (Stripe, Slack)
3. **SQLModel compatible**: Works with existing ORM patterns
4. **Flexible**: Can enable RLS later for defense-in-depth
5. **Analytics friendly**: Cross-studio reporting possible
6. **GDPR compliance**: Clear data ownership for deletion

### Negative

1. **Developer discipline required**: Must always filter by `studio_id`
2. **No automatic isolation**: Unlike schema-per-tenant
3. **Index overhead**: Every query includes `studio_id` in WHERE clause

### Mitigations

1. **Service layer abstraction**: All queries go through services that enforce isolation
2. **Comprehensive tests**: `tests/security/test_tenant_isolation.py` with 95%+ coverage
3. **Code review checklist**: Verify `studio_id` in all client-related queries
4. **Future RLS**: PostgreSQL RLS as defense-in-depth (Phase 2)

---

## Implementation Phases

### Phase 0: Foundation (Week 1-2)

- [ ] Create `Studio` SQLModel
- [ ] Create `Client` SQLModel with `studio_id` FK
- [ ] Create `ClientProfile` SQLModel
- [ ] Alembic migration for new tables
- [ ] Unit tests for models

### Phase 1: Service Layer (Week 3-4)

- [ ] `StudioService` with CRUD operations
- [ ] `ClientService` with isolation enforcement
- [ ] Tenant context middleware (extract `studio_id` from JWT)
- [ ] Integration tests for isolation

### Phase 2: RLS Enhancement (Post-MVP)

- [ ] PostgreSQL RLS policies
- [ ] Middleware to set `app.current_studio_id`
- [ ] Performance benchmarks with/without RLS

---

## Security Considerations

### Data Isolation

| Layer | Mechanism | Status |
|-------|-----------|--------|
| API | Authentication required | EXISTING |
| Service | `studio_id` filter enforced | NEW |
| Database | RLS policies | FUTURE |
| Encryption | PII encrypted at rest | EXISTING |

### GDPR Compliance

1. **Data ownership**: `studio_id` clearly identifies data controller
2. **Deletion**: CASCADE delete from Studio removes all clients
3. **Export**: Export scoped to `studio_id`
4. **Audit**: All client access logged with `studio_id`

---

## Performance Impact

### Index Strategy

```sql
-- Composite indexes for common queries
CREATE INDEX idx_client_studio_active ON client(studio_id, is_active);
CREATE INDEX idx_communication_studio_status ON communication(studio_id, status);
CREATE INDEX idx_client_profile_studio_ateco ON client_profile(studio_id, codice_ateco);
```

### Query Patterns

```python
# Efficient: Uses composite index
SELECT * FROM client WHERE studio_id = ? AND is_active = true;

# Efficient: Partition pruning with RLS
SELECT * FROM client;  -- RLS adds WHERE studio_id = current
```

### Benchmark Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| List clients (100) | <100ms | Single studio query |
| Client search | <200ms | BM25 + vector within studio |
| Cross-studio analytics | <5s | Admin only, no RLS |

---

## References

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Stripe's Multi-Tenant Architecture](https://stripe.com/blog/online-migrations)
- ADR-014: SQLModel Exclusive ORM
- ADR-018: Normative Matching Engine (integrates with client data)
- docs/tasks/PRATIKO_2.0.md - Full task breakdown

---

## Revision History

- 2025-12-15: Initial version - Row-level isolation with studio_id
