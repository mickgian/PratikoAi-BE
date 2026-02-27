# DEV-400: Public Sub-Processor List and Privacy Policy

## Status
DRAFT — Requires completion of DEV-397 (Hetzner DPA), DEV-398 (LLM DPAs)

## Sub-Processor List

### Infrastructure Sub-Processors

| Sub-Processor | Service | Data Processed | Location | DPA Status |
|---------------|---------|----------------|----------|------------|
| Hetzner Online GmbH | Server hosting (CX33/CX43) | All application data | Germany (EU) | Pending (DEV-397) |
| Hetzner Online GmbH | PostgreSQL database | All persistent data | Germany (EU) | Pending (DEV-397) |
| Hetzner Online GmbH | Redis cache | Session/cache data | Germany (EU) | Pending (DEV-397) |

### AI/LLM Sub-Processors

| Sub-Processor | Service | Data Processed | Location | DPA Status |
|---------------|---------|----------------|----------|------------|
| Anthropic | Claude API (BASIC/PREMIUM) | Query text, context | USA (SCCs) | Pending (DEV-398) |
| OpenAI | GPT-4o API (BASIC/PREMIUM) | Query text, context | USA (SCCs) | Pending (DEV-398) |
| OpenAI | Embedding API | Document text | USA (SCCs) | Pending (DEV-398) |
| Mistral AI | Mistral API (LOCAL tier) | Privacy-sensitive queries | France (EU) | Pending (DEV-398) |

### Payment Sub-Processors

| Sub-Processor | Service | Data Processed | Location | DPA Status |
|---------------|---------|----------------|----------|------------|
| Stripe | Payment processing | Payment data | Ireland (EU) | Active |

### Monitoring Sub-Processors

| Sub-Processor | Service | Data Processed | Location | DPA Status |
|---------------|---------|----------------|----------|------------|
| Langfuse | LLM observability | Anonymized traces | Germany (EU) | Active |

## Privacy Policy Summary

### Data Controller
PratikoAI S.r.l. (to be incorporated)

### Categories of Personal Data
1. **User account data:** Email, name, authentication tokens
2. **Client data (processed on behalf of studios):** Name, tax ID, VAT, email, phone, address
3. **Usage data:** Chat queries, interaction logs (anonymized for analytics)

### Legal Basis for Processing
- **User accounts:** Contract performance (Art. 6(1)(b))
- **Client data:** Legitimate interest of studio (Art. 6(1)(f)) + DPA
- **Analytics:** Legitimate interest (Art. 6(1)(f)) with anonymization

### Data Subject Rights
- Access (Art. 15)
- Rectification (Art. 16)
- Erasure (Art. 17) — implemented via soft-delete + GDPR cleanup
- Data portability (Art. 20) — implemented via Excel export (DEV-314)
- Objection (Art. 21)

### Security Measures
- Column-level PII encryption (AES-256)
- Multi-tenant row-level isolation
- DPA acceptance enforcement before client data processing
- Breach notification within 72 hours
- EU-hosted infrastructure (no US data storage)

### Data Retention
- Client data: Per studio DPA, minimum 10 years for fiscal records
- Usage logs: 90 days (then anonymized)
- Chat history: Configurable per studio (default 365 days)

### International Transfers
- LLM API calls to USA providers use Standard Contractual Clauses (SCCs)
- All persistent data storage remains in EU (Germany)
- Privacy-sensitive queries routed to EU-hosted Mistral (LOCAL tier)
