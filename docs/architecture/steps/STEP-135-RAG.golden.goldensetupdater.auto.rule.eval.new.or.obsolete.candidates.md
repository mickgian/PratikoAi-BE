# RAG STEP 135 — GoldenSetUpdater.auto_rule_eval new or obsolete candidates (RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates)

**Type:** process  
**Category:** golden  
**Node ID:** `GoldenRules`

## Intent (Blueprint)
Automatically evaluates knowledge base content to identify new FAQ candidates or obsolete ones needing updates. When new knowledge content is ingested (from KnowledgeStore), this step applies rule-based evaluation to generate FAQ candidates with priority scoring. Routes successful evaluations to GoldenCandidate (Step 127) for further processing. This step is derived from the Mermaid node: `GoldenRules` (GoldenSetUpdater.auto_rule_eval new or obsolete candidates).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/golden.py:1240` - `step_135__golden_rules()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator that evaluates knowledge content using rule-based scoring. Applies 5 evaluation rules: content length threshold, priority category boost, recency boost, keyword boost, and minimum score filter. Creates FAQ candidates with proposed questions, confidence scores, and priority rankings. Identifies obsolete candidates when content supersedes existing entries. Preserves all context data and routes to 'golden_candidate' step.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving rule-based evaluation logic

## TDD Task List
- [x] Unit tests (evaluate knowledge content, identify obsolete candidates, apply priority rules, handle empty updates, preserve context, log evaluation details)
- [x] Parity tests (evaluation behavior verification)
- [x] Integration tests (KnowledgeStore→GoldenRules→GoldenCandidate flow, data preparation for next step)
- [x] Implementation changes (async orchestrator with rule-based evaluation logic)
- [x] Observability: add structured log line
  `RAG STEP 135 (RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates): GoldenSetUpdater.auto_rule_eval new or obsolete candidates | attrs={step, request_id, knowledge_count, candidates_generated, obsolete_identified, processing_stage}`
- [x] Feature flag / config if needed (none required - uses rule-based evaluation)
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