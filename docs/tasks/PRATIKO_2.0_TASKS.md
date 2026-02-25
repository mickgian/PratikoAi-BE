# PratikoAI 2.0 — Implementation Task List

**Task ID Range:** DEV-300 to DEV-421 (120 tasks, DEV-362 and DEV-364 removed)
**Last Updated:** 2026-02-25

Reference documents (must be in repo):
- `docs/tasks/PRATIKO_2.0.md` — Full task specifications, acceptance criteria, testing requirements
- `docs/tasks/PRATIKO_2.0_REFERENCE.md` — Original product requirements (PRD)
- `docs/architecture/decisions/` — Architectural Decision Records (ADRs)
- `CLAUDE.md` — Code guidelines, agent workflow, development standards

---

## Wave 0: Foundation Models (start here — no dependencies)

These are the foundational SQLModel definitions. All subsequent work depends on these models existing.

### DEV-300: Create Studio SQLModel
**Depends on:** Nothing (start here)
**Priority:** CRITICAL | **Effort:** 2-3h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Clelia (tests)

**What to build:** The `Studio` tenant root entity for multi-tenancy. All client data will be isolated by `studio_id`, following the row-level isolation pattern.

**File:** `app/models/studio.py`

**Fields:** `id` (UUID PK), `name` (str), `slug` (str, unique), `settings` (JSONB), `max_clients` (int, default 100), `created_at`, `updated_at`

**Tests:** `tests/models/test_studio.py` — valid creation, slug uniqueness, JSONB settings, max_clients default

**Unlocks:** DEV-301, DEV-304, DEV-306, DEV-308, DEV-315, DEV-324, DEV-380, DEV-394, DEV-307

---

### DEV-301: Create Client SQLModel
**Depends on:** DEV-300 (Studio model for studio_id FK)
**Priority:** CRITICAL | **Effort:** 2-3h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Severino (security review), @Clelia (tests)

**What to build:** The `Client` model with encrypted PII fields (codice fiscale, P.IVA, contact info) using existing `EncryptedTaxID`. Implements soft delete for GDPR compliance.

**File:** `app/models/client.py`

**Fields:** `id` (int PK), `studio_id` (UUID FK), `codice_fiscale` (encrypted), `partita_iva` (encrypted, nullable), `nome` (encrypted), `tipo_cliente` (enum), `email` (encrypted, nullable), `phone` (encrypted, nullable), `indirizzo`, `cap`, `comune`, `provincia`, `stato_cliente` (enum), `data_nascita_titolare`, `note_studio`, `created_at`, `updated_at`, `deleted_at`

**Tests:** `tests/models/test_client.py` — valid creation, CF validation, P.IVA validation, PII encryption, soft delete, studio FK

**Unlocks:** DEV-302, DEV-304, DEV-306, DEV-309, DEV-380, DEV-307

---

### DEV-303: Create MatchingRule SQLModel
**Depends on:** Nothing (standalone model)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Mario (rule definitions), @Clelia (tests)

**What to build:** The `MatchingRule` model with flexible JSONB conditions supporting AND/OR operators and field comparisons. Pre-seed with 10 rules for common scenarios (R001-R010 as defined in REFERENCE FR-003 §3.3.4).

**File:** `app/models/matching_rule.py`

**Fields:** `id` (UUID PK), `name` (str, unique), `description` (text), `rule_type` (enum: NORMATIVA/SCADENZA/OPPORTUNITA), `conditions` (JSONB), `priority` (int 1-100), `is_active` (bool), `valid_from` (date), `valid_to` (date, nullable), `categoria`, `fonte_normativa`

**Tests:** `tests/models/test_matching_rule.py` — valid creation, JSONB conditions, priority ordering, validity dates, enum types

**Unlocks:** DEV-320, DEV-321, DEV-307

---

### DEV-305: Create Procedura SQLModel
**Depends on:** Nothing (standalone model)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Mario (procedura definitions), @Clelia (tests)

**What to build:** The `Procedura` model with JSONB steps array containing checklists, documents, and notes. Supports versioning for procedure updates.

**File:** `app/models/procedura.py`

**Fields:** `id` (UUID PK), `code` (str, unique), `title` (str), `description` (text), `category` (enum: FISCALE/LAVORO/SOCIETARIO/PREVIDENZA), `steps` (JSONB), `estimated_time_minutes` (int), `version` (int), `is_active` (bool), `last_updated` (date)

**Tests:** `tests/models/test_procedura.py` — valid creation, code uniqueness, JSONB steps, category enum, versioning

**Unlocks:** DEV-306, DEV-340, DEV-307

---

### DEV-388: PDF Export Service
**Depends on:** Nothing (independent utility service)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Shared PDF generation service using WeasyPrint or ReportLab. Multiple features need PDF export (procedure, calculations, dashboard reports, communications).

**File:** `app/services/pdf_export_service.py`

**Unlocks:** Procedura export, calculation export, dashboard reports, communication archive

---

### DEV-389: Integrate Hallucination Guard into RAG Pipeline
**Depends on:** Nothing (service already exists at `app/services/hallucination_guard.py`)
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Integrate the existing HallucinationGuard service into the LangGraph pipeline. Created in DEV-245 Phase 2.3 but never connected to production.

**File:** `app/core/langgraph/nodes/step_064__llm_call.py` (modify)

**Unlocks:** Improved response accuracy for legal citations

---

### DEV-390: OCR Integration for Scanned Documents
**Depends on:** Nothing (independent utility service)
**Priority:** MEDIUM | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** OCR service (Tesseract or cloud-based) for extracting text from scanned documents (images, scanned PDFs).

**File:** `app/services/ocr_service.py`

**Unlocks:** DEV-363 enhancement, DEV-392 scanned support

---

### DEV-393: Enhance Regional Tax Configuration System
**Depends on:** Nothing (service already exists at `app/services/regional_tax_service.py` + `app/models/regional_taxes.py`)
**Priority:** MEDIUM | **Effort:** 4h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Primo (DB), @Clelia (tests)

**What to build:** Enhance the existing RegionalTaxService to support PratikoAI 2.0 client-context-aware calculations. Add addizionali IRPEF by comune/regione and IMU aliquote lookup. Service and model files already exist — extend, do not recreate.

**File:** `app/services/regional_tax_service.py` (enhance), `app/models/regional_taxes.py` (enhance)

**Unlocks:** DEV-349, DEV-351, DEV-413 (Regional Data Population)

---

### DEV-395: API Rate Limiting
**Depends on:** Nothing (independent middleware)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (security review), @Clelia (tests)

**What to build:** Rate limiting middleware using Redis with configurable limits per endpoint.

**File:** `app/middleware/rate_limit.py`

**Unlocks:** Production deployment security gate

---

### DEV-396: DPIA Preparation and Documentation
**Depends on:** Nothing
**Priority:** CRITICAL | **Classification:** ADDITIVE
**Agent:** @Severino (primary), @Mario (requirements)

**What to build:** Data Protection Impact Assessment document required before processing client data.

**File:** `docs/compliance/DPIA_PratikoAI.md`

**Unlocks:** DEV-397, DEV-398, DEV-399, DEV-401

**Verification:** DPIA document covers all processing activities, risk assessment, and mitigation measures.

---

## Wave 1: Dependent Models + Foundation Services

These tasks depend on Wave 0 models. Can all run in parallel once their specific model dependencies are met.

### DEV-302: Create ClientProfile SQLModel
**Depends on:** DEV-301 (Client model for client_id FK)
**Priority:** CRITICAL | **Effort:** 2-3h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Ezio (vector support), @Clelia (tests)

**What to build:** `ClientProfile` as a 1:1 extension of `Client` containing business/fiscal metadata and a 1536-dimension vector for semantic matching with HNSW index.

**File:** `app/models/client_profile.py`

**Fields:** `id` (int PK), `client_id` (int 1:1 FK), `codice_ateco_principale` (str XX.XX.XX), `codici_ateco_secondari` (ARRAY), `regime_fiscale` (enum), `ccnl_applicato` (str, nullable), `n_dipendenti` (int), `data_inizio_attivita` (date), `data_cessazione_attivita` (date, nullable), `immobili` (JSONB), `posizione_agenzia_entrate` (enum, nullable), `profile_vector` (Vector 1536)

**Tests:** `tests/models/test_client_profile.py` — creation, 1:1 FK, ATECO format, regime enum, vector dimension

**Unlocks:** DEV-310, DEV-320, DEV-322, DEV-383, DEV-307

---

### DEV-304: Create Communication SQLModel
**Depends on:** DEV-300 (Studio), DEV-301 (Client for client_id FK)
**Priority:** HIGH | **Effort:** 2-3h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Severino (workflow security), @Clelia (tests)

**What to build:** `Communication` model with status workflow (DRAFT → PENDING_REVIEW → APPROVED → REJECTED → SENT → FAILED) and audit fields. Enforce that creator cannot approve their own communications.

**File:** `app/models/communication.py`

**Fields:** `id` (UUID PK), `studio_id` (UUID FK), `client_id` (int FK, nullable for bulk), `subject`, `content`, `channel` (enum: EMAIL/WHATSAPP), `status` (enum workflow), `created_by` (int FK), `approved_by` (int FK, nullable), `approved_at`, `sent_at`, `normativa_riferimento`, `matching_rule_id` (UUID FK, nullable)

**Tests:** `tests/models/test_communication.py` — creation, status enum, channel enum, self-approval constraint, audit fields

**Unlocks:** DEV-330, DEV-307

---

### DEV-306: Create ProceduraProgress SQLModel
**Depends on:** DEV-300 (Studio), DEV-301 (Client), DEV-305 (Procedura)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Clelia (tests)

**What to build:** `ProceduraProgress` model linking user, studio, procedura, and optionally client. Tracks current step and completed steps array for progress resumption.

**File:** `app/models/procedura_progress.py`

**Fields:** `id` (UUID PK), `user_id` (int FK), `studio_id` (UUID FK), `procedura_id` (UUID FK), `client_id` (int FK, nullable), `current_step` (int), `completed_steps` (JSONB), `started_at`, `completed_at` (nullable), `notes` (text, nullable)

**Tests:** `tests/models/test_procedura_progress.py` — creation, FK constraints, JSONB completed_steps, resume, optional client

**Unlocks:** DEV-340, DEV-307

---

### DEV-324: Proactive Suggestion Model
**Depends on:** DEV-300 (Studio model FK), DEV-307 (Migration)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Clelia (tests)

**What to build:** `ProactiveSuggestion` model to store matches found by background matching jobs. Separate from Communications which are for sending to clients.

**File:** `app/models/proactive_suggestion.py`

**Unlocks:** DEV-325, DEV-326

---

### DEV-397: Vendor DPA Execution and Encryption at Rest
**Depends on:** DEV-396 (DPIA should inform security requirements)
**Priority:** CRITICAL | **Classification:** ADDITIVE
**Agent:** @Silvano (primary)

**What to build:** Execute Data Processing Agreements with Hetzner and implement encryption at rest for client data storage.

**Unlocks:** DEV-308 (StudioService — must complete before client data storage), DEV-400

---

### DEV-398: LLM Provider DPA and Transfer Safeguards
**Depends on:** DEV-396 (DPIA should assess transfer risks first)
**Priority:** CRITICAL | **Classification:** ADDITIVE
**Agent:** @Severino (primary), @Ezio (backend integration)

**What to build:** Data Processing Agreements with LLM providers and safeguards for cross-border data transfers.

**Unlocks:** Production LLM calls with client context, DEV-399, DEV-400

---

### DEV-394: Feature Flag Infrastructure
**Depends on:** DEV-300 (Studio model for per-studio flags)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Silvano (deployment), @Clelia (tests)

**What to build:** Feature flag system with studio-level and global flags for safe gradual rollout of all new features.

**File:** `app/services/feature_flag_service.py`

**Unlocks:** Safe gradual rollout of all new features

---

## Wave 2: Alembic Migration (gates all service-layer work)

### DEV-307: Alembic Migration for Phase 0
**Depends on:** DEV-300, DEV-301, DEV-302, DEV-303, DEV-304, DEV-305, DEV-306 (all models from Waves 0-1)
**Priority:** CRITICAL | **Effort:** 3h | **Classification:** RESTRUCTURING
**Agent:** @Primo (primary), @Ezio (review), @Severino (security review)

**What to build:** Single Alembic migration creating ALL Phase 0 tables with HNSW vector index, composite indexes, foreign keys, and constraints.

**File:** `alembic/versions/YYYYMMDD_add_pratikoai_2_0_models.py`

**Performance:** <30s migration time, <1s lock per table, CONCURRENTLY for indexes

**Pre-deployment:** Backup database, test on staging, document rollback procedure

**Tests:** `tests/migrations/test_phase0_migration.py`

**Unlocks:** ALL Phase 1+ service tasks (DEV-308 through DEV-319)

**Important notes:**
- This is a HIGH-RISK migration affecting production
- Must be reversible (downgrade function)
- Test on staging environment first
- HNSW index for `profile_vector` with m=16, ef_construction=64

---

## Wave 3: Core Service Layer (all depend on DEV-307 migration)

These services implement CRUD operations and business logic on top of the models. Can run in parallel.

### DEV-308: StudioService with CRUD
**Depends on:** DEV-300 (Studio model), DEV-307 (Migration)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Service layer to manage Studio lifecycle (create, read, update, deactivate) with slug uniqueness validation and settings management.

**File:** `app/services/studio_service.py`

**Unlocks:** DEV-311 (Studio API), DEV-315 (User-Studio)

---

### DEV-309: ClientService with CRUD
**Depends on:** DEV-301 (Client model), DEV-307 (Migration)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (security review), @Clelia (tests)

**What to build:** Service to manage clients with business rules: 100 client limit per studio, CF/P.IVA validation, PII encryption, tenant isolation.

**File:** `app/services/client_service.py`

**Unlocks:** DEV-312 (Client API), DEV-313 (Import), DEV-314 (Export), DEV-320 (Matching), DEV-317 (GDPR), DEV-345, DEV-403

---

### DEV-310: ClientProfileService
**Depends on:** DEV-302 (ClientProfile model), DEV-309 (ClientService), DEV-307 (Migration)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Profile CRUD with automatic profile vector generation when profile is created/updated.

**File:** `app/services/client_profile_service.py`

**Unlocks:** DEV-312 (combined in API), DEV-322 (Vector Generation)

---

### DEV-321: Pre-configured Matching Rules (10 MVP + 5 extended)
**Depends on:** DEV-304 (MatchingRule model), DEV-307 (Migration)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Mario (primary), @Primo (migration)

**What to build:** Define matching rules and seed via migration. The REFERENCE PRD (FR-003 §3.3.4) specifies **10 MVP rules** (R001-R010: Rottamazione, Resto al Sud, Bonus Assunzioni Under 30, Bonus Donne, Bonus Sud, Obbligo Registratore Cassa, Obbligo POS, DVR Sicurezza, Cedolare Secca, IMU Seconda Casa). Add 5 extended rules for additional coverage (total: 15).

**File:** `app/data/matching_rules.json` + seed migration

**Unlocks:** DEV-320 (NormativeMatchingService)

---

### DEV-330: CommunicationService with Draft/Approve Workflow
**Depends on:** DEV-304 (Communication model), DEV-307 (Migration)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (workflow review), @Clelia (tests)

**What to build:** Service with draft/review/approve/send workflow state machine. State transitions: DRAFT → PENDING_REVIEW → APPROVED → SENT (or REJECTED/FAILED).

**File:** `app/services/communication_service.py`

**Unlocks:** DEV-331, DEV-332, DEV-335, DEV-336, DEV-337, DEV-338, DEV-339

---

### DEV-340: ProceduraService with Progress Tracking
**Depends on:** DEV-305, DEV-306, DEV-307 (Procedura + ProceduraProgress models, Migration)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Service to manage procedure lifecycle including starting, resuming, and completing progress. Tracks current step and completed steps.

**File:** `app/services/procedura_service.py`

**Unlocks:** DEV-341, DEV-342, DEV-343, DEV-344, DEV-345, DEV-346, DEV-347, DEV-402, DEV-403, DEV-404

---

### DEV-380: Deadline SQLModel & Migration
**Depends on:** DEV-300 (Studio), DEV-301 (Client), DEV-307 (Migration infrastructure)
**Priority:** CRITICAL | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Severino (security review), @Clelia (tests)

**What to build:** `Deadline` model to track deadlines from multiple sources (regulatory, tax, client-specific) and `ClientDeadline` for many-to-many with clients.

**File:** `app/models/deadline.py`

**Unlocks:** DEV-381, DEV-382, DEV-383, DEV-384, DEV-385, DEV-387

---

### DEV-322: Client Profile Vector Generation
**Depends on:** DEV-302 (ClientProfile with profile_vector column), DEV-307 (HNSW index migration)
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Embedding service using existing LLM infrastructure. Generates 1536-dim vectors from profile text (regime, ATECO description, etc.) when profile is created/updated.

**File:** `app/services/profile_embedding_service.py`

**Unlocks:** DEV-320 (NormativeMatchingService semantic fallback)

---

### DEV-372: Data Processing Agreement (DPA) Model
**Depends on:** DEV-307 (Migration for new tables)
**Priority:** CRITICAL | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Severino (compliance), @Clelia (tests)

**What to build:** DPA model with version tracking and acceptance records. Required before processing any client data.

**File:** `app/models/dpa.py`

**Unlocks:** DEV-373, DEV-378, DEV-379

---

### DEV-374: Data Breach Notification Model
**Depends on:** DEV-307 (Migration)
**Priority:** CRITICAL | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Severino (compliance), @Clelia (tests)

**What to build:** Breach notification model with status tracking. GDPR requires notification within 72 hours.

**File:** `app/models/breach_notification.py`

**Unlocks:** DEV-375, DEV-378, DEV-379

---

## Wave 4: API Layer + Advanced Services

These depend on Wave 3 services. Can run in parallel within the wave.

### DEV-311: Studio API Endpoints
**Depends on:** DEV-308 (StudioService)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Studio router with CRUD endpoints following existing FastAPI patterns in `app/api/v1/`.

**File:** `app/api/v1/studio.py`

**Unlocks:** DEV-315 (User-Studio), Frontend integration

---

### DEV-312: Client API Endpoints
**Depends on:** DEV-309 (ClientService), DEV-310 (ClientProfileService)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Client router with CRUD endpoints, list with pagination, filtering, and proper error handling for business rules (100 limit, validation).

**File:** `app/api/v1/clients.py`

**Unlocks:** DEV-313 (Import), DEV-314 (Export), Frontend integration

---

### DEV-315: User-Studio Association
**Depends on:** DEV-300 (Studio), DEV-307 (Migration), DEV-308 (StudioService)
**Priority:** HIGH | **Effort:** 2h | **Classification:** MODIFYING
**Agent:** @Primo (primary), @Ezio (migration), @Severino (security)

**What to build:** Add nullable `studio_id` FK to existing `User` model. Migration creates column as nullable. Auto-create studio for existing users.

**File:** `app/models/user.py` (MODIFY)

**Important:** BREAKING CHANGE affecting all existing users. Nullable FK ensures backward compatibility.

**Unlocks:** DEV-316 (Tenant Middleware), all multi-tenant features

---

### DEV-320: NormativeMatchingService
**Depends on:** DEV-302 (ClientProfile), DEV-309 (ClientService), DEV-321 (Matching Rules), DEV-322 (Vector Generation)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Mario (rule logic), @Clelia (tests)

**What to build:** Hybrid matching: first structured (fast, explainable) using rule conditions, then semantic fallback via profile vectors for ambiguous cases. Must complete in <100ms for inline use.

**File:** `app/services/normative_matching_service.py`

**Unlocks:** DEV-323 (LangGraph Node), DEV-325 (Background Job), DEV-328 (Performance Tests), DEV-383

---

### DEV-331: LLM Communication Generation Tool
**Depends on:** DEV-330 (CommunicationService)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** LangGraph tool for generating communication drafts using LLM with regulation and client context.

**File:** `app/core/langgraph/tools/communication_tool.py`

**Unlocks:** DEV-337 (Response Formatter)

---

### DEV-332: Communication API Endpoints
**Depends on:** DEV-330 (CommunicationService)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Communication router with all workflow endpoints: create, review, approve, reject, send.

**File:** `app/api/v1/communications.py`

**Unlocks:** DEV-339 (E2E Tests)

---

### DEV-333: Email Sending Integration
**Depends on:** DEV-330 (CommunicationService)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Email sending service using existing patterns. Handle retries, failures, and status tracking.

**File:** `app/services/email_service.py`

**Unlocks:** DEV-334 (WhatsApp), DEV-384 (Deadline notifications)

---

### DEV-334: WhatsApp wa.me Link Integration
**Depends on:** DEV-330 (CommunicationService)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** WhatsApp service using `wa.me/{phone}?text={message}` links (no API approval needed). Opens WhatsApp with pre-filled message.

**File:** `app/services/whatsapp_service.py`

---

### DEV-335: Bulk Communication Creation
**Depends on:** DEV-330 (CommunicationService)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Bulk creation endpoint that creates draft communications for multiple clients at once.

**File:** `app/services/communication_service.py` (extend)

---

### DEV-336: Communication Templates
**Depends on:** DEV-330 (CommunicationService)
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Template model and service for managing reusable communication templates.

**File:** `app/models/communication_template.py` + `app/services/template_service.py`

---

### DEV-341: 10 Pre-configured Procedure (P001-P010)
**Depends on:** DEV-340 (ProceduraService)
**Priority:** HIGH | **Effort:** 5h | **Classification:** ADDITIVE
**Agent:** @Mario (primary), @Primo (seed migration)

**What to build:** Define all 10 pre-configured procedure from REFERENCE FR-001 §3.1.4 with steps, documents, checklists, and costs. Seed via migration.

**Procedures:** P001 (Apertura attività artigiano), P002 (Apertura attività commerciale), P003 (Apertura studio professionale), P004 (Domanda pensione vecchiaia), P005 (Domanda pensione anticipata), P006 (Assunzione dipendente), P007 (Trasformazione regime fiscale), P008 (Chiusura attività), P009 (Variazione dati azienda), P010 (Iscrizione gestione separata INPS).

**Unlocks:** DEV-402 (/procedura command)

---

### DEV-342: Procedura API Endpoints
**Depends on:** DEV-340 (ProceduraService)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Procedure router with endpoints to list procedure, start progress, and track completion.

**File:** `app/api/v1/procedure.py`

---

### DEV-343: Procedura Step Checklist Tracking
**Depends on:** DEV-340 (ProceduraService)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Extend progress tracking with granular checklist item completion within each step.

**File:** `app/services/procedura_service.py` (extend)

---

### DEV-344: Procedura Notes and Attachments
**Depends on:** DEV-340 (ProceduraService)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Add notes field to ProceduraProgress and document attachment support.

**File:** `app/services/procedura_service.py` (extend)

---

### DEV-345: Procedura Context in Chat
**Depends on:** DEV-340 (ProceduraService), DEV-309 (ClientService)
**Priority:** HIGH | **Effort:** 3h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Add procedura context to RAGState when user has active procedura. When `@NomeCliente` mentioned, inject client profile into RAGState.

**File:** `app/core/langgraph/nodes/` (modify context builder)

**Unlocks:** DEV-403 (@client mentions)

---

### DEV-381: DeadlineService CRUD
**Depends on:** DEV-380 (Deadline model)
**Priority:** CRITICAL | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Primo (DB support), @Clelia (tests)

**What to build:** CRUD operations for deadlines with studio_id isolation and deadline status management.

**File:** `app/services/deadline_service.py`

**Unlocks:** DEV-382, DEV-383, DEV-384, DEV-385, DEV-387

---

### DEV-314: Client Export to Excel
**Depends on:** DEV-309 (ClientService)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (GDPR review), @Clelia (tests)

**What to build:** Export service generating Excel file with all client data (decrypted for export). Required by GDPR data portability.

**File:** `app/services/client_export_service.py`

**Unlocks:** DEV-317 (GDPR Deletion — uses export for portability)

---

### DEV-373: DPA Acceptance Workflow
**Depends on:** DEV-372 (DPA model)
**Priority:** CRITICAL | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**What to build:** DPA service with acceptance workflow and API enforcement. Users must accept DPA before adding clients.

**File:** `app/services/dpa_service.py` + `app/api/v1/dpa.py`

**Unlocks:** DEV-378, DEV-379

---

### DEV-375: Breach Notification Service
**Depends on:** DEV-374 (Breach model)
**Priority:** CRITICAL | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**What to build:** Breach lifecycle management: detection, assessment, notification within 72-hour requirement.

**File:** `app/services/breach_notification_service.py`

**Unlocks:** DEV-378, DEV-379

---

### DEV-376: Processing Register
**Depends on:** DEV-309 (ClientService), existing GDPR infrastructure
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**What to build:** GDPR register of processing activities — what data is processed, why, and legal basis.

**File:** `app/models/processing_register.py` + `app/services/processing_register_service.py`

**Unlocks:** DEV-378, DEV-379

---

### DEV-399: Italian AI Law Garante Notification
**Depends on:** DEV-396 (DPIA), DEV-398 (LLM DPAs — needed to list processors)
**Priority:** HIGH | **Classification:** ADDITIVE
**Agent:** @Mario (primary)

**What to build:** Prepare notification for Italian AI Authority (Garante). Requires 30-day waiting period before public launch.

**Unlocks:** Public launch

---

### DEV-400: Public Sub-Processor List and Privacy Policy
**Depends on:** DEV-397 (Hetzner DPA), DEV-398 (LLM DPAs) — need finalized vendor list
**Priority:** HIGH | **Classification:** ADDITIVE
**Agent:** @Severino (primary), @Mario (business requirements)

**What to build:** Public-facing sub-processor list and updated privacy policy.

**Unlocks:** Public launch

---

### DEV-401: ADR GDPR Client Data Architecture
**Depends on:** DEV-396 (DPIA informs architecture decisions)
**Priority:** MEDIUM | **Classification:** ADDITIVE
**Agent:** @Egidio (primary)

**What to build:** Architectural Decision Record documenting GDPR client data architecture decisions. **Note:** ADR-025 is already taken by "LLM Model Inventory & Tiering" (see `docs/architecture/decisions/ADR-025-llm-model-inventory-and-tiering.md`). Assign next available ADR number.

**File:** `docs/architecture/decisions/ADR-0XX-gdpr-client-data-architecture.md` (use next available number)

---

## Wave 5: Multi-Tenancy + Import/Export + Advanced Matching

These depend on Wave 4 APIs and Wave 3 services.

### DEV-316: Tenant Context Middleware
**Depends on:** DEV-315 (User-Studio Association)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (security review)

**What to build:** Middleware that extracts `studio_id` from JWT and sets it in request state. Services access via dependency injection.

**File:** `app/middleware/tenant_context.py`

**Unlocks:** All multi-tenant service operations

---

### DEV-313: Client Import from Excel/PDF
**Depends on:** DEV-309 (ClientService), DEV-312 (Client API)
**Priority:** HIGH | **Effort:** 6h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Mario (template design), @Clelia (tests)

**What to build:** Import service supporting Excel (openpyxl) and PDF (using existing document parsing). Uses LLM-assisted extraction for non-standard formats.

**File:** `app/services/client_import_service.py`

---

### DEV-317: Client GDPR Deletion
**Depends on:** DEV-309 (ClientService), DEV-314 (Client Export — for data portability before deletion)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (GDPR review), @Clelia (tests)

**What to build:** GDPR erasure service. Soft delete with anonymization, cascade to communications, export data before deletion.

**File:** `app/services/client_gdpr_service.py`

---

### DEV-323: LangGraph Matching Node
**Depends on:** DEV-320 (NormativeMatchingService), DEV-316 (Tenant Middleware for studio_id)
**Priority:** HIGH | **Effort:** 4h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Severino (review), @Clelia (tests)

**What to build:** LangGraph node inserted after domain classification (step 35). Queries client database for matches and adds to RAGState.

**File:** `app/core/langgraph/nodes/client_matching_node.py`

**Important:** Modifies the 134-step LangGraph pipeline. HIGH RISK.

**Unlocks:** DEV-327 (Response Enrichment), DEV-337

---

### DEV-325: Background Matching Job
**Depends on:** DEV-320 (NormativeMatchingService), DEV-324 (ProactiveSuggestion model)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Background job using FastAPI BackgroundTasks. Runs after RSS ingestion to scan all clients for matches.

**File:** `app/jobs/matching_job.py`

**Unlocks:** DEV-326 (Matching API)

---

### DEV-326: Matching API Endpoints
**Depends on:** DEV-325 (Background Matching Job), DEV-324 (ProactiveSuggestion)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Matching router with endpoints for suggestions management: fetch, trigger manual matching, mark as read/dismissed.

**File:** `app/api/v1/matching.py`

---

### DEV-337: Response Formatter with Suggestions
**Depends on:** DEV-323 (LangGraph Node), DEV-330 (CommunicationService)
**Priority:** HIGH | **Effort:** 3h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Modify `response_formatter_node.py` to append proactive suggestions when matched_clients exist in RAGState.

**File:** `app/core/langgraph/nodes/response_formatter_node.py` (modify)

---

### DEV-338: Communication Audit Logging
**Depends on:** DEV-330 (CommunicationService)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**What to build:** Audit logging for all communication actions using existing `SecurityAuditLogger`.

**File:** `app/services/communication_service.py` (extend)

---

### DEV-346: Procedura Completion Analytics
**Depends on:** DEV-340 (ProceduraService)
**Priority:** LOW | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Analytics methods on ProceduraService: how many started, completed, average time.

**File:** `app/services/procedura_service.py` (extend)

---

### DEV-382: Automatic Deadline Extraction from KB
**Depends on:** DEV-381 (DeadlineService), existing KB/RSS ingestion system
**Priority:** HIGH | **Effort:** 6h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Mario (extraction rules), @Clelia (tests)

**What to build:** Service that processes KB items and extracts deadline metadata using LLM + regex patterns.

**File:** `app/services/deadline_extraction_service.py`

**Unlocks:** DEV-383 (Client matching for extracted deadlines)

---

### DEV-383: Client-Deadline Matching Logic
**Depends on:** DEV-381 (DeadlineService), DEV-302 (ClientProfile), DEV-320 (Matching criteria engine)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Primo (query optimization), @Clelia (tests)

**What to build:** Match deadlines to clients using the same criteria engine as normative matching.

**File:** `app/services/deadline_matching_service.py`

**Unlocks:** DEV-384 (Notifications)

---

### DEV-384: Deadline Notification Background Job
**Depends on:** DEV-381 (DeadlineService), DEV-383 (Client-Deadline Matching), DEV-333 (Email sending)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Silvano (background jobs), @Clelia (tests)

**What to build:** Daily background job sending notifications for upcoming deadlines at configurable intervals (30 days, 7 days, 1 day before).

**File:** `app/jobs/deadline_notification_job.py`

---

### DEV-385: Upcoming Deadlines API Endpoint
**Depends on:** DEV-381 (DeadlineService)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Livia (frontend contract), @Clelia (tests)

**What to build:** REST endpoints for deadline management and queries for dashboard and calendar widget.

**File:** `app/api/v2/endpoints/deadlines.py`

**Unlocks:** DEV-386 (Calendar Widget)

---

### DEV-377: Enhanced Client Data Rights
**Depends on:** DEV-309 (ClientService), existing GDPR deletion service
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**What to build:** Client-facing data rights API: access, rectification, erasure, portability.

**File:** `app/api/v1/data_rights.py`

**Unlocks:** DEV-378, DEV-379

---

## Wave 6: Fiscal Calculations + Documents + Dashboard

These depend on Wave 3-5 services. Can run in parallel.

### DEV-348: Client Context Injection for Calculations
**Depends on:** DEV-309 (ClientService), DEV-302 (ClientProfile)
**Priority:** HIGH | **Effort:** 3h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Modify existing calculation tools (IRPEF, INPS, etc.) to accept optional client_id and use profile data.

**File:** `app/core/langgraph/tools/` (modify existing calculation tools)

---

### DEV-349: IRPEF Calculator Enhancement
**Depends on:** DEV-348 (Client Context Injection)
**Priority:** HIGH | **Effort:** 3h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Regime-aware IRPEF calculation (forfettario vs ordinario) with specific deductions.

**File:** `app/services/tax_calculator_service.py` (enhance)

---

### DEV-350: INPS Calculator Enhancement
**Depends on:** DEV-348 (Client Context Injection)
**Priority:** HIGH | **Effort:** 3h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** ATECO-based INPS contribution rates with context-aware calculation.

**File:** `app/services/tax_calculator_service.py` (enhance)

---

### DEV-351: IMU Calculator with Client Property
**Depends on:** DEV-348 (Client Context Injection)
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** IMU calculator using stored client property data (rendita catastale, tipo immobile).

**File:** `app/services/imu_calculator_service.py`

---

### DEV-406: IVA Calculator (Scorporo + Liquidazione)
**Depends on:** DEV-348 (Client Context Injection)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** IVA calculator supporting: (1) scorporo IVA (from gross to net + VAT), (2) IVA liquidation (sales VAT - purchase VAT = balance), (3) forfettario regime coefficient calculation. Required by PRD FR-007 §3.7.3 and MVP scope §6.1 ("Calcoli fiscali base: IRPEF, IVA, contributi").

**Note:** `app/services/italian_tax_calculator.py` already has `calculate_vat()` / `calculate_reverse_vat()` methods. Consolidate or deprecate those in favor of this dedicated service (the existing file is 1300+ lines, well over the 200-line service limit).

**File:** `app/services/iva_calculator_service.py`

**Tests:** `tests/services/test_iva_calculator.py` — scorporo 4%/10%/22%, liquidation positive/negative balance, forfettario coefficient, edge cases (zero amounts, negative values)

**Unlocks:** DEV-353 (Calculation Accuracy Tests)

---

### DEV-407: Ritenuta d'Acconto Calculator
**Depends on:** DEV-348 (Client Context Injection)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Ritenuta d'acconto calculator supporting: (1) professionisti (20% on full amount), (2) agenti/rappresentanti (23% on 50% of commissions), (3) other withholding tax scenarios. Required by PRD FR-007 §3.7.3.

**File:** `app/services/ritenuta_calculator_service.py`

**Tests:** `tests/services/test_ritenuta_calculator.py` — professional 20%, agent 23% on 50%, edge cases

**Unlocks:** DEV-353 (Calculation Accuracy Tests)

---

### DEV-408: Cedolare Secca Calculator
**Depends on:** DEV-348 (Client Context Injection)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Cedolare secca calculator: 21% ordinary rate, 10% reduced rate for agreed-rent contracts (concordati). Required by PRD FR-007 §3.7.3.

**File:** `app/services/cedolare_secca_calculator_service.py`

**Tests:** `tests/services/test_cedolare_secca_calculator.py` — 21% rate, 10% reduced, comparison with ordinary IRPEF

**Unlocks:** DEV-353 (Calculation Accuracy Tests)

---

### DEV-409: TFR Calculator
**Depends on:** DEV-348 (Client Context Injection)
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** TFR (Trattamento Fine Rapporto) calculator: annual accrual = annual retribution / 13.5, revaluation using ISTAT index + 1.5% fixed rate. Required by PRD FR-007 §3.7.3.

**File:** `app/services/tfr_calculator_service.py`

**Tests:** `tests/services/test_tfr_calculator.py` — single year, multi-year accrual, revaluation, partial year

**Unlocks:** DEV-353 (Calculation Accuracy Tests)

---

### DEV-410: Netto in Busta / Costo Azienda Calculator
**Depends on:** DEV-348 (Client Context Injection), DEV-349 (IRPEF), DEV-350 (INPS), DEV-393 (Regional Tax)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Payroll calculator supporting: (1) From RAL → calculate net salary (RAL - INPS employee - IRPEF - addizionali = netto), (2) From RAL → calculate total employer cost (RAL + INPS employer + INAIL + TFR accrual). Required by PRD FR-007 §3.7.3.

**File:** `app/services/payroll_calculator_service.py`

**Tests:** `tests/services/test_payroll_calculator.py` — RAL to net, RAL to employer cost, different CCNL rates, regional variations, family deductions

**Unlocks:** DEV-353 (Calculation Accuracy Tests)

---

### DEV-352: Calculation History Storage
**Depends on:** DEV-348 (Client Context Injection)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Ezio (service), @Clelia (tests)

**What to build:** CalculationHistory model to store calculations for client records and audit.

**File:** `app/models/calculation_history.py` + `app/services/calculation_history_service.py`

---

### DEV-353: Unit Tests for Calculation Accuracy
**Depends on:** DEV-349, DEV-350, DEV-351, DEV-406, DEV-407, DEV-408, DEV-409, DEV-410 (all calculators)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary)

**What to build:** Exhaustive parametrized test suite with known inputs/outputs for ALL calculation scenarios. Must validate against official sources: IRPEF vs AdE simulator (AC-007.1), INPS vs INPS tables (AC-007.4), IVA liquidation, ritenuta d'acconto, cedolare secca, TFR, netto in busta. Include regional variations for 20 cities (AC-007.5).

**File:** `tests/services/test_tax_calculations.py`

---

### DEV-354: ROI Metrics Service
**Depends on:** DEV-309 (ClientService), DEV-330 (CommunicationService), DEV-340 (ProceduraService)
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Metrics service calculating ROI and usage statistics: time saved, communications sent, regulations tracked.

**File:** `app/services/roi_metrics_service.py`

**Unlocks:** DEV-355, DEV-356

---

### DEV-360: Bilancio Document Parser
**Depends on:** Existing document parsing infrastructure
**Priority:** MEDIUM | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Parser for client financial statements (bilanci) extracting key data (fatturato, utile, etc.).

**File:** `app/services/document_parsers/bilancio_parser.py`

---

### DEV-361: CU Document Parser
**Depends on:** Existing document parsing infrastructure
**Priority:** MEDIUM | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Parser for Certificazione Unica documents extracting income and withholding data.

**File:** `app/services/document_parsers/cu_parser.py`

---

### DEV-363: Document Context in Chat
**Depends on:** DEV-360 (Bilancio Parser), existing context_builder_node
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Include client documents in RAGState context when discussing a client.

**File:** `app/core/langgraph/nodes/context_builder_node.py` (modify)

---

### DEV-391: Document Auto-Delete Background Job
**Depends on:** DEV-363 (Document Context) or existing document storage
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (security review), @Clelia (tests)

**What to build:** Background job that deletes uploaded documents after 30 minutes for GDPR data minimization.

**File:** `app/jobs/document_cleanup_job.py`

---

### DEV-392: F24 Document Parser
**Depends on:** DEV-363 (Document Context), optionally DEV-390 (OCR) for scanned F24
**Priority:** MEDIUM | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Mario (F24 structure), @Clelia (tests)

**What to build:** Specialized parser for F24 tax payment documents.

**File:** `app/services/document_parsers/f24_parser.py`

---

### DEV-411: Fattura Elettronica XML Parser
**Depends on:** Existing document parsing infrastructure
**Priority:** HIGH | **Effort:** 5h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Mario (fattura structure), @Clelia (tests)

**What to build:** Parser for Fattura Elettronica XML (SDI format FatturaPA). Extract: fornitore/cliente anagrafica, line items, imponibili per aliquota, IVA split, totale documento, data emissione, numero fattura, ritenuta d'acconto if present. This is the #1 document user story (US-008.1) and is explicitly in MVP scope (§6.1). Must handle both FatturaPA 1.2 schema and FatturaOrdinaria.

**File:** `app/services/document_parsers/fattura_xml_parser.py`

**Tests:** `tests/services/test_fattura_xml_parser.py` — valid FatturaPA XML, multi-line items, split-payment, ritenuta d'acconto, malformed XML, missing fields

**Unlocks:** DEV-363 (Document Context)

---

### DEV-412: Email Open Tracking Service
**Depends on:** DEV-333 (Email Sending Integration)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (GDPR review — requires consent for tracking), @Clelia (tests)

**What to build:** Email open tracking using link-based tracking (not pixel — GDPR safer). Track click-throughs on CTA links. Required by PRD AC-004.13 ("Tracking aperture email funzionante") and dashboard metrics (FR-005 §3.5.3 "Tasso apertura", "Click su CTA"). Must respect `consenso_marketing` and `consenso_profilazione` flags on Client model. Generate tracking URLs via redirect service.

**File:** `app/services/email_tracking_service.py` + `app/api/v1/tracking.py` (redirect endpoint)

**Tests:** `tests/services/test_email_tracking.py` — track open, track click, respect consent flags, no tracking without consent

**Unlocks:** DEV-354 (ROI Metrics — provides open rate data)

---

### DEV-413: Regional Tax Data Population (20 MVP Cities)
**Depends on:** DEV-393 (Regional Tax Configuration System)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Mario (primary — data sourcing from MEF/IFEL), @Primo (seed migration)

**What to build:** Populate regional tax database with data for 20 principal Italian cities as required by PRD AC-007.5 and MVP scope §6.1. Data includes: addizionale regionale IRPEF (all 20 regioni), addizionale comunale IRPEF (20 cities), IMU aliquote per categoria catastale (20 cities).

**Cities (suggested):** Roma, Milano, Napoli, Torino, Palermo, Genova, Bologna, Firenze, Bari, Catania, Venezia, Verona, Messina, Padova, Trieste, Brescia, Parma, Taranto, Modena, Reggio Calabria.

**File:** `app/data/regional_tax_rates.json` + seed migration

**Tests:** `tests/data/test_regional_tax_data.py` — data completeness (all 20 cities), rate ranges valid, no missing required fields

---

### DEV-414: Calendar Sync Integration (Google/Outlook)
**Depends on:** DEV-385 (Upcoming Deadlines API)
**Priority:** MEDIUM | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Livia (frontend), @Clelia (tests)

**What to build:** Export deadlines to external calendars via .ics file generation and/or CalDAV sync. Required by PRD AC-006.2 ("Integrazione con calendario esterno — Google, Outlook"). MVP: generate downloadable .ics files for individual deadlines and bulk export. Phase 2: bidirectional sync via Google Calendar API / Microsoft Graph API.

**File:** `app/services/calendar_sync_service.py`

**Tests:** `tests/services/test_calendar_sync.py` — single .ics generation, bulk .ics, valid iCalendar format, timezone handling

---

### DEV-415: Communication Unsubscribe Mechanism
**Depends on:** DEV-330 (CommunicationService), DEV-333 (Email Sending)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (compliance review), @Clelia (tests)

**What to build:** Unsubscribe mechanism for client communications. Each sent email must include an unsubscribe link. When clicked, marks the client as `consenso_marketing = false` and prevents future bulk communications. Required by PRD §8 Risk "Spam communications" mitigation. Uses List-Unsubscribe email header for standards compliance.

**File:** `app/services/unsubscribe_service.py` + `app/api/v1/unsubscribe.py`

**Tests:** `tests/services/test_unsubscribe.py` — unsubscribe via link, consent flag updated, no further emails sent, re-subscribe flow

---

### DEV-416: ADR-023 Tiered Ingestion Pipeline Verification
**Depends on:** Nothing (verification of existing implementation)
**Priority:** HIGH | **Effort:** 3h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Verify and wire the existing tiered ingestion service (`app/services/tiered_ingestion_service.py` + `config/document_tiers.yaml`) into the active RAG pipeline. ADR-023 was implemented but may not be fully integrated. Ensure legal documents are chunked with proper overlap to prevent hallucinations in matching engine. This is a prerequisite for matching quality.

**File:** `app/services/tiered_ingestion_service.py` (verify), pipeline integration nodes (modify if needed)

**Tests:** `tests/services/test_tiered_ingestion_integration.py` — verify tier assignment, chunk sizes for legal docs, overlap, pipeline connectivity

---

### DEV-417: Usage-Based Billing Studio Integration (ADR-027)
**Depends on:** DEV-300 (Studio model), DEV-307 (Migration)
**Priority:** HIGH | **Effort:** 4h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Primo (DB), @Clelia (tests)

**What to build:** Integrate existing billing infrastructure (`app/models/billing.py`, `app/services/billing_plan_service.py`, ADR-027) with the new `studio_id` multi-tenant architecture. Add per-studio LLM usage tracking and cost ceilings. Without this, a single studio could exhaust the platform's LLM budget. Wire `exchange_rate_service.py` (ADR-026) for EUR cost calculation.

**File:** `app/services/billing_plan_service.py` (enhance), `app/models/billing.py` (enhance)

**Tests:** `tests/services/test_billing_studio_integration.py` — studio usage tracking, cost ceiling enforcement, exchange rate EUR calculation

---

### DEV-418: Monitoring and Alerting Infrastructure
**Depends on:** Nothing (independent infrastructure)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Silvano (primary), @Valerio (performance), @Clelia (tests)

**What to build:** Prometheus metrics endpoint + Grafana dashboard configuration for PratikoAI 2.0. Required by PRD §4.1 (99.9% uptime measured via Prometheus). Track: P95 response time (≤3s target), matching latency (≤2s target), import throughput, communication generation time, error rates, DB connection pool, Redis cache hit rate.

**File:** `app/middleware/metrics.py` + `config/grafana/pratikoai_dashboard.json`

**Tests:** `tests/middleware/test_metrics.py` — metrics endpoint accessible, key counters increment

---

### DEV-419: Communication History Retention Policy (24 months)
**Depends on:** DEV-330 (CommunicationService)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (GDPR compliance), @Clelia (tests)

**What to build:** Background job to enforce 24-month retention of sent communications (REFERENCE §4.3). Communications older than 24 months are anonymized (client PII removed, aggregate stats kept). Configurable per studio if retention policy is studio-defined.

**File:** `app/jobs/communication_retention_job.py`

**Tests:** `tests/jobs/test_communication_retention.py` — retention enforcement, anonymization, studio override

---

### DEV-420: GDPR Data Export in JSON Format
**Depends on:** DEV-314 (Client Export to Excel)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (GDPR review), @Clelia (tests)

**What to build:** Extend client export to support JSON format in addition to Excel. GDPR data portability (Art. 20) requires machine-readable format. JSON export includes all client data, profile, communications history, and calculation history.

**File:** `app/services/client_export_service.py` (extend)

**Tests:** `tests/services/test_client_export_json.py` — JSON structure, all fields present, encrypted fields decrypted, valid JSON schema

---

### DEV-421: Document Type Auto-Detection (>90% accuracy)
**Depends on:** DEV-411 (Fattura XML Parser), DEV-360 (Bilancio Parser), DEV-361 (CU Parser), DEV-392 (F24 Parser)
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Automatic document type detection service. When user uploads a document, detect its type (fattura XML, fattura PDF, F24, CU, bilancio, busta paga, visura, contratto) and route to the appropriate parser. Target >90% accuracy (AC-008.3). Use file extension, MIME type, and content heuristics (XML namespace for fatture, keyword patterns for others).

**File:** `app/services/document_type_detector.py`

**Tests:** `tests/services/test_document_type_detector.py` — XML fattura detection, PDF F24, PDF bilancio, ambiguous documents, accuracy benchmark

---

## Wave 7: Dashboard + Frontend Integration + Cross-Cutting

### DEV-355: Dashboard Data Aggregation
**Depends on:** DEV-354 (ROI Metrics Service)
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Dashboard service aggregating data from multiple sources: client count, active procedure, pending communications, recent matches.

**File:** `app/services/dashboard_service.py`

**Unlocks:** DEV-356, DEV-358

---

### DEV-356: Dashboard API Endpoint
**Depends on:** DEV-355 (Dashboard Data Aggregation)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Single API endpoint returning all aggregated dashboard data.

**File:** `app/api/v1/dashboard.py`

---

### DEV-357: Activity Timeline Model
**Depends on:** DEV-355 (Dashboard Data Aggregation)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Primo (primary), @Clelia (tests)

**What to build:** Activity model or view aggregating recent actions (communications, procedure, matches) for the dashboard timeline.

**File:** `app/models/activity_timeline.py`

---

### DEV-358: Dashboard Caching
**Depends on:** DEV-355 (Dashboard Data Aggregation)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Add Redis caching to dashboard service for improved query performance.

**File:** `app/services/dashboard_service.py` (extend with caching)

---

### DEV-366: OpenAPI Schema Validation
**Depends on:** All API endpoints from Waves 4-5
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Ensure OpenAPI schema is accurate and complete for frontend type generation.

**File:** `app/api/` (validation additions)

---

### DEV-367: API Error Response Standardization
**Depends on:** All API endpoints
**Priority:** HIGH | **Effort:** 2h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Standardize error response format across all endpoints for consistent frontend handling.

**File:** `app/core/exceptions.py` (enhance)

---

### DEV-368: Pagination Standardization
**Depends on:** All list API endpoints
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Standardize pagination format across all list endpoints.

**File:** `app/schemas/pagination.py`

---

### DEV-369: WebSocket Events for Real-time Updates
**Depends on:** DEV-320 (Matching), DEV-330 (Communications), DEV-340 (Procedura)
**Priority:** MEDIUM | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** WebSocket endpoint for real-time events: matches, communications, progress updates.

**File:** `app/api/v1/websocket.py`

---

### DEV-370: Frontend SDK Types Generation
**Depends on:** DEV-366 (OpenAPI Schema Validation)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Livia (primary), @Ezio (API support)

**What to build:** Automatic TypeScript type generation from OpenAPI schema.

**File:** `web/src/types/generated/` + build script

---

### DEV-386: Deadline Calendar Widget (Frontend)
**Depends on:** DEV-385 (Deadlines API), DEV-370 (Frontend SDK Types)
**Priority:** MEDIUM | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Livia (primary), @Ezio (API contract), @Clelia (tests)

**What to build:** React calendar component showing deadlines with color-coding by type and status.

**File:** `web/src/components/deadlines/DeadlineCalendar.tsx`

---

### DEV-402: `/procedura` Slash Command Handler
**Depends on:** DEV-340 (ProceduraService), DEV-341 (Pre-configured Procedure)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Parse `/procedura [query]` from chat input. Show searchable procedure list or render specific procedure in read-only mode. No ProceduraProgress record created.

**File:** `app/services/slash_command_handler.py` (new) + `app/api/v1/chat.py` (extend)

**Unlocks:** DEV-405 (E2E Tests)

---

### DEV-403: `@client` Mention System with Autocomplete
**Depends on:** DEV-309 (ClientService), DEV-340 (ProceduraService), DEV-345 (Procedura Context)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Livia (frontend autocomplete), @Clelia (tests)

**What to build:** `@` mention system: autocomplete client names with 300ms debounce, inject client context into RAGState, action picker (generic question, client question, client card, start procedure).

**File:** `app/services/client_mention_service.py` (new) + `app/api/v1/chat.py` (extend)

**Unlocks:** DEV-405 (E2E Tests)

---

### DEV-404: Generic vs Client-Specific Procedure Logic Split
**Depends on:** DEV-340 (ProceduraService)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** MODIFYING
**Agent:** @Ezio (primary), @Clelia (tests)

**What to build:** Clean separation between generic consultation mode (read-only, no side effects) and client-specific tracking mode (creates ProceduraProgress).

**File:** `app/services/procedura_service.py` (refine)

**Unlocks:** DEV-405 (E2E Tests)

---

### DEV-378: GDPR Compliance Dashboard
**Depends on:** DEV-372, DEV-373, DEV-374, DEV-375, DEV-376, DEV-377 (all GDPR components)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Ezio (primary), @Severino (compliance), @Clelia (tests)

**What to build:** Compliance dashboard endpoint showing DPA status, pending data requests, breach status.

**File:** `app/api/v1/compliance.py`

**Unlocks:** DEV-379

---

## Wave 8: Testing & Validation

Comprehensive test suites that validate entire feature chains.

### DEV-318: Unit Tests for Phase 1 Services
**Depends on:** DEV-308, DEV-309, DEV-310, DEV-313, DEV-314, DEV-317 (all Phase 1 services)
**Priority:** HIGH | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary)

**What to build:** Comprehensive unit tests for all Phase 1 services with 80%+ coverage target.

**File:** `tests/services/test_studio_service.py`, `tests/services/test_client_service.py`, etc.

**Unlocks:** DEV-319

---

### DEV-319: Integration Tests for Client APIs
**Depends on:** DEV-311 (Studio API), DEV-312 (Client API), DEV-318 (Unit Tests)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary), @Ezio (support)

**What to build:** Integration tests using pytest-asyncio and httpx test client verifying full request/response cycle.

**File:** `tests/api/test_client_api.py`, `tests/api/test_studio_api.py`

---

### DEV-327: Multi-Tenant Isolation Tests
**Depends on:** DEV-316 (Tenant Middleware), DEV-323 (LangGraph Matching)
**Priority:** CRITICAL | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary), @Severino (review)

**What to build:** Comprehensive security tests verifying Studio A cannot access Studio B's data under any circumstance. Target 95%+ coverage of isolation logic.

**File:** `tests/security/test_tenant_isolation.py`

---

### DEV-328: Matching Performance Tests
**Depends on:** DEV-320 (NormativeMatchingService)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary), @Valerio (performance)

**What to build:** Performance benchmarks: inline matching <100ms, background matching <5s for 100 clients.

**File:** `tests/performance/test_matching_perf.py`

---

### DEV-329: Unit Tests for Matching Services
**Depends on:** DEV-320, DEV-322 (Matching + Vector services)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary)

**What to build:** Unit tests for NormativeMatchingService, ProfileEmbeddingService, and related components.

**File:** `tests/services/test_matching_service.py`

---

### DEV-339: E2E Tests for Communication Flow
**Depends on:** DEV-332 (Communication API), DEV-333 (Email), DEV-337 (Response Formatter)
**Priority:** HIGH | **Effort:** 3h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary)

**What to build:** End-to-end tests: create draft → submit review → approve → send → verify delivery.

**File:** `tests/e2e/test_communication_flow.py`

---

### DEV-347: E2E Tests for Procedura Flow
**Depends on:** DEV-342 (Procedura API), DEV-343 (Checklist), DEV-345 (Chat context)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary)

**What to build:** End-to-end tests: start procedura → complete steps → resume → complete → view history.

**File:** `tests/e2e/test_procedura_flow.py`

---

### DEV-359: E2E Tests for Dashboard
**Depends on:** DEV-356 (Dashboard API), DEV-358 (Dashboard Caching)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary)

**What to build:** End-to-end tests verifying dashboard data accuracy.

**File:** `tests/e2e/test_dashboard_flow.py`

---

### DEV-365: Document Parser Integration Tests
**Depends on:** DEV-360 (Bilancio Parser), DEV-361 (CU Parser)
**Priority:** MEDIUM | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary)

**What to build:** Integration tests with real sample PDF documents.

**File:** `tests/services/test_document_parsers.py`

---

### DEV-379: GDPR E2E Tests
**Depends on:** DEV-372-378 (all Phase 9 GDPR tasks)
**Priority:** CRITICAL | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary), @Severino (review)

**What to build:** Comprehensive GDPR E2E test suite. Production deployment gate — GDPR compliance required.

**File:** `tests/e2e/test_gdpr_compliance.py`

---

### DEV-387: Deadline System E2E Tests
**Depends on:** DEV-380-386 (all Phase 10 Deadline tasks)
**Priority:** CRITICAL | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary), @Severino (review)

**What to build:** Comprehensive E2E tests for the deadline system: creation → extraction → matching → notification → calendar display.

**File:** `tests/e2e/test_deadline_system.py`

---

### DEV-405: E2E Tests for `/procedura` and `@client` Features
**Depends on:** DEV-402 (/procedura command), DEV-403 (@client mention), DEV-404 (logic split)
**Priority:** HIGH | **Effort:** 2h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary)

**What to build:** End-to-end tests verifying `/procedura` slash command and `@client` mention system work correctly together and independently.

**File:** `tests/e2e/test_procedura_commands_flow.py`

---

## Wave 9: Full Journey E2E Test (final validation)

### DEV-371: Full User Journey E2E Test
**Depends on:** All Phase 0-8 tasks
**Priority:** CRITICAL | **Effort:** 4h | **Classification:** ADDITIVE
**Agent:** @Clelia (primary), @Severino (security review)

**What to build:** Comprehensive E2E test covering the entire PratikoAI 2.0 user journey:
1. Register → 2. Create Studio → 3. Import Clients → 4. Chat → 5. View Matches → 6. Create Communication → 7. Approve → 8. Send → 9. View Dashboard

**File:** `tests/e2e/test_pratikoai_2_0_flow.py`

---

## Dependency Graph

```
Wave 0 (Foundation — no dependencies):
  DEV-300 (Studio Model)
  DEV-303 (MatchingRule Model)
  DEV-305 (Procedura Model)
  DEV-388 (PDF Export)
  DEV-389 (Hallucination Guard)
  DEV-390 (OCR)
  DEV-393 (Regional Tax Config — ENHANCE existing service)
  DEV-395 (Rate Limiting)
  DEV-396 (DPIA)
  DEV-416 (Tiered Ingestion Verification — existing service)
  DEV-418 (Monitoring Infrastructure)

Wave 1 (depends on Wave 0 models):
  DEV-301 → DEV-302 (Client → ClientProfile)
  DEV-300+301+305 → DEV-306 (ProceduraProgress)
  DEV-300+301 → DEV-304 (Communication)
  DEV-300 → DEV-324 (ProactiveSuggestion)
  DEV-300 → DEV-394 (Feature Flags)
  DEV-396 → DEV-397 (Vendor DPA)
  DEV-396 → DEV-398 (LLM DPA)

Wave 2 (migration gate):
  DEV-300+301+302+303+304+305+306 → DEV-307 (Alembic Migration)

Wave 3 (core services, depend on migration):
  DEV-307 → DEV-308 (StudioService)
  DEV-307 → DEV-309 (ClientService)
  DEV-307+309 → DEV-310 (ClientProfileService)
  DEV-307 → DEV-321 (Matching Rules Seed — 10 MVP + 5 extended)
  DEV-307 → DEV-322 (Vector Generation)
  DEV-307 → DEV-330 (CommunicationService)
  DEV-307 → DEV-340 (ProceduraService)
  DEV-307 → DEV-380 (Deadline Model)
  DEV-307 → DEV-372 (DPA Model)
  DEV-307 → DEV-374 (Breach Model)
  DEV-307+300 → DEV-417 (Billing Studio Integration)

Wave 4 (API layer + advanced services):
  DEV-308 → DEV-311 (Studio API)
  DEV-309+310 → DEV-312 (Client API)
  DEV-308 → DEV-315 (User-Studio)
  DEV-309+321+322+302 → DEV-320 (MatchingService)
  DEV-330 → DEV-331, DEV-332, DEV-333, DEV-334, DEV-335, DEV-336
  DEV-330 → DEV-415 (Unsubscribe Mechanism)
  DEV-330 → DEV-419 (Communication Retention 24mo)
  DEV-333 → DEV-412 (Email Open Tracking)
  DEV-340 → DEV-341 (10 Procedures P001-P010), DEV-342, DEV-343, DEV-344, DEV-345
  DEV-380 → DEV-381 (DeadlineService)
  DEV-309 → DEV-314 (Export)
  DEV-314 → DEV-420 (JSON Export)
  DEV-372 → DEV-373 (DPA Workflow)
  DEV-374 → DEV-375 (Breach Service)
  DEV-309 → DEV-376 (Processing Register)
  DEV-309 → DEV-377 (Data Rights)
  DEV-393 → DEV-413 (Regional Data Population — 20 cities)

Wave 5 (multi-tenancy + matching pipeline):
  DEV-315 → DEV-316 (Tenant Middleware)
  DEV-309+312 → DEV-313 (Import)
  DEV-309+314 → DEV-317 (GDPR Deletion)
  DEV-320+316 → DEV-323 (LangGraph Matching Node)
  DEV-320+324 → DEV-325 (Background Matching Job)
  DEV-325 → DEV-326 (Matching API)
  DEV-323+330 → DEV-337 (Response Formatter)
  DEV-381 → DEV-382, DEV-383, DEV-384, DEV-385
  DEV-385 → DEV-414 (Calendar Sync — .ics export)
  DEV-397+398 → DEV-399, DEV-400

Wave 6 (fiscal + documents + dashboard):
  DEV-309+302 → DEV-348 → DEV-349, DEV-350, DEV-351, DEV-352
  DEV-348 → DEV-406 (IVA), DEV-407 (Ritenuta), DEV-408 (Cedolare Secca), DEV-409 (TFR)
  DEV-348+349+350+393 → DEV-410 (Netto in Busta / Costo Azienda)
  DEV-349+350+351+406+407+408+409+410 → DEV-353 (Calculation Accuracy Tests)
  DEV-309+330+340 → DEV-354 → DEV-355 → DEV-356, DEV-357, DEV-358
  DEV-412 → DEV-354 (ROI Metrics — open rate data)
  DEV-360, DEV-361, DEV-411 (Fattura XML) → DEV-363 → DEV-391, DEV-392
  DEV-411+360+361+392 → DEV-421 (Document Type Auto-Detection)

Wave 7 (frontend + cross-cutting + /procedura + @client):
  DEV-366 → DEV-370
  DEV-385+370 → DEV-386 (Calendar Widget)
  DEV-340+341 → DEV-402 (/procedura)
  DEV-309+340+345 → DEV-403 (@client)
  DEV-340 → DEV-404 (Procedure logic split)
  All GDPR → DEV-378 (GDPR Dashboard)

Wave 8 (comprehensive testing):
  Services → DEV-318, DEV-329
  APIs → DEV-319
  DEV-316+323 → DEV-327 (Tenant Isolation Tests)
  DEV-320 → DEV-328 (Performance Tests)
  DEV-332+333+337 → DEV-339 (Communication E2E)
  DEV-342+343+345 → DEV-347 (Procedura E2E)
  DEV-356+358 → DEV-359 (Dashboard E2E)
  DEV-360+361+411 → DEV-365 (Document Parser Tests)
  All GDPR → DEV-379 (GDPR E2E)
  All Deadline → DEV-387 (Deadline E2E)
  DEV-402+403+404 → DEV-405 (/procedura + @client E2E)

Wave 9 (final validation):
  All Phases 0-8 → DEV-371 (Full Journey E2E)
```

---

## Task Summary by Phase (original grouping)

| Phase | Tasks | Wave(s) | Week |
|-------|-------|---------|------|
| **Phase 0: Foundation** | DEV-300 to DEV-307 (8 tasks) | 0, 1, 2 | 1-2 |
| **Phase 1: Service Layer** | DEV-308 to DEV-319, DEV-420 (13 tasks) | 3, 4, 5, 8 | 3-4 |
| **Phase 2: Matching Engine** | DEV-320 to DEV-329 (10 tasks) | 3, 4, 5, 8 | 5-6 |
| **Phase 3: Communications** | DEV-330 to DEV-339, DEV-412, DEV-415, DEV-419 (13 tasks) | 3, 4, 5, 8 | 7-8 |
| **Phase 4: Procedure** | DEV-340 to DEV-347, DEV-402 to DEV-405 (12 tasks) | 3, 4, 5, 7, 8 | 9-10 |
| **Phase 5: Tax Calculations** | DEV-348 to DEV-353, DEV-406 to DEV-410, DEV-413 (12 tasks) | 4, 6 | 11 |
| **Phase 6: Dashboard** | DEV-354 to DEV-359 (6 tasks) | 6, 7, 8 | 12 |
| **Phase 7: Documents** | DEV-360, DEV-361, DEV-363, DEV-365, DEV-411, DEV-421 (6 tasks) | 6, 8 | 13 |
| **Phase 8: Frontend Integration** | DEV-366 to DEV-371 (6 tasks) | 7, 8, 9 | 14 |
| **Phase 9: GDPR Compliance** | DEV-372 to DEV-379 (8 tasks) | 3, 4, 5, 7, 8 | 15 |
| **Phase 10: Deadline System** | DEV-380 to DEV-387, DEV-414 (9 tasks) | 3, 4, 5, 7, 8 | 16-17 |
| **Phase 11: Infrastructure** | DEV-388 to DEV-395, DEV-416, DEV-417, DEV-418 (11 tasks) | 0, 3, 6 | 18 |
| **Phase 12: Pre-Launch** | DEV-396 to DEV-401 (6 tasks) | 0, 1, 4, 5 | Pre-launch |

**Total: 120 tasks** (was 104, added 16 tasks to close gaps identified in PRD review)

---

## High-Risk Tasks (require extra review)

| Task ID | Risk Level | Risk Type | Mitigation |
|---------|------------|-----------|------------|
| DEV-307 | CRITICAL | DB Migration | Backup before deploy, reversible migration |
| DEV-315 | HIGH | User Table Modification | Existing users affected, nullable FK |
| DEV-323 | HIGH | LangGraph Pipeline | Modifies 134-step pipeline |
| DEV-327 | CRITICAL | Security | Multi-tenant isolation must be 95%+ |
| DEV-337 | HIGH | LangGraph Modification | Response formatter changes |
| DEV-372 | CRITICAL | Legal/Compliance | DPA required before client data |
| DEV-374 | CRITICAL | Legal/Compliance | 72h breach notification requirement |
| DEV-396 | CRITICAL | Legal/Compliance | DPIA mandatory before client data storage |
| DEV-397 | CRITICAL | Infrastructure | Encryption at rest + DPA with Hetzner |
| DEV-398 | CRITICAL | Legal/Compliance | LLM transfer safeguards required |
| DEV-399 | HIGH | Legal/Compliance | 30-day Garante notification period |
| DEV-416 | HIGH | Data Quality | Tiered ingestion affects matching accuracy |
| DEV-417 | HIGH | Financial | Without billing limits a studio can exhaust LLM budget |

---

## Success Criteria

- [ ] 100 clients per studio functional
- [ ] 10 procedures available (P001-P010 per PRD FR-001 §3.1.4)
- [ ] 10 MVP matching rules + 5 extended rules seeded and functional
- [ ] Matching suggestions appear in chat within response time budget
- [ ] Communications workflow complete (draft → approve → send) with unsubscribe mechanism
- [ ] Email open tracking functional (link-based, GDPR-compliant)
- [ ] All fiscal calculations working with client context: IRPEF, IVA, INPS, IMU, ritenuta, cedolare secca, TFR, netto in busta
- [ ] IRPEF accuracy 100% vs AdE simulator (AC-007.1)
- [ ] Regional tax data populated for 20 cities (AC-007.5)
- [ ] Fattura Elettronica XML parsing functional (AC-008.4)
- [ ] Document type auto-detection >90% accuracy (AC-008.3)
- [ ] Calendar export (.ics) for deadlines functional (AC-006.2)
- [ ] 69.5%+ test coverage maintained
- [ ] Multi-tenant isolation 95%+ tested
- [ ] Response time ≤3 seconds maintained (monitored via Prometheus)
- [ ] GDPR compliance verified (DPA, breach notification, data portability JSON+Excel)
- [ ] DPA acceptance workflow functional
- [ ] Tiered ingestion pipeline verified and integrated (ADR-023)
- [ ] Billing per-studio usage tracking functional (ADR-027)
- [ ] Communication history 24-month retention enforced
- [ ] All E2E test flows passing
- [ ] All regression tests passing
