# PratikoAI v1.5 - Requisiti Funzionali
## Assistente Proattivo per Professionisti Italiani

**Versione:** 1.5
**Data:** Dicembre 2025
**Stato:** MVP Pre-Engagement Platform
**Autore:** Product Owner

---

## 1. Executive Summary

### 1.1 Visione del Prodotto

PratikoAI 1.5 evolve da assistente Q&A passivo a **assistente proattivo** che:
- Risponde alle domande E suggerisce azioni successive rilevanti
- Chiede chiarimenti in modo strutturato quando la domanda è ambigua
- Guida il professionista verso il prossimo passo logico nel workflow
- Dimostra competenza di dominio attraverso suggerimenti intelligenti

**Posizionamento:** Questa versione rafforza il modello "NormoAI-style" (assistente intelligente) preparando il terreno per la v2.0 (piattaforma di engagement).

### 1.2 Value Proposition

| Problema Attuale | Soluzione 1.5 | Beneficio |
|------------------|---------------|-----------|
| Risposta "morta" - utente non sa cosa fare dopo | Azioni suggerite contestuali | +40% interazioni per sessione |
| Domande vaghe → risposte generiche | Chiarimenti strutturati | +25% precisione risposte |
| Utente deve pensare al prossimo step | Sistema propone workflow logico | -50% tempo per task complessi |
| Percezione di "chatbot generico" | Suggerimenti da esperto di dominio | Differenziazione da ChatGPT |

### 1.3 Scope

**In Scope (v1.5):**
- ✅ Sistema di azioni suggerite post-risposta
- ✅ Domande interattive con opzioni navigabili
- ✅ Template di azioni per scenari comuni
- ✅ UI per selezione azioni e risposta a domande

**Out of Scope (rimandato a v2.0):**
- ❌ Database clienti dello studio
- ❌ Matching automatico clienti-normative
- ❌ Generazione comunicazioni per clienti
- ❌ Integrazione WhatsApp/Email
- ❌ Dashboard ROI e analytics avanzati

---

## 2. Contesto e Vincoli

### 2.1 Stato Attuale PratikoAI (v1.0)

**Funzionalità esistenti utilizzabili:**
- ✅ Chat AI con risposte contestualizzate
- ✅ RSS feed 9 fonti italiane (AdE, INPS, INAIL, MEF, GU, etc.)
- ✅ Sistema FAQ intelligente con cache 80%+
- ✅ Citazioni e riferimenti normativi
- ✅ Upload e analisi documenti (Fattura, F24, Bilancio, CU)
- ✅ Calcoli fiscali (IRPEF, IVA, ritenute, contributi)
- ✅ Classificazione automatica documenti

**Metriche attuali da preservare:**
- Costo per utente: €1.45/giorno → target ≤€1.70/giorno
- Qualità risposte: 91% → target ≥90%
- Tempo risposta P95: 2.1s → target ≤3s

### 2.2 Vincoli Tecnici

| Vincolo | Valore | Motivazione |
|---------|--------|-------------|
| Overhead proattività | ≤500ms | Non degradare UX |
| Token aggiuntivi per suggerimenti | ≤200 tokens | Controllo costi |
| Latenza UI interattiva | ≤100ms | Fluidità navigazione |
| Compatibilità mobile | Touch + keyboard | Accessibilità |

### 2.3 Vincoli di Business

- **Timeline MVP:** 2-3 settimane
- **Risorse:** 1 sviluppatore (2-3h/giorno)
- **Priorità:** Funzionalità > Perfezione
- **Approccio:** Template-first, LLM-enhanced later

---

## 3. Requisiti Funzionali

### 3.1 FR-001: Azioni Suggerite Post-Risposta

#### 3.1.1 Descrizione

Dopo ogni risposta, il sistema presenta 2-4 azioni contestuali che il professionista può eseguire con un click. Le azioni sono determinate dal tipo di domanda, dal contenuto della risposta e dal contesto (es. documento caricato).

#### 3.1.2 User Stories

**US-001.1:** Come commercialista, dopo aver chiesto l'aliquota IVA per un servizio, voglio vedere suggerimenti come "Calcola IVA" o "Normative correlate" così da approfondire senza formulare nuove domande.

**US-001.2:** Come consulente del lavoro, dopo aver caricato una busta paga, voglio vedere azioni come "Verifica contributi INPS" o "Controlla TFR" così da analizzare rapidamente i punti critici.

**US-001.3:** Come professionista, voglio poter ignorare i suggerimenti e continuare a chattare liberamente, così da non sentirmi forzato in un workflow rigido.

**US-001.4:** Come professionista, quando clicco su un'azione suggerita, voglio che venga eseguita immediatamente senza dover confermare, così da risparmiare tempo.

#### 3.1.3 Struttura Output con Azioni

```yaml
Response_With_Actions:
  answer: "L'aliquota IVA ordinaria per i servizi digitali è del 22%..."
  citations:
    - source: "DPR 633/72, Art. 7-octies"
      url: "https://..."
  suggested_actions:
    - id: "calculate_vat"
      label: "Calcola IVA"
      icon: "💰"
      prompt_template: "Calcola l'IVA al 22% per un importo di [IMPORTO]"
      requires_input: true
      input_placeholder: "Inserisci importo (es: 1000)"
    - id: "related_regulations"
      label: "Normative correlate"
      icon: "📋"
      prompt_template: "Mostra circolari e risoluzioni recenti sull'IVA servizi digitali"
      requires_input: false
    - id: "reverse_charge"
      label: "Verifica reverse charge"
      icon: "🔄"
      prompt_template: "Quando si applica il reverse charge per servizi digitali B2B?"
      requires_input: false
```

#### 3.1.4 Template Azioni per Scenario

**Scenario: Risposta a domanda fiscale generica**

| Azione | Label | Icon | Prompt Template |
|--------|-------|------|-----------------|
| calculate | Calcola | 💰 | "Calcola {tipo_imposta} per {parametri}" |
| regulations | Normative correlate | 📋 | "Mostra circolari recenti su {argomento}" |
| examples | Esempi pratici | 📝 | "Fammi un esempio pratico di {argomento}" |
| deadlines | Scadenze | 📅 | "Quali sono le scadenze per {adempimento}?" |

**Scenario: Documento caricato (Fattura Elettronica)**

| Azione | Label | Icon | Prompt Template |
|--------|-------|------|-----------------|
| verify_formal | Verifica formale | ✅ | "Verifica la correttezza formale di questa fattura" |
| calculate_vat | Calcola IVA | 💰 | "Calcola l'IVA di questa fattura" |
| check_recipient | Verifica destinatario | 🔍 | "Verifica Partita IVA e dati del destinatario" |
| accounting_entry | Registrazione contabile | 📒 | "Genera la scrittura contabile per questa fattura" |

**Scenario: Documento caricato (F24)**

| Azione | Label | Icon | Prompt Template |
|--------|-------|------|-----------------|
| verify_codes | Verifica codici tributo | 🔍 | "Verifica la correttezza dei codici tributo" |
| check_deadline | Controlla scadenza | 📅 | "Verifica se la scadenza di pagamento è corretta" |
| calculate_penalties | Calcola ravvedimento | ⚠️ | "Calcola sanzioni e interessi per ravvedimento operoso" |
| find_instructions | Istruzioni compilazione | 📖 | "Mostra le istruzioni per i codici tributo presenti" |

**Scenario: Documento caricato (Bilancio/CU)**

| Azione | Label | Icon | Prompt Template |
|--------|-------|------|-----------------|
| analyze_ratios | Analisi indici | 📊 | "Calcola i principali indici di bilancio" |
| compare_year | Confronto anno precedente | 📈 | "Confronta con l'esercizio precedente" |
| verify_cu | Verifica dati CU | ✅ | "Verifica coerenza tra CU e dichiarazione redditi" |
| extract_summary | Riepilogo | 📋 | "Estrai i dati principali in formato tabellare" |

**Scenario: Aggiornamento normativo (da RSS)**

| Azione | Label | Icon | Prompt Template |
|--------|-------|------|-----------------|
| deep_dive | Approfondisci | 📖 | "Spiega in dettaglio questa normativa" |
| practical_impact | Impatto pratico | 💼 | "Qual è l'impatto pratico per i miei clienti?" |
| original_source | Fonte originale | 🔗 | "Mostra il testo integrale della norma" |
| related_updates | Aggiornamenti correlati | 🔄 | "Ci sono altre novità collegate a questa?" |

#### 3.1.5 Logica di Selezione Azioni

```
Input: query, response, context (document_type, user_history)
                    ↓
┌─────────────────────────────────────────┐
│         INTENT CLASSIFIER               │
│  Determina categoria della query:       │
│  - fiscal_question                      │
│  - calculation_request                  │
│  - document_analysis                    │
│  - regulatory_update                    │
│  - procedural_guidance                  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         TEMPLATE MATCHER                │
│  Seleziona template azioni basato su:   │
│  1. Intent category                     │
│  2. Document type (se presente)         │
│  3. Keywords nella query/response       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         ACTION RANKER                   │
│  Ordina per rilevanza:                  │
│  - Frequenza storica per intent simili  │
│  - Specificità rispetto al contesto     │
│  - Max 4 azioni, min 2 azioni           │
└─────────────────────────────────────────┘
                    ↓
Output: [action_1, action_2, action_3, action_4]
```

#### 3.1.6 Criteri di Accettazione

- [ ] AC-001.1: Ogni risposta include 2-4 azioni suggerite entro 500ms aggiuntivi
- [ ] AC-001.2: Click su azione senza input → esegue immediatamente
- [ ] AC-001.3: Click su azione con input → mostra campo input inline
- [ ] AC-001.4: Azioni sono navigabili da tastiera (Tab, Enter)
- [ ] AC-001.5: Utente può digitare nuova domanda ignorando suggerimenti
- [ ] AC-001.6: Azioni contestuali a documento caricato mostrate automaticamente
- [ ] AC-001.7: Azioni non ripetono informazioni già nella risposta

---

### 3.2 FR-002: Domande Interattive Strutturate

#### 3.2.1 Descrizione

Quando la domanda dell'utente è ambigua o richiede parametri aggiuntivi, il sistema presenta una domanda strutturata con opzioni predefinite navigabili da tastiera, invece di rispondere in modo generico o chiedere in forma libera.

#### 3.2.2 User Stories

**US-002.1:** Come professionista, quando chiedo "calcola l'IRPEF", voglio che il sistema mi chieda il tipo di contribuente con opzioni predefinite (dipendente, autonomo, società) così da non dover riformulare la domanda.

**US-002.2:** Come commercialista, quando chiedo informazioni su una procedura, voglio poter selezionare rapidamente il settore/regime con la tastiera, così da non perdere tempo a scrivere.

**US-002.3:** Come professionista, voglio poter aggiungere dettagli personalizzati oltre alle opzioni predefinite, così da gestire casi particolari.

**US-002.4:** Come professionista, quando il sistema mi fa una domanda, voglio vedere chiaramente quale domanda originale ha generato questa richiesta di chiarimento.

#### 3.2.3 Struttura Domanda Interattiva

```yaml
Interactive_Question:
  trigger_query: "Calcola l'IRPEF"  # Domanda originale
  clarification_needed: true
  question:
    text: "Per quale tipo di contribuente vuoi calcolare l'IRPEF?"
    type: "single_choice"  # single_choice | multi_choice | input_required
    options:
      - id: "dipendente"
        label: "Persona fisica (dipendente)"
        icon: "👔"
        leads_to: "irpef_dipendente_flow"
      - id: "autonomo"
        label: "Persona fisica (autonomo/P.IVA)"
        icon: "💼"
        leads_to: "irpef_autonomo_flow"
      - id: "societa_persone"
        label: "Società di persone"
        icon: "🏢"
        leads_to: "irpef_societa_flow"
      - id: "custom"
        label: "Altro (specifica)"
        icon: "✏️"
        requires_input: true
    allow_custom_input: true
    custom_input_placeholder: "Descrivi la situazione..."
  keyboard_navigation:
    up_down: "Naviga opzioni"
    enter: "Seleziona"
    tab: "Campo personalizzato"
    escape: "Annulla e torna alla chat"
```

#### 3.2.4 Trigger per Domande Interattive

| Trigger | Esempio Query | Domanda Strutturata |
|---------|---------------|---------------------|
| Calcolo senza parametri | "Calcola IRPEF" | Tipo contribuente + reddito |
| Procedura generica | "Apertura attività" | Tipo attività + regime |
| Normativa con varianti | "Aliquota IVA" | Tipo bene/servizio + destinatario |
| Scadenza non specificata | "Quando scade?" | Tipo adempimento |
| Documento non classificato | Upload file generico | Tipo documento |

#### 3.2.5 Esempi Completi

**Esempio 1: Calcolo IRPEF**

```
Utente: "Calcola l'IRPEF"

PratikoAI:
┌────────────────────────────────────────────────────────────────┐
│  📋 Per procedere con il calcolo IRPEF:                        │
│                                                                │
│  Per quale tipo di contribuente?                               │
│                                                                │
│  ○ 👔 Persona fisica (dipendente)                              │
│  ● 💼 Persona fisica (autonomo/P.IVA)     ← Selezionato        │
│  ○ 🏢 Società di persone                                       │
│  ○ ✏️ Altro (specifica)                                        │
│                                                                │
│  [↑↓ Naviga] [Enter Seleziona] [Tab Aggiungi dettagli]         │
│                                                                │
│  💬 Dettagli aggiuntivi: _________________________________     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Dopo selezione "autonomo":**

```
PratikoAI:
┌────────────────────────────────────────────────────────────────┐
│  💰 Inserisci il reddito imponibile:                           │
│                                                                │
│  Reddito annuo lordo: € [____________]                         │
│                                                                │
│  Opzioni veloci:                                               │
│  ○ € 15.000    ○ € 30.000    ○ € 50.000    ○ € 75.000          │
│                                                                │
│  [Enter Calcola] [Esc Annulla]                                 │
└────────────────────────────────────────────────────────────────┘
```

**Esempio 2: Apertura Attività**

```
Utente: "Come si apre un'attività?"

PratikoAI:
┌────────────────────────────────────────────────────────────────┐
│  📋 Per guidarti nell'apertura attività:                       │
│                                                                │
│  Che tipo di attività vuoi aprire?                             │
│                                                                │
│  ○ 🔧 Artigiano                                                │
│  ○ 🏪 Commerciante                                             │
│  ○ 💼 Professionista (con Albo)                                │
│  ○ 📊 Professionista (senza Albo)                              │
│  ○ 🏭 Società (SRL, SAS, SNC...)                               │
│  ○ ✏️ Altro (specifica)                                        │
│                                                                │
│  [↑↓ Naviga] [Enter Seleziona]                                 │
└────────────────────────────────────────────────────────────────┘
```

**Esempio 3: Domanda Multi-Step**

```
Utente: "Verifica questo documento" [upload file]

PratikoAI (se classificazione incerta):
┌────────────────────────────────────────────────────────────────┐
│  📄 Ho ricevuto un documento. Di che tipo si tratta?           │
│                                                                │
│  ○ 🧾 Fattura elettronica                                      │
│  ○ 📝 Modello F24                                              │
│  ○ 📊 Bilancio / Situazione contabile                          │
│  ○ 👤 CU / Certificazione Unica                                │
│  ○ 📋 Contratto di lavoro                                      │
│  ○ ✏️ Altro (specifica)                                        │
│                                                                │
│  [↑↓ Naviga] [Enter Seleziona]                                 │
└────────────────────────────────────────────────────────────────┘
```

#### 3.2.6 Logica di Attivazione

```
Input: user_query, attached_documents
                    ↓
┌─────────────────────────────────────────┐
│         AMBIGUITY DETECTOR              │
│  Analizza se la query:                  │
│  - Manca parametri essenziali           │
│  - Ha più interpretazioni possibili     │
│  - Richiede scelta tra opzioni          │
└─────────────────────────────────────────┘
                    ↓
          ambiguity_score > 0.7?
                    ↓
           ┌───────┴───────┐
           │ YES           │ NO
           ↓               ↓
┌─────────────────┐  ┌─────────────────┐
│ Generate        │  │ Proceed with    │
│ Interactive     │  │ Direct Response │
│ Question        │  │ + Actions       │
└─────────────────┘  └─────────────────┘
```

**Fattori di ambiguità:**
- Query corta (<5 parole) su topic complesso → +0.3
- Verbo generico senza oggetto specifico → +0.2
- Mancanza di parametri numerici per calcolo → +0.4
- Documento non classificato automaticamente → +0.5
- Keyword con multiple interpretazioni → +0.2

#### 3.2.7 Criteri di Accettazione

- [ ] AC-002.1: Domande interattive attivate per query ambigue (accuracy >80%)
- [ ] AC-002.2: Navigazione tastiera funzionante (↑↓ Enter Tab Esc)
- [ ] AC-002.3: Touch/click funzionante su mobile
- [ ] AC-002.4: Opzione "Altro" sempre presente
- [ ] AC-002.5: Campo input personalizzato accessibile
- [ ] AC-002.6: Latenza UI <100ms
- [ ] AC-002.7: Possibilità di saltare e scrivere risposta libera
- [ ] AC-002.8: Contesto originale visibile durante chiarimento
- [ ] AC-002.9: Query con tutti i parametri richiesti → NO domande interattive
- [ ] AC-002.10: Estrazione parametri con accuracy ≥85%
- [ ] AC-002.11: Parametri parziali → domanda solo per quelli mancanti

---

### 3.3 FR-003: Smart Parameter Extraction

#### 3.3.1 Descrizione

Il sistema DEVE estrarre parametri dalla query dell'utente PRIMA di decidere se mostrare domande interattive. Se l'utente fornisce una query completa con tutti i parametri necessari, il sistema risponde direttamente senza interruzioni.

**Principio chiave:** Intelligente ma non invadente. Rispetta l'utente esperto.

#### 3.3.2 User Stories

**US-003.1:** Come commercialista esperto, quando scrivo "Calcola IRPEF autonomo €50.000", voglio ricevere immediatamente il calcolo senza domande intermedie, così da non perdere tempo.

**US-003.2:** Come professionista, quando fornisco solo alcuni parametri (es. "IRPEF €30.000"), voglio che il sistema mi chieda solo ciò che manca (tipo contribuente), non tutto da capo.

**US-003.3:** Come utente, quando il sistema riconosce i miei parametri, voglio vederli confermati nella risposta così da verificare che abbia capito correttamente.

#### 3.3.3 Logica di Estrazione

```
Input: Query utente
            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PARAMETER EXTRACTOR                          │
│                                                                 │
│  1. Identifica INTENT (es: "calcolo_irpef")                    │
│  2. Carica SCHEMA parametri per quell'intent                   │
│  3. Estrae parametri presenti (NER + pattern matching)         │
│  4. Calcola COVERAGE (required params trovati / totali)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
            ↓
      coverage >= 100%?
            ↓
   ┌────────┴────────┐
   │ YES             │ NO
   ↓                 ↓
┌──────────────┐  ┌──────────────────────────────────┐
│ RISPOSTA     │  │ DOMANDA INTERATTIVA              │
│ DIRETTA      │  │ Solo per parametri mancanti      │
│ + Azioni     │  │ Pre-compila quelli già estratti  │
└──────────────┘  └──────────────────────────────────┘
```

#### 3.3.4 Schema Parametri per Intent

```python
INTENT_SCHEMAS = {
    "calcolo_irpef": {
        "required": ["tipo_contribuente", "reddito"],
        "optional": ["detrazioni", "anno_fiscale", "regione"],
        "defaults": {"anno_fiscale": 2025}
    },
    "calcolo_iva": {
        "required": ["importo"],
        "optional": ["aliquota", "tipo_operazione"],
        "defaults": {"aliquota": 22}
    },
    "calcolo_contributi_inps": {
        "required": ["tipo_gestione", "reddito"],
        "optional": ["anno", "minimale"],
        "defaults": {"anno": 2025}
    },
    "apertura_attivita": {
        "required": ["tipo_attivita"],
        "optional": ["settore", "regime_fiscale", "comune"],
        "defaults": {}
    },
    "verifica_scadenza": {
        "required": ["tipo_adempimento"],
        "optional": ["periodo", "anno"],
        "defaults": {"anno": 2025}
    },
    "ravvedimento_operoso": {
        "required": ["importo_originale", "data_scadenza"],
        "optional": ["data_pagamento", "tipo_tributo"],
        "defaults": {"data_pagamento": "oggi"}
    }
}
```

#### 3.3.5 Pattern di Estrazione (Rule-Based MVP)

```python
EXTRACTION_PATTERNS = {
    "tipo_contribuente": {
        "dipendente": r"dipendente|lavoratore\s+dipendente|busta\s+paga|lavoro\s+subordinato",
        "autonomo": r"autonomo|p\.?\s*iva|partita\s+iva|libero\s+professionista|freelance",
        "societa_persone": r"societ[àa]\s+di\s+persone|sas|snc|ss",
        "societa_capitali": r"societ[àa]\s+di\s+capitali|srl|srls|spa"
    },
    "reddito": {
        "pattern": r"(?:€|euro|eur)?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euro|eur)?",
        "normalize": "parse_italian_number",
        "keywords": ["reddito", "imponibile", "lordo", "guadagno", "fatturato"]
    },
    "importo": {
        "pattern": r"(?:€|euro|eur)?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euro|eur)?",
        "normalize": "parse_italian_number"
    },
    "aliquota_iva": {
        "pattern": r"(\d{1,2})\s*%|aliquota\s+(\d{1,2})|iva\s+(?:al\s+)?(\d{1,2})",
        "values": [4, 5, 10, 22]
    },
    "data": {
        "pattern": r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})",
        "normalize": "parse_italian_date"
    },
    "tipo_attivita": {
        "artigiano": r"artigian[oa]|artigianato|mestiere",
        "commerciante": r"commerci(?:ante|o)|negozio|vendita",
        "professionista": r"professionista|studio|consulen(?:te|za)",
        "societa": r"societ[àa]|srl|sas|snc|impresa"
    },
    "regime_fiscale": {
        "forfettario": r"forfet(?:tario|ario)|regime\s+agevolato|flat\s+tax",
        "ordinario": r"ordinario|regime\s+normale|contabilit[àa]\s+(?:ordinaria|semplificata)"
    },
    "gestione_inps": {
        "artigiani": r"gestione\s+artigian|inps\s+artigian",
        "commercianti": r"gestione\s+commerc|inps\s+commerc",
        "separata": r"gestione\s+separata|inps\s+separata|parasubordinat"
    }
}
```

#### 3.3.6 Esempi di Coverage

| Query | Parametri Estratti | Coverage | Comportamento |
|-------|-------------------|----------|---------------|
| "Calcola IRPEF" | ∅ | 0/2 = 0% | ❓ Domanda: tipo + reddito |
| "IRPEF autonomo" | tipo=autonomo | 1/2 = 50% | ❓ Domanda: solo reddito |
| "IRPEF €50.000" | reddito=50000 | 1/2 = 50% | ❓ Domanda: solo tipo |
| "IRPEF autonomo €50.000" | tipo+reddito | 2/2 = 100% | ✅ Risposta diretta |
| "IRPEF dipendente 30k lordi" | tipo+reddito | 2/2 = 100% | ✅ Risposta diretta |
| "Calcola IVA" | ∅ | 0/1 = 0% | ❓ Domanda: importo |
| "IVA su €1.000" | importo=1000 | 1/1 = 100% | ✅ Risposta diretta (22% default) |
| "IVA 10% su €1.000" | importo+aliquota | 1/1 + opt | ✅ Risposta con aliquota specificata |

#### 3.3.7 Risposta con Parametri Estratti

Quando il sistema risponde direttamente, DEVE confermare i parametri estratti:

```
Utente: "Calcola IRPEF autonomo €50.000"

PratikoAI:
┌────────────────────────────────────────────────────────────────┐
│  💰 Calcolo IRPEF - Autonomo                                   │
│                                                                │
│  📋 Parametri:                                                 │
│  • Tipo contribuente: Autonomo/P.IVA                          │
│  • Reddito imponibile: €50.000                                │
│  • Anno fiscale: 2025 (default)                               │
│                                                                │
│  ─────────────────────────────────────────────────────────────  │
│                                                                │
│  Scaglioni IRPEF 2025:                                         │
│  • Fino a €28.000 (23%):       €6.440,00                      │
│  • Da €28.000 a €50.000 (35%): €7.700,00                      │
│                                                                │
│  IRPEF lorda:                  €14.140,00                      │
│  Detrazioni lavoro autonomo:   -€1.265,00                      │
│  ─────────────────────────────────────────────────────────────  │
│  IRPEF netta:                  €12.875,00                      │
│                                                                │
│  📋 Fonte: Art. 11 TUIR, L. 234/2021                          │
│                                                                │
│  ─────────────────────────────────────────────────────────────  │
│  💡 Azioni suggerite:                                           │
│                                                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ 🔄 Ricalcola│ │ 📊 Aggiungi │ │ 📋 Confronta│ │ 📅 Calcola│ │
│  │altro importo│ │ contrib.INPS│ │   regimi    │ │  acconti  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└────────────────────────────────────────────────────────────────┘
```

#### 3.3.8 Domanda con Pre-compilazione

Quando mancano solo alcuni parametri, la domanda mostra quelli già estratti:

```
Utente: "IRPEF su €30.000"

PratikoAI:
┌────────────────────────────────────────────────────────────────┐
│  📋 Calcolo IRPEF                                              │
│                                                                │
│  ✅ Reddito: €30.000 (rilevato dalla tua domanda)             │
│                                                                │
│  ❓ Per quale tipo di contribuente?                            │
│                                                                │
│  ○ 👔 Persona fisica (dipendente)                              │
│  ○ 💼 Persona fisica (autonomo/P.IVA)                          │
│  ○ 🏢 Società di persone                                       │
│  ○ ✏️ Altro (specifica)                                        │
│                                                                │
│  [↑↓ Naviga] [Enter Seleziona]                                 │
└────────────────────────────────────────────────────────────────┘
```

#### 3.3.9 Criteri di Accettazione FR-003

- [ ] AC-003.1: Query completa con tutti i required params → risposta diretta, zero domande
- [ ] AC-003.2: Estrazione parametri con accuracy ≥85% su test set italiano
- [ ] AC-003.3: Parametri estratti mostrati nella risposta per conferma
- [ ] AC-003.4: Parametri parziali → domanda solo per quelli mancanti
- [ ] AC-003.5: Parametri già estratti pre-compilati nella domanda interattiva
- [ ] AC-003.6: Supporto formati numerici italiani (1.000,50 e 1000.50)
- [ ] AC-003.7: Latenza estrazione <100ms
- [ ] AC-003.8: Defaults applicati quando appropriato (es. anno corrente)

---

## 4. Architettura Tecnica

### 4.1 Componenti Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/Next.js)                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Chat Component │  │ Action Buttons  │  │ Interactive     │ │
│  │                 │  │ Component       │  │ Question Modal  │ │
│  │  - Messages     │  │                 │  │                 │ │
│  │  - Input        │  │  - Icon + Label │  │  - Options list │ │
│  │  - Attachments  │  │  - Click handler│  │  - Keyboard nav │ │
│  └─────────────────┘  │  - Keyboard nav │  │  - Custom input │ │
│                       └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   PROACTIVITY ENGINE                        ││
│  │                                                             ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ ││
│  │  │   Intent    │  │  Parameter  │  │  Action Generator   │ ││
│  │  │  Classifier │  │  Extractor  │  │                     │ ││
│  │  │             │  │             │  │  - Template matcher │ ││
│  │  │  - Category │  │  - Patterns │  │  - Context ranker   │ ││
│  │  │  - Keywords │  │  - Coverage │  │  - LLM fallback     │ ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ ││
│  │         │               │                    │              ││
│  │         ▼               ▼                    ▼              ││
│  │  ┌─────────────────────────────────────────────────────┐   ││
│  │  │              DECISION ROUTER                        │   ││
│  │  │                                                     │   ││
│  │  │  coverage >= 100%? ──┬── YES ──▶ Direct Response   │   ││
│  │  │                      │          + Actions          │   ││
│  │  │                      │                              │   ││
│  │  │                      └── NO ───▶ Interactive       │   ││
│  │  │                                  Question          │   ││
│  │  │                                  (missing params)  │   ││
│  │  └─────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                 EXISTING SERVICES                           ││
│  │  Chat Service │ Document Service │ FAQ Service │ RAG Engine ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 API Endpoints

**Endpoint esistente modificato:**

```yaml
POST /api/chat
Request:
  message: string
  attachments: File[]
  session_id: string

Response (UPDATED):
  answer: string
  citations: Citation[]
  # NEW FIELDS:
  suggested_actions: Action[]
  interactive_question: InteractiveQuestion | null
```

**Nuovi endpoints:**

```yaml
POST /api/actions/execute
Request:
  action_id: string
  parameters: object  # Input dall'utente se richiesto
  session_id: string

Response:
  # Stesso formato di /api/chat
  answer: string
  citations: Citation[]
  suggested_actions: Action[]

POST /api/questions/answer
Request:
  question_id: string
  selected_option: string
  custom_input: string | null
  session_id: string

Response:
  # Può essere:
  # 1. Risposta diretta (stessa struttura /api/chat)
  # 2. Altra domanda interattiva (multi-step)
  next_question: InteractiveQuestion | null
  answer: string | null
  suggested_actions: Action[] | null
```

### 4.3 Data Models

```python
# actions.py
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ActionCategory(str, Enum):
    CALCULATE = "calculate"
    SEARCH = "search"
    VERIFY = "verify"
    EXPORT = "export"
    EXPLAIN = "explain"

class Action(BaseModel):
    id: str
    label: str
    icon: str
    category: ActionCategory
    prompt_template: str
    requires_input: bool = False
    input_placeholder: Optional[str] = None
    input_type: str = "text"  # text | number | date

class InteractiveOption(BaseModel):
    id: str
    label: str
    icon: str
    leads_to: Optional[str] = None  # Flow ID for multi-step
    requires_input: bool = False

class InteractiveQuestion(BaseModel):
    id: str
    trigger_query: str
    text: str
    question_type: str  # single_choice | multi_choice | input_required
    options: List[InteractiveOption]
    allow_custom_input: bool = True
    custom_input_placeholder: Optional[str] = None
    prefilled_params: Optional[Dict[str, Any]] = None  # Parametri già estratti

class ExtractedParameter(BaseModel):
    name: str
    value: Any
    confidence: float  # 0.0 - 1.0
    source: str  # "pattern" | "keyword" | "context"

class ParameterExtractionResult(BaseModel):
    intent: str
    extracted: List[ExtractedParameter]
    missing_required: List[str]
    coverage: float  # 0.0 - 1.0
    can_proceed: bool  # coverage >= 1.0

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    suggested_actions: List[Action]
    interactive_question: Optional[InteractiveQuestion] = None
    extracted_params: Optional[Dict[str, Any]] = None  # Per conferma utente
```

### 4.4 Template Storage

```yaml
# config/intent_schemas.yaml
intents:
  calcolo_irpef:
    required: [tipo_contribuente, reddito]
    optional: [detrazioni, anno_fiscale, regione]
    defaults:
      anno_fiscale: 2025

  calcolo_iva:
    required: [importo]
    optional: [aliquota, tipo_operazione]
    defaults:
      aliquota: 22

  calcolo_contributi_inps:
    required: [tipo_gestione, reddito]
    optional: [anno, minimale]
    defaults:
      anno: 2025

  apertura_attivita:
    required: [tipo_attivita]
    optional: [settore, regime_fiscale, comune]
    defaults: {}

  verifica_scadenza:
    required: [tipo_adempimento]
    optional: [periodo, anno]
    defaults:
      anno: 2025

  ravvedimento_operoso:
    required: [importo_originale, data_scadenza]
    optional: [data_pagamento, tipo_tributo]
    defaults:
      data_pagamento: today

# config/extraction_patterns.yaml
patterns:
  tipo_contribuente:
    dipendente:
      - "dipendente"
      - "lavoratore dipendente"
      - "lavoratore subordinato"
      - "busta paga"
    autonomo:
      - "autonomo"
      - "p.iva"
      - "p. iva"
      - "partita iva"
      - "libero professionista"
      - "freelance"
    societa_persone:
      - "società di persone"
      - "sas"
      - "snc"
      - "ss"
    societa_capitali:
      - "società di capitali"
      - "srl"
      - "srls"
      - "spa"

  reddito:
    pattern: "(?:€|euro|eur)?\\s*(\\d{1,3}(?:[.,]\\d{3})*(?:[.,]\\d{2})?)\\s*(?:€|euro|eur)?"
    keywords: [reddito, imponibile, lordo, guadagno, fatturato, compensi]
    normalize: parse_italian_number

  importo:
    pattern: "(?:€|euro|eur)?\\s*(\\d{1,3}(?:[.,]\\d{3})*(?:[.,]\\d{2})?)\\s*(?:€|euro|eur)?"
    normalize: parse_italian_number

  aliquota:
    pattern: "(\\d{1,2})\\s*%|aliquota\\s+(\\d{1,2})|iva\\s+(?:al\\s+)?(\\d{1,2})"
    valid_values: [4, 5, 10, 22]

# config/action_templates.yaml
document_actions:
  fattura_elettronica:
    - id: verify_formal
      label: Verifica formale
      icon: "✅"
      category: verify
      prompt_template: "Verifica la correttezza formale di questa fattura"
      requires_input: false
    - id: calculate_vat
      label: Calcola IVA
      icon: "💰"
      category: calculate
      prompt_template: "Calcola l'IVA di questa fattura"
      requires_input: false
    # ... more actions

query_actions:
  fiscal_calculation:
    - id: recalculate
      label: Ricalcola
      icon: "🔄"
      category: calculate
      prompt_template: "Ricalcola {tax_type} con importo {amount}"
      requires_input: true
      input_placeholder: "Nuovo importo"
    # ... more actions

interactive_questions:
  irpef_calculation:
    text: "Per quale tipo di contribuente vuoi calcolare l'IRPEF?"
    question_type: single_choice
    options:
      - id: dipendente
        label: "Persona fisica (dipendente)"
        icon: "👔"
      - id: autonomo
        label: "Persona fisica (autonomo/P.IVA)"
        icon: "💼"
      # ... more options
```

---

## 5. UI/UX Specifications

### 5.1 Action Buttons Design

```
┌─────────────────────────────────────────────────────────────────┐
│  [Risposta del sistema qui...]                                  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  💡 Azioni suggerite:                                           │
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ 💰 Calcola  │ │ 📋 Normative│ │ 📝 Esempi   │ │ 📅 Scaden.│ │
│  │    IVA     │ │   correlate │ │   pratici   │ │           │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                 │
│  [Tab per navigare] [Enter per selezionare]                     │
└─────────────────────────────────────────────────────────────────┘
```

**Specifiche:**
- Bottoni con bordo arrotondato (8px radius)
- Colore: primary brand color (outline), hover → filled
- Icon size: 16px
- Font: 14px, medium weight
- Spacing: 8px tra bottoni
- Max 4 bottoni per riga (wrap su mobile)
- Focus ring visibile per accessibilità

### 5.2 Interactive Question Modal

```
┌─────────────────────────────────────────────────────────────────┐
│                                                    [✕ Chiudi]   │
│                                                                 │
│  📋 La tua domanda: "Calcola l'IRPEF"                          │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Per procedere, ho bisogno di sapere:                          │
│                                                                 │
│  Per quale tipo di contribuente?                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ○ 👔 Persona fisica (dipendente)                        │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ ● 💼 Persona fisica (autonomo/P.IVA)     ← Selezionato  │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ ○ 🏢 Società di persone                                 │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ ○ ✏️ Altro (specifica...)                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 💬 Aggiungi dettagli (opzionale): _____________________ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [↑↓ Naviga] [Enter Conferma] [Esc Annulla]                    │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │     ❌ Annulla      │  │    ✅ Conferma      │              │
│  └─────────────────────┘  └─────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

**Specifiche:**
- Modal centrato, max-width 500px
- Overlay semi-trasparente dietro
- Options come radio buttons stilizzati
- Selezione attiva: background highlight + border accent
- Keyboard shortcuts sempre visibili
- Chiusura con Esc o click fuori

### 5.3 Mobile Responsive

```
┌───────────────────────┐
│  📋 Tipo contribuente │
│  ───────────────────  │
│                       │
│  ┌─────────────────┐  │
│  │ 👔 Dipendente   │  │
│  └─────────────────┘  │
│  ┌─────────────────┐  │
│  │ 💼 Autonomo ✓   │  │
│  └─────────────────┘  │
│  ┌─────────────────┐  │
│  │ 🏢 Società      │  │
│  └─────────────────┘  │
│  ┌─────────────────┐  │
│  │ ✏️ Altro...     │  │
│  └─────────────────┘  │
│                       │
│  [    Conferma ✅   ] │
└───────────────────────┘
```

**Specifiche mobile:**
- Options full-width, stacked verticalmente
- Touch targets min 44px height
- Swipe to dismiss (optional)
- Bottom sheet style per question modal

---

## 6. Implementazione MVP

### 6.1 Fase 1: Backend Foundation (4-5 giorni)

**Tasks:**
1. Creare modelli dati per Action, InteractiveQuestion, ExtractedParameter
2. Implementare IntentClassifier (rule-based inizialmente)
3. Implementare ParameterExtractor con pattern italiani
4. Implementare ActionTemplateService (carica da YAML)
5. Creare DecisionRouter (coverage check → direct vs interactive)
6. Modificare ChatService per includere azioni nella risposta
7. Creare endpoint /api/actions/execute
8. Creare endpoint /api/questions/answer

**Deliverables:**
- [ ] Action, InteractiveQuestion, ExtractedParameter models
- [ ] Intent classification service
- [ ] Parameter extraction service con pattern italiani
- [ ] Decision router (coverage-based)
- [ ] Action template loader
- [ ] Modified chat endpoint
- [ ] New action/question endpoints
- [ ] Unit tests per ogni componente (focus su extraction accuracy)

### 6.2 Fase 2: Template Configuration (2 giorni)

**Tasks:**
1. Definire template azioni per tutti gli scenari documento
2. Definire template azioni per query fiscali comuni
3. Definire domande interattive per calcoli
4. Definire domande interattive per procedure
5. Testare matching template-scenario

**Deliverables:**
- [ ] action_templates.yaml completo
- [ ] interactive_questions.yaml completo
- [ ] Test coverage per ogni template

### 6.3 Fase 3: Frontend Components (3-4 giorni)

**Tasks:**
1. Creare ActionButtons component
2. Creare InteractiveQuestionModal component
3. Implementare keyboard navigation
4. Integrare in ChatInterface
5. Styling responsive
6. Accessibility testing

**Deliverables:**
- [ ] ActionButtons.tsx
- [ ] InteractiveQuestionModal.tsx
- [ ] useKeyboardNavigation hook
- [ ] Updated ChatInterface
- [ ] Mobile responsive styles
- [ ] ARIA labels e keyboard support

### 6.4 Fase 4: Integration & Testing (2-3 giorni)

**Tasks:**
1. Integration tests end-to-end
2. Performance testing (<500ms overhead)
3. User testing con scenari reali
4. Bug fixing
5. Documentation

**Deliverables:**
- [ ] Integration test suite
- [ ] Performance benchmarks
- [ ] User feedback collected
- [ ] Bug fixes deployed
- [ ] Technical documentation

---

## 7. Metriche di Successo

### 7.1 KPI Tecnici

| Metrica | Target | Misura |
|---------|--------|--------|
| Overhead proattività | ≤500ms | P95 latency difference |
| Accuracy intent classification | ≥80% | Manual review sample |
| Accuracy parameter extraction | ≥85% | Test set italiano |
| Action click-through rate | ≥30% | Actions clicked / shown |
| Direct response rate | ≥60% | Queries resolved without questions |

### 7.2 KPI Business

| Metrica | Target | Misura |
|---------|--------|--------|
| Interactions per session | +40% vs baseline | Analytics |
| Query reformulation rate | -50% | Follow-up clarifications |
| User satisfaction | ≥4.2/5 | In-app survey |
| Feature awareness | ≥80% users | Usage tracking |

### 7.3 KPI Costo

| Metrica | Target | Misura |
|---------|--------|--------|
| Token overhead per response | ≤200 tokens | Token counting |
| Cost per user daily | ≤€1.70 | Cost tracking |
| Cache hit rate | ≥75% | Cache analytics |

---

## 8. Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Azioni non pertinenti annoiano utente | Media | Alto | Fallback a LLM per ranking, feedback loop |
| Domande interattive rallentano workflow | Media | Medio | Threshold alto per attivazione, skip facile |
| Overhead latenza percepibile | Bassa | Alto | Calcolo parallelo, template pre-caricati |
| Complessità UI confonde utenti | Bassa | Medio | Design minimale, progressive disclosure |

---

## 9. Dipendenze

### 9.1 Prerequisiti Tecnici

- [x] Chat API funzionante
- [x] Document upload e classificazione
- [x] Sistema FAQ attivo
- [ ] Frontend React/Next.js setup (in progress)

### 9.2 Dipendenze Esterne

- Nessuna nuova dipendenza esterna richiesta
- Utilizza stack esistente (FastAPI, PostgreSQL, Redis)

---

## 10. Domande Aperte

| # | Domanda | Decisione Necessaria | Owner |
|---|---------|----------------------|-------|
| Q1 | LLM fallback per azioni: GPT-3.5 o GPT-4? | Costo vs qualità | Mick |
| Q2 | Max azioni da mostrare: 3 o 4? | UX test | Mick |
| Q3 | Domande interattive: modal o inline? | Mobile-first decision | Mick |
| Q4 | Tracciare azioni cliccate per analytics? | Privacy consideration | Mick |
| Q5 | Salvare preferenze utente (azioni preferite)? | Scope v1.5 vs v2.0 | Mick |

---

## 11. Appendice: Template Completi

### A.1 Template Azioni per Documenti

```yaml
# Vedere file separato: config/document_action_templates.yaml
fattura_elettronica:
  - id: verify_formal
    label: "Verifica correttezza"
    icon: "✅"
    prompt: "Verifica la correttezza formale della fattura"
  - id: calculate_vat
    label: "Calcola IVA"
    icon: "💰"
    prompt: "Calcola l'IVA della fattura"
  - id: check_recipient
    label: "Verifica destinatario"
    icon: "🔍"
    prompt: "Verifica Partita IVA e dati del destinatario"
  - id: accounting_entry
    label: "Registrazione contabile"
    icon: "📒"
    prompt: "Genera scrittura contabile per questa fattura"

f24:
  - id: verify_codes
    label: "Verifica codici"
    icon: "🔍"
    prompt: "Verifica correttezza codici tributo"
  - id: check_deadline
    label: "Controlla scadenza"
    icon: "📅"
    prompt: "Verifica scadenza di pagamento"
  - id: calculate_penalties
    label: "Calcola ravvedimento"
    icon: "⚠️"
    prompt: "Calcola sanzioni per ravvedimento operoso"
  - id: find_instructions
    label: "Istruzioni"
    icon: "📖"
    prompt: "Mostra istruzioni compilazione"

bilancio:
  - id: analyze_ratios
    label: "Analisi indici"
    icon: "📊"
    prompt: "Calcola principali indici di bilancio"
  - id: compare_year
    label: "Confronta anni"
    icon: "📈"
    prompt: "Confronta con esercizio precedente"
  - id: extract_summary
    label: "Riepilogo"
    icon: "📋"
    prompt: "Estrai dati principali in tabella"

cu:
  - id: verify_data
    label: "Verifica dati"
    icon: "✅"
    prompt: "Verifica coerenza dati CU"
  - id: irpef_simulation
    label: "Simula IRPEF"
    icon: "💰"
    prompt: "Simula dichiarazione redditi da CU"
  - id: extract_summary
    label: "Riepilogo"
    icon: "📋"
    prompt: "Estrai riepilogo compensi e ritenute"
```

### A.2 Template Domande Interattive

```yaml
# Vedere file separato: config/interactive_questions.yaml
irpef_calculation:
  text: "Per quale tipo di contribuente vuoi calcolare l'IRPEF?"
  options:
    - id: dipendente
      label: "Persona fisica (dipendente)"
      icon: "👔"
      next_question: irpef_income_input
    - id: autonomo
      label: "Persona fisica (autonomo/P.IVA)"
      icon: "💼"
      next_question: irpef_income_input
    - id: societa_persone
      label: "Società di persone"
      icon: "🏢"
      next_question: irpef_societa_params
    - id: altro
      label: "Altro (specifica)"
      icon: "✏️"
      requires_input: true

apertura_attivita:
  text: "Che tipo di attività vuoi aprire?"
  options:
    - id: artigiano
      label: "Artigiano"
      icon: "🔧"
      next_question: artigiano_settore
    - id: commerciante
      label: "Commerciante"
      icon: "🏪"
      next_question: commercio_tipo
    - id: professionista_albo
      label: "Professionista (con Albo)"
      icon: "💼"
      next_question: professione_ordine
    - id: professionista_no_albo
      label: "Professionista (senza Albo)"
      icon: "📊"
      next_question: regime_fiscale
    - id: societa
      label: "Società"
      icon: "🏭"
      next_question: tipo_societa

regime_fiscale:
  text: "Quale regime fiscale vuoi adottare?"
  options:
    - id: forfettario
      label: "Regime forfettario"
      icon: "📊"
      info: "Ricavi max €85.000, tassazione 15% (5% primi 5 anni)"
    - id: ordinario
      label: "Regime ordinario"
      icon: "📈"
      info: "Nessun limite ricavi, IRPEF a scaglioni"
    - id: non_so
      label: "Non so / Aiutami a scegliere"
      icon: "❓"
```

---

## 12. Revisione SuggestedActions e InteractiveQuestion

### 12.1 Problema Identificato Post-Implementazione

L'architettura originale basata su template si è rivelata impraticabile in produzione:

| Problema | Impatto |
|----------|---------|
| Template matching fragile | Query non riconosciute → nessuna azione suggerita |
| Manutenzione infinita | Impossibile pre-definire tutte le domande possibili |
| Confusione quando usare cosa | SuggestedActions vs InteractiveQuestion non chiaro |
| Conflitto con FAQ/Knowledge Base | Sistema cerca di matchare template invece di usare conoscenza |

**Root Cause:** L'architettura assume Query → Match Template → Actions, ma questo richiede anticipare tutte le possibili domande.

### 12.2 Nuova Architettura: LLM-First

La soluzione è far generare le azioni suggerite direttamente dall'LLM come parte della risposta:

```
┌─────────────────────────────────────────────────────────────────┐
│                      NUOVO FLUSSO                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Query                                                     │
│       ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ STEP 1: È UN CALCOLO NOTO?                              │   │
│  │                                                         │   │
│  │ Intent in [IRPEF, IVA, Contributi, Ravvedimento, F24]? │   │
│  │                                                         │   │
│  │ → SÌ + Parametri mancanti: InteractiveQuestion         │   │
│  │ → SÌ + Parametri completi: Vai a Step 3                │   │
│  │ → NO: Vai a Step 2                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ STEP 2: C'È UN DOCUMENTO?                               │   │
│  │                                                         │   │
│  │ Documento riconosciuto (Fattura, F24, Bilancio, CU)?   │   │
│  │                                                         │   │
│  │ → SÌ: Usa template azioni per quel documento           │   │
│  │ → NO: LLM genererà azioni                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ STEP 3: LLM GENERA RISPOSTA + AZIONI                    │   │
│  │                                                         │   │
│  │ Prompt speciale che chiede:                             │   │
│  │ - Risposta alla domanda                                 │   │
│  │ - 2-4 azioni suggerite contestuali                      │   │
│  │                                                         │   │
│  │ Output strutturato: { answer, citations, actions }      │   │
│  └─────────────────────────────────────────────────────────┘   │
│       ↓                                                         │
│  Response con SuggestedActions (da template O da LLM)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 12.3 Regola Chiave: Quando Usare Cosa

| Situazione | Componente | Fonte Dati |
|------------|------------|------------|
| Calcolo senza parametri essenziali | InteractiveQuestion | Template (lista finita) |
| Documento caricato e riconosciuto | SuggestedActions | Template per tipo doc |
| Qualsiasi altra risposta | SuggestedActions | LLM genera dinamicamente |

### 12.4 InteractiveQuestion: Solo Per Calcoli Noti

Le InteractiveQuestion sono riservate esclusivamente a casi dove:

1. L'utente chiede un calcolo specifico
2. Mancano parametri numerici essenziali senza i quali il calcolo è impossibile

Lista esaustiva degli intent che usano InteractiveQuestion:

```python
CALCULABLE_INTENTS = {
    "calcolo_irpef": {
        "required": ["tipo_contribuente", "reddito"],
        "question_flow": "irpef_flow"
    },
    "calcolo_iva": {
        "required": ["importo"],
        "question_flow": "iva_flow"
    },
    "calcolo_contributi_inps": {
        "required": ["tipo_gestione", "reddito"],
        "question_flow": "contributi_flow"
    },
    "ravvedimento_operoso": {
        "required": ["importo_originale", "data_scadenza"],
        "question_flow": "ravvedimento_flow"
    },
    "calcolo_f24": {
        "required": ["codice_tributo", "importo"],
        "question_flow": "f24_flow"
    }
}

# REGOLA:
# SE intent IN CALCULABLE_INTENTS AND parametri_mancanti:
#     return InteractiveQuestion
# ALTRIMENTI:
#     return Risposta + SuggestedActions (da LLM)
```

Tutto il resto (domande normative, informazioni, procedure, consulenze) NON usa InteractiveQuestion.

### 12.5 SuggestedActions: LLM-Generated

Per tutte le risposte che non sono calcoli con parametri mancanti, l'LLM genera le azioni suggerite.

#### 12.5.1 System Prompt Aggiornato

```python
SYSTEM_PROMPT_WITH_PROACTIVE_ACTIONS = """
Sei PratikoAI, assistente AI per professionisti italiani: commercialisti,
consulenti del lavoro e avvocati tributaristi.

Rispondi alla domanda dell'utente in modo preciso, professionale e con
riferimenti normativi quando appropriato.

## IMPORTANTE: Azioni Suggerite

Dopo OGNI risposta, devi suggerire 2-4 azioni che il professionista potrebbe
voler fare come passo successivo. Le azioni devono essere:

1. **Pertinenti** - Direttamente collegate alla domanda appena risposta
2. **Professionali** - Utili nel contesto dello studio professionale
3. **Azionabili** - Eseguibili con un click (non vaghe)
4. **Diverse** - Non ripetere concetti simili

## Formato Output

Rispondi SEMPRE con questo formato:

<answer>
[La tua risposta completa qui, con citazioni se necessarie]
</answer>

<suggested_actions>
[
  {"id": "1", "label": "Etichetta breve (max 3 parole)", "icon": "💰", "prompt": "Il prompt completo che verrà eseguito se l'utente clicca"},
  {"id": "2", "label": "Altra azione", "icon": "📋", "prompt": "Altro prompt completo"},
  {"id": "3", "label": "Terza azione", "icon": "🔍", "prompt": "Terzo prompt"}
]
</suggested_actions>

## Esempi di Azioni per Tipo di Risposta

**Dopo risposta su calcolo fiscale:**
- "Ricalcola importo" → Ricalcola con parametri diversi
- "Aggiungi INPS" → Calcola anche i contributi previdenziali
- "Confronta regimi" → Confronta con regime forfettario/ordinario
- "Calcola acconti" → Calcola gli acconti per l'anno successivo

**Dopo risposta su normativa/circolare:**
- "Approfondisci" → Spiega in maggior dettaglio questa normativa
- "Esempi pratici" → Mostra esempi pratici di applicazione
- "Circolari correlate" → Trova altre circolari sullo stesso tema
- "Impatto clienti" → Come impatta questa novità sui clienti tipo

**Dopo risposta su procedura:**
- "Checklist completa" → Genera una checklist dettagliata
- "Modelli necessari" → Elenca i modelli da compilare
- "Timeline" → Mostra la sequenza temporale degli adempimenti
- "Costi e tributi" → Elenca i costi e i tributi previsti

**Dopo analisi documento:**
- "Verifica altro" → Verifica un altro aspetto del documento
- "Genera registrazione" → Genera la scrittura contabile
- "Calcola imposte" → Calcola le imposte relative
- "Trova errori" → Cerca possibili errori o anomalie

## Icone Consigliate
- 💰 Calcoli, importi, costi
- 📋 Documenti, liste, procedure
- 🔍 Ricerca, verifica, approfondimento
- 📊 Analisi, confronti, statistiche
- 📅 Scadenze, timeline, date
- ⚠️ Avvertenze, sanzioni, rischi
- ✅ Verifiche, controlli
- 📝 Generazione testi, modelli
- 🔄 Ricalcoli, aggiornamenti
- 📖 Normativa, leggi, circolari
"""
```

#### 12.5.2 Parsing della Risposta

```python
import re
import json
from typing import List, Optional
from pydantic import BaseModel

class SuggestedAction(BaseModel):
    id: str
    label: str
    icon: str
    prompt: str

class ParsedResponse(BaseModel):
    answer: str
    suggested_actions: List[SuggestedAction]

def parse_llm_response(raw_response: str) -> ParsedResponse:
    """Parse LLM response with answer and suggested actions."""

    # Extract answer
    answer_match = re.search(r'<answer>(.*?)</answer>', raw_response, re.DOTALL)
    answer = answer_match.group(1).strip() if answer_match else raw_response

    # Extract actions
    actions_match = re.search(r'<suggested_actions>\s*(\[.*?\])\s*</suggested_actions>',
                              raw_response, re.DOTALL)

    suggested_actions = []
    if actions_match:
        try:
            actions_json = json.loads(actions_match.group(1))
            suggested_actions = [SuggestedAction(**a) for a in actions_json[:4]]
        except (json.JSONDecodeError, ValueError):
            # Fallback: no actions if parsing fails
            pass

    return ParsedResponse(answer=answer, suggested_actions=suggested_actions)
```

### 12.6 Template Actions: Solo Per Documenti

I template di azioni rimangono solo per i documenti riconosciuti, perché sono scenari prevedibili:

```python
DOCUMENT_ACTION_TEMPLATES = {
    "fattura_elettronica": [
        {"id": "verify", "label": "Verifica formale", "icon": "✅",
         "prompt": "Verifica la correttezza formale di questa fattura elettronica"},
        {"id": "vat", "label": "Calcola IVA", "icon": "💰",
         "prompt": "Calcola l'IVA di questa fattura"},
        {"id": "entry", "label": "Registrazione", "icon": "📒",
         "prompt": "Genera la scrittura contabile per questa fattura"},
        {"id": "recipient", "label": "Verifica P.IVA", "icon": "🔍",
         "prompt": "Verifica la Partita IVA del destinatario"}
    ],
    "f24": [
        {"id": "codes", "label": "Verifica codici", "icon": "🔍",
         "prompt": "Verifica la correttezza dei codici tributo"},
        {"id": "deadline", "label": "Scadenza", "icon": "📅",
         "prompt": "Verifica la scadenza di pagamento"},
        {"id": "ravvedimento", "label": "Ravvedimento", "icon": "⚠️",
         "prompt": "Calcola ravvedimento operoso se in ritardo"}
    ],
    "bilancio": [
        {"id": "ratios", "label": "Indici", "icon": "📊",
         "prompt": "Calcola i principali indici di bilancio"},
        {"id": "compare", "label": "Confronta", "icon": "📈",
         "prompt": "Confronta con l'esercizio precedente"},
        {"id": "summary", "label": "Riepilogo", "icon": "📋",
         "prompt": "Estrai i dati principali in formato tabellare"}
    ],
    "cu": [
        {"id": "verify", "label": "Verifica", "icon": "✅",
         "prompt": "Verifica la coerenza dei dati della CU"},
        {"id": "irpef", "label": "Simula IRPEF", "icon": "💰",
         "prompt": "Simula la dichiarazione redditi da questa CU"},
        {"id": "summary", "label": "Riepilogo", "icon": "📋",
         "prompt": "Estrai riepilogo compensi e ritenute"}
    ]
}
```

### 12.7 Logica Decisionale Completa

```python
async def process_query_with_proactivity(
    query: str,
    document: Optional[Document] = None,
    session_context: Optional[dict] = None
) -> ChatResponse:
    """
    Main entry point for query processing with proactive suggestions.
    """

    # ─────────────────────────────────────────────────────────────
    # STEP 1: Check if it's a known calculation with missing params
    # ─────────────────────────────────────────────────────────────
    intent = classify_intent(query)

    if intent in CALCULABLE_INTENTS:
        extracted_params = extract_parameters(query, intent)
        required = CALCULABLE_INTENTS[intent]["required"]
        missing = [p for p in required if p not in extracted_params]

        if missing:
            # Return InteractiveQuestion for missing parameters
            return ChatResponse(
                type="interactive_question",
                interactive_question=build_question_for_missing(
                    intent=intent,
                    missing_params=missing,
                    extracted_params=extracted_params
                )
            )

    # ─────────────────────────────────────────────────────────────
    # STEP 2: Check if there's a recognized document
    # ─────────────────────────────────────────────────────────────
    template_actions = None
    doc_context = None

    if document:
        doc_type = classify_document(document)
        doc_context = extract_document_context(document)

        if doc_type in DOCUMENT_ACTION_TEMPLATES:
            template_actions = DOCUMENT_ACTION_TEMPLATES[doc_type]

    # ─────────────────────────────────────────────────────────────
    # STEP 3: Call LLM with proactive actions prompt
    # ─────────────────────────────────────────────────────────────
    llm_response = await call_llm(
        query=query,
        system_prompt=SYSTEM_PROMPT_WITH_PROACTIVE_ACTIONS,
        doc_context=doc_context,
        session_context=session_context
    )

    # Parse response
    parsed = parse_llm_response(llm_response)

    # ─────────────────────────────────────────────────────────────
    # STEP 4: Determine final actions (template priority if available)
    # ─────────────────────────────────────────────────────────────
    final_actions = template_actions if template_actions else parsed.suggested_actions

    return ChatResponse(
        type="response",
        answer=parsed.answer,
        citations=extract_citations(parsed.answer),
        suggested_actions=final_actions[:4]  # Max 4 actions
    )
```

### 12.8 Costo Incrementale

| Componente | Token Aggiuntivi | Costo Extra |
|------------|------------------|-------------|
| System prompt esteso | ~400 tokens (one-time) | ~€0.0004 |
| Actions in output | ~80-120 tokens | ~€0.0001 |
| **Totale per query** | ~100 tokens netti | ~€0.0001 |

**Impatto su costo giornaliero:** Da €1.45 a ~€1.47 per utente → trascurabile

### 12.9 Vantaggi della Nuova Architettura

| Aspetto | Prima (Template-Heavy) | Dopo (LLM-First) |
|---------|------------------------|------------------|
| Copertura | Solo query pre-mappate | Tutte le query |
| Manutenzione | Aggiungere template continuamente | Zero manutenzione |
| Qualità azioni | Fisse, spesso non pertinenti | Contestuali, intelligenti |
| Complessità codice | Alta (matching, routing) | Bassa (parsing output) |
| Template da mantenere | ~50+ scenari | ~6 (solo documenti + calcoli) |

### 12.10 Criteri di Accettazione Rivisti

- [ ] AC-REV.1: InteractiveQuestion appare SOLO per calcoli in CALCULABLE_INTENTS con parametri mancanti
- [ ] AC-REV.2: SuggestedActions appare su OGNI risposta (da template documento O da LLM)
- [ ] AC-REV.3: LLM genera 2-4 azioni pertinenti nel 90%+ delle risposte
- [ ] AC-REV.4: Parsing actions fallisce gracefully (nessuna azione se errore)
- [ ] AC-REV.5: Template documenti hanno priorità su azioni LLM quando documento presente
- [ ] AC-REV.6: Costo incrementale ≤€0.02/utente/giorno

### 12.11 Piano di Migrazione

**Fase 1: Backend (1-2 giorni)**
1. Aggiornare system prompt con formato azioni
2. Implementare parse_llm_response()
3. Semplificare logica decisionale
4. Rimuovere template matching complesso

**Fase 2: Cleanup (1 giorno)**
1. Rimuovere template non necessari
2. Mantenere solo CALCULABLE_INTENTS e DOCUMENT_ACTION_TEMPLATES
3. Aggiornare tests

**Fase 3: Validazione (1 giorno)**
1. Test end-to-end con query reali
2. Verificare qualità azioni generate
3. Monitorare costi

---

**Fine Documento**

*Versione: 1.5-MVP*
*Prossima review: Fine implementazione Fase 1*
