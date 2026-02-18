'use client'

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown, ArrowLeft, HelpCircle, Construction } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'

interface FAQ {
  question: string
  answer: string
  category: 'general' | 'technical' | 'pricing' | 'legal'
}

const faqData: FAQ[] = [
  {
    question: "Come funziona PratikoAI?",
    answer: "PratikoAI utilizza l'intelligenza artificiale per analizzare la normativa fiscale e del lavoro italiana. Il sistema monitora continuamente le fonti ufficiali (Agenzia delle Entrate, INPS, MEF) e fornisce risposte immediate alle tue domande, sempre con citazione delle fonti normative.",
    category: 'general'
  },
  {
    question: "Quanto sono aggiornate le informazioni?",
    answer: "Il nostro sistema controlla le fonti ufficiali ogni 4 ore. Ricevi notifiche immediate per modifiche rilevanti e hai sempre accesso allo storico completo delle variazioni normative. Gli aggiornamenti sono processati automaticamente e verificati dal nostro team.",
    category: 'technical'
  },
  {
    question: "Posso caricare documenti per l'analisi?",
    answer: "Sì, puoi caricare fatture, contratti e altri documenti fiscalmente rilevanti. PratikoAI effettua il riconoscimento automatico del tipo documento, estrae i dati fiscalmente rilevanti, controlla la conformità normativa e fornisce suggerimenti per l'ottimizzazione fiscale.",
    category: 'technical'
  },
  {
    question: "Quali sono i prezzi dei piani?",
    answer: "Offriamo tre piani: Starter (€49/mese) per professionisti individuali, Professional (€99/mese) per studi medi, e Enterprise (€199/mese) per grandi studi. Tutti i piani includono una prova gratuita di 14 giorni senza impegno.",
    category: 'pricing'
  },
  {
    question: "È sicuro utilizzare PratikoAI con dati sensibili?",
    answer: "Assolutamente sì. Tutti i dati sono crittografati end-to-end, rispettiamo il GDPR e le normative italiane sulla privacy. I tuoi documenti non vengono mai condivisi e vengono eliminati automaticamente dopo l'elaborazione. Siamo conformi agli standard di sicurezza più elevati.",
    category: 'legal'
  },
  {
    question: "Posso annullare il mio abbonamento in qualsiasi momento?",
    answer: "Sì, puoi annullare il tuo abbonamento in qualsiasi momento dal tuo pannello utente. Non ci sono penali né costi nascosti. Il servizio rimane attivo fino alla fine del periodo già pagato.",
    category: 'pricing'
  },
  {
    question: "PratikoAI sostituisce il mio commercialista?",
    answer: "No, PratikoAI è uno strumento di supporto che ti aiuta a rimanere aggiornato e a trovare rapidamente le informazioni normative. È progettato per ottimizzare il tuo workflow e migliorare l'efficienza, ma non sostituisce il giudizio professionale e l'esperienza di un commercialista qualificato.",
    category: 'general'
  },
  {
    question: "Che tipo di supporto offrite?",
    answer: "Offriamo supporto via email per tutti i piani, supporto telefonico per i piani Professional ed Enterprise, e accesso a webinar formativi mensili. Il nostro team di esperti è sempre disponibile per aiutarti a sfruttare al meglio la piattaforma.",
    category: 'general'
  },
  {
    question: "Posso integrare PratikoAI con il mio software gestionale?",
    answer: "Stiamo sviluppando integrazioni con i principali software gestionali italiani. Al momento è possibile esportare i dati in formati standard. Le prime integrazioni native saranno disponibili nei prossimi mesi per i clienti Enterprise.",
    category: 'technical'
  },
  {
    question: "Come viene garantita l'accuratezza delle informazioni?",
    answer: "Tutte le risposte sono basate su fonti ufficiali e vengono costantemente verificate. Ogni risposta include sempre la citazione delle fonti normative. In caso di dubbi, consigliamo sempre di consultare direttamente le fonti ufficiali o un professionista qualificato.",
    category: 'legal'
  }
]

const categories = {
  general: { name: 'Generale', color: '#2A5D67' },
  technical: { name: 'Tecnico', color: '#D4A574' },
  pricing: { name: 'Prezzi', color: '#A9C1B7' },
  legal: { name: 'Legale', color: '#1E293B' }
}

export default function FAQPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [openFAQ, setOpenFAQ] = useState<number | null>(null)

  const filteredFAQs = selectedCategory === 'all' 
    ? faqData 
    : faqData.filter(faq => faq.category === selectedCategory)

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="bg-[#2A5D67] text-white py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-4 mb-6">
            <Link href="/chat">
              <Button
                variant="ghost"
                size="sm"
                className="text-white hover:bg-white/10 p-2"
              >
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                <HelpCircle className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-3xl font-bold">Domande Frequenti</h1>
                <div className="flex items-center space-x-2 mt-1">
                  <Badge className="bg-[#D4A574] text-[#1E293B] hover:bg-[#D4A574]/90">
                    <Construction className="w-3 h-3 mr-1" />
                    Work in progress
                  </Badge>
                </div>
              </div>
            </div>
          </div>
          <p className="text-white/90 text-lg">
            Trova rapidamente le risposte alle tue domande su PratikoAI. 
            Se non trovi quello che cerchi, contattaci direttamente.
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Category Filter */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex flex-wrap gap-2 justify-center">
            <Button
              onClick={() => setSelectedCategory('all')}
              variant={selectedCategory === 'all' ? 'default' : 'outline'}
              size="sm"
              className={selectedCategory === 'all' 
                ? 'bg-[#2A5D67] hover:bg-[#1E293B]' 
                : 'border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white'
              }
            >
              Tutte le FAQ
            </Button>
            {Object.entries(categories).map(([key, category]) => (
              <Button
                key={key}
                onClick={() => setSelectedCategory(key)}
                variant={selectedCategory === key ? 'default' : 'outline'}
                size="sm"
                className={selectedCategory === key 
                  ? 'bg-[#2A5D67] hover:bg-[#1E293B]' 
                  : 'border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white'
                }
              >
                {category.name}
              </Button>
            ))}
          </div>
        </motion.div>

        {/* FAQ List */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          {filteredFAQs.map((faq, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-white border border-[#C4BDB4]/20 rounded-xl shadow-sm hover:shadow-md transition-all duration-200"
            >
              <button
                onClick={() => setOpenFAQ(openFAQ === index ? null : index)}
                className="w-full p-6 text-left flex items-center justify-between hover:bg-[#F8F5F1]/50 rounded-xl transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <Badge 
                      variant="outline" 
                      className="text-xs"
                      style={{ 
                        borderColor: categories[faq.category].color,
                        color: categories[faq.category].color 
                      }}
                    >
                      {categories[faq.category].name}
                    </Badge>
                  </div>
                  <h3 className="text-lg font-semibold text-[#1E293B] pr-4">
                    {faq.question}
                  </h3>
                </div>
                <motion.div
                  animate={{ rotate: openFAQ === index ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <ChevronDown className="w-5 h-5 text-[#2A5D67]" />
                </motion.div>
              </button>
              
              {openFAQ === index && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="px-6 pb-6"
                >
                  <div className="border-t border-[#C4BDB4]/20 pt-4">
                    <p className="text-[#1E293B] leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                </motion.div>
              )}
            </motion.div>
          ))}
        </motion.div>

        {/* Help Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-12 bg-[#F8F5F1] rounded-2xl p-8 text-center"
        >
          <HelpCircle className="w-12 h-12 text-[#2A5D67] mx-auto mb-4" />
          <h3 className="text-2xl font-bold text-[#2A5D67] mb-3">
            Non hai trovato quello che cercavi?
          </h3>
          <p className="text-[#1E293B] mb-6 max-w-2xl mx-auto">
            Il nostro team è sempre disponibile per aiutarti. Contattaci direttamente 
            e riceverai una risposta personalizzata entro 24 ore.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              className="bg-[#2A5D67] hover:bg-[#1E293B]"
              size="lg"
            >
              <span className="font-bold">Contatta il Supporto</span>
            </Button>
            <Button 
              variant="outline"
              size="lg"
              className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white"
            >
              Richiedi una Demo
            </Button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}