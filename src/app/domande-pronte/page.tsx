'use client'

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowLeft, 
  MessageSquare, 
  Search, 
  Briefcase, 
  Calculator, 
  Building, 
  Scale, 
  FileText,
  ChevronRight,
  TrendingUp,
  Brain
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import Link from 'next/link'

interface DomandaPronta {
  id: string
  domanda: string
  categoria: string
  urgenza: 'alta' | 'media' | 'bassa'
  popolare: boolean
}

const categorieNormative = [
  {
    id: 'lavoro',
    nome: 'Diritto del Lavoro',
    icon: Briefcase,
    colore: '#2A5D67',
    descrizione: 'Contratti, licenziamenti, ferie, malattia'
  },
  {
    id: 'fiscale',
    nome: 'Diritto Fiscale',
    icon: Calculator,
    colore: '#D4A574',
    descrizione: 'Imposte, detrazioni, dichiarazioni, IVA'
  },
  {
    id: 'commerciale',
    nome: 'Diritto Commerciale',
    icon: Building,
    colore: '#1E293B',
    descrizione: 'Società, contratti commerciali, partite IVA'
  },
  {
    id: 'civile',
    nome: 'Diritto Civile',
    icon: Scale,
    colore: '#2A5D67',
    descrizione: 'Contratti, successioni, proprietà, famiglia'
  },
  {
    id: 'amministrativo',
    nome: 'Diritto Amministrativo',
    icon: FileText,
    colore: '#D4A574',
    descrizione: 'Procedimenti, autorizzazioni, ricorsi'
  }
]

const domandePreparate: DomandaPronta[] = [
  // Diritto del Lavoro
  {
    id: '1',
    domanda: 'Quali sono i termini di preavviso per il licenziamento di un dipendente a tempo indeterminato?',
    categoria: 'lavoro',
    urgenza: 'alta',
    popolare: true
  },
  {
    id: '2',
    domanda: 'Come si calcola la retribuzione feriale e quando deve essere pagata?',
    categoria: 'lavoro',
    urgenza: 'media',
    popolare: true
  },
  {
    id: '3',
    domanda: 'Quali sono gli obblighi del datore di lavoro in caso di malattia del dipendente?',
    categoria: 'lavoro',
    urgenza: 'alta',
    popolare: false
  },
  {
    id: '4',
    domanda: 'Come funziona il periodo di prova per i nuovi assunti?',
    categoria: 'lavoro',
    urgenza: 'media',
    popolare: true
  },

  // Diritto Fiscale
  {
    id: '5',
    domanda: 'Quali sono le scadenze per il versamento dell\'IVA trimestrale?',
    categoria: 'fiscale',
    urgenza: 'alta',
    popolare: true
  },
  {
    id: '6',
    domanda: 'Come si applica la ritenuta d\'acconto sui compensi professionali?',
    categoria: 'fiscale',
    urgenza: 'alta',
    popolare: true
  },
  {
    id: '7',
    domanda: 'Quali detrazioni sono ammesse per le spese mediche nella dichiarazione dei redditi?',
    categoria: 'fiscale',
    urgenza: 'media',
    popolare: false
  },
  {
    id: '8',
    domanda: 'Come funziona il regime forfettario per le partite IVA?',
    categoria: 'fiscale',
    urgenza: 'alta',
    popolare: true
  },

  // Diritto Commerciale
  {
    id: '9',
    domanda: 'Quali sono i requisiti per costituire una SRL semplificata?',
    categoria: 'commerciale',
    urgenza: 'media',
    popolare: true
  },
  {
    id: '10',
    domanda: 'Come si modifica l\'oggetto sociale di una società di capitali?',
    categoria: 'commerciale',
    urgenza: 'bassa',
    popolare: false
  },
  {
    id: '11',
    domanda: 'Quali sono le responsabilità degli amministratori di una SRL?',
    categoria: 'commerciale',
    urgenza: 'media',
    popolare: true
  },
  {
    id: '12',
    domanda: 'Come si risolve un contratto commerciale per inadempimento?',
    categoria: 'commerciale',
    urgenza: 'alta',
    popolare: false
  },

  // Diritto Civile
  {
    id: '13',
    domanda: 'Quali sono i diritti del locatario in caso di vendita dell\'immobile?',
    categoria: 'civile',
    urgenza: 'alta',
    popolare: true
  },
  {
    id: '14',
    domanda: 'Come si calcola la legittima nell\'eredità?',
    categoria: 'civile',
    urgenza: 'media',
    popolare: false
  },
  {
    id: '15',
    domanda: 'Quali sono i termini di prescrizione per i crediti commerciali?',
    categoria: 'civile',
    urgenza: 'alta',
    popolare: true
  },
  {
    id: '16',
    domanda: 'Come funziona la separazione dei beni tra coniugi?',
    categoria: 'civile',
    urgenza: 'media',
    popolare: false
  },

  // Diritto Amministrativo
  {
    id: '17',
    domanda: 'Quali sono i termini per presentare ricorso contro un atto amministrativo?',
    categoria: 'amministrativo',
    urgenza: 'alta',
    popolare: true
  },
  {
    id: '18',
    domanda: 'Come si richiede l\'accesso agli atti presso la Pubblica Amministrazione?',
    categoria: 'amministrativo',
    urgenza: 'media',
    popolare: false
  },
  {
    id: '19',
    domanda: 'Quali sono i requisiti per ottenere un permesso di costruire?',
    categoria: 'amministrativo',
    urgenza: 'bassa',
    popolare: false
  },
  {
    id: '20',
    domanda: 'Come funziona il silenzio-assenso nei procedimenti amministrativi?',
    categoria: 'amministrativo',
    urgenza: 'media',
    popolare: true
  }
]

export default function DomandeProntePage() {
  const [categoriaSelezionata, setCategoriaSelezionata] = useState<string>('tutte')
  const [searchTerm, setSearchTerm] = useState('')
  const [filtroUrgenza, setFiltroUrgenza] = useState<string>('tutte')

  const domandeFiltrate = domandePreparate.filter(domanda => {
    const matchCategoria = categoriaSelezionata === 'tutte' || domanda.categoria === categoriaSelezionata
    const matchSearch = domanda.domanda.toLowerCase().includes(searchTerm.toLowerCase())
    const matchUrgenza = filtroUrgenza === 'tutte' || domanda.urgenza === filtroUrgenza
    return matchCategoria && matchSearch && matchUrgenza
  })

  const domandePopolar = domandePreparate.filter(d => d.popolare).slice(0, 6)

  const handleQuestionClick = (domanda: string) => {
    // For now, just log the question. In a real app, this would navigate to chat with the question
    console.log('Selected question:', domanda)
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-[#C4BDB4]/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <Link href="/chat">
                <Button
                  variant="ghost"
                  className="text-[#2A5D67] hover:bg-[#F8F5F1]"
                >
                  <ArrowLeft className="w-5 h-5 mr-2" />
                  Torna alla Chat
                </Button>
              </Link>
              <div className="h-6 w-px bg-[#C4BDB4]" />
              <div className="flex items-center">
                <MessageSquare className="w-6 h-6 text-[#D4A574] mr-2" />
                <h1 className="text-xl font-semibold text-[#2A5D67]">
                  Domande Pronte
                </h1>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Intro */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-8"
        >
          <h2 className="text-2xl font-semibold text-[#2A5D67] mb-4">
            Domande Frequenti sulla Normativa Italiana
          </h2>
          <p className="text-[#1E293B] max-w-2xl mx-auto">
            Seleziona una domanda pre-formulata per ottenere risposte immediate sui principali argomenti normativi
          </p>
        </motion.div>

        {/* Search and Filters */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="bg-white rounded-xl shadow-lg p-6 mb-8"
        >
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#C4BDB4] w-5 h-5" />
              <Input
                placeholder="Cerca nelle domande..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 border-[#C4BDB4]/30 focus:border-[#2A5D67]"
              />
            </div>
            <select
              value={filtroUrgenza}
              onChange={(e) => setFiltroUrgenza(e.target.value)}
              className="px-4 py-2 border border-[#C4BDB4]/30 rounded-lg focus:border-[#2A5D67] focus:outline-none"
            >
              <option value="tutte">Tutte le urgenze</option>
              <option value="alta">Alta urgenza</option>
              <option value="media">Media urgenza</option>
              <option value="bassa">Bassa urgenza</option>
            </select>
          </div>
        </motion.div>

        {/* Domande Popolari */}
        {searchTerm === '' && categoriaSelezionata === 'tutte' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mb-8"
          >
            <div className="flex items-center mb-4">
              <TrendingUp className="w-5 h-5 text-[#D4A574] mr-2" />
              <h3 className="text-lg font-semibold text-[#2A5D67]">
                Domande Più Richieste
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {domandePopolar.map((domanda, index) => {
                const categoria = categorieNormative.find(c => c.id === domanda.categoria)
                return (
                  <motion.button
                    key={domanda.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: index * 0.05 }}
                    onClick={() => handleQuestionClick(domanda.domanda)}
                    className="bg-white rounded-lg p-4 shadow-md hover:shadow-lg transition-all duration-200 text-left group border border-transparent hover:border-[#D4A574]"
                  >
                    <div className="flex items-start space-x-3">
                      {categoria && (
                        <categoria.icon 
                          className="w-5 h-5 text-[#D4A574] mt-1 flex-shrink-0" 
                        />
                      )}
                      <div className="flex-1">
                        <p className="text-sm text-[#1E293B] group-hover:text-[#2A5D67] transition-colors">
                          {domanda.domanda}
                        </p>
                        {categoria && (
                          <span className="inline-block mt-2 text-xs px-2 py-1 bg-[#F8F5F1] text-[#2A5D67] rounded-full">
                            {categoria.nome}
                          </span>
                        )}
                      </div>
                      <ChevronRight className="w-4 h-4 text-[#C4BDB4] group-hover:text-[#D4A574] transition-colors" />
                    </div>
                  </motion.button>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* Categorie */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mb-8"
        >
          <h3 className="text-lg font-semibold text-[#2A5D67] mb-4">
            Aree di Interesse
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <button
              onClick={() => setCategoriaSelezionata('tutte')}
              className={`p-4 rounded-lg text-left transition-all duration-200 ${
                categoriaSelezionata === 'tutte'
                  ? 'bg-[#2A5D67] text-white shadow-lg'
                  : 'bg-white text-[#2A5D67] hover:bg-[#F8F5F1] shadow-md'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Scale className="w-6 h-6" />
                <div>
                  <h4 className="font-medium">Tutte le Categorie</h4>
                  <p className={`text-sm ${categoriaSelezionata === 'tutte' ? 'text-white/80' : 'text-[#1E293B]'}`}>
                    Visualizza tutte le domande
                  </p>
                </div>
              </div>
            </button>
            
            {categorieNormative.map((categoria, index) => (
              <motion.button
                key={categoria.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, delay: index * 0.05 }}
                onClick={() => setCategoriaSelezionata(categoria.id)}
                className={`p-4 rounded-lg text-left transition-all duration-200 ${
                  categoriaSelezionata === categoria.id
                    ? 'bg-[#2A5D67] text-white shadow-lg'
                    : 'bg-white text-[#2A5D67] hover:bg-[#F8F5F1] shadow-md'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <categoria.icon className="w-6 h-6" />
                  <div>
                    <h4 className="font-medium">{categoria.nome}</h4>
                    <p className={`text-sm ${categoriaSelezionata === categoria.id ? 'text-white/80' : 'text-[#1E293B]'}`}>
                      {categoria.descrizione}
                    </p>
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* Lista Domande */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-[#2A5D67]">
              {categoriaSelezionata === 'tutte' ? 'Tutte le Domande' : 
               `Domande - ${categorieNormative.find(c => c.id === categoriaSelezionata)?.nome}`}
            </h3>
            <span className="text-sm text-[#1E293B]">
              {domandeFiltrate.length} domande trovate
            </span>
          </div>

          <div className="space-y-3">
            {domandeFiltrate.map((domanda, index) => {
              const categoria = categorieNormative.find(c => c.id === domanda.categoria)
              return (
                <motion.button
                  key={domanda.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.4, delay: index * 0.02 }}
                  onClick={() => handleQuestionClick(domanda.domanda)}
                  className="w-full bg-white rounded-lg p-4 shadow-md hover:shadow-lg transition-all duration-200 text-left group border border-transparent hover:border-[#D4A574]"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        {categoria && (
                          <>
                            <categoria.icon className="w-4 h-4 text-[#D4A574]" />
                            <span className="text-xs px-2 py-1 bg-[#F8F5F1] text-[#2A5D67] rounded-full">
                              {categoria.nome}
                            </span>
                          </>
                        )}
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          domanda.urgenza === 'alta' ? 'bg-red-100 text-red-600' :
                          domanda.urgenza === 'media' ? 'bg-yellow-100 text-yellow-600' :
                          'bg-green-100 text-green-600'
                        }`}>
                          {domanda.urgenza === 'alta' ? 'Alta urgenza' :
                           domanda.urgenza === 'media' ? 'Media urgenza' : 'Bassa urgenza'}
                        </span>
                        {domanda.popolare && (
                          <TrendingUp className="w-4 h-4 text-[#D4A574]" />
                        )}
                      </div>
                      <p className="text-[#1E293B] group-hover:text-[#2A5D67] transition-colors">
                        {domanda.domanda}
                      </p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-[#C4BDB4] group-hover:text-[#D4A574] transition-colors ml-4" />
                  </div>
                </motion.button>
              )
            })}
          </div>

          {domandeFiltrate.length === 0 && (
            <div className="text-center py-12">
              <Search className="w-12 h-12 text-[#C4BDB4] mx-auto mb-4" />
              <h3 className="text-lg font-medium text-[#2A5D67] mb-2">
                Nessuna domanda trovata
              </h3>
              <p className="text-[#1E293B]">
                Prova a modificare i filtri di ricerca o seleziona una categoria diversa
              </p>
            </div>
          )}
        </motion.div>

        {/* Work in Progress Overlay */}
        <div 
          className="fixed inset-0 bg-white/60 backdrop-blur-[2px] z-50 flex items-center justify-center cursor-pointer"
          onClick={() => window.location.href = '/chat'}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl border border-[#C4BDB4]/30 p-10 text-center max-w-lg mx-4 cursor-default"
            onClick={(e) => e.stopPropagation()}
          >
            <motion.div
              animate={{ 
                rotate: [0, 10, -10, 0],
                scale: [1, 1.1, 1]
              }}
              transition={{ 
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
              className="w-16 h-16 bg-[#2A5D67] rounded-2xl flex items-center justify-center mx-auto mb-6"
            >
              <motion.div
                animate={{ 
                  scale: [1, 1.2, 1],
                  rotate: [0, 5, -5, 0]
                }}
                transition={{ 
                  duration: 1.5,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: 0.5
                }}
              >
                <Brain className="w-8 h-8 text-white" />
              </motion.div>
            </motion.div>
            
            <h3 className="text-2xl font-semibold text-[#2A5D67] mb-4">
              Funzionalità in Sviluppo
            </h3>
            
            <p className="text-[#1E293B] text-lg leading-relaxed mb-2">
              Stiamo perfezionando il sistema di domande pronte per offrirti la migliore esperienza possibile.
            </p>
            <p className="text-[#C4BDB4] text-sm">
              Intravedi un&apos;anteprima di quello che ti aspetta...
            </p>
          </motion.div>
        </div>
      </div>
    </div>
  )
}