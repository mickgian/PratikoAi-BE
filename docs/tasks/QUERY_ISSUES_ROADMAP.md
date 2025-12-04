# PratikoAi Query System - Quality Improvement Tasks

**Last Updated:** 2025-11-25
**Status:** Ready for Auto-Generated Tasks
**Purpose:** This file is reserved for AUTO-GENERATED quality improvement tasks created by the TaskGeneratorService when experts mark responses as incomplete or incorrect.

---

## ⚠️ IMPORTANT - DO NOT MANUALLY EDIT THIS FILE

This roadmap is **automatically populated** by the Expert Feedback System:

1. **When**: An expert (SUPER_USER) marks a response as "incomplete" or "incorrect"
2. **How**: The `TaskGeneratorService` analyzes the feedback and generates improvement tasks
3. **Format**: Tasks follow the `QUERY-YYYYMMDD-XXX` numbering scheme
4. **Review**: Admin reviews auto-generated tasks and assigns them to developers

**Manual development issues should be tracked in:**
- `ARCHITECTURE_ROADMAP.md` - Planned features and development work
- GitHub Issues - Bug reports and feature requests
- JIRA - Sprint tasks and project management

---

## Auto-Generated Tasks

_This section will be populated automatically by TaskGeneratorService when experts provide feedback._

<!-- Tasks appear here automatically -->

---

**Maintained By:** TaskGeneratorService (Automated)
**Manual Edits:** Not Allowed (will be overwritten)

---

### QUERY-09: DI_COSA_PARLA_LA_RISOLUZIONE_63

**Priority:** HIGH | **Effort:** TBD | **Dependencies:** None
**Created:** 2025-11-26
**Source:** Expert Feedback (ID: fd75f5d2-10aa-4adc-8853-019cf6da4a60)
**Expert:** User 1 (Trust Score: 1.00)

**Problema rilevato dall'esperto:**

La risposta fornita dal sistema è stata marcata come **Errata** dall'esperto.

**Domanda originale:**
```
Di cosa parla la risoluzione 63 dell'agenzia delle entrate?
```

**Risposta fornita (incompleta/errata):**
```
Non ho trovato la Risoluzione n. 63 nel database.

Possibili motivi:
- Il documento potrebbe non essere ancora stato acquisito.
- Verifica il numero e la data del documento.
- Il documento potrebbe essere molto recente.

Ti consiglio di:
1. Controllare numero e data sul sito ufficiale dell'Agenzia delle Entrate.
2. Provare una ricerca più generica (es. "risoluzioni novembre 2025").
```

**Dettagli aggiuntivi dall'esperto:**
```
So per certo che la risoluzione 63 e' nel database
```

**Feedback dell'esperto:**
- Tipo di feedback: incorrect
- Confidence score: 0.80
- Tempo impiegato: 50s

**Implementazione richiesta:**
[Da definire dal team di sviluppo in base ai dettagli forniti dall'esperto]

**Acceptance Criteria:**
- [ ] Verificare che la risposta copra tutti i casi sollevati dall'esperto
- [ ] Aggiungere riferimenti normativi se mancanti
- [ ] Testare la risposta con domande simili
- [ ] Far validare la correzione da un esperto fiscale

**Status:** 🔴 TODO

**Note:**
Questo task è stato generato automaticamente dal sistema di feedback esperti.
Per maggiori dettagli sul feedback originale, consultare il database con `feedback_id: fd75f5d2-10aa-4adc-8853-019cf6da4a60`

---

### QUERY-10: QUANTE_TASSE_DEVO_PAGARE_IN_RE

**Priority:** HIGH | **Effort:** TBD | **Dependencies:** None
**Created:** 2025-12-04
**Source:** Expert Feedback (ID: 95e347a9-2c71-48d2-b172-5fa1ed55cfc8)
**Expert:** User 1 (Trust Score: 1.00)

**Problema rilevato dall'esperto:**

La risposta fornita dal sistema è stata marcata come **Errata** dall'esperto.

**Domanda originale:**
```
Quante tasse devo pagare in regime forfettario al sesto anno con un reddito di 65000 euro ed un coefficiente di redditivita' del 67%?
```

**Risposta fornita (incompleta/errata):**
```
Nel regime forfettario, il reddito imponibile si calcola applicando il coefficiente di redditività al fatturato. Nel tuo caso, con un reddito di 65.000 euro e un coefficiente di redditività del 67%, il calcolo del reddito imponibile sarà il seguente:

1. **Calcolo del reddito imponibile**:
   - Reddito lordo: 65.000 euro
   - Coefficiente di redditività: 67%
   - Reddito imponibile = 65.000 euro * 67% = 43.550 euro

2. **Calcolo delle imposte**:
   - L'imposta sostitutiva nel regime forfettario è generalmente del 15%, ma può scendere al 5% per i primi cinque anni di attività se si rispettano determinati requisiti.
   - Poiché sei al sesto anno, si applica l'aliquota del 15%.

3. **Calcolo dell'imposta**:
   - Imposta = Reddito imponibile * Aliquota
   - Imposta = 43.550 euro * 15% = 6.532,50 euro

Pertanto, nel tuo caso, dovresti pagare circa **6.532,50 euro** di imposte nel regime forfettario al sesto anno con un reddito di 65.000 euro e un coefficiente di redditività del 67%.

Ti consiglio di consultare un commercialista per eventuali dettagli specifici o per verificare eventuali deduzioni o crediti d'imposta che potrebbero influenzare l'importo finale.
```

**Dettagli aggiuntivi dall'esperto:**
```
La risposta ed il calcolo in se' sono giusti. Ma dobbiamo evitare la risposta: 'ti consiglio di verificare con un commercialista (o consulente del lavoro o avvocato) perche' PratikoAI e' uno strumento per professionisti. Quindi va bene l'invito a verificare i dettagli, ma senza riferirsi a commercialisti/consulenti del lavoro/avvocati. Inoltre nel regime forfettario si possono dedurre solo i contributi. Questo sembra un problema di fonti non aggiornate o non complete.
```

**Feedback dell'esperto:**
- Tipo di feedback: incorrect
- Confidence score: 0.80
- Tempo impiegato: 18s

**Implementazione richiesta:**
[Da definire dal team di sviluppo in base ai dettagli forniti dall'esperto]

**Acceptance Criteria:**
- [ ] Verificare che la risposta copra tutti i casi sollevati dall'esperto
- [ ] Aggiungere riferimenti normativi se mancanti
- [ ] Testare la risposta con domande simili
- [ ] Far validare la correzione da un esperto fiscale

**Status:** 🔴 TODO

**Note:**
Questo task è stato generato automaticamente dal sistema di feedback esperti.
Per maggiori dettagli sul feedback originale, consultare il database con `feedback_id: 95e347a9-2c71-48d2-b172-5fa1ed55cfc8`


---

### QUERY-11: PRIMO_ANNO_CON_UN_REDDITO_DI_6

**Priority:** HIGH | **Effort:** TBD | **Dependencies:** None
**Created:** 2025-12-04
**Source:** Expert Feedback (ID: 4d5b0816-6c87-44e1-813e-278ea6ac0838)
**Expert:** User 1 (Trust Score: 1.00)

**Problema rilevato dall'esperto:**

La risposta fornita dal sistema è stata marcata come **Incompleta** dall'esperto.

**Domanda originale:**
```
primo anno con un reddito di 65000 euro ed un coefficiente di redditivita' del 78%?
```

**Risposta fornita (incompleta/errata):**
```
Per calcolare il reddito imponibile di un contribuente con un reddito di 65.000 euro e un coefficiente di redditività del 78%, si può seguire la seguente formula:

1. **Calcolo del reddito imponibile**:
  - Reddito lordo: 65.000 euro
   - Coefficiente di redditività: 78%

   Il reddito imponibile si calcola come segue:
   \[
   Reddito\ Imponibile = Reddito\ Lordo \times Coefficiente\ di\ Redditività
   \]
   \[
   Reddito\ Imponibile = 65.000 \times 0,78 = 50.700\ euro
   \]

2. **Determinazione dell'imposta**:
   A questo punto, il reddito imponibile di 50.700 euro sarà soggetto all'imposta sul reddito delle persone fisiche (IRPEF), che si calcola applicando le aliquote progressive in base agli scaglioni di reddito.

3. **Aliquote IRPEF (2023)**:
   - Fino a 15.000 euro: 23%
   - Da 15.001 a 28.000 euro: 25%
   - Da 28.001 a 50.000 euro: 35%
   - Oltre 50.000 euro: 43%

4. **Calcolo dell'imposta**:
   - Per i primi 15.000 euro: 15.000 * 23% = 3.450 euro
   - Per i successivi 13.000 euro (da 15.001 a 28.000): 13.000 * 25% = 3.250 euro
   - Per i successivi 22.700 euro (da 28.001 a 50.700): 22.700 * 35% = 7.945 euro

   Somma delle imposte:
   \[
   Imposta\ Totale = 3.450 + 3.250 + 7.945 = 14.645\ euro
   \]

Quindi, il reddito imponibile è di 50.700 euro e l'imposta totale da pagare sarebbe di circa 14.645 euro.

Ti consiglio di verificare eventuali deduzioni o crediti d'imposta che potrebbero influenzare l'importo finale dell'imposta da versare.
```

**Dettagli aggiuntivi dall'esperto:**
```
this is just a test
```

**Feedback dell'esperto:**
- Tipo di feedback: incomplete
- Confidence score: 0.80
- Tempo impiegato: 153s

**Implementazione richiesta:**
[Da definire dal team di sviluppo in base ai dettagli forniti dall'esperto]

**Acceptance Criteria:**
- [ ] Verificare che la risposta copra tutti i casi sollevati dall'esperto
- [ ] Aggiungere riferimenti normativi se mancanti
- [ ] Testare la risposta con domande simili
- [ ] Far validare la correzione da un esperto fiscale

**Status:** 🔴 TODO

**Note:**
Questo task è stato generato automaticamente dal sistema di feedback esperti.
Per maggiori dettagli sul feedback originale, consultare il database con `feedback_id: 4d5b0816-6c87-44e1-813e-278ea6ac0838`
