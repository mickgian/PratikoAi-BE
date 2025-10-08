# RAG STEP 16 — AtomicFactsExtractor.canonicalize Normalize dates amounts rates (RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates)

**Type:** process  
**Category:** facts  
**Node ID:** `CanonicalizeFacts`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `CanonicalizeFacts` (AtomicFactsExtractor.canonicalize Normalize dates amounts rates).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/facts.py:step_16__canonicalize_facts`
- **Role:** Internal
- **Status:** 🔌
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (monetary amounts, dates, legal entities, empty facts, multiple fact types, Italian number formats, routing)
- [x] Integration tests (Step 14→16→17 flow, context preservation)
- [x] Implementation changes (thin async orchestrator in app/orchestrators/facts.py)
- [x] Observability: add structured log line
  `RAG STEP 16 (RAG.facts.atomicfactsextractor.canonicalize.normalize.dates.amounts.rates): AtomicFactsExtractor.canonicalize Normalize dates amounts rates | attrs={...}`
- [x] Feature flag / config if needed (none required - validation step)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->