# Policy-Gated Autonomy Integration Guide

This document explains how to integrate the policy-gated autonomy components into your RAG pipeline.

## Overview

The policy-gated autonomy system adds intelligent decision-making to your RAG workflow:

- **S034a: Retrieval Pre-Gate** - Decides if retrieval and tools are needed
- **Tool Guardrails** - Enforces max 1 tool call per turn + deduplication
- **Golden Epoch Checking** - Only serves Golden if KB hasn't been updated
- **Hardened Cache Keys** - Invalidates cache on epoch/model/tool changes
- **Structured FSM Logging** - Machine-parsable decision logs

## Components

### 1. Retrieval Gate (S034a)

**File**: `app/core/rag/retrieval_gate.py`

**Purpose**: Lightweight gate that decides if a query needs retrieval based on pattern matching.

**Usage**:
```python
from app.core.rag.retrieval_gate import retrieval_gate

# In your RAG workflow, after S034 (classification):
gate = retrieval_gate(user_query)

if gate.needs_retrieval:
    # Proceed to S039 (retrieval)
    # Allow tool_choice="auto"
    tools_allowed = True
else:
    # Skip to S041 (prompt selection)
    # Set tool_choice="none"
    tools_allowed = False
```

**Patterns**:
- **Needs retrieval**: CCNL, article references, years (2024, 2025), institutions (INPS, Agenzia Entrate)
- **No retrieval**: Simple arithmetic, basic definitions, "cos'è"

### 2. Tool Guardrails

**File**: `app/core/rag/tool_guardrails.py`

**Purpose**: Enforces max 1 tool call per turn and deduplicates identical calls.

**Usage**:
```python
from app.core.rag.tool_guardrails import should_execute_tool_call, filter_tool_calls

# Method 1: Check individual tool call
prev_calls = []  # Previously executed calls this turn
new_call = {"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}}

decision = should_execute_tool_call(prev_calls, new_call, state="S075")
if decision.should_execute:
    # Execute the tool
    result = await execute_tool(new_call)
    prev_calls.append(new_call)

# Method 2: Filter a list of tool calls
tool_calls = response.tool_calls  # From LLM
allowed_calls = filter_tool_calls(tool_calls, prev_calls, state="S075")
# allowed_calls will have max 1 element
```

### 3. FSM Logging

**File**: `app/core/rag/fsm_logging.py`

**Purpose**: Structured JSON logging for all decision points.

**Usage**:
```python
from app.core.rag.fsm_logging import (
    log_gate_decision,
    log_golden_check,
    log_fsm_violation,
    log_cache_decision
)

# S034a: Log gate decision
log_gate_decision("S034a", gate.needs_retrieval, gate.reasons, user_query)

# S027: Log Golden epoch check
log_golden_check("S027", confidence=0.95, kb_epoch=100, golden_epoch=100, serve=True)

# Cache check
log_cache_decision("S062", cache_key="abc123...", hit=True, metadata={...})

# FSM violation (if detected)
log_fsm_violation("S034", actual_next="S041", expected_next="S039", severity="warning")
```

### 4. Prompt Policy

**File**: `app/core/rag/prompt_policy.py`

**Purpose**: Tool usage policy text for system prompts.

**Usage**:
```python
from app.core.rag.prompt_policy import get_tool_policy, should_allow_tools

# S041: Add policy to system prompt
policy_text = get_tool_policy(short=False)
system_prompt = base_prompt + "\n\n" + policy_text

# Determine tool_choice based on gate
tool_choice = "auto" if should_allow_tools(gate.needs_retrieval) else "none"
```

### 5. Golden Epoch Checking

**File**: `app/services/golden_fast_path.py` (updated)

**Purpose**: Only serve Golden if KB hasn't been updated since Golden was created.

**Usage**:
```python
from app.services.golden_fast_path import GoldenFastPathService

service = GoldenFastPathService()

# S027: Check if Golden can be served
can_serve = service.can_serve_from_golden(
    confidence=golden_match.confidence,
    kb_epoch=current_kb_epoch,
    golden_epoch=golden_answer.epoch,
    confidence_threshold=0.90
)

if can_serve:
    # S028: Serve Golden
    return golden_answer
else:
    # S029: Merge KB context and go to LLM
    context = merge_kb_context(...)
```

### 6. Hardened Cache Keys

**File**: `app/services/cache.py` (updated)

**Purpose**: Cache key that invalidates when epochs, model, or tools change.

**Usage**:
```python
from app.services.cache import CacheService

cache = CacheService()

# S060-S061: Generate hardened cache key
cache_key = cache._generate_hardened_response_key(
    query_signature="abc123...",
    doc_hashes=["doc1hash", "doc2hash"],
    epochs={
        "kb_epoch": 100,
        "golden_epoch": 95,
        "ccnl_epoch": 50,
        "parser_version": 3
    },
    prompt_version="v1.2.3",
    provider="openai",
    model="gpt-4o-mini",
    temperature=0.2,
    tools_used=True
)

# Check cache
cached = await redis.get(f"llm_response:{cache_key}")
```

## Integration Example

Here's a complete example of integrating all components into your RAG workflow:

```python
from app.core.rag.retrieval_gate import retrieval_gate
from app.core.rag.tool_guardrails import filter_tool_calls
from app.core.rag.fsm_logging import log_gate_decision, log_golden_check
from app.core.rag.prompt_policy import get_tool_policy, should_allow_tools
from app.services.golden_fast_path import GoldenFastPathService
from app.services.cache import CacheService

async def execute_rag_workflow(user_query, attachments, session_id):
    # ... S001-S034: Early steps (validation, classification) ...

    # S034a: Retrieval Gate
    gate = retrieval_gate(user_query)
    log_gate_decision("S034a", gate.needs_retrieval, gate.reasons, user_query)

    if gate.needs_retrieval:
        # S039: Retrieve KB context
        kb_results = await knowledge_search.retrieve_topk(user_query)
        context = kb_results

        # Allow tools
        tools_allowed = True
        tool_choice = "auto"
    else:
        # Skip retrieval
        context = None
        tools_allowed = False
        tool_choice = "none"

    # S041: Select prompt with policy
    policy = get_tool_policy()
    system_prompt = f"{base_prompt}\n\n{policy}"

    # S048-S057: Provider selection
    provider = select_optimal_provider(...)

    # S059-S062: Check cache with hardened key
    cache_key = cache._generate_hardened_response_key(
        query_signature=canonical_query_hash,
        doc_hashes=[h.sha256 for h in attachments],
        epochs={"kb_epoch": kb_epoch, "golden_epoch": golden_epoch},
        prompt_version="v1.2.3",
        provider=provider.name,
        model=model,
        temperature=0.2,
        tools_used=tools_allowed
    )

    cached = await cache.get(cache_key)
    if cached:
        log_cache_decision("S062", cache_key, hit=True)
        return cached

    # S064: LLM call
    response = await provider.chat_completion(
        messages=messages,
        tools=tools if tools_allowed else None,
        tool_choice=tool_choice,
        temperature=0.2
    )

    # S075: Tool check with guardrails
    if response.tool_calls and tools_allowed:
        # Filter to max 1 tool, no duplicates
        allowed_calls = filter_tool_calls(response.tool_calls, [], state="S075")

        # Execute allowed tool calls
        for tool_call in allowed_calls:
            result = await execute_tool(tool_call)
            # Append to messages and make second LLM call
            # (tool execution flow continues...)

    # Cache the result
    await cache.set(cache_key, response, ttl=3600)

    return response
```

## Acceptance Criteria

✅ Queries like "2+2" or "cos'è il regime forfettario?" → skip retrieval, no tool calls, fast answer

✅ Queries like "Quali sono i requisiti CCNL metalmeccanici 2024?" → allow retrieval, at most 1 tool call, with sources

✅ Golden fast-path serves only when kb_epoch <= golden_epoch; otherwise merges KB context

✅ Cache key changes invalidate cached answers when epochs, model, temp, or tool usage change

✅ Structured logs present:
   - `retrieval_gate` / `gate_decision`
   - `golden_check`
   - `tool_decision`
   - `fsm_violation` (if any)

## Testing

See the test files in `tests/` for examples:
- `tests/test_retrieval_gate.py`
- `tests/test_tool_guardrails.py`
- `tests/test_golden_epoch_rule.py`
- `tests/test_cache_key.py`

## Configuration

No environment variables are required. All behavior is governed by:
- Pattern regexes in `retrieval_gate.py`
- `MAX_TOOL_CALLS_PER_TURN = 1` in `tool_guardrails.py`
- Epoch values fetched from database
- Cache TTL in your existing cache config
