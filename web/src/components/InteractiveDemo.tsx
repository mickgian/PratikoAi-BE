"use client";

import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Send, FileText, Calculator, Newspaper, Home } from "lucide-react";

export function InteractiveDemo() {
  const [activeTab, setActiveTab] = useState("irpef");
  const [inputValue, setInputValue] = useState("");

  const demoContent = {
    irpef: {
      icon: Calculator,
      title: "Calcolo IRPEF",
      userQuery: "Quali sono le aliquote IRPEF 2024?",
      aiResponse: `Le aliquote IRPEF per il 2024 sono:

• **23%** fino a €15.000
• **25%** da €15.001 a €28.000  
• **35%** da €28.001 a €50.000
• **43%** oltre €50.000

**Fonte:** Art. 11 del TUIR - Aggiornato con Legge di Bilancio 2024 (Legge 30 dicembre 2023, n. 213)

**Novità 2024:** Confermata la riduzione dell&apos;aliquota del secondo scaglione dal 27% al 25%.`,
    },
    fattura: {
      icon: FileText,
      title: "Analisi Fattura",
      userQuery: "Questa fattura è conforme alle nuove regole?",
      aiResponse: `✅ **Fattura conforme** alle normative vigenti.

**Verifiche effettuate:**
• Presenza di tutti i dati obbligatori (Art. 21 DPR 633/72)
• Codice Destinatario corretto per fatturazione elettronica
• Aliquota IVA applicata correttamente (22%)
• Formato XML conforme alle specifiche AgID

**Raccomandazione:** Verificare che il codice ATECO sia aggiornato.`,
    },
    novita: {
      icon: Newspaper,
      title: "Novità Fiscali",
      userQuery: "Ci sono aggiornamenti fiscali oggi?",
      aiResponse: `📋 **3 aggiornamenti importanti** nelle ultime 24 ore:

**1. Circolare AdE n. 15/2024** (pubblicata 2 ore fa)
Chiarimenti su deduzioni spese mediche

**2. Decreto MEF** (pubblicata 5 ore fa)  
Nuove modalità versamento F24

**3. Risoluzione INPS n. 42/2024** (pubblicata ieri)
Aggiornamento contributi professionisti

Vuoi i dettagli di uno specifico aggiornamento?`,
    },
    superbonus: {
      icon: Home,
      title: "Superbonus",
      userQuery: "Il Superbonus è ancora attivo nel 2024?",
      aiResponse: `⚠️ **Superbonus 110% terminato** il 31 dicembre 2023.

**Situazione 2024:**
• **70%** per condomini con CILA presentata entro 31/12/2023
• **Cessione crediti sospesa** (Art. 1, comma 28, L. 197/2022)
• Possibili **alternative**: Bonus ristrutturazione 50%, Ecobonus

**Fonte:** Legge di Bilancio 2024 e Decreto Aiuti Quater

Hai lavori già avviati? Posso verificare le opzioni disponibili.`,
    },
  };

  const currentDemo = demoContent[activeTab as keyof typeof demoContent];

  return (
    <section className="py-20 lg:py-32 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-5xl font-bold text-gray-900 mb-6">
            Provalo Subito
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Scopri quanto è facile ottenere risposte precise e aggiornate su
            qualsiasi quesito fiscale
          </p>
        </div>

        {/* Demo Interface */}
        <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
          {/* Tab Navigation */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid grid-cols-2 lg:grid-cols-4 w-full rounded-none border-b border-gray-200 bg-gray-50 h-auto p-0">
              <TabsTrigger
                value="irpef"
                className="flex items-center space-x-2 py-4 px-6 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-600 rounded-none"
              >
                <Calculator className="w-4 h-4" />
                <span className="hidden sm:inline">Calcolo IRPEF</span>
                <span className="sm:hidden">IRPEF</span>
              </TabsTrigger>
              <TabsTrigger
                value="fattura"
                className="flex items-center space-x-2 py-4 px-6 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-600 rounded-none"
              >
                <FileText className="w-4 h-4" />
                <span className="hidden sm:inline">Analisi Fattura</span>
                <span className="sm:hidden">Fattura</span>
              </TabsTrigger>
              <TabsTrigger
                value="novita"
                className="flex items-center space-x-2 py-4 px-6 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-600 rounded-none"
              >
                <Newspaper className="w-4 h-4" />
                <span className="hidden sm:inline">Novità Fiscali</span>
                <span className="sm:hidden">Novità</span>
              </TabsTrigger>
              <TabsTrigger
                value="superbonus"
                className="flex items-center space-x-2 py-4 px-6 data-[state=active]:bg-white data-[state=active]:border-b-2 data-[state=active]:border-blue-600 rounded-none"
              >
                <Home className="w-4 h-4" />
                <span className="hidden sm:inline">Superbonus</span>
                <span className="sm:hidden">Bonus</span>
              </TabsTrigger>
            </TabsList>

            {/* Chat Interface */}
            <div className="p-6 lg:p-8">
              <TabsContent value={activeTab} className="mt-0">
                <div className="space-y-6">
                  {/* User Message */}
                  <div className="flex justify-end">
                    <div className="bg-blue-600 text-white rounded-2xl rounded-br-md px-6 py-4 max-w-md">
                      <p>{currentDemo.userQuery}</p>
                    </div>
                  </div>

                  {/* AI Response */}
                  <div className="flex justify-start">
                    <div className="bg-gray-50 border border-gray-200 rounded-2xl rounded-bl-md px-6 py-4 max-w-2xl">
                      <div className="flex items-center space-x-2 mb-3">
                        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                          <span className="text-white text-sm font-bold">P</span>
                        </div>
                        <span className="font-semibold text-gray-900">
                          PratikoAI
                        </span>
                        <span className="text-xs text-gray-500">
                          Risposta in 2.1s
                        </span>
                      </div>
                      <div className="prose prose-sm max-w-none">
                        <div className="whitespace-pre-line text-gray-700">
                          {currentDemo.aiResponse}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-200 p-6 bg-gray-50">
              <div className="flex items-center space-x-4">
                <Input
                  placeholder="Fai una domanda..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  className="flex-1 h-12 border-gray-300 focus:border-blue-500 bg-white"
                />
                <Button
                  size="lg"
                  className="h-12 px-6 bg-gradient-primary hover:shadow-lg transition-all duration-200"
                >
                  <Send className="w-4 h-4 mr-2" />
                  Invia
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Premi Invio per inviare la domanda • Risposte sempre aggiornate
                con fonti ufficiali
              </p>
            </div>
          </Tabs>
        </div>
      </div>
    </section>
  );
}