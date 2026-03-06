# ADR-039: Guardrail Streaming for Real-Time LLM Response Delivery

## Status

**ACCEPTED** (2026-03-06)

## Context

PratikoAI uses LLM models to generate complex legal/fiscal responses. Without streaming,
users experience long waits (30-60+ seconds) before seeing any content — especially for
complex and multi-domain queries that trigger Tree of Thoughts (ToT) reasoning.

### Problems Identified

1. **Blocking ToT pipeline**: Complex queries ran the full ToT pipeline (hypothesis generation,
   scoring, selection, final LLM call) as a single blocking operation. The entire response
   was generated before any content was streamed to the client, causing ~60s TTFT (Time To
   First Token).

2. **Safety guardrails needed during streaming**: PratikoAI applies post-processing to LLM
   responses (disclaimer removal, PII deanonymization, section numbering, bold formatting).
   These must work during streaming without buffering the entire response.

3. **No formal documentation**: The streaming architecture was implemented but not documented
   as an architectural decision.

## Decision

Implement **Pattern 3: Guardrail Streaming** — real-time token streaming from the LLM provider
with per-sentence safety filtering applied before each chunk is emitted to the client.

### Architecture

```
LLM token stream
    → accumulate until sentence boundary (. ! ? \n)
    → DisclaimerFilter on sentence (<1ms regex)
    → deanonymize PII placeholders (<1ms string replace)
    → strip XML tags (<answer>, <suggested_actions>, caveats)
    → emit filtered sentence to client via SSE
    → [repeat until stream ends]
    → finalize: SectionNumberingFixer + BoldSectionFormatter on full text
```

### Key Design Decisions

1. **Sentence-level buffering**: Tokens are accumulated until a sentence boundary is detected.
   This allows disclaimer filtering to operate on complete sentences rather than partial tokens.
   Italian abbreviations (es., art., ecc.) are excluded from false sentence splits.

2. **Force-emit threshold**: If the buffer exceeds 500 characters without a sentence boundary,
   content is force-emitted at the nearest word boundary to prevent long pauses.

3. **Keepalive mechanism**: SSE keepalive comments (`: keepalive\n\n`) are sent every 5 seconds
   during the RAG pipeline processing (before streaming starts) to prevent client timeouts.

4. **Guardrail streaming for ALL query types**: Both simple (CoT) and complex (ToT) queries
   use the streaming path. When streaming is requested, the LLM call is deferred from
   step_064 to the streaming handler in graph.py, which uses `generate_response_stream()`.
   The correct prompt template (unified_response_simple, tree_of_thoughts,
   tree_of_thoughts_multi_domain) is automatically selected via `ModelConfig.for_complexity()`.

5. **ToT streaming**: For complex/multi_domain queries with streaming enabled, the blocking
   ToT hypothesis pipeline is skipped. Instead, the ToT prompt template is used directly
   in the streaming path, which produces equivalent output without the multi-LLM-call overhead.
   The reasoning_type is still marked as "tot" in state for metadata purposes.

### Components

| Component | File | Responsibility |
|-----------|------|----------------|
| GuardrailStreamProcessor | `app/services/guardrail_stream_processor.py` | Per-sentence filtering during streaming |
| DisclaimerFilter | `app/services/disclaimer_filter.py` | Removes prohibited disclaimer phrases |
| SinglePassStream | `app/core/streaming_guard.py` | Prevents double iteration of async generators |
| SSE keepalive | `app/core/langgraph/graph.py` | Sends keepalive during RAG processing |
| generate_response_stream | `app/services/llm_orchestrator.py` | Streams LLM response with guardrails |
| step_064 deferred streaming | `app/core/langgraph/nodes/step_064__llm_call.py` | Defers LLM call for streaming path |

### Streaming Pipeline (LangGraph Steps)

```
Step 104 (Stream Check) → determines if streaming requested
Step 105 (Stream Setup) → configures SSE headers
Step 106 (Async Generator) → creates generator wrapper
Step 107 (Single Pass) → wraps with double-iteration guard
Step 108 (Write SSE) → formats chunks as SSE events
Step 109 (Streaming Response) → creates FastAPI StreamingResponse
Step 110 (Send Done) → final client handoff
```

## Consequences

### Positive

- **Fast TTFT**: Users see the first sentence within 2-5 seconds for all query types
- **Safety preserved**: Disclaimer filtering and PII deanonymization run on every sentence
- **Consistent UX**: Simple and complex queries both stream in real-time
- **Timeout prevention**: Keepalive mechanism prevents frontend/proxy timeouts

### Negative

- **No ToT hypothesis metadata for streamed responses**: When streaming is enabled, the
  multi-hypothesis scoring/selection metadata is not available (no reasoning_trace, no
  tot_analysis with confidence scores). The trade-off is acceptable: fast UX > metadata.
- **Post-processing limitations**: Section numbering and bold formatting run at finalization
  only, so the streamed chunks may lack final formatting until the response completes.
- **25% extra token budget**: Streaming responses get 25% more max_tokens to avoid
  mid-generation truncation (since truncated content cannot be recovered once sent).

### Risks

- Italian abbreviation handling may miss edge cases, causing false sentence splits
- Force-emit at 500 chars could split mid-word in rare cases (mitigated by word-boundary search)

## References

- ADR-004: LangGraph for RAG (pipeline architecture)
- ADR-025: LLM Model Inventory & Tiering (model selection)
- DEV-245: Post-LLM disclaimer filtering
- DEV-250/251: Streaming formatting and content preservation
