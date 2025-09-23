# RAG STEP 3 — Request valid? (RAG.platform.request.valid)

**Type:** decision  
**Category:** platform  
**Node ID:** `ValidCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidCheck` (Request valid?).

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
  `RAG STEP 3 (RAG.platform.request.valid): Request valid? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/platform.py:317 — app.orchestrators.platform.step_3__valid_check (score 0.31)
   Evidence: Score 0.31, RAG STEP 3 — Request valid?
ID: RAG.platform.request.valid
Type: decision | Cate...
2) app/core/security/request_signing.py:148 — app.core.security.request_signing.RequestSigner._is_timestamp_valid (score 0.29)
   Evidence: Score 0.29, Check if timestamp is within acceptable range.

Args:
    timestamp_str: Unix ti...
3) app/orchestrators/kb.py:14 — app.orchestrators.kb.step_26__kbcontext_check (score 0.27)
   Evidence: Score 0.27, RAG STEP 26 — KnowledgeSearch.context_topk fetch recent KB for changes
ID: RAG.k...
4) version-management/cli/version_cli.py:227 — version-management.cli.version_cli.VersionCLI.check_compatibility (score 0.27)
   Evidence: Score 0.27, Check compatibility for a version deployment.
5) app/core/hash_gate.py:26 — app.core.hash_gate.HashGate.check_delta (score 0.26)
   Evidence: Score 0.26, Check if this delta has been seen before.

Args:
    delta: The delta content to...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->