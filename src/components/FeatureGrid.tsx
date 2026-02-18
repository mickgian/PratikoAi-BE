import { RefreshCw, FileText, Zap, Shield, TrendingDown } from "lucide-react";

export function FeatureGrid() {
  return (
    <section id="features" className="py-20 lg:py-32 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold text-gray-900 mb-6">
            Tutto quello che serve al tuo studio
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Una piattaforma completa per rimanere sempre aggiornati sulle
            normative fiscali italiane
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Large Card - Real-time Updates */}
          <div className="md:col-span-2 lg:col-span-2 bg-white rounded-2xl p-8 shadow-sm border border-gray-200 hover:shadow-lg transition-shadow">
            <div className="flex items-start justify-between mb-6">
              <div>
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
                  <RefreshCw className="w-6 h-6 text-blue-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">
                  Sempre Aggiornato
                </h3>
                <p className="text-gray-600">
                  Monitoraggio automatico di 9 fonti ufficiali ogni 4 ore per
                  non perdere mai un aggiornamento importante.
                </p>
              </div>
            </div>

            {/* Live Feed Animation */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="space-y-3">
                <div className="flex items-center space-x-3 animate-fade-in-up">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm text-gray-700">
                    Agenzia delle Entrate - Circolare n.15/2024
                  </span>
                  <span className="text-xs text-gray-500">Ora</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span className="text-sm text-gray-700">
                    MEF - Decreto attuativo IVA
                  </span>
                  <span className="text-xs text-gray-500">15 min</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                  <span className="text-sm text-gray-700">
                    INPS - Aggiornamento contributi
                  </span>
                  <span className="text-xs text-gray-500">1h</span>
                </div>
              </div>
            </div>
          </div>

          {/* Medium Card - Document Analysis */}
          <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mb-4">
              <FileText className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">
              Analizza Tutto
            </h3>
            <p className="text-gray-600 mb-6">
              Carica PDF, Excel, fatture e documenti per ottenere analisi
              immediate e conformità normativa.
            </p>

            {/* Drag-drop Animation */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center bg-gray-50">
              <FileText className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-500">Trascina qui i tuoi file</p>
            </div>
          </div>

          {/* Medium Card - Smart FAQs */}
          <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 bg-yellow-100 rounded-xl flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-yellow-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">
              Risposte in 3 Secondi
            </h3>
            <p className="text-gray-600 mb-6">
              Database di 72% FAQ comuni per risposte istantanee sui quesiti più
              frequenti.
            </p>

            {/* Speed Meter */}
            <div className="relative bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                <span>Velocità risposta</span>
                <span className="font-semibold text-green-600">&lt;3s</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-gradient-to-r from-yellow-400 to-green-500 h-2 rounded-full w-[95%]"></div>
              </div>
            </div>
          </div>

          {/* Medium Card - GDPR Secure */}
          <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">
              Sicurezza Totale
            </h3>
            <p className="text-gray-600 mb-6">
              Conforme GDPR, crittografia end-to-end e server in Italia per la
              massima protezione dei dati.
            </p>

            {/* Security Badges */}
            <div className="space-y-2">
              <div className="flex items-center space-x-2 text-sm">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-gray-700">GDPR Compliant</span>
              </div>
              <div className="flex items-center space-x-2 text-sm">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-gray-700">SSL 256-bit</span>
              </div>
              <div className="flex items-center space-x-2 text-sm">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-gray-700">Server in Italia</span>
              </div>
            </div>
          </div>

          {/* Wide Card - Cost Optimization */}
          <div className="md:col-span-2 lg:col-span-3 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-8 text-white">
            <div className="grid md:grid-cols-2 gap-8 items-center">
              <div>
                <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mb-4">
                  <TrendingDown className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-3">
                  Solo €1.45 per utente al giorno
                </h3>
                <p className="text-blue-100 mb-4">
                  Sostituisci tutti i tuoi abbonamenti con un&apos;unica soluzione
                  completa. Risparmia tempo e denaro.
                </p>
                <div className="text-sm text-blue-100">
                  * Prezzo calcolato su piano annuale
                </div>
              </div>

              {/* Cost Comparison */}
              <div className="bg-white/10 backdrop-blur rounded-lg p-6">
                <h4 className="font-semibold mb-4">Prima vs Dopo</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Altri strumenti</span>
                    <span className="font-semibold">€500+/mese</span>
                  </div>
                  <div className="w-full h-px bg-white/20"></div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">PratikoAI</span>
                    <span className="font-semibold text-green-300">€49/mese</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm bg-green-500 px-2 py-1 rounded text-white">
                      -90% di costo
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}