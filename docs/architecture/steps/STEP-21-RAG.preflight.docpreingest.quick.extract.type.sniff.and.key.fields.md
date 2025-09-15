# RAG STEP 21 — DocPreIngest.quick_extract type sniff and key fields (RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields)

**Type:** process  
**Category:** preflight  
**Node ID:** `QuickPreIngest`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `QuickPreIngest` (DocPreIngest.quick_extract type sniff and key fields).

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
  `RAG STEP 21 (RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields): DocPreIngest.quick_extract type sniff and key fields | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.26

Top candidates:
1) app/services/domain_action_classifier.py:530 — app.services.domain_action_classifier.DomainActionClassifier._extract_document_type (score 0.26)
   Evidence: Score 0.26, Extract document type for document generation actions
2) app/services/scrapers/cassazione_scraper.py:443 — app.services.scrapers.cassazione_scraper.CassazioneScraper._extract_decision_type (score 0.26)
   Evidence: Score 0.26, Extract decision type.
3) app/services/legal_document_analyzer.py:950 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_key_clauses (score 0.26)
   Evidence: Score 0.26, Extract important contract clauses
4) app/services/rss_feed_monitor.py:388 — app.services.rss_feed_monitor.RSSFeedMonitor._extract_agenzia_entrate_type (score 0.26)
   Evidence: Score 0.26, Extract document type from Agenzia Entrate feed URL.

Args:
    feed_url: RSS fe...
5) app/ragsteps/golden/step_20_rag_golden_golden_fast_path_eligible_no_doc_or_quick_check_safe.py:18 — app.ragsteps.golden.step_20_rag_golden_golden_fast_path_eligible_no_doc_or_quick_check_safe.step_20_rag_golden_golden_fast_path_eligible_no_doc_or_quick_check_safe (score 0.26)
   Evidence: Score 0.26, RAG STEP 20 — Golden fast-path eligible? no doc or quick check safe

Node: Golde...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for QuickPreIngest
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->