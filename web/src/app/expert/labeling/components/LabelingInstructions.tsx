'use client';

import { useState } from 'react';
import { IntentGuideDetails } from './IntentGuideDetails';

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
            Guida completa alla classificazione degli intenti
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
          {/* Cos'è la classificazione */}
          <section className="pt-4">
            <h3 className="font-semibold text-gray-900 mb-2">
              Cos&apos;è la classificazione degli intenti?
            </h3>
            <p>
              Quando un utente scrive una domanda a PratikoAI, il sistema deve
              capire <strong>che tipo di domanda è</strong> prima di poter
              rispondere. Questo passaggio si chiama &quot;classificazione
              dell&apos;intento&quot;. Un modello automatico prova a
              classificare ogni domanda, ma quando non è sicuro (confidenza
              sotto il 70%), la query finisce in questa coda per la{' '}
              <strong>revisione umana</strong>.
            </p>
            <p className="mt-2">
              I dati che etichettate servono per addestrare un modello locale
              che diventi sempre più preciso, riducendo i costi e migliorando la
              velocità del sistema.
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

          {/* Categorie con dettagli completi */}
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">
              Le 5 categorie di intento — dettaglio completo
            </h3>
            <p className="mb-3">
              Ogni query deve essere classificata in una delle seguenti
              categorie. Per ciascuna sono indicati esempi, cosa succede nel
              sistema dopo la classificazione, e suggerimenti per i casi
              ambigui. Puoi usare i tasti{' '}
              <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs font-mono">
                1
              </kbd>
              –
              <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs font-mono">
                5
              </kbd>{' '}
              come scorciatoia.
            </p>
            <IntentGuideDetails />
          </section>

          {/* Tabella riassuntiva */}
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">
              Tabella riassuntiva rapida
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="text-left px-2 py-1.5 border border-gray-200 font-semibold text-gray-700">
                      Intento
                    </th>
                    <th className="text-left px-2 py-1.5 border border-gray-200 font-semibold text-gray-700">
                      Parola chiave
                    </th>
                    <th className="text-left px-2 py-1.5 border border-gray-200 font-semibold text-gray-700">
                      Cerca documenti?
                    </th>
                    <th className="text-left px-2 py-1.5 border border-gray-200 font-semibold text-gray-700">
                      Esempio tipico
                    </th>
                  </tr>
                </thead>
                <tbody className="text-gray-600">
                  <tr>
                    <td className="px-2 py-1.5 border border-gray-200 font-medium">
                      Chiacchierata
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      Saluto, fuori tema
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200 text-red-600 font-medium">
                      No
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      &ldquo;Ciao!&rdquo;
                    </td>
                  </tr>
                  <tr className="bg-gray-50/50">
                    <td className="px-2 py-1.5 border border-gray-200 font-medium">
                      Definizione Teorica
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      &ldquo;Cos&apos;è...&rdquo;, &ldquo;Spiega...&rdquo;
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200 text-green-600 font-medium">
                      Sì
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      &ldquo;Cos&apos;è il forfettario?&rdquo;
                    </td>
                  </tr>
                  <tr>
                    <td className="px-2 py-1.5 border border-gray-200 font-medium">
                      Ricerca Tecnica
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      &ldquo;Come faccio...&rdquo;, caso pratico
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200 text-green-600 font-medium">
                      Sì (completa)
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      &ldquo;Come apro P.IVA?&rdquo;
                    </td>
                  </tr>
                  <tr className="bg-gray-50/50">
                    <td className="px-2 py-1.5 border border-gray-200 font-medium">
                      Calcolatore
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      &ldquo;Calcola...&rdquo;, numeri, importi
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200 text-red-600 font-medium">
                      No (calcola)
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      &ldquo;IVA su 1.000€?&rdquo;
                    </td>
                  </tr>
                  <tr>
                    <td className="px-2 py-1.5 border border-gray-200 font-medium">
                      Riferimento Normativo
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      Legge X, Art. Y, Decreto Z
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200 text-green-600 font-medium">
                      Sì (mirata)
                    </td>
                    <td className="px-2 py-1.5 border border-gray-200">
                      &ldquo;Art. 18 Statuto Lavoratori&rdquo;
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Casi frequenti */}
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">
              Casi frequenti e come risolverli
            </h3>
            <div className="space-y-2">
              <div className="bg-gray-50 rounded-lg p-2.5">
                <p className="font-medium text-gray-800 text-xs mb-0.5">
                  Domanda breve senza contesto (es. &ldquo;e
                  l&apos;IRAP?&rdquo;)
                </p>
                <p className="text-xs text-gray-600">
                  Sono <strong>domande di follow-up</strong>. Classificatele in
                  base a cosa sembra chiedere l&apos;utente. Il sistema le
                  riconoscerà comunque come follow-up e attiverà la ricerca
                  automaticamente.
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-2.5">
                <p className="font-medium text-gray-800 text-xs mb-0.5">
                  Domanda mista (es. &ldquo;Cos&apos;è l&apos;IRPEF e quanto
                  pago su 30.000€?&rdquo;)
                </p>
                <p className="text-xs text-gray-600">
                  Prevale la componente operativa. In questo caso{' '}
                  <strong>Calcolatore</strong> perché c&apos;è una richiesta di
                  calcolo esplicita con un importo.
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-2.5">
                <p className="font-medium text-gray-800 text-xs mb-0.5">
                  Domanda vaga (es. &ldquo;Ho un problema con le tasse&rdquo;)
                </p>
                <p className="text-xs text-gray-600">
                  Classificate come <strong>Ricerca Tecnica</strong>. In caso di
                  dubbio, è sempre la scelta più sicura.
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-2.5">
                <p className="font-medium text-gray-800 text-xs mb-0.5">
                  Ringraziamento dopo una risposta (es. &ldquo;Perfetto,
                  grazie!&rdquo;)
                </p>
                <p className="text-xs text-gray-600">
                  Classificate come <strong>Chiacchierata</strong>.
                </p>
              </div>
            </div>
          </section>

          {/* Conseguenze di errori */}
          <section>
            <h3 className="font-semibold text-gray-900 mb-2">
              Perché la vostra classificazione è importante
            </h3>
            <p className="mb-2">
              Ogni etichetta che assegnate viene usata per addestrare il modello
              locale. Un&apos;etichetta sbagliata ha conseguenze concrete:
            </p>
            <div className="space-y-1.5">
              <div className="flex items-start gap-2 text-xs">
                <span className="text-red-500 mt-0.5 flex-shrink-0">✗</span>
                <span>
                  <strong>Ricerca Tecnica → Chiacchierata:</strong>{' '}
                  l&apos;utente riceverà una risposta superficiale senza ricerca
                  documentale, quindi potenzialmente sbagliata o incompleta
                </span>
              </div>
              <div className="flex items-start gap-2 text-xs">
                <span className="text-red-500 mt-0.5 flex-shrink-0">✗</span>
                <span>
                  <strong>Chiacchierata → Ricerca Tecnica:</strong> il sistema
                  sprecherà risorse cercando documenti per un semplice
                  &ldquo;Ciao&rdquo;, rendendo la risposta più lenta e costosa
                </span>
              </div>
              <div className="flex items-start gap-2 text-xs">
                <span className="text-red-500 mt-0.5 flex-shrink-0">✗</span>
                <span>
                  <strong>Calcolatore → Definizione Teorica:</strong>{' '}
                  l&apos;utente non riceverà il calcolo numerico ma una
                  spiegazione teorica e dovrà riformulare la domanda
                </span>
              </div>
              <div className="flex items-start gap-2 text-xs">
                <span className="text-red-500 mt-0.5 flex-shrink-0">✗</span>
                <span>
                  <strong>Rif. Normativo → Ricerca Tecnica:</strong> funzionerà
                  comunque (la ricerca si attiva), ma sarà meno precisa perché
                  non focalizzata sulla normativa specifica
                </span>
              </div>
            </div>
            <div className="mt-2 bg-green-50 border border-green-200 rounded px-2.5 py-2 text-xs text-green-800">
              <strong>Regola d&apos;oro:</strong> in caso di dubbio, scegliete{' '}
              <strong>Ricerca Tecnica</strong>. È la categoria più
              &quot;sicura&quot; perché attiva la ricerca completa e non
              impedisce nessuna funzionalità.
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
                Se la query chiede un calcolo numerico esplicito con importi,
                scegli <strong>Calcolatore</strong>. Se chiede solo come si
                calcola qualcosa (senza numeri), scegli{' '}
                <strong>Definizione Teorica</strong>
              </li>
              <li>
                In caso di dubbio, scegli sempre{' '}
                <strong>Ricerca Tecnica</strong> — è la scelta più sicura
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
