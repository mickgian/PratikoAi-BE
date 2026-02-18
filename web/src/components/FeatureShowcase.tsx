'use client'

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { RefreshCw, MessageSquare, FileText, ExternalLink, Check } from 'lucide-react'
import { Badge } from './ui/badge'

interface Feature {
  id: string
  title: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  description: string
  color: string
  content: {
    title: string
    subtitle: string
    features: string[]
    mockData: {
      conversation?: Array<{
        type: string
        message: string
        time: string
        sources?: string[]
      }>
      updates?: Array<{
        time: string
        title: string
        type: string
        status: string
      }>
      analysis?: {
        fileName: string
        type: string
        status: string
        findings: Array<{
          type: string
          text: string
        }>
        suggestions: string[]
      }
    }
  }
}

export function FeatureShowcase() {
  const [activeTab, setActiveTab] = useState(0)

  const features: Feature[] = [
    {
      id: 'risposte',
      title: 'Risposte Immediate', 
      icon: MessageSquare,
      description: 'Chat intelligente con citazione delle fonti',
      color: '#A9C1B7',
      content: {
        title: 'Domande Complesse, Risposte Chiare',
        subtitle: 'L\'AI analizza il contesto e fornisce risposte precise',
        features: [
          'Elaborazione del linguaggio naturale avanzata',
          'Citazioni dirette delle fonti normative',
          'Contesto specifico per ogni risposta',
          'Cronologia delle domande per reference'
        ],
        mockData: {
          conversation: [
            {
              type: 'user',
              message: 'Quali sono le novità per le detrazioni fiscali 2024?',
              time: '14:30'
            },
            {
              type: 'ai',
              message: 'In base alla Circolare 15/E del 2024, le principali novità includono:\\n\\n• Detrazione al 50% per interventi di efficientamento energetico\\n• Nuovi limiti per le spese mediche (€8.000)\\n• Estensione del bonus mobili fino a dicembre 2024\\n\\nFonte: Circolare Agenzia Entrate 15/E/2024, art. 3-7',
              time: '14:30',
              sources: ['Circolare 15/E/2024', 'Art. 16-bis TUIR']
            }
          ]
        }
      }
    },
    {
      id: 'aggiornamenti',
      title: 'Aggiornamenti Automatici',
      icon: RefreshCw,
      description: 'Monitoriamo continuamente Agenzia Entrate, INPS e MEF',
      color: '#2A5D67',
      content: {
        title: 'Sempre Aggiornato, Sempre Avanti',
        subtitle: 'Il sistema controlla le fonti ufficiali ogni 4 ore',
        features: [
          'Scansione automatica di Agenzia delle Entrate',
          'Monitoraggio INPS e MEF in tempo reale', 
          'Notifiche immediate per modifiche rilevanti',
          'Storico completo delle variazioni normative'
        ],
        mockData: {
          updates: [
            { time: '2 ore fa', title: 'Circolare 15/E - Nuove detrazioni 2024', type: 'Agenzia Entrate', status: 'new' },
            { time: '6 ore fa', title: 'Messaggio 1247 - Aggiornamento CU 2024', type: 'INPS', status: 'updated' },
            { time: '1 giorno fa', title: 'Decreto MEF - Modifiche codici tributo', type: 'MEF', status: 'important' }
          ]
        }
      }
    },
    {
      id: 'analisi', 
      title: 'Analisi Documenti',
      icon: FileText,
      description: 'Upload e analisi automatica di fatture e contratti',
      color: '#DCC7A1',
      content: {
        title: 'Documenti Analizzati in Secondi',
        subtitle: 'Carica qualsiasi documento e ottieni un\'analisi dettagliata',
        features: [
          'Riconoscimento automatico tipo documento',
          'Estrazione dati fiscalmente rilevanti',
          'Controllo conformità normativa',
          'Suggerimenti per ottimizzazione fiscale'
        ],
        mockData: {
          analysis: {
            fileName: 'Fattura_Elettronica_2024_001.xml',
            type: 'Fattura Elettronica',
            status: 'Analizzata',
            findings: [
              { type: 'info', text: 'IVA al 22% applicata correttamente' },
              { type: 'warning', text: 'Codice destinatario mancante - può causare ritardi' },
              { type: 'success', text: 'Formato XML conforme alle specifiche' }
            ],
            suggestions: [
              'Considera l\'utilizzo del reverse charge per questa categoria',
              'Verifica la detraibilità IVA per questo fornitore'
            ]
          }
        }
      }
    }
  ]

  const TabContent = ({ feature }: { feature: Feature }) => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
      className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start"
    >
      {/* Left Content */}
      <div className="space-y-6">
        <div>
          <h3 className="text-3xl font-bold text-[#2A5D67] mb-3">
            {feature.content.title}
          </h3>
          <p className="text-lg text-[#1E293B] mb-6">
            {feature.content.subtitle}
          </p>
        </div>

        <div className="space-y-4">
          {feature.content.features.map((feat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className="flex items-start space-x-3"
            >
              <div className="flex-shrink-0 w-6 h-6 bg-[#2A5D67] rounded-full flex items-center justify-center mt-0.5">
                <Check className="w-3 h-3 text-white" />
              </div>
              <span className="text-[#1E293B]">{feat}</span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Right Mock Interface */}
      <div className="bg-white rounded-2xl shadow-xl border border-[#C4BDB4]/20 overflow-hidden">
        {/* Chat Interface for Risposte Immediate (now index 0) */}
        {activeTab === 0 && (
          <div className="p-6">
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {feature.content.mockData.conversation?.map((msg, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.3 }}
                  className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`max-w-xs lg:max-w-md p-4 rounded-2xl ${
                      msg.type === 'user'
                        ? 'bg-[#F8F5F1] text-[#1E293B]'
                        : 'bg-[#A9C1B7]/15 text-[#1E293B]'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-line">{msg.message}</p>
                    {msg.sources && (
                      <div className="mt-3 pt-2 border-t border-[#C4BDB4]/20">
                        <p className="text-xs text-[#2A5D67] font-medium mb-1">Fonti:</p>
                        <div className="flex flex-wrap gap-1">
                          {msg.sources.map((source, i) => (
                            <Badge key={i} variant="outline" className="text-xs">
                              {source}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    <span className="text-xs text-[#C4BDB4] mt-2 block">{msg.time}</span>
                  </div>
                </motion.div>
              ))}
            </div>
            
            <div className="mt-4 p-3 bg-[#F8F5F1] rounded-lg flex items-center space-x-2">
              <input 
                type="text" 
                placeholder="Scrivi la tua domanda..."
                className="flex-1 bg-transparent border-none outline-none text-[#1E293B] placeholder-[#C4BDB4]"
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-[#2A5D67] text-white p-2 rounded-lg"
              >
                <MessageSquare className="w-4 h-4" />
              </motion.button>
            </div>
          </div>
        )}

        {/* Updates Interface for Aggiornamenti Automatici (now index 1) */}
        {activeTab === 1 && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold text-[#1E293B]">Aggiornamenti Recenti</h4>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              >
                <RefreshCw className="w-4 h-4 text-[#2A5D67]" />
              </motion.div>
            </div>
            <div className="space-y-3">
              {feature.content.mockData.updates?.map((update, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.2 }}
                  className={`p-4 rounded-lg border-l-4 ${
                    update.status === 'new' 
                      ? 'border-l-[#2A5D67] bg-[#F8F5F1]'
                      : update.status === 'important'
                      ? 'border-l-[#DCC7A1] bg-[#DCC7A1]/10'
                      : 'border-l-[#A9C1B7] bg-[#A9C1B7]/10'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <Badge variant="secondary" className="text-xs">
                          {update.type}
                        </Badge>
                        <span className="text-xs text-[#C4BDB4]">{update.time}</span>
                      </div>
                      <p className="text-sm text-[#1E293B] font-medium">{update.title}</p>
                    </div>
                    <ExternalLink className="w-4 h-4 text-[#2A5D67] flex-shrink-0 ml-2" />
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Document Analysis Interface (remains at index 2) */}
        {activeTab === 2 && (
          <div className="p-6">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-[#DCC7A1]/20 rounded-full flex items-center justify-center mx-auto mb-3">
                <FileText className="w-8 h-8 text-[#2A5D67]" />
              </div>
              <h4 className="font-semibold text-[#1E293B] mb-2">
                {feature.content.mockData.analysis?.fileName}
              </h4>
              <Badge className="bg-[#2A5D67]/10 text-[#2A5D67]">
                {feature.content.mockData.analysis?.type}
              </Badge>
            </div>

            <motion.div
              initial={{ width: 0 }}
              animate={{ width: '100%' }}
              transition={{ duration: 2, delay: 0.5 }}
              className="h-2 bg-[#2A5D67] rounded-full mb-6"
            />

            <div className="space-y-3 mb-6">
              {feature.content.mockData.analysis?.findings.map((finding, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.8 + index * 0.2 }}
                  className={`p-3 rounded-lg text-sm ${
                    finding.type === 'success' 
                      ? 'bg-green-50 text-green-800 border-l-4 border-green-400'
                      : finding.type === 'warning'
                      ? 'bg-yellow-50 text-yellow-800 border-l-4 border-yellow-400'
                      : 'bg-blue-50 text-blue-800 border-l-4 border-blue-400'
                  }`}
                >
                  {finding.text}
                </motion.div>
              ))}
            </div>

            <div className="border-t border-[#C4BDB4]/20 pt-4">
              <h5 className="font-medium text-[#2A5D67] mb-2">Suggerimenti:</h5>
              <div className="space-y-2">
                {feature.content.mockData.analysis?.suggestions.map((suggestion, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.2 + index * 0.1 }}
                    className="text-sm text-[#1E293B] flex items-start space-x-2"
                  >
                    <span className="text-[#DCC7A1]">•</span>
                    <span>{suggestion}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )

  return (
    <section className="bg-[#F8F5F1] py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold text-[#2A5D67] mb-4">
            Funzionalità Avanzate per Professionisti
          </h2>
          <p className="text-xl text-[#1E293B] max-w-3xl mx-auto">
            Ogni strumento è progettato per ottimizzare il tuo workflow quotidiano
          </p>
        </motion.div>

        {/* Tab Headers */}
        <div className="flex flex-col sm:flex-row justify-center mb-12 bg-white rounded-2xl p-2 shadow-lg border border-[#C4BDB4]/20 max-w-3xl mx-auto gap-2">
          {features.map((feature, index) => (
            <motion.button
              key={feature.id}
              onClick={() => setActiveTab(index)}
              className={`flex-1 flex items-center justify-center space-x-3 p-4 rounded-xl transition-all duration-300 ${
                activeTab === index
                  ? 'bg-[#2A5D67] text-white shadow-lg'
                  : 'text-[#1E293B] bg-[#F8F5F1]/50 hover:bg-[#F8F5F1] hover:shadow-md shadow-sm'
              }`}
              whileHover={{ scale: activeTab === index ? 1 : 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <feature.icon className={`w-5 h-5 ${
                activeTab === index ? 'text-white' : 'text-[#2A5D67]'
              }`} />
              <span className="font-medium text-sm sm:text-base">{feature.title}</span>
            </motion.button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            className="bg-white rounded-2xl shadow-xl border border-[#C4BDB4]/20 p-8"
          >
            <TabContent feature={features[activeTab]} />
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  )
}