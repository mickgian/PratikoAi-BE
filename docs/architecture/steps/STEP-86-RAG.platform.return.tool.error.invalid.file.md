# RAG STEP 86 — Return tool error Invalid file (RAG.platform.return.tool.error.invalid.file)

**Type:** error  
**Category:** platform  
**Node ID:** `ToolErr`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolErr` (Return tool error Invalid file).

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
  `RAG STEP 86 (RAG.platform.return.tool.error.invalid.file): Return tool error Invalid file | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.20

Top candidates:
1) app/services/italian_tax_calculator.py:68 — app.services.italian_tax_calculator.InvalidIncomeError (score 0.20)
   Evidence: Score 0.20, Raised when income value is invalid.
2) app/services/italian_tax_calculator.py:73 — app.services.italian_tax_calculator.InvalidLocationError (score 0.20)
   Evidence: Score 0.20, Raised when location cannot be found or is invalid.
3) app/services/italian_tax_calculator.py:78 — app.services.italian_tax_calculator.InvalidTaxTypeError (score 0.20)
   Evidence: Score 0.20, Raised when tax type is not supported.
4) evals/main.py:64 — evals.main.print_error (score 0.19)
   Evidence: Score 0.19, Print an error message with colors.

Args:
    message: The message to print
5) app/models/document.py:130 — app.models.document.Document.file_size_mb (score 0.19)
   Evidence: Score 0.19, File size in megabytes

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for ToolErr
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->