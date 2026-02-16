# Usage-Based Billing System

Usage-based billing for PratikoAI with 3-tier plans, rolling cost windows, and pay-as-you-go credits. Implemented in DEV-257.

## Overview

The billing system caps LLM costs per user using rolling time windows (5-hour and 7-day), enforced at the middleware level before queries reach the LangGraph pipeline. When limits are reached, users can wait for the window to reset, upgrade their plan, or use prepaid credits.

### Key Features

- **3-tier plans** (Base/Pro/Premium) with 60% margin
- **Rolling cost windows** (5h burst + 7d sustained) instead of calendar resets
- **Pay-as-you-go credits** with plan-specific markup
- **YAML-driven config** — change prices without migrations
- **Redis + PostgreSQL** dual-layer enforcement
- **Italian user-facing messages** on all API responses

## Architecture

```
config/billing_plans.yaml             ← Source of truth for plan definitions
        │
        ▼ (sync on startup)
billing_plan_service.py               ← Plan CRUD + YAML sync
        │
        ▼
┌────────────────────┐
│ billing_plans (DB) │
└────────────────────┘
        │
        ├──► rolling_window_service.py     ← 5h/7d window checks
        │       ├── Redis sorted sets      ← Fast path
        │       └── usage_windows (DB)     ← Durable fallback
        │
        ├──► usage_credit_service.py       ← Recharge + consume credits
        │       ├── user_credits (DB)
        │       └── credit_transactions (DB)
        │
        └──► cost_limiter.py (middleware)  ← HTTP 429 enforcement on chat endpoints
```

## Plans & Limits

Current plan definitions (from `config/billing_plans.yaml`):

| | Base | Pro | Premium |
|---|---:|---:|---:|
| **Monthly price** | EUR 25 | EUR 75 | EUR 150 |
| **Monthly LLM cost cap** | EUR 10 | EUR 30 | EUR 60 |
| **5h window limit** | EUR 2.50 | EUR 5.00 | EUR 10.00 |
| **7d window limit** | EUR 7.50 | EUR 22.50 | EUR 45.00 |
| **Credit markup** | 50% (1.5x) | 30% (1.3x) | 20% (1.2x) |
| **~Queries/5h** | ~25 | ~50 | ~100 |
| **~Queries/7d** | ~75 | ~225 | ~450 |

Query estimates assume median cost of EUR 0.10 per query (`mistral-large-latest` with RAG).

## How to Change Prices

Plan definitions are stored in `config/billing_plans.yaml` and synced to the database on every app startup. To change prices:

### Step-by-step

1. **Edit** `config/billing_plans.yaml` — change the values you need
2. **Commit & deploy** — the normal deployment process
3. **Auto-sync** — on startup, `billing_plan_service.sync_plans_from_config()` upserts all plans by slug

That's it. No database migration is needed for price changes.

### Example: Increase Pro plan price

```yaml
# config/billing_plans.yaml
plans:
  pro:
    name: "Pro"
    price_eur_monthly: 99.0        # was 75.0
    monthly_cost_limit_eur: 40.0   # was 30.0 (maintain 60% margin)
    window_5h_cost_limit_eur: 7.00 # was 5.00
    window_7d_cost_limit_eur: 30.0 # was 22.50
    credit_markup_factor: 1.30
    is_active: true
```

### Important notes

- **Maintain 60% margin**: `price_eur_monthly` should be ~2.5x `monthly_cost_limit_eur`
- **Window proportions**: `window_7d` is typically 3x `window_5h`; `monthly` is ~4x `window_7d`
- **Existing users**: updated limits apply immediately on next app restart
- **Stripe sync**: if `stripe_price_id` is set on the plan, you must also update the price in Stripe separately
- **Hardcoded fallback**: if YAML is missing/corrupt, the service falls back to hardcoded defaults in `billing_plan_service.py`

### Adding a new plan

Add a new entry under `plans:` with a unique slug key:

```yaml
plans:
  enterprise:
    name: "Enterprise"
    price_eur_monthly: 500.0
    monthly_cost_limit_eur: 200.0
    window_5h_cost_limit_eur: 30.00
    window_7d_cost_limit_eur: 150.00
    credit_markup_factor: 1.10
    is_active: true
```

The sync will insert a new row in `billing_plans` with `slug = "enterprise"`.

## Rolling Windows

### Why Rolling Windows?

Calendar-based resets (midnight UTC) create unfair edges: a user who hits their limit at 11 PM must wait until midnight, while one who hits it at 1 AM gets nearly 24 hours. Rolling windows are fairer — usage ages out gradually.

### How They Work

Each LLM query records its cost and timestamp in both windows:

- **5-hour window**: sum of costs in the last 5 hours. Protects against short bursts (automated loops, excessive retries).
- **7-day window**: sum of costs in the last 7 days. Prevents sustained heavy usage from exhausting the monthly budget early.

When either window exceeds its plan limit, the middleware returns HTTP 429 with:

```json
{
  "error_code": "USAGE_LIMIT_EXCEEDED",
  "message_it": "Hai raggiunto il limite di utilizzo per questa finestra",
  "limit_info": {
    "window_type": "5h",
    "cost_consumed_eur": 2.51,
    "cost_limit_eur": 2.50,
    "reset_in_minutes": 42
  },
  "options": {
    "wait": { "reset_in_minutes": 42 },
    "upgrade": { "url": "/account/piano" },
    "recharge": { "url": "/account/crediti" },
    "use_credits": { "available": true, "balance_eur": 5.00 }
  }
}
```

### Storage

- **Redis sorted sets** (`usage_window:{user_id}:{window_type}`) for real-time checks
- **PostgreSQL `usage_windows` table** as durable fallback when Redis is unavailable
- Entries auto-expire: Redis TTL = window duration + 1h buffer

## Credits

Credits provide pay-as-you-go usage when rolling window limits are exceeded.

### Recharging

Users can recharge credits in fixed amounts: **EUR 5, 10, 25, 50, or 100**. Recharge amounts are configured via `settings.BILLING_CREDIT_RECHARGE_AMOUNTS`.

### Consuming

When a user exceeds a window limit and has `extra_usage_enabled = True`:

1. The middleware allows the request through
2. After the LLM call, the raw cost is multiplied by the plan's `credit_markup_factor`
3. The marked-up amount is deducted from the credit balance
4. A `CreditTransaction` record is created for auditing

Example: Base plan user, EUR 0.10 query cost, 1.5x markup → EUR 0.15 charged from credits.

### Enabling Extra Usage

Users must explicitly opt in to credit consumption via:
```
POST /api/v1/billing/credits/enable-extra-usage
{ "enabled": true }
```

This is intentionally opt-in to prevent surprise charges.

## API Endpoints

All endpoints are under `/api/v1/billing/`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/usage` | Yes | Current usage status (both windows + credits) |
| `GET` | `/plans` | No | List available plans with limits |
| `POST` | `/plans/{slug}/subscribe` | Yes | Subscribe to a plan |
| `POST` | `/plans/upgrade` | Yes | Change to a different plan |
| `GET` | `/credits/balance` | Yes | Current credit balance |
| `POST` | `/credits/recharge` | Yes | Add credits (fixed amounts) |
| `POST` | `/credits/enable-extra-usage` | Yes | Toggle credit consumption |
| `GET` | `/credits/transactions` | Yes | Credit transaction history |

## Key Files

| File | Purpose |
|------|---------|
| `config/billing_plans.yaml` | Source of truth for plan limits and pricing |
| `app/models/billing.py` | SQLModel definitions: `BillingPlan`, `UsageWindow`, `UserCredit`, `CreditTransaction` |
| `app/schemas/billing.py` | Pydantic request/response schemas |
| `app/services/billing_plan_service.py` | Plan CRUD + `sync_plans_from_config()` |
| `app/services/rolling_window_service.py` | 5h/7d window checks (Redis + PostgreSQL) |
| `app/services/usage_credit_service.py` | Credit recharge, consume, enable/disable |
| `app/api/v1/billing.py` | REST API endpoints |
| `app/core/middleware/cost_limiter.py` | `CostLimiterMiddleware` — enforces limits on chat endpoints |
| `app/main.py` (`lifespan()`) | Calls `sync_plans_from_config()` on startup |
| `alembic/versions/20260212_add_billing_tables.py` | Migration creating billing tables |

## Configuration Reference

### `config/billing_plans.yaml` Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name for the plan |
| `price_eur_monthly` | float | Monthly subscription price in EUR |
| `monthly_cost_limit_eur` | float | Total LLM cost cap per month |
| `window_5h_cost_limit_eur` | float | Max LLM cost in any rolling 5-hour window |
| `window_7d_cost_limit_eur` | float | Max LLM cost in any rolling 7-day window |
| `credit_markup_factor` | float | Multiplier on raw cost when consuming credits (1.5 = 50% markup) |
| `is_active` | bool | Whether the plan is available for subscription |

### Related Documentation

- **ADR-027**: `docs/architecture/decisions/ADR-027-usage-based-billing.md` — architectural decision record
- **Italian Subscriptions**: `docs/ITALIAN_SUBSCRIPTIONS.md` — Stripe/IVA compliance (separate concern)
- **LLM Tiering**: `docs/architecture/decisions/ADR-025-llm-model-inventory-and-tiering.md` — models whose costs are tracked
