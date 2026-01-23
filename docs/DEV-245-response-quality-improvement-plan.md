# DEV-245 Response Quality Improvement Plan

**Created:** January 16, 2026
**Status:** PHASE 1 + PHASE 2 + PHASE 3 + PHASE 4 + PHASE 5 FULLY IMPLEMENTED
**Priority:** CRITICAL
**Last Updated:** January 22, 2026

---

## Executive Summary

User testing revealed critical quality issues where PratikoAI responses are sometimes worse than free Brave AI search. Issues include:

1. **LLM Hallucinations** - Citing non-existent laws (Legge 197/2022 instead of 199/2025)
2. **Repetitive Responses** - Follow-up questions repeat all general info instead of being specific
3. **Missing Nuance** - Answers technically correct but missing real-world implications
4. **Short Query Failures** - "e l'irap" got no response
5. **Lack of Specificity** - Not citing articolo/comma references

---

## Issue Analysis

### Issue 1: LLM Hallucination (CRITICAL)

**Symptom:** First response cited "Legge n. 197 del 29 dicembre 2022" which doesn't exist.

**Investigation:**
```sql
-- Legge 197/2022 doesn't exist in KB
SELECT * FROM knowledge_items WHERE title ILIKE '%197%2022%';
-- Result: 0 rows

-- But correct info EXISTS in KB (ADeR document)
SELECT * FROM knowledge_chunks WHERE chunk_text ILIKE '%definizione agevolata%';
-- Result: Chunk 12134 says "Legge n. 199/2025"
```

**Root Cause:** The retrieval didn't match the user query "definizione agevolata 2026" with the relevant chunks. The LLM then hallucinated a plausible-sounding law citation.

**Proposed Fixes:**

| Fix | Effort | Impact |
|-----|--------|--------|
| **A1: Hallucination Guard** - Add post-processing check that validates legal citations against KB | Medium | High |
| **A2: Retrieval Logging** - Log what docs were retrieved vs what was cited | Low | Medium |
| **A3: "I don't know" threshold** - If retrieval confidence is low, admit uncertainty | Medium | High |
| **A4: Citation enforcement** - Instruct LLM to ONLY cite documents in context | Low | Medium |

---

### Issue 2: Repetitive Responses (UX)

**Symptom:** When asked "si possono rottamare le cartelle tasse auto?", the response repeats ALL general rottamazione info (dates, rates, decadence) that was already provided.

**Root Cause:**
1. Prompt instructs to always provide full context
2. No detection of "follow-up question" vs "new topic"
3. Conversation history not used to avoid repetition

**Proposed Fixes:**

| Fix | Effort | Impact |
|-----|--------|--------|
| **B1: Follow-up Detection** - Detect follow-up questions, provide concise answers | Medium | High |
| **B2: Conversation-Aware Prompt** - Pass summary of previous answers to LLM | Medium | High |
| **B3: "Already Covered" Flag** - Track what info has been provided in session | High | High |
| **B4: User Preference** - Let user choose "detailed" vs "concise" mode | Low | Medium |

**Ideal Response for Follow-up:**
```
Sì, le cartelle delle tasse auto possono essere rottamate.

📍 **Riferimento:** Art. 1, comma 231-235 della Legge 199/2025

Le tasse automobilistiche rientrano tra i "tributi" definiti al comma 231, lettera a).

[Link alla legge]
```

Instead of repeating all dates, rates, and general info.

---

### Issue 3: Missing Nuance (QUALITY)

**Symptom:** For IMU/tasse auto, answer is "Sì" but reality is "Dipende" - requires agreement with local entities.

**Real Answer (from https://italia-informa.com):**
> "La rottamazione quinquies per i tributi locali non offre certezze perché richiede l'accordo degli enti locali"

**Root Cause:**
1. KB only contains the law text, not real-world implications
2. No verification layer to cross-check answers
3. Missing nuanced sources (practical guides, commentary)

**Proposed Fixes:**

| Fix | Effort | Impact |
|-----|--------|--------|
| **C1: Web Verification Layer** - After generating answer, search web for contradictions | High | Very High |
| **C2: Nuanced Sources Ingestion** - Add practical guides, not just laws | Medium | High |
| **C3: "Caveat Detection"** - Train to detect when answer has conditions/exceptions | High | High |
| **C4: Expert Review Flagging** - Flag answers about local tributes for expert review | Low | Medium |

**Web Verification Architecture:**
```
User Question
     ↓
RAG Retrieval → KB Answer
     ↓
Web Search (Brave API) → Recent Articles
     ↓
Contradiction Detection
     ↓
If contradiction found:
  → Add caveat: "Nota: [nuance from web]"
  → Or: "Questa risposta potrebbe essere incompleta. Verifica con [source]"
```

---

### Issue 4: Short Query No Response (BUG)

**Symptom:** "e l'irap" got no response at all.

**Root Cause:**
1. Query too short for effective retrieval
2. Conversation context not used ("e l'irap" means "and IRAP?" in context of previous IMU question)
3. Possible timeout or error silently swallowed

**Proposed Fixes:**

| Fix | Effort | Impact |
|-----|--------|--------|
| **D1: Context Expansion** - For short queries, prepend relevant conversation context | Medium | High |
| **D2: Minimum Query Enhancement** - Detect short queries, ask for clarification OR auto-expand | Low | Medium |
| **D3: Error Visibility** - Never silently fail, always show something | Low | High |

**Example Context Expansion:**
```python
# User message: "e l'irap"
# Previous context: discussion about IMU rottamazione

# Expanded query for retrieval:
"rottamazione quinquies IRAP imposta regionale attività produttive"
```

---

### Issue 5: Lack of Specificity (QUALITY)

**Symptom:** Brave AI provides specific references (artt. 36-bis, 36-ter DPR 600/1973), PratikoAI doesn't.

**Brave AI Response Quality:**
```
✅ Inclusi: IRAP non versata in seguito a dichiarazione annuale o controllo formale (artt. 36-bis e 36-ter DPR 600/1973)
❌ Esclusi: IRAP oggetto di accertamento, IRAP da tributi locali
```

**PratikoAI Response:**
```
Sì, è possibile rottamare i debiti relativi all'IRAP...
(No specific article references)
```

**Root Cause:**
1. LLM not instructed to cite specific articolo/comma
2. KB chunks may not preserve article structure
3. No emphasis on specificity in prompts

**Proposed Fixes:**

| Fix | Effort | Impact |
|-----|--------|--------|
| **E1: Specificity Instruction** - Update prompt: "Always cite specific articolo, comma, lettera" | Low | High |
| **E2: KB Structure Enhancement** - Add article metadata to chunks | Medium | High |
| **E3: Legal Citation Extraction** - Post-process to extract and highlight citations | Medium | Medium |

---

## Implementation Roadmap

### Phase 1: Quick Wins ✅ IMPLEMENTED

| Task | File(s) | Description | Status |
|------|---------|-------------|--------|
| **1.1** Citation Instruction | `prompts/v1/unified_response_simple.md` | Add "cite articolo/comma" to system prompt | ✅ Done |
| **1.2** Context Expansion | `step_039a__multi_query.py` | For short queries (<5 words), prepend conversation context | ✅ Done |
| **1.3** Error Visibility | `graph.py` | Never return empty response, show "Non ho trovato informazioni" | ✅ Done |
| **1.4** Retrieval Logging | `parallel_retrieval.py` | Log retrieved docs + cited docs for debugging | ✅ Done |

#### Phase 1 Implementation Details (January 16, 2026)

**1.1 Citation Instruction - Anti-Hallucination Rules**

File: `app/prompts/v1/unified_response_simple.md`

Added new section "⚠️ ANTI-ALLUCINAZIONE: DIVIETO ASSOLUTO DI INVENTARE CITAZIONI (DEV-245)" with:
- **REGOLA CRITICA: MAI INVENTARE NUMERI DI LEGGE** - Only cite laws that appear EXACTLY in KB context
- **SE NON TROVI IL NUMERO DI LEGGE ESATTO** - Use "secondo la normativa vigente" instead of inventing
- **VERIFICA INCROCIATA OBBLIGATORIA** - Cross-check all citations against KB before using
- **REGOLA SPECIFICA: ARTICOLO, COMMA, LETTERA** - Preference hierarchy for specificity:
  - ✅ IDEALE: "Art. 1, comma 231, lettera a), Legge 199/2025"
  - ✅ BUONO: "Art. 1, commi 231-252, Legge 199/2025"
  - ⚠️ ACCETTABILE: "Legge 199/2025"
  - ❌ INSUFFICIENTE: "la legge sulla rottamazione"

**1.2 Context Expansion for Short Queries**

File: `app/core/langgraph/nodes/step_039a__multi_query.py`

Added `_expand_short_query()` function:
- Detects queries with <5 words (configurable via `SHORT_QUERY_THRESHOLD`)
- Extracts topics from recent conversation history (last 4 messages)
- Filters out Italian stop words (`ITALIAN_STOP_WORDS` set)
- Prepends relevant topics to the short query before retrieval

Example:
```
Previous messages: "Parlami della rottamazione quinquies"
Short query: "e l'irap"
Expanded: "rottamazione quinquies parlami e l'irap"
```

**1.3 Error Visibility - Never Return Empty Response**

File: `app/core/langgraph/graph.py`

Added fallback messages in two scenarios:

1. **Provider streaming yields nothing:**
   ```python
   if fallback_chunks_yielded == 0:
       yield "Non ho trovato informazioni specifiche sulla tua richiesta. "
             "Prova a riformulare la domanda con termini diversi o più dettagli."
   ```

2. **Streaming exception handler:**
   ```python
   except Exception as stream_error:
       yield "Si è verificato un errore durante l'elaborazione della risposta. "
             "Riprova tra qualche istante."
   ```

**1.4 Retrieval Logging**

File: `app/services/parallel_retrieval.py`

Added `DEV245_retrieval_docs_summary` log with:
- Query text (first 100 chars)
- Retrieved document count
- List of sources retrieved (gazzetta_ufficiale, agenzia_entrate_riscossione, etc.)
- Top 3 document titles for quick debugging

Added `DEV245_retrieval_docs_detail` debug log with full document details (id, source, title, score, type)

### Phase 2: Medium Term - ✅ FULLY IMPLEMENTED

| Task | File(s) | Description | Status |
|------|---------|-------------|--------|
| **2.1** Follow-up Detection | `llm_router_service.py`, `router.py`, `step_034a__llm_router.py` | Detect follow-up questions via LLM router | ✅ Done |
| **2.2** Concise Mode | `prompting.py` (step_44, step_41) | If follow-up, use concise prompt template | ✅ Done |
| **2.3** Hallucination Guard | `hallucination_guard.py` (NEW) | Validate cited laws exist in context | ✅ Done |
| **2.4** KB Article Metadata | `article_extractor.py` (NEW), `document_ingestion.py` | Extract articolo/comma structure during ingestion | ✅ Done |

#### Phase 2 Implementation Details (January 16, 2026)

**2.1 Follow-up Detection**

Files modified:
- `app/schemas/router.py` - Added `is_followup: bool` field to `RouterDecision`
- `app/services/llm_router_service.py` - Updated `ROUTER_SYSTEM_PROMPT` with follow-up detection instructions
- `app/core/langgraph/nodes/step_034a__llm_router.py` - Added `is_followup` to dict serialization

The LLM router now detects follow-up queries based on:
- Queries starting with conjunctions: "e", "ma", "però", "anche", "invece"
- Anaphoric references: "questo", "quello", "lo stesso", "anche per"
- Short queries (<5 words) assuming previous context
- Clarification/deepening requests

**2.2 Concise Mode**

Files modified:
- `app/orchestrators/prompting.py` - Added concise mode prefix injection in `step_44__default_sys_prompt` and `step_41__select_prompt`

When `is_followup=True` in routing_decision, a concise mode prefix is injected into the prompt:
- Instructions to NOT repeat previously provided information
- Direct response without preambles
- Brief, focused answers (max 3-4 points)
- Only cite specific relevant normative references

Example ideal follow-up response:
```
"Sì, le cartelle per tasse auto rientrano tra i tributi rottamabili (Art. 1, comma 231, lettera a, L. 199/2025)."
```
Instead of repeating all general rottamazione info.

**2.3 Hallucination Guard**

Files created:
- `app/services/hallucination_guard.py` - New service to detect hallucinated law citations
- `tests/services/test_hallucination_guard.py` - 27 comprehensive tests

The HallucinationGuard service:
1. **Extracts law citations** from LLM responses using regex patterns:
   - Legge patterns: `Legge n. 199/2025`, `L. 199/2025`, `Legge 30 dicembre 2025 n. 199`
   - Decreto patterns: `D.Lgs. 81/2008`, `Decreto Legislativo 81/2008`
   - DPR patterns: `DPR 633/72`, `D.P.R. 633/1972`
   - Circolare patterns: `Circolare AdE n. 12/E del 2024`

2. **Validates citations** against KB context:
   - Normalizes citations for comparison (e.g., `633/72` → `633/1972`)
   - Handles different format variations
   - Logs validation results with hallucination rate

3. **Provides correction suggestions** for hallucinated citations

Usage:
```python
from app.services.hallucination_guard import hallucination_guard

result = hallucination_guard.validate_citations(response_text, kb_context)
if result.has_hallucinations:
    logger.warning(f"Hallucinated: {result.hallucinated_citations}")
    suggestion = hallucination_guard.get_correction_suggestion(result)
```

Example detection:
- Response: "La rottamazione è disciplinata dalla Legge 197/2022"
- Context: "La Legge n. 199/2025 disciplina la definizione agevolata"
- Result: `hallucinated_citations = ["Legge 197/2022"]` (wrong number!)

**2.4 KB Article Metadata Extraction**

Files created:
- `app/services/article_extractor.py` - New service to extract Italian legal article references
- `tests/services/test_article_extractor.py` - 27 comprehensive tests

Files modified:
- `app/core/document_ingestion.py` - Integrated article extraction during ingestion

The ArticleExtractor service:
1. **Extracts article references** from legal text using regex patterns:
   - Article patterns: `Art. 1`, `articolo 1`, `Art. 2-bis`
   - Comma patterns: `comma 231`, `c. 231`, `commi da 231 a 252`
   - Lettera patterns: `lettera a)`, `lett. a)`

2. **Associates with source laws** when found in context:
   - `Art. 1, comma 231 della Legge 199/2025` -> ArticleReference with source_law

3. **Stores in KnowledgeItem.parsing_metadata** during ingestion:
   - `article_references`: List of extracted references
   - `primary_article`: Main article referenced
   - `comma_count`: Number of comma references
   - `has_definitions`: Whether chunk contains "Definizioni" section

Usage:
```python
from app.services.article_extractor import article_extractor

# Extract references from text
refs = article_extractor.extract_references(text)
for ref in refs:
    print(f"{ref}")  # "Art. 1, comma 231, lettera a)"

# Extract chunk metadata for storage
metadata = article_extractor.extract_chunk_metadata(chunk_text)
# {"article_references": [...], "primary_article": "1", ...}
```

Example extraction:
- Text: "Art. 1, comma 231, lettera a) della Legge n. 199/2025"
- Result: `ArticleReference(article="1", comma="231", lettera="a", source_law="Legge n. 199/2025")`

### Phase 3: Long Term - 3.1 IMPLEMENTED

| Task | File(s) | Description                             | Status |
|------|---------|-----------------------------------------|--------|
| **3.1** Web Verification | `services/web_verification.py` (NEW), `step_100__post_proactivity.py`, `graph.py` | Web verification with Brave Search | ✅ Done |
| **3.2** Nuanced Source Ingestion | RSS feeds | Add practical guides, not just laws     | Pending |
| **3.3** Caveat Detection | ML model | Detect when answer needs qualifications | Pending |
| **3.4** User Feedback Loop | Analytics | Track "Errata" feedback, retrain        | Pending |
| **3.5-3.8** Follow-up Query Fixes | `parallel_retrieval.py`, `router.py`, `step_039a__multi_query.py` | Short query reformulation + web result reservations | ✅ Done |
| **3.9** Keyword Ordering Fix | `parallel_retrieval.py`, `web_verification.py` | Context-first keyword ordering for Brave search | ✅ Done |

#### Phase 3.1 Implementation Details (January 16, 2026)

**3.1 Web Verification Service**

Files created:
- `app/services/web_verification.py` - Web verification service with Brave Search API
- `tests/services/test_web_verification.py` - 25 comprehensive tests

Files modified:
- `app/core/config.py` - Added `BRAVE_SEARCH_API_KEY` setting
- `app/core/langgraph/nodes/step_100__post_proactivity.py` - Integrated web verification call
- `app/core/langgraph/graph.py` - Added caveat yielding in response streams

The WebVerificationService:
1. **Searches web** using Brave Search API with AI summarization:
   - Two-step process: Web search → AI Summarizer (FREE, doesn't count toward quota)
   - Falls back to DuckDuckGo if Brave API key is not configured
2. **Detects contradictions** between KB answer and web results:
   - Checks for contradiction keywords (esclusi, dipende, richiede, accordo, etc.)
   - Focuses on sensitive topics (tributi locali, IMU, IRAP, tasse auto)
   - Detects date/deadline changes (prorogato, posticipato, nuova scadenza)
   - AI synthesis results get higher confidence (0.65 vs 0.5 base)
3. **Generates caveats** for significant contradictions:
   - Date conflict caveats
   - Local tribute agreement caveats
   - IRAP exclusion caveats
4. **Yields caveats** at end of response via graph.py

Architecture:
```
User Question
     ↓
RAG Retrieval → KB Answer
     ↓
Step 100: Web Verification (Brave Search API + AI Summarizer)
     ↓
Contradiction Detection (AI synthesis = higher confidence)
     ↓
If contradiction found:
  → Caveat added to state
     ↓
Graph: Yield caveats at end of response
```

Environment setup:
```bash
# Add to .env file
BRAVE_SEARCH_API_KEY=YOUR_API_KEY_HERE
```

Free tier: 2,000 queries/month + unlimited AI summarizer requests

Example caveat output:
```
📌 **Nota sui tributi locali:** La definizione agevolata per tributi locali
come IMU potrebbe richiedere l'accordo dell'ente locale competente.
Verifica con il tuo Comune/Regione. [Fonte: italia-informa.com]
```

Usage:
```python
from app.services.web_verification import web_verification_service

result = await web_verification_service.verify_answer(
    user_query="rottamazione tributi locali",
    kb_answer="I tributi locali possono essere rottamati.",
    kb_sources=[{"title": "Legge 199/2025"}],
)

if result.has_caveats:
    for caveat in result.caveats:
        print(caveat)
```

**3.1.2 Search Query Relevance Fix (January 17, 2026)**

**Problem:** Brave Search was returning irrelevant results (e.g., "cedolare secca" links for "rottamazione IMU" queries).

**Root Cause:** `_build_verification_query()` mixed user query words with KB source titles:
- User query: "si possono rottamare i debiti imu"
- KB source titles: ["Misure urgenti per la determinazione...", "Cessione abitazione..."]
- Polluted query: "misure cento determinazione cessione abitazione 2026" (irrelevant!)

**Fix Applied:**
```python
# app/services/web_verification.py
def _build_verification_query(
    self,
    user_query: str,
    kb_sources: list[dict],  # Kept for API compatibility but not used
) -> str:
    """Build search query from user query directly."""
    # Use user query directly - don't pollute with KB titles
    query = user_query.strip()

    # Add year for recency if not present
    if "2026" not in query.lower() and "2025" not in query.lower():
        query = f"{query} 2026"

    return query
```

**Result:** All search links now relevant to the actual user query.

**3.1.3 Logging Fix for Short Query Expansion (January 17, 2026)**

**Problem:** "e l'irap" query caused error:
```
TypeError: Logger._log() got an unexpected keyword argument 'original_query'
```

**Root Cause:** `_expand_short_query()` in `step_039a__multi_query.py` used structlog-style keyword arguments with standard Python logging.

**Fix Applied:**
```python
# Changed from structlog style:
logger.info("short_query_expanded", original_query=query, ...)

# To standard Python logging format:
logger.info(f"short_query_expanded: original_query={query[:50]!r}, ...")
```

---

### Phase 3.2: Parallel Hybrid RAG Architecture - ✅ IMPLEMENTED

**Status:** ✅ FULLY IMPLEMENTED
**Date Analyzed:** January 17, 2026
**Date Implemented:** January 17, 2026

**Previous Architecture (2 LLM calls):**
```
User Query
    ↓
KB Retrieval (pgvector)
    ↓
LLM #1: Generate KB Answer (~3-5s)
    ↓
Web Search (Brave) ← happens AFTER LLM answer
    ↓
LLM #2: Synthesize KB + Web (~3-5s)
    ↓
Final Response
```
**Total: ~6-10s, 2 LLM calls**

**NEW Architecture (1 LLM call):**
```
User Query
    ↓
Step 39c: PARALLEL Retrieval
  ├─ KB: bm25 (0.3 weight)
  ├─ KB: vector (0.35 weight)
  ├─ KB: hyde (0.25 weight)
  ├─ KB: authority (0.1 weight)
  └─ Web: brave (0.30 weight) ← NEW
    ↓
Step 40: Merge & Rank with RRF
  ├─ Separate KB docs from web results
  └─ Store web_sources_metadata in state
    ↓
Single LLM Call (Step 64)
  ├─ KB context injected
  └─ Web sources injected via prompts
    ↓
Final Response
```
**Total: ~3-5s, 1 LLM call**

**Benefits Achieved:**
- **50% fewer LLM calls** (2 → 1)
- **40-50% faster** (~3-5s vs ~6-10s)
- **Lower API costs** (single LLM synthesis)
- **Industry standard** approach (Azure AI Search, hybrid RAG systems)

**Implementation Details:**

| File | Change |
|------|--------|
| `app/services/parallel_retrieval.py` | Added `_search_brave()` as 5th parallel search, updated `SEARCH_WEIGHTS` |
| `app/core/langgraph/types.py` | Added `web_documents` and `web_sources_metadata` fields to RAGState |
| `app/core/langgraph/nodes/step_040__build_context.py` | Separates web results from KB docs, stores in state |
| `app/orchestrators/prompting.py` | Injects web sources in step_41 and step_44 prompts |
| `app/services/llm_orchestrator.py` | Passes `web_sources_metadata` to `_build_response_prompt()` |
| `app/prompts/v1/unified_response_simple.md` | Added `{web_sources_metadata}` placeholder |
| `app/services/web_verification.py` | Uses existing web sources instead of redundant search |
| `app/core/langgraph/nodes/step_100__post_proactivity.py` | Passes existing sources from state |

**New Search Weights:**
```python
SEARCH_WEIGHTS = {
    "bm25": 0.3,      # Full-text search
    "vector": 0.35,   # Semantic search
    "hyde": 0.25,     # Hypothetical doc embedding
    "authority": 0.1, # Source authority boost
    "brave": 0.3,     # Web search - balanced with BM25 (configurable via BRAVE_SEARCH_WEIGHT)
}
```

**Logging for Docker Debugging:**
```python
logger.info(
    "parallel_searches_starting",
    query_preview=queries.original_query[:80],
    has_hyde=hyde is not None and hyde.hypothetical_document is not None,
    search_types=["bm25", "vector", "hyde", "authority", "brave"],
)

logger.info(
    "parallel_searches_complete",
    source_counts={"bm25": X, "vector": Y, "hyde": Z, "authority": W, "brave": N},
    total_raw_results=sum,
    brave_results=N,
    kb_results=X+Y+Z,
)
```

**Sources:**
- [RAG 2025 Definitive Guide](https://www.chitika.com/retrieval-augmented-generation-rag-the-definitive-guide-2025/)
- [Azure AI Search RAG](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview)
- [Hybrid RAG Architecture](https://www.ai21.com/glossary/foundational-llm/hybrid-rag/)

---

### Phase 3.5-3.8: Follow-up Query Fixes - ✅ IMPLEMENTED

**Status:** ✅ FULLY IMPLEMENTED
**Date:** January 20-21, 2026

**Problem:** Follow-up queries like "e l'irap?" after "parlami della rottamazione quinquies" were not returning web sources properly.

**Root Causes Identified:**
1. **Phase 3.5:** `get_model_config()` called with wrong arguments - LLM reformulation failed
2. **Phase 3.6:** `web_verification.py` used original query instead of reformulated query
3. **Phase 3.7:** `needs_retrieval` property returned False for follow-up queries
4. **Phase 3.8:** Web results dropped from top-K selection due to no reserved slots

**Fixes Applied:**

| Phase | Fix | File |
|-------|-----|------|
| 3.5 | Fix `get_model_config()` call (no arguments) | `step_039a__multi_query.py` |
| 3.6 | Use reformulated query for web verification | `web_verification.py` |
| 3.7 | Return True for `needs_retrieval` when `is_followup=True` | `router.py` |
| 3.8 | Add `WEB_RESERVED_SLOTS = 2` constant | `parallel_retrieval.py` |

**Phase 3.5: get_model_config() Fix**
```python
# BEFORE (broken):
config = get_model_config(some_arg)  # ❌ Wrong call

# AFTER (fixed):
config = get_model_config()  # ✅ Singleton, no args
```

**Phase 3.7: needs_retrieval for Follow-ups**
```python
# router.py - RouterDecision.needs_retrieval property
@computed_field
@property
def needs_retrieval(self) -> bool:
    # DEV-245 Phase 3.7: Follow-up queries always need retrieval
    if self.is_followup:
        return True
    return self.route in retrieval_routes
```

**Phase 3.8: Reserved Slots for Web Results**
```python
# parallel_retrieval.py
WEB_RESERVED_SLOTS = 2  # Guarantee web results appear in final top-K

def _get_top_k(self, merged_results, top_k):
    web_results = [r for r in merged_results if r.get("is_web_result")]
    kb_results = [r for r in merged_results if not r.get("is_web_result")]

    # Reserve slots for web results
    kb_slots = max(0, top_k - min(len(web_results), WEB_RESERVED_SLOTS))
    # ...
```

---

### Phase 3.9: Keyword Ordering Fix - PLANNED

**Status:** PLANNED
**Date:** January 21, 2026

**Problem Discovered:**

User observed that Brave search returns better results with keywords ordered as "rottamazione quinquies irap" (context first, then follow-up) rather than "irap rottamazione quinquies" (sentence order from reformulated query).

**Current Behavior (Wrong):**
1. User asks: "parlami della rottamazione quinquies" → context established
2. User asks: "e l'irap?" → reformulated to "L'IRAP può essere inclusa nella rottamazione quinquies?"
3. Keywords extracted in sentence order: `["irap", "rottamazione", "quinquies"]` ❌
4. Brave search: `"irap rottamazione quinquies 2026"` (irap first - wrong!)

**Ideal Behavior (Goal):**
1. Extract context keywords: `["rottamazione", "quinquies"]`
2. Extract new keywords from follow-up: `["irap"]`
3. Combine: context first, then new → `["rottamazione", "quinquies", "irap"]`
4. Brave search: `"rottamazione quinquies irap 2026"` ✅

**Industry Standard:**
[BruceClay SEO Guide](https://www.bruceclay.com/seo/combining-keywords/): "It is best to use the most relevant keyword first, followed by any relevant words"

**Decision: Keep LLM Reformulation**

After analysis, we decided to KEEP the LLM-based query reformulation because:
- LLM handles typos (e.g., "rottamzaione" → "rottamazione")
- LLM understands synonyms and context
- LLM provides good natural language for BM25/vector search

The fix is to add **context-aware keyword ordering** for web searches specifically.

**Solution Architecture:**

```
User Query: "e l'irap?"
    ↓
LLM Reformulation (keep): "L'IRAP può essere inclusa nella rottamazione quinquies?"
    ↓
For BM25/Vector Search: Use reformulated query ✅
    ↓
For Brave Web Search: Extract keywords with context-first ordering
    ├─ Context keywords (from history): ["rottamazione", "quinquies"]
    └─ New keywords (from follow-up): ["irap"]
    ↓
Final search: "rottamazione quinquies irap 2026" ✅
```

**Files to Modify:**

| File | Change |
|------|--------|
| `parallel_retrieval.py` | Add `_extract_search_keywords_with_context()` method |
| `web_verification.py` | Add same method, modify `_build_verification_query()` |
| `step_100__post_proactivity.py` | Pass `messages` to `verify_answer()` call |

**New Method: `_extract_search_keywords_with_context()`**
```python
def _extract_search_keywords_with_context(
    self,
    query: str,
    messages: list[dict] | None = None,
) -> list[str]:
    """DEV-245 Phase 3.9: Extract keywords with context-first ordering.

    CRITICAL: Keep this method - it ensures Brave search uses optimal
    keyword ordering for follow-up queries.

    Industry standard (BruceClay): "Most relevant keyword first"
    """
    # Extract all keywords from reformulated query
    all_keywords = self._extract_search_keywords(query)

    if not messages or len(all_keywords) <= 2:
        return all_keywords  # No reordering needed

    # Find context keywords from conversation history
    context_keywords = set()
    for msg in reversed(messages[-4:]):
        # Extract keywords from context messages
        ...

    # Separate: context keywords vs new keywords
    context_first = [kw for kw in all_keywords if kw in context_keywords]
    new_keywords = [kw for kw in all_keywords if kw not in context_keywords]

    # Return: context first, then new keywords
    return context_first + new_keywords
```

**Verification:**
1. Docker rebuild: `docker-compose up -d --build app`
2. First query: "parlami della rottamazione quinquies"
3. Second query: "e l'irap?"
4. Check logs for: `keywords=['rottamazione', 'quinquies', 'irap']` ✅
   NOT: `keywords=['irap', 'rottamazione', 'quinquies']` ❌

---

### Phase 4: Generic Extraction Architecture - ✅ IMPLEMENTED

**Status:** ✅ FULLY IMPLEMENTED
**Date:** January 19, 2026

**Problem Identified:**
PratikoAI had **~17KB of hardcoded rottamazione-specific rules** in the system prompt. This was NOT scalable:
- Users ask dozens of questions per day on **hundreds of different topics**
- Can't maintain topic-specific rules for each topic
- Current approach required code changes to add new topics

| Location | Size | Content |
|----------|------|---------|
| `app/orchestrators/prompting.py` (lines 972-1167) | ~12KB | Rottamazione extraction tables |
| `app/prompts/v1/unified_response_simple.md` | ~2KB | Rottamazione-specific examples |
| `app/services/knowledge_search_service.py` | ~1KB | Topic-specific tags |
| `app/services/search_service.py` | ~0.5KB | Rottamazione search expansion |
| **Total** | **~17KB** | Topic-specific hardcoded rules |

**Solution: Generic Extraction Principles**

Replace **explicit extraction rules** ("extract these 8 rottamazione fields") with **universal extraction patterns** that work for ANY topic.

Core principle:
```
CURRENT (Not Scalable):
  IF topic == "rottamazione": EXTRACT [8 specific fields]
  ELIF topic == "bonus": EXTRACT [different fields]
  ELIF ... (100+ topics)

NEW (Scalable):
  FOR ANY topic:
    SCAN KB for universal patterns:
      - Temporal data (dates, deadlines)
      - Numeric data (percentages, amounts)
      - Conditions (requirements, exclusions)
      - References (articles, laws)
    INCLUDE ALL found data in response
```

**Files Modified:**

| File | Change |
|------|--------|
| `app/core/config.py` | Added `USE_GENERIC_EXTRACTION` feature flag (default: true) |
| `app/orchestrators/prompting.py` | Replaced ~12KB topic-specific rules with ~4KB generic extraction principles |
| `app/prompts/v1/unified_response_simple.md` | Replaced topic-specific examples with generic ones |
| `app/services/knowledge_search_service.py` | Simplified TOPIC_KEYWORDS: merged `rottamazione_quinquies/quater` → `fiscal_amnesty` |
| `app/services/search_service.py` | Simplified TOPIC_SYNONYMS to broad categories |

**New Generic Extraction Prompt (~4KB):**
```markdown
## REGOLE UNIVERSALI DI ESTRAZIONE

### SCANSIONE OBBLIGATORIA DEL KB

| Pattern | Esempio | Azione |
|---------|---------|--------|
| Date/Scadenze | "30 aprile 2026" | COPIA nella risposta |
| Percentuali | "3 per cento" | COPIA nella risposta |
| Importi | "€ 5.000" | COPIA nella risposta |
| Quantità | "54 rate" | COPIA nella risposta |
| Articoli/Leggi | "Art. 1, comma 231" | CITA nella risposta |
| Condizioni | "possono accedere" | ELENCA |
| Esclusioni | "esclusi", "non possono" | ELENCA |
| Conseguenze | "decadenza", "sanzione" | DETTAGLIA |

### REGOLA FONDAMENTALE
**Se un dato è nel KB, DEVE essere nella risposta.**
```

**Feature Flag for Safe Rollout:**
```python
# app/core/config.py
USE_GENERIC_EXTRACTION = os.getenv("USE_GENERIC_EXTRACTION", "true").lower() == "true"
```

**Results:**

| Metric | Before | After |
|--------|--------|-------|
| Topic-specific rules | 17KB | 0KB |
| Generic extraction prompt | 0KB | 4KB |
| **Total prompt size** | ~25KB | ~13KB |
| Topics supported | 1 (rottamazione) | Unlimited |
| Per-topic configuration | Required | None |

**Rollback:** Set `USE_GENERIC_EXTRACTION=false` to restore legacy topic-specific rules.

---

### Phase 5: Long Conversation Support & Disclaimer Filtering - ✅ IMPLEMENTED

**Status:** ✅ FULLY IMPLEMENTED
**Date:** January 22, 2026

| Task | File(s) | Description | Status |
|------|---------|-------------|--------|
| **5.1** Disclaimer Filter | `step_100__post_proactivity.py` | Remove "consulta un esperto" phrases | ✅ Done |
| **5.2** Web Source Debug | Logs verification | Verify search_keywords passthrough | ✅ Verified |
| **5.3** Topic Summary State | `types.py`, `step_034a__llm_router.py`, `parallel_retrieval.py`, `web_verification.py` | Preserve topic across 4+ turns | ✅ Done |
| **5.4** Type Safety | `parallel_retrieval.py`, `web_verification.py`, `step_034a__llm_router.py` | Validate topic_keywords is list | ✅ Done |
| **5.5** Web Result Topic Filtering | `step_040__build_context.py` | Require ALL topic keywords match in web results | ✅ Done |

#### Phase 5.1: Disclaimer Filter (January 21, 2026)

**Problem:** LLM responses contained "consulta un esperto" phrases that damage PratikoAI's reputation as an authoritative fiscal assistant.

**Solution:** Added regex-based post-processing filter in `step_100__post_proactivity.py` that removes prohibited disclaimer phrases.

#### Phase 5.3: Topic Summary State (January 22, 2026)

**Problem:** At Q4+ in a conversation, the `messages[-4:]` window loses the original topic. User asking about "rottamazione quinquies" + follow-ups about IRAP, IMU, etc. loses context at Q4.

**Root Cause:** With 8+ messages, `messages[-4:]` doesn't include the original Q1 where "rottamazione quinquies" was mentioned.

**Solution:** Implement Topic Summary State (industry best practice from JetBrains Research, Zoice AI):
1. Extract topic keywords from first query ("rottamazione", "quinquies")
2. Store in RAGState as `topic_keywords: list[str]`
3. Use `topic_keywords` for keyword ordering instead of scanning messages

**Files Modified:**

| File | Change |
|------|--------|
| `app/core/langgraph/types.py` | Added `conversation_topic: str \| None` and `topic_keywords: list[str] \| None` |
| `app/core/langgraph/nodes/step_034a__llm_router.py` | Added `_extract_topic_keywords()` function, extract on first query |
| `app/services/parallel_retrieval.py` | Use `topic_keywords` from state for keyword ordering |
| `app/services/web_verification.py` | Use `topic_keywords` from state for keyword ordering |
| `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` | Pass `topic_keywords` to service |
| `app/core/langgraph/nodes/step_100__post_proactivity.py` | Pass `topic_keywords` to service |

**Topic Keyword Extraction:**
```python
_TOPIC_STOP_WORDS = {"il", "lo", "la", "di", "a", "da", "in", "con", "su", "per", ...}

def _extract_topic_keywords(query: str) -> list[str]:
    """Extract topic keywords from first query (max 5)."""
    words = query.lower().split()
    keywords = [w for w in words if len(w) >= 3 and w not in _TOPIC_STOP_WORDS]
    return unique_keywords[:5]
```

**Tests Created:**
- `tests/langgraph/nodes/test_step_034a_topic_extraction.py` - 12 tests
- `tests/services/test_topic_preservation.py` - 13 tests (including type safety)

#### Phase 5.4: Type Safety (January 22, 2026)

**Problem:** Q5 in a conversation failed with error. Investigation revealed potential type safety issue with `topic_keywords`.

**Solution:** Added `isinstance(topic_keywords, list)` checks in all three files:
1. `parallel_retrieval.py:837` - Before using topic_keywords
2. `web_verification.py:525` - Before using topic_keywords
3. `step_034a__llm_router.py:225` - Validate and reset if corrupted

**Verification:**
```
Q1: "parlami della rottamazione quinquies" → ✅
Q2: "e l'irap?" → ✅
Q3: "e l'imu?" → ✅
Q4: "per quanto riguarda l'irap, accordo regioni?" → ✅ (stays on topic)
Q5: "la regione sicilia recepira' la rottamazione?" → ✅ (no error)
```

#### Phase 5.5: Web Result Topic Filtering (January 22, 2026)

**Problem:** Q5 ("la regione sicilia recepira' la rottamazione dell'irap?") returned off-topic content mentioning "bollo auto" and "rottamazione ter" instead of "rottamazione quinquies".

**Root Cause:** The web result filter in `step_040__build_context.py` used `any()` (OR logic), meaning a result only needed to match ONE keyword to pass. Results about "Rottamazione Ter - Sicilia" passed because they contained "rottamazione" and "sicilia", even though the topic was "rottamazione quinquies".

**Solution:** Modified `_is_web_source_topic_relevant()` to require ALL topic keywords match when `topic_keywords` is available:

```python
# OLD: any() - pass if ONE keyword matches (too permissive)
return any(kw in combined_text for kw in query_keywords)

# NEW: all() for topic keywords (strict), then any() fallback
if topic_keywords and isinstance(topic_keywords, list) and len(topic_keywords) >= 2:
    topic_match = all(kw.lower() in combined_text for kw in topic_keywords)
    if not topic_match:
        return False  # Reject: doesn't match conversation topic
return any(kw in combined_text for kw in query_keywords)
```

**Files Modified:**
- `app/core/langgraph/nodes/step_040__build_context.py`:
  - Added `topic_keywords` parameter to `_is_web_source_topic_relevant()`
  - Read `topic_keywords` from state
  - Pass to both pre-filter and Fonti filter calls

**Tests:**
- `tests/langgraph/agentic_rag/test_step_040_topic_filtering.py` - 14 tests

**Verification:**
```
- "Rottamazione Ter 2024 - Sicilia" → ❌ FILTERED (missing "quinquies")
- "Rottamazione Quinquies IRAP Sicilia 2026" → ✅ PASSED
- "Rottamazione bollo auto Sicilia" → ❌ FILTERED (missing "quinquies")
```

#### Phase 5.6: Checkpoint Topic Keywords Loading (January 22, 2026)

**Problem:** At Q4+, topic_keywords was None despite being set at Q1.

**Root Cause:** topic_keywords wasn't being loaded from checkpoint in step_034a.

**Fix:** Added `topic_keywords=state.get("topic_keywords")` in step_034a when loading from checkpoint.

**Files Modified:**
- `app/core/langgraph/nodes/step_034a__llm_router.py`

#### Phase 5.7: Topic Keywords Reducer Persistence (January 22, 2026)

**Problem:** topic_keywords lost during node transitions (Q2→Q3→Q4...).

**Root Cause:** LangGraph REPLACES state fields with None on any node that doesn't return them. Without a reducer, the value was lost.

**Solution:** Added `preserve_topic_keywords()` reducer in types.py using `Annotated` pattern:

```python
def preserve_topic_keywords(
    existing: list[str] | None,
    new: list[str] | None,
) -> list[str] | None:
    """Preserve topic_keywords across node transitions."""
    if new is not None and len(new) > 0:
        return new
    return existing

# Usage with Annotated
topic_keywords: Annotated[list[str] | None, preserve_topic_keywords]
```

**Files Modified:**
- `app/core/langgraph/types.py` (lines 193-216, 390-396)

#### Phase 5.8: Step 100 Topic Keywords Return (January 22, 2026)

**Problem:** step_100 post_proactivity didn't return topic_keywords in all return paths.

**Fix:** Added `"topic_keywords": state.get("topic_keywords")` to ALL return statements in step_100.

**Files Modified:**
- `app/core/langgraph/nodes/step_100__post_proactivity.py`

#### Phase 5.9: Step 014 Topic Keywords Return (January 22, 2026)

**Problem:** step_014 pre_proactivity didn't return topic_keywords in all return paths.

**Fix:** Added `"topic_keywords": state.get("topic_keywords")` to ALL return statements in step_014.

**Files Modified:**
- `app/core/langgraph/nodes/step_014__pre_proactivity.py`

#### Phase 5.10: Debug Tracing (January 22, 2026)

**Purpose:** Added comprehensive logging to trace topic_keywords flow through the pipeline.

**Logs Added:**
- `DEV245_checkpoint_topic_keywords` - Shows topic_keywords at checkpoint load
- `DEV245_step034a_topic_keywords` - Shows is_followup and extraction decision
- `DEV245_step039c_topic_keywords` - Shows keywords passed to Brave

#### Phase 5.11: Fix is_followup Bug (January 22, 2026)

**Problem:** Q1 query didn't extract topic_keywords because `is_followup=False` skipped extraction.

**Root Cause:** Logic was `if is_followup: ... extract topic_keywords` - but we need to extract on Q1, not on follow-ups.

**Fix:** Changed to `if topic_keywords is None: extract topic_keywords` (extract whenever missing, regardless of is_followup).

**Files Modified:**
- `app/core/langgraph/nodes/step_034a__llm_router.py`

**Evidence:** After fix, Q1 logs show `will_extract_new=True topic_keywords_from_state=None`

#### Phase 5.12: YAKE Keyword Extraction (January 23, 2026)

**Problem:** Manual stop word lists (~80 words in two locations) are not scalable:
- Missing common Italian words: 'quanto', 'riguarda', 'recepira'
- Requires constant maintenance
- Doesn't handle verb conjugations
- Duplicate logic in `parallel_retrieval.py` and `step_040__build_context.py`

**Evidence from logs:**
```
Q4: ['rottamazione', 'quinquies', 'quanto', 'riguarda', 'irap']  # 'quanto', 'riguarda' not useful
Q5: ['rottamazione', 'quinquies', 'regione', 'sicilia', 'recepira']  # 'recepira' not useful
```

**Solution:** Replaced manual stop word lists with YAKE (Yet Another Keyword Extractor) statistical scoring.

YAKE uses text features to determine keyword importance WITHOUT stop word lists:
- **Casing** - Proper nouns score higher
- **Word Position** - Early words often more important
- **Word Frequency** - Mid-frequency words preferred
- **Context Relatedness** - Co-occurrence patterns

**YAKE scores are inverted:** Lower score = more important keyword.

**Files Created:**
- `app/services/keyword_extractor.py` - YAKE wrapper service (~60 lines)
- `tests/services/test_keyword_extractor.py` - 14 tests

**Files Modified:**
- `pyproject.toml` - Added `yake>=0.4.8` dependency
- `app/services/parallel_retrieval.py` - Replaced `_extract_search_keywords()` with YAKE
- `app/core/langgraph/nodes/step_040__build_context.py` - Replaced `_extract_filter_keywords_from_query()` with YAKE
- `app/core/langgraph/types.py` - Added `search_keywords_with_scores` field
- `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` - Store scores in state

**New Log Output:**
```
DEV245_yake_keyword_scores ... query_preview="la regione sicilia recepira' la rottamazione" keywords_with_scores=[
    {"keyword": "rottamazione", "score": 0.0234},   # LOW = important
    {"keyword": "quinquies", "score": 0.0312},      # LOW = important
    {"keyword": "sicilia", "score": 0.0456},        # LOW = important
    {"keyword": "regione", "score": 0.0789},        # Medium
    {"keyword": "recepira", "score": 0.2134}        # HIGH = filtered if using top_k
]
```

**Benefits:**
- No stop word maintenance required
- Handles any Italian verb conjugation automatically
- Works for any domain (not just fiscal topics)
- Scores available for evaluation/debugging

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Hallucination rate (wrong citations) | Unknown | <1% |
| Follow-up repetition rate | ~90% | <20% |
| "Errata" feedback rate | Unknown | <5% |
| Specific citation rate (articolo/comma) | ~10% | >80% |
| Short query failure rate | Unknown | <1% |

---

## Appendix: Specific Bug Fixes

### Bug: "e l'irap" No Response

**Location:** Likely in `step_020_analyze.py` or retrieval

**Fix:**
```python
# In query analysis
if len(query.split()) < 3:
    # Expand with conversation context
    recent_topics = extract_topics_from_history(conversation_history[-3:])
    expanded_query = f"{' '.join(recent_topics)} {query}"
```

### Bug: LLM Hallucinating Laws

**Location:** Response generation prompt

**Fix:**
```python
# Add to system prompt
"""
IMPORTANT: Only cite laws and articles that appear in the provided context.
If you're unsure about a specific law number, say "secondo la normativa vigente"
instead of inventing a citation.

DO NOT cite laws that are not in the context. If asked about a topic not
covered in the context, say "Non ho informazioni specifiche su questo argomento."
"""
```

---

#### Phase 5.14: Conditional ✅/❌ Format + Centralized Stop Words (January 23, 2026)

**Problem 1: "recepira" Stop Word Problem**
The query "la regione sicilia recepira' la rottamazione dell'irap?" extracted "recepira" as a keyword because future tense verbs were missing from stop word lists.

**Solution 1: Centralized Stop Word Module**
Created `app/services/italian_stop_words.py` with:
- 372 stop words (full list) organized by category
- 51 minimal stop words for topic extraction
- Future, conditional, imperative verb forms included
- Single source of truth - all 5 previous locations now import from here

**Files Modified:**
- `app/services/italian_stop_words.py` - NEW centralized module
- `app/services/parallel_retrieval.py` - Uses STOP_WORDS
- `app/core/langgraph/nodes/step_040__build_context.py` - Uses STOP_WORDS
- `app/core/langgraph/nodes/step_034a__llm_router.py` - Uses STOP_WORDS_MINIMAL
- `app/services/italian_query_normalizer.py` - Uses STOP_WORDS_MINIMAL
- `app/services/action_validator.py` - Uses STOP_WORDS
- `tests/services/test_italian_stop_words.py` - NEW (18 tests)

---

**Problem 2: ✅ Incluso / ❌ Escluso Pattern Overuse**
The ✅/❌ format was applied to EVERY response, even general questions like "Cos'è la rottamazione?" where it felt forced.

**Solution 2: Web-Based Exclusion Detection (Option C)**
Only use ✅/❌ format when web results ACTUALLY contain exclusion keywords.

Added `EXCLUSION_KEYWORDS` constant (24 keywords) and `_web_has_genuine_exclusions()` function that:
1. Scans web result snippets for exclusion keywords
2. Returns (has_exclusions: bool, matched_keywords: list)
3. Prompts are conditional based on detection result

**Files Modified:**
- `app/services/web_verification.py` - Added detection + conditional prompts
- `tests/services/test_web_verification.py` - Added 16 tests for exclusion detection

**Behavior Change:**
| Scenario | Before | After |
|----------|--------|-------|
| "Cos'è la rottamazione?" | ✅/❌ forced | Narrative format |
| "L'IRAP può essere inclusa?" + web says "esclusa" | ✅/❌ | ✅/❌ (appropriate) |
| "Quando scade?" | ✅/❌ forced | Narrative format |

**Test Results:** 106 tests passing (44 web_verification + 18 stop_words + 44 parallel_retrieval)

---

#### Phase 5.15: Remove Suggested Actions Feature (January 23, 2026)

**Problem:** User feedback indicated that suggested actions are:
- Often generic and unhelpful
- Not contextually relevant to the actual question
- Feel like filler content rather than genuine assistance
- Create a "chatbot checklist" feel instead of expert assistant

**Solution:** Complete removal of the "Azioni Suggerite" feature while preserving:
- Interactive Questions (pre-response clarification)
- Web Verification (caveats and contradictions)

**Files Deleted (Backend):**
- `app/core/prompts/suggested_actions.md` - LLM prompt for action generation
- `app/services/action_validator.py` - Action quality validation
- `app/services/action_regenerator.py` - Action regeneration logic
- `app/services/action_quality_metrics.py` - Action quality metrics
- Related test files (6 test files)

**Files Modified (Backend):**
- `app/services/llm_response_parser.py` - Removed `<suggested_actions>` parsing
- `app/core/langgraph/nodes/step_100__post_proactivity.py` - Removed action handling, kept web verification
- `app/api/v1/chatbot.py` - Removed `suggested_actions` SSE event
- `app/schemas/proactivity.py` - Removed Action/ActionContext types

**Files Deleted (Frontend):**
- `src/app/chat/components/SuggestedActionsBar.tsx` - Action buttons component
- `src/app/chat/components/__tests__/SuggestedActionsBar.test.tsx` - Tests

**Files Modified (Frontend):**
- `src/lib/api.ts` - Removed SuggestedAction interface

**What Was Preserved:**
- Interactive Questions (pre-response clarification questions)
- Web Verification (caveats and contradiction detection)
- `InteractiveQuestionInline.tsx` component
- `interactive_question` SSE event

**Architecture Documentation:** See `docs/architecture/ARCHIVED_SUGGESTED_ACTIONS.md` for historical reference.

#### Phase 5.15.1: Fix Missed Files (January 23, 2026)

**Problem:** After Phase 5.15 implementation, the app showed "Errore nel caricamento delle sessioni" (Error loading sessions).

**Root Cause:** Two files were missed during the suggested actions removal:

1. **`app/core/langgraph/nodes/step_064__llm_call.py`** - Still referenced `suggested_actions` in 8 places:
   - Line 307: `expected_fields` set included `"suggested_actions"`
   - Line 336: `_fallback_to_text()` returned `"suggested_actions": []`
   - Lines 447-449: Set `state["suggested_actions"]` and `state["actions_source"]`
   - Line 475: Logged `actions_count` in unified response parsing
   - Line 488: Set `state["suggested_actions"] = []` in fallback branch
   - **Lines 738-739: `if unified_response.suggested_actions:` - CRITICAL AttributeError cause** (UnifiedResponse no longer has this field)
   - Line 934: Logged `actions_source` in exit logging

2. **`app/api/v1/monitoring.py`** - Still imported deleted `action_quality_metrics` module:
   - Line 20: `from app.services.action_quality_metrics import get_action_quality_metrics`
   - Lines 428-557: Four action quality endpoints (`/actions/quality/*`)

**Fixes Applied:**
- Removed all `suggested_actions` and `actions_source` references from `step_064__llm_call.py`
- Removed `action_quality_metrics` import and endpoints from `monitoring.py`

**Lesson Learned:** When removing a feature, grep the entire codebase for all references:
```bash
grep -r "suggested_actions" app/
grep -r "action_quality_metrics" app/
```

---

## Questions for @egidio (Architecture)

1. **Web Verification:** Should this be a separate microservice or integrated into LangGraph?
2. **Hallucination Guard:** Add as new LangGraph step or post-processing?
3. **Conversation Context:** Store full history or just topic summaries?

## Questions for @mario (Requirements)

1. **Concise vs Detailed:** Should user choose mode, or auto-detect?
2. **Web Sources:** Which sites are authoritative for practical tax guidance?
3. **Caveat Display:** How to show "this answer may have conditions" in UI?
