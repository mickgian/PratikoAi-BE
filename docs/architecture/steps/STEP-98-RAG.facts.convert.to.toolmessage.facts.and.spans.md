# RAG STEP 98 — Convert to ToolMessage facts and spans (RAG.facts.convert.to.toolmessage.facts.and.spans)

**Type:** process  
**Category:** facts  
**Node ID:** `ToToolResults`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToToolResults` (Convert to ToolMessage facts and spans).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/facts.py:step_98__to_tool_results`
- **Status:** ✅ Implemented
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
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/facts.py:675 — app.orchestrators.facts.step_98__to_tool_results (score 0.31)
   Evidence: Score 0.31, RAG STEP 98 — Convert to ToolMessage facts and spans
ID: RAG.facts.convert.to.to...
2) app/orchestrators/platform.py:891 — app.orchestrators.platform._convert_single_message (score 0.28)
   Evidence: Score 0.28, Convert a single message from any format to Message object.
3) app/orchestrators/platform.py:2526 — app.orchestrators.platform.step_99__tool_results (score 0.28)
   Evidence: Score 0.28, RAG STEP 99 — Return to tool caller.

ID: RAG.platform.return.to.tool.caller
Typ...
4) app/orchestrators/platform.py:2491 — app.orchestrators.platform._handle_tool_results_error (score 0.27)
   Evidence: Score 0.27, Handle errors in tool results processing with graceful fallback.
5) app/orchestrators/routing.py:94 — app.orchestrators.routing._determine_tool_type_and_routing (score 0.27)
   Evidence: Score 0.27, Determine tool type and routing destination based on tool call context.

Maps to...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->