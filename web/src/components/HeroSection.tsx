'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'motion/react'
import { Button } from './ui/button'
import { ArrowRight, CheckCircle, Building2, FileText, Brain, Clock } from 'lucide-react'

export function HeroSection() {
  const [isVisible, setIsVisible] = useState(false)
  const trustBadges = [
    "500+ Professionisti",
    "GDPR Compliant", 
    "Aggiornamenti ogni 4 ore"
  ]

  useEffect(() => {
    setIsVisible(true)
  }, [])

  // Animated elements for the illustration
  const AnimatedDocument = ({ delay = 0, path }: { delay?: number; path: { x: number; y: number } }) => (
    <motion.div
      initial={{ x: 0, y: 0, opacity: 0 }}
      animate={{ 
        x: path.x,
        y: path.y,
        opacity: [0, 1, 0.8, 0]
      }}
      transition={{
        duration: 3,
        delay,
        repeat: Infinity,
        repeatDelay: 2
      }}
      className="absolute w-6 h-6"
      style={{
        filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))'
      }}
    >
      <FileText className="w-6 h-6 text-[#D4A574]" />
    </motion.div>
  )

  const documentPaths = [
    { x: 150, y: -80, delay: 0 },
    { x: 200, y: -60, delay: 0.5 },
    { x: 180, y: -100, delay: 1 }
  ]

  return (
    <section className="relative min-h-screen bg-[#F8F5F1] pt-20 overflow-hidden">
      {/* Background Animation Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          animate={{ 
            backgroundPosition: ['0% 0%', '100% 100%']
          }}
          transition={{ 
            duration: 20,
            repeat: Infinity,
            repeatType: 'reverse'
          }}
          className="absolute inset-0 opacity-5 bg-gradient-to-br from-[#A9C1B7] to-[#2A5D67]"
          style={{
            backgroundSize: '400% 400%'
          }}
        />
        
        {/* Floating particles */}
        {Array.from({ length: 20 }).map((_, i) => {
          // Create deterministic values based on index to avoid hydration mismatch
          const initialX = (i * 123 + 456) % 800
          const targetX = (i * 789 + 234) % 800
          const duration = 10 + (i * 3) % 15
          const delay = (i * 2) % 20
          
          return (
            <motion.div
              key={i}
              className="absolute w-2 h-2 bg-[#A9C1B7]/20 rounded-full"
              initial={{
                x: initialX,
                y: 620
              }}
              animate={{
                y: -20,
                x: targetX
              }}
              transition={{
                duration,
                repeat: Infinity,
                delay
              }}
            />
          )
        })}
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-20">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12 items-center">
          {/* Left Content - 60% */}
          <div className="lg:col-span-2 space-y-8">
            {/* Main Headline - FIXED COLORS */}
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={isVisible ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="space-y-4"
            >
              <motion.h1
                className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight"
                initial={{ opacity: 0 }}
                animate={isVisible ? { opacity: 1 } : {}}
                transition={{ duration: 1.2, delay: 0.3 }}
              >
                <motion.span
                  className="text-[#2A5D67]"
                  initial={{ letterSpacing: '0.2em', opacity: 0 }}
                  animate={{ letterSpacing: '0em', opacity: 1 }}
                  transition={{ duration: 0.8, delay: 0.5 }}
                >
                  Risparmia
                </motion.span>{' '}
                {/* CRITICAL FIX: Changed from Sabbia Calda to Blu Petrolio BOLD */}
                <motion.span
                  className="text-[#2A5D67] font-black relative"
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.7 }}
                >
                  10 Ore
                  {/* Optional: Add background pill effect */}
                  <motion.div
                    className="absolute inset-0 bg-[#D4A574]/20 rounded-lg -z-10"
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.4, delay: 0.9 }}
                  />
                </motion.span>{' '}
                <motion.span
                  className="text-[#2A5D67]"
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.9 }}
                >
                  a Settimana
                </motion.span>
                <br />
                <motion.span
                  className="text-[#2A5D67]"
                  initial={{ x: -20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 1.1 }}
                >
                  con l&apos;AI per professionisti della
                </motion.span>{' '}
                <motion.span
                  className="relative text-[#2A5D67]"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.6, delay: 1.3 }}
                >
                  consulenza economica, fiscale,
                  <br />
                  legale e del lavoro
                  <motion.div
                    className="absolute -bottom-2 left-0 h-1 bg-gradient-to-r from-[#2A5D67] to-[#D4A574] origin-left"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 1, delay: 1.5 }}
                  />
                </motion.span>
              </motion.h1>
            </motion.div>

            {/* Subheadline */}
            <motion.p
              initial={{ opacity: 0, y: 30 }}
              animate={isVisible ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.8, delay: 0.6 }}
              className="text-xl text-[#1E293B] max-w-2xl leading-relaxed"
            >
              PratikoAI monitora automaticamente{' '}
              <span className="font-semibold text-[#2A5D67]">Agenzia Entrate, INPS, MEF, Gazzetta Ufficiale e molte altre fonti</span>{' '}
              per darti risposte sempre aggiornate.
            </motion.p>

            {/* Trust Badges - FIXED COLORS */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={isVisible ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.8 }}
              className="flex flex-wrap gap-6"
            >
              {trustBadges.map((badge) => (
                <motion.div
                  key={badge}
                  className="flex items-center space-x-2 bg-white px-4 py-2 rounded-lg shadow-sm border border-[#C4BDB4]/20"
                  whileHover={{ scale: 1.05, y: -2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <CheckCircle className="w-4 h-4 text-[#2A5D67]" />
                  <span className="text-[#2A5D67] font-medium">{badge}</span>
                </motion.div>
              ))}
            </motion.div>

            {/* CTA Section */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={isVisible ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.8, delay: 1.0 }}
              className="space-y-4"
            >
              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Button
                  size="lg"
                  className="bg-[#2A5D67] hover:bg-[#1E293B] text-lg px-8 py-4 h-auto rounded-xl shadow-xl hover:shadow-2xl transition-all duration-300 group relative overflow-hidden"
                >
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-[#A9C1B7]/20 to-transparent"
                    initial={{ x: '-100%' }}
                    whileHover={{ x: '100%' }}
                    transition={{ duration: 0.5 }}
                  />
                  <span className="relative flex items-center space-x-2 text-[#D4A574] font-bold">
                    <Clock className="w-5 h-5" />
                    <span>Inizia Prova Gratuita di 7 Giorni</span>
                    <motion.div
                      animate={{ x: [0, 5, 0] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      <ArrowRight className="w-5 h-5" />
                    </motion.div>
                  </span>
                </Button>
              </motion.div>
              
              <div className="flex items-center space-x-4 text-[#2A5D67]">
                <div className="flex items-center space-x-1">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm">Nessuna carta di credito</span>
                </div>
                <div className="flex items-center space-x-1">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm">Setup in 2 minuti</span>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right Illustration - 40% - FIXED COLORS */}
          <div className="lg:col-span-1 relative">
            <motion.div
              initial={{ opacity: 0, scale: 0.8, x: 50 }}
              animate={isVisible ? { opacity: 1, scale: 1, x: 0 } : {}}
              transition={{ duration: 1, delay: 0.8 }}
              className="relative w-full h-96 flex items-center justify-center"
            >
              {/* Government Buildings - Kept in Blu Petrolio */}
              <div className="absolute left-8 top-12">
                <motion.div
                  className="animate-float"
                  style={{ animationDelay: '0s' }}
                >
                  <div className="bg-[#2A5D67] w-16 h-20 rounded-lg relative shadow-lg">
                    <Building2 className="w-8 h-8 text-white absolute top-2 left-1/2 transform -translate-x-1/2" />
                    <div className="absolute bottom-2 left-1 right-1 h-1 bg-[#D4A574] rounded"></div>
                  </div>
                </motion.div>
              </div>

              <div className="absolute left-2 top-32">
                <motion.div
                  className="animate-float"
                  style={{ animationDelay: '0.5s' }}
                >
                  <div className="bg-[#2A5D67] w-12 h-16 rounded-lg relative shadow-lg">
                    <FileText className="w-6 h-6 text-white absolute top-2 left-1/2 transform -translate-x-1/2" />
                  </div>
                </motion.div>
              </div>

              <div className="absolute left-16 top-24">
                <motion.div
                  className="animate-float"
                  style={{ animationDelay: '1s' }}
                >
                  <div className="bg-[#2A5D67] w-14 h-18 rounded-lg relative shadow-lg">
                    <Building2 className="w-7 h-7 text-white absolute top-2 left-1/2 transform -translate-x-1/2" />
                    <div className="absolute bottom-2 left-1 right-1 h-0.5 bg-[#D4A574] rounded"></div>
                  </div>
                </motion.div>
              </div>

              {/* AI Brain/Circuit */}
              <div className="absolute right-8 top-20">
                <motion.div
                  className="relative"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                >
                  <div className="w-24 h-24 bg-white rounded-full shadow-xl border-4 border-[#A9C1B7]/30 flex items-center justify-center">
                    <Brain className="w-12 h-12 text-[#2A5D67]" />
                  </div>
                  
                  {/* Pulsing effect - Changed to Oro Antico */}
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-[#D4A574]"
                    animate={{ 
                      scale: [1, 1.2, 1],
                      opacity: [0.5, 0, 0.5]
                    }}
                    transition={{ 
                      duration: 2,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                  />
                </motion.div>
              </div>

              {/* Document Flow Animation - FIXED COLORS */}
              <div className="absolute top-16 left-12">
                {documentPaths.map((path, index) => (
                  <AnimatedDocument 
                    key={index}
                    delay={path.delay}
                    path={path}
                  />
                ))}
              </div>

              {/* Chat Interface Mock */}
              <div className="absolute bottom-8 right-4 bg-white rounded-lg shadow-xl p-4 w-48 border border-[#C4BDB4]/20">
                <div className="space-y-2">
                  <div className="bg-[#F8F5F1] p-2 rounded text-xs text-[#1E293B]">
                    Nuova Circolare 15/E disponibile
                  </div>
                  <div className="bg-[#A9C1B7]/15 p-2 rounded text-xs text-[#1E293B]">
                    Analisi completata in 2.3 secondi
                  </div>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 2, delay: 2 }}
                    className="h-1 bg-[#2A5D67] rounded"
                  />
                </div>
              </div>

              {/* Neural connections - Changed to Oro Antico */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                <motion.path
                  d="M80 120 Q150 80 200 100"
                  stroke="#D4A574"
                  strokeWidth="2"
                  fill="none"
                  className="animate-draw-line"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 0.6 }}
                  transition={{ duration: 2, delay: 1.5 }}
                />
                <motion.path
                  d="M60 180 Q130 140 180 120"
                  stroke="#D4A574"
                  strokeWidth="2"
                  fill="none"
                  className="animate-draw-line"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 0.6 }}
                  transition={{ duration: 2, delay: 2 }}
                />
              </svg>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}