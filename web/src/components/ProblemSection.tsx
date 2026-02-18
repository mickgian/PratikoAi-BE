import { FileText, Clock, AlertTriangle, Euro } from "lucide-react";

export function ProblemSection() {
  const stats = [
    {
      icon: FileText,
      value: "15+",
      label: "circolari/settimana",
    },
    {
      icon: Clock,
      value: "3+",
      label: "ore di ricerca/giorno",
    },
    {
      icon: AlertTriangle,
      value: "87%",
      label: "teme errori",
    },
    {
      icon: Euro,
      value: "€500+",
      label: "in abbonamenti",
    },
  ];

  return (
    <section className="py-20 lg:py-32 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-5 gap-12 lg:gap-16 items-center">
          {/* Left Visual */}
          <div className="lg:col-span-2">
            <div className="relative">
              {/* Illustration placeholder - stacked documents with warning signs */}
              <div className="relative bg-white rounded-2xl shadow-xl p-8 transform -rotate-2">
                <div className="space-y-4">
                  <div className="h-4 bg-gray-300 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-300 rounded w-full"></div>
                  <div className="h-4 bg-gray-300 rounded w-2/3"></div>
                  <div className="flex items-center space-x-2 mt-6">
                    <AlertTriangle className="w-5 h-5 text-red-500" />
                    <span className="text-sm text-red-600 font-medium">
                      Circolare del 15 Gen 2024
                    </span>
                  </div>
                </div>
                <div className="absolute -top-3 -right-3 w-8 h-8 bg-red-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">!</span>
                </div>
              </div>

              <div className="absolute -bottom-4 -right-4 bg-white rounded-2xl shadow-lg p-6 transform rotate-3">
                <div className="space-y-2">
                  <div className="h-3 bg-gray-300 rounded w-2/3"></div>
                  <div className="h-3 bg-gray-300 rounded w-full"></div>
                  <div className="h-3 bg-gray-300 rounded w-1/2"></div>
                </div>
              </div>

              <div className="absolute top-8 -left-4 bg-yellow-100 border-2 border-yellow-300 rounded-lg p-3 transform -rotate-6">
                <Clock className="w-6 h-6 text-yellow-600" />
              </div>
            </div>
          </div>

          {/* Right Content */}
          <div className="lg:col-span-3">
            <div className="max-w-2xl">
              <div className="mb-6">
                <span className="inline-block px-4 py-2 bg-red-100 text-red-800 text-sm font-semibold rounded-full uppercase tracking-wide">
                  Il Problema
                </span>
              </div>

              <h2 className="text-3xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
                Le normative cambiano.{" "}
                <span className="text-red-600">Tu rimani indietro.</span>
              </h2>

              <p className="text-xl text-gray-600 mb-12 leading-relaxed">
                Ogni giorno escono nuove circolari dall&apos;Agenzia delle Entrate,
                INPS, e MEF. Trovarle, leggerle e comprenderle richiede ore che
                non hai.
              </p>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-6">
                {stats.map((stat, index) => (
                  <div
                    key={index}
                    className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 text-center"
                  >
                    <div className="flex justify-center mb-3">
                      <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                        <stat.icon className="w-6 h-6 text-red-600" />
                      </div>
                    </div>
                    <div className="text-2xl font-bold text-gray-900 mb-1">
                      {stat.value}
                    </div>
                    <div className="text-sm text-gray-600">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}