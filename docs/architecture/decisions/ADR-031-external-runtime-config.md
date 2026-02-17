# ADR-031: External Runtime Configuration (Flagsmith)

## Status
Accepted

## Date
2026-02-17

## Context

PratikoAI has ~50 configuration values spread across `app/core/config.py` (module-level `os.getenv()` calls and `Settings` class attributes) and YAML config files (`config/llm_models.yaml`, `config/billing_plans.yaml`). All configuration changes currently require:

1. Modifying environment variables or code
2. Restarting the application (or full redeployment)

This creates friction for operations that should be instant:
- Switching LLM models during an outage (e.g., GPT-4o down, switch to Claude)
- Adjusting RAG retrieval weights based on quality metrics
- Enabling/disabling features as kill switches
- Tuning confidence thresholds based on user feedback

We evaluated two approaches:
- **Firebase Remote Config:** Google-hosted, mature SDK, but stores data on Google servers (GDPR concern for EU user data residency)
- **Flagsmith:** Open source (BSD-3-Clause), self-hostable on Hetzner, supports both feature flags AND remote config values

## Decision

### Self-hosted Flagsmith on Hetzner

Deploy Flagsmith as a Docker service alongside the application stack. This provides:

1. **Feature flags** (boolean kill switches)
2. **Remote config values** (strings, numbers for model names, weights, thresholds)
3. **EU data residency** (self-hosted on Hetzner, GDPR compliant per ADR-006)
4. **Zero vendor lock-in** (open source, can migrate away)

### Fallback Chain

All runtime-tunable configuration follows a three-level fallback:

```
Flagsmith -> Environment Variable -> Hardcoded Default
```

This ensures the application always starts and operates correctly even if:
- Flagsmith is down (falls back to env vars)
- Flagsmith is not configured (falls back to env vars)
- Neither is available (uses hardcoded defaults)

### Implementation

A new module `app/core/remote_config.py` provides two functions:

```python
get_config(key: str, default: str) -> str        # String config values
get_feature_flag(key: str, default: bool) -> bool  # Boolean feature flags
```

The Flagsmith client is lazy-initialized (only when first accessed) and requires `FLAGSMITH_SERVER_KEY` to be set. Without it, the module silently falls back to env vars.

### Configuration Categories

| Category | Where | Examples | Change Requires |
|----------|-------|---------|-----------------|
| **Secrets** | `.env` on server (NOT in git) | `OPENAI_API_KEY`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD` | File edit + restart |
| **Infrastructure** | `.env` on server | `POSTGRES_URL`, `REDIS_URL`, ports | File edit + restart |
| **Runtime-tunable** | **Flagsmith** | LLM models, feature flags, RAG weights, thresholds | **No restart** |
| **Hardcoded defaults** | Python code | Fallback if Flagsmith unavailable | Redeploy |

### High-Priority Runtime-Tunable Configs

| Config Key | Current Source | Purpose |
|-----------|---------------|---------|
| `PRODUCTION_LLM_MODEL` | `config.py` Settings | Active LLM model for chat |
| `DEFAULT_LLM_TEMPERATURE` | `config.py` Settings | LLM temperature |
| `HYBRID_WEIGHT_FTS` | `config.py` module-level | FTS search weight |
| `HYBRID_WEIGHT_VEC` | `config.py` module-level | Vector search weight |
| `HYBRID_WEIGHT_RECENCY` | `config.py` module-level | Recency weight |
| `HYBRID_WEIGHT_QUALITY` | `config.py` module-level | Quality weight |
| `HYBRID_WEIGHT_SOURCE` | `config.py` module-level | Source authority weight |
| `WEB_VERIFICATION_ENABLED` | `config.py` Settings | Web verification toggle |
| `CACHE_ENABLED` | `config.py` Settings | Cache toggle |
| `OCR_ENABLED` | `config.py` module-level | OCR toggle |
| `CONTEXT_TOP_K` | `config.py` module-level | RAG context size |

### Migration Strategy

1. **Phase 1:** Feature flags only (kill switches for existing booleans)
2. **Phase 2:** LLM model selection (highest business value - instant model switching)
3. **Phase 3:** RAG weights and thresholds (gradual, monitor quality impact)
4. Keep env vars as permanent fallback (never remove env var support)

## Consequences

### Positive
- Instant configuration changes without redeployment
- Feature flags enable safe coupled BE/FE releases (per ADR-028)
- Self-hosted maintains EU data residency (per ADR-006)
- Graceful degradation when Flagsmith is unavailable
- Audit trail for configuration changes via Flagsmith UI

### Negative
- Additional service to operate (Flagsmith Docker container, ~300MB RAM)
- Configuration now lives in two places (Flagsmith UI + code defaults)
- Team must learn Flagsmith UI for operational changes
- Small latency overhead on first flag fetch per request (mitigated by Flagsmith SDK caching)

### Neutral
- `.env` files shrink to secrets-only but remain necessary
- Existing `os.getenv()` calls remain as fallback (no breaking changes)
- Module-level config values become function calls via `remote_config.get_config()`

## References
- ADR-006: Hetzner Cloud Hosting (EU data residency)
- ADR-028: Deployment Pipeline Architecture
- `app/core/remote_config.py`: Implementation
- Flagsmith docs: https://docs.flagsmith.com/
