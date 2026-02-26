# Data Protection Impact Assessment (DPIA) — PratikoAI 2.0

**Document ID:** DPIA-PRATIKO-2026-001
**Version:** 1.0
**Date:** 2026-02-26
**Status:** DRAFT — Pending Legal Counsel Review
**Classification:** CONFIDENTIAL

---

## 1. Introduction and Legal Basis

### 1.1 Purpose

This Data Protection Impact Assessment (DPIA) is prepared pursuant to **Article 35 of the EU General Data Protection Regulation (GDPR)** and Italy's **Garante per la Protezione dei Dati Personali — Provvedimento dell'11 ottobre 2018** (Elenco delle tipologie di trattamenti soggetti al requisito di una valutazione d'impatto).

PratikoAI 2.0 is a SaaS platform for Italian *commercialisti* (chartered accountants) that processes client financial, fiscal, and personal data through AI-assisted workflows.

### 1.2 Why a DPIA Is Mandatory

PratikoAI triggers at least **three categories** from the Garante's mandatory DPIA list:

| # | Category | PratikoAI Trigger |
|---|----------|-------------------|
| 1 | Large-scale processing of financial data | Multi-tenant database of client fiscal profiles (Codice Fiscale, P.IVA, income data) |
| 2 | AI/scoring/profiling via automated decision-making | LLM-based normative matching engine, proactive suggestions, document analysis |
| 3 | Cross-referencing of personal + fiscal + employment data | Client profiles combine personal data, ATECO codes, employee counts, tax regimes |

**Penalty for non-compliance:** Up to EUR 10,000,000 or 2% of worldwide annual turnover (Art. 83(4) GDPR).

### 1.3 Data Controller

**Controller:** The professional studio (*commercialista* office) using PratikoAI.
**Processor:** PratikoAI S.r.l. (the SaaS provider), operating under Data Processing Agreements (DPAs).

---

## 2. Description of Processing Activities

### 2.1 Personal Data Categories Processed

| Data Category | Fields | Storage | Encryption | Retention |
|---------------|--------|---------|------------|-----------|
| **Tax Identifiers** | Codice Fiscale, Partita IVA | PostgreSQL (Hetzner EU) | AES-256-GCM (EncryptedTaxID) | Until client deletion + 10yr legal retention |
| **Contact Information** | Email, phone, address | PostgreSQL (Hetzner EU) | AES-256-GCM (EncryptedEmail, EncryptedPhone) | Until client deletion |
| **Personal Data** | Name, date of birth | PostgreSQL (Hetzner EU) | AES-256-GCM (EncryptedPersonalData) | Until client deletion |
| **Financial Data** | Income, property values, tax regime | PostgreSQL (Hetzner EU) | AES-256-GCM (EncryptedFinancialData) | Until client deletion + 10yr |
| **Employment Data** | ATECO codes, employee count, CCNL | PostgreSQL (Hetzner EU) | Application-level | Until client deletion |
| **Document Content** | Uploaded fiscal documents (PDF, images) | PostgreSQL + S3 (Hetzner EU) | TLS in transit, encrypted at rest | Configurable per studio |
| **Chat History** | User queries to AI assistant | PostgreSQL (Hetzner EU) | Application-level | Rolling 90 days default |
| **Usage Analytics** | Query patterns, feature usage | PostgreSQL (Hetzner EU) | Pseudonymised | 12 months |

### 2.2 Processing Purposes

| Purpose | Legal Basis (Art. 6) | Description |
|---------|---------------------|-------------|
| Client management | 6(1)(b) Contract | CRUD operations on client records for the studio |
| Normative matching | 6(1)(b) Contract | Automated matching of regulatory updates to client profiles |
| Proactive suggestions | 6(1)(f) Legitimate interest | Notifying studios of relevant regulatory changes (ADR-035: notification-only) |
| Tax calculations | 6(1)(b) Contract | IMU, IRPEF addizionali, IRAP calculations with regional variations |
| AI-assisted responses | 6(1)(b) Contract | RAG pipeline using KB context to answer fiscal queries |
| Document analysis | 6(1)(b) Contract | OCR and AI classification of uploaded fiscal documents |
| Communication generation | 6(1)(b) Contract | Draft communications to clients about regulatory updates |

### 2.3 Data Flow Architecture

```
Studio User → [HTTPS/TLS 1.3] → FastAPI Backend (Hetzner CX43, EU)
                                      │
                                      ├── PostgreSQL (Hetzner EU, encrypted at rest)
                                      │     └── PII: AES-256-GCM column-level encryption
                                      │
                                      ├── Redis (Hetzner EU, password-protected, ADR-033)
                                      │     └── Session cache, rate limiting (no PII)
                                      │
                                      └── LLM Provider API (external)
                                            └── Anonymised context only (PII stripped)
```

---

## 3. Risk Assessment

### 3.1 Risk Matrix

| Risk ID | Risk Description | Likelihood | Impact | Inherent Risk | Mitigation | Residual Risk |
|---------|------------------|------------|--------|---------------|------------|---------------|
| R-01 | Unauthorised access to client PII | Medium | High | HIGH | AES-256-GCM encryption, RBAC, multi-tenant row isolation (ADR-017) | LOW |
| R-02 | Cross-tenant data leakage | Low | Critical | HIGH | studio_id FK on all queries, application-level tenant isolation | LOW |
| R-03 | LLM hallucination of legal citations | High | Medium | HIGH | HallucinationGuard service (DEV-245/389), soft+strict modes | MEDIUM |
| R-04 | PII sent to external LLM providers | Medium | High | HIGH | PII anonymiser in RAG pipeline strips personal data before LLM calls | LOW |
| R-05 | Data breach at infrastructure provider | Low | Critical | MEDIUM | Hetzner EU hosting (GDPR-compliant), encryption at rest, DPA in place | LOW |
| R-06 | Insufficient data deletion (GDPR Art. 17) | Medium | High | HIGH | Soft delete + GDPR deletion service with verification (existing) | LOW |
| R-07 | Encryption key compromise | Low | Critical | MEDIUM | Key rotation service, key versioning, monitoring (existing) | LOW |
| R-08 | Excessive data retention | Medium | Medium | MEDIUM | Configurable retention policies, automated cleanup jobs | LOW |
| R-09 | Inaccurate tax calculations | Medium | High | HIGH | Unit tests, regional rate validation, rate bounds checking | MEDIUM |
| R-10 | Cross-border data transfer to LLM providers | Medium | High | HIGH | DPA with providers, SCCs, anonymisation before transfer (DEV-398) | MEDIUM |

### 3.2 Risk Rating Scale

- **Likelihood:** Low (unlikely) / Medium (possible) / High (probable)
- **Impact:** Low (minor inconvenience) / Medium (significant harm) / High (severe harm) / Critical (irreversible harm)
- **Risk:** LOW / MEDIUM / HIGH / CRITICAL

---

## 4. Technical and Organisational Measures

### 4.1 Encryption

| Layer | Measure | Standard |
|-------|---------|----------|
| In transit | TLS 1.3 (Caddy reverse proxy) | AEAD ciphers only |
| At rest — database | AES-256-GCM column-level encryption | `app/core/encryption/encrypted_types.py` |
| At rest — storage | Hetzner volume encryption | Provider-managed |
| Key management | Versioned keys with rotation support | `app/services/encryption_key_rotation_service.py` |

### 4.2 Access Control

| Control | Implementation |
|---------|----------------|
| Authentication | JWT tokens with refresh rotation |
| Authorisation | Role-based (REGULAR_USER, EXPERT, ADMIN, SUPER_USER) |
| Multi-tenancy | Row-level isolation via `studio_id` FK (ADR-017) |
| API rate limiting | Redis-based per-endpoint limits (DEV-395) |
| Self-approval prevention | Communication model enforces creator ≠ approver |

### 4.3 Data Minimisation

| Measure | Description |
|---------|-------------|
| PII anonymisation | PII stripped from context before LLM API calls |
| Pseudonymisation | Usage analytics use account codes, not names |
| Purpose limitation | Each data field mapped to specific processing purpose |
| Retention limits | Configurable per studio, automated deletion |

### 4.4 LLM Sub-Processor Assessment

| Provider | Data Sent | DPA Status | Transfer Safeguard |
|----------|-----------|------------|-------------------|
| Anthropic (Claude) | Anonymised KB context + user queries (no PII) | Required (DEV-398) | SCCs + anonymisation |
| OpenAI (GPT-4) | Anonymised KB context + user queries (no PII) | Required (DEV-398) | SCCs + anonymisation |

**Critical control:** The PII anonymiser in the RAG pipeline ensures no Codice Fiscale, P.IVA, names, or contact information reaches external LLM providers. Only anonymised fiscal context and user queries are transmitted.

### 4.5 Hetzner Infrastructure Assessment

| Aspect | Assessment |
|--------|------------|
| Location | EU (Germany/Finland), GDPR Article 28 compliant |
| Certification | ISO 27001 certified data centres |
| DPA | Standard DPA available and executed |
| Encryption at rest | Volume encryption provided |
| Network isolation | Private networking between services |

---

## 5. Data Subject Rights

| Right | Implementation |
|-------|----------------|
| **Access (Art. 15)** | Data export service (`app/services/data_export_service.py`) |
| **Rectification (Art. 16)** | Client CRUD API allows studio users to update all fields |
| **Erasure (Art. 17)** | GDPR deletion service with verification (`app/services/gdpr_deletion_service.py`) |
| **Restriction (Art. 18)** | Client status can be set to SOSPESO (suspended) |
| **Portability (Art. 20)** | JSON/CSV export via data export service |
| **Object (Art. 21)** | Proactive suggestions can be disabled per client |

---

## 6. Multi-Tenant Isolation Assessment

PratikoAI uses a single-database, shared-schema multi-tenancy model with row-level isolation (ADR-017):

- Every client record includes a `studio_id` foreign key
- All database queries filter by `studio_id` at the application layer
- No cross-tenant JOINs are possible without explicit `studio_id` match
- Studio administrators can only view/modify their own clients
- Background matching jobs are scoped to individual studios

**Residual risk:** Application-level isolation (not database-level RLS). Mitigated by comprehensive test coverage and code review.

---

## 7. Recommendations and Action Items

| # | Action | Priority | Owner | Status |
|---|--------|----------|-------|--------|
| 1 | Execute DPA with Hetzner for data processing | CRITICAL | @Silvano | DEV-397 |
| 2 | Execute DPAs with LLM providers (Anthropic, OpenAI) | CRITICAL | @Severino | DEV-398 |
| 3 | Implement consent management for proactive suggestions | HIGH | @Ezio | DEV-399 |
| 4 | Conduct annual DPIA review | MEDIUM | @Severino | Scheduled |
| 5 | Penetration testing before production launch | HIGH | External | Planned |
| 6 | Legal counsel review of this DPIA document | CRITICAL | External | Pending |
| 7 | Train studio users on data protection responsibilities | MEDIUM | @Mario | Planned |

---

## 8. Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Data Protection Officer | _________________ | ____/____/2026 | _________ |
| Technical Lead | _________________ | ____/____/2026 | _________ |
| Legal Counsel | _________________ | ____/____/2026 | _________ |

---

**Next Review Date:** 2027-02-26 (annual review) or upon significant processing changes.
