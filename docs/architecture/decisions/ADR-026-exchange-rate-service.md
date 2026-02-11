# ADR-026: Exchange Rate Service for Multi-Currency Cost Display

## Status

Accepted

## Date

2026-02-11

## Context

The model comparison feature (DEV-256) displays LLM call costs in EUR. Users requested to also see costs in USD to facilitate comparison with international pricing.

### Requirements

1. Display costs in both EUR and USD on the model comparison page
2. Use a reliable, free exchange rate source
3. Exchange rate should be updated daily (not hardcoded)
4. Minimize external API calls

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Google Finance API** | Well-known | No official REST API, deprecated |
| **Yahoo Finance API** | Well-known | Old CSV endpoint blocked |
| **Frankfurter API** | Free, no auth, ECB data, 10+ years uptime | Third-party service |
| **ECB Direct (SDMX)** | Official source | Complex XML format, requires parsing |
| **Hardcoded rate** | Simple | Becomes stale, maintenance burden |

## Decision

Use the **Frankfurter API** (https://frankfurter.dev/) with a 24-hour server-side cache.

### Rationale

1. **Free and reliable**: No API key, no rate limits, running 10+ years
2. **Official data**: Uses European Central Bank reference rates
3. **Simple REST API**: JSON responses, easy to integrate
4. **Daily updates**: ECB updates rates daily ~16:00 CET, matching our cache duration

### Implementation

```python
# app/services/exchange_rate_service.py
FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"

async def get_eur_to_usd_rate() -> float:
    """Fetch EUR/USD rate, cached for 24 hours."""
    # Returns cached rate or fetches from API
    # Falls back to last known rate on API failure
```

### API Response Format

```
GET https://api.frankfurter.dev/v1/latest?from=EUR&to=USD

{
  "amount": 1,
  "base": "EUR",
  "date": "2026-02-11",
  "rates": {
    "USD": 1.0875
  }
}
```

## Consequences

### Positive

- Users see costs in both EUR and USD
- Exchange rate stays current (daily updates)
- No API key management required
- Graceful degradation on API failure (uses cached rate)

### Negative

- External dependency on Frankfurter API
- 24-hour cache means rate may be slightly stale

### Mitigations

- Cache fallback ensures service continuity if API is down
- For critical applications, Frankfurter recommends self-hosting (MIT license)

## References

- [Frankfurter API Documentation](https://frankfurter.dev/)
- [ECB Exchange Rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/)
- DEV-256: Multi-Model LLM Comparison Feature
