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
| DEV-174 to DEV-183 | Phase 6: LLM-First Revision (Backend) |
| DEV-184 to DEV-199 | Phase 7: Agentic RAG Pipeline (Backend) |

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
<h3>DEV-184: Create LLM Model Configuration System (Backend)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Created YAML-based configuration for tiered LLM model selection with 20 tests and 100% coverage.
</summary>

### DEV-184: Create LLM Model Configuration System

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** CRITICAL | **Effort:** 2h (Actual: ~1.5h)

**Problem:**
Current system uses single `LLM_MODEL` environment variable. Section 13.10 requires different models per pipeline stage:
- GPT-4o-mini for routing, query expansion, HyDE
- GPT-4o / Claude 3.5 Sonnet for critical synthesis

**Solution:**
Created YAML-based configuration (`config/llm_models.yaml`) with environment overrides for tiered model selection.

**Files Created:**
- `config/llm_models.yaml` (~60 lines)
- `app/core/llm/model_config.py` (~340 lines)
- `tests/core/llm/test_model_config.py` (~305 lines, 20 tests)

**Components Implemented:**
- `ModelTier(str, Enum)` - BASIC, PREMIUM
- `LLMModelConfig` class with:
  - `load()` / `reload()` - Load/reload YAML configuration
  - `get_model(tier)` - Get model for tier
  - `get_provider(tier)` - Get provider for tier
  - `get_timeout(tier)` - Get timeout in ms
  - `get_temperature(tier)` - Get temperature
  - `get_fallback(tier)` - Get fallback config
- `get_model_config()` - Singleton accessor
- Environment variable overrides: `LLM_MODEL_BASIC`, `LLM_MODEL_PREMIUM`

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 20 tests
- ✅ YAML config loads correctly from `config/llm_models.yaml`
- ✅ Environment variables override YAML values
- ✅ Fallback to defaults on missing/invalid config
- ✅ Model validation against known models
- ✅ 100% test coverage achieved (target was 95%+)

**Git:** Branch `DEV-184-Create-LLM-Model-Configuration-System`

</details>

---

<details>
<summary>
<h3>DEV-185: Implement PremiumModelSelector Service (Backend)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2h (Actual: ~2h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Created dynamic model selector for synthesis step with execute() method bridging to LLMFactory, 25 tests, 95%+ coverage.
</summary>

### DEV-185: Implement PremiumModelSelector Service

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** CRITICAL | **Effort:** 2h (Actual: ~2h)

**Problem:**
Step 64 (synthesis) needs dynamic model selection between GPT-4o and Claude 3.5 Sonnet based on context length and provider availability.

**Solution:**
Implemented `PremiumModelSelector` class that:
- Uses GPT-4o by default (lower cost)
- Switches to Claude 3.5 Sonnet for context >8k tokens
- Falls back to alternate provider on failure
- Pre-warms both providers at startup
- `execute()` method bridges selection to LLMFactory for actual execution
- Legacy providers unified with `LLMProviderType` enum

**Files Created:**
- `app/services/premium_model_selector.py` (~300 lines)
- `tests/services/test_premium_model_selector.py` (25 tests)

**Files Modified:**
- `app/core/llm/providers/anthropic_provider.py` - Added Claude 3.5 Sonnet to supported_models
- `app/services/anthropic_provider.py` - Added `LLMProviderType.ANTHROPIC`
- `app/services/openai_provider.py` - Added `LLMProviderType.OPENAI`

**Components Implemented:**
- `PremiumModelSelector` class with select(), execute(), pre_warm()
- `SynthesisContext` dataclass: total_tokens, query_complexity
- `ModelSelection` dataclass: model, provider, is_fallback, is_degraded

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 25 tests
- ✅ Selects GPT-4o by default
- ✅ Selects Claude 3.5 Sonnet for context >8k tokens
- ✅ Fallback works when primary provider unavailable
- ✅ Pre-warm validates API keys at startup
- ✅ Claude 3.5 Sonnet added to AnthropicProvider.supported_models
- ✅ execute() method bridges selection to LLMFactory execution
- ✅ Legacy providers unified with LLMProviderType enum
- ✅ 95%+ test coverage (25 tests)

**Git:** Branch `DEV-185-Implement-PremiumModelSelector-Service`

</details>

---

<details>
<summary>
<h3>DEV-186: Define RouterDecision Schema and Constants (Backend)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 1.5h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Created Pydantic models and enums for LLM router with 21 tests and 100% coverage.
</summary>

### DEV-186: Define RouterDecision Schema and Constants

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** CRITICAL | **Effort:** 1.5h (Actual: ~1h)

**Problem:**
Need structured types for LLM router decisions to replace the current regex-based `GateDecision`.

**Solution:**
Created Pydantic models for `RoutingCategory`, `RouterDecision`, and `ExtractedEntity` as specified in Section 13.4.4.

**Files Created:**
- `app/schemas/router.py` (~100 lines)
- `tests/schemas/test_router.py` (21 tests)

**Components Implemented:**
- `RoutingCategory` enum: CHITCHAT, THEORETICAL_DEFINITION, TECHNICAL_RESEARCH, CALCULATOR, GOLDEN_SET
- `ExtractedEntity` model: text, type, confidence
- `RouterDecision` model: route, confidence, reasoning, entities, requires_freshness, suggested_sources, needs_retrieval (computed)

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 21 tests
- ✅ All 5 routing categories defined
- ✅ RouterDecision validates confidence bounds
- ✅ JSON serialization works correctly
- ✅ 100% test coverage

**Git:** Branch `DEV-186-Define-RouterDecision-Schema-and-Constants`

</details>

---

<details>
<summary>
<h3>DEV-187: Implement LLM Router Service (Backend)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 3h (Actual: ~2h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Implemented GPT-4o-mini Chain-of-Thought router with 23 tests and 95%+ coverage.
</summary>

### DEV-187: Implement LLM Router Service

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** CRITICAL | **Effort:** 3h (Actual: ~2h)

**Problem:**
Current `retrieval_gate.py` uses 17 regex patterns, causing false negatives on complex technical queries like "Qual è l'iter per aprire P.IVA forfettaria?".

**Solution:**
Implemented `LLMRouterService` using GPT-4o-mini with Chain-of-Thought prompting to semantically classify queries into 5 routing categories.

**Files Created:**
- `app/services/llm_router_service.py` (~340 lines)
- `tests/services/test_llm_router_service.py` (23 tests)

**Components Implemented:**
- `LLMRouterService` class with:
  - `route(query, history)` - Main routing method
  - `_build_prompt(query, history)` - Prompt builder with history context
  - `_call_llm(prompt)` - LLM call via LLMFactory
  - `_parse_response(response)` - JSON parsing with markdown wrapper handling
  - `_fallback_decision()` - Returns TECHNICAL_RESEARCH on error
- Chain-of-Thought system prompt for reasoning-based decisions
- Entity extraction support (legge, articolo, ente, data)
- Fallback to TECHNICAL_RESEARCH on errors/timeouts

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 23 tests
- ✅ Routing to all 5 categories working
- ✅ Fallback to TECHNICAL_RESEARCH on error
- ✅ Entities extracted and available
- ✅ 95%+ test coverage

**Git:** Branch `DEV-187-Implement-LLM-Router-Service`

</details>

---

<details>
<summary>
<h3>DEV-188: Implement Multi-Query Generator Service (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2.5h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Implemented 3 query variants (BM25, Vector, Entity) generator with 20 tests and 100% coverage.
</summary>

### DEV-188: Implement Multi-Query Generator Service

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** HIGH | **Effort:** 2.5h (Actual: ~1.5h)

**Problem:**
Single query approach misses relevant documents. Need 3 optimized variants for different search types.

**Solution:**
Implemented `MultiQueryGeneratorService` using GPT-4o-mini to generate BM25, vector, and entity-focused query variants.

**Files Created:**
- `app/services/multi_query_generator.py` (~280 lines)
- `tests/services/test_multi_query_generator.py` (20 tests)

**Components Implemented:**
- `QueryVariants` dataclass: bm25_query, vector_query, entity_query, original_query
- `MultiQueryGeneratorService` class with:
  - `generate(query, entities)` - Main generation method
  - `_build_prompt(query, entities)` - Includes entity context
  - `_parse_response(response, original_query)` - JSON parsing
  - `_fallback_variants(query)` - Returns original on error
- `MULTI_QUERY_SYSTEM_PROMPT` - Italian prompt for 3 query types

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 20 tests
- ✅ Generates 3 distinct query variants
- ✅ BM25 query contains keywords
- ✅ Vector query semantically expanded
- ✅ Entity query includes references
- ✅ Fallback to original on error
- ✅ 100% test coverage

**Git:** Branch `DEV-188-Implement-Multi-Query-Generator-Service`

</details>

---

<details>
<summary>
<h3>DEV-189: Implement HyDE Generator Service (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2.5h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Implemented hypothetical document generation in Italian bureaucratic style with 21 tests and 100% coverage.
</summary>

### DEV-189: Implement HyDE Generator Service

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** HIGH | **Effort:** 2.5h (Actual: ~1.5h)

**Problem:**
Query embeddings differ from document embeddings. HyDE generates a hypothetical answer document whose embedding is closer to real documents.

**Solution:**
Implemented `HyDEGeneratorService` using GPT-4o-mini to generate 150-250 word hypothetical documents in Italian bureaucratic style.

**Files Created:**
- `app/services/hyde_generator.py` (~260 lines)
- `tests/services/test_hyde_generator.py` (21 tests)

**Components Implemented:**
- `HyDEResult` dataclass: hypothetical_document, word_count, skipped, skip_reason
- `HyDEGeneratorService` class with:
  - `generate(query, routing)` - Main generation method
  - `should_generate(routing)` - Skip logic for CHITCHAT/CALCULATOR
  - `_build_prompt(query)` - Prompt builder
  - `_parse_response(response)` - Word counting and parsing
- `HYDE_SYSTEM_PROMPT` - Italian bureaucratic style instructions

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 21 tests
- ✅ Italian bureaucratic style generation
- ✅ Document length 150-250 words
- ✅ Skip for CHITCHAT and CALCULATOR
- ✅ Graceful fallback on error
- ✅ 100% test coverage

**Git:** Branch `DEV-189-Implement-HyDE-Generator-Service`

</details>

---

<details>
<summary>
<h3>DEV-190: Implement Parallel Hybrid Retrieval with RRF Fusion (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3h (Actual: ~2h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Implemented parallel search with RRF fusion, source authority hierarchy, and recency boost with 20 tests.
</summary>

### DEV-190: Implement Parallel Hybrid Retrieval with RRF Fusion

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** HIGH | **Effort:** 3h (Actual: ~2h)

**Problem:**
Need to combine results from multiple search queries (BM25 + Vector + HyDE) using RRF with source authority and recency boosts.

**Solution:**
Implemented `ParallelRetrievalService` with RRF fusion per Section 13.7.

**Files Created:**
- `app/services/parallel_retrieval.py` (~490 lines)
- `tests/services/test_parallel_retrieval.py` (20 tests)

**Components Implemented:**
- `RRF_K = 60` constant for RRF formula
- `SEARCH_WEIGHTS` dict: BM25=0.3, Vector=0.4, HyDE=0.3
- `GERARCHIA_FONTI` dict: legge=1.3, decreto=1.25, circolare=1.15, risoluzione=1.1, interpello=1.05, faq=1.0, guida=0.95
- `RankedDocument` dataclass: document_id, content, score, rrf_score, source_type, source_name, published_date, metadata
- `RetrievalResult` dataclass: documents, total_found, search_time_ms
- `ParallelRetrievalService` class with:
  - `retrieve(queries, hyde, top_k)` - Main retrieval method
  - `_execute_parallel_searches(queries, hyde)` - Parallel asyncio.gather
  - `_rrf_fusion(search_results)` - RRF combination
  - `_apply_boosts(docs)` - Authority and recency boosts
  - `_calculate_recency_boost(published_date)` - +50% for <12 months
  - `_get_authority_boost(source_type)` - GERARCHIA_FONTI lookup
  - `_deduplicate(docs)` - Keep highest score
  - `_get_top_k(docs, k)` - Return top K results

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 20 tests
- ✅ RRF combines all search results
- ✅ Recency boost applied (+50% for docs <12 months)
- ✅ Authority hierarchy respected (legge > circolare > faq)
- ✅ Top 10 documents returned by default
- ✅ Metadata preserved in results
- ✅ Deduplication by document_id
- ✅ 100% test coverage

**Git:** Branch `DEV-190-Implement-Parallel-Hybrid-Retrieval-with-RRF-Fusion`

</details>

---

<details>
<summary>
<h3>DEV-191: Create Document Metadata Preservation Layer (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Implemented metadata extraction and context formatting for LLM synthesis with 19 tests.
</summary>

### DEV-191: Create Document Metadata Preservation Layer

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** HIGH | **Effort:** 2h (Actual: ~1h)

**Problem:**
Document metadata (date, source, type, hierarchy) must flow from retrieval to synthesis for proper chronological analysis and source indexing.

**Solution:**
Implemented `MetadataExtractor` service that extracts DocumentMetadata from RankedDocuments and formats context per Section 13.9.3.

**Files Created:**
- `app/services/metadata_extractor.py` (~240 lines)
- `tests/services/test_metadata_extractor.py` (19 tests)

**Components Implemented:**
- `DocumentMetadata` dataclass: document_id, title, date_published, source_entity, document_type, hierarchy_level, reference_code, url, relevance_score, text_excerpt
- `HIERARCHY_LEVELS` constant: legge=1, decreto=2, circolare=3, risoluzione=4, interpello=5, faq=6, guida=7
- `MetadataExtractor` class with:
  - `extract()` - Convert RankedDocument to DocumentMetadata
  - `extract_all()` - Batch extraction from RetrievalResult
  - `sort_by_date()` - Sort documents (most recent first)
  - `format_reference_code()` - Format legal references (L., Circ., D.Lgs.)
  - `format_context_for_synthesis()` - Create formatted context with emojis and structure

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 19 tests
- ✅ All metadata preserved from retrieval
- ✅ Documents sorted by date (most recent first)
- ✅ Hierarchy level explicit in context
- ✅ Reference code formatted correctly
- ✅ URL preserved when available
- ✅ 100% test coverage

**Git:** Branch `DEV-191-Create-Document-Metadata-Preservation-Layer`

</details>

---

<details>
<summary>
<h3>DEV-192: Create Critical Synthesis Prompt Template (Backend)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Created synthesis system prompt with Verdetto Operativo structure and SynthesisPromptBuilder per Section 13.8.5.
</summary>

### DEV-192: Create Critical Synthesis Prompt Template

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** CRITICAL | **Effort:** 2h (Actual: ~1.5h)

**Problem:**
Step 64 needs a new system prompt that instructs the LLM to produce structured Verdetto Operativo output with conflict detection and source hierarchy.

**Solution:**
Created `SYNTHESIS_SYSTEM_PROMPT` per Section 13.8.5 with all 4 compiti (chronological analysis, conflict detection, hierarchy application, Verdetto Operativo structure).

**Files Created:**
- `app/core/prompts/synthesis_critical.py` (~145 lines)
- `app/services/synthesis_prompt_builder.py` (~170 lines)
- `tests/core/prompts/test_synthesis_prompt.py` (29 tests)

**Components Implemented:**
- `SYNTHESIS_SYSTEM_PROMPT` constant - Full system prompt with 4 compiti
- `VERDETTO_OPERATIVO_TEMPLATE` - Structured output template with emojis
- `HIERARCHY_RULES` - Source authority rules (Legge > Decreto > Circolare)
- `SynthesisPromptBuilder` class:
  - `get_system_prompt()` - Return system prompt
  - `build(context, query)` - Build user prompt with context
  - `get_hierarchy_rules()` - Get hierarchy rules
  - `get_verdetto_template()` - Get verdetto template
  - `build_with_custom_instructions()` - Build with extra instructions

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 29 tests
- ✅ Prompt includes all 4 compiti from Section 13.8.5
- ✅ Verdetto Operativo structure defined
- ✅ Hierarchy rules explicit
- ✅ Prudent approach emphasized
- ✅ 100% test coverage for builder

**Git:** Branch `DEV-192-Create-Critical-Synthesis-Prompt-Template-(Backend)-`

</details>

---

<details>
<summary>
<h3>DEV-193: Implement Verdetto Operativo Output Parser (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Implemented parser to extract structured Verdetto Operativo sections from LLM synthesis output with 27 tests.
</summary>

### DEV-193: Implement Verdetto Operativo Output Parser

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** HIGH | **Effort:** 3h (Actual: ~1.5h)

**Problem:**
LLM synthesis output must be parsed to extract structured Verdetto Operativo sections for API response.

**Solution:**
Implemented `VerdettoOperativoParser` that extracts all 5 sections per Section 13.8.4.

**Files Created:**
- `app/schemas/verdetto.py` (~95 lines)
- `app/services/verdetto_parser.py` (~320 lines)
- `tests/services/test_verdetto_parser.py` (27 tests)

**Components Implemented:**
- `FonteReference` schema for source references from INDICE DELLE FONTI table
- `VerdettoOperativo` schema with all 5 sections
- `ParsedSynthesis` schema for complete parsing result
- `VerdettoOperativoParser` class with:
  - `parse(response)` - Main parsing method
  - `_extract_answer_text()` - Text before VERDETTO OPERATIVO
  - `_extract_section()` - Extract individual sections by markers
  - `_extract_documentazione_list()` - Parse bulleted list
  - `_parse_fonti_table()` - Parse markdown table

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 27 tests
- ✅ Extracts all 5 Verdetto sections
- ✅ Handles missing sections gracefully (returns None)
- ✅ Parses fonti table correctly
- ✅ Never raises on malformed input
- ✅ All tests passing

**Git:** Branch `DEV-193-Implement-Verdetto-Operativo-Output-Parser`

</details>

---

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

<details>
<summary>
<h3>DEV-174: Define CALCULABLE_INTENTS and DOCUMENT_ACTION_TEMPLATES Constants</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 1h | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Created core constants for LLM-First proactivity: 5 calculable intents and 4 document action templates with 29 tests.
</summary>

### DEV-174: Define CALCULABLE_INTENTS and DOCUMENT_ACTION_TEMPLATES Constants

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** CRITICAL | **Effort:** 1h

**Problem:**
The current architecture uses complex template matching for all queries. The LLM-First approach requires a clear, minimal set of constants.

**Solution:**
Created `app/core/proactivity_constants.py` with CALCULABLE_INTENTS (5 intents) and DOCUMENT_ACTION_TEMPLATES (4 document types).

**Files Created:**
- `app/core/proactivity_constants.py` (~130 lines)
- `tests/core/test_proactivity_constants.py` (~280 lines, 29 tests)

**Constants Implemented:**
- `CALCULABLE_INTENTS`: calcolo_irpef, calcolo_iva, calcolo_contributi_inps, ravvedimento_operoso, calcolo_f24
- `DOCUMENT_ACTION_TEMPLATES`: fattura_elettronica (4 actions), f24 (3), bilancio (3), cu (3)
- `CalculableIntent` and `ActionTemplate` TypedDict definitions

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 29 tests
- ✅ CALCULABLE_INTENTS has exactly 5 entries as per Section 12.4
- ✅ DOCUMENT_ACTION_TEMPLATES has exactly 4 document types as per Section 12.6
- ✅ 100% test coverage for new file
- ✅ All tests pass

**Git:** Branch `DEV-174-Define-CALCULABLE_INTENTS-and-DOCUMENT_ACTION_TEMPLATES-Constants`

</details>

---

<details>
<summary>
<h3>DEV-175: Update System Prompt with Suggested Actions Output Format</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 1h | <strong>Status:</strong> ✅ COMPLETED (2024-12-27)<br>
Created suggested_actions.md prompt with &lt;answer&gt; and &lt;suggested_actions&gt; format instructions and 16 tests.
</summary>

### DEV-175: Update System Prompt with Suggested Actions Output Format

**Status:** ✅ COMPLETED (2024-12-27)
**Priority:** CRITICAL | **Effort:** 1h

**Problem:**
The current system prompt does not instruct the LLM to generate suggested actions with structured XML-like tags.

**Solution:**
Created `app/core/prompts/suggested_actions.md` with output format specification and added `load_suggested_actions_prompt()` function.

**Files Created:**
- `app/core/prompts/suggested_actions.md` (~50 lines, ~429 tokens)
- `tests/core/prompts/test_suggested_actions_prompt.py` (~190 lines, 16 tests)

**Modified:**
- `app/core/prompts/__init__.py` - Added loader function and `SUGGESTED_ACTIONS_PROMPT` constant

**Features Implemented:**
- Output format with `<answer>` and `<suggested_actions>` tags
- Action requirements (pertinent, professional, actionable, diverse)
- Category-specific examples (fiscal, normative, procedural, document)
- Icon reference table (10 emoji icons)

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 16 tests
- ✅ `suggested_actions.md` file created with full instruction set
- ✅ `load_suggested_actions_prompt()` function added
- ✅ Prompt token count ~429 (within 400-500 limit)
- ✅ All tests pass

**Git:** Branch `DEV-175-Update-System-Prompt-with-Suggested-Actions-Output-Format`

</details>

<details>
<summary>
<h3>✅ DEV-176: Implement parse_llm_response Function</h3>
<strong>Status:</strong> DONE | <strong>Branch:</strong> DEV-176-Implement-parse_llm_response-Function
</summary>

### DEV-176: Implement parse_llm_response Function

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.5.2](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1252-parsing-della-risposta)

**Problem:**
The LLM outputs responses with `<answer>` and `<suggested_actions>` XML-like tags. Need a robust parser that extracts these components and handles edge cases gracefully without ever raising exceptions.

**Solution:**
Created `app/services/llm_response_parser.py` with compiled regex patterns and Pydantic models for type-safe parsing.

**Files Created:**
- `app/services/llm_response_parser.py` (~155 lines)
- `tests/services/test_llm_response_parser.py` (~300 lines, 21 tests)
- `tests/services/conftest.py` - Mock database service for unit tests

**Features Implemented:**
- `parse_llm_response()` main function - never raises exceptions
- `ParsedLLMResponse` and `SuggestedAction` Pydantic models
- `_extract_answer()` helper with fallback to full response
- `_extract_actions()` helper with JSON parsing and validation
- `_validate_action()` for field validation
- Compiled regex patterns for performance
- Max 4 actions limit with truncation

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 21 tests
- ✅ Parser never raises exceptions (graceful fallback)
- ✅ Actions truncated to max 4
- ✅ Invalid actions skipped, valid ones included
- ✅ Citations preserved in answer text
- ✅ All tests pass

**Git:** Branch `DEV-176-Implement-parse_llm_response-Function`

</details>

<details>
<summary>
<h3>✅ DEV-177: Simplify ProactivityEngine Decision Logic</h3>
<strong>Status:</strong> DONE | <strong>Branch:</strong> DEV-177-Simplify-ProactivityEngine-Decision-Logic
</summary>

### DEV-177: Simplify ProactivityEngine Decision Logic

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.7](/docs/tasks/PRATIKO_1.5_REFERENCE.md#127-logica-decisionale-completa)

**Problem:**
The current ProactivityEngine uses complex template matching (~492 lines). Per Section 12.7, the logic should be simplified to three steps.

**Solution:**
Created `app/services/proactivity_engine_simplified.py` implementing the LLM-First decision logic with no external dependencies.

**Files Created:**
- `app/services/proactivity_engine_simplified.py` (~280 lines)
- `tests/services/test_proactivity_engine_simplified.py` (~400 lines, 38 tests)

**Features Implemented:**
- `ProactivityEngine` class with no external dependencies
- `process_query()` with 3-step decision logic:
  1. Calculable intent with missing params → InteractiveQuestion
  2. Recognized document type → template actions
  3. Otherwise → use_llm_actions flag
- `_classify_intent()` with compiled regex patterns
- `_extract_parameters()` for parameter extraction
- `_build_question_for_missing()` for question generation
- `ProactivityResult` Pydantic model

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 38 tests
- ✅ Decision logic follows Section 12.7 exactly
- ✅ InteractiveQuestion ONLY for 5 calculable intents
- ✅ Template actions ONLY for 4 document types
- ✅ LLM actions flag set for everything else
- ✅ Performance: decision logic <10ms
- ✅ All tests pass

**Git:** Branch `DEV-177-Simplify-ProactivityEngine-Decision-Logic`

</details>

<details>
<summary>
<h3>✅ DEV-178: Remove Unused Templates and Simplify Template Service</h3>
<strong>Status:</strong> DONE | <strong>Branch:</strong> DEV-178-Remove-Unused-Templates-and-Simplify-Template-Service
</summary>

### DEV-178: Remove Unused Templates and Simplify Template Service

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.11](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1211-piano-di-migrazione)

**Problem:**
The current template system has ~50+ scenarios across domain-specific YAML files (2,572 lines). With LLM-First architecture, templates are replaced by DOCUMENT_ACTION_TEMPLATES constants.

**Solution:**
Archived entire `ActionTemplateService`, unused YAML template files, and `AtomicFactsExtractor` to `archived/phase5_templates/` to preserve git history while removing obsolete code.

**Files Archived:**
- `archived/phase5_templates/services/action_template_service.py` (432 lines)
- `archived/phase5_templates/services/atomic_facts_extractor.py`
- `archived/phase5_templates/templates/suggested_actions/*.yaml`
- `archived/phase5_templates/templates/interactive_questions/*.yaml`
- `archived/phase5_templates/tests/test_action_template_service.py`
- `archived/phase5_templates/tests/test_atomic_facts_parameter_coverage.py`

**Files Modified:**
- `app/api/v1/chatbot.py` - Updated imports to use archived path with fallback
- `app/orchestrators/facts.py` - Updated import with try/except fallback
- `app/services/proactivity_engine.py` - Removed template service import
- `tests/test_rag_step_*.py` - Updated imports to archived path

**Acceptance Criteria (All Met):**
- ✅ All obsolete files archived to `archived/phase5_templates/`
- ✅ ActionTemplateService completely archived
- ✅ AtomicFactsExtractor archived
- ✅ No orphan imports in codebase
- ✅ All existing tests updated or archived
- ✅ All tests pass
- ✅ Git history preserved (archive, not delete)

**Git:** Branch `DEV-178-Remove-Unused-Templates-and-Simplify-Template-Service`, PR #870

</details>

<details>
<summary>
<h3>✅ DEV-179: Integrate LLM-First Proactivity in /chat Endpoint</h3>
<strong>Status:</strong> DONE | <strong>Branch:</strong> DEV-179-Integrate-LLM-First-Proactivity-in-chat-Endpoint
</summary>

### DEV-179: Integrate LLM-First Proactivity in /chat Endpoint

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.7](/docs/tasks/PRATIKO_1.5_REFERENCE.md#127-logica-decisionale-completa)

**Problem:**
The current /chat endpoint calls ProactivityEngine separately from LLM. The LLM-First approach requires:
1. Injecting suggested_actions prompt into system prompt
2. Parsing LLM response to extract actions
3. Overriding with document templates when applicable

**Solution:**
Added new helper functions to integrate the simplified ProactivityEngine and LLM response parser:
- `get_simplified_proactivity_engine()` - Returns DEV-177 engine singleton
- `inject_proactivity_prompt()` - Appends suggested_actions prompt
- `apply_action_override()` - Template actions take priority over LLM actions

**Three-Step Decision Logic (Section 12.7):**
1. Calculable intent with missing params → InteractiveQuestion
2. Recognized document type → template actions (DOCUMENT_ACTION_TEMPLATES)
3. Otherwise → LLM generates actions

**Files Modified:**
- `app/api/v1/chatbot.py` - Added LLM-First helper functions
- `tests/api/test_chatbot_llm_first.py` - 19 TDD tests

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD)
- ✅ Helper functions implemented for prompt injection
- ✅ Parser integration complete
- ✅ Template override logic complete
- ✅ All 19 tests pass
- ✅ Backward compatible API response schema

**Git:** Branch `DEV-179-Integrate-LLM-First-Proactivity-in-chat-Endpoint`

</details>

<details>
<summary>
<h3>✅ DEV-180: Integrate LLM-First Proactivity in /chat/stream Endpoint</h3>
<strong>Status:</strong> DONE | <strong>Branch:</strong> DEV-180-Integrate-LLM-First-Proactivity-in-chat-stream-Endpoint
</summary>

### DEV-180: Integrate LLM-First Proactivity in /chat/stream Endpoint

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.7](/docs/tasks/PRATIKO_1.5_REFERENCE.md#127-logica-decisionale-completa)

**Problem:**
The /chat/stream endpoint streams LLM tokens in real-time. We need to:
1. Buffer the complete response for parsing
2. Strip XML tags from streamed content
3. Send actions as final SSE event

**Solution:**
Implemented streaming tag stripping and buffering helpers:
- `strip_xml_tags()` - Removes `<answer>` and `<suggested_actions>` tags
- `StreamBuffer` class - Accumulates chunks during streaming
- `StreamTagState` class - Tracks partial tags across chunk boundaries
- `process_stream_chunk()` - Handles partial tags spanning multiple chunks
- `format_actions_sse_event()` - Formats SSE event for actions
- `format_question_sse_event()` - Formats SSE event for questions

**Key Features:**
- Handles partial tags spanning multiple chunks
- Preserves citations `[1]`, `[2]` and markdown formatting
- SSE events for `suggested_actions` and `interactive_question`
- Graceful handling of malformed tags
- Buffer with configurable max size (default 1MB)

**Files Modified:**
- `app/api/v1/chatbot.py` - Added streaming helper functions
- `tests/api/test_chatbot_stream_llm_first.py` - 28 TDD tests

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD)
- ✅ Tag stripping complete
- ✅ Buffer management complete
- ✅ All SSE events implemented
- ✅ All 28 tests pass
- ✅ Partial tag handling works across chunk boundaries

**Git:** Branch `DEV-180-Integrate-LLM-First-Proactivity-in-chat-stream-Endpoint`

</details>

<details>
<summary>
<h3>✅ DEV-181: Unit Tests for LLM-First Components</h3>
<strong>Status:</strong> DONE | <strong>Branch:</strong> DEV-181-Unit-Tests-for-LLM-First-Components
</summary>

### DEV-181: Unit Tests for LLM-First Components

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.10](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1210-criteri-di-accettazione-rivisti)

**Problem:**
Need comprehensive unit test coverage for all new/modified components to ensure LLM-First architecture works correctly.

**Solution:**
TDD approach in DEV-174 to DEV-180 already created all required tests. DEV-181 verifies test coverage meets requirements.

**Test Coverage (Requirement: 67+ tests):**

| Test File | Tests | Requirement |
|-----------|-------|-------------|
| `test_proactivity_constants.py` | 29 | 15 |
| `test_suggested_actions_prompt.py` | 15 | 7 |
| `test_llm_response_parser.py` | 21 | 20 |
| `test_proactivity_engine_simplified.py` | 38 | 25 |
| **Total** | **104** | **67+** |

**Performance:**
- Execution time: 0.17s (requirement: <30s)
- All 104 tests pass

**Acceptance Criteria (All Met):**
- ✅ 104 tests (153% of 67+ requirement)
- ✅ 95%+ coverage for new modules
- ✅ All tests follow AAA pattern
- ✅ All tests pass
- ✅ Test execution time: 0.17s (<30s requirement)

**Git:** Branch `DEV-181-Unit-Tests-for-LLM-First-Components`

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

**Note:** DEV-174 to DEV-183 (Phase 6 complete) moved to Completed Tasks section above.

---

<details>
<summary>
<h3>✅ DEV-182: Integration Tests for LLM-First Flow</h3>
<strong>Status:</strong> DONE | <strong>Branch:</strong> DEV-182-Integration-Tests-for-LLM-First-Flow
</summary>

### DEV-182: Integration Tests for LLM-First Flow

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.10](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1210-criteri-di-accettazione-rivisti)

**Problem:**
Need integration tests that verify the complete flow from API request through proactivity engine to response with actions.

**Solution:**
Create integration tests that mock LLM but test full component integration.

**Test Coverage (Requirement: 15+ tests):**

| Test Class | Tests | Coverage |
|-----------|-------|----------|
| `TestLLMFirstProactivityIntegration` | 10 | Actions, templates, questions, streaming |
| `TestGoldenSetKBRegression` | 5 | Golden set, KB injection, citations |
| `TestEdgeCases` | 5 | Empty queries, unknown docs, concurrency |
| **Total** | **20** | **15+** |

**Performance:**
- Execution time: 1.53s (requirement: <60s)
- All 20 tests pass

**Acceptance Criteria (All Met):**
- ✅ 20 integration tests (133% of 15+ requirement)
- ✅ Mocked LLM (no real API calls)
- ✅ Full request/response cycle tested
- ✅ Streaming endpoint tested with SSE events
- ✅ All 5 golden set/KB regression tests pass
- ✅ Document context flow verified unchanged
- ✅ All tests pass: `pytest tests/integration/test_proactivity_llm_first.py -v`
- ✅ Test execution time: 1.53s (<60s requirement)

**Git:** Branch `DEV-182-Integration-Tests-for-LLM-First-Flow`

</details>

---

<details>
<summary>
<h3>✅ DEV-183: E2E Validation and Quality Verification</h3>
<strong>Status:</strong> DONE | <strong>Branch:</strong> DEV-183-E2E-Validation-and-Quality-Verification
</summary>

### DEV-183: E2E Validation and Quality Verification

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 12.10](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1210-criteri-di-accettazione-rivisti)

**Problem:**
Need to verify that the LLM-First proactivity architecture meets Section 12.10 acceptance criteria.

**Solution:**
Created E2E test suite in `tests/e2e/test_proactivity_quality.py` verifying all acceptance criteria.

**Test Coverage (Requirement: 6+ tests):**

| Test Class | Tests | Coverage |
|-----------|-------|----------|
| `TestProactivityQuality` | 9 | AC-REV.1 to AC-REV.5 verification |
| `TestProactivityCostTracking` | 2 | AC-REV.6 cost controls |
| **Total** | **11** | **6+** |

**Performance:**
- Execution time: 1.32s (requirement: <5 minutes)
- All 11 tests pass

**Acceptance Criteria (All Met):**
- ✅ AC-REV.1: InteractiveQuestion ONLY for CALCULABLE_INTENTS with missing params
- ✅ AC-REV.2: SuggestedActions appears on EVERY response
- ✅ AC-REV.3: LLM generates 2-4 pertinent actions (parser enforces max 4)
- ✅ AC-REV.4: Parsing fails gracefully (no crashes)
- ✅ AC-REV.5: Document templates have priority over LLM actions
- ✅ AC-REV.6: Cost controls verified (prompt size <2000 chars, max 4 actions)
- ✅ All tests pass: `pytest tests/e2e/test_proactivity_quality.py -v`

**Phase 6 Complete Summary:**
- **Total Tests:** 182 (171 Phase 6 + 11 E2E)
- **Execution Time:** <3s total
- **Pass Rate:** 100%

**Git:** Branch `DEV-183-E2E-Validation-and-Quality-Verification`

</details>

---

## Phase 7: Agentic RAG Pipeline - 39h

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 13](/docs/tasks/PRATIKO_1.5_REFERENCE.md#13-evoluzione-verso-agentic-rag)

**Objective:** Transform PratikoAI from traditional RAG to an "Agentic RAG" system with:
- LLM-based semantic routing (replacing regex)
- Multi-Query Generation + HyDE for improved retrieval
- RRF Fusion with source authority hierarchy
- Critical synthesis with Verdetto Operativo output

**Timeline:**
- Phase 7A: Model Selection Infrastructure (DEV-184 to DEV-185) - 0.5 days
- Phase 7B: Router and Query Expansion (DEV-186 to DEV-189) - 1.5 days
- Phase 7C: Retrieval Enhancement (DEV-190 to DEV-191) - 0.5 days
- Phase 7D: Synthesis and Verdetto (DEV-192 to DEV-193) - 0.5 days
- Phase 7E: LangGraph Integration (DEV-194 to DEV-196) - 1 day
- Phase 7F: Testing and Validation (DEV-197 to DEV-199) - 1 day

**User Decisions:**
- **Provider Strategy:** GPT-4o primary, Claude 3.5 Sonnet fallback
- **Dual-Provider Failure:** Return degraded response without Verdetto, with disclaimer
- **Startup:** Pre-warm both providers to validate API keys early

Phase 7 changes MUST NOT disrupt the existing document retrieval and injection flow:
- Golden Set fast-path MUST continue to work (confidence >= 0.85)
- KB hybrid search (BM25 + Vector + Recency) MUST remain unchanged
- Document context MUST be injected before LLM call
- Token budget allocation MUST respect KB documents priority
- All Phase 7 tasks must include regression tests for document flow

### Phase 7 Dependency Map

```
DEV-184 (LLM Config)
    └── DEV-185 (PremiumModelSelector)
            └── DEV-196 (Step 64)
    └── DEV-186 (RouterDecision)
            └── DEV-187 (Router Service)
                    ├── DEV-188 (Multi-Query)
                    │       └── DEV-190 (Parallel Retrieval)
                    └── DEV-189 (HyDE)
                            └── DEV-190 (Parallel Retrieval)
                                    └── DEV-191 (Metadata)
                                            └── DEV-192 (Synthesis Prompt)
                                                    └── DEV-193 (Verdetto Parser)
                                                            └── DEV-194/195/196 (Nodes)
                                                                    └── DEV-197/198/199 (Tests)
```

---

<details>
<summary>
<h3>DEV-194: Create Step 34a LLM Router Node (Backend)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2.5h | <strong>Status:</strong> NOT STARTED | <strong>Type:</strong> Backend<br>
LangGraph node for semantic routing per Section 13.3.
</summary>

### DEV-194: Create Step 34a LLM Router Node

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 13.3](/docs/tasks/PRATIKO_1.5_REFERENCE.md#133-nuova-architettura-agentic-rag-pipeline)

**Priority:** CRITICAL | **Effort:** 2.5h | **Status:** NOT STARTED | **Type:** Backend

**Problem:**
LangGraph needs a new node for LLM-based routing at Step 34a.

**Solution:**
Create `step_034a__llm_router.py` node that:
- Uses `LLMRouterService` for classification
- Sets `routing_decision` in state
- Fallback to TECHNICAL_RESEARCH on error

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-187 (Router Service)
- **Unlocks:** DEV-195 (Step 39 nodes)

**Change Classification:** ADDITIVE

**Files to Create:**
- `app/core/langgraph/nodes/step_034a__llm_router.py` (~100 lines)
- `tests/core/langgraph/nodes/test_step_034a__llm_router.py` (~150 lines)

**Files to Update:**
- `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd` - Update S034a to reflect LLM Router with Chain-of-Thought

**Documentation to Create:**
- `docs/architecture/steps/STEP-34a-RAG.routing.llm.router.semantic.classification.md`

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Integrates with LLMRouterService
- [ ] Sets routing_decision in GraphState
- [ ] Fallback to TECHNICAL_RESEARCH on error
- [ ] <100 lines per CLAUDE.md guidelines
- [ ] 95%+ test coverage
- [ ] Architecture diagram updated with new routing node
- [ ] Step documentation created

</details>

---

<details>
<summary>
<h3>DEV-195: Create Step 39 Query Expansion Nodes (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2.5h | <strong>Status:</strong> NOT STARTED | <strong>Type:</strong> Backend<br>
LangGraph nodes for Multi-Query, HyDE, and Parallel Retrieval.
</summary>

### DEV-195: Create Step 39 Query Expansion Nodes

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 13.3](/docs/tasks/PRATIKO_1.5_REFERENCE.md#133-nuova-architettura-agentic-rag-pipeline)

**Priority:** HIGH | **Effort:** 2.5h | **Status:** NOT STARTED | **Type:** Backend

**Problem:**
LangGraph needs nodes for Step 39a (Multi-Query), 39b (HyDE), and 39c (Parallel Retrieval).

**Solution:**
Create three nodes that integrate with corresponding services:
- Skip expansion for CHITCHAT/THEORETICAL
- Skip HyDE for CALCULATOR

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-188 (Multi-Query), DEV-189 (HyDE), DEV-190 (Retrieval)
- **Unlocks:** DEV-196 (Step 64)

**Change Classification:** ADDITIVE

**Files to Create:**
- `app/core/langgraph/nodes/step_039a__multi_query.py` (~80 lines)
- `app/core/langgraph/nodes/step_039b__hyde.py` (~80 lines)
- `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` (~100 lines)
- `tests/core/langgraph/nodes/test_step_039_query_expansion.py` (~200 lines)

**Files to Update:**
- `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd` - Add Step 39a/39b/39c nodes for query expansion pipeline

**Documentation to Create:**
- `docs/architecture/steps/STEP-39a-RAG.query.multi.query.expansion.md`
- `docs/architecture/steps/STEP-39b-RAG.query.hyde.hypothetical.document.md`
- `docs/architecture/steps/STEP-39c-RAG.retrieval.parallel.hybrid.rrf.fusion.md`

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Each node <100 lines
- [ ] Skip logic for non-technical routes
- [ ] Proper state updates
- [ ] 95%+ test coverage
- [ ] Architecture diagram updated with new query expansion nodes
- [ ] Step documentation created for each sub-step

</details>

---

<details>
<summary>
<h3>DEV-196: Update Step 64 for Premium Model and Verdetto (Backend)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 3h | <strong>Status:</strong> NOT STARTED | <strong>Type:</strong> Backend<br>
Integrate PremiumModelSelector and Verdetto parser into Step 64.
</summary>

### DEV-196: Update Step 64 for Premium Model and Verdetto

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 13.8](/docs/tasks/PRATIKO_1.5_REFERENCE.md#138-fr-008-sintesi-critica-e-verdetto-operativo)

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED | **Type:** Backend

**Problem:**
Step 64 needs to use premium model selection and produce Verdetto Operativo output.

**Solution:**
Modify `step_064__llm_call.py` to:
- Use `PremiumModelSelector` for model choice
- Use `SynthesisPromptBuilder` for system prompt
- Use `VerdettoOperativoParser` for output
- Return degraded response if both providers fail

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-185 (Selector), DEV-192 (Prompt), DEV-193 (Parser), DEV-195 (Step 39)
- **Unlocks:** DEV-197 (Tests)

**Change Classification:** RESTRUCTURING

**Pre-Implementation Verification:**
- [ ] All existing Step 64 tests documented
- [ ] Baseline test pass rate captured
- [ ] Rollback plan ready

**Files to Modify:**
- `app/core/langgraph/nodes/step_064__llm_call.py`

**Acceptance Criteria:**
- [ ] Tests updated BEFORE implementation (TDD)
- [ ] Uses PremiumModelSelector
- [ ] Uses SynthesisPromptBuilder for TECHNICAL_RESEARCH
- [ ] Parses Verdetto Operativo from response
- [ ] Degraded response on dual-provider failure
- [ ] All existing Step 64 tests pass
- [ ] 95%+ test coverage

</details>

---

<details>
<summary>
<h3>DEV-197: Unit Tests for Phase 7 Components (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2h | <strong>Status:</strong> NOT STARTED | <strong>Type:</strong> Backend<br>
Comprehensive unit tests for all Phase 7 services.
</summary>

### DEV-197: Unit Tests for Phase 7 Components

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 13.12](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1312-criteri-di-accettazione-complessivi)

**Priority:** HIGH | **Effort:** 2h | **Status:** NOT STARTED | **Type:** Backend

**Problem:**
All Phase 7 components need comprehensive unit test coverage.

**Solution:**
Consolidate and verify all unit tests created during TDD in DEV-184 to DEV-196.

**Agent Assignment:** @clelia (primary)

**Dependencies:**
- **Blocking:** DEV-184 to DEV-196 (all implementation)
- **Unlocks:** DEV-198 (Integration)

**Files to Verify:**
- All `tests/` files created in DEV-184 to DEV-196 (145+ tests)

**Acceptance Criteria:**
- [ ] 145+ unit tests across all Phase 7 components
- [ ] 95%+ coverage for each new service
- [ ] All mocks properly isolated
- [ ] No flaky tests
- [ ] All tests pass: `pytest tests/ -k "phase7" -v`

</details>

---

<details>
<summary>
<h3>DEV-198: Integration Tests for Agentic RAG Flow (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2.5h | <strong>Status:</strong> NOT STARTED | <strong>Type:</strong> Backend<br>
End-to-end integration tests with mocked LLM.
</summary>

### DEV-198: Integration Tests for Agentic RAG Flow

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 13.12](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1312-criteri-di-accettazione-complessivi)

**Priority:** HIGH | **Effort:** 2.5h | **Status:** NOT STARTED | **Type:** Backend

**Problem:**
Need to verify the complete Agentic RAG pipeline works end-to-end.

**Solution:**
Create integration tests with mocked LLM that verify:
- Full pipeline from query to Verdetto
- Golden Set fast-path still works
- KB hybrid search unchanged
- Document context injection

**Agent Assignment:** @clelia (primary)

**Dependencies:**
- **Blocking:** DEV-197 (Unit tests)
- **Unlocks:** DEV-199 (E2E)

**Files to Create:**
- `tests/integration/test_agentic_rag_pipeline.py` (~400 lines)

**Key Test Classes:**
- `TestAgenticRAGPipeline` - Full flow tests
- `TestGoldenSetKBRegression` - Regression tests (CRITICAL)

**Acceptance Criteria:**
- [ ] Full pipeline integration tested
- [ ] Golden Set fast-path verified
- [ ] KB hybrid search unchanged
- [ ] Document injection verified
- [ ] All tests pass: `pytest tests/integration/test_agentic_rag_pipeline.py -v`

</details>

---

<details>
<summary>
<h3>DEV-199: E2E Validation with Real LLM Calls (Backend)</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 2.5h | <strong>Status:</strong> NOT STARTED | <strong>Type:</strong> Backend<br>
Validate acceptance criteria with real LLM calls.
</summary>

### DEV-199: E2E Validation with Real LLM Calls

**Reference:** [PRATIKO_1.5_REFERENCE.md Section 13.12](/docs/tasks/PRATIKO_1.5_REFERENCE.md#1312-criteri-di-accettazione-complessivi)

**Priority:** MEDIUM | **Effort:** 2.5h | **Status:** NOT STARTED | **Type:** Backend

**Problem:**
Need to validate all AC-ARAG criteria with actual LLM responses.

**Solution:**
Create E2E test suite with real LLM calls (rate-limited) to verify:
- AC-ARAG.1 to AC-ARAG.12

**Agent Assignment:** @clelia (primary), @egidio (quality review)

**Dependencies:**
- **Blocking:** DEV-198 (Integration tests)
- **Unlocks:** None (final task)

**Files to Create:**
- `tests/e2e/test_agentic_rag_quality.py` (~200 lines)
- `scripts/validate_agentic_rag_quality.py` (~150 lines)

**Acceptance Criteria:**
- [ ] AC-ARAG.1: Routing accuracy ≥90%
- [ ] AC-ARAG.2: False negatives <5%
- [ ] AC-ARAG.3: Routing latency ≤200ms P95
- [ ] AC-ARAG.4: Precision@5 improved ≥20%
- [ ] AC-ARAG.5: Recall improved ≥15%
- [ ] AC-ARAG.6: HyDE plausible 95%+
- [ ] AC-ARAG.7: Verdetto in 100% technical responses
- [ ] AC-ARAG.8: Conflicts detected
- [ ] AC-ARAG.9: Fonti index complete
- [ ] AC-ARAG.10: E2E latency ≤5s P95
- [ ] AC-ARAG.11: Cost ≤$0.02/query
- [ ] AC-ARAG.12: No regressions
- [ ] Quality report generated

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
| Phase 7: Agentic RAG Pipeline | DEV-184 to DEV-199 | 39h | @ezio, @clelia, @primo |
| **Total** | **50 tasks** | **~89h** | |

**Estimated Timeline:** 5-6 weeks at 3h/day *(with Claude Code)*
