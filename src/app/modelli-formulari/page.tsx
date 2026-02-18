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
  FileText, 
  Clock, 
  Star,
  Grid3X3,
  List,
  ChevronDown,
  Bookmark,
  Share2,
  Printer,
  Calendar,
  Building,
  Scale,
  Receipt,
  UserCheck,
  AlertTriangle,
  CheckCircle,
  Brain
} from 'lucide-react'
import Link from 'next/link'

interface Document {
  id: string
  title: string
  category: string
  description: string
  lastUpdated: string
  downloads: number
  rating: number
  isFavorite: boolean
  tags: string[]
  fileSize: string
  pages: number
  difficulty: 'Principiante' | 'Intermedio' | 'Avanzato'
}

const categories = [
  { id: 'contratti', name: 'Contratti', icon: FileText, count: 45, color: '#2A5D67' },
  { id: 'fiscale', name: 'Fiscale', icon: Receipt, count: 67, color: '#D4A574' },
  { id: 'societario', name: 'Diritto Societario', icon: Building, count: 38, color: '#A9C1B7' },
  { id: 'lavoro', name: 'Diritto del Lavoro', icon: UserCheck, count: 52, color: '#C4BDB4' },
  { id: 'penale', name: 'Diritto Penale', icon: Scale, count: 28, color: '#1E293B' },
  { id: 'amministrativo', name: 'Amministrativo', icon: AlertTriangle, count: 15, color: '#D4A574' }
]

const mockDocuments: Document[] = [
  {
    id: '1',
    title: 'Contratto di Lavoro a Tempo Determinato',
    category: 'lavoro',
    description: 'Modello standard per contratti a tempo determinato conforme al D.Lgs. 81/2015',
    lastUpdated: '2024-01-15',
    downloads: 1247,
    rating: 4.8,
    isFavorite: true,
    tags: ['Contratto', 'Lavoro', 'Tempo Determinato', 'Jobs Act'],
    fileSize: '156 KB',
    pages: 8,
    difficulty: 'Intermedio'
  },
  {
    id: '2',
    title: 'F24 Unificato - Guida Compilazione',
    category: 'fiscale',
    description: 'Guida completa per la compilazione del modello F24 con esempi pratici',
    lastUpdated: '2024-01-10',
    downloads: 2156,
    rating: 4.9,
    isFavorite: false,
    tags: ['F24', 'Fiscale', 'Tributi', 'Agenzia Entrate'],
    fileSize: '892 KB',
    pages: 24,
    difficulty: 'Avanzato'
  },
  {
    id: '3',
    title: 'Atto Costitutivo SRL Semplificata',
    category: 'societario',
    description: 'Modello per costituzione di SRL semplificata con capitale minimo',
    lastUpdated: '2024-01-12',
    downloads: 789,
    rating: 4.6,
    isFavorite: true,
    tags: ['SRL', 'Costituzione', 'Societario', 'Startup'],
    fileSize: '234 KB',
    pages: 12,
    difficulty: 'Intermedio'
  },
  {
    id: '4',
    title: 'Contratto di Compravendita Immobiliare',
    category: 'contratti',
    description: 'Contratto standard per compravendita immobiliare con clausole essenziali',
    lastUpdated: '2024-01-08',
    downloads: 1567,
    rating: 4.7,
    isFavorite: false,
    tags: ['Immobiliare', 'Compravendita', 'Notarile', 'Casa'],
    fileSize: '445 KB',
    pages: 16,
    difficulty: 'Avanzato'
  },
  {
    id: '5',
    title: 'Ricorso Amministrativo - TAR',
    category: 'amministrativo',
    description: 'Modello di ricorso per Tribunale Amministrativo Regionale',
    lastUpdated: '2024-01-14',
    downloads: 445,
    rating: 4.5,
    isFavorite: false,
    tags: ['TAR', 'Ricorso', 'Amministrativo', 'PA'],
    fileSize: '678 KB',
    pages: 20,
    difficulty: 'Avanzato'
  },
  {
    id: '6',
    title: 'Istanza di Patteggiamento',
    category: 'penale',
    description: 'Modello per istanza di applicazione pena su richiesta delle parti',
    lastUpdated: '2024-01-11',
    downloads: 234,
    rating: 4.4,
    isFavorite: true,
    tags: ['Patteggiamento', 'Penale', 'Procedura', 'Tribunale'],
    fileSize: '189 KB',
    pages: 6,
    difficulty: 'Intermedio'
  }
]


export default function ModelliFormulariPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [sortBy, setSortBy] = useState<'recent' | 'popular' | 'rating'>('recent')
  const [showFilters, setShowFilters] = useState(false)

  const filteredDocuments = mockDocuments.filter(doc => {
    const matchesSearch = doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         doc.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         doc.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
    
    const matchesCategory = selectedCategory === 'all' || doc.category === selectedCategory
    
    return matchesSearch && matchesCategory
  })

  const sortedDocuments = [...filteredDocuments].sort((a, b) => {
    switch (sortBy) {
      case 'popular':
        return b.downloads - a.downloads
      case 'rating':
        return b.rating - a.rating
      case 'recent':
      default:
        return new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime()
    }
  })

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'Principiante': return 'text-green-600 bg-green-50'
      case 'Intermedio': return 'text-yellow-600 bg-yellow-50'
      case 'Avanzato': return 'text-red-600 bg-red-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const handleDownload = (document: Document) => {
    console.log('Downloading:', document.title)
    alert(`Download avviato: ${document.title}`)
  }

  const handlePreview = (document: Document) => {
    console.log('Previewing:', document.title)
    alert(`Anteprima: ${document.title}`)
  }

  const toggleFavorite = (documentId: string) => {
    console.log('Toggle favorite:', documentId)
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-[#C4BDB4]/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/chat">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="flex items-center space-x-2 text-[#2A5D67] hover:text-[#1E293B] transition-colors"
                >
                  <ArrowLeft className="w-5 h-5" />
                  <span className="font-medium">Torna alla Chat</span>
                </motion.button>
              </Link>
              
              <div className="h-6 w-px bg-[#C4BDB4]/30"></div>
              
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-[#2A5D67] rounded-lg flex items-center justify-center">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold text-[#2A5D67]">Modelli e Formulari</h1>
                  <p className="text-sm text-[#1E293B]">{filteredDocuments.length} documenti disponibili</p>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
                className="text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
              >
                {viewMode === 'grid' ? <List className="w-4 h-4" /> : <Grid3X3 className="w-4 h-4" />}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative">
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
              Stiamo perfezionando la biblioteca di modelli e formulari per offrirti la migliore esperienza possibile.
            </p>
            <p className="text-[#C4BDB4] text-sm">
              Intravedi un&apos;anteprima di quello che ti aspetta...
            </p>
            <motion.div 
              className="flex justify-center space-x-1 mt-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 bg-[#2A5D67] rounded-full"
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.2 }}
                />
              ))}
            </motion.div>
          </motion.div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar - Categories & Filters */}
          <div className="lg:col-span-1">
            <div className="space-y-6">
              {/* Search */}
              <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                <h3 className="font-semibold text-[#2A5D67] mb-4">Cerca Documenti</h3>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[#C4BDB4]" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Cerca per titolo, descrizione..."
                    className="w-full pl-10 pr-4 py-3 border border-[#C4BDB4]/20 rounded-lg focus:ring-2 focus:ring-[#2A5D67]/20 focus:border-[#2A5D67] transition-all"
                  />
                </div>
              </div>

              {/* Categories */}
              <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                <h3 className="font-semibold text-[#2A5D67] mb-4">Categorie</h3>
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
                      <span>Tutti i Documenti</span>
                      <span className="text-sm opacity-70">{mockDocuments.length}</span>
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

              {/* Sort Options */}
              <div className="bg-white rounded-xl p-6 shadow-sm border border-[#C4BDB4]/20">
                <h3 className="font-semibold text-[#2A5D67] mb-4">Ordina per</h3>
                <div className="space-y-2">
                  {[
                    { key: 'recent', label: 'Più Recenti' },
                    { key: 'popular', label: 'Più Scaricati' },
                    { key: 'rating', label: 'Valutazione' }
                  ].map((option) => (
                    <button
                      key={option.key}
                      onClick={() => setSortBy(option.key as 'recent' | 'popular' | 'rating')}
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
                  {selectedCategory === 'all' ? 'Tutti i Documenti' : 
                   categories.find(c => c.id === selectedCategory)?.name}
                </h2>
                <p className="text-[#1E293B] mt-1">
                  {sortedDocuments.length} risultat{sortedDocuments.length !== 1 ? 'i' : 'o'} trovat{sortedDocuments.length !== 1 ? 'i' : 'o'}
                </p>
              </div>
            </div>

            {/* Documents Grid/List */}
            <div className={`${
              viewMode === 'grid' 
                ? 'grid grid-cols-1 md:grid-cols-2 gap-6' 
                : 'space-y-4'
            }`}>
              {sortedDocuments.map((document, index) => (
                <motion.div
                  key={document.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`bg-white rounded-xl shadow-sm border border-[#C4BDB4]/20 hover:shadow-md transition-all ${
                    viewMode === 'list' ? 'p-4' : 'p-6'
                  }`}
                >
                  {viewMode === 'grid' ? (
                    <div className="space-y-4">
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-[#F8F5F1] rounded-lg flex items-center justify-center">
                            <FileText className="w-5 h-5 text-[#2A5D67]" />
                          </div>
                          <div className="flex-1">
                            <h3 className="font-semibold text-[#2A5D67] mb-1">{document.title}</h3>
                            <div className="flex items-center space-x-2">
                              <span className={`px-2 py-1 rounded-md text-xs font-medium ${getDifficultyColor(document.difficulty)}`}>
                                {document.difficulty}
                              </span>
                              <span className="text-xs text-[#C4BDB4]">{document.pages} pagine</span>
                            </div>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleFavorite(document.id)}
                          className="text-[#C4BDB4] hover:text-[#D4A574]"
                        >
                          <Star className={`w-4 h-4 ${document.isFavorite ? 'fill-current text-[#D4A574]' : ''}`} />
                        </Button>
                      </div>

                      {/* Description */}
                      <p className="text-[#1E293B] text-sm leading-relaxed">
                        {document.description}
                      </p>

                      {/* Tags */}
                      <div className="flex flex-wrap gap-2">
                        {document.tags.slice(0, 3).map((tag, tagIndex) => (
                          <span
                            key={tagIndex}
                            className="px-2 py-1 bg-[#F8F5F1] text-[#2A5D67] text-xs rounded-md"
                          >
                            {tag}
                          </span>
                        ))}
                        {document.tags.length > 3 && (
                          <span className="px-2 py-1 bg-[#F8F5F1] text-[#C4BDB4] text-xs rounded-md">
                            +{document.tags.length - 3} altri
                          </span>
                        )}
                      </div>

                      {/* Stats */}
                      <div className="flex items-center justify-between text-xs text-[#C4BDB4]">
                        <div className="flex items-center space-x-4">
                          <div className="flex items-center space-x-1">
                            <Download className="w-3 h-3" />
                            <span>{document.downloads.toLocaleString()}</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Star className="w-3 h-3 fill-current text-yellow-400" />
                            <span>{document.rating}</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>{new Date(document.lastUpdated).toLocaleDateString('it-IT')}</span>
                          </div>
                        </div>
                        <span>{document.fileSize}</span>
                      </div>

                      {/* Actions */}
                      <div className="flex space-x-2">
                        <Button
                          onClick={() => handlePreview(document)}
                          variant="outline"
                          size="sm"
                          className="flex-1 text-[#2A5D67] border-[#2A5D67]/20 hover:bg-[#F8F5F1]"
                        >
                          <Eye className="w-4 h-4 mr-2" />
                          Anteprima
                        </Button>
                        <Button
                          onClick={() => handleDownload(document)}
                          size="sm"
                          className="flex-1 bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                        >
                          <Download className="w-4 h-4 mr-2" />
                          Scarica
                        </Button>
                      </div>
                    </div>
                  ) : (
                    /* List View */
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-[#F8F5F1] rounded-lg flex items-center justify-center flex-shrink-0">
                        <FileText className="w-6 h-6 text-[#2A5D67]" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="font-semibold text-[#2A5D67] mb-1">{document.title}</h3>
                            <p className="text-[#1E293B] text-sm mb-2">{document.description}</p>
                            <div className="flex items-center space-x-4 text-xs text-[#C4BDB4]">
                              <span>{document.downloads.toLocaleString()} download</span>
                              <span>★ {document.rating}</span>
                              <span>{document.fileSize}</span>
                              <span>{new Date(document.lastUpdated).toLocaleDateString('it-IT')}</span>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Button
                              onClick={() => handlePreview(document)}
                              variant="ghost"
                              size="sm"
                              className="text-[#2A5D67] hover:bg-[#F8F5F1]"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button
                              onClick={() => handleDownload(document)}
                              size="sm"
                              className="bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                            >
                              <Download className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>

            {/* Empty State */}
            {sortedDocuments.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-12"
              >
                <div className="w-16 h-16 bg-[#F8F5F1] rounded-full flex items-center justify-center mx-auto mb-4">
                  <FileText className="w-8 h-8 text-[#C4BDB4]" />
                </div>
                <h3 className="text-xl font-semibold text-[#2A5D67] mb-2">
                  Nessun documento trovato
                </h3>
                <p className="text-[#1E293B] mb-4">
                  Prova a modificare i filtri di ricerca o esplorare altre categorie
                </p>
                <Button
                  onClick={() => {
                    setSearchTerm('')
                    setSelectedCategory('all')
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
    </div>
  )
}