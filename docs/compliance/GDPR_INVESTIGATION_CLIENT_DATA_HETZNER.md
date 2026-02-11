# GDPR & Compliance Investigation: Client Data on Hetzner Servers

**Date:** 2026-02-04
**Status:** COMPLETED
**Author:** @Severino (Security), @Mario (Business Analyst)
**Related ADR:** ADR-025 (GDPR Client Data Architecture)

---

## TL;DR - Can PratikoAI Store Italian Client Data on Hetzner (Germany)?

**YES, it is legally permissible under GDPR.** There is NO Italian law requiring personal/financial data to stay within Italian borders. GDPR Article 1(3) explicitly guarantees free movement of personal data within the EU.

**However, there are 7 critical compliance requirements that MUST be addressed before launch.** The risks are NOT about Hetzner/Germany specifically, but about the overall data processing architecture.

---

## Table of Contents

1. [Hetzner Germany = GDPR Compliant](#1-hetzner-germany--gdpr-compliant-for-eu-data-storage)
2. [DPIA is Mandatory](#2-dpia-data-protection-impact-assessment-is-mandatory)
3. [The Real Risk: LLM Sub-Processors](#3-the-real-risk-llm-sub-processors-openaianthopic-not-hetzner)
4. [Italian AI Law (Law 132/2025)](#4-italian-ai-law-law-1322025---new-requirement)
5. [Professional Secrecy](#5-professional-secrecy-segreto-professionale---no-geographic-restriction)
6. [National Cybersecurity Perimeter](#6-perimetro-di-sicurezza-nazionale-cibernetica---not-applicable)
7. [Hetzner Gaps to Address](#7-hetzner-gaps-to-address)
8. [7 Critical Compliance Actions](#the-7-critical-compliance-actions-before-launch)
9. [Hetzner vs Italian Provider Comparison](#comparison-hetzner-vs-italian-provider-aruba-cloud)
10. [Document Inconsistencies Found](#document-inconsistencies-found)

---

## 1. Hetzner Germany = GDPR Compliant for EU Data Storage

### Legal Basis

- **GDPR Article 1(3)**: "The free movement of personal data within the Union shall be neither restricted nor prohibited for reasons connected with the protection of natural persons with regard to the processing of personal data." This is the foundational principle - EU member states cannot require data localization within their borders.

- **D.Lgs. 196/2003 (Codice Privacy)**: Italy's national privacy code, as amended by D.Lgs. 101/2018 to align with GDPR. It does NOT impose data localization requirements for private sector entities.

### Hetzner Certifications

| Certification | Scope | Relevance |
|---|---|---|
| **ISO/IEC 27001:2022** | Information security management | Industry standard for data center security |
| **BSI C5 Type 2** | Cloud Computing Compliance Criteria Catalogue | German federal standard; audit of operational effectiveness |
| **KRITIS** | Critical infrastructure compliance | Hetzner designated as critical infrastructure operator |

### Key Advantages

- **EU-only processing**: When selecting EU data center locations (Nuremberg/Falkenstein), NO non-EU sub-processors are involved in the hosting chain
- **Not subject to US CLOUD Act**: Unlike AWS (Amazon), Azure (Microsoft), and Google Cloud, Hetzner is a German company with no US parent entity. US law enforcement cannot compel Hetzner to produce data stored in its EU data centers
- **Established provider**: Operating since 1997, 350,000+ customers, dedicated server and cloud infrastructure

---

## 2. DPIA (Data Protection Impact Assessment) is MANDATORY

### Why PratikoAI Triggers DPIA Requirements

PratikoAI triggers at least 3 categories of the Garante's DPIA blacklist (Provvedimento dell'11 ottobre 2018 - "Elenco delle tipologie di trattamenti soggetti al requisito di una valutazione d'impatto"):

| Category | Trigger | PratikoAI Processing |
|---|---|---|
| **Category 3** | Large-scale processing of financial data | Codice fiscale, debiti, cartelle esattoriali, importi per multiple studi professionali |
| **Category 1** | AI/scoring/predictive processing | LLM-based analysis via OpenAI/Anthropic for normative matching |
| **Category 5** | Cross-referencing datasets | Fiscal data + personal data + employment data combined for client analysis |

### Legal Reference

- **GDPR Article 35(1)**: "Where a type of processing in particular using new technologies, and taking into account the nature, scope, context and purposes of the processing, is likely to result in a high risk to the rights and freedoms of natural persons, the controller shall, prior to the processing, carry out an assessment of the impact of the envisaged processing operations on the protection of personal data."
- **GDPR Article 35(3)(b)**: Processing on a large scale of special categories of data
- **Garante Provvedimento 11/10/2018**: Italian supervisory authority's mandatory DPIA list

### Penalty for Non-Compliance

Up to **EUR 10,000,000** or **2% of worldwide annual turnover** (whichever is higher) per GDPR Article 83(4)(a).

### PratikoAI DPIA Scope

The DPIA must cover:
- All personal data categories processed (codice fiscale, partita IVA, financial amounts, contact information)
- Processing purposes (normative matching, client analysis, communication generation)
- Data flows including LLM sub-processors
- Risk assessment and mitigations
- Encryption measures (field-level AES-256-GCM + full-disk encryption)
- PII anonymization before LLM calls
- Multi-tenant isolation (studio_id-based row-level security)

---

## 3. The REAL Risk: LLM Sub-Processors (OpenAI/Anthropic), Not Hetzner

### Current Architecture

PratikoAI uses a PII anonymizer (`app/core/privacy/anonymizer.py`) that strips identifiable data before LLM API calls. This is a strong mitigation. However, the data transfer to US-based providers requires proper legal safeguards.

### Sub-Processor Risk Assessment

| Sub-Processor | Data Location | Risk Level | Key Issue |
|---|---|---|---|
| **Hetzner** | Germany (EU) | LOW | Fully GDPR-compliant, EU-only, no US CLOUD Act exposure |
| **OpenAI** | USA | HIGH | Garante fined OpenAI EUR 15M (December 2024) for GDPR violations; not EU-US DPF certified |
| **Anthropic** | USA | HIGH | US processing by default; no EU data residency option as of early 2026 |

### Mitigations Available

1. **OpenAI**: Now offers **EU Data Residency** option with zero data retention. API requests can be routed to EU endpoints with contractual guarantee of no data storage.
2. **Anthropic**: Offers **Zero Data Retention (ZDR)** agreements for enterprise customers. Data is processed but not stored.
3. **Both**: Provide Data Processing Agreements (DPAs) incorporating Standard Contractual Clauses (SCCs) per European Commission Decision 2021/914.

### Transfer Impact Assessment (TIA) Requirement

Per the EDPB Recommendations 01/2020 on supplementary measures (post-Schrems II), PratikoAI must conduct a Transfer Impact Assessment documenting:
- The specific data transferred (anonymized queries only, NOT raw client data)
- Laws of the recipient country affecting data protection (US FISA 702, Executive Order 12333)
- Supplementary measures applied (PII anonymization, zero data retention, encryption in transit)
- Overall assessment of adequacy

---

## 4. Italian AI Law (Law 132/2025) - New Requirement

### Overview

Italy's national AI regulation (Legge 13 settembre 2025, n. 132) introduces additional requirements for AI system operators, supplementing the EU AI Act.

### Key Requirement for PratikoAI

PratikoAI must **notify the Garante per la protezione dei dati personali** of all AI-related processing activities. Specifically:

- **Notification obligation**: Before deploying AI systems that process personal data, operators must communicate the processing activities to the Garante
- **30-day waiting period**: Processing may only begin 30 days after notification, unless the Garante objects earlier
- **Content**: Notification must include description of AI processing activities, data categories, purposes, list of all data processors involved

### Impact

This is a **gating requirement** for public launch. The 30-day waiting period must be factored into the launch timeline.

---

## 5. Professional Secrecy (Segreto Professionale) - No Geographic Restriction

### Applicable Laws

- **D.Lgs. 139/2005**: Regulation of the commercialista (chartered accountant) profession
- **Legge 12/1979**: Regulation of the consulente del lavoro (labor consultant) profession
- **Art. 622 Codice Penale**: Criminal liability for breach of professional secrecy

### Key Finding

Italian professional secrecy laws do NOT impose geographic restrictions on data storage. They require:

1. **Adequate technical measures**: Encryption, access controls, audit logs (PratikoAI implements all)
2. **Adequate organizational measures**: Policies, training, NDAs
3. **Proper contractual safeguards**: DPA under GDPR Article 28 with cloud providers
4. **Confidentiality guarantees**: All personnel with data access must be bound by confidentiality

### Implication for PratikoAI

PratikoAI as the data processor (responsabile del trattamento) must ensure:
- DPA with each professional studio (titolare del trattamento) per Article 28 GDPR
- DPA with Hetzner as sub-processor per Article 28(4) GDPR
- General authorization mechanism allowing studios to approve sub-processor changes
- These are already planned in Phase 9 (DEV-372/DEV-373)

---

## 6. Perimetro di Sicurezza Nazionale Cibernetica - NOT Applicable

### What It Is

The PSNC (D.L. 105/2019, converted to L. 133/2019) establishes Italy's national cybersecurity perimeter. It imposes strict requirements on ICT procurement, data handling, and incident reporting for entities within scope.

### Why PratikoAI Is Not In Scope

The PSNC applies ONLY to:
- Government agencies and public administrations
- Entities performing essential state functions
- Critical national infrastructure operators (energy, telecoms, transport, finance at national scale)

A **B2B SaaS platform** serving private professional studios is NOT an entity performing essential state functions and is NOT critical national infrastructure. Therefore, PSNC requirements do not apply.

---

## 7. Hetzner Gaps to Address

| Gap | Impact | Mitigation |
|---|---|---|
| **No encryption at rest by default** | HIGH | Implement LUKS full-disk encryption or PostgreSQL TDE on our VPS instances. The existing field-level encryption (`app/core/encryption/encrypted_types.py` with AES-256-GCM) covers PII fields (codice_fiscale, partita_iva, importi) but full-disk encryption adds defense-in-depth. |
| **No ISO 27017/27018** (cloud-specific privacy certifications) | MEDIUM | Document in DPIA why ISO 27001:2022 + BSI C5 Type 2 provides adequate coverage. ISO 27017/27018 are "nice to have" but not legally required. |
| **2022 Strasbourg data loss incident** (OVHcloud fire affected some Hetzner customers) | MEDIUM | Maintain independent backup system outside Hetzner primary data center. Use geographically separate backup location (e.g., Hetzner Falkenstein if primary is Nuremberg, or external provider). |
| **No data centers in Italy** | LOW | Legally irrelevant under GDPR Article 1(3) (intra-EU free movement). Document rationale in DPIA for transparency. |

---

## The 7 Critical Compliance Actions Before Launch

### CRITICAL Priority (Must do before ANY client data is stored)

#### Action 1: Conduct a Formal DPIA

- **Requirement**: GDPR Article 35, Garante Provvedimento 11/10/2018
- **Scope**: All data categories, processing purposes, risks, mitigations, LLM sub-processor assessment
- **Owner**: @Severino (Security), @Mario (Requirements)
- **Task**: DEV-396
- **Output**: `docs/compliance/DPIA_PratikoAI.md`

#### Action 2: Sign DPA with Hetzner

- **How**: Via https://accounts.hetzner.com/account/dpa
- **Requirements**: Ensure EU-only server location is selected (Nuremberg or Falkenstein)
- **Owner**: @Silvano (DevOps)
- **Task**: DEV-397

#### Action 3: Execute DPAs with OpenAI and Anthropic

- **OpenAI**: Enable EU Data Residency with zero data retention
- **Anthropic**: Negotiate Zero Data Retention (ZDR) agreement
- **Both**: Ensure DPAs include Standard Contractual Clauses (SCCs)
- **Additional**: Conduct and document Transfer Impact Assessment (TIA) for US transfers
- **Owner**: @Severino (Security), @Ezio (Backend)
- **Task**: DEV-398

#### Action 4: Prepare DPA Template for Professional Studios

- **Structure**: PratikoAI = Responsabile del trattamento (data processor), Studio = Titolare del trattamento (data controller)
- **Include**: General authorization mechanism for sub-processor changes, data processing purposes, security measures, breach notification procedures
- **Status**: Already planned in DEV-372/DEV-373 (Phase 9)

### HIGH Priority (Must do before public launch)

#### Action 5: Notify the Garante under AI Law (Law 132/2025)

- **Requirement**: Communicate all AI-related processing activities to the Garante
- **Content**: AI processing description, data categories, all data processors (Hetzner, OpenAI, Anthropic)
- **Timeline**: 30-day waiting period after notification before processing may begin
- **Owner**: @Mario (Business Analyst)
- **Task**: DEV-399

#### Action 6: Implement Encryption at Rest on Hetzner

- **Options**: LUKS full-disk encryption OR PostgreSQL TDE
- **Note**: Complements existing field-level AES-256-GCM encryption in `app/core/encryption/encrypted_types.py`
- **Owner**: @Silvano (DevOps)
- **Task**: DEV-397

#### Action 7: Publish Sub-Processor List and Privacy Policy

- **Sub-processor list**: Per EDPB Opinion 22/2024, full chain visibility required
- **Privacy policy**: In Italian, covering Art. 12-13 GDPR requirements
- **Owner**: @Severino (Security), @Mario (Business Analyst)
- **Task**: DEV-400

---

## Comparison: Hetzner vs Italian Provider (Aruba Cloud)

| Aspect | Hetzner (Germany) | Aruba Cloud (Italy) |
|---|---|---|
| **ISO 27001** | Yes (2022) | Yes |
| **ISO 27017/27018** | No | Yes |
| **BSI C5 Type 2** | Yes | No |
| **Data centers in Italy** | No | Yes (3 locations) |
| **CISPE Code of Conduct** | No | Yes |
| **Estimated annual cost** | ~EUR 508 | Higher (est. 2-3x) |
| **US CLOUD Act exposure** | No | No |
| **GDPR compliant** | Yes | Yes |

**Verdict**: Both are legally compliant for EU/Italian data storage. Hetzner is significantly more cost-effective (~EUR 10,000/year savings per ADR-006). Aruba offers more cloud-specific privacy certifications (ISO 27017/27018, CISPE) and data residency in Italy. The choice is cost vs. certification depth. Hetzner is adequate if the rationale is documented in the DPIA.

---

## Document Inconsistencies Found and Corrected

The following inconsistencies were identified in `docs/tasks/PRATIKO_2.0_REFERENCE.md` and have been corrected:

1. **Line 1496**: Listed "AWS (Amazon)" as sub-processor for hosting/database, but actual deployment decision (ADR-006) chose Hetzner. **Corrected to**: Hetzner Online GmbH.

2. **Line 1406**: Listed "AWS eu-south-1 (Milano) o Hetzner (Germania)" as hosting options, but decision is already finalized for Hetzner. **Corrected to**: Hetzner (Germania - Norimberga/Falkenstein).

3. **ADR-024 in PRATIKO_2.0.md**: Referenced as "GDPR Client Data Architecture" but the actual file at `docs/architecture/decisions/ADR-024-workflow-automation-architecture.md` is about workflow automation. **Corrected**: ADR-024 description updated to "Workflow Automation Architecture"; new ADR-025 created for GDPR Client Data Architecture.

---

## Legal References

| Reference | Full Citation |
|---|---|
| GDPR Art. 1(3) | Regulation (EU) 2016/679, Article 1(3) - Free movement of personal data within the Union |
| GDPR Art. 28 | Regulation (EU) 2016/679, Article 28 - Processor obligations and DPA requirements |
| GDPR Art. 35 | Regulation (EU) 2016/679, Article 35 - Data protection impact assessment |
| GDPR Art. 44-49 | Regulation (EU) 2016/679, Articles 44-49 - Transfers to third countries |
| GDPR Art. 83(4) | Regulation (EU) 2016/679, Article 83(4) - Administrative fines for DPIA non-compliance |
| D.Lgs. 196/2003 | Codice in materia di protezione dei dati personali (Italian Privacy Code) |
| D.Lgs. 101/2018 | Amendments to D.Lgs. 196/2003 aligning with GDPR |
| D.Lgs. 139/2005 | Ordinamento della professione di dottore commercialista |
| Legge 12/1979 | Ordinamento della professione di consulente del lavoro |
| Legge 132/2025 | Italian AI Law (Legge 13 settembre 2025, n. 132) |
| D.L. 105/2019 | Perimetro di Sicurezza Nazionale Cibernetica |
| Garante 11/10/2018 | Provvedimento - Elenco tipologie trattamenti soggetti a DPIA |
| Garante Dec 2024 | Provvedimento nei confronti di OpenAI - sanzione EUR 15M |
| EDPB 01/2020 | Recommendations on supplementary measures for international transfers |
| EDPB 22/2024 | Opinion on sub-processor transparency and full chain visibility |
| EC Decision 2021/914 | Standard Contractual Clauses for international data transfers |

---

## Bottom Line

**Storing client data on Hetzner is legally permissible and adequate.** The real compliance risks are:

1. **Not having a DPIA** (mandatory, penalties up to EUR 10M)
2. **LLM data transfers to US** (OpenAI/Anthropic) without proper DPAs, SCCs, and TIA
3. **Not notifying the Garante** under Italy's new AI Law (Law 132/2025)
4. **No encryption at rest** on Hetzner (must implement LUKS or PostgreSQL TDE ourselves)

None of these risks are blockers - they all have clear mitigations. But they **MUST** be addressed before storing any real client data.

The new tasks DEV-396 through DEV-401 track these compliance actions in the project roadmap.
