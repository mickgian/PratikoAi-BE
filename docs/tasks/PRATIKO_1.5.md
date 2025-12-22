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
| DEV-173 | Phase 5: Documentation |

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

<details>
<summary>
<h3>DEV-160: Create /actions/execute Endpoint</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Created endpoint to execute suggested actions with parameter substitution.
</summary>

### DEV-160: Create /actions/execute Endpoint

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** HIGH | **Effort:** 1h (Actual: ~1h)

**Problem:**
When a user clicks a suggested action, the system needed an endpoint to execute that action and return a response.

**Solution:**
Created POST /api/v1/chatbot/actions/execute endpoint that looks up action template, substitutes parameters, and executes as chat query.

**Files Modified:**
- `app/schemas/proactivity.py` - Added `ActionExecuteRequest` schema
- `app/services/action_template_service.py` - Added `get_action_by_id()` method
- `app/api/v1/chatbot.py` - Added `/actions/execute` endpoint

**Files Created:**
- `tests/api/test_chatbot_actions.py` - 18 TDD tests

**Key Features:**
- Action template lookup by ID
- Parameter substitution in prompt_template
- Execute action as regular chat query
- Returns ChatResponse with follow-up suggested actions
- Error handling (400 for invalid action_id, 400 for missing params)

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 18 tests
- ✅ Action template looked up and executed
- ✅ Parameters substituted in prompt_template
- ✅ Returns full ChatResponse with new actions
- ✅ Proper error handling for invalid requests

**Git:** Branch `DEV-160-Create-/actions/execute-Endpoint`

</details>

---

<details>
<summary>
<h3>DEV-161: Create /questions/answer Endpoint</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Created endpoint to process answers to interactive questions with multi-step flow support.
</summary>

### DEV-161: Create /questions/answer Endpoint

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** HIGH | **Effort:** 1h (Actual: ~1h)

**Problem:**
When a user answers an interactive question, the system needed an endpoint to process the answer and continue the flow.

**Solution:**
Created POST /api/v1/chatbot/questions/answer endpoint that validates question/option, handles multi-step flows, and returns answers with follow-up actions.

**Files Modified:**
- `app/schemas/proactivity.py` - Added `QuestionAnswerRequest` and `QuestionAnswerResponse` schemas
- `app/api/v1/chatbot.py` - Added `/questions/answer` endpoint

**Files Created:**
- `tests/api/test_chatbot_questions.py` - 21 TDD tests

**Key Features:**
- Single-step question flow returns answer
- Multi-step question flow returns next question (via leads_to)
- Validates question_id, option_id (400 errors)
- Custom input validation (400 if required but missing)
- ProactivityEngine integration for follow-up actions

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 21 tests
- ✅ Single-step questions return direct answer
- ✅ Multi-step questions return next question
- ✅ Custom input captured and used
- ✅ Proper error handling for invalid requests

**Git:** Branch `DEV-161-Create-/questions/answer-Endpoint`

</details>

<details>
<summary>
<h3>DEV-162: Add Analytics Tracking to Action/Question Endpoints</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 0.5h (Actual: ~0.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Added fire-and-forget analytics tracking for action clicks and question answers.
</summary>

### DEV-162: Add Analytics Tracking to Action/Question Endpoints

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** MEDIUM | **Effort:** 0.5h (Actual: ~0.5h)

**Problem:**
Action clicks and question answers needed to be tracked for analytics to understand user behavior.

**Solution:**
Integrated ProactivityAnalyticsService into /actions/execute and /questions/answer endpoints with fire-and-forget async tracking in a thread pool.

**Files Modified:**
- `app/models/database.py` - Added sync engine and `get_sync_session()` for analytics operations
- `app/api/v1/chatbot.py` - Added analytics tracking helpers and calls to endpoints

**Files Created:**
- `tests/api/test_chatbot_analytics.py` - 10 TDD tests

**Key Features:**
- Fire-and-forget async tracking (non-blocking)
- Action clicks tracked with session_id, user_id, action, domain
- Question answers tracked with session_id, user_id, question_id, option_id, custom_input
- Thread pool executor for sync analytics writes
- Graceful degradation on analytics failures

**Acceptance Criteria (All Met):**
- ✅ Action clicks tracked in DB
- ✅ Question answers tracked in DB
- ✅ Analytics failure does not block response
- ✅ 10 TDD tests pass (61 total proactivity tests)

**Git:** Branch `DEV-162-Add-Analytics-Tracking-to-Action/Question-Endpoints`

</details>

<details>
<summary>
<h3>DEV-163: Create SuggestedActionsBar Component</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Created React component for rendering suggested action buttons after AI responses.
</summary>

### DEV-163: Create SuggestedActionsBar Component

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** HIGH | **Effort:** 2h (Actual: ~1h)

**Problem:**
The frontend needed a component to render suggested action buttons after AI responses with keyboard navigation support.

**Solution:**
Created SuggestedActionsBar React component in `/Users/micky/WebstormProjects/PratikoAiWebApp` with full TDD approach.

**Files Created:**
- `src/app/chat/components/SuggestedActionsBar.tsx` - Main component (265 lines)
- `src/app/chat/components/__tests__/SuggestedActionsBar.test.tsx` - 20 TDD tests (392 lines)

**Key Features:**
- Pill-style rounded buttons with Lucide React icons
- Keyboard navigation (Tab between buttons, Enter/Space to select)
- Input field for `requires_input` actions with Enter to submit, Escape to cancel
- Loading and disabled states
- Mobile responsive with flex-wrap
- Fade-slide-up animation on mount
- Accessible with role="group" and aria-labels

**Component Interface:**
```typescript
interface Action {
  id: string;
  label: string;
  icon?: string;
  category: 'calculate' | 'search' | 'verify' | 'export' | 'explain';
  prompt_template: string;
  requires_input?: boolean;
  input_placeholder?: string;
  input_type?: string;
}

interface SuggestedActionsBarProps {
  actions: Action[];
  onActionClick: (action: Action, input?: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
}
```

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 20 tests
- ✅ Keyboard navigation works (Tab, Enter, Space)
- ✅ Input field shown for requires_input actions
- ✅ Empty actions returns null (no render)
- ✅ Mobile responsive styling
- ✅ All 20 tests pass

**Git:** Branch `DEV-163-Create-SuggestedActionsBar-Component`

</details>

<details>
<summary>
<h3>DEV-164: Create InteractiveQuestionInline Component</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Created React component for inline interactive questions, Claude Code style.
</summary>

### DEV-164: Create InteractiveQuestionInline Component

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** HIGH | **Effort:** 3h (Actual: ~1h)

**Problem:**
The frontend needed a component to render interactive questions inline in the chat with keyboard navigation.

**Solution:**
Created InteractiveQuestionInline React component in `/Users/micky/WebstormProjects/PratikoAiWebApp` with full TDD approach.

**Files Created:**
- `src/app/chat/components/InteractiveQuestionInline.tsx` - Main component (215 lines)
- `src/app/chat/components/__tests__/InteractiveQuestionInline.test.tsx` - 26 TDD tests (455 lines)

**Key Features:**
- Question text with options in responsive grid (2 cols mobile, 4 cols desktop)
- Keyboard navigation (Arrow keys for selection, 1-9 number shortcuts, Enter to select, Esc to skip)
- Custom input field when allow_custom_input is true
- Selected option styling with blu-petrolio bg, white text, ring, shadow
- Touch-friendly targets (min 44px height)
- Accessible with role="radiogroup", aria-checked on options
- Fade-slide-up animation on mount

**Component Interface:**
```typescript
interface Option {
  id: string;
  label: string;
  icon?: string;
}

interface InteractiveQuestion {
  id: string;
  text: string;
  options: Option[];
  allow_custom_input?: boolean;
  custom_input_placeholder?: string;
}

interface InteractiveQuestionInlineProps {
  question: InteractiveQuestion;
  onAnswer: (optionId: string, customInput?: string) => void;
  onSkip?: () => void;
  disabled?: boolean;
}
```

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 26 tests
- ✅ Question and options rendered Claude Code style
- ✅ Keyboard navigation works (arrows, numbers, Enter, Esc)
- ✅ Custom input field for "Altro" option
- ✅ Skip functionality with Esc key
- ✅ All 26 tests pass

**Git:** Branch `DEV-164-Create-InteractiveQuestionInline-Component`

</details>

<details>
<summary>
<h3>DEV-165: Create useKeyboardNavigation Hook</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 1.5h (Actual: ~30min) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Created reusable keyboard navigation hook for lists and option selection.
</summary>

### DEV-165: Create useKeyboardNavigation Hook

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** MEDIUM | **Effort:** 1.5h (Actual: ~30min)

**Problem:**
Both action buttons and interactive questions need keyboard navigation, requiring a reusable hook.

**Solution:**
Created useKeyboardNavigation custom hook in `/Users/micky/WebstormProjects/PratikoAiWebApp` with full TDD approach.

**Files Created:**
- `src/lib/hooks/useKeyboardNavigation.ts` - Custom hook (115 lines)
- `src/lib/hooks/__tests__/useKeyboardNavigation.test.tsx` - 30 TDD tests (470 lines)

**Key Features:**
- Arrow key navigation (Up/Down) with wraparound at boundaries
- Enter key to select current item
- Escape key to cancel (works even from input fields)
- Number keys 1-9 for direct selection
- Input field detection to avoid keyboard conflicts
- Disabled state support
- Auto-reset selectedIndex when items change

**Hook Interface:**
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
```

**Test Coverage:**
- Statements: 100%
- Branches: 96.42%
- Functions: 100%
- Lines: 100%

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 30 tests
- ✅ Arrow keys navigate up/down with wraparound
- ✅ Enter selects current item
- ✅ Escape cancels/closes
- ✅ Number keys (1-9) select directly
- ✅ 90%+ test coverage achieved (100%/96%/100%/100%)

**Git:** Branch `DEV-165-Create-useKeyboardNavigation-Hook`

</details>

---

<details>
<summary>
<h3>DEV-166: Integrate Components into ChatInterface</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Integrated SuggestedActionsBar and InteractiveQuestionInline into AIMessageV2 component with 13 TDD tests.
</summary>

### DEV-166: Integrate Components into ChatInterface

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** CRITICAL | **Effort:** 2h (Actual: ~1h)

**Problem:**
The new proactivity components (SuggestedActionsBar and InteractiveQuestionInline) needed to be integrated into the existing chat interface to display suggested actions and interactive questions after AI messages.

**Solution:**
Modified AIMessageV2.tsx to accept new props and render the proactivity components. Used TDD approach with 13 integration tests.

**Files Modified:**
- `src/app/chat/components/AIMessageV2.tsx` (added imports, props, and rendering logic)
- `src/app/chat/components/__tests__/AIMessageV2.integration.test.tsx` (13 TDD tests)

**Props Added to AIMessageV2:**
- `suggestedActions?: Action[]` - Actions to display after message
- `onActionClick?: (action: Action, input?: string) => void` - Callback for action clicks
- `interactiveQuestion?: InteractiveQuestion` - Question to display after message
- `onQuestionAnswer?: (optionId: string, customInput?: string) => void` - Callback for question answers
- `onQuestionSkip?: () => void` - Callback when question is skipped via Escape

**Test Coverage:**
- 13 TDD tests covering all integration scenarios
- Tests for SuggestedActionsBar rendering, callbacks, disabled state
- Tests for InteractiveQuestionInline rendering, callbacks, disabled state
- Tests for both components together with proper ordering
- Tests for component positioning after message content

**Acceptance Criteria (All Met):**
- ✅ SuggestedActionsBar renders after AI messages with actions
- ✅ InteractiveQuestionInline renders when question provided
- ✅ Components disabled during streaming (isStreaming=true)
- ✅ Callbacks (onActionClick, onQuestionAnswer, onQuestionSkip) work correctly
- ✅ InteractiveQuestionInline rendered before SuggestedActionsBar
- ✅ Existing chat functionality unchanged (796 tests still pass)

**Git:** Branch `DEV-166-Integrate-Components-into-ChatInterface`

</details>

---

<details>
<summary>
<h3>DEV-167: Mobile Responsive Styling</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 1.5h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Added mobile responsive styling to SuggestedActionsBar and InteractiveQuestionInline with 11 TDD tests.
</summary>

### DEV-167: Mobile Responsive Styling

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** MEDIUM | **Effort:** 1.5h (Actual: ~1h)

**Problem:**
The proactivity components needed to work well on mobile devices with proper responsive layouts and touch-friendly targets.

**Solution:**
Enhanced SuggestedActionsBar and InteractiveQuestionInline with mobile-first responsive styles following Tailwind CSS breakpoint patterns.

**Files Modified:**
- `src/app/chat/components/SuggestedActionsBar.tsx` (responsive layout and touch targets)
- `src/app/chat/components/InteractiveQuestionInline.tsx` (responsive grid and padding)
- `src/app/chat/components/__tests__/MobileResponsive.test.tsx` (11 TDD tests)

**Key Changes:**

**SuggestedActionsBar:**
- Container: `flex-col sm:flex-row` for vertical stacking on mobile
- Buttons: `w-full sm:w-auto min-h-[44px]` for full width and touch targets
- Labels: `truncate` class for text overflow

**InteractiveQuestionInline:**
- Container: `p-3 sm:p-4` for responsive padding
- Grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` for responsive columns
- Input: `min-h-[44px]` for touch-friendly target

**Breakpoint Coverage:**
- iPhone SE (320px): Single column layout
- iPhone 14 (390px): Single column layout
- iPad Mini (768px): 2-column grid
- Desktop (1024px+): 4-column grid

**Acceptance Criteria (All Met):**
- ✅ SuggestedActionsBar stacks vertically on mobile
- ✅ InteractiveQuestionInline uses responsive grid
- ✅ All touch targets minimum 44px height
- ✅ 11 TDD tests pass
- ✅ All 807 frontend tests pass

**Git:** Branch `DEV-167-Create-Question-Templates-YAML-System-`

</details>

---

<details>
<summary>
<h3>DEV-168: Unit Tests for ProactivityEngine</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1.5h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Comprehensive unit tests for ProactivityEngine with 27 tests covering all scenarios.
</summary>

### DEV-168: Unit Tests for ProactivityEngine

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** HIGH | **Effort:** 1.5h (Actual: ~1h)

**Problem:**
ProactivityEngine needed comprehensive unit tests to ensure reliability.

**Solution:**
Created 27 unit tests covering all scenarios and edge cases for ProactivityEngine.

**Files Created/Modified:**
- `tests/services/test_proactivity_engine.py` - 27 unit tests

**Test Coverage:**
- Complete query (all params) -> actions only
- Incomplete query (0% coverage) -> question
- Partial query (50% coverage) -> question
- Near-complete query (80% coverage) -> smart fallback
- Template service failure -> graceful degradation
- Multiple domains -> correct template selection
- Document attached -> document-specific actions
- Performance under 500ms

**Acceptance Criteria (All Met):**
- ✅ 90%+ code coverage for ProactivityEngine
- ✅ All edge cases tested
- ✅ Performance assertions included
- ✅ Mock dependencies properly
- ✅ 27 tests pass

**Git:** Branch `DEV-155-Create-ProactivityEngine-Service`

</details>

---

<details>
<summary>
<h3>DEV-169: Unit Tests for Template Services</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Comprehensive unit tests for ActionTemplateService with 30 tests covering all scenarios.
</summary>

### DEV-169: Unit Tests for Template Services

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** HIGH | **Effort:** 1h (Actual: ~1h)

**Problem:**
Template loading services needed comprehensive tests.

**Solution:**
Created 30 unit tests covering all scenarios and edge cases for ActionTemplateService.

**Files Created/Modified:**
- `tests/services/test_action_template_service.py` - 30 unit tests

**Test Coverage:**
- Valid YAML loading
- Multiple file loading
- Action with all fields
- Domain fallback
- Action type fallback
- Cache hit verification
- Reload templates
- Document type lookup
- Document type not found
- Missing file graceful handling
- Invalid YAML error handling
- Schema validation failure
- Duplicate ID warning
- Empty directory handling
- Empty actions list
- Template validation errors
- Question template loading
- Question not found
- Question with leads_to
- Empty YAML file
- Default path initialization
- Missing directories handling
- Invalid question YAML
- Question parsing exception
- Invalid category enum
- Question with optional fields
- Full workflow integration
- JSON serialization

**Acceptance Criteria (All Met):**
- ✅ 90%+ code coverage for template services
- ✅ All edge cases tested
- ✅ Fixture YAML files created for tests
- ✅ 30 tests pass

**Git:** Branch `DEV-151-Create-YAML-Template-Loader-Service`

</details>

---

<details>
<summary>
<h3>DEV-170: Integration Tests for Chat Endpoints</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1.5h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Comprehensive integration tests for chat endpoints with proactivity features - 76 tests.
</summary>

### DEV-170: Integration Tests for Chat Endpoints

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** HIGH | **Effort:** 1.5h (Actual: ~1.5h)

**Problem:**
Chat endpoints with proactivity features needed integration tests.

**Solution:**
Created 76 integration tests covering all chat endpoints with proactivity features.

**Files Created/Modified:**
- `tests/api/test_chatbot_proactivity.py` - 11 tests (/chat with proactivity)
- `tests/api/test_chatbot_streaming_proactivity.py` - 16 tests (/chat/stream with proactivity)
- `tests/api/test_chatbot_actions.py` - 18 tests (/actions/execute)
- `tests/api/test_chatbot_questions.py` - 21 tests (/questions/answer)
- `tests/api/test_chatbot_analytics.py` - 10 tests (Analytics integration)

**Test Coverage:**
- /chat returns actions when query complete
- /chat returns question when params missing
- /chat/stream includes action event
- /chat/stream includes question event
- /actions/execute processes action with prompt substitution
- /actions/execute validates action ID
- /questions/answer handles single-step flow
- /questions/answer handles multi-step flow
- /questions/answer processes custom input
- Analytics recorded for all interactions
- Graceful degradation on failures

**Acceptance Criteria (All Met):**
- ✅ Full flow tested (API -> Service -> DB)
- ✅ All edge cases covered
- ✅ Cleanup after each test
- ✅ Performance assertions included
- ✅ 76 tests pass in 1.96s

**Git:** Branch `DEV-158-Modify-/chat-Endpoint-to-Include-Suggested-Actions`

</details>

---

<details>
<summary>
<h3>DEV-171: Frontend Component Tests</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Comprehensive frontend component tests for proactivity features - 100 tests.
</summary>

### DEV-171: Frontend Component Tests

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** HIGH | **Effort:** 1h (Actual: ~1h)

**Problem:**
Frontend components needed unit and integration tests.

**Solution:**
Created 100 Jest tests covering all proactivity frontend components.

**Files Created/Modified:**
- `src/app/chat/components/__tests__/SuggestedActionsBar.test.tsx` - 20 tests
- `src/app/chat/components/__tests__/InteractiveQuestionInline.test.tsx` - 26 tests
- `src/lib/hooks/__tests__/useKeyboardNavigation.test.tsx` - 30 tests
- `src/app/chat/components/__tests__/AIMessageV2.integration.test.tsx` - 13 tests
- `src/app/chat/components/__tests__/MobileResponsive.test.tsx` - 11 tests

**Test Coverage:**
- Component rendering with various props
- User interactions (click, keyboard)
- Props variations (disabled, loading, empty)
- Error states and edge cases
- Loading states
- Mobile viewport behavior
- Keyboard navigation (Arrow keys, Enter, Escape, number keys)
- Focus management
- Touch targets (min 44px)
- Responsive layouts

**Acceptance Criteria (All Met):**
- ✅ 85%+ coverage for new components
- ✅ Keyboard interactions tested
- ✅ Accessibility tested (ARIA roles, labels)
- ✅ Mobile viewport tested
- ✅ 100 tests pass in 0.976s

**Git:** Branch `DEV-163-Create-SuggestedActionsBar-Component`

</details>

---

<details>
<summary>
<h3>DEV-172: E2E Tests for Proactive Flows</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 1.5h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
Playwright E2E tests for proactivity features - 13 tests.
</summary>

### DEV-172: E2E Tests for Proactive Flows

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** MEDIUM | **Effort:** 1.5h (Actual: ~1h)

**Problem:**
End-to-end testing needed to verify complete user flows.

**Solution:**
Created 13 Playwright E2E tests covering all proactivity user flows.

**Files Created:**
- `e2e/proactivity.spec.ts` - 13 E2E tests

**Test Coverage:**
- **Suggested Actions (3 tests):**
  - Display actions after complete query
  - Execute action when clicked
  - Navigate actions with keyboard (Tab, Enter)
- **Interactive Questions (5 tests):**
  - Display question for incomplete query
  - Answer question by clicking option
  - Skip question with Escape key
  - Navigate options with arrow keys
  - Select option with number keys
- **Mobile Viewport (3 tests):**
  - Actions in vertical stack on mobile
  - Question options in single column
  - No horizontal scroll on mobile
- **Error Handling (2 tests):**
  - Graceful handling on slow connection
  - Continue chat when proactivity unavailable

**Acceptance Criteria (All Met):**
- ✅ All major flows tested
- ✅ Mobile viewport tested
- ✅ Runs in CI pipeline (Playwright config)
- ✅ Screenshots on failure (Playwright default)
- ✅ 13 E2E tests created

**Git:** Branch `DEV-172-E2E-Tests-for-Proactive-Flows`

</details>

---

## Phase 1: Foundation (Backend) - 9h

**Note:** DEV-150, DEV-151, DEV-152, DEV-153, DEV-154, DEV-155, and DEV-156 moved to Completed Tasks section above.

---

## Phase 2: API Integration (Backend) - 6h

**Note:** DEV-157, DEV-158, DEV-159, DEV-160, DEV-161, and DEV-162 moved to Completed Tasks section above.

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

**Note:** DEV-163, DEV-164, DEV-165, DEV-166, DEV-167 moved to Completed Tasks section above.

---

## Phase 4: Testing - 6.5h

**Note:** DEV-168, DEV-169, DEV-170, DEV-171, DEV-172 moved to Completed Tasks section above.

---

## Phase 5: Documentation - 1h

### DEV-173: Documentation Package

**Reference:** Egidio architectural review, New endpoints

**Priority:** LOW | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
Documentation for proactivity features needs to be created (ADRs + API docs).

**Solution:**
Create comprehensive documentation package including:
1. ADR-018: Suggested Actions Architecture
2. ADR-019: Interactive Questions Architecture
3. API Documentation updates for new endpoints

**Agent Assignment:** @egidio (ADRs), @ezio (API docs)

**Dependencies:**
- **Blocking:** DEV-162
- **Unlocks:** None

**Change Classification:** ADDITIVE

**Files:**
- `docs/architecture/decisions/ADR-018-suggested-actions.md`
- `docs/architecture/decisions/ADR-019-interactive-questions.md`
- OpenAPI schema (auto-generated from FastAPI)
- `docs/api/` manual documentation

**Deliverables:**

#### 1. ADR-018: Suggested Actions Architecture
- Context: Need for proactive suggestions
- Decision: Template-based selection (not LLM)
- Consequences: Performance gains, limited personalization
- Alternatives considered: LLM generation, hybrid

#### 2. ADR-019: Interactive Questions Architecture
- Context: Need for parameter clarification
- Decision: Inline questions (Claude Code style)
- Consequences: UX benefits, state complexity
- Alternatives considered: Modal, separate page

#### 3. API Documentation
- ChatResponse schema changes
- /actions/execute endpoint
- /questions/answer endpoint
- SSE event format for streaming

**Testing Requirements:**
- **Review Checklist:**
  - ADR-018 follows standard template
  - ADR-019 follows standard template
  - Technical accuracy reviewed by @egidio
  - All endpoints accessible in Swagger UI
  - Request/response examples work
  - Error codes documented with descriptions

**Edge Cases:**
- **Future architecture changes:** Document extensibility considerations
- **Multi-language support:** Consider i18n implications in design
- **Schema evolution:** Document backward compatibility
- **Optional fields:** Clearly mark nullable vs optional

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| ADR becomes outdated | LOW | Link to implementation, update on changes |
| Documentation out of sync | MEDIUM | Auto-generate from code annotations |
| Missing examples | LOW | Add at least one example per endpoint |

**Code Structure:**
- Follow existing ADR template format
- Use mermaid diagrams for architecture and state flows
- Follow OpenAPI 3.0 spec
- Use FastAPI docstrings for descriptions

**Acceptance Criteria:**
- [ ] ADR-018 follows standard template
- [ ] ADR-019 follows standard template
- [ ] Decision rationale clear in both ADRs
- [ ] All new endpoints documented in Swagger
- [ ] Examples provided for each endpoint
- [ ] Error responses documented

---

## Summary

| Phase | Tasks | Effort | Agent |
|-------|-------|--------|-------|
| Phase 1: Foundation | DEV-150 to DEV-156 | 9h | @ezio, @clelia |
| Phase 2: API Integration | DEV-157 to DEV-162 | 6h | @ezio, @clelia |
| Phase 3: Frontend | DEV-163 to DEV-167 | 10h | @livia, @clelia |
| Phase 4: Testing | DEV-168 to DEV-172 | 6.5h | @clelia |
| Phase 5: Documentation | DEV-173 | 1h | @egidio, @ezio |
| **Total** | **24 tasks** | **~33h** | |

**Estimated Timeline:** 2-3 weeks at 2-3h/day *(with Claude Code)*
