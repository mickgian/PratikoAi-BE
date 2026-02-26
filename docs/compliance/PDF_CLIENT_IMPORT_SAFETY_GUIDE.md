# Guida Sicurezza: Import Clienti via PDF (FR-002)

**Data:** 2026-02-26
**Stato:** DRAFT
**Autore:** @Ezio (Backend), @Severino (Security)
**Riferimenti:** FR-002, ADR-014 (SQLModel), ADR-017 (Multi-tenancy), ADR-023 (Document Ingestion)

---

## Indice

1. [Panoramica](#1-panoramica)
2. [Architettura Tecnica](#2-architettura-tecnica)
3. [Sicurezza PDF - Threat Model](#3-sicurezza-pdf---threat-model)
4. [Protezione Dati Clienti](#4-protezione-dati-clienti)
5. [Checklist Compliance (DPA, Accordi, GDPR)](#5-checklist-compliance-dpa-accordi-gdpr)
6. [Checklist Implementazione Tecnica](#6-checklist-implementazione-tecnica)
7. [Checklist Pre-Lancio](#7-checklist-pre-lancio)

---

## 1. Panoramica

FR-002 (Database Clienti dello Studio) viene esteso per supportare l'import di liste clienti
da file PDF, in aggiunta ai formati Excel (.xlsx) e CSV già previsti.

**Caso d'uso primario:** Un professionista esporta la lista clienti dal proprio gestionale
(TeamSystem, Zucchetti, etc.) in formato PDF e la carica su PratikoAI per popolare il
database clienti senza redigitazione manuale.

**Dati trattati:** Dati personali e fiscali di persone fisiche e giuridiche, inclusi:
- Codice Fiscale, Partita IVA (dati identificativi)
- Regime fiscale, Codice ATECO (dati professionali)
- Importi debiti fiscali, posizioni INPS/INAIL (dati finanziari sensibili)
- Indirizzo, CAP, comune (dati geografici)
- Email, telefono (dati di contatto)

**Classificazione dati:** ALTO RISCHIO - Dati finanziari e fiscali di clienti di studi professionali.

---

## 2. Architettura Tecnica

### 2.1 Flusso Import PDF

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  Upload PDF │────▶│  Sicurezza   │────▶│  Estrazione   │────▶│  Validazione │
│  (Frontend) │     │  (Scan+Val)  │     │  (pdfplumber) │     │  (CF/PIVA)   │
└─────────────┘     └──────────────┘     └───────────────┘     └──────────────┘
                                                                       │
                    ┌──────────────┐     ┌───────────────┐            │
                    │   Persist    │◀────│   Preview &   │◀───────────┘
                    │  (Encrypted) │     │   Conferma    │
                    └──────────────┘     └───────────────┘
```

### 2.2 Componenti

| Componente | Responsabilità | File |
|------------|----------------|------|
| `DocumentUploader` | Validazione sicurezza, malware scan | `app/services/document_uploader.py` |
| `PdfClientExtractor` (nuovo) | Estrazione tabellare da PDF | `app/services/pdf_client_extractor.py` |
| `ClientImportService` (nuovo) | Orchestrazione import, validazione, persistenza | `app/services/client_import_service.py` |
| `ClientValidationService` (nuovo) | Validazione CF, P.IVA, CAP, ATECO | `app/services/client_validation_service.py` |

### 2.3 Librerie (già in pyproject.toml)

| Libreria | Versione | Uso |
|----------|----------|-----|
| `pdfplumber>=0.9.0` | Estrazione tabelle strutturate da PDF |
| `PyPDF2>=3.0.1` | Lettura metadata PDF, info pagine |
| `pytesseract>=0.3.10` | OCR per PDF scansionati |
| `python-magic>=0.4.27` | Rilevamento MIME type |

---

## 3. Sicurezza PDF - Threat Model

### 3.1 Minacce Specifiche PDF

| Minaccia | Rischio | Mitigazione | Stato |
|----------|---------|-------------|-------|
| **JavaScript incorporato** | ALTO - Esecuzione codice arbitrario | Bloccare/rimuovere JS prima del parsing. Config: `ALLOW_JAVASCRIPT_IN_PDF=false` | Implementato in `DocumentUploader` |
| **Embedded files** | ALTO - Malware nascosto in allegati | Rifiutare PDF con file incorporati | Implementato in `DocumentUploader` |
| **Launch actions** | ALTO - Apertura programmi esterni | Bloccare /Launch e /URI actions | Implementato in `DocumentUploader` |
| **PDF bomb (zip bomb)** | MEDIO - DoS via espansione | Limite dimensione decompressed, timeout parsing | Implementato (entropy check) |
| **Font malevoli** | MEDIO - Exploit parser font | pdfplumber in sandbox, limite pagine | Da implementare (limit già previsto) |
| **Macro/form fields** | MEDIO - Iniezione dati | Ignorare form fields, estrarre solo testo tabellare | Da implementare |
| **File troncato/corrotto** | BASSO - Crash parser | Try/catch robusto, validazione struttura | Implementato |
| **Metadata exfiltration** | BASSO - Info sensibili in metadata | Strippare metadata dopo estrazione | Da implementare |

### 3.2 Controlli di Sicurezza Obbligatori

```python
# Configurazione sicurezza PDF per import clienti
PDF_IMPORT_SECURITY = {
    "ALLOW_JAVASCRIPT": False,          # MAI per import clienti
    "ALLOW_EMBEDDED_FILES": False,       # MAI per import clienti
    "ALLOW_LAUNCH_ACTIONS": False,       # MAI per import clienti
    "MAX_FILE_SIZE_MB": 25,              # Limite dimensione
    "MAX_PAGES": 200,                    # Limite pagine
    "MAX_ROWS_PER_IMPORT": 10_000,       # Limite righe estratte
    "PARSING_TIMEOUT_SECONDS": 120,      # Timeout parsing
    "OCR_TIMEOUT_SECONDS": 300,          # Timeout OCR (più lento)
    "REQUIRE_VIRUS_SCAN": True,          # ClamAV obbligatorio
    "STRIP_METADATA_AFTER_EXTRACTION": True,
}
```

### 3.3 Scansione Antivirus

Il `DocumentUploader` esistente implementa già:

1. **Signature-based detection** - Pattern eseguibili, script malevoli
2. **Heuristic analysis** - Entropia file, API sospette
3. **Document-specific scanning** - JS in PDF, macro in Excel, XXE in XML
4. **ClamAV integration** - Daemon esterno (configurabile)
5. **VirusTotal integration** - API cloud (opzionale, per hash check)

Per l'import clienti PDF, **ClamAV è OBBLIGATORIO** (non opzionale) data la
classificazione ad alto rischio dei dati trattati.

---

## 4. Protezione Dati Clienti

### 4.1 Encryption at Rest

Tutti i campi sensibili nel database clienti DEVONO usare i tipi crittografati
definiti in `app/core/encryption/encrypted_types.py`:

| Campo | Tipo Crittografato | Algoritmo |
|-------|--------------------|-----------|
| `codice_fiscale` | `EncryptedTaxID` | AES-256-CBC |
| `partita_iva` | `EncryptedTaxID` | AES-256-CBC |
| `email` | `EncryptedEmail` | AES-256-CBC |
| `telefono` | `EncryptedPhone` | AES-256-CBC |
| `importo_debiti_fiscali` | `EncryptedFinancialData` | AES-256-CBC |
| `indirizzo` | `EncryptedPersonalData` | AES-256-CBC |

### 4.2 File Temporanei

| Aspetto | Regola |
|---------|--------|
| Storage PDF uploadato | Crittografato, auto-cancellazione dopo 48h (DOCUMENT_CONFIG) |
| Dati estratti in memoria | Mai scritti su disco in chiaro |
| Preview dati | Solo in-memory, non persistita |
| Log operazione | NO dati personali nei log, solo contatori e ID |

### 4.3 Multi-Tenancy (ADR-017)

- Ogni client record ha `studio_id` come FK obbligatoria
- Il service layer filtra SEMPRE per `studio_id` dell'utente corrente
- Cross-tenant access = vulnerability critica → test obbligatori

### 4.4 Audit Trail (AC-002.5)

Ogni operazione di import DEVE essere loggata:

```python
logger.info(
    "client_import_completed",
    studio_id=studio.id,
    user_id=user.id,
    source_format="pdf",
    total_rows_extracted=150,
    valid_rows=145,
    invalid_rows=5,
    import_duration_seconds=12,
    # MAI loggare: CF, P.IVA, nomi, importi
)
```

---

## 5. Checklist Compliance (DPA, Accordi, GDPR)

### 5.1 Obblighi del Titolare (Studio Professionale)

Lo studio professionale è il **Titolare del trattamento** (Art. 4(7) GDPR). Prima di
caricare dati clienti su PratikoAI, lo studio DEVE:

- [ ] **5.1.1** Avere una base giuridica per il trattamento dati clienti (Art. 6 GDPR)
  - Tipicamente: esecuzione contratto (Art. 6(1)(b)) o obbligo legale (Art. 6(1)(c))
- [ ] **5.1.2** Aver informato i propri clienti sul trattamento dati (Art. 13/14 GDPR)
  - Informativa privacy aggiornata che menziona PratikoAI come responsabile del trattamento
- [ ] **5.1.3** Aver raccolto consenso per profilazione, se applicabile (Art. 22 GDPR)
  - Il matching normativo automatico potrebbe configurare "profilazione" per i clienti dello studio
  - Campo `consenso_profilazione` nel modello Cliente
- [ ] **5.1.4** Aver aggiornato il Registro dei Trattamenti (Art. 30 GDPR)
  - Includere PratikoAI come responsabile e i sub-responsabili (Hetzner, OpenAI, Anthropic)

### 5.2 DPA tra Studio e PratikoAI (Art. 28 GDPR)

PratikoAI agisce come **Responsabile del trattamento** (Art. 4(8) GDPR).
Il DPA deve includere:

- [ ] **5.2.1** Oggetto e durata del trattamento
- [ ] **5.2.2** Natura e finalità del trattamento (gestione anagrafica, matching normativo)
- [ ] **5.2.3** Tipo di dati personali trattati (elenco completo dal §1 sopra)
- [ ] **5.2.4** Categorie di interessati (clienti dello studio: persone fisiche e giuridiche)
- [ ] **5.2.5** Obblighi e diritti del titolare del trattamento
- [ ] **5.2.6** Istruzioni documentate del titolare (Art. 28(3)(a))
- [ ] **5.2.7** Obbligo di riservatezza del personale PratikoAI (Art. 28(3)(b))
- [ ] **5.2.8** Misure di sicurezza tecniche e organizzative (Art. 28(3)(c), Art. 32)
  - Crittografia AES-256-CBC at rest
  - TLS 1.3 in transit
  - Multi-tenancy con isolamento row-level
  - Scansione antivirus obbligatoria
  - PII anonymization prima di chiamate LLM
- [ ] **5.2.9** Condizioni per sub-responsabili (Art. 28(2) e 28(4))
  - Autorizzazione generale scritta con obbligo di notifica
  - Lista sub-responsabili: Hetzner (hosting), OpenAI/Anthropic (LLM, solo dati anonimizzati)
- [ ] **5.2.10** Assistenza al titolare per diritti degli interessati (Art. 28(3)(e))
  - Supporto per accesso, rettifica, cancellazione, portabilità
- [ ] **5.2.11** Cancellazione/restituzione dati a fine contratto (Art. 28(3)(g))
  - Export completo + cancellazione certificata (sistema GDPR deletion già implementato)
- [ ] **5.2.12** Notifica data breach entro 24h a PratikoAI → PratikoAI notifica studio entro 48h → studio notifica Garante entro 72h (Art. 33)
- [ ] **5.2.13** Diritto di audit (Art. 28(3)(h))

**Stato:** Template DPA pianificato in DEV-372/DEV-373 (Fase 9)

### 5.3 DPA tra PratikoAI e Sub-Responsabili

- [ ] **5.3.1** DPA con Hetzner (hosting dati) → Via https://accounts.hetzner.com/account/dpa (DEV-397)
- [ ] **5.3.2** DPA con OpenAI (LLM) → Con SCCs e EU Data Residency (DEV-398)
- [ ] **5.3.3** DPA con Anthropic (LLM) → Con SCCs e Zero Data Retention (DEV-398)
- [ ] **5.3.4** Transfer Impact Assessment per trasferimenti USA (DEV-398)

### 5.4 DPIA (Valutazione d'Impatto)

L'import PDF di dati clienti rientra nella DPIA già richiesta per PratikoAI:

- [ ] **5.4.1** DPIA include specificamente il flusso di import clienti (DEV-396)
- [ ] **5.4.2** DPIA copre rischi specifici PDF (malware, estrazione errata, data leakage)
- [ ] **5.4.3** DPIA documenta misure di mitigazione per import PDF

### 5.5 Segreto Professionale (D.Lgs. 139/2005, L. 12/1979)

- [ ] **5.5.1** Il DPA include clausole specifiche sul segreto professionale
- [ ] **5.5.2** Il personale PratikoAI con accesso ai dati è vincolato da NDA
- [ ] **5.5.3** Accesso ai dati clienti limitato al solo sistema automatizzato (nessun accesso umano in produzione)

### 5.6 Legge AI Italiana (L. 132/2025)

- [ ] **5.6.1** Notifica al Garante include il processing di dati clienti via matching normativo AI (DEV-399)
- [ ] **5.6.2** 30 giorni di attesa rispettati prima di attivare il matching su dati reali

### 5.7 Consensi Specifici Import PDF

- [ ] **5.7.1** UI di upload mostra informativa sintetica prima del caricamento
- [ ] **5.7.2** Checkbox conferma: "Confermo di avere base giuridica per il trattamento dei dati contenuti in questo file"
- [ ] **5.7.3** Log del consenso con timestamp, user_id, studio_id, filename (hash, non nome reale)

---

## 6. Checklist Implementazione Tecnica

### 6.1 Backend - Servizi

- [ ] **6.1.1** `PdfClientExtractor` - Estrazione tabellare da PDF
  - pdfplumber per tabelle native
  - pytesseract fallback per PDF scansionati
  - Riconoscimento automatico header colonne
  - Mapping colonne → schema Cliente
- [ ] **6.1.2** `ClientImportService` - Orchestrazione import
  - Supporto Excel, CSV, PDF (strategy pattern)
  - Validazione batch con report errori per riga
  - Transazione atomica (tutto o niente, con opzione "importa validi")
  - Rate limiting: max 5 import/ora per studio
- [ ] **6.1.3** `ClientValidationService` - Validazione dati italiani
  - Codice Fiscale: algoritmo di check (omocodia inclusa)
  - Partita IVA: check digit modulo 11
  - CAP: lookup database comuni ISTAT
  - Codice ATECO: validazione tabella ISTAT
- [ ] **6.1.4** Endpoint API: `POST /api/v1/studios/{studio_id}/clients/import`
  - Accetta: multipart/form-data con file PDF/Excel/CSV
  - Risponde: preview dati estratti + errori validazione
- [ ] **6.1.5** Endpoint API: `POST /api/v1/studios/{studio_id}/clients/import/confirm`
  - Accetta: import_id + lista righe confermate
  - Risponde: risultato import (inseriti/aggiornati/errori)

### 6.2 Backend - Sicurezza

- [ ] **6.2.1** Estendere `DocumentUploader` per import clienti con ClamAV obbligatorio
- [ ] **6.2.2** PDF parsing in processo isolato (subprocess/timeout) per prevenire crash
- [ ] **6.2.3** Strippare metadata PDF dopo estrazione
- [ ] **6.2.4** Zero PII in log (solo contatori, UUID, hash)
- [ ] **6.2.5** File temporanei: in-memory o encrypted temp dir con auto-cleanup

### 6.3 Backend - Modello Dati

- [ ] **6.3.1** Modello `Client` SQLModel con campi crittografati (§4.1)
- [ ] **6.3.2** Modello `ClientImportJob` per tracking import asincroni
- [ ] **6.3.3** Migrazione Alembic per tabelle `client` e `client_import_job`
- [ ] **6.3.4** Indici per ricerca: `denominazione`, `codice_fiscale` (encrypted), `partita_iva` (encrypted)

### 6.4 Frontend

- [ ] **6.4.1** Componente upload con drag&drop (PDF/Excel/CSV)
- [ ] **6.4.2** Progress bar durante estrazione
- [ ] **6.4.3** Preview tabella dati estratti con evidenziazione errori
- [ ] **6.4.4** Mapping colonne interattivo (drag&drop o dropdown)
- [ ] **6.4.5** Checkbox conferma consenso pre-upload
- [ ] **6.4.6** Testo UI in italiano

### 6.5 Test (TDD - ADR-013)

- [ ] **6.5.1** Test estrazione PDF: tabella strutturata (happy path)
- [ ] **6.5.2** Test estrazione PDF: PDF scansionato con OCR
- [ ] **6.5.3** Test estrazione PDF: nessuna tabella trovata (edge case)
- [ ] **6.5.4** Test sicurezza: PDF con JavaScript → rifiutato
- [ ] **6.5.5** Test sicurezza: PDF con embedded files → rifiutato
- [ ] **6.5.6** Test sicurezza: PDF > 25MB → rifiutato
- [ ] **6.5.7** Test sicurezza: PDF > 200 pagine → rifiutato
- [ ] **6.5.8** Test validazione: CF valido/invalido
- [ ] **6.5.9** Test validazione: P.IVA valido/invalido
- [ ] **6.5.10** Test multi-tenancy: import non accessibile da altro studio
- [ ] **6.5.11** Test audit: log generato per ogni import
- [ ] **6.5.12** Test performance: 1000 righe estratte in <60s

---

## 7. Checklist Pre-Lancio

### 7.1 Prima di accettare QUALSIASI dato cliente reale

- [ ] **7.1.1** DPIA completata e documentata (DEV-396)
- [ ] **7.1.2** DPA firmato con Hetzner (DEV-397)
- [ ] **7.1.3** DPA firmato con OpenAI e Anthropic (DEV-398)
- [ ] **7.1.4** Template DPA per studi professionali pronto (DEV-372/373)
- [ ] **7.1.5** Notifica al Garante inviata + 30gg attesa completata (DEV-399)
- [ ] **7.1.6** Encryption at rest su Hetzner (LUKS o PostgreSQL TDE) (DEV-397)
- [ ] **7.1.7** Privacy policy in italiano pubblicata (DEV-400)
- [ ] **7.1.8** Lista sub-responsabili pubblicata (DEV-400)

### 7.2 Prima del rilascio feature PDF import

- [ ] **7.2.1** ClamAV configurato e funzionante in QA e produzione
- [ ] **7.2.2** Test di sicurezza PDF superati (§6.5.4-6.5.7)
- [ ] **7.2.3** Test multi-tenancy superati (§6.5.10)
- [ ] **7.2.4** Test performance superati (§6.5.12)
- [ ] **7.2.5** Tutti i pre-commit hooks passano (ruff, mypy, pytest)
- [ ] **7.2.6** Coverage ≥70% per nuovo codice
- [ ] **7.2.7** UI informativa pre-upload implementata (§5.7)
- [ ] **7.2.8** Audit logging verificato (§4.4)

### 7.3 Ongoing (post-lancio)

- [ ] **7.3.1** Monitoraggio errori estrazione PDF (alert se >10% fallimenti)
- [ ] **7.3.2** Rotazione chiavi crittografia ogni trimestre (già implementato)
- [ ] **7.3.3** Audit GDPR trimestrale (sistema audit già in `app/core/privacy/gdpr_compliance_audit.py`)
- [ ] **7.3.4** Aggiornamento DPIA se cambiano sub-responsabili o flussi dati
- [ ] **7.3.5** Retention: cancellazione automatica file PDF uploadati dopo 48h

---

## Riferimenti

| Documento | Path |
|-----------|------|
| FR-002 Specifica | `docs/tasks/PRATIKO_2.0_REFERENCE.md` §3.2 |
| GDPR Investigation | `docs/compliance/GDPR_INVESTIGATION_CLIENT_DATA_HETZNER.md` |
| Database Encryption | `docs/DATABASE_ENCRYPTION.md` |
| GDPR Data Export | `docs/GDPR_DATA_EXPORT.md` |
| GDPR Data Deletion | `docs/GDPR_DATA_DELETION.md` |
| Document Uploader | `app/services/document_uploader.py` |
| Encrypted Types | `app/core/encryption/encrypted_types.py` |
| ADR-014 SQLModel | `docs/architecture/decisions/ADR-014-*` |
| ADR-017 Multi-tenancy | `docs/architecture/decisions/ADR-017-*` |
| ADR-023 Document Ingestion | `docs/architecture/decisions/ADR-023-*` |
| ADR-033 Redis Security | `docs/architecture/decisions/ADR-033-*` |

---

## Riepilogo Priorità

| Priorità | Azione | Bloccante per |
|----------|--------|---------------|
| **CRITICA** | DPA template per studi (§5.2) | Qualsiasi dato cliente reale |
| **CRITICA** | DPIA aggiornata con flusso PDF (§5.4) | Qualsiasi dato cliente reale |
| **CRITICA** | DPA sub-responsabili firmati (§5.3) | Qualsiasi dato cliente reale |
| **ALTA** | ClamAV in produzione (§3.3) | Rilascio feature PDF |
| **ALTA** | Test sicurezza PDF (§6.5) | Rilascio feature PDF |
| **ALTA** | Notifica Garante AI Law (§5.6) | Lancio pubblico |
| **MEDIA** | UI consenso pre-upload (§5.7) | UX completa |
| **MEDIA** | Monitoraggio post-lancio (§7.3) | Operations |
