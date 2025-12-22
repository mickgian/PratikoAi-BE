# PratikoAI v1.5 - Proactive Assistant Tasks

**Version:** 1.5
**Date:** December 2025
**Status:** IN PROGRESS
**Total Effort:** ~33h (2-3 weeks at 2-3h/day) *(with Claude Code)*

**Recent Completed Work:**
- DEV-152: Create Action Templates YAML Files (2024-12-19)
- DEV-151: Create YAML Template Loader Service (2024-12-19)
- DEV-153: Create Interactive Question Templates YAML (2024-12-19)
- DEV-150: Create Pydantic Models for Actions and Interactive Questions (2024-12-19)

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

## Completed Tasks

<details>
<summary>
<h3>DEV-150: Create Pydantic Models for Actions and Interactive Questions</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 0.5h (Actual: ~0.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-19)<br>
Created Pydantic V2 models for proactivity features with 41 tests and 96.2% coverage.
</summary>

### DEV-150: Create Pydantic Models for Actions and Interactive Questions

**Status:** ✅ COMPLETED (2024-12-19)
**Priority:** CRITICAL | **Effort:** 0.5h (Actual: ~0.5h)

**Problem:**
The system needed structured data models for suggested actions and interactive questions to ensure type safety and API contract clarity.

**Solution:**
Created Pydantic V2 models in `app/schemas/proactivity.py` with comprehensive test coverage.

**Files Created:**
- `app/schemas/proactivity.py` (168 lines)
- `tests/schemas/test_proactivity.py` (708 lines, 41 tests)

**Models Implemented:**
- `ActionCategory(str, Enum)` - CALCULATE, SEARCH, VERIFY, EXPORT, EXPLAIN
- `Action(BaseModel)` - id, label, icon, category, prompt_template, requires_input, input_placeholder, input_type
- `InteractiveOption(BaseModel)` - id, label, icon, leads_to, requires_input
- `InteractiveQuestion(BaseModel)` - id, trigger_query, text, question_type, options, allow_custom_input, custom_input_placeholder, prefilled_params (min 2 options validation)
- `ExtractedParameter(BaseModel)` - name, value, confidence (0.0-1.0), source
- `ParameterExtractionResult(BaseModel)` - intent, extracted, missing_required, coverage (0.0-1.0), can_proceed

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 41 tests
- ✅ All models use Pydantic V2 syntax
- ✅ JSON serialization works correctly
- ✅ Model validation provides clear error messages
- ✅ 96.2% test coverage achieved (target was 95%+)

**Git:** Branch `DEV-150-Create-Pydantic-Models-for-Actions-and-Interactive-Questions`

</details>

---

<details>
<summary>
<h3>DEV-153: Create Interactive Question Templates YAML</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 0.75h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-19)<br>
Created 46 interactive questions across 3 YAML template files with validation script.
</summary>

### DEV-153: Create Interactive Question Templates YAML

**Status:** ✅ COMPLETED (2024-12-19)
**Priority:** HIGH | **Effort:** 0.75h (Actual: ~1h)

**Problem:**
Interactive questions for parameter clarification needed predefined templates for common scenarios (IRPEF calculation, apertura attivita, regime fiscale).

**Solution:**
Created YAML template files in `app/core/templates/interactive_questions/` covering calculation, procedure, and document classification scenarios.

**Files Created:**
- `app/core/templates/interactive_questions/calculations.yaml` (12.9 KB) - IRPEF, IVA, INPS, ravvedimento operoso flows
- `app/core/templates/interactive_questions/procedures.yaml` (15.4 KB) - apertura attività, regime fiscale, società flows
- `app/core/templates/interactive_questions/documents.yaml` (15.5 KB) - document classification for fattura, F24, bilancio, CU, contratto, busta paga
- `scripts/validate_question_templates.py` - validation script for leads_to references and "altro" options

**Key Statistics:**
- **Total Questions:** 46 questions across 3 files
- **All leads_to references valid:** ✅ Verified by validation script
- **All questions include "altro" option:** ✅

**Acceptance Criteria (All Met):**
- ✅ IRPEF calculation flow covered (tipo_contribuente -> reddito)
- ✅ Apertura attivita flow covered (tipo_attivita -> settore -> regime)
- ✅ Document classification questions covered
- ✅ All multi-step flows have valid leads_to references
- ✅ All questions include "Altro" option

**Git:** Branch `DEV-153-Create-Interactive-Question-Templates-YAML`, merged via PR #778

</details>

---

<details>
<summary>
<h3>DEV-151: Create YAML Template Loader Service</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-19)<br>
Created ActionTemplateService for loading and caching YAML templates with 30 tests and 95.2% coverage.
</summary>

### DEV-151: Create YAML Template Loader Service

**Status:** ✅ COMPLETED (2024-12-19)
**Priority:** HIGH | **Effort:** 1h (Actual: ~1h)

**Problem:**
Action and question templates need to be loaded from YAML files for version control and hot-reloading in development.

**Solution:**
Created ActionTemplateService that loads templates from `app/core/templates/`, caches in memory, and provides lookup by domain/action type with fallback to default domain.

**Files Created:**
- `app/services/action_template_service.py` (418 lines)
- `tests/services/test_action_template_service.py` (873 lines, 30 tests)

**Service Features:**
- `ActionTemplateService` class with dependency injection
- `load_templates()` - Load all YAML files from suggested_actions/ and interactive_questions/
- `get_actions_for_domain(domain, action_type)` - Lookup with fallback to 'default' domain
- `get_actions_for_document(document_type)` - Document-specific actions
- `get_question(question_id)` - Question lookup by ID
- `reload_templates()` - Force reload for hot-reloading in dev mode
- `_validate_templates()` - Return validation errors
- `ConfigurationError` custom exception for invalid YAML syntax

**Performance:**
- Template lookup: <5ms (memory cache)
- Cold start load: <100ms for all templates

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 30 tests
- ✅ Templates loaded from YAML files
- ✅ Cache mechanism working
- ✅ Fallback to default domain works
- ✅ Clear error messages on validation failure
- ✅ 95.2% test coverage achieved (target was 90%+)

**Git:** Branch `DEV-153-Create-Interactive-Question-Templates-YAML`

</details>

---

<details>
<summary>
<h3>DEV-152: Create Action Templates YAML Files</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-19)<br>
Created comprehensive action templates for tax, labor, legal domains plus document-specific actions with 18 validation tests.
</summary>

### DEV-152: Create Action Templates YAML Files

**Status:** ✅ COMPLETED (2024-12-19)
**Priority:** HIGH | **Effort:** 1h (Actual: ~1h)

**Problem:**
The system needs predefined action templates for different domains (tax, labor, legal) and document types (fattura, F24, bilancio, CU).

**Solution:**
Created YAML template files in `app/core/templates/suggested_actions/` covering all scenarios.

**Files Created:**
- `app/core/templates/suggested_actions/tax.yaml` - Tax domain actions (IRPEF, IVA, INPS, etc.)
- `app/core/templates/suggested_actions/labor.yaml` - Labor domain actions (CCNL, salary, TFR, etc.)
- `app/core/templates/suggested_actions/legal.yaml` - Legal domain actions (jurisprudence, court rulings, etc.)
- `app/core/templates/suggested_actions/documents.yaml` - Document-specific actions (fattura, F24, bilancio, CU, busta_paga, contratto)
- `app/core/templates/suggested_actions/default.yaml` - Default fallback actions
- `tests/templates/test_action_templates.py` - 18 validation tests

**Template Structure:**
```yaml
domain: tax
actions:
  fiscal_calculation:
    - id: tax_calculate_irpef
      label: "Calcola IRPEF"
      icon: calculator
      category: calculate
      prompt_template: "Calcola l'IRPEF per {tipo_contribuente} con reddito {reddito}"
      requires_input: false
```

**Coverage:**
- **Domains:** tax, labor, legal, documents, default
- **Document Types:** fattura, F24, bilancio, CU, busta_paga, contratto
- **Action Categories:** calculate, search, verify, export, explain
- **Total Actions:** 100+ actions across all domains

**Acceptance Criteria (All Met):**
- ✅ All document types covered (fattura, F24, bilancio, CU, busta_paga, contratto)
- ✅ All domains covered (tax, labor, legal, default)
- ✅ All templates validate against Action schema
- ✅ No duplicate action IDs
- ✅ Prompt templates use consistent placeholder format {name}
- ✅ 18 validation tests passing

**Git:** Branch `DEV-152-Create-Action-Templates-YAML-Files`

</details>

---

<details>
<summary>
<h3>DEV-154: Extend AtomicFactsExtractor for Parameter Coverage</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-19)<br>
Extended AtomicFactsExtractor with parameter coverage calculation and intent schema support. 35 tests passing.
</summary>

### DEV-154: Extend AtomicFactsExtractor for Parameter Coverage

**Status:** ✅ COMPLETED (2024-12-19)
**Priority:** CRITICAL | **Effort:** 2h (Actual: ~1.5h)

**Problem:**
The existing AtomicFactsExtractor extracts facts but does not calculate parameter coverage against intent schemas to determine if a query is complete.

**Solution:**
Extended AtomicFactsExtractor with INTENT_SCHEMAS dictionary, coverage calculation methods, and parameter mapping for proactive assistant.

**Files Modified:**
- `app/services/atomic_facts_extractor.py` - Added ~300 lines with new methods and INTENT_SCHEMAS

**Files Created:**
- `tests/services/test_atomic_facts_parameter_coverage.py` - 35 tests for parameter coverage

**Methods Implemented:**
- `INTENT_SCHEMAS: dict[str, IntentSchema]` - Schema definitions for 7 intents (calcolo_irpef, calcolo_iva, calcolo_contributi_inps, calcolo_tfr, calcolo_netto, verifica_scadenza, cerca_normativa)
- `IntentSchema(TypedDict)` - required, optional, defaults
- `calculate_coverage(intent: str, extracted: list[ExtractedParameter]) -> float` - Calculate coverage ratio
- `get_missing_required(intent: str, extracted: list[ExtractedParameter]) -> list[str]` - Get missing required params
- `extract_with_coverage(query: str, intent: str | None = None) -> ParameterExtractionResult` - Full extraction with coverage
- `_parse_italian_number(text: str) -> float | None` - Handle Italian format (1.000,50)
- `_map_facts_to_params(facts, intent, query) -> list[ExtractedParameter]` - Map atomic facts to parameters
- `_extract_contributor_type(query: str) -> str | None` - Extract contributor type from query

**Key Features:**
- Confidence threshold (0.7) for coverage calculation
- Smart fallback: can_proceed=True when coverage >= 0.8
- Support for Italian number formats (both 1.000,50 and 1000.50)
- Multiple values for same param: highest confidence wins
- Contributor type extraction (dipendente, autonomo, pensionato, imprenditore)

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 35 tests
- ✅ Coverage calculation accurate
- ✅ Italian number formats supported
- ✅ Smart fallback for near-complete queries (coverage >= 0.8)
- ✅ All tests pass
- ✅ Ruff linting clean

**Git:** Branch `DEV-154-Extend-AtomicFactsExtractor-for-Parameter-Coverage`

</details>

---

<details>
<summary>
<h3>DEV-155: Create ProactivityEngine Service</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2.5h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-19)<br>
Created ProactivityEngine service orchestrating parameter extraction, action selection, and question generation. 27 tests passing.
</summary>

### DEV-155: Create ProactivityEngine Service

**Status:** ✅ COMPLETED (2024-12-19)
**Priority:** CRITICAL | **Effort:** 2.5h (Actual: ~1.5h)

**Problem:**
A central orchestrator is needed to coordinate parameter extraction, action selection, and interactive question generation.

**Solution:**
Created ProactivityEngine service with dependency injection that orchestrates all proactive features.

**Files Created:**
- `app/services/proactivity_engine.py` - ProactivityEngine service (~300 lines)
- `tests/services/test_proactivity_engine.py` - 27 unit tests

**Files Modified:**
- `app/schemas/proactivity.py` - Added ProactivityContext and ProactivityResult models

**Methods Implemented:**
- `ProactivityEngine.__init__(template_service, facts_extractor)` - Dependency injection
- `process(query, context) -> ProactivityResult` - Main orchestration method
- `select_actions(domain, action_type, document_type) -> list[Action]` - Action selection
- `should_ask_question(extraction_result) -> bool` - Question trigger logic
- `generate_question(intent, missing_params, prefilled) -> InteractiveQuestion | None` - Question generation
- `_extract_parameters(query, context) -> ParameterExtractionResult` - Parameter extraction
- `_infer_intent(context) -> str | None` - Intent inference from context

**Models Added to proactivity.py:**
- `ProactivityContext` - session_id, domain, action_type, document_type, user_history
- `ProactivityResult` - actions, question, extraction_result, processing_time_ms

**Key Features:**
- Smart fallback: can_proceed=True bypasses question generation
- Document context prioritizes document-specific actions
- Graceful error handling with warning logs
- Performance tracking with processing_time_ms
- Intent-to-question mapping for missing parameters

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 27 tests
- ✅ Actions returned for complete queries
- ✅ Questions returned for incomplete queries (coverage < 0.8)
- ✅ Smart fallback works for near-complete queries
- ✅ Performance under 500ms (verified in tests)
- ✅ Document context influences action selection
- ✅ Ruff linting clean

**Git:** Branch `DEV-155-Create-ProactivityEngine-Service`

</details>

---

<details>
<summary>
<h3>DEV-156: Create Analytics Tracking Model and Service</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 1h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-20)<br>
Created SQLModel analytics tables and ProactivityAnalyticsService with 22 tests for tracking user interactions.
</summary>

### DEV-156: Create Analytics Tracking Model and Service

**Status:** ✅ COMPLETED (2024-12-20)
**Priority:** MEDIUM | **Effort:** 1h (Actual: ~1h)

**Problem:**
User interactions with suggested actions and interactive questions needed to be tracked for analytics and future ML model training.

**Solution:**
Created SQLModel tables and analytics service with non-blocking writes and GDPR compliance.

**Files Created:**
- `app/models/proactivity_analytics.py` (89 lines)
- `app/services/proactivity_analytics_service.py` (190 lines)
- `tests/models/test_proactivity_analytics.py` (142 lines, 10 tests)
- `tests/services/test_proactivity_analytics_service.py` (233 lines, 12 tests)
- `alembic/versions/20251220_add_proactivity_analytics_tables.py`

**Models Implemented:**
- `SuggestedActionClick(BaseModel, table=True)` - id (UUID), session_id, user_id (nullable FK with CASCADE), action_template_id, action_label, domain, clicked_at, context_hash
- `InteractiveQuestionAnswer(BaseModel, table=True)` - id (UUID), session_id, user_id (nullable FK with CASCADE), question_id, selected_option, custom_input, answered_at

**Service Methods:**
- `track_action_click(session_id, user_id, action, domain, context_hash)` - Non-blocking
- `track_question_answer(session_id, user_id, question_id, option_id, custom_input)` - Non-blocking
- `get_popular_actions(domain, limit)` - Returns ActionStats list

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 22 tests
- ✅ Migration created successfully
- ✅ GDPR: user_id ON DELETE CASCADE
- ✅ Non-blocking writes (DB errors logged, not raised)
- ✅ Anonymous user support (user_id=None)
- ✅ All tests passing

**Git:** Branch `DEV-156-Create-Analytics-Tracking-Model-and-Service`

</details>

---

<details>
<summary>
<h3>DEV-157: Extend ChatResponse Schema with Actions/Questions</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 0.5h (Actual: ~0.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-20)<br>
Extended ChatResponse schema with proactivity fields in a backward-compatible way.
</summary>

### DEV-157: Extend ChatResponse Schema with Actions/Questions

**Status:** ✅ COMPLETED (2024-12-20)
**Priority:** HIGH | **Effort:** 0.5h (Actual: ~0.5h)

**Problem:**
The ChatResponse schema needed to be extended to include suggested_actions and interactive_question fields.

**Solution:**
Added optional fields to ChatResponse schema in a backward-compatible way.

**Files Modified:**
- `app/schemas/chat.py` - Added new optional fields to ChatResponse
- `tests/schemas/test_chat.py` - Added 7 new TDD tests

**Fields Added to ChatResponse:**
```python
suggested_actions: list[Action] | None = None
interactive_question: InteractiveQuestion | None = None
extracted_params: dict[str, Any] | None = None
```

**Tests Added:**
- `test_chat_response_backward_compatible` - Old clients work without new fields
- `test_chat_response_with_suggested_actions` - Actions serialize correctly
- `test_chat_response_with_interactive_question` - Questions serialize correctly
- `test_chat_response_with_extracted_params` - Params serialize correctly
- `test_chat_response_with_actions_and_question` - Both fields together
- `test_chat_response_serialization_excludes_none` - None excluded from output
- `test_chat_response_json_serialization` - JSON serialization works

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 7 new tests
- ✅ Backward compatible (optional fields default to None)
- ✅ All 36 existing tests pass
- ✅ None values excluded from serialization (exclude_none=True)

**Git:** Branch `DEV-157-Extend-ChatResponse-Schema-with-Actions/Questions`

</details>

---

<details>
<summary>
<h3>DEV-158: Modify /chat Endpoint to Include Suggested Actions</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-20)<br>
Integrated ProactivityEngine with /chat endpoint for suggested actions and interactive questions.
</summary>

### DEV-158: Modify /chat Endpoint to Include Suggested Actions

**Status:** ✅ COMPLETED (2024-12-20)
**Priority:** HIGH | **Effort:** 1h (Actual: ~1h)

**Problem:**
The /chat endpoint needed to return suggested actions and interactive questions based on query analysis.

**Solution:**
Integrated ProactivityEngine into /chat endpoint with graceful degradation.

**Files Modified:**
- `app/api/v1/chatbot.py` - Added ProactivityEngine integration

**Files Created:**
- `tests/api/test_chatbot_proactivity.py` - 11 TDD tests

**Key Features:**
- ProactivityEngine singleton pattern for performance
- Graceful degradation on engine failure
- ChatResponse includes suggested_actions, interactive_question, extracted_params
- Non-blocking processing

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 11 tests
- ✅ ProactivityEngine integrated with graceful fallback
- ✅ Actions returned for complete queries
- ✅ Questions returned for incomplete queries
- ✅ All existing tests pass

**Git:** Branch `DEV-158-Modify-/chat-Endpoint-to-Include-Suggested-Actions`

</details>

---

<details>
<summary>
<h3>DEV-159: Modify /chat/stream Endpoint for Actions</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1.5h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-20)<br>
Modified streaming endpoint to include proactivity events as SSE events before [DONE] token.
</summary>

### DEV-159: Modify /chat/stream Endpoint for Actions

**Status:** ✅ COMPLETED (2024-12-20)
**Priority:** HIGH | **Effort:** 1.5h (Actual: ~1.5h)

**Problem:**
The streaming endpoint needed to include suggested actions and interactive questions as SSE events after content but before [DONE].

**Solution:**
Extended StreamResponse schema with event_type, suggested_actions, interactive_question, and extracted_params fields. Modified /chat/stream to yield proactivity events.

**Files Modified:**
- `app/schemas/chat.py` - Extended StreamResponse with proactivity fields
- `app/api/v1/chatbot.py` - Integrated ProactivityEngine into streaming flow

**Files Created:**
- `tests/api/test_chatbot_streaming_proactivity.py` - 16 TDD tests

**SSE Event Format:**
```
data: {"content": "...", "event_type": "content", "done": false}
data: {"content": "", "event_type": "suggested_actions", "suggested_actions": [...]}
data: {"content": "", "event_type": "interactive_question", "interactive_question": {...}}
data: {"content": "", "done": true}
```

**Key Features:**
- Event types: content, suggested_actions, interactive_question
- Event order: content → actions → question → done
- Graceful degradation on ProactivityEngine failure
- Backward compatible (legacy clients can ignore new fields)

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 16 tests
- ✅ Actions sent as structured SSE event
- ✅ Event order: content -> actions -> question -> [DONE]
- ✅ All existing streaming tests pass
- ✅ Backward compatible

**Git:** Branch `DEV-159-Modify-/chat/stream-Endpoint-for-Actions`

</details>

---

## Phase 1: Foundation (Backend) - 9h

**Note:** DEV-150, DEV-151, DEV-152, DEV-153, DEV-154, DEV-155, and DEV-156 moved to Completed Tasks section above.

---

## Phase 2: API Integration (Backend) - 6h

**Note:** DEV-157, DEV-158, and DEV-159 moved to Completed Tasks section above.

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

## UI Design Reference (Phase 3 Guidance)

This section provides comprehensive styling guidance for Phase 3 frontend components to ensure consistency with the existing PratikoAI frontend design system.

### Frontend Repository
**Location:** `/Users/micky/WebstormProjects/PratikoAiWebApp`

### Component Library
- **Framework:** Radix UI + CVA (class-variance-authority) - Shadcn pattern
- **Styling:** Tailwind CSS 4 with `cn()` utility (clsx + tailwind-merge)
- **Icons:** Lucide React

### PratikoAI Color Palette
| Name | Hex Code | CSS Variable | Usage |
|------|----------|--------------|-------|
| Avorio | #F8F5F1 | --color-avorio | Cream background, button default |
| Blu-petrolio | #2A5D67 | --color-blu-petrolio | Primary color, text, selected state |
| Verde-salvia | #A9C1B7 | --color-verde-salvia | Accent color, hover states |
| Oro-antico | #D4A574 | --color-oro-antico | Highlights, warnings |
| Grigio-tortora | #C4BDB4 | --color-grigio-tortora | Neutral borders, disabled |

### Button Styling Pattern (from FeedbackButtons.tsx)
```typescript
className={cn(
  // Base styles
  'inline-flex items-center gap-1.5 px-4 py-2 rounded-full',
  'text-sm font-semibold transition-all duration-300',
  // Default state
  'bg-[#F8F5F1] text-[#2A5D67]',
  // Hover state
  'hover:bg-[#A9C1B7]/20 hover:scale-105 hover:shadow-md',
  // Focus state (accessibility)
  'focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#2A5D67]/50',
  // Active/click state
  'active:scale-95',
  // Selected state (when isSelected)
  isSelected && 'bg-[#2A5D67] text-white ring-2 ring-[#2A5D67] shadow-lg scale-105',
  // Disabled state
  'disabled:opacity-50 disabled:cursor-not-allowed'
)}
```

### Animation Patterns
| Pattern | Tailwind Class | Description |
|---------|----------------|-------------|
| Transitions | `transition-all duration-300` | Smooth state changes |
| Fade-in | `animate-fade-slide-up` | Entry animation (globals.css) |
| Focus ring | `focus-visible:ring-[3px] focus-visible:ring-[#2A5D67]/50` | Keyboard focus indicator |
| Click feedback | `active:scale-95` | Button press effect |
| Hover effect | `hover:scale-105 hover:shadow-md` | Interactive feedback |

### Responsive Breakpoints
| Breakpoint | Width | Layout Pattern |
|------------|-------|----------------|
| Default | <640px | Mobile: stacked, full-width |
| sm | ≥640px | Small tablets: 2-column grid |
| md | ≥768px | Tablets: 3-column grid |
| lg | ≥1024px | Desktop: flex-row, auto-width |

### Key Reference Files
| File | Purpose | Import Path |
|------|---------|-------------|
| `FeedbackButtons.tsx` | Button styling pattern | `@/app/chat/components/` |
| `visualConstants.ts` | Color and spacing constants | `@/app/chat/` |
| `globals.css` | CSS variables, animations | `@/app/` |
| `utils.ts` | cn() utility function | `@/lib/utils` |
| `useChatHotkeys.ts` | Keyboard navigation hook pattern | `@/app/chat/hooks/` |

### Common Tailwind Utility Patterns
```typescript
// Card container
'p-4 rounded-lg border border-[#C4BDB4]/30 bg-[#F8F5F1]/50'

// Grid layout (responsive)
'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2'

// Touch-friendly minimum
'min-h-[44px]'

// Stacked on mobile, row on desktop
'flex flex-col sm:flex-row gap-2'

// Full-width on mobile
'w-full sm:w-auto'
```

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

**UI Styling Reference:** See [UI Design Reference](#ui-design-reference-phase-3-guidance) section above.
- **Button Pattern:** Use pill-style buttons from FeedbackButtons.tsx
- **Colors:** #F8F5F1 (default bg), #2A5D67 (text/selected), #A9C1B7 (hover accent)
- **Layout:** `flex flex-wrap gap-2` (wrap on narrow viewports)
- **Entry Animation:** `animate-fade-slide-up`

**Fields/Methods/Components:**
```typescript
'use client';
import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';

interface Action {
  id: string;
  label: string;
  icon?: LucideIcon;
  requires_input?: boolean;
}

interface SuggestedActionsBarProps {
  actions: Action[];
  onActionClick: (action: Action, input?: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export function SuggestedActionsBar({
  actions,
  onActionClick,
  isLoading,
  disabled
}: SuggestedActionsBarProps) {
  if (actions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-3 animate-fade-slide-up">
      {actions.map((action) => {
        const Icon = action.icon;
        return (
          <button
            key={action.id}
            onClick={() => onActionClick(action)}
            disabled={disabled || isLoading}
            className={cn(
              // Base styles
              'inline-flex items-center gap-1.5 px-4 py-2 rounded-full',
              'text-sm font-semibold transition-all duration-300',
              // Default state
              'bg-[#F8F5F1] text-[#2A5D67]',
              // Hover state
              'hover:bg-[#A9C1B7]/20 hover:scale-105 hover:shadow-md',
              // Focus state (accessibility)
              'focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#2A5D67]/50',
              // Active/click state
              'active:scale-95',
              // Disabled state
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100'
            )}
          >
            {Icon && <Icon className="w-4 h-4" />}
            {action.label}
          </button>
        );
      })}
    </div>
  );
}
```

Component structure:
- Action buttons with icons (Lucide React)
- Pill-style rounded-full buttons following FeedbackButtons.tsx pattern
- Hover: scale-105, shadow-md, verde-salvia accent
- Focus: 3px ring in blu-petrolio/50
- Active: scale-95 for click feedback
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

**UI Styling Reference:** See [UI Design Reference](#ui-design-reference-phase-3-guidance) section above.
- **Container:** Card with `rounded-lg border border-[#C4BDB4]/30 bg-[#F8F5F1]/50`
- **Colors:** #2A5D67 (selected), #F8F5F1 (default), #C4BDB4 (border)
- **Layout:** `grid grid-cols-2 sm:grid-cols-4 gap-2` (responsive grid)
- **Entry Animation:** `animate-fade-slide-up`

**Fields/Methods/Components:**
```typescript
'use client';
import { useState, useCallback, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { useKeyboardNavigation } from '@/lib/hooks/useKeyboardNavigation';

interface Option {
  id: string;
  label: string;
}

interface InteractiveQuestion {
  text: string;
  options: Option[];
  allow_custom_input?: boolean;
}

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
  const [customText, setCustomText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const { selectedIndex, handleKeyDown } = useKeyboardNavigation({
    items: question.options.map(o => o.id),
    onSelect: (id) => onAnswer(id),
    onCancel: onSkip,
    enabled: !disabled,
  });

  // Focus input when "Altro" (custom) option is selected
  useEffect(() => {
    if (question.options[selectedIndex]?.id === 'custom') {
      inputRef.current?.focus();
    }
  }, [selectedIndex, question.options]);

  return (
    <div
      className="mt-4 p-4 rounded-lg border border-[#C4BDB4]/30 bg-[#F8F5F1]/50 animate-fade-slide-up"
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="radiogroup"
      aria-label={question.text}
    >
      {/* Question text */}
      <p className="text-sm font-medium text-[#2A5D67] mb-3">
        {question.text}
      </p>

      {/* Options grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {question.options.map((option, index) => (
          <button
            key={option.id}
            onClick={() => onAnswer(option.id)}
            disabled={disabled}
            role="radio"
            aria-checked={selectedIndex === index}
            className={cn(
              'px-3 py-2 rounded-full text-sm font-medium transition-all duration-300',
              'min-h-[44px]', // Touch-friendly minimum
              selectedIndex === index
                ? 'bg-[#2A5D67] text-white ring-2 ring-[#2A5D67] shadow-lg'
                : 'bg-white text-[#2A5D67] border border-[#C4BDB4] hover:border-[#2A5D67] hover:shadow-md',
              'focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#2A5D67]/50'
            )}
          >
            <span className="text-xs opacity-60 mr-1">{index + 1}.</span>
            {option.label}
          </button>
        ))}
      </div>

      {/* Custom input field (shown when allow_custom_input) */}
      {question.allow_custom_input && (
        <div className="mt-3">
          <input
            ref={inputRef}
            type="text"
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && customText.trim()) {
                onAnswer('custom', customText);
              }
            }}
            placeholder="Altro: scrivi la tua risposta..."
            className={cn(
              'w-full px-4 py-2 rounded-lg border border-[#C4BDB4]',
              'text-sm text-[#2A5D67] placeholder:text-[#C4BDB4]',
              'focus:outline-none focus:ring-2 focus:ring-[#2A5D67]/50 focus:border-[#2A5D67]',
              'transition-all duration-200'
            )}
          />
        </div>
      )}

      {/* Skip hint */}
      <p className="mt-3 text-xs text-[#C4BDB4]">
        Premi Esc per saltare • Usa 1-4 per selezione rapida
      </p>
    </div>
  );
}
```

Component structure:
- Question text at top with blu-petrolio color
- Options in responsive grid (2 cols mobile, 4 cols desktop)
- Selected option: blu-petrolio bg, white text, ring, shadow
- Number shortcuts (1-4) shown as prefix
- Custom input field when allow_custom_input
- Skip hint at bottom in grigio-tortora
- Touch targets minimum 44px height
- Keyboard: Arrow keys, Enter, Esc, number keys

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

**UI Styling Reference:** See [UI Design Reference](#ui-design-reference-phase-3-guidance) section above.
- **Pattern Reference:** Similar to `useChatHotkeys.ts` in `@/app/chat/hooks/`
- **Key handling:** ArrowUp, ArrowDown, Enter, Escape, number keys 1-9

**Fields/Methods/Components:**
```typescript
import { useState, useCallback, useEffect, KeyboardEvent } from 'react';

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
  const [selectedIndex, setSelectedIndex] = useState(initialIndex);

  // Reset index when items change
  useEffect(() => {
    setSelectedIndex(0);
  }, [items.length]);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled || items.length === 0) return;

    // Don't handle if user is typing in an input
    const target = event.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
      // Only handle Escape in inputs
      if (event.key === 'Escape' && onCancel) {
        event.preventDefault();
        onCancel();
      }
      return;
    }

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % items.length);
        break;
      case 'ArrowUp':
        event.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + items.length) % items.length);
        break;
      case 'Enter':
        event.preventDefault();
        if (items[selectedIndex]) {
          onSelect(items[selectedIndex]);
        }
        break;
      case 'Escape':
        event.preventDefault();
        onCancel?.();
        break;
      default:
        // Number keys 1-9 for direct selection
        const num = parseInt(event.key, 10);
        if (num >= 1 && num <= 9 && num <= items.length) {
          event.preventDefault();
          onSelect(items[num - 1]);
        }
    }
  }, [enabled, items, selectedIndex, onSelect, onCancel]);

  return { selectedIndex, setSelectedIndex, handleKeyDown };
}
```

Hook structure:
- Uses useState for selectedIndex tracking
- Wraparound navigation (ArrowDown at end wraps to start)
- Number keys 1-9 for direct selection
- Input field detection to avoid conflicts
- Escape always works (even in inputs) for cancel
- Clean dependency array for useCallback

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

**UI Styling Reference:** See [UI Design Reference](#ui-design-reference-phase-3-guidance) section above.
- **Reference Pattern:** Review existing FeedbackButtons integration in AIMessageV2
- **Import Pattern:** Use dynamic imports for proactivity components
- **API Calls:** Follow existing fetch patterns in chat components

**Fields/Methods/Components:**

**1. Update AIMessageV2.tsx:**
```typescript
'use client';
import dynamic from 'next/dynamic';
import { SuggestedActionsBar } from '@/components/chat/SuggestedActionsBar';
import { InteractiveQuestionInline } from '@/components/chat/InteractiveQuestionInline';
import { useChatContext } from '@/contexts/ChatContext';

interface AIMessageV2Props {
  // ... existing props
  suggestedActions?: Action[];
  interactiveQuestion?: InteractiveQuestion;
}

export function AIMessageV2({
  // ... existing props
  suggestedActions,
  interactiveQuestion
}: AIMessageV2Props) {
  const { dispatch, state } = useChatContext();
  const { isActionExecuting } = state;

  const handleActionClick = async (action: Action) => {
    dispatch({ type: 'SET_ACTION_EXECUTING', payload: true });
    try {
      const response = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: action.id, message_id }),
      });
      // Handle response - may trigger new chat message
    } finally {
      dispatch({ type: 'SET_ACTION_EXECUTING', payload: false });
    }
  };

  const handleQuestionAnswer = async (optionId: string, customText?: string) => {
    dispatch({ type: 'SET_ACTION_EXECUTING', payload: true });
    try {
      const response = await fetch('/api/v1/questions/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id, option_id: optionId, custom_input: customText }),
      });
      // Response may include follow-up message or actions
    } finally {
      dispatch({ type: 'SET_ACTION_EXECUTING', payload: false });
    }
  };

  return (
    <div className="...existing classes...">
      {/* Existing message content */}
      <MarkdownContent content={message.content} />

      {/* Proactivity components - render after message */}
      {interactiveQuestion && (
        <InteractiveQuestionInline
          question={interactiveQuestion}
          onAnswer={handleQuestionAnswer}
          onSkip={() => dispatch({ type: 'CLEAR_QUESTION' })}
          disabled={isActionExecuting}
        />
      )}

      {suggestedActions && suggestedActions.length > 0 && !interactiveQuestion && (
        <SuggestedActionsBar
          actions={suggestedActions}
          onActionClick={handleActionClick}
          isLoading={isActionExecuting}
        />
      )}
    </div>
  );
}
```

**2. Update ChatContext.tsx:**
```typescript
interface ChatState {
  // ... existing state
  pendingQuestion: InteractiveQuestion | null;
  isActionExecuting: boolean;
}

type ChatAction =
  // ... existing actions
  | { type: 'SET_QUESTION'; payload: InteractiveQuestion | null }
  | { type: 'CLEAR_QUESTION' }
  | { type: 'SET_ACTION_EXECUTING'; payload: boolean };

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    // ... existing cases
    case 'SET_QUESTION':
      return { ...state, pendingQuestion: action.payload };
    case 'CLEAR_QUESTION':
      return { ...state, pendingQuestion: null };
    case 'SET_ACTION_EXECUTING':
      return { ...state, isActionExecuting: action.payload };
    default:
      return state;
  }
}
```

Integration pattern:
- Show InteractiveQuestion first if present (takes priority)
- Show SuggestedActionsBar only when no question pending
- Disable all proactivity UI during API calls
- Clear question after answer received
- API response may contain new actions/questions

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

**UI Styling Reference:** See [UI Design Reference](#ui-design-reference-phase-3-guidance) section above.

**Responsive Patterns to Apply:**

**1. SuggestedActionsBar - Mobile Responsive:**
```typescript
// Container: Stack vertically on mobile, wrap on desktop
<div className={cn(
  'flex flex-col sm:flex-row flex-wrap gap-2 mt-3',
  'animate-fade-slide-up'
)}>

// Buttons: Full width on mobile, auto on desktop
<button
  className={cn(
    // Full width on mobile
    'w-full sm:w-auto',
    // Touch-friendly height
    'min-h-[44px]',
    // ... existing button styles
  )}
>
```

**2. InteractiveQuestionInline - Mobile Responsive:**
```typescript
// Container: Full width, proper padding
<div className={cn(
  'mt-4 p-3 sm:p-4',
  'rounded-lg border border-[#C4BDB4]/30 bg-[#F8F5F1]/50'
)}>

// Options grid: 1 col on mobile, 2 on sm, 4 on lg
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">

// Option buttons: Full width, touch-friendly
<button
  className={cn(
    'w-full min-h-[44px]',
    'px-3 py-2 rounded-full',
    // Text size responsive
    'text-sm sm:text-base',
    // ... existing styles
  )}
>
```

**3. Text Truncation for Long Labels:**
```typescript
// Truncate with ellipsis on mobile
<span className="truncate max-w-full sm:max-w-[200px]" title={fullLabel}>
  {label}
</span>
```

**4. Touch Target Spacing:**
```typescript
// Ensure gap between interactive elements
'gap-2 sm:gap-3'

// Minimum touch target
'min-h-[44px] min-w-[44px]'
```

**5. Keyboard Visibility (scroll into view):**
```typescript
// In InteractiveQuestionInline, when custom input focused
useEffect(() => {
  if (isInputFocused && inputRef.current) {
    inputRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}, [isInputFocused]);
```

**Breakpoint Testing Checklist:**
| Viewport | Width | Layout Expected |
|----------|-------|-----------------|
| iPhone SE | 320px | Single column, stacked buttons |
| iPhone 14 | 390px | Single column, stacked buttons |
| iPad Mini | 768px | 2-column grid, row buttons |
| Desktop | 1024px+ | 4-column grid, inline buttons |

**Edge Cases:**
- **Small screens (<375px):** Single column layout
- **Touch targets:** Minimum 44px height
- **Keyboard on mobile:** Component should scroll into view
- **Landscape mode:** Optimize for horizontal space
- **Very long labels:** Text truncation with ellipsis

**Testing Requirements:**
- **Visual Tests:**
  - Test at 320px, 375px, 768px, 1024px viewports
  - Touch target size verification (≥44px)
  - Text truncation with long labels
- **Accessibility Tests:**
  - Focus visible on touch devices
  - Swipe gestures don't interfere
  - Screen reader announces changes

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
