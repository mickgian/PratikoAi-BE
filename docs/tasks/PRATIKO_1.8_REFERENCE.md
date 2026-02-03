# PratikoAI v1.8 - Requisiti Funzionali
## Social Campaign Creator per Professionisti Italiani

**Versione:** 1.8
**Data:** Febbraio 2026
**Stato:** Discovery / Pre-Sviluppo
**Autore:** Product Owner
**Architettura:** ADR-025 (pending)

---

## 1. Executive Summary

### 1.1 Visione del Prodotto

PratikoAI 1.8 evolve coPratiko in un **Social Campaign Creator** che:
- Genera campagne social media complete per professionisti italiani
- Utilizza lo Scadenzario Fiscale Italiano come fonte di contenuti predefinita
- Automatizza la creazione di design in Canva tramite Browser MCP
- Offre un ciclo di feedback iterativo (Settimana → Mese → Anno)
- Opera in sandbox OS-level per la sicurezza

**Modello di riferimento:** Claude Cowork - stessa esperienza "fire and forget" adattata per la creazione di contenuti social.

**Posizionamento nel Roadmap:**
- **PRATIKO_1.5** → Assistente proattivo (azioni suggerite, domande interattive)
- **PRATIKO_1.8** → Social Campaign Creator (questa versione)
- **PRATIKO_1.9** → Workflow Fiscali Autonomi (backlog)
- **PRATIKO_2.0** → Piattaforma di engagement (database clienti, matching normativo)

### 1.2 Value Proposition

| Problema Attuale | Soluzione 1.8 | Beneficio |
|------------------|---------------|-----------|
| Commercialisti spendono 2-4h/settimana sui social | coPratiko genera un anno di contenuti in ~30 minuti | -90% tempo per social media |
| Contenuti non allineati con scadenze fiscali | Contenuti automaticamente legati allo Scadenzario | Maggiore rilevanza |
| Design manuali in Canva | Automazione completa via Browser MCP | -100% lavoro design |
| Costi elevati per social media manager | $5-25/mese per utente | Risparmio significativo |
| Percezione di "assistente passivo" | Workflow autonomo come "social media manager virtuale" | Differenziazione mercato |

### 1.3 Scope

**In Scope (v1.8):**
- Generazione contenuti social per 4 piattaforme (Instagram, Facebook, LinkedIn, Twitter)
- Integrazione Scadenzario Fiscale Italiano 2026
- Ricerca web per topic personalizzati (Brave Search)
- Estrazione brand voice da asset caricati
- Automazione Canva via Browser MCP
- Ciclo iterativo: Settimana → Mese → Anno
- Sandbox OS-level (macOS VM, Windows WSL2, Linux Docker)
- UI Desktop (KMP) + Web (Next.js)

**Out of Scope (rimandato):**
- Pubblicazione automatica sui social
- Scheduling integrato
- Analytics sui post
- App mobile native

---

## 2. Contesto e Vincoli

### 2.1 Stato Attuale PratikoAI (v1.5)

**Funzionalità esistenti riutilizzabili:**
- LangGraph pipeline con checkpointing
- SSE streaming per aggiornamenti real-time
- AsyncPostgresSaver per persistenza stato
- Analisi documenti (estrazione dati)
- Sistema di domande interattive
- Tree of Thoughts reasoning

**Metriche attuali da preservare:**
- Costo per utente: 1.45€/giorno → target 5-25€/mese (social campaign)
- Qualità risposte: 91% → target 90%
- Tempo risposta Q&A: P95 2.1s → invariato (workflow separati)

### 2.2 Vincoli Tecnici

| Vincolo | Valore | Motivazione |
|---------|--------|-------------|
| Costo LLM per campagna | $5-25/mese | Business model sostenibile |
| Browser MCP latency | <2s per azione | UX accettabile |
| Canva design time | <60s per design | Workflow efficiente |
| Sandbox overhead | <100MB RAM | Esecuzione background |
| Document storage | EU only | GDPR compliance |
| Offline capability | Solo visualizzazione | Canva richiede connessione |

### 2.3 Vincoli di Business

- **Timeline MVP:** 5 settimane (2h/giorno)
- **Risorse:** 1 sviluppatore + Claude Code
- **Piattaforma iniziale:** macOS + Windows (WSL2)
- **Priorità:** Workflow funzionante > UI perfetta
- **Approccio:** Backend → Canva automation → UI

### 2.4 Vincoli GDPR

| Requisito | Implementazione |
|-----------|-----------------|
| Base legale | Contratto (servizio professionale) |
| Data residency | Hetzner Germania (EU) |
| Minimizzazione | Solo documenti necessari per generazione |
| Retention | Configurabile (default 90 giorni) |
| Portabilità | Export campagne in formato standard |
| Cancellazione | Right to erasure implementato |
| Audit trail | Log completo operazioni per Art. 30 |

---

## 3. Requisiti Funzionali

### 3.1 FR-001: Selezione Progetto e Brand Assets

#### 3.1.1 Descrizione

L'utente seleziona una cartella locale contenente documenti del cliente e asset del brand. coPratiko analizza i contenuti per estrarre la brand voice e lo stile comunicativo.

#### 3.1.2 User Stories

**US-001.1:** Come commercialista, voglio selezionare una cartella con i documenti del mio cliente per iniziare la creazione della campagna.

**US-001.2:** Come professionista, voglio caricare logo, palette colori e linee guida del brand per personalizzare i contenuti.

**US-001.3:** Come commercialista, voglio che coPratiko analizzi automaticamente i documenti per capire lo stile comunicativo da adottare.

#### 3.1.3 Brand Assets Supportati

```yaml
Brand_Assets:
  logo:
    formats: ["png", "jpg", "svg"]
    max_size: "5MB"

  colors:
    formats: ["json", "pdf"]  # Color palette
    example: |
      {
        "primary": "#1a365d",
        "secondary": "#2b6cb0",
        "accent": "#ed8936"
      }

  guidelines:
    formats: ["pdf", "docx"]
    content: "Tone of voice, messaging guidelines"

  fonts:
    formats: ["otf", "ttf", "woff"]
    usage: "For Canva design consistency"
```

#### 3.1.4 Criteri di Accettazione

- [ ] AC-001.1: Selezione cartella via picker o drag-drop
- [ ] AC-001.2: Supporto formati: PDF, PNG, JPG, SVG, JSON, DOCX
- [ ] AC-001.3: Estrazione automatica palette colori da logo
- [ ] AC-001.4: Analisi tone of voice da documenti esistenti
- [ ] AC-001.5: Preview documenti nella UI

---

### 3.2 FR-002: Selezione Piattaforme Social

#### 3.2.1 Descrizione

L'utente seleziona una o più piattaforme social target. coPratiko genera contenuti ottimizzati per ciascuna piattaforma.

#### 3.2.2 User Stories

**US-002.1:** Come commercialista, voglio selezionare Instagram e LinkedIn come piattaforme target.

**US-002.2:** Come professionista, voglio che i contenuti siano ottimizzati per ogni piattaforma (lunghezza, hashtag, formato).

#### 3.2.3 Requisiti per Piattaforma

| Piattaforma | Limite Caratteri | Hashtag | Media | Formato Canva |
|-------------|------------------|---------|-------|---------------|
| Instagram | 2,200 | 3-5 | Richiesto | 1080x1080 |
| LinkedIn | 3,000 | 3-5 | Opzionale | 1200x627 |
| Facebook | 63,206 | 1-2 | Opzionale | 1200x630 |
| Twitter/X | 280 | 1-2 | Opzionale | 1600x900 |

#### 3.2.4 Criteri di Accettazione

- [ ] AC-002.1: Multi-selezione piattaforme
- [ ] AC-002.2: Contenuti rispettano limiti caratteri
- [ ] AC-002.3: Hashtag appropriati per piattaforma
- [ ] AC-002.4: Design Canva nel formato corretto

---

### 3.3 FR-003: Selezione Topic e Scadenzario Fiscale

#### 3.3.1 Descrizione

L'utente sceglie i topic per la campagna. Lo Scadenzario Fiscale Italiano è preselezionato, con possibilità di aggiungere topic personalizzati.

#### 3.3.2 User Stories

**US-003.1:** Come commercialista, voglio che i post siano allineati con le scadenze fiscali italiane del 2026.

**US-003.2:** Come professionista, voglio aggiungere topic personalizzati (es. "novità fiscali 2026", "bonus edilizi").

**US-003.3:** Come commercialista, voglio che coPratiko ricerchi online informazioni aggiornate sui topic personalizzati.

#### 3.3.3 Scadenzario Fiscale 2026

```yaml
Scadenzario_Fiscale_2026:
  - date: "2026-01-16"
    deadline: "Versamento IVA mese precedente"
    category: "IVA"
    hashtags: ["#IVA", "#F24", "#scadenzefiscali"]

  - date: "2026-02-28"
    deadline: "Consegna Certificazione Unica (CU)"
    category: "Dichiarazioni"
    hashtags: ["#CU", "#CertificazioneUnica", "#dichiarazioni"]

  - date: "2026-04-30"
    deadline: "Dichiarazione IVA annuale"
    category: "Dichiarazioni"
    hashtags: ["#DichiarazioneIVA", "#adempimenti"]

  - date: "2026-06-16"
    deadline: "Acconto IMU 2026"
    category: "IMU"
    hashtags: ["#IMU", "#tasselocali", "#acconto"]

  - date: "2026-06-30"
    deadline: "Versamento saldo IRPEF"
    category: "IRPEF"
    hashtags: ["#IRPEF", "#dichiarazioneredditi"]

  - date: "2026-09-30"
    deadline: "Modello 730 integrativo"
    category: "Dichiarazioni"
    hashtags: ["#730", "#dichiarazioneredditi"]

  - date: "2026-11-30"
    deadline: "Acconto IRPEF secondo o unico"
    category: "IRPEF"
    hashtags: ["#IRPEF", "#acconto", "#scadenza"]

  - date: "2026-12-16"
    deadline: "Saldo IMU 2026"
    category: "IMU"
    hashtags: ["#IMU", "#saldo", "#tasselocali"]
```

#### 3.3.4 Ricerca Web per Topic Personalizzati

Quando l'utente aggiunge un topic personalizzato:
1. Brave Search cerca informazioni aggiornate
2. Risultati vengono estratti e sintetizzati
3. Contenuto viene usato come context per la generazione

#### 3.3.5 Criteri di Accettazione

- [ ] AC-003.1: Scadenzario Fiscale 2026 precaricato
- [ ] AC-003.2: Possibilità di aggiungere topic personalizzati
- [ ] AC-003.3: Ricerca web automatica per topic custom
- [ ] AC-003.4: Post allineati temporalmente con scadenze

---

### 3.4 FR-004: Generazione Contenuti Iterativa

#### 3.4.1 Descrizione

coPratiko genera contenuti in modo iterativo: prima una settimana (5 post), poi propone di espandere al mese, poi all'anno. L'utente può approvare, modificare o rigenerare ogni post.

#### 3.4.2 User Stories

**US-004.1:** Come commercialista, voglio vedere un'anteprima di 5 post (Lun-Ven) prima di procedere.

**US-004.2:** Come professionista, voglio poter dire "Mi piace" / "Modifica" / "Rigenera" per ogni post.

**US-004.3:** Come commercialista, dopo aver approvato la prima settimana, voglio generare il resto del mese.

**US-004.4:** Come professionista, voglio poter espandere la campagna a tutto l'anno con un click.

#### 3.4.3 Flusso Iterativo

```
┌─────────────────────────────────────────────────────────────────┐
│                      GENERAZIONE ITERATIVA                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. SETTIMANA 1 (5 post)                                         │
│     ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐           │
│     │ Lun   │ │ Mar   │ │ Mer   │ │ Gio   │ │ Ven   │           │
│     └───────┘ └───────┘ └───────┘ └───────┘ └───────┘           │
│                                                                   │
│     Per ogni post: [👍 Mi piace] [✏️ Modifica] [🔄 Rigenera]      │
│                                                                   │
│  2. ESPANSIONE MESE                                               │
│     "Ti è piaciuta la settimana 1! Vuoi generare il resto        │
│      del mese (20 post totali)?"                                  │
│     [Sì, genera mese] [No, solo questa settimana]                │
│                                                                   │
│  3. ESPANSIONE ANNO                                               │
│     "Mese completato! Vuoi generare tutto l'anno                 │
│      (260 post totali)?"                                          │
│     [Sì, genera anno] [No, stop qui]                             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.4.4 Incorporazione Feedback

Quando l'utente chiede modifiche:
```
Utente: "Modifica: tono più formale"
coPratiko: [Rigenera con feedback] → Nuovo post con tono formale
```

Il feedback viene memorizzato e applicato ai post successivi.

#### 3.4.5 Criteri di Accettazione

- [ ] AC-004.1: Generazione iniziale di 5 post (Settimana 1)
- [ ] AC-004.2: Azioni per ogni post: Mi piace / Modifica / Rigenera
- [ ] AC-004.3: Input testuale per feedback specifico
- [ ] AC-004.4: Proposta espansione mese dopo approvazione settimana
- [ ] AC-004.5: Proposta espansione anno dopo approvazione mese
- [ ] AC-004.6: Feedback applicato ai post successivi

---

### 3.5 FR-005: Automazione Canva

#### 3.5.1 Descrizione

Dopo l'approvazione dei contenuti, coPratiko crea automaticamente i design in Canva utilizzando Browser MCP.

#### 3.5.2 User Stories

**US-005.1:** Come commercialista, voglio che coPratiko crei i design in Canva senza il mio intervento.

**US-005.2:** Come professionista, voglio vedere un'anteprima dei design prima del download.

**US-005.3:** Come commercialista, voglio scaricare tutti i design in un file ZIP.

#### 3.5.3 Flusso Automazione Canva

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOMAZIONE CANVA                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. CONNESSIONE                                                   │
│     - Verifica Browser MCP installato                            │
│     - Login Canva (credenziali utente)                           │
│                                                                   │
│  2. CREAZIONE DESIGN (per ogni post)                             │
│     - Seleziona template appropriato                             │
│     - Inserisce testo del post                                   │
│     - Applica colori brand                                       │
│     - Aggiunge elementi grafici                                  │
│     - Screenshot preview                                          │
│                                                                   │
│  3. ESPORTAZIONE                                                  │
│     - Export PNG/PDF per ogni design                             │
│     - Salva in cartella locale                                   │
│     - Crea ZIP con tutti i design                                │
│                                                                   │
│  Progress: [████████░░] 80% - Creazione design 4/5              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.5.4 Browser MCP Actions

| Azione | Parametri | Descrizione |
|--------|-----------|-------------|
| `navigate` | url | Naviga a canva.com |
| `click` | selector | Click su elementi UI |
| `type` | selector, text | Inserisce testo |
| `screenshot` | - | Cattura schermo |
| `download` | format | Esporta design |

#### 3.5.5 Criteri di Accettazione

- [ ] AC-005.1: Setup wizard per Browser MCP
- [ ] AC-005.2: Login automatico Canva
- [ ] AC-005.3: Creazione design da template
- [ ] AC-005.4: Personalizzazione colori brand
- [ ] AC-005.5: Export PNG/PDF
- [ ] AC-005.6: Download ZIP completo
- [ ] AC-005.7: Progress real-time via SSE

---

### 3.6 FR-006: Sandbox e Sicurezza

#### 3.6.1 Descrizione

L'automazione browser viene eseguita in un sandbox OS-level per garantire la sicurezza.

#### 3.6.2 User Stories

**US-006.1:** Come utente, voglio che l'automazione browser sia isolata dal mio sistema.

**US-006.2:** Come professionista, voglio concedere permessi espliciti per l'accesso alle cartelle.

#### 3.6.3 Implementazione Sandbox per Piattaforma

| Piattaforma | Tecnologia | Note |
|-------------|------------|------|
| macOS | VZVirtualMachine | Apple Virtualization Framework |
| Windows | WSL2 | Funziona anche su Home edition! |
| Linux | Docker + seccomp | Isolamento container |

#### 3.6.4 Sistema Permessi Cartelle

```
┌─────────────────────────────────────────────────────────────────┐
│  coPratiko vuole accedere a:                                     │
│  /Users/mario/Clienti/Studio_ABC                                 │
│                                                                   │
│  ☐ Lettura                                                       │
│  ☐ Scrittura                                                     │
│                                                                   │
│  [Consenti una volta] [Consenti sempre] [Nega]                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.6.5 Criteri di Accettazione

- [ ] AC-006.1: Sandbox funzionante su macOS (VM)
- [ ] AC-006.2: Sandbox funzionante su Windows (WSL2)
- [ ] AC-006.3: Sandbox funzionante su Linux (Docker)
- [ ] AC-006.4: Dialog permessi cartelle
- [ ] AC-006.5: Opzione "Consenti sempre"
- [ ] AC-006.6: Revoca permessi dalla UI

---

### 3.7 FR-007: Cost Optimization

#### 3.7.1 Descrizione

Il sistema deve mantenere i costi LLM entro $5-25/mese per utente attivo.

#### 3.7.2 Strategia Multi-Model

| Task | Modello | Costo/1M tokens | Motivazione |
|------|---------|-----------------|-------------|
| Document analysis | Haiku | $1/$5 | Task semplice |
| Brand extraction | Haiku | $1/$5 | Estrazione dati |
| Web research | Haiku | $1/$5 | Sintesi risultati |
| Canva commands | Haiku | $1/$5 | Istruzioni strutturate |
| Content generation | Sonnet | $3/$15 | Creatività richiesta |
| Complex reasoning | Opus | $5/$25 | Solo fallback |

#### 3.7.3 Prompt Caching

```
Scadenzario Fiscale → CACHED (90% risparmio)
Brand Context → CACHED per cliente (90% risparmio)
Post templates → CACHED (90% risparmio)
```

**Risparmio stimato:** 90% sui costi dopo la prima settimana generata.

#### 3.7.4 Criteri di Accettazione

- [ ] AC-007.1: Routing automatico al modello corretto
- [ ] AC-007.2: Prompt caching implementato
- [ ] AC-007.3: Token tracking per utente
- [ ] AC-007.4: Dashboard costi
- [ ] AC-007.5: Costo medio < $25/mese per utente attivo

---

## 4. Requisiti Non Funzionali

### 4.1 Performance

| Metrica | Target | Motivazione |
|---------|--------|-------------|
| Generazione 5 post | <30s | UX accettabile |
| Creazione design Canva | <60s | Automazione efficiente |
| Browser MCP action | <2s | Reattività |
| Startup app desktop | <3s | UX accettabile |

### 4.2 Reliability

| Metrica | Target |
|---------|--------|
| Uptime backend | 99.5% |
| Canva automation success rate | >90% |
| Recovery from browser error | Automatico |

### 4.3 Security

| Requisito | Implementazione |
|-----------|-----------------|
| OS-level isolation | Sandbox (VM/WSL2/Docker) |
| Credential storage | OS Keychain |
| Folder permissions | Explicit consent |
| Network isolation | Sandbox rules |

### 4.4 Scalability

| Scenario | Target |
|----------|--------|
| Concurrent campaigns | 10 per utente |
| Posts per campaign | 260 (1 anno) |
| Designs per campaign | 260 |

---

## 5. API Contracts

### 5.1 Campaign API

```yaml
# POST /api/v1/campaigns
Request:
  folder_path: "string"
  platforms: ["instagram", "linkedin"]
  topics:
    - type: "scadenzario_fiscale"
    - type: "custom"
      query: "novità fiscali 2026"
Response:
  campaign_id: "uuid"
  status: "started"

# GET /api/v1/campaigns/{id}/posts
Response:
  posts:
    - id: "uuid"
      day: "monday"
      content: "string"
      platform: "instagram"
      status: "pending_approval"

# POST /api/v1/campaigns/{id}/posts/{post_id}/approve
Request:
  action: "approve" | "modify" | "regenerate"
  feedback: "string?"  # For modify action
Response:
  status: "approved" | "regenerating"

# POST /api/v1/campaigns/{id}/expand
Request:
  scope: "month" | "year"
Response:
  status: "expanding"
  estimated_posts: 20 | 260

# GET /api/v1/campaigns/{id}/designs
Response:
  designs:
    - id: "uuid"
      post_id: "uuid"
      preview_url: "string"
      download_url: "string"

# GET /api/v1/campaigns/{id}/download
Response:
  zip_url: "string"
```

### 5.2 Canva MCP API

```yaml
# POST /api/v1/canva/connect
Request:
  mcp_server_url: "string"
Response:
  status: "connected"
  tools: ["navigate", "click", "type", "screenshot", "download"]

# POST /api/v1/canva/design
Request:
  campaign_id: "uuid"
  post_id: "uuid"
  template: "string"
  brand_colors: ["#hex1", "#hex2"]
Response:
  status: "creating"

# GET /api/v1/canva/design/{id}/status
Response:
  status: "in_progress" | "completed" | "failed"
  progress: 0-100
  preview_url: "string?"
```

---

## 6. Glossario

| Termine | Definizione |
|---------|-------------|
| **Scadenzario Fiscale** | Calendario delle scadenze fiscali italiane |
| **Brand Voice** | Tono e stile comunicativo del brand |
| **Browser MCP** | Model Context Protocol per automazione browser |
| **Prompt Caching** | Cache dei prompt per ridurre costi LLM |
| **Sandbox** | Ambiente isolato per esecuzione sicura |

---

## 7. Riferimenti

- **Browser MCP:** https://github.com/browser-use/browser-use
- **MCP Specification:** https://modelcontextprotocol.io/
- **Brave Search API:** https://brave.com/search/api/
- **Canva API:** https://www.canva.dev/
- **GDPR:** Regolamento (UE) 2016/679

---

**Documento soggetto ad approvazione @egidio (Architect)**
