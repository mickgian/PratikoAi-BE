# DEV-252: AI Agent Evaluation Framework

## Overview

This ticket implements a comprehensive evaluation framework for the PratikoAI RAG system, following Anthropic's best practices for AI agent evaluation.

## Implementation Phases

### Phase 1: Email Integration ✅

**Status**: COMPLETE

Added email delivery service for evaluation reports:
- `evals/services/email_delivery.py` - SendGrid-based email service
- HTML/plain text report formatting
- Metrics summary in email body

### Phase 2: Automatic Scheduling ✅

**Status**: COMPLETE

Integrated evaluation scheduling with existing scheduler:
- `app/services/scheduler_service.py` - Added nightly/weekly eval jobs
- Cron schedules: nightly at 2 AM, weekly on Sunday at 3 AM
- Email notifications after each run

### Phase 3: Ollama Installation ✅

**Status**: COMPLETE

Installed Ollama for LLM-as-judge evaluation:
- Ollama v0.15.2 via Homebrew
- Model: `mistral:7b-instruct` (4.4 GB)
- Running as persistent service via `brew services start ollama`
- API endpoint: `http://localhost:11434`

### Phase 4: System Integration 🔄

**Status**: IN PROGRESS

Implementing the connection between evaluation runner and RAG system:

#### Components

1. **SystemInvoker** (`evals/services/system_invoker.py`)
   - Invokes RAG components based on test category
   - Handles dependency initialization
   - Returns outputs in grader-expected format

2. **Runner Integration** (`evals/runner.py`)
   - `_grade_test_case()` routes to appropriate grader
   - Supports code-based and model-based grading
   - Ollama integration for LLM-as-judge

#### Test Category Mapping

| Category | RAG Component | Grader |
|----------|--------------|--------|
| `routing` | `LLMRouterService.route()` | `RoutingGrader` |
| `retrieval` | `KnowledgeSearchService.search()` | `RetrievalGrader` |
| `response` | `LangGraphAgent.get_response()` | `CitationGrader` + `OllamaJudge` |

## Evaluation Framework Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Test Cases    │────▶│   EvalRunner    │────▶│    Reports      │
│  (JSON files)   │     │                 │     │  (JSON + Email) │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │  Routing  │ │ Retrieval │ │ Response  │
            │  Grader   │ │  Grader   │ │  Grader   │
            └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
                  │             │             │
                  ▼             ▼             ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │   LLM     │ │    KB     │ │ LangGraph │
            │  Router   │ │  Search   │ │   Agent   │
            └───────────┘ └───────────┘ └───────────┘
```

## Graders

### Code-Based Graders (Fast, Deterministic)

1. **RoutingGrader** - Evaluates query routing decisions
   - Metrics: route accuracy, entity F1, confidence calibration
   - Weights: 60% route, 30% entity F1, 10% calibration

2. **RetrievalGrader** - Evaluates document retrieval quality
   - Metrics: precision@k, recall@k, MRR, NDCG
   - Weights: 35% recall, 25% precision, 20% MRR, 15% NDCG, 5% authority

3. **CitationGrader** - Evaluates citation accuracy
   - Metrics: hallucination rate, valid citation ratio, recall
   - Italian legal citation patterns (Legge, D.Lgs., Art., Circolare)

### Model-Based Grader (Ollama LLM-as-Judge)

**OllamaJudge** - Uses local Mistral 7B for response quality evaluation
- Italian legal accuracy rubric (0.0-1.0 scale)
- Evaluates: citation correctness, article accuracy, date validity
- Zero-cost local evaluation

## Configuration Modes

| Mode | Graders | Threshold | Use Case |
|------|---------|-----------|----------|
| `fast` | code only | 90% | Quick local check |
| `local` | code + model | 90% | Development |
| `pr` | code only | 100% | PR blocking |
| `nightly` | code + model | 100% | Scheduled |
| `weekly` | code + model | 100% | Extended |

## Usage

```bash
# Quick check (code graders only)
uv run python -m evals.runner --config fast

# Full local check with Ollama
uv run python -m evals.runner --config local --use-ollama

# Run specific category
uv run python -m evals.runner --config local --category routing

# Nightly evaluation (scheduled automatically)
uv run python -m evals.runner --config nightly --use-ollama
```

## Test Cases Location

```
evals/datasets/
├── regression/
│   ├── routing_known_good.json      # 10 routing test cases
│   ├── retrieval_known_good.json    # 5 retrieval test cases
│   └── response_known_good.json     # 5 response test cases
└── capability/                       # Hard cases for improvement
```

## Reports

Reports are generated in `evals/reports/` with format:
- `eval_report_YYYYMMDD_HHMMSS.json`

For nightly/weekly runs, email reports are sent via SendGrid.

## Related ADRs

- ADR-013: TDD Mandatory
- ADR-016: E2E RSS Testing (real LLM calls in CI)
