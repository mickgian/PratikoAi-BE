# ADR-032: Automated Benchmarking Strategy

## Status
Accepted

## Date
2026-02-17

## Context

PratikoAI's RAG pipeline processes Italian labor law queries through a 134-step LangGraph pipeline. Without automated benchmarking:

- Quality regressions from model changes or prompt updates go undetected
- Performance degradation under load is discovered only by users
- Model comparison decisions (e.g., switching from GPT-4o-mini to Mistral) lack quantitative data

## Decision

### Two-axis benchmarking: Quality + Performance

**1. RAG Quality Evaluation (DeepEval)**

Golden dataset of 30-50 Italian CCNL/labor law queries evaluated with:
- **Contextual Precision** (> 0.70): Are retrieved documents relevant?
- **Faithfulness** (> 0.85): Is the answer grounded in context? (strict on hallucination)
- **Answer Relevancy** (> 0.75): Does the answer address the query?
- **Contextual Recall** (> 0.70): Are all relevant documents retrieved? (warning only)

Quality thresholds block production promotion if regressed.

**2. Performance Load Testing (k6)**

Simulates concurrent users querying the chat API:
- Ramp up to 10 concurrent users over 3 minutes
- Measures p50, p95, p99 latency and error rate
- **p95 < 5s** and **error rate < 1%** block production promotion

**3. Quality Tracking (Langfuse)**

Leverages existing Langfuse integration to store eval results as scores, creating a time-series quality dashboard across deployments.

### CI/CD Integration

Benchmarks run automatically after every QA deployment via `benchmarks.yml` workflow. Results are posted as GitHub Actions summaries and uploaded as artifacts.

## Consequences

### Positive
- Quality regressions caught before reaching production
- Quantitative basis for model comparison decisions
- Performance baseline established and tracked over time
- Langfuse provides visual quality trend dashboard

### Negative
- DeepEval evals require OpenAI API calls (~EUR 5-10/month)
- Load tests may impact QA environment performance during execution
- Golden dataset requires ongoing curation as features expand

## Related
- **ADR-025:** LLM Model Inventory & Tiering
- **ADR-028:** Deployment Pipeline Architecture
- **DEV-255:** Langfuse Observability Integration
