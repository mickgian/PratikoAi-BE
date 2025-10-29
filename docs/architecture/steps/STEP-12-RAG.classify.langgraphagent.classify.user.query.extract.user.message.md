# RAG STEP 12 — LangGraphAgent._classify_user_query Extract user message (RAG.classify.langgraphagent.classify.user.query.extract.user.message)

**Type:** process  
**Category:** classify  
**Node ID:** `ExtractQuery`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractQuery` (LangGraphAgent._classify_user_query Extract user message).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/classify.py:16` - `step_12__extract_query()`
- **Role:** Internal
- **Status:** 🔌
- **Behavior notes:** Internal transform within parent node; [processing description].
## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing classification infrastructure

## TDD Task List
- [x] Unit tests (classification logic, domain/action scoring, Italian keywords)
- [x] Integration tests (classification flow and domain routing)
- [x] Implementation changes (async orchestrator with classification logic, domain/action scoring, Italian keywords)
- [x] Observability: add structured log line
  `RAG STEP 12 (...): ... | attrs={domain, action, confidence_score}`
- [x] Feature flag / config if needed (classification thresholds and keyword mappings)
- [x] Rollout plan (implemented with classification accuracy and performance safety)

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