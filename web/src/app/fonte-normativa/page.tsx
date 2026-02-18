'use client'

import React, { useState } from 'react'
import { motion } from 'motion/react'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { ArrowLeft, BookOpen, ExternalLink, Search, Filter, Star } from 'lucide-react'
import { Input } from '../../components/ui/input'
import Link from 'next/link'

interface RegulatorySource {
  id: string
  name: string
  type: 'normativa' | 'prassi' | 'giurisprudenza' | 'dottrina'
  description: string
  url: string
  lastUpdated: string
  documentsCount: number
  reliability: number
  featured: boolean
}

const regulatorySources: RegulatorySource[] = [
  {
    id: '1',
    name: 'Gazzetta Ufficiale della Repubblica Italiana',
    type: 'normativa',
    description: 'Pubblicazione ufficiale delle leggi, decreti e regolamenti dello Stato italiano',
    url: 'https://www.gazzettaufficiale.it',
    lastUpdated: '2024-02-16',
    documentsCount: 12450,
    reliability: 5,
    featured: true
  },
  {
    id: '2',
    name: 'Agenzia delle Entrate - Circolari e Risoluzioni',
    type: 'prassi',
    description: 'Interpretazioni ufficiali delle norme tributarie attraverso circolari e risoluzioni',
    url: 'https://www.agenziaentrate.gov.it',
    lastUpdated: '2024-02-15',
    documentsCount: 8900,
    reliability: 5,
    featured: true
  },
  {
    id: '3',
    name: 'Corte di Cassazione - Sezioni Unite',
    type: 'giurisprudenza',
    description: 'Sentenze della Suprema Corte di Cassazione in materia fiscale e tributaria',
    url: 'https://www.cortedicassazione.it',
    lastUpdated: '2024-02-14',
    documentsCount: 5670,
    reliability: 5,
    featured: true
  },
  {
    id: '4',
    name: 'Commissioni Tributarie Regionali',
    type: 'giurisprudenza',
    description: 'Sentenze delle Commissioni Tributarie Regionali su controversie fiscali',
    url: 'https://www.giustizia-tributaria.it',
    lastUpdated: '2024-02-13',
    documentsCount: 15600,
    reliability: 4,
    featured: false
  },
  {
    id: '5',
    name: 'Il Sole 24 ORE - Norme e Tributi',
    type: 'dottrina',
    description: 'Analisi dottrinali e commenti alle normative fiscali e tributarie',
    url: 'https://www.ilsole24ore.com',
    lastUpdated: '2024-02-16',
    documentsCount: 25800,
    reliability: 4,
    featured: false
  },
  {
    id: '6',
    name: 'Consiglio di Stato - Sezione Quinta',
    type: 'giurisprudenza',
    description: 'Sentenze del Consiglio di Stato in materia di contenzioso tributario',
    url: 'https://www.giustizia-amministrativa.it',
    lastUpdated: '2024-02-12',
    documentsCount: 3400,
    reliability: 5,
    featured: false
  },
  {
    id: '7',
    name: 'Rivista di Diritto Tributario',
    type: 'dottrina',
    description: 'Pubblicazione scientifica specializzata in diritto tributario italiano ed europeo',
    url: 'https://www.rivistadidirituttributario.it',
    lastUpdated: '2024-02-10',
    documentsCount: 1200,
    reliability: 4,
    featured: false
  },
  {
    id: '8',
    name: 'Corte di Giustizia UE - Materia Fiscale',
    type: 'giurisprudenza',
    description: 'Sentenze della Corte di Giustizia dell\'Unione Europea in ambito fiscale',
    url: 'https://curia.europa.eu',
    lastUpdated: '2024-02-09',
    documentsCount: 890,
    reliability: 5,
    featured: false
  }
]

const typeColors = {
  normativa: 'bg-[#D4A574]',
  prassi: 'bg-[#2A5D67]',
  giurisprudenza: 'bg-purple-500',
  dottrina: 'bg-green-500'
}

export default function FonteNormativaPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [showFeaturedOnly, setShowFeaturedOnly] = useState(false)
  
  const filteredSources = regulatorySources.filter(source => {
    const matchesSearch = source.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         source.description.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesType = selectedType === 'all' || source.type === selectedType
    const matchesFeatured = !showFeaturedOnly || source.featured
    
    return matchesSearch && matchesType && matchesFeatured
  })

  const types = [
    { value: 'all', label: 'Tutte le fonti', count: regulatorySources.length },
    { value: 'normativa', label: 'Normativa', count: regulatorySources.filter(s => s.type === 'normativa').length },
    { value: 'prassi', label: 'Prassi', count: regulatorySources.filter(s => s.type === 'prassi').length },
    { value: 'giurisprudenza', label: 'Giurisprudenza', count: regulatorySources.filter(s => s.type === 'giurisprudenza').length },
    { value: 'dottrina', label: 'Dottrina', count: regulatorySources.filter(s => s.type === 'dottrina').length }
  ]

  const renderStars = (reliability: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <Star
        key={i}
        className={`w-4 h-4 ${i < reliability ? 'text-yellow-500 fill-current' : 'text-gray-300'}`}
      />
    ))
  }

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      {/* Header */}
      <div className="bg-white border-b border-[#C4BDB4]/20 p-4">
        <div className="max-w-6xl mx-auto">
          <Link href="/chat" className="inline-flex items-center space-x-2 mb-4">
            <Button variant="ghost" size="sm" className="text-[#2A5D67]">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Torna alla Chat
            </Button>
          </Link>
          
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-[#2A5D67] rounded-xl flex items-center justify-center">
              <BookOpen className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-[#2A5D67]">Fonte Normativa</h1>
              <p className="text-[#1E293B] mt-1">Accedi alle principali fonti normative e dottrinali</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto p-6">
        {/* Stats Cards */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="bg-white border-[#C4BDB4]/20">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-[#2A5D67]">{regulatorySources.length}</p>
                    <p className="text-sm text-[#1E293B]">Fonti disponibili</p>
                  </div>
                  <BookOpen className="w-8 h-8 text-[#2A5D67]" />
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
          >
            <Card className="bg-white border-[#C4BDB4]/20">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-[#D4A574]">
                      {regulatorySources.reduce((sum, source) => sum + source.documentsCount, 0).toLocaleString()}
                    </p>
                    <p className="text-sm text-[#1E293B]">Documenti totali</p>
                  </div>
                  <div className="w-8 h-8 bg-[#D4A574]/10 rounded-lg flex items-center justify-center">
                    <div className="w-4 h-4 bg-[#D4A574] rounded"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
          >
            <Card className="bg-white border-[#C4BDB4]/20">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-yellow-500">
                      {regulatorySources.filter(s => s.featured).length}
                    </p>
                    <p className="text-sm text-[#1E293B]">Fonti principali</p>
                  </div>
                  <Star className="w-8 h-8 text-yellow-500 fill-current" />
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.3 }}
          >
            <Card className="bg-white border-[#C4BDB4]/20">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-green-500">
                      {types.length - 1}
                    </p>
                    <p className="text-sm text-[#1E293B]">Tipologie</p>
                  </div>
                  <Filter className="w-8 h-8 text-green-500" />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Search and Filters */}
        <div className="mb-8 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#C4BDB4] w-4 h-4" />
            <Input
              placeholder="Cerca per nome fonte o descrizione..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 border-[#C4BDB4] focus:border-[#2A5D67]"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {types.map((type) => (
              <Button
                key={type.value}
                variant={selectedType === type.value ? 'default' : 'outline'}
                onClick={() => setSelectedType(type.value)}
                className={selectedType === type.value 
                  ? 'bg-[#2A5D67] hover:bg-[#1E293B]' 
                  : 'border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white'
                }
                size="sm"
              >
                {type.label} ({type.count})
              </Button>
            ))}
            
            <Button
              variant={showFeaturedOnly ? 'default' : 'outline'}
              onClick={() => setShowFeaturedOnly(!showFeaturedOnly)}
              className={showFeaturedOnly 
                ? 'bg-yellow-500 hover:bg-yellow-600 text-white' 
                : 'border-yellow-500 text-yellow-500 hover:bg-yellow-500 hover:text-white'
              }
              size="sm"
            >
              <Star className="w-3 h-3 mr-1" />
              Solo principali
            </Button>
          </div>
        </div>

        {/* Sources Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {filteredSources.map((source, index) => (
            <motion.div
              key={source.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <Card className="bg-white border-[#C4BDB4]/20 hover:shadow-lg transition-shadow h-full">
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium text-white ${typeColors[source.type]}`}>
                        {source.type.toUpperCase()}
                      </span>
                      {source.featured && (
                        <div className="flex items-center space-x-1">
                          <Star className="w-3 h-3 text-yellow-500 fill-current" />
                          <span className="text-xs text-yellow-600">PRINCIPALE</span>
                        </div>
                      )}
                    </div>
                  </div>
                  <CardTitle className="text-lg text-[#2A5D67] leading-tight">
                    {source.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col">
                  <p className="text-[#1E293B] text-sm leading-relaxed mb-4 flex-1">
                    {source.description}
                  </p>
                  
                  <div className="space-y-3">
                    {/* Source Stats */}
                    <div className="flex justify-between items-center text-xs text-[#C4BDB4]">
                      <span>
                        {source.documentsCount.toLocaleString()} documenti
                      </span>
                      <span>
                        Aggiornato: {new Date(source.lastUpdated).toLocaleDateString('it-IT')}
                      </span>
                    </div>

                    {/* Reliability Rating */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-1">
                        <span className="text-xs text-[#1E293B]">Affidabilità:</span>
                        <div className="flex space-x-1">
                          {renderStars(source.reliability)}
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex space-x-2 pt-2">
                      <Button 
                        size="sm" 
                        className="flex-1 bg-[#2A5D67] hover:bg-[#1E293B] text-white"
                        asChild
                      >
                        <a href={source.url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="w-3 h-3 mr-1" />
                          Visita fonte
                        </a>
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="border-[#D4A574] text-[#D4A574] hover:bg-[#D4A574] hover:text-white"
                      >
                        Dettagli
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {filteredSources.length === 0 && (
          <div className="text-center py-12">
            <BookOpen className="w-16 h-16 text-[#C4BDB4] mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-[#2A5D67] mb-2">Nessuna fonte trovata</h3>
            <p className="text-[#1E293B]">Prova a modificare i termini di ricerca o i filtri selezionati</p>
          </div>
        )}

        {/* API Integration Info */}
        <div className="mt-12 p-6 bg-white rounded-xl border border-[#C4BDB4]/20">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-[#2A5D67] mb-2">Integrazione API</h3>
            <p className="text-[#1E293B] mb-4">
              PratikoAI si connette automaticamente a queste fonti per fornirti informazioni sempre aggiornate
            </p>
            <div className="flex justify-center space-x-4">
              <Button variant="outline" className="border-[#2A5D67] text-[#2A5D67] hover:bg-[#2A5D67] hover:text-white">
                Configura fonti preferite
              </Button>
              <Button className="bg-[#D4A574] hover:bg-[#C4A574] text-white">
                Scopri di più
              </Button>
            </div>
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
              <BookOpen className="w-8 h-8 text-white" />
            </motion.div>
          </motion.div>
          
          <h3 className="text-2xl font-semibold text-[#2A5D67] mb-4">
            Funzionalità in Sviluppo
          </h3>
          
          <p className="text-[#1E293B] text-lg leading-relaxed mb-2">
            Stiamo perfezionando l&apos;accesso alle fonti normative per offrirti la migliore esperienza possibile.
          </p>
          <p className="text-[#C4BDB4] text-sm">
            Intravedi un&apos;anteprima di quello che ti aspetta...
          </p>
        </motion.div>
      </div>
    </div>
  )
}