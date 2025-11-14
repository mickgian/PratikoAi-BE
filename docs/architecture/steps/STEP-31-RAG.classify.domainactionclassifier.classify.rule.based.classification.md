# RAG STEP 31 — DomainActionClassifier.classify Rule-based classification (RAG.classify.domainactionclassifier.classify.rule.based.classification)

**Type:** process  
**Category:** classify  
**Node ID:** `ClassifyDomain`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ClassifyDomain` (DomainActionClassifier.classify Rule-based classification).

## Current Implementation (Repo)
- **Role:** Node
- **Status:** 🔌
- **Paths / classes:** `app/orchestrators/classify.py:210` - `step_31__classify_domain()`
- **Behavior notes:** Runtime boundary; performs rule-based classification using DomainActionClassifier; routes to step 32.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing classification infrastructure

## TDD Task List
- [x] Unit tests (classification logic, domain/action scoring, Italian keywords)
- [x] Integration tests (classification flow and domain routing)
- [x] Implementation changes (async orchestrator with classification logic, domain/action scoring, Italian keywords)
- [x] Observability: add structured log line
  `RAG STEP 31 (...): ... | attrs={domain, action, confidence_score}`
- [x] Feature flag / config if needed (classification thresholds and keyword mappings)
- [x] Rollout plan (implemented with classification accuracy and performance safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: 🔌 (Implemented but Not Wired)  |  Registry: ❌ Not in registry

Notes:
- ⚠️  Node wrapper exists but not wired in graph
- Action: Wire this node in the appropriate phase
<!-- AUTO-AUDIT:END -->