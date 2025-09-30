# RAG STEP 135 — GoldenSetUpdater.auto_rule_eval new or obsolete candidates (RAG.golden.goldensetupdater.auto.rule.eval.new.or.obsolete.candidates)

**Type:** process  
**Category:** golden  
**Node ID:** `GoldenRules`

## Intent (Blueprint)
Automatically evaluates knowledge base content to identify new FAQ candidates or obsolete ones needing updates. When new knowledge content is ingested (from KnowledgeStore), this step applies rule-based evaluation to generate FAQ candidates with priority scoring. Routes successful evaluations to GoldenCandidate (Step 127) for further processing. This step is derived from the Mermaid node: `GoldenRules` (GoldenSetUpdater.auto_rule_eval new or obsolete candidates).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:1240` - `step_135__golden_rules()`
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
Status: 🔌  |  Confidence: 0.52

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.52)
   Evidence: Score 0.52, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.52)
   Evidence: Score 0.52, Publish an approved FAQ to make it available to users
3) app/orchestrators/golden.py:690 — app.orchestrators.golden.step_117__faqfeedback (score 0.50)
   Evidence: Score 0.50, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
4) app/api/v1/faq_automation.py:229 — app.api.v1.faq_automation.get_faq_candidates (score 0.49)
   Evidence: Score 0.49, Get FAQ candidates with filtering and pagination
5) app/api/v1/faq_automation.py:303 — app.api.v1.faq_automation.generate_faqs_from_candidates (score 0.48)
   Evidence: Score 0.48, Generate FAQs from selected candidates

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->