'use client';

import { INTENT_DISPLAY_NAMES, INTENT_COLORS } from '@/types/intentLabeling';

/**
 * Detailed intent guide for each classification category.
 * Shows examples, system consequences, and disambiguation tips.
 */

interface IntentDetail {
  intent: string;
  examples: string[];
  consequences: string[];
  tip?: string;
}

const INTENT_DETAILS: IntentDetail[] = [
  {
    intent: 'chitchat',
    examples: [
      'Ciao, come stai?',
      'Che tempo fa oggi?',
      'Grazie mille, sei stato gentile',
      'Chi sei?',
      'Perfetto, grazie!',
    ],
    consequences: [
      'Il sistema NON cerca documenti nella base di conoscenza',
      "L'assistente risponde direttamente con una risposta breve e conversazionale",
      'Non vengono suggerite azioni successive',
      'È la categoria più leggera: risposta immediata, costo zero per la ricerca',
    ],
  },
  {
    intent: 'theoretical_definition',
    examples: [
      "Cos'è il regime forfettario?",
      "Che differenza c'è tra IRPEF e IRES?",
      'Cosa si intende per ammortamento?',
      'Spiegami cosa sono i contributi previdenziali',
      'Definizione di reddito imponibile',
    ],
    consequences: [
      'Il sistema CERCA documenti nella base di conoscenza per dare una risposta accurata',
      'La ricerca usa un mix di ricerca testuale, semantica e documenti recenti',
      "La risposta viene generata dall'AI combinando i documenti trovati",
      'Vengono suggerite azioni di approfondimento (es. "Vuoi sapere come si applica?")',
    ],
  },
  {
    intent: 'technical_research',
    examples: [
      "Qual è l'iter per aprire una P.IVA forfettaria?",
      "Come si compila il modello F24 per il versamento dell'IVA?",
      'Quali sono i requisiti per accedere alla Legge 104?',
      'Entro quando devo presentare la dichiarazione dei redditi?',
      'Un mio cliente ha ricevuto un accertamento fiscale, come procedere?',
    ],
    consequences: [
      'Il sistema esegue una RICERCA APPROFONDITA nella base di conoscenza (ricerca ibrida completa)',
      'Vengono cercati documenti normativi, guide pratiche e precedenti',
      "L'AI genera una risposta dettagliata e strutturata con riferimenti alle fonti",
      'Vengono suggerite azioni pratiche (es. "Genera un promemoria", "Crea una checklist")',
    ],
    tip: 'In caso di dubbio tra Definizione Teorica e Ricerca Tecnica, scegliete Ricerca Tecnica. È la scelta più sicura perché attiva la ricerca completa.',
  },
  {
    intent: 'calculator',
    examples: [
      "Calcola l'IVA su 1.000 euro",
      'Quanto IRPEF pago su un reddito di 35.000 euro?',
      'Calcola il ravvedimento operoso per un F24 scaduto il 16 marzo',
      'Quanto vengono i contributi INPS per un artigiano con 50.000 di reddito?',
      'Se fatturo 80.000 euro in forfettario, quanto pago di tasse?',
    ],
    consequences: [
      'Il sistema NON cerca documenti (la risposta viene calcolata, non cercata)',
      'Il sistema verifica se ha tutti i dati necessari per il calcolo',
      'Se MANCANO informazioni → vengono fatte domande interattive all\'utente (es. "Che tipo di contribuente sei?")',
      'Se ha TUTTI i dati → procede direttamente al calcolo',
      'Calcoli supportati: IRPEF, IVA, contributi INPS, ravvedimento operoso, F24',
    ],
    tip: 'Se l\'utente chiede "Come si calcola l\'IRPEF?" (senza numeri), è una Definizione Teorica, NON un Calcolatore. La differenza: spiegare come funziona vs. eseguire il calcolo con numeri.',
  },
  {
    intent: 'normative_reference',
    examples: [
      "Cosa prevede l'Art. 18 dello Statuto dei Lavoratori?",
      'Spiegami la Legge 104/92',
      "Cosa dice il TUIR all'articolo 67?",
      'Circolare AdE 7/E del 2024 sulle detrazioni',
      'Decreto legislativo 81/2008 sulla sicurezza sul lavoro',
    ],
    consequences: [
      'Il sistema esegue una RICERCA MIRATA nella base di conoscenza, focalizzata sulla normativa citata',
      'Vengono estratte automaticamente le entità dalla domanda (legge, articolo, ente, data)',
      'La risposta include citazioni precise e riferimenti normativi',
      'Vengono suggerite azioni come "Mostra il testo completo" o "Articoli correlati"',
    ],
    tip: "Se l'utente CITA una norma specifica (numero, nome, articolo), è Riferimento Normativo. Se fa una domanda generica su un tema SENZA citare norme, è Ricerca Tecnica.",
  },
];

export function IntentGuideDetails() {
  return (
    <div className="space-y-4">
      {INTENT_DETAILS.map((detail, idx) => {
        const color =
          INTENT_COLORS[detail.intent as keyof typeof INTENT_COLORS];
        const label =
          INTENT_DISPLAY_NAMES[
            detail.intent as keyof typeof INTENT_DISPLAY_NAMES
          ];

        return (
          <div
            key={detail.intent}
            className="rounded-lg border border-gray-200 overflow-hidden"
          >
            {/* Header */}
            <div
              className="flex items-center gap-2 px-3 py-2"
              style={{ backgroundColor: `${color}10` }}
            >
              <span
                className="flex-shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-full text-white text-[10px] font-bold"
                style={{ backgroundColor: color }}
              >
                {idx + 1}
              </span>
              <span className="font-semibold text-gray-900">{label}</span>
              <code className="text-[10px] text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded font-mono">
                {detail.intent}
              </code>
            </div>

            <div className="px-3 py-2.5 space-y-2.5">
              {/* Examples */}
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                  Esempi
                </p>
                <ul className="space-y-0.5">
                  {detail.examples.map(ex => (
                    <li
                      key={ex}
                      className="text-xs text-gray-700 flex items-start gap-1.5"
                    >
                      <span className="text-gray-400 mt-px">&bull;</span>
                      <span>&ldquo;{ex}&rdquo;</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Consequences */}
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                  Cosa succede nel sistema
                </p>
                <ul className="space-y-0.5">
                  {detail.consequences.map(c => (
                    <li
                      key={c}
                      className="text-xs text-gray-700 flex items-start gap-1.5"
                    >
                      <span className="text-gray-400 mt-px">→</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Tip */}
              {detail.tip && (
                <div className="bg-amber-50 border border-amber-200 rounded px-2.5 py-2 text-xs text-amber-800">
                  <strong>Attenzione:</strong> {detail.tip}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
