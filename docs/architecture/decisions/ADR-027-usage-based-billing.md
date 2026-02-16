# ADR-027: Usage-Based Billing System

## Status
Accepted

## Date
2026-02-15

## Context

PratikoAI runs a 134-step LangGraph RAG pipeline where every query incurs real LLM costs (median ~EUR 0.10 with `mistral-large-latest`). Without usage-based billing:

- **No cost ceiling** — a single user could consume unlimited LLM resources
- **No burst protection** — automated or accidental loops could spike costs in minutes
- **Unfair pricing** — light and heavy users pay the same flat subscription fee
- **No margin control** — LLM provider price changes directly erode margins

The existing Stripe subscription system (see `docs/ITALIAN_SUBSCRIPTIONS.md`) handles payment processing and IVA compliance, but does not enforce usage limits or manage LLM cost exposure.

## Decision

Adopt a **3-tier usage-based billing system** with rolling cost windows, pay-as-you-go credits, and YAML-driven configuration.

### Tier Structure

| Plan | Monthly Price | LLM Cost Cap | 5h Window | 7d Window | Credit Markup |
|------|--------------|-------------|-----------|-----------|---------------|
| **Base** | EUR 25 | EUR 10 | EUR 2.50 | EUR 7.50 | 50% (1.5x) |
| **Pro** | EUR 75 | EUR 30 | EUR 5.00 | EUR 22.50 | 30% (1.3x) |
| **Premium** | EUR 150 | EUR 60 | EUR 10.00 | EUR 45.00 | 20% (1.2x) |

All plans maintain a **60% margin** (price vs. `monthly_cost_limit_eur`).

### Key Design Choices

#### 1. Rolling Windows (Not Calendar-Based)

Two rolling windows protect against cost bursts:

- **5-hour window** — prevents short bursts (e.g., automated loops, excessive retries)
- **7-day window** — prevents sustained high usage from exhausting the monthly budget early

Rolling windows are more user-friendly than calendar resets: a user blocked at 11 PM can resume as soon as their oldest queries age out, rather than waiting until midnight.

#### 2. YAML → DB Sync Pattern

Plan definitions live in `config/billing_plans.yaml` and sync to the `billing_plans` database table on every app startup via `billing_plan_service.sync_plans_from_config()`. This follows the same pattern as `config/llm_models.yaml`:

- **YAML is source of truth** — change prices by editing the file
- **DB is runtime store** — services read from DB for performance
- **Upsert on startup** — new plans inserted, existing plans updated by slug
- **Hardcoded fallback** — if YAML is missing/corrupt, defaults are applied

#### 3. Credit System with Plan-Specific Markup

When a user exceeds a rolling window limit, they can continue using pay-as-you-go credits (if opted in). Credits are consumed at the raw LLM cost multiplied by a plan-specific markup factor:

- Base plan: 1.5x markup (50% premium for low-tier credits)
- Pro plan: 1.3x markup
- Premium plan: 1.2x markup

This incentivizes upgrading to a higher plan over relying on credits.

#### 4. Dual-Layer Enforcement (Redis + PostgreSQL)

- **Redis sorted sets** — fast-path window checks during request processing
- **PostgreSQL** — durable storage, fallback when Redis is unavailable
- **Middleware** — `CostLimiterMiddleware` enforces limits on chat endpoints before the request reaches the LangGraph pipeline

#### 5. Admin Bypass

Users with `admin` or `super_user` roles can bypass limits via the `X-Cost-Limit-Bypass: true` header for testing and support scenarios.

### Component Architecture

```
config/billing_plans.yaml          ← Source of truth
        │
        ▼
billing_plan_service               ← YAML sync + plan CRUD
        │
        ▼
┌───────────────────┐
│   billing_plans   │              ← DB table (SQLModel)
│   (PostgreSQL)    │
└───────────────────┘
        │
        ├──► rolling_window_service     ← 5h/7d cost window checks
        │       ├── Redis sorted sets   ← Fast path
        │       └── usage_windows table ← Durable store
        │
        ├──► usage_credit_service       ← Credit recharge/consume
        │       ├── user_credits table
        │       └── credit_transactions table
        │
        └──► CostLimiterMiddleware      ← HTTP-level enforcement
                └── Returns 429 with Italian error messages + options
```

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/billing/usage` | Required | Current usage across windows |
| `GET` | `/api/v1/billing/plans` | Public | Available plans list |
| `POST` | `/api/v1/billing/plans/{slug}/subscribe` | Required | Subscribe to a plan |
| `POST` | `/api/v1/billing/plans/upgrade` | Required | Change plan |
| `GET` | `/api/v1/billing/credits/balance` | Required | Credit balance |
| `POST` | `/api/v1/billing/credits/recharge` | Required | Recharge credits (5/10/25/50/100 EUR) |
| `POST` | `/api/v1/billing/credits/enable-extra-usage` | Required | Toggle credit consumption |
| `GET` | `/api/v1/billing/credits/transactions` | Required | Transaction history |

## Consequences

### Positive

- **Predictable costs** — rolling windows cap exposure per user with known margins
- **Easy config changes** — edit YAML, deploy, auto-sync (no migration needed for price changes)
- **Graceful degradation** — PostgreSQL fallback when Redis is unavailable
- **User transparency** — 429 responses include Italian messages, reset times, and options (wait/upgrade/recharge)
- **Audit trail** — all credit transactions logged with amounts, balances, and Stripe references

### Negative

- **Redis dependency** — real-time window checks are degraded without Redis (falls back to PostgreSQL queries)
- **Sync timing** — plan changes require redeployment to take effect (no runtime admin UI)
- **No proration** — plan upgrades/downgrades take effect immediately without billing proration (to be addressed separately with Stripe integration)

## Related

- **ADR-025**: LLM Model Inventory & Tiering (models whose costs are being tracked)
- **ADR-026**: Exchange Rates (EUR cost calculations)
- **JIRA**: DEV-257
- **Feature Doc**: `docs/USAGE_BASED_BILLING.md`
