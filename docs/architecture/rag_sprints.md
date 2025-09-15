# PratikoAI RAG — Multi-Sprint Plan

This plan sequences the 135 RAG steps into pragmatic sprints with clear scope and commands to open/issues per sprint.

> Single source of truth: `docs/architecture/diagrams/pratikoai_rag.mmd`  
> Backlog view: `docs/architecture/rag_conformance.md`  
> Step docs live in: `docs/architecture/steps/STEP-*.md`

---

## Sprint 0 — Foundations & Guardrails (prep)

**Goals**
- Ensure tooling works: `gh`, `jq`, audit scripts.
- Adopt `rag_logging` (no behavior change).

**Checklist**
- [ ] `brew install gh jq` (or apt/yum equivalents)
- [ ] `python scripts/rag_code_graph.py --write`
- [ ] `python scripts/rag_audit.py --write`
- [ ] Verify no duplicate backlog files and dashboard is current.

_No step closures planned here._

---

## Sprint 1 — Core Pipeline (Week 1)

**Steps**: 20, 39, 59, 79, 82, 64  
- 20 Golden fast-path gate  
- 39 KBPreFetch (BM25+vector+recency)  
- 59 CheckCache (response cache key)  
- 79 Tool type? (router)  
- 82 DocIngest pipeline scaffold  
- 64 LLMCall (provider invocation)

**Create issues**
```bash
python scripts/rag_issue_prompter.py --create \
  --steps 20,39,59,79,82,64 \
  --status "❌,🔌" \
  --labels "priority/high,team/rag,sprint/1-core"
  ```
Success criteria

LLM calls reduced by >30% via Golden fast-path

KB retrieval < 200ms P50

Cache hit rate > 60%

Router correctness > 95%

DocIngest skeleton in place (no security holes)

## Sprint 2 — Retrieval & Prompting
**Steps**: 26, 27, 40, 41, 42, 43, 44, 45, 46, 47

26 KBContextCheck

27 KBDelta (freshness vs Golden, RSS conflicts)

40 BuildContext

41 SelectPrompt

42 ClassConfidence (≥ 0.6)

43 DomainPrompt

44 DefaultSysPrompt

45 CheckSysMsg

46 ReplaceMsg

47 InsertMsg

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 26,27,40,41,42,43,44,45,46,47 \
  --status "❌,🔌,🟡" \
  --labels "priority/high,team/rag,sprint/2-retrieval"

## Sprint 3 — Providers, Routing & Cache Hardening
**Steps**: 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 65, 66, 67, 68, 69, 70, 71, 72, 73

Focus

Deterministic provider selection & routing strategies

Epoch/versioned cache keys, solid hit/miss paths

Retry/failover/error handling

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 48,49,50,51,52,53,54,55,56,57,58,60,61,62,63,65,66,67,68,69,70,71,72,73 \
  --status "❌,🔌,🟡" \
  --labels "team/rag,sprint/3-providers-cache"
## Sprint 4 — Document Ingest (Part I: validation & security)
**Steps**: 84, 85, 86, 87, 88, 89, 95, 96, 97, 98, 99

Validation → error path

Sanitization & classification

Extraction → tool results, storage & provenance

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 84,85,86,87,88,89,95,96,97,98,99 \
  --status "❌,🔌,🟡" \
  --labels "team/rag,sprint/4-doc-ingest-I"

## Sprint 5 — Document Ingest (Part II: parsers)
**Steps**: 90, 91, 92, 93, 94

Fattura XML (XSD), F24 OCR, Contract, Payslip, Generic OCR

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 90,91,92,93,94 \
  --status "❌,🔌,🟡" \
  --labels "team/rag,sprint/5-doc-ingest-II"

## Sprint 6 — Golden Set / FAQ pipeline
**Steps**: 24, 25, 28, 29, 83, 130, 131

Golden match & thresholds

ServeGolden / merge context

FAQ tool wire-up

Invalidate + vector reindex

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 24,25,28,29,83,130,131 \
  --status "❌,🔌,🟡" \
  --labels "team/rag,sprint/6-golden"

## Sprint 7 — KB & RSS Integration
**Steps**: 39 (enhance), 132, 133, 134, 26 (enhance), 27 (enhance)

RSS monitor → parse → KB store

Ensure KB prefetch always includes RSS-fresh context

Tighten freshness/override logic

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 39,132,133,134,26,27 \
  --status "❌,🔌,🟡" \
  --labels "team/rag,sprint/7-kb-rss"

## Sprint 8 — Classification & Facts
**Steps**: 12, 13, 14, 16, 17, 18, 19, 21, 22, 23, 31, 32, 33, 34, 35, 36, 37, 38

Query extraction & atomic facts

Attachment fingerprint & query signature

Attach gating & pre-ingest & doc-dependence

Domain/action classification with metrics

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 12,13,14,16,17,18,19,21,22,23,31,32,33,34,35,36,37,38 \
  --status "❌,🔌,🟡" \
  --labels "team/rag,sprint/8-classify-facts"

## Sprint 9 — Response & Streaming
**Steps**: 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 101,102,103,104,105,106,107,108,109,110,111,112 \
  --status "❌,🔌,🟡" \
  --labels "team/rag,sprint/9-response-streaming"

##  Sprint 10 — Feedback Loop & Golden Updates
**Steps**: 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129 \
  --status "❌,🔌,🟡" \
  --labels "team/rag,sprint/10-feedback"

## Sprint 11 — Platform/Privacy & Early Steps
**Steps**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 30

Create issues

bash
Copia codice
python scripts/rag_issue_prompter.py --create \
  --steps 1,2,3,4,5,6,7,8,9,10,15,30 \
  --status "❌,🔌,🟡" \
  --labels "team/rag,sprint/11-platform-privacy"