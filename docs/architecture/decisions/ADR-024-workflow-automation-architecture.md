# ADR-024: Workflow Automation Architecture

## Status

Proposed

## Date

2026-01-30

## Decision Makers

- @egidio (Architect - approval required)
- @mario (Requirements - impact analysis)

## Context

PratikoAI needs to evolve from a proactive assistant (v1.5) to an autonomous workflow engine (v1.8) that enables Italian professionals (commercialisti, consulenti del lavoro, avvocati tributaristi) to delegate complex, multi-step compliance tasks.

### Current State (v1.5)

- Reactive Q&A with suggested actions
- Single-session interactions
- Manual document uploads per query
- No background processing capability
- Web-only interface

### Target State (v1.8)

- **Cowork-like experience**: Submit complex tasks, step away, return to completed work
- **Project-based organization**: Client workflows with persistent context
- **Desktop application**: Native folder sync, background processing, system notifications
- **End-to-end workflows**: Dichiarazione redditi, F24, apertura/chiusura attivit, pensionamento

### Key Requirements

1. **Background Execution**: Workflows must run without active user session
2. **Human-in-the-Loop**: Professional approval at configurable checkpoints
3. **Document Management**: Local folder sync with cloud storage
4. **GDPR Compliance**: EU data residency, audit trails, data minimization
5. **Cross-Platform**: Desktop app (macOS first, then Windows) + web companion

### Reference Model

Claude Desktop serves as the reference implementation for user experience patterns:
- Tab-based navigation: `Chat | Cowork | Code`
- Projects with context persistence
- Fire-and-forget task execution
- Transparent progress visibility
- Local file system integration

**PratikoAI Desktop Tab Structure:**
```
┌─────────────────────────────────────────────────┐
│  [Chat]  [coPratiko]                            │
├─────────────────────────────────────────────────┤
│                                                 │
│  Chat tab: Proactive Assistant (from 1.5)       │
│  - Existing Q&A functionality                   │
│  - Suggested actions                            │
│  - Document analysis                            │
│                                                 │
│  coPratiko tab: Autonomous Workflows (new 1.8)  │
│  - Projects with folder sync                    │
│  - Workflow execution                           │
│  - Checkpoints & approvals                      │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Key Design Decision:** coPratiko ADDS to existing chat, doesn't replace it. The v1.5 proactive assistant remains fully functional and accessible via the Chat tab. Users can seamlessly switch between interactive Q&A (Chat) and autonomous workflows (coPratiko).

## Decision

### 1. Desktop Application Framework: Kotlin Multiplatform + Compose Multiplatform

**Decision:** Use Kotlin Multiplatform (KMP) with Compose Multiplatform for the desktop application.

**Rationale:**

| Criteria | KMP + Compose | Electron | Tauri | Flutter |
|----------|---------------|----------|-------|---------|
| App Size | ~25MB | 100-150MB | 2-10MB | ~18MB |
| Memory (idle) | ~50-80MB | 200-400MB | 20-40MB | ~100MB |
| Code Sharing | Android, iOS, Desktop, Web | Desktop only | Desktop + Mobile (2.0) | All platforms |
| Native Feel | Compiles to native | Chromium-based | Webview-based | Custom rendering |
| Future Mobile | Same codebase | New codebase | New codebase | Same codebase |

**Why KMP over alternatives:**
- **vs Electron**: 4x smaller footprint, native performance, mobile code reuse
- **vs Tauri**: Better UI control (Compose vs webview), Kotlin expertise transferable
- **vs Flutter**: Kotlin closer to existing skills, stronger JetBrains tooling, growing enterprise adoption (18% developers, projected 30%+ by 2027)

**Code Sharing Strategy:**
```
┌────────────────────────────────────────────────────────┐
│                  SHARED MODULE (KMP)                    │
│                    (commonMain)                         │
├────────────────────────────────────────────────────────┤
│  API Client │ Models │ Business Logic │ State Mgmt    │
└────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Desktop    │  │   Android    │  │     iOS      │
│ (Compose UI) │  │ (Compose UI) │  │ (Compose UI) │
│   jvmMain    │  │ androidMain  │  │   iosMain    │
└──────────────┘  └──────────────┘  └──────────────┘
```

- **100% shared**: API clients, models, business logic, state management
- **95% shared**: UI with Compose Multiplatform
- **Platform-specific**: File system access, notifications, system tray

### 2. Project-Based Organization

**Decision:** Implement Projects as the primary organizational unit, mirroring Claude Cowork.

**Project Structure:**
```
Project
├── id: UUID
├── name: str (e.g., "Mario Rossi - 730/2026")
├── client_id: Optional[UUID]  # Link to future client DB
├── studio_id: UUID  # Multi-tenancy (ADR-017)
├── workflow_type: WorkflowType
├── documents: List[ProjectDocument]
│   ├── local_path: Optional[str]  # Desktop folder sync
│   ├── cloud_path: str  # S3/MinIO storage
│   └── sync_status: SyncStatus
├── workflow_state: WorkflowState
├── checkpoints: List[Checkpoint]
├── created_at: datetime
└── updated_at: datetime
```

**Desktop Folder Sync:**
- User designates local folder for each project
- Bidirectional sync via file system watcher (jvmMain platform-specific)
- Conflict resolution: server wins for workflow-generated files, ask user for manual uploads

### 3. Workflow Execution Model: LangGraph-Based

**Decision:** Extend existing LangGraph 134-step pipeline to support autonomous workflows with checkpointing.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW ENGINE                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐ │
│  │  WorkflowTemplate│   │  WorkflowExecutor│   │  DocumentGenerator│ │
│  │  (YAML configs)  │──▶│  (LangGraph)     │──▶│  (Module PDFs)   │ │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘ │
│          │                      │                      │             │
│          ▼                      ▼                      ▼             │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐ │
│  │  ChecklistManager│   │  SubAgentCoord   │   │  IntegrationMgr  │ │
│  │  (Doc tracking)  │   │  (Parallel exec) │   │  (API/Prepare)   │ │
│  └──────────────────┘   └──────────────────┘   └──────────────────┘ │
│                                                                      │
│                    ┌──────────────────────┐                         │
│                    │  CheckpointManager   │                         │
│                    │  (Human-in-loop)     │                         │
│                    └──────────────────────┘                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Components:**

| Component | Purpose | Reuses Existing |
|-----------|---------|-----------------|
| WorkflowTemplate | YAML definitions per workflow type | YAML template pattern from v1.5 |
| WorkflowExecutor | LangGraph state machine | 134-step pipeline, AsyncPostgresSaver |
| CheckpointManager | Human approval gates | New |
| SubAgentCoordinator | Parallel task execution | LangGraph parallelization |
| DocumentGenerator | Generate official forms | New (PDF generation) |
| IntegrationManager | External system adapters | New |

**Workflow State Persistence:**
- Extend `AsyncPostgresSaver` for workflow state
- New `workflow_tasks` table for persistent tracking
- SSE for real-time progress updates (existing infrastructure)

### 4. Integration Strategy: User-Configurable Levels

**Decision:** Implement progressive integration levels, letting professionals choose their comfort level.

| Level | Description | Use Case |
|-------|-------------|----------|
| **PREPARE_ONLY** (Default) | Generate filled documents, user uploads manually | Cautious users, complex cases |
| **API_WHERE_AVAILABLE** | Use official APIs (FatturaPA, INPS, etc.) | Common scenarios with API support |
| **GUIDED_RPA** | Step-by-step guidance with screenshots | Portals without APIs |
| **FULL_AUTOMATION** (Future) | Bot automation for portal submission | High-trust users, routine tasks |

**Per-Workflow Configuration:**
```yaml
# config/workflow_integrations.yaml
workflows:
  dichiarazione_redditi:
    default_level: "prepare_only"
    available_levels:
      - "prepare_only"
      - "api_where_available"  # AdE telematico
    checkpoints:
      - document_validation
      - tax_calculation
      - final_review

  f24_mensile:
    default_level: "api_where_available"
    available_levels:
      - "prepare_only"
      - "api_where_available"  # F24 web
    checkpoints:
      - amount_confirmation
```

### 5. Human-in-the-Loop: Configurable Supervision

**Decision:** Implement four supervision modes with professional override capability.

| Mode | Behavior | Risk Level | Use Case |
|------|----------|------------|----------|
| **FULL_SUPERVISION** (Default) | Every significant step requires approval | LOWEST | New users, complex cases |
| **APPROVAL_REQUIRED** | Batch approve at phase boundaries | LOW | Standard operations |
| **CONFIDENCE_BASED** | Auto-proceed if confidence >90% | MEDIUM | Experienced users |
| **REVIEW_CHECKPOINTS** | Auto-execute, pause at key review points | HIGHER | Trusted workflows |

**Checkpoint Types:**
```python
class CheckpointType(str, Enum):
    DOCUMENT_VALIDATION = "document_validation"
    CALCULATION_REVIEW = "calculation_review"
    DATA_CONFIRMATION = "data_confirmation"
    FINAL_REVIEW = "final_review"
    SUBMISSION_APPROVAL = "submission_approval"
```

**Professional Override:**
- Per-workflow configuration
- Per-client configuration (trusted client = less friction)
- Emergency stop at any point via desktop app

### 6. Target Workflows (v1.8 Scope)

| Workflow | Complexity | Priority | Integration |
|----------|------------|----------|-------------|
| Dichiarazione Redditi (730/Redditi PF) | HIGH | P1 | Prepare + Optional AdE API |
| Adempimenti Periodici (F24, IVA, LIPE) | MEDIUM | P2 | Prepare + F24 Web API |
| Apertura/Chiusura Attivit | HIGH | P3 | Prepare only (multi-portal) |
| Pensionamento/TFR | HIGH | P4 | Prepare + INPS API research |

### 7. GDPR Compliance Architecture

**Decision:** Privacy by design with EU-only data residency.

| Principle | Implementation |
|-----------|----------------|
| Data Minimization | Collect only documents needed for specific workflow |
| Purpose Limitation | Data used only for declared workflow |
| Storage Limitation | Configurable auto-purge after workflow completion |
| Integrity | SHA-256 checksums on all documents |
| Confidentiality | AES-256 at rest, TLS 1.3 in transit |
| Accountability | Full audit trail per GDPR Art. 30 |

**Data Flow:**
```
Client Documents → Desktop App → Backend (Hetzner EU) → Workflow Processing
                        ↓                    ↓
                  Local Cache           Encrypted at Rest
                  (optional)            Audit Logged
                                        Auto-purge Option
```

**Responsibility Model:**
- Professional = Data Controller
- PratikoAI = Data Processor
- DPA (Data Processing Agreement) required

## Consequences

### Positive

1. **Cowork-like UX**: Professionals can submit complex tasks and return to completed work
2. **Native Performance**: KMP desktop app is lightweight (~25MB) with native feel
3. **Code Reuse**: Shared code across desktop, Android, iOS (future)
4. **Flexible Integration**: Professionals choose their comfort level with automation
5. **GDPR Compliant**: EU data residency, human-in-the-loop, audit trails
6. **Leverages Existing**: Reuses LangGraph pipeline, SSE streaming, checkpointing

### Negative

1. **Development Effort**: ~292h (15-20 weeks) significant investment
2. **KMP Learning Curve**: Team needs Kotlin/Compose expertise (20-30% overhead initially)
3. **Maintenance Burden**: Desktop app adds distribution, updates, platform-specific bugs
4. **Integration Complexity**: Each external system (AdE, INPS) requires custom adapter

### Neutral

1. **macOS First**: Mirrors Cowork strategy, Windows follows
2. **Phased Rollout**: Desktop MVP → First workflow → Additional workflows
3. **Contractor Option**: KMP expert for initial setup could accelerate Phase D1-D3

### Mitigations

| Risk | Mitigation |
|------|------------|
| KMP learning curve | Hire contractor for Phase D1-D3, team learns in parallel |
| Platform-specific bugs | Focus macOS first, add Windows after stable |
| Integration failures | Fallback to PREPARE_ONLY level always available |
| GDPR violations | Mandatory checkpoints for data operations, audit logging |

## Implementation

### Phase Overview

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| **D1** | KMP project setup + shared module | 20h | None |
| **D2** | API client (shared) + auth | 16h | D1 |
| **D3** | Projects UI (Compose) | 24h | D2 |
| **D4** | Folder sync (jvmMain) | 24h | D3 |
| **D5** | Backend sync + offline | 20h | D4 |
| **D6** | System tray + notifications | 12h | D5 |
| **D7** | Auto-update + distribution | 16h | D6 |
| **B1** | Workflow engine foundation | 20h | None |
| **B2** | Projects API + sync endpoints | 16h | B1 |
| **B3** | First workflow (730) | 24h | B2 |
| **B4** | Document generation | 16h | B3 |
| **B5** | Integration adapters | 20h | B4 |
| **W1** | Projects view in web app | 12h | B2 |
| **W2** | Workflow status components | 8h | W1 |
| **T1-T3** | Testing (backend, desktop, E2E) | 36h | All |

### Files to Create

| File | Purpose |
|------|---------|
| `docs/tasks/PRATIKO_1.8_REFERENCE.md` | Functional requirements (Italian) |
| `docs/tasks/PRATIKO_1.8.md` | Task breakdown with DEV-XXX IDs |
| `config/workflow_definitions/` | YAML workflow templates |
| `app/models/workflow.py` | Workflow, Project, Checkpoint models |
| `app/services/workflow_engine/` | Workflow execution services |
| `app/api/v1/projects.py` | Projects CRUD API |
| `app/api/v1/workflows.py` | Workflow execution API |

### Database Schema (New Tables)

```sql
-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    studio_id UUID NOT NULL REFERENCES studios(id),
    client_id UUID REFERENCES clients(id),
    name VARCHAR(200) NOT NULL,
    workflow_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project Documents
CREATE TABLE project_documents (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id),
    filename VARCHAR(255) NOT NULL,
    cloud_path VARCHAR(500) NOT NULL,
    local_path VARCHAR(500),
    sync_status VARCHAR(20) DEFAULT 'synced',
    checksum VARCHAR(64),
    document_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workflow Tasks
CREATE TABLE workflow_tasks (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id),
    workflow_definition_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    current_step VARCHAR(100),
    state JSONB DEFAULT '{}',
    checkpoints JSONB DEFAULT '[]',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workflow Audit Log
CREATE TABLE workflow_audit_log (
    id UUID PRIMARY KEY,
    workflow_task_id UUID NOT NULL REFERENCES workflow_tasks(id),
    action VARCHAR(100) NOT NULL,
    actor_type VARCHAR(20) NOT NULL,  -- 'user' | 'system'
    actor_id UUID,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Related

- **ADR-017**: Multi-tenancy Architecture (studio_id isolation)
- **ADR-020**: Suggested Actions Architecture (proactivity patterns)
- **ADR-021**: Interactive Questions Architecture (checkpoint patterns)
- **ADR-022**: LLM Document Identification (document classification)
- **ADR-023**: Tiered Document Ingestion (document parsing)
- **PRATIKO_1.8_REFERENCE.md**: Functional requirements
- **PRATIKO_1.8.md**: Implementation task breakdown

## References

- [Claude Cowork - Getting Started](https://support.claude.com/articles/13345190-iniziare-con-cowork)
- [Kotlin Multiplatform Official](https://kotlinlang.org/multiplatform/)
- [Compose Multiplatform](https://www.jetbrains.com/lp/compose-multiplatform/)
- [KMP 2026 Adoption Trends](https://www.aetherius-solutions.com/blog-posts/kotlin-multiplatform-in-2026)

## Open Questions (Require @egidio Decision)

1. **Priority Workflow**: Start with 730 (complex but high value) or F24 (simpler, faster demo)?
2. **Document Generation**: Generate actual Modello 730 PDF or prepare data for existing tools?
3. **Offline Capability**: How much should work offline? Document viewing vs full workflow?
4. **Pricing Impact**: Does desktop app justify a higher pricing tier?
5. **Distribution**: App stores (requires approval) or direct download?

---

**Approval Required:** @egidio (Architect)
**Status:** PROPOSED - Awaiting architectural review
