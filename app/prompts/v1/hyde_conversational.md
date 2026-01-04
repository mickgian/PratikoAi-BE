# HyDE Conversazionale - Generazione Documento Ipotetico

## Obiettivo
Genera un documento ipotetico che risponda alla query corrente dell'utente, considerando il contesto completo della conversazione precedente.

## Contesto Conversazione

{conversation_history}

---

## Query Corrente

{current_query}

---

## Istruzioni per la Generazione

### 1. Analisi del Contesto
Prima di generare il documento, analizza attentamente:
- **Argomenti discussi**: Quali temi fiscali/normativi sono stati trattati nella conversazione?
- **Entità menzionate**: Quali leggi, aliquote, scadenze o concetti sono stati citati?
- **Domande precedenti**: Cosa ha chiesto l'utente in precedenza?

### 2. Risoluzione dei Riferimenti Impliciti
Se la query contiene **pronomi o riferimenti impliciti**, risolvili usando il contesto:
- **"questo", "quello", "esso"** → Identifica a cosa si riferisce dalla conversazione
- **"E per..."**, "E se..."** → Collega al tema precedente
- **"invece", "anche", "pure"** → Estendi o confronta con il contesto
- **"la stessa cosa"**, "come prima"** → Riprendi il concetto discusso

### 3. Generazione del Documento Ipotetico
Genera un documento che:
1. **Risponda direttamente** alla query corrente
2. **Sia coerente** con il contesto della conversazione
3. **Contenga informazioni** che sarebbero utili per una ricerca vettoriale
4. **Usi terminologia tecnica** italiana appropriata per il dominio fiscale/legale

### 4. Formato del Documento
Il documento ipotetico deve:
- Essere scritto come se fosse un estratto di un documento normativo o di prassi
- Contenere i termini chiave rilevanti per la query
- Essere di lunghezza moderata (150-300 parole circa)
- Non includere speculazioni, solo informazioni concrete

---

## Formato Output

Genera SOLO il documento ipotetico, senza prefissi o suffissi.
Il documento deve iniziare direttamente con il contenuto informativo.

**Esempio di formato corretto:**
```
L'aliquota IVA applicabile ai beni alimentari di prima necessità è del 4%...
```

**Esempio di formato NON corretto:**
```
Ecco il documento ipotetico:
L'aliquota IVA applicabile...
```

---

## Documento Ipotetico
