'use client'

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Button } from '../../components/ui/button'
import { 
  ArrowLeft, 
  Search, 
  Filter, 
  Download, 
  Eye,
  ExternalLink,
  Calendar,
  Building,
  Scale,
  BookOpen,
  Star,
  Clock,
  Tag,
  FileText,
  AlertCircle,
  TrendingUp,
  Globe,
  Archive,
  Bookmark,
  Brain
} from 'lucide-react'
import Link from 'next/link'

interface Normativa {
  id: string
  title: string
  description: string
  authority: string
  type: 'decreto' | 'legge' | 'circolare' | 'provvedimento' | 'regolamento'
  category: 'fiscale' | 'civile' | 'penale' | 'amministrativo' | 'societario' | 'lavoro'
  date: string
  effectiveDate?: string
  impact: 'alto' | 'medio' | 'basso'
  tags: string[]
  summary: string
  url: string
  isBookmarked: boolean
  views: number
  isNew: boolean
}

export default function NormativeRecentiPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [selectedAuthority, setSelectedAuthority] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'date' | 'impact' | 'views'>('date')

  const categories = [
    { id: 'fiscale', name: 'Fiscale', icon: Building, count: 12 },
    { id: 'civile', name: 'Civile', icon: Scale, count: 8 },
    { id: 'penale', name: 'Penale', icon: AlertCircle, count: 5 },
    { id: 'amministrativo', name: 'Amministrativo', icon: FileText, count: 7 },
    { id: 'societario', name: 'Societario', icon: Building, count: 9 },
    { id: 'lavoro', name: 'Lavoro', icon: Clock, count: 6 }
  ]

  const authorities = [
    { id: 'governo', name: 'Governo', count: 15 },
    { id: 'parlamento', name: 'Parlamento', count: 8 },
    { id: 'ministeri', name: 'Ministeri', count: 12 },
    { id: 'agenzia-entrate', name: 'Agenzia delle Entrate', count: 10 },
    { id: 'corte-costituzionale', name: 'Corte Costituzionale', count: 3 },
    { id: 'cassazione', name: 'Cassazione', count: 7 }
  ]

  const mockNormative: Normativa[] = [
    {
      id: '1',
      title: 'Decreto Crescita 2025 - Misure per lo sviluppo economico',
      description: 'Nuove agevolazioni fiscali per startup innovative e PMI, incentivi per investimenti in ricerca e sviluppo.',
      authority: 'Governo',
      type: 'decreto',
      category: 'fiscale',
      date: '2025-01-15',
      effectiveDate: '2025-02-01',
      impact: 'alto',
      tags: ['Agevolazioni Fiscali', 'Startup', 'PMI', 'R&D'],
      summary: 'Il decreto introduce significative misure di sostegno per l\'economia italiana, con particolare focus su innovazione e digitalizzazione.',
      url: '#',
      isBookmarked: false,
      views: 1247,
      isNew: true
    },
    {
      id: '2',
      title: 'Circolare AdE n. 2/2025 - Nuove modalità di versamento IVA',
      description: 'Chiarimenti sulle nuove procedure telematiche per il versamento dell\'IVA e modifiche al modello F24.',
      authority: 'Agenzia delle Entrate',
      type: 'circolare',
      category: 'fiscale',
      date: '2025-01-10',
      effectiveDate: '2025-03-01',
      impact: 'alto',
      tags: ['IVA', 'F24', 'Procedure Telematiche'],
      summary: 'Importanti modifiche alle procedure di versamento IVA che interessano tutti i contribuenti soggetti al tributo.',
      url: '#',
      isBookmarked: true,
      views: 892,
      isNew: true
    },
    {
      id: '3',
      title: 'Legge n. 12/2025 - Riforma del processo civile telematico',
      description: 'Nuove disposizioni per la digitalizzazione completa del processo civile e l\'introduzione dell\'udienza da remoto.',
      authority: 'Parlamento',
      type: 'legge',
      category: 'civile',
      date: '2025-01-08',
      effectiveDate: '2025-04-01',
      impact: 'alto',
      tags: ['Processo Civile', 'Digitalizzazione', 'Udienza Remota'],
      summary: 'Rivoluzionarie modifiche al processo civile che introducono strumenti digitali avanzati per maggiore efficienza.',
      url: '#',
      isBookmarked: false,
      views: 1156,
      isNew: true
    },
    {
      id: '4',
      title: 'DM 15 gennaio 2025 - Nuovi parametri contabilità semplificata',
      description: 'Aggiornamento dei coefficenti di redditività per i contribuenti in regime di contabilità semplificata.',
      authority: 'Ministero dell\'Economia',
      type: 'provvedimento',
      category: 'fiscale',
      date: '2025-01-05',
      effectiveDate: '2025-01-01',
      impact: 'medio',
      tags: ['Contabilità Semplificata', 'Coefficienti Redditività'],
      summary: 'Importanti aggiornamenti per i professionisti e le piccole imprese in regime semplificato.',
      url: '#',
      isBookmarked: false,
      views: 634,
      isNew: false
    },
    {
      id: '5',
      title: 'Sentenza Cassazione SS.UU. n. 1024/2025',
      description: 'Principio di diritto sulla responsabilità dell\'amministratore di fatto nelle società di capitali.',
      authority: 'Cassazione',
      type: 'provvedimento',
      category: 'societario',
      date: '2024-12-28',
      impact: 'alto',
      tags: ['Amministratore di Fatto', 'Responsabilità', 'Società'],
      summary: 'Importante precedente giurisprudenziale che chiarisce i confini della responsabilità degli amministratori.',
      url: '#',
      isBookmarked: true,
      views: 789,
      isNew: false
    },
    {
      id: '6',
      title: 'Circolare INPS n. 8/2025 - Novità sui congedi parentali',
      description: 'Nuove modalità di fruizione dei congedi parentali e aggiornamenti sui relativi contributi figurativi.',
      authority: 'INPS',
      type: 'circolare',
      category: 'lavoro',
      date: '2024-12-22',
      effectiveDate: '2025-01-01',
      impact: 'medio',
      tags: ['Congedi Parentali', 'Contributi Figurativi', 'Famiglia'],
      summary: 'Significative novità per la conciliazione vita-lavoro e la tutela della genitorialità.',
      url: '#',
      isBookmarked: false,
      views: 445,
      isNew: false
    }
  ]

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'alto': return 'bg-red-100 text-red-700 border-red-200'
      case 'medio': return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      case 'basso': return 'bg-green-100 text-green-700 border-green-200'
      default: return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'decreto': return 'bg-purple-100 text-purple-700'
      case 'legge': return 'bg-blue-100 text-blue-700'
      case 'circolare': return 'bg-green-100 text-green-700'
      case 'provvedimento': return 'bg-orange-100 text-orange-700'
      case 'regolamento': return 'bg-indigo-100 text-indigo-700'
      default: return 'bg-gray-100 text-gray-700'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('it-IT', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const filteredNormative = mockNormative.filter(normativa => {
    const matchesCategory = selectedCategory === 'all' || normativa.category === selectedCategory
    const matchesAuthority = selectedAuthority === 'all' || 
      normativa.authority.toLowerCase().includes(selectedAuthority.replace('-', ' '))
    const matchesSearch = normativa.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         normativa.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         normativa.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
    return matchesCategory && matchesAuthority && matchesSearch
  })

  const sortedNormative = [...filteredNormative].sort((a, b) => {
    switch (sortBy) {
      case 'date':
        return new Date(b.date).getTime() - new Date(a.date).getTime()
      case 'impact':
        const impactOrder = { 'alto': 3, 'medio': 2, 'basso': 1 }
        return impactOrder[b.impact] - impactOrder[a.impact]
      case 'views':
        return b.views - a.views
      default:
        return 0
    }
  })

  const toggleBookmark = (id: string) => {
    console.log('Toggle bookmark for:', id)
  }

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
                  <h1 className="text-2xl font-bold text-[#2A5D67]">Normative Recenti</h1>
                  <p className="text-[#1E293B] text-sm">Resta aggiornato sulle ultime pubblicazioni normative</p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Esporta
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                >
                  <Archive className="w-4 h-4 mr-2" />
                  Archivio
                </Button>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Sidebar */}
            <div className="lg:col-span-1">
              <div className="space-y-6">
                {/* Search */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">Cerca Normative</h3>
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

                {/* Categories */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">Aree Legali</h3>
                  <div className="space-y-2">
                    <button
                      onClick={() => setSelectedCategory('all')}
                      className={`w-full text-left p-3 rounded-lg transition-all ${
                        selectedCategory === 'all' 
                          ? 'bg-[#2A5D67] text-white' 
                          : 'hover:bg-[#F8F5F1] text-[#1E293B]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>Tutte le Aree</span>
                        <span className="text-sm opacity-70">{mockNormative.length}</span>
                      </div>
                    </button>
                    
                    {categories.map((category) => (
                      <motion.button
                        key={category.id}
                        onClick={() => setSelectedCategory(category.id)}
                        whileHover={{ scale: 1.02 }}
                        className={`w-full text-left p-3 rounded-lg transition-all ${
                          selectedCategory === category.id 
                            ? 'bg-[#2A5D67] text-white' 
                            : 'hover:bg-[#F8F5F1] text-[#1E293B]'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <category.icon className="w-4 h-4" />
                            <span className="text-sm">{category.name}</span>
                          </div>
                          <span className="text-xs opacity-70">{category.count}</span>
                        </div>
                      </motion.button>
                    ))}
                  </div>
                </div>

                {/* Authorities */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                  <h3 className="font-semibold text-[#2A5D67] mb-4">Autorità</h3>
                  <div className="space-y-2">
                    <button
                      onClick={() => setSelectedAuthority('all')}
                      className={`w-full text-left p-2 rounded-lg transition-all ${
                        selectedAuthority === 'all' 
                          ? 'bg-[#F8F5F1] text-[#2A5D67] font-medium' 
                          : 'text-[#1E293B] hover:bg-[#F8F5F1]'
                      }`}
                    >
                      Tutte le Autorità
                    </button>
                    
                    {authorities.map((authority) => (
                      <button
                        key={authority.id}
                        onClick={() => setSelectedAuthority(authority.id)}
                        className={`w-full text-left p-2 rounded-lg transition-all ${
                          selectedAuthority === authority.id 
                            ? 'bg-[#F8F5F1] text-[#2A5D67] font-medium' 
                            : 'text-[#1E293B] hover:bg-[#F8F5F1]'
                        }`}
                      >
                        <div className="flex justify-between">
                          <span className="text-sm">{authority.name}</span>
                          <span className="text-xs text-[#C4BDB4]">{authority.count}</span>
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
                      { key: 'date', label: 'Data Pubblicazione' },
                      { key: 'impact', label: 'Impatto' },
                      { key: 'views', label: 'Più Lette' }
                    ].map((option) => (
                      <button
                        key={option.key}
                        onClick={() => setSortBy(option.key as 'date' | 'impact' | 'views')}
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
                    {selectedCategory === 'all' ? 'Tutte le Normative' : 
                     categories.find(c => c.id === selectedCategory)?.name}
                  </h2>
                  <p className="text-[#1E293B] mt-1">
                    {sortedNormative.length} normativ{sortedNormative.length !== 1 ? 'e' : 'a'} trovat{sortedNormative.length !== 1 ? 'e' : 'a'}
                  </p>
                </div>
              </div>

              {/* Normative List */}
              <div className="space-y-6">
                {sortedNormative.map((normativa, index) => (
                  <motion.div
                    key={normativa.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="bg-white rounded-xl shadow-sm border border-[#C4BDB4]/20 hover:shadow-md transition-all"
                  >
                    <div className="p-6">
                      {/* Header */}
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            {normativa.isNew && (
                              <span className="px-2 py-1 bg-[#D4A574] text-white text-xs font-medium rounded-full">
                                Nuovo
                              </span>
                            )}
                            <span className={`px-2 py-1 text-xs font-medium rounded-md ${getTypeColor(normativa.type)}`}>
                              {normativa.type.charAt(0).toUpperCase() + normativa.type.slice(1)}
                            </span>
                            <span className={`px-2 py-1 text-xs font-medium rounded-md border ${getImpactColor(normativa.impact)}`}>
                              Impatto {normativa.impact}
                            </span>
                          </div>
                          <h3 className="text-lg font-semibold text-[#2A5D67] mb-2">
                            {normativa.title}
                          </h3>
                          <p className="text-[#1E293B] mb-3">
                            {normativa.description}
                          </p>
                          <p className="text-[#1E293B] text-sm leading-relaxed mb-4">
                            {normativa.summary}
                          </p>
                        </div>
                        <Button
                          onClick={() => toggleBookmark(normativa.id)}
                          variant="ghost"
                          size="sm"
                          className={`ml-4 ${
                            normativa.isBookmarked 
                              ? 'text-[#D4A574] hover:text-[#D4A574]/80' 
                              : 'text-[#C4BDB4] hover:text-[#D4A574]'
                          }`}
                        >
                          <Bookmark className={`w-4 h-4 ${normativa.isBookmarked ? 'fill-current' : ''}`} />
                        </Button>
                      </div>

                      {/* Meta Info */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-sm">
                        <div className="flex items-center space-x-2">
                          <Building className="w-4 h-4 text-[#C4BDB4]" />
                          <span className="text-[#1E293B]">{normativa.authority}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Calendar className="w-4 h-4 text-[#C4BDB4]" />
                          <span className="text-[#1E293B]">
                            {formatDate(normativa.date)}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Eye className="w-4 h-4 text-[#C4BDB4]" />
                          <span className="text-[#1E293B]">
                            {normativa.views.toLocaleString()} visualizzazioni
                          </span>
                        </div>
                      </div>

                      {/* Tags */}
                      <div className="flex flex-wrap gap-2 mb-4">
                        {normativa.tags.map((tag, tagIndex) => (
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
                          {normativa.effectiveDate && (
                            <div className="flex items-center space-x-1 text-xs text-[#C4BDB4]">
                              <Clock className="w-3 h-3" />
                              <span>Efficace dal {formatDate(normativa.effectiveDate)}</span>
                            </div>
                          )}
                        </div>
                        <div className="flex space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                          >
                            <Eye className="w-4 h-4 mr-2" />
                            Leggi
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                          >
                            <ExternalLink className="w-4 h-4 mr-2" />
                            Fonte Ufficiale
                          </Button>
                          <Button
                            size="sm"
                            className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                          >
                            <Download className="w-4 h-4 mr-2" />
                            Scarica PDF
                          </Button>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Empty State */}
              {sortedNormative.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-12 bg-white rounded-xl border border-[#C4BDB4]/20"
                >
                  <BookOpen className="w-16 h-16 text-[#C4BDB4] mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-[#2A5D67] mb-2">
                    Nessuna normativa trovata
                  </h3>
                  <p className="text-[#1E293B] mb-4">
                    Prova a modificare i filtri di ricerca per vedere più risultati
                  </p>
                  <Button
                    onClick={() => {
                      setSearchTerm('')
                      setSelectedCategory('all')
                      setSelectedAuthority('all')
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
              Stiamo perfezionando il sistema di monitoraggio normativo per offrirti la migliore esperienza possibile.
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