# PratikoAI v1.5 - Proactive Assistant Tasks

**Version:** 1.5
**Date:** December 2025
**Status:** NOT STARTED
**Total Effort:** ~33h (2-3 weeks at 2-3h/day) *(with Claude Code)*

---

## Overview

PratikoAI 2.0 is a major evolution from a Q&A assistant to a **professional engagement platform** for Italian accountants (commercialisti), labor consultants (consulenti del lavoro), and tax lawyers (avvocati tributaristi).

**Current Architecture:** See `docs/DATABASE_ARCHITECTURE.md` for detailed documentation of the production system.

**Related Documents:**
- `docs/tasks/ARCHITECTURE_ROADMAP.md` - Backend development roadmap (v1.0)
- `docs/architecture/decisions/` - Architectural Decision Records

---

## Executive Summary

Transform PratikoAI from a passive Q&A assistant to a proactive assistant that:
- Suggests contextual actions after responses (FR-001)
- Asks structured clarification questions when queries are ambiguous (FR-002)
- Extracts parameters from queries before deciding to ask (FR-003)

## User Decisions

| Decision | Choice |
|----------|--------|
| Analytics tracking | Yes, track all clicks in DB |
| Action selection method | Template-only (rule-based) |
| Error handling | Smart fallback (infer from context, ask only if truly ambiguous) |
| Feature flags | No, full rollout |
| Interactive question UI | Inline in chat (Claude Code style) |
| Config storage | YAML files in `app/core/templates/` |

---

## Key Features

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| FR-001 | Suggested Actions Post-Response | Contextual action buttons after AI responses | HIGH |
| FR-002 | Interactive Structured Questions | Clarification questions for ambiguous queries | HIGH |
| FR-003 | Smart Parameter Extraction | Extract parameters from queries before deciding to ask | CRITICAL |

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
  - `session_id`: Proactivity session context
  - `operation`: What was being attempted
  - `resource_id`: Entity being accessed (action_id, question_id, etc.)
  - `error_type`: Exception class name
  - `error_message`: Human-readable description

**Example Pattern:**
```python
import structlog
logger = structlog.get_logger(__name__)

try:
    result = await proactivity_engine.process(query, context)
except TemplateNotFoundError as e:
    logger.error(
        "template_not_found",
        user_id=current_user.id,
        session_id=context.session_id,
        operation="action_selection",
        domain=context.domain,
        error_type=type(e).__name__,
        error_message=str(e),
    )
    # Smart fallback: return empty actions instead of failing
    return ProactivityResult(actions=[], question=None)
```

### Testing File Conventions

```
tests/
├── schemas/test_proactivity.py              # Unit tests for Pydantic models
├── services/test_proactivity_engine.py      # Unit tests for ProactivityEngine
├── services/test_action_template_service.py # Unit tests for template loading
├── api/test_chatbot_proactivity.py          # Integration tests for APIs
├── api/test_chatbot_actions.py              # /actions/execute endpoint tests
├── api/test_chatbot_questions.py            # /questions/answer endpoint tests
└── e2e/proactivity.spec.ts                  # E2E Playwright tests
```

---

## Agent Assignments Summary

| Agent | Role | Primary Tasks | Support Tasks |
|-------|------|---------------|---------------|
| **@Ezio** | Backend Developer | 12 tasks | 2 tasks (review) |
| **@Livia** | Frontend Expert | 5 tasks | - |
| **@Clelia** | Test Generation | 5 tasks | 21 tasks (all features) |
| **@Egidio** | Architect | 2 tasks (ADRs) | 2 tasks (review) |
| **@Primo** | Database Designer | - | 1 task (review) |

---

## Architecture Decisions Required

| ADR | Title | Status | Description |
|-----|-------|--------|-------------|
| ADR-018 | Suggested Actions Architecture | PROPOSED | Template-based selection (not LLM) for performance |
| ADR-019 | Interactive Questions Architecture | PROPOSED | Inline questions (Claude Code style) for UX |

---

## Task ID Mapping

| Task Range | Phase |
|------------|-------|
| DEV-150 to DEV-156 | Phase 1: Foundation (Backend) |
| DEV-157 to DEV-162 | Phase 2: API Integration (Backend) |
| DEV-163 to DEV-167 | Phase 3: Frontend Components |
| DEV-168 to DEV-172 | Phase 4: Testing |
| DEV-173 to DEV-175 | Phase 5: Documentation |

---

## High-Risk Tasks (Require Extra Review)

| Task ID | Risk Level | Risk Type | Mitigation |
|---------|------------|-----------|------------|
| DEV-154 | HIGH | Existing Code Modification | Extends AtomicFactsExtractor, run full regression suite |
| DEV-157 | MEDIUM | API Schema Change | Use optional fields for backward compatibility |
| DEV-158 | HIGH | Chat Endpoint Modification | Comprehensive integration tests, timeout fallback |
| DEV-159 | HIGH | Streaming Modification | SSE format changes require frontend coordination |
| DEV-166 | HIGH | Chat UI Integration | Risk of breaking existing chat flow, feature flag option |
| DEV-167 | MEDIUM | Mobile Styling | Test all breakpoints before merge |

---

## Task Dependency Map

**Critical Path:** Tasks must be completed in order. Blocking tasks prevent downstream work.

### Phase 0 → Phase 1 Dependencies

```
DEV-150 (Pydantic Models)
    ├── DEV-151 (Template Loader) ─── DEV-152 (Action Templates)
    │                              └── DEV-153 (Question Templates)
    ├── DEV-154 (AtomicFacts Extension)
    └── DEV-157 (ChatResponse Schema)
```

### Phase 1 → Phase 2 Dependencies

```
DEV-151 (Template Loader)
    └── DEV-155 (ProactivityEngine)
            └── DEV-158 (/chat endpoint) ─── DEV-159 (/chat/stream)
                                         └── DEV-160 (/actions/execute)
                                         └── DEV-161 (/questions/answer)

DEV-156 (Analytics Model) ─── DEV-162 (Analytics Integration)
```

### Phase 2 → Phase 3 Dependencies

```
DEV-158, DEV-159 ─── DEV-163 (SuggestedActionsBar)
DEV-161 ─── DEV-164 (InteractiveQuestionInline)
DEV-164 ─── DEV-165 (useKeyboardNavigation)
DEV-163, DEV-164, DEV-165 ─── DEV-166 (Chat Integration)
DEV-166 ─── DEV-167 (Mobile Styling)
```

### Cross-Phase Critical Dependencies

| Downstream Task | Blocking Tasks |
|-----------------|----------------|
| DEV-155 (ProactivityEngine) | DEV-151, DEV-154 |
| DEV-158 (/chat with actions) | DEV-155, DEV-157 |
| DEV-166 (Chat Integration) | DEV-163, DEV-164, DEV-165 |
| DEV-172 (E2E Tests) | All Phase 1-3 tasks |

---

## Phase 1: Foundation (Backend) - 9h

### DEV-150: Create Pydantic Models for Actions and Interactive Questions

**Reference:** [Section 4.3: Data Models](./PRATIKO_1.5_REFERENCE.md#43-data-models)

**Priority:** CRITICAL | **Effort:** 0.5h | **Status:** NOT STARTED

**Problem:**
The system needs structured data models for suggested actions and interactive questions to ensure type safety and API contract clarity.

**Solution:**
Create Pydantic V2 models in `app/schemas/proactivity.py` defining Action, InteractiveQuestion, InteractiveOption, and ExtractedParameter schemas.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-151, DEV-154, DEV-155, DEV-157

**Change Classification:** ADDITIVE

**File:** `app/schemas/proactivity.py`

**Fields/Methods/Components:**
- `ActionCategory(str, Enum)` - CALCULATE, SEARCH, VERIFY, EXPORT, EXPLAIN
- `Action(BaseModel)` - id, label, icon, category, prompt_template, requires_input, input_placeholder, input_type
- `InteractiveOption(BaseModel)` - id, label, icon, leads_to, requires_input
- `InteractiveQuestion(BaseModel)` - id, trigger_query, text, question_type, options, allow_custom_input, custom_input_placeholder, prefilled_params
- `ExtractedParameter(BaseModel)` - name, value, confidence, source
- `ParameterExtractionResult(BaseModel)` - intent, extracted, missing_required, coverage, can_proceed

**Edge Cases:**
- **Empty options list:** Validation error, minimum 2 options required
- **Invalid confidence:** Must be 0.0-1.0 range
- **Missing required fields:** Pydantic validation error with clear message

**Testing Requirements:**
- **TDD:** Write `tests/schemas/test_proactivity.py` FIRST
- **Unit Tests:**
  - `test_action_validation` - Validate Action schema constraints
  - `test_interactive_question_options_required` - At least 2 options required
  - `test_extracted_parameter_confidence_range` - Confidence 0.0-1.0
  - `test_action_category_enum_values` - All enum values valid
- **Edge Case Tests:**
  - `test_action_empty_label_rejected` - Empty label not allowed
  - `test_question_single_option_rejected` - Single option rejected
- **Coverage Target:** 95%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema changes break API contracts | MEDIUM | Version schemas, use optional fields for additions |
| Pydantic V2 migration issues | LOW | Follow official migration guide |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All models use Pydantic V2 syntax
- [ ] JSON serialization works correctly
- [ ] Model validation provides clear error messages
- [ ] 95%+ test coverage achieved

---

### DEV-151: Create YAML Template Loader Service

**Reference:** [Section 4.4: Template Storage](./PRATIKO_1.5_REFERENCE.md#44-template-storage)

**Priority:** HIGH | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
Action and question templates need to be loaded from YAML files for version control and hot-reloading in development.

**Solution:**
Create ActionTemplateService that loads templates from `app/core/templates/`, caches in memory, and provides lookup by domain/action type.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-150
- **Unlocks:** DEV-152, DEV-153, DEV-155

**Change Classification:** ADDITIVE

**Error Handling:**
- Template file not found: WARNING log, return empty list, "Nessuna azione suggerita disponibile"
- Invalid YAML syntax: ERROR log, raise ConfigurationError, fail fast on startup
- Schema validation failure: ERROR log, skip invalid template, continue loading others
- **Logging:** All errors MUST be logged with context (template_path, domain, action_type) at ERROR level

**Performance Requirements:**
- Template lookup: <5ms (memory cache)
- Cold start load: <100ms for all templates

**Edge Cases:**
- **Empty templates:** Return empty action list, no error
- **Missing domain:** Fall back to 'default' domain templates
- **Hot reload:** File watcher in dev mode only (ENVIRONMENT != production)
- **Circular leads_to:** Detect and warn, break cycle
- **Duplicate IDs:** Last definition wins, log warning

**File:** `app/services/action_template_service.py`

**Fields/Methods/Components:**
- `ActionTemplateService` class with dependency injection
- `__init__(templates_path: Path)` - Initialize with configurable path
- `load_templates() -> dict[str, dict[str, list[Action]]]` - Load all YAML files
- `get_actions_for_domain(domain: str, action_type: str) -> list[Action]` - Lookup with fallback
- `get_actions_for_document(document_type: str) -> list[Action]` - Document-specific actions
- `reload_templates() -> None` - Force reload (dev mode)
- `_cache: dict` - In-memory template cache
- `_validate_templates(templates: dict) -> list[str]` - Return validation errors

**Testing Requirements:**
- **TDD:** Write `tests/services/test_action_template_service.py` FIRST
- **Unit Tests:**
  - `test_load_valid_yaml` - Successfully loads templates
  - `test_domain_fallback` - Falls back to default when domain not found
  - `test_cache_hit` - Second lookup uses cache
  - `test_document_type_lookup` - Document-specific actions returned
- **Edge Case Tests:**
  - `test_missing_file_graceful` - Handles missing files
  - `test_invalid_yaml_error` - Raises on syntax errors
  - `test_duplicate_id_warning` - Logs warning for duplicates
  - `test_empty_directory` - Returns empty dict, no error
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| YAML parsing errors on startup | HIGH | Validate on load, fail fast with clear message |
| Memory bloat from large templates | LOW | Templates are small (<1MB total expected) |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Templates loaded from YAML files
- [ ] Cache mechanism working
- [ ] Fallback to default domain works
- [ ] Clear error messages on validation failure
- [ ] 90%+ test coverage achieved

---

### DEV-152: Create Action Templates YAML Files

**Reference:** [Appendix A.1: Template Azioni per Documenti](./PRATIKO_1.5_REFERENCE.md#a1-template-azioni-per-documenti)

**Priority:** HIGH | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
The system needs predefined action templates for different domains (tax, labor, legal) and document types (fattura, F24, bilancio, CU).

**Solution:**
Create YAML template files in `app/core/templates/suggested_actions/` covering all scenarios defined in the requirements.

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-151
- **Unlocks:** DEV-155

**Change Classification:** ADDITIVE

**Files:**
- `app/core/templates/suggested_actions/tax.yaml`
- `app/core/templates/suggested_actions/labor.yaml`
- `app/core/templates/suggested_actions/legal.yaml`
- `app/core/templates/suggested_actions/documents.yaml`
- `app/core/templates/suggested_actions/default.yaml`

**Fields/Methods/Components:**
YAML structure for each template:
```yaml
domain: tax
actions:
  fiscal_calculation:
    - id: calculate_irpef
      label: Calcola IRPEF
      icon: calculate
      category: calculate
      prompt_template: "Calcola l'IRPEF per {tipo_contribuente} con reddito {reddito}"
      requires_input: false
    - id: recalculate
      label: Ricalcola
      icon: refresh
      category: calculate
      prompt_template: "Ricalcola con importo {amount}"
      requires_input: true
      input_placeholder: "Nuovo importo"
      input_type: number
```

**Edge Cases:**
- **Missing icon:** Use default icon per category
- **Empty prompt_template:** Use label as prompt
- **Special characters in prompts:** Escape properly

**Testing Requirements:**
- **Validation Tests:**
  - `test_all_templates_valid_yaml` - All YAML files parse correctly
  - `test_all_templates_match_schema` - All templates conform to Action schema
  - `test_no_duplicate_action_ids` - Action IDs unique within domain
  - `test_all_prompt_templates_have_placeholders` - Placeholders are valid

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Template syntax errors break loading | HIGH | Validate on startup, fail fast |
| Missing templates for scenarios | MEDIUM | Comprehensive coverage checklist |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] All document types covered (fattura, F24, bilancio, CU)
- [ ] All domains covered (tax, labor, legal)
- [ ] All templates validate against schema
- [ ] No duplicate action IDs
- [ ] Prompt templates use consistent placeholder format

---

### DEV-153: Create Interactive Question Templates YAML

**Reference:** [Appendix A.2: Template Domande Interattive](./PRATIKO_1.5_REFERENCE.md#a2-template-domande-interattive)

**Priority:** HIGH | **Effort:** 0.75h | **Status:** NOT STARTED

**Problem:**
Interactive questions for parameter clarification need predefined templates for common scenarios (IRPEF calculation, apertura attivita, regime fiscale).

**Solution:**
Create YAML template files in `app/core/templates/interactive_questions/` covering calculation and procedure scenarios.

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-151
- **Unlocks:** DEV-155

**Change Classification:** ADDITIVE

**Files:**
- `app/core/templates/interactive_questions/calculations.yaml`
- `app/core/templates/interactive_questions/procedures.yaml`
- `app/core/templates/interactive_questions/documents.yaml`

**Fields/Methods/Components:**
YAML structure for each template:
```yaml
questions:
  irpef_calculation:
    id: irpef_tipo_contribuente
    text: "Per quale tipo di contribuente vuoi calcolare l'IRPEF?"
    question_type: single_choice
    options:
      - id: dipendente
        label: "Persona fisica (dipendente)"
        icon: briefcase
        leads_to: irpef_income_input
      - id: autonomo
        label: "Persona fisica (autonomo/P.IVA)"
        icon: building
        leads_to: irpef_income_input
      - id: altro
        label: "Altro (specifica)"
        icon: edit
        requires_input: true
    allow_custom_input: true
    custom_input_placeholder: "Descrivi la situazione..."
```

**Edge Cases:**
- **Orphan leads_to:** Question references non-existent follow-up
- **Circular flows:** A leads to B leads to A
- **Missing default option:** Always include "Altro" option

**Testing Requirements:**
- **Validation Tests:**
  - `test_all_questions_valid_yaml` - All YAML files parse correctly
  - `test_all_questions_have_min_options` - At least 2 options per question
  - `test_question_flow_valid` - All leads_to references exist
  - `test_no_circular_flows` - No infinite loops in question flows

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular question flows | HIGH | Validate at load time, detect cycles |
| Orphan leads_to references | MEDIUM | Schema validation on startup |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] IRPEF calculation flow covered (tipo_contribuente -> reddito)
- [ ] Apertura attivita flow covered (tipo_attivita -> settore -> regime)
- [ ] Document classification questions covered
- [ ] All multi-step flows have valid leads_to references
- [ ] All questions include "Altro" option

---

### DEV-154: Extend AtomicFactsExtractor for Parameter Coverage

**Reference:** [FR-003: Smart Parameter Extraction](./PRATIKO_1.5_REFERENCE.md#33-fr-003-smart-parameter-extraction)

**Priority:** CRITICAL | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The existing AtomicFactsExtractor extracts facts but does not calculate parameter coverage against intent schemas to determine if a query is complete.

**Solution:**
Extend AtomicFactsExtractor to calculate coverage based on intent schemas and return ParameterExtractionResult with missing_required list.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-150
- **Unlocks:** DEV-155

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/services/atomic_facts_extractor.py`
- **Affected Files:**
  - `app/core/langgraph/nodes/atomic_facts_node.py` (uses extractor)
  - `app/orchestrators/classification.py` (may use coverage)
- **Related Tests:**
  - `tests/services/test_atomic_facts_extractor.py` (direct)
- **Baseline Command:** `pytest tests/services/test_atomic_facts_extractor.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing AtomicFacts dataclass reviewed
- [ ] No pre-existing test failures

**Error Handling:**
- Unknown intent: WARNING log, return coverage=0.0, "Tipo di richiesta non riconosciuto"
- Extraction failure: ERROR log, return empty result with can_proceed=True (smart fallback)
- Invalid number format: WARNING log, skip parameter, continue extraction
- **Logging:** All errors MUST be logged with context (query, intent, extracted_params)

**Performance Requirements:**
- Parameter extraction: <100ms
- Coverage calculation: <10ms

**Edge Cases:**
- **Partial parameters:** Return partial coverage (e.g., 0.5 for 1/2 params)
- **Optional vs required:** Only required params affect can_proceed
- **Italian number formats:** Support both 1.000,50 and 1000.50
- **Ambiguous values:** Use confidence score, low confidence (<0.7) doesn't count toward coverage
- **Multiple values for same param:** Take highest confidence
- **Unit variations:** Handle "euro", "EUR", "E" as equivalent

**File:** `app/services/atomic_facts_extractor.py`

**Fields/Methods/Components:**
- `INTENT_SCHEMAS: dict[str, IntentSchema]` - Schema definitions for each intent
- `IntentSchema(TypedDict)` - required, optional, defaults
- `calculate_coverage(intent: str, extracted: list[ExtractedParameter]) -> float`
- `get_missing_required(intent: str, extracted: list[ExtractedParameter]) -> list[str]`
- `extract_with_coverage(query: str, intent: str | None = None) -> ParameterExtractionResult`
- `_parse_italian_number(text: str) -> float | None` - Handle Italian format

Intent schemas to implement:
```python
INTENT_SCHEMAS = {
    "calcolo_irpef": {
        "required": ["tipo_contribuente", "reddito"],
        "optional": ["detrazioni", "anno_fiscale", "regione"],
        "defaults": {"anno_fiscale": 2025}
    },
    "calcolo_iva": {
        "required": ["importo"],
        "optional": ["aliquota", "tipo_operazione"],
        "defaults": {"aliquota": 22}
    },
    # ... additional schemas per requirements
}
```

**Testing Requirements:**
- **TDD:** Write new tests FIRST
- **Unit Tests:**
  - `test_irpef_full_coverage` - All params present returns 1.0
  - `test_irpef_partial_coverage` - Missing params returns <1.0
  - `test_italian_number_parsing` - Both formats work (1.000,50 and 1000.50)
  - `test_coverage_with_defaults` - Defaults don't count as missing
- **Edge Case Tests:**
  - `test_unknown_intent_zero_coverage` - Unknown intent handled gracefully
  - `test_optional_params_ignored` - Optional params don't affect can_proceed
  - `test_low_confidence_ignored` - Confidence <0.7 not counted
  - `test_multiple_values_highest_confidence` - Highest confidence wins
- **Regression Tests:** Run `pytest tests/services/test_atomic_facts_extractor.py`
- **Coverage Target:** 85%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing extraction | HIGH | Run full regression suite before merge |
| False positives in coverage | MEDIUM | Use confidence threshold, smart fallback |
| Italian number parsing edge cases | LOW | Comprehensive test suite for number formats |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Coverage calculation accurate to >=85%
- [ ] Italian number formats supported (both comma and period)
- [ ] Smart fallback for near-complete queries (coverage >= 0.8)
- [ ] All existing tests still pass (regression)
- [ ] 85%+ test coverage achieved

---

### DEV-155: Create ProactivityEngine Service

**Reference:** [Section 4.1: Componenti Sistema](./PRATIKO_1.5_REFERENCE.md#41-componenti-sistema)

**Priority:** CRITICAL | **Effort:** 2.5h | **Status:** NOT STARTED

**Problem:**
A central orchestrator is needed to coordinate parameter extraction, action selection, and interactive question generation.

**Solution:**
Create ProactivityEngine service that orchestrates all proactive features and returns appropriate actions or questions based on context.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-151, DEV-154
- **Unlocks:** DEV-158, DEV-159

**Change Classification:** ADDITIVE

**Error Handling:**
- Template service failure: WARNING log, return empty actions, continue with response
- Coverage check failure: WARNING log, assume can_proceed=True (smart fallback)
- Question generation failure: WARNING log, skip question, return actions only
- **Logging:** All operations MUST be logged with context (session_id, intent, coverage, action_count)

**Performance Requirements:**
- Full proactivity check: <500ms (requirement from spec)
- Action selection: <50ms
- Question generation: <100ms
- Coverage check: <10ms

**Edge Cases:**
- **No matching templates:** Return empty actions, log warning
- **Coverage threshold:** Use 1.0 for strict, 0.8 for smart fallback
- **Multi-step questions:** Track question_id in state for follow-ups
- **User ignores question:** Allow proceeding with generic response (smart fallback)
- **Document attached:** Prioritize document-specific actions
- **Streaming response:** Actions returned as final SSE event

**File:** `app/services/proactivity_engine.py`

**Fields/Methods/Components:**
- `ProactivityEngine` class with dependency injection
- `__init__(template_service: ActionTemplateService, facts_extractor: AtomicFactsExtractor)`
- `process(query: str, context: ProactivityContext) -> ProactivityResult`
- `select_actions(domain: str, action_type: str, document_type: str | None) -> list[Action]`
- `should_ask_question(extraction_result: ParameterExtractionResult) -> bool`
- `generate_question(intent: str, missing_params: list[str], prefilled: dict) -> InteractiveQuestion | None`
- `ProactivityContext(BaseModel)` - session_id, domain, action_type, document_type, user_history
- `ProactivityResult(BaseModel)` - actions, question, extraction_result, processing_time_ms

**Testing Requirements:**
- **TDD:** Write `tests/services/test_proactivity_engine.py` FIRST
- **Unit Tests:**
  - `test_complete_query_returns_actions` - Full coverage returns actions only
  - `test_incomplete_query_returns_question` - Low coverage triggers question
  - `test_smart_fallback` - Coverage >= 0.8 proceeds with generic response
  - `test_document_context_prioritizes_doc_actions` - Document actions first
- **Edge Case Tests:**
  - `test_template_failure_graceful` - Returns empty actions on failure
  - `test_multi_step_question_tracking` - Follow-up questions work
  - `test_performance_under_500ms` - Total processing time check
- **Integration Tests:** `tests/services/test_proactivity_engine_integration.py`
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance exceeds 500ms | HIGH | Parallel template loading, caching |
| Complex state for multi-step | MEDIUM | Use LangGraph checkpointer |
| Question overload annoys users | MEDIUM | Smart fallback at 0.8 coverage |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Actions returned for complete queries
- [ ] Questions returned for incomplete queries (coverage < 0.8)
- [ ] Smart fallback works for near-complete queries
- [ ] Performance under 500ms
- [ ] Document context influences action selection
- [ ] 90%+ test coverage achieved

---

### DEV-156: Create Analytics Tracking Model and Service

**Reference:** User Decision - Track all clicks in DB

**Priority:** MEDIUM | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
User interactions with suggested actions and interactive questions need to be tracked for analytics and future ML model training.

**Solution:**
Create SQLModel for tracking clicks and a service for recording events.

**Agent Assignment:** @ezio (primary), @primo (review), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-162

**Change Classification:** ADDITIVE

**Database Changes:**
1. Create model in `app/models/proactivity_analytics.py`
2. Import model in `alembic/env.py`
3. Generate migration: `alembic revision --autogenerate -m "add_proactivity_analytics"`
4. Add `import sqlmodel` to generated migration
5. Test migration: `alembic upgrade head` (Docker DB)
6. Test rollback: `alembic downgrade -1`

**Error Handling:**
- DB write failure: WARNING log, do not raise (analytics non-blocking)
- Invalid user_id: Skip tracking, log warning
- **Logging:** Log all tracking attempts with context (session_id, action_id)

**Performance Requirements:**
- Track operation: <50ms (non-blocking)
- No impact on response latency

**Edge Cases:**
- **Anonymous user:** Track with user_id=None
- **Rapid clicks:** Debounce at 300ms
- **Concurrent tracking:** Use async, non-blocking writes

**File:** `app/models/proactivity_analytics.py`

**Fields/Methods/Components:**
```python
class SuggestedActionClick(SQLModel, table=True):
    __tablename__ = "suggested_action_clicks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: str = Field(index=True)
    user_id: int | None = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    action_template_id: str = Field(index=True)
    action_label: str
    domain: str | None
    clicked_at: datetime = Field(default_factory=datetime.utcnow)
    context_hash: str | None  # For grouping similar contexts

class InteractiveQuestionAnswer(SQLModel, table=True):
    __tablename__ = "interactive_question_answers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: str = Field(index=True)
    user_id: int | None = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    question_id: str = Field(index=True)
    selected_option: str
    custom_input: str | None
    answered_at: datetime = Field(default_factory=datetime.utcnow)
```

**File:** `app/services/proactivity_analytics_service.py`

**Fields/Methods/Components:**
- `ProactivityAnalyticsService` class
- `track_action_click(session_id: str, user_id: int | None, action: Action, context_hash: str | None) -> None`
- `track_question_answer(session_id: str, user_id: int | None, question_id: str, option_id: str, custom_input: str | None) -> None`
- `get_popular_actions(domain: str, limit: int = 10) -> list[ActionStats]` - For future ML

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_track_action_click_creates_record` - Record created in DB
  - `test_track_question_answer_creates_record` - Record created in DB
  - `test_track_anonymous_user` - Works with user_id=None
- **Edge Case Tests:**
  - `test_db_failure_non_blocking` - Failure doesn't raise
  - `test_cascade_delete_on_user` - Records deleted when user deleted
- **Coverage Target:** 85%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Analytics slows response | HIGH | Async non-blocking writes |
| GDPR deletion incomplete | HIGH | ON DELETE CASCADE on user_id FK |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Migration runs successfully
- [ ] Rollback works
- [ ] GDPR: user_id ON DELETE CASCADE
- [ ] Non-blocking writes (no response latency impact)
- [ ] 85%+ test coverage achieved

---

## Phase 2: API Integration (Backend) - 6h

### DEV-157: Extend ChatResponse Schema with Actions/Questions

**Reference:** [Section 4.2: API Endpoints](./PRATIKO_1.5_REFERENCE.md#42-api-endpoints)

**Priority:** HIGH | **Effort:** 0.5h | **Status:** NOT STARTED

**Problem:**
The ChatResponse schema needs to be extended to include suggested_actions and interactive_question fields.

**Solution:**
Add optional fields to ChatResponse schema in a backward-compatible way.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-150
- **Unlocks:** DEV-158, DEV-159

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/schemas/chat.py`
- **Affected Files:**
  - `app/api/v1/chatbot.py` (returns ChatResponse)
  - Frontend API client (consumes ChatResponse)
- **Related Tests:**
  - `tests/schemas/test_chat.py` (direct)
  - `tests/api/test_chatbot.py` (consumer)
- **Baseline Command:** `pytest tests/schemas/test_chat.py tests/api/test_chatbot.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing ChatResponse usage reviewed
- [ ] No pre-existing test failures

**File:** `app/schemas/chat.py`

**Fields/Methods/Components:**
Add to `ChatResponse`:
```python
suggested_actions: list[Action] | None = None
interactive_question: InteractiveQuestion | None = None
extracted_params: dict[str, Any] | None = None  # For parameter confirmation
```

**Edge Cases:**
- **Both actions and question:** Valid state (show actions after question answered)
- **Neither actions nor question:** Valid state (system error or disabled feature)
- **Serialization of None:** Must serialize as absent, not null

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_chat_response_backward_compatible` - Old clients work without new fields
  - `test_chat_response_with_actions` - New fields serialize correctly
  - `test_chat_response_both_fields` - Actions and question together
- **Regression Tests:** Run full test suite for chatbot module
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing API contracts | HIGH | Use optional fields, version carefully |
| Frontend incompatibility | MEDIUM | Coordinate with frontend team |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Backward compatible (optional fields)
- [ ] All existing tests pass
- [ ] 90%+ test coverage achieved

---

### DEV-158: Modify /chat Endpoint to Include Suggested Actions

**Reference:** [Section 4.2: API Endpoints](./PRATIKO_1.5_REFERENCE.md#42-api-endpoints)

**Priority:** CRITICAL | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
The /chat endpoint needs to integrate ProactivityEngine to return suggested actions with each response.

**Solution:**
Modify chat endpoint to call ProactivityEngine after generating response and include actions in ChatResponse.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-155, DEV-157
- **Unlocks:** DEV-159, DEV-160, DEV-161

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/api/v1/chatbot.py`
- **Affected Files:**
  - `app/services/chat_service.py` (may need modification)
  - Frontend chat component (consumes response)
- **Related Tests:**
  - `tests/api/test_chatbot.py` (direct)
- **Baseline Command:** `pytest tests/api/test_chatbot.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing /chat flow reviewed
- [ ] No pre-existing test failures

**Error Handling:**
- ProactivityEngine failure: WARNING log, return response without actions
- Timeout: Return response without actions if proactivity exceeds 500ms
- **Logging:** Log action selection with context (session_id, domain, action_count)

**Performance Requirements:**
- Total endpoint latency: <=500ms additional overhead (per spec)

**File:** `app/api/v1/chatbot.py`

**Fields/Methods/Components:**
Modify `/chat` endpoint:
```python
@router.post("/chat")
async def chat(
    request: ChatRequest,
    proactivity_engine: ProactivityEngine = Depends(get_proactivity_engine),
    # ... existing deps
) -> ChatResponse:
    # ... existing chat logic

    # Add proactivity processing
    proactivity_result = await proactivity_engine.process(
        query=request.message,
        context=ProactivityContext(
            session_id=request.session_id,
            domain=classification.domain,
            action_type=classification.action_type,
            document_type=document_type,
        )
    )

    return ChatResponse(
        # ... existing fields
        suggested_actions=proactivity_result.actions,
        interactive_question=proactivity_result.question,
        extracted_params=proactivity_result.extraction_result.extracted if proactivity_result.extraction_result else None,
    )
```

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_chat_returns_actions` - Actions included in response
  - `test_chat_without_actions_on_error` - Graceful degradation
  - `test_chat_with_question` - Question returned when coverage low
- **Integration Tests:** `tests/api/test_chatbot_proactivity.py`
- **Regression Tests:** Run `pytest tests/api/test_chatbot.py`
- **Coverage Target:** 85%+

**Edge Cases:**
- **ProactivityEngine timeout:** Return response without actions
- **Empty actions list:** Valid state, render empty suggestion bar
- **Document upload with query:** Prioritize document-specific actions

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance degradation | HIGH | Async proactivity, timeout fallback |
| Breaking existing chat flow | HIGH | Feature flag, gradual rollout |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Actions returned with each response
- [ ] Latency under 500ms overhead
- [ ] Graceful degradation on error
- [ ] All existing tests pass
- [ ] 85%+ test coverage achieved

---

### DEV-159: Modify /chat/stream Endpoint for Actions

**Reference:** [Section 4.2: API Endpoints](./PRATIKO_1.5_REFERENCE.md#42-api-endpoints)

**Priority:** HIGH | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
The streaming endpoint needs to include suggested actions as a final SSE event after the response is complete.

**Solution:**
Modify /chat/stream to send actions as a structured SSE event after the [DONE] token.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-158
- **Unlocks:** DEV-163

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/api/v1/chatbot.py`
- **Affected Files:**
  - Frontend SSE handler
- **Related Tests:**
  - `tests/api/test_chatbot_stream.py` (direct)
- **Baseline Command:** `pytest tests/api/test_chatbot_stream.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing streaming flow reviewed
- [ ] No pre-existing test failures

**Error Handling:**
- Stream interrupted before actions: Log warning, no recovery needed
- **Logging:** Log streaming completion with action count

**Performance Requirements:**
- Actions event latency: <100ms after response complete

**File:** `app/api/v1/chatbot.py`

**Fields/Methods/Components:**
SSE event format for actions:
```
data: {"type": "content", "content": "Response text..."}
data: {"type": "content", "content": " more text"}
data: {"type": "suggested_actions", "actions": [...]}
data: {"type": "interactive_question", "question": {...}}  // if applicable
data: [DONE]
```

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_stream_includes_actions_event` - Actions sent as SSE event
  - `test_stream_actions_after_content` - Actions come after content
  - `test_stream_with_question` - Question event when needed
- **Regression Tests:** Run `pytest tests/api/test_chatbot_stream.py`
- **Coverage Target:** 85%+

**Edge Cases:**
- **Client disconnects early:** Clean up gracefully, no action event sent
- **Empty actions:** Send empty actions array, not null
- **Streaming error mid-response:** Log error, attempt to send actions anyway

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| SSE format incompatibility | HIGH | Test with frontend before deployment |
| Event ordering issues | MEDIUM | Strict sequence validation in tests |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Actions sent as structured SSE event
- [ ] Event order: content -> actions -> question -> [DONE]
- [ ] All existing streaming tests pass
- [ ] 85%+ test coverage achieved

---

### DEV-160: Create /actions/execute Endpoint

**Reference:** [Section 4.2: API Endpoints](./PRATIKO_1.5_REFERENCE.md#42-api-endpoints)

**Priority:** HIGH | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
When a user clicks a suggested action, the system needs an endpoint to execute that action and return a response.

**Solution:**
Create POST /api/v1/chatbot/actions/execute endpoint that takes action_id and optional parameters.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-158
- **Unlocks:** DEV-162, DEV-163

**Change Classification:** ADDITIVE

**Error Handling:**
- Unknown action_id: HTTP 400, "Azione non valida"
- Missing required input: HTTP 400, "Parametro richiesto mancante: {param}"
- **Logging:** Log action execution with context (session_id, action_id, input_provided)

**Performance Requirements:**
- Action execution: Same as /chat endpoint (response within 3s)

**File:** `app/api/v1/chatbot.py`

**Fields/Methods/Components:**
```python
class ActionExecuteRequest(BaseModel):
    action_id: str
    parameters: dict[str, Any] | None = None
    session_id: str

@router.post("/actions/execute")
async def execute_action(
    request: ActionExecuteRequest,
    # ... deps
) -> ChatResponse:
    # 1. Lookup action template
    # 2. Fill prompt_template with parameters
    # 3. Execute as regular chat query
    # 4. Return ChatResponse with new actions
```

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_execute_action_valid` - Action executes successfully
  - `test_execute_action_with_params` - Parameters substituted correctly
  - `test_execute_action_invalid_id` - 400 error for unknown action
  - `test_execute_action_missing_input` - 400 error when input required but missing
- **Integration Tests:** `tests/api/test_chatbot_actions.py`
- **Coverage Target:** 85%+

**Edge Cases:**
- **Action template not found:** Return 404 with helpful message
- **Parameter type mismatch:** Validate before substitution
- **Concurrent action execution:** Handle session state correctly

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Invalid prompt generation | MEDIUM | Template validation at load time |
| Session state corruption | LOW | Stateless action execution |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Action template looked up and executed
- [ ] Parameters substituted in prompt_template
- [ ] Returns full ChatResponse with new actions
- [ ] Proper error handling for invalid requests
- [ ] 85%+ test coverage achieved

---

### DEV-161: Create /questions/answer Endpoint

**Reference:** [Section 4.2: API Endpoints](./PRATIKO_1.5_REFERENCE.md#42-api-endpoints)

**Priority:** HIGH | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
When a user answers an interactive question, the system needs an endpoint to process the answer and continue the flow.

**Solution:**
Create POST /api/v1/chatbot/questions/answer endpoint that processes the selected option.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-158
- **Unlocks:** DEV-162, DEV-164

**Change Classification:** ADDITIVE

**Error Handling:**
- Unknown question_id: HTTP 400, "Domanda non valida"
- Unknown option_id: HTTP 400, "Opzione non valida"
- Custom input required but empty: HTTP 400, "Input personalizzato richiesto"
- **Logging:** Log question answer with context (session_id, question_id, option_id)

**Performance Requirements:**
- Answer processing: <500ms

**File:** `app/api/v1/chatbot.py`

**Fields/Methods/Components:**
```python
class QuestionAnswerRequest(BaseModel):
    question_id: str
    selected_option: str
    custom_input: str | None = None
    session_id: str

class QuestionAnswerResponse(BaseModel):
    next_question: InteractiveQuestion | None = None
    answer: str | None = None
    suggested_actions: list[Action] | None = None

@router.post("/questions/answer")
async def answer_question(
    request: QuestionAnswerRequest,
    # ... deps
) -> QuestionAnswerResponse:
    # 1. Validate question and option
    # 2. If leads_to exists, return next question
    # 3. If terminal, process with extracted params and return answer
```

**Testing Requirements:**
- **TDD:** Write tests FIRST
- **Unit Tests:**
  - `test_answer_question_single_step` - Single question returns answer
  - `test_answer_question_multi_step` - Multi-step returns next question
  - `test_answer_question_custom_input` - Custom input processed
  - `test_answer_question_invalid` - 400 error for invalid question/option
- **Integration Tests:** `tests/api/test_chatbot_questions.py`
- **Coverage Target:** 85%+

**Edge Cases:**
- **Question flow ends unexpectedly:** Return error with context
- **Custom input validation:** Sanitize user input
- **Multi-step flow timeout:** Handle abandoned flows gracefully

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Infinite question loops | HIGH | Validate flows at template load |
| State management complexity | MEDIUM | Use LangGraph checkpointer |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Single-step questions return direct answer
- [ ] Multi-step questions return next question
- [ ] Custom input captured and used
- [ ] Proper error handling for invalid requests
- [ ] 85%+ test coverage achieved

---

### DEV-162: Add Analytics Tracking to Action/Question Endpoints

**Reference:** User Decision - Track all clicks in DB

**Priority:** MEDIUM | **Effort:** 0.5h | **Status:** NOT STARTED

**Problem:**
Action clicks and question answers need to be tracked for analytics.

**Solution:**
Integrate ProactivityAnalyticsService into /actions/execute and /questions/answer endpoints.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-156, DEV-160, DEV-161
- **Unlocks:** None

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary Files:** `app/api/v1/chatbot.py`
- **Affected Files:** None
- **Related Tests:**
  - `tests/api/test_chatbot_actions.py`
  - `tests/api/test_chatbot_questions.py`
- **Baseline Command:** `pytest tests/api/test_chatbot_actions.py tests/api/test_chatbot_questions.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Analytics service tested independently
- [ ] No pre-existing test failures

**File:** `app/api/v1/chatbot.py`

**Fields/Methods/Components:**
Add to execute_action:
```python
await analytics_service.track_action_click(
    session_id=request.session_id,
    user_id=current_user.id if current_user else None,
    action=action,
    context_hash=context_hash,
)
```

Add to answer_question:
```python
await analytics_service.track_question_answer(
    session_id=request.session_id,
    user_id=current_user.id if current_user else None,
    question_id=request.question_id,
    option_id=request.selected_option,
    custom_input=request.custom_input,
)
```

**Testing Requirements:**
- **Unit Tests:**
  - `test_action_click_tracked` - Analytics called on action execute
  - `test_question_answer_tracked` - Analytics called on question answer
  - `test_analytics_failure_non_blocking` - Endpoint works even if analytics fails
- **Coverage Target:** 85%+

**Edge Cases:**
- **Analytics service unavailable:** Continue endpoint execution, log warning
- **Duplicate tracking calls:** Idempotent writes, use session_id + timestamp
- **High traffic burst:** Async non-blocking writes handle load

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Analytics slows endpoint response | HIGH | Fire-and-forget async writes |
| Missing analytics data | LOW | Log failures for manual review |
| GDPR compliance issues | MEDIUM | Ensure CASCADE delete on user_id |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Action clicks tracked in DB
- [ ] Question answers tracked in DB
- [ ] Analytics failure does not block response
- [ ] 85%+ test coverage achieved

---

## Phase 3: Frontend Components - 10h

### DEV-163: Create SuggestedActionsBar Component

**Reference:** [Section 5.1: Action Buttons Design](./PRATIKO_1.5_REFERENCE.md#51-action-buttons-design)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The frontend needs a component to render suggested action buttons after AI responses.

**Solution:**
Create SuggestedActionsBar React component with keyboard navigation support.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-158
- **Unlocks:** DEV-166

**Change Classification:** ADDITIVE

**Performance Requirements:**
- Render time: <50ms
- Keyboard navigation response: <16ms (60fps)

**Edge Cases:**
- **Empty actions:** Don't render component
- **Single action:** Still show as button bar
- **Action with input:** Show inline input field on click
- **Mobile:** Stack vertically, touch-friendly targets

**File:** `src/components/chat/SuggestedActionsBar.tsx`

**Fields/Methods/Components:**
```typescript
interface SuggestedActionsBarProps {
  actions: Action[];
  onActionClick: (action: Action, input?: string) => void;
  disabled?: boolean;
}

export function SuggestedActionsBar({ actions, onActionClick, disabled }: SuggestedActionsBarProps) {
  // Render 2-4 action buttons
  // Handle keyboard navigation (Tab, Enter)
  // Show input field when requires_input
}
```

Component structure:
- Action buttons with icons
- Inline input field for actions requiring input
- Loading state while action executes
- Keyboard navigation with Tab/Enter

**Testing Requirements:**
- **Unit Tests:**
  - `test_renders_action_buttons` - Buttons rendered for each action
  - `test_keyboard_navigation` - Tab navigates, Enter selects
  - `test_input_field_shown` - Input shown for requires_input actions
  - `test_empty_actions_no_render` - Nothing rendered for empty array
- **Coverage Target:** 85%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Keyboard navigation conflicts | MEDIUM | Use proper event handling, stopPropagation |
| Accessibility issues | HIGH | Follow WAI-ARIA patterns, test with screen readers |
| Performance on many actions | LOW | Limit to 4 actions max, virtualize if needed |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max component: 150 lines, extract sub-components
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Action buttons rendered with icons and labels
- [ ] Click triggers onActionClick callback
- [ ] Keyboard navigation works (Tab, Enter)
- [ ] Input field shown for actions requiring input
- [ ] Mobile responsive (stacked layout)
- [ ] 85%+ test coverage achieved

---

### DEV-164: Create InteractiveQuestionInline Component

**Reference:** [Section 5.2: Interactive Question Modal](./PRATIKO_1.5_REFERENCE.md#52-interactive-question-modal)

**Priority:** HIGH | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
The frontend needs a component to render interactive questions inline in the chat, Claude Code style.

**Solution:**
Create InteractiveQuestionInline React component with keyboard navigation and option selection.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-161
- **Unlocks:** DEV-166

**Change Classification:** ADDITIVE

**Performance Requirements:**
- Render time: <50ms
- Keyboard navigation response: <16ms (60fps)

**Edge Cases:**
- **Single option:** Still show as selectable (user can type custom)
- **Custom input selected:** Show text input field
- **Long option labels:** Truncate with ellipsis, show full on hover
- **Mobile:** Full-width options, touch-friendly

**File:** `src/components/chat/InteractiveQuestionInline.tsx`

**Fields/Methods/Components:**
```typescript
interface InteractiveQuestionInlineProps {
  question: InteractiveQuestion;
  onAnswer: (optionId: string, customInput?: string) => void;
  onSkip?: () => void;
  disabled?: boolean;
}

export function InteractiveQuestionInline({
  question,
  onAnswer,
  onSkip,
  disabled
}: InteractiveQuestionInlineProps) {
  // Render question text
  // Render options as selectable items (Claude Code style)
  // Handle keyboard navigation (arrows, numbers, Enter)
  // Show custom input field when "Altro" selected
}
```

Component structure:
- Question text at top
- Options as radio-button style items
- Number shortcuts (1, 2, 3, 4) for selection
- Custom input field when allow_custom_input
- Skip button (Esc)

**Testing Requirements:**
- **Unit Tests:**
  - `test_renders_question_and_options` - Question and all options rendered
  - `test_keyboard_selection` - Arrow keys and numbers work
  - `test_custom_input_shown` - Input shown when "Altro" selected
  - `test_skip_button` - Skip triggers onSkip callback
- **Accessibility Tests:**
  - `test_aria_labels` - Proper ARIA labels for screen readers
  - `test_focus_management` - Focus trapped within component
- **Coverage Target:** 85%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex state management | MEDIUM | Use useReducer for state transitions |
| Focus management issues | HIGH | Implement focus trap, test thoroughly |
| Long text overflow | LOW | Truncate with ellipsis, full text on hover |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max component: 150 lines, extract sub-components
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Question and options rendered Claude Code style
- [ ] Keyboard navigation works (arrows, numbers, Enter, Esc)
- [ ] Custom input field for "Altro" option
- [ ] Skip functionality with Esc key
- [ ] Accessible with screen readers
- [ ] Mobile responsive
- [ ] 85%+ test coverage achieved

---

### DEV-165: Create useKeyboardNavigation Hook

**Reference:** [Section 5.2: Interactive Question Modal](./PRATIKO_1.5_REFERENCE.md#52-interactive-question-modal)

**Priority:** MEDIUM | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
Both action buttons and interactive questions need keyboard navigation, requiring a reusable hook.

**Solution:**
Create useKeyboardNavigation custom hook for managing keyboard navigation state.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-164
- **Unlocks:** DEV-166

**Change Classification:** ADDITIVE

**File:** `src/lib/hooks/useKeyboardNavigation.ts`

**Fields/Methods/Components:**
```typescript
interface UseKeyboardNavigationOptions {
  items: string[];  // Item IDs
  onSelect: (itemId: string) => void;
  onCancel?: () => void;
  enabled?: boolean;
  initialIndex?: number;
}

interface UseKeyboardNavigationReturn {
  selectedIndex: number;
  setSelectedIndex: (index: number) => void;
  handleKeyDown: (event: KeyboardEvent) => void;
}

export function useKeyboardNavigation({
  items,
  onSelect,
  onCancel,
  enabled = true,
  initialIndex = 0,
}: UseKeyboardNavigationOptions): UseKeyboardNavigationReturn {
  // Handle arrow keys for navigation
  // Handle Enter for selection
  // Handle Escape for cancel
  // Handle number keys (1-9) for direct selection
}
```

**Testing Requirements:**
- **Unit Tests:**
  - `test_arrow_key_navigation` - Up/Down changes selected index
  - `test_enter_selects` - Enter triggers onSelect
  - `test_escape_cancels` - Escape triggers onCancel
  - `test_number_keys` - 1-4 directly select options
  - `test_wraparound` - Navigation wraps at boundaries
- **Coverage Target:** 90%+

**Edge Cases:**
- **Empty items array:** No-op, return immediately
- **Disabled state:** Ignore all keyboard events
- **Rapid key presses:** Debounce to prevent double selection
- **Focus lost:** Clean up event listeners properly

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Event listener memory leaks | MEDIUM | Proper cleanup in useEffect return |
| Keyboard conflicts with inputs | MEDIUM | Check activeElement before handling |
| Browser-specific key codes | LOW | Use standardized key values |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max hook: 50 lines, single concern
- Max file: 100 lines, keep focused

**Acceptance Criteria:**
- [ ] Arrow keys navigate up/down
- [ ] Enter selects current item
- [ ] Escape cancels/closes
- [ ] Number keys (1-4) select directly
- [ ] Navigation wraps around
- [ ] 90%+ test coverage achieved

---

### DEV-166: Integrate Components into ChatInterface

**Reference:** [FR-001: Azioni Suggerite Post-Risposta](./PRATIKO_1.5_REFERENCE.md#31-fr-001-azioni-suggerite-post-risposta) | [FR-002: Domande Interattive Strutturate](./PRATIKO_1.5_REFERENCE.md#32-fr-002-domande-interattive-strutturate)

**Priority:** CRITICAL | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The new proactivity components need to be integrated into the existing chat interface.

**Solution:**
Modify ChatLayoutV2 and AIMessageV2 to include SuggestedActionsBar and InteractiveQuestionInline.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-163, DEV-164, DEV-165
- **Unlocks:** DEV-167

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary Files:**
  - `src/app/chat/ChatLayoutV2.tsx`
  - `src/app/chat/AIMessageV2.tsx`
- **Affected Files:**
  - `src/contexts/ChatContext.tsx` (state management)
- **Related Tests:**
  - `src/__tests__/chat/` (existing chat tests)
- **Baseline Command:** `npm test -- --testPathPattern=chat`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing chat flow reviewed
- [ ] No pre-existing test failures

**File:** `src/app/chat/AIMessageV2.tsx`

**Fields/Methods/Components:**
Add to AIMessageV2:
```typescript
interface AIMessageV2Props {
  // ... existing props
  suggestedActions?: Action[];
  interactiveQuestion?: InteractiveQuestion;
}

// Render SuggestedActionsBar after message content
// Render InteractiveQuestionInline when question present
```

Add to ChatContext:
```typescript
interface ChatState {
  // ... existing state
  pendingQuestion: InteractiveQuestion | null;
  isActionExecuting: boolean;
}
```

**Testing Requirements:**
- **Integration Tests:**
  - `test_actions_shown_after_message` - Actions render after AI message
  - `test_question_shown_when_present` - Question renders inline
  - `test_action_click_triggers_api` - Click calls /actions/execute
  - `test_question_answer_triggers_api` - Answer calls /questions/answer
- **E2E Tests:** (DEV-172)
- **Coverage Target:** 85%+

**Edge Cases:**
- **Actions and question both present:** Show question first, actions after answer
- **API call fails:** Show error toast, keep UI responsive
- **Rapid clicks:** Disable buttons during API call
- **Stale state:** Invalidate actions when new message received

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing chat functionality | HIGH | Comprehensive regression tests |
| State synchronization issues | MEDIUM | Use ChatContext reducer pattern |
| Performance degradation | MEDIUM | Lazy load proactivity components |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max component: 150 lines, extract sub-components
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] SuggestedActionsBar appears after AI messages
- [ ] InteractiveQuestionInline appears when question present
- [ ] Action clicks call backend API
- [ ] Question answers call backend API
- [ ] Loading states shown during API calls
- [ ] Error states handled gracefully
- [ ] 85%+ test coverage achieved

---

### DEV-167: Mobile Responsive Styling

**Reference:** [Section 5.3: Mobile Responsive](./PRATIKO_1.5_REFERENCE.md#53-mobile-responsive)

**Priority:** MEDIUM | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
The proactivity components need to work well on mobile devices.

**Solution:**
Add responsive styles and ensure touch-friendly interactions.

**Agent Assignment:** @livia (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-166
- **Unlocks:** None

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary Files:**
  - `src/components/chat/SuggestedActionsBar.tsx`
  - `src/components/chat/InteractiveQuestionInline.tsx`
- **Related Tests:**
  - Component tests with mobile viewport
- **Baseline Command:** `npm test -- --testPathPattern=SuggestedActionsBar --testPathPattern=InteractiveQuestionInline`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing responsive breakpoints reviewed
- [ ] No pre-existing visual regressions

**Edge Cases:**
- **Small screens (<375px):** Single column layout
- **Touch targets:** Minimum 44px height
- **Keyboard on mobile:** Component should scroll into view
- **Landscape mode:** Optimize for horizontal space
- **Very long labels:** Text truncation with ellipsis

**Testing Requirements:**
- **Visual Tests:**
  - Test at 320px, 375px, 768px, 1024px viewports
  - Touch target size verification
- **Accessibility Tests:**
  - Focus visible on touch devices
  - Swipe gestures don't interfere

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking desktop layout | MEDIUM | Test all breakpoints before merge |
| Touch target overlap | LOW | Use spacing utilities, test touch accuracy |
| CSS specificity conflicts | LOW | Use Tailwind utility classes consistently |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max component: 150 lines, extract sub-components
- Max file: 400 lines, create submodules

**Acceptance Criteria:**
- [ ] Actions stack vertically on mobile
- [ ] Question options full-width on mobile
- [ ] Touch targets minimum 44px
- [ ] No horizontal scroll on mobile
- [ ] Keyboard doesn't obscure input fields

---

## Phase 4: Testing - 6.5h

### DEV-168: Unit Tests for ProactivityEngine

**Reference:** DEV-155

**Priority:** HIGH | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
ProactivityEngine needs comprehensive unit tests to ensure reliability.

**Solution:**
Write extensive unit tests covering all scenarios and edge cases.

**Agent Assignment:** @clelia (primary)

**Dependencies:**
- **Blocking:** DEV-155
- **Unlocks:** DEV-172

**Change Classification:** ADDITIVE

**File:** `tests/services/test_proactivity_engine.py`

**Testing Requirements:**
- **Coverage Scenarios:**
  - Complete query (all params) -> actions only
  - Incomplete query (0% coverage) -> question
  - Partial query (50% coverage) -> question
  - Near-complete query (80% coverage) -> smart fallback
  - Template service failure -> graceful degradation
  - Multiple domains -> correct template selection
  - Document attached -> document-specific actions
  - Performance under 500ms

**Edge Cases:**
- **Mocking LLM responses:** Use deterministic mock responses
- **Async timing issues:** Use proper async test patterns
- **Flaky tests:** Avoid time-dependent assertions

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Tests too tightly coupled | MEDIUM | Test behaviors, not implementation |
| Insufficient coverage | HIGH | Use coverage tools, enforce threshold |
| Slow test suite | LOW | Mock external dependencies |

**Code Structure:**
- Max test function: 30 lines
- Group tests by feature/scenario
- Use fixtures for common setup

**Acceptance Criteria:**
- [ ] 90%+ code coverage for ProactivityEngine
- [ ] All edge cases tested
- [ ] Performance assertions included
- [ ] Mock dependencies properly

---

### DEV-169: Unit Tests for Template Services

**Reference:** DEV-151

**Priority:** HIGH | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
Template loading services need comprehensive tests.

**Solution:**
Write unit tests for ActionTemplateService and question template loading.

**Agent Assignment:** @clelia (primary)

**Dependencies:**
- **Blocking:** DEV-151
- **Unlocks:** DEV-172

**Change Classification:** ADDITIVE

**File:** `tests/services/test_action_template_service.py`

**Testing Requirements:**
- **Coverage Scenarios:**
  - Valid YAML loading
  - Invalid YAML handling
  - Missing file handling
  - Domain fallback
  - Cache hit verification
  - Hot reload (dev mode)
  - Schema validation

**Edge Cases:**
- **Empty YAML files:** Should handle gracefully
- **Malformed YAML:** Clear error messages
- **File permission errors:** Handle OS-level issues

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Fixture files out of sync | MEDIUM | Version fixtures with tests |
| File system dependencies | LOW | Use temp directories in tests |
| Cache state pollution | MEDIUM | Reset cache between tests |

**Code Structure:**
- Max test function: 30 lines
- Group tests by feature/scenario
- Use fixtures for common setup

**Acceptance Criteria:**
- [ ] 90%+ code coverage for template services
- [ ] All edge cases tested
- [ ] Fixture YAML files created for tests

---

### DEV-170: Integration Tests for Chat Endpoints

**Reference:** DEV-158, DEV-159, DEV-160, DEV-161

**Priority:** HIGH | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
Chat endpoints with proactivity features need integration tests.

**Solution:**
Write integration tests that test the full flow from API to database.

**Agent Assignment:** @clelia (primary)

**Dependencies:**
- **Blocking:** DEV-159
- **Unlocks:** DEV-172

**Change Classification:** ADDITIVE

**File:** `tests/api/test_chatbot_proactivity_integration.py`

**Testing Requirements:**
- **Coverage Scenarios:**
  - /chat returns actions
  - /chat returns question when params missing
  - /chat/stream includes action event
  - /actions/execute processes action
  - /questions/answer handles single-step
  - /questions/answer handles multi-step
  - Analytics recorded for all interactions

**Edge Cases:**
- **Database connection failures:** Graceful handling
- **Concurrent requests:** Test race conditions
- **Large payload responses:** Handle streaming correctly

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Flaky integration tests | HIGH | Use transaction rollback, proper cleanup |
| Slow test execution | MEDIUM | Parallelize independent tests |
| DB state pollution | HIGH | Isolate each test with fresh data |

**Code Structure:**
- Max test function: 50 lines (integration tests may be longer)
- Group tests by endpoint
- Use pytest fixtures for DB setup

**Acceptance Criteria:**
- [ ] Full flow tested (API -> Service -> DB)
- [ ] Docker DB used for tests
- [ ] Cleanup after each test
- [ ] Performance assertions included

---

### DEV-171: Frontend Component Tests

**Reference:** DEV-163, DEV-164, DEV-165, DEV-166

**Priority:** HIGH | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
Frontend components need unit and integration tests.

**Solution:**
Write Jest tests for all new components.

**Agent Assignment:** @clelia (primary)

**Dependencies:**
- **Blocking:** DEV-166
- **Unlocks:** DEV-172

**Change Classification:** ADDITIVE

**Files:**
- `src/__tests__/components/SuggestedActionsBar.test.tsx`
- `src/__tests__/components/InteractiveQuestionInline.test.tsx`
- `src/__tests__/hooks/useKeyboardNavigation.test.ts`

**Testing Requirements:**
- **Coverage Scenarios:**
  - Component rendering
  - User interactions (click, keyboard)
  - Props variations
  - Error states
  - Loading states
  - Mobile viewport

**Edge Cases:**
- **Component unmounting during async:** Cleanup handlers properly
- **Viewport resize during test:** Handle responsive behavior
- **Focus management edge cases:** Tab trap scenarios

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Snapshot test brittleness | MEDIUM | Use semantic selectors, not snapshots |
| Mock implementation drift | LOW | Keep mocks close to real behavior |
| Test isolation issues | MEDIUM | Reset all mocks between tests |

**Code Structure:**
- Max test function: 30 lines
- Group tests by component
- Use React Testing Library best practices

**Acceptance Criteria:**
- [ ] 85%+ coverage for new components
- [ ] Keyboard interactions tested
- [ ] Accessibility tested
- [ ] Mobile viewport tested

---

### DEV-172: E2E Tests for Proactive Flows

**Reference:** All proactivity features

**Priority:** MEDIUM | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
End-to-end testing needed to verify complete user flows.

**Solution:**
Write Playwright E2E tests for proactive features.

**Agent Assignment:** @clelia (primary)

**Dependencies:**
- **Blocking:** DEV-170, DEV-171
- **Unlocks:** None

**Change Classification:** ADDITIVE

**File:** `e2e/proactivity.spec.ts`

**Testing Requirements:**
- **User Flows:**
  - User asks complete query -> sees actions -> clicks action
  - User asks incomplete query -> sees question -> answers -> gets result
  - User answers multi-step question flow
  - User skips question with Esc
  - User uses keyboard to navigate actions

**Edge Cases:**
- **Network latency simulation:** Test slow connections
- **Authentication state changes:** Handle session expiry mid-flow
- **Browser back/forward navigation:** Preserve state correctly

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Flaky E2E tests | HIGH | Use retry logic, stable selectors |
| Slow CI execution | MEDIUM | Parallelize, use headless mode |
| Environment differences | LOW | Use Docker for consistent env |

**Code Structure:**
- Max test file: 200 lines
- Group tests by user flow
- Use Page Object pattern for maintainability

**Acceptance Criteria:**
- [ ] All major flows tested
- [ ] Mobile viewport tested
- [ ] Runs in CI pipeline
- [ ] Screenshots on failure

---

## Phase 5: Documentation - 1h

### DEV-173: Create ADR-018: Suggested Actions Architecture

**Reference:** Egidio architectural review

**Priority:** LOW | **Effort:** 0.25h | **Status:** NOT STARTED

**Problem:**
Architectural decision for suggested actions needs documentation.

**Solution:**
Create ADR documenting the template-based action selection approach.

**Agent Assignment:** @egidio (primary)

**Dependencies:**
- **Blocking:** DEV-155
- **Unlocks:** None

**Change Classification:** ADDITIVE

**File:** `docs/architecture/decisions/ADR-018-suggested-actions.md`

**Fields/Methods/Components:**
ADR sections:
- Context: Need for proactive suggestions
- Decision: Template-based selection (not LLM)
- Consequences: Performance gains, limited personalization
- Alternatives considered: LLM generation, hybrid

**Testing Requirements:**
- **Review Checklist:**
  - ADR template compliance verified
  - Technical accuracy reviewed by @egidio
  - Linked to relevant code files

**Edge Cases:**
- **Future architecture changes:** Document extensibility considerations
- **Multi-language support:** Consider i18n implications in design

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| ADR becomes outdated | LOW | Link to implementation, update on changes |
| Missing alternatives | LOW | Review with team before finalizing |

**Code Structure:**
- Follow existing ADR template format
- Use mermaid diagrams for architecture
- Keep concise, link to detailed docs

**Acceptance Criteria:**
- [ ] ADR follows standard template
- [ ] Decision rationale clear
- [ ] Consequences documented
- [ ] Alternatives listed

---

### DEV-174: Create ADR-019: Interactive Questions Architecture

**Reference:** Egidio architectural review

**Priority:** LOW | **Effort:** 0.25h | **Status:** NOT STARTED

**Problem:**
Architectural decision for interactive questions needs documentation.

**Solution:**
Create ADR documenting the inline question flow approach.

**Agent Assignment:** @egidio (primary)

**Dependencies:**
- **Blocking:** DEV-155
- **Unlocks:** None

**Change Classification:** ADDITIVE

**File:** `docs/architecture/decisions/ADR-019-interactive-questions.md`

**Fields/Methods/Components:**
ADR sections:
- Context: Need for parameter clarification
- Decision: Inline questions (Claude Code style)
- Consequences: UX benefits, state complexity
- Alternatives considered: Modal, separate page

**Testing Requirements:**
- **Review Checklist:**
  - ADR template compliance verified
  - Technical accuracy reviewed by @egidio
  - State management approach validated

**Edge Cases:**
- **Multi-step flow complexity:** Document state machine approach
- **Accessibility requirements:** Document ARIA considerations

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| ADR becomes outdated | LOW | Link to implementation, update on changes |
| State complexity underestimated | MEDIUM | Include detailed state diagrams |

**Code Structure:**
- Follow existing ADR template format
- Use mermaid diagrams for state flows
- Keep concise, link to detailed docs

**Acceptance Criteria:**
- [ ] ADR follows standard template
- [ ] Decision rationale clear
- [ ] State management approach documented
- [ ] Alternatives listed

---

### DEV-175: Update API Documentation

**Reference:** New endpoints

**Priority:** LOW | **Effort:** 0.5h | **Status:** NOT STARTED

**Problem:**
API documentation needs to include new endpoints and schema changes.

**Solution:**
Update OpenAPI/Swagger documentation for all new endpoints.

**Agent Assignment:** @ezio (primary)

**Dependencies:**
- **Blocking:** DEV-162
- **Unlocks:** None

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary Files:**
  - `docs/api/` manual documentation files
- **Affected Files:**
  - OpenAPI schema (auto-generated from FastAPI decorators)
- **Related Tests:**
  - API endpoint tests verify documentation accuracy
- **Baseline Command:** `uvicorn app.main:app --reload` (verify Swagger UI)

**Pre-Implementation Verification:**
- [ ] Existing API documentation reviewed
- [ ] OpenAPI schema generation working
- [ ] No pre-existing documentation errors

**Files:**
- OpenAPI schema auto-generated from FastAPI
- `docs/api/` manual documentation

**Fields/Methods/Components:**
Document:
- ChatResponse schema changes
- /actions/execute endpoint
- /questions/answer endpoint
- SSE event format for streaming

**Testing Requirements:**
- **Validation Checklist:**
  - All endpoints accessible in Swagger UI
  - Request/response examples work
  - Error codes documented with descriptions

**Edge Cases:**
- **Schema evolution:** Document backward compatibility
- **Optional fields:** Clearly mark nullable vs optional

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Documentation out of sync | MEDIUM | Auto-generate from code annotations |
| Missing examples | LOW | Add at least one example per endpoint |

**Code Structure:**
- Follow OpenAPI 3.0 spec
- Use FastAPI docstrings for descriptions
- Keep examples close to actual usage

**Acceptance Criteria:**
- [ ] All new endpoints documented
- [ ] Schema changes documented
- [ ] Examples provided
- [ ] Error responses documented

---

## Summary

| Phase | Tasks | Effort | Agent |
|-------|-------|--------|-------|
| Phase 1: Foundation | DEV-150 to DEV-156 | 9h | @ezio, @clelia |
| Phase 2: API Integration | DEV-157 to DEV-162 | 6h | @ezio, @clelia |
| Phase 3: Frontend | DEV-163 to DEV-167 | 10h | @livia, @clelia |
| Phase 4: Testing | DEV-168 to DEV-172 | 6.5h | @clelia |
| Phase 5: Documentation | DEV-173 to DEV-175 | 1h | @egidio, @ezio |
| **Total** | **26 tasks** | **~33h** | |

**Estimated Timeline:** 2-3 weeks at 2-3h/day *(with Claude Code)*
