# RAG STEP 98 — Convert to ToolMessage facts and spans (RAG.facts.convert.to.toolmessage.facts.and.spans)

**Type:** process  
**Category:** facts  
**Node ID:** `ToToolResults`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToToolResults` (Convert to ToolMessage facts and spans).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/facts.py:step_98__to_tool_results`
- **Status:** 🔌
- **Behavior notes:** Thin async orchestrator that converts extracted document facts and provenance into ToolMessage format for returning to the LLM tool caller. Formats facts into readable content, includes provenance metadata, and creates langchain ToolMessage. Routes to Step 99 (ToolResults).

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing fact extraction infrastructure

## TDD Task List
- [x] Unit tests (ToolMessage conversion, facts formatting, provenance metadata, empty facts, multiple document types, routing, context preservation)
- [x] Integration tests (Step 97→98 flow, Step 99 preparation)
- [x] Implementation changes (thin async orchestrator creating ToolMessage from facts)
- [x] Observability: add structured log line
  `RAG STEP 98 (RAG.facts.convert.to.toolmessage.facts.and.spans): Convert to ToolMessage facts and spans | attrs={...}`
- [x] Feature flag / config if needed (none required - standard conversion)
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