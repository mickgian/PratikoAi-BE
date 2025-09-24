# RAG STEP 15 — Continue without classification (RAG.prompting.continue.without.classification)

**Type:** process  
**Category:** prompting  
**Node ID:** `DefaultPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DefaultPrompt` (Continue without classification).

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
  `RAG STEP 15 (RAG.prompting.continue.without.classification): Continue without classification | attrs={...}`
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
1) app/orchestrators/prompting.py:14 — app.orchestrators.prompting.step_15__default_prompt (score 0.29)
   Evidence: Score 0.29, RAG STEP 15 — Continue without classification
ID: RAG.prompting.continue.without...
2) app/orchestrators/prompting.py:203 — app.orchestrators.prompting._get_default_system_prompt (score 0.28)
   Evidence: Score 0.28, Get appropriate default system prompt based on query analysis.
3) app/orchestrators/prompting.py:470 — app.orchestrators.prompting.step_44__default_sys_prompt (score 0.28)
   Evidence: Score 0.28, RAG STEP 44 — Use default SYSTEM_PROMPT
ID: RAG.prompting.use.default.system.pro...
4) app/orchestrators/classify.py:829 — app.orchestrators.classify.step_43__domain_prompt (score 0.26)
   Evidence: Score 0.26, RAG STEP 43 — PromptTemplateManager.get_prompt Get domain-specific prompt
ID: RA...
5) app/orchestrators/prompting.py:211 — app.orchestrators.prompting.step_41__select_prompt (score 0.26)
   Evidence: Score 0.26, RAG STEP 41 — LangGraphAgent._get_system_prompt Select appropriate prompt
ID: RA...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DefaultPrompt
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->