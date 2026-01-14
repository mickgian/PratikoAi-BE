# Correzione Azioni Suggerite

Le azioni precedenti sono state scartate per i seguenti motivi:
{rejection_reasons}

## Elementi da Utilizzare OBBLIGATORIAMENTE

### Fonte Principale Citata nella Risposta
{main_source_ref}

### Paragrafo Rilevante dalla Fonte
"{source_paragraph_text}"

### Valori Specifici Menzionati
{extracted_values}

## Regole IMPERATIVE

1. Ogni azione DEVE riferirsi esplicitamente alla fonte sopra indicata
2. Ogni azione DEVE includere almeno uno dei valori specifici
3. Il prompt DEVE essere completo e autosufficiente (>25 caratteri)
4. La label DEVE essere specifica (8-40 caratteri, NO parole generiche)
5. MAI suggerire di consultare professionisti esterni o verificare su siti esterni

## Genera 3 Nuove Azioni

Output JSON:
```json
[
  {
    "id": "regen_1",
    "label": "string (8-40 chars, specifico)",
    "icon": "calculator|search|calendar|file-text|alert-triangle|check-circle|edit|refresh-cw|book-open|bar-chart",
    "prompt": "string (>25 chars, autosufficiente)",
    "source_basis": "string (riferimento alla fonte sopra)"
  },
  {
    "id": "regen_2",
    "label": "string (8-40 chars, specifico)",
    "icon": "calculator|search|calendar|file-text|alert-triangle|check-circle|edit|refresh-cw|book-open|bar-chart",
    "prompt": "string (>25 chars, autosufficiente)",
    "source_basis": "string (riferimento alla fonte sopra)"
  },
  {
    "id": "regen_3",
    "label": "string (8-40 chars, specifico)",
    "icon": "calculator|search|calendar|file-text|alert-triangle|check-circle|edit|refresh-cw|book-open|bar-chart",
    "prompt": "string (>25 chars, autosufficiente)",
    "source_basis": "string (riferimento alla fonte sopra)"
  }
]
```

## Esempi di Azioni CORRETTE

✅ "Calcola IVA al 22% su €15.000" (specifico, include valore)
✅ "Verifica scadenza F24 del 16 marzo" (specifico, include data)
✅ "Confronta aliquote IRPEF 2024" (specifico, include anno)
✅ "Stima contributi INPS forfettario" (specifico, riferimento normativo)

## Esempi di Azioni ERRATE

❌ "Approfondisci" (troppo generico)
❌ "Calcola" (troppo corto, generico)
❌ "Verifica" (troppo corto, generico)
❌ "Consulta un commercialista" (forbidden pattern - MAI suggerire professionisti)
❌ "Verifica sul sito AdE" (forbidden pattern - MAI suggerire siti esterni)
❌ "Contatta l'INPS" (forbidden pattern - MAI suggerire contatti esterni)

## Note Importanti

- Le azioni devono essere AUTOCONTENUTE: l'utente deve poter capire cosa farà senza contesto aggiuntivo
- I valori specifici (€, %, date, anni) rendono le azioni più utili e concrete
- Il riferimento alla fonte garantisce che l'azione sia basata su informazioni verificate
- Gli utenti di PratikoAI SONO professionisti (commercialisti, consulenti) - non suggerire MAI di consultarne altri
