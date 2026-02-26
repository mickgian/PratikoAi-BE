# PratikoAI 2.0 - Original Requirements Reference

**Document Type:** Product Requirements Document (PRD)
**Version:** 1.1
**Last Updated:** 2026-02-26

> This document contains the original requirements and specifications for PratikoAI 2.0.
> For the implementation task breakdown, see [PRATIKO_2.0.md](./PRATIKO_2.0.md).

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Context and Constraints](#2-context-and-constraints)
3. [Functional Requirements](#3-functional-requirements)
   - [FR-001: Procedure Interattive](#fr-001-procedure-interattive)
   - [FR-002: Studio Client Database](#fr-002-database-clienti-dello-studio)
   - [FR-003: Automatic Normative Matching](#fr-003-matching-normativo-automatico)
   - [FR-004: Proactive Suggestions & Communications](#fr-004-suggerimenti-proattivi-e-generazione-comunicazioni)
   - [FR-005: ROI Dashboard & Analytics](#fr-005-dashboard-roi-e-analytics)
   - [FR-006: Proactive Deadline System](#fr-006-sistema-scadenze-proattivo)
   - [FR-007: Tax Calculations](#fr-007-calcoli-fiscali)
   - [FR-008: Document Upload & Analysis](#fr-008-upload-e-analisi-documenti)
   - [FR-009: Hybrid Email Sending](#fr-009-configurazione-email-ibrida-hybrid-email-sending)
4. [Non-Functional Requirements](#4-requisiti-non-funzionali)
5. [Architecture Proposal](#5-architettura-proposta)
6. [MVP Definition](#6-definizione-mvp)
7. [Open Questions](#7-domande-aperte)
8. [Risks & Mitigations](#8-rischi-e-mitigazioni)
9. [Glossary](#9-glossario)
10. [GDPR & Data Management](#11-gdpr-e-gestione-dati-clienti)

---

## 1. Executive Summary

### 1.1 Visione del Prodotto

Voglio fare dei cambiamenti per far evolvere PratikoAI da assistente per commercialisti, consulenti del lavoro e avvocati a piattaforma di engagement professionale che:

* Fornisce informazioni normative sempre aggiornate con fonti autorevoli
* Guida il professionista attraverso procedure complesse con checklist interattive e tracciamento del progresso
* Identifica automaticamente quali clienti sono impattati da nuove normative
* Genera comunicazioni personalizzate per acquisire nuovo lavoro

### 1.2 Value Proposition

| Per il Professionista | Beneficio Quantificabile |
|-----------------------|--------------------------|
| Risparmio tempo ricerca | -3h/settimana |
| Matching automatico clienti-normative | +15% pratiche/mese |
| Comunicazioni proattive | +20% retention clienti |
| Preparazione appuntamenti | -30min/appuntamento |

### 1.3 Target Users

**Utenti Primari:**

| Ruolo | Focus Principale | % Mercato Target |
|-------|------------------|------------------|
| Commercialista | Fiscale, bilanci, contabilità | 50% |
| Consulente del Lavoro | Buste paga, INPS, pensioni, assunzioni | 35% |
| Avvocato Tributarista | Contenzioso, ricorsi, consulenza | 15% |

**Utenti Secondari:**
* Collaboratore di studio (accesso limitato, sola consultazione)
* Amministratore studio (gestione database clienti, configurazioni)

---

## 2. Context and Constraints

### 2.1 Stato Attuale PratikoAI (v1.0)

**Funzionalità già implementate:**
* ✅ Chat AI con risposte contestualizzate
* ✅ 16 RSS feeds + 2 website scraping (source of truth: database)
* ✅ Sistema FAQ intelligente con auto-apprendimento
* ✅ Citazioni e riferimenti normativi

**Funzionalità da implementare:**
* ❌ Calcoli fiscali (IRPEF, IVA, ritenute, contributi) (da verificare se funzionalità sia effettivamente non implementata)
* ❌ Upload e analisi documenti (fatture, F24, bilanci) (upload funziona ma analisi dei documenti specifici è da verificare)
* ❌ Variazioni fiscali regionali (IMU, IRAP, addizionali) (da verificare se funzionalità implementata)
* ❌ Camere di Commercio (no RSS, da aggiungere se possibile, altrimenti scraping)

**Metriche attuali:**
* Costo per utente: €1.45/giorno
* Qualità risposte: 91%
* Tempo risposta P95: 2.1s

### 2.2 Vincoli Tecnici

| Vincolo | Valore | Motivazione |
|---------|--------|-------------|
| Hosting | EU (Hetzner Germany) | GDPR compliance |
| Costo target per utente | ≤ €2/mese | Sostenibilità economica |
| Response time | ≤ 3 secondi | UX professionale |
| Uptime | 99.9% | Affidabilità business-critical |

### 2.3 Vincoli di Business

* **Pricing:** €69/mese (fisso, già definito)
* **Competitor:** NormoAI (€99/mese) - differenziazione su engagement clienti
* **Timeline MVP:** 12 settimane
* **Risorse:** 1 sviluppatore umano (2-3h/giorno) + Claude code

---

## 3. Functional Requirements

### FR-001: Procedure Interattive

#### 3.1.1 Descrizione

Sistema di procedure passo-passo che accompagna il professionista attraverso procedure amministrative complesse, fornendo checklist, modelli, timeline e riferimenti normativi. Le procedure possono essere consultate come riferimento generico (via comando `/procedura` in chat) oppure avviate per un cliente specifico con tracciamento del progresso (via menzione `@NomeCliente`).

#### 3.1.2 User Stories

**US-001.1:** Come commercialista, voglio cercare "apertura attività artigiano" e ricevere una procedura completa con tutti i passaggi, così da preparare l'appuntamento con il cliente.

**US-001.2:** Come consulente del lavoro, voglio inserire i dati di un cliente che vuole andare in pensione e ricevere indicazioni su quale legge si applica, quali modelli compilare e quando presentare domanda.

**US-001.3:** Come professionista, voglio poter stampare/esportare la procedura in PDF per condividerla con il cliente o archiviarla.

**US-001.4:** Come professionista, voglio digitare `/procedura` in chat per consultare rapidamente una procedura come riferimento generico, senza creare un tracciamento del progresso.

**US-001.5:** Come professionista, voglio avviare una procedura per un cliente specifico (es: `@Mario Rossi`) con tracciamento completo del progresso, checklist e note.

**US-001.6:** Come professionista, quando digito `@` in chat, voglio vedere un elenco autocomplete dei miei clienti per selezionarne uno rapidamente.

**US-001.7:** Come professionista, dopo aver selezionato un cliente con `@NomeCliente`, voglio scegliere l'azione da compiere: fare una domanda generica con contesto cliente, fare una domanda specifica sul cliente, visualizzare la scheda completa del cliente, oppure avviare una procedura guidata per quel cliente.

**US-001.8:** Come professionista, quando scelgo "Scheda cliente" dopo una menzione `@`, voglio vedere un riepilogo completo: anagrafica, regime fiscale, ATECO, posizione contributiva e procedure attive, così da avere il quadro completo prima di operare.

#### 3.1.3 Struttura Output Procedure

```yaml
Procedura:
  titolo: "Apertura Attività Artigiano - Settore Edilizia"
  ultimo_aggiornamento: "2025-12-01"
  tipo: "GENERIC"  # oppure "CLIENT_SPECIFIC"

  sezione_1_checklist_documenti:
    titolo: "Documentazione da Richiedere al Cliente"
    items:
      - documento: "Documento identità valido"
        obbligatorio: true
        note: "Carta identità o passaporto"
      - documento: "Codice fiscale"
        obbligatorio: true
      - documento: "Titolo di studio o attestato qualifica professionale"
        obbligatorio: true
        note: "Per iscrizione Albo Artigiani"
      - documento: "Certificato casellario giudiziale"
        obbligatorio: false
        note: "Richiesto per alcune attività regolamentate"
      - documento: "Contratto di locazione o proprietà sede"
        obbligatorio: true

  sezione_2_modelli:
    titolo: "Modelli da Compilare"
    items:
      - modello: "Modello AA9/12"
        ente: "Agenzia delle Entrate"
        scopo: "Apertura Partita IVA"
        link: "https://www.agenziaentrate.gov.it/..."
        istruzioni: "Compilare sezione A e B..."
      - modello: "ComUnica"
        ente: "Camera di Commercio"
        scopo: "Iscrizione REA + INPS + INAIL"
        link: "https://www.registroimprese.it/..."

  sezione_3_timeline:
    titolo: "Timeline Procedurale"
    steps:
      - giorno: 0
        azione: "Invio Modello AA9/12 all'Agenzia delle Entrate"
        modalita: "Telematico via Entratel/Fisconline"
      - giorno: 0-30
        azione: "Iscrizione INPS Gestione Artigiani"
        note: "Automatica tramite ComUnica"
      - giorno: 0-30
        azione: "Iscrizione INAIL (se prevista)"
        note: "Obbligatoria per attività con rischio"
      - giorno: 0-30
        azione: "Iscrizione Albo Artigiani presso Camera di Commercio"

  sezione_4_costi:
    titolo: "Costi e Tributi"
    items:
      - voce: "Diritti di segreteria CCIAA"
        importo: 18.00
        frequenza: "una tantum"
      - voce: "Diritto annuale CCIAA"
        importo: 120.00
        frequenza: "annuale"
      - voce: "Bollo ComUnica"
        importo: 17.50
        frequenza: "una tantum"

  sezione_5_riferimenti:
    titolo: "Riferimenti Normativi"
    items:
      - norma: "L. 443/1985"
        descrizione: "Legge quadro artigianato"
      - norma: "D.Lgs. 112/1998"
        descrizione: "Conferimento funzioni alle Regioni"
      - norma: "Circolare INPS 52/2024"
        descrizione: "Contributi artigiani 2024"

  sezione_6_note:
    titolo: "Note e Avvertenze"
    items:
      - "Verificare eventuali requisiti regionali aggiuntivi"
      - "Per attività edili: verificare obbligo DURC"
```

#### 3.1.4 Procedure da Implementare (Priorità Alta)

| ID | Procedura | Enti Coinvolti | Complessità |
|----|-----------|----------------|-------------|
| P001 | Apertura attività artigiano | AdE, CCIAA, INPS, INAIL, ISTAT | Alta |
| P002 | Apertura attività commerciale | AdE, CCIAA, INPS, Comune (SCIA) | Alta |
| P003 | Apertura studio professionale | AdE, Ordine, INPS gestione separata | Media |
| P004 | Domanda pensione vecchiaia | INPS | Media |
| P005 | Domanda pensione anticipata | INPS | Media |
| P006 | Assunzione dipendente | INPS, INAIL, Centro Impiego | Alta |
| P007 | Trasformazione regime fiscale | AdE | Bassa |
| P008 | Chiusura attività | AdE, CCIAA, INPS, INAIL | Alta |
| P009 | Variazione dati azienda | AdE, CCIAA | Bassa |
| P010 | Iscrizione gestione separata INPS | INPS | Bassa |

#### 3.1.5 Criteri di Accettazione

* **AC-001.1:** Ricerca "apertura attività + settore" restituisce procedura completa in <3s
* **AC-001.2:** Ogni procedura include almeno: checklist, modelli, timeline, costi, riferimenti
* **AC-001.3:** Link ai modelli ufficiali sono verificati e funzionanti
* **AC-001.4:** Export PDF mantiene formattazione professionale
* **AC-001.5:** Procedure aggiornate automaticamente quando RSS rileva modifiche normative
* **AC-001.6:** Indicazione chiara della data ultimo aggiornamento
* **AC-001.7:** Comando `/procedura` in chat apre selezione procedure in modalità consultazione (read-only)
* **AC-001.8:** Consultazione generica NON crea record di progresso (ProceduraProgress)
* **AC-001.9:** Avvio procedura per cliente specifico (`@NomeCliente`) crea ProceduraProgress con tracciamento completo
* **AC-001.10:** Digitazione `@` in chat mostra autocomplete clienti con debounce 300ms
* **AC-001.11:** Menzione `@NomeCliente` inietta contesto cliente e procedure attive/pertinenti in RAGState

#### 3.1.6 Fonti Dati

| Fonte | Tipo | Già Integrata | Azione |
|-------|------|---------------|--------|
| Agenzia Entrate | RSS | ✅ Sì | Estendere per modelli |
| INPS | RSS | ✅ Sì | Implementare scraper circolari |
| INAIL | RSS | ✅ Sì | Implementare |
| MEF | RSS | ✅ Sì | Implementare |
| Gazzetta Ufficiale | Scraping/API | ✅ Sì | Implementare |
| Camere di Commercio | RSS or Scraping | ❌ No | Implementare |
| ISTAT (codici ATECO) | API/Statico | ❌ No | Implementare |
| Ordini Professionali | Statico | ❌ No | Database manuale |

---

### FR-002: Database Clienti dello Studio

#### 3.2.1 Descrizione

Sistema di gestione anagrafica clienti che permette al professionista di caricare e mantenere un database dei propri clienti/prospect, con attributi strutturati per il matching normativo automatico.

#### 3.2.2 User Stories

**US-002.1:** Come professionista, voglio caricare un file Excel con l'elenco dei miei clienti, così da iniziare subito a usare il matching automatico.

**US-002.2:** Come professionista, voglio aggiungere manualmente un nuovo cliente con i suoi dati fiscali, così da includerlo nelle comunicazioni future.

**US-002.3:** Come professionista, voglio poter taggare i clienti con etichette personalizzate (es: "interessato a Resto al Sud"), così da segmentarli per comunicazioni mirate.

**US-002.4:** Come amministratore studio, voglio gestire chi può vedere/modificare i dati clienti, così da proteggere informazioni sensibili.

#### 3.2.3 Schema Dati Cliente

```yaml
Cliente:
  # Identificazione
  id: UUID
  studio_id: UUID  # Appartenenza allo studio
  codice_interno: string  # Codice cliente nel gestionale

  # Anagrafica Base
  tipo_soggetto: enum [persona_fisica, ditta_individuale, societa_persone, societa_capitali, ente_no_profit, pubblica_amministrazione]
  denominazione: string  # Nome o ragione sociale
  codice_fiscale: string (encrypted)
  partita_iva: string (encrypted, nullable)

  # Dati Geografici
  indirizzo: string
  cap: string
  comune: string
  provincia: string (2 char)
  regione: string

  # Dati Fiscali
  regime_fiscale: enum [ordinario, semplificato, forfettario, agricolo, minimi]
  codice_ateco_principale: string  # Es: "41.20.00"
  codici_ateco_secondari: array[string]
  data_inizio_attivita: date
  data_cessazione_attivita: date (nullable)

  # Dati Lavoro (per Consulenti del Lavoro)
  numero_dipendenti: integer
  ccnl_applicato: string  # Es: "Commercio", "Metalmeccanico"
  ha_apprendisti: boolean
  ha_lavoratori_stagionali: boolean

  # Dati Personali (per matching età-based)
  data_nascita_titolare: date
  eta_titolare: computed integer
  soci: array[{nome, cf, data_nascita, quota_percentuale}]

  # Posizioni Fiscali
  posizione_agenzia_entrate: enum [regolare, con_debiti, con_rateizzazione, contenzioso]
  ha_cartelle_esattoriali: boolean
  importo_debiti_fiscali: decimal (encrypted)

  posizione_inps: enum [regolare, con_debiti, non_iscritto]
  posizione_inail: enum [regolare, con_debiti, non_iscritto, esente]

  # Immobili (per IMU, cedolare secca, etc.)
  immobili: array[{tipo, comune, rendita_catastale, uso}]

  # Classificazione
  stato_cliente: enum [attivo, prospect, cessato, sospeso]
  data_acquisizione: date
  referente_studio: string  # Chi segue il cliente

  # Tag Personalizzati
  tags: array[string]  # Es: ["interessato bonus sud", "export", "e-commerce"]

  # Consensi GDPR
  consenso_marketing: boolean
  consenso_profilazione: boolean
  data_ultimo_consenso: timestamp

  # Metadata
  created_at: timestamp
  updated_at: timestamp
  created_by: UUID
  note: text
```

#### 3.2.4 Import/Export

**Formati Supportati (MVP):**
* Excel (.xlsx) con template predefinito
* CSV con header standardizzato

**Template Excel Minimo:**

| Campo | Obbligatorio | Formato |
|-------|--------------|---------|
| denominazione | Sì | Testo |
| codice_fiscale | Sì | 16 caratteri |
| partita_iva | No | 11 caratteri |
| tipo_soggetto | Sì | Da lista valori |
| codice_ateco | No | XX.XX.XX |
| regime_fiscale | Sì | Da lista valori |
| numero_dipendenti | No | Numero |
| email | No | Email valida |
| telefono | No | Testo |
| cap | Sì | 5 cifre |

**Validazioni Import:**
* Codice fiscale: validazione algoritmica
* Partita IVA: validazione check digit
* CAP: lookup su database comuni
* Codice ATECO: validazione su tabella ISTAT

#### 3.2.5 Integrazioni Future (Post-MVP)

| Gestionale | Priorità | Complessità | Note |
|------------|----------|-------------|------|
| TeamSystem | Alta | Alta | 40% mercato, API disponibili |
| Zucchetti | Alta | Alta | Molto diffuso |
| Wolters Kluwer | Media | Media | IPSOA |
| Buffetti | Bassa | Media | Target piccoli studi |
| Sistemi | Bassa | Media | Settore paghe |

#### 3.2.6 Criteri di Accettazione

* **AC-002.1:** Import Excel di 1000 clienti completo in <30 secondi
* **AC-002.2:** Validazione codice fiscale con feedback errore specifico
* **AC-002.3:** Ricerca cliente per nome/CF/P.IVA in <1 secondo
* **AC-002.4:** Campi sensibili (CF, P.IVA, importi) crittografati at rest
* **AC-002.5:** Log audit per ogni modifica dati cliente
* **AC-002.6:** Export completo database in formato Excel

---

### FR-003: Matching Normativo Automatico

#### 3.3.1 Descrizione

Sistema invisibile all'utente che analizza automaticamente il database clienti per identificare chi potrebbe essere interessato da una normativa. Il matching viene eseguito in modo **asincrono** (dopo la consegna della risposta normativa o dopo l'ingestione RSS) e i risultati vengono consegnati tramite il **sistema di notifiche** (bell icon dropdown), mai inline nella risposta chat (vedi ADR-035).

#### 3.3.2 User Stories

**US-003.1:** Come professionista, NON devo fare nulla di speciale: quando cerco informazioni su una normativa, PratikoAI mi dice automaticamente se e quanti clienti potrebbero essere interessati.

**US-003.2:** Come professionista, voglio poter cliccare su "Mostra lista clienti" per vedere chi sono i clienti matchati prima di decidere se preparare una comunicazione.

**US-003.3:** Come professionista, voglio che il matching sia intelligente e consideri la situazione specifica di ogni cliente (regime fiscale, debiti, settore, etc.).

#### 3.3.3 Architettura Matching (Backend)

> **Decisione architetturale (ADR-035, 2026-02-26):** Il matching NON avviene in modo sincrono
> all'interno della pipeline RAG. Avviene in modo **asincrono** dopo la consegna della risposta
> normativa. I risultati vengono consegnati tramite **notifiche**, mai inline nella chat.
> Questo evita: (1) inquinamento del contesto RAG con dati CRM, (2) responsabilità miste nel
> singolo LLM call, (3) accoppiamento sincrono che aggiunge latenza e rischio di failure.

**Panoramica:**
Il Matching Engine opera in modo **asincrono** tramite background job, attivato da due trigger: (1) dopo la consegna di una risposta normativa nella chat, (2) dopo l'ingestione di nuove normative via RSS/KB. I risultati vengono consegnati tramite il sistema di notifiche.

**Flusso del Processo:**

1. **Input: Query Utente**
   L'utente inserisce una domanda (es: "Spiegami la rottamazione quinquies")

2. **Risposta Normativa (pipeline RAG invariata)**
   Il LLM Response Generator elabora la query e genera la risposta normativa completa.
   La pipeline RAG NON viene modificata — nessun nodo di matching inserito.

3. **Matching Asincrono (background job, dopo la risposta)**
   Dopo la consegna della risposta, un background job asincrono:
   * Normativa Classifier: Analizza il topic della query per identificare l'argomento normativo
   * Rule Matcher: Consulta il Rules Database per trovare regole di matching applicabili
   * Client Counter: Interroga il Database Clienti dello studio per contare quanti clienti soddisfano le condizioni

4. **Notifica (se clienti matchati > 0)**
   Se il Client Counter trova clienti matchati:
   * Crea record `ClientMatch` e `ProactiveSuggestion` nel database
   * Crea notifica di tipo MATCH: "La rottamazione quinquies potrebbe interessare 7 dei tuoi clienti"
   * Il badge della bell icon si aggiorna (unread count +1)

5. **Azione dell'utente**
   L'utente clicca la notifica → viene indirizzato alla pagina Comunicazioni dove può:
   * Vedere la lista clienti matchati
   * Generare una comunicazione personalizzata
   * Selezionare destinatari e canali (Email/WhatsApp)
   * Inviare la comunicazione

**Componenti e Database Coinvolti:**

| Componente | Funzione | Database Utilizzato |
|------------|----------|---------------------|
| LLM Response Generator | Genera risposta alla query (pipeline invariata) | Knowledge Base |
| Normativa Classifier | Identifica l'argomento normativo (async) | - |
| Rule Matcher | Trova regole applicabili (async) | Rules Database |
| Client Counter | Conta clienti che matchano (async) | Database Clienti |
| NotificationService | Crea notifica MATCH (async) | Notifications DB |

**Tempi di Esecuzione:**
Il matching è completamente asincrono e NON impatta la latenza della risposta:
* LLM Response: ~2-3 secondi (invariato, zero overhead aggiunto)
* Matching (background, dopo risposta): ~0.5-1 secondo
* Notifica creata: entro 5 secondi dalla consegna della risposta

#### 3.3.4 Regole di Matching

**Formato Regola:**

```yaml
Regola:
  id: "RULE_ROTTAMAZIONE_QUINQUIES"
  nome: "Rottamazione Quinquies"
  descrizione: "Definizione agevolata carichi affidati"
  validita:
    data_inizio: "2025-01-01"
    data_fine: "2025-03-31"

  condizioni:
    operator: AND
    rules:
      - campo: "posizione_agenzia_entrate"
        operatore: "IN"
        valori: ["con_debiti", "con_rateizzazione"]
      - campo: "ha_cartelle_esattoriali"
        operatore: "="
        valore: true

  esclusioni:
    - campo: "stato_cliente"
      operatore: "="
      valore: "cessato"

  priorita: "alta"
  categoria: "definizione_agevolata"
  fonte_normativa: "DL 145/2024"
```

**Regole Pre-configurate (MVP):**

| ID | Regola | Condizioni Principali | Categoria |
|----|--------|----------------------|-----------|
| R001 | Rottamazione Quinquies | posizione_ade IN (debiti, rateizzazione) | Fiscale |
| R002 | Resto al Sud | età < 35 AND p_iva = false AND regione IN (Sud) | Agevolazioni |
| R003 | Bonus Assunzioni Under 30 | tipo = azienda AND dipendenti > 0 | Lavoro |
| R004 | Bonus Assunzioni Donne | tipo = azienda AND dipendenti > 0 | Lavoro |
| R005 | Bonus Sud Assunzioni | tipo = azienda AND regione IN (Sud) | Lavoro |
| R006 | Obbligo Registratore Cassa | tipo = commercio AND regime != forfettario | Adempimenti |
| R007 | Obbligo POS | tipo IN (commercio, artigiano, servizi) | Adempimenti |
| R008 | Sicurezza Lavoro DVR | dipendenti > 0 | Adempimenti |
| R009 | Cedolare Secca | immobili.uso = locazione_abitativa | Fiscale |
| R010 | IMU Seconda Casa | immobili.count > 1 OR immobili.uso != abitazione_principale | Fiscale |

#### 3.3.5 Trigger Automatici

**Proactive Matching (notifiche push):**

```yaml
Trigger:
  tipo: "rss_update"
  fonte: "Gazzetta Ufficiale"
  azione:
    - Analizza nuovo documento
    - Identifica keywords normative
    - Matcha con regole esistenti
    - Se clienti_impattati > 0:
        - Notifica in-app al professionista
        - Suggerisci preparazione comunicazione
```

#### 3.3.6 Trigger Proattivo

> **Aggiornamento (ADR-035):** Il matching NON inserisce suggerimenti inline nella risposta chat.
> I risultati vengono consegnati esclusivamente tramite notifiche. La risposta normativa resta
> pulita e invariata.

Il matching crea una **notifica** (non un suggerimento inline) quando trova clienti interessati:

```json
{
  "matching_result": {
    "normativa_identificata": "rottamazione_quinquies",
    "regola_applicata": "RULE_ROTTAMAZIONE_QUINQUIES",
    "clienti_matchati": 7,
    "trigger_notifica": true
  },
  "notifica": {
    "type": "MATCH",
    "priority": "HIGH",
    "title": "La rottamazione quinquies potrebbe interessare 7 dei tuoi clienti",
    "description": "Clicca per vedere la lista e preparare una comunicazione",
    "reference_type": "proactive_suggestion",
    "reference_id": "UUID della ProactiveSuggestion",
    "action_url": "/comunicazioni?suggestion_id=UUID"
  }
}
```

**Quando NON creare notifica:**
* clienti_matchati = 0 → Nessuna notifica
* Database clienti vuoto → Suggerire di importare clienti (notifica separata di tipo NORMATIVA)
* Normativa non rilevante per matching (es: domanda teorica)
* Notifica duplicata già creata nell'ultima ora (deduplicazione)

#### 3.3.7 Lista Clienti (Pagina Comunicazioni)

> **Aggiornamento (ADR-035):** La lista clienti matchati viene mostrata sulla pagina
> Comunicazioni (GestioneComunicazioniPage), non inline nella chat.

Quando l'utente clicca una notifica MATCH, viene indirizzato alla pagina Comunicazioni
con il contesto della suggestion:

```yaml
Lista_Clienti_Matchati:
  header: "7 clienti potrebbero essere interessati alla Rottamazione Quinquies"
  pagina: "/comunicazioni?suggestion_id=UUID"

  clienti:
    - nome: "Mario Rossi SRL"
      motivazione: "Ha cartelle esattoriali per €12.500"
      posizione: "con_debiti"

    - nome: "Bianchi Giuseppe"
      motivazione: "Rateizzazione INPS in corso"
      posizione: "con_rateizzazione"

    - nome: "Verdi & Associati SNC"
      motivazione: "Avvisi di accertamento pendenti"
      posizione: "contenzioso"

  azioni:
    - "Prepara comunicazione per tutti"
    - "Seleziona clienti specifici"
    - "Esporta lista"
```

#### 3.3.8 Criteri di Accettazione

> **Aggiornamento (ADR-035):** Criteri aggiornati per riflettere il delivery via notifiche.

* **AC-003.1:** Matching eseguito in modo **asincrono** dopo la consegna della risposta (zero latenza aggiunta alla pipeline RAG)
* **AC-003.2:** Notifica MATCH creata SOLO se clienti_matchati > 0
* **AC-003.3:** Conteggio clienti è sempre accurato (query real-time)
* **AC-003.4:** Pagina Comunicazioni mostra nome + motivazione per ogni cliente matchato
* **AC-003.5:** Regole con scadenza temporale rispettate (non notificare normative scadute)
* **AC-003.6:** Se database clienti vuoto, suggerire importazione (notifica di tipo NORMATIVA)
* **AC-003.7:** Notifica creata entro 5 secondi dalla consegna della risposta normativa
* **AC-003.8:** Deduplicazione notifiche: stessa normativa + stesso studio = max 1 notifica per ora

---

### FR-004: Suggerimenti Proattivi e Generazione Comunicazioni

#### 3.4.1 Descrizione

> **Decisione architetturale (ADR-035, 2026-02-26):** Il workflow di suggerimento proattivo
> NON avviene inline nella chat. Il matching è asincrono e i risultati vengono consegnati
> tramite notifiche. Il workflow di creazione comunicazione avviene sulla pagina dedicata
> GestioneComunicazioniPage.

Dopo ogni ricerca normativa, PratikoAI esegue in background un matching asincrono del database clienti. Se trova clienti potenzialmente interessati, crea una **notifica di tipo MATCH** che il professionista vede nel bell icon dropdown. Cliccando la notifica, il professionista viene indirizzato alla pagina Comunicazioni dove può generare, personalizzare e inviare comunicazioni tramite un workflow dedicato.

#### 3.4.2 User Stories

> **Aggiornamento (ADR-035):** Le user stories sono state aggiornate per riflettere il delivery
> via notifiche invece che inline nella chat.

**US-004.1:** Come professionista, dopo aver cercato informazioni su una normativa, voglio ricevere una **notifica** che mi dica automaticamente quanti clienti potrebbero essere interessati, così da poter decidere se preparare una comunicazione dalla pagina dedicata.

**US-004.2:** Come professionista, voglio poter accettare o modificare il messaggio generato da PratikoAI nella pagina Comunicazioni prima di procedere.

**US-004.3:** Come professionista, voglio poter scegliere cosa fare con il messaggio: salvarlo, stamparlo, o inviarlo direttamente.

**US-004.4:** Come professionista, se scelgo di inviare, voglio vedere la lista dei clienti interessati e poter scegliere per ciascuno il canale di contatto preferito (email o WhatsApp).

#### 3.4.3 Workflow Proattivo Dettagliato

> **Decisione architetturale (ADR-035, 2026-02-26):** Il workflow originale era "conversazionale"
> (inline nella chat). È stato sostituito con un workflow basato su **notifiche + pagina dedicata**.
> Il matching avviene in modo asincrono e non impatta la pipeline RAG.

**STEP 1: Ricerca del Professionista**
Il professionista inserisce una domanda nella chat.
Esempio: "Spiegami la rottamazione quinquies"

**STEP 2: Risposta Normativa (pipeline RAG invariata)**
PratikoAI risponde con la spiegazione completa della normativa, includendo fonti e riferimenti normativi.
La risposta è pulita — nessun suggerimento o dato CRM inline.

**STEP 3: Matching Asincrono + Notifica**
Dopo la consegna della risposta, un background job esegue il matching clienti:
- Se clienti matchati > 0 → Crea notifica MATCH
- Il badge della bell icon si aggiorna (es: "7")
- Opzionale: toast/snackbar temporaneo "Trovati 7 clienti interessati alla rottamazione quinquies"

**STEP 4: Navigazione alla Pagina Comunicazioni**
Il professionista clicca la notifica MATCH → viene indirizzato a `/comunicazioni?suggestion_id=UUID`
La pagina mostra:
- Titolo della normativa e regola di matching applicata
- Lista clienti matchati con motivazione per ciascuno

**STEP 5: Generazione Messaggio (Pagina Comunicazioni)**
Il professionista clicca "Prepara comunicazione":

> **Messaggio generato (editor full-page):**
> Oggetto: Opportunità di risparmio fiscale - Rottamazione
>
> Gentile {{nome_cliente}},
> La contatto per informarLa di una importante opportunità... [testo completo del messaggio]
>
> Cordiali saluti, Studio [Nome Studio]

L'editor offre:
- Rich text toolbar (bold, italic, elenchi puntati)
- Inserimento variabili ({{nome_cliente}}, {{importo_debito}}, etc.)
- Anteprima con variabili risolte
- Opzioni: Modifica / Va bene così

**STEP 6: Scelta Azione**
Dopo l'approvazione del messaggio, il professionista sceglie cosa fare:
* Salva in PratikoAI (bozza)
* Stampa (genera PDF)
* Invia ai clienti (procede a selezione destinatari)

**STEP 7: Selezione Destinatari e Canali (Pagina Comunicazioni)**
Se il professionista sceglie "Invia ai clienti", la pagina mostra la tabella destinatari:

| Seleziona | Cliente | Contatti | Canale |
|-----------|---------|----------|--------|
| ☑ | Mario Rossi SRL | mario.rossi@email.it / +39 333 1234567 | Email |
| ☑ | Bianchi Giuseppe | g.bianchi@pec.it / +39 340 9876543 | WhatsApp |
| ☑ | Verdi & Associati SNC | info@verdiassociati.it / +39 335 5555555 | Email |
| ☐ | Neri Costruzioni SPA | (già contattato il 15/11) | - |

Riepilogo: 6 clienti selezionati (4 email, 2 WhatsApp)

Opzioni disponibili:
* Indietro
* Anteprima
* Invia ora

**STEP 8: Conferma e Invio**
Dopo l'invio, la pagina Comunicazioni mostra la conferma:

> Messaggi inviati con successo!
> * 4 email inviate
> * 2 messaggi WhatsApp inviati (modale conferma wa.me)
>
> Puoi monitorare le aperture nella sezione Dashboard.

#### 3.4.4 Dettaglio Step per Step

**STEP 3: Matching Asincrono + Notifica**

> **Aggiornamento (ADR-035):** Il trigger non produce più un suggerimento inline ma una notifica.

```yaml
Notifica_Match:
  trigger: "risposta_normativa_completata"
  esecuzione: "asincrona (background job)"
  condizione: "clienti_matchati > 0"
  deduplicazione: "max 1 notifica per normativa+studio per ora"

  notifica:
    type: "MATCH"
    priority: "HIGH"
    title_template: |
      {{normativa}} potrebbe interessare {{count}} dei tuoi clienti
    description: "Clicca per vedere la lista e preparare una comunicazione"
    action_url: "/comunicazioni?suggestion_id={{suggestion_id}}"
```

**STEP 5: Generazione Messaggio (Pagina Comunicazioni)**

```yaml
Template_Messaggio:
  oggetto: "Opportunità: {{titolo_normativa}} - Scadenza {{data_scadenza}}"

  corpo: |
    Gentile {{nome_cliente}},

    La contatto per informarLa di {{descrizione_breve_normativa}}.

    **Cosa prevede:**
    {{punti_chiave}}

    **Perché La riguarda:**
    {{motivazione_personalizzata}}

    **Scadenza:** {{data_scadenza}}

    Resto a disposizione per una consulenza personalizzata.

    Cordiali saluti,
    {{nome_studio}}
    {{contatti_studio}}

  variabili:
    - nome_cliente: "dal database clienti"
    - titolo_normativa: "dalla ricerca"
    - descrizione_breve: "generata da AI"
    - punti_chiave: "estratti dalla normativa"
    - motivazione_personalizzata: "basata su matching rule"
    - data_scadenza: "dalla normativa"
    - nome_studio: "da impostazioni"
    - contatti_studio: "da impostazioni"
```

**STEP 4: Opzioni Azione**

| Azione | Descrizione | Implementazione |
|--------|-------------|-----------------|
| Salva in PratikoAI | Salva messaggio per uso futuro | Database comunicazioni |
| Stampa | Genera PDF stampabile | Export PDF con variabili risolte |
| Invia ai clienti | Procede a selezione destinatari | Apre Step 5 |

#### 3.4.5 Gestione WhatsApp

**Confronto Opzioni:**

| Aspetto | Link wa.me (MVP) | WhatsApp Business API (Fase 2) |
|---------|------------------|--------------------------------|
| Costo per PratikoAI | €0 | Setup complesso (2-3 settimane) |
| Costo per messaggio | €0 | ~€0.03-0.05/messaggio |
| Invio automatico | ❌ No (click manuale) | ✅ Sì |
| Tracking consegna/lettura | ❌ No | ✅ Sì |
| Numero mittente | Numero del professionista | Numero studio (verificato) o PratikoAI |
| Setup per studio | Nessuno | Verifica Meta Business (1-2 settimane) |
| Tempo implementazione | 2 ore | 2-3 settimane |

**MVP: Link wa.me (Raccomandato)**

Come funziona:
1. PratikoAI genera un link `wa.me` con messaggio pre-compilato
2. Il professionista clicca "Invia" sulla comunicazione approvata
3. Si apre un **modale di conferma** dentro PratikoAI con anteprima del messaggio
4. Il professionista clicca "Apri WhatsApp" nel modale → si apre WhatsApp Web/App in un **nuovo tab**
5. Il professionista clicca "Invia" in WhatsApp per ogni cliente

**UX Flow — Modale di Conferma (Decisione architetturale, 2026-02-26):**

Quando il professionista clicca "Invia" su una comunicazione WhatsApp approvata (dalla Dashboard Comunicazioni o dal wizard chat), PratikoAI mostra un modale:

```
┌───────────────────────────────────┐
│  📨 Invia via WhatsApp            │
│                                   │
│  Destinatario:                    │
│  Mario Rossi (+39 333 123 4567)   │
│                                   │
│  Messaggio:                       │
│  "Gentile Mario, le ricordiamo    │
│   che la scadenza per..."         │
│                                   │
│  [Apri WhatsApp]  [Annulla]       │
└───────────────────────────────────┘
```

- "Apri WhatsApp" → `window.open(waLink, '_blank')` → WhatsApp Web/App si apre in un nuovo tab
- PratikoAI resta aperto → il professionista torna facilmente alla dashboard
- La comunicazione viene marcata come SENT nel sistema (il tracking effettivo non è disponibile in MVP)

**Invio Bulk WhatsApp:** Per invii multipli, il modale mostra la lista di tutti i destinatari con link individuali:

```
┌───────────────────────────────────────┐
│  📨 Invia via WhatsApp (3 clienti)    │
│                                       │
│  ☐ Mario Rossi (+39 333..)  [Apri]   │
│  ☐ Bianchi Giuseppe (+39 340..) [Apri]│
│  ☐ Verdi SNC (+39 335..)    [Apri]   │
│                                       │
│  Progresso: 0/3 inviati              │
│                                       │
│  [Chiudi]                             │
└───────────────────────────────────────┘
```

Ogni "Apri" apre WhatsApp in un nuovo tab. Il checkbox si spunta dopo il click per tracciare il progresso. "Chiudi" è attivo solo dopo che tutti i link sono stati aperti (o con conferma "Sei sicuro? 2 messaggi non ancora aperti").

Esempio link generato:
```
https://wa.me/393331234567?text=Gentile%20Mario%20Rossi%2C%20La%20contatto%20per%20informarLa...
```

**Vantaggi MVP:**
* Zero costi
* Implementazione immediata (2 ore)
* Il cliente riceve dal numero che già conosce (lo studio)
* Nessuna approvazione Meta necessaria
* Nessun setup richiesto al professionista
* Il professionista rivede il messaggio prima dell'invio (modale di conferma)
* PratikoAI resta aperto durante l'invio (nuovo tab)

**Limitazione accettabile:** Se un professionista seleziona 7 clienti per WhatsApp, dovrà fare 7 click manuali. Tuttavia, la maggior parte delle comunicazioni avverrà via email (automatica), quindi WhatsApp sarà usato per casi specifici.

#### 3.4.6 Salvataggio Messaggi

```yaml
Messaggio_Salvato:
  id: UUID
  studio_id: UUID

  metadata:
    titolo: "Rottamazione Quinquies - Dicembre 2025"
    normativa_riferimento: "DL 145/2024"
    data_creazione: timestamp
    clienti_target: [lista UUID clienti matchati]

  contenuto:
    oggetto: string
    corpo: text  # con variabili non risolte

  utilizzo:
    volte_inviato: integer
    ultimo_invio: timestamp

  tags: ["rottamazione", "definizione_agevolata", "2025"]
```

#### 3.4.7 Criteri di Accettazione

> **Aggiornamento (ADR-035):** Criteri aggiornati per riflettere il delivery via notifiche
> e il workflow sulla pagina Comunicazioni.

**Notifiche Proattive (sostituisce suggerimenti inline):**
* **AC-004.1:** Notifica MATCH creata entro 5s dalla consegna della risposta normativa
* **AC-004.2:** Conteggio clienti matchati è accurato (±0 errori)
* **AC-004.3:** Notifica NON creata se clienti matchati = 0
* **AC-004.3b:** Notifiche deduplicate: max 1 per normativa+studio per ora

**Generazione Messaggio (Pagina Comunicazioni):**
* **AC-004.4:** Generazione messaggio completo in <5 secondi
* **AC-004.5:** Editor full-page permette modifica libera del testo con rich text toolbar
* **AC-004.6:** Variabile {{nome_cliente}} presente nel messaggio generato

**Selezione Destinatari (Pagina Comunicazioni):**
* **AC-004.7:** Pagina destinatari mostra tutti i clienti matchati con checkbox
* **AC-004.8:** Selezione canale (Email/WhatsApp) disponibile per ogni cliente
* **AC-004.9:** Anteprima mostra messaggio con nome cliente reale

**Azioni Messaggio:**
* **AC-004.10:** Opzione "Salva" persiste messaggio nel database
* **AC-004.11:** Opzione "Stampa" genera PDF con variabili risolte (1 pagina per cliente)

**Invio Email (Automatico):**
* **AC-004.12:** Invio email funzionante via SMTP configurato
* **AC-004.13:** Tracking aperture email funzionante

**Invio WhatsApp (MVP - Modale di Conferma):**
* **AC-004.14:** Link wa.me generato correttamente con testo URL-encoded
* **AC-004.15:** Modale di conferma mostra anteprima destinatario, numero e messaggio prima dell'invio
* **AC-004.16:** "Apri WhatsApp" apre wa.me link in nuovo tab (WhatsApp Web/App con messaggio pre-compilato)
* **AC-004.17:** PratikoAI resta aperto nel tab originale durante l'invio WhatsApp
* **AC-004.18:** Invio bulk WhatsApp mostra lista destinatari con "Apri" individuale e contatore progresso
* **AC-004.19:** Nessun tracking WhatsApp in MVP (limitazione accettata)

**Logging:**
* **AC-004.20:** Log completo di ogni invio (email) e tentativo (WhatsApp link generato)

---

### FR-005: Dashboard ROI e Analytics

#### 3.5.1 Descrizione

Dashboard che mostra al professionista il valore generato da PratikoAI in termini di comunicazioni inviate, opportunità identificate, e tempo risparmiato.

#### 3.5.2 User Stories

**US-005.1:** Come professionista, voglio vedere quante comunicazioni ho inviato questo mese.

**US-005.2:** Come professionista, voglio vedere il tasso di apertura delle mie comunicazioni, così da capire cosa funziona.

**US-005.3:** Come titolare studio, voglio vedere quali collaboratori usano di più la piattaforma, così da incentivare l'adozione.

#### 3.5.3 Metriche Dashboard

**Sezione: Attività**

| Metrica | Periodo | Calcolo |
|---------|---------|---------|
| Query effettuate | Giorno/Settimana/Mese | Count query |
| Procedure consultate | Settimana/Mese | Count procedure views |
| Documenti analizzati | Settimana/Mese | Count uploads |

**Sezione: Engagement Clienti**

| Metrica | Periodo | Calcolo |
|---------|---------|---------|
| Comunicazioni inviate | Mese | Count sent |
| Tasso apertura | Mese | opened/sent % |
| Click su CTA | Mese | clicks/opened % |
| Clienti raggiunti | Mese | Unique clients |

**Sezione: Opportunità**

| Metrica | Periodo | Calcolo |
|---------|---------|---------|
| Matching effettuati | Mese | Count matches |
| Clienti identificati | Mese | Sum matched clients |
| Valore potenziale pratiche | Mese | Sum estimated value |

**Sezione: Tempo Risparmiato**

| Metrica | Calcolo |
|---------|---------|
| Tempo ricerca risparmiato | Query × 5 min media |
| Tempo comunicazioni risparmiato | Comunicazioni × 15 min |
| Totale ore risparmiate | Somma |

#### 3.5.4 Criteri di Accettazione

* **AC-005.1:** Dashboard carica in <2 secondi
* **AC-005.2:** Dati aggiornati in tempo reale (max 5 min delay)
* **AC-005.3:** Export report PDF mensile
* **AC-005.4:** Filtro per periodo personalizzabile
* **AC-005.5:** Breakdown per collaboratore (multi-user)

---

### FR-006: Sistema Scadenze Proattivo

#### 3.6.1 Descrizione

Sistema che mantiene un calendario delle scadenze fiscali e, incrociandolo con il database clienti, avvisa proattivamente il professionista delle scadenze che impattano i suoi clienti.

#### 3.6.2 User Stories

**US-006.1:** Come professionista, voglio ricevere un alert 30 giorni prima della scadenza IMU con il conteggio dei clienti interessati.

**US-006.2:** Come professionista, voglio vedere un calendario mensile con tutte le scadenze e i clienti impattati per ciascuna.

#### 3.6.3 Scadenze Pre-configurate

| Scadenza | Data | Matching Clienti |
|----------|------|------------------|
| IMU acconto | 16 Giugno | immobili.count > 0 |
| IMU saldo | 16 Dicembre | immobili.count > 0 |
| IRPEF acconto | 30 Giugno | regime IN (ordinario, semplificato) |
| IRPEF saldo | 30 Novembre | regime IN (ordinario, semplificato) |
| IVA trimestrale | 16/05, 16/08, 16/11, 16/02 | partita_iva IS NOT NULL |
| F24 mensile | 16 ogni mese | dipendenti > 0 |
| INPS fissi | trimestrale | regime = forfettario |
| Dichiarazione redditi | 30 Novembre | tutti |

#### 3.6.4 Criteri di Accettazione

* **AC-006.1:** Alert configurabile (30/15/7 giorni prima)
* **AC-006.2:** Integrazione con calendario esterno (Google, Outlook)
* **AC-006.3:** Notifica in-app e via email
* **AC-006.4:** Possibilità di silenziare scadenze non rilevanti

---

### FR-007: Calcoli Fiscali

#### 3.7.1 Descrizione

Sistema di calcolo integrato nel chat che permette al professionista di ottenere calcoli fiscali precisi (IRPEF, IVA, ritenute, contributi, IMU, etc.) inserendo i dati rilevanti nella conversazione. PratikoAI deve riconoscere la richiesta di calcolo e guidare l'utente nell'inserimento dei dati necessari.

#### 3.7.2 User Stories

**US-007.1:** Come commercialista, voglio poter chiedere "calcola l'IRPEF per un reddito di €45.000" e ricevere il calcolo dettagliato con aliquote, detrazioni e importo netto.

**US-007.2:** Come commercialista, voglio poter chiedere "quanto IVA devo versare se ho fatturato €10.000 + IVA e ho acquisti per €3.000 + IVA" e ricevere il calcolo della liquidazione.

**US-007.3:** Come consulente del lavoro, voglio poter inserire i dati di una busta paga e ottenere il calcolo di contributi INPS, IRPEF e netto in busta.

**US-007.4:** Come professionista, voglio poter calcolare la ritenuta d'acconto su una fattura di prestazione professionale.

**US-007.5:** Come commercialista, voglio poter calcolare l'IMU per un immobile inserendo rendita catastale, categoria e comune.

**US-007.6:** Come professionista, voglio che PratikoAI mi chieda i dati mancanti se la mia richiesta è incompleta, così da guidarmi nel calcolo corretto.

#### 3.7.3 Tipi di Calcolo Supportati

**Imposte sui Redditi:**

| Calcolo | Input Richiesti | Output |
|---------|-----------------|--------|
| IRPEF Persone Fisiche | Reddito imponibile, detrazioni | Imposta lorda, detrazioni, imposta netta, aliquota effettiva |
| IRPEF con scaglioni | Reddito complessivo | Dettaglio per scaglione, totale |
| Addizionali regionali/comunali | Reddito, regione, comune | Importo addizionale |
| Cedolare secca | Canone annuo, tipo contratto | Imposta 21% o 10% |

**IVA:**

| Calcolo | Input Richiesti | Output |
|---------|-----------------|--------|
| Scorporo IVA | Importo lordo, aliquota | Imponibile, IVA |
| Liquidazione IVA | Vendite, acquisti, aliquote | IVA a debito/credito |
| IVA regime forfettario | Compensi, coefficiente | Reddito imponibile |

**Contributi e Ritenute:**

| Calcolo | Input Richiesti | Output |
|---------|-----------------|--------|
| Contributi INPS artigiani/commercianti | Reddito | Fissi + percentuale, totale |
| Contributi gestione separata | Compensi | Contributo dovuto |
| Ritenuta d'acconto professionisti | Compenso | Ritenuta 20%, netto |
| Ritenuta agenti | Provvigioni | Ritenuta 23% su 50% |

**Imposte Locali:**

| Calcolo | Input Richiesti | Output |
|---------|-----------------|--------|
| IMU | Rendita, categoria, comune, % possesso | Imposta annua, acconti |
| TARI (stima) | mq, comune, categoria | Importo stimato |

**Lavoro Dipendente:**

| Calcolo | Input Richiesti | Output |
|---------|-----------------|--------|
| Netto in busta | RAL, regione, familiari a carico | Lordo, contributi, IRPEF, netto |
| Costo azienda | RAL, CCNL | Costo totale per l'azienda |
| TFR | Anni servizio, retribuzione | TFR maturato |

#### 3.7.4 Gestione Variazioni Regionali

```yaml
Variazioni_Regionali:
  addizionale_regionale:
    lombardia:
      aliquota_unica: 1.23%
      scaglioni:
        - {fino_a: 15000, aliquota: 1.23%}
        - {fino_a: 28000, aliquota: 1.58%}
        - {oltre: 28000, aliquota: 1.73%}
    lazio:
      scaglioni:
        - {fino_a: 15000, aliquota: 1.73%}
        - {fino_a: 28000, aliquota: 2.73%}
        - {oltre: 28000, aliquota: 3.33%}
    # ... altre regioni

  addizionale_comunale:
    fonte: "Database comuni IFEL/MEF"
    aggiornamento: "annuale"
    campi:
      - comune
      - aliquota
      - esenzione_reddito_minimo

  imu_aliquote:
    fonte: "Delibere comunali"
    campi:
      - comune
      - categoria_catastale
      - aliquota_ordinaria
      - aliquota_abitazione_principale
      - detrazioni
```

#### 3.7.5 Criteri di Accettazione

* **AC-007.1:** Calcolo IRPEF corretto al 100% rispetto a simulatori ufficiali (AdE)
* **AC-007.2:** Gestione automatica degli scaglioni vigenti
* **AC-007.3:** Richiesta guidata dei dati mancanti (non errore generico)
* **AC-007.4:** Calcolo contributi INPS allineato a tabelle INPS vigenti
* **AC-007.5:** Variazioni regionali/comunali per almeno 20 città principali al lancio
* **AC-007.6:** Export PDF del calcolo con dettaglio e fonti normative
* **AC-007.7:** Indicazione chiara della data di aggiornamento aliquote/parametri
* **AC-007.8:** Warning se parametri potrebbero essere obsoleti (>6 mesi)

---

### FR-008: Upload e Analisi Documenti

#### 3.8.1 Descrizione

Sistema che permette al professionista di caricare documenti (PDF, immagini, Excel) direttamente nella chat e ricevere un'analisi automatica. PratikoAI deve riconoscere il tipo di documento, estrarre i dati rilevanti e fornire un'analisi contestuale.

#### 3.8.2 User Stories

**US-008.1:** Come commercialista, voglio poter caricare una fattura elettronica XML e ottenere un riepilogo dei dati principali (fornitore, importo, IVA, data).

**US-008.2:** Come commercialista, voglio poter caricare un modello F24 compilato e verificare che i calcoli siano corretti.

**US-008.3:** Come professionista, voglio poter caricare un bilancio in PDF e ottenere un'analisi degli indicatori principali (ROI, ROE, liquidità).

**US-008.4:** Come consulente del lavoro, voglio poter caricare una busta paga e verificare la correttezza dei calcoli contributivi.

**US-008.5:** Come professionista, voglio poter caricare un documento e fare domande specifiche su di esso ("qual è l'imponibile?", "ci sono errori?").

**US-008.6:** Come professionista, voglio che i documenti caricati NON vengano salvati permanentemente per motivi di privacy e GDPR.

#### 3.8.3 Tipi di Documento Supportati

| Tipo Documento | Formato | Analisi Fornita |
|----------------|---------|-----------------|
| Fattura elettronica | XML (SDI) | Dati anagrafici, imponibili per aliquota, totale, verifica coerenza |
| Fattura PDF/immagine | PDF, JPG, PNG | OCR + estrazione dati principali |
| Modello F24 | PDF | Codici tributo, importi, verifica scadenze |
| CU (Certificazione Unica) | PDF | Redditi, ritenute, dati anagrafici |
| Modello 730/Redditi | PDF | Quadri compilati, redditi dichiarati, imposte |
| Bilancio | PDF, Excel | Stato patrimoniale, conto economico, indici |
| Busta paga | PDF | Lordo, contributi, trattenute, netto |
| Visura camerale | PDF | Dati società, cariche, attività |
| Contratto | PDF | Estrazione clausole chiave (su richiesta) |

#### 3.8.4 Privacy e Gestione Documenti

```yaml
Policy_Documenti:
  storage:
    tipo: "temporaneo in memoria"
    durata_massima: "durata della sessione chat"
    persistenza: false

  eliminazione:
    automatica: true
    trigger:
      - "fine sessione"
      - "richiesta utente"
      - "timeout 30 minuti inattività"

  dati_estratti:
    salvati: false  # Solo mostrati, non persistiti
    eccezione: "se utente richiede esplicitamente salvataggio"

  log:
    contenuto_documento: false
    metadata: true  # tipo doc, dimensione, timestamp

  gdpr_compliance:
    informativa: "I documenti caricati vengono elaborati in tempo reale
                  e non vengono salvati sui nostri server."
    base_giuridica: "esecuzione contratto"
```

#### 3.8.5 Criteri di Accettazione

* **AC-008.1:** Upload drag-and-drop funzionante per PDF, XML, JPG, PNG, XLSX
* **AC-008.2:** Limite dimensione file: 10 MB
* **AC-008.3:** Riconoscimento automatico tipo documento con accuratezza >90%
* **AC-008.4:** Parsing fattura elettronica XML con estrazione tutti i campi principali
* **AC-008.5:** OCR su documenti scansionati con accuratezza >85%
* **AC-008.6:** Analisi bilancio con calcolo automatico di almeno 5 indici
* **AC-008.7:** Verifica F24: validazione codici tributo e coerenza importi
* **AC-008.8:** Documento eliminato da memoria entro 30 minuti da fine elaborazione
* **AC-008.9:** Nessun dato del documento persistito nel database
* **AC-008.10:** Possibilità di fare domande contestuali sul documento caricato
* **AC-008.11:** Export analisi in PDF

---

### FR-009: Configurazione Email Ibrida (Hybrid Email Sending)

#### 3.9.1 Descrizione

Sistema di invio email ibrido con gating basato sul piano di abbonamento. Gli studi con piano Base utilizzano l'infrastruttura email centralizzata di PratikoAI (`comunicazioni@pratikoai.com`). Gli studi con piano Pro o Premium possono configurare il proprio server SMTP per inviare email dal proprio dominio, aumentando la fiducia dei clienti e i tassi di apertura.

#### 3.9.2 User Stories

**US-009.1:** Come professionista con piano Base, voglio che le comunicazioni ai miei clienti vengano inviate automaticamente da PratikoAI senza dover configurare nulla.

**US-009.2:** Come professionista con piano Pro, voglio poter configurare il mio server email (SMTP) nelle impostazioni per inviare comunicazioni dal mio dominio professionale (es. `info@studiorossi.it`).

**US-009.3:** Come professionista, voglio poter testare la configurazione SMTP prima di salvare, per verificare che funzioni correttamente.

**US-009.4:** Come professionista con piano Base, voglio vedere chiaramente che posso passare al piano Pro per avere email personalizzate dal mio dominio.

**US-009.5:** Come professionista, se la mia configurazione SMTP personalizzata fallisce, voglio che l'email venga inviata comunque tramite il sistema PratikoAI come fallback.

**US-009.6:** Come professionista, voglio che le credenziali del mio server email siano protette e crittografate, e che la mia password non sia mai visibile nell'interfaccia dopo averla salvata.

#### 3.9.3 Dettaglio Funzionale

**Livelli di servizio:**

| Piano | Prezzo | Email Personalizzata | Mittente | Reply-To |
|-------|--------|---------------------|----------|----------|
| Base | €25/mese | No | `"Nome Studio" <comunicazioni@pratikoai.com>` | Email studio (da profilo) |
| Pro | €75/mese | Sì (opzionale) | `"Nome Studio" <info@studiorossi.it>` | Configurabile |
| Premium | €150/mese | Sì (opzionale) | `"Nome Studio" <info@studiorossi.it>` | Configurabile |

**Catena di fallback per invio email:**
1. Se l'utente ha configurazione SMTP personalizzata verificata → usa SMTP personalizzato
2. Se configurazione personalizzata assente o fallisce → usa SMTP PratikoAI predefinito
3. Se anche SMTP predefinito fallisce → registra errore nel log

**Configurazione SMTP richiesta:**
- Host SMTP (es. `smtp.gmail.com`, `mail.studiorossi.it`)
- Porta (25, 465, 587)
- Username
- Password (crittografata con Fernet, AES-128-CBC + HMAC-SHA256)
- TLS/STARTTLS (default: attivo)
- Nome mittente
- Email mittente
- Email risposte (opzionale)

#### 3.9.4 Sicurezza e GDPR

```yaml
Sicurezza_Email_Config:
  crittografia_credenziali:
    algoritmo: "Fernet (AES-128-CBC + HMAC-SHA256)"
    chiave: "variabile d'ambiente SMTP_ENCRYPTION_KEY"
    storage: "colonna smtp_password_encrypted nel DB"

  protezione_api:
    password_in_risposta: false  # Mai restituita in GET
    password_in_log: false  # Mai registrata nei log
    rate_limit_test: "5 tentativi/ora per utente"

  protezione_ssrf:
    porte_consentite: [25, 465, 587]
    ip_bloccati: ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8"]
    timeout_connessione: "10 secondi"

  gdpr:
    ruolo_pratikoai: "responsabile del trattamento (data processor)"
    base_giuridica: "esecuzione contratto"
    diritto_cancellazione: "credenziali SMTP eliminate su richiesta o cancellazione studio"
    notifica_violazione: "credenziali SMTP compromesse = violazione notificabile (Art. 33, 72h)"
    rotazione_chiavi: "supporto re-crittografia con nuova chiave Fernet"
```

#### 3.9.5 Criteri di Accettazione

* **AC-009.1:** Piano Base invia email da `comunicazioni@pratikoai.com` senza configurazione
* **AC-009.2:** Piani Pro e Premium possono configurare SMTP personalizzato nelle impostazioni
* **AC-009.3:** Piano Base riceve errore 403 se tenta configurazione email personalizzata
* **AC-009.4:** Credenziali SMTP crittografate con Fernet e mai visibili in API o log
* **AC-009.5:** Validazione connessione SMTP (EHLO + STARTTLS + LOGIN) prima del salvataggio
* **AC-009.6:** Fallback automatico a PratikoAI se SMTP personalizzato fallisce
* **AC-009.7:** Header `From` e `Reply-To` corretti per entrambe le modalità
* **AC-009.8:** Rate limit di 5 test SMTP per ora per utente
* **AC-009.9:** Protezione SSRF attiva (porte consentite, IP privati bloccati)
* **AC-009.10:** Rotazione chiave di crittografia supportata senza downtime
* **AC-009.11:** UI impostazioni mostra upsell per Base e form SMTP per Pro/Premium

---

## 4. Requisiti Non Funzionali

### 4.1 Performance

| Requisito | Target | Misurazione |
|-----------|--------|-------------|
| Response time query | ≤ 3s P95 | Prometheus |
| Response time matching | ≤ 2s P95 | Prometheus |
| Import 1000 clienti | ≤ 30s | Test automatico |
| Generazione 50 comunicazioni | ≤ 10s | Test automatico |
| Disponibilità | 99.9% | Uptime monitor |

### 4.2 Sicurezza

| Requisito | Implementazione |
|-----------|-----------------|
| Crittografia dati sensibili | AES-256 at rest (già implementato) |
| Crittografia in transito | TLS 1.3 |
| Autenticazione | JWT con refresh token |
| Audit log | Log immutabile per 5 anni |
| Backup | Daily, retention 30 giorni |

### 4.3 Privacy e GDPR

| Requisito | Implementazione |
|-----------|-----------------|
| Data Processing Agreement | Template DPA per ogni studio |
| Consenso marketing | Opt-in esplicito per comunicazioni |
| Diritto all'oblio | Già implementato (GDPR deletion) |
| Data portability | Già implementato (export) |
| Retention policy | Clienti: definita dallo studio, max 10 anni |
| Data location | EU only (Hetzner Germany) |

---

## 5. Architettura Proposta

### 5.1 Overview

**Livello 1: Frontend (Next.js)**

Interfaccia utente composta da 5 moduli principali:
* Chat AI - Conversazione con assistente fiscale
* Procedure - Procedure passo-passo per adempimenti
* Clienti Database - Gestione anagrafica clienti dello studio
* Comunicazioni - Generazione e invio messaggi ai clienti
* Dashboard ROI - Analytics e metriche di utilizzo

**Livello 2: API Layer (FastAPI)**

Backend con 5 servizi principali:
* Query Service - Gestione domande e risposte AI
* Procedure - Logica procedure interattive
* Client Manager - CRUD e gestione clienti
* Match Engine - Motore di matching clienti-normative
* Comms Service - Generazione e invio comunicazioni

**Livello 3: Data Layer**

4 sistemi di storage:
* PostgreSQL - Database principale (clienti, regole, storico)
* Redis - Cache e code di elaborazione
* Pinecone - Database vettoriale per ricerca semantica
* S3 - Storage documenti e backup

**Livello 4: External Integrations**

5 integrazioni esterne:
* RSS Feeds - Aggiornamenti normativi (Agenzia Entrate)
* OpenAI/Anthropic - Modelli LLM per risposte AI
* SendGrid - Invio email transazionali
* Stripe - Gestione abbonamenti e pagamenti
* ISTAT - Database codici ATECO

**Flusso Dati:**

```
Frontend (Next.js)
       ↓
API Layer (FastAPI)
       ↓
Data Layer (PostgreSQL, Redis, Pinecone, S3)
       ↓
External Integrations (RSS, LLM, Email, Payments, ATECO)
```

> **Very important note:** PratikoAI already has an architecture. We need to integrate these points into the current architecture. If some point get in contrast always refer to agent Egidio who is our architecture or involve the human in the loop.

---

## 6. Definizione MVP

### 6.1 In Scope MVP

* ✅ Import clienti da Excel
* ✅ Matching automatico su query con notifica proattiva (ADR-035: via notifiche, non inline chat)
* ✅ Calcoli fiscali base (IRPEF, IVA, contributi)
* ✅ Upload e analisi documenti (fatture XML, F24, bilanci)
* ✅ 9 procedure interattive principali
* ✅ Generazione comunicazioni con scelta canale (Email/WhatsApp)
* ✅ Opzioni Salva/Stampa/Invia per messaggi
* ✅ Dashboard base
* ✅ Tutte le variazioni regionali (solo 20 città principali)

### 6.2 Out of Scope MVP

* ❌ Integrazioni gestionali (TeamSystem, Zucchetti)
* ❌ PEC automatica
* ❌ WhatsApp Business API (solo link wa.me)
* ❌ Modifica regole matching da UI
* ❌ Multi-studio (white label)

---

## 7. Domande Aperte

### 7.1 Funzionalità

| # | Domanda | Impatto |
|---|---------|---------|
| Q1 | Quante procedure sono necessarie per MVP? Suggerimento: 9 | Alto |
| Q2 | Il professionista può creare regole di matching custom? | Medio |
| Q3 | Serve approvazione prima dell'invio comunicazioni o invio diretto? | Alto |
| Q4 | Template comunicazioni devono essere personalizzabili per studio? | Medio |
| Q5 | Servono report periodici automatici (es: settimanali)? | Basso |

### 7.2 Calcoli Fiscali

| # | Domanda | Impatto |
|---|---------|---------|
| Q6 | Quali calcoli sono prioritari per MVP? (IRPEF, IVA, contributi base?) | Alto |
| Q7 | Quante città/comuni servire con aliquote locali al lancio? (20? 50? 100?) | Medio |
| Q8 | Serve storico dei calcoli effettuati per ogni cliente? | Basso |
| Q9 | I calcoli devono poter essere allegati alle comunicazioni? | Medio |

### 7.3 Documenti

| # | Domanda | Impatto |
|---|---------|---------|
| Q10 | Quali tipi di documento sono prioritari? (Fatture XML, F24, bilanci?) | Alto |
| Q11 | Serve OCR per documenti scansionati o solo file nativi digitali? | Alto |
| Q12 | Analisi bilancio: quanti e quali indici calcolare? | Medio |
| Q13 | I documenti possono essere associati ai clienti nel database? | Medio |

### 7.4 Dati Clienti

| # | Domanda | Impatto |
|---|---------|---------|
| Q14 | Quali campi cliente sono obbligatori per il matching minimo? | Alto |
| Q15 | Retention policy dati clienti: chi decide? Studio o piattaforma? | Alto |
| Q16 | Serve storico comunicazioni inviate per compliance? Quanto? | Medio |
| Q17 | Database ATECO: fonte ufficiale ISTAT o copia statica? | Basso |

### 7.5 Integrazioni

| # | Domanda | Impatto |
|---|---------|---------|
| Q18 | Priorità integrazione gestionali: quale primo? | Alto |
| Q19 | Calendario: Google, Outlook, o entrambi? | Basso |
| Q20 | Tracking email: pixel o link tracking? (GDPR implications) | Medio |

### 7.6 Business

| # | Domanda | Impatto |
|---|---------|---------|
| Q21 | Limite clienti per piano base? O illimitati? | Alto |
| Q22 | Limite comunicazioni mensili? | Medio |
| Q23 | Addon pricing per funzionalità extra? | Medio |

---

## 8. Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Complessità matching | Media | Alto | MVP con regole semplici, iterare |
| GDPR dati clienti | Bassa | Alto | DPA obbligatorio, encryption |
| Adozione procedure | Media | Medio | Focus su 9 più usate |
| Spam comunicazioni | Media | Alto | Rate limiting, unsubscribe facile |
| Accuratezza regole | Media | Alto | Validazione con partner fiscale |

---

## 9. Glossario

| Termine | Definizione |
|---------|-------------|
| Matching | Processo di identificazione clienti interessati da una normativa |
| Regola | Set di condizioni che definiscono quali clienti sono impattati |
| Procedura | Workflow passo-passo per completare un adempimento. Consultabile come riferimento generico (`/procedura`) o avviabile per un cliente specifico (`@NomeCliente`) con tracciamento del progresso |
| Studio | Account principale del professionista |
| Comunicazione | Messaggio generato per informare i clienti |
| ATECO | Codice classificazione attività economiche ISTAT |
| CTA | Call to Action - invito all'azione nel messaggio |

---

## 11. GDPR e Gestione Dati Clienti

### 11.1 Contesto e Rischi

PratikoAI memorizza dati dei clienti degli studi professionali. Questo comporta responsabilità specifiche in ambito GDPR e richiede misure tecniche e organizzative adeguate.

**Dati trattati:**

| Categoria | Esempi | Sensibilità |
|-----------|--------|-------------|
| Identificativi | Nome, Codice Fiscale, P.IVA | Alta |
| Contatto | Email, telefono, indirizzo | Media |
| Fiscali | Regime fiscale, codice ATECO, debiti | Alta |
| Finanziari | Cartelle esattoriali, rateizzazioni | Alta |
| Comunicazioni | Storico messaggi inviati | Media |

**Rischi principali:**
* Data breach con esposizione dati sensibili
* Uso improprio dei dati da parte di terzi
* Non conformità GDPR con sanzioni fino al 4% del fatturato
* Danno reputazionale per PratikoAI e per lo studio

### 11.2 Ruoli GDPR

**Definizione ruoli:**

| Soggetto | Ruolo GDPR | Responsabilità |
|----------|------------|----------------|
| Cliente finale (es: Mario Rossi SRL) | Interessato | Proprietario dei propri dati |
| Studio professionale | Titolare del trattamento | Decide finalità e mezzi del trattamento |
| PratikoAI | Responsabile del trattamento | Tratta i dati per conto dello studio |

**Implicazioni:**
* Lo studio è responsabile di avere base giuridica per trattare i dati dei propri clienti
* PratikoAI tratta i dati solo su istruzione dello studio
* È obbligatorio un Data Processing Agreement (DPA) tra PratikoAI e ogni studio

### 11.3 Data Processing Agreement (DPA)

**Contenuto obbligatorio del DPA:**

1. **Oggetto e durata**
   * Descrizione del trattamento
   * Durata legata al contratto di servizio

2. **Natura e finalità**
   * Erogazione servizio PratikoAI
   * Matching clienti-normative
   * Generazione comunicazioni
   * Analytics aggregate (anonimizzate)

3. **Categorie di dati**
   * Dati identificativi
   * Dati di contatto
   * Dati fiscali e finanziari

4. **Obblighi di PratikoAI**
   * Trattare i dati solo su istruzione documentata
   * Garantire riservatezza del personale
   * Implementare misure di sicurezza adeguate
   * Non ricorrere a sub-responsabili senza autorizzazione
   * Assistere lo studio per richieste degli interessati
   * Cancellare i dati al termine del contratto
   * Consentire audit di conformità

5. **Sub-responsabili**
   * Lista dei sub-responsabili (es: AWS, OpenAI)
   * Procedura di notifica per nuovi sub-responsabili

### 11.4 Misure Tecniche di Sicurezza

**Encryption:**

| Dove | Tipo | Standard |
|------|------|----------|
| Dati in transito | TLS | TLS 1.3 |
| Dati a riposo (database) | AES | AES-256 |
| Backup | AES | AES-256 |
| Campi sensibili (CF, email) | Field-level encryption | AES-256-GCM |

**Access Control:**

| Misura | Implementazione |
|--------|-----------------|
| Autenticazione | JWT + refresh token |
| Autorizzazione | RBAC (Role-Based Access Control) |
| Isolamento dati | Ogni studio vede solo i propri clienti |
| Audit log | Log di ogni accesso e modifica |
| Session management | Timeout 30 minuti inattività |

**Infrastructure:**

| Requisito | Implementazione |
|-----------|-----------------|
| Hosting | EU (preferibilmente Italia) |
| Provider | Hetzner (Germania - Norimberga/Falkenstein) |
| Backup | Giornaliero, retention 30 giorni, encrypted |
| Disaster recovery | RTO 4 ore, RPO 24 ore |

### 11.5 Misure Organizzative

**Accesso ai dati:**
* Solo personale autorizzato e formato
* Principio del minimo privilegio
* NDA obbligatorio per tutti i dipendenti/collaboratori
* Revisione periodica degli accessi (trimestrale)

**Formazione:**
* Training GDPR obbligatorio per il team
* Aggiornamento annuale

**Procedure:**
* Procedura gestione data breach
* Procedura per richieste degli interessati
* Procedura per audit

### 11.6 Diritti degli Interessati

I clienti finali (interessati) possono esercitare i loro diritti tramite lo studio. PratikoAI deve supportare lo studio nel rispondere.

**Diritti e implementazione:**

| Diritto | Come lo supportiamo |
|---------|---------------------|
| Accesso | Export completo dati cliente in JSON/CSV |
| Rettifica | UI per modifica dati da parte dello studio |
| Cancellazione | Eliminazione completa con conferma |
| Portabilità | Export in formato machine-readable |
| Opposizione | Flag per escludere cliente da comunicazioni |
| Limitazione | Flag per bloccare trattamento |

**SLA per richieste:**
* Risposta entro 72 ore lavorative
* Completamento entro 30 giorni (come da GDPR)

### 11.7 Data Retention

**Policy di conservazione:**

| Dato | Retention | Motivazione |
|------|-----------|-------------|
| Dati cliente attivo | Durata contratto studio | Necessario per servizio |
| Dati cliente eliminato | Cancellazione immediata | Richiesta studio |
| Storico comunicazioni | 24 mesi | Compliance professionale |
| Audit log | 36 mesi | Requisiti sicurezza |
| Backup contenenti dati cancellati | Max 30 giorni | Ciclo backup |

**Cancellazione automatica:**
* Alla chiusura account studio: cancellazione entro 30 giorni
* Possibilità di export prima della cancellazione

### 11.8 Data Breach Management

**Procedura in caso di violazione:**

**Step 1: Rilevazione (0-4 ore)**
* Identificazione della violazione
* Contenimento immediato
* Valutazione impatto iniziale

**Step 2: Valutazione (4-24 ore)**
* Analisi tecnica approfondita
* Identificazione dati compromessi
* Valutazione rischio per gli interessati

**Step 3: Notifica (entro 72 ore)**
* Se rischio per interessati: notifica al Garante
* Notifica agli studi interessati
* Documentazione dell'incidente

**Step 4: Comunicazione agli interessati (se necessario)**
* Se rischio elevato: comunicazione diretta
* Tramite lo studio (Titolare del trattamento)

**Step 5: Remediation**
* Risoluzione vulnerabilità
* Miglioramento misure di sicurezza
* Aggiornamento procedure

### 11.9 Sub-Responsabili

**Lista sub-responsabili autorizzati:**

| Fornitore | Servizio | Dati trattati | Paese |
|-----------|----------|---------------|-------|
| Hetzner Online GmbH | Hosting, database | Tutti | Germania (EU) |
| OpenAI | LLM per risposte | Query (no dati clienti) | USA* |
| Anthropic | LLM per risposte | Query (no dati clienti) | USA* |
| Stripe | Pagamenti | Solo dati studio (no clienti) | USA* |
| SendGrid | Email | Email destinatari | USA* |

*Con Standard Contractual Clauses (SCC) per trasferimento extra-EU

**Nota importante su LLM:**
* Le query inviate a OpenAI/Anthropic NON contengono dati identificativi dei clienti
* Il matching avviene localmente, solo la domanda normativa va all'LLM
* Esempio: "Spiega la rottamazione quinquies" → va all'LLM
* I dati "Mario Rossi ha cartelle per €12.500" → restano nel nostro DB

### 11.10 Checklist Compliance Pre-Lancio

**Documentazione legale:**
- [ ] Privacy Policy pubblicata sul sito
- [ ] Termini di Servizio con sezione dati
- [ ] DPA template pronto per gli studi
- [ ] Registro dei trattamenti compilato
- [ ] DPIA (Data Protection Impact Assessment) completata

**Misure tecniche:**
- [ ] Encryption at rest implementata
- [ ] Encryption in transit (TLS 1.3)
- [ ] Audit logging attivo
- [ ] Backup encrypted e testati
- [ ] Procedura di cancellazione dati testata
- [ ] Export dati funzionante

**Misure organizzative:**
- [ ] DPO nominato (se necessario) o referente privacy
- [ ] Formazione team completata
- [ ] Procedura data breach documentata
- [ ] Contratti con sub-responsabili firmati

### 11.11 Responsabilità dello Studio

**Obblighi dello studio (da comunicare chiaramente):**

1. **Base giuridica**
   * Lo studio deve avere base giuridica per trattare i dati dei propri clienti
   * Tipicamente: esecuzione contratto professionale o consenso

2. **Informativa**
   * Lo studio deve informare i propri clienti che usa PratikoAI
   * Deve indicare PratikoAI come responsabile del trattamento

3. **Qualità dei dati**
   * Lo studio è responsabile dell'accuratezza dei dati inseriti
   * Deve mantenere i dati aggiornati

4. **Richieste degli interessati**
   * Lo studio è il punto di contatto per i propri clienti
   * PratikoAI supporta tecnicamente ma non risponde direttamente

**Template informativa per studio:**

> "Il nostro studio utilizza PratikoAI, una piattaforma di assistenza fiscale, per gestire le comunicazioni e identificare opportunità rilevanti per i nostri clienti. I dati vengono trattati in conformità al GDPR e conservati su server in Unione Europea. Per maggiori informazioni o per esercitare i propri diritti, contattare lo studio."

### 11.12 Domande Aperte GDPR

| # | Domanda | Impatto | Decisione necessaria |
|---|---------|---------|----------------------|
| G1 | Serve nominare un DPO? | Alto | Verificare se >250 dipendenti o trattamento su larga scala |
| G2 | DPIA è obbligatoria? | Alto | Probabilmente sì per trattamento dati fiscali su larga scala |
| G3 | Hosting Italia vs EU? | Medio | Hetzner Germania più economico, AWS Milano più vicino |
| G4 | OpenAI/Anthropic: SCC sufficienti? | Alto | Verificare con legale, considerare alternative EU |
| G5 | Retention comunicazioni: 24 mesi ok? | Medio | Verificare requisiti ordini professionali |
| G6 | Serve assicurazione cyber? | Alto | Fortemente consigliata |

---

## Related Documents

- [PRATIKO_2.0.md](./PRATIKO_2.0.md) - Implementation task breakdown
- [ADR-017: Multi-Tenancy Architecture](../architecture/decisions/ADR-017-multi-tenancy-architecture.md)
- [ADR-018: Normative Matching Engine](../architecture/decisions/ADR-018-normative-matching-engine.md)

---

## Appendix A: Figma Design Prompts

> **Usage:** Copy these prompts into Figma AI to generate UI designs for PratikoAI 2.0 features.
> After generating, take screenshots and attach to relevant frontend tasks in PRATIKO_2.0.md.

### A.1 PratikoAI Design System Reference

All designs must follow the existing PratikoAI design system (from `globals.css`):

**Color Palette:**

| Name | Hex | Usage |
|------|-----|-------|
| Blu Petrolio | #2A5D67 | Primary color, headings, buttons, links |
| Avorio | #F8F5F1 | Background, cards, light areas |
| Verde Salvia | #A9C1B7 | Secondary accent, success states |
| Oro Antico | #D4A574 | Accent, highlights, CTAs |
| Grigio Tortora | #C4BDB4 | Muted text, borders, dividers |
| Dark Slate | #1E293B | Body text, foreground |
| Sabbia Calda | #DCC7A1 | Decorative elements only |

**Typography & Components:**

- **Font:** Inter, -apple-system, BlinkMacSystemFont
- **Framework:** Radix UI components
- **Border radius:** 0.625rem (10px)
- **Cards:** White (#ffffff) with subtle shadows, rounded corners
- **Focused state:** Light teal background

### A.2 Claude Code Style Option Selector Pattern

When the AI suggests actions or asks for decisions, use this keyboard-navigable pattern:

```
┌─────────────────────────────────────────────────────────────┐
│ 💡 La rottamazione potrebbe interessare 7 dei tuoi clienti. │
│    Vuoi che ti prepari un messaggio?                        │
├─────────────────────────────────────────────────────────────┤
│  ● Sì, prepara il messaggio (Recommended)                   │  ← focused
│    Genera bozza comunicazione per tutti i clienti           │
│                                                             │
│  ○ Mostra lista clienti                                     │
│    Vedi quali clienti sono interessati prima di decidere    │
│                                                             │
│  ○ No, grazie                                               │
│    Ignora questo suggerimento                               │
└─────────────────────────────────────────────────────────────┘

Keyboard: ↑↓ to navigate, Enter to select, Esc to dismiss
Visual:
- Card border: Blu Petrolio (#2A5D67)
- Focused row background: Verde Salvia light (#A9C1B780)
- Radio indicator focused: Blu Petrolio filled
- Option text: Dark Slate (#1E293B)
- Description text: Grigio Tortora (#C4BDB4)
```

---

### A.3 Prompt 1A: Client Database Screens (HIGH Priority)

```
CONTEXT (from FR-002):
PratikoAI 2.0 introduces "Database Clienti dello Studio" - a system that allows professionals (commercialisti, consulenti del lavoro, avvocati tributaristi) to upload and maintain a database of their clients with structured attributes for automatic normative matching. Key fields include: tipo_soggetto (persona_fisica, ditta_individuale, societa_persone, societa_capitali, ente_no_profit), regime_fiscale (ordinario, semplificato, forfettario), codice_ateco, CCNL, n_dipendenti, posizione_agenzia_entrate, and tags. Import from Excel/CSV is required.

DESIGN TASK:
Add to the existing PratikoAI Figma design: client database management screens. Use the PratikoAI color palette: Blu Petrolio (#2A5D67) for headers/buttons, Avorio (#F8F5F1) for backgrounds, Dark Slate (#1E293B) for text, Grigio Tortora (#C4BDB4) for borders/muted elements.

SCREEN 1: CLIENT LIST VIEW
- Header: "Database Clienti" with search bar and filters
- Filters: tipo_soggetto (dropdown), regime_fiscale (dropdown), stato_cliente (tabs: Attivi/Prospect/Tutti)
- Table columns: Nome/Ragione Sociale, Codice Fiscale (masked: ***XXXX), Regime, ATECO, Dipendenti, Tags, Azioni
- Row actions: View, Edit, Delete icons
- Bulk actions bar (when rows selected): "Esporta", "Crea comunicazione"
- Pagination: "Mostrando 1-50 di 847 clienti"
- FAB button: "+ Aggiungi Cliente"
- Empty state: Illustration + "Nessun cliente trovato. Importa da Excel o aggiungi manualmente."

SCREEN 2: CLIENT DETAIL/EDIT FORM
- Tabbed form with sections:
  - Tab 1 "Anagrafica": denominazione, codice_fiscale, partita_iva, tipo_soggetto, indirizzo, CAP, comune, provincia
  - Tab 2 "Dati Fiscali": regime_fiscale, codice_ateco (with search), data_inizio_attivita, posizione_agenzia_entrate, ha_cartelle_esattoriali
  - Tab 3 "Lavoro": numero_dipendenti, ccnl_applicato, ha_apprendisti, ha_lavoratori_stagionali
  - Tab 4 "Immobili": List of immobili with add/remove
  - Tab 5 "Tags & Note": Tag chips with add, note textarea
- Validation: Red border + error message under invalid fields
- Actions: "Annulla", "Salva" (primary blue)

SCREEN 3: IMPORT WIZARD (3-step)
- Step 1: File upload dropzone "Trascina file Excel o CSV" + "Sfoglia" button
- Step 2: Column mapping table (Our Field → Your Column dropdown)
- Step 3: Preview with validation errors highlighted in red, success count in green
- Progress bar at top
- "Indietro", "Avanti" / "Importa X clienti" buttons

Maintain consistency with existing PratikoAI design system. Use Radix UI components, Inter font.
```

---

### A.4 Prompt 1B: Communication Workflow Screens (HIGH Priority)

```
CONTEXT (from FR-004, updated per ADR-035):
PratikoAI automatically matches clients with relevant regulations via async background matching. When matches are found, a MATCH notification appears in the bell icon dropdown. The professional clicks the notification and is navigated to the Comunicazioni page where the full workflow happens: see matched clients → generate draft with variables ({{nome_cliente}}, {{importo_debito}}) → review/edit → select recipients with channel preference (Email or WhatsApp) → send. For MVP, WhatsApp uses wa.me links (manual send), email is automatic via SMTP. The workflow does NOT happen inline in the chat (see ADR-035).

DESIGN TASK:
Add to the existing PratikoAI Figma design: communication generation wizard. Use Blu Petrolio (#2A5D67) for primary buttons, Oro Antico (#D4A574) for accent/CTA, Verde Salvia (#A9C1B7) for success states.

SCREEN 1: MESSAGE EDITOR
- Header: "Nuova Comunicazione" with breadcrumb
- Preview card showing:
  - Subject line (editable): "Opportunità: Rottamazione Quinquies - Scadenza 31/03/2025"
  - Body with variable placeholders highlighted: {{nome_cliente}}, {{importo_debito}}
  - Rich text toolbar (bold, italic, bullet list)
- Right sidebar: Variable inserter with available placeholders
- Footer: "Annulla", "Anteprima", "Avanti" buttons

SCREEN 2: RECIPIENT SELECTION
- Header: "Seleziona Destinatari" with count "7 clienti selezionati"
- Table:
  - Checkbox column
  - Cliente (name + company type badge)
  - Contatti (email icon + phone icon with values)
  - Canale (toggle: Email / WhatsApp)
  - Motivazione (why they matched - e.g., "Cartelle esattoriali: €12.500")
  - Last contacted (date or "Mai")
- "Seleziona tutti" / "Deseleziona tutti"
- Summary bar: "4 via Email, 3 via WhatsApp"
- Footer: "Indietro", "Anteprima" buttons

SCREEN 3: PREVIEW MODAL
- Split view:
  - Left: Recipient dropdown to preview for each client
  - Right: Rendered message with variables replaced
- Subject line shown above body
- "Email Preview" / "WhatsApp Preview" tabs
- Footer: "Modifica", "Salva bozza", "Invia ora" (primary)

SCREEN 4: CONFIRMATION/STATUS
- Success illustration with checkmark
- Stats: "6 email inviate con successo", "3 messaggi WhatsApp da inviare"
- If WhatsApp: Confirmation modal with message preview and "Apri WhatsApp" button per recipient (opens wa.me link in new tab). Bulk view shows checklist of recipients with individual "Apri" buttons and progress counter (e.g., "2/3 inviati"). Modal stays open until all links opened or user confirms close.
- "Visualizza in Dashboard", "Nuova comunicazione" buttons

Maintain step indicator at top, consistent with existing PratikoAI form styling.
```

---

### A.5 Prompt 2: Notification-Based Match Alerts & Calculator Cards (HIGH Priority)

> **Aggiornamento (ADR-035):** I componenti PROACTIVE SUGGESTION CARD e MATCHED CLIENTS INLINE LIST
> sono stati rimossi dal chat. Il matching è ora consegnato tramite il sistema di notifiche
> (NotificationsDropdown, DEV-426) e il workflow avviene sulla pagina Comunicazioni.
> L'unico componente inline rimasto in questa sezione è il CALCULATOR RESULT CARD.

```
CONTEXT (from FR-003 + FR-004, updated per ADR-035):
The Matching Engine operates ASYNCHRONOUSLY after each normative response delivery (not inline in chat). When matches are found, a MATCH notification is created and displayed in the bell icon dropdown (NotificationsDropdown). Clicking the notification navigates to the Comunicazioni page where the full workflow happens.

DESIGN TASK:
Add to the existing PratikoAI Figma design: (1) MATCH notification toast, (2) calculator result card for chat.

COMPONENT 1: MATCH NOTIFICATION TOAST (temporary, auto-dismissing)
- Appears bottom-right after normative response when matches found (async)
- Auto-dismisses after 8 seconds, or click to navigate
- Card with Oro Antico (#D4A574) left border accent (3px)
- Background: white with subtle shadow
- Icon: Target icon in Oro Antico (#D4A574)
- Text: "Trovati 7 clienti interessati alla rottamazione quinquies"
- Subtext: "Clicca per vedere la lista" (link to /comunicazioni)
- Close X button in Grigio Tortora (#C4BDB4)
- Animates in from bottom-right, fades out on dismiss

NOTE: The full MATCH notification item in NotificationsDropdown is already designed in DEV-426.
This toast is a supplementary visual cue that appears alongside the badge update.

COMPONENT 2: CALCULATOR RESULT CARD (inline in chat — unchanged)
- Card header: "Calcolo IRPEF 2024" with result badge
- Summary table:
  | Voce | Importo |
  | Reddito imponibile | €45.000 |
  | Imposta lorda | €11.520 |
  | Detrazioni | -€1.880 |
  | Imposta netta | €9.640 |
  | Aliquota effettiva | 21.4% |
- Expandable "Mostra dettaglio scaglioni ▼"
- Action options (keyboard navigable, horizontal row):
  [Copia] [Esporta PDF] [Allega a comunicazione]

Integrate seamlessly with existing PratikoAI chat UI.
```

---

### A.6 Prompt 3A: ROI Dashboard (MEDIUM Priority)

```
CONTEXT (from FR-005):
The Dashboard ROI e Analytics shows professionals the value generated by PratikoAI:
- Activity metrics: Query effettuate, Procedure consultate, Documenti analizzati
- Client engagement: Comunicazioni inviate, Tasso apertura (%), Click su CTA, Clienti raggiunti
- Opportunities: Matching effettuati, Clienti identificati, Valore potenziale pratiche
- Time saved: Tempo ricerca risparmiato (Query × 5 min), Tempo comunicazioni risparmiato (× 15 min), Totale ore risparmiate

DESIGN TASK:
Add to the existing PratikoAI Figma design: ROI/analytics dashboard. Use Blu Petrolio (#2A5D67) for charts/metrics, Oro Antico (#D4A574) for highlights/increases, Verde Salvia (#A9C1B7) for success indicators.

MAIN DASHBOARD LAYOUT:
- Header: "Dashboard" with date range picker (Oggi / Settimana / Mese / Anno)
- 4 metric cards in row:
  - "Query effettuate" - 127 (this week) with +12% vs last week
  - "Comunicazioni inviate" - 23 with open rate 68%
  - "Clienti matchati" - 45 with icon
  - "Ore risparmiate" - 8.5h with calculation tooltip

SECTION: ENGAGEMENT CLIENTI
- Chart: Bar chart showing communications sent per week (last 8 weeks)
- Stats below: "Tasso apertura: 68%", "Click su CTA: 34%"

SECTION: OPPORTUNITÀ IDENTIFICATE
- List of recent matches:
  - "Rottamazione Quinquies" - 7 clienti - 2 giorni fa
  - "Bonus Assunzioni Under 30" - 3 clienti - 5 giorni fa
  - "IMU Seconda Casa" - 12 clienti - 1 settimana fa
- "Vedi tutte" link

SECTION: ATTIVITÀ RECENTE (Timeline)
- Timeline items:
  - "Comunicazione inviata a 6 clienti" - 2h fa
  - "Procedura consultata: Apertura P.IVA Artigiano" - ieri
  - "Documento analizzato: Bilancio 2023.pdf" - 2 giorni fa

SECTION: TEMPO RISPARMIATO
- Visual breakdown:
  - Research time saved: 3h (icon: magnifying glass)
  - Communication time saved: 5.5h (icon: envelope)
- "Basato su 127 query e 23 comunicazioni"

Export button: "Scarica Report PDF"

Consistent with existing PratikoAI dashboard styling.
```

---

### A.7 Prompt 3B: Procedure Interattive (MEDIUM Priority)

```
CONTEXT (from FR-001):
"Procedure Interattive" - Step-by-step procedure for complex administrative tasks. Each procedura includes:
- Sezione 1: Checklist Documenti (required vs optional)
- Sezione 2: Modelli da Compilare (form name, ente, link)
- Sezione 3: Timeline Procedurale (day 0, day 0-30, etc.)
- Sezione 4: Costi e Tributi (voce, importo, frequenza)
- Sezione 5: Riferimenti Normativi (L. 443/1985, etc.)
Priority procedures: P001-Apertura artigiano, P002-Apertura commerciale, P004/P005-Pensioni, P006-Assunzione dipendente.

DESIGN TASK:
Add to the existing PratikoAI Figma design: procedure interattive system. Use Blu Petrolio (#2A5D67) for section headers, Verde Salvia (#A9C1B7) for completed/checked items, Oro Antico (#D4A574) for complexity badges, Grigio Tortora (#C4BDB4) for timeline connectors.

SCREEN 1: PROCEDURE LIST
- Header: "Procedure" with search
- Category filter chips: "Tutte", "Apertura Attività", "Pensioni", "Assunzioni", "Adempimenti"
- Procedure cards grid (2 columns):
  - Card contains:
    - Icon (document, briefcase, etc.)
    - Title: "Apertura Attività Artigiano"
    - Subtitle: "Settore Edilizia"
    - Complexity badge: "Alta" (red), "Media" (yellow), "Bassa" (green)
    - "Ultimo aggiornamento: 01/12/2025"
    - Enti coinvolti icons: AdE, CCIAA, INPS, INAIL
- Popular procedure section at top

SCREEN 2: PROCEDURA DETAIL (scrollable single page)
- Header: Title + "Esporta PDF" button
- Progress indicator: "Fase 1 di 5 completata"
- Collapsible sections:

  SECTION 1: CHECKLIST DOCUMENTI
  - Checkbox list:
    - ☑ Documento identità (obbligatorio)
    - ☐ Codice fiscale (obbligatorio)
    - ☐ Attestato qualifica professionale (obbligatorio)
  - Notes icon next to optional items

  SECTION 2: MODELLI DA COMPILARE
  - Cards for each form:
    - "Modello AA9/12" - Agenzia Entrate
    - "Apertura P.IVA" - Link button

  SECTION 3: TIMELINE PROCEDURALE
  - Vertical timeline:
    - Day 0: "Invio Modello AA9/12" ✓
    - Day 0-30: "Iscrizione INPS" (in progress)
    - Day 0-30: "Iscrizione INAIL"

  SECTION 4: COSTI
  - Table: Voce, Importo, Frequenza

  SECTION 5: RIFERIMENTI NORMATIVI
  - List with links: "L. 443/1985 - Legge quadro artigianato"

Sticky footer with keyboard-navigable actions:
  [Salva progressi] [Esporta PDF] [Torna alla lista]

Maintain existing PratikoAI design hierarchy and typography.
```

---

### A.8 Prompt 4: Deadline Calendar & Document Analysis (MEDIUM/LOW Priority)

```
CONTEXT (from FR-006 + FR-008):

FR-006 "Sistema Scadenze Proattivo": Calendar of tax deadlines matched with client database. Pre-configured deadlines: IMU (16 Giugno/Dicembre), IRPEF (30 Giugno/Novembre), IVA trimestrale, F24 mensile, INPS fissi. Each deadline shows number of affected clients. Alerts configurable 30/15/7 days before.

FR-008 "Upload e Analisi Documenti": Upload documents (PDF, XML, JPG, XLSX) for analysis. Supported types: Fattura elettronica XML, Modello F24, CU, 730/Redditi, Bilancio, Busta paga, Visura camerale. IMPORTANT: Documents are NOT saved permanently - processed in-memory only, deleted after session/30min inactivity.

DESIGN TASK:
Add to the existing PratikoAI Figma design: deadline calendar and document analysis. Use Blu Petrolio (#2A5D67) for calendar header, Oro Antico (#D4A574) for urgent deadlines, Verde Salvia (#A9C1B7) for routine items, Avorio (#F8F5F1) for document analysis cards.

SCREEN 1: DEADLINE CALENDAR
- Header: "Scadenze" with month/year selector and view toggle (Calendario/Lista)
- Monthly calendar grid:
  - Days with deadlines have colored dots (red=urgent, yellow=upcoming, blue=routine)
  - Clicking day shows deadline list
- Right sidebar (selected date):
  - Date header: "16 Giugno 2025"
  - Deadline cards:
    - "IMU Acconto" - 12 clienti interessati
    - "F24 Mensile" - 8 clienti interessati
  - "Crea comunicazione" button for each

SCREEN 2: DEADLINE DETAIL
- Header: "IMU Acconto - 16 Giugno 2025"
- Alert config: "Avvisami" dropdown (30/15/7 giorni prima)
- Client list matching this deadline
- Quick action: "Prepara comunicazione per tutti"

SCREEN 3: DOCUMENT UPLOAD
- Drag-drop zone: "Trascina un documento o clicca per sfogliare"
- Supported formats: PDF, XML, JPG, PNG, XLSX (max 10MB)
- Recent uploads list below
- Privacy notice: "I documenti vengono elaborati in tempo reale e non salvati."

SCREEN 4: DOCUMENT ANALYSIS RESULT
- Header: Detected document type badge "Fattura Elettronica XML"
- Summary card:
  - Fornitore: ABC SRL
  - Data: 15/12/2025
  - Imponibile: €1.500,00
  - IVA 22%: €330,00
  - Totale: €1.830,00
- Expandable "Dettaglio completo ▼"
- Action options (keyboard navigable):
  ● Fai una domanda su questo documento
    Usa l'AI per analizzare specifici aspetti
  ○ Esporta analisi (PDF)
  ○ Carica altro documento

Consistent with existing PratikoAI design system.
```

---

### A.9 Next Steps After Design

1. Generate UI screenshots in Figma using these prompts
2. Save screenshots to `docs/ui/` directory (create if needed)
3. Update relevant frontend tasks in PRATIKO_2.0.md with `**UI Reference:** docs/ui/<screenshot>.png`
4. Prioritize HIGH priority prompts (A.3-A.5) for immediate generation
