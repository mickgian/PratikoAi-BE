# CLAUDE.md - PratikoAI Code Guidelines

This file provides guidelines for Claude Code when working on the PratikoAI codebase.

---

## Project Overview

This is a monorepo with a Next.js frontend (TypeScript) and a Python/FastAPI backend. Key technologies: SQLModel ORM, Flagsmith feature flags, Caddy reverse proxy, Docker Compose for deployment, GitHub Actions CI/CD.

---

## CRITICAL RULES (Never Violate)

1. **NO TODOs or incomplete code** - Always complete implementations. No "will implement later" patterns.
2. **Use @mario for requirements** - When task affects 3+ files, DB schema, or API changes
3. **Use @egidio for architecture** - For any architectural decision. Has veto power.
4. **SQLModel ONLY** - No SQLAlchemy Base patterns (ADR-014)
5. **TDD mandatory** - Write tests FIRST, then implement (ADR-013)
6. **Italian for user-facing text** - All frontend UI text must be in Italian
7. **Pre-commit hooks must pass** - Ruff, MyPy, pytest, alembic check

---

## Environment

**Status:** DEVELOPMENT + QA

- **Development:** Local Docker Compose (`docker-compose.yml`)
- **QA:** Hetzner CX33, auto-deploys on merge to `develop` (see `docs/deployment/DEPLOYMENT_RUNBOOK.md`)
- **Production:** Hetzner CX43, manual approval on merge to `master` (not yet provisioned)

---

## Project Paths

| Project | Path |
|---------|------|
| **Backend** | `/Users/micky/PycharmProjects/PratikoAi-BE` (repo root) |
| **Frontend** | `/Users/micky/PycharmProjects/PratikoAi-BE/web` |

---

## Subagent Quick Reference

| Agent | When to Use | Tools |
|-------|-------------|-------|
| **@mario** | 3+ files, DB schema, API changes, unclear requirements | Read, Grep, Glob, AskUserQuestion |
| **@egidio** | Architecture decisions, ADRs, veto situations (HAS VETO POWER) | Read, Grep, Glob, WebFetch |
| **@primo** | Database design, migrations, pgvector optimization | Read, Write, Edit, Bash, Grep, Glob |
| **@ezio** | Backend implementation (FastAPI, LangGraph, PostgreSQL) | Read, Write, Edit, Bash, Grep, Glob |
| **@livia** | Frontend implementation (Next.js, React, Tailwind) | Read, Write, Edit, Bash, Grep, Glob |
| **@clelia** | Test generation, coverage improvement (target: 69.5%) | Read, Write, Edit, Bash, Grep, Glob |
| **@severino** | Security audits, GDPR compliance | Read, Bash, Grep, Glob, WebFetch |
| **@valerio** | Performance optimization, caching, profiling | Read, Bash, Grep, Glob, WebFetch |
| **@silvano** | DevOps, CI/CD, PR creation, GitHub integration | Read, Bash, Grep, Glob, WebFetch |
| **@tiziano** | Debugging, error investigation, root cause analysis | Read, Write, Edit, Bash, Grep, Glob |
| **@ottavio** | Sprint planning, task coordination, progress tracking | Read, Grep, Glob, WebFetch |

### Development Workflow

```
User Request
    |
    v
@mario (Requirements + Impact Analysis)
    |
    v
@egidio (Architecture Review - Can VETO)
    |
    v
@primo/@ezio/@livia (Implementation with TDD)
    |
    v
@clelia (Test Validation)
    |
    v
@silvano (PR Creation)
```

---

## Feature Implementation

When implementing new backend features, always verify the corresponding frontend is updated and accessible before marking the task complete.

---

## Before Implementing Non-Trivial Tasks

**ALWAYS follow this workflow for tasks affecting 3+ files:**

1. **@mario** - Gather requirements, analyze codebase impact, identify breaking changes
2. **@egidio** - Review architecture, check ADR compliance, approve or veto
3. **Document** - Use the mandatory task template
4. **Implement** - Follow TDD (RED-GREEN-REFACTOR)

---

## Mandatory Task Template

When creating tasks, use @egidio's template format (full template in `.claude/agents/architect.md`):

```markdown
### DEV-XXX: [Task Title]

**Priority:** [CRITICAL|HIGH|MEDIUM|LOW] | **Effort:** [Xh] | **Status:** NOT STARTED

**Problem:** [1-2 sentences - why this task is needed]

**Solution:** [1-2 sentences - the approach]

**Agent Assignment:** @[Primary] (primary), @[Secondary] (tests/review)

**Dependencies:**
- **Blocking:** [Tasks that must complete first, or "None"]
- **Unlocks:** [Tasks enabled by this one]

**Change Classification:** [ADDITIVE|MODIFYING|RESTRUCTURING]

**File:** `[path/to/file.py]`

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All integrations complete and functional
- [ ] No "will implement later" patterns

**Testing Requirements:**
- [ ] TDD: Write tests FIRST
- [ ] Minimum 3 tests (happy + error + edge)
- [ ] Coverage target: 70%+ for new code

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation
- [ ] All existing tests still pass
- [ ] Pre-commit hooks pass
```

---

## Code Size Guidelines

### Backend (Python/FastAPI/LangGraph)

| Component | Max Lines | Guidance |
|-----------|-----------|----------|
| Functions | 50 | Extract helpers if larger |
| Classes | 200 | Split into focused services |
| Files | 400 | Create submodules |
| LangGraph nodes | 100 | Delegate to orchestrators |
| API route handlers | 30 | Delegate to services |

### Frontend (Next.js/React/TypeScript)

| Component | Max Lines | Guidance |
|-----------|-----------|----------|
| Page files | 100 | Delegate to components |
| React components | 150 | Extract sub-components |
| Custom hooks | 50 | Single concern |
| API clients | 100 | One resource per file |

---

## Architecture Pattern: Functional Core, Imperative Shell

### Backend Structure

```
app/
├── api/v1/          # Thin route handlers (<30 lines each)
├── services/        # Business logic (<200 lines each)
├── orchestrators/   # Complex workflows (<300 lines each)
├── core/langgraph/
│   └── nodes/       # Thin wrappers (<100 lines each)
├── models/          # SQLModel definitions (<100 lines each)
└── schemas/         # Pydantic schemas (<50 lines each)
```

### Frontend Structure

```
src/
├── app/             # Next.js pages (<100 lines each)
├── components/
│   ├── ui/          # Radix primitives (<100 lines each)
│   └── features/    # Feature components (<150 lines each)
├── lib/
│   ├── api/         # API clients (<100 lines each)
│   └── hooks/       # Custom hooks (<50 lines each)
├── contexts/        # Context providers (<100 lines each)
└── types/           # TypeScript types (<50 lines each)
```

### Structure Rules

**Backend:**
- **API routes:** HTTP handling only, delegate to services
- **Services:** Single responsibility, inject via FastAPI `Depends()`
- **Orchestrators:** Coordinate multiple services for complex workflows
- **LangGraph nodes:** Thin wrappers that call orchestrators/services
- **Models:** Data definitions only, no business logic

**Frontend:**
- **Pages:** Route handling only, import feature components
- **Components:** Single responsibility, props-only dependencies
- **Hooks:** One concern per hook, return typed values
- **Context:** useReducer pattern for complex state

---

## Deployment Rules

### Expand-Contract Pattern (Mandatory for Breaking API Changes)

All API changes affecting the frontend MUST follow the Expand-Contract pattern:

```
EXPAND:   Backend adds NEW endpoint alongside old one (both coexist)
MIGRATE:  Frontend updates to call new endpoint
CONTRACT: Backend removes old endpoint (after all clients migrated)
```

- **Backend ALWAYS deploys before frontend** (enforced in CI/CD)
- Never introduce a breaking change in a single deploy
- Already using `/api/v1/`; when breaking changes are needed, create `/api/v2/` alongside

### Deployment Ordering
1. Backend deploys first (db, redis, app, flagsmith)
2. Wait for backend health check
3. Frontend deploys second (frontend, caddy)
4. Smoke tests run against both

---

## Infrastructure

This project uses a Hetzner QA server for deployment — NOT Vercel, NOT Netlify. The QA deploy pipeline uses Docker Compose via SSH/SCP to the Hetzner server. Never suggest or attempt Vercel-based deployment.

---

## Git Workflow

When asked to commit and push, do it immediately without entering plan mode or creating plan files first. The user expects direct action for git operations.

---

## Working Style

When the user asks to update documentation or task files, do NOT start implementing actual code changes or explore the codebase extensively. Stick to the documentation/planning scope unless explicitly asked to implement.

---

## Figma / Design References

Figma references use Figma Make MCP. Component names may differ from expected screen names (e.g., ProceduraInterattivaPage vs ProceduraPage). When a Figma resource isn't found by expected name, search by partial match before asking the user.

---

## Common Commands

### Backend

```bash
# Testing
uv run pytest                           # Run all tests
uv run pytest tests/path/ -v            # Run specific tests
uv run pytest --cov=app                 # With coverage

# Database
docker-compose up -d db redis           # Start services
alembic upgrade head                    # Run migrations
alembic revision --autogenerate -m "description"  # Generate migration

# Code quality
ruff check . --fix                      # Lint and fix
ruff format .                           # Format code
./scripts/check_code.sh                 # Run all checks
```

### Frontend

```bash
# Development
npm run dev                             # Start dev server (Turbopack)
npm run build                           # Production build

# Testing
npm run test                            # Run Jest tests
npm run test:coverage                   # With coverage
npm run test:e2e                        # Playwright E2E tests

# Code quality
npm run lint                            # ESLint
```

---

## Testing Requirements (ADR-013)

### TDD Workflow (RED-GREEN-REFACTOR)

1. **RED:** Write failing test FIRST
2. **GREEN:** Write minimal code to pass
3. **REFACTOR:** Improve while tests pass

### Coverage Thresholds

| Scope | Threshold |
|-------|-----------|
| Global (legacy) | 30% |
| New code | 70% |
| Target | 69.5% |

### Test Conventions

- Co-located: `Component.tsx` + `Component.test.tsx`
- Or: `__tests__/` directory
- Minimum 3 tests per feature: happy path + error + edge case

---

## ADR Quick Reference

### Infrastructure (ADR-001 to ADR-006)

| ADR | Decision | Key Rule |
|-----|----------|----------|
| **001** | FastAPI over Flask | Native async/await, 3x faster |
| **002** | Hybrid Search (50% FTS + 35% Vector + 15% Recency) | 87% accuracy target |
| **003** | pgvector over Pinecone | $2,400/year savings, GDPR compliant |
| **004** | LangGraph for RAG | 134-step pipeline with checkpointing |
| **005** | Pydantic V2 | 5-50x faster validation |
| **006** | Hetzner over AWS | $10,000/year savings, EU hosting |

### Quality & Testing (ADR-012 to ADR-016)

| ADR | Decision | Key Rule |
|-----|----------|----------|
| **012** | Pre-commit test enforcement | Test file must exist, co-modify tests |
| **013** | TDD mandatory | RED-GREEN-REFACTOR for all features |
| **014** | SQLModel exclusive | NO SQLAlchemy Base patterns |
| **015** | Chat history in PostgreSQL | Server-side storage, NOT IndexedDB-only |
| **016** | E2E RSS testing | Real LLM calls in CI, ~$360/year |

### Frontend (ADR-007 to ADR-009)

| ADR | Decision | Key Rule |
|-----|----------|----------|
| **007** | Next.js 15 App Router | NOT Pages Router, Turbopack enabled |
| **008** | Context API | NO Redux/Zustand |
| **009** | Radix UI | NO Material-UI, headless + Tailwind |

### Domain Architecture (ADR-017 to ADR-027)

| ADR | Decision | Key Rule |
|-----|----------|----------|
| **017** | Multi-tenancy with studio_id | Row-level isolation, Docker Compose only |
| **018** | Normative matching engine | Italian regulatory document matching |
| **019** | Communication generation | Outreach features |
| **020** | Suggested actions | Template-based, YAML-driven, <50ms |
| **021** | Interactive questions | User engagement, follow-up suggestions |
| **022** | LLM document identification | AI-powered document type detection |
| **023** | Tiered document ingestion | Priority-based document processing |
| **024** | Workflow automation | Automated business workflows |
| **025** | LLM model inventory & tiering | BASIC/PREMIUM/LOCAL model strategy |
| **026** | Exchange rate service | EUR cost calculations for LLM usage |
| **027** | Usage-based billing | YAML config, rolling windows, 60% margin |

### Infrastructure & Delivery (ADR-028 to ADR-035)

| ADR | Decision | Key Rule |
|-----|----------|----------|
| **028** | Deployment pipeline | CI/CD automation |
| **029** | Frontend dockerization | Container-based frontend |
| **030** | ML model versioning | Model version management |
| **031** | External runtime config | Runtime configuration |
| **032** | Automated benchmarking | Performance benchmarks |
| **033** | Redis security hardening | Redis security |
| **034** | Hybrid email sending | Plan-gated custom SMTP |
| **035** | Notification-only proactive delivery | **No in-chat suggestions; async matching → notifications only** |

**Full ADRs:** `docs/architecture/decisions/`

---

## Common Patterns

### Backend: API Route Handler

```python
# app/api/v1/example.py - <30 lines
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import get_db
from app.services.example_service import example_service

router = APIRouter()

@router.post("/endpoint")
async def api_endpoint(
    request: ExampleRequest,
    db: AsyncSession = Depends(get_db),
) -> ExampleResponse:
    result = await example_service.process(request, db)
    return ExampleResponse(**result)
```

### Backend: Service Layer

```python
# app/services/example_service.py - <200 lines
from app.core.logging import logger

class ExampleService:
    @staticmethod
    async def process(request: ExampleRequest, db: AsyncSession) -> dict:
        logger.info("processing_request", request_id=request.id)
        try:
            # Business logic here
            return {"status": "success"}
        except Exception as e:
            logger.error("processing_error", error=str(e))
            raise

example_service = ExampleService()
```

### Backend: SQLModel

```python
# app/models/example.py - SQLModel ONLY
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

class Example(SQLModel, table=True):
    __tablename__ = "example"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100, index=True)
```

### Frontend: Component

```tsx
// src/components/features/Example.tsx - <150 lines
'use client'

interface ExampleProps {
  title: string
  onAction: () => void
}

export function Example({ title, onAction }: ExampleProps) {
  return (
    <div>
      <ExampleHeader title={title} />
      <ExampleContent />
      <ExampleActions onAction={onAction} />
    </div>
  )
}
```

### Frontend: Custom Hook

```tsx
// src/lib/hooks/useExample.ts - <50 lines
import { useState, useCallback } from 'react'

export function useExample() {
  const [data, setData] = useState(null)

  const fetch = useCallback(async () => {
    const result = await apiClient.getExample()
    setData(result)
  }, [])

  return { data, fetch }
}
```

---

## Code Conventions

- **Avoid hardcoding values** that should be dynamic or configurable - always ask for clarification if the intended behavior is ambiguous.
- **LLM model configurations:** Prefer environment variables or config files over hardcoded model names.

---

## Logging Standards

All errors MUST be logged with structured context:

```python
logger.error(
    "operation_failed",
    user_id=user.id,
    operation="client_lookup",
    resource_id=client_id,
    error_type=type(e).__name__,
    error_message=str(e),
)
```

---

## Edge Cases to Address

Every task should consider these categories:

1. **Nulls/Empty:** Null fields, empty strings, missing optional values
2. **Boundaries:** Limits, pagination (page 0, beyond max)
3. **Concurrency:** Race conditions, advisory locks
4. **Validation:** Invalid formats, special characters
5. **Soft Delete:** Deleted item queries, reactivation
6. **Tenant Isolation:** Wrong tenant, null tenant, cross-tenant
7. **Error Recovery:** Partial failures, retries, graceful degradation

---

## When to Extract

- Function >50 lines -> Extract helper functions
- Class >200 lines -> Split into multiple services
- Component >150 lines -> Extract sub-components
- Logic >20 lines in JSX -> Extract to hook or utility

---

## References

- **Full task template:** `.claude/agents/architect.md`
- **ADRs:** `docs/architecture/decisions/`
- **SQLModel standards:** `docs/architecture/SQLMODEL_STANDARDS.md`
- **AI architect knowledge base:** `docs/architecture/AI_ARCHITECT_KNOWLEDGE_BASE.md`
- **Subagent configs:** `.claude/agents/`
