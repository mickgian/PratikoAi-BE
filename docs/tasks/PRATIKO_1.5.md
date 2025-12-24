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

<details>
<summary>
<h3>DEV-173: Documentation Package</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 1h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-22)<br>
ADRs for Suggested Actions and Interactive Questions architecture.
</summary>

### DEV-173: Documentation Package

**Status:** ✅ COMPLETED (2024-12-22)
**Priority:** LOW | **Effort:** 1h (Actual: ~1h)

**Problem:**
Documentation for proactivity features needed to be created (ADRs + API docs).

**Solution:**
Created comprehensive documentation package including architectural decision records.

**Files Created:**
- `docs/architecture/decisions/ADR-020-suggested-actions-architecture.md`
- `docs/architecture/decisions/ADR-021-interactive-questions-architecture.md`

**Documentation Coverage:**

**ADR-020: Suggested Actions Architecture**
- Context: Need for proactive suggestions
- Decision: Template-based selection (not LLM) for performance
- Architecture diagrams with mermaid
- Action categories and YAML schema
- Selection algorithm documentation
- API integration patterns
- Consequences and trade-offs

**ADR-021: Interactive Questions Architecture**
- Context: Parameter clarification needs
- Decision: Inline questions (Claude Code style)
- State flow diagrams
- Keyboard navigation specification
- Parameter coverage algorithm
- Multi-step flow support
- Mobile considerations

**API Documentation:**
- OpenAPI schema auto-generated from FastAPI (existing)
- ChatResponse schema changes documented in ADRs
- /actions/execute endpoint documented
- /questions/answer endpoint documented
- SSE event formats documented

**Acceptance Criteria (All Met):**
- ✅ ADR-020 follows standard template
- ✅ ADR-021 follows standard template
- ✅ Architecture diagrams included
- ✅ API endpoint documentation
- ✅ Request/response examples included

**Git:** Branch `DEV-173-Documentation-Package`

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

**Note:** DEV-173 moved to Completed Tasks section above.

---

## Phase 6: LLM-First Proactivity Architecture Revision - 17h

**Context:** The template-heavy proactivity architecture from Phase 1-5 proved impractical in production. Section 12 of PRATIKO_1.5_REFERENCE.md describes the revised LLM-First architecture where:
- InteractiveQuestion is ONLY for 5 calculable intents with missing parameters
- SuggestedActions are LLM-generated for EVERY response (with document template fallback)

**Migration Plan (from Section 12.11):**
- Phase 6A: Backend Core (DEV-174 to DEV-177) - 1.5 days
- Phase 6B: Cleanup & Integration (DEV-178 to DEV-180) - 1 day
- Phase 6C: Testing & Validation (DEV-181 to DEV-183) - 1 day

**Golden Set & KB Compatibility (CRITICAL):**
Phase 6 changes MUST NOT disrupt the existing document retrieval and injection flow:
- Golden Set fast-path (confidence >= 0.85) remains unchanged
- KB hybrid search (BM25 + Vector + Recency) remains unchanged
- Document context injection happens BEFORE LLM call (unchanged)
- Response parsing happens AFTER LLM call (new, but non-disruptive)
- All Phase 6 tasks must include regression tests for document flow

**Obsolete Code from Phase 1-5 to Remove (~4,100 lines):**

| File | Lines to Remove | % of File | What Becomes Obsolete |
|------|-----------------|-----------|----------------------|
| `proactivity_engine.py` | ~492 | 54% | Template matching, `CLASSIFICATION_TO_INTENT`, `INTENT_QUESTION_MAP`, `INTENT_MULTIFIELD_QUESTIONS`, `generate_question()`, `select_actions()`, `_infer_intent()` |
| `action_template_service.py` | 432 | 100% | Entire service (YAML loading, template caching, domain/document lookups) |
| `atomic_facts_extractor.py` | ~400 | 80% | `INTENT_SCHEMAS`, `extract_with_coverage()`, coverage calculation logic |
| `proactivity.py` (schemas) | ~215 | 72% | `ActionCategory` enum, `InputField`, `ExtractedParameter`, `ParameterExtractionResult` |
| YAML template files | 2,572 | 100% | All suggested_actions/ and most interactive_questions/ files |

---

### Phase 6 Dependency Map

```
DEV-174 (CALCULABLE_INTENTS Constants)
    └── DEV-175 (System Prompt Update)
            └── DEV-176 (parse_llm_response)
                    └── DEV-177 (Simplified ProactivityEngine)
                            └── DEV-178 (Template Cleanup) ← MUST complete before DEV-179
                                    └── DEV-179 (/chat Integration)
                                            └── DEV-180 (/chat/stream Integration)
                                                    └── DEV-181 (Unit Tests)
                                                            └── DEV-182 (Integration Tests)
                                                                    └── DEV-183 (E2E Validation)
```

**CRITICAL: DEV-178 → DEV-179 Dependency**
`chatbot.py` imports `ActionTemplateService` at line 64. DEV-178 must archive this service BEFORE DEV-179 can integrate the new proactivity flow.

---

<details>
<summary>
<h3>DEV-174: Define CALCULABLE_INTENTS and DOCUMENT_ACTION_TEMPLATES Constants</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 1h | <strong>Status:</strong> NOT STARTED<br>
Define the core constants for LLM-First architecture: calculable intents and document action templates.
</summary>

### DEV-174: Define CALCULABLE_INTENTS and DOCUMENT_ACTION_TEMPLATES Constants

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.4 and 12.6](/docs/tasks/PRATIKO_1.5_REFERENCE.md#124-interactivequestion-solo-per-calcoli-noti)

**Priority:** CRITICAL | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
The current architecture uses complex template matching for all queries. The LLM-First approach requires a clear, minimal set of constants defining which intents trigger InteractiveQuestion and which document types have predefined action templates.

**Solution:**
Create a new constants module with CALCULABLE_INTENTS (5 intents) and DOCUMENT_ACTION_TEMPLATES (4 document types) as defined in Section 12.4 and 12.6.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None (first task in Phase 6)
- **Unlocks:** DEV-175, DEV-177

**Change Classification:** ADDITIVE

**Error Handling:**
- Not applicable (constants module, no runtime logic)

**Performance Requirements:**
- Module import: <10ms (constants only, no computation)

**Edge Cases:**
- **Empty values:** All intents must have non-empty `required` list
- **Validation:** All document templates must have exactly 4 fields (id, label, icon, prompt)
- **Type safety:** Use Literal types for icon strings to catch typos
- **Duplicate IDs:** Ensure no duplicate action IDs within a document type

**File:** `app/core/proactivity_constants.py`

**Fields/Methods/Components:**
- `CALCULABLE_INTENTS: dict[str, CalculableIntent]` - 5 intent definitions with required params
  - `calcolo_irpef`: required=["tipo_contribuente", "reddito"]
  - `calcolo_iva`: required=["importo"]
  - `calcolo_contributi_inps`: required=["tipo_gestione", "reddito"]
  - `ravvedimento_operoso`: required=["importo_originale", "data_scadenza"]
  - `calcolo_f24`: required=["codice_tributo", "importo"]
- `DOCUMENT_ACTION_TEMPLATES: dict[str, list[ActionTemplate]]` - 4 document types
  - `fattura_elettronica`: 4 actions (verify, vat, entry, recipient)
  - `f24`: 3 actions (codes, deadline, ravvedimento)
  - `bilancio`: 3 actions (ratios, compare, summary)
  - `cu`: 3 actions (verify, irpef, summary)
- `CalculableIntent: TypedDict` - Type definition for intent structure
- `ActionTemplate: TypedDict` - Type definition for action template

**Testing Requirements:**
- **TDD:** Write `tests/core/test_proactivity_constants.py` FIRST
- **Unit Tests:**
  - `test_calculable_intents_has_exactly_five_entries`
  - `test_calculable_intents_all_have_required_params`
  - `test_document_templates_has_exactly_four_types`
  - `test_document_templates_all_actions_have_required_fields`
  - `test_action_ids_unique_within_document_type`
  - `test_icons_are_valid_emoji`
  - `test_prompts_are_non_empty_strings`
- **Edge Case Tests:**
  - `test_no_empty_required_lists`
  - `test_no_duplicate_intent_keys`
  - `test_constants_are_immutable_at_runtime`
- **Integration Tests:** Not applicable (pure constants)
- **Regression Tests:** Not applicable (new file)
- **Coverage Target:** 100% for new file

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Typo in intent name | HIGH | Use constants for all intent names, match Section 12.4 exactly |
| Missing required field | MEDIUM | TypedDict with Required[] for all fields |
| Inconsistent with reference | HIGH | Copy-paste from Section 12.4/12.6, code review |

**Code Structure:**
- Max file: 100 lines
- Use TypedDict for type safety
- Group constants logically (intents, then documents)

**Code Completeness:**
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All 5 intents from Section 12.4 implemented
- [ ] All 4 document types from Section 12.6 implemented
- [ ] All action templates have complete fields

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] CALCULABLE_INTENTS has exactly 5 entries as specified in Section 12.4
- [ ] DOCUMENT_ACTION_TEMPLATES has exactly 4 document types as specified in Section 12.6
- [ ] All action templates have required fields (id, label, icon, prompt)
- [ ] Constants are importable from `app.core.proactivity_constants`
- [ ] 100% test coverage for new file
- [ ] All tests pass: `pytest tests/core/test_proactivity_constants.py -v`

</details>

---

<details>
<summary>
<h3>DEV-175: Update System Prompt with Suggested Actions Output Format</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 1h | <strong>Status:</strong> NOT STARTED<br>
Add proactive actions instruction block to system prompt with &lt;answer&gt; and &lt;suggested_actions&gt; format.
</summary>

### DEV-175: Update System Prompt with Suggested Actions Output Format

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.5.1](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1251-system-prompt-aggiornato)

**Priority:** CRITICAL | **Effort:** 1h | **Status:** NOT STARTED

**Problem:**
The current system prompt does not instruct the LLM to generate suggested actions. The LLM-First architecture requires the LLM to output structured actions in every response using XML-like tags.

**Solution:**
Create a new prompt file `suggested_actions.md` with the proactive actions instruction block from Section 12.5.1.

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-174 (constants define action structure)
- **Unlocks:** DEV-176 (parser expects this format)

**Change Classification:** ADDITIVE

**Error Handling:**
- Not applicable (prompt file, no runtime logic)

**Performance Requirements:**
- Prompt loading: <5ms (file read)
- Token count: ~400 tokens (one-time cost per conversation)

**Edge Cases:**
- **Icon availability:** Use only standard emoji (no platform-specific)
- **JSON in prompt:** Escape examples properly in markdown
- **Encoding:** Ensure UTF-8 encoding for emoji
- **Loader failure:** `load_suggested_actions_prompt()` raises clear error if file missing
- **Token budget:** Prompt must not exceed ~400 tokens to preserve KB context allocation
- **Prompt order:** Suggested actions instructions APPENDED to system prompt (after document context)

**File:** `app/core/prompts/suggested_actions.md`

**Fields/Methods/Components:**
- `suggested_actions.md` (~80 lines) - Prompt content
  - Introduction section (professional context)
  - Output format specification (`<answer>` and `<suggested_actions>` tags)
  - Action requirements (pertinent, professional, actionable, diverse)
  - JSON format example
  - Category-specific action examples (fiscal, normative, procedural, document)
  - Icon reference table
- `load_suggested_actions_prompt() -> str` - Loader function in `__init__.py`

**Testing Requirements:**
- **TDD:** Write `tests/core/prompts/test_suggested_actions_prompt.py` FIRST
- **Unit Tests:**
  - `test_prompt_file_exists`
  - `test_prompt_contains_answer_tag_instruction`
  - `test_prompt_contains_suggested_actions_tag_instruction`
  - `test_prompt_contains_json_format_example`
  - `test_prompt_contains_all_icon_suggestions`
  - `test_load_function_returns_string`
  - `test_load_function_raises_on_missing_file`
- **Edge Case Tests:**
  - `test_prompt_valid_utf8_encoding`
  - `test_prompt_json_examples_are_valid_json`
- **Integration Tests:** Not applicable (static file)
- **Regression Tests:** Not applicable (new file)
- **Coverage Target:** 100% for loader function

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM ignores format | HIGH | Clear, emphatic instructions; test with real LLM |
| Token bloat | LOW | Keep prompt concise (~400 tokens max) |
| Encoding issues | MEDIUM | Explicit UTF-8 in file read |

**Code Structure:**
- Prompt file: ~80 lines
- Loader function: <20 lines

**Code Completeness:**
- [ ] No TODO comments for required functionality
- [ ] All icon suggestions from Section 12.5.1 included
- [ ] All example categories covered
- [ ] JSON format exactly matches Section 12.5.1

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] `suggested_actions.md` file created with full instruction set
- [ ] `load_suggested_actions_prompt()` function added to `__init__.py`
- [ ] Prompt includes all icon suggestions from Section 12.5.1
- [ ] Prompt includes output format with `<answer>` and `<suggested_actions>` tags
- [ ] No breaking changes to existing `SYSTEM_PROMPT`
- [ ] Prompt token count <= 400 tokens (verified with tiktoken)
- [ ] Prompt is APPENDED to system prompt, not prepended (document context takes priority)
- [ ] All tests pass: `pytest tests/core/prompts/ -v`

</details>

---

<details>
<summary>
<h3>DEV-176: Implement parse_llm_response Function</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 1.5h | <strong>Status:</strong> NOT STARTED<br>
Create parsing function to extract &lt;answer&gt; and &lt;suggested_actions&gt; from LLM output.
</summary>

### DEV-176: Implement parse_llm_response Function

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.5.2](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1252-parsing-della-risposta)

**Priority:** CRITICAL | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
The LLM will output responses with `<answer>` and `<suggested_actions>` XML-like tags. We need a robust parser that extracts these components and handles edge cases gracefully without ever raising exceptions.

**Solution:**
Implement `parse_llm_response()` function as specified in Section 12.5.2. The function must handle malformed output gracefully, never crash.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-175 (defines output format to parse)
- **Unlocks:** DEV-177, DEV-179, DEV-180

**Change Classification:** ADDITIVE

**Error Handling:**
- **Malformed JSON:** Log warning, return empty actions list
- **Missing tags:** Log info, use full response as answer
- **Invalid action fields:** Skip invalid action, include valid ones
- **Empty response:** Return empty answer and empty actions
- **Logging:** All parsing failures logged with context at WARNING level

**Performance Requirements:**
- Parse time: <5ms for typical response (500-2000 chars)
- Memory: No excessive string copies

**Edge Cases:**
- **Nulls/Empty:** Empty response returns empty answer + empty actions
- **Missing tags:** Full response used as answer, no actions
- **Malformed JSON:** Actions array has syntax error - return empty actions
- **Partial JSON:** Some actions valid, some invalid - include valid only
- **Nested tags:** Handle `<answer>` inside code blocks gracefully
- **Whitespace:** Trim whitespace from extracted content
- **Action limit:** Always truncate to max 4 actions
- **Extra fields:** Ignore unknown fields in action objects
- **Missing fields:** Skip actions missing required fields (id, label, icon, prompt)
- **Citation markers:** Preserve `[1]`, `[source:xyz]` format in answer text
- **Tag parsing order:** Parse suggested_actions BEFORE citation processing in downstream code

**File:** `app/services/llm_response_parser.py`

**Fields/Methods/Components:**
- `ParsedLLMResponse(BaseModel)` - Response container
  - `answer: str` - Extracted answer text
  - `suggested_actions: list[SuggestedAction]` - Parsed actions (max 4)
- `SuggestedAction(BaseModel)` - Single action
  - `id: str`
  - `label: str`
  - `icon: str`
  - `prompt: str`
- `parse_llm_response(raw_response: str) -> ParsedLLMResponse` - Main parser function
- `_extract_answer(raw: str) -> str` - Helper to extract answer
- `_extract_actions(raw: str) -> list[SuggestedAction]` - Helper to extract actions
- `_validate_action(action_dict: dict) -> Optional[SuggestedAction]` - Validate single action

**Testing Requirements:**
- **TDD:** Write `tests/services/test_llm_response_parser.py` FIRST
- **Unit Tests:**
  - `test_parse_valid_response_with_both_tags`
  - `test_parse_response_without_answer_tag`
  - `test_parse_response_without_actions_tag`
  - `test_parse_response_with_empty_actions`
  - `test_parse_response_with_malformed_json`
  - `test_parse_response_with_more_than_4_actions_truncates`
  - `test_parse_response_with_missing_action_fields_skips`
  - `test_parse_empty_response`
  - `test_parse_response_with_nested_tags_in_code_block`
  - `test_parse_response_with_extra_whitespace`
- **Edge Case Tests:**
  - `test_parse_partial_valid_actions`
  - `test_parse_unicode_in_response`
  - `test_parse_very_long_response`
  - `test_parse_response_with_only_closing_tag`
  - `test_parse_response_never_raises`
- **Integration Tests:** `tests/services/test_llm_response_parser_integration.py`
- **Regression Tests:** Run `pytest tests/services/` to verify no conflicts
- **Coverage Target:** 95%+ for parser module

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Regex too strict | HIGH | Test with varied real LLM outputs |
| Regex too loose | MEDIUM | Validate extracted content structure |
| Performance on large responses | LOW | Compile regex, single-pass extraction |
| JSON injection | MEDIUM | Validate action fields before use |

**Code Structure:**
- Max file: 80 lines
- Use compiled regex patterns
- Extract helpers for testability

**Code Completeness:**
- [ ] No TODO comments for required functionality
- [ ] All edge cases handled (never raises)
- [ ] Logging for all failure paths
- [ ] All action fields validated

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] `parse_llm_response()` handles all edge cases without crashing
- [ ] Graceful fallback: always returns ParsedLLMResponse (never raises)
- [ ] Actions truncated to max 4
- [ ] Invalid actions skipped, valid ones included
- [ ] Citations in answer text preserved after tag extraction (`[1]`, `[2]` markers)
- [ ] 95%+ test coverage for parser module
- [ ] All tests pass: `pytest tests/services/test_llm_response_parser.py -v`

</details>

---

<details>
<summary>
<h3>DEV-177: Simplify ProactivityEngine Decision Logic</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2h | <strong>Status:</strong> NOT STARTED<br>
Refactor ProactivityEngine to use LLM-First logic with simplified decision flow.
</summary>

### DEV-177: Simplify ProactivityEngine Decision Logic

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.7](/docs/tasks/PRATIKO_1.5_REFERENCE.md#127-logica-decisionale-completa)

**Priority:** CRITICAL | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The current ProactivityEngine uses complex template matching (~492 lines). Per Section 12.7, the logic should be simplified to three steps:
1. Check if calculable intent with missing params -> InteractiveQuestion
2. Check if document present -> use DOCUMENT_ACTION_TEMPLATES
3. Otherwise -> LLM generates actions

**Solution:**
Refactor ProactivityEngine to implement the simplified decision logic from Section 12.7, removing all template matching code.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-174 (constants), DEV-176 (parser)
- **Unlocks:** DEV-178, DEV-179, DEV-180

**Change Classification:** RESTRUCTURING

**Impact Analysis:**
- **Primary File:** `app/services/proactivity_engine.py`
- **Affected Files:**
  - `app/api/v1/chatbot.py` (imports ProactivityEngine)
  - `app/schemas/proactivity.py` (uses Action, InteractiveQuestion)
- **Related Tests:**
  - `tests/services/test_proactivity_engine.py` (direct - MAJOR UPDATE)
  - `tests/api/test_chatbot_proactivity.py` (consumer)
  - `tests/api/test_chatbot_streaming_proactivity.py` (consumer)
- **Baseline Command:** `pytest tests/services/test_proactivity_engine.py tests/api/test_chatbot_proactivity.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass (document current state)
- [ ] Existing code reviewed (identify all removal targets)
- [ ] No pre-existing test failures in proactivity tests

**Error Handling:**
- **Intent classification failure:** Log error, default to LLM-generated actions
- **Document type unknown:** Use LLM-generated actions (no template override)
- **Missing parameters extraction failure:** Log warning, skip InteractiveQuestion
- **Logging:** All decision paths logged at DEBUG level with context

**Performance Requirements:**
- Decision logic: <10ms (no LLM calls in decision)
- Full proactivity flow: <50ms (excluding LLM call)

**Edge Cases:**
- **Nulls/Empty:** Empty query returns empty actions
- **Unknown intent:** Treated as non-calculable, use LLM actions
- **Unknown document type:** No template override, use LLM actions
- **Partial parameters:** Extract what's available, ask for missing only
- **All parameters present:** No InteractiveQuestion, proceed to LLM
- **Concurrent requests:** Engine is stateless, thread-safe

**File:** `app/services/proactivity_engine.py`

**Code to REMOVE (~492 lines):**
- `CLASSIFICATION_TO_INTENT` constant (30 lines)
- `CLASSIFIER_ACTION_TO_TEMPLATE_ACTION` constant (12 lines)
- `INTENT_QUESTION_MAP` constant (14 lines)
- `INTENT_MULTIFIELD_QUESTIONS` constant (130 lines)
- `FALLBACK_CHOICE_QUESTION` constant (14 lines)
- `_infer_intent()` method (48 lines)
- `_legacy_infer_intent()` method (26 lines)
- `_get_question_id_for_param()` method (18 lines)
- `generate_question()` method (72 lines)
- `_generate_multifield_question()` method (71 lines)
- `should_ask_question()` method (94 lines)
- `_extract_parameters()` method (18 lines)
- `_select_actions_for_context()` method (35 lines)
- `select_actions()` method (49 lines)

**Fields/Methods/Components (NEW):**
- `ProactivityEngine` class (refactored)
  - `__init__(self)` - Initialize with constants only
  - `process_query(query: str, document: Optional[Document], session_context: Optional[dict]) -> ProactivityResult`
  - `_check_calculable_intent(query: str) -> Optional[InteractiveQuestion]`
  - `_get_document_actions(document: Optional[Document]) -> Optional[list[Action]]`
  - `_classify_intent(query: str) -> Optional[str]` - Simple intent classifier
  - `_extract_parameters(query: str, intent: str) -> dict[str, Any]`
  - `_build_question_for_missing(intent: str, missing: list[str], extracted: dict) -> InteractiveQuestion`
- `ProactivityResult(BaseModel)` - New result type
  - `interactive_question: Optional[InteractiveQuestion]`
  - `template_actions: Optional[list[Action]]`
  - `use_llm_actions: bool`

**Testing Requirements:**
- **TDD:** Update `tests/services/test_proactivity_engine.py` FIRST
- **Unit Tests:**
  - `test_process_query_calcolo_irpef_missing_params_returns_question`
  - `test_process_query_calcolo_irpef_complete_params_no_question`
  - `test_process_query_fattura_returns_template_actions`
  - `test_process_query_generic_returns_llm_flag`
  - `test_process_query_unknown_intent_uses_llm`
  - `test_process_query_unknown_document_uses_llm`
  - `test_all_five_calculable_intents_trigger_questions`
  - `test_all_four_document_types_return_templates`
- **Edge Case Tests:**
  - `test_empty_query_returns_llm_flag`
  - `test_partial_parameters_asks_for_missing_only`
  - `test_concurrent_calls_are_thread_safe`
- **Integration Tests:** `tests/integration/test_proactivity_flow.py`
- **Regression Tests:** `pytest tests/services/test_proactivity_engine.py tests/api/test_chatbot*.py -v`
- **Coverage Target:** 90%+ for engine module

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing API | CRITICAL | Maintain same public interface signatures |
| Missing test coverage | HIGH | Update all tests before removing code |
| Intent classification accuracy | MEDIUM | Test with real query examples |
| Parameter extraction regression | MEDIUM | Preserve working extraction logic |

**Code Structure:**
- Max class: 200 lines (down from ~900)
- Max method: 50 lines
- Extract helpers for testability

**Code Completeness:**
- [ ] No TODO comments for required functionality
- [ ] All 5 calculable intents implemented
- [ ] All 4 document types implemented
- [ ] All obsolete code removed (verify with grep)
- [ ] No stub implementations

**Acceptance Criteria:**
- [ ] Tests updated BEFORE implementation changes (TDD)
- [ ] Decision logic follows Section 12.7 exactly
- [ ] InteractiveQuestion ONLY for 5 calculable intents
- [ ] Template actions ONLY for 4 document types
- [ ] LLM actions flag set for everything else
- [ ] All obsolete methods/constants removed (~492 lines)
- [ ] Public API unchanged (backward compatible)
- [ ] 90%+ test coverage for engine module
- [ ] All regression tests pass
- [ ] All tests pass: `pytest tests/services/test_proactivity_engine.py -v`

</details>

---

<details>
<summary>
<h3>DEV-178: Remove Unused Templates and Simplify Template Service</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1.5h | <strong>Status:</strong> NOT STARTED<br>
Clean up template files and archive ActionTemplateService after LLM-First migration.
</summary>

### DEV-178: Remove Unused Templates and Simplify Template Service

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.11](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1211-piano-di-migrazione)

**Priority:** HIGH | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
The current template system has ~50+ scenarios across domain-specific YAML files (2,572 lines). With LLM-First architecture, templates are replaced by DOCUMENT_ACTION_TEMPLATES constants.

**Solution:**
1. Archive entire `ActionTemplateService` (432 lines - no longer needed)
2. Archive unused YAML template files
3. Remove unused schemas from `proactivity.py`
4. Simplify `atomic_facts_extractor.py` (remove coverage logic)

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-177 (engine no longer uses templates)
- **Unlocks:** DEV-179 (clean codebase for integration)

**Change Classification:** RESTRUCTURING

**Impact Analysis:**
- **Primary File:** `app/services/action_template_service.py` (archive entire file)
- **Affected Files:**
  - `app/schemas/proactivity.py` (remove unused models)
  - `app/services/atomic_facts_extractor.py` (simplify/archive)
  - `app/services/proactivity_engine.py` (remove import)
  - All YAML files in `app/core/templates/`
- **Related Tests:**
  - `tests/services/test_action_template_service.py` (archive)
  - `tests/templates/test_action_templates.py` (archive)
  - `tests/schemas/test_proactivity.py` (update for removed models)
  - `tests/services/test_atomic_facts_parameter_coverage.py` (archive)
- **Baseline Command:** `pytest tests/services/test_action_template_service.py tests/schemas/test_proactivity.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests documented (will be archived, not deleted)
- [ ] All imports to ActionTemplateService identified
- [ ] All imports to removed schemas identified
- [ ] Archive folder structure planned

**Error Handling:**
- Not applicable (code removal, no new runtime logic)

**Performance Requirements:**
- Import time improvement: ~50ms faster (fewer YAML loads at startup)

**Edge Cases:**
- **Dangling imports:** Grep for all removed modules
- **Test imports:** Update or archive tests that use removed code
- **Circular dependencies:** Verify no circular imports after removal

**Files to ARCHIVE (move to `archived/phase5_templates/`):**
- `app/services/action_template_service.py` (432 lines)
- `app/core/templates/suggested_actions/tax.yaml` (~214 lines)
- `app/core/templates/suggested_actions/labor.yaml` (~220 lines)
- `app/core/templates/suggested_actions/legal.yaml` (~150 lines)
- `app/core/templates/suggested_actions/default.yaml` (~100 lines)
- `app/core/templates/suggested_actions/documents.yaml` (~150 lines)
- `app/core/templates/interactive_questions/procedures.yaml` (~400 lines)
- Most of `app/core/templates/interactive_questions/calculations.yaml` (keep only if needed for 5 flows)

**Code to REMOVE from proactivity.py (~215 lines):**
- `ActionCategory` enum (15 lines)
- `InputField` model (22 lines)
- `ExtractedParameter` model (18 lines)
- `ParameterExtractionResult` model (19 lines)
- Complex fields from `InteractiveQuestion` (`trigger_query`, `fields`, `prefilled_params`)
- Complex fields from `Action` (`prompt_template`, `requires_input`, `input_placeholder`, `input_type`)

**Code to ARCHIVE from atomic_facts_extractor.py (~400 lines):**
- Archive entire file to `archived/phase5_templates/`
- Or simplify to minimal parameter extraction only

**Testing Requirements:**
- **TDD:** Update tests BEFORE removing code
- **Unit Tests:**
  - `test_proactivity_schema_action_minimal_fields`
  - `test_proactivity_schema_interactive_question_minimal_fields`
  - `test_no_import_errors_after_cleanup`
- **Edge Case Tests:**
  - `test_no_dangling_imports_to_archived_code`
- **Integration Tests:** Run full test suite to verify no breaks
- **Regression Tests:** `pytest tests/ -v --ignore=archived/` (exclude archived tests)
- **Coverage Target:** Maintain 69.5%+ overall coverage

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking imports | CRITICAL | Grep all imports before removal |
| Test failures | HIGH | Archive tests, don't delete |
| Accidental data loss | MEDIUM | Archive, don't delete files |
| Coverage drop | MEDIUM | Archive tests count toward coverage |

**Code Structure:**
- Archive folder: `archived/phase5_templates/`
- Maintain git history (archive, don't delete)

**Code Completeness:**
- [ ] All listed files archived
- [ ] All listed code removed from schemas
- [ ] All imports updated
- [ ] No orphan files

**Acceptance Criteria:**
- [ ] Tests updated BEFORE removing code
- [ ] All obsolete files archived to `archived/phase5_templates/`
- [ ] ActionTemplateService completely archived
- [ ] Schemas simplified (remove ~215 lines)
- [ ] AtomicFactsExtractor archived or simplified
- [ ] No orphan imports in codebase (verified with grep)
- [ ] All existing tests updated or archived
- [ ] All tests pass: `pytest tests/ -v --ignore=archived/`
- [ ] Coverage remains >=69.5%

</details>

---

<details>
<summary>
<h3>DEV-179: Integrate LLM-First Proactivity in /chat Endpoint</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2h | <strong>Status:</strong> NOT STARTED<br>
Update /chat endpoint to use new ProactivityEngine with LLM response parsing.
</summary>

### DEV-179: Integrate LLM-First Proactivity in /chat Endpoint

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.7](/docs/tasks/PRATIKO_1.5_REFERENCE.md#127-logica-decisionale-completa)

**Priority:** CRITICAL | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
The current /chat endpoint calls ProactivityEngine separately from LLM. The LLM-First approach requires:
1. Injecting suggested_actions prompt into system prompt
2. Parsing LLM response to extract actions
3. Overriding with document templates when applicable

**Solution:**
Modify /chat endpoint to inject suggested_actions prompt, use parse_llm_response(), and integrate with new ProactivityEngine.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-176 (parser), DEV-177 (engine), DEV-178 (template cleanup)
- **Unlocks:** DEV-180 (streaming endpoint)

**Golden Set & KB Integration (CRITICAL):**
This task MUST preserve the existing document flow:
1. Query → Golden/KB lookup → Context injection → LLM call → Parse response
2. Suggested actions prompt added to system prompt BEFORE LLM call
3. Response parsing happens AFTER document context already processed
4. InteractiveQuestion early-return does NOT skip document context
5. Token budget allocation respects KB documents priority

**Pre-Implementation Verification (Golden Set/KB):**
- [ ] Verify golden fast-path flow (Step 24) is unchanged
- [ ] Verify KB freshness validation (Step 26) is unchanged
- [ ] Document context injection timing documented
- [ ] Review `app/services/context_builder_merge.py` for token budget

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/api/v1/chatbot.py`
- **Affected Files:**
  - `app/core/langgraph/graph.py` (prompt injection)
  - `app/orchestrators/prompting.py` (prompt composition)
- **Related Tests:**
  - `tests/api/test_chatbot.py` (direct)
  - `tests/api/test_chatbot_proactivity.py` (direct - MAJOR UPDATE)
  - `tests/api/test_chatbot_actions.py` (consumer)
- **Baseline Command:** `pytest tests/api/test_chatbot.py tests/api/test_chatbot_proactivity.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Current /chat flow documented
- [ ] No pre-existing test failures

**Error Handling:**
- **Parser failure:** Log warning, return response without actions (graceful degradation)
- **ProactivityEngine failure:** Log error, continue with response
- **Template lookup failure:** Log warning, use LLM actions
- **Logging:** All errors logged with user_id, session_id, query context

**Performance Requirements:**
- Endpoint latency: <200ms overhead (excluding LLM call)
- Parsing: <5ms
- Template lookup: <1ms

**Edge Cases:**
- **LLM response without tags:** Parser returns full response as answer
- **Empty actions from LLM:** Return response without actions
- **Document present + LLM actions:** Template takes priority
- **Calculable intent detected:** Return InteractiveQuestion before LLM call
- **Concurrent requests:** Thread-safe, no shared state

**File:** `app/api/v1/chatbot.py`

**Fields/Methods/Components:**
- `chat()` function (modify)
  - Add suggested_actions prompt injection
  - Call `parse_llm_response()` after LLM
  - Integrate with `ProactivityEngine.process_query()`
  - Handle InteractiveQuestion early return
  - Apply document template override
- `_inject_proactivity_prompt(base_prompt: str) -> str` - Helper (new)
- `_apply_action_override(llm_actions: list, template_actions: Optional[list]) -> list` - Helper (new)

**Testing Requirements:**
- **TDD:** Write `tests/api/test_chatbot_llm_first.py` FIRST
- **Unit Tests:**
  - `test_chat_includes_suggested_actions_in_response`
  - `test_chat_uses_document_template_when_present`
  - `test_chat_uses_llm_actions_when_no_template`
  - `test_chat_returns_interactive_question_for_calculation`
  - `test_chat_graceful_degradation_on_parser_failure`
  - `test_chat_response_format_unchanged`
- **Edge Case Tests:**
  - `test_chat_empty_actions_from_llm`
  - `test_chat_concurrent_requests`
  - `test_chat_very_long_response`
- **Integration Tests:** `tests/api/test_chatbot_llm_first_integration.py`
- **Regression Tests:** `pytest tests/api/test_chatbot*.py -v`
- **Coverage Target:** 90%+ for modified code paths

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking API contract | CRITICAL | Same response schema, new field values only |
| Performance regression | HIGH | Measure baseline, compare after |
| LLM prompt too long | MEDIUM | Token budget validation |
| Parser bugs | MEDIUM | Graceful degradation, extensive tests |

**Code Structure:**
- Max route handler: 30 lines (delegate to helpers)
- Extract proactivity logic to helpers

**Code Completeness:**
- [ ] No TODO comments for required functionality
- [ ] Prompt injection complete
- [ ] Parser integration complete
- [ ] Template override logic complete
- [ ] All error paths handled

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation changes
- [ ] System prompt includes suggested_actions instructions
- [ ] LLM response is parsed to extract clean answer
- [ ] Actions come from LLM unless document/calculable override
- [ ] Backward compatible: API response schema unchanged
- [ ] Graceful degradation on errors
- [ ] Golden fast-path flow unchanged (Step 24)
- [ ] KB freshness validation unchanged (Step 26)
- [ ] Document context injection timing preserved
- [ ] Token budget respects KB document priority
- [ ] All regression tests pass
- [ ] All tests pass: `pytest tests/api/test_chatbot*.py -v`

</details>

---

<details>
<summary>
<h3>DEV-180: Integrate LLM-First Proactivity in /chat/stream Endpoint</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 1.5h | <strong>Status:</strong> NOT STARTED<br>
Update /chat/stream endpoint to handle streamed LLM output with suggested actions parsing.
</summary>

### DEV-180: Integrate LLM-First Proactivity in /chat/stream Endpoint

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.7](/docs/tasks/PRATIKO_1.5_REFERENCE.md#127-logica-decisionale-completa)

**Priority:** HIGH | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
The /chat/stream endpoint streams LLM tokens in real-time. We need to:
1. Buffer the complete response for parsing
2. Strip XML tags from streamed content
3. Send actions as final SSE event

**Solution:**
Buffer full response during streaming, strip tags from content tokens, parse actions after stream completes, send as final SSE event before `done`.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-179 (/chat integration pattern)
- **Unlocks:** DEV-181 (unit tests)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/api/v1/chatbot.py`
- **Affected Files:**
  - None (changes within same file)
- **Related Tests:**
  - `tests/api/test_chatbot_streaming.py` (direct)
  - `tests/api/test_chatbot_streaming_proactivity.py` (direct - MAJOR UPDATE)
- **Baseline Command:** `pytest tests/api/test_chatbot_streaming*.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline streaming tests pass
- [ ] Current streaming flow documented
- [ ] SSE event format documented

**Error Handling:**
- **Buffer overflow:** Log error, continue streaming without actions
- **Parser failure on buffered content:** Log warning, send done without actions
- **Connection closed during stream:** Clean up gracefully
- **Logging:** All errors logged with session context

**Performance Requirements:**
- Streaming latency: <10ms per chunk (unchanged)
- Final events (actions + done): <50ms total
- Buffer memory: <1MB per request

**Edge Cases:**
- **Very long response:** Buffer management, no memory leak
- **Client disconnect:** Clean up buffer, cancel stream
- **Partial tags in stream:** Buffer until tag complete before stripping
- **No actions in response:** Send done without actions event
- **InteractiveQuestion detected:** Send question event, skip LLM stream
- **Partial `<answer>` tag:** Buffer until `>` received before stripping
- **Partial `</answer>` tag:** Buffer until complete to avoid content corruption
- **Tag spans multiple chunks:** Maintain state across chunk boundaries
- **Document citations in stream:** Preserve `[1]`, `[2]` markers

**File:** `app/api/v1/chatbot.py`

**Fields/Methods/Components:**
- `chat_stream()` function (modify)
  - Add response buffer
  - Strip `<answer>` and `<suggested_actions>` tags from stream
  - Parse buffered response after stream
  - Send `suggested_actions` SSE event
  - Send `interactive_question` SSE event (when applicable)
- `_buffer_and_strip_response(chunk: str, buffer: StringIO) -> str` - Helper (new)
- `_send_proactivity_events(buffer: str, template_actions: Optional[list]) -> Generator` - Helper (new)

**SSE Event Format:**
```
event: content
data: {"text": "streamed content without tags"}

event: suggested_actions
data: {"actions": [{"id": "1", "label": "...", "icon": "...", "prompt": "..."}]}

event: done
data: {}
```

**Testing Requirements:**
- **TDD:** Write `tests/api/test_chatbot_stream_llm_first.py` FIRST
- **Unit Tests:**
  - `test_stream_strips_answer_tags`
  - `test_stream_strips_actions_tags`
  - `test_stream_sends_actions_event_after_content`
  - `test_stream_sends_done_last`
  - `test_stream_uses_document_template_when_present`
  - `test_stream_sends_interactive_question_when_applicable`
- **Edge Case Tests:**
  - `test_stream_handles_partial_tags`
  - `test_stream_handles_very_long_response`
  - `test_stream_handles_client_disconnect`
  - `test_stream_handles_no_actions`
- **Integration Tests:** `tests/api/test_chatbot_stream_integration.py`
- **Regression Tests:** `pytest tests/api/test_chatbot_streaming*.py -v`
- **Coverage Target:** 90%+ for streaming code paths

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking streaming format | CRITICAL | Maintain SSE event compatibility |
| Memory leak in buffer | HIGH | StringIO cleanup, max buffer size |
| Tag stripping breaks content | HIGH | Careful regex, test edge cases |
| Performance regression | MEDIUM | Measure streaming latency |

**Code Structure:**
- Max route handler: 50 lines (streaming is complex)
- Extract helpers for testability

**Code Completeness:**
- [ ] No TODO comments for required functionality
- [ ] Buffer management complete
- [ ] Tag stripping complete
- [ ] All SSE events implemented
- [ ] Cleanup on disconnect

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation changes
- [ ] Stream tokens unchanged (backward compatible content)
- [ ] `<answer>` and `<suggested_actions>` tags stripped from stream
- [ ] `suggested_actions` event sent after content stream
- [ ] `interactive_question` event sent when applicable
- [ ] `done` event always sent last
- [ ] Content between tags streamed without delay
- [ ] Tag characters never appear in streamed content
- [ ] Buffering does not cause visible latency
- [ ] Citations preserved in streamed content (`[1]`, `[2]` markers)
- [ ] All regression tests pass
- [ ] All tests pass: `pytest tests/api/test_chatbot_streaming*.py -v`

</details>

---

<details>
<summary>
<h3>DEV-181: Unit Tests for LLM-First Components</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2h | <strong>Status:</strong> NOT STARTED<br>
Comprehensive unit tests for new LLM-First components.
</summary>

### DEV-181: Unit Tests for LLM-First Components

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.10](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1210-criteri-di-accettazione-rivisti)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need comprehensive unit test coverage for all new/modified components to ensure LLM-First architecture works correctly.

**Solution:**
Create/update unit test files for all LLM-First components with TDD pattern.

**Agent Assignment:** @clelia (primary)

**Dependencies:**
- **Blocking:** DEV-174 to DEV-180 (all implementation complete)
- **Unlocks:** DEV-182 (integration tests)

**Change Classification:** ADDITIVE

**Error Handling:**
- Not applicable (test code)

**Performance Requirements:**
- Full unit test suite: <30s
- Individual test: <500ms

**Edge Cases:**
- See individual task edge cases (DEV-174 to DEV-180)

**Files to Create/Update:**
- `tests/core/test_proactivity_constants.py` (~100 lines, 15 tests)
- `tests/core/prompts/test_suggested_actions_prompt.py` (~60 lines, 7 tests)
- `tests/services/test_llm_response_parser.py` (~250 lines, 20 tests)
- `tests/services/test_proactivity_engine.py` (~300 lines, 25 tests - major update)

**Fields/Methods/Components:**
- `TestProactivityConstants` class (15 tests)
- `TestSuggestedActionsPrompt` class (7 tests)
- `TestLLMResponseParser` class (20 tests)
- `TestProactivityEngine` class (25 tests)

**Testing Requirements:**
- **TDD:** Already applied in DEV-174 to DEV-180
- **Unit Tests:** 67+ total tests across 4 files
  - Constants: 15 tests
  - Prompt: 7 tests
  - Parser: 20 tests
  - Engine: 25 tests
- **Edge Case Tests:** Included in unit test counts
- **Integration Tests:** Covered in DEV-182
- **Regression Tests:** Run all tests together
- **Coverage Target:** 95%+ for new modules, 90%+ for modified

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing edge cases | MEDIUM | Review Section 12 requirements |
| Flaky tests | MEDIUM | Avoid timing-dependent tests |
| Test maintenance | LOW | Follow AAA pattern, clear naming |

**Code Structure:**
- Follow AAA pattern (Arrange, Act, Assert)
- One assertion per test (where practical)
- Descriptive test names

**Code Completeness:**
- [ ] All 67+ tests implemented
- [ ] All edge cases covered
- [ ] No TODO in test code
- [ ] No skipped tests without reason

**Acceptance Criteria:**
- [ ] 67+ new/updated tests across all files
- [ ] 95%+ coverage for new modules (`proactivity_constants.py`, `llm_response_parser.py`)
- [ ] 90%+ coverage for modified modules (`proactivity_engine.py`)
- [ ] All tests follow AAA pattern
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Test execution time <30s

</details>

---

<details>
<summary>
<h3>DEV-182: Integration Tests for LLM-First Flow</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2h | <strong>Status:</strong> NOT STARTED<br>
Integration tests verifying full LLM-First proactivity flow.
</summary>

### DEV-182: Integration Tests for LLM-First Flow

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.10](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1210-criteri-di-accettazione-rivisti)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
Need integration tests that verify the complete flow from API request through proactivity engine to response with actions.

**Solution:**
Create integration tests that mock LLM but test full component integration.

**Agent Assignment:** @clelia (primary), @ezio (review)

**Dependencies:**
- **Blocking:** DEV-181 (unit tests complete)
- **Unlocks:** DEV-183 (E2E validation)

**Change Classification:** ADDITIVE

**Error Handling:**
- Not applicable (test code)

**Performance Requirements:**
- Integration test suite: <60s (mocked LLM)
- Individual test: <2s

**Edge Cases:**
- **Full flow with document:** Request -> ProactivityEngine -> Template actions -> Response
- **Full flow without document:** Request -> ProactivityEngine -> LLM parse -> Response
- **Full flow with calculation:** Request -> ProactivityEngine -> InteractiveQuestion -> Response
- **Streaming flow:** Request -> Stream -> Buffer -> Parse -> Actions event -> Done

**File:** `tests/integration/test_proactivity_llm_first.py`

**Fields/Methods/Components:**
- `TestLLMFirstProactivityIntegration` class
  - `test_chat_endpoint_returns_actions_from_llm`
  - `test_chat_endpoint_returns_template_actions_for_document`
  - `test_chat_endpoint_returns_interactive_question_for_calculation`
  - `test_chat_endpoint_overrides_llm_actions_with_template`
  - `test_chat_endpoint_graceful_degradation_on_malformed_llm`
  - `test_stream_endpoint_sends_actions_event`
  - `test_stream_endpoint_strips_tags_from_content`
  - `test_stream_endpoint_sends_interactive_question`
  - `test_full_flow_with_session_context`
  - `test_full_flow_with_document_context`
- `TestGoldenSetKBRegression` class (CRITICAL - Regression tests)
  - `test_golden_set_fast_path_still_works_with_proactivity`
  - `test_kb_documents_injected_before_llm_call`
  - `test_document_citations_preserved_in_response`
  - `test_user_attachment_context_not_affected`
  - `test_token_budget_respects_kb_priority`
- Fixtures:
  - `mock_llm_response` - Configurable mock LLM
  - `test_document` - Sample document fixtures
  - `test_session` - Session with context
  - `golden_set_entry` - Sample golden set FAQ entry
  - `kb_document` - Sample KB document for injection

**Testing Requirements:**
- **TDD:** Write tests FIRST (before any manual testing)
- **Unit Tests:** Not applicable (integration tests)
- **Integration Tests:** 10+ tests covering all major flows
  - Non-streaming: 5 tests
  - Streaming: 4 tests
  - Context: 2 tests
- **Regression Tests:** Run with full test suite
- **Coverage Target:** 85%+ for integration paths

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mocking complexity | MEDIUM | Use pytest-mock, clear mock setup |
| Test flakiness | MEDIUM | Avoid async timing issues |
| Maintenance burden | LOW | Clear test structure, shared fixtures |

**Code Structure:**
- One test class per endpoint
- Shared fixtures at module level
- Clear mock configuration

**Code Completeness:**
- [ ] All 10+ integration tests implemented
- [ ] All major flows covered
- [ ] Mocking complete and accurate
- [ ] No manual testing steps required

**Acceptance Criteria:**
- [ ] 15+ integration tests covering all major flows
- [ ] Mocked LLM (no real API calls)
- [ ] Full request/response cycle tested
- [ ] Streaming endpoint tested with SSE client
- [ ] All 5 golden set/KB regression tests pass
- [ ] Document context flow verified unchanged
- [ ] Golden fast-path still triggers on eligible queries
- [ ] KB documents still injected before LLM call
- [ ] All tests pass: `pytest tests/integration/test_proactivity_llm_first.py -v`
- [ ] Test execution time <60s

</details>

---

<details>
<summary>
<h3>DEV-183: E2E Validation and Quality Verification</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 1.5h | <strong>Status:</strong> NOT STARTED<br>
End-to-end validation with real LLM calls and quality assessment.
</summary>

### DEV-183: E2E Validation and Quality Verification

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.10](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1210-criteri-di-accettazione-rivisti)

**Priority:** MEDIUM | **Effort:** 1.5h | **Status:** NOT STARTED

**Problem:**
Need to verify that real LLM calls produce quality suggested actions meeting Section 12.10 acceptance criteria.

**Solution:**
Create E2E test suite with real LLM calls (rate-limited) to verify acceptance criteria from Section 12.10.

**Agent Assignment:** @clelia (tests), @egidio (quality review)

**Dependencies:**
- **Blocking:** DEV-182 (integration tests complete)
- **Unlocks:** None (final task)

**Change Classification:** ADDITIVE

**Error Handling:**
- **LLM rate limit:** Retry with exponential backoff
- **LLM timeout:** Skip test with warning, not failure
- **Cost monitoring:** Track tokens used per test run

**Performance Requirements:**
- E2E test suite: <5 minutes (rate-limited LLM calls)
- Individual test: <30s (including LLM call)
- Cost per run: <EUR 0.10

**Edge Cases:**
- **LLM downtime:** Tests skip gracefully
- **Rate limiting:** Respect API limits
- **Response variability:** Accept range of valid responses

**Files to Create:**
- `tests/e2e/test_proactivity_quality.py` (~100 lines)
- `scripts/validate_proactivity_quality.py` (~150 lines)

**Fields/Methods/Components:**
- `TestProactivityQuality` class
  - `test_interactive_question_only_for_calculable_intents`
  - `test_suggested_actions_on_every_response`
  - `test_llm_generates_2_to_4_actions`
  - `test_actions_are_pertinent_to_query`
  - `test_parsing_fails_gracefully`
  - `test_document_templates_have_priority`
- `validate_proactivity_quality.py` script
  - `run_quality_checks()` - Main validation
  - `calculate_action_relevance_score()` - LLM-as-judge
  - `measure_cost_per_query()` - Cost tracking
  - `generate_quality_report()` - Summary report

**Testing Requirements:**
- **TDD:** Write test structure FIRST
- **Unit Tests:** Not applicable (E2E tests)
- **E2E Tests:** 6+ tests with real LLM
- **Quality Script:** Validation script for manual runs
- **Coverage Target:** Not applicable (E2E tests)

**Risks & Mitigations:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM cost | MEDIUM | Rate limit tests, mock for CI |
| Flaky tests | HIGH | Allow variance, test for patterns |
| LLM behavior changes | MEDIUM | Test core behaviors, not exact outputs |

**Code Structure:**
- E2E tests separate from unit/integration
- Validation script standalone

**Code Completeness:**
- [ ] All 6 acceptance criteria tested
- [ ] Quality script complete
- [ ] Cost tracking implemented
- [ ] Report generation works

**Acceptance Criteria (from Section 12.10):**
- [ ] AC-REV.1: InteractiveQuestion ONLY for CALCULABLE_INTENTS with missing params (verified)
- [ ] AC-REV.2: SuggestedActions appears on EVERY response (verified)
- [ ] AC-REV.3: LLM generates 2-4 pertinent actions in 90%+ of responses (verified)
- [ ] AC-REV.4: Parsing fails gracefully (no crashes) (verified)
- [ ] AC-REV.5: Document templates have priority over LLM actions (verified)
- [ ] AC-REV.6: Cost increment <= EUR 0.02/user/day (measured)
- [ ] All tests pass: `pytest tests/e2e/test_proactivity_quality.py -v`
- [ ] Quality report generated successfully

</details>

---

## Summary

| Phase | Tasks | Effort | Agent |
|-------|-------|--------|-------|
| Phase 1: Foundation | DEV-150 to DEV-156 | 9h | @ezio, @clelia |
| Phase 2: API Integration | DEV-157 to DEV-162 | 6h | @ezio, @clelia |
| Phase 3: Frontend | DEV-163 to DEV-167 | 10h | @livia, @clelia |
| Phase 4: Testing | DEV-168 to DEV-172 | 6.5h | @clelia |
| Phase 5: Documentation | DEV-173 | 1h | @egidio, @ezio |
| Phase 6: LLM-First Revision | DEV-174 to DEV-183 | 17h | @ezio, @clelia |
| **Total** | **34 tasks** | **~50h** | |

**Estimated Timeline:** 3-4 weeks at 2-3h/day *(with Claude Code)*
