# DEV-242: Response Quality & Completeness Improvement - Summary

**Issue:** GitHub #975
**Status:** Phase 22-32 ✅ | Phase 29A 🔴 Pending
**Started:** January 8, 2026
**Last Updated:** January 12, 2026

---

## Problem Statement

PratikoAI responses lack specific details compared to competitors (laleggepertutti.it).

**Example Query:** "Parlami della rottamazione quinquies"

| Detail | PratikoAI (Before) | Expected |
|--------|-------------------|----------|
| Law reference | ✅ L. 199/2025 | ✅ |
| 54 installments/9 years | ✅ | ✅ |
| **Application deadline** | ❌ Missing | **30 aprile 2026** |
| **First payment date** | ❌ Missing | **31 luglio 2026** |
| **3% annual interest** | ❌ Missing | ✅ |
| **Non-payment consequences** | ❌ Missing | 2 missed = forfeiture |

---

## Root Cause Analysis

### Finding 1: KB Content is NOT the Issue

The Knowledge Base CONTAINS all the details in Doc 2463 (Gazzetta Ufficiale, Legge 199/2025):

| Chunk ID | Content | Details |
|----------|---------|---------|
| 9537 | "31 luglio 2026...pagamento...rata" | First payment date |
| 9538 | "interessi al tasso..." | Interest rate info |
| 9539 | "30 aprile 2026...dichiarazione" | Application deadline |
| 9540 | "decadenza...scadenza" | Consequences |
| 9541 | "rata...pagamento...estinzione" | Payment terms |
| 9542 | "30 giugno 2026...versamenti" | Communication date |

### Finding 2: Wrong Document Prioritized

Doc 2080 (MEF summary, 7KB) was ranking higher than Doc 2463 (full law, 450KB) because:
- BM25 term density favors shorter summaries
- Authority boost was only 1.3x (insufficient)

### Finding 3: Authority Boost Field Mapping Bug

The `source` field was stored in `metadata["source"]` but `_apply_boosts()` read from `doc.get("source")` which returned empty string. SOURCE_AUTHORITY boosts were NOT being applied.

### Finding 4: Wrong Chunks Retrieved (Current Issue)

Even after fixing authority boost, the **wrong chunks** from Doc 2463 are retrieved. Chunks 9537-9542 contain:
- ✅ "pagamento", "rata", "versamento", "dichiarazione", "decadenza", "scadenza"
- ❌ "pace fiscale", "rottamazione", "definizione agevolata" (missing!)

BM25 search for "rottamazione quinquies pace fiscale" doesn't match these chunks.

---

## Completed Changes

### Phase 8-14: Initial Fixes (Completed Earlier)
- FTS ranking improvements
- Prompts and schemas updates
- GPT-4o for all contexts
- LEFT() truncation increase
- Version-specific topics

### Phase 15: FTS Synonym Fix (Band-aid)
**File:** `app/services/search_service.py`

Added "pace fiscale", "pacificazione" to TOPIC_SYNONYMS for "rottamazione quinquies".

### Phase 16A: Semantic Expansions
**File:** `app/services/multi_query_generator.py`

Added `semantic_expansions` field to LLM query generation:
```python
"semantic_expansions": ["pace fiscale", "pacificazione fiscale", "definizione agevolata"]
```

### Phase 17: Increased GERARCHIA_FONTI Boosts
**File:** `app/services/parallel_retrieval.py` (lines 38-47)

```python
GERARCHIA_FONTI = {
    "legge": 1.8,      # Was 1.3
    "decreto": 1.6,    # Was 1.25
    "circolare": 1.3,  # Was 1.15
    "risoluzione": 1.2,# Was 1.1
    "interpello": 1.1, # Was 1.05
    "faq": 1.0,
    "guida": 0.8,      # Was 0.95 - penalty for summaries
}
```

### Phase 18: Added SOURCE_AUTHORITY Dict
**File:** `app/services/parallel_retrieval.py` (lines 50-58)

```python
SOURCE_AUTHORITY = {
    "gazzetta_ufficiale": 1.3,
    "agenzia_entrate": 1.2,
    "inps": 1.2,
    "corte_cassazione": 1.15,
    "ministero_economia_documenti": 0.9,  # Summaries penalized
    "ministero_lavoro_news": 0.9,
}
```

### Phase 19: Increased max_tokens
**File:** `app/core/llm/model_config.py` (line 56)

```python
"max_tokens": 6000  # Was 4000
```

### Phase 20: Added COMPLETEZZA OBBLIGATORIA Prompt
**File:** `app/prompts/v1/unified_response_simple.md` (lines 154-179)

Added section requiring exhaustive detail extraction from KB.

### Phase 21: Increased Retrieval Depth
**File:** `app/core/config.py` (lines 477-480)

```python
HYBRID_K_FTS = 30   # Was 20
HYBRID_K_VEC = 30   # Was 20
CONTEXT_TOP_K = 20  # Was 14
```

### Phase 22: Fixed Source Field Mapping Bug ✅
**File:** `app/services/parallel_retrieval.py` (line 400)

```python
doc = {
    "document_id": str(result.knowledge_item_id or result.id),
    "content": result.content or "",
    "score": result.rank_score,
    "source_type": result.category or "",
    "source": result.source or "",  # DEV-242 Phase 22: Added for SOURCE_AUTHORITY matching
    ...
}
```

---

## Phase 23: Fixed Wrong Chunks Retrieved ✅

### Problem
Authority boosts ARE now applied (2.34x for Gazzetta laws), but BM25 still retrieves wrong chunks from Doc 2463 because chunks with dates don't contain "pace fiscale" or "rottamazione".

### Solution Implemented
**File:** `app/services/multi_query_generator.py` (lines 93-113)

Updated semantic_expansions example to include deadline-related terms:
```python
"rottamazione quinquies" → [
    "pace fiscale", "pacificazione fiscale", "definizione agevolata",
    "pagamento", "rata", "dichiarazione", "versamento", "decadenza", "scadenza"
]
```

Added general instruction (DEV-242 Phase 23):
```
REGOLA AGGIUNTIVA (DEV-242 Phase 23): Per domande su normative/procedure, INCLUDI SEMPRE:
- "pagamento", "rata", "versamento" (per trovare modalità di pagamento)
- "dichiarazione", "scadenza", "termine" (per trovare tempistiche)
- "decadenza", "sanzione" (per trovare conseguenze)
Questi termini aiutano a recuperare i chunks con dettagli specifici come date e importi.
```

---

## Phase 24: Fixed semantic_expansions Pipeline Bug ✅

### Problem
Phase 23 added deadline terms to the LLM prompt, but semantic_expansions were **never reconstructed** from state in step 039c. The LLM generated the terms correctly, but they were lost before reaching the BM25 search.

### Flow Analysis
```
Step 39a: LLM generates semantic_expansions ✅
         ["pace fiscale", "pagamento", "rata", "scadenza", ...]
              ↓
State:   Stores semantic_expansions in query_variants dict ✅
              ↓
Step 39c: Reconstructs QueryVariants from state ❌ MISSING semantic_expansions!
              ↓
BM25:    queries.semantic_expansions = None ❌
```

### Solution Implemented
**File:** `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` (line 137)

Added `semantic_expansions` to QueryVariants reconstruction:
```python
query_variants = QueryVariants(
    bm25_query=query_variants_dict.get("bm25_query", user_query),
    vector_query=query_variants_dict.get("vector_query", user_query),
    entity_query=query_variants_dict.get("entity_query", user_query),
    original_query=query_variants_dict.get("original_query", user_query),
    document_references=query_variants_dict.get("document_references"),  # ADR-022
    semantic_expansions=query_variants_dict.get("semantic_expansions"),  # DEV-242 Phase 24
)
```

### Expected Result
BM25 search query will expand from:
```
"rottamazione quinquies pace fiscale"
```
to:
```
"rottamazione quinquies pace fiscale pagamento rata dichiarazione scadenza decadenza"
```

This will match chunks 9537-9542 which contain dates like "30 aprile 2026" and "31 luglio 2026".

---

## Phase 25: Add Chunk ID Logging ✅

**File:** `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` (lines 171-178)

Added logging to show which chunk IDs are retrieved for debugging:
```python
chunk_ids = [
    doc.get("metadata", {}).get("chunk_id")
    for doc in retrieval_result.get("documents", [])
]
logger.info(f"Step {NODE_LABEL}: Chunk IDs retrieved: {chunk_ids}")
```

---

## Phase 26: Pass CONTEXT_TOP_K to Retrieval ✅

**File:** `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` (lines 21, 162)

- Added import: `from app.core.config import CONTEXT_TOP_K`
- Changed: `service.retrieve(queries=..., hyde=..., top_k=CONTEXT_TOP_K)`

---

## Phase 27: Fix Deduplication Bug ✅

**Files:**
- `app/services/parallel_retrieval.py` (line 396-398)
- `app/core/config.py` (line 480)

**Problem:** Deduplication used `knowledge_item_id` (document ID), so ALL chunks from same doc were deduplicated to just ONE chunk.

**Solution:**
1. Changed `document_id` to use `result.id` (chunk ID) instead of `result.knowledge_item_id`
2. Reduced `CONTEXT_TOP_K` from 20 to 12 to stay within 50,000 char Message limit

**Result:** Chunks 9537-9542 now ALL retrieved (was only 9542 before)

```
Chunk IDs retrieved: ['9542', '9537', '9539', '9540', '9536', '9538', '9541', '9511', '9555', '9545', '1943', '1582']
```

---

## Phase 28: Enhance Grounding Rules for Completeness ✅

**File:** `app/orchestrators/prompting.py` (lines 812-839)

**Problem:** Grounding rules enforce accuracy but not completeness. Response missing:
- 3% annual interest rate (in chunk 9538)
- Decadenza rule - 2 missed payments (in chunk 9542)
- Debt period - fino al 31 dicembre 2023
- Exclusions - rottamazione-quater

**Solution:** Added COMPLETEZZA OBBLIGATORIA checklist to grounding_rules with 7 mandatory elements:

| Elemento | Esempio |
|----------|---------|
| Scadenza domanda | "entro il 30 aprile 2026" |
| Prima rata | "31 luglio 2026" |
| Tasso interessi | "3 per cento annuo" |
| Numero rate | "54 rate bimestrali" |
| Periodo carichi | "fino al 31 dicembre 2023" |
| Decadenza | "due rate mancate = decadenza" |
| Esclusioni | "esclusi piani quater in regola" |

---

## Phase 29B: Increase CONTEXT_TOP_K to Include Chunk 9534 ✅

**File:** `app/core/config.py` (line 480)

**Problem:** Chunk 9534 contains the debt period ("dal 1° gennaio 2000 al 31 dicembre 2023") but was NOT in TOP-12 retrieved chunks.

**Solution:** Increased CONTEXT_TOP_K from 12 to 15 to capture more chunks.

```python
CONTEXT_TOP_K = int(os.getenv("CONTEXT_TOP_K", "15"))  # DEV-242 Phase 29B: Increased from 12 to 15
```

**Expected Result:** Chunk 9534 should now be included in retrieval, enabling the LLM to extract the debt period dates.

---

## Phase 30: Fix HYBRID_K_FTS Hardcoded Limit ✅

**File:** `app/services/parallel_retrieval.py` (lines 365-370, 388-393)

**Problem:** `HYBRID_K_FTS=30` was defined in config but the BM25 search used hardcoded `limit=20`, reducing the candidate pool by 33%.

**Solution:** Import and use `HYBRID_K_FTS` from config.

```python
# Added import:
from app.core.config import HYBRID_K_FTS

# Changed from:
limit=20
# To:
limit=HYBRID_K_FTS
```

**Impact:** BM25 now retrieves 30 candidates instead of 20, increasing the candidate pool by 50%.

---

## Phase 31: ECCELLENZA PROFESSIONALE - "WOW" Quality ✅

**File:** `app/orchestrators/prompting.py` (lines 839-864)

**Problem:** Responses were accurate and complete but lacked operational structure professionals need. Users said: "better, but not WOW".

**Gap Analysis:**
| Current (Good) | Needed (Exceptional) |
|----------------|---------------------|
| Lists facts from KB | Provides actionable guidance |
| Cites deadlines | Creates action timeline |
| Mentions consequences | Quantifies specific penalties |
| Single-path answer | Compares multiple options |

**Solution:** Added ECCELLENZA PROFESSIONALE section to grounding_rules requiring:

1. **STRUTTURA OPERATIVA** - Sections: ✅ COSA FARE, ⚠️ RISCHI, 📅 TIMELINE, 💼 ASPETTI PRATICI
2. **QUANTIFICA I RISCHI** - Specific percentages, not generic "sanzioni"
3. **CONFRONTA OPZIONI** - Pro/contro when alternatives exist
4. **SUGGERISCI IL PASSO SUCCESSIVO** - Actionable next step
5. **GERARCHIA DELLE FONTI** - Emphasize most authoritative source

**Expected Response Structure:**
```
La rottamazione quinquies...

✅ COSA FARE
Presentare domanda entro il 30 aprile 2026...

⚠️ RISCHI SPECIFICI
- 2 rate mancate = DECADENZA totale
- Interessi: 3% annuo
- NON sono previsti i 5 giorni di tolleranza

📅 TIMELINE AZIONI
1. Entro 30/4/2026: Presentare dichiarazione
2. 31/7/2026: Prima rata
...

💼 ASPETTI PRATICI
- Verificare carichi (1/1/2000 - 31/12/2023)
- Organizzare bonifico periodico automatico
```

---

## Phase 32: Fix Chunk 9534 Retrieval ✅

**Problem:** Chunk 9534 contains the debt period ("dal 1° gennaio 2000 al 31 dicembre 2023") but was NOT being retrieved because it lacks topic keywords like "rottamazione" or "pace fiscale".

**Root Cause:** BM25 search doesn't match chunk 9534 because it contains "carichi affidati" and dates but NOT the search terms.

**Solution (Both Approaches):**

**32A: Semantic Expansions**
- File: `app/services/multi_query_generator.py`
- Added "carichi affidati", "debiti risultanti", "periodo", "interessi" to semantic expansions
- Updated REGOLA AGGIUNTIVA with debt period terms

**32C: Increased CONTEXT_TOP_K**
- File: `app/core/config.py`
- Increased from 15 to 18 to accommodate more chunks

**Expected Result:** Chunk 9534 should now be retrieved, enabling correct debt period in response.

---

## Phase 29A: Ingest AdER Official Rules 🔴 (PENDING)

**Problem:** AdER (Agenzia delle Entrate-Riscossione) published "regole ufficiali" on their portal for rottamazione quinquies, but these documents were NEVER ingested into the PratikoAI knowledge base.

**Evidence:**
```sql
SELECT DISTINCT source FROM knowledge_items WHERE source ILIKE '%ader%' OR source ILIKE '%agenzia%riscossione%';
-- Result: No rows returned
```

**Solution:** Ingest AdER official rules from their portal.

---

## Key Database Values

### Doc 2463 (Full Law - Target)
```sql
id: 2463
title: "LEGGE 30 dicembre 2025, n. 199 - Art. 1 - guenti: «33 per cento»"
source: "gazzetta_ufficiale"
category: "legge"
document_type: "article"
```

**Expected boost:** 1.8 × 1.3 = **2.34x**

### Doc 2080 (MEF Summary - Should Rank Lower)
```sql
id: 2080
title: "Principali misure della legge di bilancio 2026"
source: "ministero_economia_documenti"
category: "regulatory_documents"
document_type: "chunk"
```

**Expected boost:** 1.0 × 0.9 = **0.9x**

---

## Test Commands

### Verify Configuration in Docker
```bash
docker exec pratikoai-be-app-1 grep "legge.*1.8" /app/app/services/parallel_retrieval.py
docker exec pratikoai-be-app-1 grep "gazzetta_ufficiale.*1.3" /app/app/services/parallel_retrieval.py
docker exec pratikoai-be-app-1 grep "CONTEXT_TOP_K" /app/app/core/config.py
```

### Verify DB Content
```sql
SELECT id, title, source, category FROM knowledge_items WHERE id IN (2463, 2080);
```

### Check Chunks with Dates
```sql
SELECT kc.id, LEFT(kc.chunk_text, 200)
FROM knowledge_chunks kc
WHERE kc.id IN (9537, 9538, 9539, 9540, 9541, 9542);
```

---

## Files Modified

| File | Changes |
|------|---------|
| `app/services/parallel_retrieval.py` | GERARCHIA_FONTI, SOURCE_AUTHORITY, source field fix, chunk_id dedup, HYBRID_K_FTS fix (Phase 17-18, 22, 27, 30) |
| `app/services/multi_query_generator.py` | semantic_expansions field + deadline terms (Phase 16A, 23) |
| `app/core/langgraph/nodes/step_039c__parallel_retrieval.py` | semantic_expansions reconstruction, CONTEXT_TOP_K, chunk ID logging (Phase 24-26) |
| `app/core/llm/model_config.py` | max_tokens increase (Phase 19) |
| `app/core/config.py` | CONTEXT_TOP_K=15, HYBRID_K_* increases (Phase 21, 27, 29B) |
| `app/prompts/v1/unified_response_simple.md` | COMPLETEZZA OBBLIGATORIA section (Phase 20) |
| `app/services/search_service.py` | TOPIC_SYNONYMS update (Phase 15) |
| `app/orchestrators/prompting.py` | grounding_rules completeness + ECCELLENZA PROFESSIONALE (Phase 28, 31) |

---

## Phase 45: Fix Missing `<answer>` Tags ✅

**File:** `app/orchestrators/prompting.py`

**Problem:** LLM follows grounding rules format (numbered list) but ignores `<answer>` wrapper tags from SUGGESTED_ACTIONS_PROMPT because grounding rules come later in prompt and don't mention the wrapper.

**Solution:**
1. Added `<answer>` tag reminder at END of grounding rules (lines 967-985)
2. Added "5 giorni tolleranza" to COMPLETEZZA checklist (line 862)

**Key Addition (lines 967-984):**
```
### 🔴 FORMATO OUTPUT FINALE (DEV-242 Phase 45) - CRITICO
La risposta DEVE essere avvolta in tag XML:

<answer>
[Tutta la tua risposta qui: lista numerata + fonti]
</answer>

<suggested_actions>
[JSON array with 2-4 actions]
</suggested_actions>

⛔ OBBLIGATORIO: Se NON includi i tag <answer> e <suggested_actions>, la risposta sarà RIFIUTATA.
```

---

## Success Criteria

Response to "Parlami della rottamazione quinquies" must include:
- ✅ "30 aprile 2026" (application deadline)
- ✅ "31 luglio 2026" (first payment date)
- ✅ "3 per cento annuo" (interest rate)
- ✅ "54 rate bimestrali" (payment schedule)
- ✅ "due rate = decadenza" (forfeiture rule)
- ✅ "NON previsti i 5 giorni di tolleranza" (Phase 45)
- ✅ `<answer>` wrapper tags (Phase 45)
- ✅ `<suggested_actions>` JSON block (Phase 45)
