# RAG STEP 95 — Extractor.extract Structured fields (RAG.facts.extractor.extract.structured.fields)

**Type:** process  
**Category:** facts  
**Node ID:** `ExtractDocFacts`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractDocFacts` (Extractor.extract Structured fields).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/facts.py:588` - `step_95__extract_doc_facts()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator extracting structured facts from parsed documents using AtomicFactsExtractor. Identifies monetary amounts, dates, legal entities, and domain-specific fields. Routes to Step 98 (ToToolResults) for result formatting.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (fact extraction, atomic facts processing, context building)
- [x] Integration tests (fact processing flow and context integration)
- [x] Implementation changes (async orchestrator with fact extraction, atomic facts processing, context building)
- [x] Observability: add structured log line
  `RAG STEP 95 (...): ... | attrs={fact_count, extraction_confidence, context_size}`
- [x] Feature flag / config if needed (fact extraction settings and confidence thresholds)
- [x] Rollout plan (implemented with fact extraction accuracy and context quality safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->