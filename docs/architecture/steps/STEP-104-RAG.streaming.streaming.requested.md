# RAG STEP 104 — Streaming requested? (RAG.streaming.streaming.requested)

**Type:** decision  
**Category:** streaming  
**Node ID:** `StreamCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `StreamCheck` (Streaming requested?).

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
  `RAG STEP 104 (RAG.streaming.streaming.requested): Streaming requested? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.28

Top candidates:
1) app/core/streaming_guard.py:19 — app.core.streaming_guard.SinglePassStream.__init__ (score 0.28)
   Evidence: Score 0.28, method: __init__
2) app/core/streaming_guard.py:23 — app.core.streaming_guard.SinglePassStream.__aiter__ (score 0.28)
   Evidence: Score 0.28, method: __aiter__
3) version-management/cli/version_cli.py:227 — version-management.cli.version_cli.VersionCLI.check_compatibility (score 0.26)
   Evidence: Score 0.26, Check compatibility for a version deployment.
4) app/core/hash_gate.py:26 — app.core.hash_gate.HashGate.check_delta (score 0.26)
   Evidence: Score 0.26, Check if this delta has been seen before.

Args:
    delta: The delta content to...
5) validate_italian_implementation.py:8 — validate_italian_implementation.check_file_exists (score 0.26)
   Evidence: Score 0.26, Check if a file exists and return status.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for StreamCheck
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->