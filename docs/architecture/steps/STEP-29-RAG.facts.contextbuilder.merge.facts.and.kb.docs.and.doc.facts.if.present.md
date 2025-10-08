# RAG STEP 29 — ContextBuilder.merge facts and KB docs and doc facts if present (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present)

**Type:** process  
**Category:** facts  
**Node ID:** `PreContextFromGolden`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `PreContextFromGolden` (ContextBuilder.merge facts and KB docs and doc facts if present).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/facts.py:step_29__pre_context_from_golden`
- **Role:** Internal
- **Status:** 🔌
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (golden+KB merge, atomic facts, optional document facts, empty KB deltas, routing, context preservation)
- [x] Integration tests (KBDelta=Yes path, context preservation for Step 39)
- [x] Implementation changes (thin async orchestrator wrapping ContextBuilderMerge service)
- [x] Observability: add structured log line
  `RAG STEP 29 (RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.doc.facts.if.present): ContextBuilder.merge facts and KB docs and doc facts if present | attrs={...}`
- [x] Feature flag / config if needed (uses existing ContextBuilderMerge configuration)
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