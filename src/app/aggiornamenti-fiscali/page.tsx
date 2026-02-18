'use client'

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Button } from '../../components/ui/button'
import { 
  ArrowLeft, 
  AlertTriangle, 
  Clock, 
  Zap,
  Bell,
  Star,
  Eye,
  Download,
  Share2,
  Calendar,
  Tag,
  ExternalLink,
  TrendingUp,
  AlertCircle,
  Info,
  CheckCircle,
  XCircle,
  Target,
  Building,
  Users,
  FileText,
  Search,
  Filter,
  Brain
} from 'lucide-react'
import Link from 'next/link'

interface AggiornamentoUrgente {
  id: string
  title: string
  description: string
  summary: string
  urgency: 'critico' | 'alto' | 'medio'
  category: 'fiscale' | 'societario' | 'lavoro' | 'contratti' | 'procedimenti'
  date: string
  deadline?: string
  source: string
  tags: string[]
  impact: string[]
  actions: string[]
  isRead: boolean
  isBookmarked: boolean
  views: number
  relatedDocs: string[]
}

export default function AggiornamentiFiscaliPage() {
  const [selectedUrgency, setSelectedUrgency] = useState<string>('all')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'date' | 'urgency' | 'views'>('urgency')

  const urgencyLevels = [
    { id: 'critico', name: 'Critico', color: 'bg-red-100 text-red-700 border-red-200', count: 3 },
    { id: 'alto', name: 'Alto', color: 'bg-orange-100 text-orange-700 border-orange-200', count: 5 },
    { id: 'medio', name: 'Medio', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', count: 4 }
  ]

  const categories = [
    { id: 'fiscale', name: 'Fiscale', icon: Building, count: 8 },
    { id: 'societario', name: 'Societario', icon: Building, count: 3 },
    { id: 'lavoro', name: 'Lavoro', icon: Users, count: 2 },
    { id: 'contratti', name: 'Contratti', icon: FileText, count: 2 },
    { id: 'procedimenti', name: 'Procedimenti', icon: AlertCircle, count: 1 }
  ]

  const mockAggiornamenti: AggiornamentoUrgente[] = [
    {
      id: '1',
      title: 'URGENTE: Modifica scadenze versamenti IVA - Febbraio 2025',
      description: 'L\'Agenzia delle Entrate ha comunicato lo slittamento della scadenza per i versamenti IVA del mese di gennaio 2025 dal 16 al 20 febbraio.',
      summary: 'Importante proroga che interessa tutti i contribuenti IVA mensili. La scadenza viene posticipata di 4 giorni per problemi tecnici al sistema telematico.',
      urgency: 'critico',
      category: 'fiscale',
      date: '2025-01-15',
      deadline: '2025-02-20',
      source: 'Agenzia delle Entrate',
      tags: ['IVA', 'Scadenze', 'Versamenti', 'Proroga'],
      impact: ['Contribuenti IVA mensili', 'Sostituti d\'imposta', 'Professionisti'],
      actions: ['Aggiorna calendari scadenze', 'Informa i clienti', 'Riprogramma versamenti'],
      isRead: false,
      isBookmarked: true,
      views: 2341,
      relatedDocs: ['Comunicato AdE n. 15/2025', 'Circolare 2/2025']
    },
    {
      id: '2',
      title: 'CRITICO: Nuovi obblighi fatturazione elettronica per forfettari',
      description: 'Dal 1° marzo 2025 estensione obbligatoria della fatturazione elettronica anche ai regimi forfettari con ricavi superiori a €25.000.',
      summary: 'Cambiamento significativo che impatta una vasta platea di contribuenti in regime forfettario, richiedendo immediate azioni di adeguamento.',
      urgency: 'critico',
      category: 'fiscale',
      date: '2025-01-12',
      deadline: '2025-03-01',
      source: 'Decreto Legge 8/2025',
      tags: ['Fatturazione Elettronica', 'Regime Forfettario', 'Adempimenti'],
      impact: ['Forfettari >€25k', 'Software house', 'Commercialisti'],
      actions: ['Verificare soglie clienti', 'Attivare fatturazione elettronica', 'Aggiornare software'],
      isRead: false,
      isBookmarked: false,
      views: 1987,
      relatedDocs: ['DL 8/2025', 'Istruzioni operative AdE']
    },
    {
      id: '3',
      title: 'ALTO: Sospensione termini processuali per eventi atmosferici',
      description: 'Sospensione dei termini processuali per i tribunali delle regioni Emilia-Romagna e Marche dal 14 al 28 gennaio 2025.',
      summary: 'Misura eccezionale dovuta alle condizioni meteorologiche avverse che hanno colpito le regioni del centro-nord Italia.',
      urgency: 'alto',
      category: 'procedimenti',
      date: '2025-01-14',
      deadline: '2025-01-28',
      source: 'Ministero della Giustizia',
      tags: ['Sospensione Termini', 'Tribunali', 'Emergenza Meteo'],
      impact: ['Avvocati Emilia-Romagna/Marche', 'Procedure in corso', 'Scadenze processuali'],
      actions: ['Verificare procedure pendenti', 'Ricalcolare scadenze', 'Informare clienti'],
      isRead: true,
      isBookmarked: false,
      views: 876,
      relatedDocs: ['Decreto sospensione 14/01/2025']
    },
    {
      id: '4',
      title: 'MEDIO: Aggiornamento coefficienti redditività 2025',
      description: 'Pubblicati i nuovi coefficienti di redditività per il calcolo degli studi di settore e parametri 2025.',
      summary: 'Aggiornamento annuale dei coefficienti che determina l\'adeguamento automatico per contribuenti che utilizzano gli studi di settore.',
      urgency: 'medio',
      category: 'fiscale',
      date: '2025-01-10',
      source: 'Decreto Ministeriale',
      tags: ['Coefficienti Redditività', 'Studi di Settore', 'Parametri'],
      impact: ['Contribuenti studi settore', 'Professionisti', 'Piccole imprese'],
      actions: ['Aggiornare software', 'Verificare nuovi parametri', 'Controllare adeguamento'],
      isRead: true,
      isBookmarked: true,
      views: 654,
      relatedDocs: ['DM Coefficienti 2025', 'Tabelle aggiornate']
    },
    {
      id: '5',
      title: 'ALTO: Modifiche contributive INPS per consulenti',
      description: 'Nuove aliquote contributive per consulenti del lavoro e professionisti iscritti alla Gestione Separata INPS.',
      summary: 'Incremento dell\'aliquota contributiva dal 25% al 26% per i professionisti senza cassa, efficace da marzo 2025.',
      urgency: 'alto',
      category: 'lavoro',
      date: '2025-01-08',
      deadline: '2025-03-01',
      source: 'INPS Circolare 7/2025',
      tags: ['Contributi INPS', 'Gestione Separata', 'Aliquote'],
      impact: ['Consulenti del lavoro', 'Professionisti senza cassa', 'Collaboratori'],
      actions: ['Aggiornare calcoli contributi', 'Informare clienti', 'Modificare contratti'],
      isRead: false,
      isBookmarked: false,
      views: 1123,
      relatedDocs: ['Circolare INPS 7/2025', 'Tabelle contributive']
    },
    {
      id: '6',
      title: 'CRITICO: Blocco sistema telematico Cassetto Fiscale',
      description: 'Interruzione del servizio Cassetto Fiscale dell\'Agenzia delle Entrate dalle 14:00 del 15/01 alle 08:00 del 16/01.',
      summary: 'Manutenzione straordinaria che impedisce l\'accesso ai documenti fiscali e la consultazione delle pratiche in corso.',
      urgency: 'critico',
      category: 'fiscale',
      date: '2025-01-15',
      deadline: '2025-01-16',
      source: 'Agenzia delle Entrate',
      tags: ['Cassetto Fiscale', 'Manutenzione', 'Servizi Telematici'],
      impact: ['Tutti gli utenti', 'Commercialisti', 'CAF'],
      actions: ['Pianificare attività alternative', 'Avvisare clienti', 'Rimandare pratiche urgenti'],
      isRead: false,
      isBookmarked: false,
      views: 3456,
      relatedDocs: ['Avviso interruzione servizi']
    }
  ]

  const getUrgencyInfo = (urgency: string) => {
    return urgencyLevels.find(level => level.id === urgency) || urgencyLevels[2]
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('it-IT', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const getDaysUntilDeadline = (deadline?: string) => {
    if (!deadline) return null
    const now = new Date()
    const deadlineDate = new Date(deadline)
    const diffTime = deadlineDate.getTime() - now.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays
  }

  const filteredAggiornamenti = mockAggiornamenti.filter(aggiornamento => {
    const matchesUrgency = selectedUrgency === 'all' || aggiornamento.urgency === selectedUrgency
    const matchesCategory = selectedCategory === 'all' || aggiornamento.category === selectedCategory
    const matchesSearch = aggiornamento.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         aggiornamento.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         aggiornamento.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
    return matchesUrgency && matchesCategory && matchesSearch
  })

  const sortedAggiornamenti = [...filteredAggiornamenti].sort((a, b) => {
    switch (sortBy) {
      case 'urgency':
        const urgencyOrder = { 'critico': 3, 'alto': 2, 'medio': 1 }
        return urgencyOrder[b.urgency] - urgencyOrder[a.urgency]
      case 'date':
        return new Date(b.date).getTime() - new Date(a.date).getTime()
      case 'views':
        return b.views - a.views
      default:
        return 0
    }
  })

  const criticalCount = mockAggiornamenti.filter(a => a.urgency === 'critico' && !a.isRead).length
  const unreadCount = mockAggiornamenti.filter(a => !a.isRead).length

  return (
    <div className="min-h-screen bg-[#F8F5F1] relative">
      <div className="relative">
        {/* Header */}
        <div className="bg-white border-b border-[#C4BDB4]/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Link href="/chat">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-[#2A5D67] hover:bg-[#F8F5F1]"
                  >
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Torna alla Chat
                  </Button>
                </Link>
                <div className="w-px h-6 bg-[#C4BDB4]" />
                <div>
                  <div className="flex items-center space-x-3">
                    <h1 className="text-2xl font-bold text-[#2A5D67]">Aggiornamenti Urgenti</h1>
                    {criticalCount > 0 && (
                      <motion.span
                        animate={{ scale: [1, 1.1, 1] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full border border-red-200"
                      >
                        {criticalCount} critic{criticalCount === 1 ? 'o' : 'i'}
                      </motion.span>
                    )}
                    {unreadCount > 0 && (
                      <span className="px-2 py-1 bg-[#D4A574] text-white text-xs font-medium rounded-full">
                        {unreadCount} non lett{unreadCount === 1 ? 'o' : 'i'}
                      </span>
                    )}
                  </div>
                  <p className="text-[#1E293B] text-sm">Monitoraggio in tempo reale degli aggiornamenti critici</p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                >
                  <Bell className="w-4 h-4 mr-2" />
                  Notifiche
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Report
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Critical Alerts Bar */}
        {criticalCount > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-r from-red-600 to-red-500 text-white py-3"
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <motion.div
                    animate={{ rotate: [0, 15, -15, 0] }}
                    transition={{ duration: 0.5, repeat: Infinity, repeatDelay: 2 }}
                  >
                    <AlertTriangle className="w-5 h-5" />
                  </motion.div>
                  <span className="font-medium">
                    {criticalCount} aggiornament{criticalCount === 1 ? 'o critico richiede' : 'i critici richiedono'} attenzione immediata
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-white hover:bg-white/20"
                  onClick={() => setSelectedUrgency('critico')}
                >
                  Visualizza
                </Button>
              </div>
            </div>
          </motion.div>
        )}

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Sidebar */}
            <div className="lg:col-span-1">
              <div className="space-y-6">
                {/* Search */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">Cerca Aggiornamenti</h3>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[#C4BDB4]" />
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Cerca per titolo, tag..."
                      className="w-full pl-10 pr-4 py-3 border border-[#C4BDB4]/20 rounded-lg focus:ring-2 focus:ring-[#2A5D67]/20 focus:border-[#2A5D67] transition-all"
                    />
                  </div>
                </div>

                {/* Urgency Levels */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">Livello di Urgenza</h3>
                  <div className="space-y-2">
                    <button
                      onClick={() => setSelectedUrgency('all')}
                      className={`w-full text-left p-3 rounded-lg transition-all ${
                        selectedUrgency === 'all' 
                          ? 'bg-[#2A5D67] text-white' 
                          : 'hover:bg-[#F8F5F1] text-[#1E293B]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>Tutti i Livelli</span>
                        <span className="text-sm opacity-70">{mockAggiornamenti.length}</span>
                      </div>
                    </button>
                    
                    {urgencyLevels.map((level) => {
                      const icon = level.id === 'critico' ? Zap : level.id === 'alto' ? AlertTriangle : Info
                      const IconComponent = icon
                      
                      return (
                        <motion.button
                          key={level.id}
                          onClick={() => setSelectedUrgency(level.id)}
                          whileHover={{ scale: 1.02 }}
                          className={`w-full text-left p-3 rounded-lg transition-all ${
                            selectedUrgency === level.id 
                              ? 'bg-[#2A5D67] text-white' 
                              : 'hover:bg-[#F8F5F1] text-[#1E293B]'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              <IconComponent className="w-4 h-4" />
                              <span className="text-sm">{level.name}</span>
                            </div>
                            <span className="text-xs opacity-70">{level.count}</span>
                          </div>
                        </motion.button>
                      )
                    })}
                  </div>
                </div>

                {/* Categories */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">Categorie</h3>
                  <div className="space-y-2">
                    <button
                      onClick={() => setSelectedCategory('all')}
                      className={`w-full text-left p-2 rounded-lg transition-all ${
                        selectedCategory === 'all' 
                          ? 'bg-[#F8F5F1] text-[#2A5D67] font-medium' 
                          : 'text-[#1E293B] hover:bg-[#F8F5F1]'
                      }`}
                    >
                      Tutte le Categorie
                    </button>
                    
                    {categories.map((category) => (
                      <button
                        key={category.id}
                        onClick={() => setSelectedCategory(category.id)}
                        className={`w-full text-left p-2 rounded-lg transition-all ${
                          selectedCategory === category.id 
                            ? 'bg-[#F8F5F1] text-[#2A5D67] font-medium' 
                            : 'text-[#1E293B] hover:bg-[#F8F5F1]'
                        }`}
                      >
                        <div className="flex justify-between">
                          <span className="text-sm">{category.name}</span>
                          <span className="text-xs text-[#C4BDB4]">{category.count}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Sort Options */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">Ordina per</h3>
                  <div className="space-y-2">
                    {[
                      { key: 'urgency', label: 'Urgenza' },
                      { key: 'date', label: 'Data' },
                      { key: 'views', label: 'Visualizzazioni' }
                    ].map((option) => (
                      <button
                        key={option.key}
                        onClick={() => setSortBy(option.key as 'date' | 'urgency' | 'views')}
                        className={`w-full text-left p-2 rounded-lg transition-all ${
                          sortBy === option.key 
                            ? 'bg-[#F8F5F1] text-[#2A5D67] font-medium' 
                            : 'text-[#1E293B] hover:bg-[#F8F5F1]'
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-3">
              {/* Results Header */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-semibold text-[#2A5D67]">
                    {selectedUrgency === 'all' ? 'Tutti gli Aggiornamenti' : 
                     `Aggiornamenti ${urgencyLevels.find(l => l.id === selectedUrgency)?.name}`}
                  </h2>
                  <p className="text-[#1E293B] mt-1">
                    {sortedAggiornamenti.length} aggiornament{sortedAggiornamenti.length !== 1 ? 'i' : 'o'} trovat{sortedAggiornamenti.length !== 1 ? 'i' : 'o'}
                  </p>
                </div>
              </div>

              {/* Updates List */}
              <div className="space-y-6">
                {sortedAggiornamenti.map((aggiornamento, index) => {
                  const urgencyInfo = getUrgencyInfo(aggiornamento.urgency)
                  const daysUntilDeadline = getDaysUntilDeadline(aggiornamento.deadline)
                  
                  return (
                    <motion.div
                      key={aggiornamento.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className={`bg-white rounded-xl shadow-sm border transition-all hover:shadow-md ${
                        aggiornamento.urgency === 'critico' && !aggiornamento.isRead 
                          ? 'border-red-200 bg-red-50' 
                          : 'border-[#C4BDB4]/20'
                      }`}
                    >
                      <div className="p-6">
                        {/* Header */}
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3 mb-2">
                              {!aggiornamento.isRead && (
                                <span className="w-2 h-2 bg-[#D4A574] rounded-full"></span>
                              )}
                              <span className={`px-2 py-1 text-xs font-medium rounded-md border ${urgencyInfo.color}`}>
                                {urgencyInfo.name.toUpperCase()}
                              </span>
                              {aggiornamento.urgency === 'critico' && (
                                <motion.div
                                  animate={{ scale: [1, 1.2, 1] }}
                                  transition={{ duration: 2, repeat: Infinity }}
                                >
                                  <Zap className="w-4 h-4 text-red-500" />
                                </motion.div>
                              )}
                              {daysUntilDeadline !== null && daysUntilDeadline <= 3 && (
                                <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded-full">
                                  {daysUntilDeadline === 0 ? 'Oggi' : `${daysUntilDeadline} giorni`}
                                </span>
                              )}
                            </div>
                            <h3 className="text-lg font-semibold text-[#2A5D67] mb-2">
                              {aggiornamento.title}
                            </h3>
                            <p className="text-[#1E293B] mb-3">
                              {aggiornamento.description}
                            </p>
                            <p className="text-[#1E293B] text-sm leading-relaxed mb-4">
                              {aggiornamento.summary}
                            </p>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            className={`ml-4 ${
                              aggiornamento.isBookmarked 
                                ? 'text-[#D4A574] hover:text-[#D4A574]/80' 
                                : 'text-[#C4BDB4] hover:text-[#D4A574]'
                            }`}
                          >
                            <Star className={`w-4 h-4 ${aggiornamento.isBookmarked ? 'fill-current' : ''}`} />
                          </Button>
                        </div>

                        {/* Meta Info */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-sm">
                          <div className="flex items-center space-x-2">
                            <Building className="w-4 h-4 text-[#C4BDB4]" />
                            <span className="text-[#1E293B]">{aggiornamento.source}</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Calendar className="w-4 h-4 text-[#C4BDB4]" />
                            <span className="text-[#1E293B]">
                              {formatDate(aggiornamento.date)}
                            </span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Eye className="w-4 h-4 text-[#C4BDB4]" />
                            <span className="text-[#1E293B]">
                              {aggiornamento.views.toLocaleString()} views
                            </span>
                          </div>
                        </div>

                        {/* Impact */}
                        <div className="mb-4">
                          <h4 className="text-sm font-medium text-[#2A5D67] mb-2">Impatto su:</h4>
                          <div className="flex flex-wrap gap-2">
                            {aggiornamento.impact.map((item, itemIndex) => (
                              <span
                                key={itemIndex}
                                className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-md"
                              >
                                {item}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Actions Required */}
                        <div className="mb-4">
                          <h4 className="text-sm font-medium text-[#2A5D67] mb-2">Azioni richieste:</h4>
                          <div className="space-y-1">
                            {aggiornamento.actions.map((action, actionIndex) => (
                              <div key={actionIndex} className="flex items-center space-x-2 text-sm">
                                <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
                                <span className="text-[#1E293B]">{action}</span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Tags */}
                        <div className="flex flex-wrap gap-2 mb-4">
                          {aggiornamento.tags.map((tag, tagIndex) => (
                            <span
                              key={tagIndex}
                              className="px-2 py-1 bg-[#F8F5F1] text-[#2A5D67] text-xs rounded-md"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            {aggiornamento.deadline && (
                              <div className="flex items-center space-x-1 text-xs text-[#C4BDB4]">
                                <Clock className="w-3 h-3" />
                                <span>Scadenza: {formatDate(aggiornamento.deadline)}</span>
                              </div>
                            )}
                          </div>
                          <div className="flex space-x-2">
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                            >
                              <Share2 className="w-4 h-4 mr-2" />
                              Condividi
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                            >
                              <ExternalLink className="w-4 h-4 mr-2" />
                              Dettagli
                            </Button>
                            <Button
                              size="sm"
                              className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                            >
                              {aggiornamento.isRead ? (
                                <>
                                  <CheckCircle className="w-4 h-4 mr-2" />
                                  Letto
                                </>
                              ) : (
                                <>
                                  <Eye className="w-4 h-4 mr-2" />
                                  Segna come Letto
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )
                })}
              </div>

              {/* Empty State */}
              {sortedAggiornamenti.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-12 bg-white rounded-xl border border-[#C4BDB4]/20"
                >
                  <AlertCircle className="w-16 h-16 text-[#C4BDB4] mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-[#2A5D67] mb-2">
                    Nessun aggiornamento trovato
                  </h3>
                  <p className="text-[#1E293B] mb-4">
                    Modifica i filtri per vedere più risultati
                  </p>
                  <Button
                    onClick={() => {
                      setSearchTerm('')
                      setSelectedCategory('all')
                      setSelectedUrgency('all')
                    }}
                    variant="outline"
                    className="text-[#2A5D67] border-[#2A5D67] hover:bg-[#F8F5F1]"
                  >
                    Resetta Filtri
                  </Button>
                </motion.div>
              )}
            </div>
          </div>
        </div>

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
              Stiamo perfezionando il sistema di monitoraggio degli aggiornamenti urgenti per offrirti la migliore esperienza possibile.
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