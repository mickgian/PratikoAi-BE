'use client'

import React from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { MessageSquare, X } from 'lucide-react'
import { Button } from './ui/button'

interface ChatInterfaceProps {
  isOpen: boolean
  onToggle: () => void
}

export function ChatInterface({ isOpen, onToggle }: ChatInterfaceProps) {
  return (
    <>
      {/* Chat Toggle Button */}
      <motion.div
        className="fixed bottom-6 right-6 z-50"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
      >
        <Button
          onClick={onToggle}
          className="w-16 h-16 rounded-full bg-[#2A5D67] hover:bg-[#1E293B] shadow-xl"
          size="icon"
        >
          {isOpen ? (
            <X className="w-8 h-8 text-white" />
          ) : (
            <MessageSquare className="w-8 h-8 text-white" />
          )}
        </Button>
      </motion.div>

      {/* Chat Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-24 right-6 w-96 h-[500px] bg-white rounded-lg shadow-2xl border border-[#C4BDB4]/20 z-40 flex flex-col"
          >
            {/* Chat Header */}
            <div className="bg-[#2A5D67] text-white p-4 rounded-t-lg">
              <h3 className="font-semibold">PratikoAI Assistant</h3>
              <p className="text-xs text-[#A9C1B7]">Online e pronto ad aiutarti</p>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 p-4 bg-[#F8F5F1] overflow-y-auto">
              <div className="space-y-4">
                <div className="bg-white p-3 rounded-lg shadow-sm">
                  <p className="text-sm text-[#1E293B]">
                    Ciao! Sono qui per aiutarti con tutte le tue domande su fiscalita, normative e molto altro.
                  </p>
                </div>
              </div>
            </div>

            {/* Chat Input */}
            <div className="p-4 border-t border-[#C4BDB4]/20">
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="Scrivi la tua domanda..."
                  className="flex-1 px-3 py-2 border border-[#C4BDB4]/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2A5D67]/20"
                />
                <Button size="sm" className="bg-[#2A5D67] hover:bg-[#1E293B]">
                  Invia
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}