# AI Application Architect Knowledge Base

**Purpose:** Domain expertise for reviewing and designing AI/LLM applications
**Audience:** Egidio (Architect Agent) and human architects
**Last Updated:** 2025-12-12

---

## Overview

This document captures the expertise of a senior AI application architect with 10+ years of experience building production LLM systems. Use this knowledge when:

- Reviewing architectural decisions for AI features
- Planning new conversation, RAG, or LLM orchestration features
- Debugging issues related to context, state, or retrieval
- Evaluating trade-offs in AI system design

---

## Part 1: Conversational AI Architecture

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **Context is not magic** | Multi-turn conversations require explicit state management. LLMs have no memory between API calls. |
| **Context windows are finite** | Every token counts. A 128K context window is not infinite - budget carefully. |
| **Memory != History** | Chat history is raw data. Memory is processed, summarized understanding. They serve different purposes. |
| **Sessions are boundaries** | Never assume state persists without explicit design. Define when context resets. |

### How Production Systems Work

Understanding how industry leaders handle conversation state:

**ChatGPT (OpenAI):**
- Server-side conversation storage in PostgreSQL
- `conversation_id` as primary key for message threading
- Full message history sent to API (with sliding window for long conversations)
- Explicit "New Chat" to reset context

**Claude (Anthropic):**
- Similar server-side storage pattern
- `conversation_id` groups related messages
- System prompts can set persistent context
- Conversation history managed by client, sent per-request

**Perplexity:**
- Query-focused design with minimal multi-turn
- Each query is largely independent (by design choice)
- "Follow-up" feature explicitly links queries
- Optimized for search, not conversation

**Key Insight:** All production systems store conversation state server-side and explicitly manage what gets sent to the LLM.

### Common Anti-Patterns

| Anti-Pattern | Why It's Wrong | Correct Approach |
|--------------|----------------|------------------|
| Assuming LLM "remembers" previous turns | LLMs are stateless - each API call starts fresh | Explicitly send relevant history |
| Sending full history every turn | Context overflow, increased latency and cost | Use sliding window or summarization |
| Not resolving anaphora | "it", "that", "the document" become ambiguous | Track references explicitly in state |
| Losing attachment context between turns | User expects document to stay "in memory" | Persist document context in session state |
| Relying on client-side storage only | Lost on browser clear, no multi-device sync | Server-side as source of truth |

### Decision Framework: Multi-Turn Features

When reviewing any feature that involves multi-turn conversations, systematically ask:

```
1. STATE STORAGE
   - Where is conversation state stored? (memory, DB, checkpointer, Redis?)
   - What's the source of truth? (server vs client)
   - How long does state persist? (session, 24h, forever?)

2. CONTEXT LOADING
   - How is previous context loaded for new turns?
   - Is it automatic or explicit?
   - What happens if the load fails?

3. TOKEN LIMITS
   - What happens if context exceeds token limits?
   - Is there a sliding window? Summarization?
   - How do you prioritize what to keep vs drop?

4. REFERENCE RESOLUTION
   - How are pronouns ("it", "that") resolved?
   - How are document references ("the PDF I uploaded") tracked?
   - What happens when references become ambiguous?

5. SESSION BOUNDARIES
   - When does context reset? (explicit new chat, timeout, logout?)
   - How does the user know their context scope?
   - Can users explicitly manage their context?
```

---

## Part 2: RAG (Retrieval-Augmented Generation) Architecture

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **Retrieval quality > Generation quality** | If you retrieve garbage, the LLM will confidently present garbage. Retrieval is the bottleneck. |
| **Hybrid search beats single-method** | Combine vector similarity + keyword matching + metadata filtering for best results. |
| **Context injection is an art** | Too little context = no grounding. Too much = dilution and "lost in the middle" problems. |
| **Chunking strategy matters** | Wrong chunk size = wrong retrieval. Semantic boundaries beat arbitrary character counts. |

### RAG Failure Modes

Understanding failure modes is critical for debugging and prevention:

| Failure Mode | Symptom | Root Cause | Mitigation |
|--------------|---------|------------|------------|
| **Retrieval drift** | Wrong documents returned for query | Poor embedding model, bad query expansion, or stale index | Better embeddings, query rewriting, regular index refresh |
| **Context poisoning** | LLM uses irrelevant retrieved content | No relevance threshold, retrieves K docs regardless of score | Add relevance filtering, minimum score threshold |
| **Hallucination despite RAG** | Confident wrong answers | Retrieved context doesn't contain the answer | Add "I don't know" fallback, confidence scoring |
| **Lost in the middle** | LLM ignores content in middle of context | Attention bias toward beginning and end | Reorder by relevance, put critical info at edges |
| **Stale knowledge** | Outdated answers despite new documents | No freshness weighting in retrieval | Add recency boost, timestamp filtering |
| **Over-retrieval** | Generic, unfocused responses | Too many documents, diluted signal | Retrieve fewer, more relevant chunks |
| **Chunk boundary issues** | Partial or nonsensical retrieved content | Chunks split mid-sentence or mid-concept | Semantic chunking, overlap between chunks |

### Retrieval Pipeline Design

A well-designed RAG pipeline has multiple stages:

```
User Query
    │
    ▼
┌─────────────────┐
│ Query Analysis  │  ← Classify intent, extract entities, expand query
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Multi-Retrieval │  ← Vector search + BM25 + metadata filter (in parallel)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fusion/Merge    │  ← Combine results, remove duplicates, apply weights
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Reranking       │  ← Cross-encoder or LLM-based relevance scoring
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Filtering       │  ← Remove below-threshold, limit count, check freshness
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Format  │  ← Structure for LLM consumption with citations
└────────┬────────┘
         │
         ▼
    LLM Generation
```

### Decision Framework: RAG Features

When reviewing RAG-related changes, systematically ask:

```
1. CHUNKING STRATEGY
   - What's the chunk size? (characters, tokens, semantic?)
   - Is there overlap between chunks?
   - How are chunk boundaries determined? (arbitrary vs semantic)
   - Are metadata and source preserved per-chunk?

2. RETRIEVAL METHOD
   - Vector only? Keyword only? Hybrid?
   - What embedding model? What dimension?
   - How many results retrieved (K)?
   - Is there query expansion or rewriting?

3. RELEVANCE SCORING
   - What's the relevance threshold?
   - Is there reranking after initial retrieval?
   - How are duplicates/near-duplicates handled?
   - Is vector distance the only signal?

4. CONTEXT BUDGET
   - How many tokens allocated to retrieved content?
   - What happens when budget exceeded?
   - How is the budget split among sources?
   - Is there summarization for long documents?

5. FRESHNESS
   - How is document recency weighted?
   - Are there time-based filters?
   - How often is the index updated?
   - Can stale content be excluded?

6. FALLBACK STRATEGY
   - What happens when nothing relevant is found?
   - Is there a confidence score exposed to users?
   - Does the system say "I don't know" or hallucinate?
   - Are there fallback data sources?
```

---

## Part 3: LLM Orchestration (LangGraph/LangChain)

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **State is explicit** | Use TypedDict or Pydantic models. Never rely on implicit variables or closures. |
| **Nodes are pure functions** | Input state → Output state. No side effects in business logic (logging OK). |
| **Checkpointing is recovery** | Design checkpointing for crash recovery, not just debugging. |
| **Streaming is not optional** | Modern users expect real-time feedback. Design for streaming from day 1. |

### LangGraph-Specific Patterns

**State Accumulation:**
```python
# CORRECT: Use Annotated for lists that grow across nodes
from typing import Annotated
import operator

class State(TypedDict):
    messages: Annotated[list[dict], operator.add]  # Accumulates across nodes

# WRONG: List gets overwritten each node
class State(TypedDict):
    messages: list[dict]  # Each node overwrites entire list
```

**Conditional Edges:**
```python
# CORRECT: Route based on state values
def route_by_intent(state: State) -> str:
    if state["intent"] == "search":
        return "search_node"
    return "chat_node"

graph.add_conditional_edges("classifier", route_by_intent)

# WRONG: Hardcoded routing
graph.add_edge("classifier", "search_node")  # No flexibility
```

**Thread ID Consistency:**
```python
# CORRECT: Use session_id as thread_id throughout
config = {"configurable": {"thread_id": session_id}}
result = await graph.ainvoke(state, config)

# WRONG: Different IDs for checkpointer vs history
checkpointer_id = str(uuid4())  # New ID each time = no recovery
```

### Common LangGraph Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|--------------|---------|------------------|
| Mutating state directly | Breaks immutability, causes bugs | Return new state dict from nodes |
| Side effects in nodes | Hard to test, unpredictable | Separate IO from logic, use dedicated persistence nodes |
| Ignoring checkpointer failures | Lost state on crash | Graceful degradation, retry logic |
| Assuming state persists across invocations | State is ephemeral without checkpointer | Configure checkpointer with persistent storage |
| Blocking operations in streaming | UI hangs waiting | Use async, yield chunks immediately |
| Not typing state | Runtime errors, hard to debug | TypedDict with all fields explicitly typed |
| Mixing concerns in nodes | 500-line nodes, untestable | Single responsibility per node |

### Decision Framework: Orchestration Changes

When reviewing LangGraph or pipeline changes, systematically ask:

```
1. STATE TYPING
   - Is state explicitly typed? (TypedDict with all fields)
   - Are all fields documented?
   - Is there validation on state transitions?
   - Are accumulator fields properly annotated?

2. NODE PURITY
   - Are nodes pure functions? (input → output, no side effects)
   - Is business logic separate from IO?
   - Can each node be tested in isolation?
   - Are there any hidden dependencies?

3. CHECKPOINTING
   - Is checkpointing configured?
   - What storage backend? (memory, PostgreSQL, Redis?)
   - How is thread_id determined? Is it consistent?
   - What happens if checkpointing fails?

4. STREAMING
   - Does streaming work through this change?
   - Are there blocking operations in the streaming path?
   - Is state updated before or after streaming?
   - Can partial results be delivered?

5. ERROR HANDLING
   - What happens if a node fails mid-execution?
   - Is there retry logic?
   - Are errors propagated to the user meaningfully?
   - Can the workflow resume from checkpoints?

6. THREAD MANAGEMENT
   - Is session_id used consistently as thread_id?
   - Is thread_id passed through all subgraphs?
   - How are parallel branches handled?
   - What happens with concurrent requests to same thread?
```

---

## Part 4: Context Window Management

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **Token budgets are hard limits** | Exceeding the context window = truncation or API error. No exceptions. |
| **Prioritize recent over ancient** | In most cases, recent messages matter more. Use sliding windows. |
| **Summarize, don't truncate** | Lossy compression (summarization) beats arbitrary cutting. |
| **Reserve tokens for output** | Input budget != context window. Always reserve space for the response. |

### Token Budget Allocation

A typical budget for an 8K context window:

```
┌────────────────────────────────────────────┐
│ CONTEXT WINDOW: 8,192 tokens              │
├────────────────────────────────────────────┤
│                                            │
│  System Prompt       [500-1000 tokens]     │  ← Fixed, carefully crafted
│  ─────────────────────────────────────     │
│  Retrieved Context   [2000-3000 tokens]    │  ← RAG results, variable
│  (RAG results)                             │
│  ─────────────────────────────────────     │
│  Conversation History [1000-2000 tokens]   │  ← Sliding window
│  (recent turns)                            │
│  ─────────────────────────────────────     │
│  Current User Query  [100-500 tokens]      │  ← Variable
│  ─────────────────────────────────────     │
│  OUTPUT RESERVATION  [1500-2000 tokens]    │  ← MUST reserve this
│                                            │
└────────────────────────────────────────────┘
```

**Key Formula:**
```
Available Input = Context Window - Output Reservation

If Available Input < (System + RAG + History + Query):
    Must truncate something!
```

### Truncation Strategies

When you exceed the budget, something must go. Prioritize:

| Priority | What to Truncate | Strategy |
|----------|------------------|----------|
| 1 (Last) | System Prompt | Never truncate - it defines behavior |
| 2 | Current Query | Truncate only if absurdly long |
| 3 | Most Recent History | Keep recent turns, drop oldest |
| 4 | Retrieved Context | Drop lowest relevance chunks first |
| 5 (First) | Old History | Summarize or drop oldest messages |

**Summarization vs Truncation:**
```
TRUNCATION (lossy, fast):
"The quick brown fox jumps over the lazy dog" → "The quick brown fox"

SUMMARIZATION (preserves meaning, slow):
"The quick brown fox jumps over the lazy dog" → "A fox leaps over a dog"
```

Use summarization for important context (conversation history).
Use truncation for less critical content (old retrieved chunks).

### Decision Framework: Context Changes

When reviewing context-related changes, systematically ask:

```
1. TOTAL BUDGET
   - What's the total token budget for this model?
   - Is it hardcoded or configurable?
   - How is it measured? (tiktoken, approximate?)

2. OUTPUT RESERVATION
   - How much is reserved for output?
   - Is max_tokens set appropriately?
   - What happens if output exceeds reservation?

3. TRUNCATION PRIORITY
   - What gets truncated first when budget exceeded?
   - Is there a defined priority order?
   - Is critical content protected?

4. TRUNCATION METHOD
   - Is truncation lossy or summarized?
   - Are truncation points semantic or arbitrary?
   - Is the user notified when truncation occurs?

5. BUDGET SPLIT
   - How is budget split between RAG/history/system?
   - Are the splits fixed or adaptive?
   - Can one category borrow from another?

6. MEASUREMENT
   - How are tokens counted? (exact vs estimate)
   - Is counting done before or after formatting?
   - Are special tokens (BOS, EOS) accounted for?
```

---

## Part 5: Security and Privacy in AI Systems

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **Prompt injection is real** | User input can manipulate LLM behavior. Always sanitize and constrain. |
| **PII exposure is catastrophic** | LLMs can leak training data or user data in context. Anonymize aggressively. |
| **Audit everything** | Log inputs, outputs, and decisions for debugging and compliance. |
| **Least privilege** | LLMs should not have access to systems they don't need. |

### Common Security Issues

| Issue | Risk | Mitigation |
|-------|------|------------|
| **Prompt injection** | User tricks LLM into ignoring system prompt | Input validation, output filtering, structured outputs |
| **Data exfiltration** | LLM reveals sensitive context | PII anonymization, output filtering |
| **Jailbreaking** | User bypasses safety guidelines | Defense in depth, multiple validation layers |
| **Indirect injection** | Malicious content in retrieved documents | Sanitize retrieved content before injection |
| **Context leakage** | One user's data exposed to another | Strict tenant isolation, session boundaries |

### GDPR Considerations for AI

For EU-based systems (like PratikoAI):

1. **Right to be Forgotten**: User deletion must cascade to all stored context
2. **Data Export**: Users can request all their conversation data
3. **Consent**: Clear disclosure that conversations may be processed by LLMs
4. **Data Minimization**: Don't store more than necessary
5. **Retention Limits**: Define and enforce retention periods

---

## Part 6: AI Evaluation & Metrics

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **Measure what matters** | Define success metrics before building. Relevance, accuracy, latency, cost. |
| **Hallucination is the enemy** | Detecting and preventing hallucination is critical for trust. |
| **User satisfaction ≠ technical metrics** | High retrieval precision doesn't guarantee users are happy. |
| **Baseline everything** | You can't improve what you don't measure. Establish baselines first. |

### Key Metrics for RAG Systems

| Metric | What It Measures | How to Measure | Target |
|--------|------------------|----------------|--------|
| **Retrieval Precision@K** | % of retrieved docs that are relevant | Human annotation / LLM-as-judge | >80% |
| **Retrieval Recall@K** | % of relevant docs that are retrieved | Requires known-relevant set | >70% |
| **Answer Relevance** | Does the answer address the query? | LLM-as-judge scoring | >90% |
| **Faithfulness** | Is answer grounded in retrieved context? | Citation verification | >95% |
| **Answer Correctness** | Is the answer factually correct? | Domain expert review | >90% |
| **Latency (p95)** | Response time | APM tooling | <500ms |
| **Cost per query** | API + compute costs | Cost tracking | <€0.01 |

### Hallucination Detection Strategies

**Types of Hallucination:**
1. **Factual**: LLM states incorrect facts (e.g., wrong tax rate)
2. **Fabricated citations**: LLM invents sources that don't exist
3. **Temporal**: LLM uses outdated information as current
4. **Extrapolation**: LLM extends beyond what context supports

**Detection Methods:**

| Method | How It Works | Pros | Cons |
|--------|--------------|------|------|
| **Citation verification** | Check if cited sources exist and support claim | High precision | Expensive |
| **Entailment checking** | Use NLI model to verify answer ⊆ context | Automated | False positives |
| **LLM self-consistency** | Ask same question multiple times, check agreement | Simple | Misses consistent errors |
| **Confidence scoring** | Track model confidence, flag low-confidence answers | Real-time | Uncalibrated confidence |
| **Human spot-checking** | Sample responses for human review | Ground truth | Not scalable |

**"I Don't Know" Calibration:**
- Configure the system to say "I don't know" when:
  - No relevant documents retrieved (retrieval score < threshold)
  - Answer confidence below threshold
  - Query outside known domain
- Track "I don't know" rate: Too high = retrieval problem, too low = overconfidence

### Evaluation Datasets

**Build evaluation sets for:**
1. **Golden queries**: Known good queries with expected answers
2. **Edge cases**: Queries that historically caused problems
3. **Domain coverage**: Representative queries across all supported topics
4. **Adversarial**: Queries designed to trick the system

**Recommended size:** 100-500 queries per evaluation set

### Decision Framework: Evaluation

When reviewing AI features, systematically ask:

```
1. SUCCESS METRICS
   - How will we know if this is working?
   - What are the target metrics?
   - Do we have baseline measurements?

2. FAILURE DETECTION
   - How do we detect when it's failing?
   - What monitoring/alerting is in place?
   - What's the rollback plan?

3. HALLUCINATION PREVENTION
   - How do we measure hallucinations?
   - What's the hallucination rate target?
   - Is there citation verification?

4. USER FEEDBACK
   - How do we collect user feedback?
   - Are there thumbs up/down signals?
   - How is feedback incorporated?

5. EVALUATION COVERAGE
   - Do we have an evaluation dataset?
   - Does it cover edge cases?
   - When was it last updated?
```

---

## Part 7: Cost Optimization for LLM Applications

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **Token efficiency is money** | Every token costs. Optimize prompts, truncate smartly. |
| **Cache aggressively** | Semantic caching can reduce costs 30-60%. |
| **Use the smallest model that works** | GPT-4 for complex reasoning, GPT-3.5 for simple tasks. |
| **Batch when possible** | Batch processing is cheaper than real-time for non-urgent tasks. |

### Cost Breakdown

**Typical LLM cost structure:**
```
Total Cost = Input Tokens × Input Price + Output Tokens × Output Price

Example (GPT-4 Turbo, 1000 queries/day):
- Avg input: 2000 tokens × $0.01/1K = $0.02
- Avg output: 500 tokens × $0.03/1K = $0.015
- Cost per query: $0.035
- Daily cost: $35
- Monthly cost: ~$1,050

With 60% cache hit rate:
- Queries hitting LLM: 400/day
- Monthly cost: ~$420 (60% savings)
```

### Cost Optimization Strategies

| Strategy | Potential Savings | Implementation Complexity | PratikoAI Status |
|----------|-------------------|---------------------------|------------------|
| **Semantic caching** | 30-60% | Medium | ✅ Implemented (Redis) |
| **Prompt optimization** | 10-20% | Low | ⏳ Ongoing |
| **Model tiering** | 50-90% | Medium | ⏳ Planned |
| **Response length limits** | 10-30% | Low | ✅ Implemented |
| **Batch processing** | 20-40% | Medium | N/A (real-time only) |
| **Embedding caching** | 20-30% | Low | ✅ Implemented |

### Model Tiering Strategy

**Route queries to appropriate model:**

| Query Type | Model | Cost | Example |
|------------|-------|------|---------|
| Simple FAQ | GPT-3.5 / cached | $0.001 | "What's the VAT rate?" |
| Complex reasoning | GPT-4 | $0.03 | "How do I structure a holding company?" |
| Classification only | GPT-3.5 | $0.001 | Intent detection |
| Summarization | GPT-3.5 | $0.005 | Document summaries |

**Implementation approach:**
1. Classify query complexity (fast, cheap classifier)
2. Route to appropriate model
3. Track cost per query type
4. Adjust thresholds based on user feedback

### PratikoAI Budget Context

**Constraints:**
- Monthly LLM budget: €2,000
- Target users: 500 active
- Per-user monthly budget: €4
- Per-query target: <€0.004 (assuming 1000 queries/user/month)

**Current cost tracking:**
- Semantic cache hit rate target: ≥60%
- Average cost per query: Track via `query_history.cost_cents`
- Daily cost alerts: When daily spend > €100

### Decision Framework: Cost

When reviewing features with LLM costs, systematically ask:

```
1. COST ESTIMATION
   - What's the expected cost per query?
   - What's the expected query volume?
   - What's the monthly cost projection?

2. CACHING
   - Is semantic caching applicable?
   - What's the expected cache hit rate?
   - How is cache invalidation handled?

3. MODEL SELECTION
   - Can a smaller/cheaper model handle this?
   - Is model tiering possible?
   - What's the quality trade-off?

4. OPTIMIZATION
   - Is the prompt optimized for token efficiency?
   - Can response length be limited?
   - Are we batching where possible?

5. SCALING
   - What's the cost if usage 10x?
   - Are there cost caps/alerts?
   - What's the fallback if budget exceeded?
```

---

## Part 8: Italian Legal/Tax Domain Expertise

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **Citations must be precise** | Users rely on citations for compliance. "Art. 13, comma 2, lettera b) del D.Lgs. 196/2003" |
| **Temporal context is critical** | Laws change. "As of 2024" is different from "As of 2020". |
| **Deadlines are non-negotiable** | Missing a tax deadline (scadenza) has real consequences. |
| **Hierarchy matters** | Later laws can modify/repeal earlier ones (abrogazione). |

### Italian Legal Document Structure

```
Hierarchy:
Costituzione
    └── Legge (L.)
         └── Decreto Legislativo (D.Lgs.)
              └── Decreto del Presidente della Repubblica (D.P.R.)
                   └── Decreto Ministeriale (D.M.)
                        └── Circolare
                             └── Risoluzione
                                  └── Interpello (Risposta)

Within a document:
Titolo → Capo → Sezione → Articolo → Comma → Lettera → Numero

Citation format:
Art. 13, comma 2, lettera b), numero 1) del D.Lgs. 196/2003
```

### Common Document Types

| Type | Abbreviation | Authority | Example | Binding? |
|------|--------------|-----------|---------|----------|
| Decreto Legislativo | D.Lgs. | Governo (delegated by Parliament) | D.Lgs. 81/2008 (Sicurezza) | Yes |
| Decreto del Presidente della Repubblica | D.P.R. | Presidente | D.P.R. 917/1986 (TUIR) | Yes |
| Legge | L. | Parlamento | L. 104/1992 (Disabilità) | Yes |
| Decreto Legge | D.L. | Governo (emergency) | D.L. 18/2020 (COVID) | Yes (temporary) |
| Circolare | Circ. | Agenzia Entrate | Circ. 19/E/2023 | Interpretive |
| Risoluzione | Ris. | Agenzia Entrate | Ris. 45/E/2024 | Interpretive |
| Interpello | Risposta n. | Agenzia Entrate | Risposta n. 123/2024 | Case-specific |

### Key Tax Deadlines (Scadenze)

| Deadline | Description | Frequency |
|----------|-------------|-----------|
| 16th of month | F24 payment (taxes, contributions) | Monthly |
| 20th of month | INTRASTAT | Monthly/Quarterly |
| End of month | IVA liquidation | Monthly/Quarterly |
| 30 June | Dichiarazione dei redditi (persone fisiche) | Annual |
| 30 September | Dichiarazione IVA | Annual |
| 30 November | Secondo acconto imposte | Annual |
| 31 December | Various annual deadlines | Annual |

**Important terminology:**
- **Entro** = by/before (hard deadline)
- **Entro il termine di X giorni** = within X days of
- **A decorrere da** = starting from
- **Salvo proroghe** = unless extended

### Domain-Specific RAG Considerations

**1. Citation Accuracy:**
```
CRITICAL: Users will cite your sources to tax authorities.
- Always include full citation: Art. X, comma Y, D.Lgs. Z/YYYY
- Link to official source (Normattiva, Gazzetta Ufficiale)
- Indicate publication date and any amendments
```

**2. Temporal Relevance:**
```
Tax rules change frequently:
- Track effective dates (in vigore dal)
- Track expiration/repeal dates (abrogato dal)
- Store version history when possible
- Default to most recent unless user specifies historical query
```

**3. Hierarchy and Amendments:**
```
Later laws can modify earlier ones:
- "L'articolo X è sostituito dal seguente" (replacement)
- "L'articolo X è abrogato" (repeal)
- "Dopo l'articolo X è inserito il seguente" (addition)

RAG must understand these relationships.
```

**4. Regional Variations:**
```
Some rules vary by region:
- IRAP rates (Imposta Regionale Attività Produttive)
- Addizionali regionali/comunali IRPEF
- Bollo auto rates

When answering, clarify if regional variation applies.
```

### Common User Query Patterns

| Pattern | Example | What User Needs |
|---------|---------|-----------------|
| Deadline query | "Quando scade l'F24?" | Date + any extensions |
| Rate query | "Qual è l'aliquota IVA per..." | Current rate + exceptions |
| Procedure query | "Come faccio a..." | Step-by-step + forms needed |
| Document query | "Dove trovo la circolare su..." | Citation + link |
| Calculation query | "Quanto devo pagare di..." | Formula + example |
| Compliance query | "Devo fare X?" | Yes/no + source |

### Decision Framework: Italian Legal/Tax Features

When reviewing Italian legal/tax features, systematically ask:

```
1. CITATION FORMAT
   - Are citations in correct Italian format?
   - Example: Art. X, comma Y, D.Lgs. Z/YYYY
   - Is the official source linked?

2. TEMPORAL CONTEXT
   - Is the version/date of the law specified?
   - Are amendments tracked?
   - What happens if user asks about historical rules?

3. DEADLINES
   - Are deadlines (scadenze) handled correctly?
   - Is the format consistent (DD/MM/YYYY)?
   - Are extensions/proroghe communicated?

4. REGIONAL VARIATION
   - Is there regional variation to consider?
   - Is the user's region known/relevant?
   - Is variation clearly communicated?

5. HIERARCHY
   - How do we handle conflicting regulations?
   - Are superseded rules flagged?
   - Is the source authority level clear?
```

---

## Quick Reference: Review Checklists

### Conversation/Chat Feature Checklist

- [ ] Where is conversation state stored?
- [ ] How is previous context loaded for new turns?
- [ ] What's the session boundary?
- [ ] How are document/file references resolved across turns?
- [ ] What happens when context window is exceeded?
- [ ] Is there proper session isolation between users?

### RAG Feature Checklist

- [ ] What's the chunking strategy and chunk size?
- [ ] Is relevance scored beyond vector distance?
- [ ] What's the context token budget?
- [ ] What's the fallback when nothing relevant found?
- [ ] Is there freshness/recency weighting?
- [ ] Are retrieved documents sanitized before injection?

### LangGraph/Pipeline Checklist

- [ ] Is state explicitly typed with TypedDict?
- [ ] Are nodes pure functions (no side effects)?
- [ ] Is checkpointing configured for recovery?
- [ ] Does streaming work through this change?
- [ ] Is thread_id/session_id consistent throughout?
- [ ] What happens if a node fails mid-execution?

### Context/Token Checklist

- [ ] What's the total context window budget?
- [ ] How much is reserved for output?
- [ ] What gets truncated first when exceeded?
- [ ] Is truncation lossy or summarized?
- [ ] How is the budget split between RAG/history/system?

### AI Evaluation Checklist

- [ ] What are the success metrics for this feature?
- [ ] How do we detect hallucinations?
- [ ] Is there an evaluation dataset?
- [ ] How is user feedback collected?
- [ ] What's the rollback plan if quality degrades?

### Cost Optimization Checklist

- [ ] What's the expected cost per query?
- [ ] Is semantic caching applicable?
- [ ] Can a smaller/cheaper model handle this?
- [ ] What happens if usage scales 10x?
- [ ] Are there cost alerts configured?

### Italian Legal/Tax Checklist

- [ ] Are citations in correct format? (Art. X, comma Y, D.Lgs. Z/YYYY)
- [ ] Is temporal context handled? (version/date of law)
- [ ] Are deadlines (scadenze) accurate?
- [ ] Is regional variation considered?
- [ ] How are superseded rules handled?

---

## Part 9: Response Quality & RAG Optimization Patterns (DEV-242)

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **Retrieval completeness > retrieval precision** | Missing critical chunks causes incomplete responses. Better to include more chunks than miss important content. |
| **Grounding rules position matters** | Rules injected RIGHT BEFORE KB context get highest LLM attention. |
| **Formatting vs content rules separation** | Formatting instructions (structure, headers) cause LLM to use large headers. Keep formatting minimal. |
| **Source authority affects ranking** | New authoritative sources need explicit weight configuration or they rank too low. |

### Retrieval Pipeline Parameters

Critical parameters that control what chunks reach the LLM:

| Parameter | Location | Default | Purpose |
|-----------|----------|---------|---------|
| `CONTEXT_TOP_K` | `app/core/config.py` | 22 | Maximum chunks sent to LLM context |
| `HYBRID_K_FTS` | `app/core/config.py` | 30 | BM25/FTS candidates before fusion |
| `HYBRID_K_VEC` | `app/core/config.py` | 30 | Vector search candidates (if enabled) |

**The Funnel:**
```
BM25 Search → HYBRID_K_FTS candidates (30)
     ↓
RRF Fusion + Authority Boosts
     ↓
Final Selection → CONTEXT_TOP_K chunks (22) → LLM
```

**Lesson Learned (DEV-242 Phase 27):**
Deduplication MUST use `chunk_id`, NOT `knowledge_item_id` (document ID). Using document ID causes all chunks from the same document to deduplicate to just ONE chunk - losing critical information.

### Source Authority Weights

Location: `app/core/config.py` → `SOURCE_AUTHORITY_WEIGHTS`

```python
SOURCE_AUTHORITY_WEIGHTS = {
    "gazzetta_ufficiale": 0.20,           # Official laws - highest authority
    "agenzia_entrate": 0.18,              # Tax authority
    "agenzia_entrate_riscossione": 0.15,  # AdER rules (DEV-242)
    "inps": 0.12,                         # Social security
    "ministero_economia_documenti": 0.10, # MEF documents
    ...
}
```

**Pattern:** When adding a new authoritative source:
1. Add to `DocumentSource` enum in `app/models/regulatory_documents.py`
2. Add to `SOURCE_AUTHORITY_WEIGHTS` in `app/core/config.py`
3. Without weight, new sources rank lower than existing ones

### Grounding Rules Architecture

Location: `app/orchestrators/prompting.py` (injected before KB context)

**Structure (DEV-242 Phase 28-39):**
```
## REGOLE CRITICHE PER LA RISPOSTA (DEV-242)

### FORMATO RISPOSTA (Phase 39)
- NO markdown headers (#, ##, ###)
- USE numbered list: `1. **Label**: Content...`

### ACCURATEZZA
- Use only KB data
- Copy exact values
- Cite sources

### COMPLETEZZA OBBLIGATORIA
- Table of required elements for fiscal procedures
- Scadenza, Prima rata, Tasso interessi, etc.

### ESTRAZIONE DATI NUMERICI (Phase 33)
- Pattern scanning for percentages, dates, penalties
- "3 per cento annuo" → MUST appear in response

### ESTRAZIONE OBBLIGATORIA ROTTAMAZIONE (Phase 34/37)
- Domain-specific extraction rules
- 5-day tolerance warning
- Decadenza rule

### ECCELLENZA PROFESSIONALE (Phase 31/39)
- Content quality rules (KEEP)
- NO formatting structure rules (REMOVED - caused large headers)
```

**Critical Lesson (DEV-242 Phase 39):**
Formatting instructions like "STRUTTURA OPERATIVA" with section headers (✅ COSA FARE, ⚠️ RISCHI) cause the LLM to use large markdown headers (`# 1. Title`), breaking the clean numbered list format. Keep formatting rules minimal and explicit.

### Recurring Source Ingestion Patterns

For sources without RSS feeds, use web scraper pattern:

| Source Type | Implementation | Example |
|-------------|----------------|---------|
| RSS Feed | `app/ingest/rss_normativa.py` + `feed_status` table | Agenzia Entrate, INPS |
| Web Scraper | `app/services/scrapers/*.py` + scheduler task | Gazzetta, Cassazione, AdER |

**AdER Scraper Pattern (DEV-242 Phase 38):**
```python
# app/services/scrapers/ader_scraper.py
class AdERScraper:
    BASE_URL = "https://www.agenziaentrateriscossione.gov.it"

    # Topic filtering keywords
    RELEVANT_KEYWORDS = [
        "rottamazione", "definizione agevolata", "pace fiscale",
        "rateizzazione", "pagamento", "decadenza", "tolleranza",
    ]

    # Rate limiting: 2s between requests
    # Deduplication: content hash
    # Integration: KnowledgeIntegrator for DB persistence
```

**Scheduler Registration:**
```python
# app/services/scheduler_service.py
ader_scraper_task = ScheduledTask(
    name="ader_scraper_daily",
    interval=ScheduleInterval.DAILY,
    function=scrape_ader_task,
    target_time=rss_collection_time,  # 01:00 Europe/Rome
)
```

### Multi-Query Expansion

Location: `app/services/multi_query_generator.py`

**Pattern:** Add semantic expansions for domain-specific terms to improve retrieval:

```python
semantic_expansions = {
    "rottamazione": [
        "definizione agevolata", "pace fiscale",
        "tolleranza", "decadenza", "rate", "pagamento"
    ],
    ...
}
```

**Lesson (DEV-242 Phase 35):** Missing semantic expansions cause relevant chunks (like AdER rules with "tolleranza" keyword) to rank too low in BM25 search.

### Prompt Injection Points

Understanding where rules have highest impact:

| Injection Point | File | LLM Attention | Use For |
|-----------------|------|---------------|---------|
| System prompt | `app/core/prompts/system.md` | Medium | Base behavior |
| Domain templates | `PromptTemplateManager` | Medium | Domain-specific |
| **Grounding rules** | `app/orchestrators/prompting.py` | **HIGH** | Critical rules |
| Response format | `unified_response_simple.md` | Low | JSON schema |

**Critical:** Rules injected RIGHT BEFORE KB context (grounding_rules) get highest LLM attention because they're closest to the retrieval context the LLM needs to process.

### Decision Framework: Response Quality Issues

When debugging response quality, systematically check:

```
1. RETRIEVAL COMPLETENESS
   - Are relevant chunks in TOP-K? (check chunk IDs in logs)
   - Is CONTEXT_TOP_K high enough?
   - Is the source in SOURCE_AUTHORITY_WEIGHTS?

2. CONTENT EXTRACTION
   - Are grounding rules in place for this content type?
   - Is there domain-specific extraction (like ROTTAMAZIONE rules)?
   - Are numeric patterns being scanned?

3. FORMATTING
   - Is formatting rule minimal? (no headers, just numbered list)
   - Is there conflicting structure instruction?

4. SEMANTIC EXPANSION
   - Are domain terms in semantic_expansions?
   - Is BM25 finding the right chunks?

5. SOURCE INGESTION
   - Is the source being ingested? (RSS or scraper)
   - Is there a scheduled task for recurring updates?
```

### Response Quality Checklist

Use this when reviewing response quality issues:

- [ ] Check chunk IDs retrieved (logs in step_039c)
- [ ] Verify `CONTEXT_TOP_K` includes relevant chunks
- [ ] Confirm source has authority weight
- [ ] Check semantic expansions for query terms
- [ ] Verify grounding rules have extraction patterns
- [ ] Confirm formatting rules don't force headers
- [ ] Test with target query after changes

---

## Part 10: Cost-Free Local Classification (DEV-251)

### Core Principles

| Principle | Explanation |
|-----------|-------------|
| **Local-first for simple tasks** | Use local models for high-volume, low-complexity tasks (intent classification, entity extraction). |
| **Graceful fallback** | Always have API fallback for low-confidence local predictions. |
| **Lazy loading** | Load models on first use, not at startup, to avoid cold start overhead. |
| **Singleton pattern** | One model instance in memory to avoid repeated loading. |

### Zero-Shot Classification

Zero-shot classification uses Natural Language Inference (NLI) to classify text into arbitrary categories without task-specific training:

**How It Works:**
```
Input: "Calcola IVA su 1000 euro"
Hypothesis: "Questa domanda riguarda richiesta di calcolo numerico"

NLI Model → Entailment Score: 0.89 → Intent: "calculator"
```

**Model Selection:**

| Model | Size | Latency | Italian Support | Use Case |
|-------|------|---------|-----------------|----------|
| `facebook/bart-large-mnli` | 400MB | ~50ms | Good | General purpose |
| `MoritzLaworski/mDeBERTa-v3-base-mnli-xnli` | 280MB | ~40ms | Excellent | Italian-specific |
| `dbmdz/bert-base-italian-cased` | 440MB | ~30ms | Native | Fine-tunable |

### PratikoAI Implementation Pattern

**Architecture:**

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│  Local HF Classifier            │
│  (zero-shot, CPU)               │
└──────────────┬──────────────────┘
               │
               ▼
       Confidence ≥ 0.7?
       ┌───────┴───────┐
      YES              NO
       │                │
       ▼                ▼
   Use Local        GPT Fallback
   (free)           (paid, accurate)
```

**Code Pattern:**

```python
from app.services.hf_intent_classifier import get_hf_intent_classifier

classifier = get_hf_intent_classifier()  # Singleton
result = classifier.classify(user_query)

if not classifier.should_fallback_to_gpt(result):
    # High confidence - use free local result
    routing_decision = hf_result_to_decision_dict(result)
else:
    # Low confidence - fall back to GPT-4o-mini
    decision = await router_service.route(query=user_query, history=messages)
    routing_decision = decision_to_dict(decision)
```

### Intent Label Design

**Best Practices for Zero-Shot Labels:**

| Practice | Example | Rationale |
|----------|---------|-----------|
| Use natural language descriptions | `"conversazione casuale, saluti"` NOT `"chitchat"` | Model understands descriptions |
| Include synonyms | `"calcolo numerico o computazione"` | Covers variations |
| Use target language | Italian descriptions for Italian queries | Better alignment |
| Keep descriptions concise | 5-10 words per label | Avoids confusion |

**PratikoAI Labels:**

```python
INTENT_LABELS = {
    "chitchat": "conversazione casuale, saluti, chiacchierata",
    "theoretical_definition": "richiesta di definizione o spiegazione di un concetto",
    "technical_research": "domanda tecnica complessa che richiede ricerca e analisi",
    "calculator": "richiesta di calcolo numerico o computazione",
    "golden_set": "riferimento specifico a legge, articolo, normativa o regolamento",
}
```

### Confidence Thresholds

**Threshold Selection Framework:**

| Threshold | HF Usage | GPT Fallback | Best For |
|-----------|----------|--------------|----------|
| 0.5 | High | Low | Cost-sensitive, lower accuracy OK |
| 0.7 | Medium | Medium | **Balanced (recommended)** |
| 0.9 | Low | High | Accuracy-critical |

**Monitoring Confidence Distribution:**

```
Expected Distribution (healthy system):
┌────────────────────────────────────────┐
│  < 0.5  │  ██████      │  ~15%        │  → Always fallback
│  0.5-0.7│  ████        │  ~10%        │  → Edge cases
│  > 0.7  │  ████████████│  ~75%        │  → Use local
└────────────────────────────────────────┘

Red Flags:
- >40% below threshold → Label descriptions need tuning
- >95% above threshold → Threshold may be too low
- Bimodal distribution → Domain mismatch
```

### Performance Optimization

**Lazy Loading Pattern:**

```python
class HFIntentClassifier:
    def __init__(self):
        self._classifier = None  # Not loaded yet

    def _load_model(self):
        if self._classifier is None:
            self._classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=-1,  # CPU
            )

    def classify(self, query: str) -> IntentResult:
        self._load_model()  # Load on first use
        # ... classification logic
```

**Performance Characteristics:**

| Operation | First Call | Subsequent |
|-----------|------------|------------|
| Model download | ~5s (one-time) | N/A (cached) |
| Model load | ~2s | N/A (in memory) |
| Classification | ~50-100ms | ~50-100ms |

**Memory Management:**
- Model stays in memory after first load
- ~400MB RAM for BART-large-mnli
- Consider model unloading for memory-constrained environments

### Cost Analysis

**Comparison with API-based Classification:**

| Approach | Cost/1000 queries | Latency | Accuracy |
|----------|-------------------|---------|----------|
| GPT-4o-mini | $0.60-1.00 | ~200ms | 95%+ |
| Local Zero-Shot | $0.00 | ~50ms | 80-85% |
| Hybrid (70% local) | $0.18-0.30 | ~80ms avg | 90%+ |

**Monthly Savings (1M queries):**

```
Before (100% GPT-4o-mini):  ~$800/month
After (70% local, 30% GPT): ~$240/month
Savings: $560/month (~70%)
```

### Future Path: Fine-Tuning

**Phase 1 (Current):** Zero-shot classification (no training data needed)
**Phase 2 (DEV-253):** Expert labeling UI to collect training data
**Phase 3 (Future):** Fine-tune Italian BERT model

**Expected Accuracy Improvement:**

| Approach | Accuracy | Training Data |
|----------|----------|---------------|
| Zero-shot | 80-85% | None |
| Fine-tuned (1k samples) | 88-92% | 1,000 labels |
| Fine-tuned (10k samples) | 93-97% | 10,000 labels |

### Decision Framework: Local vs API Classification

When deciding whether to use local classification, systematically ask:

```
1. VOLUME
   - How many classifications per day?
   - Is cost a significant factor?
   - (>10k/day strongly favors local)

2. ACCURACY REQUIREMENTS
   - What's the acceptable error rate?
   - Are errors recoverable downstream?
   - (>5% error tolerance enables local)

3. LATENCY REQUIREMENTS
   - Is real-time response needed?
   - What's the p95 latency budget?
   - (Local is 2-4x faster than API)

4. COMPLEXITY
   - How many categories?
   - Are categories well-defined?
   - (5-10 categories ideal for zero-shot)

5. FALLBACK STRATEGY
   - Is API fallback acceptable?
   - What's the confidence threshold?
   - (Always have fallback for low-confidence)
```

### Local Classification Checklist

Use this when implementing local classification:

- [ ] Model selected based on language and accuracy needs
- [ ] Lazy loading implemented (no startup cost)
- [ ] Singleton pattern prevents multiple model loads
- [ ] Confidence threshold tuned for use case
- [ ] API fallback for low-confidence predictions
- [ ] Structured logging for monitoring
- [ ] Memory impact assessed
- [ ] First-call latency acceptable
- [ ] Labels use natural language descriptions
- [ ] Tests cover edge cases (empty, long, special chars)

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2025-12-12 | Initial creation (Parts 1-5) | System |
| 2025-12-12 | Added Part 6 (Evaluation & Metrics) | System |
| 2025-12-12 | Added Part 7 (Cost Optimization) | System |
| 2025-12-12 | Added Part 8 (Italian Legal/Tax Domain) | System |
| 2026-01-12 | Added Part 9 (Response Quality & RAG Optimization - DEV-242) | System |
| 2026-01-30 | Added Part 10 (Cost-Free Local Classification - DEV-251) | System |

---

**Document Status:** Active
**Review Cadence:** Quarterly (or when new patterns emerge)
