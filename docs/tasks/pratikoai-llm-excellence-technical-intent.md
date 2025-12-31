# Technical Intent Document: PratikoAI LLM Excellence Architecture

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 2.0 |
| **Date** | 2024-12-30 |
| **Status** | Final - Ready for Development |
| **Author** | Technical Architecture Review |
| **Reviewers** | Claude (Anthropic), Gemini (Google) |
| **Related Docs** | LLM_ARCHITECTURE_AUDIT.md, pratikoai-technical-intent.md |

---

## Document Structure

| Part | Title | Content |
|------|-------|---------|
| 1 | Current State Analysis | Audit findings, issues, baseline metrics |
| 2 | Target Architecture | Architecture diagram, cost model, reasoning strategies |
| 3 | Component Specifications | GraphState, prompts, orchestrator, validator |
| 4 | Data Flow Specification | Request flow, error handling |
| 5 | API Contracts | Internal/external response schemas |
| 6 | Implementation Phases | Week-by-week task breakdown |
| 7 | Success Metrics | Quality, performance, cost, business metrics |
| 8 | Risk Assessment | Technical/business risks, rollback plans |
| 9 | Testing Strategy | Unit, integration, quality tests |
| 10 | Glossary | Term definitions |
| **11** | **Excellence Refinements** | Source hierarchy, risk analysis, dual reasoning, Golden Loop |
| **12** | **User Experience (UI/UX)** | Loading states, action cards, reasoning display |
| A | Prompt Templates Reference | Classifier, action examples |
| B | Migration Checklist | Phase-by-phase deployment checklist |

---

## Executive Summary

This document defines the technical architecture for elevating PratikoAI's LLM reasoning capabilities from the current state to an "Excellence" tier. The primary goals are:

1. **Fix context fragmentation** - Ensure suggested actions have access to KB documents
2. **Implement explicit reasoning** - Chain of Thought (CoT) and Tree of Thoughts (ToT)
3. **Optimize costs** - Multi-LLM routing based on query complexity
4. **Improve coherence** - Unified output format across all query types

**Target Metrics:**
- Answer quality: 95%+ accuracy (up from 91%)
- Suggested actions relevance: 90%+ (up from ~60%)
- Cost per query: €0.0052 blended average
- Response time: <3s (simple), <5s (complex)

---

## Part 1: Current State Analysis

### 1.1 Architecture Audit Findings

The LLM Architecture Audit (2024-12-29) identified these critical issues:

#### Issue 1: Context Fragmentation (CRITICAL)

```
CURRENT FLOW:
Step 40 (BuildContext) → KB_DOCS loaded
Step 64 (LLM Call)     → KB_DOCS used for answer generation
Step 100 (Post-Proact) → KB_DOCS LOST - only answer text available
```

**Impact:** Suggested actions are generated without access to the source documents that informed the answer, resulting in generic, disconnected suggestions.

**Evidence:** Actions like "Approfondisci" or "Verifica sul sito" instead of specific actions referencing actual KB content.

#### Issue 2: Implicit Reasoning (HIGH)

Current prompts contain implicit reasoning instructions ("analyze... then... finally...") but no explicit Chain of Thought structure.

**Impact:**
- Inconsistent reasoning quality
- No visibility into model's decision process
- Difficult to debug incorrect answers

#### Issue 3: Dual-Path Logic (MEDIUM)

Two different prompt paths exist:
- `SYNTHESIS_SYSTEM_PROMPT` → VERDETTO format (technical_research route)
- `SYSTEM_PROMPT + SUGGESTED_ACTIONS_PROMPT` → XML tags format (other routes)

**Impact:**
- Inconsistent output formats
- Different quality levels between routes
- Parsing complexity

#### Issue 4: Prompt Quality Issues (MEDIUM)

- 404-line system prompt (overwhelming)
- Mixed Italian/English instructions
- Repeated rules (3x "never suggest consultants")
- Emoji policy contradiction
- No examples in suggested_actions prompt

### 1.2 Current Cost Structure

| Component | Model | Cost/Call | Calls/Query | Total |
|-----------|-------|-----------|-------------|-------|
| Router | GPT-4o-mini | €0.0002 | 1 | €0.0002 |
| Multi-Query | GPT-4o-mini | €0.0002 | 1 | €0.0002 |
| HyDE | GPT-4o-mini | €0.0001 | 1 | €0.0001 |
| Main Response | GPT-4o | €0.015 | 1 | €0.015 |
| **Total** | | | | **€0.0155** |

**Issue:** All queries use GPT-4o for main response, regardless of complexity.

### 1.3 Current Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User Query                                                  │
│     │                                                       │
│     ▼                                                       │
│ Step 34a: Router (GPT-4o-mini)                             │
│     │ Output: category, domain, confidence                  │
│     ▼                                                       │
│ Step 39a: Multi-Query Generator (GPT-4o-mini)              │
│     │ Output: 3 query variants                              │
│     ▼                                                       │
│ Step 39b: HyDE Generator (GPT-4o-mini)                     │
│     │ Output: hypothetical document                         │
│     │ ⚠️ ISSUE: Ignores conversation history               │
│     ▼                                                       │
│ Step 39c: Parallel Retrieval                               │
│     │ Output: KB documents                                  │
│     ▼                                                       │
│ Step 40: Build Context                                      │
│     │ Output: formatted context string                      │
│     │ ⚠️ ISSUE: kb_documents not stored in state          │
│     ▼                                                       │
│ Step 41-47: Prompt Selection                               │
│     │ Output: system prompt (varies by route)               │
│     ▼                                                       │
│ Step 64: LLM Call (GPT-4o always)                          │
│     │ Output: answer + maybe actions (XML format)           │
│     │ ⚠️ ISSUE: No explicit reasoning trace                │
│     ▼                                                       │
│ Step 100: Post-Proactivity                                 │
│     │ Input: ONLY answer text                               │
│     │ ⚠️ CRITICAL: KB context lost                         │
│     │ Output: suggested_actions (often poor quality)        │
│     ▼                                                       │
│ Final Response                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 2: Target Architecture

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PratikoAI Excellence Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   User Query                                                                 │
│       │                                                                      │
│       ▼                                                                      │
│   ┌───────────────────────────────────────────────────────────────┐         │
│   │  COMPLEXITY CLASSIFIER (GPT-4o-mini)                          │         │
│   │  Input: query, detected_domains, has_history, has_documents   │         │
│   │  Output: simple | complex | multi_domain                      │         │
│   │  Cost: €0.0002                                                │         │
│   └───────────────────────────────────────────────────────────────┘         │
│                       │                                                      │
│         ┌─────────────┼─────────────┐                                       │
│         ▼             ▼             ▼                                       │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐                              │
│   │ SIMPLE   │  │ COMPLEX  │  │ MULTI-DOMAIN │                              │
│   │ ~70%     │  │ ~25%     │  │ ~5%          │                              │
│   └────┬─────┘  └────┬─────┘  └──────┬───────┘                              │
│        │             │               │                                       │
│        ▼             ▼               ▼                                       │
│   ┌───────────────────────────────────────────────────────────────┐         │
│   │  CONVERSATIONAL HYDE (GPT-4o-mini)                            │         │
│   │  Input: query + last 3 conversation turns                     │         │
│   │  Output: hypothetical document (150-250 words)                │         │
│   │  Cost: €0.0001                                                │         │
│   └───────────────────────────────────────────────────────────────┘         │
│                       │                                                      │
│                       ▼                                                      │
│   ┌───────────────────────────────────────────────────────────────┐         │
│   │  RETRIEVAL (Hybrid: BM25 + Vector)                            │         │
│   │  Input: original query + HyDE embedding                       │         │
│   │  Output: kb_documents[], kb_sources_metadata[]                │         │
│   │  ✅ NEW: Store full documents in state                        │         │
│   └───────────────────────────────────────────────────────────────┘         │
│                       │                                                      │
│         ┌─────────────┼─────────────┐                                       │
│         ▼             ▼             ▼                                       │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐                              │
│   │ LINEAR   │  │ TREE OF  │  │ PARALLEL     │                              │
│   │ CoT      │  │ THOUGHTS │  │ ToT          │                              │
│   │ mini     │  │ GPT-4o   │  │ GPT-4o       │                              │
│   │ €0.001   │  │ €0.015   │  │ €0.020       │                              │
│   └────┬─────┘  └────┬─────┘  └──────┬───────┘                              │
│        │             │               │                                       │
│        └─────────────┴───────────────┘                                       │
│                       │                                                      │
│                       ▼                                                      │
│   ┌───────────────────────────────────────────────────────────────┐         │
│   │  UNIFIED OUTPUT (JSON)                                        │         │
│   │  {                                                            │         │
│   │    reasoning: {...} | tot_analysis: {...},                    │         │
│   │    answer: "...",                                             │         │
│   │    sources_cited: [...],                                      │         │
│   │    suggested_actions: [...]  ← Generated WITH kb_context      │         │
│   │  }                                                            │         │
│   └───────────────────────────────────────────────────────────────┘         │
│                       │                                                      │
│                       ▼                                                      │
│   ┌───────────────────────────────────────────────────────────────┐         │
│   │  ACTION VALIDATOR                                             │         │
│   │  - Reject generic labels (<8 chars)                           │         │
│   │  - Reject forbidden patterns (consult expert, etc.)           │         │
│   │  - Reject actions not grounded in KB sources                  │         │
│   │  - Ensure JSON validity                                       │         │
│   └───────────────────────────────────────────────────────────────┘         │
│                       │                                                      │
│                       ▼                                                      │
│   ┌───────────────────────────────────────────────────────────────┐         │
│   │  FINAL RESPONSE                                               │         │
│   │  answer + sources + validated_actions + reasoning_trace       │         │
│   └───────────────────────────────────────────────────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Cost Optimization Model

| Query Type | Distribution | Model | Cost/Query |
|------------|--------------|-------|------------|
| Simple | 70% | GPT-4o-mini | €0.0013 |
| Complex | 25% | GPT-4o | €0.0161 |
| Multi-Domain | 5% | GPT-4o | €0.0211 |
| **Blended Average** | 100% | - | **€0.0052** |

**Monthly Cost per User (50 queries/day):**
- Current: €0.0155 × 50 × 30 = €23.25/user
- Target: €0.0052 × 50 × 30 = €7.80/user
- **Savings: 66%**

### 2.3 Reasoning Strategies

#### 2.3.1 Chain of Thought (CoT) - For Simple Queries

Linear reasoning path for straightforward questions.

```
Query: "Qual è l'aliquota IVA ordinaria?"

REASONING:
├── Step 1: Identify topic → IVA rates
├── Step 2: Find sources → Art. 16 DPR 633/72
├── Step 3: Extract answer → 22%
└── Step 4: Formulate response

ANSWER: "L'aliquota IVA ordinaria è del 22%..."
```

**When to Use:**
- Single-concept questions
- Definitions and explanations
- Known facts with clear sources
- Basic calculations

#### 2.3.2 Tree of Thoughts (ToT) - For Complex Queries

Parallel hypothesis exploration for ambiguous or multi-faceted questions.

```
Query: "Come fatturare consulenza a azienda tedesca?"

HYPOTHESES:
├── Hypothesis A: B2B with VIES-registered company
│   ├── Assumption: Client has valid DE VAT number
│   ├── Fiscal consequence: Non-taxable + Reverse Charge
│   └── Score: 0.75
│
├── Hypothesis B: B2B without VIES registration
│   ├── Assumption: Client has no valid EU VAT
│   ├── Fiscal consequence: Italian VAT 22%
│   └── Score: 0.15
│
└── Hypothesis C: B2C to private individual
    ├── Assumption: Client is private person
    ├── Fiscal consequence: Italian VAT or OSS
    └── Score: 0.10

EVALUATION: Hypothesis A most likely (score 0.75)
ANSWER: Based on B2B EU scenario...
ALTERNATIVE NOTE: "If client lacks valid VAT, verify on VIES first"
```

**When to Use:**
- Ambiguous queries requiring interpretation
- Scenarios with multiple valid answers
- Questions where user context is unclear
- Regulatory situations with exceptions

#### 2.3.3 Multi-Domain ToT - For Cross-Domain Queries

Parallel analysis across professional domains.

```
Query: "Assumo dipendente che apre anche P.IVA freelance"

DOMAIN ANALYSIS:
├── LABOR Domain (Consulente del Lavoro)
│   ├── Employment contract considerations
│   ├── INPS contributions as employee
│   └── Non-compete clause implications
│
├── TAX Domain (Commercialista)
│   ├── Regime forfettario eligibility
│   ├── Gestione separata INPS
│   └── Cause of exclusion (employer relationship)
│
└── SYNTHESIS
    ├── Conflict: Forfettario exclusion if >€30k from employer?
    └── Recommendation: Verify income thresholds

ANSWER: Addresses both labor and tax implications...
```

**When to Use:**
- Questions spanning multiple professional domains
- Complex life/business situations
- Regulatory interactions between domains

---

## Part 3: Component Specifications

### 3.1 Graph State Schema

**File:** `app/graph/state.py`

```python
class GraphState(TypedDict):
    # ─────────────────────────────────────────────────────────
    # INPUT
    # ─────────────────────────────────────────────────────────
    user_query: str                      # Original user question
    user_id: str                         # User identifier
    conversation_id: str                 # Conversation thread ID
    conversation_history: list[dict]     # Previous turns [{role, content}]
    user_documents: list[dict]           # Uploaded documents metadata

    # ─────────────────────────────────────────────────────────
    # CLASSIFICATION (Step 34a)
    # ─────────────────────────────────────────────────────────
    query_category: str                  # chitchat|theoretical|technical|calculator
    query_complexity: str                # simple|complex|multi_domain (NEW)
    detected_domains: list[str]          # [TAX, LABOR, LEGAL]
    classification_confidence: float     # 0.0-1.0

    # ─────────────────────────────────────────────────────────
    # RETRIEVAL (Steps 39a-40)
    # ─────────────────────────────────────────────────────────
    multi_query_variants: list[str]      # Expanded query variants
    hyde_document: str                   # Hypothetical document

    # ✅ NEW: Full context preservation
    kb_documents: list[dict]             # Raw KB documents from retrieval
    kb_context_text: str                 # Formatted context string for LLM
    kb_sources_metadata: list[dict]      # Source metadata for action generation
    # Structure: [{title, type, date, url, key_topics}]

    # ─────────────────────────────────────────────────────────
    # REASONING (Step 64) - NEW
    # ─────────────────────────────────────────────────────────
    reasoning_type: str                  # cot|tot|tot_multi_domain
    reasoning_trace: dict                # CoT steps or ToT analysis
    # CoT: {tema, fonti_utilizzate, elementi_chiave, conclusione}
    # ToT: {hypotheses[], selected, selection_reasoning, confidence}

    tot_analysis: Optional[dict]         # Tree of Thoughts specific
    # Structure: {
    #   hypotheses: [{id, scenario, assumptions, fiscal_consequence, score, sources}],
    #   selected: str,
    #   selection_reasoning: str,
    #   confidence: float,
    #   alternative_note: str
    # }

    # ─────────────────────────────────────────────────────────
    # OUTPUT (Steps 64, 100)
    # ─────────────────────────────────────────────────────────
    llm_response: str                    # Main answer text
    sources_cited: list[dict]            # [{ref, relevance, url}]

    suggested_actions: list[dict]        # Validated actions
    # Structure: [{id, label, icon, prompt, source_basis}]
    actions_source: str                  # unified_llm|fallback|template
    actions_validation_log: list[str]    # Rejection reasons for debugging

    # ─────────────────────────────────────────────────────────
    # METRICS
    # ─────────────────────────────────────────────────────────
    query_cost_euros: float              # Total LLM cost for this query
    response_time_ms: int                # End-to-end latency
    model_used: str                      # Primary model for response
    cache_hit: bool                      # Whether response was cached
```

### 3.2 Prompt Templates

#### 3.2.1 Directory Structure

```
app/prompts/
├── __init__.py                          # Prompt loader utility
├── config.yaml                          # Version and A/B test config
│
├── v1/                                  # Version 1 prompts
│   ├── system_base.md                   # Core system instructions
│   ├── unified_response_simple.md       # Simple CoT prompt
│   ├── tree_of_thoughts.md              # Complex ToT prompt
│   ├── tree_of_thoughts_multi_domain.md # Multi-domain ToT prompt
│   ├── hyde_conversational.md           # HyDE with conversation context
│   ├── complexity_classifier.md         # Query complexity classification
│   └── action_examples.md               # Domain-specific action examples
│
└── components/                          # Reusable prompt components
    ├── forbidden_actions.md             # Actions to never suggest
    ├── source_citation_rules.md         # How to cite sources
    ├── italian_formatting.md            # Italian language rules
    └── verdetto_format.md               # VERDETTO structure template
```

#### 3.2.2 Prompt Loader Specification

**File:** `app/prompts/__init__.py`

```python
"""
Prompt Management System

Features:
- Versioned prompts
- Template variable substitution
- Component composition
- Caching for performance
- A/B testing support (future)
"""

@lru_cache(maxsize=50)
def load_prompt(
    name: str,
    version: str = "v1",
    **variables
) -> str:
    """
    Load and format a prompt template.

    Args:
        name: Prompt name (e.g., "unified_response_simple")
        version: Prompt version directory
        **variables: Template variables to substitute

    Returns:
        Formatted prompt string

    Raises:
        FileNotFoundError: If prompt file doesn't exist
        KeyError: If required variable is missing
    """

def load_component(name: str) -> str:
    """Load a reusable prompt component."""

def compose_prompt(*parts: str, separator: str = "\n\n---\n\n") -> str:
    """Compose multiple prompt parts with separators."""

def get_prompt_version() -> str:
    """Get current active prompt version from config."""
```

#### 3.2.3 Unified Response Prompt (Simple CoT)

**File:** `app/prompts/v1/unified_response_simple.md`

**Purpose:** Generate answer + actions in single call with linear reasoning

**Template Variables:**
- `{kb_context}` - Formatted knowledge base documents
- `{kb_sources_metadata}` - JSON array of source metadata
- `{query}` - User question
- `{conversation_context}` - Last 3 conversation turns (optional)
- `{current_date}` - Current date for temporal context

**Output Schema:**
```json
{
  "reasoning": {
    "tema_identificato": "string",
    "fonti_utilizzate": ["string"],
    "elementi_chiave": ["string"],
    "conclusione": "string"
  },
  "answer": "string",
  "sources_cited": [
    {"ref": "string", "relevance": "principale|supporto", "url": "string|null"}
  ],
  "suggested_actions": [
    {
      "id": "string",
      "label": "string (8-40 chars)",
      "icon": "calculator|search|calendar|info|document|law|euro|warning",
      "prompt": "string (25+ chars)",
      "source_basis": "string (which KB source inspired this)"
    }
  ]
}
```

#### 3.2.4 Tree of Thoughts Prompt

**File:** `app/prompts/v1/tree_of_thoughts.md`

**Purpose:** Explore multiple hypotheses for complex/ambiguous queries

**Template Variables:** Same as unified_response_simple

**Output Schema:**
```json
{
  "tot_analysis": {
    "hypotheses": [
      {
        "id": "A|B|C|D",
        "scenario": "string",
        "assumptions": ["string"],
        "fiscal_consequence": "string",
        "supporting_sources": ["string"],
        "score": 0.0-1.0
      }
    ],
    "selected": "A|B|C|D",
    "selection_reasoning": "string",
    "confidence": 0.0-1.0,
    "alternative_note": "string (what if different scenario)"
  },
  "answer": "string",
  "sources_cited": [...],
  "suggested_actions": [
    {
      ...
      "hypothesis_related": "A|B|C|D|all"
    }
  ]
}
```

#### 3.2.5 Conversational HyDE Prompt

**File:** `app/prompts/v1/hyde_conversational.md`

**Purpose:** Generate hypothetical document considering conversation context

**Template Variables:**
- `{query}` - Current user question
- `{conversation_context}` - Last 3 turns formatted as dialogue

**Output:** Plain text (150-250 words) - Italian bureaucratic style

**Key Requirement:** If conversation context exists, the hypothetical document must be a logical continuation of the discussed topic, not a standalone document.

### 3.3 LLM Orchestrator

**File:** `app/services/llm_orchestrator.py`

#### 3.3.1 Class: LLMOrchestrator

**Responsibility:** Route queries to appropriate models and manage costs

**Dependencies:**
- `LLMClient` - Unified client for OpenAI/Anthropic
- `CostTracker` - Cost monitoring
- `PromptLoader` - Prompt management

**Methods:**

```python
class LLMOrchestrator:

    async def classify_complexity(
        self,
        query: str,
        context: ComplexityContext
    ) -> QueryComplexity:
        """
        Classify query complexity using GPT-4o-mini.

        Args:
            query: User question
            context: {domains, has_history, has_documents}

        Returns:
            QueryComplexity enum: SIMPLE | COMPLEX | MULTI_DOMAIN

        Cost: ~€0.0002
        Latency: <500ms
        """

    async def generate_hyde(
        self,
        query: str,
        conversation_history: Optional[list[dict]] = None
    ) -> str:
        """
        Generate hypothetical document for retrieval.

        Args:
            query: User question
            conversation_history: Last N turns for context

        Returns:
            Hypothetical document (150-250 words)

        Model: GPT-4o-mini (always)
        Cost: ~€0.0001
        Latency: <800ms
        """

    async def generate_response(
        self,
        query: str,
        kb_context: str,
        kb_sources_metadata: list[dict],
        complexity: QueryComplexity,
        conversation_history: Optional[list[dict]] = None
    ) -> UnifiedResponse:
        """
        Generate response with appropriate model and reasoning strategy.

        Args:
            query: User question
            kb_context: Formatted KB documents
            kb_sources_metadata: Source metadata for action grounding
            complexity: Determined complexity level
            conversation_history: For context continuity

        Returns:
            UnifiedResponse with reasoning, answer, sources, actions

        Model Selection:
            SIMPLE → GPT-4o-mini (CoT)
            COMPLEX → GPT-4o (ToT)
            MULTI_DOMAIN → GPT-4o (ToT Multi-Domain)
        """

    def get_session_costs(self) -> CostReport:
        """Get detailed cost breakdown for current session."""
```

#### 3.3.2 Model Configuration

```python
MODEL_CONFIGS = {
    QueryComplexity.SIMPLE: ModelConfig(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=1500,
        cost_input_per_1k=0.00015,
        cost_output_per_1k=0.0006,
        prompt_template="unified_response_simple",
        timeout_seconds=30
    ),
    QueryComplexity.COMPLEX: ModelConfig(
        model="gpt-4o",
        temperature=0.4,
        max_tokens=2500,
        cost_input_per_1k=0.005,
        cost_output_per_1k=0.015,
        prompt_template="tree_of_thoughts",
        timeout_seconds=45
    ),
    QueryComplexity.MULTI_DOMAIN: ModelConfig(
        model="gpt-4o",
        temperature=0.5,
        max_tokens=3500,
        cost_input_per_1k=0.005,
        cost_output_per_1k=0.015,
        prompt_template="tree_of_thoughts_multi_domain",
        timeout_seconds=60
    ),
}

HYDE_CONFIG = ModelConfig(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=400,
    cost_input_per_1k=0.00015,
    cost_output_per_1k=0.0006,
    prompt_template="hyde_conversational",
    timeout_seconds=15
)
```

### 3.4 Action Validator

**File:** `app/services/action_validator.py`

#### 3.4.1 Validation Rules

| Rule | Threshold | Action |
|------|-----------|--------|
| Label length minimum | 8 characters | Reject |
| Label length maximum | 40 characters | Truncate |
| Prompt length minimum | 25 characters | Reject |
| Generic label detection | Exact match list | Reject |
| Forbidden pattern | Regex match | Reject |
| Source grounding | Must reference KB | Warn (log) |
| Valid icon | Enum check | Default to "info" |
| JSON validity | Parse check | Reject malformed |

#### 3.4.2 Forbidden Patterns

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

#### 3.4.3 Validation Output

```python
@dataclass
class ValidationResult:
    is_valid: bool
    rejection_reason: Optional[str]
    warnings: list[str]
    modified_action: Optional[dict]  # If auto-fixed (e.g., icon)

@dataclass
class BatchValidationResult:
    validated_actions: list[dict]
    rejected_count: int
    rejection_log: list[tuple[dict, str]]  # (action, reason)
    quality_score: float  # 0.0-1.0
```

### 3.5 Updated Graph Steps

#### 3.5.1 Step 39b: Conversational HyDE

**Changes:**
- Accept `conversation_history` from state
- Pass last 3 turns to HyDE generator
- Store conversation context awareness flag

```python
async def step_039b__hyde(state: GraphState) -> GraphState:
    """Generate HyDE document with conversation awareness."""

    hyde_doc = await orchestrator.generate_hyde(
        query=state["user_query"],
        conversation_history=state.get("conversation_history", [])
    )

    state["hyde_document"] = hyde_doc
    state["hyde_conversation_aware"] = bool(state.get("conversation_history"))

    return state
```

#### 3.5.2 Step 40: Build Context (Enhanced)

**Changes:**
- Store raw KB documents in state
- Generate source metadata for action grounding
- Preserve document IDs for citation tracking

```python
async def step_040__build_context(state: GraphState) -> GraphState:
    """Build context and preserve full KB documents for action generation."""

    # ... existing retrieval logic ...

    # ✅ NEW: Store raw documents
    state["kb_documents"] = retrieved_docs

    # ✅ NEW: Store formatted context
    state["kb_context_text"] = format_context(retrieved_docs)

    # ✅ NEW: Store metadata for action grounding
    state["kb_sources_metadata"] = [
        {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "type": doc.get("type"),  # circolare, decreto, articolo
            "date": doc.get("date"),
            "url": doc.get("url"),
            "key_topics": extract_topics(doc),
            "key_values": extract_values(doc)  # numbers, dates, rates
        }
        for doc in retrieved_docs
    ]

    return state
```

#### 3.5.3 Step 64: LLM Call (Unified)

**Changes:**
- Add complexity classification
- Route to appropriate model/prompt
- Parse structured JSON output
- Extract reasoning trace

```python
async def step_064__llm_call(state: GraphState) -> GraphState:
    """Generate response using complexity-appropriate model and reasoning."""

    # 1. Classify complexity
    complexity = await orchestrator.classify_complexity(
        query=state["user_query"],
        context=ComplexityContext(
            domains=state.get("detected_domains", []),
            has_history=bool(state.get("conversation_history")),
            has_documents=bool(state.get("user_documents"))
        )
    )
    state["query_complexity"] = complexity.value

    # 2. Generate response with appropriate strategy
    response = await orchestrator.generate_response(
        query=state["user_query"],
        kb_context=state["kb_context_text"],
        kb_sources_metadata=state["kb_sources_metadata"],
        complexity=complexity,
        conversation_history=state.get("conversation_history")
    )

    # 3. Store structured output
    state["reasoning_type"] = "tot" if complexity != QueryComplexity.SIMPLE else "cot"
    state["reasoning_trace"] = response.reasoning

    if response.tot_analysis:
        state["tot_analysis"] = response.tot_analysis

    state["llm_response"] = response.answer
    state["sources_cited"] = response.sources_cited
    state["suggested_actions"] = response.suggested_actions
    state["actions_source"] = "unified_llm"
    state["model_used"] = orchestrator.get_model_for_complexity(complexity)
    state["query_cost_euros"] = orchestrator.get_session_costs().total

    return state
```

#### 3.5.4 Step 100: Action Validation

**Changes:**
- Remove action generation logic (now in Step 64)
- Focus only on validation
- Add fallback for failed unified generation

```python
async def step_100__post_proactivity(state: GraphState) -> GraphState:
    """Validate actions generated in Step 64."""

    actions = state.get("suggested_actions", [])

    # Fallback if unified generation failed
    if state.get("actions_source") == "fallback_needed" or not actions:
        actions = await generate_fallback_actions(
            query=state["user_query"],
            response=state["llm_response"],
            kb_context=state["kb_context_text"],  # ✅ NOW AVAILABLE
            kb_sources=state["kb_sources_metadata"]
        )
        state["actions_source"] = "fallback"

    # Validate
    validation_result = action_validator.validate_batch(
        actions=actions,
        response_text=state["llm_response"],
        kb_sources=state["kb_sources_metadata"]
    )

    state["suggested_actions"] = validation_result.validated_actions
    state["actions_validation_log"] = [
        f"{a.get('label', 'N/A')}: {reason}"
        for a, reason in validation_result.rejection_log
    ]

    return state
```

---

## Part 4: Data Flow Specification

### 4.1 Complete Request Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ REQUEST FLOW                                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ 1. API ENTRY                                                                  │
│    POST /api/chat                                                            │
│    Body: {query, conversation_id, documents[]}                               │
│    │                                                                          │
│    ▼                                                                          │
│ 2. STATE INITIALIZATION                                                       │
│    Load conversation history from DB                                         │
│    Initialize GraphState with user context                                   │
│    │                                                                          │
│    ▼                                                                          │
│ 3. COMPLEXITY CLASSIFICATION (GPT-4o-mini)                                   │
│    Input: query, domains, history_exists, docs_exist                         │
│    Output: simple | complex | multi_domain                                   │
│    Cost: €0.0002 | Latency: ~400ms                                          │
│    │                                                                          │
│    ▼                                                                          │
│ 4. QUERY EXPANSION                                                           │
│    4a. Multi-Query Generation (GPT-4o-mini)                                  │
│        Output: 3 query variants                                              │
│        Cost: €0.0002 | Latency: ~500ms                                      │
│    │                                                                          │
│    4b. Conversational HyDE (GPT-4o-mini)                                     │
│        Input: query + last 3 conversation turns                              │
│        Output: hypothetical document                                         │
│        Cost: €0.0001 | Latency: ~600ms                                      │
│    │                                                                          │
│    ▼                                                                          │
│ 5. RETRIEVAL                                                                  │
│    Hybrid search: BM25 (40%) + Vector (60%)                                  │
│    Input: original query + multi-query + HyDE embedding                      │
│    Output: kb_documents[], kb_sources_metadata[]                             │
│    Latency: ~300ms                                                           │
│    │                                                                          │
│    ▼                                                                          │
│ 6. RESPONSE GENERATION                                                        │
│    ┌─────────────────┬─────────────────┬─────────────────┐                   │
│    │ SIMPLE (70%)    │ COMPLEX (25%)   │ MULTI-DOM (5%)  │                   │
│    │ GPT-4o-mini     │ GPT-4o          │ GPT-4o          │                   │
│    │ Linear CoT      │ Tree of Thoughts│ Parallel ToT    │                   │
│    │ €0.001          │ €0.015          │ €0.020          │                   │
│    │ ~1.5s           │ ~3s             │ ~4s             │                   │
│    └─────────────────┴─────────────────┴─────────────────┘                   │
│    Output: {reasoning, answer, sources, actions}                             │
│    │                                                                          │
│    ▼                                                                          │
│ 7. ACTION VALIDATION                                                          │
│    Apply validation rules                                                     │
│    Log rejections for analysis                                               │
│    Latency: ~10ms                                                            │
│    │                                                                          │
│    ▼                                                                          │
│ 8. RESPONSE FORMATTING                                                        │
│    Assemble final response                                                   │
│    Store in conversation history                                             │
│    Update cost tracking                                                      │
│    │                                                                          │
│    ▼                                                                          │
│ 9. API RESPONSE                                                               │
│    {                                                                          │
│      answer: "...",                                                          │
│      sources: [...],                                                         │
│      suggested_actions: [...],                                               │
│      metadata: {reasoning_type, model_used, cost, latency}                  │
│    }                                                                          │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Error Handling Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ERROR HANDLING                                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ COMPLEXITY CLASSIFICATION FAILURE                                             │
│ └── Default to SIMPLE complexity                                             │
│     └── Continue with GPT-4o-mini                                            │
│                                                                               │
│ HYDE GENERATION FAILURE                                                       │
│ └── Skip HyDE, use only multi-query for retrieval                           │
│     └── Log warning, continue                                                │
│                                                                               │
│ RETRIEVAL FAILURE (No KB docs found)                                         │
│ └── Set kb_context = "Nessun documento trovato nella Knowledge Base"        │
│     └── Continue with LLM call (will use training knowledge)                │
│                                                                               │
│ RESPONSE GENERATION FAILURE                                                   │
│ ├── Timeout (>60s)                                                           │
│ │   └── Retry once with smaller max_tokens                                  │
│ │       └── If still fails, return error response                           │
│ ├── JSON Parse Error                                                         │
│ │   └── Attempt regex extraction of answer                                  │
│ │       └── Set actions_source = "fallback_needed"                          │
│ └── Rate Limit                                                               │
│     └── Wait and retry with exponential backoff                             │
│         └── Max 3 retries, then error response                              │
│                                                                               │
│ ACTION VALIDATION - ALL REJECTED                                              │
│ └── Generate fallback actions WITH kb_context                               │
│     └── Validate fallback actions                                           │
│         └── If still all rejected, return empty actions                     │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 5: API Contracts

### 5.1 Internal Response Schema

```python
@dataclass
class UnifiedResponse:
    """Response from LLM Orchestrator."""

    # Reasoning
    reasoning: dict              # CoT steps or ToT summary
    reasoning_type: str          # "cot" | "tot" | "tot_multi_domain"
    tot_analysis: Optional[dict] # Full ToT if applicable

    # Answer
    answer: str                  # Main response text

    # Sources
    sources_cited: list[dict]    # [{ref, relevance, url}]

    # Actions
    suggested_actions: list[dict]  # [{id, label, icon, prompt, source_basis}]

    # Metadata
    model_used: str
    tokens_input: int
    tokens_output: int
    cost_euros: float
    latency_ms: int


@dataclass
class ComplexityContext:
    """Context for complexity classification."""
    domains: list[str]           # Detected professional domains
    has_history: bool            # Whether conversation has prior turns
    has_documents: bool          # Whether user uploaded documents
```

### 5.2 External API Response

```json
{
  "id": "resp_abc123",
  "conversation_id": "conv_xyz789",
  "answer": "L'aliquota IVA ordinaria è del 22%...",
  "sources": [
    {
      "ref": "Art. 16 DPR 633/72",
      "relevance": "principale",
      "url": "https://..."
    }
  ],
  "suggested_actions": [
    {
      "id": "1",
      "label": "Calcola IVA su 10.000€",
      "icon": "calculator",
      "prompt": "Calcola l'IVA al 22% su un imponibile di 10.000 euro"
    }
  ],
  "metadata": {
    "reasoning_type": "cot",
    "complexity": "simple",
    "model_used": "gpt-4o-mini",
    "cost_euros": 0.0013,
    "latency_ms": 1842,
    "sources_count": 3,
    "actions_validated": 3,
    "actions_rejected": 1
  }
}
```

---

## Part 6: Implementation Phases

### Phase 1: Foundation + Golden Loop (Week 1)

**Goal:** Fix context fragmentation, establish unified output, add action regeneration

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| 1.1 Update GraphState schema | P0 | 2h | None |
| 1.2 Create prompt loader utility | P0 | 3h | None |
| 1.3 Create unified_response_simple.md | P0 | 3h | 1.2 |
| 1.4 Update Step 40 to preserve KB context | P0 | 2h | 1.1 |
| 1.5 Update Step 64 for unified output | P0 | 4h | 1.1, 1.3, 1.4 |
| 1.6 Create action validator | P0 | 3h | None |
| 1.7 Update Step 100 for validation only | P0 | 2h | 1.5, 1.6 |
| 1.8 **NEW:** Implement ActionRegenerator | P0 | 4h | 1.6 |
| 1.9 **NEW:** Create action regeneration prompt | P0 | 2h | 1.2 |
| 1.10 **NEW:** Integrate regeneration loop | P0 | 2h | 1.7, 1.8 |
| 1.11 Integration testing | P0 | 4h | All above |

**Deliverables:**
- Actions generated with KB context
- Unified JSON output format
- Basic CoT reasoning in all responses
- Action validation active
- **NEW:** Golden Loop for action regeneration

**Total Phase 1: ~31 hours**

### Phase 2: Intelligence + Excellence (Week 2)

**Goal:** Implement multi-LLM routing, Tree of Thoughts, source hierarchy, and risk analysis

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| 2.1 Create complexity classifier prompt | P1 | 2h | Phase 1 |
| 2.2 Implement LLMOrchestrator class | P1 | 5h | 2.1 |
| 2.3 Create tree_of_thoughts.md prompt | P1 | 4h | None |
| 2.4 Create tree_of_thoughts_multi_domain.md | P1 | 3h | 2.3 |
| 2.5 Update Step 64 for routing | P1 | 3h | 2.2 |
| 2.6 Implement cost tracking | P1 | 2h | 2.2 |
| 2.7 **NEW:** Create source hierarchy mapping | P0 | 2h | None |
| 2.8 **NEW:** Implement SourceConflictDetector | P0 | 4h | 2.7 |
| 2.9 **NEW:** Update ToT with source weighting | P0 | 2h | 2.3, 2.7 |
| 2.10 **NEW:** Add risk analysis to ToT | P1 | 4h | 2.3 |
| 2.11 **NEW:** Implement risk-aware action generation | P1 | 3h | 2.10 |
| 2.12 **NEW:** Create DualReasoning structures | P1 | 2h | None |
| 2.13 **NEW:** Implement ReasoningTransformer | P1 | 4h | 2.12 |
| 2.14 Integration testing | P1 | 4h | All above |

**Deliverables:**
- Query complexity classification
- Model routing based on complexity
- ToT for complex queries
- Cost tracking per query
- **NEW:** Source hierarchy weighting in ToT
- **NEW:** Conflict detection between sources
- **NEW:** Risk/sanction analysis for hypotheses
- **NEW:** Dual reasoning (internal/public)

**Total Phase 2: ~44 hours**

### Phase 3: Conversation + Grounding (Week 3)

**Goal:** Make HyDE conversation-aware, handle ambiguous queries, add paragraph-level grounding

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| 3.1 Create hyde_conversational.md prompt | P1 | 2h | None |
| 3.2 Update HyDE generator for history | P1 | 2h | 3.1 |
| 3.3 Update Step 39b | P1 | 1h | 3.2 |
| 3.4 Add conversation context to prompts | P2 | 2h | Phase 1 |
| 3.5 **NEW:** Implement QueryAmbiguityDetector | P1 | 3h | None |
| 3.6 **NEW:** Create multi-variant HyDE prompt | P1 | 2h | 3.1 |
| 3.7 **NEW:** Update HyDE for ambiguity handling | P1 | 2h | 3.2, 3.5, 3.6 |
| 3.8 **NEW:** Update source schema for paragraphs | P2 | 3h | Phase 1 |
| 3.9 **NEW:** Implement paragraph extraction | P2 | 4h | 3.8 |
| 3.10 **NEW:** Update action schema with grounding | P2 | 2h | 3.8 |
| 3.11 Testing with multi-turn conversations | P1 | 3h | All above |

**Deliverables:**
- HyDE considers conversation history
- Better follow-up question handling
- Conversation-aware action suggestions
- **NEW:** Self-correcting HyDE for vague queries
- **NEW:** Multi-variant HyDE for ambiguous context
- **NEW:** Paragraph-level source grounding in actions

**Total Phase 3: ~26 hours**

### Phase 4: Quality & Monitoring (Week 4)

**Goal:** Production hardening and observability

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| 4.1 Add detailed logging for reasoning | P2 | 2h | Phase 2 |
| 4.2 Create cost monitoring dashboard | P2 | 4h | 2.6 |
| 4.3 Add action quality metrics | P2 | 3h | 1.6 |
| 4.4 Create prompt A/B testing framework | P3 | 5h | 1.2 |
| 4.5 Performance optimization | P2 | 4h | All phases |
| 4.6 Documentation | P2 | 3h | All phases |

**Deliverables:**
- Cost dashboard
- Quality metrics
- A/B testing capability
- Performance baseline

---

## Part 7: Success Metrics

### 7.1 Quality Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Answer accuracy | 91% | 95%+ | Expert review sampling |
| Action relevance | ~60% | 90%+ | User click-through rate |
| Action specificity | Low | High | Avg prompt length >30 chars |
| Source grounding | Unknown | 95%+ | Actions referencing KB sources |
| JSON parse success | ~70% | 99%+ | Parse error rate |
| **NEW:** Source hierarchy compliance | N/A | 100% | Higher sources override lower |
| **NEW:** Risk flagging accuracy | N/A | 95%+ | High-risk scenarios identified |
| **NEW:** Paragraph-level grounding | N/A | 80%+ | Actions with source_paragraph_id |

### 7.2 Performance Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Simple query latency | ~3s | <2s | P95 response time |
| Complex query latency | ~5s | <5s | P95 response time |
| HyDE generation | ~1s | <800ms | P95 time |
| Action validation | N/A | <50ms | P95 time |
| **NEW:** Action regeneration | N/A | <1.5s | P95 time (when triggered) |
| **NEW:** Conflict detection | N/A | <100ms | P95 time |

### 7.3 Cost Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Cost per query (blended) | €0.0155 | €0.0052 | Average across all queries |
| Simple query cost | €0.0155 | €0.0013 | GPT-4o-mini |
| Complex query cost | €0.0155 | €0.0161 | GPT-4o |
| Monthly cost per user | €23.25 | €7.80 | 50 queries/day |
| **NEW:** Regeneration overhead | N/A | <10% | % queries needing regeneration |

### 7.4 Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Action click-through rate | >30% | Analytics |
| User satisfaction (NPS) | >50 | Survey |
| Support tickets (action quality) | <2/week | Ticket count |
| Conversation depth | >3 turns avg | Analytics |
| **NEW:** Risk warning acknowledgment | >80% | User interaction tracking |
| **NEW:** Alternative scenario exploration | >20% | Users clicking "E se invece" |

### 7.5 Excellence-Specific Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Source conflict detection rate | 100% | All conflicts flagged |
| Dual reasoning availability | 100% | All responses have public explanation |
| Ambiguous query handling | 95%+ | Multi-variant HyDE when needed |
| Golden Loop success rate | >90% | Regeneration produces valid actions |
| Internal reasoning completeness | 100% | All fields populated for debugging |

---

## Part 8: Risk Assessment

### 8.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| JSON parsing failures increase | Medium | High | Structured output mode, fallback parsing |
| GPT-4o latency spikes | Medium | Medium | Timeout handling, user feedback |
| Complexity misclassification | Medium | Medium | Conservative defaults, logging |
| ToT produces verbose output | Low | Medium | Max token limits, truncation |
| Cost tracking inaccuracy | Low | Low | Validation against billing |
| **NEW:** Source hierarchy misapplication | Medium | High | Expert review, comprehensive mapping |
| **NEW:** Risk analysis false positives | Medium | Medium | Calibration with expert feedback |
| **NEW:** Regeneration loop infinite | Low | High | MAX_ATTEMPTS limit, fallback actions |
| **NEW:** Multi-variant HyDE retrieval noise | Medium | Medium | Variant filtering, relevance threshold |

### 8.2 Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Users confused by ToT responses | Medium | Medium | Clear formatting, confidence display |
| Action quality regression | Low | High | Validation, monitoring, rollback |
| Cost exceeds targets | Medium | Medium | Real-time monitoring, alerts |
| **NEW:** Over-warning on risks | Medium | Low | Risk threshold calibration |
| **NEW:** Public reasoning too technical | Medium | Medium | ReasoningTransformer refinement |

### 8.3 Rollback Plan

Each phase should be independently rollbackable:

1. **Phase 1 Rollback:** Revert to XML parsing, remove action validation, disable regeneration loop
2. **Phase 2 Rollback:** Force all queries to SIMPLE complexity, disable source hierarchy
3. **Phase 3 Rollback:** Disable conversation context in HyDE, disable ambiguity detection
4. **NEW Excellence Rollback:**
   - Source hierarchy: Use flat weighting (all sources = 0.7)
   - Risk analysis: Disable risk phase in ToT
   - Dual reasoning: Return only public reasoning
   - Golden Loop: Return empty actions instead of regenerating

---

## Part 9: Testing Strategy

### 9.1 Unit Tests

```python
# test_complexity_classifier.py
def test_simple_query_classification():
    """FAQ-style questions should be SIMPLE."""

def test_complex_query_classification():
    """Multi-step reasoning questions should be COMPLEX."""

def test_multi_domain_classification():
    """Cross-domain questions should be MULTI_DOMAIN."""

# test_action_validator.py
def test_rejects_short_label():
    """Labels <8 chars should be rejected."""

def test_rejects_forbidden_patterns():
    """Patterns like 'consulta commercialista' should be rejected."""

def test_accepts_valid_action():
    """Well-formed actions should pass validation."""

# test_prompt_loader.py
def test_loads_prompt_with_variables():
    """Prompt loader should substitute template variables."""

def test_caches_prompts():
    """Repeated loads should use cache."""

# NEW: test_source_hierarchy.py
def test_source_weighting():
    """Legge should have higher weight than Circolare."""

def test_conflict_detection():
    """Conflicting sources should be flagged."""

def test_hierarchy_in_scoring():
    """Hypothesis with Legge support should score higher."""

# NEW: test_risk_analysis.py
def test_high_risk_flagging():
    """High sanction scenarios should be flagged even if low probability."""

def test_risk_in_actions():
    """High-risk alternatives should generate verification actions."""

# NEW: test_action_regenerator.py
def test_regeneration_triggered():
    """Regeneration should trigger when all actions rejected."""

def test_max_attempts_respected():
    """Should fall back after MAX_ATTEMPTS."""

def test_safe_fallback_generated():
    """Safe fallback actions should be generated after max attempts."""

# NEW: test_reasoning_transformer.py
def test_internal_to_public():
    """Technical reasoning should transform to user-friendly explanation."""

def test_confidence_labels():
    """Numeric confidence should map to Italian labels."""

def test_source_simplification():
    """Detailed source refs should simplify for users."""

# NEW: test_ambiguity_detector.py
def test_short_query_detected():
    """Queries <5 words should be flagged as ambiguous."""

def test_pronoun_without_antecedent():
    """Queries with pronouns and no history should be ambiguous."""

def test_multi_variant_hyde_triggered():
    """Ambiguous queries should trigger multi-variant HyDE."""
```

### 9.2 Integration Tests

```python
# test_response_flow.py
def test_simple_query_uses_mini_model():
    """Simple queries should route to GPT-4o-mini."""

def test_complex_query_produces_tot():
    """Complex queries should have tot_analysis in response."""

def test_actions_reference_kb_sources():
    """Generated actions should reference KB source metadata."""

def test_conversation_aware_hyde():
    """Follow-up questions should produce relevant HyDE."""

# NEW: test_excellence_flow.py
def test_source_hierarchy_in_tot():
    """ToT should weight hypotheses by source quality."""

def test_risk_analysis_in_tot():
    """ToT should include risk analysis for each hypothesis."""

def test_conflict_flagged_in_response():
    """Source conflicts should appear in reasoning."""

def test_dual_reasoning_in_response():
    """Response should have both internal and public reasoning."""

def test_regeneration_loop():
    """Invalid actions should trigger regeneration."""

def test_paragraph_grounding():
    """Actions should include source_paragraph_id."""

def test_ambiguous_query_multi_variant():
    """Vague follow-ups should use multi-variant HyDE."""
```

### 9.3 Quality Tests (Manual/Sampling)

| Test Case | Expected Behavior |
|-----------|-------------------|
| "Qual è l'aliquota IVA ordinaria?" | SIMPLE, CoT, actions reference Art. 16 |
| "Come fatturare a azienda tedesca?" | COMPLEX, ToT with 3 hypotheses |
| "Assumo dipendente che apre P.IVA" | MULTI_DOMAIN, labor + tax analysis |
| Follow-up: "E se è part-time?" | HyDE references previous context |
| **NEW:** "E per l'IVA?" (vague) | Multi-variant HyDE, covers B2B/B2C/Extra-UE |
| **NEW:** Circolare vs Legge conflict | Legge weighted higher, conflict flagged |
| **NEW:** High-risk low-probability | Risk warning in response, verification action |
| **NEW:** All actions rejected | Regeneration triggered, valid actions produced |

### 9.4 Excellence-Specific Test Scenarios

#### Scenario 1: Source Hierarchy
```
Query: "Posso dedurre le spese di rappresentanza?"

Expected:
- ToT identifies: Art. 108 TUIR (Legge) + Circolare 34/E interpretation
- Source weighting: Art. 108 = 1.0, Circolare = 0.6
- If conflict: Legge prevails, conflict noted in reasoning
- Actions reference specific comma of Art. 108
```

#### Scenario 2: Risk Analysis
```
Query: "Come gestisco una fattura senza dati del cliente?"

Expected:
- Hypothesis A: Errore formale sanabile (prob: 0.7, risk: LOW)
- Hypothesis B: Fattura irregolare (prob: 0.2, risk: HIGH)
- Hypothesis C: Operazione inesistente (prob: 0.1, risk: CRITICAL)
- Even with low probability, B and C flagged in response
- Actions include: "Verifica che non sia operazione inesistente"
```

#### Scenario 3: Ambiguous Query
```
Conversation:
- User: "Quanto costa assumere un dipendente?"
- Assistant: [risposta su costi]
- User: "E per l'IVA?"

Expected:
- AmbiguityDetector: is_ambiguous=True (generic follow-up)
- HyDE: Multi-variant covering IVA su lavoro/IVA su acquisti/IVA su servizi
- Response asks for clarification or covers multiple scenarios
```

#### Scenario 4: Golden Loop
```
Query: "Calcola l'IRPEF su 50.000€"

Step 64 produces actions:
- "Calcola" (rejected: too short)
- "Verifica sul sito AdE" (rejected: forbidden pattern)
- "Approfondisci" (rejected: generic)

Expected:
- Regeneration triggered with correction prompt
- New actions reference: "scaglioni IRPEF 2024", "€50.000"
- Validated actions returned
```

---

## Part 10: Glossary

| Term | Definition |
|------|------------|
| **CoT** | Chain of Thought - Linear step-by-step reasoning |
| **ToT** | Tree of Thoughts - Parallel hypothesis exploration |
| **HyDE** | Hypothetical Document Embeddings - Generate fake doc for retrieval |
| **KB** | Knowledge Base - Italian regulatory documents |
| **Unified Output** | Single JSON schema for all response types |
| **Action Grounding** | Actions based on KB sources, not just answer text |
| **Complexity Routing** | Directing queries to appropriate models |

---

## Appendix A: Prompt Templates Reference

### A.1 Complexity Classifier Prompt

```markdown
Classifica questa query fiscale italiana:

QUERY: {query}

CONTESTO:
- Domini rilevati: {domains}
- Conversazione precedente: {has_history}
- Documenti utente: {has_documents}

CATEGORIE:
- simple: Domanda singola, risposta diretta
- complex: Ragionamento multi-step, casi specifici
- multi_domain: Coinvolge più domini professionali

Output JSON: {"complexity": "...", "reasoning": "..."}
```

### A.2 Action Examples by Domain

```markdown
### TAX Example
Query: "Acconto IVA dicembre"
Actions:
- "Calcola acconto 88% su €15.000" (calculator)
- "Codice tributo F24" (search)
- "Casi esonero acconto" (info)

### LABOR Example
Query: "Costo apprendista"
Actions:
- "Calcola costo su RAL €22.000" (calculator)
- "Ore formazione obbligatorie" (info)
- "Confronto costo dipendente" (calculator)

### LEGAL Example
Query: "Termini ricorso cartella"
Actions:
- "Calcola scadenza da notifica 15/01" (calendar)
- "Motivi impugnazione vizi formali" (search)
- "Costi contributo unificato" (euro)
```

---

## Appendix B: Migration Checklist

### Pre-Migration
- [ ] Backup current prompts
- [ ] Document current action quality baseline
- [ ] Set up monitoring for new metrics
- [ ] Prepare rollback scripts
- [ ] **NEW:** Document current source citation patterns
- [ ] **NEW:** Baseline risk detection accuracy

### Phase 1 Migration (Foundation + Golden Loop)
- [ ] Deploy new GraphState schema
- [ ] Deploy prompt loader
- [ ] Deploy unified_response_simple.md
- [ ] Update Step 40
- [ ] Update Step 64
- [ ] Deploy action validator
- [ ] Update Step 100
- [ ] **NEW:** Deploy ActionRegenerator
- [ ] **NEW:** Deploy action regeneration prompt
- [ ] **NEW:** Integrate Golden Loop
- [ ] Run integration tests
- [ ] Monitor for 24h
- [ ] **NEW:** Track regeneration trigger rate

### Phase 2 Migration (Intelligence + Excellence)
- [ ] Deploy complexity classifier
- [ ] Deploy LLMOrchestrator
- [ ] Deploy ToT prompts
- [ ] Update routing logic
- [ ] **NEW:** Deploy source hierarchy mapping
- [ ] **NEW:** Deploy SourceConflictDetector
- [ ] **NEW:** Update ToT with source weighting
- [ ] **NEW:** Deploy risk analysis phase
- [ ] **NEW:** Deploy DualReasoning structures
- [ ] **NEW:** Deploy ReasoningTransformer
- [ ] Run integration tests
- [ ] Monitor costs for 48h
- [ ] **NEW:** Validate source hierarchy correctness
- [ ] **NEW:** Review risk flagging accuracy

### Phase 3 Migration (Conversation + Grounding)
- [ ] Deploy conversational HyDE
- [ ] Update Step 39b
- [ ] **NEW:** Deploy QueryAmbiguityDetector
- [ ] **NEW:** Deploy multi-variant HyDE prompt
- [ ] **NEW:** Deploy paragraph-level grounding
- [ ] Test multi-turn conversations
- [ ] **NEW:** Test ambiguous query handling
- [ ] Monitor for 24h

### Phase 4 Migration (UI + Quality)
- [ ] Deploy UI loading states
- [ ] Deploy reasoning display components
- [ ] Deploy action grouping
- [ ] Deploy alternative scenario labels
- [ ] Accessibility audit
- [ ] Performance optimization

### Post-Migration
- [ ] Compare quality metrics to baseline
- [ ] Compare cost metrics to targets
- [ ] Gather user feedback
- [ ] Document lessons learned
- [ ] **NEW:** Validate source hierarchy compliance rate
- [ ] **NEW:** Review risk analysis effectiveness
- [ ] **NEW:** Assess regeneration loop efficiency
- [ ] **NEW:** Evaluate public reasoning clarity

### Excellence Validation Checklist
- [ ] Source hierarchy: Legge > Circolare in all ToT responses
- [ ] Conflict detection: 100% of known conflicts flagged
- [ ] Risk analysis: All HIGH/CRITICAL risks surfaced
- [ ] Dual reasoning: All responses have public explanation
- [ ] Golden Loop: <10% queries need regeneration
- [ ] Paragraph grounding: >80% actions have source_paragraph_id
- [ ] Ambiguity handling: Multi-variant HyDE for vague queries

---

## Part 11: Excellence Refinements

### 11.1 Source Hierarchy Weighting (Gerarchia delle Fonti)

In Italian fiscal law, source hierarchy is paramount. A Circolare interpretation can be overruled by a subsequent Legge. The ToT process must explicitly weight sources.

#### 11.1.1 Italian Legal Source Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GERARCHIA DELLE FONTI ITALIANE (Peso Decrescente)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LIVELLO 1 - FONTI PRIMARIE (weight: 1.0)                                   │
│  ├── Costituzione                                                           │
│  ├── Leggi ordinarie (L.)                                                   │
│  ├── Decreti Legislativi (D.Lgs.)                                          │
│  ├── Decreti Legge (D.L.) convertiti                                       │
│  └── DPR (Decreti del Presidente della Repubblica)                         │
│                                                                              │
│  LIVELLO 2 - FONTI SECONDARIE (weight: 0.8)                                 │
│  ├── Decreti Ministeriali (D.M.)                                           │
│  ├── Regolamenti UE (direttamente applicabili)                             │
│  └── Direttive UE (recepite)                                               │
│                                                                              │
│  LIVELLO 3 - PRASSI AMMINISTRATIVA (weight: 0.6)                            │
│  ├── Circolari Agenzia delle Entrate                                       │
│  ├── Risoluzioni Agenzia delle Entrate                                     │
│  ├── Provvedimenti del Direttore                                           │
│  └── Circolari INPS/INAIL                                                  │
│                                                                              │
│  LIVELLO 4 - INTERPRETAZIONI (weight: 0.4)                                  │
│  ├── Interpelli (risposta a istanza specifica)                             │
│  ├── Principi di diritto                                                   │
│  └── FAQ ufficiali                                                         │
│                                                                              │
│  LIVELLO 5 - GIURISPRUDENZA (weight: 0.5-0.9 based on court)               │
│  ├── Corte di Cassazione (0.9)                                             │
│  ├── Corte Costituzionale (1.0)                                            │
│  ├── Corte di Giustizia UE (0.95)                                          │
│  └── Commissioni Tributarie (0.5)                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 11.1.2 Source Weighting in ToT Prompt

**Add to `tree_of_thoughts.md`:**

```markdown
### FASE 1.5: Pesatura delle Fonti

Per ogni ipotesi, valuta la QUALITÀ delle fonti che la supportano:

<source_weighting>
IPOTESI A:
- Fonti primarie (Leggi, DPR, D.Lgs.): [lista]
- Fonti secondarie (D.M., Reg. UE): [lista]
- Prassi (Circolari, Risoluzioni): [lista]
- Peso complessivo fonti: [0.0-1.0]

IPOTESI B:
- Fonti primarie: [lista]
- Fonti secondarie: [lista]
- Prassi: [lista]
- Peso complessivo fonti: [0.0-1.0]

CONFLITTI RILEVATI:
- [Se una Circolare contraddice una Legge successiva, segnalarlo]
- [Se prassi consolidata vs nuova norma, segnalarlo]

REGOLA: A parità di probabilità, preferire l'ipotesi con fonti di livello superiore.
</source_weighting>
```

#### 11.1.3 Conflict Detection Rules

```python
# app/services/source_conflict_detector.py

class SourceConflictDetector:
    """Detects conflicts between sources of different hierarchy levels."""

    SOURCE_HIERARCHY = {
        # Level 1 - Primary
        "legge": 1.0,
        "decreto_legislativo": 1.0,
        "dpr": 1.0,
        "decreto_legge": 1.0,

        # Level 2 - Secondary
        "decreto_ministeriale": 0.8,
        "regolamento_ue": 0.8,

        # Level 3 - Administrative Practice
        "circolare": 0.6,
        "risoluzione": 0.6,
        "provvedimento": 0.6,

        # Level 4 - Interpretations
        "interpello": 0.4,
        "faq": 0.4,

        # Level 5 - Case Law
        "cassazione": 0.9,
        "corte_costituzionale": 1.0,
        "cgue": 0.95,
        "ctp_ctr": 0.5,
    }

    def detect_conflicts(
        self,
        sources: list[dict]
    ) -> list[SourceConflict]:
        """
        Detect conflicts where lower-hierarchy sources contradict higher ones.

        Returns list of conflicts with:
        - conflicting_sources: The two sources in conflict
        - conflict_type: "superseded" | "contradictory" | "temporal"
        - recommendation: Which source should prevail
        """
        conflicts = []

        # Sort by date (newest first) and hierarchy
        sorted_sources = sorted(
            sources,
            key=lambda s: (s.get("date", ""), -self.SOURCE_HIERARCHY.get(s["type"], 0.5)),
            reverse=True
        )

        for i, source_a in enumerate(sorted_sources):
            for source_b in sorted_sources[i+1:]:
                if self._are_conflicting(source_a, source_b):
                    conflicts.append(SourceConflict(
                        higher_source=source_a if self._get_weight(source_a) > self._get_weight(source_b) else source_b,
                        lower_source=source_b if self._get_weight(source_a) > self._get_weight(source_b) else source_a,
                        conflict_type=self._classify_conflict(source_a, source_b),
                        recommendation=self._get_recommendation(source_a, source_b)
                    ))

        return conflicts

    def calculate_hypothesis_source_weight(
        self,
        hypothesis_sources: list[dict]
    ) -> float:
        """
        Calculate weighted score for hypothesis based on source quality.
        """
        if not hypothesis_sources:
            return 0.0

        weights = [
            self.SOURCE_HIERARCHY.get(s.get("type", ""), 0.5)
            for s in hypothesis_sources
        ]

        # Highest weight source matters most (60%) + average (40%)
        max_weight = max(weights)
        avg_weight = sum(weights) / len(weights)

        return (max_weight * 0.6) + (avg_weight * 0.4)
```

#### 11.1.4 Updated ToT Scoring Formula

```
Final Hypothesis Score =
    (Probability Score × 0.4) +
    (Source Weight × 0.4) +
    (Risk Adjustment × 0.2)

Where:
- Probability Score: How likely this scenario given query context (0.0-1.0)
- Source Weight: Quality of supporting sources (0.0-1.0)
- Risk Adjustment: Inverse of sanction risk (0.0-1.0, see 11.2)
```

---

### 11.2 Risk/Sanction Analysis (Analisi Rischio)

Even low-probability scenarios must be flagged if they carry high sanction risk.

#### 11.2.1 Risk Categories

| Risk Level | Sanction Range | Examples |
|------------|----------------|----------|
| **CRITICAL** | >100% of tax + criminal | Frode fiscale, falsa fatturazione |
| **HIGH** | 90-180% of tax | Omessa dichiarazione, infedele dichiarazione |
| **MEDIUM** | 30-90% of tax | Errori formali con impatto sostanziale |
| **LOW** | 0-30% of tax | Ritardi, errori formali minori |

#### 11.2.2 ToT Risk Analysis Phase

**Add to `tree_of_thoughts.md` after Fase 1.5:**

```markdown
### FASE 1.6: Analisi del Rischio Sanzionatorio

Per ogni ipotesi, valuta il RISCHIO se applicata erroneamente:

<risk_analysis>
IPOTESI A (score probabilità: 0.75):
- Rischio se errata: [LOW/MEDIUM/HIGH/CRITICAL]
- Sanzione potenziale: [descrizione e % ]
- Riferimento normativo sanzione: [Art. X D.Lgs. 472/97]
- Azione di mitigazione: [cosa fare per ridurre il rischio]

IPOTESI B (score probabilità: 0.15):
- Rischio se errata: [HIGH]
- Sanzione potenziale: [90-180% dell'imposta]
- Riferimento normativo sanzione: [Art. 1 D.Lgs. 471/97]
- Azione di mitigazione: [verifica preventiva VIES]

REGOLA CRITICA:
Se un'ipotesi ha probabilità bassa (<0.3) MA rischio CRITICAL o HIGH,
DEVE essere menzionata nella risposta come "scenario da escludere con certezza"
e generare un'azione suggerita di verifica.
</risk_analysis>
```

#### 11.2.3 Risk-Adjusted Action Generation

```python
# When generating actions, prioritize risk mitigation

def generate_risk_aware_actions(
    hypotheses: list[Hypothesis],
    selected: Hypothesis
) -> list[SuggestedAction]:
    actions = []

    # Primary actions for selected hypothesis
    actions.extend(generate_primary_actions(selected))

    # Risk mitigation actions for high-risk alternatives
    for hyp in hypotheses:
        if hyp.id != selected.id:
            if hyp.risk_level in ["CRITICAL", "HIGH"] and hyp.probability > 0.1:
                actions.append(SuggestedAction(
                    label=f"Escludi scenario: {hyp.short_label}",
                    prompt=f"Come verificare che NON si applichi {hyp.scenario}?",
                    actionType="risk",
                    icon="warning",
                    hypothesisRelated=hyp.id,
                    riskContext={
                        "risk_level": hyp.risk_level,
                        "potential_sanction": hyp.sanction_description,
                        "mitigation": hyp.mitigation_action
                    }
                ))

    return actions
```

---

### 11.3 Self-Correction HyDE (Query Vaghe)

When user queries are ambiguous, HyDE must not hallucinate specifics.

#### 11.3.1 Query Ambiguity Detection

```python
# app/services/query_analyzer.py

class QueryAmbiguityDetector:
    """Detect when a query is too vague for specific HyDE generation."""

    AMBIGUITY_INDICATORS = [
        # Very short follow-ups
        lambda q: len(q.split()) < 5,

        # Pronouns without clear antecedent
        lambda q: any(p in q.lower() for p in ["questo", "quello", "lo stesso", "anche"]),

        # Generic questions
        lambda q: q.lower().startswith(("e per", "e se", "invece", "anche")),

        # Missing key fiscal elements
        lambda q: not any(term in q.lower() for term in [
            "iva", "irpef", "inps", "fattura", "contribut", "imposta",
            "aliquota", "deduz", "detraz", "scadenz"
        ]),
    ]

    def analyze(self, query: str, conversation_history: list) -> AmbiguityResult:
        """
        Analyze query ambiguity level.

        Returns:
            AmbiguityResult with:
            - is_ambiguous: bool
            - ambiguity_type: "short" | "pronoun" | "generic" | "missing_context"
            - suggested_strategy: "multi_variant" | "clarification" | "standard"
        """
        ambiguity_score = sum(
            1 for indicator in self.AMBIGUITY_INDICATORS
            if indicator(query)
        )

        if ambiguity_score >= 2:
            return AmbiguityResult(
                is_ambiguous=True,
                ambiguity_type=self._classify_ambiguity(query),
                suggested_strategy="multi_variant"
            )

        return AmbiguityResult(
            is_ambiguous=False,
            suggested_strategy="standard"
        )
```

#### 11.3.2 Multi-Variant HyDE for Ambiguous Queries

**Add to `hyde_conversational.md`:**

```markdown
## Gestione Query Ambigue

Se la query è breve o vaga (es: "E per l'IVA?", "Anche questo?"):

NON inventare dettagli specifici. Invece, genera un documento ipotetico
che ESPLORI MULTIPLE VARIANTI:

### Esempio Query Vaga

Query: "E per l'IVA?"
Contesto: Conversazione precedente su fatturazione a cliente estero

### Documento Ipotetico Multi-Variante (CORRETTO)

```
La disciplina IVA nelle operazioni con l'estero varia significativamente
in base alla natura del cliente e dell'operazione:

SCENARIO B2B (cliente con P.IVA): Per le prestazioni di servizi verso
soggetti passivi UE, si applica l'art. 7-ter DPR 633/72 con regime di
non imponibilità e reverse charge...

SCENARIO B2C (cliente privato): Per le prestazioni verso privati
consumatori, si applicano le regole del luogo di stabilimento del
prestatore o il regime OSS per e-commerce...

SCENARIO EXTRA-UE: Per operazioni con paesi terzi, la territorialità
segue criteri specifici con possibile non imponibilità ex art. 9...
```

### Documento Ipotetico Specifico (SBAGLIATO - da evitare)

```
L'IVA per la fatturazione verso la società tedesca XYZ GmbH con P.IVA
DE123456789 si applica con reverse charge al 22%...
← ERRORE: Ha inventato dettagli non forniti dall'utente
```

## Output Flag

Se generi un documento multi-variante, segnalalo:

{
  "hyde_document": "...",
  "hyde_type": "multi_variant",  // vs "specific"
  "variants_covered": ["B2B_UE", "B2C_UE", "EXTRA_UE"]
}
```

#### 11.3.3 Updated HyDE Generator

```python
# app/services/hyde_generator.py

class ConversationalHyDEGenerator:

    async def generate(
        self,
        query: str,
        conversation_history: list[dict] = None
    ) -> HyDEResult:

        # Check for ambiguity
        ambiguity = self.ambiguity_detector.analyze(query, conversation_history)

        if ambiguity.is_ambiguous and ambiguity.suggested_strategy == "multi_variant":
            return await self._generate_multi_variant_hyde(
                query,
                conversation_history,
                ambiguity.ambiguity_type
            )

        return await self._generate_standard_hyde(query, conversation_history)

    async def _generate_multi_variant_hyde(
        self,
        query: str,
        history: list,
        ambiguity_type: str
    ) -> HyDEResult:
        """Generate HyDE that explores multiple scenarios without hallucinating."""

        prompt = load_prompt(
            "hyde_multi_variant",
            query=query,
            conversation_context=self._format_history(history),
            ambiguity_type=ambiguity_type
        )

        response = await self.llm_client.chat_completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        return HyDEResult(
            document=response.content,
            hyde_type="multi_variant",
            variants_covered=self._extract_variants(response.content)
        )
```

---

### 11.4 Internal vs Public Reasoning

The reasoning trace serves two purposes that require different formats.

#### 11.4.1 Dual Reasoning Structure

```python
@dataclass
class DualReasoning:
    """Separate internal and public reasoning representations."""

    # For debugging, logging, quality analysis
    internal_reasoning: InternalReasoning

    # For user display
    public_explanation: PublicExplanation


@dataclass
class InternalReasoning:
    """Technical reasoning for developers and debugging."""

    # Raw ToT/CoT trace
    raw_trace: dict

    # Detailed hypothesis analysis
    hypotheses_full: list[dict]  # All scores, all sources, all calculations

    # Source conflict details
    conflicts_detected: list[SourceConflict]

    # Model metadata
    model_used: str
    tokens_consumed: int
    latency_ms: int

    # Quality signals
    confidence_calibration: float  # How confident vs how correct historically
    source_coverage: float  # % of relevant KB docs used


@dataclass
class PublicExplanation:
    """User-friendly explanation of the reasoning."""

    # Simple summary
    summary: str  # "Ho analizzato 3 possibili scenari..."

    # Selected scenario explanation
    selected_scenario: str  # "Lo scenario più probabile è..."
    why_selected: str  # "...perché la tua domanda menziona 'azienda'"

    # Key sources (simplified)
    main_sources: list[str]  # ["Art. 7-ter DPR 633/72", "Circolare 37/E"]

    # Confidence (human-readable)
    confidence_label: str  # "alta probabilità" | "probabile" | "da verificare"

    # Alternative notice (if relevant)
    alternative_notice: Optional[str]  # "Se invece il cliente non ha P.IVA..."

    # Risk warning (if any high-risk alternatives)
    risk_warning: Optional[str]  # "Attenzione: verifica che non si applichi..."
```

#### 11.4.2 Reasoning Transformation Rules

```python
# app/services/reasoning_transformer.py

class ReasoningTransformer:
    """Transform internal reasoning to user-friendly explanation."""

    CONFIDENCE_LABELS = {
        (0.9, 1.0): "alta probabilità",
        (0.7, 0.9): "probabile",
        (0.5, 0.7): "possibile",
        (0.3, 0.5): "incerto - da verificare",
        (0.0, 0.3): "poco probabile"
    }

    def transform(self, internal: InternalReasoning) -> PublicExplanation:
        """
        Transform technical reasoning to professional explanation.

        Rules:
        1. Never mention model names or technical terms
        2. Use professional Italian fiscal language
        3. Focus on WHAT was decided, not HOW the model works
        4. Highlight actionable insights, not process details
        """

        selected = self._get_selected_hypothesis(internal)
        alternatives = self._get_significant_alternatives(internal)

        # Build summary
        if len(internal.hypotheses_full) > 1:
            summary = f"Ho analizzato {len(internal.hypotheses_full)} possibili scenari normativi."
        else:
            summary = "Ho verificato la normativa applicabile."

        # Build selection explanation
        why_selected = self._generate_selection_reason(
            selected,
            internal.raw_trace.get("selection_reasoning", "")
        )

        # Simplify sources
        main_sources = self._simplify_sources(selected.get("sources", []))

        # Generate confidence label
        confidence_label = self._get_confidence_label(selected.get("score", 0.5))

        # Generate alternative notice (if significant alternatives exist)
        alternative_notice = None
        if alternatives:
            best_alt = alternatives[0]
            alternative_notice = self._generate_alternative_notice(best_alt)

        # Generate risk warning (if high-risk alternatives)
        risk_warning = None
        high_risk_alts = [a for a in alternatives if a.get("risk_level") in ["HIGH", "CRITICAL"]]
        if high_risk_alts:
            risk_warning = self._generate_risk_warning(high_risk_alts[0])

        return PublicExplanation(
            summary=summary,
            selected_scenario=selected.get("scenario", ""),
            why_selected=why_selected,
            main_sources=main_sources,
            confidence_label=confidence_label,
            alternative_notice=alternative_notice,
            risk_warning=risk_warning
        )

    def _generate_selection_reason(self, selected: dict, raw_reasoning: str) -> str:
        """
        Transform technical reasoning to user-friendly explanation.

        INTERNAL: "Hypothesis A selected with score 0.75 based on
                   keyword match 'azienda' indicating B2B context"

        PUBLIC:  "Ho scelto questo scenario perché dalla tua domanda
                  emerge che il cliente è un'azienda (soggetto B2B)."
        """
        # Template-based transformation
        templates = {
            "b2b_indicator": "dalla tua domanda emerge che il cliente è un'azienda (soggetto B2B)",
            "b2c_indicator": "il contesto suggerisce un cliente privato (consumatore finale)",
            "eu_indicator": "l'operazione riguarda un paese UE",
            "extra_eu_indicator": "l'operazione coinvolge un paese extra-UE",
        }

        # Match indicators in raw reasoning and select appropriate template
        reason_parts = []
        for key, template in templates.items():
            if key.replace("_indicator", "") in raw_reasoning.lower():
                reason_parts.append(template)

        if reason_parts:
            return f"Ho scelto questo scenario perché {', e '.join(reason_parts)}."

        return "Ho scelto questo scenario in base al contesto della tua domanda."

    def _simplify_sources(self, sources: list) -> list[str]:
        """
        Simplify source references for user display.

        INTERNAL: {"type": "circolare", "number": "37/E", "date": "2011-08-09",
                   "issuer": "Agenzia delle Entrate", "section": "par. 2.3"}

        PUBLIC:  "Circolare 37/E del 2011"
        """
        simplified = []
        for source in sources[:3]:  # Max 3 sources for user
            source_type = source.get("type", "").replace("_", " ").title()
            number = source.get("number", "")
            year = source.get("date", "")[:4] if source.get("date") else ""

            if number and year:
                simplified.append(f"{source_type} {number} del {year}")
            elif number:
                simplified.append(f"{source_type} {number}")

        return simplified
```

#### 11.4.3 API Response with Dual Reasoning

```json
{
  "answer": "...",
  "sources": [...],
  "suggested_actions": [...],

  "reasoning": {
    "public": {
      "summary": "Ho analizzato 3 possibili scenari normativi.",
      "selected_scenario": "Operazione B2B intracomunitaria",
      "why_selected": "Ho scelto questo scenario perché dalla tua domanda emerge che il cliente è un'azienda (soggetto B2B).",
      "main_sources": ["Art. 7-ter DPR 633/72", "Circolare 37/E del 2011"],
      "confidence_label": "alta probabilità",
      "alternative_notice": "Se invece il cliente non ha partita IVA comunitaria valida, la procedura cambia.",
      "risk_warning": null
    },

    "internal": {
      "_note": "Available only in debug mode or admin API",
      "raw_trace": {...},
      "hypotheses_full": [...],
      "model_used": "gpt-4o",
      "tokens_consumed": 2847,
      "latency_ms": 3421
    }
  }
}
```

---

### 11.5 Action Regeneration Loop (Golden Loop)

When Action Validator rejects all proposed actions, trigger regeneration.

#### 11.5.1 Regeneration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ACTION VALIDATION & REGENERATION FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 64: Generate Response                                                  │
│      │                                                                       │
│      │ Output: {answer, actions[4]}                                         │
│      ▼                                                                       │
│  Step 100: Validate Actions                                                  │
│      │                                                                       │
│      ├── All valid? ──────────────► Return response                         │
│      │                                                                       │
│      ├── Some valid (≥2)? ────────► Return with valid subset                │
│      │                                                                       │
│      └── All rejected OR <2 valid?                                          │
│              │                                                               │
│              ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │  REGENERATION TRIGGER                                       │            │
│  │                                                             │            │
│  │  IF regeneration_attempts < MAX_ATTEMPTS (2):               │            │
│  │      │                                                      │            │
│  │      ▼                                                      │            │
│  │  Generate correction prompt:                                │            │
│  │  "Le azioni precedenti sono state scartate perché:         │            │
│  │   - {rejection_reason_1}                                   │            │
│  │   - {rejection_reason_2}                                   │            │
│  │                                                             │            │
│  │   Rigenera 3 azioni basandoti STRETTAMENTE su:             │            │
│  │   - Fonte principale: {main_source_cited}                  │            │
│  │   - Valori specifici dalla risposta: {extracted_values}    │            │
│  │   - Paragrafo chiave: {source_paragraph}"                  │            │
│  │      │                                                      │            │
│  │      ▼                                                      │            │
│  │  LLM Call (GPT-4o-mini for speed)                          │            │
│  │      │                                                      │            │
│  │      ▼                                                      │            │
│  │  Validate again ──► Loop back if still invalid             │            │
│  │                                                             │            │
│  │  ELSE (max attempts reached):                               │            │
│  │      │                                                      │            │
│  │      ▼                                                      │            │
│  │  Generate SAFE FALLBACK actions:                           │            │
│  │  - "Approfondisci {main_topic}"                            │            │
│  │  - "Calcola {if numbers in response}"                      │            │
│  │  - "Verifica scadenze correlate"                           │            │
│  │                                                             │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 11.5.2 Regeneration Prompt

```markdown
## Correzione Azioni Suggerite

Le azioni precedenti sono state scartate per i seguenti motivi:
{rejection_reasons}

### Elementi da utilizzare OBBLIGATORIAMENTE

Fonte principale citata nella risposta:
{main_source_ref}

Paragrafo rilevante dalla fonte:
"{source_paragraph_text}"

Valori specifici menzionati:
{extracted_values}  // es: "22%", "16 marzo", "€15.000"

### Genera 3 nuove azioni

Ogni azione DEVE:
1. Riferirsi esplicitamente alla fonte sopra indicata
2. Includere almeno uno dei valori specifici
3. Essere un prompt completo e autosufficiente (>25 caratteri)

### Output (JSON)

[
  {"id": "1", "label": "...", "icon": "...", "prompt": "...", "source_basis": "..."},
  {"id": "2", "label": "...", "icon": "...", "prompt": "...", "source_basis": "..."},
  {"id": "3", "label": "...", "icon": "...", "prompt": "...", "source_basis": "..."}
]
```

#### 11.5.3 Implementation

```python
# app/services/action_regenerator.py

class ActionRegenerator:
    """Regenerate actions when validation fails."""

    MAX_ATTEMPTS = 2

    async def regenerate_if_needed(
        self,
        original_actions: list[dict],
        validation_result: BatchValidationResult,
        response_context: ResponseContext
    ) -> list[dict]:
        """
        Attempt to regenerate actions if too many were rejected.

        Args:
            original_actions: Actions from Step 64
            validation_result: Validation results with rejection reasons
            response_context: Contains answer, sources, extracted values

        Returns:
            List of valid actions (regenerated if necessary)
        """

        # If enough valid actions, return them
        if len(validation_result.validated_actions) >= 2:
            return validation_result.validated_actions

        # Attempt regeneration
        for attempt in range(self.MAX_ATTEMPTS):
            regenerated = await self._attempt_regeneration(
                attempt=attempt,
                rejection_reasons=validation_result.rejection_log,
                context=response_context
            )

            # Validate regenerated actions
            reval_result = action_validator.validate_batch(
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

        prompt = load_prompt(
            "action_regeneration",
            rejection_reasons=self._format_rejections(rejection_reasons),
            main_source_ref=context.primary_source.get("ref", ""),
            source_paragraph_text=context.primary_source.get("relevant_paragraph", "")[:500],
            extracted_values=", ".join(context.extracted_values)
        )

        response = await self.llm_client.chat_completion(
            model="gpt-4o-mini",  # Fast model for regeneration
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        return json.loads(response.content)

    def _generate_safe_fallback(self, context: ResponseContext) -> list[dict]:
        """Generate minimal safe actions when regeneration fails."""

        actions = []

        # Topic-based action
        if context.main_topic:
            actions.append({
                "id": "1",
                "label": f"Approfondisci {context.main_topic[:20]}",
                "icon": "search",
                "prompt": f"Dimmi di più su {context.main_topic}",
                "source_basis": "topic_fallback"
            })

        # Calculation action if numbers present
        if context.extracted_values:
            first_value = context.extracted_values[0]
            actions.append({
                "id": "2",
                "label": f"Calcolo su {first_value}",
                "icon": "calculator",
                "prompt": f"Esegui un calcolo pratico considerando {first_value}",
                "source_basis": "value_fallback"
            })

        # Generic deadline action
        actions.append({
            "id": "3",
            "label": "Verifica scadenze",
            "icon": "calendar",
            "prompt": "Quali sono le scadenze rilevanti per questa situazione?",
            "source_basis": "deadline_fallback"
        })

        return actions[:3]
```

---

### 11.6 Enhanced Source Grounding (Paragraph-Level)

Actions should reference specific paragraphs, not just documents.

#### 11.6.1 Source Paragraph Tracking

```python
@dataclass
class EnhancedSource:
    """Source with paragraph-level granularity."""

    # Document-level
    doc_id: str
    doc_type: str  # legge, circolare, etc.
    doc_ref: str   # "Circolare 37/E del 2011"
    doc_url: Optional[str]

    # Paragraph-level
    paragraph_id: str  # "par_2_3"
    paragraph_number: str  # "2.3"
    paragraph_title: Optional[str]  # "Prestazioni di servizi B2B"
    paragraph_text: str  # Actual text (truncated)

    # Relevance
    relevance_score: float
    matched_query_terms: list[str]
```

#### 11.6.2 Updated Action Schema

```python
@dataclass
class GroundedAction:
    """Action with precise source grounding."""

    id: str
    label: str
    icon: str
    prompt: str
    actionType: str

    # Enhanced grounding
    source_basis: str  # Human-readable: "Art. 7-ter, comma 1"
    source_doc_id: str  # Machine reference: "dpr_633_72"
    source_paragraph_id: str  # Precise: "art_7ter_comma_1"

    # For UI tooltip
    source_excerpt: str  # "...le prestazioni di servizi si considerano effettuate..."
```

#### 11.6.3 API Response with Paragraph Grounding

```json
{
  "suggested_actions": [
    {
      "id": "1",
      "label": "Calcola reverse charge su €15.000",
      "icon": "calculator",
      "prompt": "Calcola l'applicazione del reverse charge su una fattura di €15.000 per consulenza a cliente tedesco",
      "actionType": "primary",

      "grounding": {
        "source_ref": "Art. 7-ter DPR 633/72",
        "source_doc_id": "dpr_633_72",
        "source_paragraph_id": "art_7ter_comma_1_lett_a",
        "source_excerpt": "Le prestazioni di servizi si considerano effettuate nel territorio dello Stato quando sono rese a soggetti passivi stabiliti nel territorio dello Stato...",
        "source_url": "https://..."
      }
    }
  ]
}
```

---

### 11.7 Excellence Checklist

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| ✅ Context Integrity | COMPLETE | kb_sources_metadata passed to Step 100 |
| ✅ Reasoning Transparency | COMPLETE | ToT/CoT with dual reasoning |
| ✅ Cost Efficiency | COMPLETE | €0.0052 blended average |
| ✅ Source Hierarchy | **NEW** | Weighting in ToT scoring |
| ✅ Risk Analysis | **NEW** | Phase 1.6 in ToT |
| ✅ Ambiguous Query Handling | **NEW** | Multi-variant HyDE |
| ✅ Public vs Internal Reasoning | **NEW** | Dual reasoning structure |
| ✅ Action Regeneration | **NEW** | Golden Loop with correction |
| ✅ Paragraph-Level Grounding | **NEW** | source_paragraph_id in actions |

### 11.8 Implementation Tasks (Excellence Refinements)

| Task | Priority | Effort | Phase |
|------|----------|--------|-------|
| 11.1.1 Create source hierarchy mapping | P0 | 2h | Phase 2 |
| 11.1.2 Implement SourceConflictDetector | P0 | 4h | Phase 2 |
| 11.1.3 Update ToT prompt with source weighting | P0 | 2h | Phase 2 |
| 11.2.1 Add risk categories to hypothesis schema | P1 | 2h | Phase 2 |
| 11.2.2 Implement risk-aware action generation | P1 | 3h | Phase 2 |
| 11.2.3 Update ToT prompt with risk analysis phase | P1 | 2h | Phase 2 |
| 11.3.1 Implement QueryAmbiguityDetector | P1 | 3h | Phase 3 |
| 11.3.2 Create multi-variant HyDE prompt | P1 | 2h | Phase 3 |
| 11.3.3 Update HyDE generator for ambiguity handling | P1 | 2h | Phase 3 |
| 11.4.1 Create DualReasoning data structures | P1 | 2h | Phase 2 |
| 11.4.2 Implement ReasoningTransformer | P1 | 4h | Phase 2 |
| 11.4.3 Update API response schema | P1 | 1h | Phase 2 |
| 11.5.1 Implement ActionRegenerator | P0 | 4h | Phase 1 |
| 11.5.2 Create action regeneration prompt | P0 | 2h | Phase 1 |
| 11.5.3 Integrate regeneration loop in Step 100 | P0 | 2h | Phase 1 |
| 11.6.1 Update source schema for paragraph tracking | P2 | 3h | Phase 3 |
| 11.6.2 Implement paragraph extraction in retrieval | P2 | 4h | Phase 3 |
| 11.6.3 Update action schema with grounding fields | P2 | 2h | Phase 3 |

**Total Excellence Refinements: ~48 hours**

### 11.9 Updated Phase Plan

With excellence refinements, the phases are updated:

**Phase 1 (Week 1):** Foundation + Golden Loop
- Original Phase 1 tasks (23h)
- Action regeneration loop (8h)
- **Total: ~31 hours**

**Phase 2 (Week 2):** Intelligence + Source Hierarchy + Risk
- Original Phase 2 tasks (23h)
- Source hierarchy and conflict detection (8h)
- Risk analysis integration (7h)
- Dual reasoning (7h)
- **Total: ~45 hours**

**Phase 3 (Week 3):** Conversation + Ambiguity + Grounding
- Original Phase 3 tasks (10h)
- Ambiguous query handling (7h)
- Paragraph-level grounding (9h)
- **Total: ~26 hours**

**Phase 4 (Week 4):** Quality, Monitoring, UI
- Original Phase 4 tasks (21h)
- UI enhancements (30h)
- **Total: ~51 hours**

---

## Part 12: User Experience (UI/UX)

### 11.1 Design Philosophy

The Excellence Architecture should be **visible but not intrusive** to users. Italian tax professionals value:
- **Transparency** - Understanding how the AI reached its conclusion
- **Professionalism** - No gimmicks, clear communication
- **Efficiency** - Quick access to relevant actions

### 11.2 Loading States & Progress Indicators

#### 11.2.1 Complexity-Aware Loading Messages

Display contextual messages based on query complexity:

| Complexity | Loading Message (Italian) | Duration |
|------------|---------------------------|----------|
| SIMPLE | "Ricerca in corso..." | ~2s |
| COMPLEX | "Analisi di {n} scenari fiscali in corso..." | ~4s |
| MULTI_DOMAIN | "Analisi multi-dominio: fiscale + lavoro..." | ~5s |

**Implementation:**

```typescript
// Frontend loading state
interface LoadingState {
  isLoading: boolean;
  complexity: 'simple' | 'complex' | 'multi_domain';
  message: string;
  subMessage?: string;
}

const LOADING_MESSAGES = {
  simple: {
    message: "Ricerca in corso...",
    subMessage: null
  },
  complex: {
    message: "Analisi approfondita in corso...",
    subMessage: "Valutazione di {n} scenari possibili"
  },
  multi_domain: {
    message: "Analisi multi-dominio in corso...",
    subMessage: "Verifica normativa fiscale e del lavoro"
  }
};
```

#### 11.2.2 Progressive Loading UI

```
┌─────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🔍 Analisi di 3 scenari fiscali in corso...        │   │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░  65%    │   │
│  │                                                      │   │
│  │  ├── Scenario A: B2B con partita IVA UE      ✓     │   │
│  │  ├── Scenario B: B2B senza VIES              ✓     │   │
│  │  └── Scenario C: Prestazione a privato       ◐     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Note:** Progress indicators should be subtle and professional - no bouncing animations or excessive colors.

#### 11.2.3 Streaming Response with Reasoning Preview

For complex queries, optionally show reasoning as it streams:

```
┌─────────────────────────────────────────────────────────────┐
│  Ragionamento:                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  "Sto analizzando la normativa sulla fatturazione   │   │
│  │   intracomunitaria. Ho identificato 3 possibili     │   │
│  │   scenari basati sul contesto della domanda..."     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Risposta:                                                  │
│  Per fatturare servizi di consulenza a un'azienda tedesca, │
│  la procedura dipende dalla natura del cliente...          │
│  █                                                          │
└─────────────────────────────────────────────────────────────┘
```

### 11.3 Response Display

#### 11.3.1 Confidence & Reasoning Indicator

For ToT responses, show a collapsible reasoning summary:

```
┌─────────────────────────────────────────────────────────────┐
│  RISPOSTA                                                   │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Per fatturare servizi di consulenza a un'azienda tedesca  │
│  con partita IVA valida, si applica il regime di non       │
│  imponibilità ai sensi dell'Art. 7-ter DPR 633/72...       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ▶ Come ho ragionato (clicca per espandere)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  📎 Fonti: Art. 7-ter DPR 633/72, Circolare 37/E 2011     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Expanded Reasoning View:**

```
┌─────────────────────────────────────────────────────────────┐
│  ▼ Come ho ragionato                                        │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Ho analizzato 3 possibili scenari:                        │
│                                                             │
│  ● Scenario A (più probabile - 75%):                       │
│    Cliente B2B con P.IVA tedesca valida                    │
│    → Non imponibile + Reverse Charge                       │
│                                                             │
│  ○ Scenario B (15%):                                       │
│    Cliente B2B senza iscrizione VIES                       │
│    → IVA italiana 22%                                      │
│                                                             │
│  ○ Scenario C (10%):                                       │
│    Cliente privato                                         │
│    → IVA italiana o regime OSS                             │
│                                                             │
│  Ho scelto lo Scenario A perché la domanda menziona        │
│  "azienda", indicando un soggetto B2B.                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 11.3.2 Alternative Scenario Notice

When ToT identifies significant alternative scenarios, show a notice:

```
┌─────────────────────────────────────────────────────────────┐
│  ⚡ NOTA: Se il cliente non ha partita IVA comunitaria     │
│     valida, la procedura cambia. Verifica su VIES.         │
│                                                [Approfondisci]
└─────────────────────────────────────────────────────────────┘
```

### 11.4 Suggested Actions UI

#### 11.4.1 Action Card Design

```
┌─────────────────────────────────────────────────────────────┐
│  AZIONI SUGGERITE                                           │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔢  Calcola IVA su fattura                          │   │
│  │     "Calcola reverse charge su €15.000 di consulenza"│   │
│  │                                          [Esegui →] │   │
│  │     📎 Da: Art. 7-ter DPR 633/72                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔍  Verifica P.IVA su VIES                          │   │
│  │     "Come verificare validità partita IVA tedesca?" │   │
│  │                                          [Esegui →] │   │
│  │     📎 Da: Regolamento UE 904/2010                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 💡  E SE INVECE...?                    [Alternativo]│   │
│  │     Scenario: Cliente senza P.IVA valida            │   │
│  │     "Come fatturare se il cliente non è su VIES?"   │   │
│  │                                          [Esegui →] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 11.4.2 Action Labels by Type

| Action Type | Label | Badge Color | Icon |
|-------------|-------|-------------|------|
| Primary (selected hypothesis) | None | None | Domain icon |
| Alternative scenario | "E se invece...?" | Orange | 💡 |
| Deepening | "Approfondimento" | Blue | 🔍 |
| Calculation | "Calcolo" | Green | 🔢 |
| Deadline | "Scadenza" | Red | 📅 |
| Risk | "Attenzione" | Yellow | ⚠️ |

#### 11.4.3 Action Data Structure for UI

```typescript
interface SuggestedAction {
  id: string;
  label: string;                    // Short label (8-40 chars)
  prompt: string;                   // Full prompt to execute
  icon: ActionIcon;                 // calculator|search|calendar|info|...

  // NEW: UI Enhancement fields
  actionType: 'primary' | 'alternative' | 'deepening' | 'calculation' | 'deadline' | 'risk';
  hypothesisRelated?: 'A' | 'B' | 'C' | 'all';
  sourceBasis: string;              // Which KB source inspired this

  // For alternative scenario actions
  alternativeContext?: {
    scenario: string;               // Brief description of the scenario
    condition: string;              // When this applies
  };
}

// Example action for alternative scenario
const alternativeAction: SuggestedAction = {
  id: "3",
  label: "Fatturazione senza VIES",
  prompt: "Come fatturare consulenza a cliente tedesco non iscritto VIES?",
  icon: "info",
  actionType: "alternative",
  hypothesisRelated: "B",
  sourceBasis: "Art. 17 DPR 633/72",
  alternativeContext: {
    scenario: "Cliente B2B senza partita IVA comunitaria valida",
    condition: "Se la verifica VIES risulta negativa"
  }
};
```

#### 11.4.4 Action Grouping

When multiple hypotheses generate actions, group them visually:

```
┌─────────────────────────────────────────────────────────────┐
│  AZIONI SUGGERITE                                           │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Per lo scenario principale:                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔢  Calcola reverse charge EU                       │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📋  Obblighi Intrastat                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│                                                             │
│  Scenari alternativi da considerare:                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 💡  E se il cliente non ha P.IVA?      [Alternativo]│   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 11.5 Mobile Considerations

#### 11.5.1 Compact Loading State

```
┌─────────────────────────────┐
│  🔍 Analisi 3 scenari...   │
│  ━━━━━━━━━━━━━━░░░░  65%   │
└─────────────────────────────┘
```

#### 11.5.2 Swipeable Action Cards

On mobile, actions can be presented as swipeable cards:

```
┌─────────────────────────────┐
│  ← Swipe per altre azioni → │
│  ┌───────────────────────┐  │
│  │ 🔢 Calcola reverse    │  │
│  │    charge EU          │  │
│  │         [Esegui →]    │  │
│  │ ● ○ ○                 │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

#### 11.5.3 Collapsible Reasoning (Default Collapsed)

On mobile, reasoning is collapsed by default to save space:

```
┌─────────────────────────────┐
│  [▶ Vedi ragionamento]      │
└─────────────────────────────┘
```

### 11.6 Accessibility

| Element | Requirement |
|---------|-------------|
| Loading messages | Screen reader announces progress |
| Action buttons | Minimum 44x44px touch target |
| Alternative badges | Color + icon (not color alone) |
| Reasoning toggle | Keyboard accessible (Enter/Space) |
| Confidence scores | Text alternative ("alta probabilità") |

### 11.7 UI State Machine

```
┌─────────────────────────────────────────────────────────────┐
│  UI STATE MACHINE                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  IDLE                                                       │
│    │                                                        │
│    │ [User submits query]                                   │
│    ▼                                                        │
│  CLASSIFYING ──────────────────────────────────────────┐   │
│    │ Message: "Analisi della domanda..."               │   │
│    │ Duration: ~400ms                                   │   │
│    │                                                    │   │
│    │ [Complexity determined]                            │   │
│    ▼                                                    │   │
│  RETRIEVING                                             │   │
│    │ Message: "Ricerca documenti..."                   │   │
│    │ Duration: ~500ms                                   │   │
│    │                                                    │   │
│    │ [Documents retrieved]                              │   │
│    ▼                                                    │   │
│  REASONING ◄────────────────────────────────────────────┘   │
│    │ Message (based on complexity):                         │
│    │   SIMPLE: "Elaborazione risposta..."                  │
│    │   COMPLEX: "Analisi di N scenari..."                  │
│    │   MULTI: "Analisi multi-dominio..."                   │
│    │ Duration: 1.5-4s                                       │
│    │                                                        │
│    │ [Response received]                                    │
│    ▼                                                        │
│  STREAMING                                                  │
│    │ Display: Streaming text + reasoning preview           │
│    │ Duration: Variable                                     │
│    │                                                        │
│    │ [Stream complete]                                      │
│    ▼                                                        │
│  COMPLETE                                                   │
│    │ Display: Full response + actions                       │
│    │                                                        │
│    │ [User clicks action] ──► IDLE (with new query)        │
│    │ [User types new query] ──► IDLE                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 11.8 API Response for UI

Extend API response with UI hints:

```json
{
  "answer": "...",
  "sources": [...],
  "suggested_actions": [...],

  "ui_hints": {
    "complexity_level": "complex",
    "reasoning_available": true,
    "reasoning_summary": "Analizzati 3 scenari: B2B VIES (75%), B2B no-VIES (15%), B2C (10%)",
    "primary_hypothesis": {
      "id": "A",
      "label": "B2B con P.IVA comunitaria",
      "confidence": 0.75,
      "confidence_label": "alta probabilità"
    },
    "has_alternatives": true,
    "alternative_notice": "Se il cliente non ha P.IVA valida, la procedura cambia.",
    "action_groups": [
      {
        "group": "primary",
        "label": "Per lo scenario principale",
        "action_ids": ["1", "2"]
      },
      {
        "group": "alternative",
        "label": "Scenari alternativi",
        "action_ids": ["3"]
      }
    ]
  }
}
```

### 11.9 Implementation Tasks

| Task | Priority | Effort | Phase |
|------|----------|--------|-------|
| 11.1 Complexity-aware loading messages | P1 | 2h | Phase 4 |
| 11.2 Reasoning collapse/expand component | P2 | 3h | Phase 4 |
| 11.3 Action card with source badge | P1 | 2h | Phase 4 |
| 11.4 Alternative scenario label/badge | P1 | 2h | Phase 4 |
| 11.5 Action grouping (primary/alternative) | P2 | 3h | Phase 4 |
| 11.6 Mobile swipeable actions | P3 | 4h | Phase 5 |
| 11.7 Streaming with reasoning preview | P3 | 5h | Phase 5 |
| 11.8 UI state machine implementation | P2 | 4h | Phase 4 |
| 11.9 API ui_hints extension | P1 | 2h | Phase 4 |
| 11.10 Accessibility audit | P2 | 3h | Phase 5 |

**Total UI effort: ~30 hours (Phase 4-5)**

---

*End of Technical Intent Document*
