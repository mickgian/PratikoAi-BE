# DEV-250: Response Quality Fix - Free-Form Responses

**Issue:** Response quality degradation after DEV-250 refactoring
**Status:** ✅ FIXED - Switched to free-form responses
**Started:** January 28, 2026
**Last Updated:** January 28, 2026

---

## Problem Statement

After the DEV-250 refactoring of oversized LangGraph nodes, response quality degraded significantly:

| Symptom | Before DEV-250 | After DEV-250 |
|---------|----------------|---------------|
| Response style | Natural flowing prose | Excessive bullet points |
| Section count | 7+ detailed sections | 4 short sections |
| Detail level | Specific dates, rates, conditions | Generic summaries |
| Document feel | Professional legal document | Bulleted outline |

**Example Query:** "Parlami della rottamazione quinquies"

**Before (Good):**
- Definizione with context
- Requisiti (chi può aderire, chi è escluso)
- Scadenze (domanda: 30 aprile 2026, prima rata: 31 luglio 2026, etc.)
- Condizioni di pagamento (unica soluzione vs rateale, 3% annuo)
- Decadenza dal beneficio
- Sospensione attività di riscossione
- Avvertenze importanti

**After (Degraded):**
- 4 bullet-heavy sections
- Missing specific dates and rates
- Overly summarized content

---

## Root Cause Analysis

### The Problem: Structured Output Constrains LLM Writing

The unified response prompt (`unified_response_simple.md`) required XML structured output:

```xml
<response>
<reasoning>...</reasoning>
<answer>...</answer>
<sources>...</sources>
<suggested_actions>...</suggested_actions>
</response>
```

**Why This Caused Quality Degradation:**

1. **Format Focus:** LLM spent cognitive effort on structure compliance instead of content quality
2. **Bullet Bias:** XML/JSON schemas subtly encourage list-based responses over prose
3. **Token Competition:** Schema overhead reduced tokens available for actual content
4. **Parsing Anxiety:** LLM simplified responses to avoid breaking XML structure

---

## Solution: Free-Form Responses

Removed structured JSON/XML requirements, returned to natural prose writing.

### Changes Made

#### 1. Prompt Update: `app/prompts/v1/unified_response_simple.md`

**Removed:**
- Entire `## Formato Output (XML OBBLIGATORIO)` section
- XML schema examples
- `suggested_actions` generation rules (complex, rarely used)
- XML example for KB empty responses

**Added:**
```markdown
## Formato Risposta

Scrivi la risposta come un documento professionale in italiano.

### Stile di Scrittura

**PREFERISCI LA PROSA FLUIDA:**
- Usa paragrafi discorsivi per spiegazioni, definizioni e concetti
- Evita eccessivi bullet point - la prosa è più leggibile e professionale
- Riserva le liste SOLO quando servono davvero

**USA LISTE NUMERATE SOLO PER:**
- Sequenze ordinate (fasi di una procedura, scadenze cronologiche)

**USA LISTE PUNTATE SOLO PER:**
- Elenchi non ordinati (requisiti, eccezioni, casi possibili)
- Quando ci sono 4+ elementi dello stesso tipo
```

**Kept (Critical Instructions):**
- ✅ COMPLETEZZA OBBLIGATORIA (include all KB details)
- ✅ Anti-hallucination rules (cite only from KB)
- ✅ Inline citation format (Art. X, comma Y, L. Z/AAAA)
- ✅ KB empty detection
- ✅ Follow-up handling
- ✅ Sequential numbering rules
- ✅ Chain of Thought reasoning

#### 2. Orchestrator: No Changes Needed

**File:** `app/services/llm_orchestrator.py`

The `_parse_unified_response()` method (lines 586-622) already had robust fallback handling:

```python
def _parse_unified_response(self, response: str, config: ModelConfig) -> dict:
    try:
        json_str = self._extract_json(response)
        data = json.loads(json_str)
        return {
            "reasoning": data.get("reasoning", {}),
            "answer": data.get("answer", response),
            # ...
        }
    except (json.JSONDecodeError, KeyError):
        # DEV-250: Free-form response - use raw text as answer
        return {
            "reasoning": {},
            "answer": response,  # Raw text becomes the answer
            "sources_cited": [],
            "suggested_actions": [],
        }
```

This means free-form responses are automatically handled correctly.

---

## Frontend Changes: Global CSS for Markdown Prose

**File:** `src/app/globals.css` (Frontend repo)

Added prose styling rules to encourage natural reading flow:

```css
/* DEV-250: Markdown prose styling for AI responses */
.prose {
  /* Base typography */
  line-height: 1.75;

  /* Paragraph spacing */
  p {
    margin-bottom: 1em;
  }

  /* Headers */
  h2, h3 {
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    font-weight: 600;
  }

  /* Lists - only when semantically appropriate */
  ul, ol {
    margin-bottom: 1em;
    padding-left: 1.5em;
  }

  li {
    margin-bottom: 0.25em;
  }

  /* Inline citations */
  .citation {
    font-style: italic;
    color: var(--muted-foreground);
  }
}
```

**Why This Matters:**
- Encourages reading prose as continuous text
- Proper spacing between paragraphs and sections
- Lists styled appropriately when used
- Citations visually distinguished

---

## Files Modified

| File | Repository | Changes |
|------|------------|---------|
| `app/prompts/v1/unified_response_simple.md` | Backend | Removed XML format, added free-form instructions |
| `app/services/llm_orchestrator.py` | Backend | No changes (fallback already handled) |
| `src/app/globals.css` | Frontend | Added prose styling for markdown responses |

---

## Verification

### Test Commands

```bash
# Run llm_response tests
uv run pytest tests/unit/services/llm_response/ -v

# Run prompt tests
uv run pytest tests/prompts/ -v
```

### Results

- ✅ 63 `llm_response` tests passed
- ✅ 23 prompt and disclaimer filter tests passed

### Manual Verification

Test with: `"parlami della rottamazione quinquies"`

**Expected Output:**
- Natural flowing prose (not excessive bullets)
- 7+ detailed sections
- Specific details (dates, rates, conditions)
- Professional document style
- Inline citations (Art. 1, comma 231, L. 199/2025)

---

## Rollback Plan

If free-form causes issues, can revert by:

1. Restore XML schema in `unified_response_simple.md`
2. The orchestrator's JSON/XML parsing will automatically pick it up

---

## Architectural Lessons Learned

### 1. Structured Output Has Hidden Costs

**Lesson:** JSON/XML schemas impose cognitive overhead on LLMs that can degrade content quality. Use structured output only when:
- Downstream systems need machine-readable data
- The structure itself carries semantic meaning
- Parsing reliability is critical

For human-readable responses, free-form text often produces better results.

### 2. Fallback Handlers Enable Flexibility

**Lesson:** The orchestrator's existing fallback to raw text made this fix trivial. Always implement graceful degradation:

```python
try:
    return parse_structured(response)
except ParseError:
    return use_raw_text(response)  # Fallback works
```

### 3. Prompt Instructions Shape Response Style

**Lesson:** Explicit instructions about writing style (prose vs bullets) significantly impact output:

- **Vague:** "Write a response" → LLM defaults to bullets
- **Specific:** "Use flowing prose, reserve lists for ordered sequences" → Natural document

---

## Related Issues

- **DEV-242**: Response Quality & Completeness (COMPLETEZZA OBBLIGATORIA rules)
- **DEV-244**: KB Source URLs Display (frontend SSE fixes)
- **DEV-245**: Anti-hallucination rules (cite only from KB)
