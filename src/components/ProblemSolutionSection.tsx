'use client'

import React from 'react'
import { motion } from 'motion/react'
import { Clock, FileStack, Sparkles, ArrowRight } from 'lucide-react'

export function ProblemSolutionSection() {
  const cards = [
    {
      type: 'problem',
      icon: Clock,
      title: 'Tempo Sprecato',
      description: 'Perdi ore cercando circolari e aggiornamenti sparsi in diverse banche dati?',
      animation: 'timeWasting',
      color: '#2A5D67'
    },
    {
      type: 'problem', 
      icon: FileStack,
      title: 'Sovraccarico Informativo',
      description: 'Sommerso da normative che cambiano ogni settimana senza un sistema organizzato?',
      animation: 'stackGrowing',
      color: '#2A5D67'
    },
    {
      type: 'solution',
      icon: Sparkles,
      title: 'Soluzione Intelligente',
      description: 'PratikoAI trova e applica le risposte in secondi, sempre aggiornate.',
      animation: 'sparkleReveal',
      color: '#2A5D67'
    }
  ]

  const TimeWastingAnimation = () => (
    <div className="relative w-16 h-16 mx-auto">
      <motion.div
        className="absolute inset-0 border-4 border-[#2A5D67] rounded-full"
        animate={{ rotate: 360 }}
        transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute top-1/2 left-1/2 w-0.5 h-6 bg-[#2A5D67] origin-bottom -translate-x-1/2 -translate-y-6"
        animate={{ rotate: [0, 360] }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute top-1/2 left-1/2 w-0.5 h-4 bg-[#1E293B] origin-bottom -translate-x-1/2 -translate-y-4"
        animate={{ rotate: [0, 30] }}
        transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
      />
      {/* Draining effect */}
      <motion.div
        className="absolute bottom-0 left-1/2 w-1 bg-[#D4A574] origin-top -translate-x-1/2"
        animate={{ height: [0, 20, 0] }}
        transition={{ duration: 3, repeat: Infinity, repeatDelay: 1 }}
      />
    </div>
  )

  const StackGrowingAnimation = () => (
    <div className="relative w-16 h-16 mx-auto flex flex-col justify-end">
      {[1, 2, 3, 4, 5].map((layer, index) => (
        <motion.div
          key={layer}
          className="w-full bg-[#2A5D67] rounded-sm border border-[#1E293B]/20 mb-0.5"
          initial={{ height: 8, opacity: 0.5 }}
          animate={{
            height: [8, 12, 8],
            opacity: [0.5, 0.9, 0.5],
            y: [0, -2, 0]
          }}
          transition={{
            duration: 2,
            delay: index * 0.2,
            repeat: Infinity,
            repeatType: 'reverse'
          }}
        />
      ))}
      {/* Overflow indicator */}
      <motion.div
        className="absolute -top-2 left-1/2 transform -translate-x-1/2"
        animate={{ 
          y: [-5, 0, -5],
          opacity: [0, 1, 0]
        }}
        transition={{ 
          duration: 1.5,
          repeat: Infinity 
        }}
      >
        <div className="text-xs text-[#D4A574] font-bold">...</div>
      </motion.div>
    </div>
  )

  const SparkleRevealAnimation = () => (
    <div className="relative w-16 h-16 mx-auto">
      <motion.div
        className="absolute inset-0 bg-[#2A5D67] rounded-full flex items-center justify-center"
        animate={{ 
          scale: [0.8, 1, 0.8],
          boxShadow: [
            '0 0 0 0 rgba(42, 93, 103, 0.3)',
            '0 0 0 8px rgba(42, 93, 103, 0)',
            '0 0 0 0 rgba(42, 93, 103, 0.3)'
          ]
        }}
        transition={{ 
          duration: 2,
          repeat: Infinity 
        }}
      >
        <Sparkles className="w-8 h-8 text-white" />
      </motion.div>
      
      {/* Sparkle particles */}
      {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, index) => (
        <motion.div
          key={angle}
          className="absolute w-1 h-1 bg-[#D4A574] rounded-full"
          style={{
            top: '50%',
            left: '50%',
            transformOrigin: '0 0',
          }}
          animate={{
            rotate: angle,
            x: [0, 30, 0],
            opacity: [0, 1, 0],
            scale: [0, 1, 0]
          }}
          transition={{
            duration: 2,
            delay: index * 0.1,
            repeat: Infinity,
            repeatDelay: 1
          }}
        />
      ))}
    </div>
  )

  const getAnimation = (animationType: string) => {
    switch (animationType) {
      case 'timeWasting':
        return <TimeWastingAnimation />
      case 'stackGrowing':
        return <StackGrowingAnimation />
      case 'sparkleReveal':
        return <SparkleRevealAnimation />
      default:
        return null
    }
  }

  return (
    <section className="bg-white py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold text-[#2A5D67] mb-4">
            Trasforma il Problema in Opportunità
          </h2>
          <p className="text-xl text-[#1E293B] max-w-3xl mx-auto">
            Ogni professionista affronta le stesse sfide quotidiane. 
            È tempo di una soluzione intelligente.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {cards.map((card, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 50, rotateY: -15 }}
              whileInView={{ opacity: 1, y: 0, rotateY: 0 }}
              viewport={{ once: true }}
              transition={{ 
                duration: 0.6,
                delay: index * 0.2,
                type: "spring",
                stiffness: 100
              }}
              whileHover={{ 
                y: -10,
                rotateY: 5,
                transition: { duration: 0.3 }
              }}
              className={`relative overflow-hidden rounded-2xl p-8 transition-all duration-300 ${
                card.type === 'solution' 
                  ? 'bg-gradient-to-br from-[#2A5D67] to-[#1E293B] text-white shadow-2xl' 
                  : 'bg-white shadow-lg hover:shadow-xl border border-[#C4BDB4]/20'
              }`}
            >
              {/* Background decoration */}
              <div className={`absolute top-0 right-0 w-32 h-32 opacity-10 transform rotate-12 translate-x-8 -translate-y-8 ${
                card.type === 'solution' ? 'text-white' : 'text-[#2A5D67]'
              }`}>
                <card.icon className="w-full h-full" />
              </div>

              <div className="relative z-10">
                {/* Icon Animation */}
                <div className="mb-6">
                  {getAnimation(card.animation)}
                </div>

                <h3 className={`text-2xl font-bold mb-4 ${
                  card.type === 'solution' ? 'text-[#D4A574]' : 'text-[#1E293B]'
                }`}>
                  {card.title}
                </h3>

                <p className={`text-lg leading-relaxed mb-6 ${
                  card.type === 'solution' ? 'text-white/90' : 'text-[#1E293B]'
                }`}>
                  {card.description}
                </p>

                {card.type === 'solution' && (
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.8 }}
                    className="flex items-center text-[#D4A574] font-semibold"
                  >
                    <span>Scopri come</span>
                    <motion.div
                      animate={{ x: [0, 5, 0] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      <ArrowRight className="w-5 h-5 ml-2" />
                    </motion.div>
                  </motion.div>
                )}
              </div>

              {/* Animated border for solution card */}
              {card.type === 'solution' && (
                <motion.div
                  className="absolute inset-0 rounded-2xl border-2 border-[#D4A574]"
                  animate={{
                    boxShadow: [
                      '0 0 0 0 rgba(212, 165, 116, 0.4)',
                      '0 0 0 4px rgba(212, 165, 116, 0)',
                      '0 0 0 0 rgba(212, 165, 116, 0.4)'
                    ]
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity
                  }}
                />
              )}
            </motion.div>
          ))}
        </div>

        {/* Connection line animation */}
        <div className="hidden md:block relative mt-8">
          <svg className="absolute top-0 left-0 w-full h-4 pointer-events-none">
            <motion.path
              d="M 120 20 Q 400 -20 680 20"
              stroke="#D4A574"
              strokeWidth="2"
              fill="none"
              strokeDasharray="5,5"
              initial={{ pathLength: 0, opacity: 0 }}
              whileInView={{ pathLength: 1, opacity: 0.6 }}
              viewport={{ once: true }}
              transition={{ duration: 2, delay: 1 }}
            />
            <motion.circle
              cx="120"
              cy="20"
              r="3"
              fill="#2A5D67"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 1.5 }}
            />
          </svg>
        </div>
      </div>
    </section>
  )
}