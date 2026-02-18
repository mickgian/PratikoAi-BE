'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'motion/react'
import { Building2, Award, Shield, Clock } from 'lucide-react'

export function SocialProofBar() {
  const [clientCount, setClientCount] = useState(0)
  const targetCount = 18

  useEffect(() => {
    const duration = 2000 // 2 seconds
    const increment = targetCount / (duration / 16) // 60fps
    
    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= targetCount) {
        setClientCount(targetCount)
        clearInterval(timer)
      } else {
        setClientCount(Math.floor(current))
      }
    }, 16)

    return () => clearInterval(timer)
  }, [])

  const clientLogos = [
    { name: "Commercialisti", icon: Building2 },
    { name: "Consulenti del Lavoro", icon: Award },
    { name: "CAF (Centri di Assistenza Fiscale)", icon: Shield },
    { name: "Patronati", icon: Clock },
    { name: "Ragionieri e Periti Commerciali", icon: Building2 },
    { name: "Avvocati", icon: Award },
    { name: "Notai", icon: Shield },
    { name: "Revisori Legali e Sindaci", icon: Clock },
    { name: "Consulenti Aziendali", icon: Building2 },
    { name: "Uffici Amministrativi PMI", icon: Award },
    { name: "Studi Associati Multidisciplinari", icon: Shield },
    { name: "Società di Consulenza", icon: Clock },
    { name: "Agenti Immobiliari", icon: Building2 },
    { name: "Consulenti Finanziari", icon: Award },
    { name: "Amministratori di Condominio", icon: Shield },
    { name: "Liberi Professionisti con Partita IVA", icon: Clock },
    { name: "Praticanti e Tirocinanti presso studi professionali", icon: Building2 },
    { name: "Formatori e Docenti di materie fiscali", icon: Award },
  ]

  return (
    <section className="bg-[#A9C1B7] py-12 relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0 bg-gradient-to-r from-[#2A5D67] to-transparent"></div>
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="flex items-center justify-center space-x-4"
          >
            <span className="text-2xl font-semibold text-[#1E293B]">
              Utile per oltre
            </span>
            <motion.span
              key={clientCount}
              initial={{ scale: 1.2, color: '#D4A574' }} // FIXED: Changed to Oro Antico
              animate={{ scale: 1, color: '#2A5D67' }}
              className="text-4xl font-bold"
            >
              {clientCount}+
            </motion.span>
            <span className="text-2xl font-semibold text-[#1E293B]">
              categorie professionali
            </span>
          </motion.div>
        </div>

        {/* Auto-scrolling logos - FIXED: Changed to white pills */}
        <div className="relative">
          <div className="flex overflow-hidden">
            <motion.div
              className="flex space-x-8 min-w-max"
              animate={{ x: ['0%', '-50%'] }}
              transition={{
                duration: 60,
                repeat: Infinity,
                ease: 'linear',
              }}
            >
              {/* First set */}
              {clientLogos.map((client, index) => (
                <motion.div
                  key={`first-${index}`}
                  className="flex items-center space-x-3 bg-white px-6 py-4 rounded-lg shadow-sm border border-[#C4BDB4]/20 min-w-max" // FIXED: Changed to white background
                  whileHover={{ scale: 1.05, y: -2 }}
                  transition={{ type: 'spring', stiffness: 300 }}
                >
                  <client.icon className="w-6 h-6 text-[#2A5D67]" />
                  <span className="text-[#2A5D67] font-medium whitespace-nowrap"> {/* FIXED: Changed to Blu Petrolio text */}
                    {client.name}
                  </span>
                </motion.div>
              ))}
              
              {/* Duplicate set for seamless loop */}
              {clientLogos.map((client, index) => (
                <motion.div
                  key={`second-${index}`}
                  className="flex items-center space-x-3 bg-white px-6 py-4 rounded-lg shadow-sm border border-[#C4BDB4]/20 min-w-max" // FIXED: Changed to white background
                  whileHover={{ scale: 1.05, y: -2 }}
                  transition={{ type: 'spring', stiffness: 300 }}
                >
                  <client.icon className="w-6 h-6 text-[#2A5D67]" />
                  <span className="text-[#2A5D67] font-medium whitespace-nowrap"> {/* FIXED: Changed to Blu Petrolio text */}
                    {client.name}
                  </span>
                </motion.div>
              ))}
            </motion.div>
          </div>
          
          {/* Gradient overlays */}
          <div className="absolute left-0 top-0 w-32 h-full bg-gradient-to-r from-[#A9C1B7] to-transparent pointer-events-none"></div>
          <div className="absolute right-0 top-0 w-32 h-full bg-gradient-to-l from-[#A9C1B7] to-transparent pointer-events-none"></div>
        </div>

        {/* Trust indicators */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-wrap justify-center items-center gap-6 mt-8"
        >
          <div className="flex items-center space-x-2 text-[#1E293B]">
            <Shield className="w-5 h-5 text-[#2A5D67]" />
            <span className="font-medium">Certificato GDPR</span>
          </div>
          <div className="flex items-center space-x-2 text-[#1E293B]">
            <Clock className="w-5 h-5 text-[#2A5D67]" />
            <span className="font-medium">Aggiornamenti H24</span>
          </div>
          <div className="flex items-center space-x-2 text-[#1E293B]">
            <Award className="w-5 h-5 text-[#2A5D67]" />
            <span className="font-medium">WCAG 2.2</span>
          </div>
        </motion.div>
      </div>
    </section>
  )
}