"use client";

import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

export function FinalCTASection() {
  const [email, setEmail] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Email submitted:", email);
    // Handle email submission
  };

  return (
    <section className="py-20 lg:py-32 bg-gradient-to-br from-blue-600 via-blue-700 to-purple-700">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Main Content */}
        <div className="text-white mb-12">
          <h2 className="text-3xl md:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
            Inizia a risparmiare{" "}
            <span className="text-yellow-300">10 ore</span> a settimana
          </h2>
          <p className="text-xl md:text-2xl text-blue-100 max-w-3xl mx-auto leading-relaxed">
            Unisciti a 50+ professionisti che hanno già automatizzato la ricerca
            normativa e si concentrano sui clienti
          </p>
        </div>

        {/* Email Form */}
        <form
          onSubmit={handleSubmit}
          className="max-w-2xl mx-auto bg-white rounded-2xl p-6 md:p-8 shadow-2xl mb-8"
        >
          <div className="flex flex-col md:flex-row gap-4">
            <Input
              type="email"
              placeholder="La tua email professionale"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1 h-14 px-6 text-lg border-2 border-gray-200 focus:border-blue-500 rounded-lg"
              required
            />
            <Button
              type="submit"
              size="lg"
              className="h-14 px-8 bg-gradient-primary hover:shadow-xl transition-all duration-300 hover:scale-105 text-lg font-semibold rounded-lg whitespace-nowrap"
            >
              Attiva Prova →
            </Button>
          </div>
          <div className="flex flex-col sm:flex-row items-center justify-center space-y-2 sm:space-y-0 sm:space-x-6 text-sm text-gray-600 mt-4">
            <span>✓ 7 giorni gratis</span>
            <span>✓ Nessuna carta richiesta</span>
            <span>✓ Cancella in qualsiasi momento</span>
          </div>
        </form>

        {/* Trust Indicators */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-white/90">
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-300 mb-2">7 giorni</div>
            <div className="text-sm">Prova gratuita</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-300 mb-2">50+</div>
            <div className="text-sm">Professionisti attivi</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-300 mb-2">95%</div>
            <div className="text-sm">Soddisfazione cliente</div>
          </div>
        </div>

        {/* Security Notice */}
        <div className="mt-12 text-center">
          <p className="text-blue-100 text-sm">
            🔒 I tuoi dati sono protetti e conformi GDPR • Server in Italia •
            Crittografia end-to-end
          </p>
        </div>
      </div>
    </section>
  );
}