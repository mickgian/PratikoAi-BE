# DEV-245: Response Quality Improvement Plan

**Created:** January 16, 2026
**Status:** PHASE 1 IMPLEMENTED
**Priority:** CRITICAL
**Last Updated:** January 16, 2026

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

### Phase 2: Medium Term (2-4 weeks)

| Task | File(s) | Description |
|------|---------|-------------|
| **2.1** Follow-up Detection | `step_020_analyze.py` | Detect follow-up questions, set flag |
| **2.2** Concise Mode | `step_070_generate.py` | If follow-up, use concise prompt template |
| **2.3** Hallucination Guard | `step_075_validate.py` (NEW) | Validate cited laws exist in context |
| **2.4** KB Article Metadata | `document_ingestion.py` | Extract articolo/comma structure during ingestion |

### Phase 3: Long Term (1-2 months)

| Task | File(s) | Description |
|------|---------|-------------|
| **3.1** Web Verification | `services/web_verification.py` (NEW) | Search web for contradictions after RAG |
| **3.2** Nuanced Source Ingestion | RSS feeds | Add practical guides, not just laws |
| **3.3** Caveat Detection | ML model | Detect when answer needs qualifications |
| **3.4** User Feedback Loop | Analytics | Track "Errata" feedback, retrain |

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

## Questions for @egidio (Architecture)

1. **Web Verification:** Should this be a separate microservice or integrated into LangGraph?
2. **Hallucination Guard:** Add as new LangGraph step or post-processing?
3. **Conversation Context:** Store full history or just topic summaries?

## Questions for @mario (Requirements)

1. **Concise vs Detailed:** Should user choose mode, or auto-detect?
2. **Web Sources:** Which sites are authoritative for practical tax guidance?
3. **Caveat Display:** How to show "this answer may have conditions" in UI?
