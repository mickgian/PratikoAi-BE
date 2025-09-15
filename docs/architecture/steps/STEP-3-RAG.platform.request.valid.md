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
Status: ❌  |  Confidence: 0.29

Top candidates:
1) app/core/security/request_signing.py:148 — app.core.security.request_signing.RequestSigner._is_timestamp_valid (score 0.29)
   Evidence: Score 0.29, Check if timestamp is within acceptable range.

Args:
    timestamp_str: Unix ti...
2) version-management/cli/version_cli.py:227 — version-management.cli.version_cli.VersionCLI.check_compatibility (score 0.27)
   Evidence: Score 0.27, Check compatibility for a version deployment.
3) app/core/hash_gate.py:26 — app.core.hash_gate.HashGate.check_delta (score 0.26)
   Evidence: Score 0.26, Check if this delta has been seen before.

Args:
    delta: The delta content to...
4) app/jobs/data_export_jobs.py:73 — app.jobs.data_export_jobs.process_export_request (score 0.26)
   Evidence: Score 0.26, Process a data export request asynchronously.

Args:
    export_id: UUID of the ...
5) app/models/cassazione_data.py:217 — app.models.cassazione_data.Citation.is_valid (score 0.26)
   Evidence: Score 0.26, Validate the citation.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for ValidCheck
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->