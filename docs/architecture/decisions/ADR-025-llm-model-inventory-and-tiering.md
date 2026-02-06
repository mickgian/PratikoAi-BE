# ADR-025: LLM Model Inventory & Tiering Strategy

## Status
Accepted

## Date
2026-02-04

## Context

PratikoAI uses 10+ LLM models across 4 providers (OpenAI, Anthropic, HuggingFace local, Ollama local) for different pipeline stages. Without a documented inventory, it is difficult to:

- Understand which model serves which purpose
- Reason about cost implications of pipeline changes
- Configure Langfuse pricing definitions accurately
- Plan model upgrades or provider migrations
- Onboard new developers to the LLM architecture

The system already implements a 2-tier strategy (BASIC for internal pipeline tasks, PREMIUM for user-facing generation) but this was never formally documented.

## Decision

Adopt a **2-tier + local** model strategy with documented inventory, fallback chains, and Langfuse cost tracking.

### Tier Definitions

| Tier | Purpose | Cost Profile | Latency |
|------|---------|-------------|---------|
| **BASIC** | Routing, query expansion, HyDE, normalization, evaluation | Low (~$0.15/1M input tokens) | Fast |
| **PREMIUM** | Final answer synthesis (user-facing responses) | Higher (~$2.50/1M input tokens) | Moderate |
| **LOCAL** | Intent classification | Zero (self-hosted) | <100ms |

### Production Model Inventory

| Model | Provider | Tier | Purpose | Config Key |
|-------|----------|------|---------|------------|
| `gpt-4o-mini` | OpenAI | BASIC | Routing, multi-query, query normalization, evaluation | `LLM_MODEL_BASIC` |
| `gpt-4o` | OpenAI | PREMIUM | Main response synthesis (step_064) | `LLM_MODEL_PREMIUM` |
| `claude-3-haiku-20240307` | Anthropic | BASIC | HyDE generation, cost-optimized fallback | `HYDE_MODEL` |
| `claude-3-5-sonnet-20241022` | Anthropic | PREMIUM fallback | Fallback for gpt-4o in step_064 | YAML config |
| `text-embedding-3-small` | OpenAI | — | RAG vector embeddings (1536-d) | `EMBEDDING_MODEL` |
| `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` | HuggingFace (local) | LOCAL | Zero-shot intent classification | `HF_INTENT_MODEL` |
| `facebook/bart-large-mnli` | HuggingFace (local) | LOCAL | Alternative intent classifier | `HF_INTENT_MODEL` |

### Supported but Not Default

| Model | Provider | Notes |
|-------|----------|-------|
| `gpt-4-turbo` | OpenAI | Supported in provider, not in default YAML |
| `gpt-3.5-turbo` | OpenAI | Legacy budget option |
| `claude-3-opus-20240229` | Anthropic | Highest quality, rarely used |
| `claude-3-sonnet-20241022` | Anthropic | Standard alternative |
| `mistral:7b-instruct` | Ollama (local) | Evaluation only |

### Fallback Chains

```
BASIC tier:
  Primary:  gpt-4o-mini (OpenAI)
  Fallback: claude-3-haiku-20240307 (Anthropic)

PREMIUM tier:
  Primary:  gpt-4o (OpenAI)
  Fallback: claude-3-5-sonnet-20241022 (Anthropic)

LOCAL tier:
  Primary:  MoritzLaurer/mDeBERTa-v3-base-mnli-xnli (HuggingFace)
  Fallback: gpt-4o-mini (LLM-based router)
```

### Langfuse Model Pricing Definitions

| Model | Langfuse Status | Notes |
|-------|----------------|-------|
| `gpt-4o-mini` | Built-in | Auto-tracked |
| `gpt-4o` | Built-in | Auto-tracked |
| `gpt-4-turbo` | Built-in | Auto-tracked |
| `text-embedding-3-small` | Built-in | Auto-tracked |
| `claude-3-haiku-20240307` | Built-in | Auto-tracked |
| `claude-3-5-sonnet-20241022` | Manually cloned | Cloned from `-20240620` pricing definition |

Local HuggingFace models have zero cost and do not require Langfuse pricing definitions.

### Key Configuration Files

| File | Purpose |
|------|---------|
| `config/llm_models.yaml` | Tier definitions (BASIC/PREMIUM, models, timeouts) |
| `app/core/config.py` | Environment variable defaults |
| `app/core/llm/model_config.py` | Config loader with singleton pattern |
| `app/core/llm/factory.py` | Provider factory & routing strategy |
| `app/core/llm/providers/openai_provider.py` | OpenAI integration |
| `app/core/llm/providers/anthropic_provider.py` | Anthropic integration |
| `app/core/embed.py` | Embedding model config |
| `app/services/hf_intent_classifier.py` | HuggingFace local inference |

## Consequences

### Positive

- **Single source of truth** for all LLM model decisions
- **Cost visibility** through documented tiers and Langfuse pricing
- **Clear fallback strategy** ensures resilience across providers
- **Onboarding efficiency** — new developers can quickly understand the model landscape
- **Migration planning** — documented inventory makes model upgrades straightforward

### Negative

- Must be updated when models are added, removed, or changed
- Dual-provider strategy (OpenAI + Anthropic) adds operational complexity

## Related

- **ADR-004**: LangGraph for RAG Orchestration (pipeline where models are used)
- **ADR-002**: Hybrid Search Strategy (embedding model selection)
- **JIRA**: DEV-255
