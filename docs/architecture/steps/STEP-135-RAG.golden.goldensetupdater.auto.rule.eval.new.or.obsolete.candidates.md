# RAG STEP 135 — GoldenSetUpdater.auto_rule_eval new or obsolete candidates (RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates)

**Type:** process  
**Category:** golden  
**Node ID:** `GoldenRules`

## Intent (Blueprint)
Automatically evaluates knowledge base content to identify new FAQ candidates or obsolete ones needing updates. When new knowledge content is ingested (from KnowledgeStore), this step applies rule-based evaluation to generate FAQ candidates with priority scoring. Routes successful evaluations to GoldenCandidate (Step 127) for further processing. This step is derived from the Mermaid node: `GoldenRules` (GoldenSetUpdater.auto_rule_eval new or obsolete candidates).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_135__golden_rules`
- **Status:** ✅ Implemented
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
Status: ✅  |  Confidence: 1.00

Implementation:
- app/orchestrators/golden.py:1084 — step_135__golden_rules (async orchestrator)
- tests/test_rag_step_135_golden_rules.py — 9 comprehensive tests (all passing)

Key Features:
- Async orchestrator evaluating knowledge content for FAQ candidates
- Rule-based evaluation with 5 scoring criteria (content length, category priority, recency, keywords, minimum score)
- Obsolete candidate identification when content supersedes existing entries
- Priority scoring system with configurable thresholds and weights
- Structured logging with rag_step_log (step 135, processing stages)
- Context preservation (user/session data, metadata, original knowledge updates)
- Candidate generation metadata tracking (candidates_generated, obsolete_identified, success)
- Routes to 'golden_candidate' (Step 127) per Mermaid flow

Test Coverage:
- Unit: knowledge content evaluation, obsolete identification, priority rules, empty updates handling, context preservation, logging
- Parity: evaluation behavior verification
- Integration: KnowledgeStore→GoldenRules→GoldenCandidate flow, data preparation

Evaluation Rules:
1. Content length threshold (min 100 chars default)
2. Priority category boost (+0.3 score for priority categories)
3. Recency boost (+0.2 if within threshold days)
4. Priority keyword boost (+0.1 per keyword match)
5. Minimum priority score filter (0.6 default threshold)

Notes:
- Full implementation complete following MASTER_GUARDRAILS
- Thin orchestrator pattern (coordination only, no external service dependencies)
- All TDD tasks completed
- Routes from KnowledgeStore to GoldenCandidate as per Mermaid diagram
<!-- AUTO-AUDIT:END -->