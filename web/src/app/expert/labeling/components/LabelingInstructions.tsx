'use client';

import { useState } from 'react';
import {
  INTENT_DISPLAY_NAMES,
  INTENT_COLORS,
  INTENT_LABELS,
} from '@/types/intentLabeling';

export function LabelingInstructions() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm mb-6">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors rounded-lg"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">📖</span>
          <span className="text-sm font-medium text-gray-900">
            Guida al sistema di etichettatura
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-5 text-sm text-gray-700 border-t border-gray-100">
          {/* Scopo */}
          <section className="pt-4">
            <h3 className="font-semibold text-gray-900 mb-2">
              Scopo di questa pagina
            </h3>
            <p>
              Questa pagina raccoglie le query degli utenti che il
              classificatore automatico (mDeBERTa) non riesce a classificare con
              sufficiente sicurezza (confidenza &lt; 70%). Il tuo compito come
              esperto è assegnare l&apos;intento corretto a ciascuna query,
              creando dati di addestramento per migliorare il modello.
            </p>
          </section>

          {/* Pipeline */}
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">
              Come funziona la pipeline
            </h3>
            <div className="bg-gray-50 rounded-lg p-3 space-y-1 font-mono text-xs text-gray-600">
              <p>1. L&apos;utente invia una domanda a Pratiko</p>
              <p>
                2. Il modello mDeBERTa classifica l&apos;intento (gratis,
                locale, ~100ms)
              </p>
              <p>
                3. Se la confidenza è ≥ 70% → il risultato viene usato
                direttamente
              </p>
              <p>
                4. Se la confidenza è &lt; 70% → la query finisce in questa coda
                + si usa GPT come fallback
              </p>
              <p>
                5. L&apos;esperto etichetta l&apos;intento corretto (questa
                pagina)
              </p>
              <p>
                6. I dati etichettati vengono esportati ed usati per il
                fine-tuning del modello
              </p>
              <p>
                7. Il modello aggiornato classifica meglio → meno fallback su
                GPT → meno costi
              </p>
            </div>
          </section>

          {/* Intenti */}
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">
              Categorie di intento
            </h3>
            <p className="mb-3">
              Ogni query deve essere classificata in una delle seguenti
              categorie. Puoi usare i tasti{' '}
              <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs font-mono">
                1
              </kbd>
              –
              <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs font-mono">
                5
              </kbd>{' '}
              come scorciatoia.
            </p>
            <div className="space-y-2">
              {INTENT_LABELS.map((intent, index) => {
                const color = INTENT_COLORS[intent];
                const label = INTENT_DISPLAY_NAMES[intent];
                const descriptions: Record<string, string> = {
                  chitchat:
                    'Conversazione casuale, saluti, domande fuori tema. Es: "Ciao, come stai?", "Che tempo fa?"',
                  theoretical_definition:
                    'Richiesta di definizione o spiegazione teorica. Es: "Cos\'è il TFR?", "Cosa si intende per CCNL?"',
                  technical_research:
                    'Domanda tecnica complessa che richiede ricerca approfondita. Es: "Come si calcola l\'indennità di licenziamento con 15 anni di anzianità?"',
                  calculator:
                    'Richiesta di calcolo numerico (tasse, contributi, stipendi). Es: "Calcola l\'IVA su 1000€", "Quanto pago di IRPEF su 30.000€?"',
                  normative_reference:
                    'Riferimento specifico a legge, articolo o normativa. Es: "Cosa dice la Legge 104?", "Art. 18 dello Statuto dei Lavoratori"',
                };

                return (
                  <div
                    key={intent}
                    className="flex items-start gap-3 p-2 rounded-md bg-gray-50"
                  >
                    <span
                      className="mt-0.5 flex-shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-full text-white text-[10px] font-bold"
                      style={{ backgroundColor: color }}
                    >
                      {index + 1}
                    </span>
                    <div>
                      <span className="font-medium text-gray-900">{label}</span>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {descriptions[intent]}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Predizione */}
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">
              Come leggere la &quot;Predizione&quot;
            </h3>
            <p>
              Ogni scheda mostra la <strong>predizione</strong> del modello
              mDeBERTa: l&apos;intento che il classificatore ritiene più
              probabile, con il relativo punteggio di confidenza. Viene anche
              mostrata la distribuzione dei punteggi su tutte le 5 categorie.
              Una confidenza bassa (es. 0.35) indica che il modello è molto
              incerto — il tuo contributo in questi casi è particolarmente
              prezioso.
            </p>
          </section>

          {/* Consigli */}
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">
              Consigli per l&apos;etichettatura
            </h3>
            <ul className="space-y-1.5 list-disc list-inside text-gray-600">
              <li>Leggi attentamente l&apos;intera query prima di scegliere</li>
              <li>
                Se la query contiene un riferimento normativo specifico (legge,
                articolo, decreto), scegli{' '}
                <strong>Riferimento Normativo</strong> anche se chiede una
                spiegazione
              </li>
              <li>
                Se la query chiede un calcolo numerico esplicito, scegli{' '}
                <strong>Calcolatore</strong>
              </li>
              <li>
                Usa il campo &quot;Note&quot; per segnalare query ambigue o casi
                particolari
              </li>
              <li>
                Se una query è davvero inclassificabile, usa il pulsante{' '}
                <strong>Salta</strong> — ci penserà un altro esperto
              </li>
            </ul>
          </section>

          {/* Fine-tuning */}
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">
              Fine-tuning del modello
            </h3>
            <p>
              I dati etichettati vengono esportati tramite il pulsante
              &quot;Esporta&quot; in alto a destra (formato JSONL). Ogni
              esportazione include <strong>tutti</strong> i dati etichettati
              (sicuro per il retraining completo). Il badge verde sul pulsante
              indica quante nuove etichette sono state aggiunte dall&apos;ultima
              esportazione; dopo l&apos;esportazione il contatore si azzera. Si
              raccomandano almeno 200 esempi etichettati per categoria per
              ottenere risultati significativi. Con ogni ciclo di fine-tuning,
              il modello diventa più accurato e si riduce la dipendenza da GPT
              (e i relativi costi).
            </p>
          </section>
        </div>
      )}
    </div>
  );
}
