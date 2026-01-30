# PratikoAI v1.8 - Autonomous Workflow Engine Tasks

**Version:** 1.8
**Date:** January 2026
**Status:** NOT STARTED
**Total Effort:** ~29h (4 weeks at 2h/day with Claude Code)
**Architecture:** ADR-024

---

## Overview

PratikoAI 1.8 transforms the platform from a proactive assistant to an **autonomous workflow engine** with:
- Desktop application (Kotlin Multiplatform + Compose)
- Project-based organization with folder sync
- 4 core workflows: Dichiarazione Redditi, Adempimenti Periodici, Apertura/Chiusura, Pensionamento
- Human-in-the-loop checkpoints
- GDPR-compliant EU data processing

**Reference Documents:**
- `docs/architecture/decisions/ADR-024-workflow-automation-architecture.md`
- `docs/tasks/PRATIKO_1.8_REFERENCE.md`

---

## Architecture: Chat + coPratiko (like Claude Desktop)

**Reference Model:** Claude Desktop has tabs: `Chat | Cowork | Code`

**PratikoAI Desktop will have:**
```
┌─────────────────────────────────────────────────┐
│  [Chat]  [coPratiko]                            │
├─────────────────────────────────────────────────┤
│                                                 │
│  Chat tab: Proactive Assistant (from 1.5)       │
│  - Q&A with suggested actions                   │
│  - Interactive questions                        │
│  - Document analysis                            │
│                                                 │
│  coPratiko tab: Autonomous Workflows (new 1.8)  │
│  - Projects with folder sync                    │
│  - Workflow execution                           │
│  - Checkpoints & approvals                      │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Web App:**
- Chat (proactive assistant) - existing, unchanged
- Projects section (workflow management) - new addition

**Key Point:** 1.8 ADDS coPratiko alongside existing chat, doesn't replace it. The existing Chat functionality from v1.5 remains fully functional and accessible via its own tab.

---

## Project Locations

| Project | Path | Status |
|---------|------|--------|
| **Backend** | `/Users/micky/PycharmProjects/PratikoAi-BE` | Existing FastAPI |
| **Frontend** | `/Users/micky/WebstormProjects/PratikoAiWebApp` | Existing Next.js 15 |
| **Desktop** | `/Users/micky/AndroidStudioProjects/PratikoAi-KMP` | Existing KMP project |

---

## Executive Summary

| Component | Tasks | Effort |
|-----------|-------|--------|
| Backend | 7 | ~16h |
| Desktop (KMP) | 4 | ~8h |
| Frontend | 3 | ~5h |
| **TOTAL** | **14** | **~29h** |

**Critical Path:** Backend Foundation → Desktop API → First Workflow → Frontend

---

## Task ID Mapping

| Task Range | Phase |
|------------|-------|
| DEV-260 to DEV-266 | Backend |
| DEV-280 to DEV-283 | Desktop (KMP) |
| DEV-300 to DEV-302 | Frontend (Next.js) |

---

## Phase 1: Backend (~16h)

---

### DEV-260: Workflow Data Layer

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** CRITICAL | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The workflow automation feature requires persistent storage for Projects, Documents, Tasks, and Audit logs. No database models or YAML configuration infrastructure exists.

**Solution:**
Create SQLModel models for workflow entities, Alembic migration with proper indexes, YAML workflow definitions, and a WorkflowTemplateLoader service.

**Agent Assignment:** @ezio (primary), @clelia (tests), @primo (migration review)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-261, DEV-262, DEV-280, DEV-300

**Change Classification:** ADDITIVE

**Error Handling:**
- Invalid YAML: Log error with file path, raise `WorkflowTemplateError("Template non valido: {path}")`
- Missing required field: Log error, raise `WorkflowTemplateError("Campo richiesto mancante: {field}")`
- **Logging:** All errors MUST be logged with context (workflow_type, template_path) at ERROR level

**Performance Requirements:**
- YAML template loading: <50ms per file
- Database queries: <10ms (indexed)

**Edge Cases:**
- **Nulls/Empty:** Empty project name → validation error; null user_id → FK constraint error
- **Boundaries:** Project name max 200 chars; workflow_type enum validation
- **Validation:** Invalid workflow_type → enum validation error
- **Soft Delete:** ProjectStatus.DELETED filters from default queries
- **Tenant Isolation:** user_id required on all queries (future: studio_id)

**Files:**
- `app/models/workflow.py` - SQLModel models
- `alembic/versions/20260130_add_workflow_tables.py` - Migration
- `config/workflow_definitions/dichiarazione_redditi.yaml`
- `config/workflow_definitions/adempimenti_periodici.yaml`
- `config/workflow_definitions/apertura_chiusura.yaml`
- `config/workflow_definitions/pensionamento.yaml`
- `app/services/workflow/__init__.py` - Package init
- `app/services/workflow/workflow_template_loader.py` - Template service

**Fields/Methods/Components:**

**Enums:**
- `WorkflowType(str, Enum)` - dichiarazione_redditi, adempimenti_periodici, apertura_chiusura, pensionamento
- `ProjectStatus(str, Enum)` - active, archived, deleted
- `WorkflowStatus(str, Enum)` - pending, running, paused, waiting_approval, completed, failed, cancelled
- `SyncStatus(str, Enum)` - synced, pending_upload, pending_download, conflict, error
- `SupervisionMode(str, Enum)` - full_supervision, approval_required, confidence_based, review_checkpoints
- `CheckpointType(str, Enum)` - document_validation, calculation_review, data_confirmation, final_review, submission_approval
- `CheckpointStatus(str, Enum)` - pending, approved, rejected, skipped

**Models:**
- `Project(BaseModel, table=True)` - id (UUID), name, user_id, workflow_type, client_id, status, settings (JSONB), created_at, updated_at
- `ProjectDocument(BaseModel, table=True)` - id (UUID), project_id (FK), filename, cloud_path, local_path, sync_status, checksum, document_type, file_size, mime_type
- `WorkflowTask(BaseModel, table=True)` - id (UUID), project_id (FK), workflow_definition_id, status, current_step, state (JSONB), checkpoints (JSONB), supervision_mode, started_at, completed_at
- `WorkflowAuditLog(BaseModel, table=True)` - id (UUID), workflow_task_id (FK), action, actor_type, actor_id, details (JSONB), created_at

**Service:**
- `WorkflowTemplateLoader.load(workflow_type: WorkflowType) -> dict` - Load and validate YAML template
- `WorkflowTemplateLoader.list_templates() -> list[WorkflowType]` - List available templates
- `WorkflowTemplateLoader.validate(template: dict) -> bool` - Validate template structure

**Testing Requirements:**
- **TDD:** Write `tests/models/test_workflow_models.py` FIRST
- **Unit Tests:**
  - `test_workflow_type_values` - Enum values match ADR-024
  - `test_project_creation_minimal` - Create with required fields only
  - `test_project_creation_full` - Create with all fields
  - `test_project_default_values` - Verify defaults (status=active, settings={})
  - `test_document_creation` - ProjectDocument creation and defaults
  - `test_workflow_task_creation` - WorkflowTask creation and defaults
  - `test_audit_log_creation_system` - System actor audit log
  - `test_audit_log_creation_user` - User actor audit log
- **Edge Case Tests:**
  - `test_project_empty_name` - Empty name validation
  - `test_invalid_workflow_type` - Invalid enum value
  - `test_audit_log_gdpr_fields` - GDPR required fields present
- **Integration Tests:** `tests/models/test_workflow_models_integration.py` - DB relationships
- **Regression Tests:** Run `pytest tests/models/` to verify no conflicts
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| YAML schema drift | MEDIUM | JSON Schema validation for templates |
| Migration conflicts | HIGH | Run `alembic check` before merge |
| Missing indexes | MEDIUM | Performance testing with realistic data |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Code Completeness:** (MANDATORY - NO EXCEPTIONS)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All integrations complete and functional
- [ ] All conditional logic paths tested and working
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All enum values match ADR-024 specification
- [ ] Migration runs without errors (`alembic upgrade head`)
- [ ] Migration rolls back cleanly (`alembic downgrade -1`)
- [ ] YAML templates load successfully
- [ ] Template validation catches malformed YAML
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass (regression)
- [ ] No TODO/FIXME comments in committed code

---

### DEV-261: Workflow Engine Core

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Workflows need an execution engine with human-in-the-loop checkpoints, audit logging for GDPR compliance, and real-time progress updates via SSE.

**Solution:**
Create CheckpointManager (4 supervision modes), WorkflowExecutor (LangGraph + AsyncPostgresSaver), and WorkflowAuditLogger with SSE event emission.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-260
- **Unlocks:** DEV-262, DEV-263, DEV-264, DEV-266

**Change Classification:** ADDITIVE

**Error Handling:**
- Checkpoint timeout: Log with workflow_id, return `CheckpointResult(status=TIMEOUT)`
- Workflow execution error: Log full state, emit SSE error event, set status=FAILED
- State persistence error: Log, retry 3x, then fail workflow
- **Logging:** All errors MUST be logged with context (workflow_id, step, user_id) at ERROR level

**Performance Requirements:**
- Checkpoint creation: <100ms
- State persistence: <50ms
- SSE event emission: <10ms

**Edge Cases:**
- **Nulls/Empty:** Empty state dict → initialize with defaults
- **Boundaries:** Max 100 checkpoints per workflow; checkpoint timeout 24h
- **Concurrency:** Only one active workflow per project; advisory lock on workflow
- **Validation:** Invalid supervision mode → default to FULL_SUPERVISION
- **Error Recovery:** Failed step → retry with exponential backoff (3 attempts)

**Files:**
- `app/services/workflow/checkpoint_manager.py` - Checkpoint handling
- `app/services/workflow/workflow_executor.py` - LangGraph executor
- `app/services/workflow/audit_logger.py` - GDPR audit logging
- `tests/services/workflow/test_checkpoint_manager.py`
- `tests/services/workflow/test_workflow_executor.py`
- `tests/services/workflow/test_audit_logger.py`

**Fields/Methods/Components:**

**CheckpointManager:**
- `create_checkpoint(task_id, checkpoint_type, data) -> Checkpoint` - Create pending checkpoint
- `approve_checkpoint(checkpoint_id, user_id, comment) -> bool` - Approve with audit
- `reject_checkpoint(checkpoint_id, user_id, reason) -> bool` - Reject with audit
- `should_pause(task, checkpoint_type) -> bool` - Check supervision mode
- `get_pending_checkpoints(task_id) -> list[Checkpoint]` - List pending

**WorkflowExecutor:**
- `start_workflow(project_id, workflow_type) -> WorkflowTask` - Initialize and start
- `resume_workflow(task_id) -> WorkflowTask` - Resume from checkpoint
- `cancel_workflow(task_id, reason) -> bool` - Cancel with audit
- `get_workflow_state(task_id) -> dict` - Current state

**WorkflowAuditLogger:**
- `log_action(task_id, action, actor_type, actor_id, details) -> WorkflowAuditLog`
- `get_audit_trail(task_id) -> list[WorkflowAuditLog]`

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_checkpoint_creation` - Create checkpoint with all types
  - `test_checkpoint_approval` - Approve with audit log
  - `test_checkpoint_rejection` - Reject with audit log
  - `test_supervision_modes` - All 4 modes behavior
  - `test_workflow_start` - Start workflow correctly
  - `test_workflow_resume` - Resume from checkpoint
  - `test_audit_log_creation` - GDPR fields present
- **Edge Case Tests:**
  - `test_concurrent_workflow_prevention` - Only one active per project
  - `test_checkpoint_timeout` - Timeout handling
  - `test_workflow_error_recovery` - Retry behavior
- **Integration Tests:** `tests/services/workflow/test_workflow_executor_integration.py`
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| LangGraph state corruption | HIGH | Checkpointing with AsyncPostgresSaver |
| SSE connection drops | MEDIUM | Client reconnection with last event ID |
| Concurrent modifications | HIGH | Advisory locks on workflow |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All integrations complete and functional
- [ ] All conditional logic paths tested and working
- [ ] No "will implement later" patterns

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All 4 supervision modes work correctly
- [ ] Checkpoints pause workflow as expected
- [ ] Audit log captures all GDPR-required fields
- [ ] SSE events emit correctly
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass

---

### DEV-262: Projects & Workflows API

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Frontend and desktop apps need REST API endpoints for Projects CRUD, Workflow control, and Sync operations.

**Solution:**
Create FastAPI routers for Projects, Workflows, and Sync with proper authentication, validation, and SSE streaming.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-260, DEV-261
- **Unlocks:** DEV-280, DEV-300

**Change Classification:** ADDITIVE

**Error Handling:**
- Project not found: HTTP 404, `"Progetto non trovato"`
- Workflow already running: HTTP 409, `"Workflow già in esecuzione"`
- Invalid workflow type: HTTP 400, `"Tipo workflow non valido"`
- Document upload failed: HTTP 500, `"Errore caricamento documento"`
- Unauthorized: HTTP 401, `"Non autorizzato"`
- **Logging:** All errors MUST be logged with context (user_id, project_id, operation)

**Performance Requirements:**
- GET /projects: <50ms
- POST /projects: <100ms
- GET /workflows/{id}/status: <20ms
- SSE /workflows/{id}/events: <10ms latency

**Edge Cases:**
- **Nulls/Empty:** Empty project list → return []
- **Boundaries:** Max 100 projects per user; max 50 documents per project
- **Concurrency:** Optimistic locking on project updates
- **Validation:** Invalid UUID → HTTP 400
- **Tenant Isolation:** user_id filter on all queries

**Files:**
- `app/api/v1/projects.py` - Projects CRUD
- `app/api/v1/workflows.py` - Workflow control
- `app/api/v1/sync.py` - Document sync
- `tests/api/test_projects.py`
- `tests/api/test_workflows.py`
- `tests/api/test_sync.py`

**Fields/Methods/Components:**

**Projects API:**
- `GET /projects` - List user's projects
- `POST /projects` - Create project
- `GET /projects/{id}` - Get project details
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Soft delete project
- `POST /projects/{id}/documents` - Upload document
- `DELETE /projects/{id}/documents/{doc_id}` - Remove document

**Workflows API:**
- `POST /workflows/start` - Start workflow for project
- `GET /workflows/{id}/status` - Get workflow status
- `POST /workflows/{id}/checkpoint/{checkpoint_id}/approve` - Approve checkpoint
- `POST /workflows/{id}/checkpoint/{checkpoint_id}/reject` - Reject checkpoint
- `POST /workflows/{id}/cancel` - Cancel workflow
- `GET /workflows/{id}/events` - SSE stream for real-time updates

**Sync API:**
- `POST /sync/upload` - Upload document
- `GET /sync/download/{doc_id}` - Download document
- `GET /sync/changes` - List changes since timestamp
- `POST /sync/resolve-conflict` - Resolve sync conflict

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_create_project` - Create with valid data
  - `test_list_projects` - List user's projects only
  - `test_start_workflow` - Start workflow successfully
  - `test_approve_checkpoint` - Approve with audit
  - `test_upload_document` - Upload and store
- **Edge Case Tests:**
  - `test_project_not_found` - 404 response
  - `test_workflow_already_running` - 409 response
  - `test_unauthorized_access` - 401 response
  - `test_cross_user_isolation` - Cannot access other user's projects
- **Integration Tests:** `tests/api/test_projects_integration.py`
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| SSE connection management | MEDIUM | Connection pooling, heartbeat |
| Large file uploads | MEDIUM | Streaming upload, size limits |
| Cross-user data leakage | CRITICAL | user_id filter on all queries |

**Code Structure:**
- Max function: 50 lines
- API handlers: <30 lines, delegate to services

**Code Completeness:** (MANDATORY)
- [ ] No TODO comments for required functionality
- [ ] All endpoints fully functional
- [ ] Authentication required on all endpoints
- [ ] Proper error responses

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All CRUD operations work
- [ ] SSE streaming works for workflow events
- [ ] Document upload/download works
- [ ] Proper HTTP status codes
- [ ] 80%+ test coverage achieved
- [ ] All existing tests still pass

---

### DEV-263: Dichiarazione Redditi 730 Workflow

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
The primary use case for workflow automation is the 730/Redditi PF declaration. Need complete workflow with IRPEF calculation and detrazioni engine.

**Solution:**
Implement 6-step workflow with IRPEF 2025 calculator (scaglioni), detrazioni calculator (lavoro dipendente, familiari, spese mediche, mutuo), and checkpoint integration.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-261
- **Unlocks:** DEV-265

**Change Classification:** ADDITIVE

**Error Handling:**
- Missing required document: Log, return `WorkflowStepResult(needs_document=True)`
- Invalid CU data: Log validation errors, pause at checkpoint
- Calculation error: Log full state, pause for manual review
- **Logging:** All errors MUST be logged with context (workflow_id, step, field)

**Performance Requirements:**
- IRPEF calculation: <100ms
- Detrazioni calculation: <100ms
- Full workflow step: <500ms

**Edge Cases:**
- **Nulls/Empty:** Missing income → 0 tax; missing detrazioni → skip
- **Boundaries:** Income >75,000€ → no lavoro dipendente detrazione; max spese mediche 129.11€ franchigia
- **Validation:** Negative income → error; invalid codice fiscale → validation error
- **Calculation Edge Cases:** Rounding to 2 decimals; multiple CUs same employer

**Files:**
- `app/services/workflow/workflows/dichiarazione_redditi.py` - 6-step workflow
- `app/services/workflow/calculators/irpef_calculator.py` - IRPEF 2025
- `app/services/workflow/calculators/detrazioni_calculator.py` - Detrazioni
- `tests/services/workflow/workflows/test_dichiarazione_redditi.py`
- `tests/services/workflow/calculators/test_irpef_calculator.py`
- `tests/services/workflow/calculators/test_detrazioni_calculator.py`

**Fields/Methods/Components:**

**Workflow Steps:**
1. `collect_documents` - Gather CU, spese mediche, mutuo docs
2. `extract_data` - OCR/parse documents
3. `validate_data` - Validate extracted data (CHECKPOINT)
4. `calculate_irpef` - Calculate gross tax (CHECKPOINT)
5. `calculate_detrazioni` - Apply detrazioni (CHECKPOINT)
6. `final_review` - Review final numbers (CHECKPOINT)

**IRPEF Calculator (2025 Scaglioni):**
- `calculate_irpef(reddito_imponibile: Decimal) -> IRPEFResult`
- Scaglioni: 0-28k (23%), 28k-50k (35%), >50k (43%)
- Returns: imposta_lorda, aliquota_media, scaglione_marginale

**Detrazioni Calculator:**
- `calculate_detrazioni_lavoro_dipendente(reddito: Decimal, giorni: int) -> Decimal`
- `calculate_detrazioni_familiari(familiari: list[Familiare]) -> Decimal`
- `calculate_detrazioni_spese_mediche(spese: Decimal) -> Decimal` (19% over 129.11€)
- `calculate_detrazioni_mutuo(interessi: Decimal) -> Decimal` (19% max 4000€)

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_irpef_scaglione_1` - Income < 28k
  - `test_irpef_scaglione_2` - Income 28k-50k
  - `test_irpef_scaglione_3` - Income > 50k
  - `test_detrazioni_lavoro_dipendente` - Various income levels
  - `test_detrazioni_familiari` - Spouse, children
  - `test_detrazioni_spese_mediche` - Above/below franchigia
  - `test_detrazioni_mutuo` - Max cap
  - `test_workflow_complete` - Full workflow execution
- **Edge Case Tests:**
  - `test_irpef_zero_income` - Zero income handling
  - `test_irpef_boundary_28k` - Exact boundary
  - `test_detrazioni_no_lavoro_over_75k` - No detrazione above threshold
  - `test_spese_mediche_exact_franchigia` - Exactly 129.11€
- **Integration Tests:** `tests/services/workflow/workflows/test_dichiarazione_redditi_integration.py`
- **Coverage Target:** 95%+ for calculators (financial critical)

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Incorrect tax calculation | CRITICAL | Test with known results from AdE |
| Scaglioni changes | MEDIUM | Configurable rates in YAML |
| Rounding errors | HIGH | Use Decimal, test edge cases |

**Code Structure:**
- Calculators: Pure functions, no side effects
- Workflow: Thin wrapper calling calculators

**Code Completeness:** (MANDATORY)
- [ ] All IRPEF scaglioni implemented
- [ ] All detrazione types implemented
- [ ] Checkpoints at correct steps
- [ ] No hardcoded values (configurable)

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] IRPEF calculation matches AdE examples
- [ ] All detrazione types work correctly
- [ ] Workflow pauses at checkpoints
- [ ] 95%+ coverage for calculators
- [ ] All existing tests still pass

---

### DEV-264: Additional Workflows

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** MEDIUM | **Effort:** 2.5h | **Status:** NOT STARTED

**Problem:**
Beyond 730, professionals need F24 (monthly payments), Apertura/Chiusura (business start/end), and Pensionamento (retirement) workflows.

**Solution:**
Implement 3 additional workflows with specific calculators: F24 codici tributo, TFR calculation, pension eligibility rules.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-261
- **Unlocks:** None

**Change Classification:** ADDITIVE

**Error Handling:**
- Invalid codice tributo: Log, return validation error `"Codice tributo non valido"`
- Missing TFR data: Pause at checkpoint for manual input
- Pension eligibility unclear: Flag for expert review
- **Logging:** All errors logged with workflow context

**Performance Requirements:**
- F24 preparation: <200ms
- TFR calculation: <100ms
- Pension eligibility check: <100ms

**Edge Cases:**
- **F24:** Multiple codici tributo; ravvedimento operoso; interessi moratori
- **Apertura/Chiusura:** Activity type determines checklist; SUAP vs single window
- **Pensionamento:** Quota 103; anticipata; vecchiaia; contributi misti

**Files:**
- `app/services/workflow/workflows/adempimenti_periodici.py` - F24, IVA, LIPE
- `app/services/workflow/workflows/apertura_chiusura.py` - Business start/end
- `app/services/workflow/workflows/pensionamento.py` - Retirement
- `app/services/workflow/calculators/tfr_calculator.py`
- `app/services/workflow/calculators/pension_calculator.py`
- `tests/services/workflow/workflows/test_adempimenti_periodici.py`
- `tests/services/workflow/workflows/test_apertura_chiusura.py`
- `tests/services/workflow/workflows/test_pensionamento.py`

**Fields/Methods/Components:**

**F24 Workflow:**
- `prepare_f24(tributi: list[Tributo]) -> F24Data`
- Codici tributo lookup
- Ravvedimento operoso calculation
- Compensazione handling

**Apertura/Chiusura Workflow:**
- `get_checklist(activity_type: ActivityType) -> list[ChecklistItem]`
- Dynamic checklist based on: commercio, artigianato, professionista, società
- SUAP integration requirements
- Camera di Commercio steps

**Pensionamento Workflow:**
- `check_eligibility(contributi: ContributiHistory) -> EligibilityResult`
- `calculate_tfr(rapporto: RapportoLavoro) -> TFRResult`
- Pension types: vecchiaia (67 anni + 20 contrib), anticipata (42+10 M / 41+10 F), quota 103

**TFR Calculator:**
- `calculate_tfr_lordo(retribuzioni: list[Decimal], anni: int) -> Decimal`
- `calculate_rivalutazione(tfr_accantonato: Decimal, anni: int) -> Decimal`
- `calculate_tassazione_separata(tfr: Decimal, anni_lavoro: int) -> Decimal`

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_f24_single_tributo` - Single payment
  - `test_f24_multiple_tributi` - Multiple payments
  - `test_f24_ravvedimento` - Late payment calculation
  - `test_tfr_calculation` - Known TFR examples
  - `test_pension_vecchiaia` - Standard retirement
  - `test_pension_anticipata` - Early retirement
  - `test_pension_quota_103` - Quota 103 rules
  - `test_apertura_commercio` - Commerce checklist
  - `test_chiusura_professionista` - Professional closure
- **Edge Case Tests:**
  - `test_f24_zero_amount` - Zero handling
  - `test_tfr_short_employment` - < 1 year
  - `test_pension_insufficient_contrib` - Not eligible
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Pension rules change | MEDIUM | YAML configuration |
| TFR calculation complexity | HIGH | Test with real examples |
| Codici tributo updates | LOW | Database table for codes |

**Code Completeness:** (MANDATORY)
- [ ] All 3 workflow types implemented
- [ ] TFR calculator complete
- [ ] Pension eligibility rules complete
- [ ] F24 codici tributo mapping

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] F24 workflow generates valid data
- [ ] TFR calculation matches examples
- [ ] Pension eligibility correctly determined
- [ ] Dynamic checklists for apertura/chiusura
- [ ] 80%+ coverage achieved

---

### DEV-265: PDF Document Generator

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Workflows produce documents that need to be presented as properly formatted PDFs (Modello 730, F24, TFR prospetto).

**Solution:**
Create PDF generation service using reportlab with templates for Italian tax forms. Support PDF/A for archiving.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-263
- **Unlocks:** None

**Change Classification:** ADDITIVE

**Error Handling:**
- Invalid data for template: Log, raise `PDFGenerationError("Dati mancanti per generazione PDF")`
- PDF generation failed: Log, raise `PDFGenerationError("Errore generazione PDF")`
- **Logging:** All errors logged with template_type, data_keys

**Performance Requirements:**
- Single page PDF: <500ms
- Multi-page PDF (730): <2s
- PDF/A conversion: +200ms

**Edge Cases:**
- **Nulls/Empty:** Optional fields → blank in PDF
- **Boundaries:** Long text → truncate with ellipsis
- **Validation:** Required fields checked before generation
- **Special Characters:** Italian accents, € symbol

**Files:**
- `app/services/document_generator/pdf_generator.py` - Main service
- `app/services/document_generator/templates/modello_730.py` - 730 template
- `app/services/document_generator/templates/modello_f24.py` - F24 template
- `app/services/document_generator/templates/riepilogo.py` - Summary template
- `app/services/document_generator/templates/prospetto_tfr.py` - TFR template
- `tests/services/document_generator/test_pdf_generator.py`

**Fields/Methods/Components:**

**PDFGenerator:**
- `generate_pdf(template_type: str, data: dict) -> bytes`
- `generate_pdf_a(template_type: str, data: dict) -> bytes` - PDF/A compliant
- `save_pdf(pdf_bytes: bytes, path: str) -> str`

**Templates:**
- `Modello730Template` - Simplified 730 layout (not official AdE form)
- `ModelloF24Template` - F24 with sezioni (erario, regioni, INPS)
- `RiepilogoTemplate` - Calculation summary with breakdown
- `ProspettoTFRTemplate` - TFR calculation details

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_generate_730_pdf` - Valid 730 generation
  - `test_generate_f24_pdf` - Valid F24 generation
  - `test_generate_riepilogo_pdf` - Summary generation
  - `test_generate_tfr_pdf` - TFR prospetto
  - `test_pdf_a_compliance` - PDF/A validation
  - `test_italian_characters` - Accents and symbols
- **Edge Case Tests:**
  - `test_missing_required_field` - Error handling
  - `test_long_text_truncation` - Overflow handling
  - `test_empty_optional_fields` - Blank handling
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| PDF rendering issues | MEDIUM | Visual regression tests |
| Font issues | LOW | Embed fonts in PDF |
| PDF/A compliance | LOW | Use pdfa library |

**Code Completeness:** (MANDATORY)
- [ ] All 4 templates implemented
- [ ] PDF/A support working
- [ ] Italian character support
- [ ] No hardcoded paths

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All templates generate valid PDFs
- [ ] PDFs open correctly in Adobe Reader
- [ ] PDF/A passes validation
- [ ] Italian characters display correctly
- [ ] 80%+ coverage achieved

---

### DEV-266: Integration Adapters + Notifications

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** MEDIUM | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
Workflows need to notify users of checkpoints and completion. Future: integrate with external systems (AdE, INPS).

**Solution:**
Create pluggable adapter pattern for integrations with PrepareOnlyAdapter as default. NotificationService for checkpoint and completion alerts.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-261
- **Unlocks:** None

**Change Classification:** ADDITIVE

**Error Handling:**
- Notification send failed: Log, retry 3x, then store in queue
- Integration API error: Log, fallback to PREPARE_ONLY
- **Logging:** All errors logged with notification_type, recipient

**Performance Requirements:**
- Send notification: <500ms
- Queue notification: <50ms

**Edge Cases:**
- **Nulls/Empty:** No email → skip email notification
- **Concurrency:** Multiple notifications for same event → deduplicate
- **Error Recovery:** Failed notification → retry with backoff

**Files:**
- `app/services/integrations/base_adapter.py` - Abstract interface
- `app/services/integrations/prepare_only_adapter.py` - Default adapter
- `app/services/workflow/notification_service.py` - Notification handling
- `tests/services/integrations/test_adapters.py`
- `tests/services/workflow/test_notification_service.py`

**Fields/Methods/Components:**

**BaseIntegrationAdapter (Abstract):**
- `submit(data: dict) -> SubmissionResult`
- `check_status(submission_id: str) -> StatusResult`
- `get_capabilities() -> list[str]`

**PrepareOnlyAdapter:**
- Always returns `SubmissionResult(status=PREPARED, instructions="Manual submission required")`
- No external API calls

**NotificationService:**
- `notify_checkpoint_pending(task_id, checkpoint, user) -> bool`
- `notify_workflow_complete(task_id, user) -> bool`
- `notify_deadline_approaching(task_id, deadline, user) -> bool`
- Channels: Desktop push, Email fallback

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_prepare_only_adapter` - Returns PREPARED status
  - `test_notification_checkpoint` - Checkpoint notification
  - `test_notification_complete` - Completion notification
  - `test_notification_deadline` - Deadline notification
  - `test_email_fallback` - Email when desktop unavailable
- **Edge Case Tests:**
  - `test_notification_no_email` - Skip gracefully
  - `test_notification_retry` - Retry on failure
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Email deliverability | LOW | Use reliable provider |
| Desktop not connected | LOW | Email fallback |

**Code Completeness:** (MANDATORY)
- [ ] Base adapter interface complete
- [ ] PrepareOnlyAdapter functional
- [ ] All notification types working
- [ ] Email fallback working

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] PrepareOnlyAdapter works correctly
- [ ] Notifications sent successfully
- [ ] Email fallback works
- [ ] 80%+ coverage achieved

---

## Phase 2: Desktop KMP (~8h)

**Location:** `/Users/micky/AndroidStudioProjects/PratikoAi-KMP`

---

### DEV-280: Projects API + Repository

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** CRITICAL | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Desktop app needs API client and repositories for Projects/Workflows to communicate with backend.

**Solution:**
Extend existing Ktor client with Projects/Workflows endpoints. Create data models and repositories following existing patterns.

**Agent Assignment:** @livia (primary - KMP), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-262
- **Unlocks:** DEV-281

**Change Classification:** ADDITIVE

**Error Handling:**
- Network error: Show offline indicator, queue for retry
- 401 Unauthorized: Redirect to login
- 404 Not found: Show "Project not found" message
- 500 Server error: Show generic error, log details

**Performance Requirements:**
- API call latency: <2s (including network)
- Repository cache: <50ms

**Edge Cases:**
- **Nulls/Empty:** Empty project list → show empty state
- **Network:** Offline mode → use cached data
- **Validation:** Invalid UUID → handle gracefully

**Files:**
- `shared/src/commonMain/kotlin/api/ProjectsApi.kt`
- `shared/src/commonMain/kotlin/api/WorkflowsApi.kt`
- `shared/src/commonMain/kotlin/api/SyncApi.kt`
- `shared/src/commonMain/kotlin/models/Project.kt`
- `shared/src/commonMain/kotlin/models/Workflow.kt`
- `shared/src/commonMain/kotlin/repository/ProjectRepository.kt`
- `shared/src/commonMain/kotlin/repository/WorkflowRepository.kt`
- `shared/src/commonTest/kotlin/repository/ProjectRepositoryTest.kt`

**Fields/Methods/Components:**

**Data Models (Kotlin):**
```kotlin
data class Project(
    val id: String,
    val name: String,
    val workflowType: WorkflowType,
    val status: ProjectStatus,
    val documents: List<ProjectDocument>,
    val createdAt: Instant,
    val updatedAt: Instant
)

data class WorkflowTask(
    val id: String,
    val projectId: String,
    val status: WorkflowStatus,
    val currentStep: String?,
    val checkpoints: List<Checkpoint>
)
```

**ProjectsApi:**
- `suspend fun getProjects(): List<Project>`
- `suspend fun getProject(id: String): Project`
- `suspend fun createProject(request: CreateProjectRequest): Project`
- `suspend fun updateProject(id: String, request: UpdateProjectRequest): Project`
- `suspend fun deleteProject(id: String)`

**WorkflowsApi:**
- `suspend fun startWorkflow(projectId: String, type: WorkflowType): WorkflowTask`
- `suspend fun getWorkflowStatus(taskId: String): WorkflowTask`
- `suspend fun approveCheckpoint(taskId: String, checkpointId: String)`
- `suspend fun rejectCheckpoint(taskId: String, checkpointId: String, reason: String)`

**ProjectRepository:**
- `fun getProjects(): Flow<List<Project>>`
- `suspend fun refreshProjects()`
- `suspend fun createProject(name: String, type: WorkflowType): Project`

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_get_projects` - Fetch project list
  - `test_create_project` - Create new project
  - `test_start_workflow` - Start workflow
  - `test_approve_checkpoint` - Approve checkpoint
- **Edge Case Tests:**
  - `test_offline_cache` - Use cached data when offline
  - `test_network_error` - Handle network failures
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Ktor version mismatch | MEDIUM | Use same version as existing |
| Serialization issues | MEDIUM | Test with real API responses |

**Code Completeness:** (MANDATORY)
- [ ] All API endpoints implemented
- [ ] All models match backend
- [ ] Repository pattern implemented
- [ ] Error handling complete

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] API calls work with backend
- [ ] Models serialize/deserialize correctly
- [ ] Repository caching works
- [ ] 80%+ coverage achieved

---

### DEV-281: coPratiko Tab UI + State

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** HIGH | **Effort:** 2.5h | **Status:** NOT STARTED

**Problem:**
Desktop app needs tab-based navigation (Chat | coPratiko) and UI screens for Projects and Workflows, similar to Claude Desktop.

**Solution:**
Add tab bar to MainScreen. Create coPratiko tab with ProjectsListScreen, ProjectDetailScreen, WorkflowProgressView, and CheckpointDialog.

**Agent Assignment:** @livia (primary - KMP/Compose), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-280
- **Unlocks:** DEV-282

**Change Classification:** MODIFYING (MainScreen.kt)

**Impact Analysis:**
- **Primary File:** `desktopApp/src/desktopMain/kotlin/ui/MainScreen.kt`
- **Affected Files:** Navigation state, existing chat UI
- **Related Tests:** UI tests for MainScreen
- **Baseline Command:** Run existing MainScreen tests

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing MainScreen.kt reviewed
- [ ] Chat functionality unchanged

**Error Handling:**
- Empty project list: Show "No projects" empty state
- Workflow error: Show error dialog with retry option
- Checkpoint data invalid: Show validation errors

**Performance Requirements:**
- Screen navigation: <100ms
- List rendering: 60fps
- State updates: <16ms

**Edge Cases:**
- **Nulls/Empty:** No projects → empty state; no documents → empty list
- **Navigation:** Deep link to project → navigate correctly
- **State:** Tab switch → preserve scroll position

**Files:**
- `desktopApp/src/desktopMain/kotlin/ui/MainScreen.kt` (MODIFY - add tab bar)
- `shared/src/commonMain/kotlin/viewmodel/ProjectsViewModel.kt`
- `shared/src/commonMain/kotlin/viewmodel/WorkflowViewModel.kt`
- `desktopApp/src/desktopMain/kotlin/ui/copratiko/ProjectsListScreen.kt`
- `desktopApp/src/desktopMain/kotlin/ui/copratiko/ProjectDetailScreen.kt`
- `desktopApp/src/desktopMain/kotlin/ui/copratiko/WorkflowProgressView.kt`
- `desktopApp/src/desktopMain/kotlin/ui/copratiko/CheckpointDialog.kt`

**Fields/Methods/Components:**

**Tab Structure:**
```kotlin
enum class MainTab {
    Chat,      // Existing proactive assistant
    CoPratiko  // New autonomous workflows
}
```

**MainScreen Changes:**
- Add `TabRow` with Chat and coPratiko tabs
- Route to existing ChatScreen or new ProjectsListScreen

**ProjectsViewModel:**
- `val projects: StateFlow<List<Project>>`
- `val isLoading: StateFlow<Boolean>`
- `fun loadProjects()`
- `fun createProject(name: String, type: WorkflowType)`
- `fun deleteProject(id: String)`

**WorkflowViewModel:**
- `val workflow: StateFlow<WorkflowTask?>`
- `val currentCheckpoint: StateFlow<Checkpoint?>`
- `fun startWorkflow(projectId: String)`
- `fun approveCheckpoint(checkpointId: String)`
- `fun rejectCheckpoint(checkpointId: String, reason: String)`

**UI Screens:**
- `ProjectsListScreen` - Grid of project cards, "New Project" FAB
- `ProjectDetailScreen` - Project info, documents list, workflow status
- `WorkflowProgressView` - Step indicator, current step details
- `CheckpointDialog` - Data review, approve/reject buttons

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_projects_viewmodel_load` - Projects load correctly
  - `test_workflow_viewmodel_start` - Workflow starts
  - `test_tab_navigation` - Tab switching works
- **Edge Case Tests:**
  - `test_empty_projects_state` - Empty state displays
  - `test_workflow_error_handling` - Error dialogs show
- **Regression Tests:** Existing chat functionality unchanged
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing chat | HIGH | Regression tests |
| State management complexity | MEDIUM | Follow existing patterns |

**Code Completeness:** (MANDATORY)
- [ ] Tab navigation working
- [ ] All screens implemented
- [ ] ViewModels with StateFlow
- [ ] Checkpoint dialogs functional

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Tab navigation works
- [ ] Projects list displays
- [ ] Workflow progress shows
- [ ] Checkpoint approval works
- [ ] Existing chat unchanged
- [ ] 80%+ coverage achieved

---

### DEV-282: Folder Sync + Offline

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Desktop users need local folder sync for project documents and offline access capability.

**Solution:**
Implement FileSystemWatcher (jvmMain), SyncManager with upload/download queue, conflict resolution, and offline cache.

**Agent Assignment:** @livia (primary - KMP), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-281
- **Unlocks:** DEV-283

**Change Classification:** ADDITIVE

**Error Handling:**
- File locked: Log, skip file, retry later
- Upload failed: Queue for retry with backoff
- Conflict detected: Show conflict resolution dialog
- Disk full: Show warning, pause sync

**Performance Requirements:**
- File change detection: <1s
- Small file upload: <2s
- Sync status update: <100ms

**Edge Cases:**
- **Concurrency:** Multiple file changes → batch and deduplicate
- **Conflicts:** Same file modified locally and remotely → user choice
- **Large Files:** >100MB → show progress, chunk upload
- **Network:** Offline → queue changes, sync when online

**Files:**
- `shared/src/jvmMain/kotlin/sync/FileSystemWatcher.kt`
- `shared/src/jvmMain/kotlin/sync/SyncManager.kt`
- `shared/src/jvmMain/kotlin/sync/ConflictResolver.kt`
- `shared/src/commonMain/kotlin/sync/OfflineCache.kt`
- `shared/src/commonMain/kotlin/sync/SyncQueue.kt`
- `shared/src/jvmMain/kotlin/sync/NetworkMonitor.kt`

**Fields/Methods/Components:**

**FileSystemWatcher (jvmMain):**
- `fun watch(directory: Path, onChange: (FileEvent) -> Unit)`
- `fun stopWatching()`
- Uses `java.nio.file.WatchService`

**SyncManager:**
- `fun startSync(projectId: String, localPath: Path)`
- `fun stopSync(projectId: String)`
- `fun getSyncStatus(projectId: String): SyncStatus`
- `fun forceSync(projectId: String)`

**ConflictResolver:**
- `fun detectConflict(local: FileVersion, remote: FileVersion): ConflictType?`
- `fun resolveConflict(conflict: Conflict, resolution: Resolution): Result`
- Resolutions: KEEP_LOCAL, KEEP_REMOTE, KEEP_BOTH

**OfflineCache:**
- `suspend fun cacheDocument(docId: String, bytes: ByteArray)`
- `suspend fun getCachedDocument(docId: String): ByteArray?`
- `fun clearCache(projectId: String)`

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_file_watcher_detects_changes` - File changes detected
  - `test_sync_upload_queue` - Files queued for upload
  - `test_conflict_detection` - Conflicts identified
  - `test_offline_cache` - Documents cached correctly
- **Edge Case Tests:**
  - `test_rapid_file_changes` - Debouncing works
  - `test_conflict_resolution` - User choices applied
  - `test_network_reconnection` - Sync resumes
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| File locking issues | MEDIUM | Retry with backoff |
| Data loss on conflict | HIGH | Default to KEEP_BOTH |
| Large file handling | MEDIUM | Chunked uploads |

**Code Completeness:** (MANDATORY)
- [ ] File watcher working
- [ ] Upload/download queue
- [ ] Conflict detection
- [ ] Offline cache

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] File changes sync automatically
- [ ] Conflicts detected and resolved
- [ ] Offline mode works
- [ ] Network reconnection syncs queued changes
- [ ] 80%+ coverage achieved

---

### DEV-283: System Tray + Distribution

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** MEDIUM | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
Desktop app needs system tray integration for background operation and proper macOS distribution (code signing, notarization, DMG).

**Solution:**
Implement system tray icon with context menu, native notifications, and macOS distribution pipeline.

**Agent Assignment:** @livia (primary - KMP), @silvano (CI/CD)

**Dependencies:**
- **Blocking:** DEV-282
- **Unlocks:** None

**Change Classification:** ADDITIVE

**Error Handling:**
- Notification permission denied: Log, skip notifications
- Code signing failed: CI fails with clear error
- Notarization timeout: Retry 3x

**Performance Requirements:**
- System tray icon: <50ms load
- Notification display: <500ms

**Edge Cases:**
- **macOS Permissions:** Notification permission → request on first use
- **Background Mode:** App hidden → tray icon accessible
- **Distribution:** DMG mounting → app installs correctly

**Files:**
- `shared/src/jvmMain/kotlin/platform/SystemTray.kt`
- `shared/src/jvmMain/kotlin/platform/NotificationManager.kt`
- `.github/workflows/desktop-build.yml`
- `scripts/notarize.sh`

**Fields/Methods/Components:**

**SystemTray:**
- `fun show(icon: Image, menu: List<MenuItem>)`
- `fun updateIcon(icon: Image)`
- `fun hide()`
- Menu items: Open App, Sync Status, Quit

**NotificationManager:**
- `fun showCheckpointNotification(checkpoint: Checkpoint)`
- `fun showWorkflowCompleteNotification(workflow: WorkflowTask)`
- `fun showDeadlineNotification(deadline: Instant, message: String)`
- Uses native macOS notifications

**GitHub Actions Workflow:**
```yaml
jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - Build with Gradle
      - Code sign with Developer ID
      - Notarize with Apple
      - Create DMG
      - Upload artifact
```

**Testing Requirements:**
- **Unit Tests:**
  - `test_system_tray_menu` - Menu items work
  - `test_notification_checkpoint` - Notification displays
- **Manual Testing:**
  - DMG installs correctly
  - Code signing verified
  - Notarization passes

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Apple notarization delays | LOW | Async notarization |
| Code signing secrets exposure | HIGH | GitHub secrets |

**Code Completeness:** (MANDATORY)
- [ ] System tray functional
- [ ] Notifications working
- [ ] DMG builds
- [ ] Code signing configured

**Acceptance Criteria:**
- [ ] System tray icon appears
- [ ] Context menu works
- [ ] Notifications display correctly
- [ ] DMG installs on macOS
- [ ] Code signing verified
- [ ] Notarization passes

---

## Phase 3: Frontend Next.js (~5h)

**Location:** `/Users/micky/WebstormProjects/PratikoAiWebApp`

---

### DEV-300: Projects Pages + API

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Web users need to view and manage projects through browser interface with proper API integration.

**Solution:**
Create Projects list and detail pages, extend API client with Projects/Workflows endpoints, create custom hooks.

**Agent Assignment:** @livia (primary - Frontend), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-262
- **Unlocks:** DEV-301

**Change Classification:** ADDITIVE

**Error Handling:**
- API error: Show toast with error message
- 404 Not found: Redirect to projects list
- 401 Unauthorized: Redirect to login
- Network error: Show offline indicator

**Performance Requirements:**
- Page load: <1s
- List rendering: <100ms
- API response: <500ms (backend)

**Edge Cases:**
- **Nulls/Empty:** No projects → empty state with "Create first project" CTA
- **Pagination:** >50 projects → paginate or infinite scroll
- **Deep links:** Direct link to project → load correctly

**Files:**
- `src/app/projects/page.tsx` - Projects list page
- `src/app/projects/[id]/page.tsx` - Project detail page
- `src/lib/api.ts` (EXTEND with projects/workflows)
- `src/lib/hooks/useProjects.ts`
- `src/lib/hooks/useProjectDetail.ts`
- `src/types/project.ts`
- `tests/app/projects/page.test.tsx`

**Fields/Methods/Components:**

**Types (project.ts):**
```typescript
interface Project {
  id: string;
  name: string;
  workflowType: WorkflowType;
  status: ProjectStatus;
  documents: ProjectDocument[];
  createdAt: string;
  updatedAt: string;
}

interface WorkflowTask {
  id: string;
  projectId: string;
  status: WorkflowStatus;
  currentStep: string | null;
  checkpoints: Checkpoint[];
}
```

**API Client Extensions:**
```typescript
// Add to ApiClient class
async getProjects(): Promise<Project[]>
async getProject(id: string): Promise<Project>
async createProject(data: CreateProjectRequest): Promise<Project>
async deleteProject(id: string): Promise<void>
async startWorkflow(projectId: string, type: WorkflowType): Promise<WorkflowTask>
async getWorkflowStatus(taskId: string): Promise<WorkflowTask>
async approveCheckpoint(taskId: string, checkpointId: string): Promise<void>
```

**Hooks:**
- `useProjects()` - List with loading/error states
- `useProjectDetail(id)` - Single project with documents
- `useCreateProject()` - Create mutation

**Pages:**
- `ProjectsPage` - Grid/list of projects, filters, create button
- `ProjectDetailPage` - Project info, documents, workflow status

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_projects_page_renders` - Page renders correctly
  - `test_projects_list_displays` - Projects display
  - `test_create_project_button` - Create button works
  - `test_project_detail_loads` - Detail page loads
- **Edge Case Tests:**
  - `test_empty_state` - No projects message
  - `test_api_error_handling` - Error toast displays
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| API type mismatch | MEDIUM | Shared types with backend |
| State management complexity | LOW | Follow existing patterns |

**Code Completeness:** (MANDATORY)
- [ ] All pages implemented
- [ ] API client extended
- [ ] Hooks working
- [ ] Types defined

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Projects list displays
- [ ] Project creation works
- [ ] Project detail loads
- [ ] Error handling works
- [ ] 80%+ coverage achieved

---

### DEV-301: Workflow Status + Checkpoint UI

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Web users need to see workflow progress in real-time and approve/reject checkpoints.

**Solution:**
Create WorkflowProgress component with SSE for real-time updates, CheckpointApprovalModal, and WorkflowHistory component.

**Agent Assignment:** @livia (primary - Frontend), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-300
- **Unlocks:** DEV-302

**Change Classification:** ADDITIVE

**Error Handling:**
- SSE connection lost: Auto-reconnect with backoff
- Checkpoint approval failed: Show error toast, allow retry
- Invalid checkpoint data: Show validation errors

**Performance Requirements:**
- SSE latency: <100ms
- UI update: <16ms (60fps)
- Modal open: <100ms

**Edge Cases:**
- **SSE:** Connection drop → auto-reconnect; browser tab hidden → pause
- **Checkpoint:** Already approved → show approved state; expired → show expired
- **History:** Long history → paginate; no history → empty state

**Files:**
- `src/components/workflow/WorkflowProgress.tsx`
- `src/components/workflow/CheckpointApprovalModal.tsx`
- `src/components/workflow/WorkflowHistory.tsx`
- `src/lib/hooks/useWorkflowStatus.ts`
- `src/app/projects/[id]/workflow/page.tsx`
- `tests/components/workflow/WorkflowProgress.test.tsx`

**Fields/Methods/Components:**

**WorkflowProgress:**
```tsx
interface WorkflowProgressProps {
  taskId: string;
  onCheckpointPending: (checkpoint: Checkpoint) => void;
}
// Visual step indicator with current step highlighted
// Progress bar showing completion percentage
// Current step details and status
```

**CheckpointApprovalModal:**
```tsx
interface CheckpointApprovalModalProps {
  checkpoint: Checkpoint;
  onApprove: () => void;
  onReject: (reason: string) => void;
  onClose: () => void;
}
// Data review section
// Approve/Reject buttons
// Rejection reason input
```

**WorkflowHistory:**
```tsx
interface WorkflowHistoryProps {
  taskId: string;
}
// Timeline of workflow events
// Audit log entries
// Expandable details
```

**useWorkflowStatus Hook:**
```typescript
function useWorkflowStatus(taskId: string) {
  const [status, setStatus] = useState<WorkflowTask | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // SSE connection management
  // Auto-reconnect on disconnect
  // Cleanup on unmount

  return { status, isConnected, error };
}
```

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_workflow_progress_renders` - Component renders
  - `test_step_indicator` - Steps display correctly
  - `test_checkpoint_modal_approve` - Approve works
  - `test_checkpoint_modal_reject` - Reject with reason
  - `test_workflow_history` - History displays
- **Edge Case Tests:**
  - `test_sse_reconnection` - Reconnects on disconnect
  - `test_checkpoint_expired` - Expired state shows
- **Integration Tests:** SSE with mock server
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| SSE browser support | LOW | Fallback to polling |
| Modal accessibility | MEDIUM | Use Radix Dialog |

**Code Completeness:** (MANDATORY)
- [ ] WorkflowProgress complete
- [ ] CheckpointApprovalModal complete
- [ ] WorkflowHistory complete
- [ ] SSE hook working

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Workflow progress displays correctly
- [ ] SSE updates work in real-time
- [ ] Checkpoint modal opens/closes
- [ ] Approve/reject work
- [ ] History displays
- [ ] 80%+ coverage achieved

---

### DEV-302: Navigation + Session Integration

**Reference:** `docs/tasks/PRATIKO_1.8_REFERENCE.md`, ADR-024

**Priority:** MEDIUM | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
Need to integrate Projects into main navigation and allow linking sessions to projects.

**Solution:**
Update Navigation to include Projects link, add project switcher to ChatHeader, create "Move to Project" action.

**Agent Assignment:** @livia (primary - Frontend), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-301
- **Unlocks:** None

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary Files:** `src/components/features/Navigation.tsx`, `src/app/chat/components/ChatHeader.tsx`
- **Affected Files:** Chat sidebar, session context
- **Related Tests:** Navigation tests, ChatHeader tests
- **Baseline Command:** `npm run test -- Navigation ChatHeader`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing Navigation reviewed
- [ ] Existing ChatHeader reviewed

**Error Handling:**
- Move to project failed: Show toast error
- Invalid project ID: Show "Project not found"

**Performance Requirements:**
- Navigation render: <16ms
- Project switcher: <100ms

**Edge Cases:**
- **No Projects:** Project switcher shows "No projects" option
- **Session Already in Project:** Show current project, allow change
- **Breadcrumbs:** Deep navigation → show full path

**Files:**
- `src/components/features/Navigation.tsx` (MODIFY)
- `src/app/chat/components/ChatHeader.tsx` (MODIFY)
- `src/app/chat/components/ChatSidebar.tsx` (MODIFY)
- `src/components/projects/ProjectBreadcrumbs.tsx`
- `src/components/projects/MoveToProjectDialog.tsx`
- `tests/components/features/Navigation.test.tsx`

**Fields/Methods/Components:**

**Navigation Changes:**
```tsx
// Add Projects link to navigation
<NavLink href="/projects" icon={FolderIcon}>
  Progetti
</NavLink>
```

**ChatHeader Changes:**
```tsx
// Add project indicator/switcher
{currentProject && (
  <ProjectIndicator project={currentProject} onSwitch={openSwitcher} />
)}
```

**ProjectBreadcrumbs:**
```tsx
<Breadcrumb>
  <BreadcrumbItem href="/projects">Progetti</BreadcrumbItem>
  <BreadcrumbItem href={`/projects/${project.id}`}>{project.name}</BreadcrumbItem>
  <BreadcrumbItem>Workflow</BreadcrumbItem>
</Breadcrumb>
```

**MoveToProjectDialog:**
```tsx
// Dialog to move session to a project
// Project selection dropdown
// Confirmation button
```

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_navigation_projects_link` - Link appears
  - `test_project_breadcrumbs` - Breadcrumbs render
  - `test_move_to_project_dialog` - Dialog works
- **Regression Tests:**
  - `test_existing_navigation_unchanged` - Other links work
  - `test_chat_header_unchanged` - Chat still works
- **Coverage Target:** 80%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing navigation | HIGH | Regression tests |
| State management conflicts | MEDIUM | Follow existing patterns |

**Code Completeness:** (MANDATORY)
- [ ] Navigation updated
- [ ] ChatHeader updated
- [ ] Breadcrumbs working
- [ ] Move dialog working

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Projects link in navigation
- [ ] Project indicator in chat
- [ ] Breadcrumbs work correctly
- [ ] Move to project works
- [ ] Existing functionality unchanged
- [ ] 80%+ coverage achieved

---

## Task Dependency Map

```
DEV-260 (Data Layer)
    │
    └── DEV-261 (Engine Core)
            │
            ├── DEV-262 (APIs) ───────────┬──────────────┐
            │       │                     │              │
            │       └── DEV-280 (KMP API) │              │
            │               │             │              │
            │               └── DEV-281 (KMP UI)        │
            │                       │                    │
            │                       └── DEV-282 (Sync)   │
            │                               │            │
            │                               └── DEV-283  │
            │                                            │
            ├── DEV-263 (730 Workflow)                   │
            │       │                                    │
            │       └── DEV-265 (PDF Generator)         │
            │                                            │
            ├── DEV-264 (Other Workflows)               │
            │                                            │
            └── DEV-266 (Integrations)                  │
                                                         │
                    DEV-300 (Frontend Projects) ◄────────┘
                        │
                        └── DEV-301 (Workflow UI)
                                │
                                └── DEV-302 (Navigation)
```

---

## Implementation Order

```
Week 1 (Backend Foundation):
  DEV-260 → DEV-261 → DEV-262

Week 2 (Workflows + Desktop Start):
  DEV-263 → DEV-265
  DEV-280 (parallel)

Week 3 (Desktop UI + Other Workflows):
  DEV-264
  DEV-281 → DEV-282

Week 4 (Frontend + Polish):
  DEV-300 → DEV-301 → DEV-302
  DEV-266, DEV-283
```

---

## Verification

After each task:
1. `uv run pytest` - all tests pass
2. `./scripts/check_code.sh` - pre-commit hooks pass
3. APIs: Test with curl/httpie against local server
4. Desktop: Build and run locally
5. Frontend: `npm run dev` and manual test
