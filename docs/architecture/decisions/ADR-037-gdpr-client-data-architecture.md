# ADR-037: GDPR Client Data Architecture

## Status
ACCEPTED

## Date
2026-02-27

## Context
PratikoAI processes personal data (PII) of clients belonging to professional studios (commercialisti). Under GDPR (EU 2016/679), we must ensure:

1. **Data minimization** — Only collect data necessary for the service
2. **Purpose limitation** — Clear legal basis for each processing activity
3. **Storage limitation** — Defined retention periods
4. **Integrity and confidentiality** — Encryption and access controls
5. **Accountability** — Processing register and audit trails

This ADR documents the architectural decisions governing how client data flows through the system.

## Decision

### 1. Multi-Tenant Data Isolation (ADR-017)
- All client data is scoped to a `studio_id` (UUID FK)
- Every database query enforces tenant isolation via `WHERE studio_id = :sid`
- No cross-tenant data access is possible at the application layer

### 2. PII Encryption at Rest
- Sensitive fields use column-level encryption via `EncryptedType` decorators:
  - `EncryptedTaxID` — Codice Fiscale, Partita IVA
  - `EncryptedPersonalData` — Names
  - `EncryptedEmail` — Email addresses
  - `EncryptedPhone` — Phone numbers
- Encryption key is stored in environment variables, rotated per ADR schedule
- Non-sensitive address data (comune, provincia, CAP) stored in plaintext per DPIA assessment

### 3. Soft Delete for GDPR Right-to-Erasure
- Client records use `deleted_at` timestamp (not physical deletion)
- Soft-deleted clients are excluded from all queries
- A scheduled GDPR cleanup job physically purges records after the retention period
- Export-before-delete supports GDPR data portability (DEV-314)

### 4. Data Processing Agreement (DPA) Enforcement
- Studios must accept the current DPA before adding clients (DEV-373)
- DPA versions are tracked with full acceptance audit trail (IP, user agent, timestamp)
- DPA acceptance is checked at the API layer before client creation

### 5. Breach Notification Lifecycle (DEV-375)
- Detection → Investigation → Containment → Authority Notification → Resolution
- 72-hour GDPR deadline tracked automatically
- Overdue breach notifications flagged by scheduled check

### 6. Processing Register (DEV-376)
- GDPR Article 30 compliant register of processing activities
- Tracks: activity name, purpose, legal basis, data categories, subjects, retention, recipients
- Studio-scoped with full CRUD

### 7. Communication Workflow with Audit Trail
- All client communications go through: DRAFT → REVIEW → APPROVED → SENT
- Creator cannot approve their own communications (separation of duties)
- Full audit trail: created_by, approved_by, approved_at, sent_at

## Consequences

### Positive
- GDPR compliance built into the architecture from day one
- Clear data flow documentation for DPO and auditors
- Encryption at rest protects against database breaches
- Multi-tenant isolation prevents data leakage between studios

### Negative
- Column-level encryption adds slight query overhead
- Soft delete requires careful query construction (always filter `deleted_at IS NULL`)
- DPA enforcement adds a step to the client creation flow

### Risks
- Encryption key rotation requires careful coordination
- Soft-deleted data must still be physically purged after retention period
- Cross-border data transfers need additional assessment (currently EU-only per ADR-006)
