# Prompt Engineering Knowledge Base

**Purpose:** Senior-level prompt engineering patterns for PratikoAI
**Audience:** Developers, architects, and agents working on prompts
**Last Updated:** 2025-12-12

---

## Part 1: PratikoAI Prompt Architecture

### Multi-Layer Composition

PratikoAI uses a layered prompt architecture where prompts are composed from multiple sources:

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: Base System Prompt (system.md)                      │
│ ├─ Role definition (Italian tax specialist)                  │
│ ├─ Core behavior rules (no emojis, professional tone)        │
│ ├─ Source citation formatting                                │
│ └─ Fallback behavior ("I don't know")                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: Conditional Injections                              │
│ ├─ Document Analysis Guidelines (document_analysis.md)       │
│ │   └─ Injected when query_composition = "pure_doc"/"hybrid" │
│ └─ Date/Time Injection ({current_date_and_time})             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: Domain-Specific Templates                           │
│ ├─ 5 Domains: TAX, LEGAL, LABOR, BUSINESS, ACCOUNTING        │
│ ├─ 7 Actions: INFO_REQUEST, DOC_GEN, CALCULATION, etc.       │
│ └─ Domain+Action specific instructions                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: RAG Context Injection (Step 40)                     │
│ ├─ Retrieved documents from knowledge base                   │
│ ├─ User-uploaded document content                            │
│ └─ Merged context with source URLs                           │
└─────────────────────────────────────────────────────────────┘
```

### Prompt Flow Through LangGraph (Steps 15, 41-47)

```
STEP 15: Default Prompt Setup
    │
    ├─ Load SYSTEM_PROMPT from system.md
    ├─ Inject DOCUMENT_ANALYSIS_PROMPT if query_composition is "pure_doc" or "hybrid"
    └─ Set state["system_prompt"]
    │
    ▼
STEP 41: Select Appropriate Prompt
    │
    ├─ Check if classification is available
    └─ Check classification confidence (threshold: 0.6)
        │
        ├─ confidence >= 0.6 → STEP 43 (Domain-Specific)
        └─ confidence < 0.6 → STEP 44 (Default)
    │
    ▼
STEP 43: Domain-Specific Prompt (if confident)
    │
    ├─ Get domain from classification (TAX, LEGAL, etc.)
    ├─ Get action from classification (CALCULATION, etc.)
    ├─ Call PromptTemplateManager.get_prompt(domain, action, query)
    └─ Inject document analysis prompt if applicable
    │
    ▼
STEP 44: Default System Prompt (if not confident)
    │
    └─ Use base SYSTEM_PROMPT with conditional injections
    │
    ▼
STEPS 45-47: Message Management
    │
    ├─ Check if system message exists in messages
    ├─ Replace existing OR insert new system message
    └─ Set state["messages"] with updated system prompt
```

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `app/core/prompts/system.md` | ~372 | Base system prompt |
| `app/core/prompts/document_analysis.md` | ~157 | Document handling rules |
| `app/services/domain_prompt_templates.py` | ~662 | PromptTemplateManager |
| `app/orchestrators/prompting.py` | ~1070 | Steps 15, 41, 44-47 |
| `app/orchestrators/classify.py` | - | Step 43 domain routing |

---

## Part 2: Prompt Design Principles

### Principle 1: Token Efficiency

Every token costs money. Be concise without losing clarity.

**Anti-pattern:**
```
You are an AI assistant that is designed to help users with their questions.
When a user asks you a question, you should try to give them the most helpful
answer possible. If you don't know the answer, you should let them know that
you don't know and suggest they look elsewhere for the information.
```

**Better:**
```
Aiuta professionisti con domande fiscali e tributarie italiane.
Se non sai la risposta, dillo chiaramente.
```

### Principle 2: Instruction Clarity

One instruction per line. Avoid compound sentences that bundle multiple rules.

**Anti-pattern:**
```
When citing sources, always include the document type and URL, and make sure
to explain the authority level, and also include the date if available.
```

**Better:**
```
# Source Citation Rules
1. Include document type label (e.g., [NORMATIVA/PRASSI])
2. Provide clickable markdown links
3. Explain authority level (binding vs. informational)
4. Include exact publication date from 📅 marker
```

### Principle 3: Explicit Negatives

State what NOT to do when behavior is commonly wrong.

**PratikoAI Example (system.md:17-21):**
```markdown
# IMPORTANT: Formatting Rules
- **DO NOT use emojis in your responses** (no ✅, 📊, 💡, ⚠️, etc.)
- Use professional, formal Italian language
- Use bullet points (•) or numbers (1., 2., 3.) instead of emoji bullets
```

### Principle 4: Examples Over Abstractions

Concrete examples are more effective than abstract rules.

**PratikoAI Example (system.md:47-54):**
```markdown
4. **Example of proper citation**
   ```
   Secondo la [NORMATIVA/PRASSI - AGENZIAENTRATE] Interpello n. 280/2025,
   il trattamento fiscale prevede...
   [Interpello n. 280 del 30/10/2025](https://www.agenziaentrate.gov.it/...)
   ```
```

### Principle 5: Conditional Injection

Only inject instructions when relevant. Don't bloat every prompt.

**PratikoAI Pattern:**
```python
# Step 15: Only inject document analysis for document queries
if query_composition in ["pure_doc", "hybrid"]:
    prompt = f"{base_prompt}\n\n{DOCUMENT_ANALYSIS_PROMPT}"
```

---

## Part 3: Italian Legal/Tax Prompt Patterns

### Citation Format

Italian legal documents have specific citation conventions:

| Document Type | Format | Example |
|--------------|--------|---------|
| **Article** | Art. X, comma Y | Art. 2, comma 3 |
| **Decree** | D.Lgs. n. X/YYYY | D.Lgs. n. 231/2001 |
| **Circular** | Circolare n. X/E del DD/MM/YYYY | Circolare n. 15/E del 10/03/2025 |
| **Resolution** | Risoluzione n. X del DD/MM/YYYY | Risoluzione n. 56 del 13/10/2025 |
| **Interpello** | Interpello n. X del DD/MM/YYYY | Interpello n. 280 del 30/10/2025 |

### Authority Hierarchy

PratikoAI must distinguish source authority levels:

```
LEGALLY BINDING (highest authority)
├── Gazzetta Ufficiale publications
├── Decreti Legge
└── D.Lgs. (Decreti Legislativi)

AUTHORITATIVE INTERPRETATION
├── Circolari Agenzia delle Entrate
├── Circolari INPS
└── Interpelli

INFORMATIONAL (non-binding)
└── News articles and announcements
```

### Professional Tone

| Requirement | Implementation |
|-------------|---------------|
| Formal address | Use "Lei" form, not "tu" |
| No emojis | Text labels only (NOTA:, ATTENZIONE:) |
| Professional language | Avoid colloquialisms |
| Precise dates | "13 ottobre 2025", never "a few days ago" |

### Deadline Handling (Scadenze)

Italian tax deadlines are critical. Never approximate.

**System prompt rule (enforced):**
```markdown
## Document Date Handling

**CRITICAL RULES FOR DATES:**
1. ALWAYS use the date from 📅 Publication Date marker
2. NEVER invent, assume, or guess document dates
3. If no date shown, say "publication date not specified"
```

---

## Part 4: RAG Context Integration

### Context Injection Placement

Context should be injected AFTER system instructions, BEFORE the user query:

```
[System Prompt - Layer 1-3]
...

---
## Context from Knowledge Base:

[Retrieved Document 1]
Source URL: https://...
📅 Publication Date: 13/10/2025
Content: ...

[Retrieved Document 2]
...

---

User Query: {user_question}
```

### Missing Context Handling

When RAG retrieval returns nothing:

**Anti-pattern:**
```
Based on the context provided... [but there was no context]
```

**Correct (from system.md:56-59):**
```markdown
5. **If no sources are provided in context**
   - Clearly state you're using general knowledge
   - Do not claim sources you don't have
   - Suggest the user verify with official sources
```

### Source Attribution Rules

Every factual claim must be traceable:

```markdown
# From system.md
- When the context includes a source link, you MUST include it in response
- Use markdown links with COMPLETE URL: [Title](COMPLETE_URL)
- **CRITICAL**: NEVER truncate URLs
- Never paraphrase sources without attribution
```

### Fallback Behavior

Define explicit fallback text in Italian:

```
Non ho trovato documenti specifici su questo argomento nel database.
Ti suggerisco di consultare direttamente il sito dell'Agenzia delle Entrate
o rivolgerti a un professionista abilitato.
```

---

## Part 5: Evaluation & Quality

### Quality Metrics

PratikoAI tracks prompt quality via `PromptTemplate` model:

| Metric | Range | Description |
|--------|-------|-------------|
| `clarity_score` | 0.0-1.0 | How clear are instructions? |
| `completeness_score` | 0.0-1.0 | Are all scenarios covered? |
| `accuracy_score` | 0.0-1.0 | Do outputs match intent? |
| `overall_quality_score` | 0.0-1.0 | Weighted average |

### A/B Testing Infrastructure

PratikoAI has built-in A/B testing support (currently unused):

```python
# PromptTemplate model supports:
variant_group: str | None  # "control", "variant_a", "variant_b"
is_active: bool            # Enable/disable without deletion
usage_count: int           # Track usage
success_rate: float        # Track success
```

### Regression Testing for Prompts

When modifying prompts:

1. **Run evaluation dataset:**
   ```bash
   uv run pytest evals/ -v
   ```

2. **Check metrics:**
   - Hallucination rate (should not increase)
   - Citation accuracy (should not decrease)
   - Fallback triggers (should work correctly)

3. **Test files:**
   - `tests/orchestrators/test_prompting.py`
   - `tests/test_rag_step_43_domain_prompt_generation.py`
   - `tests/test_rag_step_15_default_prompt.py`

### Hallucination Detection Patterns

Test for common hallucination scenarios:

| Scenario | Test |
|----------|------|
| **Invented citations** | Verify cited documents exist in KB |
| **Wrong dates** | Compare against 📅 Publication Date |
| **Future dates** | Flag any date > current date |
| **Truncated URLs** | Check URLs are complete, no "..." |

---

## Part 6: Common Anti-Patterns

### Anti-Pattern 1: Over-Constraining

Too many rules kill creativity and helpfulness.

**Problem:**
```markdown
- NEVER use more than 3 bullet points
- ALWAYS respond in exactly 150 words
- DO NOT mention any topics outside fiscal law
- NEVER use the word "maybe"
```

**Better:** Only constrain what matters (emojis, citation format).

### Anti-Pattern 2: Conflicting Instructions

Different layers shouldn't contradict each other.

**Problem:**
```markdown
# Layer 1
Be concise and brief.

# Layer 2 (document analysis)
Provide detailed, comprehensive explanations of every column.
```

**Solution:** Make conditional injection truly conditional, or harmonize rules.

### Anti-Pattern 3: Token Waste

Redundant or verbose instructions waste budget.

**Problem (repeated 3 times in prompt):**
```markdown
Remember to always cite your sources.
...
Don't forget to include citations.
...
Make sure to provide source links.
```

**Solution:** Say it once, clearly.

### Anti-Pattern 4: Vague Fallback

Undefined behavior when things go wrong.

**Problem:**
```markdown
If you can't find relevant information, try to help the user.
```

**Better:**
```markdown
If no sources found in context:
1. State: "Non ho trovato documenti specifici nel database."
2. Suggest official sources (Agenzia delle Entrate website)
3. Never fabricate information
```

### Anti-Pattern 5: Placeholder Leakage

Example placeholders appearing in outputs.

**Problem (system.md:98-99):**
```markdown
**NEVER use placeholder text like [summary], [specifiche questioni fiscali]**
- These are EXAMPLE PLACEHOLDERS in documentation
- ALWAYS write actual summaries from document content
```

This rule exists because the anti-pattern was observed.

---

## Part 7: Prompt Change Workflow

### Before Changing Prompts

1. **Read this knowledge base**
2. **Understand the layer being modified** (system.md vs domain template)
3. **Consider cascading effects** on other layers
4. **Check existing tests** that verify prompt behavior

### Approval Process

| Change Type | Approval Needed |
|-------------|-----------------|
| Typo fix | Self-approve |
| Minor wording change | Peer review |
| New instruction | Egidio (architect) |
| New conditional injection | Egidio + ADR |
| Restructure prompt layers | Egidio + ADR + stakeholder |

### Testing After Changes

```bash
# Run prompt-specific tests
uv run pytest tests/orchestrators/test_prompting.py -v
uv run pytest tests/test_rag_step_43_domain_prompt_generation.py -v
uv run pytest tests/test_rag_step_15_default_prompt.py -v

# Run evaluation suite
uv run pytest evals/ -v
```

### Rollback Plan

Prompts are in code, so rollback = git revert.

For urgent rollback:
```bash
git revert HEAD  # Revert last commit
git push origin develop
# Wait for CI/CD deployment
```

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2025-12-12 | Initial creation | System |

---

**Document Status:** Active
**Related Files:** `app/core/prompts/`, `app/services/domain_prompt_templates.py`
**Related ADRs:** ADR-016 (Document Analysis Injection)
