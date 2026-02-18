'use client'

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown, ChevronUp, HelpCircle, Brain, Shield, Clock, FileCheck, Sparkles } from 'lucide-react'

const faqData = [
  {
    category: 'Funzionalità',
    icon: Brain,
    questions: [
      {
        question: 'Come funziona PratikoAI per gli aggiornamenti normativi?',
        answer: 'PratikoAI monitora costantemente le fonti ufficiali (Gazzetta Ufficiale, Agenzia delle Entrate, Ministeri) e utilizza AI avanzata per analizzare, classificare e sintetizzare gli aggiornamenti normativi in tempo reale, fornendoti notifiche personalizzate basate sulla tua area di pratica.'
      },
      {
        question: 'Che tipo di documenti può analizzare PratikoAI?',
        answer: 'PratikoAI può analizzare contratti, fatture, documenti fiscali, atti legali, corrispondenza e molto altro. Il sistema riconosce automaticamente il tipo di documento, estrae i dati fiscalmente rilevanti e verifica la conformità normativa.'
      },
      {
        question: 'Le risposte di PratikoAI sono sempre aggiornate?',
        answer: 'Sì, il nostro sistema si aggiorna continuamente dalle fonti ufficiali italiane. Ogni risposta include il riferimento normativo e la data dell&apos;ultimo aggiornamento per garantire massima affidabilità.'
      }
    ]
  },
  {
    category: 'Sicurezza',
    icon: Shield,
    questions: [
      {
        question: 'I miei documenti sono sicuri con PratikoAI?',
        answer: 'Assolutamente sì. Utilizziamo crittografia end-to-end, server in Europa conformi GDPR, e non conserviamo i documenti dopo l&apos;analisi. Tutti i dati sono processati in modo anonimo e sicuro.'
      },
      {
        question: 'PratikoAI è conforme al GDPR?',
        answer: 'Sì, siamo completamente conformi al GDPR. I tuoi dati sono processati solo per fornire il servizio richiesto, non vengono condivisi con terze parti e puoi richiedere la cancellazione in qualsiasi momento.'
      }
    ]
  },
  {
    category: 'Utilizzo',
    icon: Clock,
    questions: [
      {
        question: 'Quanto tempo serve per ottenere una risposta?',
        answer: 'Le risposte arrivano in pochi secondi per le domande normative standard. L&apos;analisi dei documenti richiede più tempo a seconda della complessità.'
      },
      {
        question: 'Posso utilizzare PratikoAI anche da mobile?',
        answer: 'Sì, PratikoAI è completamente ottimizzato per dispositivi mobili. Puoi accedere a tutte le funzionalità dal tuo smartphone o tablet con la stessa esperienza della versione desktop.'
      },
      {
        question: 'Che tipo di supporto offrite?',
        answer: 'Offriamo supporto email dedicato per tutti gli utenti e sessioni di formazione personalizzate per i piani multiutente.'
      }
    ]
  },
  {
    category: 'Abbonamenti',
    icon: FileCheck,
    questions: [
      {
        question: 'Posso disdire l&apos;abbonamento in qualsiasi momento?',
        answer: 'Sì, puoi disdire l&apos;abbonamento in qualsiasi momento dal tuo pannello utente. La disdetta avrà effetto alla fine del periodo di fatturazione corrente.'
      },
      {
        question: 'Offrite sconti per studi legali o commercialisti?',
        answer: 'Sì, offriamo sconti progressivi per team (a partire da 3 utenti) e piani enterprise personalizzati per studi e società. Contattaci per un preventivo dedicato.'
      }
    ]
  }
]

export function FAQSection() {
  const [openItems, setOpenItems] = useState<string[]>([])
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: ''
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const toggleItem = (id: string) => {
    setOpenItems(prev => 
      prev.includes(id) 
        ? prev.filter(item => item !== id)
        : [...prev, id]
    )
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    
    // Simulate form submission
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Reset form
    setFormData({ name: '', email: '', message: '' })
    setIsSubmitting(false)
    
    // Show success feedback (in a real app, you'd handle this with proper toast/notification)
    alert('Messaggio inviato con successo! Ti contatteremo presto.')
  }

  return (
    <section id="faq" className="py-20 bg-[#F8F5F1]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <div className="flex items-center justify-center mb-4">
            <HelpCircle className="w-8 h-8 text-[#2A5D67] mr-3" />
            <Sparkles className="w-6 h-6 text-[#D4A574]" />
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-[#2A5D67] mb-4">
            Domande Frequenti
          </h2>
          <p className="text-lg text-[#1E293B] max-w-2xl mx-auto">
            Tutto quello che devi sapere su PratikoAI e come può aiutarti nel tuo lavoro quotidiano
          </p>
        </motion.div>

        {/* FAQ Categories */}
        <div className="space-y-8">
          {faqData.map((category, categoryIndex) => (
            <motion.div
              key={category.category}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: categoryIndex * 0.1 }}
              viewport={{ once: true }}
              className="bg-white rounded-2xl shadow-lg overflow-hidden"
            >
              {/* Category Header */}
              <div className="bg-gradient-to-r from-[#2A5D67] to-[#1E293B] px-6 py-4">
                <div className="flex items-center">
                  <category.icon className="w-6 h-6 text-[#D4A574] mr-3" />
                  <h3 className="text-xl font-semibold text-white">
                    {category.category}
                  </h3>
                </div>
              </div>

              {/* Questions */}
              <div className="divide-y divide-[#C4BDB4]/30">
                {category.questions.map((faq, faqIndex) => {
                  const itemId = `${category.category}-${faqIndex}`
                  const isOpen = openItems.includes(itemId)

                  return (
                    <motion.div
                      key={itemId}
                      initial={{ opacity: 0 }}
                      whileInView={{ opacity: 1 }}
                      transition={{ duration: 0.4, delay: faqIndex * 0.05 }}
                      viewport={{ once: true }}
                    >
                      <button
                        onClick={() => toggleItem(itemId)}
                        className="w-full px-6 py-6 text-left hover:bg-[#F8F5F1] transition-all duration-200 focus:outline-none focus:bg-[#F8F5F1]"
                      >
                        <div className="flex items-center justify-between">
                          <h4 className="text-lg font-medium text-[#2A5D67] pr-4">
                            {faq.question}
                          </h4>
                          <motion.div
                            animate={{ rotate: isOpen ? 180 : 0 }}
                            transition={{ duration: 0.2 }}
                            className="flex-shrink-0"
                          >
                            <ChevronDown className="w-5 h-5 text-[#2A5D67]" />
                          </motion.div>
                        </div>
                      </button>
                      
                      <motion.div
                        initial={false}
                        animate={{
                          height: isOpen ? 'auto' : 0,
                          opacity: isOpen ? 1 : 0
                        }}
                        transition={{ duration: 0.3, ease: 'easeInOut' }}
                        className="overflow-hidden"
                      >
                        <div className="px-6 pb-6">
                          <p className="text-[#1E293B] leading-relaxed">
                            {faq.answer}
                          </p>
                        </div>
                      </motion.div>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Bottom CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <div className="bg-white rounded-2xl shadow-lg p-8 max-w-2xl mx-auto">
            <h3 className="text-2xl font-semibold text-[#2A5D67] mb-4">
              Non hai trovato la risposta che cercavi?
            </h3>
            <p className="text-[#1E293B] mb-6">
              Il nostro team di esperti è sempre disponibile per aiutarti
            </p>
            <form onSubmit={handleSubmit} className="space-y-4 w-full max-w-md mx-auto">
              <div>
                <input
                  type="text"
                  name="name"
                  placeholder="Il tuo nome"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 bg-[#F8F5F1] border border-[#C4BDB4]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2A5D67] focus:border-transparent transition-all duration-200"
                />
              </div>
              <div>
                <input
                  type="email"
                  name="email"
                  placeholder="La tua email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 bg-[#F8F5F1] border border-[#C4BDB4]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2A5D67] focus:border-transparent transition-all duration-200"
                />
              </div>
              <div>
                <textarea
                  name="message"
                  placeholder="Il tuo messaggio"
                  value={formData.message}
                  onChange={handleInputChange}
                  required
                  rows={4}
                  className="w-full px-4 py-3 bg-[#F8F5F1] border border-[#C4BDB4]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2A5D67] focus:border-transparent transition-all duration-200 resize-none"
                />
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full inline-flex items-center justify-center px-6 py-3 bg-[#2A5D67] hover:bg-[#1E293B] disabled:bg-[#C4BDB4] text-white font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed"
              >
                <HelpCircle className="w-5 h-5 mr-2" />
                <span className="font-bold">
                  {isSubmitting ? 'Invio in corso...' : 'Invia Messaggio'}
                </span>
              </button>
            </form>
          </div>
        </motion.div>
      </div>
    </section>
  )
}