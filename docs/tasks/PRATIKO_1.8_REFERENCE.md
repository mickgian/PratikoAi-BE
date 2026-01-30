# PratikoAI v1.8 - Requisiti Funzionali
## Motore Autonomo di Workflow per Professionisti Italiani

**Versione:** 1.8
**Data:** Gennaio 2026
**Stato:** Discovery / Pre-Sviluppo
**Autore:** Product Owner
**Architettura:** ADR-024

---

## 1. Executive Summary

### 1.1 Visione del Prodotto

PratikoAI 1.8 evolve da assistente proattivo (v1.5) a **motore autonomo di workflow** che:
- Permette di delegare task complessi multi-step ("Prepara dichiarazione redditi per Mario Rossi")
- Esegue workflow in background mentre il professionista lavora su altro
- Notifica al completamento con deliverable professionali pronti
- Mantiene controllo umano configurabile (checkpoint di approvazione)

**Modello di riferimento:** Claude Cowork - la stessa esperienza "fire and forget" adattata per workflow di compliance italiana.

**Posizionamento nel Roadmap:**
- **PRATIKO_1.5** → Assistente proattivo (azioni suggerite, domande interattive)
- **PRATIKO_1.8** → Motore autonomo di workflow (questa versione)
- **PRATIKO_2.0** → Piattaforma di engagement (database clienti, matching normativo)

### 1.2 Value Proposition

| Problema Attuale | Soluzione 1.8 | Beneficio |
|------------------|---------------|-----------|
| Workflow manuali multi-step richiedono ore | Automazione end-to-end con supervisione | -70% tempo per adempimenti |
| Documenti sparsi tra email, cartelle, portali | Projects con folder sync centralizzato | +50% organizzazione |
| Scadenze dimenticate o gestite manualmente | Tracking automatico con notifiche | -90% scadenze mancate |
| Solo web = richiede connessione attiva | App desktop con background processing | Lavoro asincrono |
| Percezione di "assistente passivo" | Workflow autonomo come "collega virtuale" | Differenziazione mercato |

### 1.3 Scope

**In Scope (v1.8):**
- App desktop (Kotlin Multiplatform + Compose)
- Sistema Projects con folder sync locale
- 4 workflow core: Dichiarazione Redditi, Adempimenti Periodici, Apertura/Chiusura, Pensionamento
- Human-in-the-loop configurabile
- Generazione documenti (Modelli pre-compilati)
- Integrazione API dove disponibile (AdE, INPS)
- Companion web per accesso remoto

**Out of Scope (rimandato a v2.0):**
- Database clienti completo
- Matching automatico clienti-normative
- Generazione comunicazioni per clienti
- Integrazione WhatsApp/Email
- Dashboard ROI avanzati
- App mobile native (Android/iOS)

---

## 2. Contesto e Vincoli

### 2.1 Stato Attuale PratikoAI (v1.5)

**Funzionalit esistenti riutilizzabili:**
- LangGraph pipeline 134 step con checkpointing
- SSE streaming per aggiornamenti real-time
- AsyncPostgresSaver per persistenza stato
- Analisi documenti (Fattura, F24, Bilancio, CU)
- Calcoli fiscali (IRPEF, IVA, ritenute, contributi)
- Template YAML per azioni suggerite
- Sistema di domande interattive

**Metriche attuali da preservare:**
- Costo per utente: 1.45/giorno → target 2.00/giorno (overhead workflow)
- Qualit risposte: 91% → target 90%
- Tempo risposta Q&A: P95 2.1s → invariato (workflow separati)

### 2.2 Vincoli Tecnici

| Vincolo | Valore | Motivazione |
|---------|--------|-------------|
| App desktop size | 30MB | User experience download |
| Memory footprint | 100MB idle | Esecuzione background |
| Sync latency | 5s | Folder sync responsive |
| Workflow checkpoint | 30s max | Attesa approvazione utente |
| Document storage | EU only | GDPR compliance |
| Offline capability | Lettura progetti | Accesso documenti senza rete |

### 2.3 Vincoli di Business

- **Timeline MVP:** 15-20 settimane (2-3h/giorno)
- **Risorse:** 1 sviluppatore + possibile contractor KMP
- **Piattaforma iniziale:** macOS (come Claude Cowork)
- **Priorit:** Workflow funzionante > UI perfetta
- **Approccio:** Desktop MVP → Primo workflow → Iterazione

### 2.4 Vincoli GDPR

| Requisito | Implementazione |
|-----------|-----------------|
| Base legale | Contratto (servizio professionale) |
| Data residency | Hetzner Germania (EU) |
| Minimizzazione | Solo documenti necessari per workflow |
| Retention | Configurabile (default 2 anni, auto-purge opzionale) |
| Portabilit | Export completo progetti in formato standard |
| Cancellazione | Right to erasure implementato |
| Audit trail | Log completo operazioni per Art. 30 |

---

## 3. Requisiti Funzionali

### 3.1 FR-001: App Desktop con Projects

#### 3.1.1 Descrizione

App desktop nativa (Kotlin Multiplatform + Compose) che organizza il lavoro in **Projects**, ciascuno contenente documenti, stato workflow e cronologia interazioni. Replica l'esperienza Claude Desktop/Cowork per professionisti italiani.

#### 3.1.2 User Stories

**US-001.1:** Come commercialista, voglio creare un Project "Mario Rossi - 730/2026" per organizzare tutti i documenti e le operazioni relative a quel cliente/adempimento.

**US-001.2:** Come professionista, voglio designare una cartella locale che si sincronizza automaticamente con il Project, cos i documenti che salvo l si caricano automaticamente.

**US-001.3:** Come professionista, voglio vedere lo stato di tutti i miei Projects attivi nella sidebar dell'app, con indicatore di avanzamento workflow.

**US-001.4:** Come professionista, voglio ricevere notifiche di sistema quando un workflow richiede la mia approvazione o  completato.

**US-001.5:** Come professionista mobile, voglio accedere ai miei Projects anche da web per verificare lo stato quando non sono al computer principale.

#### 3.1.3 Struttura Project

```yaml
Project:
  id: "uuid-project-001"
  name: "Mario Rossi - 730/2026"
  client:
    name: "Mario Rossi"
    codice_fiscale: "RSSMRA80A01H501Z"  # Opzionale
  workflow_type: "dichiarazione_redditi_730"
  status: "in_progress"  # draft | in_progress | pending_approval | completed | archived

  documents:
    - id: "doc-001"
      filename: "CU_2025.pdf"
      type: "certificazione_unica"
      sync_status: "synced"
      extracted_data:
        reddito_lordo: 45230.00
        ritenute_irpef: 12456.00
    - id: "doc-002"
      filename: "spese_mediche/"
      type: "folder"
      sync_status: "synced"
      document_count: 12

  workflow_state:
    current_step: "document_validation"
    progress_percent: 33
    checkpoints_completed: ["document_collection"]
    checkpoints_pending: ["data_validation", "calculation", "generation", "final_review"]

  local_folder: "/Users/mario/Clienti/Rossi_Mario/730_2026"
  created_at: "2026-01-15T10:30:00Z"
  updated_at: "2026-01-30T14:22:00Z"
```

#### 3.1.4 UI Desktop - Componenti Principali

**Sidebar (sinistra):**
```
┌──────────────────────────┐
│  PRATIKO                 │
├──────────────────────────┤
│  Projects                │
│  ├─ Mario Rossi 730      │
│  │  ████████░░ 80%       │
│  ├─ Studio ABC F24       │
│  │  ██░░░░░░░░ 20%       │
│  ├─ Nuova Attivit        │
│  │  Pending approval     │
│  └─ + Nuovo Project      │
├──────────────────────────┤
│  Recenti                 │
│  Chat Q&A                │
│  Impostazioni            │
└──────────────────────────┘
```

**Area principale (Project selezionato):**
```
┌────────────────────────────────────────────────────────────────────┐
│  Mario Rossi - 730/2026                              [Sync] []   │
├────────────────────────────────────────────────────────────────────┤
│  Documenti                    │  Workflow                         │
│  ┌──────────────────────────┐ │  ┌──────────────────────────────┐ │
│  │  CU_2025.pdf       ✓     │ │  │  Step 1: Raccolta       ✓    │ │
│  │  spese_mediche/    ✓     │ │  │  Step 2: Validazione    →    │ │
│  │  mutuo.pdf         ✓     │ │  │  Step 3: Calcolo        ○    │ │
│  │  + Aggiungi documento    │ │  │  Step 4: Generazione    ○    │ │
│  └──────────────────────────┘ │  │  Step 5: Revisione      ○    │ │
│                               │  └──────────────────────────────┘ │
│  Cartella sincronizzata:      │                                   │
│  /Users/mario/Clienti/Rossi   │  [Avvia Workflow] [Checkpoint]    │
│  [Apri cartella] [Cambia]     │                                   │
├────────────────────────────────────────────────────────────────────┤
│  Cronologia                                                        │
│  14:22 - Documento aggiunto: mutuo.pdf                            │
│  14:20 - Validazione CU completata                                │
│  10:30 - Project creato                                           │
└────────────────────────────────────────────────────────────────────┘
```

#### 3.1.5 Folder Sync

**Meccanismo:**
1. Utente designa cartella locale per Project
2. File system watcher monitora modifiche
3. Nuovi file → upload automatico al backend
4. File generati da workflow → download in cartella locale
5. Conflitti → notifica utente con opzioni (mantieni locale / mantieni server / rinomina)

**Tipi file supportati:**
- PDF (fatture, modelli, certificazioni)
- XML (FatturaPA, F24 telematico)
- Immagini (scontrini, ricevute)
- Excel/CSV (import dati)

**File ignorati:**
- .DS_Store, Thumbs.db, .git/
- File > 50MB (avviso utente)
- File temporanei (~*, .tmp)

#### 3.1.6 Criteri di Accettazione

- [ ] AC-001.1: Creazione Project con nome, tipo workflow e cartella locale
- [ ] AC-001.2: Folder sync bidirezionale funzionante entro 5s
- [ ] AC-001.3: Progress indicator workflow visibile in sidebar
- [ ] AC-001.4: Notifiche di sistema per checkpoint e completamento
- [ ] AC-001.5: Accesso Projects da web app (sola lettura + stato)
- [ ] AC-001.6: Offline: visualizzazione documenti cached
- [ ] AC-001.7: App size 30MB, memory idle 100MB

---

### 3.2 FR-002: Workflow Dichiarazione dei Redditi (730/Redditi PF)

#### 3.2.1 Descrizione

Workflow completo per la preparazione della dichiarazione dei redditi persone fisiche, dalla raccolta documenti alla generazione del modello compilato.

#### 3.2.2 User Stories

**US-002.1:** Come commercialista, voglio caricare i documenti del cliente (CU, spese mediche, mutuo) e far elaborare automaticamente il 730.

**US-002.2:** Come professionista, voglio verificare i dati estratti dai documenti prima che vengano usati per i calcoli.

**US-002.3:** Come commercialista, voglio vedere il riepilogo dei calcoli IRPEF con le detrazioni applicate prima della generazione finale.

**US-002.4:** Come professionista, voglio ricevere il Modello 730 compilato in formato PDF pronto per la revisione.

**US-002.5:** Come commercialista, dopo la revisione voglio poter inviare telematicamente (se disponibile API) o scaricare per invio manuale.

#### 3.2.3 Workflow Steps

```yaml
Workflow_Dichiarazione_Redditi:
  id: "dichiarazione_redditi_730"
  name: "Dichiarazione dei Redditi 730"
  estimated_duration: "15-30 minuti"

  steps:
    - id: "document_collection"
      name: "Raccolta Documenti"
      description: "Caricamento CU, spese deducibili/detraibili"
      required_documents:
        - type: "certificazione_unica"
          required: true
          description: "CU 2025 del datore di lavoro"
        - type: "spese_mediche"
          required: false
          description: "Scontrini, fatture mediche"
        - type: "interessi_mutuo"
          required: false
          description: "Certificazione banca per interessi passivi"
        - type: "spese_istruzione"
          required: false
          description: "Ricevute scuola, universit"
        - type: "contributi_previdenza"
          required: false
          description: "Fondi pensione, previdenza complementare"
      checkpoint: false  # Nessuna approvazione, raccolta automatica

    - id: "document_validation"
      name: "Validazione Documenti"
      description: "OCR ed estrazione dati dai documenti"
      actions:
        - "ocr_extraction"
        - "data_validation"
        - "cross_reference_check"
      checkpoint: true  # CHECKPOINT: Conferma dati estratti
      checkpoint_message: "Verifica i dati estratti dai documenti"

    - id: "deduction_identification"
      name: "Identificazione Deduzioni/Detrazioni"
      description: "Analisi spese per deducibilit e detraibilit"
      actions:
        - "categorize_expenses"
        - "apply_limits"  # Es: max 19% su 129.11 franchigia
        - "check_eligibility"
      checkpoint: false

    - id: "tax_calculation"
      name: "Calcolo IRPEF"
      description: "Calcolo imposta lorda, detrazioni, imposta netta"
      actions:
        - "calculate_gross_tax"
        - "apply_deductions"
        - "calculate_regional_municipal"
        - "determine_refund_or_due"
      checkpoint: true  # CHECKPOINT: Verifica calcoli
      checkpoint_message: "Verifica il riepilogo calcoli IRPEF"

    - id: "module_generation"
      name: "Generazione Modello"
      description: "Compilazione Modello 730 o Redditi PF"
      actions:
        - "select_model_type"
        - "fill_quadri"
        - "generate_pdf"
      checkpoint: false

    - id: "final_review"
      name: "Revisione Finale"
      description: "Controllo documento generato e preparazione invio"
      checkpoint: true  # CHECKPOINT: Approvazione finale
      checkpoint_message: "Rivedi e approva il modello generato"
      outputs:
        - "modello_730.pdf"
        - "riepilogo_calcoli.pdf"
        - "documentazione_allegata.zip"
```

#### 3.2.4 Checkpoint: Validazione Documenti

```
┌────────────────────────────────────────────────────────────────────┐
│  CHECKPOINT: Verifica Dati Estratti                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  CU 2025 - Datore: Azienda XYZ S.r.l.                            │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Campo                      │  Valore Estratto    │  ✓/✗    │ │
│  ├──────────────────────────────────────────────────────────────┤ │
│  │  Reddito da lavoro dipend.  │  45.230,00         │  [✓]    │ │
│  │  Ritenute IRPEF             │  12.456,00         │  [✓]    │ │
│  │  Addizionale regionale      │     678,00         │  [✓]    │ │
│  │  Addizionale comunale       │     234,00         │  [✓]    │ │
│  │  Giorni lavoro              │        365         │  [✓]    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  Spese Mediche (12 documenti)                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Totale spese sanitarie     │   1.234,56         │  [✓]    │ │
│  │  Di cui tracciabili         │   1.100,00         │  [✓]    │ │
│  │  Franchigia 129,11        │    -129,11         │  auto   │ │
│  │  Detrazione 19%             │     209,49         │  calc   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  [Modifica valore]  [Aggiungi documento]                          │
│                                                                    │
│  [Approva e continua]              [Richiedi revisione manuale]   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

#### 3.2.5 Checkpoint: Calcolo IRPEF

```
┌────────────────────────────────────────────────────────────────────┐
│  CHECKPOINT: Riepilogo Calcoli IRPEF                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  REDDITO COMPLESSIVO                                              │
│  Reddito da lavoro dipendente      45.230,00                     │
│  Altri redditi                            0,00                     │
│  ─────────────────────────────────────────────                    │
│  TOTALE REDDITO IMPONIBILE         45.230,00                     │
│                                                                    │
│  CALCOLO IRPEF LORDA                                              │
│  Scaglione 0-28.000 (23%)           6.440,00                     │
│  Scaglione 28.001-50.000 (35%)      6.030,50                     │
│  ─────────────────────────────────────────────                    │
│  IRPEF LORDA                       12.470,50                     │
│                                                                    │
│  DETRAZIONI                                                        │
│  Detrazione lavoro dipendente      -1.880,00                     │
│  Detrazione spese mediche            -209,49                     │
│  Detrazione interessi mutuo          -380,00                     │
│  ─────────────────────────────────────────────                    │
│  TOTALE DETRAZIONI                 -2.469,49                     │
│                                                                    │
│  IRPEF NETTA                       10.001,01                     │
│                                                                    │
│  CONFRONTO CON RITENUTE                                           │
│  Ritenute gi versate              12.456,00                     │
│  IRPEF dovuta                      10.001,01                     │
│  ─────────────────────────────────────────────                    │
│  CREDITO IRPEF                     2.454,99                     │
│                                                                    │
│  [Dettaglio calcoli]  [Modifica parametri]                        │
│                                                                    │
│  [Approva e genera modello]        [Richiedi supporto]            │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

#### 3.2.6 Output Generati

| Output | Formato | Descrizione |
|--------|---------|-------------|
| Modello 730 compilato | PDF | Pronto per firma e invio |
| Riepilogo calcoli | PDF | Dettaglio per archivio studio |
| Documentazione | ZIP | Tutti i documenti di input |
| Log elaborazione | JSON | Audit trail completo |

#### 3.2.7 Criteri di Accettazione

- [ ] AC-002.1: Upload documenti CU obbligatorio, altri opzionali
- [ ] AC-002.2: OCR estrae dati con accuracy 95%
- [ ] AC-002.3: Checkpoint validazione mostra tutti i dati estratti
- [ ] AC-002.4: Calcolo IRPEF corretto (validato su casi di test)
- [ ] AC-002.5: Detrazioni applicate secondo normativa vigente
- [ ] AC-002.6: Generazione PDF Modello 730 conforme
- [ ] AC-002.7: Workflow completabile in <30 minuti (escluse attese utente)

---

### 3.3 FR-003: Workflow Adempimenti Periodici

#### 3.3.1 Descrizione

Workflow per la gestione degli adempimenti fiscali ricorrenti: F24, liquidazione IVA, LIPE, CU, Modello 770.

#### 3.3.2 User Stories

**US-003.1:** Come commercialista, voglio preparare automaticamente l'F24 mensile/trimestrale per un cliente basandomi sui dati contabili.

**US-003.2:** Come professionista, voglio che il sistema mi ricordi le scadenze imminenti con sufficiente anticipo.

**US-003.3:** Come commercialista, voglio generare la LIPE trimestrale aggregando i dati IVA gi elaborati.

**US-003.4:** Come professionista, voglio generare le CU per i dipendenti/collaboratori a fine anno.

#### 3.3.3 Sub-Workflow: F24

```yaml
Workflow_F24:
  id: "adempimento_f24"
  name: "Modello F24"
  frequency: "monthly | quarterly"

  steps:
    - id: "data_aggregation"
      name: "Aggregazione Dati"
      description: "Raccolta importi da versare per periodo"
      sources:
        - "contabilit_iva"
        - "ritenute_dipendenti"
        - "contributi_inps"
        - "tributi_locali"
      checkpoint: false

    - id: "amount_calculation"
      name: "Calcolo Importi"
      description: "Determinazione importi per codice tributo"
      checkpoint: true
      checkpoint_message: "Verifica importi da versare"

    - id: "f24_generation"
      name: "Generazione F24"
      description: "Compilazione modello F24"
      outputs:
        - "modello_f24.pdf"
        - "f24_telematico.xml"  # Per invio Entratel
      checkpoint: true
      checkpoint_message: "Approva F24 per invio"
```

#### 3.3.4 Calendario Scadenze

Il sistema traccia automaticamente:

| Adempimento | Scadenza | Frequenza |
|-------------|----------|-----------|
| F24 ritenute dipendenti | 16 mese successivo | Mensile |
| F24 IVA | 16 mese successivo (mensile) / 16 trimestre successivo | Mensile/Trimestrale |
| LIPE | Fine mese successivo trimestre | Trimestrale |
| CU | 16 marzo | Annuale |
| Modello 770 | 31 ottobre | Annuale |

#### 3.3.5 Criteri di Accettazione

- [ ] AC-003.1: Aggregazione dati da fonti multiple
- [ ] AC-003.2: Codici tributo corretti per tipo versamento
- [ ] AC-003.3: Generazione F24 PDF e XML telematico
- [ ] AC-003.4: Notifica scadenze 7 giorni e 1 giorno prima
- [ ] AC-003.5: Tracciamento storico versamenti per cliente

---

### 3.4 FR-004: Workflow Apertura/Chiusura Attivit

#### 3.4.1 Descrizione

Workflow guidato per apertura nuova attivit (P.IVA, iscrizioni enti, SCIA) o chiusura (cancellazioni, liquidazione).

#### 3.4.2 User Stories

**US-004.1:** Come commercialista, voglio una checklist completa dei documenti e passaggi necessari per aprire una nuova P.IVA.

**US-004.2:** Come professionista, voglio generare la documentazione pre-compilata per SCIA, Camera di Commercio, INPS.

**US-004.3:** Come commercialista, per una chiusura attivit voglio verificare che tutti gli adempimenti siano completati.

#### 3.4.3 Workflow Apertura

```yaml
Workflow_Apertura_Attivita:
  id: "apertura_attivita"
  name: "Apertura Nuova Attivit"

  steps:
    - id: "client_profile"
      name: "Profilo Attivit"
      questions:
        - "Tipo attivit (artigiano/commerciante/professionista/societ)"
        - "Codice ATECO"
        - "Regime fiscale (ordinario/forfettario/semplificato)"
        - "Sede legale"
      checkpoint: true

    - id: "checklist_generation"
      name: "Generazione Checklist"
      description: "Lista adempimenti basata su profilo"
      dynamic_items:
        - condition: "tipo == 'artigiano'"
          items: ["iscrizione_albo_artigiani", "inail"]
        - condition: "tipo == 'commerciante'"
          items: ["scia_comunale", "inps_commercianti"]
        - condition: "societa"
          items: ["atto_costitutivo", "camera_commercio", "pec"]
      checkpoint: true

    - id: "document_preparation"
      name: "Preparazione Documenti"
      description: "Generazione modulistica pre-compilata"
      outputs:
        - "richiesta_partita_iva.pdf"
        - "scia_comunale.pdf"  # Se applicabile
        - "iscrizione_inps.pdf"
        - "iscrizione_inail.pdf"  # Se applicabile
      checkpoint: true

    - id: "submission_tracking"
      name: "Tracciamento Invii"
      description: "Monitoraggio stato pratiche"
      integration_level: "guided_rpa"  # Step-by-step con screenshot
```

#### 3.4.4 Criteri di Accettazione

- [ ] AC-004.1: Profilazione attivit con domande guidate
- [ ] AC-004.2: Checklist dinamica basata su tipo attivit
- [ ] AC-004.3: Generazione documenti pre-compilati
- [ ] AC-004.4: Tracciamento stato avanzamento pratiche
- [ ] AC-004.5: Guide step-by-step per portali (SUAP, Registro Imprese)

---

### 3.5 FR-005: Workflow Pensionamento/TFR

#### 3.5.1 Descrizione

Workflow per calcolo pensione, verifica requisiti, preparazione domanda INPS e calcolo TFR.

#### 3.5.2 User Stories

**US-005.1:** Come consulente del lavoro, voglio verificare i requisiti pensionistici di un lavoratore.

**US-005.2:** Come professionista, voglio calcolare l'importo stimato della pensione con diverse opzioni (anticipata, vecchiaia).

**US-005.3:** Come consulente, voglio preparare la domanda di pensione INPS con i dati pre-compilati.

**US-005.4:** Come professionista, voglio calcolare il TFR maturato e le opzioni di liquidazione.

#### 3.5.3 Workflow Steps

```yaml
Workflow_Pensionamento:
  id: "pensionamento"
  name: "Pensionamento e TFR"

  steps:
    - id: "contribution_history"
      name: "Estratto Contributivo"
      description: "Acquisizione storia contributiva INPS"
      required_documents:
        - type: "estratto_conto_inps"
          source: "upload | api_inps"
      checkpoint: true

    - id: "requirements_check"
      name: "Verifica Requisiti"
      calculations:
        - "pensione_anticipata"  # 42 anni e 10 mesi (uomini) / 41 anni e 10 mesi (donne)
        - "pensione_vecchiaia"   # 67 anni
        - "quota_103"            # 62 anni + 41 anni contributi
        - "opzione_donna"        # Se applicabile
      checkpoint: true

    - id: "pension_calculation"
      name: "Calcolo Pensione"
      methods:
        - "retributivo"  # Pre-1996
        - "contributivo" # Post-1996
        - "misto"        # Transizione
      outputs:
        - "simulazione_pensione.pdf"
      checkpoint: true

    - id: "tfr_calculation"
      name: "Calcolo TFR"
      inputs:
        - "anni_servizio"
        - "retribuzione_annua"
        - "anticipi_erogati"
      outputs:
        - "prospetto_tfr.pdf"
      checkpoint: true

    - id: "application_preparation"
      name: "Preparazione Domanda"
      outputs:
        - "domanda_pensione_inps.pdf"
      integration_level: "api_where_available"  # INPS API se disponibile
```

#### 3.5.4 Criteri di Accettazione

- [ ] AC-005.1: Import estratto conto INPS (PDF o API)
- [ ] AC-005.2: Verifica requisiti per tutte le forme pensionistiche
- [ ] AC-005.3: Calcolo pensione con metodo corretto
- [ ] AC-005.4: Calcolo TFR secondo formula di legge
- [ ] AC-005.5: Generazione domanda INPS pre-compilata

---

### 3.6 FR-006: Human-in-the-Loop Configurabile

#### 3.6.1 Descrizione

Sistema di checkpoint configurabile che permette al professionista di scegliere il livello di supervisione per ogni workflow.

#### 3.6.2 User Stories

**US-006.1:** Come commercialista esperto, voglio ridurre i checkpoint per workflow che conosco bene.

**US-006.2:** Come nuovo utente, voglio approvare ogni step significativo per verificare che il sistema funzioni correttamente.

**US-006.3:** Come professionista, voglio poter interrompere un workflow in qualsiasi momento.

**US-006.4:** Come titolare di studio, voglio configurare le policy di supervisione per i collaboratori.

#### 3.6.3 Modi di Supervisione

```yaml
Supervision_Modes:
  full_supervision:
    name: "Supervisione Completa"
    description: "Approvazione richiesta per ogni step significativo"
    risk_level: "LOWEST"
    default_for: ["new_users", "complex_workflows"]

  approval_required:
    name: "Approvazione ai Checkpoint"
    description: "Approvazione solo ai checkpoint definiti"
    risk_level: "LOW"
    default_for: ["standard_users"]

  confidence_based:
    name: "Basato su Confidenza"
    description: "Auto-procede se confidenza >90%, altrimenti chiede"
    risk_level: "MEDIUM"
    requires: ["user_opt_in"]

  review_checkpoints:
    name: "Solo Revisione Finale"
    description: "Esegue tutto, pausa solo per revisione finale"
    risk_level: "HIGHER"
    requires: ["explicit_consent"]
```

#### 3.6.4 Configurazione per Workflow

```yaml
# Esempio configurazione utente
user_workflow_settings:
  user_id: "uuid-user-001"

  workflow_settings:
    dichiarazione_redditi_730:
      supervision_mode: "approval_required"
      custom_checkpoints:
        - "document_validation"  # Sempre attivo
        - "tax_calculation"      # Sempre attivo
        - "final_review"         # Sempre attivo

    adempimento_f24:
      supervision_mode: "confidence_based"
      confidence_threshold: 0.95
      custom_checkpoints:
        - "amount_confirmation"  # Sempre per importi

    apertura_attivita:
      supervision_mode: "full_supervision"  # Workflow complesso, sempre supervisionato
```

#### 3.6.5 Emergency Stop

```
┌────────────────────────────────────────────────────────────────────┐
│  EMERGENCY STOP                                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Workflow interrotto dall'utente                                 │
│                                                                    │
│   Stato salvato al checkpoint: "tax_calculation"                  │
│   Dati non persi                                                   │
│                                                                    │
│   Opzioni:                                                         │
│   [Riprendi da qui]  [Ricomincia]  [Archivia]                     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

#### 3.6.6 Criteri di Accettazione

- [ ] AC-006.1: 4 modi di supervisione selezionabili
- [ ] AC-006.2: Configurazione persistente per utente e workflow
- [ ] AC-006.3: Emergency stop disponibile in qualsiasi momento
- [ ] AC-006.4: Stato workflow salvato ad ogni step
- [ ] AC-006.5: Ripresa workflow da ultimo checkpoint

---

### 3.7 FR-007: Integrazione Sistemi Esterni

#### 3.7.1 Descrizione

Sistema di integrazione modulare con livelli progressivi: prepare-only, API dove disponibile, guided RPA.

#### 3.7.2 Livelli di Integrazione

| Livello | Descrizione | Implementazione |
|---------|-------------|-----------------|
| **PREPARE_ONLY** | Genera documenti, utente invia manualmente | PDF/XML generation |
| **API_WHERE_AVAILABLE** | Usa API ufficiali dove esistono | FatturaPA, INPS, F24 Web |
| **GUIDED_RPA** | Guide step-by-step con screenshot | Portali senza API |

#### 3.7.3 Integrazioni Target

| Sistema | Livello Iniziale | API Disponibile |
|---------|------------------|-----------------|
| Agenzia delle Entrate | PREPARE_ONLY | S (Entratel/Fisconline) |
| INPS | PREPARE_ONLY | Parziale |
| INAIL | PREPARE_ONLY | No |
| Camera di Commercio | GUIDED_RPA | No |
| SUAP Comunale | GUIDED_RPA | No |
| F24 Web | API_WHERE_AVAILABLE | S |
| FatturaPA | API_WHERE_AVAILABLE | S |

#### 3.7.4 Criteri di Accettazione

- [ ] AC-007.1: Fallback a PREPARE_ONLY sempre disponibile
- [ ] AC-007.2: Configurazione livello per workflow
- [ ] AC-007.3: API FatturaPA funzionante
- [ ] AC-007.4: API F24 Web funzionante
- [ ] AC-007.5: Guide RPA con screenshot per portali principali

---

## 4. Requisiti Non Funzionali

### 4.1 Performance

| Metrica | Target | Motivazione |
|---------|--------|-------------|
| Startup app desktop | <3s | UX accettabile |
| Sync folder change | <5s | Reattivit percepita |
| Workflow step | <30s | Esclude attese umane |
| Checkpoint notification | <1s | Reattivit |
| OCR document | <10s | Estrazione dati |
| PDF generation | <5s | Output finale |

### 4.2 Reliability

| Metrica | Target |
|---------|--------|
| Uptime backend | 99.5% |
| Data durability | 99.99% |
| Workflow completion rate | >95% |
| Checkpoint state recovery | 100% |

### 4.3 Security

| Requisito | Implementazione |
|-----------|-----------------|
| Encryption at rest | AES-256 |
| Encryption in transit | TLS 1.3 |
| Authentication | OAuth 2.0 / JWT |
| Authorization | RBAC per studio |
| Audit logging | Completo per GDPR |

### 4.4 Scalability

| Scenario | Target |
|----------|--------|
| Concurrent workflows per studio | 10 |
| Documents per project | 100 |
| Projects per studio | 500 |
| File size max | 50MB |

---

## 5. API Contracts

### 5.1 Projects API

```yaml
# GET /api/v1/projects
Response:
  - id: "uuid"
    name: "string"
    workflow_type: "string"
    status: "draft | in_progress | pending_approval | completed | archived"
    progress_percent: 0-100
    documents_count: number
    last_activity: "datetime"

# POST /api/v1/projects
Request:
  name: "string"
  workflow_type: "string"
  client_id: "uuid?"
  local_folder_path: "string?"
Response:
  id: "uuid"
  ... project fields

# GET /api/v1/projects/{id}
Response:
  ... full project with documents, workflow_state, checkpoints

# POST /api/v1/projects/{id}/documents
Request:
  file: binary
  document_type: "string?"
Response:
  document_id: "uuid"
  extracted_data: object?
  sync_status: "string"
```

### 5.2 Workflows API

```yaml
# POST /api/v1/projects/{id}/workflow/start
Request:
  supervision_mode: "string?"
Response:
  workflow_task_id: "uuid"
  status: "started"
  current_step: "string"

# GET /api/v1/projects/{id}/workflow/status
Response:
  status: "running | pending_checkpoint | completed | failed"
  current_step: "string"
  progress_percent: number
  pending_checkpoint: object?

# POST /api/v1/projects/{id}/workflow/checkpoint/{checkpoint_id}/approve
Request:
  approved: boolean
  modifications: object?
Response:
  status: "resumed"
  next_step: "string"

# POST /api/v1/projects/{id}/workflow/stop
Response:
  status: "stopped"
  saved_at_step: "string"
```

### 5.3 Sync API (Desktop)

```yaml
# POST /api/v1/sync/upload
Request:
  project_id: "uuid"
  file: binary
  local_path: "string"
  checksum: "string"
Response:
  document_id: "uuid"
  cloud_path: "string"

# GET /api/v1/sync/changes/{project_id}
Query:
  since: "datetime"
Response:
  changes:
    - type: "added | modified | deleted"
      document_id: "uuid"
      cloud_path: "string"
      checksum: "string"

# POST /api/v1/sync/download/{document_id}
Response:
  file: binary
  checksum: "string"
```

---

## 6. Glossario

| Termine | Definizione |
|---------|-------------|
| **Project** | Unit organizzativa contenente documenti, workflow state, cronologia |
| **Workflow** | Sequenza di step automatizzati per completare un adempimento |
| **Checkpoint** | Punto nel workflow che richiede approvazione umana |
| **Folder Sync** | Sincronizzazione bidirezionale tra cartella locale e cloud |
| **Supervision Mode** | Livello di controllo umano su un workflow |
| **Integration Level** | Grado di automazione nell'invio a sistemi esterni |

---

## 7. Riferimenti

- **ADR-024**: Workflow Automation Architecture
- **ADR-017**: Multi-tenancy Architecture (studio_id)
- **ADR-020**: Suggested Actions Architecture
- **Claude Cowork**: [Iniziare con Cowork](https://support.claude.com/articles/13345190-iniziare-con-cowork)
- **GDPR**: Regolamento (UE) 2016/679

---

**Documento soggetto ad approvazione @egidio (Architect)**
