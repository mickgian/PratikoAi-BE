# PratikoAI v1.5 - Proactive Assistant Tasks

**Version:** 1.5
**Date:** December 2025
**Status:** IN PROGRESS
**Total Effort:** ~33h (2-3 weeks at 2-3h/day) *(with Claude Code)*

**Recent Completed Work:**
- DEV-200: Refactor Proactivity into LangGraph Nodes (2024-12-29)
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
<h3>DEV-194: Create Step 34a LLM Router Node (Backend)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 2.5h (Actual: ~2h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-28)<br>
LangGraph node wrapper for semantic query classification with 14 tests and 95% coverage.
</summary>


### DEV-194: Create Step 34a LLM Router Node

**Status:** ✅ COMPLETED (2024-12-28)
**Priority:** CRITICAL | **Effort:** 2.5h (Actual: ~2h)

**Problem:**
LangGraph needed a new node for LLM-based semantic routing at Step 34a to replace regex-based routing.

**Solution:**
Created `step_034a__llm_router.py` node that integrates `LLMRouterService` for semantic query classification into routing categories: CHITCHAT, CALCULATOR, THEORETICAL_DEFINITION, TECHNICAL_RESEARCH, GOLDEN_SET.

**Files Created:**
- `app/core/langgraph/nodes/step_034a__llm_router.py` (~100 lines)
- `tests/langgraph/agentic_rag/test_step_034a__llm_router.py` (14 tests)
- `tests/langgraph/agentic_rag/__init__.py`
- `tests/langgraph/agentic_rag/conftest.py`
- `docs/architecture/steps/STEP-34a-RAG.routing.llm.router.semantic.classification.md`

**Files Modified:**
- `app/core/langgraph/nodes/__init__.py` - Added node_step_34a export
- `app/core/langgraph/types.py` - Added routing_decision field to RAGState
- `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd` - Updated S034a with LLM Router

**Components Implemented:**
- `node_step_34a()` async function - Main LangGraph node
- `_decision_to_dict()` - Convert RouterDecision to serializable dict
- `_create_fallback_decision()` - Fallback to TECHNICAL_RESEARCH on error
- Lazy import pattern to avoid database connection during module load

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 14 tests
- ✅ Integrates with LLMRouterService
- ✅ Sets routing_decision in GraphState
- ✅ Fallback to TECHNICAL_RESEARCH on error
- ✅ <100 lines per CLAUDE.md guidelines
- ✅ 95% test coverage
- ✅ Architecture diagram updated with new routing node
- ✅ Step documentation created

**Git:** Branch `DEV-194-Create-Step-34a-LLM-Router-Node`

</details>

---

<details>
<summary>
<h3>DEV-195: Create Step 39 Query Expansion Nodes (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2.5h (Actual: ~2h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-28)<br>
LangGraph nodes for Multi-Query, HyDE, and Parallel Retrieval with 15 tests.
</summary>


### DEV-195: Create Step 39 Query Expansion Nodes

**Status:** ✅ COMPLETED (2024-12-28)
**Priority:** HIGH | **Effort:** 2.5h (Actual: ~2h)

**Problem:**
LangGraph needed nodes for Step 39a (Multi-Query), 39b (HyDE), and 39c (Parallel Retrieval) to implement query expansion pipeline.

**Solution:**
Created three nodes that integrate with corresponding services for enhanced document retrieval with skip logic for non-retrieval routes.

**Files Created:**
- `app/core/langgraph/nodes/step_039a__multi_query.py` (~150 lines)
- `app/core/langgraph/nodes/step_039b__hyde.py` (~135 lines)
- `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` (~180 lines)
- `tests/langgraph/agentic_rag/test_step_039_query_expansion.py` (15 tests)
- `docs/architecture/steps/STEP-39a-RAG.query.multi.query.generator.service.generate.md`
- `docs/architecture/steps/STEP-39b-RAG.query.hyde.generator.service.generate.md`
- `docs/architecture/steps/STEP-39c-RAG.retrieval.parallel.retrieval.service.retrieve.md`

**Files Modified:**
- `app/core/langgraph/nodes/__init__.py` - Added node exports
- `app/core/langgraph/types.py` - Added query_variants, hyde_result, retrieval_result to RAGState
- `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd` - Updated with Step 39 nodes

**Components Implemented:**
- `node_step_39a()` - Multi-Query expansion (BM25, vector, entity variants)
- `node_step_39b()` - HyDE generation (hypothetical documents)
- `node_step_39c()` - Parallel retrieval with RRF fusion
- Skip logic for CHITCHAT/THEORETICAL_DEFINITION/CALCULATOR routes
- Lazy import pattern to avoid database connection during module load

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 15 tests
- ✅ Each node <200 lines
- ✅ Skip logic for non-technical routes
- ✅ Proper state updates (serializable dicts)
- ✅ All tests passing
- ✅ Architecture diagram updated
- ✅ Step documentation created

**Git:** Branch `DEV-195-Create-Step-39-Query-Expansion-Nodes`

</details>

---

<details>
<summary>
<h3>DEV-196: Update Step 64 for Premium Model and Verdetto (Backend)</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 3h (Actual: ~2h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-28)<br>
Integrated VerdettoOperativoParser for TECHNICAL_RESEARCH route with 7 tests.
</summary>


### DEV-196: Update Step 64 for Premium Model and Verdetto

**Status:** ✅ COMPLETED (2024-12-28)
**Priority:** CRITICAL | **Effort:** 3h (Actual: ~2h)

**Problem:**
Step 64 needed to parse Verdetto Operativo from LLM responses for TECHNICAL_RESEARCH queries.

**Solution:**
Added verdetto parsing integration to Step 64 with `_parse_verdetto()` helper function.

**Files Created:**
- `tests/langgraph/agentic_rag/test_step_064_premium_verdetto.py` (7 tests)

**Files Modified:**
- `app/core/langgraph/nodes/step_064__llm_call.py` - Added verdetto parsing
- `app/core/langgraph/types.py` - Added `parsed_synthesis` to RAGState

**Components Implemented:**
- `_parse_verdetto()` - Parses Verdetto Operativo sections
- `parsed_synthesis` state field with structured verdetto data
- Integration with VerdettoOperativoParser service

**Acceptance Criteria (All Met):**
- ✅ Tests written BEFORE implementation (TDD) - 7 tests
- ✅ Parses Verdetto Operativo from TECHNICAL_RESEARCH responses
- ✅ Existing Step 64 tests still pass
- ✅ Backwards compatibility preserved (deanonymization)

**Git:** Branch `DEV-196-Update-Step-64-for-Premium-Model-and-Verdetto`

</details>

---

<details>
<summary>
<h3>DEV-197: Unit Tests for Phase 7 Components (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2h (Actual: ~1h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-28)<br>
Consolidated and verified 261+ unit tests across all Phase 7 components.
</summary>


### DEV-197: Unit Tests for Phase 7 Components

**Status:** ✅ COMPLETED (2024-12-28)
**Priority:** HIGH | **Effort:** 2h (Actual: ~1h)

**Problem:**
All Phase 7 components needed comprehensive unit test coverage verification.

**Solution:**
Created consolidation test suite to verify all Phase 7 tests exist and pass.

**Files Created:**
- `tests/phase7/__init__.py`
- `tests/phase7/test_phase7_consolidation.py` (~240 lines)

**Test Count by Component:**
- DEV-184: LLM Model Config (20 tests)
- DEV-185: PremiumModelSelector (25 tests)
- DEV-186: RouterDecision schema (21 tests)
- DEV-187: LLMRouterService (23 tests)
- DEV-188: MultiQueryGeneratorService (20 tests)
- DEV-189: HyDEGeneratorService (21 tests)
- DEV-190: ParallelRetrievalService (20 tests)
- DEV-191: MetadataExtractor (19 tests)
- DEV-192: SynthesisPromptBuilder (29 tests)
- DEV-193: VerdettoOperativoParser (27 tests)
- DEV-194: Step 34a LLM Router Node (14 tests)
- DEV-195: Step 39 Query Expansion Nodes (15 tests)
- DEV-196: Step 64 Premium Verdetto (7 tests)
- **Total: 261+ tests** (exceeds 145+ requirement)

**Acceptance Criteria (All Met):**
- ✅ 261+ unit tests (target was 145+)
- ✅ All test files exist for Phase 7 services
- ✅ No flaky tests detected
- ✅ Proper mock isolation verified

**Git:** Branch `DEV-197-198-199-Phase7-Testing-Validation`

</details>

---

<details>
<summary>
<h3>DEV-198: Integration Tests for Agentic RAG Flow (Backend)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2.5h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-28)<br>
Created integration tests with mocked LLM for full pipeline verification.
</summary>


### DEV-198: Integration Tests for Agentic RAG Flow

**Status:** ✅ COMPLETED (2024-12-28)
**Priority:** HIGH | **Effort:** 2.5h (Actual: ~1.5h)

**Problem:**
Need to verify the complete Agentic RAG pipeline works end-to-end.

**Solution:**
Created integration tests with mocked LLM to verify full pipeline.

**Files Created:**
- `tests/integration/test_agentic_rag_pipeline.py` (~400 lines)

**Key Test Classes:**
- `TestAgenticRAGPipeline` - Full flow tests (4 tests)
- `TestGoldenSetKBRegression` - Regression tests (4 tests)
- `TestDocumentContextInjection` - Document flow tests (3 tests)
- `TestPipelineErrorHandling` - Error handling tests (3 tests)

**Acceptance Criteria (All Met):**
- ✅ Full pipeline integration tested
- ✅ Golden Set fast-path verified
- ✅ KB hybrid search unchanged
- ✅ Document injection verified
- ✅ All tests pass

**Git:** Branch `DEV-197-198-199-Phase7-Testing-Validation`

</details>

---

<details>
<summary>
<h3>DEV-199: E2E Validation with Real LLM Calls (Backend)</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 2.5h (Actual: ~1.5h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-28)<br>
Created E2E tests and validation script for all AC-ARAG criteria.
</summary>


### DEV-199: E2E Validation with Real LLM Calls

**Status:** ✅ COMPLETED (2024-12-28)
**Priority:** MEDIUM | **Effort:** 2.5h (Actual: ~1.5h)

**Problem:**
Need to validate all AC-ARAG criteria with quality metrics.

**Solution:**
Created E2E test suite and validation script for acceptance criteria verification.

**Files Created:**
- `tests/e2e/test_agentic_rag_quality.py` (~300 lines, 15 tests)
- `scripts/validate_agentic_rag_quality.py` (~180 lines)

**Test Classes:**
- `TestAgenticRAGRouting` - AC-ARAG.1 to AC-ARAG.3 (routing quality)
- `TestAgenticRAGRetrieval` - AC-ARAG.4 to AC-ARAG.6 (retrieval quality)
- `TestAgenticRAGSynthesis` - AC-ARAG.7 to AC-ARAG.9 (synthesis quality)
- `TestAgenticRAGPerformance` - AC-ARAG.10 to AC-ARAG.11 (performance)
- `TestAgenticRAGRegression` - AC-ARAG.12 (no regressions)

**Acceptance Criteria Validated:**
- ✅ AC-ARAG.1: Routing accuracy ≥90%
- ✅ AC-ARAG.2: False negatives <5%
- ✅ AC-ARAG.3: Routing latency ≤200ms P95
- ✅ AC-ARAG.4: Precision@5 improved ≥20%
- ✅ AC-ARAG.5: Recall improved ≥15%
- ✅ AC-ARAG.6: HyDE plausible 95%+
- ✅ AC-ARAG.7: Verdetto in 100% technical responses
- ✅ AC-ARAG.8: Conflicts detected
- ✅ AC-ARAG.9: Fonti index complete
- ✅ AC-ARAG.10: E2E latency ≤5s P95
- ✅ AC-ARAG.11: Cost ≤$0.02/query
- ✅ AC-ARAG.12: No regressions

**Git:** Branch `DEV-197-198-199-Phase7-Testing-Validation`

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

<details>
<summary>
<h3>DEV-200: Refactor Proactivity into LangGraph Nodes</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 12h | <strong>Status:</strong> ✅ DONE (2024-12-29)<br>
Refactor proactivity features from chatbot.py into proper LangGraph nodes (Step 14, Step 100) + route-based prompt injection.
</summary>


### DEV-200: Refactor Proactivity into LangGraph Nodes

**Reference:** PRATIKO_1.5_REFERENCE.md Section 12 (Proactive Suggested Actions)

**Priority:** HIGH | **Effort:** 12h | **Status:** ✅ DONE (2024-12-29)

**Branch:** `DEV-200-Refactor-Proactivity-into-LangGraph-Nodes`

---

### Phase 1: LangGraph Nodes (COMPLETE ✅)

**Original Problem:**
DEV-179 (Integrate LLM-First Proactivity in /chat Endpoint) was incomplete. It added `get_simplified_proactivity_engine()` at line 177 of chatbot.py but never wired it to the 5 code paths that still call `get_proactivity_engine()` (lines 807, 1010, 1386, 1805, 2120). The original `ProactivityEngine` depends on archived services (AtomicFactsExtractor, ParameterMatcher) and raises RuntimeError.

**Solution Implemented:**
Created proper LangGraph nodes following the established pattern:
- ✅ Step 14 (Pre-Response Proactivity) - handles calculable intent parameter collection BEFORE RAG
- ✅ Step 100 (Post-Response Proactivity) - adds suggested actions AFTER LLM response
- ✅ ProactivityGraphService - unified service for graph nodes
- ✅ Graph wiring with conditional edges
- ✅ 28 TDD tests passing

**Files Created:**
- `app/core/langgraph/nodes/step_014__pre_proactivity.py` ✅
- `app/core/langgraph/nodes/step_100__post_proactivity.py` ✅
- `app/services/proactivity_graph_service.py` ✅
- `tests/langgraph/agentic_rag/test_step_014_pre_proactivity.py` ✅
- `tests/langgraph/agentic_rag/test_step_100_post_proactivity.py` ✅

---

### Phase 2: Route-Based Prompt Integration (COMPLETE ✅)

**Gap Found During Manual Testing:**
- Query: "Parlami della rottamazione quinquies"
- Expected: Post-response suggested actions
- Actual: No suggested actions shown

**Root Cause Analysis:**
1. `SUGGESTED_ACTIONS_PROMPT` exists in `app/core/prompts/suggested_actions.md` but is **never injected** into the system prompt
2. `SYNTHESIS_SYSTEM_PROMPT` (DEV-192/193) is only imported for TYPE_CHECKING in step_064 - **not actually used at runtime**
3. The `inject_proactivity_prompt()` function in chatbot.py exists but is never called
4. Prompt building happens in `app/orchestrators/prompting.py` (steps 41, 43, 44) which does NOT use either prompt

**Solution Required:** Route-Based Prompt Selection

The LLM Router (Step 34a) classifies queries into routes. Use this classification to inject appropriate prompts:

| Route | Classification | Prompt to Use |
|-------|---------------|---------------|
| `chitchat` | Casual conversation | Regular prompt (no actions) |
| `theoretical_definition` | Definitions, concepts | Regular + SUGGESTED_ACTIONS_PROMPT |
| **`technical_research`** | Complex fiscal/legal | **SYNTHESIS_SYSTEM_PROMPT + VERDETTO** |
| `calculator` | Calculations | Regular + SUGGESTED_ACTIONS_PROMPT |
| `golden_set` | Specific law references | Golden Set (skip RAG) |

**Acceptance Criteria (All Met):**
- [x] Step 14 node handles pre-response proactivity
- [x] Step 100 node handles post-response actions
- [x] Graph wired with conditional edges
- [x] 28 TDD tests pass
- [x] "Calcola IRPEF" shows input fields question (no LLM call)
- [x] Route-based prompt injection in prompting.py
- [x] All tests pass

**Git:** Branch `DEV-200-Refactor-Proactivity-into-LangGraph-Nodes`

</details>

---

<details>
<summary>
<h3>DEV-201: Suggested Actions Quality & Compliance</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 8.5h | <strong>Status:</strong> ✅ DONE (2024-12-29)<br>
Fix 4 critical issues: action history tracking, domain-aware meta-prompting for contextual actions, KB access affirmation in system.md, forbidden action filtering.
</summary>


### DEV-201: Suggested Actions Quality & Compliance

**Reference:** E2E Testing Results from DEV-200 Completion

**Priority:** HIGH | **Effort:** 8.5h | **Status:** ✅ DONE (2024-12-29)

**Branch:** `DEV-201-Suggested-Actions-Quality`

---

### Problem Statement

E2E testing with "Come funziona il regime forfettario?" revealed 4 critical issues:

1. **No Action Selection in History** - When user clicks action, no trace remains in conversation
2. **Generic/Irrelevant Actions** - Actions too generic ("Calcola", "Verifica") instead of context-specific
3. **CRITICAL: "Non ho accesso a documenti" Lie** - System falsely claims no KB access (reputational damage)
4. **CRITICAL: "Contatta un commercialista" Forbidden** - Violates system.md rules (customers ARE commercialisti)

**Solution:**
Multi-layered fix: (a) Frontend tracks action source in message metadata, (b) Redesign action prompt with **meta-prompting strategy** that teaches HOW to generate contextual actions (not hardcoded WHAT), (c) Add KB access affirmation to base `system.md` prompt (applies to ALL LLM calls), (d) Add regex-based validation layer to filter forbidden action patterns.

**Subtasks Completed:**
- ✅ DEV-201a: Action Source Tracking (Frontend)
- ✅ DEV-201b: Meta-Prompting for Action Generation (Backend)
- ✅ DEV-201c: KB Access Affirmation in Base Prompt (Backend)
- ✅ DEV-201d: Forbidden Action Validation Layer (Backend)

**Acceptance Criteria (All Met):**
- [x] "Come funziona il regime forfettario?" produces SPECIFIC actions (not generic)
- [x] LLM never says "non ho accesso a documenti"
- [x] "Contatta un commercialista" never appears in suggestions
- [x] Action source visible in frontend conversation
- [x] All baseline tests pass
- [x] 90%+ test coverage on new code

**Git:** Branch `DEV-201-Suggested-Actions-Quality`

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

## Phase 8: Bugfix - ✅ COMPLETED

**Status:** All tasks completed (2024-12-29)

**Tasks:** DEV-200, DEV-201 → Moved to [Completed Tasks](#completed-tasks) section above.

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
| Phase 8: Bugfix | DEV-200, DEV-201 | 16.5h | @ezio, @livia, @clelia |
| **Total** | **52+ tasks** | **~105h+** | |

**Estimated Timeline:** 5-6 weeks at 3h/day *(with Claude Code)*

---

## Phase 9: LLM Excellence - ~131h (10-12 weeks)

**Reference:** Technical Intent Document: PratikoAI LLM Excellence Architecture v2.0 (2024-12-30)
**Status:** NOT STARTED
**Total Effort:** ~131h (10-12 weeks at 2-3h/day)
**Priority:** HIGH - Core reasoning capability upgrade

### Overview

Phase 9 elevates PratikoAI's LLM reasoning capabilities through:

1. **Context Preservation** - Fix KB document loss between Step 40 and Step 100
2. **Explicit Reasoning** - Chain of Thought (CoT) and Tree of Thoughts (ToT)
3. **Cost Optimization** - Multi-LLM routing based on query complexity
4. **Source Hierarchy** - Italian legal source weighting (Legge > Circolare > Interpello)
5. **Action Quality** - Golden Loop regeneration for action validation

**Target Metrics:**
| Metric | Current | Target |
|--------|---------|--------|
| Answer accuracy | 91% | 95%+ |
| Action relevance | ~60% | 90%+ |
| Cost per query | €0.0155 | €0.0052 |
| Response time (simple) | ~3s | <2s |
| Response time (complex) | ~5s | <5s |

### Task ID Mapping

| Task Range | Sub-Phase |
|------------|-----------|
| DEV-210 to DEV-214 | Phase 9.1: Foundation (GraphState, PromptLoader, KB Preservation) |
| DEV-215 to DEV-219 | Phase 9.2: Golden Loop (ActionValidator, ActionRegenerator) |
| DEV-220 to DEV-226 | Phase 9.3: Intelligence (Complexity, LLMOrchestrator, ToT) |
| DEV-227 to DEV-232 | Phase 9.4: Excellence (Source Hierarchy, Risk Analysis, Dual Reasoning) |
| DEV-233 to DEV-237 | Phase 9.5: Conversation (HyDE, Ambiguity, Paragraph Grounding) |
| DEV-238 to DEV-241 | Phase 9.6: Quality & Monitoring |
| DEV-242 | Phase 9.7: Frontend UI (Reasoning Display) |

### Files for Refactoring or Deletion

Based on analysis, these files may need refactoring or deletion as the new architecture replaces their functionality:

| File | Action | Reason |
|------|--------|--------|
| `app/services/synthesis_prompt_builder.py` | REFACTOR | Merge into PromptLoader, simplify to use new unified templates |
| `app/core/prompts/suggested_actions.md` | KEEP | Enhanced in PR #900 with domain/confidence templating and STEP 1-4 methodology |
| `app/services/premium_model_selector.py` | REFACTOR | LLMOrchestrator will absorb model selection logic |
| `app/orchestrators/prompting.py` | REFACTOR | PromptLoader centralizes prompt management |
| `app/services/domain_prompt_templates.py` | EVALUATE | May be superseded by new ToT domain prompts |
| `app/services/advanced_prompt_engineer.py` | EVALUATE | Review for redundancy with new reasoning prompts |

### Dependency Graph

```
DEV-210 (GraphState) ─────────────────────────────────────────┐
    │                                                         │
    ├──► DEV-211 (PromptLoader)                              │
    │        │                                                │
    │        ├──► DEV-212 (unified_response_simple.md)       │
    │        ├──► DEV-220 (complexity_classifier.md)         │
    │        ├──► DEV-223 (tree_of_thoughts.md)              │
    │        └──► DEV-233 (hyde_conversational.md)           │
    │                                                         │
    ├──► DEV-213 (Step 40 KB Preservation) ◄─────────────────┤
    │        │                                                │
    │        └──► DEV-214 (Step 64 Unified Output)           │
    │                 │                                       │
    │                 ├──► DEV-215 (ActionValidator)         │
    │                 │        │                              │
    │                 │        └──► DEV-217 (ActionRegenerator)
    │                 │                 │                     │
    │                 │                 └──► DEV-218 (Step 100 Update)
    │                 │                                       │
    │                 └──► DEV-229 (DualReasoning)           │
    │                          │                              │
    │                          └──► DEV-230 (ReasoningTransformer)
    │                                                         │
    ├──► DEV-220 (Complexity Classifier)                     │
    │        │                                                │
    │        └──► DEV-221 (LLMOrchestrator) ◄────────────────┤
    │                 │                                       │
    │                 └──► DEV-222 (Step 64 Routing)         │
    │                                                         │
    └──► DEV-227 (Source Hierarchy) ─────────────────────────┤
             │                                                │
             └──► DEV-228 (SourceConflictDetector)           │
                      │                                       │
                      └──► DEV-231 (Risk Analysis ToT)       │
```


---

<details>
<summary>
<h3>DEV-210: Update GraphState with LLM Excellence Fields</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 4h (Actual: ~2h) | <strong>Status:</strong> ✅ COMPLETED (2024-12-31)<br>
Added 13 new Optional fields to RAGState for LLM Excellence: kb_documents, kb_sources_metadata, query_complexity, complexity_classification, reasoning_type, reasoning_trace, tot_analysis, internal_reasoning, public_reasoning, action_validation_result, action_regeneration_count, actions_source, actions_validation_log.
</summary>


### DEV-210: Update GraphState with LLM Excellence Fields

**Reference:** [Technical Intent Part 3.1](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Graph State Schema)

**Priority:** CRITICAL | **Effort:** 4h (Actual: ~2h) | **Status:** ✅ COMPLETED (2024-12-31)

**Problem:**
RAGState lacks fields for reasoning traces, KB document preservation, complexity classification, ToT analysis, and action validation state needed for LLM Excellence features.

**Solution:**
Add new Optional fields to RAGState TypedDict with proper typing and None defaults to maintain backward compatibility with existing 70+ nodes.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-211, DEV-213, DEV-214, DEV-215, DEV-220, DEV-227, DEV-229

**Change Classification:** RESTRUCTURING

**Impact Analysis:**
- **Primary File:** `app/core/langgraph/types.py`
- **Affected Files:**
  - All 70+ nodes in `app/core/langgraph/nodes/`
  - `app/schemas/graph.py`
- **Related Tests:**
  - `tests/core/langgraph_tests/` (all)
  - `tests/unit/core/langgraph/nodes/`
- **Baseline Command:** `pytest tests/core/langgraph_tests/ -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass (run `pytest tests/core/langgraph_tests/ -v`)
- [ ] Existing RAGState documentation reviewed
- [ ] No pre-existing test failures in langgraph tests

**File:** `app/core/langgraph/types.py`

**Fields to Add:**
```python
# Phase 9: LLM Excellence - KB Preservation
kb_documents: list[dict] | None  # Preserved KB docs from Step 40
kb_sources_metadata: list[dict] | None  # Source metadata for grounding
# Structure: [{id, title, type, date, url, key_topics, key_values, hierarchy_weight}]

# Phase 9: LLM Excellence - Complexity & Routing
query_complexity: str | None  # "simple" | "complex" | "multi_domain"
complexity_classification: dict | None  # Full classification result
# Structure: {complexity, domains, confidence, reasoning}

# Phase 9: LLM Excellence - Reasoning
reasoning_type: str | None  # "cot" | "tot" | "tot_multi_domain"
reasoning_trace: dict | None  # Internal reasoning log (CoT steps or ToT summary)
# CoT: {tema, fonti_utilizzate, elementi_chiave, conclusione}
# ToT: {hypotheses, selected, selection_reasoning, confidence}
tot_analysis: dict | None  # Full Tree of Thoughts analysis
# Structure: {hypotheses[], selected, selection_reasoning, confidence, alternative_note}

# Phase 9: LLM Excellence - Dual Reasoning
internal_reasoning: dict | None  # Technical reasoning for debugging
public_reasoning: dict | None  # User-friendly explanation
# Structure: {summary, selected_scenario, why_selected, main_sources, confidence_label}

# Phase 9: LLM Excellence - Action Validation
action_validation_result: dict | None  # ActionValidator output
action_regeneration_count: int | None  # Golden Loop iteration count (max 2)
actions_source: str | None  # "unified_llm" | "fallback" | "template" | "regenerated"
actions_validation_log: list[str] | None  # Rejection reasons for debugging
```

**Edge Cases:**
- **Nulls/Empty:** All new fields must default to None to avoid breaking existing nodes
- **Backward Compatibility:** Existing checkpoint deserialization must work with new schema
- **Type Mismatches:** Fields must be properly typed to pass mypy strict mode
- **Serialization:** All dict structures must be JSON-serializable for checkpointing

**Testing Requirements:**
- **TDD:** Write `tests/unit/core/langgraph/test_types_phase9.py` FIRST
- **Unit Tests:**
  - `test_ragstate_new_fields_optional` - All new fields are Optional with None default
  - `test_ragstate_backward_compatible` - Existing state dicts work without new fields
  - `test_ragstate_serialization` - JSON serialization works for all field types
  - `test_ragstate_checkpoint_migration` - Checkpoints with old schema deserialize correctly
  - `test_ragstate_kb_documents_structure` - kb_documents field structure validates
  - `test_ragstate_reasoning_trace_structure` - reasoning_trace CoT/ToT structures validate
- **Edge Case Tests:**
  - `test_ragstate_none_values_all_fields` - All fields can be None
  - `test_ragstate_partial_update` - Partial field updates don't break state
  - `test_ragstate_mypy_compliance` - No type errors with mypy strict
- **Regression Tests:** Run full `pytest tests/core/langgraph_tests/`
- **Coverage Target:** 95%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing nodes | CRITICAL | All fields Optional with None default, run full regression suite |
| Checkpoint deserialization fails | HIGH | Test with existing checkpoint data before merge |
| Type mismatches in nodes | HIGH | Run mypy after changes, fix all errors |
| Memory increase from new fields | LOW | Fields are None until populated, minimal overhead |

**Code Structure:**
- Max function: 50 lines, extract helpers if larger
- Max class: 200 lines, split into focused services
- Max file: 400 lines, create submodules

**Code Completeness:**
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values
- [ ] All fields properly typed with TypedDict
- [ ] All structures documented with inline comments

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] All new fields are Optional with None default
- [x] mypy passes with no errors
- [x] All existing langgraph tests pass (regression)
- [x] Checkpoint with old schema deserializes correctly
- [x] 95%+ test coverage for new code
- [x] No breaking changes to existing node behavior

---

</details>

<details>
<summary>
<h3>DEV-211: Create PromptLoader Utility Service</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 3h | <strong>Status:</strong> ✅ COMPLETED (2024-12-31)<br>
Prompts are currently scattered across multiple files with inline loading. Need centralized prompt l...
</summary>


### DEV-211: Create PromptLoader Utility Service

**Reference:** [Technical Intent Part 3.2.2](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Prompt Loader Specification)

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Prompts are currently scattered across multiple files with inline loading. Need centralized prompt loading with caching, variable substitution, and hot-reload capability for development.

**Solution:**
Create PromptLoader service that loads .md files from `app/prompts/` directory with LRU caching and template variable substitution.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** None
- **Unlocks:** DEV-212, DEV-216, DEV-220, DEV-223, DEV-224, DEV-233, DEV-234

**Change Classification:** ADDITIVE

**File:** `app/services/prompt_loader.py`

**Directory Structure to Create:**
```
app/prompts/
├── __init__.py                          # Prompt loader utility
├── config.yaml                          # Version and A/B test config
│
├── v1/                                  # Version 1 prompts
│   ├── unified_response_simple.md       # Simple CoT prompt
│   ├── tree_of_thoughts.md              # Complex ToT prompt
│   ├── tree_of_thoughts_multi_domain.md # Multi-domain ToT prompt
│   ├── hyde_conversational.md           # HyDE with conversation context
│   ├── complexity_classifier.md         # Query complexity classification
│   └── action_regeneration.md           # Golden Loop regeneration
│
└── components/                          # Reusable prompt components
    ├── forbidden_actions.md             # Actions to never suggest
    ├── source_citation_rules.md         # How to cite sources
    ├── italian_formatting.md            # Italian language rules
    └── verdetto_format.md               # VERDETTO structure template
```

**Methods:**
```python
class PromptLoader:
    def __init__(self, prompts_dir: Path = None, version: str = "v1"):
        """Initialize with prompts directory and version."""

    @lru_cache(maxsize=50)
    def load(self, name: str, **variables) -> str:
        """Load prompt by name with variable substitution.

        Args:
            name: Prompt name (e.g., "unified_response_simple")
            **variables: Template variables to substitute ({var} syntax)

        Returns:
            Formatted prompt string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            KeyError: If required variable is missing
        """

    def load_component(self, name: str) -> str:
        """Load a reusable prompt component from components/ directory."""

    def compose(self, *parts: str, separator: str = "\n\n---\n\n") -> str:
        """Compose multiple prompt parts with separators."""

    def reload(self, name: str = None) -> None:
        """Clear cache and reload (single prompt or all)."""

    def list_prompts(self) -> list[str]:
        """List available prompt names."""

    def get_version(self) -> str:
        """Get current active prompt version from config."""
```

**Error Handling:**
- File not found: Raise `FileNotFoundError` with list of available prompts
- Missing variable: Raise `KeyError` with variable name and prompt name
- Invalid YAML config: Log warning, use default version "v1"
- **Logging:** All errors MUST be logged with context (prompt_name, version, variables)

**Performance Requirements:**
- Cold load: <100ms for any prompt
- Cached load: <1ms (memory cache)
- Cache TTL: 1 hour (configurable)

**Edge Cases:**
- **Empty Prompt File:** Return empty string, log warning
- **Missing Variables:** Raise KeyError with clear message
- **Unicode Issues:** Handle UTF-8 encoding for Italian characters
- **Hot Reload:** Clear cache on reload() call
- **Version Not Found:** Fall back to "v1" with warning

**Testing Requirements:**
- **TDD:** Write `tests/unit/services/test_prompt_loader.py` FIRST
- **Unit Tests:**
  - `test_load_existing_prompt` - Loads .md file content
  - `test_load_with_variables` - Variable substitution works
  - `test_load_cached_returns_same` - Cache hit returns same object
  - `test_reload_clears_cache` - Reload forces fresh load
  - `test_list_prompts_returns_all` - Lists all .md files
  - `test_load_component` - Component loading works
  - `test_compose_multiple_parts` - Composition works
- **Edge Case Tests:**
  - `test_load_missing_prompt_raises` - FileNotFoundError for missing
  - `test_load_empty_prompt` - Handles empty files with warning
  - `test_load_with_missing_variable` - Raises KeyError
  - `test_load_with_unicode` - Italian characters handled
- **Integration Tests:** `tests/integration/services/test_prompt_loader_integration.py`
- **Coverage Target:** 95%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| File not found errors | MEDIUM | Clear error messages with available prompts list |
| Cache staleness | LOW | 1h TTL, manual reload() method for development |
| Memory usage | LOW | LRU cache with maxsize=50 |

**Code Completeness:**
- [ ] No TODO comments for required functionality
- [ ] All error paths tested
- [ ] Logging implemented for all errors

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Loads all prompt files from app/prompts/
- [x] Variable substitution works ({variable} syntax)
- [x] LRU cache with 1h TTL
- [x] Component composition works
- [x] 95%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-212: Create unified_response_simple.md Prompt Template</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 3h | <strong>Status:</strong> ✅ COMPLETED (2024-12-31)<br>
Current response prompts are scattered across multiple files with inconsistent formatting. Need unif...
</summary>


### DEV-212: Create unified_response_simple.md Prompt Template

**Reference:** [Technical Intent Part 3.2.3](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Unified Response Prompt)

**Priority:** CRITICAL | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Current response prompts are scattered across multiple files with inconsistent formatting. Need unified prompt with JSON schema for structured output including answer, reasoning, sources, and actions in a single LLM call.

**Solution:**
Create unified_response_simple.md with Italian professional formatting, JSON output schema, Chain of Thought structure, and clear instructions for source citation and action generation.

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-211 (PromptLoader)
- **Unlocks:** DEV-214 (Step 64 integration)

**Change Classification:** ADDITIVE

**File:** `app/prompts/v1/unified_response_simple.md`

**Template Structure:**
```markdown
# PratikoAI - Risposta Unificata (Simple CoT)

## Ruolo
Sei PratikoAI, assistente esperto in normativa fiscale, del lavoro e legale italiana.

## Contesto Fornito
{kb_context}

## Metadati Fonti Disponibili
{kb_sources_metadata}

## Domanda Utente
{query}

## Contesto Conversazione (se presente)
{conversation_context}

## Data Corrente
{current_date}

## Istruzioni di Ragionamento (Chain of Thought)

Prima di rispondere, esegui questi passaggi mentali:

1. **TEMA**: Identifica l'argomento principale della domanda
2. **FONTI**: Individua le fonti rilevanti nel contesto fornito
3. **ELEMENTI CHIAVE**: Estrai i punti essenziali per la risposta
4. **CONCLUSIONE**: Formula la risposta basandoti sulle fonti

## Formato Output (JSON OBBLIGATORIO)

Rispondi SEMPRE con questo schema JSON:

```json
{
  "reasoning": {
    "tema_identificato": "string - argomento principale",
    "fonti_utilizzate": ["string - riferimento fonte 1", "..."],
    "elementi_chiave": ["string - punto 1", "..."],
    "conclusione": "string - sintesi del ragionamento"
  },
  "answer": "string - risposta completa in italiano professionale",
  "sources_cited": [
    {
      "ref": "string - es: Art. 16 DPR 633/72",
      "relevance": "principale|supporto",
      "url": "string|null"
    }
  ],
  "suggested_actions": [
    {
      "id": "string - univoco",
      "label": "string - 8-40 caratteri",
      "icon": "calculator|search|calendar|file-text|alert-triangle|check-circle|edit|refresh-cw|book-open|bar-chart",
      "prompt": "string - almeno 25 caratteri, autosufficiente",
      "source_basis": "string - quale fonte KB ha ispirato questa azione"
    }
  ]
}
```

## Regole per Azioni Suggerite

1. **BASATE SU FONTI**: Ogni azione DEVE riferirsi a una fonte nel contesto
2. **SPECIFICHE**: Label 8-40 caratteri, prompt >25 caratteri
3. **VIETATE**: Mai suggerire "consulta un professionista", "verifica sul sito"
4. **NUMERO**: Genera 2-4 azioni rilevanti, non di più
5. **ICON**: Usa icone appropriate al tipo di azione

## Regole Citazioni

- Cita SEMPRE la fonte più autorevole (Legge > Decreto > Circolare)
- Usa formato italiano: Art. X, comma Y, D.Lgs. Z/AAAA
- Se non trovi fonti nel contesto, rispondi con la tua conoscenza ma indica "Nota: questa informazione potrebbe richiedere verifica"
```

**Template Variables:**
- `{kb_context}` - Formatted knowledge base documents from Step 40
- `{kb_sources_metadata}` - JSON array of source metadata for action grounding
- `{query}` - User question
- `{conversation_context}` - Last 3 conversation turns (optional)
- `{current_date}` - Current date for temporal context

**Testing Requirements:**
- **TDD:** Write `tests/unit/prompts/test_unified_response_simple.py` FIRST
- **Unit Tests:**
  - `test_prompt_loads_via_loader` - PromptLoader can load it
  - `test_prompt_contains_json_schema` - Has valid JSON example
  - `test_prompt_variables_substitute` - All variables work
  - `test_prompt_reasoning_structure` - CoT structure present
  - `test_prompt_action_rules_present` - Action rules documented
- **Integration Tests:** Test with actual LLM call, validate JSON output parseable
- **Coverage Target:** 90%+

**Routing Logic (Step 64 Integration):**
Step 64 must select the appropriate prompt based on query complexity:

```python
# Routing decision in Step 64
def _select_prompt_template(state: RAGState) -> str:
    """Select prompt template based on query complexity.

    Returns:
        Prompt template path for PromptLoader
    """
    complexity = state.get("query_complexity", "SIMPLE")

    if complexity in ("SIMPLE", "MODERATE"):
        # Use unified response for simple/moderate queries
        return "v1/unified_response_simple.md"
    elif complexity == "COMPLEX":
        # Use synthesis_critical for multi-domain complex queries
        return "v1/synthesis_critical.md"
    elif complexity == "CRITICAL":
        # Use synthesis_critical with additional legal rigor
        return "v1/synthesis_critical.md"
    else:
        # Default to simple
        return "v1/unified_response_simple.md"
```

**Route Conditions:**
| Complexity | Prompt Template | Model | Use Case |
|------------|-----------------|-------|----------|
| SIMPLE | unified_response_simple.md | GPT-4o-mini | Single-domain, direct questions |
| MODERATE | unified_response_simple.md | GPT-4o-mini | Single-domain with some nuance |
| COMPLEX | synthesis_critical.md | GPT-4o | Multi-domain, conflicting sources |
| CRITICAL | synthesis_critical.md | GPT-4o | Legal risk, regulatory compliance |

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Prompt loads without errors via PromptLoader
- [x] Contains valid JSON schema example
- [x] All template variables documented and work
- [x] Produces parseable JSON from LLM (integration test)
- [x] Follows Italian professional language guidelines
- [x] Action rules clearly specified
- [x] Routing logic documented and integrated with DEV-214

---

</details>

<details>
<summary>
<h3>DEV-213: Update Step 40 to Preserve KB Documents and Metadata</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 4h | <strong>Status:</strong> ✅ COMPLETED (2024-12-31)<br>
Step 40 currently merges KB documents into a context string but doesn't preserve the original docume...
</summary>


### DEV-213: Update Step 40 to Preserve KB Documents and Metadata

**Reference:** [Technical Intent Part 3.5.2](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Step 40: Build Context Enhanced)

**Priority:** CRITICAL | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Step 40 currently merges KB documents into a context string but doesn't preserve the original documents or their metadata. This causes "context fragmentation" - Step 100 cannot access KB sources for action generation, resulting in generic, disconnected action suggestions.

**Solution:**
Update Step 40 to store `kb_documents` (raw documents) and `kb_sources_metadata` (structured metadata for action grounding) in state alongside the merged context string.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-210 (GraphState fields)
- **Unlocks:** DEV-214, DEV-218, DEV-228, DEV-236

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/core/langgraph/nodes/step_040__build_context.py`
- **Affected Files:**
  - `app/orchestrators/facts.py` (step_40__build_context function)
- **Related Tests:**
  - `tests/integration/orchestrators/test_step_39_40_integration.py`
- **Baseline Command:** `pytest tests/integration/orchestrators/test_step_39_40_integration.py -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Existing Step 40 code reviewed (97 lines)
- [ ] Understand current context merging logic

**File:** `app/core/langgraph/nodes/step_040__build_context.py`

**Changes Required:**
```python
# After line 30 (merged_context = res.get("merged_context", ""))
# Add KB document preservation:

# ✅ NEW: Store raw KB documents for downstream use
kb_documents = res.get("kb_documents", [])
state["kb_documents"] = kb_documents

# ✅ NEW: Store metadata for action grounding
kb_sources_metadata = []
for doc in kb_documents:
    kb_sources_metadata.append({
        "id": doc.get("id"),
        "title": doc.get("title", ""),
        "type": doc.get("type", ""),  # legge, decreto, circolare, etc.
        "date": doc.get("date", ""),
        "url": doc.get("url"),
        "key_topics": extract_topics(doc),  # New helper function
        "key_values": extract_values(doc),  # Numbers, dates, rates
        "hierarchy_weight": get_hierarchy_weight(doc.get("type", ""))
    })
state["kb_sources_metadata"] = kb_sources_metadata
```

**Helper Functions to Add:**
```python
def extract_topics(doc: dict) -> list[str]:
    """Extract key topics from document for action relevance."""
    # Extract from title, content keywords

def extract_values(doc: dict) -> list[str]:
    """Extract specific values (percentages, dates, amounts) for action prompts."""
    # Regex patterns for: percentages, euro amounts, dates, article numbers

def get_hierarchy_weight(doc_type: str) -> float:
    """Return Italian legal hierarchy weight for source prioritization."""
    HIERARCHY = {
        "legge": 1.0, "decreto_legislativo": 1.0, "dpr": 1.0,
        "decreto_ministeriale": 0.8, "regolamento_ue": 0.8,
        "circolare": 0.6, "risoluzione": 0.6,
        "interpello": 0.4, "faq": 0.4,
        "cassazione": 0.9, "corte_costituzionale": 1.0
    }
    return HIERARCHY.get(doc_type.lower(), 0.5)
```

**Error Handling:**
- Missing kb_documents: Set empty list, log warning
- Malformed document: Skip document, log warning, continue processing
- **Logging:** All warnings MUST be logged with context (request_id, doc_count)

**Performance Requirements:**
- Metadata extraction: <50ms for 10 documents
- No increase in context string generation time

**Edge Cases:**
- **Empty KB Results:** Set kb_documents=[], kb_sources_metadata=[], continue
- **Missing Document Fields:** Use defaults ("" for strings, None for optional)
- **Large Document Set (50+):** Cap at top-20 by relevance, log truncation
- **Duplicate Documents:** Deduplicate by document ID
- **Missing Date Field:** Use "data non disponibile" in metadata

**Testing Requirements:**
- **TDD:** Write `tests/unit/core/langgraph/nodes/test_step_040_kb_preservation.py` FIRST
- **Unit Tests:**
  - `test_step40_preserves_kb_documents` - kb_documents stored in state
  - `test_step40_preserves_kb_metadata` - kb_sources_metadata stored
  - `test_step40_metadata_structure` - Correct structure for each doc
  - `test_step40_hierarchy_weight` - Correct weights for doc types
  - `test_step40_extract_topics` - Topics extracted correctly
  - `test_step40_extract_values` - Values (%, €, dates) extracted
- **Edge Case Tests:**
  - `test_step40_empty_kb_docs` - Handles empty KB gracefully
  - `test_step40_null_kb_docs` - None handling
  - `test_step40_large_kb_docs_capped` - Cap at 20 docs
  - `test_step40_malformed_doc_skipped` - Bad docs skipped with warning
  - `test_step40_missing_fields_defaults` - Missing fields get defaults
- **Regression Tests:** Run `pytest tests/integration/orchestrators/test_step_39_40_integration.py`
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing context flow | HIGH | Keep merged context unchanged, only ADD new fields |
| Context size explosion | MEDIUM | Cap kb_documents to top-20 |
| Performance degradation | MEDIUM | Async metadata extraction, <50ms target |

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] kb_documents preserved in state with full document content
- [x] kb_sources_metadata preserved with structured metadata
- [x] Hierarchy weights assigned correctly
- [x] Topics and values extracted for action grounding
- [x] Existing context behavior unchanged
- [x] All existing Step 40 tests pass (regression)
- [x] 90%+ test coverage for new code

---

</details>

<details>
<summary>
<h3>DEV-214: Update Step 64 for Unified JSON Output with Reasoning</h3>
<strong>Priority:</strong> CRITICAL | <strong>Effort:</strong> 6h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
Step 64 currently uses Verdetto parsing for TECHNICAL_RESEARCH and separate action generation. Need ...
</summary>


### DEV-214: Update Step 64 for Unified JSON Output with Reasoning

**Reference:** [Technical Intent Part 3.5.3](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Step 64: LLM Call Unified)

**Priority:** CRITICAL | **Effort:** 6h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
Step 64 currently uses Verdetto parsing for TECHNICAL_RESEARCH and separate action generation. Need unified JSON output that includes reasoning traces, answer, sources, and actions in a single structured response.

**Solution:**
Update Step 64 to use unified_response_simple.md prompt for simple queries, parse JSON output, store reasoning trace in state, and fallback gracefully to text extraction if JSON parsing fails.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-210 (GraphState), DEV-212 (unified prompt)
- **Unlocks:** DEV-215 (ActionValidator), DEV-218 (Step 100), DEV-229 (DualReasoning)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/core/langgraph/nodes/step_064__llm_call.py`
- **Affected Files:**
  - `app/orchestrators/providers.py` (step_64__llmcall)
  - `app/services/verdetto_parser.py`
  - `app/services/synthesis_prompt_builder.py`
- **Related Tests:**
  - `tests/core/langgraph_tests/nodes/test_step_064_deanonymization.py`
  - `tests/langgraph/agentic_rag/test_step_064_premium_verdetto.py`
- **Baseline Command:** `pytest tests/core/langgraph_tests/nodes/test_step_064* -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Step 64 code fully reviewed (287 lines)
- [ ] Verdetto parsing logic understood
- [ ] Deanonymization flow documented

**File:** `app/core/langgraph/nodes/step_064__llm_call.py`

**New Functions to Add:**
```python
def _parse_unified_response(content: str) -> dict | None:
    """Parse unified JSON response from LLM.

    Args:
        content: LLM response content

    Returns:
        Parsed dict with reasoning, answer, sources, actions
        None if parsing fails
    """
    # Try JSON extraction from markdown code block first
    # Then try raw JSON parsing
    # Log parsing failures with content sample

def _extract_json_from_content(content: str) -> dict | None:
    """Extract JSON from response that may contain markdown code blocks."""
    # Match ```json ... ``` blocks
    # Match raw JSON objects
    # Return None if no valid JSON found

def _fallback_to_text(content: str, state: RAGState) -> dict:
    """Fallback parsing when JSON extraction fails.

    Returns minimal valid response with answer only.
    """
    return {
        "reasoning": None,
        "answer": content,  # Use full content as answer
        "sources_cited": [],
        "suggested_actions": []
    }
```

**Logic Changes:**
```python
# After successful LLM call, before storing response:

# Try unified JSON parsing (replaces legacy Verdetto/XML parsing)
parsed = _parse_unified_response(content)

if parsed:
    # Store reasoning trace
    state["reasoning_type"] = "cot"
    state["reasoning_trace"] = parsed.get("reasoning")

    # Store suggested actions for Step 100 validation
    state["suggested_actions"] = parsed.get("suggested_actions", [])
    state["actions_source"] = "unified_llm"

    # Store and validate sources with hierarchy
    sources = parsed.get("sources_cited", [])
    state["sources_cited"] = _apply_source_hierarchy(sources)

    # Use answer for display
    content = parsed.get("answer", content)
else:
    # Fallback: mark for action regeneration
    state["actions_source"] = "fallback_needed"
    logger.warning("step64_json_parse_failed", request_id=state.get("request_id"))
```

**Source Hierarchy Validation:**
```python
# Italian legal source hierarchy (highest to lowest authority)
SOURCE_HIERARCHY = {
    "legge": 1,           # Legge (Law)
    "decreto": 2,         # Decreto Legislativo / DPR
    "circolare": 3,       # Circolare AdE
    "interpello": 4,      # Interpello / Risposta
    "prassi": 5,          # Other prassi
    "unknown": 99
}

def _apply_source_hierarchy(sources: list[dict]) -> list[dict]:
    """Sort sources by legal hierarchy and flag conflicts.

    Args:
        sources: List of source dicts from LLM response

    Returns:
        Sorted sources with hierarchy_rank added, highest authority first
    """
    for source in sources:
        ref = source.get("ref", "").lower()
        # Determine hierarchy rank
        if "legge" in ref or "l." in ref:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["legge"]
        elif "decreto" in ref or "d.lgs" in ref or "dpr" in ref:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["decreto"]
        elif "circolare" in ref:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["circolare"]
        elif "interpello" in ref or "risposta" in ref:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["interpello"]
        else:
            source["hierarchy_rank"] = SOURCE_HIERARCHY["unknown"]

    # Sort by hierarchy rank (lowest number = highest authority)
    return sorted(sources, key=lambda s: s.get("hierarchy_rank", 99))

def _detect_source_conflicts(sources: list[dict]) -> list[dict]:
    """Detect conflicting sources on the same topic with different conclusions.

    Returns list of conflict dicts with source_a, source_b, reason.
    """
    # Group by topic, compare conclusions
    # Flag temporal conflicts (newer supersedes older)
    # Flag hierarchy conflicts (higher authority supersedes lower)
    pass  # Implementation in DEV-228
```

**Legacy Parser Deprecation (Part of this task):**
After unified parsing is implemented and tested, follow the **DEV-178 archiving pattern** to preserve git history:

1. Create `archived/phase9_legacy_parsers/` directory
2. Archive (move, don't delete) the following files:
   - `archived/phase9_legacy_parsers/verdetto_parser.py` ← from `app/services/verdetto_parser.py`
   - `archived/phase9_legacy_parsers/synthesis_prompt_builder.py` ← from `app/services/synthesis_prompt_builder.py`
   - `archived/phase9_legacy_parsers/tests/` ← related test files
3. Remove `_parse_verdetto()` function and all VERDETTO XML tag parsing from Step 64
4. Remove `_extract_actions_from_xml()` function
5. Update imports to use archived path with try/except fallback (if needed for backwards compatibility)
6. Update or archive related tests

**Archiving Pattern Reference (from DEV-178):**
```python
# Pattern for import fallback if needed temporarily
try:
    from app.services.verdetto_parser import parse_verdetto
except ImportError:
    from archived.phase9_legacy_parsers.verdetto_parser import parse_verdetto
    import warnings
    warnings.warn("Using archived verdetto_parser - remove this import", DeprecationWarning)
```

**Error Handling:**
- JSON parse failure: Log with content sample, fallback to text extraction
- Missing required fields in JSON: Use defaults, log warning
- Empty response: Log error, return failure state
- **Logging:** All errors MUST be logged with context (request_id, model_used, content_length)

**Performance Requirements:**
- JSON parsing: <10ms
- Total Step 64: <2s (same as current)
- No latency regression

**Edge Cases:**
- **JSON Parse Failure:** LLM returns non-JSON -> fallback to text extraction
- **Partial JSON:** LLM returns truncated JSON -> log, use available fields
- **Empty Response:** LLM returns empty -> log error, return failure state
- **Mixed Format:** LLM returns JSON + extra text -> extract JSON block only
- **Markdown Code Block:** JSON in \`\`\`json block -> extract correctly
- **Missing Fields:** Some fields missing in JSON -> use defaults

**Testing Requirements:**
- **TDD:** Write `tests/unit/core/langgraph/nodes/test_step_064_unified_output.py` FIRST
- **Unit Tests:**
  - `test_step64_parses_json_response` - Valid JSON parsed correctly
  - `test_step64_extracts_from_markdown_block` - JSON in code block extracted
  - `test_step64_extracts_answer` - answer field extracted
  - `test_step64_extracts_actions` - suggested_actions extracted
  - `test_step64_stores_reasoning_trace` - reasoning_trace in state
  - `test_step64_stores_sources_cited` - sources_cited in state
  - `test_step64_sets_actions_source` - actions_source set correctly
- **Edge Case Tests:**
  - `test_step64_fallback_to_text` - Non-JSON handled gracefully
  - `test_step64_partial_json` - Truncated JSON handled
  - `test_step64_empty_response` - Empty response handled
  - `test_step64_missing_fields_defaults` - Missing fields get defaults
- **Source Hierarchy Tests:**
  - `test_step64_source_hierarchy_ordering` - Sources sorted by authority
  - `test_step64_legge_ranked_highest` - Legge sources ranked first
  - `test_step64_hierarchy_rank_added` - hierarchy_rank field added to sources
- **Regression Tests:** `pytest tests/core/langgraph_tests/nodes/test_step_064* -v`
- **Integration Tests:** Full pipeline test with unified prompt
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM doesn't produce JSON | CRITICAL | Robust fallback parsing, mark for regeneration |
| Legacy parser removal breaks tests | HIGH | Update tests before removing legacy code |
| Latency increase | MEDIUM | Async JSON parsing target <10ms |
| Breaking deanonymization | HIGH | Test deanonymization flow with new parsing |
| Source hierarchy incorrect | MEDIUM | Comprehensive tests for Italian legal hierarchy |

**Code Completeness:**
- [ ] No TODO comments for required functionality
- [ ] All JSON fields handled (not just happy path)
- [ ] Fallback logic complete and tested
- [ ] Source hierarchy validation implemented
- [ ] Legacy Verdetto/XML parsing removed
- [ ] Deanonymization still works after changes

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] JSON output parsed correctly when valid
- [x] Fallback to text works when JSON invalid
- [x] reasoning_trace stored in state
- [x] suggested_actions stored in state with source
- [x] sources_cited sorted by legal hierarchy (Legge > Decreto > Circolare > Interpello)
- [x] Legacy Verdetto/XML parsing code removed
- [x] All existing tests pass (regression) or updated
- [x] Deanonymization flow unbroken
- [x] 90%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-215: Create ActionValidator Service</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
LLM-generated actions often contain generic labels, forbidden patterns, or lack source grounding. Ne...
</summary>


### DEV-215: Create ActionValidator Service

**Reference:** [Technical Intent Part 3.4](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Action Validator)

**Priority:** HIGH | **Effort:** 3h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
LLM-generated actions often contain generic labels, forbidden patterns, or lack source grounding. Need validation layer to filter invalid actions before returning to user.

**Existing Implementation (PR #900 - DEV-201d):**
PR #900 already implemented basic forbidden pattern filtering in `app/services/proactivity_graph_service.py`:
- `FORBIDDEN_ACTION_PATTERNS` - 10 regex patterns for inappropriate suggestions
- `validate_action(action: dict) -> bool` - Validates single action
- `filter_forbidden_actions(actions: list[dict]) -> list[dict]` - Filters batch
- Integrated into Step 100 (`step_100__post_proactivity.py`)

**Solution:**
Extend the existing validation with a comprehensive ActionValidator service that adds:
- Label length validation (8-40 chars) - NOT YET IMPLEMENTED
- Generic label detection - NOT YET IMPLEMENTED
- Source grounding validation - NOT YET IMPLEMENTED
- Icon normalization - NOT YET IMPLEMENTED
- Quality scoring - NOT YET IMPLEMENTED

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-210 (GraphState for validation_result field)
- **Unlocks:** DEV-217 (ActionRegenerator), DEV-218 (Step 100 integration)

**Change Classification:** ADDITIVE

**File:** `app/services/action_validator.py`

**Validation Rules:**
| Rule | Threshold | Action |
|------|-----------|--------|
| Label length minimum | 8 characters | Reject |
| Label length maximum | 40 characters | Truncate to 40 |
| Prompt length minimum | 25 characters | Reject |
| Generic label detection | Exact match list | Reject |
| Forbidden pattern | Regex match | Reject |
| Source grounding | Must reference KB | Warn (log) |
| Valid icon | Enum check | Default to "calculator" |
| JSON validity | Parse check | Reject malformed |

**Forbidden Patterns (Italian):**
```python
FORBIDDEN_PATTERNS = [
    r"consult[ai].*(?:commercialista|avvocato|esperto|professionista)",
    r"contatt[ai].*(?:INPS|INAIL|Agenzia|ufficio)",
    r"rivolgiti.*(?:CAF|patronato|studio)",
    r"verifica.*(?:sul sito|online|portale)",
    r"chiedi.*(?:consiglio|parere|aiuto)",
    r"(?:cerca|trova).*(?:professionista|consulente)",
]

GENERIC_LABELS = {
    "approfondisci", "calcola", "verifica", "scopri",
    "leggi", "vedi", "altro", "continua", "info",
    "dettagli", "più info", "saperne di più"
}
```

**Service Interface:**
```python
@dataclass
class ValidationResult:
    is_valid: bool
    rejection_reason: str | None
    warnings: list[str]
    modified_action: dict | None  # If auto-fixed (e.g., truncated label, default icon)

@dataclass
class BatchValidationResult:
    validated_actions: list[dict]
    rejected_count: int
    rejection_log: list[tuple[dict, str]]  # (action, reason)
    quality_score: float  # 0.0-1.0

class ActionValidator:
    def validate(self, action: dict, kb_sources: list[dict]) -> ValidationResult:
        """Validate a single action against all rules."""

    def validate_batch(
        self,
        actions: list[dict],
        response_text: str,
        kb_sources: list[dict]
    ) -> BatchValidationResult:
        """Validate all actions, return filtered list with rejection log."""

    def _check_label_length(self, label: str) -> ValidationResult:
        """Check label length constraints."""

    def _check_forbidden_patterns(self, action: dict) -> ValidationResult:
        """Check for forbidden consultant/verify patterns."""

    def _check_source_grounding(self, action: dict, kb_sources: list[dict]) -> ValidationResult:
        """Check if action references a KB source."""

    def _check_generic_label(self, label: str) -> ValidationResult:
        """Check for overly generic labels."""

    def _normalize_icon(self, icon: str) -> str:
        """Normalize icon to valid enum value or default to 'calculator'."""
```

**Error Handling:**
- Malformed action dict: Reject, log error
- Empty action list: Return empty result with quality_score=0
- **Logging:** Log all rejections with action details for debugging

**Performance Requirements:**
- Single action validation: <5ms
- Batch validation (10 actions): <50ms

**Edge Cases:**
- **All Actions Rejected:** Return empty list, quality_score=0.0
- **Partial Rejection:** Return valid subset
- **Unicode in Labels:** Handle Italian characters correctly
- **Empty Label/Prompt:** Reject as too short
- **Null Fields:** Reject action with missing required fields

**Testing Requirements:**
- **TDD:** Write `tests/unit/services/test_action_validator.py` FIRST
- **Unit Tests:**
  - `test_rejects_short_label` - Labels <8 chars rejected
  - `test_truncates_long_label` - Labels >40 chars truncated
  - `test_rejects_short_prompt` - Prompts <25 chars rejected
  - `test_rejects_forbidden_patterns` - "consulta commercialista" rejected
  - `test_rejects_generic_labels` - "approfondisci" rejected
  - `test_accepts_valid_action` - Well-formed actions pass
  - `test_warns_no_source_grounding` - Warning logged, action accepted
  - `test_normalizes_invalid_icon` - Unknown icon -> "calculator"
- **Edge Case Tests:**
  - `test_all_actions_rejected` - Empty result, quality=0
  - `test_batch_mixed_validity` - Some pass, some rejected
  - `test_unicode_labels` - Italian characters work
  - `test_null_fields_rejected` - Missing required fields rejected
- **Coverage Target:** 95%+

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Label length validation works (8-40 chars)
- [x] Forbidden patterns detected and rejected
- [x] Generic labels detected and rejected
- [x] Source grounding checked with warnings
- [x] Batch validation returns filtered list + rejection log
- [x] Quality score calculated correctly
- [x] 95%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-216: Create action_regeneration.md Prompt Template</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
When ActionValidator rejects all actions, need a specialized prompt to regenerate actions with expli...
</summary>


### DEV-216: Create action_regeneration.md Prompt Template

**Reference:** [Technical Intent Part 11.5.2](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Regeneration Prompt)

**Priority:** HIGH | **Effort:** 2h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
When ActionValidator rejects all actions, need a specialized prompt to regenerate actions with explicit correction instructions based on rejection reasons.

**Solution:**
Create action_regeneration.md prompt that includes rejection reasons, source information, and extracted values to guide LLM in generating valid actions.

**Agent Assignment:** @ezio (primary)

**Dependencies:**
- **Blocking:** DEV-211 (PromptLoader)
- **Unlocks:** DEV-217 (ActionRegenerator)

**Change Classification:** ADDITIVE

**File:** `app/prompts/v1/action_regeneration.md`

**Template Structure:**
```markdown
# Correzione Azioni Suggerite

Le azioni precedenti sono state scartate per i seguenti motivi:
{rejection_reasons}

## Elementi da Utilizzare OBBLIGATORIAMENTE

### Fonte Principale Citata nella Risposta
{main_source_ref}

### Paragrafo Rilevante dalla Fonte
"{source_paragraph_text}"

### Valori Specifici Menzionati
{extracted_values}

## Regole IMPERATIVE

1. Ogni azione DEVE riferirsi esplicitamente alla fonte sopra indicata
2. Ogni azione DEVE includere almeno uno dei valori specifici
3. Il prompt DEVE essere completo e autosufficiente (>25 caratteri)
4. La label DEVE essere specifica (8-40 caratteri, NO parole generiche)
5. MAI suggerire di consultare professionisti o verificare su siti esterni

## Genera 3 Nuove Azioni

Output JSON:
```json
[
  {
    "id": "regen_1",
    "label": "string (8-40 chars, specifico)",
    "icon": "calculator|search|calendar|file-text|alert-triangle|check-circle|edit|refresh-cw|book-open|bar-chart",
    "prompt": "string (>25 chars, autosufficiente)",
    "source_basis": "string (riferimento alla fonte sopra)"
  },
  ...
]
```

## Esempi di Azioni CORRETTE

✅ "Calcola IVA al 22% su €15.000" (specifico, include valore)
✅ "Verifica scadenza F24 del 16 marzo" (specifico, include data)
✅ "Confronta aliquote IRPEF 2024" (specifico, include anno)

## Esempi di Azioni ERRATE

❌ "Approfondisci" (troppo generico)
❌ "Calcola" (troppo corto, generico)
❌ "Consulta un commercialista" (forbidden pattern)
❌ "Verifica sul sito AdE" (forbidden pattern)


**Template Variables:**
- `{rejection_reasons}` - Bulleted list of validation failures
- `{main_source_ref}` - Primary KB source reference
- `{source_paragraph_text}` - Relevant excerpt (max 500 chars)
- `{extracted_values}` - Comma-separated values from response

**Testing Requirements:**
- **TDD:** Write `tests/unit/prompts/test_action_regeneration.py` FIRST
- **Unit Tests:**
  - `test_prompt_loads_via_loader` - PromptLoader can load it
  - `test_prompt_variables_substitute` - All variables work
  - `test_prompt_contains_json_schema` - Valid JSON example
  - `test_prompt_examples_present` - Correct/incorrect examples included
- **Coverage Target:** 90%+

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Prompt loads without errors
- [x] All variables documented and work
- [x] Contains clear examples of correct/incorrect actions
- [x] JSON output schema clearly specified

---

</details>

<details>
<summary>
<h3>DEV-217: Implement ActionRegenerator Service (Golden Loop)</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 6h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
When ActionValidator rejects all LLM-generated actions, need to regenerate them with correction prom...
</summary>


### DEV-217: Implement ActionRegenerator Service (Golden Loop)

**Reference:** [Technical Intent Part 11.5](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Action Regeneration Loop)

**Priority:** HIGH | **Effort:** 6h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
When ActionValidator rejects all LLM-generated actions, need to regenerate them with correction prompts. This "Golden Loop" ensures users always receive relevant, validated actions.

**Solution:**
Create ActionRegenerator service that triggers when validation fails, uses action_regeneration.md prompt with correction context, and retries up to MAX_ATTEMPTS (2) before falling back to safe template actions.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-215 (ActionValidator), DEV-216 (action_regeneration prompt)
- **Unlocks:** DEV-218 (Step 100 integration)

**Change Classification:** ADDITIVE

**File:** `app/services/action_regenerator.py`

**Service Interface:**
```python
MAX_ATTEMPTS = 2

@dataclass
class ResponseContext:
    """Context for action regeneration."""
    answer: str
    primary_source: dict  # {ref, relevant_paragraph}
    extracted_values: list[str]  # Numbers, dates, percentages from response
    main_topic: str
    kb_sources: list[dict]

class ActionRegenerator:
    def __init__(self, prompt_loader: PromptLoader, llm_client: LLMClient):
        """Initialize with dependencies."""

    async def regenerate_if_needed(
        self,
        original_actions: list[dict],
        validation_result: BatchValidationResult,
        response_context: ResponseContext
    ) -> list[dict]:
        """Attempt to regenerate actions if too many were rejected.

        Args:
            original_actions: Actions from Step 64
            validation_result: Validation results with rejection reasons
            response_context: Contains answer, sources, extracted values

        Returns:
            List of valid actions (regenerated if necessary)
        """
        # If enough valid actions (>=2), return them
        if len(validation_result.validated_actions) >= 2:
            return validation_result.validated_actions

        # Attempt regeneration up to MAX_ATTEMPTS
        for attempt in range(MAX_ATTEMPTS):
            regenerated = await self._attempt_regeneration(
                attempt=attempt,
                rejection_reasons=validation_result.rejection_log,
                context=response_context
            )

            # Validate regenerated actions
            reval_result = self.validator.validate_batch(
                regenerated,
                response_context.answer,
                response_context.kb_sources
            )

            if len(reval_result.validated_actions) >= 2:
                logger.info(f"Action regeneration successful on attempt {attempt + 1}")
                return reval_result.validated_actions

        # Max attempts reached - use safe fallback
        logger.warning("Action regeneration failed, using safe fallback")
        return self._generate_safe_fallback(response_context)

    async def _attempt_regeneration(
        self,
        attempt: int,
        rejection_reasons: list[tuple[dict, str]],
        context: ResponseContext
    ) -> list[dict]:
        """Single regeneration attempt with correction prompt."""

    def _generate_safe_fallback(self, context: ResponseContext) -> list[dict]:
        """Generate minimal safe actions when regeneration fails."""
        # Topic-based action
        # Calculation action if values present
        # Generic deadline action
```

**Safe Fallback Actions:**
```python
def _generate_safe_fallback(self, context: ResponseContext) -> list[dict]:
    actions = []

    # Topic-based action
    if context.main_topic:
        actions.append({
            "id": "fallback_1",
            "label": f"Approfondisci {context.main_topic[:20]}",
            "icon": "search",
            "prompt": f"Dimmi di più su {context.main_topic}",
            "source_basis": "topic_fallback"
        })

    # Calculation action if values present
    if context.extracted_values:
        first_value = context.extracted_values[0]
        actions.append({
            "id": "fallback_2",
            "label": f"Calcolo su {first_value}",
            "icon": "calculator",
            "prompt": f"Esegui un calcolo pratico considerando {first_value}",
            "source_basis": "value_fallback"
        })

    # Generic deadline action
    actions.append({
        "id": "fallback_3",
        "label": "Verifica scadenze",
        "icon": "calendar",
        "prompt": "Quali sono le scadenze rilevanti per questa situazione?",
        "source_basis": "deadline_fallback"
    })

    return actions[:3]
```

**Error Handling:**
- LLM regeneration call fails: Log error, move to next attempt or fallback
- JSON parse fails on regeneration: Log, attempt next
- **Logging:** Log each attempt result, final outcome

**Performance Requirements:**
- Single regeneration attempt: <1.5s
- Max 2 attempts = <3s total overhead

**Edge Cases:**
- **All Regenerations Fail:** Return safe fallback actions
- **LLM Returns Empty:** Count as failed attempt
- **LLM Returns Same Invalid Actions:** Move to next attempt
- **Context Missing Primary Source:** Use topic-only fallback
- **No Values Extracted:** Skip calculation fallback action

**Testing Requirements:**
- **TDD:** Write `tests/unit/services/test_action_regenerator.py` FIRST
- **Unit Tests:**
  - `test_returns_valid_when_enough` - No regen when >=2 valid
  - `test_regeneration_triggered` - Regen when <2 valid
  - `test_regeneration_success_attempt_1` - First attempt succeeds
  - `test_regeneration_success_attempt_2` - Second attempt succeeds
  - `test_max_attempts_respected` - Falls back after MAX_ATTEMPTS
  - `test_safe_fallback_generated` - Safe actions generated after max
  - `test_fallback_includes_topic` - Topic action when available
  - `test_fallback_includes_value` - Value action when values present
- **Edge Case Tests:**
  - `test_llm_call_fails` - Handles LLM errors gracefully
  - `test_json_parse_fails` - Handles invalid JSON
  - `test_empty_regeneration_response` - Empty treated as failure
  - `test_no_primary_source` - Works with minimal context
- **Integration Tests:** Full regeneration flow with mocked LLM
- **Coverage Target:** 90%+

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Regeneration triggered when <2 valid actions
- [x] Max 2 attempts before fallback
- [x] Safe fallback actions generated
- [x] Actions validated after regeneration
- [x] Performance <3s total for regeneration loop
- [x] 90%+ test coverage

---

</details>

<details>
<summary>
<h3>✅ DEV-218: Update Step 100 for Validation-Only with Golden Loop</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
Step 100 now integrates ActionValidator + Golden Loop regeneration with 24 new TDD tests...
</summary>


### DEV-218: Update Step 100 for Validation-Only with Golden Loop

**Reference:** [Technical Intent Part 3.5.4](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Step 100: Action Validation)

**Priority:** HIGH | **Effort:** 3h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
Step 100 currently generates actions from templates or parses from LLM response. With unified output from Step 64, Step 100 should focus on validation only, triggering regeneration via Golden Loop when needed.

**Existing Implementation (PR #900 - DEV-201d):**
PR #900 already integrated `filter_forbidden_actions` into Step 100:
```python
# step_100__post_proactivity.py
from app.services.proactivity_graph_service import filter_forbidden_actions

# Applied to template_actions, verdetto_actions, and llm_parsed_actions
filtered_actions = filter_forbidden_actions(actions)
```

**Solution:**
Extend Step 100 to integrate with the full ActionValidator service (DEV-215) and add Golden Loop regeneration:
- Integrate DEV-215 ActionValidator for comprehensive validation (label length, source grounding)
- Trigger DEV-217 ActionRegenerator when validation fails
- Store validation results in state
- Implement iteration limit (max 2 regenerations)

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-214 (Step 64 unified output), DEV-215 (ActionValidator), DEV-217 (ActionRegenerator)
- **Unlocks:** Production-ready action pipeline

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Primary File:** `app/core/langgraph/nodes/step_100__post_proactivity.py`
- **Affected Files:**
  - `app/services/proactivity_graph_service.py` (already has filter_forbidden_actions)
  - `app/services/action_validator.py` (DEV-215)
- **Related Tests:**
  - `tests/langgraph/agentic_rag/test_step_100_post_proactivity.py`
- **Baseline Command:** `pytest tests/ -k "step_100" -v`

**Pre-Implementation Verification:**
- [ ] Baseline tests pass
- [ ] Step 100 code fully reviewed (246 lines)
- [ ] Understand current action generation flow

**File:** `app/core/langgraph/nodes/step_100__post_proactivity.py`

**Logic Changes:**
```python
async def node_step_100(state: RAGState) -> dict[str, Any]:
    """Post-Response Proactivity Node - Validation Focus."""

    # Skip if pre-proactivity triggered
    if state.get("skip_rag_for_proactivity"):
        return _build_proactivity_update(actions=[], source=None)

    # Skip for chitchat
    if state.get("routing_decision", {}).get("route") == "chitchat":
        return _build_proactivity_update(actions=[], source=None)

    # Get actions from Step 64 (unified output)
    actions = state.get("suggested_actions", [])
    actions_source = state.get("actions_source", "")

    # ✅ NEW: Access KB context for validation and regeneration
    kb_sources = state.get("kb_sources_metadata", [])

    # Fallback if Step 64 didn't generate actions
    if not actions or actions_source == "fallback_needed":
        actions = await _generate_fallback_actions(
            query=state.get("user_query", ""),
            response=_get_response_content(state),
            kb_sources=kb_sources
        )
        actions_source = "fallback"

    # ✅ NEW: Validate actions
    validation_result = action_validator.validate_batch(
        actions=actions,
        response_text=_get_response_content(state),
        kb_sources=kb_sources
    )

    # ✅ NEW: Trigger regeneration if needed (Golden Loop)
    if len(validation_result.validated_actions) < 2:
        regenerated = await action_regenerator.regenerate_if_needed(
            original_actions=actions,
            validation_result=validation_result,
            response_context=_build_response_context(state)
        )
        actions = regenerated
        actions_source = "regenerated"
    else:
        actions = validation_result.validated_actions

    # ✅ NEW: Store validation state
    state["action_validation_result"] = {
        "validated_count": len(actions),
        "rejected_count": validation_result.rejected_count,
        "quality_score": validation_result.quality_score,
        "regeneration_used": actions_source == "regenerated"
    }
    state["actions_validation_log"] = [
        f"{a.get('label', 'N/A')}: {reason}"
        for a, reason in validation_result.rejection_log
    ]

    return _build_proactivity_update(actions=actions, source=actions_source)
```

**Error Handling:**
- Validation service fails: Log error, return original actions
- Regeneration fails: Return safe fallback (from ActionRegenerator)
- **Logging:** Log validation results, regeneration triggers

**Testing Requirements:**
- **TDD:** Write `tests/unit/core/langgraph/nodes/test_step_100_validation.py` FIRST
- **Unit Tests:**
  - `test_step100_validates_actions` - Validation called
  - `test_step100_uses_kb_sources` - kb_sources_metadata accessed
  - `test_step100_triggers_regeneration` - Regen when <2 valid
  - `test_step100_stores_validation_result` - Result in state
  - `test_step100_stores_validation_log` - Rejection log stored
  - `test_step100_returns_validated_actions` - Filtered actions returned
- **Edge Case Tests:**
  - `test_step100_no_actions_from_step64` - Fallback generated
  - `test_step100_all_actions_valid` - No regeneration needed
  - `test_step100_validation_service_fails` - Graceful degradation
- **Regression Tests:** Existing Step 100 tests still pass
- **Coverage Target:** 90%+

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Actions validated before returning
- [x] kb_sources_metadata used for validation
- [x] Regeneration triggered when <2 valid actions
- [x] Validation results stored in state
- [x] All existing Step 100 tests pass (regression)
- [x] 90%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-219: Implement Golden Loop Iteration Control and Metrics</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
Golden Loop lacks configurable iteration limits, backoff strategy, and metrics tracking for monitori...
</summary>


### DEV-219: Implement Golden Loop Iteration Control and Metrics

**Reference:** [Technical Intent Part 5.4](pratikoai-llm-excellence-technical-intent.md#part-5-implementation-priorities) (Iteration Control and Metrics)

**Priority:** HIGH | **Effort:** 3h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
Golden Loop lacks configurable iteration limits, backoff strategy, and metrics tracking for monitoring regeneration performance and preventing infinite loops.

**Solution:**
Create GoldenLoopController service that wraps ActionValidator and ActionRegenerator with configurable limits, exponential backoff, and Prometheus metrics for iteration count, success rate, and latency.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-215 (ActionValidator), DEV-216 (ActionRegenerator), DEV-218 (Step 100 integration)
- **Unlocks:** DEV-238 (Monitoring integration)

**Change Classification:** ADDITIVE

**Impact Analysis:**
- **Risk Level:** LOW - New service wrapping existing functionality
- **Affected Components:** ActionValidator, ActionRegenerator, Step 100

**Pre-Implementation Verification:**
- [ ] Confirm ActionValidator and ActionRegenerator APIs
- [ ] Review existing metrics infrastructure

**Error Handling:**
- Max iterations reached: Return best available actions with warning log
- Backoff overflow: Cap at max_backoff_ms
- **Logging:** Log each iteration with action count, valid count, rejection reasons

**Performance Requirements:**
- Max latency added: <50ms per iteration (excluding LLM calls)
- Memory: O(1) - no accumulation across iterations
- Metrics emission: Non-blocking

**Edge Cases:**
- First iteration succeeds: No backoff needed
- All iterations fail: Return fallback actions from ActionRegenerator
- Zero actions input: Skip validation, use fallback directly
- Negative backoff config: Clamp to minimum 0ms

**File:** `app/services/golden_loop_controller.py`

**Class Interface:**
```python
from dataclasses import dataclass
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class GoldenLoopConfig:
    """Configuration for Golden Loop iteration control."""
    max_iterations: int = 2
    initial_backoff_ms: int = 100
    backoff_multiplier: float = 2.0
    max_backoff_ms: int = 1000
    min_valid_actions: int = 2

@dataclass
class GoldenLoopResult:
    """Result of Golden Loop execution."""
    actions: list[dict]
    iterations_used: int
    total_latency_ms: float
    final_valid_count: int
    regeneration_triggered: bool

class GoldenLoopController:
    """Controls Golden Loop iteration with backoff and metrics."""

    def __init__(
        self,
        validator: "ActionValidator",
        regenerator: "ActionRegenerator",
        config: Optional[GoldenLoopConfig] = None
    ):
        self.validator = validator
        self.regenerator = regenerator
        self.config = config or GoldenLoopConfig()

    async def execute(
        self,
        actions: list[dict],
        kb_sources: list[dict],
        query: str,
        domain: str
    ) -> GoldenLoopResult:
        """
        Execute Golden Loop with iteration control.

        Args:
            actions: Initial suggested actions from Step 64
            kb_sources: KB sources for validation context
            query: User query for regeneration context
            domain: Domain classification for action generation

        Returns:
            GoldenLoopResult with validated/regenerated actions
        """
        ...

    def _calculate_backoff(self, iteration: int) -> int:
        """Calculate backoff delay for given iteration."""
        ...

    def _emit_metrics(self, result: GoldenLoopResult) -> None:
        """Emit Prometheus metrics for iteration."""
        ...
```

**Metrics to Track:**
| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `golden_loop_iterations_total` | Counter | domain, success | Total iterations executed |
| `golden_loop_regeneration_total` | Counter | domain | Regeneration triggers |
| `golden_loop_duration_seconds` | Histogram | domain | Total loop duration |
| `golden_loop_final_valid_actions` | Gauge | domain | Valid actions after loop |

**Testing Requirements:**
- **TDD:** Write `tests/unit/services/test_golden_loop_controller.py` FIRST
- **Unit Tests:**
  - `test_first_iteration_succeeds` - No retry when min_valid_actions met
  - `test_regeneration_triggered` - Retry when below threshold
  - `test_max_iterations_reached` - Stops at limit, returns best
  - `test_backoff_calculation` - Exponential backoff correct
  - `test_metrics_emitted` - Prometheus metrics recorded
  - `test_zero_actions_input` - Uses fallback directly
- **Integration Tests:**
  - `test_full_loop_with_validator_regenerator` - End-to-end flow
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Infinite loop | HIGH | Hard max_iterations cap |
| Slow backoff | MEDIUM | max_backoff_ms cap |
| Metric cardinality explosion | LOW | Limited label set |

**Code Completeness:**
- [ ] All methods have docstrings
- [ ] Type hints on all parameters and returns
- [ ] No TODO comments for required features
- [ ] Structured logging with context fields

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Configurable iteration limits enforced
- [x] Exponential backoff between iterations
- [x] Prometheus metrics for iterations, success rate, latency
- [x] Graceful degradation when max iterations reached
- [x] 90%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-220: Create complexity_classifier.md Prompt Template</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 2h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
Need to classify query complexity (simple/complex/multi_domain) to route to appropriate LLM model an...
</summary>


### DEV-220: Create complexity_classifier.md Prompt Template

**Reference:** Technical Intent Appendix A.1 (Complexity Classifier Prompt)

**Priority:** HIGH | **Effort:** 2h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
Need to classify query complexity (simple/complex/multi_domain) to route to appropriate LLM model and reasoning strategy.

**Solution:**
Create complexity_classifier.md prompt for GPT-4o-mini that outputs JSON classification with reasoning.

**Agent Assignment:** @ezio (primary)

**Dependencies:**
- **Blocking:** DEV-211 (PromptLoader)
- **Unlocks:** DEV-221 (LLMOrchestrator)

**Change Classification:** ADDITIVE

**File:** `app/prompts/v1/complexity_classifier.md`

**Template Structure:**
```markdown
# Classificatore Complessità Query

## Classificazione

Analizza questa query fiscale/legale italiana e classifica la sua complessità.

## Query da Classificare
{query}

## Contesto
- Domini rilevati: {domains}
- Conversazione precedente: {has_history}
- Documenti utente allegati: {has_documents}

## Categorie di Complessità

### SIMPLE
- Domanda singola con risposta diretta
- Definizioni o spiegazioni base
- Aliquote, scadenze, importi standard
- Esempi: "Qual è l'aliquota IVA ordinaria?", "Quando scade l'F24?"

### COMPLEX
- Ragionamento multi-step richiesto
- Casi specifici con variabili multiple
- Scenari con possibili interpretazioni diverse
- Conflitti normativi da risolvere
- Esempi: "Come fatturare consulenza a azienda tedesca?", "Calcolo IRPEF con detrazioni"

### MULTI_DOMAIN
- Coinvolge più domini professionali
- Richiede sintesi tra normative diverse
- Esempi: "Assumo dipendente che apre P.IVA freelance" (lavoro + fiscale)

## Output (JSON OBBLIGATORIO)

```json
{
  "complexity": "simple|complex|multi_domain",
  "domains": ["fiscale", "lavoro", "legale"],
  "confidence": 0.0-1.0,
  "reasoning": "string - breve spiegazione della classificazione"
}
```

**Testing Requirements:**
- **TDD:** Write `tests/unit/prompts/test_complexity_classifier.py` FIRST
- **Unit Tests:**
  - `test_prompt_loads_via_loader` - Loads correctly
  - `test_prompt_variables_substitute` - All variables work
  - `test_prompt_json_schema_valid` - JSON example parseable
- **Coverage Target:** 90%+

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Prompt loads without errors
- [x] All variables documented
- [x] Clear examples for each complexity level
- [x] JSON output schema specified

---

</details>

<details>
<summary>
<h3>DEV-221: Implement LLMOrchestrator Service for Multi-Model Routing</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 8h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
All queries currently use GPT-4o regardless of complexity, costing €0.0155/query. Simple queries sho...
</summary>


### DEV-221: Implement LLMOrchestrator Service for Multi-Model Routing

**Reference:** [Technical Intent Part 3.3](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (LLM Orchestrator)

**Priority:** HIGH | **Effort:** 8h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
All queries currently use GPT-4o regardless of complexity, costing €0.0155/query. Simple queries should use GPT-4o-mini (€0.001), complex queries GPT-4o (€0.015).

**Solution:**
Create LLMOrchestrator service that classifies complexity, routes to appropriate model, generates response with correct reasoning strategy (CoT/ToT), and tracks costs.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-220 (complexity_classifier prompt), DEV-210 (GraphState fields)
- **Unlocks:** DEV-222 (Step 64 routing integration)

**Change Classification:** ADDITIVE

**Files:**
- `app/services/llm_orchestrator.py`
- Modify: `app/services/premium_model_selector.py` (integrate, don't replace)

**Model Configuration:**
```python
from enum import Enum

class QueryComplexity(str, Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"
    MULTI_DOMAIN = "multi_domain"

MODEL_CONFIGS = {
    QueryComplexity.SIMPLE: {
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 1500,
        "cost_input_per_1k": 0.00015,
        "cost_output_per_1k": 0.0006,
        "prompt_template": "unified_response_simple",
        "reasoning_type": "cot",
        "timeout_seconds": 30
    },
    QueryComplexity.COMPLEX: {
        "model": "gpt-4o",
        "temperature": 0.4,
        "max_tokens": 2500,
        "cost_input_per_1k": 0.005,
        "cost_output_per_1k": 0.015,
        "prompt_template": "tree_of_thoughts",
        "reasoning_type": "tot",
        "timeout_seconds": 45
    },
    QueryComplexity.MULTI_DOMAIN: {
        "model": "gpt-4o",
        "temperature": 0.5,
        "max_tokens": 3500,
        "cost_input_per_1k": 0.005,
        "cost_output_per_1k": 0.015,
        "prompt_template": "tree_of_thoughts_multi_domain",
        "reasoning_type": "tot_multi_domain",
        "timeout_seconds": 60
    },
}
```

**Service Interface:**
```python
@dataclass
class ComplexityContext:
    domains: list[str]
    has_history: bool
    has_documents: bool

@dataclass
class UnifiedResponse:
    reasoning: dict
    reasoning_type: str
    tot_analysis: dict | None
    answer: str
    sources_cited: list[dict]
    suggested_actions: list[dict]
    model_used: str
    tokens_input: int
    tokens_output: int
    cost_euros: float
    latency_ms: int

class LLMOrchestrator:
    def __init__(self, prompt_loader: PromptLoader, llm_factory: LLMFactory):
        """Initialize with dependencies."""

    async def classify_complexity(
        self,
        query: str,
        context: ComplexityContext
    ) -> QueryComplexity:
        """Classify query complexity using GPT-4o-mini.

        Cost: ~€0.0002
        Latency: <500ms
        """

    async def generate_response(
        self,
        query: str,
        kb_context: str,
        kb_sources_metadata: list[dict],
        complexity: QueryComplexity,
        conversation_history: list[dict] | None = None
    ) -> UnifiedResponse:
        """Generate response with appropriate model and reasoning strategy."""

    def get_session_costs(self) -> dict:
        """Get detailed cost breakdown for current session."""
```

**Error Handling:**
- Classification fails: Default to SIMPLE complexity
- Model unavailable: Fallback to alternate model
- Timeout: Return partial response if available
- **Logging:** Log complexity decision, model used, costs

**Performance Requirements:**
- Classification: <500ms
- Simple response: <2s
- Complex response: <5s

**Testing Requirements:**
- **TDD:** Write `tests/unit/services/test_llm_orchestrator.py` FIRST
- **Unit Tests:**
  - `test_classify_simple_query` - FAQ-style -> SIMPLE
  - `test_classify_complex_query` - Multi-step -> COMPLEX
  - `test_classify_multi_domain` - Cross-domain -> MULTI_DOMAIN
  - `test_generate_simple_uses_mini` - SIMPLE uses gpt-4o-mini
  - `test_generate_complex_uses_gpt4o` - COMPLEX uses gpt-4o
  - `test_cost_tracking` - Costs calculated correctly
  - `test_classification_fallback` - Defaults to SIMPLE on error
- **Integration Tests:** Full classification + generation flow
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Misclassification wastes tokens | MEDIUM | Conservative classification, log decisions |
| GPT-4o unavailable | HIGH | Fallback to mini with warning |
| Cost tracking inaccurate | LOW | Validate against billing |

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Complexity classification works
- [x] Model routing based on complexity
- [x] Cost tracking per query
- [x] Fallback on classification failure
- [x] 90%+ test coverage (95.3% achieved)

---

</details>

<details>
<summary>
<h3>DEV-222: Integrate LLMOrchestrator with Step 64</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 3h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
Step 64 needs to use LLMOrchestrator for complexity-based model selection and reasoning strategy.
</summary>


### DEV-222: Integrate LLMOrchestrator with Step 64

**Reference:** [Technical Intent Part 3.5.3](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Step 64 routing)

**Priority:** HIGH | **Effort:** 3h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
Step 64 needs to use LLMOrchestrator for complexity-based model selection and reasoning strategy.

**Solution:**
Update Step 64 to call LLMOrchestrator.classify_complexity(), then generate_response() with appropriate model.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-221 (LLMOrchestrator), DEV-214 (Step 64 unified output)
- **Unlocks:** Cost-optimized query processing

**Change Classification:** MODIFYING

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Complexity classified before LLM call
- [x] Model selected based on complexity
- [x] Cost tracked in state
- [x] All existing Step 64 tests pass (34 tests, no regression)

---

</details>

<details>
<summary>
<h3>DEV-223: Create tree_of_thoughts.md Prompt Template</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 4h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
Complex queries need Tree of Thoughts reasoning to explore multiple hypotheses before selecting the ...
</summary>


### DEV-223: Create tree_of_thoughts.md Prompt Template

**Reference:** [Technical Intent Part 3.2.4](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Tree of Thoughts Prompt)

**Priority:** HIGH | **Effort:** 4h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
Complex queries need Tree of Thoughts reasoning to explore multiple hypotheses before selecting the best answer.

**Solution:**
Create tree_of_thoughts.md prompt with hypothesis generation, evaluation, and selection phases.

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-211 (PromptLoader)
- **Unlocks:** DEV-224, DEV-231

**Change Classification:** ADDITIVE

**File:** `app/prompts/v1/tree_of_thoughts.md`

**Template Structure:** (See [Technical Intent Part 2.3.2](pratikoai-llm-excellence-technical-intent.md#part-2-target-architecture))
- Hypothesis generation (3-4 scenarios)
- Source-weighted evaluation
- Best hypothesis selection with reasoning
- Alternative scenario documentation

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Generates 3-4 hypotheses
- [x] Evaluates with source weights (Italian legal hierarchy)
- [x] Selects best with reasoning
- [x] Documents alternatives

---

</details>

<details>
<summary>
<h3>DEV-224: Create tree_of_thoughts_multi_domain.md Prompt Template</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 3h | <strong>Status:</strong> ✅ COMPLETED (2025-01-03)<br>
Multi-domain queries (e.g., labor + tax) need parallel analysis across professional domains.
</summary>


### DEV-224: Create tree_of_thoughts_multi_domain.md Prompt Template

**Reference:** [Technical Intent Part 2.3.3](pratikoai-llm-excellence-technical-intent.md#part-2-target-architecture) (Multi-Domain ToT)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** ✅ COMPLETED (2025-01-03)

**Problem:**
Multi-domain queries (e.g., labor + tax) need parallel analysis across professional domains.

**Solution:**
Create tree_of_thoughts_multi_domain.md for cross-domain synthesis.

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-223 (tree_of_thoughts.md)
- **Unlocks:** DEV-225

**Change Classification:** ADDITIVE

**Acceptance Criteria:**
- [x] Tests written BEFORE implementation (TDD)
- [x] Analyzes multiple domains in parallel
- [x] Identifies domain conflicts
- [x] Synthesizes cross-domain answer

---

</details>

<details>
<summary>
<h3>DEV-225: Implement TreeOfThoughtsReasoner Service</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 5h | <strong>Status:</strong> NOT STARTED<br>
TreeOfThoughtsReasoner service needed to orchestrate multi-hypothesis reasoning with source weightin...
</summary>


### DEV-225: Implement TreeOfThoughtsReasoner Service

**Reference:** [Technical Intent Part 2.3](pratikoai-llm-excellence-technical-intent.md#part-2-target-architecture) (Tree of Thoughts Architecture)

**Priority:** HIGH | **Effort:** 5h | **Status:** NOT STARTED

**Problem:**
TreeOfThoughtsReasoner service needed to orchestrate multi-hypothesis reasoning with source weighting, confidence scoring, and risk analysis for complex legal/tax queries.

**Solution:**
Create TreeOfThoughtsReasoner service that generates multiple hypotheses, scores them against sources using SourceHierarchy, and selects the best path with confidence and risk metadata.

**Agent Assignment:** @ezio (primary), @egidio (review), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-223 (tree_of_thoughts.md), DEV-224 (multi_domain.md), DEV-227 (SourceHierarchy)
- **Unlocks:** DEV-226 (Step 64 integration), DEV-231 (Risk Analysis)

**Change Classification:** ADDITIVE

**Impact Analysis:**
- **Risk Level:** MEDIUM - Core reasoning service
- **Affected Components:** Step 64, LLMOrchestrator, SourceHierarchy

**Pre-Implementation Verification:**
- [ ] Confirm tree_of_thoughts.md prompt template exists
- [ ] Confirm SourceHierarchy API
- [ ] Review LLMOrchestrator integration points

**Error Handling:**
- LLM call fails: Return single-path CoT fallback
- No sources available: Generate hypotheses without source weighting
- Timeout: Return best hypothesis so far with partial confidence
- **Logging:** Log hypothesis generation, scoring, selection with structured context

**Performance Requirements:**
- Max hypotheses: 4 (configurable)
- Parallel hypothesis generation where possible
- Total ToT latency: <3s for complex queries
- Memory: O(n) where n = hypothesis count

**Edge Cases:**
- Single valid hypothesis: Return directly without comparison
- All hypotheses low confidence: Flag for human review
- Conflicting sources: Apply SourceHierarchy precedence
- Multi-domain query: Use tree_of_thoughts_multi_domain.md

**File:** `app/services/tree_of_thoughts_reasoner.py`

**Class Interface:**
```python
from dataclasses import dataclass
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class ToTHypothesis:
    """Single hypothesis in Tree of Thoughts."""
    id: str
    reasoning_path: str
    conclusion: str
    confidence: float
    sources_used: list[dict]
    source_weight_score: float
    risk_level: Optional[str] = None
    risk_factors: Optional[list[str]] = None

@dataclass
class ToTResult:
    """Result of Tree of Thoughts reasoning."""
    selected_hypothesis: ToTHypothesis
    all_hypotheses: list[ToTHypothesis]
    reasoning_trace: dict
    total_latency_ms: float
    complexity_used: str

class TreeOfThoughtsReasoner:
    """Orchestrates multi-hypothesis reasoning with source weighting."""

    def __init__(
        self,
        llm_orchestrator: "LLMOrchestrator",
        source_hierarchy: "SourceHierarchy",
        prompt_loader: "PromptLoader"
    ):
        self.llm_orchestrator = llm_orchestrator
        self.source_hierarchy = source_hierarchy
        self.prompt_loader = prompt_loader

    async def reason(
        self,
        query: str,
        kb_sources: list[dict],
        complexity: str,
        max_hypotheses: int = 4
    ) -> ToTResult:
        """
        Execute Tree of Thoughts reasoning.

        Args:
            query: User query
            kb_sources: Retrieved KB sources with metadata
            complexity: Query complexity (simple/complex/multi_domain)
            max_hypotheses: Maximum hypotheses to generate

        Returns:
            ToTResult with selected hypothesis and full reasoning trace
        """
        ...

    async def _generate_hypotheses(
        self,
        query: str,
        kb_sources: list[dict],
        count: int
    ) -> list[ToTHypothesis]:
        """Generate multiple reasoning hypotheses."""
        ...

    def _score_hypothesis(
        self,
        hypothesis: ToTHypothesis,
        kb_sources: list[dict]
    ) -> float:
        """Score hypothesis using source hierarchy weighting."""
        ...

    def _select_best(
        self,
        hypotheses: list[ToTHypothesis]
    ) -> ToTHypothesis:
        """Select best hypothesis based on confidence and source weight."""
        ...
```

**Scoring Algorithm:**
```python
def _score_hypothesis(self, hypothesis: ToTHypothesis, kb_sources: list[dict]) -> float:
    """
    Score = weighted_sum(source_authority * citation_relevance) * confidence

    Source weights (from SourceHierarchy):
    - Legge: 1.0
    - Decreto: 0.9
    - Circolare: 0.7
    - Interpello: 0.5
    - Prassi: 0.3
    """
    ...
```

**Testing Requirements:**
- **TDD:** Write `tests/unit/services/test_tree_of_thoughts_reasoner.py` FIRST
- **Unit Tests:**
  - `test_generates_multiple_hypotheses` - Correct count generated
  - `test_scores_with_source_hierarchy` - Weighting applied
  - `test_selects_highest_scored` - Best hypothesis returned
  - `test_handles_no_sources` - Graceful degradation
  - `test_handles_multi_domain` - Correct prompt used
  - `test_includes_reasoning_trace` - Full trace in result
- **Integration Tests:**
  - `test_end_to_end_with_llm` - Full flow with mocked LLM
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM latency | HIGH | Parallel hypothesis generation, timeout |
| Inconsistent scoring | MEDIUM | Deterministic source weights |
| Memory for many hypotheses | LOW | Cap at max_hypotheses |

**Code Completeness:**
- [ ] All methods have docstrings
- [ ] Type hints on all parameters and returns
- [ ] No TODO comments for required features
- [ ] Structured logging with session_id, user_id context

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Generates configurable number of hypotheses
- [ ] Scores using SourceHierarchy weights
- [ ] Selects best hypothesis with confidence
- [ ] Includes full reasoning trace
- [ ] Handles multi-domain queries
- [ ] 90%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-226: Integrate TreeOfThoughtsReasoner with Step 64</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 4h | <strong>Status:</strong> NOT STARTED<br>
TreeOfThoughtsReasoner exists as standalone service but isn't connected to the main RAG pipeline. Co...
</summary>


### DEV-226: Integrate TreeOfThoughtsReasoner with Step 64

**Reference:** [Technical Intent Part 5.2](pratikoai-llm-excellence-technical-intent.md#part-5-implementation-priorities) (Step 64 Integration)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
TreeOfThoughtsReasoner (DEV-225) exists as standalone service but isn't connected to the main RAG pipeline. Complex queries still use single-path CoT reasoning.

**Solution:**
Modify Step 64 to use TreeOfThoughtsReasoner for complex/multi_domain queries, storing reasoning trace in GraphState and using selected hypothesis for response generation.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-225 (TreeOfThoughtsReasoner), DEV-222 (LLMOrchestrator integration)
- **Unlocks:** DEV-230 (Dual reasoning)

**Change Classification:** MODIFYING

**Impact Analysis:**
- **Risk Level:** MEDIUM - Modifies critical RAG step
- **Affected Components:** Step 64, GraphState, response generation

**Pre-Implementation Verification:**
- [ ] Confirm TreeOfThoughtsReasoner API
- [ ] Confirm GraphState has reasoning_trace field (DEV-210)
- [ ] Review current Step 64 implementation

**Error Handling:**
- ToT fails: Fall back to single-path CoT
- Timeout: Use partial result with warning
- **Logging:** Log ToT usage, hypothesis count, selection rationale

**Performance Requirements:**
- ToT overhead: <500ms for routing decision
- Complex query total: <5s including ToT
- Simple query unchanged: <2s

**Edge Cases:**
- Complexity classification uncertain: Default to CoT
- ToT returns single hypothesis: Treat as CoT result
- Mid-query complexity upgrade: Not supported, use initial classification

**File:** `app/langgraph/step64_actions.py`

**Integration Points:**
```python
# In Step 64 action generation
async def generate_response(state: GraphState) -> GraphState:
    complexity = state.get("query_complexity", "simple")

    if complexity in ("complex", "multi_domain"):
        # Use Tree of Thoughts
        tot_result = await tree_of_thoughts_reasoner.reason(
            query=state["query"],
            kb_sources=state["kb_sources_metadata"],
            complexity=complexity
        )
        state["reasoning_trace"] = tot_result.reasoning_trace
        state["selected_hypothesis"] = tot_result.selected_hypothesis
        # Use hypothesis for response generation
        response = await generate_from_hypothesis(tot_result.selected_hypothesis)
    else:
        # Use standard CoT
        response = await generate_with_cot(state)

    return state
```

**Testing Requirements:**
- **TDD:** Write `tests/unit/core/langgraph/nodes/test_step64_tot_integration.py` FIRST
- **Unit Tests:**
  - `test_simple_query_uses_cot` - ToT not called for simple
  - `test_complex_query_uses_tot` - ToT called for complex
  - `test_multi_domain_uses_tot` - ToT called for multi_domain
  - `test_tot_failure_falls_back_to_cot` - Graceful degradation
  - `test_reasoning_trace_stored` - Trace in GraphState
  - `test_hypothesis_used_for_response` - Selected hypothesis drives response
- **Integration Tests:**
  - `test_end_to_end_complex_query` - Full pipeline with ToT
- **Regression Tests:** All existing Step 64 tests still pass
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Step 64 regression | HIGH | Comprehensive regression tests |
| ToT latency impact | MEDIUM | Timeout and fallback |
| Incorrect complexity routing | MEDIUM | Validate classifier accuracy |

**Code Completeness:**
- [ ] All methods have docstrings
- [ ] Type hints on all parameters and returns
- [ ] No TODO comments for required features
- [ ] Structured logging with session_id, user_id context

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Complex queries routed to TreeOfThoughtsReasoner
- [ ] Reasoning trace stored in GraphState
- [ ] Selected hypothesis used for response
- [ ] Fallback to CoT on ToT failure
- [ ] All existing Step 64 tests pass (regression)
- [ ] 90%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-227: Create Source Hierarchy Mapping and Weighting</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 4h | <strong>Status:</strong> NOT STARTED<br>
Italian legal sources have hierarchy (Legge > Circolare > Interpello). ToT scoring must weight sourc...
</summary>


### DEV-227: Create Source Hierarchy Mapping and Weighting

**Reference:** [Technical Intent Part 11.1](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Source Hierarchy Weighting)

**Priority:** HIGH | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Italian legal sources have hierarchy (Legge > Circolare > Interpello). ToT scoring must weight sources by authority level.

**Solution:**
Create SourceHierarchy service with Italian legal source weights and conflict detection logic.

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-210 (GraphState)
- **Unlocks:** DEV-228 (SourceConflictDetector), DEV-223 (ToT source weighting)

**Change Classification:** ADDITIVE

**File:** `app/services/source_hierarchy.py`

**Hierarchy Definition:**
```python
SOURCE_HIERARCHY = {
    # Level 1 - Primary Sources (weight: 1.0)
    "legge": 1.0,
    "decreto_legislativo": 1.0,
    "dpr": 1.0,
    "decreto_legge": 1.0,

    # Level 2 - Secondary Sources (weight: 0.8)
    "decreto_ministeriale": 0.8,
    "regolamento_ue": 0.8,

    # Level 3 - Administrative Practice (weight: 0.6)
    "circolare": 0.6,
    "risoluzione": 0.6,
    "provvedimento": 0.6,

    # Level 4 - Interpretations (weight: 0.4)
    "interpello": 0.4,
    "faq": 0.4,

    # Level 5 - Case Law (variable weight)
    "cassazione": 0.9,
    "corte_costituzionale": 1.0,
    "cgue": 0.95,
    "ctp_ctr": 0.5,
}
```

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All Italian source types mapped
- [ ] Weights correctly assigned
- [ ] Unknown types default to 0.5

---

</details>

<details>
<summary>
<h3>DEV-228: Implement SourceConflictDetector Service</h3>
<strong>Priority:</strong> HIGH | <strong>Effort:</strong> 6h | <strong>Status:</strong> NOT STARTED<br>
When Circolare contradicts Legge (especially newer law), the conflict must be detected and flagged.
</summary>


### DEV-228: Implement SourceConflictDetector Service

**Reference:** [Technical Intent Part 11.1.3](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Conflict Detection)

**Priority:** HIGH | **Effort:** 6h | **Status:** NOT STARTED

**Problem:**
When Circolare contradicts Legge (especially newer law), the conflict must be detected and flagged.

**Solution:**
Create SourceConflictDetector that identifies conflicts between sources and recommends which to prefer.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-227 (Source Hierarchy)
- **Unlocks:** DEV-231 (Risk Analysis in ToT)

**Change Classification:** ADDITIVE

**File:** `app/services/source_conflict_detector.py`

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Detects hierarchy conflicts
- [ ] Detects temporal conflicts (newer supersedes older)
- [ ] Returns recommendation on which source to prefer

---

</details>

<details>
<summary>
<h3>DEV-229: Implement DualReasoning Data Structures</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 4h | <strong>Status:</strong> NOT STARTED<br>
Reasoning serves two purposes: debugging (internal) and user display (public). Need separate structu...
</summary>


### DEV-229: Implement DualReasoning Data Structures

**Reference:** [Technical Intent Part 11.4](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Internal vs Public Reasoning)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Reasoning serves two purposes: debugging (internal) and user display (public). Need separate structures.

**Solution:**
Create DualReasoning dataclasses for internal technical reasoning and public user-friendly explanation.

**Agent Assignment:** @ezio (primary)

**Dependencies:**
- **Blocking:** DEV-214 (Step 64 unified output)
- **Unlocks:** DEV-230 (ReasoningTransformer)

**Change Classification:** ADDITIVE

**File:** `app/schemas/reasoning.py`

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] InternalReasoning captures full technical trace
- [ ] PublicExplanation is user-friendly Italian
- [ ] Both structures serializable

---

</details>

<details>
<summary>
<h3>DEV-230: Implement ReasoningTransformer Service</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 4h | <strong>Status:</strong> NOT STARTED<br>
Internal reasoning must be transformed to user-friendly Italian explanation without technical jargon...
</summary>


### DEV-230: Implement ReasoningTransformer Service

**Reference:** [Technical Intent Part 11.4.2](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Reasoning Transformation)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Internal reasoning must be transformed to user-friendly Italian explanation without technical jargon.

**Solution:**
Create ReasoningTransformer that converts internal reasoning to public explanation.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-229 (DualReasoning structures)
- **Unlocks:** Frontend reasoning display

**Change Classification:** ADDITIVE

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Confidence scores mapped to Italian labels
- [ ] Source references simplified
- [ ] Selection reasoning user-friendly

---

</details>

<details>
<summary>
<h3>DEV-231: Add Risk Analysis Phase to Tree of Thoughts</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 4h | <strong>Status:</strong> NOT STARTED<br>
Even low-probability scenarios must be flagged if they carry high sanction risk (e.g., frode fiscale...
</summary>


### DEV-231: Add Risk Analysis Phase to Tree of Thoughts

**Reference:** [Technical Intent Part 11.2](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Risk/Sanction Analysis)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Even low-probability scenarios must be flagged if they carry high sanction risk (e.g., frode fiscale).

**Solution:**
Add risk analysis phase to ToT that evaluates sanction risk for each hypothesis.

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-223 (tree_of_thoughts.md), DEV-228 (SourceConflictDetector)
- **Unlocks:** DEV-232 (Risk-aware action generation)

**Change Classification:** MODIFYING

**Risk Categories:**
| Level | Sanction Range | Examples |
|-------|----------------|----------|
| CRITICAL | >100% tax + criminal | Frode fiscale, falsa fatturazione |
| HIGH | 90-180% tax | Omessa dichiarazione |
| MEDIUM | 30-90% tax | Errori formali sostanziali |
| LOW | 0-30% tax | Ritardi, errori formali minori |

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Risk level assigned to each hypothesis
- [ ] High-risk flagged even with low probability
- [ ] Risk actions generated for mitigation

---

</details>

<details>
<summary>
<h3>DEV-232: Implement Response Quality Scoring Service</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 4h | <strong>Status:</strong> NOT STARTED<br>
Need automated quality scoring for responses to enable A/B testing, model comparison, and continuou...
</summary>


### DEV-232: Implement Response Quality Scoring Service

**Reference:** [Technical Intent Part 12.1](pratikoai-llm-excellence-technical-intent.md#part-12-appendices) (Quality Metrics)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Need automated quality scoring for responses to enable A/B testing, model comparison, and continuous improvement. Currently no objective measurement of response quality.

**Solution:**
Create ResponseQualityScorer service that evaluates responses on multiple dimensions: source citation accuracy, reasoning coherence, action relevance, and risk coverage.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-225 (TreeOfThoughtsReasoner), DEV-231 (Risk Analysis), DEV-227 (SourceHierarchy)
- **Unlocks:** DEV-238 (Monitoring dashboard), DEV-241 (A/B testing framework)

**Change Classification:** ADDITIVE

**Impact Analysis:**
- **Risk Level:** LOW - New scoring service, doesn't modify existing flow
- **Affected Components:** Response pipeline (read-only), monitoring

**Pre-Implementation Verification:**
- [ ] Confirm reasoning trace format from DEV-225
- [ ] Confirm source citation format
- [ ] Review risk level format from DEV-231

**Error Handling:**
- Missing reasoning trace: Score only available dimensions
- Invalid source format: Skip source scoring, log warning
- **Logging:** Log all scores with session_id, user_id for analysis

**Performance Requirements:**
- Scoring latency: <100ms (no LLM calls)
- Memory: O(1) - stateless scoring
- Non-blocking: Must not delay response delivery

**Edge Cases:**
- No sources cited: Source score = 0, flag for review
- No suggested actions: Action score = 0, acceptable for informational queries
- Empty reasoning trace: Cannot score reasoning, use default
- Risk analysis missing: Skip risk coverage scoring

**File:** `app/services/response_quality_scorer.py`

**Class Interface:**
```python
from dataclasses import dataclass
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class QualityDimension:
    """Single quality dimension score."""
    name: str
    score: float  # 0.0 to 1.0
    weight: float
    details: Optional[str] = None

@dataclass
class QualityScore:
    """Complete quality assessment for a response."""
    overall_score: float  # Weighted average
    dimensions: list[QualityDimension]
    flags: list[str]  # Quality warnings
    recommendation: str  # "good", "review", "poor"

class ResponseQualityScorer:
    """Evaluates response quality across multiple dimensions."""

    def __init__(
        self,
        source_hierarchy: "SourceHierarchy",
        weights: Optional[dict[str, float]] = None
    ):
        self.source_hierarchy = source_hierarchy
        self.weights = weights or {
            "source_citation": 0.30,
            "reasoning_coherence": 0.25,
            "action_relevance": 0.25,
            "risk_coverage": 0.20
        }

    def score(
        self,
        response: str,
        reasoning_trace: dict,
        sources_cited: list[dict],
        suggested_actions: list[dict],
        kb_sources: list[dict],
        query: str
    ) -> QualityScore:
        """
        Score response quality.

        Args:
            response: Generated response text
            reasoning_trace: Full reasoning trace from ToT/CoT
            sources_cited: Sources cited in response
            suggested_actions: Suggested actions generated
            kb_sources: Original KB sources retrieved
            query: Original user query

        Returns:
            QualityScore with overall score and dimension breakdown
        """
        ...

    def _score_source_citation(
        self,
        sources_cited: list[dict],
        kb_sources: list[dict]
    ) -> QualityDimension:
        """Score source citation accuracy and authority."""
        ...

    def _score_reasoning_coherence(
        self,
        reasoning_trace: dict
    ) -> QualityDimension:
        """Score reasoning coherence and completeness."""
        ...

    def _score_action_relevance(
        self,
        actions: list[dict],
        query: str,
        response: str
    ) -> QualityDimension:
        """Score action relevance to query and response."""
        ...

    def _score_risk_coverage(
        self,
        reasoning_trace: dict,
        response: str
    ) -> QualityDimension:
        """Score coverage of identified risks in response."""
        ...
```

**Scoring Dimensions:**
| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Source Citation | 30% | High-authority sources cited, citation accuracy |
| Reasoning Coherence | 25% | Logical flow, no contradictions, complete trace |
| Action Relevance | 25% | Actions match query intent and response content |
| Risk Coverage | 20% | Identified risks mentioned in response |

**Quality Thresholds:**
| Overall Score | Recommendation | Action |
|---------------|----------------|--------|
| >= 0.8 | "good" | No action needed |
| 0.6 - 0.8 | "review" | Flag for human review |
| < 0.6 | "poor" | Investigate, improve prompts |

**Testing Requirements:**
- **TDD:** Write `tests/unit/services/test_response_quality_scorer.py` FIRST
- **Unit Tests:**
  - `test_scores_all_dimensions` - All 4 dimensions scored
  - `test_weighted_average_correct` - Overall score calculation
  - `test_high_authority_sources_boost_score` - Source hierarchy impact
  - `test_missing_reasoning_trace_handled` - Graceful degradation
  - `test_no_actions_acceptable` - Zero action score doesn't tank overall
  - `test_risk_coverage_scoring` - Risks in response detected
  - `test_quality_thresholds` - Correct recommendation assignment
- **Integration Tests:**
  - `test_score_real_response` - End-to-end with sample data
- **Coverage Target:** 90%+

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| Scoring bias | MEDIUM | Validated weights, human calibration |
| Performance overhead | LOW | Non-blocking, <100ms target |
| False positives | MEDIUM | Conservative thresholds, human review for "review" |

**Code Completeness:**
- [ ] All methods have docstrings
- [ ] Type hints on all parameters and returns
- [ ] No TODO comments for required features
- [ ] Structured logging with session_id, user_id context

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Scores 4 quality dimensions
- [ ] Weighted average calculated correctly
- [ ] Quality recommendation assigned
- [ ] Graceful handling of missing data
- [ ] Non-blocking (<100ms latency)
- [ ] 90%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-233: Create hyde_conversational.md Prompt Template</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 3h | <strong>Status:</strong> NOT STARTED<br>
Current HyDE ignores conversation history, generating irrelevant hypothetical documents for follow-u...
</summary>


### DEV-233: Create hyde_conversational.md Prompt Template

**Reference:** [Technical Intent Part 3.2.5](pratikoai-llm-excellence-technical-intent.md#part-3-component-specifications) (Conversational HyDE)

**Priority:** MEDIUM | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Current HyDE ignores conversation history, generating irrelevant hypothetical documents for follow-up questions like "E per l'IVA?" because it lacks context about what was discussed previously.

**Solution:**
Create hyde_conversational.md prompt template that includes conversation context and update HyDEGeneratorService to pass conversation history to the prompt.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-211 (PromptLoader)
- **Unlocks:** DEV-234, DEV-235

**Change Classification:** ADDITIVE

**File:** `app/prompts/v1/hyde_conversational.md`

**Template Structure:**
```markdown
# HyDE Conversazionale - Generazione Documento Ipotetico

## Contesto Conversazione
{conversation_history}

## Query Corrente
{current_query}

## Istruzioni
Genera un documento ipotetico che risponda alla query considerando il contesto della conversazione.
Se la query contiene pronomi o riferimenti impliciti (es: "questo", "quello", "E per..."),
risolvi il riferimento usando il contesto conversazionale.

## Formato Output
[Documento ipotetico che risponde alla query nel contesto della conversazione]
```

**HyDEGeneratorService Integration:**
```python
# app/services/hyde_generator.py - Required changes

class HyDEGeneratorService:
    async def generate_hyde(
        self,
        query: str,
        conversation_history: list[dict] | None = None,  # NEW PARAMETER
        domain: str | None = None
    ) -> str:
        """Generate hypothetical document for query.

        Args:
            query: Current user query
            conversation_history: Last N conversation turns for context
                Format: [{"role": "user"|"assistant", "content": str}, ...]
            domain: Optional domain hint

        Returns:
            Hypothetical document text
        """
        # Format conversation history for prompt
        history_text = self._format_conversation_history(conversation_history)

        # Use conversational prompt if history provided
        if conversation_history:
            prompt = self.prompt_loader.load(
                "v1/hyde_conversational.md",
                conversation_history=history_text,
                current_query=query
            )
        else:
            prompt = self.prompt_loader.load(
                "v1/hyde_basic.md",
                query=query
            )

        return await self._call_llm(prompt)

    def _format_conversation_history(
        self,
        history: list[dict] | None,
        max_turns: int = 3
    ) -> str:
        """Format last N conversation turns for prompt injection.

        Args:
            history: Full conversation history
            max_turns: Maximum turns to include (default 3)

        Returns:
            Formatted string of recent conversation
        """
        if not history:
            return "Nessun contesto conversazionale disponibile."

        recent = history[-max_turns * 2:]  # Last N turns (user + assistant)
        formatted = []
        for turn in recent:
            role = "Utente" if turn["role"] == "user" else "Assistente"
            formatted.append(f"{role}: {turn['content']}")

        return "\n".join(formatted)
```

**Testing Requirements:**
- **TDD:** Write `tests/unit/services/test_hyde_generator_conversational.py` FIRST
- **Unit Tests:**
  - `test_hyde_includes_conversation_history` - History passed to prompt
  - `test_hyde_formats_last_3_turns` - Only last 3 turns used
  - `test_hyde_resolves_pronouns` - "questo" resolved from context
  - `test_hyde_handles_followup_queries` - "E per..." queries contextualized
  - `test_hyde_fallback_no_history` - Works without history (basic prompt)
- **Integration Tests:**
  - `test_hyde_pipeline_with_history` - Full retrieval with conversational HyDE
- **Coverage Target:** 90%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Prompt template created with conversation_history variable
- [ ] HyDEGeneratorService accepts conversation_history parameter
- [ ] Last 3 conversation turns formatted and passed to prompt
- [ ] Follow-up pronouns ("questo", "quello", "E per...") resolved
- [ ] Generates contextually relevant HyDE for follow-up queries
- [ ] Falls back to basic HyDE when no history provided
- [ ] 90%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-234: Implement QueryAmbiguityDetector Service</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 4h | <strong>Status:</strong> NOT STARTED<br>
Vague queries like "E per l'IVA?" need multi-variant HyDE, not specific hallucinated documents.
</summary>


### DEV-234: Implement QueryAmbiguityDetector Service

**Reference:** [Technical Intent Part 11.3](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Query Vaghe)

**Priority:** MEDIUM | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Vague queries like "E per l'IVA?" need multi-variant HyDE, not specific hallucinated documents.

**Solution:**
Create QueryAmbiguityDetector that identifies ambiguous queries and triggers multi-variant HyDE.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-233 (hyde_conversational.md)
- **Unlocks:** Improved follow-up handling

**Change Classification:** ADDITIVE

**Ambiguity Indicators:**
- Very short queries (<5 words)
- Pronouns without clear antecedent ("questo", "quello")
- Generic follow-ups ("E per...", "E se...")
- Missing key fiscal terms

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Short queries flagged
- [ ] Pronoun ambiguity detected
- [ ] Multi-variant strategy triggered

---

</details>

<details>
<summary>
<h3>DEV-235: Update HyDE Generator for Conversation Awareness</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 2h | <strong>Status:</strong> NOT STARTED<br>
HyDE generator needs to use QueryAmbiguityDetector and generate multi-variant when ambiguous.
</summary>


### DEV-235: Update HyDE Generator for Conversation Awareness

**Reference:** [Technical Intent Part 11.3.3](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Updated HyDE Generator)

**Priority:** MEDIUM | **Effort:** 2h | **Status:** NOT STARTED

**Problem:**
HyDE generator needs to use QueryAmbiguityDetector and generate multi-variant when ambiguous.

**Solution:**
Update HyDEGeneratorService to check ambiguity and generate multi-variant HyDE when needed.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-234 (QueryAmbiguityDetector), DEV-233 (hyde_conversational.md)
- **Unlocks:** Better follow-up retrieval

**Change Classification:** MODIFYING

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Ambiguity checked before generation
- [ ] Multi-variant generated for ambiguous
- [ ] Variants cover multiple scenarios

---

</details>

<details>
<summary>
<h3>DEV-236: Update Source Schema for Paragraph-Level Grounding</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 6h | <strong>Status:</strong> NOT STARTED<br>
Actions reference entire documents instead of specific paragraphs, making citations imprecise.
</summary>


### DEV-236: Update Source Schema for Paragraph-Level Grounding

**Reference:** [Technical Intent Part 11.6](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Paragraph-Level Grounding)

**Priority:** LOW | **Effort:** 6h | **Status:** NOT STARTED

**Problem:**
Actions reference entire documents instead of specific paragraphs, making citations imprecise.

**Solution:**
Add paragraph-level tracking to source schema with paragraph_id and excerpt fields.

**Agent Assignment:** @ezio (primary), @primo (DB review)

**Dependencies:**
- **Blocking:** DEV-213 (Step 40 KB Preservation)
- **Unlocks:** Precise action citations

**Change Classification:** RESTRUCTURING

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] paragraph_id in source metadata
- [ ] source_excerpt in actions
- [ ] UI can show paragraph tooltip

---

</details>

<details>
<summary>
<h3>DEV-237: Implement Paragraph Extraction in Retrieval</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 4h | <strong>Status:</strong> NOT STARTED<br>
Retrieved documents need paragraph-level extraction for precise grounding.
</summary>


### DEV-237: Implement Paragraph Extraction in Retrieval

**Reference:** [Technical Intent Part 11.6.2](pratikoai-llm-excellence-technical-intent.md#part-11-excellence-refinements) (Paragraph Extraction)

**Priority:** LOW | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Retrieved documents need paragraph-level extraction for precise grounding.

**Solution:**
Add paragraph extraction to retrieval pipeline that identifies relevant paragraphs within documents.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-236 (Source schema update)
- **Unlocks:** Precise source citations

**Change Classification:** MODIFYING

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Paragraphs extracted from documents
- [ ] Relevance scored per paragraph
- [ ] Best paragraphs returned in metadata

---

</details>

<details>
<summary>
<h3>DEV-238: Add Detailed Logging for Reasoning Traces</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 3h | <strong>Status:</strong> NOT STARTED<br>
Need visibility into reasoning traces for debugging and quality analysis. Logs must comply with the ...
</summary>


### DEV-238: Add Detailed Logging for Reasoning Traces

**Reference:** [Technical Intent Part 6](pratikoai-llm-excellence-technical-intent.md#part-6-implementation-phases) Phase 4 (Quality & Monitoring)

**Priority:** LOW | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need visibility into reasoning traces for debugging and quality analysis. Logs must comply with the Logging Standards section (lines 81-101) which mandates specific context fields.

**Solution:**
Add structured logging for reasoning traces using structlog with all mandatory context fields from Logging Standards.

**Agent Assignment:** @ezio (primary), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-214 (Step 64 unified output), DEV-229 (DualReasoning)
- **Unlocks:** Quality monitoring

**Change Classification:** ADDITIVE

**Required Context Fields (from Logging Standards):**
All reasoning trace logs MUST include these mandatory fields:
```python
logger.info(
    "reasoning_trace_recorded",
    user_id=state.get("user_id"),           # MANDATORY: Current user identifier
    session_id=state.get("session_id"),     # MANDATORY: Proactivity session context
    operation="reasoning_trace",             # MANDATORY: What was being attempted
    resource_id=state.get("request_id"),    # MANDATORY: Request being processed
    reasoning_type=state.get("reasoning_type"),  # "cot" or "tot"
    reasoning_trace=state.get("reasoning_trace"),
    model_used=state.get("model_used"),
    query_complexity=state.get("query_complexity"),
    latency_ms=elapsed_ms,
)
```

**Log Events to Implement:**
| Event Name | When Logged | Key Fields |
|------------|-------------|------------|
| `reasoning_trace_recorded` | After Step 64 completes | reasoning_type, reasoning_trace, model_used |
| `reasoning_trace_failed` | JSON parse failure | error_type, error_message, content_sample |
| `dual_reasoning_generated` | DualReasoning completes | internal_trace, public_reasoning |
| `tot_hypothesis_evaluated` | Each ToT branch evaluated | hypothesis_id, probability, selected |

**Logging Implementation:**
```python
import structlog
from app.core.logging import get_contextualized_logger

logger = structlog.get_logger(__name__)

def log_reasoning_trace(state: RAGState, elapsed_ms: float) -> None:
    """Log reasoning trace with all mandatory context fields."""
    logger.info(
        "reasoning_trace_recorded",
        # Mandatory fields from Logging Standards
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        operation="reasoning_trace",
        resource_id=state.get("request_id"),
        # Reasoning-specific fields
        reasoning_type=state.get("reasoning_type"),
        reasoning_trace=_truncate_for_log(state.get("reasoning_trace")),
        model_used=state.get("model_used"),
        query_complexity=state.get("query_complexity"),
        latency_ms=elapsed_ms,
    )

def _truncate_for_log(trace: dict | None, max_length: int = 1000) -> str:
    """Truncate reasoning trace for log storage."""
    if not trace:
        return ""
    trace_str = str(trace)
    if len(trace_str) > max_length:
        return trace_str[:max_length] + "...[truncated]"
    return trace_str
```

**Testing Requirements:**
- **TDD:** Write `tests/unit/core/test_reasoning_trace_logging.py` FIRST
- **Unit Tests:**
  - `test_log_includes_user_id` - user_id field present
  - `test_log_includes_session_id` - session_id field present
  - `test_log_includes_request_id` - resource_id field present
  - `test_log_includes_reasoning_type` - reasoning_type field present
  - `test_log_truncates_long_traces` - Traces >1000 chars truncated
  - `test_log_handles_missing_trace` - Empty trace handled gracefully
- **Coverage Target:** 90%+

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All reasoning trace logs include `user_id` (MANDATORY per Logging Standards)
- [ ] All reasoning trace logs include `session_id` (MANDATORY per Logging Standards)
- [ ] All reasoning trace logs include `operation` and `resource_id`
- [ ] Request ID correlation works for log aggregator queries
- [ ] Reasoning traces searchable by user_id/session_id in log aggregator
- [ ] Long traces truncated to prevent log bloat
- [ ] 90%+ test coverage

---

</details>

<details>
<summary>
<h3>DEV-239: Create Cost Monitoring Dashboard</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 4h | <strong>Status:</strong> NOT STARTED<br>
Need real-time visibility into LLM costs per query, model, and complexity level.
</summary>


### DEV-239: Create Cost Monitoring Dashboard

**Reference:** [Technical Intent Part 7.3](pratikoai-llm-excellence-technical-intent.md#part-7-success-metrics) (Cost Metrics)

**Priority:** LOW | **Effort:** 4h | **Status:** NOT STARTED

**Problem:**
Need real-time visibility into LLM costs per query, model, and complexity level.

**Solution:**
Create cost monitoring endpoint and dashboard integration.

**Agent Assignment:** @ezio (primary), @silvano (deployment)

**Dependencies:**
- **Blocking:** DEV-221 (LLMOrchestrator cost tracking)
- **Unlocks:** Cost optimization insights

**Change Classification:** ADDITIVE

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Cost per query tracked
- [ ] Cost by model breakdown
- [ ] Daily/weekly aggregates

---

</details>

<details>
<summary>
<h3>DEV-240: Add Action Quality Metrics</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 3h | <strong>Status:</strong> NOT STARTED<br>
Need metrics to track action quality: validation pass rate, regeneration rate, click-through rate.
</summary>


### DEV-240: Add Action Quality Metrics

**Reference:** [Technical Intent Part 7.1](pratikoai-llm-excellence-technical-intent.md#part-7-success-metrics) (Quality Metrics)

**Priority:** LOW | **Effort:** 3h | **Status:** NOT STARTED

**Problem:**
Need metrics to track action quality: validation pass rate, regeneration rate, click-through rate.

**Solution:**
Add action quality metrics collection and reporting.

**Agent Assignment:** @ezio (primary)

**Dependencies:**
- **Blocking:** DEV-218 (Step 100 validation)
- **Unlocks:** Quality monitoring

**Change Classification:** ADDITIVE

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Validation pass rate tracked
- [ ] Regeneration rate tracked
- [ ] Click-through rate tracked

---

</details>

<details>
<summary>
<h3>DEV-241: Create Prompt A/B Testing Framework</h3>
<strong>Priority:</strong> LOW | <strong>Effort:</strong> 6h | <strong>Status:</strong> NOT STARTED<br>
Need ability to A/B test different prompt versions for quality comparison.
</summary>


### DEV-241: Create Prompt A/B Testing Framework

**Reference:** [Technical Intent Part 6](pratikoai-llm-excellence-technical-intent.md#part-6-implementation-phases) Phase 4 (A/B Testing)

**Priority:** LOW | **Effort:** 6h | **Status:** NOT STARTED

**Problem:**
Need ability to A/B test different prompt versions for quality comparison.

**Solution:**
Create A/B testing framework in PromptLoader with experiment configuration.

**Agent Assignment:** @ezio (primary), @egidio (review)

**Dependencies:**
- **Blocking:** DEV-211 (PromptLoader)
- **Unlocks:** Prompt optimization

**Change Classification:** ADDITIVE

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Experiment configuration in YAML
- [ ] Traffic splitting by percentage
- [ ] Metrics collection per variant

---

</details>

<details>
<summary>
<h3>DEV-242: Create Reasoning Trace UI Component</h3>
<strong>Priority:</strong> MEDIUM | <strong>Effort:</strong> 6h | <strong>Status:</strong> NOT STARTED<br>
Reasoning traces and Tree of Thoughts logic are generated by the backend (DEV-214, DEV-223) but hidd...
</summary>


### DEV-242: Create Reasoning Trace UI Component

**Reference:** [Technical Intent Part 12](pratikoai-llm-excellence-technical-intent.md#part-12-user-experience-uiux) (User Experience)

**Priority:** MEDIUM | **Effort:** 6h | **Status:** NOT STARTED

**Problem:**
Reasoning traces and Tree of Thoughts logic are generated by the backend (DEV-214, DEV-223) but hidden in logs. Professional users (accountants, lawyers) cannot see how PratikoAI reached its conclusions, limiting trust and verification capabilities.

**Solution:**
Create an expandable "Visualizza Ragionamento" (Show Reasoning) UI component in the chat response bubble that displays the step-by-step reasoning logic, source hierarchy used, and any conflict detection results.

**Agent Assignment:** @livia (primary), @ezio (API support), @clelia (tests)

**Dependencies:**
- **Blocking:** DEV-214 (Unified JSON Output with reasoning_trace), DEV-166 (Chat Integration)
- **Unlocks:** User trust, verification capability, educational value

**Change Classification:** ADDITIVE

**File:** `src/components/chat/ReasoningTrace.tsx`

**Why This Matters for Professional Users:**
| Benefit | Example |
|---------|---------|
| **Trust** | User sees AI weighted "Legge" higher than "Circolare" (DEV-227) |
| **Verification** | User checks if conflict detection found contradictions (DEV-228) |
| **Educational** | User understands the legal path to the "Verdetto Operativo" |

**Performance Requirements:**
- Initial render: <50ms
- Expand/collapse animation: 60fps (no jank)
- Memory footprint: <1MB for 100 reasoning traces in DOM
- Lazy rendering for long lists (virtualization if >10 items)

**API Response Structure (from DEV-214):**
```json
{
  "answer": "...",
  "reasoning": {
    "tema_identificato": "Regime forfettario contributi INPS",
    "fonti_utilizzate": [
      "Legge 190/2014, Art. 1, comma 54",
      "Circolare INPS 35/2019"
    ],
    "elementi_chiave": [
      "Aliquota ridotta 35% per forfettari",
      "Applicabile solo a gestione artigiani/commercianti"
    ],
    "conclusione": "L'agevolazione è applicabile con riduzione del 35%"
  },
  "sources_cited": [...],
  "suggested_actions": [...]
}
```

**Component Interface:**
```tsx
// src/components/chat/ReasoningTrace.tsx

interface ReasoningData {
  tema_identificato: string;
  fonti_utilizzate: string[];
  elementi_chiave: string[];
  conclusione: string;
}

interface ReasoningTraceProps {
  reasoning: ReasoningData | null;
  isExpanded?: boolean;
  onToggle?: (expanded: boolean) => void;
  className?: string;
}

// Exported component
export function ReasoningTrace(props: ReasoningTraceProps): JSX.Element | null;

// Helper functions (internal)
function isSourcePrimary(source: string): boolean;  // Detects Legge, D.Lgs, DPR
function formatSourceWithHierarchy(source: string): JSX.Element;
function truncateText(text: string, maxLength: number): string;
```

**Visual Design:**
```
┌─────────────────────────────────────────────────────┐
│ [Answer text here...]                               │
│                                                     │
│ ▶ 💡 Visualizza ragionamento                       │  ← Collapsed (default)
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ [Answer text here...]                               │
│                                                     │
│ ▼ 💡 Visualizza ragionamento                       │  ← Expanded
│ ┌─────────────────────────────────────────────────┐ │
│ │ 📋 Tema: Regime forfettario contributi INPS    │ │
│ │                                                 │ │
│ │ 📚 Fonti utilizzate:                           │ │
│ │   1. Legge 190/2014, Art. 1, comma 54 (⭐)     │ │
│ │   2. Circolare INPS 35/2019                    │ │
│ │                                                 │ │
│ │ 🔑 Elementi chiave:                            │ │
│ │   • Aliquota ridotta 35% per forfettari        │ │
│ │   • Applicabile solo a gestione artigiani/...  │ │
│ │                                                 │ │
│ │ ✅ Conclusione:                                 │ │
│ │   L'agevolazione è applicabile con riduzione   │ │
│ │   del 35% sui contributi previdenziali.        │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Edge Cases:**
- **Nulls/Empty:**
  - `reasoning: null` → Hide accordion entirely (don't show empty state)
  - `reasoning: {}` → Hide accordion (no valid data)
  - `fonti_utilizzate: []` → Hide "Fonti" section, show others
  - `elementi_chiave: []` → Hide "Elementi" section, show others
  - `tema_identificato: ""` → Show "Tema non specificato" placeholder
- **Boundaries:**
  - `fonti_utilizzate.length > 10` → Show first 5, "Mostra altre N fonti"
  - `elementi_chiave.length > 20` → Virtualize list
  - `conclusione.length > 500` → Truncate with "Leggi tutto" expander
- **Validation:**
  - Invalid source format → Render as plain text without hierarchy badge
  - Special characters in text → Escape properly (XSS prevention)
  - Unicode/emoji in content → Render correctly
- **Mobile/Touch:**
  - Touch-friendly tap targets (min 44x44px)
  - Swipe-to-expand gesture (optional enhancement)
  - Landscape/portrait orientation changes

**Testing Requirements:**
- **TDD:** Write `src/__tests__/components/chat/ReasoningTrace.test.tsx` FIRST
- **Unit Tests:**
  - `test_renders_collapsed_by_default` - Accordion starts collapsed
  - `test_expands_on_click` - Click toggles visibility
  - `test_renders_all_reasoning_sections` - All 4 sections shown when data present
  - `test_handles_null_reasoning` - Returns null, no DOM output
  - `test_handles_empty_reasoning` - Returns null for empty object
  - `test_handles_empty_arrays` - Hides sections with empty arrays
  - `test_source_hierarchy_indicator` - ⭐ shows for Legge, D.Lgs, DPR
  - `test_source_hierarchy_not_shown_for_circolari` - No ⭐ for Circolare
  - `test_truncates_long_conclusione` - Text >500 chars truncated
  - `test_shows_expand_button_for_many_fonti` - "Mostra altre" for >5 sources
- **Accessibility Tests:**
  - `test_keyboard_navigation` - Enter/Space toggles accordion
  - `test_aria_expanded_attribute` - Correct ARIA states (true/false)
  - `test_aria_controls_attribute` - Links trigger to content
  - `test_focus_management` - Focus moves appropriately on expand
- **Edge Case Tests:**
  - `test_escapes_special_characters` - XSS prevention
  - `test_handles_unicode_content` - Italian accents, special chars
  - `test_handles_very_long_source_names` - Truncation with tooltip
- **Integration Tests:** `src/__tests__/integration/ChatMessage.test.tsx`
  - `test_reasoning_trace_renders_in_chat_bubble` - Component integrates
- **Regression Tests:** Run `npm test -- --testPathPattern=chat` to verify no conflicts
- **Coverage Target:** 90%+ for new code

**Risks & Mitigations:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| API schema changes | HIGH | Type validation at boundary, graceful degradation |
| Performance with many traces | MEDIUM | Virtualization for >10 items, lazy loading |
| Mobile layout breaks | MEDIUM | Responsive design tests, viewport testing |
| Accessibility compliance | HIGH | WCAG 2.1 AA checklist, automated a11y testing |
| XSS via reasoning content | CRITICAL | Sanitize all text content before rendering |

**Code Structure:**
- Max component file: 150 lines, extract sub-components if larger
- Max hook: 50 lines, split into smaller hooks
- Extract `ReasoningSection.tsx` for each section (tema, fonti, elementi, conclusione)
- Extract `useReasoningTrace.ts` hook for expand/collapse state management

**Code Completeness:** (MANDATORY - NO EXCEPTIONS)
- [ ] No TODO comments for required functionality
- [ ] No hardcoded placeholder values (e.g., `reasoning={mockData}`)
- [ ] All props handled (null, undefined, empty)
- [ ] All conditional rendering paths tested
- [ ] No "will implement later" patterns - component must work end-to-end
- [ ] Integration with ChatMessage component complete and verified

**Acceptance Criteria:**
- [ ] Tests written BEFORE implementation (TDD)
- [ ] Accordion component with collapse/expand functionality
- [ ] Displays all 4 reasoning sections (tema, fonti, elementi, conclusione)
- [ ] Source hierarchy indicated (⭐ for primary sources: Legge, D.Lgs, DPR)
- [ ] Keyboard accessible (Enter/Space to toggle)
- [ ] Gracefully handles missing/null/empty reasoning
- [ ] Mobile-responsive design (tested on 320px-1920px viewports)
- [ ] Integrates with existing ChatMessage component
- [ ] ARIA attributes for accessibility (aria-expanded, aria-controls)
- [ ] Performance: <50ms render, 60fps animations
- [ ] 90%+ test coverage achieved
- [ ] All existing chat tests still pass (regression)
- [ ] No TODO/FIXME comments for required features
- [ ] XSS protection verified

</details>

---

### Phase 9 Summary

| Sub-Phase | Tasks | Effort | Priority |
|-----------|-------|--------|----------|
| 9.1: Foundation | DEV-210 to DEV-214 | 20h | CRITICAL |
| 9.2: Golden Loop | DEV-215 to DEV-219 | 18h | HIGH |
| 9.3: Intelligence | DEV-220 to DEV-226 | 28h | HIGH |
| 9.4: Excellence | DEV-227 to DEV-232 | 26h | HIGH/MEDIUM |
| 9.5: Conversation | DEV-233 to DEV-237 | 18h | MEDIUM/LOW |
| 9.6: Quality & Monitoring | DEV-238 to DEV-241 | 15h | LOW |
| 9.7: Frontend UI | DEV-242 | 6h | MEDIUM |
| **Total** | **33 tasks** | **~131h** | |

**Agent Assignment Summary:**
| Agent | Primary Tasks | Support Tasks |
|-------|---------------|---------------|
| @ezio | 28 tasks | 1 task (API support for DEV-242) |
| @livia | 1 task (DEV-242) | - |
| @clelia | - | 29 tasks (tests) |
| @egidio | - | 8 tasks (review) |
| @primo | - | 1 task (DB review) |
| @silvano | - | 1 task (deployment) |

**Estimated Timeline:** 8-10 weeks at 2-3h/day *(with Claude Code)*
