# PratikoAI 2.0 - Professional Engagement Platform

**Last Updated:** 2026-02-26
**Status:** Active Development
**Task ID Range:** DEV-300 to DEV-449
**Timeline:** 10-12 weeks (~148 tasks, accelerated with Claude Code)
**Target:** MVP Launch

---

## Overview

PratikoAI 2.0 is a major evolution from a Q&A assistant to a **professional engagement platform** for Italian accountants (commercialisti), labor consultants (consulenti del lavoro), and tax lawyers (avvocati tributaristi).

**Current Architecture:** See `docs/DATABASE_ARCHITECTURE.md` for detailed documentation of the production system.

**Related Documents:**
- `docs/tasks/ARCHITECTURE_ROADMAP.md` - Backend development roadmap (v1.0)
- `docs/architecture/decisions/` - Architectural Decision Records

---

## Key Features

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| FR-001 | Procedure Interattive | Step-by-step workflows with `/procedura` consultation + `@client` tracking | HIGH |
| FR-002 | Studio Client Database | Import and manage up to 100 clients per studio | CRITICAL |
| FR-003 | Automatic Normative Matching | Match clients to regulations automatically | CRITICAL |
| FR-004 | Proactive Suggestions & Communications | AI-generated messages with approval workflow | HIGH |
| FR-005 | ROI Dashboard & Analytics | Track value generated for the professional | MEDIUM |
| FR-006 | Proactive Deadline System | Alert professionals about upcoming deadlines | MEDIUM |
| FR-007 | Fiscal Calculations | IRPEF, IVA, INPS, IMU with client context | HIGH |
| FR-008 | Document Enhancement | Extended document parsing (Bilanci, CU) | MEDIUM |
| FR-009 | Hybrid Email Sending | Plan-gated custom SMTP: Base uses PratikoAI, Pro/Premium can use own email | HIGH |

---

## Development Standards

**All tasks in this roadmap must follow these requirements:**

### Test-Driven Development (TDD)
- **Write tests FIRST, then implement features**
- Follow the Red-Green-Refactor cycle:
  1. RED: Write failing test
  2. GREEN: Write minimal code to pass test
  3. BLUE: Refactor while keeping tests green

### Code Coverage Requirements
- **Overall coverage:** >= 69.5% (configured in `pyproject.toml`)
- **New modules:** >= 80%
- **Security-critical:** >= 95%
- **GDPR compliance:** >= 90%

### Code Quality & Style
- **Linting:** All code must pass Ruff linter checks
- **Formatting:** Use Ruff formatter
- **Type Hints:** Add type hints to all new functions
- **Pre-commit Hooks:** All checks run automatically before commits

### Logging Standards (MANDATORY)
- **All errors MUST be logged** for Docker log visibility
- **Library:** Use `structlog` with JSON format
- **Log Levels:**
  - `ERROR`: Exceptions, failures, invalid operations
  - `WARNING`: Recoverable issues, degraded performance
  - `INFO`: Important business events (auditing)
  - `DEBUG`: Development/troubleshooting details
- **Required Context Fields:**
  - `user_id`: Current user identifier
  - `studio_id`: Multi-tenant isolation context
  - `operation`: What was being attempted
  - `resource_id`: Entity being accessed (client_id, document_id, etc.)
  - `error_type`: Exception class name
  - `error_message`: Human-readable description

**Example Pattern:**
```python
import structlog
logger = structlog.get_logger(__name__)

try:
    result = await service.process(data)
except NotFoundException as e:
    logger.error(
        "resource_not_found",
        user_id=current_user.id,
        studio_id=current_user.studio_id,
        operation="client_lookup",
        client_id=client_id,
        error_type=type(e).__name__,
        error_message=str(e),
    )
    raise HTTPException(status_code=404, detail="Cliente non trovato")
```

### Testing File Conventions

```
tests/
├── models/test_{model_name}.py          # Unit tests for models
├── services/test_{service_name}.py      # Unit tests for services
├── api/test_{router_name}_api.py        # Integration tests for APIs
├── e2e/test_pratikoai_2_0_flow.py       # E2E user journey tests
├── security/test_tenant_isolation.py    # Security regression tests
├── langgraph/test_{node_name}.py        # LangGraph node tests
└── performance/test_{feature}_perf.py   # Performance benchmarks
```

---

## Agent Assignments Summary

| Agent | Role | Primary Tasks | Support Tasks |
|-------|------|---------------|---------------|
| **@Ezio** | Backend Developer | 35 tasks | 10 tasks |
| **@Primo** | Database Designer | 12 tasks | 8 tasks |
| **@Clelia** | Test Generation | 15 tasks | 45 tasks (all features) |
| **@Severino** | Security Audit | 8 tasks | 12 tasks |
| **@Livia** | Frontend Expert | 6 tasks | 4 tasks |
| **@Mario** | Business Analyst | 4 tasks | 6 tasks |

---

## Architecture Decisions Required

| ADR | Title | Status | Description |
|-----|-------|--------|-------------|
| ADR-017 | Multi-Tenancy Architecture | PROPOSED | Row-level with `studio_id` + PostgreSQL RLS |
| ADR-018 | Normative Matching Engine | PROPOSED | Hybrid: LangGraph node + background service |
| ADR-019 | Communication Generation | PROPOSED | LangGraph tool following existing patterns |
| ADR-020 | Suggested Actions | SUPERSEDED | Feature removed per user feedback (see Deprecated Features) |
| ADR-024 | Workflow Automation Architecture | PROPOSED | LangGraph workflow patterns |
| ADR-025 | GDPR Client Data Architecture | PROPOSED | DPA, encryption, data residency, LLM isolation |

---

## Deprecated Features (Do Not Implement)

### Suggested Actions (Azioni Suggerite) - REMOVED
**Removed in:** DEV-245 Phase 5.15 (January 2026)
**Reason:** User feedback - actions were generic, not contextually relevant

**What was removed:**
- `<suggested_actions>` XML tag parsing
- `SuggestedActionsBar.tsx` frontend component
- `ActionValidator`, `ActionRegenerator` services
- `suggested_actions` SSE event

**What was kept:**
- Interactive Questions (pre-response clarification)
- Web Verification caveats

**Important:** If any PRATIKO 2.0 task mentions "suggested actions", verify whether it refers to the removed feature or a new design.

---

## Architectural Patterns from PRATIKO 1.5 (DEV-242/244/245)

The following patterns were established during Response Quality improvements and should be reused:

### 1. Parallel Hybrid RAG Architecture (DEV-245 Phase 3.2)
- **Pattern:** Execute KB retrieval and web search in parallel, merge with RRF
- **Benefit:** 50% fewer LLM calls, 40-50% faster responses
- **Files:** `app/services/parallel_retrieval.py`, `app/services/web_verification.py`
- **Use for:** Any feature requiring external data verification

### 2. Topic Summary State for Long Conversations (DEV-245 Phase 5.3)
- **Pattern:** Store `conversation_topic` + `topic_keywords` in RAGState with reducers
- **Benefit:** Maintains context across 4+ conversation turns
- **Files:** `app/core/langgraph/types.py`
- **Use for:** Phase 4 (Procedure) context persistence

### 3. Generic Extraction Principles (DEV-245 Phase 4)
- **Pattern:** Universal extraction rules instead of topic-specific rules
- **Benefit:** Works for any topic without code changes
- **Files:** `app/orchestrators/prompting.py`
- **Use for:** All LLM prompting in PRATIKO 2.0

### 4. Source Authority Hierarchy (DEV-242/244)
- **Pattern:** `SOURCE_AUTHORITY` dict with official source boosts
- **Files:** `app/services/parallel_retrieval.py`
- **Use for:** Phase 2 (Matching Engine) source prioritization

### 5. Hallucination Guard (DEV-245 Phase 2.3)
- **Status:** Created but not yet integrated into pipeline
- **Files:** `app/services/hallucination_guard.py`
- **Opportunity:** Integrate in Phase 11 (Infrastructure) - see DEV-389

---

## Task ID Mapping

| Old ID | New ID | Phase |
|--------|--------|-------|
| DEV-2.0-001 to DEV-2.0-008 | DEV-300 to DEV-307 | Phase 0: Foundation |
| DEV-2.0-009 to DEV-2.0-020 | DEV-308 to DEV-319 | Phase 1: Service Layer |
| DEV-2.0-021 to DEV-2.0-030 | DEV-320 to DEV-329 | Phase 2: Matching Engine |
| DEV-2.0-031 to DEV-2.0-040 | DEV-330 to DEV-339 | Phase 3: Communications |
| DEV-2.0-041 to DEV-2.0-048 | DEV-340 to DEV-347 | Phase 4: Procedure (original) |
| DEV-2.0-049 to DEV-2.0-054 | DEV-348 to DEV-353 | Phase 5: Tax Calculations |
| DEV-2.0-055 to DEV-2.0-060 | DEV-354 to DEV-359 | Phase 6: Dashboard |
| DEV-2.0-061 to DEV-2.0-064 | DEV-360, DEV-361, DEV-363, DEV-365 | Phase 7: Documents (4 tasks — DEV-362, DEV-364 removed: persistent client doc storage contradicts FR-008 temp-only policy) |
| DEV-2.0-067 to DEV-2.0-072 | DEV-366 to DEV-371 | Phase 8: Frontend Integration |
| DEV-2.0-073 to DEV-2.0-080 | DEV-372 to DEV-379 | Phase 9: GDPR Compliance |
| NEW | DEV-380 to DEV-387 | Phase 10: Deadline System |
| NEW | DEV-388 to DEV-395 | Phase 11: Infrastructure & Quality |
| NEW | DEV-396 to DEV-401 | Phase 12: Pre-Launch Compliance |
| NEW | DEV-402 to DEV-405 | Phase 4: Procedure (/procedura + @client) |
| NEW | DEV-406 to DEV-410 | Phase 5: Tax Calculations (IVA, Ritenuta, Cedolare, TFR, Payroll) |
| NEW | DEV-411 | Phase 7: Documents (Fattura XML Parser) |
| NEW | DEV-412 | Phase 3: Communications (Email Tracking) |
| NEW | DEV-413 | Phase 5: Tax (Regional Data Population) |
| NEW | DEV-414 | Phase 10: Deadlines (Calendar Sync) |
| NEW | DEV-415 | Phase 3: Communications (Unsubscribe) |
| NEW | DEV-416 | Phase 11: Infrastructure (Tiered Ingestion Verification) |
| NEW | DEV-417 | Phase 11: Infrastructure (Billing Studio Integration) |
| NEW | DEV-418 | Phase 11: Infrastructure (Monitoring/Alerting) |
| NEW | DEV-419 | Phase 3: Communications (Retention Policy) |
| NEW | DEV-420 | Phase 1: Service Layer (JSON Export) |
| NEW | DEV-421 | Phase 7: Documents (Document Type Detection) |
| NEW | DEV-422 to DEV-427 | Phase 13: In-App Notifications |
| NEW | DEV-428 | Phase 1: Service Layer (ClientProfile INPS/INAIL fields) |
| NEW | DEV-429 | Phase 4: Procedure (Procedure Suggestions per Client) |
| NEW | DEV-430 | Phase 6: Dashboard (Quick Action Counts API) |
| NEW | DEV-431 to DEV-432 | Phase 13: Modelli e Formulari Library |
| NEW | DEV-433 | Phase 13: Chat Feedback Persistent Storage |
| NEW | DEV-434 | Phase 6: Dashboard (Client Distribution Charts) — extends DEV-355 |
| NEW | DEV-435 | Phase 6: Dashboard (Matching Statistics) — extends DEV-355 |
| NEW | DEV-436 | Phase 6: Dashboard (Period Selector) — extends DEV-356 |
| NEW | DEV-437 | Phase 10: Deadlines (Amount & Penalties fields) — extends DEV-380 |
| NEW | DEV-438 | Phase 10: Deadlines (Per-Deadline User Reminders) |
| NEW | DEV-439 | Phase 13: Interactive Question Templates Activation |
| NEW | DEV-440 | Phase 13: Full Notifications Page |
| NEW | DEV-441 | Phase 13: Settings Page (Studio Preferences UI) |
| NEW | DEV-442 to DEV-445 | Phase 14: Hybrid Email Config (backend — model, service, API, hybrid sending) |
| NEW | DEV-446 | Phase 14: Hybrid Email Config (Settings UI section) |
| NEW | DEV-447 | Phase 14: Hybrid Email Config (E2E tests) |
| NEW | DEV-448 | Phase 14: Hybrid Email Config (BillingPlan custom_email_allowed field) |
| NEW | DEV-449 | Phase 14: Hybrid Email Config (SMTP key rotation) |

---

## High-Risk Tasks (Require Extra Review)

| Task ID | Risk Level | Risk Type | Mitigation |
|---------|------------|-----------|------------|
| DEV-307 | CRITICAL | DB Migration | Backup before deploy, reversible migration |
| DEV-315 | HIGH | User Table Modification | Existing users affected, nullable FK |
| DEV-322 | HIGH | LangGraph Pipeline | Modifies 134-step pipeline |
| DEV-327 | CRITICAL | Security | Multi-tenant isolation must be 95%+ |
| DEV-337 | HIGH | LangGraph Modification | Response formatter changes |
| DEV-372 | CRITICAL | Legal/Compliance | DPA required before client data |
| DEV-374 | CRITICAL | Legal/Compliance | 72h breach notification requirement |
| DEV-396 | CRITICAL | Legal/Compliance | DPIA mandatory before client data storage |
| DEV-397 | CRITICAL | Infrastructure | Encryption at rest + DPA with Hetzner |
| DEV-398 | CRITICAL | Legal/Compliance | LLM transfer safeguards required |
| DEV-399 | HIGH | Legal/Compliance | 30-day Garante notification period |
| DEV-425 | HIGH | Multi-Service Modification | Notification triggers modify 4 existing services (fire-and-forget pattern) |
| DEV-428 | MEDIUM | DB Schema Extension | Adds columns to existing client model, migration required |

---

## Task Dependency Map

**Critical Path:** Tasks must be completed in order. Blocking tasks prevent downstream work.

### Phase 0 → Phase 1 Dependencies

```
DEV-300 (Studio Model)
    ├── DEV-308 (StudioService) ─── DEV-311 (Studio API)
    └── DEV-315 (User-Studio Association)

DEV-301 (Client Model)
    ├── DEV-302 (ClientProfile) ─── DEV-322 (Vector Generation)
    └── DEV-309 (ClientService) ─── DEV-312 (Client API)
                                └── DEV-313 (Import)
                                └── DEV-314 (Export)

DEV-303 (MatchingRule) ─── DEV-321 (Pre-configured Rules)
DEV-304 (ClientMatch) ─── DEV-320 (MatchingService)
DEV-305 (Communication) ─── DEV-330 (CommunicationService)
DEV-306 (Procedura) ─── DEV-340 (ProceduraService)

DEV-307 (Alembic Migration) ← BLOCKS ALL Phase 1
```

### Phase 2 (Matching Engine) Dependencies

```
DEV-320 (NormativeMatchingService)
    ← DEV-302 (ClientProfile)
    ← DEV-303 (MatchingRule)
    ← DEV-304 (ClientMatch)
    └── DEV-323 (LangGraph Node) ← DEV-322 (Vector Generation)
    └── DEV-324 (ProactiveSuggestion)
    └── DEV-325-229 (Background Jobs, API, Tests)
```

### Phase 3 (Communications) Dependencies

```
DEV-330 (CommunicationService)
    ← DEV-305 (Communication Model)
    ← DEV-324 (ProactiveSuggestion) [for suggestion-to-communication]
    └── DEV-331 (LLM Generation)
    └── DEV-332 (Approval Workflow)
    └── DEV-333 (Email) + DEV-334 (WhatsApp)
```

### Phase 10 (Deadline System) Dependencies

```
DEV-380 (Deadline Model)
    └── DEV-381 (DeadlineService) ─── DEV-385 (API)
    └── DEV-382 (KB Extraction) ← Knowledge Base ingestion
    └── DEV-383 (Client Matching) ← DEV-309, DEV-302
    └── DEV-384 (Notifications) ← DEV-333 (Email)
```

### Phase 13 (Figma Gap Coverage) Dependencies

```
DEV-422 (Notification Model)
    └── DEV-423 (NotificationService) ─── DEV-424 (API)
    └── DEV-425 (Triggers) ← DEV-383, DEV-320, DEV-335
    └── DEV-426 (Frontend Dropdown) ← DEV-424
    └── DEV-427 (E2E Tests) ← DEV-422-426
    └── DEV-440 (Full Page) ← DEV-424, DEV-426

DEV-431 (Formulario Model)
    └── DEV-432 (Formulario API)
    └── DEV-430 (Quick Action Counts) ← DEV-381

DEV-355 (Dashboard Aggregation)
    └── DEV-434 (Distribution Charts)
    └── DEV-435 (Matching Stats)
    └── DEV-436 (Period Selector) ← DEV-356

DEV-380 (Deadline Model)
    └── DEV-437 (Amount/Penalties fields)
    └── DEV-438 (User Reminders) ← DEV-422
```

### Cross-Phase Critical Dependencies

| Downstream Task | Blocking Tasks |
|-----------------|----------------|
| DEV-323 (LangGraph Node) | DEV-320, DEV-322 |
| DEV-337 (Response Formatter) | DEV-323, DEV-330 |
| DEV-363 (Document Context) | DEV-360 (Document Parser), Existing context_builder_node |
| DEV-371 (E2E Tests) | All Phase 0-8 tasks |
| DEV-387 (Deadline E2E) | All Phase 10 tasks |
| DEV-427 (Notification E2E) | All Phase 13 notification tasks (DEV-422 to DEV-426) |

---

## Phase 0: Foundation (Week 1-2) - 8 Tasks

### DEV-300: Create Studio SQLModel

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** CRITICAL | **Effort:** 2-3h | **Status:** NOT STARTED

**Problem:**
PratikoAI 1.0 is single-user. Each user has isolated data via `user_id` FK. We need multi-tenancy where professional studios can manage multiple clients, but currently there's no Studio entity to group users and clients together.

**Solution:**
Create a `Studio` SQLModel as the tenant root entity. All client data will be isolated by `studio_id`. This follows the row-level isolation pattern used by Stripe and Slack.

**Agent Assignment:** @Primo (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** None (foundation task)
- **Unlocks:** DEV-308 (StudioService), DEV-315 (User-Studio), DEV-307 (Migration)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/studio.py`

**Fields:**
- `id`: UUID (primary key)
- `name`: str (required)
- `slug`: str (unique, for URLs)
- `settings`: JSONB (studio preferences)
- `max_clients`: int (default: 100)
- `created_at`: datetime
- `updated_at`: datetime

**Testing Requirements:**
- **TDD:** Write `tests/models/test_studio.py` FIRST
- **Unit Tests:**
  - `test_studio_creation_valid` - valid studio creation
  - `test_studio_slug_uniqueness` - slug unique constraint
  - `test_studio_settings_jsonb` - JSONB field handling
  - `test_studio_max_clients_default` - default value
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/` to ensure no model conflicts
- **Coverage Target:** 80%+ for new model code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Slug collision | LOW | Unique constraint + validation |
| UUID performance | LOW | Use uuid7 for sortable IDs |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] SQLModel class with all fields defined
- [ ] UUID primary key generation
- [ ] Slug uniqueness validation
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-301: Create Client SQLModel

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** CRITICAL | **Effort:** 2-3h | **Status:** NOT STARTED

**Problem:**
Studios need to manage their clients (up to 100 per studio). Client data includes sensitive PII (codice fiscale, P.IVA, contact info) that must be encrypted and properly isolated between studios.

**Solution:**
Create `Client` SQLModel with encrypted PII fields using existing `EncryptedTaxID` from `app/core/encryption/encrypted_types.py`. Implement soft delete for GDPR compliance.

**Agent Assignment:** @Primo (primary), @Severino (security review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model for studio_id FK)
- **Unlocks:** DEV-302 (ClientProfile), DEV-309 (ClientService), DEV-307 (Migration)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/client.py`

**Fields:**
- `id`: int (primary key)
- `studio_id`: UUID (FK to Studio)
- `codice_fiscale`: str (encrypted via EncryptedTaxID)
- `partita_iva`: str (encrypted, nullable)
- `nome`: str (encrypted)
- `tipo_cliente`: enum (PERSONA_FISICA, DITTA_INDIVIDUALE, SOCIETA, etc.)
- `email`: str (encrypted, nullable)
- `phone`: str (encrypted, nullable)
- `indirizzo`: str (nullable)
- `cap`: str (5 digits)
- `comune`: str
- `provincia`: str (2 chars)
- `stato_cliente`: enum (ATTIVO, PROSPECT, CESSATO, SOSPESO)
- `data_nascita_titolare`: date (nullable, for PERSONA_FISICA)
- `note_studio`: text (nullable, internal notes)
- `created_at`, `updated_at`, `deleted_at`

**Testing Requirements:**
- **TDD:** Write `tests/models/test_client.py` FIRST
- **Unit Tests:**
  - `test_client_creation_valid` - valid client creation
  - `test_client_cf_validation` - CF format validation
  - `test_client_piva_validation` - P.IVA format validation
  - `test_client_pii_encryption` - verify encryption applied
  - `test_client_soft_delete` - deleted_at handling
  - `test_client_studio_fk` - FK constraint
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/` and verify encryption tests pass
- **Coverage Target:** 80%+ for new model code, 95%+ for encryption logic

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| PII exposure | CRITICAL | Use existing EncryptedTaxID |
| CF/P.IVA validation | MEDIUM | Reuse validators from `italian_subscription_service.py` |
| Cross-tenant access | CRITICAL | Always filter by studio_id |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] SQLModel class with encrypted PII fields
- [ ] CF/P.IVA validation using existing validators
- [ ] Soft delete support (deleted_at)
- [ ] 80%+ test coverage achieved
- [ ] Security review by @Severino
- [ ] All existing tests still pass (regression)

---

### DEV-302: Create ClientProfile SQLModel

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** CRITICAL | **Effort:** 2-3h | **Status:** NOT STARTED

**Problem:**
Client matching requires structured metadata (ATECO, regime fiscale, CCNL) and semantic matching via embeddings. This data is separate from core client PII and needs its own model for the matching engine.

**Solution:**
Create `ClientProfile` as a 1:1 extension of `Client` containing business/fiscal metadata and a 1536-dimension vector for semantic matching. Use HNSW index for fast similarity search.

**Agent Assignment:** @Primo (primary), @Ezio (vector support), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-301 (Client model for client_id FK)
- **Unlocks:** DEV-320 (MatchingService), DEV-322 (Vector Generation), DEV-307 (Migration)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/client_profile.py`

**Fields:**
- `id`: int (primary key)
- `client_id`: int (1:1 FK to Client)
- `codice_ateco_principale`: str (XX.XX.XX format)
- `codici_ateco_secondari`: ARRAY[str]
- `regime_fiscale`: enum (ORDINARIO, SEMPLIFICATO, FORFETTARIO, AGRICOLO, MINIMI)
- `ccnl_applicato`: str (nullable, for employers)
- `n_dipendenti`: int (default: 0)
- `data_inizio_attivita`: date
- `data_cessazione_attivita`: date (nullable)
- `immobili`: JSONB (nullable, array of property objects for IMU/TASI calculations)
- `posizione_agenzia_entrate`: enum (REGOLARE, IRREGOLARE, IN_VERIFICA, nullable)
- `profile_vector`: Vector(1536) (for semantic matching)

**Immobili JSONB Schema:**
```json
{
  "tipo": "ABITAZIONE_PRINCIPALE|SECONDA_CASA|COMMERCIALE",
  "comune": "string",
  "rendita_catastale": 1000.00,
  "percentuale_possesso": 100
}
```

**Testing Requirements:**
- **TDD:** Write `tests/models/test_client_profile.py` FIRST
- **Unit Tests:**
  - `test_client_profile_creation` - valid profile creation
  - `test_client_profile_one_to_one` - 1:1 FK constraint
  - `test_ateco_format_validation` - XX.XX.XX format
  - `test_regime_fiscale_enum` - enum values
  - `test_profile_vector_dimension` - 1536-dim vector
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/` to ensure no conflicts
- **Coverage Target:** 80%+ for new model code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Vector index performance | MEDIUM | HNSW with m=16, ef_construction=64 |
| ATECO validation | LOW | Regex validation for XX.XX.XX format |
| Orphaned profiles | LOW | CASCADE delete from Client |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] 1:1 relationship with Client
- [ ] ATECO code format validation
- [ ] Vector column for semantic matching
- [ ] HNSW index specification in model
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-303: Create MatchingRule SQLModel

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The matching engine needs pre-configured rules to identify which regulations affect which clients. Rules must be flexible (JSONB conditions) but not user-configurable for MVP to reduce complexity.

**Solution:**
Create `MatchingRule` model with JSONB conditions supporting AND/OR operators and field comparisons. Pre-seed with 10 rules covering common scenarios (rottamazione, bonus sud, etc.).

**Agent Assignment:** @Primo (primary), @Mario (rule definitions), @Clelia (tests)

**Dependencies:**
- **Blocking:** None (standalone model)
- **Unlocks:** DEV-320 (MatchingService), DEV-321 (Pre-configured Rules), DEV-307 (Migration)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/matching_rule.py`

**Fields:**
- `id`: UUID (primary key)
- `name`: str (unique)
- `description`: text
- `rule_type`: enum (NORMATIVA, SCADENZA, OPPORTUNITA)
- `conditions`: JSONB (rule conditions)
- `priority`: int (1-100)
- `is_active`: bool
- `valid_from`: date
- `valid_to`: date (nullable)
- `categoria`: str
- `fonte_normativa`: str

**Testing Requirements:**
- **TDD:** Write `tests/models/test_matching_rule.py` FIRST
- **Unit Tests:**
  - `test_matching_rule_creation` - valid rule creation
  - `test_matching_rule_jsonb_conditions` - JSONB validation
  - `test_matching_rule_priority_ordering` - priority 1-100
  - `test_matching_rule_validity_dates` - valid_from/valid_to
  - `test_matching_rule_enum_types` - rule_type enum
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/` to ensure no conflicts
- **Coverage Target:** 80%+ for new model code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| JSONB validation | MEDIUM | Pydantic schema for conditions |
| Rule conflicts | LOW | Priority ordering |
| Outdated rules | MEDIUM | valid_from/valid_to dates |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] JSONB conditions with Pydantic validation
- [ ] Priority ordering support
- [ ] Validity date range support
- [ ] 10 pre-configured rules defined
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-304: Create Communication SQLModel

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Priority:** HIGH | **Effort:** 2-3h | **Status:** NOT STARTED

**Problem:**
Professionals need to send communications to clients about regulations. These must go through an approval workflow (AI generates, human approves) with full audit trail for compliance.

**Solution:**
Create `Communication` model with status workflow (DRAFT → PENDING_REVIEW → APPROVED → SENT) and audit fields. Enforce that creator cannot approve their own communications.

**Agent Assignment:** @Primo (primary), @Severino (workflow security), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio), DEV-301 (Client for client_id FK)
- **Unlocks:** DEV-330 (CommunicationService), DEV-307 (Migration)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/communication.py`

**Fields:**
- `id`: UUID (primary key)
- `studio_id`: UUID (FK)
- `client_id`: int (FK, nullable for bulk)
- `subject`: str
- `content`: text
- `channel`: enum (EMAIL, WHATSAPP)
- `status`: enum (DRAFT, PENDING_REVIEW, APPROVED, REJECTED, SENT, FAILED)
- `created_by`: int (FK to User)
- `approved_by`: int (FK to User, nullable)
- `approved_at`: datetime (nullable)
- `sent_at`: datetime (nullable)
- `normativa_riferimento`: str (nullable)
- `matching_rule_id`: UUID (FK, nullable)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_communication.py` FIRST
- **Unit Tests:**
  - `test_communication_creation` - valid communication creation
  - `test_communication_status_enum` - all status values
  - `test_communication_channel_enum` - EMAIL, WHATSAPP
  - `test_communication_self_approval_constraint` - approved_by != created_by
  - `test_communication_audit_fields` - created_by, approved_by, approved_at
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/` to ensure no conflicts
- **Coverage Target:** 80%+ for new model code, 95%+ for workflow logic

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Self-approval | HIGH | DB constraint: approved_by != created_by |
| Status bypass | HIGH | State machine validation in service |
| Missing audit | MEDIUM | Use existing SecurityAuditLogger |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Status workflow enforcement
- [ ] Audit trail (created_by, approved_by)
- [ ] Cannot approve own communications (DB constraint)
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-305: Create Procedura SQLModel

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Professionals follow complex multi-step procedures (e.g., opening P.IVA, hiring employee). Currently they rely on memory or external checklists. PratikoAI should provide interactive step-by-step procedure.

**Solution:**
Create `Procedura` model with JSONB steps array containing checklists, documents, and notes. Support versioning for procedura updates.

**Agent Assignment:** @Primo (primary), @Mario (procedura definitions), @Clelia (tests)

**Dependencies:**
- **Blocking:** None (standalone model)
- **Unlocks:** DEV-306 (ProceduraProgress), DEV-340 (ProceduraService), DEV-307 (Migration)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/procedura.py`

**Fields:**
- `id`: UUID (primary key)
- `code`: str (unique, e.g., "APERTURA_PIVA")
- `title`: str
- `description`: text
- `category`: enum (FISCALE, LAVORO, SOCIETARIO, PREVIDENZA)
- `steps`: JSONB (array of step objects)
- `estimated_time_minutes`: int
- `version`: int
- `is_active`: bool
- `last_updated`: date

**Testing Requirements:**
- **TDD:** Write `tests/models/test_procedura.py` FIRST
- **Unit Tests:**
  - `test_procedura_creation` - valid procedura creation
  - `test_procedura_code_uniqueness` - unique code constraint
  - `test_procedura_steps_jsonb` - JSONB steps validation
  - `test_procedura_category_enum` - category values
  - `test_procedura_versioning` - version increment
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/` to ensure no conflicts
- **Coverage Target:** 80%+ for new model code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| JSONB schema changes | MEDIUM | Version field for migrations |
| Stale procedure | LOW | last_updated tracking |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] JSONB steps with Pydantic validation
- [ ] Version tracking
- [ ] Category filtering support
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-306: Create ProceduraProgress SQLModel

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Users need to track their progress through procedure, resume where they left off, and optionally associate procedura progress with a specific client.

**Solution:**
Create `ProceduraProgress` model linking user, studio, procedura, and optionally client. Track current step and completed steps array.

**Agent Assignment:** @Primo (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio), DEV-301 (Client), DEV-305 (Procedura)
- **Unlocks:** DEV-340 (ProceduraService), DEV-307 (Migration)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/procedura_progress.py`

**Fields:**
- `id`: UUID (primary key)
- `user_id`: int (FK)
- `studio_id`: UUID (FK)
- `procedura_id`: UUID (FK to Procedura)
- `client_id`: int (FK, nullable - procedura can be for specific client)
- `current_step`: int
- `completed_steps`: JSONB (array of completed step numbers)
- `started_at`: datetime
- `completed_at`: datetime (nullable)
- `notes`: text (nullable)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_procedura_progress.py` FIRST
- **Unit Tests:**
  - `test_progress_creation` - valid progress creation
  - `test_progress_fk_constraints` - user, studio, procedura FKs
  - `test_progress_completed_steps_jsonb` - JSONB array handling
  - `test_progress_resume` - current_step tracking
  - `test_progress_client_optional` - nullable client_id
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/` to ensure no conflicts
- **Coverage Target:** 80%+ for new model code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Orphaned progress | LOW | CASCADE on procedura delete |
| Concurrent updates | LOW | Optimistic locking via version |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Track progress per user per procedura
- [ ] Optional client association
- [ ] Completion timestamp
- [ ] Resume capability
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-307: Alembic Migration for Phase 0

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
All 7 new models need database tables with proper indexes, foreign keys, and constraints. This is a critical migration affecting production.

**Solution:**
Create single Alembic migration creating all Phase 0 tables with HNSW vector index and composite indexes for common queries.

**Agent Assignment:** @Primo (primary), @Ezio (review), @Severino (security review)

**Dependencies:**
- **Blocking:** DEV-300, DEV-301, DEV-302, DEV-303, DEV-304, DEV-305, DEV-306 (all models)
- **Unlocks:** ALL Phase 1 tasks (DEV-308-219)

**Change Classification:** RESTRUCTURING

**Impact Analysis:**
- **Primary File:** `alembic/versions/YYYYMMDD_add_pratikoai_2_0_models.py`
- **Affected Files:**
  - `alembic/env.py` (import new models)
  - All Phase 1+ services (depend on new tables)
- **Related Tests:**
  - `tests/migrations/test_phase0_migration.py` (direct)
  - `tests/models/test_*.py` (all model tests)
- **Baseline Command:** `pytest tests/models/ -v && alembic check`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Database backup completed
- [ ] Staging environment available
- [ ] Rollback procedure documented

**Error Handling:**
- Migration syntax error: Alembic stops with detailed error message
- Table already exists: Migration skipped with warning (idempotent check)
- Index creation failure: Log error, continue with partial migration, manual fix required
- Foreign key violation: Migration rolled back, detailed constraint error logged
- Disk space exhausted: Migration rolled back, error logged
- **Logging:** All errors MUST be logged with context (migration_id, operation, table_name) at ERROR level

**Performance Requirements:**
- Total migration time: <30s for empty database
- Lock time per table: <1s (use CONCURRENTLY for indexes)
- HNSW index creation: <5s (empty table, scales with data)
- Rollback time: <10s

**Edge Cases:**
- **Partial Migration:** If migration fails mid-way, ensure atomicity via transaction
- **Concurrent Migrations:** Multiple pods -> only first applies, others skip (Alembic lock)
- **Large Existing Data:** N/A for new tables, but plan for future data migrations
- **Index Creation:** Use CONCURRENTLY to avoid table locks
- **Rollback:** Ensure downgrade() drops tables in reverse dependency order

**File:** `alembic/versions/YYYYMMDD_add_pratikoai_2_0_models.py`

**Tables to Create:**
1. `studios`
2. `clients`
3. `client_profiles`
4. `matching_rules`
5. `communications`
6. `procedure`
7. `procedura_progress`

**Indexes:**
- HNSW on `client_profiles.profile_vector` (m=16, ef_construction=64)
- Composite on `clients(studio_id, stato_cliente)`
- Composite on `communications(studio_id, status)`
- Composite on `client_profiles(studio_id, regime_fiscale)`

**Testing Requirements:**
- **TDD:** Write migration tests FIRST
- **Unit Tests:**
  - `test_migration_upgrade` - tables created correctly
  - `test_migration_downgrade` - tables dropped correctly
  - `test_migration_indexes` - indexes created
  - `test_migration_constraints` - FK constraints work
- **Integration Tests:** `tests/migrations/test_phase0_migration.py`
  - Test full upgrade/downgrade cycle
  - Verify data integrity
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:**
  - `pytest tests/models/` - all model tests pass
  - `alembic check` - no pending migrations
- **Coverage Target:** 95%+ for migration code (critical)

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration failure | CRITICAL | Test on staging first |
| Rollback needed | CRITICAL | Ensure downgrade() works |
| Long lock time | MEDIUM | Create indexes CONCURRENTLY |
| Data loss | CRITICAL | Full backup before deploy |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Migration tests written BEFORE implementation (TDD)
- [ ] All 7 tables created
- [ ] HNSW vector index
- [ ] All foreign key constraints
- [ ] Migration reversible (downgrade works)
- [ ] Tested on staging environment
- [ ] All existing tests still pass (regression)

**Pre-Deployment Checklist:**
- [ ] Database backup completed
- [ ] Staging migration successful
- [ ] Rollback tested

---

## Phase 1: Studio-Client Service Layer (Week 3-4) - 12 Tasks

### DEV-308: StudioService with CRUD

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need service layer to manage Studio lifecycle (create, read, update, delete) with business logic like slug uniqueness validation and settings management.

**Solution:**
Create `StudioService` with async CRUD methods following existing service patterns in `app/services/`.

> **Navigation:** When implementing the frontend, add "Clienti" menu item (Users icon, route `/clients`) to the user menu dropdown in `web/src/app/chat/components/ChatHeader.tsx`. Insert as the first item in the feature links section above "Il mio Account". Target menu layout:
> ```
> ┌──────────────────────┐
> │  Clienti             │  (DEV-308)
> │  Comunicazioni       │  (DEV-330)
> │  Procedure           │  (DEV-340)
> │  Dashboard           │  (DEV-354)
> │  Scadenze Fiscali    │  (DEV-385)
> │ ──────────────────── │
> │  Il mio Account      │
> │  [superuser items]   │
> │ ──────────────────── │
> │  Esci                │
> └──────────────────────┘
> ```

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model), DEV-307 (Migration)
- **Unlocks:** DEV-311 (Studio API), DEV-315 (User-Studio)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Nulls/Empty:** Empty name rejected (min length 1); empty slug auto-generated from name; null settings → `{}`
- **Slug Validation:** Special chars stripped, Unicode normalized, max 50 chars, lowercase enforced
- **Concurrency:** Two simultaneous slug creates → DB unique constraint + retry with suffix
- **Cascade Delete:** Soft delete studio → all clients marked inactive (not deleted)
- **JSONB Settings:** Null keys ignored, max settings size 10KB, invalid JSON rejected
- **Recovery:** Soft-deleted studio can be reactivated via admin API within 30 days

**File:** `app/services/studio_service.py`

**Methods:**
- `create_studio(name, slug, settings)` - Create new studio
- `get_studio(studio_id)` - Get studio by ID
- `get_studio_by_slug(slug)` - Get studio by URL slug
- `update_studio(studio_id, data)` - Update studio settings
- `delete_studio(studio_id)` - Soft delete studio
- `get_user_studio(user_id)` - Get studio for user

**Testing Requirements:**
- **TDD:** Write `tests/services/test_studio_service.py` FIRST
- **Unit Tests:**
  - `test_create_studio_success` - valid creation
  - `test_create_studio_duplicate_slug` - slug collision
  - `test_get_studio_found` - existing studio
  - `test_get_studio_not_found` - 404 handling
  - `test_update_studio_settings` - JSONB update
  - `test_delete_studio_soft` - soft delete
- **Edge Case Tests:**
  - `test_create_studio_empty_name` - rejects empty name
  - `test_create_studio_auto_slug` - generates slug from name when empty
  - `test_create_studio_unicode_slug` - Unicode normalized correctly
  - `test_create_studio_concurrent_slug` - handles race condition with retry
  - `test_update_settings_null_keys` - ignores null keys in JSONB
  - `test_update_settings_too_large` - rejects >10KB settings
  - `test_delete_cascade_clients` - clients marked inactive on studio delete
  - `test_reactivate_soft_deleted` - admin can restore within 30 days
- **Integration Tests:** `tests/services/test_studio_service_integration.py`
  - Database transaction testing
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/` to ensure no service conflicts
- **Coverage Target:** 80%+ for service code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Slug collision race | LOW | DB unique constraint + retry logic |
| Orphaned data on delete | MEDIUM | Soft delete, cascade to clients |
| Settings overflow | LOW | 10KB limit enforced |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All CRUD methods implemented
- [ ] Slug uniqueness validation
- [ ] Settings JSONB handling
- [ ] Soft delete with cascade consideration
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-309: ClientService with CRUD

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need service to manage clients with business rules: 100 client limit per studio, CF/P.IVA validation, and PII encryption. Must ensure tenant isolation.

**Solution:**
Create `ClientService` with CRUD methods that enforce business rules. Reuse existing CF/P.IVA validators from `italian_subscription_service.py`.

**Agent Assignment:** @Ezio (primary), @Severino (security review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-301 (Client model), DEV-307 (Migration)
- **Unlocks:** DEV-312 (Client API), DEV-313 (Import), DEV-314 (Export), DEV-320 (Matching)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid CF format: HTTP 422, `"Codice fiscale non valido"`
- Duplicate CF in studio: HTTP 409, `"Cliente con questo CF già presente"`
- Studio limit exceeded: HTTP 400, `"Raggiunto limite di 100 clienti per studio"`
- Client not found: HTTP 404, `"Cliente non trovato"`
- Unauthorized access: HTTP 403, `"Accesso non autorizzato a questo cliente"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- List clients (100): <100ms
- Create client: <200ms
- Search by CF: <50ms

**Edge Cases:**
- **CF/PIVA Nulls:** Null CF allowed only if P.IVA provided; both null → HTTP 422
- **CF Format:** Empty string, spaces-only, special chars → HTTP 422; lowercase → normalized to uppercase
- **100-Client Limit:** At exactly 99 clients, concurrent creates → DB advisory lock prevents race
- **Pagination:** page=0 → page=1; page>max → returns empty list (not error); size=0 → default 20
- **Empty Filters:** Empty search string → returns all; null filter values → ignored
- **Soft Delete:** Deleted clients excluded from counts; deleted client CF can be reused
- **Encryption:** Key rotation → background job re-encrypts; decryption failure → log error, return masked data
- **Tenant Isolation:** studio_id=null in request → HTTP 400; mismatched studio → HTTP 404 (not 403)

**File:** `app/services/client_service.py`

**Methods:**
- `create_client(studio_id, data)` - Create client with validation
- `get_client(client_id, studio_id)` - Get client by ID (with tenant check)
- `update_client(client_id, studio_id, data)` - Update client data
- `delete_client(client_id, studio_id)` - Soft delete client
- `list_clients(studio_id, filters, page, size)` - List with pagination
- `count_clients(studio_id)` - Count for limit enforcement

**Testing Requirements:**
- **TDD:** Write `tests/services/test_client_service.py` FIRST
- **Unit Tests:**
  - `test_create_client_success` - valid creation
  - `test_create_client_limit_exceeded` - 100 client limit
  - `test_create_client_invalid_cf` - CF validation
  - `test_create_client_invalid_piva` - P.IVA validation
  - `test_create_client_duplicate_cf` - uniqueness per studio
  - `test_get_client_tenant_isolation` - cannot access other studio's clients
  - `test_list_clients_pagination` - pagination works
- **Edge Case Tests:**
  - `test_create_client_null_cf_with_piva` - allowed when P.IVA provided
  - `test_create_client_both_null` - rejected HTTP 422
  - `test_create_client_cf_lowercase` - normalized to uppercase
  - `test_create_client_cf_spaces` - rejected
  - `test_concurrent_create_at_limit` - advisory lock prevents race at 99 clients
  - `test_list_page_zero` - treated as page 1
  - `test_list_page_beyond_max` - returns empty list
  - `test_list_empty_search` - returns all clients
  - `test_soft_delete_frees_cf` - deleted client CF can be reused
  - `test_encryption_key_rotation` - re-encryption works
  - `test_tenant_null_studio_id` - HTTP 400
  - `test_tenant_wrong_studio_404` - returns 404 not 403
- **Integration Tests:** `tests/services/test_client_service_integration.py`
  - Database with encryption
  - Tenant isolation verification
- **E2E Tests:** (covered in DEV-319)
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:**
  - Run `pytest tests/services/`
  - Run `pytest tests/security/` for isolation
- **Coverage Target:** 80%+ for service, 95%+ for tenant isolation

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Exceed client limit | HIGH | Check before insert |
| Duplicate CF/P.IVA | MEDIUM | Unique constraint per studio |
| Cross-tenant access | CRITICAL | Always include studio_id in queries |
| PII leak | CRITICAL | Use EncryptedTaxID |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] 100 client limit enforced with clear error message
- [ ] CF/P.IVA format validation (reuse existing)
- [ ] CF/P.IVA uniqueness per studio
- [ ] PII encryption working
- [ ] Pagination for list endpoint
- [ ] All queries include studio_id filter
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-310: ClientProfileService

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Client profiles contain matching metadata (ATECO, regime, CCNL) and need separate management from core client data. Profile vectors need generation for semantic matching.

**Solution:**
Create `ClientProfileService` for profile CRUD with automatic profile vector generation when profile is created/updated.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-302 (ClientProfile model), DEV-309 (ClientService), DEV-307 (Migration)
- **Unlocks:** DEV-311 (combined in API), DEV-322 (Vector Generation)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Profile already exists: HTTP 409, `"Profilo cliente già esistente"`
- Client not found: HTTP 404, `"Cliente non trovato"`
- Invalid ATECO format: HTTP 422, `"Formato codice ATECO non valido (XX.XX.XX)"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Get profile: <50ms
- Update with vector regeneration: <500ms (async vector)

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/services/client_profile_service.py`

**Methods:**
- `create_profile(client_id, profile_data)` - Create client profile
- `update_profile(client_id, profile_data)` - Update profile
- `get_profile(client_id)` - Get profile by client ID
- `get_profile_for_matching(client_id)` - Get profile with vector
- `regenerate_vector(client_id)` - Regenerate embedding

**Testing Requirements:**
- **TDD:** Write `tests/services/test_client_profile_service.py` FIRST
- **Unit Tests:**
  - `test_create_profile_success` - valid creation
  - `test_create_profile_auto_vector` - vector generated
  - `test_update_profile_regenerate_vector` - vector updated on change
  - `test_get_profile_for_matching` - returns with vector
  - `test_ateco_validation` - format validation
- **Integration Tests:** Test with actual embedding service
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for service code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Vector generation cost | LOW | Batch generation option |
| Stale vectors | LOW | Regenerate on profile update |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] CRUD methods for profiles
- [ ] Auto-vector generation on create/update
- [ ] ATECO validation
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-311: Studio API Endpoints

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Frontend needs REST API endpoints to manage studios. Must follow existing API patterns in `app/api/v1/`.

**Solution:**
Create Studio router with CRUD endpoints following FastAPI patterns.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-308 (StudioService)
- **Unlocks:** DEV-315 (User-Studio), Frontend integration

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Unauthorized: HTTP 401, `"Autenticazione richiesta"`
- Studio not found: HTTP 404, `"Studio non trovato"`
- Duplicate slug: HTTP 409, `"Slug già in uso"`
- Validation error: HTTP 422, field-specific messages
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- All endpoints: <200ms
- Get current studio: <100ms

**Edge Cases:**
- **Empty Body:** PATCH with empty body → HTTP 400, `"Nessun campo da aggiornare"`
- **Malformed UUID:** Invalid UUID in path → HTTP 422, `"ID non valido"`
- **Already Deleted:** DELETE on soft-deleted studio → HTTP 204 (idempotent)
- **Concurrent Delete:** DELETE during active update → update fails with 404
- **User Without Studio:** GET current studio when none exists → HTTP 404, `"Nessuno studio associato"`
- **Null Fields:** Null values in PATCH → interpreted as "remove field" (JSONB merge)

**File:** `app/api/v1/studio.py`

**Endpoints:**
- `POST /api/v1/studio` - Create studio
- `GET /api/v1/studio` - Get current user's studio
- `GET /api/v1/studio/{studio_id}` - Get studio by ID
- `PATCH /api/v1/studio/{studio_id}` - Update studio
- `DELETE /api/v1/studio/{studio_id}` - Delete studio

**Testing Requirements:**
- **TDD:** Write `tests/api/test_studio_api.py` FIRST
- **Unit Tests:** N/A (API tests are integration)
- **Integration Tests:** `tests/api/test_studio_api.py`
  - `test_create_studio_201` - successful creation
  - `test_create_studio_401_unauthorized` - auth required
  - `test_create_studio_422_validation` - invalid data
  - `test_get_studio_200` - successful get
  - `test_get_studio_404` - not found
  - `test_update_studio_200` - successful update
  - `test_delete_studio_204` - successful delete
- **Edge Case Tests:**
  - `test_patch_empty_body` - HTTP 400
  - `test_path_invalid_uuid` - HTTP 422
  - `test_delete_already_deleted` - HTTP 204 (idempotent)
  - `test_get_current_no_studio` - HTTP 404
  - `test_patch_null_removes_field` - JSONB merge behavior
  - `test_concurrent_delete_update` - update gets 404
- **E2E Tests:** `tests/e2e/test_studio_flow.py`
  - Full CRUD flow
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/` to ensure no API conflicts
- **Coverage Target:** 80%+ for API code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Unauthorized access | HIGH | Auth dependency on all routes |
| Missing validation | MEDIUM | Pydantic request schemas |
| Concurrent operations | LOW | Optimistic locking via version field |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All CRUD endpoints implemented
- [ ] Authentication required
- [ ] Pydantic request/response schemas
- [ ] OpenAPI documentation
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-312: Client API Endpoints

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Figma Reference:** `ClientListPage.tsx` + `ClientDetailPage.tsx` — Source: [`docs/figma-make-references/ClientListPage.tsx`](../figma-make-references/ClientListPage.tsx), [`docs/figma-make-references/ClientDetailPage.tsx`](../figma-make-references/ClientDetailPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Frontend needs REST API endpoints to manage clients with pagination, filtering, and proper error handling for business rules (100 limit, validation).

**Solution:**
Create Client router with CRUD endpoints and list with pagination.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-309 (ClientService), DEV-310 (ClientProfileService)
- **Unlocks:** DEV-313 (Import), DEV-314 (Export), Frontend integration

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Unauthorized: HTTP 401, `"Autenticazione richiesta"`
- Client not found: HTTP 404, `"Cliente non trovato"`
- Studio limit: HTTP 400, `"Raggiunto limite di 100 clienti"`
- Invalid CF: HTTP 422, `"Codice fiscale non valido"`
- Duplicate CF: HTTP 409, `"Cliente con questo CF già presente"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- List clients (page): <100ms
- Create/Update: <200ms
- Get single client: <50ms

**Edge Cases:**
- **Pagination Bounds:** page≤0 → page=1; size≤0 → size=20; size>100 → size=100
- **Empty List:** Empty studio returns `{"items": [], "total": 0, "page": 1}`
- **Filter Injection:** SQL/NoSQL injection in filters → sanitized, not errored
- **Empty PATCH:** PATCH with no changes → HTTP 200 (no-op), not error
- **Duplicate CF Across Studios:** Same CF allowed in different studios (isolated)
- **Delete + List Race:** Deleted client appears in list until cache refresh (<5s)
- **Profile Partial:** Client without profile still listable; profile returned as null

**File:** `app/api/v1/clients.py`

**Endpoints:**
- `POST /api/v1/clients` - Create client
- `GET /api/v1/clients` - List clients (paginated)
- `GET /api/v1/clients/{client_id}` - Get client
- `PATCH /api/v1/clients/{client_id}` - Update client
- `DELETE /api/v1/clients/{client_id}` - Delete client

**Testing Requirements:**
- **TDD:** Write `tests/api/test_client_api.py` FIRST
- **Integration Tests:** `tests/api/test_client_api.py`
  - `test_create_client_201` - successful creation
  - `test_create_client_400_limit_exceeded` - 100 limit error
  - `test_create_client_422_invalid_cf` - CF validation error
  - `test_list_clients_200_paginated` - pagination
  - `test_list_clients_200_filtered` - filtering
  - `test_get_client_404_wrong_studio` - tenant isolation
  - `test_update_client_200` - successful update
  - `test_delete_client_204` - soft delete
- **Edge Case Tests:**
  - `test_list_page_zero` - normalizes to page 1
  - `test_list_size_exceeds_max` - capped at 100
  - `test_list_empty_studio` - returns empty array, not error
  - `test_filter_sql_injection` - sanitized safely
  - `test_patch_no_changes` - HTTP 200 no-op
  - `test_same_cf_different_studios` - allowed
  - `test_client_without_profile` - profile=null in response
- **E2E Tests:** `tests/e2e/test_client_crud_flow.py`
  - Create → Read → Update → Delete flow
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/` and `pytest tests/security/`
- **Coverage Target:** 80%+ for API code, 95%+ for tenant isolation

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Pagination performance | MEDIUM | Keyset pagination for large sets |
| Filter injection | LOW | Pydantic validation + sanitization |
| Cache staleness | LOW | 5s cache TTL for list operations |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All CRUD endpoints implemented
- [ ] Pagination with filters
- [ ] Clear error messages for limit/validation
- [ ] Tenant isolation enforced
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-313: Client Import from Excel/PDF

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Figma Reference:** `ClientImportPage.tsx` (3-step wizard) — Source: [`docs/figma-make-references/ClientImportPage.tsx`](../figma-make-references/ClientImportPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 6h | **Status:** NOT STARTED

**Problem:**
Studios have existing client lists in various formats. Some accounting software (e.g., legacy systems) only export to PDF, not Excel/CSV. Manual entry of 100 clients is tedious. Need bulk import supporting multiple formats with validation and error reporting.

**Solution:**
Create import service supporting both Excel (openpyxl) and PDF (using existing document parsing from `app/services/document_processor.py`). Use LLM-assisted extraction for PDF tables. Validate all rows before insert, rollback on any error, return detailed import report.

**Agent Assignment:** @Ezio (primary), @Mario (template design), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-309 (ClientService), DEV-312 (Client API)
- **Unlocks:** None (leaf task)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid file format: HTTP 415, `"Formato file non supportato. Usa Excel (.xlsx) o PDF"`
- Parse error: HTTP 422, `"Impossibile leggere il file: [dettaglio]"`
- Validation errors: HTTP 422, row-by-row errors in response body
- Studio limit exceeded: HTTP 400, `"Import supera limite di 100 clienti"`
- Partial failure: HTTP 422, `"Import fallito: nessun cliente importato"` (atomic)
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Excel parse (100 rows): <5s
- PDF parse (10 pages): <30s (LLM involved)
- Validation: <2s for 100 clients
- Import transaction: <10s for 100 clients

**Edge Cases:**
- **Empty File:** 0 rows in Excel or empty PDF → HTTP 422, `"File vuoto"`
- **Headers Only:** Excel with headers but no data rows → HTTP 422, `"Nessun dato trovato"`
- **Duplicate CFs:** Same CF appears twice in file → reject entire file, list duplicates
- **CF Exists in DB:** Client CF already exists in studio → skip row with warning, not error
- **Mixed Encoding:** Excel with non-UTF8 encoding → detect and convert, warn if conversion lossy
- **Exactly 100 Limit:** Import 100 when studio has 0 → success; import 1 when studio has 100 → reject
- **Large File:** >5MB Excel or >50 pages PDF → HTTP 413, `"File troppo grande"`
- **Malformed PDF:** Scanned image without OCR text → use LLM vision, warn about accuracy

**File:** `app/services/client_import_service.py`

**Supported Formats:**
- Excel (.xlsx, .xls) - structured parsing with openpyxl
- PDF (.pdf) - table extraction using existing document processor + LLM for unstructured PDFs

**Methods:**
- `detect_format(file)` - Detect file format and route to appropriate parser
- `validate_file(file)` - Validate without importing (format-agnostic)
- `parse_excel(file)` - Parse Excel to client data
- `parse_pdf(file)` - Parse PDF tables to client data (uses LLM for extraction)
- `import_clients(studio_id, file)` - Import with transaction
- `get_template()` - Return empty Excel template

**Testing Requirements:**
- **TDD:** Write `tests/services/test_client_import_service.py` FIRST
- **Unit Tests:**
  - `test_detect_format_excel` - Excel format detected
  - `test_detect_format_pdf` - PDF format detected
  - `test_validate_excel_valid` - valid Excel file passes
  - `test_validate_pdf_valid` - valid PDF file passes
  - `test_validate_invalid_cf` - CF errors detected (both formats)
  - `test_validate_missing_required` - required field errors
  - `test_parse_pdf_table_extraction` - PDF table parsed correctly
  - `test_parse_pdf_llm_fallback` - LLM extraction for unstructured PDFs
  - `test_import_clients_success` - all rows imported
  - `test_import_clients_rollback` - transaction rollback on error
  - `test_import_clients_limit_check` - respects 100 limit
  - `test_get_template` - template has correct columns
- **Integration Tests:** `tests/services/test_client_import_integration.py`
  - Test with real Excel files
  - Test with real PDF files (tabular and unstructured)
  - Database transaction testing
- **E2E Tests:** `tests/e2e/test_client_import_flow.py`
  - Upload Excel → Validate → Import → Verify flow
  - Upload PDF → Validate → Import → Verify flow
- **Edge Case Tests:**
  - `test_import_empty_file_rejected` - empty file error
  - `test_import_headers_only_rejected` - no data rows error
  - `test_import_duplicate_cfs_rejected` - duplicates listed
  - `test_import_existing_cf_skipped` - existing CF warning not error
  - `test_import_encoding_conversion` - non-UTF8 handled
  - `test_import_exactly_100_limit` - boundary condition
  - `test_import_large_file_rejected` - size limit enforced
  - `test_import_scanned_pdf_llm_vision` - OCR fallback works
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for import code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Partial import | HIGH | All-or-nothing transaction |
| Memory on large files | MEDIUM | Streaming parser |
| Encoding issues | LOW | Force UTF-8, handle BOM |
| PDF extraction errors | MEDIUM | LLM fallback for unstructured PDFs |
| PDF table misalignment | MEDIUM | Preview & confirm step before import |
| LLM cost for PDF parsing | LOW | Cache extracted data, ~$0.01/page |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Parse Excel template (.xlsx, .xls)
- [ ] Parse PDF files with tabular data
- [ ] LLM-assisted extraction for unstructured PDFs
- [ ] Preview extracted data before import
- [ ] Validate all rows before import
- [ ] Batch insert with transaction
- [ ] Return detailed import report (success/errors per row)
- [ ] Enforce 100 client limit
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-314: Client Export to Excel

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Figma Reference:** `ClientListPage.tsx` (export button in bulk actions) — Source: [`docs/figma-make-references/ClientListPage.tsx`](../figma-make-references/ClientListPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
GDPR requires data portability - users must be able to export their data. Studios need to export client lists.

**Solution:**
Create export service generating Excel file with all client data (decrypted for export).

**Agent Assignment:** @Ezio (primary), @Severino (GDPR review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-309 (ClientService)
- **Unlocks:** DEV-317 (GDPR Deletion - uses export for portability)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- No clients to export: HTTP 204, no content
- Export generation failure: HTTP 500, `"Errore generazione export"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Export 100 clients: <5s
- File generation: async with progress if >10s

**Edge Cases:**
- **Zero Clients:** Studio with 0 clients → HTTP 204, no file generated
- **Deleted Clients:** Soft-deleted clients excluded from export unless ?include_deleted=true
- **Decryption Failure:** CF decryption fails → log error, export with [DECRYPTION_ERROR] placeholder
- **Large Export:** >1000 clients → async job with download link
- **Concurrent Exports:** Same user requests export twice → return cached file if <5min old
- **Special Characters:** Client names with Unicode → ensure UTF-8 BOM in Excel
- **GDPR Single Export:** Export single client includes all related data (communications, deadlines)

**File:** `app/services/client_export_service.py`

**Methods:**
- `export_clients(studio_id)` - Export all clients to Excel
- `export_client(client_id)` - Export single client (for GDPR)

**Testing Requirements:**
- **TDD:** Write `tests/services/test_client_export_service.py` FIRST
- **Unit Tests:**
  - `test_export_clients_success` - exports all clients
  - `test_export_clients_decrypted` - PII decrypted in export
  - `test_export_client_single` - single client export
  - `test_export_audit_logged` - export action logged
- **Integration Tests:** Verify Excel file can be opened
- **Edge Case Tests:**
  - `test_export_zero_clients_204` - empty studio no file
  - `test_export_excludes_deleted` - soft deleted excluded
  - `test_export_decryption_failure_placeholder` - graceful degradation
  - `test_export_large_async` - async for large exports
  - `test_export_cached_recent` - cache hit within 5min
  - `test_export_unicode_utf8_bom` - special chars handled
  - `test_gdpr_export_includes_related` - all related data included
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/` and `pytest tests/gdpr/`
- **Coverage Target:** 80%+ for export code, 95%+ for GDPR compliance

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| PII in export | HIGH | Audit log the export |
| Large exports | LOW | Streaming response |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Export to Excel format
- [ ] Include all client + profile data
- [ ] Audit log the export
- [ ] GDPR data portability compliance
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-315: User-Studio Association

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Existing `User` model has no `studio_id`. Need to modify production table to add FK. This is a BREAKING CHANGE affecting all existing users.

**Solution:**
Add nullable `studio_id` FK to User model. Migration creates column as nullable. Auto-create studio for existing users.

**Agent Assignment:** @Primo (primary), @Ezio (migration), @Severino (security)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model), DEV-307 (Migration), DEV-308 (StudioService)
- **Unlocks:** DEV-316 (Tenant Middleware), All multi-tenant features

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/models/user.py`
- **Affected Files:**
  - `app/services/auth_service.py` (uses User model)
  - `app/api/v1/endpoints/auth.py` (registration flow)
  - `alembic/versions/` (migration required)
- **Related Tests:**
  - `tests/models/test_user.py` (direct)
  - `tests/api/test_auth.py` (consumer)
- **Baseline Command:** `pytest tests/models/test_user.py tests/api/test_auth.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing User model reviewed
- [ ] Auth flow documented

**Error Handling:**
- User without studio accessing client features: HTTP 403, `"Associazione studio richiesta"`
- Invalid studio_id assignment: HTTP 400, `"Studio non trovato"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Add studio_id column: <1s (ALTER TABLE)
- Auto-create studio migration: <5s for 1000 existing users
- FK lookup on login: <10ms

**Edge Cases:**
- **Existing Users:** Migration finds user without studio → auto-create personal studio
- **Concurrent Migration:** Multiple pods running migration → only first creates studio (DB constraint)
- **Orphaned Studio:** User deleted but studio remains → cascade delete or transfer ownership
- **Multiple Users Future:** Same studio_id for two users → allowed for future multi-operator
- **Null studio_id Access:** User with null studio_id → allowed for backwards compat, limited features
- **Studio Reassignment:** User moved to different studio → clear caches, update JWT on next login

**File:** `app/models/user.py` (MODIFY)

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:** `tests/models/test_user_studio.py`
  - `test_user_studio_id_nullable` - FK is nullable
  - `test_user_with_studio` - user with studio works
  - `test_user_without_studio` - user without studio works (backward compat)
- **Integration Tests:** `tests/migrations/test_user_studio_migration.py`
  - `test_migration_adds_column` - column added
  - `test_migration_existing_users` - studios created for existing users
  - `test_migration_rollback` - can rollback safely
- **Edge Case Tests:**
  - `test_existing_user_auto_studio` - migration creates personal studio
  - `test_concurrent_migration_safe` - DB constraint prevents duplicates
  - `test_orphaned_studio_cascade` - user deletion cascades
  - `test_multiple_users_same_studio` - future multi-operator allowed
  - `test_null_studio_backwards_compat` - null studio limited features
  - `test_studio_reassignment_cache_clear` - cache cleared on move
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:**
  - Run `pytest tests/models/test_user.py` - existing user tests pass
  - Run `pytest tests/api/` - existing auth still works
- **Coverage Target:** 95%+ for migration code (critical)

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing users broken | HIGH | Nullable FK, gradual migration |
| Migration failure | HIGH | Test on staging, backup |
| Orphaned users | MEDIUM | Script to create studios |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Add studio_id FK (nullable)
- [ ] Migration for existing users
- [ ] Auto-create studio on registration
- [ ] Backward compatible
- [ ] 95%+ test coverage for migration
- [ ] All existing tests still pass (regression)

---

### DEV-316: Tenant Context Middleware

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Every request needs the current user's `studio_id` for tenant isolation. Extracting this repeatedly in every endpoint is error-prone.

**Solution:**
Create middleware that extracts `studio_id` from JWT and sets it in request state. Services can access via dependency injection.

**Agent Assignment:** @Ezio (primary), @Severino (security review)

**Dependencies:**
- **Blocking:** DEV-315 (User-Studio Association)
- **Unlocks:** All multi-tenant service operations

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Missing studio_id in JWT: HTTP 403, `"Contesto studio non disponibile"`
- Invalid studio_id: HTTP 403, `"Studio non valido"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Middleware overhead: <1ms per request

**Edge Cases:**
- **Expired JWT:** Token expired → HTTP 401 before middleware executes
- **No Studio in JWT:** User logged in before studio association → HTTP 403 with helpful message
- **Studio Deleted:** studio_id in JWT but studio deleted → HTTP 403, `"Studio non più attivo"`
- **Multiple Studios Future:** User with multiple studios → use X-Studio-ID header override
- **Null studio_id Bypass:** Malformed JWT with null studio_id → reject, don't pass null
- **Middleware Order:** Runs after auth middleware, before route handlers
- **Public Endpoints:** Certain endpoints (docs, health) skip middleware entirely

**File:** `app/middleware/tenant_context.py`

**Testing Requirements:**
- **TDD:** Write `tests/middleware/test_tenant_context.py` FIRST
- **Unit Tests:**
  - `test_middleware_extracts_studio_id` - studio_id set from JWT
  - `test_middleware_no_user` - handles unauthenticated requests
  - `test_middleware_no_studio` - handles user without studio
  - `test_middleware_propagates` - studio_id available in request.state
- **Integration Tests:** `tests/middleware/test_tenant_context_integration.py`
  - Test with actual JWT tokens
  - Test with FastAPI dependencies
- **Edge Case Tests:**
  - `test_middleware_expired_jwt_401` - expired before middleware
  - `test_middleware_no_studio_403` - no studio helpful message
  - `test_middleware_deleted_studio_403` - deleted studio rejected
  - `test_middleware_null_studio_rejected` - null bypass blocked
  - `test_middleware_public_endpoints_skip` - public endpoints work
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/` - all endpoints still work
- **Coverage Target:** 95%+ for middleware code (security critical)

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing studio_id | HIGH | Explicit error for None |
| Performance | LOW | Cache user lookup |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Extract studio_id from JWT
- [ ] Set context for RLS (when enabled)
- [ ] Dependency for services to access
- [ ] Error handling for missing studio
- [ ] 95%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-317: Client GDPR Deletion

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Figma Reference:** `ClientDetailPage.tsx` (delete action) — Source: [`docs/figma-make-references/ClientDetailPage.tsx`](../figma-make-references/ClientDetailPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
GDPR requires right to erasure. When a client requests deletion, all their data must be removed or anonymized, including related communications.

**Solution:**
Create GDPR deletion service using existing patterns from `app/services/gdpr_deletion_service.py`. Soft delete with anonymization, cascade to communications.

**Agent Assignment:** @Ezio (primary), @Severino (GDPR review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-309 (ClientService), DEV-314 (Client Export - for data portability before deletion)
- **Unlocks:** None (end of GDPR chain)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Client not found: HTTP 404, `"Cliente non trovato"`
- Unauthorized deletion: HTTP 403, `"Non autorizzato a eliminare questo cliente"`
- Deletion in progress: HTTP 409, `"Eliminazione già in corso"`
- Cascade failure: HTTP 500, `"Errore durante eliminazione dati correlati"` + transaction rollback
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- GDPR deletion (single client): <3s
- Anonymization: <1s
- Audit log write: <100ms

**Edge Cases:**
- **Already Deleted:** Deletion request on already-deleted client → HTTP 200 (idempotent)
- **Concurrent Deletion:** Two simultaneous deletion requests → first succeeds, second gets 409
- **Partial Cascade Failure:** Communications delete fails → rollback client deletion too
- **Pending Communications:** Client has PENDING_REVIEW communications → reject deletion, list blockers
- **Export First:** GDPR best practice → suggest export before deletion, not enforced
- **Undo Period:** Soft delete for 30 days before hard delete → reactivation possible
- **Vector Deletion:** Client profile vectors must also be removed from pgvector index
- **Anonymous Audit:** Audit trail after deletion contains anonymized UUID, not PII

**File:** `app/services/client_gdpr_service.py`

**Methods:**
- `delete_client_gdpr(client_id, studio_id)` - Full GDPR deletion
- `anonymize_client(client_id)` - Anonymize without delete

**Testing Requirements:**
- **TDD:** Write `tests/services/test_client_gdpr_service.py` FIRST
- **Unit Tests:**
  - `test_delete_gdpr_soft_delete` - sets deleted_at
  - `test_delete_gdpr_anonymizes_pii` - PII replaced with [DELETED]
  - `test_delete_gdpr_cascades_communications` - related data deleted
  - `test_delete_gdpr_audit_logged` - action logged
  - `test_anonymize_preserves_structure` - non-PII preserved
- **Integration Tests:** `tests/services/test_client_gdpr_integration.py`
  - Full deletion flow
  - Verify audit trail
- **Edge Case Tests:**
  - `test_delete_already_deleted_idempotent` - re-delete succeeds
  - `test_delete_concurrent_409` - concurrent blocked
  - `test_delete_cascade_rollback` - partial failure rolls back
  - `test_delete_pending_communications_blocked` - blockers listed
  - `test_delete_undo_period_30_days` - reactivation works
  - `test_delete_removes_vectors` - pgvector cleanup
  - `test_audit_anonymized_after_delete` - no PII in audit
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:**
  - Run `pytest tests/gdpr/` - existing GDPR tests pass
  - Run `pytest tests/services/` - no service conflicts
- **Coverage Target:** 95%+ for GDPR code (compliance critical)

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Incomplete deletion | CRITICAL | Transaction, verify all tables |
| Audit trail loss | MEDIUM | Keep anonymized audit |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Soft delete with anonymization
- [ ] CASCADE to communications
- [ ] Audit logging (without PII)
- [ ] Follows existing GDPR patterns
- [ ] 95%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-318: Unit Tests for Phase 1 Services

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Phase 1 services need comprehensive unit tests to ensure business logic works correctly and prevent regressions.

**Solution:**
Create unit tests for all Phase 1 services with 80%+ coverage target.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-308 (StudioService), DEV-309 (ClientService), DEV-310 (ClientProfileService), DEV-313 (Import), DEV-314 (Export), DEV-317 (GDPR) - all Phase 1 services
- **Unlocks:** DEV-319 (Integration Tests), Phase 2 start

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**Files:**
- `tests/services/test_studio_service.py`
- `tests/services/test_client_service.py`
- `tests/services/test_client_profile_service.py`
- `tests/services/test_client_import_service.py`
- `tests/services/test_client_export_service.py`
- `tests/services/test_client_gdpr_service.py`

**Test Methods:**
- `test_studio_service_crud` - StudioService CRUD operations
- `test_studio_service_slug_validation` - Slug uniqueness and format
- `test_client_service_crud` - ClientService CRUD operations
- `test_client_service_limit_enforcement` - 100 client limit
- `test_client_service_cf_piva_validation` - CF/P.IVA format validation
- `test_client_service_tenant_isolation` - Cross-studio access prevention
- `test_client_profile_service_crud` - ClientProfileService operations
- `test_client_profile_service_vector_generation` - Auto-vector on create/update
- `test_client_import_service_excel` - Excel file parsing and import
- `test_client_import_service_pdf` - PDF table extraction and import
- `test_client_import_service_validation` - Row-level validation errors
- `test_client_export_service_excel` - Excel export generation
- `test_client_export_service_gdpr` - GDPR data portability export
- `test_client_gdpr_service_deletion` - Soft delete with anonymization
- `test_client_gdpr_service_cascade` - CASCADE to related entities

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **Unit Tests:** See individual service tasks for test cases
- **Test Categories:**
  - CRUD operations (happy path)
  - Business rule enforcement (100 limit, validation)
  - Tenant isolation
  - Error handling
  - Edge cases
- **Coverage Target:** 80%+ per service, 95%+ for security-critical

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] All services have unit tests
- [ ] 80%+ coverage per service
- [ ] Business rules tested
- [ ] Error conditions tested
- [ ] Edge cases covered

---

### DEV-319: Integration Tests for Client APIs

**Reference:** [FR-002: Database Clienti dello Studio](./PRATIKO_2.0_REFERENCE.md#fr-002-database-clienti-dello-studio)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
API endpoints need integration tests verifying full request/response cycle including authentication, validation, and database operations.

**Solution:**
Create integration tests using pytest-asyncio and httpx test client.

**Agent Assignment:** @Clelia (primary), @Ezio (support)

**Dependencies:**
- **Blocking:** DEV-311 (Studio API), DEV-312 (Client API), DEV-318 (Unit Tests)
- **Unlocks:** Phase 2 start (all Phase 1 complete)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `tests/api/test_client_api.py`

**Test Methods:**
- `test_create_client_201_success` - Valid client creation returns 201
- `test_create_client_400_limit_exceeded` - Rejects when 100 client limit reached
- `test_create_client_422_invalid_cf` - Rejects invalid codice fiscale format
- `test_create_client_409_duplicate_cf` - Rejects duplicate CF in same studio
- `test_list_clients_200_paginated` - Returns paginated results
- `test_list_clients_200_filtered` - Filters by stato_cliente, tipo_cliente
- `test_get_client_200_success` - Returns client details
- `test_get_client_404_wrong_studio` - Returns 404 for other studio's client (not 403)
- `test_update_client_200_success` - Updates client fields
- `test_update_client_404_not_found` - Returns 404 for non-existent client
- `test_delete_client_204_success` - Soft deletes client
- `test_import_excel_201_success` - Imports valid Excel file
- `test_import_excel_422_validation_errors` - Returns row-level errors
- `test_import_pdf_201_success` - Imports valid PDF with tables
- `test_export_excel_200_success` - Exports clients to Excel
- `test_export_excel_204_empty` - Returns 204 when no clients to export

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **Integration Tests:**
  - Create client (success, validation error, limit exceeded)
  - List clients (pagination, filters, empty)
  - Update client (success, not found, unauthorized)
  - Delete client (success, not found)
  - Import from Excel (success, validation errors)
  - Export to Excel
- **E2E Tests:** `tests/e2e/test_client_crud_flow.py`
  - Full user journey from login to client management
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Verify no existing API tests broken
- **Coverage Target:** 80%+ for API endpoints

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] All CRUD endpoints tested
- [ ] Authorization checks verified
- [ ] Import/export flows tested
- [ ] Error responses validated
- [ ] E2E flow tested

---

## Phase 2: Matching Engine (Week 5-6) - 10 Tasks

### DEV-320: NormativeMatchingService

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Need to automatically identify which clients are affected by regulations. Must match client profiles against knowledge items using structured criteria (regime, ATECO) and optionally semantic similarity.

**Solution:**
Create `NormativeMatchingService` with hybrid matching: first structured (fast, explainable), then semantic fallback for ambiguous cases.

**Agent Assignment:** @Ezio (primary), @Mario (rule logic), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-302 (ClientProfile), DEV-309 (ClientService), DEV-321 (Matching Rules), DEV-322 (Vector Generation)
- **Unlocks:** DEV-323 (LangGraph Node), DEV-325 (Background Job), DEV-328 (Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- No clients in studio: Return empty matches (not error)
- Invalid knowledge_item_id: HTTP 404, `"Normativa non trovata"`
- Matching timeout: HTTP 408, `"Timeout durante matching"` + partial results
- Vector index unavailable: Fallback to structured-only matching
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Match 100 clients: <5s
- Structured query: <50ms
- Semantic fallback: <200ms per client
- Background job throughput: 1000 clients/second

**Edge Cases:**
- **Null Criteria:** Client with null ATECO/regime → falls through all structured rules, semantic fallback used
- **Stale Vectors:** Profile updated but vector not regenerated → log warning, use stale vector with flag
- **Vector Index Down:** pgvector unavailable → structured-only mode, no semantic fallback
- **Empty Rules:** No matching rules for knowledge item → return empty matches (not error)
- **Score Ties:** Multiple rules match with same score → order by rule priority, then alphabetical
- **Batch Crash Recovery:** Background job crashes mid-batch → resume from last checkpoint (stored in Redis)
- **Concurrent Matching:** Same regulation matched twice → idempotent (upsert ProactiveSuggestion)
- **Zero Clients:** Studio with 0 clients → return empty matches, log info

**File:** `app/services/normative_matching_service.py`

**Methods:**
- `match_regulation(knowledge_item_id)` - Match single regulation against all clients
- `match_client(client_id)` - Find regulations for single client
- `get_suggestions(studio_id)` - Get proactive suggestions for studio
- `daily_scan()` - Batch match new regulations

**Testing Requirements:**
- **TDD:** Write `tests/services/test_normative_matching_service.py` FIRST
- **Unit Tests:**
  - `test_match_regulation_forfettario` - matches forfettario clients
  - `test_match_regulation_no_match` - returns empty for no matches
  - `test_match_client_multiple` - client matches multiple regulations
  - `test_match_score_calculation` - scores calculated correctly
  - `test_match_structured_criteria` - ATECO, regime filtering
  - `test_match_semantic_fallback` - vector similarity used when needed
- **Edge Case Tests:**
  - `test_client_null_ateco` - uses semantic fallback
  - `test_stale_vector_warning` - logs warning, continues with stale
  - `test_vector_index_unavailable` - structured-only mode
  - `test_empty_rules` - returns empty matches
  - `test_score_tie_ordering` - priority then alphabetical
  - `test_batch_crash_recovery` - resumes from checkpoint
  - `test_concurrent_match_idempotent` - upsert behavior
  - `test_zero_clients_studio` - returns empty, no error
- **Integration Tests:** `tests/services/test_matching_integration.py`
  - Test with real knowledge items
  - Test with real client profiles
- **Performance Tests:** `tests/performance/test_matching_performance.py`
  - 100 clients in <5s
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for matching logic

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives | MEDIUM | Threshold tuning, user feedback |
| Performance | MEDIUM | Index on criteria fields |
| Missing matches | HIGH | Semantic fallback |
| Stale vectors | MEDIUM | Regeneration on profile update + warning flag |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Match clients against knowledge items
- [ ] Use ATECO, regime, CCNL for filtering
- [ ] Calculate match scores
- [ ] <5s for 100 clients
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-321: Pre-configured Matching Rules (15 rules)

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Matching engine needs rules to identify client-regulation matches. For MVP, these are pre-configured (not user-defined) to reduce complexity.

**Solution:**
Define 15 matching rules covering common scenarios and seed via migration.

**Agent Assignment:** @Mario (primary), @Primo (migration)

**Dependencies:**
- **Blocking:** DEV-304 (MatchingRule model), DEV-307 (Migration)
- **Unlocks:** DEV-320 (NormativeMatchingService)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`
**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/data/matching_rules.json`

**Error Handling:**
- Invalid JSON schema: Migration aborted, `"Schema regole non valido"`
- Duplicate rule name: Migration aborted, `"Nome regola duplicato: {name}"`
- Missing required fields: Migration aborted, `"Campi obbligatori mancanti: {fields}"`
- **Logging:** All errors MUST be logged with context at ERROR level

**Performance Requirements:**
- Migration execution: <30s
- Rule loading at startup: <500ms
- Rule validation: <100ms per rule

**Rules (15 total):**
1. **Rottamazione Quater** - regime_fiscale IN [FORFETTARIO, ORDINARIO]
2. **Bonus Sud Assunzioni** - regione IN [southern regions]
3. **Bonus Under 30** - tipo_cliente = AZIENDA AND n_dipendenti > 0
4. **CCNL Metalmeccanici** - ccnl = "METALMECCANICI"
5. **Regime Forfettario Updates** - regime_fiscale = FORFETTARIO
6. **Contributi INPS Artigiani** - codice_ateco LIKE '43.%'
7. **IVA Edilizia** - codice_ateco IN [construction codes]
8. **Agevolazioni Startup** - data_inizio_attivita > 2 years ago
9. **Obblighi Fatturazione Elettronica** - all businesses
10. **Scadenze IMU** - tipo_cliente = PERSONA_FISICA AND immobili IS NOT NULL
11. **CCNL Edilizia** - ccnl = "EDILIZIA" OR codice_ateco LIKE '41.%' OR '42.%' OR '43.%'
12. **Agevolazione Prima Casa** - tipo_cliente = PERSONA_FISICA AND immobili.tipo = "ABITAZIONE_PRINCIPALE"
13. **NASPI Disoccupazione** - tipo_cliente = PERSONA_FISICA (general info)
14. **Bonus Mamme Lavoratrici** - tipo_cliente IN [DITTA_INDIVIDUALE, AZIENDA] AND n_dipendenti > 0
15. **Esonero Contributivo Giovani** - tipo_cliente = AZIENDA AND n_dipendenti > 0

**Methods:**
- `load_rules()` - Load rules from JSON file
- `validate_rule(rule)` - Validate rule structure and conditions
- `seed_rules(session)` - Insert rules into database via migration

**Testing Requirements:**
- **TDD:** Write rule tests FIRST
- **Unit Tests:** `tests/data/test_matching_rules.py`
  - `test_rules_json_valid` - JSON schema valid
  - `test_rules_all_have_conditions` - all rules have conditions
  - `test_rules_priority_unique` - no duplicate priorities
  - `test_rule_rottamazione_matches` - specific rule testing
  - `test_rule_bonus_sud_matches` - region matching
- **Integration Tests:** Test rules against sample clients
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/test_normative_matching_service.py`
- **Coverage Target:** 100% for rule definitions

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Outdated rules | MEDIUM | valid_from/valid_to dates |
| Missing scenarios | LOW | Iterate based on feedback |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] 15 rules defined in JSON
- [ ] Migration to seed rules
- [ ] Each rule has valid_from date
- [ ] Rules tested against sample clients
- [ ] All existing tests still pass (regression)

---

### DEV-322: Client Profile Vector Generation

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Semantic matching requires embedding vectors for client profiles. Need to generate 1536-dim vectors from profile text (regime, ATECO description, etc.).

**Solution:**
Create embedding service using existing LLM infrastructure. Generate vector when profile is created/updated.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-302 (ClientProfile with profile_vector column), DEV-307 (HNSW index migration)
- **Unlocks:** DEV-320 (NormativeMatchingService - semantic fallback)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
**Error Handling:**
- Embedding API failure: HTTP 503, `"Servizio embedding non disponibile"` + use stale vector
- Invalid profile data: Skip vector generation, log warning
- Rate limit exceeded: Exponential backoff, retry up to 3 times
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Single vector generation: <500ms
- Batch generation (100 profiles): <30s
- Cost tracking: ~$0.0001 per profile

**Edge Cases:**
- **Empty Profile:** Profile with all null fields → generate vector from studio name only
- **API Timeout:** OpenAI timeout → retry 3x, use stale vector, flag for regeneration
- **Rate Limit:** 429 from OpenAI → exponential backoff, batch continues after delay
- **Invalid Dimension:** API returns wrong dimension → reject, log error, use stale
- **Batch Partial Failure:** 50/100 succeed → commit successful, queue failed for retry
- **Profile Update:** Only regenerate if embeddable fields changed (skip pure metadata updates)
- **Cost Spike:** Daily cost > $1 → alert, continue processing
- **Stale Vector Flag:** Vector older than 30 days → queue for background refresh

**File:** `app/services/profile_embedding_service.py`

**Methods:**
- `generate_profile_vector(client_profile)` - Generate embedding
- `batch_generate_vectors(studio_id)` - Batch generation
- `profile_to_text(profile)` - Convert profile to embeddable text

**Testing Requirements:**
- **TDD:** Write `tests/services/test_profile_embedding_service.py` FIRST
- **Unit Tests:**
  - `test_profile_to_text_format` - correct text format
  - `test_generate_vector_dimension` - 1536 dimensions
  - `test_generate_vector_deterministic` - same input = similar output
  - `test_batch_generate_all_profiles` - batch processing
- **Edge Case Tests:**
  - `test_empty_profile_studio_only` - null fields use studio name
  - `test_api_timeout_retry` - retry on timeout, use stale
  - `test_rate_limit_backoff` - exponential backoff works
  - `test_invalid_dimension_rejected` - wrong dimension logged
  - `test_batch_partial_failure` - successful committed
  - `test_skip_unchanged_profile` - metadata-only skipped
  - `test_stale_vector_flagged` - old vectors queued
- **Integration Tests:** Test with actual embedding API (mocked for unit)
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for embedding code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Embedding cost | LOW | ~$0.0001 per profile |
| Vector staleness | LOW | Regenerate on update |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Generate embedding from profile text
- [ ] Store in profile_vector column
- [ ] Batch generation for imports
- [ ] Cost tracking
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-323: LangGraph Matching Node

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
During chat, when user asks about a regulation, we should automatically identify which of their clients might be affected. This enriches the response with proactive suggestions.

**Solution:**
Create LangGraph node inserted after domain classification (step 35). Query client database for matches and add to RAGState.

**Agent Assignment:** @Ezio (primary), @Severino (review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-320 (NormativeMatchingService), DEV-316 (Tenant Middleware - for studio_id)
- **Unlocks:** DEV-327 (Response Enrichment), DEV-328 (Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/core/langgraph/graph.py`
- **Affected Files:**
  - `app/core/langgraph/nodes/` (existing node patterns)
  - `app/schemas/rag_state.py` (adds matched_clients to state)
- **Related Tests:**
  - `tests/langgraph/test_graph.py` (direct)
  - `tests/integration/test_rag_pipeline.py` (consumer)
- **Baseline Command:** `pytest tests/langgraph/ -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing graph.py reviewed
- [ ] Node insertion point identified (after step 35)

**Error Handling:**
- Matching service timeout: Skip node, continue pipeline (graceful degradation)
- No studio_id in context: Skip node (user without studio)
- Database unavailable: Log error, continue pipeline without matches
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Node execution: <100ms added latency to pipeline
- Query extraction: <10ms
- Database query: <50ms

**Edge Cases:**
- **No Studio:** User without studio_id → skip node entirely, no error
- **Zero Clients:** Studio with 0 clients → skip matching, return empty
- **Service Timeout:** Matching service >100ms → skip, continue pipeline
- **Database Down:** DB unavailable → skip, continue without matches
- **Ambiguous Query:** Query without clear criteria → no matches, don't force
- **Large Match Set:** >20 clients match → limit to top 10 by relevance
- **Feature Flag Off:** Matching disabled for studio → skip node
- **State Corruption:** Missing fields in RAGState → log, continue without crash

**File:** `app/core/langgraph/nodes/client_matching_node.py`

**Methods:**
- `match_clients_node(state)` - Main node entry point
- `should_match(state)` - Check if matching should run
- `extract_matching_criteria(state)` - Extract criteria from classification
- `limit_matches(matches, max_count)` - Limit to top N matches

**Testing Requirements:**
- **TDD:** Write `tests/langgraph/test_client_matching_node.py` FIRST
- **Unit Tests:**
  - `test_node_should_match_true` - matches when studio has clients
  - `test_node_should_match_false` - skips when no clients
  - `test_node_extracts_criteria` - criteria from classification
  - `test_node_finds_matches` - matches added to state
  - `test_node_no_matches` - empty array when no matches
  - `test_node_latency` - <100ms execution
- **Edge Case Tests:**
  - `test_no_studio_skipped` - no studio_id continues cleanly
  - `test_zero_clients_empty` - empty studio returns []
  - `test_timeout_graceful_skip` - >100ms skipped
  - `test_db_down_continues` - DB failure doesn't crash pipeline
  - `test_ambiguous_query_no_force` - unclear query = no matches
  - `test_large_match_limit_10` - >20 matches trimmed
  - `test_feature_flag_off_skipped` - disabled flag skips
  - `test_state_corruption_logged` - missing fields handled
- **Integration Tests:** `tests/langgraph/test_matching_node_integration.py`
  - Test with real RAGState
  - Test pipeline integration
- **E2E Tests:** `tests/e2e/test_chat_with_matching.py`
  - Chat query → Matching → Response with suggestion
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:**
  - Run `pytest tests/langgraph/` - all pipeline tests pass
  - Run full RAG pipeline test suite
- **Coverage Target:** 80%+ for node, 95%+ for pipeline integration

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Pipeline regression | HIGH | Extensive testing |
| Latency increase | MEDIUM | Target <100ms added latency |
| Breaking changes | HIGH | Feature flag for rollout |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Insert after step 35 (domain classification)
- [ ] Query client database for matches
- [ ] Add matched_clients to RAGState
- [ ] <100ms added latency
- [ ] Feature flag for gradual rollout
- [ ] 80%+ test coverage achieved
- [ ] All existing pipeline tests pass (regression)

---

### DEV-324: Proactive Suggestion Model

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
When background job finds matches, need to store them as suggestions for professionals to review. Separate from communications which are for sending to clients.

**Solution:**
Create `ProactiveSuggestion` model to store matches found by background job.

**Agent Assignment:** @Primo (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model - FK), DEV-307 (Migration)
- **Unlocks:** DEV-325 (Background Matching Job), DEV-326 (Matching API)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)
**Error Handling:**
- Invalid suggestion data: HTTP 422, `"Dati suggerimento non validi"`
- Studio not found: HTTP 404, `"Studio non trovato"`
- Knowledge item not found: HTTP 404, `"Normativa di riferimento non trovata"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Suggestion creation: <100ms
- List suggestions: <50ms
- JSONB operations: <20ms
**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/proactive_suggestion.py`

**Fields:**
- `id`: UUID (primary key)
- `studio_id`: UUID (FK)
- `knowledge_item_id`: UUID (FK to knowledge_items)
- `matched_client_ids`: JSONB (array of client IDs)
- `match_score`: float
- `suggestion_text`: text
- `is_read`: bool
- `is_dismissed`: bool
- `created_at`: datetime

**Testing Requirements:**
- **TDD:** Write `tests/models/test_proactive_suggestion.py` FIRST
- **Unit Tests:**
  - `test_suggestion_creation` - valid creation
  - `test_suggestion_jsonb_client_ids` - JSONB array handling
  - `test_suggestion_read_status` - is_read toggle
  - `test_suggestion_dismissed_status` - is_dismissed toggle
  - `test_suggestion_fk_constraints` - FK to studio, knowledge_item
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/`
- **Coverage Target:** 80%+ for model code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Store match results
- [ ] Track read/dismissed status
- [ ] Link to knowledge item
- [ ] Multiple clients per suggestion
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-325: Background Matching Job

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
When new regulations are ingested via RSS, need to automatically scan all clients for matches. This should run asynchronously to not block ingestion.

**Solution:**
Create background job using FastAPI BackgroundTasks. Run after RSS ingestion completes.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-320 (NormativeMatchingService), DEV-324 (ProactiveSuggestion model)
- **Unlocks:** DEV-326 (Matching API - trigger endpoint), DEV-328 (Performance Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`
**Error Handling:**
- Job failure: Log error, retry up to 3 times with exponential backoff
- Partial failure: Continue with remaining items, report failures
- Database unavailable: Abort job, reschedule for next cycle
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Process 1000 clients/second
- Daily scan for 10K total clients: <10 minutes
- Memory usage: <500MB per job

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/jobs/matching_job.py`

**Methods:**
- `run_matching_job(knowledge_item_id)` - Match single regulation
- `daily_scan()` - Scan regulations from last 24h
- `full_scan(studio_id)` - Rescan all for a studio

**Testing Requirements:**
- **TDD:** Write `tests/jobs/test_matching_job.py` FIRST
- **Unit Tests:**
  - `test_matching_job_single_regulation` - matches one regulation
  - `test_matching_job_creates_suggestions` - ProactiveSuggestion created
  - `test_daily_scan_24h` - scans last 24h only
  - `test_full_scan_studio` - rescans all for studio
  - `test_matching_job_idempotent` - no duplicate suggestions
- **Integration Tests:** `tests/jobs/test_matching_job_integration.py`
  - Test with real database
  - Test with RSS ingestion trigger
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/jobs/` and `pytest tests/services/`
- **Coverage Target:** 80%+ for job code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Job failure | MEDIUM | Retry logic, monitoring |
| Duplicate matches | LOW | Upsert logic |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Scan new regulations against all clients
- [ ] Generate ProactiveSuggestion records
- [ ] Use FastAPI BackgroundTasks
- [ ] Logging and monitoring
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-326: Matching API Endpoints

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Figma Reference:** `MatchingNormativoPage.tsx` + `RisultatiMatchingNormativoPanel.tsx` — Source: [`docs/figma-make-references/MatchingNormativoPage.tsx`](../figma-make-references/MatchingNormativoPage.tsx), [`docs/figma-make-references/RisultatiMatchingNormativoPanel.tsx`](../figma-make-references/RisultatiMatchingNormativoPanel.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Frontend needs API to fetch suggestions, trigger manual matching, and mark suggestions as read/dismissed.

**Solution:**
Create Matching router with endpoints for suggestions management.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-320 (NormativeMatchingService), DEV-324 (ProactiveSuggestion model), DEV-325 (Background Job)
- **Unlocks:** DEV-329 (Unit Tests), Frontend integration
**Error Handling:**
- No suggestions: HTTP 200, empty array (not 404)
- Suggestion not found: HTTP 404, `"Suggerimento non trovato"`
- Unauthorized access: HTTP 403, `"Accesso non autorizzato"`
- Job already running: HTTP 409, `"Matching già in esecuzione"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- List suggestions: <100ms
- Trigger matching: <50ms (job queued async)
- Update suggestion: <50ms

**Edge Cases:**
- **Rapid Triggers:** POST /run while job running → HTTP 409 (not queue another)
- **Dismiss Dismissed:** PATCH to dismiss already-dismissed → HTTP 200 (idempotent)
- **Mark Read Twice:** PATCH to mark read again → HTTP 200 (idempotent)
- **Filter Combinations:** read=true AND dismissed=true → valid, returns both
- **Empty Client Matches:** Client with no matches → empty array (not 404)
- **Suggestion Deleted:** PATCH on deleted suggestion → HTTP 404
- **Pagination Empty:** page=5 when only 2 pages exist → empty items, correct total

**File:** `app/api/v1/matching.py`

**Endpoints:**
- `GET /api/v1/matching/suggestions` - List suggestions for studio
- `POST /api/v1/matching/run` - Trigger manual matching
- `PATCH /api/v1/matching/suggestions/{id}` - Update suggestion status
- `GET /api/v1/matching/client/{client_id}` - Get matches for client

**Testing Requirements:**
- **TDD:** Write `tests/api/test_matching_api.py` FIRST
- **Integration Tests:**
  - `test_list_suggestions_200` - returns suggestions
  - `test_list_suggestions_paginated` - pagination works
  - `test_list_suggestions_filtered` - read/unread filter
  - `test_trigger_matching_202` - job triggered
  - `test_update_suggestion_mark_read` - mark as read
  - `test_update_suggestion_dismiss` - dismiss suggestion
  - `test_get_client_matches_200` - matches for client
- **E2E Tests:** `tests/e2e/test_matching_flow.py`
  - Regulation → Match → Suggestion → Read flow
- **Edge Case Tests:**
  - `test_trigger_matching_while_running_409` - concurrent job rejected
  - `test_dismiss_already_dismissed_idempotent` - no error on re-dismiss
  - `test_mark_read_twice_idempotent` - no error on re-read
  - `test_filter_read_and_dismissed` - combined filters work
  - `test_client_no_matches_empty_array` - empty not 404
  - `test_patch_deleted_suggestion_404` - deleted suggestion rejected
  - `test_pagination_beyond_results_empty` - empty items, correct total
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 80%+ for API code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] List suggestions (paginated)
- [ ] Trigger manual matching
- [ ] Update suggestion status
- [ ] Filter by read/unread
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)

---

### DEV-327: Multi-Tenant Isolation Tests

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** CRITICAL | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Multi-tenancy is the highest security risk. Must verify that Studio A cannot access Studio B's data under any circumstance.

**Solution:**
Create comprehensive security tests covering all access patterns. Target 95%+ coverage of isolation logic.

**Agent Assignment:** @Severino (primary), @Clelia (support)

**Dependencies:**
- **Blocking:** DEV-309 (ClientService), DEV-316 (Tenant Middleware), DEV-320 (MatchingService)
- **Unlocks:** Production deployment (security gate)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Cross-tenant access attempt: HTTP 404, `"Risorsa non trovata"` (not 403 to avoid info leak)
- SQL injection attempt: HTTP 400, `"Parametri non validi"`
- Direct ID access: HTTP 404, `"Risorsa non trovata"`
- **Logging:** All security violations MUST be logged at WARN level with full context

**Performance Requirements:**
- Security test suite: <60s total runtime
- Individual isolation check: <50ms
- Full cross-tenant matrix: <10s

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `tests/security/test_tenant_isolation.py`

**Methods:**
- `test_cannot_get_other_tenant_clients()` - GET returns 404
- `test_cannot_update_other_tenant_clients()` - UPDATE fails
- `test_cannot_delete_other_tenant_clients()` - DELETE fails
- `test_cannot_see_other_tenant_matches()` - matches isolated
- `test_cannot_see_other_tenant_communications()` - communications isolated
- `test_404_not_403()` - no information leakage
- `test_sql_injection_blocked()` - injection attempts fail

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **Security Tests:**
  - `test_cannot_get_other_tenant_clients` - GET returns 404
  - `test_cannot_update_other_tenant_clients` - UPDATE fails
  - `test_cannot_delete_other_tenant_clients` - DELETE fails
  - `test_cannot_see_other_tenant_matches` - matches isolated
  - `test_cannot_see_other_tenant_communications` - communications isolated
  - `test_cannot_see_other_tenant_guide_progress` - progress isolated
  - `test_404_not_403` - no information leakage
  - `test_sql_injection_blocked` - injection attempts fail
  - `test_direct_id_access_blocked` - cannot guess IDs
- **E2E Tests:** `tests/e2e/test_tenant_isolation_e2e.py`
  - Full API flow with two studios
- **Coverage Target:** 95%+ for all isolation code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Cannot access other tenant's clients
- [ ] Cannot see other tenant's matches
- [ ] Cannot see other tenant's communications
- [ ] 95%+ coverage of isolation code
- [ ] No information leakage (404 vs 403)
- [ ] SQL injection protected
- [ ] All tests documented

---

### DEV-328: Matching Performance Tests

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Matching must be fast enough for inline use (<100ms) and background jobs (<5s for 100 clients). Need benchmarks to ensure performance targets.

**Solution:**
Create performance tests with realistic data volumes.

**Agent Assignment:** @Clelia (primary), @Ezio (optimization)

**Dependencies:**
- **Blocking:** DEV-320 (NormativeMatchingService), DEV-323 (LangGraph Node), DEV-325 (Background Job)
- **Unlocks:** Production deployment (performance gate)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Performance test timeout: Mark test as FAILED, log actual duration
- Database connection slow: Log warning, still measure actual performance
- Memory limit exceeded: Fail test, log memory usage
- **Logging:** All performance violations MUST be logged at WARN level

**Performance Requirements:**
- Test suite completion: <60s total
- Individual benchmark: <5s timeout
- Memory profiling: Track peak usage

**Edge Cases:**
- **Cold Start:** First query after server restart may be slower
- **Database Load:** Test with concurrent queries
- **Large Datasets:** Scale tests with 1000+ clients
- **Index Rebuilds:** Performance during index maintenance
- **Memory Pressure:** Behavior under low memory conditions

**File:** `tests/performance/test_matching_performance.py`

**Methods:**
- `test_inline_matching_latency()` - Verify <100ms for inline matching
- `test_batch_matching_100_clients()` - Verify <5s for 100 clients
- `test_concurrent_matching_load()` - Test under concurrent load
- `benchmark_structured_vs_semantic()` - Compare matching strategies
- `profile_memory_usage()` - Track memory during matching

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **Performance Tests:**
  - `test_inline_matching_p95_under_100ms` - inline latency benchmark
  - `test_batch_100_clients_under_5s` - batch performance
  - `test_concurrent_10_requests` - concurrent load test
  - `test_memory_stable_under_load` - memory profiling
- **Benchmarks:**

| Operation | Target | Volume |
|-----------|--------|--------|
| Inline matching | <100ms (p95) | Single client |
| Batch matching | <5s | 100 clients |
| Concurrent matching | <200ms (p95) | 10 parallel requests |

**Acceptance Criteria:**
- [ ] Inline matching <100ms (p95)
- [ ] Batch 100 clients <5s
- [ ] Results logged for monitoring
- [ ] Benchmarks documented

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Flaky performance tests | MEDIUM | Use p95 thresholds, warm-up phase |
| CI environment variance | LOW | Document baseline environment |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

---

### DEV-329: Unit Tests for Matching Services

**Reference:** [FR-003: Matching Normativo Automatico](./PRATIKO_2.0_REFERENCE.md#fr-003-matching-normativo-automatico)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Matching services need comprehensive unit tests to ensure correctness of rule evaluation, scoring, and edge case handling.

**Solution:**
Create unit tests for NormativeMatchingService, ProfileEmbeddingService, and related components.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-320 (NormativeMatchingService), DEV-321 (Matching Rules), DEV-322 (Vector Generation), DEV-323 (LangGraph Node)
- **Unlocks:** Phase 3 start (all Phase 2 complete)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Test fixture setup failure: Mark test as ERROR, log setup issue
- Mock configuration error: Fail test, log expected vs actual mock setup
- Assertion failure: Provide detailed diff in log output
- **Logging:** All test failures MUST be logged with context at ERROR level

**Performance Requirements:**
- Unit test suite: <30s total runtime
- Individual test: <500ms
- Coverage analysis: <10s

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**Files:**
- `tests/services/test_normative_matching_service.py`
- `tests/services/test_profile_embedding_service.py`

**Methods:**
- `test_rule_condition_evaluation()` - Test rule condition parsing
- `test_ateco_matching_exact()` - Exact ATECO code matching
- `test_ateco_matching_prefix()` - ATECO prefix matching (e.g., 43.*)
- `test_regime_matching()` - Fiscal regime filtering
- `test_score_calculation()` - Match score computation
- `test_no_clients_returns_empty()` - Empty studio handling
- `test_no_rules_returns_empty()` - No matching rules

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **Unit Tests:**
  - Rule condition evaluation
  - ATECO matching (exact, prefix)
  - Regime matching
  - Score calculation
  - Edge cases (no clients, no rules)
- **Test Categories:**
  - Happy path tests
  - Edge case tests
  - Error handling tests
  - Performance tests
- **Coverage Target:** 80%+ for all matching code

**Acceptance Criteria:**
- [ ] All matching service methods tested
- [ ] Edge cases covered
- [ ] 80%+ coverage achieved
- [ ] All tests pass

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**

---

## Phase 3: Communications (Week 7-8) - 10 Tasks

### DEV-330: CommunicationService with Draft/Approve Workflow

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Figma Reference:** `GestioneComunicazioniPage.tsx` — Source: [`docs/figma-make-references/GestioneComunicazioniPage.tsx`](../figma-make-references/GestioneComunicazioniPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Professionals need to send communications to clients about relevant regulations. Communications require a review/approval workflow to ensure quality.

**Solution:**
Create `CommunicationService` with draft/review/approve/send workflow state machine.

> **Navigation:** Add "Comunicazioni" menu item (Mail icon, route `/comunicazioni`) to the user menu dropdown in `web/src/app/chat/components/ChatHeader.tsx`. Insert above "Il mio Account", with a divider separating feature links from account/settings. Create the Next.js route at `web/src/app/comunicazioni/page.tsx`. Target menu layout:
> ```
> Clienti | Comunicazioni | Procedure | Dashboard | Scadenze Fiscali
> ─────────────
> Il mio Account | [superuser items]
> ─────────────
> Esci
> ```

**Agent Assignment:** @Ezio (primary), @Severino (workflow review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-305 (Communication model), DEV-309 (ClientService), DEV-307 (Migration)
- **Unlocks:** DEV-331 (LLM Generation), DEV-332 (Communication API), DEV-333 (Email), DEV-334 (WhatsApp)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`
- Self-approval attempted: HTTP 403, `"Non puoi approvare le tue comunicazioni"`
- Communication not found: HTTP 404, `"Comunicazione non trovata"`
- Client not in studio: HTTP 403, `"Cliente non appartenente allo studio"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Create draft: <200ms
- State transition: <100ms
- List communications (paginated): <150ms

**Edge Cases:**
- **Concurrent Approvals:** Two approvers click simultaneously → first wins, second gets HTTP 409
- **Reject After Approve:** Cannot reject APPROVED → HTTP 400 with clear message
- **Re-Approve Rejected:** REJECTED → can create new draft, but not re-approve same record
- **Self-Approval Bypass:** Creator changes to different studio → still blocked (creator_id check)
- **Empty Content:** Draft with empty body → HTTP 422, `"Contenuto obbligatorio"`
- **State Rollback:** System failure mid-transition → transaction rollback, no orphan state
- **Audit Trail:** Every transition logged even if failed (for security audit)
- **Soft Delete:** Deleted communication → excluded from lists, but audit trail preserved

**File:** `app/services/communication_service.py`

**Methods:**
- `create_draft(studio_id, client_id, data)` - Create draft communication
- `submit_for_review(communication_id)` - Move to pending review
- `approve(communication_id, approver_id)` - Approve (must be different user)
- `reject(communication_id, reason)` - Reject with reason
- `send(communication_id)` - Send approved communication

**Testing Requirements:**
- **TDD:** Write `tests/services/test_communication_service.py` FIRST
- **Unit Tests:**
  - `test_create_draft_success` - valid draft creation
  - `test_submit_for_review` - state transition
  - `test_approve_different_user` - approver != creator
  - `test_approve_same_user_fails` - self-approval blocked
  - `test_reject_with_reason` - rejection recorded
  - `test_send_approved_only` - cannot send unapproved
  - `test_state_machine_valid_transitions` - all valid transitions
  - `test_state_machine_invalid_transitions` - invalid transitions blocked
- **Integration Tests:** `tests/services/test_communication_service_integration.py`
- **E2E Tests:** Part of DEV-339
- **Edge Case Tests:**
  - `test_concurrent_approval_race` - second approver gets 409
  - `test_reject_after_approve_fails` - state machine enforced
  - `test_self_approval_creator_id_check` - blocked regardless of studio change
  - `test_empty_content_rejected` - draft with empty body fails
  - `test_state_transition_rollback` - no orphan state on failure
  - `test_audit_trail_on_failure` - failed attempts logged
  - `test_soft_delete_excludes_from_list` - deleted not returned
  - `test_soft_delete_preserves_audit` - audit accessible after delete
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 95%+ for workflow logic

**Risks & Mitigations:**
**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Workflow complexity | MEDIUM | State machine pattern |
| Concurrent approvals | LOW | Optimistic locking |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Create draft communication
- [ ] Submit for review workflow
- [ ] Approve/reject workflow
- [ ] Self-approval blocked
- [ ] 95%+ test coverage achieved

---

### DEV-331: LLM Communication Generation Tool

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Professionals need AI-generated communication drafts based on regulations and client context.

**Solution:**
Create LangGraph tool for generating communication content using LLM. Consider using existing `WebVerificationService` to verify regulatory claims before generating client communications.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-330 (CommunicationService), DEV-320 (NormativeMatchingService - for context)
- **Unlocks:** DEV-332 (Communication API), DEV-339 (E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- LLM generation failure: Retry up to 3 times, then HTTP 503, `"Generazione temporaneamente non disponibile"`
- Invalid client context: HTTP 400, `"Dati cliente insufficienti per generazione"`
- Content too long: Truncate with summary, warn user
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Single generation: <5s (LLM latency)
- Cost per generation: ~$0.02 (estimated)

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/core/langgraph/tools/communication_generator_tool.py`

**Methods:**
- `generate_communication(regulation, client_profile, channel)` - Generate draft content
- `format_for_email(content)` - Format content for email channel
- `format_for_whatsapp(content)` - Format content for WhatsApp (shorter)
- `personalize_content(content, client)` - Insert client-specific details

**Testing Requirements:**
- **TDD:** Write `tests/langgraph/tools/test_communication_generator_tool.py` FIRST
- **Unit Tests:**
  - `test_generate_email_format` - correct email structure
  - `test_generate_whatsapp_format` - correct WhatsApp format
  - `test_include_client_context` - personalizes for client
  - `test_include_regulation_reference` - cites regulation
  - `test_italian_language` - generates in Italian
  - `test_professional_tone` - appropriate tone
  - `test_communication_no_contradicted_info` - Verify generated communications don't contain web-contradicted information
- **Integration Tests:** Test with real LLM
- **E2E Tests:** Part of DEV-339
- **Regression Tests:** Run `pytest tests/langgraph/`
- **Coverage Target:** 80%+ for tool code

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Generate email-formatted communications
- [ ] Generate WhatsApp-formatted communications
- [ ] Include client context in generation
- [ ] Include regulation references
- [ ] 80%+ test coverage achieved

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM inconsistency | MEDIUM | Temperature tuning, validation |
| Cost overruns | LOW | Budget tracking, caching |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

---

### DEV-332: Communication API Endpoints

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Figma Reference:** `GestioneComunicazioniPage.tsx` — Source: [`docs/figma-make-references/GestioneComunicazioniPage.tsx`](../figma-make-references/GestioneComunicazioniPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Frontend needs API endpoints for the full communication workflow: create, review, approve, reject, send.

**Solution:**
Create Communication API router with all workflow endpoints.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-330 (CommunicationService), DEV-331 (LLM Generation Tool)
- **Unlocks:** DEV-333 (Email Sending), DEV-334 (WhatsApp), DEV-339 (E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- See DEV-330 for state transition errors
- Validation errors: HTTP 422, detailed field-level errors
- Rate limiting: HTTP 429, `"Troppe richieste, riprova tra {seconds} secondi"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- All endpoints: <200ms (excluding generation)
- Pagination: 20 items default, max 100

**Edge Cases:**
- **Concurrent Submit:** Two users submit same draft - first wins, second gets HTTP 409
- **Approve Own Draft:** API blocks even if UI bypassed - HTTP 403
- **Invalid UUID Format:** Malformed ID - HTTP 422 with clear format hint
- **Missing Required Fields:** POST with missing fields - HTTP 422 with field-level errors
- **Pagination Edge:** page=0 - treated as page=1; per_page=0 - default 20
- **Status Filter Invalid:** ?status=INVALID - HTTP 400 with valid options
- **Delete Pending Review:** Cannot delete while in review - HTTP 400
- **Rate Limit Per User:** 30 requests/minute per endpoint per user

**File:** `app/api/v1/communications.py`

**Endpoints:**
- `POST /api/v1/communications` - Create draft
- `GET /api/v1/communications` - List communications
- `GET /api/v1/communications/{id}` - Get single
- `POST /api/v1/communications/{id}/submit` - Submit for review
- `POST /api/v1/communications/{id}/approve` - Approve
- `POST /api/v1/communications/{id}/reject` - Reject
- `POST /api/v1/communications/{id}/send` - Send (for email: sends via SMTP; for WhatsApp: returns `whatsapp_link` in response body, marks as SENT)

**Channel-specific send behavior:**
- **Email:** Delegates to `EmailSendingService`, sends asynchronously, updates status on delivery/failure
- **WhatsApp:** Generates wa.me link via `WhatsAppService`, returns `{ "whatsapp_link": "https://wa.me/..." }` in response. Frontend shows confirmation modal with the link. Status set to SENT immediately (no delivery tracking in MVP).

**Testing Requirements:**
- **TDD:** Write `tests/api/test_communications_api.py` FIRST
- **Integration Tests:**
  - `test_create_draft_201` - draft created
  - `test_submit_for_review_200` - state transition
  - `test_approve_200` - approval works
  - `test_approve_self_400` - self-approval blocked
  - `test_reject_200` - rejection with reason
  - `test_send_200` - approved communication sent
  - `test_send_unapproved_400` - cannot send unapproved
  - `test_list_filtered_by_status` - status filtering
- **E2E Tests:** Part of DEV-339
- **Edge Case Tests:**
  - `test_concurrent_submit_409` - second submit gets conflict
  - `test_approve_own_draft_403` - API level self-approval block
  - `test_malformed_uuid_422` - clear error message for invalid ID
  - `test_missing_fields_422_field_level` - field-level validation errors
  - `test_pagination_page_zero_normalized` - page=0 treated as 1
  - `test_invalid_status_filter_400` - invalid filter rejected
  - `test_delete_pending_review_400` - cannot delete in review
  - `test_rate_limit_exceeded_429` - rate limiting enforced
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 80%+ for API code

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All workflow endpoints implemented
- [ ] Proper error messages for invalid transitions
- [ ] Tenant isolation enforced
- [ ] 80%+ test coverage achieved

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing API patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules
### DEV-333: Email Sending Integration

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need to actually send approved communications via email. Must integrate with existing email infrastructure.

**Solution:**
Create email sending service using existing patterns. Handle retries, failures, and status tracking.
**Error Handling:**
- SMTP connection failure: HTTP 503, `"Servizio email non disponibile"` + retry queue
- Invalid recipient email: HTTP 400, `"Indirizzo email non valido"`
- Bounce/rejection: Update status to FAILED, log reason
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Single email send: <3s
- Bulk send (10 emails): <15s (with rate limiting)
- Retry attempts: 3 with exponential backoff

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| SMTP rate limiting | MEDIUM | Queue with delays |
| Email bounces | LOW | Track delivery status |
| Spam filtering | MEDIUM | SPF/DKIM configuration |

**Edge Cases:**
- **SMTP Down:** Connection timeout → queue for retry, return HTTP 202 (accepted)
- **Invalid Email Format:** Malformed email address → reject before send attempt
- **Bounce After Send:** Email bounces → webhook updates status to FAILED
- **Duplicate Send:** Same communication sent twice → idempotent (skip if already SENT)
- **Empty Recipient:** Client without email → HTTP 400, `"Email cliente mancante"`
- **Rate Limit Hit:** SMTP rate limit → exponential backoff, continue queue
- **Large Attachment:** Attachment >10MB → reject, suggest file sharing link
- **Unsubscribed Client:** Client opted out → skip, log info, don't error

**File:** `app/services/email_sending_service.py`

**Methods:**
- `send_email(communication_id)` - Send single email
- `send_bulk(studio_id, communication_ids)` - Send multiple
- `track_delivery(communication_id)` - Update delivery status

**Testing Requirements:**
- **TDD:** Write `tests/services/test_email_sending_service.py` FIRST
- **Unit Tests:**
  - `test_send_email_success` - email sent
  - `test_send_email_failure_retry` - retry on failure
  - `test_send_email_update_status` - status updated
  - `test_send_bulk_partial_failure` - handles partial failures
  - `test_track_delivery` - delivery tracking
- **Integration Tests:** Test with mock SMTP
- **E2E Tests:** Part of DEV-339
- **Edge Case Tests:**
  - `test_smtp_down_queued_202` - connection timeout queued
  - `test_invalid_email_rejected` - malformed email fails
  - `test_bounce_webhook_updates_status` - bounce handling
  - `test_duplicate_send_idempotent` - already sent skipped
  - `test_empty_recipient_400` - missing email error
  - `test_rate_limit_backoff` - exponential backoff
  - `test_large_attachment_rejected` - size limit
  - `test_unsubscribed_skipped` - opt-out respected
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for email code

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Send emails via configured SMTP
- [ ] Retry logic for failures
- [ ] Track sent_at and delivery status
- [ ] 80%+ test coverage achieved

---

### DEV-334: WhatsApp wa.me Link Integration

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Figma Reference:** `GestioneComunicazioniPage.tsx` (channel toggle, "Invia" action) — Source: [`docs/figma-make-references/GestioneComunicazioniPage.tsx`](../figma-make-references/GestioneComunicazioniPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Professionals want to send WhatsApp messages to clients. For MVP, we use simple wa.me links rather than the complex WhatsApp Business API. The UX must let the professional review the message before leaving PratikoAI.

**Solution:**
Create WhatsApp service using `wa.me/{phone}?text={message}` links. When the professional clicks "Invia" on an approved WhatsApp communication, PratikoAI shows a **confirmation modal** with message preview and an "Apri WhatsApp" button that opens the wa.me link **in a new browser tab**. PratikoAI stays open in the original tab. No WhatsApp Business API needed.

**UX Decision (2026-02-26):** Modal confirmation before opening WhatsApp, chosen over: (a) direct navigation (disruptive, leaves PratikoAI), (b) copy-to-clipboard (requires manual paste), (c) open-in-new-tab without preview (no review step).

**Agent Assignment:** @Ezio (primary, backend service), @Livia (frontend modal component), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-330 (CommunicationService), DEV-309 (ClientService - for phone numbers)
- **Unlocks:** DEV-339 (Integration Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid phone format: HTTP 400, `"Formato numero di telefono non valido"`
- Missing phone number: HTTP 400, `"Numero di telefono cliente mancante"`
- Message too long: Warn user, suggest shortening (WhatsApp limit ~65536 chars)
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Phone format variations | LOW | Normalize to international format |
| URL encoding issues | LOW | Comprehensive test coverage |
| Pop-up blocker | MEDIUM | Fallback: show clickable link if `window.open` blocked |

**Performance Requirements:**
- Link generation response: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Non-Italian Phone:** International number without +39 → detect country code or reject
- **Phone with Spaces:** "+39 333 123 4567" → normalize to "393331234567"
- **Invalid Phone:** Non-numeric characters → HTTP 400 with format hint
- **Empty Message:** No message text → generate link without text param
- **Very Long Message:** >65536 chars → warn, truncate with "..." suffix
- **Special Characters:** Emojis, newlines → URL encode properly
- **Null Phone:** Client without phone → return null link, not error
- **Bulk Generation:** 100 clients → return array of links, nulls for missing phones
- **Pop-up Blocked:** `window.open` returns null → show fallback clickable link in modal

**Backend File:** `app/services/whatsapp_service.py`

**Backend Methods:**
- `generate_whatsapp_link(phone, message)` - Generate wa.me link
- `format_phone_number(phone)` - Format to international format (remove +, spaces)
- `url_encode_message(message)` - URL-encode the message text
- `generate_client_links(clients, template)` - Bulk generate for multiple clients

**Frontend File:** `web/src/components/features/WhatsAppSendModal.tsx`

**Frontend Behavior:**
- **Single send:** Modal shows recipient name, phone number, message preview, "Apri WhatsApp" (primary) + "Annulla" buttons
- **Bulk send:** Modal shows recipient checklist with individual "Apri" buttons. Each click opens wa.me in new tab and checks off the recipient. Progress counter shows "X/Y inviati". "Chiudi" button warns if not all links opened.
- **Pop-up fallback:** If `window.open` is blocked, display the wa.me URL as a clickable `<a target="_blank">` link
- **State update:** After all links opened (or modal closed), mark communication(s) as SENT via API call

**Example:**
```python
# Input: phone="+39 333 1234567", message="Gentile Mario, la rottamazione..."
# Output: "https://wa.me/393331234567?text=Gentile%20Mario%2C%20la%20rottamazione..."
```

**Testing Requirements:**
- **TDD:** Write `tests/services/test_whatsapp_service.py` FIRST
- **Unit Tests:**
  - `test_generate_link_valid_phone` - correct link format
  - `test_format_phone_italian` - +39 prefix handling
  - `test_url_encode_message` - special characters encoded
  - `test_bulk_generate_clients` - multiple clients
  - `test_empty_message` - link without text param
- **Edge Case Tests:**
  - `test_non_italian_phone_detected` - international format
  - `test_phone_spaces_normalized` - whitespace removed
  - `test_invalid_phone_400` - non-numeric rejected
  - `test_empty_message_no_text_param` - link without text
  - `test_long_message_truncated` - over limit truncated
  - `test_special_chars_encoded` - emojis encoded
  - `test_null_phone_null_link` - missing phone handled
  - `test_bulk_with_missing_phones` - nulls in array
- **Frontend Tests:** `web/src/components/features/WhatsAppSendModal.test.tsx`
  - `test_modal_shows_recipient_info` - name, phone, message displayed
  - `test_apri_whatsapp_opens_new_tab` - window.open called with wa.me URL
  - `test_bulk_modal_checklist` - all recipients listed with individual buttons
  - `test_bulk_progress_counter` - counter updates on each click
  - `test_popup_blocked_fallback` - clickable link shown when window.open fails
  - `test_close_warns_if_incomplete` - warning when not all links opened
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 90%+ for WhatsApp backend code, 80%+ for modal component

**MVP Note:**
WhatsApp Business API integration is deferred to post-MVP. The wa.me approach provides immediate value without API approval delays.

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules
- Frontend modal: <150 lines, extract sub-components if larger

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Generate wa.me links with phone and message
- [ ] Handle Italian phone number formats
- [ ] URL-encode message properly
- [ ] Bulk generation for multiple clients
- [ ] Confirmation modal shows message preview before opening WhatsApp
- [ ] "Apri WhatsApp" opens wa.me in new tab (PratikoAI stays open)
- [ ] Bulk modal shows recipient checklist with progress counter
- [ ] Pop-up blocker fallback (clickable link)
- [ ] 90%+ backend test coverage, 80%+ frontend test coverage

---

### DEV-335: Bulk Communication Creation

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Figma Reference:** `GestioneComunicazioniPage.tsx` (bulk actions) — Source: [`docs/figma-make-references/GestioneComunicazioniPage.tsx`](../figma-make-references/GestioneComunicazioniPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
When a regulation affects multiple clients, the professional wants to create communications for all at once.

**Solution:**
Add bulk creation endpoint that creates draft communications for multiple clients.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-330 (CommunicationService), DEV-320 (Matching - for matched client IDs)
- **Unlocks:** DEV-339 (E2E Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/services/communication_service.py`
- **Affected Files:**
  - `app/api/v1/communications.py` (bulk endpoint addition)
- **Related Tests:**
  - `tests/services/test_communication_service.py` (direct)
  - `tests/api/test_communications_api.py` (consumer)
- **Baseline Command:** `pytest tests/services/test_communication_service.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing CommunicationService reviewed
- [ ] Bulk operation patterns documented

**Error Handling:**
- Empty client list: HTTP 400, `"Seleziona almeno un cliente"`
- Max clients exceeded (>50): HTTP 400, `"Massimo 50 clienti per operazione bulk"`
- Partial client validation failure: Continue with valid clients, return error report
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Bulk create 50 drafts: <5s
- All-or-nothing transaction for consistency

**Edge Cases:**
- **Empty Client List:** 0 clients selected → HTTP 400, not empty draft list
- **Exactly 50 Clients:** At limit → success; 51 clients → HTTP 400
- **Deleted Client in List:** One deleted client → skip, continue with others, report
- **All Clients Invalid:** All clients deleted/inactive → HTTP 400, `"Nessun cliente valido"`
- **Duplicate Client IDs:** Same client twice in list → deduplicate, create once
- **Mixed Studios:** Client IDs from different studios → filter to current studio only
- **Transaction Failure:** DB failure at client 25/50 → full rollback, no partial
- **Template Not Found:** Referenced template missing → HTTP 404

**File:** `app/services/communication_service.py` (extend)

**Methods:**
- `log_action(communication_id, action, user_id)` - Log communication action
- `get_audit_trail(communication_id)` - Retrieve audit history
- `redact_pii(log_entry)` - Remove PII from audit logs

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_bulk_create_success` - creates for all clients
  - `test_bulk_create_partial` - handles client filtering
  - `test_bulk_create_limit` - respects max limit
  - `test_bulk_create_same_studio` - tenant isolation
- **Integration Tests:** Test with multiple clients
- **Edge Case Tests:**
  - `test_bulk_empty_list_400` - empty rejected
  - `test_bulk_exactly_50_success` - at limit works
  - `test_bulk_51_rejected` - over limit fails
  - `test_bulk_deleted_client_skipped` - skip deleted
  - `test_bulk_all_invalid_400` - all invalid fails
  - `test_bulk_duplicate_deduplicated` - no duplicates
  - `test_bulk_mixed_studios_filtered` - cross-studio filtered
  - `test_bulk_transaction_rollback` - failure rolls back all
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for bulk code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Create drafts for multiple clients
- [ ] Use matched client IDs from suggestions
- [ ] Single approval for bulk
- [ ] 80%+ test coverage achieved

---

### DEV-336: Communication Templates

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Figma Reference:** `GestioneComunicazioniPage.tsx` (template selector) — Source: [`docs/figma-make-references/GestioneComunicazioniPage.tsx`](../figma-make-references/GestioneComunicazioniPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Professionals want reusable templates for common communication scenarios rather than generating from scratch each time.

**Solution:**
Create template model and service for managing communication templates.

**Agent Assignment:** @Ezio (primary), @Mario (template content), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-305 (Communication model), DEV-307 (Migration)
- **Unlocks:** DEV-331 (Generation Tool can use templates)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Template not found: HTTP 404, `"Template non trovato"`
- Invalid template syntax: HTTP 422, `"Sintassi template non valida"`
- Variable substitution failure: Log warning, use fallback value
- **Logging:** All errors MUST be logged with context at ERROR level

**Performance Requirements:**
- Template rendering: <50ms
- Variable substitution: <10ms per variable
- Template listing: <100ms

**Edge Cases:**
- **Missing Variables:** Template has {{client_name}} but client has no name → use fallback "Cliente"
- **Invalid Variable Syntax:** Template has {client_name} not {{}} → treat as literal text
- **Empty Template Body:** Template with empty body → HTTP 422, `"Contenuto template obbligatorio"`
- **Deleted Template:** Communication references deleted template → use snapshot, warn user
- **Studio vs Global:** Studio template with same name as global → studio takes precedence
- **Variable Loop:** Template references another template → reject, prevent infinite loop
- **Long Template:** Template body >10KB → reject, suggest splitting

**File:** `app/models/communication_template.py`

**Fields:**
- `id`: UUID (primary key)
- `name`: String (template name)
- `category`: Enum (EMAIL, WHATSAPP)
- `subject_template`: String (email subject with variables)
- `body_template`: Text (body with {{variable}} placeholders)
- `variables`: JSONB (list of required variables)
- `studio_id`: UUID (FK, null for global templates)
- `created_at`: DateTime
- `updated_at`: DateTime

**Testing Requirements:**
- **TDD:** Write `tests/models/test_communication_template.py` FIRST
- **Unit Tests:**
  - `test_template_creation` - valid template
  - `test_template_variables` - variable substitution
  - `test_template_category` - category filtering
  - `test_template_studio_specific` - studio templates
- **Edge Case Tests:**
  - `test_missing_variable_fallback` - fallback values
  - `test_invalid_syntax_literal` - bad syntax treated as text
  - `test_empty_body_rejected` - empty rejected
  - `test_deleted_template_snapshot` - snapshot preserved
  - `test_studio_precedence` - studio overrides global
  - `test_template_loop_rejected` - circular reference blocked
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/`
- **Coverage Target:** 80%+ for template code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Template model with variables
- [ ] Pre-configured templates
- [ ] Studio-specific templates (future)
- [ ] 80%+ test coverage achieved

---

### DEV-337: Response Formatter with Suggestions

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Figma Reference:** `ChatPage.tsx` (suggestion cards) in [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
When matching finds affected clients, the response should include a proactive suggestion. Need to modify response formatter.

**Solution:**
Modify `response_formatter_node.py` to append suggestions when matched_clients exist.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-323 (LangGraph Matching Node - provides matched_clients)
- **Unlocks:** DEV-339 (E2E Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/core/langgraph/nodes/response_formatter_node.py`
- **Affected Files:**
  - `app/core/langgraph/graph.py` (node consumer)
  - `app/schemas/rag_state.py` (uses matched_clients field)
- **Related Tests:**
  - `tests/langgraph/test_response_formatter_node.py` (direct)
  - `tests/integration/test_rag_pipeline.py` (consumer)
- **Baseline Command:** `pytest tests/langgraph/ -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing response_formatter_node.py reviewed
- [ ] RAGState matched_clients field available

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/core/langgraph/nodes/response_formatter_node.py` (MODIFY)

**Methods:**
- `format_response_with_suggestions(state)` - Main node entry point
- `append_client_match_suggestion(response, matched_clients)` - Add suggestion text
- `format_suggestion_text(count)` - Generate Italian suggestion text
- `should_include_suggestion(state)` - Check if suggestions apply

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_formatter_no_matches` - normal response
  - `test_formatter_with_matches` - includes suggestion
  - `test_formatter_match_count` - correct count
  - `test_formatter_italian_text` - Italian suggestion text
- **Integration Tests:** Test with full RAGState
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/langgraph/` - all pipeline tests pass
- **Coverage Target:** 80%+ for formatter, 95%+ for pipeline integration

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Append suggestion to response
- [ ] "X dei tuoi clienti potrebbero essere interessati"
- [ ] No change when no matches
- [ ] All pipeline tests pass

---

### DEV-338: Communication Audit Logging

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Figma Reference:** `GestioneComunicazioniPage.tsx` (audit trail) — Source: [`docs/figma-make-references/GestioneComunicazioniPage.tsx`](../figma-make-references/GestioneComunicazioniPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
All communication actions must be audited for compliance. Who created, reviewed, approved, sent.

**Solution:**
Use existing `SecurityAuditLogger` to log all communication actions.

**Agent Assignment:** @Ezio (primary), @Severino (audit review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-330 (CommunicationService), Existing SecurityAuditLogger
- **Unlocks:** DEV-339 (E2E Tests), GDPR compliance verification

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/services/communication_service.py`
- **Affected Files:**
  - `app/services/security_audit_logger.py` (integrates with)
- **Related Tests:**
  - `tests/services/test_communication_service.py` (direct)
  - `tests/security/test_audit_logging.py` (consumer)
- **Baseline Command:** `pytest tests/services/test_communication_service.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing CommunicationService reviewed
- [ ] SecurityAuditLogger patterns understood

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level
**Performance Requirements:**
- Audit log write: <10ms (non-blocking)
- Log retrieval: <100ms for 1000 entries
- No impact on API response time
**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/services/communication_service.py` (extend)

**Methods:**
- `log_action(communication_id, action, user_id)` - Log communication action
- `get_audit_trail(communication_id)` - Retrieve audit history
- `redact_pii(log_entry)` - Remove PII from audit logs

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_audit_create` - creation logged
  - `test_audit_submit` - submission logged
  - `test_audit_approve` - approval logged
  - `test_audit_reject` - rejection logged
  - `test_audit_send` - sending logged
  - `test_audit_no_pii` - no PII in logs
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/` and `pytest tests/security/`
- **Coverage Target:** 95%+ for audit code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All actions logged
- [ ] No PII in audit logs
- [ ] Follows existing patterns
- [ ] 95%+ test coverage achieved

---

### DEV-339: E2E Tests for Communication Flow

**Reference:** [FR-004: Suggerimenti Proattivi e Generazione Comunicazioni](./PRATIKO_2.0_REFERENCE.md#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need end-to-end tests verifying the complete communication workflow from draft to delivery.

**Solution:**
Create comprehensive E2E tests for communication flow.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-330 (CommunicationService), DEV-332 (API), DEV-333 (Email), DEV-334 (WhatsApp), DEV-337 (Response Formatter), DEV-338 (Audit)
- **Unlocks:** Phase 4 start (all Phase 3 complete)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Test environment setup failure: Mark test as ERROR, log setup issue
- External service unavailable: Skip test with SKIP, log reason
- Assertion failure: Provide detailed diff in log output
- **Logging:** All test failures MUST be logged at ERROR level

**Performance Requirements:**
- E2E test suite: <120s total runtime
- Individual flow test: <30s
- Setup/teardown: <5s

**Edge Cases:**
- **Service Unavailable:** External services down - skip or mock
- **Concurrent Tests:** Ensure test isolation
- **Data Cleanup:** Clean test data after each test

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow (send endpoint returns whatsapp_link)
- `test_whatsapp_send_returns_link()` - Verify POST /send for WhatsApp channel returns `{ whatsapp_link: "https://wa.me/..." }` and marks as SENT
- `test_whatsapp_bulk_returns_links()` - Bulk send returns array of wa.me links (nulls for missing phones)
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients, mixed channels
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **E2E Tests:**
  - `test_create_draft_to_send_email_flow` - full email flow
  - `test_create_draft_to_send_whatsapp_flow` - full WhatsApp flow (verify link returned)
  - `test_whatsapp_send_returns_link` - send endpoint returns wa.me link in response
  - `test_whatsapp_bulk_returns_links` - bulk send returns array of links
  - `test_rejection_flow` - draft → review → reject → revise
  - `test_bulk_communication_flow` - multiple clients, mixed email + WhatsApp
  - `test_self_approval_blocked` - security check E2E
- **Coverage Target:** Full workflow coverage

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Draft creation tested
- [ ] Approval workflow tested
- [ ] Email sending tested
- [ ] WhatsApp send returns wa.me link (not actual sending)
- [ ] WhatsApp bulk returns array of links
- [ ] Self-approval blocking verified

---

## Phase 4: Procedure Interattive (Week 9-10) - 12 Tasks

### DEV-340: ProceduraService with Progress Tracking

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Figma Reference:** `ProceduraInterattivaPage.tsx` — Source: [`docs/figma-make-references/ProceduraInterattivaPage.tsx`](../figma-make-references/ProceduraInterattivaPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Users need to track progress through multi-step procedure, resume where they left off, and associate procedure with specific clients.

**Solution:**
Create `ProceduraService` with two operational modes:
- **Generic consultation** (`get_reference(procedura_id)`): Read-only access to procedura content. No side effects, no ProceduraProgress created. Used by `/procedura` slash command.
- **Client-specific tracking** (`start_for_client(user_id, procedura_id, client_id)`): Requires `client_id`, creates ProceduraProgress record, enables step tracking and notes. Used by `@NomeCliente` mention system.

> **Navigation:** When implementing the frontend, add "Procedure" menu item (ClipboardList icon, route `/procedure`) to the user menu dropdown in `web/src/app/chat/components/ChatHeader.tsx`. Insert in the feature links section above "Il mio Account". Target menu layout:
> ```
> ┌──────────────────────┐
> │  Clienti             │  (DEV-308)
> │  Comunicazioni       │  (DEV-330)
> │  Procedure           │  (DEV-340)
> │  Dashboard           │  (DEV-354)
> │  Scadenze Fiscali    │  (DEV-385)
> │ ──────────────────── │
> │  Il mio Account      │
> │  [superuser items]   │
> │ ──────────────────── │
> │  Esci                │
> └──────────────────────┘
> ```

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-306 (Procedura model), DEV-307 (ProceduraProgress model), DEV-307 (Migration)
- **Unlocks:** DEV-342 (Procedura API), DEV-343 (Checklist), DEV-345 (Chat Context), DEV-346 (Analytics), DEV-402 (/procedura command), DEV-403 (@client mention), DEV-404 (Generic vs Client-Specific split)
**Error Handling:**
- Procedura not found: HTTP 404, `"Procedura non trovata"`
- Progress not found: HTTP 404, `"Progresso non trovato"`
- Invalid step number: HTTP 400, `"Numero step non valido"`
- Step out of order: HTTP 400, `"Completa prima i passi precedenti"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- List procedure: <100ms
- Start procedura: <200ms
- Complete step: <100ms

**Edge Cases:**
- **Procedura Already Started:** start_procedura when progress exists → return existing progress (idempotent)
- **Skip Steps:** complete_step(3) when step 1 incomplete → HTTP 400, list missing steps
- **Complete Twice:** complete_step on already-completed step → HTTP 200 (idempotent)
- **Client Deleted:** Procedura progress on deleted client → orphan allowed, display warning
- **Procedura Updated:** Procedura content updated after user started → continue with old structure
- **Zero Steps:** Procedura with 0 steps → rejected during admin creation
- **Resume Completed:** Resume on completed procedura → HTTP 400, `"Procedura già completata"`
- **Concurrent Progress:** Same user starts same procedura twice → single progress record
- **Generic Consultation Must NOT Create Progress:** `get_reference()` is read-only, must NOT create ProceduraProgress records

**File:** `app/services/procedura_service.py`

**Methods:**
- `list_procedure(category)` - List available procedure
- `get_reference(procedura_id)` - Read-only access for generic consultation (NO progress record)
- `start_for_client(user_id, procedura_id, client_id)` - Start procedure for specific client (REQUIRES client_id, creates ProceduraProgress)
- `complete_step(progress_id, step_number)` - Mark step complete (client-specific mode only)
- `get_progress(user_id, procedura_id)` - Get current progress
- `resume_procedura(progress_id)` - Resume from last step

**Testing Requirements:**
- **TDD:** Write `tests/services/test_procedura_service.py` FIRST
- **Unit Tests:**
  - `test_list_procedure_by_category` - filtering works
  - `test_start_procedura_new_progress` - creates progress record
  - `test_start_procedura_with_client` - associates client
  - `test_complete_step` - updates progress
  - `test_complete_step_order` - enforces step order
  - `test_resume_procedura` - returns current state
  - `test_complete_procedura` - marks completed_at
- **Integration Tests:** `tests/services/test_procedura_service_integration.py`
- **E2E Tests:** Part of DEV-347
- **Edge Case Tests:**
  - `test_start_procedura_already_started_idempotent` - returns existing
  - `test_complete_step_skip_rejected` - skip steps blocked
  - `test_complete_step_twice_idempotent` - re-complete ok
  - `test_progress_deleted_client_warning` - orphan handled
  - `test_procedura_updated_old_structure` - version locking
  - `test_resume_completed_rejected` - completed procedura blocked
  - `test_concurrent_start_single_record` - no duplicates
  - `test_get_reference_readonly` - no progress record created
  - `test_start_for_client_requires_client_id` - client_id mandatory
  - `test_generic_consultation_no_side_effects` - get_reference is pure read
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for procedura code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Progress tracking per user per procedura
- [ ] Optional client association
- [ ] Step completion tracking
- [ ] Resume functionality
- [ ] 80%+ test coverage achieved

**Methods:**
- `load_procedure()` - Load procedure from JSON file
- `validate_procedura(procedura)` - Validate procedura structure and steps
- `seed_procedure(session)` - Insert procedure into database via migration

---

### DEV-341: 9 Pre-configured Procedure

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Need procedure for common administrative tasks. These should be pre-configured with steps, documents, and checklists.

**Solution:**
Define 9 procedure and seed via migration. Note: "Apertura P.IVA Persona Fisica" and "Apertura P.IVA Ditta Individuale" are merged into a single "Apertura P.IVA" procedure with a conditional branching step at step 1 to distinguish PF vs DI.

**Agent Assignment:** @Mario (primary), @Primo (migration)

**Dependencies:**
- **Blocking:** DEV-306 (Procedura model), DEV-307 (Migration)
- **Unlocks:** DEV-340 (ProceduraService - needs procedure to operate on)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`
**Error Handling:**
- Invalid JSON schema: Migration aborted, `"Schema procedura non valido"`
- Duplicate procedura code: Migration aborted, `"Codice procedura duplicato: {code}"`
- Missing required steps: Migration aborted, `"Step obbligatori mancanti"`
- **Logging:** All errors MUST be logged with context at ERROR level

**Performance Requirements:**
- Migration execution: <30s
- Procedura loading at startup: <500ms
- Procedura validation: <100ms per procedura
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/data/procedure.json`

**Procedure:**
1. **Apertura P.IVA** (merged: Persona Fisica + Ditta Individuale, conditional branching at step 1)
2. **Costituzione SRL**
3. **Assunzione Dipendente**
4. **Licenziamento Dipendente**
5. **Trasformazione Regime Fiscale**
6. **Cessazione Attività**
7. **Iscrizione INPS Artigiani**
8. **Richiesta DURC**
9. **Dichiarazione IVA Annuale**

**Testing Requirements:**
- **TDD:** Write procedura tests FIRST
- **Unit Tests:** `tests/data/test_procedure.py`
  - `test_procedure_json_valid` - JSON schema valid
  - `test_procedure_all_have_steps` - all procedure have steps
  - `test_procedure_steps_have_content` - steps have required fields
  - `test_procedura_apertura_piva` - specific procedura structure
- **Integration Tests:** Test procedura loading
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/test_procedura_service.py`
- **Coverage Target:** 100% for procedura definitions

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] 9 procedure defined
- [ ] Each procedura has step-by-step instructions
- [ ] Each step has checklist items
- [ ] Migration seeds procedure

---

### DEV-342: Procedura API Endpoints

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Figma Reference:** `ProceduraInterattivaPage.tsx` — Source: [`docs/figma-make-references/ProceduraInterattivaPage.tsx`](../figma-make-references/ProceduraInterattivaPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Frontend needs API to list procedure, start progress, and track completion.

**Solution:**
Create Procedure router with endpoints.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-340 (ProceduraService), DEV-341 (Pre-configured Procedure)
- **Unlocks:** DEV-347 (E2E Tests), Frontend integration

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`
**Error Handling:**
- See DEV-340 for service-level errors
- Validation errors: HTTP 422, detailed field-level errors
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- All endpoints: <200ms

**Edge Cases:**
- **Invalid Step Number:** step_num > procedura.total_steps → HTTP 400, `"Step non valido"`
- **Progress Not Found:** Complete step on non-existent progress → HTTP 404
- **Procedura Not Found:** Start non-existent procedura → HTTP 404
- **Pagination Empty:** page=10 on 2-page list → empty items, correct total
- **Category Filter Empty:** ?category=NONEXISTENT → empty list (not 404)
- **Complete Zero Steps:** POST complete with step_num=0 → HTTP 400

**File:** `app/api/v1/procedure.py`

**Endpoints:**
- `GET /api/v1/procedure` - List procedure
- `GET /api/v1/procedure/{id}` - Get procedura details
- `GET /api/v1/procedure/{id}/reference` - Read-only view for `/procedura` command (no progress created)
- `POST /api/v1/procedure/{id}/start` - Start procedura for client (requires client_id)
- `GET /api/v1/procedure/progress` - List user's progress
- `POST /api/v1/procedure/progress/{id}/step/{step_num}` - Complete step

**Testing Requirements:**
- **TDD:** Write `tests/api/test_procedure_api.py` FIRST
- **Integration Tests:**
  - `test_list_procedure_200` - returns procedure
  - `test_list_procedure_filtered` - category filter
  - `test_get_procedura_200` - returns procedura with steps
  - `test_start_procedura_201` - creates progress
  - `test_complete_step_200` - updates progress
  - `test_list_progress_200` - returns user's progress
- **E2E Tests:** Part of DEV-347
- **Edge Case Tests:**
  - `test_invalid_step_number_400` - step beyond total rejected
  - `test_progress_not_found_404` - non-existent progress
  - `test_procedura_not_found_404` - non-existent procedura
  - `test_pagination_empty_items` - beyond results empty
  - `test_category_filter_empty_list` - unknown category empty
  - `test_complete_step_zero_400` - step 0 rejected
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 80%+ for API code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] List procedure with filtering
- [ ] Start procedura for user
- [ ] Track step completion
- [ ] 80%+ test coverage achieved

---

### DEV-343: Procedura Step Checklist Tracking

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Figma Reference:** `ProceduraInterattivaPage.tsx` (step checklist) — Source: [`docs/figma-make-references/ProceduraInterattivaPage.tsx`](../figma-make-references/ProceduraInterattivaPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Each step may have multiple checklist items. Need granular tracking of which items are completed.

**Solution:**
Extend progress tracking to include checklist item completion.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-340 (ProceduraService), DEV-307 (ProceduraProgress model)
- **Unlocks:** DEV-347 (E2E Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/models/procedura_progress.py`
- **Affected Files:**
  - `app/services/procedura_service.py` (uses ProceduraProgress model)
- **Related Tests:**
  - `tests/models/test_procedura_progress.py` (direct)
  - `tests/services/test_procedura_service.py` (consumer)
- **Baseline Command:** `pytest tests/models/test_procedura_progress.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing ProceduraProgress model reviewed
- [ ] Checklist structure designed

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully

**Performance Requirements:**
- Checklist item toggle: <50ms
- Step auto-completion check: <20ms
- Progress update: <100ms

**Methods:**
- `toggle_checklist_item(progress_id, step_num, item_idx)` - Toggle item completion
- `get_checklist_status(progress_id, step_num)` - Get step checklist status
- `check_step_completion(progress_id, step_num)` - Auto-complete if all items done
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/procedura_progress.py` (extend)

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_checklist_item_complete` - item completion
  - `test_checklist_partial_complete` - partial progress
  - `test_checklist_all_complete` - step auto-completes
  - `test_checklist_uncheck` - can uncheck item
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/` and `pytest tests/services/`
- **Coverage Target:** 80%+ for checklist code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Track individual checklist items
- [ ] Auto-complete step when all items done
- [ ] Allow unchecking items
- [ ] 80%+ test coverage achieved

---

### DEV-344: Procedura Notes and Attachments

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Figma Reference:** `ProceduraInterattivaPage.tsx` (notes/attachments section) — Source: [`docs/figma-make-references/ProceduraInterattivaPage.tsx`](../figma-make-references/ProceduraInterattivaPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Users need to add notes and attachments to procedura progress for their reference.

**Solution:**
Add notes field to ProceduraProgress and document attachment support.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-340 (ProceduraService), DEV-307 (ProceduraProgress model)
- **Unlocks:** DEV-347 (E2E Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/models/procedura_progress.py`
- **Affected Files:**
  - `app/services/procedura_service.py` (uses ProceduraProgress model)
  - `app/api/v1/procedure.py` (notes endpoint)
- **Related Tests:**
  - `tests/models/test_procedura_progress.py` (direct)
  - `tests/services/test_procedura_service.py` (consumer)
- **Baseline Command:** `pytest tests/models/test_procedura_progress.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing ProceduraProgress model reviewed
- [ ] Notes storage approach designed

**Edge Cases:**

**Error Handling:**
- Note too long: HTTP 422, `"Nota troppo lunga (max 5000 caratteri)"`
- Attachment too large: HTTP 413, `"File troppo grande (max 10MB)"`
- Invalid file type: HTTP 422, `"Tipo file non supportato"`
- Progress not found: HTTP 404, `"Progresso non trovato"`
- **Logging:** All errors MUST be logged with context at ERROR level

**Performance Requirements:**
- Add note: <100ms
- Update note: <50ms
- Attachment upload: <5s (for 10MB file)

**Methods:**
- `add_note(progress_id, step_num, content)` - Add note to step
- `update_note(progress_id, step_num, content)` - Update existing note
- `add_attachment(progress_id, step_num, file)` - Upload attachment
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/procedura_progress.py` (extend)

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_add_note` - note saved
  - `test_update_note` - note updated
  - `test_note_per_step` - notes per step
  - `test_attachment_upload` - file upload
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/` and `pytest tests/services/`
- **Coverage Target:** 80%+ for notes code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Add notes to progress
- [ ] Notes per step
- [ ] Document attachment (future)
- [ ] 80%+ test coverage achieved

---

### DEV-345: Procedura Context in Chat

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Figma Reference:** `ChatPage.tsx` in [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
When user is working through a procedura and asks a question, the AI should know which procedura step they're on. Additionally, `@NomeCliente` mentions in chat should inject both client context AND active/relevant procedures into the conversation.

**Solution:**
Add procedura context to RAGState when user has active procedura progress. When `@NomeCliente` is mentioned, inject client profile (regime fiscale, ATECO, posizione) and any active or suggested procedures for that client into RAGState via `procedura_context` field.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-340 (ProceduraService), DEV-403 (@client mention system), Existing context_builder_node
- **Unlocks:** DEV-347 (E2E Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/core/langgraph/nodes/context_builder_node.py`
- **Affected Files:**
  - `app/core/langgraph/graph.py` (node consumer)
  - `app/schemas/rag_state.py` (adds procedura_context field)
- **Related Tests:**
  - `tests/langgraph/test_context_builder_node.py` (direct)
  - `tests/integration/test_rag_pipeline.py` (consumer)
- **Baseline Command:** `pytest tests/langgraph/test_context_builder_node.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing context_builder_node.py reviewed
- [ ] Procedura context structure designed

**Error Handling:**
- Procedura service unavailable: Skip context injection, continue pipeline
- Invalid procedura progress: Log warning, continue without procedura context
- Context too large: Truncate procedura context, prioritize current step
- **Logging:** All errors MUST be logged with context at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/core/langgraph/nodes/context_builder_node.py` (extend)

**Methods:**
- `inject_document_context(state, client_id)` - Inject client documents into RAGState
- `summarize_document(document)` - Summarize large documents for context window
- `filter_relevant_documents(documents, query)` - Filter documents by relevance to query
- `format_document_context(documents)` - Format documents for LLM consumption

**Performance Requirements:**
- Document context injection: <200ms
- Document summarization: <500ms per document
- Context building: <300ms total
- Database queries: <50ms (p95)

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_context_includes_procedura` - procedura in context
  - `test_context_current_step` - current step included
  - `test_context_no_active_procedura` - normal context
- **Integration Tests:** Test with RAGState
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/langgraph/`
- **Coverage Target:** 80%+ for context code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Include procedura context in RAGState
- [ ] Current step awareness
- [ ] No change when no active procedura
- [ ] 80%+ test coverage achieved

---

### DEV-346: Procedura Completion Analytics

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Priority:** LOW | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need to track procedura usage for analytics: how many started, completed, average time.

**Solution:**
Add analytics methods to ProceduraService.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-340 (ProceduraService), DEV-307 (ProceduraProgress model)
- **Unlocks:** Dashboard analytics (post-MVP)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/services/procedura_service.py`
- **Affected Files:**
  - `app/api/v1/procedure.py` (analytics endpoint)
- **Related Tests:**
  - `tests/services/test_procedura_service.py` (direct)
- **Baseline Command:** `pytest tests/services/test_procedura_service.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing ProceduraService reviewed
- [ ] Analytics metrics defined

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Analytics query: <200ms
- Aggregation calculations: <100ms
- Historical data (30 days): <500ms

**Methods:**
- `get_started_count(studio_id, procedura_id, period)` - Count started procedure
- `get_completed_count(studio_id, procedura_id, period)` - Count completed procedure
- `get_completion_rate(studio_id, procedura_id, period)` - Calculate completion rate
- `get_average_time(studio_id, procedura_id)` - Calculate average completion time

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/services/procedura_service.py` (extend)

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_analytics_started_count` - counts started
  - `test_analytics_completed_count` - counts completed
  - `test_analytics_completion_rate` - calculates rate
  - `test_analytics_average_time` - calculates avg time
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for analytics code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Track procedura starts
- [ ] Track completions
- [ ] Calculate completion rate
- [ ] 80%+ test coverage achieved

---

### DEV-347: E2E Tests for Procedura Flow

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need end-to-end tests verifying the complete procedura workflow.

**Solution:**
Create comprehensive E2E tests for procedura flow.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-340 (ProceduraService), DEV-341 (Procedure), DEV-342 (API), DEV-343 (Checklist), DEV-344 (Notes), DEV-345 (Chat Context)
- **Unlocks:** Phase 5 start (all Phase 4 complete)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Test environment setup failure: Mark test as ERROR, log setup issue
- External service unavailable: Skip test with SKIP, log reason
- Assertion failure: Provide detailed diff in log output
- **Logging:** All test failures MUST be logged at ERROR level

**Performance Requirements:**
- E2E test suite: <90s total runtime
- Individual flow test: <20s
- Setup/teardown: <5s

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `tests/e2e/test_procedura_flow.py`

**Methods:**
- `test_list_start_complete_procedura_flow()` - Full procedura workflow
- `test_resume_procedura_flow()` - Resume from progress
- `test_procedura_with_client_flow()` - Client-specific procedura
- `test_procedura_chat_context_flow()` - Chat during procedura
- `test_procedura_generic_consultation_flow()` - Generic read-only consultation via `/procedura`
- `test_client_mention_procedura_flow()` - `@NomeCliente` triggers client context + procedures in RAGState

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **E2E Tests:**
  - `test_list_start_complete_procedura_flow` - full flow
  - `test_resume_procedura_flow` - resume from progress
  - `test_procedura_with_client_flow` - client-specific procedura
  - `test_procedura_chat_context_flow` - chat during procedura
  - `test_procedura_generic_consultation_flow` - generic read-only consultation
  - `test_client_mention_procedura_flow` - @client mention triggers context injection
- **Coverage Target:** Full workflow coverage

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Procedura listing tested
- [ ] Start and progress tested
- [ ] Step completion tested
- [ ] Resume functionality tested

---

## Phase 5: Fiscal Calculations Enhancement (Week 11) - 6 Tasks

### DEV-348: Client Context Injection for Calculations

**Reference:** [FR-007: Calcoli Fiscali](./PRATIKO_2.0_REFERENCE.md#fr-007-calcoli-fiscali)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Existing calculation tools (IRPEF, INPS, etc.) don't know client context. Need to inject client profile data.

**Solution:**
Modify calculation tools to accept optional client_id and use profile data.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-302 (ClientProfile), DEV-309 (ClientService), Existing calculation tools
- **Unlocks:** DEV-349 (IRPEF), DEV-350 (INPS), DEV-351 (IMU)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/core/langgraph/tools/` (multiple tools)
- **Affected Files:**
  - `app/core/langgraph/nodes/` (tool consumers)
  - `app/services/` (calculation services)
- **Related Tests:**
  - `tests/langgraph/tools/test_irpef_tool.py` (direct)
  - `tests/langgraph/tools/test_inps_tool.py` (direct)
- **Baseline Command:** `pytest tests/langgraph/tools/ -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing calculation tools reviewed
- [ ] Client context injection pattern designed

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/core/langgraph/tools/` (multiple tools)

**Methods:**
- `inject_client_context(tool_input, client_id)` - Inject client profile into calculation
- `extract_regime_fiscale(client_profile)` - Extract fiscal regime for IRPEF
- `extract_ateco_codes(client_profile)` - Extract ATECO codes for INPS
- `extract_property_data(client_profile)` - Extract immobili for IMU

**Performance Requirements:**
- Client context lookup: <50ms
- Context injection: <10ms
- Response time: <200ms (p95)

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_irpef_with_client_context` - uses client regime
  - `test_inps_with_client_context` - uses client ATECO
  - `test_calculation_without_client` - backward compatible
  - `test_client_context_extraction` - extracts correct fields
- **Integration Tests:** Test with real client profiles
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/langgraph/tools/`
- **Coverage Target:** 95%+ for calculation code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Calculations use client context when available
- [ ] Backward compatible without client
- [ ] 95%+ test coverage achieved

---

### DEV-349: IRPEF Calculator Enhancement

**Reference:** [FR-007: Calcoli Fiscali](./PRATIKO_2.0_REFERENCE.md#fr-007-calcoli-fiscali)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
IRPEF calculation needs to consider regime fiscale (forfettario vs ordinario) and specific deductions.

**Solution:**
Enhance IRPEF calculator with regime-aware calculations.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-348 (Client Context Injection), Existing IRPEF calculator
- **Unlocks:** DEV-352 (Calculation History), DEV-353 (Accuracy Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/services/irpef_calculator.py`
- **Affected Files:**
  - `app/core/langgraph/tools/irpef_tool.py` (uses calculator)
- **Related Tests:**
  - `tests/services/test_irpef_calculator.py` (direct)
- **Baseline Command:** `pytest tests/services/test_irpef_calculator.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing IRPEF calculator reviewed
- [ ] Regime-aware logic designed

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/services/irpef_calculator.py` (extend)

**Methods:**
- `calculate_irpef_ordinario(reddito, detrazioni)` - Calculate IRPEF with ordinary regime
- `calculate_irpef_forfettario(reddito, coefficiente)` - Calculate IRPEF with forfettario regime (5% or 15%)
- `apply_deductions(irpef_lordo, detrazioni)` - Apply eligible deductions
- `get_tax_bracket(reddito)` - Determine applicable tax bracket

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests (parametrized):**
  - `test_irpef_ordinario_brackets` - tax brackets
  - `test_irpef_forfettario_flat_5` - 5% rate
  - `test_irpef_forfettario_flat_15` - 15% rate
  - `test_irpef_deductions` - deduction calculation
  - `test_irpef_edge_cases` - boundary values
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run existing IRPEF tests
- **Coverage Target:** 95%+ for calculation code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Regime-aware IRPEF
- [ ] Deductions calculation
- [ ] 95%+ test coverage achieved

---

### DEV-350: INPS Calculator Enhancement

**Reference:** [FR-007: Calcoli Fiscali](./PRATIKO_2.0_REFERENCE.md#fr-007-calcoli-fiscali)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
INPS contributions vary by ATECO code and worker type. Need context-aware calculation.

**Solution:**
Enhance INPS calculator with ATECO-based rates.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-348 (Client Context Injection), Existing INPS calculator
- **Unlocks:** DEV-352 (Calculation History), DEV-353 (Accuracy Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/services/inps_calculator.py`
- **Affected Files:**
  - `app/core/langgraph/tools/inps_tool.py` (uses calculator)
- **Related Tests:**
  - `tests/services/test_inps_calculator.py` (direct)
- **Baseline Command:** `pytest tests/services/test_inps_calculator.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing INPS calculator reviewed
- [ ] ATECO-based rates researched

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/services/inps_calculator.py` (extend)

**Methods:**
- `calculate_inps_artigiano(reddito, ateco)` - Calculate INPS for artigiano
- `calculate_inps_commerciante(reddito, ateco)` - Calculate INPS for commerciante
- `calculate_gestione_separata(reddito, aliquota)` - Calculate gestione separata contributions
- `get_minimum_contribution(categoria)` - Get minimum contribution amount

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests (parametrized):**
  - `test_inps_artigiano` - artigiano rates
  - `test_inps_commerciante` - commerciante rates
  - `test_inps_gestione_separata` - gestione separata
  - `test_inps_minimum_contribution` - minimum values
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run existing INPS tests
- **Coverage Target:** 95%+ for calculation code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] ATECO-based contribution rates
- [ ] Multiple gestioni supported
- [ ] 95%+ test coverage achieved

---

### DEV-351: IMU Calculator with Client Property

**Reference:** [FR-007: Calcoli Fiscali](./PRATIKO_2.0_REFERENCE.md#fr-007-calcoli-fiscali)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
IMU calculation requires property data. When client context available, should use stored property info.

**Solution:**
Create IMU calculator that can use client property data.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-348 (Client Context Injection)
- **Unlocks:** DEV-352 (Calculation History), DEV-353 (Accuracy Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/services/imu_calculator.py`

**Methods:**
- `calculate_imu(immobile, comune)` - Calculate IMU for single property
- `calculate_imu_prima_casa(rendita, comune)` - Calculate IMU for primary residence (often exempt)
- `calculate_imu_seconda_casa(rendita, comune, aliquota)` - Calculate IMU for secondary properties
- `get_aliquota_comunale(comune, tipo_immobile)` - Get municipal IMU rate

**Testing Requirements:**
- **TDD:** Write `tests/services/test_imu_calculator.py` FIRST
- **Unit Tests:**
  - `test_imu_prima_casa` - prima casa exemption
  - `test_imu_seconda_casa` - seconda casa rate
  - `test_imu_terreno` - terreno calculation
  - `test_imu_with_client_property` - uses client data
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 95%+ for calculation code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] IMU calculation with property data
- [ ] Client context integration
- [ ] 95%+ test coverage achieved

---

### DEV-352: Calculation History Storage

**Reference:** [FR-007: Calcoli Fiscali](./PRATIKO_2.0_REFERENCE.md#fr-007-calcoli-fiscali)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need to store calculation history for client records and audit.

**Solution:**
Create CalculationHistory model to store calculations.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-349 (IRPEF), DEV-350 (INPS), DEV-351 (IMU), DEV-307 (Migration)
- **Unlocks:** DEV-353 (Accuracy Tests), DEV-355 (Dashboard)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/models/calculation_history.py`

**Fields:**
- `id`: UUID (primary key)
- `studio_id`: UUID (FK to Studio)
- `client_id`: int (FK to Client, nullable)
- `calculation_type`: enum (IRPEF, INPS, IMU, IVA)
- `input_parameters`: JSONB (input values used)
- `result`: JSONB (calculation result)
- `calculated_by`: int (FK to User)
- `calculated_at`: datetime
- `notes`: text (nullable)

**Error Handling:**
- Invalid calculation type: HTTP 400, `"Tipo calcolo non valido"`
- Missing parameters: HTTP 422, `"Parametri mancanti per il calcolo"`
- Storage failure: HTTP 500, `"Errore salvataggio storico"`
- **Logging:** All errors MUST be logged with context at ERROR level

**Performance Requirements:**
- History storage: <100ms
- History retrieval: <200ms (paginated)
- Database queries: <50ms (p95)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_calculation_history.py` FIRST
- **Unit Tests:**
  - `test_history_creation` - stores calculation
  - `test_history_client_association` - links to client
  - `test_history_retrieval` - list history
  - `test_history_parameters` - stores input params
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/`
- **Coverage Target:** 80%+ for history code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Store calculation results
- [ ] Link to client
- [ ] Store input parameters
- [ ] 80%+ test coverage achieved

---

### DEV-353: Unit Tests for Calculation Accuracy

**Reference:** [FR-007: Calcoli Fiscali](./PRATIKO_2.0_REFERENCE.md#fr-007-calcoli-fiscali)

**Priority:** CRITICAL | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Tax calculations must be accurate. Need comprehensive parametrized tests with known inputs/outputs.

**Solution:**
Create exhaustive test suite for all calculation scenarios.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-349 (IRPEF), DEV-350 (INPS), DEV-351 (IMU), DEV-352 (History)
- **Unlocks:** Phase 6 start (all Phase 5 complete)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `tests/services/test_calculation_accuracy.py`

**Error Handling:**
- Test assertion failures: Descriptive error messages with expected vs actual
- Test setup failures: Clear logging of fixture initialization errors
- **Logging:** All test failures logged with context for debugging

**Performance Requirements:**
- Individual test execution: <500ms
- Full accuracy suite: <30s
- Parametrized test expansion: <5ms per case

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **Unit Tests (parametrized):**
  - 20+ IRPEF scenarios
  - 15+ INPS scenarios
  - 10+ IMU scenarios
  - Edge cases and boundary values
- **Test Data:** Real-world examples with verified results
- **Coverage Target:** 95%+ for all calculation code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] 50+ parametrized test cases
- [ ] All tax brackets covered
- [ ] Edge cases tested
- [ ] Results verified against official formulas
- [ ] 95%+ coverage achieved

---

## Phase 6: Dashboard & Analytics (Week 12) - 6 Tasks

### DEV-354: ROI Metrics Service

**Reference:** [FR-005: Dashboard ROI e Analytics](./PRATIKO_2.0_REFERENCE.md#fr-005-dashboard-roi-e-analytics)

**Figma Reference:** `DashboardPage.tsx` — Source: [`docs/figma-make-references/DashboardPage.tsx`](../figma-make-references/DashboardPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Professionals want to see the value PratikoAI provides: time saved, communications sent, regulations tracked.

**Solution:**
Create metrics service calculating ROI and usage statistics.

> **Navigation:** When implementing the frontend, add "Dashboard" menu item (BarChart3 icon, route `/dashboard`) to the user menu dropdown in `web/src/app/chat/components/ChatHeader.tsx`. Insert in the feature links section above "Il mio Account". Target menu layout:
> ```
> ┌──────────────────────┐
> │  Clienti             │  (DEV-308)
> │  Comunicazioni       │  (DEV-330)
> │  Procedure           │  (DEV-340)
> │  Dashboard           │  (DEV-354)
> │  Scadenze Fiscali    │  (DEV-385)
> │ ──────────────────── │
> │  Il mio Account      │
> │  [superuser items]   │
> │ ──────────────────── │
> │  Esci                │
> └──────────────────────┘
> ```

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-309 (ClientService), DEV-330 (CommunicationService), DEV-340 (ProceduraService)
- **Unlocks:** DEV-355 (Dashboard Aggregation), DEV-356 (Dashboard API)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **New Studio:** 0 data points → return zeros, not errors
- **Future Period:** period end > today → cap at today
- **Invalid Period:** start > end → HTTP 400, `"Periodo non valido"`
- **Division by Zero:** ROI with 0 costs → return infinity or skip metric
- **Stale Cache:** Metrics cached 1hr → background refresh, serve stale during
- **Timezone Edge:** Period crossing DST → use UTC for calculations
- **Partial Data:** Some metrics unavailable → return available, flag missing

**File:** `app/services/metrics_service.py`

**Methods:**
- `get_roi_metrics(studio_id, period)` - Calculate ROI
- `get_usage_stats(studio_id, period)` - Usage statistics
- `get_time_saved_estimate(studio_id)` - Estimated time savings

**Testing Requirements:**
- **TDD:** Write `tests/services/test_metrics_service.py` FIRST
- **Unit Tests:**
  - `test_roi_calculation` - correct ROI formula
  - `test_usage_stats_period` - respects period
  - `test_time_saved_calculation` - estimates time
  - `test_metrics_empty_studio` - handles new studios
- **Integration Tests:** Test with real data
- **Edge Case Tests:**
  - `test_new_studio_zeros` - empty studio returns zeros
  - `test_future_period_capped` - future date capped to today
  - `test_invalid_period_400` - start > end rejected
  - `test_division_by_zero_handled` - zero costs handled
  - `test_stale_cache_served` - cache refresh transparent
  - `test_partial_data_flagged` - missing metrics flagged
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for metrics code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Calculate ROI metrics
- [ ] Period filtering
- [ ] Time savings estimation
- [ ] 80%+ test coverage achieved

---

### DEV-355: Dashboard Data Aggregation

**Reference:** [FR-005: Dashboard ROI e Analytics](./PRATIKO_2.0_REFERENCE.md#fr-005-dashboard-roi-e-analytics)

**Figma Reference:** `DashboardPage.tsx` — Source: [`docs/figma-make-references/DashboardPage.tsx`](../figma-make-references/DashboardPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

> **Figma Gap Note (2026-02-25):** Figma's DashboardPage.tsx shows 3 distribution charts (clients per regime fiscale, per ATECO settore, per stato) and a matching statistics card (total matches, conversion rate, pending reviews) not originally scoped here. These are now covered by DEV-434 (Client Distribution Charts) and DEV-435 (Matching Statistics) which extend this task's aggregation service.

**Problem:**
Dashboard needs aggregated data: client count, active procedure, pending communications, recent matches.

**Solution:**
Create dashboard service aggregating data from multiple sources.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-354 (ROI Metrics), DEV-320 (Matching - for match stats)
- **Unlocks:** DEV-356 (Dashboard API), DEV-358 (Caching)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **New Studio:** No clients/comms/procedure → return all zeros, not null
- **Partial Data:** Some stats unavailable → return available, flag `"incomplete": true`
- **Large Dataset:** 100 clients × 1000 activities → use pagination/limits internally
- **Concurrent Updates:** Client added during aggregation → eventual consistency OK
- **Soft-Deleted Clients:** Exclude from counts unless explicitly requested
- **Date Range Empty:** No activity in period → return zeros with `"no_activity": true`
- **Future Date Request:** Period end > today → cap at today

**File:** `app/services/dashboard_service.py`

**Methods:**
- `aggregate_client_stats(studio_id)` - Aggregate client counts and status
- `aggregate_communication_stats(studio_id, period)` - Aggregate communication metrics
- `aggregate_procedura_stats(studio_id)` - Aggregate procedura progress statistics
- `aggregate_match_stats(studio_id, period)` - Aggregate recent match statistics
- `build_dashboard_response(studio_id, period)` - Build complete dashboard data

**Testing Requirements:**
- **TDD:** Write `tests/services/test_dashboard_service.py` FIRST
- **Unit Tests:**
  - `test_dashboard_client_stats` - client counts
  - `test_dashboard_communication_stats` - comm stats
  - `test_dashboard_procedura_stats` - procedura progress
  - `test_dashboard_match_stats` - recent matches
- **Edge Case Tests:**
  - `test_new_studio_returns_zeros` - empty studio handled
  - `test_partial_data_flagged` - incomplete data marked
  - `test_large_dataset_paginated` - performance maintained
  - `test_soft_deleted_excluded` - deleted clients not counted
  - `test_empty_period_zeros` - no activity handled
  - `test_future_date_capped` - end date capped to today
- **Integration Tests:** Test with multiple data sources
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for dashboard code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Aggregate from multiple sources
- [ ] Efficient queries
- [ ] Caching consideration
- [ ] 80%+ test coverage achieved

---

### DEV-356: Dashboard API Endpoint

**Reference:** [FR-005: Dashboard ROI e Analytics](./PRATIKO_2.0_REFERENCE.md#fr-005-dashboard-roi-e-analytics)

**Figma Reference:** `DashboardPage.tsx` — Source: [`docs/figma-make-references/DashboardPage.tsx`](../figma-make-references/DashboardPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

> **Figma Gap Note (2026-02-25):** Figma's DashboardPage.tsx shows a Week/Month/Year period selector that filters all dashboard data. This API should accept a `period` query parameter (see DEV-436).

**Problem:**
Frontend needs single endpoint to fetch all dashboard data.

**Solution:**
Create dashboard endpoint returning aggregated data.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-354 (ROI Metrics), DEV-355 (Dashboard Aggregation)
- **Unlocks:** DEV-359 (E2E Tests), Frontend integration

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Missing Period:** No dates provided → default to last 30 days
- **Invalid Period Format:** Non-ISO date → HTTP 400, `"Formato data non valido"`
- **Period Too Long:** >365 days → HTTP 400, `"Periodo massimo 1 anno"`
- **No Permission:** User not in studio → HTTP 403
- **Concurrent Requests:** Multiple dashboard calls → cache serves all
- **Service Timeout:** Aggregation >5s → HTTP 504, partial response if possible

**File:** `app/api/v1/dashboard.py`

**Endpoints:**
- `GET /api/v1/dashboard` - Get dashboard data
- `GET /api/v1/dashboard/roi` - Get ROI metrics

**Testing Requirements:**
- **TDD:** Write `tests/api/test_dashboard_api.py` FIRST
- **Integration Tests:**
  - `test_dashboard_200` - returns data
  - `test_dashboard_roi_200` - returns ROI
  - `test_dashboard_period_filter` - period works
  - `test_dashboard_tenant_isolation` - isolated data
- **Edge Case Tests:**
  - `test_missing_period_defaults_30d` - default period applied
  - `test_invalid_date_format_400` - bad date rejected
  - `test_period_over_year_400` - max period enforced
  - `test_no_permission_403` - non-member rejected
  - `test_timeout_504_partial` - graceful timeout
- **E2E Tests:** Part of DEV-359
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 80%+ for API code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Single endpoint for dashboard
- [ ] Period filtering
- [ ] Tenant isolation
- [ ] 80%+ test coverage achieved

---

### DEV-357: Activity Timeline Model

**Reference:** [FR-005: Dashboard ROI e Analytics](./PRATIKO_2.0_REFERENCE.md#fr-005-dashboard-roi-e-analytics)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Dashboard needs activity timeline showing recent actions (communications, procedure, matches).

**Solution:**
Create activity model or view aggregating actions.

**Agent Assignment:** @Primo (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-307 (Migration)
- **Unlocks:** DEV-355 (Dashboard Aggregation)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Same Timestamp:** Two activities same millisecond → secondary sort by ID
- **Deleted Entity:** Referenced client deleted → activity preserved with `"entity_deleted": true`
- **Activity Type Unknown:** New type added → fallback display, log warning
- **Bulk Actions:** 50 clients updated at once → single batch activity, not 50 individual
- **Empty Timeline:** New studio → empty array, not null
- **Actor Unknown:** System-triggered activity → `actor_id: null`, `"system": true`
- **Timezone Display:** Store UTC, display in user's TZ → conversion in API layer

**File:** `app/models/activity.py`

**Fields:**
- `id`: UUID (primary key)
- `studio_id`: UUID (FK to Studio)
- `user_id`: int (FK to User, nullable for system activities)
- `activity_type`: enum (CLIENT_CREATED, COMMUNICATION_SENT, PROCEDURA_COMPLETED, MATCH_FOUND, etc.)
- `entity_type`: str (client, communication, procedura, match)
- `entity_id`: str (ID of the related entity)
- `description`: str (human-readable description)
- `metadata`: JSONB (additional context)
- `created_at`: datetime

**Performance Requirements:**
- Activity creation: <50ms
- Timeline retrieval: <200ms (paginated, limit 50)
- Database queries: <50ms (p95)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_activity.py` FIRST
- **Unit Tests:**
  - `test_activity_creation` - activity recorded
  - `test_activity_types` - different types
  - `test_activity_timeline` - ordered by time
  - `test_activity_filtering` - by type
- **Edge Case Tests:**
  - `test_same_timestamp_secondary_sort` - ID tiebreaker
  - `test_deleted_entity_preserved` - orphan activity kept
  - `test_unknown_type_fallback` - graceful handling
  - `test_bulk_action_batched` - single activity for batch
  - `test_empty_timeline_array` - empty returns []
  - `test_system_activity_no_actor` - null actor handled
  - `test_utc_storage` - timestamps stored in UTC
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/`
- **Coverage Target:** 80%+ for activity code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Track different activity types
- [ ] Chronological ordering
- [ ] 80%+ test coverage achieved

---

### DEV-358: Dashboard Caching

**Reference:** [FR-005: Dashboard ROI e Analytics](./PRATIKO_2.0_REFERENCE.md#fr-005-dashboard-roi-e-analytics)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Dashboard queries multiple tables and should be cached to improve performance.

**Solution:**
Add Redis caching to dashboard service.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-355 (Dashboard Aggregation), Existing Redis cache infrastructure
- **Unlocks:** DEV-359 (E2E Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/services/dashboard_service.py`
- **Affected Files:**
  - `app/api/v1/dashboard.py` (uses cached service)
  - `app/core/redis.py` (cache infrastructure)
- **Related Tests:**
  - `tests/services/test_dashboard_service.py` (direct)
  - `tests/api/test_dashboard.py` (consumer)
- **Baseline Command:** `pytest tests/services/test_dashboard_service.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing dashboard_service.py reviewed
- [ ] Redis cache patterns understood

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Redis Down:** Connection failed → bypass cache, query DB directly, log warning
- **Partial Cache Miss:** Some keys missing → fetch missing, merge with cached
- **TTL Race:** Cache expires during request → fetch fresh, don't serve stale
- **Invalidation Propagation:** Multi-instance → use Redis pub/sub for invalidation
- **Cache Key Collision:** Different periods same key → include period in key hash
- **Large Payload:** >1MB cached data → compression before storage
- **Cold Start:** First request → cache miss, populate async after response

**File:** `app/services/dashboard_service.py` (extend)

**Methods:**
- `get_cached_dashboard(studio_id, period)` - Retrieve from cache if available
- `set_dashboard_cache(studio_id, period, data)` - Store dashboard data in cache
- `invalidate_dashboard_cache(studio_id)` - Invalidate cache on data changes
- `get_cache_key(studio_id, period)` - Generate cache key with period hash

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_dashboard_cache_hit` - returns cached
  - `test_dashboard_cache_miss` - fetches fresh
  - `test_dashboard_cache_invalidation` - clears on update
  - `test_dashboard_cache_ttl` - respects TTL
- **Edge Case Tests:**
  - `test_redis_down_bypass` - graceful degradation
  - `test_partial_miss_merged` - partial data handled
  - `test_ttl_race_fresh_fetch` - no stale during expiry
  - `test_key_includes_period` - different periods different keys
  - `test_large_payload_compressed` - compression applied
  - `test_cold_start_async_populate` - first request not delayed
- **Integration Tests:** Test with Redis
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for caching code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Cache dashboard data
- [ ] Invalidate on updates
- [ ] Configurable TTL
- [ ] 80%+ test coverage achieved

---

### DEV-359: E2E Tests for Dashboard

**Reference:** [FR-005: Dashboard ROI e Analytics](./PRATIKO_2.0_REFERENCE.md#fr-005-dashboard-roi-e-analytics)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need end-to-end tests verifying dashboard data accuracy.

**Solution:**
Create E2E tests for dashboard flow.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-354 (ROI Metrics), DEV-355 (Aggregation), DEV-356 (API), DEV-357 (Activity), DEV-358 (Caching)
- **Unlocks:** Phase 7 start (all Phase 6 complete)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `tests/e2e/test_dashboard_flow.py`

**Error Handling:**
- Test assertion failures: Descriptive error messages with expected vs actual
- Fixture setup failures: Clear logging of data setup errors
- **Logging:** All test failures logged with context for debugging

**Performance Requirements:**
- Individual E2E test: <5s
- Full dashboard E2E suite: <30s
- Data accuracy verification: <2s per check

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **E2E Tests:**
  - `test_dashboard_data_accuracy` - data matches source
  - `test_dashboard_roi_calculation` - ROI is correct
  - `test_dashboard_period_filtering` - periods work
  - `test_dashboard_tenant_isolation` - no cross-tenant
- **Coverage Target:** Full dashboard coverage

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Dashboard data accuracy verified
- [ ] ROI calculation verified
- [ ] Tenant isolation verified

---

## Phase 7: Document Enhancement (Week 13) - 6 Tasks

### DEV-360: Bilancio Document Parser

**Reference:** [FR-008: Upload e Analisi Documenti](./PRATIKO_2.0_REFERENCE.md#fr-008-upload-e-analisi-documenti)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Professionals upload client financial statements (bilanci). Need to extract key data (fatturato, utile, etc.).

**Solution:**
Create bilancio parser using existing document parsing infrastructure.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** Existing document parsing infrastructure
- **Unlocks:** DEV-363 (Chat Context), DEV-365 (Integration Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Bilancio Abbreviato:** Simplified format → use abbreviato parser, fewer fields
- **Bilancio Consolidato:** Group statements → extract consolidated figures only
- **Negative Utile:** Loss year → return negative value, not error
- **Currency Symbols:** € vs EUR vs "euro" → normalize to numeric
- **Multi-Year Comparison:** Previous year columns → extract both, label accordingly
- **Scanned PDF:** Image-based → trigger OCR pipeline, flag `"ocr_used": true`
- **Missing Fields:** Some fields not present → return partial, flag `"incomplete": true`
- **Format Year Variance:** 2020 vs 2024 format → version detection + appropriate parser

**File:** `app/services/bilancio_parser_service.py`

**Methods:**
- `parse_bilancio(file_path)` - Parse bilancio PDF and extract data
- `extract_fatturato(parsed_data)` - Extract revenue from parsed bilancio
- `extract_utile(parsed_data)` - Extract profit from parsed bilancio
- `extract_attivo_passivo(parsed_data)` - Extract balance sheet data
- `detect_bilancio_type(file_path)` - Detect if abbreviato or ordinario

**Testing Requirements:**
- **TDD:** Write `tests/services/test_bilancio_parser_service.py` FIRST
- **Unit Tests:**
  - `test_parse_bilancio_pdf` - extracts from PDF
  - `test_extract_fatturato` - finds revenue
  - `test_extract_utile` - finds profit
  - `test_extract_attivo_passivo` - balance sheet
  - `test_parse_invalid_format` - handles errors
- **Edge Case Tests:**
  - `test_bilancio_abbreviato_parser` - simplified format handled
  - `test_negative_utile_loss` - loss returns negative
  - `test_currency_normalization` - symbols converted
  - `test_multi_year_extracted` - both years returned
  - `test_scanned_pdf_ocr_triggered` - OCR fallback works
  - `test_missing_fields_partial` - incomplete flagged
  - `test_format_version_detection` - old format handled
- **Integration Tests:** Test with sample bilanci
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for parser code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Parse bilancio PDFs
- [ ] Extract key financial data
- [ ] Associate with client
- [ ] 80%+ test coverage achieved

---

### DEV-361: CU Document Parser

**Reference:** [FR-008: Upload e Analisi Documenti](./PRATIKO_2.0_REFERENCE.md#fr-008-upload-e-analisi-documenti)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Certificazione Unica (CU) documents contain employee income data. Need to parse and extract.

**Solution:**
Create CU parser for extracting income and withholding data.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** Existing document parsing infrastructure
- **Unlocks:** DEV-365 (Integration Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **CU Dipendente vs Autonomo:** Different layouts → detect type, use appropriate parser
- **Multiple CU:** Same CF, multiple employers → return array of results
- **Old CU Format:** Pre-2024 layout → version detection, fallback parser
- **Encrypted PDF:** Password protected → HTTP 422, `"PDF protetto"`
- **Scanned CU:** Image-based → trigger OCR, lower confidence threshold
- **Partial Data:** Some boxes empty → return extracted, flag missing
- **Invalid CF in CU:** Checksum fails → log warning, return with `"cf_valid": false`
- **Euro Cents:** Amount with cents → preserve decimal precision

**File:** `app/services/cu_parser_service.py`

**Methods:**
- `parse_cu(file_path)` - Parse CU PDF and extract data
- `extract_redditi(parsed_data)` - Extract income data from CU
- `extract_ritenute(parsed_data)` - Extract withholdings from CU
- `extract_codice_fiscale(parsed_data)` - Extract CF from CU
- `detect_cu_type(file_path)` - Detect if dipendente or autonomo

**Testing Requirements:**
- **TDD:** Write `tests/services/test_cu_parser_service.py` FIRST
- **Unit Tests:**
  - `test_parse_cu_pdf` - extracts from PDF
  - `test_extract_redditi` - finds income
  - `test_extract_ritenute` - finds withholdings
  - `test_extract_cf` - finds codice fiscale
- **Edge Case Tests:**
  - `test_cu_dipendente_vs_autonomo` - type detection works
  - `test_multiple_cu_array` - multiple employers returned
  - `test_old_cu_format_fallback` - pre-2024 handled
  - `test_encrypted_pdf_rejected` - password protected fails
  - `test_scanned_cu_ocr` - OCR triggered for images
  - `test_partial_data_flagged` - missing boxes noted
  - `test_invalid_cf_flagged` - bad checksum marked
  - `test_decimal_precision` - cents preserved
- **Integration Tests:** Test with sample CUs
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for parser code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Parse CU documents
- [ ] Extract income data
- [ ] Associate with client
- [ ] 80%+ test coverage achieved

---

### ~~DEV-362: Client Document Association~~ REMOVED

> **Removed:** This task described persistent client-document storage (linking uploaded files to clients permanently). This contradicts FR-008's explicit GDPR policy: documents are **temporary only** (session-scoped, 48h max, no persistence). Document upload and analysis is already implemented via the existing `/api/v1/documents/upload` and `/api/v1/documents/{id}/analyze` endpoints. No persistent "client file cabinet" is needed.

---

### DEV-363: Document Context in Chat

**Reference:** [FR-008: Upload e Analisi Documenti](./PRATIKO_2.0_REFERENCE.md#fr-008-upload-e-analisi-documenti)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
When discussing a client, AI should have access to their uploaded documents.

**Solution:**
Include client documents in RAGState context.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-360 (Bilancio Parser), Existing context_builder_node
- **Unlocks:** DEV-365 (Integration Tests)

> **Note:** Documents in chat context come from temporary uploads (FR-008 session-scoped), not from persistent client-document associations (DEV-362 was removed).

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/core/langgraph/nodes/context_builder_node.py`
- **Affected Files:**
  - `app/core/langgraph/graph.py` (node consumer)
  - `app/schemas/rag_state.py` (adds document context to state)
- **Related Tests:**
  - `tests/langgraph/test_context_builder_node.py` (direct)
  - `tests/integration/test_rag_pipeline.py` (consumer)
- **Baseline Command:** `pytest tests/langgraph/test_context_builder_node.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing context_builder_node.py reviewed
- [ ] Document retrieval patterns understood

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Context window overflow | MEDIUM | Summarize documents |
| Slow document retrieval | LOW | Cache parsed documents |

**Edge Cases:**
- **No Documents:** Client has no uploads → skip document context, no error
- **Too Many Documents:** 50+ documents → include only 5 most recent, flag `"truncated": true`
- **Large Document:** Single doc >10KB text → summarize to 2KB max
- **Mixed Languages:** Italian + English docs → preserve both, no translation
- **Document Expired:** 30-min temp doc expired → exclude, log warning
- **Parsing Failed:** Document couldn't be parsed → exclude with reason in metadata
- **Circular Reference:** Document mentions query topic → de-duplicate context

**File:** `app/core/langgraph/nodes/context_builder_node.py` (extend)

**Methods:**
- `inject_document_context(state, client_id)` - Inject client documents into RAGState
- `summarize_document(document)` - Summarize large documents for context window
- `filter_relevant_documents(documents, query)` - Filter documents by relevance to query
- `format_document_context(documents)` - Format documents for LLM consumption

**Performance Requirements:**
- Document context injection: <200ms
- Document summarization: <500ms per document
- Context building: <300ms total
- Database queries: <50ms (p95)

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_context_includes_documents` - docs in context
  - `test_context_document_summary` - summarized content
  - `test_context_no_documents` - handles missing
- **Edge Case Tests:**
  - `test_no_documents_skipped` - empty client no error
  - `test_too_many_documents_truncated` - 50+ limited to 5
  - `test_large_document_summarized` - >10KB compressed
  - `test_expired_document_excluded` - temp docs removed
  - `test_parsing_failed_excluded` - unparseable skipped
  - `test_context_deduplication` - no circular refs
- **Integration Tests:** Test with RAGState
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/langgraph/`
- **Coverage Target:** 80%+ for context code

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Include documents in context
- [ ] Summarize for context window
- [ ] 80%+ test coverage achieved

---

### ~~DEV-364: Document API Endpoints~~ REMOVED

> **Removed:** This task described client-scoped document CRUD endpoints (`POST /clients/{id}/documents`, etc.) for persistent document management. This contradicts FR-008's GDPR policy. Document upload/analysis API already exists at `app/api/v1/documents.py` with temporary storage (48h expiry, encrypted, auto-cleanup). No additional persistent endpoints needed.

---

### DEV-365: Document Parser Integration Tests

**Reference:** [FR-008: Upload e Analisi Documenti](./PRATIKO_2.0_REFERENCE.md#fr-008-upload-e-analisi-documenti)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Document parsers need integration tests with real sample documents.

**Solution:**
Create integration tests with sample PDFs.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-360 (Bilancio Parser), DEV-361 (CU Parser), DEV-363 (Chat Context)
- **Unlocks:** Phase 8 start (all Phase 7 complete)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `tests/integration/test_document_parsers.py`

**Error Handling:**
- Parser failures: Descriptive error messages with file context
- Invalid PDF format: Clear logging of format detection errors
- OCR failures: Log OCR confidence and fallback behavior
- **Logging:** All test failures logged with context for debugging

**Performance Requirements:**
- Individual parser test: <2s (including PDF processing)
- Full parser integration suite: <30s
- Performance benchmark tests: <5s per document type

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **Integration Tests:**
  - `test_bilancio_parser_real_pdf` - real bilancio
  - `test_cu_parser_real_pdf` - real CU
  - `test_parser_error_handling` - malformed PDFs
  - `test_parser_performance` - timing
- **Test Data:** Sample anonymized documents
- **Coverage Target:** 80%+ for parser code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests with real PDFs
- [ ] Error handling verified
- [ ] Performance benchmarked

---

## Phase 8: Frontend Integration Points (Week 14) - 6 Tasks

### DEV-366: OpenAPI Schema Validation

**Reference:** [Non-Functional Requirements](./PRATIKO_2.0_REFERENCE.md#4-requisiti-non-funzionali)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Frontend relies on OpenAPI schema for type generation. Must ensure schema is accurate and complete.

**Solution:**
Add schema validation and generate TypeScript types.

**Agent Assignment:** @Ezio (primary), @Livia (frontend)

**Dependencies:**
- **Blocking:** All API endpoints (DEV-311, DEV-312, DEV-326, DEV-332, DEV-342, DEV-356)
- **Unlocks:** DEV-370 (Frontend SDK Types)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid input: HTTP 400, `"Dati non validi"`
- Not found: HTTP 404, `"Risorsa non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Server error: HTTP 500, `"Errore interno del server"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Response time: <200ms (p95)
- Database queries: <50ms (p95)
- Concurrent requests: Handle 100 concurrent requests

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/api/openapi.py`

**Methods:**
- `validate_openapi_schema()` - Validate OpenAPI schema completeness
- `check_endpoint_documentation()` - Verify all endpoints are documented
- `validate_response_schemas()` - Ensure all responses have schemas
- `generate_typescript_types()` - Generate TypeScript types from schema

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_openapi_schema_valid` - schema is valid
  - `test_openapi_all_endpoints` - all endpoints documented
  - `test_openapi_response_schemas` - responses defined
  - `test_openapi_examples` - examples provided
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 100% API endpoint documentation

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All endpoints documented
- [ ] Response schemas complete
- [ ] Examples provided
- [ ] TypeScript types generated

---

### DEV-367: API Error Response Standardization

**Reference:** [Non-Functional Requirements](./PRATIKO_2.0_REFERENCE.md#4-requisiti-non-funzionali)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Error responses must be consistent for frontend to handle properly.

**Solution:**
Standardize error response format across all endpoints.

**Agent Assignment:** @Ezio (primary), @Livia (frontend), @Clelia (tests)

**Dependencies:**
- **Blocking:** All existing API endpoints (foundation must exist)
- **Unlocks:** DEV-370 (Frontend SDK Types), all future API development

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/api/error_handlers.py`
- **Affected Files:**
  - `app/api/v1/*.py` (all API endpoints use error handlers)
  - `app/core/exceptions.py` (exception definitions)
- **Related Tests:**
  - `tests/api/test_error_handlers.py` (direct)
  - `tests/api/test_*.py` (all API tests may be affected)
- **Baseline Command:** `pytest tests/api/ -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing error handling patterns reviewed
- [ ] All API endpoints identified for migration

**Error Handling:**
- This task DEFINES error handling - implement standard format:
  - `{"error": {"code": "ERROR_CODE", "message": "Human readable", "details": {...}}}`
  - HTTP codes: 400 (validation), 401 (auth), 403 (forbidden), 404 (not found), 422 (unprocessable), 500 (server)
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Error serialization: <5ms
- No additional latency to success responses

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/api/error_handlers.py`

**Methods:**
- `format_error_response(error, status_code)` - Format error to standard structure
- `handle_validation_error(exc)` - Handle Pydantic validation errors (HTTP 400)
- `handle_not_found_error(exc)` - Handle not found errors (HTTP 404)
- `handle_server_error(exc)` - Handle internal server errors (HTTP 500)
- `log_error_context(error, request)` - Log error with request context

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_error_format_standard` - format consistent
  - `test_error_400_format` - validation errors
  - `test_error_401_format` - auth errors
  - `test_error_404_format` - not found
  - `test_error_500_format` - server errors
- **Integration Tests:** Test across all endpoints
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 100% error handling

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Standard error format
- [ ] All endpoints return consistent errors
- [ ] Documented in OpenAPI

---

### DEV-368: Pagination Standardization

**Reference:** [Non-Functional Requirements](./PRATIKO_2.0_REFERENCE.md#4-requisiti-non-funzionali)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
List endpoints need consistent pagination format.

**Solution:**
Standardize pagination across all list endpoints.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-312 (Client API), DEV-326 (Matching API), DEV-332 (Communication API) - any list endpoint
- **Unlocks:** All list endpoints use consistent pagination

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid page: HTTP 400, `"Numero pagina non valido"`
- Invalid per_page: HTTP 400, `"Items per pagina deve essere tra 1 e 100"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Pagination metadata calculation: <10ms
- Total count query: Use COUNT(*) OVER() for efficiency

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/api/pagination.py`

**Methods:**
- `paginate(query, page, per_page)` - Apply pagination to SQLAlchemy query
- `build_pagination_metadata(total, page, per_page)` - Build pagination metadata
- `build_pagination_links(request, total, page, per_page)` - Build next/prev links
- `validate_pagination_params(page, per_page)` - Validate pagination parameters

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_pagination_format` - format consistent
  - `test_pagination_metadata` - includes total, pages
  - `test_pagination_links` - next/prev links
  - `test_pagination_empty` - handles empty
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 100% pagination coverage

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Standard pagination format
- [ ] Total count included
- [ ] Next/prev links

---

### DEV-369: WebSocket Events for Real-time Updates

**Reference:** [Non-Functional Requirements](./PRATIKO_2.0_REFERENCE.md#4-requisiti-non-funzionali)

**Figma Reference:** `ChatPage.tsx` (real-time patterns) in [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Frontend needs real-time updates for matches, communications, and progress.

**Solution:**
Create WebSocket endpoint for real-time events.

**Agent Assignment:** @Ezio (primary), @Livia (frontend), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-320 (NormativeMatchingService), DEV-330 (CommunicationService) - event sources
- **Unlocks:** Real-time frontend updates, DEV-386 (Calendar Widget live updates)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Connection failure: Auto-reconnect with exponential backoff
- Invalid token: Close with 4001, `"Token non valido"`
- Tenant mismatch: Close with 4003, `"Accesso non autorizzato"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Connection handshake: <100ms
- Event delivery latency: <50ms
- Max concurrent connections per studio: 50

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `app/api/websocket.py`

**Endpoints:**
- `WS /api/v1/ws/events` - WebSocket endpoint for real-time events

**Event Types:**
- `MATCH_FOUND` - New normative match discovered
- `COMMUNICATION_STATUS` - Communication status changed
- `PROCEDURA_PROGRESS` - Procedura progress updated
- `DEADLINE_REMINDER` - Upcoming deadline notification

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_websocket_connection` - connects
  - `test_websocket_match_event` - receives match
  - `test_websocket_communication_event` - receives comm
  - `test_websocket_tenant_isolation` - isolated events
- **Integration Tests:** Test WebSocket flow
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 80%+ for WebSocket code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] WebSocket endpoint
- [ ] Event types defined
- [ ] Tenant isolation
- [ ] 80%+ test coverage achieved

---

### DEV-370: Frontend SDK Types Generation

**Reference:** [Non-Functional Requirements](./PRATIKO_2.0_REFERENCE.md#4-requisiti-non-funzionali)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Frontend needs TypeScript types generated from OpenAPI schema.

**Solution:**
Set up automatic type generation from OpenAPI.

**Agent Assignment:** @Livia (primary), @Ezio (backend)

**Dependencies:**
- **Blocking:** DEV-366 (OpenAPI Schema Validation), DEV-367 (Error Response Standardization)
- **Unlocks:** Type-safe frontend development, reduces integration bugs

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Type generation: <30s (build-time, not runtime)
- Types must regenerate on every OpenAPI change

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `scripts/generate_types.sh`

**Methods:**
- `generate_types.sh` - Shell script to generate TypeScript types
- `validate_types()` - Validate generated types compile correctly
- `compare_types()` - Compare with previous version for breaking changes

**Error Handling:**
- OpenAPI fetch failure: Exit with error code 1, log URL
- Type generation failure: Log generator output, exit with error
- Compilation failure: Log TypeScript errors, exit with error
- **Logging:** All errors logged to stderr with timestamp

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_types_generated` - types file created
  - `test_types_complete` - all models included
  - `test_types_compile` - TypeScript compiles
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Frontend type check
- **Coverage Target:** 100% model types

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Type generation script
- [ ] All models covered
- [ ] Types compile in frontend

---

### DEV-371: Full User Journey E2E Test

**Reference:** [Non-Functional Requirements](./PRATIKO_2.0_REFERENCE.md#4-requisiti-non-funzionali)

**Figma Reference:** `SignUpPage.tsx` → `ChatPage.tsx` → `ClientListPage.tsx` (full journey) — Source: [`docs/figma-make-references/ClientListPage.tsx`](../figma-make-references/ClientListPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** CRITICAL | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Need comprehensive E2E test covering the entire PratikoAI 2.0 user journey.

**Solution:**
Create complete E2E test from registration to dashboard.

**Agent Assignment:** @Clelia (primary), @Ezio (support)

**Dependencies:**
- **Blocking:** All Phase 0-8 tasks (this tests the complete system)
  - DEV-300-207 (Models), DEV-308-219 (Services), DEV-320-229 (Matching)
  - DEV-330-239 (Communications), DEV-340-253 (Procedure/Calculations)
  - DEV-354-265 (Document Analysis), DEV-366-270 (API Quality)
- **Unlocks:** Production deployment gate (must pass)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Full E2E test suite: <60s total execution
- Individual test steps: <5s each

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `tests/e2e/test_pratikoai_2_0_flow.py`

**Error Handling:**
- Step failures: Descriptive error messages with step number and context
- Integration failures: Clear logging of which service failed
- Timeout failures: Log step duration and timeout threshold
- **Logging:** All test failures logged with full step trace

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **E2E Tests:**
  - Step 1: Register new user
  - Step 2: Create studio
  - Step 3: Import clients from Excel
  - Step 4: Ask question about regulation
  - Step 5: See matched clients in response
  - Step 6: Create communication for matched clients
  - Step 7: Approve communication
  - Step 8: Send communication
  - Step 9: View dashboard metrics
- **Coverage Target:** Full user journey

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Complete user journey tested
- [ ] All integrations verified
- [ ] <60s total execution time
- [ ] Documented test scenario

---

## Phase 9: GDPR Compliance Enhancement (Week 15) - 8 Tasks

### DEV-372: Data Processing Agreement (DPA) Model

**Reference:** [GDPR e Gestione Dati Clienti](./PRATIKO_2.0_REFERENCE.md#11-gdpr-e-gestione-dati-clienti)

**Priority:** CRITICAL | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
GDPR requires DPA before processing client data. Need to track DPA acceptance.

**Solution:**
Create DPA model with version tracking and acceptance records.

**Agent Assignment:** @Primo (primary), @Severino (legal review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model), DEV-307 (Migration infrastructure)
- **Unlocks:** DEV-373 (DPA Acceptance Workflow), DEV-378 (GDPR Dashboard)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Missing DPA version: HTTP 500 (system config error), alert ops team
- Concurrent acceptance: Use optimistic locking to prevent race conditions
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- DPA check: <10ms (cached in Redis after first check per session)

**Edge Cases:**
- **DPA Version Upgrade:** New DPA version → require re-acceptance for new features only
- **Acceptance Revocation:** User wants to revoke → must delete all client data first
- **Concurrent Acceptance:** Two users accept simultaneously → both recorded (no conflict)
- **Missing IP Address:** IP logging fails → log null, still accept
- **Cache Stale:** Redis has outdated acceptance → short TTL (5min), DB check on miss
- **Multiple DPA Types:** Different DPA for different features → track per type
- **Audit Trail Immutable:** Acceptance records cannot be modified or deleted

**File:** `app/models/dpa.py`

**Fields:**
- `id`: UUID (primary key)
- `version`: str (e.g., "1.0", "2.0")
- `content`: text (full DPA text)
- `effective_date`: date (when this version becomes active)
- `is_current`: bool (is this the current version)
- `created_at`: datetime

**DPAAcceptance Fields:**
- `id`: UUID (primary key)
- `studio_id`: UUID (FK to Studio)
- `user_id`: int (FK to User who accepted)
- `dpa_id`: UUID (FK to DPA version)
- `accepted_at`: datetime
- `ip_address`: str (nullable)
- `user_agent`: str (nullable)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_dpa.py` FIRST
- **Unit Tests:**
  - `test_dpa_creation` - DPA version created
  - `test_dpa_acceptance` - acceptance recorded
  - `test_dpa_required` - blocks without acceptance
  - `test_dpa_version_tracking` - versions tracked
- **Edge Case Tests:**
  - `test_dpa_version_upgrade_reaccept` - new version requires accept
  - `test_revocation_requires_data_deletion` - revoke blocked if data exists
  - `test_concurrent_acceptance_no_conflict` - both recorded
  - `test_missing_ip_logged_null` - null IP allowed
  - `test_cache_miss_db_check` - stale cache falls back to DB
  - `test_audit_trail_immutable` - records cannot be modified
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/`
- **Coverage Target:** 95%+ for GDPR code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] DPA version tracking
- [ ] Acceptance records
- [ ] Block processing without DPA
- [ ] 95%+ test coverage achieved

---

### DEV-373: DPA Acceptance Workflow

**Reference:** [GDPR e Gestione Dati Clienti](./PRATIKO_2.0_REFERENCE.md#11-gdpr-e-gestione-dati-clienti)

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Users must accept DPA before adding clients. Need workflow enforcement.

**Solution:**
Create DPA service with acceptance workflow and API enforcement.

**Agent Assignment:** @Ezio (primary), @Severino (legal review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-372 (DPA Model)
- **Unlocks:** DEV-309 (ClientService) - cannot create clients without DPA, DEV-378 (Dashboard)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- DPA not accepted: HTTP 403, `"Accettare il DPA prima di aggiungere clienti"`
- DPA version outdated: HTTP 428, `"Nuova versione DPA disponibile, riaccettazione richiesta"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- DPA acceptance: <100ms
- DPA version check: <10ms (cached)

**Edge Cases:**
- **Already Accepted:** User accepts again → idempotent, update timestamp
- **Minor Version Update:** v1.0 → v1.1 → auto-accept if major unchanged
- **Major Version Update:** v1.x → v2.0 → require explicit re-acceptance
- **Expired Session:** Accept during expired session → HTTP 401, preserve acceptance intent
- **Partial Acceptance:** Accept DPA A but not B → track per-DPA, block only missing
- **Middleware Bypass:** Direct DB access → application-level check always, not just API
- **Version Rollback:** Downgrade DPA version → reject, only forward upgrades allowed

**File:** `app/services/dpa_service.py`

**Methods:**
- `get_current_dpa()` - Get the current DPA version
- `check_dpa_accepted(studio_id)` - Check if studio has accepted current DPA
- `accept_dpa(studio_id, user_id, ip_address)` - Record DPA acceptance
- `require_dpa_acceptance(studio_id)` - Middleware to enforce DPA acceptance
- `get_acceptance_history(studio_id)` - Get DPA acceptance history for studio

**Testing Requirements:**
- **TDD:** Write `tests/services/test_dpa_service.py` FIRST
- **Unit Tests:**
  - `test_dpa_acceptance_required` - enforces acceptance
  - `test_dpa_accept` - records acceptance
  - `test_dpa_version_update` - handles new versions
  - `test_client_blocked_without_dpa` - blocks client creation
- **Edge Case Tests:**
  - `test_already_accepted_idempotent` - reaccept updates timestamp
  - `test_minor_version_auto_accept` - v1.0→v1.1 auto-accepted
  - `test_major_version_requires_accept` - v1→v2 blocked
  - `test_partial_dpa_tracked` - per-DPA tracking works
  - `test_version_rollback_rejected` - downgrade fails
- **E2E Tests:** Part of DEV-379
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 95%+ for DPA code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Enforce DPA acceptance
- [ ] Version update workflow
- [ ] Block client operations without DPA
- [ ] 95%+ test coverage achieved

---

### DEV-374: Data Breach Notification Model

**Reference:** [GDPR e Gestione Dati Clienti](./PRATIKO_2.0_REFERENCE.md#11-gdpr-e-gestione-dati-clienti)

**Priority:** CRITICAL | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
GDPR requires breach notification within 72 hours. Need to track and manage breaches.

**Solution:**
Create breach notification model with status tracking.

**Agent Assignment:** @Primo (primary), @Severino (compliance), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-307 (Migration infrastructure)
- **Unlocks:** DEV-375 (Breach Notification Service), DEV-378 (GDPR Dashboard)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid status transition: HTTP 400, `"Transizione stato violazione non valida"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Breach creation: <50ms (critical path)
- 72h deadline calculation: immediate on creation

**Edge Cases:**
- **Weekend/Holiday:** 72h includes non-business days → calendar days, not business days
- **Multiple Breaches:** Two breaches same day → each has own record and deadline
- **Breach Escalation:** Minor → major impact discovered → update severity, recalculate deadline
- **Cross-Studio Breach:** Affects multiple studios → create per-studio records, link parent
- **False Positive:** Breach determined to be non-breach → status CLOSED_NO_BREACH, preserve record
- **Timezone Calculation:** 72h calculated in UTC → display in user's TZ
- **Deadline Extension:** Legitimate extension needed → record reason, update deadline with audit

**File:** `app/models/breach_notification.py`

**Fields:**
- `id`: UUID (primary key)
- `studio_id`: UUID (FK to Studio, nullable for platform-wide breaches)
- `reported_by`: int (FK to User)
- `breach_type`: enum (DATA_LEAK, UNAUTHORIZED_ACCESS, SYSTEM_COMPROMISE, etc.)
- `severity`: enum (LOW, MEDIUM, HIGH, CRITICAL)
- `description`: text (description of the breach)
- `affected_data_categories`: ARRAY[str] (types of data affected)
- `estimated_affected_count`: int (number of affected data subjects)
- `status`: enum (REPORTED, ASSESSING, NOTIFYING_AUTHORITY, NOTIFYING_USERS, RESOLVED, CLOSED)
- `discovered_at`: datetime
- `reported_at`: datetime
- `deadline_at`: datetime (72h from discovery)
- `authority_notified_at`: datetime (nullable)
- `users_notified_at`: datetime (nullable)
- `resolution_notes`: text (nullable)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_breach_notification.py` FIRST
- **Unit Tests:**
  - `test_breach_creation` - breach recorded
  - `test_breach_status_workflow` - status transitions
  - `test_breach_deadline_calculation` - 72h deadline
  - `test_breach_notification_sent` - tracks sending
- **Edge Case Tests:**
  - `test_weekend_included_in_72h` - calendar days used
  - `test_multiple_breaches_same_day` - separate records
  - `test_severity_escalation_recalc` - deadline updated
  - `test_cross_studio_linked` - parent breach linked
  - `test_false_positive_closed` - no-breach status preserved
  - `test_utc_deadline_display` - TZ conversion works
  - `test_extension_audited` - deadline change logged
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/`
- **Coverage Target:** 95%+ for breach code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Breach recording
- [ ] 72h deadline tracking
- [ ] Notification status
- [ ] 95%+ test coverage achieved

---

### DEV-375: Breach Notification Service

**Reference:** [GDPR e Gestione Dati Clienti](./PRATIKO_2.0_REFERENCE.md#11-gdpr-e-gestione-dati-clienti)

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need service to manage breach lifecycle: detection, assessment, notification.

**Solution:**
Create breach service with workflow and deadline tracking.

**Agent Assignment:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-374 (Breach Model), DEV-333 (Email sending for notifications)
- **Unlocks:** DEV-378 (GDPR Dashboard), DEV-379 (GDPR E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Notification send failure: Retry 3x, then HTTP 500, log for manual follow-up
- Authority API unavailable: Queue for retry, alert compliance team
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Report breach: <100ms
- 72h deadline check: runs every hour as background job

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Miss 72h deadline | CRITICAL | Hourly monitoring job + email alerts at 48h, 24h, 12h |
| Authority API failure | HIGH | Manual fallback procedure documented |

**Edge Cases:**
- **Authority Endpoint Down:** API unavailable → queue notification, retry every 15min
- **Partial Notification:** Authority notified but users pending → status AUTHORITY_NOTIFIED, continue
- **No Affected Users:** Breach with 0 data subjects → still notify authority if required
- **Large Affected Set:** 10K+ affected users → batch notifications, track progress
- **Deadline Already Passed:** Breach discovered after 72h → log violation, notify anyway
- **Assessment Incomplete:** Report submitted before assessment done → block, require completion
- **Concurrent Assessment:** Two users assess same breach → merge assessments, log conflict

**File:** `app/services/breach_notification_service.py`

**Methods:**
- `report_breach(studio_id, breach_data)` - Create new breach report
- `assess_breach(breach_id, assessment)` - Complete breach assessment
- `notify_authority(breach_id)` - Notify data protection authority
- `notify_affected_users(breach_id)` - Notify affected data subjects
- `check_deadline_compliance()` - Background job to check 72h deadlines
- `get_active_breaches(studio_id)` - Get all unresolved breaches
- `resolve_breach(breach_id, resolution_notes)` - Mark breach as resolved

**Testing Requirements:**
- **TDD:** Write `tests/services/test_breach_notification_service.py` FIRST
- **Unit Tests:**
  - `test_report_breach` - creates record
  - `test_assess_breach` - assessment workflow
  - `test_notify_authority` - authority notification
  - `test_notify_affected` - affected party notification
  - `test_deadline_alert` - 72h deadline monitoring
- **Edge Case Tests:**
  - `test_authority_down_queued` - API failure retried
  - `test_partial_notification_tracked` - partial status preserved
  - `test_zero_affected_notified` - authority notified anyway
  - `test_large_affected_batched` - 10K+ users batched
  - `test_late_discovery_logged` - post-72h violation logged
  - `test_incomplete_assessment_blocked` - premature report fails
  - `test_concurrent_assessment_merged` - conflict resolved
- **E2E Tests:** Part of DEV-379
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 95%+ for breach code

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Breach lifecycle management
- [ ] 72h deadline enforcement
- [ ] Authority notification
- [ ] 95%+ test coverage achieved

---

### DEV-376: Processing Register

**Reference:** [GDPR e Gestione Dati Clienti](./PRATIKO_2.0_REFERENCE.md#11-gdpr-e-gestione-dati-clienti)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
GDPR requires register of processing activities. Need to track what data is processed and why.

**Solution:**
Create processing register model and service.

**Agent Assignment:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model), DEV-307 (Migration infrastructure)
- **Unlocks:** DEV-378 (GDPR Dashboard), DEV-379 (GDPR E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid purpose: HTTP 422, `"Finalità trattamento non valida"`
- Missing legal basis: HTTP 422, `"Base giuridica richiesta"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Register entry creation: <100ms
- Register listing: <200ms (paginated)

**Edge Cases:**
- **Multiple Legal Bases:** Activity has >1 basis → store array, validate each
- **Purpose Change:** Activity purpose changes → create new entry, archive old
- **Retention Period Update:** Retention changed → update entry, log change with reason
- **Missing Categories:** Data categories empty → HTTP 422, require at least one
- **Cross-Border Transfer:** Data leaves EU → additional fields required (adequacy decision)
- **Sub-Processor Added:** New processor involved → update entry, track chain
- **Activity Terminated:** Processing stops → archive entry, preserve for audit (6 years)

**File:** `app/models/processing_register.py`

**Fields:**
- `id`: UUID (primary key)
- `studio_id`: UUID (FK to Studio)
- `activity_name`: str (name of processing activity)
- `purpose`: text (purpose of processing)
- `legal_basis`: ARRAY[enum] (CONSENT, CONTRACT, LEGAL_OBLIGATION, VITAL_INTEREST, PUBLIC_TASK, LEGITIMATE_INTEREST)
- `data_categories`: ARRAY[str] (categories of personal data processed)
- `data_subjects`: ARRAY[str] (categories of data subjects)
- `recipients`: ARRAY[str] (recipients of the data)
- `retention_period`: str (how long data is retained)
- `cross_border_transfers`: JSONB (nullable, details of EU exit transfers)
- `security_measures`: text (description of security measures)
- `created_at`: datetime
- `updated_at`: datetime
- `archived_at`: datetime (nullable)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_processing_register.py` FIRST
- **Unit Tests:**
  - `test_register_entry` - entry creation
  - `test_register_purpose` - purpose tracking
  - `test_register_legal_basis` - legal basis
  - `test_register_data_categories` - data categories
- **Edge Case Tests:**
  - `test_multiple_legal_bases_array` - >1 basis stored
  - `test_purpose_change_archives` - old entry preserved
  - `test_retention_update_logged` - change recorded
  - `test_empty_categories_rejected` - validation enforced
  - `test_cross_border_extra_fields` - EU exit requires adequacy
  - `test_sub_processor_chain` - processor chain tracked
  - `test_terminated_preserved` - 6-year retention
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/`
- **Coverage Target:** 90%+ for register code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Processing activities logged
- [ ] Legal basis tracking
- [ ] Data categories
- [ ] 90%+ test coverage achieved

---

### DEV-377: Enhanced Client Data Rights

**Reference:** [GDPR e Gestione Dati Clienti](./PRATIKO_2.0_REFERENCE.md#11-gdpr-e-gestione-dati-clienti)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
GDPR gives data subjects rights: access, rectification, erasure, portability. Need client-facing API.

**Solution:**
Create data rights API for client self-service.

**Agent Assignment:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-309 (ClientService), existing GDPR deletion service
- **Unlocks:** DEV-378 (GDPR Dashboard), DEV-379 (GDPR E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Client not found: HTTP 404, `"Cliente non trovato"`
- Access denied: HTTP 403, `"Accesso non autorizzato ai dati"`
- Export generation failure: HTTP 500, log and retry
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Access request: <500ms (may aggregate multiple tables)
- Export generation: <5s (includes file creation)
- Erasure: <2s (soft delete with cascade)

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Incomplete erasure | CRITICAL | Cascade delete + audit verification |
| Export missing data | HIGH | Schema-driven export with completeness check |

**Edge Cases:**
- **Erasure with Active Contract:** Client has ongoing services → block erasure, show reason
- **Partial Rectification:** Some fields updated, others unchanged → partial update OK
- **Export Large Dataset:** 50MB+ export → stream response, not memory-bound
- **Multiple Export Formats:** Request JSON + CSV → support both, return zip
- **Erasure Undo Window:** Accidental erasure → 24h soft-delete window before hard delete
- **Access Request Rate Limit:** Prevent abuse → max 1 access request per hour
- **Portability to Competitor:** Export for migration → machine-readable format (JSON)
- **Rectification Audit:** Every change logged → before/after values stored

**File:** `app/api/v1/data_rights.py`

**Endpoints:**
- `GET /api/v1/data-rights/access` - Right to access
- `POST /api/v1/data-rights/rectification` - Right to rectification
- `POST /api/v1/data-rights/erasure` - Right to erasure
- `GET /api/v1/data-rights/export` - Right to portability

**Testing Requirements:**
- **TDD:** Write `tests/api/test_data_rights_api.py` FIRST
- **Integration Tests:**
  - `test_access_right_200` - returns data
  - `test_rectification_200` - updates data
  - `test_erasure_200` - deletes data
  - `test_export_200` - exports data
  - `test_audit_logged` - all actions logged
- **Edge Case Tests:**
  - `test_erasure_blocked_active_contract` - ongoing services prevent delete
  - `test_partial_rectification_ok` - some fields update
  - `test_large_export_streamed` - 50MB+ doesn't OOM
  - `test_multi_format_export_zip` - JSON+CSV in zip
  - `test_erasure_undo_window` - 24h soft-delete
  - `test_access_rate_limited` - >1/hour blocked
  - `test_portability_json` - machine-readable export
  - `test_rectification_audit_before_after` - changes logged
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/` and `pytest tests/gdpr/`
- **Coverage Target:** 95%+ for data rights code

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All GDPR rights implemented
- [ ] Actions audit logged
- [ ] 95%+ test coverage achieved

---

### DEV-378: GDPR Compliance Dashboard

**Reference:** [GDPR e Gestione Dati Clienti](./PRATIKO_2.0_REFERENCE.md#11-gdpr-e-gestione-dati-clienti)

**Figma Reference:** `GDPRCompliancePage.tsx` — Source: [`docs/figma-make-references/GDPRCompliancePage.tsx`](../figma-make-references/GDPRCompliancePage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Studios need visibility into GDPR compliance status: DPA status, pending requests, breaches.

**Solution:**
Create compliance dashboard endpoint.

**Agent Assignment:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-372 (DPA), DEV-373 (DPA Workflow), DEV-374-275 (Breach), DEV-376 (Register), DEV-377 (Data Rights)
- **Unlocks:** DEV-379 (GDPR E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Dashboard aggregation failure: Return partial data with `"incomplete": true` flag
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Dashboard load: <500ms (aggregate queries)
- Cache compliance metrics: 5 minute TTL

**Edge Cases:**
- **No DPA Yet:** Studio hasn't accepted DPA → show banner, status = INCOMPLETE
- **Breach In Progress:** Active breach within 72h → highlight with urgency indicator
- **All Compliant:** Every check passes → green status, celebratory indicator
- **Partial Compliance:** Some checks pass, others fail → show per-check status
- **Service Degraded:** Some metrics unavailable → show available, flag degraded
- **Historic View:** Request past compliance status → query audit trail
- **Export Compliance Report:** Generate PDF → scheduled job, not realtime

**File:** `app/api/v1/compliance.py`

**Endpoints:**
- `GET /api/v1/compliance/status` - Overall compliance status
- `GET /api/v1/compliance/requests` - Pending data requests

**Testing Requirements:**
- **TDD:** Write `tests/api/test_compliance_api.py` FIRST
- **Integration Tests:**
  - `test_compliance_status_200` - returns status
  - `test_compliance_dpa_status` - DPA included
  - `test_compliance_pending_requests` - requests listed
- **Edge Case Tests:**
  - `test_no_dpa_incomplete` - missing DPA shows banner
  - `test_breach_in_progress_urgent` - active breach highlighted
  - `test_all_compliant_green` - full compliance shown
  - `test_partial_compliance_per_check` - individual status
  - `test_service_degraded_flagged` - unavailable metrics noted
  - `test_historic_compliance_audit` - past status queryable
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 80%+ for compliance code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Compliance overview
- [ ] DPA status
- [ ] Pending requests
- [ ] 80%+ test coverage achieved

---

### DEV-379: GDPR E2E Tests

**Reference:** [GDPR e Gestione Dati Clienti](./PRATIKO_2.0_REFERENCE.md#11-gdpr-e-gestione-dati-clienti)

**Priority:** CRITICAL | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
GDPR compliance must be verified end-to-end. Critical for legal compliance.

**Solution:**
Create comprehensive GDPR E2E test suite.

**Agent Assignment:** @Clelia (primary), @Severino (review)

**Dependencies:**
- **Blocking:** DEV-372-278 (All Phase 9 GDPR tasks)
- **Unlocks:** Production deployment gate (GDPR compliance required)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Full GDPR E2E suite: <120s execution
- Individual test: <15s

**Edge Cases:**
- **Nulls/Empty:** Handle null or empty input values gracefully
- **Validation:** Validate input formats before processing
- **Error Recovery:** Handle partial failures with clear error messages
- **Boundaries:** Test boundary conditions (limits, max values)
- **Concurrency:** Consider concurrent access scenarios

**File:** `tests/e2e/test_gdpr_compliance.py`

**Error Handling:**
- GDPR workflow failures: Descriptive error messages with compliance context
- DPA enforcement failures: Clear logging of blocked operations
- Breach notification failures: Log deadline status and notification attempts
- **Logging:** All test failures logged with GDPR compliance context

**Performance Requirements:**
- Individual GDPR test: <10s
- Full GDPR E2E suite: <120s
- Data rights operations: <5s per operation

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **E2E Tests:**
  - `test_dpa_acceptance_flow` - full DPA workflow
  - `test_client_blocked_without_dpa` - enforcement
  - `test_data_access_request_flow` - access right E2E
  - `test_data_erasure_flow` - erasure E2E
  - `test_data_export_flow` - portability E2E
  - `test_breach_notification_flow` - breach workflow
  - `test_72h_deadline_enforcement` - deadline checked
- **Coverage Target:** 95%+ for all GDPR code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] DPA workflow verified
- [ ] All data rights tested E2E
- [ ] Breach notification tested
- [ ] 72h deadline enforced
- [ ] 95%+ coverage achieved

---

## Phase 10: Proactive Deadline System (Week 16-17) - 8 Tasks

**Reference:** [FR-006: Sistema Scadenze Proattivo](./PRATIKO_2.0_REFERENCE.md#fr-006-sistema-scadenze-proattivo)

This phase implements FR-006 - the proactive deadline system that tracks tax deadlines, regulatory deadlines, and client-specific obligations. The system automatically matches deadlines to clients based on their profile and sends proactive notifications.

### DEV-380: Deadline SQLModel & Migration

**Reference:** [FR-006: Sistema Scadenze Proattivo](./PRATIKO_2.0_REFERENCE.md#fr-006-sistema-scadenze-proattivo)

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

> **Figma Gap Note (2026-02-25):** Figma's ScadenzeFiscaliPage.tsx shows each deadline with "Importo: €X" and "Sanzioni: percentuale + importo" fields not included in the original field list below. DEV-437 adds these fields as an extension to this model.

**Problem:**
The system needs to track deadlines from multiple sources (regulatory, tax, client-specific) and match them to relevant clients.

**Solution:**
Create `Deadline` SQLModel to store deadline metadata and `ClientDeadline` for the many-to-many relationship with clients.

**Agent Assignment:** @Primo (primary), @Severino (security review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model), DEV-301 (Client model), DEV-307 (Migration infrastructure)
- **Unlocks:** DEV-381 (DeadlineService), DEV-382 (Extraction), DEV-383 (Matching), DEV-384 (Notifications), DEV-385 (API)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid deadline_type: HTTP 422, `"Tipo scadenza non valido"`
- Invalid recurrence: HTTP 422, `"Ricorrenza non valida"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Deadline model creation: <50ms
- ClientDeadline bulk insert: 100 records in <500ms

**Edge Cases:**
- **Date Validation:** deadline_date in past → rejected with HTTP 422 (unless source=MANUAL and override flag)
- **Today's Date:** deadline_date=today → valid, included in "upcoming" with days_until=0
- **Null Optional Fields:** null source_reference, null applicability_criteria → allowed
- **Invalid Recurrence:** recurrence=ONCE with next_occurrence → next_occurrence ignored
- **Duplicate ClientDeadline:** same client+deadline combo → upsert, not duplicate
- **Enum Validation:** Invalid deadline_type or source → HTTP 422 with valid options
- **JSONB Size:** applicability_criteria > 10KB → HTTP 422, `"Criteri troppo complessi"`
- **Cascade Delete:** Deadline deleted → all ClientDeadline records soft-deleted

**File:** `app/models/deadline.py`

**Deadline Fields:**
- `id`: UUID (primary key)
- `title`: str (deadline name)
- `description`: text
- `deadline_type`: enum (FISCALE, CONTRIBUTIVO, DICHIARATIVO, CONTRATTUALE, ALTRO)
- `deadline_date`: date (when due)
- `source`: enum (AGENZIA_ENTRATE, INPS, INAIL, MEF, KB_EXTRACTED, MANUAL)
- `source_reference`: str (nullable, link to KB item or regulation)
- `applicability_criteria`: JSONB (who this deadline applies to)
- `recurrence`: enum (ONCE, MONTHLY, QUARTERLY, ANNUAL)
- `notification_days_before`: int[] (default: [30, 7, 1])
- `is_active`: bool (default: true)
- `created_at`, `updated_at`

**ClientDeadline Fields:**
- `id`: UUID (primary key)
- `client_id`: UUID (FK to Client)
- `deadline_id`: UUID (FK to Deadline)
- `studio_id`: UUID (FK to Studio, for isolation)
- `status`: enum (PENDING, NOTIFIED, COMPLETED, OVERDUE)
- `completed_at`: datetime (nullable)
- `notes`: text (nullable)
- `notification_sent_at`: datetime[] (track each notification)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_deadline.py` FIRST
- **Unit Tests:**
  - `test_deadline_creation_valid` - valid deadline creation
  - `test_deadline_type_enum` - all enum values
  - `test_deadline_recurrence` - recurrence handling
  - `test_client_deadline_studio_isolation` - tenant isolation
  - `test_client_deadline_status_transitions` - status flow
- **Edge Case Tests:**
  - `test_deadline_date_past_rejected` - past dates blocked
  - `test_deadline_date_today_valid` - today allowed
  - `test_null_optional_fields_allowed` - nulls accepted
  - `test_recurrence_once_ignores_next` - next_occurrence ignored for ONCE
  - `test_client_deadline_upsert` - no duplicates
  - `test_invalid_enum_422` - bad enum rejected
  - `test_jsonb_size_limit` - large JSONB rejected
  - `test_cascade_soft_delete` - cascade works
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/models/`
- **Coverage Target:** 80%+ for new model code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Deadline SQLModel created
- [ ] ClientDeadline SQLModel created
- [ ] Alembic migration created and tested
- [ ] studio_id isolation enforced
- [ ] 80%+ test coverage achieved

---

### DEV-381: DeadlineService CRUD

**Reference:** [FR-006: Sistema Scadenze Proattivo](./PRATIKO_2.0_REFERENCE.md#fr-006-sistema-scadenze-proattivo)

**Priority:** CRITICAL | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Need CRUD operations for deadlines with studio_id isolation and deadline status management.

**Solution:**
Create DeadlineService with full CRUD and status management.

**Agent Assignment:** @Ezio (primary), @Primo (DB support), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-380 (Deadline model)
- **Unlocks:** DEV-382 (Extraction), DEV-383 (Matching), DEV-384 (Notifications), DEV-385 (API), DEV-387 (E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Deadline not found: HTTP 404, `"Scadenza non trovata"`
- Unauthorized studio: HTTP 403, `"Accesso non autorizzato alla scadenza"`
- Invalid status transition: HTTP 400, `"Transizione stato non valida"`
- Client not in studio: HTTP 403, `"Cliente non appartenente allo studio"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- CRUD operations: <100ms
- List upcoming (30 days): <200ms (paginated)
- List overdue: <150ms

**Edge Cases:**
- **Date in Past:** create_deadline with date in past → HTTP 422 (unless override flag)
- **Today Boundary:** deadline_date=today → included in "upcoming" with days_until=0
- **Overdue Lifetime:** Overdue deadline never auto-deleted, requires explicit mark_completed or soft delete
- **Status Transitions:** PENDING→COMPLETED valid; COMPLETED→PENDING invalid → HTTP 400
- **Assign Deleted Client:** Cannot assign deadline to soft-deleted client → HTTP 404
- **Duplicate Assignment:** Same client-deadline assignment → upsert, not duplicate
- **Empty Filters:** null filters in list_deadlines → returns all (within studio)
- **Timezone Handling:** All dates stored in UTC, converted to user timezone in API response

**File:** `app/services/deadline_service.py`

**Methods:**
- `create_deadline(deadline_data)` - Create new deadline
- `get_deadline(deadline_id, studio_id)` - Get with isolation
- `list_deadlines(studio_id, filters)` - List with filters
- `update_deadline(deadline_id, data, studio_id)` - Update
- `delete_deadline(deadline_id, studio_id)` - Soft delete
- `assign_to_client(deadline_id, client_id, studio_id)` - Create ClientDeadline
- `mark_completed(client_deadline_id, studio_id)` - Mark as done
- `get_upcoming(studio_id, days=30)` - Get upcoming deadlines
- `get_overdue(studio_id)` - Get overdue deadlines

**Testing Requirements:**
- **TDD:** Write `tests/services/test_deadline_service.py` FIRST
- **Unit Tests:**
  - `test_create_deadline` - creation
  - `test_list_deadlines_filtered` - filtering
  - `test_deadline_studio_isolation` - isolation enforced
  - `test_assign_deadline_to_client` - assignment
  - `test_mark_completed` - status transition
  - `test_get_upcoming_deadlines` - upcoming query
  - `test_get_overdue_deadlines` - overdue query
- **Edge Case Tests:**
  - `test_create_deadline_past_date_rejected` - past dates blocked
  - `test_deadline_today_days_until_zero` - today boundary correct
  - `test_overdue_persists_indefinitely` - overdue not auto-deleted
  - `test_completed_to_pending_invalid` - status reversal blocked
  - `test_assign_deleted_client_404` - deleted client rejected
  - `test_duplicate_assignment_upsert` - no duplicates
  - `test_null_filters_returns_all` - empty filters work
  - `test_dates_in_utc` - timezone handling correct
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for service code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Full CRUD operations
- [ ] studio_id isolation on all operations
- [ ] Status management (PENDING→COMPLETED, PENDING→OVERDUE)
- [ ] Filtering by type, date range, status
- [ ] 80%+ test coverage achieved

---

### DEV-382: Automatic Deadline Extraction from KB

**Reference:** [FR-006: Sistema Scadenze Proattivo](./PRATIKO_2.0_REFERENCE.md#fr-006-sistema-scadenze-proattivo)

**Priority:** HIGH | **Effort:** 6h | **Status:** NOT STARTED

**Problem:**
When new regulations are ingested via RSS, the system should automatically extract deadline information and create Deadline records.

**Solution:**
Create DeadlineExtractionService that processes KB items and extracts deadline metadata using LLM + regex patterns.

**Agent Assignment:** @Ezio (primary), @Mario (extraction rules), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-381 (DeadlineService), existing KB/RSS ingestion system
- **Unlocks:** DEV-383 (Client matching for extracted deadlines), DEV-387 (E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- No dates found: Log warning, skip item
- Invalid date format: Log warning, attempt alternative parsing
- LLM extraction failure: Retry 2x, then log for manual review
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Single KB item extraction: <2s (includes LLM call if needed)
- Batch extraction: 100 items in <3 minutes

**Edge Cases:**
- **No Dates Found:** Document with no dates → return empty, log info
- **Past Dates:** Extracted date is in past → skip unless within 7 days
- **Relative Dates:** "entro 30 giorni" without reference → flag for human review
- **Multiple Deadlines:** Single document with 5 deadlines → create 5 separate records
- **Duplicate Extraction:** Same KB item processed twice → idempotent, update existing
- **LLM Timeout:** OpenAI timeout → retry 2x, then queue for later
- **Ambiguous Dates:** "15 gennaio" without year → assume next occurrence
- **Batch Crash Recovery:** Batch fails at item 50/100 → resume from item 51

**File:** `app/services/deadline_extraction_service.py`

**Methods:**
- `extract_from_kb_item(knowledge_item_id)` - Extract from single item
- `batch_extract(source, since_date)` - Batch process new items
- `_parse_date_mentions(text)` - Regex for Italian date formats
- `_determine_applicability(text)` - Extract who it applies to
- `_classify_deadline_type(text)` - Classify as FISCALE, etc.

**Extraction Patterns:**
- "entro il [date]" → deadline_date
- "scadenza [date]" → deadline_date
- "termine ultimo [date]" → deadline_date
- "soggetti interessati: [criteria]" → applicability_criteria

**Testing Requirements:**
- **TDD:** Write `tests/services/test_deadline_extraction_service.py` FIRST
- **Unit Tests:**
  - `test_extract_single_date` - single date extraction
  - `test_extract_multiple_dates` - multiple deadlines in one doc
  - `test_italian_date_formats` - "15 gennaio 2025", "15/01/2025"
  - `test_determine_applicability` - criteria extraction
  - `test_classify_deadline_type` - type classification
- **Integration Tests:** Test with real KB items
- **Edge Case Tests:**
  - `test_extract_no_dates_empty` - no dates returns empty
  - `test_extract_past_dates_skipped` - past dates filtered
  - `test_extract_relative_dates_flagged` - relative dates need review
  - `test_extract_multiple_deadlines` - multiple deadlines created
  - `test_extract_duplicate_idempotent` - re-extraction updates
  - `test_extract_llm_timeout_retry` - timeout retried
  - `test_extract_ambiguous_year_assumed` - next occurrence assumed
  - `test_batch_crash_recovery` - resume from checkpoint
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for extraction code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives | MEDIUM | Human review flag for auto-extracted |
| Date parsing errors | MEDIUM | Multiple format support |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Extract deadlines from KB item text
- [ ] Support Italian date formats
- [ ] Classify deadline types
- [ ] Flag auto-extracted for review
- [ ] 80%+ test coverage achieved

---

### DEV-383: Client-Deadline Matching Logic

**Reference:** [FR-006: Sistema Scadenze Proattivo](./PRATIKO_2.0_REFERENCE.md#fr-006-sistema-scadenze-proattivo)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
When a new deadline is created, the system needs to identify which clients it applies to based on their profile (regime fiscale, ATECO, tipo cliente, etc.).

**Solution:**
Create DeadlineMatchingService that matches deadlines to clients using the same criteria engine as normative matching.

**Agent Assignment:** @Ezio (primary), @Primo (query optimization), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-381 (DeadlineService), DEV-302 (ClientProfile), DEV-320 (NormativeMatchingService criteria engine)
- **Unlocks:** DEV-384 (Notifications use matched clients), DEV-387 (E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- No matching clients: Log info, deadline remains without ClientDeadline records
- Criteria evaluation error: Log error, skip client, continue with others
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Match single deadline to 100 clients: <100ms
- Bulk match new client to all active deadlines: <500ms

**Edge Cases:**
- **No Matching Clients:** Deadline with narrow criteria → 0 matches, deadline still valid
- **All Clients Match:** Deadline with no criteria → matches all active clients
- **Client Profile Null:** Client with null ATECO/regime → evaluates to no match
- **Criteria JSONB Empty:** Empty `{}` criteria → matches all clients
- **Inactive Clients:** Soft-deleted clients excluded from matching
- **Duplicate Match:** Same client-deadline match attempted twice → upsert
- **Stale Profile:** Client profile updated after match → re-match on profile update
- **Criteria Syntax Error:** Invalid JSONB criteria → log error, skip deadline

**File:** `app/services/deadline_matching_service.py`

**Methods:**
- `match_deadline_to_clients(deadline_id)` - Match single deadline
- `match_client_to_deadlines(client_id)` - Match client to all active
- `_evaluate_criteria(client_profile, criteria)` - Evaluate JSONB criteria
- `create_client_deadlines(matches)` - Bulk create ClientDeadline

**Testing Requirements:**
- **TDD:** Write `tests/services/test_deadline_matching_service.py` FIRST
- **Unit Tests:**
  - `test_match_forfettario_deadline` - regime fiscale match
  - `test_match_ateco_deadline` - ATECO code match
  - `test_match_employer_deadline` - n_dipendenti > 0
  - `test_no_match_when_criteria_fail` - negative case
  - `test_bulk_create_client_deadlines` - bulk creation
- **Integration Tests:** Test with sample clients and deadlines
- **Edge Case Tests:**
  - `test_match_no_clients_empty` - narrow criteria 0 matches
  - `test_match_all_clients_empty_criteria` - empty matches all
  - `test_match_null_profile_no_match` - null fields no match
  - `test_match_inactive_excluded` - deleted excluded
  - `test_match_duplicate_upsert` - no duplicates
  - `test_match_stale_profile_rematch` - profile update triggers
  - `test_match_criteria_syntax_error_skipped` - invalid skipped
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/services/`
- **Coverage Target:** 80%+ for matching code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Match deadlines to clients by criteria
- [ ] Bulk assign ClientDeadline records
- [ ] Reuse normative matching criteria engine
- [ ] Performance: <100ms for 100 clients
- [ ] 80%+ test coverage achieved

---

### DEV-384: Deadline Notification Background Job

**Reference:** [FR-006: Sistema Scadenze Proattivo](./PRATIKO_2.0_REFERENCE.md#fr-006-sistema-scadenze-proattivo)

**Figma Reference:** `NotificationsDropdown.tsx` (dropdown in ChatPage) — Source: [`docs/figma-make-references/NotificationsDropdown.tsx`](../figma-make-references/NotificationsDropdown.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Users need to be notified of upcoming deadlines. Notifications should be sent at configurable intervals (e.g., 30 days, 7 days, 1 day before).

**Solution:**
Create background job that runs daily and sends notifications for upcoming deadlines.

**Agent Assignment:** @Ezio (primary), @Silvano (background jobs), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-381 (DeadlineService), DEV-383 (Client-Deadline Matching), DEV-333 (Email sending)
- **Unlocks:** DEV-387 (E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Notification send failure: Retry 3x, log for manual follow-up
- Job crash: APScheduler auto-restart, alert via monitoring
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Daily job execution: <5 minutes for 10K ClientDeadline records
- Individual notification: <100ms

**Edge Cases:**
- **Already Notified:** Deadline at 7 days with 7-day notification sent → skip (idempotent)
- **Notification Disabled:** User has email notifications off → in-app only
- **Client Deleted:** Deadline for deleted client → skip notification
- **Deadline Completed:** Notification for completed deadline → skip
- **Multiple Intervals:** Deadline at exactly 7 days → send 7-day notification, skip 30-day
- **Job Overlap:** Previous job still running → skip this run, log warning
- **Timezone Edge:** Deadline due at midnight → use studio timezone for calculation
- **Overdue Transition:** Deadline becomes overdue mid-job → update status, notify

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Duplicate notifications | LOW | Track notification_sent_at per interval |
| Job failure | MEDIUM | APScheduler retry + alerting |

**File:** `app/jobs/deadline_notification_job.py`

**Methods:**
- `run()` - Main job entry point (daily)
- `_get_deadlines_to_notify(days_before)` - Query upcoming
- `_send_notification(client_deadline)` - Send via preferred channel
- `_mark_notified(client_deadline_id)` - Update notification_sent_at
- `_check_overdue()` - Mark overdue deadlines

**Notification Channels:**
- In-app notification (always)
- Email (if enabled)
- ProactiveSuggestion (for chat display)

**Testing Requirements:**
- **TDD:** Write `tests/jobs/test_deadline_notification_job.py` FIRST
- **Unit Tests:**
  - `test_job_runs_daily` - scheduler config
  - `test_notify_30_days_before` - 30-day notification
  - `test_notify_7_days_before` - 7-day notification
  - `test_notify_1_day_before` - 1-day notification
  - `test_mark_overdue` - overdue status update
  - `test_no_duplicate_notifications` - idempotency
- **Integration Tests:** Test full notification flow
- **Edge Case Tests:**
  - `test_already_notified_skipped` - duplicate prevention
  - `test_notification_disabled_in_app_only` - email off
  - `test_deleted_client_skipped` - deleted excluded
  - `test_completed_deadline_skipped` - completed excluded
  - `test_multiple_intervals_single_send` - no double notification
  - `test_job_overlap_skipped` - concurrent protection
  - `test_timezone_midnight_boundary` - timezone correct
  - `test_overdue_transition_notified` - overdue state updated
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/jobs/`
- **Coverage Target:** 80%+ for job code

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Daily job schedule
- [ ] Configurable notification intervals
- [ ] Multiple notification channels
- [ ] Idempotent (no duplicate notifications)
- [ ] 80%+ test coverage achieved

---

### DEV-385: Upcoming Deadlines API Endpoint

**Reference:** [FR-006: Sistema Scadenze Proattivo](./PRATIKO_2.0_REFERENCE.md#fr-006-sistema-scadenze-proattivo)

**Figma Reference:** `NotificationsDropdown.tsx` (dropdown in ChatPage) — Source: [`docs/figma-make-references/NotificationsDropdown.tsx`](../figma-make-references/NotificationsDropdown.tsx) + `ScadenzeFiscaliPage.tsx` — Source: [`docs/figma-make-references/ScadenzeFiscaliPage.tsx`](../figma-make-references/ScadenzeFiscaliPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Frontend needs API to fetch upcoming deadlines for display in dashboard and calendar widget.

**Solution:**
Create REST endpoints for deadline management and queries.

> **Navigation:** When implementing the frontend, add "Scadenze Fiscali" menu item (Calendar icon, route `/scadenze`) to the user menu dropdown in `web/src/app/chat/components/ChatHeader.tsx`. Insert in the feature links section above "Il mio Account". Target menu layout:
> ```
> ┌──────────────────────┐
> │  Clienti             │  (DEV-308)
> │  Comunicazioni       │  (DEV-330)
> │  Procedure           │  (DEV-340)
> │  Dashboard           │  (DEV-354)
> │  Scadenze Fiscali    │  (DEV-385)
> │ ──────────────────── │
> │  Il mio Account      │
> │  [superuser items]   │
> │ ──────────────────── │
> │  Esci                │
> └──────────────────────┘
> ```

**Agent Assignment:** @Ezio (primary), @Livia (frontend contract), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-381 (DeadlineService)
- **Unlocks:** DEV-386 (Calendar Widget), DEV-387 (E2E Tests)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Deadline not found: HTTP 404, `"Scadenza non trovata"`
- Unauthorized studio: HTTP 403, `"Accesso non autorizzato"`
- Invalid date range: HTTP 400, `"Range date non valido"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- List upcoming: <100ms (paginated, default 20)
- List overdue: <100ms
- Single deadline: <50ms

**Edge Cases:**
- **days_until Negative:** Overdue deadlines have negative days_until (e.g., -3 for 3 days overdue)
- **days_until Zero:** deadline_date=today → days_until=0, included in upcoming
- **Date Range Invalid:** from_date > to_date → HTTP 400 with clear message
- **Overdue Sorting:** Overdue list sorted by most overdue first (most negative days_until)
- **Upcoming Sorting:** Upcoming list sorted by soonest first (lowest positive days_until)
- **Pagination Beyond Results:** page=10 when only 2 pages → empty items, total correct
- **Complete Already Completed:** Mark completed on COMPLETED deadline → HTTP 200 (idempotent)
- **Delete Completed:** Can delete completed deadlines (soft delete)

**File:** `app/api/v2/endpoints/deadlines.py`

**Endpoints:**
- `GET /v2/deadlines` - List deadlines (filtered)
- `GET /v2/deadlines/upcoming` - Upcoming deadlines
- `GET /v2/deadlines/overdue` - Overdue deadlines
- `GET /v2/deadlines/{id}` - Single deadline
- `POST /v2/deadlines` - Create deadline (manual)
- `PUT /v2/deadlines/{id}` - Update deadline
- `DELETE /v2/deadlines/{id}` - Delete deadline
- `POST /v2/deadlines/{id}/complete` - Mark as completed
- `GET /v2/clients/{id}/deadlines` - Client's deadlines

**Response Schema:**
```python
class DeadlineResponse(BaseModel):
    id: UUID
    title: str
    deadline_date: date
    deadline_type: DeadlineType
    status: DeadlineStatus
    days_until: int  # computed
    client_count: int  # how many clients affected
```

**Testing Requirements:**
- **TDD:** Write `tests/api/v2/test_deadlines_api.py` FIRST
- **Unit Tests:**
  - `test_list_deadlines_authenticated` - auth required
  - `test_list_deadlines_studio_isolated` - isolation
  - `test_get_upcoming_sorted` - sorted by date
  - `test_create_deadline_validation` - input validation
  - `test_mark_completed` - status transition
- **E2E Tests:** Full deadline workflow
- **Edge Case Tests:**
  - `test_days_until_negative_overdue` - overdue has negative days
  - `test_days_until_zero_today` - today boundary correct
  - `test_date_range_invalid_400` - from>to rejected
  - `test_overdue_sorted_most_overdue_first` - correct sort order
  - `test_upcoming_sorted_soonest_first` - correct sort order
  - `test_pagination_beyond_results_empty` - empty not error
  - `test_complete_idempotent` - re-complete returns 200
  - `test_delete_completed_allowed` - soft delete works
- **Edge Case Tests:** See Edge Cases section above
- **Regression Tests:** Run `pytest tests/api/`
- **Coverage Target:** 80%+ for endpoint code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Full CRUD endpoints
- [ ] Upcoming/overdue specialized queries
- [ ] studio_id isolation on all endpoints
- [ ] OpenAPI schema documented
- [ ] 80%+ test coverage achieved

---

### DEV-386: Deadline Calendar Widget (Frontend)

**Reference:** [FR-006: Sistema Scadenze Proattivo](./PRATIKO_2.0_REFERENCE.md#fr-006-sistema-scadenze-proattivo)

**Figma Reference:** `ScadenzeFiscaliPage.tsx` — Source: [`docs/figma-make-references/ScadenzeFiscaliPage.tsx`](../figma-make-references/ScadenzeFiscaliPage.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Users need a visual calendar view of upcoming deadlines in the dashboard.

**Solution:**
Create React calendar component showing deadlines with color-coding by type and status.

**Agent Assignment:** @Livia (primary), @Ezio (API contract), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-385 (Deadlines API), DEV-370 (Frontend SDK Types)
- **Unlocks:** DEV-387 (E2E Tests - frontend integration)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- API fetch failure: Show error toast, `"Impossibile caricare le scadenze"`
- Empty calendar: Show placeholder, `"Nessuna scadenza in questo mese"`
- Mark complete failure: Show error toast, `"Impossibile completare la scadenza"`
- WebSocket disconnect: Fallback to polling every 30s
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Calendar render: <200ms
- Month navigation: <100ms
- Real-time updates via DEV-369 WebSocket

**Edge Cases:**
- **Empty Month:** No deadlines in selected month -> show placeholder with next deadline info
- **Past Deadlines:** Deadlines in past months -> allow navigation back, gray out past dates
- **Today Boundary:** Deadline due today -> highlight with "TODAY" badge, yellow color
- **Many Deadlines:** Day with 5+ deadlines -> show first 3 + "+N more" popover
- **Month Navigation:** Navigate to month with no deadlines -> show empty state, suggest nearest month
- **Long Title Truncation:** Deadline title > 30 chars -> truncate with "..." in calendar cell
- **Timezone Mismatch:** User in different TZ than server -> use user TZ for display
- **Rapid Click:** Double-click on deadline -> debounce, open modal only once

**File:** `src/components/deadlines/DeadlineCalendar.tsx`

**Components:**
- `DeadlineCalendar` - Main calendar container with month navigation
- `DeadlineDay` - Single day cell with deadline indicators
- `DeadlinePopover` - Click-to-view detail popover
- `DeadlineFilters` - Type/status filter controls
- `DeadlineList` - Mobile-friendly list view alternative

**Features:**
- Monthly calendar view
- Color-coded by deadline type
- Click to view deadline details
- Mark as completed action
- Filter by type, status
- Mobile responsive

**Testing Requirements:**
- **TDD:** Write component tests FIRST
- **Unit Tests:** `src/components/deadlines/__tests__/`
  - `test_renders_deadlines` - deadlines appear on calendar
  - `test_color_coding` - correct colors by type
  - `test_click_deadline` - detail modal opens
  - `test_mark_completed` - action works
  - `test_responsive_mobile` - mobile view works
- **Edge Case Tests:**
  - `test_api_failure_shows_error` - error toast displayed
  - `test_empty_month_placeholder` - empty state shown
  - `test_websocket_disconnect_fallback` - polling fallback works
  - `test_mark_complete_failure_retry` - error allows retry
- **E2E Tests:** Full calendar interaction
- **Coverage Target:** 80%+ for component code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Monthly calendar view
- [ ] Color-coded deadlines
- [ ] Click-to-view details
- [ ] Mark completed action
- [ ] Mobile responsive

---

### DEV-387: Deadline System E2E Tests

**Reference:** [FR-006: Sistema Scadenze Proattivo](./PRATIKO_2.0_REFERENCE.md#fr-006-sistema-scadenze-proattivo)

**Priority:** CRITICAL | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
The deadline system is critical for user value. Need comprehensive E2E tests covering the full workflow.

**Solution:**
Create E2E test suite for deadline system.

**Agent Assignment:** @Clelia (primary), @Severino (review)

**Dependencies:**
- **Blocking:** DEV-380-286 (All Phase 10 Deadline tasks)
- **Unlocks:** Production deployment gate (deadline system must work)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Test environment failure: Retry 3x, then skip with clear message
- Database reset failure: Log error, continue with existing data
- Assertion failure: Capture full state for debugging
- Timeout exceeded: Kill test, log timeout context
- **Logging:** All test failures MUST be logged with context (test_name, step, error) at ERROR level

**Performance Requirements:**
- Full deadline E2E suite: <120s execution
- Individual test flow: <15s

**Edge Cases:**
- **Database Reset:** Test DB reset fails -> log error, continue with existing data
- **Parallel Test Run:** Tests run in parallel -> ensure data isolation per test
- **Flaky Network:** Network timeout during API call -> retry 2x with backoff
- **Timezone Boundaries:** Deadline at midnight UTC -> verify correct date in user TZ
- **Large Data Volume:** Create 100 deadlines -> verify list performance <500ms
- **Concurrent Notification:** Two notifications same deadline -> verify no duplicate sends
- **State Cleanup:** Test failure mid-flow -> ensure cleanup hook removes test data
- **Cross-Browser:** Calendar widget tested on Chrome, Firefox, Safari

**File:** `tests/e2e/test_deadline_system.py`

**Test Classes:**
- `TestDeadlineCreationFlow` - Deadline creation and client assignment
- `TestDeadlineExtractionFlow` - KB extraction to deadline creation
- `TestDeadlineNotificationFlow` - Notification timing and delivery
- `TestDeadlineCompletionFlow` - Status transitions and completion
- `TestDeadlineOverdueFlow` - Overdue detection and marking

**Test Flows:**
1. **Deadline Creation Flow**
   - Create deadline → Assign to clients → Verify ClientDeadline records
2. **Auto-Extraction Flow**
   - Ingest KB item → Extract deadline → Verify deadline created
3. **Notification Flow**
   - Create deadline due in 7 days → Run job → Verify notification sent
4. **Completion Flow**
   - Create deadline → Mark completed → Verify status change
5. **Overdue Flow**
   - Create past deadline → Run job → Verify marked overdue

**Testing Requirements:**

**File:** `tests/e2e/test_communication_flow.py`

**Methods:**
- `test_create_draft_to_send_email_flow()` - Full email workflow
- `test_create_draft_to_send_whatsapp_flow()` - Full WhatsApp workflow
- `test_rejection_flow()` - Draft -> review -> reject -> revise
- `test_bulk_communication_flow()` - Multiple clients
- `test_self_approval_blocked()` - Security check E2E

- **This IS the testing task**
- **E2E Tests:**
  - `test_deadline_creation_assigns_clients` - full creation flow
  - `test_kb_extraction_creates_deadline` - auto-extraction
  - `test_notification_sent_before_deadline` - notification timing
  - `test_mark_completed_updates_status` - completion
  - `test_overdue_detection` - overdue marking
  - `test_deadline_studio_isolation` - multi-tenant
- **Coverage Target:** 95%+ for deadline system code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] All E2E flows passing
- [ ] Multi-tenant isolation verified
- [ ] Notification timing verified
- [ ] Auto-extraction verified
- [ ] 95%+ coverage achieved

---

## Phase 11: Infrastructure & Quality (Week 18) - 7 Tasks

This phase adds missing infrastructure components identified in the gap analysis.

### DEV-388: PDF Export Service

**Reference:** [NFR-001: Performance Requirements](./PRATIKO_2.0_REFERENCE.md#7-requisiti-non-funzionali)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Multiple features need PDF export capability (procedure, calculations, dashboard reports, communications).

**Solution:**
Create shared PDF generation service using WeasyPrint or ReportLab.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** None (independent utility service)
- **Unlocks:** Procedura export, calculation export, dashboard reports, communication archive

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- PDF generation failure: HTTP 500, `"Generazione PDF fallita"`
- Template not found: HTTP 500 (config error), alert ops
- Content too large: Split into multiple pages or summarize
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Simple PDF: <500ms
- Complex report with charts: <3s
- Max file size: 10MB

**Edge Cases:**
- **Empty Content:** No content to export → generate empty PDF with header/footer only
- **Unicode Characters:** Italian accents, special chars → ensure UTF-8 rendering
- **Very Long Content:** Content > 100 pages → split into multiple files or summarize
- **Missing Template:** Template file not found → use default template, log warning
- **Image Embedding:** Images in content → embed as base64, max 2MB per image
- **Concurrent Generation:** Many PDFs at once → queue with max 5 concurrent
- **Font Missing:** Custom font not available → fallback to system font
- **Memory Limit:** Large PDF OOM → streaming generation or limit pages

**File:** `app/services/pdf_export_service.py`

**Methods:**
- `generate_pdf(content, template, options)` - Generate PDF from content
- `export_procedura(procedura_id, progress)` - Export procedura with progress
- `export_calculation(calculation_result)` - Export tax calculation
- `export_dashboard_report(studio_id, date_range)` - Export report
- `export_communication(communication_id)` - Export for archive

**Testing Requirements:**
- **TDD:** Write `tests/services/test_pdf_export_service.py` FIRST
- **Unit Tests:**
  - `test_generate_pdf_basic` - basic generation
  - `test_export_procedura_with_progress` - procedura export
  - `test_export_calculation_formatted` - calculation export
  - `test_pdf_headers_footers` - consistent branding
- **Edge Case Tests:**
  - `test_empty_content_generates_header` - empty content handled
  - `test_unicode_italian_accents` - special chars render
  - `test_long_content_split` - multi-file for large
  - `test_missing_template_fallback` - default template used
  - `test_image_embedding_limit` - large images rejected
  - `test_concurrent_queue_limit` - queue respects max
  - `test_font_fallback` - missing font handled
- **Coverage Target:** 80%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Shared service for all PDF exports
- [ ] Italian formatting (dates, numbers)
- [ ] Consistent branding
- [ ] 80%+ test coverage achieved

---

### DEV-389: Integrate Hallucination Guard into RAG Pipeline

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
HallucinationGuard service (`app/services/hallucination_guard.py`) validates law citations but is not called in production. Created in DEV-245 Phase 2.3. Currently, responses may contain incorrect legal citations that could mislead users.

**Solution:**
Add validation step in `step_064__llm_call.py` before yielding response. If hallucinations detected:
1. Soft mode: Log warning, continue with flagged response
2. Strict mode: Request LLM regeneration without hallucinated citations

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** None (service already exists)
- **Unlocks:** Improved response accuracy for legal citations

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Modified Files:** `app/core/langgraph/nodes/step_064__llm_call.py`
- **Integration Points:** RAG pipeline response generation

**Error Handling:**
- Validation failure: Log warning, continue with original response in soft mode
- Service unavailable: Fallback to unvalidated response with warning log
- **Logging:** All hallucination detections MUST be logged with citation details

**Edge Cases:**
- **Empty citations:** Skip validation if no legal citations in response
- **Timeout:** Set 2s timeout for validation, fallback to unvalidated if exceeded
- **Partial validation:** If some citations valid and some invalid, flag only invalid ones

**File:** `app/core/langgraph/nodes/step_064__llm_call.py`

**Testing Requirements:**
- **TDD:** Write `tests/langgraph/test_hallucination_guard_integration.py` FIRST
- **Unit Tests:**
  - `test_hallucination_guard_soft_mode` - warning logged but response continues
  - `test_hallucination_guard_strict_mode` - regeneration triggered
  - `test_hallucination_guard_timeout` - fallback on timeout
  - `test_hallucination_guard_no_citations` - skip validation when no citations
- **Integration Tests:** Test with real LLM responses containing citations
- **Coverage Target:** 80%+ for integration code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Response latency increase | MEDIUM | Set strict 2s timeout |
| False positives | LOW | Start in soft mode, tune thresholds |
| Service failure | LOW | Graceful fallback to unvalidated |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] HallucinationGuard called in RAG pipeline
- [ ] Soft/strict mode configurable via environment variable
- [ ] All validations logged with structured context
- [ ] Timeout handling implemented
- [ ] 80%+ test coverage achieved

---

### DEV-390: OCR Integration for Scanned Documents

**Reference:** [FR-008: Upload e Analisi Documenti Temporanei](./PRATIKO_2.0_REFERENCE.md#fr-008-upload-e-analisi-documenti-temporanei)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Users may upload scanned documents (images, scanned PDFs) that need text extraction.

**Solution:**
Integrate OCR service (Tesseract or cloud-based) into document processing pipeline.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** None (independent utility service)
- **Unlocks:** DEV-363 (Document Context) enhancement, DEV-392 (F24 Parser) scanned support

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- OCR failure: HTTP 500, `"Estrazione testo fallita"`
- Low confidence: Return text with `"low_confidence": true` flag
- Unsupported format: HTTP 422, `"Formato immagine non supportato"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Single page OCR: <3s
- Multi-page PDF OCR: <2s per page
- Italian language model required

**Edge Cases:**
- **Empty Image:** No text detected → return empty string, `"text_found": false`
- **Rotated Image:** Auto-detect rotation (90°/180°/270°) → auto-correct before OCR
- **Mixed Languages:** Italian + English text → prioritize Italian, flag `"mixed_language": true`
- **Very Low Resolution:** <72 DPI → reject with HTTP 422, `"Risoluzione insufficiente"`
- **Corrupted File:** OCR library crash → catch exception, HTTP 500 with partial results if any
- **Confidence Threshold:** OCR confidence <60% → return text but flag `"low_confidence": true`
- **Handwritten Text:** Detected handwriting → log warning, attempt OCR with disclaimer
- **Password-Protected PDF:** Can't extract → HTTP 422, `"PDF protetto da password"`

**File:** `app/services/ocr_service.py`

**Methods:**
- `extract_text(file)` - Extract text from image/scanned PDF
- `detect_if_scanned(pdf_file)` - Check if PDF is scanned
- `preprocess_image(image)` - Improve OCR accuracy

**Testing Requirements:**
- **TDD:** Write `tests/services/test_ocr_service.py` FIRST
- **Unit Tests:**
  - `test_extract_from_image` - image OCR
  - `test_extract_from_scanned_pdf` - scanned PDF
  - `test_detect_scanned_vs_native` - detection
  - `test_italian_language_support` - Italian text
- **Edge Case Tests:**
  - `test_empty_image_returns_empty` - no text flagged
  - `test_rotated_image_corrected` - auto-rotation applied
  - `test_low_resolution_rejected` - <72 DPI fails
  - `test_corrupted_file_handled` - graceful failure
  - `test_low_confidence_flagged` - <60% confidence marked
  - `test_password_protected_rejected` - encrypted PDF fails
  - `test_handwritten_attempted` - handwriting OCR attempted
- **Coverage Target:** 80%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] OCR for images and scanned PDFs
- [ ] Italian language support
- [ ] Integration with document processor
- [ ] 80%+ test coverage achieved

---

### DEV-391: Document Auto-Delete Background Job

**Reference:** [FR-008: Upload e Analisi Documenti Temporanei](./PRATIKO_2.0_REFERENCE.md#fr-008-upload-e-analisi-documenti-temporanei)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Uploaded documents should be automatically deleted after 30 minutes for GDPR compliance.

**Solution:**
Create background job that deletes documents older than 30 minutes.

**Agent Assignment:** @Ezio (primary), @Severino (security review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-363 (Document Context) or existing document storage
- **Unlocks:** GDPR compliance (data minimization requirement)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- File deletion failure: Log error, retry next cycle
- DB record deletion failure: Log critical, alert ops (orphaned file)
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Job execution: Every 5 minutes
- Delete batch: 100 documents per cycle max
- Total job duration: <30s

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Premature deletion | HIGH | Conservative 30 min threshold + user warning |
| Orphaned files | MEDIUM | Reconciliation job weekly |

**Edge Cases:**
- **File Already Deleted:** File missing but DB record exists → delete DB record, log warning
- **DB Record Missing:** File exists but no DB record → orphan, delete file + log
- **Concurrent Deletion:** User deletes while job runs → idempotent delete (no error)
- **Timezone Mismatch:** Server TZ vs UTC → use UTC for all timestamps
- **Clock Skew:** uploaded_at in future → skip until valid, log warning
- **Batch Limit Hit:** 100+ expired → process 100, continue next cycle
- **Storage Full:** Can't delete (quota issue?) → log CRITICAL, alert ops
- **Active Upload:** File still being written → check lock status, skip if locked

**File:** `app/jobs/document_cleanup_job.py`

**Methods:**
- `run()` - Main job (runs every 5 minutes)
- `_find_expired_documents()` - Find docs older than 30 min
- `_delete_document(doc_id)` - Delete file and DB record
- `_log_deletion(doc_id)` - Audit log

**Testing Requirements:**
- **TDD:** Write `tests/jobs/test_document_cleanup_job.py` FIRST
- **Unit Tests:**
  - `test_finds_expired_documents` - correct selection
  - `test_deletes_file_and_record` - complete deletion
  - `test_respects_30_min_threshold` - timing
  - `test_audit_logging` - deletion logged
- **Edge Case Tests:**
  - `test_file_missing_db_record_cleanup` - orphan DB record handled
  - `test_orphan_file_detected` - file without DB record deleted
  - `test_concurrent_delete_idempotent` - no error on double delete
  - `test_utc_timestamps_used` - timezone handling correct
  - `test_future_timestamp_skipped` - clock skew handled
  - `test_batch_limit_100` - respects batch size
  - `test_locked_file_skipped` - active upload not deleted
- **Coverage Target:** 90%+

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Delete documents after 30 minutes
- [ ] Delete both file and DB record
- [ ] Audit logging for compliance
- [ ] 90%+ test coverage achieved

---

### DEV-392: F24 Document Parser

**Reference:** [FR-008: Upload e Analisi Documenti Temporanei](./PRATIKO_2.0_REFERENCE.md#fr-008-upload-e-analisi-documenti-temporanei)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
F24 tax payment documents have a standard structure that can be parsed to extract payment details.

**Solution:**
Create specialized parser for F24 documents.

**Agent Assignment:** @Ezio (primary), @Mario (F24 structure), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-363 (Document Context) for PDF parsing, optionally DEV-390 (OCR) for scanned F24
- **Unlocks:** Tax calculation validation, payment tracking features

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Invalid F24 format: HTTP 422, `"Formato F24 non riconosciuto"`
- Missing required fields: HTTP 422, `"Campo obbligatorio mancante: {field}"`
- Calculation mismatch: Log warning, return parsed with `"total_mismatch": true`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Parse single F24: <1s
- Extract all codes: <500ms

**Edge Cases:**
- **Empty F24:** No tributi sections filled → return empty list, `"sections_found": 0`
- **Partial F24:** Only sezione I filled → parse available, skip missing sections
- **F24 Semplificato:** Different layout → detect variant, use appropriate parser
- **Handwritten Amounts:** OCR required → combine with DEV-390, flag confidence
- **Zero Amounts:** All importi = 0 → valid F24, return parsed with totale 0
- **Compensazione:** Crediti > Debiti → `"compensazione": true`, no totale versare
- **Invalid CF:** Checksum fails → log warning, return with `"cf_valid": false`
- **Multi-Page F24:** Continuation pages → combine all pages before parsing
- **Old F24 Format:** Pre-2020 layout → fallback parser, flag `"legacy_format": true`

**File:** `app/services/document_parsers/f24_parser.py`

**Methods:**
- `parse_f24(file)` - Parse F24 document and extract all fields
- `detect_f24_variant(file)` - Detect F24 variant (standard, elide, semplificato)
- `extract_codici_tributo(content)` - Extract tributo codes and amounts
- `validate_totals(parsed)` - Verify totale calculations match
- `extract_contribuente_data(content)` - Extract codice fiscale and anagrafica

**Extracted Fields:**
- Codice fiscale contribuente
- Periodo di riferimento
- Codici tributo
- Importi a debito/credito
- Totale da versare

**Testing Requirements:**
- **TDD:** Write `tests/services/document_parsers/test_f24_parser.py` FIRST
- **Unit Tests:**
  - `test_parse_f24_standard` - standard F24
  - `test_parse_f24_elide` - F24 ELIDE variant
  - `test_extract_codici_tributo` - tributo extraction
  - `test_calculate_totals` - total calculation
- **Edge Case Tests:**
  - `test_empty_f24_sections` - no tributi returns empty
  - `test_partial_f24_sections` - missing sections skipped
  - `test_f24_semplificato_variant` - different layout parsed
  - `test_zero_amounts_valid` - all zeros is valid F24
  - `test_compensazione_detected` - credits > debits flagged
  - `test_invalid_cf_flagged` - bad checksum marked
  - `test_multi_page_combined` - continuation pages merged
  - `test_legacy_format_fallback` - pre-2020 format handled
- **Coverage Target:** 80%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Parse standard F24 format
- [ ] Extract all payment details
- [ ] Support F24 variants
- [ ] 80%+ test coverage achieved

---

### DEV-393: Regional Tax Configuration System

**Reference:** [FR-007: Calcoli Fiscali](./PRATIKO_2.0_REFERENCE.md#fr-007-calcoli-fiscali)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Tax calculations need regional variations (addizionali IRPEF) that vary by comune/regione.

**Solution:**
Create configuration system for regional tax rates.

**Agent Assignment:** @Ezio (primary), @Primo (DB), @Clelia (tests)

**Dependencies:**
- **Blocking:** None (independent configuration system)
- **Unlocks:** DEV-360 (TaxCalculatorService) enhancement for regional accuracy

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Region not found: HTTP 404, `"Regione non trovata"`
- Municipality not found: HTTP 404, `"Comune non trovato"`
- Outdated rates: Log warning, return with `"rates_may_be_outdated": true`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Rate lookup: <10ms (cached)
- Cache refresh: daily at 4 AM

**Edge Cases:**
- **New Region:** Trentino split → add new region, migration script
- **Merged Comuni:** Comune merger → redirect old code to new, log warning
- **Year Transition:** Rate change Jan 1 → use effective_date, not upload_date
- **Missing Rate:** Rate not configured → use regional default, flag `"default_rate": true`
- **Zero Rate:** Some comuni have 0% → valid, return 0 tax
- **Bracket Boundary:** Imponibile exactly at bracket limit → use lower bracket (<=)
- **Negative Imponibile:** Losses → return 0 tax, no negative calculation
- **Rate Update Conflict:** Two updates same day → use later timestamp
- **Province Lookup:** PIVA province code (first 3 digits) → map to regione

**File:** `app/services/regional_tax_service.py`

**Data:**
- Regional IRPEF rates by regione (20 regions)
- Municipal IRPEF rates by comune (configurable)
- IRPEF brackets (national, with update mechanism)

**Methods:**
- `get_regional_rate(regione)` - Get regional rate
- `get_municipal_rate(comune)` - Get municipal rate
- `calculate_regional_tax(imponibile, regione)` - Calculate regional
- `update_rates(year, rates)` - Update rates

**Testing Requirements:**
- **TDD:** Write `tests/services/test_regional_tax_service.py` FIRST
- **Unit Tests:**
  - `test_get_regional_rate_lombardia` - specific region
  - `test_calculate_regional_tax` - calculation
  - `test_update_rates` - rate update
- **Edge Case Tests:**
  - `test_merged_comune_redirects` - old code maps to new
  - `test_year_transition_effective_date` - Jan 1 rates apply correctly
  - `test_missing_rate_uses_default` - fallback flagged
  - `test_zero_rate_valid` - 0% rate returns 0 tax
  - `test_bracket_boundary_inclusive` - exact limit uses lower
  - `test_negative_imponibile_zero_tax` - losses return 0
  - `test_update_conflict_last_wins` - timestamp ordering
  - `test_piva_province_to_regione` - province mapping works
- **Coverage Target:** 80%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Implementation complexity | MEDIUM | Follow existing service patterns |
| Test coverage gaps | LOW | TDD approach with edge case tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All 20 regional rates configured
- [ ] Municipal rate lookup
- [ ] Rate update mechanism
- [ ] 80%+ test coverage achieved

---

### DEV-394: Feature Flag Infrastructure

**Reference:** [NFR-003: Deployment Requirements](./PRATIKO_2.0_REFERENCE.md#7-requisiti-non-funzionali)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Need ability to enable/disable features per studio or globally for gradual rollout.

**Solution:**
Create feature flag system with studio-level and global flags.

**Agent Assignment:** @Ezio (primary), @Silvano (deployment), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model) for per-studio flags
- **Unlocks:** Safe gradual rollout of all new features

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Flag not found: Return default (false), log warning
- Redis unavailable: Fall back to environment defaults
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Flag check: <5ms (Redis cached)
- Cache TTL: 60 seconds
- Fallback to env vars: <1ms

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Stale cache | LOW | Short TTL + manual invalidation API |
| Redis failure | MEDIUM | Environment variable fallback |

**Edge Cases:**
- **Unknown Flag:** Flag name not defined → return false (safe default), log warning
- **Studio Override Removed:** Delete per-studio flag → inherit global immediately
- **Empty Flag Name:** Blank string as flag name → HTTP 400, `"Nome flag obbligatorio"`
- **Special Characters:** Flag name with spaces/unicode → sanitize, allow only [a-z0-9_-]
- **Global vs Studio Conflict:** Studio=false, Global=true → studio wins (override)
- **Flag Audit:** Who changed what when → log all changes with user_id + timestamp
- **Percentage Rollout:** Enable for 50% studios → hash(studio_id) mod 100 < percentage
- **Cache Invalidation Race:** Update arrives during read → eventual consistency OK (60s max)
- **Flag Dependencies:** Flag A requires Flag B → validate on set, reject if dependency disabled

**File:** `app/services/feature_flag_service.py`

**Features:**
- Global flags (all studios)
- Per-studio flags (override global)
- Environment-based defaults
- Admin API for flag management

**Methods:**
- `is_enabled(flag_name, studio_id)` - Check if enabled
- `set_global_flag(flag_name, enabled)` - Set global
- `set_studio_flag(flag_name, studio_id, enabled)` - Set per-studio
- `list_flags()` - List all flags

**Testing Requirements:**
- **TDD:** Write `tests/services/test_feature_flag_service.py` FIRST
- **Unit Tests:**
  - `test_global_flag_enabled` - global flag
  - `test_studio_override` - studio overrides global
  - `test_default_from_env` - environment defaults
- **Edge Case Tests:**
  - `test_unknown_flag_returns_false` - safe default
  - `test_studio_override_removed_inherits` - deletion inherits global
  - `test_empty_flag_name_rejected` - blank name fails
  - `test_special_chars_sanitized` - invalid chars rejected
  - `test_studio_false_overrides_global_true` - override wins
  - `test_flag_changes_audited` - change log created
  - `test_percentage_rollout_consistent` - hash is stable
  - `test_redis_failure_env_fallback` - graceful degradation
- **Coverage Target:** 90%+

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Global and per-studio flags
- [ ] Environment-based defaults
- [ ] Admin API
- [ ] 90%+ test coverage achieved

---

### DEV-395: API Rate Limiting

**Reference:** [NFR-002: Security Requirements](./PRATIKO_2.0_REFERENCE.md#7-requisiti-non-funzionali)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
API needs rate limiting to prevent abuse and ensure fair usage.

**Solution:**
Implement rate limiting using Redis with configurable limits per endpoint.

**Agent Assignment:** @Ezio (primary), @Severino (security review), @Clelia (tests)

**Dependencies:**
- **Blocking:** None (independent middleware)
- **Unlocks:** Production deployment security gate

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Error Handling:**
- Invalid state transition: HTTP 400, `"Transizione di stato non valida: {from} -> {to}"`

**Error Handling:**
- Rate limit exceeded: HTTP 429, `"Troppe richieste. Riprova tra {seconds} secondi"`
- Headers: Include `Retry-After`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Rate check: <2ms (Redis INCR)
- No latency impact on normal requests
- Redis unavailable: Fail open (allow request), log critical

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Redis failure | MEDIUM | Fail open + alerting |
| Distributed attacks | HIGH | Per-IP + per-user limits |

**Edge Cases:**
- **Redis Unavailable:** Connection timeout → fail open (allow request), log CRITICAL
- **Redis Partial Failure:** INCR succeeds but TTL fails → manual cleanup job hourly
- **Distributed Attack:** Same user from multiple IPs → per-user limit still enforced
- **IP Spoofing:** X-Forwarded-For manipulation → use rightmost trusted proxy IP
- **Window Boundary:** Request at 59.9s of 1-min window → counted in current window
- **Limit Zero:** endpoint with limit=0 → effectively disabled, all requests pass
- **Negative Remaining:** Race condition shows -1 remaining → clamped to 0 in response
- **User + IP Combined:** Unauthenticated requests → IP-based limiting only

**File:** `app/middleware/rate_limit.py`

**Limits:**
- Auth endpoints: 10/minute
- Chat endpoints: 30/minute
- Search endpoints: 60/minute
- Document uploads: 10/minute
- Default: 100/minute

**Methods:**
- `rate_limit(limit, window)` - Decorator
- `check_rate_limit(user_id, endpoint)` - Check limit
- `get_remaining(user_id, endpoint)` - Get remaining calls

**Testing Requirements:**
- **TDD:** Write `tests/middleware/test_rate_limit.py` FIRST
- **Unit Tests:**
  - `test_under_limit_allowed` - normal usage
  - `test_over_limit_rejected` - 429 returned
  - `test_limit_resets` - window reset
  - `test_per_endpoint_limits` - different limits
- **Edge Case Tests:**
  - `test_redis_unavailable_fail_open` - connection timeout allows request
  - `test_redis_ttl_failure_logged` - partial failure handled
  - `test_distributed_attack_per_user` - multi-IP same user limited
  - `test_ip_spoofing_rightmost_proxy` - correct IP extraction
  - `test_window_boundary_timing` - boundary requests correct
  - `test_limit_zero_disabled` - zero limit allows all
  - `test_negative_remaining_clamped` - race condition handled
  - `test_unauthenticated_ip_only` - IP limiting for anon users
- **Coverage Target:** 90%+

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Redis-based rate limiting
- [ ] Per-endpoint configurable limits
- [ ] 429 response with Retry-After header
- [ ] 90%+ test coverage achieved

---

## Phase 12: Pre-Launch Compliance - 6 Tasks

This phase covers the **legal and operational compliance prerequisites** that must be completed before or in parallel with Phase 9's in-app GDPR software. Phase 9 builds the technical GDPR features (DPA models, breach tracking, processing registers, data rights API). This phase covers the actual vendor contracts, formal legal documents, regulatory notifications, and infrastructure security measures.

**Reference:** `docs/compliance/GDPR_INVESTIGATION_CLIENT_DATA_HETZNER.md`

---

### DEV-396: DPIA Preparation and Documentation

**Priority:** CRITICAL | **Status:** NOT STARTED

**Problem:** GDPR Article 35 and the Garante's Provvedimento of Oct 11, 2018 mandate a Data Protection Impact Assessment for PratikoAI's processing activities. PratikoAI triggers at least 3 categories of the Garante's DPIA blacklist: large-scale financial data processing, AI/scoring processing via LLMs, and cross-referencing fiscal + personal + employment data. Penalty for non-compliance: up to EUR 10,000,000 or 2% of worldwide turnover.

**Solution:** Create a formal DPIA document covering all data categories, processing purposes, risk assessment, and mitigations. Include LLM sub-processor assessment and Hetzner security analysis.

**Agent Assignment:** @Severino (primary), @Mario (requirements)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-397, DEV-398, DEV-399

**Change Classification:** ADDITIVE

**File:** `docs/compliance/DPIA_PratikoAI.md`

**Relationship to Phase 9:** Phase 9 builds the in-app software (DPA models, breach tracking, processing registers). This task produces the legal DPIA document required by law, which is NOT a software artifact.

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All sections complete with accurate legal references
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] DPIA covers all personal data categories processed by PratikoAI
- [ ] DPIA includes LLM sub-processor risk assessment (OpenAI, Anthropic)
- [ ] DPIA includes Hetzner security gap analysis and mitigations
- [ ] DPIA includes multi-tenant isolation assessment
- [ ] DPIA references existing technical measures (PII anonymizer, AES-256-GCM encryption)
- [ ] Document reviewed by legal counsel before finalization

**Code Size Guidelines:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

---

### DEV-397: Vendor DPA Execution and Encryption at Rest

**Priority:** CRITICAL | **Status:** NOT STARTED

**Problem:** Hetzner does not provide encryption at rest by default. Additionally, a formal DPA must be signed with Hetzner as sub-processor under GDPR Article 28. The existing field-level encryption (AES-256-GCM for codice_fiscale, partita_iva, importi) covers PII fields but does not protect database files, logs, or temporary files on disk. Hetzner also had a 2022 data loss incident, requiring independent backup strategy.

**Solution:** Sign DPA with Hetzner via customer portal. Implement LUKS full-disk encryption on all Hetzner VPS instances. Configure independent backup system to a geographically separate location.

**Agent Assignment:** @Silvano (primary)

**Dependencies:**
- **Blocking:** DEV-396 (DPIA should inform security requirements)
- **Unlocks:** DEV-308 (StudioService - must complete before client data storage)

**Change Classification:** ADDITIVE

**Relationship to Phase 9:** DEV-372/DEV-373 are about PratikoAI-to-studio DPAs (software). This task is about PratikoAI-to-vendor DPAs (legal contracts) and infrastructure security.

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All integrations complete and functional
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] DPA signed with Hetzner via https://accounts.hetzner.com/account/dpa
- [ ] EU-only server location confirmed (Nuremberg or Falkenstein)
- [ ] LUKS full-disk encryption implemented and verified on all VPS instances
- [ ] Independent backup system configured (separate geographic location)
- [ ] Backup restoration tested and documented

**Code Size Guidelines:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

---

### DEV-398: LLM Provider DPA and Transfer Safeguards

**Priority:** CRITICAL | **Status:** NOT STARTED

**Problem:** PratikoAI sends anonymized queries to OpenAI and Anthropic (US-based). Post-Schrems II, international data transfers to the US require proper legal safeguards including DPAs with Standard Contractual Clauses (SCCs) and a Transfer Impact Assessment (TIA). The Garante fined OpenAI EUR 15M in December 2024 for GDPR violations, making proper documentation especially important.

**Solution:** Execute DPAs with both LLM providers, enable EU Data Residency / Zero Data Retention options, and document a Transfer Impact Assessment per EDPB Recommendations 01/2020.

**Agent Assignment:** @Severino (primary), @Ezio (backend integration)

**Dependencies:**
- **Blocking:** DEV-396 (DPIA should assess transfer risks first)
- **Unlocks:** Production LLM calls with client context

**Change Classification:** ADDITIVE

**Relationship to Phase 9:** No Phase 9 task addresses vendor LLM contracts, SCCs, or TIA documentation.

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All integrations complete and functional
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] DPA executed with OpenAI (including EU Data Residency with zero retention)
- [ ] DPA executed with Anthropic (including Zero Data Retention agreement)
- [ ] Both DPAs include Standard Contractual Clauses (SCCs) per EC Decision 2021/914
- [ ] Transfer Impact Assessment (TIA) documented for US transfers
- [ ] TIA documents supplementary measures (PII anonymization, zero retention, encryption in transit)
- [ ] Backend configuration updated to use EU endpoints where available

**Code Size Guidelines:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

---

### DEV-399: Italian AI Law Garante Notification

**Priority:** HIGH | **Status:** NOT STARTED

**Problem:** Italy's AI Law (Legge 132/2025, signed September 2025) requires operators of AI systems processing personal data to notify the Garante before deployment. Processing may only begin 30 days after notification unless the Garante objects. This law postdates the original PratikoAI roadmap and is not covered by any existing task.

**Solution:** Prepare and submit notification to the Garante listing all AI-related processing activities, data categories, purposes, and data processors (Hetzner, OpenAI, Anthropic).

**Agent Assignment:** @Mario (primary)

**Dependencies:**
- **Blocking:** DEV-396 (DPIA), DEV-398 (LLM DPAs - needed to list processors)
- **Unlocks:** Public launch (30-day waiting period)

**Change Classification:** ADDITIVE

**Relationship to Phase 9:** New legal requirement that postdates the original Phase 9 planning. Not covered by any existing task.

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All sections complete
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] Notification document prepared listing all AI processing activities
- [ ] All data processors listed (Hetzner, OpenAI, Anthropic)
- [ ] Data categories and processing purposes documented
- [ ] Notification submitted to the Garante
- [ ] 30-day waiting period tracked and documented
- [ ] Launch timeline updated to account for waiting period

**Code Size Guidelines:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

---

### DEV-400: Public Sub-Processor List and Privacy Policy

**Priority:** HIGH | **Status:** NOT STARTED

**Problem:** EDPB Opinion 22/2024 requires full chain visibility of sub-processors. GDPR Articles 12-13 require a clear, accessible privacy policy. PratikoAI currently has neither a public sub-processor list nor a formal Italian-language privacy policy.

**Solution:** Create and publish a sub-processor list with all vendors, their roles, data processed, and locations. Draft an Italian-language privacy policy compliant with Art. 12-13 GDPR. Draft studio informativa template.

**Agent Assignment:** @Severino (primary), @Mario (business requirements)

**Dependencies:**
- **Blocking:** DEV-397 (Hetzner DPA), DEV-398 (LLM DPAs) - need finalized vendor list
- **Unlocks:** Public launch

**Change Classification:** ADDITIVE

**Files:**
- `docs/compliance/SUB_PROCESSORS.md`
- `docs/compliance/PRIVACY_POLICY_IT.md`

**Relationship to Phase 9:** Phase 9 builds technical GDPR features (software). This task produces the legal documentation required for public launch.

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All sections complete with accurate information
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] Sub-processor list includes all vendors (Hetzner, OpenAI, Anthropic, Stripe, SendGrid)
- [ ] Each sub-processor entry includes: name, service, data processed, country, DPA status
- [ ] Privacy policy in Italian covering all Art. 12-13 GDPR requirements
- [ ] Studio informativa template drafted
- [ ] Documents reviewed by legal counsel

**Code Size Guidelines:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

---

### DEV-401: ADR-025 GDPR Client Data Architecture

**Priority:** MEDIUM | **Status:** NOT STARTED

**Problem:** The project's architecture decision for GDPR client data handling (originally referenced as ADR-024) needs a formal ADR. ADR-024 was found to be about Workflow Automation Architecture, not GDPR. A new ADR-025 is needed to formally document the GDPR architecture decisions.

**Solution:** Create ADR-025 documenting the GDPR client data architecture: DPA structure between PratikoAI and studios, encryption layers (field-level AES-256-GCM + full-disk LUKS), data residency rationale (Hetzner Germany), LLM isolation strategy (PII anonymizer), and multi-tenant data isolation.

**Agent Assignment:** @Egidio (primary)

**Dependencies:**
- **Blocking:** DEV-396 (DPIA informs architecture decisions)
- **Unlocks:** None (documentation task)

**Change Classification:** ADDITIVE

**File:** `docs/architecture/decisions/ADR-025-gdpr-client-data-architecture.md`

**Relationship to Phase 9:** Provides the architectural rationale document that Phase 9's implementation should follow.

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All sections complete
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] ADR follows project ADR template format
- [ ] Documents DPA structure (processor/controller/sub-processor relationships)
- [ ] Documents encryption architecture (field-level + full-disk)
- [ ] Documents data residency decision (Hetzner Germany) with legal rationale
- [ ] Documents LLM isolation strategy (PII anonymizer architecture)
- [ ] Documents multi-tenant isolation (studio_id + RLS)
- [ ] Reviewed and approved by @Egidio

**Code Size Guidelines:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

---

### DEV-402: `/procedura` Slash Command Handler

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Professionals need a quick way to consult procedures as generic reference without starting a tracked workflow. The `/procedura` slash command (same pattern as existing `/utilizzo`) provides this.

**Solution:**
Parse `/procedura [query]` from chat input. Show a searchable procedure list or render a specific procedure in read-only mode. No ProceduraProgress record is created — this is purely informational.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-340 (ProceduraService), DEV-341 (Pre-configured Procedure)
- **Unlocks:** DEV-405 (E2E Tests)

**Change Classification:** ADDITIVE

**Figma Reference:** `ProcedureSelector.tsx` (inline procedure picker + CommandPopover) — Source: [`docs/figma-make-references/ProcedureSelector.tsx`](../figma-make-references/ProcedureSelector.tsx) | [Figma Make](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page)

**Error Handling:**
- Unknown command: Ignore, pass to normal chat flow
- No matching procedure: Return `"Nessuna procedura trovata per: {query}"`
- Service unavailable: Fallback to chat response, log at ERROR level
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation) at ERROR level

**Performance Requirements:**
- Command parsing: <50ms
- Procedure list render: <200ms
- Specific procedure render: <300ms

**Edge Cases:**
- **Empty Query:** `/procedura` with no args → show full searchable list
- **Partial Match:** `/procedura apertura` → show filtered list of matching procedures
- **Exact Match:** `/procedura apertura-piva` → render specific procedure detail
- **No Match:** `/procedura xyzabc` → friendly "no results" message

**File:** `app/services/slash_command_handler.py` (new) + `app/api/v1/chat.py` (extend)

**Methods:**
- `parse_slash_command(message)` - Detect and parse `/procedura` command from chat input
- `handle_procedura_command(query, studio_id)` - Route to list or detail view
- `render_procedura_list(procedures, query)` - Format searchable procedure list for chat
- `render_procedura_detail(procedura)` - Format read-only procedure detail for chat

**Testing Requirements:**
- **TDD:** Write `tests/services/test_slash_command_handler.py` FIRST
- **Unit Tests:**
  - `test_parse_procedura_command` - recognizes `/procedura` in message
  - `test_parse_procedura_with_query` - extracts query param
  - `test_handle_empty_query_returns_list` - shows all procedures
  - `test_handle_query_filters_results` - filters by query
  - `test_no_progress_record_created` - verify no ProceduraProgress side effect
- **Integration Tests:** `tests/api/test_chat_slash_commands.py`
- **Regression Tests:** Run `pytest tests/api/test_chat*.py`
- **Coverage Target:** 80%+ for slash command code

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All integrations complete and functional
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] `/procedura` recognized in chat input
- [ ] Searchable procedure list rendered
- [ ] Specific procedure rendered in read-only mode
- [ ] NO ProceduraProgress records created
- [ ] 80%+ test coverage achieved

---

### DEV-403: `@client` Mention System with Autocomplete

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Professionals need to quickly reference a specific client in chat to start tracked procedures or get client-contextual responses. The `@` mention pattern is familiar from messaging apps and provides a natural interaction model.

**Solution:**
When user types `@` in chat, trigger an autocomplete dropdown with client names (debounced 300ms). After selecting `@NomeCliente`, show an **action picker** with 4 options:
1. **Domanda generica** — Injects client context (regime, ATECO, posizione) into RAGState, user types free-form question
2. **Domanda sul cliente** — Focused client query mode (e.g., "ha pagamenti in scadenza?", "possiede un secondo immobile?"), queries client data directly
3. **Scheda cliente** — Renders full client info card inline in chat (anagrafica, regime, ATECO, posizione contributiva, procedure attive)
4. **Avvia procedura guidata** — Opens procedure selector (reuses ProcedureSelector from DEV-402) filtered/contextualized for this client, then starts tracked workflow via DEV-404

**Agent Assignment:** @Ezio (primary), @Livia (frontend autocomplete), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-309 (ClientService), DEV-340 (ProceduraService), DEV-345 (Procedura Context)
- **Unlocks:** DEV-405 (E2E Tests)

**Change Classification:** ADDITIVE

**Error Handling:**
- No matching client: Show `"Nessun cliente trovato per: {query}"`
- Ambiguous match (same name): Append CF suffix for disambiguation (e.g., `@Mario Rossi (RSSMRA80...)`)
- Deleted client mentioned: Show warning `"Cliente non più attivo"`, no context injection
- Special characters in name: Handle apostrophes (`@D'Angelo`), accents (`@André`), spaces
- Action picker timeout: If no action selected within 60s, collapse picker and show hint "Digita @ per riprovare"
- Client card data incomplete: Show available fields, gray out missing ones with "Dato non disponibile"
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, client_id) at ERROR level

**Performance Requirements:**
- Autocomplete search: <100ms (debounced 300ms on frontend)
- Client context injection: <200ms
- Full mention resolution: <500ms

**Edge Cases:**
- **Special Characters:** `@D'Angelo`, `@André Müller` → handle apostrophes, accents
- **Same-Name Disambiguation:** Multiple "Mario Rossi" → append CF suffix
- **Deleted Client:** `@` mentions deleted client → warning, no context injection
- **Empty Client DB:** `@` typed but no clients → show "Importa clienti per usare le menzioni"
- **Null Tenant:** `@` without valid studio_id → HTTP 403
- **Cross-Tenant:** Client from different studio → not shown in autocomplete

**File:** `app/services/client_mention_service.py` (new) + `app/api/v1/chat.py` (extend)

**Methods:**
- `search_clients_for_autocomplete(query, studio_id)` - Debounced search returning client list with CF, regime badge
- `resolve_client_mention(mention_text, studio_id)` - Map `@NomeCliente` → client_id
- `get_client_action_options(client_id)` - Return available actions for the selected client (all 4 by default, may vary if client has no procedures)
- `handle_client_action(client_id, action, rag_state)` - Route to appropriate handler based on selected action:
  - `generic_question`: inject client context into RAGState
  - `client_question`: inject client context + set query_mode to "client_focused"
  - `client_card`: return full client profile card data
  - `start_procedure`: delegate to ProcedureSelector + DEV-404 start_for_client
- `format_client_mention_tag(client)` - Format as styled mention tag (blue pill) for frontend
- `get_client_card(client_id, studio_id)` - Return full client info (anagrafica, regime, ATECO, posizione, active procedures)

**Testing Requirements:**
- **TDD:** Write `tests/services/test_client_mention_service.py` FIRST
- **Unit Tests:**
  - `test_search_clients_returns_matches` - basic autocomplete
  - `test_search_clients_debounce_ready` - search returns within 100ms
  - `test_resolve_mention_exact_match` - single match resolution
  - `test_resolve_mention_disambiguation` - same-name CF suffix
  - `test_resolve_mention_special_chars` - apostrophes, accents
  - `test_resolve_mention_deleted_client` - warning returned
  - `test_get_client_action_options_all_available` - all 4 actions returned
  - `test_handle_action_generic_question` - context injected into RAGState
  - `test_handle_action_client_question` - client-focused query mode set
  - `test_handle_action_client_card` - full profile returned
  - `test_handle_action_start_procedure` - delegates to procedure selector
  - `test_get_client_card_complete` - all fields populated
  - `test_get_client_card_partial` - missing fields handled gracefully
- **Integration Tests:** `tests/services/test_client_mention_integration.py`
- **Security Tests:**
  - `test_cross_tenant_mention_blocked` - no cross-studio leakage
  - `test_null_tenant_mention_rejected` - 403 on missing studio
- **Regression Tests:** Run `pytest tests/services/test_client*.py`
- **Coverage Target:** 80%+ for mention code

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All integrations complete and functional
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] `@` triggers autocomplete with client names
- [ ] Autocomplete debounced at 300ms
- [ ] Same-name disambiguation with CF suffix
- [ ] Special characters handled (apostrophes, accents)
- [ ] Deleted client warning displayed
- [ ] Action picker shows 4 options after client selection
- [ ] "Domanda generica" injects context and allows free-form input
- [ ] "Domanda sul cliente" sets client-focused query mode
- [ ] "Scheda cliente" renders full client info card inline
- [ ] "Avvia procedura guidata" opens procedure selector for client
- [ ] Action picker collapses after selection
- [ ] Cross-tenant isolation enforced
- [ ] 80%+ test coverage achieved

---

### DEV-404: Generic vs Client-Specific Procedure Logic Split

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
ProceduraService needs an explicit, clean separation between generic consultation mode (read-only, no side effects) and client-specific tracking mode (creates ProceduraProgress, enables step tracking). This separation must be enforced at the service layer to prevent accidental progress creation during consultation.

**Solution:**
Refine `ProceduraService` to have clearly separated code paths:
- `get_reference(procedura_id)` — returns procedure content, raises if not found, NO database writes
- `start_for_client(user_id, procedura_id, client_id)` — validates client exists and belongs to studio, creates ProceduraProgress, returns trackable progress object

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-340 (ProceduraService)
- **Unlocks:** DEV-405 (E2E Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/services/procedura_service.py`
- **Affected Files:**
  - `app/api/v1/procedure.py` (routes call correct service method)
- **Related Tests:**
  - `tests/services/test_procedura_service.py` (direct)
- **Baseline Command:** `pytest tests/services/test_procedura_service.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing ProceduraService reviewed
- [ ] Code paths clearly identified

**Error Handling:**
- `get_reference` on non-existent procedura: HTTP 404, `"Procedura non trovata"`
- `start_for_client` without client_id: HTTP 400, `"client_id obbligatorio per avviare una procedura"`
- `start_for_client` with deleted client: HTTP 400, `"Cliente non più attivo"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, procedura_id) at ERROR level

**Performance Requirements:**
- `get_reference`: <100ms (read-only, no writes)
- `start_for_client`: <200ms (includes ProceduraProgress creation)

**Edge Cases:**
- **get_reference Never Writes:** Verify with DB transaction inspection that no INSERT/UPDATE occurs
- **start_for_client Validates Client:** Client must exist, be active, and belong to same studio
- **Idempotent Start:** If progress already exists for same user+procedura+client → return existing

**File:** `app/services/procedura_service.py` (refine)

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_get_reference_returns_content` - returns procedura details
  - `test_get_reference_no_db_writes` - verify no ProceduraProgress created
  - `test_start_for_client_creates_progress` - creates ProceduraProgress
  - `test_start_for_client_requires_client_id` - rejects None client_id
  - `test_start_for_client_validates_client_active` - rejects deleted client
  - `test_start_for_client_validates_tenant` - rejects cross-tenant client
  - `test_start_for_client_idempotent` - returns existing progress
- **Regression Tests:** Run `pytest tests/services/test_procedura_service.py -v`
- **Coverage Target:** 90%+ for split logic

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All integrations complete and functional
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] `get_reference` is purely read-only (no DB writes)
- [ ] `start_for_client` requires and validates client_id
- [ ] Clear separation in code paths
- [ ] Idempotent start behavior
- [ ] 90%+ test coverage for split logic

---

### DEV-405: E2E Tests for `/procedura` and `@client` Features

**Reference:** [FR-001: Procedure Interattive](./PRATIKO_2.0_REFERENCE.md#fr-001-procedure-interattive)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need end-to-end tests verifying the new `/procedura` slash command and `@client` mention system work correctly together and independently.

**Solution:**
Create comprehensive E2E tests covering both features and their interaction.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-402 (/procedura command), DEV-403 (@client mention), DEV-404 (Logic split)
- **Unlocks:** None (final validation task)

**Change Classification:** ADDITIVE

**Error Handling:**
- Test environment setup failure: Mark test as ERROR, log setup issue
- External service unavailable: Skip test with SKIP, log reason
- **Logging:** All test failures MUST be logged at ERROR level

**Performance Requirements:**
- E2E test suite: <60s total runtime
- Individual flow test: <15s
- Setup/teardown: <5s

**File:** `tests/e2e/test_procedura_commands_flow.py`

**Methods:**
- `test_procedura_slash_command_list()` - `/procedura` shows all procedures in read-only mode
- `test_procedura_slash_command_search()` - `/procedura apertura` filters results
- `test_procedura_slash_command_detail()` - `/procedura apertura-piva` shows specific procedure
- `test_procedura_slash_command_no_progress()` - Verify no ProceduraProgress records created
- `test_client_mention_autocomplete()` - `@` triggers autocomplete with client names
- `test_client_mention_resolve()` - `@NomeCliente` resolves to client context
- `test_client_mention_start_procedura()` - `@NomeCliente` + procedure selection starts tracked workflow
- `test_combined_flow()` - `/procedura` consultation → then `@NomeCliente` to start tracked version
- `test_client_mention_cross_tenant_blocked()` - Security: no cross-studio client access
- `test_client_mention_action_picker_shown()` - After `@NomeCliente`, action picker with 4 options appears
- `test_client_mention_action_generic_question()` - "Domanda generica" injects context, allows question
- `test_client_mention_action_client_question()` - "Domanda sul cliente" enables focused query
- `test_client_mention_action_client_card()` - "Scheda cliente" renders inline card
- `test_client_mention_action_start_procedure()` - "Avvia procedura guidata" opens procedure selector

**Testing Requirements:**
- **This IS the testing task**
- **E2E Tests:**
  - `test_procedura_slash_command_list` - full list consultation
  - `test_procedura_slash_command_search` - filtered consultation
  - `test_procedura_slash_command_no_progress` - read-only verified
  - `test_client_mention_autocomplete` - autocomplete works
  - `test_client_mention_resolve` - context injection works
  - `test_client_mention_start_procedura` - tracked workflow started
  - `test_combined_flow` - consultation then tracking
  - `test_client_mention_cross_tenant_blocked` - security verified
- **Coverage Target:** Full workflow coverage

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All integrations complete and functional
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] `/procedura` consultation flow tested
- [ ] `@client` mention flow tested
- [ ] Combined flow tested
- [ ] No ProceduraProgress in read-only mode verified
- [ ] Cross-tenant isolation verified
- [ ] Action picker flow tested for all 4 actions
- [ ] All tests passing

---

## Phase 13: Figma Gap Coverage (20 Tasks)

> **Added:** 2026-02-25 — Gap analysis of 15 Figma reference files (11,478 lines) against PRATIKO_2.0_TASKS.md revealed 16 gaps across Significant, Moderate, and Minor severity levels. This phase closes those gaps. Tasks that extend existing phases are cross-referenced here but numbered in the DEV-422–441 range for traceability.

### Figma Gap Coverage Summary

| Gap # | Severity | Description | Task(s) | Extends |
|-------|----------|-------------|---------|---------|
| 1 | SIGNIFICANT | In-App Notification System | DEV-422 to DEV-427 | — |
| 2 | SIGNIFICANT | INPS/INAIL Fields on ClientProfile | DEV-428 | DEV-302 |
| 3 | SIGNIFICANT | Procedure Suggestions per Client | DEV-429 | — |
| 4 | SIGNIFICANT | Quick Action Counts API | DEV-430 | — |
| 5 | SIGNIFICANT | Modelli e Formulari Library | DEV-431, DEV-432 | — |
| 6 | MODERATE | Chat Feedback Persistent Storage | DEV-433 | — |
| 7 | MODERATE | Dashboard Client Distribution Charts | DEV-434 | DEV-355 |
| 8 | MODERATE | Dashboard Matching Statistics | DEV-435 | DEV-355 |
| 9 | MODERATE | Dashboard Period Selector | DEV-436 | DEV-356 |
| 10 | MODERATE | Deadline Amount & Penalties Fields | DEV-437 | DEV-380 |
| 11 | MODERATE | Per-Deadline User Reminders | DEV-438 | — |
| 12 | MODERATE | Interactive Question Templates Activation | DEV-439 | — |
| 13 | MINOR | Figma README Update | — | (housekeeping, done inline) |
| 14 | MINOR | Domande Pronte / FAQ Libraries | (deferred — content curation, no code task) | — |
| 15 | MINOR | Full Notifications Page | DEV-440 | DEV-422 |
| 16 | MINOR | Settings Page (Studio Preferences) | DEV-441 | DEV-300 |

> **Gap 13 (Figma README):** Resolved inline — the 6 missing "Used By" mappings have been added to `docs/figma-make-references/README.md` and the Appendix below.
>
> **Gap 14 (Domande Pronte / FAQ):** Deferred — these are content curation tasks (populating a question/FAQ library), not code tasks. They can be served by the existing Knowledge Base once content is authored. No new DEV task needed.

---

### DEV-422: Notification SQLModel & Migration

**Reference:** [NotificationsDropdown.tsx](../figma-make-references/NotificationsDropdown.tsx)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The Figma NotificationsDropdown shows a full in-app notification system with 4 types (scadenza, match, comunicazione, normativa), time-grouped display, unread badges, and mark-as-read. The existing `ccnl_notification_service.py` uses in-memory mock data with no persistence. There is no Notification SQLModel, no API endpoint, and no database storage.

**Solution:**
Create a `Notification` SQLModel for persistent storage of in-app notifications. Include type, priority, read status, and timestamps for time-grouped display.

**Agent Assignment:** @Primo (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model), DEV-307 (Migration infrastructure)
- **Unlocks:** DEV-423 (NotificationService), DEV-424 (API), DEV-425 (Triggers), DEV-426 (Frontend), DEV-440 (Full Page)

**Change Classification:** ADDITIVE

**Impact Analysis:** N/A (new code only)

**Pre-Implementation Verification:** N/A (ADDITIVE)

**Figma Reference:** `NotificationsDropdown.tsx` — Source: [`docs/figma-make-references/NotificationsDropdown.tsx`](../figma-make-references/NotificationsDropdown.tsx)

**Error Handling:**
- Invalid notification_type: HTTP 422, `"Tipo notifica non valido"`
- Invalid priority: HTTP 422, `"Priorità non valida"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Notification creation: <50ms
- Bulk insert (100 notifications): <500ms

**Edge Cases:**
- **Nulls:** null title → HTTP 422; null description → allowed (some notification types are title-only)
- **Enum Validation:** Invalid type/priority → HTTP 422 with valid options listed
- **Timestamp:** created_at auto-set; read_at null until explicitly marked
- **Tenant Isolation:** All queries must include user_id + studio_id filter
- **Soft Delete:** Dismissed notifications soft-deleted, excluded from unread count

**File:** `app/models/notification.py`

**Notification Fields:**
- `id`: UUID (primary key)
- `user_id`: UUID (FK to User)
- `studio_id`: UUID (FK to Studio, for tenant isolation)
- `notification_type`: enum (SCADENZA, MATCH, COMUNICAZIONE, NORMATIVA)
- `priority`: enum (LOW, MEDIUM, HIGH, URGENT)
- `title`: str (max 200)
- `description`: text (nullable)
- `reference_id`: UUID (nullable — FK to related entity: deadline, match, communication, or regulation)
- `reference_type`: str (nullable — "deadline", "match", "communication", "regulation")
- `is_read`: bool (default: false)
- `read_at`: datetime (nullable)
- `dismissed`: bool (default: false)
- `created_at`: datetime
- `updated_at`: datetime

**Testing Requirements:**
- **TDD:** Write `tests/models/test_notification.py` FIRST
- **Unit Tests:**
  - `test_notification_creation_valid` - valid notification with all fields
  - `test_notification_type_enum` - all 4 type values
  - `test_notification_priority_enum` - all 4 priority values
  - `test_notification_default_unread` - is_read defaults to false
  - `test_notification_studio_isolation` - tenant isolation via studio_id
- **Edge Case Tests:**
  - `test_notification_null_description_allowed` - nullable description
  - `test_notification_reference_polymorphic` - reference_id + reference_type combos
- **Coverage Target:** 80%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| High notification volume | MEDIUM | Index on (user_id, is_read, created_at), pagination |
| Cross-tenant leak | CRITICAL | Always filter by studio_id |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Notification model with all 4 types from Figma
- [ ] Polymorphic reference (reference_id + reference_type) for linking to source entity
- [ ] Tenant isolation via studio_id
- [ ] Migration runs cleanly
- [ ] All existing tests still pass

---

### DEV-423: NotificationService CRUD

**Reference:** [NotificationsDropdown.tsx](../figma-make-references/NotificationsDropdown.tsx)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need a service layer to create, list, mark-as-read, and manage notifications. The Figma shows grouped display (Oggi/Ieri/Questa Settimana), unread badge count, mark-as-read per item, and bulk "Segna tutte come lette".

**Solution:**
Create `NotificationService` with CRUD methods, time-grouped listing, unread count, and bulk operations.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-422 (Notification model)
- **Unlocks:** DEV-424 (API), DEV-425 (Triggers)

**Change Classification:** ADDITIVE

**Error Handling:**
- Notification not found: HTTP 404, `"Notifica non trovata"`
- Already read: Idempotent (no error, return success)
- Unauthorized: HTTP 403, `"Accesso non autorizzato a questa notifica"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- List notifications (50): <100ms
- Unread count: <50ms
- Mark as read: <50ms
- Mark all as read: <200ms

**Edge Cases:**
- **Empty List:** No notifications → return empty array, unread_count=0
- **Already Read:** Mark-as-read on already-read notification → idempotent, no error
- **Pagination:** page=0 → page=1; page>max → empty list
- **Time Grouping:** Notifications from today, yesterday, this week, and older → grouped correctly
- **Bulk Mark Read:** Mark-all only affects current user's unread notifications in current studio
- **Concurrent Reads:** Two sessions mark-as-read simultaneously → both succeed (idempotent)

**File:** `app/services/notification_service.py`

**Methods:**
- `create_notification(user_id, studio_id, type, title, description, reference_id, reference_type, priority)` - Create notification
- `list_notifications(user_id, studio_id, page, size, unread_only)` - List with time grouping
- `get_unread_count(user_id, studio_id)` - Count for badge
- `mark_as_read(notification_id, user_id, studio_id)` - Mark single as read
- `mark_all_as_read(user_id, studio_id)` - Bulk mark as read
- `dismiss_notification(notification_id, user_id, studio_id)` - Soft delete

**Testing Requirements:**
- **TDD:** Write `tests/services/test_notification_service.py` FIRST
- **Unit Tests:**
  - `test_create_notification` - creates with correct fields
  - `test_list_notifications_grouped` - time-grouped output
  - `test_unread_count` - accurate count
  - `test_mark_as_read` - sets is_read and read_at
  - `test_mark_all_as_read` - bulk update
  - `test_dismiss_notification` - soft delete
  - `test_list_unread_only` - filter by unread
- **Edge Case Tests:**
  - `test_mark_as_read_idempotent` - already-read notification
  - `test_list_empty` - no notifications
  - `test_cross_tenant_blocked` - wrong studio_id returns 404
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Time-grouped listing (Oggi/Ieri/Questa Settimana/Precedenti)
- [ ] Unread count for badge display
- [ ] Single and bulk mark-as-read
- [ ] Tenant isolation enforced
- [ ] 80%+ test coverage

---

### DEV-424: Notification API Endpoints

**Reference:** [NotificationsDropdown.tsx](../figma-make-references/NotificationsDropdown.tsx)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Frontend needs API endpoints to fetch, display, and manage notifications shown in the NotificationsDropdown component.

**Solution:**
Create notification REST endpoints: list (with time grouping), unread count, mark-as-read, mark-all-as-read.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-423 (NotificationService)
- **Unlocks:** DEV-426 (Frontend dropdown), DEV-440 (Full page)

**Change Classification:** ADDITIVE

**Error Handling:**
- Notification not found: HTTP 404, `"Notifica non trovata"`
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- Invalid input: HTTP 422, `"Dati non validi"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- GET /notifications: <200ms (p95)
- GET /notifications/unread-count: <50ms (p95)
- PUT /notifications/:id/read: <100ms
- PUT /notifications/mark-all-read: <300ms

**File:** `app/api/v1/notifications.py`

**Endpoints:**
- `GET /api/v1/notifications` - List notifications (query params: page, size, unread_only)
- `GET /api/v1/notifications/unread-count` - Unread badge count
- `PUT /api/v1/notifications/{id}/read` - Mark single as read
- `PUT /api/v1/notifications/mark-all-read` - Bulk mark as read
- `DELETE /api/v1/notifications/{id}` - Dismiss notification

**Testing Requirements:**
- **TDD:** Write `tests/api/v1/test_notifications.py` FIRST
- **Unit Tests:**
  - `test_list_notifications_200` - successful list
  - `test_list_notifications_unread_filter` - unread_only param
  - `test_unread_count_200` - badge count
  - `test_mark_as_read_200` - mark single
  - `test_mark_all_as_read_200` - bulk mark
  - `test_dismiss_notification_200` - soft delete
  - `test_notification_not_found_404` - invalid ID
  - `test_cross_tenant_403` - wrong studio
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All endpoints follow existing API patterns (thin handlers, delegate to service)
- [ ] Pagination support
- [ ] Tenant isolation in all endpoints
- [ ] OpenAPI schema complete

---

### DEV-425: Notification Creation Triggers

**Reference:** [NotificationsDropdown.tsx](../figma-make-references/NotificationsDropdown.tsx)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Notifications must be created automatically when relevant events occur: deadline approaching, match found, communication approved, normativa updated. Currently no trigger wiring exists.

**Solution:**
Add notification creation calls to existing service methods for the 4 trigger types. Use the NotificationService.create_notification() method from DEV-423.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-423 (NotificationService), DEV-383 (Deadline Matching), DEV-320 (NormativeMatching), DEV-335 (Communication Approval)
- **Unlocks:** DEV-427 (E2E Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- `app/services/deadline_service.py` — add notification on approaching deadline
- `app/services/matching_service.py` — add notification on new match found
- `app/services/communication_service.py` — add notification on communication approved
- `app/services/rss_feed_service.py` or KB ingestion — add notification on normativa update

**Pre-Implementation Verification:**
- Verify each service exists and has the right hook point
- Confirm NotificationService is importable

**Error Handling:**
- Notification creation failure: Log at ERROR, do NOT fail the parent operation (fire-and-forget pattern)
- Missing reference entity: Log warning, create notification without reference_id
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Notification creation must not add >50ms to parent operation
- Use background task or fire-and-forget for bulk notifications

**Edge Cases:**
- **Duplicate Triggers:** Same event triggers twice → deduplicate by reference_id + type within 1 hour window
- **Missing User:** Notification for deleted/deactivated user → skip silently, log warning
- **Bulk Events:** Regulation update affects 50 clients → batch-create notifications, not 50 individual creates
- **Service Down:** NotificationService unavailable → parent operation succeeds, notification silently skipped

**File:** Multiple files (see Impact Analysis)

**Trigger Map:**
- **SCADENZA:** When `DeadlineService` detects deadline within notification_days_before threshold → create SCADENZA notification for each affected client's studio user
- **MATCH:** When `MatchingService` creates a new match → create MATCH notification
- **COMUNICAZIONE:** When `CommunicationService` approves a communication → create COMUNICAZIONE notification
- **NORMATIVA:** When RSS/KB ingestion detects a new or updated regulation → create NORMATIVA notification

**Testing Requirements:**
- **TDD:** Write `tests/services/test_notification_triggers.py` FIRST
- **Unit Tests:**
  - `test_deadline_approaching_creates_notification` - scadenza trigger
  - `test_match_found_creates_notification` - match trigger
  - `test_communication_approved_creates_notification` - comunicazione trigger
  - `test_normativa_updated_creates_notification` - normativa trigger
  - `test_trigger_failure_does_not_fail_parent` - fire-and-forget
  - `test_duplicate_trigger_deduplicated` - deduplication
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All 4 notification types triggered by real events
- [ ] Fire-and-forget: parent operations never fail due to notification errors
- [ ] Deduplication within 1-hour window
- [ ] All existing tests still pass

---

### DEV-426: Notification Dropdown Frontend Component

**Reference:** [NotificationsDropdown.tsx](../figma-make-references/NotificationsDropdown.tsx)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
The frontend needs a bell icon dropdown in `ChatHeader.tsx` showing notifications grouped by time period, with unread badge, mark-as-read, and "Vedi tutte" link.

**Solution:**
Implement `NotificationsDropdown` component using the Figma reference for layout/styling, integrated into the existing ChatHeader. Uses the API from DEV-424.

**Agent Assignment:** @Livia (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-424 (Notification API)
- **Unlocks:** DEV-440 (Full Notifications Page)

**Change Classification:** ADDITIVE (new component) + MODIFYING (ChatHeader integration)

**Figma Reference:** `NotificationsDropdown.tsx` — Source: [`docs/figma-make-references/NotificationsDropdown.tsx`](../figma-make-references/NotificationsDropdown.tsx)

**Error Handling:**
- API failure: Show "Errore nel caricamento delle notifiche" with retry button
- Empty state: Show "Nessuna nuova notifica" message

**File:** `web/src/app/chat/components/NotificationsDropdown.tsx` (new) + `web/src/app/chat/components/ChatHeader.tsx` (modify)

**UI Elements (from Figma):**
- Bell icon with unread count badge (red dot with number)
- Dropdown panel with gradient header
- Time-grouped sections: Oggi, Ieri, Questa Settimana
- 4 notification types color-coded: Scadenza (red), Match (orange), Comunicazione (green), Normativa (blue)
- Per-item mark-as-read button
- "Segna tutte come lette" bulk action in header
- "Vedi tutte le notifiche" footer link → DEV-440

**Testing Requirements:**
- **TDD:** Write `web/src/app/chat/components/__tests__/NotificationsDropdown.test.tsx` FIRST
- **Unit Tests:**
  - `test_renders_bell_icon` - icon visible in header
  - `test_shows_unread_badge` - badge with count
  - `test_opens_dropdown_on_click` - dropdown toggles
  - `test_groups_by_time_period` - Oggi/Ieri/Questa Settimana grouping
  - `test_color_codes_notification_types` - 4 colors
  - `test_mark_as_read` - calls API
  - `test_mark_all_as_read` - bulk action
  - `test_empty_state` - no notifications message
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Bell icon in ChatHeader with unread badge
- [ ] Dropdown with time-grouped notifications
- [ ] 4 notification types with correct colors
- [ ] Mark-as-read (single + bulk)
- [ ] "Vedi tutte le notifiche" link present
- [ ] Italian text throughout

---

### DEV-427: Notification System E2E Tests

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
End-to-end validation that the full notification pipeline works: trigger → storage → API → frontend display.

**Solution:**
Write E2E test covering the complete notification flow.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-422 to DEV-426 (all notification tasks)
- **Unlocks:** None (validation task)

**Change Classification:** ADDITIVE

**File:** `tests/e2e/test_notification_flow.py`

**Testing Requirements:**
- `test_deadline_notification_flow` - deadline approaching → notification created → appears in API → mark as read
- `test_match_notification_flow` - match found → notification created → appears in dropdown
- `test_mark_all_read_flow` - create multiple → mark all read → unread count = 0
- `test_cross_tenant_isolation` - notifications from studio A not visible to studio B
- **Coverage Target:** Full workflow coverage

**Acceptance Criteria:**
- [ ] All 4 notification types tested end-to-end
- [ ] Tenant isolation verified
- [ ] Mark-as-read verified
- [ ] All tests passing

---

### DEV-428: ClientProfile INPS/INAIL Extension

**Reference:** [ClientActionPicker.tsx](../figma-make-references/ClientActionPicker.tsx)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The Figma ClientProfileCard (in ClientActionPicker.tsx) shows a "Posizione Contributiva" section with INPS data (status, matricola, ultimo pagamento) and INAIL data (status, PAT number). The current ClientProfile model (DEV-302) has `posizione_agenzia_entrate` but no INPS/INAIL fields. These fields don't exist in any model.

**Solution:**
Extend the Client or ClientProfile model with INPS and INAIL fields. Add migration. Update the ClientService (DEV-309) to handle these fields in CRUD operations.

**Agent Assignment:** @Primo (primary), @Ezio (service update), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-301 (Client model), DEV-302 (ClientProfile), DEV-307 (Migration)
- **Unlocks:** DEV-403 (Client mention — profile card shows these fields)

**Change Classification:** MODIFYING

**Impact Analysis:**
- `app/models/client.py` or `app/models/client_profile.py` — add fields
- `app/services/client_service.py` — update CRUD for new fields
- `app/schemas/client.py` — update request/response schemas
- Migration file — new columns

**Pre-Implementation Verification:**
- Read DEV-302's current model definition to determine correct placement

**Figma Reference:** `ClientActionPicker.tsx` — Source: [`docs/figma-make-references/ClientActionPicker.tsx`](../figma-make-references/ClientActionPicker.tsx) (ClientProfileCard section)

**Error Handling:**
- Invalid INPS status: HTTP 422, `"Stato INPS non valido"`
- Invalid INAIL PAT format: HTTP 422, `"Numero PAT INAIL non valido"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Nulls:** All INPS/INAIL fields nullable (not all clients have these)
- **INPS Matricola Format:** Validate format if provided (numeric, 10 digits)
- **INAIL PAT Format:** Validate format if provided (numeric, 8-10 digits)
- **Status Enum:** REGOLARE, IRREGOLARE, NON_ISCRITTO, SOSPESO
- **Date Validation:** inps_ultimo_pagamento must be ≤ today

**New Fields:**
- `inps_matricola`: str (nullable, max 10, indexed)
- `inps_status`: enum (REGOLARE, IRREGOLARE, NON_ISCRITTO, SOSPESO) (nullable)
- `inps_ultimo_pagamento`: date (nullable)
- `inail_pat`: str (nullable, max 10)
- `inail_status`: enum (REGOLARE, IRREGOLARE, NON_ISCRITTO, SOSPESO) (nullable)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_client_inps_inail.py` FIRST
- **Unit Tests:**
  - `test_client_inps_fields_nullable` - all fields accept null
  - `test_client_inps_status_enum` - valid enum values
  - `test_client_inail_pat_format` - PAT validation
  - `test_client_inps_matricola_format` - matricola validation
  - `test_client_service_crud_with_inps_inail` - CRUD operations include new fields
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] INPS/INAIL fields added to model
- [ ] Migration runs cleanly
- [ ] ClientService CRUD handles new fields
- [ ] Schemas updated for API request/response
- [ ] All existing tests still pass

---

### DEV-429: Procedure Suggestions per Client

**Reference:** [ClientActionPicker.tsx](../figma-make-references/ClientActionPicker.tsx)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
The Figma ClientProfileCard and ClientContextCard show "Procedure Suggerite" — procedures recommended for a specific client based on their profile (regime fiscale, codice ATECO, situation). No task generates these suggestions. DEV-320 (NormativeMatchingService) matches regulations, not procedures. The archived suggested_actions were quick actions, not full procedure recommendations.

**Solution:**
Create a `ProcedureSuggestionService` that, given a client profile, returns relevant procedures from the P001-P010 library. Use rule-based matching on regime fiscale, ATECO code, and client status (e.g., "Apertura P.IVA" for a prospect, "Trasformazione regime" for a forfettario approaching revenue limits).

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-301 (Client model), DEV-341 (Pre-configured Procedures)
- **Unlocks:** DEV-403 (Client mention — shows suggested procedures on profile card)

**Change Classification:** ADDITIVE

**Figma Reference:** `ClientActionPicker.tsx` — Source: [`docs/figma-make-references/ClientActionPicker.tsx`](../figma-make-references/ClientActionPicker.tsx) (Procedure Suggerite section)

**Error Handling:**
- Client not found: HTTP 404, `"Cliente non trovato"`
- No matching procedures: Return empty array (not an error)
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Performance Requirements:**
- Suggestion generation: <200ms (rule-based, no LLM)
- Cache suggestions per client for 1 hour (invalidate on profile update)

**Edge Cases:**
- **Incomplete Profile:** Missing regime_fiscale or ATECO → return generic procedures only
- **No Matches:** Profile doesn't match any rule → return empty array
- **Deactivated Client:** Soft-deleted client → return empty array
- **Multiple Matches:** Client matches 5+ procedures → return all, sorted by relevance score

**File:** `app/services/procedure_suggestion_service.py`

**Methods:**
- `suggest_procedures(client_id, studio_id)` - Return list of suggested procedures with relevance scores
- `_match_by_regime(regime_fiscale)` - Match procedures by tax regime
- `_match_by_ateco(codice_ateco)` - Match procedures by ATECO sector
- `_match_by_status(client_status)` - Match procedures by client lifecycle status

**Matching Rules (examples):**
- Prospect with no P.IVA → suggest "Apertura P.IVA" (P001)
- Forfettario near €85k limit → suggest "Trasformazione Regime" (P003)
- New employee hired → suggest "Assunzione Dipendente" (P005)
- Regime ordinario, ATECO construction → suggest "DURC Renewal" (P008)

**Testing Requirements:**
- **TDD:** Write `tests/services/test_procedure_suggestion_service.py` FIRST
- **Unit Tests:**
  - `test_suggest_apertura_piva_for_prospect` - prospect gets apertura
  - `test_suggest_trasformazione_for_forfettario` - near-limit forfettario
  - `test_no_suggestions_for_generic_client` - no matches returns empty
  - `test_multiple_suggestions_sorted` - relevance sorting
  - `test_incomplete_profile_generic_only` - missing fields
  - `test_cache_invalidation_on_profile_update` - cache works correctly
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Rule-based matching on regime, ATECO, status
- [ ] Returns relevant procedures from P001-P010 library
- [ ] Cached per client (1 hour TTL)
- [ ] Integrates with ClientProfileCard display
- [ ] 80%+ test coverage

---

### DEV-430: Quick Action Counts API

**Reference:** [ChatPage.tsx](../figma-make-references/ChatPage.tsx)

**Priority:** LOW | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The Figma ChatPage shows 6 Quick Action cards with live counts: "Modelli e Formulari (245)", "Scadenze Fiscali (12)", "Aggiornamenti Urgenti (3)", "Normative Recenti (28)", "Domande Pronte (89)", "FAQ (127)". No backend endpoint supplies these counts.

**Solution:**
Create a lightweight aggregation endpoint that returns counts from existing services: deadlines, KB/RSS for normative/aggiornamenti, and future content stores for FAQ/questions. Return 0 for categories not yet populated.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-381 (DeadlineService — for deadline count), DEV-300 (Studio — for tenant context)
- **Unlocks:** Frontend Quick Actions widget

**Change Classification:** ADDITIVE

**Error Handling:**
- Service unavailable: Return 0 for that category, log at WARNING
- Unauthorized: HTTP 403, `"Accesso non autorizzato"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation) at ERROR level

**Performance Requirements:**
- Total response: <300ms (parallel queries to each source)
- Cache counts for 5 minutes (studio-scoped)

**Edge Cases:**
- **No Data:** All counts return 0 (valid for new studio)
- **Partial Failure:** One source unavailable → return 0 for that category, other counts still populated
- **Cache Stale:** Counts may be up to 5 minutes stale (acceptable for dashboard display)

**File:** `app/api/v1/quick_actions.py` (new) + `app/services/quick_action_counts_service.py` (new)

**Endpoint:**
- `GET /api/v1/quick-actions/counts` → `{ modelli_formulari: int, scadenze_fiscali: int, aggiornamenti_urgenti: int, normative_recenti: int, domande_pronte: int, faq: int }`

**Testing Requirements:**
- **TDD:** Write `tests/api/v1/test_quick_actions.py` FIRST
- **Unit Tests:**
  - `test_quick_action_counts_200` - returns all 6 counts
  - `test_quick_action_counts_empty_studio` - all zeros for new studio
  - `test_quick_action_counts_partial_failure` - one service down → 0 for that, others populated
  - `test_quick_action_counts_cached` - second call uses cache
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Returns all 6 count categories
- [ ] Graceful degradation on partial failures
- [ ] Cached for 5 minutes per studio
- [ ] Tenant isolation enforced

---

### DEV-431: Formulari SQLModel & Service

**Priority:** LOW | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
The Figma ChatPage Quick Actions show "Modelli e Formulari — 245 modelli". No task covers a forms/templates library. This is distinct from Communication Templates (DEV-336) — it's a document templates/forms repository (e.g., Modello AA9/12, F24, CU, Modello Unico).

**Solution:**
Create a `Formulario` SQLModel for document templates with categories, and a `FormularioService` with listing and search. Templates are reference data (pre-seeded), not user-generated.

**Agent Assignment:** @Primo (model), @Ezio (service), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model), DEV-307 (Migration)
- **Unlocks:** DEV-432 (API), DEV-430 (Quick Action Counts — modelli_formulari count)

**Change Classification:** ADDITIVE

**Error Handling:**
- Formulario not found: HTTP 404, `"Modello non trovato"`
- Invalid category: HTTP 422, `"Categoria non valida"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**File:** `app/models/formulario.py` (new) + `app/services/formulario_service.py` (new)

**Formulario Fields:**
- `id`: UUID (primary key)
- `code`: str (unique, e.g., "AA9-12", "F24", "CU")
- `name`: str (e.g., "Modello AA9/12 — Apertura P.IVA")
- `description`: text
- `category`: enum (APERTURA, DICHIARAZIONI, VERSAMENTI, LAVORO, PREVIDENZA, ALTRO)
- `issuing_authority`: str (e.g., "Agenzia delle Entrate", "INPS")
- `external_url`: str (nullable — link to official form download)
- `is_active`: bool (default: true)
- `created_at`, `updated_at`

**Methods:**
- `list_formulari(category, search_query, page, size)` - Paginated list with optional filters
- `get_formulario(formulario_id)` - Single form detail
- `count_formulari()` - Total count for Quick Actions widget
- `seed_formulari()` - Seed initial reference data

**Testing Requirements:**
- **TDD:** Write `tests/models/test_formulario.py` and `tests/services/test_formulario_service.py` FIRST
- **Unit Tests:**
  - `test_formulario_creation` - valid creation
  - `test_formulario_category_enum` - all categories
  - `test_list_formulari_paginated` - pagination
  - `test_list_formulari_by_category` - filter by category
  - `test_search_formulari_by_name` - text search
  - `test_count_formulari` - total count
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Formulario model with categories
- [ ] Service with list, search, count
- [ ] Seed data for common Italian tax forms
- [ ] Migration runs cleanly

---

### DEV-432: Formulari API Endpoint

**Priority:** LOW | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
Frontend needs API to list and search document templates for the "Modelli e Formulari" Quick Action.

**Solution:**
Create thin API endpoint delegating to FormularioService.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-431 (FormularioService)
- **Unlocks:** Frontend Formulari page

**Change Classification:** ADDITIVE

**File:** `app/api/v1/formulari.py`

**Endpoints:**
- `GET /api/v1/formulari` - List with pagination + category filter + search
- `GET /api/v1/formulari/{id}` - Single form detail
- `GET /api/v1/formulari/count` - Total count

**Testing Requirements:**
- **TDD:** Write `tests/api/v1/test_formulari.py` FIRST
- **Unit Tests:**
  - `test_list_formulari_200` - successful list
  - `test_list_formulari_by_category` - category filter
  - `test_get_formulario_200` - single detail
  - `test_get_formulario_404` - not found
  - `test_count_formulari_200` - count endpoint
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Thin handlers (<30 lines), delegate to service
- [ ] OpenAPI schema complete
- [ ] All endpoints paginated where appropriate

---

### DEV-433: Chat Feedback Persistent Storage

**Reference:** [ChatPage.tsx](../figma-make-references/ChatPage.tsx)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
The Figma ChatPage shows a rich feedback system with 3 types (correct/incomplete/wrong) and 13 Italian categories (normativa obsoleta, calcolo sbagliato, etc.). The existing `app/api/v1/feedback.py` only sends thumbs up/down to Langfuse (no database persistence). The `expert_feedback_collector.py` has the right category schema but is only wired for expert review flows, not standard user chat feedback. User feedback is lost if Langfuse is unavailable and cannot be queried for analytics.

**Solution:**
Create a `ChatFeedback` SQLModel that persists user feedback in the app database alongside the Langfuse integration. Wire the existing Italian categories from `expert_feedback_collector.py` into the standard user feedback flow. Keep the existing Langfuse integration as a secondary destination.

> **Note:** The frontend FeedbackButtons component (`web/src/app/chat/components/FeedbackButtons.tsx`) is already implemented with its own design (thumbs up/down + copy) and must NOT be restyled to match Figma. This task is backend-only: add persistence and optionally extend the API to accept richer feedback categories.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model), DEV-307 (Migration)
- **Unlocks:** Analytics on feedback quality, feedback-driven KB improvement

**Change Classification:** ADDITIVE (new model) + MODIFYING (existing feedback endpoint)

**Impact Analysis:**
- `app/models/chat_feedback.py` — new SQLModel
- `app/api/v1/feedback.py` — extend to persist to DB alongside Langfuse
- `app/services/expert_feedback_collector.py` — reuse category definitions

**Error Handling:**
- Invalid feedback_type: HTTP 422, `"Tipo feedback non valido"`
- Invalid category: HTTP 422, `"Categoria non valida"`
- DB persistence failure: Log error, still send to Langfuse (graceful degradation)
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Langfuse Down:** Feedback still persists to DB
- **DB Down:** Feedback still sent to Langfuse, log error
- **Both Down:** Return HTTP 503, `"Servizio feedback temporaneamente non disponibile"`
- **Duplicate Feedback:** Same user + same message → upsert (update existing feedback)
- **Anonymous User:** Allow feedback without user_id (set to null)

**File:** `app/models/chat_feedback.py` (new)

**ChatFeedback Fields:**
- `id`: UUID (primary key)
- `user_id`: UUID (nullable — FK to User)
- `studio_id`: UUID (nullable — FK to Studio)
- `trace_id`: str (Langfuse trace ID for correlation)
- `message_id`: str (chat message identifier)
- `feedback_type`: enum (CORRECT, INCOMPLETE, INCORRECT)
- `category`: str (nullable — one of the 13 Italian categories)
- `comment`: text (nullable, max 1000 chars)
- `score`: int (0 or 1, for backward compat with existing thumbs up/down)
- `created_at`: datetime

**Testing Requirements:**
- **TDD:** Write `tests/models/test_chat_feedback.py` and `tests/api/v1/test_feedback_persistence.py` FIRST
- **Unit Tests:**
  - `test_chat_feedback_creation` - valid creation with all fields
  - `test_chat_feedback_type_enum` - 3 feedback types
  - `test_chat_feedback_categories` - valid Italian categories
  - `test_feedback_endpoint_persists_to_db` - DB write on feedback submit
  - `test_feedback_endpoint_still_sends_langfuse` - Langfuse integration unchanged
  - `test_feedback_upsert_on_duplicate` - same user+message updates
  - `test_feedback_langfuse_down_db_still_works` - graceful degradation
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] ChatFeedback model with type + category + comment
- [ ] Existing feedback endpoint extended (not replaced)
- [ ] Dual-write: DB + Langfuse
- [ ] Backward compatible with existing thumbs up/down
- [ ] Italian categories reused from expert_feedback_collector
- [ ] Frontend FeedbackButtons NOT modified

---

### DEV-434: Dashboard Client Distribution Charts

**Reference:** [DashboardPage.tsx](../figma-make-references/DashboardPage.tsx)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The Figma DashboardPage shows 3 distribution charts not covered by DEV-355: clients per regime fiscale (pie), clients per settore ATECO (bar), clients per stato (donut). DEV-355 only mentions "client count, active procedure, pending communications, recent matches".

**Solution:**
Extend the dashboard aggregation service (DEV-355) to include client distribution queries grouped by regime_fiscale, codice_ateco sector, and status.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-355 (Dashboard Aggregation), DEV-301 (Client model with regime/ATECO)
- **Unlocks:** DEV-356 (Dashboard API — include distribution data in response)

**Change Classification:** MODIFYING (extends DEV-355's service)

**Impact Analysis:**
- `app/services/dashboard_service.py` — add distribution aggregation methods

**Figma Reference:** `DashboardPage.tsx` — Source: [`docs/figma-make-references/DashboardPage.tsx`](../figma-make-references/DashboardPage.tsx)

**Error Handling:**
- No clients: Return empty distributions (valid for new studio)
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation) at ERROR level

**Performance Requirements:**
- Distribution queries: <100ms each (indexed GROUP BY)
- Cacheable for 5 minutes per studio

**File:** `app/services/dashboard_service.py` (extend)

**Methods:**
- `get_client_distribution_by_regime(studio_id)` → `[{ regime: str, count: int }]`
- `get_client_distribution_by_ateco(studio_id)` → `[{ settore: str, count: int }]`
- `get_client_distribution_by_status(studio_id)` → `[{ status: str, count: int }]`

**Testing Requirements:**
- **TDD:** Write `tests/services/test_dashboard_distributions.py` FIRST
- **Unit Tests:**
  - `test_distribution_by_regime` - groups clients by regime fiscale
  - `test_distribution_by_ateco` - groups clients by ATECO sector
  - `test_distribution_by_status` - groups clients by active/pending/inactive
  - `test_distribution_empty_studio` - returns empty arrays
  - `test_distribution_tenant_isolation` - only counts studio's clients
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] 3 distribution queries matching Figma charts
- [ ] Tenant-isolated (studio_id filter)
- [ ] Cached for 5 minutes
- [ ] All existing tests still pass

---

### DEV-435: Dashboard Matching Statistics

**Reference:** [DashboardPage.tsx](../figma-make-references/DashboardPage.tsx)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The Figma DashboardPage shows a "Statistiche Matching" card with: Total Matches (342), Conversion Rate (73.2%), Pending Reviews (18), and a "Rivedi match" action button. DEV-355 mentions "recent matches" but not conversion rate or pending review counts.

**Solution:**
Extend the dashboard aggregation service to include matching statistics: total matches, conversion rate (actioned/total), and pending review count.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-355 (Dashboard Aggregation), DEV-320 (NormativeMatching — for match data)
- **Unlocks:** DEV-356 (Dashboard API — include matching stats in response)

**Change Classification:** MODIFYING (extends DEV-355's service)

**Figma Reference:** `DashboardPage.tsx` — Source: [`docs/figma-make-references/DashboardPage.tsx`](../figma-make-references/DashboardPage.tsx)

**Performance Requirements:**
- Matching stats query: <100ms
- Cacheable for 5 minutes per studio

**File:** `app/services/dashboard_service.py` (extend)

**Methods:**
- `get_matching_statistics(studio_id)` → `{ total_matches: int, conversion_rate: float, pending_reviews: int }`

**Testing Requirements:**
- **TDD:** Write `tests/services/test_dashboard_matching_stats.py` FIRST
- **Unit Tests:**
  - `test_matching_stats_total` - correct total count
  - `test_matching_stats_conversion_rate` - actioned / total ratio
  - `test_matching_stats_pending_reviews` - unresolved matches count
  - `test_matching_stats_empty` - no matches → total=0, rate=0.0, pending=0
  - `test_matching_stats_tenant_isolation` - only studio's matches
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Total matches, conversion rate, pending reviews
- [ ] Tenant-isolated
- [ ] Cached for 5 minutes
- [ ] All existing tests still pass

---

### DEV-436: Dashboard Period Selector

**Reference:** [DashboardPage.tsx](../figma-make-references/DashboardPage.tsx)

**Priority:** LOW | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The Figma DashboardPage shows a Week/Month/Year toggle that filters all dashboard data. DEV-355/356 don't mention period-based filtering.

**Solution:**
Extend the Dashboard API (DEV-356) to accept a `period` query parameter (WEEK, MONTH, YEAR) and apply date range filtering to all aggregation queries.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-356 (Dashboard API)
- **Unlocks:** Frontend period toggle

**Change Classification:** MODIFYING (extends DEV-356)

**Impact Analysis:**
- `app/api/v1/dashboard.py` — add `period` query param
- `app/services/dashboard_service.py` — add date range filtering to all queries

**Figma Reference:** `DashboardPage.tsx` — Source: [`docs/figma-make-references/DashboardPage.tsx`](../figma-make-references/DashboardPage.tsx)

**Performance Requirements:**
- Filtered queries: <200ms (indexed on created_at/date columns)

**Edge Cases:**
- **No Period:** Default to MONTH
- **Invalid Period:** HTTP 422, `"Periodo non valido. Valori accettati: WEEK, MONTH, YEAR"`
- **No Data in Period:** Return zeros (valid result)

**File:** `app/api/v1/dashboard.py` (extend) + `app/services/dashboard_service.py` (extend)

**Testing Requirements:**
- **TDD:** Write `tests/api/v1/test_dashboard_period.py` FIRST
- **Unit Tests:**
  - `test_dashboard_period_week` - last 7 days
  - `test_dashboard_period_month` - last 30 days
  - `test_dashboard_period_year` - last 365 days
  - `test_dashboard_period_default` - no param → MONTH
  - `test_dashboard_period_invalid` - HTTP 422
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] `period` query parameter on dashboard endpoint
- [ ] WEEK/MONTH/YEAR filtering
- [ ] Default to MONTH
- [ ] All existing dashboard tests still pass

---

### DEV-437: Deadline Amount & Penalties Fields

**Reference:** [ScadenzeFiscaliPage.tsx](../figma-make-references/ScadenzeFiscaliPage.tsx)

**Priority:** MEDIUM | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
The Figma ScadenzeFiscaliPage shows each deadline with "Importo: €X" and "Sanzioni: percentuale + importo" fields. DEV-380's Deadline model doesn't include amount or penalty information.

**Solution:**
Add `importo` (decimal, nullable) and `sanzioni` (JSONB, nullable) fields to the Deadline model (DEV-380). The JSONB sanzioni field stores `{ percentuale: float, importo_fisso: decimal, descrizione: str }`.

**Agent Assignment:** @Primo (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-380 (Deadline model)
- **Unlocks:** DEV-385 (Deadline API — include amount/penalties in response)

**Change Classification:** MODIFYING (extends DEV-380)

**Impact Analysis:**
- `app/models/deadline.py` — add fields
- Migration file — add columns
- `app/services/deadline_service.py` — update CRUD
- `app/schemas/deadline.py` — update schemas

**Error Handling:**
- Negative importo: HTTP 422, `"L'importo non può essere negativo"`
- Invalid sanzioni format: HTTP 422, `"Formato sanzioni non valido"`

**Edge Cases:**
- **Null Amount:** Many deadlines have no fixed amount (e.g., "Dichiarazione Redditi") → null allowed
- **Null Penalties:** Some deadlines have no defined penalties → null allowed
- **Zero Amount:** Valid (some deadlines are zero-cost but time-sensitive)
- **Multiple Penalties:** sanzioni JSONB can be an array of penalty tiers

**New Fields on Deadline:**
- `importo`: Numeric(12, 2) (nullable — deadline amount in EUR)
- `sanzioni`: JSONB (nullable — penalty info: `{ percentuale: float, importo_fisso: str, descrizione: str }` or array of penalty tiers)

**Testing Requirements:**
- **TDD:** Write `tests/models/test_deadline_amounts.py` FIRST
- **Unit Tests:**
  - `test_deadline_importo_nullable` - null allowed
  - `test_deadline_importo_valid` - decimal value stored correctly
  - `test_deadline_importo_negative_rejected` - validation
  - `test_deadline_sanzioni_jsonb` - JSON structure stored/retrieved
  - `test_deadline_sanzioni_nullable` - null allowed
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] importo and sanzioni fields added
- [ ] Migration runs cleanly
- [ ] Existing deadline tests still pass
- [ ] Schemas updated

---

### DEV-438: Per-Deadline User Reminders

**Reference:** [ScadenzeFiscaliPage.tsx](../figma-make-references/ScadenzeFiscaliPage.tsx)

**Priority:** LOW | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The Figma ScadenzeFiscaliPage shows a bell icon on each deadline card letting users set a personal reminder. DEV-384 (Deadline Notification Background Job) sends automatic notifications at fixed intervals (30/7/1 day), but users cannot configure per-deadline custom reminders.

**Solution:**
Create a `DeadlineReminder` SQLModel and API to let users opt-in to specific deadline notifications at a custom time. Integrate with the notification system (DEV-422-427).

**Agent Assignment:** @Primo (model), @Ezio (service + API), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-380 (Deadline model), DEV-422 (Notification model), DEV-384 (Background job)
- **Unlocks:** Frontend bell icon on deadline cards

**Change Classification:** ADDITIVE

**Error Handling:**
- Deadline not found: HTTP 404, `"Scadenza non trovata"`
- Reminder in past: HTTP 422, `"La data del promemoria deve essere futura"`
- Duplicate reminder: HTTP 409, `"Promemoria già impostato per questa scadenza"`
- **Logging:** All errors MUST be logged with context (user_id, studio_id, operation, resource_id) at ERROR level

**Edge Cases:**
- **Already Passed:** remind_at in the past → rejected
- **Same Day:** remind_at = deadline_date → allowed (last-minute reminder)
- **Multiple Reminders:** One user can have only one reminder per deadline (upsert)
- **Deadline Deleted:** Cascade soft-delete the reminder
- **User Deletes Reminder:** Soft delete, stop future notification

**File:** `app/models/deadline_reminder.py` (new) + `app/services/deadline_reminder_service.py` (new) + `app/api/v1/deadline_reminders.py` (new)

**DeadlineReminder Fields:**
- `id`: UUID (primary key)
- `deadline_id`: UUID (FK to Deadline)
- `user_id`: UUID (FK to User)
- `studio_id`: UUID (FK to Studio)
- `remind_at`: datetime (when to send notification)
- `is_active`: bool (default: true)
- `notification_sent`: bool (default: false)
- `created_at`, `updated_at`

**Endpoints:**
- `POST /api/v1/deadlines/{id}/reminder` — Set reminder (body: `{ remind_at: datetime }`)
- `DELETE /api/v1/deadlines/{id}/reminder` — Remove reminder
- `GET /api/v1/deadlines/{id}/reminder` — Check if reminder is set

**Testing Requirements:**
- **TDD:** Write `tests/models/test_deadline_reminder.py` and `tests/api/v1/test_deadline_reminders.py` FIRST
- **Unit Tests:**
  - `test_create_reminder` - valid creation
  - `test_create_reminder_past_rejected` - past date rejected
  - `test_delete_reminder` - soft delete
  - `test_duplicate_reminder_upsert` - upsert behavior
  - `test_reminder_tenant_isolation` - studio_id filter
  - `test_cascade_on_deadline_delete` - reminder removed when deadline deleted
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] DeadlineReminder model with user-configurable remind_at
- [ ] API for set/remove/check reminder
- [ ] Integrates with notification system (creates SCADENZA notification at remind_at)
- [ ] Tenant isolation
- [ ] Migration runs cleanly

---

### DEV-439: Interactive Question Templates Activation

**Priority:** LOW | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
The Figma ChatPage shows 3 interactive question template categories (tax_situation, compliance_issue, planning_optimization) with multi-step follow-up flows. The codebase has archived YAML templates under `archived/phase5_templates/templates/interactive_questions/` (procedures.yaml, calculations.yaml) and the `proactivity_engine.py` service, but these aren't in production. ADR-021 is accepted but the templates are dormant.

**Solution:**
Un-archive the interactive question templates, update them to match the Figma's 3 categories, and wire them into the active LangGraph pipeline via the proactivity engine.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-340 (Procedure framework — for procedure-based questions), existing LangGraph pipeline
- **Unlocks:** Proactive question generation in chat

**Change Classification:** MODIFYING

**Impact Analysis:**
- `archived/phase5_templates/` → move to `app/templates/interactive_questions/`
- `app/services/proactivity_engine_simplified.py` — wire template loading
- LangGraph pipeline config — enable interactive question node

**Error Handling:**
- Template not found: Log warning, skip question generation (no user-facing error)
- Invalid YAML: Log error at startup, skip malformed template
- **Logging:** All errors MUST be logged with context (template_id, category) at ERROR level

**Edge Cases:**
- **No Matching Template:** Query doesn't match any template category → no question asked (normal chat)
- **Template Validation:** Invalid YAML at startup → skip that template, log error, others still work
- **User Skips Question:** User ignores interactive question → proceed with normal response

**File:** `app/templates/interactive_questions/` (new directory) + `app/services/proactivity_engine_simplified.py` (extend)

**Template Categories (from Figma):**
1. `tax_situation` — Tax calculations (IRPEF, IVA, INPS, ravvedimento)
2. `compliance_issue` — Compliance checks (scadenze, adempimenti, CCNL)
3. `planning_optimization` — Planning (apertura, trasformazione, assunzione)

**Testing Requirements:**
- **TDD:** Write `tests/services/test_interactive_questions_activation.py` FIRST
- **Unit Tests:**
  - `test_templates_load_from_yaml` - YAML parsing works
  - `test_tax_situation_template_triggers` - correct trigger conditions
  - `test_compliance_issue_template_triggers` - correct trigger conditions
  - `test_planning_optimization_template_triggers` - correct trigger conditions
  - `test_no_template_match_skips_question` - graceful skip
  - `test_invalid_yaml_skipped_gracefully` - malformed YAML handled
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Templates un-archived to active directory
- [ ] 3 Figma categories implemented
- [ ] Wired into proactivity engine
- [ ] LangGraph pipeline activates question node
- [ ] All existing tests still pass

---

### DEV-440: Full Notifications Page

**Reference:** [NotificationsDropdown.tsx](../figma-make-references/NotificationsDropdown.tsx)

**Priority:** LOW | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The NotificationsDropdown's "Vedi tutte le notifiche" footer link navigates to a full-page notification view. No frontend task covers this page.

**Solution:**
Create a `/notifiche` page that shows all notifications with pagination, filtering by type, and bulk actions. Reuses the API from DEV-424.

**Agent Assignment:** @Livia (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-424 (Notification API), DEV-426 (NotificationsDropdown — shares components)
- **Unlocks:** None

**Change Classification:** ADDITIVE

**Error Handling:**
- API failure: Show "Errore nel caricamento delle notifiche" with retry
- Empty state: Show "Nessuna notifica" with friendly illustration

**File:** `web/src/app/notifiche/page.tsx` (new)

**UI Elements:**
- Page header: "Notifiche" with unread count
- Filter tabs: Tutte, Scadenze, Match, Comunicazioni, Normative
- Notification list with pagination (reuse card design from dropdown)
- Bulk actions: "Segna tutte come lette", "Elimina lette"
- Add "Notifiche" menu item to ChatHeader user menu (between Scadenze Fiscali and separator)

**Testing Requirements:**
- **TDD:** Write `web/src/app/notifiche/__tests__/page.test.tsx` FIRST
- **Unit Tests:**
  - `test_renders_notifications_page` - page loads
  - `test_filter_by_type` - type filter tabs work
  - `test_pagination` - pagination controls
  - `test_mark_all_read` - bulk action
  - `test_empty_state` - no notifications message
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Full-page notification list with pagination
- [ ] Filter by notification type
- [ ] Bulk mark-as-read
- [ ] Menu item added to ChatHeader
- [ ] Italian text throughout

---

### DEV-441: Settings Page (Studio Preferences)

**Priority:** LOW | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
The Figma sidebar shows "Impostazioni" but no Figma file or task exists for a settings page. DEV-300 (Studio model) has a `settings` JSONB field but no UI to manage it. Users need a page to configure studio-level preferences (notification preferences, display settings, etc.).

**Solution:**
Create a `/impostazioni` settings page with sections for studio preferences, notification preferences, and account settings. Uses the existing Studio.settings JSONB field for persistence.

**Agent Assignment:** @Livia (primary), @Ezio (API), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model — settings JSONB), DEV-422 (Notification model — for notification prefs)
- **Unlocks:** None

**Change Classification:** ADDITIVE

**Error Handling:**
- Save failure: Show "Errore nel salvataggio delle impostazioni" with retry
- Invalid settings: HTTP 422, `"Impostazioni non valide"`

**File:** `web/src/app/impostazioni/page.tsx` (new) + `app/api/v1/settings.py` (new)

**UI Sections:**
1. **Profilo Studio** — Studio name, logo, contact info (read from DEV-300)
2. **Preferenze Notifiche** — Toggle per notification type (scadenze, match, comunicazioni, normative)
3. **Visualizzazione** — Display preferences (items per page, default period)

**API Endpoints:**
- `GET /api/v1/settings` — Get studio settings
- `PUT /api/v1/settings` — Update studio settings
- Add "Impostazioni" menu item to ChatHeader user menu (before "Esci")

**Testing Requirements:**
- **TDD:** Write `web/src/app/impostazioni/__tests__/page.test.tsx` and `tests/api/v1/test_settings.py` FIRST
- **Unit Tests:**
  - `test_renders_settings_page` - page loads
  - `test_save_notification_preferences` - toggles persist
  - `test_get_settings_200` - API returns current settings
  - `test_update_settings_200` - API persists changes
  - `test_update_settings_tenant_isolation` - studio_id enforced
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Settings page with 3 sections
- [ ] API for get/update studio settings
- [ ] Menu item added to ChatHeader
- [ ] Italian text throughout
- [ ] Tenant isolation enforced

---

## Phase 14: Hybrid Email Sending Configuration (8 Tasks)

> **Added:** 2026-02-26 — Hybrid email sending with plan-based gating per ADR-034. Base plan studios use PratikoAI centralized email (`comunicazioni@pratikoai.com` with `Reply-To` header). Pro/Premium studios can optionally configure their own SMTP server for branded email sending from their own domain. SMTP credentials encrypted at rest via Fernet.

### Hybrid Email Configuration Summary

| Plan | Monthly Price | Custom SMTP | Sender Identity | Reply-To |
|------|--------------|-------------|-----------------|----------|
| **Base** | €25 | No | `"Studio Name" <comunicazioni@pratikoai.com>` | Studio's email (from profile) |
| **Pro** | €75 | Yes (optional) | `"Studio Name" <info@studiorossi.it>` | Configurable |
| **Premium** | €150 | Yes (optional) | `"Studio Name" <info@studiorossi.it>` | Configurable |

---

### DEV-442: StudioEmailConfig SQLModel & Migration

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Studios on Pro/Premium plans need to send emails from their own domain for brand trust and higher open rates, but there is no model to store per-studio SMTP configuration. SMTP passwords are sensitive data requiring encryption at rest per GDPR Art. 32.

**Solution:**
Create a `StudioEmailConfig` SQLModel with Fernet-encrypted password storage. One config per user (unique constraint on `user_id`). Password is write-only — never returned in API responses or logged.

**Agent Assignment:** @Primo (primary), @Severino (security review — credential encryption), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300 (Studio model), DEV-307 (Migration infrastructure)
- **Unlocks:** DEV-443 (Service), DEV-444 (API), DEV-445 (Hybrid Sending)

**Change Classification:** ADDITIVE

**ADR Reference:** `docs/architecture/decisions/ADR-034-hybrid-email-sending-configuration.md`

**Error Handling:**
- Duplicate user_id: HTTP 409, `"Configurazione email già esistente per questo utente"`
- Invalid SMTP host: HTTP 422, `"Host SMTP non valido"`
- **Logging:** All errors MUST be logged with context (user_id, operation). NEVER log SMTP passwords.

**Security Requirements:**
- SMTP password encrypted via `cryptography.fernet.Fernet`
- Encryption key in `SMTP_ENCRYPTION_KEY` env var (not in DB)
- Password excluded from `__repr__`, model serialization, and structured logs

**File:** `app/models/studio_email_config.py`

**Fields:**
- `id`: int (primary key)
- `user_id`: int (FK to user.id, unique, indexed)
- `smtp_host`: str (max 255)
- `smtp_port`: int (default 587)
- `smtp_username`: str (max 255)
- `smtp_password_encrypted`: str (max 1024 — Fernet ciphertext)
- `use_tls`: bool (default true)
- `from_email`: str (max 255)
- `from_name`: str (max 255)
- `reply_to_email`: str (nullable, max 255)
- `is_verified`: bool (default false)
- `is_active`: bool (default true)
- `created_at`: datetime
- `updated_at`: datetime

**Testing Requirements:**
- **TDD:** Write `tests/models/test_studio_email_config.py` FIRST
- **Unit Tests:**
  - `test_valid_creation` — all fields populated
  - `test_user_id_uniqueness` — unique constraint
  - `test_password_encryption_roundtrip` — encrypt then decrypt matches original
  - `test_tls_default_true` — use_tls defaults to True
  - `test_is_verified_default_false` — new configs start unverified
  - `test_nullable_reply_to` — reply_to_email can be null
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Fernet encryption for SMTP password
- [ ] Password never appears in logs or `__repr__`
- [ ] Unique constraint on user_id
- [ ] Alembic migration generated

---

### DEV-443: StudioEmailConfigService (CRUD + Validation)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Need a service layer to manage studio email configurations with plan gating, credential encryption, and SMTP connection validation before saving.

**Solution:**
Service with CRUD operations, `billing_plan_slug` check (Pro/Premium only), Fernet encrypt/decrypt, SMTP handshake validation (EHLO + STARTTLS + LOGIN without sending), and SSRF protection (allowlist ports, reject private IPs).

**Agent Assignment:** @Ezio (primary), @Severino (security review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-442 (StudioEmailConfig model)
- **Unlocks:** DEV-444 (API), DEV-445 (Hybrid Sending), DEV-449 (Key Rotation)

**Change Classification:** ADDITIVE

**Error Handling:**
- Base plan user: HTTP 403, `"La configurazione email personalizzata richiede il piano Pro o Premium"`
- SMTP connection failure: HTTP 422, `"Impossibile connettersi al server SMTP: {error}"`
- Private IP SSRF attempt: HTTP 422, `"Host SMTP non consentito"`
- Invalid port: HTTP 422, `"Porta SMTP non consentita (usa 25, 465 o 587)"`
- **Logging:** Log connection validation attempts (success/failure) with user_id, smtp_host, smtp_port. NEVER log passwords.

**Security Requirements:**
- SSRF protection: allowlist ports (25, 465, 587), reject RFC 1918 private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), reject localhost/127.x
- Connection timeout: 10 seconds max
- Rate limit: 5 test attempts per hour per user

**File:** `app/services/studio_email_config_service.py`

**Methods:**
- `create_or_update_config(user_id, config_data)` — encrypt password, validate SMTP, save
- `get_config(user_id)` — return config with password redacted
- `delete_config(user_id)` — remove config, revert to default
- `validate_smtp_connection(host, port, username, password, use_tls)` — handshake only
- `_encrypt_password(plaintext)` → ciphertext
- `_decrypt_password(ciphertext)` → plaintext
- `_check_plan_eligibility(user)` — raises if Base plan

**Testing Requirements:**
- **TDD:** Write `tests/services/test_studio_email_config_service.py` FIRST
- **Unit Tests:**
  - `test_create_config_pro_plan` — succeeds for Pro
  - `test_create_config_premium_plan` — succeeds for Premium
  - `test_create_config_base_plan_rejected` — 403
  - `test_update_config` — updates existing
  - `test_get_config_password_redacted` — password not in response
  - `test_delete_config` — removes record
  - `test_smtp_validation_success` — mock SMTP handshake
  - `test_smtp_validation_failure` — connection error
  - `test_ssrf_private_ip_blocked` — 10.x, 172.16.x, 192.168.x rejected
  - `test_invalid_port_rejected` — port 8080 rejected
  - `test_encrypt_decrypt_roundtrip` — Fernet encryption works
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Plan gating: Base → 403, Pro/Premium → allowed
- [ ] SMTP password encrypted via Fernet
- [ ] GET never returns plaintext password
- [ ] SSRF protection active
- [ ] Connection validation before save

---

### DEV-444: Studio Email Config API Endpoints

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
No API endpoints exist for studios to configure their custom email sending settings.

**Solution:**
Thin REST endpoints delegating to `StudioEmailConfigService`. Plan gating at endpoint level. Rate-limited test endpoint.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-443 (StudioEmailConfigService)
- **Unlocks:** DEV-446 (Settings UI), DEV-447 (E2E Tests)

**Change Classification:** ADDITIVE

**File:** `app/api/v1/email_config.py`

**Endpoints:**
- `POST /api/v1/email-config` — Create/update SMTP config (Pro/Premium only)
- `GET /api/v1/email-config` — Get config (password → `has_password: true`)
- `DELETE /api/v1/email-config` — Remove custom config
- `POST /api/v1/email-config/test` — Send test email (rate limited: 5/hour)

**Testing Requirements:**
- **TDD:** Write `tests/api/v1/test_email_config.py` FIRST
- **Unit Tests:**
  - `test_create_config_201` — valid creation
  - `test_get_config_200_password_redacted` — password not in response
  - `test_delete_config_204` — successful deletion
  - `test_base_plan_403` — rejected for Base plan
  - `test_test_email_200` — test email sent
  - `test_test_email_failure_422` — SMTP error returns details
  - `test_unauthenticated_401` — no token
  - `test_rate_limit_test_endpoint` — 429 after 5 attempts
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Plan gating enforced (403 for Base)
- [ ] Password never in GET response
- [ ] Rate limiting on test endpoint
- [ ] All user-facing errors in Italian

---

### DEV-445: EmailService Hybrid Sending (Fallback Chain)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
`EmailService._send_email()` currently uses only global SMTP settings. It needs to support per-user custom SMTP configurations with a fallback chain.

**Solution:**
Refactor email sending to: (1) check for verified custom SMTP config → use it, (2) fall back to PratikoAI default SMTP if no config or sending fails, (3) log error if both fail. Set appropriate `From` and `Reply-To` headers based on which sender is used.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-443 (StudioEmailConfigService), DEV-333 (Email Sending Integration)
- **Unlocks:** DEV-447 (E2E Tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Modified file:** `app/services/email_service.py`
- **Existing callers:** `send_welcome_email()`, `send_metrics_report()`, communication sending, task digests
- **Backward compatibility:** All existing callers continue to work (they don't pass user_id → always use default SMTP)
- **New callers:** Communication sending passes `user_id` to enable custom SMTP lookup

**Modifies:** `app/services/email_service.py`

**Testing Requirements:**
- **TDD:** Write `tests/services/test_email_service_hybrid.py` FIRST
- **Unit Tests:**
  - `test_send_with_custom_config` — uses studio's SMTP
  - `test_fallback_on_custom_failure` — custom fails → default succeeds
  - `test_default_when_no_custom_config` — no config → default SMTP
  - `test_reply_to_header_set` — Reply-To matches studio email
  - `test_from_header_with_studio_name` — From includes studio name
  - `test_unverified_config_skipped` — is_verified=false → skip to default
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Fallback chain: custom → default → log error
- [ ] From/Reply-To headers correct per sender
- [ ] Unverified configs skipped
- [ ] Backward compatible with existing callers
- [ ] No breaking changes to existing email flows

---

### DEV-446: Email Config Settings UI Section

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Pro/Premium users need a UI to configure their custom SMTP settings. Base users should see a clear upsell.

**Solution:**
Add "Configurazione Email" section to `/impostazioni` settings page. Plan-gated: Base shows upsell banner, Pro/Premium shows SMTP form with test button.

**Agent Assignment:** @Livia (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-444 (Email Config API), DEV-441 (Settings Page)
- **Unlocks:** None

**Change Classification:** MODIFYING (extends DEV-441)

**Modifies:** `web/src/app/impostazioni/page.tsx`

**UI Elements:**
- **Base plan:** Banner: "Passa al piano Pro per inviare email dal tuo dominio" with upgrade CTA
- **Pro/Premium:** Form fields: Host SMTP, Porta, Username, Password (masked), TLS toggle, Nome mittente, Email mittente, Email risposte (opzionale)
- **Status indicator:** Badge "Verificata" (green) / "Non verificata" (yellow)
- **Test button:** "Testa configurazione" — sends test email, shows success/error

**Testing Requirements:**
- **TDD:** Write `web/src/app/impostazioni/__tests__/email-config.test.tsx` FIRST
- **Unit Tests:**
  - `test_base_plan_shows_upsell` — upsell banner visible
  - `test_pro_plan_shows_form` — SMTP form visible
  - `test_form_submit` — save triggers API call
  - `test_test_button` — test triggers POST /email-config/test
  - `test_status_indicator` — shows verified/unverified badge
  - `test_password_field_masked` — password input type=password
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Plan-gated UI (upsell vs form)
- [ ] SMTP form with all fields
- [ ] Test button with success/error feedback
- [ ] Italian text throughout

---

### DEV-447: Hybrid Email Sending E2E Tests

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need end-to-end validation that the full hybrid email pipeline works correctly including plan gating, config persistence, and sending fallback.

**Solution:**
E2E tests covering: configure → verify → send → check headers. Also test plan downgrade behavior and Base plan default-only flow.

**Agent Assignment:** @Clelia (primary)

**Dependencies:**
- **Blocking:** DEV-445 (Hybrid Sending), DEV-444 (Email Config API)
- **Unlocks:** None

**Change Classification:** ADDITIVE

**File:** `tests/e2e/test_hybrid_email_flow.py`

**Testing Requirements:**
- `test_custom_smtp_send_flow` — Pro user: configure → verify → send → correct headers
- `test_fallback_to_default_flow` — custom SMTP fails → fallback works
- `test_plan_downgrade_disables_custom` — Pro→Base: custom config becomes inactive
- `test_base_plan_uses_default_only` — Base user: always PratikoAI sender

**Acceptance Criteria:**
- [ ] All 4 E2E flows passing
- [ ] Cross-plan behavior verified

---

### DEV-448: Add `custom_email_allowed` to Billing Plans

**Priority:** HIGH | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
The billing plan model has no field to gate custom email configuration at the data level. Plan checking is currently by slug comparison, which is fragile.

**Solution:**
Add `custom_email_allowed` boolean to `BillingPlan` model and YAML config. Base: false, Pro: true, Premium: true. Update sync and schema.

**Agent Assignment:** @Ezio (primary), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-442 (StudioEmailConfig model — needs the gating field)
- **Unlocks:** None (DEV-443 can use slug-based check initially, then migrate to this field)

**Change Classification:** MODIFYING

**Modifies:** `app/models/billing.py`, `config/billing_plans.yaml`, `app/services/billing_plan_service.py`, `app/schemas/billing.py`

**Testing Requirements:**
- **TDD:** Write `tests/services/test_billing_plan_custom_email.py` FIRST
- **Unit Tests:**
  - `test_base_plan_custom_email_false` — Base = false
  - `test_pro_plan_custom_email_true` — Pro = true
  - `test_premium_plan_custom_email_true` — Premium = true
  - `test_yaml_sync_includes_field` — field synced from YAML
  - `test_schema_exposes_field` — API response includes field
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] YAML, model, service, and schema updated
- [ ] Sync preserves field on app startup

---

### DEV-449: SMTP Encryption Key Rotation Support

**Priority:** LOW | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
If the Fernet encryption key (`SMTP_ENCRYPTION_KEY`) is compromised or needs periodic rotation, all stored SMTP passwords must be re-encrypted with the new key.

**Solution:**
Management script that accepts old key + new key, decrypts all passwords with old, re-encrypts with new, and updates records atomically within a database transaction.

**Agent Assignment:** @Ezio (primary), @Severino (security review), @Clelia (tests)

**Dependencies:**
- **Blocking:** DEV-443 (StudioEmailConfigService)
- **Unlocks:** None

**Change Classification:** ADDITIVE

**File:** `app/scripts/rotate_smtp_encryption_key.py`

**Testing Requirements:**
- **TDD:** Write `tests/scripts/test_rotate_smtp_key.py` FIRST
- **Unit Tests:**
  - `test_reencrypt_all_records` — all passwords re-encrypted correctly
  - `test_atomic_transaction` — rollback on failure
  - `test_invalid_old_key_raises` — wrong old key detected
  - `test_empty_table_noop` — no records = success with count 0
- **Coverage Target:** 80%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Atomic re-encryption (all or nothing)
- [ ] Logs count of re-encrypted records (never logs passwords)
- [ ] Works with 0, 1, or N records

---

## Critical E2E Test Flows

### Flow 1: Client Management
```
tests/e2e/test_client_management_flow.py
1. Login → 2. Create Studio → 3. Import Clients → 4. Update Client → 5. Delete Client
```

### Flow 2: Matching & Suggestions
```
tests/e2e/test_matching_flow.py
1. Create Clients → 2. Ingest Regulation → 3. Match → 4. View Suggestions → 5. Dismiss
```

### Flow 3: Communication Workflow
```
tests/e2e/test_communication_flow.py
1. Create Draft → 2. Submit Review → 3. Approve → 4. Send → 5. Verify Delivery
```

### Flow 4: Procedura Progress
```
tests/e2e/test_procedura_flow.py
1. Start Procedura → 2. Complete Steps → 3. Resume → 4. Complete → 5. View History
```

### Flow 5: Notification System (DEV-427)
```
tests/e2e/test_notification_flow.py
1. Trigger Event → 2. Notification Created → 3. Appears in API → 4. Mark as Read → 5. Verify Cross-Tenant Isolation
```

### Flow 6: Full User Journey (DEV-371)
```
tests/e2e/test_pratikoai_2_0_flow.py
1. Register → 2. Create Studio → 3. Import Clients → 4. Chat → 5. View Matches
   → 6. Create Communication → 7. Approve → 8. Send → 9. View Dashboard
```

### Flow 7: Hybrid Email Sending (DEV-447)
```
tests/e2e/test_hybrid_email_flow.py
1. Pro user configures custom SMTP → 2. Validates connection → 3. Sends communication
   → 4. Verify From/Reply-To headers → 5. Simulate failure → 6. Verify fallback to default
   → 7. Base user sends → 8. Verify PratikoAI sender used
```

---

## Success Criteria

- [ ] 100 clients per studio functional
- [ ] 9 procedure available
- [ ] Matching suggestions appear in chat
- [ ] Communications workflow complete (draft → approve → send)
- [ ] All fiscal calculations working with client context
- [ ] **69.5%+ test coverage maintained**
- [ ] **Multi-tenant isolation 95%+ tested**
- [ ] Response time ≤3 seconds maintained
- [ ] GDPR compliance verified
- [ ] DPA acceptance workflow functional
- [ ] In-app notification system operational (4 trigger types)
- [ ] Hybrid email sending: Base uses PratikoAI email, Pro/Premium can configure custom SMTP (ADR-034)
- [ ] **All E2E test flows passing**
- [ ] **All regression tests passing**

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Multi-tenancy breaks data | Reversible migrations, backup before deploy, **95%+ isolation tests** |
| Matching >3s | HNSW index, profile vector pre-computation, **performance tests** |
| GDPR isolation breach | RLS + encryption + explicit checks, **GDPR test suite** |
| Feature creep | Strict MVP scope, defer complex features |
| Migration failure | Test on staging, full backup, **migration tests** |
| Pipeline regression | Feature flags, **extensive LangGraph tests**, **E2E tests** |

---

## ChatPage Integration Guidelines

> **IMPORTANT:** The Figma Make `ChatPage.tsx` reference file (`docs/figma-make-references/ChatPage.tsx`) is a 108KB standalone prototype that includes features and UI patterns we do NOT implement in our codebase. When implementing tasks that reference ChatPage.tsx, follow these rules:

### What to extract from Figma's ChatPage.tsx

- **Only the specific Screen feature** described in the task's `**Figma Reference:**` section
- Component interaction patterns (e.g., how @mention triggers autocomplete, how /command opens a popover)
- Color values, spacing, and styling tokens that match our existing design system
- Italian text/labels for UI elements

### What NOT to change in the existing ChatPage

The following aspects of our chat implementation are FINAL and must NOT be modified to match Figma's ChatPage.tsx:

- **Navigation:** We use a user menu dropdown in `ChatHeader.tsx` (top-right User icon), NOT a sidebar nav. Do not add sidebar navigation, tab bars, or header navigation links from Figma.
- **Sidebar:** Our sidebar (`ChatSidebar.tsx`) shows chat sessions only. Do not replace it with Figma's multi-section sidebar (Modelli, Scadenze, Normative, Aggiornamenti, FAQ links).
- **Input modes:** We have a single chat input mode. Do not add Figma's input mode switcher (simple/complex/interactive/document).
- **Notifications:** The notification dropdown (Screen 6) is a separate task (DEV-384/385). Do not add it when implementing other screens.
- **Message rendering:** Do not change AIMessageV2, FeedbackButtons, or InteractiveQuestionInline unless the task specifically requires it. **Note:** FeedbackButtons (`web/src/app/chat/components/FeedbackButtons.tsx`) is already implemented with its own design (thumbs up/down + copy button) and must NOT be restyled to match Figma's ChatPage.tsx feedback UI.
- **State management:** Keep existing Context API patterns (ChatStateProvider, ChatSessionsProvider). Do not introduce new providers from Figma.

### User Menu in ChatHeader

New PRATIKO_2.0 pages add their menu item to the existing user menu dropdown in `web/src/app/chat/components/ChatHeader.tsx`. Each task adds its item progressively when its page is implemented. The target layout:

```
┌──────────────────────┐
│  Clienti             │  (DEV-308, Users icon, /clients)
│  Comunicazioni       │  (DEV-330, Mail icon, /comunicazioni)
│  Procedure           │  (DEV-340, ClipboardList icon, /procedure)
│  Dashboard           │  (DEV-354, BarChart3 icon, /dashboard)
│  Scadenze Fiscali    │  (DEV-385, Calendar icon, /scadenze)
│ ──────────────────── │
│  Il mio Account      │  (existing)
│  [superuser items]   │  (existing — Etichettatura, Confronta Modelli, Configurazione)
│ ──────────────────── │
│  Esci                │  (existing)
└──────────────────────┘
```

Each menu item is added ONLY when its corresponding page/route is created. Do not add menu items for pages that don't exist yet.

---

## Appendix: Figma Make Prompts for Missing Screens

All screens have been implemented in the [Figma Make project](https://www.figma.com/make/zeerNWSwapo0VxhMEc6DWx/PratikoAI-Landing-Page). Screen 5 was removed (contradicted FR-008 GDPR temp-only policy). The `ChatPage.tsx` reference is a full standalone prototype — see [ChatPage Integration Guidelines](#chatpage-integration-guidelines) for what to use and what to ignore from it.

### Screen 1: Communication Dashboard (`GestioneComunicazioniPage.tsx`) ✅ IMPLEMENTED

**Used by:** DEV-330, DEV-332, DEV-335, DEV-336, DEV-338

**Source:** [`docs/figma-make-references/GestioneComunicazioniPage.tsx`](../figma-make-references/GestioneComunicazioniPage.tsx)

**Key UI Elements:** Stats bar (Bozze/In Revisione/Approvate/Inviate), filter tabs, communication list with status-based action buttons, bulk select/approve/send, editor modal (client/template/channel/subject/body).

---

### Screen 2: Procedura Interattiva (`ProceduraInterattivaPage.tsx`) ✅ IMPLEMENTED

**Used by:** DEV-340, DEV-342, DEV-343, DEV-344

**Source:** [`docs/figma-make-references/ProceduraInterattivaPage.tsx`](../figma-make-references/ProceduraInterattivaPage.tsx)

**Key UI Elements:** Left sidebar with procedure list (progress bars, category badges), stepper with step numbers/checkmarks, current step content (checklist, required documents, notes/attachments), two modes (Modalità consultazione vs client-specific tracking with "Avvia per un cliente" button), client selector modal.

---

### Screen 3: ROI Dashboard & Analytics (`DashboardPage.tsx`) ✅ IMPLEMENTED

**Used by:** DEV-354, DEV-355, DEV-356, DEV-434 (distributions), DEV-435 (matching stats), DEV-436 (period selector)

**Source:** [`docs/figma-make-references/DashboardPage.tsx`](../figma-make-references/DashboardPage.tsx)

**Key UI Elements:** Top row KPI cards (Clienti Attivi, Ore Risparmiate, Comunicazioni Inviate, Normative Monitorate), ROI "Valore Generato" area chart with savings breakdown, matching stats panel, activity timeline, upcoming deadlines (next 7 days), client distribution charts (pie by regime fiscale, bar by ATECO sector, donut by status).

---

### Screen 4: Matching Results Panel (`MatchingNormativoPage.tsx` + `RisultatiMatchingNormativoPanel.tsx`) ✅ IMPLEMENTED

**Used by:** DEV-326

**Source:** [`docs/figma-make-references/MatchingNormativoPage.tsx`](../figma-make-references/MatchingNormativoPage.tsx) (page wrapper), [`docs/figma-make-references/RisultatiMatchingNormativoPanel.tsx`](../figma-make-references/RisultatiMatchingNormativoPanel.tsx) (panel)

**Key UI Elements:** Header with client name and match count badge, search bar with collapsible filters (type: NORMATIVA/SCADENZA/OPPORTUNITA, urgency: Critica/Alta/Media/Informativa, status), expandable match cards with color-coded urgency borders, circular relevance score indicator (%), matched attributes badges, deadline countdown, source links, bulk actions bar (Genera Comunicazione, Segna come Gestito, Ignora), select-all checkbox, embeddable mode support.

---

### ~~Screen 5: Client Documents Tab (`ClientDocumentsTab.tsx`)~~ REMOVED

> **Removed:** This screen described a persistent "Documenti Cliente" file cabinet with drag & drop upload, document list per client, fiscal year association, and download/preview. This contradicts FR-008's explicit GDPR policy: documents are **temporary only** (session-scoped, 48h max, no persistence, no server-side storage). Document upload for AI analysis is already handled via the chat interface. DEV-362 and DEV-364 (which referenced this screen) have also been removed.

---

### Screen 6: Notification Panel (`NotificationsDropdown.tsx`) ✅ IMPLEMENTED

**Used by:** DEV-384, DEV-385, DEV-422 to DEV-427, DEV-440

**Source:** [`docs/figma-make-references/NotificationsDropdown.tsx`](../figma-make-references/NotificationsDropdown.tsx)

**Key UI Elements:** Bell icon dropdown (entry point in ChatPage), gradient header with unread count badge, notifications grouped by Oggi/Ieri/Questa Settimana, four notification types color-coded (Scadenza Imminente red, Nuovo Match orange, Comunicazione Approvata green, Aggiornamento Normativo blue), mark-as-read per item + "Segna tutte come lette" bulk action, "Vedi tutte le notifiche" footer link, empty state.

---

### Screen 7: Slash Command Procedure Selector (`ProcedureSelector.tsx`) ✅ IMPLEMENTED

**Used by:** DEV-402

**Source:** [`docs/figma-make-references/ProcedureSelector.tsx`](../figma-make-references/ProcedureSelector.tsx)

**Key UI Elements:** CommandPopover (Slack/Notion-style `/` command list, triggered in chat input), inline ProcedureSelector card with search bar + category chips (Tutte/Apertura/Chiusura/Lavoro/Fiscale), scrollable procedure cards (name, category badge, step count, estimated time), read-only detail view (step list with numbered circles, documents grid, stats cards), "Modalità consultazione" badge, "Avvia per un cliente" CTA button. 6 mock procedures covering apertura/chiusura/lavoro/fiscale categories.

---

### Screen 8: Client Mention Autocomplete (`ClientMentionAutocomplete.tsx` + `ClientActionPicker.tsx`) ✅ IMPLEMENTED

**Used by:** DEV-403, DEV-428 (INPS/INAIL fields), DEV-429 (procedure suggestions)

**Source:** [`docs/figma-make-references/ClientMentionAutocomplete.tsx`](../figma-make-references/ClientMentionAutocomplete.tsx) (autocomplete dropdown + mention pill + context card), [`docs/figma-make-references/ClientActionPicker.tsx`](../figma-make-references/ClientActionPicker.tsx) (action picker + client profile card), [`docs/figma-make-references/ChatPage.tsx`](../figma-make-references/ChatPage.tsx) (entry point with mentions integration)

**Key UI Elements:** `@` trigger autocomplete dropdown with search filtering by name/CF, client rows with Building2/User icon + name + codice fiscale + regime badge (Forfettario green/Ordinario blue/Semplificato orange), same-name disambiguation via CF prefix, keyboard nav hint footer. Blue pill `ClientMentionPill` tag in chat input with `@Name` and X remove button. `ClientActionPicker` 2x2 grid card (Domanda generica, Domanda sul cliente, Scheda cliente, Avvia procedura) with gradient header showing client name/regime/posizione. `ClientProfileCard` full detail view with sections: Anagrafica (nome, CF, P.IVA), Regime Fiscale (badge + law reference), Codice ATECO (code + description), Posizione Contributiva (INPS matricola + INAIL PAT), Procedure Attive (progress bars), Procedure Suggerite (hover-to-reveal PlayCircle). `ClientContextCard` compact version for AI response context. Empty state: "Importa i tuoi clienti per usare le menzioni @". 8 mock clients with full Italian fiscal data.

> **ChatPage.tsx usage note:** Only use `ChatPage.tsx` for the `@mention` interaction pattern (how typing `@` triggers the autocomplete, how client selection shows the action picker, how actions route to different flows). Do NOT implement ChatPage.tsx's sidebar navigation, notification dropdown, input mode switcher, or any other features unrelated to the @mention system. See [ChatPage Integration Guidelines](#chatpage-integration-guidelines) above.
