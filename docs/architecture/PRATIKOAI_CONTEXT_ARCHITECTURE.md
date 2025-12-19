# PratikoAI Conversation Context Architecture

**Purpose:** Document how conversation context flows through PratikoAI's RAG pipeline
**Audience:** Developers and architects working on PratikoAI
**Last Updated:** 2025-12-12

---

## Overview

PratikoAI uses a 134-step LangGraph pipeline to process user queries. This document explains how conversation context flows through the system and identifies known gaps.

---

## Context Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ CLIENT REQUEST (/chat or /chat/stream)                              │
│ ├─ messages: [user_msg, assistant_msg?, ...]                        │
│ └─ attachment_ids: [uuid1, uuid2]?                                  │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ API LAYER (app/api/v1/chatbot.py)                                   │
│ ├─ Validates session/user                                           │
│ ├─ Resolves attachments via AttachmentResolver                      │
│ └─ Calls agent.get_response() or agent.get_stream_response()        │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ LANGGRAPH AGENT (app/core/langgraph/graph.py)                       │
│ ├─ Creates RAGState with messages, session_id, user_id, attachments │
│ └─ Invokes graph with checkpointer thread_id = session_id           │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1-10: Request Validation Lane                                   │
│ ├─ Validates session/user                                           │
│ ├─ Anonymizes PII in messages (if PRIVACY_ANONYMIZE_REQUESTS=true)  │
│ └─ Creates initial RAGState                                         │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 11-13: Message Processing Lane                                  │
│ ├─ Converts messages to standardized Message objects                │
│ ├─ Extracts latest user_query from messages                         │
│ └─ Validates message count > 0                                      │
│                                                                      │
│ Key file: app/orchestrators/platform.py (step_11__convert_messages) │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ATTACHMENT PROCESSING (DEV-007 Feature)                              │
│ ├─ AttachmentResolver validates user ownership                       │
│ ├─ Waits for document processing (60-second timeout)                 │
│ ├─ Applies prompt injection sanitization                             │
│ ├─ MANDATORY PII anonymization (GDPR compliance)                     │
│ └─ Stores in RAGState["attachments"]                                │
│                                                                      │
│ Key file: app/services/attachment_resolver.py                        │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 20-30: Golden Fast-Path Gate                                    │
│ └─ Check if query matches FAQ database (bypass LLM if match)        │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 31-34: Classification & Scoring                                 │
│ ├─ Classifies domain/action                                         │
│ ├─ Sets query_composition: pure_kb | pure_doc | hybrid | chat       │
│ └─ Calculates confidence scores                                      │
│                                                                      │
│ Key insight: query_composition affects context building priority     │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 35-39: RAG Preparation                                          │
│ ├─ Extracts atomic facts from user_query                            │
│ ├─ Canonicalizes facts (normalize dates, amounts)                    │
│ ├─ KB pre-fetch (searches knowledge base)                            │
│ └─ Stores: canonical_facts, kb_docs in RAGState                     │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 40: BUILD CONTEXT (CRITICAL)                                    │
│                                                                      │
│ Inputs:                                                              │
│ ├─ canonical_facts: Extracted facts from user query                 │
│ ├─ kb_docs: Knowledge base search results                           │
│ ├─ attachments: Converted to doc_facts                              │
│ ├─ messages: Full conversation history                              │
│ └─ query_composition: From Step 31 classification                   │
│                                                                      │
│ Processing:                                                          │
│ ├─ _convert_attachments_to_doc_facts() with PII anonymization       │
│ ├─ Dynamic token budgeting (3500-8000 tokens)                       │
│ ├─ Composition-based prioritization:                                │
│ │   ├─ pure_kb: Prioritizes KB over attachments                    │
│ │   ├─ pure_doc: Prioritizes attachment content                    │
│ │   ├─ hybrid: Balanced weighting                                   │
│ │   └─ chat: Includes conversation history                         │
│ └─ Deduplication and truncation                                     │
│                                                                      │
│ Output:                                                              │
│ ├─ state["context"]: Unified merged text for LLM prompt             │
│ ├─ state["context_metadata"]: source_distribution, quality_score    │
│ └─ state["query_composition"]: Preserved for decision tracing       │
│                                                                      │
│ Key file: app/orchestrators/facts.py (lines 398-623)                 │
│ Key file: app/core/langgraph/nodes/step_040__build_context.py        │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 41-63: Prompt Selection & Provider Setup                        │
│ ├─ Selects domain-specific prompt template                          │
│ ├─ Inserts system message into messages list                        │
│ ├─ Selects LLM provider (OpenAI/Anthropic)                          │
│ ├─ Cost estimation & budget check                                    │
│ └─ Cache lookup                                                      │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 64: LLM CALL                                                     │
│                                                                      │
│ Input:                                                               │
│ ├─ messages[]: Full conversation with system prompt                 │
│ ├─ context: Merged context from Step 40                             │
│ └─ Provider-specific parameters                                      │
│                                                                      │
│ CRITICAL: Response is APPENDED to state["messages"]                  │
│                                                                      │
│ Key file: app/core/langgraph/nodes/step_064__llm_call.py             │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 104-112: Response Processing (if streaming=True)                │
│ ├─ Formats response chunks for SSE                                  │
│ ├─ Yields to client                                                 │
│ └─ Collects full response for database save                         │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PERSISTENCE LAYER                                                    │
│                                                                      │
│ 1. LangGraph Checkpointer (AsyncPostgresSaver):                      │
│    ├─ Full state snapshot at each node                              │
│    ├─ thread_id = session_id                                        │
│    └─ Enables workflow recovery                                      │
│                                                                      │
│ 2. PostgreSQL query_history table:                                   │
│    ├─ Individual interactions (user_query, ai_response)             │
│    ├─ Indexed by user_id, session_id                                │
│    └─ Used for history API and GDPR export                          │
│                                                                      │
│ 3. Redis/In-Memory Cache:                                            │
│    └─ Fast retrieval for active sessions                            │
│                                                                      │
│ Key file: app/services/chat_history_service.py                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## RAGState Definition

The central state container for the entire workflow:

```python
# File: app/core/langgraph/types.py

class RAGState(TypedDict):
    # Core request data
    messages: list[dict]          # Original request messages (as dicts)
    session_id: str               # Primary key for conversation continuity
    user_id: str | None           # Links to user for auth and GDPR
    user_query: str | None        # Extracted user query (from messages)

    # Attachment handling (DEV-007)
    attachments: list[dict] | None    # Resolved file attachments
    doc_facts: list[dict] | None      # Converted from attachments in Step 40

    # RAG processing
    atomic_facts: list[dict] | None   # Raw extracted facts from query
    canonical_facts: list[dict] | None # Normalized atomic facts
    kb_docs: list[dict] | None        # Knowledge base search results

    # Context building
    context: str | None               # Merged context for LLM (from Step 40)
    context_metadata: dict | None     # Source distribution, quality score
    query_composition: str | None     # pure_kb | pure_doc | hybrid | chat

    # LLM response
    llm_response: str | None          # Final response from LLM

    # ... additional fields for streaming, caching, etc.
```

**Key Insight:** The system uses `messages` throughout, not a separate `chat_history` field. All messages flow through steps 1-112 via the RAGState object.

---

## Known Gaps and Issues

### Gap 1: Previous Turns Not Auto-Loaded

**Issue:** When a new request comes in, previous conversation turns are NOT automatically fetched and included.

**Evidence:**
- `chatbot.py` (lines 247-252): Only `processed_messages` from the current request are sent
- Previous turns must be explicitly included by the client in the `messages` array
- LangGraph checkpointer stores state, but it's not automatically merged

**Impact:** If client doesn't send full history, AI loses context of previous turns.

**Workaround:** Frontend must maintain and send full message history with each request.

---

### Gap 2: Attachment Context Not Persisted Across Turns

**Issue:** Document/attachment context is only available for the turn in which attachments are provided.

**Evidence:**
- Attachments are resolved fresh per request (`chatbot.py` lines 214-244)
- Converted to `doc_facts` only for current turn's context building
- Not persisted for subsequent turns

**Impact:** User uploads a document, asks about it, then asks a follow-up without re-attaching → AI has no document context.

**Mitigation Options:**
1. Store resolved attachment content in PostgreSQL indexed by session_id
2. Allow client to reference previous attachment IDs
3. Implement "active documents" concept that persists for session lifetime

---

### Gap 3: Query Composition Not Persisted

**Issue:** The `query_composition` value (`pure_kb/pure_doc/hybrid/chat`) is computed in Step 31 but not saved.

**Evidence:**
- Computed in Step 31 (ClassifyDomain node)
- Used in Step 40 for adaptive context weighting
- Not included in `chat_history_service.save_chat_interaction()`

**Impact:** Cannot analyze why certain context prioritization was applied for historical queries.

---

### Gap 4: Context Metadata Not Saved

**Issue:** Rich context metadata (`source_distribution`, `token_count`, `quality_score`) from Step 40 is not persisted.

**Evidence:**
- Stored in `state["context_metadata"]` during processing
- Never written to `query_history` table

**Impact:** Cannot audit context quality or debug retrieval decisions retrospectively.

---

### Gap 5: PII in Conversation History

**Issue:** While attachments are anonymized, raw query_history entries are NOT anonymized by default.

**Evidence:**
- `save_chat_interaction()` stores raw `user_query` and `ai_response`
- Only request-level anonymization via `PRIVACY_ANONYMIZE_REQUESTS` setting

**Impact:** PII in conversation history could be exposed if database is compromised.

---

## Key Files Reference

| Purpose | File |
|---------|------|
| State Definition | `app/core/langgraph/types.py` |
| Chat API Endpoints | `app/api/v1/chatbot.py` |
| History Persistence | `app/services/chat_history_service.py` |
| Attachment Resolution | `app/services/attachment_resolver.py` |
| Context Building | `app/orchestrators/facts.py` (step_40) |
| Message Conversion | `app/orchestrators/platform.py` (step_11) |
| LLM Call | `app/core/langgraph/nodes/step_064__llm_call.py` |
| History Retrieval | `app/core/langgraph/graph.py` (get_chat_history) |

---

## Session and Thread Management

### Session ID Flow

```
Frontend generates session_id (UUID)
        │
        ▼
ChatRequest includes session from auth token
        │
        ▼
LangGraph uses session_id as checkpointer thread_id
        │
        ▼
query_history table indexes by session_id
        │
        ▼
get_chat_history() retrieves by session_id
```

### Checkpointer Configuration

```python
# File: app/core/langgraph/graph.py

checkpointer = AsyncPostgresSaver(connection_pool)

# Invocation with thread tracking
config = {
    "configurable": {
        "thread_id": session_id  # Links all turns in conversation
    }
}
result = await graph.ainvoke(state, config)
```

**Key Insight:** `thread_id` MUST equal `session_id` for conversation continuity. If these diverge, state recovery breaks.

---

## Token Budget Allocation (Step 40)

Current configuration in PratikoAI:

```
Base budget: 3500 tokens
Per-result scaling: +500 tokens per search result
Maximum budget: 8000 tokens

Allocation priority (depends on query_composition):
├─ pure_kb:   KB docs > atomic facts > doc_facts
├─ pure_doc:  doc_facts > atomic facts > KB docs
├─ hybrid:    Balanced weighting
└─ chat:      Includes conversation history in budget
```

---

## Recommendations for Future Development

1. **Auto-load conversation history:** Fetch previous N turns from PostgreSQL and prepend to messages before graph execution

2. **Persist attachment references:** Store attachment metadata per-session, allowing follow-up questions about previously uploaded documents

3. **Save context metadata:** Extend `save_chat_interaction()` to include:
   - `query_composition`
   - `source_distribution`
   - `context_quality_score`
   - `truncation_applied`

4. **Implement session-scoped document memory:** Track "active documents" per session that remain in context until explicitly removed

5. **Add anaphora resolution:** Track what "it", "that", "the document" refer to across turns

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2025-12-12 | Initial creation based on codebase exploration | System |

---

**Document Status:** Active
**Related ADRs:** ADR-015 (Chat History Storage)
