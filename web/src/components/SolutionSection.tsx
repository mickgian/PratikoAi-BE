import { Button } from "./ui/button";
import { Check, Rss, RefreshCw, FileText, Database, Zap } from "lucide-react";

export function SolutionSection() {
  const features = [
    {
      icon: Rss,
      text: "Monitoraggio RSS di 9 fonti ufficiali",
    },
    {
      icon: RefreshCw,
      text: "Aggiornamenti automatici ogni 4 ore",
    },
    {
      icon: FileText,
      text: "Risposte con citazioni dirette",
    },
    {
      icon: Database,
      text: "Analisi documenti (PDF, Excel, Fatture)",
    },
    {
      icon: Zap,
      text: "Database di 72% FAQ per risposte istantanee",
    },
  ];

  return (
    <section className="py-20 lg:py-32 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-5 gap-12 lg:gap-16 items-center">
          {/* Left Content */}
          <div className="lg:col-span-3 order-2 lg:order-1">
            <div className="max-w-2xl lg:max-w-none">
              <div className="mb-6">
                <span className="inline-block px-4 py-2 bg-green-100 text-green-800 text-sm font-semibold rounded-full uppercase tracking-wide">
                  La Soluzione
                </span>
              </div>

              <h2 className="text-3xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
                Un&apos;IA che monitora tutto.{" "}
                <span className="text-green-600">Tu ti concentri sui clienti.</span>
              </h2>

              <p className="text-xl text-gray-600 mb-8 leading-relaxed">
                PratikoAI monitora automaticamente tutte le fonti normative
                ufficiali e ti fornisce risposte precise in tempo reale.
              </p>

              {/* Feature List */}
              <div className="space-y-4 mb-8">
                {features.map((feature, index) => (
                  <div key={index} className="flex items-start space-x-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                      <feature.icon className="w-5 h-5 text-green-600" />
                    </div>
                    <span className="text-lg text-gray-700 font-medium pt-2">
                      {feature.text}
                    </span>
                  </div>
                ))}
              </div>

              <Button
                size="lg"
                variant="outline"
                className="h-12 px-8 border-2 border-blue-600 text-blue-600 hover:bg-blue-600 hover:text-white transition-colors"
              >
                Scopri Come Funziona →
              </Button>
            </div>
          </div>

          {/* Right Visual */}
          <div className="lg:col-span-2 order-1 lg:order-2">
            <div className="relative">
              {/* Dashboard mockup */}
              <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
                {/* Header */}
                <div className="bg-gradient-to-r from-green-500 to-blue-600 text-white p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold">Dashboard PratikoAI</h3>
                    <div className="flex items-center space-x-2 text-sm">
                      <div className="w-2 h-2 bg-green-300 rounded-full animate-pulse"></div>
                      <span>Live</span>
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  {/* Updates Feed */}
                  <div className="space-y-4">
                    <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          Nuova circolare IRPEF
                        </p>
                        <p className="text-xs text-gray-600">2 minuti fa</p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                      <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          Aggiornamento IVA 2024
                        </p>
                        <p className="text-xs text-gray-600">15 minuti fa</p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                      <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900">
                          Modifica Superbonus
                        </p>
                        <p className="text-xs text-gray-600">1 ora fa</p>
                      </div>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="mt-6 pt-6 border-t border-gray-200">
                    <div className="grid grid-cols-2 gap-4 text-center">
                      <div>
                        <div className="text-2xl font-bold text-green-600">9</div>
                        <div className="text-xs text-gray-600">Fonti monitorate</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-blue-600">4h</div>
                        <div className="text-xs text-gray-600">Intervallo update</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating elements */}
              <div className="absolute -top-4 -right-4 w-16 h-16 bg-green-500 rounded-full flex items-center justify-center shadow-lg">
                <Check className="w-8 h-8 text-white" />
              </div>

              <div className="absolute -bottom-4 -left-4 w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center shadow-lg">
                <RefreshCw className="w-6 h-6 text-white animate-spin" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}