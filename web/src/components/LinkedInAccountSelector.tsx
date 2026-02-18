import React from 'react'
import Image from 'next/image'
import { motion, AnimatePresence } from 'motion/react'
import { Button } from './ui/button'
import { X, Check, Briefcase } from 'lucide-react'

interface LinkedInAccount {
  id: string
  name: string
  email: string
  title: string
  company: string
  avatar: string
  connections: number
}

interface LinkedInAccountSelectorProps {
  isOpen: boolean
  onClose: () => void
  onSelectAccount: (account: LinkedInAccount) => void
}

const mockLinkedInAccounts: LinkedInAccount[] = [
  {
    id: '1',
    name: 'Marco Ferretti',
    email: 'marco.ferretti@studiolegale.it',
    title: 'Avvocato Senior',
    company: 'Studio Legale Ferretti & Partners',
    avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face',
    connections: 500
  },
  {
    id: '2',
    name: 'Elena Bianchi',
    email: 'elena.bianchi@consulenza.it',
    title: 'Consulente del Lavoro',
    company: 'Bianchi Consulenza HR',
    avatar: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=150&h=150&fit=crop&crop=face',
    connections: 750
  },
  {
    id: '3',
    name: 'Giuseppe Verde',
    email: 'giuseppe.verde@tributario.it',
    title: 'Specialista Diritto Tributario',
    company: 'Verde & Associati',
    avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&h=150&fit=crop&crop=face',
    connections: 320
  }
]

export function LinkedInAccountSelector({ isOpen, onClose, onSelectAccount }: LinkedInAccountSelectorProps) {
  const handleAccountSelect = (account: LinkedInAccount) => {
    onSelectAccount(account)
    onClose()
  }

  const handleUseAnotherAccount = () => {
    // In a real implementation, this would trigger the LinkedIn OAuth flow
    alert('Reindirizzamento a LinkedIn per autenticazione...')
    onClose()
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            {/* Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-[#C4BDB4]/20 bg-gradient-to-r from-[#0A66C2]/5 to-[#0A66C2]/10">
                <div className="flex items-center space-x-3">
                  <svg className="w-6 h-6" fill="#0A66C2" viewBox="0 0 24 24">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                  </svg>
                  <div>
                    <h3 className="text-xl font-semibold text-[#2A5D67]">Scegli un account</h3>
                    <p className="text-sm text-[#1E293B]">per continuare con PratikoAI</p>
                  </div>
                </div>
                <Button
                  onClick={onClose}
                  variant="ghost"
                  size="sm"
                  className="text-[#C4BDB4] hover:text-[#2A5D67] hover:bg-[#F8F5F1] rounded-full w-8 h-8 p-0"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>

              {/* Account List */}
              <div className="max-h-80 overflow-y-auto">
                {mockLinkedInAccounts.map((account, index) => (
                  <motion.button
                    key={account.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => handleAccountSelect(account)}
                    className="w-full p-4 hover:bg-[#F8F5F1] transition-colors duration-200 flex items-center space-x-4 border-b border-[#C4BDB4]/10 last:border-b-0 group"
                  >
                    <div className="relative">
                      <Image
                        src={account.avatar}
                        alt={account.name}
                        width={56}
                        height={56}
                        className="w-14 h-14 rounded-full object-cover ring-2 ring-[#0A66C2]/20"
                      />
                      {/* LinkedIn professional indicator */}
                      <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-[#0A66C2] rounded-full flex items-center justify-center shadow-sm">
                        <Briefcase className="w-3 h-3 text-white" />
                      </div>
                    </div>
                    <div className="flex-1 text-left">
                      <p className="font-semibold text-[#2A5D67] text-base">{account.name}</p>
                      <p className="text-sm text-[#1E293B] font-medium">{account.title}</p>
                      <p className="text-sm text-[#0A66C2] hover:underline">{account.company}</p>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="text-xs text-[#C4BDB4]">{account.connections}+ connessioni</span>
                        <span className="text-xs text-[#C4BDB4]">•</span>
                        <span className="text-xs text-[#C4BDB4]">{account.email}</span>
                      </div>
                    </div>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <Check className="w-5 h-5 text-[#0A66C2]" />
                    </div>
                  </motion.button>
                ))}
              </div>

              {/* Footer Actions */}
              <div className="p-4 border-t border-[#C4BDB4]/20 bg-gradient-to-r from-[#0A66C2]/5 to-[#0A66C2]/10">
                <Button
                  onClick={handleUseAnotherAccount}
                  variant="outline"
                  className="w-full border-[#0A66C2] text-[#0A66C2] hover:bg-[#0A66C2] hover:text-white transition-all duration-200"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Usa un altro account LinkedIn
                </Button>

                <div className="mt-3 text-center">
                  <p className="text-xs text-[#C4BDB4]">
                    Accedendo, accetti di condividere le informazioni del tuo profilo LinkedIn con PratikoAI.
                  </p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}