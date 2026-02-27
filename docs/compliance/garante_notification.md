# DEV-399: Italian AI Law — Garante Notification

## Status
DRAFT — Requires completion of DEV-398 (LLM provider DPAs)

## Overview
Under the Italian AI Act implementation (D.Lgs. implementing EU AI Act), PratikoAI must notify the Italian Data Protection Authority (Garante per la Protezione dei Dati Personali) before public launch.

## Notification Requirements

### 1. System Description
- **Product:** PratikoAI — AI-powered assistant for Italian professionals (commercialisti)
- **AI Purpose:** Legal/tax information retrieval, document analysis, client communication
- **AI Category:** Low-risk AI system (advisory, non-autonomous decision-making)
- **Deployment:** EU-hosted (Hetzner, Germany) per ADR-006

### 2. Data Processing
- **Personal data processed:** Client PII (name, tax ID, email, phone)
- **Legal basis:** Legitimate interest (Art. 6(1)(f) GDPR) + DPA consent
- **Data subjects:** Clients of professional studios
- **Retention:** Per studio DPA agreement, minimum 10 years for fiscal records

### 3. AI Model Inventory (per ADR-025)
- **BASIC tier:** Claude Haiku, GPT-4o-mini (general queries)
- **PREMIUM tier:** Claude Sonnet/Opus, GPT-4o (complex analysis)
- **LOCAL tier:** Mistral (privacy-sensitive operations)
- All models accessed via API (no local training on client data)

### 4. DPIA Reference
- Full DPIA completed as DEV-396
- Risk assessment: LOW (advisory system, human oversight required)
- Mitigations: Encryption at rest, multi-tenant isolation, audit trails

### 5. Timeline
- **Notification submission:** [TBD — requires DEV-398 completion]
- **30-day waiting period:** Required before public launch
- **Public launch:** After waiting period + Garante acknowledgment

## Required Attachments
- [ ] DPIA document (DEV-396)
- [ ] Sub-processor list with DPAs (DEV-397, DEV-398)
- [ ] Privacy policy (DEV-400)
- [ ] Technical security measures documentation

## Contact
- **DPO:** [To be designated]
- **Legal representative:** [To be designated]
