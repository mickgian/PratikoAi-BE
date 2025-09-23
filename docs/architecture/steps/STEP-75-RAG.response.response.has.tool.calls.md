# RAG STEP 75 — Response has tool_calls? (RAG.response.response.has.tool.calls)

**Type:** process  
**Category:** response  
**Node ID:** `ToolCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolCheck` (Response has tool_calls?).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 75 (RAG.response.response.has.tool.calls): Response has tool_calls? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.34

Top candidates:
1) app/orchestrators/response.py:180 — app.orchestrators.response.step_75__tool_check (score 0.34)
   Evidence: Score 0.34, RAG STEP 75 — Response has tool_calls?
ID: RAG.response.response.has.tool.calls
...
2) app/api/v1/italian.py:65 — app.api.v1.italian.ComplianceCheckResponse (score 0.26)
   Evidence: Score 0.26, Compliance check response.
3) app/orchestrators/kb.py:14 — app.orchestrators.kb.step_26__kbcontext_check (score 0.26)
   Evidence: Score 0.26, RAG STEP 26 — KnowledgeSearch.context_topk fetch recent KB for changes
ID: RAG.k...
4) app/orchestrators/kb.py:32 — app.orchestrators.kb.step_80__kbquery_tool (score 0.26)
   Evidence: Score 0.26, RAG STEP 80 — KnowledgeSearchTool.search KB on demand
ID: RAG.kb.knowledgesearch...
5) version-management/cli/version_cli.py:227 — version-management.cli.version_cli.VersionCLI.check_compatibility (score 0.26)
   Evidence: Score 0.26, Check compatibility for a version deployment.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->