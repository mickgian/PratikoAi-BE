# RAG STEP 127 — GoldenSetUpdater.propose_candidate from expert feedback (RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback)

**Type:** process
**Category:** golden
**Node ID:** `GoldenCandidate`

## Intent (Blueprint)
Proposes a new FAQ candidate for the Golden Set based on expert feedback. When an expert provides improved answers and corrections, this step transforms that feedback into a structured FAQ candidate with priority scoring, quality metrics, and regulatory references. The candidate is then routed to GoldenApproval (Step 128) for approval decision. This step is derived from the Mermaid node: `GoldenCandidate` (GoldenSetUpdater.propose_candidate from expert feedback).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/golden.py:step_127__golden_candidate`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator that transforms expert feedback into FAQ candidate. Extracts expert feedback data (query, answer, category, regulatory refs, confidence), calculates priority score based on confidence × trust × frequency, derives quality score from expert metrics, and routes to GoldenApproval (Step 128) with candidate metadata.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing workflow

## TDD Task List
- [x] Unit tests (propose candidate, priority calculation, regulatory refs preservation, context preservation, metadata, missing category, error handling, logging)
- [x] Parity tests (candidate creation behavior verification)
- [x] Integration tests (DetermineAction→GoldenCandidate→GoldenApproval flow, data preparation for approval)
- [x] Implementation changes (async orchestrator creating FAQ candidate from expert feedback)
- [x] Observability: add structured log line
  `RAG STEP 127 (RAG.golden.goldensetupdater.propose.candidate.from.expert.feedback): GoldenSetUpdater.propose_candidate from expert feedback | attrs={candidate_id, priority_score, quality_score, expert_confidence, category, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing workflow)
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