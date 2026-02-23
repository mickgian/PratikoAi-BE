# Prompt Caching Analysis — PratikoAI Codebase Audit

**Date:** 2026-02-23
**Scope:** Read-only analysis of LLM integration layer for prompt caching opportunities
**Branch:** `claude/analyze-prompt-caching-k9U8M`

---

## Section A: Current Architecture Map

### A.1 Prompt Assembly Pipeline

```
User Query
    │
    ▼
┌─────────────────────────────┐
│  Step 4: LLM Router Service │  ← GPT-4o-mini classifies query (chitchat/technical/etc.)
│  (llm_router_service.py)    │    Uses static ROUTER_SYSTEM_PROMPT
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Steps 20-39: RAG Pipeline  │  ← HyDE generation (Claude Haiku), KB search, context merge
│  (hybrid search, KB, web)   │    Produces: kb_context, kb_sources_metadata, web_sources_metadata
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Step 41: SelectPrompt      │  ← Routes based on classification confidence (≥0.6 threshold)
│  (prompting.py:348-716)     │
└──────┬──────────────┬───────┘
       │              │
       ▼              ▼
┌─────────────┐ ┌─────────────────┐
│ Step 43:    │ │ Step 44:        │
│ Domain      │ │ Default System  │  ← Assembles system prompt with KB context
│ Prompt      │ │ Prompt          │
└──────┬──────┘ └────────┬────────┘
       │                 │
       ▼                 ▼
┌─────────────────────────────┐
│  Steps 45-47: Message Mgmt  │  ← Insert/Replace system message in conversation
│  (CheckSysMsg/Replace/Insert)│
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Step 64: LLM Call (node_step_64)       │
│  ┌─────────────────────────────────┐    │
│  │ PRIMARY PATH: LLMOrchestrator   │    │  ← Builds enriched prompt from v1 templates
│  │ (llm_orchestrator.py)           │    │    Sends as SINGLE user message
│  │  - Complexity classification    │    │    NO system message, NO tools
│  │  - Tree of Thoughts (if complex)│    │
│  │  - Model: production-chat alias │    │
│  └─────────────┬───────────────────┘    │
│                │ (on failure)           │
│                ▼                        │
│  ┌─────────────────────────────────┐    │
│  │ FALLBACK PATH: Direct Provider  │    │  ← Uses system message from Steps 41-47
│  │ (step_64__llmcall orchestrator) │    │    Messages array with conversation history
│  │  - Uses Steps 41-47 prompts     │    │    May include tools
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### A.2 What is Static vs. Dynamic in Each LLM Call

#### Primary Path (LLMOrchestrator — ~90% of requests)

| Component | Static/Dynamic | Location | Size (est.) |
|-----------|---------------|----------|-------------|
| Template instructions (CoT/ToT) | **STATIC** | `app/prompts/v1/*.md` | ~2,000-4,000 tokens |
| Formatting rules, citation rules | **STATIC** | Embedded in v1 templates | ~1,500 tokens |
| Anti-hallucination rules | **STATIC** | Embedded in v1 templates | ~800 tokens |
| Follow-up mode instructions | **SEMI-STATIC** | `is_followup_mode` variable | ~100-200 tokens |
| Completeness section | **SEMI-STATIC** | `completeness_section` variable (empty for follow-ups) | 0-600 tokens |
| `{kb_context}` | **DYNAMIC** | RAG pipeline output | ~500-5,000 tokens |
| `{query}` | **DYNAMIC** | User input | ~10-200 tokens |
| `{kb_sources_metadata}` | **DYNAMIC** | KB search results JSON | ~200-1,000 tokens |
| `{web_sources_metadata}` | **DYNAMIC** | Brave Search results JSON | 0-1,000 tokens |
| `{conversation_context}` | **DYNAMIC** | Last 3 turns, truncated to 200 chars each | 0-600 tokens |
| `{current_date}` | **DAILY CHANGE** | `datetime.date.today().isoformat()` | ~10 tokens |
| `{domains}` | **DYNAMIC** | Detected domains | ~5-20 tokens |

**Critical finding:** Everything is concatenated into a **single user message** and sent with NO system prompt. The entire prompt is one monolithic string.

#### Fallback Path (Direct Provider — ~10% of requests)

| Component | Static/Dynamic | Location | Size (est.) |
|-----------|---------------|----------|-------------|
| `system.md` base prompt | **STATIC** (per process) | `app/core/prompts/system.md` | ~1,500 tokens |
| `{agent_name}` in system.md | **STATIC** | Settings constant | ~5 tokens |
| `{current_date_and_time}` in system.md | **PER-SECOND CHANGE** | `datetime.now()` | ~20 tokens |
| Document analysis override | **STATIC** | `document_analysis_override.md` | ~500 tokens |
| Grounding rules | **SEMI-STATIC** (follow-up vs. new) | `prompting.py` constants | ~400-1,200 tokens |
| KB context section | **DYNAMIC** | RAG pipeline | ~500-5,000 tokens |
| Post-context instruction | **STATIC** | `POST_CONTEXT_INSTRUCTION` | ~150 tokens |
| Web sources section | **DYNAMIC** | Brave Search JSON | 0-1,000 tokens |
| Conversation messages | **DYNAMIC** | Session history | Varies |

#### Auxiliary LLM Calls (6 additional call sites in the pipeline)

| Call | Model | System Prompt | Dynamic Content |
|------|-------|---------------|-----------------|
| Query routing (Step 4) | GPT-4o-mini | `ROUTER_SYSTEM_PROMPT` (STATIC, ~500 tokens) | Query + history context |
| Complexity classification | GPT-4o-mini | `complexity_classifier.md` template (STATIC) | Query + domains + flags |
| HyDE generation | Claude 3 Haiku | `hyde_conversational.md` template (STATIC) | Conversation history + query |
| Domain classification | varies | Hardcoded prompt in `domain_action_classifier.py` | Query text |
| Query normalization | QUERY_NORMALIZATION_MODEL env | Dynamic via `_get_system_prompt()` | Query + conversation context |
| Query reformulation | LLM_MODEL_REFORMULATION env | Embedded in prompt string (STATIC) | Short query + last assistant msg |
| Document analysis | GPT-4o (ChatOpenAI) | Dynamic via `_build_system_prompt(analysis_type)` | Document content + analysis type |

**Note on fallback path:** The production fallback at `app/orchestrators/providers.py:1589` (`_execute_llm_api_call`) calls `provider.chat_completion(messages=messages, **llm_params)` using the message array assembled by Steps 41-47. This is the actual API invocation point for the message-based path, and it does pass tools via `llm_params` when present.

### A.3 Current Ordering of Prompt Components

**Primary Path (v1 templates):**
```
1. Role definition (static)
2. {kb_context} (dynamic)
3. {kb_sources_metadata} (dynamic)
4. {web_sources_metadata} (dynamic)
5. Web sources instructions (static)
6. {query} (dynamic)
7. {conversation_context} (dynamic)
8. {current_date} (daily change)
9. Follow-up handling rules (static)
10. Typo correction rules (static)
11. Chain of Thought instructions (static)
12. Response format rules (static)
13. Citation rules (static)
14. Anti-hallucination rules (static)
15. {is_followup_mode} (semi-static)
16. {completeness_section} (semi-static)
```

**Fallback Path (system message):**
```
1. [If doc query] DOCUMENT_ANALYSIS_OVERRIDE (static)
2. system.md content with {agent_name} and {current_date_and_time} (static per process)
3. [If has KB context] Grounding rules (semi-static)
4. "# Relevant Knowledge Base Context" (static label)
5. {merged_context} (dynamic)
6. POST_CONTEXT_INSTRUCTION (static)
7. [If web sources] Web sources JSON section (dynamic)
```

---

## Section B: Prompt Caching Readiness Score

| Area | Score | Assessment |
|------|-------|------------|
| **System prompt stability** | 🔴 Needs significant refactoring | Primary path has NO system prompt — everything is one user message. Fallback path has `datetime.now()` changing every second. |
| **Tool definition stability** | 🟢 Ready | Tools are static LangChain BaseTool subclasses. Same definitions per deployment. Conversion to Anthropic format is deterministic. |
| **Message-based context injection** | 🔴 Needs significant refactoring | Primary path sends everything as a single user message. No separation between static instructions and dynamic context. |
| **Model consistency within sessions** | 🟡 Needs minor changes | Production model is resolved from registry alias (`production-chat` → `mistral:mistral-large-latest`). Same model used within a session, but multi-model routing exists (GPT-4o-mini for classification, Haiku for HyDE, Mistral for main response). Prompt caching is per-model. |
| **Conversation history management** | 🟡 Needs minor changes | Fallback path sends full message history (no compaction). Primary path truncates to last 3 turns at 200 chars. History grows linearly, but truncation helps. |
| **Deterministic ordering** | 🟢 Ready | Prompt template variables are filled in deterministic order. Tool lists are built deterministically from LangChain tool definitions. |

**Overall Readiness: 🔴 Not ready for Anthropic prompt caching without refactoring**

The core blocker is architectural: the primary LLM call path builds a single monolithic user message with no separation between cacheable static content and per-request dynamic content.

---

## Section C: Identified Cache-Breaking Patterns

### C.1 Critical: Monolithic Prompt Construction (Primary Path)

**File:** `app/services/llm_orchestrator.py:494-548`
**Impact:** Blocks all prompt caching on the primary path

The `_call_llm()` method creates a single `Message(role="user", content=prompt)` containing the entire enriched prompt. With Anthropic prompt caching, `cache_control` breakpoints must be set on specific messages (system, user, assistant). When everything is one message, the entire message must match exactly for a cache hit — which never happens since dynamic content (query, KB context) changes every request.

```python
# llm_orchestrator.py:526-527
messages = [Message(role="user", content=prompt)]
response = await provider.chat_completion(messages=messages, ...)
```

### C.2 Critical: Per-Second Timestamp in System Prompt

**File:** `app/core/prompts/__init__.py:14`
**Impact:** Breaks cache on every request for the fallback path

```python
current_date_and_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
```

The system prompt includes a timestamp that changes every second. Even though `SYSTEM_PROMPT` is loaded once at module import (line 35), if the process restarts or the module is reloaded, it gets a new timestamp. More importantly, this pattern means any dynamic system prompt reconstruction would break caching.

### C.3 High: Follow-up Mode Branching in Prompt Assembly

**Files:**
- `app/services/llm_orchestrator.py:587-609` (primary path)
- `app/orchestrators/prompting.py:876-953` (fallback path)

The prompt structure differs significantly between follow-up and new question modes:
- Follow-ups: `completeness_section` is empty string, `is_followup_mode` has concise instructions
- New questions: `completeness_section` has ~600 tokens of completeness rules

This creates two distinct prompt "shapes" that cannot share a cache prefix.

### C.4 Medium: Dynamic KB Context Injection Position

**File:** `app/orchestrators/prompting.py:869-1010`

In the fallback path, the grounding rules inserted before KB context differ based on:
1. `is_followup` flag → `FOLLOWUP_GROUNDING_RULES` (~400 tokens)
2. `USE_GENERIC_EXTRACTION` flag → Universal extraction rules (~1,200 tokens)
3. Neither → Legacy rules (~300 tokens)

This creates 3 different prompt prefixes before the dynamic content, reducing cache hit potential.

### C.5 Medium: Conditional Document Analysis Override

**Files:**
- `app/orchestrators/prompting.py:523-537` (domain prompt path)
- `app/orchestrators/prompting.py:823-833` (default prompt path)

When `query_composition` is `"pure_doc"` or `"hybrid"`, `DOCUMENT_ANALYSIS_OVERRIDE` is injected at the TOP of the system prompt. This changes the prompt prefix, breaking caching for document queries vs. non-document queries.

### C.6 Low: Web Sources Metadata Injection

**Files:**
- `app/orchestrators/prompting.py:572-596` (domain prompt path)
- `app/orchestrators/prompting.py:988-1010` (default prompt path)
- `app/services/llm_orchestrator.py:628` (primary path)

Web sources are serialized as JSON and injected. Even when the same query is asked, web sources change, and their JSON includes titles, URLs, and snippets that differ between requests.

### C.7 Low: Model Switching Across Pipeline Stages

**Files:**
- `app/services/llm_router_service.py:27-70` — GPT-4o-mini for routing
- `config/llm_models.yaml:284` — Claude 3 Haiku for HyDE generation
- `config/llm_models.yaml:281` — Mistral Large for production chat
- `config/llm_models.yaml:306-308` — Claude 3.5 Sonnet as premium fallback

Different models are used at different pipeline stages. Anthropic prompt caching only applies to Anthropic API calls. Currently, the primary production model is Mistral Large (`production-chat` alias), which means **Anthropic prompt caching has zero impact on the main response generation path** unless the production model is switched to Anthropic.

---

## Section D: Implementation Opportunities

### D.1 Estimated Cache Hit Rates

| Scenario | Estimated Cache Hit Rate | Notes |
|----------|------------------------|-------|
| **Current architecture** | **0%** | No prompt caching implemented. Primary path uses Mistral, not Anthropic. |
| **After switching production model to Anthropic + refactoring** | **60-75%** | System prompt (~2,000-4,000 tokens) can be cached across all requests. Tool definitions cached. |
| **After full optimization** | **75-85%** | With prompt restructuring, follow-up/new normalization, and stable prefixes |

### D.2 Cost Impact Estimate

**Assumptions:**
- Switch production model from Mistral to Claude 3.5 Sonnet (or Claude 4.5 Sonnet)
- Average input prompt: ~4,000-8,000 tokens
- Cacheable prefix (system prompt + instructions): ~2,500-4,000 tokens (~50% of input)
- Anthropic cached token pricing: 90% discount on cached input tokens
- ~500 queries/day (estimated)

| Metric | Without Caching | With Caching | Savings |
|--------|----------------|--------------|---------|
| Cacheable tokens per request | 0 | ~3,000 tokens | — |
| Input cost per request (Claude 3.5 Sonnet) | ~$0.018 | ~$0.0108 | ~40% input cost reduction |
| Daily input cost (500 queries) | ~$9.00 | ~$5.40 | ~$3.60/day |
| Monthly input cost | ~$270 | ~$162 | **~$108/month** |
| Annual input cost | ~$3,240 | ~$1,944 | **~$1,296/year** |

**Note:** These estimates are for input tokens only. Output token costs are unchanged. The actual savings depend heavily on switching to Anthropic as the production provider.

### D.3 Anthropic API Features to Use

1. **`cache_control` breakpoints** — Set `{"type": "ephemeral"}` on:
   - System message (static instructions)
   - Tool definitions block
   - First user message block (if it contains static context like grounding rules)

2. **Auto-caching** — For prompts >1,024 tokens, Anthropic automatically caches. However, explicit `cache_control` markers give more control over what is and isn't cached.

3. **Multi-turn caching** — In multi-turn conversations, the growing message history naturally benefits from prefix caching. Prior turns remain identical.

### D.4 Quick Wins vs. Larger Refactors

#### Quick Wins (< 1 day each)

| # | Change | Impact | Files |
|---|--------|--------|-------|
| 1 | **Replace `datetime.now()` with daily-granularity date in system.md** | Eliminates per-second cache-breaking in fallback path | `app/core/prompts/__init__.py:14` |
| 2 | **Add `cache_control` markers to Anthropic provider** | Enables caching on Anthropic calls that already use system messages | `app/core/llm/providers/anthropic_provider.py:164-174` |
| 3 | **Cache tool definitions in Anthropic format** | Avoids re-conversion and enables tool caching | `app/core/llm/providers/anthropic_provider.py:102-137` |
| 4 | **Stabilize HyDE/classification prompts** | These auxiliary Anthropic calls (Haiku) can benefit from prompt caching immediately | `app/services/llm_router_service.py`, `app/prompts/v1/hyde_conversational.md` |

#### Medium Refactors (1-3 days each)

| # | Change | Impact | Files |
|---|--------|--------|-------|
| 5 | **Refactor LLMOrchestrator to use system + user message separation** | Enables prompt caching on primary path for Anthropic models | `app/services/llm_orchestrator.py:494-548, 550-647` |
| 6 | **Normalize follow-up vs. new-question prompt structure** | Single cacheable prefix with follow-up mode as a flag in the dynamic portion | `app/services/llm_orchestrator.py:587-639`, `app/orchestrators/prompting.py:876-953` |
| 7 | **Restructure v1 templates: static-first ordering** | Move all dynamic variables ({query}, {kb_context}) to the END of templates | `app/prompts/v1/unified_response_simple.md`, `app/prompts/v1/tree_of_thoughts.md` |

#### Larger Refactors (1+ week)

| # | Change | Impact | Files |
|---|--------|--------|-------|
| 8 | **Switch production model to Anthropic** | Required for Anthropic prompt caching to have any impact on main path | `config/llm_models.yaml`, `app/core/llm/model_registry.py` |
| 9 | **Implement multi-message prompt architecture** | System message (cached) + context message (partially cached) + user message (dynamic) | `app/services/llm_orchestrator.py`, `app/core/llm/providers/*.py` |
| 10 | **Implement prompt fingerprinting for cache analytics** | Track actual cache hit rates and optimize prefix stability | New service |

### D.5 Recommended Implementation Order

```
Phase 1 (Immediate — no model switch needed):
  ├── Quick Win #1: Fix datetime.now() → date-only
  ├── Quick Win #2: Add cache_control to Anthropic provider
  ├── Quick Win #3: Cache tool definitions
  └── Quick Win #4: Stabilize HyDE/classification prompts

Phase 2 (Short-term — if switching to Anthropic):
  ├── Medium #5: System/user message separation in LLMOrchestrator
  ├── Medium #7: Restructure v1 templates (static-first)
  └── Medium #6: Normalize follow-up prompt structure

Phase 3 (Strategic):
  ├── Large #8: Switch production model to Anthropic
  ├── Large #9: Multi-message prompt architecture
  └── Large #10: Prompt fingerprinting analytics
```

---

## Section E: Risks and Tradeoffs

### E.1 What Would Be Lost or Constrained

| Constraint | Impact | Mitigation |
|-----------|--------|------------|
| **Static system prompt requirement** | Cannot inject per-request data into system prompt without breaking cache | Move per-request data to user messages |
| **Template ordering rigidity** | All templates must put static content first, dynamic content last | Design pattern discipline; linting rule |
| **Follow-up mode differentiation** | Can't structurally change the prompt prefix based on follow-up status | Use a single template with conditional sections in the dynamic portion |
| **Provider lock-in** | Prompt caching is Anthropic-specific. OpenAI has different caching semantics. | Design the separation generically (system vs. user messages), which benefits all providers |
| **Prompt evolution friction** | Changing static instructions invalidates caches across all sessions | Cache has 5-minute TTL anyway; changes propagate naturally |

### E.2 Impact on Regulatory Freshness (4-Hour Update Cycle)

**Current behavior:** KB content is refreshed from ingestion pipeline. New regulatory documents flow into the knowledge base and appear in RAG results.

**With prompt caching:** Only the static prefix is cached. The dynamic `{kb_context}` and `{kb_sources_metadata}` are injected per-request from the live RAG pipeline. **No impact on regulatory freshness.**

However, if the prompt structure were changed (e.g., new grounding rules), the cache would invalidate, causing a brief cost spike as all requests generate new cache entries.

### E.3 Impact on Multi-Model Routing Strategy

**Current state:** The system uses different models for different pipeline stages:
- GPT-4o-mini for routing/classification
- Claude 3 Haiku for HyDE generation
- Mistral Large for main response generation
- Claude 3.5 Sonnet as premium fallback

**With Anthropic prompt caching:**
- **Haiku HyDE calls** would benefit immediately (same `hyde_conversational.md` template prefix)
- **Classification calls** are GPT-4o-mini — no Anthropic caching benefit
- **Main response** is Mistral — no Anthropic caching benefit unless switched
- **Premium fallback** is Claude 3.5 Sonnet — would benefit from caching

**Key insight:** To fully leverage Anthropic prompt caching, the production model (`production-chat` alias in `config/llm_models.yaml:281`) would need to point to an Anthropic model instead of Mistral. This is a strategic decision that affects pricing, quality, and latency tradeoffs.

### E.4 Conflicts with Existing Redis Caching Layer

**Current Redis caching** (`app/services/cache.py`) operates at a **different level** than prompt caching:

| Layer | What's Cached | TTL | Scope |
|-------|--------------|-----|-------|
| **Redis (current)** | Full LLM responses, conversation history, HyDE docs, MultiQuery variants | Configurable (hours) | Exact query match (hash of messages + model + temperature) |
| **Anthropic Prompt Caching (proposed)** | Prompt prefix tokens (system prompt, instructions) | 5 minutes (auto-expiry) | Token-level prefix match across different requests |

**These layers are complementary, not conflicting:**
- Redis cache: Eliminates LLM calls entirely for identical queries
- Prompt caching: Reduces cost of LLM calls that DO happen (cache miss at Redis level)

**Order of evaluation:**
```
Request → Redis cache check → [HIT] → Return cached response (no LLM call)
                            → [MISS] → LLM call with prompt caching → Cache response in Redis
```

The hardened cache key (`_generate_hardened_response_key`) already includes `prompt_version` — this aligns well with prompt caching, as changes to the static prefix would naturally invalidate both caches.

### E.5 Anthropic-Specific Prompt Caching Behavior

Important Anthropic prompt caching characteristics to be aware of:

1. **Cache TTL is 5 minutes** — Caches auto-expire. High-traffic periods benefit more.
2. **Minimum cacheable size is 1,024 tokens** — System prompts under this threshold won't be cached.
3. **Cache is per-model** — Switching between Claude 3 Haiku and Claude 3.5 Sonnet means separate caches.
4. **Write cost** — First request with a new prefix pays a small cache write premium (~25% more than uncached input). This is amortized over subsequent cache hits.
5. **Cached reads cost 90% less** — The discount is substantial, making the write premium worthwhile at even 2 cache hits within the 5-minute window.

---

## Appendix: File Reference

### Prompt Construction Files
| File | Purpose | Lines |
|------|---------|-------|
| `app/core/prompts/__init__.py` | Loads system prompt, document prompts at import time | 1-38 |
| `app/core/prompts/system.md` | Main system prompt (Italian fiscal expert persona) | 1-132 |
| `app/core/prompts/document_analysis.md` | Document analysis guidelines | 1-173 |
| `app/core/prompts/document_analysis_override.md` | Short override directive for doc queries | 1-157 |
| `app/prompts/v1/unified_response_simple.md` | CoT response template (SIMPLE queries) | 1-341 |
| `app/prompts/v1/tree_of_thoughts.md` | ToT template (COMPLEX queries) | 1-232 |
| `app/prompts/v1/tree_of_thoughts_multi_domain.md` | ToT template (MULTI_DOMAIN queries) | — |
| `app/prompts/v1/hyde_conversational.md` | HyDE document generation template | 1-67 |
| `app/prompts/v1/complexity_classifier.md` | GPT fallback complexity classification | — |
| `app/prompts/config.yaml` | Prompt version and cache TTL config | 1-6 |

### Prompt Assembly & Orchestration Files
| File | Purpose | Lines |
|------|---------|-------|
| `app/orchestrators/prompting.py` | Steps 15, 41, 44, 45, 46, 47 — prompt selection and injection | 1-1438 |
| `app/orchestrators/classify.py` | Step 43 — domain-specific prompt generation | — |
| `app/services/domain_prompt_templates.py` | `PromptTemplateManager` — domain/action template library | 1-100+ |
| `app/services/llm_orchestrator.py` | `LLMOrchestrator` — primary LLM call path with prompt building | 1-880 |
| `app/services/prompt_loader.py` | `PromptLoader` — file-based prompt loading with LRU cache | 1-254 |

### LLM Provider Files
| File | Purpose | Lines |
|------|---------|-------|
| `app/core/llm/providers/anthropic_provider.py` | Anthropic Claude provider (direct API) | 1-499 |
| `app/core/llm/providers/openai_provider.py` | OpenAI provider (direct + LangChain) | 1-461 |
| `app/core/llm/providers/mistral_provider.py` | Mistral provider | — |
| `app/core/llm/base.py` | `LLMProvider` abstract base, `LLMResponse` dataclass | 1-196 |
| `app/core/llm/factory.py` | `LLMFactory` — provider creation and routing | 1-376 |
| `app/core/llm/model_registry.py` | Model registry loading from YAML | — |
| `config/llm_models.yaml` | Centralized model catalog (costs, tiers, aliases) | 1-333 |

### LangGraph Pipeline Files
| File | Purpose | Lines |
|------|---------|-------|
| `app/core/langgraph/nodes/step_064__llm_call.py` | Step 64 node — main LLM call wrapper | 1-167 |
| `app/core/langgraph/tools/knowledge_search_tool.py` | KB search tool definition | 1-178 |
| `app/core/langgraph/tools/duckduckgo_search.py` | Web search tool | — |
| `app/core/langgraph/tools/ccnl_tool.py` | CCNL integration tool | — |
| `app/core/langgraph/tools/faq_tool.py` | FAQ retrieval tool | — |

### Caching Files
| File | Purpose | Lines |
|------|---------|-------|
| `app/services/cache.py` | Redis `CacheService` — LLM responses, conversations, HyDE, MultiQuery | 1-766 |
| `app/core/decorators/cache.py` | Caching decorator | — |

### Router, Classification, & Auxiliary LLM Call Files
| File | Purpose | Lines |
|------|---------|-------|
| `app/services/llm_router_service.py` | LLM-based query routing (GPT-4o-mini) | 1-80+ |
| `app/services/domain_action_classifier.py` | Domain/action classification | — |
| `app/services/local_classifier.py` | Local rule-based complexity classifier | — |
| `app/services/query_normalizer.py` | Document reference extraction (direct OpenAI) | Line 62 |
| `app/services/query_reformulation/llm_reformulator.py` | Short query expansion (direct OpenAI) | Line 85 |
| `app/services/italian_document_analyzer.py` | Document analysis (LangChain ChatOpenAI) | Line 278 |
| `app/services/hyde_generator.py` | HyDE hypothetical document generation | Lines 497, 561 |
| `app/orchestrators/providers.py` | Fallback LLM API call (`_execute_llm_api_call`) | Line 1589 |
