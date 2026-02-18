'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Brain, ChevronDown, Search, BookOpen, Scale, FileText, AlertCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'

interface FAQ {
  id: string
  question: string
  answer: string
  category: string
  priority: 'alta' | 'media' | 'bassa'
  tags: string[]
}

export default function NormativeFAQPage() {
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('tutte')
  const [expandedFAQ, setExpandedFAQ] = useState<string | null>(null)

  // Ensure page starts at top
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [])

  // Simula il caricamento iniziale
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 2500) // 2.5 secondi di caricamento

    return () => clearTimeout(timer)
  }, [])

  const categories = [
    { id: 'tutte', label: 'Tutte le categorie', icon: BookOpen },
    { id: 'fiscale', label: 'Normativa Fiscale', icon: Scale },
    { id: 'lavoro', label: 'Diritto del Lavoro', icon: FileText },
    { id: 'societario', label: 'Diritto Societario', icon: AlertCircle }
  ]

  const faqs: FAQ[] = [
    {
      id: '1',
      question: 'Quali sono le principali novità del Decreto Legislativo n. 146/2021 in materia di lavoro?',
      answer: 'Il Decreto Legislativo n. 146/2021 ha introdotto importanti modifiche in materia di lavoro, tra cui: nuove disposizioni per il telelavoro e smart working, aggiornamenti sui contratti a termine, modifiche alle procedure di licenziamento collettivo, e nuove tutele per i lavoratori in situazioni di crisi aziendale. Le principali novità riguardano anche la digitalizzazione dei processi HR e nuovi obblighi informativi verso l\'Ispettorato del Lavoro.',
      category: 'lavoro',
      priority: 'alta',
      tags: ['smart working', 'contratti', 'licenziamenti', 'tutele lavoratori']
    },
    {
      id: '2',
      question: 'Come funziona il nuovo regime fiscale per le startup innovative del 2024?',
      answer: 'Il regime fiscale per le startup innovative 2024 prevede: agevolazioni IRES con aliquota ridotta al 15% per i primi 3 anni, deducibilità integrale degli investimenti in R&S, crediti d\'imposta per assunzioni di personale qualificato, e semplificazioni amministrative. È necessario mantenere i requisiti di innovatività e rispettare specifici vincoli di investimento per almeno 5 anni.',
      category: 'fiscale',
      priority: 'alta',
      tags: ['startup', 'agevolazioni', 'IRES', 'R&S', 'crediti imposta']
    },
    {
      id: '3',
      question: 'Quali sono gli obblighi di trasparenza societaria introdotti dalla Direttiva UE 2019/1151?',
      answer: 'La Direttiva UE 2019/1151 ha introdotto nuovi obblighi di trasparenza per le società, inclusi: pubblicazione online dei bilanci entro termini più stringenti, maggiore accessibilità delle informazioni societarie, digitalizzazione del registro delle imprese, e nuovi standard per la comunicazione delle partecipazioni societarie. Le sanzioni per inadempimento sono state significativamente aumentate.',
      category: 'societario',
      priority: 'media',
      tags: ['trasparenza', 'bilanci', 'registro imprese', 'partecipazioni', 'sanzioni']
    },
    {
      id: '4',
      question: 'Come si applica la nuova disciplina del reverse charge nel settore edile?',
      answer: 'La disciplina del reverse charge nel settore edile si applica a tutte le cessioni di beni e prestazioni di servizi rese nell\'ambito di contratti di appalto, subappalto e sub-contratto relativi ai settori edilizia e affini. Il committente è tenuto ad assolvere l\'IVA in luogo del cedente/prestatore. Sono escluse le operazioni sotto i 200 euro e quelle verso consumatori finali.',
      category: 'fiscale',
      priority: 'alta',
      tags: ['reverse charge', 'edilizia', 'IVA', 'appalti', 'subappalti']
    },
    {
      id: '5',
      question: 'Cosa prevede il nuovo Codice della Crisi d\'Impresa per le PMI?',
      answer: 'Il nuovo Codice della Crisi d\'Impresa per le PMI introduce: strumenti di allerta precoce obbligatori, procedure semplificate per la composizione negoziata, nuove misure di sostegno alla continuità aziendale, e tempistiche accelerate per le procedure concorsuali. È previsto un sistema di rating di legalità semplificato per le imprese che adottano le nuove procedure preventive.',
      category: 'societario',
      priority: 'media',
      tags: ['crisi impresa', 'PMI', 'procedure', 'continuità aziendale', 'rating legalità']
    },
    {
      id: '6',
      question: 'Quali sono le novità per i contratti di collaborazione coordinata e continuativa?',
      answer: 'Le novità per i contratti co.co.co. includono: obbligo di forma scritta per tutti i contratti, definizione più stringente dei requisiti di coordinamento, nuovi limiti temporali per la durata massima, estensione delle tutele previdenziali, e maggiori controlli ispettivi. È stata introdotta anche la possibilità di conversione automatica in rapporto subordinato in caso di violazione dei requisiti.',
      category: 'lavoro',
      priority: 'media',
      tags: ['co.co.co', 'forma scritta', 'coordinamento', 'tutele previdenziali', 'controlli ispettivi']
    }
  ]

  const filteredFAQs = faqs.filter(faq => {
    const matchesSearch = faq.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         faq.answer.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         faq.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
    
    const matchesCategory = selectedCategory === 'tutte' || faq.category === selectedCategory
    
    return matchesSearch && matchesCategory
  })

  const LoadingOverlay = () => (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-white/95 backdrop-blur-sm z-50 flex items-center justify-center"
    >
      <div className="text-center">
        <motion.div
          animate={{ 
            rotate: 360,
            scale: [1, 1.1, 1]
          }}
          transition={{ 
            rotate: { duration: 2, repeat: Infinity, ease: "linear" },
            scale: { duration: 1.5, repeat: Infinity, ease: "easeInOut" }
          }}
          className="w-20 h-20 bg-[#2A5D67] rounded-full flex items-center justify-center mx-auto mb-6"
        >
          <Brain className="w-10 h-10 text-white" />
        </motion.div>
        
        <motion.h2
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-2xl font-bold text-[#2A5D67] mb-2"
        >
          Caricamento FAQ Normative
        </motion.h2>
        
        <motion.p
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-[#1E293B] mb-4"
        >
          Recupero le domande più frequenti sulla normativa italiana...
        </motion.p>
        
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: "100%" }}
          transition={{ duration: 2, ease: "easeInOut" }}
          className="h-1 bg-[#2A5D67] rounded-full mx-auto max-w-xs"
        />
      </div>
    </motion.div>
  )

  return (
    <div className="min-h-screen bg-white">
      <AnimatePresence>
        {isLoading && <LoadingOverlay />}
      </AnimatePresence>

      {/* Header */}
      <header className="bg-white border-b border-[#C4BDB4]/20 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link href="/chat">
              <Button
                variant="ghost"
                className="flex items-center space-x-2 text-[#2A5D67] hover:bg-[#F8F5F1] transition-all duration-200"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Torna alla Chat</span>
              </Button>
            </Link>
            
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center space-x-2"
            >
              <div className="w-8 h-8 bg-[#2A5D67] rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-[#2A5D67]">PratikoAI</span>
            </motion.div>
          </div>
        </div>
      </header>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: isLoading ? 0 : 1 }}
        transition={{ duration: 0.5 }}
        className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8"
      >
        {/* Page Header */}
        <div className="text-center mb-12">
          <motion.h1
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-4xl font-bold text-[#2A5D67] mb-4"
          >
            Domande Frequenti sulla Normativa Italiana
          </motion.h1>
          <motion.p
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-xl text-[#1E293B] max-w-3xl mx-auto"
          >
            Le risposte alle domande più comuni su normativa fiscale, del lavoro e societaria, 
            sempre aggiornate con le ultime disposizioni legislative.
          </motion.p>
        </div>

        {/* Search and Filters */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mb-8 space-y-4"
        >
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#C4BDB4] w-5 h-5" />
            <input
              type="text"
              placeholder="Cerca nelle FAQ..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-[#C4BDB4] rounded-lg focus:ring-2 focus:ring-[#2A5D67] focus:border-transparent transition-all duration-200"
            />
          </div>

          <div className="flex flex-wrap gap-3">
            {categories.map((category) => (
              <Button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                variant={selectedCategory === category.id ? "default" : "outline"}
                className={`flex items-center space-x-2 ${
                  selectedCategory === category.id
                    ? "bg-[#2A5D67] text-white"
                    : "border-[#C4BDB4] text-[#2A5D67] hover:bg-[#F8F5F1]"
                }`}
              >
                <category.icon className="w-4 h-4" />
                <span>{category.label}</span>
              </Button>
            ))}
          </div>
        </motion.div>

        {/* FAQ List */}
        <div className="space-y-4">
          {filteredFAQs.map((faq, index) => (
            <motion.div
              key={faq.id}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 + index * 0.1 }}
            >
              <div className="bg-white border border-[#C4BDB4]/20 rounded-xl shadow-sm hover:shadow-lg transition-all duration-200">
                <div
                  className="cursor-pointer p-6"
                  onClick={() => setExpandedFAQ(expandedFAQ === faq.id ? null : faq.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <Badge 
                          variant={faq.priority === 'alta' ? 'destructive' : faq.priority === 'media' ? 'default' : 'secondary'}
                          className="text-xs"
                        >
                          {faq.priority === 'alta' ? 'Priorità Alta' : faq.priority === 'media' ? 'Priorità Media' : 'Priorità Bassa'}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {categories.find(cat => cat.id === faq.category)?.label}
                        </Badge>
                      </div>
                      <h3 className="text-left text-[#2A5D67] text-lg font-bold">
                        {faq.question}
                      </h3>
                    </div>
                    <motion.div
                      animate={{ rotate: expandedFAQ === faq.id ? 180 : 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <ChevronDown className="w-5 h-5 text-[#C4BDB4] flex-shrink-0 ml-4" />
                    </motion.div>
                  </div>
                </div>
                
                <AnimatePresence>
                  {expandedFAQ === faq.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="overflow-hidden"
                    >
                      <div className="px-6 pb-6">
                        <div className="border-t border-[#C4BDB4]/20 pt-4">
                          <p className="text-[#1E293B] leading-relaxed mb-4">
                            {faq.answer}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {faq.tags.map((tag, tagIndex) => (
                              <Badge
                                key={tagIndex}
                                variant="secondary"
                                className="text-xs bg-[#F8F5F1] text-[#2A5D67]"
                              >
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          ))}
        </div>

        {filteredFAQs.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-12"
          >
            <div className="w-16 h-16 bg-[#F8F5F1] rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-[#C4BDB4]" />
            </div>
            <h3 className="text-xl font-semibold text-[#2A5D67] mb-2">
              Nessun risultato trovato
            </h3>
            <p className="text-[#1E293B]">
              Prova a modificare i termini di ricerca o seleziona una categoria diversa.
            </p>
          </motion.div>
        )}

        {/* Contact CTA */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-16 text-center"
        >
          <div className="bg-[#F8F5F1] rounded-xl p-8">
            <h3 className="text-2xl font-bold text-[#2A5D67] mb-4">
              Non hai trovato la risposta che cercavi?
            </h3>
            <p className="text-[#1E293B] mb-6">
              Il nostro assistente AI è sempre disponibile per rispondere alle tue domande specifiche sulla normativa italiana.
            </p>
            <Link href="/chat">
              <Button
                className="bg-[#2A5D67] hover:bg-[#1E293B] text-white px-6 py-3"
              >
                <strong>Fai una domanda all&apos;AI</strong>
              </Button>
            </Link>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}