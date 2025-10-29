# RAG STEP 18 — QuerySignature.compute Hash from canonical facts (RAG.facts.querysignature.compute.hash.from.canonical.facts)

**Type:** process  
**Category:** facts  
**Node ID:** `QuerySig`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `QuerySig` (QuerySignature.compute Hash from canonical facts).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/facts.py:114` - `step_18__query_sig()`
- **Role:** Internal
- **Status:** 🔌
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (signature computation, identical facts, different facts, empty facts, deterministic hashing, all fact types, routing)
- [x] Integration tests (Step 16→18 flow, context preservation)
- [x] Implementation changes (thin async orchestrator in app/orchestrators/facts.py)
- [x] Observability: add structured log line
  `RAG STEP 18 (RAG.facts.querysignature.compute.hash.from.canonical.facts): QuerySignature.compute Hash from canonical facts | attrs={...}`
- [x] Feature flag / config if needed (none required - core functionality)
- [x] Rollout plan (implemented with comprehensive tests)

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